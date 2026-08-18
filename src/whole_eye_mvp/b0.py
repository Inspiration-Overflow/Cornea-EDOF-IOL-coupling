from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from .domain import CORNEA_LOCK_B0_555_V1
from .metrics import DistancePeak, DofInterval, dof_interval, find_distance_peak
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
    achieved_delta_c40_um: float | None = None
    morphology_reject: bool = False
    morphology_reason: str = ""


@dataclass(frozen=True, slots=True)
class B0CandidateResult:
    candidate_id: str
    delta_c40_um: float
    achieved_delta_c40_um: float
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
    return dof_interval(
        curve.defocus_d,
        curve.q_lock,
        peak=peak,
        threshold=threshold,
        absolute=True,
    )


def _canonical_scan_hash(
    a0_epd3: LockCurve,
    a0_epd5: LockCurve,
    candidates: Sequence[B0CandidateInput],
) -> str:
    payload = {
        "settings": asdict(CORNEA_LOCK_B0_555_V1),
        "a0_epd3": asdict(a0_epd3),
        "a0_epd5": asdict(a0_epd5),
        "candidates": [asdict(c) for c in candidates],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def _validate_curve(curve: LockCurve, label: str) -> None:
    expected_grid = CORNEA_LOCK_B0_555_V1.defocus_grid()
    if curve.defocus_d != expected_grid:
        raise ValueError(f"{label} must use the frozen 17-plane B0 defocus grid")
    if len(curve.q_lock) != len(expected_grid):
        raise ValueError(f"{label} must contain exactly 17 Q_lock samples")
    if not all(math.isfinite(float(value)) and value >= 0 for value in curve.q_lock):
        raise ValueError(f"{label} Q_lock values must be finite and non-negative")


def _canonical_candidate_id(delta_c40_um: float) -> str:
    return f"B{delta_c40_um:.2f}"


def _validate_candidate(candidate: B0CandidateInput) -> None:
    if not math.isfinite(candidate.delta_c40_um):
        raise ValueError("candidate target ΔC4 must be finite")
    if candidate.candidate_id != _canonical_candidate_id(candidate.delta_c40_um):
        raise ValueError("candidate ID does not match its frozen ΔC4 target")
    if candidate.achieved_delta_c40_um is None or not math.isfinite(candidate.achieved_delta_c40_um):
        raise ValueError("candidate requires a finite achieved ΔC4 measurement")
    if abs(candidate.achieved_delta_c40_um - candidate.delta_c40_um) > 0.01 + 1e-12:
        raise ValueError("candidate achieved ΔC4 is outside ±0.01 µm target tolerance")
    _validate_curve(candidate.epd3, f"{candidate.candidate_id} EPD3")
    _validate_curve(candidate.epd5, f"{candidate.candidate_id} EPD5")
    if candidate.morphology_reject and not candidate.morphology_reason.strip():
        raise ValueError("morphology reject requires a reason")


def rank_b0_candidates(
    a0_epd3: LockCurve,
    a0_epd5: LockCurve,
    candidates: Sequence[B0CandidateInput],
) -> B0ScanReport:
    _validate_curve(a0_epd3, "A0 EPD3")
    _validate_curve(a0_epd5, "A0 EPD5")
    a0_peak3 = a0_epd3.peak().value
    a0_peak5 = a0_epd5.peak().value
    if not math.isfinite(a0_peak3) or not math.isfinite(a0_peak5) or a0_peak3 <= 0 or a0_peak5 <= 0:
        raise ValueError("A0 B0-lock peaks must be finite and positive")

    ids = [candidate.candidate_id for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("B0 candidate IDs must be unique")
    for candidate in candidates:
        _validate_candidate(candidate)

    expected = {round(value, 2) for value in B_CANDIDATE_DELTA_C40_UM}
    actual = {round(candidate.delta_c40_um, 2) for candidate in candidates}
    complete = len(candidates) == 5 and actual == expected
    t3, t5 = 0.5 * a0_peak3, 0.5 * a0_peak5
    results: list[B0CandidateResult] = []
    for candidate in candidates:
        p3, p5 = candidate.epd3.peak(), candidate.epd5.peak()
        r3 = p3.value / a0_peak3
        r5 = p5.value / a0_peak5
        d3 = _curve_dof(candidate.epd3, t3).width_d
        d5 = _curve_dof(candidate.epd5, t5).width_d
        gates = r3 >= 0.80 and r5 >= 0.70
        results.append(
            B0CandidateResult(
                candidate.candidate_id,
                candidate.delta_c40_um,
                float(candidate.achieved_delta_c40_um),
                r3,
                r5,
                d3,
                d5,
                gates,
                candidate.morphology_reject,
                candidate.morphology_reason,
                gates and not candidate.morphology_reject,
            )
        )

    eligible = sorted(
        (result for result in results if result.eligible),
        key=lambda result: (
            -result.epd3_dof_abs_d,
            -result.epd5_dof_abs_d,
            -result.epd3_distance_retention,
            abs(result.delta_c40_um),
        ),
    )
    rank_map = {result.candidate_id: index + 1 for index, result in enumerate(eligible)}
    ranked = tuple(
        B0CandidateResult(**{**asdict(result), "rank": rank_map.get(result.candidate_id)})
        for result in results
    )
    recommendation = eligible[0].candidate_id if complete and eligible else None
    return B0ScanReport(
        a0_peak3,
        a0_peak5,
        t3,
        t5,
        ranked,
        recommendation,
        _canonical_scan_hash(a0_epd3, a0_epd5, candidates),
        complete,
    )


def lock_b0(
    report: B0ScanReport,
    candidate_id: str,
    *,
    selection_reason: str = "confirmed recommendation",
) -> B0Lock:
    if not report.complete or report.recommendation_id is None:
        raise ValueError("B0 scan must be complete and have a recommendation")
    by_id: Mapping[str, B0CandidateResult] = {
        candidate.candidate_id: candidate for candidate in report.candidates
    }
    candidate = by_id.get(candidate_id)
    if candidate is None or not candidate.eligible:
        raise ValueError("candidate is unknown or ineligible")
    override = candidate_id != report.recommendation_id
    if override and not selection_reason.strip():
        raise ValueError("override requires a non-empty selection reason")
    return B0Lock(
        candidate_id,
        report.recommendation_id,
        report.scan_hash,
        selection_reason,
        override,
    )
