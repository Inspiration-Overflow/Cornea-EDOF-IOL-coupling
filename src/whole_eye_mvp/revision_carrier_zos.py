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
from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .carrier_zos import (
    GEOMETRY_TOLERANCE_MM,
    INDEX_TOLERANCE,
    TASK007_CARRIER_ANT_ROLE,
    TASK007_CARRIER_POST_ROLE,
    base_spec_for_id,
    iol_ant_to_image_mm_for_base,
)
from .cornea_zos import FIXED_CORNEA_POST_ROLE
from .domain import ScientificBaseline
from .model_revision import CARRIER_FOCUS_PUPIL_DIAMETER_MM, MODEL_REVISION_ID
from .model_revision_zos import (
    RevisionGeometryReadback,
    apply_revision_to_cornea_scaffold,
    apply_revision_to_full_eye,
    read_revision_geometry,
    validate_revision_geometry,
)
from .ref_mono import initial_ref_mono_radius_mm, symmetric_biconvex_power_d
from .ref_mono_zos import solve_ref_mono_radius_mm
from .zos import SequentialEditor, ZosSession


class RevisionCarrierZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RevisionAnalyticalCarrierResult:
    revision_id: str
    base_id: str
    source_cornea_path: str
    path: str
    radius_ant_mm: float
    radius_post_mm: float
    power_d: float
    q_ant: float
    q_post: float
    focus_shift_mm: float
    axial_length_mm: float
    iol_position_mm: float
    geometry: RevisionGeometryReadback


