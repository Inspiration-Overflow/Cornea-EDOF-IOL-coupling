from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path

from .carrier_q_zos import (
    CarrierQSolution,
    build_physical_carrier_in_standard_eye,
    measure_zero_hoa_reference,
    solve_q_for_platform,
)
from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .domain import PlatformId
from .grid_sag_residual import apply_grid_sag_residual, write_grid_sag_dat
from .model_revision import IOL_CLEAR_SEMI_DIAMETER_MM, binary4_mechanism_spec
from .residual_payload import (
    RadialResidualCandidate,
    build_hoa_residual_candidate,
    build_rad_residual_candidate,
    build_wfs_residual_candidate,
)
from .residual_profiles import (
    fit_piston_and_global_defocus,
    hoa_raw_opd_um,
    rad_raw_opd_um,
    rad_relative_power_d,
    wfs_raw_opd_um,
)
from .revision_r4_fit import (
    R4_MECHANISM_MAX_FRACTION_TARGET,
    R4_MECHANISM_RMS_FRACTION_TARGET,
    R4_REPRESENTATIVE_POWER_D,
    R4MechanismFitResult,
    R4ZonePrescription,
    fit_r4_mechanism,
    representative_radius_mm,
)
from .standard_eye import CORNEAL_SA_PUPIL_MM, _quick_focus_wavefront
from .zos import (
    Binary4Zone,
    MfeFullHoaRunner,
    MfeMtfGridRunner,
    MfeMtfGridSettings,
    MfePowpRunner,
    MfePowpSettings,
    SequentialEditor,
    ZosSession,
)
from .zos.primitives import binary4_zone_columns

R4_MTF_FREQUENCIES_CYC_PER_MM = tuple(float(value) for value in range(0, 101, 5))
R4_MTF_GRID_SIZE = 128
R4_READBACK_STEP_MM = 0.025
R4_READBACK_RADIUS_MM = 3.0
R4_LOW_ORDER_RADIUS_MM = 2.575
R4_POWP_PX = tuple(index / 10.0 for index in range(11))
R4_READBACK_FIDELITY_SLACK = 1.25


class RevisionR4ZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class R4Binary4ZoneReadback:
    zone: int
    r_inner_mm: float
    r_outer_mm: float
    radius_mm: float
    conic: float
    diffraction_order: float
    alpha_p2_native: float
    alpha_p4_native: float
    alpha_p6_native: float


@dataclass(frozen=True, slots=True)
class R4AnalyticalCarrierResult:
    platform_id: str
    representative_power_d: float
    radius_ant_mm: float
    radius_post_mm: float
    q_ant: float
    q_post: float
    path: str
    q_solution: CarrierQSolution


@dataclass(frozen=True, slots=True)
class R4Binary4BuildResult:
    platform_id: str
    optic_state: str
    surface_number: int
    path: str
    zones: tuple[R4Binary4ZoneReadback, ...]


@dataclass(frozen=True, slots=True)
class R4MechanismReadback:
    platform_id: str
    radii_mm: tuple[float, ...]
    residual_opd_um: tuple[float, ...]
    target_raw_opd_um: tuple[float, ...]
    piston_alignment_um: float
    rms_opd_error_um: float
    max_abs_opd_error_um: float
    target_peak_to_peak_um: float
    rms_fraction_of_target: float
    max_fraction_of_target: float
    engineering_target_passed: bool
    low_order_piston_um: float
    low_order_global_defocus_d: float


@dataclass(frozen=True, slots=True)
class R4MtfSeries:
    operand_type: str
    frequencies_cyc_per_mm: tuple[float, ...]
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class R4OpticalAudit:
    path: str
    best_focus_shift_mm: float
    c40_um: float
    c60_um: float
    hoa_rms_um: float
    mtf: tuple[R4MtfSeries, ...]
    ray_health_passed: bool
    ray_health_failures: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class R4PowpPoint:
    px: float
    mono_radius_mm: float
    edof_radius_mm: float
    mono_power_d: float
    edof_power_d: float
    relative_power_d: float
    target_relative_power_d: float
    error_d: float


