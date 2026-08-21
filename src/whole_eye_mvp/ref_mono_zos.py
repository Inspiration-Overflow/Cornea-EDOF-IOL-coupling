from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .base_assets import (
    IMAGE_ROLE,
    IOL_ANT_ROLE,
    STOP_ROLE,
    _refractive_indices,
    _set_material_index_at_nominal_wavelength,
)
from .cornea_assets import MAIN_CORNEA_SCAFFOLD, cornea_lock_eye_geometry
from .cornea_zos import (
    FIXED_CORNEA_POST_ROLE,
    measure_distance_cornea_scaffold,
    validate_distance_cornea_measurements,
)
from .domain import ScientificBaseline
from .ref_mono import (
    REF_MONO_ENVELOPE,
    REF_MONO_FOCUS_EPD_MM,
    REF_MONO_INITIAL_CONIC,
    RefMonoEnvelope,
    initial_ref_mono_radius_mm,
    symmetric_biconvex_power_d,
)
from .standard_eye import _quick_focus_wavefront
from .zos import SequentialEditor, ZosSession

REF_MONO_ANT_ROLE = "REF_MONO_ANT"
REF_MONO_POST_ROLE = "REF_MONO_POST"
REF_MONO_RADIUS_BRACKET_SCALE = 0.40
REF_MONO_FOCUS_SHIFT_TOLERANCE_MM = 0.001
REF_MONO_RADIUS_ITERATIONS = 40
REF_MONO_RADIUS_FLOOR_MM = 1.0
REF_MONO_RADIUS_CAP_MM = 500.0
REF_MONO_BRACKET_MAX_EXPANSIONS = 12
INDEX_TOLERANCE = 1.0e-6
GEOMETRY_TOLERANCE_MM = 0.001


class RefMonoZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RefMonoMeasurements:
    cornea_ant_role: str
    radius_ant_mm: float
    radius_post_mm: float
    conic: float
    equivalent_power_d: float
    center_thickness_mm: float
    iol_index: float
    optic_diameter_mm: float
    entrance_pupil_mm: float
    focus_shift_mm: float
    post_cornea_to_iol_ant_mm: float
    iol_post_to_image_mm: float
    axial_length_mm: float
    surface_count: int
    stop_surface: int


def _set_epd(session: ZosSession, diameter_mm: float) -> None:
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(diameter_mm)


def _require_distance_scaffold(
    session: ZosSession,
    baseline: ScientificBaseline,
    path: Path,
) -> None:
    measurement = measure_distance_cornea_scaffold(session, path)
    findings = validate_distance_cornea_measurements(measurement, baseline)
    if findings:
        raise RefMonoZosError(
            "distance-cornea input failed validation: " + " | ".join(findings)
        )


def _require_cornea_only_scaffold(
    session: ZosSession,
    baseline: ScientificBaseline,
    path: Path,
) -> None:
    session.system.LoadFile(str(path.resolve()), False)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 6:
        raise RefMonoZosError(
            f"cornea-only candidate must contain 6 surfaces, got {lde.NumberOfSurfaces}"
        )
    expected = {
        2: FIXED_CORNEA_POST_ROLE,
        3: STOP_ROLE,
        4: IOL_ANT_ROLE,
        5: IMAGE_ROLE,
    }
    for surface_number, role in expected.items():
        actual = str(lde.GetSurfaceAt(surface_number).Comment).strip()
        if actual != role:
            raise RefMonoZosError(
                f"cornea-only surface {surface_number} role mismatch: expected {role!r}, got {actual!r}"
            )

    geometry = cornea_lock_eye_geometry(baseline)
    posterior = lde.GetSurfaceAt(2)
    stop = lde.GetSurfaceAt(3)
    iol_ref = lde.GetSurfaceAt(4)
    post_to_iol = float(posterior.Thickness) + float(stop.Thickness)
    axial = sum(float(lde.GetSurfaceAt(index).Thickness) for index in range(1, 5))
    if abs(post_to_iol - geometry.post_cornea_to_iol_ant_mm) > GEOMETRY_TOLERANCE_MM:
        raise RefMonoZosError("cornea-only candidate changed post-cornea→IOL reference distance")
    if abs(float(iol_ref.Thickness) - geometry.iol_ant_to_image_mm) > GEOMETRY_TOLERANCE_MM:
        raise RefMonoZosError("cornea-only candidate changed IOL-reference→IMAGE distance")
    if abs(axial - geometry.axial_length_mm) > GEOMETRY_TOLERANCE_MM:
        raise RefMonoZosError("cornea-only candidate changed locked LB axial length")


