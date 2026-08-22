from __future__ import annotations

import math
from dataclasses import replace

from .domain import PlatformId
from .revision_r4_fit import R4ZonePrescription, _conic_sag_scalar
from .revision_r5_lock import R5_REPRESENTATIVE_RADIUS_MM, r5_1_zones_for_carrier

R5_2_FREEZE_ID = "MODEL-REVISION-R5.2-HOA-BOUNDARY-SAG-INVARIANT-2026-08-21"
R5_2_RULE_DESCRIPTION = (
    "HOA applies the frozen R5.1 conic rule, then solves native A6 sequentially "
    "for active zones 1 and 2 so the complete EDOF-MONO Binary4 sag difference "
    "at each active-zone outer boundary equals the +20 D reference; zone 2 uses "
    "the already-updated zone 1 C0 state. WFS/RAD remain bit-identical to R5.1/R5."
)
_R5_2_ACTIVE_HOA_ZONE_INDICES = (0, 1)
_R5_2_SOLVE_TOLERANCE_MM = 5.0e-14


def _raw_zone_sag_mm(r_mm: float, zone: R4ZonePrescription) -> float:
    p = float(r_mm) / float(zone.r_outer_mm)
    return (
        _conic_sag_scalar(float(r_mm), zone.radius_mm, zone.conic)
        + zone.alpha_p4_native * p**4
        + zone.alpha_p6_native * p**6
    )


def r5_2_boundary_delta_z_mm(
    zones: tuple[R4ZonePrescription, ...],
    *,
    base_radius_mm: float,
    base_conic: float,
    zone_index: int,
) -> float:
    """Return complete EDOF-MONO Binary4 sag difference at one zone outer edge.

    The EDOF value includes exact conic sag, native A4/A6, and Binary4's automatic
    inter-zone C0 offsets. The MONO prescription is the degenerate carrier surface,
    so its inter-zone offsets are identically zero.
    """

    if zone_index < 0 or zone_index >= len(zones):
        raise ValueError("R5.2 zone index is outside the prescription")
    radius = float(base_radius_mm)
    conic = float(base_conic)
    if not math.isfinite(radius) or radius == 0.0:
        raise ValueError("R5.2 carrier base radius must be finite and non-zero")
    if not math.isfinite(conic):
        raise ValueError("R5.2 carrier base conic must be finite")

    offset = 0.0
    previous: R4ZonePrescription | None = None
    for index, zone in enumerate(zones[: zone_index + 1]):
        if index > 0:
            assert previous is not None
            inner = zone.r_inner_mm
            offset += _raw_zone_sag_mm(inner, previous) - _raw_zone_sag_mm(inner, zone)
        previous = zone

    selected = zones[zone_index]
    r_outer = selected.r_outer_mm
    edof = _raw_zone_sag_mm(r_outer, selected) + offset
    mono = _conic_sag_scalar(r_outer, radius, conic)
    return edof - mono


def _hoa_reference_boundary_deltas_mm() -> tuple[float, float]:
    reference = r5_1_zones_for_carrier(
        PlatformId.HOA.value,
        base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
        base_conic=0.0,
    )
    return tuple(
        r5_2_boundary_delta_z_mm(
            reference,
            base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
            base_conic=0.0,
            zone_index=index,
        )
        for index in _R5_2_ACTIVE_HOA_ZONE_INDICES
    )


def _solve_zone_a6(
    zones: tuple[R4ZonePrescription, ...],
    *,
    base_radius_mm: float,
    base_conic: float,
    zone_index: int,
    target_delta_z_mm: float,
) -> tuple[R4ZonePrescription, ...]:
    """Solve one A6 from the affine full-boundary-sag equation, without fitting."""

    zero_rows = list(zones)
    zero_rows[zone_index] = replace(zero_rows[zone_index], alpha_p6_native=0.0)
    zero = tuple(zero_rows)
    unit_rows = list(zero)
    unit_rows[zone_index] = replace(unit_rows[zone_index], alpha_p6_native=1.0)
    unit = tuple(unit_rows)

    intercept = r5_2_boundary_delta_z_mm(
        zero,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
        zone_index=zone_index,
    )
    slope = (
        r5_2_boundary_delta_z_mm(
            unit,
            base_radius_mm=base_radius_mm,
            base_conic=base_conic,
            zone_index=zone_index,
        )
        - intercept
    )
    if not math.isfinite(slope) or abs(slope) <= 1.0e-15:
        raise ValueError(f"R5.2 HOA zone {zone_index + 1} A6 equation is singular")
    solved_a6 = (float(target_delta_z_mm) - intercept) / slope
    if not math.isfinite(solved_a6):
        raise ValueError(f"R5.2 HOA zone {zone_index + 1} produced non-finite A6")

    output = list(zones)
    output[zone_index] = replace(output[zone_index], alpha_p6_native=solved_a6)
    solved = tuple(output)
    achieved = r5_2_boundary_delta_z_mm(
        solved,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
        zone_index=zone_index,
    )
    if not math.isclose(
        achieved,
        float(target_delta_z_mm),
        rel_tol=0.0,
        abs_tol=_R5_2_SOLVE_TOLERANCE_MM,
    ):
        raise ValueError(f"R5.2 HOA zone {zone_index + 1} boundary-sag solve did not close")
    return solved


def r5_2_zones_for_carrier(
    platform_id: str,
    *,
    base_radius_mm: float,
    base_conic: float,
) -> tuple[R4ZonePrescription, ...]:
    """Apply the reviewed deterministic R5.2 prescription to one carrier.

    WFS and RAD delegate unchanged to R5.1, which is already bit-identical to R5 for
    those platforms. HOA first applies R5.1 conic scaling, then uniquely solves A6 in
    zone order 1 -> 2 from the frozen +20 D complete boundary-sag invariants. No gate
    result, mechanism RMS, optimizer, or least-squares refit participates in the solve.
    """

    try:
        platform = PlatformId(platform_id)
    except ValueError as exc:
        raise ValueError(f"unsupported R5.2 platform: {platform_id}") from exc

    base = r5_1_zones_for_carrier(
        platform.value,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
    )
    if platform is not PlatformId.HOA:
        return base

    conic = float(base_conic)
    if conic != 0.0:
        raise ValueError("R5.2 HOA requires the frozen q_ant=0 carrier contract")

    radius = float(base_radius_mm)
    if radius == R5_REPRESENTATIVE_RADIUS_MM:
        # Preserve the frozen +20 D prescription bit-for-bit, including native A6.
        return base

    targets = _hoa_reference_boundary_deltas_mm()
    solved = base
    for zone_index, target in zip(_R5_2_ACTIVE_HOA_ZONE_INDICES, targets, strict=True):
        solved = _solve_zone_a6(
            solved,
            base_radius_mm=radius,
            base_conic=conic,
            zone_index=zone_index,
            target_delta_z_mm=target,
        )
    return solved
