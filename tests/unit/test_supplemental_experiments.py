from __future__ import annotations

import math
from dataclasses import replace

import pytest

from whole_eye_mvp.supplemental_experiments import (
    BASE_IDS,
    CENTRAL_NEAR_CORNEA_ID,
    DISTANCE_COMPONENT_ANCHORED,
    OPTIC_STATES,
    PLATFORM_IDS,
    SUPPLEMENTAL_DEFOCUS_GRID,
    SupplementalConfig,
    SupplementalExperimentError,
    SupplementalRow,
    build_distance_component_anchored_plan,
    common_reference_threshold,
    common_threshold_metrics,
    cycles_per_degree_to_cycles_mm,
    derive_config_metrics,
    derive_difference_in_differences,
    find_supplemental_distance_peak,
    validate_distance_component_anchored_plan,
)


def _rows(config_id: str, scale: float = 1.0, *, broad: bool = False) -> tuple[SupplementalRow, ...]:
    rows: list[SupplementalRow] = []
    for defocus in SUPPLEMENTAL_DEFOCUS_GRID:
        exponent = 0.01 if broad else 2.0
        mtfa = scale * math.exp(-exponent * defocus * defocus)
        rows.append(
            SupplementalRow(
                config_id=config_id,
                pair_key=f"{config_id}_PAIR",
                base_id=BASE_IDS[0],
                cornea_id="N0",
                platform_id=PLATFORM_IDS[0],
                pupil_mm=3.0,
                optic_state="MONO",
                defocus_d=defocus,
                mtfa=mtfa,
                mtf30_cpd=scale * max(0.0, 1.0 - 0.1 * abs(defocus)),
            )
        )
    return tuple(rows)


def _carrier_keys() -> dict[tuple[str, str], str]:
    return {(base, platform): f"carrier-{base}-{platform}" for base in BASE_IDS for platform in PLATFORM_IDS}


@pytest.mark.unit
def test_supplemental_grid_is_exactly_49_points() -> None:
    assert len(SUPPLEMENTAL_DEFOCUS_GRID) == 49
    assert SUPPLEMENTAL_DEFOCUS_GRID[0] == 1.0
    assert SUPPLEMENTAL_DEFOCUS_GRID[-1] == -5.0
    assert SUPPLEMENTAL_DEFOCUS_GRID[8] == 0.0


@pytest.mark.unit
def test_grid_rejects_old_or_extended_sampling() -> None:
    with pytest.raises(SupplementalExperimentError, match="49 planes"):
        find_supplemental_distance_peak([0.5, 0.0, -0.5], [0.1, 1.0, 0.1])


@pytest.mark.unit
def test_peak_is_limited_to_plus_minus_one_d_and_marks_boundary() -> None:
    values = [2.0 if abs(defocus) == 1.0 else 0.1 for defocus in SUPPLEMENTAL_DEFOCUS_GRID]
    peak = find_supplemental_distance_peak(SUPPLEMENTAL_DEFOCUS_GRID, values)
    assert peak.defocus_d == 1.0
    assert peak.peak_search_censored


@pytest.mark.unit
def test_metrics_derive_three_relative_thresholds_and_30_cpd_curve() -> None:
    metrics = derive_config_metrics(_rows("config-1"))
    assert set(metrics.dof_by_threshold) == {0.3, 0.5, 0.7}
    assert metrics.peak_defocus_d == pytest.approx(0.0)
    assert metrics.mtfa_at_zero_d == pytest.approx(1.0)
    assert len(metrics.mtf30_cpd_curve) == 49
    assert metrics.tf_mtfa_mean > 0.0


@pytest.mark.unit
def test_common_threshold_uses_untreated_monofocal_peak() -> None:
    reference = derive_config_metrics(_rows("reference", scale=0.8))
    target = common_threshold_metrics(_rows("target", scale=0.5), reference)
    assert target.common_threshold_dof is not None
    assert common_reference_threshold(reference) == pytest.approx(0.4)
    assert target.common_threshold_dof.width_d >= 0.0


