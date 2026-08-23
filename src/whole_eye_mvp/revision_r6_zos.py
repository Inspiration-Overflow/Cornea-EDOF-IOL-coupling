from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path

from .carrier_focus_zos import P_Q_RECHECK_THRESHOLD_D, image_distance_shift_to_vergence_d
from .carrier_q_zos import (
    Q_REPLAY_SA_TOLERANCE_UM,
    CarrierQSolution,
    build_physical_carrier_in_standard_eye,
    measure_standard_eye_c40,
    measure_zero_hoa_reference,
    solve_q_for_platform,
)
from .carrier_zos import TASK007_CARRIER_ANT_ROLE, TASK007_CARRIER_POST_ROLE
from .domain import PlatformId, ScientificBaseline
from .model_revision import IOL_CLEAR_SEMI_DIAMETER_MM, binary4_mechanism_spec
from .model_revision_zos import (
    RevisionGeometryReadback,
    apply_revision_to_full_eye,
    read_revision_geometry,
    validate_revision_geometry,
)
from .ref_mono import symmetric_biconvex_power_d
from .ref_mono_zos import (
    REF_MONO_FOCUS_SHIFT_TOLERANCE_MM,
    REF_MONO_RADIUS_BRACKET_SCALE,
    REF_MONO_RADIUS_ITERATIONS,
)
from .revision_carrier_zos import RevisionAnalyticalCarrierResult
from .revision_r4_fit import (
    R4BoundaryDiagnostic,
    R4ZonePrescription,
    _boundary_diagnostics,
    _minimum_radicand,
)
from .revision_r4_zos import (
    R4Binary4ZoneReadback,
    R4MechanismReadback,
    R4OpticalAudit,
    R4RadPowerReadback,
    audit_r4_model,
    read_r4_mechanism,
    read_rad_power_profile,
)
from .revision_r5_2 import r5_2_zones_for_carrier
from .zos import Binary4Zone, SequentialEditor, ZosSession
from .zos.primitives import binary4_zone_columns

R6_FOCUS_PUPIL_DIAMETER_MM = 3.0
R6_RAY_HEALTH_PUPILS_MM = (3.0, 5.0)


class RevisionR6ZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class R6ActualEyeQFocusCheck:
    q: float
    fixed_iol_post_to_retina_mm: float
    best_iol_post_to_retina_mm: float
    focus_shift_mm: float
    equivalent_vergence_shift_d: float
    recheck_required: bool


@dataclass(frozen=True, slots=True)
class R6ActualEyeRadiusSolveResult:
    q: float
    initial_radius_mm: float
    solved_radius_mm: float
    power_d: float
    focus_shift_mm: float
    iterations: int


@dataclass(frozen=True, slots=True)
class R6CarrierSolveResult:
    base_id: str
    cornea_id: str
    platform_id: str
    carrier_id: str
    q0: RevisionAnalyticalCarrierResult
    q_solution: CarrierQSolution
    recheck_cycles: tuple[dict[str, object], ...]
    final_focus: R6ActualEyeQFocusCheck
    path: str
    radius_ant_mm: float
    radius_post_mm: float
    power_d: float
    q_ant: float
    q_post: float
    geometry_3mm: RevisionGeometryReadback
    standard_eye_sa_replay_um: float
    standard_eye_sa_error_um: float


@dataclass(frozen=True, slots=True)
class R6Binary4BuildResult:
    base_id: str
    cornea_id: str
    platform_id: str
    optic_state: str
    surface_number: int
    path: str
    zones: tuple[R4Binary4ZoneReadback, ...]
    boundaries: tuple[R4BoundaryDiagnostic, ...]
    minimum_conic_radicand: float


