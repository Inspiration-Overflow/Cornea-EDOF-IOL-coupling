from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .mfe_zernike import ZERN_CELL_POSITIONS
from .primitives import ZosPrimitiveError


class MfeFullHoaError(ZosPrimitiveError):
    pass


@dataclass(frozen=True, slots=True)
class MfeFullHoaResult:
    wavelength_um: float
    coefficients_waves: tuple[tuple[int, float], ...]

    def coefficient_waves(self, term: int) -> float:
        try:
            return dict(self.coefficients_waves)[term]
        except KeyError as exc:
            raise KeyError(f"missing Zernike term Z{term}") from exc

    @property
    def c40_um(self) -> float:
        return self.coefficient_waves(11) * self.wavelength_um

    @property
    def c60_um(self) -> float:
        return self.coefficient_waves(22) * self.wavelength_um

    @property
    def hoa_rms_um(self) -> float:
        return self.wavelength_um * math.sqrt(
            math.fsum(self.coefficient_waves(term) ** 2 for term in range(7, 29))
        )


@dataclass(slots=True)
class MfeFullHoaRunner:
    system: Any
    zosapi: Any
    sampling: int = 1
    wavelength_number: int = 1
    field_number: int = 1

    def run(self) -> MfeFullHoaResult:
        if self.sampling != 1 or self.wavelength_number != 1 or self.field_number != 1:
            raise ValueError("TASK-009 HOA readback is frozen to Samp1/Wave1/Field1")
        mfe = self.system.MFE
        calculate = getattr(mfe, "CalculateMeritFunction", None)
        if not callable(calculate):
            raise MfeFullHoaError("installed MFE exposes no CalculateMeritFunction")
        baseline = int(mfe.NumberOfOperands)
        operands: list[tuple[int, Any]] = []
        try:
            for offset, term in enumerate(range(7, 29), start=1):
                operand = mfe.InsertNewOperandAt(baseline + offset)
                if operand is None:
                    raise MfeFullHoaError("failed to insert temporary ZERN operand")
                self._configure(operand, term)
                operands.append((term, operand))
            calculate()
            coefficients = tuple((term, float(operand.Value)) for term, operand in operands)
        finally:
            added = int(mfe.NumberOfOperands) - baseline
            if added > 0:
                mfe.RemoveOperandsAt(baseline + 1, added)
        if len(coefficients) != 22 or not all(math.isfinite(value) for _, value in coefficients):
            raise MfeFullHoaError(f"invalid full-HOA ZERN readback: {coefficients!r}")
        wavelength_um = float(
            self.system.SystemData.Wavelengths.GetWavelength(self.wavelength_number).Wavelength
        )
        if not math.isfinite(wavelength_um) or wavelength_um <= 0:
            raise MfeFullHoaError("invalid analysis wavelength")
        return MfeFullHoaResult(wavelength_um, coefficients)

    def _configure(self, operand: Any, term: int) -> None:
        zern = getattr(self.zosapi.Editors.MFE.MeritOperandType, "ZERN", None)
        if zern is None:
            raise MfeFullHoaError("installed MeritOperandType exposes no ZERN member")
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
                raise MfeFullHoaError(
                    f"unexpected ZERN cell layout at {position}: {header!r}"
                )
            value = values[name]
            try:
                cell.IntegerValue = value
            except Exception:  # noqa: BLE001 - numeric cells expose mixed setters
                cell.DoubleValue = float(value)
