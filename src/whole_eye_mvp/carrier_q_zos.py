from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .base_assets import _refractive_indices, _set_material_index_at_nominal_wavelength
from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .carriers import SA_TARGETS_UM
from .domain import PlatformId, ScientificBaseline
from .standard_eye import (
    CORNEAL_SA_PUPIL_MM,
    STANDARD_EYE_CALIBRATION_WAVELENGTH_NM,
    _quick_focus_wavefront,
)
from .zos import (
    MfeZernikeStandardRunner,
    MfeZernikeStandardSettings,
    SequentialEditor,
    ZosSession,
)

ZERO_HOA_OPD_MODE = 1
ZERO_HOA_ANT_ROLE = "ZERO_HOA_PARAXIAL_ANT"
ZERO_HOA_POST_ROLE = "ZERO_HOA_PARAXIAL_POST"
TASK007_STD_CARRIER_ANT_ROLE = "TASK007_STD_CARRIER_ANT"
TASK007_STD_CARRIER_POST_ROLE = "TASK007_STD_CARRIER_POST"
Q_SOLVE_SA_TOLERANCE_UM = 0.005
Q_REPLAY_SA_TOLERANCE_UM = 0.01
Q_BRACKET_MAGNITUDES = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)
Q_BISECTION_ITERATIONS = 40
GEOMETRY_TOLERANCE_MM = 0.001
INDEX_TOLERANCE = 1.0e-6


class CarrierQZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SurfacePowerPair:
    anterior_power_d: float
    posterior_power_d: float
    equivalent_power_d: float
    anterior_focal_length_mm: float
    posterior_focal_length_mm: float


@dataclass(frozen=True, slots=True)
class StandardEyeC40Measurement:
    c40_um: float
    z11_waves: float
    z37_waves: float
    best_focus_shift_mm: float


@dataclass(frozen=True, slots=True)
class ZeroHoaReferenceMeasurement:
    radius_ant_mm: float
    radius_post_mm: float
    center_thickness_mm: float
    iol_index: float
    medium_index: float
    opd_mode: int
    surface_powers: SurfacePowerPair
    wavefront: StandardEyeC40Measurement


@dataclass(frozen=True, slots=True)
class CarrierQSolution:
    platform_id: str
    source_power_d: float
    radius_ant_mm: float
    radius_post_mm: float
    q: float
    target_sa_um: float
    achieved_sa_um: float
    zero_hoa_c40_um: float
    candidate_c40_um: float
    candidate_wavefront: StandardEyeC40Measurement
    q_evaluations: int

    @property
    def target_passed(self) -> bool:
        return abs(self.achieved_sa_um - self.target_sa_um) <= Q_REPLAY_SA_TOLERANCE_UM


def paraxial_focal_length_mm_from_power_d(power_d: float) -> float:
    power = float(power_d)
    if not math.isfinite(power) or power == 0.0:
        raise ValueError("paraxial surface power must be finite and non-zero")
    return 1000.0 / power


def surface_power_pair_from_radii(
    radius_ant_mm: float,
    radius_post_mm: float,
) -> SurfacePowerPair:
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    scaffold.validate()
    r_ant = float(radius_ant_mm)
    r_post = float(radius_post_mm)
    if not all(math.isfinite(value) and value != 0.0 for value in (r_ant, r_post)):
        raise ValueError("carrier radii must be finite and non-zero")

    n_lens = scaffold.refractive_index
    n_medium = scaffold.surrounding_index
    ant_power = 1000.0 * (n_lens - n_medium) / r_ant
    post_power = 1000.0 * (n_medium - n_lens) / r_post
    thickness_m = scaffold.center_thickness_mm / 1000.0
    equivalent = ant_power + post_power - thickness_m / n_lens * ant_power * post_power
    return SurfacePowerPair(
        anterior_power_d=ant_power,
        posterior_power_d=post_power,
        equivalent_power_d=equivalent,
        anterior_focal_length_mm=paraxial_focal_length_mm_from_power_d(ant_power),
        posterior_focal_length_mm=paraxial_focal_length_mm_from_power_d(post_power),
    )


def _set_epd(session: ZosSession, diameter_mm: float) -> None:
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(diameter_mm)


