from __future__ import annotations

import math

import pytest

from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline
from whole_eye_mvp.task014_vertex_corrected_cornea import (
    TASK014_A0_ID,
    TASK014_B0_ID,
    TASK014_C0_ID,
    TASK014_LEGACY_DIRECT_TREATMENT_D,
    TASK014_RX_CONTRACT,
    TASK014_VERTEX_DISTANCE_MM,
    cornea_to_spectacle_plane_d,
    spectacle_to_cornea_plane_d,
    task014_cornea_prescriptions,
    task014_prescription_snapshot,
)


def _baseline() -> ScientificBaseline:
    return ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)


def test_vertex_conversion_minus_3d_at_12mm() -> None:
    value = spectacle_to_cornea_plane_d(-3.0, 12.0)
    assert value == pytest.approx(-2.8957528957528957, abs=1e-12)
    assert cornea_to_spectacle_plane_d(value, 12.0) == pytest.approx(-3.0, abs=1e-12)


def test_task014_contract_is_frozen_and_less_minus_than_legacy() -> None:
    TASK014_RX_CONTRACT.validate()
    assert TASK014_RX_CONTRACT.vertex_distance_mm == TASK014_VERTEX_DISTANCE_MM
    assert TASK014_RX_CONTRACT.preoperative_spectacle_sphere_d == -3.0
    assert TASK014_RX_CONTRACT.corneal_plane_distance_treatment_d > -3.0
    assert TASK014_RX_CONTRACT.legacy_direct_treatment_delta_d == pytest.approx(
        0.1042471042471043,
        abs=1e-12,
    )


def test_task014_does_not_mutate_frozen_baseline_treatment() -> None:
    baseline = _baseline()
    assert {float(spec.treatment_d) for spec in baseline.cornea_specs} == {
        TASK014_LEGACY_DIRECT_TREATMENT_D
    }

    prescriptions = task014_cornea_prescriptions(baseline)
    assert tuple(item.candidate_id for item in prescriptions) == (
        TASK014_A0_ID,
        TASK014_B0_ID,
        TASK014_C0_ID,
    )
    assert all(
        item.treatment_d
        == pytest.approx(TASK014_RX_CONTRACT.corneal_plane_distance_treatment_d, abs=1e-12)
        for item in prescriptions
    )
    assert {float(spec.treatment_d) for spec in baseline.cornea_specs} == {
        TASK014_LEGACY_DIRECT_TREATMENT_D
    }


def test_task014_preserves_a_b_c_modulation_targets() -> None:
    a, b, c = task014_cornea_prescriptions(_baseline())
    assert a.target_delta_c40_um == pytest.approx(0.13)
    assert b.target_delta_c40_um == pytest.approx(0.20)
    assert c.near_diameter_mm == pytest.approx(3.0)
    assert c.add_rx_d == pytest.approx(1.75)
    assert c.transition_width_mm == pytest.approx(0.75)


def test_task014_snapshot_has_expected_distance_baseline() -> None:
    snapshot = task014_prescription_snapshot(_baseline())
    assert snapshot["reference_cornea_equivalent_power_d"] == pytest.approx(
        42.251148573823,
        abs=1e-12,
    )
    assert snapshot["vertex_corrected_distance_cornea_power_d"] == pytest.approx(
        39.35539567807011,
        abs=1e-12,
    )
    assert snapshot["vertex_corrected_distance_front_radius_mm"] == pytest.approx(
        8.263362674864794,
        abs=1e-12,
    )
    assert math.isfinite(float(snapshot["legacy_to_vertex_corrected_delta_d"]))


def test_vertex_conversion_rejects_negative_vertex_distance() -> None:
    with pytest.raises(ValueError):
        spectacle_to_cornea_plane_d(-3.0, -1.0)
