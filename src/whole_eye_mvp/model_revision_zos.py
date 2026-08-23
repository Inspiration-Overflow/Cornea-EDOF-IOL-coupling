from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .model_revision import (
    CORNEA_CLEAR_SEMI_DIAMETER_MM,
    IOL_CLEAR_SEMI_DIAMETER_MM,
    RETINA_CLEAR_SEMI_DIAMETER_MM,
    physical_stop_semi_diameter_mm,
    retina_prescription_for_base,
)
from .zos import SequentialEditor, ZosSession


class ModelRevisionZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RevisionGeometryReadback:
    aperture_type: str
    stop_surface: int
    physical_pupil_diameter_mm: float
    cornea_ant_semi_diameter_mm: float
    cornea_post_semi_diameter_mm: float
    stop_semi_diameter_mm: float
    iol_ant_semi_diameter_mm: float
    iol_post_semi_diameter_mm: float | None
    retina_semi_diameter_mm: float
    retina_is_image: bool
    retina_surface_type: str
    retina_radius_y_mm: float
    retina_conic_y: float
    retina_radius_x_mm: float | None
    retina_conic_x: float | None


def _set_clear_semi_diameter(
    editor: SequentialEditor,
    surface_number: int,
    value_mm: float,
) -> None:
    value = float(value_mm)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("clear semi-diameter must be finite and positive")
    row = editor.surface(surface_number)
    try:
        row.SemiDiameter = value
    except Exception as exc:
        raise ModelRevisionZosError(
            f"failed to set clear semi-diameter at surface {surface_number}: {exc}"
        ) from exc


def _require_parameter_header(
    editor: SequentialEditor,
    surface_number: int,
    parameter_number: int,
    expected: str,
) -> None:
    actual = editor.parameter_header(surface_number, parameter_number)
    if actual != expected:
        raise ModelRevisionZosError(
            f"surface {surface_number} Par{parameter_number} header mismatch: "
            f"expected {expected!r}, got {actual!r}"
        )


def configure_biconic_retina(
    editor: SequentialEditor,
    surface_number: int,
    *,
    radius_x_mm: float,
    conic_x: float,
    radius_y_mm: float,
    conic_y: float,
) -> Any:
    numeric = (radius_x_mm, conic_x, radius_y_mm, conic_y)
    if not all(math.isfinite(float(value)) for value in numeric):
        raise ValueError("Biconic retina parameters must be finite")
    if radius_x_mm == 0 or radius_y_mm == 0:
        raise ValueError("Biconic retina radii must be non-zero")

    row = editor.change_surface_type(surface_number, "Biconic")
    # OpticStudio Biconic convention: ordinary Radius/Conic cells are the Y
    # meridian; Par1/Par2 hold X Radius/X Conic.
    editor.set_radius_conic(
        surface_number,
        radius_mm=float(radius_y_mm),
        conic=float(conic_y),
    )
    _require_parameter_header(editor, surface_number, 1, "X Radius")
    _require_parameter_header(editor, surface_number, 2, "X Conic")
    editor.set_parameter(surface_number, 1, float(radius_x_mm))
    editor.set_parameter(surface_number, 2, float(conic_x))
    return row


def apply_retina_prescription(
    session: ZosSession,
    base_id: str,
    *,
    surface_number: int,
) -> None:
    prescription = retina_prescription_for_base(base_id)
    editor = SequentialEditor(session.system, session.zosapi)
    row = editor.surface(surface_number)
    comment = str(row.Comment)
    material = str(row.Material)
    thickness = float(row.Thickness)

    if prescription.surface_type == "Standard":
        editor.change_surface_type(surface_number, "Standard")
        editor.set_radius_conic(
            surface_number,
            radius_mm=prescription.radius_y_mm,
            conic=prescription.conic_y,
        )
    else:
        if prescription.radius_x_mm is None or prescription.conic_x is None:
            raise ModelRevisionZosError("Biconic retina source lock is incomplete")
        configure_biconic_retina(
            editor,
            surface_number,
            radius_x_mm=prescription.radius_x_mm,
            conic_x=prescription.conic_x,
            radius_y_mm=prescription.radius_y_mm,
            conic_y=prescription.conic_y,
        )

    editor.set_comment(surface_number, comment)
    editor.set_material(surface_number, material)
    editor.set_thickness(surface_number, thickness)
    _set_clear_semi_diameter(editor, surface_number, prescription.semi_diameter_mm)