def _require_standard_eye_layout(session: ZosSession, standard_eye_path: str | Path) -> float:
    path = Path(standard_eye_path)
    if not path.is_file():
        raise CarrierQZosError(f"standard-eye input is missing: {path}")
    session.system.LoadFile(str(path.resolve()), False)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 5:
        raise CarrierQZosError(
            f"TASK-007 standard-eye carrier insertion expects 5 surfaces, got {lde.NumberOfSurfaces}"
        )
    wavelength_nm = float(session.system.SystemData.Wavelengths.GetWavelength(1).Wavelength) * 1000.0
    if abs(wavelength_nm - STANDARD_EYE_CALIBRATION_WAVELENGTH_NM) > 1.0:
        raise CarrierQZosError("standard-eye wavelength differs from the frozen ~546-nm calibration")
    _set_epd(session, CORNEAL_SA_PUPIL_MM)
    iol_to_image = float(lde.GetSurfaceAt(3).Thickness)
    if iol_to_image <= CONTROLLED_IOL_CARRIER_546_V1.center_thickness_mm:
        raise CarrierQZosError("standard-eye IOL reference leaves no post-IOL image space")
    return iol_to_image


def _configure_paraxial_surface(
    editor: SequentialEditor,
    surface: int,
    *,
    focal_length_mm: float,
    opd_mode: int = ZERO_HOA_OPD_MODE,
) -> None:
    if not math.isfinite(float(focal_length_mm)) or focal_length_mm == 0.0:
        raise ValueError("Paraxial focal length must be finite and non-zero")
    if opd_mode not in (0, 1, 2, 3):
        raise ValueError("Paraxial OPD mode must be 0, 1, 2, or 3")
    editor.change_surface_type(surface, "Paraxial")
    if editor.parameter_header(surface, 1) != "Focal Length":
        raise CarrierQZosError("Paraxial Par1 header is not 'Focal Length'")
    if editor.parameter_header(surface, 2) != "OPD Mode":
        raise CarrierQZosError("Paraxial Par2 header is not 'OPD Mode'")
    editor.set_radius_conic(surface, radius_mm=0.0, conic=0.0)
    editor.set_parameter(surface, 1, focal_length_mm)
    editor.set_parameter(surface, 2, float(opd_mode))


def build_zero_hoa_reference_in_standard_eye(
    session: ZosSession,
    standard_eye_path: str | Path,
    *,
    radius_ant_mm: float,
    radius_post_mm: float,
) -> SurfacePowerPair:
    """Build the same-power zero-HOA reference from two ideal paraxial power surfaces.

    The paired Paraxial surfaces retain the carrier anterior/posterior axial positions,
    1-mm material path and index transitions. Their focal lengths reproduce the first-order
    powers of the physical carrier surfaces while removing physical surface-shape HOA.
    """

    iol_to_image = _require_standard_eye_layout(session, standard_eye_path)
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    powers = surface_power_pair_from_radii(radius_ant_mm, radius_post_mm)
    editor = SequentialEditor(session.system, session.zosapi)

    editor.set_comment(3, ZERO_HOA_ANT_ROLE)
    _configure_paraxial_surface(
        editor,
        3,
        focal_length_mm=powers.anterior_focal_length_mm,
    )
    editor.set_thickness(3, scaffold.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 3, scaffold.refractive_index)

    editor.insert_surface(4)
    editor.set_comment(4, ZERO_HOA_POST_ROLE)
    _configure_paraxial_surface(
        editor,
        4,
        focal_length_mm=powers.posterior_focal_length_mm,
    )
    editor.set_thickness(4, iol_to_image - scaffold.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 4, scaffold.surrounding_index)
    _set_epd(session, CORNEAL_SA_PUPIL_MM)
    return powers


def build_physical_carrier_in_standard_eye(
    session: ZosSession,
    standard_eye_path: str | Path,
    *,
    radius_ant_mm: float,
    radius_post_mm: float,
    q: float,
) -> None:
    iol_to_image = _require_standard_eye_layout(session, standard_eye_path)
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    if not all(math.isfinite(float(value)) for value in (radius_ant_mm, radius_post_mm, q)):
        raise ValueError("physical carrier radius/Q values must be finite")
    if radius_ant_mm == 0.0 or radius_post_mm == 0.0:
        raise ValueError("physical carrier radii must be non-zero")

    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_comment(3, TASK007_STD_CARRIER_ANT_ROLE)
    editor.set_radius_conic(3, radius_mm=radius_ant_mm, conic=q)
    editor.set_thickness(3, scaffold.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 3, scaffold.refractive_index)

    editor.insert_surface(4)
    editor.set_comment(4, TASK007_STD_CARRIER_POST_ROLE)
    editor.set_radius_conic(4, radius_mm=radius_post_mm, conic=0.0)
    editor.set_thickness(4, iol_to_image - scaffold.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 4, scaffold.surrounding_index)
    _set_epd(session, CORNEAL_SA_PUPIL_MM)


