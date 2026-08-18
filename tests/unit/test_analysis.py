from __future__ import annotations

import pytest

from whole_eye_mvp.analysis import AberrationSummary, AnalysisError, ConfigArtifacts, ConfigResult, ExportError, matched_pair_delta, validate_completed_result, validate_selection, with_shape_axis
from whole_eye_mvp.domain import NOMINAL_MAIN_555_V1
from whole_eye_mvp.manifest import NominalConfig


def config(state: str) -> NominalConfig:
    return NominalConfig(f'CFG_{state}', 'CAR_X', 'LB_AL2395', 'A0', 'WFS', state, 3.0)


def rows():
    d = NOMINAL_MAIN_555_V1.defocus_grid(); peak_i = d.index(0.0)
    vs = tuple(max(.05, 1-abs(i-peak_i)*.15) for i in range(len(d)))
    mtfa = tuple(v*.7 for v in vs); cols = [tuple(v*(1-j*.05) for v in vs) for j in range(6)]
    return with_shape_axis(d, mtfa, vs, cols)


def result(state: str) -> ConfigResult:
    return ConfigResult(config(state), 'run', rows(), 0.0, AberrationSummary(.1,.02,.15), 5.5, 3.0, 5.0, 6.0, 'hash','hash',23.95,23.95, ConfigArtifacts('a.zos','tf.png','mtf.png',('p1.png','p2.png','p3.png')), True)


@pytest.mark.unit
def test_shape_axis_is_retina_axis_minus_distance_peak() -> None:
    r = rows(); assert len(r) == 15
    assert next(x for x in r if x.defocus_retina_d == 0).defocus_shape_d == 0
    assert r[0].defocus_shape_d == pytest.approx(.5)


@pytest.mark.unit
def test_selection_rejects_external_id() -> None:
    manifest = [config('MONO'), config('EDOF')]
    assert len(validate_selection(['CFG_MONO'], manifest)) == 1
    with pytest.raises(AnalysisError, match='external'):
        validate_selection(['NOPE'], manifest)


@pytest.mark.unit
def test_completed_result_contract_and_artifact_rule() -> None:
    validate_completed_result(result('MONO'))
    a = result('MONO')
    bad = ConfigResult(a.config,a.run_id,a.rows,a.distance_peak_retina_d,a.aberrations,a.cornea_footprint_mm,a.stop_footprint_mm,a.iol_footprint_mm,a.iol_optical_diameter_mm,a.model_hash_before,'changed',a.retina_position_before_mm,a.retina_position_after_mm,a.artifacts,a.completed)
    with pytest.raises(AnalysisError, match='model'):
        validate_completed_result(bad)
    missing = ConfigResult(a.config,a.run_id,a.rows,a.distance_peak_retina_d,a.aberrations,a.cornea_footprint_mm,a.stop_footprint_mm,a.iol_footprint_mm,a.iol_optical_diameter_mm,a.model_hash_before,a.model_hash_after,a.retina_position_before_mm,a.retina_position_after_mm,ConfigArtifacts('', 'tf','m',('1','2','3')),True)
    with pytest.raises(ExportError):
        validate_completed_result(missing)


@pytest.mark.unit
def test_matched_pair_delta_is_edof_minus_mono() -> None:
    mono, edof = result('MONO'), result('EDOF')
    edof = ConfigResult(edof.config,edof.run_id,edof.rows,.125,AberrationSummary(.2,.03,.18),edof.cornea_footprint_mm,edof.stop_footprint_mm,edof.iol_footprint_mm,edof.iol_optical_diameter_mm,edof.model_hash_before,edof.model_hash_after,edof.retina_position_before_mm,edof.retina_position_after_mm,edof.artifacts,True)
    delta = matched_pair_delta(mono,edof)
    assert delta.deltas['distance_peak_retina_d'] == pytest.approx(.125)
    assert delta.deltas['c40_um'] == pytest.approx(.1)