def configure_physical_pupil(
    session: ZosSession,
    pupil_diameter_mm: float,
    *,
    stop_surface: int = 3,
) -> None:
    semi_diameter = physical_stop_semi_diameter_mm(pupil_diameter_mm)
    lde = session.system.LDE
    if int(lde.StopSurface) != int(stop_surface):
        raise ModelRevisionZosError(
            f"physical pupil expects STOP surface {stop_surface}, got {int(lde.StopSurface)}"
        )
    row = lde.GetSurfaceAt(stop_surface)
    if not bool(row.IsStop):
        raise ModelRevisionZosError(f"surface {stop_surface} is not the active STOP")

    aperture_types = session.zosapi.SystemData.ZemaxApertureType
    aperture_type = getattr(aperture_types, "FloatByStopSize", None)
    if aperture_type is None:
        raise ModelRevisionZosError(
            "installed API exposes no ZemaxApertureType.FloatByStopSize"
        )
    session.system.SystemData.Aperture.ApertureType = aperture_type
    _set_clear_semi_diameter(
        SequentialEditor(session.system, session.zosapi),
        stop_surface,
        semi_diameter,
    )


def apply_revision_to_cornea_scaffold(
    session: ZosSession,
    base_id: str,
    *,
    pupil_diameter_mm: float = 3.0,
) -> None:
    """Apply post-audit geometry to a 6-surface cornea-only scaffold."""

    editor = SequentialEditor(session.system, session.zosapi)
    if int(editor.lde.NumberOfSurfaces) != 6:
        raise ModelRevisionZosError(
            "cornea scaffold revision expects 6 surfaces, "
            f"got {int(editor.lde.NumberOfSurfaces)}"
        )
    configure_physical_pupil(session, pupil_diameter_mm, stop_surface=3)
    _set_clear_semi_diameter(editor, 1, CORNEA_CLEAR_SEMI_DIAMETER_MM)
    _set_clear_semi_diameter(editor, 2, CORNEA_CLEAR_SEMI_DIAMETER_MM)
    _set_clear_semi_diameter(editor, 4, IOL_CLEAR_SEMI_DIAMETER_MM)
    apply_retina_prescription(session, base_id, surface_number=5)


def apply_revision_to_full_eye(
    session: ZosSession,
    base_id: str,
    *,
    pupil_diameter_mm: float,
) -> None:
    """Apply post-audit clear apertures, physical STOP and curved retina to a full eye."""

    editor = SequentialEditor(session.system, session.zosapi)
    if int(editor.lde.NumberOfSurfaces) != 7:
        raise ModelRevisionZosError(
            f"full-eye revision expects 7 surfaces, got {int(editor.lde.NumberOfSurfaces)}"
        )
    configure_physical_pupil(session, pupil_diameter_mm, stop_surface=3)
    _set_clear_semi_diameter(editor, 1, CORNEA_CLEAR_SEMI_DIAMETER_MM)
    _set_clear_semi_diameter(editor, 2, CORNEA_CLEAR_SEMI_DIAMETER_MM)
    _set_clear_semi_diameter(editor, 4, IOL_CLEAR_SEMI_DIAMETER_MM)
    _set_clear_semi_diameter(editor, 5, IOL_CLEAR_SEMI_DIAMETER_MM)
    apply_retina_prescription(session, base_id, surface_number=6)


def _surface_type_name(row: Any) -> str:
    value = str(getattr(row, "TypeName", "") or "").strip()
    if value:
        return value
    get_type = getattr(row, "GetType", None)
    if callable(get_type):
        return str(get_type())
    return str(getattr(row, "Type", ""))


