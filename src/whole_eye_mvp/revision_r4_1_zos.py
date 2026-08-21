from __future__ import annotations

from pathlib import Path

from .domain import PlatformId
from .revision_r4_1_rad_fit import R41RadPowerDiagnostic, fit_r4_1_rad_mechanism
from .revision_r4_zos import (
    R4PlatformPilotResult,
    RevisionR4ZosError,
    audit_r4_model,
    build_r4_analytical_carrier,
    build_r4_binary4_edof,
    build_r4_binary4_mono,
    build_r4_grid_sag_comparator,
    read_r4_mechanism,
    read_rad_power_profile,
    run_r4_platform_pilot,
)
from .carrier_q_zos import CarrierQSolution
from .zos import ZosSession


def run_r4_1_platform_pilot(
    session: ZosSession,
    standard_eye_path: str | Path,
    platform_id: str,
    q_solution: CarrierQSolution,
    output_dir: str | Path,
) -> tuple[R4PlatformPilotResult, tuple[R41RadPowerDiagnostic, ...] | None]:
    """Run one R4.1 platform; only RAD changes its fit objective.

    WFS and HOA deliberately reuse the accepted R4 implementation unchanged so the
    new evidence is a same-HEAD regression of all three mechanisms. RAD is rebuilt
    from the same analytical carrier but fits the source-locked P(r) quantity before
    the unchanged OPD/serialization/optical audits are applied.
    """

    if platform_id != PlatformId.RAD.value:
        return (
            run_r4_platform_pilot(
                session,
                standard_eye_path,
                platform_id,
                q_solution,
                output_dir,
            ),
            None,
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
    fit, power_diagnostics = fit_r4_1_rad_mechanism(
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
    if fit.engineering_target_passed and not mechanism.engineering_target_passed:
        raise RevisionR4ZosError(
            "R4.1 RAD serialized Binary4 readback lost the fitted OPD fidelity"
        )

    grid_sag_path = build_r4_grid_sag_comparator(
        session,
        analytical_path,
        PlatformId.RAD.value,
        root,
    )
    rad_power = read_rad_power_profile(session, mono_path, edof_path)
    result = R4PlatformPilotResult(
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
    return result, power_diagnostics


def rad_powp_sign_consistent(result: R4PlatformPilotResult) -> bool:
    """Hard identity check with no new numeric tolerance.

    For every sampled non-zero source target, measured POWP relative power must keep
    the same sign. Magnitude fidelity remains a manual Web review item in R4.1.
    """

    readback = result.rad_power_readback
    if readback is None:
        raise ValueError("RAD POWP sign check requires RAD power readback")
    return all(
        point.target_relative_power_d == 0.0
        or point.relative_power_d * point.target_relative_power_d > 0.0
        for point in readback.points
    )
