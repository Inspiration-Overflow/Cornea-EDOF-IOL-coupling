from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import pytest

from whole_eye_mvp.zos import (
    MfeZernikeError,
    MfeZernikeResult,
    MfeZernikeStandardRunner,
    MfeZernikeStandardSettings,
)

EXPECTED_HEADERS = {
    2: "Term",
    3: "Wave",
    4: "Samp",
    5: "Field",
    6: "Type",
    7: "Epsilon",
    8: "Vertex?",
}


class FakeCell:
    def __init__(self, header: str, *, reject_integer: bool = False) -> None:
        self._header = header
        self._reject_integer = reject_integer
        self._value: Any = None
        self.last_setter = ""

    @property
    def Header(self) -> str:
        return self._header

    @property
    def Value(self) -> str:
        return str(self._value)

    @property
    def IntegerValue(self) -> Any:
        return self._value

    @IntegerValue.setter
    def IntegerValue(self, value: Any) -> None:
        if self._reject_integer:
            raise TypeError("cell does not accept integer assignment")
        self._value = value
        self.last_setter = "integer"

    @property
    def DoubleValue(self) -> Any:
        return self._value

    @DoubleValue.setter
    def DoubleValue(self, value: Any) -> None:
        self._value = value
        self.last_setter = "double"


class FakeOperand:
    def __init__(
        self,
        value: float,
        *,
        header_override: dict[int, str] | None = None,
    ) -> None:
        headers = dict(EXPECTED_HEADERS)
        if header_override:
            headers.update(header_override)
        self.headers = headers
        self.cells = {
            position: FakeCell(headers[position], reject_integer=(position == 7))
            for position in headers
        }
        self.changed_types: list[Any] = []
        self._value = value

    def ChangeType(self, value: Any) -> None:
        self.changed_types.append(value)

    def GetCellAt(self, position: int) -> FakeCell:
        if position not in self.cells:
            raise AttributeError(f"no cell at position {position}")
        return self.cells[position]

    @property
    def Value(self) -> float:
        return self._value

    @property
    def Type(self) -> str:
        return "ZERN" if self.changed_types else "BLNK"


class FakeMfe:
    def __init__(
        self,
        *,
        baseline_operands: int = 1,
        operand_values: list[float] | None = None,
        header_override: dict[int, str] | None = None,
        insert_error: Exception | None = None,
        insert_returns_none: bool = False,
        calculate_error: Exception | None = None,
        remove_error: Exception | None = None,
        remove_is_broken: bool = False,
    ) -> None:
        self.baseline_operands = baseline_operands
        self._values = list(operand_values or [0.0, 0.0])
        self._header_override = header_override
        self.insert_error = insert_error
        self.insert_returns_none = insert_returns_none
        self.calculate_error = calculate_error
        self.remove_error = remove_error
        self.remove_is_broken = remove_is_broken
        self.extra: list[FakeOperand] = []
        self.created: list[FakeOperand] = []
        self.insert_calls: list[int] = []
        self.remove_calls: list[tuple[int, int]] = []
        self.calculate_calls = 0

    @property
    def NumberOfOperands(self) -> int:
        return self.baseline_operands + len(self.extra)

    def InsertNewOperandAt(self, row: int) -> Any:
        self.insert_calls.append(row)
        if self.insert_error is not None:
            raise self.insert_error
        if self.insert_returns_none:
            return None
        operand = FakeOperand(
            self._values.pop(0),
            header_override=self._header_override,
        )
        self.extra.append(operand)
        self.created.append(operand)
        return operand

    def RemoveOperandsAt(self, row: int, count: int) -> int:
        self.remove_calls.append((row, count))
        if self.remove_error is not None:
            raise self.remove_error
        if self.remove_is_broken:
            return 0
        del self.extra[-count:]
        return count

    def CalculateMeritFunction(self) -> float:
        self.calculate_calls += 1
        if self.calculate_error is not None:
            raise self.calculate_error
        return 0.0


class FakeSystem:
    def __init__(self, mfe: FakeMfe, wavelength_um: float = 0.546) -> None:
        self.MFE = mfe
        self.SystemData = SimpleNamespace(
            Wavelengths=SimpleNamespace(
                GetWavelength=lambda number: SimpleNamespace(Wavelength=wavelength_um)
            )
        )


class FakeZosApi:
    def __init__(self) -> None:
        self.Editors = SimpleNamespace(
            MFE=SimpleNamespace(MeritOperandType=SimpleNamespace(ZERN="ZERN"))
        )


def _runner(mfe: FakeMfe) -> MfeZernikeStandardRunner:
    return MfeZernikeStandardRunner(FakeSystem(mfe), FakeZosApi())


