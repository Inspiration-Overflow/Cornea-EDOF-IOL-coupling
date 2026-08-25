"""Contracts and offline derivations for the prespecified supplemental experiments.

This module deliberately contains no OpticStudio adapter and no optical constants.  It
validates the data produced by the local acquisition layer and derives the requested
supplemental outcomes from already-exported through-focus rows.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise

from .metrics import DistancePeak, DofInterval, cpd_to_cycles_mm, dof_interval
from .run72_analysis import NumericBound

SUPPLEMENTAL_DEFOCUS_START_D = 1.0
SUPPLEMENTAL_DEFOCUS_STOP_D = -5.0
SUPPLEMENTAL_DEFOCUS_STEP_D = -0.125
SUPPLEMENTAL_DEFOCUS_GRID = tuple(
    round(SUPPLEMENTAL_DEFOCUS_START_D + index * SUPPLEMENTAL_DEFOCUS_STEP_D, 10)
    for index in range(49)
)
SUPPLEMENTAL_PEAK_SEARCH_MIN_D = -1.0
SUPPLEMENTAL_PEAK_SEARCH_MAX_D = 1.0
SUPPLEMENTAL_RELATIVE_THRESHOLDS = (0.30, 0.50, 0.70)
CENTRAL_NEAR_CORNEA_ID = "C0"
CENTRAL_NEAR_ADD_D = 1.75
DISTANCE_COMPONENT_ANCHORED = "distance_component_anchored"
FULL_EYE_CALIBRATION = "full_eye"
BASE_IDS = ("LB_AL2395", "ATC_M3_AL24477")
CORNEA_IDS = ("N0", "A0", "B0", "C0")
PLATFORM_IDS = ("WFS", "RAD", "HOA")
PUPIL_MM = (3.0, 5.0)
OPTIC_STATES = ("MONO", "EDOF")
ABS_TOL = 1.0e-9


class SupplementalExperimentError(ValueError):
    """An input violates the supplemental experiment contract."""


@dataclass(frozen=True, slots=True)
class SupplementalRow:
    """One exported through-focus point with the fixed 30 cpd measurement."""

    config_id: str
    pair_key: str
    base_id: str
    cornea_id: str
    platform_id: str
    pupil_mm: float
    optic_state: str
    defocus_d: float
    mtfa: float
    mtf30_cpd: float


@dataclass(frozen=True, slots=True)
class SupplementalConfig:
    """Configuration metadata required to match MONO and EDOF states."""

    config_id: str
    pair_key: str
    base_id: str
    cornea_id: str
    platform_id: str
    pupil_mm: float
    optic_state: str
    calibration_strategy: str = FULL_EYE_CALIBRATION
    carrier_key: str = ""
    near_add_d: float = CENTRAL_NEAR_ADD_D
    near_add_zeroed_for_solve: bool = False
    carrier_frozen: bool = True
    near_add_restored: bool = True
    post_restore_iol_power_solves: int = 0
    post_restore_refocus_count: int = 0
    post_restore_carrier_optimizations: int = 0

    def validate(self) -> None:
        if not self.config_id or not self.pair_key or not self.carrier_key:
            raise SupplementalExperimentError("config_id, pair_key, and carrier_key are required")
        if self.base_id not in BASE_IDS:
            raise SupplementalExperimentError(f"unsupported base_id: {self.base_id}")
        if self.cornea_id not in CORNEA_IDS:
            raise SupplementalExperimentError(f"unsupported cornea_id: {self.cornea_id}")
        if self.platform_id not in PLATFORM_IDS:
            raise SupplementalExperimentError(f"unsupported platform_id: {self.platform_id}")
        if self.pupil_mm not in PUPIL_MM:
            raise SupplementalExperimentError(f"unsupported physical pupil: {self.pupil_mm}")
        if self.optic_state not in OPTIC_STATES:
            raise SupplementalExperimentError(f"unsupported optic_state: {self.optic_state}")
        if not math.isclose(self.near_add_d, CENTRAL_NEAR_ADD_D, abs_tol=ABS_TOL):
            raise SupplementalExperimentError("restored central near add must equal +1.75 D")
        if self.calibration_strategy == DISTANCE_COMPONENT_ANCHORED:
            if self.cornea_id != CENTRAL_NEAR_CORNEA_ID:
                raise SupplementalExperimentError("distance-anchored strategy is limited to C0")
            if not self.near_add_zeroed_for_solve:
                raise SupplementalExperimentError("distance-anchored solve must record near-add zeroing")
            if not self.carrier_frozen or not self.near_add_restored:
                raise SupplementalExperimentError("distance-anchored carrier must be frozen before restoring near add")
            if any(
                value != 0
                for value in (
                    self.post_restore_iol_power_solves,
                    self.post_restore_refocus_count,
                    self.post_restore_carrier_optimizations,
                )
            ):
                raise SupplementalExperimentError("no IOL solve, refocus, or carrier optimization is allowed after restoration")
        elif self.calibration_strategy != FULL_EYE_CALIBRATION:
            raise SupplementalExperimentError(f"unknown calibration strategy: {self.calibration_strategy}")


@dataclass(frozen=True, slots=True)
class SupplementalMetrics:
    """Metrics derived from one config's through-focus curve."""

    config_id: str
    peak_defocus_d: float
    peak_mtfa: float
    peak_search_censored: bool
    mtfa_at_zero_d: float
    tf_mtfa_mean: float
    dof_by_threshold: Mapping[float, DofInterval]
    common_threshold_dof: DofInterval | None
    mtf30_cpd_curve: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class DifferenceInDifferences:
    """Special-cornea EDOF effect minus untreated-reference EDOF effect."""

    base_id: str
    cornea_id: str
    platform_id: str
    pupil_mm: float
    threshold: float
    value: float
    bound_status: str
    lower_bound: float | None
    upper_bound: float | None
    source_peak_censored: bool


