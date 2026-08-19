from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .residual_payload import RadialResidualCandidate
from .residual_profiles import fit_piston_and_global_defocus
from .zos import ZosSession

GRID_SAG_HALF_WIDTH_MM = 3.05
GRID_SAG_STEP_MM = 0.01
GRID_SAG_SIZE = 611
GRID_SAG_INTERPOLATION = 1  # linear; avoids spline overshoot near WFS transitions
READBACK_STEP_MM = 0.025
READBACK_RADIUS_MM = 2.575


class GridSagResidualError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GridSagImportResult:
    platform_id: str
    surface_number: int
    surface_role: str
    dat_path: str
    grid_size: int
    grid_step_mm: float
    grid_half_width_mm: float
    interpolation: int
    radius_mm: float
    conic: float
    import_comment: str


@dataclass(frozen=True, slots=True)
class ResidualReadbackResult:
    platform_id: str
    surface_number: int
    radii_mm: tuple[float, ...]
    residual_sag_um: tuple[float, ...]
    residual_opd_um: tuple[float, ...]
    target_opd_um: tuple[float, ...]
    measured_piston_um: float
    measured_global_defocus_d: float
    max_abs_opd_error_um: float


def _interp_radial(values_r: tuple[float, ...], values_y: tuple[float, ...], r_mm: float) -> float:
    if len(values_r) != len(values_y) or len(values_r) < 2:
        raise ValueError("radial interpolation requires equal arrays of length >=2")
    radius = float(r_mm)
    if not math.isfinite(radius) or radius < 0:
        raise ValueError("radial coordinate must be finite and non-negative")
    if radius <= values_r[0]:
        return float(values_y[0])
    if radius >= values_r[-1]:
        return float(values_y[-1])
    step = values_r[1] - values_r[0]
    if step <= 0 or any(
        not math.isclose(values_r[index] - values_r[index - 1], step, rel_tol=0.0, abs_tol=1e-12)
        for index in range(2, len(values_r))
    ):
        raise ValueError("residual radial grid must be uniformly spaced")
    left = min(int(radius / step), len(values_r) - 2)
    r0 = values_r[left]
    r1 = values_r[left + 1]
    fraction = (radius - r0) / (r1 - r0)
    return float(values_y[left] + fraction * (values_y[left + 1] - values_y[left]))


