# Purpose: Prove acknowledged non-prepared viewer invalidation across worker lifecycles.
# Map: subsystems/execution.md
# Tests: this file
from __future__ import annotations

from dataclasses import replace
import io
import json
import queue
import sys
import threading
from types import SimpleNamespace

import pytest

from ea_node_editor.execution.backend_client import ExecutionBackendClient
from ea_node_editor.execution.external_python_client import (
    ExternalPythonExecutionClient,
)
from ea_node_editor.execution.process_client import ProcessExecutionClient
from ea_node_editor.execution.protocol_codec import (
    command_to_dict,
    dict_to_command,
    dict_to_event,
    event_to_dict,
)
from ea_node_editor.execution.run_messages import (
    ShutdownCommand,
    RetireWorkspaceCommand,
    WorkspaceRetiredEvent,
)
from ea_node_editor.execution.runtime import CorexRuntime
from ea_node_editor.execution.runtime_requests import ExecutionRequest
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.execution.trusted_client import TrustedInProcessExecutionClient
from ea_node_editor.execution.viewer_messages import (
    InvalidateViewerSessionsCommand,
    OpenViewerSessionCommand,
    ViewerSessionsInvalidatedEvent,
    viewer_epoch_snapshot_digest,
)
from ea_node_editor.execution.worker import worker_main
from ea_node_editor.execution.worker_protocol import dispatch_viewer_invalidation
from ea_node_editor.execution.worker_runner import RunControl
from ea_node_editor.execution import stdio_worker
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from tests.test_runtime import _wait_for_backend_run_cleanup
from tests.typed_handle_support import core_worker_services
from tests.execution_client_fixtures import _external_selection


def invalidation(
    *, workspace_id="ws", node_ids=None, workspace_epoch=1, node_epochs=()
):
    fields = dict(
        workspace_id=workspace_id,
        node_ids=node_ids,
        workspace_epoch=workspace_epoch,
        node_epochs=node_epochs,
    )
    return InvalidateViewerSessionsCommand(
        request_id="invalidate_1",
        **fields,
        snapshot_digest=viewer_epoch_snapshot_digest(**fields),
    )


@pytest.mark.parametrize(
    "node_ids,node_epochs", [(None, ()), (("a", "b"), (("a", 1), ("b", 2)))]
)
def test_invalidation_protocol_roundtrip_and_digest_validation(node_ids, node_epochs):
    command = invalidation(node_ids=node_ids, node_epochs=node_epochs)
    assert dict_to_command(command_to_dict(command)) == command
    ack = ViewerSessionsInvalidatedEvent(
        request_id=command.request_id,
        workspace_id=command.workspace_id,
        snapshot_digest=command.snapshot_digest,
    )
    assert dict_to_event(event_to_dict(ack)) == ack
    with pytest.raises(ValueError, match="digest mismatch"):
        command_to_dict(replace(command, workspace_epoch=2))
    with pytest.raises((ValueError, TypeError)):
        command_to_dict(replace(command, workspace_epoch=True))


def test_explicit_global_invalidation_repairs_old_context_without_baseline_relaxation():
    services = core_worker_services()
    service = services.viewer_session_service
    service.install_workspace_context(workspace_id="ws")
    empty = dict(workspace_id="ws", node_ids=(), workspace_epoch=1, node_epochs=())
    empty["snapshot_digest"] = viewer_epoch_snapshot_digest(**empty)
    with pytest.raises(ValueError, match="fresh service"):
        service.validate_invalidation_snapshot(**empty)
    events = queue.Queue()
    dispatch_viewer_invalidation(
        invalidation(), event_queue=events, worker_services=services
    )
    assert events.get_nowait()["type"] == "viewer_sessions_invalidated"
    assert service.validate_invalidation_snapshot(**empty) == ((), ())
    assert "ws" in service._workspace_contexts


