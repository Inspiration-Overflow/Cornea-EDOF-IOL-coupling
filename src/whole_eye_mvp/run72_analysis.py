from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

TASK012_SOURCE_COMMIT = "f28b3032136aa28f54abb5fe5129765a125d3926"
TASK012_ANALYSIS_PLAN_ID = "TASK012_RUN72_ANALYSIS_PLAN_2026-08-19"
TASK012_ANALYSIS_PLAN = "docs/TASK_012_RUN72_ANALYSIS_PLAN_2026-08-19.md"
TASK012_SOURCE_HASHES = {
    "TASK_011_RUN72_EVIDENCE.json": (
        "d1b347cc221293fccd5a08679e8b6368788b22eecaa904f6b8f617a6296c50ee"
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
TASK011_CODE_COMMIT = "01f13b768cf1eca361703469b2fdce3d21f3376d"
TASK011_RUN_ID = "analysis-1cc1441dec4744a18d7ac73763507a6c"
TASK011_MANIFEST_HASH = "29205cf1bd27848bb378fad956709b7cde4686ffd917b10351a992fc0d59ad49"
TASK011_LOCK_SET_HASH = "b1dff4c05d2c817099c913c32d9eb8c0b1c9cfa3c9ca8a2022b20c6521e08923"
TASK011_ANALYSIS_SETTINGS_HASH = (
    "0cb7cd5d4c1551463d0a0913abd23b35f2a6bb4da8a2f76f689a4ce69386cebc"
)
TASK011_ACQUISITION_HASH = "f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d"
TASK011_PAIR_REFERENCE_HASH = (
    "a1cb8a899718d0327d8b1ecde21a4324e54090fd3db12cab36e649bb3cfc5b5d"
)
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
    **{name: field for name, field in SCALAR_FIELDS.items() if name != "delta_f_residual_d"},
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
        return {
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
        if coefficient == 0:
            return NumericBound(0.0, 0.0)
        if coefficient > 0:
            return NumericBound(coefficient * self.lower, coefficient * self.upper)
        return NumericBound(coefficient * self.upper, coefficient * self.lower)

    def add(self, other: NumericBound) -> NumericBound:
        return NumericBound(self.lower + other.lower, self.upper + other.upper)

    def status(self) -> str:
        lower_finite = math.isfinite(self.lower)
        upper_finite = math.isfinite(self.upper)
        if lower_finite and upper_finite:
            if abs(self.upper - self.lower) <= ABS_TOL:
                return "exact"
            return "bounded_interval"
        if lower_finite:
            return "lower_bound"
        if upper_finite:
            return "upper_bound"
        return "indeterminate"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source_hashes(evidence_dir: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    mismatches: dict[str, tuple[str, str]] = {}
    for filename, expected in TASK012_SOURCE_HASHES.items():
        path = evidence_dir / filename
        if not path.is_file():
            raise Task012Error(f"missing formal TASK-011 evidence file: {path}")
        actual = sha256_file(path)
        observed[filename] = actual
        if actual != expected:
            mismatches[filename] = (actual, expected)
    if mismatches:
        raise Task012Error(f"formal TASK-011 evidence hash mismatch: {mismatches}")
    return observed


def validate_evidence_metadata(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Task012Error("TASK-011 evidence JSON root must be an object")
    expected = {
        "schema_version": 1,
        "phase": "TASK-011-RUN72",
        "code_commit": TASK011_CODE_COMMIT,
        "baseline_id": "MVP_2026_v2",
        "manifest_hash": TASK011_MANIFEST_HASH,
        "lock_set_hash": TASK011_LOCK_SET_HASH,
        "analysis_settings_id": "NOMINAL_MAIN_FFT_MTF_555_v2",
        "analysis_settings_sha256": TASK011_ANALYSIS_SETTINGS_HASH,
        "acquisition_contract_id": "TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2",
        "acquisition_contract_sha256": TASK011_ACQUISITION_HASH,
        "frequency_scale_mode": "paired_residual_free_MONO_EFFL",
        "production_sampling": 128,
        "latest_run_id": TASK011_RUN_ID,
        "resume_mode": False,
        "selection_count": 72,
        "pair_reference_count": 36,
        "pair_reference_set_sha256": TASK011_PAIR_REFERENCE_HASH,
        "completed_config_count": 72,
        "failed_config_count": 0,
        "run72_started": True,
        "run72_complete": True,
        "acceptance_passed": True,
        "accepted_completed_configs": 72,
        "accepted_matched_pairs": 36,
        "accepted_through_focus_rows": 1080,
        "config_results_csv_sha256": TASK012_SOURCE_HASHES["TASK_011_RUN72_CONFIG_RESULTS.csv"],
        "through_focus_csv_sha256": TASK012_SOURCE_HASHES["TASK_011_RUN72_THROUGH_FOCUS.csv"],
        "paired_deltas_csv_sha256": TASK012_SOURCE_HASHES["TASK_011_RUN72_PAIRED_DELTAS.csv"],
    }
    mismatches = {
        key: (payload.get(key), value)
        for key, value in expected.items()
        if payload.get(key) != value
    }
    if mismatches:
        raise Task012Error(f"TASK-011 evidence metadata mismatch: {mismatches}")
    if payload.get("run_ids") != [TASK011_RUN_ID]:
        raise Task012Error("TASK-011 formal evidence must contain exactly the non-resume run ID")


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
    checks = (
        ({item.factors.base_id for item in configs}, set(BASE_IDS), "base_id"),
        ({item.factors.cornea_id for item in configs}, set(CORNEA_IDS), "cornea_id"),
        ({item.factors.platform_id for item in configs}, set(PLATFORM_IDS), "platform_id"),
        ({item.factors.pupil_mm for item in configs}, set(PUPIL_MM), "pupil_mm"),
        ({item.optic_state for item in configs}, set(OPTIC_STATES), "optic_state"),
    )
    for observed, expected, field in checks:
        if observed != expected:
            raise Task012Error(f"{field} set differs from frozen TASK-012 factors")


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
        config = ConfigSummary(
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
        if not config.run_id or not config.pair_key or not config.carrier_id:
            raise Task012Error(f"config identity fields must be non-empty: {config_id}")
        configs.append(config)
    _validate_factor_sets(configs)
    return tuple(configs)


def _trapezoid_mean(rows: Sequence[Mapping[str, str]]) -> float:
    points = sorted((_float(row, "defocus_retina_d"), _float(row, "mtfa")) for row in rows)
    area = 0.0
    for index in range(len(points) - 1):
        x0, y0 = points[index]
        x1, y1 = points[index + 1]
        area += (x1 - x0) * (y0 + y1) / 2.0
    width = points[-1][0] - points[0][0]
    if abs(width - 3.5) > ABS_TOL:
        raise Task012Error(f"through-focus integration width differs from 3.5 D: {width}")
    return area / width


def validate_through_focus(path: Path, configs: Sequence[ConfigSummary]) -> None:
    rows = _read_csv(path)
    if len(rows) != 1080:
        raise Task012Error(f"TASK-012 requires exactly 1080 through-focus rows, got {len(rows)}")
    by_config: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_config.setdefault(row.get("config_id", ""), []).append(row)
    config_map = {config.config_id: config for config in configs}
    if set(by_config) != set(config_map):
        raise Task012Error("through-focus config IDs differ from the config-summary IDs")
    for config_id, config_rows in by_config.items():
        if len(config_rows) != 15:
            raise Task012Error(f"through-focus rows/config must equal 15: {config_id}")
        grid = tuple(_float(row, "defocus_retina_d") for row in config_rows)
        if grid != EXPECTED_DEFOCUS_GRID:
            raise Task012Error(f"through-focus grid differs from frozen grid: {config_id}")
        config = config_map[config_id]
        expected_identity = (
            config.factors.base_id,
            config.factors.cornea_id,
            config.factors.platform_id,
            config.factors.pupil_mm,
            config.optic_state,
            config.pair_key,
        )
        for row in config_rows:
            observed_identity = (
                row.get("base_id", ""),
                row.get("cornea_id", ""),
                row.get("platform_id", ""),
                _float(row, "pupil_mm"),
                row.get("optic_state", ""),
                row.get("pair_key", ""),
            )
            if observed_identity != expected_identity:
                raise Task012Error(f"through-focus factor identity mismatch: {config_id}")
        zero_rows = [
            row for row in config_rows if abs(_float(row, "defocus_retina_d")) <= ABS_TOL
        ]
        if len(zero_rows) != 1:
            raise Task012Error(f"through-focus grid must contain one zero-D row: {config_id}")
        if abs(_float(zero_rows[0], "mtfa") - config.mtfa_at_zero_d) > ABS_TOL:
            raise Task012Error(f"mtfa_at_zero_d reconstruction failed: {config_id}")
        if abs(_trapezoid_mean(config_rows) - config.tf_mtfa_mean) > ABS_TOL:
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
    return {
        output: float(getattr(edof, field) - getattr(mono, field))
        for output, field in SCALAR_FIELDS.items()
    }


def build_pairs(configs: Sequence[ConfigSummary]) -> tuple[PairResult, ...]:
    grouped: dict[str, list[ConfigSummary]] = {}
    for config in configs:
        grouped.setdefault(config.pair_key, []).append(config)
    if len(grouped) != 36:
        raise Task012Error(f"TASK-012 requires exactly 36 pair keys, got {len(grouped)}")
    pairs: list[PairResult] = []
    factors_seen: set[FactorKey] = set()
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
        if mono.factors in factors_seen:
            raise Task012Error(f"duplicate Base×Cornea×Platform×Pupil pair: {mono.factors}")
        factors_seen.add(mono.factors)
        status = dof50_effect_status(mono, edof)
        pairs.append(
            PairResult(
                pair_key,
                mono.config_id,
                edof.config_id,
                mono.factors,
                _pair_delta(mono, edof),
                status,
                status != "exact",
                mono.dof50_censored,
                edof.dof50_censored,
                mono.peak_search_censored or edof.peak_search_censored,
                mono.peak_search_censored,
                edof.peak_search_censored,
            )
        )
    if len(factors_seen) != 36:
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
            raise Task012Error(f"duplicate or empty formal pair_key: {pair_key!r}")
        by_pair[pair_key] = row
    if set(by_pair) != {pair.pair_key for pair in pairs}:
        raise Task012Error("formal paired-delta pair keys differ from reconstructed pairs")
    for pair in pairs:
        row = by_pair[pair.pair_key]
        if row.get("mono_config_id") != pair.mono_config_id:
            raise Task012Error(f"formal paired MONO config mismatch: {pair.pair_key}")
        if row.get("edof_config_id") != pair.edof_config_id:
            raise Task012Error(f"formal paired EDOF config mismatch: {pair.pair_key}")
        for output, formal_column in FORMAL_DELTA_COLUMNS.items():
            if abs(_float(row, formal_column) - pair.values[output]) > ABS_TOL:
                raise Task012Error(f"paired delta reconstruction mismatch {pair.pair_key}:{output}")


def _pair_index(pairs: Sequence[PairResult]) -> dict[FactorKey, PairResult]:
    index = {pair.factors: pair for pair in pairs}
    if len(index) != 36:
        raise Task012Error("pair factor index is not unique")
    return index


def _contrast_bound(
    terms: Sequence[tuple[float, PairResult]], outcome: str
) -> tuple[str, float | str, float | str]:
    if outcome != "delta_dof50_width_d":
        return "not_applicable", "", ""
    result = NumericBound(0.0, 0.0)
    for coefficient, pair in terms:
        source = NumericBound.from_status(pair.values[outcome], pair.dof50_effect_status)
        result = result.add(source.scaled(coefficient))
    lower: float | str = result.lower if math.isfinite(result.lower) else ""
    upper: float | str = result.upper if math.isfinite(result.upper) else ""
    return result.status(), lower, upper


def _contrast_row(
    contrast_type: str,
    outcome: str,
    label: str,
    terms: Sequence[tuple[float, PairResult]],
    *,
    base_id: str = "",
    cornea_id: str = "",
    platform_id: str = "",
    pupil_mm: float | str = "",
) -> dict[str, object]:
    status, lower, upper = _contrast_bound(terms, outcome)
    return {
        "contrast_type": contrast_type,
        "outcome": outcome,
        "label": label,
        "base_id": base_id,
        "cornea_id": cornea_id,
        "platform_id": platform_id,
        "pupil_mm": pupil_mm,
        "value": sum(coef * pair.values[outcome] for coef, pair in terms),
        "bound_status": status,
        "lower_bound": lower,
        "upper_bound": upper,
        "source_pair_keys": json.dumps([pair.pair_key for _, pair in terms], separators=(",", ":")),
        "source_dof50_statuses": json.dumps(
            [pair.dof50_effect_status for _, pair in terms], separators=(",", ":")
        ),
        "source_peak_censored": any(pair.pair_peak_censored for _, pair in terms),
    }


def build_contrasts(pairs: Sequence[PairResult]) -> tuple[dict[str, object], ...]:
    index = _pair_index(pairs)
    rows: list[dict[str, object]] = []
    platform_pairs = (("WFS", "RAD"), ("WFS", "HOA"), ("RAD", "HOA"))
    cornea_pairs = (("B0", "A0"), ("C0", "A0"), ("B0", "C0"))
    for outcome in PAIR_OUTCOMES:
        for base in BASE_IDS:
            for cornea in CORNEA_IDS:
                for pupil in PUPIL_MM:
                    for left, right in platform_pairs:
                        terms = (
                            (1.0, index[FactorKey(base, cornea, left, pupil)]),
                            (-1.0, index[FactorKey(base, cornea, right, pupil)]),
                        )
                        rows.append(
                            _contrast_row(
                                "platform",
                                outcome,
                                f"{left}-{right}",
                                terms,
                                base_id=base,
                                cornea_id=cornea,
                                pupil_mm=pupil,
                            )
                        )
        for base in BASE_IDS:
            for platform in PLATFORM_IDS:
                for pupil in PUPIL_MM:
                    for left, right in cornea_pairs:
                        terms = (
                            (1.0, index[FactorKey(base, left, platform, pupil)]),
                            (-1.0, index[FactorKey(base, right, platform, pupil)]),
                        )
                        rows.append(
                            _contrast_row(
                                "cornea",
                                outcome,
                                f"{left}-{right}",
                                terms,
                                base_id=base,
                                platform_id=platform,
                                pupil_mm=pupil,
                            )
                        )
        for base in BASE_IDS:
            for pupil in PUPIL_MM:
                for cornea_left, cornea_right in cornea_pairs:
                    for platform_left, platform_right in platform_pairs:
                        terms = (
                            (1.0, index[FactorKey(base, cornea_left, platform_left, pupil)]),
                            (-1.0, index[FactorKey(base, cornea_right, platform_left, pupil)]),
                            (-1.0, index[FactorKey(base, cornea_left, platform_right, pupil)]),
                            (1.0, index[FactorKey(base, cornea_right, platform_right, pupil)]),
                        )
                        label = (
                            f"({cornea_left}-{cornea_right})_{platform_left}-"
                            f"({cornea_left}-{cornea_right})_{platform_right}"
                        )
                        rows.append(
                            _contrast_row(
                                "cornea_x_platform_did",
                                outcome,
                                label,
                                terms,
                                base_id=base,
                                pupil_mm=pupil,
                            )
                        )
        for base in BASE_IDS:
            for cornea in CORNEA_IDS:
                for platform in PLATFORM_IDS:
                    terms = (
                        (1.0, index[FactorKey(base, cornea, platform, 5.0)]),
                        (-1.0, index[FactorKey(base, cornea, platform, 3.0)]),
                    )
                    rows.append(
                        _contrast_row(
                            "pupil_sensitivity",
                            outcome,
                            "EPD5-EPD3",
                            terms,
                            base_id=base,
                            cornea_id=cornea,
                            platform_id=platform,
                        )
                    )
        for cornea in CORNEA_IDS:
            for platform in PLATFORM_IDS:
                for pupil in PUPIL_MM:
                    terms = (
                        (1.0, index[FactorKey("ATC_M3_AL24477", cornea, platform, pupil)]),
                        (-1.0, index[FactorKey("LB_AL2395", cornea, platform, pupil)]),
                    )
                    rows.append(
                        _contrast_row(
                            "base_sensitivity",
                            outcome,
                            "ATC-LB",
                            terms,
                            cornea_id=cornea,
                            platform_id=platform,
                            pupil_mm=pupil,
                        )
                    )
    return tuple(rows)


def _direction_count(values: Sequence[float]) -> str:
    positive = sum(value > ABS_TOL for value in values)
    negative = sum(value < -ABS_TOL for value in values)
    zero = len(values) - positive - negative
    return f"+{positive}/0{zero}/-{negative}"


def _mean_dof50_bound(cell: Sequence[PairResult]) -> NumericBound:
    result = NumericBound(0.0, 0.0)
    for pair in cell:
        source = NumericBound.from_status(
            pair.values["delta_dof50_width_d"], pair.dof50_effect_status
        )
        result = result.add(source.scaled(1.0 / len(cell)))
    return result


def build_coupling_matrix(pairs: Sequence[PairResult]) -> tuple[dict[str, object], ...]:
    index = _pair_index(pairs)
    rows: list[dict[str, object]] = []
    for cornea in CORNEA_IDS:
        for platform in PLATFORM_IDS:
            cell = tuple(
                index[FactorKey(base, cornea, platform, pupil)]
                for base in BASE_IDS
                for pupil in PUPIL_MM
            )
            dof_mean_bound = _mean_dof50_bound(cell)
            row: dict[str, object] = {
                "cornea_id": cornea,
                "platform_id": platform,
                "platform_label": PLATFORM_LABELS[platform],
                "stratum_count": 4,
                "strata": json.dumps(
                    [
                        {
                            "base_id": pair.factors.base_id,
                            "pupil_mm": pair.factors.pupil_mm,
                            "pupil_label": PUPIL_LABELS[pair.factors.pupil_mm],
                            "pair_key": pair.pair_key,
                        }
                        for pair in cell
                    ],
                    separators=(",", ":"),
                ),
                "dof50_effect_statuses": json.dumps(
                    [pair.dof50_effect_status for pair in cell], separators=(",", ":")
                ),
                "dof50_censored_count": sum(pair.pair_dof50_censored for pair in cell),
                "dof50_mean_bound_status": dof_mean_bound.status(),
                "dof50_mean_lower_bound": (
                    dof_mean_bound.lower if math.isfinite(dof_mean_bound.lower) else ""
                ),
                "dof50_mean_upper_bound": (
                    dof_mean_bound.upper if math.isfinite(dof_mean_bound.upper) else ""
                ),
                "peak_censored_count": sum(pair.pair_peak_censored for pair in cell),
            }
            for outcome in PAIR_OUTCOMES:
                values = tuple(pair.values[outcome] for pair in cell)
                row[f"{outcome}_values"] = json.dumps(values, separators=(",", ":"))
                row[f"{outcome}_direction"] = _direction_count(values)
                if outcome in PAIR_OUTCOMES[:4]:
                    row[f"{outcome}_mean"] = sum(values) / 4.0
                    row[f"{outcome}_min"] = min(values)
                    row[f"{outcome}_max"] = max(values)
            rows.append(row)
    return tuple(rows)


def analyze_evidence(evidence_dir: Path) -> Task012Analysis:
    source_hashes = verify_source_hashes(evidence_dir)
    validate_evidence_metadata(evidence_dir / "TASK_011_RUN72_EVIDENCE.json")
    configs = load_config_summaries(evidence_dir / "TASK_011_RUN72_CONFIG_RESULTS.csv")
    validate_through_focus(evidence_dir / "TASK_011_RUN72_THROUGH_FOCUS.csv", configs)
    pairs = build_pairs(configs)
    validate_formal_paired_deltas(evidence_dir / "TASK_011_RUN72_PAIRED_DELTAS.csv", pairs)
    return Task012Analysis(
        pairs=pairs,
        contrasts=build_contrasts(pairs),
        coupling_matrix=build_coupling_matrix(pairs),
        source_hashes=source_hashes,
    )