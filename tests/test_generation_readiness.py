# Purpose: Prove generation initialization shares work and has no workflow effects.
# Map: subsystems/execution.md
# Tests: this file
from __future__ import annotations

import threading
import queue
from unittest.mock import patch

from ea_node_editor.execution.backends import ExecutionBackendSelection
from ea_node_editor.execution.environment_identity import EnvironmentIdentityCache
from ea_node_editor.nodes.bootstrap import (
    build_builtin_registry,
    build_default_registry,
)
from ea_node_editor.execution.generation_messages import PrepareGenerationCommand
from ea_node_editor.execution.generation_readiness import GenerationReadiness
from ea_node_editor.execution.protocol_codec import (
    command_to_dict,
    dict_to_command,
    dict_to_event,
)
from ea_node_editor.execution.registry_agreement import RegistryAgreement
from ea_node_editor.execution.worker_runtime import RuntimePreparationCache
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.execution.worker_protocol import dispatch_generation_preparation
import pytest
from ea_node_editor.execution.runtime import CorexRuntime
from ea_node_editor.execution.runtime_requests import ExecutionRequest
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.graph.model import GraphModel
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import Mock
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMainWindow
from ea_node_editor.ui.shell.composition.startup_worker import StartupWorkerWarmup
from ea_node_editor.ui.shell.state import ShellRunState
from ea_node_editor.nodes.node_specs import NodeTypeSpec


def test_environment_preview_is_single_flight_and_generation_owned():
    registry = build_builtin_registry()
    cache = EnvironmentIdentityCache()
    entered, release = threading.Event(), threading.Event()
    results = []
    calls = []

    def identity(_names):
        calls.append(True)
        entered.set()
        assert release.wait(10)
        return {"interpreter": "reference", "packages": ()}

    with patch(
        "ea_node_editor.execution.environment_identity._local_runtime_identity",
        side_effect=identity,
    ):
        workers = [
            threading.Thread(
                target=lambda: results.append(
                    cache.compute(ExecutionBackendSelection(), registry)
                )
            )
            for _ in range(2)
        ]
        workers[0].start()
        assert entered.wait(10)
        workers[1].start()
        release.set()
        for worker in workers:
            worker.join(10)
            assert not worker.is_alive()
        assert len(calls) == 1 and len(set(results)) == 1
        assert cache.compute(ExecutionBackendSelection(), registry) == results[0]
        candidate = registry.fork()
        candidate.set_addon_runtime_config((("tests.changed", True),))
        candidate.freeze()
        changed = cache.compute(ExecutionBackendSelection(), candidate)
        assert changed != results[0]
        assert len(calls) == 2


def test_generation_wire_is_complete_and_strict():
    registry = build_builtin_registry()
    agreement = RegistryAgreement.from_registry(registry)
    command = PrepareGenerationCommand("prepare", agreement)
    payload = command_to_dict(command)
    assert payload["agreement"] == agreement.to_payload()
    assert dict_to_command(payload) == command
    with pytest.raises(ValueError):
        dict_to_command({**payload, "runtime_snapshot": {}})
    malformed = agreement.to_payload()
    malformed["catalog_revisions"][0]["implementation_version"] = []
    with pytest.raises((TypeError, ValueError)):
        dict_to_command({**payload, "agreement": malformed})


def test_worker_readiness_reuses_verified_declarations_without_running_a_workflow():
    registry = build_builtin_registry()
    agreement = RegistryAgreement.from_registry(registry)
    cache = RuntimePreparationCache()
    services = WorkerServices()
    events = queue.Queue()
    with (
        patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ),
        patch(
            "ea_node_editor.execution.plugin_worker_runtime.validated_package_declarations",
            side_effect=AssertionError("rebuilt trusted declarations"),
        ),
        patch(
            "ea_node_editor.execution.solution_identity.corex_build_digest",
            return_value="a" * 64,
        ),
        patch(
            "ea_node_editor.execution.worker_runtime.load_runtime_snapshot",
            side_effect=AssertionError("read workflow"),
        ),
    ):
        dispatch_generation_preparation(
            PrepareGenerationCommand("prepare", agreement),
            event_queue=events,
            worker_services=services,
            runtime_cache=cache,
        )
    event = dict_to_event(events.get_nowait())
    assert event.type == "generation_prepared", event
    assert event.registry_contract_fingerprint == registry.contract_fingerprint()
    assert not cache._plugin_runtime._modules and not cache._plugin_runtime._functions
    assert services._mechanical_session_service is None
    assert services._viewer_session_service is None
    assert services._prepared_scene_runtime is None
    assert services.handle_registry.active_handle_count == 0


