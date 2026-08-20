from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .run72_analysis import BASE_IDS, CORNEA_IDS, PLATFORM_IDS, PLATFORM_LABELS, PUPIL_LABELS

MANUSCRIPT_FIGURE_SCHEMA_VERSION = 1
MANUSCRIPT_FIGURE_NAMES = (
    "MANUSCRIPT_FIGURE_1_DOF50_MATRIX.png",
    "MANUSCRIPT_FIGURE_2_MTFA0_MATRIX.png",
    "MANUSCRIPT_FIGURE_3_EXTENSION_QUALITY_TRADEOFF.png",
    "MANUSCRIPT_FIGURE_4_SELECTED_THROUGH_FOCUS.png",
    "MANUSCRIPT_FIGURE_5_HOA_MECHANISM.png",
)
SELECTED_COUPLINGS = (
    ("B0", "WFS", "B0 × WFS-like"),
    ("C0", "RAD", "C0 × RAD-like"),
    ("C0", "HOA", "C0 × HOA-like"),
)


class ManuscriptFigureError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ManuscriptFigureError(f"missing source CSV: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(row: Mapping[str, str], field: str) -> float:
    try:
        return float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ManuscriptFigureError(f"invalid numeric field {field}") from exc


def load_pair_rows(path: Path) -> tuple[dict[str, str], ...]:
    rows = _read_csv(path)
    if len(rows) != 36:
        raise ManuscriptFigureError(f"manuscript figures require exactly 36 pairs, got {len(rows)}")

    observed_factors = {
        (
            row.get("base_id", ""),
            row.get("cornea_id", ""),
            row.get("platform_id", ""),
            _float(row, "pupil_mm"),
        )
        for row in rows
    }
    expected_factors = {
        (base_id, cornea_id, platform_id, pupil_mm)
        for base_id in BASE_IDS
        for cornea_id in CORNEA_IDS
        for platform_id in PLATFORM_IDS
        for pupil_mm in (3.0, 5.0)
    }
    if observed_factors != expected_factors:
        raise ManuscriptFigureError("pair CSV does not contain the exact frozen 2×3×3×2 factor matrix")

    if len({row.get("pair_key", "") for row in rows}) != 36:
        raise ManuscriptFigureError("pair CSV contains duplicate or empty pair keys")
    return tuple(rows)


def pair_index(rows: Sequence[Mapping[str, str]]) -> dict[tuple[str, str, str, float], Mapping[str, str]]:
    index = {
        (
            row["base_id"],
            row["cornea_id"],
            row["platform_id"],
            float(row["pupil_mm"]),
        ): row
        for row in rows
    }
    if len(index) != 36:
        raise ManuscriptFigureError("pair index must contain exactly 36 factor-unique rows")
    return index


def load_through_focus(path: Path) -> dict[str, tuple[tuple[float, float], ...]]:
    rows = _read_csv(path)
    if len(rows) != 1080:
        raise ManuscriptFigureError(f"through-focus source must contain 1080 rows, got {len(rows)}")
    curves: dict[str, list[tuple[float, float]]] = {}
    for row in rows:
        config_id = row.get("config_id", "")
        if not config_id:
            raise ManuscriptFigureError("through-focus row has empty config_id")
        curves.setdefault(config_id, []).append(
            (_float(row, "defocus_retina_d"), _float(row, "mtfa"))
        )
    if len(curves) != 72:
        raise ManuscriptFigureError(f"through-focus source must contain 72 curves, got {len(curves)}")
    normalized: dict[str, tuple[tuple[float, float], ...]] = {}
    for config_id, points in curves.items():
        if len(points) != 15:
            raise ManuscriptFigureError(f"curve must contain 15 rows: {config_id}")
        normalized[config_id] = tuple(sorted(points))
    return normalized


def _bound_prefix(row: Mapping[str, str]) -> str:
    return {
        "exact": "",
        "lower_bound": "≥",
        "upper_bound": "≤",
        "indeterminate": "~",
    }.get(row.get("dof50_effect_status", ""), "?")


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _matrix(
    index: Mapping[tuple[str, str, str, float], Mapping[str, str]],
    *,
    base_id: str,
    pupil_mm: float,
    outcome: str,
) -> np.ndarray:
    return np.array(
        [
            [
                _float(index[(base_id, cornea_id, platform_id, pupil_mm)], outcome)
                for platform_id in PLATFORM_IDS
            ]
            for cornea_id in CORNEA_IDS
        ],
        dtype=float,
    )


def _figure_matrix(
    rows: Sequence[Mapping[str, str]],
    *,
    outcome: str,
    label: str,
    path: Path,
    dof_bounds: bool,
) -> None:
    index = pair_index(rows)
    strata = tuple((base_id, pupil_mm) for base_id in BASE_IDS for pupil_mm in (3.0, 5.0))
    matrices = [
        _matrix(index, base_id=base_id, pupil_mm=pupil_mm, outcome=outcome)
        for base_id, pupil_mm in strata
    ]
    global_min = min(float(matrix.min()) for matrix in matrices)
    global_max = max(float(matrix.max()) for matrix in matrices)

    fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.2), constrained_layout=True)
    image = None
    for ax, (base_id, pupil_mm), matrix in zip(axes.flat, strata, matrices, strict=True):
        image = ax.imshow(matrix, aspect="auto", vmin=global_min, vmax=global_max)
        ax.set_xticks(range(len(PLATFORM_IDS)), [PLATFORM_LABELS[item] for item in PLATFORM_IDS])
        ax.set_yticks(range(len(CORNEA_IDS)), CORNEA_IDS)
        ax.set_title(f"{base_id} · {PUPIL_LABELS[pupil_mm]}")
        ax.set_xlabel("EDoF mechanism surrogate")
        ax.set_ylabel("Corneal prototype")
        for row_i, cornea_id in enumerate(CORNEA_IDS):
            for col_i, platform_id in enumerate(PLATFORM_IDS):
                row = index[(base_id, cornea_id, platform_id, pupil_mm)]
                value = _float(row, outcome)
                prefix = _bound_prefix(row) if dof_bounds else ""
                ax.text(col_i, row_i, f"{prefix}{value:+.3f}", ha="center", va="center")
    if image is None:
        raise ManuscriptFigureError("matrix figure did not render any strata")
    fig.colorbar(image, ax=axes.ravel().tolist(), label=label, shrink=0.86)
    fig.suptitle(label)
    _save(fig, path)


