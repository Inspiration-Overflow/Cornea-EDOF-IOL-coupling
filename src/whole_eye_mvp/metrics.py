from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class DistancePeak:
    defocus_d: float
    value: float
    index: int
    peak_search_censored: bool


@dataclass(frozen=True, slots=True)
class DofInterval:
    far_d: float | None
    near_d: float | None
    width_d: float
    far_censored: bool = False
    near_censored: bool = False
    below_absolute_threshold: bool = False


def psf_to_complex_otf(psf: np.ndarray, *, pad_factor: int = 4) -> np.ndarray:
    psf = np.asarray(psf, dtype=float)
    if psf.ndim != 2 or min(psf.shape) < 1:
        raise ValueError("psf must be a non-empty 2D array")
    if not np.all(np.isfinite(psf)) or np.sum(psf) <= 0:
        raise ValueError("psf must contain finite positive total energy")
    if pad_factor < 1:
        raise ValueError("pad_factor must be >= 1")
    target = tuple(int(n * pad_factor) for n in psf.shape)
    before = tuple(t // 2 - n // 2 for t, n in zip(target, psf.shape))
    after = tuple(t - n - b for t, n, b in zip(target, psf.shape, before))
    padded = np.pad(psf, tuple(zip(before, after)))
    otf = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(padded)))
    center = tuple(n // 2 for n in otf.shape)
    dc = otf[center]
    if abs(dc) == 0:
        raise ValueError("OTF DC bin is zero")
    return otf / dc


def radial_mtf(otf: np.ndarray, fx_cpd: np.ndarray, fy_cpd: np.ndarray, *, max_cpd: int = 60) -> tuple[np.ndarray, np.ndarray]:
    otf = np.asarray(otf)
    fx = np.asarray(fx_cpd, dtype=float)
    fy = np.asarray(fy_cpd, dtype=float)
    if otf.shape != (fy.size, fx.size):
        raise ValueError("otf shape must be (len(fy), len(fx))")
    xx, yy = np.meshgrid(fx, fy)
    radius = np.hypot(xx, yy)
    mtf = np.abs(otf)
    grid = np.arange(0, max_cpd + 1, dtype=float)
    values = np.full_like(grid, np.nan)
    for i, f in enumerate(grid):
        mask = radius < 0.5 if i == 0 else (radius >= f - 0.5) & (radius < f + 0.5)
        if np.any(mask):
            values[i] = float(np.mean(mtf[mask]))
    return grid, values


def mtfa(frequencies_cpd: Sequence[float], radial_mtf_values: Sequence[float], *, max_cpd: float = 60.0) -> float:
    f = np.asarray(frequencies_cpd, dtype=float)
    m = np.asarray(radial_mtf_values, dtype=float)
    mask = np.isfinite(f) & np.isfinite(m) & (f >= 0) & (f <= max_cpd)
    f = f[mask]
    m = m[mask]
    if f.size < 2 or f[0] > 0 or f[-1] < max_cpd:
        raise ValueError("MTFa requires finite coverage from 0 through max_cpd")
    order = np.argsort(f)
    return float(np.trapezoid(m[order], f[order]) / max_cpd)


def csf_n(f_cpd: np.ndarray | float) -> np.ndarray:
    f = np.asarray(f_cpd, dtype=float)
    return 2.6 * (0.0192 + 0.114 * f) * np.exp(-((0.114 * f) ** 1.1))


def diffraction_limited_otf(radius_cpd: np.ndarray, *, pupil_mm: float, wavelength_nm: float) -> np.ndarray:
    radius = np.asarray(radius_cpd, dtype=float)
    fc = (pupil_mm / (wavelength_nm * 1e-6)) * np.tan(np.deg2rad(1.0))
    nu = radius / fc
    out = np.zeros_like(nu)
    mask = (nu >= 0) & (nu <= 1)
    x = nu[mask]
    out[mask] = (2 / np.pi) * (np.arccos(x) - x * np.sqrt(np.maximum(0.0, 1 - x**2)))
    return out


def vsotf_discrete(otf: np.ndarray, fx_cpd: Sequence[float], fy_cpd: Sequence[float], *, otf_dl: np.ndarray | None = None, max_cpd: float = 60.0) -> float:
    otf = np.asarray(otf, dtype=complex)
    fx = np.asarray(fx_cpd, dtype=float)
    fy = np.asarray(fy_cpd, dtype=float)
    if otf.shape != (fy.size, fx.size):
        raise ValueError("otf shape mismatch")
    xx, yy = np.meshgrid(fx, fy)
    radius = np.hypot(xx, yy)
    mask = radius <= max_cpd
    weights = csf_n(radius)
    reference = np.ones_like(radius) if otf_dl is None else np.asarray(otf_dl, dtype=float)
    if reference.shape != otf.shape:
        raise ValueError("otf_dl shape mismatch")
    numerator = np.sum(weights[mask] * np.real(otf[mask]))
    denominator = np.sum(weights[mask] * reference[mask])
    if denominator == 0:
        raise ValueError("VSOTF denominator is zero")
    return float(numerator / denominator)


def vsmtf_discrete(otf: np.ndarray, fx_cpd: Sequence[float], fy_cpd: Sequence[float], *, otf_dl: np.ndarray | None = None, max_cpd: float = 60.0) -> float:
    otf = np.asarray(otf, dtype=complex)
    fx = np.asarray(fx_cpd, dtype=float)
    fy = np.asarray(fy_cpd, dtype=float)
    xx, yy = np.meshgrid(fx, fy)
    radius = np.hypot(xx, yy)
    mask = radius <= max_cpd
    weights = csf_n(radius)
    reference = np.ones_like(radius) if otf_dl is None else np.asarray(otf_dl, dtype=float)
    return float(np.sum(weights[mask] * np.abs(otf[mask])) / np.sum(weights[mask] * reference[mask]))


def find_distance_peak(defocus_d: Sequence[float], values: Sequence[float]) -> DistancePeak:
    d = np.asarray(defocus_d, dtype=float)
    y = np.asarray(values, dtype=float)
    if d.shape != y.shape or d.ndim != 1 or d.size == 0:
        raise ValueError("defocus and values must be equal non-empty vectors")
    search = (d >= -0.5 - 1e-12) & (d <= 0.5 + 1e-12) & np.isfinite(y)
    if not np.any(search):
        raise ValueError("no finite samples in distance-peak search window")
    max_value = np.max(y[search])
    candidates = np.flatnonzero(search & np.isclose(y, max_value, rtol=0, atol=1e-12))
    index = min(candidates, key=lambda i: (abs(d[i]), -d[i]))
    edge = np.isclose(abs(d[index]), 0.5, atol=1e-12)
    return DistancePeak(float(d[index]), float(y[index]), int(index), bool(edge))


def _crossing(d1: float, y1: float, d2: float, y2: float, threshold: float) -> float:
    if y1 == y2:
        return float(d1)
    return float(d1 + (threshold - y1) * (d2 - d1) / (y2 - y1))


def dof_interval(defocus_d: Sequence[float], values: Sequence[float], *, peak: DistancePeak, threshold: float, absolute: bool = False) -> DofInterval:
    d = np.asarray(defocus_d, dtype=float)
    y = np.asarray(values, dtype=float)
    if absolute and peak.value < threshold:
        return DofInterval(None, None, 0.0, below_absolute_threshold=True)
    if not (0 <= peak.index < d.size):
        raise ValueError("peak index out of range")
    if y[peak.index] < threshold:
        return DofInterval(None, None, 0.0, below_absolute_threshold=absolute)
    left = peak.index
    while left > 0 and y[left - 1] >= threshold:
        left -= 1
    right = peak.index
    while right < d.size - 1 and y[right + 1] >= threshold:
        right += 1
    left_censored = left == 0 and y[left] >= threshold
    right_censored = right == d.size - 1 and y[right] >= threshold
    left_d = float(d[left]) if left_censored else _crossing(d[left - 1], y[left - 1], d[left], y[left], threshold)
    right_d = float(d[right]) if right_censored else _crossing(d[right], y[right], d[right + 1], y[right + 1], threshold)
    far = max(left_d, right_d)
    near = min(left_d, right_d)
    far_censored = left_censored if d[left] > d[right] else right_censored
    near_censored = right_censored if d[left] > d[right] else left_censored
    return DofInterval(far, near, abs(far - near), far_censored, near_censored)


def relative_dof(defocus_d: Sequence[float], values: Sequence[float], *, peak: DistancePeak, fraction: float = 0.5) -> DofInterval:
    return dof_interval(defocus_d, values, peak=peak, threshold=fraction * peak.value)


def absolute_dof(defocus_d: Sequence[float], values: Sequence[float], *, peak: DistancePeak, threshold: float = 0.10) -> DofInterval:
    return dof_interval(defocus_d, values, peak=peak, threshold=threshold, absolute=True)


def mm_per_degree(effective_focal_length_mm: float) -> float:
    return float(effective_focal_length_mm * np.tan(np.deg2rad(1.0)))


def cycles_mm_to_cpd(cycles_per_mm: np.ndarray | float, effective_focal_length_mm: float) -> np.ndarray:
    return np.asarray(cycles_per_mm, dtype=float) * mm_per_degree(effective_focal_length_mm)


def matched_numeric_delta(edof: Mapping[str, float], mono: Mapping[str, float]) -> dict[str, float]:
    if edof.keys() != mono.keys():
        raise ValueError("matched rows must have identical numeric keys")
    return {key: float(edof[key] - mono[key]) for key in edof}
