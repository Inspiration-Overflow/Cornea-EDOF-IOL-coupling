from __future__ import annotations

import csv
import hashlib
import json
import re
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .domain import AnalysisSettings
from .store import PROJECT_SCHEMA_VERSION, SchemaError


FORBIDDEN_EXACT_PRODUCT_MODEL_IDS = {
    "Vivity",
    "TECNIS PureSee",
    "PureSee",
    "LuxSmart",
    "PRESBYOND",
    "PresbyMAX",
}


def settings_hash(settings: AnalysisSettings) -> str:
    payload = json.dumps(asdict(settings), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_surrogate_model_id(model_id: str) -> None:
    if not model_id.strip():
        raise ValueError("model ID must not be empty")
    if model_id in FORBIDDEN_EXACT_PRODUCT_MODEL_IDS:
        raise ValueError("commercial product name must not be used as a research model ID")


def new_run_id(prefix: str = "run") -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "-", prefix).strip("-") or "run"
    return f"{clean}-{uuid.uuid4().hex}"


def read_csv_strict(
    path: str | Path,
    *,
    required_columns: Sequence[str],
    schema_version: int = PROJECT_SCHEMA_VERSION,
) -> list[dict[str, str]]:
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = tuple(reader.fieldnames or ())
        expected = tuple(required_columns)
        if actual != expected:
            raise SchemaError(f"CSV schema mismatch: expected {expected}, got {actual}")
        rows = list(reader)
    for row in rows:
        if row.get("schema_version") != str(schema_version):
            raise SchemaError("unsupported or missing CSV schema version")
    return rows


def assert_trace_coverage(
    trace_text: str,
    urd_ac_count: int = 15,
    mdd_api_count: int = 12,
) -> None:
    missing: list[str] = []
    for i in range(1, urd_ac_count + 1):
        ident = f"URD-AC-{i:03d}"
        if ident not in trace_text:
            missing.append(ident)
    for i in range(1, mdd_api_count + 1):
        ident = f"MDD-API-{i:03d}"
        if ident not in trace_text:
            missing.append(ident)
    if missing:
        raise ValueError(f"trace coverage missing IDs: {missing}")
