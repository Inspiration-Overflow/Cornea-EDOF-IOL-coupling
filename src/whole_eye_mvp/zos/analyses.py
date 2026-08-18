from __future__ import annotations

import math
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .primitives import SystemAnalysisRunner, ZosPrimitiveError

SUPPORTED_SAMPLE_SIZES = frozenset(2**power for power in range(5, 15))


class HuygensPsfError(ZosPrimitiveError):
    """The Huygens PSF settings or returned grid violate the acquisition contract."""


@dataclass(frozen=True, slots=True)
class HuygensPsfSettings:
    pupil_sampling: int
    image_sampling: int
    image_delta_um: float
    wavelength_number: int = 1
    field_number: int = 1
    normalize: bool = True
    use_centroid: bool = False
    use_polarization: bool = False

    def validate(self) -> None:
        if self.pupil_sampling not in SUPPORTED_SAMPLE_SIZES:
            raise ValueError(f"unsupported Huygens pupil sampling: {self.pupil_sampling}")
        if self.image_sampling not in SUPPORTED_SAMPLE_SIZES:
            raise ValueError(f"unsupported Huygens image sampling: {self.image_sampling}")
        if not math.isfinite(self.image_delta_um) or self.image_delta_um <= 0:
            raise ValueError("Huygens image delta must be finite and positive")
        if self.wavelength_number < 1 or self.field_number < 1:
            raise ValueError("Huygens wavelength and field numbers are 1-based")


@dataclass(frozen=True, slots=True)
class HuygensPsfGrid:
    values: tuple[tuple[float, ...], ...]
    min_x: float
    min_y: float
    dx: float
    dy: float
    x_label: str
    y_label: str
    value_label: str
    description: str

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.values), len(self.values[0]) if self.values else 0

    @property
    def total_energy(self) -> float:
        return math.fsum(value for row in self.values for value in row)


@dataclass(slots=True)
class HuygensPsfRunner:
    system: Any
    zosapi: Any

    def run(self, settings: HuygensPsfSettings) -> HuygensPsfGrid:
        settings.validate()
        lifecycle = SystemAnalysisRunner(self.system, self.zosapi)
        try:
            analysis = self.system.Analyses.New_HuygensPsf()
        except AttributeError as exc:
            raise HuygensPsfError("installed API does not expose New_HuygensPsf") from exc
        try:
            try:
                target = self.zosapi.Analysis.Settings.Psf.IAS_HuygensPsf(
                    analysis.GetSettings()
                )
            except (AttributeError, TypeError) as exc:
                raise HuygensPsfError(
                    "installed API cannot cast Huygens PSF settings to IAS_HuygensPsf"
                ) from exc
            self._configure(target, settings)
            return lifecycle.run_and_parse(analysis, self._cast_and_parse_grid)
        finally:
            lifecycle.close(analysis)

    def _configure(self, target: Any, settings: HuygensPsfSettings) -> None:
        sample_sizes = self.zosapi.Analysis.SampleSizes
        try:
            target.PupilSampleSize = getattr(
                sample_sizes, f"S_{settings.pupil_sampling}x{settings.pupil_sampling}"
            )
            target.ImageSampleSize = getattr(
                sample_sizes, f"S_{settings.image_sampling}x{settings.image_sampling}"
            )
        except AttributeError as exc:
            raise HuygensPsfError("installed API does not expose the requested sample size") from exc
        target.ImageDelta = float(settings.image_delta_um)
        target.Type = self.zosapi.Analysis.Settings.HuygensPsfTypes.Linear
        target.Normalize = bool(settings.normalize)
        target.UseCentroid = bool(settings.use_centroid)
        target.UsePolarization = bool(settings.use_polarization)
        target.Wavelength.SetWavelengthNumber(settings.wavelength_number)
        target.Field.SetFieldNumber(settings.field_number)

    def _cast_and_parse_grid(self, results: Any) -> HuygensPsfGrid:
        implementation = getattr(results, "__implementation__", results)
        return self._parse_grid(implementation)

    @staticmethod
    def _parse_grid(results: Any) -> HuygensPsfGrid:
        if not bool(results.IsValid) or int(results.NumberOfDataGrids) < 1:
            raise HuygensPsfError("Huygens PSF returned no valid data grid")
        grid = results.GetDataGrid(0)
        values = grid.Values
        rows = int(values.GetLength(0))
        columns = int(values.GetLength(1))
        if rows != int(grid.Ny) or columns != int(grid.Nx) or rows < 1 or columns < 1:
            raise HuygensPsfError("Huygens PSF grid dimensions are inconsistent")
        copied = tuple(
            tuple(float(values.GetValue(row, column)) for column in range(columns))
            for row in range(rows)
        )
        if not all(math.isfinite(value) for row in copied for value in row):
            raise HuygensPsfError("Huygens PSF grid contains a non-finite intensity")
        result = HuygensPsfGrid(
            values=copied,
            min_x=float(grid.MinX),
            min_y=float(grid.MinY),
            dx=float(grid.Dx),
            dy=float(grid.Dy),
            x_label=str(grid.XLabel),
            y_label=str(grid.YLabel),
            value_label=str(grid.ValueLabel),
            description=str(grid.Description),
        )
        if not math.isfinite(result.total_energy) or result.total_energy <= 0:
            raise HuygensPsfError("Huygens PSF grid has no positive total energy")
        return result


