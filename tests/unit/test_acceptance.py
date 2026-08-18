from __future__ import annotations

import math

import pytest

from whole_eye_mvp.acceptance import (
    AcceptanceError,
    RepeatabilityPoint,
    ResultEnvelope,
    validate_nominal_acceptance,
    validate_repeatability,
)
from whole_eye_mvp.carriers import (
    ProvisionalCarrier,
    ResidualValidationPolicy,
    expected_carrier_keys,
)
from whole_eye_mvp.domain import PlatformId
from whole_eye_mvp.manifest import CarrierLock, build_manifests, compute_carrier_lock_hash


def bundle():
    locks = []
    for index, key in enumerate(expected_carrier_keys()):
        target = {PlatformId.WFS: -0.20, PlatformId.RAD: -0.27, PlatformId.HOA: 0.0}[
            key.platform_id
        ]
        carrier = ProvisionalCarrier(
            key,
            20 + index * 0.01,
            -0.2,
            20 + index * 0.01,
            12,
            -12,
            1,
            "IOL",
            4.5,
            target,
        )
        residual_id = f"RES_{key.platform_id}"
        residual_sha = f"sha-{key.platform_id}"
        policy = ResidualValidationPolicy("POLICY_v1", 0.01, 0.05)
        delta_f = 0.1
        locks.append(
            CarrierLock(
                carrier,
                residual_id,
                residual_sha,
                policy.policy_id,
                policy.policy_hash,
                delta_f,
                compute_carrier_lock_hash(
                    carrier,
                    residual_id,
                    residual_sha,
                    policy.policy_id,
                    policy.policy_hash,
                    delta_f,
                ),
            )
        )
    return build_manifests(locks)


@pytest.mark.unit
def test_nominal_acceptance_requires_exact_manifest_72_36_1080() -> None:
    data = bundle()
    rows = [
        ResultEnvelope(config.config_id, config.pair_key, True, 15)
        for config in data.nominal_configs
    ]
    pairs = sorted({config.pair_key for config in data.nominal_configs})
    summary = validate_nominal_acceptance(rows, pairs, manifest=data)
    assert (summary.completed_configs, summary.matched_pairs, summary.through_focus_rows) == (
        72,
        36,
        1080,
    )
    with pytest.raises(AcceptanceError, match="manifest"):
        validate_nominal_acceptance(rows[:-1], pairs, manifest=data)


@pytest.mark.unit
def test_duplicate_missing_pair_and_wrong_config_ids_are_rejected() -> None:
    data = bundle()
    rows = [
        ResultEnvelope(config.config_id, config.pair_key, True, 15)
        for config in data.nominal_configs
    ]
    pairs = sorted({config.pair_key for config in data.nominal_configs})
    with pytest.raises(AcceptanceError, match="duplicate"):
        validate_nominal_acceptance(
            rows[:-1] + [rows[0]], pairs, manifest=data
        )
    with pytest.raises(AcceptanceError, match="paired deltas"):
        validate_nominal_acceptance(rows, pairs[:-1], manifest=data)

    wrong = [
        ResultEnvelope(f"WRONG_{index}", row.pair_key, True, 15)
        for index, row in enumerate(rows)
    ]
    with pytest.raises(AcceptanceError, match="manifest"):
        validate_nominal_acceptance(wrong, pairs, manifest=data)


@pytest.mark.unit
def test_repeatability_tolerances_and_finite_values() -> None:
    first = {"x": RepeatabilityPoint(0.5, 0.4, 0.1, 0.02, 0.0)}
    second = {"x": RepeatabilityPoint(0.5004, 0.4003, 0.1005, 0.0205, 0.0)}
    validate_repeatability(first, second)
    with pytest.raises(AcceptanceError, match="mtfa"):
        validate_repeatability(
            first, {"x": RepeatabilityPoint(0.51, 0.4, 0.1, 0.02, 0.0)}
        )
    with pytest.raises(AcceptanceError, match="distance"):
        validate_repeatability(
            first, {"x": RepeatabilityPoint(0.5, 0.4, 0.1, 0.02, 0.25)}
        )
    with pytest.raises(AcceptanceError, match="finite"):
        validate_repeatability(
            first, {"x": RepeatabilityPoint(math.nan, 0.4, 0.1, 0.02, 0.0)}
        )
