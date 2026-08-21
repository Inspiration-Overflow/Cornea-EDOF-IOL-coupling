from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any

from .mfe_zernike import ZERN_CELL_POSITIONS
from .primitives import ZosPrimitiveError


class MfeFullHoaError(ZosPrimitiveError):
    pass


@dataclass(frozen=True, slots=True)
class MfeFullHoaSettings:
    """Versioned MFE ZERN contract used by TASK-009/Run72 aberration readback."""

    settings_id: str = "TASK009_MFE_ZERN_HOA_555_v1"
    sampling: int = 1
    wavelength_number: int = 1
    field_number: int = 1
    zernike_type: int = 1
    epsilon: float = 0.0
    vertex: int = 0
    term_start: int = 7
    term_stop: int = 28

    def validate(self) -> None:
        if not self.settings_id.strip():
            raise ValueError("HOA ZERN settings ID is required")
        if (
            self.sampling != 1
            or self.wavelength_number != 1
            or self.field_number != 1
            or self.zernike_type != 1
            or self.epsilon != 0.0
            or self.vertex != 0
            or self.term_start != 7
            or self.term_stop != 28
        ):
            raise ValueError(
                "TASK-009 HOA readback is frozen to Samp1/Wave1/Field1/Type1/"
                "Epsilon0/Vertex0/Z7..Z28"
            )

    @property
    def settings_hash(self) -> str:
        self.validate()
        text = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


TASK009_MFE_FULL_HOA_555_V1 = MfeFullHoaSettings()


@dataclass(frozen=True, slots=True)
class MfeFullHoaResult:
    wavelength_um: float
    coefficients_waves: tuple[tuple[int, float], ...]
    settings_id: str
    settings_hash: str

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
            math.fsum(value**2 for term, value in self.coefficients_waves if 7 <= term <= 28)
        )


@dataclass(slots=True)
class MfeFullHoaRunner:
    system: Any
    zosapi: Any
    settings: MfeFullHoaSettings = TASK009_MFE_FULL_HOA_555_V1

    def run(self) -> MfeFullHoaResult:
        settings = self.settings
        settings.validate()
        mfe = self.system.MFE
        calculate = getattr(mfe, "CalculateMeritFunction", None)
        if not callable(calculate):
            raise MfeFullHoaError("installed MFE exposes no CalculateMeritFunction")
        baseline = int(mfe.NumberOfOperands)
        operands: list[tuple[int, Any]] = []
        coefficients: tuple[tuple[int, float], ...] = ()
        try:
            for offset, term in enumerate(
                range(settings.term_start, settings.term_stop + 1), start=1
            ):
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
        expected_count = settings.term_stop - settings.term_start + 1
        if len(coefficients) != expected_count or not all(
            math.isfinite(value) for _, value in coefficients
        ):
            raise MfeFullHoaError(f"invalid full-HOA ZERN readback: {coefficients!r}")
        if int(mfe.NumberOfOperands) != baseline:
            raise MfeFullHoaError("temporary full-HOA ZERN cleanup left the MFE modified")
        wavelength_um = float(
            self.system.SystemData.Wavelengths.GetWavelength(settings.wavelength_number).Wavelength
        )
        if not math.isfinite(wavelength_um) or wavelength_um <= 0:
            raise MfeFullHoaError("invalid analysis wavelength")
        return MfeFullHoaResult(
            wavelength_um,
            coefficients,
            settings.settings_id,
            settings.settings_hash,
        )

    def _configure(self, operand: Any, term: int) -> None:
        settings = self.settings
        zern = getattr(self.zosapi.Editors.MFE.MeritOperandType, "ZERN", None)
        if zern is None:
            raise MfeFullHoaError("installed MeritOperandType exposes no ZERN member")
        operand.ChangeType(zern)
        values = {
            "term": term,
            "wave": settings.wavelength_number,
            "samp": settings.sampling,
            "field": settings.field_number,
            "type": settings.zernike_type,
            "epsilon": settings.epsilon,
            "vertex": settings.vertex,
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
                cell.IntegerValue = int(value)
            except Exception:  # noqa: BLE001 - numeric cells expose mixed setters
                cell.DoubleValue = float(value)
