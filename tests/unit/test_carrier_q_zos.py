from __future__ import annotations

import pytest

from whole_eye_mvp.carrier_q_zos import (
    _find_q_bracket,
    paraxial_focal_length_mm_from_power_d,
    surface_power_pair_from_radii,
)
from whole_eye_mvp.ref_mono import symmetric_biconvex_power_d


def test_surface_power_pair_preserves_controlled_carrier_equivalent_power() -> None:
    radius = 9.77576192316701
    pair = surface_power_pair_from_radii(radius, -radius)
    assert pair.anterior_power_d > 0.0
    assert pair.posterior_power_d > 0.0
    assert pair.equivalent_power_d == pytest.approx(
        symmetric_biconvex_power_d(radius), abs=1.0e-12
    )
    assert pair.anterior_focal_length_mm == pytest.approx(
        1000.0 / pair.anterior_power_d, abs=1.0e-12
    )
    assert pair.posterior_focal_length_mm == pytest.approx(
        1000.0 / pair.posterior_power_d, abs=1.0e-12
    )


def test_paraxial_focal_length_uses_air_defined_dioptric_power() -> None:
    assert paraxial_focal_length_mm_from_power_d(20.0) == pytest.approx(50.0)
    assert paraxial_focal_length_mm_from_power_d(-10.0) == pytest.approx(-100.0)
    with pytest.raises(ValueError, match="non-zero"):
        paraxial_focal_length_mm_from_power_d(0.0)


def test_q_bracket_prefers_nearest_sign_change_to_zero() -> None:
    samples = {
        -8.0: -0.40,
        -4.0: -0.22,
        -2.0: -0.10,
        0.0: 0.05,
        4.0: 0.30,
    }
    assert _find_q_bracket(samples, -0.20) == (-4.0, -2.0)


def test_q_bracket_returns_none_when_target_is_not_bracketed() -> None:
    samples = {-2.0: 0.10, 0.0: 0.20, 2.0: 0.30}
    assert _find_q_bracket(samples, -0.20) is None
