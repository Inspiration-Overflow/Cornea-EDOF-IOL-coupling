"""Re-evaluate TASK-007 consolidated evidence using the frozen normative review domain.

This is a pure-Python review. It does not start OpticStudio, mutate scientific models,
or create TASK-008 formal carrier locks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.task007_review import MechanismDecision, review_task007_consolidated_payload

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    REPOSITORY_ROOT
    / "docs/evidence/task007/consolidated_batch/TASK_007_CONSOLIDATED_EVIDENCE.json"
)
DEFAULT_DECISIONS = (
    REPOSITORY_ROOT
    / "docs/evidence/task007/consolidated_review/TASK_007_MECHANISM_DECISIONS.json"
)
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "docs/evidence/task007/consolidated_review/TASK_007_CONSOLIDATED_REVIEW.json"
)
EXPECTED_SOURCE_EVIDENCE_SHA256 = (
    "88f89484d1684ce43005d5ce7a30feb88b485065962ee4df5ae517426a231c51"
)
EXPECTED_SOURCE_EVIDENCE_COMMIT = "a67288a4af1bdd4a9ec692c3b797f0e3e3469d9d"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON root must be an object: {path}")
    return payload


def main() -> None:
    args = _parser().parse_args()
    source = args.source.resolve()
    decisions_path = args.decisions.resolve()
    output = args.output.resolve()
    if not source.is_file() or not decisions_path.is_file():
        raise SystemExit("TASK-007 review requires both source evidence and mechanism decisions")
    if output.exists() and not args.overwrite:
        raise SystemExit(f"review output already exists; pass --overwrite: {output}")

    source_sha = _sha256(source)
    if source_sha != EXPECTED_SOURCE_EVIDENCE_SHA256:
        raise SystemExit(
            "TASK-007 consolidated evidence hash differs from the Web-reviewed source: "
            f"expected {EXPECTED_SOURCE_EVIDENCE_SHA256}, got {source_sha}"
        )
    source_payload = _load_object(source)
    decisions_payload = _load_object(decisions_path)
    if decisions_payload.get("source_evidence_commit") != EXPECTED_SOURCE_EVIDENCE_COMMIT:
        raise SystemExit("mechanism decisions reference the wrong source evidence commit")
    if decisions_payload.get("source_evidence_sha256") != source_sha:
        raise SystemExit("mechanism decisions reference the wrong source evidence hash")
    raw_decisions = decisions_payload.get("decisions")
    if not isinstance(raw_decisions, list):
        raise TypeError("mechanism decisions must be a list")
    decisions: list[MechanismDecision] = []
    for item in raw_decisions:
        if not isinstance(item, dict):
            raise TypeError("each mechanism decision must be an object")
        decisions.append(
            MechanismDecision(
                platform_id=str(item.get("platform_id") or ""),
                passed=item.get("passed") is True,
                reason=str(item.get("reason") or ""),
            )
        )

    result = review_task007_consolidated_payload(source_payload, tuple(decisions))
    payload = {
        **asdict(result),
        "source_evidence_sha256": source_sha,
        "source_evidence_commit": EXPECTED_SOURCE_EVIDENCE_COMMIT,
        "decision_file_sha256": _sha256(decisions_path),
        "review_scope": {
            "normative_low_order_gate": "STD_IOL_EYE_2024 EPD6 imported residual readback",
            "actual_eye_low_order_readback": "diagnostic only; source SSAG Mode 0 is aperture-limited",
            "actual_eye_hard_evidence": "ray health + through-focus + whole-eye wavefront/mechanism behavior",
        },
        "scientific_settings_changed": False,
        "residual_payload_changed": False,
        "requires_opticstudio_rerun": False,
        "next_task": "TASK-008 formal carrier/pair locks and exact 18/72 manifests",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not result.tdd_999_cleared:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
