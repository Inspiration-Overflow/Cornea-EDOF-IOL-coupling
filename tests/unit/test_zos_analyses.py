from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from whole_eye_mvp.zos import (
    HuygensPsfError,
    HuygensPsfRunner,
    HuygensPsfSettings,
    ZernikeStandardError,
    ZernikeStandardSettings,
    parse_zernike_standard_text,
)


class Selector:
    def __init__(self) -> None:
        self.selected: int | None = None

    def SetWavelengthNumber(self, number: int) -> None:
        self.selected = number

    def SetFieldNumber(self, number: int) -> None:
        self.selected = number


class Settings:
    def __init__(self) -> None:
        self.Wavelength = Selector()
        self.Field = Selector()


class Values:
    Rank = 2

    def __init__(self, rows: list[list[float]]) -> None:
        self.rows = rows

    def GetLength(self, dimension: int) -> int:
        return len(self.rows) if dimension == 0 else len(self.rows[0])

    def GetValue(self, row: int, column: int) -> float:
        return self.rows[row][column]


class Grid:
    def __init__(self, rows: list[list[float]]) -> None:
        self.Values = Values(rows)
        self.Ny = len(rows)
        self.Nx = len(rows[0])
        self.MinX = -1.0
        self.MinY = -1.0
        self.Dx = 0.5
        self.Dy = 0.5
        self.XLabel = "X"
        self.YLabel = "Y"
        self.ValueLabel = "Intensity"
        self.Description = "fake"


class Results:
    def __init__(self, rows: list[list[float]], *, valid: bool = True) -> None:
        self.IsValid = valid
        self.NumberOfDataGrids = 1
        self.grid = Grid(rows)

    def GetDataGrid(self, index: int) -> Grid:
        assert index == 0
        return self.grid


class Analysis:
    def __init__(self, rows: list[list[float]]) -> None:
        self.settings = Settings()
        self.results = Results(rows)
        self.ran = False
        self.closed = False

    def GetSettings(self) -> Settings:
        return self.settings

    def ApplyAndWaitForCompletion(self) -> None:
        self.ran = True

    def GetResults(self) -> Results:
        return self.results

    def Close(self) -> None:
        self.closed = True


class Analyses:
    def __init__(self, rows: list[list[float]]) -> None:
        self.analysis = Analysis(rows)

    def New_HuygensPsf(self) -> Analysis:
        return self.analysis


def fake_zosapi() -> SimpleNamespace:
    return SimpleNamespace(
        Analysis=SimpleNamespace(
            AnalysisIDM=SimpleNamespace(HuygensPsf="HPSF"),
            SampleSizes=SimpleNamespace(S_32x32="S32", S_64x64="S64"),
            Settings=SimpleNamespace(
                HuygensPsfTypes=SimpleNamespace(Linear="LINEAR"),
                Psf=SimpleNamespace(IAS_HuygensPsf=lambda value: value),
            ),
        )
    )


@pytest.mark.unit
def test_huygens_psf_copies_grid_and_applies_explicit_settings() -> None:
    analyses = Analyses([[1.0, 2.0], [3.0, 4.0]])
    runner = HuygensPsfRunner(SimpleNamespace(Analyses=analyses), fake_zosapi())
    grid = runner.run(HuygensPsfSettings(32, 64, 0.5, wavelength_number=2, field_number=3))

    configured = analyses.analysis.settings
    assert configured.PupilSampleSize == "S32"
    assert configured.ImageSampleSize == "S64"
    assert configured.ImageDelta == 0.5
    assert configured.Type == "LINEAR"
    assert configured.Normalize is True
    assert configured.UseCentroid is False
    assert configured.UsePolarization is False
    assert configured.Wavelength.selected == 2
    assert configured.Field.selected == 3
    assert grid.values == ((1.0, 2.0), (3.0, 4.0))
    assert grid.shape == (2, 2)
    assert grid.total_energy == 10.0
    assert analyses.analysis.ran and analyses.analysis.closed


@pytest.mark.unit
@pytest.mark.parametrize(
    "settings",
    (
        HuygensPsfSettings(16, 32, 0.5),
        HuygensPsfSettings(32, 16, 0.5),
        HuygensPsfSettings(32, 32, 0.0),
        HuygensPsfSettings(32, 32, 0.5, wavelength_number=0),
    ),
)
def test_huygens_psf_rejects_invalid_settings_before_opening_analysis(
    settings: HuygensPsfSettings,
) -> None:
    with pytest.raises(ValueError):
        settings.validate()


@pytest.mark.unit
@pytest.mark.parametrize("bad_value", (math.nan, math.inf, 0.0))
def test_huygens_psf_rejects_invalid_result_and_still_closes(bad_value: float) -> None:
    analyses = Analyses([[bad_value]])
    runner = HuygensPsfRunner(SimpleNamespace(Analyses=analyses), fake_zosapi())

    with pytest.raises(HuygensPsfError):
        runner.run(HuygensPsfSettings(32, 32, 0.5))

    assert analyses.analysis.closed


@pytest.mark.unit
def test_zernike_text_parser_converts_waves_and_uses_standard_term_groups() -> None:
    values = {term: 0.0 for term in range(1, 29)}
    values[7] = 0.1
    values[11] = 0.2
    values[22] = -0.4
    text = "\n".join(
        f"Z {term:3d}\t{value:.8f}\t:\tterm {term}" for term, value in values.items()
    )

    result = parse_zernike_standard_text(text, maximum_terms=28, wavelength_um=0.5)

    assert len(result.coefficients) == 28
    assert result.c40_um == pytest.approx(0.1)
    assert result.c60_um == pytest.approx(-0.2)
    assert result.hoa_n3_to_n6_rms_um == pytest.approx(
        0.5 * math.sqrt(0.1**2 + 0.2**2 + 0.4**2)
    )
    with pytest.raises(KeyError, match="Z0"):
        result.coefficient_waves(0)


@pytest.mark.unit
def test_zernike_text_parser_rejects_missing_duplicate_and_invalid_settings() -> None:
    complete = "\n".join(f"Z {term} 0.0 : term" for term in range(1, 29))
    with pytest.raises(ZernikeStandardError, match="missing"):
        parse_zernike_standard_text(complete.rsplit("\n", 1)[0], maximum_terms=28, wavelength_um=0.5)
    with pytest.raises(ZernikeStandardError, match="duplicate"):
        parse_zernike_standard_text(
            complete + "\nZ 28 0.0 : duplicate", maximum_terms=28, wavelength_um=0.5
        )
    with pytest.raises(ValueError):
        ZernikeStandardSettings(16).validate()
    with pytest.raises(ValueError):
        ZernikeStandardSettings(32, maximum_terms=22).validate()
