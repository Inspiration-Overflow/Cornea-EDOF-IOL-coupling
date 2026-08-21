from __future__ import annotations

from types import SimpleNamespace

import pytest

from whole_eye_mvp.zos.fft_mtf import FftMtfRunner, FftMtfSettings


class XData:
    def __init__(self, values: tuple[float, ...]):
        self.values = values
        self.Length = len(values)

    def GetValueAt(self, index: int) -> float:
        return self.values[index]


class YData:
    def __init__(self, rows: tuple[tuple[float, float], ...]):
        self.rows = rows

    def GetValueAt(self, index: int, series: int) -> float:
        return self.rows[index][series]


class DataSeries:
    def __init__(self):
        self.XData = XData((0.0, 50.0, 100.0))
        self.YData = YData(((1.0, 1.0), (0.5, 0.4), (0.2, 0.1)))
        self.NumSeries = 2


class Results:
    NumberOfDataSeries = 1

    def GetDataSeries(self, index: int) -> DataSeries:
        assert index == 0
        return DataSeries()


class Settings:
    def __init__(self):
        self.MaximumFrequency = None
        self.SampleSize = None


class Analysis:
    def __init__(self):
        self.settings = Settings()
        self.ran = False
        self.closed = False

    def GetSettings(self) -> Settings:
        return self.settings

    def ApplyAndWaitForCompletion(self) -> None:
        self.ran = True

    def GetResults(self) -> Results:
        assert self.ran
        return Results()

    def Close(self) -> None:
        self.closed = True


class Analyses:
    def __init__(self):
        self.last: Analysis | None = None

    def New_FftMtf(self) -> Analysis:
        self.last = Analysis()
        return self.last


@pytest.mark.unit
def test_fft_mtf_runner_configures_parses_and_closes_analysis() -> None:
    system = SimpleNamespace(Analyses=Analyses())
    zosapi = SimpleNamespace(
        Analysis=SimpleNamespace(
            SampleSizes=SimpleNamespace(S_128x128="S128")
        )
    )
    settings = FftMtfSettings(maximum_frequency_cyc_per_mm=100.0, sample_size=128)
    result = FftMtfRunner(system, zosapi).run(settings)

    assert system.Analyses.last is not None
    assert system.Analyses.last.settings.MaximumFrequency == pytest.approx(100.0)
    assert system.Analyses.last.settings.SampleSize == "S128"
    assert system.Analyses.last.closed
    assert result.series[0].frequencies_cyc_per_mm == (0.0, 50.0, 100.0)
    assert result.series[0].tangential == (1.0, 0.5, 0.2)
    assert result.series[0].sagittal == (1.0, 0.4, 0.1)
