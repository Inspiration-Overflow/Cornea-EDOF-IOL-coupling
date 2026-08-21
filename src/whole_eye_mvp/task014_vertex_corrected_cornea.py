from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .cornea_assets import (
    MAIN_CORNEA_SCAFFOLD,
    CorneaLockPrescription,
    CorneaSurfaceFamily,
    distance_corrected_front_radius_mm,
    paraxial_cornea_power_d,
)
from .domain import CorneaId, ScientificBaseline

TASK014_ID = "TASK-014-VERTEX-CORRECTED-POSTOP-CORNEA"
TASK014_RX_CONTRACT_ID = "TASK014_SPECTACLE_M3_VERTEX12_v1"
TASK014_PREOP_SPECTACLE_SPHERE_D = -3.0
TASK014_VERTEX_DISTANCE_MM = 12.0
TASK014_LEGACY_DIRECT_TREATMENT_D = -3.0
TASK014_A0_ID = "A0V12"
TASK014_B0_ID = "B0V12"
TASK014_C0_ID = "C0V12"
TASK014_B0_TARGET_DELTA_C40_UM = 0.20


class Task014Error(RuntimeError):
    pass


def spectacle_to_cornea_plane_d(
    spectacle_power_d: float,
    vertex_distance_mm: float,
) -> float:
    power = float(spectacle_power_d)
    vertex_mm = float(vertex_distance_mm)
    if not math.isfinite(power) or not math.isfinite(vertex_mm):
        raise ValueError("spectacle power and vertex distance must be finite")
    if vertex_mm < 0.0:
        raise ValueError("vertex distance must be non-negative")
    distance_m = vertex_mm / 1000.0
    denominator = 1.0 - distance_m * power
    if abs(denominator) <= 1.0e-12:
        raise ValueError("spectacle-to-corneal conversion is singular")
    return power / denominator


def cornea_to_spectacle_plane_d(
    corneal_power_d: float,
    vertex_distance_mm: float,
) -> float:
    power = float(corneal_power_d)
    vertex_mm = float(vertex_distance_mm)
    if not math.isfinite(power) or not math.isfinite(vertex_mm):
        raise ValueError("corneal power and vertex distance must be finite")
    if vertex_mm < 0.0:
        raise ValueError("vertex distance must be non-negative")
    distance_m = vertex_mm / 1000.0
    denominator = 1.0 + distance_m * power
    if abs(denominator) <= 1.0e-12:
        raise ValueError("corneal-to-spectacle conversion is singular")
    return power / denominator


