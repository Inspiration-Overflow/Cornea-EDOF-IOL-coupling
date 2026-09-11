"""Generate the four prespecified supplemental figures from exported CSV data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

CORNEA_COLORS = {"A0": "#2f6f9f", "B0": "#c46b27", "C0": "#4d8b57"}
THRESHOLD_STYLES = {
    "0.3": ("#2f6f9f", "o"),
    "0.5": ("#c46b27", "s"),
    "0.7": ("#4d8b57", "^"),
}
STRATEGY_STYLES = {
    ("full_eye", "MONO"): ("#2f6f9f", "-"),
    ("full_eye", "EDOF"): ("#2f6f9f", "--"),
    ("distance_component_anchored", "MONO"): ("#c46b27", "-"),
    ("distance_component_anchored", "EDOF"): ("#c46b27", "--"),
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return rows


def _float(row: dict[str, str], field: str) -> float:
    value = float(row[field])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {field}: {row[field]!r}")
    return value


def _bool(row: dict[str, str], field: str) -> bool:
    return row[field].strip().lower() in {"true", "1"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _save_figure(fig, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    png = output_dir / f"{stem}.png"
    pdf = output_dir / f"{stem}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return [png, pdf]


def _style_axes(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="both", color="#d9d9d9", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def _figure_one(
    old_config_rows: list[dict[str, str]],
    old_pair_rows: list[dict[str, str]],
    supplemental_config_rows: list[dict[str, str]],
    supplemental_pair_rows: list[dict[str, str]],
    output_dir: Path,
) -> list[Path]:
    old_by_config = {row["config_id"]: row for row in old_config_rows}
    supplemental_by_config = {row["config_id"]: row for row in supplemental_config_rows}
    new_by_pair = {row["pair_key"]: row for row in supplemental_pair_rows}
    points: list[dict[str, object]] = []
    for old in old_pair_rows:
        new = new_by_pair.get(old["pair_key"])
        if new is None:
            raise ValueError(f"supplemental pair is missing: {old['pair_key']}")
        new_mono = supplemental_by_config[new["mono_config_id"]]
        new_edof = supplemental_by_config[new["edof_config_id"]]
        old_mono = old_by_config[old["mono_config_id"]]
        old_edof = old_by_config[old["edof_config_id"]]
        old_censored = any(
            _bool(old_mono, field) or _bool(old_edof, field)
            for field in ("dof50_far_censored", "dof50_near_censored", "peak_search_censored")
        )
        new_censored = any(
            _bool(config, field)
            for config in (new_mono, new_edof)
            for field in ("peak_search_censored", "dof50_far_censored", "dof50_near_censored")
        )
        points.append(
            {
                "x": _float(old, "dof50_width_d"),
                "y": _float(new, "delta_dof50_d"),
                "cornea": new["cornea_id"],
                "censored": old_censored or new_censored,
            }
        )

    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    for cornea, color in CORNEA_COLORS.items():
        exact = [point for point in points if point["cornea"] == cornea and not point["censored"]]
        censored = [point for point in points if point["cornea"] == cornea and point["censored"]]
        ax.scatter(
            [point["x"] for point in exact],
            [point["y"] for point in exact],
            s=35,
            color=color,
            label=cornea,
            alpha=0.9,
        )
        ax.scatter(
            [point["x"] for point in censored],
            [point["y"] for point in censored],
            s=48,
            facecolors="none",
            edgecolors=color,
            marker="o",
            linewidths=1.2,
        )
    values = [float(point["x"]) for point in points] + [float(point["y"]) for point in points]
    low = min(values)
    high = max(values)
    pad = max(0.05, 0.08 * (high - low))
    ax.plot([low - pad, high + pad], [low - pad, high + pad], color="#777777", linewidth=1.0)
    ax.axhline(0.0, color="#777777", linewidth=0.8)
    ax.axvline(0.0, color="#777777", linewidth=0.8)
    ax.set_xlim(low - pad, high + pad)
    ax.set_ylim(low - pad, high + pad)
    ax.set_xlabel("Original-window EDOF-MONO ΔDOF50 (D)")
    ax.set_ylabel("Extended-window EDOF-MONO ΔDOF50 (D)")
    ax.set_title("Supplementary Fig. S1 - Extended-window change across 48 matched pairs")
    ax.legend(title="Cornea", frameon=False, loc="best")
    _style_axes(ax)
    return _save_figure(fig, output_dir, "SUPPLEMENTAL_FIGURE_1_EXTENDED_WINDOW_DELTA_DOF50")


def _figure_two(
    common_rows: list[dict[str, str]],
    supplemental_pair_rows: list[dict[str, str]],
    output_dir: Path,
) -> list[Path]:
    by_pair: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in common_rows:
        by_pair[row["pair_key"]][row["optic_state"]] = row
    points: list[dict[str, object]] = []
    for pair in supplemental_pair_rows:
        members = by_pair[pair["pair_key"]]
        if set(members) != {"MONO", "EDOF"}:
            raise ValueError(f"common-threshold pair is incomplete: {pair['pair_key']}")
        mono = members["MONO"]
        edof = members["EDOF"]
        common_delta = _float(edof, "common_dof50_width_d") - _float(mono, "common_dof50_width_d")
        common_censored = any(
            _bool(member, field)
            for member in (mono, edof)
            for field in ("common_dof50_far_censored", "common_dof50_near_censored")
        )
        points.append(
            {
                "x": _float(pair, "delta_dof50_d"),
                "y": common_delta,
                "cornea": pair["cornea_id"],
                "censored": common_censored,
            }
        )

    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    for cornea, color in CORNEA_COLORS.items():
        for censored, marker, face in ((False, "o", color), (True, "o", "none")):
            selected = [
                point
                for point in points
                if point["cornea"] == cornea and bool(point["censored"]) is censored
            ]
            ax.scatter(
                [point["x"] for point in selected],
                [point["y"] for point in selected],
                s=35 if not censored else 48,
                color=color if not censored else None,
                facecolors=face,
                edgecolors=color,
                marker=marker,
                linewidths=1.2,
            )
    values = [float(point["x"]) for point in points] + [float(point["y"]) for point in points]
    low = min(values)
    high = max(values)
    pad = max(0.05, 0.08 * (high - low))
    ax.plot([low - pad, high + pad], [low - pad, high + pad], color="#777777", linewidth=1.0)
    ax.axhline(0.0, color="#777777", linewidth=0.8)
    ax.axvline(0.0, color="#777777", linewidth=0.8)
    ax.set_xlim(low - pad, high + pad)
    ax.set_ylim(low - pad, high + pad)
    ax.set_xlabel("Relative-threshold EDOF-MONO ΔDOF50 (D)")
    ax.set_ylabel("Common N0+MONO threshold EDOF-MONO ΔDOF50 (D)")
    ax.set_title("Supplementary Fig. S2 - Relative versus reference-anchored threshold")
    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor=color, label=cornea)
        for cornea, color in CORNEA_COLORS.items()
    ]
    legend.append(Line2D([0], [0], marker="o", color="#777777", markerfacecolor="none", label="Censored"))
    ax.legend(handles=legend, title="Cornea / status", frameon=False, loc="best")
    _style_axes(ax)
    return _save_figure(fig, output_dir, "SUPPLEMENTAL_FIGURE_2_THRESHOLD_ROBUSTNESS")


def _figure_three(
    main_rows: list[dict[str, str]],
    distance_rows: list[dict[str, str]],
    output_dir: Path,
) -> list[Path]:
    identity = {"base_id": "LB_AL2395", "platform_id": "WFS", "pupil_mm": "3.0", "cornea_id": "C0"}

    def selected(rows: list[dict[str, str]], state: str) -> list[dict[str, str]]:
        result = [
            row
            for row in rows
            if all(row[field] == value for field, value in identity.items())
            and row["optic_state"] == state
        ]
        if len(result) != 49:
            raise ValueError(f"representative strategy curve is not 49 points: {state}")
        return sorted(result, key=lambda row: _float(row, "defocus_retina_d" if "defocus_retina_d" in row else "defocus_d"), reverse=True)

    fig, ax = plt.subplots(figsize=(8.0, 5.8))
    for strategy, rows, field in (
        ("full_eye", main_rows, "mtfa"),
        ("distance_component_anchored", distance_rows, "mtfa"),
    ):
        for state in ("MONO", "EDOF"):
            data = selected(rows, state)
            x_field = "defocus_retina_d" if "defocus_retina_d" in data[0] else "defocus_d"
            color, linestyle = STRATEGY_STYLES[(strategy, state)]
            label = f"{strategy.replace('_', ' ')} {state}"
            ax.plot(
                [_float(row, x_field) for row in data],
                [_float(row, field) for row in data],
                color=color,
                linestyle=linestyle,
                linewidth=1.8,
                label=label,
            )
    ax.axvspan(-2.25, -1.25, color="#9a9a9a", alpha=0.13, label="-1.25 to -2.25 D")
    ax.axvline(-1.0, color="#777777", linewidth=0.8, linestyle=":")
    ax.axvline(1.0, color="#777777", linewidth=0.8, linestyle=":")
    ax.set_xlabel("Retina defocus (D)")
    ax.set_ylabel("MTFa")
    ax.set_title("Supplementary Fig. S3 - C0 calibration strategies\nLB / WFS / 3 mm representative pair")
    ax.legend(frameon=False, loc="upper right")
    _style_axes(ax)
    return _save_figure(fig, output_dir, "SUPPLEMENTAL_FIGURE_3_C0_CALIBRATION_STRATEGIES")


def _figure_four(did_rows: list[dict[str, str]], output_dir: Path) -> list[Path]:
    groups = sorted({(row["base_id"], row["pupil_mm"]) for row in did_rows})
    platforms = ("WFS", "RAD", "HOA")
    fig, axes = plt.subplots(4, 3, figsize=(12.0, 11.5), sharey=True)
    for row_index, (base, pupil) in enumerate(groups):
        for col_index, platform in enumerate(platforms):
            ax = axes[row_index, col_index]
            subset = [
                row
                for row in did_rows
                if row["base_id"] == base and row["pupil_mm"] == pupil and row["platform_id"] == platform
            ]
            for threshold, (color, marker) in THRESHOLD_STYLES.items():
                threshold_rows = [row for row in subset if row["threshold"] == threshold]
                for x_position, cornea in enumerate(("A0", "B0", "C0")):
                    row = next(item for item in threshold_rows if item["cornea_id"] == cornea)
                    status = row["bound_status"]
                    if status == "exact":
                        ax.scatter(x_position, _float(row, "delta_delta_dof_d"), color=color, marker=marker, s=28)
                    elif status == "lower_bound":
                        ax.scatter(
                            x_position,
                            _float(row, "delta_delta_dof_d"),
                            color=color,
                            marker="v",
                            s=34,
                            alpha=0.9,
                        )
                    else:
                        ax.scatter(
                            x_position,
                            _float(row, "delta_delta_dof_d"),
                            color=color,
                            marker="x",
                            s=38,
                            linewidths=1.2,
                        )
            ax.axhline(0.0, color="#777777", linewidth=0.7)
            ax.set_xticks(range(3), ("A0", "B0", "C0"))
            ax.set_title(f"{platform} | {base} | {pupil} mm", fontsize=9)
            ax.set_ylim(min(_float(row, "delta_delta_dof_d") for row in did_rows) - 0.1, max(_float(row, "delta_delta_dof_d") for row in did_rows) + 0.1)
            _style_axes(ax)
            if col_index == 0:
                ax.set_ylabel("ΔΔ DOF (D)")
            if row_index == len(groups) - 1:
                ax.set_xlabel("Cornea")
    legend = [
        Line2D([0], [0], marker=marker, color=color, linestyle="none", label=f"{int(float(threshold) * 100)}%")
        for threshold, (color, marker) in THRESHOLD_STYLES.items()
    ]
    legend.extend(
        [
            Line2D([0], [0], marker="o", color="#444444", linestyle="none", label="Exact"),
            Line2D([0], [0], marker="v", color="#444444", linestyle="none", label="Lower bound"),
            Line2D([0], [0], marker="x", color="#444444", linestyle="none", label="Indeterminate"),
        ]
    )
    fig.legend(handles=legend, loc="lower center", ncol=6, frameon=False, bbox_to_anchor=(0.5, 0.005))
    fig.suptitle("Supplementary Fig. S4 - Corneal-background modulation of EDOF effect", y=0.995)
    fig.tight_layout(rect=(0.0, 0.05, 1.0, 0.98))
    return _save_figure(fig, output_dir, "SUPPLEMENTAL_FIGURE_4_DID_COUPLING")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-r8-dir", type=Path, required=True)
    parser.add_argument("--experiment1-dir", type=Path, required=True)
    parser.add_argument("--experiment2-dir", type=Path, required=True)
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    old_dir = args.old_r8_dir.resolve()
    experiment1_dir = args.experiment1_dir.resolve()
    experiment2_dir = args.experiment2_dir.resolve()
    analysis_dir = args.analysis_dir.resolve()
    output_dir = args.output_dir.resolve()
    paths = {
        "old_config": old_dir / "MODEL_REVISION_R8_96_CONFIG_RESULTS.csv",
        "old_pair": old_dir / "MODEL_REVISION_R8_96_PAIRED_DELTAS.csv",
        "experiment1_config": experiment1_dir / "SUPPLEMENTAL_EXPERIMENT_1_CONFIG_RESULTS.csv",
        "experiment1_pair": analysis_dir / "SUPPLEMENTAL_PAIR_ANALYSIS.csv",
        "experiment1_through_focus": experiment1_dir / "SUPPLEMENTAL_EXPERIMENT_1_THROUGH_FOCUS.csv",
        "experiment2_through_focus": experiment2_dir / "SUPPLEMENTAL_EXPERIMENT_2_THROUGH_FOCUS.csv",
        "common_threshold": analysis_dir / "SUPPLEMENTAL_COMMON_THRESHOLD.csv",
        "did": analysis_dir / "SUPPLEMENTAL_DID.csv",
        "calibration_comparison": analysis_dir / "SUPPLEMENTAL_CALIBRATION_STRATEGY_COMPARISON.csv",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise SystemExit(f"missing required source files: {missing}")

    old_config = _read_csv(paths["old_config"])
    old_pair = _read_csv(paths["old_pair"])
    experiment1_config = _read_csv(paths["experiment1_config"])
    experiment1_pair = _read_csv(paths["experiment1_pair"])
    common_threshold = _read_csv(paths["common_threshold"])
    did = _read_csv(paths["did"])
    main_through_focus = _read_csv(paths["experiment1_through_focus"])
    distance_through_focus = _read_csv(paths["experiment2_through_focus"])
    calibration_comparison = _read_csv(paths["calibration_comparison"])
    if len(old_pair) != 48 or len(experiment1_pair) != 48:
        raise SystemExit("figure 1 requires exactly 48 old and 48 supplemental pairs")
    if len(common_threshold) != 96 or len(did) != 108 or len(calibration_comparison) != 12:
        raise SystemExit("figure sources do not have the prespecified row counts")

    generated: list[Path] = []
    generated.extend(_figure_one(old_config, old_pair, experiment1_config, experiment1_pair, output_dir))
    generated.extend(_figure_two(common_threshold, experiment1_pair, output_dir))
    generated.extend(_figure_three(main_through_focus, distance_through_focus, output_dir))
    generated.extend(_figure_four(did, output_dir))
    manifest = {
        "schema_version": 1,
        "figure_count": 4,
        "source_sha256": {name: _sha256(path) for name, path in paths.items()},
        "output_files": [
            {"path": str(path), "sha256": _sha256(path)} for path in generated
        ],
        "source_row_counts": {
            "old_pair": len(old_pair),
            "experiment1_config": len(experiment1_config),
            "supplemental_pair": len(experiment1_pair),
            "common_threshold": len(common_threshold),
            "did": len(did),
            "calibration_comparison": len(calibration_comparison),
            "experiment1_through_focus": len(main_through_focus),
            "experiment2_through_focus": len(distance_through_focus),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "SUPPLEMENTAL_FIGURE_MANIFEST.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
