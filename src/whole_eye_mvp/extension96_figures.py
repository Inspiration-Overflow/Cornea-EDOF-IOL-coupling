from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .extension96_analysis import BASE_IDS, CORNEA_IDS, PLATFORM_IDS, PUPIL_MM, Task015Analysis
from .run72_analysis import PLATFORM_LABELS, PUPIL_LABELS, FactorKey, NumericBound, PairResult

HEATMAP_OUTCOMES = (
    ("delta_dof50_width_d", "ΔDOF50 (D)"),
    ("delta_mtfa_at_zero_d", "ΔMTFa at 0 D"),
    ("delta_tf_mtfa_mean", "ΔTF MTFa mean"),
)


class Task015FigureError(RuntimeError):
    pass


def _slug(value: str) -> str:
    return value.lower().replace("_", "-")


def _pair_index(pairs: Sequence[PairResult]) -> dict[FactorKey, PairResult]:
    index = {pair.factors: pair for pair in pairs}
    if len(index) != 48:
        raise Task015FigureError("TASK-015 figure generation requires 48 factor-unique pairs")
    return index


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _read_through_focus(paths: Sequence[Path]) -> dict[str, tuple[tuple[float, float], ...]]:
    curves: dict[str, list[tuple[float, float]]] = {}
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                config_id = row.get("config_id", "")
                if not config_id:
                    raise Task015FigureError(f"empty config_id in {path}")
                curves.setdefault(config_id, []).append(
                    (float(row["defocus_retina_d"]), float(row["mtfa"]))
                )
    result: dict[str, tuple[tuple[float, float], ...]] = {}
    for config_id, points in curves.items():
        if len(points) != 15:
            raise Task015FigureError(f"through-focus curve is not 15 points: {config_id}")
        result[config_id] = tuple(points)
    if len(result) != 96:
        raise Task015FigureError(f"expected 96 through-focus curves, got {len(result)}")
    return result


def _curve(curves: Mapping[str, tuple[tuple[float, float], ...]], config_id: str) -> tuple[tuple[float, float], ...]:
    try:
        return curves[config_id]
    except KeyError as exc:
        raise Task015FigureError(f"missing through-focus curve: {config_id}") from exc


def _draw_pair_curves(
    ax: plt.Axes,
    pair: PairResult,
    curves: Mapping[str, tuple[tuple[float, float], ...]],
    *,
    title: str,
    legend: bool,
) -> None:
    mono = _curve(curves, pair.mono_config_id)
    edof = _curve(curves, pair.edof_config_id)
    ax.plot([x for x, _ in mono], [y for _, y in mono], marker="o", label="MONO")
    ax.plot([x for x, _ in edof], [y for _, y in edof], marker="o", label="EDOF")
    ax.axvline(0.0, linewidth=0.8)
    annotations: list[str] = []
    if pair.pair_peak_censored:
        annotations.append("peak-window censored")
    if pair.dof50_effect_status != "exact":
        annotations.append(f"DOF50 {pair.dof50_effect_status}")
    if annotations:
        title += "\n[" + "; ".join(annotations) + "]"
    ax.set_title(title)
    ax.set_xlabel("Retinal defocus (D)")
    ax.set_ylabel("MTFa")
    if legend:
        ax.legend()


def _generate_raw_pair_figures(
    analysis: Task015Analysis,
    curves: Mapping[str, tuple[tuple[float, float], ...]],
    output_dir: Path,
) -> list[Path]:
    paths: list[Path] = []
    for pair in sorted(
        analysis.pairs,
        key=lambda item: (
            BASE_IDS.index(item.factors.base_id),
            CORNEA_IDS.index(item.factors.cornea_id),
            PLATFORM_IDS.index(item.factors.platform_id),
            PUPIL_MM.index(item.factors.pupil_mm),
        ),
    ):
        fig, ax = plt.subplots(figsize=(7.2, 5.2))
        title = (
            f"{pair.factors.base_id} — {pair.factors.cornea_id} × "
            f"{PLATFORM_LABELS[pair.factors.platform_id]} — {PUPIL_LABELS[pair.factors.pupil_mm]}"
        )
        _draw_pair_curves(ax, pair, curves, title=title, legend=True)
        path = output_dir / "raw" / (
            "through_focus_"
            f"{_slug(pair.factors.base_id)}_{_slug(pair.factors.cornea_id)}_"
            f"{_slug(pair.factors.platform_id)}_{PUPIL_LABELS[pair.factors.pupil_mm].lower()}.png"
        )
        _save(fig, path)
        paths.append(path)
    if len(paths) != 48:
        raise Task015FigureError(f"expected 48 raw pair figures, got {len(paths)}")
    return paths


