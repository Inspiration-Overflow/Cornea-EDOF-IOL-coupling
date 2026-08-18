from __future__ import annotations

import csv
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from whole_eye_mvp.analysis import (
    AberrationSummary,
    ConfigArtifacts,
    ConfigResult,
    with_shape_axis,
)
from whole_eye_mvp.carriers import (
    ProvisionalCarrier,
    ResidualCalibration,
    ResidualDefinition,
    ResidualValidationPolicy,
    ScientificInvariantError,
    expected_calibration_carriers,
    expected_carrier_keys,
)
from whole_eye_mvp.domain import NOMINAL_MAIN_555_V1, PlatformId, RunEnvironment, ScientificBaseline
from whole_eye_mvp.manifest import build_manifests, compute_lock_set_hash
from whole_eye_mvp.store import PROJECT_SCHEMA_VERSION, ProjectStoreError, open_project_store
from whole_eye_mvp.workflows import (
    export_manifest_bundle,
    finalize_carrier_locks,
    rerun_failed,
    run_analysis_batch,
)

POLICY = ResidualValidationPolicy("TEST_POLICY_v1", 0.01, 0.05)


def carrier(key, index: int) -> ProvisionalCarrier:
    target = {PlatformId.WFS: -0.20, PlatformId.RAD: -0.27, PlatformId.HOA: 0.0}[
        key.platform_id
    ]
    power = 18.0 + index * 0.25
    return ProvisionalCarrier(key, power, -0.2, power, 12, -12, 1, "IOL", 4.5, target)


def carriers() -> list[ProvisionalCarrier]:
    return [carrier(key, index) for index, key in enumerate(expected_carrier_keys())]


def _file(tmp_path: Path, name: str, text: str) -> tuple[str, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path), hashlib.sha256(path.read_bytes()).hexdigest()


