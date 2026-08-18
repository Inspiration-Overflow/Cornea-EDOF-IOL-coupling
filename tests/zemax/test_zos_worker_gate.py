from __future__ import annotations

import os
import queue
import threading
from pathlib import Path
from typing import Any

import pytest

from whole_eye_mvp.zos import open_zos_session

INSTALL_ENV = "WHOLE_EYE_ZOS_INSTALL_DIR"


def _install_dir() -> Path:
    value = os.environ.get(INSTALL_ENV)
    if not value:
        pytest.skip(f"Set {INSTALL_ENV} on a configured OpticStudio workstation.")
    return Path(value)


@pytest.mark.zemax
def test_session_opens_primary_system_and_closes() -> None:
    install_dir = _install_dir()

    with open_zos_session(install_dir) as session:
        assert session.system is not None
        assert session.system.LDE is not None


@pytest.mark.zemax
def test_repeated_sessions_reuse_process_bootstrap_without_native_failure() -> None:
    install_dir = _install_dir()

    for _ in range(10):
        with open_zos_session(install_dir) as session:
            session.system.New(False)
            assert session.system.LDE.NumberOfSurfaces >= 2


@pytest.mark.zemax
def test_worker_thread_session_risk_gate() -> None:
    install_dir = _install_dir()
    outcomes: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            with open_zos_session(install_dir) as session:
                session.system.New(False)
                surface_count = session.system.LDE.NumberOfSurfaces
                outcomes.put(("ok", surface_count))
        except BaseException as exc:  # noqa: BLE001 - boundary test must report CLR failures
            outcomes.put(("error", exc))

    thread = threading.Thread(target=worker, name="zos-worker-risk-gate", daemon=True)
    thread.start()
    thread.join(timeout=60.0)

    assert not thread.is_alive(), "ZOS-API worker-thread gate hung for more than 60 seconds"
    status, payload = outcomes.get_nowait()
    if status == "error":
        raise payload
    assert isinstance(payload, int)
    assert payload >= 2
