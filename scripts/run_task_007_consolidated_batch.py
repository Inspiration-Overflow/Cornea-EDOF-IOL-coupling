"""Run the consolidated TASK-007 full-carrier and residual-calibration batch.

This is deliberately a larger-grained local handoff than the earlier probes:
1. solve the six Base×Cornea Q=0 starting carriers once;
2. branch those six starts into all 18 Base×Cornea×Platform P/Q carriers, with the
   already-validated maximum two P-Q engineering rechecks;
3. choose low/median/high actual powers for each platform;
4. physicalize the frozen WFS/RAD/HOA residual seeds as additive Grid Sag departures;
5. acquire low-order readback, ray-health, C4/C6, and EPD3 through-focus evidence.

The batch is evidence-only. It never writes formal carrier/residual locks and never
clears TDD-999. Mechanism-specific morphology remains a Web review, not a new local
threshold or classifier.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.b0_zos import acquire_b0_lock_curve
from whole_eye_mvp.carrier_focus_zos import (
    P_Q_RECHECK_THRESHOLD_D,
    measure_actual_eye_q_focus,
    solve_actual_eye_radius_at_q,
)
from whole_eye_mvp.carrier_q_zos import (
    Q_REPLAY_SA_TOLERANCE_UM,
    build_physical_carrier_in_standard_eye,
    measure_standard_eye_c40,
    measure_standard_eye_powp,
    solve_q_for_platform,
)
from whole_eye_mvp.carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from whole_eye_mvp.carrier_zos import ActualEyeCarrierPowerResult, solve_actual_eye_carrier_power
from whole_eye_mvp.carriers import (
    CarrierKey,
    ProvisionalCarrier,
    SA_TARGETS_UM,
    expected_calibration_carriers,
    sha256_path,
    validate_18_provisional_carriers,
)
from whole_eye_mvp.cornea_candidates_zos import C0_TRANSITION_SLICES_NOMINAL
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    BaseId,
    CorneaId,
    PlatformId,
    ScientificBaseline,
)
from whole_eye_mvp.grid_sag_residual import (
    GRID_SAG_INTERPOLATION,
    GRID_SAG_SIZE,
    GRID_SAG_STEP_MM,
    apply_grid_sag_residual,
    readback_residual_low_order,
    write_grid_sag_dat,
)
from whole_eye_mvp.residual_payload import (
    RadialResidualCandidate,
    build_hoa_residual_candidate,
    build_rad_residual_candidate,
    build_wfs_residual_candidate,
)
from whole_eye_mvp.residual_policy import RESIDUAL_VALIDATION_546_V1
from whole_eye_mvp.standard_eye import ARTIFACT_ID as STANDARD_EYE_ARTIFACT_ID
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import SequentialEditor, open_zos_session
from whole_eye_mvp.zos.mfe_zernike_hoa import MfeHoaZernikeRunner

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
TASK005D_REPORT_REL = Path("diagnostics/task005d/corneas/TASK_005D_CORNEA_CANDIDATES.json")
B0_LOCK_REL = Path("locks/B0_LOCK.json")
A3_EVIDENCE = REPOSITORY_ROOT / "docs/evidence/task007/phase_a3/TASK_007_A3_EVIDENCE.json"
OUTPUT_REL_DIR = Path("diagnostics/task007/consolidated_batch")
REPORT_NAME = "TASK_007_CONSOLIDATED_BATCH.json"
CARRIER_CSV_NAME = "TASK_007_18_CARRIERS.csv"
CALIBRATION_CSV_NAME = "TASK_007_RESIDUAL_CALIBRATIONS.csv"
REPO_EVIDENCE_DIR = REPOSITORY_ROOT / "docs/evidence/task007/consolidated_batch"
REPO_JSON_NAME = "TASK_007_CONSOLIDATED_EVIDENCE.json"
REPO_CARRIER_CSV = "TASK_007_18_CARRIERS.csv"
REPO_CALIBRATION_CSV = "TASK_007_RESIDUAL_CALIBRATIONS.csv"
MAX_PQ_RECHECK_CYCLES = 2
C40_REPEATABILITY_TOLERANCE_UM = 0.001


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-dir", type=Path, default=os.environ.get(INSTALL_ENV))
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-repo-evidence", action="store_true")
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
        raise SystemExit("TASK-007 consolidated batch requires a clean tracked checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"required JSON is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON root must be an object: {path}")
    return payload


def _verify_reported_file(project_dir: Path, item: dict[str, object]) -> tuple[Path, str]:
    path_text = item.get("path")
    sha_text = item.get("sha256")
    if not isinstance(path_text, str) or not isinstance(sha_text, str):
        raise TypeError("TASK-005D cornea evidence item lacks path/hash")
    path = project_dir / "diagnostics" / "task005d" / "corneas" / Path(path_text).name
    if not path.is_file() or sha256_path(path) != sha_text:
        raise SystemExit(f"TASK-005D cornea file/hash mismatch: {path.name}")
    return path, sha_text


def _cornea_sources(project_dir: Path) -> dict[str, dict[str, object]]:
    report = _load_json(project_dir / TASK005D_REPORT_REL)
    if report.get("passed") is not True or report.get("formal_artifact") is not False:
        raise SystemExit("TASK-005D cornea diagnostic report is not the expected PASS evidence")

    lock = _load_json(project_dir / B0_LOCK_REL)
    if lock.get("formal_artifact") is not True or lock.get("selection_locked") is not True:
        raise SystemExit("B0 lock is not formal/locked")
    lock_block = lock.get("lock")
    if not isinstance(lock_block, dict) or lock_block.get("candidate_id") != "B0.20":
        raise SystemExit("TASK-007 requires the frozen B0.20 lock")

    a_item = report.get("A0")
    if not isinstance(a_item, dict):
        raise TypeError("TASK-005D report lacks A0")
    a_path, a_sha = _verify_reported_file(project_dir, a_item)

    b_items = report.get("B_candidates")
    if not isinstance(b_items, list):
        raise TypeError("TASK-005D report lacks B candidates")
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
        raise SystemExit("frozen B0.20 cornea file is missing from TASK-005D report")
    b_path, b_sha = _verify_reported_file(project_dir, b_match)

    c_items = report.get("C0_convergence")
    if not isinstance(c_items, list) or not c_items:
        raise TypeError("TASK-005D report lacks C0 convergence evidence")
    c_match: dict[str, object] | None = None
    for item in c_items:
        if not isinstance(item, dict):
            continue
        measurement = item.get("measurement")
        control = measurement.get("control_value") if isinstance(measurement, dict) else None
        if isinstance(control, (int, float)) and math.isclose(
            float(control), float(C0_TRANSITION_SLICES_NOMINAL), rel_tol=0.0, abs_tol=1.0e-12
        ):
            c_match = item
            break
    if c_match is None:
        raise SystemExit(
            f"nominal C0 N={C0_TRANSITION_SLICES_NOMINAL} file is missing from convergence evidence"
        )
    c_path, c_sha = _verify_reported_file(project_dir, c_match)

    return {
        str(CorneaId.A0): {"path": a_path, "sha256": a_sha, "source": "TASK005D_A0"},
        str(CorneaId.B0): {"path": b_path, "sha256": b_sha, "source": "B0_LOCK_B0.20"},
        str(CorneaId.C0): {
            "path": c_path,
            "sha256": c_sha,
            "source": "TASK005D_C0_NOMINAL",
            "control_value": C0_TRANSITION_SLICES_NOMINAL,
        },
    }


def _load_a3_evidence() -> dict[str, object]:
    payload = _load_json(A3_EVIDENCE)
    if payload.get("phase") != "TASK-007-A.3-P-Q-REPRESENTATIVE-RECHECK":
        raise SystemExit("A.3 evidence phase mismatch")
    if payload.get("all_rechecks_converged") is not True:
        raise SystemExit("A.3 representative P-Q recheck did not converge")
    if payload.get("formal_artifact") is not False or payload.get("tdd_999_cleared") is not False:
        raise SystemExit("A.3 evidence has invalid formal/TDD state")
    return payload


def _prepare_output_dir(path: Path, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise SystemExit(f"consolidated output directory is not empty; pass --overwrite: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _best_peak(defocus: tuple[float, ...], values: tuple[float, ...]) -> tuple[float, float]:
    if len(defocus) != len(values) or not defocus:
        raise ValueError("through-focus curve is incomplete")
    index = max(range(len(values)), key=lambda i: (values[i], -abs(defocus[i]), defocus[i]))
    return float(defocus[index]), float(values[index])


def _relative_half_width(defocus: tuple[float, ...], values: tuple[float, ...]) -> float:
    """Descriptive 50%-of-own-peak width for the 17-point diagnostic curve only."""
    peak_d, peak = _best_peak(defocus, values)
    peak_index = defocus.index(peak_d)
    threshold = 0.5 * peak

    def crossing(i0: int, i1: int) -> float:
        x0, y0 = defocus[i0], values[i0]
        x1, y1 = defocus[i1], values[i1]
        if y0 == y1:
            return float(x1)
        return float(x0 + (threshold - y0) * (x1 - x0) / (y1 - y0))

    positive_side = float(defocus[0])
    for index in range(peak_index, 0, -1):
        if values[index - 1] < threshold <= values[index]:
            positive_side = crossing(index, index - 1)
            break

    negative_side = float(defocus[-1])
    for index in range(peak_index, len(values) - 1):
        if values[index] >= threshold > values[index + 1]:
            negative_side = crossing(index, index + 1)
            break
    return abs(negative_side - positive_side)


def _ray_health(session, path: Path, pupil_mm: float = 5.0) -> dict[str, object]:
    session.system.LoadFile(str(path.resolve()), False)
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(pupil_mm)
    image_surface = int(session.system.LDE.NumberOfSurfaces) - 1
    tool = session.system.Tools.OpenBatchRayTrace()
    try:
        rays = tool.CreateNormUnpol(9, session.zosapi.Tools.RayTrace.RaysType.Real, image_surface)
        rays.ClearData()
        opd_enum = session.zosapi.Tools.RayTrace.OPDMode
        opd_none = getattr(opd_enum, "None", getattr(opd_enum, "None_", None))
        if opd_none is None:
            raise RuntimeError("installed API exposes no OPDMode.None")
        for py in (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0):
            rays.AddRay(1, 0.0, 0.0, 0.0, py, opd_none)
        tool.RunAndWaitForCompletion()
        rays.StartReadingResults()
        failures: list[dict[str, object]] = []
        for index in range(9):
            values = tuple(rays.ReadNextResult())
            success = bool(values[0])
            error = int(values[2])
            vignette = int(values[3])
            if not success or error != 0 or vignette != 0:
                failures.append(
                    {"ray": index, "success": success, "error": error, "vignette": vignette}
                )
        return {"pupil_mm": pupil_mm, "passed": not failures, "failures": failures}
    finally:
        close = getattr(tool, "Close", None)
        if callable(close):
            close()


def _solve_platform_carrier(
    session,
    standard_eye_path: Path,
    base_id: str,
    cornea_id: str,
    platform_id: str,
    p0: ActualEyeCarrierPowerResult,
    p0_path: Path,
    output_dir: Path,
) -> tuple[ProvisionalCarrier, Path, dict[str, object]]:
    current_power = p0.power_d
    current_radius = p0.radius_ant_mm
    q_solution = solve_q_for_platform(
        session,
        standard_eye_path,
        platform_id=platform_id,
        source_power_d=current_power,
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
    )
    current_q = q_solution.q
    focus = measure_actual_eye_q_focus(session, p0_path, q=current_q)
    working_path = p0_path
    cycles: list[dict[str, object]] = []

    for cycle in range(1, MAX_PQ_RECHECK_CYCLES + 1):
        if not focus.recheck_required:
            break
        refocused = output_dir / "carriers" / f"PQ_{base_id}_{cornea_id}_{platform_id}_C{cycle}.zmx"
        radius_result = solve_actual_eye_radius_at_q(
            session,
            working_path,
            q=current_q,
            initial_radius_mm=current_radius,
            destination=refocused,
        )
        current_radius = radius_result.solved_radius_mm
        current_power = radius_result.power_d
        q_solution = solve_q_for_platform(
            session,
            standard_eye_path,
            platform_id=platform_id,
            source_power_d=current_power,
            radius_ant_mm=current_radius,
            radius_post_mm=-current_radius,
        )
        current_q = q_solution.q
        focus = measure_actual_eye_q_focus(session, refocused, q=current_q)
        cycles.append(
            {
                "cycle": cycle,
                "radius_solve": asdict(radius_result),
                "q": current_q,
                "sa_um": q_solution.achieved_sa_um,
                "powp_delta_d": q_solution.powp_delta_d,
                "actual_eye_focus": asdict(focus),
            }
        )
        working_path = refocused

    if focus.recheck_required:
        raise SystemExit(
            f"{base_id}/{cornea_id}/{platform_id} did not converge within two P-Q cycles"
        )

    # Reload the final working actual-eye carrier, apply the final Q, restore the fixed retina,
    # and save one canonical provisional carrier file for downstream calibration.
    final_focus = measure_actual_eye_q_focus(session, working_path, q=current_q)
    if final_focus.recheck_required:
        raise SystemExit(f"{base_id}/{cornea_id}/{platform_id} final focus replay crossed recheck gate")
    final_path = output_dir / "carriers" / f"CAR_{base_id}_{cornea_id}_{platform_id}.zmx"
    SequentialEditor(session.system, session.zosapi).save_as(final_path)

    session.system.LoadFile(str(final_path.resolve()), False)
    ant = session.system.LDE.GetSurfaceAt(4)
    post = session.system.LDE.GetSurfaceAt(5)
    if (
        abs(float(ant.Radius) - current_radius) > 1.0e-9
        or abs(float(post.Radius) + current_radius) > 1.0e-9
        or abs(float(ant.Conic) - current_q) > 1.0e-12
        or abs(float(post.Conic)) > 1.0e-12
    ):
        raise SystemExit(f"{base_id}/{cornea_id}/{platform_id} final actual-eye R/Q replay mismatch")

    build_physical_carrier_in_standard_eye(
        session,
        standard_eye_path,
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
        q=0.0,
        zero_hoa_reference=True,
    )
    ref_c40 = measure_standard_eye_c40(session)
    ref_powp = measure_standard_eye_powp(session)
    build_physical_carrier_in_standard_eye(
        session,
        standard_eye_path,
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
        q=current_q,
    )
    candidate_c40 = measure_standard_eye_c40(session)
    candidate_powp = measure_standard_eye_powp(session)
    replay_sa = candidate_c40.c40_um - ref_c40.c40_um
    target = float(SA_TARGETS_UM[platform_id])
    if abs(replay_sa - target) > Q_REPLAY_SA_TOLERANCE_UM:
        raise SystemExit(
            f"{base_id}/{cornea_id}/{platform_id} final SA replay failed: {replay_sa:.6g}"
        )
    if abs(candidate_c40.c40_um - q_solution.candidate_c40_um) > C40_REPEATABILITY_TOLERANCE_UM:
        raise SystemExit(f"{base_id}/{cornea_id}/{platform_id} final C40 replay drifted")

    carrier = ProvisionalCarrier(
        key=CarrierKey(base_id, cornea_id, platform_id),
        power_d=current_power,
        q=current_q,
        q_source_power_d=current_power,
        r_ant_mm=current_radius,
        r_post_mm=-current_radius,
        center_thickness_mm=CONTROLLED_IOL_CARRIER_546_V1.center_thickness_mm,
        material="MODEL_N1460",
        iol_position_mm=4.5,
        achieved_sa_um=replay_sa,
    )
    record = {
        "carrier": asdict(carrier),
        "p0_sha256": sha256_path(p0_path),
        "initial_power_d": p0.power_d,
        "initial_radius_mm": p0.radius_ant_mm,
        "recheck_cycles": cycles,
        "final_focus": asdict(final_focus),
        "final_sa_replay_um": replay_sa,
        "final_sa_error_um": replay_sa - target,
        "final_powp_delta_d": candidate_powp.power_d - ref_powp.power_d,
        "actual_eye_sha256": sha256_path(final_path),
    }
    return carrier, final_path, record


def _residual_candidates() -> dict[str, RadialResidualCandidate]:
    return {
        str(PlatformId.WFS): build_wfs_residual_candidate(),
        str(PlatformId.RAD): build_rad_residual_candidate(),
        str(PlatformId.HOA): build_hoa_residual_candidate(),
    }


def _sanitize_for_repo(value):
    if isinstance(value, dict):
        return {
            key: _sanitize_for_repo(item)
            for key, item in value.items()
            if "path" not in key.lower()
        }
    if isinstance(value, list):
        return [_sanitize_for_repo(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_for_repo(item) for item in value]
    return value


def _write_repo_evidence(payload: dict[str, object], carrier_rows, calibration_rows) -> None:
    REPO_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    repo_payload = _sanitize_for_repo(payload)
    repo_payload["local_report_sha256"] = payload["local_report_sha256"]
    text = json.dumps(repo_payload, ensure_ascii=False, indent=2)
    lowered = text.lower()
    if ".zmx" in lowered or ":\\" in text or ":/" in text:
        raise SystemExit("sanitized GitHub evidence still contains a machine path or .zmx reference")
    (REPO_EVIDENCE_DIR / REPO_JSON_NAME).write_text(text, encoding="utf-8")
    _write_csv(REPO_EVIDENCE_DIR / REPO_CARRIER_CSV, carrier_rows)
    _write_csv(REPO_EVIDENCE_DIR / REPO_CALIBRATION_CSV, calibration_rows)


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    code_commit = _clean_git_head()
    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(project_dir, baseline)
    _load_a3_evidence()
    corneas = _cornea_sources(project_dir)

    std_record = store.find_artifact(STANDARD_EYE_ARTIFACT_ID)
    if std_record is None or std_record.relative_path != STANDARD_EYE_RELATIVE_PATH:
        raise SystemExit("locked STD_IOL_EYE_2024 is not registered")
    if not std_record.locked or not store.verify_artifact(std_record):
        raise SystemExit("STD_IOL_EYE_2024 immutable hash validation failed")
    standard_eye_path = store.resolve(std_record.relative_path)

    output_dir = project_dir / OUTPUT_REL_DIR
    _prepare_output_dir(output_dir, args.overwrite)
    carrier_rows: list[dict[str, object]] = []
    calibration_rows: list[dict[str, object]] = []
    carriers: list[ProvisionalCarrier] = []
    actual_paths: dict[str, Path] = {}
    carrier_evidence: dict[str, object] = {}
    calibration_evidence: dict[str, object] = {}
    p0_evidence: dict[str, object] = {}

    with open_zos_session(args.install_dir) as session:
        # Stage 1A: six shared Q=0 starts, one per Base×Cornea.
        p0_map: dict[tuple[str, str], tuple[ActualEyeCarrierPowerResult, Path]] = {}
        for base in (BaseId.LB_AL2395, BaseId.ATC_M3_AL24477):
            for cornea in (CorneaId.A0, CorneaId.B0, CorneaId.C0):
                base_id = str(base)
                cornea_id = str(cornea)
                cornea_item = corneas[cornea_id]
                cornea_path = cornea_item["path"]
                if not isinstance(cornea_path, Path):
                    raise TypeError("resolved cornea path is invalid")
                p0_path = output_dir / "carriers" / f"P0_{base_id}_{cornea_id}.zmx"
                p0 = solve_actual_eye_carrier_power(
                    session,
                    baseline,
                    base_id,
                    cornea_path,
                    p0_path,
                )
                p0_map[(base_id, cornea_id)] = (p0, p0_path)
                p0_evidence[f"{base_id}_{cornea_id}"] = {
                    "power_d": p0.power_d,
                    "radius_mm": p0.radius_ant_mm,
                    "focus_shift_mm": p0.focus_shift_mm,
                    "sha256": sha256_path(p0_path),
                }

        # Stage 1B: branch the six shared starts into 18 platform-specific P/Q carriers.
        for base in (BaseId.LB_AL2395, BaseId.ATC_M3_AL24477):
            for cornea in (CorneaId.A0, CorneaId.B0, CorneaId.C0):
                base_id = str(base)
                cornea_id = str(cornea)
                p0, p0_path = p0_map[(base_id, cornea_id)]
                for platform in (PlatformId.WFS, PlatformId.RAD, PlatformId.HOA):
                    platform_id = str(platform)
                    carrier, final_path, record = _solve_platform_carrier(
                        session,
                        standard_eye_path,
                        base_id,
                        cornea_id,
                        platform_id,
                        p0,
                        p0_path,
                        output_dir,
                    )
                    carriers.append(carrier)
                    actual_paths[carrier.key.carrier_id] = final_path
                    carrier_evidence[carrier.key.carrier_id] = record
                    carrier_rows.append(
                        {
                            "carrier_id": carrier.key.carrier_id,
                            "base_id": carrier.key.base_id,
                            "cornea_id": carrier.key.cornea_id,
                            "platform_id": carrier.key.platform_id,
                            "power_d": carrier.power_d,
                            "q": carrier.q,
                            "r_ant_mm": carrier.r_ant_mm,
                            "r_post_mm": carrier.r_post_mm,
                            "achieved_sa_um": carrier.achieved_sa_um,
                            "actual_eye_sha256": record["actual_eye_sha256"],
                            "recheck_cycles": len(record["recheck_cycles"]),
                            "final_vergence_shift_d": record["final_focus"]["equivalent_vergence_shift_d"],
                        }
                    )
        validate_18_provisional_carriers(carriers)

        # Stage 2: one frozen residual per platform, checked on actual low/median/high powers.
        residuals = _residual_candidates()
        dat_paths: dict[str, Path] = {}
        dat_sha: dict[str, str] = {}
        for platform_id, candidate in residuals.items():
            dat_path = output_dir / "residual_payloads" / f"RESIDUAL_{platform_id}.DAT"
            write_grid_sag_dat(candidate, dat_path)
            dat_paths[platform_id] = dat_path
            dat_sha[platform_id] = sha256_path(dat_path)

        hard_gate_passed = True
        selected_calibrations: dict[str, dict[str, str]] = {}
        for platform in (PlatformId.WFS, PlatformId.RAD, PlatformId.HOA):
            platform_id = str(platform)
            candidate = residuals[platform_id]
            selected = expected_calibration_carriers(carriers, platform_id)
            selected_calibrations[platform_id] = {
                label: carrier.key.carrier_id for label, carrier in selected.items()
            }
            platform_records: dict[str, object] = {}

            for label in ("low", "median", "high"):
                carrier = selected[label]
                mono_path = actual_paths[carrier.key.carrier_id]
                edof_path = output_dir / "calibrations" / f"{carrier.key.carrier_id}_{label}_EDOF.zmx"
                import_result = apply_grid_sag_residual(
                    session,
                    mono_path,
                    candidate,
                    dat_paths[platform_id],
                    edof_path,
                )
                actual_readback = readback_residual_low_order(
                    session, mono_path, edof_path, candidate
                )
                actual_policy_pass = (
                    abs(actual_readback.measured_piston_um)
                    <= RESIDUAL_VALIDATION_546_V1.piston_tolerance_um
                    and abs(actual_readback.measured_global_defocus_d)
                    <= RESIDUAL_VALIDATION_546_V1.global_defocus_tolerance_d
                )
                mono_health = _ray_health(session, mono_path)
                edof_health = _ray_health(session, edof_path)

                # EPD3/555-nm MTFA-v2 is diagnostic-only here. It is not the Run72
                # Huygens-PSF production pipeline and does not redefine main metrics.
                session.system.LoadFile(str(mono_path.resolve()), False)
                mono_curve = acquire_b0_lock_curve(session, 3.0).curve
                mono_hoa = MfeHoaZernikeRunner(session.system, session.zosapi).run()
                session.system.LoadFile(str(edof_path.resolve()), False)
                edof_curve = acquire_b0_lock_curve(session, 3.0).curve
                edof_hoa = MfeHoaZernikeRunner(session.system, session.zosapi).run()
                mono_peak_d, mono_peak = _best_peak(mono_curve.defocus_d, mono_curve.q_lock)
                edof_peak_d, edof_peak = _best_peak(edof_curve.defocus_d, edof_curve.q_lock)

                std_mono = output_dir / "calibrations" / f"{carrier.key.carrier_id}_{label}_STD_MONO.zmx"
                std_edof = output_dir / "calibrations" / f"{carrier.key.carrier_id}_{label}_STD_EDOF.zmx"
                build_physical_carrier_in_standard_eye(
                    session,
                    standard_eye_path,
                    radius_ant_mm=carrier.r_ant_mm,
                    radius_post_mm=carrier.r_post_mm,
                    q=carrier.q,
                )
                SequentialEditor(session.system, session.zosapi).save_as(std_mono)
                std_mono_hoa = MfeHoaZernikeRunner(session.system, session.zosapi).run()
                apply_grid_sag_residual(
                    session,
                    std_mono,
                    candidate,
                    dat_paths[platform_id],
                    std_edof,
                )
                std_readback = readback_residual_low_order(
                    session, std_mono, std_edof, candidate
                )
                standard_policy_pass = (
                    abs(std_readback.measured_piston_um)
                    <= RESIDUAL_VALIDATION_546_V1.piston_tolerance_um
                    and abs(std_readback.measured_global_defocus_d)
                    <= RESIDUAL_VALIDATION_546_V1.global_defocus_tolerance_d
                )
                session.system.LoadFile(str(std_edof.resolve()), False)
                std_edof_hoa = MfeHoaZernikeRunner(session.system, session.zosapi).run()

                numerical_pass = (
                    actual_policy_pass
                    and standard_policy_pass
                    and bool(mono_health["passed"])
                    and bool(edof_health["passed"])
                )
                hard_gate_passed = hard_gate_passed and numerical_pass
                record = {
                    "label": label,
                    "carrier_id": carrier.key.carrier_id,
                    "actual_power_d": carrier.power_d,
                    "residual_payload_sha256": dat_sha[platform_id],
                    "grid_import": asdict(import_result),
                    "actual_readback": asdict(actual_readback),
                    "standard_readback": asdict(std_readback),
                    "actual_policy_passed": actual_policy_pass,
                    "standard_policy_passed": standard_policy_pass,
                    "mono_ray_health": mono_health,
                    "edof_ray_health": edof_health,
                    "mono_curve": asdict(mono_curve),
                    "edof_curve": asdict(edof_curve),
                    "mono_peak_defocus_d": mono_peak_d,
                    "edof_peak_defocus_d": edof_peak_d,
                    "distance_shift_d": edof_peak_d - mono_peak_d,
                    "mono_peak_q": mono_peak,
                    "edof_peak_q": edof_peak,
                    "mono_dof50_d": _relative_half_width(
                        mono_curve.defocus_d, mono_curve.q_lock
                    ),
                    "edof_dof50_d": _relative_half_width(
                        edof_curve.defocus_d, edof_curve.q_lock
                    ),
                    "actual_wavefront": {
                        "mono_c40_um": mono_hoa.c40_um,
                        "mono_c60_um": mono_hoa.c60_um,
                        "edof_c40_um": edof_hoa.c40_um,
                        "edof_c60_um": edof_hoa.c60_um,
                    },
                    "standard_wavefront": {
                        "mono_c40_um": std_mono_hoa.c40_um,
                        "mono_c60_um": std_mono_hoa.c60_um,
                        "edof_c40_um": std_edof_hoa.c40_um,
                        "edof_c60_um": std_edof_hoa.c60_um,
                    },
                    "numerical_hard_gate_passed": numerical_pass,
                    "mechanism_review_pending_web": True,
                    "edof_actual_eye_sha256": sha256_path(edof_path),
                    "std_mono_sha256": sha256_path(std_mono),
                    "std_edof_sha256": sha256_path(std_edof),
                }
                platform_records[label] = record
                calibration_rows.append(
                    {
                        "platform_id": platform_id,
                        "label": label,
                        "carrier_id": carrier.key.carrier_id,
                        "actual_power_d": carrier.power_d,
                        "measured_piston_um": actual_readback.measured_piston_um,
                        "measured_global_defocus_d": actual_readback.measured_global_defocus_d,
                        "standard_piston_um": std_readback.measured_piston_um,
                        "standard_global_defocus_d": std_readback.measured_global_defocus_d,
                        "max_abs_opd_error_um": actual_readback.max_abs_opd_error_um,
                        "distance_shift_d": edof_peak_d - mono_peak_d,
                        "mono_dof50_d": record["mono_dof50_d"],
                        "edof_dof50_d": record["edof_dof50_d"],
                        "numerical_hard_gate_passed": numerical_pass,
                        "mechanism_review_pending_web": True,
                    }
                )
            calibration_evidence[platform_id] = platform_records

    _write_csv(output_dir / CARRIER_CSV_NAME, carrier_rows)
    _write_csv(output_dir / CALIBRATION_CSV_NAME, calibration_rows)
    payload: dict[str, object] = {
        "schema_version": 2,
        "phase": "TASK-007-CONSOLIDATED-FULL18-RESIDUAL-CALIBRATION",
        "evidence_only": True,
        "formal_artifact": False,
        "tdd_999_cleared": False,
        "baseline_id": baseline.baseline_id,
        "code_commit": code_commit,
        "a3_evidence_sha256": sha256_path(A3_EVIDENCE),
        "standard_eye_sha256": sha256_path(standard_eye_path),
        "b0_lock_sha256": sha256_path(project_dir / B0_LOCK_REL),
        "settings": {
            "max_pq_recheck_cycles": MAX_PQ_RECHECK_CYCLES,
            "p_q_recheck_threshold_d": P_Q_RECHECK_THRESHOLD_D,
            "residual_policy_id": RESIDUAL_VALIDATION_546_V1.policy_id,
            "piston_tolerance_um": RESIDUAL_VALIDATION_546_V1.piston_tolerance_um,
            "global_defocus_tolerance_d": RESIDUAL_VALIDATION_546_V1.global_defocus_tolerance_d,
            "grid_sag_size": GRID_SAG_SIZE,
            "grid_sag_step_mm": GRID_SAG_STEP_MM,
            "grid_sag_interpolation": GRID_SAG_INTERPOLATION,
            "mechanism_tf_metric": "diagnostic CORNEA_LOCK_B0_555_v2 EPD3 MTFA; not Run72 production",
        },
        "cornea_inputs": {
            key: {
                "sha256": value["sha256"],
                "source": value["source"],
                **(
                    {"control_value": value["control_value"]}
                    if "control_value" in value
                    else {}
                ),
            }
            for key, value in corneas.items()
        },
        "shared_p0_count": len(p0_evidence),
        "shared_p0_evidence": p0_evidence,
        "carrier_count": len(carriers),
        "all_18_carriers_validated": True,
        "carrier_evidence": carrier_evidence,
        "selected_calibrations": selected_calibrations,
        "residual_payloads": {
            platform: {
                "sha256": dat_sha[platform],
                "surface_role": residuals[platform].surface_role,
                "seed_sample_count": len(residuals[platform].radii_mm),
                "grid_sag_interpolation": GRID_SAG_INTERPOLATION,
            }
            for platform in residuals
        },
        "calibration_evidence": calibration_evidence,
        "calibration_count": len(calibration_rows),
        "numerical_hard_gates_passed": hard_gate_passed,
        "mechanism_review_pending_web": True,
        "next_gate": (
            "Web mechanism review; if all 9 calibrations are accepted, proceed to formal TASK-007 lock finalization without another OpticStudio calibration run"
        ),
    }
    report_path = output_dir / REPORT_NAME
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["local_report_sha256"] = sha256_path(report_path)

    if args.write_repo_evidence:
        _write_repo_evidence(payload, carrier_rows, calibration_rows)

    print(
        json.dumps(
            {
                "report_path": str(report_path.resolve()),
                "shared_p0_count": len(p0_evidence),
                "carrier_count": len(carriers),
                "calibration_count": len(calibration_rows),
                "numerical_hard_gates_passed": hard_gate_passed,
                "mechanism_review_pending_web": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not hard_gate_passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
