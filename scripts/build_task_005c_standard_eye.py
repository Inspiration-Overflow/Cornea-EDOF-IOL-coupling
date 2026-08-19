"""Build or read-only validate the TASK-005C standard IOL eye."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline
from whole_eye_mvp.standard_eye import (
    build_standard_eye_asset,
    finalize_standard_eye_candidate,
    standard_eye_construction,
    validate_registered_standard_eye,
)
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[1] / "project"
WORKER_ACTIONS = ("build-candidate", "finalize-candidate", "validate-registered")


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
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Reload the existing locked standard eye without rewriting it",
    )
    parser.add_argument(
        "--worker-action",
        choices=WORKER_ACTIONS,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--candidate-path", type=Path, help=argparse.SUPPRESS)
    return parser


def _validation_payload(validation: object) -> dict[str, object]:
    payload = asdict(validation)
    payload["path"] = str(payload["path"])
    return payload


def _report_payload(report: object) -> dict[str, object]:
    return {
        "mode": "build",
        "passed": report.passed,
        "validation": _validation_payload(report.validation),
        "artifact": None if report.artifact is None else asdict(report.artifact),
        "validation_artifact": None
        if report.validation_artifact is None
        else asdict(report.validation_artifact),
    }


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload.get("passed", False):
        raise SystemExit(1)


def _worker(args: argparse.Namespace) -> None:
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")
    baseline = ScientificBaseline(args.baseline_id)

    if args.worker_action == "build-candidate":
        if args.candidate_path is None:
            raise SystemExit("--candidate-path is required for build-candidate")
        open_project_store(args.project_dir, baseline)
        spec = standard_eye_construction(baseline)
        with open_zos_session(args.install_dir) as session:
            built_path = build_standard_eye_asset(session, spec, args.candidate_path)
        _emit(
            {
                "mode": "worker-build-candidate",
                "passed": built_path.is_file(),
                "candidate_path": str(built_path),
            }
        )
        return

    store = open_project_store(args.project_dir, baseline)
    with open_zos_session(args.install_dir) as session:
        if args.worker_action == "finalize-candidate":
            if args.candidate_path is None:
                raise SystemExit("--candidate-path is required for finalize-candidate")
            report = finalize_standard_eye_candidate(
                session,
                store,
                baseline,
                args.candidate_path,
            )
            _emit(_report_payload(report))
            return
        if args.worker_action == "validate-registered":
            validation = validate_registered_standard_eye(session, store, baseline)
            _emit(
                {
                    "mode": "validate-only",
                    "passed": validation.passed,
                    "validation": _validation_payload(validation),
                }
            )
            return
    raise SystemExit(f"unsupported worker action: {args.worker_action}")


def _parse_worker_json(stdout: str) -> dict[str, Any]:
    starts = [index for index, char in enumerate(stdout) if char == "{"]
    for start in reversed(starts):
        try:
            payload, _ = json.JSONDecoder().raw_decode(stdout[start:])
        except json.JSONDecodeError:
            continue
        # Only the outer worker payload carries both markers; nested payloads such as
        # StandardEyeValidation also contain "passed" but never "mode".
        if isinstance(payload, dict) and "passed" in payload and "mode" in payload:
            return payload
    raise RuntimeError(f"worker emitted no JSON payload:\n{stdout}")


def _run_worker(
    args: argparse.Namespace,
    action: str,
    *,
    candidate_path: Path | None = None,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--install-dir",
        str(args.install_dir),
        "--project-dir",
        str(args.project_dir),
        "--baseline-id",
        str(args.baseline_id),
        "--worker-action",
        action,
    ]
    if candidate_path is not None:
        command.extend(("--candidate-path", str(candidate_path)))
    completed = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stdout + completed.stderr
        try:
            payload = _parse_worker_json(completed.stdout)
        except RuntimeError:
            raise RuntimeError(
                f"TASK-005C {action} worker failed with exit {completed.returncode}:\n{message}"
            ) from None
        print(completed.stderr, file=sys.stderr, end="")
        return payload
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    return _parse_worker_json(completed.stdout)


def main() -> None:
    args = _parser().parse_args()
    if args.worker_action is not None:
        _worker(args)
        return
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    # Fail fast on scientific-baseline mismatch before launching OpticStudio workers.
    baseline = ScientificBaseline(args.baseline_id)
    open_project_store(args.project_dir, baseline)

    if args.validate_only:
        payload = _run_worker(args, "validate-registered")
        _emit(payload)
        return

    with tempfile.TemporaryDirectory(prefix="task-005c-candidate-") as temp_name:
        candidate = Path(temp_name) / "STD_IOL_EYE_2024.candidate.zos"
        built = _run_worker(args, "build-candidate", candidate_path=candidate)
        if not built.get("passed", False):
            _emit(built)
            return
        # This second worker starts a fresh Python/OpticStudio process. It only loads the
        # saved candidate, runs Quick Focus + Zernike validation, and registers the asset
        # if every formal oracle passes.
        payload = _run_worker(args, "finalize-candidate", candidate_path=candidate)
        _emit(payload)


if __name__ == "__main__":
    main()
