from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from whole_eye_mvp.zos import (
    ZosConnectionError,
    ZosEnvironmentError,
    ZosLicenseError,
    ZosModeError,
    ZosSessionAdapter,
    open_zos_session,
)
from whole_eye_mvp.zos.session import _find_first_file, _PythonNetBootstrapRegistry


@dataclass
class FakeApp:
    IsValidLicenseForAPI: bool = True
    LicenseStatus: str = "Premium"
    Mode: str = "Server"
    PrimarySystem: Any = None

    def __post_init__(self) -> None:
        if self.PrimarySystem is None:
            self.PrimarySystem = SimpleNamespace(LDE=object())


class FakeBackend:
    def __init__(self, app: FakeApp | None = None) -> None:
        self._zosapi = SimpleNamespace(name="fake-zosapi")
        self.app = app if app is not None else FakeApp()
        self.initialized_with: Path | None = None
        self.close_calls = 0
        self.raise_on_close = False

    @property
    def zosapi(self) -> Any:
        return self._zosapi

    def initialize(self, install_dir: Path) -> None:
        self.initialized_with = install_dir

    def create_application(self) -> FakeApp | None:
        return self.app

    def is_standalone_mode(self, app: FakeApp) -> bool:
        return app.Mode == "Server"

    def close_application(self, app: FakeApp) -> None:
        self.close_calls += 1
        if self.raise_on_close:
            raise RuntimeError("close failed")


@pytest.fixture
def install_dir(tmp_path: Path) -> Path:
    path = tmp_path / "OpticStudio"
    path.mkdir()
    return path


@pytest.mark.unit
def test_context_returns_primary_system_and_closes_once(install_dir: Path) -> None:
    backend = FakeBackend()
    adapter = ZosSessionAdapter(backend)

    with open_zos_session(install_dir, adapter=adapter) as session:
        assert session.app is backend.app
        assert session.system is backend.app.PrimarySystem
        assert session.zosapi is backend.zosapi
        assert session.closed is False

    assert session.closed is True
    assert backend.close_calls == 1

    session.close()
    assert backend.close_calls == 1


@pytest.mark.unit
def test_missing_install_directory_is_typed_environment_error(tmp_path: Path) -> None:
    adapter = ZosSessionAdapter(FakeBackend())

    with pytest.raises(ZosEnvironmentError):
        adapter.open(tmp_path / "missing")


@pytest.mark.unit
def test_license_failure_closes_before_raise(install_dir: Path) -> None:
    backend = FakeBackend(FakeApp(IsValidLicenseForAPI=False, LicenseStatus="Invalid"))
    adapter = ZosSessionAdapter(backend)

    with pytest.raises(ZosLicenseError, match="Invalid"):
        adapter.open(install_dir)

    assert backend.close_calls == 1


@pytest.mark.unit
def test_wrong_application_mode_closes_before_raise(install_dir: Path) -> None:
    backend = FakeBackend(FakeApp(Mode="Plugin"))
    adapter = ZosSessionAdapter(backend)

    with pytest.raises(ZosModeError, match="standalone/server"):
        adapter.open(install_dir)

    assert backend.close_calls == 1


@pytest.mark.unit
def test_missing_primary_system_closes_before_raise(install_dir: Path) -> None:
    app = FakeApp()
    app.PrimarySystem = None
    backend = FakeBackend(app)
    adapter = ZosSessionAdapter(backend)

    with pytest.raises(ZosConnectionError, match="PrimarySystem"):
        adapter.open(install_dir)

    assert backend.close_calls == 1


@pytest.mark.unit
def test_none_application_is_typed_connection_error(install_dir: Path) -> None:
    backend = FakeBackend()
    backend.app = None
    adapter = ZosSessionAdapter(backend)

    with pytest.raises(ZosConnectionError, match="no standalone application"):
        adapter.open(install_dir)

    assert backend.close_calls == 0


@pytest.mark.unit
def test_api_file_layout_prefers_modern_root_and_supports_legacy(tmp_path: Path) -> None:
    modern = tmp_path / "ZOSAPI_NetHelper.dll"
    legacy = tmp_path / "ZOS-API" / "Libraries" / "ZOSAPI_NetHelper.dll"
    legacy.parent.mkdir(parents=True)
    legacy.touch()

    assert _find_first_file(modern, legacy) == legacy
    modern.touch()
    assert _find_first_file(modern, legacy) == modern


@pytest.mark.unit
def test_missing_api_file_reports_every_checked_location(tmp_path: Path) -> None:
    first = tmp_path / "modern.dll"
    second = tmp_path / "legacy.dll"

    with pytest.raises(ZosEnvironmentError) as error:
        _find_first_file(first, second)

    assert str(first) in str(error.value)
    assert str(second) in str(error.value)


@pytest.mark.unit
def test_pythonnet_bootstrap_is_process_idempotent_and_rejects_install_switch(
    tmp_path: Path,
) -> None:
    first = tmp_path / "OpticStudio-A"
    second = tmp_path / "OpticStudio-B"
    first.mkdir()
    second.mkdir()
    registry = _PythonNetBootstrapRegistry()
    calls: list[Path] = []
    api = object()

    def loader(path: Path) -> object:
        calls.append(path)
        return api

    assert registry.get_or_initialize(first, loader) is api
    assert registry.get_or_initialize(first, loader) is api
    assert calls == [first.resolve()]

    with pytest.raises(ZosEnvironmentError, match="refusing to switch"):
        registry.get_or_initialize(second, loader)
    assert calls == [first.resolve()]
