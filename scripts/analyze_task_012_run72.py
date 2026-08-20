"""Run the frozen TASK-012 pure-offline analysis on formal TASK-011 evidence."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path

from whole_eye_mvp.run72_analysis import (
    TASK011_RECORDED_EXPORT_HASHES,
    TASK012_ANALYSIS_PLAN,
    TASK012_ANALYSIS_PLAN_ID,
    TASK012_SOURCE_COMMIT,
    Task012Analysis,
    analyze_evidence,
    sha256_file,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_DIR = REPOSITORY_ROOT / "docs/evidence/task011"
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "docs/evidence/task012"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def _git_head() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise SystemExit("TASK-012 formal export requires a clean tracked checkout")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(head) != 40:
        raise SystemExit("TASK-012 could not resolve a canonical Git commit")
    return head


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty TASK-012 CSV: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_evidence_payload(
    analysis: Task012Analysis,
    *,
    code_commit: str,
    plan_sha256: str,
    output_hashes: dict[str, str],
) -> dict[str, object]:
    status_counts: dict[str, int] = {}
    for pair in analysis.pairs:
        status_counts[pair.dof50_effect_status] = status_counts.get(pair.dof50_effect_status, 0) + 1
    return {
        "schema_version": 1,
        "phase": "TASK-012-OFFLINE-ANALYSIS",
        "formal_scientific_lock": False,
        "source_task011_commit": TASK012_SOURCE_COMMIT,
        "source_task011_repository_sha256": dict(analysis.source_hashes),
        "source_task011_recorded_producer_export_sha256": dict(TASK011_RECORDED_EXPORT_HASHES),
        "analysis_code_commit": code_commit,
        "analysis_plan_id": TASK012_ANALYSIS_PLAN_ID,
        "analysis_plan_path": TASK012_ANALYSIS_PLAN,
        "analysis_plan_sha256": plan_sha256,
        "pair_count": len(analysis.pairs),
        "contrast_count": len(analysis.contrasts),
        "coupling_cell_count": len(analysis.coupling_matrix),
        "dof50_effect_status_counts": status_counts,
        "peak_censored_pair_count": sum(pair.pair_peak_censored for pair in analysis.pairs),
        "reconstruction_gate_passed": True,
        "censor_propagation_passed": True,
        "opticstudio_used": False,
        "output_files": output_hashes,
    }


def main() -> None:
    args = _parser().parse_args()
    evidence_dir = args.evidence_dir.resolve()
    output_dir = args.output_dir.resolve()
    code_commit = _git_head()

    analysis = analyze_evidence(evidence_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pair_csv = output_dir / "TASK_012_PAIR_ANALYSIS.csv"
    contrast_csv = output_dir / "TASK_012_INTERACTION_CONTRASTS.csv"
    coupling_csv = output_dir / "TASK_012_COUPLING_MATRIX.csv"
    evidence_json = output_dir / "TASK_012_ANALYSIS_EVIDENCE.json"

    _write_csv(pair_csv, [pair.to_row() for pair in analysis.pairs])
    _write_csv(contrast_csv, list(analysis.contrasts))
    _write_csv(coupling_csv, list(analysis.coupling_matrix))

    plan_path = REPOSITORY_ROOT / TASK012_ANALYSIS_PLAN
    if not plan_path.is_file():
        raise SystemExit(f"TASK-012 analysis plan is missing: {TASK012_ANALYSIS_PLAN}")

    output_hashes = {
        pair_csv.name: sha256_file(pair_csv),
        contrast_csv.name: sha256_file(contrast_csv),
        coupling_csv.name: sha256_file(coupling_csv),
    }
    evidence = build_evidence_payload(
        analysis,
        code_commit=code_commit,
        plan_sha256=sha256_file(plan_path),
        output_hashes=output_hashes,
    )
    evidence_json.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "TASK-012 offline analysis PASS: "
        f"pairs={len(analysis.pairs)} contrasts={len(analysis.contrasts)} "
        f"coupling_cells={len(analysis.coupling_matrix)}"
    )
    print(f"evidence={evidence_json.relative_to(REPOSITORY_ROOT)}")
    print(f"evidence_sha256={sha256_file(evidence_json)}")


if __name__ == "__main__":
    main()
