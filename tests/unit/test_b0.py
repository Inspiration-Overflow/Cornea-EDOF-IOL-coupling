from __future__ import annotations

import math

import pytest

from whole_eye_mvp.b0 import B0CandidateInput, LockCurve, lock_b0, rank_b0_candidates
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


def candidate(value: float, epd3: LockCurve, epd5: LockCurve, **kwargs) -> B0CandidateInput:
    return B0CandidateInput(
        f"B{value:.2f}",
        value,
        epd3,
        epd5,
        achieved_delta_c40_um=value,
        **kwargs,
    )


@pytest.mark.unit
def test_b0_thresholds_distance_gates_and_deterministic_rank() -> None:
    a0_3, a0_5 = curve(1.0, 3), curve(0.8, 3)
    candidates = [
        candidate(v, curve(p, w), curve(p * 0.8, w))
        for v, p, w in [
            (0.10, 0.95, 4),
            (0.15, 0.92, 5),
            (0.20, 0.90, 6),
            (0.25, 0.88, 6),
            (0.30, 0.70, 8),
        ]
    ]
    report = rank_b0_candidates(a0_3, a0_5, candidates)
    assert report.complete
    assert report.threshold_epd3 == pytest.approx(0.5)
    assert report.threshold_epd5 == pytest.approx(0.4)
    assert report.recommendation_id == "B0.20"
    assert next(c for c in report.candidates if c.candidate_id == "B0.30").eligible is False
    assert [c.rank for c in report.candidates if c.candidate_id in {"B0.20", "B0.25"}] == [1, 2]


@pytest.mark.unit
def test_morphology_reject_requires_reason_and_changes_recommendation() -> None:
    a0 = curve(1.0, 3)
    candidates = [
        candidate(v, curve(0.9, 6 - i), curve(0.9, 6 - i))
        for i, v in enumerate((0.10, 0.15, 0.20, 0.25, 0.30))
    ]
    candidates[0] = candidate(
        0.10,
        curve(0.9, 6),
        curve(0.9, 6),
        morphology_reject=True,
        morphology_reason="stable double peak/deep valley",
    )
    report = rank_b0_candidates(a0, a0, candidates)
    assert report.recommendation_id != "B0.10"
    with pytest.raises(ValueError, match="reason"):
        bad = list(candidates)
        bad[0] = candidate(
            0.10,
            curve(0.9, 6),
            curve(0.9, 6),
            morphology_reject=True,
            morphology_reason="",
        )
        rank_b0_candidates(a0, a0, bad)


@pytest.mark.unit
def test_lock_recommendation_and_override_reason_rule() -> None:
    a0 = curve(1.0, 3)
    candidates = [
        candidate(v, curve(0.95 - i * 0.01, 6 - i), curve(0.9 - i * 0.01, 6 - i))
        for i, v in enumerate((0.10, 0.15, 0.20, 0.25, 0.30))
    ]
    report = rank_b0_candidates(a0, a0, candidates)
    lock = lock_b0(report, report.recommendation_id or "")
    assert not lock.override and lock.scan_hash == report.scan_hash
    other = next(
        c.candidate_id
        for c in report.candidates
        if c.eligible and c.candidate_id != report.recommendation_id
    )
    with pytest.raises(ValueError, match="override"):
        lock_b0(report, other, selection_reason="")
    assert lock_b0(report, other, selection_reason="manual morphology preference").override


@pytest.mark.unit
def test_incomplete_five_point_scan_cannot_lock() -> None:
    a0 = curve(1, 3)
    candidates = [candidate(v, curve(0.9, 5), curve(0.9, 5)) for v in (0.10, 0.15, 0.20, 0.25)]
    report = rank_b0_candidates(a0, a0, candidates)
    assert not report.complete and report.recommendation_id is None
    with pytest.raises(ValueError, match="complete"):
        lock_b0(report, "B0.10")


@pytest.mark.unit
def test_b0_rejects_short_grid_duplicate_id_bad_achieved_c40_and_nan() -> None:
    a0 = curve(1.0, 3)
    good = [candidate(v, curve(0.9, 5), curve(0.9, 5)) for v in (0.10, 0.15, 0.20, 0.25, 0.30)]

    short = list(good)
    short[0] = B0CandidateInput(
        "B0.10",
        0.10,
        LockCurve((0.0,), (0.9,)),
        curve(0.9, 5),
        achieved_delta_c40_um=0.10,
    )
    with pytest.raises(ValueError, match="17-plane"):
        rank_b0_candidates(a0, a0, short)

    duplicate = list(good)
    duplicate[1] = B0CandidateInput(
        "B0.10",
        0.15,
        curve(0.9, 5),
        curve(0.9, 5),
        achieved_delta_c40_um=0.15,
    )
    with pytest.raises(ValueError, match="unique|ID"):
        rank_b0_candidates(a0, a0, duplicate)

    bad_achieved = list(good)
    bad_achieved[0] = B0CandidateInput(
        "B0.10",
        0.10,
        curve(0.9, 5),
        curve(0.9, 5),
        achieved_delta_c40_um=0.20,
    )
    with pytest.raises(ValueError, match="achieved"):
        rank_b0_candidates(a0, a0, bad_achieved)

    nan_curve = LockCurve(D, tuple(math.nan if i == 5 else 0.5 for i in range(len(D))))
    nan_case = list(good)
    nan_case[0] = B0CandidateInput(
        "B0.10",
        0.10,
        nan_curve,
        curve(0.9, 5),
        achieved_delta_c40_um=0.10,
    )
    with pytest.raises(ValueError, match="finite"):
        rank_b0_candidates(a0, a0, nan_case)
