from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1

RESIDUAL_SEED_VERSION = "TASK007_RESIDUAL_SEEDS_546_v1"
RESIDUAL_NORMALIZATION_RADIUS_MM = 5.15 / 2.0
RESIDUAL_SAMPLE_STEP_MM = 0.005


@dataclass(frozen=True)
class WfsPatentSeed:
    """Public phase-shift embodiment used only as a WFS-like mechanism seed."""

    r1_mm: float = 0.55
    r2_mm: float = 0.65
    r3_mm: float = 0.87
    r4_mm: float = 1.05
    r5_mm: float = 1.11
    optic_radius_mm: float = 3.00
    delta1_um: float = -1.02
    delta2_um: float = 0.59


WFS_PATENT_SEED = WfsPatentSeed()


@dataclass(frozen=True)
class RadPowerZone:
    inner_radius_mm: float
    outer_radius_mm: float
    start_power_d: float
    amplitude_d: float
    cosine_order: int = 1

    @property
    def end_power_d(self) -> float:
        # For the frozen order-1 patent equation, P(re) = S - A.
        return self.start_power_d - self.amplitude_d


RAD_PATENT_ZONES: tuple[RadPowerZone, ...] = (
    RadPowerZone(0.00, 0.50, -0.25, 0.00),
    RadPowerZone(0.50, 0.90, -0.25, -3.25),
    RadPowerZone(0.90, 1.10, 3.00, 3.25),
    RadPowerZone(1.10, 1.40, -0.25, -0.25),
    RadPowerZone(1.40, 2.50, 0.00, 0.00),
)
RAD_OPTIC_RADIUS_MM = 3.00


@dataclass(frozen=True)
class HoaBenchSeed:
    """Bench-derived 4th/6th-order HOA seed, not a manufacturing prescription."""

    wavelength_um: float = 0.546
    source_power_d: float = 22.0
    zernike_radius_mm: float = 1.00
    core_radius_mm: float = 0.90
    transition_outer_radius_mm: float = 1.10
    z4_waves: float = -0.49
    z6_waves: float = 0.46

    @property
    def z4_um(self) -> float:
        return self.z4_waves * self.wavelength_um

    @property
    def z6_um(self) -> float:
        return self.z6_waves * self.wavelength_um


HOA_BENCH_SEED = HoaBenchSeed()


@dataclass(frozen=True)
class LowOrderFit:
    piston_um: float
    global_defocus_d: float


def _validate_radius(radius_mm: float, *, maximum_mm: float) -> float:
    radius = float(radius_mm)
    if not math.isfinite(radius) or radius < 0.0 or radius > maximum_mm:
        raise ValueError(f"radius must be finite and inside [0, {maximum_mm}] mm")
    return radius


def wfs_raw_surface_sag_um(radius_mm: float, seed: WfsPatentSeed = WFS_PATENT_SEED) -> float:
    """Return the residual-only phase-shift sag from the public WFS patent embodiment.

    The patent's base asphere is intentionally excluded because TASK-007 controls base
    spherical aberration through the matched carrier Q(P). With one controlled base
    profile, the residual outer plateau is continued through the 3 mm optic radius.
    r5 is retained as provenance for the patent's base-zone boundary.
    """

    radius = _validate_radius(radius_mm, maximum_mm=seed.optic_radius_mm)
    if radius < seed.r1_mm:
        return 0.0
    if radius < seed.r2_mm:
        fraction = (radius - seed.r1_mm) / (seed.r2_mm - seed.r1_mm)
        return fraction * seed.delta1_um
    if radius < seed.r3_mm:
        return seed.delta1_um
    if radius < seed.r4_mm:
        fraction = (radius - seed.r3_mm) / (seed.r4_mm - seed.r3_mm)
        return seed.delta1_um + fraction * seed.delta2_um
    return seed.delta1_um + seed.delta2_um


def wfs_raw_opd_um(radius_mm: float) -> float:
    """First-order OPD equivalent of the WFS physical sag on the controlled carrier."""

    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    index_step = scaffold.refractive_index - scaffold.surrounding_index
    return index_step * wfs_raw_surface_sag_um(radius_mm)


