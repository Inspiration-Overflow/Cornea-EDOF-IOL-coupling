"""Run the R4.2 RAD low-order constrained spherical-power pilot.

R4.2 preserves the R4.1 local spherical-power correction but constrains the RAD
Binary4 residual to the frozen source's own low-order global defocus. WFS and HOA
rerun unchanged. Real OpticStudio spherical POWP remains the final mechanism
validation, and this script always stops before R6/R7 or production expansion.
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
)
from whole_eye_mvp.revision_r4_2_rad_fit import (
    R4_2_GLOBAL_DEFOCUS_TOLERANCE_D,
    fit_r4_2_rad_mechanism,
)
from whole_eye_mvp.revision_r4_2_zos import run_r4_2_platform_pilot
from whole_eye_mvp.revision_r4_fit import R4_REPRESENTATIVE_POWER_D, representative_radius_mm
from whole_eye_mvp.revision_r4_zos import r4_platform_summary, solve_r4_platform_qs
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
OUTPUT_RELATIVE_DIR = Path("diagnostics/model_revision/r4_2_pilot")
REPORT_NAME = "MODEL_REVISION_R4_2_PILOT_EVIDENCE.json"
SOURCE_R4_1_REPORT_RELATIVE_PATH = Path(
    "diagnostics/model_revision/r4_1_pilot/MODEL_REVISION_R4_1_PILOT_EVIDENCE.json"
)
SOURCE_R4_1_EXECUTION_COMMIT = "f0332eea21921ba4aa7ce43ae0fa5e290bb55ba2"


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
        raise SystemExit("R4.2 local pilot requires a clean tracked Git checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load_source_r4_1(project_dir: Path) -> tuple[Path, dict[str, object]]:
    path = project_dir / SOURCE_R4_1_REPORT_RELATIVE_PATH
    if not path.is_file():
        raise SystemExit(f"source R4.1 evidence is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("source R4.1 evidence root is not a JSON object")
    expected = {
        "schema_version": 2,
        "phase": "MODEL-REVISION-R4.1-RAD-SPHERICAL-POWER-PILOT",
        "code_commit": SOURCE_R4_1_EXECUTION_COMMIT,
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise SystemExit(
                f"R4.2 requires source R4.1 evidence {key}={value!r}; "
                f"got {payload.get(key)!r}"
            )

    checks = payload.get("local_checks")
    if not isinstance(checks, dict):
        raise SystemExit("source R4.1 evidence is missing local_checks")
    required_true = (
        "wfs_hoa_existing_engineering_targets_passed",
        "rad_fit_valid",
        "ray_health_all_passed",
        "rad_powp_sign_identity_passed",
        "rad_powp_rms_improved_vs_rejected_r4",
        "rad_powp_max_improved_vs_rejected_r4",
    )
    for key in required_true:
        if checks.get(key) is not True:
            raise SystemExit(f"R4.2 source R4.1 prerequisite {key} did not pass")
    if checks.get("defocus_reference_all_passed") is not False:
        raise SystemExit("R4.2 requires R4.1 to have failed the defocus reference")
    if checks.get("local_pilot_passed") is not False:
        raise SystemExit("R4.2 requires the source R4.1 local pilot to be a FAIL")

    platforms = payload.get("platforms")
    if not isinstance(platforms, dict) or not isinstance(platforms.get("RAD"), dict):
        raise SystemExit("R4.2 source R4.1 evidence is missing RAD platform data")
    rad_defocus = float(platforms["RAD"]["low_order_global_defocus_d"])
    if abs(rad_defocus) <= R4_2_GLOBAL_DEFOCUS_TOLERANCE_D:
        raise SystemExit("R4.2 source R4.1 RAD defocus does not reproduce the known failure")
    return path, payload


def _guard_output(output_dir: Path, overwrite: bool) -> Path:
    report = output_dir / REPORT_NAME
    if report.exists() and not overwrite:
        raise SystemExit(f"R4.2 pilot evidence already exists; pass --overwrite: {report}")
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
    low_order = fit.selected.low_order
    mechanism = result.mechanism_readback
    readback = result.rad_power_readback
    if readback is None:
        raise SystemExit("R4.2 RAD result is missing POWP readback")
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
        "fit_source_low_order": asdict(low_order),
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
            "role": "historical diagnostic only; not a RAD mechanism gate",
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
    source_r4_1_path, source_r4_1 = _load_source_r4_1(project_dir)
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
            result = run_r4_2_platform_pilot(
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

    source_r4 = source_r4_1.get("source_r4")
    if not isinstance(source_r4, dict):
        raise SystemExit("source R4.1 evidence is missing rejected R4 baseline metadata")
    rejected_r4_rms = float(source_r4["rejected_rad_powp_rms_error_d"])
    rejected_r4_max = float(source_r4["rejected_rad_powp_max_abs_error_d"])
    source_r4_1_rad = source_r4_1["platforms"]["RAD"]
    source_r4_1_rms = float(source_r4_1_rad["rad_power_rms_error_d"])
    source_r4_1_max = float(source_r4_1_rad["rad_power_max_abs_error_d"])

    rad_result = raw_results[PlatformId.RAD.value]
    rad_rms_improved, rad_max_improved = rad_powp_improves_source(
        rad_result,
        source_rms_error_d=rejected_r4_rms,
        source_max_abs_error_d=rejected_r4_max,
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
        <= R4_2_GLOBAL_DEFOCUS_TOLERANCE_D
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

    rad_row = platform_results[PlatformId.RAD.value]
    payload = {
        "schema_version": 3,
        "formal_artifact": False,
        "pilot": True,
        "phase": "MODEL-REVISION-R4.2-RAD-LOW-ORDER-CONSTRAINED-PILOT",
        "code_commit": code_commit,
        "source_r4_1": {
            "path": str(source_r4_1_path.resolve()),
            "sha256": sha256_path(source_r4_1_path),
            "execution_commit": SOURCE_R4_1_EXECUTION_COMMIT,
            "source_local_pilot_passed": source_r4_1["local_checks"]["local_pilot_passed"],
            "web_review": "REVISE: local spherical-power identity fixed; RAD defocus exceeded 0.125 D",
            "rad_global_defocus_d": source_r4_1_rad["low_order_global_defocus_d"],
            "rad_powp_rms_error_d": source_r4_1_rms,
            "rad_powp_max_abs_error_d": source_r4_1_max,
        },
        "rejected_r4_baseline": {
            "rad_powp_rms_error_d": rejected_r4_rms,
            "rad_powp_max_abs_error_d": rejected_r4_max,
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
        "r4_2_revision_policy": {
            "scope": "RAD low-order constraint only; WFS and HOA rerun unchanged",
            "rad_complexity_held_at_r4_selected_level": "R+Q+A4",
            "rad_primary_fit_quantity": "source-locked local spherical power P(r)",
            "rad_secondary_fit_constraint": (
                "Binary4 residual global defocus aligned to frozen RAD source global defocus"
            ),
            "rad_source_global_defocus_d": rad_row["fit_source_low_order"][
                "target_global_defocus_d"
            ],
            "global_defocus_tolerance_d": R4_2_GLOBAL_DEFOCUS_TOLERANCE_D,
            "new_scientific_threshold_added": False,
            "powp_role": "independent OpticStudio serialized/full-ray validation",
            "powp_absolute_magnitude_is_manual_web_review": True,
            "powp_nonzero_target_sign_is_local_hard_identity_check": True,
            "powp_rms_and_max_must_remain_improved_vs_rejected_r4": True,
            "powp_change_vs_r4_1_is_evidence_only_not_a_hard_gate": True,
            "rad_old_integrated_opd_is_historical_diagnostic_only": True,
            "p2_changed": False,
            "a6_added_to_rad": False,
            "zone_boundaries_changed": False,
            "mtf_used_in_fit_objective": False,
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
        "rad_tradeoff_vs_r4_1": {
            "r4_1_powp_rms_error_d": source_r4_1_rms,
            "r4_2_powp_rms_error_d": rad_row["rad_power_rms_error_d"],
            "r4_1_powp_max_abs_error_d": source_r4_1_max,
            "r4_2_powp_max_abs_error_d": rad_row["rad_power_max_abs_error_d"],
            "r4_1_global_defocus_d": source_r4_1_rad["low_order_global_defocus_d"],
            "r4_2_global_defocus_d": rad_row["low_order_global_defocus_d"],
            "role": "manual Web trade-off evidence; not an automatic gate",
        },
        "artifact_sha256": {},
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
        "next_gate": (
            "STOP for Web R4.2 review; do not start R6/R7 or production expansion"
            if local_pilot_passed
            else "STOP: R4.2 did not clear local checks; return evidence to Web"
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