def _require_cornea_scaffold(session: ZosSession, path: Path) -> None:
    if not path.is_file():
        raise RevisionCarrierZosError(f"cornea input is missing: {path}")
    session.system.LoadFile(str(path.resolve()), False)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 6:
        raise RevisionCarrierZosError(
            f"revised carrier requires a 6-surface cornea scaffold, got {int(lde.NumberOfSurfaces)}"
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
            raise RevisionCarrierZosError(
                f"surface {surface_number} role mismatch: expected {role!r}, got {actual!r}"
            )


def _prepare_cornea_geometry_for_base(
    session: ZosSession,
    baseline: ScientificBaseline,
    base_id: str,
) -> float:
    lde = session.system.LDE
    cornea_thickness = float(lde.GetSurfaceAt(1).Thickness)
    if not math.isfinite(cornea_thickness) or cornea_thickness <= 0:
        raise RevisionCarrierZosError("cornea thickness must be finite and positive")
    post_to_iol = float(lde.GetSurfaceAt(2).Thickness) + float(lde.GetSurfaceAt(3).Thickness)
    spec = base_spec_for_id(baseline, base_id)
    if abs(post_to_iol - spec.post_cornea_to_iol_ant_mm) > GEOMETRY_TOLERANCE_MM:
        raise RevisionCarrierZosError(
            "cornea input post-cornea→IOL distance differs from the frozen base landmark"
        )
    iol_to_retina = iol_ant_to_image_mm_for_base(
        baseline,
        base_id,
        cornea_thickness_mm=cornea_thickness,
    )
    lde.GetSurfaceAt(4).Thickness = iol_to_retina
    return iol_to_retina


def _insert_q0_controlled_carrier(
    session: ZosSession,
    radius_mm: float,
    iol_ant_to_retina_mm: float,
) -> None:
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    scaffold.validate()
    if not math.isfinite(radius_mm) or radius_mm <= 0:
        raise ValueError("carrier radius must be finite and positive")
    if iol_ant_to_retina_mm <= scaffold.center_thickness_mm:
        raise RevisionCarrierZosError("carrier thickness leaves no post-IOL retinal space")

    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_comment(4, TASK007_CARRIER_ANT_ROLE)
    editor.set_radius_conic(4, radius_mm=radius_mm, conic=0.0)
    editor.set_thickness(4, scaffold.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 4, scaffold.refractive_index)

    editor.insert_surface(5)
    editor.set_comment(5, TASK007_CARRIER_POST_ROLE)
    editor.set_radius_conic(5, radius_mm=-radius_mm, conic=0.0)
    editor.set_thickness(5, iol_ant_to_retina_mm - scaffold.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 5, scaffold.surrounding_index)

    # The former IMAGE row has shifted from 5 to 6.  Its curved-retina type and
    # parameters are intentionally preserved rather than rewritten as a plane.
    editor.set_comment(6, IMAGE_ROLE)


def build_revision_q0_analytical_carrier(
    session: ZosSession,
    baseline: ScientificBaseline,
    base_id: str,
    cornea_path: str | Path,
    destination: str | Path,
    *,
    initial_radius_mm: float | None = None,
) -> RevisionAnalyticalCarrierResult:
    source = Path(cornea_path)
    _require_cornea_scaffold(session, source)
    iol_to_retina = _prepare_cornea_geometry_for_base(session, baseline, base_id)
    apply_revision_to_cornea_scaffold(
        session,
        base_id,
        pupil_diameter_mm=CARRIER_FOCUS_PUPIL_DIAMETER_MM,
    )

    start = initial_radius_mm if initial_radius_mm is not None else initial_ref_mono_radius_mm(baseline)
    _insert_q0_controlled_carrier(session, start, iol_to_retina)
    apply_revision_to_full_eye(
        session,
        base_id,
        pupil_diameter_mm=CARRIER_FOCUS_PUPIL_DIAMETER_MM,
    )
    _radius, focus_shift = solve_ref_mono_radius_mm(
        session,
        baseline,
        initial_radius_mm=start,
    )
    apply_revision_to_full_eye(
        session,
        base_id,
        pupil_diameter_mm=CARRIER_FOCUS_PUPIL_DIAMETER_MM,
    )

    output = Path(destination)
    SequentialEditor(session.system, session.zosapi).save_as(output)
    session.system.LoadFile(str(output.resolve()), False)

    geometry = read_revision_geometry(session, base_id, full_eye=True)
    findings = validate_revision_geometry(
        geometry,
        base_id,
        expected_pupil_diameter_mm=CARRIER_FOCUS_PUPIL_DIAMETER_MM,
    )
    if findings:
        raise RevisionCarrierZosError(
            "revised carrier geometry failed readback: " + " | ".join(findings)
        )

    lde = session.system.LDE
    ant = lde.GetSurfaceAt(4)
    post = lde.GetSurfaceAt(5)
    radius_ant = float(ant.Radius)
    radius_post = float(post.Radius)
    q_ant = float(ant.Conic)
    q_post = float(post.Conic)
    if abs(radius_ant + radius_post) > 1.0e-9:
        raise RevisionCarrierZosError("revised Q0 carrier lost symmetric biconvex radii")
    if abs(q_ant) > 1.0e-12 or abs(q_post) > 1.0e-12:
        raise RevisionCarrierZosError("revised Q0 P-solve changed the carrier conic")
    iol_index = _refractive_indices(session.system, 4)[0]
    if abs(iol_index - CONTROLLED_IOL_CARRIER_546_V1.refractive_index) > INDEX_TOLERANCE:
        raise RevisionCarrierZosError("revised carrier material index readback mismatch")

    axial_length = math.fsum(float(lde.GetSurfaceAt(index).Thickness) for index in range(1, 6))
    spec = base_spec_for_id(baseline, base_id)
    if abs(axial_length - spec.axial_length_mm) > GEOMETRY_TOLERANCE_MM:
        raise RevisionCarrierZosError(
            f"revised carrier changed axial length: expected {spec.axial_length_mm}, got {axial_length}"
        )

    return RevisionAnalyticalCarrierResult(
        revision_id=MODEL_REVISION_ID,
        base_id=str(base_id),
        source_cornea_path=str(source.resolve()),
        path=str(output.resolve()),
        radius_ant_mm=radius_ant,
        radius_post_mm=radius_post,
        power_d=symmetric_biconvex_power_d(radius_ant),
        q_ant=q_ant,
        q_post=q_post,
        focus_shift_mm=focus_shift,
        axial_length_mm=axial_length,
        iol_position_mm=spec.post_cornea_to_iol_ant_mm,
        geometry=geometry,
    )
