"""Render the complete accepted TASK-015 96-config figure supplement."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from whole_eye_mvp.extension96_analysis import analyze_extension96, sha256_file
from whole_eye_mvp.extension96_figures import generate_task015_figures

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK013_DIR = REPOSITORY_ROOT / "docs/evidence/task013"
DEFAULT_TASK014_DIR = REPOSITORY_ROOT / "docs/evidence/task014"
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "docs/evidence/task015/figures"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task013-dir", type=Path, default=DEFAULT_TASK013_DIR)
    parser.add_argument("--task014-dir", type=Path, default=DEFAULT_TASK014_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
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
        raise SystemExit("TASK-015 figure rendering requires a clean tracked checkout")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(head) != 40:
        raise SystemExit("TASK-015 figure rendering could not resolve Git HEAD")
    return head


def main() -> None:
    args = _parser().parse_args()
    task013_dir = args.task013_dir.resolve()
    task014_dir = args.task014_dir.resolve()
    output_dir = args.output_dir.resolve()
    code_commit = _git_head()

    analysis = analyze_extension96(task013_dir, task014_dir)
    through_focus_csvs = (
        task013_dir / "TASK_013_NATIVE_REFERENCE_THROUGH_FOCUS.csv",
        task014_dir / "TASK_014_THROUGH_FOCUS.csv",
    )
    figures = generate_task015_figures(
        analysis,
        through_focus_csvs=through_focus_csvs,
        output_dir=output_dir,
    )

    raw = tuple(path for path in figures if path.parent.name == "raw")
    summary = tuple(path for path in figures if path.parent.name == "summary")
    manifest = {
        "schema_version": 1,
        "phase": "TASK-015-FIGURE-SUPPLEMENT",
        "render_code_commit": code_commit,
        "opticstudio_used": False,
        "figure_count": len(figures),
        "raw_through_focus_figure_count": len(raw),
        "summary_figure_count": len(summary),
        "raw_pair_coverage_complete": len(raw) == 48,
        "source_through_focus_rows": 1440,
        "figures": [
            {
                "path": path.relative_to(output_dir).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in figures
        ],
    }
    manifest_path = output_dir / "TASK_015_FIGURE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "TASK-015 figure supplement PASS: "
        f"raw={len(raw)} summary={len(summary)} total={len(figures)}"
    )
    print(f"manifest={manifest_path.relative_to(REPOSITORY_ROOT)}")
    print(f"manifest_sha256={sha256_file(manifest_path)}")


if __name__ == "__main__":
    main()
