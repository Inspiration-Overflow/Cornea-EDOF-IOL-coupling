from __future__ import annotations

import math

from whole_eye_mvp.revision_r4_2_rad_fit import (
    R4_2_GLOBAL_DEFOCUS_TOLERANCE_D,
    fit_r4_2_rad_mechanism,
    rad_source_low_order_reference,
)
from whole_eye_mvp.revision_r4_fit import representative_radius_mm


def test_r4_2_frozen_rad_source_defocus_fits_existing_reference() -> None:
    reference = rad_source_low_order_reference()

    assert math.isclose(
        reference.target_global_defocus_d,
        0.10449993581993025,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    )
    assert abs(reference.target_global_defocus_d) < R4_2_GLOBAL_DEFOCUS_TOLERANCE_D
    assert reference.source_headroom_to_tolerance_d > 0.0


def test_r4_2_rad_fit_preserves_source_low_order_without_more_complexity() -> None:
    radius = representative_radius_mm()
    result = fit_r4_2_rad_mechanism(
        base_radius_mm=-radius,
        base_conic=0.0,
    )
    selected = result.selected
    low_order = selected.low_order

    assert result.selected_complexity == "R+Q+A4"
    assert result.fit_valid is True
    assert low_order.absolute_defocus_passed is True
    assert abs(low_order.modeled_global_defocus_d) <= R4_2_GLOBAL_DEFOCUS_TOLERANCE_D
    assert abs(low_order.defocus_error_d) < low_order.source_headroom_to_tolerance_d

    # Regression sanity only, not a new scientific acceptance threshold.
    assert selected.spherical_power.rms_fraction_of_target < 0.15
    assert selected.spherical_power.max_fraction_of_target < 0.50

    for zone in selected.zones:
        assert zone.alpha_p2_native == 0.0
        assert zone.alpha_p6_native == 0.0
    for zone in selected.zones[4:]:
        assert zone.active is False
        assert math.isclose(zone.radius_mm, -radius, rel_tol=0.0, abs_tol=1.0e-12)
        assert zone.conic == 0.0
        assert zone.alpha_p4_native == 0.0
