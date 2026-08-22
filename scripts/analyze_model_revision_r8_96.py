"""Validate, integrate, and render the R8 96-config production export."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from whole_eye_mvp.r8_analysis import (
    R8AnalysisError,
    build_coupling_matrix,
    build_n0_interactions,
    build_pairs,
    load_configs,
    validate_factorial,
    validate_paired_deltas,
    validate_through_focus,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_R8_DIR = (
    REPOSITORY_ROOT
    / "project_mvp_2026_v2_zmx"
    / "diagnostics"
    / "model_revision"
    / "r8_96"
)
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "docs" / "evidence" / "r8_96"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r8-dir", type=Path, default=DEFAULT_R8_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-figures", action="store_true")
    return parser


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise R8AnalysisError(f"cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _figure_generation(analysis, *, r8_dir: Path, output_dir: Path) -> list[str]:
    """Reuse the reviewed figure renderer with R8's exact factor labels."""
    import whole_eye_mvp.extension96_figures as figures

    figures.BASE_IDS = ("LB_AL2395", "ATC_M3_AL24477")
    figures.CORNEA_IDS = ("N0", "A0", "B0", "C0")
    figures.PLATFORM_IDS = ("WFS", "RAD", "HOA")
    figures.PUPIL_MM = (3.0, 5.0)
    paths = figures.generate_task015_figures(
        analysis,
        through_focus_csvs=(r8_dir / "MODEL_REVISION_R8_96_THROUGH_FOCUS.csv",),
        output_dir=output_dir / "figures",
    )
    return [path.relative_to(output_dir).as_posix() for path in paths]


def main() -> None:
    args = _parser().parse_args()
    r8_dir = args.r8_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = r8_dir / "MODEL_REVISION_R8_96_EVIDENCE.json"
    config_path = r8_dir / "MODEL_REVISION_R8_96_CONFIG_RESULTS.csv"
    through_focus_path = r8_dir / "MODEL_REVISION_R8_96_THROUGH_FOCUS.csv"
    paired_path = r8_dir / "MODEL_REVISION_R8_96_PAIRED_DELTAS.csv"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not evidence.get("local_r8_passed") or evidence.get("failed_configs") != 0:
        raise R8AnalysisError("R8 production evidence is not a local PASS")

    configs = load_configs(config_path)
    validate_factorial(configs)
    validate_through_focus(through_focus_path, configs)
    pairs = build_pairs(configs)
    validate_paired_deltas(paired_path, pairs)
    n0_interactions = build_n0_interactions(pairs)
    coupling_matrix = build_coupling_matrix(pairs)

    from whole_eye_mvp.extension96_analysis import Task015Analysis

    analysis = Task015Analysis(
        pairs=pairs,
        n0_interactions=n0_interactions,
        coupling_matrix=coupling_matrix,
        source_blob_sha1={},
        source_run_ids={"r8": str(evidence["run_id"])},
    )
    pair_csv = output_dir / "MODEL_REVISION_R8_96_PAIR_ANALYSIS.csv"
    matrix_csv = output_dir / "MODEL_REVISION_R8_96_COUPLING_MATRIX.csv"
    _write_csv(pair_csv, [pair.to_row() for pair in pairs])
    _write_csv(matrix_csv, list(coupling_matrix))

    statuses = Counter(pair.dof50_effect_status for pair in pairs)
    outcomes = (
        "delta_dof50_width_d",
        "delta_distance_peak_mtfa",
        "delta_mtfa_at_zero_d",
        "delta_tf_mtfa_mean",
        "delta_c40_um",
        "delta_c60_um",
        "delta_hoa_rms_um",
        "delta_f_residual_d",
    )
    summary_stats = {
        outcome: {
            "mean": sum(pair.values[outcome] for pair in pairs) / len(pairs),
            "min": min(pair.values[outcome] for pair in pairs),
            "max": max(pair.values[outcome] for pair in pairs),
            "negative_count": sum(pair.values[outcome] < 0 for pair in pairs),
            "positive_count": sum(pair.values[outcome] > 0 for pair in pairs),
        }
        for outcome in outcomes
    }
    figure_refs: list[str] = []
    if not args.no_figures:
        figure_refs = _figure_generation(analysis, r8_dir=r8_dir, output_dir=output_dir)
    payload = {
        "schema_version": 1,
        "phase": "MODEL-REVISION-R8-96-OFFLINE-INTEGRATION",
        "formal_scientific_lock": False,
        "analysis_code_commit": _git_head(),
        "source_r8_evidence_sha256": _sha256(evidence_path),
        "source_r8_run_id": evidence["run_id"],
        "source_r8_code_commit": evidence["code_commit"],
        "source_r5_freeze_id": evidence["r5_freeze_id"],
        "source_acquisition_contract_id": evidence["acquisition_contract_id"],
        "source_frequency_scale_mode": evidence["frequency_scale_mode"],
        "source_production_sampling": evidence["production_sampling"],
        "accepted_config_count": len(configs),
        "accepted_through_focus_row_count": 1440,
        "matched_pair_count": len(pairs),
        "n0_referenced_interaction_count": len(n0_interactions),
        "coupling_cell_count": len(coupling_matrix),
        "dof50_effect_status_counts": dict(statuses),
        "peak_censored_pair_count": sum(pair.pair_peak_censored for pair in pairs),
        "summary_stats": summary_stats,
        "pair_analysis_sha256": _sha256(pair_csv),
        "coupling_matrix_sha256": _sha256(matrix_csv),
        "figure_count": len(figure_refs),
        "figure_refs": figure_refs,
        "reconstruction_gate_passed": True,
        "censor_propagation_passed": True,
        "opticstudio_used": False,
    }
    evidence_out = output_dir / "MODEL_REVISION_R8_96_OFFLINE_ANALYSIS_EVIDENCE.json"
    evidence_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        "R8 offline integration PASS: "
        f"configs={len(configs)} pairs={len(pairs)} interactions={len(n0_interactions)} "
        f"figures={len(figure_refs)}"
    )
    print(f"evidence={evidence_out.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
