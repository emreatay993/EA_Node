from __future__ import annotations

import json
import queue
import sys
import unittest

from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer


class ExecutionWorkerTests(unittest.TestCase):
    @staticmethod
    def _drain_events(event_queue: queue.Queue) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        while not event_queue.empty():
            events.append(event_queue.get())
        return events

    def test_run_workflow_completes(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 100, 0, properties={"message": "ok"})
        end = model.add_node(ws.workspace_id, "core.end", "End", 200, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
        model.add_edge(ws.workspace_id, logger.node_id, "exec_out", end.node_id, "exec_in")

        event_queue: queue.Queue = queue.Queue()
        serializer = JsonProjectSerializer(build_default_registry())
        run_workflow(
            {
                "run_id": "run_test",
                "workspace_id": ws.workspace_id,
                "project_doc": serializer.to_document(model.project),
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
        serializer = JsonProjectSerializer(build_default_registry())
        run_workflow(
            {
                "run_id": "run_error",
                "workspace_id": ws.workspace_id,
                "project_doc": serializer.to_document(model.project),
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

    def test_run_workflow_emits_pause_resume_and_stop_transitions(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 100, 0, properties={"message": "ok"})
        end = model.add_node(ws.workspace_id, "core.end", "End", 200, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
        model.add_edge(ws.workspace_id, logger.node_id, "exec_out", end.node_id, "exec_in")

        serializer = JsonProjectSerializer(build_default_registry())

        pause_event_queue: queue.Queue = queue.Queue()
        pause_command_queue: queue.Queue = queue.Queue()
        pause_command_queue.put({"type": "pause_run", "run_id": "run_pause"})
        pause_command_queue.put({"type": "resume_run", "run_id": "run_pause"})
        run_workflow(
            {
                "run_id": "run_pause",
                "workspace_id": ws.workspace_id,
                "project_doc": serializer.to_document(model.project),
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
                "project_doc": serializer.to_document(model.project),
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
        serializer = JsonProjectSerializer(build_default_registry())
        run_workflow(
            {
                "run_id": "run_stream_worker",
                "workspace_id": ws.workspace_id,
                "project_doc": serializer.to_document(model.project),
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
        serializer = JsonProjectSerializer(build_default_registry())
        run_workflow(
            {
                "run_id": "run_nested",
                "workspace_id": ws.workspace_id,
                "project_doc": serializer.to_document(model.project),
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
        serializer = JsonProjectSerializer(build_default_registry())
        run_workflow(
            {
                "run_id": "run_nested_fail",
                "workspace_id": ws.workspace_id,
                "project_doc": serializer.to_document(model.project),
                "trigger": {},
            },
            event_queue,
        )

        events = self._drain_events(event_queue)
        failed = [event for event in events if str(event.get("type", "")) == "run_failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(str(failed[0].get("node_id", "")), failing_script.node_id)
        self.assertIn("RuntimeError: nested boom", str(failed[0].get("traceback", "")))


if __name__ == "__main__":
    unittest.main()
