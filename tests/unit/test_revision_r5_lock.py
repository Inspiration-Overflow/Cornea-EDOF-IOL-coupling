from __future__ import annotations

import math

import pytest

from whole_eye_mvp.domain import PlatformId
from whole_eye_mvp.revision_r5_lock import (
    R5_REPRESENTATIVE_RADIUS_MM,
    r5_mechanism_lock,
    r5_zones_for_carrier,
)


def _radii(zones):
    return tuple(zone.radius_mm for zone in zones)


def test_r5_locks_validate_frozen_complexity_and_neutral_zones() -> None:
    wfs = r5_mechanism_lock(PlatformId.WFS.value)
    rad = r5_mechanism_lock(PlatformId.RAD.value)
    hoa = r5_mechanism_lock(PlatformId.HOA.value)

    assert wfs.selected_complexity == "R"
    assert rad.selected_complexity == "R+Q+A4"
    assert hoa.selected_complexity == "R+Q+A4+A6"
    assert all(zone.active for zone in wfs.zones)
    assert [zone.active for zone in rad.zones] == [True, True, True, True, False, False]
    assert [zone.active for zone in hoa.zones] == [True, True, False]
    assert all(zone.alpha_p6_native == 0.0 for zone in rad.zones)


def test_r5_reconstructs_reviewed_plus20_pilot_prescriptions() -> None:
    wfs = r5_zones_for_carrier(
        PlatformId.WFS.value,
        base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
        base_conic=-9.0,
    )
    rad = r5_zones_for_carrier(
        PlatformId.RAD.value,
        base_radius_mm=-R5_REPRESENTATIVE_RADIUS_MM,
        base_conic=0.0,
    )
    hoa = r5_zones_for_carrier(
        PlatformId.HOA.value,
        base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
        base_conic=0.0,
    )

    assert _radii(wfs) == pytest.approx(
        (12.37178813194, 15.72790338137, 12.34228496635, 11.82286618367, 12.35773340664),
        abs=2.0e-10,
    )
    assert _radii(rad) == pytest.approx(
        (
            -12.675703499202,
            -16.333548021307,
            -6.039861064879,
            -16.111247991253,
            -R5_REPRESENTATIVE_RADIUS_MM,
            -R5_REPRESENTATIVE_RADIUS_MM,
        ),
        abs=2.0e-10,
    )
    assert _radii(hoa) == pytest.approx(
        (3.69169669841, 9.2281697388, R5_REPRESENTATIVE_RADIUS_MM),
        abs=2.0e-10,
    )

    assert tuple(zone.conic for zone in wfs) == pytest.approx((-9.0,) * 5, abs=1.0e-12)
    assert tuple(zone.conic for zone in rad) == pytest.approx(
        (0.032796262113, -0.876401226297, -0.999700078812, -0.999999985532, 0.0, 0.0),
        abs=1.0e-12,
    )
    assert tuple(zone.conic for zone in hoa) == pytest.approx((-34.1538507, 50.0, 0.0))


def test_r5_normalized_application_moves_with_carrier_base() -> None:
    base_radius = 10.0
    base_q = -5.0
    zones = r5_zones_for_carrier(
        PlatformId.WFS.value,
        base_radius_mm=base_radius,
        base_conic=base_q,
    )
    lock = r5_mechanism_lock(PlatformId.WFS.value)
    for zone, frozen in zip(zones, lock.zones, strict=True):
        assert 1.0 / zone.radius_mm == pytest.approx(
            1.0 / base_radius + frozen.delta_curvature_mm_inv,
            abs=1.0e-14,
        )
        assert zone.conic == pytest.approx(base_q)
        assert zone.alpha_p2_native == 0.0
        assert zone.alpha_p4_native == 0.0
        assert zone.alpha_p6_native == 0.0


def test_r5_rejects_wrong_surface_radius_sign() -> None:
    with pytest.raises(ValueError, match="surface role"):
        r5_zones_for_carrier(
            PlatformId.RAD.value,
            base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
            base_conic=0.0,
        )

    with pytest.raises(ValueError, match="surface role"):
        r5_zones_for_carrier(
            PlatformId.WFS.value,
            base_radius_mm=-R5_REPRESENTATIVE_RADIUS_MM,
            base_conic=-9.0,
        )


def test_r5_neutral_zones_follow_power_specific_carrier_exactly() -> None:
    rad_base = -11.0
    rad = r5_zones_for_carrier(
        PlatformId.RAD.value,
        base_radius_mm=rad_base,
        base_conic=0.0,
    )
    for zone in rad[4:]:
        assert zone.radius_mm == pytest.approx(rad_base, abs=1.0e-12)
        assert zone.conic == 0.0
        assert zone.alpha_p4_native == 0.0
        assert zone.alpha_p6_native == 0.0

    hoa_base = 10.5
    hoa_q = 0.25
    hoa = r5_zones_for_carrier(
        PlatformId.HOA.value,
        base_radius_mm=hoa_base,
        base_conic=hoa_q,
    )
    neutral = hoa[2]
    assert math.isclose(neutral.radius_mm, hoa_base, rel_tol=0.0, abs_tol=1.0e-12)
    assert neutral.conic == pytest.approx(hoa_q)
    assert neutral.alpha_p4_native == 0.0
    assert neutral.alpha_p6_native == 0.0
