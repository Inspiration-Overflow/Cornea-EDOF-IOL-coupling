"""Run post-audit R6/R7 24-carrier rebuild and exact-mechanism validation.

This is a carrier/mechanism gate only. It builds N0+A0+B0+C0 across both base eyes
and all three IOL platforms, solves each physical carrier P->Q(P) with the revised
physical STOP/fixed-retina geometry, applies the frozen R5.2 Binary4 prescription,
validates mechanism identity, and stops for Web review. It never runs R8 production
configurations and never performs an automatic power-specific refit.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.carriers import sha256_path
from whole_eye_mvp.cornea_candidates_zos import C0_TRANSITION_SLICES_NOMINAL
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    BaseId,
    PlatformId,
    ScientificBaseline,
)
from whole_eye_mvp.revision_carrier_zos import build_revision_q0_analytical_carrier
from whole_eye_mvp.revision_r5_2 import R5_2_FREEZE_ID, R5_2_RULE_DESCRIPTION
from whole_eye_mvp.revision_r5_lock import (
    R5_1_FREEZE_ID,
    R5_GLOBAL_DEFOCUS_TOLERANCE_D,
    R5_REPRESENTATIVE_POWER_D,
    R5_REPRESENTATIVE_RADIUS_MM,
)
from whole_eye_mvp.revision_r6 import (
    R6_EXPECTED_CARRIER_COUNT,
    R6_MAX_PQ_RECHECK_CYCLES,
    R6_R7_PHASE,
    R6_RAD_REJECTED_R4_MAX_ABS_ERROR_D,
    R6_RAD_REJECTED_R4_RMS_ERROR_D,
    R6CarrierKey,
    calibration_labels_by_platform,
    expected_r6_carrier_keys,
    rad_powp_local_gate,
    validate_r6_carrier_keys,
)
from whole_eye_mvp.revision_r6_native import (
    NATIVE_CORNEA_SOURCE_ID,
    build_native_cornea_source,
)
from whole_eye_mvp.revision_r6_zos import (
    R6CarrierValidationResult,
    build_and_validate_r6_carrier,
    solve_revision_platform_carrier,
)
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
OUTPUT_RELATIVE_DIR = Path("diagnostics/model_revision/r6_r7")
REPORT_NAME = "MODEL_REVISION_R6_R7_EVIDENCE.json"
R2_R3_REPORT_RELATIVE = Path(
    "diagnostics/model_revision/r2_r3/MODEL_REVISION_R2_R3_EVIDENCE.json"
)
R4_2_REPORT_RELATIVE = Path(
    "diagnostics/model_revision/r4_2_pilot/MODEL_REVISION_R4_2_PILOT_EVIDENCE.json"
)
TASK005D_REPORT_RELATIVE = Path(
    "diagnostics/task005d/corneas/TASK_005D_CORNEA_CANDIDATES.json"
)
B0_LOCK_RELATIVE = Path("locks/B0_LOCK.json")
R2_R3_ACCEPTED_COMMIT = "f88a8e27e8a96b2852c648dde04649ecbefa34c9"
R4_2_ACCEPTED_EXECUTION_COMMIT = "e242cc88a6e59cce85f2a990e44a56b070b11149"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-dir", type=Path, default=os.environ.get(INSTALL_ENV))
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
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
        raise SystemExit("R6/R7 requires a clean tracked Git checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"required JSON is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON root must be an object: {path}")
    return payload


def _require_prerequisites(project_dir: Path) -> dict[str, object]:
    r2_path = project_dir / R2_R3_REPORT_RELATIVE
    r2 = _load_json(r2_path)
    if (
        r2.get("schema_version") != 2
        or r2.get("phase") != "MODEL-REVISION-R2-R3"
        or r2.get("code_commit") != R2_R3_ACCEPTED_COMMIT
        or r2.get("passed") is not True
    ):
        raise SystemExit("R6/R7 requires the accepted canonical R2/R3 evidence")

    r4_path = project_dir / R4_2_REPORT_RELATIVE
    r4 = _load_json(r4_path)
    if (
        r4.get("schema_version") != 3
        or r4.get("phase") != "MODEL-REVISION-R4.2-RAD-LOW-ORDER-CONSTRAINED-PILOT"
        or r4.get("code_commit") != R4_2_ACCEPTED_EXECUTION_COMMIT
        or r4.get("manual_web_review_required") is not True
        or r4.get("automatic_progression_allowed") is not False
    ):
        raise SystemExit("R6/R7 requires the canonical R4.2 execution evidence")
    checks = r4.get("local_checks")
    if not isinstance(checks, dict) or checks.get("local_pilot_passed") is not True:
        raise SystemExit("R6/R7 requires R4.2 local_pilot_passed=true")

    return {
        "r2_r3_path": str(r2_path.resolve()),
        "r2_r3_sha256": sha256_path(r2_path),
        "r2_r3": r2,
        "r4_2_path": str(r4_path.resolve()),
        "r4_2_sha256": sha256_path(r4_path),
        "r4_2": r4,
    }


def _verify_reported_file(project_dir: Path, item: dict[str, object]) -> tuple[Path, str]:
    path_text = item.get("path")
    sha_text = item.get("sha256")
    if not isinstance(path_text, str) or not isinstance(sha_text, str):
        raise SystemExit("TASK-005D cornea evidence item lacks path/hash")
    path = project_dir / "diagnostics" / "task005d" / "corneas" / Path(path_text).name
    if not path.is_file() or sha256_path(path) != sha_text:
        raise SystemExit(f"TASK-005D cornea file/hash mismatch: {path.name}")
    return path, sha_text


def _postop_cornea_sources(project_dir: Path) -> dict[str, dict[str, object]]:
    report = _load_json(project_dir / TASK005D_REPORT_RELATIVE)
    if report.get("passed") is not True or report.get("formal_artifact") is not False:
        raise SystemExit("TASK-005D cornea diagnostic report is not the expected PASS evidence")
    lock = _load_json(project_dir / B0_LOCK_RELATIVE)
    lock_block = lock.get("lock")
    if (
        lock.get("formal_artifact") is not True
        or lock.get("selection_locked") is not True
        or not isinstance(lock_block, dict)
        or lock_block.get("candidate_id") != "B0.20"
    ):
        raise SystemExit("R6/R7 requires the frozen B0.20 cornea lock")

    a_item = report.get("A0")
    if not isinstance(a_item, dict):
        raise SystemExit("TASK-005D report lacks A0")
    a_path, a_sha = _verify_reported_file(project_dir, a_item)

    b_items = report.get("B_candidates")
    if not isinstance(b_items, list):
        raise SystemExit("TASK-005D report lacks B candidates")
    b_match: dict[str, object] | None = None
    for item in b_items:
        if not isinstance(item, dict):
            continue
        measurement = item.get("measurement")
        candidate_id = measurement.get("candidate_id") if isinstance(measurement, dict) else None
        if candidate_id == "B0.20" or Path(str(item.get("path", ""))).stem == "CORNEA_B0_20":
            b_match = item
            break
    if b_match is None:
        raise SystemExit("frozen B0.20 file is missing from TASK-005D report")
    b_path, b_sha = _verify_reported_file(project_dir, b_match)

    c_items = report.get("C0_convergence")
    if not isinstance(c_items, list) or not c_items:
        raise SystemExit("TASK-005D report lacks C0 convergence evidence")
    c_match: dict[str, object] | None = None
    for item in c_items:
        if not isinstance(item, dict):
            continue
        measurement = item.get("measurement")
        control = measurement.get("control_value") if isinstance(measurement, dict) else None
        if isinstance(control, (int, float)) and math.isclose(
            float(control),
            float(C0_TRANSITION_SLICES_NOMINAL),
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            c_match = item
            break
    if c_match is None:
        raise SystemExit("nominal C0 cornea file is missing from convergence evidence")
    c_path, c_sha = _verify_reported_file(project_dir, c_match)
    return {
        "A0": {"path": a_path, "sha256": a_sha, "source": "TASK005D_A0"},
        "B0": {"path": b_path, "sha256": b_sha, "source": "B0_LOCK_B0.20"},
        "C0": {
            "path": c_path,
            "sha256": c_sha,
            "source": "TASK005D_C0_NOMINAL",
            "control_value": C0_TRANSITION_SLICES_NOMINAL,
        },
    }


def _prepare_output(path: Path, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise SystemExit(f"R6/R7 output is not empty; pass --overwrite: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _artifact_hashes(root: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != REPORT_NAME:
            rows[str(path.relative_to(root)).replace("\\", "/")] = sha256_path(path)
    return rows


def _rad_sign_identity(result: R6CarrierValidationResult) -> bool:
    readback = result.rad_power_readback
    if readback is None:
        raise ValueError("RAD validation requires POWP readback")
    return all(
        point.target_relative_power_d == 0.0
        or point.relative_power_d * point.target_relative_power_d > 0.0
        for point in readback.points
    )


def _validation_summary(result: R6CarrierValidationResult) -> dict[str, object]:
    mechanism = result.standard_mechanism
    rad = result.rad_power_readback
    sign = _rad_sign_identity(result) if rad is not None else None
    rad_gate = (
        rad_powp_local_gate(
            sign_identity_passed=bool(sign),
            rms_error_d=rad.rms_error_d,
            max_abs_error_d=rad.max_abs_error_d,
        )
        if rad is not None
        else None
    )
    ray_health = all(
        item.passed
        for item in (*result.actual_mono_ray_health, *result.actual_edof_ray_health)
    )
    return {
        "carrier_id": result.carrier.carrier_id,
        "base_id": result.carrier.base_id,
        "cornea_id": result.carrier.cornea_id,
        "platform_id": result.carrier.platform_id,
        "power_d": result.carrier.power_d,
        "q_ant": result.carrier.q_ant,
        "p_q_recheck_cycles": len(result.carrier.recheck_cycles),
        "final_focus_vergence_shift_d": result.carrier.final_focus.equivalent_vergence_shift_d,
        "standard_eye_sa_target_um": result.carrier.q_solution.target_sa_um,
        "standard_eye_sa_replay_um": result.carrier.standard_eye_sa_replay_um,
        "standard_eye_sa_error_um": result.carrier.standard_eye_sa_error_um,
        "selected_complexity": (
            "R"
            if result.carrier.platform_id == "WFS"
            else "R+Q+A4"
            if result.carrier.platform_id == "RAD"
            else "R+Q+A4+A6"
        ),
        "serialized_mechanism_engineering_target_passed": mechanism.engineering_target_passed,
        "serialized_mechanism_rms_fraction": mechanism.rms_fraction_of_target,
        "serialized_mechanism_max_fraction": mechanism.max_fraction_of_target,
        "low_order_global_defocus_d": mechanism.low_order_global_defocus_d,
        "defocus_reference_passed": abs(mechanism.low_order_global_defocus_d)
        <= R5_GLOBAL_DEFOCUS_TOLERANCE_D,
        "rad_powp_sign_identity_passed": sign,
        "rad_powp_rms_error_d": rad.rms_error_d if rad is not None else None,
        "rad_powp_max_abs_error_d": rad.max_abs_error_d if rad is not None else None,
        "rad_powp_local_gate_passed": rad_gate,
        "actual_eye_ray_health_passed": ray_health,
        "minimum_conic_radicand": result.actual_edof.minimum_conic_radicand,
        "max_abs_c1_slope_jump": max(
            (abs(item.c1_slope_jump) for item in result.actual_edof.boundaries),
            default=0.0,
        ),
        "full_standard_audit_acquired": result.full_standard_audit_edof is not None,
        "raw": asdict(result),
    }


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")
    code_commit = _clean_git_head()
    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    prerequisites = _require_prerequisites(project_dir)
    standard_eye = (project_dir / STANDARD_EYE_RELATIVE_PATH).resolve()
    if not standard_eye.is_file():
        raise SystemExit(f"STD_IOL_EYE_2024 is missing: {standard_eye}")
    postop = _postop_cornea_sources(project_dir)
    output_dir = project_dir / OUTPUT_RELATIVE_DIR
    _prepare_output(output_dir, args.overwrite)

    expected_keys = expected_r6_carrier_keys()
    validate_r6_carrier_keys(expected_keys)
    solved = {}
    source_rows: dict[str, dict[str, object]] = {}

    with open_zos_session(args.install_dir) as session:
        for base in BaseId:
            base_id = base.value
            for cornea_id in ("N0", "A0", "B0", "C0"):
                if cornea_id == "N0":
                    native_path = output_dir / "sources" / f"N0_NATIVE_LIOU_{base_id}.zmx"
                    build_native_cornea_source(
                        session,
                        baseline,
                        base_id,
                        native_path,
                    )
                    source = {
                        "path": native_path,
                        "sha256": sha256_path(native_path),
                        "source": NATIVE_CORNEA_SOURCE_ID,
                    }
                else:
                    source = postop[cornea_id]
                source_path = source["path"]
                if not isinstance(source_path, Path):
                    raise SystemExit("resolved R6 cornea source path is invalid")
                source_rows[f"{base_id}_{cornea_id}"] = {
                    key: str(value.resolve()) if isinstance(value, Path) else value
                    for key, value in source.items()
                }
                q0_path = output_dir / "q0" / f"Q0_{base_id}_{cornea_id}.zmx"
                q0 = build_revision_q0_analytical_carrier(
                    session,
                    baseline,
                    base_id,
                    source_path,
                    q0_path,
                )
                for platform in PlatformId:
                    result = solve_revision_platform_carrier(
                        session,
                        baseline,
                        standard_eye,
                        base_id=base_id,
                        cornea_id=cornea_id,
                        platform_id=platform.value,
                        q0=q0,
                        q0_path=q0_path,
                        output_dir=output_dir / "carriers",
                        max_rechecks=R6_MAX_PQ_RECHECK_CYCLES,
                    )
                    solved[result.carrier_id] = result

        if len(solved) != R6_EXPECTED_CARRIER_COUNT:
            raise SystemExit(
                f"R6 solved {len(solved)} carriers, expected {R6_EXPECTED_CARRIER_COUNT}"
            )
        solved_keys = tuple(
            R6CarrierKey(item.base_id, item.cornea_id, item.platform_id)
            for item in solved.values()
        )
        validate_r6_carrier_keys(solved_keys)
        calibration = calibration_labels_by_platform(
            tuple(
                (R6CarrierKey(item.base_id, item.cornea_id, item.platform_id), item.power_d)
                for item in solved.values()
            )
        )
        heavy_ids = {
            carrier_id
            for by_platform in calibration.values()
            for carrier_id in by_platform.values()
        }

        validations: dict[str, R6CarrierValidationResult] = {}
        validation_failures: dict[str, dict[str, object]] = {}
        for carrier_id in sorted(solved):
            item = solved[carrier_id]
            try:
                validations[carrier_id] = build_and_validate_r6_carrier(
                    session,
                    standard_eye,
                    item,
                    output_dir / "validated",
                    full_standard_audit=carrier_id in heavy_ids,
                )
            except Exception as error:  # noqa: BLE001 - isolate per-carrier failures
                validation_failures[carrier_id] = {
                    "carrier_id": carrier_id,
                    "base_id": item.base_id,
                    "cornea_id": item.cornea_id,
                    "platform_id": item.platform_id,
                    "power_d": item.power_d,
                    "q_ant": item.q_ant,
                    "p_q_recheck_cycles": len(item.recheck_cycles),
                    "final_focus_vergence_shift_d": item.final_focus.equivalent_vergence_shift_d,
                    "standard_eye_sa_target_um": item.q_solution.target_sa_um,
                    "standard_eye_sa_replay_um": item.standard_eye_sa_replay_um,
                    "standard_eye_sa_error_um": item.standard_eye_sa_error_um,
                    "validation_error": f"{type(error).__name__}: {error}",
                    "selected_complexity": (
                        "R"
                        if item.platform_id == "WFS"
                        else "R+Q+A4"
                        if item.platform_id == "RAD"
                        else "R+Q+A4+A6"
                    ),
                    "serialized_mechanism_engineering_target_passed": False,
                    "serialized_mechanism_rms_fraction": None,
                    "serialized_mechanism_max_fraction": None,
                    "low_order_global_defocus_d": None,
                    "defocus_reference_passed": False,
                    "rad_powp_sign_identity_passed": None,
                    "rad_powp_rms_error_d": None,
                    "rad_powp_max_abs_error_d": None,
                    "rad_powp_local_gate_passed": (
                        False if item.platform_id == "RAD" else None
                    ),
                    "actual_eye_ray_health_passed": False,
                    "minimum_conic_radicand": 0.0,
                    "max_abs_c1_slope_jump": None,
                    "full_standard_audit_acquired": False,
                }

    summaries = {
        carrier_id: _validation_summary(result)
        for carrier_id, result in validations.items()
    }
    summaries.update(validation_failures)
    wfs_hoa_mechanism_passed = all(
        row["serialized_mechanism_engineering_target_passed"] is True
        for row in summaries.values()
        if row["platform_id"] in {"WFS", "HOA"}
    )
    rad_rows = [row for row in summaries.values() if row["platform_id"] == "RAD"]
    rad_identity_passed = all(row["rad_powp_local_gate_passed"] is True for row in rad_rows)
    defocus_all_passed = all(
        row["defocus_reference_passed"] is True for row in summaries.values()
    )
    ray_health_all_passed = all(
        row["actual_eye_ray_health_passed"] is True for row in summaries.values()
    )
    sa_all_passed = all(
        abs(float(row["standard_eye_sa_error_um"])) <= 0.01
        for row in summaries.values()
    )
    geometry_all_passed = all(
        float(row["minimum_conic_radicand"]) > 0.0 for row in summaries.values()
    )
    heavy_audit_all_passed = all(
        carrier_id in validations
        and validations[carrier_id].full_standard_audit_mono is not None
        and validations[carrier_id].full_standard_audit_edof is not None
        and validations[carrier_id].full_standard_audit_mono.ray_health_passed
        and validations[carrier_id].full_standard_audit_edof.ray_health_passed
        for carrier_id in heavy_ids
    )
    local_passed = (
        len(summaries) == R6_EXPECTED_CARRIER_COUNT
        and wfs_hoa_mechanism_passed
        and rad_identity_passed
        and defocus_all_passed
        and ray_health_all_passed
        and sa_all_passed
        and geometry_all_passed
        and heavy_audit_all_passed
    )

    power_ranges = {}
    for platform in PlatformId:
        values = sorted(
            float(row["power_d"])
            for row in summaries.values()
            if row["platform_id"] == platform.value
        )
        power_ranges[platform.value] = {
            "min_d": values[0],
            "median_lower_d": values[(len(values) - 1) // 2],
            "max_d": values[-1],
        }

    payload = {
        "schema_version": 1,
        "formal_artifact": False,
        "pilot": False,
        "phase": R6_R7_PHASE,
        "code_commit": code_commit,
        "r5_freeze_id": R5_2_FREEZE_ID,
        "r5_1_conic_normalization": {
            "id": R5_1_FREEZE_ID,
            "applies_to": "HOA",
            "rule": "delta_conic * (R_zone(P)/R_zone(+20D))^3; WFS/RAD bit-identical to R5",
        },
        "r5_2_hoa_a6_rule": {
            "id": R5_2_FREEZE_ID,
            "applies_to": "HOA active zones 1 and 2 only",
            "reference_power_d": R5_REPRESENTATIVE_POWER_D,
            "reference_radius_mm": R5_REPRESENTATIVE_RADIUS_MM,
            "zone_order": [1, 2],
            "rule": R5_2_RULE_DESCRIPTION,
            "gate_feedback_used": False,
            "optimizer_used": False,
        },
        "prerequisites": {
            "r2_r3_path": prerequisites["r2_r3_path"],
            "r2_r3_sha256": prerequisites["r2_r3_sha256"],
            "r4_2_path": prerequisites["r4_2_path"],
            "r4_2_sha256": prerequisites["r4_2_sha256"],
        },
        "standard_eye": {
            "path": str(standard_eye),
            "sha256": sha256_path(standard_eye),
            "role": "IOL mechanism calibration only; EPD6 is not a main-study pupil definition",
        },
        "cornea_sources": source_rows,
        "contract": {
            "carrier_count": R6_EXPECTED_CARRIER_COUNT,
            "carrier_space": "2 base × 4 cornea (N0/A0/B0/C0) × 3 platform",
            "p_q_recheck_max_cycles": R6_MAX_PQ_RECHECK_CYCLES,
            "pupil_semantics": "actual-eye 3/5 mm are physical STOP diameters / Float By Stop Size",
            "standard_eye_q_solve": "power-specific Q(P); EPD6 calibration domain only",
            "edof_separate_p_q_callback_allowed": False,
            "normalized_r5_residual_first": True,
            "r5_2_hoa_q_ant_required": 0.0,
            "automatic_power_specific_refit_allowed": False,
            "mtf_used_in_mechanism_fit": False,
            "global_defocus_tolerance_d": R5_GLOBAL_DEFOCUS_TOLERANCE_D,
            "rad_powp_rejected_r4_rms_baseline_d": R6_RAD_REJECTED_R4_RMS_ERROR_D,
            "rad_powp_rejected_r4_max_baseline_d": R6_RAD_REJECTED_R4_MAX_ABS_ERROR_D,
        },
        "power_ranges": power_ranges,
        "low_median_high_full_standard_audits": calibration,
        "carriers": summaries,
        "local_checks": {
            "all_24_carriers_present": len(summaries) == R6_EXPECTED_CARRIER_COUNT,
            "standard_eye_sa_all_passed": sa_all_passed,
            "wfs_hoa_serialized_mechanism_all_passed": wfs_hoa_mechanism_passed,
            "rad_real_powp_identity_regression_all_passed": rad_identity_passed,
            "global_defocus_all_passed": defocus_all_passed,
            "actual_eye_3_5mm_ray_health_all_passed": ray_health_all_passed,
            "binary4_geometry_all_passed": geometry_all_passed,
            "selected_low_median_high_full_standard_audit_all_passed": heavy_audit_all_passed,
            "local_r6_r7_passed": local_passed,
        },
        "artifact_sha256": {},
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
        "next_gate": (
            "STOP for Web R6/R7 review; R8 remains locked"
            if local_passed
            else "STOP: R6/R7 carrier/mechanism validation failed; no automatic refit or R8"
        ),
    }
    payload["artifact_sha256"] = _artifact_hashes(output_dir)
    report_path = output_dir / REPORT_NAME
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "report_path": str(report_path.resolve()),
                "local_r6_r7_passed": local_passed,
                "manual_web_review_required": True,
                "automatic_progression_allowed": False,
                "power_ranges": power_ranges,
                "local_checks": payload["local_checks"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not local_passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