@dataclass(frozen=True, slots=True)
class R6RayHealth:
    pupil_diameter_mm: float
    passed: bool
    failures: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class R6CarrierValidationResult:
    carrier: R6CarrierSolveResult
    actual_mono: R6Binary4BuildResult
    actual_edof: R6Binary4BuildResult
    standard_mono: R6Binary4BuildResult
    standard_edof: R6Binary4BuildResult
    standard_mechanism: R4MechanismReadback
    rad_power_readback: R4RadPowerReadback | None
    actual_mono_ray_health: tuple[R6RayHealth, ...]
    actual_edof_ray_health: tuple[R6RayHealth, ...]
    full_standard_audit_mono: R4OpticalAudit | None
    full_standard_audit_edof: R4OpticalAudit | None


def _require_actual_eye(session: ZosSession, path: str | Path, base_id: str) -> Path:
    source = Path(path)
    if not source.is_file():
        raise RevisionR6ZosError(f"R6 actual-eye carrier is missing: {source}")
    session.system.LoadFile(str(source.resolve()), False)
    if int(session.system.LDE.NumberOfSurfaces) != 7:
        raise RevisionR6ZosError("R6 actual-eye carrier must contain seven surfaces")
    if str(session.system.LDE.GetSurfaceAt(4).Comment).strip() != TASK007_CARRIER_ANT_ROLE:
        raise RevisionR6ZosError("R6 actual-eye anterior carrier role mismatch")
    if str(session.system.LDE.GetSurfaceAt(5).Comment).strip() != TASK007_CARRIER_POST_ROLE:
        raise RevisionR6ZosError("R6 actual-eye posterior carrier role mismatch")
    apply_revision_to_full_eye(
        session,
        base_id,
        pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM,
    )
    return source


def _set_actual_radius_q(session: ZosSession, radius_mm: float, q: float) -> None:
    radius = float(radius_mm)
    conic = float(q)
    if not math.isfinite(radius) or radius <= 0.0:
        raise ValueError("R6 carrier radius must be finite and positive")
    if not math.isfinite(conic):
        raise ValueError("R6 carrier Q must be finite")
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_radius_conic(4, radius_mm=radius, conic=conic)
    editor.set_radius_conic(5, radius_mm=-radius, conic=0.0)


def _focus_shift_mm(session: ZosSession) -> float:
    from .standard_eye import _quick_focus_wavefront

    posterior = session.system.LDE.GetSurfaceAt(5)
    fixed = float(posterior.Thickness)
    try:
        _quick_focus_wavefront(session)
        best = float(posterior.Thickness)
        shift = best - fixed
        if not math.isfinite(shift):
            raise RevisionR6ZosError("R6 Quick Focus returned non-finite focus shift")
        return shift
    finally:
        posterior.Thickness = fixed


def measure_revision_actual_eye_q_focus(
    session: ZosSession,
    carrier_path: str | Path,
    *,
    base_id: str,
    q: float,
) -> R6ActualEyeQFocusCheck:
    _require_actual_eye(session, carrier_path, base_id)
    _set_actual_radius_q(
        session,
        abs(float(session.system.LDE.GetSurfaceAt(4).Radius)),
        q,
    )
    apply_revision_to_full_eye(
        session,
        base_id,
        pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM,
    )
    posterior = session.system.LDE.GetSurfaceAt(5)
    fixed = float(posterior.Thickness)
    shift = _focus_shift_mm(session)
    best = fixed + shift
    vergence = image_distance_shift_to_vergence_d(fixed, best)
    return R6ActualEyeQFocusCheck(
        q=float(q),
        fixed_iol_post_to_retina_mm=fixed,
        best_iol_post_to_retina_mm=best,
        focus_shift_mm=shift,
        equivalent_vergence_shift_d=vergence,
        recheck_required=abs(vergence) >= P_Q_RECHECK_THRESHOLD_D,
    )


