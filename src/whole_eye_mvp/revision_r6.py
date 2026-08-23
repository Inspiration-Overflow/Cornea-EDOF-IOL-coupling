from __future__ import annotations

from dataclasses import dataclass

from .domain import BaseId, PlatformId

R6_R7_PHASE = "MODEL-REVISION-R6-R7-24-CARRIER-VALIDATION"
R6_CORNEA_IDS = ("N0", "A0", "B0", "C0")
R6_EXPECTED_CARRIER_COUNT = 24
R6_MAX_PQ_RECHECK_CYCLES = 2
R6_RAD_REJECTED_R4_RMS_ERROR_D = 1.923769959492952
R6_RAD_REJECTED_R4_MAX_ABS_ERROR_D = 6.2575543068007216


@dataclass(frozen=True, slots=True)
class R6CarrierKey:
    base_id: str
    cornea_id: str
    platform_id: str

    @property
    def carrier_id(self) -> str:
        return f"R6_{self.base_id}_{self.cornea_id}_{self.platform_id}"


def expected_r6_carrier_keys() -> tuple[R6CarrierKey, ...]:
    rows = tuple(
        R6CarrierKey(base.value, cornea, platform.value)
        for base in BaseId
        for cornea in R6_CORNEA_IDS
        for platform in PlatformId
    )
    if len(rows) != R6_EXPECTED_CARRIER_COUNT:
        raise AssertionError("R6 carrier key-space changed unexpectedly")
    return rows


def validate_r6_carrier_keys(keys: tuple[R6CarrierKey, ...]) -> None:
    expected = set(expected_r6_carrier_keys())
    actual = set(keys)
    if len(keys) != R6_EXPECTED_CARRIER_COUNT or actual != expected:
        raise ValueError("R6/R7 requires exactly the 2×4×3 carrier key-space")
    if len(actual) != len(keys):
        raise ValueError("R6/R7 carrier keys must be unique")


def rad_powp_local_gate(
    *,
    sign_identity_passed: bool,
    rms_error_d: float,
    max_abs_error_d: float,
) -> bool:
    """Return the frozen R6/R7 local RAD identity/regression gate.

    No new absolute scientific POWP threshold is invented at R6. The normalized
    transfer must keep target sign and remain better than the R4 solution rejected
    by Web review. Comparison with the accepted +20 D R4.2 result is evidence only.
    """

    return (
        bool(sign_identity_passed)
        and float(rms_error_d) < R6_RAD_REJECTED_R4_RMS_ERROR_D
        and float(max_abs_error_d) < R6_RAD_REJECTED_R4_MAX_ABS_ERROR_D
    )


def calibration_labels_by_platform(
    power_rows: tuple[tuple[R6CarrierKey, float], ...],
) -> dict[str, dict[str, str]]:
    """Select deterministic low/median/high exact carriers for heavier diagnostics."""

    output: dict[str, dict[str, str]] = {}
    for platform in PlatformId:
        rows = sorted(
            (
                (key, float(power))
                for key, power in power_rows
                if key.platform_id == platform.value
            ),
            key=lambda item: (item[1], item[0].carrier_id),
        )
        if len(rows) != 8:
            raise ValueError(f"R6 {platform.value} calibration selection requires eight carriers")
        # For an even population, use the lower of the two central entries so the
        # selection is deterministic and is itself one of the exact carriers.
        chosen = {"low": rows[0], "median": rows[(len(rows) - 1) // 2], "high": rows[-1]}
        output[platform.value] = {
            label: key.carrier_id for label, (key, _power) in chosen.items()
        }
    return output
