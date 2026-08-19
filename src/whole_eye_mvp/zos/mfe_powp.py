"""MFE ``POWP`` pupil-point power acquisition primitive for TASK-007.

The production use is deliberately narrow: on-axis field, pupil center, spherical
power, evaluated immediately after the IOL posterior surface.  The operand is
inserted temporarily, evaluated, and removed again so lens files are never saved
with diagnostic Merit Function rows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .primitives import ZosPrimitiveError


class MfePowpError(ZosPrimitiveError):
    pass


@dataclass(frozen=True, slots=True)
class MfePowpSettings:
    surface: int
    wavelength_number: int = 1
    hx: float = 0.0
    hy: float = 0.0
    px: float = 0.0
    py: float = 0.0
    data: int = 0

    def validate(self) -> None:
        if self.surface < 1:
            raise ValueError("POWP surface must be positive")
        if self.wavelength_number < 1:
            raise ValueError("POWP wavelength number must be positive")
        if not all(math.isfinite(float(v)) and -1.0 <= float(v) <= 1.0 for v in (self.hx, self.hy, self.px, self.py)):
            raise ValueError("POWP normalized field/pupil coordinates must lie in [-1, 1]")
        if self.data != 0:
            raise ValueError("TASK-007 POWP Data is frozen to spherical power (0)")


@dataclass(frozen=True, slots=True)
class MfePowpResult:
    power_d: float
    parameter_headers: tuple[tuple[int, str], ...]

    def __post_init__(self) -> None:
        if not math.isfinite(self.power_d):
            raise ValueError("POWP power must be finite")


@dataclass(slots=True)
class MfePowpRunner:
    system: Any
    zosapi: Any

    def run(self, settings: MfePowpSettings) -> MfePowpResult:
        settings.validate()
        mfe = self.system.MFE
        calculate = getattr(mfe, "CalculateMeritFunction", None)
        if not callable(calculate):
            raise MfePowpError("installed MFE exposes no CalculateMeritFunction")
        baseline_count = int(mfe.NumberOfOperands)
        operand = self._insert_temporary_operand(mfe, baseline_count + 1)
        try:
            self._change_to_powp(operand)
            headers = self._parameter_headers(operand)
            cells = self._resolve_cells(operand, headers)
            values = {
                "Surf": settings.surface,
                "Wave": settings.wavelength_number,
                "Hx": settings.hx,
                "Hy": settings.hy,
                "Px": settings.px,
                "Py": settings.py,
                "Data": settings.data,
            }
            for name, value in values.items():
                cell = cells[name]
                try:
                    cell.IntegerValue = value
                except Exception:  # noqa: BLE001 - numeric operand cells expose mixed setters
                    cell.DoubleValue = float(value)
            calculate()
            try:
                result = float(operand.Value)
            except Exception as exc:
                raise MfePowpError("failed to read POWP operand value") from exc
        finally:
            self._remove_temporary_operand(mfe, baseline_count)
        if not math.isfinite(result):
            raise MfePowpError(f"MFE POWP returned non-finite power: {result}")
        return MfePowpResult(power_d=result, parameter_headers=headers)

    @staticmethod
    def _insert_temporary_operand(mfe: Any, row: int) -> Any:
        insert = getattr(mfe, "InsertNewOperandAt", None)
        if not callable(insert):
            raise MfePowpError("installed MFE exposes no InsertNewOperandAt")
        operand = insert(row)
        if operand is None:
            raise MfePowpError(f"InsertNewOperandAt({row}) returned no operand")
        return operand

    @staticmethod
    def _remove_temporary_operand(mfe: Any, baseline_count: int) -> None:
        added = int(mfe.NumberOfOperands) - baseline_count
        if added <= 0:
            return
        if added != 1:
            raise MfePowpError(f"unexpected temporary POWP operand count: {added}")
        remove = getattr(mfe, "RemoveOperandsAt", None)
        if not callable(remove):
            raise MfePowpError("installed MFE exposes no RemoveOperandsAt")
        remove(baseline_count + 1, 1)
        if int(mfe.NumberOfOperands) != baseline_count:
            raise MfePowpError("temporary POWP cleanup left the MFE modified")

    def _change_to_powp(self, operand: Any) -> None:
        enum_type = self.zosapi.Editors.MFE.MeritOperandType
        powp = getattr(enum_type, "POWP", None)
        if powp is None:
            raise MfePowpError("installed MeritOperandType exposes no POWP member")
        try:
            operand.ChangeType(powp)
        except Exception as exc:
            raise MfePowpError("failed to change MFE operand type to POWP") from exc

    @staticmethod
    def _parameter_headers(operand: Any) -> tuple[tuple[int, str], ...]:
        headers: list[tuple[int, str]] = []
        for position in range(2, 17):
            try:
                cell = operand.GetCellAt(position)
            except Exception:  # noqa: BLE001 - probe until the installed row ends
                break
            header = str(getattr(cell, "Header", "") or "").strip()
            if header:
                headers.append((position, header))
        return tuple(headers)

    @staticmethod
    def _resolve_cells(operand: Any, headers: tuple[tuple[int, str], ...]) -> dict[str, Any]:
        expected = {"Surf", "Wave", "Hx", "Hy", "Px", "Py", "Data"}
        positions = {header: position for position, header in headers if header in expected}
        missing = expected - set(positions)
        if missing:
            raise MfePowpError(
                "installed POWP cell layout is missing required headers: " + ", ".join(sorted(missing))
            )
        return {name: operand.GetCellAt(positions[name]) for name in expected}
