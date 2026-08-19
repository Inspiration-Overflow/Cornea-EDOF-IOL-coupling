from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .analyses import _analysis_settings, _is_valid_result, _matrix, _set_sample_size, _vector
from .primitives import SystemAnalysisRunner


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
        allowed = {32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384}
        if self.pupil_sampling not in allowed or self.image_sampling not in allowed:
            raise ValueError("unsupported Huygens MTF sampling")
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


def _split_mtf_rows(
    frequencies: tuple[float, ...],
    matrix: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    n = len(frequencies)
    if not matrix:
        raise HuygensMtfError("Huygens MTF returned an empty y-data matrix")

    # ZOS-API has exposed MTF data in both frequency-major and curve-major matrix shapes
    # across examples/versions.  Accept either shape, but never guess if neither matches.
    if len(matrix) == n and all(len(row) >= 2 for row in matrix):
        first = tuple(float(row[0]) for row in matrix)
        second = tuple(float(row[1]) for row in matrix)
        return first, second
    if len(matrix) >= 2 and len(matrix[0]) == n and len(matrix[1]) == n:
        return tuple(float(value) for value in matrix[0]), tuple(
            float(value) for value in matrix[1]
        )
    if len(matrix) == n and all(len(row) == 1 for row in matrix):
        single = tuple(float(row[0]) for row in matrix)
        return single, single
    if len(matrix) == 1 and len(matrix[0]) == n:
        single = tuple(float(value) for value in matrix[0])
        return single, single
    raise HuygensMtfError(
        f"unexpected Huygens MTF y-data shape: rows={len(matrix)}, "
        f"columns={tuple(len(row) for row in matrix[:4])}, frequency_count={n}"
    )


def _parse_curve(results: Any) -> HuygensMtfCurve:
    if not _is_valid_result(results):
        raise HuygensMtfError("Huygens MTF returned an invalid result")
    if int(results.NumberOfDataSeries) < 1:
        raise HuygensMtfError("Huygens MTF returned no data series")
    series = results.GetDataSeries(0)
    frequencies = tuple(float(value) for value in _vector(series.xData.Data))
    tangential, sagittal = _split_mtf_rows(frequencies, _matrix(series.yData.Data))
    if len(frequencies) < 2 or len(tangential) != len(frequencies):
        raise HuygensMtfError("Huygens MTF returned inconsistent curve lengths")
    if any(
        not math.isfinite(value)
        for value in (*frequencies, *tangential, *sagittal)
    ):
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
        runner = SystemAnalysisRunner(self.system, self.zosapi)
        analysis = runner.open_analysis("HuygensMtf")
        try:
            target = _analysis_settings(analysis.GetSettings())
            _set_sample_size(target, "PupilSampleSize", settings.pupil_sampling, self.zosapi)
            _set_sample_size(target, "ImageSampleSize", settings.image_sampling, self.zosapi)
            target.ImageDelta = float(settings.image_delta_um)
            target.MaximumFrequency = float(settings.maximum_frequency_cyc_per_mm)
            target.Wavelength.SetWavelengthNumber(settings.wavelength_number)
            target.Field.SetFieldNumber(settings.field_number)
            if hasattr(target, "UsePolarization"):
                target.UsePolarization = bool(settings.use_polarization)
            return runner.run_and_parse(analysis, _parse_curve)
        finally:
            runner.close(analysis)
