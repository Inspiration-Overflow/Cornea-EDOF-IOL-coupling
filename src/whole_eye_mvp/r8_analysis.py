"""Offline integration of the R8 96-config production export."""

from __future__ import annotations

import csv
import itertools
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

from .run72_analysis import (
    ABS_TOL,
    EXPECTED_DEFOCUS_GRID,
    FORMAL_DELTA_COLUMNS,
    PAIR_OUTCOMES,
    PLATFORM_LABELS,
    PUPIL_LABELS,
    SCALAR_FIELDS,
    ConfigSummary,
    FactorKey,
    NumericBound,
    PairResult,
    dof50_effect_status,
)

R8_BASE_IDS = ("LB_AL2395", "ATC_M3_AL24477")
R8_CORNEA_IDS = ("N0", "A0", "B0", "C0")
R8_POSTOP_CORNEA_IDS = ("A0", "B0", "C0")
R8_PLATFORM_IDS = ("WFS", "RAD", "HOA")
R8_PUPIL_MM = (3.0, 5.0)
R8_OPTIC_STATES = ("MONO", "EDOF")


class R8AnalysisError(RuntimeError):
    """R8 export violates the declared factorial or reconstruction contract."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(row: Mapping[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise R8AnalysisError(f"invalid numeric field {field}") from exc
    if not math.isfinite(value):
        raise R8AnalysisError(f"non-finite numeric field {field}")
    return value


def _strict_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise R8AnalysisError(f"expected canonical boolean, got {value!r}")


def load_configs(path: Path) -> tuple[ConfigSummary, ...]:
    rows = _read_csv(path)
    if len(rows) != 96:
        raise R8AnalysisError(f"expected 96 config rows, got {len(rows)}")
    configs: list[ConfigSummary] = []
    seen: set[str] = set()
    for row in rows:
        config_id = row.get("config_id", "")
        if not config_id or config_id in seen:
            raise R8AnalysisError(f"duplicate or empty config_id: {config_id!r}")
        seen.add(config_id)
        configs.append(
            ConfigSummary(
                run_id=row.get("run_id", ""),
                config_id=config_id,
                pair_key=row.get("pair_key", ""),
                carrier_id=row.get("carrier_id", ""),
                factors=FactorKey(
                    row.get("base_id", ""),
                    row.get("cornea_id", ""),
                    row.get("platform_id", ""),
                    _float(row, "pupil_mm"),
                ),
                optic_state=row.get("optic_state", ""),
                distance_peak_retina_d=_float(row, "distance_peak_retina_d"),
                distance_peak_mtfa=_float(row, "distance_peak_mtfa"),
                mtfa_at_zero_d=_float(row, "mtfa_at_zero_d"),
                dof50_width_d=_float(row, "dof50_width_d"),
                dof50_far_censored=_strict_bool(row.get("dof50_far_censored", "")),
                dof50_near_censored=_strict_bool(row.get("dof50_near_censored", "")),
                tf_mtfa_mean=_float(row, "tf_mtfa_mean"),
                peak_search_censored=_strict_bool(row.get("peak_search_censored", "")),
                c40_um=_float(row, "c40_um"),
                c60_um=_float(row, "c60_um"),
                hoa_rms_um=_float(row, "hoa_rms_um"),
            )
        )
    return tuple(configs)


def validate_factorial(configs: Sequence[ConfigSummary]) -> None:
    expected = {
        FactorKey(base, cornea, platform, pupil)
        for base in R8_BASE_IDS
        for cornea in R8_CORNEA_IDS
        for platform in R8_PLATFORM_IDS
        for pupil in R8_PUPIL_MM
    }
    observed = {config.factors for config in configs}
    if observed != expected:
        raise R8AnalysisError("R8 factor coverage is not exact 2×4×3×2")
    identities = {(config.factors, config.optic_state) for config in configs}
    if len(identities) != 96 or {config.optic_state for config in configs} != set(R8_OPTIC_STATES):
        raise R8AnalysisError("R8 optic-state factorial identity is not exact")


def _trapezoid_mean(rows: Sequence[Mapping[str, str]]) -> float:
    points = sorted((_float(row, "defocus_retina_d"), _float(row, "mtfa")) for row in rows)
    area = sum(
        (x1 - x0) * (y0 + y1) / 2.0
        for (x0, y0), (x1, y1) in itertools.pairwise(points)
    )
    width = points[-1][0] - points[0][0]
    if abs(width - 3.5) > ABS_TOL:
        raise R8AnalysisError(f"through-focus width differs from 3.5 D: {width}")
    return area / width


def validate_through_focus(path: Path, configs: Sequence[ConfigSummary]) -> None:
    rows = _read_csv(path)
    if len(rows) != 1440:
        raise R8AnalysisError(f"expected 1440 through-focus rows, got {len(rows)}")
    by_config: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_config.setdefault(row.get("config_id", ""), []).append(row)
    config_map = {config.config_id: config for config in configs}
    if set(by_config) != set(config_map):
        raise R8AnalysisError("through-focus config IDs differ from config results")
    for config_id, config_rows in by_config.items():
        if len(config_rows) != 15:
            raise R8AnalysisError(f"through-focus rows/config must equal 15: {config_id}")
        grid = tuple(_float(row, "defocus_retina_d") for row in config_rows)
        if grid != EXPECTED_DEFOCUS_GRID:
            raise R8AnalysisError(f"through-focus grid drift: {config_id}")
        zero = [row for row in config_rows if abs(_float(row, "defocus_retina_d")) <= ABS_TOL]
        if len(zero) != 1 or abs(_float(zero[0], "mtfa") - config_map[config_id].mtfa_at_zero_d) > ABS_TOL:
            raise R8AnalysisError(f"0-D reconstruction failed: {config_id}")
        if abs(_trapezoid_mean(config_rows) - config_map[config_id].tf_mtfa_mean) > ABS_TOL:
            raise R8AnalysisError(f"TF-mean reconstruction failed: {config_id}")


def _pair_delta(mono: ConfigSummary, edof: ConfigSummary) -> dict[str, float]:
    return {
        output: float(getattr(edof, field) - getattr(mono, field))
        for output, field in SCALAR_FIELDS.items()
    }


def build_pairs(configs: Sequence[ConfigSummary]) -> tuple[PairResult, ...]:
    grouped: dict[str, list[ConfigSummary]] = {}
    for config in configs:
        grouped.setdefault(config.pair_key, []).append(config)
    if len(grouped) != 48:
        raise R8AnalysisError(f"expected 48 pair keys, got {len(grouped)}")
    pairs: list[PairResult] = []
    factors_seen: set[FactorKey] = set()
    for pair_key in sorted(grouped):
        members = grouped[pair_key]
        states = {member.optic_state: member for member in members}
        if len(members) != 2 or set(states) != set(R8_OPTIC_STATES):
            raise R8AnalysisError(f"pair must contain MONO+EDOF exactly once: {pair_key}")
        mono, edof = states["MONO"], states["EDOF"]
        if mono.factors != edof.factors or mono.factors in factors_seen:
            raise R8AnalysisError(f"pair factor identity mismatch: {pair_key}")
        factors_seen.add(mono.factors)
        status = dof50_effect_status(mono, edof)
        pairs.append(
            PairResult(
                pair_key=pair_key,
                mono_config_id=mono.config_id,
                edof_config_id=edof.config_id,
                factors=mono.factors,
                values=_pair_delta(mono, edof),
                dof50_effect_status=status,
                pair_dof50_censored=status != "exact",
                mono_dof50_censored=mono.dof50_censored,
                edof_dof50_censored=edof.dof50_censored,
                pair_peak_censored=mono.peak_search_censored or edof.peak_search_censored,
                mono_peak_censored=mono.peak_search_censored,
                edof_peak_censored=edof.peak_search_censored,
            )
        )
    if len(factors_seen) != 48:
        raise R8AnalysisError("R8 pair factor coverage is not exact")
    return tuple(pairs)


def validate_paired_deltas(path: Path, pairs: Sequence[PairResult]) -> None:
    rows = _read_csv(path)
    if len(rows) != 48:
        raise R8AnalysisError(f"expected 48 paired rows, got {len(rows)}")
    by_pair = {row.get("pair_key", ""): row for row in rows}
    if len(by_pair) != 48:
        raise R8AnalysisError("paired keys are not unique")
    for pair in pairs:
        row = by_pair.get(pair.pair_key)
        if row is None or row.get("mono_config_id") != pair.mono_config_id or row.get("edof_config_id") != pair.edof_config_id:
            raise R8AnalysisError(f"paired identity mismatch: {pair.pair_key}")
        for output, formal_column in FORMAL_DELTA_COLUMNS.items():
            if abs(_float(row, formal_column) - pair.values[output]) > ABS_TOL:
                raise R8AnalysisError(f"paired delta mismatch: {pair.pair_key}:{output}")


def build_n0_interactions(pairs: Sequence[PairResult]) -> tuple[dict[str, object], ...]:
    index = {pair.factors: pair for pair in pairs}
    rows: list[dict[str, object]] = []
    for base in R8_BASE_IDS:
        for cornea in R8_POSTOP_CORNEA_IDS:
            for platform in R8_PLATFORM_IDS:
                for pupil in R8_PUPIL_MM:
                    postop = index[FactorKey(base, cornea, platform, pupil)]
                    n0 = index[FactorKey(base, "N0", platform, pupil)]
                    for outcome in PAIR_OUTCOMES:
                        status = "exact"
                        lower: float | str = ""
                        upper: float | str = ""
                        if outcome == "delta_dof50_width_d":
                            bound = NumericBound.from_status(
                                postop.values[outcome], postop.dof50_effect_status
                            ).add(
                                NumericBound.from_status(
                                    n0.values[outcome], n0.dof50_effect_status
                                ).scaled(-1.0)
                            )
                            status = bound.status()
                            lower = bound.lower if math.isfinite(bound.lower) else ""
                            upper = bound.upper if math.isfinite(bound.upper) else ""
                        rows.append(
                            {
                                "contrast_type": "postop_minus_N0_edof_effect",
                                "outcome": outcome,
                                "base_id": base,
                                "cornea_id": cornea,
                                "platform_id": platform,
                                "platform_label": PLATFORM_LABELS[platform],
                                "pupil_mm": pupil,
                                "pupil_label": PUPIL_LABELS[pupil],
                                "value": postop.values[outcome] - n0.values[outcome],
                                "bound_status": status,
                                "lower_bound": lower,
                                "upper_bound": upper,
                                "postop_pair_key": postop.pair_key,
                                "n0_pair_key": n0.pair_key,
                                "postop_dof50_status": postop.dof50_effect_status,
                                "n0_dof50_status": n0.dof50_effect_status,
                                "source_peak_censored": postop.pair_peak_censored or n0.pair_peak_censored,
                            }
                        )
    if len(rows) != 288:
        raise R8AnalysisError(f"expected 288 N0 interactions, got {len(rows)}")
    return tuple(rows)


def build_coupling_matrix(pairs: Sequence[PairResult]) -> tuple[dict[str, object], ...]:
    index = {pair.factors: pair for pair in pairs}
    rows: list[dict[str, object]] = []
    for cornea in R8_CORNEA_IDS:
        for platform in R8_PLATFORM_IDS:
            cell = tuple(
                index[FactorKey(base, cornea, platform, pupil)]
                for base in R8_BASE_IDS
                for pupil in R8_PUPIL_MM
            )
            bound = NumericBound(0.0, 0.0)
            for pair in cell:
                source = NumericBound.from_status(
                    pair.values["delta_dof50_width_d"], pair.dof50_effect_status
                )
                bound = bound.add(source.scaled(0.25))
            row: dict[str, object] = {
                "cornea_id": cornea,
                "platform_id": platform,
                "platform_label": PLATFORM_LABELS[platform],
                "stratum_count": 4,
                "dof50_censored_count": sum(pair.pair_dof50_censored for pair in cell),
                "dof50_mean_bound_status": bound.status(),
                "dof50_mean_lower_bound": bound.lower if math.isfinite(bound.lower) else "",
                "dof50_mean_upper_bound": bound.upper if math.isfinite(bound.upper) else "",
                "peak_censored_count": sum(pair.pair_peak_censored for pair in cell),
            }
            for outcome in PAIR_OUTCOMES:
                values = tuple(pair.values[outcome] for pair in cell)
                positive = sum(value > ABS_TOL for value in values)
                negative = sum(value < -ABS_TOL for value in values)
                row[f"{outcome}_direction"] = f"+{positive}/0{4-positive-negative}/-{negative}"
                if outcome in PAIR_OUTCOMES[:4]:
                    row[f"{outcome}_mean"] = sum(values) / 4.0
                    row[f"{outcome}_min"] = min(values)
                    row[f"{outcome}_max"] = max(values)
            rows.append(row)
    return tuple(rows)
