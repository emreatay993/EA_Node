# Purpose: Guard rails for the automation packages: Qt/UI-free client side, handler table == catalog, no dialogs/decorators/getattr dispatch, B1 string pin.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTOMATION_PKG = REPO_ROOT / "ea_node_editor" / "automation"
SHELL_AUTOMATION_PKG = REPO_ROOT / "ea_node_editor" / "ui" / "shell" / "automation"
HANDLERS_PKG = SHELL_AUTOMATION_PKG / "handlers"
TESTS_PKG = REPO_ROOT / "tests" / "automation"

_FORBIDDEN_CLIENT_IMPORT_PREFIXES = ("PyQt6", "ea_node_editor.ui", "ea_node_editor.ui_qml", "ea_node_editor.settings")
_FORBIDDEN_DIALOG_NAMES = ("QMessageBox", "QInputDialog", "QFileDialog", "QDialog(")
# The repo pins the count of this exact string at 1 (tests/test_architecture_boundaries.py);
# spell it in two halves here so this file never contributes to the count.
_EXECUTION_EVENT_CONNECT = "execution_event" + ".connect("


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _imports(tree: ast.Module) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


class AutomationClientSideBoundaryTests(unittest.TestCase):
    def test_automation_package_never_imports_qt_or_ui(self) -> None:
        for path in _python_files(AUTOMATION_PKG):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for module in _imports(tree):
                with self.subTest(path=path.name, module=module):
                    self.assertFalse(
                        module.startswith(_FORBIDDEN_CLIENT_IMPORT_PREFIXES),
                        f"{path.relative_to(REPO_ROOT)} imports {module}",
                    )

    def test_automation_package_imports_cleanly_without_qt(self) -> None:
        import importlib
        import sys

        for name in (
            "ea_node_editor.automation.errors",
            "ea_node_editor.automation.protocol",
            "ea_node_editor.automation.op_model",
            "ea_node_editor.automation.op_catalog",
            "ea_node_editor.automation.gate",
            "ea_node_editor.automation.discovery",
            "ea_node_editor.automation.transport",
            "ea_node_editor.automation.launcher",
            "ea_node_editor.automation.client",
            "ea_node_editor.automation.guidance",
            "ea_node_editor.automation.mcp_server",
            "ea_node_editor.automation.docgen",
        ):
            with self.subTest(module=name):
                importlib.import_module(name)
        # ``mcp`` is optional: importing the server module must not require it.
        self.assertIn("ea_node_editor.automation.mcp_server", sys.modules)

    def test_no_lazy_getattr_barrels_or_import_side_effects(self) -> None:
        for path in (*_python_files(AUTOMATION_PKG), *_python_files(SHELL_AUTOMATION_PKG)):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertNotIn("def __getattr__", text)
                self.assertNotIn(_EXECUTION_EVENT_CONNECT, text)

    def test_every_automation_source_file_carries_a_map_banner(self) -> None:
        for path in (*_python_files(AUTOMATION_PKG), *_python_files(SHELL_AUTOMATION_PKG), *_python_files(TESTS_PKG)):
            if path.name == "__init__.py" and path.parent == TESTS_PKG:
                continue
            head = path.read_text(encoding="utf-8").splitlines()[:4]
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertTrue(any(line.startswith("# Purpose:") for line in head), "missing # Purpose:")
                self.assertTrue(
                    any(line.startswith("# Map: feature_routes/automation_api_mcp") for line in head),
                    "missing # Map: feature_routes/automation_api_mcp",
                )
                self.assertTrue(any(line.startswith("# Tests:") for line in head), "missing # Tests:")


