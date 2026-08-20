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

# v2 restores the gate domain frozen by TASK-007 Web review. v1 incorrectly
# promoted actual-eye aperture-limited SSAG Mode-0 low-order readback to a hard gate.
VALIDATION_SCHEMA_VERSION = 2
VALIDATION_PUPIL_MM = 5.0
VALIDATION_INDEX_NAME = "VALIDATION_INDEX.json"
CURRENT_POINTER_NAME = "CURRENT.json"
NORMATIVE_LOW_ORDER_GATE_DOMAIN = "STD_IOL_EYE_2024_EPD6_imported_residual_readback"
ACTUAL_EYE_LOW_ORDER_ROLE = "diagnostic_only_aperture_limited_mode0"
TASK007_CONSOLIDATED_REVIEW_HASH = (
    "f325533cb86910399a2290426cdfe52215968450edb3a82c62553c38a8aaecc6"
)


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


def _numerical_gate_pass(
    *,
    standard_policy_passed: bool,
    mono_ray_health_passed: bool,
    edof_ray_health_passed: bool,
) -> bool:
    """Return the TASK-007 normative numerical gate for an exact carrier/residual pair.

    Actual-eye SSAG Mode-0 piston/defocus is deliberately absent: TASK-007
    consolidated Web review froze that readback as diagnostic-only because it is
    aperture-limited. The low-order hard gate lives in STD_IOL_EYE_2024 EPD6.
    """

    return (
        bool(standard_policy_passed)
        and bool(mono_ray_health_passed)
        and bool(edof_ray_health_passed)
    )


def _read_actual_carrier_geometry(
    session: ZosSession,
    carrier_path: Path,
) -> tuple[float, float, float]:
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
        or payload.get("normative_low_order_gate_domain") != NORMATIVE_LOW_ORDER_GATE_DOMAIN
        or payload.get("actual_eye_low_order_role") != ACTUAL_EYE_LOW_ORDER_ROLE
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


