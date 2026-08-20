from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .acceptance import ResultEnvelope, validate_nominal_acceptance
from .analysis import (
    AberrationSummary,
    ConfigArtifacts,
    ConfigResult,
    MatchedPairDelta,
    ThroughFocusRow,
    matched_pair_delta,
    validate_completed_result,
)
from .analysis_zos_pair_scale import (
    EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
    PAIR_MONO_FREQUENCY_SCALE_MODE,
    TASK009_PAIR_MONO_MTF_ACQUISITION,
)
from .domain import NOMINAL_MAIN_FFT_MTF_555_V2, OpticState
from .manifest import ManifestBundle, NominalConfig
from .quality import settings_hash

RUN72_CLEARANCE_ID = "TASK009_RUN72_WEB_CLEARANCE_v1"
RUN72_RESULT_SCHEMA_VERSION = 1


class Run72Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Run72Acceptance:
    completed_configs: int
    matched_pairs: int
    through_focus_rows: int
    passed: bool


@dataclass(frozen=True, slots=True)
class Run72Aggregate:
    results: tuple[ConfigResult, ...]
    paired_deltas: tuple[MatchedPairDelta, ...]
    acceptance: Run72Acceptance


def validate_run72_clearance(payload: Mapping[str, object]) -> None:
    expected = {
        "clearance_id": RUN72_CLEARANCE_ID,
        "run72_authorized": True,
        "run72_started": False,
        "task009_complete": True,
        "production_sampling": NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
        "production_sampling_locked": True,
        "analysis_settings_id": NOMINAL_MAIN_FFT_MTF_555_V2.settings_id,
        "analysis_settings_sha256": settings_hash(NOMINAL_MAIN_FFT_MTF_555_V2),
        "acquisition_contract_id": TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id,
        "acquisition_contract_sha256": EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
        "frequency_scale_mode": PAIR_MONO_FREQUENCY_SCALE_MODE,
        "corrected_convergence_passed": True,
        "corrected_repeatability_passed": True,
        "six_config_integration_passed": True,
        "crosscheck_web_review": "PASS",
        "run_environment_provenance_hardened": True,
        "backend_provenance_fail_closed": True,
        "active_specs_synchronized": True,
        "no_additional_representative_opticstudio_rerun_required": True,
    }
    mismatches = {
        key: (payload.get(key), value)
        for key, value in expected.items()
        if payload.get(key) != value
    }
    if mismatches:
        raise Run72Error(f"Run72 Web clearance mismatch: {mismatches}")


