from __future__ import annotations

from dataclasses import replace

import pytest

from whole_eye_mvp.base_assets import (
    CORNEA_ANT_ROLE,
    CORNEA_POST_ROLE,
    IMAGE_ROLE,
    IOL_ANT_ROLE,
    STOP_ROLE,
    base_asset_prescriptions,
)
from whole_eye_mvp.domain import BASELINE_BASE_SPECS, BaseId, ScientificBaseline


@pytest.mark.unit
def test_task_005b_prescriptions_freeze_sources_and_axial_reference_stack() -> None:
    prescriptions = base_asset_prescriptions(ScientificBaseline("MVP_2026_v1"))
    assert [item.base_spec.base_id for item in prescriptions] == [
        BaseId.LB_AL2395,
        BaseId.ATC_M3_AL24477,
    ]

    lb, atc = prescriptions
    assert lb.base_spec.source_model_id == "Liou_Brennan_1997"
    assert lb.base_spec.source_refraction_d is None
    assert atc.base_spec.source_model_id == "Atchison_2006_Model_1"
    assert atc.base_spec.source_refraction_d == -3.0

    expected_roles = (
        CORNEA_ANT_ROLE,
        CORNEA_POST_ROLE,
        STOP_ROLE,
        IOL_ANT_ROLE,
        IMAGE_ROLE,
    )
    assert tuple(surface.role for surface in lb.surfaces) == expected_roles
    assert tuple(surface.vertex_mm for surface in lb.surfaces) == (
        0.0,
        0.0,
        3.150,
        4.500,
        23.950,
    )
    assert tuple(surface.vertex_mm for surface in atc.surfaces) == (
        0.0,
        0.0,
        3.150,
        4.500,
        24.477,
    )
    assert lb.surfaces[0].medium_after_index is None
    assert [surface.medium_after_index for surface in lb.surfaces[1:4]] == [
        1.336,
        1.336,
        1.336,
    ]


@pytest.mark.unit
def test_base_prescription_contract_fails_closed() -> None:
    base = BASELINE_BASE_SPECS[0]
    with pytest.raises(ValueError, match="finite"):
        replace(base, axial_length_mm=float("nan")).validate()
    with pytest.raises(ValueError, match="strictly ordered"):
        replace(base, post_cornea_to_stop_mm=4.6).validate()
    with pytest.raises(ValueError, match="greater than one"):
        replace(base, vitreous_index=1.0).validate()


@pytest.mark.unit
def test_base_asset_set_must_contain_exactly_the_two_frozen_base_ids() -> None:
    baseline = ScientificBaseline("MVP_2026_v1", base_specs=(BASELINE_BASE_SPECS[0],))
    with pytest.raises(ValueError, match="base set mismatch"):
        base_asset_prescriptions(baseline)
