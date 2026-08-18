from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

from .domain import BaseId, CorneaId, PlatformId

SA_TARGETS_UM = {PlatformId.WFS: -0.20, PlatformId.RAD: -0.27, PlatformId.HOA: 0.00}
ALLOWED_RESIDUAL_REPRESENTATIONS = {
    "radial_sag_samples",
    "analytic_coefficients",
    "grid_sag_resource",
}
CALIBRATION_LABELS = ("low", "median", "high")


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
class ResidualValidationPolicy:
    """Frozen numerical policy supplied by the scientific baseline before formal locking.

    The project documents intentionally do not invent these two tolerances.  A formal
    residual lock therefore cannot be created until local OpticStudio validation has
    supplied a versioned policy with explicit numerical limits.
    """

    policy_id: str
    piston_tolerance_um: float
    global_defocus_tolerance_d: float

    def validate(self) -> None:
        if not self.policy_id.strip():
            raise ScientificInvariantError("residual validation policy ID is required")
        if not math.isfinite(self.piston_tolerance_um) or self.piston_tolerance_um < 0:
            raise ScientificInvariantError("residual piston tolerance must be finite and non-negative")
        if not math.isfinite(self.global_defocus_tolerance_d) or self.global_defocus_tolerance_d < 0:
            raise ScientificInvariantError(
                "residual global-defocus tolerance must be finite and non-negative"
            )

    @property
    def policy_hash(self) -> str:
        self.validate()
        text = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ResidualCalibration:
    label: str
    carrier_id: str
    actual_power_d: float
    oracle_passed: bool
    distance_shift_d: float
    evidence_ref: str
    evidence_sha256: str


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
    measured_piston_um: float | None = None
    measured_global_defocus_d: float | None = None
    validation_evidence_ref: str = ""
    validation_evidence_sha256: str = ""
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


def _finite(*values: float) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def validate_provisional_carrier(
    carrier: ProvisionalCarrier, *, sa_tolerance_um: float = 0.01
) -> None:
    if carrier.key not in set(expected_carrier_keys()):
        raise ScientificInvariantError("carrier key is outside the frozen 2×3×3 key space")
    if not _finite(
        carrier.power_d,
        carrier.q,
        carrier.q_source_power_d,
        carrier.r_ant_mm,
        carrier.r_post_mm,
        carrier.center_thickness_mm,
        carrier.iol_position_mm,
        carrier.achieved_sa_um,
    ):
        raise ScientificInvariantError("carrier optical values must all be finite")
    if carrier.center_thickness_mm <= 0:
        raise ScientificInvariantError("carrier center thickness must be positive")
    if not carrier.material.strip():
        raise ScientificInvariantError("carrier material is required")
    if not math.isfinite(sa_tolerance_um) or sa_tolerance_um < 0:
        raise ScientificInvariantError("SA tolerance must be finite and non-negative")
    if abs(carrier.q_source_power_d - carrier.power_d) > 1e-12:
        raise ScientificInvariantError("Q source power must equal carrier power")
    target = SA_TARGETS_UM[carrier.key.platform_id]
    if abs(carrier.achieved_sa_um - target) > sa_tolerance_um:
        raise ScientificInvariantError(
            f"achieved standard-eye SA {carrier.achieved_sa_um} outside target "
            f"{target}±{sa_tolerance_um}"
        )


def _verify_hashed_file(path_text: str, expected_sha256: str, label: str) -> None:
    if not path_text.strip() or not expected_sha256.strip():
        raise ScientificInvariantError(f"{label} reference/hash is missing")
    path = Path(path_text)
    if not path.is_file():
        raise ScientificInvariantError(f"{label} is missing")
    if sha256_path(path) != expected_sha256:
        raise ScientificInvariantError(f"{label} hash mismatch")


def expected_calibration_carriers(
    carriers: Sequence[ProvisionalCarrier], platform_id: str
) -> dict[str, ProvisionalCarrier]:
    platform_carriers = [c for c in carriers if c.key.platform_id == platform_id]
    if len(platform_carriers) != 6:
        raise ScientificInvariantError(
            f"residual calibration requires six actual carriers for platform {platform_id}"
        )
    for carrier in platform_carriers:
        validate_provisional_carrier(carrier)
    ordered = sorted(platform_carriers, key=lambda c: (c.power_d, c.key.carrier_id))
    median_power = median(c.power_d for c in ordered)
    median_carrier = min(
        ordered,
        key=lambda c: (abs(c.power_d - median_power), c.power_d, c.key.carrier_id),
    )
    selected = {"low": ordered[0], "median": median_carrier, "high": ordered[-1]}
    if len({carrier.key.carrier_id for carrier in selected.values()}) != 3:
        raise ScientificInvariantError(
            "low/median/high residual calibration must resolve to three distinct actual carriers"
        )
    return selected


