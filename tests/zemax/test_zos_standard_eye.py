from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPOSITORY_ROOT / "scripts" / "build_task_005c_standard_eye.py"


def _install_dir() -> Path:
    value = os.environ.get(INSTALL_ENV)
    if not value:
        pytest.skip(f"Set {INSTALL_ENV} on a configured OpticStudio workstation.")
    return Path(value)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_worker(project_dir: Path, *extra_args: str) -> dict[str, Any]:
    environment = os.environ.copy()
    environment[INSTALL_ENV] = str(_install_dir())
    completed = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--project-dir",
            str(project_dir),
            *extra_args,
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=360,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    json_start = completed.stdout.find("{")
    assert json_start >= 0, completed.stdout
    payload, _ = json.JSONDecoder().raw_decode(completed.stdout[json_start:])
    return payload


@pytest.mark.zemax
def test_task_005c_standard_eye_build_reload_and_validate_without_rewrite(tmp_path: Path) -> None:
    project_dir = tmp_path / "project_mvp_2026_v2"
    built = _run_worker(project_dir)
    asset = project_dir / "models" / "assets" / "STD_IOL_EYE_2024.zos"
    hash_before = _sha256(asset)

    validated = _run_worker(project_dir, "--validate-only")
    hash_after = _sha256(asset)

    assert built["passed"] and validated["passed"]
    assert hash_after == hash_before
    measurement = validated["validation"]["measurements"]
    assert measurement["wavelength_nm"] == pytest.approx(546.0, abs=1.0)
    assert measurement["calibration_aperture_mm"] == pytest.approx(6.0, abs=0.001)
    assert measurement["corneal_sa_pupil_mm"] == pytest.approx(6.0, abs=0.001)
    assert measurement["corneal_c40_um_6mm"] == pytest.approx(0.258, abs=0.005)
    assert measurement["iol_footprint_mm_6mm"] == pytest.approx(5.15, abs=0.10)
    assert measurement["cornea_index"] == pytest.approx(1.376, abs=1e-6)
    assert measurement["medium_index"] == pytest.approx(1.336, abs=1e-6)
    assert measurement["medium_index_after_iol_ref"] == pytest.approx(1.336, abs=1e-6)
    assert measurement["best_focus_criterion"] == "WavefrontError"
    assert measurement["best_focus_iol_to_image_mm"] > 0
    assert measurement["reference_axial_length_mm"] == pytest.approx(23.950, abs=0.001)
    assert measurement["surface_count"] == 5
    assert measurement["stop_surface"] == 1
