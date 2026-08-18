from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol


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
    candidate_id: str = ""
    selection_reason: str = ""


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


@dataclass(frozen=True, slots=True)
class WorkflowSet:
    build: Workflow
    validate: Workflow
    b0_scan: Workflow
    b0_lock: Workflow
    carriers: Workflow
    run72: Workflow
    rerun: Workflow


class ActionSubmitter(Protocol):
    def __call__(self, request: ActionRequest, event_sink: EventSink) -> None: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ActionDispatcher:
    """Single-action orchestration boundary independent from Tk and ZOS-API."""

    def __init__(self, workflows: Mapping[ActionName, Workflow]) -> None:
        self._workflows = dict(workflows)
        self._busy = False
        self._state_lock = threading.Lock()

    @property
    def busy(self) -> bool:
        with self._state_lock:
            return self._busy

    def submit(self, request: ActionRequest, event_sink: EventSink) -> None:
        with self._state_lock:
            if self._busy:
                raise WorkflowBusyError("another long action is already running")
            workflow = self._workflows.get(request.action)
            if workflow is None:
                raise KeyError(f"no workflow registered for {request.action}")
            self._busy = True
        try:
            event_sink(
                ProgressEvent(request.action, "started", f"{request.action} started", _now())
            )
            try:
                workflow(request, event_sink)
            except Exception as exc:
                event_sink(
                    ProgressEvent(
                        request.action,
                        "failed",
                        f"{type(exc).__name__}: {exc}",
                        _now(),
                    )
                )
                raise
            else:
                event_sink(
                    ProgressEvent(
                        request.action,
                        "completed",
                        f"{request.action} completed",
                        _now(),
                    )
                )
        finally:
            with self._state_lock:
                self._busy = False


def compose_dispatcher(workflows: WorkflowSet) -> ActionDispatcher:
    """Explicit composition root for the seven MVP user actions."""

    return ActionDispatcher(
        {
            ActionName.BUILD: workflows.build,
            ActionName.VALIDATE: workflows.validate,
            ActionName.B0_SCAN: workflows.b0_scan,
            ActionName.B0_LOCK: workflows.b0_lock,
            ActionName.CARRIERS: workflows.carriers,
            ActionName.RUN72: workflows.run72,
            ActionName.RERUN: workflows.rerun,
        }
    )


def inline_submitter(dispatcher: ActionDispatcher) -> ActionSubmitter:
    """Synchronous submitter for tests/CLI; do not use for long GUI actions."""

    return dispatcher.submit


def threaded_submitter(dispatcher: ActionDispatcher) -> ActionSubmitter:
    """Optional worker-thread submitter, enabled only after TDD-TEST-401 passes locally."""

    def submit(request: ActionRequest, event_sink: EventSink) -> None:
        def target() -> None:
            try:
                dispatcher.submit(request, event_sink)
            except WorkflowBusyError as exc:
                event_sink(
                    ProgressEvent(request.action, "rejected", str(exc), _now())
                )
            except Exception:  # noqa: BLE001 - dispatcher already records boundary failures
                # ActionDispatcher already emitted the typed failed event.
                return

        threading.Thread(target=target, name=f"whole-eye-{request.action}", daemon=True).start()

    return submit


def submit_action(
    dispatcher: ActionDispatcher,
    request: ActionRequest,
    event_sink: EventSink,
) -> None:
    dispatcher.submit(request, event_sink)


def launch_desktop_app(
    dispatcher: ActionDispatcher,
    *,
    submitter: ActionSubmitter,
) -> None:
    """Launch the minimal CustomTkinter shell; GUI never owns raw ZOS-API handles.

    The caller must explicitly choose an orchestration submitter after the local
    worker-thread gate.  This prevents silently hard-wiring an unvalidated ZOS-API
    threading assumption into the GUI.
    """

    import customtkinter as ctk

    root = ctk.CTk()
    root.title("Cornea × EDOF IOL MVP")
    root.geometry("900x700")

    install_var = ctk.StringVar(value="")
    project_var = ctk.StringVar(value=str(Path.cwd() / "project"))
    candidate_var = ctk.StringVar(value="")
    reason_var = ctk.StringVar(value="")
    status_var = ctk.StringVar(value="Idle")

    ctk.CTkLabel(root, text="OpticStudio install path").pack(
        anchor="w", padx=16, pady=(16, 2)
    )
    ctk.CTkEntry(root, textvariable=install_var, width=820).pack(padx=16, fill="x")
    ctk.CTkLabel(root, text="Project path").pack(anchor="w", padx=16, pady=(12, 2))
    ctk.CTkEntry(root, textvariable=project_var, width=820).pack(padx=16, fill="x")
    ctk.CTkLabel(root, text="B0 candidate ID (for Lock B0)").pack(
        anchor="w", padx=16, pady=(12, 2)
    )
    ctk.CTkEntry(root, textvariable=candidate_var, width=820).pack(padx=16, fill="x")
    ctk.CTkLabel(root, text="B0 selection / override reason").pack(
        anchor="w", padx=16, pady=(12, 2)
    )
    ctk.CTkEntry(root, textvariable=reason_var, width=820).pack(padx=16, fill="x")

    log = ctk.CTkTextbox(root, height=300)
    status = ctk.CTkLabel(root, textvariable=status_var)

    def apply_event(event: ProgressEvent) -> None:
        status_var.set(f"{event.action}: {event.status}")
        log.insert("end", f"{event.timestamp}  {event.message}\n")
        log.see("end")

    event_queue: queue.SimpleQueue[ProgressEvent] = queue.SimpleQueue()

    def sink(event: ProgressEvent) -> None:
        # Worker code never calls Tk.  It only enqueues immutable events.
        event_queue.put(event)

    def drain_events() -> None:
        while True:
            try:
                event = event_queue.get_nowait()
            except queue.Empty:
                break
            apply_event(event)
        root.after(50, drain_events)

    def run(action: ActionName) -> None:
        request = ActionRequest(
            action,
            install_var.get(),
            project_var.get(),
            candidate_id=candidate_var.get().strip(),
            selection_reason=reason_var.get().strip(),
        )
        try:
            submitter(request, sink)
        except Exception as exc:  # noqa: BLE001 - GUI boundary must display submitter failures
            status_var.set(f"Failed: {exc}")

    frame = ctk.CTkFrame(root)
    frame.pack(fill="x", padx=16, pady=16)
    buttons = [
        ("Build", ActionName.BUILD),
        ("Validate", ActionName.VALIDATE),
        ("B0 Scan", ActionName.B0_SCAN),
        ("Lock B0", ActionName.B0_LOCK),
        ("Build Carriers", ActionName.CARRIERS),
        ("Run 72", ActionName.RUN72),
        ("Rerun", ActionName.RERUN),
    ]
    for text, action in buttons:
        ctk.CTkButton(frame, text=text, command=lambda selected=action: run(selected)).pack(
            side="left", padx=4, pady=8
        )
    status.pack(anchor="w", padx=16)
    log.pack(fill="both", expand=True, padx=16, pady=(8, 16))
    root.after(50, drain_events)
    root.mainloop()
