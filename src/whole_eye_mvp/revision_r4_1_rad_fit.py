from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .domain import PlatformId
from .model_revision import binary4_mechanism_spec
from .residual_profiles import (
    RAD_OPTIC_RADIUS_MM,
    RESIDUAL_SAMPLE_STEP_MM,
    rad_raw_opd_um,
    rad_relative_power_d,
)
from .revision_r4_fit import (
    R4_REPRESENTATIVE_POWER_D,
    R4BoundaryDiagnostic,
    R4FitError,
    R4ZonePrescription,
    _boundary_diagnostics,
    _decode_zones,
    _index_step,
    _make_base_zones,
    _minimum_radicand,
    _projected_lm,
    _variables,
    _zone_equal_weights,
    _zone_raw_slope,
    binary4_piecewise_sag_mm,
)

R4_1_RAD_COMPLEXITY_LEVEL = 3
R4_1_RAD_COMPLEXITY = "R+Q+A4"


@dataclass(frozen=True, slots=True)
class R41RadPowerDiagnostic:
    radii_mm: tuple[float, ...]
    modeled_spherical_power_d: tuple[float, ...]
    target_relative_power_d: tuple[float, ...]
    rms_error_d: float
    max_abs_error_d: float
    target_peak_to_peak_d: float
    rms_fraction_of_target: float
    max_fraction_of_target: float


@dataclass(frozen=True, slots=True)
class R41RadFitLevelResult:
    complexity: str
    active_parameter_count: int
    iterations: int
    objective: float
    spherical_power: R41RadPowerDiagnostic
    historical_integrated_opd_rms_error_um: float
    historical_integrated_opd_max_abs_error_um: float
    historical_integrated_opd_target_peak_to_peak_um: float
    historical_integrated_opd_rms_fraction: float
    historical_integrated_opd_max_fraction: float
    historical_integrated_opd_piston_alignment_um: float
    zones: tuple[R4ZonePrescription, ...]
    boundaries: tuple[R4BoundaryDiagnostic, ...]
    minimum_conic_radicand: float


@dataclass(frozen=True, slots=True)
class R41RadFitResult:
    platform_id: str
    representative_power_d: float
    base_radius_mm: float
    base_conic: float
    surface_role: str
    target_definition: str
    sample_step_mm: float
    selected_complexity: str
    fit_valid: bool
    selected: R41RadFitLevelResult


def _zone_index(radial_apertures_mm: tuple[float, ...], radius_mm: float) -> int:
    return next(
        (
            index
            for index, outer in enumerate(radial_apertures_mm)
            if radius_mm <= outer + 1.0e-12
        ),
        len(radial_apertures_mm) - 1,
    )


def _zone_raw_second_derivative(
    r_mm: float,
    *,
    outer_radius_mm: float,
    radius_mm: float,
    conic: float,
    alpha4_mm: float,
    alpha6_mm: float,
) -> float:
    r = float(r_mm)
    c = 1.0 / float(radius_mm)
    radicand = 1.0 - (1.0 + float(conic)) * c * c * r * r
    if radicand <= 0.0:
        raise R4FitError("Binary4 fit candidate contains an invalid conic second derivative")
    conic_term = c / radicand**1.5
    p4 = 12.0 * float(alpha4_mm) * r * r / float(outer_radius_mm) ** 4
    p6 = 30.0 * float(alpha6_mm) * r**4 / float(outer_radius_mm) ** 6
    return conic_term + p4 + p6


