"""Grid-based diffraction-MTF acquisition through temporary MFE operands.

TASK-009 uses MTFA/MTFS/MTFT with ``Grid=1``. OpticStudio documents that
``Grid=1`` selects the grid-based algorithm used by the MTF analysis feature,
while avoiding the Python.NET ``AS_FftMtf`` analysis-settings type that is not
loadable on the validated 2026 R1 workstation.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from .primitives import ZosPrimitiveError

_CELL_POSITIONS = tuple(range(2, 8))
_HEADER_TOKEN = re.compile(r"[^a-z0-9]+")
_ALLOWED_OPERANDS = frozenset({"MTFA", "MTFS", "MTFT"})
_HEADER_ALIASES: dict[str, frozenset[str]] = {
    "sampling": frozenset({"samp", "sampling"}),
    "wave": frozenset({"wave", "wavelength"}),
    "field": frozenset({"field"}),
    "frequency": frozenset({"freq", "frequency"}),
    "grid": frozenset({"grid"}),
    "data_type": frozenset({"datatype", "type"}),
}


class MfeMtfGridError(ZosPrimitiveError):
    """The grid-based MTF operands or returned values violate the contract."""


def sampling_index_for_grid_size(grid_size: int) -> int:
    """Map OpticStudio pupil grid size to the MTF operand ``Samp`` index.

    OpticStudio's sampling convention is 1=32, 2=64, 3=128, 4=256, ... .
    """

    if not isinstance(grid_size, int) or grid_size < 32 or grid_size & (grid_size - 1):
        raise ValueError("MTF grid size must be a power of two >=32")
    index = int(math.log2(grid_size)) - 4
    if index < 1:
        raise ValueError("MTF sampling index must be positive")
    return index


def _normalize_header(value: object) -> str:
    return _HEADER_TOKEN.sub("", str(value or "").strip().lower())


@dataclass(frozen=True, slots=True)
class MfeMtfGridSettings:
    frequencies_cyc_per_mm: tuple[float, ...]
    sampling_grid_size: int
    operand_type: str = "MTFA"
    wavelength_number: int = 1
    field_number: int = 1
    grid: int = 1
    data_type: int = 0

    @property
    def sampling_index(self) -> int:
        return sampling_index_for_grid_size(self.sampling_grid_size)

    def validate(self) -> None:
        if not self.frequencies_cyc_per_mm:
            raise ValueError("MTF frequency grid must not be empty")
        frequencies = tuple(float(value) for value in self.frequencies_cyc_per_mm)
        if not all(math.isfinite(value) and value >= 0 for value in frequencies):
            raise ValueError("MTF frequencies must be finite and non-negative")
        if any(right <= left for left, right in pairwise(frequencies)):
            raise ValueError("MTF frequencies must be strictly increasing")
        sampling_index_for_grid_size(self.sampling_grid_size)
        if self.operand_type not in _ALLOWED_OPERANDS:
            raise ValueError(f"unsupported grid-based MTF operand: {self.operand_type}")
        if self.wavelength_number < 1 or self.field_number < 1:
            raise ValueError("MTF wavelength/field numbers are 1-based")
        if self.grid != 1:
            raise ValueError("TASK-009 production grid-based MTF requires Grid=1")
        if self.data_type != 0:
            raise ValueError("TASK-009 production grid-based MTF requires modulation Data Type=0")


@dataclass(frozen=True, slots=True)
class MfeMtfGridResult:
    frequencies_cyc_per_mm: tuple[float, ...]
    values: tuple[float, ...]
    operand_type: str
    sampling_grid_size: int
    sampling_index: int
    grid: int
    data_type: int
    parameter_headers: tuple[tuple[int, str], ...]

    def __post_init__(self) -> None:
        if len(self.frequencies_cyc_per_mm) != len(self.values):
            raise ValueError("MTF frequency/value lengths differ")
        if not self.frequencies_cyc_per_mm:
            raise ValueError("MTF result must not be empty")
        if not all(
            math.isfinite(float(value))
            for value in (*self.frequencies_cyc_per_mm, *self.values)
        ):
            raise ValueError("MTF result contains non-finite values")


@dataclass(slots=True)
class MfeMtfGridRunner:
    """Evaluate adjacent temporary MTFA/MTFS/MTFT operands and restore the MFE."""

    system: Any
    zosapi: Any

    def run(self, settings: MfeMtfGridSettings) -> MfeMtfGridResult:
        settings.validate()
        mfe = self.system.MFE
        calculate = getattr(mfe, "CalculateMeritFunction", None)
        if not callable(calculate):
            raise MfeMtfGridError("installed MFE exposes no CalculateMeritFunction")
        baseline_count = int(mfe.NumberOfOperands)
        maximum_added = len(settings.frequencies_cyc_per_mm)
        operands: list[Any] = []
        headers: tuple[tuple[int, str], ...] | None = None
        try:
            for offset, frequency in enumerate(settings.frequencies_cyc_per_mm, start=1):
                operand = self._insert_temporary_operand(mfe, baseline_count + offset)
                operands.append(operand)
                current_headers = self._configure_operand(operand, settings, float(frequency))
                if headers is None:
                    headers = current_headers
                elif current_headers != headers:
                    raise MfeMtfGridError("MTF operand parameter headers changed within one batch")
            calculate()
            values = tuple(self._read_operand_value(operand) for operand in operands)
        finally:
            self._remove_temporary_operands(mfe, baseline_count, maximum_added)

        if headers is None:
            raise MfeMtfGridError("MTF operand batch produced no parameter headers")
        if any(value < -1.0e-9 or value > 1.01 for value in values):
            raise MfeMtfGridError(f"MTF modulation lies outside expected [0, 1]: {values!r}")
        return MfeMtfGridResult(
            frequencies_cyc_per_mm=tuple(float(value) for value in settings.frequencies_cyc_per_mm),
            values=values,
            operand_type=settings.operand_type,
            sampling_grid_size=settings.sampling_grid_size,
            sampling_index=settings.sampling_index,
            grid=settings.grid,
            data_type=settings.data_type,
            parameter_headers=headers,
        )

    @staticmethod
    def _insert_temporary_operand(mfe: Any, row: int) -> Any:
        insert = getattr(mfe, "InsertNewOperandAt", None)
        if not callable(insert):
            raise MfeMtfGridError("installed MFE exposes no InsertNewOperandAt")
        try:
            operand = insert(row)
        except Exception as exc:
            raise MfeMtfGridError(f"failed to insert temporary MTF operand at row {row}") from exc
        if operand is None:
            raise MfeMtfGridError(f"InsertNewOperandAt({row}) returned no operand")
        return operand

    @staticmethod
    def _remove_temporary_operands(mfe: Any, baseline_count: int, maximum_added: int) -> None:
        added = int(mfe.NumberOfOperands) - baseline_count
        if added <= 0:
            return
        if added > maximum_added:
            raise MfeMtfGridError(
                f"unexpected temporary MTF operand count: expected <= {maximum_added}, got {added}"
            )
        remove = getattr(mfe, "RemoveOperandsAt", None)
        if not callable(remove):
            raise MfeMtfGridError("installed MFE exposes no RemoveOperandsAt")
        try:
            remove(baseline_count + 1, added)
        except Exception as exc:
            raise MfeMtfGridError("failed to remove temporary MTF operands") from exc
        if int(mfe.NumberOfOperands) != baseline_count:
            raise MfeMtfGridError("temporary MTF operand cleanup left the MFE modified")

    def _change_type(self, operand: Any, operand_type: str) -> None:
        enum_type = self.zosapi.Editors.MFE.MeritOperandType
        target = getattr(enum_type, operand_type, None)
        if target is None:
            raise MfeMtfGridError(
                f"installed MeritOperandType exposes no {operand_type} member"
            )
        try:
            operand.ChangeType(target)
        except Exception as exc:
            raise MfeMtfGridError(f"failed to change MFE operand type to {operand_type}") from exc

    @staticmethod
    def _cell_map(operand: Any) -> tuple[dict[str, Any], tuple[tuple[int, str], ...]]:
        by_header: dict[str, Any] = {}
        seen_headers: list[tuple[int, str]] = []
        for position in _CELL_POSITIONS:
            cell = operand.GetCellAt(position)
            header = str(getattr(cell, "Header", "") or "").strip()
            seen_headers.append((position, header))
            normalized = _normalize_header(header)
            for semantic, aliases in _HEADER_ALIASES.items():
                if normalized in aliases:
                    if semantic in by_header:
                        raise MfeMtfGridError(
                            f"duplicate MTF parameter header for {semantic!r}: {seen_headers!r}"
                        )
                    by_header[semantic] = cell
                    break
        missing = tuple(name for name in _HEADER_ALIASES if name not in by_header)
        if missing:
            raise MfeMtfGridError(
                f"unexpected MTF cell layout; missing {missing!r}, headers={seen_headers!r}"
            )
        return by_header, tuple(seen_headers)

    def _configure_operand(
        self,
        operand: Any,
        settings: MfeMtfGridSettings,
        frequency: float,
    ) -> tuple[tuple[int, str], ...]:
        self._change_type(operand, settings.operand_type)
        cells, headers = self._cell_map(operand)
        self._set_integer(cells["sampling"], settings.sampling_index)
        self._set_integer(cells["wave"], settings.wavelength_number)
        self._set_integer(cells["field"], settings.field_number)
        self._set_double(cells["frequency"], frequency)
        self._set_integer(cells["grid"], settings.grid)
        self._set_integer(cells["data_type"], settings.data_type)
        return headers

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
            raise MfeMtfGridError("failed to read MTF operand value") from exc
