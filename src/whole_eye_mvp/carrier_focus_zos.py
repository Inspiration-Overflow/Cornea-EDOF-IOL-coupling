from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .carrier_zos import TASK007_CARRIER_ANT_ROLE, TASK007_CARRIER_POST_ROLE
from .ref_mono import symmetric_biconvex_power_d
from .ref_mono_zos import (
    REF_MONO_FOCUS_SHIFT_TOLERANCE_MM,
    REF_MONO_RADIUS_BRACKET_SCALE,
    REF_MONO_RADIUS_ITERATIONS,
)
from .standard_eye import _quick_focus_wavefront
from .zos import SequentialEditor, ZosSession

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


@dataclass(frozen=True, slots=True)
class ActualEyeRadiusSolveResult:
    q: float
    initial_radius_mm: float
    solved_radius_mm: float
    power_d: float
    focus_shift_mm: float
    iterations: int


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


def _require_actual_eye_carrier(session: ZosSession, carrier_path: str | Path) -> Path:
    path = Path(carrier_path)
    if not path.is_file():
        raise CarrierFocusZosError(f"actual-eye carrier input is missing: {path}")
    session.system.LoadFile(str(path.resolve()), False)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise CarrierFocusZosError(
            f"actual-eye carrier expects 7 surfaces, got {lde.NumberOfSurfaces}"
        )
    if str(lde.GetSurfaceAt(4).Comment).strip() != TASK007_CARRIER_ANT_ROLE:
        raise CarrierFocusZosError("actual-eye carrier anterior role mismatch")
    if str(lde.GetSurfaceAt(5).Comment).strip() != TASK007_CARRIER_POST_ROLE:
        raise CarrierFocusZosError("actual-eye carrier posterior role mismatch")
    return path


def _set_radius_and_q(session: ZosSession, radius_mm: float, q: float) -> None:
    radius = float(radius_mm)
    conic = float(q)
    if not math.isfinite(radius) or radius <= 0.0:
        raise ValueError("actual-eye carrier radius must be finite and positive")
    if not math.isfinite(conic):
        raise ValueError("actual-eye carrier Q must be finite")
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_radius_conic(4, radius_mm=radius, conic=conic)
    editor.set_radius_conic(5, radius_mm=-radius, conic=0.0)


def _focus_shift_mm(session: ZosSession) -> float:
    lde = session.system.LDE
    posterior = lde.GetSurfaceAt(5)
    fixed = float(posterior.Thickness)
    try:
        _quick_focus_wavefront(session)
        best = float(posterior.Thickness)
        shift = best - fixed
        if not math.isfinite(shift):
            raise CarrierFocusZosError("Quick Focus returned a non-finite focus shift")
        return shift
    finally:
        posterior.Thickness = fixed


def solve_actual_eye_radius_at_q(
    session: ZosSession,
    carrier_path: str | Path,
    *,
    q: float,
    initial_radius_mm: float | None = None,
    destination: str | Path | None = None,
    tolerance_mm: float = REF_MONO_FOCUS_SHIFT_TOLERANCE_MM,
) -> ActualEyeRadiusSolveResult:
    """Refocus a physical carrier by radius while preserving anterior Q/posterior Q=0."""

    _require_actual_eye_carrier(session, carrier_path)
    _set_epd(session, TASK007_POWER_FOCUS_EPD_MM)
    lde = session.system.LDE
    start = (
        float(initial_radius_mm)
        if initial_radius_mm is not None
        else abs(float(lde.GetSurfaceAt(4).Radius))
    )
    if not math.isfinite(start) or start <= 0.0:
        raise ValueError("starting carrier radius must be finite and positive")
    if not math.isfinite(float(tolerance_mm)) or tolerance_mm <= 0.0:
        raise ValueError("focus-shift tolerance must be finite and positive")

    lower = start * (1.0 - REF_MONO_RADIUS_BRACKET_SCALE)
    upper = start * (1.0 + REF_MONO_RADIUS_BRACKET_SCALE)
    _set_radius_and_q(session, lower, q)
    f_lower = _focus_shift_mm(session)
    _set_radius_and_q(session, upper, q)
    f_upper = _focus_shift_mm(session)
    if f_lower * f_upper > 0.0:
        raise CarrierFocusZosError(
            "P-Q radius bracket does not straddle the fixed retina: "
            f"lower={f_lower:.6g} mm, upper={f_upper:.6g} mm"
        )

    best_radius = start
    best_shift = math.inf
    best_iteration = 0
    for iteration in range(1, REF_MONO_RADIUS_ITERATIONS + 1):
        middle = 0.5 * (lower + upper)
        _set_radius_and_q(session, middle, q)
        shift = _focus_shift_mm(session)
        if abs(shift) < abs(best_shift):
            best_radius = middle
            best_shift = shift
            best_iteration = iteration
        if abs(shift) <= tolerance_mm:
            break
        if f_lower * shift <= 0.0:
            upper = middle
        else:
            lower = middle
            f_lower = shift

    _set_radius_and_q(session, best_radius, q)
    if abs(best_shift) > tolerance_mm:
        raise CarrierFocusZosError(
            f"P-Q radius solve did not converge: best shift={best_shift:.6g} mm"
        )
    if destination is not None:
        SequentialEditor(session.system, session.zosapi).save_as(Path(destination))
    return ActualEyeRadiusSolveResult(
        q=float(q),
        initial_radius_mm=start,
        solved_radius_mm=best_radius,
        power_d=symmetric_biconvex_power_d(best_radius),
        focus_shift_mm=best_shift,
        iterations=best_iteration,
    )


def measure_actual_eye_q_focus(
    session: ZosSession,
    carrier_path: str | Path,
    *,
    q: float,
) -> ActualEyeQFocusCheck:
    _require_actual_eye_carrier(session, carrier_path)
    if not math.isfinite(float(q)):
        raise ValueError("carrier Q must be finite")
    lde = session.system.LDE
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
