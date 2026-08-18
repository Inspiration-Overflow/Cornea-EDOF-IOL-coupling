from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, TypeVar


class ZosPrimitiveError(RuntimeError):
    pass


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Binary4Zone:
    radial_aperture: float
    radius: float
    conic: float
    diffraction_order: float = 0.0
    aspheric_terms: tuple[float, ...] = ()
    phase_terms: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class Binary4ZoneColumns:
    radial_aperture: int
    radius: int
    conic: int
    diffraction_order: int
    aspheric_terms: tuple[int, ...]
    phase_terms: tuple[int, ...]


def binary4_zone_columns(
    zone_number: int,
    aspheric_term_count: int,
    phase_term_count: int,
) -> Binary4ZoneColumns:
    """Return the verified 2026 R1 Binary 4 ``ParN`` numbers for one zone."""

    if zone_number < 1:
        raise ValueError("Binary 4 zone number is 1-based")
    if aspheric_term_count < 0 or phase_term_count < 0:
        raise ValueError("Binary 4 term counts must be non-negative")
    if aspheric_term_count > 20 or phase_term_count > 20:
        raise ValueError("Binary 4 supports at most 20 aspheric and 20 phase terms per zone")
    stride = 4 + aspheric_term_count + phase_term_count
    start = 13 + (zone_number - 1) * stride
    stop = start + stride - 1
    if stop > 254:
        raise ValueError("Binary 4 parameters exceed the available Par254 column")
    aspheric_start = start + 4
    phase_start = aspheric_start + aspheric_term_count
    return Binary4ZoneColumns(
        radial_aperture=start,
        radius=start + 1,
        conic=start + 2,
        diffraction_order=start + 3,
        aspheric_terms=tuple(range(aspheric_start, aspheric_start + aspheric_term_count)),
        phase_terms=tuple(range(phase_start, phase_start + phase_term_count)),
    )


def even_asphere_parameter_number(order: int) -> int:
    """Map verified Even Asphere orders 2..16 to ``Par1``..``Par8``."""

    if order < 2 or order > 16 or order % 2:
        raise ValueError("Even Asphere order must be one of 2, 4, ..., 16")
    return order // 2


