from __future__ import annotations

from pathlib import Path

import pytest

import whole_eye_mvp.app as app
from whole_eye_mvp.app import ActionDispatcher, ActionName, ActionRequest, ProgressEvent, WorkflowBusyError


def req(action=ActionName.BUILD):
    return ActionRequest(action, 'C:/Program Files/OpticStudio', 'project')


@pytest.mark.unit
def test_action_success_emits_started_then_completed() -> None:
    events: list[ProgressEvent] = []
    dispatcher = ActionDispatcher({ActionName.BUILD: lambda request, sink: sink(ProgressEvent(request.action,'progress','half','t',1,2))})
    dispatcher.submit(req(), events.append)
    assert [e.status for e in events] == ['started','progress','completed']
    assert not dispatcher.busy


@pytest.mark.unit
def test_workflow_exception_emits_failed_and_no_completed() -> None:
    events = []
    def boom(request, sink):
        raise RuntimeError('bad')
    dispatcher = ActionDispatcher({ActionName.BUILD: boom})
    with pytest.raises(RuntimeError, match='bad'):
        dispatcher.submit(req(), events.append)
    assert [e.status for e in events] == ['started','failed']
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
    assert events[-1].status == 'completed'


@pytest.mark.unit
def test_gui_module_has_no_raw_zosapi_import() -> None:
    source = Path(app.__file__).read_text(encoding='utf-8')
    assert 'import ZOSAPI' not in source
    assert 'import clr' not in source
    assert 'customtkinter' in source
