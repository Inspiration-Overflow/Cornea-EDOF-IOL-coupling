"""Run the consolidated TASK-009 FFT-MTF representative integration batch.

One local OpticStudio session performs:
1. real FFT MTF / EFFL capability validation;
2. 64/128/256 sampling convergence on three frozen EDOF representative configs;
3. 128-sampling repeatability on the same three EDOF configs;
4. production-setting MONO+EDOF integration for the three representative pair keys;
5. a limited MFE MTFA Grid=1 diagnostic cross-check.

The command never changes TASK-005/006/007/008 locks and never runs the full 72-config matrix.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.analysis import summarize_mtfa_curve, with_shape_axis
from whole_eye_mvp.b0_zos import object_thickness_for_defocus_d
from whole_eye_mvp.domain import NOMINAL_MAIN_FFT_MTF_555_V2
from whole_eye_mvp.grid_sag_residual import apply_grid_sag_residual
from whole_eye_mvp.metrics import mm_per_degree, mtfa, resample_fft_mtf_to_cpd
from whole_eye_mvp.residual_payload import (
    RadialResidualCandidate,
    build_hoa_residual_candidate,
    build_rad_residual_candidate,
    build_wfs_residual_candidate,
)
from whole_eye_mvp.store import sha256_file
from whole_eye_mvp.zos import (
    FftMtfRunner,
    FftMtfSettings,
    MfeEfflRunner,
    MfeFullHoaRunner,
    MfeMtfaRunner,
    MfeMtfaSettings,
    open_zos_session,
)

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
TASK008_EVIDENCE = REPOSITORY_ROOT / "docs/evidence/task008/TASK_008_LOCK_MANIFEST_EVIDENCE.json"
OUTPUT_REL = Path("diagnostics/task009/fft_mtf_representative")
LOCAL_REPORT = "TASK_009_FFT_MTF_REPRESENTATIVE.json"
REPO_EVIDENCE_DIR = REPOSITORY_ROOT / "docs/evidence/task009"
REPO_EVIDENCE_NAME = "TASK_009_FFT_MTF_REPRESENTATIVE_EVIDENCE.json"
REPO_TF_CSV = "TASK_009_REPRESENTATIVE_THROUGH_FOCUS.csv"

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


def _candidate(platform: str) -> RadialResidualCandidate:
    builders = {
        "WFS": build_wfs_residual_candidate,
        "RAD": build_rad_residual_candidate,
        "HOA": build_hoa_residual_candidate,
    }
    try:
        return builders[platform]()
    except KeyError as exc:
        raise ValueError(f"unknown platform: {platform}") from exc


def _require_cycles_per_mm(session) -> None:
    units = getattr(session.system.SystemData, "Units", None)
    value = getattr(units, "MTFUnits", None)
    if value is None:
        raise RuntimeError("installed API exposes no SystemData.Units.MTFUnits")
    text = str(value).casefold().replace("_", "")
    if "millimeter" in text or "millimetre" in text:
        return
    try:
        if int(value) == 0:
            return
    except (TypeError, ValueError):
        pass
    raise RuntimeError(f"TASK-009 requires cycles/mm MTF units; installed value is {value!r}")


def _set_epd(session, pupil_mm: float) -> None:
    aperture = session.system.SystemData.Aperture
    aperture.ApertureType = session.zosapi.SystemData.ZemaxApertureType.EntrancePupilDiameter
    aperture.ApertureValue = float(pupil_mm)


def _assert_555_nm(session) -> None:
    wavelength_nm = float(session.system.SystemData.Wavelengths.GetWavelength(1).Wavelength) * 1000.0
    if abs(wavelength_nm - NOMINAL_MAIN_FFT_MTF_555_V2.wavelength_nm) > 1.0e-6:
        raise RuntimeError(f"TASK-009 requires 555 nm, got {wavelength_nm:.12g} nm")


def _sample_index_for_mtfa(pupil_sampling: int) -> int:
    mapping = {32: 1, 64: 2, 128: 3, 256: 4, 512: 5, 1024: 6}
    try:
        return mapping[pupil_sampling]
    except KeyError as exc:
        raise ValueError(f"no MFE MTFA sampling index is frozen for {pupil_sampling}") from exc


def _relative_change(first: float, second: float) -> float:
    scale = max(abs(first), abs(second), 1.0e-15)
    return abs(first - second) / scale


def _prepare_output(path: Path, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise SystemExit(f"TASK-009 output exists; pass --overwrite: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _make_edof(session, mono: Path, platform: str, residual_dat: Path, output: Path) -> Path:
    apply_grid_sag_residual(session, mono, _candidate(platform), residual_dat, output)
    return output


def _acquire_curve(session, model_path: Path, pupil_mm: float, sampling: int) -> dict[str, object]:
    session.system.LoadFile(str(model_path.resolve()), False)
    _assert_555_nm(session)
    _require_cycles_per_mm(session)
    _set_epd(session, pupil_mm)

    object_surface = session.system.LDE.GetSurfaceAt(0)
    saved_object_thickness = float(object_surface.Thickness)
    object_surface.Thickness = saved_object_thickness
    effl_mm = MfeEfflRunner(session.system, session.zosapi).run().effective_focal_length_mm
    scale_mm_per_degree = mm_per_degree(effl_mm)
    max_frequency_cyc_per_mm = math.ceil(65.0 / scale_mm_per_degree)
    fft_runner = FftMtfRunner(session.system, session.zosapi)

    common_cpd: tuple[float, ...] | None = None
    mtfa_values: list[float] = []
    fixed_columns: dict[float, list[float]] = {
        frequency: [] for frequency in NOMINAL_MAIN_FFT_MTF_555_V2.mtf_sample_frequencies_cpd
    }
    native_series_meta: dict[str, object] | None = None
    grid = NOMINAL_MAIN_FFT_MTF_555_V2.defocus_grid()
    try:
        for defocus_d in grid:
            object_surface.Thickness = object_thickness_for_defocus_d(
                defocus_d,
                infinity_thickness_mm=saved_object_thickness,
            )
            fft = fft_runner.run(
                FftMtfSettings(
                    sampling=sampling,
                    maximum_frequency_cyc_per_mm=float(max_frequency_cyc_per_mm),
                    use_polarization=NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_use_polarization,
                )
            )
            cpd, avg = resample_fft_mtf_to_cpd(
                fft.frequency_cycles_per_mm,
                fft.sagittal_mtf,
                fft.tangential_mtf,
                effective_focal_length_mm=effl_mm,
                max_cpd=NOMINAL_MAIN_FFT_MTF_555_V2.mtfa_max_cpd,
                step_cpd=NOMINAL_MAIN_FFT_MTF_555_V2.mtf_frequency_step_cpd,
            )
            if common_cpd is None:
                common_cpd = tuple(float(value) for value in cpd)
                native_series_meta = {
                    "description": fft.description,
                    "x_label": fft.x_label,
                    "series_labels": fft.series_labels,
                    "native_frequency_min_cycles_per_mm": fft.frequency_cycles_per_mm[0],
                    "native_frequency_max_cycles_per_mm": fft.frequency_cycles_per_mm[-1],
                    "native_frequency_count": len(fft.frequency_cycles_per_mm),
                }
            elif tuple(float(value) for value in cpd) != common_cpd:
                raise RuntimeError("TASK-009 common cpd grid changed between defocus planes")
            mtfa_values.append(mtfa(cpd, avg, max_cpd=NOMINAL_MAIN_FFT_MTF_555_V2.mtfa_max_cpd))
            for frequency in fixed_columns:
                index = int(round(frequency / NOMINAL_MAIN_FFT_MTF_555_V2.mtf_frequency_step_cpd))
                fixed_columns[frequency].append(float(avg[index]))
    finally:
        object_surface.Thickness = saved_object_thickness

    rows = with_shape_axis(
        grid,
        tuple(mtfa_values),
        tuple(tuple(fixed_columns[frequency]) for frequency in (10.0, 20.0, 30.0, 40.0, 50.0, 60.0)),
    )
    summary = summarize_mtfa_curve(rows)
    object_surface.Thickness = saved_object_thickness
    hoa = MfeFullHoaRunner(session.system, session.zosapi).run()
    return {
        "sampling": sampling,
        "pupil_mm": pupil_mm,
        "effective_focal_length_mm": effl_mm,
        "mm_per_degree": scale_mm_per_degree,
        "requested_max_frequency_cycles_per_mm": max_frequency_cyc_per_mm,
        "native_series": native_series_meta,
        "through_focus": [asdict(row) for row in rows],
        "summary": summary,
        "aberrations": {
            "c40_um": hoa.c40_um,
            "c60_um": hoa.c60_um,
            "hoa_rms_um": hoa.hoa_rms_um,
        },
    }


def _check_convergence(low: dict[str, object], nominal: dict[str, object], high: dict[str, object]) -> dict[str, object]:
    del low  # retained in evidence; convergence gate is nominal 128 versus high 256
    n = nominal["summary"]
    h = high["summary"]
    if not isinstance(n, dict) or not isinstance(h, dict):
        raise TypeError("TASK-009 convergence summary is invalid")
    peak_mtfa_rel = _relative_change(float(n["distance_peak_mtfa"]), float(h["distance_peak_mtfa"]))
    tf_mean_rel = _relative_change(float(n["tf_mtfa_mean"]), float(h["tf_mtfa_mean"]))
    peak_shift = abs(float(n["distance_peak_retina_d"]) - float(h["distance_peak_retina_d"]))
    dof50_change = abs(float(n["dof50_width_d"]) - float(h["dof50_width_d"]))
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


def _check_repeatability(first: dict[str, object], second: dict[str, object]) -> dict[str, object]:
    a = first["summary"]
    b = second["summary"]
    aa = first["aberrations"]
    bb = second["aberrations"]
    if not all(isinstance(item, dict) for item in (a, b, aa, bb)):
        raise TypeError("TASK-009 repeatability evidence is invalid")
    peak_rel = _relative_change(float(a["distance_peak_mtfa"]), float(b["distance_peak_mtfa"]))
    tf_rel = _relative_change(float(a["tf_mtfa_mean"]), float(b["tf_mtfa_mean"]))
    c40_delta = abs(float(aa["c40_um"]) - float(bb["c40_um"]))
    c60_delta = abs(float(aa["c60_um"]) - float(bb["c60_um"]))
    same_peak_sample = float(a["distance_peak_retina_d"]) == float(b["distance_peak_retina_d"])
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


def _mtfa_crosscheck(session, model_path: Path, pupil_mm: float, production: dict[str, object]) -> dict[str, object]:
    session.system.LoadFile(str(model_path.resolve()), False)
    _assert_555_nm(session)
    _require_cycles_per_mm(session)
    _set_epd(session, pupil_mm)
    object_surface = session.system.LDE.GetSurfaceAt(0)
    saved = float(object_surface.Thickness)
    object_surface.Thickness = saved
    effl = float(production["effective_focal_length_mm"])
    scale = mm_per_degree(effl)
    frequencies_mm = tuple(frequency / scale for frequency in CROSSCHECK_CPD)
    result = MfeMtfaRunner(session.system, session.zosapi).run(
        MfeMtfaSettings(
            frequencies_cyc_per_mm=frequencies_mm,
            sampling=_sample_index_for_mtfa(128),
            grid=1,
            data_type=0,
        )
    )
    rows = production["through_focus"]
    if not isinstance(rows, list):
        raise TypeError("production through-focus evidence is invalid")
    zero = next(row for row in rows if abs(float(row["defocus_retina_d"])) <= 1.0e-12)
    fft_values = tuple(float(zero[f"mtf{int(frequency)}"]) for frequency in CROSSCHECK_CPD)
    deltas = tuple(abs(left - right) for left, right in zip(fft_values, result.mtf_average, strict=True))
    return {
        "cpd": CROSSCHECK_CPD,
        "cycles_per_mm": frequencies_mm,
        "fft_mtf_analysis_average": fft_values,
        "mfe_mtfa_grid1": result.mtf_average,
        "absolute_differences": deltas,
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
    output = project_dir / OUTPUT_REL
    _prepare_output(output, args.overwrite)

    settings = NOMINAL_MAIN_FFT_MTF_555_V2
    settings.validate()
    convergence: dict[str, object] = {}
    integration: dict[str, object] = {}
    crosschecks: dict[str, object] = {}
    csv_rows: list[dict[str, object]] = []
    all_convergence_passed = True
    all_repeatability_passed = True

    with open_zos_session(args.install_dir) as session:
        for base, cornea, platform, pupil in REPRESENTATIVES:
            key = f"{base}_{cornea}_{platform}_EPD{int(pupil)}"
            carrier_id = f"CAR_{base}_{cornea}_{platform}"
            mono_path = project_dir / "models" / "carriers" / f"{carrier_id}.zmx"
            if not mono_path.is_file():
                raise SystemExit(f"formal representative carrier missing: {carrier_id}")
            carrier_hashes = task008.get("carrier_asset_sha256")
            if not isinstance(carrier_hashes, dict) or sha256_file(mono_path) != carrier_hashes.get(carrier_id):
                raise SystemExit(f"formal representative carrier hash mismatch: {carrier_id}")
            residual_dat = project_dir / "models" / "assets" / "residuals" / f"RESIDUAL_{platform}_546_v1.DAT"
            residual_hashes = task008.get("residual_asset_sha256")
            if not isinstance(residual_hashes, dict) or not residual_dat.is_file() or sha256_file(residual_dat) != residual_hashes.get(platform):
                raise SystemExit(f"formal representative residual hash mismatch: {platform}")
            edof_path = output / "models" / f"{carrier_id}_EDOF.zmx"
            _make_edof(session, mono_path, platform, residual_dat, edof_path)

            samples = {
                str(sampling): _acquire_curve(session, edof_path, pupil, sampling)
                for sampling in settings.fft_mtf_convergence_samplings
            }
            repeat128 = _acquire_curve(session, edof_path, pupil, settings.fft_mtf_sampling)
            convergence_gate = _check_convergence(samples["64"], samples["128"], samples["256"])
            repeat_gate = _check_repeatability(samples["128"], repeat128)
            all_convergence_passed = all_convergence_passed and bool(convergence_gate["passed"])
            all_repeatability_passed = all_repeatability_passed and bool(repeat_gate["passed"])
            convergence[key] = {
                "pair": {"base_id": base, "cornea_id": cornea, "platform_id": platform, "pupil_mm": pupil},
                "edof_model_sha256": sha256_file(edof_path),
                "sampling_results": samples,
                "repeat_128": repeat128,
                "convergence_gate": convergence_gate,
                "repeatability_gate": repeat_gate,
            }

            mono128 = _acquire_curve(session, mono_path, pupil, settings.fft_mtf_sampling)
            edof128 = samples["128"]
            mono_summary = mono128["summary"]
            edof_summary = edof128["summary"]
            if not isinstance(mono_summary, dict) or not isinstance(edof_summary, dict):
                raise TypeError("representative integration summary is invalid")
            delta_f = float(edof_summary["distance_peak_retina_d"]) - float(mono_summary["distance_peak_retina_d"])
            integration[key] = {
                "pair": {"base_id": base, "cornea_id": cornea, "platform_id": platform, "pupil_mm": pupil},
                "mono": mono128,
                "edof": edof128,
                "delta_f_residual_d": delta_f,
                "delta_distance_peak_mtfa": float(edof_summary["distance_peak_mtfa"]) - float(mono_summary["distance_peak_mtfa"]),
                "delta_mtfa_at_zero_d": float(edof_summary["mtfa_at_zero_d"]) - float(mono_summary["mtfa_at_zero_d"]),
                "delta_dof50_width_d": float(edof_summary["dof50_width_d"]) - float(mono_summary["dof50_width_d"]),
                "delta_tf_mtfa_mean": float(edof_summary["tf_mtfa_mean"]) - float(mono_summary["tf_mtfa_mean"]),
            }
            crosschecks[key] = _mtfa_crosscheck(session, edof_path, pupil, edof128)

            for state, result in (("MONO", mono128), ("EDOF", edof128)):
                for row in result["through_focus"]:
                    csv_rows.append(
                        {
                            "pair_key": key,
                            "state": state,
                            "sampling": 128,
                            **row,
                        }
                    )

    report: dict[str, object] = {
        "schema_version": 1,
        "phase": "TASK-009-FFT-MTF-REPRESENTATIVE",
        "evidence_only": True,
        "formal_artifact": False,
        "run72_started": False,
        "code_commit": code_commit,
        "task008_evidence_sha256": sha256_file(TASK008_EVIDENCE),
        "task008_manifest_hash": task008.get("manifest_hash"),
        "task008_lock_set_hash": task008.get("lock_set_hash"),
        "settings": asdict(settings),
        "representatives": REPRESENTATIVES,
        "convergence": convergence,
        "integration": integration,
        "crosschecks": crosschecks,
        "all_convergence_passed": all_convergence_passed,
        "all_repeatability_passed": all_repeatability_passed,
        "crosscheck_review_pending_web": True,
        "production_sampling_locked": all_convergence_passed and all_repeatability_passed,
        "next_gate": "Web review of FFT-family diagnostic cross-check and TASK-009 evidence before Run72",
    }
    local_report = output / LOCAL_REPORT
    local_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    local_csv = output / REPO_TF_CSV
    _write_csv(local_csv, csv_rows)
    report["local_report_sha256"] = hashlib.sha256(local_report.read_bytes()).hexdigest()

    if args.write_repo_evidence:
        REPO_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        repo_payload = _sanitize(report)
        text = json.dumps(repo_payload, ensure_ascii=False, indent=2)
        if ":\\" in text or ":/" in text or ".zmx" in text.casefold():
            raise SystemExit("sanitized TASK-009 evidence still contains a local path")
        (REPO_EVIDENCE_DIR / REPO_EVIDENCE_NAME).write_text(text, encoding="utf-8")
        _write_csv(REPO_EVIDENCE_DIR / REPO_TF_CSV, csv_rows)

    print(
        json.dumps(
            {
                "report": str(local_report.resolve()),
                "all_convergence_passed": all_convergence_passed,
                "all_repeatability_passed": all_repeatability_passed,
                "crosscheck_review_pending_web": True,
                "run72_started": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not all_convergence_passed or not all_repeatability_passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