def solve_revision_actual_eye_radius_at_q(
    session: ZosSession,
    carrier_path: str | Path,
    *,
    base_id: str,
    q: float,
    initial_radius_mm: float | None = None,
    destination: str | Path | None = None,
) -> R6ActualEyeRadiusSolveResult:
    _require_actual_eye(session, carrier_path, base_id)
    start = (
        float(initial_radius_mm)
        if initial_radius_mm is not None
        else abs(float(session.system.LDE.GetSurfaceAt(4).Radius))
    )
    if not math.isfinite(start) or start <= 0.0:
        raise ValueError("R6 starting carrier radius must be finite and positive")

    lower = start * (1.0 - REF_MONO_RADIUS_BRACKET_SCALE)
    upper = start * (1.0 + REF_MONO_RADIUS_BRACKET_SCALE)
    _set_actual_radius_q(session, lower, q)
    apply_revision_to_full_eye(session, base_id, pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM)
    f_lower = _focus_shift_mm(session)
    _set_actual_radius_q(session, upper, q)
    apply_revision_to_full_eye(session, base_id, pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM)
    f_upper = _focus_shift_mm(session)
    if f_lower * f_upper > 0.0:
        raise RevisionR6ZosError(
            "R6 P/Q radius bracket does not straddle fixed retina: "
            f"lower={f_lower:.6g}, upper={f_upper:.6g} mm"
        )

    best_radius = start
    best_shift = math.inf
    best_iteration = 0
    for iteration in range(1, REF_MONO_RADIUS_ITERATIONS + 1):
        middle = 0.5 * (lower + upper)
        _set_actual_radius_q(session, middle, q)
        apply_revision_to_full_eye(session, base_id, pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM)
        shift = _focus_shift_mm(session)
        if abs(shift) < abs(best_shift):
            best_radius = middle
            best_shift = shift
            best_iteration = iteration
        if abs(shift) <= REF_MONO_FOCUS_SHIFT_TOLERANCE_MM:
            break
        if f_lower * shift <= 0.0:
            upper = middle
        else:
            lower = middle
            f_lower = shift

    _set_actual_radius_q(session, best_radius, q)
    apply_revision_to_full_eye(session, base_id, pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM)
    if abs(best_shift) > REF_MONO_FOCUS_SHIFT_TOLERANCE_MM:
        raise RevisionR6ZosError(
            f"R6 P/Q radius solve did not converge: best shift={best_shift:.6g} mm"
        )
    if destination is not None:
        SequentialEditor(session.system, session.zosapi).save_as(Path(destination))
    return R6ActualEyeRadiusSolveResult(
        q=float(q),
        initial_radius_mm=start,
        solved_radius_mm=best_radius,
        power_d=symmetric_biconvex_power_d(best_radius),
        focus_shift_mm=best_shift,
        iterations=best_iteration,
    )


