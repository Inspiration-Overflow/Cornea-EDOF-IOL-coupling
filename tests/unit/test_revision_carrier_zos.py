from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp.domain import ScientificBaseline
from whole_eye_mvp.revision_carrier_zos import (
    RevisionCarrierZosError,
    _prepare_cornea_geometry_for_base,
    _require_cornea_scaffold,
)


class _FakeSurface:
    def __init__(self, comment: str, thickness: float = 0.0) -> None:
        self.Comment = comment
        self.Thickness = thickness


class _FakeLde:
    def __init__(self, surfaces: tuple[_FakeSurface, ...]) -> None:
        self.NumberOfSurfaces = len(surfaces)
        self._surfaces = surfaces

    def GetSurfaceAt(self, number: int) -> _FakeSurface:
        return self._surfaces[number]


class _FakeSystem:
    def __init__(self, surfaces: tuple[_FakeSurface, ...]) -> None:
        self.LDE = _FakeLde(surfaces)
        self.loaded: list[str] = []

    def LoadFile(self, path: str, prompt: bool) -> None:
        self.loaded.append(path)


class _FakeSession:
    def __init__(self, surfaces: tuple[_FakeSurface, ...]) -> None:
        self.system = _FakeSystem(surfaces)


def _role_surfaces(post_role: str) -> tuple[_FakeSurface, ...]:
    return (
        _FakeSurface("OBJECT"),
        _FakeSurface("CORNEA_ANT_MODULE_REF"),
        _FakeSurface(post_role),
        _FakeSurface("STOP"),
        _FakeSurface("IOL_ANT_REF"),
        _FakeSurface("IMAGE_FIXED"),
    )


def _native_base_surfaces() -> tuple[_FakeSurface, ...]:
    surfaces = list(_role_surfaces("CORNEA_POST_REF"))
    surfaces[2].Thickness = 3.15
    surfaces[3].Thickness = 1.35
    return tuple(surfaces)


def test_scaffold_accepts_legacy_and_fixed_post_cornea_roles(tmp_path: Path) -> None:
    source = tmp_path / "base.zmx"
    source.write_text("VER 1", encoding="utf-16")
    for role in ("CORNEA_POST_REF", "CORNEA_POST_FIXED"):
        session = _FakeSession(_role_surfaces(role))
        _require_cornea_scaffold(session, source)  # type: ignore[arg-type]
        assert session.system.loaded == [str(source.resolve())]


def test_scaffold_rejects_unknown_post_cornea_role(tmp_path: Path) -> None:
    source = tmp_path / "base.zmx"
    source.write_text("VER 1", encoding="utf-16")
    session = _FakeSession(_role_surfaces("CORNEA_POST_REVISED"))
    with pytest.raises(RevisionCarrierZosError, match="surface 2 role mismatch"):
        _require_cornea_scaffold(session, source)  # type: ignore[arg-type]


def test_native_zero_thickness_reference_slot_uses_bare_axial_landmark() -> None:
    baseline = ScientificBaseline("TEST")
    session = _FakeSession(_native_base_surfaces())
    iol_to_retina = _prepare_cornea_geometry_for_base(  # type: ignore[arg-type]
        session,
        baseline,
        "LB_AL2395",
    )
    spec = next(
        spec for spec in baseline.base_specs if spec.base_id == "LB_AL2395"
    )
    assert iol_to_retina == pytest.approx(
        spec.axial_length_mm - spec.post_cornea_to_iol_ant_mm
    )
    assert session.system.LDE.GetSurfaceAt(4).Thickness == pytest.approx(iol_to_retina)


def test_positive_cornea_thickness_keeps_strict_landmark_math() -> None:
    baseline = ScientificBaseline("TEST")
    surfaces = list(_native_base_surfaces())
    surfaces[1].Thickness = 0.5
    session = _FakeSession(tuple(surfaces))
    iol_to_retina = _prepare_cornea_geometry_for_base(  # type: ignore[arg-type]
        session,
        baseline,
        "LB_AL2395",
    )
    spec = next(
        spec for spec in baseline.base_specs if spec.base_id == "LB_AL2395"
    )
    assert iol_to_retina == pytest.approx(
        spec.axial_length_mm - 0.5 - spec.post_cornea_to_iol_ant_mm
    )


def test_negative_cornea_thickness_is_rejected() -> None:
    surfaces = list(_native_base_surfaces())
    surfaces[1].Thickness = -0.1
    session = _FakeSession(tuple(surfaces))
    with pytest.raises(RevisionCarrierZosError, match="non-negative"):
        _prepare_cornea_geometry_for_base(  # type: ignore[arg-type]
            session,
            ScientificBaseline("TEST"),
            "LB_AL2395",
        )
