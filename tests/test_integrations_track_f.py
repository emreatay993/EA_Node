from __future__ import annotations

import csv
import json
import queue
import smtplib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins import integrations_email, integrations_spreadsheet
from ea_node_editor.nodes.builtins.core import PythonScriptNodePlugin
from ea_node_editor.nodes.builtins.integrations import (
    EmailSendNodePlugin,
    ExcelReadNodePlugin,
    ExcelWriteNodePlugin,
    FileReadNodePlugin,
    FileWriteNodePlugin,
)
from ea_node_editor.nodes.types import ExecutionContext
from ea_node_editor.persistence.serializer import JsonProjectSerializer


def _context(
    *,
    inputs: dict | None = None,
    properties: dict | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        run_id="run_test",
        node_id="node_test",
        workspace_id="ws_test",
        inputs=dict(inputs or {}),
        properties=dict(properties or {}),
        emit_log=lambda _level, _message: None,
        trigger={},
    )


class IntegrationNodesTrackFTests(unittest.TestCase):
    def test_excel_csv_read_write_success_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "rows.csv"
            rows = [
                {"b": "2", "a": "1"},
                {"a": "3", "b": "4"},
            ]

            write_result = ExcelWriteNodePlugin().execute(
                _context(inputs={"rows": rows}, properties={"path": str(output_path)})
            )
            self.assertEqual(write_result.outputs["written_path"], str(output_path))
            self.assertTrue(output_path.exists())

            read_result = ExcelReadNodePlugin().execute(_context(properties={"path": str(output_path)}))
            self.assertEqual(read_result.outputs["rows"], [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}])

    def test_excel_xlsx_dependency_gated_when_openpyxl_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            read_path = Path(temp_dir) / "input.xlsx"
            read_path.write_text("placeholder", encoding="utf-8")
            write_path = Path(temp_dir) / "output.xlsx"
            with mock.patch.object(integrations_spreadsheet, "openpyxl", None):
                with self.assertRaises(RuntimeError) as read_error:
                    ExcelReadNodePlugin().execute(_context(properties={"path": str(read_path)}))
                self.assertIn("openpyxl", str(read_error.exception).lower())

                with self.assertRaises(RuntimeError) as write_error:
                    ExcelWriteNodePlugin().execute(
                        _context(inputs={"rows": [{"name": "x"}]}, properties={"path": str(write_path)})
                    )
                message = str(write_error.exception).lower()
                self.assertIn("openpyxl", message)
                self.assertIn("runtime mode: source", message)
                self.assertIn("csv remains supported", message)

    def test_excel_xlsx_dependency_message_in_packaged_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            read_path = Path(temp_dir) / "input.xlsx"
            read_path.write_text("placeholder", encoding="utf-8")
            with mock.patch.object(integrations_spreadsheet, "openpyxl", None), mock.patch.object(
                integrations_spreadsheet.sys,
                "frozen",
                True,
                create=True,
            ):
                with self.assertRaises(RuntimeError) as read_error:
                    ExcelReadNodePlugin().execute(_context(properties={"path": str(read_path)}))
        message = str(read_error.exception).lower()
        self.assertIn("runtime mode: packaged", message)
        self.assertIn("rebuild package", message)
        self.assertIn("csv remains supported", message)

    def test_file_read_write_text_and_json_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            text_path = temp_path / "message.txt"
            json_path = temp_path / "payload.json"

            FileWriteNodePlugin().execute(
                _context(inputs={"text": "hello world"}, properties={"path": str(text_path), "as_json": False})
            )
            text_result = FileReadNodePlugin().execute(_context(properties={"path": str(text_path)}))
            self.assertEqual(text_result.outputs["text"], "hello world")

            payload = {"z": 2, "a": 1}
            FileWriteNodePlugin().execute(
                _context(inputs={"data": payload}, properties={"path": str(json_path), "as_json": True})
            )
            json_result = FileReadNodePlugin().execute(_context(properties={"path": str(json_path)}))
            self.assertEqual(
                json_result.outputs["text"],
                json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True),
            )

    def test_email_send_with_mocked_smtp(self) -> None:
        class FakeSMTP:
            instances: list["FakeSMTP"] = []

            def __init__(self, *, host: str, port: int, timeout: int) -> None:
                self.host = host
                self.port = port
                self.timeout = timeout
                self.started_tls = False
                self.login_args: tuple[str, str] | None = None
                self.messages = []
                FakeSMTP.instances.append(self)

            def __enter__(self) -> "FakeSMTP":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
                return None

            def starttls(self) -> None:
                self.started_tls = True

            def login(self, username: str, password: str) -> None:
                self.login_args = (username, password)

            def send_message(self, message) -> None:  # noqa: ANN001
                self.messages.append(message)

        with mock.patch.object(integrations_email.smtplib, "SMTP", FakeSMTP):
            result = EmailSendNodePlugin().execute(
                _context(
                    inputs={"subject": "subj", "body": "body"},
                    properties={
                        "smtp_host": "smtp.example.com",
                        "smtp_port": 2525,
                        "username": "user",
                        "password": "pass",
                        "sender": "from@example.com",
                        "to": "a@example.com, b@example.com",
                        "use_tls": True,
                    },
                )
            )

        self.assertTrue(result.outputs["sent"])
        smtp = FakeSMTP.instances[-1]
        self.assertEqual((smtp.host, smtp.port, smtp.timeout), ("smtp.example.com", 2525, 10))
        self.assertTrue(smtp.started_tls)
        self.assertEqual(smtp.login_args, ("user", "pass"))
        self.assertEqual(len(smtp.messages), 1)
        self.assertEqual(smtp.messages[0]["From"], "from@example.com")
        self.assertEqual(smtp.messages[0]["To"], "a@example.com, b@example.com")

    def test_email_send_validation_and_error_wrapping(self) -> None:
        with self.assertRaises(ValueError) as missing_error:
            EmailSendNodePlugin().execute(_context(properties={"smtp_host": "localhost"}))
        self.assertIn("sender", str(missing_error.exception).lower())

        class FailingSMTP:
            def __init__(self, **_kwargs) -> None:
                return None

            def __enter__(self) -> "FailingSMTP":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
                return None

            def send_message(self, _message) -> None:  # noqa: ANN001
                raise smtplib.SMTPException("boom")

        with mock.patch.object(integrations_email.smtplib, "SMTP", FailingSMTP):
            with self.assertRaises(RuntimeError) as smtp_error:
                EmailSendNodePlugin().execute(
                    _context(
                        properties={
                            "smtp_host": "localhost",
                            "smtp_port": 25,
                            "sender": "from@example.com",
                            "to": "to@example.com",
                        }
                    )
                )
        self.assertIn("smtp error", str(smtp_error.exception).lower())

    def test_file_and_excel_error_messages_are_clear(self) -> None:
        with self.assertRaises(ValueError) as file_error:
            FileReadNodePlugin().execute(_context())
        self.assertIn("file path", str(file_error.exception).lower())

        with tempfile.TemporaryDirectory() as temp_dir:
            bad_path = Path(temp_dir) / "unsupported.bin"
            bad_path.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError) as excel_error:
                ExcelReadNodePlugin().execute(_context(properties={"path": str(bad_path)}))
        self.assertIn("supports only", str(excel_error.exception).lower())


