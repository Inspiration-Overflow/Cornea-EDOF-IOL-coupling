from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .primitives import SystemAnalysisRunner, ZosPrimitiveError


class FftMtfError(ZosPrimitiveError):
    """FFT MTF settings or returned data violate the acquisition contract."""


@dataclass(frozen=True, slots=True)
class FftMtfSettings:
    sampling: int
    maximum_frequency_cyc_per_mm: float
    wavelength_number: int = 1
    field_number: int = 1
    use_polarization: bool = False

    def validate(self) -> None:
        if self.sampling not in (32, 64, 128, 256, 512, 1024, 2048):
            raise ValueError(f"unsupported FFT MTF pupil sampling: {self.sampling}")
        if (
            not math.isfinite(self.maximum_frequency_cyc_per_mm)
            or self.maximum_frequency_cyc_per_mm <= 0
        ):
            raise ValueError("FFT MTF maximum frequency must be finite and positive")
        if self.wavelength_number < 1 or self.field_number < 1:
            raise ValueError("FFT MTF wavelength and field numbers are 1-based")


@dataclass(frozen=True, slots=True)
class FftMtfResult:
    frequency_cycles_per_mm: tuple[float, ...]
    tangential_mtf: tuple[float, ...]
    sagittal_mtf: tuple[float, ...]
    description: str
    x_label: str
    series_labels: tuple[str, ...]
    analysis_api_name: str
    settings_implementation_type: str
    sample_size_enum: str
    modulation_enum: str
    data_series_count: int
    data_series_runtime_type: str
    selected_series_runtime_type: str

    def validate(self) -> None:
        n = len(self.frequency_cycles_per_mm)
        if n < 2 or len(self.tangential_mtf) != n or len(self.sagittal_mtf) != n:
            raise FftMtfError("FFT MTF result vectors must have equal length >= 2")
        if not all(math.isfinite(value) for value in self.frequency_cycles_per_mm):
            raise FftMtfError("FFT MTF frequency axis contains a non-finite value")
        if any(
            right <= left
            for left, right in zip(
                self.frequency_cycles_per_mm,
                self.frequency_cycles_per_mm[1:],
                strict=False,
            )
        ):
            raise FftMtfError("FFT MTF frequency axis must be strictly increasing")
        for values in (self.tangential_mtf, self.sagittal_mtf):
            if not all(math.isfinite(value) and value >= 0 for value in values):
                raise FftMtfError("FFT MTF modulation data must be finite and non-negative")
        for value in (
            self.analysis_api_name,
            self.settings_implementation_type,
            self.sample_size_enum,
            self.modulation_enum,
            self.data_series_runtime_type,
            self.selected_series_runtime_type,
        ):
            if not value.strip():
                raise FftMtfError("FFT MTF runtime API metadata is incomplete")
        if self.data_series_count < 1:
            raise FftMtfError("FFT MTF DataSeries count must be positive")


