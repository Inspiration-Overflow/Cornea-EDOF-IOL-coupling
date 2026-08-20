from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path

from .carrier_q_zos import build_physical_carrier_in_standard_eye
from .grid_sag_residual import apply_grid_sag_residual, readback_residual_low_order
from .residual_payload import (
    RadialResidualCandidate,
    build_hoa_residual_candidate,
    build_rad_residual_candidate,
    build_wfs_residual_candidate,
)
from .residual_policy import RESIDUAL_VALIDATION_546_V1
from .store import sha256_file
from .zos import SequentialEditor, ZosSession

VALIDATION_SCHEMA_VERSION = 1
VALIDATION_PUPIL_MM = 5.0


class ResidualExtensionValidationError(RuntimeError):
    pass


def _candidate(platform_id: str) -> RadialResidualCandidate:
    builders = {
        "WFS": build_wfs_residual_candidate,
        "RAD": build_rad_residual_candidate,
        "HOA": build_hoa_residual_candidate,
    }
    builder = builders.get(str(platform_id))
    if builder is None:
        raise ResidualExtensionValidationError(f"unknown residual platform: {platform_id}")
    candidate = builder()
    candidate.validate()
    return candidate


def _ray_health(
    session: ZosSession,
    path: Path,
    pupil_mm: float = VALIDATION_PUPIL_MM,
) -> dict[str, object]:
    session.system.LoadFile(str(path.resolve()), False)
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(pupil_mm)
    image_surface = int(session.system.LDE.NumberOfSurfaces) - 1
    tool = session.system.Tools.OpenBatchRayTrace()
    try:
        rays = tool.CreateNormUnpol(
            9,
            session.zosapi.Tools.RayTrace.RaysType.Real,
            image_surface,
        )
        rays.ClearData()
        opd_enum = session.zosapi.Tools.RayTrace.OPDMode
        opd_none = getattr(opd_enum, "None", getattr(opd_enum, "None_", None))
        if opd_none is None:
            raise ResidualExtensionValidationError("installed API exposes no OPDMode.None")
        for py in (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0):
            rays.AddRay(1, 0.0, 0.0, 0.0, py, opd_none)
        tool.RunAndWaitForCompletion()
        rays.StartReadingResults()
        failures: list[dict[str, object]] = []
        for index in range(9):
            values = tuple(rays.ReadNextResult())
            success = bool(values[0])
            error = int(values[2])
            vignette = int(values[3])
            if not success or error != 0 or vignette != 0:
                failures.append(
                    {"ray": index, "success": success, "error": error, "vignette": vignette}
                )
        return {"pupil_mm": float(pupil_mm), "passed": not failures, "failures": failures}
    finally:
        close = getattr(tool, "Close", None)
        if callable(close):
            close()


def _policy_pass(readback) -> bool:
    return (
        abs(float(readback.measured_piston_um))
        <= RESIDUAL_VALIDATION_546_V1.piston_tolerance_um
        and abs(float(readback.measured_global_defocus_d))
        <= RESIDUAL_VALIDATION_546_V1.global_defocus_tolerance_d
    )


def _read_actual_carrier_geometry(
    session: ZosSession,
    carrier_path: Path,
) -> tuple[float, float, float]:
    """Read Rant/Rpost/Q from the exact saved actual-eye carrier bytes."""

    session.system.LoadFile(str(carrier_path.resolve()), False)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise ResidualExtensionValidationError(
            f"actual-eye carrier validation expects 7 surfaces, got {int(lde.NumberOfSurfaces)}"
        )
    ant = lde.GetSurfaceAt(4)
    post = lde.GetSurfaceAt(5)
    r_ant = float(ant.Radius)
    r_post = float(post.Radius)
    q_ant = float(ant.Conic)
    q_post = float(post.Conic)
    values = (r_ant, r_post, q_ant, q_post)
    if not all(math.isfinite(value) for value in values):
        raise ResidualExtensionValidationError("actual-eye carrier R/Q readback is non-finite")
    if abs(r_post + r_ant) > 1.0e-8:
        raise ResidualExtensionValidationError(
            f"actual-eye carrier is not symmetric biconvex: Rant={r_ant}, Rpost={r_post}"
        )
    if abs(q_post) > 1.0e-10:
        raise ResidualExtensionValidationError(
            f"actual-eye carrier posterior conic drifted from zero: {q_post}"
        )
    return r_ant, r_post, q_ant


def _load_reusable_validation(
    record_path: Path,
    *,
    carrier_sha256: str,
    residual_sha256: str,
) -> dict[str, object] | None:
    if not record_path.is_file():
        return None
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    if (
        payload.get("schema_version") != VALIDATION_SCHEMA_VERSION
        or payload.get("carrier_sha256") != carrier_sha256
        or payload.get("residual_sha256") != residual_sha256
        or payload.get("policy_id") != RESIDUAL_VALIDATION_546_V1.policy_id
        or payload.get("passed") is not True
    ):
        return None
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    for item in artifacts.values():
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        expected = item.get("sha256")
        if not isinstance(name, str) or not isinstance(expected, str):
            return None
        artifact = record_path.parent / name
        if not artifact.is_file() or sha256_file(artifact) != expected:
            return None
    payload["reused"] = True
    return payload


