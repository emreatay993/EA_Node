from __future__ import annotations

import ast
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _top_level_function_names(relative_path: str) -> set[str]:
    module_path = _REPO_ROOT / relative_path
    module_text = module_path.read_text(encoding="utf-8")
    module_ast = ast.parse(module_text, filename=str(module_path))
    return {
        node.name
        for node in module_ast.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


class DeadCodeHygienePythonHelperBoundaryTests(unittest.TestCase):
    def test_removed_internal_helpers_do_not_reappear(self) -> None:
        expectations = {
            "ea_node_editor/execution/protocol.py": {"dict_to_event_type"},
            "ea_node_editor/ui/shell/library_flow.py": {"input_port_is_available"},
            "ea_node_editor/ui_qml/edge_routing.py": {"inline_body_height"},
        }

        for relative_path, absent_names in expectations.items():
            function_names = _top_level_function_names(relative_path)
            for function_name in absent_names:
                with self.subTest(path=relative_path, function_name=function_name):
                    self.assertNotIn(function_name, function_names)