@dataclass(slots=True)
class FftMtfRunner:
    system: Any
    zosapi: Any

    def run(self, settings: FftMtfSettings) -> FftMtfResult:
        settings.validate()
        lifecycle = SystemAnalysisRunner(self.system, self.zosapi)
        try:
            analysis = self.system.Analyses.New_FftMtf()
        except AttributeError as exc:
            raise FftMtfError("installed API does not expose New_FftMtf") from exc
        try:
            raw_settings = analysis.GetSettings()
            target = getattr(raw_settings, "__implementation__", raw_settings)
            sample_enum, modulation_enum = self._configure(target, settings)
            settings_type = type(target).__name__
            return lifecycle.run_and_parse(
                analysis,
                lambda results: self._parse_results(
                    results,
                    settings_implementation_type=settings_type,
                    sample_size_enum=sample_enum,
                    modulation_enum=modulation_enum,
                ),
            )
        finally:
            lifecycle.close(analysis)

    def _configure(self, target: Any, settings: FftMtfSettings) -> tuple[str, str]:
        target.MaximumFrequency = float(settings.maximum_frequency_cyc_per_mm)
        target.ShowDiffractionLimit = False
        target.UsePolarization = bool(settings.use_polarization)
        target.UseDashes = False

        sample_sizes = self.zosapi.Analysis.SampleSizes
        sample_value = None
        sample_name = ""
        for name in (
            f"S_{settings.sampling}x{settings.sampling}",
            f"_{settings.sampling}x{settings.sampling}",
        ):
            if hasattr(sample_sizes, name):
                sample_value = getattr(sample_sizes, name)
                sample_name = name
                break
        if sample_value is None:
            raise FftMtfError(
                f"installed API exposes no FFT MTF sample enum for {settings.sampling}x{settings.sampling}"
            )
        target.SampleSize = sample_value

        mtf_types = self.zosapi.Analysis.Settings.Mtf.MtfTypes
        modulation = None
        modulation_name = ""
        for name in ("Modulation", "ModulationTransferFunction", "MTF"):
            if hasattr(mtf_types, name):
                modulation = getattr(mtf_types, name)
                modulation_name = name
                break
        if modulation is None:
            raise FftMtfError("installed API exposes no modulation MTF enum")
        target.Type = modulation
        target.Wavelength.SetWavelengthNumber(settings.wavelength_number)
        target.Field.SetFieldNumber(settings.field_number)
        target.Surface.UseImageSurface()
        return sample_name, modulation_name

    @staticmethod
    def _copy_vector(vector: Any) -> tuple[float, ...]:
        length = int(vector.Length)
        data = vector.Data
        return tuple(float(data[index]) for index in range(length))

    @staticmethod
    def _matrix_value(matrix: Any, row: int, column: int) -> float:
        data = matrix.Data
        try:
            return float(data[row, column])
        except TypeError:
            return float(data.GetValue(row, column))

    @classmethod
    def _parse_results(
        cls,
        results: Any,
        *,
        settings_implementation_type: str,
        sample_size_enum: str,
        modulation_enum: str,
    ) -> FftMtfResult:
        implementation = getattr(results, "__implementation__", results)
        if hasattr(implementation, "IsValid") and not bool(implementation.IsValid):
            raise FftMtfError("FFT MTF returned an invalid result")
        data_series = getattr(implementation, "DataSeries", None)
        if data_series is None:
            raise FftMtfError("FFT MTF returned no DataSeries")

        series_items = tuple(data_series)
        candidates: list[Any] = []
        for series in series_items:
            if series is None:
                continue
            x_data = getattr(series, "XData", None)
            y_data = getattr(series, "YData", None)
            if x_data is None or y_data is None:
                continue
            if int(getattr(series, "NumSeries", 0)) == 2:
                candidates.append(series)
        if len(candidates) != 1:
            raise FftMtfError(
                f"FFT MTF expected exactly one two-column field series; received {len(candidates)}"
            )

        series = candidates[0]
        labels = tuple(str(value) for value in tuple(series.SeriesLabels))
        normalized = tuple(label.casefold() for label in labels)
        tangential_index = next(
            (index for index, label in enumerate(normalized) if "tang" in label), None
        )
        sagittal_index = next(
            (index for index, label in enumerate(normalized) if "sag" in label), None
        )
        if tangential_index is None or sagittal_index is None or tangential_index == sagittal_index:
            raise FftMtfError(
                "FFT MTF cannot identify tangential/sagittal columns from SeriesLabels: "
                + repr(labels)
            )

        frequencies = cls._copy_vector(series.XData)
        rows = len(frequencies)
        tangential = tuple(
            cls._matrix_value(series.YData, row, tangential_index) for row in range(rows)
        )
        sagittal = tuple(
            cls._matrix_value(series.YData, row, sagittal_index) for row in range(rows)
        )
        result = FftMtfResult(
            frequency_cycles_per_mm=frequencies,
            tangential_mtf=tangential,
            sagittal_mtf=sagittal,
            description=str(series.Description),
            x_label=str(series.XLabel),
            series_labels=labels,
            analysis_api_name="New_FftMtf",
            settings_implementation_type=settings_implementation_type,
            sample_size_enum=sample_size_enum,
            modulation_enum=modulation_enum,
            data_series_count=len(series_items),
            data_series_runtime_type=type(data_series).__name__,
            selected_series_runtime_type=type(series).__name__,
        )
        result.validate()
        return result
