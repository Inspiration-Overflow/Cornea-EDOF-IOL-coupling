from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from .domain import BaseId, CorneaId, ScientificBaseline

MAIN_CORNEA_SCAFFOLD_ID = "MAIN_CORNEA_LIOU_555_v1"
CORNEA_LOCK_BASE_ID = BaseId.LB_AL2395
CORNEA_LOCK_WAVELENGTH_NM = 555.0

REFERENCE_FRONT_RADIUS_MM = 7.77
REFERENCE_FRONT_CONIC = -0.18
REFERENCE_THICKNESS_MM = 0.50
REFERENCE_BACK_RADIUS_MM = 6.40
REFERENCE_BACK_CONIC = -0.60
REFERENCE_CORNEA_INDEX = 1.376
REFERENCE_AQUEOUS_INDEX = 1.336


class CorneaSurfaceFamily(StrEnum):
    BINARY4 = "Binary4"
    EVEN_ASPHERE = "EvenAsphere"


@dataclass(frozen=True, slots=True)
class CorneaScaffold:
    scaffold_id: str = MAIN_CORNEA_SCAFFOLD_ID
    wavelength_nm: float = CORNEA_LOCK_WAVELENGTH_NM
    front_radius_mm: float = REFERENCE_FRONT_RADIUS_MM
    front_conic: float = REFERENCE_FRONT_CONIC
    thickness_mm: float = REFERENCE_THICKNESS_MM
    back_radius_mm: float = REFERENCE_BACK_RADIUS_MM
    back_conic: float = REFERENCE_BACK_CONIC
    cornea_index: float = REFERENCE_CORNEA_INDEX
    aqueous_index: float = REFERENCE_AQUEOUS_INDEX

    def validate(self) -> None:
        values = (
            self.wavelength_nm,
            self.front_radius_mm,
            self.front_conic,
            self.thickness_mm,
            self.back_radius_mm,
            self.back_conic,
            self.cornea_index,
            self.aqueous_index,
        )
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("cornea scaffold values must be finite")
        if not self.scaffold_id.strip():
            raise ValueError("cornea scaffold ID is required")
        if self.wavelength_nm <= 0 or self.thickness_mm <= 0:
            raise ValueError("cornea scaffold wavelength/thickness must be positive")
        if self.front_radius_mm == 0 or self.back_radius_mm == 0:
            raise ValueError("cornea scaffold radii must be non-zero")
        if self.cornea_index <= 1 or self.aqueous_index <= 1:
            raise ValueError("cornea/aqueous indices must be greater than one")
        if self.cornea_index <= self.aqueous_index:
            raise ValueError("cornea index must exceed aqueous index")


MAIN_CORNEA_SCAFFOLD = CorneaScaffold()


def paraxial_cornea_power_d(
    front_radius_mm: float,
    *,
    scaffold: CorneaScaffold = MAIN_CORNEA_SCAFFOLD,
) -> float:
    """Return thick-cornea equivalent power for a fixed posterior surface."""

    scaffold.validate()
    if not math.isfinite(front_radius_mm) or front_radius_mm == 0:
        raise ValueError("front radius must be finite and non-zero")
    r1_m = front_radius_mm / 1000.0
    r2_m = scaffold.back_radius_mm / 1000.0
    thickness_m = scaffold.thickness_mm / 1000.0
    f1 = (scaffold.cornea_index - 1.0) / r1_m
    f2 = (scaffold.aqueous_index - scaffold.cornea_index) / r2_m
    return f1 + f2 - (thickness_m / scaffold.cornea_index) * f1 * f2


def front_radius_for_cornea_power_d(
    target_power_d: float,
    *,
    scaffold: CorneaScaffold = MAIN_CORNEA_SCAFFOLD,
) -> float:
    """Invert thick-cornea power while the posterior surface stays fixed."""

    scaffold.validate()
    if not math.isfinite(target_power_d):
        raise ValueError("target cornea power must be finite")
    r2_m = scaffold.back_radius_mm / 1000.0
    thickness_m = scaffold.thickness_mm / 1000.0
    f2 = (scaffold.aqueous_index - scaffold.cornea_index) / r2_m
    denominator = 1.0 - (thickness_m / scaffold.cornea_index) * f2
    f1 = (target_power_d - f2) / denominator
    if not math.isfinite(f1) or f1 <= 0:
        raise ValueError("target power does not yield a positive anterior corneal power")
    return 1000.0 * (scaffold.cornea_index - 1.0) / f1


