"""Probe one real Huygens PSF and derive B0 Q_lock without AS_HuygensMtf."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from whole_eye_mvp.b0_zos import q_lock_from_huygens_mtf
from whole_eye_mvp.domain import CORNEA_LOCK_B0_555_V1
from whole_eye_mvp.zos import HuygensPsfRunner, HuygensPsfSettings, open_zos_session
from whole_eye_mvp.zos.huygens_psf_mtf import mtf_from_huygens_psf

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=os.environ.get(INSTALL_ENV),
        help=f"OpticStudio installation directory; defaults to {INSTALL_ENV}",
    )
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    project_dir = args.project_dir.resolve()
    ref_path = project_dir / "diagnostics" / "task005d" / "b0_scan" / "REF_MONO_A0.zmx"
    if not ref_path.is_file():
        raise SystemExit(f"Required retained Phase B diagnostic is missing: {ref_path}")

    frozen = CORNEA_LOCK_B0_555_V1
    frozen.validate()
    settings = HuygensPsfSettings(
        pupil_sampling=frozen.huygens_pupil_sampling,
        image_sampling=frozen.huygens_image_sampling,
        image_delta_um=frozen.huygens_image_delta_um,
        wavelength_number=1,
        field_number=1,
        normalize=frozen.huygens_normalize,
        use_centroid=frozen.huygens_use_centroid,
        use_polarization=frozen.huygens_use_polarization,
    )

    with open_zos_session(args.install_dir) as session:
        session.system.LoadFile(str(ref_path), False)
        aperture = session.system.SystemData.Aperture
        aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
        aperture.ApertureValue = 3.0
        grid = HuygensPsfRunner(session.system, session.zosapi).run(settings)

    transformed = mtf_from_huygens_psf(grid)
    q_lock = q_lock_from_huygens_mtf(
        transformed.curve,
        maximum_frequency=frozen.b0_q_lock_max_cycles_per_mm,
    )
    curve = transformed.curve
    payload = {
        "passed": True,
        "formal_artifact": False,
        "source": str(ref_path),
        "pupil_mm": 3.0,
        "psf_shape": list(grid.shape),
        "psf_dx_um": grid.dx,
        "psf_dy_um": grid.dy,
        "psf_total_energy": grid.total_energy,
        "mtf_frequency_step_cyc_per_mm": transformed.frequency_step_cyc_per_mm,
        "mtf_frequency_max_cyc_per_mm": curve.frequency_cyc_per_mm[-1],
        "mtf0_average": curve.average[0],
        "q_lock_0_50": q_lock,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
