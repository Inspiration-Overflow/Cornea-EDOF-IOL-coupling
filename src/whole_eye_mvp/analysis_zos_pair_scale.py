from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .analysis import (
    AberrationSummary,
    ConfigArtifacts,
    ConfigResult,
    summarize_mtfa_curve,
    with_shape_axis,
)
from .analysis_zos import (
    AnalysisZosError,
    MtfAcquisitionContract,
    ZosMtfaGridAnalysisBackend,
    _assert_loaded_nominal_model,
    _write_plots,
    _write_through_focus_csv,
    acquire_footprints,
    capture_entity_snapshot,
)
from .b0_zos import object_thickness_for_defocus_d
from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .domain import NOMINAL_MAIN_FFT_MTF_555_V2, OpticState
from .manifest import NominalConfig
from .metrics import mm_per_degree, mtfa
from .quality import settings_hash
from .store import sha256_file
from .zos import MfeEfflRunner, MfeFullHoaRunner, MfeMtfGridRunner, MfeMtfGridSettings, ZosSession

TASK009_PAIR_MONO_MTF_ACQUISITION = MtfAcquisitionContract(
    contract_id="TASK009_MFE_MTFA_GRID1_PAIR_MONO_SCALE_v2",
    frequency_axis="direct_0_to_60_cpd_via_paired_MONO_EFFL",
)
EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH = (
    "f7f1551eeb3b339bf8b3353067786e1e7a943fd4383d58ee1f33fc4f59c8c21d"
)


@dataclass(frozen=True, slots=True)
class PairAngularScaleReference:
    pair_key: str
    mono_config_id: str
    reference_effl_mm: float
    mm_per_degree: float
    model_sha256: str
    entity_fingerprint: str

    def validate(self) -> None:
        if not self.pair_key or not self.mono_config_id:
            raise ValueError("pair angular-scale reference requires pair/config identity")
        if not math.isfinite(self.reference_effl_mm) or self.reference_effl_mm <= 0:
            raise ValueError("pair reference EFFL must be finite and positive")
        if not math.isfinite(self.mm_per_degree) or self.mm_per_degree <= 0:
            raise ValueError("pair reference mm/degree must be finite and positive")
        if not self.model_sha256 or not self.entity_fingerprint:
            raise ValueError("pair angular-scale reference requires model/entity provenance")


def frequencies_for_pair_reference(
    reference_effl_mm: float,
    cpd_grid: tuple[float, ...],
) -> tuple[float, ...]:
    scale = mm_per_degree(reference_effl_mm)
    if not cpd_grid or any(not math.isfinite(float(value)) or value < 0 for value in cpd_grid):
        raise ValueError("cpd grid must be non-empty, finite, and non-negative")
    return tuple(float(value / scale) for value in cpd_grid)


def measure_pair_mono_reference(
    session: ZosSession,
    project_dir: Path,
    carrier_asset_sha256: Mapping[str, str],
    residual_asset_sha256: Mapping[str, str],
    config: NominalConfig,
    destination: Path,
) -> PairAngularScaleReference:
    """Measure one residual-free MONO reference EFFL for a frozen matched pair.

    The helper deliberately reuses the already validated formal-model preparation code,
    but it does not run any MTF analysis. The returned scale is then held fixed for both
    MONO and EDOF states and for every through-focus plane in that pair.
    """

    if config.optic_state != OpticState.MONO:
        raise AnalysisZosError("pair angular-scale reference must come from the MONO manifest row")
    if any(
        value is not None
        for value in (
            config.residual_id,
            config.residual_sha256,
            config.residual_validation_policy_id,
            config.residual_validation_policy_hash,
        )
    ):
        raise AnalysisZosError("pair angular-scale MONO reference unexpectedly carries residual")

    preparer = ZosMtfaGridAnalysisBackend(
        session,
        Path(project_dir),
        carrier_asset_sha256,
        residual_asset_sha256,
        sampling=NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
    )
    destination = Path(destination).resolve()
    preparer._prepare_model(config, destination)
    model_sha = sha256_file(destination)
    session.system.LoadFile(str(destination), False)
    _assert_loaded_nominal_model(session, config)
    snapshot = capture_entity_snapshot(session)
    effl_mm = MfeEfflRunner(session.system, session.zosapi).run().effective_focal_length_mm
    reference = PairAngularScaleReference(
        pair_key=config.pair_key,
        mono_config_id=config.config_id,
        reference_effl_mm=float(effl_mm),
        mm_per_degree=mm_per_degree(float(effl_mm)),
        model_sha256=model_sha,
        entity_fingerprint=snapshot.fingerprint,
    )
    reference.validate()
    return reference


