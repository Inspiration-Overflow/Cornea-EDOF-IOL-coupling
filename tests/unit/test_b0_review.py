from __future__ import annotations

from dataclasses import asdict

import pytest

from whole_eye_mvp.b0 import B0CandidateInput, LockCurve, rank_b0_candidates
from whole_eye_mvp.b0_review import (
    B0ReviewError,
    MorphologyDecision,
    review_and_lock_b0_scan_payload,
    review_b0_scan_payload,
)
from whole_eye_mvp.domain import CORNEA_LOCK_B0_555_V2

D = CORNEA_LOCK_B0_555_V2.defocus_grid()


def curve(peak: float, width_samples: int) -> LockCurve:
    values = []
    for index, _defocus in enumerate(D):
        distance = abs(index - 2)
        values.append(
            peak
            if distance == 0
            else max(0.05, peak * (1 - distance / max(width_samples, 1)))
        )
    return LockCurve(D, tuple(values))


def source_scan_payload() -> dict[str, object]:
    a0_3 = curve(1.0, 3)
    a0_5 = curve(0.8, 3)
    candidates = tuple(
        B0CandidateInput(
            candidate_id=f"B{target:.2f}",
            delta_c40_um=target,
            achieved_delta_c40_um=target,
            epd3=curve(0.95 - index * 0.01, 7 - index),
            epd5=curve(0.78 - index * 0.01, 7 - index),
        )
        for index, target in enumerate((0.10, 0.15, 0.20, 0.25, 0.30))
    )
    report = rank_b0_candidates(a0_3, a0_5, candidates)
    return {
        "formal_artifact": False,
        "selection_locked": False,
        "analysis_settings": asdict(CORNEA_LOCK_B0_555_V2),
        "A0": {"epd3": asdict(a0_3), "epd5": asdict(a0_5)},
        "candidates": [
            {
                "candidate_id": item.candidate_id,
                "achieved_delta_c40_um": item.achieved_delta_c40_um,
                "epd3": asdict(item.epd3),
                "epd5": asdict(item.epd5),
            }
            for item in candidates
        ],
        "scan_report": asdict(report),
    }


def all_accept() -> tuple[MorphologyDecision, ...]:
    return tuple(
        MorphologyDecision(candidate_id, False, "")
        for candidate_id in ("B0.10", "B0.15", "B0.20", "B0.25", "B0.30")
    )


@pytest.mark.unit
def test_review_reproduces_scan_then_reject_changes_recommendation_and_hash() -> None:
    payload = source_scan_payload()
    original = payload["scan_report"]
    assert isinstance(original, dict)

    unchanged = review_b0_scan_payload(payload, all_accept())
    assert unchanged.recommendation_id == original["recommendation_id"]
    assert unchanged.scan_hash == original["scan_hash"]

    rejected_id = str(original["recommendation_id"])
    decisions = tuple(
        MorphologyDecision(
            item.candidate_id,
            item.candidate_id == rejected_id,
            "stable double peak/deep valley" if item.candidate_id == rejected_id else "",
        )
        for item in all_accept()
    )
    reviewed = review_b0_scan_payload(payload, decisions)
    assert reviewed.recommendation_id != rejected_id
    assert reviewed.scan_hash != original["scan_hash"]


@pytest.mark.unit
def test_review_requires_complete_decisions_and_reject_reason() -> None:
    payload = source_scan_payload()
    with pytest.raises(B0ReviewError, match="cover exactly"):
        review_b0_scan_payload(payload, all_accept()[:-1])

    bad = list(all_accept())
    bad[0] = MorphologyDecision("B0.10", True, "")
    with pytest.raises(ValueError, match="reason"):
        review_b0_scan_payload(payload, tuple(bad))


@pytest.mark.unit
def test_review_and_lock_records_reviewed_hash_and_override_rule() -> None:
    payload = source_scan_payload()
    report = review_b0_scan_payload(payload, all_accept())
    reviewed = review_and_lock_b0_scan_payload(
        payload,
        all_accept(),
        report.recommendation_id or "",
        selection_reason="confirmed recommendation after morphology review",
    )
    assert reviewed.lock.scan_hash == reviewed.report.scan_hash
    assert not reviewed.lock.override
    assert reviewed.source_scan_hash == payload["scan_report"]["scan_hash"]

    other = next(
        item.candidate_id
        for item in report.candidates
        if item.eligible and item.candidate_id != report.recommendation_id
    )
    with pytest.raises(ValueError, match="override"):
        review_and_lock_b0_scan_payload(
            payload,
            all_accept(),
            other,
            selection_reason="",
        )
