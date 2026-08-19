from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .domain import ScientificBaseline
from .ref_mono import REF_MONO_ENVELOPE
from .standard_eye import (
    IMAGE_REF,
    IOL_REF,
    _quick_focus_wavefront,
    _set_material_index,
    standard_eye_construction,
    validate_standard_eye_asset,
)
from .zos import (
    MfeZernikeStandardRunner,
    MfeZernikeStandardSettings,
    SequentialEditor,
    ZosSession,
)

REF_MONO_STD_ANT_ROLE = "REF_MONO_STD_ANT"
REF_MONO_STD_POST_ROLE = "REF_MONO_STD_POST"
REF_MONO_SA_NEUTRAL_TOLERANCE_UM = 0.005
REF_MONO_CONIC_SCAN = (-8.0, -4.0, -2.0, -1.0, 0.0, 1.0, 2.0, 4.0, 8.0)
REF_MONO_CONIC_ITERATIONS = 32


class RefMonoCalibrationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RefMonoSaCalibration:
    radius_mm: float
    conic: float
    reference_c40_um: float
    actual_c40_um: float
    delta_c40_um: float

    @property
    def passed(self) -> bool:
        return abs(self.delta_c40_um) <= REF_MONO_SA_NEUTRAL_TOLERANCE_UM


def _best_focus_c40_um(session: ZosSession) -> float:
    lde = session.system.LDE
    image_index = int(lde.NumberOfSurfaces) - 1
    if image_index < 2:
        raise RefMonoCalibrationError("standard-eye system has too few surfaces")
    pre_image = lde.GetSurfaceAt(image_index - 1)
    fixed = float(pre_image.Thickness)
    try:
        _quick_focus_wavefront(session)
        result = MfeZernikeStandardRunner(session.system, session.zosapi).run(
            MfeZernikeStandardSettings()
        )
        if not math.isfinite(result.c40_um):
            raise RefMonoCalibrationError("MFE ZERN returned a non-finite C40")
        return result.c40_um
    finally:
        pre_image.Thickness = fixed


def _load_reference_c40_um(
    session: ZosSession,
    baseline: ScientificBaseline,
    standard_eye_path: Path,
) -> float:
    spec = standard_eye_construction(baseline)
    validation = validate_standard_eye_asset(session, spec, standard_eye_path)
    if not validation.passed or validation.measurements is None:
        raise RefMonoCalibrationError(
            "STD_IOL_EYE_2024 failed validation before REF_MONO calibration: "
            + " | ".join(validation.findings)
        )
    return validation.measurements.corneal_c40_um_6mm


def _insert_ref_mono_in_standard_eye(
    session: ZosSession,
    baseline: ScientificBaseline,
    radius_mm: float,
    conic: float,
) -> None:
    editor = SequentialEditor(session.system, session.zosapi)
    if int(editor.lde.NumberOfSurfaces) != 5:
        raise RefMonoCalibrationError(
            "REF_MONO standard-eye insertion expects the 5-surface empty standard eye"
        )
    if str(editor.surface(3).Comment).strip() != IOL_REF:
        raise RefMonoCalibrationError("standard-eye IOL reference surface role mismatch")
    if str(editor.surface(4).Comment).strip() != IMAGE_REF:
        raise RefMonoCalibrationError("standard-eye IMAGE surface role mismatch")

    original_iol_to_image = float(editor.surface(3).Thickness)
    if original_iol_to_image <= REF_MONO_ENVELOPE.center_thickness_mm:
        raise RefMonoCalibrationError("standard-eye IOL reference leaves no post-IOL image space")

    editor.set_comment(3, REF_MONO_STD_ANT_ROLE)
    editor.set_radius_conic(3, radius_mm=radius_mm, conic=conic)
    editor.set_thickness(3, REF_MONO_ENVELOPE.center_thickness_mm)
    _set_material_index(editor, 3, REF_MONO_ENVELOPE.iol_index)

    editor.insert_surface(4)
    editor.set_comment(4, REF_MONO_STD_POST_ROLE)
    editor.set_radius_conic(4, radius_mm=-radius_mm, conic=conic)
    editor.set_thickness(4, original_iol_to_image - REF_MONO_ENVELOPE.center_thickness_mm)
    _set_material_index(editor, 4, baseline.standard_eye_spec.medium_index)

    editor.set_comment(5, IMAGE_REF)
    editor.set_radius_conic(5, radius_mm=0.0, conic=0.0)


