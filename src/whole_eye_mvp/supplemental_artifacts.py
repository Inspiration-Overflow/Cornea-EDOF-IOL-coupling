"""CSV artifact helpers for the prespecified supplemental analysis."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .supplemental_experiments import (
    SupplementalExperimentError,
    SupplementalRow,
    derive_config_metrics,
)


def _field(row: dict[str, str], *names: str, default: str | None = None) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    if default is not None:
        return default
    raise SupplementalExperimentError(f"missing through-focus field; accepted names: {names}")


def annotate_config_csv_with_original_window_mean(
    config_csv: Path,
    through_focus_csv: Path,
) -> int:
    """Add the original +0.50 to -3.00 D MTFa mean to every config row."""

    config_path = Path(config_csv).resolve()
    through_focus_path = Path(through_focus_csv).resolve()
    with config_path.open("r", encoding="utf-8-sig", newline="") as handle:
        config_rows = list(csv.DictReader(handle))
    with through_focus_path.open("r", encoding="utf-8-sig", newline="") as handle:
        through_focus_rows = list(csv.DictReader(handle))
    if not config_rows or not through_focus_rows:
        raise SupplementalExperimentError("config and through-focus CSVs must be non-empty")

    grouped: dict[str, list[SupplementalRow]] = defaultdict(list)
    for row in through_focus_rows:
        grouped[_field(row, "config_id")].append(
            SupplementalRow(
                config_id=_field(row, "config_id"),
                pair_key=_field(row, "pair_key", default="") if "pair_key" in row else "",
                base_id=_field(row, "base_id", default="") if "base_id" in row else "",
                cornea_id=_field(row, "cornea_id", default="") if "cornea_id" in row else "",
                platform_id=_field(row, "platform_id", default="") if "platform_id" in row else "",
                pupil_mm=float(_field(row, "pupil_mm", default="3.0") if "pupil_mm" in row else "3.0"),
                optic_state=_field(row, "optic_state", default="MONO") if "optic_state" in row else "MONO",
                defocus_d=float(_field(row, "defocus_d", "defocus_retina_d")),
                mtfa=float(_field(row, "mtfa", "mtfa_0_60_cpd")),
                mtf30_cpd=float(_field(row, "mtf30_cpd", "mtf30", "mtfa30_cpd")),
            )
        )

    fields = list(config_rows[0])
    if "tf_mtfa_mean_original_window" not in fields:
        fields.append("tf_mtfa_mean_original_window")
    for row in config_rows:
        config_id = _field(row, "config_id")
        points = grouped.get(config_id)
        if points is None:
            raise SupplementalExperimentError(
                f"missing through-focus rows for config: {config_id}"
            )
        row["tf_mtfa_mean_original_window"] = format(
            derive_config_metrics(tuple(points)).tf_mtfa_mean_original_window,
            ".17g",
        )
    with config_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(config_rows)
    return len(config_rows)
