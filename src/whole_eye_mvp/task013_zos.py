from __future__ import annotations

import math
import shutil
from dataclasses import asdict
from pathlib import Path

from .analysis_zos import (
    AnalysisZosError,
    _assert_loaded_nominal_model,
    _candidate,
    capture_entity_snapshot,
)
from .analysis_zos_pair_scale import (
    PairAngularScaleReference,
    ZosMtfaPairScaleAnalysisBackend,
)
from .carrier_focus_zos import measure_actual_eye_q_focus, solve_actual_eye_radius_at_q
from .carrier_q_zos import (
    Q_REPLAY_SA_TOLERANCE_UM,
    build_physical_carrier_in_standard_eye,
    measure_standard_eye_c40,
    solve_q_for_platform,
)
from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .carrier_zos import ActualEyeCarrierPowerResult
from .carriers import SA_TARGETS_UM, CarrierKey, ProvisionalCarrier
from .domain import NOMINAL_MAIN_FFT_MTF_555_V2, OpticState
from .grid_sag_residual import apply_grid_sag_residual
from .manifest import NominalConfig
from .metrics import mm_per_degree
from .residual_extension_validation_zos import (
    ensure_frozen_residual_carrier_validation,
    validation_passed,
)
from .standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from .store import sha256_file
from .task013_native_reference import NATIVE_REFERENCE_CORNEA_ID, validate_native_carrier
from .zos import MfeEfflRunner, SequentialEditor, ZosSession

TASK013_MAX_PQ_RECHECK_CYCLES = 2


class Task013ZosError(RuntimeError):
    pass


def solve_native_platform_carrier(
    session: ZosSession,
    standard_eye_path: str | Path,
    *,
    base_id: str,
    platform_id: str,
    p0: ActualEyeCarrierPowerResult,
    p0_path: str | Path,
    destination: str | Path,
    recheck_dir: str | Path,
) -> tuple[ProvisionalCarrier, dict[str, object]]:
    """Solve one N0 carrier with the already-validated TASK-007 P→Q(P) route."""

    current_power = float(p0.power_d)
    current_radius = float(p0.radius_ant_mm)
    p0_path = Path(p0_path)
    working_path = p0_path
    recheck_root = Path(recheck_dir)
    recheck_root.mkdir(parents=True, exist_ok=True)

    q_solution = solve_q_for_platform(
        session,
        standard_eye_path,
        platform_id=platform_id,
        source_power_d=current_power,
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
    )
    current_q = float(q_solution.q)
    focus = measure_actual_eye_q_focus(session, working_path, q=current_q)
    cycles: list[dict[str, object]] = []

    for cycle in range(1, TASK013_MAX_PQ_RECHECK_CYCLES + 1):
        if not focus.recheck_required:
            break
        refocused = recheck_root / f"PQ_{base_id}_{NATIVE_REFERENCE_CORNEA_ID}_{platform_id}_C{cycle}.zmx"
        radius_result = solve_actual_eye_radius_at_q(
            session,
            working_path,
            q=current_q,
            initial_radius_mm=current_radius,
            destination=refocused,
        )
        current_radius = float(radius_result.solved_radius_mm)
        current_power = float(radius_result.power_d)
        q_solution = solve_q_for_platform(
            session,
            standard_eye_path,
            platform_id=platform_id,
            source_power_d=current_power,
            radius_ant_mm=current_radius,
            radius_post_mm=-current_radius,
        )
        current_q = float(q_solution.q)
        focus = measure_actual_eye_q_focus(session, refocused, q=current_q)
        cycles.append(
            {
                "cycle": cycle,
                "radius_solve": asdict(radius_result),
                "q": current_q,
                "achieved_sa_um": q_solution.achieved_sa_um,
                "actual_eye_focus": asdict(focus),
            }
        )
        working_path = refocused

    if focus.recheck_required:
        raise Task013ZosError(
            f"{base_id}/{NATIVE_REFERENCE_CORNEA_ID}/{platform_id} did not converge "
            "within two P-Q rechecks"
        )

    final_focus = measure_actual_eye_q_focus(session, working_path, q=current_q)
    if final_focus.recheck_required:
        raise Task013ZosError(
            f"{base_id}/{NATIVE_REFERENCE_CORNEA_ID}/{platform_id} final focus replay "
            "crossed the P-Q recheck gate"
        )

    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    SequentialEditor(session.system, session.zosapi).save_as(destination_path)

    session.system.LoadFile(str(destination_path.resolve()), False)
    ant = session.system.LDE.GetSurfaceAt(4)
    post = session.system.LDE.GetSurfaceAt(5)
    if (
        abs(float(ant.Radius) - current_radius) > 1.0e-9
        or abs(float(post.Radius) + current_radius) > 1.0e-9
        or abs(float(ant.Conic) - current_q) > 1.0e-12
        or abs(float(post.Conic)) > 1.0e-12
    ):
        raise Task013ZosError(
            f"{base_id}/{NATIVE_REFERENCE_CORNEA_ID}/{platform_id} final actual-eye R/Q replay mismatch"
        )

    build_physical_carrier_in_standard_eye(
        session,
        standard_eye_path,
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
        q=0.0,
        zero_hoa_reference=True,
    )
    reference_c40 = measure_standard_eye_c40(session).c40_um
    build_physical_carrier_in_standard_eye(
        session,
        standard_eye_path,
        radius_ant_mm=current_radius,
        radius_post_mm=-current_radius,
        q=current_q,
    )
    candidate_c40 = measure_standard_eye_c40(session).c40_um
    replay_sa = float(candidate_c40 - reference_c40)
    target_sa = float(SA_TARGETS_UM[platform_id])
    if abs(replay_sa - target_sa) > Q_REPLAY_SA_TOLERANCE_UM:
        raise Task013ZosError(
            f"{base_id}/{NATIVE_REFERENCE_CORNEA_ID}/{platform_id} final standard-eye SA "
            f"replay failed: {replay_sa:.6g} µm vs {target_sa:.6g} µm"
        )

    carrier = ProvisionalCarrier(
        key=CarrierKey(base_id, NATIVE_REFERENCE_CORNEA_ID, platform_id),
        power_d=current_power,
        q=current_q,
        q_source_power_d=current_power,
        r_ant_mm=current_radius,
        r_post_mm=-current_radius,
        center_thickness_mm=CONTROLLED_IOL_CARRIER_546_V1.center_thickness_mm,
        material="MODEL_N1460",
        iol_position_mm=4.5,
        achieved_sa_um=replay_sa,
    )
    validate_native_carrier(carrier)
    evidence = {
        "carrier": asdict(carrier),
        "p0_power_d": p0.power_d,
        "p0_radius_ant_mm": p0.radius_ant_mm,
        "p0_sha256": sha256_file(p0_path),
        "recheck_cycles": cycles,
        "final_focus": asdict(final_focus),
        "standard_eye_sa_target_um": target_sa,
        "standard_eye_sa_replay_um": replay_sa,
        "carrier_sha256": sha256_file(destination_path),
    }
    return carrier, evidence