def solve_revision_platform_carrier(
    session: ZosSession,
    baseline: ScientificBaseline,
    standard_eye_path: str | Path,
    *,
    base_id: str,
    cornea_id: str,
    platform_id: str,
    q0: RevisionAnalyticalCarrierResult,
    q0_path: str | Path,
    output_dir: str | Path,
    max_rechecks: int,
) -> R6CarrierSolveResult:
    del baseline
    if platform_id not in {item.value for item in PlatformId}:
        raise ValueError(f"unsupported R6 platform: {platform_id}")
    if max_rechecks < 0:
        raise ValueError("R6 max_rechecks must be non-negative")

    current_path = Path(q0_path)
    current_radius = q0.radius_ant_mm
    current_power = q0.power_d
    cycles: list[dict[str, object]] = []

    q_solution = solve_q_for_platform(
        session,
        standard_eye_path,
        platform_id=platform_id,
        source_power_d=current_power,
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
    )
    focus = measure_revision_actual_eye_q_focus(
        session,
        current_path,
        base_id=base_id,
        q=q_solution.q,
    )

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    for cycle in range(1, max_rechecks + 1):
        if not focus.recheck_required:
            break
        refocused = root / f"PQ_{base_id}_{cornea_id}_{platform_id}_C{cycle}.zmx"
        radius_result = solve_revision_actual_eye_radius_at_q(
            session,
            current_path,
            base_id=base_id,
            q=q_solution.q,
            initial_radius_mm=current_radius,
            destination=refocused,
        )
        current_radius = radius_result.solved_radius_mm
        current_power = radius_result.power_d
        q_solution = solve_q_for_platform(
            session,
            standard_eye_path,
            platform_id=platform_id,
            source_power_d=current_power,
            radius_ant_mm=current_radius,
            radius_post_mm=-current_radius,
        )
        focus = measure_revision_actual_eye_q_focus(
            session,
            refocused,
            base_id=base_id,
            q=q_solution.q,
        )
        cycles.append(
            {
                "cycle": cycle,
                "radius_solve": asdict(radius_result),
                "q_solution": asdict(q_solution),
                "actual_eye_focus": asdict(focus),
            }
        )
        current_path = refocused

    if focus.recheck_required:
        raise RevisionR6ZosError(
            f"R6 {base_id}/{cornea_id}/{platform_id} did not converge within {max_rechecks} P/Q cycles"
        )

    _require_actual_eye(session, current_path, base_id)
    _set_actual_radius_q(session, current_radius, q_solution.q)
    apply_revision_to_full_eye(session, base_id, pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM)
    final_path = root / f"ANALYTICAL_MONO_{base_id}_{cornea_id}_{platform_id}.zmx"
    SequentialEditor(session.system, session.zosapi).save_as(final_path)
    session.system.LoadFile(str(final_path.resolve()), False)
    apply_revision_to_full_eye(session, base_id, pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM)

    ant = session.system.LDE.GetSurfaceAt(4)
    post = session.system.LDE.GetSurfaceAt(5)
    if (
        abs(float(ant.Radius) - current_radius) > 1.0e-9
        or abs(float(post.Radius) + current_radius) > 1.0e-9
        or abs(float(ant.Conic) - q_solution.q) > 1.0e-10
        or abs(float(post.Conic)) > 1.0e-12
    ):
        raise RevisionR6ZosError("R6 final analytical carrier R/Q replay mismatch")
    geometry = read_revision_geometry(session, base_id, full_eye=True)
    findings = validate_revision_geometry(
        geometry,
        base_id,
        expected_pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM,
    )
    if findings:
        raise RevisionR6ZosError("R6 final carrier geometry failed: " + " | ".join(findings))

    reference = measure_zero_hoa_reference(
        session,
        standard_eye_path,
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
    )
    build_physical_carrier_in_standard_eye(
        session,
        standard_eye_path,
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
        q=q_solution.q,
    )
    measured = measure_standard_eye_c40(session)
    replay_sa = measured.c40_um - reference.wavefront.c40_um
    if abs(replay_sa - q_solution.target_sa_um) > Q_REPLAY_SA_TOLERANCE_UM:
        raise RevisionR6ZosError(
            f"R6 standard-eye SA replay failed: {replay_sa:.6g} vs {q_solution.target_sa_um:.6g} µm"
        )

    final_focus = measure_revision_actual_eye_q_focus(
        session,
        final_path,
        base_id=base_id,
        q=q_solution.q,
    )
    if final_focus.recheck_required:
        raise RevisionR6ZosError("R6 final carrier focus replay crossed P/Q recheck threshold")

    carrier_id = f"R6_{base_id}_{cornea_id}_{platform_id}"
    return R6CarrierSolveResult(
        base_id=base_id,
        cornea_id=cornea_id,
        platform_id=platform_id,
        carrier_id=carrier_id,
        q0=q0,
        q_solution=q_solution,
        recheck_cycles=tuple(cycles),
        final_focus=final_focus,
        path=str(final_path.resolve()),
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
        power_d=current_power,
        q_ant=q_solution.q,
        q_post=0.0,
        geometry_3mm=geometry,
        standard_eye_sa_replay_um=replay_sa,
        standard_eye_sa_error_um=replay_sa - q_solution.target_sa_um,
    )


