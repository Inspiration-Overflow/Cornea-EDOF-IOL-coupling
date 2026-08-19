from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from .carriers import CarrierKey, ProvisionalCarrier
from .manifest import CarrierLock, ManifestBundle, NominalConfig, build_manifests
from .store import PROJECT_SCHEMA_VERSION, sha256_file


class ManifestLoadError(RuntimeError):
    pass


PHYSICAL_COLUMNS = (
    "schema_version",
    "carrier_id",
    "base_id",
    "cornea_id",
    "platform_id",
    "power_d",
    "q",
    "q_source_power_d",
    "r_ant_mm",
    "r_post_mm",
    "center_thickness_mm",
    "material",
    "iol_position_mm",
    "achieved_sa_um",
    "residual_id",
    "residual_sha256",
    "residual_validation_policy_id",
    "residual_validation_policy_hash",
    "lock_hash",
)
NOMINAL_COLUMNS = (
    "schema_version",
    "config_id",
    "carrier_id",
    "base_id",
    "cornea_id",
    "platform_id",
    "optic_state",
    "pupil_mm",
    "carrier_lock_hash",
    "residual_id",
    "residual_sha256",
    "residual_validation_policy_id",
    "residual_validation_policy_hash",
    "wavelength_nm",
    "field_deg",
    "cornea_decentration_mm",
    "iol_decentration_mm",
    "iol_tilt_deg",
    "micro_monovision_defocus_d",
)


def _read_rows(path: Path, expected_columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ManifestLoadError(f"formal manifest file is missing: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != expected_columns:
            raise ManifestLoadError(
                f"formal manifest columns differ from frozen schema: {path.name}"
            )
        rows = list(reader)
    if any(row.get("schema_version") != str(PROJECT_SCHEMA_VERSION) for row in rows):
        raise ManifestLoadError(f"formal manifest schema version mismatch: {path.name}")
    return rows


def _optional(text: str) -> str | None:
    return text if text else None


def _carrier_lock(row: dict[str, str]) -> CarrierLock:
    carrier = ProvisionalCarrier(
        key=CarrierKey(row["base_id"], row["cornea_id"], row["platform_id"]),
        power_d=float(row["power_d"]),
        q=float(row["q"]),
        q_source_power_d=float(row["q_source_power_d"]),
        r_ant_mm=float(row["r_ant_mm"]),
        r_post_mm=float(row["r_post_mm"]),
        center_thickness_mm=float(row["center_thickness_mm"]),
        material=row["material"],
        iol_position_mm=float(row["iol_position_mm"]),
        achieved_sa_um=float(row["achieved_sa_um"]),
    )
    lock = CarrierLock(
        carrier=carrier,
        residual_id=row["residual_id"],
        residual_sha256=row["residual_sha256"],
        residual_validation_policy_id=row["residual_validation_policy_id"],
        residual_validation_policy_hash=row["residual_validation_policy_hash"],
        lock_hash=row["lock_hash"],
    )
    if row["carrier_id"] != lock.carrier_id:
        raise ManifestLoadError(f"carrier_id does not match carrier key: {row['carrier_id']}")
    return lock


def _nominal_config(row: dict[str, str]) -> NominalConfig:
    return NominalConfig(
        config_id=row["config_id"],
        carrier_id=row["carrier_id"],
        base_id=row["base_id"],
        cornea_id=row["cornea_id"],
        platform_id=row["platform_id"],
        optic_state=row["optic_state"],
        pupil_mm=float(row["pupil_mm"]),
        carrier_lock_hash=row["carrier_lock_hash"],
        residual_id=_optional(row["residual_id"]),
        residual_sha256=_optional(row["residual_sha256"]),
        residual_validation_policy_id=_optional(row["residual_validation_policy_id"]),
        residual_validation_policy_hash=_optional(row["residual_validation_policy_hash"]),
        wavelength_nm=float(row["wavelength_nm"]),
        field_deg=float(row["field_deg"]),
        cornea_decentration_mm=float(row["cornea_decentration_mm"]),
        iol_decentration_mm=float(row["iol_decentration_mm"]),
        iol_tilt_deg=float(row["iol_tilt_deg"]),
        micro_monovision_defocus_d=float(row["micro_monovision_defocus_d"]),
    )


def load_formal_manifest_bundle(
    project_dir: str | Path,
    *,
    expected_manifest_hash: str | None = None,
    expected_physical_csv_sha256: str | None = None,
    expected_nominal_csv_sha256: str | None = None,
) -> ManifestBundle:
    """Load TASK-008 formal CSVs and prove they reproduce the canonical ManifestBundle."""

    root = Path(project_dir).resolve()
    manifest_dir = root / "manifests"
    physical_path = manifest_dir / "physical_carriers.csv"
    nominal_path = manifest_dir / "nominal_72.csv"
    hash_path = manifest_dir / "manifest.sha256"

    if expected_physical_csv_sha256 and sha256_file(physical_path) != expected_physical_csv_sha256:
        raise ManifestLoadError("physical carrier manifest SHA-256 differs from TASK-008 evidence")
    if expected_nominal_csv_sha256 and sha256_file(nominal_path) != expected_nominal_csv_sha256:
        raise ManifestLoadError("nominal manifest SHA-256 differs from TASK-008 evidence")

    physical_rows = _read_rows(physical_path, PHYSICAL_COLUMNS)
    nominal_rows = _read_rows(nominal_path, NOMINAL_COLUMNS)
    if len(physical_rows) != 18 or len(nominal_rows) != 72:
        raise ManifestLoadError("formal TASK-008 manifests must contain exactly 18 and 72 rows")

    locks = tuple(_carrier_lock(row) for row in physical_rows)
    rebuilt = build_manifests(locks)
    loaded_configs = tuple(_nominal_config(row) for row in nominal_rows)
    if loaded_configs != rebuilt.nominal_configs:
        raise ManifestLoadError("nominal_72.csv does not reproduce the canonical generated config set")

    if not hash_path.is_file():
        raise ManifestLoadError("manifest.sha256 is missing")
    recorded_hash = hash_path.read_text(encoding="utf-8").strip()
    if recorded_hash != rebuilt.manifest_hash:
        raise ManifestLoadError("manifest.sha256 does not match rebuilt formal manifest")
    if expected_manifest_hash and rebuilt.manifest_hash != expected_manifest_hash:
        raise ManifestLoadError("rebuilt manifest hash differs from TASK-008 evidence")

    # Explicitly exercise dataclass serialization here: changes in public manifest
    # fields must not be hidden by the CSV loader.
    if len({tuple(asdict(config)) for config in rebuilt.nominal_configs}) != 72:
        raise ManifestLoadError("rebuilt nominal configs are not uniquely serializable")
    return rebuilt
