from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .domain import BaseId, CorneaId, PlatformId

SA_TARGETS_UM = {PlatformId.WFS: -0.20, PlatformId.RAD: -0.27, PlatformId.HOA: 0.00}
ALLOWED_RESIDUAL_REPRESENTATIONS = {"radial_sag_samples", "analytic_coefficients", "grid_sag_resource"}


class ScientificInvariantError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CarrierKey:
    base_id: str
    cornea_id: str
    platform_id: str

    @property
    def carrier_id(self) -> str:
        return f"CAR_{self.base_id}_{self.cornea_id}_{self.platform_id}"


@dataclass(frozen=True, slots=True)
class ProvisionalCarrier:
    key: CarrierKey
    power_d: float
    q: float
    q_source_power_d: float
    r_ant_mm: float
    r_post_mm: float
    center_thickness_mm: float
    material: str
    iol_position_mm: float
    achieved_sa_um: float


@dataclass(frozen=True, slots=True)
class ResidualCalibration:
    label: str
    actual_power_d: float
    passed: bool
    distance_shift_d: float


@dataclass(frozen=True, slots=True)
class ResidualDefinition:
    residual_id: str
    platform_id: str
    version: str
    representation: str
    payload_ref: str
    units: str
    radial_domain_mm: tuple[float, float]
    piston_removed: bool
    defocus_removed: bool
    sha256: str
    calibrations: tuple[ResidualCalibration, ...] = ()


@dataclass(frozen=True, slots=True)
class MatchedPair:
    carrier: ProvisionalCarrier
    mono_residual_id: None
    edof_residual_id: str
    delta_f_residual_d: float


def sha256_path(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_carrier_keys() -> tuple[CarrierKey, ...]:
    return tuple(
        CarrierKey(base, cornea, platform)
        for base in (BaseId.LB_AL2395, BaseId.ATC_M3_AL24477)
        for cornea in (CorneaId.A0, CorneaId.B0, CorneaId.C0)
        for platform in (PlatformId.WFS, PlatformId.RAD, PlatformId.HOA)
    )


def validate_provisional_carrier(carrier: ProvisionalCarrier, *, sa_tolerance_um: float = 0.01) -> None:
    if abs(carrier.q_source_power_d - carrier.power_d) > 1e-12:
        raise ScientificInvariantError("Q source power must equal carrier power")
    target = SA_TARGETS_UM[carrier.key.platform_id]
    if abs(carrier.achieved_sa_um - target) > sa_tolerance_um:
        raise ScientificInvariantError(f"achieved standard-eye SA {carrier.achieved_sa_um} outside target {target}±{sa_tolerance_um}")


def validate_residual_definition(residual: ResidualDefinition, *, require_payload: bool = True) -> None:
    if residual.platform_id not in SA_TARGETS_UM:
        raise ScientificInvariantError("unknown residual platform")
    if residual.representation not in ALLOWED_RESIDUAL_REPRESENTATIONS:
        raise ScientificInvariantError("unsupported residual representation")
    if not residual.piston_removed or not residual.defocus_removed:
        raise ScientificInvariantError("residual must have piston and global defocus removed")
    if require_payload:
        path = Path(residual.payload_ref)
        if not path.is_file():
            raise ScientificInvariantError("residual payload is missing")
        if sha256_path(path) != residual.sha256:
            raise ScientificInvariantError("residual payload hash mismatch")
    labels = {c.label for c in residual.calibrations if c.passed}
    if labels != {"low", "median", "high"}:
        raise ScientificInvariantError("residual requires passing low/median/high actual-power calibration")


def residuals_ready(residuals: Sequence[ResidualDefinition], *, require_payload: bool = True) -> bool:
    by_platform = {r.platform_id: r for r in residuals}
    if set(by_platform) != set(SA_TARGETS_UM):
        return False
    try:
        for residual in by_platform.values():
            validate_residual_definition(residual, require_payload=require_payload)
    except ScientificInvariantError:
        return False
    return True


def validate_18_provisional_carriers(carriers: Sequence[ProvisionalCarrier]) -> None:
    expected = set(expected_carrier_keys())
    actual = {c.key for c in carriers}
    if len(carriers) != 18 or actual != expected:
        raise ScientificInvariantError("provisional carrier set must contain exactly the 2×3×3 key space")
    for carrier in carriers:
        validate_provisional_carrier(carrier)


def make_matched_pair(carrier: ProvisionalCarrier, residual: ResidualDefinition, *, delta_f_residual_d: float) -> MatchedPair:
    validate_provisional_carrier(carrier)
    if residual.platform_id != carrier.key.platform_id:
        raise ScientificInvariantError("residual platform must match carrier platform")
    validate_residual_definition(residual)
    return MatchedPair(carrier, None, residual.residual_id, delta_f_residual_d)
