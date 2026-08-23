from __future__ import annotations

import math
from dataclasses import dataclass

from .domain import PlatformId
from .model_revision import binary4_mechanism_spec
from .revision_r4_fit import R4ZonePrescription

R5_FREEZE_ID = "MODEL-REVISION-R5-2026-08-21"
R5_1_FREEZE_ID = "MODEL-REVISION-R5.1-HOA-CONIC-SAG-INVARIANT-2026-08-21"
R5_REPRESENTATIVE_POWER_D = 20.0
R5_REPRESENTATIVE_RADIUS_MM = 12.357387811201875
R5_GLOBAL_DEFOCUS_TOLERANCE_D = 0.125


@dataclass(frozen=True, slots=True)
class R5NormalizedZone:
    zone: int
    r_inner_mm: float
    r_outer_mm: float
    delta_curvature_mm_inv: float
    delta_conic: float
    alpha_p4_native: float
    alpha_p6_native: float
    active: bool


@dataclass(frozen=True, slots=True)
class R5MechanismLock:
    platform_id: str
    surface_role: str
    selected_complexity: str
    representative_base_radius_mm: float
    representative_base_conic: float
    manufacturing_status: str
    zones: tuple[R5NormalizedZone, ...]

    def validate(self) -> None:
        platform = PlatformId(self.platform_id)
        spec = binary4_mechanism_spec(platform.value)
        if self.surface_role != spec.surface_role:
            raise ValueError("R5 surface role differs from the frozen Binary4 mechanism spec")
        if len(self.zones) != len(spec.radial_apertures_mm):
            raise ValueError("R5 zone count differs from the frozen Binary4 mechanism spec")
        if not math.isfinite(self.representative_base_radius_mm) or self.representative_base_radius_mm == 0:
            raise ValueError("R5 representative base radius must be finite and non-zero")
        if not math.isfinite(self.representative_base_conic):
            raise ValueError("R5 representative base conic must be finite")
        inner = 0.0
        for index, (zone, outer) in enumerate(
            zip(self.zones, spec.radial_apertures_mm, strict=True), start=1
        ):
            if zone.zone != index:
                raise ValueError("R5 zones must be numbered consecutively")
            if not math.isclose(zone.r_inner_mm, inner, rel_tol=0.0, abs_tol=1.0e-12):
                raise ValueError("R5 zone inner boundary mismatch")
            if not math.isclose(zone.r_outer_mm, outer, rel_tol=0.0, abs_tol=1.0e-12):
                raise ValueError("R5 zone outer boundary mismatch")
            if not all(
                math.isfinite(value)
                for value in (
                    zone.delta_curvature_mm_inv,
                    zone.delta_conic,
                    zone.alpha_p4_native,
                    zone.alpha_p6_native,
                )
            ):
                raise ValueError("R5 normalized zone parameters must be finite")
            inner = outer

        if platform == PlatformId.WFS:
            if self.selected_complexity != "R":
                raise ValueError("R5 WFS complexity must remain R")
            if any(
                abs(zone.delta_conic) > 1.0e-15
                or abs(zone.alpha_p4_native) > 1.0e-15
                or abs(zone.alpha_p6_native) > 1.0e-15
                for zone in self.zones
            ):
                raise ValueError("R5 WFS may only carry curvature deltas")
        elif platform == PlatformId.RAD:
            if self.selected_complexity != "R+Q+A4":
                raise ValueError("R5 RAD complexity must remain R+Q+A4")
            if any(abs(zone.alpha_p6_native) > 1.0e-15 for zone in self.zones):
                raise ValueError("R5 RAD A6 must remain zero")
            for zone in self.zones[4:]:
                if zone.active or any(
                    abs(value) > 1.0e-15
                    for value in (
                        zone.delta_curvature_mm_inv,
                        zone.delta_conic,
                        zone.alpha_p4_native,
                        zone.alpha_p6_native,
                    )
                ):
                    raise ValueError("R5 RAD zones 5/6 must remain neutral")
        else:
            if self.selected_complexity != "R+Q+A4+A6":
                raise ValueError("R5 HOA complexity must remain R+Q+A4+A6")
            zone = self.zones[2]
            if zone.active or any(
                abs(value) > 1.0e-15
                for value in (
                    zone.delta_curvature_mm_inv,
                    zone.delta_conic,
                    zone.alpha_p4_native,
                    zone.alpha_p6_native,
                )
            ):
                raise ValueError("R5 HOA zone 3 must remain neutral")


def _zone(
    zone: int,
    inner: float,
    outer: float,
    dc: float,
    dq: float = 0.0,
    a4: float = 0.0,
    a6: float = 0.0,
    *,
    active: bool = True,
) -> R5NormalizedZone:
    return R5NormalizedZone(zone, inner, outer, dc, dq, a4, a6, active)


# Curvature deltas are relative to the +20 D representative carrier base curvature.
# The +20 D absolute zone prescriptions are the Web-reviewed R4/R4.2 pilot values.
_WFS = R5MechanismLock(
    platform_id=PlatformId.WFS.value,
    surface_role="anterior",
    selected_complexity="R",
    representative_base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
    representative_base_conic=-9.0,
    manufacturing_status="PASS",
    zones=(
        _zone(1, 0.00, 0.55, -9.419178233005532e-05),
        _zone(2, 0.55, 0.65, -1.734198590136897e-02),
        _zone(3, 0.65, 0.87, +9.902309933150500e-05),
        _zone(4, 0.87, 1.05, +3.658607595670105e-03),
        _zone(5, 1.05, 3.00, -2.263093529214499e-06),
    ),
)

