"""Generate TASK-005C diagnostic .zos files for manual OpticStudio GUI review.

This script intentionally never creates a Zernike analysis.  The three output files
are diagnostic-only and must never be registered as formal project assets or locks.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline
from whole_eye_mvp.standard_eye import (
    IMAGE_REF,
    build_standard_eye_asset,
    corneal_paraxial_focus_from_post_mm,
    standard_eye_construction,
)
from whole_eye_mvp.zos import SequentialEditor, open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "diagnostics" / "task005c_manual"

FIXED_NAME = "TASK005C_A_FIXED_REFERENCE.zos"
PARAXIAL_NAME = "TASK005C_B_PARAXIAL_FOCUS.zos"
WAVEFRONT_NAME = "TASK005C_C_WAVEFRONT_BEST_FOCUS.zos"
MANIFEST_NAME = "TASK005C_DIAGNOSTIC_MANIFEST.json"
WORKER_ACTIONS = ("fixed", "paraxial", "wavefront")


class DiagnosticBuildError(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=os.environ.get(INSTALL_ENV),
        help=f"OpticStudio installation directory; defaults to {INSTALL_ENV}",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing diagnostic files in the output directory",
    )
    parser.add_argument("--worker-action", choices=WORKER_ACTIONS, help=argparse.SUPPRESS)
    parser.add_argument("--source", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--destination", type=Path, help=argparse.SUPPRESS)
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _index_at_surface(system: Any, surface: int) -> float:
    count = int(system.SystemData.Wavelengths.NumberOfWavelengths)
    system_module = importlib.import_module("System")
    values = system_module.Array[system_module.Double]([0.0] * count)
    returned = int(system.LDE.GetIndex(surface, count, values))
    if returned != count or count < 1:
        raise DiagnosticBuildError(
            f"LDE.GetIndex({surface}) returned {returned}; expected {count}"
        )
    value = float(values[0])
    if not math.isfinite(value) or value <= 0:
        raise DiagnosticBuildError(f"invalid refractive index at surface {surface}: {value}")
    return value


def _quick_focus_wavefront(session: Any) -> None:
    enum_type = session.zosapi.Tools.General.QuickFocusCriterion
    criterion = None
    for name in ("WavefrontError", "Wavefront", "WavefrontOPD"):
        criterion = getattr(enum_type, name, None)
        if criterion is not None:
            break
    if criterion is None:
        try:
            system_module = importlib.import_module("System")
            names = tuple(str(name) for name in system_module.Enum.GetNames(enum_type))
        except Exception as exc:  # noqa: BLE001 - workstation enum discovery is diagnostic
            raise DiagnosticBuildError(
                "cannot enumerate QuickFocusCriterion values"
            ) from exc
        match = next((name for name in names if "wave" in name.lower()), None)
        if match is None:
            raise DiagnosticBuildError(
                f"no wavefront Quick Focus criterion is exposed; names={names}"
            )
        criterion = getattr(enum_type, match)

    tool = session.system.Tools.OpenQuickFocus()
    try:
        tool.Criterion = criterion
        tool.UseCentroid = False
        tool.RunAndWaitForCompletion()
    finally:
        close = getattr(tool, "Close", None)
        if callable(close):
            close()


def _geometry_payload(session: Any, *, variant: str, focus_method: str, path: Path) -> dict[str, Any]:
    system = session.system
    lde = system.LDE
    if int(lde.NumberOfSurfaces) != 5:
        raise DiagnosticBuildError(
            f"diagnostic file must have 5 sequential surfaces, got {int(lde.NumberOfSurfaces)}"
        )
    rows = tuple(lde.GetSurfaceAt(index) for index in range(1, 5))
    wavelength_nm = float(system.SystemData.Wavelengths.GetWavelength(1).Wavelength) * 1000.0
    aperture = float(system.SystemData.Aperture.ApertureValue)
    cornea_to_iol = float(rows[1].Thickness)
    iol_to_image = float(rows[2].Thickness)
    total = float(rows[0].Thickness) + cornea_to_iol + iol_to_image
    payload = {
        "variant": variant,
        "focus_method": focus_method,
        "formal_artifact": False,
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "wavelength_nm": wavelength_nm,
        "entrance_pupil_diameter_mm": aperture,
        "surface_count": int(lde.NumberOfSurfaces),
        "post_cornea_to_iol_ref_mm": cornea_to_iol,
        "iol_ref_to_image_mm": iol_to_image,
        "anterior_cornea_to_image_mm": total,
        "medium_index_after_cornea": _index_at_surface(system, 2),
        "medium_index_after_iol_ref": _index_at_surface(system, 3),
        "image_comment": str(rows[3].Comment).strip(),
    }
    if not math.isclose(payload["medium_index_after_iol_ref"], 1.336, abs_tol=1e-6):
        raise DiagnosticBuildError(
            "IOL reference does not continue the expected n=1.336 medium"
        )
    return payload


def _save_loaded_system(session: Any, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    session.system.SaveAs(str(destination.resolve()))
    if not destination.is_file():
        raise DiagnosticBuildError(f"OpticStudio did not create {destination}")


def _worker(args: argparse.Namespace) -> None:
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")
    if args.destination is None:
        raise SystemExit("--destination is required in worker mode")

    baseline = ScientificBaseline(args.baseline_id)
    spec = standard_eye_construction(baseline)
    destination = args.destination.resolve()

    with open_zos_session(args.install_dir) as session:
        if args.worker_action == "fixed":
            build_standard_eye_asset(session, spec, destination)
            image = session.system.LDE.GetSurfaceAt(4)
            image.Comment = f"{IMAGE_REF}__DIAG_A_FIXED"
            _save_loaded_system(session, destination)
            payload = _geometry_payload(
                session,
                variant="A_FIXED_REFERENCE",
                focus_method="fixed_reference",
                path=destination,
            )
        else:
            if args.source is None or not args.source.is_file():
                raise SystemExit("--source must reference DIAG-A in derive worker modes")
            session.system.LoadFile(str(args.source.resolve()), False)
            editor = SequentialEditor(session.system, session.zosapi)
            image = editor.surface(4)

            if args.worker_action == "paraxial":
                target_post_to_image = corneal_paraxial_focus_from_post_mm(spec)
                target_iol_to_image = target_post_to_image - spec.iol_from_post_cornea_mm
                if not math.isfinite(target_iol_to_image) or target_iol_to_image <= 0:
                    raise DiagnosticBuildError(
                        f"invalid paraxial diagnostic IMAGE distance: {target_iol_to_image}"
                    )
                editor.set_thickness(3, target_iol_to_image)
                image.Comment = f"{IMAGE_REF}__DIAG_B_PARAXIAL"
                _save_loaded_system(session, destination)
                payload = _geometry_payload(
                    session,
                    variant="B_PARAXIAL_FOCUS",
                    focus_method="paraxial_diagnostic",
                    path=destination,
                )
            elif args.worker_action == "wavefront":
                _quick_focus_wavefront(session)
                image.Comment = f"{IMAGE_REF}__DIAG_C_QF_WAVEFRONT"
                _save_loaded_system(session, destination)
                payload = _geometry_payload(
                    session,
                    variant="C_WAVEFRONT_BEST_FOCUS",
                    focus_method="quickfocus_wavefront_error",
                    path=destination,
                )
            else:
                raise SystemExit(f"unsupported worker action: {args.worker_action}")

    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _parse_worker_payload(stdout: str) -> dict[str, Any]:
    starts = [index for index, char in enumerate(stdout) if char == "{"]
    for start in reversed(starts):
        try:
            payload, _ = json.JSONDecoder().raw_decode(stdout[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("formal_artifact") is False:
            return payload
    raise DiagnosticBuildError(f"worker emitted no diagnostic JSON payload:\n{stdout}")


def _run_worker(
    args: argparse.Namespace,
    action: str,
    destination: Path,
    *,
    source: Path | None = None,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--install-dir",
        str(args.install_dir),
        "--baseline-id",
        str(args.baseline_id),
        "--worker-action",
        action,
        "--destination",
        str(destination),
    ]
    if source is not None:
        command.extend(("--source", str(source)))
    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    if completed.returncode != 0:
        raise DiagnosticBuildError(
            f"diagnostic {action} worker failed with exit {completed.returncode}:\n"
            f"{completed.stdout}{completed.stderr}"
        )
    return _parse_worker_payload(completed.stdout)


def main() -> None:
    args = _parser().parse_args()
    if args.worker_action is not None:
        _worker(args)
        return
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = (
        output_dir / FIXED_NAME,
        output_dir / PARAXIAL_NAME,
        output_dir / WAVEFRONT_NAME,
        output_dir / MANIFEST_NAME,
    )
    existing = tuple(path for path in targets if path.exists())
    if existing and not args.overwrite:
        names = ", ".join(path.name for path in existing)
        raise SystemExit(
            f"Refusing to overwrite existing diagnostic output(s): {names}. "
            "Use a new --output-dir or pass --overwrite explicitly."
        )
    if args.overwrite:
        for path in existing:
            if path.is_file():
                path.unlink()

    fixed_path = output_dir / FIXED_NAME
    paraxial_path = output_dir / PARAXIAL_NAME
    wavefront_path = output_dir / WAVEFRONT_NAME

    fixed = _run_worker(args, "fixed", fixed_path)
    paraxial = _run_worker(args, "paraxial", paraxial_path, source=fixed_path)
    wavefront = _run_worker(args, "wavefront", wavefront_path, source=fixed_path)

    manifest = {
        "task": "TASK-005C-manual-diagnostics",
        "formal_artifact": False,
        "baseline_id": args.baseline_id,
        "python_version": platform.python_version(),
        "diagnostic_files": [fixed, paraxial, wavefront],
        "manual_zernike_required": True,
        "zernike_api_invoked_by_this_script": False,
    }
    manifest_path = output_dir / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
