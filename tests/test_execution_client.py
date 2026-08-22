from __future__ import annotations

import json
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock, patch

from ea_node_editor.execution.backends import (
    EXTERNAL_SUBPROCESS_BACKEND,
    PROCESS_ISOLATED_BACKEND,
    TRUSTED_IN_PROCESS_BACKEND,
    ExecutionBackendOrchestrator,
    ExecutionBackendSelection,
)
from ea_node_editor.execution.client import (
    ExecutionBackendClient,
    ExternalPythonExecutionClient,
    ProcessExecutionClient,
    TrustedInProcessExecutionClient,
    _ExecutionClientCommon,
    _PendingViewerRequest,
)
from ea_node_editor.execution.headless_runtime import (
    CorexRuntime,
    ExecutionRequest,
    WorkspaceSelection,
    load_project,
    select_workspace,
)
from ea_node_editor.execution.python_environment import (
    resolve_workflow_python_environment,
)
from ea_node_editor.execution.managed_runtime import (
    ADDON_RUNTIME_PYTHON_ENV,
    resolve_addon_runtime_paths,
    resolve_managed_runtime_paths,
)
from ea_node_editor.execution.protocol import (
    NodeSettledEvent,
    NodeStartedEvent,
    ProtocolErrorEvent,
    RunCompletedEvent,
    SettledPortResult,
    ViewerSessionOpenedEvent,
    catalog_agreement,
    event_to_dict,
)
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.execution.worker_runtime import (
    DEFAULT_RUNTIME_PREPARATION_CACHE,
)
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.types import (
    RuntimeArtifactRef,
    RuntimeHandleRef,
    deserialize_runtime_value,
)
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.runtime_contracts import (
    ARRAY_DATA_REF_TYPE_ID,
    TABULAR_DATA_REF_TYPE_ID,
    ArrayDataRef,
    DataTypeCatalog,
    DataTypeCatalogError,
    DataTypeFamilySpec,
    DataTypeSpec,
    DataTree,
    ImageValue,
    PATH_DATA_TYPE_ID,
    TabularDataRef,
)


def _revision_catalog(implementation_version: str) -> DataTypeCatalog:
    catalog = DataTypeCatalog()
    catalog.register_many(
        families=(
            DataTypeFamilySpec("tests.catalog", "Catalog", "data.tests", "tests"),
        ),
        types=(
            DataTypeSpec(
                "tests.CatalogValue",
                "Catalog Value",
                "tests.catalog",
                lambda value: isinstance(value, str),
                implementation_version=implementation_version,
            ),
        ),
        owner_id="tests.catalog",
        owner_version=implementation_version,
    )
    catalog.freeze()
    return catalog


