from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .base_assets import IMAGE_ROLE, STOP_ROLE, _refractive_indices
from .carrier_zos import TASK007_CARRIER_ANT_ROLE, TASK007_CARRIER_POST_ROLE
from .domain import PlatformId
from .model_revision import (
    IOL_CLEAR_SEMI_DIAMETER_MM,
    MODEL_REVISION_ID,
    binary4_mechanism_spec,
    degenerate_binary4_zones,
    equivalent_even_asphere_coefficients,
)
from .model_revision_zos import (
    apply_revision_to_full_eye,
    read_revision_geometry,
    validate_revision_geometry,
)
from .zos import MfeEfflRunner, MfeFullHoaRunner, SequentialEditor, ZosSession
from .zos.primitives import binary4_zone_columns


class RevisionBinary4ZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Binary4ZoneReadback:
    zone: int
    r_inner_mm: float
    r_outer_mm: float
    radius_mm: float
    conic: float
    diffraction_order: float
    alpha_p2_native: float
    alpha_p4_native: float
    alpha_p6_native: float
    a4_equiv_mm_minus3: float
    a6_equiv_mm_minus5: float


@dataclass(frozen=True, slots=True)
class DegenerateBinary4BuildResult:
    revision_id: str
    base_id: str
    platform_id: str
    surface_number: int
    source_path: str
    path: str
    zones: tuple[Binary4ZoneReadback, ...]


@dataclass(frozen=True, slots=True)
class DegenerateEquivalenceThresholds:
    max_abs_sag_error_mm: float = 1.0e-6
    max_abs_effl_error_mm: float = 1.0e-6
    max_abs_c40_error_um: float = 1.0e-6
    max_abs_c60_error_um: float = 1.0e-6


DEFAULT_DEGENERATE_EQUIVALENCE_THRESHOLDS = DegenerateEquivalenceThresholds()


@dataclass(frozen=True, slots=True)
class DegenerateEquivalenceResult:
    base_id: str
    platform_id: str
    analytical_path: str
    binary4_path: str
    max_abs_sag_error_mm: float
    abs_effl_error_mm: float
    abs_c40_error_um: float
    abs_c60_error_um: float
    passed: bool
    findings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _EquivalenceSnapshot:
    sag_mm: tuple[float, ...]
    effl_mm: float
    c40_um: float
    c60_um: float


def binary4_surface_number(platform_id: str) -> int:
    spec = binary4_mechanism_spec(platform_id)
    return 4 if spec.surface_role == "anterior" else 5


def _require_full_eye_roles(session: ZosSession) -> None:
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise RevisionBinary4ZosError(
            f"Binary4 MONO conversion expects 7 surfaces, got {int(lde.NumberOfSurfaces)}"
        )
    expected = {
        3: STOP_ROLE,
        4: TASK007_CARRIER_ANT_ROLE,
        5: TASK007_CARRIER_POST_ROLE,
        6: IMAGE_ROLE,
    }
    for number, role in expected.items():
        actual = str(lde.GetSurfaceAt(number).Comment).strip()
        if actual != role:
            raise RevisionBinary4ZosError(
                f"surface {number} role mismatch: expected {role!r}, got {actual!r}"
            )


def _parameter_double(
    session: ZosSession,
    surface_number: int,
    parameter_number: int,
) -> float:
    columns = session.zosapi.Editors.LDE.SurfaceColumn
    try:
        column = getattr(columns, f"Par{parameter_number}")
    except AttributeError as exc:
        raise RevisionBinary4ZosError(
            f"installed API exposes no Par{parameter_number} column"
        ) from exc
    return float(
        session.system.LDE.GetSurfaceAt(surface_number)
        .GetSurfaceCell(column)
        .DoubleValue
    )


def _parameter_integer(
    session: ZosSession,
    surface_number: int,
    parameter_number: int,
) -> int:
    columns = session.zosapi.Editors.LDE.SurfaceColumn
    try:
        column = getattr(columns, f"Par{parameter_number}")
    except AttributeError as exc:
        raise RevisionBinary4ZosError(
            f"installed API exposes no Par{parameter_number} column"
        ) from exc
    return int(
        session.system.LDE.GetSurfaceAt(surface_number)
        .GetSurfaceCell(column)
        .IntegerValue
    )


