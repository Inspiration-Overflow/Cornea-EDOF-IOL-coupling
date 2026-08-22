from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "run_model_revision_r8_96.py"
)


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_model_revision_r8_96", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


r8 = _load_runner()


def _valid_evidence(plan):
    carrier_ids = {row.carrier_id for row in plan}
    model_keys = {row.model_artifact_key for row in plan}
    return {
        "schema_version": 1,
        "formal_artifact": False,
        "pilot": False,
        "phase": r8.R6_R7_PHASE,
        "r5_freeze_id": r8.R5_2_FREEZE_ID,
        "r5_2_hoa_a6_rule": {
            "id": r8.R5_2_FREEZE_ID,
            "zone_order": [1, 2],
            "gate_feedback_used": False,
            "optimizer_used": False,
        },
        "contract": {
            "carrier_count": r8.R6_EXPECTED_CARRIER_COUNT,
            "r5_2_hoa_q_ant_required": 0.0,
            "automatic_power_specific_refit_allowed": False,
            "mtf_used_in_mechanism_fit": False,
        },
        "carriers": {carrier_id: {} for carrier_id in carrier_ids},
        "local_checks": {
            key: True for key in r8.REQUIRED_R6_R7_LOCAL_CHECKS
        },
        "artifact_sha256": {key: "a" * 64 for key in model_keys},
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
    }


def test_r8_plan_is_exact_96_config_48_pair_1440_row_factorial() -> None:
    plan = r8.build_r8_plan()
    assert len(plan) == r8.R8_EXPECTED_CONFIG_COUNT == 96
    assert len({row.carrier_id for row in plan}) == r8.R6_EXPECTED_CARRIER_COUNT == 24
    assert len({row.pair_key for row in plan}) == r8.R8_EXPECTED_PAIR_COUNT == 48
    assert len(r8.focus_grid_d()) == 15
    assert len(plan) * len(r8.focus_grid_d()) == 1440
    assert r8.focus_grid_d()[0] == pytest.approx(0.50)
    assert r8.focus_grid_d()[-1] == pytest.approx(-3.00)
    assert 0.0 in r8.focus_grid_d()


def test_r8_pairs_share_exact_carrier_and_use_canonical_pair_keys() -> None:
    plan = r8.build_r8_plan()
    by_pair = {}
    for row in plan:
        by_pair.setdefault(row.pair_key, []).append(row)
    assert len(by_pair) == 48
    for pair_key, rows in by_pair.items():
        assert {row.optic_state for row in rows} == set(r8._state_values())
        assert len({row.carrier_id for row in rows}) == 1
        assert len({row.base_id for row in rows}) == 1
        assert len({row.cornea_id for row in rows}) == 1
        assert len({row.platform_id for row in rows}) == 1
        assert len({row.pupil_mm for row in rows}) == 1
        row = rows[0]
        assert pair_key == f"{row.carrier_id}_EPD{row.pupil_mm:g}"


def test_r8_plan_uses_only_r6_serialized_mono_edof_models() -> None:
    plan = r8.build_r8_plan()
    model_keys = {row.model_artifact_key for row in plan}
    assert len(model_keys) == r8.R8_EXPECTED_MODEL_COUNT == 48
    assert all(key.startswith("validated/R6_") for key in model_keys)
    assert all(
        key.endswith(("/ACTUAL_BINARY4_MONO.zmx", "/ACTUAL_BINARY4_EDOF.zmx"))
        for key in model_keys
    )


def test_r8_contract_reports_direct_adapter_available_and_keeps_authorization() -> None:
    summary = r8.r8_contract_summary(r8.build_r8_plan())
    assert summary["r5_freeze_id"] == r8.R5_2_FREEZE_ID
    assert summary["direct_model_adapter_implemented"] is True
    assert summary["execution_ready_after_preflight"] is True
    assert summary["missing_prerequisite_id"] is None
    with pytest.raises(r8.R8AuthorizationError):
        r8.validate_execution_authorization(None)
    with pytest.raises(r8.R8AuthorizationError):
        r8.validate_execution_authorization("wrong-task")
    r8.validate_execution_authorization(r8.R8_AUTHORIZATION_ID)


def test_r8_r6_r7_evidence_validator_accepts_exact_frozen_input_contract() -> None:
    plan = r8.build_r8_plan()
    payload = _valid_evidence(plan)
    hashes = r8.validate_r6_r7_evidence_payload(payload, plan)
    assert len(hashes) == 48
    assert set(hashes) == {row.model_artifact_key for row in plan}


def test_r8_r6_r7_evidence_validator_rejects_freeze_or_artifact_drift() -> None:
    plan = r8.build_r8_plan()
    wrong_freeze = _valid_evidence(plan)
    wrong_freeze["r5_freeze_id"] = "R5.1"
    with pytest.raises(r8.R8PlanError, match="identity mismatch"):
        r8.validate_r6_r7_evidence_payload(wrong_freeze, plan)

    missing_model = _valid_evidence(plan)
    model_key = next(iter(missing_model["artifact_sha256"]))
    del missing_model["artifact_sha256"][model_key]
    with pytest.raises(r8.R8PlanError, match="valid model SHA-256"):
        r8.validate_r6_r7_evidence_payload(missing_model, plan)


def test_r8_model_file_hash_verification_is_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / r8.R6_R7_OUTPUT_RELATIVE
    relative = "validated/R6_FAKE/ACTUAL_BINARY4_MONO.zmx"
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"serialized-model")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    r8.verify_r6_r7_model_files(tmp_path, {relative: digest})
    with pytest.raises(r8.R8PlanError, match="hash mismatch"):
        r8.verify_r6_r7_model_files(tmp_path, {relative: "0" * 64})


def test_r8_expected_outputs_are_structured() -> None:
    paths = r8.expected_r8_artifact_paths()
    assert len(paths) == 4
    assert paths[0].endswith(r8.R8_EVIDENCE_NAME)
