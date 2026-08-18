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
from whole_eye_mvp.store import PROJECT_SCHEMA_VERSION, SchemaError, open_project_store


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
def test_settings_hashes_include_frozen_huygens_metric_and_zernike_settings() -> None:
    assert settings_hash(CORNEA_LOCK_B0_555_V1) == (
        "400be5ae8dc2d64fcf068f6b355b92e4af36753897bbca1dba7acc275346cd8e"
    )
    assert settings_hash(NOMINAL_MAIN_555_V1) == (
        "9e1822cfd9fb5b30cb8fdafa5c5092d8f434a7c62956420204dd6893539282b0"
    )


@pytest.mark.unit
def test_surrogate_naming_rejects_commercial_product_ids_case_insensitively() -> None:
    for model_id in ("WFS-like surrogate", "RAD-like surrogate", "HOA-like surrogate"):
        validate_surrogate_model_id(model_id)
    for model_id in ("Vivity", "TECNIS PureSee", "LuxSmart", "  vivity  ", "puresee"):
        with pytest.raises(ValueError, match="commercial"):
            validate_surrogate_model_id(model_id)


@pytest.mark.unit
def test_strict_csv_rejects_missing_columns_and_unknown_schema(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    path.write_text(
        f"schema_version,id\n{PROJECT_SCHEMA_VERSION},a\n",
        encoding="utf-8",
    )
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
    assert first != second and first.startswith("rerun-") and second.startswith("rerun-")
