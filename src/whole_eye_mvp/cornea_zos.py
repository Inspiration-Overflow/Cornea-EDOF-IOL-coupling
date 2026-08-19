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
    base_asset_prescriptions,
    validate_base_asset,
)
from .cornea_assets import (
    CORNEA_LOCK_BASE_ID,
    MAIN_CORNEA_SCAFFOLD,
    CorneaScaffold,
    cornea_lock_eye_geometry,
    distance_corrected_front_radius_mm,
)
from .domain import ScientificBaseline
from .zos import SequentialEditor, ZosSession

REFERENCE_CORNEA_ANT_ROLE = "CORNEA_ANT_LIOU_REFERENCE"
DISTANCE_CORNEA_ANT_ROLE = "CORNEA_ANT_DISTANCE_M3"
FIXED_CORNEA_POST_ROLE = "CORNEA_POST_FIXED"
CORNEA_DIAGNOSTIC_EPD_MM = 6.0
GEOMETRY_TOLERANCE_MM = 0.001
INDEX_TOLERANCE = 1.0e-6


class CorneaZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DistanceCorneaMeasurements:
    wavelength_nm: float
    entrance_pupil_mm: float
    front_radius_mm: float
    front_conic: float
    cornea_thickness_mm: float
    back_radius_mm: float
    back_conic: float
    cornea_index: float
    aqueous_index_after_cornea: float
    post_cornea_to_stop_mm: float
    stop_to_iol_ant_mm: float
    post_cornea_to_iol_ant_mm: float
    iol_ant_to_image_mm: float
    axial_length_mm: float
    surface_count: int
    stop_surface: int


def _lb_base_prescription(baseline: ScientificBaseline):
    matches = tuple(
        item
        for item in base_asset_prescriptions(baseline)
        if item.base_spec.base_id == CORNEA_LOCK_BASE_ID
    )
    if len(matches) != 1:
        raise CorneaZosError("expected exactly one LB base prescription")
    return matches[0]


def _set_entrance_pupil(session: ZosSession, diameter_mm: float) -> None:
    if not math.isfinite(diameter_mm) or diameter_mm <= 0:
        raise ValueError("entrance pupil diameter must be finite and positive")
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(diameter_mm)


def build_distance_cornea_scaffold(
    session: ZosSession,
    baseline: ScientificBaseline,
    base_asset_path: str | Path,
    destination: str | Path,
    *,
    scaffold: CorneaScaffold = MAIN_CORNEA_SCAFFOLD,
) -> Path:
    """Replace the 005B coincident corneal reference slot with a physical -3 D cornea."""

    scaffold.validate()
    geometry = cornea_lock_eye_geometry(baseline, scaffold=scaffold)
    prescription = _lb_base_prescription(baseline)
    validation = validate_base_asset(session, prescription, base_asset_path)
    if not validation.passed:
        raise CorneaZosError(
            "LB base asset failed read-only validation: " + " | ".join(validation.findings)
        )

    editor = SequentialEditor(session.system, session.zosapi)
    if int(editor.lde.NumberOfSurfaces) != 6:
        raise CorneaZosError(
            f"LB base scaffold must contain 6 surfaces, got {int(editor.lde.NumberOfSurfaces)}"
        )

    _set_entrance_pupil(session, CORNEA_DIAGNOSTIC_EPD_MM)

    editor.set_comment(1, DISTANCE_CORNEA_ANT_ROLE)
    editor.set_radius_conic(
        1,
        radius_mm=distance_corrected_front_radius_mm(-3.0, scaffold=scaffold),
        conic=scaffold.front_conic,
    )
    editor.set_thickness(1, scaffold.thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 1, scaffold.cornea_index)

    editor.set_comment(2, FIXED_CORNEA_POST_ROLE)
    editor.set_radius_conic(2, radius_mm=scaffold.back_radius_mm, conic=scaffold.back_conic)
    editor.set_thickness(2, geometry.post_cornea_to_stop_mm)
    _set_material_index_at_nominal_wavelength(editor, 2, scaffold.aqueous_index)

    editor.set_comment(3, STOP_ROLE)
    editor.set_radius_conic(3, radius_mm=0.0, conic=0.0)
    editor.set_thickness(3, geometry.stop_to_iol_ant_mm)
    _set_material_index_at_nominal_wavelength(editor, 3, scaffold.aqueous_index)
    editor.set_stop_surface(3)

    editor.set_comment(4, IOL_ANT_ROLE)
    editor.set_radius_conic(4, radius_mm=0.0, conic=0.0)
    editor.set_thickness(4, geometry.iol_ant_to_image_mm)
    _set_material_index_at_nominal_wavelength(editor, 4, scaffold.aqueous_index)

    editor.set_comment(5, IMAGE_ROLE)
    editor.set_radius_conic(5, radius_mm=0.0, conic=0.0)

    output = Path(destination)
    editor.save_as(output)
    return output


def build_reference_cornea_scaffold(
    session: ZosSession,
    baseline: ScientificBaseline,
    base_asset_path: str | Path,
    destination: str | Path,
    *,
    scaffold: CorneaScaffold = MAIN_CORNEA_SCAFFOLD,
) -> Path:
    """Build the physical pre-treatment Liou reference with the same locked LB landmarks."""

    output = build_distance_cornea_scaffold(
        session,
        baseline,
        base_asset_path,
        destination,
        scaffold=scaffold,
    )
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_comment(1, REFERENCE_CORNEA_ANT_ROLE)
    editor.set_radius_conic(
        1,
        radius_mm=scaffold.front_radius_mm,
        conic=scaffold.front_conic,
    )
    editor.save_as(output)
    return output


