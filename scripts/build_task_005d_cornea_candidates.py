"""Build TASK-005D A0, five B candidates, and C0 convergence diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.base_assets import base_asset_prescriptions
from whole_eye_mvp.cornea_assets import CORNEA_LOCK_BASE_ID, cornea_lock_prescriptions
from whole_eye_mvp.cornea_candidates_zos import (
    C0_TRANSITION_SLICES_CONVERGENCE,
    build_a_candidate,
    build_b_candidate,
    build_c_candidate,
    measure_cornea_file_wavefront,
)
from whole_eye_mvp.cornea_zos import (
    build_distance_cornea_scaffold,
    build_reference_cornea_scaffold,
)
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, CorneaId, ScientificBaseline
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
REFERENCE_NAME = "TASK005D_LB_REFERENCE_CORNEA.zmx"
DISTANCE_NAME = "TASK005D_LB_DISTANCE_CORNEA.zmx"
RESULT_NAME = "TASK_005D_CORNEA_CANDIDATES.json"


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _guard_outputs(paths: tuple[Path, ...], *, overwrite: bool) -> None:
    existing = tuple(path for path in paths if path.exists())
    if existing and not overwrite:
        text = ", ".join(str(path) for path in existing)
        raise SystemExit(f"Diagnostics already exist; pass --overwrite to replace them: {text}")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(project_dir, baseline)
    lb = next(
        item
        for item in base_asset_prescriptions(baseline)
        if item.base_spec.base_id == CORNEA_LOCK_BASE_ID
    )
    lb_path = store.resolve(lb.relative_path)
    if not lb_path.is_file():
        raise SystemExit(f"Required locked LB base is missing: {lb_path}")

    output_dir = project_dir / "diagnostics" / "task005d" / "corneas"
    reference_path = output_dir / REFERENCE_NAME
    distance_path = output_dir / DISTANCE_NAME
    a_path = output_dir / "CORNEA_A0.zmx"
    result_path = output_dir / RESULT_NAME
    b_prescriptions = tuple(
        item for item in cornea_lock_prescriptions(baseline) if item.cornea_id == CorneaId.B0
    )
    b_paths = tuple(
        output_dir / f"CORNEA_{prescription.candidate_id.replace('.', '_')}.zmx"
        for prescription in b_prescriptions
    )
    c_paths = tuple(
        output_dir / f"CORNEA_C0_N{slices}.zmx"
        for slices in C0_TRANSITION_SLICES_CONVERGENCE
    )
    _guard_outputs(
        (reference_path, distance_path, a_path, *b_paths, *c_paths, result_path),
        overwrite=args.overwrite,
    )

    with open_zos_session(args.install_dir) as session:
        build_reference_cornea_scaffold(session, baseline, lb_path, reference_path)
        reference_wavefront = measure_cornea_file_wavefront(session, reference_path)
        reference_c40 = reference_wavefront.c40_um

        build_distance_cornea_scaffold(session, baseline, lb_path, distance_path)
        distance_wavefront = measure_cornea_file_wavefront(session, distance_path)

        a = build_a_candidate(
            session,
            baseline,
            distance_path,
            a_path,
            reference_c40,
        )
        if not a.target_passed:
            raise SystemExit("A0 achieved ΔC40 is outside its construction tolerance")

        b_results = []
        for prescription, path in zip(b_prescriptions, b_paths, strict=True):
            result = build_b_candidate(
                session,
                prescription,
                distance_path,
                path,
                reference_c40,
            )
            if not result.target_passed:
                raise SystemExit(
                    f"{prescription.candidate_id} achieved ΔC40 is outside construction tolerance"
                )
            b_results.append(result)

        c_results = [
            build_c_candidate(
                session,
                baseline,
                distance_path,
                path,
                reference_c40,
                transition_slices=slices,
            )
            for slices, path in zip(
                C0_TRANSITION_SLICES_CONVERGENCE,
                c_paths,
                strict=True,
            )
        ]

    c_by_slices = {int(result.control_value): result for result in c_results}
    c_convergence = {
        "delta_c40_N4_to_N8_um": (
            c_by_slices[8].achieved_delta_c40_um - c_by_slices[4].achieved_delta_c40_um
        ),
        "delta_c40_N8_to_N16_um": (
            c_by_slices[16].achieved_delta_c40_um - c_by_slices[8].achieved_delta_c40_um
        ),
    }
    payload = {
        "formal_artifact": False,
        "passed": True,
        "reference_cornea": {
            "path": str(reference_path.resolve()),
            "sha256": _sha256(reference_path),
            "wavefront": asdict(reference_wavefront),
        },
        "distance_cornea": {
            "path": str(distance_path.resolve()),
            "sha256": _sha256(distance_path),
            "wavefront": asdict(distance_wavefront),
        },
        "A0": {
            "path": str(a_path.resolve()),
            "sha256": _sha256(a_path),
            "measurement": asdict(a),
        },
        "B_candidates": [
            {
                "path": str(path.resolve()),
                "sha256": _sha256(path),
                "measurement": asdict(result),
            }
            for path, result in zip(b_paths, b_results, strict=True)
        ],
        "C0_convergence": [
            {
                "path": str(path.resolve()),
                "sha256": _sha256(path),
                "measurement": asdict(result),
            }
            for path, result in zip(c_paths, c_results, strict=True)
        ],
        "C0_convergence_summary": c_convergence,
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result_path": str(result_path.resolve()), **payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
