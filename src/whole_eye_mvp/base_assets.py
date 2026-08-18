from __future__ import annotations

import csv
import importlib
import math
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .domain import ArtifactRecord, ArtifactRef, BaseId, BaselineBaseSpec, ScientificBaseline
from .store import ProjectStore
from .zos import SequentialEditor, ZosSession

BASE_WAVELENGTH_NM = 555.0
BASE_FIELD_DEG = 0.0
MODEL_MATERIAL_ABBE_VD = 1.0e8
MODEL_MATERIAL_DPGF = 0.0
GEOMETRY_TOLERANCE_MM = 0.001
INDEX_TOLERANCE = 1.0e-6
MATERIAL_CALIBRATION_TOLERANCE = 1.0e-10
MATERIAL_CALIBRATION_LIMIT = 8

CORNEA_ANT_ROLE = "CORNEA_ANT_MODULE_REF"
CORNEA_POST_ROLE = "CORNEA_POST_REF"
STOP_ROLE = "STOP"
IOL_ANT_ROLE = "IOL_ANT_REF"
IMAGE_ROLE = "IMAGE_FIXED"


class BaseAssetError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BaseSurfacePrescription:
    role: str
    vertex_mm: float
    medium_after_index: float | None = None
    is_stop: bool = False


@dataclass(frozen=True, slots=True)
class BaseAssetPrescription:
    artifact_id: str
    relative_path: str
    base_spec: BaselineBaseSpec
    wavelength_nm: float = BASE_WAVELENGTH_NM
    field_deg: float = BASE_FIELD_DEG

    def validate(self) -> None:
        self.base_spec.validate()
        if not self.artifact_id.strip() or not self.relative_path.strip():
            raise ValueError("base artifact ID and path are required")
        if not self.relative_path.lower().endswith(".zos"):
            raise ValueError("base artifact path must end in .zos")
        if not math.isfinite(self.wavelength_nm) or self.wavelength_nm <= 0:
            raise ValueError("base wavelength must be finite and positive")
        if not math.isfinite(self.field_deg) or self.field_deg != 0:
            raise ValueError("TASK-005B base field must be exactly zero degrees")

    @property
    def surfaces(self) -> tuple[BaseSurfacePrescription, ...]:
        """Return the ordered axial reference stack, excluding OBJECT.

        TASK-005A does not freeze a numerical project corneal thickness.  The two
        corneal reference surfaces are therefore coincident in this base scaffold.
        A later A0/B0/C0 module replaces this reference slot while preserving the
        frozen anterior-cornea-to-IMAGE distance and the posterior landmarks.
        """

        spec = self.base_spec
        return (
            BaseSurfacePrescription(CORNEA_ANT_ROLE, 0.0),
            BaseSurfacePrescription(
                CORNEA_POST_ROLE,
                0.0,
                medium_after_index=spec.aqueous_index,
            ),
            BaseSurfacePrescription(
                STOP_ROLE,
                spec.post_cornea_to_stop_mm,
                medium_after_index=spec.aqueous_index,
                is_stop=True,
            ),
            BaseSurfacePrescription(
                IOL_ANT_ROLE,
                spec.post_cornea_to_iol_ant_mm,
                medium_after_index=spec.vitreous_index,
            ),
            BaseSurfacePrescription(IMAGE_ROLE, spec.axial_length_mm),
        )


@dataclass(frozen=True, slots=True)
class BaseAssetMeasurements:
    wavelength_nm: float
    field_x_deg: float
    field_y_deg: float
    cornea_reference_slot_mm: float
    axial_length_mm: float
    post_cornea_to_stop_mm: float
    post_cornea_to_iol_ant_mm: float
    aqueous_index_after_cornea: float
    aqueous_index_after_stop: float
    vitreous_index: float
    surface_count: int
    stop_surface: int
    image_is_plane: bool
    image_thickness_solve: str


@dataclass(frozen=True, slots=True)
class BaseAssetValidation:
    asset_id: str
    base_id: str
    source_model_id: str
    source_refraction_d: float | None
    path: Path
    passed: bool
    findings: tuple[str, ...]
    measurements: BaseAssetMeasurements | None = None


