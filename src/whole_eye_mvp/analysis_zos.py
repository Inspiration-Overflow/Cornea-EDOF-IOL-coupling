from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .analysis import (
    AberrationSummary,
    ConfigArtifacts,
    ConfigResult,
    summarize_mtfa_curve,
    with_shape_axis,
)
from .b0_zos import object_thickness_for_defocus_d
from .base_assets import IMAGE_ROLE, STOP_ROLE
from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .carrier_zos import TASK007_CARRIER_ANT_ROLE, TASK007_CARRIER_POST_ROLE
from .cornea_zos import FIXED_CORNEA_POST_ROLE
from .domain import NOMINAL_MAIN_FFT_MTF_555_V2, OpticState
from .grid_sag_residual import apply_grid_sag_residual
from .manifest import NominalConfig
from .metrics import mm_per_degree, mtfa, resample_fft_mtf_to_cpd
from .quality import settings_hash
from .ref_mono import symmetric_biconvex_power_d
from .residual_payload import (
    RadialResidualCandidate,
    build_hoa_residual_candidate,
    build_rad_residual_candidate,
    build_wfs_residual_candidate,
)
from .store import sha256_file
from .zos import (
    FftMtfRunner,
    FftMtfSettings,
    MfeEfflRunner,
    MfeFullHoaRunner,
    ZosSession,
)


class AnalysisZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EntitySnapshot:
    fingerprint: str
    retina_position_mm: float
    iol_position_mm: float
    elp_mm: float
    carrier_power_d: float
    radius_ant_mm: float
    radius_post_mm: float
    q_ant: float
    q_post: float


@dataclass(frozen=True, slots=True)
class FootprintReadback:
    cornea_footprint_mm: float
    stop_footprint_mm: float
    iol_footprint_mm: float
    unintended_vignetting: bool
    failures: tuple[dict[str, object], ...]


def _candidate(platform: str) -> RadialResidualCandidate:
    builders = {
        "WFS": build_wfs_residual_candidate,
        "RAD": build_rad_residual_candidate,
        "HOA": build_hoa_residual_candidate,
    }
    try:
        return builders[platform]()
    except KeyError as exc:
        raise AnalysisZosError(f"unknown platform: {platform}") from exc


def _set_epd(session: ZosSession, pupil_mm: float) -> None:
    if pupil_mm not in NOMINAL_MAIN_FFT_MTF_555_V2.pupils_mm:
        raise AnalysisZosError(f"pupil {pupil_mm:g} mm is outside the frozen nominal set")
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(pupil_mm)


def _require_cycles_per_mm(session: ZosSession) -> None:
    units = getattr(session.system.SystemData, "Units", None)
    value = getattr(units, "MTFUnits", None)
    if value is None:
        raise AnalysisZosError("installed API exposes no SystemData.Units.MTFUnits")
    text = str(value).casefold().replace("_", "")
    if "millimeter" in text or "millimetre" in text:
        return
    try:
        if int(value) == 0:
            return
    except (TypeError, ValueError):
        pass
    raise AnalysisZosError(f"TASK-009 requires cycles/mm MTF units; got {value!r}")


def _assert_loaded_nominal_model(session: ZosSession, config: NominalConfig) -> None:
    settings = NOMINAL_MAIN_FFT_MTF_555_V2
    if config.wavelength_nm != settings.wavelength_nm:
        raise AnalysisZosError("manifest wavelength differs from active main-analysis settings")
    if config.field_deg != 0.0:
        raise AnalysisZosError("TASK-009 nominal field must be zero")
    if any(
        value != 0.0
        for value in (
            config.cornea_decentration_mm,
            config.iol_decentration_mm,
            config.iol_tilt_deg,
            config.micro_monovision_defocus_d,
        )
    ):
        raise AnalysisZosError("TASK-009 nominal alignment/monovision invariants are not zero")
    wavelength_nm = float(session.system.SystemData.Wavelengths.GetWavelength(1).Wavelength) * 1000.0
    if abs(wavelength_nm - settings.wavelength_nm) > 1.0e-6:
        raise AnalysisZosError(
            f"loaded model wavelength is {wavelength_nm:.12g} nm, expected {settings.wavelength_nm:g}"
        )
    _require_cycles_per_mm(session)
    _set_epd(session, config.pupil_mm)


