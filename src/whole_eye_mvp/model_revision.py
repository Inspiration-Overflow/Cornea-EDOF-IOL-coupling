from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

from .domain import BaseId, PlatformId
from .zos.primitives import Binary4Zone

MODEL_REVISION_ID = "POST_HUMAN_AUDIT_2026_v1"

CORNEA_CLEAR_SEMI_DIAMETER_MM = 5.0
IOL_CLEAR_SEMI_DIAMETER_MM = 3.0
RETINA_CLEAR_SEMI_DIAMETER_MM = 5.0
PHYSICAL_PUPIL_DIAMETERS_MM = (3.0, 5.0)
CARRIER_FOCUS_PUPIL_DIAMETER_MM = 3.0


@dataclass(frozen=True, slots=True)
class RetinaPrescription:
    base_id: str
    surface_type: str
    radius_y_mm: float
    conic_y: float
    radius_x_mm: float | None = None
    conic_x: float | None = None
    semi_diameter_mm: float = RETINA_CLEAR_SEMI_DIAMETER_MM

    def validate(self) -> None:
        if not self.base_id.strip():
            raise ValueError("retina base_id is required")
        if self.surface_type not in {"Standard", "Biconic"}:
            raise ValueError("retina surface_type must be Standard or Biconic")
        if not math.isfinite(self.radius_y_mm) or self.radius_y_mm == 0:
            raise ValueError("retina Y radius must be finite and non-zero")
        if not math.isfinite(self.conic_y):
            raise ValueError("retina Y conic must be finite")
        if not math.isfinite(self.semi_diameter_mm) or self.semi_diameter_mm <= 0:
            raise ValueError("retina semi-diameter must be finite and positive")
        if self.surface_type == "Standard":
            if self.radius_x_mm is not None or self.conic_x is not None:
                raise ValueError("Standard retina must not define independent X parameters")
        else:
            if self.radius_x_mm is None or self.conic_x is None:
                raise ValueError("Biconic retina requires X radius and X conic")
            if not math.isfinite(self.radius_x_mm) or self.radius_x_mm == 0:
                raise ValueError("retina X radius must be finite and non-zero")
            if not math.isfinite(self.conic_x):
                raise ValueError("retina X conic must be finite")


RETINA_LB_SOURCE_LOCK = RetinaPrescription(
    base_id=BaseId.LB_AL2395,
    surface_type="Standard",
    radius_y_mm=-12.000,
    conic_y=0.0,
)

RETINA_ATC_M3_SOURCE_LOCK = RetinaPrescription(
    base_id=BaseId.ATC_M3_AL24477,
    surface_type="Biconic",
    # OpticStudio Biconic uses the ordinary Radius/Conic cells for Y and
    # Par1/Par2 for X Radius/X Conic.
    radius_y_mm=-12.732,
    conic_y=0.199,
    radius_x_mm=-12.628,
    conic_x=0.192,
)

_RETINA_BY_BASE = {
    BaseId.LB_AL2395: RETINA_LB_SOURCE_LOCK,
    BaseId.ATC_M3_AL24477: RETINA_ATC_M3_SOURCE_LOCK,
}


def retina_prescription_for_base(base_id: str) -> RetinaPrescription:
    try:
        prescription = _RETINA_BY_BASE[BaseId(base_id)]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported model-revision base: {base_id}") from exc
    prescription.validate()
    return prescription


def physical_stop_semi_diameter_mm(pupil_diameter_mm: float) -> float:
    diameter = float(pupil_diameter_mm)
    if not math.isfinite(diameter) or diameter not in PHYSICAL_PUPIL_DIAMETERS_MM:
        raise ValueError(
            f"physical pupil must be one of {PHYSICAL_PUPIL_DIAMETERS_MM}, got {pupil_diameter_mm!r}"
        )
    return 0.5 * diameter