def test_scoped_invalidation_releases_only_matching_viewer_owner():
    services = core_worker_services()
    service = services.viewer_session_service
    handles = []
    for workspace_id, node_id in (("ws", "a"), ("ws", "b"), ("other", "a")):
        service.open_session(
            OpenViewerSessionCommand(
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=node_id,
                transport={"kind": "mock_live"},
            )
        )
        handles.append(service.session_handle(workspace_id, node_id))
    assert services.handle_registry.active_handle_count == 3
    events = queue.Queue()
    dispatch_viewer_invalidation(
        invalidation(node_ids=("a",), workspace_epoch=0, node_epochs=(("a", 1),)),
        event_queue=events,
        worker_services=services,
    )
    assert events.get_nowait()["type"] == "viewer_sessions_invalidated"
    assert services.handle_registry.active_handle_count == 2
    assert service._sessions[("ws", "a")].session_state == "invalidated"
    for handle in handles[1:]:
        assert services.resolve_handle(handle) is not None
    services.reset()


@pytest.mark.parametrize("active", [False, True])
def test_idle_and_active_worker_dispatch_ack_only_after_service_adoption(active):
    services = core_worker_services()
    services.viewer_session_service.install_workspace_context(workspace_id="ws")
    commands, events = queue.Queue(), queue.Queue()
    commands.put(command_to_dict(invalidation()))
    if active:
        control = RunControl(
            commands,
            events,
            run_id="run",
            workspace_id="ws",
            data_types=services.data_types,
            viewer_invalidation_handler=lambda command: dispatch_viewer_invalidation(
                command, event_queue=events, worker_services=services
            ),
        )
        control.poll_commands()
    else:
        commands.put(command_to_dict(ShutdownCommand()))
        worker_main(commands, events, services)
    assert events.get_nowait()["type"] == "viewer_sessions_invalidated"
    assert services.viewer_session_service._workspace_invalidation_epochs["ws"] >= 1


@pytest.mark.parametrize(
    "client_type", [ProcessExecutionClient, ExternalPythonExecutionClient]
)
@pytest.mark.parametrize(
    "bad_ack", ["generation", "workspace", "digest", "replacement"]
)
def test_transport_ack_is_required_and_generation_and_digest_are_checked(
    client_type, monkeypatch, bad_ack
):
    client = client_type()
    sent = []
    monkeypatch.setattr(client, "_viewer_generation_is_live", lambda: True)
    monkeypatch.setattr(
        client, "_post_command", lambda command: sent.append(command) is None
    )
    try:
        client.invalidate_viewer_requests("ws", None)
        with pytest.raises(RuntimeError, match="not been acknowledged"):
            client._assert_viewer_invalidations_ready("ws")
        with pytest.raises(TimeoutError, match="did not acknowledge"):
            client.wait_for_viewer_invalidations("ws", timeout_sec=0.001)
        command = sent[-1]
        ack = ViewerSessionsInvalidatedEvent(
            request_id=command.request_id,
            workspace_id="ws",
            snapshot_digest=command.snapshot_digest,
        )
        client._dispatch_event(ack, generation_token=0)
        client.wait_for_viewer_invalidations("ws", timeout_sec=0.1)
        client._dispatch_event(ack, generation_token=0)
        client.wait_for_viewer_invalidations("ws", timeout_sec=0.1)
        client.invalidate_viewer_requests("ws", None)
        command = sent[-1]
        invalid_ack = replace(
            ack, request_id=command.request_id, snapshot_digest=command.snapshot_digest
        )
        expected_error = "does not match"
        if bad_ack == "replacement":
            client._catalog_generation_token = 1
            client._accepted_physical_generation_token = 1
            expected_error = "generation changed"
        else:
            if bad_ack == "workspace":
                invalid_ack = replace(invalid_ack, workspace_id="other")
            elif bad_ack == "digest":
                invalid_ack = replace(invalid_ack, snapshot_digest="0" * 64)
            else:
                expected_error = "generation changed"
            client._dispatch_event(
                invalid_ack, generation_token=1 if bad_ack == "generation" else 0
            )
        with pytest.raises(RuntimeError, match=expected_error):
            client.wait_for_viewer_invalidations("ws", timeout_sec=0.1)
    finally:
        client.shutdown()


