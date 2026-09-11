"""Build and acquire the prespecified C0 distance-component-anchored branch."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import asdict
from pathlib import Path

from run_model_revision_r8_96 import _opticstudio_version, validate_execution_authorization
from run_supplemental_experiments_opticstudio import (
    SUPPLEMENTAL_ANALYSIS_SETTINGS,
    SUPPLEMENTAL_PEAK_WINDOW_D,
)

from whole_eye_mvp.analysis_zos_r8_direct import (
    DirectModelSpec,
    artifact_hashes,
    run_r8_direct_acquisition,
    write_r8_aggregate_outputs,
)
from whole_eye_mvp.carriers import sha256_path
from whole_eye_mvp.cornea_assets import MAIN_CORNEA_SCAFFOLD, distance_corrected_front_radius_mm
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    ScientificBaseline,
)
from whole_eye_mvp.model_revision import CORNEA_CLEAR_SEMI_DIAMETER_MM
from whole_eye_mvp.revision_carrier_zos import build_revision_q0_analytical_carrier
from whole_eye_mvp.revision_r6 import R6_MAX_PQ_RECHECK_CYCLES
from whole_eye_mvp.revision_r6_zos import (
    build_and_validate_r6_carrier,
    solve_revision_platform_carrier,
)
from whole_eye_mvp.standard_eye import RELATIVE_PATH as STANDARD_EYE_RELATIVE_PATH
from whole_eye_mvp.supplemental_artifacts import annotate_config_csv_with_original_window_mean
from whole_eye_mvp.zos import Binary4Zone, SequentialEditor, open_zos_session
from whole_eye_mvp.zos.primitives import binary4_zone_columns

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DIR = REPOSITORY_ROOT / "project_mvp_2026_v2_zmx"
OUTPUT_RELATIVE = Path("diagnostics/supplemental_experiments/experiment2_distance_anchor")
EVIDENCE_NAME = "SUPPLEMENTAL_EXPERIMENT_2_DISTANCE_ANCHOR_EVIDENCE.json"
CONFIG_NAME = "SUPPLEMENTAL_EXPERIMENT_2_CONFIG_RESULTS.csv"
THROUGH_FOCUS_NAME = "SUPPLEMENTAL_EXPERIMENT_2_THROUGH_FOCUS.csv"
PAIRED_NAME = "SUPPLEMENTAL_EXPERIMENT_2_PAIRED_DELTAS.csv"
C0_SOURCE_RELATIVE = Path("diagnostics/task005d/corneas/CORNEA_C0_N8.zmx")
BASE_IDS = ("LB_AL2395", "ATC_M3_AL24477")
PLATFORM_IDS = ("WFS", "RAD", "HOA")
PUPIL_MM = (3.0, 5.0)
OPTIC_STATES = ("MONO", "EDOF")
CENTRAL_NEAR_ADD_D = 1.75


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _parameter_double(session, surface_number: int, parameter_number: int) -> float:
    column = getattr(session.zosapi.Editors.LDE.SurfaceColumn, f"Par{parameter_number}")
    return float(
        session.system.LDE.GetSurfaceAt(surface_number)
        .GetSurfaceCell(column)
        .DoubleValue
    )


def _parameter_integer(session, surface_number: int, parameter_number: int) -> int:
    column = getattr(session.zosapi.Editors.LDE.SurfaceColumn, f"Par{parameter_number}")
    return int(
        session.system.LDE.GetSurfaceAt(surface_number)
        .GetSurfaceCell(column)
        .IntegerValue
    )


def _read_binary4_zones(session, surface_number: int = 1) -> tuple[Binary4Zone, ...]:
    zone_count = _parameter_integer(session, surface_number, 1)
    aspheric_count = _parameter_integer(session, surface_number, 2)
    phase_count = _parameter_integer(session, surface_number, 3)
    if zone_count <= 0:
        raise RuntimeError("C0 cornea Binary4 surface has no zones")
    zones: list[Binary4Zone] = []
    for zone_number in range(1, zone_count + 1):
        columns = binary4_zone_columns(zone_number, aspheric_count, phase_count)
        zones.append(
            Binary4Zone(
                radial_aperture=_parameter_double(session, surface_number, columns.radial_aperture),
                radius=_parameter_double(session, surface_number, columns.radius),
                conic=_parameter_double(session, surface_number, columns.conic),
                diffraction_order=_parameter_double(
                    session, surface_number, columns.diffraction_order
                ),
                aspheric_terms=tuple(
                    _parameter_double(session, surface_number, number)
                    for number in columns.aspheric_terms
                ),
                phase_terms=tuple(
                    _parameter_double(session, surface_number, number)
                    for number in columns.phase_terms
                ),
            )
        )
    return tuple(zones)


def _build_distance_only_cornea(session, source: Path, destination: Path) -> tuple[Binary4Zone, ...]:
    session.system.LoadFile(str(source.resolve()), False)
    original_zones = _read_binary4_zones(session)
    distance_radius = distance_corrected_front_radius_mm(-3.0)
    zones = tuple(
        Binary4Zone(
            radial_aperture=zone.radial_aperture,
            radius=distance_radius,
            conic=MAIN_CORNEA_SCAFFOLD.front_conic,
            diffraction_order=zone.diffraction_order,
            aspheric_terms=zone.aspheric_terms,
            phase_terms=zone.phase_terms,
        )
        for zone in original_zones
    )
    editor = SequentialEditor(session.system, session.zosapi)
    editor.configure_binary4(1, zones)
    editor.set_radius_conic(1, radius_mm=distance_radius, conic=MAIN_CORNEA_SCAFFOLD.front_conic)
    editor.surface(1).SemiDiameter = CORNEA_CLEAR_SEMI_DIAMETER_MM
    destination.parent.mkdir(parents=True, exist_ok=True)
    editor.save_as(destination)
    return original_zones


def _restore_c0_cornea(
    session,
    model_path: Path,
    destination: Path,
    original_zones: tuple[Binary4Zone, ...],
) -> None:
    session.system.LoadFile(str(model_path.resolve()), False)
    editor = SequentialEditor(session.system, session.zosapi)
    editor.configure_binary4(1, original_zones)
    editor.set_radius_conic(
        1,
        radius_mm=original_zones[0].radius,
        conic=original_zones[0].conic,
    )
    editor.surface(1).SemiDiameter = CORNEA_CLEAR_SEMI_DIAMETER_MM
    editor.save_as(destination)


def _make_specs(model_paths: dict[tuple[str, str, str], Path]) -> tuple[DirectModelSpec, ...]:
    specs: list[DirectModelSpec] = []
    for base_id in BASE_IDS:
        for platform_id in PLATFORM_IDS:
            carrier_id = f"R6_{base_id}_C0_{platform_id}"
            pair_carrier_id = f"S2_{carrier_id}"
            for pupil_mm in PUPIL_MM:
                pupil_label = int(pupil_mm)
                pair_key = f"{pair_carrier_id}_EPD{pupil_mm:g}"
                for optic_state in OPTIC_STATES:
                    source = model_paths[(base_id, platform_id, optic_state)]
                    key = f"distance_component_anchored/{carrier_id}/ACTUAL_BINARY4_{optic_state}.zmx"
                    specs.append(
                        DirectModelSpec(
                            config_id=f"S2_{carrier_id}_{optic_state}_EPD{pupil_label}",
                            pair_key=pair_key,
                            carrier_id=pair_carrier_id,
                            base_id=base_id,
                            cornea_id="C0",
                            platform_id=platform_id,
                            optic_state=optic_state,
                            pupil_mm=pupil_mm,
                            model_artifact_key=key,
                            source_path=source,
                            source_sha256=_sha256(source),
                        )
                    )
    if len(specs) != 24 or len({item.model_artifact_key for item in specs}) != 12:
        raise RuntimeError("experiment 2 requires exactly 24 configs and 12 models")
    return tuple(specs)


def _annotate_distance_config_csv(path: Path) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 24:
        raise RuntimeError(f"experiment 2 config CSV must contain 24 rows, got {len(rows)}")
    fields = list(rows[0])
    for field in (
        "calibration_strategy",
        "carrier_key",
        "near_add_d",
        "near_add_zeroed_for_solve",
        "carrier_frozen",
        "near_add_restored",
        "post_restore_iol_power_solves",
        "post_restore_refocus_count",
        "post_restore_carrier_optimizations",
    ):
        if field not in fields:
            fields.append(field)
    for row in rows:
        row.update(
            {
                "calibration_strategy": "distance_component_anchored",
                "carrier_key": row["carrier_id"],
                "near_add_d": str(CENTRAL_NEAR_ADD_D),
                "near_add_zeroed_for_solve": "True",
                "carrier_frozen": "True",
                "near_add_restored": "True",
                "post_restore_iol_power_solves": "0",
                "post_restore_refocus_count": "0",
                "post_restore_carrier_optimizations": "0",
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def execute(*, install_dir: Path, project_dir: Path) -> dict[str, object]:
    source = (project_dir / C0_SOURCE_RELATIVE).resolve()
    standard_eye = (project_dir / STANDARD_EYE_RELATIVE_PATH).resolve()
    if not source.is_file() or not standard_eye.is_file():
        raise SystemExit("experiment 2 requires the frozen C0 cornea and standard-eye assets")

    output_root = (project_dir / OUTPUT_RELATIVE).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"experiment 2 output directory is not empty: {output_root}")
    calibration_root = output_root / "calibration"
    acquisition_root = output_root / "acquisition"
    distance_cornea = calibration_root / "cornea" / "CORNEA_C0_DISTANCE_ONLY.zmx"
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    calibration_records: list[dict[str, object]] = []
    model_paths: dict[tuple[str, str, str], Path] = {}
    run_id = f"supplemental-2-{uuid.uuid4().hex}"

    with open_zos_session(install_dir) as session:
        original_zones = _build_distance_only_cornea(session, source, distance_cornea)
        for base_id in BASE_IDS:
            q0_path = calibration_root / "q0" / f"Q0_{base_id}_C0_DISTANCE_ONLY.zmx"
            q0 = build_revision_q0_analytical_carrier(
                session,
                baseline,
                base_id,
                distance_cornea,
                q0_path,
            )
            for platform_id in PLATFORM_IDS:
                carrier = solve_revision_platform_carrier(
                    session,
                    baseline,
                    standard_eye,
                    base_id=base_id,
                    cornea_id="C0",
                    platform_id=platform_id,
                    q0=q0,
                    q0_path=q0_path,
                    output_dir=calibration_root / "carriers",
                    max_rechecks=R6_MAX_PQ_RECHECK_CYCLES,
                )
                validation = build_and_validate_r6_carrier(
                    session,
                    standard_eye,
                    carrier,
                    calibration_root / "models",
                    full_standard_audit=False,
                )
                restored_paths: dict[str, str] = {}
                for optic_state, model in (
                    ("MONO", Path(validation.actual_mono.path)),
                    ("EDOF", Path(validation.actual_edof.path)),
                ):
                    _restore_c0_cornea(session, model, model, original_zones)
                    model_paths[(base_id, platform_id, optic_state)] = model
                    restored_paths[optic_state] = str(model.resolve())
                calibration_records.append(
                    {
                        "base_id": base_id,
                        "cornea_id": "C0",
                        "platform_id": platform_id,
                        "carrier_id": carrier.carrier_id,
                        "distance_component_anchor": True,
                        "near_add_d": CENTRAL_NEAR_ADD_D,
                        "near_add_zeroed_for_base_power_solve": True,
                        "near_add_zeroed_for_mechanism_sa_calibration": True,
                        "carrier_frozen_before_near_add_restore": True,
                        "near_add_restored": True,
                        "post_restore_iol_power_solves": 0,
                        "post_restore_refocus_count": 0,
                        "post_restore_carrier_optimizations": 0,
                        "q0": asdict(q0),
                        "carrier": asdict(carrier),
                        "restored_models": restored_paths,
                    }
                )

        specs = _make_specs(model_paths)
        direct_run, diagnostics = run_r8_direct_acquisition(
            session,
            project_dir=project_dir,
            specs=specs,
            output_root=acquisition_root,
            run_id=run_id,
            analysis_settings=SUPPLEMENTAL_ANALYSIS_SETTINGS,
            peak_search_window_d=SUPPLEMENTAL_PEAK_WINDOW_D,
            expected_pair_count=12,
            expected_model_count=12,
        )
        opticstudio_version = _opticstudio_version(session)

    aggregate_paths = write_r8_aggregate_outputs(
        direct_run,
        output_root=output_root,
        config_csv_name=CONFIG_NAME,
        through_focus_csv_name=THROUGH_FOCUS_NAME,
        paired_csv_name=PAIRED_NAME,
    )
    _annotate_distance_config_csv(aggregate_paths["config_csv"])
    annotate_config_csv_with_original_window_mean(
        aggregate_paths["config_csv"], aggregate_paths["through_focus_csv"]
    )
    evidence = {
        "schema_version": 1,
        "formal_artifact": True,
        "experiment": "experiment_2_c0_distance_component_anchored",
        "task_id": "supplemental-experiments-20260824",
        "run_id": run_id,
        "code_commit": _git_head(),
        "opticstudio_version": opticstudio_version,
        "cornea_source_path": str(source),
        "cornea_source_sha256": sha256_path(source),
        "distance_only_cornea_sha256": _sha256(distance_cornea),
        "analysis_settings_id": SUPPLEMENTAL_ANALYSIS_SETTINGS.settings_id,
        "defocus_grid_retina_d": list(SUPPLEMENTAL_ANALYSIS_SETTINGS.defocus_grid()),
        "original_comparison_window_retina_d": [
            value
            for value in SUPPLEMENTAL_ANALYSIS_SETTINGS.defocus_grid()
            if -3.0 <= value <= 0.5
        ],
        "peak_search_window_d": SUPPLEMENTAL_PEAK_WINDOW_D,
        "config_count": len(direct_run.results),
        "matched_pair_count": len(direct_run.paired_deltas),
        "through_focus_rows": len(direct_run.through_focus_rows),
        "calibration_records": calibration_records,
        "config_results_csv_sha256": _sha256(aggregate_paths["config_csv"]),
        "through_focus_csv_sha256": _sha256(aggregate_paths["through_focus_csv"]),
        "paired_deltas_csv_sha256": _sha256(aggregate_paths["paired_csv"]),
        "runtime_artifact_sha256": artifact_hashes(output_root),
        "config_diagnostics": diagnostics,
        "local_acquisition_passed": True,
        "manual_web_review_required": True,
    }
    evidence_path = output_root / EVIDENCE_NAME
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "evidence_path": str(evidence_path),
        "run_id": run_id,
        "config_count": evidence["config_count"],
        "matched_pair_count": evidence["matched_pair_count"],
        "through_focus_rows": evidence["through_focus_rows"],
        "local_acquisition_passed": evidence["local_acquisition_passed"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-dir", type=Path, default=os.environ.get(INSTALL_ENV))
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--authorization-id", required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    validate_execution_authorization(args.authorization_id)
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")
    payload = execute(
        install_dir=Path(args.install_dir).resolve(),
        project_dir=args.project_dir.resolve(),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