def _figure_tradeoff(rows: Sequence[Mapping[str, str]], path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.3), constrained_layout=True)
    marker_by_platform = {"WFS": "o", "RAD": "s", "HOA": "^"}
    for ax, outcome, ylabel in (
        (axes[0], "delta_mtfa_at_zero_d", "ΔMTFa at 0 D"),
        (axes[1], "delta_tf_mtfa_mean", "ΔTF MTFa mean"),
    ):
        for platform_id in PLATFORM_IDS:
            selected = [row for row in rows if row["platform_id"] == platform_id]
            exact = [row for row in selected if row["dof50_effect_status"] == "exact"]
            limited = [row for row in selected if row["dof50_effect_status"] != "exact"]
            ax.scatter(
                [_float(row, "delta_dof50_width_d") for row in exact],
                [_float(row, outcome) for row in exact],
                marker=marker_by_platform[platform_id],
                label=PLATFORM_LABELS[platform_id],
            )
            if limited:
                ax.scatter(
                    [_float(row, "delta_dof50_width_d") for row in limited],
                    [_float(row, outcome) for row in limited],
                    marker="x",
                    label=f"{PLATFORM_LABELS[platform_id]} DOF bound",
                )
        ax.axhline(0.0, linewidth=0.8)
        ax.axvline(0.0, linewidth=0.8)
        ax.set_xlabel("ΔDOF50 (D), EDOF − MONO")
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8)
    axes[0].set_title("Fixed-focus quality")
    axes[1].set_title("Whole-window quality")
    fig.suptitle("Extension–quality trade-off")
    _save(fig, path)


def _figure_selected_through_focus(
    rows: Sequence[Mapping[str, str]],
    curves: Mapping[str, Sequence[tuple[float, float]]],
    path: Path,
) -> None:
    index = pair_index(rows)
    strata = tuple((base_id, pupil_mm) for base_id in BASE_IDS for pupil_mm in (3.0, 5.0))
    selected_curves: list[Sequence[tuple[float, float]]] = []
    for cornea_id, platform_id, _ in SELECTED_COUPLINGS:
        for base_id, pupil_mm in strata:
            row = index[(base_id, cornea_id, platform_id, pupil_mm)]
            selected_curves.extend((curves[row["mono_config_id"]], curves[row["edof_config_id"]]))
    y_values = [value for curve in selected_curves for _, value in curve]
    y_min, y_max = min(y_values), max(y_values)

    fig, axes = plt.subplots(3, 4, figsize=(15.0, 10.0), sharex=True, sharey=True, constrained_layout=True)
    for row_i, (cornea_id, platform_id, coupling_label) in enumerate(SELECTED_COUPLINGS):
        for col_i, (base_id, pupil_mm) in enumerate(strata):
            ax = axes[row_i, col_i]
            pair = index[(base_id, cornea_id, platform_id, pupil_mm)]
            mono = curves[pair["mono_config_id"]]
            edof = curves[pair["edof_config_id"]]
            ax.plot([x for x, _ in mono], [y for _, y in mono], marker="o", label="MONO")
            ax.plot([x for x, _ in edof], [y for _, y in edof], marker="o", label="EDOF")
            ax.axvline(0.0, linewidth=0.8)
            ax.set_ylim(y_min, y_max)
            suffixes: list[str] = []
            if pair["dof50_effect_status"] != "exact":
                suffixes.append(f"DOF {pair['dof50_effect_status']}")
            if pair.get("pair_peak_censored") == "True":
                suffixes.append("peak-window")
            suffix = f" · {', '.join(suffixes)}" if suffixes else ""
            ax.set_title(f"{base_id} · {PUPIL_LABELS[pupil_mm]}{suffix}", fontsize=9)
            if col_i == 0:
                ax.set_ylabel(f"{coupling_label}\nMTFa")
            if row_i == 2:
                ax.set_xlabel("Retinal defocus (D)")
            if row_i == 0 and col_i == 0:
                ax.legend(fontsize=8)
    fig.suptitle("Selected coupling through-focus MTFa")
    _save(fig, path)


