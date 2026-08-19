from __future__ import annotations

import pytest

from whole_eye_mvp.cornea_assets import (
    MAIN_CORNEA_SCAFFOLD,
    cornea_lock_prescriptions,
)
from whole_eye_mvp.cornea_candidates_zos import (
    A_TRANSITION_SLICES_NOMINAL,
    A_TRANSITION_WIDTH_MM,
    CORNEA_SUPPORT_RADIUS_MM,
    _a_zones,
)
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline


@pytest.mark.unit
def test_a0_binary4_has_treated_transition_and_untreated_regions() -> None:
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    prescription = cornea_lock_prescriptions(baseline)[0]
    inner_conic = -1.0
    zones = _a_zones(prescription, inner_conic)

    assert len(zones) == A_TRANSITION_SLICES_NOMINAL + 2
    assert zones[0].radial_aperture == pytest.approx(prescription.optical_radius_mm)
    assert zones[0].radius == pytest.approx(prescription.distance_front_radius_mm)
    assert zones[0].conic == pytest.approx(inner_conic)

    transition_outer = prescription.optical_radius_mm + A_TRANSITION_WIDTH_MM
    assert zones[-2].radial_aperture == pytest.approx(transition_outer)
    assert zones[-1].radial_aperture == pytest.approx(CORNEA_SUPPORT_RADIUS_MM)
    assert zones[-1].radius == pytest.approx(MAIN_CORNEA_SCAFFOLD.front_radius_mm)
    assert zones[-1].conic == pytest.approx(MAIN_CORNEA_SCAFFOLD.front_conic)

    apertures = tuple(zone.radial_aperture for zone in zones)
    assert apertures == tuple(sorted(apertures))
    assert all(right > left for left, right in zip(apertures, apertures[1:]))