def _surface_number(platform_id: str, *, standard_eye: bool) -> int:
    role = binary4_mechanism_spec(platform_id).surface_role
    if standard_eye:
        return 3 if role == "anterior" else 4
    return 4 if role == "anterior" else 5


def _parameter_double(session: ZosSession, surface_number: int, parameter_number: int) -> float:
    column = getattr(session.zosapi.Editors.LDE.SurfaceColumn, f"Par{parameter_number}")
    return float(session.system.LDE.GetSurfaceAt(surface_number).GetSurfaceCell(column).DoubleValue)


def _parameter_integer(session: ZosSession, surface_number: int, parameter_number: int) -> int:
    column = getattr(session.zosapi.Editors.LDE.SurfaceColumn, f"Par{parameter_number}")
    return int(session.system.LDE.GetSurfaceAt(surface_number).GetSurfaceCell(column).IntegerValue)


def _read_binary4_zones(
    session: ZosSession,
    platform_id: str,
    *,
    standard_eye: bool,
) -> tuple[R4Binary4ZoneReadback, ...]:
    spec = binary4_mechanism_spec(platform_id)
    surface_number = _surface_number(platform_id, standard_eye=standard_eye)
    row = session.system.LDE.GetSurfaceAt(surface_number)
    type_name = str(getattr(row, "TypeName", "") or "")
    fallback = str(row.GetType()) if callable(getattr(row, "GetType", None)) else ""
    if "binary" not in type_name.casefold() and "binary" not in fallback.casefold():
        raise RevisionR6ZosError("R6 serialized surface did not replay as Binary 4")
    zone_count = _parameter_integer(session, surface_number, 1)
    aspheric_count = _parameter_integer(session, surface_number, 2)
    phase_count = _parameter_integer(session, surface_number, 3)
    if zone_count != len(spec.radial_apertures_mm) or aspheric_count != 3 or phase_count != 0:
        raise RevisionR6ZosError(
            f"R6 Binary4 structure mismatch: Nz={zone_count}, Na={aspheric_count}, Np={phase_count}"
        )
    output: list[R4Binary4ZoneReadback] = []
    inner = 0.0
    for zone_number in range(1, zone_count + 1):
        columns = binary4_zone_columns(zone_number, aspheric_count, phase_count)
        outer = _parameter_double(session, surface_number, columns.radial_aperture)
        alpha2, alpha4, alpha6 = (
            _parameter_double(session, surface_number, item) for item in columns.aspheric_terms
        )
        output.append(
            R4Binary4ZoneReadback(
                zone=zone_number,
                r_inner_mm=inner,
                r_outer_mm=outer,
                radius_mm=_parameter_double(session, surface_number, columns.radius),
                conic=_parameter_double(session, surface_number, columns.conic),
                diffraction_order=_parameter_double(
                    session, surface_number, columns.diffraction_order
                ),
                alpha_p2_native=alpha2,
                alpha_p4_native=alpha4,
                alpha_p6_native=alpha6,
            )
        )
        inner = outer
    return tuple(output)


def _validate_zone_replay(
    expected: tuple[R4ZonePrescription, ...],
    actual: tuple[R4Binary4ZoneReadback, ...],
) -> None:
    if len(expected) != len(actual):
        raise RevisionR6ZosError("R6 Binary4 zone count differs after serialization")
    for wanted, observed in zip(expected, actual, strict=True):
        for left, right, label in (
            (wanted.r_outer_mm, observed.r_outer_mm, "boundary"),
            (wanted.radius_mm, observed.radius_mm, "radius"),
            (wanted.conic, observed.conic, "conic"),
            (wanted.alpha_p4_native, observed.alpha_p4_native, "p4"),
            (wanted.alpha_p6_native, observed.alpha_p6_native, "p6"),
        ):
            if abs(float(left) - float(right)) > 1.0e-9:
                raise RevisionR6ZosError(
                    f"R6 Binary4 zone {wanted.zone} {label} replay mismatch: {left} vs {right}"
                )
        if abs(observed.alpha_p2_native) > 1.0e-12:
            raise RevisionR6ZosError("R6 Binary4 native p2 must remain zero")
        if abs(observed.diffraction_order) > 1.0e-12:
            raise RevisionR6ZosError("R6 Binary4 diffraction order must remain zero")


