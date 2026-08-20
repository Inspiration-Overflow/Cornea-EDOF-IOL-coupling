"""Run the formal 72-configuration TASK-011 analysis or resume failed configs only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp import __version__
from whole_eye_mvp.analysis import ConfigResult
from whole_eye_mvp.analysis_zos_pair_scale import (
    EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
    PAIR_MONO_FREQUENCY_SCALE_MODE,
    TASK009_PAIR_MONO_MTF_ACQUISITION,
    ZosMtfaPairScaleAnalysisBackend,
    measure_pair_mono_reference,
)
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    NOMINAL_MAIN_FFT_MTF_555_V2,
    OpticState,
    RunEnvironment,
    ScientificBaseline,
)
from whole_eye_mvp.manifest import compute_lock_set_hash
from whole_eye_mvp.manifest_io import load_formal_manifest_bundle
from whole_eye_mvp.quality import settings_hash
from whole_eye_mvp.run72 import (
    RUN72_RESULT_SCHEMA_VERSION,
    build_run72_aggregate,
    config_scalar_row,
    load_config_result_json,
    paired_delta_row,
    through_focus_rows,
    validate_run72_clearance,
)
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.workflows import run_analysis_batch
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
TASK008_EVIDENCE = REPOSITORY_ROOT / "docs/evidence/task008/TASK_008_LOCK_MANIFEST_EVIDENCE.json"
RUN72_CLEARANCE = REPOSITORY_ROOT / "docs/evidence/task009/TASK_009_RUN72_WEB_CLEARANCE.json"
REPO_EVIDENCE_DIR = REPOSITORY_ROOT / "docs/evidence/task011"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-dir", type=Path, default=os.environ.get(INSTALL_ENV))
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument(
        "--resume-report",
        type=Path,
        help="Prior TASK-011 local report; reruns only its failed config IDs.",
    )
    parser.add_argument("--write-repo-evidence", action="store_true")
    return parser


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"required JSON is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON root must be an object: {path}")
    return payload


def _git_head() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise SystemExit("TASK-011 requires a clean tracked checkout")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(head) != 40:
        raise SystemExit("TASK-011 could not resolve a canonical Git commit")
    return head


def _opticstudio_version(session) -> str:
    for name in ("OpticStudioVersion", "ZOSVersion", "Version"):
        value = getattr(session.app, name, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise RuntimeError("installed application exposes no OpticStudio version string")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_resume(
    payload: dict[str, object],
    *,
    manifest_hash: str,
    lock_set_hash: str,
) -> None:
    expected = {
        "schema_version": RUN72_RESULT_SCHEMA_VERSION,
        "phase": "TASK-011-RUN72",
        "manifest_hash": manifest_hash,
        "lock_set_hash": lock_set_hash,
        "analysis_settings_id": NOMINAL_MAIN_FFT_MTF_555_V2.settings_id,
        "analysis_settings_sha256": settings_hash(NOMINAL_MAIN_FFT_MTF_555_V2),
        "acquisition_contract_id": TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id,
        "acquisition_contract_sha256": EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
        "frequency_scale_mode": PAIR_MONO_FREQUENCY_SCALE_MODE,
        "production_sampling": NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
    }
    mismatches = {
        key: (payload.get(key), value)
        for key, value in expected.items()
        if payload.get(key) != value
    }
    if mismatches:
        raise SystemExit(f"resume report identity mismatch: {mismatches}")
    if payload.get("run72_complete") is True:
        raise SystemExit("resume report is already complete")


def _prior_results(payload: dict[str, object]) -> dict[str, ConfigResult]:
    index = payload.get("completed_result_json_paths")
    if not isinstance(index, dict):
        raise SystemExit("resume report lacks completed_result_json_paths")
    results: dict[str, ConfigResult] = {}
    for config_id, raw_path in index.items():
        result = load_config_result_json(Path(str(raw_path)))
        if result.config.config_id != config_id:
            raise SystemExit(f"resume result index identity mismatch: {config_id}")
        results[str(config_id)] = result
    return results


def _write_repo_evidence(
    report: dict[str, object],
    aggregate,
) -> dict[str, str]:
    REPO_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    config_csv = REPO_EVIDENCE_DIR / "TASK_011_RUN72_CONFIG_RESULTS.csv"
    tf_csv = REPO_EVIDENCE_DIR / "TASK_011_RUN72_THROUGH_FOCUS.csv"
    delta_csv = REPO_EVIDENCE_DIR / "TASK_011_RUN72_PAIRED_DELTAS.csv"
    evidence_json = REPO_EVIDENCE_DIR / "TASK_011_RUN72_EVIDENCE.json"

    _write_csv(config_csv, [config_scalar_row(result) for result in aggregate.results])
    _write_csv(
        tf_csv,
        [row for result in aggregate.results for row in through_focus_rows(result)],
    )
    _write_csv(delta_csv, [paired_delta_row(delta) for delta in aggregate.paired_deltas])

    evidence = {
        key: value
        for key, value in report.items()
        if key not in {"completed_result_json_paths", "pair_references"}
    }
    evidence.update(
        {
            "evidence_only": True,
            "formal_scientific_lock": False,
            "config_results_csv_sha256": _sha(config_csv),
            "through_focus_csv_sha256": _sha(tf_csv),
            "paired_deltas_csv_sha256": _sha(delta_csv),
        }
    )
    evidence_json.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "evidence_json": str(evidence_json),
        "evidence_json_sha256": _sha(evidence_json),
        "config_csv_sha256": _sha(config_csv),
        "through_focus_csv_sha256": _sha(tf_csv),
        "delta_csv_sha256": _sha(delta_csv),
    }


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")
    code_commit = _git_head()
    project_dir = args.project_dir.resolve()

    task008 = _load_json(TASK008_EVIDENCE)
    clearance = _load_json(RUN72_CLEARANCE)
    validate_run72_clearance(clearance)

    manifest_artifacts = task008.get("manifest_artifact_sha256")
    carrier_hashes = task008.get("carrier_asset_sha256")
    residual_hashes = task008.get("residual_asset_sha256")
    if (
        not isinstance(manifest_artifacts, dict)
        or not isinstance(carrier_hashes, dict)
        or not isinstance(residual_hashes, dict)
    ):
        raise SystemExit("TASK-008 evidence lacks required artifact hash maps")

    bundle = load_formal_manifest_bundle(
        project_dir,
        expected_manifest_hash=str(task008.get("manifest_hash", "")),
        expected_physical_csv_sha256=str(
            manifest_artifacts.get("TASK008_PHYSICAL_CARRIER_LOCKS", "")
        ),
        expected_nominal_csv_sha256=str(manifest_artifacts.get("TASK008_NOMINAL_72", "")),
    )
    if len(bundle.nominal_configs) != 72:
        raise SystemExit("TASK-011 requires exact frozen 72-config manifest")
    lock_set_hash = compute_lock_set_hash(bundle.physical_carriers)
    if lock_set_hash != task008.get("lock_set_hash"):
        raise SystemExit("TASK-011 rebuilt lock-set hash differs from TASK-008 evidence")

    prior_payload: dict[str, object] | None = None
    combined: dict[str, ConfigResult] = {}
    prior_run_ids: list[str] = []
    pair_reference_effl_mm: dict[str, float] = {}
    pair_reference_records: dict[str, object] = {}

    if args.resume_report is not None:
        prior_payload = _load_json(args.resume_report.resolve())
        _validate_resume(
            prior_payload,
            manifest_hash=bundle.manifest_hash,
            lock_set_hash=lock_set_hash,
        )
        combined.update(_prior_results(prior_payload))
        failed = prior_payload.get("failed_config_ids")
        if not isinstance(failed, list) or not failed:
            raise SystemExit("resume report has no failed config IDs")
        selection = tuple(str(value) for value in failed)
        prior_run_ids = [str(value) for value in prior_payload.get("run_ids", [])]
        raw_refs = prior_payload.get("pair_references")
        if not isinstance(raw_refs, dict):
            raise SystemExit("resume report lacks pair_references")
        for pair_key, record in raw_refs.items():
            if not isinstance(record, dict):
                raise SystemExit("resume pair reference record is malformed")
            effl = float(record["reference_effl_mm"])
            pair_reference_effl_mm[str(pair_key)] = effl
            pair_reference_records[str(pair_key)] = record
    else:
        selection = tuple(config.config_id for config in bundle.nominal_configs)

    store = open_project_store(
        project_dir, ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    )
    output_root = project_dir / "results" / "task011_run72"
    pair_model_dir = project_dir / "diagnostics" / "task011" / "pair_reference_models"
    pair_model_dir.mkdir(parents=True, exist_ok=True)

    with open_zos_session(args.install_dir) as session:
        opticstudio_version = _opticstudio_version(session)

        if prior_payload is None:
            mono_by_pair = {
                config.pair_key: config
                for config in bundle.nominal_configs
                if config.optic_state == OpticState.MONO
            }
            if len(mono_by_pair) != 36:
                raise SystemExit("frozen manifest must contain exactly 36 MONO pair references")
            for pair_key, mono_config in sorted(mono_by_pair.items()):
                reference = measure_pair_mono_reference(
                    session,
                    project_dir,
                    carrier_hashes,
                    residual_hashes,
                    mono_config,
                    pair_model_dir / f"{pair_key}.zmx",
                )
                pair_reference_effl_mm[pair_key] = reference.reference_effl_mm
                pair_reference_records[pair_key] = asdict(reference)

        selection_set = set(selection)
        required_pairs = {
            config.pair_key
            for config in bundle.nominal_configs
            if config.config_id in selection_set
        }
        missing_refs = sorted(required_pairs - set(pair_reference_effl_mm))
        if missing_refs:
            raise SystemExit(f"missing pair-MONO angular-scale references: {missing_refs}")

        backend = ZosMtfaPairScaleAnalysisBackend(
            session,
            project_dir,
            carrier_hashes,
            residual_hashes,
            sampling=NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
            pair_reference_effl_mm=pair_reference_effl_mm,
        )
        environment = RunEnvironment(
            f"{__version__}+git.{code_commit[:12]}+task011-run72",
            opticstudio_version,
            CURRENT_SCIENTIFIC_BASELINE_ID,
            NOMINAL_MAIN_FFT_MTF_555_V2.settings_id,
            bundle.manifest_hash,
            lock_set_hash,
            TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id,
            EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
            PAIR_MONO_FREQUENCY_SCALE_MODE,
        )
        batch = run_analysis_batch(
            backend,
            bundle,
            output_root,
            store=store,
            environment=environment,
            selection=selection,
        )

    completed_paths: dict[str, str] = {}
    for outcome in batch.completed:
        if outcome.result is None:
            raise RuntimeError("completed batch outcome lacks ConfigResult")
        combined[outcome.config_id] = outcome.result
        result_json = Path(outcome.result.artifacts.zos_path).parent / "config_result.json"
        if not result_json.is_file():
            raise RuntimeError(f"completed result JSON is missing: {outcome.config_id}")
        completed_paths[outcome.config_id] = str(result_json.resolve())

    if prior_payload is not None:
        prior_index = prior_payload.get("completed_result_json_paths")
        if isinstance(prior_index, dict):
            completed_paths = {
                **{str(key): str(value) for key, value in prior_index.items()},
                **completed_paths,
            }

    expected_ids = {config.config_id for config in bundle.nominal_configs}
    failed_ids = sorted(expected_ids - set(combined))
    run_ids = [*prior_run_ids, batch.run_id]
    report: dict[str, object] = {
        "schema_version": RUN72_RESULT_SCHEMA_VERSION,
        "phase": "TASK-011-RUN72",
        "code_commit": code_commit,
        "baseline_id": CURRENT_SCIENTIFIC_BASELINE_ID,
        "manifest_hash": bundle.manifest_hash,
        "lock_set_hash": lock_set_hash,
        "analysis_settings_id": NOMINAL_MAIN_FFT_MTF_555_V2.settings_id,
        "analysis_settings_sha256": settings_hash(NOMINAL_MAIN_FFT_MTF_555_V2),
        "acquisition_contract_id": TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id,
        "acquisition_contract_sha256": EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
        "frequency_scale_mode": PAIR_MONO_FREQUENCY_SCALE_MODE,
        "production_sampling": NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
        "clearance_id": clearance["clearance_id"],
        "run_ids": run_ids,
        "latest_run_id": batch.run_id,
        "latest_environment_ref": batch.environment_ref,
        "resume_mode": prior_payload is not None,
        "selection_count": len(selection),
        "selection_config_ids": list(selection),
        "pair_reference_count": len(pair_reference_records),
        "pair_references": pair_reference_records,
        "completed_config_count": len(combined),
        "completed_config_ids": sorted(combined),
        "completed_result_json_paths": completed_paths,
        "failed_config_count": len(failed_ids),
        "failed_config_ids": failed_ids,
        "run72_started": True,
        "run72_complete": False,
        "acceptance_passed": False,
    }

    aggregate = None
    if not failed_ids:
        aggregate = build_run72_aggregate(tuple(combined.values()), manifest=bundle)
        report.update(
            {
                "run72_complete": True,
                "acceptance_passed": aggregate.acceptance.passed,
                "accepted_completed_configs": aggregate.acceptance.completed_configs,
                "accepted_matched_pairs": aggregate.acceptance.matched_pairs,
                "accepted_through_focus_rows": aggregate.acceptance.through_focus_rows,
            }
        )

    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{batch.run_id}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"TASK-011 report: {report_path}")
    print(
        f"completed={len(combined)} failed={len(failed_ids)} "
        f"latest_run_id={batch.run_id}"
    )

    if failed_ids:
        print("Failed config IDs:")
        for config_id in failed_ids:
            print(f"  {config_id}")
        raise SystemExit(2)

    if aggregate is None or not aggregate.acceptance.passed:
        raise SystemExit("Run72 aggregate acceptance did not pass")

    if args.write_repo_evidence:
        refs = _write_repo_evidence(report, aggregate)
        print(json.dumps(refs, indent=2))

    print("TASK-011 Run72 PASS: 72 configs / 36 pairs / 1080 through-focus rows")


if __name__ == "__main__":
    main()
