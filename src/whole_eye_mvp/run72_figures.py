from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .run72_analysis import (
    BASE_IDS,
    CORNEA_IDS,
    PLATFORM_IDS,
    PLATFORM_LABELS,
    PUPIL_LABELS,
    FactorKey,
    PairResult,
    Task012Analysis,
)

HEATMAP_OUTCOMES = (
    ("delta_dof50_width_d", "ΔDOF50 (D)"),
    ("delta_mtfa_at_zero_d", "ΔMTFa at 0 D"),
    ("delta_tf_mtfa_mean", "ΔTF MTFa mean"),
)


class Task012FigureError(RuntimeError):
    pass


def _slug(value: str) -> str:
    return value.lower().replace("_", "-")


def _pair_index(pairs: Sequence[PairResult]) -> dict[FactorKey, PairResult]:
    index = {pair.factors: pair for pair in pairs}
    if len(index) != 36:
        raise Task012FigureError("figure generation requires exact 36 factor-unique pairs")
    return index


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _heatmap_text(pair: PairResult, outcome: str) -> str:
    value = pair.values[outcome]
    if outcome != "delta_dof50_width_d":
        return f"{value:+.3f}"
    prefix = {
        "exact": "",
        "lower_bound": "≥",
        "upper_bound": "≤",
        "indeterminate": "~",
    }[pair.dof50_effect_status]
    return f"{prefix}{value:+.3f}"


def _generate_heatmaps(
    analysis: Task012Analysis,
    output_dir: Path,
) -> list[Path]:
    index = _pair_index(analysis.pairs)
    paths: list[Path] = []
    for base_id in BASE_IDS:
        for pupil_mm in (3.0, 5.0):
            for outcome, title in HEATMAP_OUTCOMES:
                matrix = np.array(
                    [
                        [
                            index[FactorKey(base_id, cornea, platform, pupil_mm)].values[outcome]
                            for platform in PLATFORM_IDS
                        ]
                        for cornea in CORNEA_IDS
                    ],
                    dtype=float,
                )
                fig, ax = plt.subplots(figsize=(6.2, 4.8))
                image = ax.imshow(matrix, aspect="auto")
                ax.set_xticks(range(len(PLATFORM_IDS)), [PLATFORM_LABELS[p] for p in PLATFORM_IDS])
                ax.set_yticks(range(len(CORNEA_IDS)), CORNEA_IDS)
                ax.set_xlabel("EDoF platform surrogate")
                ax.set_ylabel("Corneal prototype")
                ax.set_title(f"{title} — {base_id}, {PUPIL_LABELS[pupil_mm]}")
                for row_index, cornea in enumerate(CORNEA_IDS):
                    for col_index, platform in enumerate(PLATFORM_IDS):
                        pair = index[FactorKey(base_id, cornea, platform, pupil_mm)]
                        ax.text(
                            col_index,
                            row_index,
                            _heatmap_text(pair, outcome),
                            ha="center",
                            va="center",
                        )
                fig.colorbar(image, ax=ax, label=title)
                path = output_dir / (
                    f"heatmap_{outcome}_{_slug(base_id)}_{PUPIL_LABELS[pupil_mm].lower()}.png"
                )
                _save(fig, path)
                paths.append(path)
    return paths