def _rad_spherical_power_proxy_d(
    radii_mm: np.ndarray,
    zones: tuple[R4ZonePrescription, ...],
    *,
    base_radius_mm: float,
    base_conic: float,
) -> np.ndarray:
    """Return a paraxial proxy for OpticStudio spherical POWP.

    OpticStudio POWP Data=0 is the average power from a ring of real rays around
    the pupil reference ray. For a rotationally symmetric paraxial wavefront,
    the corresponding local principal powers are tangential d2W/dr2 and
    sagittal (1/r)dW/dr; their mean is therefore the appropriate fit proxy.

    This function is deliberately not treated as an exact POWP implementation.
    Real OpticStudio POWP remains the serialized/full-ray validation in R4.1.
    """

    platform = PlatformId.RAD.value
    spec = binary4_mechanism_spec(platform)
    index_step = _index_step(platform)
    output = np.empty_like(radii_mm, dtype=float)
    base_curvature = 1.0 / float(base_radius_mm)
    for sample, raw_radius in enumerate(radii_mm):
        radius = float(raw_radius)
        zone = zones[_zone_index(spec.radial_apertures_mm, radius)]
        if radius == 0.0:
            sagittal = 1000.0 * index_step * (
                1.0 / float(zone.radius_mm) - base_curvature
            )
        else:
            modeled_slope = _zone_raw_slope(
                radius,
                outer_radius_mm=zone.r_outer_mm,
                radius_mm=zone.radius_mm,
                conic=zone.conic,
                alpha4_mm=zone.alpha_p4_native,
                alpha6_mm=zone.alpha_p6_native,
            )
            base_slope = _zone_raw_slope(
                radius,
                outer_radius_mm=spec.radial_apertures_mm[-1],
                radius_mm=base_radius_mm,
                conic=base_conic,
                alpha4_mm=0.0,
                alpha6_mm=0.0,
            )
            sagittal = 1000.0 * index_step * (modeled_slope - base_slope) / radius

        modeled_second = _zone_raw_second_derivative(
            radius,
            outer_radius_mm=zone.r_outer_mm,
            radius_mm=zone.radius_mm,
            conic=zone.conic,
            alpha4_mm=zone.alpha_p4_native,
            alpha6_mm=zone.alpha_p6_native,
        )
        base_second = _zone_raw_second_derivative(
            radius,
            outer_radius_mm=spec.radial_apertures_mm[-1],
            radius_mm=base_radius_mm,
            conic=base_conic,
            alpha4_mm=0.0,
            alpha6_mm=0.0,
        )
        tangential = 1000.0 * index_step * (modeled_second - base_second)
        output[sample] = 0.5 * (sagittal + tangential)
    return output


def rad_spherical_power_diagnostic(
    zones: tuple[R4ZonePrescription, ...],
    *,
    base_radius_mm: float,
    base_conic: float,
) -> R41RadPowerDiagnostic:
    radii = np.arange(
        0.0,
        RAD_OPTIC_RADIUS_MM + 0.5 * RESIDUAL_SAMPLE_STEP_MM,
        RESIDUAL_SAMPLE_STEP_MM,
        dtype=float,
    )
    target = np.asarray(
        [rad_relative_power_d(float(radius)) for radius in radii],
        dtype=float,
    )
    modeled = _rad_spherical_power_proxy_d(
        radii,
        zones,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
    )
    weights = _zone_equal_weights(
        radii,
        binary4_mechanism_spec(PlatformId.RAD.value).radial_apertures_mm,
    )
    error = modeled - target
    rms = math.sqrt(float(np.sum(weights * error * error)))
    target_peak_to_peak = float(np.ptp(target))
    if target_peak_to_peak <= 0.0:
        raise R4FitError("R4.1 RAD power target has zero peak-to-peak value")
    maximum = float(np.max(np.abs(error)))
    return R41RadPowerDiagnostic(
        radii_mm=tuple(float(value) for value in radii),
        modeled_spherical_power_d=tuple(float(value) for value in modeled),
        target_relative_power_d=tuple(float(value) for value in target),
        rms_error_d=rms,
        max_abs_error_d=maximum,
        target_peak_to_peak_d=target_peak_to_peak,
        rms_fraction_of_target=rms / target_peak_to_peak,
        max_fraction_of_target=maximum / target_peak_to_peak,
    )


def _historical_integrated_opd_diagnostic(
    zones: tuple[R4ZonePrescription, ...],
    base_zones: tuple[R4ZonePrescription, ...],
) -> tuple[float, float, float, float, float, float]:
    platform = PlatformId.RAD.value
    spec = binary4_mechanism_spec(platform)
    radii = np.arange(
        0.0,
        RAD_OPTIC_RADIUS_MM + 0.5 * RESIDUAL_SAMPLE_STEP_MM,
        RESIDUAL_SAMPLE_STEP_MM,
        dtype=float,
    )
    weights = _zone_equal_weights(radii, spec.radial_apertures_mm)
    base_sag, _ = binary4_piecewise_sag_mm(radii, spec.radial_apertures_mm, base_zones)
    fitted_sag, _ = binary4_piecewise_sag_mm(radii, spec.radial_apertures_mm, zones)
    fitted_opd = (fitted_sag - base_sag) * 1000.0 * _index_step(platform)
    target = np.asarray([rad_raw_opd_um(float(radius)) for radius in radii], dtype=float)
    raw_difference = fitted_opd - target
    piston = float(np.sum(weights * raw_difference))
    difference = raw_difference - piston
    rms = math.sqrt(float(np.sum(weights * difference * difference)))
    maximum = float(np.max(np.abs(difference)))
    target_peak_to_peak = float(np.ptp(target))
    return (
        rms,
        maximum,
        target_peak_to_peak,
        rms / target_peak_to_peak,
        maximum / target_peak_to_peak,
        piston,
    )


