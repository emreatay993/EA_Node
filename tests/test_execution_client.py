from __future__ import annotations

import json
import sys
import threading
import time
import unittest

from ea_node_editor.execution.client import ProcessExecutionClient
from ea_node_editor.execution.protocol import (
    NodeCompletedEvent,
    ProtocolErrorEvent,
    RunCompletedEvent,
    ViewerSessionOpenedEvent,
    event_to_dict,
)
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.types import RuntimeArtifactRef, RuntimeHandleRef


class ProcessExecutionClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = ProcessExecutionClient()
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

    @staticmethod
    def _build_runtime_snapshot(*, with_sleep_script: bool = False):
        model = GraphModel()
        workspace = model.active_workspace
        start = model.add_node(workspace.workspace_id, "core.start", "Start", 0, 0)
        if with_sleep_script:
            script = model.add_node(
                workspace.workspace_id,
                "core.python_script",
                "Script",
                100,
                0,
                properties={"script": "import time\ntime.sleep(2)\noutput_data = 1"},
            )
            model.add_edge(workspace.workspace_id, start.node_id, "exec_out", script.node_id, "exec_in")
        else:
            logger = model.add_node(
                workspace.workspace_id,
                "core.logger",
                "Logger",
                100,
                0,
                properties={"message": "ok"},
            )
            end = model.add_node(workspace.workspace_id, "core.end", "End", 200, 0)
            model.add_edge(workspace.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, logger.node_id, "exec_out", end.node_id, "exec_in")

        registry = build_default_registry()
        return workspace.workspace_id, build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=registry,
        )

    def test_invalid_worker_payload_emits_protocol_error(self) -> None:
        self.client._event_queue.put("not-a-dict")  # noqa: SLF001

        event = self._wait_for_event(
            lambda payload: payload.get("type") == "protocol_error"
            and "non-dictionary event" in str(payload.get("error", "")),
            timeout=3.0,
        )

        self.assertIsNotNone(event)

    def test_client_listener_preserves_structured_artifact_ref_event_payloads(self) -> None:
        self.client._event_queue.put(
            event_to_dict(
                NodeCompletedEvent(
                    run_id="run_artifact",
                    workspace_id="ws_main",
                    node_id="node_process",
                    outputs={
                        "stdout": RuntimeArtifactRef.staged("stored_stdout"),
                        "preview": "ok",
                    },
                )
            )
        )  # noqa: SLF001

        event = self._wait_for_event(
            lambda payload: payload.get("type") == "node_completed"
            and payload.get("run_id") == "run_artifact",
            timeout=3.0,
        )

        self.assertIsNotNone(event)
        if event is None:
            self.fail("node_completed event was not received")
        self.assertEqual(
            event["outputs"]["stdout"],
            {
                "__ea_runtime_value__": "artifact_ref",
                "ref": "artifact-stage://stored_stdout",
                "artifact_id": "stored_stdout",
                "scope": "staged",
            },
        )
        self.assertEqual(event["outputs"]["preview"], "ok")

    def test_worker_death_emits_failure_and_next_run_recovers(self) -> None:
        workspace_id, long_runtime_snapshot = self._build_runtime_snapshot(with_sleep_script=True)
        first_run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace_id,
            trigger={"kind": "manual", "runtime_snapshot": long_runtime_snapshot},
        )
        self.assertTrue(first_run_id)

        started = self._wait_for_event(
            lambda event: event.get("type") == "run_started" and event.get("run_id") == first_run_id,
            timeout=4.0,
        )
        self.assertIsNotNone(started)

        process = self.client._process  # noqa: SLF001
        self.assertIsNotNone(process)
        if process is not None:
            process.terminate()
            process.join(timeout=1.0)

        failed = self._wait_for_event(
            lambda event: event.get("type") == "run_failed"
            and event.get("run_id") == first_run_id
            and bool(event.get("fatal")),
            timeout=5.0,
        )
        self.assertIsNotNone(failed)

        recovery_workspace_id, recovery_runtime_snapshot = self._build_runtime_snapshot(with_sleep_script=False)
        second_run_id = self.client.start_run(
            project_path="",
            workspace_id=recovery_workspace_id,
            trigger={"kind": "manual", "runtime_snapshot": recovery_runtime_snapshot},
        )
        self.assertTrue(second_run_id)
        self.assertNotEqual(first_run_id, second_run_id)

        completed = self._wait_for_event(
            lambda event: event.get("type") == "run_completed" and event.get("run_id") == second_run_id,
            timeout=6.0,
        )
        self.assertIsNotNone(completed)

    def test_client_receives_streamed_process_output_events(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        start = model.add_node(workspace.workspace_id, "core.start", "Start", 0, 0)
        process_node = model.add_node(
            workspace.workspace_id,
            "io.process_run",
            "Process",
            100,
            0,
            properties={
                "command": sys.executable,
                "args": json.dumps(
                    [
                        "-c",
                        (
                            "import sys, time\n"
                            "print('tick_client_0', flush=True)\n"
                            "time.sleep(0.15)\n"
                            "print('warn_client_0', file=sys.stderr, flush=True)\n"
                            "time.sleep(0.15)\n"
                            "print('tick_client_1', flush=True)\n"
                        ),
                    ]
                ),
                "timeout_sec": 5.0,
                "shell": False,
                "fail_on_nonzero": True,
                "env": {},
                "encoding": "utf-8",
                "cwd": "",
            },
        )
        end = model.add_node(workspace.workspace_id, "core.end", "End", 200, 0)
        model.add_edge(workspace.workspace_id, start.node_id, "exec_out", process_node.node_id, "exec_in")
        model.add_edge(workspace.workspace_id, process_node.node_id, "exec_out", end.node_id, "exec_in")
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=build_default_registry(),
        )

        run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace.workspace_id,
            trigger={"kind": "manual", "runtime_snapshot": runtime_snapshot},
        )
        self.assertTrue(run_id)

        first_stream_event = self._wait_for_event(
            lambda event: event.get("type") == "log"
            and event.get("run_id") == run_id
            and "tick_client_0" in str(event.get("message", "")),
            timeout=6.0,
        )
        self.assertIsNotNone(first_stream_event)

        completed = self._wait_for_event(
            lambda event: event.get("type") == "run_completed" and event.get("run_id") == run_id,
            timeout=6.0,
        )
        self.assertIsNotNone(completed)

        with self._events_lock:
            run_events = [event for event in self._events if event.get("run_id") == run_id]

        stream_messages = [
            str(event.get("message", ""))
            for event in run_events
            if event.get("type") == "log"
        ]
        self.assertTrue(any("tick_client_0" in message for message in stream_messages))
        self.assertTrue(any("tick_client_1" in message for message in stream_messages))
        self.assertTrue(any("warn_client_0" in message for message in stream_messages))

    def test_client_accepts_legacy_project_doc_trigger(self) -> None:
        workspace_id, runtime_snapshot = self._build_runtime_snapshot(with_sleep_script=False)

        run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace_id,
            trigger={
                "kind": "manual",
                "workflow_settings": {"general": {"project_name": "Demo"}},
                "project_doc": runtime_snapshot.to_document(),
            },
        )
        self.assertTrue(run_id)

        completed = self._wait_for_event(
            lambda event: event.get("type") == "run_completed" and event.get("run_id") == run_id,
            timeout=6.0,
        )
        self.assertIsNotNone(completed)

    def test_open_viewer_session_enqueues_correlated_runtime_ref_payload(self) -> None:
        self.client._ensure_process = lambda: None  # type: ignore[method-assign]  # noqa: SLF001

        request_id = self.client.open_viewer_session(
            "ws_main",
            "node_viewer",
            session_id="session_existing",
            data_refs={
                "dataset": RuntimeHandleRef(
                    handle_id="viewer_dataset_live",
                    kind="dpf.viewer_dataset",
                    owner_scope="viewer:session_existing",
                    worker_generation=3,
                ),
                "preview": RuntimeArtifactRef.staged("viewer_preview_png"),
            },
            summary={"result_name": "displacement", "set_ids": [1, 2]},
            options={"live_mode": "proxy"},
        )

        payload = self.client._command_queue.get(timeout=1.0)  # noqa: SLF001

        self.assertEqual(payload["type"], "open_viewer_session")
        self.assertEqual(payload["request_id"], request_id)
        self.assertEqual(payload["workspace_id"], "ws_main")
        self.assertEqual(payload["node_id"], "node_viewer")
        self.assertEqual(payload["session_id"], "session_existing")
        self.assertEqual(
            payload["data_refs"]["dataset"],
            {
                "__ea_runtime_value__": "handle_ref",
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
                "ref": "artifact-stage://viewer_preview_png",
                "artifact_id": "viewer_preview_png",
                "scope": "staged",
            },
        )
        self.assertEqual(payload["summary"], {"result_name": "displacement", "set_ids": [1, 2]})
        self.assertEqual(payload["options"], {"live_mode": "proxy"})

    def test_viewer_protocol_error_emits_correlated_failure_event(self) -> None:
        self.client._ensure_process = lambda: None  # type: ignore[method-assign]  # noqa: SLF001

        request_id = self.client.update_viewer_session(
            "ws_main",
            "node_viewer",
            "session_live",
            options={"selection": {"set_ids": [2]}},
        )
        self.client._command_queue.get(timeout=1.0)  # noqa: SLF001

        self.client._event_queue.put(
            event_to_dict(
                ProtocolErrorEvent(
                    workspace_id="ws_main",
                    command="update_viewer_session",
                    error="Unknown command type.",
                )
            )
        )  # noqa: SLF001

        failure = self._wait_for_event(
            lambda event: event.get("type") == "viewer_session_failed"
            and event.get("request_id") == request_id,
            timeout=3.0,
        )
        protocol_error = self._wait_for_event(
            lambda event: event.get("type") == "protocol_error"
            and event.get("command") == "update_viewer_session",
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
            lambda event: event.get("type") == "viewer_session_opened"
            and event.get("request_id") == request_id,
            timeout=3.0,
        )
        completed = self._wait_for_event(
            lambda event: event.get("type") == "run_completed"
            and event.get("run_id") == "run_demo",
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