@dataclass(frozen=True, slots=True)
class BaseAssetBuildReport:
    validations: tuple[BaseAssetValidation, ...]
    artifacts: tuple[ArtifactRef, ...]
    validation_artifact: ArtifactRef | None

    @property
    def passed(self) -> bool:
        return (
            len(self.validations) == len(_BASE_ARTIFACTS)
            and len(self.artifacts) == len(_BASE_ARTIFACTS)
            and all(item.passed for item in self.validations)
        )


_BASE_ARTIFACTS = {
    BaseId.LB_AL2395: (
        "BASE_LB_PSEUDOPHAKIC",
        "models/assets/BASE_LB_PSEUDOPHAKIC.zos",
    ),
    BaseId.ATC_M3_AL24477: (
        "BASE_ATC_M3_PSEUDOPHAKIC",
        "models/assets/BASE_ATC_M3_PSEUDOPHAKIC.zos",
    ),
}


def base_asset_prescriptions(
    baseline: ScientificBaseline,
) -> tuple[BaseAssetPrescription, ...]:
    specs_by_id = {spec.base_id: spec for spec in baseline.base_specs}
    if len(specs_by_id) != len(baseline.base_specs):
        raise ValueError("scientific baseline contains duplicate base IDs")
    missing = tuple(base_id for base_id in _BASE_ARTIFACTS if base_id not in specs_by_id)
    unexpected = tuple(base_id for base_id in specs_by_id if base_id not in _BASE_ARTIFACTS)
    if missing or unexpected:
        raise ValueError(f"base set mismatch; missing={missing}, unexpected={unexpected}")

    prescriptions = tuple(
        BaseAssetPrescription(artifact_id, relative_path, specs_by_id[base_id])
        for base_id, (artifact_id, relative_path) in _BASE_ARTIFACTS.items()
    )
    for prescription in prescriptions:
        prescription.validate()
    return prescriptions


def _configure_nominal_system(system: Any, zosapi: Any, prescription: BaseAssetPrescription) -> None:
    wavelengths = system.SystemData.Wavelengths
    while wavelengths.NumberOfWavelengths > 1:
        wavelengths.RemoveWavelength(wavelengths.NumberOfWavelengths)
    if wavelengths.NumberOfWavelengths == 0:
        wavelengths.AddWavelength(prescription.wavelength_nm / 1000.0, 1.0)
    wavelength = wavelengths.GetWavelength(1)
    wavelength.Wavelength = prescription.wavelength_nm / 1000.0
    wavelength.Weight = 1.0

    fields = system.SystemData.Fields
    while fields.NumberOfFields > 1:
        fields.DeleteFieldAt(fields.NumberOfFields)
    if fields.NumberOfFields == 0:
        fields.AddField(0.0, 0.0, 1.0)
    fields.SetFieldType(zosapi.SystemData.FieldType.Angle)
    field = fields.GetField(1)
    field.X = prescription.field_deg
    field.Y = 0.0
    field.Weight = 1.0


def _refractive_indices(system: Any, surface: int) -> tuple[float, ...]:
    count = int(system.SystemData.Wavelengths.NumberOfWavelengths)
    if count < 1:
        raise BaseAssetError("system has no wavelength for material readback")
    system_module = importlib.import_module("System")
    values = system_module.Array[system_module.Double]([0.0] * count)
    returned = int(system.LDE.GetIndex(int(surface), count, values))
    if returned != count:
        raise BaseAssetError(
            f"LDE.GetIndex returned {returned} wavelengths; expected {count}"
        )
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) and value > 0 for value in result):
        raise BaseAssetError(f"invalid refractive index readback at surface {surface}: {result}")
    return result


