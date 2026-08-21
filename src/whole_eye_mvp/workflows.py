from __future__ import annotations

import csv
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .analysis import AnalysisBackend, ConfigResult, validate_completed_result, validate_selection
from .carriers import (
    ProvisionalCarrier,
    ResidualDefinition,
    ResidualValidationPolicy,
    ScientificInvariantError,
    residuals_ready,
    validate_18_provisional_carriers,
)
from .domain import (
    NOMINAL_MAIN_FFT_MTF_555_V2,
    ArtifactRecord,
    RunEnvironment,
    RunRecord,
    RunStatus,
)
from .manifest import (
    CarrierLock,
    ManifestBundle,
    build_manifests,
    compute_carrier_lock_hash,
    compute_lock_set_hash,
)
from .quality import new_run_id
from .store import PROJECT_SCHEMA_VERSION, ProjectStore, ProjectStoreError


@dataclass(frozen=True, slots=True)
class ManifestPaths:
    physical_carriers_csv: str
    nominal_72_csv: str
    manifest_hash_file: str


@dataclass(frozen=True, slots=True)
class TargetOutcome:
    config_id: str
    status: str
    result: ConfigResult | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class AnalysisBatchSummary:
    run_id: str
    environment_ref: str
    outcomes: tuple[TargetOutcome, ...]

    @property
    def completed(self) -> tuple[TargetOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.status == "completed")

    @property
    def failed(self) -> tuple[TargetOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.status == "failed")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def finalize_carrier_locks(
    carriers: Sequence[ProvisionalCarrier],
    residuals: Sequence[ResidualDefinition],
    *,
    residual_policy: ResidualValidationPolicy,
) -> tuple[CarrierLock, ...]:
    """Create formal physical locks only from validated carrier/residual evidence.

    Residual-induced best-focus shift is intentionally excluded from the physical lock.
    It is pupil/metric dependent and remains an analysis/result quantity.
    """

    validate_18_provisional_carriers(carriers)
    if not residuals_ready(
        residuals,
        carriers=carriers,
        policy=residual_policy,
        require_payload=True,
    ):
        raise ScientificInvariantError(
            "formal carrier locks require three evidence-backed validated residuals"
        )
    residual_by_platform = {residual.platform_id: residual for residual in residuals}

    locks: list[CarrierLock] = []
    for carrier in carriers:
        residual = residual_by_platform[carrier.key.platform_id]
        policy_hash = residual_policy.policy_hash
        lock_hash = compute_carrier_lock_hash(
            carrier,
            residual.residual_id,
            residual.sha256,
            residual_policy.policy_id,
            policy_hash,
        )
        locks.append(
            CarrierLock(
                carrier=carrier,
                residual_id=residual.residual_id,
                residual_sha256=residual.sha256,
                residual_validation_policy_id=residual_policy.policy_id,
                residual_validation_policy_hash=policy_hash,
                lock_hash=lock_hash,
            )
        )
    return tuple(locks)


def _atomic_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def export_manifest_bundle(bundle: ManifestBundle, output_dir: str | Path) -> ManifestPaths:
    output = Path(output_dir)
    carriers_path = output / "physical_carriers.csv"
    configs_path = output / "nominal_72.csv"
    hash_path = output / "manifest.sha256"

    carrier_rows: list[dict[str, object]] = []
    for lock in bundle.physical_carriers:
        carrier = lock.carrier
        carrier_rows.append(
            {
                "schema_version": PROJECT_SCHEMA_VERSION,
                "carrier_id": lock.carrier_id,
                "base_id": carrier.key.base_id,
                "cornea_id": carrier.key.cornea_id,
                "platform_id": carrier.key.platform_id,
                "power_d": carrier.power_d,
                "q": carrier.q,
                "q_source_power_d": carrier.q_source_power_d,
                "r_ant_mm": carrier.r_ant_mm,
                "r_post_mm": carrier.r_post_mm,
                "center_thickness_mm": carrier.center_thickness_mm,
                "material": carrier.material,
                "iol_position_mm": carrier.iol_position_mm,
                "achieved_sa_um": carrier.achieved_sa_um,
                "residual_id": lock.residual_id,
                "residual_sha256": lock.residual_sha256,
                "residual_validation_policy_id": lock.residual_validation_policy_id,
                "residual_validation_policy_hash": lock.residual_validation_policy_hash,
                "lock_hash": lock.lock_hash,
            }
        )
    _atomic_csv(carriers_path, tuple(carrier_rows[0]), carrier_rows)

    config_rows = [
        {"schema_version": PROJECT_SCHEMA_VERSION, **asdict(config)}
        for config in bundle.nominal_configs
    ]
    _atomic_csv(configs_path, tuple(config_rows[0]), config_rows)
    _atomic_text(hash_path, bundle.manifest_hash + "\n")
    return ManifestPaths(str(carriers_path), str(configs_path), str(hash_path))


def finalize_and_export_manifests(
    carriers: Sequence[ProvisionalCarrier],
    residuals: Sequence[ResidualDefinition],
    output_dir: str | Path,
    *,
    residual_policy: ResidualValidationPolicy,
) -> tuple[ManifestBundle, ManifestPaths]:
    locks = finalize_carrier_locks(
        carriers,
        residuals,
        residual_policy=residual_policy,
    )
    bundle = build_manifests(locks)
    return bundle, export_manifest_bundle(bundle, output_dir)


