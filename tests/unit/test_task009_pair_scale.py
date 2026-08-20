from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from whole_eye_mvp.analysis_zos_pair_scale import (
    EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
    TASK009_PAIR_MONO_MTF_ACQUISITION,
    ZosMtfaPairScaleAnalysisBackend,
    frequencies_for_pair_reference,
)
from whole_eye_mvp.metrics import mm_per_degree

SCRIPT_PATH = Path("scripts/run_task_009_pair_mono_scale_representative.py")


def _load_task009_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("task009_pair_scale_script", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TASK-009 paired-scale script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
def test_pair_mono_acquisition_contract_is_exactly_frozen() -> None:
    contract = TASK009_PAIR_MONO_MTF_ACQUISITION
    assert contract.contract_id == "TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2"
    assert contract.production_operand == "MTFA"
    assert contract.grid == 1
    assert contract.data_type == 0
    assert contract.wavelength_number == 1
    assert contract.field_number == 1
    assert contract.frequency_axis == "direct_0_to_60_cpd_via_paired_MONO_EFFL"
    assert contract.contract_hash == EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH
    assert EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH == (
        "f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d"
    )


@pytest.mark.unit
def test_pair_reference_frequency_grid_uses_one_fixed_reference_scale() -> None:
    reference_effl_mm = 17.0
    cpd = (0.0, 20.0, 40.0, 60.0)
    frequencies = frequencies_for_pair_reference(reference_effl_mm, cpd)
    scale = mm_per_degree(reference_effl_mm)
    assert frequencies == pytest.approx(tuple(value / scale for value in cpd), abs=1e-12)

    # A pathological state EFFL must not enter this conversion. The same pair reference
    # gives the same requested cycles/mm regardless of the EDOF state's diagnostic EFFL.
    pathological_state_effl_mm = 9.633329064114418
    assert pathological_state_effl_mm != reference_effl_mm
    assert frequencies_for_pair_reference(reference_effl_mm, cpd) == pytest.approx(
        frequencies, abs=1e-12
    )


@pytest.mark.unit
def test_pair_scale_backend_fails_closed_without_valid_reference(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="pair reference"):
        ZosMtfaPairScaleAnalysisBackend(
            SimpleNamespace(),
            tmp_path,
            {},
            {},
            sampling=128,
            pair_reference_effl_mm={},
        )

    with pytest.raises(ValueError, match="pair reference"):
        ZosMtfaPairScaleAnalysisBackend(
            SimpleNamespace(),
            tmp_path,
            {},
            {},
            sampling=128,
            pair_reference_effl_mm={"PAIR": 0.0},
        )


@pytest.mark.unit
def test_pair_report_uses_config_identity_not_configresult_shortcuts(monkeypatch) -> None:
    task009_script = _load_task009_script()

    def result(config_id: str, pair_key: str):
        return SimpleNamespace(
            config=SimpleNamespace(
                config_id=config_id,
                pair_key=pair_key,
                optic_state="MONO" if "MONO" in config_id else "EDOF",
                pupil_mm=5.0,
            ),
            distance_peak_retina_d=0.0,
            distance_peak_mtfa=0.1,
            mtfa_at_zero_d=0.1,
            dof50_far_d=0.25,
            dof50_near_d=-0.5,
            dof50_width_d=0.75,
            tf_mtfa_mean=0.05,
            aberrations=SimpleNamespace(c40_um=0.0, c60_um=0.0, hoa_rms_um=0.0),
            model_hash_before="m",
            entity_fingerprint_before="e",
            analysis_settings_hash="s",
            hoa_settings_id="h",
            hoa_settings_hash="hh",
        )

    mono = result("CFG_X_MONO", "PAIR_X")
    edof = result("CFG_X_EDOF", "PAIR_X")
    monkeypatch.setattr(
        task009_script,
        "matched_pair_delta",
        lambda _mono, _edof: SimpleNamespace(
            pair_key="PAIR_X",
            deltas={"distance_peak_retina_d": -0.25, "distance_peak_mtfa": -0.01},
        ),
    )
    pair_key, block = task009_script._pair_result_block(mono, edof)
    assert pair_key == "PAIR_X"
    assert block["mono"]["config_id"] == "CFG_X_MONO"
    assert block["edof"]["config_id"] == "CFG_X_EDOF"
    assert block["delta_f_residual_d"] == pytest.approx(-0.25)


@pytest.mark.unit
def test_task009_script_has_no_known_configresult_identity_shortcuts() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden = (
        "mono_result.config_id",
        "edof_result.config_id",
        "mono_result.pair_key",
        "edof_result.pair_key",
        "config_result.config_id",
        "config_result.pair_key",
    )
    for token in forbidden:
        assert token not in text, f"ConfigResult identity shortcut reintroduced: {token}"