@dataclass(frozen=True, slots=True)
class Binary4MechanismSpec:
    platform_id: str
    surface_role: str
    radial_apertures_mm: tuple[float, ...]
    aspheric_term_count: int = 3
    phase_term_count: int = 0

    def validate(self) -> None:
        if self.platform_id not in {item.value for item in PlatformId}:
            raise ValueError(f"unsupported Binary 4 platform: {self.platform_id}")
        if self.surface_role not in {"anterior", "posterior"}:
            raise ValueError("Binary 4 surface role must be anterior or posterior")
        if self.aspheric_term_count != 3:
            raise ValueError("model revision freezes Binary 4 Na=3 (p^2, p^4, p^6)")
        if self.phase_term_count != 0:
            raise ValueError("model revision freezes Binary 4 Np=0")
        if not self.radial_apertures_mm:
            raise ValueError("Binary 4 requires at least one zone")
        if not all(math.isfinite(value) and value > 0 for value in self.radial_apertures_mm):
            raise ValueError("Binary 4 zone apertures must be finite and positive")
        if any(right <= left for left, right in pairwise(self.radial_apertures_mm)):
            raise ValueError("Binary 4 zone apertures must be strictly increasing")
        if not math.isclose(
            self.radial_apertures_mm[-1],
            IOL_CLEAR_SEMI_DIAMETER_MM,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise ValueError("Binary 4 final zone must end at the 3.0 mm IOL radius")


BINARY4_WFS_SPEC = Binary4MechanismSpec(
    platform_id=PlatformId.WFS,
    surface_role="anterior",
    radial_apertures_mm=(0.55, 0.65, 0.87, 1.05, 3.00),
)
BINARY4_RAD_SPEC = Binary4MechanismSpec(
    platform_id=PlatformId.RAD,
    surface_role="posterior",
    radial_apertures_mm=(0.50, 0.90, 1.10, 1.40, 2.50, 3.00),
)
BINARY4_HOA_SPEC = Binary4MechanismSpec(
    platform_id=PlatformId.HOA,
    surface_role="anterior",
    radial_apertures_mm=(0.90, 1.10, 3.00),
)

_BINARY4_BY_PLATFORM = {
    PlatformId.WFS: BINARY4_WFS_SPEC,
    PlatformId.RAD: BINARY4_RAD_SPEC,
    PlatformId.HOA: BINARY4_HOA_SPEC,
}


def binary4_mechanism_spec(platform_id: str) -> Binary4MechanismSpec:
    try:
        spec = _BINARY4_BY_PLATFORM[PlatformId(platform_id)]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported Binary 4 platform: {platform_id}") from exc
    spec.validate()
    return spec


def degenerate_binary4_zones(
    platform_id: str,
    *,
    radius_mm: float,
    conic: float,
) -> tuple[Binary4Zone, ...]:
    """Return a Binary4 MONO surface that is analytically identical zone-by-zone.

    All zones keep the carrier radius/conic, diffraction order is zero, Np is zero,
    and the Na=3 coefficients (p^2/p^4/p^6) are all zero.  The p^2 slot is present
    structurally but is never an optical degree of freedom in this revision.
    """

    radius = float(radius_mm)
    q = float(conic)
    if not math.isfinite(radius) or radius == 0:
        raise ValueError("degenerate Binary 4 radius must be finite and non-zero")
    if not math.isfinite(q):
        raise ValueError("degenerate Binary 4 conic must be finite")
    spec = binary4_mechanism_spec(platform_id)
    return tuple(
        Binary4Zone(
            radial_aperture=aperture,
            radius=radius,
            conic=q,
            diffraction_order=0.0,
            aspheric_terms=(0.0, 0.0, 0.0),
            phase_terms=(),
        )
        for aperture in spec.radial_apertures_mm
    )


def equivalent_even_asphere_coefficients(
    *,
    outer_radius_mm: float,
    alpha_p4_native: float,
    alpha_p6_native: float,
) -> tuple[float, float]:
    """Convert Binary 4 native normalized p^4/p^6 values to r^4/r^6 coefficients."""

    radius = float(outer_radius_mm)
    alpha4 = float(alpha_p4_native)
    alpha6 = float(alpha_p6_native)
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("Binary 4 normalization radius must be finite and positive")
    if not all(math.isfinite(value) for value in (alpha4, alpha6)):
        raise ValueError("Binary 4 native coefficients must be finite")
    return alpha4 / radius**4, alpha6 / radius**6
