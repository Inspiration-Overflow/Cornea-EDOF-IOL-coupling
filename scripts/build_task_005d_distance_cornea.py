"""Build and reload the TASK-005D physical -3 D distance-cornea diagnostic scaffold."""

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
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
DEFAULT_NAME = "TASK005D_LB_DISTANCE_CORNEA.zmx"


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
    parser.add_argument("--output", type=Path)
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

    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(args.project_dir, baseline)
    base = next(
        item
        for item in base_asset_prescriptions(baseline)
        if item.base_spec.base_id == CORNEA_LOCK_BASE_ID
    )
    base_path = store.resolve(base.relative_path)
    if not base_path.is_file():
        raise SystemExit(f"Required locked LB base is missing: {base_path}")

    output = args.output or (
        args.project_dir / "diagnostics" / "task005d" / DEFAULT_NAME
    )
    if output.exists() and not args.overwrite:
        raise SystemExit(f"Diagnostic already exists; pass --overwrite to replace it: {output}")

    with open_zos_session(args.install_dir) as session:
        build_distance_cornea_scaffold(session, baseline, base_path, output)
        measurement = measure_distance_cornea_scaffold(session, output)
        findings = validate_distance_cornea_measurements(measurement, baseline)

    payload = {
        "formal_artifact": False,
        "passed": not findings,
        "path": str(output.resolve()),
        "sha256": _sha256(output),
        "measurements": asdict(measurement),
        "findings": list(findings),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
