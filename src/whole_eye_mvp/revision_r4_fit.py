from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .domain import PlatformId
from .model_revision import binary4_mechanism_spec
from .ref_mono import symmetric_biconvex_power_d
from .residual_profiles import (
    RAD_OPTIC_RADIUS_MM,
    RESIDUAL_SAMPLE_STEP_MM,
    hoa_raw_opd_um,
    rad_raw_opd_um,
    wfs_raw_opd_um,
)

R4_REPRESENTATIVE_POWER_D = 20.0
R4_MECHANISM_RMS_FRACTION_TARGET = 0.02
R4_MECHANISM_MAX_FRACTION_TARGET = 0.05
R4_CURVATURE_ABS_MIN_MM_INV = 0.01
R4_CURVATURE_ABS_MAX_MM_INV = 0.50
R4_Q_SEARCH_HALF_WIDTH = 50.0
R4_ALPHA_SEARCH_HALF_WIDTH_MM = 0.10
R4_OPTIMIZER_MAX_ITERATIONS = 500
R4_OPTIMIZER_FINITE_DIFFERENCE = 1.0e-5
R4_COMPLEXITY_LEVELS = (
    "R",
    "R+Q",
    "R+Q+A4",
    "R+Q+A4+A6",
)


class R4FitError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class R4ZonePrescription:
    zone: int
    r_inner_mm: float
    r_outer_mm: float
    radius_mm: float
    conic: float
    alpha_p2_native: float
    alpha_p4_native: float
    alpha_p6_native: float
    active: bool


@dataclass(frozen=True, slots=True)
class R4BoundaryDiagnostic:
    boundary_mm: float
    c0_error_mm: float
    left_slope: float
    right_slope: float
    c1_slope_jump: float


@dataclass(frozen=True, slots=True)
class R4FitLevelResult:
    complexity: str
    active_parameter_count: int
    iterations: int
    objective: float
    rms_opd_error_um: float
    max_abs_opd_error_um: float
    target_peak_to_peak_um: float
    rms_fraction_of_target: float
    max_fraction_of_target: float
    piston_alignment_um: float
    engineering_target_passed: bool
    zones: tuple[R4ZonePrescription, ...]
    boundaries: tuple[R4BoundaryDiagnostic, ...]
    minimum_conic_radicand: float


@dataclass(frozen=True, slots=True)
class R4MechanismFitResult:
    platform_id: str
    representative_power_d: float
    base_radius_mm: float
    base_conic: float
    surface_role: str
    target_definition: str
    sample_step_mm: float
    engineering_rms_fraction_target: float
    engineering_max_fraction_target: float
    levels_attempted: tuple[R4FitLevelResult, ...]
    selected_complexity: str
    engineering_target_passed: bool

    @property
    def selected(self) -> R4FitLevelResult:
        for result in self.levels_attempted:
            if result.complexity == self.selected_complexity:
                return result
        raise R4FitError("selected R4 fit complexity is absent from attempted levels")


def representative_radius_mm(power_d: float = R4_REPRESENTATIVE_POWER_D) -> float:
    """Return the symmetric-biconvex radius for the representative physical power."""

    target = float(power_d)
    if not math.isfinite(target) or target <= 0.0:
        raise ValueError("representative carrier power must be finite and positive")
    left = 2.0
    right = 100.0
    f_left = symmetric_biconvex_power_d(left) - target
    f_right = symmetric_biconvex_power_d(right) - target
    if f_left * f_right > 0.0:
        raise R4FitError("representative carrier power is outside the radius bracket")
    for _ in range(100):
        middle = 0.5 * (left + right)
        value = symmetric_biconvex_power_d(middle) - target
        if abs(value) <= 1.0e-12 or right - left <= 1.0e-12:
            return middle
        if f_left * value <= 0.0:
            right = middle
        else:
            left = middle
            f_left = value
    return 0.5 * (left + right)


def _platform_id(value: str) -> str:
    try:
        return PlatformId(value).value
    except ValueError as exc:
        raise ValueError(f"unsupported R4 platform: {value}") from exc


def _target_profile(platform_id: str):
    platform = _platform_id(platform_id)
    if platform == PlatformId.WFS.value:
        return wfs_raw_opd_um, "WFS source-locked phase-shift OPD"
    if platform == PlatformId.RAD.value:
        return rad_raw_opd_um, "RAD source-locked integrated radial-power OPD"
    if platform == PlatformId.HOA.value:
        return hoa_raw_opd_um, "HOA source-locked Z4/Z6 windowed OPD"
    raise AssertionError(platform)


