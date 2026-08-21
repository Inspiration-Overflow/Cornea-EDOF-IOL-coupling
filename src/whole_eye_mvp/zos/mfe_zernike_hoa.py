from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .mfe_zernike import ZERN_CELL_POSITIONS
from .primitives import ZosPrimitiveError


class MfeHoaZernikeError(ZosPrimitiveError):
    pass


@dataclass(frozen=True, slots=True)
class MfeHoaZernikeResult:
    wavelength_um: float
    z11_waves: float
    z22_waves: float
    z37_waves: float

    @property
    def c40_um(self) -> float:
        return self.z11_waves * self.wavelength_um

    @property
    def c60_um(self) -> float:
        return self.z22_waves * self.wavelength_um


@dataclass(slots=True)
class MfeHoaZernikeRunner:
    system: Any
    zosapi: Any
    sampling: int = 1
    wavelength_number: int = 1
    field_number: int = 1

    def run(self) -> MfeHoaZernikeResult:
        if self.sampling != 1 or self.wavelength_number != 1 or self.field_number != 1:
            raise ValueError("TASK-007 HOA ZERN readback is frozen to Samp1/Wave1/Field1")
        mfe = self.system.MFE
        calculate = getattr(mfe, "CalculateMeritFunction", None)
        if not callable(calculate):
            raise MfeHoaZernikeError("installed MFE exposes no CalculateMeritFunction")
        baseline = int(mfe.NumberOfOperands)
        rows = []
        try:
            for offset, term in enumerate((11, 22, 37), start=1):
                operand = mfe.InsertNewOperandAt(baseline + offset)
                if operand is None:
                    raise MfeHoaZernikeError("failed to insert temporary ZERN operand")
                self._configure(operand, term)
                rows.append(operand)
            calculate()
            values = tuple(float(row.Value) for row in rows)
        finally:
            added = int(mfe.NumberOfOperands) - baseline
            if added > 0:
                mfe.RemoveOperandsAt(baseline + 1, added)
        if len(values) != 3 or not all(math.isfinite(value) for value in values):
            raise MfeHoaZernikeError(f"invalid ZERN readback: {values!r}")
        wavelength_um = float(
            self.system.SystemData.Wavelengths.GetWavelength(self.wavelength_number).Wavelength
        )
        return MfeHoaZernikeResult(wavelength_um, values[0], values[1], values[2])

    def _configure(self, operand: Any, term: int) -> None:
        zern = getattr(self.zosapi.Editors.MFE.MeritOperandType, "ZERN", None)
        if zern is None:
            raise MfeHoaZernikeError("installed MeritOperandType exposes no ZERN member")
        operand.ChangeType(zern)
        values = {
            "term": term,
            "wave": self.wavelength_number,
            "samp": self.sampling,
            "field": self.field_number,
            "type": 1,
            "epsilon": 0.0,
            "vertex": 0,
        }
        for name, (position, expected_header) in ZERN_CELL_POSITIONS.items():
            cell = operand.GetCellAt(position)
            header = str(getattr(cell, "Header", "") or "").strip()
            if header != expected_header:
                raise MfeHoaZernikeError(
                    f"unexpected ZERN cell layout at {position}: {header!r}"
                )
            value = values[name]
            try:
                cell.IntegerValue = value
            except Exception:  # noqa: BLE001 - numeric cells expose mixed setters
                cell.DoubleValue = float(value)
