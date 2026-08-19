from __future__ import annotations

import math

import pytest

from whole_eye_mvp.domain import NOMINAL_MAIN_FFT_MTF_555_V2
from whole_eye_mvp.zos import (
    ZernikeStandardError,
    ZernikeStandardSettings,
    parse_zernike_standard_text,
)


@pytest.mark.unit
def test_zernike_settings_are_derived_from_fft_mtf_main_settings() -> None:
    zernike = ZernikeStandardSettings.from_analysis_settings(NOMINAL_MAIN_FFT_MTF_555_V2)

    assert zernike.sample_size == 32
    assert zernike.maximum_terms == 37
    assert zernike.reference_opd_to_vertex is False
    assert zernike.normalized_radius == 1.0


@pytest.mark.unit
def test_zernike_text_parser_converts_waves_and_uses_standard_term_groups() -> None:
    values = {term: 0.0 for term in range(1, 29)}
    values[7] = 0.1
    values[11] = 0.2
    values[22] = -0.4
    text = "\n".join(
        f"Z {term:3d}\t{value:.8f}\t:\tterm {term}" for term, value in values.items()
    )

    result = parse_zernike_standard_text(text, maximum_terms=28, wavelength_um=0.5)

    assert len(result.coefficients) == 28
    assert result.c40_um == pytest.approx(0.1)
    assert result.c60_um == pytest.approx(-0.2)
    assert result.hoa_n3_to_n6_rms_um == pytest.approx(
        0.5 * math.sqrt(0.1**2 + 0.2**2 + 0.4**2)
    )
    with pytest.raises(KeyError, match="Z0"):
        result.coefficient_waves(0)


@pytest.mark.unit
def test_zernike_text_parser_rejects_missing_duplicate_and_invalid_settings() -> None:
    complete = "\n".join(f"Z {term} 0.0 : term" for term in range(1, 29))
    with pytest.raises(ZernikeStandardError, match="missing"):
        parse_zernike_standard_text(
            complete.rsplit("\n", 1)[0], maximum_terms=28, wavelength_um=0.5
        )
    with pytest.raises(ZernikeStandardError, match="duplicate"):
        parse_zernike_standard_text(
            complete + "\nZ 28 0.0 : duplicate", maximum_terms=28, wavelength_um=0.5
        )
    with pytest.raises(ValueError):
        ZernikeStandardSettings(16).validate()
    with pytest.raises(ValueError):
        ZernikeStandardSettings(32, maximum_terms=22).validate()
