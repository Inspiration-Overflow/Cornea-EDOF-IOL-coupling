from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .zos import SequentialEditor, ZosSession

BINARY4_FIRST_ZONE_PARAMETER = 13
BINARY4_ZONE_WIDTH = 4
CORNEA_SUPPORT_RADIUS_MM = 4.0


class CorneaSurfaceZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Binary4Zone:
    aperture_radius_mm: float
    radius_mm: float
    conic: float
    diffraction_order: int = 0

    def validate(self) -> None:
        values = (self.aperture_radius_mm, self.radius_mm, self.conic)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("Binary4 zone values must be finite")
        if self.aperture_radius_mm <= 0:
            raise ValueError("Binary4 zone aperture must be positive")
        if self.radius_mm == 0:
            raise ValueError("Binary4 zone radius must be non-zero")
        if self.diffraction_order != 0:
            raise ValueError("TASK-005D Binary4 zones are refractive-only and require order 0")


def _surface_type(zosapi: Any, name: str) -> Any:
    value = getattr(zosapi.Editors.LDE.SurfaceType, name, None)
    if value is None:
        raise CorneaSurfaceZosError(f"installed ZOS-API exposes no surface type {name!r}")
    return value


def _change_surface_type(row: Any, zosapi: Any, name: str) -> None:
    settings = row.GetSurfaceTypeSettings(_surface_type(zosapi, name))
    if settings is None or not bool(settings.IsValid):
        raise CorneaSurfaceZosError(f"invalid surface-type settings for {name}")
    changed = row.ChangeType(settings)
    if changed is False:
        raise CorneaSurfaceZosError(f"OpticStudio refused surface-type change to {name}")


def _parameter_cell(row: Any, zosapi: Any, number: int) -> Any:
    column = getattr(zosapi.Editors.LDE.SurfaceColumn, f"Par{number}", None)
    if column is None:
        raise CorneaSurfaceZosError(f"installed ZOS-API exposes no Par{number} column")
    return row.GetSurfaceCell(column)


def _set_parameter(row: Any, zosapi: Any, number: int, value: float | int) -> None:
    cell = _parameter_cell(row, zosapi, number)
    if isinstance(value, int):
        cell.IntegerValue = value
    else:
        cell.DoubleValue = float(value)


def configure_even_asphere(
    session: ZosSession,
    surface_number: int,
    *,
    radius_mm: float,
    conic: float,
    alpha1: float,
    semi_diameter_mm: float = CORNEA_SUPPORT_RADIUS_MM,
) -> None:
    if not all(math.isfinite(value) for value in (radius_mm, conic, alpha1, semi_diameter_mm)):
        raise ValueError("Even Asphere values must be finite")
    if radius_mm == 0 or semi_diameter_mm <= 0:
        raise ValueError("Even Asphere radius/semi-diameter are invalid")

    editor = SequentialEditor(session.system, session.zosapi)
    row = editor.surface(surface_number)
    _change_surface_type(row, session.zosapi, "EvenAspheric")
    editor.set_radius_conic(surface_number, radius_mm=radius_mm, conic=conic)
    row.SemiDiameter = float(semi_diameter_mm)
    _set_parameter(row, session.zosapi, 1, float(alpha1))
    for parameter in range(2, 9):
        _set_parameter(row, session.zosapi, parameter, 0.0)


def configure_binary4(
    session: ZosSession,
    surface_number: int,
    zones: tuple[Binary4Zone, ...],
) -> None:
    if not zones or len(zones) > 60:
        raise ValueError("Binary4 requires between 1 and 60 zones")
    previous = 0.0
    for zone in zones:
        zone.validate()
        if zone.aperture_radius_mm <= previous:
            raise ValueError("Binary4 zone apertures must be strictly increasing")
        previous = zone.aperture_radius_mm

    editor = SequentialEditor(session.system, session.zosapi)
    row = editor.surface(surface_number)
    _change_surface_type(row, session.zosapi, "Binary4")
    _set_parameter(row, session.zosapi, 1, len(zones))
    _set_parameter(row, session.zosapi, 2, 0)
    _set_parameter(row, session.zosapi, 3, 0)

    for index, zone in enumerate(zones):
        first = BINARY4_FIRST_ZONE_PARAMETER + BINARY4_ZONE_WIDTH * index
        _set_parameter(row, session.zosapi, first, zone.aperture_radius_mm)
        _set_parameter(row, session.zosapi, first + 1, zone.radius_mm)
        _set_parameter(row, session.zosapi, first + 2, zone.conic)
        _set_parameter(row, session.zosapi, first + 3, zone.diffraction_order)

    # Keep the conventional LDE radius/conic aligned with zone 1 for readable prescriptions.
    editor.set_radius_conic(
        surface_number,
        radius_mm=zones[0].radius_mm,
        conic=zones[0].conic,
    )
    row.SemiDiameter = zones[-1].aperture_radius_mm


def set_binary4_zone_conic(
    session: ZosSession,
    surface_number: int,
    zone_index: int,
    conic: float,
) -> None:
    if not math.isfinite(conic):
        raise ValueError("Binary4 conic must be finite")
    if zone_index < 0:
        raise ValueError("Binary4 zone index must be non-negative")
    row = SequentialEditor(session.system, session.zosapi).surface(surface_number)
    parameter = BINARY4_FIRST_ZONE_PARAMETER + BINARY4_ZONE_WIDTH * zone_index + 2
    _set_parameter(row, session.zosapi, parameter, conic)
    if zone_index == 0:
        row.Conic = float(conic)


def set_even_asphere_alpha1(
    session: ZosSession,
    surface_number: int,
    alpha1: float,
) -> None:
    if not math.isfinite(alpha1):
        raise ValueError("Even Asphere alpha1 must be finite")
    row = SequentialEditor(session.system, session.zosapi).surface(surface_number)
    _set_parameter(row, session.zosapi, 1, alpha1)