@dataclass(frozen=True, slots=True)
class R4RadPowerReadback:
    points: tuple[R4PowpPoint, ...]
    rms_error_d: float
    max_abs_error_d: float


@dataclass(frozen=True, slots=True)
class R4PlatformPilotResult:
    platform_id: str
    analytical: R4AnalyticalCarrierResult
    fit: R4MechanismFitResult
    binary4_mono: R4Binary4BuildResult
    binary4_edof: R4Binary4BuildResult
    grid_sag_path: str
    mechanism_readback: R4MechanismReadback
    rad_power_readback: R4RadPowerReadback | None
    mono_audit: R4OpticalAudit
    binary4_edof_audit: R4OpticalAudit
    grid_sag_edof_audit: R4OpticalAudit


def _platform(value: str) -> str:
    try:
        return PlatformId(value).value
    except ValueError as exc:
        raise ValueError(f"unsupported R4 platform: {value}") from exc


def _candidate(platform_id: str) -> RadialResidualCandidate:
    builders = {
        PlatformId.WFS.value: build_wfs_residual_candidate,
        PlatformId.RAD.value: build_rad_residual_candidate,
        PlatformId.HOA.value: build_hoa_residual_candidate,
    }
    candidate = builders[_platform(platform_id)]()
    candidate.validate()
    return candidate


def _raw_target(platform_id: str, radius_mm: float) -> float:
    platform = _platform(platform_id)
    if platform == PlatformId.WFS.value:
        return wfs_raw_opd_um(radius_mm)
    if platform == PlatformId.RAD.value:
        return rad_raw_opd_um(radius_mm)
    if platform == PlatformId.HOA.value:
        return hoa_raw_opd_um(radius_mm)
    raise AssertionError(platform)


def _surface_number(platform_id: str) -> int:
    spec = binary4_mechanism_spec(platform_id)
    return 3 if spec.surface_role == "anterior" else 4


def _set_epd6(session: ZosSession) -> None:
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = CORNEAL_SA_PUPIL_MM


def _require_standard_carrier(session: ZosSession) -> None:
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 6:
        raise RevisionR4ZosError(
            f"R4 standard-eye carrier expects 6 surfaces, got {int(lde.NumberOfSurfaces)}"
        )
    ant = lde.GetSurfaceAt(3)
    post = lde.GetSurfaceAt(4)
    if float(ant.Radius) <= 0.0 or float(post.Radius) >= 0.0:
        raise RevisionR4ZosError("R4 carrier radii have unexpected signs")
    if abs(float(ant.Radius) + float(post.Radius)) > 1.0e-8:
        raise RevisionR4ZosError("R4 carrier lost symmetric-biconvex base radii")
    if abs(float(post.Conic)) > 1.0e-10:
        raise RevisionR4ZosError("R4 carrier posterior conic must remain zero")


def solve_r4_platform_qs(
    session: ZosSession,
    standard_eye_path: str | Path,
) -> dict[str, CarrierQSolution]:
    radius = representative_radius_mm()
    zero_reference = measure_zero_hoa_reference(
        session,
        standard_eye_path,
        radius_ant_mm=radius,
        radius_post_mm=-radius,
    )
    output: dict[str, CarrierQSolution] = {}
    for platform in PlatformId:
        solution = solve_q_for_platform(
            session,
            standard_eye_path,
            platform_id=platform.value,
            source_power_d=R4_REPRESENTATIVE_POWER_D,
            radius_ant_mm=radius,
            radius_post_mm=-radius,
            zero_reference=zero_reference,
        )
        if not solution.target_passed:
            raise RevisionR4ZosError(
                f"R4 {platform.value} +20 D carrier Q solve missed the frozen SA target"
            )
        output[platform.value] = solution
    return output