class ZernikeStandardError(ZosPrimitiveError):
    """The Zernike Standard settings or text result violate the acquisition contract."""


@dataclass(frozen=True, slots=True)
class ZernikeStandardSettings:
    sample_size: int
    maximum_terms: int = 37
    wavelength_number: int = 1
    field_number: int = 1
    reference_opd_to_vertex: bool = False
    center_x: float = 0.0
    center_y: float = 0.0
    normalized_radius: float = 1.0
    epsilon: float = 0.0

    def validate(self) -> None:
        if self.sample_size not in SUPPORTED_SAMPLE_SIZES:
            raise ValueError(f"unsupported Zernike sample size: {self.sample_size}")
        if self.maximum_terms < 28:
            raise ValueError("at least 28 Zernike terms are required for n=3..6 HOA RMS")
        if self.wavelength_number < 1 or self.field_number < 1:
            raise ValueError("Zernike wavelength and field numbers are 1-based")
        numeric = (self.center_x, self.center_y, self.normalized_radius, self.epsilon)
        if not all(math.isfinite(float(value)) for value in numeric):
            raise ValueError("Zernike reference values must be finite")
        if self.normalized_radius <= 0:
            raise ValueError("Zernike normalized radius must be positive")
        if self.epsilon < 0 or self.epsilon >= 1:
            raise ValueError("Zernike epsilon must lie in [0, 1)")


@dataclass(frozen=True, slots=True)
class ZernikeCoefficient:
    term: int
    value_waves: float
    description: str


@dataclass(frozen=True, slots=True)
class ZernikeStandardResult:
    wavelength_um: float
    coefficients: tuple[ZernikeCoefficient, ...]

    def coefficient_waves(self, term: int) -> float:
        if term < 1:
            raise KeyError(f"Zernike term Z{term} is not present")
        try:
            return self.coefficients[term - 1].value_waves
        except IndexError as exc:
            raise KeyError(f"Zernike term Z{term} is not present") from exc

    def coefficient_um(self, term: int) -> float:
        return self.coefficient_waves(term) * self.wavelength_um

    @property
    def c40_um(self) -> float:
        return self.coefficient_um(11)

    @property
    def c60_um(self) -> float:
        return self.coefficient_um(22)

    @property
    def hoa_n3_to_n6_rms_um(self) -> float:
        return self.wavelength_um * math.sqrt(
            math.fsum(self.coefficient_waves(term) ** 2 for term in range(7, 29))
        )


ZERNIKE_LINE = re.compile(
    r"^\s*Z\s+(?P<term>\d+)\s+"
    r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)"
    r"\s*:\s*(?P<description>.*)$"
)


