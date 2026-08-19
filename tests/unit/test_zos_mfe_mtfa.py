from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import pytest

from whole_eye_mvp.zos import MfeMtfaError, MfeMtfaRunner, MfeMtfaSettings

EXPECTED_HEADERS = {
    2: "Samp",
    3: "Wave",
    4: "Field",
    5: "Freq",
    6: "Grid",
    7: "Data Type",
}


class FakeCell:
    def __init__(self, header: str) -> None:
        self.Header = header
        self._value: Any = None

    @property
    def IntegerValue(self) -> Any:
        return self._value

    @IntegerValue.setter
    def IntegerValue(self, value: Any) -> None:
        self._value = value

    @property
    def DoubleValue(self) -> Any:
        return self._value

    @DoubleValue.setter
    def DoubleValue(self, value: Any) -> None:
        self._value = value


class FakeOperand:
    def __init__(self, value: float, header_override: dict[int, str] | None = None) -> None:
        headers = dict(EXPECTED_HEADERS)
        if header_override:
            headers.update(header_override)
        self.cells = {position: FakeCell(header) for position, header in headers.items()}
        self.changed_types: list[Any] = []
        self._value = value

    def ChangeType(self, value: Any) -> None:
        self.changed_types.append(value)

    def GetCellAt(self, position: int) -> FakeCell:
        return self.cells[position]

    @property
    def Value(self) -> float:
        return self._value


class FakeMfe:
    def __init__(
        self,
        values: list[float],
        *,
        baseline_operands: int = 2,
        header_override: dict[int, str] | None = None,
        calculate_error: Exception | None = None,
        remove_is_broken: bool = False,
        insert_returns_none_after_add: bool = False,
    ) -> None:
        self.baseline_operands = baseline_operands
        self.values = list(values)
        self.header_override = header_override
        self.calculate_error = calculate_error
        self.remove_is_broken = remove_is_broken
        self.insert_returns_none_after_add = insert_returns_none_after_add
        self.extra: list[FakeOperand] = []
        self.created: list[FakeOperand] = []
        self.insert_calls: list[int] = []
        self.remove_calls: list[tuple[int, int]] = []
        self.calculate_calls = 0

    @property
    def NumberOfOperands(self) -> int:
        return self.baseline_operands + len(self.extra)

    def InsertNewOperandAt(self, row: int) -> FakeOperand | None:
        self.insert_calls.append(row)
        operand = FakeOperand(self.values.pop(0), self.header_override)
        self.extra.append(operand)
        self.created.append(operand)
        if self.insert_returns_none_after_add:
            return None
        return operand

    def RemoveOperandsAt(self, row: int, count: int) -> int:
        self.remove_calls.append((row, count))
        if not self.remove_is_broken:
            del self.extra[-count:]
        return count

    def CalculateMeritFunction(self) -> float:
        self.calculate_calls += 1
        if self.calculate_error is not None:
            raise self.calculate_error
        return 0.0


class FakeSystem:
    def __init__(self, mfe: FakeMfe) -> None:
        self.MFE = mfe


class FakeZosApi:
    def __init__(self) -> None:
        self.Editors = SimpleNamespace(
            MFE=SimpleNamespace(MeritOperandType=SimpleNamespace(MTFA="MTFA"))
        )


def _runner(mfe: FakeMfe) -> MfeMtfaRunner:
    return MfeMtfaRunner(FakeSystem(mfe), FakeZosApi())


@pytest.mark.unit
def test_mtfa_settings_validate_frequency_and_operand_contract() -> None:
    settings = MfeMtfaSettings(
        frequencies_cyc_per_mm=(0.0, 5.0, 10.0),
        sampling=3,
        wavelength_number=1,
        field_number=1,
        grid=0,
        data_type=0,
    )
    settings.validate()

    with pytest.raises(ValueError, match="strictly increasing"):
        MfeMtfaSettings((0.0, 5.0, 5.0), 3).validate()
    with pytest.raises(ValueError, match="sampling"):
        MfeMtfaSettings((0.0, 5.0), 0).validate()
    with pytest.raises(ValueError, match="Grid"):
        MfeMtfaSettings((0.0, 5.0), 3, grid=2).validate()
    with pytest.raises(ValueError, match="Data Type"):
        MfeMtfaSettings((0.0, 5.0), 3, data_type=4).validate()


