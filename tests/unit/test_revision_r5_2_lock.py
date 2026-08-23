from __future__ import annotations

import math

import numpy as np
import pytest

from whole_eye_mvp.carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from whole_eye_mvp.model_revision import binary4_mechanism_spec
from whole_eye_mvp.residual_profiles import hoa_raw_opd_um
from whole_eye_mvp.revision_r4_fit import (
    R4ZonePrescription,
    _zone_equal_weights,
    binary4_piecewise_sag_mm,
)
from whole_eye_mvp.revision_r5_2 import (
    R5_2_FREEZE_ID,
    r5_2_boundary_delta_z_mm,
    r5_2_zones_for_carrier,
)
from whole_eye_mvp.revision_r5_lock import (
    R5_REPRESENTATIVE_RADIUS_MM,
    r5_1_zones_for_carrier,
)

_HOA_CASES = (
    (
        "ATC A0",
        10.6607177397636,
        0.042843228031728,
        -0.049768591452183,
        1.1403719218599668,
        3.873044280533011,
    ),
    (
        "ATC B0",
        10.7994608127046,
        0.042796627074844,
        -0.049904251031978,
        1.1321586892047213,
        3.862022848532071,
    ),
    (
        "ATC C0",
        11.9319042729257,
        0.042448113245389,
        -0.051112914597138,
        1.085573754456201,
        3.749213495625393,
    ),
    (
        "ATC N0",
        13.0868466098400,
        0.042142604666272,
        -0.052561201642766,
        1.1157631293787236,
        3.9702160240822932,
    ),
    (
        "LB A0",
        9.82075967655328,
        0.043146386119843,
        -0.048999851666158,
        1.1955480642618987,
        3.929074252012369,
    ),
    (
        "LB B0",
        9.93700387280114,
        0.043102143275457,
        -0.049101025920726,
        1.1875264175099327,
        3.9223303269731855,
    ),
    (
        "LB C0",
        10.8857065066950,
        0.042768119191440,
        -0.049989874959669,
        1.127241338816112,
        3.854893595069231,
    ),
    (
        "LB N0",
        11.8419087661532,
        0.042473892850381,
        -0.051009815103168,
        1.0873771748874406,
        3.759845588531939,
    ),
)


def _mono_zones(radius_mm: float) -> tuple[R4ZonePrescription, ...]:
    spec = binary4_mechanism_spec("HOA")
    rows: list[R4ZonePrescription] = []
    inner = 0.0
    for index, outer in enumerate(spec.radial_apertures_mm, start=1):
        rows.append(
            R4ZonePrescription(
                zone=index,
                r_inner_mm=inner,
                r_outer_mm=outer,
                radius_mm=radius_mm,
                conic=0.0,
                alpha_p2_native=0.0,
                alpha_p4_native=0.0,
                alpha_p6_native=0.0,
                active=True,
            )
        )
        inner = outer
    return tuple(rows)


def _hoa_mechanism_percent(radius_mm: float) -> tuple[float, float]:
    spec = binary4_mechanism_spec("HOA")
    radii = np.arange(0.0, 3.0 + 0.5 * 0.025, 0.025, dtype=float)
    mono_sag, _ = binary4_piecewise_sag_mm(
        radii,
        spec.radial_apertures_mm,
        _mono_zones(radius_mm),
    )
    edof_sag, _ = binary4_piecewise_sag_mm(
        radii,
        spec.radial_apertures_mm,
        r5_2_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0),
    )
    index_step = (
        CONTROLLED_IOL_CARRIER_546_V1.refractive_index
        - CONTROLLED_IOL_CARRIER_546_V1.surrounding_index
    )
    fitted_opd = (edof_sag - mono_sag) * 1000.0 * index_step
    target = np.asarray([hoa_raw_opd_um(float(radius)) for radius in radii], dtype=float)
    weights = _zone_equal_weights(radii, spec.radial_apertures_mm)
    raw_difference = fitted_opd - target
    piston = float(np.sum(weights * raw_difference))
    difference = raw_difference - piston
    target_peak_to_peak = float(np.ptp(target))
    rms_fraction = math.sqrt(float(np.sum(weights * difference * difference))) / target_peak_to_peak
    max_fraction = float(np.max(np.abs(difference))) / target_peak_to_peak
    return 100.0 * rms_fraction, 100.0 * max_fraction


def test_r5_2_freeze_id_is_formal_and_versioned() -> None:
    assert R5_2_FREEZE_ID == "MODEL-REVISION-R5.2-HOA-BOUNDARY-SAG-INVARIANT-2026-08-21"


def test_r5_2_reproduces_plus20_hoa_prescription_bit_identically() -> None:
    previous = r5_1_zones_for_carrier(
        "HOA",
        base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
        base_conic=0.0,
    )
    current = r5_2_zones_for_carrier(
        "HOA",
        base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
        base_conic=0.0,
    )
    assert current == previous
    assert current[0].alpha_p6_native == 0.0423302736
    assert current[1].alpha_p6_native == -0.0516184660
    assert current[2].alpha_p6_native == 0.0


