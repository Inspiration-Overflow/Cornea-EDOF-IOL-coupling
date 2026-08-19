from __future__ import annotations

import pytest

from whole_eye_mvp.zos.huygens_mtf import (
    HuygensMtfError,
    HuygensMtfSettings,
    _parse_curve,
)


class VectorData:
    def __init__(self, values: tuple[float, ...]) -> None:
        self._values = values
        self.Length = len(values)

    def __getitem__(self, index: int) -> float:
        return self._values[index]


class MatrixData:
    def __init__(self, rows: tuple[tuple[float, ...], ...]) -> None:
        self._rows = rows

    def GetLength(self, dimension: int) -> int:
        return len(self._rows) if dimension == 0 else len(self._rows[0])

    def GetValue(self, row: int, column: int) -> float:
        return self._rows[row][column]


class Container:
    def __init__(self, data) -> None:
        self.Data = data


class Series:
    def __init__(self) -> None:
        self.XData = Container(VectorData((0.0, 25.0, 50.0)))
        self.YData = Container(
            MatrixData(
                (
                    (1.0, 1.0),
                    (0.7, 0.5),
                    (0.3, 0.1),
                )
            )
        )
        self.NumSeries = 2


class Results:
    IsValid = True
    NumberOfDataSeries = 1

    def GetDataSeries(self, index: int):
        assert index == 0
        return Series()


@pytest.mark.unit
def test_huygens_mtf_settings_freeze_b0_sampling_defaults() -> None:
    settings = HuygensMtfSettings()
    settings.validate()
    assert settings.pupil_sampling == 128
    assert settings.image_sampling == 256
    assert settings.image_delta_um == 0.5
    assert settings.maximum_frequency_cyc_per_mm == 50.0


@pytest.mark.unit
def test_huygens_mtf_parser_uses_frequency_major_dataseries_contract() -> None:
    curve = _parse_curve(Results())
    assert curve.frequency_cyc_per_mm == (0.0, 25.0, 50.0)
    assert curve.tangential == (1.0, 0.7, 0.3)
    assert curve.sagittal == (1.0, 0.5, 0.1)
    assert curve.average == pytest.approx((1.0, 0.6, 0.2))


@pytest.mark.unit
def test_huygens_mtf_parser_rejects_nonmonotonic_frequency() -> None:
    bad = Results()
    series = bad.GetDataSeries(0)
    series.XData = Container(VectorData((0.0, 50.0, 25.0)))
    bad.GetDataSeries = lambda index: series
    with pytest.raises(HuygensMtfError, match="strictly increasing"):
        _parse_curve(bad)
