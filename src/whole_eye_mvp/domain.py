from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from enum import StrEnum
from typing import Any, Mapping


class BaseId(StrEnum):
    LB_AL2395 = "LB_AL2395"
    ATC_M3_AL24477 = "ATC_M3_AL24477"


class CorneaId(StrEnum):
    A0 = "A0"
    B0 = "B0"
    C0 = "C0"


class PlatformId(StrEnum):
    WFS = "WFS"
    RAD = "RAD"
    HOA = "HOA"


class OpticState(StrEnum):
    MONO = "MONO"
    EDOF = "EDOF"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AnalysisSettings:
    settings_id: str
    wavelength_nm: float
    pupils_mm: tuple[float, ...]
    defocus_start_d: float
    defocus_stop_d: float
    defocus_step_d: float
    dof_relative_fraction: float = 0.5
    dof_absolute_threshold: float = 0.10

    def defocus_grid(self) -> tuple[float, ...]:
        values: list[float] = []
        value = self.defocus_start_d
        if self.defocus_step_d == 0:
            raise ValueError("defocus_step_d must not be zero")
        if self.defocus_step_d < 0:
            while value >= self.defocus_stop_d - 1e-12:
                values.append(round(value, 10))
                value += self.defocus_step_d
        else:
            while value <= self.defocus_stop_d + 1e-12:
                values.append(round(value, 10))
                value += self.defocus_step_d
        return tuple(values)


CORNEA_LOCK_B0_555_V1 = AnalysisSettings(
    settings_id="CORNEA_LOCK_B0_555_v1",
    wavelength_nm=555.0,
    pupils_mm=(3.0, 5.0),
    defocus_start_d=0.50,
    defocus_stop_d=-3.50,
    defocus_step_d=-0.25,
)

NOMINAL_MAIN_555_V1 = AnalysisSettings(
    settings_id="NOMINAL_MAIN_555_v1",
    wavelength_nm=555.0,
    pupils_mm=(3.0, 5.0),
    defocus_start_d=0.50,
    defocus_stop_d=-3.00,
    defocus_step_d=-0.25,
)


@dataclass(frozen=True, slots=True)
class ScientificBaseline:
    baseline_id: str
    base_ids: tuple[str, ...] = (BaseId.LB_AL2395, BaseId.ATC_M3_AL24477)
    cornea_ids: tuple[str, ...] = (CorneaId.A0, CorneaId.B0, CorneaId.C0)
    platform_ids: tuple[str, ...] = (PlatformId.WFS, PlatformId.RAD, PlatformId.HOA)
    iteration_limit: int = 2


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    artifact_type: str
    relative_path: str
    baseline_id: str
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    artifact_type: str
    relative_path: str
    sha256: str
    baseline_id: str
    run_id: str | None
    locked: bool


@dataclass(frozen=True, slots=True)
class RunEnvironment:
    program_version: str
    opticstudio_version: str
    baseline_id: str
    analysis_settings_id: str
    manifest_hash: str
    lock_set_hash: str

    def validate(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field.name} is required")


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    action: str
    target_id: str
    status: RunStatus
    started_at: str
    finished_at: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    environment_ref: str | None = None


def strict_dataclass_from_mapping(cls: type[Any], payload: Mapping[str, Any]) -> Any:
    if not is_dataclass(cls):
        raise TypeError("cls must be a dataclass type")
    expected = {f.name for f in fields(cls)}
    actual = set(payload)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        raise ValueError(f"schema mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    return cls(**payload)


def dataclass_to_dict(value: Any) -> dict[str, Any]:
    if not is_dataclass(value):
        raise TypeError("value must be a dataclass instance")
    return asdict(value)
