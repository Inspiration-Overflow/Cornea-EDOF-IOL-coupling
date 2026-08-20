"""Archive existing TASK-011 .zmx models without rerunning OpticStudio."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from whole_eye_mvp.model_archive import (
    ModelIndexRecord,
    archive_model,
    project_relative_path,
    sha256_file,
    validate_model_index,
    write_model_index,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
TASK011_EVIDENCE = REPOSITORY_ROOT / "docs/evidence/task011/TASK_011_RUN72_EVIDENCE.json"
TASK011_CONFIG_CSV = REPOSITORY_ROOT / "docs/evidence/task011/TASK_011_RUN72_CONFIG_RESULTS.csv"
TASK008_EVIDENCE = REPOSITORY_ROOT / "docs/evidence/task008/TASK_008_LOCK_MANIFEST_EVIDENCE.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--run-id", help="Defaults to TASK-011 evidence latest_run_id")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON root must be an object: {path}")
    return payload


def _read_config_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 72:
        raise SystemExit(f"TASK-011 config evidence must contain 72 rows, got {len(rows)}")
    return rows


def main() -> None:
    args = _parser().parse_args()
    project_dir = args.project_dir.resolve()
    evidence = _load_json(TASK011_EVIDENCE)
    task008 = _load_json(TASK008_EVIDENCE)
    run_id = str(args.run_id or evidence.get("latest_run_id") or "")
    if not run_id:
        raise SystemExit("TASK-011 evidence does not resolve a run ID")
    if run_id not in {str(value) for value in evidence.get("run_ids", [])}:
        raise SystemExit(f"run ID is outside formal TASK-011 evidence: {run_id}")

    rows = _read_config_rows(TASK011_CONFIG_CSV)
    by_config = {row["config_id"]: row for row in rows}
    if len(by_config) != 72:
        raise SystemExit("TASK-011 config evidence contains duplicate config IDs")

    pair_refs = evidence.get("pair_references")
    carrier_hashes = task008.get("carrier_asset_sha256")
    if not isinstance(pair_refs, dict) or len(pair_refs) != 36:
        raise SystemExit("TASK-011 evidence must contain exactly 36 pair references")
    if not isinstance(carrier_hashes, dict) or len(carrier_hashes) != 18:
        raise SystemExit("TASK-008 evidence must contain exactly 18 carrier asset hashes")

    archive_root = project_dir / "models" / "task011_run72" / "archive" / run_id
    config_archive_dir = archive_root / "configs"
    pair_archive_dir = archive_root / "pair_references"
    index_path = archive_root / "MODEL_INDEX.csv"
    records: list[ModelIndexRecord] = []

    for row in rows:
        config_id = row["config_id"]
        source = project_dir / "results" / "task011_run72" / run_id / config_id / "model.zmx"
        destination = config_archive_dir / f"{config_id}.zmx"
        expected_sha = row["model_sha256"]
        archived_sha = archive_model(
            source,
            destination,
            expected_sha256=expected_sha,
            overwrite=args.overwrite,
        )
        records.append(
            ModelIndexRecord(
                model_role="analyzed_config_source_snapshot",
                run_id=run_id,
                config_id=config_id,
                pair_key=row["pair_key"],
                carrier_id=row["carrier_id"],
                base_id=row["base_id"],
                cornea_id=row["cornea_id"],
                platform_id=row["platform_id"],
                optic_state=row["optic_state"],
                pupil_mm=float(row["pupil_mm"]),
                relative_path=project_relative_path(project_dir, destination),
                sha256=archived_sha,
            )
        )

    for pair_key in sorted(pair_refs):
        raw = pair_refs[pair_key]
        if not isinstance(raw, dict):
            raise SystemExit(f"invalid TASK-011 pair-reference record: {pair_key}")
        mono_config_id = str(raw.get("mono_config_id", ""))
        mono_row = by_config.get(mono_config_id)
        if mono_row is None:
            raise SystemExit(f"pair reference MONO config is absent from config evidence: {pair_key}")
        source = project_dir / "diagnostics" / "task011" / "pair_reference_models" / f"{pair_key}.zmx"
        destination = pair_archive_dir / f"{pair_key}.zmx"
        expected_sha = str(raw.get("model_sha256", ""))
        archived_sha = archive_model(
            source,
            destination,
            expected_sha256=expected_sha,
            overwrite=args.overwrite,
        )
        records.append(
            ModelIndexRecord(
                model_role="pair_mono_reference_source_snapshot",
                run_id=run_id,
                config_id=mono_config_id,
                pair_key=pair_key,
                carrier_id=mono_row["carrier_id"],
                base_id=mono_row["base_id"],
                cornea_id=mono_row["cornea_id"],
                platform_id=mono_row["platform_id"],
                optic_state=mono_row["optic_state"],
                pupil_mm=float(mono_row["pupil_mm"]),
                relative_path=project_relative_path(project_dir, destination),
                sha256=archived_sha,
            )
        )

    first_by_carrier: dict[str, dict[str, str]] = {}
    for row in rows:
        first_by_carrier.setdefault(row["carrier_id"], row)
    if set(first_by_carrier) != set(carrier_hashes):
        raise SystemExit("TASK-011 config evidence carrier set differs from TASK-008 carrier hash map")
    for carrier_id in sorted(first_by_carrier):
        row = first_by_carrier[carrier_id]
        path = project_dir / "models" / "carriers" / f"{carrier_id}.zmx"
        expected_sha = str(carrier_hashes[carrier_id])
        actual_sha = sha256_file(path)
        if actual_sha != expected_sha:
            raise SystemExit(f"formal carrier SHA mismatch during archive indexing: {carrier_id}")
        records.append(
            ModelIndexRecord(
                model_role="physical_carrier",
                run_id=run_id,
                config_id="",
                pair_key="",
                carrier_id=carrier_id,
                base_id=row["base_id"],
                cornea_id=row["cornea_id"],
                platform_id=row["platform_id"],
                optic_state="",
                pupil_mm="",
                relative_path=project_relative_path(project_dir, path),
                sha256=actual_sha,
            )
        )

    if len(records) != 126:
        raise SystemExit(f"TASK-011 model archive must index 126 models, got {len(records)}")
    write_model_index(index_path, tuple(records))
    validate_model_index(project_dir, tuple(records))
    print(
        json.dumps(
            {
                "run_id": run_id,
                "config_models_archived": 72,
                "pair_reference_models_archived": 36,
                "physical_carriers_indexed": 18,
                "model_index_records": len(records),
                "model_index": str(index_path.resolve()),
                "opticstudio_used": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
