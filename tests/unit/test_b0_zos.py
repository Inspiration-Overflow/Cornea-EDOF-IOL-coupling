from __future__ import annotations

import pytest

from whole_eye_mvp.b0_zos import (
    B0_OBJECT_INFINITY_MM,
    object_thickness_for_defocus_d,
    q_lock_from_huygens_mtf,
)
from whole_eye_mvp.zos import HuygensMtfCurve


@pytest.mark.unit
def test_b0_defocus_maps_only_to_analysis_object_vergence() -> None:
    assert object_thickness_for_defocus_d(0.0) == B0_OBJECT_INFINITY_MM
    assert object_thickness_for_defocus_d(-1.0) == pytest.approx(1000.0)
    assert object_thickness_for_defocus_d(-2.0) == pytest.approx(500.0)
    assert object_thickness_for_defocus_d(0.5) == pytest.approx(-2000.0)


@pytest.mark.unit
def test_q_lock_is_normalized_mtf_area_from_zero_to_fifty_cycles_per_mm() -> None:
    curve = HuygensMtfCurve(
        frequency_cyc_per_mm=(0.0, 25.0, 50.0),
        tangential=(1.0, 0.6, 0.2),
        sagittal=(1.0, 0.4, 0.0),
        average=(1.0, 0.5, 0.1),
    )
    # trapezoid area = 25*(1+0.5)/2 + 25*(0.5+0.1)/2 = 26.25
    assert q_lock_from_huygens_mtf(curve) == pytest.approx(26.25 / 50.0)


@pytest.mark.unit
def test_q_lock_interpolates_exact_zero_and_fifty_boundaries() -> None:
    curve = HuygensMtfCurve(
        frequency_cyc_per_mm=(-10.0, 20.0, 60.0),
        tangential=(1.0, 0.7, 0.3),
        sagittal=(1.0, 0.7, 0.3),
        average=(1.0, 0.7, 0.3),
    )
    value = q_lock_from_huygens_mtf(curve)
    assert 0.0 < value < 1.0
