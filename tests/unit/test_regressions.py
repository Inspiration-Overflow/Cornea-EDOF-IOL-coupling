from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest

from whole_eye_mvp.domain import (
    CORNEA_LOCK_B0_555_V2,
    NOMINAL_MAIN_FFT_MTF_555_V2,
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
def test_settings_hashes_are_stable_and_main_fft_mtf_hash_is_frozen() -> None:
    b0_hash = settings_hash(CORNEA_LOCK_B0_555_V2)
    main_hash = settings_hash(NOMINAL_MAIN_FFT_MTF_555_V2)
    assert b0_hash == "aee210e884aa59f74e2963efddca9fc789f2b4e85de521606348d1e586790b8e"
    assert main_hash == "0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc"
    assert main_hash == settings_hash(NOMINAL_MAIN_FFT_MTF_555_V2)
    changed = replace(NOMINAL_MAIN_FFT_MTF_555_V2, fft_mtf_sampling=256)
    assert settings_hash(changed) != main_hash


@pytest.mark.unit
@pytest.mark.parametrize(
    "settings",
    (
        replace(NOMINAL_MAIN_FFT_MTF_555_V2, wavelength_nm=math.nan),
        replace(NOMINAL_MAIN_FFT_MTF_555_V2, defocus_step_d=math.inf),
        replace(NOMINAL_MAIN_FFT_MTF_555_V2, pupils_mm=(3.0, math.nan)),
        replace(NOMINAL_MAIN_FFT_MTF_555_V2, mtfa_max_cpd=math.nan),
        replace(NOMINAL_MAIN_FFT_MTF_555_V2, mtf_sample_frequencies_cpd=(10.0, math.inf)),
    ),
)
def test_analysis_settings_reject_nonfinite_values(settings) -> None:
    with pytest.raises(ValueError, match="finite"):
        settings.validate()


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
