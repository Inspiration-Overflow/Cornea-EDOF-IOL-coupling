from __future__ import annotations

import math

from whole_eye_mvp.revision_r4_1_rad_fit import (
    fit_r4_1_rad_mechanism,
    rad_power_diagnostic,
)
from whole_eye_mvp.revision_r4_fit import (
    R4_MECHANISM_MAX_FRACTION_TARGET,
    R4_MECHANISM_RMS_FRACTION_TARGET,
    fit_r4_mechanism,
    representative_radius_mm,
)


def test_r4_1_rad_power_fit_keeps_existing_opd_gate_and_stops_at_a4() -> None:
    radius = representative_radius_mm()
    result, power_levels = fit_r4_1_rad_mechanism(
        base_radius_mm=-radius,
        base_conic=0.0,
    )

    assert result.engineering_target_passed is True
    assert result.selected_complexity == "R+Q+A4"
    assert len(result.levels_attempted) == 3
    assert len(power_levels) == 3
    assert result.selected.rms_fraction_of_target <= R4_MECHANISM_RMS_FRACTION_TARGET
    assert result.selected.max_fraction_of_target <= R4_MECHANISM_MAX_FRACTION_TARGET

    selected_power = power_levels[-1]
    assert selected_power.rms_error_d < 0.10
    assert selected_power.max_abs_error_d < 0.40

    selected_zones = result.selected.zones
    assert all(zone.alpha_p2_native == 0.0 for zone in selected_zones)
    assert all(zone.alpha_p6_native == 0.0 for zone in selected_zones)
    assert math.isclose(selected_zones[4].radius_mm, -radius, rel_tol=0.0, abs_tol=1.0e-12)
    assert math.isclose(selected_zones[5].radius_mm, -radius, rel_tol=0.0, abs_tol=1.0e-12)
    assert selected_zones[4].conic == 0.0
    assert selected_zones[5].conic == 0.0


def test_r4_1_rad_power_objective_materially_improves_old_opd_fit_power_shape() -> None:
    radius = representative_radius_mm()
    old = fit_r4_mechanism("RAD", base_radius_mm=-radius, base_conic=0.0)
    old_power = rad_power_diagnostic(
        old.selected.zones,
        base_radius_mm=-radius,
        base_conic=0.0,
    )
    revised, revised_levels = fit_r4_1_rad_mechanism(
        base_radius_mm=-radius,
        base_conic=0.0,
    )
    revised_power = revised_levels[-1]

    assert old.selected_complexity == "R+Q+A4"
    assert revised.selected_complexity == "R+Q+A4"
    assert revised_power.rms_error_d < 0.10 * old_power.rms_error_d
    assert revised_power.max_abs_error_d < 0.10 * old_power.max_abs_error_d