def test_failed_delivery_cannot_admit_run_and_empty_invalidation_does_nothing(
    monkeypatch,
):
    client = ProcessExecutionClient()
    monkeypatch.setattr(client, "_viewer_generation_is_live", lambda: True)
    monkeypatch.setattr(client, "_post_command", lambda _command: False)
    try:
        assert client.invalidate_viewer_requests("ws", ()) == 0
        assert not hasattr(client, "_viewer_invalidation_deliveries")
        client.invalidate_viewer_requests("ws", None)
        with pytest.raises(RuntimeError, match="Failed to dispatch"):
            client.wait_for_viewer_invalidations("ws", timeout_sec=0.1)
        with pytest.raises(RuntimeError, match="Failed to dispatch"):
            client._assert_viewer_invalidations_ready("ws")
    finally:
        client.shutdown()


@pytest.mark.parametrize(
    "filter_factory",
    [lambda: ("b", "a", "b"), lambda: {"b", "a"}, lambda: iter(("b", "a"))],
)
def test_scoped_lifecycle_canonicalizes_public_iterable_filter(filter_factory):
    client = TrustedInProcessExecutionClient()
    service = client._worker_services.viewer_session_service
    service.install_workspace_context(workspace_id="ws")
    try:
        client.invalidate_viewer_requests("ws", filter_factory())
        client.wait_for_viewer_invalidations("ws", timeout_sec=2)
        assert service._node_invalidation_epochs == {("ws", "a"): 1, ("ws", "b"): 1}
    finally:
        client.shutdown()


def test_reader_can_invalidate_while_process_retirement_waits_for_reader_ack(
    monkeypatch,
):
    client = ProcessExecutionClient()
    client._process = SimpleNamespace(pid=123, is_alive=lambda: True)
    client._physical_generation_run_dispatched = True
    monkeypatch.setattr(client, "_viewer_generation_is_live", lambda: True)
    posted_retirement, reader_done = threading.Event(), threading.Event()
    retirement_commands, errors = [], []

    def post(command):
        if isinstance(command, RetireWorkspaceCommand):
            retirement_commands.append(command)
            posted_retirement.set()
        else:
            client._dispatch_event(
                ViewerSessionsInvalidatedEvent(
                    request_id=command.request_id,
                    workspace_id=command.workspace_id,
                    snapshot_digest=command.snapshot_digest,
                ),
                generation_token=0,
            )
        return True

    monkeypatch.setattr(client, "_post_command", post)

    def retire():
        try:
            client.retire_workspace("ws")
        except Exception as exc:
            errors.append(exc)

    def read_earlier_callback_then_ack():
        assert posted_retirement.wait(3)
        client.invalidate_viewer_requests("ws", None)
        command = retirement_commands[0]
        client._dispatch_event(
            WorkspaceRetiredEvent(request_id=command.request_id, workspace_id="ws"),
            generation_token=0,
        )
        reader_done.set()

    retirement_thread = threading.Thread(target=retire)
    reader_thread = threading.Thread(target=read_earlier_callback_then_ack)
    try:
        retirement_thread.start()
        reader_thread.start()
        assert reader_done.wait(3), (
            "reader callback was blocked by retirement's start lock"
        )
        retirement_thread.join(3)
        assert not retirement_thread.is_alive()
        assert not errors
        client.wait_for_viewer_invalidations("ws", timeout_sec=0.1)
    finally:
        client._fail_workspace_retirements("test cleanup")
        retirement_thread.join(3)
        reader_thread.join(3)
        client._process = None
        client.shutdown()


def test_dormant_participants_do_not_start_workers(monkeypatch):
    backend = ExecutionBackendClient()
    try:
        for client in (
            backend._process_client,
            backend._external_python_client,
            backend._trusted_client,
        ):
            monkeypatch.setattr(
                client,
                "_post_command",
                lambda _command: pytest.fail(
                    "must not start or contact a dormant worker"
                ),
            )
        backend.invalidate_viewer_requests("ws", None)
        for client in (
            backend._process_client,
            backend._external_python_client,
            backend._trusted_client,
        ):
            assert client._workspace_viewer_epochs["ws"] == 1
            assert not client._viewer_invalidation_deliveries
    finally:
        backend.shutdown()


