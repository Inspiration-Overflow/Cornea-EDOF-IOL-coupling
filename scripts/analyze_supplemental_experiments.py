"""Derive the prespecified supplemental tables from exported CSV data.

The script performs no optical acquisition.  It fails closed when metadata or the
49-point through-focus contract is not satisfied.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from whole_eye_mvp.supplemental_experiments import (
    BASE_IDS,
    CENTRAL_NEAR_CORNEA_ID,
    CORNEA_IDS,
    OPTIC_STATES,
    PLATFORM_IDS,
    PUPIL_MM,
    SupplementalConfig,
    SupplementalExperimentError,
    SupplementalRow,
    common_reference_threshold,
    common_threshold_metrics,
    derive_config_metrics,
    derive_difference_in_differences,
    validate_distance_component_anchored_plan,
)


def _field(row: dict[str, str], *names: str, default: str | None = None) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    if default is not None:
        return default
    raise SupplementalExperimentError(f"missing required field; accepted names: {names}")


def _float(row: dict[str, str], *names: str, default: float | None = None) -> float:
    value = _field(row, *names, default=None if default is None else str(default))
    try:
        number = float(value)
    except ValueError as exc:
        raise SupplementalExperimentError(f"invalid numeric field {names}: {value!r}") from exc
    if not math.isfinite(number):
        raise SupplementalExperimentError(f"non-finite numeric field {names}")
    return number


def _bool(row: dict[str, str], *names: str, default: bool = False) -> bool:
    value = _field(row, *names, default=str(default))
    if value in {"True", "true", "1"}:
        return True
    if value in {"False", "false", "0"}:
        return False
    raise SupplementalExperimentError(f"invalid boolean field {names}: {value!r}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SupplementalExperimentError(f"missing input CSV: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SupplementalExperimentError(f"input CSV is empty: {path}")
    return rows


def _load_configs(path: Path) -> tuple[SupplementalConfig, ...]:
    rows = _read_csv(path)
    configs: list[SupplementalConfig] = []
    seen: set[str] = set()
    for row in rows:
        config = SupplementalConfig(
            config_id=_field(row, "config_id"),
            pair_key=_field(row, "pair_key"),
            base_id=_field(row, "base_id"),
            cornea_id=_field(row, "cornea_id"),
            platform_id=_field(row, "platform_id"),
            pupil_mm=_float(row, "pupil_mm"),
            optic_state=_field(row, "optic_state"),
            calibration_strategy=_field(row, "calibration_strategy", default="full_eye"),
            carrier_key=_field(row, "carrier_key", "carrier_id"),
            near_add_d=_float(row, "near_add_d", "central_near_add_d", default=1.75),
            near_add_zeroed_for_solve=_bool(row, "near_add_zeroed_for_solve", default=False),
            carrier_frozen=_bool(row, "carrier_frozen", default=True),
            near_add_restored=_bool(row, "near_add_restored", default=True),
            post_restore_iol_power_solves=int(_float(row, "post_restore_iol_power_solves", default=0.0)),
            post_restore_refocus_count=int(_float(row, "post_restore_refocus_count", default=0.0)),
            post_restore_carrier_optimizations=int(
                _float(row, "post_restore_carrier_optimizations", default=0.0)
            ),
        )
        if config.config_id in seen:
            raise SupplementalExperimentError(f"duplicate config_id: {config.config_id}")
        seen.add(config.config_id)
        config.validate()
        configs.append(config)
    return tuple(configs)


def _load_through_focus(path: Path, configs: tuple[SupplementalConfig, ...]) -> dict[str, tuple[SupplementalRow, ...]]:
    config_map = {config.config_id: config for config in configs}
    grouped: dict[str, list[SupplementalRow]] = {config_id: [] for config_id in config_map}
    for row in _read_csv(path):
        config_id = _field(row, "config_id")
        config = config_map.get(config_id)
        if config is None:
            raise SupplementalExperimentError(f"through-focus row references unknown config: {config_id}")
        grouped[config_id].append(
            SupplementalRow(
                config_id=config_id,
                pair_key=_field(row, "pair_key", default=config.pair_key),
                base_id=_field(row, "base_id", default=config.base_id),
                cornea_id=_field(row, "cornea_id", default=config.cornea_id),
                platform_id=_field(row, "platform_id", default=config.platform_id),
                pupil_mm=_float(row, "pupil_mm", default=config.pupil_mm),
                optic_state=_field(row, "optic_state", default=config.optic_state),
                defocus_d=_float(row, "defocus_d", "defocus_retina_d"),
                mtfa=_float(row, "mtfa", "mtfa_0_60_cpd"),
                mtf30_cpd=_float(row, "mtf30_cpd", "mtf30", "mtfa30_cpd"),
            )
        )
    missing = [config_id for config_id, rows in grouped.items() if not rows]
    if missing:
        raise SupplementalExperimentError(f"missing through-focus rows for configs: {missing[:3]}")
    return {config_id: tuple(rows) for config_id, rows in grouped.items()}


def _validate_main_matrix(configs: tuple[SupplementalConfig, ...]) -> None:
    if len(configs) != 96:
        raise SupplementalExperimentError(f"main supplemental branch must contain 96 configs, got {len(configs)}")
    identities = {
        (config.base_id, config.cornea_id, config.platform_id, config.pupil_mm, config.optic_state)
        for config in configs
    }
    expected = {
        (base, cornea, platform, pupil, state)
        for base in BASE_IDS
        for cornea in CORNEA_IDS
        for platform in PLATFORM_IDS
        for pupil in PUPIL_MM
        for state in OPTIC_STATES
    }
    if identities != expected:
        raise SupplementalExperimentError("main coverage is not exact 2×4×3×2×2")
    if any(config.calibration_strategy != "full_eye" for config in configs):
        raise SupplementalExperimentError("the original 96 branch must use the full-eye calibration strategy")
    by_pair: dict[str, list[SupplementalConfig]] = {}
    for config in configs:
        by_pair.setdefault(config.pair_key, []).append(config)
    if len(by_pair) != 48 or any({item.optic_state for item in items} != set(OPTIC_STATES) for items in by_pair.values()):
        raise SupplementalExperimentError("main branch must contain 48 MONO/EDOF pairs")
    for items in by_pair.values():
        if len({item.carrier_key for item in items}) != 1:
            raise SupplementalExperimentError("matched main states must share one carrier key")


def _metrics_by_config(configs: tuple[SupplementalConfig, ...], rows: dict[str, tuple[SupplementalRow, ...]]):
    return {config.config_id: derive_config_metrics(rows[config.config_id]) for config in configs}


def _pair_rows(configs: tuple[SupplementalConfig, ...], metrics):
    grouped: dict[str, list[SupplementalConfig]] = {}
    for config in configs:
        grouped.setdefault(config.pair_key, []).append(config)
    output: list[dict[str, object]] = []
    for pair_key, members in sorted(grouped.items()):
        if len(members) != 2 or {item.optic_state for item in members} != set(OPTIC_STATES):
            raise SupplementalExperimentError(f"invalid matched pair: {pair_key}")
        mono = next(item for item in members if item.optic_state == "MONO")
        edof = next(item for item in members if item.optic_state == "EDOF")
        if mono.carrier_key != edof.carrier_key:
            raise SupplementalExperimentError(f"MONO/EDOF carrier mismatch: {pair_key}")
        mono_metrics = metrics[mono.config_id]
        edof_metrics = metrics[edof.config_id]
        record: dict[str, object] = {
            "pair_key": pair_key,
            "base_id": mono.base_id,
            "cornea_id": mono.cornea_id,
            "platform_id": mono.platform_id,
            "pupil_mm": mono.pupil_mm,
            "carrier_key": mono.carrier_key,
            "mono_config_id": mono.config_id,
            "edof_config_id": edof.config_id,
            "mono_peak_search_censored": mono_metrics.peak_search_censored,
            "edof_peak_search_censored": edof_metrics.peak_search_censored,
            "delta_mtfa_at_zero_d": edof_metrics.mtfa_at_zero_d - mono_metrics.mtfa_at_zero_d,
            "delta_peak_mtfa": edof_metrics.peak_mtfa - mono_metrics.peak_mtfa,
            "delta_tf_mtfa_mean": edof_metrics.tf_mtfa_mean - mono_metrics.tf_mtfa_mean,
            "mono_tf_mtfa_mean_original_window": mono_metrics.tf_mtfa_mean_original_window,
            "edof_tf_mtfa_mean_original_window": edof_metrics.tf_mtfa_mean_original_window,
            "delta_tf_mtfa_mean_original_window": (
                edof_metrics.tf_mtfa_mean_original_window
                - mono_metrics.tf_mtfa_mean_original_window
            ),
        }
        for fraction in (0.30, 0.50, 0.70):
            mono_dof = mono_metrics.dof_by_threshold[fraction]
            edof_dof = edof_metrics.dof_by_threshold[fraction]
            record[f"mono_dof{int(fraction * 100)}_d"] = mono_dof.width_d
            record[f"edof_dof{int(fraction * 100)}_d"] = edof_dof.width_d
            record[f"mono_dof{int(fraction * 100)}_far_censored"] = mono_dof.far_censored
            record[f"mono_dof{int(fraction * 100)}_near_censored"] = mono_dof.near_censored
            record[f"edof_dof{int(fraction * 100)}_far_censored"] = edof_dof.far_censored
            record[f"edof_dof{int(fraction * 100)}_near_censored"] = edof_dof.near_censored
            record[f"delta_dof{int(fraction * 100)}_d"] = edof_dof.width_d - mono_dof.width_d
        return_record = record
        output.append(return_record)
    return output


def _common_threshold_rows(configs, rows, metrics):
    index = {(config.base_id, config.platform_id, config.pupil_mm): config for config in configs if config.cornea_id == "N0" and config.optic_state == "MONO"}
    output: list[dict[str, object]] = []
    for config in configs:
        reference = index[(config.base_id, config.platform_id, config.pupil_mm)]
        derived = common_threshold_metrics(rows[config.config_id], metrics[reference.config_id])
        interval = derived.common_threshold_dof
        assert interval is not None
        output.append(
            {
                "config_id": config.config_id,
                "pair_key": config.pair_key,
                "base_id": config.base_id,
                "cornea_id": config.cornea_id,
                "platform_id": config.platform_id,
                "pupil_mm": config.pupil_mm,
                "optic_state": config.optic_state,
                "reference_config_id": reference.config_id,
                "common_threshold": common_reference_threshold(metrics[reference.config_id]),
                "common_dof50_width_d": interval.width_d,
                "common_dof50_far_censored": interval.far_censored,
                "common_dof50_near_censored": interval.near_censored,
            }
        )
    return output


def _curve_rows(rows: dict[str, tuple[SupplementalRow, ...]]):
    output: list[dict[str, object]] = []
    for config_rows in rows.values():
        for row in sorted(config_rows, key=lambda item: item.defocus_d, reverse=True):
            output.append(
                {
                    "config_id": row.config_id,
                    "pair_key": row.pair_key,
                    "base_id": row.base_id,
                    "cornea_id": row.cornea_id,
                    "platform_id": row.platform_id,
                    "pupil_mm": row.pupil_mm,
                    "optic_state": row.optic_state,
                    "defocus_d": row.defocus_d,
                    "mtf30_cpd": row.mtf30_cpd,
                }
            )
    return output


def _did_rows(configs, metrics):
    index = {(config.base_id, config.cornea_id, config.platform_id, config.pupil_mm, config.optic_state): config for config in configs}
    output: list[dict[str, object]] = []
    for base in BASE_IDS:
        for platform in PLATFORM_IDS:
            for pupil in PUPIL_MM:
                reference_mono = index[(base, "N0", platform, pupil, "MONO")]
                reference_edof = index[(base, "N0", platform, pupil, "EDOF")]
                for cornea in ("A0", "B0", "C0"):
                    special_mono = index[(base, cornea, platform, pupil, "MONO")]
                    special_edof = index[(base, cornea, platform, pupil, "EDOF")]
                    for row in derive_difference_in_differences(
                        metrics[special_mono.config_id],
                        metrics[special_edof.config_id],
                        metrics[reference_mono.config_id],
                        metrics[reference_edof.config_id],
                        base_id=base,
                        cornea_id=cornea,
                        platform_id=platform,
                        pupil_mm=pupil,
                    ):
                        output.append({
                            "base_id": row.base_id,
                            "cornea_id": row.cornea_id,
                            "platform_id": row.platform_id,
                            "pupil_mm": row.pupil_mm,
                            "threshold": row.threshold,
                            "delta_delta_dof_d": row.value,
                            "bound_status": row.bound_status,
                            "lower_bound": row.lower_bound if row.lower_bound is not None else "",
                            "upper_bound": row.upper_bound if row.upper_bound is not None else "",
                            "source_peak_censored": row.source_peak_censored,
                        })
    return output


def _local_subrange_max(rows: tuple[SupplementalRow, ...]) -> float:
    values = [
        row.mtfa
        for row in rows
        if -2.25 - 1.0e-9 <= row.defocus_d <= -1.25 + 1.0e-9
    ]
    if not values:
        raise SupplementalExperimentError(
            "the -1.25 to -2.25 D local-shape interval is missing"
        )
    return max(values)


def _strategy_metrics(
    record: dict[str, object],
    *,
    prefix: str,
    config: SupplementalConfig,
    rows: dict[str, tuple[SupplementalRow, ...]],
    metrics,
) -> None:
    derived = metrics[config.config_id]
    record[f"{prefix}_config_id"] = config.config_id
    record[f"{prefix}_carrier_key"] = config.carrier_key
    record[f"{prefix}_peak_defocus_d"] = derived.peak_defocus_d
    record[f"{prefix}_peak_mtfa"] = derived.peak_mtfa
    record[f"{prefix}_peak_search_censored"] = derived.peak_search_censored
    record[f"{prefix}_mtfa_at_zero_d"] = derived.mtfa_at_zero_d
    record[f"{prefix}_tf_mtfa_mean"] = derived.tf_mtfa_mean
    record[f"{prefix}_tf_mtfa_mean_original_window"] = derived.tf_mtfa_mean_original_window
    local_max = _local_subrange_max(rows[config.config_id])
    record[f"{prefix}_near_range_max_mtfa"] = local_max
    record[f"{prefix}_near_range_to_peak_ratio"] = (
        local_max / derived.peak_mtfa if derived.peak_mtfa > 0.0 else ""
    )
    for fraction in (0.30, 0.50, 0.70):
        interval = derived.dof_by_threshold[fraction]
        label = int(fraction * 100)
        record[f"{prefix}_dof{label}_d"] = interval.width_d
        record[f"{prefix}_dof{label}_far_censored"] = interval.far_censored
        record[f"{prefix}_dof{label}_near_censored"] = interval.near_censored


def _calibration_strategy_rows(
    main_configs: tuple[SupplementalConfig, ...],
    main_rows: dict[str, tuple[SupplementalRow, ...]],
    main_metrics,
    distance_configs: tuple[SupplementalConfig, ...],
    distance_rows: dict[str, tuple[SupplementalRow, ...]],
    distance_metrics,
) -> list[dict[str, object]]:
    main_index = {
        (config.base_id, config.platform_id, config.pupil_mm, config.optic_state): config
        for config in main_configs
        if config.cornea_id == "C0"
    }
    distance_index = {
        (config.base_id, config.platform_id, config.pupil_mm, config.optic_state): config
        for config in distance_configs
    }
    expected = {
        (base, platform, pupil, state)
        for base in BASE_IDS
        for platform in PLATFORM_IDS
        for pupil in PUPIL_MM
        for state in OPTIC_STATES
    }
    if set(main_index) != expected or set(distance_index) != expected:
        raise SupplementalExperimentError(
            "C0 calibration strategy comparison does not cover the exact 24 configurations"
        )
    output: list[dict[str, object]] = []
    for base in BASE_IDS:
        for platform in PLATFORM_IDS:
            for pupil in PUPIL_MM:
                record: dict[str, object] = {
                    "base_id": base,
                    "cornea_id": CENTRAL_NEAR_CORNEA_ID,
                    "platform_id": platform,
                    "pupil_mm": pupil,
                    "full_eye_pair_key": main_index[(base, platform, pupil, "MONO")].pair_key,
                    "distance_component_anchored_pair_key": distance_index[
                        (base, platform, pupil, "MONO")
                    ].pair_key,
                }
                for state in OPTIC_STATES:
                    _strategy_metrics(
                        record,
                        prefix=f"full_eye_{state.lower()}",
                        config=main_index[(base, platform, pupil, state)],
                        rows=main_rows,
                        metrics=main_metrics,
                    )
                    _strategy_metrics(
                        record,
                        prefix=f"distance_component_anchored_{state.lower()}",
                        config=distance_index[(base, platform, pupil, state)],
                        rows=distance_rows,
                        metrics=distance_metrics,
                    )
                for strategy in ("full_eye", "distance_component_anchored"):
                    mono = f"{strategy}_mono"
                    edof = f"{strategy}_edof"
                    record[f"{strategy}_delta_mtfa_at_zero_d"] = (
                        record[f"{edof}_mtfa_at_zero_d"]
                        - record[f"{mono}_mtfa_at_zero_d"]
                    )
                    record[f"{strategy}_delta_peak_mtfa"] = (
                        record[f"{edof}_peak_mtfa"] - record[f"{mono}_peak_mtfa"]
                    )
                    record[f"{strategy}_delta_peak_defocus_d"] = (
                        record[f"{edof}_peak_defocus_d"]
                        - record[f"{mono}_peak_defocus_d"]
                    )
                    record[f"{strategy}_delta_tf_mtfa_mean_original_window"] = (
                        record[f"{edof}_tf_mtfa_mean_original_window"]
                        - record[f"{mono}_tf_mtfa_mean_original_window"]
                    )
                    for label in (30, 50, 70):
                        record[f"{strategy}_delta_dof{label}_d"] = (
                            record[f"{edof}_dof{label}_d"]
                            - record[f"{mono}_dof{label}_d"]
                        )
                for label in (30, 50, 70):
                    record[f"delta_delta_dof{label}_d_distance_minus_full_eye"] = (
                        record[f"distance_component_anchored_delta_dof{label}_d"]
                        - record[f"full_eye_delta_dof{label}_d"]
                    )
                output.append(record)
    return output


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise SupplementalExperimentError(f"refusing to write empty output: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-csv", type=Path, required=True)
    parser.add_argument("--through-focus-csv", type=Path, required=True)
    parser.add_argument("--distance-config-csv", type=Path)
    parser.add_argument("--distance-through-focus-csv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    configs = _load_configs(args.config_csv.resolve())
    _validate_main_matrix(configs)
    rows = _load_through_focus(args.through_focus_csv.resolve(), configs)
    metrics = _metrics_by_config(configs, rows)
    output_dir = args.output_dir.resolve()
    _write_csv(output_dir / "SUPPLEMENTAL_PAIR_ANALYSIS.csv", _pair_rows(configs, metrics))
    _write_csv(output_dir / "SUPPLEMENTAL_COMMON_THRESHOLD.csv", _common_threshold_rows(configs, rows, metrics))
    _write_csv(output_dir / "SUPPLEMENTAL_30CPD_THROUGH_FOCUS.csv", _curve_rows(rows))
    _write_csv(output_dir / "SUPPLEMENTAL_DID.csv", _did_rows(configs, metrics))

    if (args.distance_config_csv is None) != (args.distance_through_focus_csv is None):
        raise SupplementalExperimentError("distance config and through-focus CSVs must be supplied together")
    if args.distance_config_csv is not None:
        distance_configs = _load_configs(args.distance_config_csv.resolve())
        validate_distance_component_anchored_plan(distance_configs)
        distance_rows = _load_through_focus(args.distance_through_focus_csv.resolve(), distance_configs)
        distance_metrics = _metrics_by_config(distance_configs, distance_rows)
        _write_csv(output_dir / "SUPPLEMENTAL_DISTANCE_PAIR_ANALYSIS.csv", _pair_rows(distance_configs, distance_metrics))
        _write_csv(output_dir / "SUPPLEMENTAL_DISTANCE_30CPD_THROUGH_FOCUS.csv", _curve_rows(distance_rows))
        _write_csv(
            output_dir / "SUPPLEMENTAL_CALIBRATION_STRATEGY_COMPARISON.csv",
            _calibration_strategy_rows(
                configs,
                rows,
                metrics,
                distance_configs,
                distance_rows,
                distance_metrics,
            ),
        )


if __name__ == "__main__":
    try:
        main()
    except SupplementalExperimentError as exc:
        raise SystemExit(f"supplemental experiment contract error: {exc}") from exc
