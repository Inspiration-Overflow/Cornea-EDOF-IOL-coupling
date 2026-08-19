from __future__ import annotations

from dataclasses import replace

import pytest

from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline
from whole_eye_mvp.ref_mono import (
    REF_MONO_ENVELOPE,
    REF_MONO_ID,
    initial_ref_mono_radius_mm,
    paraxial_ref_mono_image_height_mm,
    symmetric_biconvex_power_d,
)


@pytest.mark.unit
def test_ref_mono_envelope_freezes_simple_platform_independent_geometry() -> None:
    envelope = REF_MONO_ENVELOPE
    envelope.validate()
    assert envelope.reference_id == REF_MONO_ID == "REF_MONO_CORNEA_LOCK"
    assert envelope.iol_index == 1.46
    assert envelope.center_thickness_mm == 1.0
    assert envelope.optic_diameter_mm == 6.0
    assert envelope.focus_epd_mm == 3.0


@pytest.mark.unit
def test_ref_mono_paraxial_starting_radius_focuses_distance_cornea() -> None:
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    radius = initial_ref_mono_radius_mm(baseline)
    assert radius == pytest.approx(9.599520722484, abs=1e-9)
    assert paraxial_ref_mono_image_height_mm(radius, baseline) == pytest.approx(0.0, abs=1e-10)
    assert symmetric_biconvex_power_d(radius) == pytest.approx(25.720337546275, abs=1e-9)


@pytest.mark.unit
def test_ref_mono_starting_radius_contract_rejects_invalid_envelope_or_bracket() -> None:
    with pytest.raises(ValueError, match="IOL index"):
        replace(REF_MONO_ENVELOPE, iol_index=1.30).validate()

    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    with pytest.raises(ValueError, match="strictly ordered"):
        initial_ref_mono_radius_mm(baseline, lower_mm=10.0, upper_mm=5.0)
    with pytest.raises(ValueError, match="does not contain"):
        initial_ref_mono_radius_mm(baseline, lower_mm=15.0, upper_mm=20.0)
