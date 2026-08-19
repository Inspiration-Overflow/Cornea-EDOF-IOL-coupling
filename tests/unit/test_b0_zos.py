from __future__ import annotations

import pytest

from whole_eye_mvp.b0_zos import (
    B0_OBJECT_INFINITY_MM,
    B0ZosError,
    object_thickness_for_defocus_d,
    q_lock_from_mtfa_samples,
)
from whole_eye_mvp.domain import CORNEA_LOCK_B0_555_V2


@pytest.mark.unit
def test_b0_defocus_maps_only_to_analysis_object_vergence() -> None:
    assert object_thickness_for_defocus_d(0.0) == B0_OBJECT_INFINITY_MM
    assert object_thickness_for_defocus_d(-1.0) == pytest.approx(1000.0)
    assert object_thickness_for_defocus_d(-2.0) == pytest.approx(500.0)
    assert object_thickness_for_defocus_d(0.5) == pytest.approx(-2000.0)


@pytest.mark.unit
def test_b0_v2_freezes_five_cycle_frequency_grid() -> None:
    settings = CORNEA_LOCK_B0_555_V2
    settings.validate()
    assert settings.settings_id == "CORNEA_LOCK_B0_555_v2"
    assert settings.frequency_grid() == tuple(float(value) for value in range(0, 51, 5))
    assert settings.mtfa_grid == 0
    assert settings.mtfa_data_type == 0
    assert settings.wavelength_number == 1
    assert settings.field_number == 1


@pytest.mark.unit
def test_q_lock_is_normalized_mtfa_area_from_zero_to_fifty_cycles_per_mm() -> None:
    frequencies = (0.0, 25.0, 50.0)
    mtfa = (1.0, 0.5, 0.1)
    # trapezoid area = 25*(1+0.5)/2 + 25*(0.5+0.1)/2 = 26.25
    assert q_lock_from_mtfa_samples(
        frequencies,
        mtfa,
        maximum_frequency=50.0,
    ) == pytest.approx(26.25 / 50.0)


@pytest.mark.unit
def test_q_lock_requires_exact_frozen_frequency_boundaries() -> None:
    with pytest.raises(B0ZosError, match="start at 0"):
        q_lock_from_mtfa_samples(
            (5.0, 25.0, 50.0),
            (0.9, 0.5, 0.1),
            maximum_frequency=50.0,
        )
    with pytest.raises(B0ZosError, match="end at"):
        q_lock_from_mtfa_samples(
            (0.0, 25.0, 45.0),
            (1.0, 0.5, 0.1),
            maximum_frequency=50.0,
        )


@pytest.mark.unit
def test_frequency_grid_can_be_refined_for_probe_without_changing_v2_default() -> None:
    settings = CORNEA_LOCK_B0_555_V2
    refined = settings.frequency_grid(step_cyc_per_mm=2.5)
    assert len(refined) == 21
    assert refined[0] == 0.0
    assert refined[-1] == 50.0
    assert settings.frequency_grid()[1] == 5.0