@pytest.mark.parametrize("service_created_before_run", [False, True])
def test_trusted_active_to_idle_drain_preserves_unpolled_invalidation(
    monkeypatch, service_created_before_run
):
    client = TrustedInProcessExecutionClient()
    if service_created_before_run:
        client._worker_services.viewer_session_service.install_workspace_context(
            workspace_id="ws"
        )
    entered, finish = threading.Event(), threading.Event()

    def run_without_polling(*_args, **_kwargs):
        entered.set()
        assert finish.wait(5)
        if not service_created_before_run:
            client._worker_services.viewer_session_service.install_workspace_context(
                workspace_id="ws"
            )

    monkeypatch.setattr(
        "ea_node_editor.execution.trusted_client.run_workflow", run_without_polling
    )
    thread = threading.Thread(
        target=client._run_workflow_thread, args=(SimpleNamespace(), 0)
    )
    client._run_thread = thread
    try:
        thread.start()
        assert entered.wait(5)
        client.invalidate_viewer_requests("ws", None)
        with pytest.raises(RuntimeError, match="not been acknowledged"):
            client._assert_viewer_invalidations_ready("ws")
        finish.set()
        thread.join(5)
        assert not thread.is_alive()
        client.wait_for_viewer_invalidations("ws", timeout_sec=2)
        assert client._run_thread is None
        assert (
            client._worker_services.viewer_session_service._workspace_invalidation_epochs[
                "ws"
            ]
            == 1
        )
        client._drain_command_queue()
        client.invalidate_viewer_requests("ws", None)
        client.wait_for_viewer_invalidations("ws", timeout_sec=2)
        assert (
            client._worker_services.viewer_session_service._workspace_invalidation_epochs[
                "ws"
            ]
            == 2
        )
    finally:
        finish.set()
        thread.join(5)
        client.shutdown()


@pytest.mark.parametrize(
    "backend_id", ["trusted_in_process", "process_isolated", "external_subprocess"]
)
def test_prepared_empty_viewer_run_project_close_and_same_workspace_reopen(backend_id):
    registry = build_builtin_registry()
    model = GraphModel()
    workspace_id = model.active_workspace.workspace_id
    model.add_node(
        workspace_id, "core.constant", "Constant", 0, 0, properties={"value": "reopen"}
    )
    snapshot = build_runtime_snapshot(
        model.project, workspace_id=workspace_id, registry=registry
    )
    runtime = CorexRuntime(registry=registry)
    terminal, events = threading.Event(), []

    def capture(event):
        events.append(event)
        if event.get("type") in {"run_completed", "run_failed", "run_stopped"}:
            terminal.set()

    runtime.subscribe(capture)
    try:
        request = ExecutionRequest(
            runtime_snapshot=snapshot,
            workspace_id=workspace_id,
            execution_backend={
                "requested_backend": backend_id,
                "allow_trusted_in_process": True,
                "allow_external_subprocess": True,
                "python_executable": sys.executable,
            },
        )
        for reopening in (False, True):
            if reopening:
                # This is the shell's project-close invalidation followed by a
                # fresh solution session for the same persisted workspace ID.
                runtime.invalidate_viewer_requests(workspace_id, None)
                runtime.reset_project_session(model.project.project_id)
                # UI projection epochs are independent from the selected worker.
                runtime._client._workspace_viewer_epochs[workspace_id] += 7
            events.clear()
            terminal.clear()
            prepared = runtime.prepare_execution(request)
            assert runtime.dispatch_prepared(prepared), "; ".join(
                str(event.get("error", event)) for event in events
            )
            assert terminal.wait(45), events
            assert [
                event["type"]
                for event in events
                if event["type"] in {"run_completed", "run_failed", "run_stopped"}
            ] == ["run_completed"], events
            _wait_for_backend_run_cleanup(runtime)
    finally:
        runtime.shutdown()


def test_stdio_idle_entrypoint_applies_and_acknowledges_invalidation():
    output = io.StringIO()
    source = io.StringIO(
        "\n".join(
            json.dumps(command_to_dict(command))
            for command in (invalidation(), ShutdownCommand())
        )
        + "\n"
    )
    previous_stdout = sys.stdout
    try:
        assert stdio_worker.main(source, output) == 0
    finally:
        sys.stdout = previous_stdout
    events = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [event["type"] for event in events] == ["viewer_sessions_invalidated"]
    assert events[0]["snapshot_digest"] == invalidation().snapshot_digest