class _RoutingClient:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[str, tuple, dict]] = []

    def _record(self, method: str, args: tuple, kwargs: dict) -> str:
        self.calls.append((method, args, dict(kwargs)))
        return f"{self.name}_{method}"

    def open_viewer_session(self, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
        return self._record("open", args, kwargs)

    def update_viewer_session(self, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
        return self._record("update", args, kwargs)

    def close_viewer_session(self, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
        return self._record("close", args, kwargs)

    def materialize_viewer_data(self, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
        return self._record("materialize", args, kwargs)

    def query_viewer_session(self, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
        return self._record("query", args, kwargs)

    def shutdown(self) -> None:
        return None


class ExecutionClientCommonTests(unittest.TestCase):
    def test_common_methods_and_commands_are_shared_across_backends(self) -> None:
        common_methods = (
            "subscribe",
            "_dispatch_event",
            "_clear_active_node_state_locked",
            "_clear_active_run_state_locked",
            "_record_execution_event_state",
            "_emit_protocol_error",
            "_next_viewer_request_id",
            "_track_viewer_request",
            "_complete_viewer_request",
            "_dispatch_viewer_request_failure",
            "_viewer_protocol_error_failure",
            "pause_run",
            "resume_run",
            "stop_run",
            "open_viewer_session",
            "update_viewer_session",
            "close_viewer_session",
            "materialize_viewer_data",
            "query_viewer_session",
        )
        for client_type in (
            ProcessExecutionClient,
            ExternalPythonExecutionClient,
            TrustedInProcessExecutionClient,
        ):
            with self.subTest(client_type=client_type.__name__):
                for method_name in common_methods:
                    self.assertNotIn(method_name, client_type.__dict__)
                    self.assertIs(
                        getattr(client_type, method_name),
                        getattr(_ExecutionClientCommon, method_name),
                    )

                client = object.__new__(client_type)
                client._callbacks = []  # noqa: SLF001
                client._state_lock = threading.Lock()  # noqa: SLF001
                client._active_run_id = ""  # noqa: SLF001
                client._active_workspace_id = ""  # noqa: SLF001
                client._active_node_id = ""  # noqa: SLF001
                client._active_node_deadline = 0.0  # noqa: SLF001
                client._active_node_timeout_sec = 0.0  # noqa: SLF001
                client._script_timeout_by_node_id = {}  # noqa: SLF001
                client._viewer_request_lock = threading.Lock()  # noqa: SLF001
                client._pending_viewer_requests = {}  # noqa: SLF001
                posted_commands = []
                viewer_commands = []

                def post_command(command):  # noqa: ANN001
                    posted_commands.append(command)
                    return True

                def send_viewer_command(command, *, require_session_id=False):  # noqa: ANN001
                    viewer_commands.append((command, require_session_id))
                    return command.request_id

                client._post_command = post_command  # type: ignore[method-assign]  # noqa: SLF001
                client._send_viewer_command = send_viewer_command  # type: ignore[method-assign]  # noqa: SLF001

                client.pause_run("run_demo")
                client.resume_run("run_demo")
                client.stop_run("run_demo")
                self.assertEqual(
                    [command.type for command in posted_commands],
                    ["pause_run", "resume_run", "stop_run"],
                )
                self.assertEqual(
                    [command.run_id for command in posted_commands], ["run_demo"] * 3
                )

                request_ids = (
                    client.open_viewer_session(
                        "ws", "node", session_id="session", backend_id="backend"
                    ),
                    client.update_viewer_session(
                        "ws", "node", "session", backend_id="backend"
                    ),
                    client.close_viewer_session("ws", "node", "session"),
                    client.materialize_viewer_data(
                        "ws", "node", "session", backend_id="backend"
                    ),
                    client.query_viewer_session(
                        "ws",
                        "node",
                        "session",
                        backend_id="backend",
                        query_type="camera",
                    ),
                )
                self.assertEqual(
                    request_ids,
                    tuple(command.request_id for command, _ in viewer_commands),
                )
                self.assertTrue(
                    all(request_id.startswith("viewer_") for request_id in request_ids)
                )
                self.assertEqual(
                    [
                        (command.type, requires_session)
                        for command, requires_session in viewer_commands
                    ],
                    [
                        ("open_viewer_session", False),
                        ("update_viewer_session", True),
                        ("close_viewer_session", True),
                        ("materialize_viewer_data", True),
                        ("query_viewer_session", True),
                    ],
                )
                self.assertTrue(
                    all(command.workspace_id == "ws" for command, _ in viewer_commands)
                )
                self.assertTrue(
                    all(command.node_id == "node" for command, _ in viewer_commands)
                )
                self.assertEqual(viewer_commands[-1][0].query_type, "camera")

    def test_each_public_start_requires_a_new_explicit_catalog(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        model.add_node(
            workspace.workspace_id,
            "core.constant",
            "Constant",
            0,
            0,
            properties={"value": 1},
        )
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )
        clients = (
            (
                ProcessExecutionClient(),
                {},
            ),
            (
                ExternalPythonExecutionClient(),
                {
                    "execution_backend": ExecutionBackendSelection(
                        backend_id=EXTERNAL_SUBPROCESS_BACKEND,
                        isolation="external_subprocess",
                        external_subprocess=True,
                        python_executable=sys.executable,
                    )
                },
            ),
            (
                TrustedInProcessExecutionClient(),
                {},
            ),
        )
        try:
            for client, extra_kwargs in clients:
                with self.subTest(client=type(client).__name__):
                    client._data_types = registry.data_types  # noqa: SLF001
                    events: list[dict] = []
                    client.subscribe(lambda event, target=events: target.append(event))
                    run_id = client.start_run(
                        "",
                        workspace.workspace_id,
                        {"runtime_snapshot": runtime_snapshot},
                        data_types=None,
                        **extra_kwargs,
                    )
                    self.assertEqual(run_id, "")
                    self.assertTrue(
                        any(
                            "authoritative data-type catalog"
                            in str(event.get("error", ""))
                            for event in events
                        )
                    )
        finally:
            for client, _extra_kwargs in clients:
                client.shutdown()

        backend = ExecutionBackendClient()
        try:
            backend._process_client._data_types = registry.data_types  # noqa: SLF001
            backend_events: list[dict] = []
            backend.subscribe(backend_events.append)
            self.assertEqual(
                backend.start_run(
                    "",
                    workspace.workspace_id,
                    {"runtime_snapshot": runtime_snapshot},
                    data_types=None,
                ),
                "",
            )
            self.assertTrue(
                any(
                    "authoritative data-type catalog" in str(event.get("error", ""))
                    for event in backend_events
                )
            )
        finally:
            backend.shutdown()

    def test_all_backend_start_paths_derive_agreement_from_supplied_catalog(
        self,
    ) -> None:
        registry = build_default_registry()
        catalog = registry.data_types
        expected_fingerprint, expected_revisions = catalog_agreement(catalog)
        stale_catalog = _revision_catalog("stale-v1")
        model = GraphModel()
        workspace = model.active_workspace
        model.add_node(
            workspace.workspace_id,
            "core.constant",
            "Constant",
            0,
            0,
            properties={"value": 1},
        )
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )

        process = ProcessExecutionClient()
        external = ExternalPythonExecutionClient()
        trusted = TrustedInProcessExecutionClient()
        clients = (process, external, trusted)
        try:
            process._data_types = stale_catalog  # noqa: SLF001
            process_commands = []
            with (
                patch.object(process, "_ensure_process"),
                patch.object(
                    process,
                    "_post_command",
                    side_effect=lambda command: process_commands.append(command)
                    or True,
                ),
            ):
                self.assertTrue(
                    process.start_run(
                        "",
                        workspace.workspace_id,
                        {"runtime_snapshot": runtime_snapshot},
                        data_types=catalog,
                    )
                )

            external._data_types = stale_catalog  # noqa: SLF001
            external_commands = []
            with (
                patch.object(external, "_ensure_process"),
                patch.object(
                    external,
                    "_post_command",
                    side_effect=lambda command: external_commands.append(command)
                    or True,
                ),
            ):
                self.assertTrue(
                    external.start_run(
                        "",
                        workspace.workspace_id,
                        {"runtime_snapshot": runtime_snapshot},
                        execution_backend=ExecutionBackendSelection(
                            backend_id=EXTERNAL_SUBPROCESS_BACKEND,
                            isolation="external_subprocess",
                            external_subprocess=True,
                            python_executable=sys.executable,
                        ),
                        data_types=catalog,
                    )
                )

            trusted._data_types = stale_catalog  # noqa: SLF001
            trusted_commands = []
            trusted._run_workflow_thread = (  # type: ignore[method-assign]  # noqa: SLF001
                lambda command, _generation: trusted_commands.append(command)
            )
            self.assertTrue(
                trusted.start_run(
                    "",
                    workspace.workspace_id,
                    {"runtime_snapshot": runtime_snapshot},
                    data_types=catalog,
                )
            )
            trusted._run_thread.join(timeout=2.0)  # noqa: SLF001

            commands = (
                *process_commands,
                *external_commands,
                *trusted_commands,
            )
            self.assertEqual(len(commands), 3)
            for command in commands:
                self.assertEqual(
                    command.catalog_fingerprint,
                    expected_fingerprint,
                )
                self.assertEqual(command.catalog_revisions, expected_revisions)
        finally:
            for client in clients:
                client.shutdown()

    def test_second_start_with_different_catalog_cannot_rebind_active_client(
        self,
    ) -> None:
        registry = build_default_registry()
        active_catalog = registry.data_types
        competing_catalog = _revision_catalog("competing-v2")
        model = GraphModel()
        workspace = model.active_workspace
        model.add_node(
            workspace.workspace_id,
            "core.constant",
            "Constant",
            0,
            0,
            properties={"value": 1},
        )
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )
        client = ProcessExecutionClient()
        events: list[dict] = []
        commands = []
        client.subscribe(events.append)

        try:
            with (
                patch.object(client, "_ensure_process"),
                patch.object(
                    client,
                    "_post_command",
                    side_effect=lambda command: commands.append(command) or True,
                ),
            ):
                active_run_id = client.start_run(
                    "",
                    workspace.workspace_id,
                    {"runtime_snapshot": runtime_snapshot},
                    data_types=active_catalog,
                )
                self.assertTrue(active_run_id)
                self.assertEqual(
                    client.start_run(
                        "",
                        workspace.workspace_id,
                        {"runtime_snapshot": runtime_snapshot},
                        data_types=competing_catalog,
                    ),
                    "",
                )

            self.assertIs(client._data_types, active_catalog)  # noqa: SLF001
            self.assertEqual(len(commands), 1)
            expected_fingerprint, expected_revisions = catalog_agreement(
                active_catalog
            )
            self.assertEqual(
                commands[0].catalog_fingerprint,
                expected_fingerprint,
            )
            self.assertEqual(commands[0].catalog_revisions, expected_revisions)
            self.assertTrue(
                any(
                    "already has an active run" in str(event.get("error", ""))
                    for event in events
                )
            )
        finally:
            if "active_run_id" in locals():
                client._release_start_run(active_run_id)  # noqa: SLF001
            client.shutdown()

    def test_post_terminal_catalog_change_recycles_each_backend_generation(
        self,
    ) -> None:
        registry = build_default_registry()
        first_catalog = _revision_catalog("generation-v1")
        second_catalog = _revision_catalog("generation-v2")
        model = GraphModel()
        workspace = model.active_workspace
        model.add_node(
            workspace.workspace_id,
            "core.constant",
            "Constant",
            0,
            0,
            properties={"value": 1},
        )
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )
        external_selection = ExecutionBackendSelection(
            backend_id=EXTERNAL_SUBPROCESS_BACKEND,
            isolation="external_subprocess",
            external_subprocess=True,
            python_executable=sys.executable,
        )

        for client in (
            ProcessExecutionClient(),
            ExternalPythonExecutionClient(),
            TrustedInProcessExecutionClient(),
        ):
            with self.subTest(client_type=type(client).__name__):
                commands = []
                if isinstance(client, TrustedInProcessExecutionClient):
                    client._run_workflow_thread = (  # type: ignore[method-assign]  # noqa: SLF001
                        lambda command, _generation: commands.append(command)
                    )
                    ensure_context = nullcontext()
                elif isinstance(client, ExternalPythonExecutionClient):
                    ensure_context = patch.object(client, "_ensure_process")
                else:
                    ensure_context = patch.object(client, "_ensure_process")
                try:
                    with (
                        ensure_context,
                        patch.object(
                            client,
                            "_post_command",
                            side_effect=lambda command: commands.append(command)
                            or True,
                        ),
                        patch.object(
                            client,
                            "_recycle_catalog_generation",
                        ) as recycle,
                    ):
                        first_run_id = client.start_run(
                            "",
                            workspace.workspace_id,
                            {"runtime_snapshot": runtime_snapshot},
                            execution_backend=(
                                external_selection
                                if isinstance(
                                    client,
                                    ExternalPythonExecutionClient,
                                )
                                else None
                            ),
                            data_types=first_catalog,
                        )
                        self.assertTrue(first_run_id)
                        if isinstance(client, TrustedInProcessExecutionClient):
                            client._run_thread.join(timeout=2.0)  # noqa: SLF001
                        client._release_start_run(first_run_id)  # noqa: SLF001

                        second_run_id = client.start_run(
                            "",
                            workspace.workspace_id,
                            {"runtime_snapshot": runtime_snapshot},
                            execution_backend=(
                                external_selection
                                if isinstance(
                                    client,
                                    ExternalPythonExecutionClient,
                                )
                                else None
                            ),
                            data_types=second_catalog,
                        )
                        self.assertTrue(second_run_id)
                        if isinstance(client, TrustedInProcessExecutionClient):
                            client._run_thread.join(timeout=2.0)  # noqa: SLF001

                    recycle.assert_called_once_with()
                    self.assertIs(client._data_types, second_catalog)  # noqa: SLF001
                    self.assertEqual(  # noqa: SLF001
                        client._catalog_generation_fingerprint,
                        second_catalog.fingerprint(),
                    )
                    client._release_start_run(second_run_id)  # noqa: SLF001
                finally:
                    client.shutdown()

    def test_catalog_recycle_failure_preserves_old_worker_and_catalog_pin(
        self,
    ) -> None:
        first_catalog = _revision_catalog("stubborn-v1")
        second_catalog = _revision_catalog("stubborn-v2")

        process_client = ProcessExecutionClient()
        process_worker = Mock()
        process_worker.is_alive.return_value = True
        process_client._process = process_worker  # noqa: SLF001

        external_client = ExternalPythonExecutionClient()
        external_worker = Mock()
        external_worker.poll.return_value = None
        external_worker.wait.side_effect = subprocess.TimeoutExpired(
            cmd="external-worker",
            timeout=1.5,
        )
        external_client._process = external_worker  # noqa: SLF001

        cases = (
            (process_client, process_worker, None),
            (external_client, external_worker, "_terminate_process"),
        )
        try:
            for client, worker, termination_method in cases:
                with self.subTest(client_type=type(client).__name__):
                    client._data_types = first_catalog  # noqa: SLF001
                    client._catalog_generation_fingerprint = (  # noqa: SLF001
                        first_catalog.fingerprint()
                    )
                    client._catalog_generation_token = 7  # noqa: SLF001
                    termination_context = (
                        patch.object(client, termination_method)
                        if termination_method is not None
                        else nullcontext()
                    )
                    with (
                        patch.object(client, "_post_command", return_value=True),
                        termination_context as terminate,
                    ):
                        with self.assertRaisesRegex(
                            DataTypeCatalogError,
                            "Failed to recycle the idle worker generation",
                        ):
                            client._prepare_start_run(  # noqa: SLF001
                                "run_stubborn",
                                "ws_stubborn",
                                second_catalog,
                            )
                    if termination_method is not None:
                        terminate.assert_called_once_with(worker)
                    self.assertIs(client._process, worker)  # noqa: SLF001
                    self.assertIs(client._data_types, first_catalog)  # noqa: SLF001
                    self.assertEqual(  # noqa: SLF001
                        client._catalog_generation_fingerprint,
                        first_catalog.fingerprint(),
                    )
                    self.assertEqual(client._catalog_generation_token, 7)  # noqa: SLF001
                    self.assertEqual(client._active_run_id, "")  # noqa: SLF001
        finally:
            process_client._process = None  # noqa: SLF001
            external_client._process = None  # noqa: SLF001
            process_client.shutdown()
            external_client.shutdown()

    def test_process_respawn_advances_generation_and_replaces_queues(
        self,
    ) -> None:
        class FakeProcess:
            def __init__(self) -> None:
                self.alive = False

            def start(self) -> None:
                self.alive = True

            def is_alive(self) -> bool:
                return self.alive

            def join(self, timeout=None) -> None:  # noqa: ANN001, ARG002
                return None

            def terminate(self) -> None:
                self.alive = False

            def kill(self) -> None:
                self.alive = False

        class FakeContext:
            def __init__(self) -> None:
                self.queues: list[queue.Queue] = []
                self.processes: list[FakeProcess] = []

            def Queue(self):  # noqa: N802, ANN201
                created_queue = queue.Queue()
                self.queues.append(created_queue)
                return created_queue

            def Process(self, **_kwargs):  # noqa: N802, ANN201
                created_process = FakeProcess()
                self.processes.append(created_process)
                return created_process

        client = ProcessExecutionClient()
        fake_context = FakeContext()
        client._ctx = fake_context  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        events: list[dict] = []
        client.subscribe(events.append)

        try:
            client._ensure_process()  # noqa: SLF001
            first_process = client._process  # noqa: SLF001
            first_command_queue = client._command_queue  # noqa: SLF001
            first_event_queue = client._event_queue  # noqa: SLF001
            first_listener = client._listener_thread  # noqa: SLF001
            client._active_run_id = "run_first"  # noqa: SLF001
            client._active_workspace_id = "ws_first"  # noqa: SLF001
            client._run_generation_tokens["run_first"] = 1  # noqa: SLF001
            first_process.alive = False

            request_id = client.open_viewer_session(
                "ws_viewer",
                "node_viewer",
            )

            self.assertEqual(client._catalog_generation_token, 2)  # noqa: SLF001
            self.assertEqual(client._physical_generation_token, 2)  # noqa: SLF001
            self.assertEqual(client._active_run_id, "")  # noqa: SLF001
            self.assertNotIn("run_first", client._run_generation_tokens)  # noqa: SLF001
            self.assertIsNot(client._process, first_process)  # noqa: SLF001
            self.assertIsNot(client._command_queue, first_command_queue)  # noqa: SLF001
            self.assertIsNot(client._event_queue, first_event_queue)  # noqa: SLF001
            self.assertFalse(first_listener.is_alive())
            self.assertTrue(
                any(
                    event.get("type") == "run_failed"
                    and event.get("run_id") == "run_first"
                    for event in events
                )
            )
            self.assertTrue(
                any(
                    event.get("type") == "run_state"
                    and event.get("run_id") == "run_first"
                    and event.get("reason") == "worker_terminated"
                    for event in events
                )
            )
            self.assertEqual(  # noqa: SLF001
                client._pending_viewer_requests[request_id].generation_token,
                2,
            )
            self.assertEqual(  # noqa: SLF001
                client._command_queue.get_nowait()["request_id"],
                request_id,
            )
        finally:
            client.shutdown()

    def test_first_catalog_pin_reuses_viewer_started_process_generation(
        self,
    ) -> None:
        client = ProcessExecutionClient()
        process = Mock()
        process.is_alive.return_value = True
        client._process = process  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        client._physical_generation_token = 1  # noqa: SLF001
        client._accepted_physical_generation_token = 1  # noqa: SLF001
        session_key = ("ws_viewer", "session_viewer")
        client._viewer_session_ids.add(session_key)  # noqa: SLF001
        client._viewer_session_generations[session_key] = 1  # noqa: SLF001

        try:
            self.assertTrue(
                client._prepare_start_run(  # noqa: SLF001
                    "run_first",
                    "ws_viewer",
                    _revision_catalog("first-pin"),
                )
            )
            self.assertEqual(client._catalog_generation_token, 1)  # noqa: SLF001
            self.assertEqual(  # noqa: SLF001
                client._run_generation_tokens["run_first"],
                1,
            )
            self.assertEqual(  # noqa: SLF001
                client._viewer_session_generations[session_key],
                1,
            )
            self.assertTrue(  # noqa: SLF001
                client._source_generation_is_current(1)
            )
        finally:
            client._process = None  # noqa: SLF001
            client.shutdown()

    def test_external_respawn_settles_dead_run_and_ignores_old_stdout(
        self,
    ) -> None:
        def external_process() -> Mock:
            process = Mock()
            process.returncode = None
            process.poll.side_effect = lambda: process.returncode
            process.stdout.readline.return_value = ""
            process.stderr.readline.return_value = ""

            def wait(*, timeout=None):  # noqa: ANN001, ARG001
                process.returncode = 0
                return 0

            process.wait.side_effect = wait
            process.terminate.side_effect = lambda: setattr(
                process,
                "returncode",
                -15,
            )
            process.kill.side_effect = lambda: setattr(
                process,
                "returncode",
                -9,
            )
            return process

        first_process = external_process()
        second_process = external_process()
        client = ExternalPythonExecutionClient()
        client._data_types = _revision_catalog("external-respawn")  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        events: list[dict] = []
        client.subscribe(events.append)

        try:
            with (
                patch.object(client, "_verify_runtime_available"),
                patch(
                    "ea_node_editor.execution.client.subprocess.Popen",
                    side_effect=(first_process, second_process),
                ),
            ):
                client._ensure_process("python-a")  # noqa: SLF001
                client._active_run_id = "run_second"  # noqa: SLF001
                client._active_workspace_id = "ws_second"  # noqa: SLF001
                client._run_generation_tokens["run_second"] = 1  # noqa: SLF001
                first_process.returncode = 1
                client._ensure_process("python-a")  # noqa: SLF001

            self.assertEqual(client._catalog_generation_token, 2)  # noqa: SLF001
            self.assertIs(client._process, second_process)  # noqa: SLF001
            self.assertEqual(client._active_run_id, "")  # noqa: SLF001
            self.assertNotIn("run_second", client._run_generation_tokens)  # noqa: SLF001
            self.assertTrue(
                any(
                    event.get("type") == "run_failed"
                    and event.get("run_id") == "run_second"
                    for event in events
                )
            )
            self.assertTrue(
                any(
                    event.get("type") == "run_state"
                    and event.get("run_id") == "run_second"
                    and event.get("reason")
                    == "external_python_worker_terminated"
                    for event in events
                )
            )
            events_before_stale_stdout = list(events)
            client._handle_stdout_line(  # noqa: SLF001
                json.dumps(
                    event_to_dict(
                        ViewerSessionOpenedEvent(
                            request_id="viewer_old",
                            workspace_id="ws_old",
                            session_id="session_old",
                        ),
                        catalog=client._data_types,  # noqa: SLF001
                    )
                ),
                generation_token=1,
            )
            self.assertEqual(events, events_before_stale_stdout)
            self.assertNotIn(  # noqa: SLF001
                ("ws_old", "session_old"),
                client._viewer_session_ids,
            )
        finally:
            client.shutdown()

    def test_external_executable_switch_rejects_live_viewer_generation(
        self,
    ) -> None:
        client = ExternalPythonExecutionClient()
        process = Mock()
        process.poll.return_value = None
        client._process = process  # noqa: SLF001
        client._python_executable = "python-a"  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        client._physical_generation_token = 1  # noqa: SLF001
        client._viewer_session_ids.add(("ws", "session"))  # noqa: SLF001

        try:
            with (
                patch.object(client, "_terminate_process") as terminate,
                self.assertRaisesRegex(
                    RuntimeError,
                    "viewer requests or sessions remain active",
                ),
            ):
                client._ensure_process("python-b")  # noqa: SLF001
            terminate.assert_not_called()
            self.assertIs(client._process, process)  # noqa: SLF001
            self.assertEqual(client._catalog_generation_token, 1)  # noqa: SLF001
        finally:
            client._process = None  # noqa: SLF001
            client.shutdown()

    def test_retiring_process_generation_cannot_mutate_viewer_state(
        self,
    ) -> None:
        client = ProcessExecutionClient()
        client._data_types = _revision_catalog("retiring-source")  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        client._physical_generation_token = 1  # noqa: SLF001
        client._accepted_physical_generation_token = 1  # noqa: SLF001
        retiring_events = queue.Queue()
        retiring_events.put(
            event_to_dict(
                ViewerSessionOpenedEvent(
                    request_id="viewer_retired",
                    workspace_id="ws_retired",
                    session_id="session_retired",
                ),
                catalog=client._data_types,  # noqa: SLF001
            )
        )
        retiring_events.put({"type": "__listener_shutdown__"})

        try:
            client._invalidate_physical_generation()  # noqa: SLF001
            client._event_listener(retiring_events, None, 1)  # noqa: SLF001
            self.assertNotIn(  # noqa: SLF001
                ("ws_retired", "session_retired"),
                client._viewer_session_ids,
            )
        finally:
            client.shutdown()

    def test_dead_process_health_cannot_clear_a_pending_successor_start(
        self,
    ) -> None:
        client = ProcessExecutionClient()
        process = Mock()
        process.is_alive.return_value = False
        client._process = process  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        client._physical_generation_token = 1  # noqa: SLF001
        client._accepted_physical_generation_token = 1  # noqa: SLF001
        client._active_run_id = "run_successor"  # noqa: SLF001
        client._start_run_pending_id = "run_successor"  # noqa: SLF001

        try:
            client._check_worker_health(process, 1)  # noqa: SLF001
            self.assertEqual(client._active_run_id, "run_successor")  # noqa: SLF001
            process.join.assert_not_called()
        finally:
            client._process = None  # noqa: SLF001
            client.shutdown()

    def test_process_timeout_revalidates_before_terminating_successor(
        self,
    ) -> None:
        client = ProcessExecutionClient()
        process = Mock()
        process.is_alive.return_value = True
        client._process = process  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        client._physical_generation_token = 1  # noqa: SLF001
        client._accepted_physical_generation_token = 1  # noqa: SLF001
        client._active_run_id = "run_old"  # noqa: SLF001
        client._active_workspace_id = "ws_old"  # noqa: SLF001
        client._active_node_id = "node_old"  # noqa: SLF001
        transition_started = threading.Event()

        def terminate_old_run() -> None:
            transition_started.set()
            client._terminate_timed_out_worker(  # noqa: SLF001
                process,
                run_id="run_old",
                workspace_id="ws_old",
                node_id="node_old",
                timeout_sec=1.0,
                generation_token=1,
            )

        try:
            with client._start_lock:  # noqa: SLF001
                monitor = threading.Thread(target=terminate_old_run)
                monitor.start()
                self.assertTrue(transition_started.wait(timeout=1.0))
                monitor.join(timeout=0.1)
                self.assertTrue(monitor.is_alive())
                with client._state_lock:  # noqa: SLF001
                    client._active_run_id = "run_successor"  # noqa: SLF001
                    client._active_workspace_id = "ws_successor"  # noqa: SLF001
                    client._start_run_pending_id = "run_successor"  # noqa: SLF001
                    client._active_node_id = ""  # noqa: SLF001
            monitor.join(timeout=1.0)
            self.assertFalse(monitor.is_alive())
            process.terminate.assert_not_called()
            self.assertEqual(client._active_run_id, "run_successor")  # noqa: SLF001
            self.assertEqual(  # noqa: SLF001
                client._accepted_physical_generation_token,
                1,
            )
        finally:
            client._process = None  # noqa: SLF001
            client.shutdown()

    def test_external_timeout_monitor_resnapshots_under_transition_lock(
        self,
    ) -> None:
        client = ExternalPythonExecutionClient()
        process = Mock()
        process.poll.return_value = None
        client._process = process  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        client._physical_generation_token = 1  # noqa: SLF001
        client._accepted_physical_generation_token = 1  # noqa: SLF001
        client._active_run_id = "run_old"  # noqa: SLF001
        client._active_node_id = "node_old"  # noqa: SLF001
        client._active_node_deadline = time.monotonic() - 1.0  # noqa: SLF001
        check_started = threading.Event()

        def check_health() -> None:
            check_started.set()
            client._check_worker_health()  # noqa: SLF001

        try:
            with (
                patch.object(client, "_terminate_process") as terminate,
                client._start_lock,  # noqa: SLF001
            ):
                monitor = threading.Thread(target=check_health)
                monitor.start()
                self.assertTrue(check_started.wait(timeout=1.0))
                client._active_run_id = "run_successor"  # noqa: SLF001
                client._active_node_id = ""  # noqa: SLF001
                client._active_node_deadline = 0.0  # noqa: SLF001
            monitor.join(timeout=1.0)
            self.assertFalse(monitor.is_alive())
            terminate.assert_not_called()
            self.assertEqual(client._active_run_id, "run_successor")  # noqa: SLF001
        finally:
            client._process = None  # noqa: SLF001
            client.shutdown()

    def test_trusted_catalog_recycle_resets_services_and_runtime_cache(
        self,
    ) -> None:
        registry = build_default_registry()
        first_catalog = _revision_catalog("trusted-v1")
        second_catalog = _revision_catalog("trusted-v2")
        model = GraphModel()
        workspace = model.active_workspace
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )
        services = WorkerServices()
        services.bind_data_types(first_catalog)
        client = TrustedInProcessExecutionClient(worker_services=services)
        client._data_types = first_catalog  # noqa: SLF001
        client._catalog_generation_fingerprint = (  # noqa: SLF001
            first_catalog.fingerprint()
        )
        client._run_workflow_thread = (  # type: ignore[method-assign]  # noqa: SLF001
            lambda _command, _generation: None
        )
        initial_generation = services.worker_generation

        try:
            with patch.object(
                DEFAULT_RUNTIME_PREPARATION_CACHE,
                "clear",
                wraps=DEFAULT_RUNTIME_PREPARATION_CACHE.clear,
            ) as clear_cache:
                run_id = client.start_run(
                    "",
                    workspace.workspace_id,
                    {"runtime_snapshot": runtime_snapshot},
                    data_types=second_catalog,
                )
                self.assertTrue(run_id)
                client._run_thread.join(timeout=2.0)  # noqa: SLF001

            clear_cache.assert_called_once_with()
            self.assertEqual(services.worker_generation, initial_generation + 1)
            self.assertIs(client._data_types, second_catalog)  # noqa: SLF001
            client._release_start_run(run_id)  # noqa: SLF001
        finally:
            client.shutdown()

    def test_trusted_reset_retires_viewers_and_allows_catalog_change(
        self,
    ) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )
        first_catalog = _revision_catalog("trusted-reset-v1")
        second_catalog = _revision_catalog("trusted-reset-v2")
        services = WorkerServices()
        services.bind_data_types(first_catalog)
        client = TrustedInProcessExecutionClient(worker_services=services)
        client._data_types = first_catalog  # noqa: SLF001
        client._catalog_generation_fingerprint = (  # noqa: SLF001
            first_catalog.fingerprint()
        )
        client._catalog_generation_token = 1  # noqa: SLF001
        client._accepted_physical_generation_token = 1  # noqa: SLF001
        client._active_run_id = "run_failed"  # noqa: SLF001
        client._active_workspace_id = workspace.workspace_id  # noqa: SLF001
        client._run_generation_tokens["run_failed"] = 1  # noqa: SLF001
        session_key = (workspace.workspace_id, "session_live")
        client._viewer_session_ids.add(session_key)  # noqa: SLF001
        client._viewer_session_generations[session_key] = 1  # noqa: SLF001
        pending_request = _PendingViewerRequest(
            request_id="viewer_pending",
            command="open_viewer_session",
            workspace_id=workspace.workspace_id,
            node_id="node_viewer",
            session_id="session_pending",
            generation_token=1,
        )
        client._pending_viewer_requests[pending_request.request_id] = (  # noqa: SLF001
            pending_request
        )
        terminal_received = threading.Event()
        events: list[dict] = []

        def record_event(event: dict) -> None:
            events.append(event)
            if (
                event.get("type") == "run_failed"
                and event.get("run_id") == "run_failed"
            ):
                terminal_received.set()

        client.subscribe(record_event)
        failed_command = Mock(
            run_id="run_failed",
            workspace_id=workspace.workspace_id,
        )
        initial_worker_generation = services.worker_generation

        try:
            with patch(
                "ea_node_editor.execution.client.run_workflow",
                side_effect=RuntimeError("trusted failure"),
            ):
                client._run_workflow_thread(  # noqa: SLF001
                    failed_command,
                    1,
                )
            self.assertTrue(terminal_received.wait(timeout=1.0))
            self.assertNotIn(session_key, client._viewer_session_ids)  # noqa: SLF001
            self.assertNotIn(  # noqa: SLF001
                session_key,
                client._viewer_session_generations,
            )
            self.assertNotIn(  # noqa: SLF001
                pending_request.request_id,
                client._pending_viewer_requests,
            )
            self.assertTrue(
                any(
                    event.get("type") == "viewer_session_failed"
                    and event.get("request_id") == pending_request.request_id
                    for event in events
                )
            )
            self.assertGreater(client._catalog_generation_token, 1)  # noqa: SLF001
            self.assertGreater(
                services.worker_generation,
                initial_worker_generation,
            )

            client._run_workflow_thread = (  # type: ignore[method-assign]  # noqa: SLF001
                lambda _command, _generation: None
            )
            successor_run_id = client.start_run(
                "",
                workspace.workspace_id,
                {"runtime_snapshot": runtime_snapshot},
                data_types=second_catalog,
            )
            self.assertTrue(successor_run_id)
            client._run_thread.join(timeout=1.0)  # noqa: SLF001
            client._release_start_run(successor_run_id)  # noqa: SLF001
        finally:
            client.shutdown()

    def test_trusted_listener_drops_retired_generation_events(
        self,
    ) -> None:
        client = TrustedInProcessExecutionClient()
        client._data_types = _revision_catalog("trusted-events")  # noqa: SLF001
        client._catalog_generation_token = 2  # noqa: SLF001
        client._accepted_physical_generation_token = 2  # noqa: SLF001
        client._active_run_id = "run_current"  # noqa: SLF001
        client._active_workspace_id = "ws_current"  # noqa: SLF001
        client._run_generation_tokens["run_current"] = 2  # noqa: SLF001
        events: list[dict] = []
        current_received = threading.Event()

        def record_event(event: dict) -> None:
            events.append(event)
            if (
                event.get("type") == "run_completed"
                and event.get("run_id") == "run_current"
            ):
                current_received.set()

        client.subscribe(record_event)

        try:
            client._event_queue.put(  # noqa: SLF001
                (
                    1,
                    event_to_dict(
                        ProtocolErrorEvent(
                            command="stale",
                            error="stale generation event",
                        )
                    ),
                )
            )
            client._event_queue.put(  # noqa: SLF001
                (
                    2,
                    event_to_dict(
                        RunCompletedEvent(
                            run_id="run_current",
                            workspace_id="ws_current",
                        )
                    ),
                )
            )

            self.assertTrue(current_received.wait(timeout=1.0))
            self.assertFalse(
                any(event.get("command") == "stale" for event in events)
            )
        finally:
            client.shutdown()

    def test_catalog_change_preserves_active_viewer_session_and_routing(
        self,
    ) -> None:
        registry = build_default_registry()
        first_catalog = _revision_catalog("viewer-v1")
        second_catalog = _revision_catalog("viewer-v2")
        model = GraphModel()
        workspace = model.active_workspace
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )
        backend = ExecutionBackendClient()
        client = backend._process_client  # noqa: SLF001
        client._data_types = first_catalog  # noqa: SLF001
        client._catalog_generation_fingerprint = (  # noqa: SLF001
            first_catalog.fingerprint()
        )
        process = Mock()
        process.is_alive.return_value = True
        client._process = process  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        client._physical_generation_token = 1  # noqa: SLF001
        client._accepted_physical_generation_token = 1  # noqa: SLF001
        session_key = (workspace.workspace_id, "session_retained")
        client._viewer_session_ids.add(session_key)  # noqa: SLF001
        backend._session_clients[session_key] = client  # noqa: SLF001
        backend._workspace_clients[workspace.workspace_id] = client  # noqa: SLF001
        events: list[dict] = []
        backend.subscribe(events.append)

        try:
            with (
                patch.object(client, "_recycle_catalog_generation") as recycle,
                patch.object(
                    client,
                    "update_viewer_session",
                    return_value="viewer_preserved",
                ) as update_viewer,
            ):
                self.assertEqual(
                    backend.start_run(
                        "",
                        workspace.workspace_id,
                        {"runtime_snapshot": runtime_snapshot},
                        data_types=second_catalog,
                    ),
                    "",
                )
                request_id = backend.update_viewer_session(
                    workspace.workspace_id,
                    "node_viewer",
                    "session_retained",
                )

            recycle.assert_not_called()
            self.assertEqual(request_id, "viewer_preserved")
            update_viewer.assert_called_once_with(
                workspace.workspace_id,
                "node_viewer",
                "session_retained",
            )
            self.assertIs(client._data_types, first_catalog)  # noqa: SLF001
            self.assertIn(session_key, client._viewer_session_ids)  # noqa: SLF001
            self.assertIs(  # noqa: SLF001
                backend._session_clients[session_key],
                client,
            )
            self.assertTrue(
                any(
                    "viewer requests or sessions" in str(event.get("error", ""))
                    for event in events
                )
            )
        finally:
            client._viewer_session_ids.clear()  # noqa: SLF001
            client._process = None  # noqa: SLF001
            backend.shutdown()

    def test_dead_worker_viewer_state_does_not_block_catalog_change(
        self,
    ) -> None:
        first_catalog = _revision_catalog("dead-viewer-v1")
        second_catalog = _revision_catalog("dead-viewer-v2")
        process_client = ProcessExecutionClient()
        process = Mock()
        process.is_alive.return_value = False
        process_client._process = process  # noqa: SLF001
        external_client = ExternalPythonExecutionClient()
        external_process = Mock()
        external_process.poll.return_value = 1
        external_client._process = external_process  # noqa: SLF001

        try:
            for client in (process_client, external_client):
                with self.subTest(client_type=type(client).__name__):
                    client._data_types = first_catalog  # noqa: SLF001
                    client._catalog_generation_fingerprint = (  # noqa: SLF001
                        first_catalog.fingerprint()
                    )
                    client._catalog_generation_token = 1  # noqa: SLF001
                    client._physical_generation_token = 1  # noqa: SLF001
                    client._accepted_physical_generation_token = 1  # noqa: SLF001
                    session_key = ("ws_dead", "session_dead")
                    client._viewer_session_ids.add(session_key)  # noqa: SLF001
                    client._viewer_session_generations[session_key] = 1  # noqa: SLF001

                    with patch.object(
                        client,
                        "_recycle_catalog_generation",
                    ) as recycle:
                        self.assertTrue(
                            client._prepare_start_run(  # noqa: SLF001
                                "run_after_dead_viewer",
                                "ws_dead",
                                second_catalog,
                            )
                        )

                    recycle.assert_called_once_with()
                    self.assertEqual(client._viewer_session_ids, set())  # noqa: SLF001
                    self.assertEqual(  # noqa: SLF001
                        client._viewer_session_generations,
                        {},
                    )
                    self.assertEqual(  # noqa: SLF001
                        client._accepted_physical_generation_token,
                        -1,
                    )
                    self.assertEqual(client._catalog_generation_token, 2)  # noqa: SLF001
                    self.assertEqual(  # noqa: SLF001
                        client._start_run_pending_id,
                        "run_after_dead_viewer",
                    )
                    client._release_start_run(  # noqa: SLF001
                        "run_after_dead_viewer"
                    )
        finally:
            process_client._process = None  # noqa: SLF001
            external_client._process = None  # noqa: SLF001
            process_client.shutdown()
            external_client.shutdown()

    def test_backend_routes_are_generation_owned_and_ignore_delayed_events(
        self,
    ) -> None:
        backend = ExecutionBackendClient()
        client = backend._process_client  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        session_key = ("ws_old", "session_old")
        backend._active_clients["run_old"] = client  # noqa: SLF001
        backend._run_clients["run_old"] = client  # noqa: SLF001
        backend._run_client_generations["run_old"] = 1  # noqa: SLF001
        backend._run_workspace_ids["run_old"] = "ws_old"  # noqa: SLF001
        backend._workspace_clients["ws_old"] = client  # noqa: SLF001
        backend._workspace_client_generations["ws_old"] = 1  # noqa: SLF001
        backend._session_clients[session_key] = client  # noqa: SLF001
        backend._session_client_generations[session_key] = 1  # noqa: SLF001
        events: list[dict] = []
        backend.subscribe(events.append)

        try:
            client._catalog_generation_token = 2  # noqa: SLF001
            with backend._active_lock:  # noqa: SLF001
                backend._forget_client_generation_locked(client)  # noqa: SLF001

            self.assertNotIn("run_old", backend._active_clients)  # noqa: SLF001
            self.assertNotIn("run_old", backend._run_clients)  # noqa: SLF001
            self.assertNotIn("ws_old", backend._workspace_clients)  # noqa: SLF001
            self.assertNotIn(session_key, backend._session_clients)  # noqa: SLF001

            backend._dispatch_client_event(  # noqa: SLF001
                client,
                {
                    "type": "viewer_session_opened",
                    "workspace_id": "ws_old",
                    "session_id": "session_old",
                },
                generation_token=1,
            )
            self.assertEqual(events, [])
            self.assertNotIn("ws_old", backend._workspace_clients)  # noqa: SLF001
            self.assertNotIn(session_key, backend._session_clients)  # noqa: SLF001
        finally:
            backend.shutdown()

    def test_failed_viewer_open_releases_only_the_requested_session_owner(
        self,
    ) -> None:
        backend = ExecutionBackendClient()
        client = backend._process_client  # noqa: SLF001
        retained_client = backend._trusted_client  # noqa: SLF001
        client._catalog_generation_token = 1  # noqa: SLF001
        failed_key = ("ws_viewer", "session_failed")
        live_key = ("ws_viewer", "session_live")
        request_id = "viewer_failed_open"

        try:
            backend._run_clients["run_retained"] = retained_client  # noqa: SLF001
            backend._run_client_generations["run_retained"] = 0  # noqa: SLF001
            backend._run_workspace_ids["run_retained"] = failed_key[0]  # noqa: SLF001
            backend._workspace_clients[failed_key[0]] = retained_client  # noqa: SLF001
            backend._workspace_client_generations[failed_key[0]] = 0  # noqa: SLF001
            backend._session_clients[failed_key] = retained_client  # noqa: SLF001
            backend._session_client_generations[failed_key] = 0  # noqa: SLF001
            backend._remember_requested_session_owner(  # noqa: SLF001
                client=client,
                workspace_id=failed_key[0],
                session_id=failed_key[1],
                request_id=request_id,
            )
            client._catalog_generation_token = 2  # noqa: SLF001
            backend._dispatch_client_event(  # noqa: SLF001
                client,
                {
                    "type": "viewer_session_failed",
                    "request_id": request_id,
                    "workspace_id": failed_key[0],
                    "session_id": failed_key[1],
                    "command": "open_viewer_session",
                },
                generation_token=2,
            )
            self.assertIs(backend._session_clients[failed_key], retained_client)  # noqa: SLF001
            self.assertIs(  # noqa: SLF001
                backend._workspace_clients[failed_key[0]],
                retained_client,
            )
            self.assertIs(  # noqa: SLF001
                backend._run_clients["run_retained"],
                retained_client,
            )

            backend._session_clients[live_key] = client  # noqa: SLF001
            backend._session_client_generations[live_key] = 2  # noqa: SLF001
            backend._workspace_clients[live_key[0]] = client  # noqa: SLF001
            backend._workspace_client_generations[live_key[0]] = 2  # noqa: SLF001
            backend._dispatch_client_event(  # noqa: SLF001
                client,
                {
                    "type": "viewer_session_failed",
                    "workspace_id": live_key[0],
                    "session_id": live_key[1],
                    "command": "update_viewer_session",
                },
                generation_token=2,
            )
            self.assertIs(backend._session_clients[live_key], client)  # noqa: SLF001
            self.assertIs(  # noqa: SLF001
                backend._workspace_clients[live_key[0]],
                client,
            )
        finally:
            backend.shutdown()

    def test_concurrent_failed_opens_restore_the_preexisting_session_owner(
        self,
    ) -> None:
        backend = ExecutionBackendClient()
        proposed_client = backend._process_client  # noqa: SLF001
        baseline_client = backend._trusted_client  # noqa: SLF001
        proposed_client._catalog_generation_token = 1  # noqa: SLF001
        session_key = ("ws_viewer", "session_shared")
        backend._session_clients[session_key] = baseline_client  # noqa: SLF001
        backend._session_client_generations[session_key] = 0  # noqa: SLF001

        try:
            for request_id in ("viewer_open_a", "viewer_open_b"):
                backend._remember_requested_session_owner(  # noqa: SLF001
                    client=proposed_client,
                    workspace_id=session_key[0],
                    session_id=session_key[1],
                    request_id=request_id,
                )

            backend._dispatch_client_event(  # noqa: SLF001
                proposed_client,
                {
                    "type": "viewer_session_failed",
                    "request_id": "viewer_open_a",
                    "workspace_id": session_key[0],
                    "session_id": session_key[1],
                    "command": "open_viewer_session",
                },
                generation_token=1,
            )
            self.assertIs(  # noqa: SLF001
                backend._session_clients[session_key],
                proposed_client,
            )

            backend._dispatch_client_event(  # noqa: SLF001
                proposed_client,
                {
                    "type": "viewer_session_failed",
                    "request_id": "viewer_open_b",
                    "workspace_id": session_key[0],
                    "session_id": session_key[1],
                    "command": "open_viewer_session",
                },
                generation_token=1,
            )
            self.assertIs(  # noqa: SLF001
                backend._session_clients[session_key],
                baseline_client,
            )
        finally:
            backend.shutdown()

    def test_stale_generation_run_controls_are_not_dispatched(
        self,
    ) -> None:
        backend = ExecutionBackendClient()
        client = backend._process_client  # noqa: SLF001
        client._catalog_generation_token = 2  # noqa: SLF001
        backend._active_clients["run_stale"] = client  # noqa: SLF001
        backend._run_clients["run_stale"] = client  # noqa: SLF001
        backend._run_client_generations["run_stale"] = 1  # noqa: SLF001
        backend._run_workspace_ids["run_stale"] = "ws_stale"  # noqa: SLF001

        try:
            with (
                patch.object(client, "pause_run") as pause,
                patch.object(client, "resume_run") as resume,
                patch.object(client, "stop_run") as stop,
            ):
                backend.pause_run("run_stale")
                backend.resume_run("run_stale")
                backend.stop_run("run_stale")
            pause.assert_not_called()
            resume.assert_not_called()
            stop.assert_not_called()
            self.assertNotIn("run_stale", backend._active_clients)  # noqa: SLF001
            self.assertNotIn("run_stale", backend._run_clients)  # noqa: SLF001
        finally:
            backend.shutdown()

    def test_stale_viewer_controls_do_not_fall_through_to_successor(
        self,
    ) -> None:
        backend = ExecutionBackendClient()
        stale_client = backend._process_client  # noqa: SLF001
        successor = backend._trusted_client  # noqa: SLF001
        stale_client._catalog_generation_token = 2  # noqa: SLF001
        controls = (
            ("update_viewer_session", {}),
            ("close_viewer_session", {}),
            ("materialize_viewer_data", {}),
            ("query_viewer_session", {"query_type": "camera"}),
        )

        try:
            for route_kind in ("run", "session", "workspace"):
                for method_name, extra_kwargs in controls:
                    with self.subTest(
                        route_kind=route_kind,
                        method_name=method_name,
                    ):
                        backend._clear_viewer_owners()  # noqa: SLF001
                        backend._active_clients["run_successor"] = successor  # noqa: SLF001
                        kwargs = dict(extra_kwargs)
                        if route_kind == "run":
                            backend._run_clients["run_stale"] = stale_client  # noqa: SLF001
                            backend._run_client_generations["run_stale"] = 1  # noqa: SLF001
                            kwargs["run_id"] = "run_stale"
                        elif route_kind == "session":
                            session_key = ("ws_stale", "session_stale")
                            backend._session_clients[session_key] = stale_client  # noqa: SLF001
                            backend._session_client_generations[session_key] = 1  # noqa: SLF001
                        else:
                            backend._workspace_clients["ws_stale"] = stale_client  # noqa: SLF001
                            backend._workspace_client_generations["ws_stale"] = 1  # noqa: SLF001

                        with (
                            patch.object(stale_client, method_name) as stale_call,
                            patch.object(successor, method_name) as successor_call,
                        ):
                            result = getattr(backend, method_name)(
                                "ws_stale",
                                "node_stale",
                                "session_stale",
                                **kwargs,
                            )

                        self.assertEqual(result, "")
                        stale_call.assert_not_called()
                        successor_call.assert_not_called()

            backend._clear_viewer_owners()  # noqa: SLF001
            session_key = ("ws_stale", "session_stale")
            backend._session_clients[session_key] = successor  # noqa: SLF001
            backend._session_client_generations[session_key] = 1  # noqa: SLF001
            with patch.object(backend._process_client, "query_viewer_session") as query:  # noqa: SLF001
                self.assertEqual(
                    backend.query_viewer_session(
                        "ws_stale",
                        "node_stale",
                        "session_stale",
                        query_type="camera",
                    ),
                    "",
                )
            query.assert_not_called()
        finally:
            backend.shutdown()

    def test_unowned_viewer_open_keeps_active_and_default_fallbacks(
        self,
    ) -> None:
        backend = ExecutionBackendClient()
        active_client = backend._trusted_client  # noqa: SLF001

        try:
            backend._active_clients["run_active"] = active_client  # noqa: SLF001
            with patch.object(
                active_client,
                "open_viewer_session",
                return_value="viewer_active",
            ) as active_open:
                self.assertEqual(
                    backend.open_viewer_session(
                        "ws_active",
                        "node_active",
                        session_id="session_active",
                    ),
                    "viewer_active",
                )
            active_open.assert_called_once()

            backend._clear_viewer_owners()  # noqa: SLF001
            backend._process_client._catalog_generation_token = 2  # noqa: SLF001
            backend._workspace_clients["ws_stale"] = backend._process_client  # noqa: SLF001
            backend._workspace_client_generations["ws_stale"] = 1  # noqa: SLF001
            backend._active_clients["run_active"] = active_client  # noqa: SLF001
            with patch.object(
                active_client,
                "open_viewer_session",
                return_value="viewer_after_stale",
            ) as stale_fallback_open:
                self.assertEqual(
                    backend.open_viewer_session(
                        "ws_stale",
                        "node_stale",
                        session_id="session_stale",
                    ),
                    "viewer_after_stale",
                )
            stale_fallback_open.assert_called_once()

            backend._clear_viewer_owners()  # noqa: SLF001
            with patch.object(
                backend._process_client,  # noqa: SLF001
                "open_viewer_session",
                return_value="viewer_default",
            ) as default_open:
                self.assertEqual(
                    backend.open_viewer_session(
                        "ws_default",
                        "node_default",
                        session_id="session_default",
                    ),
                    "viewer_default",
                )
            default_open.assert_called_once()
        finally:
            backend.shutdown()

    def test_newer_open_success_survives_older_late_success(self) -> None:
        backend = ExecutionBackendClient()
        older_client = backend._process_client  # noqa: SLF001
        newer_client = backend._trusted_client  # noqa: SLF001
        baseline_client = backend._external_python_client  # noqa: SLF001
        older_client._catalog_generation_token = 1  # noqa: SLF001
        newer_client._catalog_generation_token = 1  # noqa: SLF001
        baseline_client._catalog_generation_token = 1  # noqa: SLF001
        session_key = ("ws_viewer", "session_shared")
        backend._session_clients[session_key] = baseline_client  # noqa: SLF001
        backend._session_client_generations[session_key] = 1  # noqa: SLF001
        backend._workspace_clients[session_key[0]] = baseline_client  # noqa: SLF001
        backend._workspace_client_generations[session_key[0]] = 1  # noqa: SLF001

        try:
            backend._remember_requested_session_owner(  # noqa: SLF001
                client=older_client,
                workspace_id=session_key[0],
                session_id=session_key[1],
                request_id="viewer_open_older",
            )
            backend._remember_requested_session_owner(  # noqa: SLF001
                client=newer_client,
                workspace_id=session_key[0],
                session_id=session_key[1],
                request_id="viewer_open_newer",
            )

            backend._dispatch_client_event(  # noqa: SLF001
                newer_client,
                {
                    "type": "viewer_session_opened",
                    "request_id": "viewer_open_newer",
                    "workspace_id": session_key[0],
                    "session_id": session_key[1],
                },
                generation_token=1,
            )
            self.assertIs(  # noqa: SLF001
                backend._session_clients[session_key],
                newer_client,
            )
            self.assertIs(  # noqa: SLF001
                backend._workspace_clients[session_key[0]],
                newer_client,
            )

            backend._dispatch_client_event(  # noqa: SLF001
                older_client,
                {
                    "type": "viewer_session_opened",
                    "request_id": "viewer_open_older",
                    "workspace_id": session_key[0],
                    "session_id": session_key[1],
                },
                generation_token=1,
            )
            self.assertIs(  # noqa: SLF001
                backend._session_clients[session_key],
                newer_client,
            )
            self.assertIs(  # noqa: SLF001
                backend._workspace_clients[session_key[0]],
                newer_client,
            )
            self.assertEqual(backend._provisional_viewer_routes, {})  # noqa: SLF001
            self.assertEqual(backend._provisional_request_sessions, {})  # noqa: SLF001
        finally:
            backend.shutdown()

    def test_backend_routes_post_terminal_viewer_sessions_to_run_owners(
        self,
    ) -> None:
        process = _RoutingClient("process")
        external = _RoutingClient("external")
        trusted = _RoutingClient("trusted")
        backend = object.__new__(ExecutionBackendClient)
        backend._process_client = process  # noqa: SLF001
        backend._external_python_client = external  # noqa: SLF001
        backend._trusted_client = trusted  # noqa: SLF001
        backend._callbacks = []  # noqa: SLF001
        backend._active_lock = threading.Lock()  # noqa: SLF001
        backend._active_clients = {  # noqa: SLF001
            "run_external": external,
            "run_trusted": trusted,
        }
        backend._run_clients = dict(backend._active_clients)  # noqa: SLF001
        backend._run_workspace_ids = {  # noqa: SLF001
            "run_external": "ws_shared",
            "run_trusted": "ws_trusted",
        }
        backend._workspace_clients = {  # noqa: SLF001
            "ws_shared": external,
            "ws_trusted": trusted,
        }
        backend._session_clients = {}  # noqa: SLF001
        backend._terminal_run_ids_seen = set()  # noqa: SLF001

        backend._dispatch_client_event(  # noqa: SLF001
            external,
            {
                "type": "run_completed",
                "run_id": "run_external",
                "workspace_id": "ws_shared",
            },
        )
        backend._dispatch_client_event(  # noqa: SLF001
            trusted,
            {
                "type": "run_completed",
                "run_id": "run_trusted",
                "workspace_id": "ws_trusted",
            },
        )
        self.assertEqual(backend._active_clients, {})  # noqa: SLF001

        backend.open_viewer_session(
            "ws_shared",
            "node_external",
            session_id="session_external",
        )
        backend.open_viewer_session(
            "ws_trusted",
            "node_trusted",
            session_id="session_trusted",
        )
        backend.update_viewer_session(
            "ws_shared",
            "node_external",
            "session_external",
        )
        backend.query_viewer_session(
            "ws_shared",
            "node_external",
            "session_external",
            query_type="camera",
        )
        backend.update_viewer_session(
            "ws_trusted",
            "node_trusted",
            "session_trusted",
        )
        backend.query_viewer_session(
            "ws_trusted",
            "node_trusted",
            "session_trusted",
            query_type="camera",
        )

        self.assertEqual(
            [call[0] for call in external.calls],
            ["open", "update", "query"],
        )
        self.assertEqual(
            [call[0] for call in trusted.calls],
            ["open", "update", "query"],
        )
        self.assertEqual(process.calls, [])

        # A run ID disambiguates concurrent ownership even if workspaces collide.
        backend._run_clients["run_trusted_shared"] = trusted  # noqa: SLF001
        backend._run_workspace_ids["run_trusted_shared"] = "ws_shared"  # noqa: SLF001
        backend.open_viewer_session(
            "ws_shared",
            "node_trusted_shared",
            session_id="session_trusted_shared",
            run_id="run_trusted_shared",
        )
        self.assertEqual(trusted.calls[-1][0], "open")

        backend._dispatch_client_event(  # noqa: SLF001
            external,
            {
                "type": "viewer_session_closed",
                "workspace_id": "ws_shared",
                "session_id": "session_external",
            },
        )
        self.assertNotIn(
            ("ws_shared", "session_external"),
            backend._session_clients,  # noqa: SLF001
        )

    def test_backend_routes_same_session_id_by_workspace_and_run_precedence(
        self,
    ) -> None:
        process = _RoutingClient("process")
        external = _RoutingClient("external")
        trusted = _RoutingClient("trusted")
        backend = object.__new__(ExecutionBackendClient)
        backend._process_client = process  # noqa: SLF001
        backend._external_python_client = external  # noqa: SLF001
        backend._trusted_client = trusted  # noqa: SLF001
        backend._callbacks = []  # noqa: SLF001
        backend._active_lock = threading.Lock()  # noqa: SLF001
        backend._active_clients = {}  # noqa: SLF001
        backend._run_clients = {  # noqa: SLF001
            "run_external": external,
            "run_trusted": trusted,
        }
        backend._run_workspace_ids = {  # noqa: SLF001
            "run_external": "ws_external",
            "run_trusted": "ws_trusted",
        }
        backend._workspace_clients = {  # noqa: SLF001
            "ws_external": external,
            "ws_trusted": trusted,
        }
        backend._session_clients = {}  # noqa: SLF001
        backend._terminal_run_ids_seen = set()  # noqa: SLF001

        backend.open_viewer_session(
            "ws_external",
            "node_external",
            session_id="shared_session",
        )
        backend.open_viewer_session(
            "ws_trusted",
            "node_trusted",
            session_id="shared_session",
        )
        backend.update_viewer_session(
            "ws_external",
            "node_external",
            "shared_session",
        )
        backend.query_viewer_session(
            "ws_trusted",
            "node_trusted",
            "shared_session",
            query_type="camera",
        )
        self.assertEqual(
            [call[0] for call in external.calls],
            ["open", "update"],
        )
        self.assertEqual(
            [call[0] for call in trusted.calls],
            ["open", "query"],
        )

        # An explicit run owner wins even when the composite session points
        # at another backend.
        backend.update_viewer_session(
            "ws_external",
            "node_external",
            "shared_session",
            run_id="run_trusted",
        )
        self.assertEqual(trusted.calls[-1][0], "update")

        backend.close_viewer_session(
            "ws_external",
            "node_external",
            "shared_session",
        )
        backend._dispatch_client_event(  # noqa: SLF001
            external,
            {
                "type": "viewer_session_closed",
                "workspace_id": "ws_external",
                "session_id": "shared_session",
            },
        )
        self.assertNotIn(
            ("ws_external", "shared_session"),
            backend._session_clients,  # noqa: SLF001
        )
        self.assertIn(
            ("ws_trusted", "shared_session"),
            backend._session_clients,  # noqa: SLF001
        )
        backend.query_viewer_session(
            "ws_trusted",
            "node_trusted",
            "shared_session",
            query_type="camera",
        )
        self.assertEqual(trusted.calls[-1][0], "query")
        self.assertEqual(process.calls, [])

    def test_backend_bounds_completed_run_owners_with_open_session(self) -> None:
        process = _RoutingClient("process")
        external = _RoutingClient("external")
        trusted = _RoutingClient("trusted")
        backend = object.__new__(ExecutionBackendClient)
        backend._process_client = process  # noqa: SLF001
        backend._external_python_client = external  # noqa: SLF001
        backend._trusted_client = trusted  # noqa: SLF001
        backend._callbacks = []  # noqa: SLF001
        backend._active_lock = threading.Lock()  # noqa: SLF001
        backend._active_clients = {}  # noqa: SLF001
        backend._run_clients = {}  # noqa: SLF001
        backend._run_workspace_ids = {}  # noqa: SLF001
        backend._workspace_clients = {"ws_shared": external}  # noqa: SLF001
        backend._session_clients = {  # noqa: SLF001
            ("ws_shared", "live_session"): external,
        }
        backend._terminal_run_ids_seen = set()  # noqa: SLF001

        for index in range(70):
            run_id = f"run_{index:03d}"
            owner = external if index < 69 else trusted
            backend._active_clients[run_id] = owner  # noqa: SLF001
            backend._run_clients[run_id] = owner  # noqa: SLF001
            backend._run_workspace_ids[run_id] = "ws_shared"  # noqa: SLF001
            backend._workspace_clients["ws_shared"] = owner  # noqa: SLF001
            backend._dispatch_client_event(  # noqa: SLF001
                owner,
                {
                    "type": "run_completed",
                    "run_id": run_id,
                    "workspace_id": "ws_shared",
                },
            )

        self.assertLessEqual(
            len(backend._run_clients),  # noqa: SLF001
            backend._RETAINED_VIEWER_RUN_LIMIT,  # noqa: SLF001
        )
        self.assertLessEqual(
            len(backend._run_workspace_ids),  # noqa: SLF001
            backend._RETAINED_VIEWER_RUN_LIMIT,  # noqa: SLF001
        )
        backend.query_viewer_session(
            "ws_shared",
            "node",
            "live_session",
            query_type="camera",
        )
        self.assertEqual(external.calls[-1][0], "query")
        backend.open_viewer_session("ws_shared", "node")
        self.assertEqual(trusted.calls[-1][0], "open")

        backend._dispatch_client_event(  # noqa: SLF001
            external,
            {
                "type": "viewer_session_closed",
                "workspace_id": "ws_shared",
                "session_id": "live_session",
            },
        )
        self.assertEqual(backend._session_clients, {})  # noqa: SLF001
        self.assertEqual(backend._run_clients, {})  # noqa: SLF001
        self.assertEqual(backend._run_workspace_ids, {})  # noqa: SLF001
        self.assertEqual(backend._workspace_clients, {})  # noqa: SLF001

        backend._run_clients["run_after_close"] = trusted  # noqa: SLF001
        backend._run_workspace_ids["run_after_close"] = "ws_after"  # noqa: SLF001
        backend._workspace_clients["ws_after"] = trusted  # noqa: SLF001
        backend._session_clients[("ws_after", "session_after")] = trusted  # noqa: SLF001
        backend.shutdown()
        self.assertEqual(backend._run_clients, {})  # noqa: SLF001
        self.assertEqual(backend._run_workspace_ids, {})  # noqa: SLF001
        self.assertEqual(backend._workspace_clients, {})  # noqa: SLF001
        self.assertEqual(backend._session_clients, {})  # noqa: SLF001


class ProcessExecutionClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = ProcessExecutionClient()
        self.data_types = build_default_registry().data_types
        # Viewer-only tests emulate a catalog retained from their owning run.
        self.client._data_types = self.data_types  # noqa: SLF001
        self._events: list[dict] = []
        self._events_lock = threading.Lock()
        self.client.subscribe(self._on_event)

    def tearDown(self) -> None:
        self.client.shutdown()

    def _wait_for_event(self, predicate, timeout: float = 6.0) -> dict | None:  # noqa: ANN001
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._events_lock:
                for event in self._events:
                    if predicate(event):
                        return event
            time.sleep(0.05)
        return None

    def _on_event(self, event: dict) -> None:
        with self._events_lock:
            self._events.append(dict(event))

    def test_current_trigger_capture_roundtrips_without_running_upstream(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        source = model.add_node(
            workspace.workspace_id,
            "core.constant",
            "Source",
            0,
            0,
            properties={"value": "upstream"},
        )
        trigger = model.add_node(
            workspace.workspace_id,
            "core.trigger",
            "Trigger",
            100,
            0,
        )
        model.add_edge(
            workspace.workspace_id, source.node_id, "value", trigger.node_id, "input"
        )
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=build_default_registry(),
        )
        captured = SettledPortResult(
            status="value",
            value=DataTree.from_item("captured"),
        )

        run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace.workspace_id,
            trigger={"kind": "trigger", "runtime_snapshot": runtime_snapshot},
            target_node_ids=(trigger.node_id,),
            trigger_captures={trigger.node_id: captured},
            clicked_trigger_node_id=trigger.node_id,
            data_types=self.data_types,
        )
        published = self._wait_for_event(
            lambda event: (
                event.get("type") == "trigger_published"
                and event.get("run_id") == run_id
            ),
            timeout=30.0,
        )
        completed = self._wait_for_event(
            lambda event: (
                event.get("type") == "run_completed" and event.get("run_id") == run_id
            ),
            timeout=12.0,
        )

        self.assertIsNotNone(published)
        self.assertIsNotNone(completed)
        if published is None:
            self.fail("trigger publication was not received")
        self.assertEqual(
            deserialize_runtime_value(published["result"]["value"]),
            DataTree.from_item("captured"),
        )
        with self._events_lock:
            self.assertFalse(
                any(
                    event.get("type") == "node_started"
                    and event.get("run_id") == run_id
                    and event.get("node_id") == source.node_id
                    for event in self._events
                )
            )

    @staticmethod
    def _build_runtime_snapshot(
        *,
        with_sleep_script: bool = False,
        workflow_python_path: str = "",
    ):
        model = GraphModel()
        workspace = model.active_workspace
        if with_sleep_script:
            script = model.add_node(
                workspace.workspace_id,
                "core.python_script",
                "Script",
                100,
                0,
                properties={"script": "import time\ntime.sleep(2)\nresult = 1"},
            )
        else:
            logger = model.add_node(
                workspace.workspace_id,
                "core.logger",
                "Logger",
                100,
                0,
                properties={"message": "ok"},
            )

        if workflow_python_path:
            model.project.metadata["workflow_settings"] = {
                "environment": {"python_path": workflow_python_path}
            }
        registry = build_default_registry()
        return workspace.workspace_id, build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )

    @staticmethod
    def _build_script_runtime_snapshot(
        script_source: str,
        *,
        timeout_sec: float = 0.0,
        workflow_python_path: str = "",
    ):
        model = GraphModel()
        workspace = model.active_workspace
        script = model.add_node(
            workspace.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
            properties={"script": script_source, "timeout_sec": timeout_sec},
        )
        if workflow_python_path:
            model.project.metadata["workflow_settings"] = {
                "environment": {"python_path": workflow_python_path}
            }
        registry = build_default_registry()
        return (
            workspace.workspace_id,
            script.node_id,
            build_runtime_snapshot(
                model.project,
                workspace_id=workspace.workspace_id,
                registry=registry,
            ),
        )

    def test_signal_plot_image_value_survives_real_process_queue_transport(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        source = model.add_node(
            workspace.workspace_id,
            "data.number_slider",
            "Value",
            0,
            0,
            properties={"value": 5.0},
        )
        signal = model.add_node(
            workspace.workspace_id,
            "plot.signal",
            "Signal Plot",
            220,
            0,
            properties={"marker_shapes": [0]},
        )
        model.add_edge(workspace.workspace_id, source.node_id, "value", signal.node_id, "values")
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )
        run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace.workspace_id,
            trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
            target_node_ids=(signal.node_id,),
            data_types=registry.data_types,
        )
        settled = self._wait_for_event(
            lambda event: event.get("type") == "node_settled"
            and event.get("run_id") == run_id
            and event.get("node_id") == signal.node_id,
            timeout=30.0,
        )
        completed = self._wait_for_event(
            lambda event: event.get("type") == "run_completed" and event.get("run_id") == run_id,
            timeout=12.0,
        )
        self.assertIsNotNone(settled)
        self.assertIsNotNone(completed)
        if settled is None:
            self.fail("Signal Plot node_settled event was not received")
        image_tree = deserialize_runtime_value(
            settled["outputs"]["image"]["value"],
            catalog=registry.data_types,
        )
        image = image_tree.branches[0][1][0]
        self.assertIs(type(image), ImageValue)
        self.assertEqual((image.width, image.height), (600, 400))

    def test_invalid_worker_payload_emits_protocol_error(self) -> None:
        self.client._event_queue.put("not-a-dict")  # noqa: SLF001

        event = self._wait_for_event(
            lambda payload: (
                payload.get("type") == "protocol_error"
                and "non-dictionary event" in str(payload.get("error", ""))
            ),
            timeout=3.0,
        )

        self.assertIsNotNone(event)

    def test_client_listener_preserves_structured_artifact_ref_event_payloads(
        self,
    ) -> None:
        self.client._event_queue.put(
            event_to_dict(
                NodeSettledEvent(
                    run_id="run_artifact",
                    workspace_id="ws_main",
                    node_id="node_process",
                    outputs={
                        "stdout": SettledPortResult(
                            status="value",
                            value=DataTree.from_item(
                                RuntimeArtifactRef.staged(
                                    "stored_stdout",
                                    data_type_id=PATH_DATA_TYPE_ID,
                                    schema_version=1,
                                    format="txt",
                                    size_bytes=0,
                                    sha256="0" * 64,
                                    provenance="corex.test.fixture",
                                )
                            ),
                        ),
                        "preview": SettledPortResult(
                            status="value",
                            value=DataTree.from_item("ok"),
                        ),
                    },
                ),
                catalog=self.client._data_types,  # noqa: SLF001
            )
        )  # noqa: SLF001

        event = self._wait_for_event(
            lambda payload: (
                payload.get("type") == "node_settled"
                and payload.get("run_id") == "run_artifact"
            ),
            timeout=3.0,
        )

        self.assertIsNotNone(event)
        if event is None:
            self.fail("node_settled event was not received")
        stdout_tree = deserialize_runtime_value(
            event["outputs"]["stdout"]["value"],
            catalog=self.client._data_types,  # noqa: SLF001
        )
        preview_tree = deserialize_runtime_value(event["outputs"]["preview"]["value"])
        self.assertEqual(
            stdout_tree,
            DataTree.from_item(
                RuntimeArtifactRef.staged(
                    "stored_stdout",
                    data_type_id=PATH_DATA_TYPE_ID,
                    schema_version=1,
                    format="txt",
                    size_bytes=0,
                    sha256="0" * 64,
                    provenance="corex.test.fixture",
                )
            ),
        )
        self.assertEqual(preview_tree, DataTree.from_item("ok"))

    def test_persistent_node_elapsed_time_protocol_client_listener_preserves_timing_fields(
        self,
    ) -> None:
        self.client._event_queue.put(
            event_to_dict(
                NodeStartedEvent(
                    run_id="run_timing",
                    workspace_id="ws_main",
                    node_id="node_timing",
                    started_at_epoch_ms=1234.5,
                )
            )
        )  # noqa: SLF001
        self.client._event_queue.put(
            event_to_dict(
                NodeSettledEvent(
                    run_id="run_timing",
                    workspace_id="ws_main",
                    node_id="node_timing",
                    elapsed_ms=45.25,
                    outputs={
                        "status": SettledPortResult(
                            status="value",
                            value=DataTree.from_item("ok"),
                        )
                    },
                )
            )
        )  # noqa: SLF001

        started = self._wait_for_event(
            lambda payload: (
                payload.get("type") == "node_started"
                and payload.get("run_id") == "run_timing"
            ),
            timeout=3.0,
        )
        completed = self._wait_for_event(
            lambda payload: (
                payload.get("type") == "node_settled"
                and payload.get("run_id") == "run_timing"
            ),
            timeout=3.0,
        )

        self.assertIsNotNone(started)
        self.assertIsNotNone(completed)
        if started is None or completed is None:
            self.fail("timing events were not received")
        self.assertEqual(started["started_at_epoch_ms"], 1234.5)
        self.assertEqual(completed["elapsed_ms"], 45.25)
        self.assertEqual(completed["outputs"]["status"]["status"], "value")

    def test_persistent_node_elapsed_time_protocol_client_listener_defaults_legacy_timing_fields(
        self,
    ) -> None:
        self.client._event_queue.put(
            {
                "type": "node_started",
                "run_id": "run_legacy",
                "workspace_id": "ws_main",
                "node_id": "node_legacy",
            }
        )  # noqa: SLF001
        legacy_settled = event_to_dict(
            NodeSettledEvent(
                run_id="run_legacy",
                workspace_id="ws_main",
                node_id="node_legacy",
                outputs={"status": SettledPortResult(status="empty")},
            )
        )
        legacy_settled.pop("elapsed_ms")
        self.client._event_queue.put(legacy_settled)  # noqa: SLF001

        started = self._wait_for_event(
            lambda payload: (
                payload.get("type") == "node_started"
                and payload.get("run_id") == "run_legacy"
            ),
            timeout=3.0,
        )
        completed = self._wait_for_event(
            lambda payload: (
                payload.get("type") == "node_settled"
                and payload.get("run_id") == "run_legacy"
            ),
            timeout=3.0,
        )

        self.assertIsNotNone(started)
        self.assertIsNotNone(completed)
        if started is None or completed is None:
            self.fail("legacy timing events were not received")
        self.assertEqual(started["started_at_epoch_ms"], 0.0)
        self.assertEqual(completed["elapsed_ms"], 0.0)
        self.assertEqual(completed["outputs"]["status"]["status"], "empty")

    def test_worker_death_emits_failure_and_next_run_recovers(self) -> None:
        workspace_id, long_runtime_snapshot = self._build_runtime_snapshot(
            with_sleep_script=True
        )
        first_run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace_id,
            trigger={"kind": "manual", "runtime_snapshot": long_runtime_snapshot},
            data_types=self.data_types,
        )
        self.assertTrue(first_run_id)

        started = self._wait_for_event(
            lambda event: (
                event.get("type") == "run_started"
                and event.get("run_id") == first_run_id
            ),
            timeout=12.0,
        )
        self.assertIsNotNone(started)

        process = self.client._process  # noqa: SLF001
        self.assertIsNotNone(process)
        if process is not None:
            process.terminate()
            process.join(timeout=1.0)

        failed = self._wait_for_event(
            lambda event: (
                event.get("type") == "run_failed"
                and event.get("run_id") == first_run_id
                and bool(event.get("fatal"))
            ),
            timeout=5.0,
        )
        self.assertIsNotNone(failed)

        recovery_workspace_id, recovery_runtime_snapshot = self._build_runtime_snapshot(
            with_sleep_script=False
        )
        second_run_id = self.client.start_run(
            project_path="",
            workspace_id=recovery_workspace_id,
            trigger={"kind": "manual", "runtime_snapshot": recovery_runtime_snapshot},
            data_types=self.data_types,
        )
        self.assertTrue(second_run_id)
        self.assertNotEqual(first_run_id, second_run_id)

        completed = self._wait_for_event(
            lambda event: (
                event.get("type") == "run_completed"
                and event.get("run_id") == second_run_id
            ),
            timeout=12.0,
        )
        self.assertIsNotNone(completed)

    def test_worker_death_emits_failure_with_running_python_script_node_id(
        self,
    ) -> None:
        workspace_id, script_id, runtime_snapshot = self._build_script_runtime_snapshot(
            "import os, time\ntime.sleep(0.2)\nos._exit(17)"
        )
        run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace_id,
            trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
            data_types=self.data_types,
        )
        self.assertTrue(run_id)

        started = self._wait_for_event(
            lambda event: (
                event.get("type") == "node_started"
                and event.get("run_id") == run_id
                and event.get("node_id") == script_id
            ),
            timeout=12.0,
        )
        self.assertIsNotNone(started)

        failed = self._wait_for_event(
            lambda event: (
                event.get("type") == "run_failed"
                and event.get("run_id") == run_id
                and bool(event.get("fatal"))
                and event.get("node_id") == script_id
            ),
            timeout=8.0,
        )
        self.assertIsNotNone(failed)
        self.assertIn("terminated unexpectedly", str(failed.get("error", "")))

    def test_python_script_timeout_terminates_worker_with_node_id(self) -> None:
        workspace_id, script_id, runtime_snapshot = self._build_script_runtime_snapshot(
            "while True:\n    pass",
            timeout_sec=0.25,
        )
        run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace_id,
            trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
            data_types=self.data_types,
        )
        self.assertTrue(run_id)

        failed = self._wait_for_event(
            lambda event: (
                event.get("type") == "run_failed"
                and event.get("run_id") == run_id
                and bool(event.get("fatal"))
                and event.get("node_id") == script_id
                and "timed out" in str(event.get("error", ""))
            ),
            timeout=8.0,
        )
        self.assertIsNotNone(failed)
        timeout_state = self._wait_for_event(
            lambda event: (
                event.get("type") == "run_state"
                and event.get("run_id") == run_id
                and event.get("state") == "error"
                and event.get("reason") == "python_script_timeout"
            ),
            timeout=3.0,
        )
        self.assertIsNotNone(timeout_state)

    def test_client_receives_streamed_process_output_events(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        process_node = model.add_node(
            workspace.workspace_id,
            "io.process_run",
            "Process",
            100,
            0,
            properties={
                "command": sys.executable,
                "args": [
                    "-c",
                    (
                        "import sys, time\n"
                        "print('tick_client_0', flush=True)\n"
                        "time.sleep(0.15)\n"
                        "print('warn_client_0', file=sys.stderr, flush=True)\n"
                        "time.sleep(0.15)\n"
                        "print('tick_client_1', flush=True)\n"
                    ),
                ],
                "timeout_sec": 5.0,
                "shell": False,
                "fail_on_nonzero": True,
                "env": {},
                "encoding": "utf-8",
                "cwd": "",
            },
        )
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=build_default_registry(),
        )

        run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace.workspace_id,
            trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
            data_types=self.data_types,
        )
        self.assertTrue(run_id)

        first_stream_event = self._wait_for_event(
            lambda event: (
                event.get("type") == "log"
                and event.get("run_id") == run_id
                and "tick_client_0" in str(event.get("message", ""))
            ),
            timeout=30.0,
        )
        self.assertIsNotNone(first_stream_event)

        completed = self._wait_for_event(
            lambda event: (
                event.get("type") == "run_completed" and event.get("run_id") == run_id
            ),
            timeout=30.0,
        )
        self.assertIsNotNone(completed)

        with self._events_lock:
            run_events = [
                event for event in self._events if event.get("run_id") == run_id
            ]

        stream_messages = [
            str(event.get("message", ""))
            for event in run_events
            if event.get("type") == "log"
        ]
        self.assertTrue(any("tick_client_0" in message for message in stream_messages))
        self.assertTrue(any("tick_client_1" in message for message in stream_messages))
        self.assertTrue(any("warn_client_0" in message for message in stream_messages))

    def test_client_requires_runtime_snapshot_trigger(self) -> None:
        workspace_id, _runtime_snapshot = self._build_runtime_snapshot(
            with_sleep_script=False
        )

        run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace_id,
            trigger={
                "kind": "manual",
                "workflow_settings": {"general": {"project_name": "Demo"}},
            },
            data_types=self.data_types,
        )
        self.assertEqual(run_id, "")

        protocol_error = self._wait_for_event(
            lambda event: (
                event.get("type") == "protocol_error"
                and event.get("command") == "start_run"
                and "requires runtime_snapshot" in str(event.get("error", ""))
            ),
            timeout=3.0,
        )
        self.assertIsNotNone(protocol_error)
        self.assertIsNone(self.client._process)  # noqa: SLF001

    def test_workflow_python_environment_resolver_handles_configured_paths(
        self,
    ) -> None:
        _workspace_id, default_snapshot = self._build_runtime_snapshot()

        default_environment = resolve_workflow_python_environment(default_snapshot)

        self.assertFalse(default_environment.configured)
        self.assertTrue(default_environment.valid)

        _workspace_id, current_snapshot = self._build_runtime_snapshot(
            workflow_python_path=f'"{sys.executable}"'
        )
        current_environment = resolve_workflow_python_environment(current_snapshot)

        self.assertTrue(current_environment.configured)
        self.assertTrue(current_environment.valid)
        self.assertTrue(current_environment.is_current_python)
        self.assertEqual(
            Path(current_environment.python_executable).resolve(),
            Path(sys.executable).resolve(),
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_python = Path(tmp_dir) / "missing_python.exe"
            _workspace_id, invalid_snapshot = self._build_runtime_snapshot(
                workflow_python_path=str(missing_python)
            )

            invalid_environment = resolve_workflow_python_environment(invalid_snapshot)

        self.assertTrue(invalid_environment.configured)
        self.assertFalse(invalid_environment.valid)
        self.assertIn("does not exist", invalid_environment.error)

        with tempfile.TemporaryDirectory() as tmp_dir:
            managed_paths = resolve_managed_runtime_paths(data_dir=tmp_dir)
            managed_paths.python_executable.parent.mkdir(parents=True, exist_ok=True)
            managed_paths.python_executable.write_text("", encoding="utf-8")
            managed_paths.python_executable.chmod(0o755)
            _workspace_id, managed_snapshot = self._build_runtime_snapshot(
                workflow_python_path=str(managed_paths.python_executable)
            )

            managed_environment = resolve_workflow_python_environment(
                managed_snapshot,
                current_executable=Path(tmp_dir) / "other_python.exe",
            )

        self.assertTrue(managed_environment.configured)
        self.assertTrue(managed_environment.valid)
        self.assertFalse(managed_environment.is_current_python)
        self.assertEqual(
            Path(managed_environment.python_executable),
            managed_paths.python_executable.resolve(),
        )

    def test_backend_orchestrator_defaults_to_process_and_requires_trusted_opt_in(
        self,
    ) -> None:
        orchestrator = ExecutionBackendOrchestrator()

        default_selection = orchestrator.select()
        self.assertEqual(default_selection.backend_id, PROCESS_ISOLATED_BACKEND)
        self.assertEqual(default_selection.reason, "process_isolation_default")

        plugin_heavy_selection = orchestrator.select(
            {
                "runtime_backends": [
                    {
                        "backend_id": "packet.external",
                        "kind": "external_process",
                    }
                ]
            }
        )
        self.assertEqual(plugin_heavy_selection.backend_id, PROCESS_ISOLATED_BACKEND)
        self.assertEqual(
            plugin_heavy_selection.reason,
            "process_isolation_for_external_runtime_contracts",
        )

        with self.assertRaisesRegex(ValueError, "allow_trusted_in_process=True"):
            orchestrator.select(TRUSTED_IN_PROCESS_BACKEND)

        trusted_selection = orchestrator.select(
            {
                "requested_backend": TRUSTED_IN_PROCESS_BACKEND,
                "allow_trusted_in_process": True,
            }
        )
        self.assertEqual(trusted_selection.backend_id, TRUSTED_IN_PROCESS_BACKEND)
        self.assertTrue(trusted_selection.trusted_in_process)

        external_selection = orchestrator.select(
            {
                "requested_backend": EXTERNAL_SUBPROCESS_BACKEND,
                "runtime_backends": [
                    {
                        "backend_id": "packet.external",
                        "kind": "external_process",
                    }
                ],
            }
        )
        self.assertEqual(external_selection.backend_id, EXTERNAL_SUBPROCESS_BACKEND)
        self.assertTrue(external_selection.external_subprocess)

        python_selection = orchestrator.select(
            {
                "requested_backend": EXTERNAL_SUBPROCESS_BACKEND,
                "python_executable": sys.executable,
            }
        )
        self.assertEqual(python_selection.backend_id, EXTERNAL_SUBPROCESS_BACKEND)
        self.assertEqual(python_selection.python_executable, sys.executable)

    def test_execution_backend_client_rejects_invalid_workflow_python_executable(
        self,
    ) -> None:
        backend_client = ExecutionBackendClient()
        events: list[dict] = []
        events_lock = threading.Lock()

        def _on_event(event: dict) -> None:
            with events_lock:
                events.append(dict(event))

        def _wait_for_event(predicate, timeout: float = 6.0) -> dict | None:  # noqa: ANN001
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                with events_lock:
                    for event in events:
                        if predicate(event):
                            return event
                time.sleep(0.05)
            return None

        backend_client.subscribe(_on_event)
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_python = Path(tmp_dir) / "missing_python.exe"
            workspace_id, runtime_snapshot = self._build_runtime_snapshot(
                workflow_python_path=str(missing_python)
            )
            try:
                run_id = backend_client.start_run(
                    project_path="",
                    workspace_id=workspace_id,
                    trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
                    data_types=build_default_registry().data_types,
                )
                self.assertEqual(run_id, "")
                rejected = _wait_for_event(
                    lambda event: (
                        event.get("type") == "protocol_error"
                        and "does not exist" in str(event.get("error", ""))
                    ),
                    timeout=3.0,
                )
                self.assertIsNotNone(rejected)
            finally:
                backend_client.shutdown()

    def test_execution_backend_client_uses_workflow_python_executable_for_external_worker(
        self,
    ) -> None:
        backend_client = ExecutionBackendClient()
        events: list[dict] = []
        events_lock = threading.Lock()

        def _on_event(event: dict) -> None:
            with events_lock:
                events.append(dict(event))

        def _wait_for_event(predicate, timeout: float = 12.0) -> dict | None:  # noqa: ANN001
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                with events_lock:
                    for event in events:
                        if predicate(event):
                            return event
                time.sleep(0.05)
            return None

        backend_client.subscribe(_on_event)
        workspace_id, script_id, runtime_snapshot = self._build_script_runtime_snapshot(
            (
                "import os, sys\n"
                "result = {"
                "'python': sys.executable, "
                f"'addon_python': os.environ.get('{ADDON_RUNTIME_PYTHON_ENV}', '')"
                "}"
            ),
            workflow_python_path=sys.executable,
        )
        try:
            run_id = backend_client.start_run(
                project_path="",
                workspace_id=workspace_id,
                trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
                data_types=build_default_registry().data_types,
            )
            self.assertTrue(run_id)
            completed = _wait_for_event(
                lambda event: (
                    event.get("type") == "run_completed"
                    and event.get("run_id") == run_id
                ),
                timeout=12.0,
            )
            self.assertIsNotNone(completed)
            backend_log = _wait_for_event(
                lambda event: (
                    event.get("type") == "log"
                    and event.get("run_id") == run_id
                    and EXTERNAL_SUBPROCESS_BACKEND in str(event.get("message", ""))
                ),
                timeout=3.0,
            )
            self.assertIsNotNone(backend_log)
            script_completed = _wait_for_event(
                lambda event: (
                    event.get("type") == "node_settled"
                    and event.get("run_id") == run_id
                    and event.get("node_id") == script_id
                ),
                timeout=3.0,
            )
            self.assertIsNotNone(script_completed)
            if script_completed is None:
                self.fail("script node did not complete")
            result_tree = deserialize_runtime_value(
                script_completed["outputs"]["result"]["value"]
            )
            self.assertIsInstance(result_tree, DataTree)
            result_payload = result_tree[(0,)][0]
            self.assertEqual(
                Path(result_payload["python"]).resolve(),
                Path(sys.executable).resolve(),
            )
            self.assertEqual(
                Path(result_payload["addon_python"]).resolve(),
                resolve_addon_runtime_paths().python_executable,
            )
            self.assertIsNotNone(backend_client._external_python_client._process)  # noqa: SLF001
        finally:
            backend_client.shutdown()

    def test_execution_backend_client_runs_trusted_in_process_only_with_explicit_opt_in(
        self,
    ) -> None:
        backend_client = ExecutionBackendClient()
        events: list[dict] = []
        events_lock = threading.Lock()

        def _on_event(event: dict) -> None:
            with events_lock:
                events.append(dict(event))

        def _wait_for_event(predicate, timeout: float = 6.0) -> dict | None:  # noqa: ANN001
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                with events_lock:
                    for event in events:
                        if predicate(event):
                            return event
                time.sleep(0.05)
            return None

        backend_client.subscribe(_on_event)
        workspace_id, runtime_snapshot = self._build_runtime_snapshot(
            with_sleep_script=False
        )
        try:
            rejected_run_id = backend_client.start_run(
                project_path="",
                workspace_id=workspace_id,
                trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
                execution_backend={"requested_backend": TRUSTED_IN_PROCESS_BACKEND},
                data_types=build_default_registry().data_types,
            )
            self.assertEqual(rejected_run_id, "")
            rejected = _wait_for_event(
                lambda event: (
                    event.get("type") == "protocol_error"
                    and "allow_trusted_in_process=True" in str(event.get("error", ""))
                ),
                timeout=3.0,
            )
            self.assertIsNotNone(rejected)

            run_id = backend_client.start_run(
                project_path="",
                workspace_id=workspace_id,
                trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
                execution_backend={
                    "requested_backend": TRUSTED_IN_PROCESS_BACKEND,
                    "allow_trusted_in_process": True,
                },
                data_types=build_default_registry().data_types,
            )
            self.assertTrue(run_id)

            completed = _wait_for_event(
                lambda event: (
                    event.get("type") == "run_completed"
                    and event.get("run_id") == run_id
                ),
                timeout=8.0,
            )
            self.assertIsNotNone(completed)
            selected = _wait_for_event(
                lambda event: (
                    event.get("type") == "log"
                    and event.get("run_id") == run_id
                    and TRUSTED_IN_PROCESS_BACKEND in str(event.get("message", ""))
                ),
                timeout=3.0,
            )
            self.assertIsNotNone(selected)
            self.assertIsNone(backend_client._process_client._process)  # noqa: SLF001
        finally:
            backend_client.shutdown()

    def test_execution_backend_client_rejects_trusted_python_script_timeout(
        self,
    ) -> None:
        backend_client = ExecutionBackendClient()
        events: list[dict] = []
        events_lock = threading.Lock()

        def _on_event(event: dict) -> None:
            with events_lock:
                events.append(dict(event))

        def _wait_for_event(predicate, timeout: float = 6.0) -> dict | None:  # noqa: ANN001
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                with events_lock:
                    for event in events:
                        if predicate(event):
                            return event
                time.sleep(0.05)
            return None

        backend_client.subscribe(_on_event)
        workspace_id, _script_id, runtime_snapshot = (
            self._build_script_runtime_snapshot(
                "while True:\n    pass",
                timeout_sec=1.0,
            )
        )
        try:
            run_id = backend_client.start_run(
                project_path="",
                workspace_id=workspace_id,
                trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
                execution_backend={
                    "requested_backend": TRUSTED_IN_PROCESS_BACKEND,
                    "allow_trusted_in_process": True,
                },
                data_types=build_default_registry().data_types,
            )
            self.assertEqual(run_id, "")
            rejected = _wait_for_event(
                lambda event: (
                    event.get("type") == "protocol_error"
                    and "Python Script timeouts require process-isolated execution"
                    in str(event.get("error", ""))
                ),
                timeout=3.0,
            )
            self.assertIsNotNone(rejected)
        finally:
            backend_client.shutdown()

    def test_headless_runtime_loads_project_selects_workspace_and_runs_without_qapplication(
        self,
    ) -> None:
        qt_widgets = sys.modules.get("PyQt6.QtWidgets")
        qapplication_before = (
            qt_widgets.QApplication.instance() if qt_widgets is not None else None
        )
        model = GraphModel()
        workspace = model.active_workspace
        logger = model.add_node(
            workspace.workspace_id,
            "core.logger",
            "Logger",
            100,
            0,
            properties={"message": "headless ok"},
        )

        registry = build_default_registry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir) / "headless_runtime.cxproj"
            JsonProjectSerializer(registry).save(str(project_path), model.project)
            loaded = load_project(project_path, registry=registry)
            selected = select_workspace(loaded, WorkspaceSelection())
            self.assertEqual(selected.workspace_id, workspace.workspace_id)

            runtime = CorexRuntime(client=self.client, registry=registry)
            streamed_events: list[dict] = []
            result = runtime.run(
                ExecutionRequest(
                    project_path=project_path, workspace_id=selected.workspace_id
                ),
                timeout=12.0,
                on_event=streamed_events.append,
            )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.workspace_id, workspace.workspace_id)
        self.assertIn("run_started", {event.get("type") for event in streamed_events})
        self.assertEqual(result.terminal_event.get("type"), "run_completed")
        qt_widgets = sys.modules.get("PyQt6.QtWidgets")
        qapplication_after = (
            qt_widgets.QApplication.instance() if qt_widgets is not None else None
        )
        self.assertIs(qapplication_after, qapplication_before)

    def test_corex_runtime_injects_registry_catalog_and_forwards_trigger_captures(
        self,
    ) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace_id,
            registry=registry,
        )
        capture = SettledPortResult(
            status="value",
            value=DataTree.from_item("captured"),
        )
        backend_client = Mock()
        backend_client.start_run.return_value = "run_capture"
        runtime = CorexRuntime(client=backend_client, registry=registry)

        run_id = runtime.start_run(
            project_path="",
            workspace_id=workspace_id,
            trigger={"runtime_snapshot": runtime_snapshot},
            trigger_captures={"node_trigger": capture},
            clicked_trigger_node_id="node_trigger",
        )

        self.assertEqual(run_id, "run_capture")
        start_payload = backend_client.start_run.call_args.kwargs
        self.assertIs(start_payload["data_types"], registry.data_types)
        self.assertEqual(
            start_payload["trigger_captures"],
            {"node_trigger": capture},
        )

    def test_open_viewer_session_enqueues_correlated_runtime_ref_payload(self) -> None:
        self.client._ensure_process = lambda: None  # type: ignore[method-assign]  # noqa: SLF001

        request_id = self.client.open_viewer_session(
            "ws_main",
            "node_viewer",
            session_id="session_existing",
            backend_id="dpf_embedded",
            data_refs={
                "dataset": RuntimeHandleRef(
                    data_type_id="COREX.Viewer.Dataset",
                    schema_version=1,
                    handle_id="viewer_dataset_live",
                    kind="dpf.viewer_dataset",
                    owner_scope="viewer:session_existing",
                    worker_generation=3,
                ),
                "preview": RuntimeArtifactRef.staged(
                    "viewer_preview_png",
                    data_type_id=PATH_DATA_TYPE_ID,
                    schema_version=1,
                    format="png",
                    size_bytes=0,
                    sha256="0" * 64,
                    provenance="corex.test.fixture",
                ),
                "table": TabularDataRef(
                    ref_id="table_runtime_client",
                    resolver_id="tabular.cache",
                    backend_id="duckdb",
                    row_count=50,
                    column_count=3,
                ),
                "array": ArrayDataRef(
                    ref_id="array_runtime_client",
                    resolver_id="tabular.cache",
                    backend_id="npy_mmap",
                    shape=(20, 10),
                    dtype="float32",
                ),
            },
            transport={
                "kind": "dpf_handle_refs",
                "version": 1,
            },
            transport_revision=5,
            live_open_status="ready",
            camera_state={"position": [1.0, 2.0, 3.0]},
            playback_state={"state": "paused", "step_index": 1},
            summary={"result_name": "displacement", "set_ids": [1, 2]},
            options={"live_mode": "proxy"},
        )

        payload = self.client._command_queue.get(timeout=1.0)  # noqa: SLF001

        self.assertEqual(payload["type"], "open_viewer_session")
        self.assertEqual(payload["request_id"], request_id)
        self.assertEqual(payload["workspace_id"], "ws_main")
        self.assertEqual(payload["node_id"], "node_viewer")
        self.assertEqual(payload["session_id"], "session_existing")
        self.assertEqual(payload["backend_id"], "dpf_embedded")
        self.assertEqual(
            payload["transport"], {"kind": "dpf_handle_refs", "version": 1}
        )
        self.assertEqual(payload["transport_revision"], 5)
        self.assertEqual(payload["live_open_status"], "ready")
        self.assertEqual(payload["camera_state"], {"position": [1.0, 2.0, 3.0]})
        self.assertEqual(
            payload["playback_state"], {"state": "paused", "step_index": 1}
        )
        self.assertEqual(
            payload["data_refs"]["dataset"],
            {
                "__ea_runtime_value__": "handle_ref",
                "data_type_id": "COREX.Viewer.Dataset",
                "schema_version": 1,
                "handle_id": "viewer_dataset_live",
                "kind": "dpf.viewer_dataset",
                "owner_scope": "viewer:session_existing",
                "worker_generation": 3,
            },
        )
        self.assertEqual(
            payload["data_refs"]["preview"],
            {
                "__ea_runtime_value__": "artifact_ref",
                "ref": "temp://viewer_preview_png",
                "artifact_id": "viewer_preview_png",
                "scope": "staged",
                "data_type_id": PATH_DATA_TYPE_ID,
                "schema_version": 1,
                "format": "png",
                "size_bytes": 0,
                "sha256": "0" * 64,
                "provenance": "corex.test.fixture",
            },
        )
        self.assertEqual(
            payload["data_refs"]["table"],
            {
                "__ea_runtime_value__": "tabular_data_ref",
                "data_type_id": TABULAR_DATA_REF_TYPE_ID,
                "schema_version": 1,
                "ref_id": "table_runtime_client",
                "resolver_id": "tabular.cache",
                "backend_id": "duckdb",
                "row_count": 50,
                "column_count": 3,
            },
        )
        self.assertEqual(
            payload["data_refs"]["array"],
            {
                "__ea_runtime_value__": "array_data_ref",
                "data_type_id": ARRAY_DATA_REF_TYPE_ID,
                "schema_version": 1,
                "ref_id": "array_runtime_client",
                "resolver_id": "tabular.cache",
                "backend_id": "npy_mmap",
                "shape": [20, 10],
                "dtype": "float32",
            },
        )
        self.assertEqual(
            payload["summary"], {"result_name": "displacement", "set_ids": [1, 2]}
        )
        self.assertEqual(payload["options"], {"live_mode": "proxy"})

    def test_viewer_protocol_error_uses_request_id_instead_of_command_order(
        self,
    ) -> None:
        self.client._ensure_process = lambda: None  # type: ignore[method-assign]  # noqa: SLF001

        first_request_id = self.client.update_viewer_session(
            "ws_main",
            "node_viewer",
            "session_live",
            options={"selection": {"set_ids": [1]}},
        )
        second_request_id = self.client.update_viewer_session(
            "ws_main",
            "node_viewer",
            "session_live",
            options={"selection": {"set_ids": [2]}},
        )
        self.client._command_queue.get(timeout=1.0)  # noqa: SLF001
        self.client._command_queue.get(timeout=1.0)  # noqa: SLF001

        self.client._event_queue.put(
            event_to_dict(
                ProtocolErrorEvent(
                    request_id=second_request_id,
                    workspace_id="ws_main",
                    command="update_viewer_session",
                    error="Unknown command type.",
                )
            )
        )  # noqa: SLF001

        failure = self._wait_for_event(
            lambda event: (
                event.get("type") == "viewer_session_failed"
                and event.get("request_id") == second_request_id
            ),
            timeout=3.0,
        )
        protocol_error = self._wait_for_event(
            lambda event: (
                event.get("type") == "protocol_error"
                and event.get("command") == "update_viewer_session"
                and event.get("request_id") == second_request_id
            ),
            timeout=3.0,
        )

        self.assertIsNotNone(protocol_error)
        self.assertIsNotNone(failure)
        if failure is None:
            self.fail("viewer_session_failed event was not received")
        self.assertEqual(failure["workspace_id"], "ws_main")
        self.assertEqual(failure["node_id"], "node_viewer")
        self.assertEqual(failure["session_id"], "session_live")
        self.assertEqual(failure["command"], "update_viewer_session")
        self.assertEqual(failure["error"], "Unknown command type.")
        with self.client._viewer_request_lock:  # noqa: SLF001
            self.assertIn(first_request_id, self.client._pending_viewer_requests)  # noqa: SLF001
            self.assertNotIn(second_request_id, self.client._pending_viewer_requests)  # noqa: SLF001

    def test_viewer_success_event_coexists_with_run_terminal_state_reset(self) -> None:
        self.client._ensure_process = lambda: None  # type: ignore[method-assign]  # noqa: SLF001

        request_id = self.client.open_viewer_session(
            "ws_main",
            "node_viewer",
            summary={"result_name": "displacement"},
        )
        self.client._command_queue.get(timeout=1.0)  # noqa: SLF001

        with self.client._state_lock:  # noqa: SLF001
            self.client._active_run_id = "run_demo"  # noqa: SLF001
            self.client._active_workspace_id = "ws_main"  # noqa: SLF001

        self.client._event_queue.put(
            event_to_dict(
                ViewerSessionOpenedEvent(
                    request_id=request_id,
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live",
                    summary={"dataset_type": "UnstructuredGrid"},
                    options={"live_mode": "proxy"},
                )
            )
        )  # noqa: SLF001
        self.client._event_queue.put(
            event_to_dict(
                RunCompletedEvent(
                    run_id="run_demo",
                    workspace_id="ws_main",
                )
            )
        )  # noqa: SLF001

        opened = self._wait_for_event(
            lambda event: (
                event.get("type") == "viewer_session_opened"
                and event.get("request_id") == request_id
            ),
            timeout=3.0,
        )
        completed = self._wait_for_event(
            lambda event: (
                event.get("type") == "run_completed"
                and event.get("run_id") == "run_demo"
            ),
            timeout=3.0,
        )

        self.assertIsNotNone(opened)
        self.assertIsNotNone(completed)
        with self.client._state_lock:  # noqa: SLF001
            self.assertEqual(self.client._active_run_id, "")  # noqa: SLF001
            self.assertEqual(self.client._active_workspace_id, "")  # noqa: SLF001
        with self.client._viewer_request_lock:  # noqa: SLF001
            self.assertNotIn(request_id, self.client._pending_viewer_requests)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
