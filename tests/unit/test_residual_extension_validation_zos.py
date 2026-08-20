from __future__ import annotations

import json
from pathlib import Path

from whole_eye_mvp.residual_extension_validation_zos import (
    VALIDATION_INDEX_NAME,
    _write_current_pointer,
    _write_validation_index,
    validation_passed,
)


def _payload(carrier_sha: str, *, passed: bool) -> dict[str, object]:
    return {
        "schema_version": 1,
        "carrier_id": "CAR_LB_AL2395_N0_WFS",
        "base_id": "LB_AL2395",
        "cornea_id": "N0",
        "platform_id": "WFS",
        "carrier_sha256": carrier_sha,
        "residual_id": "RES_WFS",
        "residual_sha256": "r" * 64,
        "policy_id": "RESIDUAL_VALIDATION_546_v1",
        "passed": passed,
    }


def _write_record(root: Path, name: str, payload: dict[str, object]) -> Path:
    record = root / "CAR_LB_AL2395_N0_WFS" / name / "VALIDATION.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return record


def test_validation_index_tracks_current_record_without_deleting_history(tmp_path: Path) -> None:
    root = tmp_path / "validations"
    old_payload = _payload("a" * 64, passed=False)
    old_record = _write_record(root, "old", old_payload)
    _write_current_pointer(root, old_record, old_payload)
    _write_validation_index(root)
    first = json.loads((root / VALIDATION_INDEX_NAME).read_text(encoding="utf-8"))
    assert first["validation_count"] == 1
    assert first["all_passed"] is False

    new_payload = _payload("b" * 64, passed=True)
    new_record = _write_record(root, "new", new_payload)
    _write_current_pointer(root, new_record, new_payload)
    _write_validation_index(root)
    second = json.loads((root / VALIDATION_INDEX_NAME).read_text(encoding="utf-8"))

    assert old_record.is_file()
    assert new_record.is_file()
    assert second["validation_count"] == 1
    assert second["all_passed"] is True
    assert second["records"][0]["carrier_sha256"] == "b" * 64
    assert second["records"][0]["record_relative_path"].endswith("new/VALIDATION.json")


def test_validation_passed_is_strict_boolean_true() -> None:
    assert validation_passed({"passed": True}) is True
    assert validation_passed({"passed": False}) is False
    assert validation_passed({}) is False
