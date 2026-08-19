"""Probe physical Q=0 ZERO_HOA reference and representative Q(P) solves.

Phase A.2 uses the successful LB+A0 P solve from A.1.  ZERO_HOA is the same
controlled thick carrier (same R/CT/n/position) with Q=0 and no residual.  MFE POWP
at the IOL posterior surface records first-order power identity between this reference
and each Q candidate.  No formal carrier/residual lock is created.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.carrier_focus_zos import P_Q_RECHECK_THRESHOLD_D, measure_actual_eye_q_focus
from whole_eye_mvp.carrier_q_zos import (
    Q_REPLAY_SA_TOLERANCE_UM,
    build_physical_carrier_in_standard_eye,
    measure_standard_eye_c40,
    measure_standard_eye_powp,
    measure_zero_hoa_reference,
    solve_q_for_platform,
    validate_zero_hoa_measurement,
)
from whole_eye_mvp.carriers import SA_TARGETS_UM, sha256_path
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    BaseId,
    PlatformId,
    ScientificBaseline,
)
from whole_eye_mvp.standard_eye import ARTIFACT_ID as STANDARD_EYE_ARTIFACT_ID
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import SequentialEditor, open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
A1_REPORT_RELATIVE_PATH = Path(
    "diagnostics/task007/carrier_p_paraxial_probe/TASK_007_CARRIER_P_PARAXIAL_PROBE.json"
)
OUTPUT_RELATIVE_DIR = Path("diagnostics/task007/q_zero_hoa_probe")
REPORT_NAME = "TASK_007_Q_ZERO_HOA_PROBE.json"
SUMMARY_NAME = "TASK_007_Q_ZERO_HOA_SUMMARY.csv"
ZERO_HOA_NAME = "TASK007_ZERO_HOA_Q0_LB_A0.zmx"
C40_REPEATABILITY_TOLERANCE_UM = 0.001
DEFAULT_REPO_EVIDENCE_DIR = REPOSITORY_ROOT / "docs/evidence/task007/phase_a2"
REPO_EVIDENCE_JSON = "TASK_007_A2_EVIDENCE.json"
REPO_EVIDENCE_CSV = "TASK_007_A2_SUMMARY.csv"


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
    parser.add_argument("--a1-report", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--write-repo-evidence",
        action="store_true",
        help="also emit sanitized JSON/CSV under docs/evidence for GitHub handoff",
    )
    parser.add_argument("--repo-evidence-dir", type=Path, default=DEFAULT_REPO_EVIDENCE_DIR)
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
        raise SystemExit("TASK-007 Q probe requires a clean tracked Git checkout")
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


def _load_a1_report(path: Path, standard_eye_path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"Required Phase A.1 report is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("phase") != "TASK-007-A.1-P-SOLVE-PARAXIAL-CAPABILITY":
        raise SystemExit("Phase A.1 report has the wrong phase identity")
    if payload.get("formal_artifact") is not False or payload.get("tdd_999_cleared") is not False:
        raise SystemExit("Phase A.1 report has invalid formal/TDD-999 state")
    capability = payload.get("paraxial_surface_capability")
    if not isinstance(capability, dict) or not capability.get("changed_type"):
        raise SystemExit("Phase A.1 report lacks the completed API capability evidence")
    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        raise SystemExit("Phase A.1 report inputs are missing")
    if inputs.get("standard_eye_sha256") != sha256_path(standard_eye_path):
        raise SystemExit("Phase A.1 standard-eye hash no longer matches the locked input")
    return payload


def _lb_power_measurement(a1_payload: dict[str, object]) -> tuple[dict[str, object], Path, str]:
    power_solve = a1_payload.get("power_solve")
    if not isinstance(power_solve, dict):
        raise SystemExit("Phase A.1 power_solve block is missing")
    item = power_solve.get(str(BaseId.LB_AL2395))
    if not isinstance(item, dict):
        raise SystemExit("Phase A.1 LB+A0 power result is missing")
    measurement = item.get("measurement")
    if not isinstance(measurement, dict):
        raise SystemExit("Phase A.1 LB+A0 measurement is missing")
    candidate_path = Path(str(item.get("candidate_path", "")))
    candidate_sha = str(item.get("candidate_sha256", ""))
    if not candidate_path.is_file() or sha256_path(candidate_path) != candidate_sha:
        raise SystemExit("Phase A.1 LB+A0 candidate file/hash mismatch")
    return measurement, candidate_path, candidate_sha


def _write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("Q probe summary requires at least one row")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _repo_evidence_payload(
    payload: dict[str, object],
    *,
    report_sha256: str,
    summary_sha256: str,
) -> dict[str, object]:
    platform_solutions = payload["platform_solutions"]
    if not isinstance(platform_solutions, dict):
        raise ValueError("platform solutions missing from A.2 payload")
    compact_solutions: dict[str, object] = {}
    for platform, item in platform_solutions.items():
        if not isinstance(item, dict):
            raise ValueError("invalid platform solution block")
        solution = item["solution"]
        focus = item["actual_eye_q_focus"]
        if not isinstance(solution, dict) or not isinstance(focus, dict):
            raise ValueError("invalid platform solution/focus evidence")
        compact_solutions[platform] = {
            "q": solution["q"],
            "target_sa_um": solution["target_sa_um"],
            "solve_achieved_sa_um": solution["achieved_sa_um"],
            "zero_hoa_powp_d": solution["zero_hoa_powp_d"],
            "candidate_powp_d": solution["candidate_powp_d"],
            "powp_delta_d": solution["powp_delta_d"],
            "replay_achieved_sa_um": item["replay_achieved_sa_um"],
            "replay_error_um": item["replay_error_um"],
            "q_evaluations": solution["q_evaluations"],
            "actual_eye_focus_shift_mm": focus["focus_shift_mm"],
            "actual_eye_equivalent_vergence_shift_d": focus["equivalent_vergence_shift_d"],
            "p_q_recheck_required": focus["recheck_required"],
            "saved_candidate_sha256": item["saved_candidate_sha256"],
        }
    return {
        "schema_version": 1,
        "evidence_only": True,
        "formal_artifact": False,
        "tdd_999_cleared": False,
        "phase": payload["phase"],
        "baseline_id": payload["baseline_id"],
        "code_commit": payload["code_commit"],
        "reference_definition": payload["zero_hoa_reference_model"],
        "powp_definition": payload["powp_definition"],
        "source_carrier": payload["source_carrier"],
        "standard_eye_sha256": payload["inputs"]["standard_eye_sha256"],
        "phase_a1_lb_candidate_sha256": payload["inputs"]["phase_a1_lb_candidate_sha256"],
        "powp_parameter_headers": payload["zero_hoa"]["measurement"]["powp_parameter_headers"],
        "zero_hoa_powp_d": payload["zero_hoa"]["measurement"]["powp_d"],
        "zero_hoa_c40_um": payload["zero_hoa"]["measurement"]["wavefront"]["c40_um"],
        "platform_solutions": compact_solutions,
        "p_q_recheck_threshold_d": payload["p_q_recheck_threshold_d"],
        "p_q_recheck_platforms": payload["p_q_recheck_platforms"],
        "local_report_sha256": report_sha256,
        "summary_csv_sha256": summary_sha256,
    }


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

    a1_report_path = (
        args.a1_report.resolve()
        if args.a1_report is not None
        else (project_dir / A1_REPORT_RELATIVE_PATH).resolve()
    )
    a1_payload = _load_a1_report(a1_report_path, standard_eye_path)
    power_measurement, a1_candidate_path, a1_candidate_sha = _lb_power_measurement(a1_payload)

    source_power_d = float(power_measurement["power_d"])
    radius_ant_mm = float(power_measurement["radius_ant_mm"])
    radius_post_mm = float(power_measurement["radius_post_mm"])
    if float(power_measurement["q"]) != 0.0:
        raise SystemExit("Phase A.1 source carrier must have Q=0")

    output_dir = project_dir / OUTPUT_RELATIVE_DIR
    report_path = output_dir / REPORT_NAME
    summary_path = output_dir / SUMMARY_NAME
    zero_path = output_dir / ZERO_HOA_NAME
    candidate_paths = {
        platform: output_dir / f"TASK007_Q_LB_A0_{platform}.zmx"
        for platform in (PlatformId.WFS, PlatformId.RAD, PlatformId.HOA)
    }
    _guard_outputs((report_path, summary_path, zero_path, *candidate_paths.values()), overwrite=args.overwrite)

    solutions: dict[str, dict[str, object]] = {}
    summary_rows: list[dict[str, object]] = []
    with open_zos_session(args.install_dir) as session:
        zero_reference = measure_zero_hoa_reference(
            session,
            standard_eye_path,
            radius_ant_mm=radius_ant_mm,
            radius_post_mm=radius_post_mm,
        )
        zero_findings = validate_zero_hoa_measurement(zero_reference, expected_power_d=source_power_d)
        if zero_findings:
            raise SystemExit("ZERO_HOA validation failed: " + " | ".join(zero_findings))

        build_physical_carrier_in_standard_eye(
            session,
            standard_eye_path,
            radius_ant_mm=radius_ant_mm,
            radius_post_mm=radius_post_mm,
            q=0.0,
            zero_hoa_reference=True,
        )
        SequentialEditor(session.system, session.zosapi).save_as(zero_path)
        session.system.LoadFile(str(zero_path.resolve()), False)
        zero_replay = measure_standard_eye_c40(session)
        zero_powp_replay = measure_standard_eye_powp(session)
        if abs(zero_replay.c40_um - zero_reference.wavefront.c40_um) > C40_REPEATABILITY_TOLERANCE_UM:
            raise SystemExit("ZERO_HOA saved-file C40 replay exceeded repeatability tolerance")

        for platform, destination in candidate_paths.items():
            solution = solve_q_for_platform(
                session,
                standard_eye_path,
                platform_id=str(platform),
                source_power_d=source_power_d,
                radius_ant_mm=radius_ant_mm,
                radius_post_mm=radius_post_mm,
                zero_reference=zero_reference,
            )
            build_physical_carrier_in_standard_eye(
                session,
                standard_eye_path,
                radius_ant_mm=radius_ant_mm,
                radius_post_mm=radius_post_mm,
                q=solution.q,
            )
            SequentialEditor(session.system, session.zosapi).save_as(destination)
            session.system.LoadFile(str(destination.resolve()), False)
            candidate_replay = measure_standard_eye_c40(session)
            candidate_powp_replay = measure_standard_eye_powp(session)
            if abs(candidate_replay.c40_um - solution.candidate_c40_um) > C40_REPEATABILITY_TOLERANCE_UM:
                raise SystemExit(f"{platform} saved-file candidate C40 replay exceeded repeatability tolerance")
            replay_sa = candidate_replay.c40_um - zero_replay.c40_um
            replay_error = replay_sa - float(SA_TARGETS_UM[platform])
            if abs(replay_error) > Q_REPLAY_SA_TOLERANCE_UM:
                raise SystemExit(
                    f"{platform} saved-candidate SA replay failed: "
                    f"target={SA_TARGETS_UM[platform]:.6g}, achieved={replay_sa:.6g}"
                )

            actual_eye_focus = measure_actual_eye_q_focus(session, a1_candidate_path, q=solution.q)
            replay_powp_delta = candidate_powp_replay.power_d - zero_powp_replay.power_d
            solutions[str(platform)] = {
                "solution": asdict(solution),
                "saved_candidate_path": str(destination.resolve()),
                "saved_candidate_sha256": sha256_path(destination),
                "replay_candidate_wavefront": asdict(candidate_replay),
                "replay_zero_wavefront": asdict(zero_replay),
                "replay_zero_powp_d": zero_powp_replay.power_d,
                "replay_candidate_powp_d": candidate_powp_replay.power_d,
                "replay_powp_delta_d": replay_powp_delta,
                "replay_achieved_sa_um": replay_sa,
                "replay_error_um": replay_error,
                "replay_passed": True,
                "actual_eye_q_focus": asdict(actual_eye_focus),
            }
            summary_rows.append(
                {
                    "platform_id": str(platform),
                    "source_power_d": source_power_d,
                    "q": solution.q,
                    "target_sa_um": float(SA_TARGETS_UM[platform]),
                    "solve_achieved_sa_um": solution.achieved_sa_um,
                    "replay_achieved_sa_um": replay_sa,
                    "replay_error_um": replay_error,
                    "zero_hoa_powp_d": zero_powp_replay.power_d,
                    "candidate_powp_d": candidate_powp_replay.power_d,
                    "powp_delta_d": replay_powp_delta,
                    "q_evaluations": solution.q_evaluations,
                    "actual_eye_focus_shift_mm": actual_eye_focus.focus_shift_mm,
                    "actual_eye_equivalent_vergence_shift_d": actual_eye_focus.equivalent_vergence_shift_d,
                    "p_q_recheck_required": actual_eye_focus.recheck_required,
                    "candidate_sha256": sha256_path(destination),
                }
            )

    _write_summary_csv(summary_path, summary_rows)
    recheck_platforms = [row["platform_id"] for row in summary_rows if bool(row["p_q_recheck_required"])]
    payload: dict[str, object] = {
        "schema_version": 2,
        "formal_artifact": False,
        "phase": "TASK-007-A.2-Q0-POWP-REPRESENTATIVE-Q-SOLVE",
        "baseline_id": baseline.baseline_id,
        "code_commit": code_commit,
        "tdd_999_cleared": False,
        "representative_q_solve_completed": True,
        "all_18_q_solve_completed": False,
        "residual_calibration_completed": False,
        "zero_hoa_reference_model": "same_physical_carrier_q0_no_residual",
        "powp_definition": {
            "surface": "IOL posterior surface",
            "wave": 1,
            "hx": 0.0,
            "hy": 0.0,
            "px": 0.0,
            "py": 0.0,
            "data": 0,
            "meaning": "on-axis pupil-center spherical power in diopters after IOL refraction",
        },
        "c40_repeatability_tolerance_um": C40_REPEATABILITY_TOLERANCE_UM,
        "p_q_recheck_threshold_d": P_Q_RECHECK_THRESHOLD_D,
        "p_q_recheck_platforms": recheck_platforms,
        "powp_delta_acceptance_pending_web_review": True,
        "inputs": {
            "phase_a1_report_path": str(a1_report_path),
            "phase_a1_report_sha256": sha256_path(a1_report_path),
            "phase_a1_lb_candidate_path": str(a1_candidate_path),
            "phase_a1_lb_candidate_sha256": a1_candidate_sha,
            "standard_eye_path": str(standard_eye_path.resolve()),
            "standard_eye_sha256": sha256_path(standard_eye_path),
        },
        "source_carrier": {
            "base_id": str(BaseId.LB_AL2395),
            "cornea_id": "A0",
            "power_d": source_power_d,
            "radius_ant_mm": radius_ant_mm,
            "radius_post_mm": radius_post_mm,
        },
        "zero_hoa": {
            "measurement": asdict(zero_reference),
            "saved_path": str(zero_path.resolve()),
            "saved_sha256": sha256_path(zero_path),
            "replay_wavefront": asdict(zero_replay),
            "replay_powp_d": zero_powp_replay.power_d,
        },
        "platform_solutions": solutions,
        "summary_csv_path": str(summary_path.resolve()),
        "summary_csv_sha256": sha256_path(summary_path),
        "next_gate": "Web review of POWP identity and representative P-Q coupling before full 18-carrier solve",
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.write_repo_evidence:
        evidence_dir = args.repo_evidence_dir.resolve()
        evidence_json = evidence_dir / REPO_EVIDENCE_JSON
        evidence_csv = evidence_dir / REPO_EVIDENCE_CSV
        _guard_outputs((evidence_json, evidence_csv), overwrite=args.overwrite)
        report_sha = sha256_path(report_path)
        summary_sha = sha256_path(summary_path)
        evidence = _repo_evidence_payload(payload, report_sha256=report_sha, summary_sha256=summary_sha)
        evidence_json.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.copyfile(summary_path, evidence_csv)
        payload["repo_evidence"] = {
            "json_path": str(evidence_json),
            "json_sha256": sha256_path(evidence_json),
            "csv_path": str(evidence_csv),
            "csv_sha256": sha256_path(evidence_csv),
        }

    print(json.dumps({"report_path": str(report_path.resolve()), **payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