def validate_supplemental_grid(defocus_d: Sequence[float]) -> tuple[float, ...]:
    observed = tuple(round(float(value), 10) for value in defocus_d)
    if observed != SUPPLEMENTAL_DEFOCUS_GRID:
        raise SupplementalExperimentError(
            "through-focus grid must be exactly +1.00 to -5.00 D at -0.125 D, 49 planes"
        )
    return observed


def _finite_vector(values: Sequence[float], *, field: str) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result or not all(math.isfinite(value) for value in result):
        raise SupplementalExperimentError(f"{field} must contain finite values")
    return result


def find_supplemental_distance_peak(
    defocus_d: Sequence[float], values: Sequence[float]
) -> DistancePeak:
    d = _finite_vector(defocus_d, field="defocus_d")
    y = _finite_vector(values, field="curve values")
    if len(d) != len(y):
        raise SupplementalExperimentError("defocus and curve vectors must have equal length")
    validate_supplemental_grid(d)
    candidates = [
        index
        for index, value in enumerate(d)
        if SUPPLEMENTAL_PEAK_SEARCH_MIN_D - ABS_TOL <= value <= SUPPLEMENTAL_PEAK_SEARCH_MAX_D + ABS_TOL
        and y[index] >= 0
    ]
    if not candidates:
        raise SupplementalExperimentError("no sample exists in the ±1.00 D peak-search window")
    max_value = max(y[index] for index in candidates)
    tied = [index for index in candidates if math.isclose(y[index], max_value, abs_tol=ABS_TOL)]
    index = min(tied, key=lambda item: (abs(d[item]), -d[item]))
    censored = math.isclose(abs(d[index]), 1.0, abs_tol=ABS_TOL)
    return DistancePeak(float(d[index]), float(y[index]), index, censored)


def _mean_curve(defocus_d: Sequence[float], values: Sequence[float]) -> float:
    points = sorted(zip(defocus_d, values, strict=True))
    area = sum(
        (x1 - x0) * (y0 + y1) / 2.0
        for (x0, y0), (x1, y1) in pairwise(points)
    )
    span = points[-1][0] - points[0][0]
    if not math.isclose(span, 6.0, abs_tol=ABS_TOL):
        raise SupplementalExperimentError("expanded through-focus span must equal 6.00 D")
    return float(area / span)


