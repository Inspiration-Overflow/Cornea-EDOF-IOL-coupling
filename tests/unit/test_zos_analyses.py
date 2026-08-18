from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from whole_eye_mvp.domain import NOMINAL_MAIN_555_V1
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
    def __init__(
        self,
        rows: list[list[float]],
        *,
        dx: float = 0.5,
        dy: float = 0.5,
        min_x: float | None = None,
        min_y: float | None = None,
    ) -> None:
        self.Values = Values(rows)
        self.Ny = len(rows)
        self.Nx = len(rows[0])
        self.Dx = dx
        self.Dy = dy
        self.MinX = -0.5 * self.Nx * dx if min_x is None else min_x
        self.MinY = -0.5 * self.Ny * dy if min_y is None else min_y
        self.XLabel = "X"
        self.YLabel = "Y"
        self.ValueLabel = "Intensity"
        self.Description = "fake"


class Results:
    def __init__(self, grid: Grid, *, valid: bool = True) -> None:
        self.IsValid = valid
        self.NumberOfDataGrids = 1
        self.grid = grid

    def GetDataGrid(self, index: int) -> Grid:
        assert index == 0
        return self.grid


class Analysis:
    def __init__(self, grid: Grid) -> None:
        self.settings = Settings()
        self.results = Results(grid)
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
    def __init__(self, grid: Grid) -> None:
        self.analysis = Analysis(grid)

    def New_HuygensPsf(self) -> Analysis:
        return self.analysis


def fake_zosapi() -> SimpleNamespace:
    return SimpleNamespace(
        Analysis=SimpleNamespace(
            AnalysisIDM=SimpleNamespace(HuygensPsf="HPSF"),
            SampleSizes=SimpleNamespace(
                S_32x32="S32",
                S_64x64="S64",
                S_128x128="S128",
                S_256x256="S256",
            ),
            Settings=SimpleNamespace(
                HuygensPsfTypes=SimpleNamespace(Linear="LINEAR"),
                Psf=SimpleNamespace(IAS_HuygensPsf=lambda value: value),
            ),
        )
    )


def square_rows(size: int, value: float = 1.0) -> list[list[float]]:
    return [[value for _ in range(size)] for _ in range(size)]


@pytest.mark.unit
def test_huygens_psf_copies_grid_and_applies_explicit_settings() -> None:
    analyses = Analyses(Grid(square_rows(32)))
    runner = HuygensPsfRunner(SimpleNamespace(Analyses=analyses), fake_zosapi())
    grid = runner.run(HuygensPsfSettings(32, 32, 0.5, wavelength_number=2, field_number=3))

    configured = analyses.analysis.settings
    assert configured.PupilSampleSize == "S32"
    assert configured.ImageSampleSize == "S32"
    assert configured.ImageDelta == 0.5
    assert configured.Type == "LINEAR"
    assert configured.Normalize is True
    assert configured.UseCentroid is False
    assert configured.UsePolarization is False
    assert configured.Wavelength.selected == 2
    assert configured.Field.selected == 3
    assert grid.shape == (32, 32)
    assert grid.total_energy == 1024.0
    assert analyses.analysis.ran and analyses.analysis.closed


@pytest.mark.unit
def test_zos_analysis_settings_are_derived_from_frozen_analysis_settings() -> None:
    psf = HuygensPsfSettings.from_analysis_settings(NOMINAL_MAIN_555_V1)
    zernike = ZernikeStandardSettings.from_analysis_settings(NOMINAL_MAIN_555_V1)

    assert psf.pupil_sampling == 128
    assert psf.image_sampling == 256
    assert psf.image_delta_um == 0.5
    assert psf.normalize is True and psf.use_centroid is False
    assert zernike.sample_size == 32
    assert zernike.maximum_terms == 37
    assert zernike.reference_opd_to_vertex is False
    assert zernike.normalized_radius == 1.0


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
@pytest.mark.parametrize(
    "grid,error",
    (
        (Grid(square_rows(32, math.nan)), "non-finite"),
        (Grid(square_rows(32, math.inf)), "non-finite"),
        (Grid(square_rows(32, -1.0)), "negative"),
        (Grid(square_rows(32), dx=0.25, dy=0.25), "ImageDelta"),
        (Grid(square_rows(32), min_x=100.0), "centered"),
        (Grid(square_rows(64)), "shape mismatch"),
    ),
)
def test_huygens_psf_rejects_invalid_result_and_still_closes(
    grid: Grid,
    error: str,
) -> None:
    analyses = Analyses(grid)
    runner = HuygensPsfRunner(SimpleNamespace(Analyses=analyses), fake_zosapi())

    with pytest.raises(HuygensPsfError, match=error):
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
        parse_zernike_standard_text(
            complete.rsplit("\n", 1)[0], maximum_terms=28, wavelength_um=0.5
        )
    with pytest.raises(ZernikeStandardError, match="duplicate"):
        parse_zernike_standard_text(
            complete + "\nZ 28 0.0 : duplicate", maximum_terms=28, wavelength_um=0.5
        )
    with pytest.raises(ValueError):
        ZernikeStandardSettings(16).validate()
    with pytest.raises(ValueError):
        ZernikeStandardSettings(32, maximum_terms=22).validate()