def distance_corrected_cornea_power_d(
    treatment_d: float,
    *,
    scaffold: CorneaScaffold = MAIN_CORNEA_SCAFFOLD,
) -> float:
    if not math.isfinite(treatment_d):
        raise ValueError("treatment must be finite")
    return paraxial_cornea_power_d(scaffold.front_radius_mm, scaffold=scaffold) + treatment_d


def distance_corrected_front_radius_mm(
    treatment_d: float,
    *,
    scaffold: CorneaScaffold = MAIN_CORNEA_SCAFFOLD,
) -> float:
    return front_radius_for_cornea_power_d(
        distance_corrected_cornea_power_d(treatment_d, scaffold=scaffold),
        scaffold=scaffold,
    )


def quintic_smoothstep(t: float) -> float:
    if not math.isfinite(t) or not 0.0 <= t <= 1.0:
        raise ValueError("quintic coordinate must lie in [0, 1]")
    return 10.0 * t**3 - 15.0 * t**4 + 6.0 * t**5


def quintic_smoothstep_derivative(t: float) -> float:
    if not math.isfinite(t) or not 0.0 <= t <= 1.0:
        raise ValueError("quintic coordinate must lie in [0, 1]")
    return 30.0 * t**2 - 60.0 * t**3 + 30.0 * t**4


def quintic_smoothstep_second_derivative(t: float) -> float:
    if not math.isfinite(t) or not 0.0 <= t <= 1.0:
        raise ValueError("quintic coordinate must lie in [0, 1]")
    return 60.0 * t - 180.0 * t**2 + 120.0 * t**3


