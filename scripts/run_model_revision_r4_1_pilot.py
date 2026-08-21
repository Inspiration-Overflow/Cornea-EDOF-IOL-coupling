"""Run the R4.1 RAD spherical-power fidelity pilot and stop for Web review.

WFS and HOA rerun the unchanged R4 implementation on the same HEAD. RAD keeps the
R4-selected ``R+Q+A4`` topology but refits it to a paraxial proxy for spherical
POWP. Real OpticStudio POWP is the independent serialized/full-ray mechanism
validation. No R6/R7 or production expansion is authorized by this script.
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
    rad_powp_improves_source,
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
                f"R4.1 requires source R4 evidence {key}={value!r}; "
                f"got {payload.get(key)!r}"
            )
    local_checks = payload.get("local_checks")
    if not isinstance(local_checks, dict) or local_checks.get("local_pilot_passed") is not True:
        raise SystemExit("R4.1 requires the source R4 local execution gate to have passed")
    platforms = payload.get("platforms")
    if not isinstance(platforms, dict) or not isinstance(platforms.get("RAD"), dict):
        raise SystemExit("R4.1 source R4 evidence is missing RAD platform data")
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


def _rad_summary(result) -> dict[str, object]:
    fit = result.fit
    power = fit.selected.spherical_power
    mechanism = result.mechanism_readback
    readback = result.rad_power_readback
    if readback is None:
        raise SystemExit("R4.1 RAD result is missing POWP readback")
    return {
        "platform_id": result.platform_id,
        "representative_power_d": result.analytical.representative_power_d,
        "q_ant": result.analytical.q_ant,
        "selected_complexity": fit.selected_complexity,
        "fit_valid": fit.fit_valid,
        "fit_primary_quantity": fit.target_definition,
        "fit_spherical_power_proxy_rms_error_d": power.rms_error_d,
        "fit_spherical_power_proxy_max_abs_error_d": power.max_abs_error_d,
        "fit_spherical_power_proxy_rms_fraction": power.rms_fraction_of_target,
        "fit_spherical_power_proxy_max_fraction": power.max_fraction_of_target,
        "historical_integrated_opd_fit_rms_fraction": (
            fit.selected.historical_integrated_opd_rms_fraction
        ),
        "historical_integrated_opd_fit_max_fraction": (
            fit.selected.historical_integrated_opd_max_fraction
        ),
        "serialized_integrated_opd_diagnostic": {
            "engineering_target_passed": mechanism.engineering_target_passed,
            "rms_fraction": mechanism.rms_fraction_of_target,
            "max_fraction": mechanism.max_fraction_of_target,
            "role": "historical diagnostic only in R4.1; not a RAD mechanism gate",
        },
        "low_order_piston_um_diagnostic": mechanism.low_order_piston_um,
        "low_order_global_defocus_d": mechanism.low_order_global_defocus_d,
        "rad_power_rms_error_d": readback.rms_error_d,
        "rad_power_max_abs_error_d": readback.max_abs_error_d,
        "ray_health": {
            "mono": result.mono_audit.ray_health_passed,
            "binary4_edof": result.binary4_edof_audit.ray_health_passed,
            "grid_sag_edof": result.grid_sag_edof_audit.ray_health_passed,
        },
        "manual_web_review_required": True,
        "raw": asdict(result),
    }


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
        raw_results = {}
        platform_results: dict[str, dict[str, object]] = {}
        for platform in PlatformId:
            result = run_r4_1_platform_pilot(
                session,
                standard_eye,
                platform.value,
                q_solutions[platform.value],
                output_dir,
            )
            raw_results[platform.value] = result
            platform_results[platform.value] = (
                _rad_summary(result)
                if platform == PlatformId.RAD
                else r4_platform_summary(result)
            )

    source_rad = source_r4["platforms"]["RAD"]
    source_rms = float(source_rad["rad_power_rms_error_d"])
    source_max = float(source_rad["rad_power_max_abs_error_d"])
    rad_result = raw_results[PlatformId.RAD.value]
    rad_rms_improved, rad_max_improved = rad_powp_improves_source(
        rad_result,
        source_rms_error_d=source_rms,
        source_max_abs_error_d=source_max,
    )
    rad_sign_passed = rad_powp_sign_consistent(rad_result)

    wfs_hoa_engineering_passed = all(
        platform_results[platform.value]["fit_engineering_target_passed"] is True
        and platform_results[platform.value]["serialized_mechanism_target_passed"] is True
        for platform in (PlatformId.WFS, PlatformId.HOA)
    )
    rad_fit_valid = bool(platform_results[PlatformId.RAD.value]["fit_valid"])
    ray_health_all_passed = all(
        all(bool(value) for value in row["ray_health"].values())
        for row in platform_results.values()
    )
    defocus_reference_all_passed = all(
        abs(float(row["low_order_global_defocus_d"]))
        <= HISTORICAL_GLOBAL_DEFOCUS_TOLERANCE_D
        for row in platform_results.values()
    )
    local_pilot_passed = (
        wfs_hoa_engineering_passed
        and rad_fit_valid
        and ray_health_all_passed
        and defocus_reference_all_passed
        and rad_sign_passed
        and rad_rms_improved
        and rad_max_improved
    )

    payload = {
        "schema_version": 2,
        "formal_artifact": False,
        "pilot": True,
        "phase": "MODEL-REVISION-R4.1-RAD-SPHERICAL-POWER-PILOT",
        "code_commit": code_commit,
        "source_r4": {
            "path": str(source_r4_path.resolve()),
            "sha256": sha256_path(source_r4_path),
            "execution_commit": SOURCE_R4_EXECUTION_COMMIT,
            "source_local_pilot_passed": source_r4["local_checks"]["local_pilot_passed"],
            "web_review": "REVISE: WFS ACCEPT; RAD REVISE; HOA PROVISIONAL ACCEPT",
            "rejected_rad_powp_rms_error_d": source_rms,
            "rejected_rad_powp_max_abs_error_d": source_max,
        },
        "standard_eye": {
            "path": str(standard_eye),
            "sha256": sha256_path(standard_eye),
            "role": (
                "mechanism-calibration domain only; EPD6 is not a main-study "
                "physical-pupil definition"
            ),
        },
        "representative_carrier": {
            "power_d": R4_REPRESENTATIVE_POWER_D,
            "symmetric_biconvex_radius_mm": representative_radius_mm(),
        },
        "r4_1_revision_policy": {
            "scope": "RAD fit objective only; WFS and HOA rerun unchanged",
            "rad_complexity_held_at_r4_selected_level": "R+Q+A4",
            "rad_primary_fit_quantity": "source-locked local spherical power P(r)",
            "rad_fit_proxy": (
                "paraxial mean of local tangential d2W/dr2 and sagittal "
                "(1/r)dW/dr principal powers; r=0 uses curvature limit"
            ),
            "powp_role": "independent OpticStudio serialized/full-ray validation",
            "powp_absolute_magnitude_is_manual_web_review": True,
            "powp_nonzero_target_sign_is_local_hard_identity_check": True,
            "powp_rms_and_max_must_improve_vs_rejected_r4": True,
            "new_absolute_powp_acceptance_threshold_added": False,
            "rad_old_integrated_opd_is_historical_diagnostic_only": True,
            "wfs_hoa_existing_engineering_targets_unchanged": True,
            "existing_serialization_slack_unchanged_for_wfs_hoa": True,
            "mtf_used_in_fit_objective": False,
            "zone_boundaries_changed": False,
            "binary4_parameter_semantics_changed": False,
        },
        "low_order_policy": {
            "historical_global_defocus_tolerance_d": (
                HISTORICAL_GLOBAL_DEFOCUS_TOLERANCE_D
            ),
            "global_defocus_is_local_hard_reference": True,
            "surface_piston_is_diagnostic_only": True,
        },
        "platforms": platform_results,
        "local_checks": {
            "wfs_hoa_existing_engineering_targets_passed": wfs_hoa_engineering_passed,
            "rad_fit_valid": rad_fit_valid,
            "ray_health_all_passed": ray_health_all_passed,
            "defocus_reference_all_passed": defocus_reference_all_passed,
            "rad_powp_sign_identity_passed": rad_sign_passed,
            "rad_powp_rms_improved_vs_rejected_r4": rad_rms_improved,
            "rad_powp_max_improved_vs_rejected_r4": rad_max_improved,
            "local_pilot_passed": local_pilot_passed,
        },
        "artifact_sha256": {},
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
        "next_gate": (
            "STOP for Web R4.1 review; do not start R6/R7 or production expansion"
            if local_pilot_passed
            else "STOP: R4.1 did not clear local identity/regression checks; return evidence to Web"
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
                "rad_powp_sign_identity_passed": rad_sign_passed,
                "rad_powp_rms_improved_vs_rejected_r4": rad_rms_improved,
                "rad_powp_max_improved_vs_rejected_r4": rad_max_improved,
                "platform_summary": {
                    platform: {
                        "selected_complexity": row["selected_complexity"],
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
