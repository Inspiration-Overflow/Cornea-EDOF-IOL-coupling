from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .base_assets import (
    BaseAssetPrescription,
    _configure_nominal_system,
    _set_material_index_at_nominal_wavelength,
)
from .carrier_zos import (
    base_spec_for_id,
    iol_ant_to_image_mm_for_base,
)
from .cornea_assets import MAIN_CORNEA_SCAFFOLD
from .domain import ScientificBaseline
from .model_revision_zos import (
    apply_revision_to_cornea_scaffold,
    read_revision_geometry,
    validate_revision_geometry,
)
from .zos import SequentialEditor, ZosSession

NATIVE_CORNEA_ANT_ROLE = "CORNEA_ANT_NATIVE_LIOU"
NATIVE_CORNEA_SOURCE_ID = "MAIN_CORNEA_LIOU_555_v1_NATIVE_UNTREATED"


class RevisionR6NativeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class NativeCorneaRow:
    role: str
    radius_mm: float
    conic: float
    thickness_mm: float
    medium_after_index: float | None = None
    is_stop: bool = False


def native_cornea_rows(
    baseline: ScientificBaseline,
    base_id: str,
) -> tuple[NativeCorneaRow, ...]:
    """Return the six-surface untreated Liou cornea source stack for one base.

    The frozen TASK-005A base assets keep a plano coincident corneal reference
    slot by design; only A0/B0/C0 modules were ever meant to fill it.  The N0
    native untreated reference instead carries the frozen Liou cornea geometry
    (MAIN_CORNEA_LIOU_555_v1) so the carrier solves against real corneal power.
    """

    scaffold = MAIN_CORNEA_SCAFFOLD
    scaffold.validate()
    spec = base_spec_for_id(baseline, base_id)
    post_stop_to_iol = spec.post_cornea_to_iol_ant_mm - spec.post_cornea_to_stop_mm
    iol_to_retina = iol_ant_to_image_mm_for_base(
        baseline,
        base_id,
        cornea_thickness_mm=scaffold.thickness_mm,
    )
    if post_stop_to_iol <= 0 or not math.isfinite(post_stop_to_iol):
        raise RevisionR6NativeError(
            "native cornea stack requires strictly ordered stop/IOL landmarks"
        )
    return (
        NativeCorneaRow(
            role=NATIVE_CORNEA_ANT_ROLE,
            radius_mm=scaffold.front_radius_mm,
            conic=scaffold.front_conic,
            thickness_mm=scaffold.thickness_mm,
            medium_after_index=scaffold.cornea_index,
        ),
        NativeCorneaRow(
            role="CORNEA_POST_FIXED",
            radius_mm=scaffold.back_radius_mm,
            conic=scaffold.back_conic,
            thickness_mm=spec.post_cornea_to_stop_mm,
            medium_after_index=scaffold.aqueous_index,
        ),
        NativeCorneaRow(
            role="STOP",
            radius_mm=0.0,
            conic=0.0,
            thickness_mm=post_stop_to_iol,
            medium_after_index=spec.aqueous_index,
            is_stop=True,
        ),
        NativeCorneaRow(
            role="IOL_ANT_REF",
            radius_mm=0.0,
            conic=0.0,
            thickness_mm=iol_to_retina,
            medium_after_index=spec.vitreous_index,
        ),
        NativeCorneaRow(
            role="IMAGE_FIXED",
            radius_mm=0.0,
            conic=0.0,
            thickness_mm=0.0,
        ),
    )


def build_native_cornea_source(
    session: ZosSession,
    baseline: ScientificBaseline,
    base_id: str,
    destination: str | Path,
    *,
    pupil_diameter_mm: float = 3.0,
) -> Path:
    rows = native_cornea_rows(baseline, base_id)
    output = Path(destination)
    editor = SequentialEditor(session.system, session.zosapi)
    editor.new_system()

    scaffold = MAIN_CORNEA_SCAFFOLD
    nominal = BaseAssetPrescription(
        artifact_id=NATIVE_CORNEA_SOURCE_ID,
        relative_path="r6_native_cornea_source.zmx",
        base_spec=base_spec_for_id(baseline, base_id),
        wavelength_nm=scaffold.wavelength_nm,
    )
    _configure_nominal_system(session.system, session.zosapi, nominal)

    required = len(rows) + 1
    while editor.lde.NumberOfSurfaces < required:
        editor.insert_surface(1)
    if editor.lde.NumberOfSurfaces != required:
        raise RevisionR6NativeError(
            f"unexpected new-system surface count: {editor.lde.NumberOfSurfaces}"
        )

    for index, row in enumerate(rows, start=1):
        editor.set_comment(index, row.role)
        editor.set_radius_conic(index, radius_mm=row.radius_mm, conic=row.conic)
        editor.set_thickness(index, row.thickness_mm)
        if row.medium_after_index is not None:
            _set_material_index_at_nominal_wavelength(
                editor,
                index,
                row.medium_after_index,
            )

    stop_index = next(
        index for index, row in enumerate(rows, start=1) if row.is_stop
    )
    editor.set_stop_surface(stop_index)

    apply_revision_to_cornea_scaffold(
        session,
        base_id,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    editor.save_as(output)
    session.system.LoadFile(str(output.resolve()), False)

    geometry = read_revision_geometry(session, base_id, full_eye=False)
    findings = validate_revision_geometry(
        geometry,
        base_id,
        expected_pupil_diameter_mm=pupil_diameter_mm,
    )
    if findings:
        raise RevisionR6NativeError(
            "native cornea source readback failed: " + " | ".join(findings)
        )
    return output
