from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import whole_eye_mvp.revision_r4_zos as r4


class _StopAfterEdofSourceCheck(RuntimeError):
    pass


def test_r4_binary4_edof_is_built_from_analytical_carrier(monkeypatch, tmp_path) -> None:
    """EDoF must get a fresh Standard->Binary4 conversion, not Binary4->Binary4."""

    analytical = SimpleNamespace(
        radius_ant_mm=12.0,
        radius_post_mm=-12.0,
        q_ant=0.0,
        q_post=0.0,
    )
    fit = SimpleNamespace(platform_id="WFS")

    monkeypatch.setattr(
        r4,
        "build_r4_analytical_carrier",
        lambda *args, **kwargs: analytical,
    )
    monkeypatch.setattr(
        r4,
        "fit_r4_mechanism",
        lambda *args, **kwargs: fit,
    )
    monkeypatch.setattr(
        r4,
        "build_r4_binary4_mono",
        lambda *args, **kwargs: SimpleNamespace(),
    )

    expected_source = tmp_path / "R4_ANALYTICAL_MONO_WFS.zmx"

    def _capture_edof_source(session, source_path, fit_arg, destination):
        assert Path(source_path) == expected_source
        assert fit_arg is fit
        raise _StopAfterEdofSourceCheck

    monkeypatch.setattr(r4, "build_r4_binary4_edof", _capture_edof_source)

    with pytest.raises(_StopAfterEdofSourceCheck):
        r4.run_r4_platform_pilot(
            object(),
            tmp_path / "STD_IOL_EYE_2024.zmx",
            "WFS",
            object(),
            tmp_path,
        )