def _generate_through_focus_panels(
    analysis: Task015Analysis,
    curves: Mapping[str, tuple[tuple[float, float], ...]],
    output_dir: Path,
) -> list[Path]:
    index = _pair_index(analysis.pairs)
    paths: list[Path] = []
    for base_id in BASE_IDS:
        for pupil_mm in PUPIL_MM:
            fig, axes = plt.subplots(4, 3, figsize=(13.2, 13.0), sharex=True, sharey=True)
            for row_index, cornea in enumerate(CORNEA_IDS):
                for col_index, platform in enumerate(PLATFORM_IDS):
                    pair = index[FactorKey(base_id, cornea, platform, pupil_mm)]
                    title = f"{cornea} × {PLATFORM_LABELS[platform]}"
                    _draw_pair_curves(
                        axes[row_index, col_index],
                        pair,
                        curves,
                        title=title,
                        legend=row_index == 0 and col_index == 0,
                    )
                    if row_index != len(CORNEA_IDS) - 1:
                        axes[row_index, col_index].set_xlabel("")
                    if col_index != 0:
                        axes[row_index, col_index].set_ylabel("")
            fig.suptitle(f"Through-focus MTFa — {base_id}, {PUPIL_LABELS[pupil_mm]}")
            path = output_dir / "summary" / (
                f"through_focus_panel_{_slug(base_id)}_{PUPIL_LABELS[pupil_mm].lower()}.png"
            )
            _save(fig, path)
            paths.append(path)
    return paths


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


def _generate_heatmaps(analysis: Task015Analysis, output_dir: Path) -> list[Path]:
    index = _pair_index(analysis.pairs)
    paths: list[Path] = []
    for base_id in BASE_IDS:
        for pupil_mm in PUPIL_MM:
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
                fig, ax = plt.subplots(figsize=(6.4, 5.4))
                image = ax.imshow(matrix, aspect="auto")
                ax.set_xticks(
                    range(len(PLATFORM_IDS)),
                    [PLATFORM_LABELS[platform] for platform in PLATFORM_IDS],
                )
                ax.set_yticks(range(len(CORNEA_IDS)), CORNEA_IDS)
                ax.set_xlabel("EDoF platform surrogate")
                ax.set_ylabel("Corneal background")
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
                path = output_dir / "summary" / (
                    f"heatmap_{outcome}_{_slug(base_id)}_{PUPIL_LABELS[pupil_mm].lower()}.png"
                )
                _save(fig, path)
                paths.append(path)
    return paths


def _tradeoff_group_label(dof_limited: bool, peak_limited: bool) -> str:
    if dof_limited and peak_limited:
        return "DOF boundary-limited + peak-window"
    if dof_limited:
        return "DOF boundary-limited"
    if peak_limited:
        return "Peak-window limited"
    return "DOF exact + peak exact"


def _tradeoff_marker(dof_limited: bool, peak_limited: bool) -> str:
    if dof_limited and peak_limited:
        return "s"
    if dof_limited:
        return "x"
    if peak_limited:
        return "^"
    return "o"


