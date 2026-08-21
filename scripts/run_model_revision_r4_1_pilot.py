"""Run the R4.1 RAD power-fidelity revision pilot and stop for Web review.

WFS and HOA are rerun unchanged from accepted/provisional R4 behavior so all three
platforms are captured on one HEAD. RAD alone changes its fit objective from the
integrated OPD surrogate to the source-locked local radial power P(r). Existing
2%/5% OPD engineering gates, serialization slack, physical definitions and optical
audit settings remain unchanged. POWP magnitude remains a Web-review quantity.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.carriers import sha256_path
from whole_eye_mvp.domain import PlatformId
from whole_eye_mvp.revision_r4_1_zos import (
    rad_powp_sign_consistent,
    run_r4_1_platform_pilot,
)
from whole_eye_mvp.revision_r4_fit import R4_REPRESENTATIVE_POWER_D, representative_radius_mm
from whole_eye_mvp.revision_r4_zos import r4_platform_summary, solve_r4_platform_qs
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
OUTPUT_RELATIVE_DIR = Path("diagnostics/model_revision/r4_1_pilot")
REPORT_NAME = "MODEL_REVISION_R4_1_PILOT_EVIDENCE.json"
SOURCE_R4_REPORT_RELATIVE_PATH = Path(
    "diagnostics/model_revision/r4_pilot/MODEL_REVISION_R4_PILOT_EVIDENCE.json"
)
SOURCE_R4_EXECUTION_COMMIT = "a8f5ab5d575008adcecd76446324d1674d7b90b7"
HISTORICAL_GLOBAL_DEFOCUS_TOLERANCE_D = 0.125


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=os.environ.get(INSTALL_ENV),
        help=f"OpticStudio installation directory; defaults to {INSTALL_ENV}",
    )
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--standard-eye-path", type=Path, default=None)
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
        raise SystemExit("R4.1 local pilot requires a clean tracked Git checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load_source_r4(project_dir: Path) -> tuple[Path, dict[str, object]]:
    path = project_dir / SOURCE_R4_REPORT_RELATIVE_PATH
    if not path.is_file():
        raise SystemExit(f"source R4 evidence is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("source R4 evidence root is not a JSON object")
    expected = {
        "schema_version": 1,
        "phase": "MODEL-REVISION-R4-MECHANISM-PILOT",
        "code_commit": SOURCE_R4_EXECUTION_COMMIT,
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise SystemExit(
                f"R4.1 requires source R4 evidence {key}={value!r}; got {payload.get(key)!r}"
            )
    local_checks = payload.get("local_checks")
    if not isinstance(local_checks, dict) or local_checks.get("local_pilot_passed") is not True:
        raise SystemExit("R4.1 requires the source R4 local execution gate to have passed")
    return path, payload


def _guard_output(output_dir: Path, overwrite: bool) -> Path:
    report = output_dir / REPORT_NAME
    if report.exists() and not overwrite:
        raise SystemExit(f"R4.1 pilot evidence already exists; pass --overwrite: {report}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return report


def _artifact_hashes(output_dir: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != REPORT_NAME:
            rows[path.name] = sha256_path(path)
    return rows


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    code_commit = _clean_git_head()
    project_dir = args.project_dir.resolve()
    source_r4_path, source_r4 = _load_source_r4(project_dir)
    standard_eye = (
        args.standard_eye_path.resolve()
        if args.standard_eye_path is not None
        else (project_dir / STANDARD_EYE_RELATIVE_PATH).resolve()
    )
    if not standard_eye.is_file():
        raise SystemExit(f"STD_IOL_EYE_2024 input is missing: {standard_eye}")
    output_dir = project_dir / OUTPUT_RELATIVE_DIR
    report_path = _guard_output(output_dir, args.overwrite)

    with open_zos_session(args.install_dir) as session:
        q_solutions = solve_r4_platform_qs(session, standard_eye)
        platform_results: dict[str, dict[str, object]] = {}
        raw_results = {}
        for platform in PlatformId:
            result, rad_fit_power = run_r4_1_platform_pilot(
                session,
                standard_eye,
                platform.value,
                q_solutions[platform.value],
                output_dir,
            )
            raw_results[platform.value] = result
            summary = r4_platform_summary(result)
            if rad_fit_power is not None:
                summary["r4_1_rad_fit_power_diagnostics"] = [
                    asdict(item) for item in rad_fit_power
                ]
                summary["r4_1_rad_selected_power_diagnostic"] = asdict(rad_fit_power[-1])
            platform_results[platform.value] = summary

    engineering_targets_all_passed = all(
        row["fit_engineering_target_passed"] is True
        and row["serialized_mechanism_target_passed"] is True
        for row in platform_results.values()
    )
    ray_health_all_passed = all(
        all(bool(value) for value in row["ray_health"].values())
        for row in platform_results.values()
    )
    defocus_reference_all_passed = all(
        abs(float(row["low_order_global_defocus_d"]))
        <= HISTORICAL_GLOBAL_DEFOCUS_TOLERANCE_D
        for row in platform_results.values()
    )
    rad_powp_sign_identity_passed = rad_powp_sign_consistent(raw_results[PlatformId.RAD.value])
    local_pilot_passed = (
        engineering_targets_all_passed
        and ray_health_all_passed
        and defocus_reference_all_passed
        and rad_powp_sign_identity_passed
    )

    payload = {
        "schema_version": 1,
        "formal_artifact": False,
        "pilot": True,
        "phase": "MODEL-REVISION-R4.1-RAD-POWER-FIDELITY-PILOT",
        "code_commit": code_commit,
        "source_r4": {
            "path": str(source_r4_path.resolve()),
            "sha256": sha256_path(source_r4_path),
            "execution_commit": SOURCE_R4_EXECUTION_COMMIT,
            "source_local_pilot_passed": source_r4["local_checks"]["local_pilot_passed"],
            "web_review": "REVISE: WFS ACCEPT; RAD REVISE; HOA PROVISIONAL ACCEPT",
        },
        "standard_eye": {
            "path": str(standard_eye),
            "sha256": sha256_path(standard_eye),
            "role": "mechanism-calibration domain only; EPD6 is not a main-study physical-pupil definition",
        },
        "representative_carrier": {
            "power_d": R4_REPRESENTATIVE_POWER_D,
            "symmetric_biconvex_radius_mm": representative_radius_mm(),
        },
        "r4_1_revision_policy": {
            "scope": "RAD fit objective only; WFS and HOA rerun unchanged",
            "rad_primary_fit_quantity": "source-locked local radial power P(r)",
            "rad_fit_proxy": "P(r)=(1/r)dW/dr from Binary4 surface slope; r=0 uses curvature limit",
            "powp_role": "independent OpticStudio serialized/full-ray validation",
            "powp_magnitude_is_manual_web_review": True,
            "powp_nonzero_target_sign_is_local_hard_identity_check": True,
            "new_numeric_acceptance_thresholds_added": False,
            "existing_opd_engineering_targets_unchanged": True,
            "existing_serialization_slack_unchanged": True,
            "mtf_used_in_fit_objective": False,
            "zone_boundaries_changed": False,
            "binary4_parameter_semantics_changed": False,
        },
        "low_order_policy": {
            "historical_global_defocus_tolerance_d": HISTORICAL_GLOBAL_DEFOCUS_TOLERANCE_D,
            "global_defocus_is_local_hard_reference": True,
            "surface_piston_is_diagnostic_only": True,
        },
        "platforms": platform_results,
        "local_checks": {
            "engineering_targets_all_passed": engineering_targets_all_passed,
            "ray_health_all_passed": ray_health_all_passed,
            "defocus_reference_all_passed": defocus_reference_all_passed,
            "rad_powp_sign_identity_passed": rad_powp_sign_identity_passed,
            "local_pilot_passed": local_pilot_passed,
        },
        "artifact_sha256": {},
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
        "next_gate": (
            "STOP for Web R4.1 review; do not start R6/R7 or production expansion"
            if local_pilot_passed
            else "STOP: R4.1 pilot did not clear local engineering/identity checks; return evidence to Web"
        ),
    }
    payload["artifact_sha256"] = _artifact_hashes(output_dir)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "report_path": str(report_path.resolve()),
                "local_pilot_passed": local_pilot_passed,
                "manual_web_review_required": True,
                "rad_powp_sign_identity_passed": rad_powp_sign_identity_passed,
                "platform_summary": {
                    platform: {
                        "selected_complexity": row["selected_complexity"],
                        "serialized_rms_fraction": row["serialized_rms_fraction"],
                        "serialized_max_fraction": row["serialized_max_fraction"],
                        "low_order_global_defocus_d": row["low_order_global_defocus_d"],
                        "rad_power_rms_error_d": row["rad_power_rms_error_d"],
                        "rad_power_max_abs_error_d": row["rad_power_max_abs_error_d"],
                    }
                    for platform, row in platform_results.items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not local_pilot_passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
