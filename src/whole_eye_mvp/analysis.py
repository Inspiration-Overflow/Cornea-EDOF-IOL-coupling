from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from .domain import NOMINAL_MAIN_555_V1, OpticState
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
    through_focus_csv: str
    through_focus_plot: str
    mtf_plot: str
    psf_paths: tuple[str, str, str]

    def required_paths(self) -> tuple[str, ...]:
        return (
            self.zos_path,
            self.through_focus_csv,
            self.through_focus_plot,
            self.mtf_plot,
            *self.psf_paths,
        )


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
    iol_position_before_mm: float
    iol_position_after_mm: float
    elp_before_mm: float
    elp_after_mm: float
    unintended_vignetting: bool
    artifacts: ConfigArtifacts
    completed: bool


@dataclass(frozen=True, slots=True)
class MatchedPairDelta:
    pair_key: str
    mono_config_id: str
    edof_config_id: str
    deltas: Mapping[str, float]


class AnalysisBackend(Protocol):
    """OpticStudio-facing acquisition boundary implemented during local integration."""

    def run_config(
        self,
        config: NominalConfig,
        output_dir: Path,
        run_id: str,
    ) -> ConfigResult: ...


def _all_finite(values: Sequence[float]) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def with_shape_axis(
    defocus_retina_d: Sequence[float],
    mtfa: Sequence[float],
    vsotf: Sequence[float],
    mtf_columns: Sequence[Sequence[float]],
) -> tuple[ThroughFocusRow, ...]:
    if len(mtf_columns) != 6:
        raise ValueError("six MTF columns at 10/20/30/40/50/60 cpd are required")
    n = len(defocus_retina_d)
    if any(len(values) != n for values in (mtfa, vsotf, *mtf_columns)):
        raise ValueError("through-focus columns must have equal lengths")
    if not _all_finite(tuple(defocus_retina_d)):
        raise ValueError("defocus samples must be finite")
    if not all(_all_finite(tuple(values)) for values in (mtfa, vsotf, *mtf_columns)):
        raise ValueError("through-focus metric values must be finite")
    peak = find_distance_peak(defocus_retina_d, vsotf)
    return tuple(
        ThroughFocusRow(
            float(defocus_retina_d[index]),
            float(defocus_retina_d[index] - peak.defocus_d),
            float(mtfa[index]),
            float(vsotf[index]),
            *(float(column[index]) for column in mtf_columns),
        )
        for index in range(n)
    )


def validate_selection(
    selection: Sequence[str], manifest: Sequence[NominalConfig]
) -> tuple[NominalConfig, ...]:
    by_id = {config.config_id: config for config in manifest}
    if len(by_id) != len(manifest):
        raise AnalysisError("manifest contains duplicate config IDs")
    unknown = [config_id for config_id in selection if config_id not in by_id]
    if unknown:
        raise AnalysisError(f"selection contains manifest-external IDs: {unknown}")
    if len(selection) != len(set(selection)):
        raise AnalysisError("selection contains duplicate config IDs")
    return tuple(by_id[config_id] for config_id in selection)


