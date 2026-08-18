"""Run each real OpticStudio gate in a fresh Python.NET process."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GATES = (
    "tests/zemax/test_zos_huygens_psf.py",
    "tests/zemax/test_zos_surface_mapping.py",
    "tests/zemax/test_zos_worker_gate.py",
    "tests/zemax/test_zos_zernike.py",
    "tests/zemax/test_zos_base_assets.py",
    "tests/zemax/test_zos_standard_eye.py",
)


def main() -> None:
    if not os.environ.get(INSTALL_ENV):
        raise SystemExit(f"Set {INSTALL_ENV} before running the OpticStudio gates.")

    for gate in GATES:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:faulthandler",
                gate,
                "-q",
            ],
            cwd=REPOSITORY_ROOT,
            check=False,
        )
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