def test_readiness_correlates_and_retires_late_responses():
    agreement = RegistryAgreement.from_registry(build_builtin_registry())
    state = GenerationReadiness()
    first, created = state.begin(1, agreement)
    same, repeated = state.begin(1, agreement)
    assert created and not repeated and first is same
    state.retire("worker ended")
    with pytest.raises(RuntimeError, match="worker ended"):
        first.result()
    second, created = state.begin(2, agreement)
    response = {
        "type": "generation_prepared",
        "request_id": first.request_id,
        "registry_contract_fingerprint": agreement.registry_contract_fingerprint,
        "runtime_registry_fingerprint": agreement.runtime_registry_fingerprint,
        "build_fingerprint": "a" * 64,
    }
    state.receive(response, 1)
    assert not second.done
    state.receive({**response, "request_id": second.request_id}, 2)
    assert second.result().build_fingerprint == "a" * 64


def test_real_builtin_readiness_is_shared_and_does_not_execute_nodes():
    registry = build_default_registry(include_public_plugins=False)
    runtime = CorexRuntime(registry=registry)
    events = []
    runtime.subscribe(events.append)
    try:
        first = runtime.warm_up_builtin_generation()
        assert runtime.warm_up_builtin_generation() is first
        generation = first.result(30)
        assert generation.available
        assert not any(
            event.get("type") in {"run_started", "node_started", "trigger_published"}
            for event in events
        )
        assert runtime.solution_store.stats()["runs"] == 0
        assert runtime.warm_up_builtin_generation() is first
        process = runtime._client._process_client._process
        model = GraphModel()
        workspace = model.active_workspace
        model.add_node(
            workspace.workspace_id,
            "data.number_slider",
            "Value",
            0,
            0,
            properties={"value": 3},
        )
        result = runtime.run(
            ExecutionRequest(
                workspace_id=workspace.workspace_id,
                runtime_snapshot=build_runtime_snapshot(
                    model.project,
                    workspace_id=workspace.workspace_id,
                    registry=registry,
                ),
            ),
            timeout=15,
        )
        assert result.status == "completed", result.error
        assert runtime._client._process_client._process is process
    finally:
        runtime.shutdown()


def test_immediate_run_waits_for_the_same_generation_preparation():
    registry = build_default_registry(include_public_plugins=False)
    runtime = CorexRuntime(registry=registry)
    entered, release, completed = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    runtime.subscribe(
        lambda event: completed.set() if event.get("type") == "run_completed" else None
    )
    model = GraphModel()
    wid = model.active_workspace.workspace_id
    model.add_node(wid, "data.number_slider", "Value", 0, 0)
    compute = runtime._client._environment_identity.compute

    def blocked(*args):
        entered.set()
        assert release.wait(15)
        return compute(*args)

    try:
        with patch.object(
            runtime._client._environment_identity, "compute", side_effect=blocked
        ):
            ready = runtime.warm_up_builtin_generation()
            assert entered.wait(15)
            process = runtime._client._process_client._process
            submission = runtime.submit_execution(
                ExecutionRequest(
                    workspace_id=wid,
                    runtime_snapshot=build_runtime_snapshot(
                        model.project, workspace_id=wid, registry=registry
                    ),
                )
            )
            assert submission.state == "queued"
            release.set()
            assert ready.result(30).available
            assert submission.result(15)
            assert completed.wait(15)
            assert runtime._client._process_client._process is process
    finally:
        release.set()
        runtime.shutdown()


def test_shutdown_does_not_wait_for_blocked_warmup():
    registry = build_default_registry(include_public_plugins=False)
    runtime = CorexRuntime(registry=registry)
    entered, release = threading.Event(), threading.Event()

    def blocked(*args):
        entered.set()
        assert release.wait(15)
        return "a" * 64

    try:
        with patch.object(
            runtime._client._environment_identity, "compute", side_effect=blocked
        ):
            ready = runtime.warm_up_builtin_generation()
            assert entered.wait(15)
            runtime.shutdown(wait=False)
            release.set()
            with pytest.raises(RuntimeError):
                ready.result(15)
    finally:
        release.set()
        runtime.shutdown()
    assert runtime._client._process_client._process is None


