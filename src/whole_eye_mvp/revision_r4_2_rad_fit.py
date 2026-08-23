from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .domain import PlatformId
from .model_revision import binary4_mechanism_spec
from .residual_profiles import (
    RAD_OPTIC_RADIUS_MM,
    RESIDUAL_SAMPLE_STEP_MM,
    fit_piston_and_global_defocus,
    rad_raw_opd_um,
    rad_relative_power_d,
)
from .revision_r4_1_rad_fit import (
    R4_1_RAD_COMPLEXITY,
    R4_1_RAD_COMPLEXITY_LEVEL,
    R41RadPowerDiagnostic,
    _historical_integrated_opd_diagnostic,
    _rad_spherical_power_proxy_d,
    rad_spherical_power_diagnostic,
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
    binary4_piecewise_sag_mm,
)

R4_2_GLOBAL_DEFOCUS_TOLERANCE_D = 0.125
R4_2_LOW_ORDER_RADIUS_MM = 2.575
R4_2_LOW_ORDER_STEP_MM = 0.025


@dataclass(frozen=True, slots=True)
class R42RadLowOrderDiagnostic:
    target_piston_um: float
    target_global_defocus_d: float
    modeled_piston_um: float
    modeled_global_defocus_d: float
    defocus_error_d: float
    absolute_defocus_tolerance_d: float
    source_headroom_to_tolerance_d: float
    normalized_source_defocus_residual: float
    absolute_defocus_passed: bool


@dataclass(frozen=True, slots=True)
class R42RadFitLevelResult:
    complexity: str
    active_parameter_count: int
    iterations: int
    objective: float
    spherical_power: R41RadPowerDiagnostic
    low_order: R42RadLowOrderDiagnostic
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
class R42RadFitResult:
    platform_id: str
    representative_power_d: float
    base_radius_mm: float
    base_conic: float
    surface_role: str
    target_definition: str
    sample_step_mm: float
    selected_complexity: str
    fit_valid: bool
    selected: R42RadFitLevelResult


def _low_order_grid_mm() -> np.ndarray:
    ratio = R4_2_LOW_ORDER_RADIUS_MM / R4_2_LOW_ORDER_STEP_MM
    if not math.isclose(ratio, round(ratio), rel_tol=0.0, abs_tol=1.0e-12):
        raise R4FitError("R4.2 low-order step does not divide the low-order radius")
    return np.asarray(
        [index * R4_2_LOW_ORDER_STEP_MM for index in range(round(ratio) + 1)],
        dtype=float,
    )


def _rad_low_order_diagnostic(
    zones: tuple[R4ZonePrescription, ...],
    base_zones: tuple[R4ZonePrescription, ...],
) -> R42RadLowOrderDiagnostic:
    platform = PlatformId.RAD.value
    spec = binary4_mechanism_spec(platform)
    radii = _low_order_grid_mm()
    base_sag, _ = binary4_piecewise_sag_mm(radii, spec.radial_apertures_mm, base_zones)
    fitted_sag, _ = binary4_piecewise_sag_mm(radii, spec.radial_apertures_mm, zones)
    modeled_opd = (fitted_sag - base_sag) * 1000.0 * _index_step(platform)
    target_opd = np.asarray([rad_raw_opd_um(float(radius)) for radius in radii], dtype=float)

    target = fit_piston_and_global_defocus(tuple(radii), tuple(target_opd))
    modeled = fit_piston_and_global_defocus(tuple(radii), tuple(modeled_opd))
    headroom = R4_2_GLOBAL_DEFOCUS_TOLERANCE_D - abs(target.global_defocus_d)
    if headroom <= 0.0:
        raise R4FitError(
            "R4.2 frozen RAD source itself does not fit inside the global-defocus reference"
        )
    error = modeled.global_defocus_d - target.global_defocus_d
    return R42RadLowOrderDiagnostic(
        target_piston_um=target.piston_um,
        target_global_defocus_d=target.global_defocus_d,
        modeled_piston_um=modeled.piston_um,
        modeled_global_defocus_d=modeled.global_defocus_d,
        defocus_error_d=error,
        absolute_defocus_tolerance_d=R4_2_GLOBAL_DEFOCUS_TOLERANCE_D,
        source_headroom_to_tolerance_d=headroom,
        normalized_source_defocus_residual=error / headroom,
        absolute_defocus_passed=(
            abs(modeled.global_defocus_d) <= R4_2_GLOBAL_DEFOCUS_TOLERANCE_D
        ),
    )


