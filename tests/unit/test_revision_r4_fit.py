from __future__ import annotations

import math

import numpy as np

from whole_eye_mvp.model_revision import BINARY4_WFS_SPEC
from whole_eye_mvp.ref_mono import symmetric_biconvex_power_d
from whole_eye_mvp.revision_r4_fit import (
    R4_MECHANISM_MAX_FRACTION_TARGET,
    R4_MECHANISM_RMS_FRACTION_TARGET,
    R4_REPRESENTATIVE_POWER_D,
    binary4_piecewise_sag_mm,
    fit_r4_mechanism,
    representative_radius_mm,
)


def test_r4_representative_radius_is_exactly_twenty_diopters() -> None:
    radius = representative_radius_mm()
    assert math.isclose(radius, 12.3573878112, rel_tol=0.0, abs_tol=1.0e-9)
    assert math.isclose(
        symmetric_biconvex_power_d(radius),
        R4_REPRESENTATIVE_POWER_D,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    )


def test_r4_wfs_stops_at_first_acceptable_complexity() -> None:
    radius = representative_radius_mm()
    result = fit_r4_mechanism("WFS", base_radius_mm=radius, base_conic=0.0)
    assert result.engineering_target_passed is True
    assert result.selected_complexity == "R"
    assert len(result.levels_attempted) == 1
    selected = result.selected
    assert selected.rms_fraction_of_target <= R4_MECHANISM_RMS_FRACTION_TARGET
    assert selected.max_fraction_of_target <= R4_MECHANISM_MAX_FRACTION_TARGET
    assert all(zone.alpha_p2_native == 0.0 for zone in selected.zones)
    assert all(zone.alpha_p4_native == 0.0 for zone in selected.zones)
    assert all(zone.alpha_p6_native == 0.0 for zone in selected.zones)
    assert max(abs(item.c0_error_mm) for item in selected.boundaries) <= 1.0e-12


def test_binary4_degenerate_piecewise_sag_matches_one_conic() -> None:
    radius = representative_radius_mm()
    result = fit_r4_mechanism("WFS", base_radius_mm=radius, base_conic=0.0)
    zones = tuple(
        type(zone)(
            zone=zone.zone,
            r_inner_mm=zone.r_inner_mm,
            r_outer_mm=zone.r_outer_mm,
            radius_mm=radius,
            conic=0.0,
            alpha_p2_native=0.0,
            alpha_p4_native=0.0,
            alpha_p6_native=0.0,
            active=zone.active,
        )
        for zone in result.selected.zones
    )
    radii = np.linspace(0.0, 3.0, 121)
    sag, _ = binary4_piecewise_sag_mm(radii, BINARY4_WFS_SPEC.radial_apertures_mm, zones)
    c = 1.0 / radius
    expected = c * radii**2 / (1.0 + np.sqrt(1.0 - c * c * radii**2))
    assert np.max(np.abs(sag - expected)) <= 1.0e-12