def _set_material_index_at_nominal_wavelength(
    editor: SequentialEditor,
    surface: int,
    target_index: float,
) -> float:
    if not math.isfinite(target_index) or target_index <= 1:
        raise ValueError("target material index must be finite and greater than one")
    cell = editor.surface(surface).MaterialCell
    candidate_nd = target_index
    for _ in range(MATERIAL_CALIBRATION_LIMIT):
        solve = cell.CreateSolveType(editor.zosapi.Editors.SolveType.MaterialModel)
        model = solve._S_MaterialModel
        model.IndexNd = candidate_nd
        model.AbbeVd = MODEL_MATERIAL_ABBE_VD
        model.dPgF = MODEL_MATERIAL_DPGF
        status = str(cell.SetSolveData(solve))
        if status != "Success":
            raise BaseAssetError(
                f"failed to set Material Model at surface {surface}: {status}"
            )
        actual = _refractive_indices(editor.system, surface)[0]
        error = target_index - actual
        if abs(error) <= MATERIAL_CALIBRATION_TOLERANCE:
            return actual
        candidate_nd += error
    raise BaseAssetError(
        f"material calibration did not converge at surface {surface}: "
        f"target={target_index:.12g}, actual={actual:.12g}"
    )


def build_base_asset(
    session: ZosSession,
    prescription: BaseAssetPrescription,
    destination: str | Path,
) -> Path:
    prescription.validate()
    destination_path = Path(destination)
    editor = SequentialEditor(session.system, session.zosapi)
    editor.new_system()
    _configure_nominal_system(session.system, session.zosapi, prescription)

    required_surface_count = len(prescription.surfaces) + 1
    while editor.lde.NumberOfSurfaces < required_surface_count:
        editor.insert_surface(1)
    if editor.lde.NumberOfSurfaces != required_surface_count:
        raise BaseAssetError(
            f"unexpected new-system surface count: {editor.lde.NumberOfSurfaces}"
        )

    surfaces = prescription.surfaces
    for index, surface in enumerate(surfaces, start=1):
        editor.set_comment(index, surface.role)
        editor.set_radius_conic(index, radius_mm=0.0, conic=0.0)
        if index < len(surfaces):
            thickness = surfaces[index].vertex_mm - surface.vertex_mm
            if thickness < 0 or not math.isfinite(thickness):
                raise BaseAssetError(f"invalid axial thickness after {surface.role}: {thickness}")
            editor.set_thickness(index, thickness)
        if surface.medium_after_index is not None:
            _set_material_index_at_nominal_wavelength(
                editor,
                index,
                surface.medium_after_index,
            )

    stop_index = next(
        index
        for index, surface in enumerate(surfaces, start=1)
        if surface.is_stop
    )
    editor.set_stop_surface(stop_index)
    editor.save_as(destination_path)
    return destination_path


def _append_close_finding(
    findings: list[str],
    label: str,
    actual: float,
    expected: float,
    tolerance: float,
) -> None:
    if not math.isfinite(actual) or abs(actual - expected) > tolerance:
        findings.append(
            f"{label}: expected {expected:.12g} ± {tolerance:.3g}, got {actual:.12g}"
        )