def rad_source_low_order_reference() -> R42RadLowOrderDiagnostic:
    """Return the frozen RAD source low-order reference on the R4 readback grid."""

    platform = PlatformId.RAD.value
    base_radius = -12.357387811201875
    base_zones = _make_base_zones(
        platform,
        base_radius_mm=base_radius,
        base_conic=0.0,
    )
    return _rad_low_order_diagnostic(base_zones, base_zones)


def fit_r4_2_rad_mechanism(
    *,
    base_radius_mm: float,
    base_conic: float,
) -> R42RadFitResult:
    """Fit RAD spherical power while preserving the frozen source low-order defocus.

    R4.1 corrected the primary local-power quantity but its unconstrained optimum
    introduced excess low-order defocus. R4.2 keeps the same fixed ``R+Q+A4``
    topology and spherical-power proxy, and adds one source-derived low-order
    residual. The residual is normalized only by the already-frozen 0.125 D
    reference headroom of the source, so it introduces no new scientific threshold.
    """

    if not math.isfinite(float(base_radius_mm)) or float(base_radius_mm) >= 0.0:
        raise ValueError("R4.2 RAD posterior mechanism requires a finite negative base radius")
    if not math.isfinite(float(base_conic)):
        raise ValueError("R4.2 RAD base conic must be finite")

    platform = PlatformId.RAD.value
    spec = binary4_mechanism_spec(platform)
    radii = np.arange(
        0.0,
        RAD_OPTIC_RADIUS_MM + 0.5 * RESIDUAL_SAMPLE_STEP_MM,
        RESIDUAL_SAMPLE_STEP_MM,
        dtype=float,
    )
    target_power = np.asarray(
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
    source_low_order = _rad_low_order_diagnostic(base_zones, base_zones)
    headroom = source_low_order.source_headroom_to_tolerance_d

    def residual_function(normalized: np.ndarray) -> np.ndarray:
        try:
            zones = _decode_zones(normalized, variables, base_zones)
            modeled_power = _rad_spherical_power_proxy_d(
                radii,
                zones,
                base_radius_mm=base_radius_mm,
                base_conic=base_conic,
            )
            power_difference = modeled_power - target_power
            if np.any(~np.isfinite(power_difference)):
                raise R4FitError("non-finite R4.2 RAD spherical-power residual")
            low_order = _rad_low_order_diagnostic(zones, base_zones)
            defocus_residual = (
                low_order.modeled_global_defocus_d
                - source_low_order.target_global_defocus_d
            ) / headroom
            return np.concatenate(
                (power_difference * sqrt_weights, np.asarray((defocus_residual,)))
            )
        except (R4FitError, ValueError, FloatingPointError):
            return np.full(radii.size + 1, 1.0e6, dtype=float)

    normalized, _, objective, iterations = _projected_lm(residual_function, initial)
    zones = _decode_zones(normalized, variables, base_zones)
    power = rad_spherical_power_diagnostic(
        zones,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
    )
    low_order = _rad_low_order_diagnostic(zones, base_zones)
    historical = _historical_integrated_opd_diagnostic(zones, base_zones)
    minimum_radicand = _minimum_radicand(zones)
    if minimum_radicand <= 0.0:
        raise R4FitError("R4.2 RAD fit ended with an invalid conic radicand")

    level = R42RadFitLevelResult(
        complexity=R4_1_RAD_COMPLEXITY,
        active_parameter_count=len(variables),
        iterations=iterations,
        objective=objective,
        spherical_power=power,
        low_order=low_order,
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
    return R42RadFitResult(
        platform_id=platform,
        representative_power_d=R4_REPRESENTATIVE_POWER_D,
        base_radius_mm=float(base_radius_mm),
        base_conic=float(base_conic),
        surface_role="posterior",
        target_definition=(
            "RAD source-locked local spherical power P(r) with source-derived "
            "global-defocus consistency; paraxial tangential/sagittal mean is fit-only "
            "and OpticStudio POWP remains final validation"
        ),
        sample_step_mm=RESIDUAL_SAMPLE_STEP_MM,
        selected_complexity=R4_1_RAD_COMPLEXITY,
        fit_valid=True,
        selected=level,
    )