@dataclass(slots=True)
class SequentialEditor:
    """Late-bound wrapper around stable sequential ZOS-API editor operations."""

    system: Any
    zosapi: Any

    @property
    def lde(self) -> Any:
        return self.system.LDE

    def new_system(self, save_if_needed: bool = False) -> None:
        self.system.New(save_if_needed)
        make_sequential = getattr(self.system, "MakeSequential", None)
        if not callable(make_sequential):
            raise ZosPrimitiveError("installed API does not expose IOpticalSystem.MakeSequential")
        make_sequential()

    def surface(self, index: int) -> Any:
        return self.lde.GetSurfaceAt(index)

    def insert_surface(self, index: int) -> Any:
        return self.lde.InsertNewSurfaceAt(index)

    def remove_surfaces(self, index: int, count: int = 1) -> None:
        self.lde.RemoveSurfacesAt(index, count)

    def change_surface_type(self, index: int, surface_type_name: str) -> Any:
        row = self.surface(index)
        try:
            surface_type = getattr(self.zosapi.Editors.LDE.SurfaceType, surface_type_name)
        except AttributeError as exc:
            raise ZosPrimitiveError(f"unknown surface type: {surface_type_name}") from exc
        settings = row.GetSurfaceTypeSettings(surface_type)
        row.ChangeType(settings)
        return row

    def set_radius_conic(self, index: int, *, radius_mm: float, conic: float = 0.0) -> None:
        row = self.surface(index)
        row.Radius = float(radius_mm)
        row.Conic = float(conic)

    def set_thickness(self, index: int, thickness_mm: float) -> None:
        self.surface(index).Thickness = float(thickness_mm)

    def set_material(self, index: int, material: str) -> None:
        self.surface(index).Material = material

    def set_comment(self, index: int, comment: str) -> None:
        self.surface(index).Comment = comment

    def set_parameter(self, index: int, parameter_number: int, value: float) -> None:
        if parameter_number < 1:
            raise ValueError("parameter_number is 1-based")
        row = self.surface(index)
        name = f"Par{parameter_number}"
        try:
            column = getattr(self.zosapi.Editors.LDE.SurfaceColumn, name)
        except AttributeError as exc:
            raise ZosPrimitiveError(f"surface parameter column not available: {name}") from exc
        row.GetSurfaceCell(column).DoubleValue = float(value)

    def set_integer_parameter(self, index: int, parameter_number: int, value: int) -> None:
        if parameter_number < 1:
            raise ValueError("parameter_number is 1-based")
        row = self.surface(index)
        name = f"Par{parameter_number}"
        try:
            column = getattr(self.zosapi.Editors.LDE.SurfaceColumn, name)
        except AttributeError as exc:
            raise ZosPrimitiveError(f"surface parameter column not available: {name}") from exc
        row.GetSurfaceCell(column).IntegerValue = int(value)

    def parameter_header(self, index: int, parameter_number: int) -> str:
        if parameter_number < 1:
            raise ValueError("parameter_number is 1-based")
        name = f"Par{parameter_number}"
        try:
            column = getattr(self.zosapi.Editors.LDE.SurfaceColumn, name)
        except AttributeError as exc:
            raise ZosPrimitiveError(f"surface parameter column not available: {name}") from exc
        return str(self.surface(index).GetSurfaceCell(column).Header).strip()

    def _require_parameter_header(
        self, index: int, parameter_number: int, expected: str
    ) -> None:
        actual = self.parameter_header(index, parameter_number)
        if actual != expected:
            raise ZosPrimitiveError(
                f"surface Par{parameter_number} header mismatch: expected {expected!r}, "
                f"received {actual!r}"
            )

    def configure_binary4(
        self,
        index: int,
        zones: tuple[Binary4Zone, ...],
    ) -> Any:
        if not zones:
            raise ValueError("Binary 4 requires at least one radial zone")
        aspheric_count = len(zones[0].aspheric_terms)
        phase_count = len(zones[0].phase_terms)
        if aspheric_count > 20 or phase_count > 20:
            raise ValueError("Binary 4 supports at most 20 aspheric and 20 phase terms per zone")
        if any(
            len(zone.aspheric_terms) != aspheric_count
            or len(zone.phase_terms) != phase_count
            for zone in zones
        ):
            raise ValueError("all Binary 4 zones must use equal aspheric and phase term counts")
        numeric_values = tuple(
            value
            for zone in zones
            for value in (
                zone.radial_aperture,
                zone.radius,
                zone.conic,
                zone.diffraction_order,
                *zone.aspheric_terms,
                *zone.phase_terms,
            )
        )
        if not all(math.isfinite(float(value)) for value in numeric_values):
            raise ValueError("Binary 4 values must be finite")
        apertures = tuple(float(zone.radial_aperture) for zone in zones)
        if any(aperture <= 0 for aperture in apertures) or any(
            right <= left for left, right in pairwise(apertures)
        ):
            raise ValueError("Binary 4 radial apertures must be positive and strictly increasing")

        row = self.change_surface_type(index, "Binary4")
        for parameter_number, expected_header in (
            (1, "# Radial Zones"),
            (2, "# Aspheric Terms"),
            (3, "# Phase Terms"),
            (4, "Sine(delta0)"),
        ):
            self._require_parameter_header(index, parameter_number, expected_header)
        self.set_integer_parameter(index, 1, len(zones))
        self.set_integer_parameter(index, 2, aspheric_count)
        self.set_integer_parameter(index, 3, phase_count)
        # Par4 is a Binary 4 diagnostic calculated by OpticStudio from the phase data.
        # It is intentionally verified by header but never written by the project.

        for zone_number, zone in enumerate(zones, start=1):
            columns = binary4_zone_columns(zone_number, aspheric_count, phase_count)
            fixed = (
                (columns.radial_aperture, f"Radial Aperture {zone_number}", zone.radial_aperture),
                (columns.radius, f"Radius {zone_number}", zone.radius),
                (columns.conic, f"Conic {zone_number}", zone.conic),
                (columns.diffraction_order, f"Order {zone_number}", zone.diffraction_order),
            )
            for parameter_number, header, value in fixed:
                self._require_parameter_header(index, parameter_number, header)
                self.set_parameter(index, parameter_number, value)
            for term_number, (parameter_number, value) in enumerate(
                zip(columns.aspheric_terms, zone.aspheric_terms, strict=True), start=1
            ):
                self._require_parameter_header(
                    index, parameter_number, f"Asphere {zone_number} P^{2 * term_number}"
                )
                self.set_parameter(index, parameter_number, value)
            for term_number, (parameter_number, value) in enumerate(
                zip(columns.phase_terms, zone.phase_terms, strict=True), start=1
            ):
                self._require_parameter_header(
                    index, parameter_number, f"Phase {zone_number} P^{2 * term_number}"
                )
                self.set_parameter(index, parameter_number, value)
        return row

    def configure_even_asphere(
        self,
        index: int,
        coefficients: Mapping[int, float],
    ) -> Any:
        if not coefficients:
            raise ValueError("at least one Even Asphere coefficient is required")
        if not all(math.isfinite(float(value)) for value in coefficients.values()):
            raise ValueError("Even Asphere coefficients must be finite")
        row = self.change_surface_type(index, "EvenAspheric")
        ordinal = {2: "2nd", 4: "4th", 6: "6th", 8: "8th"}
        for order, value in sorted(coefficients.items()):
            parameter_number = even_asphere_parameter_number(order)
            header = f"{ordinal.get(order, f'{order}th')} Order Term"
            self._require_parameter_header(index, parameter_number, header)
            self.set_parameter(index, parameter_number, value)
        return row

    def configure_coordinate_break(
        self,
        index: int,
        *,
        decenter_x_mm: float = 0.0,
        decenter_y_mm: float = 0.0,
        tilt_x_deg: float = 0.0,
        tilt_y_deg: float = 0.0,
        tilt_z_deg: float = 0.0,
        order: int = 0,
    ) -> Any:
        values = (decenter_x_mm, decenter_y_mm, tilt_x_deg, tilt_y_deg, tilt_z_deg)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("Coordinate Break values must be finite")
        if order not in (0, 1):
            raise ValueError("Coordinate Break order must be 0 or 1")
        row = self.change_surface_type(index, "CoordinateBreak")
        mapping = (
            (1, "Decenter X", decenter_x_mm),
            (2, "Decenter Y", decenter_y_mm),
            (3, "Tilt About X", tilt_x_deg),
            (4, "Tilt About Y", tilt_y_deg),
            (5, "Tilt About Z", tilt_z_deg),
        )
        for parameter_number, header, value in mapping:
            self._require_parameter_header(index, parameter_number, header)
            self.set_parameter(index, parameter_number, value)
        self._require_parameter_header(index, 6, "Order")
        self.set_integer_parameter(index, 6, order)
        return row

    def make_radius_variable(self, index: int) -> None:
        self.surface(index).RadiusCell.MakeSolveVariable()

    def set_stop_surface(self, index: int) -> None:
        self.surface(index).IsStop = True

    def save_as(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.system.SaveAs(str(destination))


@dataclass(slots=True)
class SystemAnalysisRunner:
    """Generic analysis lifecycle that snapshots results before closing the analysis.

    ZOS-API result proxies are analysis-owned.  Callers therefore provide a parser
    that converts the live result object into a pure Python value while the analysis
    is still open.  Returning a live result after ``Close`` is intentionally forbidden.
    """

    system: Any
    zosapi: Any

    def open_analysis(self, analysis_id_name: str) -> Any:
        try:
            analysis_id = getattr(self.zosapi.Analysis.AnalysisIDM, analysis_id_name)
        except AttributeError as exc:
            raise ZosPrimitiveError(f"unknown analysis ID: {analysis_id_name}") from exc
        return self.system.Analyses.New_Analysis(analysis_id)

    def run_and_parse(self, analysis: Any, parser: Callable[[Any], T]) -> T:
        if not callable(parser):
            raise TypeError("analysis parser must be callable")
        analysis.ApplyAndWaitForCompletion()
        results = analysis.GetResults()
        return parser(results)

    def close(self, analysis: Any) -> None:
        close = getattr(analysis, "Close", None)
        if callable(close):
            close()

    def run_by_id(self, analysis_id_name: str, parser: Callable[[Any], T]) -> T:
        analysis = self.open_analysis(analysis_id_name)
        try:
            return self.run_and_parse(analysis, parser)
        finally:
            self.close(analysis)
