from __future__ import annotations

from pathlib import Path

from .carrier_q_zos import CarrierQSolution
from .domain import PlatformId
from .revision_r4_2_rad_fit import fit_r4_2_rad_mechanism
from .revision_r4_zos import (
    R4PlatformPilotResult,
    audit_r4_model,
    build_r4_analytical_carrier,
    build_r4_binary4_edof,
    build_r4_binary4_mono,
    build_r4_grid_sag_comparator,
    read_r4_mechanism,
    read_rad_power_profile,
    run_r4_platform_pilot,
)
from .zos import ZosSession


def run_r4_2_platform_pilot(
    session: ZosSession,
    standard_eye_path: str | Path,
    platform_id: str,
    q_solution: CarrierQSolution,
    output_dir: str | Path,
) -> R4PlatformPilotResult:
    """Run one R4.2 platform; only RAD adds source low-order consistency."""

    if platform_id != PlatformId.RAD.value:
        return run_r4_platform_pilot(
            session,
            standard_eye_path,
            platform_id,
            q_solution,
            output_dir,
        )

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    analytical_path = root / "R4_ANALYTICAL_MONO_RAD.zmx"
    mono_path = root / "R4_BINARY4_MONO_RAD.zmx"
    edof_path = root / "R4_BINARY4_EDOF_RAD.zmx"

    analytical = build_r4_analytical_carrier(
        session,
        standard_eye_path,
        PlatformId.RAD.value,
        q_solution,
        analytical_path,
    )
    fit = fit_r4_2_rad_mechanism(
        base_radius_mm=analytical.radius_post_mm,
        base_conic=analytical.q_post,
    )
    binary4_mono = build_r4_binary4_mono(
        session,
        analytical_path,
        PlatformId.RAD.value,
        mono_path,
    )
    binary4_edof = build_r4_binary4_edof(session, analytical_path, fit, edof_path)

    mechanism = read_r4_mechanism(
        session,
        mono_path,
        edof_path,
        PlatformId.RAD.value,
    )
    grid_sag_path = build_r4_grid_sag_comparator(
        session,
        analytical_path,
        PlatformId.RAD.value,
        root,
    )
    rad_power = read_rad_power_profile(session, mono_path, edof_path)
    return R4PlatformPilotResult(
        platform_id=PlatformId.RAD.value,
        analytical=analytical,
        fit=fit,
        binary4_mono=binary4_mono,
        binary4_edof=binary4_edof,
        grid_sag_path=str(grid_sag_path.resolve()),
        mechanism_readback=mechanism,
        rad_power_readback=rad_power,
        mono_audit=audit_r4_model(session, mono_path),
        binary4_edof_audit=audit_r4_model(session, edof_path),
        grid_sag_edof_audit=audit_r4_model(session, grid_sag_path),
    )
