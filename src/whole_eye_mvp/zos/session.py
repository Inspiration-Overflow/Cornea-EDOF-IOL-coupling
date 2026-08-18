"""Standalone ZOS-API lifecycle boundary.

The public entry point is :func:`open_zos_session`.  Importing this module does not
load Python.NET or any OpticStudio DLL.  The external runtime is loaded lazily when
a real session is opened so pure unit tests remain independent of OpticStudio.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol, Self

from .errors import (
    ZosCloseError,
    ZosConnectionError,
    ZosEnvironmentError,
    ZosInitializationError,
    ZosLicenseError,
    ZosModeError,
    ZosSessionError,
)


def _find_first_file(*candidates: Path) -> Path:
    """Return the first installed API file from an ordered layout list."""

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    checked = ", ".join(str(candidate) for candidate in candidates)
    raise ZosEnvironmentError(f"Missing ZOS-API file; checked: {checked}")


class ZosBackend(Protocol):
    """Small test seam around the external Python.NET/ZOS-API runtime."""

    @property
    def zosapi(self) -> Any: ...

    def initialize(self, install_dir: Path) -> None: ...

    def create_application(self) -> Any: ...

    def is_standalone_mode(self, app: Any) -> bool: ...

    def close_application(self, app: Any) -> None: ...


@dataclass(slots=True)
class ZosSession:
    """Handles owned by one standalone OpticStudio session.

    A session owns exactly one standalone application.  ``close`` is idempotent so
    cleanup remains safe when an exception is raised during a workflow.
    """

    app: Any
    zosapi: Any
    system: Any
    _backend: ZosBackend = field(repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    @property
    def closed(self) -> bool:
        """Whether the application has already been closed by this session."""

        return self._closed

    def close(self) -> None:
        """Close the owned OpticStudio application once."""

        if self._closed:
            return
        try:
            self._backend.close_application(self.app)
        except Exception as exc:  # pragma: no cover - exercised through fake backend
            raise ZosCloseError("OpticStudio failed to close cleanly.") from exc
        finally:
            self._closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.close()
        return False


class PythonNetZosBackend:
    """Real standalone backend implemented with Python.NET and ZOS-API."""

    def __init__(self) -> None:
        self._zosapi: Any | None = None
        self._connection: Any | None = None

    @property
    def zosapi(self) -> Any:
        if self._zosapi is None:
            raise ZosInitializationError("ZOS-API has not been initialized.")
        return self._zosapi

    def initialize(self, install_dir: Path) -> None:
        helper = _find_first_file(
            install_dir / "ZOSAPI_NetHelper.dll",
            install_dir / "ZOS-API" / "Libraries" / "ZOSAPI_NetHelper.dll",
        )

        try:
            clr = importlib.import_module("clr")
        except ImportError as exc:
            raise ZosEnvironmentError(
                "Python.NET is not importable; install/sync the project environment first."
            ) from exc

        try:
            clr.AddReference(str(helper))
            nethelper = importlib.import_module("ZOSAPI_NetHelper")
            initializer = nethelper.ZOSAPI_Initializer
            initialized = bool(initializer.Initialize(str(install_dir)))
        except ZosSessionError:
            raise
        except Exception as exc:
            raise ZosInitializationError("Failed to initialize ZOSAPI_NetHelper.") from exc

        if not initialized:
            raise ZosInitializationError(
                f"ZOSAPI_NetHelper could not initialize OpticStudio at {install_dir}."
            )

        try:
            zemax_dir = Path(str(initializer.GetZemaxDirectory()))
            interfaces = _find_first_file(
                zemax_dir / "ZOSAPI_Interfaces.dll",
                install_dir / "ZOSAPI_Interfaces.dll",
            )
            api = _find_first_file(
                zemax_dir / "ZOSAPI.dll",
                install_dir / "ZOSAPI.dll",
            )
            clr.AddReference(str(interfaces))
            clr.AddReference(str(api))
            self._zosapi = importlib.import_module("ZOSAPI")
        except ZosSessionError:
            raise
        except Exception as exc:
            raise ZosInitializationError("Failed to load ZOSAPI assemblies.") from exc

    def create_application(self) -> Any:
        try:
            self._connection = self.zosapi.ZOSAPI_Connection()
            return self._connection.CreateNewApplication()
        except Exception as exc:
            raise ZosConnectionError("Failed to create a standalone OpticStudio application.") from exc

    def is_standalone_mode(self, app: Any) -> bool:
        return bool(app.Mode == self.zosapi.ZOSAPI_Mode.Server)

    def close_application(self, app: Any) -> None:
        app.CloseApplication()


class ZosSessionAdapter:
    """Open and validate one standalone ZOS-API session."""

    def __init__(self, backend: ZosBackend | None = None) -> None:
        self._backend = backend or PythonNetZosBackend()

    def open(self, install_dir: str | Path) -> ZosSession:
        install_path = Path(install_dir).expanduser()
        if not install_path.is_dir():
            raise ZosEnvironmentError(f"OpticStudio install directory does not exist: {install_path}")

        self._backend.initialize(install_path)

        app: Any | None = None
        try:
            app = self._backend.create_application()
            if app is None:
                raise ZosConnectionError("ZOS-API returned no standalone application.")

            if not bool(app.IsValidLicenseForAPI):
                status = getattr(app, "LicenseStatus", "unknown")
                raise ZosLicenseError(f"OpticStudio license is not valid for ZOS-API: {status}")

            if not self._backend.is_standalone_mode(app):
                mode = getattr(app, "Mode", "unknown")
                raise ZosModeError(
                    f"Expected standalone/server ZOS-API mode, received: {mode}"
                )

            system = app.PrimarySystem
            if system is None:
                raise ZosConnectionError("Standalone application returned no PrimarySystem.")

            return ZosSession(
                app=app,
                zosapi=self._backend.zosapi,
                system=system,
                _backend=self._backend,
            )
        except Exception as exc:
            if app is not None:
                try:
                    self._backend.close_application(app)
                except Exception as close_exc:
                    if isinstance(exc, ZosSessionError):
                        exc.add_note(f"Cleanup also failed: {close_exc!r}")
                    else:
                        raise ZosCloseError(
                            "OpticStudio initialization failed and cleanup also failed."
                        ) from close_exc

            if isinstance(exc, ZosSessionError):
                raise
            raise ZosConnectionError("Unexpected failure while opening ZOS-API session.") from exc


def open_zos_session(
    install_dir: str | Path,
    *,
    adapter: ZosSessionAdapter | None = None,
) -> ZosSession:
    """Open a validated standalone OpticStudio session.

    The optional adapter exists for deterministic unit testing.  Production callers
    normally pass only ``install_dir`` and use the returned object as a context
    manager.
    """

    return (adapter or ZosSessionAdapter()).open(install_dir)