def _read_through_focus(path: Path) -> dict[str, tuple[tuple[float, float], ...]]:
    curves: dict[str, list[tuple[float, float]]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            config_id = row.get("config_id", "")
            curves.setdefault(config_id, []).append(
                (float(row["defocus_retina_d"]), float(row["mtfa"]))
            )
    result: dict[str, tuple[tuple[float, float], ...]] = {}
    for config_id, points in curves.items():
        if len(points) != 15:
            raise Task012FigureError(f"through-focus figure curve is not 15 points: {config_id}")
        result[config_id] = tuple(points)
    return result


def _generate_through_focus_panels(
    analysis: Task012Analysis,
    through_focus_csv: Path,
    output_dir: Path,
) -> list[Path]:
    index = _pair_index(analysis.pairs)
    curves = _read_through_focus(through_focus_csv)
    paths: list[Path] = []
    for base_id in BASE_IDS:
        for pupil_mm in (3.0, 5.0):
            fig, axes = plt.subplots(3, 3, figsize=(13.2, 10.2), sharex=True, sharey=True)
            for row_index, cornea in enumerate(CORNEA_IDS):
                for col_index, platform in enumerate(PLATFORM_IDS):
                    ax = axes[row_index, col_index]
                    pair = index[FactorKey(base_id, cornea, platform, pupil_mm)]
                    mono = curves[pair.mono_config_id]
                    edof = curves[pair.edof_config_id]
                    ax.plot([x for x, _ in mono], [y for _, y in mono], marker="o", label="MONO")
                    ax.plot([x for x, _ in edof], [y for _, y in edof], marker="o", label="EDOF")
                    ax.axvline(0.0, linewidth=0.8)
                    ax.set_title(f"{cornea} × {PLATFORM_LABELS[platform]}")
                    if row_index == 2:
                        ax.set_xlabel("Retinal defocus (D)")
                    if col_index == 0:
                        ax.set_ylabel("MTFa")
                    if row_index == 0 and col_index == 0:
                        ax.legend()
            fig.suptitle(f"Through-focus MTFa — {base_id}, {PUPIL_LABELS[pupil_mm]}")
            path = output_dir / f"through_focus_{_slug(base_id)}_{PUPIL_LABELS[pupil_mm].lower()}.png"
            _save(fig, path)
            paths.append(path)
    return paths


def _tradeoff_plot(
    pairs: Sequence[PairResult],
    y_outcome: str,
    y_label: str,
    path: Path,
) -> None:
    exact = [pair for pair in pairs if pair.dof50_effect_status == "exact"]
    limited = [pair for pair in pairs if pair.dof50_effect_status != "exact"]
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    ax.scatter(
        [pair.values["delta_dof50_width_d"] for pair in exact],
        [pair.values[y_outcome] for pair in exact],
        label="DOF50 exact",
    )
    if limited:
        ax.scatter(
            [pair.values["delta_dof50_width_d"] for pair in limited],
            [pair.values[y_outcome] for pair in limited],
            marker="x",
            label="DOF50 boundary-limited",
        )
    ax.axhline(0.0, linewidth=0.8)
    ax.axvline(0.0, linewidth=0.8)
    ax.set_xlabel("ΔDOF50 (D), EDOF − MONO")
    ax.set_ylabel(y_label)
    ax.set_title(f"Extension–quality trade-off: {y_label}")
    ax.legend()
    _save(fig, path)


def _generate_tradeoffs(analysis: Task012Analysis, output_dir: Path) -> list[Path]:
    specs = (
        ("delta_mtfa_at_zero_d", "ΔMTFa at 0 D", "tradeoff_dof50_vs_mtfa_zero.png"),
        ("delta_tf_mtfa_mean", "ΔTF MTFa mean", "tradeoff_dof50_vs_tf_mean.png"),
        (
            "delta_distance_peak_mtfa",
            "Δobserved peak MTFa within preregistered window",
            "tradeoff_dof50_vs_window_peak_mtfa.png",
        ),
    )
    paths: list[Path] = []
    for outcome, label, filename in specs:
        path = output_dir / filename
        _tradeoff_plot(analysis.pairs, outcome, label, path)
        paths.append(path)
    return paths


def _sensitivity_plot(
    analysis: Task012Analysis,
    contrast_type: str,
    outcome: str,
    title: str,
    path: Path,
) -> None:
    rows = [
        row
        for row in analysis.contrasts
        if row["contrast_type"] == contrast_type and row["outcome"] == outcome
    ]
    labels: list[str] = []
    values: list[float] = []
    for row in rows:
        if contrast_type == "pupil_sensitivity":
            labels.append(f"{row['base_id']}|{row['cornea_id']}|{row['platform_id']}")
        else:
            labels.append(f"{row['cornea_id']}|{row['platform_id']}|EPD{int(float(row['pupil_mm']))}")
        values.append(float(row["value"]))
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    ax.scatter(range(len(values)), values)
    ax.axhline(0.0, linewidth=0.8)
    ax.set_xticks(range(len(labels)), labels, rotation=70, ha="right")
    ax.set_ylabel("Contrast value")
    ax.set_title(title)
    _save(fig, path)


def _generate_sensitivity_figures(analysis: Task012Analysis, output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for outcome, short in (
        ("delta_dof50_width_d", "dof50"),
        ("delta_mtfa_at_zero_d", "mtfa_zero"),
    ):
        pupil_path = output_dir / f"pupil_sensitivity_{short}.png"
        _sensitivity_plot(
            analysis,
            "pupil_sensitivity",
            outcome,
            f"Pupil sensitivity ({outcome}): EPD5 − EPD3",
            pupil_path,
        )
        paths.append(pupil_path)
        base_path = output_dir / f"base_sensitivity_{short}.png"
        _sensitivity_plot(
            analysis,
            "base_sensitivity",
            outcome,
            f"Base-eye sensitivity ({outcome}): ATC − LB",
            base_path,
        )
        paths.append(base_path)
    return paths


def _generate_mechanism_map(analysis: Task012Analysis, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.0, 5.4))
    for platform in PLATFORM_IDS:
        pairs = [pair for pair in analysis.pairs if pair.factors.platform_id == platform]
        ax.scatter(
            [pair.values["delta_c40_um"] for pair in pairs],
            [pair.values["delta_c60_um"] for pair in pairs],
            label=PLATFORM_LABELS[platform],
        )
    ax.axhline(0.0, linewidth=0.8)
    ax.axvline(0.0, linewidth=0.8)
    ax.set_xlabel("ΔC40 (µm)")
    ax.set_ylabel("ΔC60 (µm)")
    ax.set_title("Whole-eye HOA mechanism map")
    ax.legend()
    path = output_dir / "mechanism_delta_c40_c60.png"
    _save(fig, path)
    return path


def generate_task012_figures(
    analysis: Task012Analysis,
    *,
    through_focus_csv: Path,
    output_dir: Path,
) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    paths.extend(_generate_heatmaps(analysis, output_dir))
    paths.extend(_generate_through_focus_panels(analysis, through_focus_csv, output_dir))
    paths.extend(_generate_tradeoffs(analysis, output_dir))
    paths.extend(_generate_sensitivity_figures(analysis, output_dir))
    paths.append(_generate_mechanism_map(analysis, output_dir))
    expected_count = 24
    if len(paths) != expected_count:
        raise Task012FigureError(f"expected {expected_count} TASK-012 figures, got {len(paths)}")
    if len({path.name for path in paths}) != len(paths):
        raise Task012FigureError("TASK-012 figure filenames are not unique")
    return tuple(paths)
