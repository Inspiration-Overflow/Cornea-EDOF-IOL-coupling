from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from whole_eye_mvp.run72_analysis import (
    PLATFORM_LABELS,
    TASK011_RECORDED_EXPORT_HASHES,
    TASK012_REPOSITORY_HASHES,
    TASK012_SOURCE_HASHES,
    ConfigSummary,
    FactorKey,
    NumericBound,
    Task012Error,
    analyze_evidence,
    build_pairs,
    dof50_effect_status,
    load_config_summaries,
    validate_evidence_metadata,
    verify_source_hashes,
)

EVIDENCE_DIR = Path("docs/evidence/task011")
CONFIG_CSV = EVIDENCE_DIR / "TASK_011_RUN72_CONFIG_RESULTS.csv"
EVIDENCE_JSON = EVIDENCE_DIR / "TASK_011_RUN72_EVIDENCE.json"


def _config(*, censored: bool, state: str) -> ConfigSummary:
    return ConfigSummary(
        run_id="run",
        config_id=f"cfg-{state}",
        pair_key="pair",
        carrier_id="carrier",
        factors=FactorKey("LB_AL2395", "A0", "WFS", 3.0),
        optic_state=state,
        distance_peak_retina_d=0.0,
        distance_peak_mtfa=0.5,
        mtfa_at_zero_d=0.5,
        dof50_width_d=1.0,
        dof50_far_censored=censored,
        dof50_near_censored=False,
        tf_mtfa_mean=0.2,
        peak_search_censored=False,
        c40_um=0.0,
        c60_um=0.0,
        hoa_rms_um=0.0,
    )


@pytest.mark.unit
def test_task012_repository_source_hashes_are_exact() -> None:
    assert TASK012_SOURCE_HASHES is TASK012_REPOSITORY_HASHES
    assert verify_source_hashes(EVIDENCE_DIR) == TASK012_REPOSITORY_HASHES
    assert TASK012_REPOSITORY_HASHES["TASK_011_RUN72_CONFIG_RESULTS.csv"] != (
        TASK011_RECORDED_EXPORT_HASHES["TASK_011_RUN72_CONFIG_RESULTS.csv"]
    )


@pytest.mark.unit
def test_task012_reconstructs_formal_run72_and_censoring() -> None:
    analysis = analyze_evidence(EVIDENCE_DIR)
    assert len(analysis.pairs) == 36
    assert len(analysis.contrasts) == 1152
    assert len(analysis.coupling_matrix) == 9

    statuses = [pair.dof50_effect_status for pair in analysis.pairs]
    assert statuses.count("exact") == 31
    assert statuses.count("lower_bound") == 5
    assert statuses.count("upper_bound") == 0
    assert statuses.count("indeterminate") == 0
    assert sum(pair.pair_peak_censored for pair in analysis.pairs) == 8


@pytest.mark.unit
def test_task012_evidence_metadata_fails_closed_on_tamper(tmp_path: Path) -> None:
    payload = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8"))
    payload["code_commit"] = "0" * 40
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Task012Error, match="metadata mismatch"):
        validate_evidence_metadata(path)


@pytest.mark.unit
def test_task012_dof50_effect_status_truth_table() -> None:
    mono_exact = _config(censored=False, state="MONO")
    mono_lower = _config(censored=True, state="MONO")
    edof_exact = _config(censored=False, state="EDOF")
    edof_lower = _config(censored=True, state="EDOF")

    assert dof50_effect_status(mono_exact, edof_exact) == "exact"
    assert dof50_effect_status(mono_exact, edof_lower) == "lower_bound"
    assert dof50_effect_status(mono_lower, edof_exact) == "upper_bound"
    assert dof50_effect_status(mono_lower, edof_lower) == "indeterminate"


@pytest.mark.unit
def test_task012_numeric_bound_propagates_signed_contrasts() -> None:
    lower = NumericBound.from_status(0.4, "lower_bound")
    exact = NumericBound.from_status(0.1, "exact")
    result = lower.add(exact.scaled(-1.0))
    assert result.status() == "lower_bound"
    assert result.lower == pytest.approx(0.3)

    upper = NumericBound.from_status(0.4, "upper_bound")
    result = upper.add(exact.scaled(-1.0))
    assert result.status() == "upper_bound"
    assert result.upper == pytest.approx(0.3)


@pytest.mark.unit
def test_task012_formal_contrast_and_matrix_keep_censor_semantics() -> None:
    analysis = analyze_evidence(EVIDENCE_DIR)
    dof_rows = [
        row for row in analysis.contrasts if row["outcome"] == "delta_dof50_width_d"
    ]
    assert any(row["bound_status"] != "exact" for row in dof_rows)
    non_dof = next(
        row for row in analysis.contrasts if row["outcome"] == "delta_mtfa_at_zero_d"
    )
    assert non_dof["bound_status"] == "not_applicable"

    b0_wfs = next(
        row
        for row in analysis.coupling_matrix
        if row["cornea_id"] == "B0" and row["platform_id"] == "WFS"
    )
    assert b0_wfs["dof50_censored_count"] == 2
    assert b0_wfs["dof50_mean_bound_status"] == "lower_bound"
    assert b0_wfs["dof50_mean_lower_bound"] != ""

    a0_rad = next(
        row
        for row in analysis.coupling_matrix
        if row["cornea_id"] == "A0" and row["platform_id"] == "RAD"
    )
    assert a0_rad["dof50_censored_count"] == 0
    assert a0_rad["dof50_mean_bound_status"] == "exact"


@pytest.mark.unit
def test_task012_reporting_labels_do_not_replace_raw_platform_ids() -> None:
    analysis = analyze_evidence(EVIDENCE_DIR)
    row = analysis.pairs[0].to_row()
    assert row["platform_id"] in PLATFORM_LABELS
    assert row["platform_label"] == PLATFORM_LABELS[row["platform_id"]]
    assert row["platform_id"] != row["platform_label"]


@pytest.mark.unit
def test_task012_pairing_uses_explicit_factor_columns() -> None:
    configs = list(load_config_summaries(CONFIG_CSV))
    target_index = next(
        index
        for index, config in enumerate(configs)
        if config.optic_state == "EDOF" and config.factors.base_id == "LB_AL2395"
    )
    target = configs[target_index]
    configs[target_index] = replace(
        target,
        factors=replace(target.factors, pupil_mm=5.0 if target.factors.pupil_mm == 3.0 else 3.0),
    )
    with pytest.raises(Task012Error, match="explicit factor columns differ"):
        build_pairs(configs)


@pytest.mark.unit
def test_task012_duplicate_config_id_fails_closed(tmp_path: Path) -> None:
    source = CONFIG_CSV.read_text(encoding="utf-8").splitlines()
    duplicate = source[:]
    duplicate[2] = duplicate[1]
    path = tmp_path / "duplicate.csv"
    path.write_text("\n".join(duplicate) + "\n", encoding="utf-8")
    with pytest.raises(Task012Error, match="duplicate or empty config_id"):
        load_config_summaries(path)
