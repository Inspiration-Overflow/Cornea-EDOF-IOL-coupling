from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .primitives import ZosPrimitiveError


class MfeEfflError(ZosPrimitiveError):
    pass


@dataclass(frozen=True, slots=True)
class MfeEfflResult:
    effective_focal_length_mm: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.effective_focal_length_mm) or self.effective_focal_length_mm <= 0:
            raise ValueError("effective focal length must be finite and positive")


@dataclass(slots=True)
class MfeEfflRunner:
    system: Any
    zosapi: Any

    def run(self) -> MfeEfflResult:
        mfe = self.system.MFE
        calculate = getattr(mfe, "CalculateMeritFunction", None)
        insert = getattr(mfe, "InsertNewOperandAt", None)
        remove = getattr(mfe, "RemoveOperandsAt", None)
        if not callable(calculate) or not callable(insert) or not callable(remove):
            raise MfeEfflError("installed MFE lacks temporary operand lifecycle methods")

        baseline_count = int(mfe.NumberOfOperands)
        operand = insert(baseline_count + 1)
        if operand is None:
            raise MfeEfflError("failed to insert temporary EFFL operand")
        try:
            enum_type = self.zosapi.Editors.MFE.MeritOperandType
            effl = getattr(enum_type, "EFFL", None)
            if effl is None:
                raise MfeEfflError("installed MeritOperandType exposes no EFFL member")
            operand.ChangeType(effl)
            calculate()
            value = float(operand.Value)
        except MfeEfflError:
            raise
        except Exception as exc:
            raise MfeEfflError("failed to evaluate temporary EFFL operand") from exc
        finally:
            added = int(mfe.NumberOfOperands) - baseline_count
            if added == 1:
                remove(baseline_count + 1, 1)
            elif added != 0:
                raise MfeEfflError(f"unexpected temporary EFFL operand count: {added}")
        if int(mfe.NumberOfOperands) != baseline_count:
            raise MfeEfflError("temporary EFFL cleanup left the MFE modified")
        if not math.isfinite(value) or value <= 0:
            raise MfeEfflError(f"MFE EFFL returned invalid focal length: {value}")
        return MfeEfflResult(value)
