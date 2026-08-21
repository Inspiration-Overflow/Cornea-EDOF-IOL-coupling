from __future__ import annotations

import os
from pathlib import Path

from whole_eye_mvp.manuscript_figures import (
    MANUSCRIPT_FIGURE_NAMES,
    render_manuscript_figures,
    write_manuscript_figure_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_CSV = PROJECT_ROOT / "docs/evidence/task012/TASK_012_PAIR_ANALYSIS.csv"
THROUGH_FOCUS_CSV = PROJECT_ROOT / "docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv"
OUTPUT_DIR = PROJECT_ROOT / "docs/evidence/task012/manuscript_figures"
MANIFEST_PATH = OUTPUT_DIR / "MANUSCRIPT_FIGURE_EVIDENCE.json"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUTPUT_DIR.glob("*.png"):
        path.unlink()
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()

    figures = render_manuscript_figures(
        pair_csv=PAIR_CSV,
        through_focus_csv=THROUGH_FOCUS_CSV,
        output_dir=OUTPUT_DIR,
    )
    write_manuscript_figure_manifest(
        pair_csv=PAIR_CSV.relative_to(PROJECT_ROOT),
        through_focus_csv=THROUGH_FOCUS_CSV.relative_to(PROJECT_ROOT),
        figure_paths=figures,
        output_path=MANIFEST_PATH,
        renderer_commit=os.environ.get("GITHUB_SHA", "WORKTREE"),
    )
    if tuple(path.name for path in figures) != MANUSCRIPT_FIGURE_NAMES:
        raise RuntimeError("manuscript figure set differs from the frozen presentation contract")
    print(f"Generated {len(figures)} manuscript figures in {OUTPUT_DIR}")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
