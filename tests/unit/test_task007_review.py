from __future__ import annotations

import copy

import pytest

from whole_eye_mvp.task007_review import (
    MechanismDecision,
    Task007ReviewError,
    review_task007_consolidated_payload,
)


def _record() -> dict[str, object]:
    return {
        "carrier_id": "CAR",
        "actual_power_d": 22.0,
        "standard_readback": {
            "measured_piston_um": 0.001,
            "measured_global_defocus_d": 0.002,
        },
        "actual_readback": {
            "measured_piston_um": 0.04,
            "measured_global_defocus_d": 0.09,
        },
        "mono_ray_health": {"passed": True, "failures": []},
        "edof_ray_health": {"passed": True, "failures": []},
    }


def _payload() -> dict[str, object]:
    return {
        "phase": "TASK-007-CONSOLIDATED-FULL18-RESIDUAL-CALIBRATION",
        "evidence_only": True,
        "formal_artifact": False,
        "tdd_999_cleared": False,
        "shared_p0_count": 6,
        "carrier_count": 18,
        "all_18_carriers_validated": True,
        "calibration_count": 9,
        "settings": {"piston_tolerance_um": 0.01, "global_defocus_tolerance_d": 0.125},
        "residual_payloads": {platform: {} for platform in ("WFS", "RAD", "HOA")},
        "calibration_evidence": {
            platform: {label: _record() for label in ("low", "median", "high")}
            for platform in ("WFS", "RAD", "HOA")
        },
        "numerical_hard_gates_passed": False,
        "code_commit": "a" * 40,
        "local_report_sha256": "b" * 64,
    }


def _decisions() -> tuple[MechanismDecision, ...]:
    return tuple(
        MechanismDecision(platform, True, f"{platform} mechanism preserved across low/median/high")
        for platform in ("WFS", "RAD", "HOA")
    )


def test_review_uses_standard_eye_low_order_gate_not_actual_eye_ssag_diagnostic() -> None:
    result = review_task007_consolidated_payload(_payload(), _decisions())
    assert result.source_numerical_hard_gates_passed is False
    assert result.source_false_negative_explained is True
    assert result.standard_eye_low_order_gate_passed is True
    assert result.all_ray_health_passed is True
    assert result.all_mechanisms_passed is True
    assert result.tdd_999_evidence_complete is True
    assert result.tdd_999_cleared is True
    assert result.formal_artifact is False
    assert len(result.review_hash) == 64


def test_review_rejects_standard_eye_policy_failure() -> None:
    payload = _payload()
    records = payload["calibration_evidence"]
    assert isinstance(records, dict)
    rad = records["RAD"]
    assert isinstance(rad, dict)
    low = rad["low"]
    assert isinstance(low, dict)
    standard = low["standard_readback"]
    assert isinstance(standard, dict)
    standard["measured_piston_um"] = 0.011
    with pytest.raises(Task007ReviewError, match="standard-eye"):
        review_task007_consolidated_payload(payload, _decisions())


def test_review_rejects_missing_ray_health_or_calibration() -> None:
    payload = _payload()
    records = payload["calibration_evidence"]
    assert isinstance(records, dict)
    wfs = records["WFS"]
    assert isinstance(wfs, dict)
    high = wfs["high"]
    assert isinstance(high, dict)
    high["edof_ray_health"] = {"passed": False, "failures": [{"ray": 1}]}
    with pytest.raises(Task007ReviewError, match="ray-health"):
        review_task007_consolidated_payload(payload, _decisions())

    payload = _payload()
    records = payload["calibration_evidence"]
    assert isinstance(records, dict)
    rad = records["RAD"]
    assert isinstance(rad, dict)
    del rad["median"]
    with pytest.raises(Task007ReviewError, match="low/median/high"):
        review_task007_consolidated_payload(payload, _decisions())


def test_review_requires_complete_explicit_mechanism_decisions() -> None:
    payload = copy.deepcopy(_payload())
    with pytest.raises(Task007ReviewError, match="exactly one"):
        review_task007_consolidated_payload(payload, _decisions()[:-1])
    bad = (
        MechanismDecision("WFS", True, "ok"),
        MechanismDecision("RAD", False, "mechanism not preserved"),
        MechanismDecision("HOA", True, "ok"),
    )
    result = review_task007_consolidated_payload(payload, bad)
    assert result.all_mechanisms_passed is False
    assert result.tdd_999_cleared is False
