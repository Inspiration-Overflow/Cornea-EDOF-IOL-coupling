from __future__ import annotations

import pytest

from whole_eye_mvp.carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from whole_eye_mvp.residual_payload import (
    RadialResidualCandidate,
    build_hoa_residual_candidate,
    build_rad_residual_candidate,
    build_wfs_residual_candidate,
    normalization_prefix,
    opd_to_surface_sag_um,
)
from whole_eye_mvp.residual_profiles import fit_piston_and_global_defocus


def _assert_normalized(candidate: RadialResidualCandidate) -> None:
    radii, _, normalized = normalization_prefix(candidate)
    fit = fit_piston_and_global_defocus(radii, normalized)
    assert fit.piston_um == pytest.approx(0.0, abs=1.0e-12)
    assert fit.global_defocus_d == pytest.approx(0.0, abs=1.0e-12)


def test_opd_surface_conversion_uses_propagation_index_step() -> None:
    opd_um = 0.124
    anterior = opd_to_surface_sag_um(opd_um, surface_role="anterior")
    posterior = opd_to_surface_sag_um(opd_um, surface_role="posterior")
    assert anterior == pytest.approx(1.0)
    assert posterior == pytest.approx(-1.0)
    assert CONTROLLED_IOL_CARRIER_546_V1.refractive_index - 1.336 == pytest.approx(0.124)


def test_wfs_candidate_has_low_order_removed_before_surface_conversion() -> None:
    candidate = build_wfs_residual_candidate()
    candidate.validate()
    assert candidate.platform_id == "WFS"
    assert candidate.surface_role == "anterior"
    assert len(candidate.radii_mm) == 601
    assert candidate.radii_mm[-1] == pytest.approx(3.0)
    _assert_normalized(candidate)
    assert max(candidate.surface_sag_um) - min(candidate.surface_sag_um) > 0.5


def test_rad_candidate_has_low_order_removed_and_lives_on_posterior_surface() -> None:
    candidate = build_rad_residual_candidate()
    candidate.validate()
    assert candidate.platform_id == "RAD"
    assert candidate.surface_role == "posterior"
    assert len(candidate.radii_mm) == 601
    assert candidate.radii_mm[-1] == pytest.approx(3.0)
    _assert_normalized(candidate)
    assert max(candidate.raw_opd_um) - min(candidate.raw_opd_um) > 0.5


def test_hoa_candidate_is_frozen_and_keeps_same_low_order_contract() -> None:
    candidate = build_hoa_residual_candidate()
    candidate.validate()
    assert candidate.platform_id == "HOA"
    assert candidate.surface_role == "anterior"
    assert candidate.radii_mm[-1] == pytest.approx(3.0)
    _assert_normalized(candidate)
    assert max(candidate.raw_opd_um) - min(candidate.raw_opd_um) > 1.0
