from __future__ import annotations

import json
import queue
import sys
import threading
import time
import unittest

from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.integrations import ProcessRunNodePlugin
from ea_node_editor.nodes.types import ExecutionContext
from ea_node_editor.persistence.serializer import JsonProjectSerializer


class ProcessRunNodeRc2Tests(unittest.TestCase):
    def test_process_run_node_success_path(self) -> None:
        plugin = ProcessRunNodePlugin()
        result = plugin.execute(
            ExecutionContext(
                run_id="run",
                node_id="node",
                workspace_id="ws",
                inputs={
                    "command": sys.executable,
                    "args": json.dumps(["-c", "print('hello')"]),
                },
                properties={
                    "args": "[]",
                    "timeout_sec": 5.0,
                    "shell": False,
                    "fail_on_nonzero": True,
                    "env": {},
                    "encoding": "utf-8",
                    "cwd": "",
                },
                emit_log=lambda _level, _message: None,
            )
        )
        self.assertEqual(result.outputs["exit_code"], 0)
        self.assertIn("hello", result.outputs["stdout"])

    def test_process_run_node_nonzero_and_timeout(self) -> None:
        plugin = ProcessRunNodePlugin()
        with self.assertRaises(RuntimeError):
            plugin.execute(
                ExecutionContext(
                    run_id="run",
                    node_id="node",
                    workspace_id="ws",
                    inputs={
                        "command": sys.executable,
                        "args": json.dumps(["-c", "import sys; sys.exit(3)"]),
                    },
                    properties={
                        "args": "[]",
                        "timeout_sec": 5.0,
                        "shell": False,
                        "fail_on_nonzero": True,
                        "env": {},
                        "encoding": "utf-8",
                        "cwd": "",
                    },
                    emit_log=lambda _level, _message: None,
                )
            )

        with self.assertRaises(TimeoutError):
            plugin.execute(
                ExecutionContext(
                    run_id="run",
                    node_id="node",
                    workspace_id="ws",
                    inputs={
                        "command": sys.executable,
                        "args": json.dumps(["-c", "import time; time.sleep(2)"]),
                    },
                    properties={
                        "args": "[]",
                        "timeout_sec": 0.3,
                        "shell": False,
                        "fail_on_nonzero": True,
                        "env": {},
                        "encoding": "utf-8",
                        "cwd": "",
                    },
                    emit_log=lambda _level, _message: None,
                )
            )

    def test_process_run_node_streams_stdout_and_stderr_logs(self) -> None:
        plugin = ProcessRunNodePlugin()
        stream_logs: list[tuple[str, str]] = []
        script = (
            "import sys, time\n"
            "print('tick_0', flush=True)\n"
            "time.sleep(0.15)\n"
            "print('warn_0', file=sys.stderr, flush=True)\n"
            "time.sleep(0.15)\n"
            "print('tick_1', flush=True)\n"
        )
        result = plugin.execute(
            ExecutionContext(
                run_id="run_stream",
                node_id="node_stream",
                workspace_id="ws",
                inputs={
                    "command": sys.executable,
                    "args": json.dumps(["-c", script]),
                },
                properties={
                    "args": "[]",
                    "timeout_sec": 5.0,
                    "shell": False,
                    "fail_on_nonzero": True,
                    "env": {},
                    "encoding": "utf-8",
                    "cwd": "",
                },
                emit_log=lambda level, message: stream_logs.append((str(level), str(message))),
            )
        )

        self.assertEqual(result.outputs["exit_code"], 0)
        self.assertIn("tick_0", result.outputs["stdout"])
        self.assertIn("tick_1", result.outputs["stdout"])
        self.assertIn("warn_0", result.outputs["stderr"])
        messages = [message for _level, message in stream_logs]
        self.assertTrue(any("[stdout] tick_0" in message for message in messages))
        self.assertTrue(any("[stdout] tick_1" in message for message in messages))
        self.assertTrue(any("[stderr] warn_0" in message for message in messages))

    def test_stop_run_cancels_active_process_node(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        start = model.add_node(ws.workspace_id, "core.start", "Start", 0.0, 0.0)
        process_node = model.add_node(
            ws.workspace_id,
            "io.process_run",
            "Process",
            120.0,
            0.0,
            properties={
                "command": sys.executable,
                "args": json.dumps(["-c", "import time; time.sleep(10)"]),
                "timeout_sec": 20.0,
                "shell": False,
                "fail_on_nonzero": True,
                "env": {},
                "encoding": "utf-8",
                "cwd": "",
            },
        )
        model.add_edge(ws.workspace_id, start.node_id, "exec_out", process_node.node_id, "exec_in")

        serializer = JsonProjectSerializer(build_default_registry())
        event_queue: queue.Queue = queue.Queue()
        command_queue: queue.Queue = queue.Queue()
        run_id = "run_stop_process"

        def _runner() -> None:
            run_workflow(
                {
                    "run_id": run_id,
                    "workspace_id": ws.workspace_id,
                    "project_doc": serializer.to_document(model.project),
                    "trigger": {},
                },
                event_queue,
                command_queue=command_queue,
            )

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()

        seen_node_started = False
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline and not seen_node_started:
            try:
                event = event_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if event.get("type") == "node_started" and event.get("node_id") == process_node.node_id:
                seen_node_started = True
                break
        self.assertTrue(seen_node_started)

        command_queue.put({"type": "stop_run", "run_id": run_id})
        thread.join(timeout=6.0)
        self.assertFalse(thread.is_alive(), "run_workflow did not stop after stop_run command")

        events = []
        while not event_queue.empty():
            events.append(event_queue.get())
        event_types = [event.get("type") for event in events]
        self.assertIn("run_stopped", event_types)
        self.assertNotIn("run_failed", event_types)


if __name__ == "__main__":
    unittest.main()