def test_stdio_run_exit_drains_unpolled_invalidation_before_idle_handoff(monkeypatch):
    services = core_worker_services()
    entered, finish, finished = threading.Event(), threading.Event(), threading.Event()
    commands, events = queue.Queue(), queue.Queue()
    lifecycle_lock = threading.Lock()

    def run_without_polling(*_args, **_kwargs):
        entered.set()
        assert finish.wait(5)
        services.viewer_session_service.install_workspace_context(workspace_id="ws")

    monkeypatch.setattr(stdio_worker, "run_workflow", run_without_polling)
    thread = threading.Thread(
        target=stdio_worker._run_workflow_thread,
        args=(SimpleNamespace(),),
        kwargs=dict(
            event_queue=events,
            command_queue=commands,
            worker_services=services,
            lifecycle_lock=lifecycle_lock,
            run_finished=finished,
        ),
    )
    try:
        thread.start()
        assert entered.wait(5)
        with lifecycle_lock:
            assert not finished.is_set()
            commands.put(command_to_dict(invalidation()))
        finish.set()
        thread.join(5)
        assert not thread.is_alive()
        assert finished.is_set()
        assert events.get_nowait()["type"] == "viewer_sessions_invalidated"
        assert services.viewer_session_service._workspace_invalidation_epochs["ws"] == 1
    finally:
        finish.set()
        thread.join(5)
        services.reset()


@pytest.mark.parametrize(
    "client_type", [ProcessExecutionClient, ExternalPythonExecutionClient]
)
def test_direct_start_releases_reservation_after_unacknowledged_invalidation(
    client_type, monkeypatch
):
    registry = build_builtin_registry()
    model = GraphModel()
    workspace_id = model.active_workspace.workspace_id
    model.add_node(workspace_id, "core.constant", "Constant", 0, 0)
    snapshot = build_runtime_snapshot(
        model.project, workspace_id=workspace_id, registry=registry
    )
    client = client_type()
    monkeypatch.setattr(client, "_ensure_process", lambda *_args: None)
    monkeypatch.setattr(client, "_post_command", lambda _command: True)
    if isinstance(client, ExternalPythonExecutionClient):
        monkeypatch.setattr(client, "_process_start_required", lambda *_args: False)
    kwargs = dict(
        project_path="",
        workspace_id=workspace_id,
        trigger={"runtime_snapshot": snapshot},
        data_types=registry.data_types,
        plugin_bundles=registry.plugin_bundle_refs(),
        plugin_fingerprint=registry.plugin_fingerprint(),
        registry_contract_fingerprint=registry.contract_fingerprint(),
        addon_runtime_config=registry.addon_runtime_config(),
    )
    if isinstance(client, ExternalPythonExecutionClient):
        kwargs["execution_backend"] = _external_selection(sys.executable)

    def pending(_workspace_id):
        raise RuntimeError("Viewer invalidation has not been acknowledged")

    try:
        monkeypatch.setattr(client, "_assert_viewer_invalidations_ready", pending)
        assert client.start_run(**kwargs) == ""
        assert not client._active_run_id
        assert not client._start_run_pending_id
        monkeypatch.setattr(
            client, "_assert_viewer_invalidations_ready", lambda _workspace_id: None
        )
        assert client.start_run(**kwargs)
    finally:
        client.shutdown()


