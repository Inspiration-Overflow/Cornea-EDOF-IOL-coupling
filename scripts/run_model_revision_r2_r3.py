"""Run the post-human-audit R2/R3 OpticStudio gate in one local batch.

The batch intentionally stops before any EDoF mechanism fitting. It builds two
curved-retina/physical-STOP base eyes, solves one Q=0 analytical A0 carrier per
base, converts each carrier into the three platform-specific degenerate Binary 4
MONO structures, and verifies analytical-vs-Binary4 equivalence at 3 and 5 mm
physical STOP diameters.

Native FFT MTF is intentionally acquired here, in the diagnostic script, rather
than reintroduced into the production ``src`` analysis path.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.carriers import sha256_path
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    BaseId,
    PlatformId,
    ScientificBaseline,
)
from whole_eye_mvp.model_revision_zos import apply_revision_to_full_eye
from whole_eye_mvp.revision_base_zos import (
    build_revision_base_asset,
    revision_base_prescriptions,
)
from whole_eye_mvp.revision_binary4_zos import (
    DegenerateEquivalenceThresholds,
    build_degenerate_binary4_mono,
    compare_degenerate_binary4_to_analytical,
)
from whole_eye_mvp.revision_carrier_zos import build_revision_q0_analytical_carrier
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
DEFAULT_A0_RELATIVE_PATH = Path("diagnostics/task005d/corneas/CORNEA_A0.zmx")
OUTPUT_RELATIVE_DIR = Path("diagnostics/model_revision/r2_r3")
REPORT_NAME = "MODEL_REVISION_R2_R3_EVIDENCE.json"
FFT_MTF_MAX_FREQUENCY_CYC_PER_MM = 100.0
FFT_MTF_SAMPLE_SIZE = 128
FFT_MTF_EQUIVALENCE_TOLERANCE = 1.0e-6


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=os.environ.get(INSTALL_ENV),
        help=f"OpticStudio installation directory; defaults to {INSTALL_ENV}",
    )
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
    parser.add_argument("--a0-path", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _clean_git_head() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise SystemExit("R2/R3 local gate requires a clean tracked Git checkout")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _guard_outputs(output_dir: Path, *, overwrite: bool) -> None:
    report = output_dir / REPORT_NAME
    if report.exists() and not overwrite:
        raise SystemExit(
            f"R2/R3 evidence already exists; pass --overwrite: {report}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)


def _native_fft_mtf_snapshot(
    session,
    base_id: str,
    path: Path,
    *,
    pupil_diameter_mm: float,
) -> tuple[tuple[float, ...], ...]:
    """Acquire native FFT MTF only for the R2/R3 audit-equivalence diagnostic."""

    session.system.LoadFile(str(path.resolve()), False)
    apply_revision_to_full_eye(
        session,
        base_id,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    try:
        analysis = session.system.Analyses.New_FftMtf()
    except AttributeError as exc:
        raise RuntimeError("installed API exposes no New_FftMtf analysis") from exc
    try:
        raw_settings = analysis.GetSettings()
        settings = getattr(raw_settings, "__implementation__", raw_settings)
        settings.MaximumFrequency = FFT_MTF_MAX_FREQUENCY_CYC_PER_MM
        sample_sizes = session.zosapi.Analysis.SampleSizes
        settings.SampleSize = getattr(
            sample_sizes,
            f"S_{FFT_MTF_SAMPLE_SIZE}x{FFT_MTF_SAMPLE_SIZE}",
        )
        analysis.ApplyAndWaitForCompletion()
        results = analysis.GetResults()
        series_count = int(results.NumberOfDataSeries)
        if series_count < 1:
            raise RuntimeError("native FFT MTF returned no data series")

        flattened: list[tuple[float, ...]] = []
        for series_number in range(series_count):
            data = results.GetDataSeries(series_number)
            x_data = data.XData
            y_data = data.YData
            length = int(x_data.Length)
            if length < 2 or int(data.NumSeries) < 2:
                raise RuntimeError(
                    f"native FFT MTF series {series_number} has an invalid shape"
                )
            frequencies = tuple(
                float(x_data.GetValueAt(index)) for index in range(length)
            )
            tangential = tuple(
                float(y_data.GetValueAt(index, 0)) for index in range(length)
            )
            sagittal = tuple(
                float(y_data.GetValueAt(index, 1)) for index in range(length)
            )
            numeric = (*frequencies, *tangential, *sagittal)
            if not all(math.isfinite(value) for value in numeric):
                raise RuntimeError(
                    f"native FFT MTF series {series_number} contains non-finite values"
                )
            flattened.extend((frequencies, tangential, sagittal))
        return tuple(flattened)
    finally:
        close = getattr(analysis, "Close", None)
        if callable(close):
            close()


def _native_fft_mtf_max_difference(
    session,
    base_id: str,
    analytical_path: Path,
    binary4_path: Path,
    *,
    pupil_diameter_mm: float,
) -> float:
    left = _native_fft_mtf_snapshot(
        session,
        base_id,
        analytical_path,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    right = _native_fft_mtf_snapshot(
        session,
        base_id,
        binary4_path,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    if len(left) != len(right):
        return math.inf
    difference = 0.0
    for index, (left_values, right_values) in enumerate(
        zip(left, right, strict=True)
    ):
        if len(left_values) != len(right_values):
            return math.inf
        # Every group of three rows is frequency, tangential, sagittal.
        if index % 3 == 0:
            if any(
                abs(a - b) > 1.0e-12
                for a, b in zip(left_values, right_values, strict=True)
            ):
                return math.inf
            continue
        difference = max(
            difference,
            max(
                (
                    abs(a - b)
                    for a, b in zip(left_values, right_values, strict=True)
                ),
                default=0.0,
            ),
        )
    return difference


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    code_commit = _clean_git_head()
    project_dir = args.project_dir.resolve()
    baseline = ScientificBaseline(args.baseline_id)
    a0_path = (
        args.a0_path.resolve()
        if args.a0_path is not None
        else (project_dir / DEFAULT_A0_RELATIVE_PATH).resolve()
    )
    if not a0_path.is_file():
        raise SystemExit(f"Required A0 cornea input is missing: {a0_path}")

    output_dir = project_dir / OUTPUT_RELATIVE_DIR
    _guard_outputs(output_dir, overwrite=args.overwrite)
    report_path = output_dir / REPORT_NAME

    thresholds = DegenerateEquivalenceThresholds()
    base_results: dict[str, object] = {}
    carrier_results: dict[str, object] = {}
    binary_results: dict[str, object] = {}
    comparisons: list[dict[str, object]] = []

    with open_zos_session(args.install_dir) as session:
        for prescription in revision_base_prescriptions(baseline):
            base_id = str(prescription.source.base_spec.base_id)
            destination = output_dir / f"R2_BASE_{base_id}.zmx"
            result = build_revision_base_asset(session, prescription, destination)
            base_results[base_id] = {
                "measurement": asdict(result),
                "sha256": sha256_path(destination),
            }

        analytical_paths: dict[BaseId, Path] = {}
        for base_id in BaseId:
            destination = output_dir / f"R2_ANALYTICAL_Q0_{base_id}.zmx"
            result = build_revision_q0_analytical_carrier(
                session,
                baseline,
                base_id,
                a0_path,
                destination,
            )
            analytical_paths[base_id] = destination
            carrier_results[str(base_id)] = {
                "measurement": asdict(result),
                "sha256": sha256_path(destination),
            }

        for base_id, analytical_path in analytical_paths.items():
            for platform in PlatformId:
                destination = output_dir / f"R3_BINARY4_MONO_{base_id}_{platform}.zmx"
                build = build_degenerate_binary4_mono(
                    session,
                    base_id,
                    platform,
                    analytical_path,
                    destination,
                    pupil_diameter_mm=3.0,
                )
                key = f"{base_id}__{platform}"
                binary_results[key] = {
                    "measurement": asdict(build),
                    "sha256": sha256_path(destination),
                }
                for pupil in (3.0, 5.0):
                    core = compare_degenerate_binary4_to_analytical(
                        session,
                        base_id,
                        platform,
                        analytical_path,
                        destination,
                        pupil_diameter_mm=pupil,
                        thresholds=thresholds,
                    )
                    fft_difference = _native_fft_mtf_max_difference(
                        session,
                        base_id,
                        analytical_path,
                        destination,
                        pupil_diameter_mm=pupil,
                    )
                    fft_passed = (
                        math.isfinite(fft_difference)
                        and fft_difference <= FFT_MTF_EQUIVALENCE_TOLERANCE
                    )
                    findings = list(core.findings)
                    if not fft_passed:
                        findings.append(
                            "max_abs_fft_mtf_error: "
                            f"{fft_difference:.12g} exceeds "
                            f"{FFT_MTF_EQUIVALENCE_TOLERANCE:.12g}"
                        )
                    comparisons.append(
                        {
                            "pupil_diameter_mm": pupil,
                            **asdict(core),
                            "max_abs_fft_mtf_error": fft_difference,
                            "fft_mtf_tolerance": FFT_MTF_EQUIVALENCE_TOLERANCE,
                            "passed": core.passed and fft_passed,
                            "findings": findings,
                        }
                    )

    passed = all(bool(item["passed"]) for item in comparisons)
    payload = {
        "schema_version": 1,
        "formal_artifact": False,
        "phase": "MODEL-REVISION-R2-R3",
        "baseline_id": baseline.baseline_id,
        "code_commit": code_commit,
        "inputs": {
            "a0_path": str(a0_path),
            "a0_sha256": sha256_path(a0_path),
        },
        "equivalence_thresholds": {
            **asdict(thresholds),
            "max_abs_fft_mtf_error": FFT_MTF_EQUIVALENCE_TOLERANCE,
        },
        "revised_bases": base_results,
        "revised_q0_analytical_carriers": carrier_results,
        "binary4_degenerate_mono": binary_results,
        "equivalence": comparisons,
        "passed": passed,
        "next_gate": (
            "Web review; if accepted, proceed to R4 mechanism-fit pilot"
            if passed
            else "STOP: return full evidence to Web review; do not start R4"
        ),
    }
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"report_path": str(report_path.resolve()), **payload},
            ensure_ascii=False,
            indent=2,
        )
    )
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
