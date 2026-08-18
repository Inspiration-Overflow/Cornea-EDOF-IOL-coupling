from __future__ import annotations

from dataclasses import replace

import pytest

from whole_eye_mvp.carriers import CarrierKey, ProvisionalCarrier
from whole_eye_mvp.domain import PlatformId, ScientificBaseline
from whole_eye_mvp.standard_eye import (
    CORNEAL_SA_PUPIL_MM,
    CORNEA_BACK_CONIC,
    CORNEA_BACK_RADIUS_MM,
    CORNEA_FRONT_CONIC,
    CORNEA_FRONT_RADIUS_MM,
    CORNEA_INDEX,
    CORNEA_THICKNESS_MM,
    StandardEyeMeasurements,
    ZeroHoaReferenceRecord,
    corneal_paraxial_focus_from_post_mm,
    paraxial_iol_plane_distance_mm,
    standard_eye_construction,
    validate_standard_eye_measurements,
)


@pytest.mark.unit
def test_standard_eye_uses_liou_cornea_and_distinct_validation_apertures() -> None:
    spec = standard_eye_construction(ScientificBaseline("MVP_2026_v1"))
    assert spec.cornea_front_radius_mm == CORNEA_FRONT_RADIUS_MM == 7.77
    assert spec.cornea_front_conic == CORNEA_FRONT_CONIC == -0.18
    assert spec.cornea_back_radius_mm == CORNEA_BACK_RADIUS_MM == 6.40
    assert spec.cornea_back_conic == CORNEA_BACK_CONIC == -0.60
    assert spec.cornea_thickness_mm == CORNEA_THICKNESS_MM == 0.50
    assert spec.cornea_index == CORNEA_INDEX == 1.376
    assert spec.corneal_sa_pupil_mm == CORNEAL_SA_PUPIL_MM == 6.0
    assert spec.eye.aperture_mm == 3.0
    assert spec.eye.corneal_c40_um == pytest.approx(0.258)
    assert spec.eye.iol_footprint_mm == pytest.approx(5.15)
    assert spec.eye.wavelength_nm == pytest.approx(546.0)


@pytest.mark.unit
def test_paraxial_iol_plane_is_deterministic_start_for_real_footprint_gate() -> None:
    spec = standard_eye_construction(ScientificBaseline("MVP_2026_v1"))
    assert paraxial_iol_plane_distance_mm(spec) == pytest.approx(3.92355, abs=1e-4)
    assert corneal_paraxial_focus_from_post_mm(spec) == pytest.approx(31.06443, abs=1e-4)
    assert spec.iol_vertex_mm == pytest.approx(4.42355, abs=1e-4)
    assert spec.iol_to_image_mm > 0


@pytest.mark.unit
def test_standard_eye_measurements_enforce_6mm_c40_and_footprint_plus_3mm_calibration() -> None:
    spec = standard_eye_construction(ScientificBaseline("MVP_2026_v1"))
    measurements = StandardEyeMeasurements(
        wavelength_nm=546.0,
        calibration_aperture_mm=3.0,
        corneal_sa_pupil_mm=6.0,
        corneal_c40_um_6mm=0.258,
        iol_footprint_mm_6mm=5.15,
        cornea_front_radius_mm=7.77,
        cornea_front_conic=-0.18,
        cornea_back_radius_mm=6.40,
        cornea_back_conic=-0.60,
        cornea_thickness_mm=0.50,
        cornea_index=1.376,
        medium_index=1.336,
        iol_from_post_cornea_mm=spec.iol_from_post_cornea_mm,
        reference_axial_length_mm=23.950,
        field_x_deg=0.0,
        field_y_deg=0.0,
        surface_count=5,
        stop_surface=1,
    )
    assert validate_standard_eye_measurements(measurements, spec) == ()

    wrong = replace(measurements, calibration_aperture_mm=6.0)
    findings = validate_standard_eye_measurements(wrong, spec)
    assert any("calibration_aperture_mm" in finding for finding in findings)

    wrong = replace(measurements, corneal_c40_um_6mm=0.270)
    findings = validate_standard_eye_measurements(wrong, spec)
    assert any("corneal_c40_um_6mm" in finding for finding in findings)


@pytest.mark.unit
def test_zero_hoa_reference_preserves_carrier_identity_metadata() -> None:
    carrier = ProvisionalCarrier(
        key=CarrierKey("LB_AL2395", "A0", PlatformId.WFS),
        power_d=20.0,
        q=-1.2,
        q_source_power_d=20.0,
        r_ant_mm=12.0,
        r_post_mm=-12.0,
        center_thickness_mm=1.0,
        material="MODEL_N1460",
        iol_position_mm=4.5,
        achieved_sa_um=-0.20,
    )
    reference = ZeroHoaReferenceRecord.from_carrier(carrier)
    reference.validate_against(carrier)
    assert reference.power_d == carrier.power_d
    assert reference.optical_model == "ideal_paraxial_zero_hoa"

    other = replace(carrier, power_d=21.0, q_source_power_d=21.0)
    with pytest.raises(ValueError, match="preserve carrier"):
        reference.validate_against(other)