_RAD = R5MechanismLock(
    platform_id=PlatformId.RAD.value,
    surface_role="posterior",
    selected_complexity="R+Q+A4",
    representative_base_radius_mm=-R5_REPRESENTATIVE_RADIUS_MM,
    representative_base_conic=0.0,
    manufacturing_status="REVIEW",
    zones=(
        _zone(1, 0.00, 0.50, +2.0321665328883465e-03, +0.032796262113, -1.9470598e-07),
        _zone(2, 0.50, 0.90, +1.9699566298184944e-02, -0.876401226297, -0.004782893220),
        _zone(3, 0.90, 1.10, -8.464347099630155e-02, -0.999700078812, +0.013248218724),
        _zone(4, 1.10, 1.40, +1.885481317684591e-02, -0.999999985532, -0.005541252428),
        _zone(5, 1.40, 2.50, 0.0, 0.0, 0.0, 0.0, active=False),
        _zone(6, 2.50, 3.00, 0.0, 0.0, 0.0, 0.0, active=False),
    ),
)

_HOA = R5MechanismLock(
    platform_id=PlatformId.HOA.value,
    surface_role="anterior",
    selected_complexity="R+Q+A4+A6",
    representative_base_radius_mm=R5_REPRESENTATIVE_RADIUS_MM,
    representative_base_conic=0.0,
    manufacturing_status="REVIEW",
    zones=(
        _zone(
            1,
            0.00,
            0.90,
            +1.899549062173450e-01,
            -34.1538507,
            -0.0825456077,
            +0.0423302736,
        ),
        _zone(
            2,
            0.90,
            1.10,
            +2.744059849363385e-02,
            +50.0,
            +0.0365006281,
            -0.0516184660,
        ),
        _zone(3, 1.10, 3.00, 0.0, 0.0, 0.0, 0.0, active=False),
    ),
)

_LOCKS = {
    PlatformId.WFS: _WFS,
    PlatformId.RAD: _RAD,
    PlatformId.HOA: _HOA,
}


def r5_mechanism_lock(platform_id: str) -> R5MechanismLock:
    try:
        result = _LOCKS[PlatformId(platform_id)]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported R5 platform: {platform_id}") from exc
    result.validate()
    return result


def _lock_zones_for_base(
    lock: R5MechanismLock,
    *,
    base_radius_mm: float,
    base_conic: float,
    conic_sag_scaling: bool,
) -> tuple[R4ZonePrescription, ...]:
    radius = float(base_radius_mm)
    conic = float(base_conic)
    if not math.isfinite(radius) or radius == 0.0:
        raise ValueError("R5 carrier base radius must be finite and non-zero")
    if not math.isfinite(conic):
        raise ValueError("R5 carrier base conic must be finite")
    expected_sign = 1.0 if lock.surface_role == "anterior" else -1.0
    if math.copysign(1.0, radius) != expected_sign:
        raise ValueError("R5 carrier base radius sign does not match the frozen surface role")

    base_curvature = 1.0 / radius
    reference_curvature = 1.0 / lock.representative_base_radius_mm
    output: list[R4ZonePrescription] = []
    for zone in lock.zones:
        curvature = base_curvature + zone.delta_curvature_mm_inv
        if curvature == 0.0 or math.copysign(1.0, curvature) != expected_sign:
            raise ValueError("R5 normalized curvature produced an invalid zone radius")
        delta_conic = zone.delta_conic
        if conic_sag_scaling and zone.delta_conic != 0.0:
            # R5.1: the conic sag term Q*r^4/(8*R_zone^3) carries the frozen
            # mechanism contribution.  Porting the absolute offset to another
            # carrier power rescales that term as R_zone^-3, so restore it by
            # scaling the offset with (R_zone/R_zone_at_freeze)^3.
            reference_zone_curvature = (
                reference_curvature + zone.delta_curvature_mm_inv
            )
            radius_ratio = reference_zone_curvature / curvature
            delta_conic = zone.delta_conic * radius_ratio**3
        output.append(
            R4ZonePrescription(
                zone=zone.zone,
                r_inner_mm=zone.r_inner_mm,
                r_outer_mm=zone.r_outer_mm,
                radius_mm=1.0 / curvature,
                conic=conic + delta_conic,
                alpha_p2_native=0.0,
                alpha_p4_native=zone.alpha_p4_native,
                alpha_p6_native=zone.alpha_p6_native,
                active=zone.active,
            )
        )
    return tuple(output)


def r5_zones_for_carrier(
    platform_id: str,
    *,
    base_radius_mm: float,
    base_conic: float,
) -> tuple[R4ZonePrescription, ...]:
    """Apply the frozen R5 normalized residual to one power-specific carrier.

    R6/R7 tests whether these power-independent curvature/conic deltas and native
    p4/p6 coefficients remain mechanism-faithful across the actual carrier range.
    This function does not refit any parameter.
    """

    lock = r5_mechanism_lock(platform_id)
    return _lock_zones_for_base(
        lock,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
        conic_sag_scaling=False,
    )


def r5_1_zones_for_carrier(
    platform_id: str,
    *,
    base_radius_mm: float,
    base_conic: float,
) -> tuple[R4ZonePrescription, ...]:
    """R5.1 application of the same frozen residual with HOA conic sag scaling.

    WFS/RAD prescriptions are bit-identical to ``r5_zones_for_carrier``.  Only
    the HOA conic offsets are rescaled to preserve the frozen r^4 sag term at
    other carrier powers; curvature deltas and native p4/p6 coefficients stay
    exactly as frozen.
    """

    lock = r5_mechanism_lock(platform_id)
    return _lock_zones_for_base(
        lock,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
        conic_sag_scaling=PlatformId(platform_id) is PlatformId.HOA,
    )
