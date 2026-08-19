from __future__ import annotations

import math
from dataclasses import dataclass

from .b0 import LockCurve
from .domain import CORNEA_LOCK_B0_555_V2
from .zos import MfeMtfaRunner, MfeMtfaSettings, ZosSession

B0_OBJECT_INFINITY_MM = 1.0e10


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


def q_lock_from_mtfa_samples(
    frequencies_cyc_per_mm: tuple[float, ...],
    mtf_average: tuple[float, ...],
    *,
    maximum_frequency: float,
) -> float:
    """Compute Q_lock=(1/Fmax) integral_0^Fmax MTFA df by trapezoidal integration."""

    if not math.isfinite(maximum_frequency) or maximum_frequency <= 0:
        raise ValueError("Q_lock maximum frequency must be finite and positive")
    if len(frequencies_cyc_per_mm) != len(mtf_average) or len(mtf_average) < 2:
        raise B0ZosError("MTFA frequency/value grids must have equal length >= 2")
    if not all(
        math.isfinite(float(value)) for value in (*frequencies_cyc_per_mm, *mtf_average)
    ):
        raise B0ZosError("MTFA Q_lock inputs must be finite")
    if abs(frequencies_cyc_per_mm[0]) > 1.0e-12:
        raise B0ZosError("MTFA Q_lock frequency grid must start at 0 cycles/mm")
    if abs(frequencies_cyc_per_mm[-1] - maximum_frequency) > 1.0e-12:
        raise B0ZosError("MTFA Q_lock frequency grid must end at the frozen maximum")
    if any(
        right <= left
        for left, right in zip(frequencies_cyc_per_mm, frequencies_cyc_per_mm[1:])
    ):
        raise B0ZosError("MTFA Q_lock frequencies must be strictly increasing")
    if any(value < -1.0e-9 or value > 1.01 for value in mtf_average):
        raise B0ZosError("MTFA modulation lies outside expected [0, 1] range")

    area = math.fsum(
        0.5 * (left_y + right_y) * (right_x - left_x)
        for (left_x, left_y), (right_x, right_y) in zip(
            zip(frequencies_cyc_per_mm, mtf_average, strict=True),
            zip(frequencies_cyc_per_mm[1:], mtf_average[1:], strict=True),
            strict=True,
        )
    )
    result = area / maximum_frequency
    if not math.isfinite(result) or result < 0 or result > 1.01:
        raise B0ZosError(f"invalid Q_lock result: {result}")
    return result


def _set_epd(session: ZosSession, pupil_mm: float) -> None:
    settings = CORNEA_LOCK_B0_555_V2
    if pupil_mm not in settings.pupils_mm:
        raise ValueError(f"B0 lock pupil must be one of {settings.pupils_mm}")
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = pupil_mm


def acquire_b0_lock_curve(
    session: ZosSession,
    pupil_mm: float,
    *,
    sampling: int | None = None,
    frequency_step_cyc_per_mm: float | None = None,
) -> B0LockAcquisition:
    """Acquire the frozen 17-point B0 Q_lock curve through temporary MFE MTFA operands."""

    settings = CORNEA_LOCK_B0_555_V2
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
    selected_sampling = settings.mtfa_sampling if sampling is None else int(sampling)
    frequencies = settings.frequency_grid(step_cyc_per_mm=frequency_step_cyc_per_mm)
    mtfa_settings = MfeMtfaSettings(
        frequencies_cyc_per_mm=frequencies,
        sampling=selected_sampling,
        wavelength_number=settings.wavelength_number,
        field_number=settings.field_number,
        grid=settings.mtfa_grid,
        data_type=settings.mtfa_data_type,
    )
    runner = MfeMtfaRunner(session.system, session.zosapi)
    grid = settings.defocus_grid()
    values: list[float] = []
    try:
        for defocus_d in grid:
            object_surface.Thickness = object_thickness_for_defocus_d(
                defocus_d,
                infinity_thickness_mm=saved_object_thickness,
            )
            mtfa = runner.run(mtfa_settings)
            values.append(
                q_lock_from_mtfa_samples(
                    mtfa.frequencies_cyc_per_mm,
                    mtfa.mtf_average,
                    maximum_frequency=settings.q_lock_max_cycles_per_mm,
                )
            )
    finally:
        object_surface.Thickness = saved_object_thickness

    if len(values) != len(grid) or not all(
        math.isfinite(value) and value >= 0 for value in values
    ):
        raise B0ZosError("B0 Q_lock acquisition returned an incomplete or invalid curve")
    return B0LockAcquisition(pupil_mm, LockCurve(grid, tuple(values)))
