from __future__ import annotations

import math
from dataclasses import dataclass

from .b0 import LockCurve
from .domain import CORNEA_LOCK_B0_555_V1
from .zos import HuygensMtfCurve, HuygensMtfRunner, HuygensMtfSettings, ZosSession

B0_Q_LOCK_MAX_FREQUENCY_CYC_PER_MM = 50.0
B0_MTF_ANALYSIS_MAX_FREQUENCY_CYC_PER_MM = 60.0
B0_OBJECT_INFINITY_MM = 1.0e10
B0_PUPILS_MM = (3.0, 5.0)


class B0ZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class B0LockAcquisition:
    pupil_mm: float
    curve: LockCurve


def object_thickness_for_defocus_d(
    defocus_d: float,
    *,
    infinity_thickness_mm: float = B0_OBJECT_INFINITY_MM,
) -> float:
    """Map frozen through-focus vergence to temporary OBJECT thickness in air."""

    if not math.isfinite(defocus_d):
        raise ValueError("B0 defocus must be finite")
    if abs(defocus_d) <= 1.0e-12:
        if math.isnan(infinity_thickness_mm) or infinity_thickness_mm <= 0:
            raise ValueError("nominal infinity thickness must be positive")
        return float(infinity_thickness_mm)
    return -1000.0 / defocus_d


def _require_cycles_per_mm(session: ZosSession) -> None:
    units = getattr(session.system.SystemData, "Units", None)
    value = getattr(units, "MTFUnits", None)
    if value is None:
        raise B0ZosError("installed API exposes no SystemData.Units.MTFUnits")
    text = str(value).lower().replace("_", "")
    if "millimeter" in text or "millimetre" in text:
        return
    try:
        if int(value) == 0:
            return
    except (TypeError, ValueError):
        pass
    raise B0ZosError(f"B0 lock requires MTF units cycles/mm; installed value is {value!r}")


def _linear_value(curve: HuygensMtfCurve, frequency: float) -> float:
    x = curve.frequency_cyc_per_mm
    y = curve.average
    if frequency < x[0] - 1.0e-12 or frequency > x[-1] + 1.0e-12:
        raise B0ZosError(
            f"requested Q_lock frequency {frequency:g} lies outside returned MTF range "
            f"[{x[0]:g}, {x[-1]:g}]"
        )
    for index, value in enumerate(x):
        if abs(value - frequency) <= 1.0e-12:
            return y[index]
        if value > frequency:
            left_x, right_x = x[index - 1], value
            left_y, right_y = y[index - 1], y[index]
            fraction = (frequency - left_x) / (right_x - left_x)
            return left_y + fraction * (right_y - left_y)
    return y[-1]


def q_lock_from_huygens_mtf(
    curve: HuygensMtfCurve,
    *,
    maximum_frequency: float = B0_Q_LOCK_MAX_FREQUENCY_CYC_PER_MM,
) -> float:
    """Compute Q_lock=(1/Fmax) integral_0^Fmax average Huygens MTF df."""

    if not math.isfinite(maximum_frequency) or maximum_frequency <= 0:
        raise ValueError("Q_lock maximum frequency must be finite and positive")
    if curve.frequency_cyc_per_mm[0] > 0 or curve.frequency_cyc_per_mm[-1] < maximum_frequency:
        raise B0ZosError("Huygens MTF curve does not cover the frozen 0..50 cycles/mm range")

    points: list[tuple[float, float]] = [(0.0, _linear_value(curve, 0.0))]
    points.extend(
        (frequency, value)
        for frequency, value in zip(
            curve.frequency_cyc_per_mm,
            curve.average,
            strict=True,
        )
        if 0.0 < frequency < maximum_frequency
    )
    points.append((maximum_frequency, _linear_value(curve, maximum_frequency)))
    area = math.fsum(
        0.5 * (left_y + right_y) * (right_x - left_x)
        for (left_x, left_y), (right_x, right_y) in zip(points, points[1:])
    )
    result = area / maximum_frequency
    if not math.isfinite(result) or result < 0 or result > 1.01:
        raise B0ZosError(f"invalid Q_lock result: {result}")
    return result


def _set_epd(session: ZosSession, pupil_mm: float) -> None:
    if pupil_mm not in B0_PUPILS_MM:
        raise ValueError(f"B0 lock pupil must be one of {B0_PUPILS_MM}")
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = pupil_mm


def acquire_b0_lock_curve(session: ZosSession, pupil_mm: float) -> B0LockAcquisition:
    """Acquire the frozen 17-point B0 Q_lock curve without moving retina/IOL surfaces."""

    settings = CORNEA_LOCK_B0_555_V1
    settings.validate()
    if pupil_mm not in settings.pupils_mm:
        raise ValueError(f"pupil {pupil_mm:g} mm is not frozen for B0 lock")
    wavelength_nm = (
        float(session.system.SystemData.Wavelengths.GetWavelength(1).Wavelength) * 1000.0
    )
    if abs(wavelength_nm - settings.wavelength_nm) > 1.0e-6:
        raise B0ZosError(
            f"B0 lock requires {settings.wavelength_nm:g} nm, got {wavelength_nm:.12g} nm"
        )
    _require_cycles_per_mm(session)
    _set_epd(session, pupil_mm)

    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise B0ZosError(
            f"B0 lock REF_MONO eye must have 7 surfaces, got {lde.NumberOfSurfaces}"
        )
    object_surface = lde.GetSurfaceAt(0)
    saved_object_thickness = float(object_surface.Thickness)
    runner = HuygensMtfRunner(session.system, session.zosapi)
    mtf_settings = HuygensMtfSettings(
        pupil_sampling=settings.huygens_pupil_sampling,
        image_sampling=settings.huygens_image_sampling,
        image_delta_um=settings.huygens_image_delta_um,
        maximum_frequency_cyc_per_mm=B0_MTF_ANALYSIS_MAX_FREQUENCY_CYC_PER_MM,
        normalize=settings.huygens_normalize,
        use_centroid=settings.huygens_use_centroid,
        use_polarization=settings.huygens_use_polarization,
    )
    grid = settings.defocus_grid()
    values: list[float] = []
    try:
        for defocus_d in grid:
            object_surface.Thickness = object_thickness_for_defocus_d(
                defocus_d,
                infinity_thickness_mm=saved_object_thickness,
            )
            curve = runner.run(mtf_settings)
            values.append(
                q_lock_from_huygens_mtf(
                    curve,
                    maximum_frequency=settings.b0_q_lock_max_cycles_per_mm,
                )
            )
    finally:
        object_surface.Thickness = saved_object_thickness

    if len(values) != len(grid) or not all(
        math.isfinite(value) and value >= 0 for value in values
    ):
        raise B0ZosError("B0 Q_lock acquisition returned an incomplete or invalid curve")
    return B0LockAcquisition(pupil_mm, LockCurve(grid, tuple(values)))
