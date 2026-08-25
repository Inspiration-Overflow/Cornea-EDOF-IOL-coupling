"""Acquire the prespecified 96-configuration supplemental through-focus matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path

from run_model_revision_r8_96 import (
    R6_R7_OUTPUT_RELATIVE,
    _opticstudio_version,
    _preflight_inputs,
    build_r8_plan,
    r8_contract_summary,
    validate_execution_authorization,
)

from whole_eye_mvp.analysis_zos_r8_direct import (
    build_direct_model_specs,
    run_r8_direct_acquisition,
    verify_direct_model_sources,
    write_r8_aggregate_outputs,
)
from whole_eye_mvp.domain import AnalysisSettings
from whole_eye_mvp.quality import settings_hash
from whole_eye_mvp.supplemental_artifacts import annotate_config_csv_with_original_window_mean
from whole_eye_mvp.supplemental_experiments import SUPPLEMENTAL_DEFOCUS_GRID
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
SUPPLEMENTAL_OUTPUT_RELATIVE = Path("diagnostics/supplemental_experiments/experiment1_96")
SUPPLEMENTAL_EVIDENCE_NAME = "SUPPLEMENTAL_EXPERIMENT_1_96_EVIDENCE.json"
SUPPLEMENTAL_CONFIG_NAME = "SUPPLEMENTAL_EXPERIMENT_1_CONFIG_RESULTS.csv"
SUPPLEMENTAL_THROUGH_FOCUS_NAME = "SUPPLEMENTAL_EXPERIMENT_1_THROUGH_FOCUS.csv"
SUPPLEMENTAL_PAIRED_NAME = "SUPPLEMENTAL_EXPERIMENT_1_PAIRED_DELTAS.csv"
SUPPLEMENTAL_PEAK_WINDOW_D = 1.0

SUPPLEMENTAL_ANALYSIS_SETTINGS = AnalysisSettings(
    settings_id="SUPPLEMENTAL_TF_MTF_555_v1",
    wavelength_nm=555.0,
    pupils_mm=(3.0, 5.0),
    defocus_start_d=1.0,
    defocus_stop_d=-5.0,
    defocus_step_d=-0.125,
    fft_mtf_sampling=128,
    fft_mtf_convergence_samplings=(64, 128, 256),
    fft_mtf_use_polarization=False,
    mtf_frequency_step_cpd=1.0,
    mtfa_max_cpd=60.0,
    mtf_sample_frequencies_cpd=(10.0, 20.0, 30.0, 40.0, 50.0, 60.0),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _validate_settings() -> None:
    SUPPLEMENTAL_ANALYSIS_SETTINGS.validate()
    actual = SUPPLEMENTAL_ANALYSIS_SETTINGS.defocus_grid()
    if actual != SUPPLEMENTAL_DEFOCUS_GRID:
        raise RuntimeError(
            f"supplemental settings drifted from the exact 49-plane grid: {actual}"
        )


def expected_artifacts() -> tuple[str, ...]:
    root = SUPPLEMENTAL_OUTPUT_RELATIVE
    return tuple(
        str(root / name).replace("\\", "/")
        for name in (
            SUPPLEMENTAL_EVIDENCE_NAME,
            SUPPLEMENTAL_CONFIG_NAME,
            SUPPLEMENTAL_THROUGH_FOCUS_NAME,
            SUPPLEMENTAL_PAIRED_NAME,
        )
    )


def execute(
    *,
    install_dir: Path,
    project_dir: Path,
    evidence_path: Path | None,
) -> dict[str, object]:
    _validate_settings()
    plan, model_hashes, source_evidence_path, preflight_status = _preflight_inputs(
        project_dir,
        evidence_path,
        SUPPLEMENTAL_ANALYSIS_SETTINGS,
    )
    specs = build_direct_model_specs(
        project_dir,
        plan,
        model_hashes,
        r6_r7_output_relative=R6_R7_OUTPUT_RELATIVE,
    )
    verify_direct_model_sources(specs)

    output_root = (project_dir / SUPPLEMENTAL_OUTPUT_RELATIVE).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"supplemental output directory is not empty: {output_root}")
    run_id = f"supplemental-1-{uuid.uuid4().hex}"

    with open_zos_session(install_dir) as session:
        opticstudio_version = _opticstudio_version(session)
        direct_run, diagnostics = run_r8_direct_acquisition(
            session,
            project_dir=project_dir,
            specs=specs,
            output_root=output_root,
            run_id=run_id,
            analysis_settings=SUPPLEMENTAL_ANALYSIS_SETTINGS,
            peak_search_window_d=SUPPLEMENTAL_PEAK_WINDOW_D,
        )

    aggregate_paths = write_r8_aggregate_outputs(
        direct_run,
        output_root=output_root,
        config_csv_name=SUPPLEMENTAL_CONFIG_NAME,
        through_focus_csv_name=SUPPLEMENTAL_THROUGH_FOCUS_NAME,
        paired_csv_name=SUPPLEMENTAL_PAIRED_NAME,
    )
    annotate_config_csv_with_original_window_mean(
        aggregate_paths["config_csv"], aggregate_paths["through_focus_csv"]
    )
    evidence = {
        "schema_version": 1,
        "formal_artifact": True,
        "experiment": "experiment_1_extended_through_focus",
        "task_id": "supplemental-experiments-20260824",
        "run_id": run_id,
        "code_commit": _git_head(),
        "opticstudio_version": opticstudio_version,
        "source_r6_r7_evidence_path": str(source_evidence_path),
        "source_r6_r7_evidence_sha256": _sha256(source_evidence_path),
        "source_model_sha256": dict(sorted(direct_run.source_model_sha256.items())),
        "analysis_settings_id": SUPPLEMENTAL_ANALYSIS_SETTINGS.settings_id,
        "analysis_settings_sha256": settings_hash(SUPPLEMENTAL_ANALYSIS_SETTINGS),
        "defocus_grid_retina_d": list(SUPPLEMENTAL_DEFOCUS_GRID),
        "original_comparison_window_retina_d": [
            value for value in SUPPLEMENTAL_DEFOCUS_GRID if -3.0 <= value <= 0.5
        ],
        "peak_search_window_d": SUPPLEMENTAL_PEAK_WINDOW_D,
        "config_count": len(direct_run.results),
        "matched_pair_count": len(direct_run.paired_deltas),
        "through_focus_rows": len(direct_run.through_focus_rows),
        "expected_artifacts": list(expected_artifacts()),
        "config_results_csv_sha256": _sha256(aggregate_paths["config_csv"]),
        "through_focus_csv_sha256": _sha256(aggregate_paths["through_focus_csv"]),
        "paired_deltas_csv_sha256": _sha256(aggregate_paths["paired_csv"]),
        "preflight": preflight_status,
        "config_diagnostics": diagnostics,
        "local_acquisition_passed": True,
        "manual_web_review_required": True,
    }
    evidence_path_out = output_root / SUPPLEMENTAL_EVIDENCE_NAME
    evidence_path_out.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "evidence_path": str(evidence_path_out),
        "run_id": run_id,
        "config_count": evidence["config_count"],
        "matched_pair_count": evidence["matched_pair_count"],
        "through_focus_rows": evidence["through_focus_rows"],
        "local_acquisition_passed": evidence["local_acquisition_passed"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-dir", type=Path, default=os.environ.get(INSTALL_ENV))
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument(
        "--r6-r7-evidence",
        type=Path,
        help="Optional explicit R6/R7 evidence JSON; defaults to project diagnostics.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan-only", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    parser.add_argument("--authorization-id")
    return parser


def main() -> None:
    args = _parser().parse_args()
    project_dir = args.project_dir.resolve()
    if args.plan_only:
        _validate_settings()
        payload = r8_contract_summary(
            build_r8_plan(SUPPLEMENTAL_ANALYSIS_SETTINGS),
            analysis_settings=SUPPLEMENTAL_ANALYSIS_SETTINGS,
        )
    elif args.preflight:
        _validate_settings()
        payload = _preflight_inputs(
            project_dir,
            args.r6_r7_evidence,
            SUPPLEMENTAL_ANALYSIS_SETTINGS,
        )[3]
    else:
        validate_execution_authorization(args.authorization_id)
        if args.install_dir is None:
            raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")
        payload = execute(
            install_dir=Path(args.install_dir).resolve(),
            project_dir=project_dir,
            evidence_path=args.r6_r7_evidence,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
