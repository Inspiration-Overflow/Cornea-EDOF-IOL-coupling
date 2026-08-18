from __future__ import annotations

import pytest

from whole_eye_mvp.carriers import ProvisionalCarrier, ScientificInvariantError, expected_carrier_keys
from whole_eye_mvp.domain import PlatformId
from whole_eye_mvp.manifest import CarrierLock, build_manifests


def lock_for(key, i: int) -> CarrierLock:
    target = {PlatformId.WFS:-.20, PlatformId.RAD:-.27, PlatformId.HOA:0.0}[key.platform_id]
    c = ProvisionalCarrier(key, 19+i*.01, -0.2, 19+i*.01, 12, -12, 1, 'IOL_1.46', 4.5, target)
    return CarrierLock(c, f'RES_{key.platform_id}', .1, f'hash-{i}')


@pytest.mark.unit
def test_manifest_is_exactly_18_carriers_and_72_configs() -> None:
    locks = [lock_for(k,i) for i,k in enumerate(expected_carrier_keys())]
    bundle = build_manifests(locks)
    assert len(bundle.physical_carriers) == 18
    assert len(bundle.nominal_configs) == 72
    assert len({c.config_id for c in bundle.nominal_configs}) == 72
    assert len({c.pair_key for c in bundle.nominal_configs}) == 36
    assert {c.optic_state for c in bundle.nominal_configs} == {'MONO','EDOF'}
    assert {c.pupil_mm for c in bundle.nominal_configs} == {3.0,5.0}
    assert all(c.wavelength_nm == 555 and c.field_deg == 0 and c.iol_tilt_deg == 0 for c in bundle.nominal_configs)


@pytest.mark.unit
def test_manifest_hash_is_stable_under_input_order() -> None:
    locks = [lock_for(k,i) for i,k in enumerate(expected_carrier_keys())]
    assert build_manifests(locks).manifest_hash == build_manifests(list(reversed(locks))).manifest_hash


@pytest.mark.unit
def test_missing_or_duplicate_lock_is_rejected() -> None:
    locks = [lock_for(k,i) for i,k in enumerate(expected_carrier_keys())]
    with pytest.raises(ScientificInvariantError, match='18'):
        build_manifests(locks[:-1])
    with pytest.raises(ScientificInvariantError, match='18'):
        build_manifests(locks[:-1] + [locks[0]])