def residual(tmp_path: Path, platform: str, all_carriers: list[ProvisionalCarrier]) -> ResidualDefinition:
    payload_ref, payload_sha = _file(tmp_path, f"{platform}.dat", "0.0\n")
    validation_ref, validation_sha = _file(tmp_path, f"{platform}-validation.json", "{}")
    selected = expected_calibration_carriers(all_carriers, platform)
    calibrations = []
    for label, target in selected.items():
        evidence_ref, evidence_sha = _file(
            tmp_path,
            f"{platform}-{label}.json",
            target.key.carrier_id,
        )
        calibrations.append(
            ResidualCalibration(
                label,
                target.key.carrier_id,
                target.power_d,
                True,
                0.05,
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
        (0, 3),
        True,
        True,
        payload_sha,
        0.0,
        0.0,
        validation_ref,
        validation_sha,
        tuple(calibrations),
    )


def formal_bundle(tmp_path: Path):
    all_carriers = carriers()
    residuals = [residual(tmp_path, platform, all_carriers) for platform in ("WFS", "RAD", "HOA")]
    deltas = {carrier.key.carrier_id: 0.1 for carrier in all_carriers}
    locks = finalize_carrier_locks(
        all_carriers,
        residuals,
        deltas,
        residual_policy=POLICY,
    )
    return build_manifests(locks)


@pytest.mark.unit
def test_formal_locks_require_all_evidence_gates_and_delta_f_map(tmp_path: Path) -> None:
    all_carriers = carriers()
    residuals = [residual(tmp_path, platform, all_carriers) for platform in ("WFS", "RAD", "HOA")]
    deltas = {carrier.key.carrier_id: 0.1 for carrier in all_carriers}
    locks = finalize_carrier_locks(
        all_carriers,
        residuals,
        deltas,
        residual_policy=POLICY,
    )
    assert len(locks) == 18
    assert len({lock.lock_hash for lock in locks}) == 18
    with pytest.raises(ScientificInvariantError, match="delta-F"):
        finalize_carrier_locks(
            all_carriers,
            residuals,
            {},
            residual_policy=POLICY,
        )
    with pytest.raises(ScientificInvariantError, match="residuals"):
        finalize_carrier_locks(
            all_carriers,
            residuals[:-1],
            deltas,
            residual_policy=POLICY,
        )

    forged = replace(
        residuals[0],
        measured_piston_um=None,
        measured_global_defocus_d=None,
        validation_evidence_ref="",
        validation_evidence_sha256="",
    )
    with pytest.raises(ScientificInvariantError, match="residuals"):
        finalize_carrier_locks(
            all_carriers,
            [forged, *residuals[1:]],
            deltas,
            residual_policy=POLICY,
        )


@pytest.mark.unit
def test_export_manifest_writes_versioned_exact_18_and_72_csv_rows(tmp_path: Path) -> None:
    bundle = formal_bundle(tmp_path)
    paths = export_manifest_bundle(bundle, tmp_path / "manifest")
    with open(paths.physical_carriers_csv, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        assert len(rows) == 18
        assert {row["schema_version"] for row in rows} == {str(PROJECT_SCHEMA_VERSION)}
    with open(paths.nominal_72_csv, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        assert len(rows) == 72
        assert len({row["config_id"] for row in rows}) == 72
        assert {row["schema_version"] for row in rows} == {str(PROJECT_SCHEMA_VERSION)}
        assert all(row["carrier_lock_hash"] for row in rows)
    assert Path(paths.manifest_hash_file).read_text(encoding="utf-8").strip() == bundle.manifest_hash


def fake_result(config, output: Path, run_id: str) -> ConfigResult:
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in ("model.zos", "through_focus.csv", "tf.png", "mtf.png", "p1.png", "p2.png", "p3.png"):
        path = output / name
        path.write_text("x", encoding="utf-8")
        paths.append(str(path))
    defocus = NOMINAL_MAIN_555_V1.defocus_grid()
    vsotf = tuple(max(0.05, 1 - abs(index - 2) * 0.15) for index in range(len(defocus)))
    mtfa = tuple(value * 0.7 for value in vsotf)
    columns = [tuple(value for value in vsotf) for _ in range(6)]
    rows = with_shape_axis(defocus, mtfa, vsotf, columns)
    return ConfigResult(
        config,
        run_id,
        rows,
        0.0,
        AberrationSummary(0.1, 0.02, 0.1),
        5,
        3,
        5,
        6,
        "h",
        "h",
        23.95,
        23.95,
        4.5,
        4.5,
        4.5,
        4.5,
        False,
        ConfigArtifacts(paths[0], paths[1], paths[2], paths[3], tuple(paths[4:])),
        True,
    )


class FakeBackend:
    def __init__(self, fail_id=None, *, wrong_identity: bool = False):
        self.fail_id = fail_id
        self.wrong_identity = wrong_identity
        self.called: list[str] = []

    def run_config(self, config, output_dir, run_id):
        self.called.append(config.config_id)
        if config.config_id == self.fail_id:
            raise RuntimeError("injected export failure")
        result = fake_result(config, output_dir, run_id)
        if self.wrong_identity:
            return replace(result, run_id="WRONG-RUN")
        return result


def environment(baseline_id: str, bundle) -> RunEnvironment:
    return RunEnvironment(
        "0.1.0",
        "2026 R1",
        baseline_id,
        NOMINAL_MAIN_555_V1.settings_id,
        bundle.manifest_hash,
        compute_lock_set_hash(bundle.physical_carriers),
    )


@pytest.mark.unit
def test_analysis_batch_isolates_failure_records_provenance_and_reruns_only_failed(tmp_path: Path) -> None:
    bundle = formal_bundle(tmp_path / "science")
    selected = bundle.nominal_configs[:3]
    store = open_project_store(tmp_path / "project", ScientificBaseline("baseline"))
    env = environment("baseline", bundle)
    backend = FakeBackend(fail_id=selected[1].config_id)
    first = run_analysis_batch(
        backend,
        bundle,
        store.root / "results",
        store=store,
        environment=env,
        selection=[config.config_id for config in selected],
    )
    assert len(first.completed) == 2 and len(first.failed) == 1
    assert first.environment_ref.startswith("environments/")
    history = store.run_history_path.read_text(encoding="utf-8")
    assert first.run_id in history and "completed" in history and "failed" in history
    artifact_index = store.artifact_index_path.read_text(encoding="utf-8")
    assert "config_result.json" in artifact_index
    assert "through_focus.csv" in artifact_index

    rerun_backend = FakeBackend()
    second = rerun_failed(
        rerun_backend,
        bundle,
        first,
        store.root / "results",
        store=store,
        environment=env,
    )
    assert second.run_id != first.run_id
    assert rerun_backend.called == [selected[1].config_id]
    assert len(second.completed) == 1 and not second.failed


@pytest.mark.unit
def test_analysis_batch_rejects_backend_result_with_wrong_run_identity(tmp_path: Path) -> None:
    bundle = formal_bundle(tmp_path / "science")
    selected = bundle.nominal_configs[:1]
    store = open_project_store(tmp_path / "project", ScientificBaseline("baseline"))
    summary = run_analysis_batch(
        FakeBackend(wrong_identity=True),
        bundle,
        store.root / "results",
        store=store,
        environment=environment("baseline", bundle),
        selection=[selected[0].config_id],
    )
    assert not summary.completed
    assert len(summary.failed) == 1
    assert "wrong run_id" in (summary.failed[0].error_message or "")


@pytest.mark.unit
def test_analysis_environment_must_match_manifest_lock_set_settings_and_project_output(
    tmp_path: Path,
) -> None:
    bundle = formal_bundle(tmp_path / "science")
    store = open_project_store(tmp_path / "project", ScientificBaseline("baseline"))
    good = environment("baseline", bundle)
    selected = [bundle.nominal_configs[0].config_id]

    with pytest.raises(ProjectStoreError, match="manifest hash"):
        run_analysis_batch(
            FakeBackend(),
            bundle,
            store.root / "results",
            store=store,
            environment=replace(good, manifest_hash="wrong"),
            selection=selected,
        )
    with pytest.raises(ProjectStoreError, match="lock-set"):
        run_analysis_batch(
            FakeBackend(),
            bundle,
            store.root / "results",
            store=store,
            environment=replace(good, lock_set_hash="wrong"),
            selection=selected,
        )
    with pytest.raises(ProjectStoreError, match="settings"):
        run_analysis_batch(
            FakeBackend(),
            bundle,
            store.root / "results",
            store=store,
            environment=replace(good, analysis_settings_id="OTHER"),
            selection=selected,
        )
    with pytest.raises(ProjectStoreError, match="inside project root"):
        run_analysis_batch(
            FakeBackend(),
            bundle,
            tmp_path / "outside",
            store=store,
            environment=good,
            selection=selected,
        )


@pytest.mark.unit
def test_residual_policy_numeric_change_changes_policy_and_formal_lock_hash(tmp_path: Path) -> None:
    all_carriers = carriers()
    residuals = [residual(tmp_path, platform, all_carriers) for platform in ("WFS", "RAD", "HOA")]
    deltas = {carrier.key.carrier_id: 0.1 for carrier in all_carriers}
    first_policy = ResidualValidationPolicy("POLICY", 0.01, 0.05)
    second_policy = ResidualValidationPolicy("POLICY", 0.02, 0.05)
    first = finalize_carrier_locks(
        all_carriers, residuals, deltas, residual_policy=first_policy
    )
    second = finalize_carrier_locks(
        all_carriers, residuals, deltas, residual_policy=second_policy
    )
    assert first_policy.policy_hash != second_policy.policy_hash
    assert first[0].lock_hash != second[0].lock_hash
