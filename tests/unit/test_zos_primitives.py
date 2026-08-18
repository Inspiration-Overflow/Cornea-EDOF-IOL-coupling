from __future__ import annotations

from types import SimpleNamespace

import pytest

from whole_eye_mvp.zos.primitives import (
    Binary4Zone,
    SequentialEditor,
    SystemAnalysisRunner,
    ZosPrimitiveError,
    binary4_zone_columns,
    even_asphere_parameter_number,
)

BINARY_HEADERS = {
    "P1": "# Radial Zones",
    "P2": "# Aspheric Terms",
    "P3": "# Phase Terms",
    "P4": "Sine(delta0)",
    "P13": "Radial Aperture 1",
    "P14": "Radius 1",
    "P15": "Conic 1",
    "P16": "Order 1",
}


class Cell:
    def __init__(self, header: str = ""):
        self.DoubleValue = None
        self.IntegerValue = None
        self.Header = header
        self.variable = False

    def MakeSolveVariable(self):
        self.variable = True


class Row:
    def __init__(self):
        self.Radius = 0
        self.Conic = 0
        self.Thickness = 0
        self.Material = ""
        self.Comment = ""
        self.IsStop = False
        self.RadiusCell = Cell()
        self.cells = {}

    def GetSurfaceTypeSettings(self, surface_type):
        return ("settings", surface_type)

    def ChangeType(self, settings):
        self.type_settings = settings

    def GetSurfaceCell(self, column):
        return self.cells.setdefault(column, Cell(BINARY_HEADERS.get(column, "")))


class LDE:
    def __init__(self):
        self.rows = [Row() for _ in range(5)]
        self.StopSurface = 1

    def GetSurfaceAt(self, index):
        return self.rows[index]

    def InsertNewSurfaceAt(self, index):
        self.rows.insert(index, Row())
        return self.rows[index]

    def RemoveSurfacesAt(self, index, count):
        del self.rows[index : index + count]


class AnalysisResult:
    def __init__(self, owner):
        self.owner = owner

    def read(self):
        if self.owner.closed:
            raise RuntimeError("result proxy is invalid after Close")
        return {"ok": self.owner.ran}


class Analysis:
    def __init__(self):
        self.ran = False
        self.closed = False

    def ApplyAndWaitForCompletion(self):
        self.ran = True

    def GetResults(self):
        return AnalysisResult(self)

    def Close(self):
        self.closed = True


class Analyses:
    def __init__(self):
        self.last = None

    def New_Analysis(self, ident):
        self.last = Analysis()
        self.last.ident = ident
        return self.last


class System:
    def __init__(self):
        self.LDE = LDE()
        self.new_calls = []
        self.make_sequential_calls = 0
        self.saved = []
        self.Analyses = Analyses()

    def New(self, save_if_needed):
        self.new_calls.append(save_if_needed)

    def MakeSequential(self):
        self.make_sequential_calls += 1

    def SaveAs(self, path):
        self.saved.append(path)


SURFACE_COLUMNS = {f"Par{index}": f"P{index}" for index in range(1, 17)}
ZOS = SimpleNamespace(
    Editors=SimpleNamespace(
        LDE=SimpleNamespace(
            SurfaceType=SimpleNamespace(EvenAspheric="EVEN", Binary4="BINARY4"),
            SurfaceColumn=SimpleNamespace(**SURFACE_COLUMNS),
        )
    ),
    Analysis=SimpleNamespace(AnalysisIDM=SimpleNamespace(HuygensPsf="HPSF")),
)


@pytest.mark.unit
def test_sequential_editor_sets_surfaces_and_parameters(tmp_path) -> None:
    system = System()
    editor = SequentialEditor(system, ZOS)
    editor.new_system()
    row = editor.change_surface_type(1, "EvenAspheric")
    editor.set_radius_conic(1, radius_mm=7.8, conic=-0.2)
    editor.set_thickness(1, 0.55)
    editor.set_material(1, "CORNEA")
    editor.set_comment(1, "anterior")
    editor.set_parameter(1, 2, 0.001)
    editor.make_radius_variable(1)
    editor.set_stop_surface(2)
    editor.save_as(tmp_path / "x.zos")
    assert system.new_calls == [False]
    assert system.make_sequential_calls == 1
    assert row.type_settings == ("settings", "EVEN")
    assert row.Radius == 7.8 and row.Conic == -0.2
    assert row.cells["P2"].DoubleValue == 0.001 and row.RadiusCell.variable
    assert system.LDE.GetSurfaceAt(2).IsStop and system.saved[-1].endswith("x.zos")


@pytest.mark.unit
def test_unknown_surface_parameter_and_type_are_typed_errors() -> None:
    editor = SequentialEditor(System(), ZOS)
    with pytest.raises(ZosPrimitiveError):
        editor.change_surface_type(1, "NoSuchSurface")
    with pytest.raises(ZosPrimitiveError):
        editor.set_parameter(1, 255, 1.0)


@pytest.mark.unit
def test_generic_analysis_lifecycle_snapshots_before_close() -> None:
    system = System()
    runner = SystemAnalysisRunner(system, ZOS)
    result = runner.run_by_id("HuygensPsf", lambda proxy: proxy.read())
    assert result == {"ok": True}
    assert system.Analyses.last.closed
    with pytest.raises(ZosPrimitiveError):
        runner.run_by_id("NoSuchAnalysis", lambda proxy: proxy.read())


@pytest.mark.unit
def test_verified_binary4_and_even_asphere_column_mappings() -> None:
    first = binary4_zone_columns(1, 8, 0)
    second = binary4_zone_columns(2, 8, 0)
    assert first.radial_aperture == 13
    assert first.aspheric_terms == tuple(range(17, 25))
    assert second.radial_aperture == 25
    assert second.aspheric_terms == tuple(range(29, 37))
    assert even_asphere_parameter_number(2) == 1
    assert even_asphere_parameter_number(16) == 8
    with pytest.raises(ValueError):
        binary4_zone_columns(0, 8, 0)
    with pytest.raises(ValueError, match="at most 20"):
        binary4_zone_columns(1, 21, 0)
    with pytest.raises(ValueError):
        even_asphere_parameter_number(5)


@pytest.mark.unit
def test_binary4_par4_is_verified_but_never_written() -> None:
    system = System()
    editor = SequentialEditor(system, ZOS)
    row = editor.configure_binary4(1, (Binary4Zone(1.5, 7.8, -0.2),))

    assert row.cells["P1"].IntegerValue == 1
    assert row.cells["P2"].IntegerValue == 0
    assert row.cells["P3"].IntegerValue == 0
    assert row.cells["P4"].DoubleValue is None
    assert row.cells["P13"].DoubleValue == pytest.approx(1.5)