@pytest.mark.parametrize(
    "client_type",
    [
        TrustedInProcessExecutionClient,
        ProcessExecutionClient,
        ExternalPythonExecutionClient,
    ],
)
def test_direct_runs_and_project_close_share_concrete_worker_epochs(client_type):
    registry = build_builtin_registry()
    model = GraphModel()
    workspace_id = model.active_workspace.workspace_id
    model.add_node(
        workspace_id, "core.constant", "Constant", 0, 0, properties={"value": "direct"}
    )
    snapshot = build_runtime_snapshot(
        model.project, workspace_id=workspace_id, registry=registry
    )
    client = client_type()
    terminal, events = threading.Event(), []

    def capture(event):
        events.append(event)
        if event.get("type") in {"run_completed", "run_failed", "run_stopped"}:
            terminal.set()

    client.subscribe(capture)
    kwargs = dict(
        project_path="",
        workspace_id=workspace_id,
        trigger={"runtime_snapshot": snapshot},
        data_types=registry.data_types,
        plugin_bundles=registry.plugin_bundle_refs(),
        plugin_fingerprint=registry.plugin_fingerprint(),
        registry_contract_fingerprint=registry.contract_fingerprint(),
        addon_runtime_config=registry.addon_runtime_config(),
    )
    if isinstance(client, ExternalPythonExecutionClient):
        kwargs["execution_backend"] = _external_selection(sys.executable)
    try:
        # A dormant participant can already be ahead of a genuinely new service.
        client.invalidate_viewer_requests(workspace_id, None)
        client.invalidate_viewer_requests(workspace_id, None)
        for run_index in range(3):
            if run_index == 2:
                client.invalidate_viewer_requests(workspace_id, None)
                client.wait_for_viewer_invalidations(workspace_id, timeout_sec=5)
            events.clear()
            terminal.clear()
            assert client.start_run(**kwargs), events
            assert terminal.wait(30), events
            assert [
                event["type"]
                for event in events
                if event["type"] in {"run_completed", "run_failed", "run_stopped"}
            ] == ["run_completed"], events
            run_thread = getattr(client, "_run_thread", None)
            if run_thread is not None:
                run_thread.join(5)
        assert client._workspace_viewer_epochs[workspace_id] == 6
        if isinstance(client, TrustedInProcessExecutionClient):
            assert (
                client._worker_services.viewer_session_service._workspace_invalidation_epochs[
                    workspace_id
                ]
                == 6
            )
    finally:
        client.shutdown()


@pytest.mark.parametrize(
    "client_type", [ProcessExecutionClient, ExternalPythonExecutionClient]
)
def test_viewer_command_cannot_overtake_its_published_lifecycle_epoch(
    client_type, monkeypatch
):
    client = client_type()
    services = core_worker_services()
    services.viewer_session_service.install_workspace_context(workspace_id="ws")
    client._data_types = services.data_types
    lifecycle_entered, release_lifecycle, viewer_attempted, viewer_sent = (
        threading.Event() for _ in range(4)
    )
    commands, errors = [], []
    monkeypatch.setattr(client, "_viewer_generation_is_live", lambda: True)
    monkeypatch.setattr(
        client, "_ensure_process", lambda *_args: viewer_attempted.set()
    )

    def post(command):
        if isinstance(command, InvalidateViewerSessionsCommand):
            lifecycle_entered.set()
            assert release_lifecycle.wait(3)
            events = queue.Queue()
            dispatch_viewer_invalidation(
                command, event_queue=events, worker_services=services
            )
            ack = dict_to_event(events.get_nowait())
            client._dispatch_event(ack, generation_token=0)
        else:
            viewer_sent.set()
            services.viewer_session_service.handle_command(command)
        commands.append(command.type)
        return True

    monkeypatch.setattr(client, "_post_command", post)
    monkeypatch.setattr(
        client, "_try_post_command", lambda command: (post(command), "")
    )

    def invoke(call):
        try:
            call()
        except Exception as exc:
            errors.append(exc)

    invalidate_thread = threading.Thread(
        target=invoke, args=(lambda: client.invalidate_viewer_requests("ws", None),)
    )
    viewer_thread = threading.Thread(
        target=invoke,
        args=(
            lambda: client._send_viewer_command(
                OpenViewerSessionCommand(
                    request_id="open",
                    workspace_id="ws",
                    node_id="a",
                    session_id="session",
                    transport={"kind": "mock_live"},
                )
            ),
        ),
    )
    try:
        invalidate_thread.start()
        assert lifecycle_entered.wait(3)
        viewer_thread.start()
        if isinstance(client, ProcessExecutionClient):
            assert viewer_attempted.wait(3)
        assert not viewer_sent.wait(0.1)
        release_lifecycle.set()
        invalidate_thread.join(3)
        viewer_thread.join(3)
        assert not invalidate_thread.is_alive() and not viewer_thread.is_alive()
        assert not errors
        assert commands == ["invalidate_viewer_sessions", "open_viewer_session"]
        client.wait_for_viewer_invalidations("ws", timeout_sec=0.1)
    finally:
        release_lifecycle.set()
        invalidate_thread.join(3)
        viewer_thread.join(3)
        client.shutdown()
        services.reset()
