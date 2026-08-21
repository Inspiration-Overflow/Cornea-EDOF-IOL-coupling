from __future__ import annotations

from pathlib import Path

from .carrier_q_zos import CarrierQSolution
from .domain import PlatformId
from .revision_r4_1_rad_fit import fit_r4_1_rad_mechanism
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


def run_r4_1_platform_pilot(
    session: ZosSession,
    standard_eye_path: str | Path,
    platform_id: str,
    q_solution: CarrierQSolution,
    output_dir: str | Path,
) -> R4PlatformPilotResult:
    """Run one R4.1 platform; only RAD changes its fit objective.

    WFS and HOA deliberately reuse the accepted/provisional R4 implementation
    unchanged so the new evidence is a same-HEAD regression of all three
    mechanisms. RAD is rebuilt from the same analytical carrier but refits the
    already-selected `R+Q+A4` Binary4 topology to local spherical power.
    """

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
    fit = fit_r4_1_rad_mechanism(
        base_radius_mm=analytical.radius_post_mm,
        base_conic=analytical.q_post,
    )
    binary4_mono = build_r4_binary4_mono(
        session,
        analytical_path,
        PlatformId.RAD.value,
        mono_path,
    )
    # Preserve the serialized-readback fix: EDoF is an independent
    # Standard-to-Binary4 conversion from the analytical carrier.
    binary4_edof = build_r4_binary4_edof(session, analytical_path, fit, edof_path)

    # The legacy integrated-OPD readback remains useful evidence but is no longer
    # a RAD hard gate in R4.1 because that surrogate was exactly what Web review
    # rejected. The source identity is now verified by spherical POWP below.
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


def rad_powp_sign_consistent(result: R4PlatformPilotResult) -> bool:
    """Require measured POWP to keep the target sign where the target is nonzero."""

    readback = result.rad_power_readback
    if readback is None:
        raise ValueError("RAD POWP sign check requires RAD power readback")
    return all(
        point.target_relative_power_d == 0.0
        or point.relative_power_d * point.target_relative_power_d > 0.0
        for point in readback.points
    )


def rad_powp_improves_source(
    result: R4PlatformPilotResult,
    *,
    source_rms_error_d: float,
    source_max_abs_error_d: float,
) -> tuple[bool, bool]:
    """Compare R4.1 POWP magnitude errors with the rejected R4 baseline.

    This adds no new absolute acceptance threshold. R4.1 must at least improve
    both baseline error measures; final magnitude acceptance remains a Web gate.
    """

    readback = result.rad_power_readback
    if readback is None:
        raise ValueError("RAD POWP improvement check requires RAD power readback")
    return (
        readback.rms_error_d < float(source_rms_error_d),
        readback.max_abs_error_d < float(source_max_abs_error_d),
    )
