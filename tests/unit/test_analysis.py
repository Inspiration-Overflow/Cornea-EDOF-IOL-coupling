from __future__ import annotations

import math
from dataclasses import replace

import pytest

from whole_eye_mvp.analysis import (
    AberrationSummary,
    AnalysisError,
    ConfigArtifacts,
    ConfigResult,
    ExportError,
    matched_pair_delta,
    summarize_mtfa_curve,
    validate_completed_result,
    validate_selection,
    with_shape_axis,
)
from whole_eye_mvp.domain import NOMINAL_MAIN_FFT_MTF_555_V2, AnalysisSettings, OpticState
from whole_eye_mvp.manifest import NominalConfig
from whole_eye_mvp.quality import settings_hash
from whole_eye_mvp.zos import TASK009_MFE_FULL_HOA_555_V1


def config(state: str) -> NominalConfig:
    is_edof = state == OpticState.EDOF
    return NominalConfig(
        config_id=f"CFG_{state}",
        carrier_id="CAR_X",
        base_id="LB_AL2395",
        cornea_id="A0",
        platform_id="WFS",
        optic_state=state,
        pupil_mm=3.0,
        carrier_lock_hash="lock-hash",
        residual_id="RES_WFS" if is_edof else None,
        residual_sha256="res-sha" if is_edof else None,
        residual_validation_policy_id="POLICY_v1" if is_edof else None,
        residual_validation_policy_hash="policy-hash" if is_edof else None,
    )


def rows(peak_d: float = 0.0, *, analysis_settings=NOMINAL_MAIN_FFT_MTF_555_V2):
    defocus = analysis_settings.defocus_grid()
    peak_i = defocus.index(peak_d)
    mtfa = tuple(max(0.05, 0.8 - abs(index - peak_i) * 0.10) for index in range(len(defocus)))
    columns = [tuple(value * (1 - index * 0.05) for value in mtfa) for index in range(6)]
    return with_shape_axis(defocus, mtfa, columns)


def result(
    state: str,
    *,
    peak_d: float = 0.0,
    run_id: str = "run",
    analysis_settings=NOMINAL_MAIN_FFT_MTF_555_V2,
    peak_window_d: float = 0.5,
) -> ConfigResult:
    tf_rows = rows(peak_d, analysis_settings=analysis_settings)
    summary = summarize_mtfa_curve(tf_rows, peak_window_d=peak_window_d)
    return ConfigResult(
        config=config(state),
        run_id=run_id,
        rows=tf_rows,
        distance_peak_retina_d=float(summary["distance_peak_retina_d"]),
        distance_peak_mtfa=float(summary["distance_peak_mtfa"]),
        mtfa_at_zero_d=float(summary["mtfa_at_zero_d"]),
        dof50_far_d=summary["dof50_far_d"],
        dof50_near_d=summary["dof50_near_d"],
        dof50_width_d=float(summary["dof50_width_d"]),
        dof50_far_censored=bool(summary["dof50_far_censored"]),
        dof50_near_censored=bool(summary["dof50_near_censored"]),
        tf_mtfa_mean=float(summary["tf_mtfa_mean"]),
        peak_search_censored=bool(summary["peak_search_censored"]),
        aberrations=AberrationSummary(0.1, 0.02, 0.15),
        analysis_settings_hash=settings_hash(analysis_settings),
        hoa_settings_id=TASK009_MFE_FULL_HOA_555_V1.settings_id,
        hoa_settings_hash=TASK009_MFE_FULL_HOA_555_V1.settings_hash,
        cornea_footprint_mm=5.5,
        stop_footprint_mm=3.0,
        iol_footprint_mm=5.0,
        iol_optical_diameter_mm=6.0,
        model_hash_before="hash",
        model_hash_after="hash",
        entity_fingerprint_before="entity",
        entity_fingerprint_after="entity",
        retina_position_before_mm=23.95,
        retina_position_after_mm=23.95,
        iol_position_before_mm=4.5,
        iol_position_after_mm=4.5,
        elp_before_mm=4.5,
        elp_after_mm=4.5,
        unintended_vignetting=False,
        artifacts=ConfigArtifacts("a.zmx", "tf.csv", "tf.png", "mtf.png"),
        completed=True,
    )


@pytest.mark.unit
def test_shape_axis_is_retina_axis_minus_distance_peak() -> None:
    data = rows()
    assert len(data) == 15
    assert next(row for row in data if row.defocus_retina_d == 0).defocus_shape_d == 0
    assert data[0].defocus_shape_d == pytest.approx(0.5)