def _degenerate_prescriptions(
    platform_id: str,
    *,
    base_radius_mm: float,
    base_conic: float,
) -> tuple[R4ZonePrescription, ...]:
    spec = binary4_mechanism_spec(platform_id)
    inner = 0.0
    rows: list[R4ZonePrescription] = []
    for index, outer in enumerate(spec.radial_apertures_mm, start=1):
        rows.append(
            R4ZonePrescription(
                zone=index,
                r_inner_mm=inner,
                r_outer_mm=outer,
                radius_mm=base_radius_mm,
                conic=base_conic,
                alpha_p2_native=0.0,
                alpha_p4_native=0.0,
                alpha_p6_native=0.0,
                active=True,
            )
        )
        inner = outer
    return tuple(rows)


def _configure_binary4(
    session: ZosSession,
    platform_id: str,
    prescriptions: tuple[R4ZonePrescription, ...],
    *,
    standard_eye: bool,
) -> None:
    surface_number = _surface_number(platform_id, standard_eye=standard_eye)
    editor = SequentialEditor(session.system, session.zosapi)
    row = editor.surface(surface_number)
    common = (
        float(row.Radius),
        float(row.Conic),
        float(row.Thickness),
        str(row.Material),
        str(row.Comment),
    )
    zones = tuple(
        Binary4Zone(
            radial_aperture=item.r_outer_mm,
            radius=item.radius_mm,
            conic=item.conic,
            diffraction_order=0.0,
            aspheric_terms=(0.0, item.alpha_p4_native, item.alpha_p6_native),
            phase_terms=(),
        )
        for item in prescriptions
    )
    editor.configure_binary4(surface_number, zones)
    editor.set_radius_conic(surface_number, radius_mm=common[0], conic=common[1])
    editor.set_thickness(surface_number, common[2])
    editor.set_material(surface_number, common[3])
    editor.set_comment(surface_number, common[4])
    editor.surface(surface_number).SemiDiameter = IOL_CLEAR_SEMI_DIAMETER_MM


def _build_binary4_model(
    session: ZosSession,
    *,
    source_path: str | Path,
    destination: str | Path,
    base_id: str,
    cornea_id: str,
    platform_id: str,
    optic_state: str,
    prescriptions: tuple[R4ZonePrescription, ...],
    standard_eye: bool,
) -> R6Binary4BuildResult:
    source = Path(source_path)
    if not source.is_file():
        raise RevisionR6ZosError(f"R6 Binary4 source is missing: {source}")
    session.system.LoadFile(str(source.resolve()), False)
    if standard_eye:
        if int(session.system.LDE.NumberOfSurfaces) != 6:
            raise RevisionR6ZosError("R6 standard-eye Binary4 source must have six surfaces")
        session.system.LDE.GetSurfaceAt(3).SemiDiameter = IOL_CLEAR_SEMI_DIAMETER_MM
        session.system.LDE.GetSurfaceAt(4).SemiDiameter = IOL_CLEAR_SEMI_DIAMETER_MM
    else:
        apply_revision_to_full_eye(session, base_id, pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM)
    _configure_binary4(
        session,
        platform_id,
        prescriptions,
        standard_eye=standard_eye,
    )
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    SequentialEditor(session.system, session.zosapi).save_as(output)
    session.system.LoadFile(str(output.resolve()), False)
    if not standard_eye:
        apply_revision_to_full_eye(session, base_id, pupil_diameter_mm=R6_FOCUS_PUPIL_DIAMETER_MM)
    zones = _read_binary4_zones(session, platform_id, standard_eye=standard_eye)
    _validate_zone_replay(prescriptions, zones)
    boundaries = _boundary_diagnostics(
        binary4_mechanism_spec(platform_id).radial_apertures_mm,
        prescriptions,
    )
    if any(abs(item.c0_error_mm) > 1.0e-10 for item in boundaries):
        raise RevisionR6ZosError("R6 Binary4 prescription lost C0 continuity")
    minimum = _minimum_radicand(prescriptions)
    if minimum <= 0.0:
        raise RevisionR6ZosError("R6 Binary4 prescription has non-positive conic radicand")
    return R6Binary4BuildResult(
        base_id=base_id,
        cornea_id=cornea_id,
        platform_id=platform_id,
        optic_state=optic_state,
        surface_number=_surface_number(platform_id, standard_eye=standard_eye),
        path=str(output.resolve()),
        zones=zones,
        boundaries=boundaries,
        minimum_conic_radicand=minimum,
    )


