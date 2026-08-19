from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


def _load_export_module() -> object:
    path = Path(__file__).resolve().parents[2] / "scripts" / "export_task_007_residual_seeds.py"
    spec = importlib.util.spec_from_file_location("export_task_007_residual_seeds", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_task007_seed_export_is_diagnostic_only_and_hashes_three_payloads(tmp_path: Path) -> None:
    module = _load_export_module()
    manifest_path = module.export_residual_seeds(tmp_path)  # type: ignore[attr-defined]
    assert manifest_path.is_file()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["formal_artifact"] is False
    assert payload["tdd_999_cleared"] is False
    assert payload["opticstudio_validation_pending"] is True
    assert payload["residual_seed_version"] == "TASK007_RESIDUAL_SEEDS_546_v1"
    assert payload["validation_policy"]["global_defocus_tolerance_d"] == 0.125

    rows = payload["payloads"]
    assert [row["platform_id"] for row in rows] == ["WFS", "RAD", "HOA"]
    for row in rows:
        path = manifest_path.parent / row["payload_ref"]
        assert path.is_file()
        assert row["sha256"] == _sha256(path)
        assert row["sample_count"] == 601
        assert row["optic_radius_mm"] == 3.0
        assert row["normalization_radius_mm"] == 2.575
        assert row["formal_artifact"] is False