def measure_distance_cornea_scaffold(
    session: ZosSession,
    path: str | Path,
) -> DistanceCorneaMeasurements:
    session.system.LoadFile(str(Path(path).resolve()), False)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 6:
        raise CorneaZosError(
            f"distance-cornea scaffold must contain 6 surfaces, got {int(lde.NumberOfSurfaces)}"
        )
    rows = tuple(lde.GetSurfaceAt(index) for index in range(1, 6))
    expected_roles = (
        DISTANCE_CORNEA_ANT_ROLE,
        FIXED_CORNEA_POST_ROLE,
        STOP_ROLE,
        IOL_ANT_ROLE,
        IMAGE_ROLE,
    )
    actual_roles = tuple(str(row.Comment).strip() for row in rows)
    if actual_roles != expected_roles:
        raise CorneaZosError(
            f"distance-cornea surface roles differ: expected={expected_roles}, got={actual_roles}"
        )

    wavelength_nm = (
        float(session.system.SystemData.Wavelengths.GetWavelength(1).Wavelength) * 1000.0
    )
    entrance_pupil = float(session.system.SystemData.Aperture.ApertureValue)
    cornea_index = _refractive_indices(session.system, 1)[0]
    aqueous_index = _refractive_indices(session.system, 2)[0]
    thicknesses = tuple(float(row.Thickness) for row in rows[:-1])
    axial_length = sum(thicknesses)

    return DistanceCorneaMeasurements(
        wavelength_nm=wavelength_nm,
        entrance_pupil_mm=entrance_pupil,
        front_radius_mm=float(rows[0].Radius),
        front_conic=float(rows[0].Conic),
        cornea_thickness_mm=thicknesses[0],
        back_radius_mm=float(rows[1].Radius),
        back_conic=float(rows[1].Conic),
        cornea_index=cornea_index,
        aqueous_index_after_cornea=aqueous_index,
        post_cornea_to_stop_mm=thicknesses[1],
        stop_to_iol_ant_mm=thicknesses[2],
        post_cornea_to_iol_ant_mm=thicknesses[1] + thicknesses[2],
        iol_ant_to_image_mm=thicknesses[3],
        axial_length_mm=axial_length,
        surface_count=int(lde.NumberOfSurfaces),
        stop_surface=int(lde.StopSurface),
    )


def validate_distance_cornea_measurements(
    measurement: DistanceCorneaMeasurements,
    baseline: ScientificBaseline,
    *,
    scaffold: CorneaScaffold = MAIN_CORNEA_SCAFFOLD,
) -> tuple[str, ...]:
    scaffold.validate()
    geometry = cornea_lock_eye_geometry(baseline, scaffold=scaffold)
    findings: list[str] = []

    def close(label: str, actual: float, expected: float, tolerance: float) -> None:
        if not math.isfinite(actual) or abs(actual - expected) > tolerance:
            findings.append(
                f"{label}: expected {expected:.12g} ± {tolerance:.3g}, got {actual:.12g}"
            )

    close("wavelength_nm", measurement.wavelength_nm, scaffold.wavelength_nm, 1.0e-9)
    close(
        "entrance_pupil_mm",
        measurement.entrance_pupil_mm,
        CORNEA_DIAGNOSTIC_EPD_MM,
        0.001,
    )
    close(
        "front_radius_mm",
        measurement.front_radius_mm,
        distance_corrected_front_radius_mm(-3.0, scaffold=scaffold),
        GEOMETRY_TOLERANCE_MM,
    )
    close("front_conic", measurement.front_conic, scaffold.front_conic, 1.0e-9)
    close(
        "cornea_thickness_mm",
        measurement.cornea_thickness_mm,
        scaffold.thickness_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "back_radius_mm",
        measurement.back_radius_mm,
        scaffold.back_radius_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close("back_conic", measurement.back_conic, scaffold.back_conic, 1.0e-9)
    close("cornea_index", measurement.cornea_index, scaffold.cornea_index, INDEX_TOLERANCE)
    close(
        "aqueous_index_after_cornea",
        measurement.aqueous_index_after_cornea,
        scaffold.aqueous_index,
        INDEX_TOLERANCE,
    )
    close(
        "post_cornea_to_stop_mm",
        measurement.post_cornea_to_stop_mm,
        geometry.post_cornea_to_stop_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "stop_to_iol_ant_mm",
        measurement.stop_to_iol_ant_mm,
        geometry.stop_to_iol_ant_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "post_cornea_to_iol_ant_mm",
        measurement.post_cornea_to_iol_ant_mm,
        geometry.post_cornea_to_iol_ant_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "iol_ant_to_image_mm",
        measurement.iol_ant_to_image_mm,
        geometry.iol_ant_to_image_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "axial_length_mm",
        measurement.axial_length_mm,
        geometry.axial_length_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    if measurement.surface_count != 6:
        findings.append(f"surface_count: expected 6, got {measurement.surface_count}")
    if measurement.stop_surface != 3:
        findings.append(f"stop_surface: expected 3, got {measurement.stop_surface}")
    return tuple(findings)
