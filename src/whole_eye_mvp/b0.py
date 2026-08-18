from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .metrics import DofInterval, DistancePeak, dof_interval, find_distance_peak
from .science_assets import B_CANDIDATE_DELTA_C40_UM


@dataclass(frozen=True, slots=True)
class LockCurve:
    defocus_d: tuple[float, ...]
    q_lock: tuple[float, ...]

    def peak(self) -> DistancePeak:
        return find_distance_peak(self.defocus_d, self.q_lock)


@dataclass(frozen=True, slots=True)
class B0CandidateInput:
    candidate_id: str
    delta_c40_um: float
    epd3: LockCurve
    epd5: LockCurve
    morphology_reject: bool = False
    morphology_reason: str = ""


@dataclass(frozen=True, slots=True)
class B0CandidateResult:
    candidate_id: str
    delta_c40_um: float
    epd3_distance_retention: float
    epd5_distance_retention: float
    epd3_dof_abs_d: float
    epd5_dof_abs_d: float
    passes_distance_gates: bool
    morphology_reject: bool
    morphology_reason: str
    eligible: bool
    rank: int | None = None


@dataclass(frozen=True, slots=True)
class B0ScanReport:
    a0_peak_epd3: float
    a0_peak_epd5: float
    threshold_epd3: float
    threshold_epd5: float
    candidates: tuple[B0CandidateResult, ...]
    recommendation_id: str | None
    scan_hash: str
    complete: bool


@dataclass(frozen=True, slots=True)
class B0Lock:
    candidate_id: str
    recommendation_id: str
    scan_hash: str
    selection_reason: str
    override: bool


def _curve_dof(curve: LockCurve, threshold: float) -> DofInterval:
    peak = curve.peak()
    return dof_interval(curve.defocus_d, curve.q_lock, peak=peak, threshold=threshold, absolute=True)


def _canonical_scan_hash(a0_epd3: LockCurve, a0_epd5: LockCurve, candidates: Sequence[B0CandidateInput]) -> str:
    payload = {"a0_epd3": asdict(a0_epd3), "a0_epd5": asdict(a0_epd5), "candidates": [asdict(c) for c in candidates]}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def rank_b0_candidates(a0_epd3: LockCurve, a0_epd5: LockCurve, candidates: Sequence[B0CandidateInput]) -> B0ScanReport:
    expected = set(B_CANDIDATE_DELTA_C40_UM)
    actual = {round(c.delta_c40_um, 2) for c in candidates}
    complete = len(candidates) == 5 and actual == expected
    a0_peak3 = a0_epd3.peak().value
    a0_peak5 = a0_epd5.peak().value
    t3, t5 = 0.5 * a0_peak3, 0.5 * a0_peak5
    results: list[B0CandidateResult] = []
    for candidate in candidates:
        p3, p5 = candidate.epd3.peak(), candidate.epd5.peak()
        r3 = p3.value / a0_peak3 if a0_peak3 else 0.0
        r5 = p5.value / a0_peak5 if a0_peak5 else 0.0
        d3 = _curve_dof(candidate.epd3, t3).width_d
        d5 = _curve_dof(candidate.epd5, t5).width_d
        gates = r3 >= 0.80 and r5 >= 0.70
        if candidate.morphology_reject and not candidate.morphology_reason.strip():
            raise ValueError("morphology reject requires a reason")
        results.append(B0CandidateResult(candidate.candidate_id, candidate.delta_c40_um, r3, r5, d3, d5, gates, candidate.morphology_reject, candidate.morphology_reason, gates and not candidate.morphology_reject))
    eligible = sorted((r for r in results if r.eligible), key=lambda r: (-r.epd3_dof_abs_d, -r.epd5_dof_abs_d, -r.epd3_distance_retention, abs(r.delta_c40_um)))
    rank_map = {r.candidate_id: i + 1 for i, r in enumerate(eligible)}
    ranked = tuple(B0CandidateResult(**{**asdict(r), "rank": rank_map.get(r.candidate_id)}) for r in results)
    recommendation = eligible[0].candidate_id if complete and eligible else None
    return B0ScanReport(a0_peak3, a0_peak5, t3, t5, ranked, recommendation, _canonical_scan_hash(a0_epd3, a0_epd5, candidates), complete)


def lock_b0(report: B0ScanReport, candidate_id: str, *, selection_reason: str = "confirmed recommendation") -> B0Lock:
    if not report.complete or report.recommendation_id is None:
        raise ValueError("B0 scan must be complete and have a recommendation")
    by_id: Mapping[str, B0CandidateResult] = {c.candidate_id: c for c in report.candidates}
    candidate = by_id.get(candidate_id)
    if candidate is None or not candidate.eligible:
        raise ValueError("candidate is unknown or ineligible")
    override = candidate_id != report.recommendation_id
    if override and not selection_reason.strip():
        raise ValueError("override requires a non-empty selection reason")
    return B0Lock(candidate_id, report.recommendation_id, report.scan_hash, selection_reason, override)
