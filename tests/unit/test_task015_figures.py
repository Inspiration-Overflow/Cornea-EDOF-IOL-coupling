from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp.extension96_analysis import analyze_extension96
from whole_eye_mvp.extension96_figures import generate_task015_figures

TASK013_DIR = Path("docs/evidence/task013")
TASK014_DIR = Path("docs/evidence/task014")


@pytest.mark.unit
def test_task015_renders_all_raw_and_summary_figures(tmp_path: Path) -> None:
    analysis = analyze_extension96(TASK013_DIR, TASK014_DIR)
    figures = generate_task015_figures(
        analysis,
        through_focus_csvs=(
            TASK013_DIR / "TASK_013_NATIVE_REFERENCE_THROUGH_FOCUS.csv",
            TASK014_DIR / "TASK_014_THROUGH_FOCUS.csv",
        ),
        output_dir=tmp_path,
    )

    raw = [path for path in figures if path.parent.name == "raw"]
    summary = [path for path in figures if path.parent.name == "summary"]
    assert len(figures) == 72
    assert len(raw) == 48
    assert len(summary) == 24
    assert all(path.is_file() and path.stat().st_size > 0 for path in figures)


@pytest.mark.unit
def test_task015_raw_figure_names_cover_every_pair(tmp_path: Path) -> None:
    analysis = analyze_extension96(TASK013_DIR, TASK014_DIR)
    figures = generate_task015_figures(
        analysis,
        through_focus_csvs=(
            TASK013_DIR / "TASK_013_NATIVE_REFERENCE_THROUGH_FOCUS.csv",
            TASK014_DIR / "TASK_014_THROUGH_FOCUS.csv",
        ),
        output_dir=tmp_path,
    )
    raw = [path.name for path in figures if path.parent.name == "raw"]
    assert len(set(raw)) == 48
    assert any("n0" in name for name in raw)
    assert any("a0v12" in name for name in raw)
    assert any("b0v12" in name for name in raw)
    assert any("c0v12" in name for name in raw)
    assert any("epd3" in name for name in raw)
    assert any("epd5" in name for name in raw)