def read_binary4_zones(
    session: ZosSession,
    platform_id: str,
) -> tuple[Binary4ZoneReadback, ...]:
    spec = binary4_mechanism_spec(platform_id)
    surface_number = binary4_surface_number(platform_id)
    row = session.system.LDE.GetSurfaceAt(surface_number)
    type_name = str(getattr(row, "TypeName", "") or "")
    get_type = getattr(row, "GetType", None)
    fallback_type = str(get_type()) if callable(get_type) else ""
    if "binary" not in type_name.casefold() and "binary" not in fallback_type.casefold():
        raise RevisionBinary4ZosError(
            f"surface {surface_number} did not replay as Binary 4: {type_name!r}"
        )

    zone_count = _parameter_integer(session, surface_number, 1)
    aspheric_count = _parameter_integer(session, surface_number, 2)
    phase_count = _parameter_integer(session, surface_number, 3)
    if (
        zone_count != len(spec.radial_apertures_mm)
        or aspheric_count != spec.aspheric_term_count
        or phase_count != spec.phase_term_count
    ):
        raise RevisionBinary4ZosError(
            "Binary 4 structural readback differs from the frozen mechanism spec: "
            f"Nz={zone_count}, Na={aspheric_count}, Np={phase_count}"
        )

    result: list[Binary4ZoneReadback] = []
    inner = 0.0
    for zone_number in range(1, zone_count + 1):
        columns = binary4_zone_columns(zone_number, aspheric_count, phase_count)
        outer = _parameter_double(session, surface_number, columns.radial_aperture)
        radius = _parameter_double(session, surface_number, columns.radius)
        conic = _parameter_double(session, surface_number, columns.conic)
        order = _parameter_double(session, surface_number, columns.diffraction_order)
        if len(columns.aspheric_terms) != 3:
            raise RevisionBinary4ZosError(
                "model revision requires exactly p^2/p^4/p^6 slots"
            )
        alpha2, alpha4, alpha6 = (
            _parameter_double(session, surface_number, number)
            for number in columns.aspheric_terms
        )
        a4, a6 = equivalent_even_asphere_coefficients(
            outer_radius_mm=outer,
            alpha_p4_native=alpha4,
            alpha_p6_native=alpha6,
        )
        result.append(
            Binary4ZoneReadback(
                zone=zone_number,
                r_inner_mm=inner,
                r_outer_mm=outer,
                radius_mm=radius,
                conic=conic,
                diffraction_order=order,
                alpha_p2_native=alpha2,
                alpha_p4_native=alpha4,
                alpha_p6_native=alpha6,
                a4_equiv_mm_minus3=a4,
                a6_equiv_mm_minus5=a6,
            )
        )
        inner = outer
    return tuple(result)


