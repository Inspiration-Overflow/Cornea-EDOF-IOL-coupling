from __future__ import annotations

import math

import pytest

from whole_eye_mvp.carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from whole_eye_mvp.residual_policy import RESIDUAL_VALIDATION_546_V1
from whole_eye_mvp.residual_profiles import (
    HOA_BENCH_SEED,
    RAD_PATENT_ZONES,
    RESIDUAL_NORMALIZATION_RADIUS_MM,
    WFS_PATENT_SEED,
    fit_piston_and_global_defocus,
    hoa_raw_opd_um,
    hoa_window,
    osa_primary_spherical,
    osa_secondary_spherical,
    rad_raw_opd_um,
    rad_relative_power_d,
    remove_piston_and_global_defocus,
    sample_radial_profile,
    wfs_raw_opd_um,
    wfs_raw_surface_sag_um,
)


def test_controlled_carrier_scaffold_is_minimal_and_fixed() -> None:
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    scaffold.validate()
    assert scaffold.refractive_index == pytest.approx(1.460)
    assert scaffold.surrounding_index == pytest.approx(1.336)
    assert scaffold.center_thickness_mm == pytest.approx(1.0)
    assert scaffold.optical_diameter_mm == pytest.approx(6.0)
    assert scaffold.bending == "symmetric_biconvex"
    assert scaffold.asphere_surface == "anterior"


def test_residual_validation_policy_is_frozen_before_opticstudio_calibration() -> None:
    policy = RESIDUAL_VALIDATION_546_V1
    policy.validate()
    assert policy.policy_id == "RESIDUAL_VALIDATION_546_v1"
    assert policy.piston_tolerance_um == pytest.approx(0.010)
    assert policy.global_defocus_tolerance_d == pytest.approx(0.125)
    assert len(policy.policy_hash) == 64


def test_wfs_public_seed_hits_frozen_phase_shift_boundaries() -> None:
    seed = WFS_PATENT_SEED
    assert wfs_raw_surface_sag_um(0.0) == pytest.approx(0.0)
    assert wfs_raw_surface_sag_um(seed.r1_mm) == pytest.approx(0.0)
    assert wfs_raw_surface_sag_um(seed.r2_mm) == pytest.approx(seed.delta1_um)
    assert wfs_raw_surface_sag_um(seed.r3_mm) == pytest.approx(seed.delta1_um)
    assert wfs_raw_surface_sag_um(seed.r4_mm) == pytest.approx(seed.delta1_um + seed.delta2_um)
    assert wfs_raw_surface_sag_um(seed.optic_radius_mm) == pytest.approx(
        seed.delta1_um + seed.delta2_um
    )


def test_wfs_opd_uses_controlled_carrier_index_step() -> None:
    radius = 0.70
    sag = wfs_raw_surface_sag_um(radius)
    index_step = (
        CONTROLLED_IOL_CARRIER_546_V1.refractive_index
        - CONTROLLED_IOL_CARRIER_546_V1.surrounding_index
    )
    assert wfs_raw_opd_um(radius) == pytest.approx(index_step * sag)


def test_rad_patent_zones_are_continuous_and_match_table_endpoints() -> None:
    expected = {
        0.00: -0.25,
        0.50: -0.25,
        0.90: 3.00,
        1.10: -0.25,
        1.40: 0.00,
        2.50: 0.00,
        3.00: 0.00,
    }
    for radius, power in expected.items():
        assert rad_relative_power_d(radius) == pytest.approx(power, abs=1.0e-12)

    for left, right in zip(RAD_PATENT_ZONES, RAD_PATENT_ZONES[1:], strict=True):
        assert left.outer_radius_mm == pytest.approx(right.inner_radius_mm)
        assert left.end_power_d == pytest.approx(right.start_power_d)


def test_rad_integrated_opd_derivative_recovers_relative_power() -> None:
    for radius in (0.25, 0.70, 1.00, 1.25, 1.80):
        h = 1.0e-5
        derivative = (rad_raw_opd_um(radius + h) - rad_raw_opd_um(radius - h)) / (2.0 * h)
        recovered_power = derivative / radius
        assert recovered_power == pytest.approx(rad_relative_power_d(radius), rel=1.0e-7, abs=1.0e-7)


def test_hoa_seed_is_direct_opposite_sign_osa_z4_z6_with_smooth_local_window() -> None:
    seed = HOA_BENCH_SEED
    assert seed.z4_um == pytest.approx(-0.49 * 0.546)
    assert seed.z6_um == pytest.approx(0.46 * 0.546)
    assert seed.z4_um * seed.z6_um < 0.0
    assert osa_primary_spherical(0.0) == pytest.approx(math.sqrt(5.0))
    assert osa_secondary_spherical(0.0) == pytest.approx(-math.sqrt(7.0))
    assert hoa_window(seed.core_radius_mm) == pytest.approx(1.0)
    assert hoa_window(seed.transition_outer_radius_mm) == pytest.approx(0.0)
    assert 0.0 < hoa_window(1.0) < 1.0
    assert math.isfinite(hoa_raw_opd_um(0.5))
    assert hoa_raw_opd_um(1.2) == pytest.approx(0.0)


def test_low_order_fit_exactly_recovers_piston_and_defocus() -> None:
    radii = tuple(index * 0.05 for index in range(52))
    piston_um = 0.123
    defocus_d = -0.375
    opd = tuple(piston_um + 0.5 * defocus_d * radius**2 for radius in radii)
    fit = fit_piston_and_global_defocus(radii, opd)
    assert fit.piston_um == pytest.approx(piston_um, abs=1.0e-12)
    assert fit.global_defocus_d == pytest.approx(defocus_d, abs=1.0e-12)

    normalized, removed = remove_piston_and_global_defocus(radii, opd)
    assert removed == fit
    assert max(abs(value) for value in normalized) <= 1.0e-12


def test_normalization_removes_low_order_components_from_real_seed() -> None:
    radii, raw = sample_radial_profile(wfs_raw_opd_um)
    assert radii[-1] == pytest.approx(RESIDUAL_NORMALIZATION_RADIUS_MM)
    normalized, removed = remove_piston_and_global_defocus(radii, raw)
    assert math.isfinite(removed.piston_um)
    assert math.isfinite(removed.global_defocus_d)
    residual_fit = fit_piston_and_global_defocus(radii, normalized)
    assert residual_fit.piston_um == pytest.approx(0.0, abs=1.0e-12)
    assert residual_fit.global_defocus_d == pytest.approx(0.0, abs=1.0e-12)
