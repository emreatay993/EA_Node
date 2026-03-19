from __future__ import annotations

import json
import queue
import sys
import threading
import time
import unittest

from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.integrations_process import (
    ProcessRunNodePlugin,
    normalize_args,
    normalize_env,
)
from ea_node_editor.nodes.types import ExecutionContext


def _context(
    *,
    inputs: dict | None = None,
    properties: dict | None = None,
    emit_log=None,  # noqa: ANN001
    should_stop=None,  # noqa: ANN001
    register_cancel=None,  # noqa: ANN001
) -> ExecutionContext:
    return ExecutionContext(
        run_id="run",
        node_id="node",
        workspace_id="ws",
        inputs=dict(inputs or {}),
        properties=dict(properties or {}),
        emit_log=emit_log or (lambda _level, _message: None),
        trigger={},
        should_stop=should_stop or (lambda: False),
        register_cancel=register_cancel or (lambda _callback: None),
    )


class ProcessRunNodeTests(unittest.TestCase):
    def test_normalize_args_and_env_accept_json_and_shell_text(self) -> None:
        self.assertEqual(normalize_args(["a", 2, True]), ["a", "2", "True"])
        self.assertEqual(normalize_args('["-c", "print(1)"]'), ["-c", "print(1)"])
        self.assertEqual(normalize_args("--flag value"), ["--flag", "value"])

        self.assertEqual(normalize_env({"A": 1, "B": True}), {"A": "1", "B": "True"})
        self.assertEqual(normalize_env('{"A": 1}'), {"A": "1"})
        self.assertEqual(normalize_env("bad json"), {})

    def test_process_run_node_success_path(self) -> None:
        plugin = ProcessRunNodePlugin()
        result = plugin.execute(
            _context(
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
            )
        )

        self.assertEqual(result.outputs["exit_code"], 0)
        self.assertIn("hello", result.outputs["stdout"])

    def test_process_run_node_nonzero_timeout_and_invalid_cwd(self) -> None:
        plugin = ProcessRunNodePlugin()

        with self.assertRaises(RuntimeError):
            plugin.execute(
                _context(
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
                )
            )

        with self.assertRaises(TimeoutError):
            plugin.execute(
                _context(
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
                )
            )

        with self.assertRaises(ValueError) as cwd_error:
            plugin.execute(
                _context(
                    inputs={
                        "command": sys.executable,
                    },
                    properties={
                        "cwd": "/path/that/does/not/exist",
                        "timeout_sec": 1.0,
                    },
                )
            )
        self.assertIn("working directory", str(cwd_error.exception).lower())

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
            _context(
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
        workspace = model.active_workspace
        start = model.add_node(workspace.workspace_id, "core.start", "Start", 0.0, 0.0)
        process_node = model.add_node(
            workspace.workspace_id,
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
        model.add_edge(workspace.workspace_id, start.node_id, "exec_out", process_node.node_id, "exec_in")

        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace.workspace_id,
            registry=build_default_registry(),
        )
        event_queue: queue.Queue = queue.Queue()
        command_queue: queue.Queue = queue.Queue()
        run_id = "run_stop_process"

        def _runner() -> None:
            run_workflow(
                {
                    "run_id": run_id,
                    "workspace_id": workspace.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
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
