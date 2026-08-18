from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .analysis import AnalysisBackend, ConfigResult, validate_completed_result, validate_selection
from .carriers import (
    ProvisionalCarrier,
    ResidualDefinition,
    ScientificInvariantError,
    residuals_ready,
    validate_18_provisional_carriers,
)
from .manifest import CarrierLock, ManifestBundle, NominalConfig, build_manifests
from .quality import new_run_id


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
    outcomes: tuple[TargetOutcome, ...]

    @property
    def completed(self) -> tuple[TargetOutcome, ...]:
        return tuple(x for x in self.outcomes if x.status == "completed")

    @property
    def failed(self) -> tuple[TargetOutcome, ...]:
        return tuple(x for x in self.outcomes if x.status == "failed")


def _stable_lock_hash(
    carrier: ProvisionalCarrier,
    residual: ResidualDefinition,
    delta_f_d: float,
) -> str:
    payload = {
        "carrier": asdict(carrier),
        "residual_id": residual.residual_id,
        "residual_sha256": residual.sha256,
        "delta_f_residual_d": delta_f_d,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def finalize_carrier_locks(
    carriers: Sequence[ProvisionalCarrier],
    residuals: Sequence[ResidualDefinition],
    delta_f_by_carrier_id: Mapping[str, float],
) -> tuple[CarrierLock, ...]:
    """Create formal locks only from already validated optical results."""

    validate_18_provisional_carriers(carriers)
    if not residuals_ready(residuals, require_payload=True):
        raise ScientificInvariantError("formal carrier locks require three validated residuals")
    residual_by_platform = {r.platform_id: r for r in residuals}
    expected_ids = {c.key.carrier_id for c in carriers}
    if set(delta_f_by_carrier_id) != expected_ids:
        raise ScientificInvariantError("delta-F map must contain exactly one value per carrier")

    locks: list[CarrierLock] = []
    for carrier in carriers:
        residual = residual_by_platform[carrier.key.platform_id]
        delta_f = float(delta_f_by_carrier_id[carrier.key.carrier_id])
        locks.append(
            CarrierLock(
                carrier=carrier,
                residual_id=residual.residual_id,
                delta_f_residual_d=delta_f,
                lock_hash=_stable_lock_hash(carrier, residual, delta_f),
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
                "delta_f_residual_d": lock.delta_f_residual_d,
                "lock_hash": lock.lock_hash,
            }
        )
    _atomic_csv(carriers_path, tuple(carrier_rows[0]), carrier_rows)

    config_rows = [asdict(config) for config in bundle.nominal_configs]
    _atomic_csv(configs_path, tuple(config_rows[0]), config_rows)
    hash_path.parent.mkdir(parents=True, exist_ok=True)
    hash_path.write_text(bundle.manifest_hash + "\n", encoding="utf-8")
    return ManifestPaths(str(carriers_path), str(configs_path), str(hash_path))


def finalize_and_export_manifests(
    carriers: Sequence[ProvisionalCarrier],
    residuals: Sequence[ResidualDefinition],
    delta_f_by_carrier_id: Mapping[str, float],
    output_dir: str | Path,
) -> tuple[ManifestBundle, ManifestPaths]:
    locks = finalize_carrier_locks(carriers, residuals, delta_f_by_carrier_id)
    bundle = build_manifests(locks)
    return bundle, export_manifest_bundle(bundle, output_dir)


def run_analysis_batch(
    backend: AnalysisBackend,
    manifest: Sequence[NominalConfig],
    output_dir: str | Path,
    *,
    selection: Sequence[str] | None = None,
    run_id: str | None = None,
    require_files: bool = True,
) -> AnalysisBatchSummary:
    selected = tuple(manifest) if selection is None else validate_selection(selection, manifest)
    current_run_id = run_id or new_run_id("analysis")
    output = Path(output_dir)
    outcomes: list[TargetOutcome] = []
    for config in selected:
        target_dir = output / current_run_id / config.config_id
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = backend.run_config(config, target_dir)
            validate_completed_result(result, require_files=require_files)
        except Exception as exc:
            outcomes.append(
                TargetOutcome(
                    config.config_id,
                    "failed",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
        else:
            outcomes.append(TargetOutcome(config.config_id, "completed", result=result))
    return AnalysisBatchSummary(current_run_id, tuple(outcomes))


def rerun_failed(
    backend: AnalysisBackend,
    manifest: Sequence[NominalConfig],
    previous: AnalysisBatchSummary,
    output_dir: str | Path,
    *,
    require_files: bool = True,
) -> AnalysisBatchSummary:
    failed_ids = tuple(x.config_id for x in previous.failed)
    if not failed_ids:
        raise ValueError("previous run has no failed targets")
    return run_analysis_batch(
        backend,
        manifest,
        output_dir,
        selection=failed_ids,
        require_files=require_files,
    )