def fit_r4_1_rad_mechanism(
    *,
    base_radius_mm: float,
    base_conic: float,
) -> R41RadFitResult:
    """Refit the frozen R4 RAD `R+Q+A4` topology to local spherical power.

    R4.1 deliberately holds complexity at the R4-selected `R+Q+A4` level so the
    revision isolates one issue: mechanism identity. The rejected integrated-OPD
    surrogate is retained only as a historical diagnostic. No new absolute POWP
    acceptance threshold is introduced here.
    """

    if not math.isfinite(float(base_radius_mm)) or float(base_radius_mm) >= 0.0:
        raise ValueError("R4.1 RAD posterior mechanism requires a finite negative base radius")
    if not math.isfinite(float(base_conic)):
        raise ValueError("R4.1 RAD base conic must be finite")

    platform = PlatformId.RAD.value
    spec = binary4_mechanism_spec(platform)
    radii = np.arange(
        0.0,
        RAD_OPTIC_RADIUS_MM + 0.5 * RESIDUAL_SAMPLE_STEP_MM,
        RESIDUAL_SAMPLE_STEP_MM,
        dtype=float,
    )
    target = np.asarray(
        [rad_relative_power_d(float(radius)) for radius in radii],
        dtype=float,
    )
    weights = _zone_equal_weights(radii, spec.radial_apertures_mm)
    sqrt_weights = np.sqrt(weights)
    base_zones = _make_base_zones(
        platform,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
    )
    variables = _variables(platform, base_zones, R4_1_RAD_COMPLEXITY_LEVEL)
    initial = np.asarray([variable.encode_initial() for variable in variables], dtype=float)

    def residual_function(normalized: np.ndarray) -> np.ndarray:
        try:
            zones = _decode_zones(normalized, variables, base_zones)
            modeled = _rad_spherical_power_proxy_d(
                radii,
                zones,
                base_radius_mm=base_radius_mm,
                base_conic=base_conic,
            )
            difference = modeled - target
            if np.any(~np.isfinite(difference)):
                raise R4FitError("non-finite R4.1 RAD spherical-power residual")
            return difference * sqrt_weights
        except (R4FitError, ValueError, FloatingPointError):
            return np.full(radii.size, 1.0e6, dtype=float)

    normalized, _, objective, iterations = _projected_lm(residual_function, initial)
    zones = _decode_zones(normalized, variables, base_zones)
    power = rad_spherical_power_diagnostic(
        zones,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
    )
    historical = _historical_integrated_opd_diagnostic(zones, base_zones)
    minimum_radicand = _minimum_radicand(zones)
    if minimum_radicand <= 0.0:
        raise R4FitError("R4.1 RAD fit ended with an invalid conic radicand")

    level = R41RadFitLevelResult(
        complexity=R4_1_RAD_COMPLEXITY,
        active_parameter_count=len(variables),
        iterations=iterations,
        objective=objective,
        spherical_power=power,
        historical_integrated_opd_rms_error_um=historical[0],
        historical_integrated_opd_max_abs_error_um=historical[1],
        historical_integrated_opd_target_peak_to_peak_um=historical[2],
        historical_integrated_opd_rms_fraction=historical[3],
        historical_integrated_opd_max_fraction=historical[4],
        historical_integrated_opd_piston_alignment_um=historical[5],
        zones=zones,
        boundaries=_boundary_diagnostics(spec.radial_apertures_mm, zones),
        minimum_conic_radicand=minimum_radicand,
    )
    return R41RadFitResult(
        platform_id=platform,
        representative_power_d=R4_REPRESENTATIVE_POWER_D,
        base_radius_mm=float(base_radius_mm),
        base_conic=float(base_conic),
        surface_role="posterior",
        target_definition=(
            "RAD source-locked local spherical power P(r); paraxial tangential/sagittal mean used only as fit proxy; OpticStudio POWP is final validation"
        ),
        sample_step_mm=RESIDUAL_SAMPLE_STEP_MM,
        selected_complexity=R4_1_RAD_COMPLEXITY,
        fit_valid=True,
        selected=level,
    )