def _validate_analysis_environment(
    store: ProjectStore,
    bundle: ManifestBundle,
    environment: RunEnvironment,
) -> None:
    environment.validate()
    if environment.baseline_id != store.baseline.baseline_id:
        raise ProjectStoreError("analysis environment baseline does not match project baseline")
    if environment.analysis_settings_id != NOMINAL_MAIN_FFT_MTF_555_V2.settings_id:
        raise ProjectStoreError("analysis environment does not reference frozen main-analysis settings")
    if environment.manifest_hash != bundle.manifest_hash:
        raise ProjectStoreError("analysis environment manifest hash does not match manifest bundle")
    expected_lock_set_hash = compute_lock_set_hash(bundle.physical_carriers)
    if environment.lock_set_hash != expected_lock_set_hash:
        raise ProjectStoreError("analysis environment lock-set hash does not match manifest bundle")


def _validate_backend_provenance(backend: AnalysisBackend, environment: RunEnvironment) -> None:
    expected = {
        "acquisition_contract_id": environment.acquisition_contract_id,
        "acquisition_contract_hash": environment.acquisition_contract_hash,
        "frequency_scale_mode": environment.frequency_scale_mode,
    }
    for name, value in expected.items():
        actual = getattr(backend, name, None)
        if not isinstance(actual, str) or not actual.strip():
            raise ProjectStoreError(f"analysis backend does not expose required {name}")
        if actual != value:
            raise ProjectStoreError(
                f"analysis backend {name} does not match the frozen run environment"
            )


def _ensure_project_output_dir(store: ProjectStore, output_dir: str | Path) -> Path:
    output = Path(output_dir).expanduser().resolve()
    try:
        output.relative_to(store.root)
    except ValueError as exc:
        raise ProjectStoreError("formal analysis output directory must be inside project root") from exc
    output.mkdir(parents=True, exist_ok=True)
    return output


def _record_completed_result(
    store: ProjectStore,
    result: ConfigResult,
    target_dir: Path,
) -> None:
    result_json = target_dir / "config_result.json"
    _atomic_text(result_json, json.dumps(asdict(result), ensure_ascii=False, indent=2))
    artifact_paths = (result_json, *(Path(path) for path in result.artifacts.required_paths()))
    for index, path in enumerate(artifact_paths):
        resolved = path.expanduser().resolve()
        try:
            relative = resolved.relative_to(store.root)
            resolved.relative_to(target_dir.resolve())
        except ValueError as exc:
            raise ProjectStoreError("completed result artifact escaped its project target directory") from exc
        store.record_artifact(
            resolved,
            ArtifactRecord(
                artifact_id=f"{result.run_id}:{result.config.config_id}:{index}",
                artifact_type="config_result" if index == 0 else "analysis_artifact",
                relative_path=str(relative),
                baseline_id=store.baseline.baseline_id,
                run_id=result.run_id,
            ),
            lock=False,
        )


def run_analysis_batch(
    backend: AnalysisBackend,
    bundle: ManifestBundle,
    output_dir: str | Path,
    *,
    store: ProjectStore,
    environment: RunEnvironment,
    selection: Sequence[str] | None = None,
    run_id: str | None = None,
    require_files: bool = True,
) -> AnalysisBatchSummary:
    _validate_analysis_environment(store, bundle, environment)
    _validate_backend_provenance(backend, environment)
    manifest = bundle.nominal_configs
    selected = manifest if selection is None else validate_selection(selection, manifest)
    output = _ensure_project_output_dir(store, output_dir)
    current_run_id = run_id or new_run_id("analysis")
    environment_ref = store.record_environment(current_run_id, environment)
    outcomes: list[TargetOutcome] = []

    for config in selected:
        target_dir = output / current_run_id / config.config_id
        target_dir.mkdir(parents=True, exist_ok=True)
        started_at = _now()
        store.append_run(
            RunRecord(
                current_run_id,
                "analysis",
                config.config_id,
                RunStatus.RUNNING,
                started_at,
                environment_ref=environment_ref,
            )
        )
        try:
            result = backend.run_config(config, target_dir, current_run_id)
            validate_completed_result(
                result,
                require_files=require_files,
                expected_config=config,
                expected_run_id=current_run_id,
            )
            _record_completed_result(store, result, target_dir)
        except Exception as exc:  # noqa: BLE001 - isolate and record each backend target failure
            finished_at = _now()
            store.append_run(
                RunRecord(
                    current_run_id,
                    "analysis",
                    config.config_id,
                    RunStatus.FAILED,
                    started_at,
                    finished_at,
                    type(exc).__name__,
                    str(exc),
                    environment_ref,
                )
            )
            outcomes.append(
                TargetOutcome(
                    config.config_id,
                    "failed",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
        else:
            finished_at = _now()
            store.append_run(
                RunRecord(
                    current_run_id,
                    "analysis",
                    config.config_id,
                    RunStatus.COMPLETED,
                    started_at,
                    finished_at,
                    environment_ref=environment_ref,
                )
            )
            outcomes.append(TargetOutcome(config.config_id, "completed", result=result))
    return AnalysisBatchSummary(current_run_id, environment_ref, tuple(outcomes))


def rerun_failed(
    backend: AnalysisBackend,
    bundle: ManifestBundle,
    previous: AnalysisBatchSummary,
    output_dir: str | Path,
    *,
    store: ProjectStore,
    environment: RunEnvironment,
    require_files: bool = True,
) -> AnalysisBatchSummary:
    failed_ids = tuple(outcome.config_id for outcome in previous.failed)
    if not failed_ids:
        raise ValueError("previous run has no failed targets")
    return run_analysis_batch(
        backend,
        bundle,
        output_dir,
        store=store,
        environment=environment,
        selection=failed_ids,
        require_files=require_files,
    )