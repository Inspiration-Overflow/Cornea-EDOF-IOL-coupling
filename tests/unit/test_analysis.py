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
    validate_completed_result,
    validate_selection,
    with_shape_axis,
)
from whole_eye_mvp.domain import NOMINAL_MAIN_555_V1, OpticState
from whole_eye_mvp.manifest import NominalConfig


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
    )


def rows(peak_d: float = 0.0):
    defocus = NOMINAL_MAIN_555_V1.defocus_grid()
    peak_i = defocus.index(peak_d)
    vsotf = tuple(max(0.05, 1 - abs(index - peak_i) * 0.15) for index in range(len(defocus)))
    mtfa = tuple(value * 0.7 for value in vsotf)
    columns = [tuple(value * (1 - index * 0.05) for value in vsotf) for index in range(6)]
    return with_shape_axis(defocus, mtfa, vsotf, columns)


def result(state: str, *, peak_d: float = 0.0, run_id: str = "run") -> ConfigResult:
    return ConfigResult(
        config(state),
        run_id,
        rows(peak_d),
        peak_d,
        AberrationSummary(0.1, 0.02, 0.15),
        5.5,
        3.0,
        5.0,
        6.0,
        "hash",
        "hash",
        23.95,
        23.95,
        4.5,
        4.5,
        4.5,
        4.5,
        False,
        ConfigArtifacts("a.zmx", "tf.csv", "tf.png", "mtf.png", ("p1.png", "p2.png", "p3.png")),
        True,
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
    with pytest.raises(AnalysisError, match="IOL position"):
        validate_completed_result(replace(good, iol_position_after_mm=4.6))
    with pytest.raises(AnalysisError, match="ELP"):
        validate_completed_result(replace(good, elp_after_mm=4.6))
    with pytest.raises(AnalysisError, match="vignetting"):
        validate_completed_result(replace(good, unintended_vignetting=True))
    with pytest.raises(ExportError):
        validate_completed_result(
            replace(good, artifacts=ConfigArtifacts("", "tf.csv", "tf", "m", ("1", "2", "3")))
        )


@pytest.mark.unit
def test_completed_result_rejects_wrong_config_run_nan_peak_and_shape_axis() -> None:
    good = result("MONO")
    with pytest.raises(AnalysisError, match="different manifest config"):
        validate_completed_result(good, expected_config=config("EDOF"))
    with pytest.raises(AnalysisError, match="wrong run_id"):
        validate_completed_result(good, expected_run_id="other-run")
    with pytest.raises(AnalysisError, match="finite"):
        validate_completed_result(
            replace(good, aberrations=AberrationSummary(math.nan, 0.02, 0.15))
        )
    with pytest.raises(AnalysisError, match="distance peak"):
        validate_completed_result(replace(good, distance_peak_retina_d=0.25))

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

    with pytest.raises(AnalysisError, match="carrier_lock_hash"):
        matched_pair_delta(mono, replace(edof, config=replace(edof.config, carrier_lock_hash="other")))
