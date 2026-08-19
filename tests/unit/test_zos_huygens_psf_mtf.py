from __future__ import annotations

import math

import pytest

from whole_eye_mvp.zos.analyses import HuygensPsfGrid
from whole_eye_mvp.zos.huygens_psf_mtf import HuygensPsfMtfError, mtf_from_huygens_psf


def _grid(values: tuple[tuple[float, ...], ...], *, delta_um: float = 1.0) -> HuygensPsfGrid:
    size = len(values)
    return HuygensPsfGrid(
        values=values,
        min_x=-0.5 * (size - 1) * delta_um,
        min_y=-0.5 * (size - 1) * delta_um,
        dx=delta_um,
        dy=delta_um,
        x_label="X",
        y_label="Y",
        value_label="Intensity",
        description="synthetic",
    )


def test_centered_delta_has_unity_mtf() -> None:
    values = tuple(
        tuple(1.0 if (row, column) == (4, 4) else 0.0 for column in range(8))
        for row in range(8)
    )
    result = mtf_from_huygens_psf(_grid(values, delta_um=0.5))

    assert result.frequency_step_cyc_per_mm == pytest.approx(250.0)
    assert result.curve.frequency_cyc_per_mm == pytest.approx((0.0, 250.0, 500.0, 750.0))
    assert result.curve.tangential == pytest.approx((1.0, 1.0, 1.0, 1.0))
    assert result.curve.sagittal == pytest.approx((1.0, 1.0, 1.0, 1.0))
    assert result.curve.average == pytest.approx((1.0, 1.0, 1.0, 1.0))


def test_shifted_delta_keeps_unity_mtf_magnitude() -> None:
    values = tuple(
        tuple(2.0 if (row, column) == (2, 5) else 0.0 for column in range(8))
        for row in range(8)
    )
    result = mtf_from_huygens_psf(_grid(values))

    assert result.curve.average == pytest.approx((1.0, 1.0, 1.0, 1.0))


def test_broad_psf_reduces_nonzero_frequency_mtf() -> None:
    size = 16
    center = size // 2
    sigma = 2.0
    values = tuple(
        tuple(
            math.exp(-((row - center) ** 2 + (column - center) ** 2) / (2.0 * sigma**2))
            for column in range(size)
        )
        for row in range(size)
    )
    result = mtf_from_huygens_psf(_grid(values, delta_um=0.5))

    assert result.curve.average[0] == pytest.approx(1.0)
    assert result.curve.average[1] < 1.0
    assert result.curve.average[2] < result.curve.average[1]
    assert result.curve.tangential == pytest.approx(result.curve.sagittal)


def test_rejects_non_square_grid() -> None:
    grid = HuygensPsfGrid(
        values=((1.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        min_x=0.0,
        min_y=0.0,
        dx=1.0,
        dy=1.0,
        x_label="X",
        y_label="Y",
        value_label="Intensity",
        description="synthetic",
    )
    with pytest.raises(HuygensPsfMtfError, match="square"):
        mtf_from_huygens_psf(grid)