@dataclass(frozen=True, slots=True)
class VertexCorrectedRxContract:
    contract_id: str
    preoperative_spectacle_sphere_d: float
    vertex_distance_mm: float

    @property
    def corneal_plane_distance_treatment_d(self) -> float:
        return spectacle_to_cornea_plane_d(
            self.preoperative_spectacle_sphere_d,
            self.vertex_distance_mm,
        )

    @property
    def legacy_direct_treatment_delta_d(self) -> float:
        return self.corneal_plane_distance_treatment_d - TASK014_LEGACY_DIRECT_TREATMENT_D

    def validate(self) -> None:
        if self.contract_id != TASK014_RX_CONTRACT_ID:
            raise Task014Error("TASK-014 refraction contract ID drifted")
        if not math.isclose(
            self.preoperative_spectacle_sphere_d,
            TASK014_PREOP_SPECTACLE_SPHERE_D,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise Task014Error("TASK-014 spectacle sphere drifted")
        if not math.isclose(
            self.vertex_distance_mm,
            TASK014_VERTEX_DISTANCE_MM,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise Task014Error("TASK-014 vertex distance drifted")
        if self.preoperative_spectacle_sphere_d >= 0.0:
            raise Task014Error("TASK-014 frozen prescription must remain myopic")
        if self.vertex_distance_mm <= 0.0:
            raise Task014Error("TASK-014 vertex distance must remain positive")
        roundtrip = cornea_to_spectacle_plane_d(
            self.corneal_plane_distance_treatment_d,
            self.vertex_distance_mm,
        )
        if not math.isclose(
            roundtrip,
            self.preoperative_spectacle_sphere_d,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise Task014Error("TASK-014 vertex conversion roundtrip failed")


TASK014_RX_CONTRACT = VertexCorrectedRxContract(
    contract_id=TASK014_RX_CONTRACT_ID,
    preoperative_spectacle_sphere_d=TASK014_PREOP_SPECTACLE_SPHERE_D,
    vertex_distance_mm=TASK014_VERTEX_DISTANCE_MM,
)
TASK014_RX_CONTRACT.validate()


def _legacy_specs(baseline: ScientificBaseline):
    by_id = {str(spec.cornea_id): spec for spec in baseline.cornea_specs}
    expected = {str(CorneaId.A0), str(CorneaId.B0), str(CorneaId.C0)}
    if set(by_id) != expected:
        raise Task014Error("TASK-014 requires the unchanged frozen A0/B0/C0 baseline")
    for cornea_id, spec in by_id.items():
        if not math.isclose(
            float(spec.treatment_d),
            TASK014_LEGACY_DIRECT_TREATMENT_D,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise Task014Error(
                f"legacy {cornea_id} treatment changed; TASK-014 must not silently follow it"
            )
    return by_id


def task014_cornea_prescriptions(
    baseline: ScientificBaseline,
) -> tuple[CorneaLockPrescription, CorneaLockPrescription, CorneaLockPrescription]:
    by_id = _legacy_specs(baseline)
    treatment = TASK014_RX_CONTRACT.corneal_plane_distance_treatment_d
    a = by_id[str(CorneaId.A0)]
    b = by_id[str(CorneaId.B0)]
    c = by_id[str(CorneaId.C0)]

    prescriptions = (
        CorneaLockPrescription(
            candidate_id=TASK014_A0_ID,
            cornea_id=CorneaId.A0,
            surface_family=CorneaSurfaceFamily.BINARY4,
            treatment_d=treatment,
            optical_zone_mm=a.optical_zone_mm,
            target_delta_c40_um=a.target_delta_c40_um,
        ),
        CorneaLockPrescription(
            candidate_id=TASK014_B0_ID,
            cornea_id=CorneaId.B0,
            surface_family=CorneaSurfaceFamily.EVEN_ASPHERE,
            treatment_d=treatment,
            optical_zone_mm=b.optical_zone_mm,
            target_delta_c40_um=TASK014_B0_TARGET_DELTA_C40_UM,
        ),
        CorneaLockPrescription(
            candidate_id=TASK014_C0_ID,
            cornea_id=CorneaId.C0,
            surface_family=CorneaSurfaceFamily.BINARY4,
            treatment_d=treatment,
            optical_zone_mm=c.optical_zone_mm,
            near_diameter_mm=c.near_diameter_mm,
            add_rx_d=c.add_rx_d,
            transition_width_mm=c.transition_width_mm,
        ),
    )
    for prescription in prescriptions:
        prescription.validate()
    return prescriptions


def task014_prescription_snapshot(baseline: ScientificBaseline) -> dict[str, object]:
    TASK014_RX_CONTRACT.validate()
    prescriptions = task014_cornea_prescriptions(baseline)
    reference_power = paraxial_cornea_power_d(MAIN_CORNEA_SCAFFOLD.front_radius_mm)
    treatment = TASK014_RX_CONTRACT.corneal_plane_distance_treatment_d
    return {
        "task_id": TASK014_ID,
        "contract": asdict(TASK014_RX_CONTRACT),
        "corneal_plane_distance_treatment_d": treatment,
        "legacy_direct_treatment_d": TASK014_LEGACY_DIRECT_TREATMENT_D,
        "legacy_to_vertex_corrected_delta_d": (
            treatment - TASK014_LEGACY_DIRECT_TREATMENT_D
        ),
        "reference_cornea_equivalent_power_d": reference_power,
        "vertex_corrected_distance_cornea_power_d": reference_power + treatment,
        "vertex_corrected_distance_front_radius_mm": distance_corrected_front_radius_mm(
            treatment
        ),
        "prescriptions": [asdict(item) for item in prescriptions],
        "base_semantics": (
            "base phenotype is orthogonal to the standardized surgical prescription; "
            "ATC source_refraction_d is not added to TASK-014 treatment"
        ),
    }