def read_revision_geometry(
    session: ZosSession,
    base_id: str,
    *,
    full_eye: bool,
) -> RevisionGeometryReadback:
    editor = SequentialEditor(session.system, session.zosapi)
    expected_count = 7 if full_eye else 6
    if int(editor.lde.NumberOfSurfaces) != expected_count:
        raise ModelRevisionZosError(
            f"revision readback expects {expected_count} surfaces, "
            f"got {int(editor.lde.NumberOfSurfaces)}"
        )
    if int(editor.lde.StopSurface) != 3:
        raise ModelRevisionZosError("revision readback requires STOP surface 3")

    retina_number = 6 if full_eye else 5
    retina = editor.surface(retina_number)
    prescription = retina_prescription_for_base(base_id)
    radius_x: float | None = None
    conic_x: float | None = None
    if prescription.surface_type == "Biconic":
        _require_parameter_header(editor, retina_number, 1, "X Radius")
        _require_parameter_header(editor, retina_number, 2, "X Conic")
        columns = session.zosapi.Editors.LDE.SurfaceColumn
        radius_x = float(retina.GetSurfaceCell(columns.Par1).DoubleValue)
        conic_x = float(retina.GetSurfaceCell(columns.Par2).DoubleValue)

    stop_semi = float(editor.surface(3).SemiDiameter)
    return RevisionGeometryReadback(
        aperture_type=str(session.system.SystemData.Aperture.ApertureType),
        stop_surface=int(editor.lde.StopSurface),
        physical_pupil_diameter_mm=2.0 * stop_semi,
        cornea_ant_semi_diameter_mm=float(editor.surface(1).SemiDiameter),
        cornea_post_semi_diameter_mm=float(editor.surface(2).SemiDiameter),
        stop_semi_diameter_mm=stop_semi,
        iol_ant_semi_diameter_mm=float(editor.surface(4).SemiDiameter),
        iol_post_semi_diameter_mm=(
            float(editor.surface(5).SemiDiameter) if full_eye else None
        ),
        retina_semi_diameter_mm=float(retina.SemiDiameter),
        retina_is_image=bool(retina.IsImage),
        retina_surface_type=_surface_type_name(retina),
        retina_radius_y_mm=float(retina.Radius),
        retina_conic_y=float(retina.Conic),
        retina_radius_x_mm=radius_x,
        retina_conic_x=conic_x,
    )


def validate_revision_geometry(
    measurement: RevisionGeometryReadback,
    base_id: str,
    *,
    expected_pupil_diameter_mm: float,
) -> tuple[str, ...]:
    expected = retina_prescription_for_base(base_id)
    findings: list[str] = []

    def close(
        label: str,
        actual: float,
        target: float,
        tolerance: float = 1.0e-9,
    ) -> None:
        if not math.isfinite(actual) or abs(actual - target) > tolerance:
            findings.append(f"{label}: expected {target:.12g}, got {actual:.12g}")

    aperture_name = measurement.aperture_type.casefold()
    if "float" not in aperture_name or "stop" not in aperture_name:
        findings.append(
            "aperture_type: expected Float By Stop Size, "
            f"got {measurement.aperture_type!r}"
        )
    close(
        "physical_pupil_diameter_mm",
        measurement.physical_pupil_diameter_mm,
        expected_pupil_diameter_mm,
    )
    close("cornea_ant_semi_diameter_mm", measurement.cornea_ant_semi_diameter_mm, 5.0)
    close("cornea_post_semi_diameter_mm", measurement.cornea_post_semi_diameter_mm, 5.0)
    close(
        "stop_semi_diameter_mm",
        measurement.stop_semi_diameter_mm,
        0.5 * expected_pupil_diameter_mm,
    )
    close("iol_ant_semi_diameter_mm", measurement.iol_ant_semi_diameter_mm, 3.0)
    if measurement.iol_post_semi_diameter_mm is not None:
        close("iol_post_semi_diameter_mm", measurement.iol_post_semi_diameter_mm, 3.0)
    close(
        "retina_semi_diameter_mm",
        measurement.retina_semi_diameter_mm,
        RETINA_CLEAR_SEMI_DIAMETER_MM,
    )
    if not measurement.retina_is_image:
        findings.append("retina final surface lost IMAGE identity")
    if expected.surface_type.casefold() not in measurement.retina_surface_type.casefold():
        findings.append(
            f"retina_surface_type: expected {expected.surface_type}, "
            f"got {measurement.retina_surface_type!r}"
        )
    close(
        "retina_radius_y_mm",
        measurement.retina_radius_y_mm,
        expected.radius_y_mm,
        1.0e-6,
    )
    close("retina_conic_y", measurement.retina_conic_y, expected.conic_y, 1.0e-6)
    if expected.radius_x_mm is not None:
        if measurement.retina_radius_x_mm is None or measurement.retina_conic_x is None:
            findings.append("Biconic retina X readback is missing")
        else:
            close(
                "retina_radius_x_mm",
                measurement.retina_radius_x_mm,
                expected.radius_x_mm,
                1.0e-6,
            )
            if expected.conic_x is None:
                raise ModelRevisionZosError("Biconic retina source lock has no X conic")
            close(
                "retina_conic_x",
                measurement.retina_conic_x,
                expected.conic_x,
                1.0e-6,
            )
    return tuple(findings)