def measure_standard_eye_c40(session: ZosSession) -> StandardEyeC40Measurement:
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 6:
        raise CarrierQZosError(
            f"standard-eye IOL wavefront measurement expects 6 surfaces, got {lde.NumberOfSurfaces}"
        )
    pre_image = lde.GetSurfaceAt(4)
    fixed = float(pre_image.Thickness)
    _set_epd(session, CORNEAL_SA_PUPIL_MM)
    try:
        _quick_focus_wavefront(session)
        best = float(pre_image.Thickness)
        result = MfeZernikeStandardRunner(session.system, session.zosapi).run(
            MfeZernikeStandardSettings()
        )
        return StandardEyeC40Measurement(
            c40_um=result.c40_um,
            z11_waves=result.z11_waves,
            z37_waves=result.z37_waves,
            best_focus_shift_mm=best - fixed,
        )
    finally:
        pre_image.Thickness = fixed


def measure_zero_hoa_reference(
    session: ZosSession,
    standard_eye_path: str | Path,
    *,
    radius_ant_mm: float,
    radius_post_mm: float,
) -> ZeroHoaReferenceMeasurement:
    powers = build_zero_hoa_reference_in_standard_eye(
        session,
        standard_eye_path,
        radius_ant_mm=radius_ant_mm,
        radius_post_mm=radius_post_mm,
    )
    wavefront = measure_standard_eye_c40(session)
    lde = session.system.LDE
    iol_index = _refractive_indices(session.system, 3)[0]
    medium_index = _refractive_indices(session.system, 4)[0]
    return ZeroHoaReferenceMeasurement(
        radius_ant_mm=radius_ant_mm,
        radius_post_mm=radius_post_mm,
        center_thickness_mm=float(lde.GetSurfaceAt(3).Thickness),
        iol_index=iol_index,
        medium_index=medium_index,
        opd_mode=ZERO_HOA_OPD_MODE,
        surface_powers=powers,
        wavefront=wavefront,
    )


def _find_q_bracket(samples: Mapping[float, float], target_sa_um: float) -> tuple[float, float] | None:
    ordered = sorted(samples.items())
    candidates: list[tuple[float, float]] = []
    for (q_left, sa_left), (q_right, sa_right) in zip(ordered, ordered[1:], strict=False):
        left_error = sa_left - target_sa_um
        right_error = sa_right - target_sa_um
        if left_error == 0.0:
            return q_left, q_left
        if right_error == 0.0:
            return q_right, q_right
        if left_error * right_error < 0.0:
            candidates.append((q_left, q_right))
    if not candidates:
        return None
    return min(candidates, key=lambda pair: (max(abs(pair[0]), abs(pair[1])), abs(pair[1] - pair[0])))


