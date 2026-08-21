from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from .carriers import (
    CarrierKey,
    ProvisionalCarrier,
    ScientificInvariantError,
    expected_carrier_keys,
    validate_provisional_carrier,
)
from .domain import OpticState


@dataclass(frozen=True, slots=True)
class CarrierLock:
    """Immutable physical-carrier + residual provenance.

    Delta-F is deliberately not part of carrier identity: the residual-induced best-focus
    shift is an analysis result that can depend on pupil and analysis metric. It is saved
    by the analysis/result layer rather than hashed into the physical carrier lock.
    """

    carrier: ProvisionalCarrier
    residual_id: str
    residual_sha256: str
    residual_validation_policy_id: str
    residual_validation_policy_hash: str
    lock_hash: str

    @property
    def carrier_id(self) -> str:
        return self.carrier.key.carrier_id


@dataclass(frozen=True, slots=True)
class NominalConfig:
    config_id: str
    carrier_id: str
    base_id: str
    cornea_id: str
    platform_id: str
    optic_state: str
    pupil_mm: float
    carrier_lock_hash: str
    residual_id: str | None = None
    residual_sha256: str | None = None
    residual_validation_policy_id: str | None = None
    residual_validation_policy_hash: str | None = None
    wavelength_nm: float = 555.0
    field_deg: float = 0.0
    cornea_decentration_mm: float = 0.0
    iol_decentration_mm: float = 0.0
    iol_tilt_deg: float = 0.0
    micro_monovision_defocus_d: float = 0.0

    @property
    def pair_key(self) -> str:
        return f"{self.carrier_id}_EPD{self.pupil_mm:g}"


@dataclass(frozen=True, slots=True)
class ManifestBundle:
    physical_carriers: tuple[CarrierLock, ...]
    nominal_configs: tuple[NominalConfig, ...]
    manifest_hash: str


def compute_carrier_lock_hash(
    carrier: ProvisionalCarrier,
    residual_id: str,
    residual_sha256: str,
    residual_validation_policy_id: str,
    residual_validation_policy_hash: str,
) -> str:
    payload = {
        "carrier": asdict(carrier),
        "residual_id": residual_id,
        "residual_sha256": residual_sha256,
        "residual_validation_policy_id": residual_validation_policy_id,
        "residual_validation_policy_hash": residual_validation_policy_hash,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_locks(locks: Sequence[CarrierLock]) -> None:
    expected = set(expected_carrier_keys())
    keys = [lock.carrier.key for lock in locks]
    if len(locks) != 18 or set(keys) != expected or len(set(keys)) != 18:
        raise ScientificInvariantError("formal manifest requires exactly 18 unique carrier locks")
    for lock in locks:
        validate_provisional_carrier(lock.carrier)
        if not lock.residual_id.strip() or not lock.residual_sha256.strip():
            raise ScientificInvariantError("formal carrier lock must include residual identity/hash")
        if not lock.residual_validation_policy_id.strip() or not lock.residual_validation_policy_hash.strip():
            raise ScientificInvariantError(
                "formal carrier lock must include residual validation policy ID/hash"
            )
        expected_hash = compute_carrier_lock_hash(
            lock.carrier,
            lock.residual_id,
            lock.residual_sha256,
            lock.residual_validation_policy_id,
            lock.residual_validation_policy_hash,
        )
        if lock.lock_hash != expected_hash:
            raise ScientificInvariantError("formal carrier lock hash does not match lock contents")


def compute_lock_set_hash(locks: Sequence[CarrierLock]) -> str:
    _validate_locks(locks)
    ordered_hashes = sorted(lock.lock_hash for lock in locks)
    text = json.dumps(ordered_hashes, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_manifests(locks: Sequence[CarrierLock]) -> ManifestBundle:
    _validate_locks(locks)
    ordered = tuple(
        sorted(
            locks,
            key=lambda item: (
                item.carrier.key.base_id,
                item.carrier.key.cornea_id,
                item.carrier.key.platform_id,
            ),
        )
    )
    configs: list[NominalConfig] = []
    for lock in ordered:
        key: CarrierKey = lock.carrier.key
        for state in (OpticState.MONO, OpticState.EDOF):
            for pupil in (3.0, 5.0):
                config_id = (
                    f"CFG_{key.base_id}_{key.cornea_id}_{key.platform_id}_{state}_EPD{int(pupil)}"
                )
                is_edof = state == OpticState.EDOF
                configs.append(
                    NominalConfig(
                        config_id=config_id,
                        carrier_id=lock.carrier_id,
                        base_id=key.base_id,
                        cornea_id=key.cornea_id,
                        platform_id=key.platform_id,
                        optic_state=state,
                        pupil_mm=pupil,
                        carrier_lock_hash=lock.lock_hash,
                        residual_id=lock.residual_id if is_edof else None,
                        residual_sha256=lock.residual_sha256 if is_edof else None,
                        residual_validation_policy_id=(
                            lock.residual_validation_policy_id if is_edof else None
                        ),
                        residual_validation_policy_hash=(
                            lock.residual_validation_policy_hash if is_edof else None
                        ),
                    )
                )
    if len(configs) != 72 or len({config.config_id for config in configs}) != 72:
        raise ScientificInvariantError("nominal manifest must contain 72 unique configs")
    for config in configs:
        if config.optic_state == OpticState.MONO:
            if any(
                value is not None
                for value in (
                    config.residual_id,
                    config.residual_sha256,
                    config.residual_validation_policy_id,
                    config.residual_validation_policy_hash,
                )
            ):
                raise ScientificInvariantError("MONO config must not carry an EDOF residual")
        else:
            if not all(
                value
                for value in (
                    config.residual_id,
                    config.residual_sha256,
                    config.residual_validation_policy_id,
                    config.residual_validation_policy_hash,
                )
            ):
                raise ScientificInvariantError("EDOF config must carry residual provenance")
    payload = {
        "carrier_locks": [asdict(lock) for lock in ordered],
        "configs": [asdict(config) for config in configs],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return ManifestBundle(
        ordered,
        tuple(configs),
        hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )
