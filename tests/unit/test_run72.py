from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import whole_eye_mvp.run72 as run72
from whole_eye_mvp.analysis import MatchedPairDelta
from whole_eye_mvp.domain import OpticState
from whole_eye_mvp.manifest import ManifestBundle, NominalConfig


CLEARANCE = Path("docs/evidence/task009/TASK_009_RUN72_WEB_CLEARANCE.json")


def _manifest() -> ManifestBundle:
    configs = []
    for carrier_index in range(18):
        carrier_id = f"CAR_{carrier_index:02d}"
        for state in (OpticState.MONO, OpticState.EDOF):
            for pupil in (3.0, 5.0):
                configs.append(
                    NominalConfig(
                        config_id=f"CFG_{carrier_index:02d}_{state}_EPD{int(pupil)}",
                        carrier_id=carrier_id,
                        base_id="B",
                        cornea_id="C",
                        platform_id="P",
                        optic_state=state,
                        pupil_mm=pupil,
                        carrier_lock_hash=f"LOCK_{carrier_index:02d}",
                        residual_id="R" if state == OpticState.EDOF else None,
                        residual_sha256="S" if state == OpticState.EDOF else None,
                        residual_validation_policy_id="P" if state == OpticState.EDOF else None,
                        residual_validation_policy_hash="H" if state == OpticState.EDOF else None,
                    )
                )
    return ManifestBundle((), tuple(configs), "manifest")


@pytest.mark.unit
def test_run72_clearance_matches_active_pair_mono_contract() -> None:
    payload = json.loads(CLEARANCE.read_text(encoding="utf-8"))
    run72.validate_run72_clearance(payload)
    broken = dict(payload)
    broken["frequency_scale_mode"] = "per_state_EFFL"
    with pytest.raises(run72.Run72Error, match="clearance mismatch"):
        run72.validate_run72_clearance(broken)


@pytest.mark.unit
def test_run72_aggregate_requires_exact_72_and_36_pairs(monkeypatch) -> None:
    manifest = _manifest()
    results = tuple(
        SimpleNamespace(config=config, completed=True, rows=tuple(range(15)))
        for config in manifest.nominal_configs
    )
    by_id = {result.config.config_id: result for result in results}
    monkeypatch.setattr(run72, "_result_map", lambda _results, _manifest: by_id)

    def fake_delta(mono, edof):
        assert mono.config.pair_key == edof.config.pair_key
        return MatchedPairDelta(
            mono.config.pair_key,
            mono.config.config_id,
            edof.config.config_id,
            {"distance_peak_retina_d": 0.0},
        )

    monkeypatch.setattr(run72, "matched_pair_delta", fake_delta)
    aggregate = run72.build_run72_aggregate(results, manifest=manifest)
    assert aggregate.acceptance.passed is True
    assert aggregate.acceptance.completed_configs == 72
    assert aggregate.acceptance.matched_pairs == 36
    assert aggregate.acceptance.through_focus_rows == 1080
    assert len(aggregate.paired_deltas) == 36

    missing = results[:-1]
    missing_by_id = {result.config.config_id: result for result in missing}
    monkeypatch.setattr(run72, "_result_map", lambda _results, _manifest: missing_by_id)
    with pytest.raises(run72.Run72Error, match="missing completed configs"):
        run72.build_run72_aggregate(missing, manifest=manifest)
