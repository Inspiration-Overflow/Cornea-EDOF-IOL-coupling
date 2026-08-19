from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .residual_profiles import (
    LowOrderFit,
    RAD_OPTIC_RADIUS_MM,
    RESIDUAL_NORMALIZATION_RADIUS_MM,
    RESIDUAL_SAMPLE_STEP_MM,
    fit_piston_and_global_defocus,
    hoa_raw_opd_um,
    rad_raw_opd_um,
    sample_radial_profile,
    wfs_raw_opd_um,
)


@dataclass(frozen=True)
class RadialResidualCandidate:
    platform_id: str
    surface_role: str
    radii_mm: tuple[float, ...]
    raw_opd_um: tuple[float, ...]
    normalized_opd_um: tuple[float, ...]
    surface_sag_um: tuple[float, ...]
    removed_low_order: LowOrderFit
    normalization_radius_mm: float
    optic_radius_mm: float
    sample_step_mm: float

    def validate(self) -> None:
        count = len(self.radii_mm)
        if count < 3:
            raise ValueError("residual candidate requires at least three radial samples")
        if not (
            len(self.raw_opd_um)
            == len(self.normalized_opd_um)
            == len(self.surface_sag_um)
            == count
        ):
            raise ValueError("residual candidate sample arrays must have equal length")
        if self.radii_mm[0] != 0.0:
            raise ValueError("residual radial samples must start on axis")
        if not math.isclose(
            self.radii_mm[-1], self.optic_radius_mm, rel_tol=0.0, abs_tol=1.0e-12
        ):
            raise ValueError("residual radial samples must cover the full optic radius")
        if not 0.0 < self.normalization_radius_mm <= self.optic_radius_mm:
            raise ValueError("residual normalization radius must lie inside the optic")
        if self.surface_role not in {"anterior", "posterior"}:
            raise ValueError("residual surface role must be anterior or posterior")
        for values in (self.raw_opd_um, self.normalized_opd_um, self.surface_sag_um):
            if not all(math.isfinite(value) for value in values):
                raise ValueError("residual candidate samples must be finite")


def opd_to_surface_sag_um(opd_um: float, *, surface_role: str) -> float:
    """First-order OPD→surface-sag conversion for the controlled carrier.

    The sign follows the index step in the direction of propagation. Final acceptance
    still requires real OpticStudio ray-trace/readback; this conversion is only the
    deterministic starting payload for that calibration.
    """

    scaffold = CONTROLLED_IOL_CARRIER_546_V1
    if surface_role == "anterior":
        index_step = scaffold.refractive_index - scaffold.surrounding_index
    elif surface_role == "posterior":
        index_step = scaffold.surrounding_index - scaffold.refractive_index
    else:
        raise ValueError("surface role must be anterior or posterior")
    if index_step == 0.0:
        raise ValueError("surface index step must be non-zero")
    return float(opd_um) / index_step


def normalization_prefix(candidate: RadialResidualCandidate) -> tuple[tuple[float, ...], ...]:
    """Return radii/raw/normalized samples inside the frozen low-order fit footprint."""

    end_index = round(candidate.normalization_radius_mm / candidate.sample_step_mm)
    if not math.isclose(
        end_index * candidate.sample_step_mm,
        candidate.normalization_radius_mm,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("normalization radius must align with the radial sample grid")
    stop = end_index + 1
    return (
        candidate.radii_mm[:stop],
        candidate.raw_opd_um[:stop],
        candidate.normalized_opd_um[:stop],
    )


def _candidate_from_opd_profile(
    *,
    platform_id: str,
    surface_role: str,
    raw_profile: Callable[[float], float],
) -> RadialResidualCandidate:
    radii, raw_opd = sample_radial_profile(
        raw_profile,
        radius_max_mm=RAD_OPTIC_RADIUS_MM,
        step_mm=RESIDUAL_SAMPLE_STEP_MM,
    )
    normalization_stop = round(RESIDUAL_NORMALIZATION_RADIUS_MM / RESIDUAL_SAMPLE_STEP_MM) + 1
    norm_radii = radii[:normalization_stop]
    norm_raw = raw_opd[:normalization_stop]
    removed = fit_piston_and_global_defocus(norm_radii, norm_raw)
    normalized_opd = tuple(
        value - removed.piston_um - 0.5 * removed.global_defocus_d * radius**2
        for radius, value in zip(radii, raw_opd, strict=True)
    )
    surface_sag = tuple(
        opd_to_surface_sag_um(value, surface_role=surface_role) for value in normalized_opd
    )
    candidate = RadialResidualCandidate(
        platform_id=platform_id,
        surface_role=surface_role,
        radii_mm=radii,
        raw_opd_um=raw_opd,
        normalized_opd_um=normalized_opd,
        surface_sag_um=surface_sag,
        removed_low_order=removed,
        normalization_radius_mm=RESIDUAL_NORMALIZATION_RADIUS_MM,
        optic_radius_mm=RAD_OPTIC_RADIUS_MM,
        sample_step_mm=RESIDUAL_SAMPLE_STEP_MM,
    )
    candidate.validate()
    return candidate


def build_wfs_residual_candidate() -> RadialResidualCandidate:
    return _candidate_from_opd_profile(
        platform_id="WFS",
        surface_role="anterior",
        raw_profile=wfs_raw_opd_um,
    )


def build_rad_residual_candidate() -> RadialResidualCandidate:
    return _candidate_from_opd_profile(
        platform_id="RAD",
        surface_role="posterior",
        raw_profile=rad_raw_opd_um,
    )


def build_hoa_residual_candidate() -> RadialResidualCandidate:
    return _candidate_from_opd_profile(
        platform_id="HOA",
        surface_role="anterior",
        raw_profile=hoa_raw_opd_um,
    )
