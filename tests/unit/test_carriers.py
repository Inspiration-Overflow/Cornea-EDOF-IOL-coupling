from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from whole_eye_mvp.carriers import (
    CarrierKey,
    ProvisionalCarrier,
    ResidualCalibration,
    ResidualDefinition,
    ResidualValidationPolicy,
    ScientificInvariantError,
    expected_calibration_carriers,
    expected_carrier_keys,
    make_matched_pair,
    residuals_ready,
    validate_18_provisional_carriers,
    validate_provisional_carrier,
    validate_residual_definition,
)
from whole_eye_mvp.domain import PlatformId

POLICY = ResidualValidationPolicy("TEST_RESIDUAL_POLICY_v1", 0.01, 0.05)


def carrier(key: CarrierKey, index: int = 0) -> ProvisionalCarrier:
    target = {PlatformId.WFS: -0.20, PlatformId.RAD: -0.27, PlatformId.HOA: 0.0}[
        key.platform_id
    ]
    return ProvisionalCarrier(
        key,
        18.0 + index * 0.25,
        -0.2,
        18.0 + index * 0.25,
        12.0,
        -12.0,
        1.0,
        "IOL_1.46",
        4.5,
        target,
    )


def all_carriers() -> list[ProvisionalCarrier]:
    return [carrier(key, index) for index, key in enumerate(expected_carrier_keys())]


def _hashed_file(tmp_path: Path, name: str, content: str) -> tuple[str, str]:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path), hashlib.sha256(path.read_bytes()).hexdigest()


def residual(
    tmp_path: Path,
    platform: str,
    carriers: list[ProvisionalCarrier],
    *,
    all_gates: bool = True,
    measured_piston_um: float = 0.0,
    measured_global_defocus_d: float = 0.0,
) -> ResidualDefinition:
    payload_ref, payload_sha = _hashed_file(tmp_path, f"{platform}.payload", "0.0 0.0\n")
    validation_ref, validation_sha = _hashed_file(
        tmp_path,
        f"{platform}.validation.json",
        '{"source":"OpticStudio-test-evidence"}',
    )
    selected = expected_calibration_carriers(carriers, platform)
    labels = ("low", "median", "high") if all_gates else ("low", "median")
    calibrations = []
    for label in labels:
        target = selected[label]
        evidence_ref, evidence_sha = _hashed_file(
            tmp_path,
            f"{platform}-{label}.json",
            f'{{"carrier":"{target.key.carrier_id}"}}',
        )
        calibrations.append(
            ResidualCalibration(
                label,
                target.key.carrier_id,
                target.power_d,
                True,
                0.1,
                evidence_ref,
                evidence_sha,
            )
        )
    return ResidualDefinition(
        f"RES_{platform}",
        platform,
        "v1",
        "radial_sag_samples",
        payload_ref,
        "mm",
        (0.0, 3.0),
        True,
        True,
        payload_sha,
        measured_piston_um,
        measured_global_defocus_d,
        validation_ref,
        validation_sha,
        tuple(calibrations),
    )


@pytest.mark.unit
def test_expected_carrier_key_space_is_exactly_18() -> None:
    keys = expected_carrier_keys()
    assert len(keys) == len(set(keys)) == 18


@pytest.mark.unit
def test_power_specific_q_and_sa_target_are_enforced() -> None:
    c = carrier(expected_carrier_keys()[0])
    validate_provisional_carrier(c)
    with pytest.raises(ScientificInvariantError, match="source power"):
        validate_provisional_carrier(
            ProvisionalCarrier(
                c.key,
                20,
                c.q,
                19.5,
                c.r_ant_mm,
                c.r_post_mm,
                c.center_thickness_mm,
                c.material,
                c.iol_position_mm,
                c.achieved_sa_um,
            )
        )
    with pytest.raises(ScientificInvariantError, match="SA"):
        validate_provisional_carrier(
            ProvisionalCarrier(
                c.key,
                20,
                c.q,
                20,
                c.r_ant_mm,
                c.r_post_mm,
                c.center_thickness_mm,
                c.material,
                c.iol_position_mm,
                0.2,
            )
        )


