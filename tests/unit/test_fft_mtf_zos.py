from __future__ import annotations

from types import SimpleNamespace

import pytest

from whole_eye_mvp.zos import FftMtfError, FftMtfRunner, FftMtfSettings


class Vector:
    def __init__(self, data):
        self.Data = tuple(data)
        self.Length = len(self.Data)


class MatrixData:
    def __init__(self, rows):
        self.Data = Matrix(rows)


class Matrix:
    def __init__(self, rows):
        self.rows = rows

    def __getitem__(self, key):
        row, column = key
        return self.rows[row][column]


class Series:
    def __init__(self, labels=("Tangential", "Sagittal")):
        self.Description = "Field 1"
        self.XLabel = "Spatial Frequency in cycles per mm"
        self.XData = Vector((0.0, 50.0, 100.0))
        self.NumSeries = 2
        self.SeriesLabels = labels
        self.YData = MatrixData(((1.0, 1.0), (0.8, 0.7), (0.5, 0.4)))


class Results:
    IsValid = True

    def __init__(self, series=None):
        self.DataSeries = (series or Series(),)


class Selector:
    def __init__(self):
        self.value = None

    def SetWavelengthNumber(self, value):
        self.value = value

    def SetFieldNumber(self, value):
        self.value = value

    def UseImageSurface(self):
        self.value = "image"


class Settings:
    def __init__(self):
        self.Wavelength = Selector()
        self.Field = Selector()
        self.Surface = Selector()


class Analysis:
    def __init__(self, results=None):
        self.settings = Settings()
        self.results = results or Results()
        self.closed = False

    def GetSettings(self):
        return self.settings

    def ApplyAndWaitForCompletion(self):
        return None

    def GetResults(self):
        return self.results

    def Close(self):
        self.closed = True


class Analyses:
    def __init__(self, analysis):
        self.analysis = analysis

    def New_FftMtf(self):
        return self.analysis


def fake_zosapi():
    return SimpleNamespace(
        Analysis=SimpleNamespace(
            SampleSizes=SimpleNamespace(S_64x64="S64", S_128x128="S128", S_256x256="S256"),
            Settings=SimpleNamespace(
                Mtf=SimpleNamespace(MtfTypes=SimpleNamespace(Modulation="MOD"))
            ),
        )
    )


@pytest.mark.unit
def test_fft_mtf_runner_sets_explicit_modulation_settings_and_copies_series() -> None:
    analysis = Analysis()
    runner = FftMtfRunner(SimpleNamespace(Analyses=Analyses(analysis)), fake_zosapi())
    result = runner.run(FftMtfSettings(128, 220.0))

    settings = analysis.settings
    assert settings.MaximumFrequency == 220.0
    assert settings.ShowDiffractionLimit is False
    assert settings.UsePolarization is False
    assert settings.UseDashes is False
    assert settings.SampleSize == "S128"
    assert settings.Type == "MOD"
    assert settings.Wavelength.value == 1
    assert settings.Field.value == 1
    assert settings.Surface.value == "image"
    assert result.frequency_cycles_per_mm == (0.0, 50.0, 100.0)
    assert result.tangential_mtf == (1.0, 0.8, 0.5)
    assert result.sagittal_mtf == (1.0, 0.7, 0.4)
    assert result.analysis_api_name == "New_FftMtf"
    assert result.settings_implementation_type == "Settings"
    assert result.sample_size_enum == "S_128x128"
    assert result.modulation_enum == "Modulation"
    assert result.data_series_count == 1
    assert result.data_series_runtime_type == "tuple"
    assert result.selected_series_runtime_type == "Series"
    assert result.series_labels == ("Tangential", "Sagittal")
    assert "cycles per mm" in result.x_label
    assert analysis.closed


@pytest.mark.unit
def test_fft_mtf_runner_fails_closed_when_series_labels_do_not_identify_axes() -> None:
    analysis = Analysis(Results(Series(("A", "B"))))
    runner = FftMtfRunner(SimpleNamespace(Analyses=Analyses(analysis)), fake_zosapi())
    with pytest.raises(FftMtfError, match="SeriesLabels"):
        runner.run(FftMtfSettings(128, 220.0))
    assert analysis.closed


@pytest.mark.unit
@pytest.mark.parametrize(
    "settings",
    (
        FftMtfSettings(16, 200.0),
        FftMtfSettings(128, 0.0),
        FftMtfSettings(128, 200.0, wavelength_number=0),
    ),
)
def test_fft_mtf_settings_reject_invalid_values(settings) -> None:
    with pytest.raises(ValueError):
        settings.validate()
