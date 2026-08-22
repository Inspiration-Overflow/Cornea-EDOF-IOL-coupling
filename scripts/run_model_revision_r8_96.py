"""Plan, preflight, and execute the bounded R8 96-configuration direct-model run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from whole_eye_mvp import __version__
from whole_eye_mvp.analysis_zos_pair_scale import (
    EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
    PAIR_MONO_FREQUENCY_SCALE_MODE,
    TASK009_PAIR_MONO_MTF_ACQUISITION,
)
from whole_eye_mvp.analysis_zos_r8_direct import (
    DIRECT_MODEL_PROVENANCE_POLICY_HASH,
    DIRECT_MODEL_PROVENANCE_POLICY_ID,
    artifact_hashes,
    build_direct_model_specs,
    run_r8_direct_acquisition,
    verify_direct_model_sources,
    write_r8_aggregate_outputs,
)
from whole_eye_mvp.domain import NOMINAL_MAIN_FFT_MTF_555_V2, OpticState
from whole_eye_mvp.extension96_analysis import EXPECTED_DEFOCUS_GRID, PUPIL_MM
from whole_eye_mvp.quality import settings_hash
from whole_eye_mvp.revision_r5_2 import R5_2_FREEZE_ID
from whole_eye_mvp.revision_r6 import (
    R6_EXPECTED_CARRIER_COUNT,
    R6_R7_PHASE,
    expected_r6_carrier_keys,
)
from whole_eye_mvp.zos import open_zos_session

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
INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"

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
            pair_key = f"{carrier_id}_EPD{pupil_mm:g}"
            for optic_state in _state_values():
                filename = f"ACTUAL_BINARY4_{optic_state}.zmx"
                rows.append(
                    R8ConfigPlan(
                        config_id=f"R8_{carrier_id}_{optic_state}_EPD{pupil_label}",
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
    if len({row.config_id for row in plan}) != R8_EXPECTED_CONFIG_COUNT:
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
        expected_pair = f"{rows[0].carrier_id}_EPD{rows[0].pupil_mm:g}"
        if pair_key != expected_pair:
            raise R8PlanError(f"R8 pair key is not canonical: {pair_key}")

    if {row.pupil_mm for row in plan} != set(_pupil_values()):
        raise R8PlanError("R8 physical pupil set differs from the accepted R6 3/5-mm set")
    if {row.optic_state for row in plan} != expected_states:
        raise R8PlanError("R8 optic-state set drift")
    grid = focus_grid_d()
    if len(grid) != 15:
        raise R8PlanError(f"R8 requires 15 through-focus planes, got {len(grid)}")
    if len(plan) * len(grid) != R8_EXPECTED_THROUGH_FOCUS_ROWS:
        raise R8PlanError("R8 through-focus row count is not exactly 1440")
    if len({row.model_artifact_key for row in plan}) != R8_EXPECTED_MODEL_COUNT:
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
        "direct_model_adapter_implemented": True,
        "execution_ready_after_preflight": True,
        "missing_prerequisite_id": None,
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
                f"R6/R7 serialized model hash mismatch: {relative}: "
                f"{actual} != {expected_sha}"
            )


def validate_execution_authorization(authorization_id: str | None) -> None:
    """Require an explicit local execution acknowledgement; fail closed by default."""

    if authorization_id != R8_AUTHORIZATION_ID:
        raise R8AuthorizationError(
            "R8 execution requires --authorization-id "
            f"{R8_AUTHORIZATION_ID!r}; planning/preflight do not require it"
        )


def expected_r8_artifact_paths() -> tuple[str, ...]:
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


def _preflight_inputs(
    project_dir: Path,
    evidence_path: Path | None = None,
) -> tuple[tuple[R8ConfigPlan, ...], dict[str, str], Path, dict[str, object]]:
    plan = build_r8_plan()
    report_path = (
        evidence_path.resolve()
        if evidence_path is not None
        else project_dir / R6_R7_OUTPUT_RELATIVE / R6_R7_REPORT_NAME
    )
    payload = _load_json(report_path)
    hashes = validate_r6_r7_evidence_payload(payload, plan)
    verify_r6_r7_model_files(project_dir, hashes)
    status = {
        **r8_contract_summary(plan),
        "r6_r7_evidence_path": str(report_path.resolve()),
        "r6_r7_evidence_sha256": _sha256(report_path),
        "r6_r7_serialized_model_hashes_verified": len(hashes),
        "input_preflight_passed": True,
        "expected_r8_artifacts": list(expected_r8_artifact_paths()),
    }
    return plan, hashes, report_path.resolve(), status


def preflight(project_dir: Path, evidence_path: Path | None = None) -> dict[str, object]:
    return _preflight_inputs(project_dir, evidence_path)[3]


def _clean_git_head() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise SystemExit("R8 execution requires a clean tracked Git checkout")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(head) != 40:
        raise SystemExit("R8 execution could not resolve canonical Git HEAD")
    return head


def _opticstudio_version(session) -> str:
    for name in ("OpticStudioVersion", "ZOSVersion", "Version"):
        value = getattr(session.app, name, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise RuntimeError("installed application exposes no OpticStudio version string")


def _pair_reference_set_hash(records: Mapping[str, Mapping[str, object]]) -> str:
    if len(records) != R8_EXPECTED_PAIR_COUNT:
        raise R8PlanError("R8 requires exactly 48 pair-reference records")
    text = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _formal_evidence(
    *,
    code_commit: str,
    opticstudio_version: str,
    run_id: str,
    preflight_status: Mapping[str, object],
    r6_r7_evidence_path: Path,
    direct_run,
    diagnostics: Mapping[str, Mapping[str, object]],
    aggregate_paths: Mapping[str, Path],
    output_root: Path,
) -> dict[str, object]:
    pair_records = {
        key: asdict(value)
        for key, value in sorted(direct_run.pair_references.items())
    }
    source_hashes = dict(sorted(direct_run.source_model_sha256.items()))
    if len(source_hashes) != R8_EXPECTED_MODEL_COUNT:
        raise R8PlanError("formal R8 evidence requires exactly 48 source model hashes")
    if len(direct_run.results) != R8_EXPECTED_CONFIG_COUNT:
        raise R8PlanError("formal R8 evidence requires exactly 96 ConfigResults")
    if len(direct_run.paired_deltas) != R8_EXPECTED_PAIR_COUNT:
        raise R8PlanError("formal R8 evidence requires exactly 48 matched deltas")
    if len(direct_run.through_focus_rows) != R8_EXPECTED_THROUGH_FOCUS_ROWS:
        raise R8PlanError("formal R8 evidence requires exactly 1440 through-focus rows")

    artifact_map = artifact_hashes(
        output_root,
        exclude_names=(R8_EVIDENCE_NAME,),
    )
    if not artifact_map:
        raise R8PlanError("formal R8 evidence has no runtime artifact hash map")
    aggregate_hashes = {
        name: _sha256(path)
        for name, path in aggregate_paths.items()
    }
    if any(not value for value in aggregate_hashes.values()):
        raise R8PlanError("formal R8 aggregate output hash is missing")

    return {
        "schema_version": 1,
        "formal_artifact": True,
        "pilot": False,
        "phase": R8_PHASE,
        "task_id": TASK_ID,
        "run_id": run_id,
        "code_commit": code_commit,
        "package_version": __version__,
        "opticstudio_version": opticstudio_version,
        "r5_freeze_id": R5_2_FREEZE_ID,
        "source_r6_r7_evidence_path": str(r6_r7_evidence_path),
        "source_r6_r7_evidence_sha256": str(
            preflight_status["r6_r7_evidence_sha256"]
        ),
        "source_model_sha256": source_hashes,
        "direct_model_provenance_policy_id": DIRECT_MODEL_PROVENANCE_POLICY_ID,
        "direct_model_provenance_policy_hash": DIRECT_MODEL_PROVENANCE_POLICY_HASH,
        "legacy_residual_reapplied": False,
        "carrier_rebuilt": False,
        "iol_refit": False,
        "analysis_settings_id": NOMINAL_MAIN_FFT_MTF_555_V2.settings_id,
        "analysis_settings_sha256": settings_hash(NOMINAL_MAIN_FFT_MTF_555_V2),
        "acquisition_contract_id": TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id,
        "acquisition_contract_sha256": EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
        "frequency_scale_mode": PAIR_MONO_FREQUENCY_SCALE_MODE,
        "production_sampling": NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
        "pair_references": pair_records,
        "pair_reference_count": len(pair_records),
        "pair_reference_set_sha256": _pair_reference_set_hash(pair_records),
        "completed_configs": len(direct_run.results),
        "failed_configs": 0,
        "matched_pairs": len(direct_run.paired_deltas),
        "through_focus_rows": len(direct_run.through_focus_rows),
        "config_results_csv_sha256": aggregate_hashes["config_csv"],
        "through_focus_csv_sha256": aggregate_hashes["through_focus_csv"],
        "paired_deltas_csv_sha256": aggregate_hashes["paired_csv"],
        "config_diagnostics": diagnostics,
        "artifact_sha256": artifact_map,
        "local_r8_passed": True,
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
        "next_gate": "STOP for Web R8 review; no automatic progression",
    }


def execute_r8(
    *,
    install_dir: Path,
    project_dir: Path,
    evidence_path: Path | None,
) -> dict[str, object]:
    code_commit = _clean_git_head()
    plan, hashes, r6_r7_evidence_path, status = _preflight_inputs(
        project_dir,
        evidence_path,
    )
    specs = build_direct_model_specs(
        project_dir,
        plan,
        hashes,
        r6_r7_output_relative=R6_R7_OUTPUT_RELATIVE,
    )
    verify_direct_model_sources(specs)

    output_root = (project_dir / R8_OUTPUT_RELATIVE).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"R8 runtime output directory is not empty: {output_root}")
    run_id = f"r8-{uuid.uuid4().hex}"

    with open_zos_session(install_dir) as session:
        opticstudio_version = _opticstudio_version(session)
        direct_run, diagnostics = run_r8_direct_acquisition(
            session,
            project_dir=project_dir,
            specs=specs,
            output_root=output_root,
            run_id=run_id,
        )

    aggregate_paths = write_r8_aggregate_outputs(
        direct_run,
        output_root=output_root,
        config_csv_name=R8_CONFIG_RESULTS_NAME,
        through_focus_csv_name=R8_THROUGH_FOCUS_NAME,
        paired_csv_name=R8_PAIRED_DELTAS_NAME,
    )
    evidence = _formal_evidence(
        code_commit=code_commit,
        opticstudio_version=opticstudio_version,
        run_id=run_id,
        preflight_status=status,
        r6_r7_evidence_path=r6_r7_evidence_path,
        direct_run=direct_run,
        diagnostics=diagnostics,
        aggregate_paths=aggregate_paths,
        output_root=output_root,
    )
    evidence_path_out = output_root / R8_EVIDENCE_NAME
    evidence_path_out.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "report_path": str(evidence_path_out),
        "run_id": run_id,
        "completed_configs": evidence["completed_configs"],
        "matched_pairs": evidence["matched_pairs"],
        "through_focus_rows": evidence["through_focus_rows"],
        "local_r8_passed": evidence["local_r8_passed"],
        "manual_web_review_required": True,
        "automatic_progression_allowed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-dir", type=Path, default=os.environ.get(INSTALL_ENV))
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument(
        "--r6-r7-evidence",
        type=Path,
        help="Optional explicit R6/R7 evidence JSON; defaults to project diagnostics.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan-only", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--authorization-id",
        help="Required only with --execute; operational acknowledgement, not a result.",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    project_dir = args.project_dir.resolve()
    if args.execute:
        validate_execution_authorization(args.authorization_id)
        if args.install_dir is None:
            raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")
        payload = execute_r8(
            install_dir=Path(args.install_dir),
            project_dir=project_dir,
            evidence_path=args.r6_r7_evidence,
        )
    elif args.preflight:
        payload = preflight(project_dir, args.r6_r7_evidence)
    else:
        payload = r8_contract_summary(build_r8_plan())
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
