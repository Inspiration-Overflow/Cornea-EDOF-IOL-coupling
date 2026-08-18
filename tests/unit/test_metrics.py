from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from whole_eye_mvp.metrics import (
    absolute_dof,
    cycles_mm_to_cpd,
    find_distance_peak,
    matched_numeric_delta,
    mm_per_degree,
    mtfa,
    psf_to_complex_otf,
    relative_dof,
    vsmtf_discrete,
    vsotf_discrete,
)


@pytest.mark.unit
def test_centered_delta_psf_has_unit_otf() -> None:
    psf = np.zeros((3, 3))
    psf[1, 1] = 1
    otf = psf_to_complex_otf(psf, pad_factor=4)
    assert np.allclose(otf, 1.0, atol=1e-10)


@pytest.mark.unit
def test_shifted_delta_keeps_magnitude_but_has_phase() -> None:
    centered = np.zeros((3, 3)); centered[1, 1] = 1
    shifted = np.zeros((3, 3)); shifted[1, 2] = 1
    a = psf_to_complex_otf(centered)
    b = psf_to_complex_otf(shifted)
    assert np.allclose(np.abs(b), 1.0, atol=1e-10)
    assert not np.allclose(b, a)


@pytest.mark.unit
def test_vsotf_endpoints() -> None:
    fx = fy = [-10.0, 0.0, 10.0]
    one = np.ones((3, 3), dtype=complex)
    zero = np.zeros((3, 3), dtype=complex)
    assert vsotf_discrete(one, fx, fy) == pytest.approx(1.0, abs=1e-10)
    assert vsotf_discrete(zero, fx, fy) == pytest.approx(0.0, abs=1e-10)


@pytest.mark.unit
def test_phase_sensitive_golden_fixture() -> None:
    fixture = json.loads(Path('tests/fixtures/COMPLEX_OTF_GOLDEN_3x3_v1.json').read_text())
    otf = np.array([[complex(cell['re'], cell['im']) for cell in row] for row in fixture['otf_complex']])
    vs = vsotf_discrete(otf, fixture['fx'], fixture['fy'])
    vsm = vsmtf_discrete(otf, fixture['fx'], fixture['fy'])
    assert vs == pytest.approx(fixture['golden_vsotf'], abs=1e-10)
    assert vsm == pytest.approx(fixture['golden_vsmtf'], abs=1e-10)
    assert vs != pytest.approx(vsm, abs=1e-5)


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
def test_dof_linear_interpolation_and_edges() -> None:
    d = [0.5, 0.0, -0.5, -1.0]
    y = [0.0, 1.0, 0.5, 0.0]
    peak = find_distance_peak(d, y)
    rel = relative_dof(d, y, peak=peak, fraction=0.5)
    assert rel.far_d == pytest.approx(0.25, abs=1e-10)
    assert rel.near_d == pytest.approx(-0.5, abs=1e-10)
    low = absolute_dof(d, [0.05, 0.08, 0.05, 0.01], peak=find_distance_peak(d, [0.05, 0.08, 0.05, 0.01]))
    assert low.width_d == 0 and low.below_absolute_threshold


@pytest.mark.unit
def test_frequency_scale() -> None:
    efl = 17.0
    assert mm_per_degree(efl) == pytest.approx(efl * np.tan(np.deg2rad(1.0)), abs=1e-10)
    assert cycles_mm_to_cpd(10.0, efl) == pytest.approx(10 * mm_per_degree(efl), abs=1e-10)


@pytest.mark.unit
def test_matched_delta() -> None:
    delta = matched_numeric_delta({'mtfa': 0.6, 'vsotf': 0.4}, {'mtfa': 0.5, 'vsotf': 0.1})
    assert delta['mtfa'] == pytest.approx(0.1, abs=1e-10)
    assert delta['vsotf'] == pytest.approx(0.3, abs=1e-10)
