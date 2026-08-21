from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .primitives import ZosPrimitiveError


class FftMtfError(ZosPrimitiveError):
    pass


@dataclass(frozen=True, slots=True)
class FftMtfSettings:
    maximum_frequency_cyc_per_mm: float = 100.0
    sample_size: int = 128

    def validate(self) -> None:
        if not math.isfinite(self.maximum_frequency_cyc_per_mm) or self.maximum_frequency_cyc_per_mm <= 0:
            raise ValueError("FFT MTF maximum frequency must be finite and positive")
        if self.sample_size not in {32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384}:
            raise ValueError("unsupported FFT MTF sample size")


@dataclass(frozen=True, slots=True)
class FftMtfSeries:
    series_number: int
    frequencies_cyc_per_mm: tuple[float, ...]
    tangential: tuple[float, ...]
    sagittal: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class FftMtfResult:
    settings: FftMtfSettings
    series: tuple[FftMtfSeries, ...]


@dataclass(slots=True)
class FftMtfRunner:
    system: Any
    zosapi: Any

    def run(self, settings: FftMtfSettings = FftMtfSettings()) -> FftMtfResult:
        settings.validate()
        try:
            analysis = self.system.Analyses.New_FftMtf()
        except AttributeError as exc:
            raise FftMtfError("installed API exposes no New_FftMtf analysis") from exc
        try:
            raw_settings = analysis.GetSettings()
            target = getattr(raw_settings, "__implementation__", raw_settings)
            target.MaximumFrequency = float(settings.maximum_frequency_cyc_per_mm)
            sample_sizes = self.zosapi.Analysis.SampleSizes
            try:
                target.SampleSize = getattr(
                    sample_sizes, f"S_{settings.sample_size}x{settings.sample_size}"
                )
            except AttributeError as exc:
                raise FftMtfError(
                    f"installed API exposes no {settings.sample_size}x{settings.sample_size} FFT sample size"
                ) from exc

            analysis.ApplyAndWaitForCompletion()
            results = analysis.GetResults()
            count = int(results.NumberOfDataSeries)
            if count < 1:
                raise FftMtfError("FFT MTF returned no data series")
            series = tuple(self._read_series(results.GetDataSeries(index), index) for index in range(count))
            return FftMtfResult(settings, series)
        finally:
            close = getattr(analysis, "Close", None)
            if callable(close):
                close()

    @staticmethod
    def _read_series(data: Any, series_number: int) -> FftMtfSeries:
        try:
            x_data = data.XData
            y_data = data.YData
            length = int(x_data.Length)
            num_series = int(data.NumSeries)
        except Exception as exc:  # noqa: BLE001 - API shape is validated at runtime
            raise FftMtfError("FFT MTF data series exposes an unexpected shape") from exc
        if length < 2 or num_series < 2:
            raise FftMtfError(
                f"FFT MTF series {series_number} must contain frequency data and two MTF traces"
            )
        frequencies = tuple(float(x_data.GetValueAt(index)) for index in range(length))
        tangential = tuple(float(y_data.GetValueAt(index, 0)) for index in range(length))
        sagittal = tuple(float(y_data.GetValueAt(index, 1)) for index in range(length))
        numeric = (*frequencies, *tangential, *sagittal)
        if not all(math.isfinite(value) for value in numeric):
            raise FftMtfError(f"FFT MTF series {series_number} contains non-finite values")
        if any(right <= left for left, right in zip(frequencies, frequencies[1:], strict=False)):
            raise FftMtfError(f"FFT MTF series {series_number} frequency axis is not increasing")
        return FftMtfSeries(series_number, frequencies, tangential, sagittal)