class IntegrationFlowSmokeTests(unittest.TestCase):
    def _run_model(self, model: GraphModel, workspace_id: str) -> list[dict]:
        event_queue: queue.Queue = queue.Queue()
        serializer = JsonProjectSerializer(build_default_registry())
        run_workflow(
            {
                "run_id": "run_smoke",
                "workspace_id": workspace_id,
                "project_doc": serializer.to_document(model.project),
                "trigger": {},
            },
            event_queue,
        )
        events: list[dict] = []
        while not event_queue.empty():
            events.append(event_queue.get())
        return events

    def test_smoke_excel_input_python_transform_excel_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_csv = temp_path / "input.csv"
            output_csv = temp_path / "output.csv"
            with input_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["name", "count"])
                writer.writeheader()
                writer.writerow({"name": "alpha", "count": "1"})

            model = GraphModel()
            workspace = model.active_workspace
            start = model.add_node(workspace.workspace_id, "core.start", "Start", 0, 0)
            excel_read = model.add_node(
                workspace.workspace_id,
                "io.excel_read",
                "Excel Read",
                120,
                0,
                properties={"path": str(input_csv)},
            )
            script = model.add_node(
                workspace.workspace_id,
                "core.python_script",
                "Python Script",
                240,
                0,
                properties={
                    "script": (
                        "output_data = [\n"
                        "    {\n"
                        "        'name': str(row.get('name', '')).upper(),\n"
                        "        'count': int(row.get('count', 0)) + 1,\n"
                        "    }\n"
                        "    for row in (input_data or [])\n"
                        "]\n"
                    )
                },
            )
            excel_write = model.add_node(
                workspace.workspace_id,
                "io.excel_write",
                "Excel Write",
                360,
                0,
                properties={"path": str(output_csv)},
            )
            end = model.add_node(workspace.workspace_id, "core.end", "End", 480, 0)

            model.add_edge(workspace.workspace_id, start.node_id, "exec_out", excel_read.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, excel_read.node_id, "rows", script.node_id, "payload")
            model.add_edge(workspace.workspace_id, excel_read.node_id, "exec_out", script.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, script.node_id, "result", excel_write.node_id, "rows")
            model.add_edge(workspace.workspace_id, script.node_id, "exec_out", excel_write.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, excel_write.node_id, "exec_out", end.node_id, "exec_in")

            events = self._run_model(model, workspace.workspace_id)
            event_types = [event["type"] for event in events]
            self.assertIn("run_completed", event_types)
            self.assertNotIn("run_failed", event_types)

            with output_csv.open("r", encoding="utf-8", newline="") as handle:
                written_rows = list(csv.DictReader(handle))
            self.assertEqual(written_rows, [{"count": "2", "name": "ALPHA"}])

    def test_smoke_file_input_python_transform_file_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.txt"
            output_path = temp_path / "output.txt"
            input_path.write_text("hello workflow", encoding="utf-8")

            model = GraphModel()
            workspace = model.active_workspace
            start = model.add_node(workspace.workspace_id, "core.start", "Start", 0, 0)
            file_read = model.add_node(
                workspace.workspace_id,
                "io.file_read",
                "File Read",
                120,
                0,
                properties={"path": str(input_path)},
            )
            script = model.add_node(
                workspace.workspace_id,
                "core.python_script",
                "Python Script",
                240,
                0,
                properties={"script": "output_data = str(input_data).upper()"},
            )
            file_write = model.add_node(
                workspace.workspace_id,
                "io.file_write",
                "File Write",
                360,
                0,
                properties={"path": str(output_path)},
            )
            end = model.add_node(workspace.workspace_id, "core.end", "End", 480, 0)

            model.add_edge(workspace.workspace_id, start.node_id, "exec_out", file_read.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, file_read.node_id, "text", script.node_id, "payload")
            model.add_edge(workspace.workspace_id, file_read.node_id, "exec_out", script.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, script.node_id, "result", file_write.node_id, "text")
            model.add_edge(workspace.workspace_id, script.node_id, "exec_out", file_write.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, file_write.node_id, "exec_out", end.node_id, "exec_in")

            events = self._run_model(model, workspace.workspace_id)
            event_types = [event["type"] for event in events]
            self.assertIn("run_completed", event_types)
            self.assertNotIn("run_failed", event_types)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "HELLO WORKFLOW")

    def test_python_script_default_output_is_input_payload(self) -> None:
        result = PythonScriptNodePlugin().execute(
            _context(inputs={"payload": {"x": 1}}, properties={"script": "pass"})
        )
        self.assertEqual(result.outputs["result"], {"x": 1})


if __name__ == "__main__":
    unittest.main()
