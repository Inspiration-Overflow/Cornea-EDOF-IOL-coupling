from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Sequence

from .carriers import CarrierKey, ProvisionalCarrier, ScientificInvariantError, expected_carrier_keys, validate_provisional_carrier
from .domain import OpticState


@dataclass(frozen=True, slots=True)
class CarrierLock:
    carrier: ProvisionalCarrier
    residual_id: str
    delta_f_residual_d: float
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


def _validate_locks(locks: Sequence[CarrierLock]) -> None:
    expected = set(expected_carrier_keys())
    keys = [lock.carrier.key for lock in locks]
    if len(locks) != 18 or set(keys) != expected or len(set(keys)) != 18:
        raise ScientificInvariantError("formal manifest requires exactly 18 unique carrier locks")
    for lock in locks:
        validate_provisional_carrier(lock.carrier)
        if not lock.residual_id or not lock.lock_hash:
            raise ScientificInvariantError("formal carrier lock must include residual_id and lock_hash")


def build_manifests(locks: Sequence[CarrierLock]) -> ManifestBundle:
    _validate_locks(locks)
    ordered = tuple(sorted(locks, key=lambda x: (x.carrier.key.base_id, x.carrier.key.cornea_id, x.carrier.key.platform_id)))
    configs: list[NominalConfig] = []
    for lock in ordered:
        key: CarrierKey = lock.carrier.key
        for state in (OpticState.MONO, OpticState.EDOF):
            for pupil in (3.0, 5.0):
                cid = f"CFG_{key.base_id}_{key.cornea_id}_{key.platform_id}_{state}_EPD{int(pupil)}"
                configs.append(NominalConfig(cid, lock.carrier_id, key.base_id, key.cornea_id, key.platform_id, state, pupil))
    if len(configs) != 72 or len({c.config_id for c in configs}) != 72:
        raise ScientificInvariantError("nominal manifest must contain 72 unique configs")
    payload = {
        "carrier_locks": [{"carrier_id": x.carrier_id, "key": asdict(x.carrier.key), "lock_hash": x.lock_hash, "residual_id": x.residual_id} for x in ordered],
        "configs": [asdict(c) for c in configs],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return ManifestBundle(ordered, tuple(configs), hashlib.sha256(text.encode()).hexdigest())
