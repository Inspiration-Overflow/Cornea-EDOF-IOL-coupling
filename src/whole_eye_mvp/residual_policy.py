from __future__ import annotations

from .carriers import ResidualValidationPolicy

# Engineering acceptance band for the residual payload itself.  It is deliberately
# distinct from the observed MONO→EDOF distance-peak shift, which remains a scientific
# output and is not forced to zero.
RESIDUAL_VALIDATION_546_V1 = ResidualValidationPolicy(
    policy_id="RESIDUAL_VALIDATION_546_v1",
    piston_tolerance_um=0.010,
    global_defocus_tolerance_d=0.125,
)
RESIDUAL_VALIDATION_546_V1.validate()
