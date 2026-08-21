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


def average_sagittal_tangential_mtf(
    sagittal: Sequence[float], tangential: Sequence[float]
) -> np.ndarray:
    sag = np.asarray(sagittal, dtype=float)
    tan = np.asarray(tangential, dtype=float)
    if sag.shape != tan.shape or sag.ndim != 1 or sag.size == 0:
        raise ValueError("sagittal and tangential MTF must be equal non-empty vectors")
    if not np.all(np.isfinite(sag)) or not np.all(np.isfinite(tan)):
        raise ValueError("MTF values must be finite")
    if np.any(sag < 0) or np.any(tan < 0):
        raise ValueError("modulation MTF values must be non-negative")
    return 0.5 * (sag + tan)


def mm_per_degree(effective_focal_length_mm: float) -> float:
    if not np.isfinite(effective_focal_length_mm) or effective_focal_length_mm <= 0:
        raise ValueError("effective focal length must be finite and positive")
    return float(effective_focal_length_mm * np.tan(np.deg2rad(1.0)))


def cycles_mm_to_cpd(
    cycles_per_mm: np.ndarray | Sequence[float] | float,
    effective_focal_length_mm: float,
) -> np.ndarray:
    values = np.asarray(cycles_per_mm, dtype=float)
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("cycles/mm values must be finite and non-negative")
    return values * mm_per_degree(effective_focal_length_mm)


def cpd_to_cycles_mm(
    cycles_per_degree: np.ndarray | Sequence[float] | float,
    effective_focal_length_mm: float,
) -> np.ndarray:
    values = np.asarray(cycles_per_degree, dtype=float)
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("cycles/degree values must be finite and non-negative")
    return values / mm_per_degree(effective_focal_length_mm)


def mtfa(
    frequencies_cpd: Sequence[float],
    mtf_values: Sequence[float],
    *,
    max_cpd: float = 60.0,
) -> float:
    f = np.asarray(frequencies_cpd, dtype=float)
    m = np.asarray(mtf_values, dtype=float)
    if f.shape != m.shape or f.ndim != 1:
        raise ValueError("MTFa frequency and MTF vectors must have equal one-dimensional shape")
    mask = np.isfinite(f) & np.isfinite(m) & (f >= 0) & (f <= max_cpd)
    f = f[mask]
    m = m[mask]
    if f.size < 2:
        raise ValueError("MTFa requires at least two finite samples")
    order = np.argsort(f)
    f = f[order]
    m = m[order]
    if f[0] > 1e-12 or f[-1] < max_cpd - 1e-12:
        raise ValueError("MTFa requires finite coverage from 0 through max_cpd")
    return float(np.trapezoid(m, f) / max_cpd)


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


def dof_interval(
    defocus_d: Sequence[float],
    values: Sequence[float],
    *,
    peak: DistancePeak,
    threshold: float,
) -> DofInterval:
    d = np.asarray(defocus_d, dtype=float)
    y = np.asarray(values, dtype=float)
    if d.shape != y.shape or d.ndim != 1 or d.size == 0:
        raise ValueError("defocus and values must be equal non-empty vectors")
    if not (0 <= peak.index < d.size):
        raise ValueError("peak index out of range")
    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError("DOF threshold must be finite and non-negative")
    if y[peak.index] < threshold:
        return DofInterval(None, None, 0.0)

    left = peak.index
    while left > 0 and y[left - 1] >= threshold:
        left -= 1
    right = peak.index
    while right < d.size - 1 and y[right + 1] >= threshold:
        right += 1

    left_censored = left == 0 and y[left] >= threshold
    right_censored = right == d.size - 1 and y[right] >= threshold
    left_d = (
        float(d[left])
        if left_censored
        else _crossing(d[left - 1], y[left - 1], d[left], y[left], threshold)
    )
    right_d = (
        float(d[right])
        if right_censored
        else _crossing(d[right], y[right], d[right + 1], y[right + 1], threshold)
    )
    far = max(left_d, right_d)
    near = min(left_d, right_d)
    far_censored = left_censored if d[left] > d[right] else right_censored
    near_censored = right_censored if d[left] > d[right] else left_censored
    return DofInterval(far, near, abs(far - near), far_censored, near_censored)


def distance_anchored_dof50(
    defocus_d: Sequence[float],
    mtfa_values: Sequence[float],
    *,
    peak: DistancePeak | None = None,
) -> DofInterval:
    distance_peak = peak or find_distance_peak(defocus_d, mtfa_values)
    return dof_interval(
        defocus_d,
        mtfa_values,
        peak=distance_peak,
        threshold=0.5 * distance_peak.value,
    )


def through_focus_mean(defocus_d: Sequence[float], values: Sequence[float]) -> float:
    d = np.asarray(defocus_d, dtype=float)
    y = np.asarray(values, dtype=float)
    if d.shape != y.shape or d.ndim != 1 or d.size < 2:
        raise ValueError("through-focus mean requires equal vectors with at least two samples")
    if not np.all(np.isfinite(d)) or not np.all(np.isfinite(y)):
        raise ValueError("through-focus data must be finite")
    order = np.argsort(d)
    d = d[order]
    y = y[order]
    span = float(d[-1] - d[0])
    if span <= 0:
        raise ValueError("through-focus defocus span must be positive")
    return float(np.trapezoid(y, d) / span)


def matched_numeric_delta(
    edof: Mapping[str, float], mono: Mapping[str, float]
) -> dict[str, float]:
    if edof.keys() != mono.keys():
        raise ValueError("matched rows must have identical numeric keys")
    return {key: float(edof[key] - mono[key]) for key in edof}
