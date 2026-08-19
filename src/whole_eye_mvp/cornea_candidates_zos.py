from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .cornea_assets import (
    MAIN_CORNEA_SCAFFOLD,
    C0RadialDesign,
    CorneaLockPrescription,
    CorneaSurfaceFamily,
    cornea_lock_prescriptions,
    distance_corrected_front_radius_mm,
)
from .domain import CorneaId, ScientificBaseline
from .standard_eye import _quick_focus_wavefront
from .zos import (
    Binary4Zone,
    MfeZernikeStandardRunner,
    MfeZernikeStandardSettings,
    SequentialEditor,
    ZosSession,
)
from .zos.primitives import binary4_zone_columns, even_asphere_parameter_number

CORNEA_C40_EPD_MM = 6.0
CORNEA_SUPPORT_RADIUS_MM = 4.0
CORNEA_DELTA_C40_SOLVE_TOLERANCE_UM = 0.005
A_CONIC_SCAN = (-8.0, -4.0, -2.0, -1.0, -0.5, -0.18, 0.0, 0.5, 1.0, 2.0, 4.0, 8.0)
B_R4_SCAN = (
    -0.003,
    -0.001,
    -0.0003,
    -0.0001,
    -0.00003,
    -0.00001,
    -0.000003,
    -0.000001,
    0.0,
    0.000001,
    0.000003,
    0.00001,
    0.00003,
    0.0001,
    0.0003,
    0.001,
    0.003,
)
SCALAR_SOLVE_ITERATIONS = 36
C0_TRANSITION_SLICES_NOMINAL = 8
C0_TRANSITION_SLICES_CONVERGENCE = (4, 8, 16)


class CorneaCandidateZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CorneaWavefrontMeasurement:
    c40_um: float
    z11_waves: float
    z37_waves: float
    best_focus_shift_mm: float


@dataclass(frozen=True, slots=True)
class CorneaCandidateMeasurement:
    candidate_id: str
    surface_family: str
    target_delta_c40_um: float | None
    achieved_delta_c40_um: float
    reference_c40_um: float
    candidate_c40_um: float
    control_name: str
    control_value: float
    wavefront: CorneaWavefrontMeasurement

    @property
    def target_passed(self) -> bool:
        if self.target_delta_c40_um is None:
            return True
        return (
            abs(self.achieved_delta_c40_um - self.target_delta_c40_um)
            <= CORNEA_DELTA_C40_SOLVE_TOLERANCE_UM
        )


def _set_epd(session: ZosSession, diameter_mm: float) -> None:
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(diameter_mm)


def measure_best_focus_cornea_wavefront(session: ZosSession) -> CorneaWavefrontMeasurement:
    """Measure on-axis EPD6 C40 at Wavefront-Error best focus and restore fixed IMAGE."""

    _set_epd(session, CORNEA_C40_EPD_MM)
    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 6:
        raise CorneaCandidateZosError(
            f"cornea-only C40 measurement expects 6 surfaces, got {lde.NumberOfSurfaces}"
        )
    pre_image = lde.GetSurfaceAt(4)
    fixed = float(pre_image.Thickness)
    try:
        _quick_focus_wavefront(session)
        best = float(pre_image.Thickness)
        result = MfeZernikeStandardRunner(session.system, session.zosapi).run(
            MfeZernikeStandardSettings()
        )
        return CorneaWavefrontMeasurement(
            c40_um=result.c40_um,
            z11_waves=result.z11_waves,
            z37_waves=result.z37_waves,
            best_focus_shift_mm=best - fixed,
        )
    finally:
        pre_image.Thickness = fixed


def measure_cornea_file_wavefront(
    session: ZosSession,
    path: str | Path,
) -> CorneaWavefrontMeasurement:
    session.system.LoadFile(str(Path(path).resolve()), False)
    return measure_best_focus_cornea_wavefront(session)


