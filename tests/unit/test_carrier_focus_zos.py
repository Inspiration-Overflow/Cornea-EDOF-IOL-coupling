from __future__ import annotations

import pytest

from whole_eye_mvp.carrier_focus_zos import (
    P_Q_RECHECK_THRESHOLD_D,
    TASK007_POWER_FOCUS_EPD_MM,
    image_distance_shift_to_vergence_d,
)


def test_image_distance_shift_to_vergence_matches_exact_plane_vergence_change() -> None:
    fixed = 17.95
    best = 17.984
    expected = 1.336 * 1000.0 * (1.0 / best - 1.0 / fixed)
    assert image_distance_shift_to_vergence_d(fixed, best) == pytest.approx(expected)


def test_image_distance_shift_to_vergence_rejects_nonpositive_distance() -> None:
    with pytest.raises(ValueError, match="positive"):
        image_distance_shift_to_vergence_d(17.95, 0.0)


def test_task007_p_q_recheck_keeps_existing_focus_contract() -> None:
    assert TASK007_POWER_FOCUS_EPD_MM == 3.0
    assert P_Q_RECHECK_THRESHOLD_D == 0.125
