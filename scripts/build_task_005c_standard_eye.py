"""Build or read-only validate the TASK-005C standard IOL eye."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.domain import ScientificBaseline
from whole_eye_mvp.standard_eye import build_standard_eye, validate_registered_standard_eye
from whole_eye_mvp.store import open_project_store
from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[1] / "project"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=os.environ.get(INSTALL_ENV),
        help=f"OpticStudio installation directory; defaults to {INSTALL_ENV}",
    )
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--baseline-id", default="MVP_2026_v1")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Reload the existing locked standard eye without rewriting it",
    )
    return parser


def _validation_payload(validation: object) -> dict[str, object]:
    payload = asdict(validation)
    payload["path"] = str(payload["path"])
    return payload


def main() -> None:
    args = _parser().parse_args()
    if args.install_dir is None:
        raise SystemExit(f"Pass --install-dir or set {INSTALL_ENV}.")

    baseline = ScientificBaseline(args.baseline_id)
    store = open_project_store(args.project_dir, baseline)
    with open_zos_session(args.install_dir) as session:
        if args.validate_only:
            validation = validate_registered_standard_eye(session, store, baseline)
            payload = {
                "mode": "validate-only",
                "passed": validation.passed,
                "validation": _validation_payload(validation),
            }
        else:
            report = build_standard_eye(session, store, baseline)
            payload = {
                "mode": "build",
                "passed": report.passed,
                "validation": _validation_payload(report.validation),
                "artifact": None if report.artifact is None else asdict(report.artifact),
                "validation_artifact": None
                if report.validation_artifact is None
                else asdict(report.validation_artifact),
            }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
