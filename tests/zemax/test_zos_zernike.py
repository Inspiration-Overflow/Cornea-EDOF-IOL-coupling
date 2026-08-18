from __future__ import annotations

import math
import os
from pathlib import Path

import pytest

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
def test_zernike_standard_returns_complete_finite_coefficients() -> None:
    with open_zos_session(_install_dir()) as session:
        configured_reference = os.environ.get(REFERENCE_ENV)
        reference = (
            Path(configured_reference)
            if configured_reference
            else Path(str(session.app.SamplesDir)) / REFERENCE_RELATIVE_PATH
        )
        assert reference.is_file(), f"OpticStudio reference file is missing: {reference}"
        session.system.LoadFile(str(reference), False)

        result = ZernikeStandardRunner(session.system, session.zosapi).run(
            ZernikeStandardSettings(32, maximum_terms=37)
        )

        assert len(result.coefficients) == 37
        assert result.wavelength_um > 0
        assert all(math.isfinite(item.value_waves) for item in result.coefficients)
        assert math.isfinite(result.c40_um)
        assert math.isfinite(result.c60_um)
        assert math.isfinite(result.hoa_n3_to_n6_rms_um)
