from __future__ import annotations

import threading
import time
import unittest

from ea_node_editor.execution.client import ProcessExecutionClient
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.persistence.serializer import JsonProjectSerializer


class ProcessExecutionClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = ProcessExecutionClient()
        self._events: list[dict] = []
        self._events_lock = threading.Lock()
        self.client.subscribe(self._on_event)

    def tearDown(self) -> None:
        self.client.shutdown()

    def _wait_for_event(self, predicate, timeout: float = 5.0) -> dict | None:  # noqa: ANN001
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
    def _build_document(*, with_sleep_script: bool = False) -> tuple[str, dict]:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0, 0)
        if with_sleep_script:
            script = model.add_node(
                ws.workspace_id,
                "core.python_script",
                "Script",
                100,
                0,
                properties={"script": "import time\ntime.sleep(2)\noutput_data = 1"},
            )
            model.add_edge(ws.workspace_id, start.node_id, "exec_out", script.node_id, "exec_in")
        else:
            logger = model.add_node(
                ws.workspace_id,
                "core.logger",
                "Logger",
                100,
                0,
                properties={"message": "ok"},
            )
            end = model.add_node(ws.workspace_id, "core.end", "End", 200, 0)
            model.add_edge(ws.workspace_id, start.node_id, "exec_out", logger.node_id, "exec_in")
            model.add_edge(ws.workspace_id, logger.node_id, "exec_out", end.node_id, "exec_in")

        serializer = JsonProjectSerializer()
        return ws.workspace_id, serializer.to_document(model.project)

    def test_worker_death_emits_failure_and_next_run_recovers(self) -> None:
        workspace_id, long_doc = self._build_document(with_sleep_script=True)
        first_run_id = self.client.start_run(
            project_path="",
            workspace_id=workspace_id,
            trigger={"kind": "manual", "project_doc": long_doc},
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

        recovery_workspace_id, recovery_doc = self._build_document(with_sleep_script=False)
        second_run_id = self.client.start_run(
            project_path="",
            workspace_id=recovery_workspace_id,
            trigger={"kind": "manual", "project_doc": recovery_doc},
        )
        self.assertTrue(second_run_id)
        self.assertNotEqual(first_run_id, second_run_id)

        completed = self._wait_for_event(
            lambda event: event.get("type") == "run_completed" and event.get("run_id") == second_run_id,
            timeout=6.0,
        )
        self.assertIsNotNone(completed)


if __name__ == "__main__":
    unittest.main()
