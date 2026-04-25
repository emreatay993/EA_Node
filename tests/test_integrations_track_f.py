from __future__ import annotations

import csv
import json
import queue
import smtplib
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.graph.boundary_adapters import _fallback_node_size
from ea_node_editor.graph.model import GraphModel, NodeInstance
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins import integrations_email, integrations_spreadsheet
from ea_node_editor.nodes.builtins.core import PythonScriptNodePlugin
from ea_node_editor.nodes.builtins.integrations import (
    EmailSendNodePlugin,
    ExcelReadNodePlugin,
    ExcelWriteNodePlugin,
    FileReadNodePlugin,
    FileWriteNodePlugin,
    PathPointerNodePlugin,
)
from ea_node_editor.nodes.builtins.integrations_file_io import (
    FILE_IO_NODE_DESCRIPTORS,
    FolderExplorerNodePlugin,
    _PATH_POINTER_CHAR_WIDTH_PX,
    _PATH_POINTER_MAX_WIDTH_PX,
    _PATH_POINTER_WIDTH_CHROME_PX,
)
from ea_node_editor.nodes.types import ExecutionContext
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui_qml.graph_geometry.standard_metrics import resolved_node_surface_size


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


class PathPointerNodeTests(unittest.TestCase):
    """Tests for ``io.path_pointer`` (Variant B from the design mockup)."""

    def test_path_pointer_file_mode_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "hello.txt"
            file_path.write_text("hi", encoding="utf-8")
            result = PathPointerNodePlugin().execute(
                _context(properties={"mode": "file", "path": str(file_path), "must_exist": True})
            )
            self.assertEqual(result.outputs["path"], str(file_path))
            self.assertIs(result.outputs["exists"], True)

    def test_path_pointer_folder_mode_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder_path = Path(temp_dir)
            result = PathPointerNodePlugin().execute(
                _context(properties={"mode": "folder", "path": str(folder_path), "must_exist": True})
            )
            self.assertEqual(result.outputs["path"], str(folder_path))
            self.assertIs(result.outputs["exists"], True)

    def test_path_pointer_missing_raises_when_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "does_not_exist.rst"
            with self.assertRaises(FileNotFoundError) as cm:
                PathPointerNodePlugin().execute(
                    _context(properties={"mode": "file", "path": str(missing), "must_exist": True})
                )
            self.assertIn("does not exist", str(cm.exception).lower())

    def test_path_pointer_missing_tolerated_when_not_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "does_not_exist.rst"
            result = PathPointerNodePlugin().execute(
                _context(properties={"mode": "file", "path": str(missing), "must_exist": False})
            )
            self.assertEqual(result.outputs["path"], str(missing))
            self.assertIs(result.outputs["exists"], False)

    def test_path_pointer_mode_mismatch_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "data.txt"
            file_path.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError) as file_as_folder:
                PathPointerNodePlugin().execute(
                    _context(properties={"mode": "folder", "path": str(file_path), "must_exist": True})
                )
            self.assertIn("folder", str(file_as_folder.exception).lower())

            with self.assertRaises(ValueError) as folder_as_file:
                PathPointerNodePlugin().execute(
                    _context(properties={"mode": "file", "path": str(temp_dir), "must_exist": True})
                )
            self.assertIn("file", str(folder_as_file.exception).lower())

    def test_path_pointer_empty_path_tolerated_when_not_must_exist(self) -> None:
        result = PathPointerNodePlugin().execute(
            _context(properties={"mode": "file", "path": "", "must_exist": False})
        )
        self.assertEqual(result.outputs, {"path": "", "exists": False})

    def test_path_pointer_empty_path_raises_when_must_exist(self) -> None:
        with self.assertRaises(ValueError) as cm:
            PathPointerNodePlugin().execute(
                _context(properties={"mode": "file", "path": "", "must_exist": True})
            )
        self.assertIn("non-empty", str(cm.exception).lower())

    def test_path_pointer_invalid_mode_raises(self) -> None:
        with self.assertRaises(ValueError) as cm:
            PathPointerNodePlugin().execute(
                _context(properties={"mode": "url", "path": "whatever", "must_exist": False})
            )
        self.assertIn("'file' or 'folder'", str(cm.exception))

    def test_path_pointer_registered_in_default_registry(self) -> None:
        """Smoke test: node is discoverable from the default registry with expected spec."""
        registry = build_default_registry()
        spec = registry.spec_or_none("io.path_pointer")
        self.assertIsNotNone(spec)
        # Ports: both outputs, passive (no exec_in/out)
        port_keys = {port.key for port in spec.ports}
        self.assertEqual(port_keys, {"path", "exists"})
        for port in spec.ports:
            self.assertEqual(port.direction, "out")
        # All properties live in the single "Source" group
        self.assertEqual(
            {prop.key for prop in spec.properties},
            {"mode", "path", "must_exist", "show_full_path"},
        )
        for prop in spec.properties:
            self.assertEqual(prop.group, "Source", f"property {prop.key} not in Source group")
        self.assertEqual(spec.runtime_behavior, "passive")
        # Folder icon requested by the user.
        self.assertEqual(spec.icon, "integrations/folder.svg")
        # Passive nodes suppress title icons by default; Path Pointer opts
        # back in so the folder glyph actually renders in the node header.
        self.assertTrue(spec.show_title_icon)

    def test_path_pointer_show_full_path_property_defaults_to_false(self) -> None:
        spec = PathPointerNodePlugin().spec()
        show_full = next(p for p in spec.properties if p.key == "show_full_path")
        self.assertEqual(show_full.type, "bool")
        self.assertEqual(show_full.default, False)
        self.assertEqual(show_full.inspector_editor, "toggle")
        self.assertEqual(show_full.group, "Source")