def _write_current_pointer(
    validation_root: Path,
    record_path: Path,
    payload: dict[str, object],
) -> Path:
    carrier_id = payload.get("carrier_id")
    if not isinstance(carrier_id, str) or not carrier_id.strip():
        raise ResidualExtensionValidationError("validation payload lacks carrier_id")
    pointer_path = validation_root / carrier_id / CURRENT_POINTER_NAME
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer = {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "carrier_id": carrier_id,
        "carrier_sha256": payload.get("carrier_sha256"),
        "residual_id": payload.get("residual_id"),
        "residual_sha256": payload.get("residual_sha256"),
        "policy_id": payload.get("policy_id"),
        "passed": payload.get("passed"),
        "record_relative_path": record_path.relative_to(validation_root).as_posix(),
        "record_sha256": sha256_file(record_path),
    }
    pointer_path.write_text(
        json.dumps(pointer, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return pointer_path


def _write_validation_index(validation_root: Path) -> Path:
    rows: list[dict[str, object]] = []
    for pointer_path in sorted(validation_root.glob(f"*/{CURRENT_POINTER_NAME}")):
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        if not isinstance(pointer, dict):
            raise ResidualExtensionValidationError(
                f"validation current pointer is not an object: {pointer_path}"
            )
        relative = pointer.get("record_relative_path")
        expected_record_sha = pointer.get("record_sha256")
        if not isinstance(relative, str) or not isinstance(expected_record_sha, str):
            raise ResidualExtensionValidationError(
                f"validation current pointer is incomplete: {pointer_path}"
            )
        record_path = validation_root / relative
        if not record_path.is_file() or sha256_file(record_path) != expected_record_sha:
            raise ResidualExtensionValidationError(
                f"validation current pointer record mismatch: {pointer_path}"
            )
        payload = json.loads(record_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ResidualExtensionValidationError(
                f"validation record root is not an object: {record_path}"
            )
        if (
            payload.get("schema_version") != pointer.get("schema_version")
            or payload.get("carrier_id") != pointer.get("carrier_id")
            or payload.get("carrier_sha256") != pointer.get("carrier_sha256")
            or payload.get("residual_sha256") != pointer.get("residual_sha256")
            or payload.get("policy_id") != pointer.get("policy_id")
            or payload.get("passed") != pointer.get("passed")
        ):
            raise ResidualExtensionValidationError(
                f"validation current pointer identity mismatch: {pointer_path}"
            )
        rows.append(
            {
                "carrier_id": payload.get("carrier_id"),
                "base_id": payload.get("base_id"),
                "cornea_id": payload.get("cornea_id"),
                "platform_id": payload.get("platform_id"),
                "carrier_sha256": payload.get("carrier_sha256"),
                "residual_id": payload.get("residual_id"),
                "residual_sha256": payload.get("residual_sha256"),
                "policy_id": payload.get("policy_id"),
                "normative_low_order_gate_domain": payload.get("normative_low_order_gate_domain"),
                "actual_eye_low_order_role": payload.get("actual_eye_low_order_role"),
                "actual_policy_passed_diagnostic": payload.get(
                    "actual_policy_passed_diagnostic"
                ),
                "standard_policy_passed": payload.get("standard_policy_passed"),
                "passed": payload.get("passed"),
                "record_relative_path": relative,
                "record_sha256": expected_record_sha,
                "current_pointer_relative_path": pointer_path.relative_to(validation_root).as_posix(),
                "current_pointer_sha256": sha256_file(pointer_path),
            }
        )
    index = validation_root / VALIDATION_INDEX_NAME
    index.write_text(
        json.dumps(
            {
                "schema_version": VALIDATION_SCHEMA_VERSION,
                "normative_low_order_gate_domain": NORMATIVE_LOW_ORDER_GATE_DOMAIN,
                "actual_eye_low_order_role": ACTUAL_EYE_LOW_ORDER_ROLE,
                "task007_consolidated_review_hash": TASK007_CONSOLIDATED_REVIEW_HASH,
                "validation_count": len(rows),
                "all_passed": bool(rows) and all(row["passed"] is True for row in rows),
                "records": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return index


def _refresh_validation_summary(
    validation_root: Path,
    record_path: Path,
    payload: dict[str, object],
) -> None:
    _write_current_pointer(validation_root, record_path, payload)
    _write_validation_index(validation_root)


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
    """Validate exact carrier bytes with the exact frozen residual before production.

    TASK-007 frozen Web review defines the normative low-order hard gate in
    STD_IOL_EYE_2024 EPD6. Actual-eye SSAG Mode-0 piston/defocus is preserved as
    diagnostic-only. Actual-eye MONO/EDOF EPD5 ray health remains a hard gate.
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
    validation_root_path = Path(validation_root).resolve()
    root = (
        validation_root_path
        / carrier_id
        / f"v{VALIDATION_SCHEMA_VERSION}_{carrier_sha[:12]}_{residual_sha256[:12]}"
    )
    root.mkdir(parents=True, exist_ok=True)
    record_path = root / "VALIDATION.json"
    reusable = _load_reusable_validation(
        record_path,
        carrier_sha256=carrier_sha,
        residual_sha256=residual_sha256,
    )
    if reusable is not None:
        _refresh_validation_summary(validation_root_path, record_path, reusable)
        return reusable

    r_ant, r_post, q_ant = _read_actual_carrier_geometry(session, mono_path)
    actual_edof = root / "ACTUAL_EDOF.zmx"
    std_mono = root / "STD_MONO.zmx"
    std_edof = root / "STD_EDOF.zmx"

    apply_grid_sag_residual(session, mono_path, candidate, residual_path, actual_edof)
    actual_readback = readback_residual_low_order(session, mono_path, actual_edof, candidate)
    actual_policy_passed_diagnostic = _policy_pass(actual_readback)
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
    apply_grid_sag_residual(session, std_mono, candidate, residual_path, std_edof)
    standard_readback = readback_residual_low_order(session, std_mono, std_edof, candidate)
    standard_policy_passed = _policy_pass(standard_readback)

    passed = _numerical_gate_pass(
        standard_policy_passed=standard_policy_passed,
        mono_ray_health_passed=bool(mono_health["passed"]),
        edof_ray_health_passed=bool(edof_health["passed"]),
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
        "carrier_geometry": {"r_ant_mm": r_ant, "r_post_mm": r_post, "q_ant": q_ant},
        "residual_id": residual_id,
        "residual_sha256": residual_sha256,
        "policy_id": RESIDUAL_VALIDATION_546_V1.policy_id,
        "task007_consolidated_review_hash": TASK007_CONSOLIDATED_REVIEW_HASH,
        "normative_low_order_gate_domain": NORMATIVE_LOW_ORDER_GATE_DOMAIN,
        "actual_eye_low_order_role": ACTUAL_EYE_LOW_ORDER_ROLE,
        "piston_tolerance_um": RESIDUAL_VALIDATION_546_V1.piston_tolerance_um,
        "global_defocus_tolerance_d": RESIDUAL_VALIDATION_546_V1.global_defocus_tolerance_d,
        "validation_pupil_mm": VALIDATION_PUPIL_MM,
        "actual_readback": asdict(actual_readback),
        "standard_readback": asdict(standard_readback),
        "actual_policy_passed_diagnostic": actual_policy_passed_diagnostic,
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
    _refresh_validation_summary(validation_root_path, record_path, payload)
    return payload


def validation_passed(payload: dict[str, object]) -> bool:
    return payload.get("passed") is True