@pytest.mark.unit
def test_selection_rejects_external_duplicate_and_duplicate_manifest_id() -> None:
    manifest = [config("MONO"), config("EDOF")]
    assert len(validate_selection(["CFG_MONO"], manifest)) == 1
    with pytest.raises(AnalysisError, match="external"):
        validate_selection(["NOPE"], manifest)
    with pytest.raises(AnalysisError, match="duplicate"):
        validate_selection(["CFG_MONO", "CFG_MONO"], manifest)
    with pytest.raises(AnalysisError, match="duplicate"):
        validate_selection(["CFG_MONO"], [manifest[0], manifest[0]])


@pytest.mark.unit
def test_completed_result_contract_and_artifact_rule() -> None:
    good = result("MONO")
    validate_completed_result(good, expected_config=good.config, expected_run_id="run")

    with pytest.raises(AnalysisError, match="model"):
        validate_completed_result(replace(good, model_hash_after="changed"))
    with pytest.raises(AnalysisError, match="fingerprint"):
        validate_completed_result(replace(good, entity_fingerprint_after="changed"))
    with pytest.raises(AnalysisError, match="IOL position"):
        validate_completed_result(replace(good, iol_position_after_mm=4.6))
    with pytest.raises(AnalysisError, match="ELP"):
        validate_completed_result(replace(good, elp_after_mm=4.6))
    with pytest.raises(AnalysisError, match="vignetting"):
        validate_completed_result(replace(good, unintended_vignetting=True))
    with pytest.raises(ExportError):
        validate_completed_result(
            replace(good, artifacts=ConfigArtifacts("", "tf.csv", "tf", "m"))
        )


@pytest.mark.unit
def test_completed_result_rejects_wrong_config_run_nan_summary_and_shape_axis() -> None:
    good = result("MONO")
    with pytest.raises(AnalysisError, match="different manifest config"):
        validate_completed_result(good, expected_config=config("EDOF"))
    with pytest.raises(AnalysisError, match="wrong run_id"):
        validate_completed_result(good, expected_run_id="other-run")
    with pytest.raises(AnalysisError, match="finite"):
        validate_completed_result(
            replace(good, aberrations=AberrationSummary(math.nan, 0.02, 0.15))
        )
    with pytest.raises(AnalysisError, match="distance_peak_retina_d"):
        validate_completed_result(replace(good, distance_peak_retina_d=0.25))
    with pytest.raises(AnalysisError, match="analysis-settings"):
        validate_completed_result(replace(good, analysis_settings_hash="wrong"))

    bad_rows = list(good.rows)
    bad_rows[0] = replace(bad_rows[0], defocus_shape_d=999.0)
    with pytest.raises(AnalysisError, match="shape-recentered"):
        validate_completed_result(replace(good, rows=tuple(bad_rows)))


@pytest.mark.unit
def test_matched_pair_delta_is_edof_minus_mono_with_full_pair_invariants() -> None:
    mono = result("MONO", peak_d=0.0)
    edof = replace(
        result("EDOF", peak_d=0.25),
        aberrations=AberrationSummary(0.2, 0.03, 0.18),
    )
    delta = matched_pair_delta(mono, edof)
    assert delta.deltas["distance_peak_retina_d"] == pytest.approx(0.25)
    assert delta.deltas["c40_um"] == pytest.approx(0.1)
    assert "dof50_width_d" in delta.deltas
    assert "tf_mtfa_mean" in delta.deltas

    with pytest.raises(AnalysisError, match="carrier_lock_hash"):
        matched_pair_delta(mono, replace(edof, config=replace(edof.config, carrier_lock_hash="other")))


@pytest.mark.unit
def test_matched_pair_delta_accepts_supplemental_49_plane_settings() -> None:
    settings = AnalysisSettings(
        settings_id="SUPPLEMENTAL_TF_MTF_555_v1",
        wavelength_nm=555.0,
        pupils_mm=(3.0, 5.0),
        defocus_start_d=1.0,
        defocus_stop_d=-5.0,
        defocus_step_d=-0.125,
    )
    mono = result("MONO", analysis_settings=settings, peak_window_d=1.0)
    edof = result(
        "EDOF",
        peak_d=0.125,
        analysis_settings=settings,
        peak_window_d=1.0,
    )

    delta = matched_pair_delta(
        mono,
        edof,
        analysis_settings=settings,
        peak_window_d=1.0,
    )

    assert len(mono.rows) == 49
    assert delta.deltas["distance_peak_retina_d"] == pytest.approx(0.125)
