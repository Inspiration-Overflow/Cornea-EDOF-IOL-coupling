from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from .domain import NOMINAL_MAIN_555_V1
from .manifest import NominalConfig
from .metrics import find_distance_peak, matched_numeric_delta


class AnalysisError(RuntimeError):
    pass


class ExportError(AnalysisError):
    pass


@dataclass(frozen=True, slots=True)
class ThroughFocusRow:
    defocus_retina_d: float
    defocus_shape_d: float
    mtfa: float
    vsotf: float
    mtf10: float
    mtf20: float
    mtf30: float
    mtf40: float
    mtf50: float
    mtf60: float


@dataclass(frozen=True, slots=True)
class AberrationSummary:
    c40_um: float
    c60_um: float
    hoa_rms_um: float


@dataclass(frozen=True, slots=True)
class ConfigArtifacts:
    zos_path: str
    through_focus_plot: str
    mtf_plot: str
    psf_paths: tuple[str, str, str]

    def required_paths(self) -> tuple[str, ...]:
        return (self.zos_path, self.through_focus_plot, self.mtf_plot, *self.psf_paths)


@dataclass(frozen=True, slots=True)
class ConfigResult:
    config: NominalConfig
    run_id: str
    rows: tuple[ThroughFocusRow, ...]
    distance_peak_retina_d: float
    aberrations: AberrationSummary
    cornea_footprint_mm: float
    stop_footprint_mm: float
    iol_footprint_mm: float
    iol_optical_diameter_mm: float
    model_hash_before: str
    model_hash_after: str
    retina_position_before_mm: float
    retina_position_after_mm: float
    artifacts: ConfigArtifacts
    completed: bool


@dataclass(frozen=True, slots=True)
class MatchedPairDelta:
    pair_key: str
    mono_config_id: str
    edof_config_id: str
    deltas: Mapping[str, float]


class AnalysisBackend(Protocol):
    def run_config(self, config: NominalConfig, output_dir: Path) -> ConfigResult: ...


def with_shape_axis(defocus_retina_d: Sequence[float], mtfa: Sequence[float], vsotf: Sequence[float], mtf_columns: Sequence[Sequence[float]]) -> tuple[ThroughFocusRow, ...]:
    peak = find_distance_peak(defocus_retina_d, vsotf)
    if len(mtf_columns) != 6:
        raise ValueError("six MTF columns at 10/20/30/40/50/60 cpd are required")
    n = len(defocus_retina_d)
    if any(len(x) != n for x in (mtfa, vsotf, *mtf_columns)):
        raise ValueError("through-focus columns must have equal lengths")
    return tuple(ThroughFocusRow(float(defocus_retina_d[i]), float(defocus_retina_d[i] - peak.defocus_d), float(mtfa[i]), float(vsotf[i]), *(float(col[i]) for col in mtf_columns)) for i in range(n))


def validate_selection(selection: Sequence[str], manifest: Sequence[NominalConfig]) -> tuple[NominalConfig, ...]:
    by_id = {c.config_id: c for c in manifest}
    unknown = [cid for cid in selection if cid not in by_id]
    if unknown:
        raise AnalysisError(f"selection contains manifest-external IDs: {unknown}")
    return tuple(by_id[cid] for cid in selection)


def validate_completed_result(result: ConfigResult, *, require_files: bool = False) -> None:
    if len(result.rows) != len(NOMINAL_MAIN_555_V1.defocus_grid()):
        raise AnalysisError("nominal config must contain exactly 15 through-focus rows")
    expected = NOMINAL_MAIN_555_V1.defocus_grid()
    actual = tuple(row.defocus_retina_d for row in result.rows)
    if actual != expected:
        raise AnalysisError("retina-anchored defocus grid differs from frozen settings")
    if result.model_hash_before != result.model_hash_after:
        raise AnalysisError("entity model changed during through-focus analysis")
    if result.retina_position_before_mm != result.retina_position_after_mm:
        raise AnalysisError("retina position changed during through-focus analysis")
    if result.iol_footprint_mm > result.iol_optical_diameter_mm:
        raise AnalysisError("IOL footprint exceeds optical diameter")
    if not all(result.artifacts.required_paths()):
        raise ExportError("mandatory artifact path is missing")
    if require_files:
        missing = [p for p in result.artifacts.required_paths() if not Path(p).is_file()]
        if missing:
            raise ExportError(f"mandatory artifact file missing: {missing}")
    if not result.completed:
        raise AnalysisError("result is not marked completed")


def matched_pair_delta(mono: ConfigResult, edof: ConfigResult) -> MatchedPairDelta:
    validate_completed_result(mono)
    validate_completed_result(edof)
    if mono.config.pair_key != edof.config.pair_key:
        raise AnalysisError("results are not a matched pair")
    if mono.config.optic_state != "MONO" or edof.config.optic_state != "EDOF":
        raise AnalysisError("matched delta expects MONO then EDOF")
    mono_scalar = {"distance_peak_retina_d": mono.distance_peak_retina_d, "c40_um": mono.aberrations.c40_um, "c60_um": mono.aberrations.c60_um, "hoa_rms_um": mono.aberrations.hoa_rms_um}
    edof_scalar = {"distance_peak_retina_d": edof.distance_peak_retina_d, "c40_um": edof.aberrations.c40_um, "c60_um": edof.aberrations.c60_um, "hoa_rms_um": edof.aberrations.hoa_rms_um}
    return MatchedPairDelta(mono.config.pair_key, mono.config.config_id, edof.config.config_id, matched_numeric_delta(edof_scalar, mono_scalar))
