"""Run the real LB + REF_MONO five-candidate B0 scan and emit a provisional recommendation."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.b0 import B0CandidateInput, rank_b0_candidates
from whole_eye_mvp.b0_zos import acquire_b0_lock_curve
from whole_eye_mvp.cornea_assets import cornea_lock_prescriptions
from whole_eye_mvp.cornea_candidates_zos import measure_cornea_file_wavefront
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, CorneaId, ScientificBaseline
from whole_eye_mvp.ref_mono_coupled import calibrate_ref_mono_for_cornea
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.store import open_project_store
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


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(args.project_dir, baseline)
    standard_eye_path = store.resolve(STANDARD_EYE_RELATIVE_PATH)
    if not standard_eye_path.is_file():
        raise SystemExit(f"Required locked standard eye is missing: {standard_eye_path}")

    cornea_dir = args.project_dir / "diagnostics" / "task005d" / "corneas"
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

    output_dir = args.project_dir / "diagnostics" / "task005d" / "b0_scan"
    result_path = output_dir / RESULT_NAME
    if result_path.exists() and not args.overwrite:
        raise SystemExit(f"B0 scan result already exists; pass --overwrite: {result_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open_zos_session(args.install_dir) as session:
        reference_wavefront = measure_cornea_file_wavefront(session, reference_path)
        reference_c40 = reference_wavefront.c40_um

        a_cornea_path = _cornea_path(cornea_dir, a_prescription.candidate_id)
        a_ref_path = output_dir / "REF_MONO_A0.zmx"
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
            ref_path = output_dir / f"REF_MONO_{prescription.candidate_id.replace('.', '_')}.zmx"
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
                    "cornea_wavefront": asdict(wavefront),
                    "achieved_delta_c40_um": achieved_delta,
                    "ref_mono_path": str(ref_path.resolve()),
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
        "reference_cornea_c40_um": reference_c40,
        "A0": {
            "cornea_path": str(a_cornea_path.resolve()),
            "ref_mono_path": str(a_ref_path.resolve()),
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
