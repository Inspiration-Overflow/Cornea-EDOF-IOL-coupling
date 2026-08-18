from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from .domain import ArtifactRecord, ArtifactRef, RunEnvironment, RunRecord, ScientificBaseline


class ProjectStoreError(RuntimeError):
    pass


class LockedArtifactConflict(ProjectStoreError):
    pass


class BaselineMismatch(ProjectStoreError):
    pass


class EnvironmentConflict(ProjectStoreError):
    pass


class SchemaError(ProjectStoreError):
    pass


PROJECT_SCHEMA_VERSION = 2
PROJECT_DIRS = (
    "models/assets",
    "models/b_candidates",
    "models/carriers",
    "models/configs",
    "locks",
    "manifests",
    "results/images",
    "logs",
    "environments",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scientific_baseline_hash(baseline: ScientificBaseline) -> str:
    text = json.dumps(asdict(baseline), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


class ProjectStore:
    def __init__(self, root: Path, baseline: ScientificBaseline) -> None:
        self.root = root
        self.baseline = baseline
        self.baseline_hash = scientific_baseline_hash(baseline)
        self.metadata_path = root / "project.json"
        self.artifact_index_path = root / "locks" / "artifact_index.csv"
        self.run_history_path = root / "logs" / "run_history.csv"

    @classmethod
    def open(cls, project_dir: str | Path, baseline: ScientificBaseline) -> ProjectStore:
        root = Path(project_dir).expanduser().resolve()
        try:
            root.mkdir(parents=True, exist_ok=True)
            probe = root / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            raise ProjectStoreError(f"project directory is not writable: {root}") from exc

        store = cls(root, baseline)
        if store.metadata_path.exists():
            try:
                payload = json.loads(store.metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SchemaError("project metadata is unreadable") from exc
            if payload.get("schema_version") != PROJECT_SCHEMA_VERSION:
                raise SchemaError("unsupported project schema version")
            if payload.get("baseline_id") != baseline.baseline_id:
                raise BaselineMismatch(
                    f"project baseline is {payload.get('baseline_id')!r}, "
                    f"requested {baseline.baseline_id!r}"
                )
            if payload.get("baseline_hash") != store.baseline_hash:
                raise BaselineMismatch(
                    "project baseline_id matches, but frozen scientific baseline contents differ"
                )
        else:
            _atomic_write_text(
                store.metadata_path,
                json.dumps(
                    {
                        "schema_version": PROJECT_SCHEMA_VERSION,
                        "baseline_id": baseline.baseline_id,
                        "baseline_hash": store.baseline_hash,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )

        for relative in PROJECT_DIRS:
            (root / relative).mkdir(parents=True, exist_ok=True)
        return store

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ProjectStoreError("artifact path escapes project root") from exc
        return candidate

    def _artifact_rows(self) -> list[dict[str, str]]:
        if not self.artifact_index_path.exists():
            return []
        expected = (
            "schema_version",
            "artifact_id",
            "artifact_type",
            "relative_path",
            "sha256",
            "baseline_id",
            "run_id",
            "locked",
        )
        with self.artifact_index_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != expected:
                raise SchemaError("artifact index CSV schema mismatch")
            rows = list(reader)
        if any(row.get("schema_version") != str(PROJECT_SCHEMA_VERSION) for row in rows):
            raise SchemaError("artifact index contains an unsupported schema version")
        return rows

    def record_artifact(
        self,
        source: str | Path,
        record: ArtifactRecord,
        *,
        lock: bool = False,
    ) -> ArtifactRef:
        source_path = Path(source)
        if not source_path.is_file():
            raise ProjectStoreError(f"artifact source does not exist: {source_path}")
        if record.baseline_id != self.baseline.baseline_id:
            raise BaselineMismatch("artifact baseline does not match project baseline")

        sha = sha256_file(source_path)
        rows = self._artifact_rows()
        existing = next((row for row in rows if row["artifact_id"] == record.artifact_id), None)
        if existing and existing["locked"] == "true":
            if existing["sha256"] == sha:
                return ArtifactRef(
                    artifact_id=existing["artifact_id"],
                    artifact_type=existing["artifact_type"],
                    relative_path=existing["relative_path"],
                    sha256=existing["sha256"],
                    baseline_id=existing["baseline_id"],
                    run_id=existing["run_id"] or None,
                    locked=True,
                )
            raise LockedArtifactConflict(record.artifact_id)
        if existing:
            rows = [row for row in rows if row["artifact_id"] != record.artifact_id]

        destination = self.resolve(record.relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != destination.resolve():
            shutil.copy2(source_path, destination)
        if sha256_file(destination) != sha:
            raise ProjectStoreError(f"artifact copy verification failed: {record.artifact_id}")

        ref = ArtifactRef(
            artifact_id=record.artifact_id,
            artifact_type=record.artifact_type,
            relative_path=record.relative_path,
            sha256=sha,
            baseline_id=record.baseline_id,
            run_id=record.run_id,
            locked=lock,
        )
        rows.append(
            {
                "schema_version": str(PROJECT_SCHEMA_VERSION),
                "artifact_id": ref.artifact_id,
                "artifact_type": ref.artifact_type,
                "relative_path": ref.relative_path,
                "sha256": ref.sha256,
                "baseline_id": ref.baseline_id,
                "run_id": ref.run_id or "",
                "locked": "true" if ref.locked else "false",
            }
        )
        self._write_csv(
            self.artifact_index_path,
            (
                "schema_version",
                "artifact_id",
                "artifact_type",
                "relative_path",
                "sha256",
                "baseline_id",
                "run_id",
                "locked",
            ),
            rows,
        )
        return ref

    def find_artifact(self, artifact_id: str) -> ArtifactRef | None:
        row = next(
            (item for item in self._artifact_rows() if item["artifact_id"] == artifact_id),
            None,
        )
        if row is None:
            return None
        return ArtifactRef(
            artifact_id=row["artifact_id"],
            artifact_type=row["artifact_type"],
            relative_path=row["relative_path"],
            sha256=row["sha256"],
            baseline_id=row["baseline_id"],
            run_id=row["run_id"] or None,
            locked=row["locked"] == "true",
        )

    def verify_artifact(self, ref: ArtifactRef) -> bool:
        path = self.resolve(ref.relative_path)
        return path.is_file() and sha256_file(path) == ref.sha256

    def record_environment(self, environment_id: str, environment: RunEnvironment) -> str:
        environment.validate()
        if environment.baseline_id != self.baseline.baseline_id:
            raise BaselineMismatch("run environment baseline does not match project baseline")
        if not environment_id.strip():
            raise ValueError("environment_id is required")
        path = self.root / "environments" / f"{environment_id}.json"
        text = json.dumps(asdict(environment), ensure_ascii=False, indent=2)
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if json.loads(existing) == json.loads(text):
                return path.relative_to(self.root).as_posix()
            raise EnvironmentConflict(f"run environment {environment_id!r} already exists")
        _atomic_write_text(path, text)
        return path.relative_to(self.root).as_posix()

    def append_run(self, record: RunRecord) -> None:
        rows: list[dict[str, str]] = []
        expected = (
            "schema_version",
            "run_id",
            "action",
            "target_id",
            "status",
            "started_at",
            "finished_at",
            "error_type",
            "error_message",
            "environment_ref",
        )
        if self.run_history_path.exists():
            with self.run_history_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if tuple(reader.fieldnames or ()) != expected:
                    raise SchemaError("run history CSV schema mismatch")
                rows.extend(reader)
            if any(row.get("schema_version") != str(PROJECT_SCHEMA_VERSION) for row in rows):
                raise SchemaError("run history contains an unsupported schema version")
        rows.append(
            {
                "schema_version": str(PROJECT_SCHEMA_VERSION),
                "run_id": record.run_id,
                "action": record.action,
                "target_id": record.target_id,
                "status": record.status.value,
                "started_at": record.started_at,
                "finished_at": record.finished_at or "",
                "error_type": record.error_type or "",
                "error_message": record.error_message or "",
                "environment_ref": record.environment_ref or "",
            }
        )
        self._write_csv(self.run_history_path, expected, rows)

    @staticmethod
    def _write_csv(path: Path, fieldnames: Iterable[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=tuple(fieldnames), extrasaction="raise")
                writer.writeheader()
                writer.writerows(rows)
            os.replace(temp_name, path)
        except (OSError, ValueError) as exc:
            raise SchemaError(f"failed to write {path.name}") from exc
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


def open_project_store(project_dir: str | Path, baseline: ScientificBaseline) -> ProjectStore:
    return ProjectStore.open(project_dir, baseline)
