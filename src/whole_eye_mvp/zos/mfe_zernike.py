"""MFE ``ZERN`` Standard-Zernike acquisition primitive.

TASK-005C production C40 acquisition contract (see
``docs/TASK_005C_MFE_ZERN_ACQUISITION_CONTRACT_2026-08-18.md``): evaluate two
adjacent temporary ``ZERN`` operands (Term 11 and Term 37) in the Merit
Function Editor instead of creating a Zernike Standard analysis object, whose
settings type triggered a Python.NET/ZemaxEngine load failure on the
OpticStudio 2026 R1 workstation.

The frozen parameter mapping verified on 2026 R1::

    Term=11 + Term=37 adjacent, Wave=1, Samp=1 (32x32), Field=1,
    Type=1 (Standard), Epsilon=0, Vertex=0 (chief-ray OPD reference)

Temporary operands are removed again after the acquisition and the lens is
never saved by this module; callers are responsible for never persisting a
system that carried temporary operands.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .primitives import ZosPrimitiveError

# Verified 2026 R1 ZERN parameter cells. GetCellAt(1) is the operand type
# column, so parameters occupy positions 2..8. The installed OpticStudio
# labels the eighth column "Vertex?".
ZERN_CELL_POSITIONS: dict[str, tuple[int, str]] = {
    "term": (2, "Term"),
    "wave": (3, "Wave"),
    "samp": (4, "Samp"),
    "field": (5, "Field"),
    "type": (6, "Type"),
    "epsilon": (7, "Epsilon"),
    "vertex": (8, "Vertex?"),
}


class MfeZernikeError(ZosPrimitiveError):
    """The MFE ZERN operands or their results violate the acquisition contract."""


@dataclass(frozen=True, slots=True)
class MfeZernikeStandardSettings:
    """Frozen TASK-005C MFE ZERN acquisition settings."""

    term_primary: int = 11
    term_maximum: int = 37
    wavelength_number: int = 1
    field_number: int = 1
    sampling: int = 1
    zernike_type: int = 1
    epsilon: float = 0.0
    vertex: int = 0

    def validate(self) -> None:
        if self.term_primary < 11:
            raise ValueError("Standard Zernike fit requires term_primary >= 11")
        if self.term_maximum < self.term_primary:
            raise ValueError("term_maximum must be at least term_primary")
        if self.wavelength_number < 1 or self.field_number < 1:
            raise ValueError("wavelength_number and field_number are 1-based")
        if self.sampling < 1:
            raise ValueError("sampling must select a valid pupil grid (1 = 32x32)")
        if self.zernike_type != 1:
            raise ValueError("only the verified Standard Zernike type (1) is supported")
        if not math.isfinite(self.epsilon) or not 0.0 <= self.epsilon < 1.0:
            raise ValueError("epsilon must lie in [0, 1)")
        if self.vertex not in (0, 1):
            raise ValueError("vertex reference must be 0 (chief ray) or 1")


@dataclass(frozen=True, slots=True)
class MfeZernikeResult:
    wavelength_um: float
    z11_waves: float
    z37_waves: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.wavelength_um) or self.wavelength_um <= 0:
            raise ValueError("acquisition wavelength must be finite and positive")
        if not math.isfinite(self.z11_waves) or not math.isfinite(self.z37_waves):
            raise ValueError("Zernike coefficients must be finite")

    @property
    def c40_um(self) -> float:
        return self.z11_waves * self.wavelength_um


@dataclass(slots=True)
class MfeZernikeStandardRunner:
    """Acquire Z11/Z37 through two adjacent temporary MFE ZERN operands."""

    system: Any
    zosapi: Any

    def run(self, settings: MfeZernikeStandardSettings) -> MfeZernikeResult:
        settings.validate()
        mfe = self.system.MFE
        calculate = getattr(mfe, "CalculateMeritFunction", None)
        if not callable(calculate):
            raise MfeZernikeError("installed MFE exposes no CalculateMeritFunction")
        baseline_count = int(mfe.NumberOfOperands)

        try:
            row11 = self._insert_temporary_operand(mfe, baseline_count + 1)
            row37 = self._insert_temporary_operand(mfe, baseline_count + 2)
        except Exception:
            self._remove_temporary_operands(mfe, baseline_count)
            raise

        try:
            self._configure_operand(row11, settings, settings.term_primary)
            self._configure_operand(row37, settings, settings.term_maximum)
            calculate()
            z11 = self._read_operand_value(row11)
            z37 = self._read_operand_value(row37)
        finally:
            self._remove_temporary_operands(mfe, baseline_count)

        if not math.isfinite(z11) or not math.isfinite(z37):
            raise MfeZernikeError(
                f"MFE ZERN returned non-finite coefficients: Z11={z11}, Z37={z37}"
            )
        wavelength = self.system.SystemData.Wavelengths.GetWavelength(
            settings.wavelength_number
        )
        wavelength_um = float(wavelength.Wavelength)
        if not math.isfinite(wavelength_um) or wavelength_um <= 0:
            raise MfeZernikeError(f"invalid acquisition wavelength: {wavelength_um}")
        return MfeZernikeResult(
            wavelength_um=wavelength_um,
            z11_waves=z11,
            z37_waves=z37,
        )

    @staticmethod
    def _insert_temporary_operand(mfe: Any, row: int) -> Any:
        insert = getattr(mfe, "InsertNewOperandAt", None)
        if not callable(insert):
            raise MfeZernikeError("installed MFE exposes no InsertNewOperandAt")
        try:
            operand = insert(row)
        except Exception as exc:
            raise MfeZernikeError(
                f"failed to insert temporary ZERN operand at row {row}"
            ) from exc
        if operand is None:
            raise MfeZernikeError(f"InsertNewOperandAt({row}) returned no operand")
        return operand

    @staticmethod
    def _remove_temporary_operands(mfe: Any, baseline_count: int) -> None:
        added = int(mfe.NumberOfOperands) - baseline_count
        if added <= 0:
            return
        if added > 2:
            raise MfeZernikeError(f"unexpected temporary operand count: {added}")
        remove = getattr(mfe, "RemoveOperandsAt", None)
        if not callable(remove):
            raise MfeZernikeError("installed MFE exposes no RemoveOperandsAt")
        try:
            remove(baseline_count + 1, added)
        except Exception as exc:
            raise MfeZernikeError("failed to remove temporary ZERN operands") from exc
        if int(mfe.NumberOfOperands) != baseline_count:
            raise MfeZernikeError("temporary ZERN operand cleanup left the MFE modified")

    def _change_to_zern(self, operand: Any) -> None:
        enum_type = self.zosapi.Editors.MFE.MeritOperandType
        zern = getattr(enum_type, "ZERN", None)
        if zern is None:
            raise MfeZernikeError("installed MeritOperandType exposes no ZERN member")
        try:
            operand.ChangeType(zern)
        except Exception as exc:
            raise MfeZernikeError("failed to change MFE operand type to ZERN") from exc

    def _configure_operand(
        self,
        operand: Any,
        settings: MfeZernikeStandardSettings,
        term: int,
    ) -> None:
        self._change_to_zern(operand)
        values = {
            "term": term,
            "wave": settings.wavelength_number,
            "samp": settings.sampling,
            "field": settings.field_number,
            "type": settings.zernike_type,
            "epsilon": settings.epsilon,
            "vertex": settings.vertex,
        }
        cells: dict[str, Any] = {}
        for name, (position, expected_header) in ZERN_CELL_POSITIONS.items():
            cell = operand.GetCellAt(position)
            header = str(getattr(cell, "Header", "") or "").strip()
            if header != expected_header:
                raise MfeZernikeError(
                    f"unexpected ZERN cell layout at position {position}: "
                    f"expected {expected_header!r}, received {header!r}"
                )
            cells[name] = cell
        for name, cell in cells.items():
            value = values[name]
            try:
                cell.IntegerValue = value
            except Exception:  # noqa: BLE001 - numeric cells accept either setter
                cell.DoubleValue = float(value)

    @staticmethod
    def _read_operand_value(operand: Any) -> float:
        try:
            return float(operand.Value)
        except Exception as exc:
            raise MfeZernikeError("failed to read the ZERN operand value") from exc
