from __future__ import annotations

import numpy as np
import pytest

from whole_eye_mvp.science_assets import (
    A0_SPEC,
    ATC_M3_BASE,
    B_CANDIDATE_DELTA_C40_UM,
    C0_SPEC,
    LB_BASE,
    PLATFORM_SPECS,
    STD_IOL_EYE,
    AssetValidation,
    NumericalStatus,
    c0_near_weight,
    smoothstep_quintic,
    summarize_asset_validations,
)


@pytest.mark.unit
def test_frozen_scientific_anchors_match_mvp_spec() -> None:
    assert LB_BASE.axial_length_mm == pytest.approx(23.950, abs=0.001)
    assert ATC_M3_BASE.axial_length_mm == pytest.approx(24.477, abs=0.001)
    assert LB_BASE.post_cornea_to_stop_mm == pytest.approx(3.150, abs=0.001)
    assert LB_BASE.post_cornea_to_iol_ant_mm == pytest.approx(4.500, abs=0.001)
    assert STD_IOL_EYE.corneal_c40_um == pytest.approx(0.258, abs=0.005)
    assert STD_IOL_EYE.aperture_mm == 6.0 and STD_IOL_EYE.wavelength_nm == 546.0
    assert A0_SPEC.treatment_d == -3.0 and A0_SPEC.target_delta_c40_um == 0.13
    assert B_CANDIDATE_DELTA_C40_UM == (0.10, 0.15, 0.20, 0.25, 0.30)
    assert [p.standard_eye_sa_target_um for p in PLATFORM_SPECS] == [-0.20, -0.27, 0.0]


@pytest.mark.unit
def test_c0_prescription_and_regions_are_fixed() -> None:
    assert C0_SPEC.near_diameter_mm == 3.0
    assert C0_SPEC.add_rx_d == 1.75
    assert C0_SPEC.optical_zone_mm == 6.5
    assert C0_SPEC.transition_width_mm == 0.75
    assert C0_SPEC.near_radius_mm == 1.5
    assert C0_SPEC.transition_outer_radius_mm == 2.25
    assert c0_near_weight(np.array([0.0, 1.5, 2.25, 3.0])).tolist() == [1, 1, 0, 0]


@pytest.mark.unit
def test_quintic_transition_has_value_first_second_derivative_continuity() -> None:
    eps = 1e-5
    f0 = smoothstep_quintic(0.0).item(); f1 = smoothstep_quintic(1.0).item()
    d0 = (smoothstep_quintic(eps) - smoothstep_quintic(0.0)) / eps
    d1 = (smoothstep_quintic(1.0) - smoothstep_quintic(1.0-eps)) / eps
    dd0 = (smoothstep_quintic(2*eps) - 2*smoothstep_quintic(eps) + smoothstep_quintic(0.0)) / eps**2
    dd1 = (smoothstep_quintic(1.0) - 2*smoothstep_quintic(1.0-eps) + smoothstep_quintic(1.0-2*eps)) / eps**2
    assert f0 == 0 and f1 == 1
    assert abs(float(d0)) < 1e-8 and abs(float(d1)) < 1e-8
    assert abs(float(dd0)) < 1e-3 and abs(float(dd1)) < 1e-3


@pytest.mark.unit
def test_residual_absence_does_not_fail_core_build_but_blocks_carriers() -> None:
    validations = [AssetValidation('LB', NumericalStatus.PASS), AssetValidation('A0', NumericalStatus.PASS)]
    report = summarize_asset_validations(validations)
    assert report.core_ok
    assert not report.carrier_ready
    assert report.residual_missing == ('WFS', 'RAD', 'HOA')
    ready = summarize_asset_validations(validations, available_residual_platforms=['WFS', 'RAD', 'HOA'])
    assert ready.carrier_ready