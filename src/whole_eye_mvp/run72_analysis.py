from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

TASK012_SOURCE_COMMIT = "f28b3032136aa28f54abb5fe5129765a125d3926"
TASK012_SOURCE_HASHES = {
    "TASK_011_RUN72_EVIDENCE.json": (
        "9044898ca71109269b1a35bd5f8701d682bad125e819c54afe50593341e0aa51"
    ),
    "TASK_011_RUN72_CONFIG_RESULTS.csv": (
        "337628d95529a3711f36e7ea250ef435413d8f6aff11c25739e3c9b9ccc69dfa"
    ),
    "TASK_011_RUN72_THROUGH_FOCUS.csv": (
        "cb4ece26a0a5d3a931db52a5f3b7e3325a99cbe26c9e175abd12bec5b7ec79da"
    ),
    "TASK_011_RUN72_PAIRED_DELTAS.csv": (
        "03dfe506566f83f6868c72890c042389ed8d0cd370255967fd1ff3b1ca25fa62"
    ),
}
TASK012_ANALYSIS_PLAN = "docs/TASK_012_RUN72_ANALYSIS_PLAN_2026-08-19.md"
ABS_TOL = 1e-12

BASE_IDS = ("LB_AL2395", "ATC_M3_AL24477")
CORNEA_IDS = ("A0", "B0", "C0")
PLATFORM_IDS = ("WFS", "RAD", "HOA")
PUPIL_MM = (3.0, 5.0)
OPTIC_STATES = ("MONO", "EDOF")
PLATFORM_LABELS = {"WFS": "WFS-like", "RAD": "RAD-like", "HOA": "HOA-like"}
PUPIL_LABELS = {3.0: "EPD3", 5.0: "EPD5"}

PAIR_OUTCOMES = (
    "delta_dof50_width_d",
    "delta_distance_peak_mtfa",
    "delta_mtfa_at_zero_d",
    "delta_tf_mtfa_mean",
    "delta_c40_um",
    "delta_c60_um",
    "delta_hoa_rms_um",
    "delta_f_residual_d",
)
SCALAR_FIELDS = {
    "delta_dof50_width_d": "dof50_width_d",
    "delta_distance_peak_mtfa": "distance_peak_mtfa",
    "delta_mtfa_at_zero_d": "mtfa_at_zero_d",
    "delta_tf_mtfa_mean": "tf_mtfa_mean",
    "delta_c40_um": "c40_um",
    "delta_c60_um": "c60_um",
    "delta_hoa_rms_um": "hoa_rms_um",
    "delta_f_residual_d": "distance_peak_retina_d",
}
FORMAL_DELTA_COLUMNS = {
    "delta_dof50_width_d": "dof50_width_d",
    "delta_distance_peak_mtfa": "distance_peak_mtfa",
    "delta_mtfa_at_zero_d": "mtfa_at_zero_d",
    "delta_tf_mtfa_mean": "tf_mtfa_mean",
    "delta_c40_um": "c40_um",
    "delta_c60_um": "c60_um",
    "delta_hoa_rms_um": "hoa_rms_um",
    "delta_f_residual_d": "delta_f_residual_d",
}

EXPECTED_DEFOCUS_GRID = tuple(round(0.50 - 0.25 * index, 10) for index in range(15))


class Task012Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FactorKey:
    base_id: str
    cornea_id: str
    platform_id: str
    pupil_mm: float


@dataclass(frozen=True, slots=True)
class ConfigSummary:
    run_id: str
    config_id: str
    pair_key: str
    carrier_id: str
    factors: FactorKey
    optic_state: str
    distance_peak_retina_d: float
    distance_peak_mtfa: float
    mtfa_at_zero_d: float
    dof50_width_d: float
    dof50_far_censored: bool
    dof50_near_censored: bool
    tf_mtfa_mean: float
    peak_search_censored: bool
    c40_um: float
    c60_um: float
    hoa_rms_um: float

    @property
    def dof50_censored(self) -> bool:
        return self.dof50_far_censored or self.dof50_near_censored