def rad_relative_power_d(radius_mm: float) -> float:
    """Frozen continuous RAD-like relative sagittal power seed in diopters."""

    radius = _validate_radius(radius_mm, maximum_mm=RAD_OPTIC_RADIUS_MM)
    for zone in RAD_PATENT_ZONES:
        if zone.inner_radius_mm <= radius <= zone.outer_radius_mm:
            if zone.cosine_order != 1:
                raise ValueError("TASK-007 RAD seed currently freezes cosine order 1 only")
            if zone.outer_radius_mm == zone.inner_radius_mm:
                return zone.start_power_d
            u = radius * radius
            u0 = zone.inner_radius_mm * zone.inner_radius_mm
            u1 = zone.outer_radius_mm * zone.outer_radius_mm
            phase = math.pi * (u - u0) / (u1 - u0)
            return zone.start_power_d + 0.5 * zone.amplitude_d * (math.cos(phase) - 1.0)
    # The public seed is zero outside 2.5 mm; the controlled optic extends to 3 mm.
    return 0.0


def _integrate_rad_zone_opd_um(zone: RadPowerZone, radius_mm: float) -> float:
    """Integrate P(r) r dr for a partial or complete order-1 RAD zone.

    With P in diopters and r in millimetres, the integral is numerically in micrometres
    of wavefront OPD because 1 D = 1/m.
    """

    if zone.cosine_order != 1:
        raise ValueError("TASK-007 RAD OPD integration currently supports cosine order 1 only")
    upper = min(max(radius_mm, zone.inner_radius_mm), zone.outer_radius_mm)
    if upper <= zone.inner_radius_mm:
        return 0.0
    u0 = zone.inner_radius_mm * zone.inner_radius_mm
    u1 = zone.outer_radius_mm * zone.outer_radius_mm
    u = upper * upper
    delta_u = u - u0
    width_u = u1 - u0
    if width_u <= 0.0:
        raise ValueError("RAD zone must have positive radial width")
    sine_term = width_u / math.pi * math.sin(math.pi * delta_u / width_u)
    return 0.5 * (
        (zone.start_power_d - 0.5 * zone.amplitude_d) * delta_u
        + 0.5 * zone.amplitude_d * sine_term
    )


def rad_raw_opd_um(radius_mm: float) -> float:
    """Integrate the RAD-like power seed into a radial wavefront OPD target."""

    radius = _validate_radius(radius_mm, maximum_mm=RAD_OPTIC_RADIUS_MM)
    total = 0.0
    for zone in RAD_PATENT_ZONES:
        if radius <= zone.inner_radius_mm:
            break
        total += _integrate_rad_zone_opd_um(zone, radius)
        if radius <= zone.outer_radius_mm:
            break
    return total


def hoa_window(radius_mm: float, seed: HoaBenchSeed = HOA_BENCH_SEED) -> float:
    """Quintic C2 taper from the HOA core into the aberration-neutral periphery."""

    radius = _validate_radius(radius_mm, maximum_mm=RAD_OPTIC_RADIUS_MM)
    if radius <= seed.core_radius_mm:
        return 1.0
    if radius >= seed.transition_outer_radius_mm:
        return 0.0
    t = (radius - seed.core_radius_mm) / (
        seed.transition_outer_radius_mm - seed.core_radius_mm
    )
    smoothstep = 10.0 * t**3 - 15.0 * t**4 + 6.0 * t**5
    return 1.0 - smoothstep


def osa_primary_spherical(rho: float) -> float:
    """OSA/ANSI normalized Z(4,0) radial polynomial on the unit disk."""

    if not math.isfinite(rho) or rho < 0.0 or rho > 1.0:
        raise ValueError("normalized radius must lie inside the unit disk")
    return math.sqrt(5.0) * (6.0 * rho**4 - 6.0 * rho**2 + 1.0)


def osa_secondary_spherical(rho: float) -> float:
    """OSA/ANSI normalized Z(6,0) radial polynomial on the unit disk."""

    if not math.isfinite(rho) or rho < 0.0 or rho > 1.0:
        raise ValueError("normalized radius must lie inside the unit disk")
    return math.sqrt(7.0) * (
        20.0 * rho**6 - 30.0 * rho**4 + 12.0 * rho**2 - 1.0
    )