def _active_zone_indices(platform_id: str) -> tuple[int, ...]:
    platform = _platform_id(platform_id)
    if platform == PlatformId.WFS.value:
        return (0, 1, 2, 3, 4)
    if platform == PlatformId.RAD.value:
        # R0 freezes 1.40–2.50 mm and 2.50–3.00 mm as neutral in the pilot.
        return (0, 1, 2, 3)
    if platform == PlatformId.HOA.value:
        # R0 freezes 1.10–3.00 mm as neutral.
        return (0, 1)
    raise AssertionError(platform)


def _index_step(platform_id: str) -> float:
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    platform = _platform_id(platform_id)
    if platform == PlatformId.RAD.value:
        return scaffold.surrounding_index - scaffold.refractive_index
    return scaffold.refractive_index - scaffold.surrounding_index


def _conic_radicand(radius_mm: float, conic: float, r_mm: float) -> float:
    c = 1.0 / float(radius_mm)
    return 1.0 - (1.0 + float(conic)) * c * c * float(r_mm) ** 2


def _conic_sag_scalar(r_mm: float, radius_mm: float, conic: float) -> float:
    r = float(r_mm)
    if r == 0.0:
        return 0.0
    radicand = _conic_radicand(radius_mm, conic, r)
    if radicand <= 0.0:
        raise R4FitError(
            f"invalid conic radicand at r={r:g} mm: R={radius_mm:g}, Q={conic:g}"
        )
    c = 1.0 / float(radius_mm)
    return c * r * r / (1.0 + math.sqrt(radicand))


def _conic_sag_vector(radii_mm: np.ndarray, radius_mm: float, conic: float) -> np.ndarray:
    c = 1.0 / float(radius_mm)
    radicand = 1.0 - (1.0 + float(conic)) * c * c * radii_mm * radii_mm
    if np.any(radicand <= 0.0):
        raise R4FitError("Binary4 fit candidate contains an invalid conic radicand")
    return c * radii_mm * radii_mm / (1.0 + np.sqrt(radicand))


def _zone_raw_sag_vector(
    radii_mm: np.ndarray,
    *,
    outer_radius_mm: float,
    radius_mm: float,
    conic: float,
    alpha4_mm: float,
    alpha6_mm: float,
) -> np.ndarray:
    p = radii_mm / float(outer_radius_mm)
    return (
        _conic_sag_vector(radii_mm, radius_mm, conic)
        + float(alpha4_mm) * p**4
        + float(alpha6_mm) * p**6
    )


def _zone_raw_sag_scalar(
    r_mm: float,
    *,
    outer_radius_mm: float,
    radius_mm: float,
    conic: float,
    alpha4_mm: float,
    alpha6_mm: float,
) -> float:
    p = float(r_mm) / float(outer_radius_mm)
    return (
        _conic_sag_scalar(r_mm, radius_mm, conic)
        + float(alpha4_mm) * p**4
        + float(alpha6_mm) * p**6
    )