class FolderExplorerNodeTests(unittest.TestCase):
    """Tests for the passive ``io.folder_explorer`` node contract."""

    def test_folder_explorer_registered_in_file_io_descriptor_chain(self) -> None:
        descriptor_type_ids = {descriptor.spec.type_id for descriptor in FILE_IO_NODE_DESCRIPTORS}
        self.assertIn("io.folder_explorer", descriptor_type_ids)

        registry = build_default_registry()
        spec = registry.spec_or_none("io.folder_explorer")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.type_id, "io.folder_explorer")
        self.assertEqual(spec.display_name, "Folder Explorer")
        self.assertEqual(spec.category_path, ("Input / Output",))
        self.assertEqual(spec.runtime_behavior, "passive")
        self.assertEqual(spec.icon, "integrations/folder.svg")
        self.assertTrue(spec.show_title_icon)

        self.assertEqual(len(spec.ports), 1)
        current_port = spec.ports[0]
        self.assertEqual(current_port.key, "current")
        self.assertEqual(current_port.direction, "out")
        self.assertEqual(current_port.kind, "data")
        self.assertEqual(current_port.data_type, "path")
        self.assertTrue(current_port.exposed)

        self.assertEqual(len(spec.properties), 1)
        current_path = spec.properties[0]
        self.assertEqual(current_path.key, "current_path")
        self.assertEqual(current_path.type, "path")
        self.assertEqual(current_path.default, "")
        self.assertEqual(current_path.inline_editor, "path")
        self.assertEqual(current_path.inspector_editor, "path")
        self.assertEqual(current_path.group, "Source")

    def test_folder_explorer_outputs_current_folder_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = FolderExplorerNodePlugin().execute(
                _context(properties={"current_path": temp_dir})
            )
        self.assertEqual(result.outputs, {"current": temp_dir})

    def test_folder_explorer_rejects_missing_or_non_folder_paths(self) -> None:
        with self.assertRaises(ValueError) as empty_error:
            FolderExplorerNodePlugin().execute(_context(properties={"current_path": ""}))
        self.assertIn("non-empty folder path", str(empty_error.exception).lower())

        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"
            with self.assertRaises(FileNotFoundError) as missing_error:
                FolderExplorerNodePlugin().execute(
                    _context(properties={"current_path": str(missing)})
                )
            self.assertIn("does not exist", str(missing_error.exception).lower())

            file_path = Path(temp_dir) / "file.txt"
            file_path.write_text("not a folder", encoding="utf-8")
            with self.assertRaises(ValueError) as file_error:
                FolderExplorerNodePlugin().execute(
                    _context(properties={"current_path": str(file_path)})
                )
            self.assertIn("folder", str(file_error.exception).lower())