def write_grid_sag_dat(candidate: RadialResidualCandidate, destination: str | Path) -> Path:
    candidate.validate()
    if GRID_SAG_SIZE < 5 or GRID_SAG_SIZE % 2 == 0:
        raise ValueError("TASK-007 Grid Sag size must be odd and >=5")
    expected = 2.0 * GRID_SAG_HALF_WIDTH_MM / (GRID_SAG_SIZE - 1)
    if not math.isclose(expected, GRID_SAG_STEP_MM, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("TASK-007 Grid Sag size/half-width/step are inconsistent")

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as handle:
        handle.write(
            f"{GRID_SAG_SIZE} {GRID_SAG_SIZE} {GRID_SAG_STEP_MM:.12g} "
            f"{GRID_SAG_STEP_MM:.12g} 0 0 0\n"
        )
        for iy in range(GRID_SAG_SIZE):
            y = -GRID_SAG_HALF_WIDTH_MM + iy * GRID_SAG_STEP_MM
            for ix in range(GRID_SAG_SIZE):
                x = -GRID_SAG_HALF_WIDTH_MM + ix * GRID_SAG_STEP_MM
                radius = math.hypot(x, y)
                sag_um = _interp_radial(candidate.radii_mm, candidate.surface_sag_um, radius)
                # Imported sag is an additive departure from the Grid Sag base R/Q surface.
                handle.write(f"{sag_um / 1000.0:.15g} 0 0 0 0\n")
    return path


def _grid_sag_interpolation_cell(session: ZosSession, surface: Any) -> tuple[Any, str]:
    columns = session.zosapi.Editors.LDE.SurfaceColumn
    candidates = []
    for name in ("Par0", "Par1"):
        column = getattr(columns, name, None)
        if column is None:
            continue
        cell = surface.GetSurfaceCell(column)
        header = str(getattr(cell, "Header", "") or "").strip()
        candidates.append((name, header))
        if "interpol" in header.lower():
            return cell, header
    raise GridSagResidualError(f"Grid Sag interpolation cell not found; candidates={candidates!r}")


def _surface_number(surface_count: int, surface_role: str) -> int:
    if surface_role not in {"anterior", "posterior"}:
        raise ValueError("surface role must be anterior or posterior")
    if surface_count == 7:  # actual-eye carrier
        return 4 if surface_role == "anterior" else 5
    if surface_count == 6:  # standard-eye carrier
        return 3 if surface_role == "anterior" else 4
    raise GridSagResidualError(
        f"Grid Sag residual requires a 6-surface standard-eye or 7-surface actual-eye carrier; got {surface_count}"
    )


def apply_grid_sag_residual(
    session: ZosSession,
    carrier_path: str | Path,
    candidate: RadialResidualCandidate,
    dat_path: str | Path,
    destination: str | Path,
) -> GridSagImportResult:
    candidate.validate()
    source = Path(carrier_path)
    data = Path(dat_path)
    if not source.is_file():
        raise GridSagResidualError(f"carrier input is missing: {source}")
    if not data.is_file():
        raise GridSagResidualError(f"Grid Sag DAT is missing: {data}")

    session.system.LoadFile(str(source.resolve()), False)
    lde = session.system.LDE
    surface_number = _surface_number(int(lde.NumberOfSurfaces), candidate.surface_role)
    surface = lde.GetSurfaceAt(surface_number)
    radius = float(surface.Radius)
    conic = float(surface.Conic)
    material = str(surface.Material)
    thickness = float(surface.Thickness)

    type_settings = surface.GetSurfaceTypeSettings(session.zosapi.Editors.LDE.SurfaceType.GridSag)
    surface.ChangeType(type_settings)
    surface.Radius = radius
    surface.Conic = conic
    surface.Material = material
    surface.Thickness = thickness
    cell, _header = _grid_sag_interpolation_cell(session, surface)
    try:
        cell.IntegerValue = GRID_SAG_INTERPOLATION
    except Exception:  # noqa: BLE001 - installed cell may expose DoubleValue only
        cell.DoubleValue = float(GRID_SAG_INTERPOLATION)

    importer = getattr(surface, "ImportData", None)
    import_file = getattr(importer, "ImportDataFile", None)
    if not callable(import_file):
        raise GridSagResidualError("installed Grid Sag surface exposes no ImportData.ImportDataFile")
    result = import_file(str(data.resolve()))
    result_text = str(result)
    if result_text and result_text.lower() not in {"success", "none"} and "success" not in result_text.lower():
        raise GridSagResidualError(f"Grid Sag import returned unexpected status: {result_text}")

    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    session.system.SaveAs(str(output.resolve()))
    session.system.LoadFile(str(output.resolve()), False)
    replay = session.system.LDE.GetSurfaceAt(surface_number)
    replay_type = str(getattr(replay, "TypeName", "") or "")
    if (
        "grid" not in replay_type.lower()
        and "grid" not in str(replay.GetType()).lower()
        and not hasattr(replay, "ImportData")
    ):
        raise GridSagResidualError("saved residual surface did not replay as Grid Sag")

    return GridSagImportResult(
        platform_id=candidate.platform_id,
        surface_number=surface_number,
        surface_role=candidate.surface_role,
        dat_path=str(data.resolve()),
        grid_size=GRID_SAG_SIZE,
        grid_step_mm=GRID_SAG_STEP_MM,
        grid_half_width_mm=GRID_SAG_HALF_WIDTH_MM,
        interpolation=GRID_SAG_INTERPOLATION,
        radius_mm=float(replay.Radius),
        conic=float(replay.Conic),
        import_comment=str(replay.Comment),
    )


def _ssag_mm(session: ZosSession, surface_number: int, x_mm: float, y_mm: float = 0.0) -> float:
    operand_type = getattr(session.zosapi.Editors.MFE.MeritOperandType, "SSAG", None)
    if operand_type is None:
        raise GridSagResidualError("installed MeritOperandType exposes no SSAG member")
    get_value = getattr(session.system.MFE, "GetOperandValue", None)
    if not callable(get_value):
        raise GridSagResidualError("installed MFE exposes no GetOperandValue")
    value = float(get_value(operand_type, int(surface_number), 0, float(x_mm), float(y_mm), 0, 0, 0, 0))
    if not math.isfinite(value):
        raise GridSagResidualError(f"SSAG returned non-finite sag at r={x_mm:g} mm")
    return value


def readback_residual_low_order(
    session: ZosSession,
    mono_path: str | Path,
    edof_path: str | Path,
    candidate: RadialResidualCandidate,
) -> ResidualReadbackResult:
    candidate.validate()
    sample_count = round(READBACK_RADIUS_MM / READBACK_STEP_MM) + 1
    radii = tuple(index * READBACK_STEP_MM for index in range(sample_count))
    if not math.isclose(radii[-1], READBACK_RADIUS_MM, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("readback radius must align with readback step")

    mono = Path(mono_path)
    edof = Path(edof_path)
    if not mono.is_file() or not edof.is_file():
        raise GridSagResidualError("MONO/EDOF readback file is missing")

    session.system.LoadFile(str(mono.resolve()), False)
    mono_count = int(session.system.LDE.NumberOfSurfaces)
    surface_number = _surface_number(mono_count, candidate.surface_role)
    mono_sag = tuple(_ssag_mm(session, surface_number, radius) for radius in radii)
    session.system.LoadFile(str(edof.resolve()), False)
    if int(session.system.LDE.NumberOfSurfaces) != mono_count:
        raise GridSagResidualError("MONO/EDOF surface counts differ")
    edof_sag = tuple(_ssag_mm(session, surface_number, radius) for radius in radii)
    residual_sag_um = tuple(
        (right - left) * 1000.0 for left, right in zip(mono_sag, edof_sag, strict=True)
    )

    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    if candidate.surface_role == "anterior":
        index_step = scaffold.refractive_index - scaffold.surrounding_index
    else:
        index_step = scaffold.surrounding_index - scaffold.refractive_index
    residual_opd = tuple(value * index_step for value in residual_sag_um)
    target_opd = tuple(
        _interp_radial(candidate.radii_mm, candidate.normalized_opd_um, radius)
        for radius in radii
    )
    low_order = fit_piston_and_global_defocus(radii, residual_opd)
    max_error = max(
        abs(actual - target) for actual, target in zip(residual_opd, target_opd, strict=True)
    )
    return ResidualReadbackResult(
        platform_id=candidate.platform_id,
        surface_number=surface_number,
        radii_mm=radii,
        residual_sag_um=residual_sag_um,
        residual_opd_um=residual_opd,
        target_opd_um=target_opd,
        measured_piston_um=low_order.piston_um,
        measured_global_defocus_d=low_order.global_defocus_d,
        max_abs_opd_error_um=max_error,
    )
