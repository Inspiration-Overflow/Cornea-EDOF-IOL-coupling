from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from whole_eye_mvp.residual_payload import (
    RadialResidualCandidate,
    build_hoa_residual_candidate,
    build_rad_residual_candidate,
    build_wfs_residual_candidate,
)
from whole_eye_mvp.residual_policy import RESIDUAL_VALIDATION_546_V1
from whole_eye_mvp.residual_profiles import (
    HOA_BENCH_SEED,
    RAD_PATENT_ZONES,
    RESIDUAL_SEED_VERSION,
    WFS_PATENT_SEED,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_candidate_csv(directory: Path, candidate: RadialResidualCandidate) -> dict[str, object]:
    filename = f"TASK_007_{candidate.platform_id}_RESIDUAL_SEED.csv"
    path = directory / filename
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("radius_mm", "raw_opd_um", "normalized_opd_um", "surface_sag_um"))
        writer.writerows(
            zip(
                candidate.radii_mm,
                candidate.raw_opd_um,
                candidate.normalized_opd_um,
                candidate.surface_sag_um,
                strict=True,
            )
        )
    return {
        "platform_id": candidate.platform_id,
        "surface_role": candidate.surface_role,
        "payload_ref": filename,
        "sha256": _sha256(path),
        "sample_count": len(candidate.radii_mm),
        "optic_radius_mm": candidate.optic_radius_mm,
        "normalization_radius_mm": candidate.normalization_radius_mm,
        "sample_step_mm": candidate.sample_step_mm,
        "removed_low_order": asdict(candidate.removed_low_order),
        "formal_artifact": False,
    }


def export_residual_seeds(project_dir: Path) -> Path:
    project_dir = project_dir.resolve()
    output_dir = project_dir / "diagnostics" / "task007" / "residual_seeds_546_v1"
    output_dir.mkdir(parents=True, exist_ok=True)

    candidates = (
        build_wfs_residual_candidate(),
        build_rad_residual_candidate(),
        build_hoa_residual_candidate(),
    )
    payloads = [_write_candidate_csv(output_dir, candidate) for candidate in candidates]
    manifest = {
        "schema_version": 1,
        "formal_artifact": False,
        "task": "TASK-007",
        "residual_seed_version": RESIDUAL_SEED_VERSION,
        "carrier_scaffold": asdict(CONTROLLED_IOL_CARRIER_546_V1),
        "validation_policy": asdict(RESIDUAL_VALIDATION_546_V1),
        "validation_policy_hash": RESIDUAL_VALIDATION_546_V1.policy_hash,
        "wfs_public_seed": asdict(WFS_PATENT_SEED),
        "rad_public_seed_zones": [asdict(zone) for zone in RAD_PATENT_ZONES],
        "hoa_bench_seed": asdict(HOA_BENCH_SEED),
        "payloads": payloads,
        "opticstudio_validation_pending": True,
        "tdd_999_cleared": False,
    }
    manifest_path = output_dir / "TASK_007_RESIDUAL_SEED_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export deterministic TASK-007 residual seeds")
    parser.add_argument("--project-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    manifest_path = export_residual_seeds(args.project_dir)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
