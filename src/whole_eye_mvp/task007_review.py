from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any

EXPECTED_PHASE = "TASK-007-CONSOLIDATED-FULL18-RESIDUAL-CALIBRATION"
EXPECTED_PLATFORMS = ("WFS", "RAD", "HOA")
EXPECTED_LABELS = ("low", "median", "high")


class Task007ReviewError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MechanismDecision:
    platform_id: str
    passed: bool
    reason: str

    def validate(self) -> None:
        if self.platform_id not in EXPECTED_PLATFORMS:
            raise Task007ReviewError(f"unknown mechanism platform: {self.platform_id}")
        if not self.reason.strip():
            raise Task007ReviewError("mechanism decision requires a non-empty reason")


@dataclass(frozen=True, slots=True)
class Task007ReviewResult:
    schema_version: int
    phase: str
    evidence_only: bool
    formal_artifact: bool
    source_phase: str
    source_code_commit: str
    source_local_report_sha256: str
    source_numerical_hard_gates_passed: bool
    source_false_negative_explained: bool
    low_order_hard_gate_domain: str
    actual_eye_ssag_readback_role: str
    standard_eye_low_order_gate_passed: bool
    all_ray_health_passed: bool
    all_18_carriers_validated: bool
    calibration_count: int
    mechanism_decisions: tuple[MechanismDecision, ...]
    all_mechanisms_passed: bool
    tdd_999_evidence_complete: bool
    tdd_999_cleared: bool
    review_hash: str


def _require_dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Task007ReviewError(f"{label} must be an object")
    return value