def build_degenerate_binary4_mono(
    session: ZosSession,
    base_id: str,
    platform_id: str,
    analytical_path: str | Path,
    destination: str | Path,
    *,
    pupil_diameter_mm: float = 3.0,
) -> DegenerateBinary4BuildResult:
    source = Path(analytical_path)
    if not source.is_file():
        raise RevisionBinary4ZosError(f"analytical carrier is missing: {source}")
    session.system.LoadFile(str(source.resolve()), False)
    _require_full_eye_roles(session)
    apply_revision_to_full_eye(
        session,
        base_id,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    geometry = read_revision_geometry(session, base_id, full_eye=True)
    findings = validate_revision_geometry(
        geometry,
        base_id,
        expected_pupil_diameter_mm=pupil_diameter_mm,
    )
    if findings:
        raise RevisionBinary4ZosError(
            "analytical carrier is not revision-compliant: " + " | ".join(findings)
        )

    surface_number = binary4_surface_number(platform_id)
    editor = SequentialEditor(session.system, session.zosapi)
    row = editor.surface(surface_number)
    base_radius = float(row.Radius)
    base_conic = float(row.Conic)
    base_thickness = float(row.Thickness)
    base_comment = str(row.Comment)
    base_index = _refractive_indices(session.system, surface_number)[0]

    zones = degenerate_binary4_zones(
        platform_id,
        radius_mm=base_radius,
        conic=base_conic,
    )
    editor.configure_binary4(surface_number, zones)
    # Keep the common row cells populated for transparent audit/display. Optical
    # zone shape is controlled by the Binary 4 zone R/Q values above.
    editor.set_radius_conic(
        surface_number,
        radius_mm=base_radius,
        conic=base_conic,
    )
    editor.set_thickness(surface_number, base_thickness)
    editor.set_comment(surface_number, base_comment)
    editor.surface(surface_number).SemiDiameter = IOL_CLEAR_SEMI_DIAMETER_MM

    output = Path(destination)
    editor.save_as(output)
    session.system.LoadFile(str(output.resolve()), False)
    _require_full_eye_roles(session)
    apply_revision_to_full_eye(
        session,
        base_id,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    replay_index = _refractive_indices(session.system, surface_number)[0]
    if abs(replay_index - base_index) > 1.0e-8:
        raise RevisionBinary4ZosError(
            f"Binary 4 conversion changed IOL refractive index: {base_index} -> {replay_index}"
        )

    readback = read_binary4_zones(session, platform_id)
    spec = binary4_mechanism_spec(platform_id)
    if tuple(item.r_outer_mm for item in readback) != spec.radial_apertures_mm:
        raise RevisionBinary4ZosError("Binary 4 zone boundary readback mismatch")
    for item in readback:
        if (
            abs(item.radius_mm - base_radius) > 1.0e-9
            or abs(item.conic - base_conic) > 1.0e-12
        ):
            raise RevisionBinary4ZosError("degenerate Binary 4 changed zone base R/Q")
        if (
            abs(item.diffraction_order) > 1.0e-12
            or abs(item.alpha_p2_native) > 1.0e-15
            or abs(item.alpha_p4_native) > 1.0e-15
            or abs(item.alpha_p6_native) > 1.0e-15
        ):
            raise RevisionBinary4ZosError(
                "degenerate Binary 4 contains non-zero residual/phase data"
            )

    # Persist the final physical-pupil/retina readback state after replay.
    SequentialEditor(session.system, session.zosapi).save_as(output)
    return DegenerateBinary4BuildResult(
        revision_id=MODEL_REVISION_ID,
        base_id=str(base_id),
        platform_id=str(platform_id),
        surface_number=surface_number,
        source_path=str(source.resolve()),
        path=str(output.resolve()),
        zones=readback,
    )


def _ssag_mm(session: ZosSession, surface_number: int, radius_mm: float) -> float:
    operand_type = getattr(
        session.zosapi.Editors.MFE.MeritOperandType,
        "SSAG",
        None,
    )
    if operand_type is None:
        raise RevisionBinary4ZosError(
            "installed MeritOperandType exposes no SSAG member"
        )
    get_value = getattr(session.system.MFE, "GetOperandValue", None)
    if not callable(get_value):
        raise RevisionBinary4ZosError("installed MFE exposes no GetOperandValue")
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
        raise RevisionBinary4ZosError(
            f"SSAG returned non-finite sag at r={radius_mm:g} mm"
        )
    return value


def _sag_grid_mm(session: ZosSession, surface_number: int) -> tuple[float, ...]:
    return tuple(
        _ssag_mm(session, surface_number, 0.05 * index)
        for index in range(round(IOL_CLEAR_SEMI_DIAMETER_MM / 0.05) + 1)
    )


def _acquire_snapshot(
    session: ZosSession,
    base_id: str,
    path: Path,
    surface_number: int,
    *,
    pupil_diameter_mm: float,
) -> _EquivalenceSnapshot:
    session.system.LoadFile(str(path.resolve()), False)
    _require_full_eye_roles(session)
    apply_revision_to_full_eye(
        session,
        base_id,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    sag = _sag_grid_mm(session, surface_number)
    effl = MfeEfflRunner(
        session.system,
        session.zosapi,
    ).run().effective_focal_length_mm
    hoa = MfeFullHoaRunner(session.system, session.zosapi).run()
    return _EquivalenceSnapshot(
        sag_mm=sag,
        effl_mm=effl,
        c40_um=hoa.c40_um,
        c60_um=hoa.c60_um,
    )


def compare_degenerate_binary4_to_analytical(
    session: ZosSession,
    base_id: str,
    platform_id: str,
    analytical_path: str | Path,
    binary4_path: str | Path,
    *,
    pupil_diameter_mm: float = 3.0,
    thresholds: DegenerateEquivalenceThresholds = (
        DEFAULT_DEGENERATE_EQUIVALENCE_THRESHOLDS
    ),
) -> DegenerateEquivalenceResult:
    analytical = Path(analytical_path)
    binary4 = Path(binary4_path)
    if not analytical.is_file() or not binary4.is_file():
        raise RevisionBinary4ZosError(
            "equivalence comparison requires both serialized ZMX files"
        )
    surface_number = binary4_surface_number(platform_id)
    left = _acquire_snapshot(
        session,
        base_id,
        analytical,
        surface_number,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    right = _acquire_snapshot(
        session,
        base_id,
        binary4,
        surface_number,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    max_sag = max(
        (
            abs(a - b)
            for a, b in zip(left.sag_mm, right.sag_mm, strict=True)
        ),
        default=0.0,
    )
    effl = abs(left.effl_mm - right.effl_mm)
    c40 = abs(left.c40_um - right.c40_um)
    c60 = abs(left.c60_um - right.c60_um)

    findings: list[str] = []
    comparisons = (
        ("max_abs_sag_error_mm", max_sag, thresholds.max_abs_sag_error_mm),
        ("abs_effl_error_mm", effl, thresholds.max_abs_effl_error_mm),
        ("abs_c40_error_um", c40, thresholds.max_abs_c40_error_um),
        ("abs_c60_error_um", c60, thresholds.max_abs_c60_error_um),
    )
    for label, actual, limit in comparisons:
        if not math.isfinite(actual) or actual > limit:
            findings.append(f"{label}: {actual:.12g} exceeds {limit:.12g}")
    return DegenerateEquivalenceResult(
        base_id=str(base_id),
        platform_id=str(PlatformId(platform_id)),
        analytical_path=str(analytical.resolve()),
        binary4_path=str(binary4.resolve()),
        max_abs_sag_error_mm=max_sag,
        abs_effl_error_mm=effl,
        abs_c40_error_um=c40,
        abs_c60_error_um=c60,
        passed=not findings,
        findings=tuple(findings),
    )
