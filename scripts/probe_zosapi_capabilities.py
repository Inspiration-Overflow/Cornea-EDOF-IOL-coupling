"""Print installed OpticStudio API surface and analysis metadata as JSON.

This diagnostic is read-only: it creates a transient sequential system in a
standalone session, inspects API metadata, and closes without saving.
"""

from __future__ import annotations

import importlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REFERENCE_ENV = "WHOLE_EYE_ZOS_REFERENCE_FILE"
SURFACE_TYPES = ("Binary4", "EvenAspheric", "CoordinateBreak")
ANALYSIS_IDS = (
    "HuygensPsf",
    "HuygensMtf",
    "ZernikeStandardCoefficients",
    "FootprintSettings",
    "PrescriptionDataSettings",
)


def _public_properties(value: Any) -> dict[str, dict[str, Any]]:
    properties: dict[str, dict[str, Any]] = {}
    for property_info in value.GetType().GetProperties():
        if property_info.GetIndexParameters().Length != 0:
            continue
        property_type = property_info.PropertyType
        metadata: dict[str, Any] = {"type": str(property_type.FullName)}
        if property_type.IsEnum:
            metadata["enum_values"] = list(property_type.GetEnumNames())
        properties[property_info.Name] = metadata
    return dict(sorted(properties.items()))


def _public_method_names(value: Any) -> list[str]:
    return sorted(
        {
            str(method.Name)
            for method in value.GetType().GetMethods()
            if bool(method.IsPublic)
        }
    )


def _public_methods(value: Any, method_name: str) -> list[dict[str, Any]]:
    methods: list[dict[str, Any]] = []
    for method in value.GetType().GetMethods():
        if not bool(method.IsPublic) or str(method.Name) != method_name:
            continue
        methods.append(
            {
                "return_type": str(method.ReturnType.FullName),
                "parameters": [
                    {
                        "name": str(parameter.Name),
                        "type": str(parameter.ParameterType.FullName),
                        "is_out": bool(parameter.IsOut),
                    }
                    for parameter in method.GetParameters()
                ],
            }
        )
    return methods


def _material_model_metadata(system: Any, zosapi: Any) -> dict[str, Any]:
    system.New(False)
    system.SystemData.Wavelengths.GetWavelength(1).Wavelength = 0.555
    row = system.LDE.GetSurfaceAt(1)
    cell = row.MaterialCell
    solve = cell.CreateSolveType(zosapi.Editors.SolveType.MaterialModel)
    material_model = solve._S_MaterialModel
    material_model.IndexNd = 1.336
    material_model.AbbeVd = 1.0e8
    material_model.dPgF = 0.0
    solve_status = cell.SetSolveData(solve)
    system_module = importlib.import_module("System")
    indices = system_module.Array[system_module.Double]([0.0])
    index_result = system.LDE.GetIndex(1, 1, indices)
    return {
        "material_value_after_solve": str(cell.Value),
        "solve_status": str(solve_status),
        "index_result_type": str(type(index_result)),
        "index_result": int(index_result),
        "indices": [float(value) for value in indices],
        "lde_stop_methods": [
            name for name in _public_method_names(system.LDE) if "Stop" in name
        ],
        "surface_stop_methods": [
            name for name in _public_method_names(row) if "Stop" in name
        ],
        "surface_properties": _public_properties(row),
        "material_cell_properties": _public_properties(cell),
        "material_cell_methods": {
            name: _public_methods(cell, name)
            for name in ("CreateSolveType", "GetSolveData", "SetSolveData")
        },
        "material_solve_runtime_type": str(solve.GetType().FullName),
        "material_model_interface_type": str(material_model.GetType().FullName),
        "material_model_interface_properties": _public_properties(material_model),
        "material_solve_properties": _public_properties(solve),
        "material_solve_methods": _public_method_names(solve),
        "lde_methods": {
            name: _public_methods(system.LDE, name)
            for name in ("GetIndex", "GetIndexModel", "GetIndexData")
        },
        "wavelength_properties": _public_properties(system.SystemData.Wavelengths),
        "wavelength_methods": _public_method_names(system.SystemData.Wavelengths),
        "field_properties": _public_properties(system.SystemData.Fields),
        "field_methods": _public_method_names(system.SystemData.Fields),
    }


def _surface_parameters(system: Any, zosapi: Any, surface_type_name: str) -> list[dict[str, Any]]:
    system.New(False)
    row = system.LDE.GetSurfaceAt(1)
    surface_type = getattr(zosapi.Editors.LDE.SurfaceType, surface_type_name)
    row.ChangeType(row.GetSurfaceTypeSettings(surface_type))
    if surface_type_name == "Binary4":
        row.GetSurfaceCell(zosapi.Editors.LDE.SurfaceColumn.Par1).IntegerValue = 3
        row.GetSurfaceCell(zosapi.Editors.LDE.SurfaceColumn.Par2).IntegerValue = 8
        row.GetSurfaceCell(zosapi.Editors.LDE.SurfaceColumn.Par3).IntegerValue = 0
    parameters: list[dict[str, Any]] = []
    for parameter_number in range(100):
        column = getattr(zosapi.Editors.LDE.SurfaceColumn, f"Par{parameter_number}")
        cell = row.GetSurfaceCell(column)
        header = str(getattr(cell, "Header", "")).strip()
        if bool(cell.IsActive) and "unused" not in header.lower():
            parameters.append(
                {
                    "column": f"Par{parameter_number}",
                    "header": header,
                    "data_type": str(cell.DataType),
                }
            )
    return parameters


