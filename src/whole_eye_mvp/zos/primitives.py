from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ZosPrimitiveError(RuntimeError):
    pass


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

    def make_radius_variable(self, index: int) -> None:
        self.surface(index).RadiusCell.MakeSolveVariable()

    def set_stop_surface(self, index: int) -> None:
        self.lde.StopSurface = int(index)

    def save_as(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.system.SaveAs(str(destination))


@dataclass(slots=True)
class SystemAnalysisRunner:
    """Generic analysis lifecycle; analysis-specific settings remain explicit."""

    system: Any
    zosapi: Any

    def open_analysis(self, analysis_id_name: str) -> Any:
        try:
            analysis_id = getattr(self.zosapi.Analysis.AnalysisIDM, analysis_id_name)
        except AttributeError as exc:
            raise ZosPrimitiveError(f"unknown analysis ID: {analysis_id_name}") from exc
        return self.system.Analyses.New_Analysis(analysis_id)

    def run(self, analysis: Any) -> Any:
        analysis.ApplyAndWaitForCompletion()
        return analysis.GetResults()

    def close(self, analysis: Any) -> None:
        close = getattr(analysis, "Close", None)
        if callable(close):
            close()

    def run_by_id(self, analysis_id_name: str) -> Any:
        analysis = self.open_analysis(analysis_id_name)
        try:
            return self.run(analysis)
        finally:
            self.close(analysis)