@pytest.mark.parametrize("platform", ["WFS", "RAD"])
@pytest.mark.parametrize("radius_mm", [9.8, 11.0, 13.2])
def test_r5_2_leaves_wfs_and_rad_bit_identical(platform: str, radius_mm: float) -> None:
    base_radius = radius_mm if platform == "WFS" else -radius_mm
    previous = r5_1_zones_for_carrier(
        platform,
        base_radius_mm=base_radius,
        base_conic=-5.0,
    )
    current = r5_2_zones_for_carrier(
        platform,
        base_radius_mm=base_radius,
        base_conic=-5.0,
    )
    assert current == previous


@pytest.mark.parametrize("_name,radius_mm,a6_zone1,a6_zone2,_rms,_maximum", _HOA_CASES)
def test_r5_2_known_hoa_carriers_reproduce_deterministic_a6(
    _name: str,
    radius_mm: float,
    a6_zone1: float,
    a6_zone2: float,
    _rms: float,
    _maximum: float,
) -> None:
    zones = r5_2_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0)
    assert zones[0].alpha_p6_native == pytest.approx(a6_zone1, abs=5.0e-15)
    assert zones[1].alpha_p6_native == pytest.approx(a6_zone2, abs=5.0e-15)
    assert zones[2].alpha_p6_native == 0.0


@pytest.mark.parametrize("_name,radius_mm,_a61,_a62,_rms,_maximum", _HOA_CASES)
def test_r5_2_preserves_both_complete_boundary_sag_invariants(
    _name: str,
    radius_mm: float,
    _a61: float,
    _a62: float,
    _rms: float,
    _maximum: float,
) -> None:
    reference = r5_2_zones_for_carrier(
        "HOA",
        base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
        base_conic=0.0,
    )
    current = r5_2_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0)
    for zone_index in (0, 1):
        target = r5_2_boundary_delta_z_mm(
            reference,
            base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
            base_conic=0.0,
            zone_index=zone_index,
        )
        achieved = r5_2_boundary_delta_z_mm(
            current,
            base_radius_mm=radius_mm,
            base_conic=0.0,
            zone_index=zone_index,
        )
        assert achieved == pytest.approx(target, abs=5.0e-14)


def test_r5_2_zone2_uses_updated_zone1_c0_state() -> None:
    radius_mm = 9.82075967655328
    r5_1 = r5_1_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0)
    r5_2 = r5_2_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0)
    reference = r5_2_zones_for_carrier(
        "HOA",
        base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
        base_conic=0.0,
    )
    target_zone2 = r5_2_boundary_delta_z_mm(
        reference,
        base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
        base_conic=0.0,
        zone_index=1,
    )

    stale_zone1 = (r5_1[0], r5_2[1], r5_2[2])
    stale_delta = r5_2_boundary_delta_z_mm(
        stale_zone1,
        base_radius_mm=radius_mm,
        base_conic=0.0,
        zone_index=1,
    )
    assert abs(stale_delta - target_zone2) > 1.0e-4
    assert r5_2[0].alpha_p6_native != r5_1[0].alpha_p6_native


@pytest.mark.parametrize("_name,radius_mm,_a61,_a62,expected_rms,expected_max", _HOA_CASES)
def test_r5_2_known_hoa_analytical_mechanism_values_pass_existing_gate(
    _name: str,
    radius_mm: float,
    _a61: float,
    _a62: float,
    expected_rms: float,
    expected_max: float,
) -> None:
    rms_percent, max_percent = _hoa_mechanism_percent(radius_mm)
    assert rms_percent == pytest.approx(expected_rms, abs=1.0e-9)
    assert max_percent == pytest.approx(expected_max, abs=1.0e-9)
    assert rms_percent <= 2.5
    assert max_percent <= 6.25


def test_r5_2_hoa_requires_q_ant_zero() -> None:
    with pytest.raises(ValueError, match="q_ant=0"):
        r5_2_zones_for_carrier("HOA", base_radius_mm=10.66, base_conic=1.0e-12)


@pytest.mark.parametrize("radius_mm", [0.0, -10.0, math.inf, -math.inf, math.nan])
def test_r5_2_rejects_illegal_hoa_radius(radius_mm: float) -> None:
    with pytest.raises(ValueError):
        r5_2_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0)


@pytest.mark.parametrize("base_conic", [math.inf, -math.inf, math.nan])
def test_r5_2_rejects_non_finite_hoa_conic(base_conic: float) -> None:
    with pytest.raises(ValueError):
        r5_2_zones_for_carrier("HOA", base_radius_mm=10.66, base_conic=base_conic)


def test_r5_2_preserves_hoa_topology_complexity_and_non_a6_terms() -> None:
    radius_mm = 10.66
    previous = r5_1_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0)
    current = r5_2_zones_for_carrier("HOA", base_radius_mm=radius_mm, base_conic=0.0)
    assert tuple(zone.r_outer_mm for zone in current) == (0.90, 1.10, 3.00)
    assert [zone.active for zone in current] == [True, True, False]
    for old, new in zip(previous, current, strict=True):
        assert new.radius_mm == old.radius_mm
        assert new.conic == old.conic
        assert new.alpha_p2_native == 0.0
        assert new.alpha_p4_native == old.alpha_p4_native
    assert current[2] == previous[2]