def _analysis_settings(system: Any, zosapi: Any, analysis_id_name: str) -> dict[str, Any]:
    analysis_id = getattr(zosapi.Analysis.AnalysisIDM, analysis_id_name)
    analysis = system.Analyses.New_Analysis(analysis_id)
    try:
        settings = analysis.GetSettings()
        properties = _public_properties(settings)
        for child_name in ("Field", "Wavelength"):
            child = getattr(settings, child_name, None)
            if child is not None:
                properties[child_name]["properties"] = _public_properties(child)
        return properties
    finally:
        analysis.Close()


def _huygens_psf_result(system: Any, zosapi: Any, reference_file: Path) -> dict[str, Any]:
    system.LoadFile(str(reference_file), False)
    analysis = system.Analyses.New_Analysis(zosapi.Analysis.AnalysisIDM.HuygensPsf)
    try:
        settings = analysis.GetSettings()
        settings.PupilSampleSize = zosapi.Analysis.SampleSizes.S_32x32
        settings.ImageSampleSize = zosapi.Analysis.SampleSizes.S_32x32
        settings.ImageDelta = 0.5
        settings.Type = zosapi.Analysis.Settings.HuygensPsfTypes.Linear
        settings.Normalize = True
        analysis.ApplyAndWaitForCompletion()
        results = analysis.GetResults()
        grid = results.GetDataGrid(0)
        values = grid.Values
        dimensions = [values.GetLength(index) for index in range(values.Rank)]
        sample_values = [float(values.GetValue(0, 0)), float(values.GetValue(1, 1))]
        return {
            "result_runtime_type": str(results.GetType().FullName),
            "result_interfaces": [
                str(interface.FullName) for interface in results.GetType().GetInterfaces()
            ],
            "result_properties": _public_properties(results),
            "grid_runtime_type": str(grid.GetType().FullName),
            "grid_interfaces": [
                str(interface.FullName) for interface in grid.GetType().GetInterfaces()
            ],
            "grid_properties": _public_properties(grid),
            "grid_dimensions": dimensions,
            "sample_values": sample_values,
        }
    finally:
        analysis.Close()


def _zernike_result(system: Any, zosapi: Any, reference_file: Path) -> dict[str, Any]:
    system.LoadFile(str(reference_file), False)
    analysis = system.Analyses.New_ZernikeStandardCoefficients()
    try:
        settings = analysis.GetSettings().__implementation__
        settings.SampleSize = zosapi.Analysis.SampleSizes.S_32x32
        settings.MaximumNumberOfTerms = 37
        settings.Wavelength.SetWavelengthNumber(1)
        settings.Field.SetFieldNumber(1)
        analysis.ApplyAndWaitForCompletion()
        results = analysis.GetResults().__implementation__
        payload = {
            "runtime_type": str(results.GetType().FullName),
            "properties": _public_properties(results),
            "methods": _public_method_names(results),
            "counts": {
                name: int(getattr(results, name))
                for name in (
                    "NumberOfDataGrids",
                    "NumberOfDataSeries",
                    "NumberOfMessages",
                )
            },
        }
        header = results.HeaderData
        payload["header_runtime_type"] = str(header.GetType().FullName)
        payload["header_properties"] = _public_properties(header)
        payload["header_methods"] = _public_method_names(header)
        payload["header_lines"] = [str(line) for line in header.Lines]
        with tempfile.TemporaryDirectory(prefix="whole-eye-zernike-") as temp_dir:
            text_path = Path(temp_dir) / "zernike.txt"
            payload["text_export_succeeded"] = bool(results.GetTextFile(str(text_path)))
            payload["text_lines"] = text_path.read_text(encoding="utf-16").splitlines()
        return payload
    finally:
        analysis.Close()


def main() -> None:
    install_dir = os.environ.get(INSTALL_ENV)
    if not install_dir:
        raise SystemExit(f"Set {INSTALL_ENV} to the OpticStudio installation directory.")

    with open_zos_session(Path(install_dir)) as session:
        payload = {
            "license_status": str(session.app.LicenseStatus),
            "material_model": _material_model_metadata(session.system, session.zosapi),
            "surface_parameters": {
                name: _surface_parameters(session.system, session.zosapi, name)
                for name in SURFACE_TYPES
            },
            "analysis_settings": {
                name: _analysis_settings(session.system, session.zosapi, name)
                for name in ANALYSIS_IDS
            },
        }
        reference_file = os.environ.get(REFERENCE_ENV)
        if reference_file:
            payload["huygens_psf_result"] = _huygens_psf_result(
                session.system, session.zosapi, Path(reference_file)
            )
            payload["zernike_result"] = _zernike_result(
                session.system, session.zosapi, Path(reference_file)
            )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
