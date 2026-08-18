from __future__ import annotations

import math
import os
from pathlib import Path

import pytest

from whole_eye_mvp.domain import NOMINAL_MAIN_555_V1
from whole_eye_mvp.zos import HuygensPsfRunner, HuygensPsfSettings, open_zos_session

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
def test_huygens_psf_returns_finite_positive_grid_at_frozen_nominal_settings() -> None:
    with open_zos_session(_install_dir()) as session:
        configured_reference = os.environ.get(REFERENCE_ENV)
        reference = (
            Path(configured_reference)
            if configured_reference
            else Path(str(session.app.SamplesDir)) / REFERENCE_RELATIVE_PATH
        )
        assert reference.is_file(), f"OpticStudio reference file is missing: {reference}"
        session.system.LoadFile(str(reference), False)

        settings = HuygensPsfSettings.from_analysis_settings(NOMINAL_MAIN_555_V1)
        grid = HuygensPsfRunner(session.system, session.zosapi).run(settings)

        assert grid.shape == (NOMINAL_MAIN_555_V1.huygens_image_sampling,) * 2
        assert grid.dx == pytest.approx(NOMINAL_MAIN_555_V1.huygens_image_delta_um)
        assert grid.dy == pytest.approx(NOMINAL_MAIN_555_V1.huygens_image_delta_um)
        assert grid.total_energy > 0
        assert all(math.isfinite(value) for row in grid.values for value in row)