def _require_role(lde: Any, surface_number: int, role: str) -> None:
    actual = str(lde.GetSurfaceAt(surface_number).Comment).strip()
    if actual != role:
        raise AnalysisZosError(
            f"surface {surface_number} role mismatch: expected {role!r}, got {actual!r}"
        )


def capture_entity_snapshot(session: ZosSession) -> EntitySnapshot:
    """Hash the in-memory physical eye while intentionally excluding OBJECT vergence."""

    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise AnalysisZosError("nominal physical carrier model must contain exactly 7 surfaces")
    _require_role(lde, 2, FIXED_CORNEA_POST_ROLE)
    _require_role(lde, 3, STOP_ROLE)
    _require_role(lde, 4, TASK007_CARRIER_ANT_ROLE)
    _require_role(lde, 5, TASK007_CARRIER_POST_ROLE)
    _require_role(lde, 6, IMAGE_ROLE)

    surfaces: list[dict[str, object]] = []
    for index in range(1, 7):
        row = lde.GetSurfaceAt(index)
        surfaces.append(
            {
                "surface": index,
                "comment": str(row.Comment),
                "type": str(getattr(row, "TypeName", "") or row.GetType()),
                "radius_mm": float(row.Radius),
                "conic": float(row.Conic),
                "thickness_mm": float(row.Thickness),
                "material": str(row.Material),
                "is_stop": bool(row.IsStop),
            }
        )
    ant = lde.GetSurfaceAt(4)
    post = lde.GetSurfaceAt(5)
    radius_ant = float(ant.Radius)
    radius_post = float(post.Radius)
    if radius_ant <= 0 or radius_post >= 0:
        raise AnalysisZosError("controlled carrier radii have unexpected signs")
    if abs(radius_ant + radius_post) > 1.0e-6:
        raise AnalysisZosError("controlled carrier lost symmetric biconvex base radii")

    retina_position = math.fsum(float(lde.GetSurfaceAt(index).Thickness) for index in range(1, 6))
    iol_position = float(lde.GetSurfaceAt(2).Thickness) + float(lde.GetSurfaceAt(3).Thickness)
    payload = {
        "surface_count": int(lde.NumberOfSurfaces),
        "stop_surface": int(lde.StopSurface),
        "surfaces_1_to_image": surfaces,
        "retina_position_mm": retina_position,
        "iol_position_from_post_cornea_mm": iol_position,
        "carrier_power_d": symmetric_biconvex_power_d(radius_ant),
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return EntitySnapshot(
        fingerprint=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        retina_position_mm=retina_position,
        iol_position_mm=iol_position,
        elp_mm=iol_position,
        carrier_power_d=float(payload["carrier_power_d"]),
        radius_ant_mm=radius_ant,
        radius_post_mm=radius_post,
        q_ant=float(ant.Conic),
        q_post=float(post.Conic),
    )


def _trace_surface_footprint(
    session: ZosSession,
    surface_number: int,
) -> tuple[float, tuple[dict[str, object], ...]]:
    tool = session.system.Tools.OpenBatchRayTrace()
    try:
        pupil_samples = (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0)
        rays = tool.CreateNormUnpol(
            len(pupil_samples),
            session.zosapi.Tools.RayTrace.RaysType.Real,
            surface_number,
        )
        rays.ClearData()
        opd_enum = session.zosapi.Tools.RayTrace.OPDMode
        opd_none = getattr(opd_enum, "None", getattr(opd_enum, "None_", None))
        if opd_none is None:
            raise AnalysisZosError("installed API exposes no OPDMode.None")
        for py in pupil_samples:
            rays.AddRay(1, 0.0, 0.0, 0.0, py, opd_none)
        tool.RunAndWaitForCompletion()
        rays.StartReadingResults()
        radii: list[float] = []
        failures: list[dict[str, object]] = []
        for index in range(len(pupil_samples)):
            values = tuple(rays.ReadNextResult())
            if len(values) < 6:
                raise AnalysisZosError(
                    f"batch ray result exposes fewer than six fields at surface {surface_number}"
                )
            success = bool(values[0])
            error = int(values[2])
            vignette = int(values[3])
            if success and error == 0:
                x = float(values[4])
                y = float(values[5])
                if math.isfinite(x) and math.isfinite(y):
                    radii.append(math.hypot(x, y))
            if not success or error != 0 or vignette != 0:
                failures.append(
                    {
                        "surface": surface_number,
                        "ray": index,
                        "success": success,
                        "error": error,
                        "vignette": vignette,
                    }
                )
        if not radii:
            raise AnalysisZosError(f"no valid real-ray footprint samples at surface {surface_number}")
        return 2.0 * max(radii), tuple(failures)
    finally:
        close = getattr(tool, "Close", None)
        if callable(close):
            close()


def acquire_footprints(session: ZosSession) -> FootprintReadback:
    cornea, a = _trace_surface_footprint(session, 1)
    stop, b = _trace_surface_footprint(session, 3)
    iol, c = _trace_surface_footprint(session, 4)
    failures = (*a, *b, *c)
    return FootprintReadback(cornea, stop, iol, bool(failures), tuple(failures))


def _write_through_focus_csv(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(records[0]))
        writer.writeheader()
        writer.writerows(records)


def _write_plots(
    rows,
    cpd_grid: tuple[float, ...],
    zero_mtf: tuple[float, ...],
    through_focus_path: Path,
    mtf_path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    from matplotlib import pyplot as plt

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot([row.defocus_retina_d for row in rows], [row.mtfa for row in rows])
    ax.set_xlabel("Retina-anchored defocus (D)")
    ax.set_ylabel("MTFa (0-60 cpd)")
    fig.tight_layout()
    fig.savefig(through_focus_path, dpi=150)
    plt.close(fig)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(cpd_grid, zero_mtf)
    ax.set_xlabel("Spatial frequency (cycles/degree)")
    ax.set_ylabel("Average modulation MTF")
    fig.tight_layout()
    fig.savefig(mtf_path, dpi=150)
    plt.close(fig)


@dataclass(slots=True)
class ZosFftMtfAnalysisBackend:
    session: ZosSession
    project_dir: Path
    carrier_asset_sha256: Mapping[str, str]
    residual_asset_sha256: Mapping[str, str]
    sampling: int = 128
    diagnostics: dict[str, dict[str, object]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.project_dir = Path(self.project_dir).resolve()
        if self.sampling not in NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_convergence_samplings:
            raise ValueError("backend sampling is outside the frozen TASK-009 convergence set")

    def _prepare_model(self, config: NominalConfig, destination: Path) -> None:
        carrier = self.project_dir / "models" / "carriers" / f"{config.carrier_id}.zmx"
        expected_carrier_sha = self.carrier_asset_sha256.get(config.carrier_id)
        if not carrier.is_file() or not expected_carrier_sha:
            raise AnalysisZosError(f"formal carrier asset is missing: {config.carrier_id}")
        if sha256_file(carrier) != expected_carrier_sha:
            raise AnalysisZosError(f"formal carrier SHA-256 mismatch: {config.carrier_id}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        if config.optic_state == OpticState.MONO:
            if any(
                value is not None
                for value in (
                    config.residual_id,
                    config.residual_sha256,
                    config.residual_validation_policy_id,
                    config.residual_validation_policy_hash,
                )
            ):
                raise AnalysisZosError("formal MONO manifest row unexpectedly carries residual provenance")
            shutil.copy2(carrier, destination)
            return

        if config.optic_state != OpticState.EDOF:
            raise AnalysisZosError(f"unknown optic state: {config.optic_state}")
        if not all(
            value
            for value in (
                config.residual_id,
                config.residual_sha256,
                config.residual_validation_policy_id,
                config.residual_validation_policy_hash,
            )
        ):
            raise AnalysisZosError("formal EDOF manifest row lacks residual provenance")
        residual = (
            self.project_dir
            / "models"
            / "assets"
            / "residuals"
            / f"{config.residual_id}.DAT"
        )
        expected_residual_sha = self.residual_asset_sha256.get(config.platform_id)
        if (
            not residual.is_file()
            or not expected_residual_sha
            or sha256_file(residual) != expected_residual_sha
            or sha256_file(residual) != config.residual_sha256
        ):
            raise AnalysisZosError(f"formal residual SHA-256 mismatch: {config.platform_id}")
        apply_grid_sag_residual(
            self.session,
            carrier,
            _candidate(config.platform_id),
            residual,
            destination,
        )

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
        effl_mm = MfeEfflRunner(self.session.system, self.session.zosapi).run().effective_focal_length_mm
        scale = mm_per_degree(effl_mm)
        requested_max_frequency = math.ceil(65.0 / scale)
        runner = FftMtfRunner(self.session.system, self.session.zosapi)
        grid = NOMINAL_MAIN_FFT_MTF_555_V2.defocus_grid()
        mtfa_values: list[float] = []
        fixed_columns: dict[float, list[float]] = {
            frequency: [] for frequency in NOMINAL_MAIN_FFT_MTF_555_V2.mtf_sample_frequencies_cpd
        }
        common_cpd: tuple[float, ...] | None = None
        zero_mtf: tuple[float, ...] | None = None
        runtime_meta: dict[str, object] | None = None
        try:
            for defocus_d in grid:
                object_surface.Thickness = object_thickness_for_defocus_d(
                    defocus_d,
                    infinity_thickness_mm=saved_object_thickness,
                )
                fft = runner.run(
                    FftMtfSettings(
                        sampling=self.sampling,
                        maximum_frequency_cyc_per_mm=float(requested_max_frequency),
                        use_polarization=NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_use_polarization,
                    )
                )
                cpd, avg = resample_fft_mtf_to_cpd(
                    fft.frequency_cycles_per_mm,
                    fft.sagittal_mtf,
                    fft.tangential_mtf,
                    effective_focal_length_mm=effl_mm,
                    max_cpd=NOMINAL_MAIN_FFT_MTF_555_V2.mtfa_max_cpd,
                    step_cpd=NOMINAL_MAIN_FFT_MTF_555_V2.mtf_frequency_step_cpd,
                )
                current_cpd = tuple(float(value) for value in cpd)
                if common_cpd is None:
                    common_cpd = current_cpd
                    runtime_meta = {
                        "analysis_api_name": fft.analysis_api_name,
                        "settings_implementation_type": fft.settings_implementation_type,
                        "sample_size_enum": fft.sample_size_enum,
                        "modulation_enum": fft.modulation_enum,
                        "data_series_count": fft.data_series_count,
                        "data_series_runtime_type": fft.data_series_runtime_type,
                        "selected_series_runtime_type": fft.selected_series_runtime_type,
                        "series_labels": fft.series_labels,
                        "x_label": fft.x_label,
                        "native_frequency_min_cycles_per_mm": fft.frequency_cycles_per_mm[0],
                        "native_frequency_max_cycles_per_mm": fft.frequency_cycles_per_mm[-1],
                        "native_frequency_count": len(fft.frequency_cycles_per_mm),
                    }
                elif current_cpd != common_cpd:
                    raise AnalysisZosError("common cpd grid changed between through-focus planes")
                mtfa_values.append(
                    mtfa(cpd, avg, max_cpd=NOMINAL_MAIN_FFT_MTF_555_V2.mtfa_max_cpd)
                )
                for frequency, values in fixed_columns.items():
                    index = round(
                        frequency / NOMINAL_MAIN_FFT_MTF_555_V2.mtf_frequency_step_cpd
                    )
                    values.append(float(avg[index]))
                if abs(defocus_d) <= 1.0e-12:
                    zero_mtf = tuple(float(value) for value in avg)
        finally:
            object_surface.Thickness = saved_object_thickness

        if common_cpd is None or zero_mtf is None or runtime_meta is None:
            raise AnalysisZosError("FFT MTF through-focus acquisition is incomplete")
        rows = with_shape_axis(
            grid,
            tuple(mtfa_values),
            tuple(
                tuple(fixed_columns[frequency])
                for frequency in NOMINAL_MAIN_FFT_MTF_555_V2.mtf_sample_frequencies_cpd
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
        _write_plots(rows, common_cpd, zero_mtf, through_focus_plot, mtf_plot)

        self.diagnostics[config.config_id] = {
            "sampling": self.sampling,
            "effective_focal_length_mm": effl_mm,
            "mm_per_degree": scale,
            "requested_max_frequency_cycles_per_mm": requested_max_frequency,
            "fft_runtime": runtime_meta,
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
            analysis_settings_hash=settings_hash(NOMINAL_MAIN_FFT_MTF_555_V2),
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
