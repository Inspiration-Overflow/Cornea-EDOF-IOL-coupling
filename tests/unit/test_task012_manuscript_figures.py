from __future__ import annotations

import json
from pathlib import Path

import pytest

from whole_eye_mvp.manuscript_figures import (
    MANUSCRIPT_FIGURE_NAMES,
    load_pair_rows,
    render_manuscript_figures,
    write_manuscript_figure_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAIR_CSV = PROJECT_ROOT / "docs/evidence/task012/TASK_012_PAIR_ANALYSIS.csv"
THROUGH_FOCUS_CSV = PROJECT_ROOT / "docs/evidence/task011/TASK_011_RUN72_THROUGH_FOCUS.csv"


def _row(rows: tuple[dict[str, str], ...], *, base: str, cornea: str, platform: str, pupil: float) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if row["base_id"] == base
        and row["cornea_id"] == cornea
        and row["platform_id"] == platform
        and float(row["pupil_mm"]) == pupil
    ]
    assert len(matches) == 1
    return matches[0]


def test_manuscript_numeric_story_matches_formal_pair_evidence() -> None:
    rows = load_pair_rows(PAIR_CSV)
    assert len(rows) == 36
    assert sum(float(row["delta_dof50_width_d"]) > 0 for row in rows) == 30
    assert sum(float(row["delta_dof50_width_d"]) < 0 for row in rows) == 6
    assert all(float(row["delta_mtfa_at_zero_d"]) < 0 for row in rows)
    assert all(float(row["delta_tf_mtfa_mean"]) < 0 for row in rows)
    assert sum(row["dof50_effect_status"] == "lower_bound" for row in rows) == 5
    assert sum(row["pair_peak_censored"] == "True" for row in rows) == 8

    b0_wfs_lb3 = _row(rows, base="LB_AL2395", cornea="B0", platform="WFS", pupil=3.0)
    b0_wfs_lb5 = _row(rows, base="LB_AL2395", cornea="B0", platform="WFS", pupil=5.0)
    c0_rad_atc5 = _row(rows, base="ATC_M3_AL24477", cornea="C0", platform="RAD", pupil=5.0)
    c0_hoa_lb5 = _row(rows, base="LB_AL2395", cornea="C0", platform="HOA", pupil=5.0)
    c0_hoa_atc5 = _row(rows, base="ATC_M3_AL24477", cornea="C0", platform="HOA", pupil=5.0)

    assert float(b0_wfs_lb3["delta_dof50_width_d"]) == pytest.approx(0.46237516440675397)
    assert b0_wfs_lb3["dof50_effect_status"] == "lower_bound"
    assert float(b0_wfs_lb5["delta_dof50_width_d"]) == pytest.approx(0.033736090170452426)
    assert float(c0_rad_atc5["delta_dof50_width_d"]) == pytest.approx(0.29018118206164023)
    assert c0_rad_atc5["dof50_effect_status"] == "lower_bound"
    assert float(c0_hoa_lb5["delta_dof50_width_d"]) == pytest.approx(-0.0973692610952116)
    assert float(c0_hoa_atc5["delta_dof50_width_d"]) == pytest.approx(0.3921003806995236)
    assert c0_hoa_atc5["dof50_effect_status"] == "lower_bound"


def test_manuscript_renderer_generates_exact_five_figure_contract(tmp_path: Path) -> None:
    output_dir = tmp_path / "figures"
    figures = render_manuscript_figures(
        pair_csv=PAIR_CSV,
        through_focus_csv=THROUGH_FOCUS_CSV,
        output_dir=output_dir,
    )
    assert tuple(path.name for path in figures) == MANUSCRIPT_FIGURE_NAMES
    assert all(path.is_file() and path.stat().st_size > 0 for path in figures)

    manifest_path = output_dir / "MANUSCRIPT_FIGURE_EVIDENCE.json"
    write_manuscript_figure_manifest(
        pair_csv=PAIR_CSV,
        through_focus_csv=THROUGH_FOCUS_CSV,
        figure_paths=figures,
        output_path=manifest_path,
        renderer_commit="test-commit",
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "MANUSCRIPT-PRESENTATION"
    assert payload["presentation_only"] is True
    assert payload["scientific_values_changed"] is False
    assert payload["opticstudio_used"] is False
    assert payload["figure_count"] == 5
    assert set(payload["figures"]) == set(MANUSCRIPT_FIGURE_NAMES)
