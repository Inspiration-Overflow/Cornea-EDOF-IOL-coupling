"""Plan and preflight the bounded R8 96-configuration production run.

The current repository can prove the exact R8 factor matrix and validate the completed
R6/R7 R5.2 serialized-model inputs. It does not expose, within this task's authorized
surface, a production acquisition adapter that consumes those pre-serialized model
paths without reapplying a legacy residual. Therefore ``--execute`` fails closed
before any OpticStudio session can be opened.

A later, explicitly authorized task may replace the implementation-gap guard once a
direct prebuilt-model pair-scale acquisition adapter exists and is unit/integration
tested against the frozen TASK-009 acquisition contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from whole_eye_mvp.domain import OpticState
from whole_eye_mvp.extension96_analysis import EXPECTED_DEFOCUS_GRID, PUPIL_MM
from whole_eye_mvp.revision_r5_2 import R5_2_FREEZE_ID
from whole_eye_mvp.revision_r6 import (
    R6_EXPECTED_CARRIER_COUNT,
    R6_R7_PHASE,
    expected_r6_carrier_keys,
)

TASK_ID = "r8-96-production-runner-20260822"
R8_PHASE = "MODEL-REVISION-R8-96-PRODUCTION"
R8_AUTHORIZATION_ID = TASK_ID
R6_R7_OUTPUT_RELATIVE = Path("diagnostics/model_revision/r6_r7")
R6_R7_REPORT_NAME = "MODEL_REVISION_R6_R7_EVIDENCE.json"
R8_OUTPUT_RELATIVE = Path("diagnostics/model_revision/r8_96")
R8_EVIDENCE_NAME = "MODEL_REVISION_R8_96_EVIDENCE.json"
R8_CONFIG_RESULTS_NAME = "MODEL_REVISION_R8_96_CONFIG_RESULTS.csv"
R8_THROUGH_FOCUS_NAME = "MODEL_REVISION_R8_96_THROUGH_FOCUS.csv"
R8_PAIRED_DELTAS_NAME = "MODEL_REVISION_R8_96_PAIRED_DELTAS.csv"

R8_EXPECTED_CONFIG_COUNT = 96
R8_EXPECTED_PAIR_COUNT = 48
R8_EXPECTED_THROUGH_FOCUS_ROWS = 1440
R8_EXPECTED_MODEL_COUNT = 48

MISSING_PREREQUISITE_ID = "DIRECT_R5_2_SERIALIZED_MODEL_PAIR_SCALE_BACKEND"

REQUIRED_R6_R7_LOCAL_CHECKS = (
    "all_24_carriers_present",
    "standard_eye_sa_all_passed",
    "wfs_hoa_serialized_mechanism_all_passed",
    "rad_real_powp_identity_regression_all_passed",
    "global_defocus_all_passed",
    "actual_eye_3_5mm_ray_health_all_passed",
    "binary4_geometry_all_passed",
    "selected_low_median_high_full_standard_audit_all_passed",
    "local_r6_r7_passed",
)


class R8PlanError(RuntimeError):
    """R8 factor-plan or R6/R7 input validation failed."""


class R8AuthorizationError(RuntimeError):
    """Explicit execution authorization was absent or invalid."""


@dataclass(frozen=True, slots=True)
class R8ConfigPlan:
    config_id: str
    pair_key: str
    carrier_id: str
    base_id: str
    cornea_id: str
    platform_id: str
    optic_state: str
    pupil_mm: float
    model_artifact_key: str


def _carrier_id(base_id: str, cornea_id: str, platform_id: str) -> str:
    return f"R6_{base_id}_{cornea_id}_{platform_id}"


def _state_values() -> tuple[str, str]:
    return (OpticState.MONO.value, OpticState.EDOF.value)


def _pupil_values() -> tuple[float, ...]:
    return tuple(float(value) for value in PUPIL_MM)


def focus_grid_d() -> tuple[float, ...]:
    """Return the accepted 15-plane through-focus grid without redefining it."""

    return tuple(float(value) for value in EXPECTED_DEFOCUS_GRID)


def build_r8_plan() -> tuple[R8ConfigPlan, ...]:
    """Build the deterministic 24-carrier x 2-state x 2-pupil R8 plan."""

    rows: list[R8ConfigPlan] = []
    for key in expected_r6_carrier_keys():
        carrier_id = _carrier_id(key.base_id, key.cornea_id, key.platform_id)
        for pupil_mm in _pupil_values():
            pupil_label = int(pupil_mm)
            pair_key = (
                f"R8_{key.base_id}_{key.cornea_id}_{key.platform_id}_EPD{pupil_label}"
            )
            for optic_state in _state_values():
                filename = f"ACTUAL_BINARY4_{optic_state}.zmx"
                rows.append(
                    R8ConfigPlan(
                        config_id=f"{pair_key}_{optic_state}",
                        pair_key=pair_key,
                        carrier_id=carrier_id,
                        base_id=key.base_id,
                        cornea_id=key.cornea_id,
                        platform_id=key.platform_id,
                        optic_state=optic_state,
                        pupil_mm=pupil_mm,
                        model_artifact_key=f"validated/{carrier_id}/{filename}",
                    )
                )
    plan = tuple(rows)
    validate_r8_plan(plan)
    return plan


def validate_r8_plan(plan: Sequence[R8ConfigPlan]) -> None:
    """Fail closed unless the plan is the exact approved 96-config factorial."""

    if len(plan) != R8_EXPECTED_CONFIG_COUNT:
        raise R8PlanError(
            f"R8 requires {R8_EXPECTED_CONFIG_COUNT} configs, got {len(plan)}"
        )

    config_ids = {row.config_id for row in plan}
    if len(config_ids) != R8_EXPECTED_CONFIG_COUNT:
        raise R8PlanError("R8 config IDs are not unique")

    expected_carriers = {
        (key.base_id, key.cornea_id, key.platform_id)
        for key in expected_r6_carrier_keys()
    }
    observed_carriers = {
        (row.base_id, row.cornea_id, row.platform_id)
        for row in plan
    }
    if len(expected_carriers) != R6_EXPECTED_CARRIER_COUNT:
        raise R8PlanError("R6 expected carrier key source is not exactly 24")
    if observed_carriers != expected_carriers:
        raise R8PlanError("R8 carrier coverage differs from the accepted R6 2x4x3 space")

    by_carrier: dict[str, list[R8ConfigPlan]] = defaultdict(list)
    by_pair: dict[str, list[R8ConfigPlan]] = defaultdict(list)
    for row in plan:
        by_carrier[row.carrier_id].append(row)
        by_pair[row.pair_key].append(row)

    if len(by_carrier) != R6_EXPECTED_CARRIER_COUNT:
        raise R8PlanError("R8 does not contain exactly 24 carrier identities")
    if any(len(rows) != 4 for rows in by_carrier.values()):
        raise R8PlanError("each R8 carrier must contribute 2 states x 2 pupils")

    if len(by_pair) != R8_EXPECTED_PAIR_COUNT:
        raise R8PlanError(
            f"R8 requires {R8_EXPECTED_PAIR_COUNT} matched pairs, got {len(by_pair)}"
        )
    expected_states = set(_state_values())
    for pair_key, rows in by_pair.items():
        if len(rows) != 2 or {row.optic_state for row in rows} != expected_states:
            raise R8PlanError(f"R8 pair is not exact MONO+EDOF: {pair_key}")
        identities = {
            (
                row.carrier_id,
                row.base_id,
                row.cornea_id,
                row.platform_id,
                row.pupil_mm,
            )
            for row in rows
        }
        if len(identities) != 1:
            raise R8PlanError(f"R8 matched carrier identity drift: {pair_key}")

    if {row.pupil_mm for row in plan} != set(_pupil_values()):
        raise R8PlanError("R8 physical pupil set differs from the accepted R6 3/5-mm set")
    if {row.optic_state for row in plan} != expected_states:
        raise R8PlanError("R8 optic-state set drift")

    grid = focus_grid_d()
    if len(grid) != 15:
        raise R8PlanError(f"R8 requires 15 through-focus planes, got {len(grid)}")
    if len(plan) * len(grid) != R8_EXPECTED_THROUGH_FOCUS_ROWS:
        raise R8PlanError("R8 through-focus row count is not exactly 1440")

    model_keys = {row.model_artifact_key for row in plan}
    if len(model_keys) != R8_EXPECTED_MODEL_COUNT:
        raise R8PlanError("R8 must resolve exactly 48 immutable MONO/EDOF model inputs")


def r8_contract_summary(plan: Sequence[R8ConfigPlan]) -> dict[str, object]:
    validate_r8_plan(plan)
    return {
        "task_id": TASK_ID,
        "phase": R8_PHASE,
        "r5_freeze_id": R5_2_FREEZE_ID,
        "carrier_count": R6_EXPECTED_CARRIER_COUNT,
        "config_count": len(plan),
        "matched_pairs": len({row.pair_key for row in plan}),
        "through_focus_planes_per_config": len(focus_grid_d()),
        "through_focus_rows": len(plan) * len(focus_grid_d()),
        "physical_pupils_mm": list(_pupil_values()),
        "optic_states": list(_state_values()),
        "focus_grid_retina_d": list(focus_grid_d()),
        "authorization_required": True,
        "execution_ready": False,
        "missing_prerequisite_id": MISSING_PREREQUISITE_ID,
    }


def _require_mapping(
    payload: Mapping[str, object],
    key: str,
) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise R8PlanError(f"R6/R7 evidence field must be an object: {key}")
    return value


def _is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def validate_r6_r7_evidence_payload(
    payload: Mapping[str, object],
    plan: Sequence[R8ConfigPlan],
) -> dict[str, str]:
    """Validate the completed R6/R7 evidence needed as immutable R8 input."""

    validate_r8_plan(plan)
    expected = {
        "schema_version": 1,
        "formal_artifact": False,
        "pilot": False,
        "phase": R6_R7_PHASE,
        "r5_freeze_id": R5_2_FREEZE_ID,
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
    }
    mismatches = {
        key: (payload.get(key), value)
        for key, value in expected.items()
        if payload.get(key) != value
    }
    if mismatches:
        raise R8PlanError(f"R6/R7 evidence identity mismatch: {mismatches}")

    local_checks = _require_mapping(payload, "local_checks")
    failed_checks = [
        key
        for key in REQUIRED_R6_R7_LOCAL_CHECKS
        if local_checks.get(key) is not True
    ]
    if failed_checks:
        raise R8PlanError(f"R6/R7 required local checks are not all true: {failed_checks}")

    contract = _require_mapping(payload, "contract")
    contract_expected = {
        "carrier_count": R6_EXPECTED_CARRIER_COUNT,
        "r5_2_hoa_q_ant_required": 0.0,
        "automatic_power_specific_refit_allowed": False,
        "mtf_used_in_mechanism_fit": False,
    }
    contract_mismatches = {
        key: (contract.get(key), value)
        for key, value in contract_expected.items()
        if contract.get(key) != value
    }
    if contract_mismatches:
        raise R8PlanError(f"R6/R7 contract mismatch: {contract_mismatches}")

    rule = _require_mapping(payload, "r5_2_hoa_a6_rule")
    rule_expected = {
        "id": R5_2_FREEZE_ID,
        "gate_feedback_used": False,
        "optimizer_used": False,
    }
    rule_mismatches = {
        key: (rule.get(key), value)
        for key, value in rule_expected.items()
        if rule.get(key) != value
    }
    if rule_mismatches or rule.get("zone_order") != [1, 2]:
        raise R8PlanError(
            "R6/R7 R5.2 HOA A6 rule identity/order differs from the frozen rule"
        )

    expected_carrier_ids = {row.carrier_id for row in plan}
    carriers = _require_mapping(payload, "carriers")
    if set(carriers) != expected_carrier_ids:
        raise R8PlanError(
            "R6/R7 carrier summary IDs differ from the exact 24-carrier R8 inputs"
        )

    artifact_hashes = _require_mapping(payload, "artifact_sha256")
    required_model_keys = sorted({row.model_artifact_key for row in plan})
    selected: dict[str, str] = {}
    for key in required_model_keys:
        value = artifact_hashes.get(key)
        if not _is_sha256(value):
            raise R8PlanError(f"R6/R7 evidence lacks a valid model SHA-256: {key}")
        selected[key] = str(value)
    if len(selected) != R8_EXPECTED_MODEL_COUNT:
        raise R8PlanError("R8 did not resolve exactly 48 R6/R7 serialized model hashes")
    return selected


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_r6_r7_model_files(
    project_dir: Path,
    model_hashes: Mapping[str, str],
) -> None:
    """Verify the 48 serialized MONO/EDOF model files against R6/R7 evidence."""

    root = project_dir / R6_R7_OUTPUT_RELATIVE
    for relative, expected_sha in model_hashes.items():
        path = root / relative
        if not path.is_file():
            raise R8PlanError(f"required R6/R7 serialized model is missing: {path}")
        actual = _sha256(path)
        if actual != expected_sha:
            raise R8PlanError(
                f"R6/R7 serialized model hash mismatch: {relative}: {actual} != {expected_sha}"
            )


def validate_execution_authorization(authorization_id: str | None) -> None:
    """Require an explicit local execution acknowledgement; fail closed by default."""

    if authorization_id != R8_AUTHORIZATION_ID:
        raise R8AuthorizationError(
            "R8 execution requires --authorization-id "
            f"{R8_AUTHORIZATION_ID!r}; planning/preflight do not require it"
        )


def implementation_gap() -> dict[str, object]:
    """Describe the exact prerequisite that prevents safe OpticStudio execution."""

    return {
        "id": MISSING_PREREQUISITE_ID,
        "blocks_opticstudio_execution": True,
        "required_capability": (
            "A production analysis adapter that accepts immutable pre-serialized "
            "R6/R7 ACTUAL_BINARY4_MONO/EDOF model paths and their expected SHA-256 "
            "values, then runs the existing paired-MONO angular-scale MTFA Grid=1 "
            "15-plane acquisition contract without reapplying a residual, refitting "
            "the IOL, or rebuilding the physical carrier."
        ),
        "reason": (
            "The authorized repository surface exposes the current R6/R7 serialized "
            "models and legacy carrier+residual production runners, but no authorized "
            "direct-model path adapter for the accepted R5.2 Binary4 inputs."
        ),
    }


def expected_r8_artifact_paths() -> tuple[str, ...]:
    """Return the minimum structured R8 outputs required after the gap is resolved."""

    return (
        str(R8_OUTPUT_RELATIVE / R8_EVIDENCE_NAME).replace("\\", "/"),
        str(R8_OUTPUT_RELATIVE / R8_CONFIG_RESULTS_NAME).replace("\\", "/"),
        str(R8_OUTPUT_RELATIVE / R8_THROUGH_FOCUS_NAME).replace("\\", "/"),
        str(R8_OUTPUT_RELATIVE / R8_PAIRED_DELTAS_NAME).replace("\\", "/"),
    )


def _load_json(path: Path) -> Mapping[str, object]:
    if not path.is_file():
        raise R8PlanError(f"required JSON is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise R8PlanError(f"JSON root must be an object: {path}")
    return payload


def preflight(project_dir: Path, evidence_path: Path | None = None) -> dict[str, object]:
    plan = build_r8_plan()
    report_path = (
        evidence_path
        if evidence_path is not None
        else project_dir / R6_R7_OUTPUT_RELATIVE / R6_R7_REPORT_NAME
    )
    payload = _load_json(report_path)
    hashes = validate_r6_r7_evidence_payload(payload, plan)
    verify_r6_r7_model_files(project_dir, hashes)
    return {
        **r8_contract_summary(plan),
        "r6_r7_evidence_path": str(report_path.resolve()),
        "r6_r7_serialized_model_hashes_verified": len(hashes),
        "input_preflight_passed": True,
        "expected_r8_artifacts": list(expected_r8_artifact_paths()),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "project_mvp_2026_v2_zmx",
    )
    parser.add_argument(
        "--r6-r7-evidence",
        type=Path,
        help=(
            "Optional explicit R6/R7 evidence JSON; defaults to the project "
            "diagnostics path."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan-only", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--authorization-id",
        help=(
            "Required only with --execute; operational acknowledgement, not a "
            "scientific result."
        ),
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    plan = build_r8_plan()

    if args.execute:
        validate_execution_authorization(args.authorization_id)
        status = preflight(args.project_dir.resolve(), args.r6_r7_evidence)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        gap = implementation_gap()
        raise SystemExit(
            "STOP: R8 OpticStudio execution is not implemented in this authorized "
            f"surface. Missing prerequisite {gap['id']}."
        )

    if args.preflight:
        payload = preflight(args.project_dir.resolve(), args.r6_r7_evidence)
    else:
        payload = r8_contract_summary(plan)
    payload = {**payload, "implementation_gap": implementation_gap()}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