@pytest.mark.unit
def test_settings_defaults_freeze_acquisition_contract() -> None:
    settings = MfeZernikeStandardSettings()
    settings.validate()
    assert settings.term_primary == 11
    assert settings.term_maximum == 37
    assert settings.wavelength_number == 1
    assert settings.field_number == 1
    assert settings.sampling == 1
    assert settings.zernike_type == 1
    assert settings.epsilon == 0.0
    assert settings.vertex == 0

    with pytest.raises(ValueError, match="term_primary"):
        MfeZernikeStandardSettings(term_primary=5).validate()
    with pytest.raises(ValueError, match="term_maximum"):
        MfeZernikeStandardSettings(term_maximum=9).validate()
    with pytest.raises(ValueError, match="Standard Zernike type"):
        MfeZernikeStandardSettings(zernike_type=2).validate()
    with pytest.raises(ValueError, match="epsilon"):
        MfeZernikeStandardSettings(epsilon=1.0).validate()
    with pytest.raises(ValueError, match="vertex"):
        MfeZernikeStandardSettings(vertex=2).validate()
    with pytest.raises(ValueError, match="sampling"):
        MfeZernikeStandardSettings(sampling=0).validate()


@pytest.mark.unit
def test_z11_to_c40_conversion_matches_gui_oracle() -> None:
    result = MfeZernikeResult(
        wavelength_um=0.546,
        z11_waves=0.47360558,
        z37_waves=0.00025905,
    )
    assert result.c40_um == pytest.approx(0.25858864668)
    assert result.z11_waves == 0.47360558
    assert result.z37_waves == 0.00025905

    with pytest.raises(ValueError, match="finite"):
        MfeZernikeResult(wavelength_um=0.546, z11_waves=math.nan, z37_waves=0.0)
    with pytest.raises(ValueError, match="wavelength"):
        MfeZernikeResult(wavelength_um=0.0, z11_waves=0.1, z37_waves=0.0)


@pytest.mark.unit
def test_runner_writes_adjacent_zern_operands_and_cleans_up() -> None:
    mfe = FakeMfe(baseline_operands=3, operand_values=[0.47360558, 0.00025905])
    result = _runner(mfe).run(MfeZernikeStandardSettings())

    assert mfe.insert_calls == [4, 5]
    row11, row37 = mfe.created
    assert [operand.changed_types for operand in (row11, row37)] == [["ZERN"], ["ZERN"]]
    assert row11.cells[2].Value == "11"
    assert row37.cells[2].Value == "37"
    for position in (3, 4, 5, 6):
        assert row11.cells[position].Value == "1"
        assert row37.cells[position].Value == "1"
    assert row11.cells[7].Value == "0.0"
    assert row11.cells[7].last_setter == "double"
    assert row11.cells[8].Value == "0"
    assert mfe.calculate_calls == 1
    assert mfe.remove_calls == [(4, 2)]
    assert mfe.NumberOfOperands == 3
    assert result.z11_waves == pytest.approx(0.47360558)
    assert result.z37_waves == pytest.approx(0.00025905)
    assert result.wavelength_um == pytest.approx(0.546)


@pytest.mark.unit
def test_runner_fails_closed_on_non_finite_coefficients() -> None:
    mfe = FakeMfe(operand_values=[math.nan, 0.00025905])
    with pytest.raises(MfeZernikeError, match="non-finite"):
        _runner(mfe).run(MfeZernikeStandardSettings())
    assert mfe.remove_calls == [(2, 2)]
    assert mfe.NumberOfOperands == 1


@pytest.mark.unit
def test_runner_fails_closed_on_calculate_failure_and_still_cleans_up() -> None:
    mfe = FakeMfe(calculate_error=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        _runner(mfe).run(MfeZernikeStandardSettings())
    assert mfe.remove_calls == [(2, 2)]
    assert mfe.NumberOfOperands == 1


@pytest.mark.unit
def test_runner_fails_closed_on_operand_create_failure() -> None:
    mfe = FakeMfe(insert_error=RuntimeError("insert failed"))
    with pytest.raises(MfeZernikeError, match="insert"):
        _runner(mfe).run(MfeZernikeStandardSettings())
    assert mfe.remove_calls == []
    assert mfe.NumberOfOperands == 1

    none_mfe = FakeMfe(insert_returns_none=True)
    with pytest.raises(MfeZernikeError, match="returned no operand"):
        _runner(none_mfe).run(MfeZernikeStandardSettings())


@pytest.mark.unit
def test_runner_fails_closed_on_unexpected_parameter_cell_layout() -> None:
    mfe = FakeMfe(operand_values=[0.1, 0.2], header_override={3: "Wavelength"})
    with pytest.raises(MfeZernikeError, match="cell layout"):
        _runner(mfe).run(MfeZernikeStandardSettings())
    assert mfe.remove_calls == [(2, 2)]
    assert mfe.NumberOfOperands == 1


@pytest.mark.unit
def test_runner_fails_closed_when_cleanup_leaves_operands() -> None:
    mfe = FakeMfe(operand_values=[0.1, 0.2], remove_is_broken=True)
    with pytest.raises(MfeZernikeError, match="cleanup left the MFE modified"):
        _runner(mfe).run(MfeZernikeStandardSettings())


@pytest.mark.unit
def test_runner_fails_closed_on_cleanup_api_failure() -> None:
    mfe = FakeMfe(operand_values=[0.1, 0.2], remove_error=RuntimeError("remove failed"))
    with pytest.raises(MfeZernikeError, match="failed to remove"):
        _runner(mfe).run(MfeZernikeStandardSettings())