def _standard_analytical_carrier(
    session: ZosSession,
    standard_eye_path: str | Path,
    carrier: R6CarrierSolveResult,
    destination: str | Path,
) -> Path:
    build_physical_carrier_in_standard_eye(
        session,
        standard_eye_path,
        radius_ant_mm=carrier.radius_ant_mm,
        radius_post_mm=carrier.radius_post_mm,
        q=carrier.q_ant,
    )
    session.system.LDE.GetSurfaceAt(3).SemiDiameter = IOL_CLEAR_SEMI_DIAMETER_MM
    session.system.LDE.GetSurfaceAt(4).SemiDiameter = IOL_CLEAR_SEMI_DIAMETER_MM
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    SequentialEditor(session.system, session.zosapi).save_as(output)
    return output


def _ray_health(
    session: ZosSession,
    path: str | Path,
    *,
    base_id: str,
    pupil_diameter_mm: float,
) -> R6RayHealth:
    source = Path(path)
    session.system.LoadFile(str(source.resolve()), False)
    apply_revision_to_full_eye(session, base_id, pupil_diameter_mm=pupil_diameter_mm)
    image_surface = int(session.system.LDE.NumberOfSurfaces) - 1
    tool = session.system.Tools.OpenBatchRayTrace()
    try:
        samples = (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0)
        rays = tool.CreateNormUnpol(
            len(samples),
            session.zosapi.Tools.RayTrace.RaysType.Real,
            image_surface,
        )
        rays.ClearData()
        opd_enum = session.zosapi.Tools.RayTrace.OPDMode
        opd_none = getattr(opd_enum, "None", getattr(opd_enum, "None_", None))
        if opd_none is None:
            raise RevisionR6ZosError("installed API exposes no OPDMode.None")
        for py in samples:
            rays.AddRay(1, 0.0, 0.0, 0.0, py, opd_none)
        tool.RunAndWaitForCompletion()
        rays.StartReadingResults()
        failures: list[dict[str, object]] = []
        for index, py in enumerate(samples):
            values = tuple(rays.ReadNextResult())
            success = bool(values[0])
            error = int(values[2])
            vignette = int(values[3])
            if not success or error != 0 or vignette != 0:
                failures.append(
                    {
                        "ray": index,
                        "py": py,
                        "success": success,
                        "error": error,
                        "vignette": vignette,
                    }
                )
        return R6RayHealth(pupil_diameter_mm, not failures, tuple(failures))
    finally:
        close = getattr(tool, "Close", None)
        if callable(close):
            close()


