from __future__ import annotations

import math
import os
from pathlib import Path

import pytest

from whole_eye_mvp.domain import NOMINAL_MAIN_555_V1
from whole_eye_mvp.zos import (
    ZernikeStandardRunner,
    ZernikeStandardSettings,
    open_zos_session,
)

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"
REFERENCE_ENV = "WHOLE_EYE_ZOS_REFERENCE_FILE"
REFERENCE_RELATIVE_PATH = Path(
    "Sequential/Image Simulation/Example 4, a diffraction limited system.ZMX"
)


def _install_dir() -> Path:
    value = os.environ.get(INSTALL_ENV)
    if not value:
        pytest.skip(f"Set {INSTALL_ENV} on a configured OpticStudio workstation.")
    return Path(value)


@pytest.mark.zemax
def test_zernike_standard_returns_complete_finite_coefficients_at_frozen_settings() -> None:
    with open_zos_session(_install_dir()) as session:
        configured_reference = os.environ.get(REFERENCE_ENV)
        reference = (
            Path(configured_reference)
            if configured_reference
            else Path(str(session.app.SamplesDir)) / REFERENCE_RELATIVE_PATH
        )
        assert reference.is_file(), f"OpticStudio reference file is missing: {reference}"
        session.system.LoadFile(str(reference), False)

        settings = ZernikeStandardSettings.from_analysis_settings(NOMINAL_MAIN_555_V1)
        result = ZernikeStandardRunner(session.system, session.zosapi).run(settings)

        assert len(result.coefficients) == NOMINAL_MAIN_555_V1.zernike_maximum_terms
        assert result.wavelength_um > 0
        assert all(math.isfinite(item.value_waves) for item in result.coefficients)
        assert math.isfinite(result.c40_um)
        assert math.isfinite(result.c60_um)
        assert math.isfinite(result.hoa_n3_to_n6_rms_um)