def _measure_loaded_base(
    session: ZosSession,
    prescription: BaseAssetPrescription,
) -> tuple[BaseAssetMeasurements, tuple[str, ...]]:
    lde = session.system.LDE
    surfaces = prescription.surfaces
    findings: list[str] = []
    expected_count = len(surfaces) + 1
    surface_count = int(lde.NumberOfSurfaces)
    if surface_count != expected_count:
        findings.append(f"surface_count: expected {expected_count}, got {surface_count}")
        raise BaseAssetError("; ".join(findings))

    rows = tuple(lde.GetSurfaceAt(index) for index in range(1, expected_count))
    for index, (row, surface) in enumerate(zip(rows, surfaces, strict=True), start=1):
        if str(row.Comment).strip() != surface.role:
            findings.append(
                f"surface {index} role: expected {surface.role!r}, got {str(row.Comment).strip()!r}"
            )
        if str(row.Type) != "Standard":
            findings.append(f"surface {index} type: expected Standard, got {row.Type}")
        radius = float(row.Radius)
        if not (radius == 0.0 or math.isinf(radius)):
            findings.append(f"surface {index} radius is not plane: {radius}")
        if not math.isfinite(float(row.Conic)) or float(row.Conic) != 0:
            findings.append(f"surface {index} conic is not zero: {row.Conic}")

    vertex_by_role: dict[str, float] = {}
    vertex = 0.0
    for index, surface in enumerate(surfaces, start=1):
        vertex_by_role[surface.role] = vertex
        if index < len(surfaces):
            thickness = float(rows[index - 1].Thickness)
            if not math.isfinite(thickness) or thickness < 0:
                findings.append(f"surface {index} thickness is invalid: {thickness}")
            vertex += thickness

    wavelengths = session.system.SystemData.Wavelengths
    if int(wavelengths.NumberOfWavelengths) != 1:
        findings.append(
            f"wavelength count: expected 1, got {int(wavelengths.NumberOfWavelengths)}"
        )
    wavelength_nm = float(wavelengths.GetWavelength(1).Wavelength) * 1000.0

    fields = session.system.SystemData.Fields
    if int(fields.NumberOfFields) != 1:
        findings.append(f"field count: expected 1, got {int(fields.NumberOfFields)}")
    field = fields.GetField(1)
    field_x = float(field.X)
    field_y = float(field.Y)

    cornea_reference_slot = (
        vertex_by_role[CORNEA_POST_ROLE] - vertex_by_role[CORNEA_ANT_ROLE]
    )
    axial_length = vertex_by_role[IMAGE_ROLE] - vertex_by_role[CORNEA_ANT_ROLE]
    post_to_stop = vertex_by_role[STOP_ROLE] - vertex_by_role[CORNEA_POST_ROLE]
    post_to_iol = vertex_by_role[IOL_ANT_ROLE] - vertex_by_role[CORNEA_POST_ROLE]
    aqueous_after_cornea = _refractive_indices(session.system, 2)[0]
    aqueous_after_stop = _refractive_indices(session.system, 3)[0]
    vitreous_index = _refractive_indices(session.system, 4)[0]
    stop_surface = int(lde.StopSurface)
    image_row = rows[-1]
    image_radius = float(image_row.Radius)
    image_is_plane = bool(image_row.IsImage) and (
        image_radius == 0.0 or math.isinf(image_radius)
    )
    image_thickness_solve = str(rows[-2].ThicknessCell.Solve)

    spec = prescription.base_spec
    _append_close_finding(
        findings, "wavelength_nm", wavelength_nm, prescription.wavelength_nm, 1.0e-9
    )
    _append_close_finding(findings, "field_x_deg", field_x, prescription.field_deg, 1.0e-12)
    _append_close_finding(findings, "field_y_deg", field_y, 0.0, 1.0e-12)
    _append_close_finding(
        findings,
        "cornea_reference_slot_mm",
        cornea_reference_slot,
        0.0,
        1.0e-12,
    )
    _append_close_finding(
        findings,
        "axial_length_mm",
        axial_length,
        spec.axial_length_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    _append_close_finding(
        findings,
        "post_cornea_to_stop_mm",
        post_to_stop,
        spec.post_cornea_to_stop_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    _append_close_finding(
        findings,
        "post_cornea_to_iol_ant_mm",
        post_to_iol,
        spec.post_cornea_to_iol_ant_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    _append_close_finding(
        findings,
        "aqueous_index_after_cornea",
        aqueous_after_cornea,
        spec.aqueous_index,
        INDEX_TOLERANCE,
    )
    _append_close_finding(
        findings,
        "aqueous_index_after_stop",
        aqueous_after_stop,
        spec.aqueous_index,
        INDEX_TOLERANCE,
    )
    _append_close_finding(
        findings,
        "vitreous_index",
        vitreous_index,
        spec.vitreous_index,
        INDEX_TOLERANCE,
    )
    if stop_surface != 3 or not bool(rows[2].IsStop):
        findings.append(f"STOP surface: expected 3, got {stop_surface}")
    if not image_is_plane:
        findings.append("IMAGE must be the plane final surface")
    if image_thickness_solve not in {"Fixed", "None"}:
        findings.append(
            f"IOL-to-IMAGE thickness must be fixed, got solve {image_thickness_solve!r}"
        )

    for index in (2, 3, 4):
        solve_type = str(rows[index - 1].MaterialCell.Solve)
        if solve_type != "MaterialModel":
            findings.append(
                f"surface {index} medium must use MaterialModel, got {solve_type!r}"
            )

    measurements = BaseAssetMeasurements(
        wavelength_nm=wavelength_nm,
        field_x_deg=field_x,
        field_y_deg=field_y,
        cornea_reference_slot_mm=cornea_reference_slot,
        axial_length_mm=axial_length,
        post_cornea_to_stop_mm=post_to_stop,
        post_cornea_to_iol_ant_mm=post_to_iol,
        aqueous_index_after_cornea=aqueous_after_cornea,
        aqueous_index_after_stop=aqueous_after_stop,
        vitreous_index=vitreous_index,
        surface_count=surface_count,
        stop_surface=stop_surface,
        image_is_plane=image_is_plane,
        image_thickness_solve=image_thickness_solve,
    )
    return measurements, tuple(findings)


def validate_base_asset(
    session: ZosSession,
    prescription: BaseAssetPrescription,
    path: str | Path,
) -> BaseAssetValidation:
    prescription.validate()
    asset_path = Path(path)
    if not asset_path.is_file():
        return BaseAssetValidation(
            asset_id=prescription.artifact_id,
            base_id=prescription.base_spec.base_id,
            source_model_id=prescription.base_spec.source_model_id,
            source_refraction_d=prescription.base_spec.source_refraction_d,
            path=asset_path,
            passed=False,
            findings=(f"base asset is missing: {asset_path}",),
        )
    try:
        session.system.LoadFile(str(asset_path.resolve()), False)
        measurements, findings = _measure_loaded_base(session, prescription)
    except Exception as exc:  # noqa: BLE001 - ZOS-API failures become validation findings
        return BaseAssetValidation(
            asset_id=prescription.artifact_id,
            base_id=prescription.base_spec.base_id,
            source_model_id=prescription.base_spec.source_model_id,
            source_refraction_d=prescription.base_spec.source_refraction_d,
            path=asset_path,
            passed=False,
            findings=(f"{type(exc).__name__}: {exc}",),
        )
    return BaseAssetValidation(
        asset_id=prescription.artifact_id,
        base_id=prescription.base_spec.base_id,
        source_model_id=prescription.base_spec.source_model_id,
        source_refraction_d=prescription.base_spec.source_refraction_d,
        path=asset_path,
        passed=not findings,
        findings=findings,
        measurements=measurements,
    )


def validate_base_assets(
    session: ZosSession,
    store: ProjectStore,
    baseline: ScientificBaseline,
) -> tuple[BaseAssetValidation, ...]:
    return tuple(
        _validate_registered_base(session, store, prescription)[0]
        for prescription in base_asset_prescriptions(baseline)
    )


def _validate_registered_base(
    session: ZosSession,
    store: ProjectStore,
    prescription: BaseAssetPrescription,
) -> tuple[BaseAssetValidation, ArtifactRef | None]:
    destination = store.resolve(prescription.relative_path)
    validation = validate_base_asset(session, prescription, destination)
    existing = store.find_artifact(prescription.artifact_id)
    extra_findings: list[str] = []
    if existing is None:
        extra_findings.append("base artifact is not registered in the artifact index")
    else:
        if existing.relative_path != prescription.relative_path:
            extra_findings.append(
                "artifact index path does not match the frozen base prescription"
            )
        if existing.artifact_type != "zemax_base":
            extra_findings.append("artifact index type is not zemax_base")
        if existing.baseline_id != store.baseline.baseline_id:
            extra_findings.append("artifact baseline does not match the project baseline")
        if not existing.locked:
            extra_findings.append("existing base artifact is not locked")
        if not store.verify_artifact(existing):
            extra_findings.append("existing base artifact hash does not match its lock")
    if extra_findings:
        validation = replace(
            validation,
            passed=False,
            findings=validation.findings + tuple(extra_findings),
        )
    return validation, existing


def _write_validation_csv(
    path: Path,
    validations: Sequence[BaseAssetValidation],
) -> None:
    fieldnames = (
        "asset_id",
        "base_id",
        "status",
        "source_model_id",
        "source_refraction_d",
        "wavelength_nm",
        "field_x_deg",
        "field_y_deg",
        "cornea_reference_slot_mm",
        "axial_length_mm",
        "post_cornea_to_stop_mm",
        "post_cornea_to_iol_ant_mm",
        "aqueous_index_after_cornea",
        "aqueous_index_after_stop",
        "vitreous_index",
        "surface_count",
        "stop_surface",
        "image_is_plane",
        "image_thickness_solve",
        "findings",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for validation in validations:
            measurement = validation.measurements
            writer.writerow(
                {
                    "asset_id": validation.asset_id,
                    "base_id": validation.base_id,
                    "status": "PASS" if validation.passed else "FAIL",
                    "source_model_id": validation.source_model_id,
                    "source_refraction_d": ""
                    if validation.source_refraction_d is None
                    else validation.source_refraction_d,
                    "wavelength_nm": "" if measurement is None else measurement.wavelength_nm,
                    "field_x_deg": "" if measurement is None else measurement.field_x_deg,
                    "field_y_deg": "" if measurement is None else measurement.field_y_deg,
                    "cornea_reference_slot_mm": ""
                    if measurement is None
                    else measurement.cornea_reference_slot_mm,
                    "axial_length_mm": ""
                    if measurement is None
                    else measurement.axial_length_mm,
                    "post_cornea_to_stop_mm": ""
                    if measurement is None
                    else measurement.post_cornea_to_stop_mm,
                    "post_cornea_to_iol_ant_mm": ""
                    if measurement is None
                    else measurement.post_cornea_to_iol_ant_mm,
                    "aqueous_index_after_cornea": ""
                    if measurement is None
                    else measurement.aqueous_index_after_cornea,
                    "aqueous_index_after_stop": ""
                    if measurement is None
                    else measurement.aqueous_index_after_stop,
                    "vitreous_index": ""
                    if measurement is None
                    else measurement.vitreous_index,
                    "surface_count": "" if measurement is None else measurement.surface_count,
                    "stop_surface": "" if measurement is None else measurement.stop_surface,
                    "image_is_plane": ""
                    if measurement is None
                    else measurement.image_is_plane,
                    "image_thickness_solve": ""
                    if measurement is None
                    else measurement.image_thickness_solve,
                    "findings": " | ".join(validation.findings),
                }
            )


def build_base_assets(
    session: ZosSession,
    store: ProjectStore,
    baseline: ScientificBaseline,
) -> BaseAssetBuildReport:
    if store.baseline != baseline:
        raise BaseAssetError("project store and requested scientific baseline differ")
    prescriptions = base_asset_prescriptions(baseline)
    validations: list[BaseAssetValidation] = []
    artifacts: list[ArtifactRef] = []
    validation_artifact: ArtifactRef | None = None

    with tempfile.TemporaryDirectory(prefix="task-005b-bases-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        for prescription in prescriptions:
            destination = store.resolve(prescription.relative_path)
            existing = store.find_artifact(prescription.artifact_id)
            if existing is not None:
                validation, existing = _validate_registered_base(
                    session, store, prescription
                )
                validations.append(validation)
                if validation.passed and existing is not None:
                    artifacts.append(existing)
                continue
            if destination.exists():
                raise BaseAssetError(
                    f"refusing to overwrite unindexed base asset: {destination}"
                )

            scratch_path = temp_dir / Path(prescription.relative_path).name
            build_base_asset(session, prescription, scratch_path)
            validation = validate_base_asset(session, prescription, scratch_path)
            if not validation.passed:
                validations.append(validation)
                continue
            artifact = store.record_artifact(
                scratch_path,
                ArtifactRecord(
                    artifact_id=prescription.artifact_id,
                    artifact_type="zemax_base",
                    relative_path=prescription.relative_path,
                    baseline_id=baseline.baseline_id,
                ),
                lock=True,
            )
            if not store.verify_artifact(artifact):
                raise BaseAssetError(
                    f"recorded base artifact failed hash verification: {artifact.artifact_id}"
                )
            validations.append(replace(validation, path=destination))
            artifacts.append(artifact)

        report_path = temp_dir / "TASK_005B_BASE_VALIDATION.csv"
        _write_validation_csv(report_path, validations)
        validation_artifact = store.record_artifact(
            report_path,
            ArtifactRecord(
                artifact_id="TASK_005B_BASE_VALIDATION",
                artifact_type="validation_csv",
                relative_path="results/TASK_005B_BASE_VALIDATION.csv",
                baseline_id=baseline.baseline_id,
            ),
            lock=False,
        )

    return BaseAssetBuildReport(
        validations=tuple(validations),
        artifacts=tuple(artifacts),
        validation_artifact=validation_artifact,
    )
