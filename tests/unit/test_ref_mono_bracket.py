from __future__ import annotations

import pytest

from whole_eye_mvp import ref_mono_zos
from whole_eye_mvp.domain import ScientificBaseline
from whole_eye_mvp.ref_mono_zos import RefMonoZosError, solve_ref_mono_radius_mm


class _LinearShiftEye:
    """Focus shift model: positive (underpowered) above the root radius."""

    def __init__(self, root_radius_mm: float) -> None:
        self.root_radius_mm = root_radius_mm
        self.radius_mm = 0.0

    def set_radius(self, session: object, radius_mm: float) -> None:
        self.radius_mm = radius_mm

    def focus_shift(self, session: object) -> float:
        return self.radius_mm - self.root_radius_mm


@pytest.fixture
def _patched_solver(monkeypatch: pytest.MonkeyPatch):
    def install(root_radius_mm: float) -> _LinearShiftEye:
        eye = _LinearShiftEye(root_radius_mm)
        monkeypatch.setattr(ref_mono_zos, "_set_symmetric_radius", eye.set_radius)
        monkeypatch.setattr(ref_mono_zos, "_focus_shift_mm", eye.focus_shift)
        return eye

    return install


def test_bracket_widens_downward_for_plano_cornea_reference_eye(
    _patched_solver,
) -> None:
    _patched_solver(root_radius_mm=5.9)
    radius, shift = solve_ref_mono_radius_mm(
        None,  # type: ignore[arg-type]
        ScientificBaseline("TEST"),
        initial_radius_mm=32.5,
    )
    assert radius == pytest.approx(5.9, abs=1.0e-3)
    assert shift == pytest.approx(0.0, abs=1.0e-3)


def test_nominal_bracket_still_solves_without_expansion(_patched_solver) -> None:
    _patched_solver(root_radius_mm=12.0)
    radius, shift = solve_ref_mono_radius_mm(
        None,  # type: ignore[arg-type]
        ScientificBaseline("TEST"),
        initial_radius_mm=12.5,
    )
    assert radius == pytest.approx(12.0, abs=1.0e-3)
    assert shift == pytest.approx(0.0, abs=1.0e-3)


def test_floor_exhaustion_raises(_patched_solver) -> None:
    _patched_solver(root_radius_mm=0.2)
    with pytest.raises(RefMonoZosError, match="does not straddle"):
        solve_ref_mono_radius_mm(
            None,  # type: ignore[arg-type]
            ScientificBaseline("TEST"),
            initial_radius_mm=32.5,
        )


def test_cap_exhaustion_raises(_patched_solver) -> None:
    _patched_solver(root_radius_mm=1000.0)
    with pytest.raises(RefMonoZosError, match="does not straddle"):
        solve_ref_mono_radius_mm(
            None,  # type: ignore[arg-type]
            ScientificBaseline("TEST"),
            initial_radius_mm=32.5,
        )
