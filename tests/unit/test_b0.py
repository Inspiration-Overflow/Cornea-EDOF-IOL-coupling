from __future__ import annotations

import pytest

from whole_eye_mvp.b0 import B0CandidateInput, LockCurve, lock_b0, rank_b0_candidates

D = (0.5, 0.25, 0.0, -0.25, -0.5, -0.75, -1.0, -1.25, -1.5, -1.75, -2.0, -2.25, -2.5, -2.75, -3.0, -3.25, -3.5)


def curve(peak: float, width_samples: int) -> LockCurve:
    y = []
    for i, d in enumerate(D):
        distance = abs(i - 2)
        y.append(peak if distance == 0 else max(0.05, peak * (1 - distance / max(width_samples, 1))))
    return LockCurve(D, tuple(y))


@pytest.mark.unit
def test_b0_thresholds_distance_gates_and_deterministic_rank() -> None:
    a0_3, a0_5 = curve(1.0, 3), curve(0.8, 3)
    candidates = [B0CandidateInput(f'B{v:.2f}', v, curve(p, w), curve(p*0.8, w)) for v, p, w in [(0.10,.95,4),(0.15,.92,5),(0.20,.90,6),(0.25,.88,6),(0.30,.70,8)]]
    report = rank_b0_candidates(a0_3, a0_5, candidates)
    assert report.complete
    assert report.threshold_epd3 == pytest.approx(0.5)
    assert report.threshold_epd5 == pytest.approx(0.4)
    assert report.recommendation_id == 'B0.20'
    assert next(c for c in report.candidates if c.candidate_id == 'B0.30').eligible is False
    assert [c.rank for c in report.candidates if c.candidate_id in {'B0.20','B0.25'}] == [1,2]


@pytest.mark.unit
def test_morphology_reject_requires_reason_and_changes_recommendation() -> None:
    a0 = curve(1.0, 3)
    candidates = [B0CandidateInput(f'B{v:.2f}', v, curve(.9, 6-i), curve(.9, 6-i)) for i,v in enumerate((.10,.15,.20,.25,.30))]
    candidates[0] = B0CandidateInput('B0.10', .10, curve(.9, 6), curve(.9, 6), True, 'stable double peak/deep valley')
    report = rank_b0_candidates(a0, a0, candidates)
    assert report.recommendation_id != 'B0.10'
    with pytest.raises(ValueError, match='reason'):
        bad = list(candidates); bad[0] = B0CandidateInput('B0.10', .10, curve(.9,6), curve(.9,6), True, '')
        rank_b0_candidates(a0, a0, bad)


@pytest.mark.unit
def test_lock_recommendation_and_override_reason_rule() -> None:
    a0 = curve(1.0, 3)
    candidates = [B0CandidateInput(f'B{v:.2f}', v, curve(.95-i*.01, 6-i), curve(.9-i*.01, 6-i)) for i,v in enumerate((.10,.15,.20,.25,.30))]
    report = rank_b0_candidates(a0, a0, candidates)
    lock = lock_b0(report, report.recommendation_id or '')
    assert not lock.override and lock.scan_hash == report.scan_hash
    other = next(c.candidate_id for c in report.candidates if c.eligible and c.candidate_id != report.recommendation_id)
    with pytest.raises(ValueError, match='override'):
        lock_b0(report, other, selection_reason='')
    assert lock_b0(report, other, selection_reason='manual morphology preference').override


@pytest.mark.unit
def test_incomplete_five_point_scan_cannot_lock() -> None:
    a0 = curve(1,3)
    candidates = [B0CandidateInput(f'B{v:.2f}', v, curve(.9,5), curve(.9,5)) for v in (.10,.15,.20,.25)]
    report = rank_b0_candidates(a0,a0,candidates)
    assert not report.complete and report.recommendation_id is None
    with pytest.raises(ValueError, match='complete'):
        lock_b0(report, 'B0.10')
