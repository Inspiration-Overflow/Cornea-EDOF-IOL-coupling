"""Run the real LB + REF_MONO five-candidate B0 MTFA-v2 scan."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.b0 import B0CandidateInput, rank_b0_candidates
from whole_eye_mvp.b0_probe import require_b0_probe_evidence
from whole_eye_mvp.b0_zos import acquire_b0_lock_curve
from whole_eye_mvp.cornea_assets import cornea_lock_prescriptions
from whole_eye_mvp.cornea_candidates_zos import measure_cornea_file_wavefront
from whole_eye_mvp.domain import (
    CORNEA_LOCK_B0_555_V2,
    CURRENT_SCIENTIFIC_BASELINE_ID,
    CorneaId,
    ScientificBaseline,
)
from whole_eye_mvp.ref_mono_coupled import calibrate_ref_mono_for_cornea
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.store import open_project_store, sha256_file
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
RESULT_NAME = "TASK_006_B0_REAL_SCAN.json"


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
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _cornea_path(output_dir: Path, candidate_id: str) -> Path:
    if candidate_id == "A0":
        return output_dir / "CORNEA_A0.zmx"
    return output_dir / f"CORNEA_{candidate_id.replace('.', '_')}.zmx"


def _repository_commit() -> str:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        if status.stdout.strip():
            raise RuntimeError("tracked repository files are modified")
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        raise SystemExit(
            "Full B0 scan requires a clean Git checkout with a resolvable commit for provenance"
        ) from exc
    commit = completed.stdout.strip()
    if len(commit) != 40:
        raise SystemExit("Full B0 scan could not resolve a canonical 40-character Git commit")
    return commit


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(project_dir, baseline)
    code_commit = _repository_commit()
    probe_evidence = require_b0_probe_evidence(project_dir)
    standard_eye_path = store.resolve(STANDARD_EYE_RELATIVE_PATH)
    if not standard_eye_path.is_file():
        raise SystemExit(f"Required locked standard eye is missing: {standard_eye_path}")

    cornea_dir = project_dir / "diagnostics" / "task005d" / "corneas"
    reference_path = cornea_dir / "TASK005D_LB_REFERENCE_CORNEA.zmx"
    prescriptions = cornea_lock_prescriptions(baseline)
    a_prescription = prescriptions[0]
    b_prescriptions = tuple(item for item in prescriptions if item.cornea_id == CorneaId.B0)
    required = (
        reference_path,
        _cornea_path(cornea_dir, a_prescription.candidate_id),
        *(_cornea_path(cornea_dir, item.candidate_id) for item in b_prescriptions),
    )
    missing = tuple(path for path in required if not path.is_file())
    if missing:
        raise SystemExit(
            "Required TASK-005D cornea diagnostics are missing; run "
            "scripts/build_task_005d_cornea_candidates.py first: "
            + ", ".join(str(path) for path in missing)
        )

    input_hashes = {
        "standard_eye": sha256_file(standard_eye_path),
        "reference_cornea": sha256_file(reference_path),
        "A0": sha256_file(_cornea_path(cornea_dir, a_prescription.candidate_id)),
        **{
            item.candidate_id: sha256_file(_cornea_path(cornea_dir, item.candidate_id))
            for item in b_prescriptions
        },
    }

    output_dir = project_dir / "diagnostics" / "task005d" / "b0_scan_mtfa_v2"
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / RESULT_NAME
    a_ref_path = output_dir / "REF_MONO_A0.zmx"
    b_ref_paths = {
        item.candidate_id: output_dir / f"REF_MONO_{item.candidate_id.replace('.', '_')}.zmx"
        for item in b_prescriptions
    }
    existing = tuple(
        path for path in (a_ref_path, *b_ref_paths.values(), result_path) if path.exists()
    )
    if existing and not args.overwrite:
        raise SystemExit(
            "B0 MTFA-v2 scan outputs already exist; pass --overwrite to replace them: "
            + ", ".join(str(path) for path in existing)
        )

    with open_zos_session(args.install_dir) as session:
        reference_wavefront = measure_cornea_file_wavefront(session, reference_path)
        reference_c40 = reference_wavefront.c40_um

        a_cornea_path = _cornea_path(cornea_dir, a_prescription.candidate_id)
        a_calibration = calibrate_ref_mono_for_cornea(
            session,
            baseline,
            a_cornea_path,
            standard_eye_path,
            a_ref_path,
        )
        session.system.LoadFile(str(a_ref_path.resolve()), False)
        a_epd3 = acquire_b0_lock_curve(session, 3.0).curve
        a_epd5 = acquire_b0_lock_curve(session, 5.0).curve

        candidate_inputs: list[B0CandidateInput] = []
        candidate_evidence: list[dict[str, object]] = []
        for prescription in b_prescriptions:
            cornea_path = _cornea_path(cornea_dir, prescription.candidate_id)
            wavefront = measure_cornea_file_wavefront(session, cornea_path)
            achieved_delta = wavefront.c40_um - reference_c40
            ref_path = b_ref_paths[prescription.candidate_id]
            calibration = calibrate_ref_mono_for_cornea(
                session,
                baseline,
                cornea_path,
                standard_eye_path,
                ref_path,
            )
            session.system.LoadFile(str(ref_path.resolve()), False)
            epd3 = acquire_b0_lock_curve(session, 3.0).curve
            epd5 = acquire_b0_lock_curve(session, 5.0).curve
            candidate = B0CandidateInput(
                candidate_id=prescription.candidate_id,
                delta_c40_um=float(prescription.target_delta_c40_um),
                achieved_delta_c40_um=achieved_delta,
                epd3=epd3,
                epd5=epd5,
                morphology_reject=False,
                morphology_reason="",
            )
            candidate_inputs.append(candidate)
            candidate_evidence.append(
                {
                    "candidate_id": prescription.candidate_id,
                    "target_delta_c40_um": float(prescription.target_delta_c40_um),
                    "cornea_path": str(cornea_path.resolve()),
                    "cornea_sha256": sha256_file(cornea_path),
                    "cornea_wavefront": asdict(wavefront),
                    "achieved_delta_c40_um": achieved_delta,
                    "ref_mono_path": str(ref_path.resolve()),
                    "ref_mono_sha256": sha256_file(ref_path),
                    "ref_mono_calibration": asdict(calibration),
                    "epd3": asdict(epd3),
                    "epd5": asdict(epd5),
                }
            )

    report = rank_b0_candidates(a_epd3, a_epd5, tuple(candidate_inputs))
    payload = {
        "formal_artifact": False,
        "passed": report.complete and report.recommendation_id is not None,
        "morphology_review_pending": True,
        "selection_locked": False,
        "acquisition": "MFE_MTFA_GRID0",
        "analysis_settings": asdict(CORNEA_LOCK_B0_555_V2),
        "provenance": {
            "code_commit": code_commit,
            "baseline_id": baseline.baseline_id,
            "opticstudio_install_dir": str(Path(args.install_dir).resolve()),
            "opticstudio_install_label": Path(args.install_dir).resolve().name,
            "phase_b1_probe": asdict(probe_evidence),
            "input_sha256": input_hashes,
        },
        "reference_cornea_c40_um": reference_c40,
        "A0": {
            "cornea_path": str(a_cornea_path.resolve()),
            "cornea_sha256": sha256_file(a_cornea_path),
            "ref_mono_path": str(a_ref_path.resolve()),
            "ref_mono_sha256": sha256_file(a_ref_path),
            "ref_mono_calibration": asdict(a_calibration),
            "epd3": asdict(a_epd3),
            "epd5": asdict(a_epd5),
        },
        "candidates": candidate_evidence,
        "scan_report": asdict(report),
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result_path": str(result_path.resolve()), **payload}, ensure_ascii=False, indent=2))
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
