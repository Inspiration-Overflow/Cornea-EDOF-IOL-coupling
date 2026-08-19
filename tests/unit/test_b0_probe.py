from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from whole_eye_mvp.b0_probe import B0ProbeEvidenceError, validate_b0_probe_payload
from whole_eye_mvp.domain import CORNEA_LOCK_B0_555_V2


def payload(*, legacy: bool = False) -> dict[str, object]:
    result: dict[str, object] = {
        "settings": asdict(CORNEA_LOCK_B0_555_V2),
        "sampling_results": {"2": {}, "3": {}, "4": {}},
        "frequency_step_results": {"5": {}, "2.5": {}},
        "summary": {
            "max_abs_q_difference_sampling_2_to_3": 0.0022,
            "max_abs_q_difference_sampling_3_to_4": 0.00068,
            "max_abs_q_difference_frequency_5_to_2_5": 0.0049,
        },
    }
    result["passed" if legacy else "runtime_passed"] = True
    return result


def json_roundtrip(value: dict[str, object]) -> dict[str, object]:
    result = json.loads(json.dumps(value))
    assert isinstance(result, dict)
    return result


@pytest.mark.unit
def test_probe_evidence_accepts_current_and_legacy_runtime_success_semantics() -> None:
    current = validate_b0_probe_payload(payload())
    legacy = validate_b0_probe_payload(json_roundtrip(payload(legacy=True)))
    assert current.runtime_passed and legacy.runtime_passed
    assert current.max_abs_q_difference_sampling_3_to_4 == pytest.approx(0.00068)


@pytest.mark.unit
def test_probe_evidence_accepts_disk_json_tuple_to_list_roundtrip() -> None:
    evidence = validate_b0_probe_payload(json_roundtrip(payload()))
    assert evidence.runtime_passed
    assert evidence.max_abs_q_difference_frequency_5_to_2_5 == pytest.approx(0.0049)


@pytest.mark.unit
def test_probe_evidence_requires_exact_v2_settings_and_full_probe_grid() -> None:
    wrong = payload()
    wrong["settings"] = {**asdict(CORNEA_LOCK_B0_555_V2), "mtfa_sampling": 4}
    with pytest.raises(B0ProbeEvidenceError, match="settings"):
        validate_b0_probe_payload(wrong)

    missing_sampling = payload()
    missing_sampling["sampling_results"] = {"2": {}, "3": {}}
    with pytest.raises(B0ProbeEvidenceError, match="Samp=2/3/4"):
        validate_b0_probe_payload(missing_sampling)


@pytest.mark.unit
def test_probe_evidence_does_not_turn_summary_differences_into_an_automatic_gate() -> None:
    evidence_payload = payload()
    evidence_payload["summary"] = {
        "max_abs_q_difference_sampling_2_to_3": 0.5,
        "max_abs_q_difference_sampling_3_to_4": 0.4,
        "max_abs_q_difference_frequency_5_to_2_5": 0.3,
    }
    evidence = validate_b0_probe_payload(evidence_payload)
    assert evidence.runtime_passed
    assert evidence.max_abs_q_difference_sampling_2_to_3 == pytest.approx(0.5)
