"""Inspect the frozen TASK-014 spectacle-to-corneal-plane prescription contract.

This script is pure Python and does not use OpticStudio. It exists to make the
preoperative spectacle prescription, vertex distance, corneal-plane treatment, and
A0V12/B0V12/C0V12 prescription identities explicit before any optical acquisition.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline
from whole_eye_mvp.task014_vertex_corrected_cornea import task014_prescription_snapshot

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-id", default=CURRENT_SCIENTIFIC_BASELINE_ID)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON path. If omitted, the snapshot is printed only.",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    baseline = ScientificBaseline(args.baseline_id)
    payload = task014_prescription_snapshot(baseline)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        output = args.output
        if not output.is_absolute():
            output = REPOSITORY_ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
