# Purpose: Prove shell submission, Auto coalescing and cancellation transitions.
# Map: feature_routes/run_controller_selected_workspace_state
# Tests: this file
from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.test_run_controller_unit import _RunHostStub, _run_controller


def _setup(*, auto=True):
    host = _RunHostStub()
    wid = host.model.active_workspace.workspace_id
    nodes = [
        host.model.add_node(wid, "data.number_slider", name, x, 0)
        for name, x in (("A", 0), ("B", 200))
    ]
    controller = _run_controller(host)
    controller.set_auto_run_enabled(auto)
    return host, controller, wid, nodes


def _edit(host, controller, node, value):
    workspace = host.model.active_workspace
    before = workspace.capture_snapshot()
    host.model.set_node_property(workspace.workspace_id, node.node_id, "value", value)
    assert controller.invalidate_solution_for_graph_change(
        workspace.workspace_id,
        before_snapshot=before,
        after_snapshot=workspace.capture_snapshot(),
    )


def _turn(host):
    callbacks, host.next_turn_callbacks = host.next_turn_callbacks, []
    for callback in callbacks:
        callback()


def test_auto_uses_latest_edit_snapshot_and_unions_exact_targets_before_turn():
    from ea_node_editor.ui.shell.controllers import run_controller as module

    host, controller, wid, (first, second) = _setup()
    with patch.object(
        module, "build_runtime_snapshot", wraps=module.build_runtime_snapshot
    ) as capture:
        _edit(host, controller, first, 2)
        _edit(host, controller, second, 3)
        assert not host.execution_client.submission_calls
        assert len(host.next_turn_callbacks) == 1
        host.flush_turns()
        assert capture.call_count == 2, (
            "Auto rebuilt the graph edit's captured snapshot"
        )
    assert len(host.execution_client.start_calls) == 1
    request = host.execution_client.submission_calls[0]
    assert set(request.target_node_ids) == {first.node_id, second.node_id}
    nodes = request.runtime_snapshot.workspace(wid).nodes_by_id
    assert nodes[first.node_id].properties["value"] == 2
    assert nodes[second.node_id].properties["value"] == 3


def test_auto_edit_during_preparation_cancels_old_capture_and_keeps_all_targets():
    host, controller, wid, (first, second) = _setup()
    _edit(host, controller, first, 2)
    _turn(host)
    previous = controller._active_submission.handle
    assert host.run_state.engine_state_value == "preparing"
    assert not host.action_pause.enabled and host.action_stop.enabled
    _edit(host, controller, second, 3)
    assert previous.cancellation.is_set()
    host.flush_turns()
    assert previous.state == "cancelled"
    assert len(host.execution_client.submission_calls) == 2
    assert len(host.execution_client.start_calls) == 1
    assert set(host.execution_client.start_calls[0]["target_node_ids"]) == {
        first.node_id,
        second.node_id,
    }
    assert host.run_state.active_run_workspace_id == wid


@pytest.mark.parametrize("preparing", [False, True])
def test_stop_clears_queued_auto_and_cancels_preparation(preparing):
    host, controller, _wid, (first, _second) = _setup()
    _edit(host, controller, first, 2)
    if preparing:
        _turn(host)
    controller.stop_workflow()
    host.flush_turns()
    assert not host.execution_client.start_calls
    assert not host.run_state.active_submission_id
    assert not host.run_state.pending_auto_run_target_node_ids


@pytest.mark.parametrize("executing", [False, True])
def test_manual_cancels_preparing_auto_and_preserves_an_admitted_run(executing):
    host, controller, _wid, (first, _second) = _setup()
    _edit(host, controller, first, 2)
    _turn(host)
    handle = controller._active_submission.handle
    if executing:
        host.flush_turns()
    controller.set_auto_run_enabled(False)
    host.flush_turns()
    assert handle.cancellation.is_set() is not executing
    assert len(host.execution_client.start_calls) == int(executing)
    assert not host.execution_client.stop_calls


def test_explicit_run_with_changed_inputs_is_cancelled_without_replay():
    host, controller, _wid, (first, _second) = _setup(auto=False)
    controller.run_workflow()
    _edit(host, controller, first, 2)
    host.flush_turns()
    assert len(host.execution_client.submission_calls) == 1
    assert not host.execution_client.start_calls
    assert not host.run_state.active_submission_id
    assert any(
        "inputs changed" in message for _level, message in host.console_panel.logs
    )


def test_admission_enables_stop_and_only_run_started_enables_pause():
    host, controller, wid, _nodes = _setup(auto=False)
    controller.run_workflow()
    assert host.run_state.active_submission_id and not host.run_state.active_run_id
    assert host.action_stop.enabled and not host.action_pause.enabled
    host.flush_turns()
    assert host.run_state.active_run_id and not host.run_state.active_submission_id
    assert host.action_stop.enabled and not host.action_pause.enabled
    host.run_event_controller.handle_execution_event(
        {
            "type": "run_started",
            "run_id": host.run_state.active_run_id,
            "workspace_id": wid,
        }
    )
    assert host.action_pause.enabled
    assert host.run_state.engine_state_value == "running"


@pytest.mark.parametrize("action", ["project_reset", "close", "navigation"])
def test_late_submission_delivery_after_session_change_cannot_start(action):
    host, controller, _wid, _nodes = _setup(auto=False)
    controller.run_workflow()
    if action == "project_reset":
        controller.reset_runtime_solution_state()
    elif action == "close":
        controller.close()
    else:
        host.workspace_manager.set_active_workspace("other")
        controller.evaluate_workspace_on_open("other")
    host.flush_turns()
    assert not host.execution_client.start_calls
