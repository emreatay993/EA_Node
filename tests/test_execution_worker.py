from __future__ import annotations

import queue
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


if __name__ == "__main__":
    unittest.main()
