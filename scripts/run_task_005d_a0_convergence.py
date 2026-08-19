"""Check A0 Binary4 transition discretization at the already calibrated inner conic."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.cornea_assets import cornea_lock_prescriptions
from whole_eye_mvp.cornea_candidates_zos import (
    _a_zones,
    measure_best_focus_cornea_wavefront,
)
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, CorneaId, ScientificBaseline
from whole_eye_mvp.zos import SequentialEditor, open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
PHASE_A_RESULT = "TASK_005D_CORNEA_CANDIDATES.json"
RESULT_NAME = "TASK_005D_A0_CONVERGENCE.json"
SLICES = (4, 8, 16)


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


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    cornea_dir = project_dir / "diagnostics" / "task005d" / "corneas"
    phase_a_path = cornea_dir / PHASE_A_RESULT
    if not phase_a_path.is_file():
        raise SystemExit(f"Required Phase A JSON is missing: {phase_a_path}")

    phase_a = json.loads(phase_a_path.read_text(encoding="utf-8"))
    a_measurement = phase_a["A0"]["measurement"]
    if a_measurement["control_name"] != "inner_zone_conic":
        raise SystemExit("Phase A A0 control is not inner_zone_conic")
    inner_conic = float(a_measurement["control_value"])
    reference_c40_um = float(phase_a["reference_cornea"]["wavefront"]["c40_um"])
    distance_path = Path(phase_a["distance_cornea"]["path"])
    if not distance_path.is_file():
        raise SystemExit(f"Required distance-cornea file is missing: {distance_path}")

    prescription = cornea_lock_prescriptions(baseline)[0]
    if prescription.cornea_id != CorneaId.A0:
        raise SystemExit("A0 prescription ordering mismatch")

    output_dir = project_dir / "diagnostics" / "task005d" / "a0_convergence"
    result_path = output_dir / RESULT_NAME
    output_paths = tuple(output_dir / f"CORNEA_A0_N{slices}.zmx" for slices in SLICES)
    existing = tuple(path for path in (*output_paths, result_path) if path.exists())
    if existing and not args.overwrite:
        raise SystemExit(
            "A0 convergence outputs already exist; pass --overwrite to replace them: "
            + ", ".join(str(path) for path in existing)
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, object]] = []
    with open_zos_session(args.install_dir) as session:
        for slices, output_path in zip(SLICES, output_paths, strict=True):
            session.system.LoadFile(str(distance_path.resolve()), False)
            editor = SequentialEditor(session.system, session.zosapi)
            editor.set_comment(1, f"CORNEA_ANT_A0_N{slices}")
            zones = _a_zones(
                prescription,
                inner_conic,
                transition_slices=slices,
            )
            editor.configure_binary4(1, zones)
            editor.set_radius_conic(
                1,
                radius_mm=prescription.distance_front_radius_mm,
                conic=inner_conic,
            )
            editor.surface(1).SemiDiameter = zones[-1].radial_aperture
            measurement = measure_best_focus_cornea_wavefront(session)
            editor.save_as(output_path)
            results.append(
                {
                    "transition_slices": slices,
                    "path": str(output_path.resolve()),
                    "sha256": _sha256(output_path),
                    "achieved_delta_c40_um": measurement.c40_um - reference_c40_um,
                    "wavefront": asdict(measurement),
                }
            )

    by_slices = {int(item["transition_slices"]): item for item in results}

    def delta(field: str, left: int, right: int) -> float:
        if field == "achieved_delta_c40_um":
            return float(by_slices[right][field]) - float(by_slices[left][field])
        left_wavefront = by_slices[left]["wavefront"]
        right_wavefront = by_slices[right]["wavefront"]
        assert isinstance(left_wavefront, dict) and isinstance(right_wavefront, dict)
        return float(right_wavefront[field]) - float(left_wavefront[field])

    payload = {
        "formal_artifact": False,
        "inner_conic_fixed": inner_conic,
        "reference_c40_um": reference_c40_um,
        "results": results,
        "differences": {
            "delta_c40_N4_to_N8_um": delta("achieved_delta_c40_um", 4, 8),
            "delta_c40_N8_to_N16_um": delta("achieved_delta_c40_um", 8, 16),
            "delta_z37_N4_to_N8_waves": delta("z37_waves", 4, 8),
            "delta_z37_N8_to_N16_waves": delta("z37_waves", 8, 16),
        },
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result_path": str(result_path), **payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
