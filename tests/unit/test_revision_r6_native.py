from __future__ import annotations

import pytest

from whole_eye_mvp.cornea_assets import MAIN_CORNEA_SCAFFOLD
from whole_eye_mvp.domain import ScientificBaseline
from whole_eye_mvp.revision_r6_native import (
    NATIVE_CORNEA_ANT_ROLE,
    native_cornea_rows,
)


def _spec(baseline: ScientificBaseline, base_id: str):
    return next(spec for spec in baseline.base_specs if spec.base_id == base_id)


@pytest.mark.parametrize("base_id", ["LB_AL2395", "ATC_M3_AL24477"])
def test_native_rows_carry_liou_cornea_geometry(base_id: str) -> None:
    rows = native_cornea_rows(ScientificBaseline("TEST"), base_id)
    assert tuple(row.role for row in rows) == (
        NATIVE_CORNEA_ANT_ROLE,
        "CORNEA_POST_FIXED",
        "STOP",
        "IOL_ANT_REF",
        "IMAGE_FIXED",
    )
    anterior, posterior = rows[0], rows[1]
    assert anterior.radius_mm == pytest.approx(MAIN_CORNEA_SCAFFOLD.front_radius_mm)
    assert anterior.conic == pytest.approx(MAIN_CORNEA_SCAFFOLD.front_conic)
    assert anterior.thickness_mm == pytest.approx(MAIN_CORNEA_SCAFFOLD.thickness_mm)
    assert anterior.medium_after_index == pytest.approx(
        MAIN_CORNEA_SCAFFOLD.cornea_index
    )
    assert posterior.radius_mm == pytest.approx(MAIN_CORNEA_SCAFFOLD.back_radius_mm)
    assert posterior.conic == pytest.approx(MAIN_CORNEA_SCAFFOLD.back_conic)
    assert posterior.medium_after_index == pytest.approx(
        MAIN_CORNEA_SCAFFOLD.aqueous_index
    )


@pytest.mark.parametrize("base_id", ["LB_AL2395", "ATC_M3_AL24477"])
def test_native_rows_preserve_frozen_axial_landmarks(base_id: str) -> None:
    baseline = ScientificBaseline("TEST")
    spec = _spec(baseline, base_id)
    rows = native_cornea_rows(baseline, base_id)
    assert rows[1].thickness_mm == pytest.approx(spec.post_cornea_to_stop_mm)
    assert rows[2].thickness_mm == pytest.approx(
        spec.post_cornea_to_iol_ant_mm - spec.post_cornea_to_stop_mm
    )
    assert rows[3].medium_after_index == pytest.approx(spec.vitreous_index)
    total_axial = sum(row.thickness_mm for row in rows)
    assert total_axial == pytest.approx(spec.axial_length_mm)


def test_native_rows_mark_unique_stop() -> None:
    rows = native_cornea_rows(ScientificBaseline("TEST"), "LB_AL2395")
    stop_rows = [row for row in rows if row.is_stop]
    assert len(stop_rows) == 1
    assert stop_rows[0].role == "STOP"
    assert rows[1].role == "CORNEA_POST_FIXED"