def _solve_scalar_target(
    setter: Callable[[float], None],
    evaluator: Callable[[], float],
    scan: tuple[float, ...],
    target: float,
    *,
    tolerance: float = CORNEA_DELTA_C40_SOLVE_TOLERANCE_UM,
) -> tuple[float, float]:
    if not math.isfinite(target) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("scalar target/tolerance must be finite and tolerance positive")
    if len(scan) < 2 or tuple(sorted(scan)) != scan:
        raise ValueError("scalar scan must contain at least two strictly ordered values")

    samples: list[tuple[float, float]] = []
    for control in scan:
        setter(control)
        value = evaluator()
        if not math.isfinite(value):
            raise CorneaCandidateZosError(
                f"non-finite corneal target metric at control={control}: {value}"
            )
        samples.append((control, value))
        if abs(value - target) <= tolerance:
            return control, value

    bracket: tuple[tuple[float, float], tuple[float, float]] | None = None
    for left, right in zip(samples, samples[1:]):
        if (left[1] - target) * (right[1] - target) < 0:
            bracket = (left, right)
            break
    if bracket is None:
        best = min(samples, key=lambda item: abs(item[1] - target))
        raise CorneaCandidateZosError(
            "corneal scalar scan did not bracket target; "
            f"target={target:.6g}, best control={best[0]:.6g}, best value={best[1]:.6g}"
        )

    left, right = bracket
    best = min((left, right), key=lambda item: abs(item[1] - target))
    for _ in range(SCALAR_SOLVE_ITERATIONS):
        middle_control = 0.5 * (left[0] + right[0])
        setter(middle_control)
        middle_value = evaluator()
        middle = (middle_control, middle_value)
        if abs(middle_value - target) < abs(best[1] - target):
            best = middle
        if abs(middle_value - target) <= tolerance:
            return middle
        if (left[1] - target) * (middle_value - target) <= 0:
            right = middle
        else:
            left = middle

    if abs(best[1] - target) > tolerance:
        raise CorneaCandidateZosError(
            "corneal scalar solve did not converge: "
            f"target={target:.6g}, best control={best[0]:.6g}, best value={best[1]:.6g}"
        )
    setter(best[0])
    return best


def _a_zones(
    prescription: CorneaLockPrescription,
    inner_conic: float,
) -> tuple[Binary4Zone, ...]:
    return (
        Binary4Zone(
            radial_aperture=prescription.optical_radius_mm,
            radius=prescription.distance_front_radius_mm,
            conic=inner_conic,
        ),
        Binary4Zone(
            radial_aperture=CORNEA_SUPPORT_RADIUS_MM,
            radius=MAIN_CORNEA_SCAFFOLD.front_radius_mm,
            conic=MAIN_CORNEA_SCAFFOLD.front_conic,
        ),
    )


def build_a_candidate(
    session: ZosSession,
    baseline: ScientificBaseline,
    distance_cornea_path: str | Path,
    destination: str | Path,
    reference_c40_um: float,
) -> CorneaCandidateMeasurement:
    prescription = cornea_lock_prescriptions(baseline)[0]
    if prescription.cornea_id != CorneaId.A0:
        raise CorneaCandidateZosError("A0 prescription ordering mismatch")
    session.system.LoadFile(str(Path(distance_cornea_path).resolve()), False)
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_comment(1, "CORNEA_ANT_A0")
    editor.configure_binary4(
        1,
        _a_zones(prescription, MAIN_CORNEA_SCAFFOLD.front_conic),
    )
    editor.set_radius_conic(
        1,
        radius_mm=prescription.distance_front_radius_mm,
        conic=MAIN_CORNEA_SCAFFOLD.front_conic,
    )
    editor.surface(1).SemiDiameter = CORNEA_SUPPORT_RADIUS_MM
    zone1_conic_parameter = binary4_zone_columns(1, 0, 0).conic
    target = float(prescription.target_delta_c40_um)

    def setter(conic: float) -> None:
        editor.set_parameter(1, zone1_conic_parameter, conic)
        editor.surface(1).Conic = float(conic)

    def evaluator() -> float:
        return measure_best_focus_cornea_wavefront(session).c40_um - reference_c40_um

    conic, _ = _solve_scalar_target(setter, evaluator, A_CONIC_SCAN, target)
    setter(conic)
    wavefront = measure_best_focus_cornea_wavefront(session)
    output = Path(destination)
    editor.save_as(output)
    return CorneaCandidateMeasurement(
        candidate_id=prescription.candidate_id,
        surface_family=prescription.surface_family,
        target_delta_c40_um=target,
        achieved_delta_c40_um=wavefront.c40_um - reference_c40_um,
        reference_c40_um=reference_c40_um,
        candidate_c40_um=wavefront.c40_um,
        control_name="inner_zone_conic",
        control_value=conic,
        wavefront=wavefront,
    )


