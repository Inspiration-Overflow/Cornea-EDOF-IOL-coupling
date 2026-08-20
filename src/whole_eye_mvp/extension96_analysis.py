from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from whole_eye_mvp.run72_analysis import (
    ABS_TOL,
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

TASK015_ID = "TASK-015-EXTENSION96-OFFLINE-INTEGRATION"
BASE_IDS = ("LB_AL2395", "ATC_M3_AL24477")
CORNEA_IDS = ("N0", "A0V12", "B0V12", "C0V12")
POSTOP_CORNEA_IDS = ("A0V12", "B0V12", "C0V12")
PLATFORM_IDS = ("WFS", "RAD", "HOA")
PUPIL_MM = (3.0, 5.0)
OPTIC_STATES = ("MONO", "EDOF")
EXPECTED_DEFOCUS_GRID = tuple(round(0.50 - 0.25 * index, 10) for index in range(15))

TASK013_EVIDENCE_COMMIT = "38ad14a12a18b1a7a30d259cde644d360442f57b"
TASK014_EVIDENCE_COMMIT = "6ffb2eaf88e386729aa3965c0f12c9b7ca134081"

SOURCE_FILES = {
    "task013": {
        "config": ("TASK_013_NATIVE_REFERENCE_CONFIG_RESULTS.csv", "fd3c578e40f695de7db2ff4b220c282fe7d6b51f"),
        "through_focus": ("TASK_013_NATIVE_REFERENCE_THROUGH_FOCUS.csv", "43bab42103b3b2d5609898438569c9d66b9546ce"),
        "paired": ("TASK_013_NATIVE_REFERENCE_PAIRED_DELTAS.csv", "2ce3220f7ac24b3a91447607ea06c9a602eb5849"),
        "evidence": ("TASK_013_NATIVE_REFERENCE_EVIDENCE.json", "c567809f371ee567fd53e8003558e23040e8e1d5"),
        "review": ("TASK_013_SCIENTIFIC_REVIEW.json", "27933c505614f5e1fb0d0510b660f90b3ceb8e9b"),
    },
    "task014": {
        "config": ("TASK_014_CONFIG_RESULTS.csv", "fa3bdfe834a15702d00a6e86d09ffaf708b05873"),
        "through_focus": ("TASK_014_THROUGH_FOCUS.csv", "e0121414803d948ea0fd1e072b9b7f7389e371b7"),
        "paired": ("TASK_014_PAIRED_DELTAS.csv", "595a546dba61a557ea53edf20e4a4c771ba702dc"),
        "evidence": ("TASK_014_EVIDENCE.json", "0e3b4595f9c9c03ce55d45bbe10bef356d542455"),
        "review": ("TASK_014_SCIENTIFIC_REVIEW.json", "96c5354c95d15d52e012488697af343bbd29b125"),
    },
}


class Task015Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Task015Analysis:
    pairs: tuple[PairResult, ...]
    n0_interactions: tuple[dict[str, object], ...]
    coupling_matrix: tuple[dict[str, object], ...]
    source_blob_sha1: Mapping[str, str]
    source_run_ids: Mapping[str, str]


def git_blob_sha1(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _strict_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise Task015Error(f"expected canonical boolean True/False, got {value!r}")


def _float(row: Mapping[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise Task015Error(f"invalid numeric field {field}") from exc
    if not math.isfinite(value):
        raise Task015Error(f"non-finite numeric field {field}")
    return value


def verify_source_blobs(task013_dir: Path, task014_dir: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for task_name, directory in (("task013", task013_dir), ("task014", task014_dir)):
        for role, (filename, expected) in SOURCE_FILES[task_name].items():
            path = directory / filename
            if not path.is_file():
                raise Task015Error(f"missing accepted source file: {path}")
            actual = git_blob_sha1(path)
            observed[f"{task_name}/{filename}"] = actual
            if actual != expected:
                raise Task015Error(
                    f"accepted source Git blob mismatch for {task_name}:{role}: {actual} != {expected}"
                )
    return observed


def _validate_review(path: Path, *, expected_task: str) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if expected_task == "task013":
        verdict = payload.get("verdict", {}).get("scientific_acceptance")
        rerun = payload.get("requires_opticstudio_rerun")
        run_id = payload.get("formal_run_id")
        if verdict != "PASS_WITH_SCIENTIFIC_CAVEATS" or rerun is not False:
            raise Task015Error("TASK-013 scientific review is not accepted/frozen")
        if run_id != "task013-183dcffcd1da4f1cb1a219d9eedb39db":
            raise Task015Error("TASK-013 formal run identity drift")
    else:
        verdict = payload.get("scientific_acceptance")
        rerun = payload.get("requires_opticstudio_rerun")
        run_id = payload.get("source_run_id")
        if verdict != "PASS_WITH_SCIENTIFIC_CAVEATS" or rerun is not False:
            raise Task015Error("TASK-014 scientific review is not accepted/frozen")
        if run_id != "task014-e270a185207543149c21da83202c4b73":
            raise Task015Error("TASK-014 formal run identity drift")


def _validate_evidence(path: Path, *, expected_task: str) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if expected_task == "task013":
        expected = {
            "phase": "TASK-013-NATIVE-CORNEA-REFERENCE",
            "run_id": "task013-183dcffcd1da4f1cb1a219d9eedb39db",
            "completed_configs": 24,
            "failed_configs": 0,
            "through_focus_rows": 360,
            "matched_pairs": 12,
            "model_archive_complete": True,
        }
    else:
        expected = {
            "phase": "TASK-014-VERTEX-CORRECTED-POSTOP-CORNEA",
            "run_id": "task014-e270a185207543149c21da83202c4b73",
            "completed_configs": 72,
            "failed_configs": 0,
            "through_focus_rows": 1080,
            "matched_pairs": 36,
            "model_archive_complete": True,
        }
    mismatches = {
        key: (payload.get(key), value)
        for key, value in expected.items()
        if payload.get(key) != value
    }
    if mismatches:
        raise Task015Error(f"{expected_task} evidence metadata mismatch: {mismatches}")
    if payload.get("analysis_settings_id") != "NOMINAL_MAIN_FFT_MTF_555_v2":
        raise Task015Error(f"{expected_task} analysis-settings drift")
    if payload.get("acquisition_contract_id") != "TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2":
        raise Task015Error(f"{expected_task} acquisition-contract drift")
    if payload.get("frequency_scale_mode") != "paired_residual_free_MONO_EFFL":
        raise Task015Error(f"{expected_task} frequency-scale drift")
    if payload.get("production_sampling") != 128:
        raise Task015Error(f"{expected_task} production-sampling drift")
    return str(payload["run_id"])


def _load_configs(path: Path, expected_rows: int) -> tuple[ConfigSummary, ...]:
    rows = _read_csv(path)
    if len(rows) != expected_rows:
        raise Task015Error(f"config row count mismatch for {path.name}: {len(rows)}")
    configs: list[ConfigSummary] = []
    seen: set[str] = set()
    for row in rows:
        config_id = row.get("config_id", "")
        if not config_id or config_id in seen:
            raise Task015Error(f"duplicate or empty config_id: {config_id!r}")
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


def _validate_factorial(configs: Sequence[ConfigSummary]) -> None:
    expected = {
        FactorKey(base, cornea, platform, pupil)
        for base in BASE_IDS
        for cornea in CORNEA_IDS
        for platform in PLATFORM_IDS
        for pupil in PUPIL_MM
    }
    observed = {config.factors for config in configs}
    if observed != expected:
        raise Task015Error("96-config factor coverage is not exact 2×4×3×2")
    identities = {(config.factors, config.optic_state) for config in configs}
    if len(identities) != 96:
        raise Task015Error("duplicate Base×Cornea×Platform×Pupil×State identity")
    if {config.optic_state for config in configs} != set(OPTIC_STATES):
        raise Task015Error("optic-state set drift")


def _trapezoid_mean(rows: Sequence[Mapping[str, str]]) -> float:
    points = sorted((_float(row, "defocus_retina_d"), _float(row, "mtfa")) for row in rows)
    area = 0.0
    for index in range(len(points) - 1):
        x0, y0 = points[index]
        x1, y1 = points[index + 1]
        area += (x1 - x0) * (y0 + y1) / 2.0
    width = points[-1][0] - points[0][0]
    if abs(width - 3.5) > ABS_TOL:
        raise Task015Error(f"through-focus integration width differs from 3.5 D: {width}")
    return area / width


def _validate_through_focus(
    path: Path,
    configs: Sequence[ConfigSummary],
    expected_rows: int,
) -> None:
    rows = _read_csv(path)
    if len(rows) != expected_rows:
        raise Task015Error(f"through-focus row count mismatch for {path.name}: {len(rows)}")
    by_config: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_config.setdefault(row.get("config_id", ""), []).append(row)
    config_map = {config.config_id: config for config in configs}
    if set(by_config) != set(config_map):
        raise Task015Error("through-focus config IDs differ from config results")
    for config_id, config_rows in by_config.items():
        if len(config_rows) != 15:
            raise Task015Error(f"through-focus rows/config must equal 15: {config_id}")
        grid = tuple(_float(row, "defocus_retina_d") for row in config_rows)
        if grid != EXPECTED_DEFOCUS_GRID:
            raise Task015Error(f"through-focus grid drift: {config_id}")
        config = config_map[config_id]
        zero = [
            row
            for row in config_rows
            if abs(_float(row, "defocus_retina_d")) <= ABS_TOL
        ]
        if len(zero) != 1 or abs(_float(zero[0], "mtfa") - config.mtfa_at_zero_d) > ABS_TOL:
            raise Task015Error(f"0-D MTFa reconstruction failed: {config_id}")
        if abs(_trapezoid_mean(config_rows) - config.tf_mtfa_mean) > ABS_TOL:
            raise Task015Error(f"TF-mean reconstruction failed: {config_id}")


def _pair_delta(mono: ConfigSummary, edof: ConfigSummary) -> dict[str, float]:
    return {
        output: float(getattr(edof, field) - getattr(mono, field))
        for output, field in SCALAR_FIELDS.items()
    }


def _build_pairs(configs: Sequence[ConfigSummary]) -> tuple[PairResult, ...]:
    grouped: dict[str, list[ConfigSummary]] = {}
    for config in configs:
        grouped.setdefault(config.pair_key, []).append(config)
    if len(grouped) != 48:
        raise Task015Error(f"expected 48 pair keys, got {len(grouped)}")
    pairs: list[PairResult] = []
    factors_seen: set[FactorKey] = set()
    for pair_key in sorted(grouped):
        members = grouped[pair_key]
        states = {member.optic_state: member for member in members}
        if len(members) != 2 or set(states) != set(OPTIC_STATES):
            raise Task015Error(f"pair must contain MONO+EDOF exactly once: {pair_key}")
        mono, edof = states["MONO"], states["EDOF"]
        if mono.factors != edof.factors:
            raise Task015Error(f"MONO/EDOF factor mismatch: {pair_key}")
        if mono.factors in factors_seen:
            raise Task015Error(f"duplicate pair factors: {mono.factors}")
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
        raise Task015Error("factorial pair coverage is not exact 2×4×3×2")
    return tuple(pairs)


def _validate_formal_paired(
    path: Path,
    pairs: Sequence[PairResult],
    expected_rows: int,
) -> None:
    rows = _read_csv(path)
    if len(rows) != expected_rows:
        raise Task015Error(f"formal paired row count mismatch for {path.name}: {len(rows)}")
    by_pair = {row.get("pair_key", ""): row for row in rows}
    relevant = [pair for pair in pairs if pair.pair_key in by_pair]
    if len(relevant) != expected_rows or len(by_pair) != expected_rows:
        raise Task015Error(f"formal paired keys mismatch for {path.name}")
    for pair in relevant:
        row = by_pair[pair.pair_key]
        if row.get("mono_config_id") != pair.mono_config_id:
            raise Task015Error(f"formal MONO identity mismatch: {pair.pair_key}")
        if row.get("edof_config_id") != pair.edof_config_id:
            raise Task015Error(f"formal EDOF identity mismatch: {pair.pair_key}")
        for output, formal_column in FORMAL_DELTA_COLUMNS.items():
            if abs(_float(row, formal_column) - pair.values[output]) > ABS_TOL:
                raise Task015Error(f"formal paired delta mismatch: {pair.pair_key}:{output}")


def _pair_index(pairs: Sequence[PairResult]) -> dict[FactorKey, PairResult]:
    index = {pair.factors: pair for pair in pairs}
    if len(index) != 48:
        raise Task015Error("pair factor index is not unique")
    return index


def _difference_bound(
    left: PairResult,
    right: PairResult,
    outcome: str,
) -> tuple[str, float | str, float | str]:
    if outcome != "delta_dof50_width_d":
        return "not_applicable", "", ""
    lhs = NumericBound.from_status(left.values[outcome], left.dof50_effect_status)
    rhs = NumericBound.from_status(right.values[outcome], right.dof50_effect_status)
    result = lhs.add(rhs.scaled(-1.0))
    lower: float | str = result.lower if math.isfinite(result.lower) else ""
    upper: float | str = result.upper if math.isfinite(result.upper) else ""
    return result.status(), lower, upper


def build_n0_interactions(pairs: Sequence[PairResult]) -> tuple[dict[str, object], ...]:
    index = _pair_index(pairs)
    rows: list[dict[str, object]] = []
    for base in BASE_IDS:
        for cornea in POSTOP_CORNEA_IDS:
            for platform in PLATFORM_IDS:
                for pupil in PUPIL_MM:
                    postop = index[FactorKey(base, cornea, platform, pupil)]
                    n0 = index[FactorKey(base, "N0", platform, pupil)]
                    for outcome in PAIR_OUTCOMES:
                        status, lower, upper = _difference_bound(postop, n0, outcome)
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
                                "source_peak_censored": (
                                    postop.pair_peak_censored or n0.pair_peak_censored
                                ),
                            }
                        )
    if len(rows) != 288:
        raise Task015Error(f"N0-referenced interaction count mismatch: {len(rows)}")
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
            pair.values["delta_dof50_width_d"],
            pair.dof50_effect_status,
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
            bound = _mean_dof50_bound(cell)
            row: dict[str, object] = {
                "cornea_id": cornea,
                "platform_id": platform,
                "platform_label": PLATFORM_LABELS[platform],
                "stratum_count": 4,
                "dof50_censored_count": sum(pair.pair_dof50_censored for pair in cell),
                "dof50_mean_bound_status": bound.status(),
                "dof50_mean_lower_bound": (
                    bound.lower if math.isfinite(bound.lower) else ""
                ),
                "dof50_mean_upper_bound": (
                    bound.upper if math.isfinite(bound.upper) else ""
                ),
                "peak_censored_count": sum(pair.pair_peak_censored for pair in cell),
            }
            for outcome in PAIR_OUTCOMES:
                values = tuple(pair.values[outcome] for pair in cell)
                row[f"{outcome}_direction"] = _direction_count(values)
                if outcome in PAIR_OUTCOMES[:4]:
                    row[f"{outcome}_mean"] = sum(values) / 4.0
                    row[f"{outcome}_min"] = min(values)
                    row[f"{outcome}_max"] = max(values)
            rows.append(row)
    return tuple(rows)


def analyze_extension96(task013_dir: Path, task014_dir: Path) -> Task015Analysis:
    source_blobs = verify_source_blobs(task013_dir, task014_dir)
    _validate_review(
        task013_dir / SOURCE_FILES["task013"]["review"][0],
        expected_task="task013",
    )
    _validate_review(
        task014_dir / SOURCE_FILES["task014"]["review"][0],
        expected_task="task014",
    )
    run_ids = {
        "task013": _validate_evidence(
            task013_dir / SOURCE_FILES["task013"]["evidence"][0],
            expected_task="task013",
        ),
        "task014": _validate_evidence(
            task014_dir / SOURCE_FILES["task014"]["evidence"][0],
            expected_task="task014",
        ),
    }
    configs013 = _load_configs(task013_dir / SOURCE_FILES["task013"]["config"][0], 24)
    configs014 = _load_configs(task014_dir / SOURCE_FILES["task014"]["config"][0], 72)
    configs = configs013 + configs014
    _validate_factorial(configs)
    _validate_through_focus(
        task013_dir / SOURCE_FILES["task013"]["through_focus"][0],
        configs013,
        360,
    )
    _validate_through_focus(
        task014_dir / SOURCE_FILES["task014"]["through_focus"][0],
        configs014,
        1080,
    )
    pairs = _build_pairs(configs)
    _validate_formal_paired(
        task013_dir / SOURCE_FILES["task013"]["paired"][0],
        pairs,
        12,
    )
    _validate_formal_paired(
        task014_dir / SOURCE_FILES["task014"]["paired"][0],
        pairs,
        36,
    )
    return Task015Analysis(
        pairs=pairs,
        n0_interactions=build_n0_interactions(pairs),
        coupling_matrix=build_coupling_matrix(pairs),
        source_blob_sha1=source_blobs,
        source_run_ids=run_ids,
    )