def validate_completed_result(
    result: ConfigResult,
    *,
    require_files: bool = False,
    expected_config: NominalConfig | None = None,
    expected_run_id: str | None = None,
) -> None:
    if expected_config is not None and result.config != expected_config:
        raise AnalysisError("backend returned a result for a different manifest config")
    if expected_run_id is not None and result.run_id != expected_run_id:
        raise AnalysisError("backend returned a result with the wrong run_id")
    if not result.run_id.strip():
        raise AnalysisError("result run_id is required")
    if len(result.rows) != len(NOMINAL_MAIN_555_V1.defocus_grid()):
        raise AnalysisError("nominal config must contain exactly 15 through-focus rows")

    expected_grid = NOMINAL_MAIN_555_V1.defocus_grid()
    actual_grid = tuple(row.defocus_retina_d for row in result.rows)
    if actual_grid != expected_grid:
        raise AnalysisError("retina-anchored defocus grid differs from frozen settings")

    row_values = [
        value
        for row in result.rows
        for value in (
            row.defocus_retina_d,
            row.defocus_shape_d,
            row.mtfa,
            row.vsotf,
            row.mtf10,
            row.mtf20,
            row.mtf30,
            row.mtf40,
            row.mtf50,
            row.mtf60,
        )
    ]
    scalar_values = (
        result.distance_peak_retina_d,
        result.aberrations.c40_um,
        result.aberrations.c60_um,
        result.aberrations.hoa_rms_um,
        result.cornea_footprint_mm,
        result.stop_footprint_mm,
        result.iol_footprint_mm,
        result.iol_optical_diameter_mm,
        result.retina_position_before_mm,
        result.retina_position_after_mm,
        result.iol_position_before_mm,
        result.iol_position_after_mm,
        result.elp_before_mm,
        result.elp_after_mm,
    )
    if not _all_finite(tuple(row_values)) or not _all_finite(scalar_values):
        raise AnalysisError("completed optical results must contain only finite numeric values")

    peak = find_distance_peak(actual_grid, tuple(row.vsotf for row in result.rows))
    if abs(result.distance_peak_retina_d - peak.defocus_d) > 1e-12:
        raise AnalysisError("stored distance peak does not match the VSOTF curve")
    for row in result.rows:
        expected_shape = row.defocus_retina_d - result.distance_peak_retina_d
        if abs(row.defocus_shape_d - expected_shape) > 1e-12:
            raise AnalysisError("shape-recentered defocus axis is inconsistent with distance peak")

    if not result.model_hash_before.strip() or not result.model_hash_after.strip():
        raise AnalysisError("entity model hashes are required")
    if result.model_hash_before != result.model_hash_after:
        raise AnalysisError("entity model changed during through-focus analysis")
    if result.retina_position_before_mm != result.retina_position_after_mm:
        raise AnalysisError("retina position changed during through-focus analysis")
    if result.iol_position_before_mm != result.iol_position_after_mm:
        raise AnalysisError("IOL position changed during through-focus analysis")
    if result.elp_before_mm != result.elp_after_mm:
        raise AnalysisError("ELP changed during through-focus analysis")

    if min(result.cornea_footprint_mm, result.stop_footprint_mm, result.iol_footprint_mm) < 0:
        raise AnalysisError("optical footprints must be non-negative")
    if result.iol_optical_diameter_mm <= 0:
        raise AnalysisError("IOL optical diameter must be positive")
    if result.iol_footprint_mm > result.iol_optical_diameter_mm:
        raise AnalysisError("IOL footprint exceeds optical diameter")
    if result.unintended_vignetting:
        raise AnalysisError("unintended vignetting was detected")

    if len(result.artifacts.psf_paths) != 3 or not all(result.artifacts.required_paths()):
        raise ExportError("mandatory artifact path is missing")
    if require_files:
        missing = [path for path in result.artifacts.required_paths() if not Path(path).is_file()]
        if missing:
            raise ExportError(f"mandatory artifact file missing: {missing}")
    if not result.completed:
        raise AnalysisError("result is not marked completed")


def _validate_matched_config_invariants(mono: NominalConfig, edof: NominalConfig) -> None:
    invariant_fields = (
        "carrier_id",
        "base_id",
        "cornea_id",
        "platform_id",
        "pupil_mm",
        "carrier_lock_hash",
        "wavelength_nm",
        "field_deg",
        "cornea_decentration_mm",
        "iol_decentration_mm",
        "iol_tilt_deg",
        "micro_monovision_defocus_d",
    )
    for field_name in invariant_fields:
        if getattr(mono, field_name) != getattr(edof, field_name):
            raise AnalysisError(f"matched pair differs in {field_name}")
    if any(
        value is not None
        for value in (
            mono.residual_id,
            mono.residual_sha256,
            mono.residual_validation_policy_id,
        )
    ):
        raise AnalysisError("matched MONO config must not contain residual provenance")
    if not all(
        value
        for value in (
            edof.residual_id,
            edof.residual_sha256,
            edof.residual_validation_policy_id,
        )
    ):
        raise AnalysisError("matched EDOF config is missing residual provenance")


def matched_pair_delta(mono: ConfigResult, edof: ConfigResult) -> MatchedPairDelta:
    validate_completed_result(mono)
    validate_completed_result(edof)
    if mono.config.pair_key != edof.config.pair_key:
        raise AnalysisError("results are not a matched pair")
    if mono.config.optic_state != OpticState.MONO or edof.config.optic_state != OpticState.EDOF:
        raise AnalysisError("matched delta expects MONO then EDOF")
    _validate_matched_config_invariants(mono.config, edof.config)
    mono_scalar = {
        "distance_peak_retina_d": mono.distance_peak_retina_d,
        "c40_um": mono.aberrations.c40_um,
        "c60_um": mono.aberrations.c60_um,
        "hoa_rms_um": mono.aberrations.hoa_rms_um,
    }
    edof_scalar = {
        "distance_peak_retina_d": edof.distance_peak_retina_d,
        "c40_um": edof.aberrations.c40_um,
        "c60_um": edof.aberrations.c60_um,
        "hoa_rms_um": edof.aberrations.hoa_rms_um,
    }
    return MatchedPairDelta(
        mono.config.pair_key,
        mono.config.config_id,
        edof.config.config_id,
        matched_numeric_delta(edof_scalar, mono_scalar),
    )