def _tradeoff_plot(
    pairs: Sequence[PairResult],
    y_outcome: str,
    y_label: str,
    path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    peak_sensitive = y_outcome == "delta_distance_peak_mtfa"
    groups: dict[tuple[bool, bool], list[PairResult]] = {}
    for pair in pairs:
        key = (
            pair.dof50_effect_status != "exact",
            pair.pair_peak_censored if peak_sensitive else False,
        )
        groups.setdefault(key, []).append(pair)
    for (dof_limited, peak_limited), members in sorted(groups.items()):
        ax.scatter(
            [pair.values["delta_dof50_width_d"] for pair in members],
            [pair.values[y_outcome] for pair in members],
            marker=_tradeoff_marker(dof_limited, peak_limited),
            label=_tradeoff_group_label(dof_limited, peak_limited),
        )
    ax.axhline(0.0, linewidth=0.8)
    ax.axvline(0.0, linewidth=0.8)
    ax.set_xlabel("ΔDOF50 (D), EDOF − MONO")
    ax.set_ylabel(y_label)
    ax.set_title(f"Extension–quality trade-off: {y_label}")
    ax.legend()
    _save(fig, path)


def _generate_tradeoffs(analysis: Task015Analysis, output_dir: Path) -> list[Path]:
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
        path = output_dir / "summary" / filename
        _tradeoff_plot(analysis.pairs, outcome, label, path)
        paths.append(path)
    return paths


def _difference_bound(left: PairResult, right: PairResult) -> NumericBound:
    left_bound = NumericBound.from_status(
        left.values["delta_dof50_width_d"], left.dof50_effect_status
    )
    right_bound = NumericBound.from_status(
        right.values["delta_dof50_width_d"], right.dof50_effect_status
    )
    return left_bound.add(right_bound.scaled(-1.0))


def _sensitivity_plot(
    analysis: Task015Analysis,
    *,
    contrast_type: str,
    outcome: str,
    title: str,
    path: Path,
) -> None:
    index = _pair_index(analysis.pairs)
    labels: list[str] = []
    values: list[float] = []
    statuses: list[str] = []
    if contrast_type == "pupil":
        for base_id in BASE_IDS:
            for cornea in CORNEA_IDS:
                for platform in PLATFORM_IDS:
                    left = index[FactorKey(base_id, cornea, platform, 5.0)]
                    right = index[FactorKey(base_id, cornea, platform, 3.0)]
                    labels.append(f"{base_id}|{cornea}|{platform}")
                    values.append(left.values[outcome] - right.values[outcome])
                    statuses.append(
                        _difference_bound(left, right).status()
                        if outcome == "delta_dof50_width_d"
                        else "exact"
                    )
    elif contrast_type == "base":
        for cornea in CORNEA_IDS:
            for platform in PLATFORM_IDS:
                for pupil_mm in PUPIL_MM:
                    left = index[FactorKey("ATC_M3_AL24477", cornea, platform, pupil_mm)]
                    right = index[FactorKey("LB_AL2395", cornea, platform, pupil_mm)]
                    labels.append(f"{cornea}|{platform}|{PUPIL_LABELS[pupil_mm]}")
                    values.append(left.values[outcome] - right.values[outcome])
                    statuses.append(
                        _difference_bound(left, right).status()
                        if outcome == "delta_dof50_width_d"
                        else "exact"
                    )
    else:
        raise Task015FigureError(f"unknown sensitivity contrast type: {contrast_type}")

    fig, ax = plt.subplots(figsize=(12.2, 5.4))
    groups: dict[str, list[tuple[int, float]]] = {}
    for index_value, (value, status) in enumerate(zip(values, statuses, strict=True)):
        groups.setdefault(status, []).append((index_value, value))
    markers = {
        "exact": "o",
        "lower_bound": ">",
        "upper_bound": "<",
        "bounded_interval": "s",
        "indeterminate": "x",
    }
    for status, points in sorted(groups.items()):
        ax.scatter(
            [point[0] for point in points],
            [point[1] for point in points],
            marker=markers.get(status, "x"),
            label=status if outcome == "delta_dof50_width_d" else None,
        )
    if outcome == "delta_dof50_width_d" and len(groups) > 1:
        ax.legend(title="DOF contrast status")
    ax.axhline(0.0, linewidth=0.8)
    ax.set_xticks(range(len(labels)), labels, rotation=70, ha="right")
    ax.set_ylabel("Contrast value")
    ax.set_title(title)
    _save(fig, path)


def _generate_sensitivity_figures(analysis: Task015Analysis, output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for outcome, short in (
        ("delta_dof50_width_d", "dof50"),
        ("delta_mtfa_at_zero_d", "mtfa_zero"),
    ):
        pupil_path = output_dir / "summary" / f"pupil_sensitivity_{short}.png"
        _sensitivity_plot(
            analysis,
            contrast_type="pupil",
            outcome=outcome,
            title=f"Pupil sensitivity ({outcome}): EPD5 − EPD3",
            path=pupil_path,
        )
        paths.append(pupil_path)
        base_path = output_dir / "summary" / f"base_sensitivity_{short}.png"
        _sensitivity_plot(
            analysis,
            contrast_type="base",
            outcome=outcome,
            title=f"Base-eye sensitivity ({outcome}): ATC − LB",
            path=base_path,
        )
        paths.append(base_path)
    return paths


def _generate_mechanism_map(analysis: Task015Analysis, output_dir: Path) -> Path:
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
    ax.set_title("Whole-eye HOA mechanism map — accepted 96-config layer")
    ax.legend()
    path = output_dir / "summary" / "mechanism_delta_c40_c60.png"
    _save(fig, path)
    return path


def generate_task015_figures(
    analysis: Task015Analysis,
    *,
    through_focus_csvs: Sequence[Path],
    output_dir: Path,
) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    curves = _read_through_focus(through_focus_csvs)
    paths: list[Path] = []
    paths.extend(_generate_raw_pair_figures(analysis, curves, output_dir))
    paths.extend(_generate_heatmaps(analysis, output_dir))
    paths.extend(_generate_through_focus_panels(analysis, curves, output_dir))
    paths.extend(_generate_tradeoffs(analysis, output_dir))
    paths.extend(_generate_sensitivity_figures(analysis, output_dir))
    paths.append(_generate_mechanism_map(analysis, output_dir))
    expected_count = 72
    if len(paths) != expected_count:
        raise Task015FigureError(f"expected {expected_count} TASK-015 figures, got {len(paths)}")
    relative_names = [path.relative_to(output_dir).as_posix() for path in paths]
    if len(set(relative_names)) != len(relative_names):
        raise Task015FigureError("TASK-015 figure filenames are not unique")
    return tuple(paths)
