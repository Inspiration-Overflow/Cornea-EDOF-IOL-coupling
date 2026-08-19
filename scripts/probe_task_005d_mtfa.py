"""Probe TASK-005D B0 MFE-MTFA acquisition before the full five-candidate scan."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.b0_zos import acquire_b0_q_samples
from whole_eye_mvp.cornea_assets import cornea_lock_prescriptions
from whole_eye_mvp.domain import (
    CORNEA_LOCK_B0_555_V2,
    CURRENT_SCIENTIFIC_BASELINE_ID,
    CorneaId,
    ScientificBaseline,
)
from whole_eye_mvp.ref_mono_coupled import calibrate_ref_mono_for_cornea
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
RESULT_NAME = "TASK_005D_MTFA_PROBE.json"
PROBE_DEFOCUS_D = (0.0, -1.5)
PROBE_SAMPLING = (2, 3, 4)
PROBE_FREQUENCY_STEPS = (5.0, 2.5)


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


def _cornea_path(cornea_dir: Path, candidate_id: str) -> Path:
    if candidate_id == "A0":
        return cornea_dir / "CORNEA_A0.zmx"
    return cornea_dir / f"CORNEA_{candidate_id.replace('.', '_')}.zmx"


def _max_abs_difference(
    left: dict[str, dict[str, object]],
    right: dict[str, dict[str, object]],
) -> float:
    differences: list[float] = []
    for candidate_id in left:
        for pupil_key in left[candidate_id]:
            left_values = left[candidate_id][pupil_key]
            right_values = right[candidate_id][pupil_key]
            assert isinstance(left_values, dict) and isinstance(right_values, dict)
            for left_q, right_q in zip(left_values["q_lock"], right_values["q_lock"], strict=True):
                differences.append(abs(float(right_q) - float(left_q)))
    return max(differences, default=0.0)


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(project_dir, baseline)
    standard_eye_path = store.resolve(STANDARD_EYE_RELATIVE_PATH)
    if not standard_eye_path.is_file():
        raise SystemExit(f"Required locked standard eye is missing: {standard_eye_path}")

    cornea_dir = project_dir / "diagnostics" / "task005d" / "corneas"
    prescriptions = cornea_lock_prescriptions(baseline)
    a_prescription = prescriptions[0]
    b020 = next(
        item
        for item in prescriptions
        if item.cornea_id == CorneaId.B0 and item.candidate_id == "B0.20"
    )
    selected = (a_prescription, b020)
    missing = tuple(
        path
        for path in (_cornea_path(cornea_dir, item.candidate_id) for item in selected)
        if not path.is_file()
    )
    if missing:
        raise SystemExit("Required Phase A cornea diagnostics are missing: " + ", ".join(map(str, missing)))

    output_dir = project_dir / "diagnostics" / "task005d" / "b0_mtfa_probe"
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / RESULT_NAME
    ref_paths = {
        item.candidate_id: output_dir / f"REF_MONO_{item.candidate_id.replace('.', '_')}.zmx"
        for item in selected
    }
    existing = tuple(path for path in (*ref_paths.values(), result_path) if path.exists())
    if existing and not args.overwrite:
        raise SystemExit(
            "MTFA probe outputs already exist; pass --overwrite to replace them: "
            + ", ".join(map(str, existing))
        )

    calibrations: dict[str, object] = {}
    sampling_results: dict[str, dict[str, dict[str, object]]] = {}
    frequency_results: dict[str, dict[str, dict[str, object]]] = {}

    with open_zos_session(args.install_dir) as session:
        for item in selected:
            candidate_id = item.candidate_id
            cornea_path = _cornea_path(cornea_dir, candidate_id)
            ref_path = ref_paths[candidate_id]
            calibration = calibrate_ref_mono_for_cornea(
                session,
                baseline,
                cornea_path,
                standard_eye_path,
                ref_path,
            )
            calibrations[candidate_id] = asdict(calibration)

        for sampling in PROBE_SAMPLING:
            sample_key = str(sampling)
            sampling_results[sample_key] = {}
            for item in selected:
                candidate_id = item.candidate_id
                session.system.LoadFile(str(ref_paths[candidate_id].resolve()), False)
                sampling_results[sample_key][candidate_id] = {}
                for pupil_mm in CORNEA_LOCK_B0_555_V2.pupils_mm:
                    samples = acquire_b0_q_samples(
                        session,
                        pupil_mm,
                        PROBE_DEFOCUS_D,
                        sampling=sampling,
                        frequency_step_cyc_per_mm=5.0,
                    )
                    sampling_results[sample_key][candidate_id][f"EPD{pupil_mm:g}"] = asdict(samples)

        for frequency_step in PROBE_FREQUENCY_STEPS:
            step_key = f"{frequency_step:g}"
            frequency_results[step_key] = {}
            for item in selected:
                candidate_id = item.candidate_id
                session.system.LoadFile(str(ref_paths[candidate_id].resolve()), False)
                frequency_results[step_key][candidate_id] = {}
                for pupil_mm in CORNEA_LOCK_B0_555_V2.pupils_mm:
                    samples = acquire_b0_q_samples(
                        session,
                        pupil_mm,
                        PROBE_DEFOCUS_D,
                        sampling=CORNEA_LOCK_B0_555_V2.mtfa_sampling,
                        frequency_step_cyc_per_mm=frequency_step,
                    )
                    frequency_results[step_key][candidate_id][f"EPD{pupil_mm:g}"] = asdict(samples)

    sampling_23 = _max_abs_difference(sampling_results["2"], sampling_results["3"])
    sampling_34 = _max_abs_difference(sampling_results["3"], sampling_results["4"])
    frequency_5_25 = _max_abs_difference(frequency_results["5"], frequency_results["2.5"])

    payload = {
        "formal_artifact": False,
        "runtime_passed": True,
        "passed_semantics": (
            "runtime acquisition completed successfully; this is not an automatic "
            "convergence-threshold decision"
        ),
        "requires_production_freeze_review": True,
        "settings": asdict(CORNEA_LOCK_B0_555_V2),
        "probe_defocus_d": PROBE_DEFOCUS_D,
        "candidate_ref_mono": {
            candidate_id: {
                "path": str(ref_paths[candidate_id].resolve()),
                "calibration": calibrations[candidate_id],
            }
            for candidate_id in ref_paths
        },
        "sampling_results": sampling_results,
        "frequency_step_results": frequency_results,
        "summary": {
            "max_abs_q_difference_sampling_2_to_3": sampling_23,
            "max_abs_q_difference_sampling_3_to_4": sampling_34,
            "max_abs_q_difference_frequency_5_to_2_5": frequency_5_25,
        },
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result_path": str(result_path.resolve()), **payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
