from __future__ import annotations

from dataclasses import replace

import pytest

from whole_eye_mvp.cornea_assets import (
    MAIN_CORNEA_SCAFFOLD,
    MAIN_CORNEA_SCAFFOLD_ID,
    C0RadialDesign,
    CorneaSurfaceFamily,
    cornea_lock_prescriptions,
    distance_corrected_cornea_power_d,
    distance_corrected_front_radius_mm,
    paraxial_cornea_power_d,
    quintic_smoothstep,
    quintic_smoothstep_derivative,
    quintic_smoothstep_second_derivative,
)
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, CorneaId, ScientificBaseline


@pytest.mark.unit
def test_main_cornea_scaffold_freezes_liou_geometry_separately_from_standard_eye() -> None:
    scaffold = MAIN_CORNEA_SCAFFOLD
    scaffold.validate()
    assert scaffold.scaffold_id == MAIN_CORNEA_SCAFFOLD_ID == "MAIN_CORNEA_LIOU_555_v1"
    assert scaffold.wavelength_nm == 555.0
    assert scaffold.front_radius_mm == 7.77
    assert scaffold.front_conic == -0.18
    assert scaffold.thickness_mm == 0.50
    assert scaffold.back_radius_mm == 6.40
    assert scaffold.back_conic == -0.60
    assert scaffold.cornea_index == 1.376
    assert scaffold.aqueous_index == 1.336
    assert paraxial_cornea_power_d(scaffold.front_radius_mm) == pytest.approx(
        42.251148573823,
        abs=1e-12,
    )


@pytest.mark.unit
def test_minus_three_distance_baseline_is_analytic_and_reversible() -> None:
    target = distance_corrected_cornea_power_d(-3.0)
    radius = distance_corrected_front_radius_mm(-3.0)
    assert target == pytest.approx(39.251148573823, abs=1e-12)
    assert radius == pytest.approx(8.282294760256, abs=1e-12)
    assert paraxial_cornea_power_d(radius) == pytest.approx(target, abs=1e-12)


@pytest.mark.unit
def test_cornea_lock_prescriptions_freeze_a_five_b_candidates_and_c() -> None:
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    prescriptions = cornea_lock_prescriptions(baseline)
    assert [item.candidate_id for item in prescriptions] == [
        "A0",
        "B0.10",
        "B0.15",
        "B0.20",
        "B0.25",
        "B0.30",
        "C0",
    ]

    a = prescriptions[0]
    assert a.cornea_id == CorneaId.A0
    assert a.surface_family == CorneaSurfaceFamily.BINARY4
    assert a.treatment_d == -3.0
    assert a.optical_zone_mm == 5.0
    assert a.target_delta_c40_um == 0.13

    b = prescriptions[1:6]
    assert all(item.cornea_id == CorneaId.B0 for item in b)
    assert all(item.surface_family == CorneaSurfaceFamily.EVEN_ASPHERE for item in b)
    assert [item.target_delta_c40_um for item in b] == [0.10, 0.15, 0.20, 0.25, 0.30]
    assert all(item.optical_zone_mm == 6.0 for item in b)

    c = prescriptions[-1]
    assert c.cornea_id == CorneaId.C0
    assert c.surface_family == CorneaSurfaceFamily.BINARY4
    assert c.near_diameter_mm == 3.0
    assert c.add_rx_d == 1.75
    assert c.optical_zone_mm == 6.5
    assert c.transition_width_mm == 0.75
    assert c.near_radius_mm == 1.5
    assert c.transition_outer_radius_mm == 2.25
    assert c.optical_radius_mm == 3.25


@pytest.mark.unit
def test_c0_quintic_weight_has_exact_endpoint_value_slope_and_curvature() -> None:
    assert quintic_smoothstep(0.0) == 0.0
    assert quintic_smoothstep(1.0) == 1.0
    assert quintic_smoothstep_derivative(0.0) == 0.0
    assert quintic_smoothstep_derivative(1.0) == 0.0
    assert quintic_smoothstep_second_derivative(0.0) == 0.0
    assert quintic_smoothstep_second_derivative(1.0) == 0.0

    c = C0RadialDesign(cornea_lock_prescriptions(ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID))[-1])
    assert c.near_weight(0.0) == 1.0
    assert c.near_weight(1.5) == 1.0
    assert c.near_weight(1.875) == pytest.approx(0.5)
    assert c.near_weight(2.25) == 0.0
    assert c.near_weight(3.25) == 0.0


@pytest.mark.unit
def test_c0_design_maps_clinical_add_to_radial_target_power_without_redefining_add() -> None:
    c = C0RadialDesign(cornea_lock_prescriptions(ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID))[-1])
    distance = distance_corrected_cornea_power_d(-3.0)
    assert c.target_cornea_power_d(0.0) == pytest.approx(distance + 1.75)
    assert c.target_cornea_power_d(1.5) == pytest.approx(distance + 1.75)
    assert c.target_cornea_power_d(2.25) == pytest.approx(distance)
    assert c.target_cornea_power_d(3.25) == pytest.approx(distance)
    assert c.target_front_radius_mm(0.0) == pytest.approx(7.975550558942, abs=1e-12)
    assert c.target_front_radius_mm(3.25) == pytest.approx(8.282294760256, abs=1e-12)


@pytest.mark.unit
def test_prescription_contract_fails_closed_on_cross_archetype_semantics() -> None:
    prescriptions = cornea_lock_prescriptions(ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID))
    a, b, c = prescriptions[0], prescriptions[1], prescriptions[-1]
    with pytest.raises(ValueError, match="Binary4"):
        replace(a, surface_family=CorneaSurfaceFamily.EVEN_ASPHERE).validate()
    with pytest.raises(ValueError, match="near-add"):
        replace(b, near_diameter_mm=3.0).validate()
    with pytest.raises(ValueError, match="derived outputs"):
        replace(c, target_delta_c40_um=0.2).validate()
    with pytest.raises(ValueError, match="far-dominant annulus"):
        replace(c, transition_width_mm=1.75).validate()