def _set_config_pupil_and_save(
    session: ZosSession,
    config: NominalConfig,
    destination: Path,
) -> None:
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(config.pupil_mm)
    _assert_loaded_nominal_model(session, config)
    SequentialEditor(session.system, session.zosapi).save_as(destination)


def prepare_task013_model(
    session: ZosSession,
    project_dir: str | Path,
    carrier_dir: str | Path,
    carrier_asset_sha256: dict[str, str],
    residual_asset_sha256: dict[str, str],
    config: NominalConfig,
    destination: str | Path,
) -> Path:
    """Materialize one N0 config model and persist the config pupil in the .zmx file."""

    project_root = Path(project_dir).resolve()
    carrier_root = Path(carrier_dir).resolve()
    output = Path(destination).resolve()
    carrier = carrier_root / f"{config.carrier_id}.zmx"
    expected_carrier_sha = carrier_asset_sha256.get(config.carrier_id)
    if not carrier.is_file() or not expected_carrier_sha:
        raise Task013ZosError(f"TASK-013 carrier asset is missing: {config.carrier_id}")
    if sha256_file(carrier) != expected_carrier_sha:
        raise Task013ZosError(f"TASK-013 carrier SHA mismatch: {config.carrier_id}")

    output.parent.mkdir(parents=True, exist_ok=True)
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
            raise Task013ZosError("TASK-013 MONO config unexpectedly carries residual provenance")
        shutil.copy2(carrier, output)
    elif config.optic_state == OpticState.EDOF:
        if not all(
            value
            for value in (
                config.residual_id,
                config.residual_sha256,
                config.residual_validation_policy_id,
                config.residual_validation_policy_hash,
            )
        ):
            raise Task013ZosError("TASK-013 EDOF config lacks residual provenance")
        residual = (
            project_root
            / "models"
            / "assets"
            / "residuals"
            / f"{config.residual_id}.DAT"
        )
        expected_residual_sha = residual_asset_sha256.get(config.platform_id)
        if (
            not residual.is_file()
            or not expected_residual_sha
            or sha256_file(residual) != expected_residual_sha
            or sha256_file(residual) != config.residual_sha256
        ):
            raise Task013ZosError(f"TASK-013 residual SHA mismatch: {config.platform_id}")

        validation = ensure_frozen_residual_carrier_validation(
            session,
            project_dir=project_root,
            standard_eye_path=project_root / STANDARD_EYE_RELATIVE_PATH,
            carrier_id=config.carrier_id,
            base_id=config.base_id,
            cornea_id=config.cornea_id,
            platform_id=config.platform_id,
            carrier_path=carrier,
            residual_id=str(config.residual_id),
            residual_sha256=str(config.residual_sha256),
            validation_root=(
                project_root
                / "models"
                / "task013_native_reference"
                / "residual_validations"
            ),
        )
        if not validation_passed(validation):
            raise SystemExit(
                "TASK-013 exact-carrier frozen-residual validation failed before EDOF "
                f"production: {config.carrier_id}"
            )

        apply_grid_sag_residual(
            session,
            carrier,
            _candidate(config.platform_id),
            residual,
            output,
        )
    else:
        raise Task013ZosError(f"unknown TASK-013 optic state: {config.optic_state}")

    session.system.LoadFile(str(output), False)
    _set_config_pupil_and_save(session, config, output)
    return output


