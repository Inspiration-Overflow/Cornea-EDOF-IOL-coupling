from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp.domain import (
    CORNEA_LOCK_B0_555_V1,
    NOMINAL_MAIN_555_V1,
    ArtifactRecord,
    ScientificBaseline,
)
from whole_eye_mvp.quality import (
    new_run_id,
    read_csv_strict,
    settings_hash,
    validate_surrogate_model_id,
)
from whole_eye_mvp.store import SchemaError, open_project_store


@pytest.mark.unit
def test_locked_artifact_tamper_is_detected(tmp_path: Path) -> None:
    store = open_project_store(tmp_path / "p", ScientificBaseline("b"))
    source = tmp_path / "asset.zos"
    source.write_bytes(b"original")
    ref = store.record_artifact(
        source,
        ArtifactRecord("A0", "zos", "models/assets/A0.zos", "b"),
        lock=True,
    )
    assert store.verify_artifact(ref)
    store.resolve(ref.relative_path).write_bytes(b"tampered")
    assert not store.verify_artifact(ref)


@pytest.mark.unit
def test_settings_hashes_are_frozen_regression_values() -> None:
    assert settings_hash(CORNEA_LOCK_B0_555_V1) == (
        "2a588f37ed60795c475354a1a931fc0329b91d077107aac224f9f4cdfd645b72"
    )
    assert settings_hash(NOMINAL_MAIN_555_V1) == (
        "5832d39a4f8a871d04d205bc3a7aafdf2e875ff3423da319baf09e5894097169"
    )


@pytest.mark.unit
def test_surrogate_naming_rejects_exact_commercial_product_ids() -> None:
    for model_id in ("WFS-like surrogate", "RAD-like surrogate", "HOA-like surrogate"):
        validate_surrogate_model_id(model_id)
    for model_id in ("Vivity", "TECNIS PureSee", "LuxSmart"):
        with pytest.raises(ValueError, match="commercial"):
            validate_surrogate_model_id(model_id)


@pytest.mark.unit
def test_strict_csv_rejects_missing_columns_and_unknown_schema(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    path.write_text("schema_version,id\n1,a\n", encoding="utf-8")
    assert read_csv_strict(path, required_columns=("schema_version", "id"))[0]["id"] == "a"
    with pytest.raises(SchemaError, match="schema mismatch"):
        read_csv_strict(path, required_columns=("schema_version", "id", "value"))
    path.write_text("schema_version,id\n99,a\n", encoding="utf-8")
    with pytest.raises(SchemaError, match="schema version"):
        read_csv_strict(path, required_columns=("schema_version", "id"))


@pytest.mark.unit
def test_rerun_ids_are_always_new() -> None:
    first = new_run_id("rerun")
    second = new_run_id("rerun")
    assert first != second
    assert first.startswith("rerun-") and second.startswith("rerun-")