def build_r4_analytical_carrier(
    session: ZosSession,
    standard_eye_path: str | Path,
    platform_id: str,
    q_solution: CarrierQSolution,
    destination: str | Path,
) -> R4AnalyticalCarrierResult:
    platform = _platform(platform_id)
    radius = representative_radius_mm()
    if q_solution.platform_id != platform:
        raise RevisionR4ZosError("R4 Q solution platform identity mismatch")
    if abs(q_solution.source_power_d - R4_REPRESENTATIVE_POWER_D) > 1.0e-9:
        raise RevisionR4ZosError("R4 Q solution is not the representative +20 D carrier")
    build_physical_carrier_in_standard_eye(
        session,
        standard_eye_path,
        radius_ant_mm=radius,
        radius_post_mm=-radius,
        q=q_solution.q,
    )
    lde = session.system.LDE
    lde.GetSurfaceAt(3).SemiDiameter = IOL_CLEAR_SEMI_DIAMETER_MM
    lde.GetSurfaceAt(4).SemiDiameter = IOL_CLEAR_SEMI_DIAMETER_MM
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    session.system.SaveAs(str(output.resolve()))
    session.system.LoadFile(str(output.resolve()), False)
    _set_epd6(session)
    _require_standard_carrier(session)
    ant = session.system.LDE.GetSurfaceAt(3)
    post = session.system.LDE.GetSurfaceAt(4)
    if abs(float(ant.Conic) - q_solution.q) > 1.0e-10:
        raise RevisionR4ZosError("R4 analytical carrier anterior Q changed on replay")
    if (
        abs(float(ant.SemiDiameter) - IOL_CLEAR_SEMI_DIAMETER_MM) > 1.0e-10
        or abs(float(post.SemiDiameter) - IOL_CLEAR_SEMI_DIAMETER_MM) > 1.0e-10
    ):
        raise RevisionR4ZosError("R4 analytical carrier IOL clear semi-diameter changed")
    return R4AnalyticalCarrierResult(
        platform_id=platform,
        representative_power_d=R4_REPRESENTATIVE_POWER_D,
        radius_ant_mm=float(ant.Radius),
        radius_post_mm=float(post.Radius),
        q_ant=float(ant.Conic),
        q_post=float(post.Conic),
        path=str(output.resolve()),
        q_solution=q_solution,
    )


def _parameter_double(
    session: ZosSession,
    surface_number: int,
    parameter_number: int,
) -> float:
    column = getattr(session.zosapi.Editors.LDE.SurfaceColumn, f"Par{parameter_number}")
    return float(
        session.system.LDE.GetSurfaceAt(surface_number).GetSurfaceCell(column).DoubleValue
    )


def _parameter_integer(
    session: ZosSession,
    surface_number: int,
    parameter_number: int,
) -> int:
    column = getattr(session.zosapi.Editors.LDE.SurfaceColumn, f"Par{parameter_number}")
    return int(
        session.system.LDE.GetSurfaceAt(surface_number).GetSurfaceCell(column).IntegerValue
    )


