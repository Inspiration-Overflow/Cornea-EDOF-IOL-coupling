from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


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
    mtfa: float
    vsotf: float
    c40_um: float
    c60_um: float
    distance_peak_grid_d: float


@dataclass(frozen=True, slots=True)
class AcceptanceSummary:
    completed_configs: int
    matched_pairs: int
    through_focus_rows: int
    passed: bool


def validate_nominal_acceptance(results: Sequence[ResultEnvelope], paired_delta_keys: Sequence[str]) -> AcceptanceSummary:
    completed = [r for r in results if r.completed]
    ids = [r.config_id for r in completed]
    if len(ids) != len(set(ids)):
        raise AcceptanceError("duplicate completed config ID")
    if len(completed) != 72:
        raise AcceptanceError(f"expected 72 completed configs, got {len(completed)}")
    rows = sum(r.through_focus_rows for r in completed)
    if rows != 1080 or any(r.through_focus_rows != 15 for r in completed):
        raise AcceptanceError("expected exactly 15 through-focus rows per config / 1080 total")
    expected_pairs = {r.pair_key for r in completed}
    actual_pairs = set(paired_delta_keys)
    if len(expected_pairs) != 36 or actual_pairs != expected_pairs or len(paired_delta_keys) != 36:
        raise AcceptanceError("expected exactly 36 complete matched-pair deltas")
    return AcceptanceSummary(72, 36, 1080, True)


def validate_repeatability(first: Mapping[str, RepeatabilityPoint], second: Mapping[str, RepeatabilityPoint], *, relative_metric_tolerance: float = 0.001, zernike_tolerance_um: float = 0.001) -> None:
    if first.keys() != second.keys():
        raise AcceptanceError("repeatability result key sets differ")
    for key in first:
        a, b = first[key], second[key]
        for name in ("mtfa", "vsotf"):
            av, bv = getattr(a, name), getattr(b, name)
            scale = max(abs(av), abs(bv), 1e-15)
            if abs(av - bv) / scale > relative_metric_tolerance:
                raise AcceptanceError(f"{key} {name} repeatability exceeds tolerance")
        if abs(a.c40_um - b.c40_um) > zernike_tolerance_um or abs(a.c60_um - b.c60_um) > zernike_tolerance_um:
            raise AcceptanceError(f"{key} Zernike repeatability exceeds tolerance")
        if a.distance_peak_grid_d != b.distance_peak_grid_d:
            raise AcceptanceError(f"{key} distance-peak grid sample changed")
