from __future__ import annotations

import json
import queue
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.execution.protocol import ShutdownCommand, StartRunCommand, command_to_dict
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.execution.worker import run_workflow, worker_main
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.decorators import node_type
from ea_node_editor.nodes.types import (
    ExecutionContext,
    NodeResult,
    PortSpec,
    RuntimeArtifactRef,
    deserialize_runtime_value,
)
from ea_node_editor.persistence.serializer import JsonProjectSerializer


@node_type(
    type_id="tests.passive_note",
    display_name="Passive Note",
    category="Tests",
    icon="note",
    ports=(),
    properties=(),
    runtime_behavior="passive",
    surface_family="annotation",
)
class _PassiveNotePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id="tests.artifact_source",
    display_name="Artifact Source",
    category="Tests",
    icon="upload",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("artifact", "out", "data", "path", exposed=True),
        PortSpec("summary", "out", "data", "str", exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(),
)
class _ArtifactSourcePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(
            outputs={
                "artifact": RuntimeArtifactRef.staged("stored_stdout"),
                "summary": "stored output staged",
                "exec_out": True,
            }
        )


@node_type(
    type_id="tests.artifact_sink",
    display_name="Artifact Sink",
    category="Tests",
    icon="download",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("artifact", "in", "data", "path", required=True),
        PortSpec("resolved_path", "out", "data", "path", exposed=True),
        PortSpec("artifact_size", "out", "data", "int", exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(),
)
class _ArtifactSinkPlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        path = ctx.resolve_input_path("artifact")
        if path is None:
            raise FileNotFoundError("Artifact Sink could not resolve the runtime artifact input.")
        contents = path.read_text(encoding="utf-8")
        return NodeResult(
            outputs={
                "resolved_path": str(path),
                "artifact_size": len(contents),
                "exec_out": True,
            }
        )


@node_type(
    type_id="tests.handle_source",
    display_name="Handle Source",
    category="Tests",
    icon="memory",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("handle", "out", "data", "json", exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(),
)
class _HandleSourcePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        handle_ref = ctx.register_handle({"value": "from_handle"}, kind="tests.payload")
        return NodeResult(outputs={"handle": handle_ref, "exec_out": True})


@node_type(
    type_id="tests.persistent_handle_source",
    display_name="Persistent Handle Source",
    category="Tests",
    icon="database",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("handle", "out", "data", "json", exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(),
)
class _PersistentHandleSourcePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        handle_ref = ctx.register_handle(
            {"value": "cached_handle"},
            kind="tests.payload",
            owner_scope="cache:tests:persistent_handle",
        )
        return NodeResult(outputs={"handle": handle_ref, "exec_out": True})


@node_type(
    type_id="tests.handle_sink",
    display_name="Handle Sink",
    category="Tests",
    icon="download",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("handle", "in", "data", "json", required=True),
        PortSpec("resolved_value", "out", "data", "str", exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(),
)
class _HandleSinkPlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        payload = ctx.resolve_handle(ctx.inputs["handle"], expected_kind="tests.payload")
        return NodeResult(outputs={"resolved_value": payload["value"], "exec_out": True})


class ExecutionWorkerTests(unittest.TestCase):
    @staticmethod
    def _drain_events(event_queue: queue.Queue) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        while not event_queue.empty():
            events.append(event_queue.get())
        return events

    @staticmethod
    def _runtime_snapshot(model: GraphModel, *, registry=None):  # noqa: ANN001
        runtime_registry = registry or build_default_registry()
        return build_runtime_snapshot(
            model.project,
            workspace_id=model.active_workspace.workspace_id,
            registry=runtime_registry,
        )

    def test_run_workflow_completes(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 100, 0, properties={"message": "ok"})
        end = model.add_node(ws.workspace_id, "core.end", "End", 200, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
        model.add_edge(ws.workspace_id, logger.node_id, "exec_out", end.node_id, "exec_in")

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            {
                "run_id": "run_test",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {},
            },
            event_queue,
        )
        events = []
        while not event_queue.empty():
            events.append(event_queue.get())
        event_types = [event["type"] for event in events]
        self.assertIn("run_started", event_types)
        self.assertIn("node_started", event_types)
        self.assertIn("node_completed", event_types)
        self.assertIn("run_completed", event_types)

    def test_run_workflow_emits_failure(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
            properties={"script": "raise RuntimeError('boom')"},
        )
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", script.node_id, "exec_in")

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            {
                "run_id": "run_error",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {},
            },
            event_queue,
        )
        events = []
        while not event_queue.empty():
            events.append(event_queue.get())
        failed = [event for event in events if event["type"] == "run_failed"]
        self.assertTrue(failed)
        self.assertEqual(failed[0]["node_id"], script.node_id)
        self.assertIn("RuntimeError: boom", failed[0]["traceback"])

    def test_run_workflow_exec_node_pulls_pure_data_dependencies(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        constant = model.add_node(
            ws.workspace_id,
            "core.constant",
            "Constant",
            100,
            -80,
            properties={"value": "from_constant"},
        )
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 200, 0)
        end = model.add_node(ws.workspace_id, "core.end", "End", 320, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
        model.add_edge(ws.workspace_id, logger.node_id, "exec_out", end.node_id, "exec_in")
        model.add_edge(ws.workspace_id, constant.node_id, "value", logger.node_id, "message")

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            {
                "run_id": "run_dependency_pull",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {},
            },
            event_queue,
        )

        events = self._drain_events(event_queue)
        started_indexes = {
            str(event.get("node_id", "")): index
            for index, event in enumerate(events)
            if str(event.get("type", "")) == "node_started"
        }
        self.assertIn(constant.node_id, started_indexes)
        self.assertIn(logger.node_id, started_indexes)
        self.assertLess(started_indexes[constant.node_id], started_indexes[logger.node_id])

        logger_logs = [
            str(event.get("message", ""))
            for event in events
            if str(event.get("type", "")) == "log" and str(event.get("node_id", "")) == logger.node_id
        ]
        self.assertIn("from_constant", logger_logs)

    def test_run_workflow_executes_pure_only_workspace_explicitly(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        constant = model.add_node(
            ws.workspace_id,
            "core.constant",
            "Constant",
            80,
            0,
            properties={"value": 42},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            {
                "run_id": "run_pure_only",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {},
            },
            event_queue,
        )

        events = self._drain_events(event_queue)
        event_types = [str(event.get("type", "")) for event in events]
        self.assertIn("run_completed", event_types)
        self.assertTrue(
            any(
                str(event.get("type", "")) == "node_started"
                and str(event.get("node_id", "")) == constant.node_id
                for event in events
            )
        )
        completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_completed"
            and str(event.get("node_id", "")) == constant.node_id
        )
        self.assertEqual(completed["outputs"]["value"], 42)

    def test_run_workflow_emits_runtime_artifact_ref_payloads_and_resolves_downstream_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_path = Path(temp_dir) / "stored_stdout.txt"
            large_payload = ("stored artifact payload\n" * 4096).strip()
            artifact_path.write_text(large_payload, encoding="utf-8")

            model = GraphModel()
            ws = model.active_workspace
            start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
            source = model.add_node(ws.workspace_id, "tests.artifact_source", "Source", 120, 0)
            sink = model.add_node(ws.workspace_id, "tests.artifact_sink", "Sink", 260, 0)
            end = model.add_node(ws.workspace_id, "core.end", "End", 400, 0)
            model.add_edge(ws.workspace_id, start.node_id, "exec_out", source.node_id, "exec_in")
            model.add_edge(ws.workspace_id, source.node_id, "exec_out", sink.node_id, "exec_in")
            model.add_edge(ws.workspace_id, source.node_id, "artifact", sink.node_id, "artifact")
            model.add_edge(ws.workspace_id, sink.node_id, "exec_out", end.node_id, "exec_in")
            model.project.metadata["artifact_store"] = {
                "artifacts": {},
                "staged": {
                    "stored_stdout": {
                        "absolute_path": str(artifact_path),
                    }
                },
            }

            registry = build_default_registry()
            registry.register(_ArtifactSourcePlugin)
            registry.register(_ArtifactSinkPlugin)
            runtime_snapshot = self._runtime_snapshot(model, registry=registry)
            event_queue: queue.Queue = queue.Queue()

            with mock.patch("ea_node_editor.nodes.bootstrap.build_default_registry", return_value=registry):
                run_workflow(
                    {
                        "run_id": "run_artifact_refs",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": runtime_snapshot,
                        "trigger": {},
                    },
                    event_queue,
                )

            events = self._drain_events(event_queue)
            source_completed = next(
                event
                for event in events
                if str(event.get("type", "")) == "node_completed"
                and str(event.get("node_id", "")) == source.node_id
            )
            self.assertEqual(source_completed["outputs"]["summary"], "stored output staged")
            self.assertEqual(
                source_completed["outputs"]["artifact"],
                {
                    "__ea_runtime_value__": "artifact_ref",
                    "ref": "artifact-stage://stored_stdout",
                    "artifact_id": "stored_stdout",
                    "scope": "staged",
                },
            )
            self.assertNotIn(large_payload[:128], json.dumps(source_completed))

            sink_completed = next(
                event
                for event in events
                if str(event.get("type", "")) == "node_completed"
                and str(event.get("node_id", "")) == sink.node_id
            )
            self.assertEqual(sink_completed["outputs"]["resolved_path"], str(artifact_path))
            self.assertEqual(sink_completed["outputs"]["artifact_size"], len(large_payload))

    def test_run_workflow_resolves_runtime_handle_refs_and_cleans_run_scope_handles(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        source = model.add_node(ws.workspace_id, "tests.handle_source", "Handle Source", 120, 0)
        sink = model.add_node(ws.workspace_id, "tests.handle_sink", "Handle Sink", 260, 0)
        end = model.add_node(ws.workspace_id, "core.end", "End", 400, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", source.node_id, "exec_in")
        model.add_edge(ws.workspace_id, source.node_id, "exec_out", sink.node_id, "exec_in")
        model.add_edge(ws.workspace_id, source.node_id, "handle", sink.node_id, "handle")
        model.add_edge(ws.workspace_id, sink.node_id, "exec_out", end.node_id, "exec_in")

        registry = build_default_registry()
        registry.register(_HandleSourcePlugin)
        registry.register(_HandleSinkPlugin)
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        event_queue: queue.Queue = queue.Queue()
        worker_services = WorkerServices()

        with mock.patch("ea_node_editor.nodes.bootstrap.build_default_registry", return_value=registry):
            run_workflow(
                {
                    "run_id": "run_handle_refs",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                },
                event_queue,
                worker_services=worker_services,
            )

        events = self._drain_events(event_queue)
        source_completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_completed"
            and str(event.get("node_id", "")) == source.node_id
        )
        self.assertEqual(source_completed["outputs"]["handle"]["__ea_runtime_value__"], "handle_ref")
        handle_ref = deserialize_runtime_value(source_completed["outputs"]["handle"])
        sink_completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_completed"
            and str(event.get("node_id", "")) == sink.node_id
        )
        self.assertEqual(sink_completed["outputs"]["resolved_value"], "from_handle")
        self.assertEqual(worker_services.handle_registry.active_handle_count, 0)

        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            worker_services.resolve_handle(handle_ref)

    def test_run_workflow_retains_non_run_scope_handles_when_allowed(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        source = model.add_node(
            ws.workspace_id,
            "tests.persistent_handle_source",
            "Persistent Handle Source",
            120,
            0,
        )
        end = model.add_node(ws.workspace_id, "core.end", "End", 260, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", source.node_id, "exec_in")
        model.add_edge(ws.workspace_id, source.node_id, "exec_out", end.node_id, "exec_in")

        registry = build_default_registry()
        registry.register(_PersistentHandleSourcePlugin)
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        event_queue: queue.Queue = queue.Queue()
        worker_services = WorkerServices()

        with mock.patch("ea_node_editor.nodes.bootstrap.build_default_registry", return_value=registry):
            run_workflow(
                {
                    "run_id": "run_persistent_handles",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                },
                event_queue,
                worker_services=worker_services,
            )

        events = self._drain_events(event_queue)
        source_completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_completed"
            and str(event.get("node_id", "")) == source.node_id
        )
        handle_ref = deserialize_runtime_value(source_completed["outputs"]["handle"])
        self.assertEqual(handle_ref.owner_scope, "cache:tests:persistent_handle")
        self.assertEqual(
            worker_services.resolve_handle(handle_ref, expected_kind="tests.payload"),
            {"value": "cached_handle"},
        )
        self.assertEqual(worker_services.handle_registry.active_handle_count, 1)
        self.assertTrue(worker_services.release_handle(handle_ref))
        self.assertEqual(worker_services.handle_registry.active_handle_count, 0)

    def test_worker_main_resets_services_after_worker_exception(self) -> None:
        worker_services = WorkerServices()
        persistent_ref = worker_services.register_handle(
            {"value": "preloaded"},
            kind="tests.payload",
            owner_scope="cache:tests:preloaded",
        )
        command_queue: queue.Queue = queue.Queue()
        event_queue: queue.Queue = queue.Queue()
        command_queue.put(command_to_dict(StartRunCommand(run_id="run_crash", workspace_id="ws_main")))
        command_queue.put(command_to_dict(ShutdownCommand()))

        with mock.patch(
            "ea_node_editor.execution.worker.run_workflow",
            side_effect=RuntimeError("worker boom"),
        ):
            worker_main(command_queue, event_queue, worker_services=worker_services)

        events = self._drain_events(event_queue)
        failed = [event for event in events if str(event.get("type", "")) == "run_failed"]

        self.assertTrue(failed)
        self.assertEqual(failed[0]["run_id"], "run_crash")
        self.assertIn("worker boom", str(failed[0]["error"]))
        self.assertEqual(worker_services.worker_generation, persistent_ref.worker_generation + 1)

        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            worker_services.resolve_handle(persistent_ref)

    def test_run_workflow_skips_action_nodes_without_exec_trigger(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        logger = model.add_node(
            ws.workspace_id,
            "core.logger",
            "Logger",
            120,
            0,
            properties={"message": "should_not_run"},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            {
                "run_id": "run_no_exec_trigger",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {},
            },
            event_queue,
        )

        events = self._drain_events(event_queue)
        event_types = [str(event.get("type", "")) for event in events]
        self.assertIn("run_completed", event_types)
        self.assertFalse(
            any(
                str(event.get("type", "")) == "node_started"
                and str(event.get("node_id", "")) == logger.node_id
                for event in events
            )
        )
        self.assertFalse(
            any(
                str(event.get("type", "")) == "log"
                and str(event.get("node_id", "")) == logger.node_id
                for event in events
            )
        )

    def test_run_workflow_manual_ui_trigger_preserves_project_doc_for_start_output(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 160, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
        model.add_edge(ws.workspace_id, start.node_id, "trigger", logger.node_id, "message")

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            {
                "run_id": "run_manual_trigger",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {
                    "kind": "manual",
                    "workflow_settings": {"general": {"project_name": "Demo"}},
                },
            },
            event_queue,
        )

        events = self._drain_events(event_queue)
        logger_logs = [
            str(event.get("message", ""))
            for event in events
            if str(event.get("type", "")) == "log" and str(event.get("node_id", "")) == logger.node_id
        ]
        self.assertTrue(any("'project_doc':" in message for message in logger_logs))
        self.assertTrue(any("'workflow_settings': {'general': {'project_name': 'Demo'}}" in message for message in logger_logs))

    def test_run_workflow_accepts_legacy_project_doc_payload(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        logger = model.add_node(
            ws.workspace_id,
            "core.logger",
            "Logger",
            100,
            0,
            properties={"message": "legacy project doc"},
        )
        end = model.add_node(ws.workspace_id, "core.end", "End", 200, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
        model.add_edge(ws.workspace_id, logger.node_id, "exec_out", end.node_id, "exec_in")

        event_queue: queue.Queue = queue.Queue()
        serializer = JsonProjectSerializer(build_default_registry())
        run_workflow(
            {
                "run_id": "run_legacy_project_doc",
                "workspace_id": ws.workspace_id,
                "project_doc": serializer.to_document(model.project),
                "trigger": {},
            },
            event_queue,
        )

        events = self._drain_events(event_queue)
        event_types = [str(event.get("type", "")) for event in events]
        self.assertIn("run_completed", event_types)
        logger_logs = [
            str(event.get("message", ""))
            for event in events
            if str(event.get("type", "")) == "log" and str(event.get("node_id", "")) == logger.node_id
        ]
        self.assertIn("legacy project doc", logger_logs)

    def test_run_workflow_emits_pause_resume_and_stop_transitions(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 100, 0, properties={"message": "ok"})
        end = model.add_node(ws.workspace_id, "core.end", "End", 200, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
        model.add_edge(ws.workspace_id, logger.node_id, "exec_out", end.node_id, "exec_in")

        runtime_snapshot = self._runtime_snapshot(model)

        pause_event_queue: queue.Queue = queue.Queue()
        pause_command_queue: queue.Queue = queue.Queue()
        pause_command_queue.put({"type": "pause_run", "run_id": "run_pause"})
        pause_command_queue.put({"type": "resume_run", "run_id": "run_pause"})
        run_workflow(
            {
                "run_id": "run_pause",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {},
            },
            pause_event_queue,
            command_queue=pause_command_queue,
        )
        pause_events = []
        while not pause_event_queue.empty():
            pause_events.append(pause_event_queue.get())
        pause_states = [
            (event.get("state"), event.get("transition"))
            for event in pause_events
            if event.get("type") == "run_state"
        ]
        self.assertIn(("paused", "pause"), pause_states)
        self.assertIn(("running", "resume"), pause_states)
        self.assertTrue(any(event.get("type") == "run_completed" for event in pause_events))

        stop_event_queue: queue.Queue = queue.Queue()
        stop_command_queue: queue.Queue = queue.Queue()
        stop_command_queue.put({"type": "stop_run", "run_id": "run_stop"})
        run_workflow(
            {
                "run_id": "run_stop",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {},
            },
            stop_event_queue,
            command_queue=stop_command_queue,
        )
        stop_events = []
        while not stop_event_queue.empty():
            stop_events.append(stop_event_queue.get())
        self.assertTrue(any(event.get("type") == "run_stopped" for event in stop_events))
        self.assertFalse(any(event.get("type") == "node_started" for event in stop_events))

    def test_run_workflow_streams_process_run_output_before_node_completion(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        process_node = model.add_node(
            ws.workspace_id,
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
                            "print('tick_worker_0', flush=True)\n"
                            "time.sleep(0.15)\n"
                            "print('tick_worker_1', flush=True)\n"
                            "print('warn_worker_0', file=sys.stderr, flush=True)\n"
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
        end = model.add_node(ws.workspace_id, "core.end", "End", 200, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", process_node.node_id, "exec_in")
        model.add_edge(ws.workspace_id, process_node.node_id, "exec_out", end.node_id, "exec_in")

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            {
                "run_id": "run_stream_worker",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {},
            },
            event_queue,
        )

        events = []
        while not event_queue.empty():
            events.append(event_queue.get())

        streamed_logs = [
            event
            for event in events
            if event.get("type") == "log" and event.get("node_id") == process_node.node_id
        ]
        self.assertTrue(any("tick_worker_0" in str(event.get("message", "")) for event in streamed_logs))
        self.assertTrue(any("tick_worker_1" in str(event.get("message", "")) for event in streamed_logs))
        self.assertTrue(any("warn_worker_0" in str(event.get("message", "")) for event in streamed_logs))

        log_indexes = [
            index
            for index, event in enumerate(events)
            if event.get("type") == "log" and event.get("node_id") == process_node.node_id
        ]
        completed_indexes = [
            index
            for index, event in enumerate(events)
            if event.get("type") == "node_completed" and event.get("node_id") == process_node.node_id
        ]
        self.assertTrue(log_indexes, "Expected streamed log events for process node")
        self.assertTrue(completed_indexes, "Expected process node completion event")
        self.assertLess(min(log_indexes), min(completed_indexes))

    def test_run_workflow_compiles_two_level_nested_subnodes(self) -> None:
        model = GraphModel()
        ws = model.active_workspace

        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        shell_outer = model.add_node(ws.workspace_id, "core.subnode", "Outer", 220, 0)
        end = model.add_node(ws.workspace_id, "core.end", "End", 640, 0)

        pin_outer_exec_in = model.add_node(
            ws.workspace_id,
            "core.subnode_input",
            "Outer Exec In",
            120,
            -80,
            properties={"label": "Outer Exec In", "kind": "exec", "data_type": "any"},
        )
        pin_outer_data_in = model.add_node(
            ws.workspace_id,
            "core.subnode_input",
            "Outer Data In",
            120,
            10,
            properties={"label": "Outer Data In", "kind": "data", "data_type": "dict"},
        )
        pin_outer_exec_out = model.add_node(
            ws.workspace_id,
            "core.subnode_output",
            "Outer Exec Out",
            320,
            120,
            properties={"label": "Outer Exec Out", "kind": "exec", "data_type": "any"},
        )

        shell_inner = model.add_node(ws.workspace_id, "core.subnode", "Inner", 360, 0)
        pin_inner_exec_in = model.add_node(
            ws.workspace_id,
            "core.subnode_input",
            "Inner Exec In",
            280,
            -60,
            properties={"label": "Inner Exec In", "kind": "exec", "data_type": "any"},
        )
        pin_inner_data_in = model.add_node(
            ws.workspace_id,
            "core.subnode_input",
            "Inner Data In",
            280,
            30,
            properties={"label": "Inner Data In", "kind": "data", "data_type": "dict"},
        )
        pin_inner_exec_out = model.add_node(
            ws.workspace_id,
            "core.subnode_output",
            "Inner Exec Out",
            440,
            130,
            properties={"label": "Inner Exec Out", "kind": "exec", "data_type": "any"},
        )

        nested_logger = model.add_node(ws.workspace_id, "core.logger", "Nested Logger", 430, 10)

        ws.nodes[pin_outer_exec_in.node_id].parent_node_id = shell_outer.node_id
        ws.nodes[pin_outer_data_in.node_id].parent_node_id = shell_outer.node_id
        ws.nodes[pin_outer_exec_out.node_id].parent_node_id = shell_outer.node_id
        ws.nodes[shell_inner.node_id].parent_node_id = shell_outer.node_id

        ws.nodes[pin_inner_exec_in.node_id].parent_node_id = shell_inner.node_id
        ws.nodes[pin_inner_data_in.node_id].parent_node_id = shell_inner.node_id
        ws.nodes[pin_inner_exec_out.node_id].parent_node_id = shell_inner.node_id
        ws.nodes[nested_logger.node_id].parent_node_id = shell_inner.node_id

        model.add_edge(ws.workspace_id, start.node_id, "exec_out", shell_outer.node_id, pin_outer_exec_in.node_id)
        model.add_edge(ws.workspace_id, start.node_id, "trigger", shell_outer.node_id, pin_outer_data_in.node_id)
        model.add_edge(ws.workspace_id, shell_outer.node_id, pin_outer_exec_out.node_id, end.node_id, "exec_in")

        model.add_edge(
            ws.workspace_id,
            pin_outer_exec_in.node_id,
            "pin",
            shell_inner.node_id,
            pin_inner_exec_in.node_id,
        )
        model.add_edge(
            ws.workspace_id,
            pin_outer_data_in.node_id,
            "pin",
            shell_inner.node_id,
            pin_inner_data_in.node_id,
        )
        model.add_edge(
            ws.workspace_id,
            shell_inner.node_id,
            pin_inner_exec_out.node_id,
            pin_outer_exec_out.node_id,
            "pin",
        )

        model.add_edge(ws.workspace_id, pin_inner_exec_in.node_id, "pin", nested_logger.node_id, "exec_in")
        model.add_edge(ws.workspace_id, pin_inner_data_in.node_id, "pin", nested_logger.node_id, "message")
        model.add_edge(ws.workspace_id, nested_logger.node_id, "exec_out", pin_inner_exec_out.node_id, "pin")

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            {
                "run_id": "run_nested",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {"nested": "two-level"},
            },
            event_queue,
        )

        events = self._drain_events(event_queue)
        event_types = [str(event.get("type", "")) for event in events]
        self.assertIn("run_completed", event_types)

        started_node_ids = {
            str(event.get("node_id", ""))
            for event in events
            if str(event.get("type", "")) == "node_started"
        }
        self.assertIn(start.node_id, started_node_ids)
        self.assertIn(nested_logger.node_id, started_node_ids)
        self.assertIn(end.node_id, started_node_ids)
        self.assertNotIn(shell_outer.node_id, started_node_ids)
        self.assertNotIn(shell_inner.node_id, started_node_ids)
        self.assertNotIn(pin_outer_exec_in.node_id, started_node_ids)
        self.assertNotIn(pin_outer_data_in.node_id, started_node_ids)
        self.assertNotIn(pin_outer_exec_out.node_id, started_node_ids)
        self.assertNotIn(pin_inner_exec_in.node_id, started_node_ids)
        self.assertNotIn(pin_inner_data_in.node_id, started_node_ids)
        self.assertNotIn(pin_inner_exec_out.node_id, started_node_ids)

        nested_logs = [
            event
            for event in events
            if str(event.get("type", "")) == "log"
            and str(event.get("node_id", "")) == nested_logger.node_id
        ]
        self.assertTrue(any("{'nested': 'two-level'}" in str(event.get("message", "")) for event in nested_logs))

    def test_run_workflow_nested_subnode_failure_uses_inner_node_id(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        shell = model.add_node(ws.workspace_id, "core.subnode", "Subnode", 220, 0)

        pin_exec_in = model.add_node(
            ws.workspace_id,
            "core.subnode_input",
            "Exec In",
            120,
            0,
            properties={"label": "Exec In", "kind": "exec", "data_type": "any"},
        )
        failing_script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Failing Script",
            380,
            0,
            properties={"script": "raise RuntimeError('nested boom')"},
        )

        ws.nodes[pin_exec_in.node_id].parent_node_id = shell.node_id
        ws.nodes[failing_script.node_id].parent_node_id = shell.node_id

        model.add_edge(ws.workspace_id, start.node_id, "exec_out", shell.node_id, pin_exec_in.node_id)
        model.add_edge(ws.workspace_id, pin_exec_in.node_id, "pin", failing_script.node_id, "exec_in")

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            {
                "run_id": "run_nested_fail",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "trigger": {},
            },
            event_queue,
        )

        events = self._drain_events(event_queue)
        failed = [event for event in events if str(event.get("type", "")) == "run_failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(str(failed[0].get("node_id", "")), failing_script.node_id)
        self.assertIn("RuntimeError: nested boom", str(failed[0].get("traceback", "")))

    def test_run_workflow_treats_passive_only_workspace_as_successful_no_op(self) -> None:
        registry = build_default_registry()
        registry.register(_PassiveNotePlugin)

        model = GraphModel()
        ws = model.active_workspace
        model.add_node(ws.workspace_id, "tests.passive_note", "Note A", 0, 0)
        model.add_node(ws.workspace_id, "tests.passive_note", "Note B", 240, 0)

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        with mock.patch("ea_node_editor.nodes.bootstrap.build_default_registry", return_value=registry):
            run_workflow(
                {
                    "run_id": "run_passive_only",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                },
                event_queue,
            )

        events = self._drain_events(event_queue)
        event_types = [str(event.get("type", "")) for event in events]
        self.assertIn("run_started", event_types)
        self.assertIn("run_completed", event_types)
        self.assertNotIn("run_failed", event_types)
        self.assertFalse(any(str(event.get("type", "")) == "node_started" for event in events))


if __name__ == "__main__":
    unittest.main()