def test_failed_warmup_does_not_prevent_ordinary_execution():
    registry = build_default_registry(include_public_plugins=False)
    runtime = CorexRuntime(registry=registry)
    model = GraphModel()
    wid = model.active_workspace.workspace_id
    model.add_node(wid, "data.number_slider", "Value", 0, 0)
    try:
        with patch.object(
            runtime._client,
            "prepare_builtin_generation",
            side_effect=RuntimeError("transient failure"),
        ):
            with pytest.raises(RuntimeError, match="transient failure"):
                runtime.warm_up_builtin_generation().result(10)
        result = runtime.run(
            ExecutionRequest(
                workspace_id=wid,
                runtime_snapshot=build_runtime_snapshot(
                    model.project, workspace_id=wid, registry=registry
                ),
            ),
            timeout=15,
        )
        assert result.status == "completed", result.error
    finally:
        runtime.shutdown()


def test_identical_registry_worker_restart_retires_readiness():
    runtime = CorexRuntime(
        registry=build_default_registry(include_public_plugins=False)
    )
    try:
        first = runtime.warm_up_builtin_generation().result(30)
        process = runtime._client._process_client._process
        process.terminate()
        process.join(5)
        assert not process.is_alive()
        second = runtime.warm_up_builtin_generation().result(30)
        assert (
            second.available and second.runtime_generation != first.runtime_generation
        )
        assert runtime._client._process_client._process is not process
    finally:
        runtime.shutdown()


def test_superseded_warmup_cannot_republish_its_old_registry():
    registry = build_default_registry(include_public_plugins=False)
    runtime = CorexRuntime(registry=registry)
    entered, release = threading.Event(), threading.Event()
    prepare = runtime._client.prepare_builtin_generation
    def blocked(candidate):
        entered.set()
        assert release.wait(10)
        return prepare(candidate)
    try:
        with patch.object(runtime._client, "prepare_builtin_generation", side_effect=blocked):
            future = runtime.warm_up_builtin_generation()
            assert entered.wait(10)
            replacement = registry.fork()
            replacement.register_descriptor(NodeTypeSpec("tests.new_generation", "New generation", ("Tests",), "", (), ()), lambda: None)
            replacement.freeze()
            runtime.replace_registry(replacement)
            release.set()
            with pytest.raises((ValueError, RuntimeError), match="registry|generation"):
                future.result(10)
        assert runtime._client._published_registry is replacement
        assert runtime._registry is replacement
    finally:
        release.set()
        runtime.shutdown()


@pytest.mark.parametrize(
    "skip",
    [
        "",
        "application_python",
        "workflow_python",
        "active_run",
        "preparing",
        "disabled",
    ],
)
def test_startup_warmup_waits_for_visible_frame_and_captures_configuration(qapp, skip):
    class Frames(QObject):
        afterRendering = pyqtSignal()

    host = QMainWindow()
    frames = Frames(host)
    host.qml_host = SimpleNamespace(quick_window=lambda: frames)
    host._shell_teardown_started = False
    host.run_state = ShellRunState()
    host.app_preferences_controller = SimpleNamespace(
        default_python_executable=lambda: (
            "python" if skip == "application_python" else ""
        )
    )
    host.project_session_controller = SimpleNamespace(
        workflow_settings_payload=lambda: {
            "environment": {
                "python_path": "python" if skip == "workflow_python" else ""
            },
        }
    )
    warm_up = Mock(return_value=Future())
    host.execution_client = SimpleNamespace(warm_up_builtin_generation=warm_up)
    startup = StartupWorkerWarmup(host)
    frames.afterRendering.emit()
    qapp.processEvents()
    warm_up.assert_not_called()
    if skip == "active_run":
        host.run_state.active_run_id = "run"
    if skip == "preparing":
        host.run_state.active_submission_id = "preparing"
    if skip == "disabled":
        startup.enabled = False
    host.show()
    qapp.processEvents()
    frames.afterRendering.emit()
    frames.afterRendering.emit()
    qapp.processEvents()
    assert warm_up.call_count == (0 if skip else 1)
    host.close()
    host.deleteLater()
    qapp.processEvents()
