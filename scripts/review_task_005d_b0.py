"""Apply human B0 morphology decisions, re-rank deterministically, and write the immutable B0 lock."""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.b0_review import MorphologyDecision, review_and_lock_b0_scan_payload
from whole_eye_mvp.domain import (
    CORNEA_LOCK_B0_555_V2,
    CURRENT_SCIENTIFIC_BASELINE_ID,
    ArtifactRecord,
    ScientificBaseline,
)
from whole_eye_mvp.store import open_project_store

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
SCAN_RELATIVE_PATH = (
    Path("diagnostics")
    / "task005d"
    / "b0_scan_mtfa_v2"
    / "TASK_006_B0_REAL_SCAN.json"
)
LOCK_RELATIVE_PATH = "locks/B0_LOCK.json"
LOCK_ARTIFACT_ID = "B0_LOCK"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
    parser.add_argument(
        "--decisions-json",
        type=Path,
        required=True,
        help=(
            "JSON mapping candidate ID to {reject: bool, reason: str}; "
            "must cover exactly B0.10/B0.15/B0.20/B0.25/B0.30"
        ),
    )
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--selection-reason", required=True)
    return parser


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"JSON root must be an object: {path}")
    return value


def _load_decisions(path: Path) -> tuple[MorphologyDecision, ...]:
    payload = _load_json_object(path)
    decisions: list[MorphologyDecision] = []
    for candidate_id, raw in payload.items():
        if not isinstance(raw, dict):
            raise SystemExit(f"Decision for {candidate_id} must be an object")
        reject = raw.get("reject")
        reason = raw.get("reason", "")
        if not isinstance(reject, bool) or not isinstance(reason, str):
            raise SystemExit(
                f"Decision for {candidate_id} requires boolean reject and string reason"
            )
        decisions.append(MorphologyDecision(candidate_id, reject, reason))
    return tuple(decisions)


def main() -> None:
    args = _parser().parse_args()
    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(project_dir, baseline)

    scan_path = project_dir / SCAN_RELATIVE_PATH
    if not scan_path.is_file():
        raise SystemExit(f"Completed B0 scan is missing: {scan_path}")
    source_scan = _load_json_object(scan_path)
    decisions = _load_decisions(args.decisions_json.resolve())
    candidate_id = args.candidate_id.strip()
    selection_reason = args.selection_reason.strip()
    if not candidate_id:
        raise SystemExit("--candidate-id must not be empty")
    if not selection_reason:
        raise SystemExit("--selection-reason must not be empty")

    reviewed = review_and_lock_b0_scan_payload(
        source_scan,
        decisions,
        candidate_id,
        selection_reason=selection_reason,
    )
    payload = {
        "formal_artifact": True,
        "selection_locked": True,
        "analysis_settings": asdict(CORNEA_LOCK_B0_555_V2),
        "source_scan_path": str(scan_path),
        "source_scan_hash": reviewed.source_scan_hash,
        "morphology_decisions": [asdict(item) for item in reviewed.decisions],
        "reviewed_scan_report": asdict(reviewed.report),
        "lock": asdict(reviewed.lock),
    }

    existing = store.find_artifact(LOCK_ARTIFACT_ID)
    if existing is not None:
        raise SystemExit(
            f"B0 lock already exists and is immutable: {store.resolve(existing.relative_path)}"
        )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    try:
        ref = store.record_artifact(
            temp_path,
            ArtifactRecord(
                artifact_id=LOCK_ARTIFACT_ID,
                artifact_type="b0_lock",
                relative_path=LOCK_RELATIVE_PATH,
                baseline_id=baseline.baseline_id,
            ),
            lock=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    print(
        json.dumps(
            {
                "artifact": asdict(ref),
                **payload,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
