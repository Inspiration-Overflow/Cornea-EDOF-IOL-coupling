from __future__ import annotations

import csv
import importlib
import math
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .carriers import ProvisionalCarrier
from .domain import ArtifactRecord, ArtifactRef, BaselineStandardEyeSpec, ScientificBaseline
from .store import ProjectStore
from .zos import SequentialEditor, ZernikeStandardRunner, ZernikeStandardSettings, ZosSession

ARTIFACT_ID = "STD_IOL_EYE_2024"
RELATIVE_PATH = "models/assets/STD_IOL_EYE_2024.zos"
VALIDATION_ID = "TASK_005C_STANDARD_EYE_VALIDATION"
VALIDATION_PATH = "results/TASK_005C_STANDARD_EYE_VALIDATION.csv"

CORNEA_ANT = "STD_CORNEA_ANT"
CORNEA_POST = "STD_CORNEA_POST"
IOL_REF = "IOL_ANT_REFERENCE"
IMAGE_REF = "IMAGE_REFERENCE"

# Norrby et al. (Applied Optics 2007), Liou cornea row. The published
# c[4,0]=+0.258 um is explicitly normalized to a 6-mm entrance pupil.
CORNEA_FRONT_RADIUS_MM = 7.77
CORNEA_FRONT_CONIC = -0.18
CORNEA_BACK_RADIUS_MM = 6.40
CORNEA_BACK_CONIC = -0.60
CORNEA_THICKNESS_MM = 0.50
CORNEA_INDEX = 1.376
CORNEAL_SA_PUPIL_MM = 6.0
STANDARD_EYE_CALIBRATION_WAVELENGTH_NM = 546.0

# Implementation reference only: keep a normal-eye axial scale while the scientific
# baseline continues to be defined solely by its frozen acceptance anchors.
REFERENCE_AXIAL_LENGTH_MM = 23.950

C40_TOLERANCE_UM = 0.005
GEOMETRY_TOLERANCE_MM = 0.001
INDEX_TOLERANCE = 1.0e-6
MATERIAL_TOLERANCE = 1.0e-10
MATERIAL_ITERATIONS = 8
MODEL_ABBE_VD = 1.0e8


class StandardEyeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StandardEyeConstruction:
    eye: BaselineStandardEyeSpec
    cornea_front_radius_mm: float = CORNEA_FRONT_RADIUS_MM
    cornea_front_conic: float = CORNEA_FRONT_CONIC
    cornea_back_radius_mm: float = CORNEA_BACK_RADIUS_MM
    cornea_back_conic: float = CORNEA_BACK_CONIC
    cornea_thickness_mm: float = CORNEA_THICKNESS_MM
    cornea_index: float = CORNEA_INDEX
    corneal_sa_pupil_mm: float = CORNEAL_SA_PUPIL_MM
    reference_axial_length_mm: float = REFERENCE_AXIAL_LENGTH_MM

    def validate(self) -> None:
        values = (
            self.cornea_front_radius_mm,
            self.cornea_front_conic,
            self.cornea_back_radius_mm,
            self.cornea_back_conic,
            self.cornea_thickness_mm,
            self.cornea_index,
            self.corneal_sa_pupil_mm,
            self.reference_axial_length_mm,
            self.eye.corneal_c40_um,
            self.eye.iol_footprint_mm,
            self.eye.iol_footprint_tolerance_mm,
            self.eye.medium_index,
            self.eye.aperture_mm,
            self.eye.wavelength_nm,
        )
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("standard-eye values must be finite")
        if self.eye.eye_id != ARTIFACT_ID:
            raise ValueError("unexpected standard-eye ID")
        if self.cornea_front_radius_mm <= 0 or self.cornea_back_radius_mm <= 0:
            raise ValueError("corneal radii must be positive")
        if self.cornea_thickness_mm <= 0:
            raise ValueError("corneal thickness must be positive")
        if self.cornea_index <= 1 or self.eye.medium_index <= 1:
            raise ValueError("refractive indices must exceed one")
        if self.eye.aperture_mm <= 0 or self.corneal_sa_pupil_mm <= 0:
            raise ValueError("standard-eye calibration pupil must be positive")
        if not math.isclose(
            self.eye.aperture_mm,
            self.corneal_sa_pupil_mm,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise ValueError(
                "standard-eye C40, footprint, and carrier SA calibration must share the 6-mm pupil"
            )
        if not math.isclose(
            self.eye.aperture_mm,
            CORNEAL_SA_PUPIL_MM,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise ValueError("standard-eye calibration pupil must be 6 mm")
        if not math.isclose(
            self.eye.wavelength_nm,
            STANDARD_EYE_CALIBRATION_WAVELENGTH_NM,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise ValueError("standard-eye calibration wavelength must be 546 nm")
        if self.eye.iol_footprint_mm <= 0 or self.eye.iol_footprint_tolerance_mm <= 0:
            raise ValueError("IOL footprint target/tolerance must be positive")
        if self.reference_axial_length_mm <= self.cornea_thickness_mm:
            raise ValueError("reference axial length is invalid")

    @property
    def iol_from_post_cornea_mm(self) -> float:
        self.validate()
        return paraxial_iol_plane_distance_mm(self)

    @property
    def iol_vertex_mm(self) -> float:
        return self.cornea_thickness_mm + self.iol_from_post_cornea_mm

    @property
    def iol_to_image_mm(self) -> float:
        distance = self.reference_axial_length_mm - self.iol_vertex_mm
        if distance <= 0:
            raise ValueError("IOL reference plane must precede IMAGE_REFERENCE")
        return distance


def standard_eye_construction(baseline: ScientificBaseline) -> StandardEyeConstruction:
    result = StandardEyeConstruction(baseline.standard_eye_spec)
    result.validate()
    return result


def _paraxial_post_cornea_ray(
    spec: StandardEyeConstruction,
) -> tuple[float, float]:
    spec.validate()
    y = spec.corneal_sa_pupil_mm / 2.0
    nu = 0.0
    nu -= (spec.cornea_index - 1.0) / spec.cornea_front_radius_mm * y
    y += spec.cornea_thickness_mm / spec.cornea_index * nu
    nu -= (
        (spec.eye.medium_index - spec.cornea_index)
        / spec.cornea_back_radius_mm
        * y
    )
    if abs(nu) < 1.0e-15:
        raise ValueError("model cornea does not converge the marginal ray")
    return y, nu


def paraxial_iol_plane_distance_mm(spec: StandardEyeConstruction) -> float:
    """Return a deterministic starting geometry for the 5.15-mm real-ray gate."""

    y, nu = _paraxial_post_cornea_ray(spec)
    target_y = spec.eye.iol_footprint_mm / 2.0
    distance = (target_y - y) * spec.eye.medium_index / nu
    if not math.isfinite(distance) or distance <= 0:
        raise ValueError("invalid paraxial IOL-plane distance")
    return distance


def corneal_paraxial_focus_from_post_mm(spec: StandardEyeConstruction) -> float:
    """Return the cornea-only paraxial focus behind the posterior corneal vertex."""

    y, nu = _paraxial_post_cornea_ray(spec)
    distance = -y * spec.eye.medium_index / nu
    if not math.isfinite(distance) or distance <= 0:
        raise ValueError("invalid paraxial corneal focus")
    return distance


@dataclass(frozen=True, slots=True)
class ZeroHoaReferenceRecord:
    reference_id: str
    carrier_id: str
    power_d: float
    r_ant_mm: float
    r_post_mm: float
    center_thickness_mm: float
    material: str
    iol_position_mm: float
    calibration_aperture_mm: float = CORNEAL_SA_PUPIL_MM
    calibration_wavelength_nm: float = STANDARD_EYE_CALIBRATION_WAVELENGTH_NM
    optical_model: str = "ideal_paraxial_zero_hoa"

    @classmethod
    def from_carrier(
        cls,
        carrier: ProvisionalCarrier,
        *,
        standard_eye_spec: BaselineStandardEyeSpec | None = None,
    ) -> ZeroHoaReferenceRecord:
        aperture = CORNEAL_SA_PUPIL_MM
        wavelength = STANDARD_EYE_CALIBRATION_WAVELENGTH_NM
        if standard_eye_spec is not None:
            if not math.isclose(
                standard_eye_spec.aperture_mm,
                CORNEAL_SA_PUPIL_MM,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise ValueError("ZERO_HOA requires the frozen 6-mm standard-eye pupil")
            if not math.isclose(
                standard_eye_spec.wavelength_nm,
                STANDARD_EYE_CALIBRATION_WAVELENGTH_NM,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise ValueError("ZERO_HOA requires the frozen 546-nm standard-eye wavelength")
            aperture = standard_eye_spec.aperture_mm
            wavelength = standard_eye_spec.wavelength_nm
        return cls(
            reference_id=f"ZERO_HOA_{carrier.key.carrier_id}",
            carrier_id=carrier.key.carrier_id,
            power_d=carrier.power_d,
            r_ant_mm=carrier.r_ant_mm,
            r_post_mm=carrier.r_post_mm,
            center_thickness_mm=carrier.center_thickness_mm,
            material=carrier.material,
            iol_position_mm=carrier.iol_position_mm,
            calibration_aperture_mm=aperture,
            calibration_wavelength_nm=wavelength,
        )

    def validate_against(
        self,
        carrier: ProvisionalCarrier,
        *,
        standard_eye_spec: BaselineStandardEyeSpec | None = None,
    ) -> None:
        if self.optical_model != "ideal_paraxial_zero_hoa":
            raise ValueError("ZERO_HOA must use an ideal paraxial optical element")
        if (
            self.carrier_id,
            self.power_d,
            self.r_ant_mm,
            self.r_post_mm,
            self.center_thickness_mm,
            self.material,
            self.iol_position_mm,
        ) != (
            carrier.key.carrier_id,
            carrier.power_d,
            carrier.r_ant_mm,
            carrier.r_post_mm,
            carrier.center_thickness_mm,
            carrier.material,
            carrier.iol_position_mm,
        ):
            raise ValueError(
                "ZERO_HOA must preserve carrier power/envelope/material/position metadata"
            )
        expected_aperture = CORNEAL_SA_PUPIL_MM
        expected_wavelength = STANDARD_EYE_CALIBRATION_WAVELENGTH_NM
        if standard_eye_spec is not None:
            if not math.isclose(
                standard_eye_spec.aperture_mm,
                CORNEAL_SA_PUPIL_MM,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise ValueError("ZERO_HOA requires the frozen 6-mm standard-eye pupil")
            if not math.isclose(
                standard_eye_spec.wavelength_nm,
                STANDARD_EYE_CALIBRATION_WAVELENGTH_NM,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise ValueError("ZERO_HOA requires the frozen 546-nm standard-eye wavelength")
            expected_aperture = standard_eye_spec.aperture_mm
            expected_wavelength = standard_eye_spec.wavelength_nm
        if not math.isclose(
            self.calibration_aperture_mm,
            expected_aperture,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise ValueError("ZERO_HOA calibration pupil does not match the standard eye")
        if not math.isclose(
            self.calibration_wavelength_nm,
            expected_wavelength,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise ValueError("ZERO_HOA calibration wavelength does not match the standard eye")


@dataclass(frozen=True, slots=True)
class StandardEyeMeasurements:
    wavelength_nm: float
    calibration_aperture_mm: float
    corneal_sa_pupil_mm: float
    corneal_c40_um_6mm: float
    iol_footprint_mm_6mm: float
    cornea_front_radius_mm: float
    cornea_front_conic: float
    cornea_back_radius_mm: float
    cornea_back_conic: float
    cornea_thickness_mm: float
    cornea_index: float
    medium_index: float
    iol_from_post_cornea_mm: float
    reference_axial_length_mm: float
    field_x_deg: float
    field_y_deg: float
    surface_count: int
    stop_surface: int


@dataclass(frozen=True, slots=True)
class StandardEyeValidation:
    path: Path
    passed: bool
    findings: tuple[str, ...]
    measurements: StandardEyeMeasurements | None = None


@dataclass(frozen=True, slots=True)
class StandardEyeBuildReport:
    validation: StandardEyeValidation
    artifact: ArtifactRef | None
    validation_artifact: ArtifactRef | None

    @property
    def passed(self) -> bool:
        return self.validation.passed and self.artifact is not None


def validate_standard_eye_measurements(
    measurements: StandardEyeMeasurements,
    spec: StandardEyeConstruction,
) -> tuple[str, ...]:
    spec.validate()
    findings: list[str] = []

    def close(label: str, actual: float, expected: float, tolerance: float) -> None:
        if not math.isfinite(actual) or abs(actual - expected) > tolerance:
            findings.append(
                f"{label}: expected {expected:.12g} ± {tolerance:.3g}, got {actual:.12g}"
            )

    close("wavelength_nm", measurements.wavelength_nm, spec.eye.wavelength_nm, 1.0)
    close(
        "calibration_aperture_mm",
        measurements.calibration_aperture_mm,
        spec.eye.aperture_mm,
        0.001,
    )
    close(
        "corneal_sa_pupil_mm",
        measurements.corneal_sa_pupil_mm,
        spec.corneal_sa_pupil_mm,
        0.001,
    )
    close(
        "corneal_c40_um_6mm",
        measurements.corneal_c40_um_6mm,
        spec.eye.corneal_c40_um,
        C40_TOLERANCE_UM,
    )
    close(
        "iol_footprint_mm_6mm",
        measurements.iol_footprint_mm_6mm,
        spec.eye.iol_footprint_mm,
        spec.eye.iol_footprint_tolerance_mm,
    )
    close(
        "cornea_front_radius_mm",
        measurements.cornea_front_radius_mm,
        spec.cornea_front_radius_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "cornea_front_conic",
        measurements.cornea_front_conic,
        spec.cornea_front_conic,
        1.0e-9,
    )
    close(
        "cornea_back_radius_mm",
        measurements.cornea_back_radius_mm,
        spec.cornea_back_radius_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "cornea_back_conic",
        measurements.cornea_back_conic,
        spec.cornea_back_conic,
        1.0e-9,
    )
    close(
        "cornea_thickness_mm",
        measurements.cornea_thickness_mm,
        spec.cornea_thickness_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close("cornea_index", measurements.cornea_index, spec.cornea_index, INDEX_TOLERANCE)
    close(
        "medium_index",
        measurements.medium_index,
        spec.eye.medium_index,
        INDEX_TOLERANCE,
    )
    close(
        "iol_from_post_cornea_mm",
        measurements.iol_from_post_cornea_mm,
        spec.iol_from_post_cornea_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close(
        "reference_axial_length_mm",
        measurements.reference_axial_length_mm,
        spec.reference_axial_length_mm,
        GEOMETRY_TOLERANCE_MM,
    )
    close("field_x_deg", measurements.field_x_deg, 0.0, 1.0e-12)
    close("field_y_deg", measurements.field_y_deg, 0.0, 1.0e-12)
    if measurements.surface_count != 5:
        findings.append(f"surface_count: expected 5, got {measurements.surface_count}")
    if measurements.stop_surface != 1:
        findings.append(f"stop_surface: expected 1, got {measurements.stop_surface}")
    return tuple(findings)


def _configure_system(system: Any, zosapi: Any, spec: StandardEyeConstruction) -> None:
    wavelengths = system.SystemData.Wavelengths
    while wavelengths.NumberOfWavelengths > 1:
        wavelengths.RemoveWavelength(wavelengths.NumberOfWavelengths)
    if wavelengths.NumberOfWavelengths == 0:
        wavelengths.AddWavelength(spec.eye.wavelength_nm / 1000.0, 1.0)
    wavelength = wavelengths.GetWavelength(1)
    wavelength.Wavelength = spec.eye.wavelength_nm / 1000.0
    wavelength.Weight = 1.0

    fields = system.SystemData.Fields
    while fields.NumberOfFields > 1:
        fields.DeleteFieldAt(fields.NumberOfFields)
    if fields.NumberOfFields == 0:
        fields.AddField(0.0, 0.0, 1.0)
    fields.SetFieldType(zosapi.SystemData.FieldType.Angle)
    field = fields.GetField(1)
    field.X = 0.0
    field.Y = 0.0
    field.Weight = 1.0

    aperture = system.SystemData.Aperture
    aperture.ApertureType = zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(spec.eye.aperture_mm)


def _indices(system: Any, surface: int) -> tuple[float, ...]:
    count = int(system.SystemData.Wavelengths.NumberOfWavelengths)
    system_module = importlib.import_module("System")
    values = system_module.Array[system_module.Double]([0.0] * count)
    returned = int(system.LDE.GetIndex(surface, count, values))
    if returned != count:
        raise StandardEyeError(
            f"LDE.GetIndex returned {returned} wavelengths; expected {count}"
        )
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) and value > 0 for value in result):
        raise StandardEyeError(f"invalid refractive-index readback: {result}")
    return result


def _set_material_index(
    editor: SequentialEditor,
    surface: int,
    target: float,
) -> None:
    cell = editor.surface(surface).MaterialCell
    candidate = target
    actual = math.nan
    for _ in range(MATERIAL_ITERATIONS):
        solve = cell.CreateSolveType(editor.zosapi.Editors.SolveType.MaterialModel)
        model = solve._S_MaterialModel
        model.IndexNd = candidate
        model.AbbeVd = MODEL_ABBE_VD
        model.dPgF = 0.0
        if str(cell.SetSolveData(solve)) != "Success":
            raise StandardEyeError(f"failed MaterialModel solve on surface {surface}")
        actual = _indices(editor.system, surface)[0]
        error = target - actual
        if abs(error) <= MATERIAL_TOLERANCE:
            return
        candidate += error
    raise StandardEyeError(
        f"material calibration failed: target={target:.12g}, actual={actual:.12g}"
    )


def build_standard_eye_asset(
    session: ZosSession,
    spec: StandardEyeConstruction,
    destination: str | Path,
) -> Path:
    spec.validate()
    editor = SequentialEditor(session.system, session.zosapi)
    editor.new_system()
    _configure_system(session.system, session.zosapi, spec)
    while editor.lde.NumberOfSurfaces < 5:
        editor.insert_surface(1)
    if editor.lde.NumberOfSurfaces != 5:
        raise StandardEyeError(
            f"unexpected new-system surface count: {editor.lde.NumberOfSurfaces}"
        )

    editor.set_comment(1, CORNEA_ANT)
    editor.set_radius_conic(
        1, radius_mm=spec.cornea_front_radius_mm, conic=spec.cornea_front_conic
    )
    editor.set_thickness(1, spec.cornea_thickness_mm)
    _set_material_index(editor, 1, spec.cornea_index)
    editor.set_stop_surface(1)

    editor.set_comment(2, CORNEA_POST)
    editor.set_radius_conic(
        2, radius_mm=spec.cornea_back_radius_mm, conic=spec.cornea_back_conic
    )
    editor.set_thickness(2, spec.iol_from_post_cornea_mm)
    _set_material_index(editor, 2, spec.eye.medium_index)

    editor.set_comment(3, IOL_REF)
    editor.set_radius_conic(3, radius_mm=0.0)
    editor.set_thickness(3, spec.iol_to_image_mm)

    editor.set_comment(4, IMAGE_REF)
    editor.set_radius_conic(4, radius_mm=0.0)
    path = Path(destination)
    editor.save_as(path)
    return path


def _footprint_mm(session: ZosSession, to_surface: int) -> float:
    tool = session.system.Tools.OpenBatchRayTrace()
    try:
        rays = tool.CreateNormUnpol(
            2, session.zosapi.Tools.RayTrace.RaysType.Real, int(to_surface)
        )
        rays.ClearData()
        opd_enum = session.zosapi.Tools.RayTrace.OPDMode
        opd_none = getattr(opd_enum, "None", getattr(opd_enum, "None_", None))
        if opd_none is None:
            raise StandardEyeError("installed API exposes no OPDMode.None value")
        for py in (-1.0, 1.0):
            rays.AddRay(1, 0.0, 0.0, 0.0, py, opd_none)
        tool.RunAndWaitForCompletion()
        rays.StartReadingResults()
        y_values: list[float] = []
        for _ in range(2):
            values = tuple(rays.ReadNextResult())
            if len(values) < 15:
                raise StandardEyeError(
                    f"unexpected BatchRayTrace result length: {len(values)}"
                )
            success, error, vignette = bool(values[0]), int(values[2]), int(values[3])
            if not success or error != 0 or vignette != 0:
                raise StandardEyeError(
                    f"footprint ray failed: success={success}, error={error}, vignette={vignette}"
                )
            y_values.append(float(values[5]))
        result = max(y_values) - min(y_values)
        if not math.isfinite(result) or result <= 0:
            raise StandardEyeError(f"invalid IOL footprint: {result}")
        return result
    finally:
        close = getattr(tool, "Close", None)
        if callable(close):
            close()


def _measure(session: ZosSession, spec: StandardEyeConstruction) -> StandardEyeMeasurements:
    system = session.system
    lde = system.LDE
    if int(lde.NumberOfSurfaces) != 5:
        raise StandardEyeError(
            f"surface_count: expected 5, got {int(lde.NumberOfSurfaces)}"
        )
    rows = tuple(lde.GetSurfaceAt(index) for index in range(1, 5))
    for row, role in zip(rows, (CORNEA_ANT, CORNEA_POST, IOL_REF, IMAGE_REF), strict=True):
        if str(row.Comment).strip() != role:
            raise StandardEyeError(f"surface role mismatch: expected {role!r}")

    aperture = system.SystemData.Aperture
    if not str(aperture.ApertureType).endswith("EntrancePupilDiameter"):
        raise StandardEyeError("standard eye must use EntrancePupilDiameter")
    calibration_aperture = float(aperture.ApertureValue)
    wavelength_nm = float(system.SystemData.Wavelengths.GetWavelength(1).Wavelength) * 1000
    field = system.SystemData.Fields.GetField(1)

    # C40 is a cornea-only oracle. Temporarily move the fixed image reference to the
    # corneal paraxial focus, but keep the saved 6-mm calibration pupil unchanged.
    original_iol_to_image = float(rows[2].Thickness)
    corneal_focus_from_post = corneal_paraxial_focus_from_post_mm(spec)
    validation_iol_to_image = corneal_focus_from_post - float(rows[1].Thickness)
    if validation_iol_to_image <= 0:
        raise StandardEyeError("corneal paraxial focus lies before the IOL reference plane")
    try:
        rows[2].Thickness = validation_iol_to_image
        c40_um = ZernikeStandardRunner(system, session.zosapi).run(
            ZernikeStandardSettings(sample_size=32, maximum_terms=37)
        ).c40_um
        footprint = _footprint_mm(session, 3)
    finally:
        rows[2].Thickness = original_iol_to_image

    return StandardEyeMeasurements(
        wavelength_nm=wavelength_nm,
        calibration_aperture_mm=calibration_aperture,
        corneal_sa_pupil_mm=spec.corneal_sa_pupil_mm,
        corneal_c40_um_6mm=c40_um,
        iol_footprint_mm_6mm=footprint,
        cornea_front_radius_mm=float(rows[0].Radius),
        cornea_front_conic=float(rows[0].Conic),
        cornea_back_radius_mm=float(rows[1].Radius),
        cornea_back_conic=float(rows[1].Conic),
        cornea_thickness_mm=float(rows[0].Thickness),
        cornea_index=_indices(system, 1)[0],
        medium_index=_indices(system, 2)[0],
        iol_from_post_cornea_mm=float(rows[1].Thickness),
        reference_axial_length_mm=float(rows[0].Thickness)
        + float(rows[1].Thickness)
        + float(rows[2].Thickness),
        field_x_deg=float(field.X),
        field_y_deg=float(field.Y),
        surface_count=int(lde.NumberOfSurfaces),
        stop_surface=int(lde.StopSurface),
    )


def validate_standard_eye_asset(
    session: ZosSession,
    spec: StandardEyeConstruction,
    path: str | Path,
) -> StandardEyeValidation:
    asset_path = Path(path)
    if not asset_path.is_file():
        return StandardEyeValidation(
            asset_path, False, (f"standard-eye asset is missing: {asset_path}",)
        )
    try:
        session.system.LoadFile(str(asset_path.resolve()), False)
        measurements = _measure(session, spec)
        findings = validate_standard_eye_measurements(measurements, spec)
    except Exception as exc:  # noqa: BLE001 - ZOS failures become validation evidence
        return StandardEyeValidation(
            asset_path, False, (f"{type(exc).__name__}: {exc}",)
        )
    return StandardEyeValidation(asset_path, not findings, findings, measurements)


def _write_validation_csv(path: Path, validation: StandardEyeValidation) -> None:
    measurement = validation.measurements
    row: dict[str, object] = {
        "asset_id": ARTIFACT_ID,
        "status": "PASS" if validation.passed else "FAIL",
        "findings": " | ".join(validation.findings),
    }
    if measurement is not None:
        row.update(asdict(measurement))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(row))
        writer.writeheader()
        writer.writerow(row)


def validate_registered_standard_eye(
    session: ZosSession,
    store: ProjectStore,
    baseline: ScientificBaseline,
) -> StandardEyeValidation:
    spec = standard_eye_construction(baseline)
    validation = validate_standard_eye_asset(
        session, spec, store.resolve(RELATIVE_PATH)
    )
    record = store.find_artifact(ARTIFACT_ID)
    findings = list(validation.findings)
    if record is None:
        findings.append("standard-eye artifact is not registered")
    else:
        if record.relative_path != RELATIVE_PATH:
            findings.append("standard-eye artifact path mismatch")
        if record.artifact_type != "zemax_standard_eye":
            findings.append("standard-eye artifact type mismatch")
        if record.baseline_id != baseline.baseline_id:
            findings.append("standard-eye baseline mismatch")
        if not record.locked:
            findings.append("standard-eye artifact must be locked")
        if not store.verify_artifact(record):
            findings.append("standard-eye artifact hash mismatch")
    return replace(validation, passed=not findings, findings=tuple(findings))


def build_standard_eye(
    session: ZosSession,
    store: ProjectStore,
    baseline: ScientificBaseline,
) -> StandardEyeBuildReport:
    if store.baseline != baseline:
        raise StandardEyeError("project store and scientific baseline differ")
    spec = standard_eye_construction(baseline)
    destination = store.resolve(RELATIVE_PATH)
    existing = store.find_artifact(ARTIFACT_ID)

    if existing is not None:
        validation = validate_registered_standard_eye(session, store, baseline)
        artifact = existing if validation.passed else None
    else:
        if destination.exists():
            raise StandardEyeError(
                f"refusing to overwrite unindexed standard-eye asset: {destination}"
            )
        with tempfile.TemporaryDirectory(prefix="task-005c-standard-eye-") as temp_name:
            scratch = Path(temp_name) / "STD_IOL_EYE_2024.zos"
            build_standard_eye_asset(session, spec, scratch)
            validation = validate_standard_eye_asset(session, spec, scratch)
            if not validation.passed:
                return StandardEyeBuildReport(validation, None, None)
            artifact = store.record_artifact(
                scratch,
                ArtifactRecord(
                    artifact_id=ARTIFACT_ID,
                    artifact_type="zemax_standard_eye",
                    relative_path=RELATIVE_PATH,
                    baseline_id=baseline.baseline_id,
                ),
                lock=True,
            )
            if not store.verify_artifact(artifact):
                raise StandardEyeError("standard-eye artifact hash verification failed")
            validation = replace(validation, path=destination)

    with tempfile.TemporaryDirectory(prefix="task-005c-validation-") as temp_name:
        csv_path = Path(temp_name) / "TASK_005C_STANDARD_EYE_VALIDATION.csv"
        _write_validation_csv(csv_path, validation)
        validation_artifact = store.record_artifact(
            csv_path,
            ArtifactRecord(
                artifact_id=VALIDATION_ID,
                artifact_type="validation_csv",
                relative_path=VALIDATION_PATH,
                baseline_id=baseline.baseline_id,
            ),
            lock=False,
        )

    return StandardEyeBuildReport(validation, artifact, validation_artifact)