def build_and_validate_r6_carrier(
    session: ZosSession,
    standard_eye_path: str | Path,
    carrier: R6CarrierSolveResult,
    output_dir: str | Path,
    *,
    full_standard_audit: bool,
) -> R6CarrierValidationResult:
    platform = carrier.platform_id
    root = Path(output_dir) / carrier.carrier_id
    root.mkdir(parents=True, exist_ok=True)
    role = binary4_mechanism_spec(platform).surface_role
    actual_base_radius = carrier.radius_ant_mm if role == "anterior" else carrier.radius_post_mm
    actual_base_conic = carrier.q_ant if role == "anterior" else carrier.q_post
    mono_prescriptions = _degenerate_prescriptions(
        platform,
        base_radius_mm=actual_base_radius,
        base_conic=actual_base_conic,
    )
    edof_prescriptions = r5_2_zones_for_carrier(
        platform,
        base_radius_mm=actual_base_radius,
        base_conic=actual_base_conic,
    )

    actual_mono = _build_binary4_model(
        session,
        source_path=carrier.path,
        destination=root / "ACTUAL_BINARY4_MONO.zmx",
        base_id=carrier.base_id,
        cornea_id=carrier.cornea_id,
        platform_id=platform,
        optic_state="MONO",
        prescriptions=mono_prescriptions,
        standard_eye=False,
    )
    actual_edof = _build_binary4_model(
        session,
        source_path=carrier.path,
        destination=root / "ACTUAL_BINARY4_EDOF.zmx",
        base_id=carrier.base_id,
        cornea_id=carrier.cornea_id,
        platform_id=platform,
        optic_state="EDOF",
        prescriptions=edof_prescriptions,
        standard_eye=False,
    )

    standard_analytical = _standard_analytical_carrier(
        session,
        standard_eye_path,
        carrier,
        root / "STD_ANALYTICAL_MONO.zmx",
    )
    standard_mono = _build_binary4_model(
        session,
        source_path=standard_analytical,
        destination=root / "STD_BINARY4_MONO.zmx",
        base_id=carrier.base_id,
        cornea_id=carrier.cornea_id,
        platform_id=platform,
        optic_state="MONO",
        prescriptions=mono_prescriptions,
        standard_eye=True,
    )
    standard_edof = _build_binary4_model(
        session,
        source_path=standard_analytical,
        destination=root / "STD_BINARY4_EDOF.zmx",
        base_id=carrier.base_id,
        cornea_id=carrier.cornea_id,
        platform_id=platform,
        optic_state="EDOF",
        prescriptions=edof_prescriptions,
        standard_eye=True,
    )

    mechanism = read_r4_mechanism(
        session,
        standard_mono.path,
        standard_edof.path,
        platform,
    )
    rad_power = (
        read_rad_power_profile(session, standard_mono.path, standard_edof.path)
        if platform == PlatformId.RAD.value
        else None
    )
    mono_health = tuple(
        _ray_health(
            session,
            actual_mono.path,
            base_id=carrier.base_id,
            pupil_diameter_mm=pupil,
        )
        for pupil in R6_RAY_HEALTH_PUPILS_MM
    )
    edof_health = tuple(
        _ray_health(
            session,
            actual_edof.path,
            base_id=carrier.base_id,
            pupil_diameter_mm=pupil,
        )
        for pupil in R6_RAY_HEALTH_PUPILS_MM
    )
    if not all(item.passed for item in (*mono_health, *edof_health)):
        raise RevisionR6ZosError(f"R6 {carrier.carrier_id} actual-eye ray health failed")

    audit_mono = audit_r4_model(session, standard_mono.path) if full_standard_audit else None
    audit_edof = audit_r4_model(session, standard_edof.path) if full_standard_audit else None
    return R6CarrierValidationResult(
        carrier=carrier,
        actual_mono=actual_mono,
        actual_edof=actual_edof,
        standard_mono=standard_mono,
        standard_edof=standard_edof,
        standard_mechanism=mechanism,
        rad_power_readback=rad_power,
        actual_mono_ray_health=mono_health,
        actual_edof_ray_health=edof_health,
        full_standard_audit_mono=audit_mono,
        full_standard_audit_edof=audit_edof,
    )
