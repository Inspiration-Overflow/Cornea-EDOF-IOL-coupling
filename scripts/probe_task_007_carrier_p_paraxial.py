"""Probe TASK-007 actual-eye carrier P solve and ZERO_HOA paraxial API capability.

This is diagnostic-only. It does not solve Q(P), calibrate residuals, or create formal locks.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.carrier_zos import (
    probe_paraxial_reference_surface,
    solve_actual_eye_carrier_power,
)
from whole_eye_mvp.carriers import sha256_path
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    BaseId,
    ScientificBaseline,
)
from whole_eye_mvp.standard_eye import ARTIFACT_ID as STANDARD_EYE_ARTIFACT_ID
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
DEFAULT_A0_RELATIVE_PATH = Path("diagnostics/task005d/corneas/CORNEA_A0.zmx")
OUTPUT_RELATIVE_DIR = Path("diagnostics/task007/carrier_p_paraxial_probe")
REPORT_NAME = "TASK_007_CARRIER_P_PARAXIAL_PROBE.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=os.environ.get(INSTALL_ENV),
        help=f"OpticStudio installation directory; defaults to {INSTALL_ENV}",
    )
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
    parser.add_argument("--a0-path", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
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
        raise SystemExit("TASK-007 probe requires a clean tracked Git checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _guard_outputs(paths: tuple[Path, ...], *, overwrite: bool) -> None:
    existing = tuple(path for path in paths if path.exists())
    if existing and not overwrite:
        text = ", ".join(str(path) for path in existing)
        raise SystemExit(f"Diagnostics already exist; pass --overwrite to replace them: {text}")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    code_commit = _clean_git_head()
    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(project_dir, baseline)

    standard_record = store.find_artifact(STANDARD_EYE_ARTIFACT_ID)
    if standard_record is None:
        raise SystemExit("Required locked STD_IOL_EYE_2024 artifact is not registered")
    if standard_record.relative_path != STANDARD_EYE_RELATIVE_PATH:
        raise SystemExit("Registered standard-eye path differs from the frozen project path")
    if not standard_record.locked or not store.verify_artifact(standard_record):
        raise SystemExit("Registered standard-eye artifact is not a valid immutable input")
    standard_eye_path = store.resolve(standard_record.relative_path)

    a0_path = (
        args.a0_path.resolve()
        if args.a0_path is not None
        else (project_dir / DEFAULT_A0_RELATIVE_PATH).resolve()
    )
    if not a0_path.is_file():
        raise SystemExit(f"Required A0 diagnostic cornea is missing: {a0_path}")

    output_dir = project_dir / OUTPUT_RELATIVE_DIR
    p_paths = {
        BaseId.LB_AL2395: output_dir / "TASK007_P_LB_A0.zmx",
        BaseId.ATC_M3_AL24477: output_dir / "TASK007_P_ATC_M3_A0.zmx",
    }
    report_path = output_dir / REPORT_NAME
    _guard_outputs((*p_paths.values(), report_path), overwrite=args.overwrite)

    power_results: dict[str, dict[str, object]] = {}
    with open_zos_session(args.install_dir) as session:
        for base_id, destination in p_paths.items():
            result = solve_actual_eye_carrier_power(
                session,
                baseline,
                base_id,
                a0_path,
                destination,
            )
            power_results[str(base_id)] = {
                "measurement": asdict(result),
                "candidate_path": str(destination.resolve()),
                "candidate_sha256": sha256_path(destination),
            }

        paraxial = probe_paraxial_reference_surface(session, standard_eye_path)

    payload = {
        "schema_version": 1,
        "formal_artifact": False,
        "phase": "TASK-007-A.1-P-SOLVE-PARAXIAL-CAPABILITY",
        "baseline_id": baseline.baseline_id,
        "code_commit": code_commit,
        "tdd_999_cleared": False,
        "q_solve_completed": False,
        "residual_calibration_completed": False,
        "inputs": {
            "a0_path": str(a0_path),
            "a0_sha256": sha256_path(a0_path),
            "standard_eye_path": str(standard_eye_path.resolve()),
            "standard_eye_sha256": sha256_path(standard_eye_path),
        },
        "power_solve": power_results,
        "paraxial_surface_capability": asdict(paraxial),
        "next_gate": (
            "Web review of Paraxial surface parameter headers before Q(P) implementation"
            if paraxial.passed
            else "STOP: Paraxial reference capability unavailable; return evidence to Web"
        ),
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report_path": str(report_path.resolve()), **payload}, ensure_ascii=False, indent=2))
    if not paraxial.passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
