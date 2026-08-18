from __future__ import annotations

import os
from pathlib import Path

import pytest

from whole_eye_mvp.zos import Binary4Zone, SequentialEditor, open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"


def _install_dir() -> Path:
    value = os.environ.get(INSTALL_ENV)
    if not value:
        pytest.skip(f"Set {INSTALL_ENV} on a configured OpticStudio workstation.")
    return Path(value)


@pytest.mark.zemax
def test_surface_specific_parameter_mappings_round_trip_without_save() -> None:
    with open_zos_session(_install_dir()) as session:
        editor = SequentialEditor(session.system, session.zosapi)
        editor.new_system()
        columns = session.zosapi.Editors.LDE.SurfaceColumn

        binary = editor.configure_binary4(
            1,
            (
                Binary4Zone(1.5, 7.8, -0.2, aspheric_terms=(1e-4, 2e-6)),
                Binary4Zone(3.25, 7.8, -0.2, aspheric_terms=(3e-4, 4e-6)),
            ),
        )
        assert binary.GetSurfaceCell(columns.Par1).IntegerValue == 2
        assert binary.GetSurfaceCell(columns.Par2).IntegerValue == 2
        assert binary.GetSurfaceCell(columns.Par13).DoubleValue == pytest.approx(1.5)
        assert binary.GetSurfaceCell(columns.Par17).DoubleValue == pytest.approx(1e-4)
        assert binary.GetSurfaceCell(columns.Par19).DoubleValue == pytest.approx(3.25)
        assert binary.GetSurfaceCell(columns.Par23).DoubleValue == pytest.approx(3e-4)

        even = editor.configure_even_asphere(1, {2: 1e-5, 4: 2e-7, 16: 3e-12})
        assert even.GetSurfaceCell(columns.Par1).DoubleValue == pytest.approx(1e-5)
        assert even.GetSurfaceCell(columns.Par2).DoubleValue == pytest.approx(2e-7)
        assert even.GetSurfaceCell(columns.Par8).DoubleValue == pytest.approx(3e-12)

        coordinate_break = editor.configure_coordinate_break(
            1,
            decenter_x_mm=0.1,
            decenter_y_mm=-0.2,
            tilt_x_deg=1.0,
            tilt_y_deg=-2.0,
            tilt_z_deg=3.0,
            order=1,
        )
        assert coordinate_break.GetSurfaceCell(columns.Par1).DoubleValue == pytest.approx(0.1)
        assert coordinate_break.GetSurfaceCell(columns.Par5).DoubleValue == pytest.approx(3.0)
        assert coordinate_break.GetSurfaceCell(columns.Par6).IntegerValue == 1
