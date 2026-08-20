from __future__ import annotations

import json
from pathlib import Path

import pytest

from whole_eye_mvp.analysis_zos_pair_scale import (
    EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
    PAIR_MONO_FREQUENCY_SCALE_MODE,
    TASK009_PAIR_MONO_MTF_ACQUISITION,
)
from whole_eye_mvp.domain import NOMINAL_MAIN_FFT_MTF_555_V2
from whole_eye_mvp.quality import assert_trace_coverage

ACTIVE_SPEC_FILES = (
    Path("docs/URD.md"),
    Path("docs/ADD.md"),
    Path("docs/MDD.md"),
    Path("docs/TDD.md"),
    Path("docs/RMD.md"),
    Path("docs/RMD_EXECUTION_STATUS.md"),
    Path("docs/TASK_009_PRODUCTION_SAMPLING_LOCK_2026-08-19.md"),
)
SAMPLING_LOCK = Path("docs/evidence/task009/TASK_009_PRODUCTION_SAMPLING_LOCK.json")
RUN72_CLEARANCE = Path("docs/evidence/task009/TASK_009_RUN72_WEB_CLEARANCE.json")

FORBIDDEN_ACTIVE_TOKENS = (
    "huygens",
    "complex otf",
    "complex_otf",
    "psf_to_complex_otf",
    "vsotf",
    "vsmtf",
    "zosfftmtfanalysisbackend",
)
FORBIDDEN_RUNTIME_TOKENS = (
    "new_fftmtf",
    "zosfftmtfanalysisbackend",
)


@pytest.mark.unit
def test_active_main_analysis_settings_and_acquisition_contract() -> None:
    settings = NOMINAL_MAIN_FFT_MTF_555_V2
    settings.validate()
    assert settings.settings_id == "NOMINAL_MAIN_FFT_MTF_555_v2"
    assert settings.wavelength_nm == 555.0
    assert settings.pupils_mm == (3.0, 5.0)
    assert settings.defocus_grid() == tuple(
        round(0.5 - 0.25 * index, 10) for index in range(15)
    )
    assert settings.fft_mtf_sampling == 128
    assert settings.fft_mtf_convergence_samplings == (64, 128, 256)
    assert settings.mtfa_max_cpd == 60.0
    assert settings.mtf_frequency_step_cpd == 1.0
    assert settings.mtf_sample_frequencies_cpd == (10.0, 20.0, 30.0, 40.0, 50.0, 60.0)
    assert not hasattr(settings, "dof_relative_fraction")
    assert not hasattr(settings, "b0_q_lock_max_cycles_per_mm")

    contract = TASK009_PAIR_MONO_MTF_ACQUISITION
    assert contract.contract_id == "TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2"
    assert contract.production_operand == "MTFA"
    assert contract.grid == 1
    assert contract.data_type == 0
    assert contract.wavelength_number == 1
    assert contract.field_number == 1
    assert contract.frequency_axis == "direct_0_to_60_cpd_via_paired_MONO_EFFL"
    assert contract.contract_hash == EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH
    assert EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH == (
        "f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d"
    )
    assert PAIR_MONO_FREQUENCY_SCALE_MODE == "paired_residual_free_MONO_EFFL"


@pytest.mark.unit
def test_formal_task009_sampling_lock_matches_active_contract_and_evidence() -> None:
    payload = json.loads(SAMPLING_LOCK.read_text(encoding="utf-8"))
    assert payload["lock_id"] == "TASK009_PRODUCTION_SAMPLING_LOCK_v1"
    assert payload["formal_artifact"] is True
    assert payload["selection_locked"] is True
    assert payload["production_sampling_locked"] is True
    assert payload["production_sampling"] == 128
    assert payload["convergence_samplings"] == [64, 128, 256]
    assert payload["analysis_settings_id"] == NOMINAL_MAIN_FFT_MTF_555_V2.settings_id
    assert payload["analysis_settings_sha256"] == (
        "0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc"
    )
    assert payload["acquisition_contract_id"] == TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id
    assert payload["acquisition_contract_sha256"] == EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH
    assert payload["frequency_scale_mode"] == PAIR_MONO_FREQUENCY_SCALE_MODE
    assert payload["representative_run_code_commit"] == (
        "d80b3a1c33fce02deda50f5ce8ebc73326e5b946"
    )
    assert payload["evidence_commit"] == "47f901dad36fb9d407826a6da8baceeef4c2edfd"
    assert payload["evidence_json_sha256"] == (
        "404502231e154ebae0813c6b52151961ad4278bef8cc4d29f412d21db7bc8d49"
    )
    assert payload["through_focus_csv_sha256"] == (
        "e51e524ee1eb009a1e2ae8cd56cc0bc101aa3dda052fe14dfba585d583987006"
    )
    assert payload["through_focus_rows"] == 90
    assert payload["all_convergence_passed"] is True
    assert payload["all_repeatability_passed"] is True
    assert payload["all_six_config_integration_passed"] is True
    assert payload["crosscheck_web_review"] == "PASS"
    assert payload["sampling_escalation_256_active"] is False
    assert payload["run72_started"] is False
    # Sampling lock remains an immutable method decision snapshot; Run72 engineering
    # authorization is represented by a separate clearance artifact below.
    assert payload["run72_authorized"] is False


