from __future__ import annotations

from whole_eye_mvp.grid_sag_residual import (
    GRID_SAG_HALF_WIDTH_MM,
    GRID_SAG_SIZE,
    GRID_SAG_STEP_MM,
    _interp_radial,
    write_grid_sag_dat,
)
from whole_eye_mvp.residual_payload import build_wfs_residual_candidate


def test_grid_sag_geometry_is_centered_and_has_margin() -> None:
    assert GRID_SAG_SIZE == 611
    assert GRID_SAG_STEP_MM == 0.01
    assert GRID_SAG_HALF_WIDTH_MM == 3.05
    assert (GRID_SAG_SIZE - 1) * GRID_SAG_STEP_MM == 2 * GRID_SAG_HALF_WIDTH_MM


def test_radial_interpolation_clamps_only_outside_physical_payload() -> None:
    radii = (0.0, 1.0, 2.0)
    values = (0.0, 10.0, 20.0)
    assert _interp_radial(radii, values, 0.5) == 5.0
    assert _interp_radial(radii, values, 1.5) == 15.0
    assert _interp_radial(radii, values, 3.0) == 20.0


def test_grid_sag_dat_has_expected_header_and_point_count(tmp_path) -> None:
    candidate = build_wfs_residual_candidate()
    path = write_grid_sag_dat(candidate, tmp_path / "wfs.dat")
    lines = path.read_text(encoding="ascii").splitlines()
    assert lines[0] == "611 611 0.01 0.01 0 0 0"
    assert len(lines) == 1 + GRID_SAG_SIZE * GRID_SAG_SIZE
    center = 1 + (GRID_SAG_SIZE // 2) * GRID_SAG_SIZE + GRID_SAG_SIZE // 2
    assert float(lines[center].split()[0]) == candidate.surface_sag_um[0] / 1000.0