def solve_q_for_platform(
    session: ZosSession,
    standard_eye_path: str | Path,
    *,
    platform_id: str,
    source_power_d: float,
    radius_ant_mm: float,
    radius_post_mm: float,
    zero_reference: ZeroHoaReferenceMeasurement | None = None,
) -> CarrierQSolution:
    if platform_id not in SA_TARGETS_UM:
        raise ValueError(f"unknown carrier platform: {platform_id}")
    target = float(SA_TARGETS_UM[platform_id])
    powers = surface_power_pair_from_radii(radius_ant_mm, radius_post_mm)
    if abs(powers.equivalent_power_d - source_power_d) > 1.0e-9:
        raise CarrierQZosError(
            "source power does not match the frozen physical carrier radii/material/thickness"
        )
    reference = zero_reference or measure_zero_hoa_reference(
        session,
        standard_eye_path,
        radius_ant_mm=radius_ant_mm,
        radius_post_mm=radius_post_mm,
    )
    zero_c40 = reference.wavefront.c40_um
    evaluations = 0

    def evaluate(q: float) -> tuple[float, StandardEyeC40Measurement]:
        nonlocal evaluations
        build_physical_carrier_in_standard_eye(
            session,
            standard_eye_path,
            radius_ant_mm=radius_ant_mm,
            radius_post_mm=radius_post_mm,
            q=q,
        )
        measurement = measure_standard_eye_c40(session)
        evaluations += 1
        return measurement.c40_um - zero_c40, measurement

    samples: dict[float, float] = {}
    measurements: dict[float, StandardEyeC40Measurement] = {}
    sa_zero, measurement_zero = evaluate(0.0)
    samples[0.0] = sa_zero
    measurements[0.0] = measurement_zero
    if abs(sa_zero - target) <= Q_SOLVE_SA_TOLERANCE_UM:
        return CarrierQSolution(
            platform_id=platform_id,
            source_power_d=source_power_d,
            radius_ant_mm=radius_ant_mm,
            radius_post_mm=radius_post_mm,
            q=0.0,
            target_sa_um=target,
            achieved_sa_um=sa_zero,
            zero_hoa_c40_um=zero_c40,
            candidate_c40_um=measurement_zero.c40_um,
            candidate_wavefront=measurement_zero,
            q_evaluations=evaluations,
        )

    bracket: tuple[float, float] | None = None
    for magnitude in Q_BRACKET_MAGNITUDES:
        for q in (-magnitude, magnitude):
            sa, measurement = evaluate(q)
            samples[q] = sa
            measurements[q] = measurement
            if abs(sa - target) <= Q_SOLVE_SA_TOLERANCE_UM:
                return CarrierQSolution(
                    platform_id=platform_id,
                    source_power_d=source_power_d,
                    radius_ant_mm=radius_ant_mm,
                    radius_post_mm=radius_post_mm,
                    q=q,
                    target_sa_um=target,
                    achieved_sa_um=sa,
                    zero_hoa_c40_um=zero_c40,
                    candidate_c40_um=measurement.c40_um,
                    candidate_wavefront=measurement,
                    q_evaluations=evaluations,
                )
        bracket = _find_q_bracket(samples, target)
        if bracket is not None:
            break
    if bracket is None:
        best_q = min(samples, key=lambda q: abs(samples[q] - target))
        raise CarrierQZosError(
            "Q scan did not bracket platform SA target; "
            f"platform={platform_id}, target={target:.6g}, "
            f"best_q={best_q:.6g}, best_sa={samples[best_q]:.6g}"
        )
    if bracket[0] == bracket[1]:
        q = bracket[0]
        measurement = measurements[q]
        return CarrierQSolution(
            platform_id=platform_id,
            source_power_d=source_power_d,
            radius_ant_mm=radius_ant_mm,
            radius_post_mm=radius_post_mm,
            q=q,
            target_sa_um=target,
            achieved_sa_um=samples[q],
            zero_hoa_c40_um=zero_c40,
            candidate_c40_um=measurement.c40_um,
            candidate_wavefront=measurement,
            q_evaluations=evaluations,
        )

    left, right = bracket
    left_error = samples[left] - target
    best_q = min((left, right), key=lambda q: abs(samples[q] - target))
    for _ in range(Q_BISECTION_ITERATIONS):
        middle = 0.5 * (left + right)
        sa, measurement = evaluate(middle)
        samples[middle] = sa
        measurements[middle] = measurement
        if abs(sa - target) < abs(samples[best_q] - target):
            best_q = middle
        if abs(sa - target) <= Q_SOLVE_SA_TOLERANCE_UM:
            best_q = middle
            break
        error = sa - target
        if left_error * error <= 0.0:
            right = middle
        else:
            left = middle
            left_error = error

    best_sa = samples[best_q]
    if abs(best_sa - target) > Q_SOLVE_SA_TOLERANCE_UM:
        raise CarrierQZosError(
            "Q bisection did not converge to the internal SA solve tolerance; "
            f"platform={platform_id}, target={target:.6g}, q={best_q:.6g}, sa={best_sa:.6g}"
        )
    best_measurement = measurements[best_q]
    return CarrierQSolution(
        platform_id=platform_id,
        source_power_d=source_power_d,
        radius_ant_mm=radius_ant_mm,
        radius_post_mm=radius_post_mm,
        q=best_q,
        target_sa_um=target,
        achieved_sa_um=best_sa,
        zero_hoa_c40_um=zero_c40,
        candidate_c40_um=best_measurement.c40_um,
        candidate_wavefront=best_measurement,
        q_evaluations=evaluations,
    )


def validate_zero_hoa_measurement(
    measurement: ZeroHoaReferenceMeasurement,
    *,
    expected_power_d: float,
) -> tuple[str, ...]:
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    findings: list[str] = []
    if abs(measurement.surface_powers.equivalent_power_d - expected_power_d) > 1.0e-9:
        findings.append("ZERO_HOA equivalent paraxial power mismatch")
    if abs(measurement.center_thickness_mm - scaffold.center_thickness_mm) > GEOMETRY_TOLERANCE_MM:
        findings.append("ZERO_HOA center thickness mismatch")
    if abs(measurement.iol_index - scaffold.refractive_index) > INDEX_TOLERANCE:
        findings.append("ZERO_HOA IOL material index mismatch")
    if abs(measurement.medium_index - scaffold.surrounding_index) > INDEX_TOLERANCE:
        findings.append("ZERO_HOA surrounding index mismatch")
    if measurement.opd_mode != ZERO_HOA_OPD_MODE:
        findings.append("ZERO_HOA OPD mode mismatch")
    if not math.isfinite(measurement.wavefront.c40_um):
        findings.append("ZERO_HOA C40 must be finite")
    return tuple(findings)