@pytest.mark.unit
def test_run72_web_clearance_requires_hardened_provenance_and_no_repeat_probe() -> None:
    payload = json.loads(RUN72_CLEARANCE.read_text(encoding="utf-8"))
    assert payload["clearance_id"] == "TASK009_RUN72_WEB_CLEARANCE_v1"
    assert payload["gate_artifact"] is True
    assert payload["formal_scientific_lock"] is False
    assert payload["source_sampling_lock_id"] == "TASK009_PRODUCTION_SAMPLING_LOCK_v1"
    assert payload["production_sampling"] == 128
    assert payload["production_sampling_locked"] is True
    assert payload["analysis_settings_id"] == NOMINAL_MAIN_FFT_MTF_555_V2.settings_id
    assert payload["acquisition_contract_id"] == TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id
    assert payload["acquisition_contract_sha256"] == EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH
    assert payload["frequency_scale_mode"] == PAIR_MONO_FREQUENCY_SCALE_MODE
    assert payload["run_environment_provenance_hardened"] is True
    assert payload["backend_provenance_fail_closed"] is True
    assert payload["active_specs_synchronized"] is True
    assert payload["as_fft_mtf_production_retired"] is True
    assert payload["per_state_effl_production_scale_forbidden"] is True
    assert payload["sampling_escalation_256_active"] is False
    assert payload["no_additional_representative_opticstudio_rerun_required"] is True
    assert payload["web_gate_ci_pytest_passed"] == 199
    assert payload["web_gate_ci_ruff"] == "PASS"
    assert payload["web_gate_ci_compileall"] == "PASS"
    assert payload["web_gate_ci_uv_lock"] == "PASS"
    assert payload["run72_authorized"] is True
    assert payload["run72_started"] is False
    assert payload["task009_complete"] is True
    assert payload["task010_gui_required_before_cli_run72"] is False


def _scan(paths, tokens=FORBIDDEN_ACTIVE_TOKENS) -> list[str]:
    findings: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8").casefold()
        for token in tokens:
            if token in text:
                findings.append(f"{path}:{token}")
    return findings


@pytest.mark.unit
def test_production_source_does_not_reintroduce_removed_paths() -> None:
    paths = tuple(Path("src/whole_eye_mvp").rglob("*.py"))
    findings = _scan(paths)
    findings += _scan(paths, FORBIDDEN_RUNTIME_TOKENS)
    assert not findings, "removed analysis path leaked into production source: " + ", ".join(findings)


@pytest.mark.unit
def test_active_scripts_do_not_reintroduce_removed_paths() -> None:
    paths = tuple(Path("scripts").glob("*task_009*.py")) + tuple(Path("scripts").glob("*run72*.py"))
    findings = _scan(paths)
    findings += _scan(paths, FORBIDDEN_RUNTIME_TOKENS)
    assert not findings, "removed analysis path leaked into active scripts: " + ", ".join(findings)


@pytest.mark.unit
def test_active_specs_do_not_reintroduce_removed_paths() -> None:
    findings = _scan(ACTIVE_SPEC_FILES)
    assert not findings, "removed analysis path leaked into active specs: " + ", ".join(findings)
    for path in ACTIVE_SPEC_FILES[:6]:
        text = path.read_text(encoding="utf-8")
        assert "TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2" in text
        assert "paired_residual_free_MONO_EFFL" in text


@pytest.mark.unit
def test_current_trace_map_covers_the_current_document_id_universe() -> None:
    trace = Path("docs/TRACE.md").read_text(encoding="utf-8")
    assert_trace_coverage(trace)
    assert "URD-0001 v1.6" in trace
    assert "ADD-0001 v1.6" in trace
    assert "MDD-0001 v1.5" in trace
    assert "TDD-0001 v1.6" in trace
