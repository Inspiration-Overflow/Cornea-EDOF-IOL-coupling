from __future__ import annotations

import pytest

from whole_eye_mvp.carriers import (
    ProvisionalCarrier,
    ResidualValidationPolicy,
    ScientificInvariantError,
    expected_carrier_keys,
)
from whole_eye_mvp.domain import OpticState, PlatformId
from whole_eye_mvp.manifest import (
    CarrierLock,
    build_manifests,
    compute_carrier_lock_hash,
)


def lock(index, key) -> CarrierLock:
    target = {PlatformId.WFS: -0.20, PlatformId.RAD: -0.27, PlatformId.HOA: 0.0}[key.platform_id]
    carrier = ProvisionalCarrier(
        key,
        19 + index * 0.01,
        -0.2,
        19 + index * 0.01,
        12,
        -12,
        1,
        "IOL_1.46",
        4.5,
        target,
    )
    residual_id = f"RES_{key.platform_id}"
    residual_sha = f"sha-{key.platform_id}"
    policy = ResidualValidationPolicy("POLICY_v1", 0.01, 0.05)
    lock_hash = compute_carrier_lock_hash(
        carrier,
        residual_id,
        residual_sha,
        policy.policy_id,
        policy.policy_hash,
    )
    return CarrierLock(
        carrier,
        residual_id,
        residual_sha,
        policy.policy_id,
        policy.policy_hash,
        lock_hash,
    )


def locks() -> list[CarrierLock]:
    return [lock(index, key) for index, key in enumerate(expected_carrier_keys())]


@pytest.mark.unit
def test_manifest_is_exactly_18_carriers_and_72_configs() -> None:
    bundle = build_manifests(locks())
    assert len(bundle.physical_carriers) == 18
    assert len(bundle.nominal_configs) == 72
    assert len({config.config_id for config in bundle.nominal_configs}) == 72
    assert len({config.pair_key for config in bundle.nominal_configs}) == 36
    assert all(config.carrier_lock_hash for config in bundle.nominal_configs)
    assert all(
        config.residual_id is None
        for config in bundle.nominal_configs
        if config.optic_state == OpticState.MONO
    )
    assert all(
        config.residual_id and config.residual_sha256 and config.residual_validation_policy_id
        for config in bundle.nominal_configs
        if config.optic_state == OpticState.EDOF
    )


@pytest.mark.unit
def test_manifest_hash_is_stable_under_input_order() -> None:
    original = locks()
    first = build_manifests(original)
    second = build_manifests(list(reversed(original)))
    assert first.manifest_hash == second.manifest_hash
    assert first.nominal_configs == second.nominal_configs


@pytest.mark.unit
def test_missing_duplicate_or_tampered_lock_is_rejected() -> None:
    original = locks()
    with pytest.raises(ScientificInvariantError, match="18"):
        build_manifests(original[:-1])
    with pytest.raises(ScientificInvariantError, match="18"):
        build_manifests([*original[:-1], original[0]])

    tampered = list(original)
    item = tampered[0]
    tampered[0] = CarrierLock(
        item.carrier,
        item.residual_id,
        item.residual_sha256,
        item.residual_validation_policy_id,
        item.residual_validation_policy_hash,
        "fake-hash",
    )
    with pytest.raises(ScientificInvariantError, match="hash"):
        build_manifests(tampered)
