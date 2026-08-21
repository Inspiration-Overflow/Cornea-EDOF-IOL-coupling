"""Run TASK-009 representative validation with one angular scale per matched pair.

The spatial-frequency coordinate is defined once from the frozen residual-free MONO
carrier of each pair and then reused for MONO, EDOF, every defocus plane, and every
sampling size. This prevents a high-order residual from redefining the cpd axis used to
judge its own MTF effect.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp import __version__
from whole_eye_mvp.analysis import ConfigResult, matched_pair_delta, validate_completed_result
from whole_eye_mvp.analysis_zos_pair_scale import (
    EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
    TASK009_PAIR_MONO_MTF_ACQUISITION,
    PairAngularScaleReference,
    ZosMtfaPairScaleAnalysisBackend,
    measure_pair_mono_reference,
)
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    NOMINAL_MAIN_FFT_MTF_555_V2,
    OpticState,
    RunEnvironment,
    ScientificBaseline,
)
from whole_eye_mvp.manifest import ManifestBundle, NominalConfig, compute_lock_set_hash
from whole_eye_mvp.manifest_io import load_formal_manifest_bundle
from whole_eye_mvp.quality import settings_hash
from whole_eye_mvp.store import open_project_store, sha256_file
from whole_eye_mvp.workflows import run_analysis_batch
from whole_eye_mvp.zos import (
    TASK009_MFE_FULL_HOA_555_V1,
    MfeMtfGridRunner,
    MfeMtfGridSettings,
    open_zos_session,
)

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
TASK008_EVIDENCE = REPOSITORY_ROOT / "docs/evidence/task008/TASK_008_LOCK_MANIFEST_EVIDENCE.json"
PRIOR_TASK009_EVIDENCE = (
    REPOSITORY_ROOT / "docs/evidence/task009/TASK_009_MTFA_GRID1_REPRESENTATIVE_EVIDENCE.json"
)
OUTPUT_REL = Path("diagnostics/task009/mtfa_grid1_pair_mono_scale")
LOCAL_REPORT = "TASK_009_PAIR_MONO_SCALE_REPRESENTATIVE.json"
REPO_EVIDENCE_DIR = REPOSITORY_ROOT / "docs/evidence/task009"
REPO_EVIDENCE_NAME = "TASK_009_PAIR_MONO_SCALE_REPRESENTATIVE_EVIDENCE.json"
REPO_TF_CSV = "TASK_009_PAIR_MONO_SCALE_REPRESENTATIVE_THROUGH_FOCUS.csv"

REPRESENTATIVES = (
    ("LB_AL2395", "A0", "WFS", 3.0),
    ("ATC_M3_AL24477", "B0", "RAD", 5.0),
    ("ATC_M3_AL24477", "C0", "HOA", 5.0),
)
CONVERGENCE_REL_TOL = 0.02
CONVERGENCE_DEFOCUS_TOL_D = 0.25
CONVERGENCE_DOF50_TOL_D = 0.25
REPEAT_REL_TOL = 0.001
REPEAT_ZERNIKE_TOL_UM = 0.001
CROSSCHECK_CPD = (20.0, 40.0, 60.0)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-dir", type=Path, default=os.environ.get(INSTALL_ENV))
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-repo-evidence", action="store_true")
    return parser


def _git_head() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise SystemExit("TASK-009 requires a clean tracked checkout")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(head) != 40:
        raise SystemExit("TASK-009 could not resolve a canonical Git commit")
    return head


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"required JSON is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON root must be an object: {path}")
    return payload


def _prepare_output(path: Path, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise SystemExit(f"TASK-009 output exists; pass --overwrite: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _relative_change(first: float, second: float) -> float:
    scale = max(abs(first), abs(second), 1.0e-15)
    return abs(first - second) / scale


def _select_pair(
    bundle: ManifestBundle,
    base_id: str,
    cornea_id: str,
    platform_id: str,
    pupil_mm: float,
) -> tuple[NominalConfig, NominalConfig]:
    matches = tuple(
        config
        for config in bundle.nominal_configs
        if config.base_id == base_id
        and config.cornea_id == cornea_id
        and config.platform_id == platform_id
        and config.pupil_mm == pupil_mm
    )
    if len(matches) != 2:
        raise SystemExit(
            "frozen manifest does not contain exactly one MONO/EDOF pair for "
            f"{base_id}/{cornea_id}/{platform_id}/EPD{pupil_mm:g}"
        )
    mono_config = next(
        (config for config in matches if config.optic_state == OpticState.MONO), None
    )
    edof_config = next(
        (config for config in matches if config.optic_state == OpticState.EDOF), None
    )
    if (
        mono_config is None
        or edof_config is None
        or mono_config.pair_key != edof_config.pair_key
    ):
        raise SystemExit("representative frozen manifest pair is malformed")
    return mono_config, edof_config


def _check_convergence(nominal: ConfigResult, high: ConfigResult) -> dict[str, object]:
    peak_mtfa_rel = _relative_change(nominal.distance_peak_mtfa, high.distance_peak_mtfa)
    tf_mean_rel = _relative_change(nominal.tf_mtfa_mean, high.tf_mtfa_mean)
    peak_shift = abs(nominal.distance_peak_retina_d - high.distance_peak_retina_d)
    dof50_change = abs(nominal.dof50_width_d - high.dof50_width_d)
    passed = (
        peak_mtfa_rel <= CONVERGENCE_REL_TOL
        and tf_mean_rel <= CONVERGENCE_REL_TOL
        and peak_shift <= CONVERGENCE_DEFOCUS_TOL_D
        and dof50_change <= CONVERGENCE_DOF50_TOL_D
    )
    return {
        "distance_peak_mtfa_relative_change_128_to_256": peak_mtfa_rel,
        "tf_mtfa_mean_relative_change_128_to_256": tf_mean_rel,
        "distance_peak_shift_d_128_to_256": peak_shift,
        "dof50_width_change_d_128_to_256": dof50_change,
        "passed": passed,
    }


def _check_repeatability(first: ConfigResult, second: ConfigResult) -> dict[str, object]:
    peak_rel = _relative_change(first.distance_peak_mtfa, second.distance_peak_mtfa)
    tf_rel = _relative_change(first.tf_mtfa_mean, second.tf_mtfa_mean)
    c40_delta = abs(first.aberrations.c40_um - second.aberrations.c40_um)
    c60_delta = abs(first.aberrations.c60_um - second.aberrations.c60_um)
    same_peak_sample = first.distance_peak_retina_d == second.distance_peak_retina_d
    passed = (
        peak_rel <= REPEAT_REL_TOL
        and tf_rel <= REPEAT_REL_TOL
        and c40_delta <= REPEAT_ZERNIKE_TOL_UM
        and c60_delta <= REPEAT_ZERNIKE_TOL_UM
        and same_peak_sample
    )
    return {
        "distance_peak_mtfa_relative_change": peak_rel,
        "tf_mtfa_mean_relative_change": tf_rel,
        "c40_abs_delta_um": c40_delta,
        "c60_abs_delta_um": c60_delta,
        "same_distance_peak_grid_sample": same_peak_sample,
        "passed": passed,
    }


def _summary(result: ConfigResult) -> dict[str, object]:
    return {
        "config_id": result.config.config_id,
        "pair_key": result.config.pair_key,
        "state": str(result.config.optic_state),
        "pupil_mm": result.config.pupil_mm,
        "distance_peak_retina_d": result.distance_peak_retina_d,
        "distance_peak_mtfa": result.distance_peak_mtfa,
        "mtfa_at_zero_d": result.mtfa_at_zero_d,
        "dof50_far_d": result.dof50_far_d,
        "dof50_near_d": result.dof50_near_d,
        "dof50_width_d": result.dof50_width_d,
        "tf_mtfa_mean": result.tf_mtfa_mean,
        "c40_um": result.aberrations.c40_um,
        "c60_um": result.aberrations.c60_um,
        "hoa_rms_um": result.aberrations.hoa_rms_um,
        "model_hash": result.model_hash_before,
        "entity_fingerprint": result.entity_fingerprint_before,
        "analysis_settings_hash": result.analysis_settings_hash,
        "hoa_settings_id": result.hoa_settings_id,
        "hoa_settings_hash": result.hoa_settings_hash,
    }


def _pair_result_block(
    mono_result: ConfigResult,
    edof_result: ConfigResult,
) -> tuple[str, dict[str, object]]:
    """Pure report assembly kept separate to catch ConfigResult/NominalConfig mixups."""

    delta = matched_pair_delta(mono_result, edof_result)
    pair_key = edof_result.config.pair_key
    if pair_key != mono_result.config.pair_key or pair_key != delta.pair_key:
        raise ValueError("matched pair report identity is inconsistent")
    return pair_key, {
        "mono": _summary(mono_result),
        "edof": _summary(edof_result),
        "paired_deltas": dict(delta.deltas),
        "delta_f_residual_d": delta.deltas["distance_peak_retina_d"],
    }


def _opticstudio_version(session) -> str:
    for name in ("OpticStudioVersion", "ZOSVersion", "Version"):
        value = getattr(session.app, name, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise RuntimeError("installed application exposes no OpticStudio version string")


def _mtf_crosscheck(
    session,
    result: ConfigResult,
    backend_diagnostics: dict[str, object],
) -> dict[str, object]:
    session.system.LoadFile(str(Path(result.artifacts.zos_path).resolve()), False)
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(result.config.pupil_mm)
    pair_scale = float(backend_diagnostics["pair_mm_per_degree"])
    frequencies_mm = tuple(float(frequency / pair_scale) for frequency in CROSSCHECK_CPD)
    runner = MfeMtfGridRunner(session.system, session.zosapi)

    def acquire(kind: str):
        return runner.run(
            MfeMtfGridSettings(
                frequencies_cyc_per_mm=frequencies_mm,
                sampling_grid_size=NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling,
                operand_type=kind,
                grid=1,
                data_type=0,
            )
        )

    avg = acquire("MTFA")
    tan = acquire("MTFT")
    sag = acquire("MTFS")
    zero = next(row for row in result.rows if abs(row.defocus_retina_d) <= 1.0e-12)
    production_values = (zero.mtf20, zero.mtf40, zero.mtf60)
    direction_average = tuple(
        0.5 * (t + s) for t, s in zip(tan.values, sag.values, strict=True)
    )
    return {
        "defocus_retina_d": 0.0,
        "cpd": CROSSCHECK_CPD,
        "cycles_per_mm": frequencies_mm,
        "pair_reference_effl_mm": backend_diagnostics["pair_reference_effl_mm"],
        "pair_mm_per_degree": pair_scale,
        "state_diagnostic_effl_mm": backend_diagnostics["state_diagnostic_effl_mm"],
        "production_mtfa": production_values,
        "repeat_mtfa_grid1": avg.values,
        "mtft_grid1": tan.values,
        "mtfs_grid1": sag.values,
        "mean_mtft_mtfs": direction_average,
        "production_vs_repeat_mtfa_abs": tuple(
            abs(left - right)
            for left, right in zip(production_values, avg.values, strict=True)
        ),
        "mtfa_vs_direction_average_abs": tuple(
            abs(left - right) for left, right in zip(avg.values, direction_average, strict=True)
        ),
        "parameter_headers": avg.parameter_headers,
        "diagnostic_only_no_new_threshold": True,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write empty TASK-009 CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sanitize(value):
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if "path" not in key.casefold()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")
    if TASK009_PAIR_MONO_MTF_ACQUISITION.contract_hash != EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH:
        raise SystemExit("paired-MONO MTF acquisition contract hash drifted")

    code_commit = _git_head()
    project_dir = args.project_dir.resolve()
    task008 = _load_json(TASK008_EVIDENCE)
    if (
        task008.get("formal_artifact") is not True
        or task008.get("tdd_999_cleared") is not True
        or task008.get("carrier_count") != 18
        or task008.get("nominal_config_count") != 72
    ):
        raise SystemExit("TASK-009 requires the frozen TASK-008 formal evidence")

    manifest_artifacts = task008.get("manifest_artifact_sha256")
    if not isinstance(manifest_artifacts, dict):
        raise TypeError("TASK-008 evidence lacks manifest artifact hashes")
    bundle = load_formal_manifest_bundle(
        project_dir,
        expected_manifest_hash=str(task008.get("manifest_hash", "")),
        expected_physical_csv_sha256=str(manifest_artifacts.get("TASK008_PHYSICAL_CARRIER_LOCKS", "")),
        expected_nominal_csv_sha256=str(manifest_artifacts.get("TASK008_NOMINAL_72", "")),
    )
    lock_set_hash = compute_lock_set_hash(bundle.physical_carriers)
    if lock_set_hash != task008.get("lock_set_hash"):
        raise SystemExit("rebuilt formal lock-set hash differs from TASK-008 evidence")

    carrier_hashes = task008.get("carrier_asset_sha256")
    residual_hashes = task008.get("residual_asset_sha256")
    if not isinstance(carrier_hashes, dict) or not isinstance(residual_hashes, dict):
        raise TypeError("TASK-008 evidence lacks carrier/residual asset hashes")

    output = project_dir / OUTPUT_REL
    _prepare_output(output, args.overwrite)
    settings = NOMINAL_MAIN_FFT_MTF_555_V2
    settings.validate()
    store = open_project_store(project_dir, ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID))

    pairs = tuple(_select_pair(bundle, *spec) for spec in REPRESENTATIVES)
    selected_ids = tuple(config.config_id for pair in pairs for config in pair)
    convergence: dict[str, object] = {}
    all_convergence_passed = True
    all_repeatability_passed = True

    with open_zos_session(args.install_dir) as session:
        opticstudio_version = _opticstudio_version(session)

        pair_references: dict[str, PairAngularScaleReference] = {}
        for mono_config, edof_config in pairs:
            if mono_config.pair_key != edof_config.pair_key:
                raise RuntimeError("internal representative pair identity mismatch")
            reference = measure_pair_mono_reference(
                session,
                project_dir,
                carrier_hashes,
                residual_hashes,
                mono_config,
                output / "pair_reference" / mono_config.pair_key / "mono_reference.zmx",
            )
            if reference.pair_key in pair_references:
                raise RuntimeError(f"duplicate pair angular-scale reference: {reference.pair_key}")
            pair_references[reference.pair_key] = reference

        pair_reference_effl_mm = {
            pair_key: reference.reference_effl_mm
            for pair_key, reference in pair_references.items()
        }

        for _mono_config, edof_config in pairs:
            pair_key = edof_config.pair_key
            samples: dict[str, ConfigResult] = {}
            sample_diagnostics: dict[str, object] = {}
            for sampling in settings.fft_mtf_convergence_samplings:
                backend = ZosMtfaPairScaleAnalysisBackend(
                    session,
                    project_dir,
                    carrier_hashes,
                    residual_hashes,
                    sampling=sampling,
                    pair_reference_effl_mm=pair_reference_effl_mm,
                )
                result = backend.run_config(
                    edof_config,
                    output / "convergence" / pair_key / str(sampling),
                    f"task009-pair-scale-convergence-{sampling}",
                )
                validate_completed_result(result, require_files=True, expected_config=edof_config)
                samples[str(sampling)] = result
                sample_diagnostics[str(sampling)] = backend.diagnostics[edof_config.config_id]

            repeat_backend = ZosMtfaPairScaleAnalysisBackend(
                session,
                project_dir,
                carrier_hashes,
                residual_hashes,
                sampling=settings.fft_mtf_sampling,
                pair_reference_effl_mm=pair_reference_effl_mm,
            )
            repeat128 = repeat_backend.run_config(
                edof_config,
                output / "repeatability" / pair_key,
                "task009-pair-scale-repeat-128",
            )
            validate_completed_result(repeat128, require_files=True, expected_config=edof_config)
            convergence_gate = _check_convergence(samples["128"], samples["256"])
            repeatability_gate = _check_repeatability(samples["128"], repeat128)
            all_convergence_passed = all_convergence_passed and bool(convergence_gate["passed"])
            all_repeatability_passed = all_repeatability_passed and bool(repeatability_gate["passed"])
            convergence[pair_key] = {
                "frozen_manifest_config_id": edof_config.config_id,
                "pair_reference": asdict(pair_references[pair_key]),
                "sampling_results": {name: _summary(value) for name, value in samples.items()},
                "sampling_diagnostics": sample_diagnostics,
                "repeat_128": _summary(repeat128),
                "repeat_128_diagnostics": repeat_backend.diagnostics[edof_config.config_id],
                "convergence_gate": convergence_gate,
                "repeatability_gate": repeatability_gate,
            }

        integration_backend = ZosMtfaPairScaleAnalysisBackend(
            session,
            project_dir,
            carrier_hashes,
            residual_hashes,
            sampling=settings.fft_mtf_sampling,
            pair_reference_effl_mm=pair_reference_effl_mm,
        )
        environment = RunEnvironment(
            f"{__version__}+git.{code_commit[:12]}+pair-scale-v2",
            opticstudio_version,
            CURRENT_SCIENTIFIC_BASELINE_ID,
            settings.settings_id,
            bundle.manifest_hash,
            lock_set_hash,
        )
        integration_run = run_analysis_batch(
            integration_backend,
            bundle,
            project_dir / "results" / "task009_pair_mono_scale_representative",
            store=store,
            environment=environment,
            selection=selected_ids,
            require_files=True,
        )
        integration_passed = len(integration_run.completed) == 6 and not integration_run.failed
        integration: dict[str, object] = {
            "run_id": integration_run.run_id,
            "environment_ref": integration_run.environment_ref,
            "completed_config_ids": [outcome.config_id for outcome in integration_run.completed],
            "failed": [
                {
                    "config_id": outcome.config_id,
                    "error_type": outcome.error_type,
                    "error_message": outcome.error_message,
                }
                for outcome in integration_run.failed
            ],
            "production_workflow_exercised": True,
            "pair_fixed_angular_scale": True,
            "passed": integration_passed,
            "pairs": {},
        }
        crosschecks: dict[str, object] = {}
        csv_rows: list[dict[str, object]] = []
        result_by_id = {
            outcome.config_id: outcome.result
            for outcome in integration_run.completed
            if outcome.result is not None
        }
        pair_block = integration["pairs"]
        if not isinstance(pair_block, dict):
            raise TypeError("internal integration pair block is invalid")

        for mono_config, edof_config in pairs:
            mono_result = result_by_id.get(mono_config.config_id)
            edof_result = result_by_id.get(edof_config.config_id)
            if mono_result is None or edof_result is None:
                continue
            pair_key, block = _pair_result_block(mono_result, edof_result)
            pair_block[pair_key] = block
            crosschecks[pair_key] = _mtf_crosscheck(
                session,
                edof_result,
                integration_backend.diagnostics[edof_result.config.config_id],
            )
            for state, config_result in (("MONO", mono_result), ("EDOF", edof_result)):
                for row in config_result.rows:
                    csv_rows.append(
                        {
                            "config_id": config_result.config.config_id,
                            "pair_key": config_result.config.pair_key,
                            "state": state,
                            "sampling": settings.fft_mtf_sampling,
                            **asdict(row),
                        }
                    )

    report: dict[str, object] = {
        "schema_version": 3,
        "phase": "TASK-009-MTFA-GRID1-PAIR-MONO-SCALE-REPRESENTATIVE",
        "evidence_only": True,
        "formal_artifact": False,
        "run72_started": False,
        "code_commit": code_commit,
        "task008_evidence_sha256": sha256_file(TASK008_EVIDENCE),
        "prior_task009_evidence_sha256": (
            sha256_file(PRIOR_TASK009_EVIDENCE) if PRIOR_TASK009_EVIDENCE.is_file() else None
        ),
        "task008_manifest_hash": bundle.manifest_hash,
        "task008_lock_set_hash": lock_set_hash,
        "analysis_settings": asdict(settings),
        "analysis_settings_hash": settings_hash(settings),
        "mtf_acquisition_contract": asdict(TASK009_PAIR_MONO_MTF_ACQUISITION),
        "mtf_acquisition_contract_hash": TASK009_PAIR_MONO_MTF_ACQUISITION.contract_hash,
        "frequency_scale_mode": "paired_residual_free_MONO_EFFL",
        "pair_angular_scale_references": {
            pair_key: asdict(reference) for pair_key, reference in pair_references.items()
        },
        "hoa_settings": asdict(TASK009_MFE_FULL_HOA_555_V1),
        "hoa_settings_hash": TASK009_MFE_FULL_HOA_555_V1.settings_hash,
        "representative_manifest_config_ids": selected_ids,
        "convergence": convergence,
        "integration": integration,
        "crosschecks": crosschecks,
        "all_convergence_passed": all_convergence_passed,
        "all_repeatability_passed": all_repeatability_passed,
        "all_six_config_integration_passed": integration_passed,
        "crosscheck_review_pending_web": True,
        "production_sampling_candidate_passed": (
            all_convergence_passed and all_repeatability_passed and integration_passed
        ),
        "production_sampling_locked": False,
        "sampling_escalation_256_active": False,
        "as_fft_mtf_analysis_path_retired": True,
        "next_gate": "Web review of corrected angular scale before sampling lock / Run72",
    }
    local_report = output / LOCAL_REPORT
    local_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    local_csv = output / REPO_TF_CSV
    if csv_rows:
        _write_csv(local_csv, csv_rows)
    report["local_report_sha256"] = hashlib.sha256(local_report.read_bytes()).hexdigest()

    if args.write_repo_evidence:
        REPO_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        repo_payload = _sanitize(report)
        text = json.dumps(repo_payload, ensure_ascii=False, indent=2)
        if ":\\" in text or ":/" in text or ".zmx" in text.casefold() or ".dat" in text.casefold():
            raise SystemExit("sanitized TASK-009 evidence still contains a local optical path")
        (REPO_EVIDENCE_DIR / REPO_EVIDENCE_NAME).write_text(text, encoding="utf-8")
        if csv_rows:
            _write_csv(REPO_EVIDENCE_DIR / REPO_TF_CSV, csv_rows)

    print(
        json.dumps(
            {
                "report": str(local_report.resolve()),
                "all_convergence_passed": all_convergence_passed,
                "all_repeatability_passed": all_repeatability_passed,
                "all_six_config_integration_passed": integration_passed,
                "crosscheck_review_pending_web": True,
                "production_sampling_locked": False,
                "run72_started": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not all_convergence_passed or not all_repeatability_passed or not integration_passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
