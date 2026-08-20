from __future__ import annotations

import pytest

from whole_eye_mvp.carriers import SA_TARGETS_UM, CarrierKey, ProvisionalCarrier
from whole_eye_mvp.domain import BaseId, OpticState, PlatformId, ScientificBaseline
from whole_eye_mvp.task013_native_reference import ResidualProvenance
from whole_eye_mvp.task014_extension import (
    TASK014_CORNEA_IDS,
    TASK014_EXPECTED_CARRIER_COUNT,
    TASK014_EXPECTED_CONFIG_COUNT,
    TASK014_EXPECTED_PAIR_COUNT,
    Task014ExtensionError,
    build_task014_manifest,
    make_task014_carrier_lock,
    require_task014_residual_power_envelopes,
    task014_prescription_contract_sha256,
)


def _residual(platform: str) -> ResidualProvenance:
    return ResidualProvenance(
        platform_id=platform,
        residual_id=f"RES_{platform}",
        residual_sha256="a" * 64,
        residual_validation_policy_id="POLICY",
        residual_validation_policy_hash="b" * 64,
    )


def _carrier(base: str, cornea: str, platform: str, power: float) -> ProvisionalCarrier:
    return ProvisionalCarrier(
        key=CarrierKey(base, cornea, platform),
        power_d=power,
        q=0.1,
        q_source_power_d=power,
        r_ant_mm=10.0,
        r_post_mm=-10.0,
        center_thickness_mm=1.0,
        material="MODEL_N1460",
        iol_position_mm=4.5,
        achieved_sa_um=float(SA_TARGETS_UM[platform]),
    )


def _locks():
    baseline = ScientificBaseline("MVP_2026_v2")
    contract_sha = task014_prescription_contract_sha256(baseline)
    locks = []
    for base_index, base in enumerate((str(BaseId.LB_AL2395), str(BaseId.ATC_M3_AL24477))):
        for cornea_index, cornea in enumerate(TASK014_CORNEA_IDS):
            for platform in (str(PlatformId.WFS), str(PlatformId.RAD), str(PlatformId.HOA)):
                power = 18.0 + base_index + 0.2 * cornea_index
                carrier = _carrier(base, cornea, platform, power)
                locks.append(make_task014_carrier_lock(carrier, _residual(platform), contract_sha))
    return locks


def test_task014_manifest_is_independent_18_72_36_matrix() -> None:
    bundle = build_task014_manifest(_locks())
    assert len(bundle.physical_carriers) == TASK014_EXPECTED_CARRIER_COUNT == 18
    assert len(bundle.nominal_configs) == TASK014_EXPECTED_CONFIG_COUNT == 72
    assert len({config.pair_key for config in bundle.nominal_configs}) == TASK014_EXPECTED_PAIR_COUNT == 36
    assert {config.cornea_id for config in bundle.nominal_configs} == set(TASK014_CORNEA_IDS)
    assert {config.pupil_mm for config in bundle.nominal_configs} == {3.0, 5.0}
    assert {str(config.optic_state) for config in bundle.nominal_configs} == {
        str(OpticState.MONO),
        str(OpticState.EDOF),
    }


def test_task014_mono_and_edof_residual_provenance_are_paired() -> None:
    bundle = build_task014_manifest(_locks())
    for pair_key in {config.pair_key for config in bundle.nominal_configs}:
        pair = [config for config in bundle.nominal_configs if config.pair_key == pair_key]
        assert len(pair) == 2
        mono = next(item for item in pair if item.optic_state == OpticState.MONO)
        edof = next(item for item in pair if item.optic_state == OpticState.EDOF)
        assert mono.carrier_id == edof.carrier_id
        assert mono.residual_id is None
        assert edof.residual_id is not None


def test_task014_rejects_legacy_cornea_identity() -> None:
    baseline = ScientificBaseline("MVP_2026_v2")
    contract_sha = task014_prescription_contract_sha256(baseline)
    carrier = _carrier(str(BaseId.LB_AL2395), "A0", str(PlatformId.WFS), 18.0)
    with pytest.raises(Task014ExtensionError):
        make_task014_carrier_lock(carrier, _residual(str(PlatformId.WFS)), contract_sha)


def test_task014_power_envelope_accepts_corrected_carriers_inside_frozen_range() -> None:
    existing = []
    corrected = []
    for platform in (str(PlatformId.WFS), str(PlatformId.RAD), str(PlatformId.HOA)):
        for index in range(6):
            existing.append(_carrier(str(BaseId.LB_AL2395), "A0V12", platform, 15.0 + index))
        for base in (str(BaseId.LB_AL2395), str(BaseId.ATC_M3_AL24477)):
            for cornea in TASK014_CORNEA_IDS:
                corrected.append(_carrier(base, cornea, platform, 17.5))
    checks = require_task014_residual_power_envelopes(existing, corrected)
    assert len(checks) == 18
    assert all(check.passed for check in checks)
    assert not any(check.extension_validation_required for check in checks)


def test_task014_power_envelope_outside_is_validation_trigger() -> None:
    existing = []
    corrected = []
    for platform in (str(PlatformId.WFS), str(PlatformId.RAD), str(PlatformId.HOA)):
        for index in range(6):
            existing.append(_carrier(str(BaseId.LB_AL2395), "A0V12", platform, 15.0 + index))
        for base in (str(BaseId.LB_AL2395), str(BaseId.ATC_M3_AL24477)):
            for cornea in TASK014_CORNEA_IDS:
                power = 25.0 if (platform == str(PlatformId.WFS) and cornea == "A0V12") else 17.5
                corrected.append(_carrier(base, cornea, platform, power))
    checks = require_task014_residual_power_envelopes(existing, corrected)
    flagged = [check for check in checks if check.extension_validation_required]
    assert len(flagged) == 2
    assert all(check.platform_id == str(PlatformId.WFS) for check in flagged)
    assert all(check.carrier_id.endswith("_A0V12_WFS") for check in flagged)
    assert all(check.passed is False for check in flagged)
