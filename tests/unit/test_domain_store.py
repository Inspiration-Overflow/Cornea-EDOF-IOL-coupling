from __future__ import annotations

import dataclasses
from dataclasses import replace
from pathlib import Path

import pytest

from whole_eye_mvp.domain import (
    CORNEA_LOCK_B0_555_V1,
    NOMINAL_MAIN_555_V1,
    ArtifactRecord,
    RunEnvironment,
    RunRecord,
    RunStatus,
    ScientificBaseline,
)
from whole_eye_mvp.store import (
    BaselineMismatch,
    EnvironmentConflict,
    LockedArtifactConflict,
    open_project_store,
)


@pytest.mark.unit
def test_settings_grids_and_optical_sampling_are_frozen_and_exact() -> None:
    assert len(CORNEA_LOCK_B0_555_V1.defocus_grid()) == 17
    assert CORNEA_LOCK_B0_555_V1.defocus_grid()[0] == 0.5
    assert CORNEA_LOCK_B0_555_V1.defocus_grid()[-1] == -3.5
    assert len(NOMINAL_MAIN_555_V1.defocus_grid()) == 15
    assert NOMINAL_MAIN_555_V1.defocus_grid()[-1] == -3.0
    assert NOMINAL_MAIN_555_V1.huygens_pupil_sampling == 128
    assert NOMINAL_MAIN_555_V1.huygens_image_sampling == 256
    assert NOMINAL_MAIN_555_V1.huygens_image_delta_um == 0.5
    assert NOMINAL_MAIN_555_V1.mtf_sample_frequencies_cpd == (10, 20, 30, 40, 50, 60)
    with pytest.raises(dataclasses.FrozenInstanceError):
        NOMINAL_MAIN_555_V1.wavelength_nm = 546.0  # type: ignore[misc]


@pytest.mark.unit
def test_project_round_trip_supports_spaces_unicode_and_full_baseline_hash() -> None:
    # pytest tmp_path is not needed here; this test is parameterized below by fixture injection.
    baseline = ScientificBaseline("MVP_2026_v1")
    assert len(baseline.base_specs) == 2
    assert len(baseline.cornea_specs) == 3
    assert len(baseline.platform_specs) == 3
    assert baseline.standard_eye_spec.eye_id == "STD_IOL_EYE_2024"


@pytest.mark.unit
def test_project_round_trip_path_and_baseline_content_mismatch(tmp_path: Path) -> None:
    baseline = ScientificBaseline("MVP_2026_v1")
    store = open_project_store(tmp_path / "项目 data", baseline)
    assert store.root.name == "项目 data"
    reopened = open_project_store(store.root, baseline)
    assert reopened.baseline.baseline_id == baseline.baseline_id

    modified = replace(
        baseline,
        iteration_limit=3,
    )
    with pytest.raises(BaselineMismatch, match="contents differ"):
        open_project_store(store.root, modified)


@pytest.mark.unit
def test_baseline_id_mismatch_does_not_rewrite_metadata(tmp_path: Path) -> None:
    first = ScientificBaseline("baseline-A")
    store = open_project_store(tmp_path / "project", first)
    before = store.metadata_path.read_text(encoding="utf-8")
    with pytest.raises(BaselineMismatch):
        open_project_store(store.root, ScientificBaseline("baseline-B"))
    assert store.metadata_path.read_text(encoding="utf-8") == before


@pytest.mark.unit
def test_locked_artifact_same_hash_is_noop_and_different_hash_conflicts(tmp_path: Path) -> None:
    baseline = ScientificBaseline("baseline")
    store = open_project_store(tmp_path / "project", baseline)
    source = tmp_path / "source.txt"
    source.write_text("alpha", encoding="utf-8")
    record = ArtifactRecord("A0", "asset", "models/assets/A0.txt", baseline.baseline_id)
    first = store.record_artifact(source, record, lock=True)
    second = store.record_artifact(source, record, lock=True)
    assert second == first
    assert store.find_artifact("A0") == first
    assert store.find_artifact("missing") is None
    source.write_text("beta", encoding="utf-8")
    with pytest.raises(LockedArtifactConflict):
        store.record_artifact(source, record, lock=True)
    assert store.verify_artifact(first)


@pytest.mark.unit
def test_run_environment_requires_all_provenance_fields_and_is_create_once(tmp_path: Path) -> None:
    valid = RunEnvironment("0.1.0", "2026 R1", "b", "s", "m", "l")
    valid.validate()
    with pytest.raises(ValueError, match="manifest_hash"):
        RunEnvironment("0.1.0", "2026 R1", "b", "s", "", "l").validate()

    store = open_project_store(tmp_path / "project", ScientificBaseline("b"))
    ref = store.record_environment("run-1", valid)
    assert ref == "environments/run-1.json"
    assert store.record_environment("run-1", valid) == ref
    with pytest.raises(EnvironmentConflict):
        store.record_environment("run-1", replace(valid, manifest_hash="different"))


@pytest.mark.unit
def test_run_history_is_append_only(tmp_path: Path) -> None:
    store = open_project_store(tmp_path / "p", ScientificBaseline("b"))
    store.append_run(RunRecord("r1", "build", "all", RunStatus.COMPLETED, "t0", "t1"))
    store.append_run(
        RunRecord("r2", "build", "all", RunStatus.FAILED, "t2", "t3", "E", "bad")
    )
    text = store.run_history_path.read_text(encoding="utf-8")
    assert "r1" in text and "r2" in text