@pytest.mark.unit
def test_runner_writes_adjacent_mtfa_operands_calculates_once_and_cleans_up() -> None:
    mfe = FakeMfe([1.0, 0.82, 0.61], baseline_operands=3)
    result = _runner(mfe).run(MfeMtfaSettings((0.0, 5.0, 10.0), sampling=3))

    assert mfe.insert_calls == [4, 5, 6]
    assert mfe.calculate_calls == 1
    assert mfe.remove_calls == [(4, 3)]
    assert mfe.NumberOfOperands == 3
    assert all(operand.changed_types == ["MTFA"] for operand in mfe.created)

    expected_frequencies = (0.0, 5.0, 10.0)
    for operand, frequency in zip(mfe.created, expected_frequencies, strict=True):
        assert operand.cells[2].IntegerValue == 3
        assert operand.cells[3].IntegerValue == 1
        assert operand.cells[4].IntegerValue == 1
        assert operand.cells[5].DoubleValue == frequency
        assert operand.cells[6].IntegerValue == 0
        assert operand.cells[7].IntegerValue == 0

    assert result.frequencies_cyc_per_mm == expected_frequencies
    assert result.mtf_average == pytest.approx((1.0, 0.82, 0.61))


@pytest.mark.unit
def test_runner_accepts_normalized_parameter_header_aliases() -> None:
    mfe = FakeMfe(
        [1.0, 0.8],
        header_override={2: "Sampling", 3: "Wavelength", 5: "Frequency", 7: "Type"},
    )
    result = _runner(mfe).run(MfeMtfaSettings((0.0, 10.0), sampling=2))
    assert result.mtf_average == pytest.approx((1.0, 0.8))
    assert mfe.NumberOfOperands == 2


@pytest.mark.unit
def test_runner_fails_closed_on_unexpected_cell_layout_and_cleans_up() -> None:
    mfe = FakeMfe([1.0], header_override={5: "Mystery"})
    with pytest.raises(MfeMtfaError, match="cell layout"):
        _runner(mfe).run(MfeMtfaSettings((0.0,), sampling=2))
    assert mfe.NumberOfOperands == 2


@pytest.mark.unit
def test_runner_cleans_native_side_effect_when_insert_returns_no_handle() -> None:
    mfe = FakeMfe([1.0], insert_returns_none_after_add=True)
    with pytest.raises(MfeMtfaError, match="returned no operand"):
        _runner(mfe).run(MfeMtfaSettings((0.0,), sampling=2))
    assert mfe.remove_calls == [(3, 1)]
    assert mfe.NumberOfOperands == 2


@pytest.mark.unit
def test_runner_fails_closed_on_calculate_error_and_cleans_up() -> None:
    mfe = FakeMfe([1.0, 0.8], calculate_error=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        _runner(mfe).run(MfeMtfaSettings((0.0, 10.0), sampling=2))
    assert mfe.NumberOfOperands == 2


@pytest.mark.unit
def test_runner_fails_closed_when_cleanup_does_not_restore_mfe() -> None:
    mfe = FakeMfe([1.0], remove_is_broken=True)
    with pytest.raises(MfeMtfaError, match="cleanup left the MFE modified"):
        _runner(mfe).run(MfeMtfaSettings((0.0,), sampling=2))


@pytest.mark.unit
@pytest.mark.parametrize("value", [math.nan, math.inf, -0.1, 1.1])
def test_runner_rejects_invalid_modulation_values(value: float) -> None:
    mfe = FakeMfe([value])
    with pytest.raises((MfeMtfaError, ValueError)):
        _runner(mfe).run(MfeMtfaSettings((0.0,), sampling=2))
    assert mfe.NumberOfOperands == 2