@pytest.mark.unit
def test_distance_anchored_plan_has_exact_24_configs() -> None:
    plan = build_distance_component_anchored_plan(_carrier_keys())
    assert len(plan) == 24
    assert {item.cornea_id for item in plan} == {CENTRAL_NEAR_CORNEA_ID}
    assert {item.calibration_strategy for item in plan} == {DISTANCE_COMPONENT_ANCHORED}
    validate_distance_component_anchored_plan(plan)


@pytest.mark.unit
def test_distance_anchored_pair_shares_frozen_carrier() -> None:
    plan = build_distance_component_anchored_plan(_carrier_keys())
    by_pair: dict[str, list[SupplementalConfig]] = {}
    for item in plan:
        by_pair.setdefault(item.pair_key, []).append(item)
    assert len(by_pair) == 12
    for members in by_pair.values():
        assert {item.optic_state for item in members} == set(OPTIC_STATES)
        assert len({item.carrier_key for item in members}) == 1


@pytest.mark.unit
def test_restoring_near_add_then_solving_is_rejected() -> None:
    plan = list(build_distance_component_anchored_plan(_carrier_keys()))
    plan[0] = replace(plan[0], post_restore_iol_power_solves=1)
    with pytest.raises(SupplementalExperimentError, match="no IOL solve"):
        validate_distance_component_anchored_plan(plan)


@pytest.mark.unit
def test_distance_strategy_rejects_non_central_cornea() -> None:
    plan = list(build_distance_component_anchored_plan(_carrier_keys()))
    plan[0] = replace(plan[0], cornea_id="A0")
    with pytest.raises(SupplementalExperimentError, match="limited to C0"):
        validate_distance_component_anchored_plan(plan)


@pytest.mark.unit
def test_difference_in_differences_is_exact_when_no_censoring() -> None:
    special_mono = derive_config_metrics(_rows("special-mono", scale=0.8))
    special_edof = derive_config_metrics(_rows("special-edof", scale=1.0))
    reference_mono = derive_config_metrics(_rows("reference-mono", scale=0.7))
    reference_edof = derive_config_metrics(_rows("reference-edof", scale=0.8))
    rows = derive_difference_in_differences(
        special_mono,
        special_edof,
        reference_mono,
        reference_edof,
        base_id=BASE_IDS[0],
        cornea_id="C0",
        platform_id="WFS",
        pupil_mm=3.0,
    )
    assert len(rows) == 3
    assert all(row.bound_status == "exact" for row in rows)


@pytest.mark.unit
def test_boundary_censoring_is_propagated_not_imputed() -> None:
    broad = derive_config_metrics(_rows("broad", broad=True))
    narrow = derive_config_metrics(_rows("narrow", scale=0.8))
    assert any(interval.far_censored or interval.near_censored for interval in broad.dof_by_threshold.values())
    rows = derive_difference_in_differences(
        broad,
        narrow,
        narrow,
        broad,
        base_id=BASE_IDS[0],
        cornea_id="C0",
        platform_id="WFS",
        pupil_mm=3.0,
    )
    assert any(row.bound_status != "exact" for row in rows)
    assert any(row.lower_bound is None or row.upper_bound is None for row in rows)


@pytest.mark.unit
def test_cpd_conversion_is_explicit_and_positive() -> None:
    assert cycles_per_degree_to_cycles_mm(30.0, 17.0) > 0.0
    with pytest.raises(ValueError):
        cycles_per_degree_to_cycles_mm(-1.0, 17.0)


@pytest.mark.unit
def test_config_rejects_unknown_factor() -> None:
    config = SupplementalConfig(
        config_id="x",
        pair_key="p",
        base_id=BASE_IDS[0],
        cornea_id="unknown",
        platform_id="WFS",
        pupil_mm=3.0,
        optic_state="MONO",
        carrier_key="carrier",
    )
    with pytest.raises(SupplementalExperimentError, match="unsupported cornea"):
        config.validate()
