from __future__ import annotations

import pytest

from whole_eye_mvp.domain import BaseId, PlatformId
from whole_eye_mvp.model_revision import (
    BINARY4_HOA_SPEC,
    BINARY4_RAD_SPEC,
    BINARY4_WFS_SPEC,
    RETINA_ATC_M3_SOURCE_LOCK,
    RETINA_LB_SOURCE_LOCK,
    binary4_mechanism_spec,
    degenerate_binary4_zones,
    equivalent_even_asphere_coefficients,
    physical_stop_semi_diameter_mm,
    retina_prescription_for_base,
)


def test_revision_retina_source_locks_are_explicit_and_base_specific() -> None:
    lb = retina_prescription_for_base(BaseId.LB_AL2395)
    atc = retina_prescription_for_base(BaseId.ATC_M3_AL24477)

    assert lb == RETINA_LB_SOURCE_LOCK
    assert lb.surface_type == "Standard"
    assert lb.radius_y_mm == pytest.approx(-12.0)
    assert lb.conic_y == 0.0
    assert lb.radius_x_mm is None

    assert atc == RETINA_ATC_M3_SOURCE_LOCK
    assert atc.surface_type == "Biconic"
    assert atc.radius_x_mm == pytest.approx(-12.628)
    assert atc.radius_y_mm == pytest.approx(-12.732)
    assert atc.conic_x == pytest.approx(0.192)
    assert atc.conic_y == pytest.approx(0.199)


def test_revision_physical_pupil_is_stop_diameter_not_enpd() -> None:
    assert physical_stop_semi_diameter_mm(3.0) == pytest.approx(1.5)
    assert physical_stop_semi_diameter_mm(5.0) == pytest.approx(2.5)
    with pytest.raises(ValueError, match="physical pupil"):
        physical_stop_semi_diameter_mm(4.0)


def test_binary4_mechanism_boundaries_and_surface_roles_are_frozen() -> None:
    assert BINARY4_WFS_SPEC.surface_role == "anterior"
    assert BINARY4_WFS_SPEC.radial_apertures_mm == (0.55, 0.65, 0.87, 1.05, 3.0)
    assert BINARY4_RAD_SPEC.surface_role == "posterior"
    assert BINARY4_RAD_SPEC.radial_apertures_mm == (0.50, 0.90, 1.10, 1.40, 2.50, 3.0)
    assert BINARY4_HOA_SPEC.surface_role == "anterior"
    assert BINARY4_HOA_SPEC.radial_apertures_mm == (0.90, 1.10, 3.0)
    assert binary4_mechanism_spec(PlatformId.WFS) == BINARY4_WFS_SPEC


def test_degenerate_binary4_mono_keeps_na3_np0_and_zeroes_all_extra_sag() -> None:
    for platform in PlatformId:
        zones = degenerate_binary4_zones(platform, radius_mm=12.5, conic=-0.2)
        spec = binary4_mechanism_spec(platform)
        assert tuple(zone.radial_aperture for zone in zones) == spec.radial_apertures_mm
        assert all(zone.radius == pytest.approx(12.5) for zone in zones)
        assert all(zone.conic == pytest.approx(-0.2) for zone in zones)
        assert all(zone.diffraction_order == 0.0 for zone in zones)
        assert all(zone.phase_terms == () for zone in zones)
        assert all(zone.aspheric_terms == (0.0, 0.0, 0.0) for zone in zones)


def test_binary4_native_to_unscaled_a4_a6_conversion_uses_zone_outer_radius() -> None:
    a4, a6 = equivalent_even_asphere_coefficients(
        outer_radius_mm=2.0,
        alpha_p4_native=16.0,
        alpha_p6_native=64.0,
    )
    assert a4 == pytest.approx(1.0)
    assert a6 == pytest.approx(1.0)
