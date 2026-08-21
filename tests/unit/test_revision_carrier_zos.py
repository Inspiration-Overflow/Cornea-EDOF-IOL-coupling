from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp.revision_carrier_zos import (
    RevisionCarrierZosError,
    _require_cornea_scaffold,
)


class _FakeSurface:
    def __init__(self, comment: str) -> None:
        self.Comment = comment


class _FakeLde:
    def __init__(self, comments: tuple[str, ...]) -> None:
        self.NumberOfSurfaces = len(comments)
        self._surfaces = tuple(_FakeSurface(comment) for comment in comments)

    def GetSurfaceAt(self, number: int) -> _FakeSurface:
        return self._surfaces[number]


class _FakeSystem:
    def __init__(self, comments: tuple[str, ...]) -> None:
        self.LDE = _FakeLde(comments)
        self.loaded: list[str] = []

    def LoadFile(self, path: str, prompt: bool) -> None:
        self.loaded.append(path)


class _FakeSession:
    def __init__(self, comments: tuple[str, ...]) -> None:
        self.system = _FakeSystem(comments)


def _base_comments(post_role: str) -> tuple[str, ...]:
    return (
        "OBJECT",
        "CORNEA_ANT_MODULE_REF",
        post_role,
        "STOP",
        "IOL_ANT_REF",
        "IMAGE_FIXED",
    )


def test_scaffold_accepts_legacy_and_fixed_post_cornea_roles(tmp_path: Path) -> None:
    source = tmp_path / "base.zmx"
    source.write_text("VER 1", encoding="utf-16")
    for role in ("CORNEA_POST_REF", "CORNEA_POST_FIXED"):
        session = _FakeSession(_base_comments(role))
        _require_cornea_scaffold(session, source)  # type: ignore[arg-type]
        assert session.system.loaded == [str(source.resolve())]


def test_scaffold_rejects_unknown_post_cornea_role(tmp_path: Path) -> None:
    source = tmp_path / "base.zmx"
    source.write_text("VER 1", encoding="utf-16")
    session = _FakeSession(_base_comments("CORNEA_POST_REVISED"))
    with pytest.raises(RevisionCarrierZosError, match="surface 2 role mismatch"):
        _require_cornea_scaffold(session, source)  # type: ignore[arg-type]