def measure_task013_pair_mono_reference(
    session: ZosSession,
    project_dir: str | Path,
    carrier_dir: str | Path,
    carrier_asset_sha256: dict[str, str],
    residual_asset_sha256: dict[str, str],
    config: NominalConfig,
    destination: str | Path,
) -> PairAngularScaleReference:
    if config.optic_state != OpticState.MONO:
        raise Task013ZosError("TASK-013 pair reference must use the matched MONO config")
    destination_path = prepare_task013_model(
        session,
        project_dir,
        carrier_dir,
        carrier_asset_sha256,
        residual_asset_sha256,
        config,
        destination,
    )
    model_sha = sha256_file(destination_path)
    session.system.LoadFile(str(destination_path), False)
    _assert_loaded_nominal_model(session, config)
    snapshot = capture_entity_snapshot(session)
    effl_mm = float(MfeEfflRunner(session.system, session.zosapi).run().effective_focal_length_mm)
    reference = PairAngularScaleReference(
        pair_key=config.pair_key,
        mono_config_id=config.config_id,
        reference_effl_mm=effl_mm,
        mm_per_degree=mm_per_degree(effl_mm),
        model_sha256=model_sha,
        entity_fingerprint=snapshot.fingerprint,
    )
    reference.validate()
    return reference


class Task013PairScaleAnalysisBackend(ZosMtfaPairScaleAnalysisBackend):
    """TASK-009 production backend pointed at the independent TASK-013 carrier archive."""

    def __init__(
        self,
        session: ZosSession,
        project_dir: str | Path,
        carrier_dir: str | Path,
        carrier_asset_sha256: dict[str, str],
        residual_asset_sha256: dict[str, str],
        *,
        pair_reference_effl_mm: dict[str, float],
        sampling: int = NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
    ) -> None:
        self.task013_carrier_dir = Path(carrier_dir).resolve()
        super().__init__(
            session,
            Path(project_dir).resolve(),
            carrier_asset_sha256,
            residual_asset_sha256,
            sampling=sampling,
            pair_reference_effl_mm=pair_reference_effl_mm,
        )

    def _prepare_model(self, config: NominalConfig, destination: Path) -> None:
        prepare_task013_model(
            self.session,
            self.project_dir,
            self.task013_carrier_dir,
            dict(self.carrier_asset_sha256),
            dict(self.residual_asset_sha256),
            config,
            destination,
        )

    def run_config(self, config: NominalConfig, output_dir: Path, run_id: str):
        result = super().run_config(config, output_dir, run_id)
        if not math.isclose(
            float(config.pupil_mm),
            float(self.session.system.SystemData.Aperture.ApertureValue),
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise AnalysisZosError("TASK-013 runtime pupil differs from config identity")
        return result
