from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp.extension96_analysis import (
    SOURCE_FILES,
    Task015Error,
    analyze_extension96,
    verify_source_blobs,
)

TASK013_DIR = Path("docs/evidence/task013")
TASK014_DIR = Path("docs/evidence/task014")


@pytest.mark.unit
def test_task015_source_git_blobs_are_exact() -> None:
    observed = verify_source_blobs(TASK013_DIR, TASK014_DIR)
    assert len(observed) == 10
    for task_name in ("task013", "task014"):
        for filename, expected in SOURCE_FILES[task_name].values():
            assert observed[f"{task_name}/{filename}"] == expected


@pytest.mark.unit
def test_task015_integrates_exact_96_config_layer() -> None:
    analysis = analyze_extension96(TASK013_DIR, TASK014_DIR)
    assert len(analysis.pairs) == 48
    assert len(analysis.n0_interactions) == 288
    assert len(analysis.coupling_matrix) == 12

    statuses = [pair.dof50_effect_status for pair in analysis.pairs]
    assert statuses.count("exact") == 43
    assert statuses.count("lower_bound") == 5
    assert statuses.count("upper_bound") == 0
    assert statuses.count("indeterminate") == 0
    assert sum(pair.pair_peak_censored for pair in analysis.pairs) == 10


@pytest.mark.unit
def test_task015_preserves_tradeoff_signal() -> None:
    analysis = analyze_extension96(TASK013_DIR, TASK014_DIR)
    assert sum(pair.values["delta_tf_mtfa_mean"] < 0 for pair in analysis.pairs) == 48
    assert sum(pair.values["delta_mtfa_at_zero_d"] < 0 for pair in analysis.pairs) == 47
    assert sum(pair.values["delta_mtfa_at_zero_d"] > 0 for pair in analysis.pairs) == 1


@pytest.mark.unit
def test_task015_n0_interaction_is_difference_in_differences() -> None:
    analysis = analyze_extension96(TASK013_DIR, TASK014_DIR)
    row = next(
        item
        for item in analysis.n0_interactions
        if item["base_id"] == "LB_AL2395"
        and item["cornea_id"] == "B0V12"
        and item["platform_id"] == "WFS"
        and item["pupil_mm"] == 3.0
        and item["outcome"] == "delta_dof50_width_d"
    )
    assert row["contrast_type"] == "postop_minus_N0_edof_effect"
    assert row["bound_status"] == "lower_bound"
    assert row["lower_bound"] != ""
    assert row["upper_bound"] == ""


@pytest.mark.unit
def test_task015_rejects_missing_accepted_source(tmp_path: Path) -> None:
    with pytest.raises(Task015Error, match="missing accepted source file"):
        verify_source_blobs(tmp_path / "task013", tmp_path / "task014")
