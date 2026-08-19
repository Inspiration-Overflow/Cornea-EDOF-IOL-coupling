from __future__ import annotations

from dataclasses import replace

import pytest

from whole_eye_mvp.cornea_assets import (
    MAIN_CORNEA_SCAFFOLD,
    cornea_lock_eye_geometry,
    distance_corrected_front_radius_mm,
)
from whole_eye_mvp.cornea_zos import (
    CORNEA_DIAGNOSTIC_EPD_MM,
    DistanceCorneaMeasurements,
    validate_distance_cornea_measurements,
)
from whole_eye_mvp.domain import CURRENT_SCIENTIFIC_BASELINE_ID, ScientificBaseline


def measurement() -> DistanceCorneaMeasurements:
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    geometry = cornea_lock_eye_geometry(baseline)
    scaffold = MAIN_CORNEA_SCAFFOLD
    return DistanceCorneaMeasurements(
        wavelength_nm=scaffold.wavelength_nm,
        entrance_pupil_mm=CORNEA_DIAGNOSTIC_EPD_MM,
        front_radius_mm=distance_corrected_front_radius_mm(-3.0),
        front_conic=scaffold.front_conic,
        cornea_thickness_mm=scaffold.thickness_mm,
        back_radius_mm=scaffold.back_radius_mm,
        back_conic=scaffold.back_conic,
        cornea_index=scaffold.cornea_index,
        aqueous_index_after_cornea=scaffold.aqueous_index,
        post_cornea_to_stop_mm=geometry.post_cornea_to_stop_mm,
        stop_to_iol_ant_mm=geometry.stop_to_iol_ant_mm,
        post_cornea_to_iol_ant_mm=geometry.post_cornea_to_iol_ant_mm,
        iol_ant_to_image_mm=geometry.iol_ant_to_image_mm,
        axial_length_mm=geometry.axial_length_mm,
        surface_count=6,
        stop_surface=3,
    )


@pytest.mark.unit
def test_distance_cornea_readback_contract_accepts_expected_geometry() -> None:
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    assert validate_distance_cornea_measurements(measurement(), baseline) == ()


@pytest.mark.unit
def test_distance_cornea_readback_contract_reports_geometry_and_index_drift() -> None:
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    bad = replace(
        measurement(),
        cornea_thickness_mm=0.55,
        aqueous_index_after_cornea=1.35,
        axial_length_mm=24.1,
    )
    findings = validate_distance_cornea_measurements(bad, baseline)
    assert any("cornea_thickness_mm" in finding for finding in findings)
    assert any("aqueous_index_after_cornea" in finding for finding in findings)
    assert any("axial_length_mm" in finding for finding in findings)