def build_b_candidate(
    session: ZosSession,
    prescription: CorneaLockPrescription,
    distance_cornea_path: str | Path,
    destination: str | Path,
    reference_c40_um: float,
) -> CorneaCandidateMeasurement:
    prescription.validate()
    if prescription.cornea_id != CorneaId.B0:
        raise ValueError("build_b_candidate requires a B candidate prescription")
    session.system.LoadFile(str(Path(distance_cornea_path).resolve()), False)
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_comment(1, f"CORNEA_ANT_{prescription.candidate_id}")
    # The verified Even Asphere mapping uses order 4 -> Par2.  The r^4 term changes
    # primary spherical aberration without adding a paraxial r^2 power term.
    editor.configure_even_asphere(1, {4: 0.0})
    editor.set_radius_conic(
        1,
        radius_mm=prescription.distance_front_radius_mm,
        conic=MAIN_CORNEA_SCAFFOLD.front_conic,
    )
    editor.surface(1).SemiDiameter = CORNEA_SUPPORT_RADIUS_MM
    r4_parameter = even_asphere_parameter_number(4)
    target = float(prescription.target_delta_c40_um)

    def setter(r4_coefficient: float) -> None:
        editor.set_parameter(1, r4_parameter, r4_coefficient)

    def evaluator() -> float:
        return measure_best_focus_cornea_wavefront(session).c40_um - reference_c40_um

    r4_coefficient, _ = _solve_scalar_target(setter, evaluator, B_R4_SCAN, target)
    setter(r4_coefficient)
    wavefront = measure_best_focus_cornea_wavefront(session)
    output = Path(destination)
    editor.save_as(output)
    return CorneaCandidateMeasurement(
        candidate_id=prescription.candidate_id,
        surface_family=prescription.surface_family,
        target_delta_c40_um=target,
        achieved_delta_c40_um=wavefront.c40_um - reference_c40_um,
        reference_c40_um=reference_c40_um,
        candidate_c40_um=wavefront.c40_um,
        control_name="even_asphere_r4",
        control_value=r4_coefficient,
        wavefront=wavefront,
    )


def c0_binary4_zones(
    prescription: CorneaLockPrescription,
    transition_slices: int,
) -> tuple[Binary4Zone, ...]:
    prescription.validate()
    if prescription.cornea_id != CorneaId.C0:
        raise ValueError("C0 Binary4 zones require the C0 prescription")
    if transition_slices < 1 or transition_slices > 40:
        raise ValueError("C0 transition slices must lie in [1, 40]")

    design = C0RadialDesign(prescription)
    near = prescription.near_radius_mm
    outer = prescription.transition_outer_radius_mm
    assert near is not None and outer is not None
    zones = [
        Binary4Zone(
            radial_aperture=near,
            radius=design.target_front_radius_mm(0.5 * near),
            conic=MAIN_CORNEA_SCAFFOLD.front_conic,
        )
    ]
    width = (outer - near) / transition_slices
    for index in range(transition_slices):
        inner = near + index * width
        aperture = near + (index + 1) * width
        midpoint = 0.5 * (inner + aperture)
        zones.append(
            Binary4Zone(
                radial_aperture=aperture,
                radius=design.target_front_radius_mm(midpoint),
                conic=MAIN_CORNEA_SCAFFOLD.front_conic,
            )
        )
    zones.append(
        Binary4Zone(
            radial_aperture=prescription.optical_radius_mm,
            radius=distance_corrected_front_radius_mm(prescription.treatment_d),
            conic=MAIN_CORNEA_SCAFFOLD.front_conic,
        )
    )
    return tuple(zones)


def build_c_candidate(
    session: ZosSession,
    baseline: ScientificBaseline,
    distance_cornea_path: str | Path,
    destination: str | Path,
    reference_c40_um: float,
    *,
    transition_slices: int = C0_TRANSITION_SLICES_NOMINAL,
) -> CorneaCandidateMeasurement:
    prescription = cornea_lock_prescriptions(baseline)[-1]
    if prescription.cornea_id != CorneaId.C0:
        raise CorneaCandidateZosError("C0 prescription ordering mismatch")
    session.system.LoadFile(str(Path(distance_cornea_path).resolve()), False)
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_comment(1, f"CORNEA_ANT_C0_N{transition_slices}")
    zones = c0_binary4_zones(prescription, transition_slices)
    editor.configure_binary4(1, zones)
    editor.set_radius_conic(1, radius_mm=zones[0].radius, conic=zones[0].conic)
    editor.surface(1).SemiDiameter = zones[-1].radial_aperture
    wavefront = measure_best_focus_cornea_wavefront(session)
    output = Path(destination)
    editor.save_as(output)
    return CorneaCandidateMeasurement(
        candidate_id=f"C0_N{transition_slices}",
        surface_family=CorneaSurfaceFamily.BINARY4,
        target_delta_c40_um=None,
        achieved_delta_c40_um=wavefront.c40_um - reference_c40_um,
        reference_c40_um=reference_c40_um,
        candidate_c40_um=wavefront.c40_um,
        control_name="transition_slices",
        control_value=float(transition_slices),
        wavefront=wavefront,
    )
