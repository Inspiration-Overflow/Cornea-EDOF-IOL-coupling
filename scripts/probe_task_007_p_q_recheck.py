"""Run the allowed 1–2 cycle TASK-007 P-Q engineering recheck on LB+A0 WFS/RAD.

Phase A.3 starts from the successful A.2 Q solutions.  For each platform that crossed
the frozen 0.125-D actual-eye recheck trigger, it alternates:

1. radius solve in the actual eye while preserving anterior Q / posterior Q=0;
2. Q re-solve in STD_IOL_EYE_2024 at the updated paraxial power;
3. saved-file SA/POWP replay;
4. fixed-retina actual-eye focus recheck.

At most two cycles are allowed.  This remains diagnostic-only and creates no formal lock.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

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
from whole_eye_mvp.carriers import SA_TARGETS_UM, sha256_path
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, PlatformId, ScientificBaseline
from whole_eye_mvp.standard_eye import ARTIFACT_ID as STANDARD_EYE_ARTIFACT_ID
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import SequentialEditor, open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
A2_EVIDENCE_PATH = REPOSITORY_ROOT / "docs/evidence/task007/phase_a2/TASK_007_A2_EVIDENCE.json"
A1_ACTUAL_EYE_RELATIVE_PATH = Path(
    "diagnostics/task007/carrier_p_paraxial_probe/TASK007_P_LB_A0.zmx"
)
OUTPUT_RELATIVE_DIR = Path("diagnostics/task007/p_q_recheck")
REPORT_NAME = "TASK_007_P_Q_RECHECK.json"
SUMMARY_NAME = "TASK_007_P_Q_RECHECK_SUMMARY.csv"
DEFAULT_REPO_EVIDENCE_DIR = REPOSITORY_ROOT / "docs/evidence/task007/phase_a3"
REPO_EVIDENCE_JSON = "TASK_007_A3_EVIDENCE.json"
REPO_EVIDENCE_CSV = "TASK_007_A3_SUMMARY.csv"
MAX_RECHECK_CYCLES = 2
C40_REPEATABILITY_TOLERANCE_UM = 0.001


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
    parser.add_argument("--a2-evidence", type=Path, default=A2_EVIDENCE_PATH)
    parser.add_argument("--actual-eye-path", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-repo-evidence", action="store_true")
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
        raise SystemExit("TASK-007 A.3 requires a clean tracked Git checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load_a2_evidence(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"required A.2 evidence is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("phase") != "TASK-007-A.2-Q0-POWP-REPRESENTATIVE-Q-SOLVE":
        raise SystemExit("A.2 evidence has the wrong phase identity")
    if payload.get("evidence_only") is not True:
        raise SystemExit("A.2 evidence is not the expected GitHub diagnostic evidence")
    if payload.get("formal_artifact") is not False or payload.get("tdd_999_cleared") is not False:
        raise SystemExit("A.2 evidence has invalid formal/TDD-999 state")
    if payload.get("p_q_recheck_platforms") != ["WFS", "RAD"]:
        raise SystemExit("A.2 recheck platform set differs from the reviewed representative result")
    source = payload.get("source_carrier")
    if not isinstance(source, dict):
        raise TypeError("A.2 source_carrier block is missing")
    if source.get("base_id") != "LB_AL2395" or source.get("cornea_id") != "A0":
        raise SystemExit("A.2 source carrier is not LB+A0")
    return payload


def _guard_outputs(paths: tuple[Path, ...], *, overwrite: bool) -> None:
    existing = tuple(path for path in paths if path.exists())
    if existing and not overwrite:
        text = ", ".join(str(path) for path in existing)
        raise SystemExit(f"diagnostics already exist; pass --overwrite: {text}")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("A.3 summary requires rows")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sanitize_evidence(payload: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "evidence_only": True,
        "formal_artifact": False,
        "tdd_999_cleared": False,
        "phase": payload["phase"],
        "baseline_id": payload["baseline_id"],
        "code_commit": payload["code_commit"],
        "source_a2_evidence_sha256": payload["source_a2_evidence_sha256"],
        "standard_eye_sha256": payload["standard_eye_sha256"],
        "actual_eye_source_sha256": payload["actual_eye_source_sha256"],
        "max_recheck_cycles": payload["max_recheck_cycles"],
        "p_q_recheck_threshold_d": payload["p_q_recheck_threshold_d"],
        "platform_results": payload["platform_results"],
        "all_rechecks_converged": payload["all_rechecks_converged"],
        "next_gate": payload["next_gate"],
    }


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    code_commit = _clean_git_head()
    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(project_dir, baseline)
    a2_path = args.a2_evidence.resolve()
    a2 = _load_a2_evidence(a2_path)

    standard_record = store.find_artifact(STANDARD_EYE_ARTIFACT_ID)
    if standard_record is None or standard_record.relative_path != STANDARD_EYE_RELATIVE_PATH:
        raise SystemExit("required locked STD_IOL_EYE_2024 artifact is not registered correctly")
    if not standard_record.locked or not store.verify_artifact(standard_record):
        raise SystemExit("registered standard-eye artifact is not a valid immutable input")
    standard_eye_path = store.resolve(standard_record.relative_path)
    if a2.get("standard_eye_sha256") != sha256_path(standard_eye_path):
        raise SystemExit("standard-eye hash differs from A.2 evidence")

    actual_eye_path = (
        args.actual_eye_path.resolve()
        if args.actual_eye_path is not None
        else (project_dir / A1_ACTUAL_EYE_RELATIVE_PATH).resolve()
    )
    if not actual_eye_path.is_file():
        raise SystemExit(f"A.1 LB+A0 actual-eye carrier is missing: {actual_eye_path}")
    if a2.get("phase_a1_lb_candidate_sha256") != sha256_path(actual_eye_path):
        raise SystemExit("A.1 actual-eye carrier hash differs from A.2 evidence")

    source = a2["source_carrier"]
    if not isinstance(source, dict):
        raise TypeError("A.2 source carrier is invalid")
    platform_solutions = a2.get("platform_solutions")
    if not isinstance(platform_solutions, dict):
        raise TypeError("A.2 platform_solutions block is missing")

    output_dir = project_dir / OUTPUT_RELATIVE_DIR
    report_path = output_dir / REPORT_NAME
    summary_path = output_dir / SUMMARY_NAME
    _guard_outputs((report_path, summary_path), overwrite=args.overwrite)

    platform_results: dict[str, object] = {}
    summary_rows: list[dict[str, object]] = []
    with open_zos_session(args.install_dir) as session:
        for platform in (PlatformId.WFS, PlatformId.RAD):
            platform_id = str(platform)
            a2_solution = platform_solutions.get(platform_id)
            if not isinstance(a2_solution, dict):
                raise TypeError(f"A.2 solution is missing for {platform_id}")
            current_radius = float(source["radius_ant_mm"])
            current_power = float(source["power_d"])
            current_q = float(a2_solution["q"])
            cycles: list[dict[str, object]] = []
            final_focus = None

            for cycle in range(1, MAX_RECHECK_CYCLES + 1):
                refocused_path = output_dir / f"TASK007_PQ_{platform_id}_C{cycle}_REFOCUSED.zmx"
                final_actual_path = output_dir / f"TASK007_PQ_{platform_id}_C{cycle}_FINAL.zmx"
                std_ref_path = output_dir / f"TASK007_PQ_{platform_id}_C{cycle}_STD_Q0.zmx"
                std_candidate_path = output_dir / f"TASK007_PQ_{platform_id}_C{cycle}_STD_Q.zmx"

                radius_result = solve_actual_eye_radius_at_q(
                    session,
                    actual_eye_path,
                    q=current_q,
                    initial_radius_mm=current_radius,
                    destination=refocused_path,
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

                build_physical_carrier_in_standard_eye(
                    session,
                    standard_eye_path,
                    radius_ant_mm=current_radius,
                    radius_post_mm=-current_radius,
                    q=0.0,
                    zero_hoa_reference=True,
                )
                SequentialEditor(session.system, session.zosapi).save_as(std_ref_path)
                session.system.LoadFile(str(std_ref_path.resolve()), False)
                replay_ref_c40 = measure_standard_eye_c40(session)
                replay_ref_powp = measure_standard_eye_powp(session)

                build_physical_carrier_in_standard_eye(
                    session,
                    standard_eye_path,
                    radius_ant_mm=current_radius,
                    radius_post_mm=-current_radius,
                    q=current_q,
                )
                SequentialEditor(session.system, session.zosapi).save_as(std_candidate_path)
                session.system.LoadFile(str(std_candidate_path.resolve()), False)
                replay_candidate_c40 = measure_standard_eye_c40(session)
                replay_candidate_powp = measure_standard_eye_powp(session)
                replay_sa = replay_candidate_c40.c40_um - replay_ref_c40.c40_um
                replay_error = replay_sa - float(SA_TARGETS_UM[platform])
                if abs(replay_error) > Q_REPLAY_SA_TOLERANCE_UM:
                    raise SystemExit(
                        f"{platform_id} cycle {cycle} SA replay failed: "
                        f"target={SA_TARGETS_UM[platform]:.6g}, achieved={replay_sa:.6g}"
                    )
                if abs(replay_candidate_c40.c40_um - q_solution.candidate_c40_um) > C40_REPEATABILITY_TOLERANCE_UM:
                    raise SystemExit(f"{platform_id} cycle {cycle} candidate C40 replay drifted")
                if abs(replay_ref_c40.c40_um - q_solution.zero_hoa_c40_um) > C40_REPEATABILITY_TOLERANCE_UM:
                    raise SystemExit(f"{platform_id} cycle {cycle} reference C40 replay drifted")

                final_focus = measure_actual_eye_q_focus(
                    session,
                    refocused_path,
                    q=current_q,
                )
                SequentialEditor(session.system, session.zosapi).save_as(final_actual_path)
                cycle_record = {
                    "cycle": cycle,
                    "radius_solve": asdict(radius_result),
                    "q_solution": asdict(q_solution),
                    "replay_sa_um": replay_sa,
                    "replay_error_um": replay_error,
                    "replay_powp_delta_d": replay_candidate_powp.power_d - replay_ref_powp.power_d,
                    "actual_eye_focus": asdict(final_focus),
                    "refocused_actual_eye_sha256": sha256_path(refocused_path),
                    "final_actual_eye_sha256": sha256_path(final_actual_path),
                    "std_q0_sha256": sha256_path(std_ref_path),
                    "std_q_sha256": sha256_path(std_candidate_path),
                }
                cycles.append(cycle_record)
                summary_rows.append(
                    {
                        "platform_id": platform_id,
                        "cycle": cycle,
                        "power_d": current_power,
                        "radius_mm": current_radius,
                        "q": current_q,
                        "target_sa_um": float(SA_TARGETS_UM[platform]),
                        "replay_sa_um": replay_sa,
                        "replay_error_um": replay_error,
                        "replay_powp_delta_d": cycle_record["replay_powp_delta_d"],
                        "actual_eye_vergence_shift_d": final_focus.equivalent_vergence_shift_d,
                        "recheck_required": final_focus.recheck_required,
                    }
                )
                if not final_focus.recheck_required:
                    break

            if final_focus is None:
                raise RuntimeError(f"no P-Q recheck result produced for {platform_id}")
            platform_results[platform_id] = {
                "initial_power_d": float(source["power_d"]),
                "initial_radius_mm": float(source["radius_ant_mm"]),
                "initial_q": float(a2_solution["q"]),
                "cycles": cycles,
                "final_power_d": current_power,
                "final_radius_mm": current_radius,
                "final_q": current_q,
                "final_focus": asdict(final_focus),
                "converged_within_two_cycles": not final_focus.recheck_required,
            }

    _write_csv(summary_path, summary_rows)
    all_converged = all(
        bool(item["converged_within_two_cycles"])
        for item in platform_results.values()
        if isinstance(item, dict)
    )
    payload = {
        "schema_version": 1,
        "formal_artifact": False,
        "phase": "TASK-007-A.3-P-Q-REPRESENTATIVE-RECHECK",
        "baseline_id": baseline.baseline_id,
        "code_commit": code_commit,
        "tdd_999_cleared": False,
        "source_a2_evidence_sha256": sha256_path(a2_path),
        "standard_eye_sha256": sha256_path(standard_eye_path),
        "actual_eye_source_sha256": sha256_path(actual_eye_path),
        "max_recheck_cycles": MAX_RECHECK_CYCLES,
        "p_q_recheck_threshold_d": P_Q_RECHECK_THRESHOLD_D,
        "platform_results": platform_results,
        "all_rechecks_converged": all_converged,
        "summary_csv_sha256": sha256_path(summary_path),
        "next_gate": (
            "Web review before extending the P-Q algorithm to all 18 carriers"
            if all_converged
            else "STOP: representative P-Q recheck did not converge within the allowed two cycles"
        ),
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.write_repo_evidence:
        repo_dir = args.repo_evidence_dir.resolve()
        repo_json = repo_dir / REPO_EVIDENCE_JSON
        repo_csv = repo_dir / REPO_EVIDENCE_CSV
        if (repo_json.exists() or repo_csv.exists()) and not args.overwrite:
            raise SystemExit("repo evidence already exists; pass --overwrite to replace it")
        repo_dir.mkdir(parents=True, exist_ok=True)
        repo_json.write_text(
            json.dumps(_sanitize_evidence(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        repo_csv.write_bytes(summary_path.read_bytes())

    print(json.dumps({"report_path": str(report_path.resolve()), **payload}, ensure_ascii=False, indent=2))
    if not all_converged:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
