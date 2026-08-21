from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .manifest import ManifestBundle


class AcceptanceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResultEnvelope:
    config_id: str
    pair_key: str
    completed: bool
    through_focus_rows: int


@dataclass(frozen=True, slots=True)
class RepeatabilityPoint:
    distance_peak_mtfa: float
    tf_mtfa_mean: float
    c40_um: float
    c60_um: float
    distance_peak_grid_d: float


@dataclass(frozen=True, slots=True)
class AcceptanceSummary:
    completed_configs: int
    matched_pairs: int
    through_focus_rows: int
    passed: bool


def validate_nominal_acceptance(
    results: Sequence[ResultEnvelope],
    paired_delta_keys: Sequence[str],
    *,
    manifest: ManifestBundle,
) -> AcceptanceSummary:
    configs = manifest.nominal_configs
    if len(configs) != 72 or len({config.config_id for config in configs}) != 72:
        raise AcceptanceError("acceptance requires the exact 72-row nominal manifest bundle")
    expected_ids = {config.config_id for config in configs}
    expected_pairs = {config.pair_key for config in configs}
    if len(expected_pairs) != 36:
        raise AcceptanceError("nominal manifest must contain exactly 36 pair keys")

    completed = [result for result in results if result.completed]
    ids = [result.config_id for result in completed]
    if len(ids) != len(set(ids)):
        raise AcceptanceError("duplicate completed config ID")
    if set(ids) != expected_ids or len(completed) != 72:
        raise AcceptanceError("completed config IDs do not exactly match the nominal manifest")
    pair_by_config = {result.config_id: result.pair_key for result in completed}
    for config in configs:
        if pair_by_config.get(config.config_id) != config.pair_key:
            raise AcceptanceError("completed result pair key differs from nominal manifest")

    rows = sum(result.through_focus_rows for result in completed)
    if rows != 1080 or any(result.through_focus_rows != 15 for result in completed):
        raise AcceptanceError("expected exactly 15 through-focus rows per config / 1080 total")
    actual_pairs = list(paired_delta_keys)
    if len(actual_pairs) != 36 or len(set(actual_pairs)) != 36 or set(actual_pairs) != expected_pairs:
        raise AcceptanceError("paired deltas do not exactly match the 36 manifest pair keys")
    return AcceptanceSummary(72, 36, 1080, True)


def validate_repeatability(
    first: Mapping[str, RepeatabilityPoint],
    second: Mapping[str, RepeatabilityPoint],
    *,
    relative_metric_tolerance: float = 0.001,
    zernike_tolerance_um: float = 0.001,
) -> None:
    if first.keys() != second.keys():
        raise AcceptanceError("repeatability result key sets differ")
    if relative_metric_tolerance < 0 or zernike_tolerance_um < 0:
        raise AcceptanceError("repeatability tolerances must be non-negative")
    for key in first:
        a, b = first[key], second[key]
        values = (
            a.distance_peak_mtfa,
            a.tf_mtfa_mean,
            a.c40_um,
            a.c60_um,
            a.distance_peak_grid_d,
            b.distance_peak_mtfa,
            b.tf_mtfa_mean,
            b.c40_um,
            b.c60_um,
            b.distance_peak_grid_d,
        )
        if not all(math.isfinite(value) for value in values):
            raise AcceptanceError(f"{key} repeatability values must be finite")
        for name in ("distance_peak_mtfa", "tf_mtfa_mean"):
            av, bv = getattr(a, name), getattr(b, name)
            scale = max(abs(av), abs(bv), 1e-15)
            if abs(av - bv) / scale > relative_metric_tolerance:
                raise AcceptanceError(f"{key} {name} repeatability exceeds tolerance")
        if (
            abs(a.c40_um - b.c40_um) > zernike_tolerance_um
            or abs(a.c60_um - b.c60_um) > zernike_tolerance_um
        ):
            raise AcceptanceError(f"{key} Zernike repeatability exceeds tolerance")
        if a.distance_peak_grid_d != b.distance_peak_grid_d:
            raise AcceptanceError(f"{key} distance-peak grid sample changed")
