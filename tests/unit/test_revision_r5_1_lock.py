from __future__ import annotations

import pytest

from whole_eye_mvp.revision_r5_lock import (
    R5_REPRESENTATIVE_RADIUS_MM,
    r5_1_zones_for_carrier,
    r5_mechanism_lock,
    r5_zones_for_carrier,
)

_REPRESENTATIVE_RADII = {
    "WFS": R5_REPRESENTATIVE_RADIUS_MM,
    "RAD": -R5_REPRESENTATIVE_RADIUS_MM,
    "HOA": R5_REPRESENTATIVE_RADIUS_MM,
}
_REPRESENTATIVE_CONICS = {"WFS": -9.0, "RAD": 0.0, "HOA": 0.0}


def _min_radicand(zone) -> float:
    if 1.0 + zone.conic <= 0.0:
        return float("inf")
    worst = max(zone.r_inner_mm, zone.r_outer_mm)
    return 1.0 - (1.0 + zone.conic) * (worst / zone.radius_mm) ** 2


@pytest.mark.parametrize("platform", ["WFS", "RAD", "HOA"])
def test_r5_1_reproduces_the_frozen_pilot_at_representative_carrier(
    platform: str,
) -> None:
    frozen = r5_zones_for_carrier(
        platform,
        base_radius_mm=_REPRESENTATIVE_RADII[platform],
        base_conic=_REPRESENTATIVE_CONICS[platform],
    )
    r5_1 = r5_1_zones_for_carrier(
        platform,
        base_radius_mm=_REPRESENTATIVE_RADII[platform],
        base_conic=_REPRESENTATIVE_CONICS[platform],
    )
    assert r5_1 == frozen


@pytest.mark.parametrize("platform", ["WFS", "RAD"])
@pytest.mark.parametrize("radius_mm", [9.8, 11.0, 13.2])
def test_r5_1_leaves_wfs_and_rad_bit_identical(platform: str, radius_mm: float) -> None:
    frozen = r5_zones_for_carrier(
        platform,
        base_radius_mm=radius_mm if platform == "WFS" else -radius_mm,
        base_conic=-5.0,
    )
    r5_1 = r5_1_zones_for_carrier(
        platform,
        base_radius_mm=radius_mm if platform == "WFS" else -radius_mm,
        base_conic=-5.0,
    )
    assert r5_1 == frozen


@pytest.mark.parametrize("radius_mm", [9.82, 10.66, 11.93, 13.09])
def test_r5_1_hoa_preserves_frozen_conic_sag_term(radius_mm: float) -> None:
    lock = r5_mechanism_lock("HOA")
    zones = r5_1_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0)
    reference_curvature = 1.0 / R5_REPRESENTATIVE_RADIUS_MM
    for zone, frozen in zip(zones, lock.zones, strict=True):
        reference_zone_radius = 1.0 / (reference_curvature + frozen.delta_curvature_mm_inv)
        frozen_sag_term = frozen.delta_conic / reference_zone_radius**3
        scaled_sag_term = zone.conic / zone.radius_mm**3
        assert scaled_sag_term == pytest.approx(frozen_sag_term, rel=1.0e-12)


@pytest.mark.parametrize(
    "radius_mm",
    [9.5, 9.82, 10.66, 11.93, 12.357387811201875, 13.09, 13.5],
)
def test_r5_1_hoa_keeps_conic_radicand_valid_across_carrier_range(
    radius_mm: float,
) -> None:
    zones = r5_1_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0)
    for zone in zones:
        if zone.active:
            assert _min_radicand(zone) > 0.0


def test_unscaled_r5_hoa_fails_radicand_at_high_power() -> None:
    zones = r5_zones_for_carrier("HOA", base_radius_mm=9.82, base_conic=0.0)
    zone_two = zones[1]
    assert _min_radicand(zone_two) < 0.0


def test_r5_1_hoa_keeps_neutral_zone_and_coefficients_frozen() -> None:
    zones = r5_1_zones_for_carrier("HOA", base_radius_mm=10.66, base_conic=0.0)
    lock = r5_mechanism_lock("HOA")
    assert len(zones) == 3
    assert not zones[2].active
    for zone, frozen in zip(zones, lock.zones, strict=True):
        assert zone.alpha_p2_native == 0.0
        assert zone.alpha_p4_native == frozen.alpha_p4_native
        assert zone.alpha_p6_native == frozen.alpha_p6_native
        assert zone.r_inner_mm == frozen.r_inner_mm
        assert zone.r_outer_mm == frozen.r_outer_mm
