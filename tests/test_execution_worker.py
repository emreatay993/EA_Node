from __future__ import annotations

import json
import queue
import sys
import unittest

from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.persistence.serializer import JsonProjectSerializer


class ExecutionWorkerTests(unittest.TestCase):
    def test_run_workflow_completes(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 100, 0, properties={"message": "ok"})
        end = model.add_node(ws.workspace_id, "core.end", "End", 200, 0)
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
        model.add_edge(ws.workspace_id, logger.node_id, "exec_out", end.node_id, "exec_in")

        event_queue: queue.Queue = queue.Queue()
        serializer = JsonProjectSerializer()
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
        serializer = JsonProjectSerializer()
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

        serializer = JsonProjectSerializer()

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
        serializer = JsonProjectSerializer()
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


if __name__ == "__main__":
    unittest.main()
