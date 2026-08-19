from __future__ import annotations

import numpy as np
import pytest

from whole_eye_mvp.metrics import (
    average_sagittal_tangential_mtf,
    cycles_mm_to_cpd,
    distance_anchored_dof50,
    find_distance_peak,
    matched_numeric_delta,
    mm_per_degree,
    mtfa,
    resample_fft_mtf_to_cpd,
    through_focus_mean,
)


@pytest.mark.unit
def test_average_sagittal_tangential_mtf() -> None:
    actual = average_sagittal_tangential_mtf([1.0, 0.6, 0.2], [1.0, 0.4, 0.0])
    assert np.allclose(actual, [1.0, 0.5, 0.1], atol=1e-12)


@pytest.mark.unit
def test_fft_mtf_resampling_converts_cycles_mm_to_cpd_without_extrapolation() -> None:
    efl = 17.0
    scale = mm_per_degree(efl)
    f_mm = np.arange(0.0, 61.0 / scale, 1.0 / scale)
    sag = np.linspace(1.0, 0.4, f_mm.size)
    tan = np.linspace(1.0, 0.2, f_mm.size)
    f_cpd, avg = resample_fft_mtf_to_cpd(
        f_mm,
        sag,
        tan,
        effective_focal_length_mm=efl,
        max_cpd=60.0,
        step_cpd=1.0,
    )
    assert f_cpd[0] == 0.0 and f_cpd[-1] == 60.0 and len(f_cpd) == 61
    assert avg[0] == pytest.approx(1.0, abs=1e-12)
    with pytest.raises(ValueError, match="cover"):
        resample_fft_mtf_to_cpd(
            f_mm[:20],
            sag[:20],
            tan[:20],
            effective_focal_length_mm=efl,
            max_cpd=60.0,
        )


@pytest.mark.unit
def test_mtfa_constant_half() -> None:
    f = np.arange(61, dtype=float)
    assert mtfa(f, np.full_like(f, 0.5)) == pytest.approx(0.5, abs=1e-10)


@pytest.mark.unit
def test_distance_peak_tie_rules_and_censor() -> None:
    d = [0.5, 0.25, 0.0, -0.25, -0.5]
    peak = find_distance_peak(d, [0.1, 1, 0.5, 1, 0.1])
    assert peak.defocus_d == 0.25
    peak = find_distance_peak(d, [0.1, 1, 1, 1, 0.1])
    assert peak.defocus_d == 0.0
    peak = find_distance_peak(d, [2, 1, 1, 1, 0.1])
    assert peak.defocus_d == 0.5 and peak.peak_search_censored


@pytest.mark.unit
def test_distance_anchored_dof50_uses_distance_peak_and_linear_crossings() -> None:
    d = [0.5, 0.0, -0.5, -1.0, -1.5]
    y = [0.0, 1.0, 0.5, 0.25, 0.0]
    peak = find_distance_peak(d, y)
    dof = distance_anchored_dof50(d, y, peak=peak)
    assert dof.far_d == pytest.approx(0.25, abs=1e-10)
    assert dof.near_d == pytest.approx(-0.5, abs=1e-10)
    assert dof.width_d == pytest.approx(0.75, abs=1e-10)


@pytest.mark.unit
def test_through_focus_mean_is_direction_invariant() -> None:
    d = [0.5, 0.0, -0.5, -1.0]
    y = [0.2, 0.8, 0.6, 0.2]
    forward = through_focus_mean(d, y)
    reverse = through_focus_mean(list(reversed(d)), list(reversed(y)))
    assert forward == pytest.approx(reverse, abs=1e-12)
    assert 0.0 < forward < 1.0


@pytest.mark.unit
def test_frequency_scale() -> None:
    efl = 17.0
    assert mm_per_degree(efl) == pytest.approx(efl * np.tan(np.deg2rad(1.0)), abs=1e-10)
    assert cycles_mm_to_cpd(10.0, efl) == pytest.approx(10 * mm_per_degree(efl), abs=1e-10)


@pytest.mark.unit
def test_matched_delta() -> None:
    delta = matched_numeric_delta(
        {"mtfa": 0.6, "dof50_width_d": 1.5},
        {"mtfa": 0.5, "dof50_width_d": 1.0},
    )
    assert delta["mtfa"] == pytest.approx(0.1, abs=1e-10)
    assert delta["dof50_width_d"] == pytest.approx(0.5, abs=1e-10)
