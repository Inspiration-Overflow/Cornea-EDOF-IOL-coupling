from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .primitives import SystemAnalysisRunner

SUPPORTED_SAMPLE_SIZES = frozenset(2**power for power in range(5, 15))


class HuygensMtfError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class HuygensMtfSettings:
    pupil_sampling: int = 128
    image_sampling: int = 256
    image_delta_um: float = 0.5
    maximum_frequency_cyc_per_mm: float = 50.0
    wavelength_number: int = 1
    field_number: int = 1
    use_polarization: bool = False

    def validate(self) -> None:
        if self.pupil_sampling not in SUPPORTED_SAMPLE_SIZES:
            raise ValueError(f"unsupported Huygens MTF pupil sampling: {self.pupil_sampling}")
        if self.image_sampling not in SUPPORTED_SAMPLE_SIZES:
            raise ValueError(f"unsupported Huygens MTF image sampling: {self.image_sampling}")
        if not math.isfinite(self.image_delta_um) or self.image_delta_um <= 0:
            raise ValueError("Huygens MTF image delta must be finite and positive")
        if (
            not math.isfinite(self.maximum_frequency_cyc_per_mm)
            or self.maximum_frequency_cyc_per_mm <= 0
        ):
            raise ValueError("Huygens MTF maximum frequency must be finite and positive")
        if self.wavelength_number < 1 or self.field_number < 1:
            raise ValueError("Huygens MTF wavelength/field numbers are 1-based")


@dataclass(frozen=True, slots=True)
class HuygensMtfCurve:
    frequency_cyc_per_mm: tuple[float, ...]
    tangential: tuple[float, ...]
    sagittal: tuple[float, ...]
    average: tuple[float, ...]


def _sample_size(zosapi: Any, value: int) -> Any:
    try:
        return getattr(zosapi.Analysis.SampleSizes, f"S_{value}x{value}")
    except AttributeError as exc:
        raise HuygensMtfError(
            f"installed API exposes no Huygens MTF sample size {value}x{value}"
        ) from exc


def _copy_vector(data: Any) -> tuple[float, ...]:
    try:
        length = int(data.Length)
        return tuple(float(data[index]) for index in range(length))
    except (AttributeError, TypeError):
        try:
            length = int(data.GetLength(0))
            return tuple(float(data.GetValue(index)) for index in range(length))
        except (AttributeError, TypeError) as exc:
            raise HuygensMtfError("unable to copy Huygens MTF x-data vector") from exc


def _copy_series_matrix(
    data: Any,
    x_count: int,
    series_count: int,
) -> tuple[tuple[float, ...], ...]:
    if x_count < 1 or series_count < 1:
        raise HuygensMtfError("Huygens MTF series dimensions must be positive")
    try:
        rows = int(data.GetLength(0))
        columns = int(data.GetLength(1))
    except AttributeError as exc:
        raise HuygensMtfError("unable to inspect Huygens MTF y-data matrix") from exc
    if rows != x_count or columns < series_count:
        raise HuygensMtfError(
            "Huygens MTF y-data dimensions differ from the DataSeries contract: "
            f"matrix={(rows, columns)}, x_count={x_count}, series_count={series_count}"
        )
    return tuple(
        tuple(float(data.GetValue(x_index, series_index)) for series_index in range(series_count))
        for x_index in range(x_count)
    )


def _parse_curve(results: Any) -> HuygensMtfCurve:
    implementation = getattr(results, "__implementation__", results)
    if not bool(implementation.IsValid):
        raise HuygensMtfError("Huygens MTF returned an invalid result")
    data_series_count = int(implementation.NumberOfDataSeries)
    if data_series_count < 1:
        raise HuygensMtfError("Huygens MTF returned no data series")
    # When a diffraction-limit series is exposed it precedes the actual system MTF.
    # B0 requires the actual system response, so use the final series deterministically.
    series = implementation.GetDataSeries(data_series_count - 1)
    if series is None or series.XData is None or series.YData is None:
        raise HuygensMtfError("Huygens MTF returned an incomplete DataSeries")
    frequencies = _copy_vector(series.XData.Data)
    series_count = int(series.NumSeries)
    matrix = _copy_series_matrix(series.YData.Data, len(frequencies), series_count)
    if series_count == 1:
        tangential = tuple(row[0] for row in matrix)
        sagittal = tangential
    else:
        tangential = tuple(row[0] for row in matrix)
        sagittal = tuple(row[1] for row in matrix)
    if len(frequencies) < 2:
        raise HuygensMtfError("Huygens MTF returned fewer than two frequency samples")
    values = (*frequencies, *tangential, *sagittal)
    if not all(math.isfinite(value) for value in values):
        raise HuygensMtfError("Huygens MTF returned non-finite data")
    if any(right <= left for left, right in zip(frequencies, frequencies[1:])):
        raise HuygensMtfError("Huygens MTF frequencies must be strictly increasing")
    average = tuple(0.5 * (t + s) for t, s in zip(tangential, sagittal, strict=True))
    if any(value < -1.0e-9 or value > 1.01 for value in average):
        raise HuygensMtfError("Huygens MTF modulation lies outside the expected [0, 1] range")
    return HuygensMtfCurve(frequencies, tangential, sagittal, average)


@dataclass(slots=True)
class HuygensMtfRunner:
    system: Any
    zosapi: Any

    def run(self, settings: HuygensMtfSettings) -> HuygensMtfCurve:
        settings.validate()
        lifecycle = SystemAnalysisRunner(self.system, self.zosapi)
        analysis = lifecycle.open_analysis("HuygensMtf")
        try:
            raw = analysis.GetSettings()
            target = getattr(raw, "__implementation__", raw)
            target.PupilSampleSize = _sample_size(
                self.zosapi,
                settings.pupil_sampling,
            )
            target.ImageSampleSize = _sample_size(
                self.zosapi,
                settings.image_sampling,
            )
            target.ImageDelta = float(settings.image_delta_um)
            target.MaximumFrequency = float(settings.maximum_frequency_cyc_per_mm)
            target.Wavelength.SetWavelengthNumber(settings.wavelength_number)
            target.Field.SetFieldNumber(settings.field_number)
            if hasattr(target, "ShowDiffractionLimit"):
                target.ShowDiffractionLimit = False
            if hasattr(target, "UsePolarization"):
                target.UsePolarization = bool(settings.use_polarization)
            return lifecycle.run_and_parse(analysis, _parse_curve)
        finally:
            lifecycle.close(analysis)