@dataclass(frozen=True, slots=True)
class PairResult:
    pair_key: str
    mono_config_id: str
    edof_config_id: str
    factors: FactorKey
    values: Mapping[str, float]
    dof50_effect_status: str
    pair_dof50_censored: bool
    mono_dof50_censored: bool
    edof_dof50_censored: bool
    pair_peak_censored: bool
    mono_peak_censored: bool
    edof_peak_censored: bool

    def to_row(self) -> dict[str, object]:
        row: dict[str, object] = {
            "pair_key": self.pair_key,
            "mono_config_id": self.mono_config_id,
            "edof_config_id": self.edof_config_id,
            "base_id": self.factors.base_id,
            "cornea_id": self.factors.cornea_id,
            "platform_id": self.factors.platform_id,
            "platform_label": PLATFORM_LABELS[self.factors.platform_id],
            "pupil_mm": self.factors.pupil_mm,
            "pupil_label": PUPIL_LABELS[self.factors.pupil_mm],
            **self.values,
            "dof50_effect_status": self.dof50_effect_status,
            "pair_dof50_censored": self.pair_dof50_censored,
            "mono_dof50_censored": self.mono_dof50_censored,
            "edof_dof50_censored": self.edof_dof50_censored,
            "pair_peak_censored": self.pair_peak_censored,
            "mono_peak_censored": self.mono_peak_censored,
            "edof_peak_censored": self.edof_peak_censored,
        }
        return row


