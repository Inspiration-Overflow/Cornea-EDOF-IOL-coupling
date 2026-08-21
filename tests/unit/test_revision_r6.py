from __future__ import annotations

import pytest

from whole_eye_mvp.revision_r6 import (
    R6_EXPECTED_CARRIER_COUNT,
    R6_RAD_REJECTED_R4_MAX_ABS_ERROR_D,
    R6_RAD_REJECTED_R4_RMS_ERROR_D,
    calibration_labels_by_platform,
    expected_r6_carrier_keys,
    rad_powp_local_gate,
    validate_r6_carrier_keys,
)


def test_r6_key_space_is_exactly_two_by_four_by_three() -> None:
    keys = expected_r6_carrier_keys()
    assert len(keys) == R6_EXPECTED_CARRIER_COUNT == 24
    assert {key.cornea_id for key in keys} == {"N0", "A0", "B0", "C0"}
    validate_r6_carrier_keys(keys)


def test_r6_key_validation_rejects_missing_or_duplicate_carriers() -> None:
    keys = expected_r6_carrier_keys()
    with pytest.raises(ValueError, match="2×4×3"):
        validate_r6_carrier_keys(keys[:-1])
    with pytest.raises(ValueError, match="2×4×3"):
        validate_r6_carrier_keys(keys[:-1] + (keys[0],))


def test_rad_powp_gate_uses_rejected_r4_not_r4_2_as_hard_baseline() -> None:
    assert rad_powp_local_gate(
        sign_identity_passed=True,
        rms_error_d=0.8,
        max_abs_error_d=2.0,
    )
    assert not rad_powp_local_gate(
        sign_identity_passed=False,
        rms_error_d=0.1,
        max_abs_error_d=0.2,
    )
    assert not rad_powp_local_gate(
        sign_identity_passed=True,
        rms_error_d=R6_RAD_REJECTED_R4_RMS_ERROR_D,
        max_abs_error_d=0.2,
    )
    assert not rad_powp_local_gate(
        sign_identity_passed=True,
        rms_error_d=0.2,
        max_abs_error_d=R6_RAD_REJECTED_R4_MAX_ABS_ERROR_D,
    )


def test_calibration_selection_returns_low_median_high_exact_carriers() -> None:
    keys = expected_r6_carrier_keys()
    rows = tuple((key, 10.0 + index) for index, key in enumerate(keys))
    selected = calibration_labels_by_platform(rows)
    assert set(selected) == {"WFS", "RAD", "HOA"}
    for row in selected.values():
        assert set(row) == {"low", "median", "high"}
        assert len(set(row.values())) == 3
