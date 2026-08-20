from __future__ import annotations

import csv
import hashlib
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


class ModelArchiveError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ModelIndexRecord:
    model_role: str
    run_id: str
    config_id: str
    pair_key: str
    carrier_id: str
    base_id: str
    cornea_id: str
    platform_id: str
    optic_state: str
    pupil_mm: float | str
    relative_path: str
    sha256: str


def sha256_file(path: str | Path) -> str:
    source = Path(path)
    if not source.is_file():
        raise ModelArchiveError(f"model file is missing: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_relative_path(project_dir: str | Path, path: str | Path) -> str:
    root = Path(project_dir).expanduser().resolve()
    resolved = Path(path).expanduser().resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ModelArchiveError(f"model escaped project root: {resolved}") from exc


def archive_model(
    source: str | Path,
    destination: str | Path,
    *,
    expected_sha256: str | None = None,
    overwrite: bool = False,
) -> str:
    source_path = Path(source).expanduser().resolve()
    destination_path = Path(destination).expanduser().resolve()
    source_sha = sha256_file(source_path)
    if expected_sha256 is not None and source_sha != expected_sha256:
        raise ModelArchiveError(
            f"source model SHA mismatch for {source_path.name}: "
            f"expected {expected_sha256}, got {source_sha}"
        )
    if source_path == destination_path:
        return source_sha
    if destination_path.exists() and not overwrite:
        destination_sha = sha256_file(destination_path)
        if destination_sha == source_sha:
            return source_sha
        raise ModelArchiveError(
            f"archive destination already exists with different bytes: {destination_path}"
        )
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)
    copied_sha = sha256_file(destination_path)
    if copied_sha != source_sha:
        raise ModelArchiveError(
            f"archive copy SHA mismatch: source={source_sha}, destination={copied_sha}"
        )
    return copied_sha


def write_model_index(
    path: str | Path,
    records: list[ModelIndexRecord] | tuple[ModelIndexRecord, ...],
) -> Path:
    if not records:
        raise ModelArchiveError("MODEL_INDEX requires at least one model record")
    index_path = Path(path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(record) for record in records]
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return index_path


def validate_model_index(
    project_dir: str | Path,
    records: list[ModelIndexRecord] | tuple[ModelIndexRecord, ...],
) -> None:
    root = Path(project_dir).expanduser().resolve()
    seen_paths: set[str] = set()
    for record in records:
        if not record.model_role.strip() or not record.relative_path.strip() or not record.sha256.strip():
            raise ModelArchiveError("MODEL_INDEX record lacks role/path/SHA")
        if record.relative_path in seen_paths:
            raise ModelArchiveError(f"MODEL_INDEX contains duplicate path: {record.relative_path}")
        seen_paths.add(record.relative_path)
        path = (root / record.relative_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ModelArchiveError(f"MODEL_INDEX path escaped project root: {record.relative_path}") from exc
        if sha256_file(path) != record.sha256:
            raise ModelArchiveError(f"MODEL_INDEX SHA mismatch: {record.relative_path}")