def _set_standard_eye_ref_mono_conic(session: ZosSession, conic: float) -> None:
    if not math.isfinite(conic):
        raise ValueError("REF_MONO conic must be finite")
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_radius_conic(3, radius_mm=float(editor.surface(3).Radius), conic=conic)
    editor.set_radius_conic(4, radius_mm=float(editor.surface(4).Radius), conic=conic)


def solve_ref_mono_neutral_conic(
    session: ZosSession,
    baseline: ScientificBaseline,
    standard_eye_path: str | Path,
    radius_mm: float,
    *,
    tolerance_um: float = REF_MONO_SA_NEUTRAL_TOLERANCE_UM,
) -> RefMonoSaCalibration:
    """Tune the shared conic until the IOL adds approximately zero C40 in the standard eye."""

    if not math.isfinite(radius_mm) or radius_mm <= 0:
        raise ValueError("REF_MONO calibration radius must be finite and positive")
    if not math.isfinite(tolerance_um) or tolerance_um <= 0:
        raise ValueError("REF_MONO SA tolerance must be finite and positive")

    path = Path(standard_eye_path)
    reference_c40 = _load_reference_c40_um(session, baseline, path)
    session.system.LoadFile(str(path.resolve()), False)
    _insert_ref_mono_in_standard_eye(session, baseline, radius_mm, 0.0)

    samples: list[tuple[float, float, float]] = []
    for conic in REF_MONO_CONIC_SCAN:
        _set_standard_eye_ref_mono_conic(session, conic)
        actual = _best_focus_c40_um(session)
        delta = actual - reference_c40
        samples.append((conic, actual, delta))
        if abs(delta) <= tolerance_um:
            return RefMonoSaCalibration(radius_mm, conic, reference_c40, actual, delta)

    bracket: tuple[tuple[float, float, float], tuple[float, float, float]] | None = None
    for left, right in zip(samples, samples[1:]):
        if left[2] * right[2] < 0:
            bracket = (left, right)
            break
    if bracket is None:
        details = ", ".join(f"Q={q:g}:Δ={delta:.6g}" for q, _, delta in samples)
        raise RefMonoCalibrationError(
            "REF_MONO conic scan did not bracket a near-neutral C40 solution; " + details
        )

    left, right = bracket
    best = min((left, right), key=lambda item: abs(item[2]))
    for _ in range(REF_MONO_CONIC_ITERATIONS):
        middle_q = 0.5 * (left[0] + right[0])
        _set_standard_eye_ref_mono_conic(session, middle_q)
        actual = _best_focus_c40_um(session)
        delta = actual - reference_c40
        middle = (middle_q, actual, delta)
        if abs(delta) < abs(best[2]):
            best = middle
        if abs(delta) <= tolerance_um:
            return RefMonoSaCalibration(
                radius_mm,
                middle_q,
                reference_c40,
                actual,
                delta,
            )
        if left[2] * delta <= 0:
            right = middle
        else:
            left = middle

    result = RefMonoSaCalibration(radius_mm, best[0], reference_c40, best[1], best[2])
    if abs(result.delta_c40_um) > tolerance_um:
        raise RefMonoCalibrationError(
            f"REF_MONO conic solve did not converge: best ΔC40={result.delta_c40_um:.6g} µm"
        )
    return result


def measure_ref_mono_sa_delta(
    session: ZosSession,
    baseline: ScientificBaseline,
    standard_eye_path: str | Path,
    radius_mm: float,
    conic: float,
) -> RefMonoSaCalibration:
    path = Path(standard_eye_path)
    reference_c40 = _load_reference_c40_um(session, baseline, path)
    session.system.LoadFile(str(path.resolve()), False)
    _insert_ref_mono_in_standard_eye(session, baseline, radius_mm, conic)
    actual = _best_focus_c40_um(session)
    return RefMonoSaCalibration(
        radius_mm,
        conic,
        reference_c40,
        actual,
        actual - reference_c40,
    )