def _figure_mechanism(rows: Sequence[Mapping[str, str]], path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.3), constrained_layout=True)

    marker_by_platform = {"WFS": "o", "RAD": "s", "HOA": "^"}
    for platform_id in PLATFORM_IDS:
        selected = [row for row in rows if row["platform_id"] == platform_id]
        axes[0].scatter(
            [_float(row, "delta_c40_um") for row in selected],
            [_float(row, "delta_c60_um") for row in selected],
            marker=marker_by_platform[platform_id],
            label=PLATFORM_LABELS[platform_id],
        )
    axes[0].axhline(0.0, linewidth=0.8)
    axes[0].axvline(0.0, linewidth=0.8)
    axes[0].set_xlabel("ΔC40 (µm)")
    axes[0].set_ylabel("ΔC60 (µm)")
    axes[0].set_title("Spherical-aberration mechanism map")
    axes[0].legend(fontsize=8)

    rad_epd5 = [
        row
        for row in rows
        if row["platform_id"] == "RAD" and abs(_float(row, "pupil_mm") - 5.0) < 1e-12
    ]
    positions = np.arange(len(CORNEA_IDS), dtype=float)
    offsets = {BASE_IDS[0]: -0.12, BASE_IDS[1]: 0.12}
    for base_id in BASE_IDS:
        by_cornea = {row["cornea_id"]: row for row in rad_epd5 if row["base_id"] == base_id}
        axes[1].scatter(
            [position + offsets[base_id] for position in positions],
            [_float(by_cornea[cornea_id], "delta_hoa_rms_um") for cornea_id in CORNEA_IDS],
            label=base_id,
        )
    axes[1].axhline(0.0, linewidth=0.8)
    axes[1].set_xticks(positions, CORNEA_IDS)
    axes[1].set_xlabel("Corneal prototype")
    axes[1].set_ylabel("ΔHOA RMS (µm)")
    axes[1].set_title("RAD-like EPD5: cornea-dependent HOA response")
    axes[1].legend(fontsize=8)

    fig.suptitle("Whole-eye HOA mechanism signatures")
    _save(fig, path)


def render_manuscript_figures(
    *,
    pair_csv: Path,
    through_focus_csv: Path,
    output_dir: Path,
) -> tuple[Path, ...]:
    rows = load_pair_rows(pair_csv)
    curves = load_through_focus(through_focus_csv)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = tuple(output_dir / name for name in MANUSCRIPT_FIGURE_NAMES)
    _figure_matrix(
        rows,
        outcome="delta_dof50_width_d",
        label="ΔDOF50 (D), EDOF − MONO",
        path=paths[0],
        dof_bounds=True,
    )
    _figure_matrix(
        rows,
        outcome="delta_mtfa_at_zero_d",
        label="ΔMTFa at 0 D, EDOF − MONO",
        path=paths[1],
        dof_bounds=False,
    )
    _figure_tradeoff(rows, paths[2])
    _figure_selected_through_focus(rows, curves, paths[3])
    _figure_mechanism(rows, paths[4])

    missing = [str(path) for path in paths if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise ManuscriptFigureError(f"manuscript figure generation failed: {missing}")
    return paths


def write_manuscript_figure_manifest(
    *,
    pair_csv: Path,
    through_focus_csv: Path,
    figure_paths: Sequence[Path],
    output_path: Path,
    renderer_commit: str,
) -> None:
    if tuple(path.name for path in figure_paths) != MANUSCRIPT_FIGURE_NAMES:
        raise ManuscriptFigureError("unexpected manuscript figure set")
    payload = {
        "schema_version": MANUSCRIPT_FIGURE_SCHEMA_VERSION,
        "phase": "MANUSCRIPT-PRESENTATION",
        "presentation_only": True,
        "scientific_values_changed": False,
        "opticstudio_used": False,
        "renderer_commit": renderer_commit,
        "source_files": {
            pair_csv.as_posix(): sha256_file(pair_csv),
            through_focus_csv.as_posix(): sha256_file(through_focus_csv),
        },
        "figure_count": len(figure_paths),
        "figures": {path.name: sha256_file(path) for path in figure_paths},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