def _finite(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise Task007ReviewError(f"{label} must be finite")
    return float(value)


def _review_hash(payload: dict[str, object]) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def review_task007_consolidated_payload(
    payload: dict[str, object],
    decisions: tuple[MechanismDecision, ...],
) -> Task007ReviewResult:
    if payload.get("phase") != EXPECTED_PHASE:
        raise Task007ReviewError("consolidated evidence phase identity mismatch")
    if payload.get("evidence_only") is not True:
        raise Task007ReviewError("consolidated input must be evidence-only")
    if payload.get("formal_artifact") is not False:
        raise Task007ReviewError("TASK-007 consolidated evidence must not be a formal artifact")
    if payload.get("tdd_999_cleared") is not False:
        raise Task007ReviewError("source evidence must predate TDD-999 clearance")
    if payload.get("shared_p0_count") != 6:
        raise Task007ReviewError("TASK-007 requires exactly six shared Q=0 P0 solves")
    if payload.get("carrier_count") != 18 or payload.get("all_18_carriers_validated") is not True:
        raise Task007ReviewError("TASK-007 requires exactly 18 validated provisional carriers")
    if payload.get("calibration_count") != 9:
        raise Task007ReviewError("TASK-007 requires exactly nine low/median/high calibrations")

    settings = _require_dict(payload.get("settings"), "settings")
    piston_tolerance = _finite(settings.get("piston_tolerance_um"), "piston tolerance")
    defocus_tolerance = _finite(
        settings.get("global_defocus_tolerance_d"), "global-defocus tolerance"
    )
    if piston_tolerance < 0.0 or defocus_tolerance < 0.0:
        raise Task007ReviewError("residual policy tolerances must be non-negative")

    residual_payloads = _require_dict(payload.get("residual_payloads"), "residual_payloads")
    if set(residual_payloads) != set(EXPECTED_PLATFORMS):
        raise Task007ReviewError("residual payloads must cover WFS/RAD/HOA exactly")

    calibration_evidence = _require_dict(
        payload.get("calibration_evidence"), "calibration_evidence"
    )
    if set(calibration_evidence) != set(EXPECTED_PLATFORMS):
        raise Task007ReviewError("calibration evidence must cover WFS/RAD/HOA exactly")

    standard_gate_passed = True
    ray_health_passed = True
    for platform in EXPECTED_PLATFORMS:
        records = _require_dict(calibration_evidence.get(platform), f"{platform} calibrations")
        if set(records) != set(EXPECTED_LABELS):
            raise Task007ReviewError(f"{platform} must contain low/median/high exactly")
        for label in EXPECTED_LABELS:
            record = _require_dict(records[label], f"{platform}/{label}")
            if record.get("carrier_id") in (None, ""):
                raise Task007ReviewError(f"{platform}/{label} carrier identity is missing")
            _finite(record.get("actual_power_d"), f"{platform}/{label} actual power")
            standard = _require_dict(
                record.get("standard_readback"), f"{platform}/{label} standard readback"
            )
            piston = abs(
                _finite(
                    standard.get("measured_piston_um"),
                    f"{platform}/{label} standard piston",
                )
            )
            defocus = abs(
                _finite(
                    standard.get("measured_global_defocus_d"),
                    f"{platform}/{label} standard global defocus",
                )
            )
            standard_gate_passed = standard_gate_passed and (
                piston <= piston_tolerance and defocus <= defocus_tolerance
            )
            mono_health = _require_dict(
                record.get("mono_ray_health"), f"{platform}/{label} MONO ray health"
            )
            edof_health = _require_dict(
                record.get("edof_ray_health"), f"{platform}/{label} EDOF ray health"
            )
            ray_health_passed = ray_health_passed and (
                mono_health.get("passed") is True and edof_health.get("passed") is True
            )

    if not standard_gate_passed:
        raise Task007ReviewError("standard-eye residual low-order hard gate did not pass")
    if not ray_health_passed:
        raise Task007ReviewError("one or more low/median/high ray-health checks failed")

    for decision in decisions:
        decision.validate()
    by_platform = {decision.platform_id: decision for decision in decisions}
    if len(decisions) != 3 or set(by_platform) != set(EXPECTED_PLATFORMS):
        raise Task007ReviewError("mechanism review requires exactly one WFS/RAD/HOA decision")
    ordered_decisions = tuple(by_platform[platform] for platform in EXPECTED_PLATFORMS)
    all_mechanisms_passed = all(decision.passed for decision in ordered_decisions)

    source_code_commit = str(payload.get("code_commit") or "").strip()
    source_report_hash = str(payload.get("local_report_sha256") or "").strip()
    if not source_code_commit or not source_report_hash:
        raise Task007ReviewError("source code/report provenance is incomplete")

    tdd_complete = standard_gate_passed and ray_health_passed and all_mechanisms_passed
    core: dict[str, object] = {
        "schema_version": 1,
        "phase": "TASK-007-CONSOLIDATED-WEB-REVIEW",
        "evidence_only": True,
        "formal_artifact": False,
        "source_phase": EXPECTED_PHASE,
        "source_code_commit": source_code_commit,
        "source_local_report_sha256": source_report_hash,
        "source_numerical_hard_gates_passed": bool(
            payload.get("numerical_hard_gates_passed")
        ),
        "source_false_negative_explained": payload.get("numerical_hard_gates_passed") is False,
        "low_order_hard_gate_domain": "STD_IOL_EYE_2024_EPD6_imported_residual_readback",
        "actual_eye_ssag_readback_role": "diagnostic_only_aperture_limited_mode0",
        "standard_eye_low_order_gate_passed": standard_gate_passed,
        "all_ray_health_passed": ray_health_passed,
        "all_18_carriers_validated": True,
        "calibration_count": 9,
        "mechanism_decisions": [asdict(item) for item in ordered_decisions],
        "all_mechanisms_passed": all_mechanisms_passed,
        "tdd_999_evidence_complete": tdd_complete,
        "tdd_999_cleared": tdd_complete,
    }
    return Task007ReviewResult(
        schema_version=1,
        phase="TASK-007-CONSOLIDATED-WEB-REVIEW",
        evidence_only=True,
        formal_artifact=False,
        source_phase=EXPECTED_PHASE,
        source_code_commit=source_code_commit,
        source_local_report_sha256=source_report_hash,
        source_numerical_hard_gates_passed=bool(payload.get("numerical_hard_gates_passed")),
        source_false_negative_explained=payload.get("numerical_hard_gates_passed") is False,
        low_order_hard_gate_domain="STD_IOL_EYE_2024_EPD6_imported_residual_readback",
        actual_eye_ssag_readback_role="diagnostic_only_aperture_limited_mode0",
        standard_eye_low_order_gate_passed=standard_gate_passed,
        all_ray_health_passed=ray_health_passed,
        all_18_carriers_validated=True,
        calibration_count=9,
        mechanism_decisions=ordered_decisions,
        all_mechanisms_passed=all_mechanisms_passed,
        tdd_999_evidence_complete=tdd_complete,
        tdd_999_cleared=tdd_complete,
        review_hash=_review_hash(core),
    )
