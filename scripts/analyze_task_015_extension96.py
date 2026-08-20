"""Integrate accepted TASK-013 and TASK-014 evidence into the 96-config extension layer."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path

from whole_eye_mvp.extension96_analysis import (
    TASK013_EVIDENCE_COMMIT,
    TASK014_EVIDENCE_COMMIT,
    Task015Analysis,
    analyze_extension96,
    sha256_file,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK013_DIR = REPOSITORY_ROOT / "docs/evidence/task013"
DEFAULT_TASK014_DIR = REPOSITORY_ROOT / "docs/evidence/task014"
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "docs/evidence/task015"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task013-dir", type=Path, default=DEFAULT_TASK013_DIR)
    parser.add_argument("--task014-dir", type=Path, default=DEFAULT_TASK014_DIR)
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
        raise SystemExit("TASK-015 formal export requires a clean tracked checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty TASK-015 CSV: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _evidence_payload(
    analysis: Task015Analysis,
    *,
    code_commit: str,
    output_hashes: dict[str, str],
) -> dict[str, object]:
    statuses: dict[str, int] = {}
    for pair in analysis.pairs:
        statuses[pair.dof50_effect_status] = statuses.get(pair.dof50_effect_status, 0) + 1
    return {
        "schema_version": 1,
        "phase": "TASK-015-EXTENSION96-OFFLINE-INTEGRATION",
        "formal_scientific_lock": False,
        "analysis_code_commit": code_commit,
        "source_task013_evidence_commit": TASK013_EVIDENCE_COMMIT,
        "source_task014_evidence_commit": TASK014_EVIDENCE_COMMIT,
        "source_run_ids": dict(analysis.source_run_ids),
        "source_git_blob_sha1": dict(analysis.source_blob_sha1),
        "accepted_config_count": 96,
        "accepted_through_focus_row_count": 1440,
        "matched_pair_count": len(analysis.pairs),
        "n0_referenced_interaction_count": len(analysis.n0_interactions),
        "coupling_cell_count": len(analysis.coupling_matrix),
        "dof50_effect_status_counts": statuses,
        "pair_peak_censored_count": sum(pair.pair_peak_censored for pair in analysis.pairs),
        "delta_mtfa_at_zero_negative_pair_count": sum(
            pair.values["delta_mtfa_at_zero_d"] < 0 for pair in analysis.pairs
        ),
        "delta_tf_mtfa_mean_negative_pair_count": sum(
            pair.values["delta_tf_mtfa_mean"] < 0 for pair in analysis.pairs
        ),
        "source_reviews_required_and_passed": True,
        "reconstruction_gate_passed": True,
        "censor_propagation_passed": True,
        "opticstudio_used": False,
        "output_files": output_hashes,
    }


def main() -> None:
    args = _parser().parse_args()
    code_commit = _git_head()
    analysis = analyze_extension96(args.task013_dir.resolve(), args.task014_dir.resolve())
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pair_csv = output_dir / "TASK_015_PAIR_ANALYSIS.csv"
    interaction_csv = output_dir / "TASK_015_N0_REFERENCED_INTERACTIONS.csv"
    matrix_csv = output_dir / "TASK_015_COUPLING_MATRIX.csv"
    evidence_json = output_dir / "TASK_015_ANALYSIS_EVIDENCE.json"

    _write_csv(pair_csv, [pair.to_row() for pair in analysis.pairs])
    _write_csv(interaction_csv, list(analysis.n0_interactions))
    _write_csv(matrix_csv, list(analysis.coupling_matrix))

    output_hashes = {
        pair_csv.name: sha256_file(pair_csv),
        interaction_csv.name: sha256_file(interaction_csv),
        matrix_csv.name: sha256_file(matrix_csv),
    }
    evidence_json.write_text(
        json.dumps(
            _evidence_payload(analysis, code_commit=code_commit, output_hashes=output_hashes),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "TASK-015 extension96 offline integration PASS: "
        f"pairs={len(analysis.pairs)} interactions={len(analysis.n0_interactions)} "
        f"coupling_cells={len(analysis.coupling_matrix)}"
    )
    print(f"evidence={evidence_json.relative_to(REPOSITORY_ROOT)}")
    print(f"evidence_sha256={sha256_file(evidence_json)}")


if __name__ == "__main__":
    main()
