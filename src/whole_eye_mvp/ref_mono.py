from __future__ import annotations

import math
from dataclasses import dataclass

from .cornea_assets import (
    MAIN_CORNEA_SCAFFOLD,
    CorneaScaffold,
    cornea_lock_eye_geometry,
    distance_corrected_front_radius_mm,
)
from .domain import ScientificBaseline

REF_MONO_ID = "REF_MONO_CORNEA_LOCK"
REF_MONO_IOL_INDEX = 1.46
REF_MONO_CENTER_THICKNESS_MM = 1.0
REF_MONO_OPTIC_DIAMETER_MM = 6.0
REF_MONO_FOCUS_EPD_MM = 3.0
REF_MONO_INITIAL_CONIC = 0.0


@dataclass(frozen=True, slots=True)
class RefMonoEnvelope:
    reference_id: str = REF_MONO_ID
    iol_index: float = REF_MONO_IOL_INDEX
    center_thickness_mm: float = REF_MONO_CENTER_THICKNESS_MM
    optic_diameter_mm: float = REF_MONO_OPTIC_DIAMETER_MM
    focus_epd_mm: float = REF_MONO_FOCUS_EPD_MM

    def validate(self) -> None:
        values = (
            self.iol_index,
            self.center_thickness_mm,
            self.optic_diameter_mm,
            self.focus_epd_mm,
        )
        if not self.reference_id.strip():
            raise ValueError("REF_MONO reference ID is required")
        if not all(math.isfinite(float(value)) and value > 0 for value in values):
            raise ValueError("REF_MONO envelope values must be finite and positive")
        if self.iol_index <= MAIN_CORNEA_SCAFFOLD.aqueous_index:
            raise ValueError("REF_MONO IOL index must exceed the surrounding medium")


REF_MONO_ENVELOPE = RefMonoEnvelope()


def symmetric_biconvex_power_d(
    radius_mm: float,
    *,
    envelope: RefMonoEnvelope = REF_MONO_ENVELOPE,
    medium_index: float = MAIN_CORNEA_SCAFFOLD.aqueous_index,
) -> float:
    """Equivalent thick-lens power for a symmetric biconvex IOL in one medium."""

    envelope.validate()
    if not math.isfinite(radius_mm) or radius_mm <= 0:
        raise ValueError("REF_MONO radius must be finite and positive")
    if not math.isfinite(medium_index) or medium_index <= 1:
        raise ValueError("surrounding medium index must exceed one")
    radius_m = radius_mm / 1000.0
    thickness_m = envelope.center_thickness_mm / 1000.0
    phi1 = (envelope.iol_index - medium_index) / radius_m
    phi2 = (medium_index - envelope.iol_index) / -radius_m
    return phi1 + phi2 - (thickness_m / envelope.iol_index) * phi1 * phi2


def paraxial_ref_mono_image_height_mm(
    radius_mm: float,
    baseline: ScientificBaseline,
    *,
    treatment_d: float = -3.0,
    conic: float = REF_MONO_INITIAL_CONIC,
    scaffold: CorneaScaffold = MAIN_CORNEA_SCAFFOLD,
    envelope: RefMonoEnvelope = REF_MONO_ENVELOPE,
) -> float:
    """Trace one unit-height reduced-angle ray to the fixed retina.

    Conic is accepted to make the first-order assumption explicit; it has no paraxial effect.
    """

    del conic
    scaffold.validate()
    envelope.validate()
    geometry = cornea_lock_eye_geometry(baseline, scaffold=scaffold)
    if envelope.center_thickness_mm >= geometry.iol_ant_to_image_mm:
        raise ValueError("REF_MONO thickness leaves no positive post-IOL image distance")

    y = 1.0
    nu = 0.0
    front_radius = distance_corrected_front_radius_mm(treatment_d, scaffold=scaffold)
    nu -= (scaffold.cornea_index - 1.0) / front_radius * y
    y += scaffold.thickness_mm / scaffold.cornea_index * nu
    nu -= (scaffold.aqueous_index - scaffold.cornea_index) / scaffold.back_radius_mm * y
    y += geometry.post_cornea_to_iol_ant_mm / scaffold.aqueous_index * nu

    radius = float(radius_mm)
    nu -= (envelope.iol_index - scaffold.aqueous_index) / radius * y
    y += envelope.center_thickness_mm / envelope.iol_index * nu
    nu -= (scaffold.aqueous_index - envelope.iol_index) / -radius * y

    post_iol_to_image = geometry.iol_ant_to_image_mm - envelope.center_thickness_mm
    y += post_iol_to_image / scaffold.aqueous_index * nu
    return y


def initial_ref_mono_radius_mm(
    baseline: ScientificBaseline,
    *,
    treatment_d: float = -3.0,
    lower_mm: float = 5.0,
    upper_mm: float = 20.0,
    tolerance_mm: float = 1.0e-10,
) -> float:
    """Bisection starting radius that paraxially focuses the distance cornea on the retina."""

    if not all(
        math.isfinite(value) and value > 0
        for value in (lower_mm, upper_mm, tolerance_mm)
    ):
        raise ValueError("REF_MONO radius bracket/tolerance must be finite and positive")
    if lower_mm >= upper_mm:
        raise ValueError("REF_MONO radius bracket must be strictly ordered")

    left = lower_mm
    right = upper_mm
    f_left = paraxial_ref_mono_image_height_mm(left, baseline, treatment_d=treatment_d)
    f_right = paraxial_ref_mono_image_height_mm(right, baseline, treatment_d=treatment_d)
    if not math.isfinite(f_left) or not math.isfinite(f_right) or f_left * f_right > 0:
        raise ValueError("REF_MONO starting radius bracket does not contain a paraxial focus root")

    for _ in range(80):
        middle = 0.5 * (left + right)
        value = paraxial_ref_mono_image_height_mm(middle, baseline, treatment_d=treatment_d)
        if abs(value) <= tolerance_mm or right - left <= tolerance_mm:
            return middle
        if f_left * value <= 0:
            right = middle
        else:
            left = middle
            f_left = value
    return 0.5 * (left + right)