@dataclass(slots=True)
class ZosMtfaPairScaleAnalysisBackend(ZosMtfaGridAnalysisBackend):
    """TASK-009 backend using one residual-free MONO angular scale per matched pair."""

    pair_reference_effl_mm: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        normalized = {str(key): float(value) for key, value in self.pair_reference_effl_mm.items()}
        if not normalized:
            raise ValueError("paired-MONO backend requires at least one pair reference EFFL")
        if any(not key or not math.isfinite(value) or value <= 0 for key, value in normalized.items()):
            raise ValueError("pair reference EFFLs must have non-empty keys and positive finite values")
        self.pair_reference_effl_mm = normalized
        if TASK009_PAIR_MONO_MTF_ACQUISITION.contract_hash != EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH:
            raise RuntimeError("paired-MONO MTF acquisition contract hash drifted")

    def _reference_effl_mm(self, config: NominalConfig) -> float:
        try:
            return float(self.pair_reference_effl_mm[config.pair_key])
        except KeyError as exc:
            raise AnalysisZosError(
                f"missing paired-MONO angular-scale reference for {config.pair_key}"
            ) from exc

    def run_config(self, config: NominalConfig, output_dir: Path, run_id: str) -> ConfigResult:
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        model_path = output / "model.zmx"
        self._prepare_model(config, model_path)
        model_hash_before = sha256_file(model_path)

        self.session.system.LoadFile(str(model_path), False)
        _assert_loaded_nominal_model(self.session, config)
        before = capture_entity_snapshot(self.session)
        footprints = acquire_footprints(self.session)

        object_surface = self.session.system.LDE.GetSurfaceAt(0)
        saved_object_thickness = float(object_surface.Thickness)
        state_effl_mm = float(
            MfeEfflRunner(self.session.system, self.session.zosapi).run().effective_focal_length_mm
        )
        reference_effl_mm = self._reference_effl_mm(config)
        pair_scale = mm_per_degree(reference_effl_mm)
        state_scale = mm_per_degree(state_effl_mm)
        settings = NOMINAL_MAIN_FFT_MTF_555_V2
        cpd_grid = settings.mtf_frequency_grid_cpd()
        frequencies_mm = frequencies_for_pair_reference(reference_effl_mm, cpd_grid)
        runner = MfeMtfGridRunner(self.session.system, self.session.zosapi)
        defocus_grid = settings.defocus_grid()
        mtfa_values: list[float] = []
        fixed_columns: dict[float, list[float]] = {
            frequency: [] for frequency in settings.mtf_sample_frequencies_cpd
        }
        zero_mtf: tuple[float, ...] | None = None
        runtime_meta: dict[str, object] | None = None
        try:
            for defocus_d in defocus_grid:
                object_surface.Thickness = object_thickness_for_defocus_d(
                    defocus_d,
                    infinity_thickness_mm=saved_object_thickness,
                )
                result = runner.run(
                    MfeMtfGridSettings(
                        frequencies_cyc_per_mm=frequencies_mm,
                        sampling_grid_size=self.sampling,
                        operand_type="MTFA",
                        grid=TASK009_PAIR_MONO_MTF_ACQUISITION.grid,
                        data_type=TASK009_PAIR_MONO_MTF_ACQUISITION.data_type,
                    )
                )
                avg = tuple(float(value) for value in result.values)
                if runtime_meta is None:
                    runtime_meta = {
                        "acquisition_contract_id": TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id,
                        "acquisition_contract_hash": TASK009_PAIR_MONO_MTF_ACQUISITION.contract_hash,
                        "production_operand": result.operand_type,
                        "grid": result.grid,
                        "data_type": result.data_type,
                        "sampling_grid_size": result.sampling_grid_size,
                        "sampling_index": result.sampling_index,
                        "parameter_headers": result.parameter_headers,
                        "frequency_min_cycles_per_mm": frequencies_mm[0],
                        "frequency_max_cycles_per_mm": frequencies_mm[-1],
                        "frequency_count": len(frequencies_mm),
                        "cpd_min": cpd_grid[0],
                        "cpd_max": cpd_grid[-1],
                        "cpd_count": len(cpd_grid),
                        "frequency_scale_mode": "paired_MONO_EFFL",
                    }
                mtfa_values.append(mtfa(cpd_grid, avg, max_cpd=settings.mtfa_max_cpd))
                for frequency, values in fixed_columns.items():
                    index = round(frequency / settings.mtf_frequency_step_cpd)
                    values.append(avg[index])
                if abs(defocus_d) <= 1.0e-12:
                    zero_mtf = avg
        finally:
            object_surface.Thickness = saved_object_thickness

        if float(object_surface.Thickness) != saved_object_thickness:
            raise AnalysisZosError("OBJECT thickness was not restored after through-focus acquisition")
        if zero_mtf is None or runtime_meta is None:
            raise AnalysisZosError("paired-MONO MTFA Grid=1 through-focus acquisition is incomplete")

        rows = with_shape_axis(
            defocus_grid,
            tuple(mtfa_values),
            tuple(
                tuple(fixed_columns[frequency])
                for frequency in settings.mtf_sample_frequencies_cpd
            ),
        )
        summary = summarize_mtfa_curve(rows)
        hoa = MfeFullHoaRunner(self.session.system, self.session.zosapi).run()
        after = capture_entity_snapshot(self.session)
        model_hash_after = sha256_file(model_path)

        through_focus_csv = output / "through_focus.csv"
        through_focus_plot = output / "through_focus_mtfa.png"
        mtf_plot = output / "mtf_at_zero_d.png"
        _write_through_focus_csv(through_focus_csv, rows)
        _write_plots(rows, cpd_grid, zero_mtf, through_focus_plot, mtf_plot)

        self.diagnostics[config.config_id] = {
            "sampling": self.sampling,
            "pair_key": config.pair_key,
            "pair_reference_effl_mm": reference_effl_mm,
            "pair_mm_per_degree": pair_scale,
            "state_diagnostic_effl_mm": state_effl_mm,
            "state_diagnostic_mm_per_degree": state_scale,
            "state_to_pair_effl_ratio": state_effl_mm / reference_effl_mm,
            "target_frequencies_cycles_per_mm": frequencies_mm,
            "mtf_runtime": runtime_meta,
            "footprint_failures": footprints.failures,
            "entity_before": asdict(before),
            "entity_after": asdict(after),
            "hoa_settings_id": hoa.settings_id,
            "hoa_settings_hash": hoa.settings_hash,
        }

        return ConfigResult(
            config=config,
            run_id=run_id,
            rows=rows,
            distance_peak_retina_d=float(summary["distance_peak_retina_d"]),
            distance_peak_mtfa=float(summary["distance_peak_mtfa"]),
            mtfa_at_zero_d=float(summary["mtfa_at_zero_d"]),
            dof50_far_d=summary["dof50_far_d"],
            dof50_near_d=summary["dof50_near_d"],
            dof50_width_d=float(summary["dof50_width_d"]),
            dof50_far_censored=bool(summary["dof50_far_censored"]),
            dof50_near_censored=bool(summary["dof50_near_censored"]),
            tf_mtfa_mean=float(summary["tf_mtfa_mean"]),
            peak_search_censored=bool(summary["peak_search_censored"]),
            aberrations=AberrationSummary(hoa.c40_um, hoa.c60_um, hoa.hoa_rms_um),
            analysis_settings_hash=settings_hash(settings),
            hoa_settings_id=hoa.settings_id,
            hoa_settings_hash=hoa.settings_hash,
            cornea_footprint_mm=footprints.cornea_footprint_mm,
            stop_footprint_mm=footprints.stop_footprint_mm,
            iol_footprint_mm=footprints.iol_footprint_mm,
            iol_optical_diameter_mm=CONTROLLED_IOL_CARRIER_546_V1.optical_diameter_mm,
            model_hash_before=model_hash_before,
            model_hash_after=model_hash_after,
            entity_fingerprint_before=before.fingerprint,
            entity_fingerprint_after=after.fingerprint,
            retina_position_before_mm=before.retina_position_mm,
            retina_position_after_mm=after.retina_position_mm,
            iol_position_before_mm=before.iol_position_mm,
            iol_position_after_mm=after.iol_position_mm,
            elp_before_mm=before.elp_mm,
            elp_after_mm=after.elp_mm,
            unintended_vignetting=footprints.unintended_vignetting,
            artifacts=ConfigArtifacts(
                str(model_path),
                str(through_focus_csv),
                str(through_focus_plot),
                str(mtf_plot),
            ),
            completed=True,
        )