def ensure_frozen_residual_carrier_validation(
    session: ZosSession,
    *,
    project_dir: str | Path,
    standard_eye_path: str | Path,
    carrier_id: str,
    base_id: str,
    cornea_id: str,
    platform_id: str,
    carrier_path: str | Path,
    residual_id: str,
    residual_sha256: str,
    validation_root: str | Path,
) -> dict[str, object]:
    """Validate exact saved carrier bytes with exact frozen residual before EDOF production.

    The numerical hard gates intentionally match TASK-007 consolidated calibration:
    actual-eye and standard-eye piston/global-defocus readback plus EPD5 actual-eye
    MONO/EDOF ray health.  Power-envelope coverage is descriptive only; these exact-
    carrier replay checks determine whether production may continue.
    """

    project_root = Path(project_dir).resolve()
    standard_eye = Path(standard_eye_path).resolve()
    mono_path = Path(carrier_path).resolve()
    if not carrier_id.strip() or not base_id.strip() or not cornea_id.strip() or not platform_id.strip():
        raise ResidualExtensionValidationError("carrier validation identity is incomplete")
    if not mono_path.is_file():
        raise ResidualExtensionValidationError(f"carrier model is missing: {mono_path}")
    if not standard_eye.is_file():
        raise ResidualExtensionValidationError(f"standard eye is missing: {standard_eye}")

    carrier_sha = sha256_file(mono_path)
    residual_path = project_root / "models" / "assets" / "residuals" / f"{residual_id}.DAT"
    if not residual_path.is_file():
        raise ResidualExtensionValidationError(f"frozen residual is missing: {residual_id}")
    actual_residual_sha = sha256_file(residual_path)
    if actual_residual_sha != residual_sha256:
        raise ResidualExtensionValidationError(
            f"frozen residual SHA mismatch for {platform_id}: "
            f"expected {residual_sha256}, got {actual_residual_sha}"
        )

    candidate = _candidate(platform_id)
    root = Path(validation_root).resolve() / carrier_id / f"{carrier_sha[:12]}_{residual_sha256[:12]}"
    root.mkdir(parents=True, exist_ok=True)
    record_path = root / "VALIDATION.json"
    reusable = _load_reusable_validation(
        record_path,
        carrier_sha256=carrier_sha,
        residual_sha256=residual_sha256,
    )
    if reusable is not None:
        return reusable

    r_ant, r_post, q_ant = _read_actual_carrier_geometry(session, mono_path)
    actual_edof = root / "ACTUAL_EDOF.zmx"
    std_mono = root / "STD_MONO.zmx"
    std_edof = root / "STD_EDOF.zmx"

    apply_grid_sag_residual(
        session,
        mono_path,
        candidate,
        residual_path,
        actual_edof,
    )
    actual_readback = readback_residual_low_order(
        session,
        mono_path,
        actual_edof,
        candidate,
    )
    actual_policy_passed = _policy_pass(actual_readback)
    mono_health = _ray_health(session, mono_path)
    edof_health = _ray_health(session, actual_edof)

    build_physical_carrier_in_standard_eye(
        session,
        standard_eye,
        radius_ant_mm=r_ant,
        radius_post_mm=r_post,
        q=q_ant,
    )
    SequentialEditor(session.system, session.zosapi).save_as(std_mono)
    apply_grid_sag_residual(
        session,
        std_mono,
        candidate,
        residual_path,
        std_edof,
    )
    standard_readback = readback_residual_low_order(
        session,
        std_mono,
        std_edof,
        candidate,
    )
    standard_policy_passed = _policy_pass(standard_readback)

    passed = (
        actual_policy_passed
        and standard_policy_passed
        and bool(mono_health["passed"])
        and bool(edof_health["passed"])
    )
    artifacts = {
        "actual_edof": {"name": actual_edof.name, "sha256": sha256_file(actual_edof)},
        "standard_mono": {"name": std_mono.name, "sha256": sha256_file(std_mono)},
        "standard_edof": {"name": std_edof.name, "sha256": sha256_file(std_edof)},
    }
    payload: dict[str, object] = {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "carrier_id": carrier_id,
        "base_id": base_id,
        "cornea_id": cornea_id,
        "platform_id": platform_id,
        "carrier_sha256": carrier_sha,
        "carrier_geometry": {
            "r_ant_mm": r_ant,
            "r_post_mm": r_post,
            "q_ant": q_ant,
        },
        "residual_id": residual_id,
        "residual_sha256": residual_sha256,
        "policy_id": RESIDUAL_VALIDATION_546_V1.policy_id,
        "piston_tolerance_um": RESIDUAL_VALIDATION_546_V1.piston_tolerance_um,
        "global_defocus_tolerance_d": RESIDUAL_VALIDATION_546_V1.global_defocus_tolerance_d,
        "validation_pupil_mm": VALIDATION_PUPIL_MM,
        "actual_readback": asdict(actual_readback),
        "standard_readback": asdict(standard_readback),
        "actual_policy_passed": actual_policy_passed,
        "standard_policy_passed": standard_policy_passed,
        "mono_ray_health": mono_health,
        "edof_ray_health": edof_health,
        "artifacts": artifacts,
        "passed": passed,
        "reused": False,
    }
    record_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def validation_passed(payload: dict[str, object]) -> bool:
    return payload.get("passed") is True
