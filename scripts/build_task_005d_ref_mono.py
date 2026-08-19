"""Build the TASK-005D diagnostic distance cornea and calibrated REF_MONO candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.base_assets import base_asset_prescriptions
from whole_eye_mvp.cornea_assets import CORNEA_LOCK_BASE_ID
from whole_eye_mvp.cornea_zos import (
    build_distance_cornea_scaffold,
    measure_distance_cornea_scaffold,
    validate_distance_cornea_measurements,
)
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline
from whole_eye_mvp.ref_mono_calibration import (
    REF_MONO_SA_NEUTRAL_TOLERANCE_UM,
    measure_ref_mono_sa_delta,
    solve_ref_mono_neutral_conic,
)
from whole_eye_mvp.ref_mono_zos import (
    build_ref_mono_candidate,
    validate_ref_mono_measurements,
)
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
DISTANCE_NAME = "TASK005D_LB_DISTANCE_CORNEA.zmx"
REF_MONO_NAME = "TASK005D_REF_MONO_CORNEA_LOCK.zmx"
MAX_POWER_CONIC_ROUNDS = 2


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


def _require_output(path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise SystemExit(f"Diagnostic already exists; pass --overwrite to replace it: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(args.project_dir, baseline)
    lb = next(
        item
        for item in base_asset_prescriptions(baseline)
        if item.base_spec.base_id == CORNEA_LOCK_BASE_ID
    )
    lb_path = store.resolve(lb.relative_path)
    standard_eye_path = store.resolve(STANDARD_EYE_RELATIVE_PATH)
    if not lb_path.is_file():
        raise SystemExit(f"Required locked LB base is missing: {lb_path}")
    if not standard_eye_path.is_file():
        raise SystemExit(f"Required locked standard eye is missing: {standard_eye_path}")

    output_dir = args.project_dir / "diagnostics" / "task005d"
    distance_path = output_dir / DISTANCE_NAME
    ref_mono_path = output_dir / REF_MONO_NAME
    _require_output(distance_path, overwrite=args.overwrite)
    _require_output(ref_mono_path, overwrite=args.overwrite)

    with open_zos_session(args.install_dir) as session:
        build_distance_cornea_scaffold(session, baseline, lb_path, distance_path)
        distance_measurement = measure_distance_cornea_scaffold(session, distance_path)
        distance_findings = validate_distance_cornea_measurements(
            distance_measurement,
            baseline,
        )
        if distance_findings:
            raise SystemExit(
                "Distance-cornea scaffold failed: " + " | ".join(distance_findings)
            )

        initial_ref = build_ref_mono_candidate(
            session,
            baseline,
            distance_path,
            ref_mono_path,
        )
        initial_findings = validate_ref_mono_measurements(initial_ref, baseline)
        if initial_findings:
            raise SystemExit("Initial REF_MONO failed: " + " | ".join(initial_findings))

        radius = initial_ref.radius_ant_mm
        conic = initial_ref.conic
        rounds: list[dict[str, object]] = []
        final_ref = initial_ref
        final_sa = None

        for round_number in range(1, MAX_POWER_CONIC_ROUNDS + 1):
            calibration = solve_ref_mono_neutral_conic(
                session,
                baseline,
                standard_eye_path,
                radius,
            )
            conic = calibration.conic

            # Reload the distance scaffold and solve the LB focus again with the new conic.
            final_ref = build_ref_mono_candidate(
                session,
                baseline,
                distance_path,
                ref_mono_path,
                conic=conic,
                initial_radius_mm=radius,
            )
            ref_findings = validate_ref_mono_measurements(final_ref, baseline)
            if ref_findings:
                raise SystemExit(
                    f"REF_MONO round {round_number} failed: " + " | ".join(ref_findings)
                )
            radius = final_ref.radius_ant_mm
            final_sa = measure_ref_mono_sa_delta(
                session,
                baseline,
                standard_eye_path,
                radius,
                conic,
            )
            rounds.append(
                {
                    "round": round_number,
                    "standard_eye_calibration": asdict(calibration),
                    "lb_ref_mono": asdict(final_ref),
                    "refined_standard_eye_check": asdict(final_sa),
                }
            )
            if abs(final_sa.delta_c40_um) <= REF_MONO_SA_NEUTRAL_TOLERANCE_UM:
                break
        else:
            raise SystemExit(
                "REF_MONO radius/conic loop did not meet the standard-eye SA-neutral gate"
            )

    assert final_sa is not None
    payload = {
        "formal_artifact": False,
        "passed": True,
        "distance_cornea": {
            "path": str(distance_path.resolve()),
            "sha256": _sha256(distance_path),
            "measurements": asdict(distance_measurement),
        },
        "initial_ref_mono": asdict(initial_ref),
        "rounds": rounds,
        "final_ref_mono": {
            "path": str(ref_mono_path.resolve()),
            "sha256": _sha256(ref_mono_path),
            "measurements": asdict(final_ref),
        },
        "final_standard_eye_delta_c40_um": final_sa.delta_c40_um,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