def derive_config_metrics(
    rows: Sequence[SupplementalRow], *, common_threshold: float | None = None
) -> SupplementalMetrics:
    if not rows:
        raise SupplementalExperimentError("at least one through-focus row is required")
    ordered = tuple(sorted(rows, key=lambda row: row.defocus_d, reverse=True))
    if len({row.config_id for row in ordered}) != 1:
        raise SupplementalExperimentError("one config is required per metric derivation")
    validate_supplemental_grid([row.defocus_d for row in ordered])
    mtfa = _finite_vector([row.mtfa for row in ordered], field="mtfa")
    mtf30 = _finite_vector([row.mtf30_cpd for row in ordered], field="mtf30_cpd")
    if any(value < 0 for value in mtfa + mtf30):
        raise SupplementalExperimentError("MTFa and 30 cpd values must be non-negative")
    peak = find_supplemental_distance_peak([row.defocus_d for row in ordered], mtfa)
    zero_rows = [row for row in ordered if math.isclose(row.defocus_d, 0.0, abs_tol=ABS_TOL)]
    if len(zero_rows) != 1:
        raise SupplementalExperimentError("expanded grid must contain exactly one 0-D row")
    dof_by_threshold = {
        fraction: dof_interval(
            [row.defocus_d for row in ordered],
            mtfa,
            peak=peak,
            threshold=fraction * peak.value,
        )
        for fraction in SUPPLEMENTAL_RELATIVE_THRESHOLDS
    }
    common_dof = None
    if common_threshold is not None:
        if not math.isfinite(common_threshold) or common_threshold < 0:
            raise SupplementalExperimentError("common threshold must be finite and non-negative")
        common_dof = dof_interval(
            [row.defocus_d for row in ordered], mtfa, peak=peak, threshold=common_threshold
        )
    return SupplementalMetrics(
        config_id=ordered[0].config_id,
        peak_defocus_d=peak.defocus_d,
        peak_mtfa=peak.value,
        peak_search_censored=peak.peak_search_censored,
        mtfa_at_zero_d=zero_rows[0].mtfa,
        tf_mtfa_mean=_mean_curve([row.defocus_d for row in ordered], mtfa),
        dof_by_threshold=dof_by_threshold,
        common_threshold_dof=common_dof,
        mtf30_cpd_curve=tuple((row.defocus_d, row.mtf30_cpd) for row in ordered),
    )


def build_distance_component_anchored_plan(
    carrier_keys: Mapping[tuple[str, str], str],
) -> tuple[SupplementalConfig, ...]:
    """Build exactly 24 C0 config identities from externally supplied carrier locks."""

    expected_keys = {(base, platform) for base in BASE_IDS for platform in PLATFORM_IDS}
    if set(carrier_keys) != expected_keys or not all(carrier_keys.values()):
        raise SupplementalExperimentError("six non-empty base/platform carrier keys are required")
    plan: list[SupplementalConfig] = []
    for base in BASE_IDS:
        for platform in PLATFORM_IDS:
            carrier_key = carrier_keys[(base, platform)]
            for pupil in PUPIL_MM:
                for state in OPTIC_STATES:
                    pair_key = f"SUPP_C0_DISTANCE_{base}_{platform}_EPD{int(pupil)}"
                    config = SupplementalConfig(
                        config_id=f"{pair_key}_{state}",
                        pair_key=pair_key,
                        base_id=base,
                        cornea_id=CENTRAL_NEAR_CORNEA_ID,
                        platform_id=platform,
                        pupil_mm=pupil,
                        optic_state=state,
                        calibration_strategy=DISTANCE_COMPONENT_ANCHORED,
                        carrier_key=carrier_key,
                        near_add_zeroed_for_solve=True,
                    )
                    config.validate()
                    plan.append(config)
    validate_distance_component_anchored_plan(plan)
    return tuple(plan)


