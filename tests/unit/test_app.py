from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp import app
from whole_eye_mvp.app import (
    ActionDispatcher,
    ActionName,
    ActionRequest,
    ProgressEvent,
    WorkflowBusyError,
    WorkflowSet,
    compose_dispatcher,
)


def req(action=ActionName.BUILD):
    return ActionRequest(
        action,
        "C:/Program Files/OpticStudio",
        "project",
        candidate_id="B0.20",
        selection_reason="confirmed recommendation",
    )


@pytest.mark.unit
def test_action_success_emits_started_then_completed() -> None:
    events: list[ProgressEvent] = []
    dispatcher = ActionDispatcher(
        {
            ActionName.BUILD: lambda request, sink: sink(
                ProgressEvent(request.action, "progress", "half", "t", 1, 2)
            )
        }
    )
    dispatcher.submit(req(), events.append)
    assert [event.status for event in events] == ["started", "progress", "completed"]
    assert not dispatcher.busy


@pytest.mark.unit
def test_workflow_exception_emits_failed_and_no_completed() -> None:
    events = []

    def boom(request, sink):
        raise RuntimeError("bad")

    dispatcher = ActionDispatcher({ActionName.BUILD: boom})
    with pytest.raises(RuntimeError, match="bad"):
        dispatcher.submit(req(), events.append)
    assert [event.status for event in events] == ["started", "failed"]
    assert not dispatcher.busy


@pytest.mark.unit
def test_busy_second_action_is_rejected() -> None:
    events = []
    dispatcher = None

    def nested(request, sink):
        with pytest.raises(WorkflowBusyError):
            dispatcher.submit(req(), sink)

    dispatcher = ActionDispatcher({ActionName.BUILD: nested})
    dispatcher.submit(req(), events.append)
    assert events[-1].status == "completed"


@pytest.mark.unit
def test_event_sink_failure_does_not_leave_dispatcher_stuck_busy() -> None:
    dispatcher = ActionDispatcher({ActionName.BUILD: lambda request, sink: None})

    def broken_sink(event):
        raise RuntimeError("sink failed")

    with pytest.raises(RuntimeError, match="sink failed"):
        dispatcher.submit(req(), broken_sink)
    assert not dispatcher.busy


@pytest.mark.unit
def test_composition_root_registers_all_seven_mvp_actions() -> None:
    called = []

    def workflow(request, sink):
        called.append(request.action)

    workflows = WorkflowSet(*(workflow for _ in range(7)))
    dispatcher = compose_dispatcher(workflows)
    for action in ActionName:
        dispatcher.submit(req(action), lambda event: None)
    assert called == list(ActionName)


@pytest.mark.unit
def test_gui_module_has_no_raw_zosapi_import_and_requires_injected_submitter() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")
    assert "import ZOSAPI" not in source
    assert "import clr" not in source
    assert "customtkinter" in source
    assert "submitter: ActionSubmitter" in source
    assert "threaded_submitter" in source
    assert "queue.SimpleQueue" in source