def read_r4_binary4_zones(
    session: ZosSession,
    platform_id: str,
) -> tuple[R4Binary4ZoneReadback, ...]:
    platform = _platform(platform_id)
    spec = binary4_mechanism_spec(platform)
    surface_number = _surface_number(platform)
    row = session.system.LDE.GetSurfaceAt(surface_number)
    type_name = str(getattr(row, "TypeName", "") or "")
    get_type = getattr(row, "GetType", None)
    fallback = str(get_type()) if callable(get_type) else ""
    if "binary" not in type_name.casefold() and "binary" not in fallback.casefold():
        raise RevisionR4ZosError("R4 pilot surface did not replay as Binary 4")
    zone_count = _parameter_integer(session, surface_number, 1)
    aspheric_count = _parameter_integer(session, surface_number, 2)
    phase_count = _parameter_integer(session, surface_number, 3)
    if (
        zone_count != len(spec.radial_apertures_mm)
        or aspheric_count != 3
        or phase_count != 0
    ):
        raise RevisionR4ZosError(
            f"R4 Binary4 structural readback mismatch: Nz={zone_count}, Na={aspheric_count}, Np={phase_count}"
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


def _configure_binary4_from_prescriptions(
    session: ZosSession,
    platform_id: str,
    prescriptions: tuple[R4ZonePrescription, ...],
) -> None:
    platform = _platform(platform_id)
    spec = binary4_mechanism_spec(platform)
    if len(prescriptions) != len(spec.radial_apertures_mm):
        raise RevisionR4ZosError("R4 fit zone count differs from platform topology")
    surface_number = _surface_number(platform)
    editor = SequentialEditor(session.system, session.zosapi)
    row = editor.surface(surface_number)
    common_radius = float(row.Radius)
    common_conic = float(row.Conic)
    common_thickness = float(row.Thickness)
    common_material = str(row.Material)
    common_comment = str(row.Comment)
    zones = tuple(
        Binary4Zone(
            radial_aperture=prescription.r_outer_mm,
            radius=prescription.radius_mm,
            conic=prescription.conic,
            diffraction_order=0.0,
            aspheric_terms=(
                0.0,
                prescription.alpha_p4_native,
                prescription.alpha_p6_native,
            ),
            phase_terms=(),
        )
        for prescription in prescriptions
    )
    editor.configure_binary4(surface_number, zones)
    # Keep transparent common-row audit values without changing zone geometry.
    editor.set_radius_conic(surface_number, radius_mm=common_radius, conic=common_conic)
    editor.set_thickness(surface_number, common_thickness)
    editor.set_material(surface_number, common_material)
    editor.set_comment(surface_number, common_comment)
    editor.surface(surface_number).SemiDiameter = IOL_CLEAR_SEMI_DIAMETER_MM


def _degenerate_prescriptions(
    platform_id: str,
    *,
    base_radius_mm: float,
    base_conic: float,
) -> tuple[R4ZonePrescription, ...]:
    spec = binary4_mechanism_spec(platform_id)
    inner = 0.0
    output: list[R4ZonePrescription] = []
    for index, outer in enumerate(spec.radial_apertures_mm, start=1):
        output.append(
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
    return tuple(output)


def _validate_zone_replay(
    expected: tuple[R4ZonePrescription, ...],
    actual: tuple[R4Binary4ZoneReadback, ...],
) -> None:
    if len(expected) != len(actual):
        raise RevisionR4ZosError("R4 Binary4 zone replay count differs")
    for wanted, observed in zip(expected, actual, strict=True):
        values = (
            (wanted.r_outer_mm, observed.r_outer_mm, "boundary"),
            (wanted.radius_mm, observed.radius_mm, "radius"),
            (wanted.conic, observed.conic, "conic"),
            (wanted.alpha_p4_native, observed.alpha_p4_native, "p4"),
            (wanted.alpha_p6_native, observed.alpha_p6_native, "p6"),
        )
        for left, right, label in values:
            if abs(float(left) - float(right)) > 1.0e-9:
                raise RevisionR4ZosError(
                    f"R4 Binary4 zone {wanted.zone} {label} replay mismatch: {left} vs {right}"
                )
        if abs(observed.alpha_p2_native) > 1.0e-12:
            raise RevisionR4ZosError("R4 Binary4 native p2 must remain zero")
        if abs(observed.diffraction_order) > 1.0e-12:
            raise RevisionR4ZosError("R4 Binary4 diffraction order must remain zero")


def build_r4_binary4_mono(
    session: ZosSession,
    analytical_path: str | Path,
    platform_id: str,
    destination: str | Path,
) -> R4Binary4BuildResult:
    platform = _platform(platform_id)
    source = Path(analytical_path)
    if not source.is_file():
        raise RevisionR4ZosError(f"R4 analytical carrier is missing: {source}")
    session.system.LoadFile(str(source.resolve()), False)
    _set_epd6(session)
    _require_standard_carrier(session)
    surface_number = _surface_number(platform)
    row = session.system.LDE.GetSurfaceAt(surface_number)
    prescriptions = _degenerate_prescriptions(
        platform,
        base_radius_mm=float(row.Radius),
        base_conic=float(row.Conic),
    )
    _configure_binary4_from_prescriptions(session, platform, prescriptions)
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    session.system.SaveAs(str(output.resolve()))
    session.system.LoadFile(str(output.resolve()), False)
    _set_epd6(session)
    zones = read_r4_binary4_zones(session, platform)
    _validate_zone_replay(prescriptions, zones)
    return R4Binary4BuildResult(
        platform_id=platform,
        optic_state="MONO",
        surface_number=surface_number,
        path=str(output.resolve()),
        zones=zones,
    )


def build_r4_binary4_edof(
    session: ZosSession,
    analytical_path: str | Path,
    fit: R4MechanismFitResult,
    destination: str | Path,
) -> R4Binary4BuildResult:
    platform = _platform(fit.platform_id)
    source = Path(analytical_path)
    if not source.is_file():
        raise RevisionR4ZosError(f"R4 analytical carrier is missing: {source}")
    session.system.LoadFile(str(source.resolve()), False)
    _set_epd6(session)
    _require_standard_carrier(session)
    prescriptions = fit.selected.zones
    # Build EDoF directly from the same analytical Standard carrier as MONO. Reconfiguring
    # an already-serialized Binary4 surface can preserve ParN readback while leaving the
    # automatic inter-zone sag-offset state inconsistent with the final prescriptions.
    _configure_binary4_from_prescriptions(session, platform, prescriptions)
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    session.system.SaveAs(str(output.resolve()))
    session.system.LoadFile(str(output.resolve()), False)
    _set_epd6(session)
    zones = read_r4_binary4_zones(session, platform)
    _validate_zone_replay(prescriptions, zones)
    return R4Binary4BuildResult(
        platform_id=platform,
        optic_state="EDOF",
        surface_number=_surface_number(platform),
        path=str(output.resolve()),
        zones=zones,
    )


def _ssag_mm(session: ZosSession, surface_number: int, radius_mm: float) -> float:
    operand_type = getattr(session.zosapi.Editors.MFE.MeritOperandType, "SSAG", None)
    if operand_type is None:
        raise RevisionR4ZosError("installed MeritOperandType exposes no SSAG member")
    get_value = getattr(session.system.MFE, "GetOperandValue", None)
    if not callable(get_value):
        raise RevisionR4ZosError("installed MFE exposes no GetOperandValue")
    value = float(
        get_value(
            operand_type,
            int(surface_number),
            0,
            float(radius_mm),
            0.0,
            0,
            0,
            0,
            0,
        )
    )
    if not math.isfinite(value):
        raise RevisionR4ZosError(f"R4 SSAG returned non-finite sag at r={radius_mm:g} mm")
    return value


def _zone_equal_weights(platform_id: str, radii: tuple[float, ...]) -> tuple[float, ...]:
    apertures = binary4_mechanism_spec(platform_id).radial_apertures_mm
    zone_indices = [
        next(
            (index for index, outer in enumerate(apertures) if radius <= outer + 1.0e-12),
            len(apertures) - 1,
        )
        for radius in radii
    ]
    weights = [0.0] * len(radii)
    for index in range(len(apertures)):
        count = zone_indices.count(index)
        if count < 1:
            raise RevisionR4ZosError(f"R4 readback did not sample zone {index + 1}")
        for sample, zone_index in enumerate(zone_indices):
            if zone_index == index:
                weights[sample] = 1.0 / (len(apertures) * count)
    total = math.fsum(weights)
    return tuple(value / total for value in weights)


def read_r4_mechanism(
    session: ZosSession,
    mono_path: str | Path,
    edof_path: str | Path,
    platform_id: str,
) -> R4MechanismReadback:
    platform = _platform(platform_id)
    sample_count = round(R4_READBACK_RADIUS_MM / R4_READBACK_STEP_MM) + 1
    radii = tuple(index * R4_READBACK_STEP_MM for index in range(sample_count))
    surface_number = _surface_number(platform)
    session.system.LoadFile(str(Path(mono_path).resolve()), False)
    _set_epd6(session)
    mono_sag = tuple(_ssag_mm(session, surface_number, radius) for radius in radii)
    session.system.LoadFile(str(Path(edof_path).resolve()), False)
    _set_epd6(session)
    edof_sag = tuple(_ssag_mm(session, surface_number, radius) for radius in radii)
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    index_step = (
        scaffold.refractive_index - scaffold.surrounding_index
        if binary4_mechanism_spec(platform).surface_role == "anterior"
        else scaffold.surrounding_index - scaffold.refractive_index
    )
    residual_opd = tuple(
        (right - left) * 1000.0 * index_step
        for left, right in zip(mono_sag, edof_sag, strict=True)
    )
    target = tuple(_raw_target(platform, radius) for radius in radii)
    weights = _zone_equal_weights(platform, radii)
    raw_difference = tuple(
        actual - wanted for actual, wanted in zip(residual_opd, target, strict=True)
    )
    piston = math.fsum(
        weight * value for weight, value in zip(weights, raw_difference, strict=True)
    )
    difference = tuple(value - piston for value in raw_difference)
    rms = math.sqrt(
        math.fsum(
            weight * value * value
            for weight, value in zip(weights, difference, strict=True)
        )
    )
    maximum = max(abs(value) for value in difference)
    target_peak_to_peak = max(target) - min(target)
    if target_peak_to_peak <= 0.0:
        raise RevisionR4ZosError("R4 mechanism target has zero peak-to-peak OPD")

    low_order_pairs = [
        (radius, opd)
        for radius, opd in zip(radii, residual_opd, strict=True)
        if radius <= R4_LOW_ORDER_RADIUS_MM + 1.0e-12
    ]
    low_order = fit_piston_and_global_defocus(
        tuple(pair[0] for pair in low_order_pairs),
        tuple(pair[1] for pair in low_order_pairs),
    )
    rms_fraction = rms / target_peak_to_peak
    max_fraction = maximum / target_peak_to_peak
    return R4MechanismReadback(
        platform_id=platform,
        radii_mm=radii,
        residual_opd_um=residual_opd,
        target_raw_opd_um=target,
        piston_alignment_um=piston,
        rms_opd_error_um=rms,
        max_abs_opd_error_um=maximum,
        target_peak_to_peak_um=target_peak_to_peak,
        rms_fraction_of_target=rms_fraction,
        max_fraction_of_target=max_fraction,
        engineering_target_passed=(
            rms_fraction
            <= R4_MECHANISM_RMS_FRACTION_TARGET * R4_READBACK_FIDELITY_SLACK
            and max_fraction
            <= R4_MECHANISM_MAX_FRACTION_TARGET * R4_READBACK_FIDELITY_SLACK
        ),
        low_order_piston_um=low_order.piston_um,
        low_order_global_defocus_d=low_order.global_defocus_d,
    )


def _ray_health(session: ZosSession) -> tuple[bool, tuple[dict[str, object], ...]]:
    _set_epd6(session)
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
            raise RevisionR4ZosError("installed API exposes no OPDMode.None")
        for py in samples:
            rays.AddRay(1, 0.0, 0.0, 0.0, py, opd_none)
        tool.RunAndWaitForCompletion()
        rays.StartReadingResults()
        failures: list[dict[str, object]] = []
        for index in range(len(samples)):
            values = tuple(rays.ReadNextResult())
            success = bool(values[0])
            error = int(values[2])
            vignette = int(values[3])
            if not success or error != 0 or vignette != 0:
                failures.append(
                    {
                        "ray": index,
                        "success": success,
                        "error": error,
                        "vignette": vignette,
                    }
                )
        return not failures, tuple(failures)
    finally:
        close = getattr(tool, "Close", None)
        if callable(close):
            close()


def audit_r4_model(session: ZosSession, path: str | Path) -> R4OpticalAudit:
    model = Path(path)
    session.system.LoadFile(str(model.resolve()), False)
    _set_epd6(session)
    passed, failures = _ray_health(session)
    pre_image = session.system.LDE.GetSurfaceAt(4)
    fixed = float(pre_image.Thickness)
    try:
        _quick_focus_wavefront(session)
        best = float(pre_image.Thickness)
        hoa = MfeFullHoaRunner(session.system, session.zosapi).run()
        mtf: list[R4MtfSeries] = []
        for operand_type in ("MTFA", "MTFS", "MTFT"):
            result = MfeMtfGridRunner(session.system, session.zosapi).run(
                MfeMtfGridSettings(
                    frequencies_cyc_per_mm=R4_MTF_FREQUENCIES_CYC_PER_MM,
                    sampling_grid_size=R4_MTF_GRID_SIZE,
                    operand_type=operand_type,
                )
            )
            mtf.append(
                R4MtfSeries(
                    operand_type=operand_type,
                    frequencies_cyc_per_mm=result.frequencies_cyc_per_mm,
                    values=result.values,
                )
            )
        return R4OpticalAudit(
            path=str(model.resolve()),
            best_focus_shift_mm=best - fixed,
            c40_um=hoa.c40_um,
            c60_um=hoa.c60_um,
            hoa_rms_um=hoa.hoa_rms_um,
            mtf=tuple(mtf),
            ray_health_passed=passed,
            ray_health_failures=failures,
        )
    finally:
        pre_image.Thickness = fixed


def _ray_radius_at_surface(
    session: ZosSession,
    surface_number: int,
    px: float,
) -> float:
    tool = session.system.Tools.OpenBatchRayTrace()
    try:
        rays = tool.CreateNormUnpol(
            1,
            session.zosapi.Tools.RayTrace.RaysType.Real,
            surface_number,
        )
        rays.ClearData()
        opd_enum = session.zosapi.Tools.RayTrace.OPDMode
        opd_none = getattr(opd_enum, "None", getattr(opd_enum, "None_", None))
        if opd_none is None:
            raise RevisionR4ZosError("installed API exposes no OPDMode.None")
        rays.AddRay(1, 0.0, 0.0, float(px), 0.0, opd_none)
        tool.RunAndWaitForCompletion()
        rays.StartReadingResults()
        values = tuple(rays.ReadNextResult())
        if len(values) < 6 or not bool(values[0]) or int(values[2]) != 0:
            raise RevisionR4ZosError(f"R4 POWP ray trace failed at Px={px:g}")
        x = float(values[4])
        y = float(values[5])
        if not math.isfinite(x) or not math.isfinite(y):
            raise RevisionR4ZosError(f"R4 POWP ray intercept is non-finite at Px={px:g}")
        return math.hypot(x, y)
    finally:
        close = getattr(tool, "Close", None)
        if callable(close):
            close()


def _powp_curve(
    session: ZosSession,
    path: str | Path,
    surface_number: int,
) -> tuple[tuple[float, float, float], ...]:
    session.system.LoadFile(str(Path(path).resolve()), False)
    _set_epd6(session)
    runner = MfePowpRunner(session.system, session.zosapi)
    rows: list[tuple[float, float, float]] = []
    for px in R4_POWP_PX:
        radius = _ray_radius_at_surface(session, surface_number, px)
        power = runner.run(MfePowpSettings(surface=surface_number, px=px)).power_d
        rows.append((px, radius, power))
    return tuple(rows)


def read_rad_power_profile(
    session: ZosSession,
    mono_path: str | Path,
    edof_path: str | Path,
) -> R4RadPowerReadback:
    surface_number = _surface_number(PlatformId.RAD.value)
    mono = _powp_curve(session, mono_path, surface_number)
    edof = _powp_curve(session, edof_path, surface_number)
    points: list[R4PowpPoint] = []
    errors: list[float] = []
    for left, right in zip(mono, edof, strict=True):
        px_l, radius_l, power_l = left
        px_r, radius_r, power_r = right
        if abs(px_l - px_r) > 1.0e-12:
            raise RevisionR4ZosError("R4 POWP MONO/EDOF Px grids differ")
        relative = power_r - power_l
        target = rad_relative_power_d(radius_r)
        error = relative - target
        errors.append(error)
        points.append(
            R4PowpPoint(
                px=px_l,
                mono_radius_mm=radius_l,
                edof_radius_mm=radius_r,
                mono_power_d=power_l,
                edof_power_d=power_r,
                relative_power_d=relative,
                target_relative_power_d=target,
                error_d=error,
            )
        )
    rms = math.sqrt(math.fsum(value * value for value in errors) / len(errors))
    return R4RadPowerReadback(
        points=tuple(points),
        rms_error_d=rms,
        max_abs_error_d=max(abs(value) for value in errors),
    )


def build_r4_grid_sag_comparator(
    session: ZosSession,
    analytical_path: str | Path,
    platform_id: str,
    output_dir: str | Path,
) -> Path:
    platform = _platform(platform_id)
    root = Path(output_dir)
    candidate = _candidate(platform)
    dat_path = root / f"R4_GRID_SAG_{platform}.DAT"
    write_grid_sag_dat(candidate, dat_path)
    destination = root / f"R4_GRID_SAG_EDOF_{platform}.zmx"
    apply_grid_sag_residual(session, analytical_path, candidate, dat_path, destination)
    return destination


def run_r4_platform_pilot(
    session: ZosSession,
    standard_eye_path: str | Path,
    platform_id: str,
    q_solution: CarrierQSolution,
    output_dir: str | Path,
) -> R4PlatformPilotResult:
    platform = _platform(platform_id)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    analytical_path = root / f"R4_ANALYTICAL_MONO_{platform}.zmx"
    mono_path = root / f"R4_BINARY4_MONO_{platform}.zmx"
    edof_path = root / f"R4_BINARY4_EDOF_{platform}.zmx"

    analytical = build_r4_analytical_carrier(
        session,
        standard_eye_path,
        platform,
        q_solution,
        analytical_path,
    )
    surface_number = _surface_number(platform)
    base_radius = (
        analytical.radius_ant_mm if surface_number == 3 else analytical.radius_post_mm
    )
    base_conic = analytical.q_ant if surface_number == 3 else analytical.q_post
    fit = fit_r4_mechanism(
        platform,
        base_radius_mm=base_radius,
        base_conic=base_conic,
    )
    binary4_mono = build_r4_binary4_mono(session, analytical_path, platform, mono_path)
    binary4_edof = build_r4_binary4_edof(session, analytical_path, fit, edof_path)
    mechanism = read_r4_mechanism(session, mono_path, edof_path, platform)
    if fit.engineering_target_passed and not mechanism.engineering_target_passed:
        raise RevisionR4ZosError(
            f"R4 {platform} serialized Binary4 readback lost the fitted mechanism fidelity"
        )

    grid_sag_path = build_r4_grid_sag_comparator(
        session,
        analytical_path,
        platform,
        root,
    )
    rad_power = (
        read_rad_power_profile(session, mono_path, edof_path)
        if platform == PlatformId.RAD.value
        else None
    )
    return R4PlatformPilotResult(
        platform_id=platform,
        analytical=analytical,
        fit=fit,
        binary4_mono=binary4_mono,
        binary4_edof=binary4_edof,
        grid_sag_path=str(grid_sag_path.resolve()),
        mechanism_readback=mechanism,
        rad_power_readback=rad_power,
        mono_audit=audit_r4_model(session, mono_path),
        binary4_edof_audit=audit_r4_model(session, edof_path),
        grid_sag_edof_audit=audit_r4_model(session, grid_sag_path),
    )


def r4_platform_summary(result: R4PlatformPilotResult) -> dict[str, object]:
    """Return a JSON-ready compact decision summary without discarding raw dataclasses."""

    return {
        "platform_id": result.platform_id,
        "representative_power_d": result.analytical.representative_power_d,
        "q_ant": result.analytical.q_ant,
        "selected_complexity": result.fit.selected_complexity,
        "fit_engineering_target_passed": result.fit.engineering_target_passed,
        "serialized_mechanism_target_passed": result.mechanism_readback.engineering_target_passed,
        "serialized_rms_fraction": result.mechanism_readback.rms_fraction_of_target,
        "serialized_max_fraction": result.mechanism_readback.max_fraction_of_target,
        "low_order_piston_um_diagnostic": result.mechanism_readback.low_order_piston_um,
        "low_order_global_defocus_d": result.mechanism_readback.low_order_global_defocus_d,
        "rad_power_rms_error_d": (
            None if result.rad_power_readback is None else result.rad_power_readback.rms_error_d
        ),
        "rad_power_max_abs_error_d": (
            None
            if result.rad_power_readback is None
            else result.rad_power_readback.max_abs_error_d
        ),
        "ray_health": {
            "mono": result.mono_audit.ray_health_passed,
            "binary4_edof": result.binary4_edof_audit.ray_health_passed,
            "grid_sag_edof": result.grid_sag_edof_audit.ray_health_passed,
        },
        "manual_web_review_required": True,
        "raw": asdict(result),
    }
