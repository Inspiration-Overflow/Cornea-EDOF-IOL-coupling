from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .domain import PlatformId
from .model_revision import binary4_mechanism_spec
from .residual_profiles import RAD_OPTIC_RADIUS_MM, RESIDUAL_SAMPLE_STEP_MM, rad_raw_opd_um, rad_relative_power_d
from .revision_r4_fit import (
    R4_COMPLEXITY_LEVELS,
    R4_MECHANISM_MAX_FRACTION_TARGET,
    R4_MECHANISM_RMS_FRACTION_TARGET,
    R4_REPRESENTATIVE_POWER_D,
    R4FitError,
    R4FitLevelResult,
    R4MechanismFitResult,
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


@dataclass(frozen=True, slots=True)
class R41RadPowerDiagnostic:
    radii_mm: tuple[float, ...]
    modeled_relative_power_d: tuple[float, ...]
    target_relative_power_d: tuple[float, ...]
    rms_error_d: float
    max_abs_error_d: float


def _zone_index(radial_apertures_mm: tuple[float, ...], radius_mm: float) -> int:
    return next(
        (index for index, outer in enumerate(radial_apertures_mm) if radius_mm <= outer + 1.0e-12),
        len(radial_apertures_mm) - 1,
    )


def _rad_relative_power_proxy_d(
    radii_mm: np.ndarray,
    zones: tuple[R4ZonePrescription, ...],
    *,
    base_radius_mm: float,
    base_conic: float,
) -> np.ndarray:
    """Return the paraxial radial-power proxy implied by the Binary4 surface.

    The frozen RAD seed obeys W(r)=integral(P(r) r dr), so numerically
    P(r)=(1/r)dW/dr for W in micrometres and r in millimetres. The Binary4
    C0 offsets do not affect this derivative. OpticStudio POWP remains the
    independent serialized/full-ray validation; this proxy is fit-only.
    """

    spec = binary4_mechanism_spec(PlatformId.RAD.value)
    index_step = _index_step(PlatformId.RAD.value)
    output = np.empty_like(radii_mm, dtype=float)
    base_curvature = 1.0 / float(base_radius_mm)
    for sample, raw_radius in enumerate(radii_mm):
        radius = float(raw_radius)
        zone = zones[_zone_index(spec.radial_apertures_mm, radius)]
        if radius == 0.0:
            output[sample] = 1000.0 * index_step * (
                1.0 / float(zone.radius_mm) - base_curvature
            )
            continue
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
        output[sample] = 1000.0 * index_step * (modeled_slope - base_slope) / radius
    return output


def rad_power_diagnostic(
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
    target = np.asarray([rad_relative_power_d(float(radius)) for radius in radii], dtype=float)
    modeled = _rad_relative_power_proxy_d(
        radii,
        zones,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
    )
    weights = _zone_equal_weights(radii, binary4_mechanism_spec(PlatformId.RAD.value).radial_apertures_mm)
    error = modeled - target
    rms = math.sqrt(float(np.sum(weights * error * error)))
    return R41RadPowerDiagnostic(
        radii_mm=tuple(float(value) for value in radii),
        modeled_relative_power_d=tuple(float(value) for value in modeled),
        target_relative_power_d=tuple(float(value) for value in target),
        rms_error_d=rms,
        max_abs_error_d=float(np.max(np.abs(error))),
    )


def _fit_level_rad_power(
    *,
    base_radius_mm: float,
    base_conic: float,
    level: int,
) -> tuple[R4FitLevelResult, R41RadPowerDiagnostic]:
    platform = PlatformId.RAD.value
    spec = binary4_mechanism_spec(platform)
    radii = np.arange(
        0.0,
        RAD_OPTIC_RADIUS_MM + 0.5 * RESIDUAL_SAMPLE_STEP_MM,
        RESIDUAL_SAMPLE_STEP_MM,
        dtype=float,
    )
    target_power = np.asarray([rad_relative_power_d(float(radius)) for radius in radii], dtype=float)
    weights = _zone_equal_weights(radii, spec.radial_apertures_mm)
    sqrt_weights = np.sqrt(weights)

    base_zones = _make_base_zones(
        platform,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
    )
    variables = _variables(platform, base_zones, level)
    initial = np.asarray([variable.encode_initial() for variable in variables], dtype=float)

    def residual_function(normalized: np.ndarray) -> np.ndarray:
        try:
            zones = _decode_zones(normalized, variables, base_zones)
            modeled_power = _rad_relative_power_proxy_d(
                radii,
                zones,
                base_radius_mm=base_radius_mm,
                base_conic=base_conic,
            )
            difference = modeled_power - target_power
            if np.any(~np.isfinite(difference)):
                raise R4FitError("non-finite R4.1 RAD power residual")
            return difference * sqrt_weights
        except (R4FitError, ValueError, FloatingPointError):
            return np.full(radii.size, 1.0e6, dtype=float)

    normalized, _, objective, iterations = _projected_lm(residual_function, initial)
    zones = _decode_zones(normalized, variables, base_zones)
    power_diagnostic = rad_power_diagnostic(
        zones,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
    )

    # Preserve the frozen R4 2%/5% engineering gate exactly: after fitting the
    # correct RAD mechanism quantity P(r), evaluate the existing integrated-OPD
    # fidelity and use the unchanged OPD fractions to stop complexity escalation.
    target_opd = np.asarray([rad_raw_opd_um(float(radius)) for radius in radii], dtype=float)
    base_sag, _ = binary4_piecewise_sag_mm(radii, spec.radial_apertures_mm, base_zones)
    fitted_sag, _ = binary4_piecewise_sag_mm(radii, spec.radial_apertures_mm, zones)
    fitted_opd = (fitted_sag - base_sag) * 1000.0 * _index_step(platform)
    raw_difference = fitted_opd - target_opd
    piston = float(np.sum(weights * raw_difference))
    difference = raw_difference - piston
    rms = math.sqrt(float(np.sum(weights * difference * difference)))
    maximum = float(np.max(np.abs(difference)))
    target_peak_to_peak = float(np.ptp(target_opd))
    if target_peak_to_peak <= 0.0:
        raise R4FitError("R4.1 RAD target has zero peak-to-peak OPD")
    rms_fraction = rms / target_peak_to_peak
    max_fraction = maximum / target_peak_to_peak
    engineering_passed = (
        rms_fraction <= R4_MECHANISM_RMS_FRACTION_TARGET
        and max_fraction <= R4_MECHANISM_MAX_FRACTION_TARGET
    )
    minimum_radicand = _minimum_radicand(zones)
    if minimum_radicand <= 0.0:
        raise R4FitError("R4.1 RAD fit ended with an invalid conic radicand")
    return (
        R4FitLevelResult(
            complexity=R4_COMPLEXITY_LEVELS[level - 1],
            active_parameter_count=len(variables),
            iterations=iterations,
            objective=objective,
            rms_opd_error_um=rms,
            max_abs_opd_error_um=maximum,
            target_peak_to_peak_um=target_peak_to_peak,
            rms_fraction_of_target=rms_fraction,
            max_fraction_of_target=max_fraction,
            piston_alignment_um=piston,
            engineering_target_passed=engineering_passed,
            zones=zones,
            boundaries=_boundary_diagnostics(spec.radial_apertures_mm, zones),
            minimum_conic_radicand=minimum_radicand,
        ),
        power_diagnostic,
    )


def fit_r4_1_rad_mechanism(
    *,
    base_radius_mm: float,
    base_conic: float,
) -> tuple[R4MechanismFitResult, tuple[R41RadPowerDiagnostic, ...]]:
    if not math.isfinite(float(base_radius_mm)) or float(base_radius_mm) >= 0.0:
        raise ValueError("R4.1 RAD posterior mechanism requires a finite negative base radius")
    if not math.isfinite(float(base_conic)):
        raise ValueError("R4.1 RAD base conic must be finite")

    attempted: list[R4FitLevelResult] = []
    power_diagnostics: list[R41RadPowerDiagnostic] = []
    selected: R4FitLevelResult | None = None
    for level in range(1, 5):
        result, power = _fit_level_rad_power(
            base_radius_mm=float(base_radius_mm),
            base_conic=float(base_conic),
            level=level,
        )
        attempted.append(result)
        power_diagnostics.append(power)
        selected = result
        if result.engineering_target_passed:
            break
    if selected is None:
        raise AssertionError("R4.1 RAD mechanism fitter attempted no complexity levels")
    return (
        R4MechanismFitResult(
            platform_id=PlatformId.RAD.value,
            representative_power_d=R4_REPRESENTATIVE_POWER_D,
            base_radius_mm=float(base_radius_mm),
            base_conic=float(base_conic),
            surface_role="posterior",
            target_definition=(
                "RAD source-locked radial power P(r) primary fit; integrated OPD retained as unchanged 2%/5% engineering gate"
            ),
            sample_step_mm=RESIDUAL_SAMPLE_STEP_MM,
            engineering_rms_fraction_target=R4_MECHANISM_RMS_FRACTION_TARGET,
            engineering_max_fraction_target=R4_MECHANISM_MAX_FRACTION_TARGET,
            levels_attempted=tuple(attempted),
            selected_complexity=selected.complexity,
            engineering_target_passed=selected.engineering_target_passed,
        ),
        tuple(power_diagnostics),
    )
