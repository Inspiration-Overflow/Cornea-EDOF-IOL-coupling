"""Run the independent TASK-013 N0 native/untreated cornea reference extension.

TASK-013 does not mutate the frozen TASK-008/011 72-config identity. It builds six new
N0 physical carriers, gates them against the frozen residual power envelope, measures
12 paired-MONO angular references, runs 24 new configs with the TASK-009 production
method, and archives every final N0 model as a hashed .zmx artifact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp import __version__
from whole_eye_mvp.analysis import (
    ConfigResult,
    matched_pair_delta,
    validate_completed_result,
)
from whole_eye_mvp.analysis_zos_pair_scale import (
    EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
    PAIR_MONO_FREQUENCY_SCALE_MODE,
    TASK009_PAIR_MONO_MTF_ACQUISITION,
)
from whole_eye_mvp.base_assets import base_asset_prescriptions
from whole_eye_mvp.carrier_zos import solve_actual_eye_carrier_power
from whole_eye_mvp.cornea_assets import CORNEA_LOCK_BASE_ID
from whole_eye_mvp.cornea_zos import build_reference_cornea_scaffold
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    NOMINAL_MAIN_FFT_MTF_555_V2,
    BaseId,
    OpticState,
    PlatformId,
    ScientificBaseline,
)
from whole_eye_mvp.manifest_io import load_formal_manifest_bundle
from whole_eye_mvp.model_archive import (
    ModelIndexRecord,
    archive_model,
    project_relative_path,
    sha256_file,
    validate_model_index,
    write_model_index,
)
from whole_eye_mvp.quality import settings_hash
from whole_eye_mvp.run72 import config_scalar_row, paired_delta_row, through_focus_rows
from whole_eye_mvp.standard_eye import ARTIFACT_ID as STANDARD_EYE_ARTIFACT_ID
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.task013_native_reference import (
    NATIVE_REFERENCE_CORNEA_ID,
    TASK013_EXPECTED_CONFIG_COUNT,
    TASK013_EXPECTED_PAIR_COUNT,
    TASK013_EXPECTED_THROUGH_FOCUS_ROWS,
    TASK013_ID,
    build_task013_manifest,
    make_native_carrier_lock,
    require_residual_power_envelopes,
    residual_provenance_from_existing_locks,
)
from whole_eye_mvp.task013_zos import (
    Task013PairScaleAnalysisBackend,
    measure_task013_pair_mono_reference,
    solve_native_platform_carrier,
)
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
TASK008_EVIDENCE = REPOSITORY_ROOT / "docs/evidence/task008/TASK_008_LOCK_MANIFEST_EVIDENCE.json"
REPO_EVIDENCE_DIR = REPOSITORY_ROOT / "docs/evidence/task013"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-dir", type=Path, default=os.environ.get(INSTALL_ENV))
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
    parser.add_argument(
        "--overwrite-models",
        action="store_true",
        help="Replace existing canonical N0 cornea/carrier files. Run directories remain unique.",
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


def _git_head() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise SystemExit("TASK-013 requires a clean tracked checkout")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(head) != 40:
        raise SystemExit("TASK-013 could not resolve a canonical Git commit")
    return head


def _opticstudio_version(session) -> str:
    for name in ("OpticStudioVersion", "ZOSVersion", "Version"):
        value = getattr(session.app, name, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise RuntimeError("installed application exposes no OpticStudio version string")


def _guard_canonical(path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise SystemExit(f"canonical model already exists; pass --overwrite-models: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_config_result(path: Path, result: ConfigResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _pair_results(results: list[ConfigResult]):
    by_pair: dict[str, dict[str, ConfigResult]] = {}
    for result in results:
        by_pair.setdefault(result.config.pair_key, {})[str(result.config.optic_state)] = result
    deltas = []
    for pair_key in sorted(by_pair):
        states = by_pair[pair_key]
        mono = states.get(str(OpticState.MONO))
        edof = states.get(str(OpticState.EDOF))
        if mono is None or edof is None or len(states) != 2:
            raise SystemExit(f"TASK-013 matched pair is incomplete: {pair_key}")
        deltas.append(matched_pair_delta(mono, edof))
    if len(deltas) != TASK013_EXPECTED_PAIR_COUNT:
        raise SystemExit("TASK-013 did not reconstruct exactly 12 matched pairs")
    return tuple(deltas)


def _pair_reference_set_hash(records: dict[str, dict[str, object]]) -> str:
    if len(records) != TASK013_EXPECTED_PAIR_COUNT:
        raise SystemExit("TASK-013 requires exactly 12 pair-reference records")
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_repo_evidence(
    *,
    report: dict[str, object],
    results: list[ConfigResult],
    deltas,
    model_index_path: Path,
) -> dict[str, str]:
    REPO_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    config_csv = REPO_EVIDENCE_DIR / "TASK_013_NATIVE_REFERENCE_CONFIG_RESULTS.csv"
    tf_csv = REPO_EVIDENCE_DIR / "TASK_013_NATIVE_REFERENCE_THROUGH_FOCUS.csv"
    delta_csv = REPO_EVIDENCE_DIR / "TASK_013_NATIVE_REFERENCE_PAIRED_DELTAS.csv"
    index_csv = REPO_EVIDENCE_DIR / "TASK_013_MODEL_INDEX.csv"
    evidence_json = REPO_EVIDENCE_DIR / "TASK_013_NATIVE_REFERENCE_EVIDENCE.json"

    _write_csv(config_csv, [config_scalar_row(result) for result in results])
    _write_csv(tf_csv, [row for result in results for row in through_focus_rows(result)])
    _write_csv(delta_csv, [paired_delta_row(delta) for delta in deltas])
    index_csv.write_bytes(model_index_path.read_bytes())

    evidence = {
        key: value
        for key, value in report.items()
        if key not in {"completed_result_json_paths", "failure_details"}
    }
    evidence.update(
        {
            "evidence_only": True,
            "formal_scientific_lock": False,
            "extends_frozen_task011": True,
            "task011_structured_evidence_changed": False,
            "config_results_csv_sha256": _sha(config_csv),
            "through_focus_csv_sha256": _sha(tf_csv),
            "paired_deltas_csv_sha256": _sha(delta_csv),
            "model_index_csv_sha256": _sha(index_csv),
        }
    )
    evidence_json.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "evidence_json": str(evidence_json),
        "evidence_json_sha256": _sha(evidence_json),
        "config_csv_sha256": _sha(config_csv),
        "through_focus_csv_sha256": _sha(tf_csv),
        "delta_csv_sha256": _sha(delta_csv),
        "model_index_csv_sha256": _sha(index_csv),
    }


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    code_commit = _git_head()
    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(project_dir, baseline)
    task008 = _load_json(TASK008_EVIDENCE)

    manifest_artifacts = task008.get("manifest_artifact_sha256")
    existing_carrier_hashes = task008.get("carrier_asset_sha256")
    residual_hashes = task008.get("residual_asset_sha256")
    if (
        not isinstance(manifest_artifacts, dict)
        or not isinstance(existing_carrier_hashes, dict)
        or not isinstance(residual_hashes, dict)
    ):
        raise SystemExit("TASK-008 evidence lacks required artifact hash maps")

    frozen_bundle = load_formal_manifest_bundle(
        project_dir,
        expected_manifest_hash=str(task008.get("manifest_hash", "")),
        expected_physical_csv_sha256=str(
            manifest_artifacts.get("TASK008_PHYSICAL_CARRIER_LOCKS", "")
        ),
        expected_nominal_csv_sha256=str(manifest_artifacts.get("TASK008_NOMINAL_72", "")),
    )
    if len(frozen_bundle.physical_carriers) != 18 or len(frozen_bundle.nominal_configs) != 72:
        raise SystemExit("TASK-013 requires the unchanged frozen 18-carrier/72-config TASK-008 source")
    residual_provenance = residual_provenance_from_existing_locks(
        frozen_bundle.physical_carriers
    )

    std_record = store.find_artifact(STANDARD_EYE_ARTIFACT_ID)
    if std_record is None or std_record.relative_path != STANDARD_EYE_RELATIVE_PATH:
        raise SystemExit("locked STD_IOL_EYE_2024 is not registered")
    if not std_record.locked or not store.verify_artifact(std_record):
        raise SystemExit("STD_IOL_EYE_2024 immutable hash validation failed")
    standard_eye_path = store.resolve(std_record.relative_path)

    lb_base = next(
        item
        for item in base_asset_prescriptions(baseline)
        if item.base_spec.base_id == CORNEA_LOCK_BASE_ID
    )
    lb_base_path = store.resolve(lb_base.relative_path)
    if not lb_base_path.is_file():
        raise SystemExit(f"locked LB base asset is missing: {lb_base_path}")

    run_id = f"task013-{uuid.uuid4().hex}"
    model_root = project_dir / "models" / "task013_native_reference"
    cornea_dir = model_root / "cornea"
    carrier_dir = model_root / "carriers"
    run_model_dir = model_root / "runs" / run_id
    pair_reference_dir = run_model_dir / "pair_references"
    config_archive_dir = run_model_dir / "configs"
    work_dir = project_dir / "diagnostics" / "task013" / run_id / "carrier_work"
    result_root = project_dir / "results" / "task013_native_reference" / run_id
    report_dir = project_dir / "results" / "task013_native_reference" / "reports"
    report_path = report_dir / f"{run_id}.json"
    model_index_path = run_model_dir / "MODEL_INDEX.csv"

    n0_path = cornea_dir / "N0_REFERENCE_CORNEA.zmx"
    _guard_canonical(n0_path, overwrite=args.overwrite_models)
    for base in (BaseId.LB_AL2395, BaseId.ATC_M3_AL24477):
        for platform in (PlatformId.WFS, PlatformId.RAD, PlatformId.HOA):
            _guard_canonical(
                carrier_dir / f"CAR_{base}_{NATIVE_REFERENCE_CORNEA_ID}_{platform}.zmx",
                overwrite=args.overwrite_models,
            )

    native_carriers = []
    carrier_evidence: dict[str, object] = {}
    model_index: list[ModelIndexRecord] = []
    pair_reference_records: dict[str, dict[str, object]] = {}
    results: list[ConfigResult] = []
    result_json_paths: dict[str, str] = {}
    failures: dict[str, str] = {}

    with open_zos_session(args.install_dir) as session:
        opticstudio_version = _opticstudio_version(session)
        build_reference_cornea_scaffold(session, baseline, lb_base_path, n0_path)
        n0_sha = sha256_file(n0_path)
        model_index.append(
            ModelIndexRecord(
                model_role="native_reference_cornea",
                run_id=run_id,
                config_id="",
                pair_key="",
                carrier_id="",
                base_id="",
                cornea_id=NATIVE_REFERENCE_CORNEA_ID,
                platform_id="",
                optic_state="",
                pupil_mm="",
                relative_path=project_relative_path(project_dir, n0_path),
                sha256=n0_sha,
            )
        )

        p0_map: dict[str, tuple[object, Path]] = {}
        for base in (BaseId.LB_AL2395, BaseId.ATC_M3_AL24477):
            base_id = str(base)
            p0_path = work_dir / f"P0_{base_id}_{NATIVE_REFERENCE_CORNEA_ID}.zmx"
            p0 = solve_actual_eye_carrier_power(
                session,
                baseline,
                base_id,
                n0_path,
                p0_path,
            )
            p0_map[base_id] = (p0, p0_path)

        for base in (BaseId.LB_AL2395, BaseId.ATC_M3_AL24477):
            base_id = str(base)
            p0, p0_path = p0_map[base_id]
            for platform in (PlatformId.WFS, PlatformId.RAD, PlatformId.HOA):
                platform_id = str(platform)
                carrier_id = f"CAR_{base_id}_{NATIVE_REFERENCE_CORNEA_ID}_{platform_id}"
                destination = carrier_dir / f"{carrier_id}.zmx"
                carrier, evidence = solve_native_platform_carrier(
                    session,
                    standard_eye_path,
                    base_id=base_id,
                    platform_id=platform_id,
                    p0=p0,
                    p0_path=p0_path,
                    destination=destination,
                    recheck_dir=work_dir / "pq_rechecks",
                )
                native_carriers.append(carrier)
                carrier_evidence[carrier_id] = evidence
                model_index.append(
                    ModelIndexRecord(
                        model_role="physical_carrier",
                        run_id=run_id,
                        config_id="",
                        pair_key="",
                        carrier_id=carrier_id,
                        base_id=base_id,
                        cornea_id=NATIVE_REFERENCE_CORNEA_ID,
                        platform_id=platform_id,
                        optic_state="",
                        pupil_mm="",
                        relative_path=project_relative_path(project_dir, destination),
                        sha256=sha256_file(destination),
                    )
                )

        envelope_checks = require_residual_power_envelopes(
            [lock.carrier for lock in frozen_bundle.physical_carriers],
            native_carriers,
        )

        native_locks = [
            make_native_carrier_lock(
                carrier,
                residual_provenance[str(carrier.key.platform_id)],
            )
            for carrier in native_carriers
        ]
        bundle = build_task013_manifest(native_locks)
        native_carrier_hashes = {
            lock.carrier_id: sha256_file(carrier_dir / f"{lock.carrier_id}.zmx")
            for lock in bundle.physical_carriers
        }

        mono_by_pair = {
            config.pair_key: config
            for config in bundle.nominal_configs
            if config.optic_state == OpticState.MONO
        }
        if len(mono_by_pair) != TASK013_EXPECTED_PAIR_COUNT:
            raise SystemExit("TASK-013 manifest did not resolve exactly 12 MONO pair references")

        pair_reference_effl_mm: dict[str, float] = {}
        for pair_key in sorted(mono_by_pair):
            config = mono_by_pair[pair_key]
            destination = pair_reference_dir / f"{pair_key}.zmx"
            reference = measure_task013_pair_mono_reference(
                session,
                project_dir,
                carrier_dir,
                native_carrier_hashes,
                {str(key): str(value) for key, value in residual_hashes.items()},
                config,
                destination,
            )
            pair_reference_effl_mm[pair_key] = reference.reference_effl_mm
            pair_reference_records[pair_key] = asdict(reference)
            model_index.append(
                ModelIndexRecord(
                    model_role="pair_mono_reference",
                    run_id=run_id,
                    config_id=config.config_id,
                    pair_key=pair_key,
                    carrier_id=config.carrier_id,
                    base_id=config.base_id,
                    cornea_id=config.cornea_id,
                    platform_id=config.platform_id,
                    optic_state=str(config.optic_state),
                    pupil_mm=config.pupil_mm,
                    relative_path=project_relative_path(project_dir, destination),
                    sha256=reference.model_sha256,
                )
            )

        backend = Task013PairScaleAnalysisBackend(
            session,
            project_dir,
            carrier_dir,
            native_carrier_hashes,
            {str(key): str(value) for key, value in residual_hashes.items()},
            pair_reference_effl_mm=pair_reference_effl_mm,
            sampling=NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
        )

        for config in bundle.nominal_configs:
            target = result_root / config.config_id
            try:
                result = backend.run_config(config, target, run_id)
                validate_completed_result(
                    result,
                    require_files=True,
                    expected_config=config,
                    expected_run_id=run_id,
                )
                config_json = target / "config_result.json"
                _write_config_result(config_json, result)
                result_json_paths[config.config_id] = str(config_json.resolve())
                archive_path = config_archive_dir / f"{config.config_id}.zmx"
                archived_sha = archive_model(
                    result.artifacts.zos_path,
                    archive_path,
                    expected_sha256=result.model_hash_before,
                )
                model_index.append(
                    ModelIndexRecord(
                        model_role="analyzed_config",
                        run_id=run_id,
                        config_id=config.config_id,
                        pair_key=config.pair_key,
                        carrier_id=config.carrier_id,
                        base_id=config.base_id,
                        cornea_id=config.cornea_id,
                        platform_id=config.platform_id,
                        optic_state=str(config.optic_state),
                        pupil_mm=config.pupil_mm,
                        relative_path=project_relative_path(project_dir, archive_path),
                        sha256=archived_sha,
                    )
                )
                results.append(result)
            except Exception as exc:  # noqa: BLE001 - formal batch records per-config failure
                failures[config.config_id] = f"{type(exc).__name__}: {exc}"

    completed = len(results)
    through_focus_count = sum(len(result.rows) for result in results)
    pair_reference_hash = _pair_reference_set_hash(pair_reference_records)
    deltas = _pair_results(results) if completed == TASK013_EXPECTED_CONFIG_COUNT else ()

    archive_complete = (
        completed == TASK013_EXPECTED_CONFIG_COUNT
        and not failures
        and through_focus_count == TASK013_EXPECTED_THROUGH_FOCUS_ROWS
        and len(deltas) == TASK013_EXPECTED_PAIR_COUNT
    )
    if archive_complete:
        write_model_index(model_index_path, tuple(model_index))
        validate_model_index(project_dir, tuple(model_index))

    report = {
        "schema_version": 1,
        "phase": "TASK-013-NATIVE-CORNEA-REFERENCE",
        "task_id": TASK013_ID,
        "run_id": run_id,
        "code_commit": code_commit,
        "package_version": __version__,
        "opticstudio_version": opticstudio_version,
        "baseline_id": args.baseline_id,
        "source_task008_manifest_hash": task008.get("manifest_hash"),
        "source_task008_lock_set_hash": task008.get("lock_set_hash"),
        "source_task011_expected_configs": 72,
        "source_task011_rerun": False,
        "native_cornea_id": NATIVE_REFERENCE_CORNEA_ID,
        "native_cornea_sha256": n0_sha,
        "native_manifest_hash": bundle.manifest_hash,
        "native_lock_set_hash": bundle.lock_set_hash,
        "native_physical_carriers": len(bundle.physical_carriers),
        "native_nominal_configs": len(bundle.nominal_configs),
        "analysis_settings_id": NOMINAL_MAIN_FFT_MTF_555_V2.settings_id,
        "analysis_settings_sha256": settings_hash(NOMINAL_MAIN_FFT_MTF_555_V2),
        "acquisition_contract_id": TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id,
        "acquisition_contract_sha256": EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
        "frequency_scale_mode": PAIR_MONO_FREQUENCY_SCALE_MODE,
        "production_sampling": NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
        "residual_power_envelope_checks": [asdict(item) for item in envelope_checks],
        "residual_power_coverage_complete": all(
            item.within_existing_coverage for item in envelope_checks
        ),
        "residual_power_extension_validation_required": any(
            item.extension_validation_required for item in envelope_checks
        ),
        "carrier_evidence": carrier_evidence,
        "pair_reference_records": pair_reference_records,
        "pair_reference_set_sha256": pair_reference_hash,
        "pair_reference_count": len(pair_reference_records),
        "completed_configs": completed,
        "failed_configs": len(failures),
        "failed_config_ids": sorted(failures),
        "failure_details": failures,
        "through_focus_rows": through_focus_count,
        "matched_pairs": len(deltas),
        "canonical_model_index_records": len(model_index) if archive_complete else 0,
        "model_archive_complete": archive_complete,
        "acceptance_passed": archive_complete,
        "task013_complete": archive_complete,
        "completed_result_json_paths": result_json_paths,
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    repo_evidence = None
    if args.write_repo_evidence:
        if not archive_complete:
            raise SystemExit("refusing to write repo evidence for incomplete TASK-013 run")
        repo_evidence = _write_repo_evidence(
            report=report,
            results=results,
            deltas=deltas,
            model_index_path=model_index_path,
        )

    print(
        json.dumps(
            {
                "report_path": str(report_path.resolve()),
                "run_id": run_id,
                "completed_configs": completed,
                "failed_configs": len(failures),
                "pair_reference_count": len(pair_reference_records),
                "matched_pairs": len(deltas),
                "through_focus_rows": through_focus_count,
                "model_archive_complete": archive_complete,
                "model_index": str(model_index_path.resolve()) if archive_complete else None,
                "repo_evidence": repo_evidence,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not archive_complete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