@pytest.mark.unit
def test_carrier_validation_is_fail_closed_for_nan_and_invalid_physical_fields() -> None:
    c = carrier(expected_carrier_keys()[0])
    with pytest.raises(ScientificInvariantError, match="finite"):
        validate_provisional_carrier(
            ProvisionalCarrier(
                c.key,
                math.nan,
                c.q,
                math.nan,
                c.r_ant_mm,
                c.r_post_mm,
                c.center_thickness_mm,
                c.material,
                c.iol_position_mm,
                c.achieved_sa_um,
            )
        )
    with pytest.raises(ScientificInvariantError, match="thickness"):
        validate_provisional_carrier(
            ProvisionalCarrier(
                c.key,
                c.power_d,
                c.q,
                c.q_source_power_d,
                c.r_ant_mm,
                c.r_post_mm,
                0.0,
                c.material,
                c.iol_position_mm,
                c.achieved_sa_um,
            )
        )


@pytest.mark.unit
def test_residual_payload_numeric_evidence_and_actual_power_gates_are_required(tmp_path: Path) -> None:
    carriers = all_carriers()
    residuals = [residual(tmp_path, platform, carriers) for platform in ("WFS", "RAD", "HOA")]
    assert residuals_ready(residuals, carriers=carriers, policy=POLICY)
    assert not residuals_ready(
        [residual(tmp_path, "WFS", carriers, all_gates=False), *residuals[1:]],
        carriers=carriers,
        policy=POLICY,
    )
    assert not residuals_ready(
        [residual(tmp_path, "WFS", carriers), residual(tmp_path, "WFS", carriers), residuals[2]],
        carriers=carriers,
        policy=POLICY,
    )

    flag_only = residuals[0]
    flag_only = ResidualDefinition(
        flag_only.residual_id,
        flag_only.platform_id,
        flag_only.version,
        flag_only.representation,
        flag_only.payload_ref,
        flag_only.units,
        flag_only.radial_domain_mm,
        True,
        True,
        flag_only.sha256,
        None,
        None,
        "",
        "",
        flag_only.calibrations,
    )
    with pytest.raises(ScientificInvariantError, match="measured"):
        validate_residual_definition(flag_only, carriers=carriers, policy=POLICY)


@pytest.mark.unit
def test_residual_calibration_must_bind_expected_low_median_high_actual_carriers(tmp_path: Path) -> None:
    carriers = all_carriers()
    r = residual(tmp_path, "WFS", carriers)
    bad_first = r.calibrations[0]
    wrong = ResidualCalibration(
        bad_first.label,
        r.calibrations[1].carrier_id,
        r.calibrations[1].actual_power_d,
        True,
        bad_first.distance_shift_d,
        bad_first.evidence_ref,
        bad_first.evidence_sha256,
    )
    bad = ResidualDefinition(
        r.residual_id,
        r.platform_id,
        r.version,
        r.representation,
        r.payload_ref,
        r.units,
        r.radial_domain_mm,
        r.piston_removed,
        r.defocus_removed,
        r.sha256,
        r.measured_piston_um,
        r.measured_global_defocus_d,
        r.validation_evidence_ref,
        r.validation_evidence_sha256,
        (wrong, *r.calibrations[1:]),
    )
    with pytest.raises(ScientificInvariantError, match="expected actual carrier"):
        validate_residual_definition(bad, carriers=carriers, policy=POLICY)


@pytest.mark.unit
def test_formal_18_set_validation_rejects_missing_key_and_nan() -> None:
    carriers = all_carriers()
    validate_18_provisional_carriers(carriers)
    with pytest.raises(ScientificInvariantError, match="exactly"):
        validate_18_provisional_carriers(carriers[:-1])
    broken = list(carriers)
    c = broken[0]
    broken[0] = ProvisionalCarrier(
        c.key,
        math.nan,
        c.q,
        math.nan,
        c.r_ant_mm,
        c.r_post_mm,
        c.center_thickness_mm,
        c.material,
        c.iol_position_mm,
        c.achieved_sa_um,
    )
    with pytest.raises(ScientificInvariantError, match="finite"):
        validate_18_provisional_carriers(broken)


@pytest.mark.unit
def test_matched_pair_reuses_same_physical_carrier(tmp_path: Path) -> None:
    carriers = all_carriers()
    c = next(carrier for carrier in carriers if carrier.key.platform_id == "WFS")
    pair = make_matched_pair(
        c,
        residual(tmp_path, "WFS", carriers),
        delta_f_residual_d=0.125,
        carriers=carriers,
        policy=POLICY,
    )
    assert pair.carrier is c
    assert pair.mono_residual_id is None
    assert pair.edof_residual_id == "RES_WFS"
    assert pair.delta_f_residual_d == 0.125
