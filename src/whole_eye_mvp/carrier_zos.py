from __future__ import annotations

import importlib
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
from .cornea_zos import FIXED_CORNEA_POST_ROLE
from .domain import BaselineBaseSpec, ScientificBaseline
from .ref_mono import initial_ref_mono_radius_mm, symmetric_biconvex_power_d
from .ref_mono_zos import solve_ref_mono_radius_mm
from .zos import SequentialEditor, ZosSession

TASK007_CARRIER_ANT_ROLE = "TASK007_CARRIER_ANT"
TASK007_CARRIER_POST_ROLE = "TASK007_CARRIER_POST"
TASK007_POWER_FOCUS_EPD_MM = 3.0
GEOMETRY_TOLERANCE_MM = 0.001
INDEX_TOLERANCE = 1.0e-6


class CarrierZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ActualEyeCarrierPowerResult:
    base_id: str
    cornea_path: str
    radius_ant_mm: float
    radius_post_mm: float
    power_d: float
    q: float
    center_thickness_mm: float
    iol_index: float
    optical_diameter_mm: float
    iol_position_mm: float
    focus_epd_mm: float
    focus_shift_mm: float
    axial_length_mm: float
    iol_post_to_image_mm: float
    surface_count: int
    stop_surface: int


@dataclass(frozen=True, slots=True)
class ParaxialSurfaceCapability:
    available_surface_types: tuple[str, ...]
    selected_surface_type: str | None
    changed_type: bool
    parameter_headers: tuple[tuple[int, str], ...]
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.selected_surface_type is not None and self.changed_type and self.error is None


def base_spec_for_id(baseline: ScientificBaseline, base_id: str) -> BaselineBaseSpec:
    matches = tuple(spec for spec in baseline.base_specs if spec.base_id == base_id)
    if len(matches) != 1:
        raise CarrierZosError(f"expected exactly one base specification for {base_id}")
    spec = matches[0]
    spec.validate()
    return spec


def iol_ant_to_image_mm_for_base(
    baseline: ScientificBaseline,
    base_id: str,
    *,
    cornea_thickness_mm: float,
) -> float:
    spec = base_spec_for_id(baseline, base_id)
    if not math.isfinite(cornea_thickness_mm) or cornea_thickness_mm <= 0:
        raise ValueError("cornea thickness must be finite and positive")
    distance = spec.axial_length_mm - cornea_thickness_mm - spec.post_cornea_to_iol_ant_mm
    if not math.isfinite(distance) or distance <= CONTROLLED_IOL_CARRIER_546_V1.center_thickness_mm:
        raise CarrierZosError("base geometry leaves no valid post-IOL image space")
    return distance


def choose_paraxial_surface_type(surface_type_names: tuple[str, ...]) -> str | None:
    if "Paraxial" in surface_type_names:
        return "Paraxial"
    matches = tuple(name for name in surface_type_names if "paraxial" in name.lower())
    if not matches:
        return None
    return min(matches, key=lambda name: (len(name), name))


def _set_epd(session: ZosSession, diameter_mm: float) -> None:
    if not math.isfinite(diameter_mm) or diameter_mm <= 0:
        raise ValueError("entrance pupil diameter must be finite and positive")
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(diameter_mm)


