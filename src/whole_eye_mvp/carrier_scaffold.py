from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CarrierScaffoldSpec:
    """Controlled monochromatic carrier geometry shared by the three MVP platforms.

    Equality of the material/CT/bending inputs is intentional: the MVP isolates
    platform-specific standard-eye spherical-aberration targets and EDOF residuals
    instead of reverse-engineering commercial IOL hardware. Each Base × Cornea ×
    Platform still receives an independent power solve and a power-specific conic.
    """

    scaffold_id: str
    refractive_index: float
    surrounding_index: float
    center_thickness_mm: float
    optical_diameter_mm: float
    bending: str
    asphere_surface: str

    def validate(self) -> None:
        if not self.scaffold_id:
            raise ValueError("carrier scaffold ID must be non-empty")
        if self.refractive_index <= self.surrounding_index:
            raise ValueError("carrier refractive index must exceed the surrounding medium")
        if self.center_thickness_mm <= 0:
            raise ValueError("carrier center thickness must be positive")
        if self.optical_diameter_mm <= 0:
            raise ValueError("carrier optical diameter must be positive")
        if self.bending != "symmetric_biconvex":
            raise ValueError("TASK-007 MVP carrier bending must remain symmetric biconvex")
        if self.asphere_surface != "anterior":
            raise ValueError("TASK-007 MVP conic control must remain on the anterior surface")


CONTROLLED_IOL_CARRIER_546_V1 = CarrierScaffoldSpec(
    scaffold_id="CONTROLLED_IOL_CARRIER_546_v1",
    refractive_index=1.460,
    surrounding_index=1.336,
    center_thickness_mm=1.000,
    optical_diameter_mm=6.000,
    bending="symmetric_biconvex",
    asphere_surface="anterior",
)
CONTROLLED_IOL_CARRIER_546_V1.validate()