def parse_zernike_standard_text(
    text: str,
    *,
    maximum_terms: int,
    wavelength_um: float,
) -> ZernikeStandardResult:
    if maximum_terms < 1:
        raise ValueError("maximum_terms must be positive")
    if not math.isfinite(wavelength_um) or wavelength_um <= 0:
        raise ValueError("Zernike wavelength must be finite and positive")
    by_term: dict[int, ZernikeCoefficient] = {}
    for line in text.splitlines():
        match = ZERNIKE_LINE.match(line)
        if match is None:
            continue
        term = int(match.group("term"))
        value = float(match.group("value"))
        if term in by_term:
            raise ZernikeStandardError(f"duplicate Zernike coefficient Z{term}")
        if not math.isfinite(value):
            raise ZernikeStandardError(f"non-finite Zernike coefficient Z{term}")
        by_term[term] = ZernikeCoefficient(term, value, match.group("description").strip())
    expected = set(range(1, maximum_terms + 1))
    actual = set(by_term)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ZernikeStandardError(
            f"Zernike coefficient set mismatch; missing={missing}, extra={extra}"
        )
    return ZernikeStandardResult(
        wavelength_um=float(wavelength_um),
        coefficients=tuple(by_term[term] for term in range(1, maximum_terms + 1)),
    )


@dataclass(slots=True)
class ZernikeStandardRunner:
    system: Any
    zosapi: Any

    def run(self, settings: ZernikeStandardSettings) -> ZernikeStandardResult:
        settings.validate()
        lifecycle = SystemAnalysisRunner(self.system, self.zosapi)
        try:
            analysis = self.system.Analyses.New_ZernikeStandardCoefficients()
        except AttributeError as exc:
            raise ZernikeStandardError(
                "installed API does not expose New_ZernikeStandardCoefficients"
            ) from exc
        try:
            raw_settings = analysis.GetSettings()
            target = getattr(raw_settings, "__implementation__", raw_settings)
            self._configure(target, settings)
            wavelength = self.system.SystemData.Wavelengths.GetWavelength(
                settings.wavelength_number
            )
            wavelength_um = float(wavelength.Wavelength)
            return lifecycle.run_and_parse(
                analysis,
                lambda results: self._parse_export(
                    results, settings.maximum_terms, wavelength_um
                ),
            )
        finally:
            lifecycle.close(analysis)

    def _configure(self, target: Any, settings: ZernikeStandardSettings) -> None:
        sample_sizes = self.zosapi.Analysis.SampleSizes
        try:
            target.SampleSize = getattr(
                sample_sizes, f"S_{settings.sample_size}x{settings.sample_size}"
            )
        except AttributeError as exc:
            raise ZernikeStandardError(
                "installed API does not expose the requested Zernike sample size"
            ) from exc
        target.MaximumNumberOfTerms = int(settings.maximum_terms)
        target.ReferenceOBDToVertex = bool(settings.reference_opd_to_vertex)
        target.Sx = float(settings.center_x)
        target.Sy = float(settings.center_y)
        target.Sr = float(settings.normalized_radius)
        target.Epsilon = float(settings.epsilon)
        target.Wavelength.SetWavelengthNumber(settings.wavelength_number)
        target.Field.SetFieldNumber(settings.field_number)
        target.Surface.UseImageSurface()

    @staticmethod
    def _parse_export(
        results: Any,
        maximum_terms: int,
        wavelength_um: float,
    ) -> ZernikeStandardResult:
        implementation = getattr(results, "__implementation__", results)
        if not bool(implementation.IsValid):
            raise ZernikeStandardError("Zernike Standard analysis returned an invalid result")
        with tempfile.TemporaryDirectory(prefix="whole-eye-zernike-") as temp_dir:
            text_path = Path(temp_dir) / "zernike.txt"
            if not bool(implementation.GetTextFile(str(text_path))) or not text_path.is_file():
                raise ZernikeStandardError("Zernike Standard text export failed")
            text = text_path.read_text(encoding="utf-16")
        return parse_zernike_standard_text(
            text,
            maximum_terms=maximum_terms,
            wavelength_um=wavelength_um,
        )