class PathPointerWidthResolverTests(unittest.TestCase):
    """Tests for the dynamic node width when ``show_full_path`` is toggled."""

    @staticmethod
    def _node(properties: dict | None = None, *, custom_width: float | None = None) -> types.SimpleNamespace:
        """Lightweight NodeInstance stand-in — resolver only reads these attrs."""
        return types.SimpleNamespace(
            properties=dict(properties or {}),
            custom_width=custom_width,
            custom_height=None,
        )

    def _spec(self):
        return PathPointerNodePlugin().spec()

    def test_show_full_path_false_returns_base_width(self) -> None:
        node = self._node({"show_full_path": False, "path": "C:/some/very/long/path/here.rst"})
        width, height = _fallback_node_size(node, self._spec())
        # Base default width is 240 (no custom_width set).
        self.assertEqual(width, 240.0)
        self.assertEqual(height, 160.0)

    def test_show_full_path_true_expands_width_for_long_path(self) -> None:
        long_path = "C:/runs/job_042/results/deep/nested/folder/file.rst"  # 52 chars
        node = self._node({"show_full_path": True, "path": long_path})
        width, _height = _fallback_node_size(node, self._spec())
        # Must be wider than the default 240 for a 52-char path.
        self.assertGreater(width, 240.0)
        # And wide enough to fit the path plus the graph row chrome.
        expected_width = _PATH_POINTER_WIDTH_CHROME_PX + _PATH_POINTER_CHAR_WIDTH_PX * len(long_path)
        self.assertGreaterEqual(width, expected_width)

    def test_show_full_path_true_expands_standard_surface_size_for_graph_payload(self) -> None:
        long_path = "C:/runs/job_042/results/deep/nested/folder/file.rst"
        node = NodeInstance(
            node_id="path_pointer",
            type_id="io.path_pointer",
            title="Path Pointer",
            x=0.0,
            y=0.0,
            properties={"show_full_path": True, "path": long_path},
        )
        width, _height = resolved_node_surface_size(node, self._spec())
        expected_width = _PATH_POINTER_WIDTH_CHROME_PX + _PATH_POINTER_CHAR_WIDTH_PX * len(long_path)
        self.assertGreaterEqual(width, expected_width)

    def test_show_full_path_true_uses_tight_width_for_typical_absolute_path(self) -> None:
        path = "C:/Users/emre_/PycharmProjects/EA_Node_Editor/examples/ansys_dpf/modal_superposition.sfe"
        node = self._node({"show_full_path": True, "path": path})
        width, _height = _fallback_node_size(node, self._spec())
        self.assertLessEqual(width, 925.0)

    def test_show_full_path_true_short_path_does_not_shrink_below_base(self) -> None:
        node = self._node({"show_full_path": True, "path": "a.txt"})
        width, _height = _fallback_node_size(node, self._spec())
        # Base width (240) already fits a 5-char path; width must not shrink.
        self.assertEqual(width, 240.0)

    def test_show_full_path_true_respects_user_custom_width_when_larger(self) -> None:
        node = self._node(
            {"show_full_path": True, "path": "a.txt"},
            custom_width=500.0,
        )
        width, _height = _fallback_node_size(node, self._spec())
        # User's drag-resize wider than computed must win.
        self.assertEqual(width, 500.0)

    def test_show_full_path_true_empty_path_returns_base_width(self) -> None:
        node = self._node({"show_full_path": True, "path": ""})
        width, _height = _fallback_node_size(node, self._spec())
        self.assertEqual(width, 240.0)

    def test_show_full_path_true_width_is_capped(self) -> None:
        node = self._node({"show_full_path": True, "path": "x" * 5000})
        width, _height = _fallback_node_size(node, self._spec())
        # Very long paths are capped so the graph remains navigable.
        self.assertLessEqual(width, _PATH_POINTER_MAX_WIDTH_PX)
        self.assertGreater(width, 240.0)

    def test_toggle_off_restores_last_user_custom_width(self) -> None:
        """Per user intent: flipping show_full_path off reverts to default, or user's last resize."""
        # User resized to 320 before ever turning the toggle on.
        node = self._node({"show_full_path": False, "path": "C:/very/long/path.rst"}, custom_width=320.0)
        width, _h = _fallback_node_size(node, self._spec())
        self.assertEqual(width, 320.0)

    def test_path_pointer_resolver_does_not_affect_other_node_types(self) -> None:
        """Sanity: the per-type override is keyed by type_id and must not leak."""
        other_spec = FileReadNodePlugin().spec()
        node = self._node({"show_full_path": True, "path": "C:/anything/at/all.txt"}, custom_width=200.0)
        width, _h = _fallback_node_size(node, other_spec)
        # FileReadNodePlugin has no override, so base/custom width is returned untouched.
        self.assertEqual(width, 200.0)