def load_config_result_json(path: str | Path) -> ConfigResult:
    result_path = Path(path)
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Run72Error(f"ConfigResult JSON root must be an object: {result_path}")
    try:
        config = NominalConfig(**payload.pop("config"))
        rows = tuple(ThroughFocusRow(**row) for row in payload.pop("rows"))
        aberrations = AberrationSummary(**payload.pop("aberrations"))
        artifacts = ConfigArtifacts(**payload.pop("artifacts"))
        result = ConfigResult(
            config=config,
            rows=rows,
            aberrations=aberrations,
            artifacts=artifacts,
            **payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise Run72Error(f"invalid ConfigResult JSON schema: {result_path}") from exc
    validate_completed_result(result, require_files=True)
    return result


def _result_map(results: Sequence[ConfigResult], manifest: ManifestBundle) -> dict[str, ConfigResult]:
    expected = {config.config_id: config for config in manifest.nominal_configs}
    actual: dict[str, ConfigResult] = {}
    for result in results:
        validate_completed_result(result, require_files=True)
        config_id = result.config.config_id
        if config_id not in expected:
            raise Run72Error(f"result is outside frozen manifest: {config_id}")
        if result.config != expected[config_id]:
            raise Run72Error(f"result config identity differs from manifest: {config_id}")
        if config_id in actual:
            raise Run72Error(f"duplicate completed result: {config_id}")
        actual[config_id] = result
    return actual


def build_run72_aggregate(
    results: Sequence[ConfigResult],
    *,
    manifest: ManifestBundle,
) -> Run72Aggregate:
    by_id = _result_map(results, manifest)
    expected_ids = {config.config_id for config in manifest.nominal_configs}
    if set(by_id) != expected_ids:
        missing = sorted(expected_ids - set(by_id))
        raise Run72Error(f"Run72 is incomplete; missing completed configs: {missing}")

    pairs: dict[str, dict[str, ConfigResult]] = {}
    for result in by_id.values():
        state = str(result.config.optic_state)
        pairs.setdefault(result.config.pair_key, {})[state] = result

    deltas: list[MatchedPairDelta] = []
    for pair_key in sorted(pairs):
        states = pairs[pair_key]
        mono = states.get(str(OpticState.MONO))
        edof = states.get(str(OpticState.EDOF))
        if mono is None or edof is None or len(states) != 2:
            raise Run72Error(f"matched pair is incomplete or duplicated: {pair_key}")
        deltas.append(matched_pair_delta(mono, edof))

    envelopes = tuple(
        ResultEnvelope(
            config_id=result.config.config_id,
            pair_key=result.config.pair_key,
            completed=result.completed,
            through_focus_rows=len(result.rows),
        )
        for result in by_id.values()
    )
    accepted = validate_nominal_acceptance(
        envelopes,
        tuple(delta.pair_key for delta in deltas),
        manifest=manifest,
    )
    return Run72Aggregate(
        results=tuple(by_id[config.config_id] for config in manifest.nominal_configs),
        paired_deltas=tuple(deltas),
        acceptance=Run72Acceptance(
            accepted.completed_configs,
            accepted.matched_pairs,
            accepted.through_focus_rows,
            accepted.passed,
        ),
    )


def config_scalar_row(result: ConfigResult) -> dict[str, object]:
    return {
        "config_id": result.config.config_id,
        "pair_key": result.config.pair_key,
        "carrier_id": result.config.carrier_id,
        "base_id": result.config.base_id,
        "cornea_id": result.config.cornea_id,
        "platform_id": result.config.platform_id,
        "optic_state": str(result.config.optic_state),
        "pupil_mm": result.config.pupil_mm,
        "distance_peak_retina_d": result.distance_peak_retina_d,
        "distance_peak_mtfa": result.distance_peak_mtfa,
        "mtfa_at_zero_d": result.mtfa_at_zero_d,
        "dof50_far_d": result.dof50_far_d,
        "dof50_near_d": result.dof50_near_d,
        "dof50_width_d": result.dof50_width_d,
        "dof50_far_censored": result.dof50_far_censored,
        "dof50_near_censored": result.dof50_near_censored,
        "tf_mtfa_mean": result.tf_mtfa_mean,
        "peak_search_censored": result.peak_search_censored,
        "c40_um": result.aberrations.c40_um,
        "c60_um": result.aberrations.c60_um,
        "hoa_rms_um": result.aberrations.hoa_rms_um,
        "analysis_settings_hash": result.analysis_settings_hash,
        "hoa_settings_id": result.hoa_settings_id,
        "hoa_settings_hash": result.hoa_settings_hash,
        "model_sha256": result.model_hash_before,
        "entity_fingerprint": result.entity_fingerprint_before,
    }


def through_focus_rows(result: ConfigResult) -> tuple[dict[str, object], ...]:
    base = {
        "config_id": result.config.config_id,
        "pair_key": result.config.pair_key,
        "base_id": result.config.base_id,
        "cornea_id": result.config.cornea_id,
        "platform_id": result.config.platform_id,
        "optic_state": str(result.config.optic_state),
        "pupil_mm": result.config.pupil_mm,
    }
    return tuple({**base, **asdict(row)} for row in result.rows)


def paired_delta_row(delta: MatchedPairDelta) -> dict[str, object]:
    return {
        "pair_key": delta.pair_key,
        "mono_config_id": delta.mono_config_id,
        "edof_config_id": delta.edof_config_id,
        **dict(delta.deltas),
        "delta_f_residual_d": delta.deltas["distance_peak_retina_d"],
    }
