from __future__ import annotations

from types import SimpleNamespace

import pytest

from whole_eye_mvp.zos import (
    TASK009_MFE_FULL_HOA_555_V1,
    MfeEfflRunner,
    MfeFullHoaRunner,
)


class Cell:
    def __init__(self, header=""):
        self.Header = header
        self.IntegerValue = 0
        self.DoubleValue = 0.0


class Operand:
    def __init__(self, value=0.0):
        self.Value = value
        self.kind = None
        self.cells = {
            2: Cell("Term"),
            3: Cell("Wave"),
            4: Cell("Samp"),
            5: Cell("Field"),
            6: Cell("Type"),
            7: Cell("Epsilon"),
            8: Cell("Vertex?"),
        }

    def ChangeType(self, kind):
        self.kind = kind

    def GetCellAt(self, position):
        return self.cells[position]


class MFE:
    def __init__(self, *, effl_value=17.0):
        self.NumberOfOperands = 0
        self.operands = []
        self.effl_value = effl_value

    def InsertNewOperandAt(self, row):
        assert row == self.NumberOfOperands + 1
        operand = Operand()
        self.operands.append(operand)
        self.NumberOfOperands += 1
        return operand

    def CalculateMeritFunction(self):
        for operand in self.operands:
            if operand.kind == "EFFL":
                operand.Value = self.effl_value
            elif operand.kind == "ZERN":
                term = int(operand.cells[2].IntegerValue)
                operand.Value = term / 1000.0

    def RemoveOperandsAt(self, row, count):
        assert row == 1
        del self.operands[:count]
        self.NumberOfOperands -= count


def fake_system(mfe):
    wavelength = SimpleNamespace(Wavelength=0.555)
    return SimpleNamespace(
        MFE=mfe,
        SystemData=SimpleNamespace(
            Wavelengths=SimpleNamespace(GetWavelength=lambda _number: wavelength)
        ),
    )


def fake_zosapi():
    return SimpleNamespace(
        Editors=SimpleNamespace(
            MFE=SimpleNamespace(
                MeritOperandType=SimpleNamespace(EFFL="EFFL", ZERN="ZERN")
            )
        )
    )


@pytest.mark.unit
def test_effl_runner_returns_positive_mm_and_restores_mfe() -> None:
    mfe = MFE(effl_value=17.25)
    result = MfeEfflRunner(fake_system(mfe), fake_zosapi()).run()
    assert result.effective_focal_length_mm == pytest.approx(17.25)
    assert mfe.NumberOfOperands == 0


@pytest.mark.unit
def test_full_hoa_settings_identity_is_frozen() -> None:
    settings = TASK009_MFE_FULL_HOA_555_V1
    settings.validate()
    assert settings.settings_id == "TASK009_MFE_ZERN_HOA_555_v1"
    assert settings.settings_hash == "7c9a2d3a7685a6df14be4d9382e7c71a6d92ae8dfa76fb5502ecfd820974fcc2"


@pytest.mark.unit
def test_full_hoa_runner_reads_terms_7_through_28_and_computes_metrics() -> None:
    mfe = MFE()
    result = MfeFullHoaRunner(fake_system(mfe), fake_zosapi()).run()
    assert len(result.coefficients_waves) == 22
    assert result.c40_um == pytest.approx(0.011 * 0.555)
    assert result.c60_um == pytest.approx(0.022 * 0.555)
    assert result.hoa_rms_um > 0
    assert result.settings_id == TASK009_MFE_FULL_HOA_555_V1.settings_id
    assert result.settings_hash == TASK009_MFE_FULL_HOA_555_V1.settings_hash
    assert mfe.NumberOfOperands == 0
