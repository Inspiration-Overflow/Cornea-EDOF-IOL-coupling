from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .b0 import B0CandidateInput, B0Lock, B0ScanReport, LockCurve, lock_b0, rank_b0_candidates
from .domain import CORNEA_LOCK_B0_555_V2


class B0ReviewError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MorphologyDecision:
    candidate_id: str
    reject: bool
    reason: str = ""

    def validate(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("morphology decision requires candidate_id")
        if self.reject and not self.reason.strip():
            raise ValueError("morphology reject requires a non-empty reason")


@dataclass(frozen=True, slots=True)
class B0ReviewedSelection:
    report: B0ScanReport
    lock: B0Lock
    decisions: tuple[MorphologyDecision, ...]
    source_scan_hash: str


def _json_normalized(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise B0ReviewError("scan analysis settings are not JSON-serializable") from exc


def _curve_from_payload(value: Any, label: str) -> LockCurve:
    if not isinstance(value, Mapping):
        raise B0ReviewError(f"{label} curve is missing")
    try:
        defocus = tuple(float(item) for item in value["defocus_d"])
        q_lock = tuple(float(item) for item in value["q_lock"])
    except (KeyError, TypeError, ValueError) as exc:
        raise B0ReviewError(f"{label} curve is malformed") from exc
    if not all(math.isfinite(item) for item in (*defocus, *q_lock)):
        raise B0ReviewError(f"{label} curve contains non-finite values")
    return LockCurve(defocus, q_lock)


def _decision_map(
    decisions: Sequence[MorphologyDecision],
    candidate_ids: set[str],
) -> dict[str, MorphologyDecision]:
    result: dict[str, MorphologyDecision] = {}
    for decision in decisions:
        decision.validate()
        if decision.candidate_id in result:
            raise B0ReviewError(f"duplicate morphology decision for {decision.candidate_id}")
        result[decision.candidate_id] = decision
    if set(result) != candidate_ids:
        missing = sorted(candidate_ids - set(result))
        extra = sorted(set(result) - candidate_ids)
        raise B0ReviewError(
            f"morphology decisions must cover exactly the five scanned candidates; "
            f"missing={missing}, extra={extra}"
        )
    return result


def review_b0_scan_payload(
    payload: Mapping[str, Any],
    decisions: Sequence[MorphologyDecision],
) -> B0ScanReport:
    """Re-rank a completed real scan after explicit human morphology decisions.

    This function never calls OpticStudio.  It rebuilds the frozen B0CandidateInput
    objects from the scan evidence, applies the supplied morphology flags/reasons,
    and delegates all thresholds, gates, DOF and ranking to ``rank_b0_candidates``.
    """

    settings = _json_normalized(payload.get("analysis_settings"))
    expected_settings = _json_normalized(asdict(CORNEA_LOCK_B0_555_V2))
    if settings != expected_settings:
        raise B0ReviewError("scan analysis settings do not match CORNEA_LOCK_B0_555_v2")
    if payload.get("selection_locked") is True:
        raise B0ReviewError("source scan is already marked locked")

    a0 = payload.get("A0")
    if not isinstance(a0, Mapping):
        raise B0ReviewError("source scan lacks A0 evidence")
    a_epd3 = _curve_from_payload(a0.get("epd3"), "A0 EPD3")
    a_epd5 = _curve_from_payload(a0.get("epd5"), "A0 EPD5")

    evidence = payload.get("candidates")
    source_report = payload.get("scan_report")
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        raise B0ReviewError("source scan candidate evidence is missing")
    if not isinstance(source_report, Mapping):
        raise B0ReviewError("source scan deterministic report is missing")

    source_rows = source_report.get("candidates")
    if not isinstance(source_rows, Sequence) or isinstance(source_rows, (str, bytes)):
        raise B0ReviewError("source scan report candidates are missing")
    target_by_id: dict[str, float] = {}
    for row in source_rows:
        if not isinstance(row, Mapping):
            raise B0ReviewError("source scan report candidate row is malformed")
        try:
            candidate_id = str(row["candidate_id"])
            target = float(row["delta_c40_um"])
        except (KeyError, TypeError, ValueError) as exc:
            raise B0ReviewError("source scan report candidate identity is malformed") from exc
        if candidate_id in target_by_id:
            raise B0ReviewError("source scan report candidate IDs must be unique")
        target_by_id[candidate_id] = target

    evidence_by_id: dict[str, Mapping[str, Any]] = {}
    for row in evidence:
        if not isinstance(row, Mapping):
            raise B0ReviewError("candidate evidence row is malformed")
        candidate_id = str(row.get("candidate_id", ""))
        if not candidate_id or candidate_id in evidence_by_id:
            raise B0ReviewError("candidate evidence IDs must be present and unique")
        evidence_by_id[candidate_id] = row

    if len(evidence_by_id) != 5 or set(evidence_by_id) != set(target_by_id):
        raise B0ReviewError("source scan must contain the same complete five-candidate set")
    decision_by_id = _decision_map(decisions, set(evidence_by_id))

    candidate_inputs: list[B0CandidateInput] = []
    for candidate_id in sorted(evidence_by_id, key=lambda item: target_by_id[item]):
        row = evidence_by_id[candidate_id]
        decision = decision_by_id[candidate_id]
        try:
            achieved = float(row["achieved_delta_c40_um"])
        except (KeyError, TypeError, ValueError) as exc:
            raise B0ReviewError(f"{candidate_id} achieved ΔC40 is missing") from exc
        candidate_inputs.append(
            B0CandidateInput(
                candidate_id=candidate_id,
                delta_c40_um=target_by_id[candidate_id],
                achieved_delta_c40_um=achieved,
                epd3=_curve_from_payload(row.get("epd3"), f"{candidate_id} EPD3"),
                epd5=_curve_from_payload(row.get("epd5"), f"{candidate_id} EPD5"),
                morphology_reject=decision.reject,
                morphology_reason=decision.reason,
            )
        )

    report = rank_b0_candidates(a_epd3, a_epd5, tuple(candidate_inputs))
    if not report.complete or report.recommendation_id is None:
        raise B0ReviewError("reviewed B0 scan has no eligible deterministic recommendation")
    return report


def review_and_lock_b0_scan_payload(
    payload: Mapping[str, Any],
    decisions: Sequence[MorphologyDecision],
    candidate_id: str,
    *,
    selection_reason: str,
) -> B0ReviewedSelection:
    report = review_b0_scan_payload(payload, decisions)
    try:
        source_scan_hash = str(payload["scan_report"]["scan_hash"])
    except (KeyError, TypeError) as exc:
        raise B0ReviewError("source scan hash is missing") from exc
    if not source_scan_hash.strip():
        raise B0ReviewError("source scan hash is empty")
    lock = lock_b0(
        report,
        candidate_id,
        selection_reason=selection_reason,
    )
    return B0ReviewedSelection(report, lock, tuple(decisions), source_scan_hash)