def validate_distance_component_anchored_plan(configs: Sequence[SupplementalConfig]) -> None:
    if len(configs) != 24:
        raise SupplementalExperimentError(f"distance-anchored branch must contain 24 configs, got {len(configs)}")
    for config in configs:
        config.validate()
    identities = {
        (config.base_id, config.cornea_id, config.platform_id, config.pupil_mm, config.optic_state)
        for config in configs
    }
    expected = {
        (base, CENTRAL_NEAR_CORNEA_ID, platform, pupil, state)
        for base in BASE_IDS
        for platform in PLATFORM_IDS
        for pupil in PUPIL_MM
        for state in OPTIC_STATES
    }
    if identities != expected:
        raise SupplementalExperimentError("distance-anchored coverage is not exact 2×1×3×2×2")
    by_pair: dict[str, list[SupplementalConfig]] = defaultdict(list)
    for config in configs:
        by_pair[config.pair_key].append(config)
    if len(by_pair) != 12 or any({item.optic_state for item in items} != set(OPTIC_STATES) for items in by_pair.values()):
        raise SupplementalExperimentError("each distance-anchored pair must contain MONO and EDOF")
    for items in by_pair.values():
        if len({item.carrier_key for item in items}) != 1:
            raise SupplementalExperimentError("matched MONO/EDOF states must share one frozen carrier")


def common_reference_threshold(reference: SupplementalMetrics) -> float:
    return 0.5 * reference.peak_mtfa


def _bound_for_threshold(metrics: SupplementalMetrics, threshold: float) -> NumericBound:
    interval = metrics.dof_by_threshold[threshold]
    # Either boundary censor means the observed width is a lower bound.  The
    # unobserved interval can only extend beyond the measured window; it cannot
    # make the true width smaller than the reported interval.
    status = "lower_bound" if interval.far_censored or interval.near_censored else "exact"
    return NumericBound.from_status(interval.width_d, status)


def derive_difference_in_differences(
    special_mono: SupplementalMetrics,
    special_edof: SupplementalMetrics,
    reference_mono: SupplementalMetrics,
    reference_edof: SupplementalMetrics,
    *,
    base_id: str,
    cornea_id: str,
    platform_id: str,
    pupil_mm: float,
) -> tuple[DifferenceInDifferences, ...]:
    if special_mono.config_id == special_edof.config_id or reference_mono.config_id == reference_edof.config_id:
        raise SupplementalExperimentError("MONO and EDOF metrics must be separate config results")
    rows: list[DifferenceInDifferences] = []
    for threshold in SUPPLEMENTAL_RELATIVE_THRESHOLDS:
        bound = _bound_for_threshold(special_edof, threshold).add(
            _bound_for_threshold(special_mono, threshold).scaled(-1.0)
        ).add(
            _bound_for_threshold(reference_edof, threshold).scaled(-1.0)
        ).add(
            _bound_for_threshold(reference_mono, threshold)
        )
        rows.append(
            DifferenceInDifferences(
                base_id=base_id,
                cornea_id=cornea_id,
                platform_id=platform_id,
                pupil_mm=pupil_mm,
                threshold=threshold,
                value=(
                    special_edof.dof_by_threshold[threshold].width_d
                    - special_mono.dof_by_threshold[threshold].width_d
                    - reference_edof.dof_by_threshold[threshold].width_d
                    + reference_mono.dof_by_threshold[threshold].width_d
                ),
                bound_status=bound.status(),
                lower_bound=bound.lower if math.isfinite(bound.lower) else None,
                upper_bound=bound.upper if math.isfinite(bound.upper) else None,
                source_peak_censored=any(
                    metrics.peak_search_censored
                    for metrics in (special_mono, special_edof, reference_mono, reference_edof)
                ),
            )
        )
    return tuple(rows)


def common_threshold_metrics(
    rows: Sequence[SupplementalRow], reference: SupplementalMetrics
) -> SupplementalMetrics:
    return derive_config_metrics(rows, common_threshold=common_reference_threshold(reference))


def cycles_per_degree_to_cycles_mm(value_cpd: float, effective_focal_length_mm: float) -> float:
    result = cpd_to_cycles_mm([value_cpd], effective_focal_length_mm)
    return float(result[0])
