from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from .carriers import SA_TARGETS_UM, ProvisionalCarrier
from .domain import BaseId, OpticState, PlatformId, ScientificBaseline
from .manifest import NominalConfig
from .task013_native_reference import ResidualProvenance
from .task014_vertex_corrected_cornea import (
    TASK014_A0_ID,
    TASK014_B0_ID,
    TASK014_C0_ID,
    TASK014_ID,
    task014_prescription_snapshot,
)

TASK014_CORNEA_IDS = (TASK014_A0_ID, TASK014_B0_ID, TASK014_C0_ID)
TASK014_EXPECTED_CARRIER_COUNT = 18
TASK014_EXPECTED_CONFIG_COUNT = 72
TASK014_EXPECTED_PAIR_COUNT = 36
TASK014_EXPECTED_THROUGH_FOCUS_ROWS = 1080


class Task014ExtensionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Task014CarrierLock:
    carrier: ProvisionalCarrier
    residual: ResidualProvenance
    prescription_contract_sha256: str
    lock_hash: str

    @property
    def carrier_id(self) -> str:
        return self.carrier.key.carrier_id


@dataclass(frozen=True, slots=True)
class Task014ManifestBundle:
    physical_carriers: tuple[Task014CarrierLock, ...]
    nominal_configs: tuple[NominalConfig, ...]
    manifest_hash: str
    lock_set_hash: str
    prescription_contract_sha256: str


@dataclass(frozen=True, slots=True)
class Task014ResidualPowerEnvelopeCheck:
    platform_id: str
    carrier_id: str
    corrected_power_d: float
    existing_min_power_d: float
    existing_max_power_d: float
    within_existing_coverage: bool

    @property
    def extension_validation_required(self) -> bool:
        return not self.within_existing_coverage


def _platform_values() -> tuple[str, ...]:
    return tuple(str(value) for value in PlatformId)


def _base_values() -> tuple[str, ...]:
    return tuple(str(value) for value in BaseId)


def task014_prescription_contract_sha256(baseline: ScientificBaseline) -> str:
    payload = task014_prescription_snapshot(baseline)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_task014_carrier(
    carrier: ProvisionalCarrier,
    *,
    sa_tolerance_um: float = 0.01,
) -> None:
    key = carrier.key
    if key.base_id not in _base_values():
        raise Task014ExtensionError(f"TASK-014 carrier base is outside the frozen set: {key.base_id}")
    if key.cornea_id not in TASK014_CORNEA_IDS:
        raise Task014ExtensionError(f"TASK-014 carrier has unknown corrected cornea: {key.cornea_id}")
    if key.platform_id not in _platform_values():
        raise Task014ExtensionError(f"TASK-014 carrier has unknown platform: {key.platform_id}")
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
        raise Task014ExtensionError("TASK-014 carrier optical values must be finite")
    if carrier.center_thickness_mm <= 0 or not carrier.material.strip():
        raise Task014ExtensionError("TASK-014 carrier material/thickness is invalid")
    if abs(carrier.q_source_power_d - carrier.power_d) > 1.0e-12:
        raise Task014ExtensionError("TASK-014 Q source power must equal actual carrier power")
    target = float(SA_TARGETS_UM[key.platform_id])
    if abs(carrier.achieved_sa_um - target) > sa_tolerance_um:
        raise Task014ExtensionError(
            f"TASK-014 carrier SA {carrier.achieved_sa_um:.6g} is outside "
            f"{target:.6g}±{sa_tolerance_um:.6g} µm"
        )