def hoa_raw_opd_um(radius_mm: float, seed: HoaBenchSeed = HOA_BENCH_SEED) -> float:
    """Window a bounded opposite-sign Z4/Z6 combination into the central HOA zone.

    The bench coefficients are used as a mechanism seed for a simplified 4th/6th-order
    surrogate. The real commercial optic also contains additional terms, so these
    coefficients are not treated as a manufacturing prescription or a hard achieved
    whole-eye Zernike target. Local OpticStudio validation remains mandatory.
    """

    radius = _validate_radius(radius_mm, maximum_mm=RAD_OPTIC_RADIUS_MM)
    rho = min(radius / seed.zernike_radius_mm, 1.0)
    central_opd = (
        seed.z4_um * osa_primary_spherical(rho)
        + seed.z6_um * osa_secondary_spherical(rho)
    )
    return hoa_window(radius, seed) * central_opd


def sample_radial_profile(
    profile: Callable[[float], float],
    *,
    radius_max_mm: float = RESIDUAL_NORMALIZATION_RADIUS_MM,
    step_mm: float = RESIDUAL_SAMPLE_STEP_MM,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if radius_max_mm <= 0.0 or step_mm <= 0.0:
        raise ValueError("radial sampling radius and step must be positive")
    ratio = radius_max_mm / step_mm
    if not math.isclose(ratio, round(ratio), rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError("radial sample step must divide the requested radius exactly")
    radii = tuple(round(index * step_mm, 12) for index in range(round(ratio) + 1))
    values = tuple(float(profile(radius)) for radius in radii)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("radial profile samples must be finite")
    return radii, values


def fit_piston_and_global_defocus(
    radii_mm: Sequence[float],
    opd_um: Sequence[float],
) -> LowOrderFit:
    """Area-weighted least-squares fit of W(r)=piston+0.5*F*r^2.

    r is in mm, W in micrometres and F in diopters; these units are consistent because
    0.5 * 1 D * (1 mm)^2 = 0.5 micrometres of paraxial wavefront OPD.
    """

    if len(radii_mm) != len(opd_um) or len(radii_mm) < 3:
        raise ValueError("low-order fit requires matching radial arrays with at least 3 points")
    previous = -math.inf
    m00_terms: list[float] = []
    m01_terms: list[float] = []
    m11_terms: list[float] = []
    v0_terms: list[float] = []
    v1_terms: list[float] = []
    for raw_radius, raw_opd in zip(radii_mm, opd_um, strict=True):
        radius = float(raw_radius)
        value = float(raw_opd)
        if not math.isfinite(radius) or not math.isfinite(value) or radius < 0.0:
            raise ValueError("low-order fit samples must be finite and radii non-negative")
        if radius <= previous:
            raise ValueError("low-order fit radii must be strictly increasing")
        previous = radius
        weight = radius
        defocus_basis = 0.5 * radius * radius
        m00_terms.append(weight)
        m01_terms.append(weight * defocus_basis)
        m11_terms.append(weight * defocus_basis * defocus_basis)
        v0_terms.append(weight * value)
        v1_terms.append(weight * value * defocus_basis)

    m00 = math.fsum(m00_terms)
    m01 = math.fsum(m01_terms)
    m11 = math.fsum(m11_terms)
    v0 = math.fsum(v0_terms)
    v1 = math.fsum(v1_terms)
    determinant = m00 * m11 - m01 * m01
    if determinant <= 0.0:
        raise ValueError("low-order fit is singular")
    piston = (v0 * m11 - v1 * m01) / determinant
    defocus = (m00 * v1 - m01 * v0) / determinant
    return LowOrderFit(piston_um=piston, global_defocus_d=defocus)


def remove_piston_and_global_defocus(
    radii_mm: Sequence[float],
    opd_um: Sequence[float],
) -> tuple[tuple[float, ...], LowOrderFit]:
    fit = fit_piston_and_global_defocus(radii_mm, opd_um)
    normalized = tuple(
        float(value) - fit.piston_um - 0.5 * fit.global_defocus_d * float(radius) ** 2
        for radius, value in zip(radii_mm, opd_um, strict=True)
    )
    return normalized, fit
