from __future__ import annotations

from types import SimpleNamespace

import pytest

from whole_eye_mvp.zos import (
    MfeMtfGridError,
    MfeMtfGridRunner,
    MfeMtfGridSettings,
    sampling_index_for_grid_size,
)


class Cell:
    def __init__(self, header: str) -> None:
        self.Header = header
        self.IntegerValue = 0
        self.DoubleValue = 0.0


class Operand:
    def __init__(self) -> None:
        self.Value = 0.0
        self.kind = None
        self.cells = {
            2: Cell("Samp"),
            3: Cell("Wave"),
            4: Cell("Field"),
            5: Cell("Freq"),
            6: Cell("Grid"),
            7: Cell("Data Type"),
        }

    def ChangeType(self, kind) -> None:
        self.kind = kind

    def GetCellAt(self, position: int):
        return self.cells[position]


class MFE:
    def __init__(self) -> None:
        self.NumberOfOperands = 0
        self.operands: list[Operand] = []

    def InsertNewOperandAt(self, row: int):
        assert row == self.NumberOfOperands + 1
        operand = Operand()
        self.operands.append(operand)
        self.NumberOfOperands += 1
        return operand

    def CalculateMeritFunction(self) -> None:
        for operand in self.operands:
            frequency = float(operand.cells[5].DoubleValue)
            operand.Value = max(0.0, 1.0 - frequency / 200.0)

    def RemoveOperandsAt(self, row: int, count: int) -> None:
        assert row == 1
        del self.operands[:count]
        self.NumberOfOperands -= count


def fake_zosapi():
    return SimpleNamespace(
        Editors=SimpleNamespace(
            MFE=SimpleNamespace(
                MeritOperandType=SimpleNamespace(MTFA="MTFA", MTFS="MTFS", MTFT="MTFT")
            )
        )
    )


@pytest.mark.unit
def test_sampling_index_matches_opticstudio_grid_convention() -> None:
    assert sampling_index_for_grid_size(32) == 1
    assert sampling_index_for_grid_size(64) == 2
    assert sampling_index_for_grid_size(128) == 3
    assert sampling_index_for_grid_size(256) == 4
    with pytest.raises(ValueError):
        sampling_index_for_grid_size(96)


@pytest.mark.unit
@pytest.mark.parametrize("operand_type", ("MTFA", "MTFS", "MTFT"))
def test_mfe_mtf_grid_runner_sets_grid1_modulation_and_restores_mfe(operand_type: str) -> None:
    mfe = MFE()
    result = MfeMtfGridRunner(SimpleNamespace(MFE=mfe), fake_zosapi()).run(
        MfeMtfGridSettings(
            frequencies_cyc_per_mm=(0.0, 20.0, 40.0),
            sampling_grid_size=128,
            operand_type=operand_type,
        )
    )
    assert result.operand_type == operand_type
    assert result.sampling_grid_size == 128
    assert result.sampling_index == 3
    assert result.grid == 1
    assert result.data_type == 0
    assert result.values == pytest.approx((1.0, 0.9, 0.8))
    assert result.parameter_headers == (
        (2, "Samp"),
        (3, "Wave"),
        (4, "Field"),
        (5, "Freq"),
        (6, "Grid"),
        (7, "Data Type"),
    )
    assert mfe.NumberOfOperands == 0


@pytest.mark.unit
def test_mfe_mtf_grid_rejects_non_grid1_or_unknown_operand() -> None:
    with pytest.raises(ValueError, match="Grid=1"):
        MfeMtfGridSettings((10.0,), 128, grid=0).validate()
    with pytest.raises(ValueError, match="unsupported"):
        MfeMtfGridSettings((10.0,), 128, operand_type="MTHA").validate()


@pytest.mark.unit
def test_mfe_mtf_grid_fails_closed_on_unexpected_headers() -> None:
    mfe = MFE()
    original = mfe.InsertNewOperandAt

    def bad_insert(row: int):
        operand = original(row)
        operand.cells[6].Header = "Unknown"
        return operand

    mfe.InsertNewOperandAt = bad_insert
    with pytest.raises(MfeMtfGridError, match="cell layout"):
        MfeMtfGridRunner(SimpleNamespace(MFE=mfe), fake_zosapi()).run(
            MfeMtfGridSettings((10.0,), 128)
        )
    assert mfe.NumberOfOperands == 0