@dataclass(frozen=True, slots=True)
class CorneaLockPrescription:
    candidate_id: str
    cornea_id: str
    surface_family: CorneaSurfaceFamily
    treatment_d: float
    optical_zone_mm: float
    target_delta_c40_um: float | None = None
    near_diameter_mm: float | None = None
    add_rx_d: float | None = None
    transition_width_mm: float | None = None

    @property
    def distance_front_radius_mm(self) -> float:
        return distance_corrected_front_radius_mm(self.treatment_d)

    @property
    def optical_radius_mm(self) -> float:
        return self.optical_zone_mm / 2.0

    @property
    def near_radius_mm(self) -> float | None:
        return None if self.near_diameter_mm is None else self.near_diameter_mm / 2.0

    @property
    def transition_outer_radius_mm(self) -> float | None:
        if self.near_radius_mm is None or self.transition_width_mm is None:
            return None
        return self.near_radius_mm + self.transition_width_mm

    def validate(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("cornea candidate ID is required")
        if self.cornea_id not in (CorneaId.A0, CorneaId.B0, CorneaId.C0):
            raise ValueError("unknown cornea archetype")
        if not math.isfinite(self.treatment_d) or self.treatment_d >= 0:
            raise ValueError("MVP corneal treatment must be a finite myopic treatment")
        if not math.isfinite(self.optical_zone_mm) or self.optical_zone_mm <= 0:
            raise ValueError("cornea optical zone must be finite and positive")

        if self.cornea_id == CorneaId.A0:
            if self.surface_family != CorneaSurfaceFamily.BINARY4:
                raise ValueError("A0 must use the Binary4 surface family")
            if self.target_delta_c40_um is None or not math.isfinite(self.target_delta_c40_um):
                raise ValueError("A0 requires a finite ΔC40 target")
            if any(
                value is not None
                for value in (self.near_diameter_mm, self.add_rx_d, self.transition_width_mm)
            ):
                raise ValueError("A0 must not define a near-add zone")
        elif self.cornea_id == CorneaId.B0:
            if self.surface_family != CorneaSurfaceFamily.EVEN_ASPHERE:
                raise ValueError("B candidates must use the EvenAsphere surface family")
            if self.target_delta_c40_um is None or not math.isfinite(self.target_delta_c40_um):
                raise ValueError("B candidate requires a finite ΔC40 target")
            if any(
                value is not None
                for value in (self.near_diameter_mm, self.add_rx_d, self.transition_width_mm)
            ):
                raise ValueError("B candidate must not define a near-add zone")
        else:
            if self.surface_family != CorneaSurfaceFamily.BINARY4:
                raise ValueError("C0 must use the Binary4 surface family")
            if self.target_delta_c40_um is not None:
                raise ValueError("C0 Zernike values are derived outputs, not prescription inputs")
            values = (self.near_diameter_mm, self.add_rx_d, self.transition_width_mm)
            if any(value is None or not math.isfinite(float(value)) for value in values):
                raise ValueError("C0 requires finite near diameter, ADD, and transition width")
            if float(self.near_diameter_mm) <= 0 or float(self.transition_width_mm) <= 0:
                raise ValueError("C0 near diameter/transition width must be positive")
            if float(self.add_rx_d) <= 0:
                raise ValueError("C0 ADD must be positive")
            transition_outer = self.transition_outer_radius_mm
            if transition_outer is None or transition_outer >= self.optical_radius_mm:
                raise ValueError("C0 requires a non-zero far-dominant annulus")


@dataclass(frozen=True, slots=True)
class C0RadialDesign:
    prescription: CorneaLockPrescription

    def __post_init__(self) -> None:
        self.prescription.validate()
        if self.prescription.cornea_id != CorneaId.C0:
            raise ValueError("C0RadialDesign requires the C0 prescription")

    def near_weight(self, radius_mm: float) -> float:
        if not math.isfinite(radius_mm) or radius_mm < 0:
            raise ValueError("radius must be finite and non-negative")
        near = self.prescription.near_radius_mm
        outer = self.prescription.transition_outer_radius_mm
        assert near is not None and outer is not None
        if radius_mm <= near:
            return 1.0
        if radius_mm >= outer:
            return 0.0
        t = (radius_mm - near) / (outer - near)
        return 1.0 - quintic_smoothstep(t)

    def target_cornea_power_d(self, radius_mm: float) -> float:
        add = self.prescription.add_rx_d
        assert add is not None
        distance = distance_corrected_cornea_power_d(self.prescription.treatment_d)
        return distance + add * self.near_weight(radius_mm)

    def target_front_radius_mm(self, radius_mm: float) -> float:
        return front_radius_for_cornea_power_d(self.target_cornea_power_d(radius_mm))


def cornea_lock_prescriptions(
    baseline: ScientificBaseline,
) -> tuple[CorneaLockPrescription, ...]:
    by_id = {spec.cornea_id: spec for spec in baseline.cornea_specs}
    if set(by_id) != {CorneaId.A0, CorneaId.B0, CorneaId.C0}:
        raise ValueError("scientific baseline must contain exactly A0/B0/C0 cornea specs")

    a = by_id[CorneaId.A0]
    b = by_id[CorneaId.B0]
    c = by_id[CorneaId.C0]
    prescriptions = [
        CorneaLockPrescription(
            candidate_id="A0",
            cornea_id=CorneaId.A0,
            surface_family=CorneaSurfaceFamily.BINARY4,
            treatment_d=a.treatment_d,
            optical_zone_mm=a.optical_zone_mm,
            target_delta_c40_um=a.target_delta_c40_um,
        )
    ]
    prescriptions.extend(
        CorneaLockPrescription(
            candidate_id=f"B{target:.2f}",
            cornea_id=CorneaId.B0,
            surface_family=CorneaSurfaceFamily.EVEN_ASPHERE,
            treatment_d=b.treatment_d,
            optical_zone_mm=b.optical_zone_mm,
            target_delta_c40_um=target,
        )
        for target in baseline.b_candidate_delta_c40_um
    )
    prescriptions.append(
        CorneaLockPrescription(
            candidate_id="C0",
            cornea_id=CorneaId.C0,
            surface_family=CorneaSurfaceFamily.BINARY4,
            treatment_d=c.treatment_d,
            optical_zone_mm=c.optical_zone_mm,
            near_diameter_mm=c.near_diameter_mm,
            add_rx_d=c.add_rx_d,
            transition_width_mm=c.transition_width_mm,
        )
    )
    result = tuple(prescriptions)
    for prescription in result:
        prescription.validate()
    return result
