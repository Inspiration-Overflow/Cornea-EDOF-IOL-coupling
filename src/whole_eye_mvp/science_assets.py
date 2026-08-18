from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

from .domain import BaseId, CorneaId, PlatformId


class NumericalStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True, slots=True)
class BaseSpec:
    base_id: str
    axial_length_mm: float
    post_cornea_to_stop_mm: float = 3.150
    post_cornea_to_iol_ant_mm: float = 4.500
    aqueous_index: float = 1.336
    vitreous_index: float = 1.336


@dataclass(frozen=True, slots=True)
class StandardEyeSpec:
    eye_id: str = "STD_IOL_EYE_2024"
    corneal_c40_um: float = 0.258
    iol_footprint_mm: float = 5.15
    iol_footprint_tolerance_mm: float = 0.10
    medium_index: float = 1.336
    aperture_mm: float = 3.0
    wavelength_nm: float = 546.0


@dataclass(frozen=True, slots=True)
class CorneaSpec:
    cornea_id: str
    treatment_d: float
    optical_zone_mm: float
    target_delta_c40_um: float | None = None


@dataclass(frozen=True, slots=True)
class C0Spec:
    cornea_id: str = CorneaId.C0
    treatment_d: float = -3.0
    near_diameter_mm: float = 3.0
    add_rx_d: float = 1.75
    optical_zone_mm: float = 6.5
    transition_width_mm: float = 0.75

    @property
    def near_radius_mm(self) -> float:
        return self.near_diameter_mm / 2

    @property
    def transition_outer_radius_mm(self) -> float:
        return self.near_radius_mm + self.transition_width_mm


@dataclass(frozen=True, slots=True)
class PlatformSpec:
    platform_id: str
    user_label: str
    standard_eye_sa_target_um: float


@dataclass(frozen=True, slots=True)
class AssetValidation:
    asset_id: str
    status: NumericalStatus
    findings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AssetBuildReport:
    validations: tuple[AssetValidation, ...]
    carrier_ready: bool
    residual_missing: tuple[str, ...]

    @property
    def core_ok(self) -> bool:
        return bool(self.validations) and all(v.status == NumericalStatus.PASS for v in self.validations)


LB_BASE = BaseSpec(BaseId.LB_AL2395, 23.950)
ATC_M3_BASE = BaseSpec(BaseId.ATC_M3_AL24477, 24.477)
STD_IOL_EYE = StandardEyeSpec()
A0_SPEC = CorneaSpec(CorneaId.A0, -3.0, 5.0, 0.13)
B_CANDIDATE_DELTA_C40_UM = (0.10, 0.15, 0.20, 0.25, 0.30)
B_OPTICAL_ZONE_MM = 6.0
C0_SPEC = C0Spec()
PLATFORM_SPECS = (
    PlatformSpec(PlatformId.WFS, "WFS-like surrogate", -0.20),
    PlatformSpec(PlatformId.RAD, "RAD-like surrogate", -0.27),
    PlatformSpec(PlatformId.HOA, "HOA-like surrogate", 0.00),
)


def smoothstep_quintic(x: float | np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if np.any((x < 0) | (x > 1)):
        raise ValueError("x must lie in [0, 1]")
    return 6 * x**5 - 15 * x**4 + 10 * x**3


def c0_near_weight(radius_mm: float | np.ndarray, spec: C0Spec = C0_SPEC) -> np.ndarray:
    r = np.asarray(radius_mm, dtype=float)
    if np.any(r < 0):
        raise ValueError("radius must be non-negative")
    out = np.ones_like(r)
    outer = spec.transition_outer_radius_mm
    out[r >= outer] = 0.0
    transition = (r > spec.near_radius_mm) & (r < outer)
    x = (r[transition] - spec.near_radius_mm) / spec.transition_width_mm
    out[transition] = 1.0 - smoothstep_quintic(x)
    return out


class ScientificAssetBackend(Protocol):
    def build_core_assets(self, output_dir: Path) -> Sequence[AssetValidation]: ...
    def validate_core_assets(self, output_dir: Path) -> Sequence[AssetValidation]: ...


def summarize_asset_validations(validations: Sequence[AssetValidation], *, available_residual_platforms: Sequence[str] = ()) -> AssetBuildReport:
    residuals = set(available_residual_platforms)
    missing = tuple(p.platform_id for p in PLATFORM_SPECS if p.platform_id not in residuals)
    core_ok = bool(validations) and all(v.status == NumericalStatus.PASS for v in validations)
    return AssetBuildReport(tuple(validations), carrier_ready=core_ok and not missing, residual_missing=missing)
