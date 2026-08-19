from __future__ import annotations

from whole_eye_mvp.carrier_q_zos import _find_q_bracket


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


def test_q_bracket_accepts_exact_target_sample() -> None:
    samples = {-2.0: -0.20, 0.0: 0.0, 2.0: 0.20}
    assert _find_q_bracket(samples, -0.20) == (-2.0, -2.0)
