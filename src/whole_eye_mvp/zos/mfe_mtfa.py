"""Temporary MFE ``MTFA`` diffraction-MTF acquisition primitive.

TASK-005D B0 production uses OpticStudio's Merit Function Editor ``MTFA``
operand with ``Grid=0`` instead of creating FFT/Huygens analysis settings
objects.  A set of adjacent temporary operands is inserted, evaluated by one
``CalculateMeritFunction()`` call, read, and removed again without saving the
lens.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from .primitives import ZosPrimitiveError

_MTFA_CELL_POSITIONS = tuple(range(2, 8))
_HEADER_TOKEN = re.compile(r"[^a-z0-9]+")


class MfeMtfaError(ZosPrimitiveError):
    """The MFE MTFA operands or returned values violate the acquisition contract."""


def _normalize_header(value: object) -> str:
    return _HEADER_TOKEN.sub("", str(value or "").strip().lower())


_HEADER_ALIASES: dict[str, frozenset[str]] = {
    "sampling": frozenset({"samp", "sampling"}),
    "wave": frozenset({"wave", "wavelength"}),
    "field": frozenset({"field"}),
    "frequency": frozenset({"freq", "frequency"}),
    "grid": frozenset({"grid"}),
    "data_type": frozenset({"datatype", "type"}),
}


@dataclass(frozen=True, slots=True)
class MfeMtfaSettings:
    """Settings shared by one adjacent batch of MTFA operands."""

    frequencies_cyc_per_mm: tuple[float, ...]
    sampling: int
    wavelength_number: int = 1
    field_number: int = 1
    grid: int = 0
    data_type: int = 0

    def validate(self) -> None:
        if not self.frequencies_cyc_per_mm:
            raise ValueError("MTFA frequency grid must not be empty")
        frequencies = tuple(float(value) for value in self.frequencies_cyc_per_mm)
        if not all(math.isfinite(value) and value >= 0 for value in frequencies):
            raise ValueError("MTFA frequencies must be finite and non-negative")
        if any(right <= left for left, right in zip(frequencies, frequencies[1:])):
            raise ValueError("MTFA frequencies must be strictly increasing")
        if self.sampling < 1:
            raise ValueError("MTFA sampling index must be positive")
        if self.wavelength_number < 1 or self.field_number < 1:
            raise ValueError("MTFA wavelength/field numbers are 1-based")
        if self.grid not in (0, 1):
            raise ValueError("MTFA Grid must be 0 or 1")
        if self.data_type not in (0, 1, 2, 3):
            raise ValueError("MTFA Data Type must be 0, 1, 2, or 3")


@dataclass(frozen=True, slots=True)
class MfeMtfaResult:
    frequencies_cyc_per_mm: tuple[float, ...]
    mtf_average: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.frequencies_cyc_per_mm) != len(self.mtf_average):
            raise ValueError("MTFA frequency/value lengths differ")
        if not self.frequencies_cyc_per_mm:
            raise ValueError("MTFA result must not be empty")
        values = (*self.frequencies_cyc_per_mm, *self.mtf_average)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("MTFA result contains non-finite values")


@dataclass(slots=True)
class MfeMtfaRunner:
    """Evaluate adjacent temporary MTFA operands and restore the MFE exactly."""

    system: Any
    zosapi: Any

    def run(self, settings: MfeMtfaSettings) -> MfeMtfaResult:
        settings.validate()
        mfe = self.system.MFE
        calculate = getattr(mfe, "CalculateMeritFunction", None)
        if not callable(calculate):
            raise MfeMtfaError("installed MFE exposes no CalculateMeritFunction")
        baseline_count = int(mfe.NumberOfOperands)
        operands: list[Any] = []
        try:
            for offset, frequency in enumerate(settings.frequencies_cyc_per_mm, start=1):
                operand = self._insert_temporary_operand(mfe, baseline_count + offset)
                operands.append(operand)
                self._configure_operand(operand, settings, float(frequency))
            calculate()
            values = tuple(self._read_operand_value(operand) for operand in operands)
        finally:
            self._remove_temporary_operands(mfe, baseline_count, len(operands))

        if not all(math.isfinite(value) for value in values):
            raise MfeMtfaError(f"MFE MTFA returned non-finite values: {values!r}")
        if settings.data_type == 0 and any(value < -1.0e-9 or value > 1.01 for value in values):
            raise MfeMtfaError(f"MFE MTFA modulation lies outside expected [0, 1]: {values!r}")
        return MfeMtfaResult(
            frequencies_cyc_per_mm=tuple(float(value) for value in settings.frequencies_cyc_per_mm),
            mtf_average=values,
        )

    @staticmethod
    def _insert_temporary_operand(mfe: Any, row: int) -> Any:
        insert = getattr(mfe, "InsertNewOperandAt", None)
        if not callable(insert):
            raise MfeMtfaError("installed MFE exposes no InsertNewOperandAt")
        try:
            operand = insert(row)
        except Exception as exc:
            raise MfeMtfaError(f"failed to insert temporary MTFA operand at row {row}") from exc
        if operand is None:
            raise MfeMtfaError(f"InsertNewOperandAt({row}) returned no operand")
        return operand

    @staticmethod
    def _remove_temporary_operands(mfe: Any, baseline_count: int, expected_added: int) -> None:
        added = int(mfe.NumberOfOperands) - baseline_count
        if added <= 0:
            return
        if added > expected_added:
            raise MfeMtfaError(
                f"unexpected temporary MTFA operand count: expected <= {expected_added}, got {added}"
            )
        remove = getattr(mfe, "RemoveOperandsAt", None)
        if not callable(remove):
            raise MfeMtfaError("installed MFE exposes no RemoveOperandsAt")
        try:
            remove(baseline_count + 1, added)
        except Exception as exc:
            raise MfeMtfaError("failed to remove temporary MTFA operands") from exc
        if int(mfe.NumberOfOperands) != baseline_count:
            raise MfeMtfaError("temporary MTFA operand cleanup left the MFE modified")

    def _change_to_mtfa(self, operand: Any) -> None:
        enum_type = self.zosapi.Editors.MFE.MeritOperandType
        mtfa = getattr(enum_type, "MTFA", None)
        if mtfa is None:
            raise MfeMtfaError("installed MeritOperandType exposes no MTFA member")
        try:
            operand.ChangeType(mtfa)
        except Exception as exc:
            raise MfeMtfaError("failed to change MFE operand type to MTFA") from exc

    @staticmethod
    def _cell_map(operand: Any) -> dict[str, Any]:
        by_header: dict[str, Any] = {}
        seen_headers: dict[int, str] = {}
        for position in _MTFA_CELL_POSITIONS:
            cell = operand.GetCellAt(position)
            header = str(getattr(cell, "Header", "") or "").strip()
            normalized = _normalize_header(header)
            seen_headers[position] = header
            for semantic, aliases in _HEADER_ALIASES.items():
                if normalized in aliases:
                    if semantic in by_header:
                        raise MfeMtfaError(
                            f"duplicate MTFA parameter header for {semantic!r}: {seen_headers!r}"
                        )
                    by_header[semantic] = cell
                    break
        missing = tuple(name for name in _HEADER_ALIASES if name not in by_header)
        if missing:
            raise MfeMtfaError(
                f"unexpected MTFA cell layout; missing {missing!r}, headers={seen_headers!r}"
            )
        return by_header

    def _configure_operand(
        self,
        operand: Any,
        settings: MfeMtfaSettings,
        frequency: float,
    ) -> None:
        self._change_to_mtfa(operand)
        cells = self._cell_map(operand)
        self._set_integer(cells["sampling"], settings.sampling)
        self._set_integer(cells["wave"], settings.wavelength_number)
        self._set_integer(cells["field"], settings.field_number)
        self._set_double(cells["frequency"], frequency)
        self._set_integer(cells["grid"], settings.grid)
        self._set_integer(cells["data_type"], settings.data_type)

    @staticmethod
    def _set_integer(cell: Any, value: int) -> None:
        try:
            cell.IntegerValue = int(value)
        except Exception:  # noqa: BLE001 - numeric cells can expose only DoubleValue
            cell.DoubleValue = float(value)

    @staticmethod
    def _set_double(cell: Any, value: float) -> None:
        try:
            cell.DoubleValue = float(value)
        except Exception:  # noqa: BLE001 - numeric cells can expose only IntegerValue
            cell.IntegerValue = int(value)

    @staticmethod
    def _read_operand_value(operand: Any) -> float:
        try:
            return float(operand.Value)
        except Exception as exc:
            raise MfeMtfaError("failed to read MTFA operand value") from exc
