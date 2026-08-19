"""Finalize TASK-008 carrier/residual locks and exact 18/72 manifests offline.

This command intentionally does not start OpticStudio. It promotes already-acquired
TASK-007 optical evidence only after hash verification and a cleared Web review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.carriers import (
    CarrierKey,
    ProvisionalCarrier,
    ResidualCalibration,
    ResidualDefinition,
    validate_18_provisional_carriers,
)
from whole_eye_mvp.domain import ArtifactRecord, CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline
from whole_eye_mvp.manifest import build_manifests, compute_lock_set_hash
from whole_eye_mvp.residual_policy import RESIDUAL_VALIDATION_546_V1
from whole_eye_mvp.store import open_project_store, sha256_file
from whole_eye_mvp.workflows import export_manifest_bundle, finalize_carrier_locks

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
SOURCE_EVIDENCE = (
    REPOSITORY_ROOT
    / "docs/evidence/task007/consolidated_batch/TASK_007_CONSOLIDATED_EVIDENCE.json"
)
REVIEW_EVIDENCE = (
    REPOSITORY_ROOT
    / "docs/evidence/task007/consolidated_review/TASK_007_CONSOLIDATED_REVIEW.json"
)
BATCH_REL = Path("diagnostics/task007/consolidated_batch")
SOURCE_REPORT_NAME = "TASK_007_CONSOLIDATED_BATCH.json"
REPO_EVIDENCE_DIR = REPOSITORY_ROOT / "docs/evidence/task008"
REPO_EVIDENCE_NAME = "TASK_008_LOCK_MANIFEST_EVIDENCE.json"
PLATFORMS = ("WFS", "RAD", "HOA")
LABELS = ("low", "median", "high")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
    parser.add_argument("--write-repo-evidence", action="store_true")
    return parser


def _clean_git_head() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise SystemExit("TASK-008 requires a clean tracked Git checkout")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(commit) != 40:
        raise SystemExit("TASK-008 could not resolve a canonical Git commit")
    return commit


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"required JSON is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON root must be an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _carrier_from_record(record: dict[str, object]) -> ProvisionalCarrier:
    carrier = record.get("carrier")
    if not isinstance(carrier, dict):
        raise TypeError("carrier evidence lacks the carrier block")
    key = carrier.get("key")
    if not isinstance(key, dict):
        raise TypeError("carrier evidence lacks the CarrierKey block")
    return ProvisionalCarrier(
        key=CarrierKey(
            str(key.get("base_id") or ""),
            str(key.get("cornea_id") or ""),
            str(key.get("platform_id") or ""),
        ),
        power_d=float(carrier["power_d"]),
        q=float(carrier["q"]),
        q_source_power_d=float(carrier["q_source_power_d"]),
        r_ant_mm=float(carrier["r_ant_mm"]),
        r_post_mm=float(carrier["r_post_mm"]),
        center_thickness_mm=float(carrier["center_thickness_mm"]),
        material=str(carrier["material"]),
        iol_position_mm=float(carrier["iol_position_mm"]),
        achieved_sa_um=float(carrier["achieved_sa_um"]),
    )


def _worst_signed(values: list[float]) -> float:
    if not values:
        raise ValueError("at least one low-order measurement is required")
    return max(values, key=lambda value: abs(float(value)))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = _parser().parse_args()
    code_commit = _clean_git_head()
    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(project_dir, baseline)

    source = _load_json(SOURCE_EVIDENCE)
    review = _load_json(REVIEW_EVIDENCE)
    source_sha = _sha256(SOURCE_EVIDENCE)
    review_sha = _sha256(REVIEW_EVIDENCE)
    if review.get("tdd_999_cleared") is not True:
        raise SystemExit("TASK-008 requires cleared TDD-999 reviewed evidence")
    if review.get("formal_artifact") is not False:
        raise SystemExit("TASK-007 review must remain evidence-only")
    if review.get("source_evidence_sha256") != source_sha:
        raise SystemExit("TASK-007 review/source evidence hash mismatch")
    if source.get("carrier_count") != 18 or source.get("all_18_carriers_validated") is not True:
        raise SystemExit("TASK-008 requires the validated 18-carrier TASK-007 source set")
    if source.get("calibration_count") != 9:
        raise SystemExit("TASK-008 requires nine TASK-007 residual calibrations")

    batch_dir = project_dir / BATCH_REL
    local_report = batch_dir / SOURCE_REPORT_NAME
    if not local_report.is_file():
        raise SystemExit("TASK-007 local consolidated report is missing")
    expected_local_report_sha = str(source.get("local_report_sha256") or "")
    if sha256_file(local_report) != expected_local_report_sha:
        raise SystemExit("TASK-007 local consolidated report hash differs from GitHub evidence")

    # Preserve the reviewed gate itself as a project-local immutable provenance artifact.
    review_ref = store.record_artifact(
        REVIEW_EVIDENCE,
        ArtifactRecord(
            artifact_id="TASK007_CONSOLIDATED_REVIEW",
            artifact_type="scientific_review_json",
            relative_path="locks/task007/TASK_007_CONSOLIDATED_REVIEW.json",
            baseline_id=baseline.baseline_id,
        ),
        lock=True,
    )

    carrier_evidence = source.get("carrier_evidence")
    if not isinstance(carrier_evidence, dict) or len(carrier_evidence) != 18:
        raise TypeError("TASK-007 source carrier evidence is incomplete")
    carriers: list[ProvisionalCarrier] = []
    carrier_asset_hashes: dict[str, str] = {}
    for carrier_id, raw_record in sorted(carrier_evidence.items()):
        if not isinstance(raw_record, dict):
            raise TypeError(f"carrier evidence is invalid: {carrier_id}")
        carrier = _carrier_from_record(raw_record)
        if carrier.key.carrier_id != carrier_id:
            raise SystemExit(f"carrier ID/key mismatch: {carrier_id}")
        source_path = batch_dir / "carriers" / f"{carrier_id}.zmx"
        expected_sha = str(raw_record.get("actual_eye_sha256") or "")
        if not source_path.is_file() or sha256_file(source_path) != expected_sha:
            raise SystemExit(f"formal carrier source/hash mismatch: {carrier_id}")
        ref = store.record_artifact(
            source_path,
            ArtifactRecord(
                artifact_id=carrier_id,
                artifact_type="zemax_carrier",
                relative_path=f"models/carriers/{carrier_id}.zmx",
                baseline_id=baseline.baseline_id,
            ),
            lock=True,
        )
        if not store.verify_artifact(ref):
            raise SystemExit(f"formal carrier artifact verification failed: {carrier_id}")
        carriers.append(carrier)
        carrier_asset_hashes[carrier_id] = ref.sha256
    validate_18_provisional_carriers(carriers)

    residual_payloads = source.get("residual_payloads")
    calibrations = source.get("calibration_evidence")
    if not isinstance(residual_payloads, dict) or set(residual_payloads) != set(PLATFORMS):
        raise TypeError("TASK-007 residual payload evidence is incomplete")
    if not isinstance(calibrations, dict) or set(calibrations) != set(PLATFORMS):
        raise TypeError("TASK-007 calibration evidence is incomplete")

    residuals: list[ResidualDefinition] = []
    residual_asset_hashes: dict[str, str] = {}
    validation_hashes: dict[str, str] = {}
    staging = project_dir / "diagnostics" / "task008" / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    for platform in PLATFORMS:
        payload_record = residual_payloads[platform]
        platform_records = calibrations[platform]
        if not isinstance(payload_record, dict) or not isinstance(platform_records, dict):
            raise TypeError(f"invalid TASK-007 residual evidence for {platform}")
        if set(platform_records) != set(LABELS):
            raise SystemExit(f"{platform} calibration labels are not exactly low/median/high")

        residual_id = f"RESIDUAL_{platform}_546_v1"
        source_dat = batch_dir / "residual_payloads" / f"RESIDUAL_{platform}.DAT"
        expected_dat_sha = str(payload_record.get("sha256") or "")
        if not source_dat.is_file() or sha256_file(source_dat) != expected_dat_sha:
            raise SystemExit(f"{platform} residual DAT hash mismatch")
        payload_ref = store.record_artifact(
            source_dat,
            ArtifactRecord(
                artifact_id=residual_id,
                artifact_type="grid_sag_residual",
                relative_path=f"models/assets/residuals/{residual_id}.DAT",
                baseline_id=baseline.baseline_id,
            ),
            lock=True,
        )
        if not store.verify_artifact(payload_ref):
            raise SystemExit(f"{platform} formal residual payload verification failed")
        residual_asset_hashes[platform] = payload_ref.sha256

        standard_pistons: list[float] = []
        standard_defocus: list[float] = []
        calibration_rows: list[dict[str, object]] = []
        calibration_objects: list[ResidualCalibration] = []
        for label in LABELS:
            record = platform_records[label]
            if not isinstance(record, dict):
                raise TypeError(f"invalid {platform}/{label} calibration evidence")
            standard = record.get("standard_readback")
            if not isinstance(standard, dict):
                raise TypeError(f"missing {platform}/{label} standard-eye readback")
            piston = float(standard["measured_piston_um"])
            defocus = float(standard["measured_global_defocus_d"])
            standard_pistons.append(piston)
            standard_defocus.append(defocus)
            calibration_rows.append(
                {
                    "label": label,
                    "carrier_id": record["carrier_id"],
                    "actual_power_d": record["actual_power_d"],
                    "standard_piston_um": piston,
                    "standard_global_defocus_d": defocus,
                    "distance_shift_d": record["distance_shift_d"],
                    "mono_dof50_d": record["mono_dof50_d"],
                    "edof_dof50_d": record["edof_dof50_d"],
                    "mono_ray_health_passed": record["mono_ray_health"]["passed"],
                    "edof_ray_health_passed": record["edof_ray_health"]["passed"],
                }
            )

        validation_payload = {
            "schema_version": 1,
            "formal_artifact": True,
            "residual_id": residual_id,
            "platform_id": platform,
            "payload_sha256": payload_ref.sha256,
            "policy_id": RESIDUAL_VALIDATION_546_V1.policy_id,
            "policy_hash": RESIDUAL_VALIDATION_546_V1.policy_hash,
            "low_order_gate_domain": "STD_IOL_EYE_2024_EPD6_imported_residual_readback",
            "actual_eye_ssag_readback_role": "diagnostic_only_aperture_limited_mode0",
            "worst_standard_piston_um": _worst_signed(standard_pistons),
            "worst_standard_global_defocus_d": _worst_signed(standard_defocus),
            "calibrations": calibration_rows,
            "task007_review_sha256": review_sha,
            "task007_review_hash": review.get("review_hash"),
            "tdd_999_cleared": True,
        }
        staging_validation = staging / f"{residual_id}_VALIDATION.json"
        _write_json(staging_validation, validation_payload)
        validation_ref = store.record_artifact(
            staging_validation,
            ArtifactRecord(
                artifact_id=f"{residual_id}_VALIDATION",
                artifact_type="residual_validation_json",
                relative_path=f"locks/residuals/{residual_id}_VALIDATION.json",
                baseline_id=baseline.baseline_id,
            ),
            lock=True,
        )
        if not store.verify_artifact(validation_ref):
            raise SystemExit(f"{platform} residual validation artifact verification failed")
        validation_hashes[platform] = validation_ref.sha256
        validation_path = store.resolve(validation_ref.relative_path)

        for row in calibration_rows:
            calibration_objects.append(
                ResidualCalibration(
                    label=str(row["label"]),
                    carrier_id=str(row["carrier_id"]),
                    actual_power_d=float(row["actual_power_d"]),
                    oracle_passed=True,
                    distance_shift_d=float(row["distance_shift_d"]),
                    evidence_ref=str(validation_path),
                    evidence_sha256=validation_ref.sha256,
                )
            )

        residuals.append(
            ResidualDefinition(
                residual_id=residual_id,
                platform_id=platform,
                version="1",
                representation="grid_sag_resource",
                payload_ref=str(store.resolve(payload_ref.relative_path)),
                units="mm",
                radial_domain_mm=(0.0, 3.0),
                piston_removed=True,
                defocus_removed=True,
                sha256=payload_ref.sha256,
                measured_piston_um=_worst_signed(standard_pistons),
                measured_global_defocus_d=_worst_signed(standard_defocus),
                validation_evidence_ref=str(validation_path),
                validation_evidence_sha256=validation_ref.sha256,
                calibrations=tuple(calibration_objects),
            )
        )

    locks = finalize_carrier_locks(
        carriers,
        residuals,
        residual_policy=RESIDUAL_VALIDATION_546_V1,
    )
    bundle = build_manifests(locks)
    paths = export_manifest_bundle(bundle, project_dir / "manifests")
    lock_set_hash = compute_lock_set_hash(locks)

    manifest_artifacts = {}
    for artifact_id, artifact_type, path_text, relative_path in (
        (
            "TASK008_PHYSICAL_CARRIER_LOCKS",
            "carrier_lock_csv",
            paths.physical_carriers_csv,
            "manifests/physical_carriers.csv",
        ),
        (
            "TASK008_NOMINAL_72",
            "nominal_manifest_csv",
            paths.nominal_72_csv,
            "manifests/nominal_72.csv",
        ),
        (
            "TASK008_MANIFEST_HASH",
            "manifest_hash",
            paths.manifest_hash_file,
            "manifests/manifest.sha256",
        ),
    ):
        ref = store.record_artifact(
            path_text,
            ArtifactRecord(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                relative_path=relative_path,
                baseline_id=baseline.baseline_id,
            ),
            lock=True,
        )
        if not store.verify_artifact(ref):
            raise SystemExit(f"TASK-008 artifact verification failed: {artifact_id}")
        manifest_artifacts[artifact_id] = ref.sha256

    summary = {
        "schema_version": 1,
        "phase": "TASK-008-FORMAL-LOCK-MANIFEST",
        "formal_artifact": True,
        "baseline_id": baseline.baseline_id,
        "code_commit": code_commit,
        "task007_review_artifact_sha256": review_ref.sha256,
        "task007_review_hash": review.get("review_hash"),
        "source_evidence_sha256": source_sha,
        "carrier_count": len(locks),
        "nominal_config_count": len(bundle.nominal_configs),
        "residual_count": len(residuals),
        "carrier_asset_sha256": carrier_asset_hashes,
        "residual_asset_sha256": residual_asset_hashes,
        "residual_validation_sha256": validation_hashes,
        "manifest_hash": bundle.manifest_hash,
        "lock_set_hash": lock_set_hash,
        "manifest_artifact_sha256": manifest_artifacts,
        "tdd_999_cleared": True,
        "selection_locked": True,
        "opticstudio_started": False,
        "next_gate": "TASK-009 representative three-configuration Huygens PSF validation",
    }
    staging_summary = staging / "TASK_008_LOCK_MANIFEST_SUMMARY.json"
    _write_json(staging_summary, summary)
    summary_ref = store.record_artifact(
        staging_summary,
        ArtifactRecord(
            artifact_id="TASK008_LOCK_MANIFEST_SUMMARY",
            artifact_type="task008_lock_summary",
            relative_path="locks/TASK_008_LOCK_MANIFEST_SUMMARY.json",
            baseline_id=baseline.baseline_id,
        ),
        lock=True,
    )
    summary["formal_summary_sha256"] = summary_ref.sha256

    if args.write_repo_evidence:
        REPO_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        repo_payload = dict(summary)
        repo_payload["formal_summary_sha256"] = summary_ref.sha256
        _write_json(REPO_EVIDENCE_DIR / REPO_EVIDENCE_NAME, repo_payload)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
