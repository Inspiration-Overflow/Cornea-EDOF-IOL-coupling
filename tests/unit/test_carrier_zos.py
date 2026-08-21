from __future__ import annotations

import pytest

from whole_eye_mvp.carrier_zos import (
    choose_paraxial_surface_type,
    iol_ant_to_image_mm_for_base,
)
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, BaseId, ScientificBaseline


def test_task007_base_specific_iol_to_image_distance_preserves_axial_length() -> None:
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    assert iol_ant_to_image_mm_for_base(
        baseline,
        BaseId.LB_AL2395,
        cornea_thickness_mm=0.5,
    ) == pytest.approx(18.950)
    assert iol_ant_to_image_mm_for_base(
        baseline,
        BaseId.ATC_M3_AL24477,
        cornea_thickness_mm=0.5,
    ) == pytest.approx(19.477)


def test_task007_base_specific_geometry_rejects_invalid_cornea_thickness() -> None:
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    with pytest.raises(ValueError, match="cornea thickness"):
        iol_ant_to_image_mm_for_base(
            baseline,
            BaseId.LB_AL2395,
            cornea_thickness_mm=0.0,
        )


def test_paraxial_surface_selection_prefers_exact_api_name() -> None:
    assert choose_paraxial_surface_type(("Standard", "Paraxial", "ParaxialXY")) == "Paraxial"


def test_paraxial_surface_selection_has_deterministic_fallback() -> None:
    assert choose_paraxial_surface_type(("Standard", "ParaxialXY", "ParaxialFoo")) == "ParaxialXY"
    assert choose_paraxial_surface_type(("Standard", "EvenAspheric")) is None