def _require_cornea_only_layout(session: ZosSession, path: Path) -> None:
    if not path.is_file():
        raise CarrierZosError(f"cornea input is missing: {path}")
    session.system.LoadFile(str(path.resolve()), False)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 6:
        raise CarrierZosError(
            f"TASK-007 cornea input must contain 6 surfaces, got {int(lde.NumberOfSurfaces)}"
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
            raise CarrierZosError(
                f"cornea surface {surface_number} role mismatch: expected {role!r}, got {actual!r}"
            )


def prepare_cornea_for_base(
    session: ZosSession,
    baseline: ScientificBaseline,
    base_id: str,
    cornea_path: str | Path,
) -> None:
    path = Path(cornea_path)
    _require_cornea_only_layout(session, path)
    lde = session.system.LDE
    cornea_thickness = float(lde.GetSurfaceAt(1).Thickness)
    post_to_iol = float(lde.GetSurfaceAt(2).Thickness) + float(lde.GetSurfaceAt(3).Thickness)
    spec = base_spec_for_id(baseline, base_id)
    if abs(post_to_iol - spec.post_cornea_to_iol_ant_mm) > GEOMETRY_TOLERANCE_MM:
        raise CarrierZosError(
            "cornea input post-cornea→IOL distance does not match the frozen base landmark"
        )
    lde.GetSurfaceAt(4).Thickness = iol_ant_to_image_mm_for_base(
        baseline,
        base_id,
        cornea_thickness_mm=cornea_thickness,
    )


def insert_controlled_carrier(
    session: ZosSession,
    baseline: ScientificBaseline,
    base_id: str,
    radius_mm: float,
    *,
    q: float = 0.0,
) -> None:
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    scaffold.validate()
    if not math.isfinite(radius_mm) or radius_mm <= 0:
        raise ValueError("controlled-carrier radius must be finite and positive")
    if not math.isfinite(q):
        raise ValueError("controlled-carrier conic must be finite")

    editor = SequentialEditor(session.system, session.zosapi)
    if int(editor.lde.NumberOfSurfaces) != 6:
        raise CarrierZosError("controlled carrier insertion requires a 6-surface cornea layout")
    cornea_thickness = float(editor.surface(1).Thickness)
    iol_to_image = iol_ant_to_image_mm_for_base(
        baseline,
        base_id,
        cornea_thickness_mm=cornea_thickness,
    )

    editor.set_comment(4, TASK007_CARRIER_ANT_ROLE)
    editor.set_radius_conic(4, radius_mm=radius_mm, conic=q)
    editor.set_thickness(4, scaffold.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 4, scaffold.refractive_index)

    editor.insert_surface(5)
    editor.set_comment(5, TASK007_CARRIER_POST_ROLE)
    editor.set_radius_conic(5, radius_mm=-radius_mm, conic=0.0)
    editor.set_thickness(5, iol_to_image - scaffold.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 5, scaffold.surrounding_index)

    editor.set_comment(6, IMAGE_ROLE)
    editor.set_radius_conic(6, radius_mm=0.0, conic=0.0)
    _set_epd(session, TASK007_POWER_FOCUS_EPD_MM)


def solve_actual_eye_carrier_power(
    session: ZosSession,
    baseline: ScientificBaseline,
    base_id: str,
    cornea_path: str | Path,
    destination: str | Path,
    *,
    initial_radius_mm: float | None = None,
) -> ActualEyeCarrierPowerResult:
    source = Path(cornea_path)
    prepare_cornea_for_base(session, baseline, base_id, source)
    start = initial_radius_mm if initial_radius_mm is not None else initial_ref_mono_radius_mm(baseline)
    insert_controlled_carrier(session, baseline, base_id, start, q=0.0)
    _radius, focus_shift = solve_ref_mono_radius_mm(
        session,
        baseline,
        initial_radius_mm=start,
    )
    output = Path(destination)
    SequentialEditor(session.system, session.zosapi).save_as(output)

    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise CarrierZosError("solved TASK-007 carrier must contain 7 surfaces")
    rows = tuple(lde.GetSurfaceAt(index) for index in range(1, 7))
    if str(rows[3].Comment).strip() != TASK007_CARRIER_ANT_ROLE:
        raise CarrierZosError("TASK-007 anterior carrier role was lost during solve")
    if str(rows[4].Comment).strip() != TASK007_CARRIER_POST_ROLE:
        raise CarrierZosError("TASK-007 posterior carrier role was lost during solve")

    radius_ant = float(rows[3].Radius)
    radius_post = float(rows[4].Radius)
    if abs(radius_ant + radius_post) > 1.0e-9:
        raise CarrierZosError("controlled carrier must keep symmetric biconvex radii")
    if abs(float(rows[3].Conic)) > 1.0e-12 or abs(float(rows[4].Conic)) > 1.0e-12:
        raise CarrierZosError("P-solve must keep Q=0 on both controlled-carrier surfaces")
    iol_index = _refractive_indices(session.system, 4)[0]
    if abs(iol_index - CONTROLLED_IOL_CARRIER_546_V1.refractive_index) > INDEX_TOLERANCE:
        raise CarrierZosError("controlled-carrier material index readback mismatch")

    axial_length = sum(float(row.Thickness) for row in rows[:-1])
    spec = base_spec_for_id(baseline, base_id)
    if abs(axial_length - spec.axial_length_mm) > GEOMETRY_TOLERANCE_MM:
        raise CarrierZosError(
            f"P-solve changed axial length: expected {spec.axial_length_mm}, got {axial_length}"
        )

    return ActualEyeCarrierPowerResult(
        base_id=base_id,
        cornea_path=str(source.resolve()),
        radius_ant_mm=radius_ant,
        radius_post_mm=radius_post,
        power_d=symmetric_biconvex_power_d(radius_ant),
        q=0.0,
        center_thickness_mm=float(rows[3].Thickness),
        iol_index=iol_index,
        optical_diameter_mm=CONTROLLED_IOL_CARRIER_546_V1.optical_diameter_mm,
        iol_position_mm=spec.post_cornea_to_iol_ant_mm,
        focus_epd_mm=TASK007_POWER_FOCUS_EPD_MM,
        focus_shift_mm=focus_shift,
        axial_length_mm=axial_length,
        iol_post_to_image_mm=float(rows[4].Thickness),
        surface_count=int(lde.NumberOfSurfaces),
        stop_surface=int(lde.StopSurface),
    )


def _surface_type_names(session: ZosSession) -> tuple[str, ...]:
    enum_type = session.zosapi.Editors.LDE.SurfaceType
    system_module = importlib.import_module("System")
    return tuple(str(name) for name in system_module.Enum.GetNames(enum_type))


def probe_paraxial_reference_surface(
    session: ZosSession,
    standard_eye_path: str | Path,
) -> ParaxialSurfaceCapability:
    path = Path(standard_eye_path)
    if not path.is_file():
        raise CarrierZosError(f"standard-eye input is missing: {path}")
    session.system.LoadFile(str(path.resolve()), False)
    editor = SequentialEditor(session.system, session.zosapi)
    if int(editor.lde.NumberOfSurfaces) != 5:
        raise CarrierZosError("paraxial capability probe requires the locked 5-surface standard eye")

    names = _surface_type_names(session)
    selected = choose_paraxial_surface_type(names)
    if selected is None:
        return ParaxialSurfaceCapability(names, None, False, (), "no paraxial surface type found")

    try:
        editor.change_surface_type(3, selected)
        headers: list[tuple[int, str]] = []
        for parameter_number in range(1, 17):
            header = editor.parameter_header(3, parameter_number)
            if header:
                headers.append((parameter_number, header))
        return ParaxialSurfaceCapability(names, selected, True, tuple(headers), None)
    except Exception as exc:  # noqa: BLE001 - capability evidence must record the API failure
        return ParaxialSurfaceCapability(
            names,
            selected,
            False,
            (),
            f"{type(exc).__name__}: {exc}",
        )
