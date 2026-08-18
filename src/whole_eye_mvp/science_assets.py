from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import numpy as np

from .domain import (
    BASELINE_B_CANDIDATES_DELTA_C40_UM,
    BASELINE_BASE_SPECS,
    BASELINE_CORNEA_SPECS,
    BASELINE_PLATFORM_SPECS,
    BASELINE_STANDARD_EYE_SPEC,
    BaselineBaseSpec,
    BaselineCorneaSpec,
    BaselinePlatformSpec,
    BaselineStandardEyeSpec,
    CorneaId,
)


class NumericalStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


BaseSpec = BaselineBaseSpec
StandardEyeSpec = BaselineStandardEyeSpec
CorneaSpec = BaselineCorneaSpec
PlatformSpec = BaselinePlatformSpec


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
class AssetValidation:
    asset_id: str
    status: str
    findings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AssetBuildReport:
    validations: tuple[AssetValidation, ...]
    carrier_ready: bool
    residual_missing: tuple[str, ...]

    @property
    def core_ok(self) -> bool:
        return bool(self.validations) and all(v.status == NumericalStatus.PASS for v in self.validations)


LB_BASE = BASELINE_BASE_SPECS[0]
ATC_M3_BASE = BASELINE_BASE_SPECS[1]
STD_IOL_EYE = BASELINE_STANDARD_EYE_SPEC
A0_SPEC = next(spec for spec in BASELINE_CORNEA_SPECS if spec.cornea_id == CorneaId.A0)
B_CANDIDATE_DELTA_C40_UM = BASELINE_B_CANDIDATES_DELTA_C40_UM
B_OPTICAL_ZONE_MM = next(
    spec.optical_zone_mm for spec in BASELINE_CORNEA_SPECS if spec.cornea_id == CorneaId.B0
)
C0_SPEC = C0Spec()
PLATFORM_SPECS = BASELINE_PLATFORM_SPECS


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


def summarize_asset_validations(
    validations: Sequence[AssetValidation], *, available_residual_platforms: Sequence[str] = ()
) -> AssetBuildReport:
    residuals = set(available_residual_platforms)
    missing = tuple(p.platform_id for p in PLATFORM_SPECS if p.platform_id not in residuals)
    core_ok = bool(validations) and all(v.status == NumericalStatus.PASS for v in validations)
    return AssetBuildReport(
        tuple(validations), carrier_ready=core_ok and not missing, residual_missing=missing
    )