def insert_ref_mono(
    session: ZosSession,
    baseline: ScientificBaseline,
    radius_mm: float,
    *,
    conic: float = REF_MONO_INITIAL_CONIC,
    envelope: RefMonoEnvelope = REF_MONO_ENVELOPE,
) -> None:
    envelope.validate()
    geometry = cornea_lock_eye_geometry(baseline)
    if envelope.center_thickness_mm >= geometry.iol_ant_to_image_mm:
        raise RefMonoZosError("REF_MONO center thickness leaves no post-IOL image space")

    editor = SequentialEditor(session.system, session.zosapi)
    if int(editor.lde.NumberOfSurfaces) != 6:
        raise RefMonoZosError("cornea-only scaffold must have 6 surfaces before IOL insertion")

    editor.set_comment(4, REF_MONO_ANT_ROLE)
    editor.set_radius_conic(4, radius_mm=radius_mm, conic=conic)
    editor.set_thickness(4, envelope.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 4, envelope.iol_index)

    editor.insert_surface(5)
    editor.set_comment(5, REF_MONO_POST_ROLE)
    editor.set_radius_conic(5, radius_mm=-radius_mm, conic=conic)
    editor.set_thickness(5, geometry.iol_ant_to_image_mm - envelope.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(
        editor,
        5,
        MAIN_CORNEA_SCAFFOLD.aqueous_index,
    )

    editor.set_comment(6, IMAGE_ROLE)
    editor.set_radius_conic(6, radius_mm=0.0, conic=0.0)
    _set_epd(session, REF_MONO_FOCUS_EPD_MM)


def _set_symmetric_radius(session: ZosSession, radius_mm: float) -> None:
    if not math.isfinite(radius_mm) or radius_mm <= 0:
        raise ValueError("REF_MONO trial radius must be finite and positive")
    editor = SequentialEditor(session.system, session.zosapi)
    conic = float(editor.surface(4).Conic)
    editor.set_radius_conic(4, radius_mm=radius_mm, conic=conic)
    editor.set_radius_conic(5, radius_mm=-radius_mm, conic=conic)


def _focus_shift_mm(session: ZosSession) -> float:
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise RefMonoZosError("REF_MONO focus solve expects 7 surfaces")
    iol_post = lde.GetSurfaceAt(5)
    fixed = float(iol_post.Thickness)
    try:
        _quick_focus_wavefront(session)
        best = float(iol_post.Thickness)
        shift = best - fixed
        if not math.isfinite(shift):
            raise RefMonoZosError("Quick Focus returned a non-finite REF_MONO focus shift")
        return shift
    finally:
        iol_post.Thickness = fixed


def solve_ref_mono_radius_mm(
    session: ZosSession,
    baseline: ScientificBaseline,
    *,
    initial_radius_mm: float | None = None,
    tolerance_mm: float = REF_MONO_FOCUS_SHIFT_TOLERANCE_MM,
) -> tuple[float, float]:
    """Solve symmetric REF_MONO radius so Wavefront Quick Focus returns near-zero shift."""

    if not math.isfinite(tolerance_mm) or tolerance_mm <= 0:
        raise ValueError("REF_MONO focus-shift tolerance must be finite and positive")
    start = (
        initial_radius_mm
        if initial_radius_mm is not None
        else initial_ref_mono_radius_mm(baseline)
    )
    if not math.isfinite(start) or start <= 0:
        raise ValueError("REF_MONO starting radius must be finite and positive")

    lower = start * (1.0 - REF_MONO_RADIUS_BRACKET_SCALE)
    upper = start * (1.0 + REF_MONO_RADIUS_BRACKET_SCALE)

    _set_symmetric_radius(session, lower)
    f_lower = _focus_shift_mm(session)
    _set_symmetric_radius(session, upper)
    f_upper = _focus_shift_mm(session)

    # The paraxial starting radius assumes a powered cornea.  Frozen native
    # reference eyes keep a plano corneal slot, so the emmetropic carrier can
    # sit far below the nominal bracket; widen geometrically toward the sign
    # that restores focus before declaring failure.
    for _ in range(REF_MONO_BRACKET_MAX_EXPANSIONS):
        if f_lower * f_upper <= 0:
            break
        if f_lower > 0:
            candidate = max(lower * 0.5, REF_MONO_RADIUS_FLOOR_MM)
            if candidate >= lower:
                break
            lower = candidate
            _set_symmetric_radius(session, lower)
            f_lower = _focus_shift_mm(session)
        else:
            candidate = min(upper * 2.0, REF_MONO_RADIUS_CAP_MM)
            if candidate <= upper:
                break
            upper = candidate
            _set_symmetric_radius(session, upper)
            f_upper = _focus_shift_mm(session)

    if f_lower * f_upper > 0:
        raise RefMonoZosError(
            "REF_MONO Quick Focus radius bracket does not straddle the fixed retina: "
            f"lower={f_lower:.6g} mm, upper={f_upper:.6g} mm"
        )

    best_radius = start
    best_shift = math.inf
    for _ in range(REF_MONO_RADIUS_ITERATIONS):
        middle = 0.5 * (lower + upper)
        _set_symmetric_radius(session, middle)
        shift = _focus_shift_mm(session)
        if abs(shift) < abs(best_shift):
            best_radius, best_shift = middle, shift
        if abs(shift) <= tolerance_mm:
            _set_symmetric_radius(session, middle)
            return middle, shift
        if f_lower * shift <= 0:
            upper = middle
        else:
            lower = middle
            f_lower = shift

    _set_symmetric_radius(session, best_radius)
    if abs(best_shift) > tolerance_mm:
        raise RefMonoZosError(
            f"REF_MONO radius solve did not converge: best shift={best_shift:.6g} mm"
        )
    return best_radius, best_shift


def build_ref_mono_on_cornea_candidate(
    session: ZosSession,
    baseline: ScientificBaseline,
    cornea_path: str | Path,
    destination: str | Path,
    *,
    conic: float = REF_MONO_INITIAL_CONIC,
    initial_radius_mm: float | None = None,
) -> RefMonoMeasurements:
    source = Path(cornea_path)
    _require_cornea_only_scaffold(session, baseline, source)
    start = (
        initial_radius_mm
        if initial_radius_mm is not None
        else initial_ref_mono_radius_mm(baseline)
    )
    insert_ref_mono(session, baseline, start, conic=conic)
    solve_ref_mono_radius_mm(session, baseline, initial_radius_mm=start)
    output = Path(destination)
    SequentialEditor(session.system, session.zosapi).save_as(output)
    return measure_ref_mono_candidate(session, baseline, output)


def build_ref_mono_candidate(
    session: ZosSession,
    baseline: ScientificBaseline,
    distance_cornea_path: str | Path,
    destination: str | Path,
    *,
    conic: float = REF_MONO_INITIAL_CONIC,
    initial_radius_mm: float | None = None,
) -> RefMonoMeasurements:
    source = Path(distance_cornea_path)
    _require_distance_scaffold(session, baseline, source)
    return build_ref_mono_on_cornea_candidate(
        session,
        baseline,
        source,
        destination,
        conic=conic,
        initial_radius_mm=initial_radius_mm,
    )


def measure_ref_mono_candidate(
    session: ZosSession,
    baseline: ScientificBaseline,
    path: str | Path,
) -> RefMonoMeasurements:
    session.system.LoadFile(str(Path(path).resolve()), False)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise RefMonoZosError(
            f"REF_MONO candidate must contain 7 surfaces, got {lde.NumberOfSurfaces}"
        )
    rows = tuple(lde.GetSurfaceAt(index) for index in range(1, 7))
    expected_roles = {
        2: FIXED_CORNEA_POST_ROLE,
        3: STOP_ROLE,
        4: REF_MONO_ANT_ROLE,
        5: REF_MONO_POST_ROLE,
        6: IMAGE_ROLE,
    }
    for surface_number, role in expected_roles.items():
        actual = str(lde.GetSurfaceAt(surface_number).Comment).strip()
        if actual != role:
            raise RefMonoZosError(
                f"REF_MONO surface {surface_number} role mismatch: expected {role!r}, got {actual!r}"
            )

    radius_ant = float(rows[3].Radius)
    radius_post = float(rows[4].Radius)
    conic_ant = float(rows[3].Conic)
    conic_post = float(rows[4].Conic)
    if abs(radius_ant + radius_post) > 1.0e-9:
        raise RefMonoZosError("REF_MONO must keep symmetric biconvex radii")
    if abs(conic_ant - conic_post) > 1.0e-12:
        raise RefMonoZosError("REF_MONO must keep the same conic on both surfaces")

    _set_epd(session, REF_MONO_FOCUS_EPD_MM)
    focus_shift = _focus_shift_mm(session)
    return RefMonoMeasurements(
        cornea_ant_role=str(rows[0].Comment).strip(),
        radius_ant_mm=radius_ant,
        radius_post_mm=radius_post,
        conic=conic_ant,
        equivalent_power_d=symmetric_biconvex_power_d(radius_ant),
        center_thickness_mm=float(rows[3].Thickness),
        iol_index=_refractive_indices(session.system, 4)[0],
        optic_diameter_mm=REF_MONO_ENVELOPE.optic_diameter_mm,
        entrance_pupil_mm=float(session.system.SystemData.Aperture.ApertureValue),
        focus_shift_mm=focus_shift,
        post_cornea_to_iol_ant_mm=float(rows[1].Thickness) + float(rows[2].Thickness),
        iol_post_to_image_mm=float(rows[4].Thickness),
        axial_length_mm=sum(float(row.Thickness) for row in rows[:-1]),
        surface_count=int(lde.NumberOfSurfaces),
        stop_surface=int(lde.StopSurface),
    )


def validate_ref_mono_measurements(
    measurement: RefMonoMeasurements,
    baseline: ScientificBaseline,
) -> tuple[str, ...]:
    geometry = cornea_lock_eye_geometry(baseline)
    findings: list[str] = []

    def close(label: str, actual: float, expected: float, tolerance: float) -> None:
        if not math.isfinite(actual) or abs(actual - expected) > tolerance:
            findings.append(
                f"{label}: expected {expected:.12g} ± {tolerance:.3g}, got {actual:.12g}"
            )

    close(
        "center_thickness_mm",
        measurement.center_thickness_mm,
        REF_MONO_ENVELOPE.center_thickness_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close("iol_index", measurement.iol_index, REF_MONO_ENVELOPE.iol_index, INDEX_TOLERANCE)
    close(
        "entrance_pupil_mm",
        measurement.entrance_pupil_mm,
        REF_MONO_FOCUS_EPD_MM,
        0.001,
    )
    if not math.isfinite(measurement.focus_shift_mm) or (
        abs(measurement.focus_shift_mm) > REF_MONO_FOCUS_SHIFT_TOLERANCE_MM
    ):
        findings.append(
            "focus_shift_mm: expected near zero within "
            f"{REF_MONO_FOCUS_SHIFT_TOLERANCE_MM:.3g} mm, "
            f"got {measurement.focus_shift_mm:.12g}"
        )
    close(
        "post_cornea_to_iol_ant_mm",
        measurement.post_cornea_to_iol_ant_mm,
        geometry.post_cornea_to_iol_ant_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "iol_post_to_image_mm",
        measurement.iol_post_to_image_mm,
        geometry.iol_ant_to_image_mm - REF_MONO_ENVELOPE.center_thickness_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "axial_length_mm",
        measurement.axial_length_mm,
        geometry.axial_length_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    if measurement.surface_count != 7:
        findings.append(f"surface_count: expected 7, got {measurement.surface_count}")
    if measurement.stop_surface != 3:
        findings.append(f"stop_surface: expected 3, got {measurement.stop_surface}")
    return tuple(findings)
