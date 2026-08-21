"""Run the post-human-audit R2/R3 OpticStudio gate in one local batch.

The batch intentionally stops before any EDoF mechanism fitting.  It builds two
curved-retina/physical-STOP base eyes, solves one Q=0 analytical A0 carrier per
base, converts each carrier into the three platform-specific degenerate Binary 4
MONO structures, and verifies analytical-vs-Binary4 equivalence at 3 and 5 mm
physical STOP diameters.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.carriers import sha256_path
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, BaseId, PlatformId, ScientificBaseline
from whole_eye_mvp.revision_base_zos import build_revision_base_asset, revision_base_prescriptions
from whole_eye_mvp.revision_binary4_zos import (
    DegenerateEquivalenceThresholds,
    build_degenerate_binary4_mono,
    compare_degenerate_binary4_to_analytical,
)
from whole_eye_mvp.revision_carrier_zos import build_revision_q0_analytical_carrier
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
DEFAULT_A0_RELATIVE_PATH = Path("diagnostics/task005d/corneas/CORNEA_A0.zmx")
OUTPUT_RELATIVE_DIR = Path("diagnostics/model_revision/r2_r3")
REPORT_NAME = "MODEL_REVISION_R2_R3_EVIDENCE.json"


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
        raise SystemExit("R2/R3 local gate requires a clean tracked Git checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _guard_outputs(output_dir: Path, *, overwrite: bool) -> None:
    report = output_dir / REPORT_NAME
    if report.exists() and not overwrite:
        raise SystemExit(f"R2/R3 evidence already exists; pass --overwrite: {report}")
    output_dir.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    code_commit = _clean_git_head()
    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    a0_path = (
        args.a0_path.resolve()
        if args.a0_path is not None
        else (project_dir / DEFAULT_A0_RELATIVE_PATH).resolve()
    )
    if not a0_path.is_file():
        raise SystemExit(f"Required A0 cornea input is missing: {a0_path}")

    output_dir = project_dir / OUTPUT_RELATIVE_DIR
    _guard_outputs(output_dir, overwrite=args.overwrite)
    report_path = output_dir / REPORT_NAME

    thresholds = DegenerateEquivalenceThresholds()
    base_results: dict[str, object] = {}
    carrier_results: dict[str, object] = {}
    binary_results: dict[str, object] = {}
    comparisons: list[dict[str, object]] = []

    with open_zos_session(args.install_dir) as session:
        for prescription in revision_base_prescriptions(baseline):
            base_id = str(prescription.source.base_spec.base_id)
            destination = output_dir / f"R2_BASE_{base_id}.zmx"
            result = build_revision_base_asset(session, prescription, destination)
            base_results[base_id] = {
                "measurement": asdict(result),
                "sha256": sha256_path(destination),
            }

        analytical_paths: dict[BaseId, Path] = {}
        for base_id in BaseId:
            destination = output_dir / f"R2_ANALYTICAL_Q0_{base_id}.zmx"
            result = build_revision_q0_analytical_carrier(
                session,
                baseline,
                base_id,
                a0_path,
                destination,
            )
            analytical_paths[base_id] = destination
            carrier_results[str(base_id)] = {
                "measurement": asdict(result),
                "sha256": sha256_path(destination),
            }

        for base_id, analytical_path in analytical_paths.items():
            for platform in PlatformId:
                destination = output_dir / f"R3_BINARY4_MONO_{base_id}_{platform}.zmx"
                build = build_degenerate_binary4_mono(
                    session,
                    base_id,
                    platform,
                    analytical_path,
                    destination,
                    pupil_diameter_mm=3.0,
                )
                key = f"{base_id}__{platform}"
                binary_results[key] = {
                    "measurement": asdict(build),
                    "sha256": sha256_path(destination),
                }
                for pupil in (3.0, 5.0):
                    comparison = compare_degenerate_binary4_to_analytical(
                        session,
                        base_id,
                        platform,
                        analytical_path,
                        destination,
                        pupil_diameter_mm=pupil,
                        thresholds=thresholds,
                    )
                    comparisons.append(
                        {
                            "pupil_diameter_mm": pupil,
                            **asdict(comparison),
                        }
                    )

    passed = all(bool(item["passed"]) for item in comparisons)
    payload = {
        "schema_version": 1,
        "formal_artifact": False,
        "phase": "MODEL-REVISION-R2-R3",
        "baseline_id": baseline.baseline_id,
        "code_commit": code_commit,
        "inputs": {
            "a0_path": str(a0_path),
            "a0_sha256": sha256_path(a0_path),
        },
        "equivalence_thresholds": asdict(thresholds),
        "revised_bases": base_results,
        "revised_q0_analytical_carriers": carrier_results,
        "binary4_degenerate_mono": binary_results,
        "equivalence": comparisons,
        "passed": passed,
        "next_gate": (
            "Web review; if accepted, proceed to R4 mechanism-fit pilot"
            if passed
            else "STOP: return full evidence to Web review; do not start R4"
        ),
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report_path": str(report_path.resolve()), **payload}, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
