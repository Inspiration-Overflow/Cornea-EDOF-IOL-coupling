from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable, Mapping, Protocol


class WorkflowBusyError(RuntimeError):
    pass


class ActionName(StrEnum):
    BUILD = "build"
    VALIDATE = "validate"
    B0_SCAN = "b0_scan"
    B0_LOCK = "b0_lock"
    CARRIERS = "carriers"
    RUN72 = "run72"
    RERUN = "rerun"


@dataclass(frozen=True, slots=True)
class ActionRequest:
    action: ActionName
    install_dir: str
    project_dir: str
    selected_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    action: ActionName
    status: str
    message: str
    timestamp: str
    completed: int = 0
    total: int = 0


class EventSink(Protocol):
    def __call__(self, event: ProgressEvent) -> None: ...


Workflow = Callable[[ActionRequest, EventSink], None]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ActionDispatcher:
    """Single-action orchestration boundary independent from Tk and ZOS-API."""

    def __init__(self, workflows: Mapping[ActionName, Workflow]) -> None:
        self._workflows = dict(workflows)
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    def submit(self, request: ActionRequest, event_sink: EventSink) -> None:
        if self._busy:
            raise WorkflowBusyError("another long action is already running")
        workflow = self._workflows.get(request.action)
        if workflow is None:
            raise KeyError(f"no workflow registered for {request.action}")
        self._busy = True
        event_sink(ProgressEvent(request.action, "started", f"{request.action} started", _now()))
        try:
            workflow(request, event_sink)
        except Exception as exc:
            event_sink(ProgressEvent(request.action, "failed", f"{type(exc).__name__}: {exc}", _now()))
            raise
        else:
            event_sink(ProgressEvent(request.action, "completed", f"{request.action} completed", _now()))
        finally:
            self._busy = False


def submit_action(dispatcher: ActionDispatcher, request: ActionRequest, event_sink: EventSink) -> None:
    dispatcher.submit(request, event_sink)


def launch_desktop_app(dispatcher: ActionDispatcher) -> None:
    """Launch the minimal CustomTkinter shell; imports GUI dependency lazily."""
    import customtkinter as ctk

    root = ctk.CTk()
    root.title("Cornea × EDOF IOL MVP")
    root.geometry("900x620")

    install_var = ctk.StringVar(value="")
    project_var = ctk.StringVar(value=str(Path.cwd() / "project"))
    status_var = ctk.StringVar(value="Idle")

    ctk.CTkLabel(root, text="OpticStudio install path").pack(anchor="w", padx=16, pady=(16, 2))
    ctk.CTkEntry(root, textvariable=install_var, width=820).pack(padx=16, fill="x")
    ctk.CTkLabel(root, text="Project path").pack(anchor="w", padx=16, pady=(12, 2))
    ctk.CTkEntry(root, textvariable=project_var, width=820).pack(padx=16, fill="x")

    log = ctk.CTkTextbox(root, height=280)
    status = ctk.CTkLabel(root, textvariable=status_var)

    def sink(event: ProgressEvent) -> None:
        status_var.set(f"{event.action}: {event.status}")
        log.insert("end", f"{event.timestamp}  {event.message}\n")
        log.see("end")

    def run(action: ActionName) -> None:
        request = ActionRequest(action, install_var.get(), project_var.get())
        try:
            dispatcher.submit(request, sink)
        except Exception as exc:
            status_var.set(f"Failed: {exc}")

    frame = ctk.CTkFrame(root)
    frame.pack(fill="x", padx=16, pady=16)
    buttons = [
        ("Build", ActionName.BUILD), ("Validate", ActionName.VALIDATE),
        ("B0 Scan", ActionName.B0_SCAN), ("Lock B0", ActionName.B0_LOCK),
        ("Build Carriers", ActionName.CARRIERS), ("Run 72", ActionName.RUN72),
        ("Rerun", ActionName.RERUN),
    ]
    for text, action in buttons:
        ctk.CTkButton(frame, text=text, command=lambda a=action: run(a)).pack(side="left", padx=4, pady=8)
    status.pack(anchor="w", padx=16)
    log.pack(fill="both", expand=True, padx=16, pady=(8, 16))
    root.mainloop()