class IntegrationFlowSmokeTests(unittest.TestCase):
    def _run_model(self, model: GraphModel, workspace_id: str) -> list[dict]:
        return self._run_model_with_runtime_snapshot(model, workspace_id)

    def _run_model_with_runtime_snapshot(
        self,
        model: GraphModel,
        workspace_id: str,
        *,
        project_path: str = "",
    ) -> list[dict]:
        event_queue: queue.Queue = queue.Queue()
        registry = build_default_registry()
        runtime_snapshot = build_runtime_snapshot(
            model.project,
            workspace_id=workspace_id,
            registry=registry,
        )
        run_workflow(
            {
                "run_id": "run_smoke",
                "workspace_id": workspace_id,
                "project_path": project_path,
                "runtime_snapshot": runtime_snapshot,
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

    def test_smoke_file_write_blank_path_stages_managed_output_for_downstream_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "managed_file_output.sfe"

            model = GraphModel()
            workspace = model.active_workspace
            start = model.add_node(workspace.workspace_id, "core.start", "Start", 0, 0)
            script = model.add_node(
                workspace.workspace_id,
                "core.python_script",
                "Python Script",
                120,
                0,
                properties={"script": "output_data = 'managed output payload'"},
            )
            file_write = model.add_node(
                workspace.workspace_id,
                "io.file_write",
                "File Write",
                240,
                0,
                properties={"path": "", "as_json": False},
            )
            file_read = model.add_node(
                workspace.workspace_id,
                "io.file_read",
                "File Read",
                360,
                0,
            )
            end = model.add_node(workspace.workspace_id, "core.end", "End", 480, 0)

            model.add_edge(workspace.workspace_id, start.node_id, "exec_out", script.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, script.node_id, "result", file_write.node_id, "text")
            model.add_edge(workspace.workspace_id, script.node_id, "exec_out", file_write.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, file_write.node_id, "written_path", file_read.node_id, "path")
            model.add_edge(workspace.workspace_id, file_write.node_id, "exec_out", file_read.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, file_read.node_id, "exec_out", end.node_id, "exec_in")

            events = self._run_model_with_runtime_snapshot(
                model,
                workspace.workspace_id,
                project_path=str(project_path),
            )

            event_types = [event["type"] for event in events]
            self.assertIn("run_completed", event_types)
            self.assertNotIn("run_failed", event_types)

            write_completed = next(
                event
                for event in events
                if event.get("type") == "node_completed" and event.get("node_id") == file_write.node_id
            )
            self.assertEqual(write_completed["outputs"]["written_path"]["__ea_runtime_value__"], "artifact_ref")
            self.assertEqual(write_completed["outputs"]["written_path"]["scope"], "staged")

            read_completed = next(
                event
                for event in events
                if event.get("type") == "node_completed" and event.get("node_id") == file_read.node_id
            )
            self.assertEqual(read_completed["outputs"]["text"], "managed output payload")

            staged_files = list(project_path.with_name("managed_file_output.data").rglob("*.txt"))
            self.assertTrue(staged_files)

    def test_smoke_excel_write_blank_path_stages_managed_output_for_downstream_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "managed_excel_output.sfe"

            model = GraphModel()
            workspace = model.active_workspace
            start = model.add_node(workspace.workspace_id, "core.start", "Start", 0, 0)
            script = model.add_node(
                workspace.workspace_id,
                "core.python_script",
                "Python Script",
                120,
                0,
                properties={
                    "script": (
                        "output_data = [\n"
                        "    {'name': 'alpha', 'count': 1},\n"
                        "    {'name': 'beta', 'count': 2},\n"
                        "]\n"
                    )
                },
            )
            excel_write = model.add_node(
                workspace.workspace_id,
                "io.excel_write",
                "Excel Write",
                240,
                0,
                properties={"path": ""},
            )
            excel_read = model.add_node(
                workspace.workspace_id,
                "io.excel_read",
                "Excel Read",
                360,
                0,
            )
            end = model.add_node(workspace.workspace_id, "core.end", "End", 480, 0)

            model.add_edge(workspace.workspace_id, start.node_id, "exec_out", script.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, script.node_id, "result", excel_write.node_id, "rows")
            model.add_edge(workspace.workspace_id, script.node_id, "exec_out", excel_write.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, excel_write.node_id, "written_path", excel_read.node_id, "path")
            model.add_edge(workspace.workspace_id, excel_write.node_id, "exec_out", excel_read.node_id, "exec_in")
            model.add_edge(workspace.workspace_id, excel_read.node_id, "exec_out", end.node_id, "exec_in")

            events = self._run_model_with_runtime_snapshot(
                model,
                workspace.workspace_id,
                project_path=str(project_path),
            )

            event_types = [event["type"] for event in events]
            self.assertIn("run_completed", event_types)
            self.assertNotIn("run_failed", event_types)

            write_completed = next(
                event
                for event in events
                if event.get("type") == "node_completed" and event.get("node_id") == excel_write.node_id
            )
            self.assertEqual(write_completed["outputs"]["written_path"]["__ea_runtime_value__"], "artifact_ref")
            self.assertEqual(write_completed["outputs"]["written_path"]["scope"], "staged")

            read_completed = next(
                event
                for event in events
                if event.get("type") == "node_completed" and event.get("node_id") == excel_read.node_id
            )
            self.assertEqual(
                read_completed["outputs"]["rows"],
                [
                    {"count": "1", "name": "alpha"},
                    {"count": "2", "name": "beta"},
                ],
            )

            staged_files = list(project_path.with_name("managed_excel_output.data").rglob("*.csv"))
            self.assertTrue(staged_files)

    def test_python_script_default_output_is_input_payload(self) -> None:
        result = PythonScriptNodePlugin().execute(
            _context(inputs={"payload": {"x": 1}}, properties={"script": "pass"})
        )
        self.assertEqual(result.outputs["result"], {"x": 1})


if __name__ == "__main__":
    unittest.main()