def validate_residual_definition(
    residual: ResidualDefinition,
    *,
    carriers: Sequence[ProvisionalCarrier],
    policy: ResidualValidationPolicy,
    require_payload: bool = True,
) -> None:
    policy.validate()
    if residual.platform_id not in SA_TARGETS_UM:
        raise ScientificInvariantError("unknown residual platform")
    for value, label in (
        (residual.residual_id, "residual ID"),
        (residual.version, "residual version"),
        (residual.units, "residual units"),
    ):
        if not value.strip():
            raise ScientificInvariantError(f"{label} is required")
    if residual.representation not in ALLOWED_RESIDUAL_REPRESENTATIONS:
        raise ScientificInvariantError("unsupported residual representation")
    if len(residual.radial_domain_mm) != 2 or not _finite(*residual.radial_domain_mm):
        raise ScientificInvariantError("residual radial domain must contain two finite values")
    if residual.radial_domain_mm[0] < 0 or residual.radial_domain_mm[1] <= residual.radial_domain_mm[0]:
        raise ScientificInvariantError("residual radial domain is invalid")
    if not residual.piston_removed or not residual.defocus_removed:
        raise ScientificInvariantError("residual must have piston and global defocus removed")
    if residual.measured_piston_um is None or residual.measured_global_defocus_d is None:
        raise ScientificInvariantError(
            "residual requires measured piston/global-defocus evidence, not metadata flags alone"
        )
    if not _finite(residual.measured_piston_um, residual.measured_global_defocus_d):
        raise ScientificInvariantError("residual piston/global-defocus measurements must be finite")
    if abs(residual.measured_piston_um) > policy.piston_tolerance_um:
        raise ScientificInvariantError("residual piston measurement exceeds frozen tolerance")
    if abs(residual.measured_global_defocus_d) > policy.global_defocus_tolerance_d:
        raise ScientificInvariantError("residual global-defocus measurement exceeds frozen tolerance")

    if require_payload:
        _verify_hashed_file(residual.payload_ref, residual.sha256, "residual payload")
    _verify_hashed_file(
        residual.validation_evidence_ref,
        residual.validation_evidence_sha256,
        "residual validation evidence",
    )

    expected = expected_calibration_carriers(carriers, residual.platform_id)
    calibrations = residual.calibrations
    if len(calibrations) != 3 or {c.label for c in calibrations} != set(CALIBRATION_LABELS):
        raise ScientificInvariantError(
            "residual requires exactly one low/median/high actual-power calibration"
        )
    if len({c.label for c in calibrations}) != len(calibrations):
        raise ScientificInvariantError("residual calibration labels must be unique")
    for calibration in calibrations:
        target_carrier = expected[calibration.label]
        if calibration.carrier_id != target_carrier.key.carrier_id:
            raise ScientificInvariantError(
                f"{calibration.label} calibration is not bound to the expected actual carrier"
            )
        if not _finite(calibration.actual_power_d, calibration.distance_shift_d):
            raise ScientificInvariantError("residual calibration values must be finite")
        if abs(calibration.actual_power_d - target_carrier.power_d) > 1e-12:
            raise ScientificInvariantError(
                f"{calibration.label} calibration power does not match its carrier power"
            )
        if not calibration.oracle_passed:
            raise ScientificInvariantError(
                f"{calibration.label} residual calibration optical oracle did not pass"
            )
        _verify_hashed_file(
            calibration.evidence_ref,
            calibration.evidence_sha256,
            f"{calibration.label} calibration evidence",
        )


def residuals_ready(
    residuals: Sequence[ResidualDefinition],
    *,
    carriers: Sequence[ProvisionalCarrier],
    policy: ResidualValidationPolicy,
    require_payload: bool = True,
) -> bool:
    if len(residuals) != 3:
        return False
    platform_ids = [r.platform_id for r in residuals]
    if len(set(platform_ids)) != 3 or set(platform_ids) != set(SA_TARGETS_UM):
        return False
    try:
        validate_18_provisional_carriers(carriers)
        for residual in residuals:
            validate_residual_definition(
                residual,
                carriers=carriers,
                policy=policy,
                require_payload=require_payload,
            )
    except ScientificInvariantError:
        return False
    return True


def validate_18_provisional_carriers(carriers: Sequence[ProvisionalCarrier]) -> None:
    expected = set(expected_carrier_keys())
    actual = {c.key for c in carriers}
    if len(carriers) != 18 or actual != expected:
        raise ScientificInvariantError(
            "provisional carrier set must contain exactly the 2×3×3 key space"
        )
    for carrier in carriers:
        validate_provisional_carrier(carrier)


def make_matched_pair(
    carrier: ProvisionalCarrier,
    residual: ResidualDefinition,
    *,
    delta_f_residual_d: float,
    carriers: Sequence[ProvisionalCarrier],
    policy: ResidualValidationPolicy,
) -> MatchedPair:
    validate_provisional_carrier(carrier)
    if residual.platform_id != carrier.key.platform_id:
        raise ScientificInvariantError("residual platform must match carrier platform")
    validate_residual_definition(residual, carriers=carriers, policy=policy)
    if not math.isfinite(delta_f_residual_d):
        raise ScientificInvariantError("residual distance shift must be finite")
    return MatchedPair(carrier, None, residual.residual_id, float(delta_f_residual_d))
