from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from .carriers import SA_TARGETS_UM, ProvisionalCarrier
from .domain import BaseId, OpticState, PlatformId
from .manifest import NominalConfig

TASK013_ID = "TASK-013-NATIVE-CORNEA-REFERENCE"
NATIVE_REFERENCE_CORNEA_ID = "N0"
TASK013_EXPECTED_CARRIER_COUNT = 6
TASK013_EXPECTED_CONFIG_COUNT = 24
TASK013_EXPECTED_PAIR_COUNT = 12
TASK013_EXPECTED_THROUGH_FOCUS_ROWS = 360


class Task013Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResidualProvenance:
    platform_id: str
    residual_id: str
    residual_sha256: str
    residual_validation_policy_id: str
    residual_validation_policy_hash: str

    def validate(self) -> None:
        if self.platform_id not in {str(value) for value in PlatformId}:
            raise Task013Error(f"unknown residual platform: {self.platform_id}")
        for name in (
            "residual_id",
            "residual_sha256",
            "residual_validation_policy_id",
            "residual_validation_policy_hash",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise Task013Error(f"{name} is required")


@dataclass(frozen=True, slots=True)
class NativeCarrierLock:
    carrier: ProvisionalCarrier
    residual: ResidualProvenance
    lock_hash: str

    @property
    def carrier_id(self) -> str:
        return self.carrier.key.carrier_id


@dataclass(frozen=True, slots=True)
class Task013ManifestBundle:
    physical_carriers: tuple[NativeCarrierLock, ...]
    nominal_configs: tuple[NominalConfig, ...]
    manifest_hash: str
    lock_set_hash: str


@dataclass(frozen=True, slots=True)
class ResidualPowerEnvelopeCheck:
    platform_id: str
    carrier_id: str
    n0_power_d: float
    existing_min_power_d: float
    existing_max_power_d: float
    passed: bool


def _platform_values() -> tuple[str, ...]:
    return tuple(str(value) for value in PlatformId)


def _base_values() -> tuple[str, ...]:
    return tuple(str(value) for value in BaseId)


def validate_native_carrier(
    carrier: ProvisionalCarrier,
    *,
    sa_tolerance_um: float = 0.01,
) -> None:
    key = carrier.key
    if key.base_id not in _base_values():
        raise Task013Error(f"N0 carrier base is outside the frozen two-base set: {key.base_id}")
    if key.cornea_id != NATIVE_REFERENCE_CORNEA_ID:
        raise Task013Error(f"TASK-013 carrier must use {NATIVE_REFERENCE_CORNEA_ID}")
    if key.platform_id not in _platform_values():
        raise Task013Error(f"unknown TASK-013 platform: {key.platform_id}")
    numeric = (
        carrier.power_d,
        carrier.q,
        carrier.q_source_power_d,
        carrier.r_ant_mm,
        carrier.r_post_mm,
        carrier.center_thickness_mm,
        carrier.iol_position_mm,
        carrier.achieved_sa_um,
    )
    if not all(math.isfinite(float(value)) for value in numeric):
        raise Task013Error("N0 carrier optical values must all be finite")
    if carrier.center_thickness_mm <= 0:
        raise Task013Error("N0 carrier center thickness must be positive")
    if not carrier.material.strip():
        raise Task013Error("N0 carrier material is required")
    if abs(carrier.q_source_power_d - carrier.power_d) > 1e-12:
        raise Task013Error("N0 carrier Q source power must equal actual carrier power")
    target = float(SA_TARGETS_UM[key.platform_id])
    if abs(carrier.achieved_sa_um - target) > sa_tolerance_um:
        raise Task013Error(
            f"N0 carrier standard-eye SA {carrier.achieved_sa_um:.6g} is outside "
            f"{target:.6g}±{sa_tolerance_um:.6g} µm"
        )


def native_carrier_lock_hash(
    carrier: ProvisionalCarrier,
    residual: ResidualProvenance,
) -> str:
    validate_native_carrier(carrier)
    residual.validate()
    if residual.platform_id != carrier.key.platform_id:
        raise Task013Error("N0 carrier and residual platform identities differ")
    payload = {
        "task_id": TASK013_ID,
        "carrier": asdict(carrier),
        "residual": asdict(residual),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_native_carrier_lock(
    carrier: ProvisionalCarrier,
    residual: ResidualProvenance,
) -> NativeCarrierLock:
    return NativeCarrierLock(
        carrier=carrier,
        residual=residual,
        lock_hash=native_carrier_lock_hash(carrier, residual),
    )


def _validate_native_locks(locks: Sequence[NativeCarrierLock]) -> tuple[NativeCarrierLock, ...]:
    expected = {
        (base, NATIVE_REFERENCE_CORNEA_ID, platform)
        for base in _base_values()
        for platform in _platform_values()
    }
    actual = {
        (
            lock.carrier.key.base_id,
            lock.carrier.key.cornea_id,
            lock.carrier.key.platform_id,
        )
        for lock in locks
    }
    if len(locks) != TASK013_EXPECTED_CARRIER_COUNT or actual != expected:
        raise Task013Error("TASK-013 requires exactly the 2×1×3 N0 carrier key space")
    if len(actual) != len(locks):
        raise Task013Error("TASK-013 carrier keys must be unique")
    for lock in locks:
        validate_native_carrier(lock.carrier)
        lock.residual.validate()
        expected_hash = native_carrier_lock_hash(lock.carrier, lock.residual)
        if lock.lock_hash != expected_hash:
            raise Task013Error(f"N0 carrier lock hash drifted: {lock.carrier_id}")
    return tuple(
        sorted(
            locks,
            key=lambda item: (
                item.carrier.key.base_id,
                item.carrier.key.platform_id,
            ),
        )
    )


def compute_native_lock_set_hash(locks: Sequence[NativeCarrierLock]) -> str:
    ordered = _validate_native_locks(locks)
    canonical = json.dumps(sorted(lock.lock_hash for lock in ordered), separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_task013_manifest(locks: Sequence[NativeCarrierLock]) -> Task013ManifestBundle:
    ordered = _validate_native_locks(locks)
    configs: list[NominalConfig] = []
    for lock in ordered:
        key = lock.carrier.key
        for state in (OpticState.MONO, OpticState.EDOF):
            for pupil in (3.0, 5.0):
                is_edof = state == OpticState.EDOF
                configs.append(
                    NominalConfig(
                        config_id=(
                            f"CFG_{key.base_id}_{NATIVE_REFERENCE_CORNEA_ID}_"
                            f"{key.platform_id}_{state}_EPD{int(pupil)}"
                        ),
                        carrier_id=lock.carrier_id,
                        base_id=key.base_id,
                        cornea_id=NATIVE_REFERENCE_CORNEA_ID,
                        platform_id=key.platform_id,
                        optic_state=state,
                        pupil_mm=pupil,
                        carrier_lock_hash=lock.lock_hash,
                        residual_id=lock.residual.residual_id if is_edof else None,
                        residual_sha256=lock.residual.residual_sha256 if is_edof else None,
                        residual_validation_policy_id=(
                            lock.residual.residual_validation_policy_id if is_edof else None
                        ),
                        residual_validation_policy_hash=(
                            lock.residual.residual_validation_policy_hash if is_edof else None
                        ),
                    )
                )
    if len(configs) != TASK013_EXPECTED_CONFIG_COUNT:
        raise Task013Error("TASK-013 manifest must contain exactly 24 configs")
    if len({config.config_id for config in configs}) != TASK013_EXPECTED_CONFIG_COUNT:
        raise Task013Error("TASK-013 config IDs must be unique")
    if len({config.pair_key for config in configs}) != TASK013_EXPECTED_PAIR_COUNT:
        raise Task013Error("TASK-013 manifest must contain exactly 12 matched pair keys")

    for config in configs:
        residual_values = (
            config.residual_id,
            config.residual_sha256,
            config.residual_validation_policy_id,
            config.residual_validation_policy_hash,
        )
        if config.optic_state == OpticState.MONO and any(
            value is not None for value in residual_values
        ):
            raise Task013Error("TASK-013 MONO config unexpectedly carries residual provenance")
        if config.optic_state == OpticState.EDOF and not all(residual_values):
            raise Task013Error("TASK-013 EDOF config lacks residual provenance")

    lock_set_hash = compute_native_lock_set_hash(ordered)
    payload = {
        "task_id": TASK013_ID,
        "native_cornea_id": NATIVE_REFERENCE_CORNEA_ID,
        "carrier_locks": [
            {
                "carrier": asdict(lock.carrier),
                "residual": asdict(lock.residual),
                "lock_hash": lock.lock_hash,
            }
            for lock in ordered
        ],
        "configs": [asdict(config) for config in configs],
        "lock_set_hash": lock_set_hash,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return Task013ManifestBundle(
        physical_carriers=ordered,
        nominal_configs=tuple(configs),
        manifest_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        lock_set_hash=lock_set_hash,
    )


def residual_provenance_from_existing_locks(
    existing_locks: Sequence[object],
) -> dict[str, ResidualProvenance]:
    by_platform: dict[str, ResidualProvenance] = {}
    for lock in existing_locks:
        carrier = getattr(lock, "carrier", None)
        if carrier is None:
            raise Task013Error("existing carrier lock lacks carrier")
        platform_id = str(carrier.key.platform_id)
        candidate = ResidualProvenance(
            platform_id=platform_id,
            residual_id=str(getattr(lock, "residual_id")),
            residual_sha256=str(getattr(lock, "residual_sha256")),
            residual_validation_policy_id=str(
                getattr(lock, "residual_validation_policy_id")
            ),
            residual_validation_policy_hash=str(
                getattr(lock, "residual_validation_policy_hash")
            ),
        )
        candidate.validate()
        prior = by_platform.get(platform_id)
        if prior is not None and prior != candidate:
            raise Task013Error(f"frozen residual provenance differs within platform {platform_id}")
        by_platform[platform_id] = candidate
    if set(by_platform) != set(_platform_values()):
        raise Task013Error("existing locks do not resolve exactly three frozen residuals")
    return by_platform


def check_residual_power_envelopes(
    existing_carriers: Sequence[ProvisionalCarrier],
    native_carriers: Sequence[ProvisionalCarrier],
) -> tuple[ResidualPowerEnvelopeCheck, ...]:
    for carrier in native_carriers:
        validate_native_carrier(carrier)
    checks: list[ResidualPowerEnvelopeCheck] = []
    for platform_id in _platform_values():
        existing = [
            float(carrier.power_d)
            for carrier in existing_carriers
            if str(carrier.key.platform_id) == platform_id
        ]
        native = [
            carrier
            for carrier in native_carriers
            if str(carrier.key.platform_id) == platform_id
        ]
        if len(existing) != 6:
            raise Task013Error(
                f"residual envelope requires six frozen existing carriers for {platform_id}"
            )
        if len(native) != 2:
            raise Task013Error(f"residual envelope requires two N0 carriers for {platform_id}")
        low, high = min(existing), max(existing)
        for carrier in sorted(native, key=lambda item: item.key.base_id):
            power = float(carrier.power_d)
            checks.append(
                ResidualPowerEnvelopeCheck(
                    platform_id=platform_id,
                    carrier_id=carrier.key.carrier_id,
                    n0_power_d=power,
                    existing_min_power_d=low,
                    existing_max_power_d=high,
                    passed=low <= power <= high,
                )
            )
    return tuple(checks)


def require_residual_power_envelopes(
    existing_carriers: Sequence[ProvisionalCarrier],
    native_carriers: Sequence[ProvisionalCarrier],
) -> tuple[ResidualPowerEnvelopeCheck, ...]:
    checks = check_residual_power_envelopes(existing_carriers, native_carriers)
    failures = tuple(check for check in checks if not check.passed)
    if failures:
        detail = ", ".join(
            f"{item.carrier_id}={item.n0_power_d:.6g}D outside "
            f"[{item.existing_min_power_d:.6g},{item.existing_max_power_d:.6g}]D"
            for item in failures
        )
        raise Task013Error(
            "N0 carrier lies outside frozen residual calibration power envelope; "
            f"additional residual replay validation is required: {detail}"
        )
    return checks


def manifest_config_map(bundle: Task013ManifestBundle) -> Mapping[str, NominalConfig]:
    return {config.config_id: config for config in bundle.nominal_configs}
