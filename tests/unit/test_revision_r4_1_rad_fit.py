from __future__ import annotations

import math

from whole_eye_mvp.revision_r4_1_rad_fit import (
    fit_r4_1_rad_mechanism,
    rad_spherical_power_diagnostic,
)
from whole_eye_mvp.revision_r4_fit import fit_r4_mechanism, representative_radius_mm


def test_r4_1_rad_spherical_power_fit_rejects_old_opd_shape_and_refits_a4() -> None:
    radius = representative_radius_mm()
    old = fit_r4_mechanism("RAD", base_radius_mm=-radius, base_conic=0.0)
    old_power = rad_spherical_power_diagnostic(
        old.selected.zones,
        base_radius_mm=-radius,
        base_conic=0.0,
    )
    revised = fit_r4_1_rad_mechanism(
        base_radius_mm=-radius,
        base_conic=0.0,
    )
    revised_power = revised.selected.spherical_power

    assert old.selected_complexity == "R+Q+A4"
    assert revised.selected_complexity == "R+Q+A4"
    assert revised.fit_valid is True

    # Regression references are deliberately broad and are not scientific gates.
    # They prove the corrected spherical-power proxy sees the failure that the old
    # integrated-OPD objective missed, then materially improves that same quantity.
    assert old_power.rms_error_d > 1.0
    assert old_power.max_abs_error_d > 5.0
    assert revised_power.rms_error_d < 0.15
    assert revised_power.max_abs_error_d < 0.60
    assert revised_power.rms_error_d < 0.10 * old_power.rms_error_d
    assert revised_power.max_abs_error_d < 0.10 * old_power.max_abs_error_d

    zones = revised.selected.zones
    assert all(zone.alpha_p2_native == 0.0 for zone in zones)
    assert all(zone.alpha_p6_native == 0.0 for zone in zones)
    assert math.isclose(zones[4].radius_mm, -radius, rel_tol=0.0, abs_tol=1.0e-12)
    assert math.isclose(zones[5].radius_mm, -radius, rel_tol=0.0, abs_tol=1.0e-12)
    assert zones[4].conic == 0.0
    assert zones[5].conic == 0.0
    assert zones[4].alpha_p4_native == 0.0
    assert zones[5].alpha_p4_native == 0.0
    assert revised.selected.minimum_conic_radicand > 0.0


def test_r4_1_rad_keeps_integrated_opd_as_diagnostic_not_selection_gate() -> None:
    radius = representative_radius_mm()
    revised = fit_r4_1_rad_mechanism(
        base_radius_mm=-radius,
        base_conic=0.0,
    )

    assert revised.target_definition.startswith("RAD source-locked local spherical power")
    assert math.isfinite(revised.selected.historical_integrated_opd_rms_fraction)
    assert math.isfinite(revised.selected.historical_integrated_opd_max_fraction)
