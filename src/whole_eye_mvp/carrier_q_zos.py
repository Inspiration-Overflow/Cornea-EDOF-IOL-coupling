from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .base_assets import _refractive_indices, _set_material_index_at_nominal_wavelength
from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .carriers import SA_TARGETS_UM
from .ref_mono import symmetric_biconvex_power_d
from .standard_eye import (
    CORNEAL_SA_PUPIL_MM,
    STANDARD_EYE_CALIBRATION_WAVELENGTH_NM,
    _quick_focus_wavefront,
)
from .zos import MfeZernikeStandardRunner, MfeZernikeStandardSettings, SequentialEditor, ZosSession
from .zos.mfe_powp import MfePowpResult, MfePowpRunner, MfePowpSettings

ZERO_HOA_ANT_ROLE = "ZERO_HOA_Q0_ANT"
ZERO_HOA_POST_ROLE = "ZERO_HOA_Q0_POST"
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
class StandardEyeC40Measurement:
    c40_um: float
    z11_waves: float
    z37_waves: float
    best_focus_shift_mm: float


@dataclass(frozen=True, slots=True)
class ZeroHoaReferenceMeasurement:
    radius_ant_mm: float
    radius_post_mm: float
    q: float
    center_thickness_mm: float
    iol_index: float
    medium_index: float
    powp_d: float
    powp_parameter_headers: tuple[tuple[int, str], ...]
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
    zero_hoa_powp_d: float
    candidate_powp_d: float
    powp_delta_d: float
    candidate_wavefront: StandardEyeC40Measurement
    q_evaluations: int

    @property
    def target_passed(self) -> bool:
        return abs(self.achieved_sa_um - self.target_sa_um) <= Q_REPLAY_SA_TOLERANCE_UM


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


def build_physical_carrier_in_standard_eye(
    session: ZosSession,
    standard_eye_path: str | Path,
    *,
    radius_ant_mm: float,
    radius_post_mm: float,
    q: float,
    zero_hoa_reference: bool = False,
) -> None:
    """Insert the real controlled thick carrier into the standard eye.

    ZERO_HOA is represented by this exact same R/CT/n/position carrier with Q=0 and
    no residual.  The word "paraxial" in ZERO_HOA_PARAXIAL_REFERENCE refers to its
    matched first-order power identity, not to the OpticStudio Paraxial surface type.
    """

    iol_to_image = _require_standard_eye_layout(session, standard_eye_path)
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    if not all(math.isfinite(float(value)) for value in (radius_ant_mm, radius_post_mm, q)):
        raise ValueError("physical carrier radius/Q values must be finite")
    if radius_ant_mm == 0.0 or radius_post_mm == 0.0:
        raise ValueError("physical carrier radii must be non-zero")
    if zero_hoa_reference and q != 0.0:
        raise ValueError("ZERO_HOA physical reference requires Q=0")

    editor = SequentialEditor(session.system, session.zosapi)
    ant_role = ZERO_HOA_ANT_ROLE if zero_hoa_reference else TASK007_STD_CARRIER_ANT_ROLE
    post_role = ZERO_HOA_POST_ROLE if zero_hoa_reference else TASK007_STD_CARRIER_POST_ROLE
    editor.set_comment(3, ant_role)
    editor.set_radius_conic(3, radius_mm=radius_ant_mm, conic=q)
    editor.set_thickness(3, scaffold.center_thickness_mm)
    _set_material_index_at_nominal_wavelength(editor, 3, scaffold.refractive_index)

    editor.insert_surface(4)
    editor.set_comment(4, post_role)
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


def measure_standard_eye_powp(session: ZosSession) -> MfePowpResult:
    if int(session.system.LDE.NumberOfSurfaces) != 6:
        raise CarrierQZosError("standard-eye POWP readback expects 6 surfaces")
    return MfePowpRunner(session.system, session.zosapi).run(
        MfePowpSettings(surface=4)
    )


def measure_zero_hoa_reference(
    session: ZosSession,
    standard_eye_path: str | Path,
    *,
    radius_ant_mm: float,
    radius_post_mm: float,
) -> ZeroHoaReferenceMeasurement:
    build_physical_carrier_in_standard_eye(
        session,
        standard_eye_path,
        radius_ant_mm=radius_ant_mm,
        radius_post_mm=radius_post_mm,
        q=0.0,
        zero_hoa_reference=True,
    )
    wavefront = measure_standard_eye_c40(session)
    power = measure_standard_eye_powp(session)
    lde = session.system.LDE
    return ZeroHoaReferenceMeasurement(
        radius_ant_mm=radius_ant_mm,
        radius_post_mm=radius_post_mm,
        q=0.0,
        center_thickness_mm=float(lde.GetSurfaceAt(3).Thickness),
        iol_index=_refractive_indices(session.system, 3)[0],
        medium_index=_refractive_indices(session.system, 4)[0],
        powp_d=power.power_d,
        powp_parameter_headers=power.parameter_headers,
        wavefront=wavefront,
    )


