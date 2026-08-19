from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .analyses import HuygensPsfGrid
from .huygens_mtf import HuygensMtfCurve


class HuygensPsfMtfError(RuntimeError):
    """A Huygens PSF grid cannot be converted into the required image-space MTF."""


@dataclass(frozen=True, slots=True)
class HuygensPsfMtfResult:
    curve: HuygensMtfCurve
    frequency_step_cyc_per_mm: float


def mtf_from_huygens_psf(grid: HuygensPsfGrid) -> HuygensPsfMtfResult:
    """Compute Huygens MTF as the normalized FFT magnitude of a Huygens PSF grid.

    OpticStudio defines Huygens MTF as an FFT of the Huygens PSF. The PSF grid is
    sampled in image-space micrometers; the returned frequency axis is cycles/mm.
    Tangential MTF is the positive-y frequency cut and sagittal MTF the positive-x
    frequency cut, matching the OpticStudio Huygens MTF convention.
    """

    rows, columns = grid.shape
    if rows < 2 or columns < 2 or rows != columns:
        raise HuygensPsfMtfError("Huygens PSF→MTF requires a square grid of size >= 2")
    if not math.isfinite(grid.dx) or not math.isfinite(grid.dy) or grid.dx <= 0 or grid.dy <= 0:
        raise HuygensPsfMtfError("Huygens PSF grid spacing must be finite and positive")
    if not math.isclose(grid.dx, grid.dy, rel_tol=1e-12, abs_tol=1e-12):
        raise HuygensPsfMtfError("Huygens PSF→MTF requires equal x/y image sampling")

    values = np.asarray(grid.values, dtype=float)
    if values.shape != (rows, columns) or not np.isfinite(values).all():
        raise HuygensPsfMtfError("Huygens PSF grid contains invalid numeric data")
    if float(values.sum()) <= 0:
        raise HuygensPsfMtfError("Huygens PSF grid has no positive total energy")

    # The PSF is centered in image coordinates. Shift its origin to index zero before
    # the FFT, then shift the OTF so zero spatial frequency is at the array center.
    otf = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(values)))
    mtf = np.abs(otf)
    center = rows // 2
    dc = float(mtf[center, center])
    if not math.isfinite(dc) or dc <= 0:
        raise HuygensPsfMtfError("Huygens PSF FFT has no positive DC component")
    mtf /= dc

    spacing_mm = grid.dx / 1000.0
    frequencies = np.fft.fftshift(np.fft.fftfreq(columns, d=spacing_mm))
    positive = frequencies[center:]
    if len(positive) < 2 or positive[0] != 0.0:
        raise HuygensPsfMtfError("Huygens PSF FFT produced an invalid frequency axis")

    sagittal = mtf[center, center:]
    tangential = mtf[center:, center]
    if len(sagittal) != len(positive) or len(tangential) != len(positive):
        raise HuygensPsfMtfError("Huygens PSF FFT cuts do not match the frequency axis")

    frequency_tuple = tuple(float(value) for value in positive)
    sagittal_tuple = tuple(float(value) for value in sagittal)
    tangential_tuple = tuple(float(value) for value in tangential)
    average_tuple = tuple(
        0.5 * (t + s)
        for t, s in zip(tangential_tuple, sagittal_tuple, strict=True)
    )
    all_values = (*frequency_tuple, *tangential_tuple, *sagittal_tuple, *average_tuple)
    if not all(math.isfinite(value) for value in all_values):
        raise HuygensPsfMtfError("Huygens PSF-derived MTF contains non-finite values")
    if any(value < -1.0e-12 or value > 1.01 for value in average_tuple):
        raise HuygensPsfMtfError("Huygens PSF-derived MTF lies outside the expected [0, 1] range")

    step = frequency_tuple[1] - frequency_tuple[0]
    return HuygensPsfMtfResult(
        curve=HuygensMtfCurve(
            frequency_cyc_per_mm=frequency_tuple,
            tangential=tangential_tuple,
            sagittal=sagittal_tuple,
            average=average_tuple,
        ),
        frequency_step_cyc_per_mm=step,
    )
