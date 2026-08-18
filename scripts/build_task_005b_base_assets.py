"""Build or read-only validate the two frozen TASK-005B Zemax base assets."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from whole_eye_mvp.base_assets import build_base_assets, validate_base_assets
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline
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
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Reload existing locked assets without saving or replacing them",
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
            validations = validate_base_assets(session, store, baseline)
            payload = {
                "mode": "validate-only",
                "passed": bool(validations) and all(item.passed for item in validations),
                "validations": [_validation_payload(item) for item in validations],
            }
        else:
            report = build_base_assets(session, store, baseline)
            payload = {
                "mode": "build",
                "passed": report.passed,
                "validations": [
                    _validation_payload(item) for item in report.validations
                ],
                "artifacts": [asdict(item) for item in report.artifacts],
                "validation_artifact": None
                if report.validation_artifact is None
                else asdict(report.validation_artifact),
            }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()