def task014_carrier_lock_hash(
    carrier: ProvisionalCarrier,
    residual: ResidualProvenance,
    prescription_contract_sha256: str,
) -> str:
    validate_task014_carrier(carrier)
    residual.validate()
    if residual.platform_id != carrier.key.platform_id:
        raise Task014ExtensionError("TASK-014 carrier/residual platform identities differ")
    if len(prescription_contract_sha256) != 64:
        raise Task014ExtensionError("TASK-014 prescription contract SHA is invalid")
    payload = {
        "task_id": TASK014_ID,
        "carrier": asdict(carrier),
        "residual": asdict(residual),
        "prescription_contract_sha256": prescription_contract_sha256,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_task014_carrier_lock(
    carrier: ProvisionalCarrier,
    residual: ResidualProvenance,
    prescription_contract_sha256: str,
) -> Task014CarrierLock:
    return Task014CarrierLock(
        carrier=carrier,
        residual=residual,
        prescription_contract_sha256=prescription_contract_sha256,
        lock_hash=task014_carrier_lock_hash(
            carrier,
            residual,
            prescription_contract_sha256,
        ),
    )


def _validate_locks(
    locks: Sequence[Task014CarrierLock],
) -> tuple[Task014CarrierLock, ...]:
    expected = {
        (base, cornea, platform)
        for base in _base_values()
        for cornea in TASK014_CORNEA_IDS
        for platform in _platform_values()
    }
    actual = {
        (lock.carrier.key.base_id, lock.carrier.key.cornea_id, lock.carrier.key.platform_id)
        for lock in locks
    }
    if len(locks) != TASK014_EXPECTED_CARRIER_COUNT or actual != expected:
        raise Task014ExtensionError("TASK-014 requires exactly the 2×3×3 corrected carrier set")
    if len(actual) != len(locks):
        raise Task014ExtensionError("TASK-014 carrier keys must be unique")
    contract_hashes = {lock.prescription_contract_sha256 for lock in locks}
    if len(contract_hashes) != 1:
        raise Task014ExtensionError("TASK-014 carriers do not share one prescription contract")
    for lock in locks:
        validate_task014_carrier(lock.carrier)
        expected_hash = task014_carrier_lock_hash(
            lock.carrier,
            lock.residual,
            lock.prescription_contract_sha256,
        )
        if lock.lock_hash != expected_hash:
            raise Task014ExtensionError(f"TASK-014 carrier lock hash drifted: {lock.carrier_id}")
    return tuple(
        sorted(
            locks,
            key=lambda item: (
                item.carrier.key.base_id,
                item.carrier.key.cornea_id,
                item.carrier.key.platform_id,
            ),
        )
    )


def compute_task014_lock_set_hash(locks: Sequence[Task014CarrierLock]) -> str:
    ordered = _validate_locks(locks)
    canonical = json.dumps(sorted(lock.lock_hash for lock in ordered), separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_task014_manifest(locks: Sequence[Task014CarrierLock]) -> Task014ManifestBundle:
    ordered = _validate_locks(locks)
    configs: list[NominalConfig] = []
    for lock in ordered:
        key = lock.carrier.key
        for state in (OpticState.MONO, OpticState.EDOF):
            for pupil in (3.0, 5.0):
                is_edof = state == OpticState.EDOF
                configs.append(
                    NominalConfig(
                        config_id=(
                            f"CFG_{key.base_id}_{key.cornea_id}_{key.platform_id}_"
                            f"{state}_EPD{int(pupil)}"
                        ),
                        carrier_id=lock.carrier_id,
                        base_id=key.base_id,
                        cornea_id=key.cornea_id,
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
    if len(configs) != TASK014_EXPECTED_CONFIG_COUNT:
        raise Task014ExtensionError("TASK-014 manifest must contain exactly 72 configs")
    if len({config.config_id for config in configs}) != TASK014_EXPECTED_CONFIG_COUNT:
        raise Task014ExtensionError("TASK-014 config IDs must be unique")
    if len({config.pair_key for config in configs}) != TASK014_EXPECTED_PAIR_COUNT:
        raise Task014ExtensionError("TASK-014 manifest must contain exactly 36 matched pairs")
    for config in configs:
        residual_values = (
            config.residual_id,
            config.residual_sha256,
            config.residual_validation_policy_id,
            config.residual_validation_policy_hash,
        )
        if config.optic_state == OpticState.MONO and any(value is not None for value in residual_values):
            raise Task014ExtensionError("TASK-014 MONO config carries residual provenance")
        if config.optic_state == OpticState.EDOF and not all(residual_values):
            raise Task014ExtensionError("TASK-014 EDOF config lacks residual provenance")

    lock_set_hash = compute_task014_lock_set_hash(ordered)
    contract_sha = ordered[0].prescription_contract_sha256
    payload = {
        "task_id": TASK014_ID,
        "corrected_cornea_ids": TASK014_CORNEA_IDS,
        "prescription_contract_sha256": contract_sha,
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
    return Task014ManifestBundle(
        physical_carriers=ordered,
        nominal_configs=tuple(configs),
        manifest_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        lock_set_hash=lock_set_hash,
        prescription_contract_sha256=contract_sha,
    )


def check_task014_residual_power_envelopes(
    existing_carriers: Sequence[ProvisionalCarrier],
    corrected_carriers: Sequence[ProvisionalCarrier],
) -> tuple[Task014ResidualPowerEnvelopeCheck, ...]:
    """Classify existing residual-validation power coverage for corrected carriers."""

    for carrier in corrected_carriers:
        validate_task014_carrier(carrier)
    checks: list[Task014ResidualPowerEnvelopeCheck] = []
    for platform_id in _platform_values():
        existing = [
            float(carrier.power_d)
            for carrier in existing_carriers
            if str(carrier.key.platform_id) == platform_id
        ]
        corrected = [
            carrier
            for carrier in corrected_carriers
            if str(carrier.key.platform_id) == platform_id
        ]
        if len(existing) != 6:
            raise Task014ExtensionError(
                f"TASK-014 envelope requires six frozen existing carriers for {platform_id}"
            )
        if len(corrected) != 6:
            raise Task014ExtensionError(
                f"TASK-014 envelope requires six corrected carriers for {platform_id}"
            )
        low, high = min(existing), max(existing)
        for carrier in sorted(corrected, key=lambda item: (item.key.base_id, item.key.cornea_id)):
            power = float(carrier.power_d)
            checks.append(
                Task014ResidualPowerEnvelopeCheck(
                    platform_id=platform_id,
                    carrier_id=carrier.key.carrier_id,
                    corrected_power_d=power,
                    existing_min_power_d=low,
                    existing_max_power_d=high,
                    within_existing_coverage=low <= power <= high,
                )
            )
    return tuple(checks)


def require_task014_residual_power_envelopes(
    existing_carriers: Sequence[ProvisionalCarrier],
    corrected_carriers: Sequence[ProvisionalCarrier],
) -> tuple[Task014ResidualPowerEnvelopeCheck, ...]:
    """Backward-compatible coverage classifier; out-of-range triggers replay validation.

    Exact-carrier frozen-residual validation is enforced in the TASK-014 EDOF model
    materialization path. This helper therefore no longer raises solely because a
    corrected carrier lies outside the historical power envelope.
    """

    return check_task014_residual_power_envelopes(existing_carriers, corrected_carriers)


def manifest_config_map(bundle: Task014ManifestBundle) -> Mapping[str, NominalConfig]:
    return {config.config_id: config for config in bundle.nominal_configs}