@dataclass(frozen=True, slots=True)
class Task012Analysis:
    pairs: tuple[PairResult, ...]
    contrasts: tuple[dict[str, object], ...]
    coupling_matrix: tuple[dict[str, object], ...]
    source_hashes: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class NumericBound:
    lower: float
    upper: float

    @classmethod
    def from_status(cls, value: float, status: str) -> NumericBound:
        if status == "exact":
            return cls(value, value)
        if status == "lower_bound":
            return cls(value, math.inf)
        if status == "upper_bound":
            return cls(-math.inf, value)
        if status == "indeterminate":
            return cls(-math.inf, math.inf)
        raise Task012Error(f"unknown bound status: {status}")

    def scaled(self, coefficient: float) -> NumericBound:
        if coefficient >= 0:
            return NumericBound(coefficient * self.lower, coefficient * self.upper)
        return NumericBound(coefficient * self.upper, coefficient * self.lower)

    def add(self, other: NumericBound) -> NumericBound:
        return NumericBound(self.lower + other.lower, self.upper + other.upper)

    def status(self) -> str:
        if math.isfinite(self.lower) and math.isfinite(self.upper):
            return "exact" if abs(self.upper - self.lower) <= ABS_TOL else "bounded_interval"
        if math.isfinite(self.lower) and math.isinf(self.upper):
            return "lower_bound"
        if math.isinf(self.lower) and math.isfinite(self.upper):
            return "upper_bound"
        return "indeterminate"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source_hashes(evidence_dir: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for filename, expected in TASK012_SOURCE_HASHES.items():
        path = evidence_dir / filename
        if not path.is_file():
            raise Task012Error(f"missing formal TASK-011 evidence file: {path}")
        actual = sha256_file(path)
        observed[filename] = actual
        if actual != expected:
            raise Task012Error(
                f"formal TASK-011 evidence hash mismatch for {filename}: {actual} != {expected}"
            )
    return observed


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _strict_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise Task012Error(f"expected canonical boolean True/False, got {value!r}")


def _float(row: Mapping[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise Task012Error(f"invalid numeric field {field}") from exc
    if not math.isfinite(value):
        raise Task012Error(f"non-finite numeric field {field}")
    return value


def _validate_factor_sets(configs: Sequence[ConfigSummary]) -> None:
    if {config.factors.base_id for config in configs} != set(BASE_IDS):
        raise Task012Error("base_id set differs from frozen TASK-012 factors")
    if {config.factors.cornea_id for config in configs} != set(CORNEA_IDS):
        raise Task012Error("cornea_id set differs from frozen TASK-012 factors")
    if {config.factors.platform_id for config in configs} != set(PLATFORM_IDS):
        raise Task012Error("platform_id set differs from frozen TASK-012 factors")
    if {config.factors.pupil_mm for config in configs} != set(PUPIL_MM):
        raise Task012Error("pupil_mm set differs from frozen TASK-012 factors")
    if {config.optic_state for config in configs} != set(OPTIC_STATES):
        raise Task012Error("optic_state set differs from frozen TASK-012 factors")


def load_config_summaries(path: Path) -> tuple[ConfigSummary, ...]:
    rows = _read_csv(path)
    if len(rows) != 72:
        raise Task012Error(f"TASK-012 requires exactly 72 config rows, got {len(rows)}")
    configs: list[ConfigSummary] = []
    seen: set[str] = set()
    for row in rows:
        config_id = row.get("config_id", "")
        if not config_id or config_id in seen:
            raise Task012Error(f"duplicate or empty config_id: {config_id!r}")
        seen.add(config_id)
        factors = FactorKey(
            base_id=row.get("base_id", ""),
            cornea_id=row.get("cornea_id", ""),
            platform_id=row.get("platform_id", ""),
            pupil_mm=_float(row, "pupil_mm"),
        )
        optic_state = row.get("optic_state", "")
        configs.append(
            ConfigSummary(
                run_id=row.get("run_id", ""),
                config_id=config_id,
                pair_key=row.get("pair_key", ""),
                carrier_id=row.get("carrier_id", ""),
                factors=factors,
                optic_state=optic_state,
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
    if any(not config.run_id or not config.pair_key or not config.carrier_id for config in configs):
        raise Task012Error("config identity fields must be non-empty")
    _validate_factor_sets(configs)
    return tuple(configs)


def _trapezoid_mean(rows: Sequence[Mapping[str, str]]) -> float:
    points = sorted((_float(row, "defocus_retina_d"), _float(row, "mtfa")) for row in rows)
    area = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=True):
        area += (x1 - x0) * (y0 + y1) / 2.0
    width = points[-1][0] - points[0][0]
    if abs(width - 3.5) > ABS_TOL:
        raise Task012Error(f"through-focus integration width differs from 3.5 D: {width}")
    return area / width


def validate_through_focus(
    path: Path,
    configs: Sequence[ConfigSummary],
) -> None:
    rows = _read_csv(path)
    if len(rows) != 1080:
        raise Task012Error(f"TASK-012 requires exactly 1080 through-focus rows, got {len(rows)}")
    by_config: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_config.setdefault(row.get("config_id", ""), []).append(row)
    expected_ids = {config.config_id for config in configs}
    if set(by_config) != expected_ids:
        raise Task012Error("through-focus config IDs differ from the 72 config-summary IDs")
    config_map = {config.config_id: config for config in configs}
    for config_id, config_rows in by_config.items():
        if len(config_rows) != 15:
            raise Task012Error(f"through-focus rows/config must equal 15: {config_id}")
        grid = tuple(_float(row, "defocus_retina_d") for row in config_rows)
        if grid != EXPECTED_DEFOCUS_GRID:
            raise Task012Error(f"through-focus grid differs from frozen grid: {config_id}")
        config = config_map[config_id]
        for row in config_rows:
            factor_values = (
                row.get("base_id", ""),
                row.get("cornea_id", ""),
                row.get("platform_id", ""),
                _float(row, "pupil_mm"),
                row.get("optic_state", ""),
                row.get("pair_key", ""),
            )
            expected = (
                config.factors.base_id,
                config.factors.cornea_id,
                config.factors.platform_id,
                config.factors.pupil_mm,
                config.optic_state,
                config.pair_key,
            )
            if factor_values != expected:
                raise Task012Error(f"through-focus factor identity mismatch: {config_id}")
        zero = [row for row in config_rows if abs(_float(row, "defocus_retina_d")) <= ABS_TOL]
        if len(zero) != 1:
            raise Task012Error(f"through-focus grid must contain one zero-D row: {config_id}")
        if abs(_float(zero[0], "mtfa") - config.mtfa_at_zero_d) > ABS_TOL:
            raise Task012Error(f"mtfa_at_zero_d reconstruction failed: {config_id}")
        tf_mean = _trapezoid_mean(config_rows)
        if abs(tf_mean - config.tf_mtfa_mean) > ABS_TOL:
            raise Task012Error(f"tf_mtfa_mean reconstruction failed: {config_id}")


def dof50_effect_status(mono: ConfigSummary, edof: ConfigSummary) -> str:
    if not mono.dof50_censored and not edof.dof50_censored:
        return "exact"
    if not mono.dof50_censored and edof.dof50_censored:
        return "lower_bound"
    if mono.dof50_censored and not edof.dof50_censored:
        return "upper_bound"
    return "indeterminate"


def _pair_delta(mono: ConfigSummary, edof: ConfigSummary) -> dict[str, float]:
    values: dict[str, float] = {}
    for output_name, field_name in SCALAR_FIELDS.items():
        values[output_name] = float(getattr(edof, field_name) - getattr(mono, field_name))
    return values


def build_pairs(configs: Sequence[ConfigSummary]) -> tuple[PairResult, ...]:
    grouped: dict[str, list[ConfigSummary]] = {}
    for config in configs:
        grouped.setdefault(config.pair_key, []).append(config)
    if len(grouped) != 36:
        raise Task012Error(f"TASK-012 requires exactly 36 pair keys, got {len(grouped)}")
    pairs: list[PairResult] = []
    seen_factors: set[FactorKey] = set()
    for pair_key in sorted(grouped):
        members = grouped[pair_key]
        if len(members) != 2:
            raise Task012Error(f"pair must contain exactly two configs: {pair_key}")
        states = {member.optic_state: member for member in members}
        if set(states) != set(OPTIC_STATES):
            raise Task012Error(f"pair must contain exactly one MONO and one EDOF: {pair_key}")
        mono = states["MONO"]
        edof = states["EDOF"]
        if mono.factors != edof.factors:
            raise Task012Error(f"MONO/EDOF explicit factor columns differ: {pair_key}")
        if mono.factors in seen_factors:
            raise Task012Error(f"duplicate Base×Cornea×Platform×Pupil pair: {mono.factors}")
        seen_factors.add(mono.factors)
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
    if len(seen_factors) != 36:
        raise Task012Error("factorial pair coverage is not exact 2×3×3×2")
    return tuple(pairs)


def validate_formal_paired_deltas(path: Path, pairs: Sequence[PairResult]) -> None:
    rows = _read_csv(path)
    if len(rows) != 36:
        raise Task012Error(f"formal paired-delta CSV must contain 36 rows, got {len(rows)}")
    by_pair: dict[str, Mapping[str, str]] = {}
    for row in rows:
        pair_key = row.get("pair_key", "")
        if not pair_key or pair_key in by_pair:
            raise Task012Error(f"duplicate or empty pair_key in formal paired CSV: {pair_key!r}")
        by_pair[pair_key] = row
    if set(by_pair) != {pair.pair_key for pair in pairs}:
        raise Task012Error("formal paired-delta pair keys differ from reconstructed pairs")
    for pair in pairs:
        row = by_pair[pair.pair_key]
        if row.get("mono_config_id") != pair.mono_config_id:
            raise Task012Error(f"formal paired MONO config mismatch: {pair.pair_key}")
        if row.get("edof_config_id") != pair.edof_config_id:
            raise Task012Error(f"formal paired EDOF config mismatch: {pair.pair_key}")
        for output_name, formal_name in FORMAL_DELTA_COLUMNS.items():
            observed = _float(row, formal_name)
            expected = pair.values[output_name]
            if abs(observed - expected) > ABS_TOL:
                raise Task012Error(
                    f"paired delta reconstruction mismatch {pair.pair_key}:{output_name}"
                )


def _pair_index(pairs: Sequence[PairResult]) -> dict[FactorKey, PairResult]:
    index = {pair.factors: pair for pair in pairs}
    if len(index) != 36:
        raise Task012Error("pair factor index is not unique")
    return index


def _contrast_bound(
    terms: Sequence[tuple[float, PairResult]],
    outcome: str,
) -> tuple[str, float | None, float | None]:
    if outcome != "delta_dof50_width_d":
        return "exact", None, None
    bound = NumericBound(0.0, 0.0)
    for coefficient, pair in terms:
        source = NumericBound.from_status(
            pair.values[outcome],
            pair.dof50_effect_status,
        )
        bound = bound.add(source.scaled(coefficient))
    lower = bound.lower if math.isfinite(bound.lower) else None
    upper = bound.upper if math.isfinite(bound.upper) else None
    return bound.status(), lower, upper


def _contrast_row(
    *,
    contrast_type: str,
    outcome: str,
    label: str,
    terms: Sequence[tuple[float, PairResult]],
    base_id: str = "",
    cornea_id: str = "",
    platform_id: str = "",
    pupil_mm: float | str = "",
) -> dict[str, object]:
    value = sum(coefficient * pair.values[outcome] for coefficient, pair in terms)
    status, lower, upper = _contrast_bound(terms, outcome)
    return {
        "contrast_type": contrast_type,
        "outcome": outcome,
        "label": label,
        "base_id": base_id,
        "cornea_id": cornea_id,
        "platform_id": platform_id,
        "pupil_mm": pupil_mm,
        "value": value,
        "bound_status": status,
        "lower_bound": lower if lower is not None else "",
        "upper_bound": upper if upper is not None else "",
        "source_pair_keys": json.dumps(
            [pair.pair_key for _, pair in terms], separators=(",", ":")
        ),
        "source_dof50_statuses": json.dumps(
            [pair.dof50_effect_status for _, pair in terms], separators=(",", ":")
        ),
        "source_peak_censored": any(pair.pair_peak_censored for _, pair in terms),
    }


def build_contrasts(pairs: Sequence[PairResult]) -> tuple[dict[str, object], ...]:
    index = _pair_index(pairs)
    rows: list[dict[str, object]] = []
    platform_contrasts = (("WFS", "RAD"), ("WFS", "HOA"), ("RAD", "HOA"))
    cornea_contrasts = (("B0", "A0"), ("C0", "A0"), ("B0", "C0"))

    for outcome in PAIR_OUTCOMES:
        for base_id in BASE_IDS:
            for cornea_id in CORNEA_IDS:
                for pupil_mm in PUPIL_MM:
                    for left, right in platform_contrasts:
                        terms = (
                            (1.0, index[FactorKey(base_id, cornea_id, left, pupil_mm)]),
                            (-1.0, index[FactorKey(base_id, cornea_id, right, pupil_mm)]),
                        )
                        rows.append(
                            _contrast_row(
                                contrast_type="platform",
                                outcome=outcome,
                                label=f"{left}-{right}",
                                terms=terms,
                                base_id=base_id,
                                cornea_id=cornea_id,
                                pupil_mm=pupil_mm,
                            )
                        )
        for base_id in BASE_IDS:
            for platform_id in PLATFORM_IDS:
                for pupil_mm in PUPIL_MM:
                    for left, right in cornea_contrasts:
                        terms = (
                            (1.0, index[FactorKey(base_id, left, platform_id, pupil_mm)]),
                            (-1.0, index[FactorKey(base_id, right, platform_id, pupil_mm)]),
                        )
                        rows.append(
                            _contrast_row(
                                contrast_type="cornea",
                                outcome=outcome,
                                label=f"{left}-{right}",
                                terms=terms,
                                base_id=base_id,
                                platform_id=platform_id,
                                pupil_mm=pupil_mm,
                            )
                        )
        for base_id in BASE_IDS:
            for pupil_mm in PUPIL_MM:
                for cornea_left, cornea_right in cornea_contrasts:
                    for platform_left, platform_right in platform_contrasts:
                        terms = (
                            (
                                1.0,
                                index[
                                    FactorKey(
                                        base_id,
                                        cornea_left,
                                        platform_left,
                                        pupil_mm,
                                    )
                                ],
                            ),
                            (
                                -1.0,
                                index[
                                    FactorKey(
                                        base_id,
                                        cornea_right,
                                        platform_left,
                                        pupil_mm,
                                    )
                                ],
                            ),
                            (
                                -1.0,
                                index[
                                    FactorKey(
                                        base_id,
                                        cornea_left,
                                        platform_right,
                                        pupil_mm,
                                    )
                                ],
                            ),
                            (
                                1.0,
                                index[
                                    FactorKey(
                                        base_id,
                                        cornea_right,
                                        platform_right,
                                        pupil_mm,
                                    )
                                ],
                            ),
                        )
                        rows.append(
                            _contrast_row(
                                contrast_type="cornea_x_platform_did",
                                outcome=outcome,
                                label=(
                                    f"({cornea_left}-{cornea_right})_"
                                    f"{platform_left}-({cornea_left}-{cornea_right})_"
                                    f"{platform_right}"
                                ),
                                terms=terms,
                                base_id=base_id,
                                pupil_mm=pupil_mm,
                            )
                        )
        for base_id in BASE_IDS:
            for cornea_id in CORNEA_IDS:
                for platform_id in PLATFORM_IDS:
                    terms = (
                        (1.0, index[FactorKey(base_id, cornea_id, platform_id, 5.0)]),
                        (-1.0, index[FactorKey(base_id, cornea_id, platform_id, 3.0)]),
                    )
                    rows.append(
                        _contrast_row(
                            contrast_type="pupil_sensitivity",
                            outcome=outcome,
                            label="EPD5-EPD3",
                            terms=terms,
                            base_id=base_id,
                            cornea_id=cornea_id,
                            platform_id=platform_id,
                        )
                    )
        for cornea_id in CORNEA_IDS:
            for platform_id in PLATFORM_IDS:
                for pupil_mm in PUPIL_MM:
                    terms = (
                        (
                            1.0,
                            index[FactorKey("ATC_M3_AL24477", cornea_id, platform_id, pupil_mm)],
                        ),
                        (
                            -1.0,
                            index[FactorKey("LB_AL2395", cornea_id, platform_id, pupil_mm)],
                        ),
                    )
                    rows.append(
                        _contrast_row(
                            contrast_type="base_sensitivity",
                            outcome=outcome,
                            label="ATC-LB",
                            terms=terms,
                            cornea_id=cornea_id,
                            platform_id=platform_id,
                            pupil_mm=pupil_mm,
                        )
                    )
    return tuple(rows)


def _direction_count(values: Iterable[float]) -> str:
    numbers = tuple(values)
    positive = sum(value > 0 for value in numbers)
    zero = sum(abs(value) <= ABS_TOL for value in numbers)
    negative = len(numbers) - positive - zero
    return f"+{positive}/0{zero}/-{negative}"


def build_coupling_matrix(pairs: Sequence[PairResult]) -> tuple[dict[str, object], ...]:
    index = _pair_index(pairs)
    rows: list[dict[str, object]] = []
    for cornea_id in CORNEA_IDS:
        for platform_id in PLATFORM_IDS:
            cell_pairs = tuple(
                index[FactorKey(base_id, cornea_id, platform_id, pupil_mm)]
                for base_id in BASE_IDS
                for pupil_mm in PUPIL_MM
            )
            row: dict[str, object] = {
                "cornea_id": cornea_id,
                "platform_id": platform_id,
                "platform_label": PLATFORM_LABELS[platform_id],
                "stratum_count": 4,
                "strata": json.dumps(
                    [
                        {
                            "base_id": pair.factors.base_id,
                            "pupil_mm": pair.factors.pupil_mm,
                            "pupil_label": PUPIL_LABELS[pair.factors.pupil_mm],
                            "pair_key": pair.pair_key,
                        }
                        for pair in cell_pairs
                    ],
                    separators=(",", ":"),
                ),
                "dof50_effect_statuses": json.dumps(
                    [pair.dof50_effect_status for pair in cell_pairs], separators=(",", ":")
                ),
                "dof50_censored_count": sum(pair.pair_dof50_censored for pair in cell_pairs),
                "peak_censored_count": sum(pair.pair_peak_censored for pair in cell_pairs),
            }
            for outcome in PAIR_OUTCOMES[:4]:
                values = tuple(pair.values[outcome] for pair in cell_pairs)
                row[f"{outcome}_values"] = json.dumps(values, separators=(",", ":"))
                row[f"{outcome}_mean"] = sum(values) / len(values)
                row[f"{outcome}_min"] = min(values)
                row[f"{outcome}_max"] = max(values)
                row[f"{outcome}_direction"] = _direction_count(values)
            for outcome in PAIR_OUTCOMES[4:]:
                values = tuple(pair.values[outcome] for pair in cell_pairs)
                row[f"{outcome}_values"] = json.dumps(values, separators=(",", ":"))
                row[f"{outcome}_direction"] = _direction_count(values)
            rows.append(row)
    return tuple(rows)


def analyze_evidence(evidence_dir: Path) -> Task012Analysis:
    source_hashes = verify_source_hashes(evidence_dir)
    configs = load_config_summaries(evidence_dir / "TASK_011_RUN72_CONFIG_RESULTS.csv")
    validate_through_focus(evidence_dir / "TASK_011_RUN72_THROUGH_FOCUS.csv", configs)
    pairs = build_pairs(configs)
    validate_formal_paired_deltas(evidence_dir / "TASK_011_RUN72_PAIRED_DELTAS.csv", pairs)
    contrasts = build_contrasts(pairs)
    coupling_matrix = build_coupling_matrix(pairs)
    return Task012Analysis(pairs, contrasts, coupling_matrix, source_hashes)