def _find_q_bracket(samples: Mapping[float, float], target_sa_um: float) -> tuple[float, float] | None:
    ordered = sorted(samples.items())
    candidates: list[tuple[float, float]] = []
    for index in range(len(ordered) - 1):
        q_left, sa_left = ordered[index]
        q_right, sa_right = ordered[index + 1]
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
    return min(
        candidates,
        key=lambda pair: (max(abs(pair[0]), abs(pair[1])), abs(pair[1] - pair[0])),
    )


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
    if abs(radius_ant_mm + radius_post_mm) > 1.0e-9:
        raise CarrierQZosError("TASK-007 controlled carrier must remain symmetric biconvex")
    if abs(symmetric_biconvex_power_d(radius_ant_mm) - source_power_d) > 1.0e-9:
        raise CarrierQZosError("source power does not match the frozen carrier radii")

    target = float(SA_TARGETS_UM[platform_id])
    reference = zero_reference or measure_zero_hoa_reference(
        session,
        standard_eye_path,
        radius_ant_mm=radius_ant_mm,
        radius_post_mm=radius_post_mm,
    )
    zero_c40 = reference.wavefront.c40_um
    evaluations = 0

    def make_solution(
        q: float,
        achieved_sa: float,
        measurement: StandardEyeC40Measurement,
        powp: float,
    ) -> CarrierQSolution:
        return CarrierQSolution(
            platform_id=platform_id,
            source_power_d=source_power_d,
            radius_ant_mm=radius_ant_mm,
            radius_post_mm=radius_post_mm,
            q=q,
            target_sa_um=target,
            achieved_sa_um=achieved_sa,
            zero_hoa_c40_um=zero_c40,
            candidate_c40_um=measurement.c40_um,
            zero_hoa_powp_d=reference.powp_d,
            candidate_powp_d=powp,
            powp_delta_d=powp - reference.powp_d,
            candidate_wavefront=measurement,
            q_evaluations=evaluations,
        )

    def evaluate(q: float) -> tuple[float, StandardEyeC40Measurement, float]:
        nonlocal evaluations
        build_physical_carrier_in_standard_eye(
            session,
            standard_eye_path,
            radius_ant_mm=radius_ant_mm,
            radius_post_mm=radius_post_mm,
            q=q,
        )
        measurement = measure_standard_eye_c40(session)
        powp = measure_standard_eye_powp(session).power_d
        evaluations += 1
        return measurement.c40_um - zero_c40, measurement, powp

    samples: dict[float, float] = {}
    measurements: dict[float, StandardEyeC40Measurement] = {}
    powers: dict[float, float] = {}
    sa_zero, measurement_zero, power_zero = evaluate(0.0)
    samples[0.0] = sa_zero
    measurements[0.0] = measurement_zero
    powers[0.0] = power_zero
    if abs(sa_zero - target) <= Q_SOLVE_SA_TOLERANCE_UM:
        return make_solution(0.0, sa_zero, measurement_zero, power_zero)

    bracket: tuple[float, float] | None = None
    for magnitude in Q_BRACKET_MAGNITUDES:
        for q in (-magnitude, magnitude):
            sa, measurement, powp = evaluate(q)
            samples[q] = sa
            measurements[q] = measurement
            powers[q] = powp
            if abs(sa - target) <= Q_SOLVE_SA_TOLERANCE_UM:
                return make_solution(q, sa, measurement, powp)
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

    left, right = bracket
    if left == right:
        return make_solution(left, samples[left], measurements[left], powers[left])
    left_error = samples[left] - target
    best_q = min((left, right), key=lambda q: abs(samples[q] - target))
    for _ in range(Q_BISECTION_ITERATIONS):
        middle = 0.5 * (left + right)
        sa, measurement, powp = evaluate(middle)
        samples[middle] = sa
        measurements[middle] = measurement
        powers[middle] = powp
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
    return make_solution(best_q, best_sa, measurements[best_q], powers[best_q])


def validate_zero_hoa_measurement(
    measurement: ZeroHoaReferenceMeasurement,
    *,
    expected_power_d: float,
) -> tuple[str, ...]:
    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    findings: list[str] = []
    if measurement.q != 0.0:
        findings.append("ZERO_HOA physical reference must have Q=0")
    if abs(measurement.radius_ant_mm + measurement.radius_post_mm) > 1.0e-9:
        findings.append("ZERO_HOA radii are not the frozen symmetric carrier geometry")
    if abs(symmetric_biconvex_power_d(measurement.radius_ant_mm) - expected_power_d) > 1.0e-9:
        findings.append("ZERO_HOA carrier power metadata mismatch")
    if abs(measurement.center_thickness_mm - scaffold.center_thickness_mm) > GEOMETRY_TOLERANCE_MM:
        findings.append("ZERO_HOA center thickness mismatch")
    if abs(measurement.iol_index - scaffold.refractive_index) > INDEX_TOLERANCE:
        findings.append("ZERO_HOA IOL material index mismatch")
    if abs(measurement.medium_index - scaffold.surrounding_index) > INDEX_TOLERANCE:
        findings.append("ZERO_HOA surrounding index mismatch")
    if not math.isfinite(measurement.powp_d):
        findings.append("ZERO_HOA POWP spherical power must be finite")
    if not math.isfinite(measurement.wavefront.c40_um):
        findings.append("ZERO_HOA C40 must be finite")
    return tuple(findings)