def _zone_raw_slope(
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
    radicand = _conic_radicand(radius_mm, conic, r)
    if radicand <= 0.0:
        raise R4FitError("Binary4 fit candidate contains an invalid conic slope")
    p4 = 4.0 * float(alpha4_mm) * r**3 / float(outer_radius_mm) ** 4
    p6 = 6.0 * float(alpha6_mm) * r**5 / float(outer_radius_mm) ** 6
    return c * r / math.sqrt(radicand) + p4 + p6


def binary4_piecewise_sag_mm(
    radii_mm: np.ndarray,
    radial_apertures_mm: tuple[float, ...],
    zones: tuple[R4ZonePrescription, ...],
) -> tuple[np.ndarray, tuple[float, ...]]:
    """Evaluate Binary 4 sag including the automatic inter-zone C0 offsets."""

    if len(radial_apertures_mm) != len(zones) or not zones:
        raise ValueError("Binary4 sag evaluation requires one prescription per zone")
    radii = np.asarray(radii_mm, dtype=float)
    if radii.ndim != 1 or radii.size < 2:
        raise ValueError("Binary4 sag evaluation requires a one-dimensional radial grid")
    if np.any(~np.isfinite(radii)) or np.any(radii < 0.0):
        raise ValueError("Binary4 sag radii must be finite and non-negative")
    if float(radii[-1]) > radial_apertures_mm[-1] + 1.0e-12:
        raise ValueError("Binary4 sag radial grid exceeds the final zone")

    result = np.empty_like(radii)
    offsets: list[float] = []
    inner = 0.0
    previous_offset = 0.0
    previous_zone: R4ZonePrescription | None = None
    previous_outer = 0.0
    for index, (outer, zone) in enumerate(zip(radial_apertures_mm, zones, strict=True)):
        if index == 0:
            offset = 0.0
        else:
            assert previous_zone is not None
            previous_value = _zone_raw_sag_scalar(
                inner,
                outer_radius_mm=previous_outer,
                radius_mm=previous_zone.radius_mm,
                conic=previous_zone.conic,
                alpha4_mm=previous_zone.alpha_p4_native,
                alpha6_mm=previous_zone.alpha_p6_native,
            )
            current_value = _zone_raw_sag_scalar(
                inner,
                outer_radius_mm=outer,
                radius_mm=zone.radius_mm,
                conic=zone.conic,
                alpha4_mm=zone.alpha_p4_native,
                alpha6_mm=zone.alpha_p6_native,
            )
            offset = previous_value + previous_offset - current_value
        offsets.append(offset)

        mask = (radii >= inner - 1.0e-12) & (radii <= outer + 1.0e-12)
        if index > 0:
            mask &= radii > inner - 1.0e-12
        local_radii = radii[mask]
        result[mask] = _zone_raw_sag_vector(
            local_radii,
            outer_radius_mm=outer,
            radius_mm=zone.radius_mm,
            conic=zone.conic,
            alpha4_mm=zone.alpha_p4_native,
            alpha6_mm=zone.alpha_p6_native,
        ) + offset
        previous_zone = zone
        previous_outer = outer
        previous_offset = offset
        inner = outer
    return result, tuple(offsets)


def _zone_equal_weights(
    radii_mm: np.ndarray,
    radial_apertures_mm: tuple[float, ...],
) -> np.ndarray:
    zone_index = np.empty(radii_mm.size, dtype=int)
    for sample, radius in enumerate(radii_mm):
        index = next(
            (
                item
                for item, outer in enumerate(radial_apertures_mm)
                if float(radius) <= outer + 1.0e-12
            ),
            len(radial_apertures_mm) - 1,
        )
        zone_index[sample] = index
    weights = np.empty(radii_mm.size, dtype=float)
    zone_count = len(radial_apertures_mm)
    for index in range(zone_count):
        count = int(np.count_nonzero(zone_index == index))
        if count < 1:
            raise R4FitError(f"R4 fit radial grid does not sample zone {index + 1}")
        weights[zone_index == index] = 1.0 / (zone_count * count)
    weights /= float(np.sum(weights))
    return weights


def _complexity_parameter_names(level: int) -> tuple[str, ...]:
    if level not in (1, 2, 3, 4):
        raise ValueError("R4 complexity level must lie in 1..4")
    return ("curvature", "conic", "alpha4", "alpha6")[:level]


def _make_base_zones(
    platform_id: str,
    *,
    base_radius_mm: float,
    base_conic: float,
) -> tuple[R4ZonePrescription, ...]:
    spec = binary4_mechanism_spec(platform_id)
    active = set(_active_zone_indices(platform_id))
    zones: list[R4ZonePrescription] = []
    inner = 0.0
    for index, outer in enumerate(spec.radial_apertures_mm):
        zones.append(
            R4ZonePrescription(
                zone=index + 1,
                r_inner_mm=inner,
                r_outer_mm=outer,
                radius_mm=float(base_radius_mm),
                conic=float(base_conic),
                alpha_p2_native=0.0,
                alpha_p4_native=0.0,
                alpha_p6_native=0.0,
                active=index in active,
            )
        )
        inner = outer
    return tuple(zones)


@dataclass(frozen=True, slots=True)
class _Variable:
    zone_index: int
    name: str
    lower: float
    upper: float
    initial: float

    def decode(self, normalized: float) -> float:
        return 0.5 * (self.lower + self.upper) + 0.5 * (self.upper - self.lower) * float(
            normalized
        )

    def encode_initial(self) -> float:
        half = 0.5 * (self.upper - self.lower)
        if half <= 0.0:
            raise ValueError("R4 variable bounds must be ordered")
        return (self.initial - 0.5 * (self.lower + self.upper)) / half


def _variables(
    platform_id: str,
    base_zones: tuple[R4ZonePrescription, ...],
    level: int,
) -> tuple[_Variable, ...]:
    names = _complexity_parameter_names(level)
    output: list[_Variable] = []
    for zone_index in _active_zone_indices(platform_id):
        zone = base_zones[zone_index]
        curvature = 1.0 / zone.radius_mm
        if curvature > 0.0:
            curvature_bounds = (
                R4_CURVATURE_ABS_MIN_MM_INV,
                R4_CURVATURE_ABS_MAX_MM_INV,
            )
        else:
            curvature_bounds = (
                -R4_CURVATURE_ABS_MAX_MM_INV,
                -R4_CURVATURE_ABS_MIN_MM_INV,
            )
        for name in names:
            if name == "curvature":
                lower, upper = curvature_bounds
                initial = curvature
            elif name == "conic":
                lower = zone.conic - R4_Q_SEARCH_HALF_WIDTH
                upper = zone.conic + R4_Q_SEARCH_HALF_WIDTH
                initial = zone.conic
            else:
                lower = -R4_ALPHA_SEARCH_HALF_WIDTH_MM
                upper = R4_ALPHA_SEARCH_HALF_WIDTH_MM
                initial = 0.0
            output.append(_Variable(zone_index, name, lower, upper, initial))
    return tuple(output)


def _decode_zones(
    normalized: np.ndarray,
    variables: tuple[_Variable, ...],
    base_zones: tuple[R4ZonePrescription, ...],
) -> tuple[R4ZonePrescription, ...]:
    values = [
        {
            "radius_mm": zone.radius_mm,
            "conic": zone.conic,
            "alpha4": zone.alpha_p4_native,
            "alpha6": zone.alpha_p6_native,
        }
        for zone in base_zones
    ]
    for coordinate, variable in zip(normalized, variables, strict=True):
        value = variable.decode(float(coordinate))
        row = values[variable.zone_index]
        if variable.name == "curvature":
            row["radius_mm"] = 1.0 / value
        elif variable.name == "conic":
            row["conic"] = value
        elif variable.name == "alpha4":
            row["alpha4"] = value
        elif variable.name == "alpha6":
            row["alpha6"] = value
        else:
            raise AssertionError(variable.name)
    return tuple(
        R4ZonePrescription(
            zone=base.zone,
            r_inner_mm=base.r_inner_mm,
            r_outer_mm=base.r_outer_mm,
            radius_mm=float(row["radius_mm"]),
            conic=float(row["conic"]),
            alpha_p2_native=0.0,
            alpha_p4_native=float(row["alpha4"]),
            alpha_p6_native=float(row["alpha6"]),
            active=base.active,
        )
        for base, row in zip(base_zones, values, strict=True)
    )


def _projected_lm(
    residual_function,
    initial: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, int]:
    coordinates = np.clip(np.asarray(initial, dtype=float), -1.0, 1.0)
    residual = residual_function(coordinates)
    objective = float(residual @ residual)
    damping = 1.0e-3
    dimension = coordinates.size
    iteration = 0
    for iteration in range(1, R4_OPTIMIZER_MAX_ITERATIONS + 1):
        jacobian = np.empty((residual.size, dimension), dtype=float)
        h = R4_OPTIMIZER_FINITE_DIFFERENCE
        for column in range(dimension):
            plus = coordinates.copy()
            minus = coordinates.copy()
            h_plus = min(h, 1.0 - coordinates[column])
            h_minus = min(h, 1.0 + coordinates[column])
            if h_plus > 1.0e-12 and h_minus > 1.0e-12:
                plus[column] += h_plus
                minus[column] -= h_minus
                jacobian[:, column] = (
                    residual_function(plus) - residual_function(minus)
                ) / (h_plus + h_minus)
            elif h_plus > 1.0e-12:
                plus[column] += h_plus
                jacobian[:, column] = (residual_function(plus) - residual) / h_plus
            else:
                minus[column] -= h_minus
                jacobian[:, column] = (residual - residual_function(minus)) / h_minus

        gradient = jacobian.T @ residual
        if float(np.linalg.norm(gradient, ord=np.inf)) < 1.0e-9:
            break
        normal = jacobian.T @ jacobian + damping * np.eye(dimension)
        try:
            step = np.linalg.solve(normal, -gradient)
        except np.linalg.LinAlgError:
            damping = min(damping * 10.0, 1.0e12)
            continue

        accepted = False
        for scale in (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625):
            candidate = np.clip(coordinates + scale * step, -1.0, 1.0)
            candidate_residual = residual_function(candidate)
            candidate_objective = float(candidate_residual @ candidate_residual)
            if candidate_objective < objective * (1.0 - 1.0e-12):
                coordinates = candidate
                residual = candidate_residual
                objective = candidate_objective
                damping = max(damping / 3.0, 1.0e-9)
                accepted = True
                break
        if not accepted:
            damping = min(damping * 10.0, 1.0e12)
            if damping >= 1.0e11:
                break
    return coordinates, residual, objective, iteration


def _boundary_diagnostics(
    radial_apertures_mm: tuple[float, ...],
    zones: tuple[R4ZonePrescription, ...],
) -> tuple[R4BoundaryDiagnostic, ...]:
    dummy = np.asarray((0.0, radial_apertures_mm[-1]), dtype=float)
    _, offsets = binary4_piecewise_sag_mm(dummy, radial_apertures_mm, zones)
    output: list[R4BoundaryDiagnostic] = []
    for index, boundary in enumerate(radial_apertures_mm[:-1]):
        left = zones[index]
        right = zones[index + 1]
        left_value = _zone_raw_sag_scalar(
            boundary,
            outer_radius_mm=left.r_outer_mm,
            radius_mm=left.radius_mm,
            conic=left.conic,
            alpha4_mm=left.alpha_p4_native,
            alpha6_mm=left.alpha_p6_native,
        ) + offsets[index]
        right_value = _zone_raw_sag_scalar(
            boundary,
            outer_radius_mm=right.r_outer_mm,
            radius_mm=right.radius_mm,
            conic=right.conic,
            alpha4_mm=right.alpha_p4_native,
            alpha6_mm=right.alpha_p6_native,
        ) + offsets[index + 1]
        left_slope = _zone_raw_slope(
            boundary,
            outer_radius_mm=left.r_outer_mm,
            radius_mm=left.radius_mm,
            conic=left.conic,
            alpha4_mm=left.alpha_p4_native,
            alpha6_mm=left.alpha_p6_native,
        )
        right_slope = _zone_raw_slope(
            boundary,
            outer_radius_mm=right.r_outer_mm,
            radius_mm=right.radius_mm,
            conic=right.conic,
            alpha4_mm=right.alpha_p4_native,
            alpha6_mm=right.alpha_p6_native,
        )
        output.append(
            R4BoundaryDiagnostic(
                boundary_mm=boundary,
                c0_error_mm=right_value - left_value,
                left_slope=left_slope,
                right_slope=right_slope,
                c1_slope_jump=right_slope - left_slope,
            )
        )
    return tuple(output)


def _minimum_radicand(zones: tuple[R4ZonePrescription, ...]) -> float:
    return min(
        _conic_radicand(zone.radius_mm, zone.conic, zone.r_outer_mm) for zone in zones
    )


def _fit_level(
    platform_id: str,
    *,
    base_radius_mm: float,
    base_conic: float,
    level: int,
) -> R4FitLevelResult:
    spec = binary4_mechanism_spec(platform_id)
    target_function, _ = _target_profile(platform_id)
    radii = np.arange(
        0.0,
        RAD_OPTIC_RADIUS_MM + 0.5 * RESIDUAL_SAMPLE_STEP_MM,
        RESIDUAL_SAMPLE_STEP_MM,
        dtype=float,
    )
    target = np.asarray([target_function(float(radius)) for radius in radii], dtype=float)
    weights = _zone_equal_weights(radii, spec.radial_apertures_mm)
    sqrt_weights = np.sqrt(weights)
    target_peak_to_peak = float(np.ptp(target))
    if target_peak_to_peak <= 0.0:
        raise R4FitError(f"R4 {platform_id} target has zero peak-to-peak OPD")

    base_zones = _make_base_zones(
        platform_id,
        base_radius_mm=base_radius_mm,
        base_conic=base_conic,
    )
    mono_sag, _ = binary4_piecewise_sag_mm(radii, spec.radial_apertures_mm, base_zones)
    variables = _variables(platform_id, base_zones, level)
    initial = np.asarray([variable.encode_initial() for variable in variables], dtype=float)
    index_step = _index_step(platform_id)

    def residual_function(normalized: np.ndarray) -> np.ndarray:
        try:
            zones = _decode_zones(normalized, variables, base_zones)
            sag, _ = binary4_piecewise_sag_mm(radii, spec.radial_apertures_mm, zones)
            modeled_opd = (sag - mono_sag) * 1000.0 * index_step
            difference = modeled_opd - target
            difference -= float(np.sum(weights * difference))
            if np.any(~np.isfinite(difference)):
                raise R4FitError("non-finite R4 mechanism residual")
            return difference * sqrt_weights
        except (R4FitError, ValueError, FloatingPointError):
            return np.full(radii.size, 1.0e6, dtype=float)

    normalized, _, objective, iterations = _projected_lm(residual_function, initial)
    zones = _decode_zones(normalized, variables, base_zones)
    fitted_sag, _ = binary4_piecewise_sag_mm(radii, spec.radial_apertures_mm, zones)
    fitted_opd = (fitted_sag - mono_sag) * 1000.0 * index_step
    raw_difference = fitted_opd - target
    piston = float(np.sum(weights * raw_difference))
    difference = raw_difference - piston
    rms = math.sqrt(float(np.sum(weights * difference * difference)))
    maximum = float(np.max(np.abs(difference)))
    rms_fraction = rms / target_peak_to_peak
    maximum_fraction = maximum / target_peak_to_peak
    engineering_passed = (
        rms_fraction <= R4_MECHANISM_RMS_FRACTION_TARGET
        and maximum_fraction <= R4_MECHANISM_MAX_FRACTION_TARGET
    )
    minimum_radicand = _minimum_radicand(zones)
    if minimum_radicand <= 0.0:
        raise R4FitError(f"R4 {platform_id} fit ended with an invalid conic radicand")
    return R4FitLevelResult(
        complexity=R4_COMPLEXITY_LEVELS[level - 1],
        active_parameter_count=len(variables),
        iterations=iterations,
        objective=objective,
        rms_opd_error_um=rms,
        max_abs_opd_error_um=maximum,
        target_peak_to_peak_um=target_peak_to_peak,
        rms_fraction_of_target=rms_fraction,
        max_fraction_of_target=maximum_fraction,
        piston_alignment_um=piston,
        engineering_target_passed=engineering_passed,
        zones=zones,
        boundaries=_boundary_diagnostics(spec.radial_apertures_mm, zones),
        minimum_conic_radicand=minimum_radicand,
    )


def fit_r4_mechanism(
    platform_id: str,
    *,
    base_radius_mm: float,
    base_conic: float,
) -> R4MechanismFitResult:
    """Fit one R4 mechanism with the frozen R→Q→A4→A6 complexity escalation.

    The objective is source-mechanism OPD fidelity after removing only an arbitrary
    piston alignment. Through-focus or MTF data never enter this fit.
    """

    platform = _platform_id(platform_id)
    if not math.isfinite(float(base_radius_mm)) or float(base_radius_mm) == 0.0:
        raise ValueError("R4 base radius must be finite and non-zero")
    if not math.isfinite(float(base_conic)):
        raise ValueError("R4 base conic must be finite")
    spec = binary4_mechanism_spec(platform)
    if spec.surface_role == "anterior" and base_radius_mm <= 0.0:
        raise ValueError("R4 anterior mechanism requires positive base radius")
    if spec.surface_role == "posterior" and base_radius_mm >= 0.0:
        raise ValueError("R4 posterior mechanism requires negative base radius")

    attempted: list[R4FitLevelResult] = []
    selected: R4FitLevelResult | None = None
    for level in range(1, 5):
        result = _fit_level(
            platform,
            base_radius_mm=float(base_radius_mm),
            base_conic=float(base_conic),
            level=level,
        )
        attempted.append(result)
        selected = result
        if result.engineering_target_passed:
            break
    if selected is None:
        raise AssertionError("R4 mechanism fitter attempted no complexity levels")
    _, target_definition = _target_profile(platform)
    return R4MechanismFitResult(
        platform_id=platform,
        representative_power_d=R4_REPRESENTATIVE_POWER_D,
        base_radius_mm=float(base_radius_mm),
        base_conic=float(base_conic),
        surface_role=spec.surface_role,
        target_definition=target_definition,
        sample_step_mm=RESIDUAL_SAMPLE_STEP_MM,
        engineering_rms_fraction_target=R4_MECHANISM_RMS_FRACTION_TARGET,
        engineering_max_fraction_target=R4_MECHANISM_MAX_FRACTION_TARGET,
        levels_attempted=tuple(attempted),
        selected_complexity=selected.complexity,
        engineering_target_passed=selected.engineering_target_passed,
    )
