from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .carrier_zos import TASK007_CARRIER_ANT_ROLE, TASK007_CARRIER_POST_ROLE
from .standard_eye import _quick_focus_wavefront
from .zos import ZosSession

TASK007_POWER_FOCUS_EPD_MM = 3.0
P_Q_RECHECK_THRESHOLD_D = 0.125


class CarrierFocusZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ActualEyeQFocusCheck:
    q: float
    fixed_iol_post_to_image_mm: float
    best_iol_post_to_image_mm: float
    focus_shift_mm: float
    equivalent_vergence_shift_d: float
    recheck_required: bool


def image_distance_shift_to_vergence_d(
    fixed_distance_mm: float,
    best_distance_mm: float,
    *,
    medium_index: float = CONTROLLED_IOL_CARRIER_546_V1.surrounding_index,
) -> float:
    fixed = float(fixed_distance_mm)
    best = float(best_distance_mm)
    index = float(medium_index)
    if not all(math.isfinite(value) and value > 0.0 for value in (fixed, best, index)):
        raise ValueError("image distances and medium index must be finite and positive")
    return index * 1000.0 * (1.0 / best - 1.0 / fixed)


def _set_epd(session: ZosSession, diameter_mm: float) -> None:
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(diameter_mm)


def measure_actual_eye_q_focus(
    session: ZosSession,
    carrier_path: str | Path,
    *,
    q: float,
) -> ActualEyeQFocusCheck:
    path = Path(carrier_path)
    if not path.is_file():
        raise CarrierFocusZosError(f"actual-eye carrier input is missing: {path}")
    if not math.isfinite(float(q)):
        raise ValueError("carrier Q must be finite")
    session.system.LoadFile(str(path.resolve()), False)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise CarrierFocusZosError(
            f"actual-eye Q focus check expects 7 surfaces, got {lde.NumberOfSurfaces}"
        )
    if str(lde.GetSurfaceAt(4).Comment).strip() != TASK007_CARRIER_ANT_ROLE:
        raise CarrierFocusZosError("actual-eye carrier anterior role mismatch")
    if str(lde.GetSurfaceAt(5).Comment).strip() != TASK007_CARRIER_POST_ROLE:
        raise CarrierFocusZosError("actual-eye carrier posterior role mismatch")

    anterior = lde.GetSurfaceAt(4)
    posterior = lde.GetSurfaceAt(5)
    anterior.Conic = float(q)
    posterior.Conic = 0.0
    _set_epd(session, TASK007_POWER_FOCUS_EPD_MM)

    fixed = float(posterior.Thickness)
    try:
        _quick_focus_wavefront(session)
        best = float(posterior.Thickness)
        if not math.isfinite(best) or best <= 0.0:
            raise CarrierFocusZosError("Quick Focus returned invalid post-IOL image distance")
        shift = best - fixed
        vergence_shift = image_distance_shift_to_vergence_d(fixed, best)
        return ActualEyeQFocusCheck(
            q=float(q),
            fixed_iol_post_to_image_mm=fixed,
            best_iol_post_to_image_mm=best,
            focus_shift_mm=shift,
            equivalent_vergence_shift_d=vergence_shift,
            recheck_required=abs(vergence_shift) >= P_Q_RECHECK_THRESHOLD_D,
        )
    finally:
        posterior.Thickness = fixed
