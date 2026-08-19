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
BUILD_SCRIPT = REPOSITORY_ROOT / "scripts" / "build_task_005b_base_assets.py"


def _install_dir() -> Path:
    value = os.environ.get(INSTALL_ENV)
    if not value:
        pytest.skip(f"Set {INSTALL_ENV} on a configured OpticStudio workstation.")
    return Path(value)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_base_worker(project_dir: Path, *extra_args: str) -> dict[str, Any]:
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
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    json_start = completed.stdout.find("{")
    assert json_start >= 0, completed.stdout
    payload, _ = json.JSONDecoder().raw_decode(completed.stdout[json_start:])
    return payload


@pytest.mark.zemax
def test_task_005b_base_assets_build_reload_and_validate_without_rewrite(tmp_path: Path) -> None:
    project_dir = tmp_path / "project_mvp_2026_v2"
    built = _run_base_worker(project_dir)
    paths = (
        project_dir / "models" / "assets" / "BASE_LB_PSEUDOPHAKIC.zos",
        project_dir / "models" / "assets" / "BASE_ATC_M3_PSEUDOPHAKIC.zos",
    )
    hashes_before = tuple(_sha256(path) for path in paths)

    validated = _run_base_worker(project_dir, "--validate-only")
    hashes_after = tuple(_sha256(path) for path in paths)

    assert built["passed"] and validated["passed"]
    assert hashes_after == hashes_before
    measurements = [item["measurements"] for item in validated["validations"]]
    assert [item["axial_length_mm"] for item in measurements] == pytest.approx(
        [23.950, 24.477], abs=0.001
    )
    assert all(
        item["cornea_reference_slot_mm"] == pytest.approx(0.0, abs=1e-12)
        and item["post_cornea_to_stop_mm"] == pytest.approx(3.150, abs=0.001)
        and item["post_cornea_to_iol_ant_mm"] == pytest.approx(4.500, abs=0.001)
        and item["aqueous_index_after_cornea"] == pytest.approx(1.336, abs=1e-6)
        and item["aqueous_index_after_stop"] == pytest.approx(1.336, abs=1e-6)
        and item["vitreous_index"] == pytest.approx(1.336, abs=1e-6)
        and item["image_is_plane"]
        and item["image_thickness_solve"] == "Fixed"
        for item in measurements
    )