class HandlerBoundaryTests(unittest.TestCase):
    def test_handler_modules_end_with_explicit_tables_without_decorators_or_dialogs(self) -> None:
        for path in _python_files(HANDLERS_PKG):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
            with self.subTest(path=path.name):
                for forbidden in _FORBIDDEN_DIALOG_NAMES:
                    self.assertNotIn(forbidden, text, f"{path.name} reaches a modal dialog ({forbidden})")
                self.assertNotIn("GraphRecordMutation", text)
                self.assertNotIn("getattr(", text.replace("hasattr(", ""), "handlers must call concrete owners, not getattr dispatch")
                assigns = [
                    node
                    for node in tree.body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "HANDLERS" for target in node.targets)
                ]
                self.assertEqual(len(assigns), 1, "exactly one module-level HANDLERS assignment")
                self.assertIsInstance(assigns[0].value, ast.Dict)
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef):
                        self.assertEqual(node.decorator_list, [], f"{path.name}:{node.name} uses a decorator")
                    if isinstance(node, ast.ClassDef):
                        self.fail(f"{path.name} defines class {node.name}; handlers are plain functions")

    def test_handler_table_matches_catalog_exactly(self) -> None:
        from ea_node_editor.automation.op_catalog import op_names
        from ea_node_editor.ui.shell.automation.registry import build_handler_table

        table = build_handler_table()
        self.assertEqual(set(table), set(op_names()))
        for op_name, handler in table.items():
            with self.subTest(op=op_name):
                self.assertTrue(callable(handler))
                self.assertEqual(getattr(handler, "__module__", "").rsplit(".", 2)[-2], "handlers")

    def test_registry_rejects_duplicate_and_missing_handlers(self) -> None:
        import ea_node_editor.ui.shell.automation.registry as registry_module
        from unittest.mock import patch

        class _Fake:
            HANDLERS = {"node.add": lambda context, params: {}}

        with patch.object(registry_module, "HANDLER_MODULES", ("nodes", "nodes")), patch.object(
            registry_module.importlib, "import_module", return_value=_Fake
        ):
            with self.assertRaises(ValueError):
                registry_module.build_handler_table()
        with patch.object(registry_module, "HANDLER_MODULES", ("nodes",)), patch.object(
            registry_module.importlib, "import_module", return_value=_Fake
        ):
            with self.assertRaises(RuntimeError):
                registry_module.build_handler_table()

    def test_catalog_snapshot_is_json_serialisable(self) -> None:
        from ea_node_editor.automation.op_catalog import catalog_json

        json.dumps(catalog_json(), sort_keys=True)


class HarnessContractTests(unittest.TestCase):
    def test_shell_free_context_builds_and_dispatches_through_the_catalog(self) -> None:
        from ea_node_editor.automation.errors import AutomationOpError
        from tests.automation import harness

        context = harness.build_context()
        self.assertFalse(context.has_shell)
        self.assertTrue(context.workspace_id())
        self.assertEqual(context.scope_path(), [])
        with self.assertRaises(AutomationOpError) as raised:
            harness.call(context, "node.nope", {})
        self.assertEqual(raised.exception.code, "UNKNOWN_OP")
        with self.assertRaises(AutomationOpError) as raised:
            harness.call(context, "node.add", {"type_id": 5})
        self.assertEqual(raised.exception.code, "INVALID_PARAMS")

    def test_context_lookup_helpers_raise_frozen_codes(self) -> None:
        from tests.automation import harness

        context = harness.build_context()
        with self.assertRaises(Exception) as missing:
            context.require_node("node_missing")
        self.assertEqual(missing.exception.code, "NOT_FOUND")
        with self.assertRaises(Exception) as unknown:
            context.spec_for("passive.flowchart.nope")
        self.assertEqual(unknown.exception.code, "UNKNOWN_NODE_TYPE")
        self.assertTrue(unknown.exception.details["suggestions"])
        spec = context.spec_for("passive.flowchart.process")
        self.assertEqual(spec.runtime_behavior, "passive")
        node_id = context.scene.add_node_from_type("passive.flowchart.process", 10.0, 20.0)
        node = context.require_node(node_id)
        summary = context.node_summary(node)
        self.assertEqual(summary["node_id"], node_id)
        self.assertEqual(summary["runtime_behavior"], "passive")
        self.assertEqual((summary["x"], summary["y"]), (10.0, 20.0))
        self.assertEqual(context.require_port(node, "right").kind, "flow")
        with self.assertRaises(Exception) as no_port:
            context.require_port(node, "nope")
        self.assertEqual(no_port.exception.code, "NOT_FOUND")
        self.assertEqual(context.new_ids_since(set()), [node_id])
        # add_node_from_type selects the new node; with_selection must restore whatever was selected before.
        other_id = context.scene.add_node_from_type("passive.flowchart.start", 300.0, 20.0)
        context.scene.clear_selection()
        context.scene.select_node(other_id, True)
        before = context.selected_node_ids()
        self.assertEqual(before, [other_id])
        with context.with_selection([node_id]):
            self.assertEqual(context.selected_node_ids(), [node_id])
        self.assertEqual(context.selected_node_ids(), before)
        context.scene.clear_selection()
        with context.with_selection([node_id, other_id]):
            self.assertEqual(sorted(context.selected_node_ids()), sorted([node_id, other_id]))
        self.assertEqual(context.selected_node_ids(), [])


if __name__ == "__main__":
    unittest.main()
