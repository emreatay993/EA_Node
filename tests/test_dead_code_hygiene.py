from __future__ import annotations

import ast
import re
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


def _parse_module(relative_path: str) -> ast.Module:
    module_path = _REPO_ROOT / relative_path
    return ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))


def _top_level_class_names(relative_path: str) -> set[str]:
    module_ast = _parse_module(relative_path)
    return {
        node.name
        for node in module_ast.body
        if isinstance(node, ast.ClassDef)
    }


def _class_method_names(relative_path: str, class_name: str) -> set[str]:
    module_ast = _parse_module(relative_path)
    for node in module_ast.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    raise AssertionError(f"Class not found: {class_name}")


def _assigned_call_names(relative_path: str) -> set[tuple[str, str]]:
    assignments: set[tuple[str, str]] = set()
    module_ast = _parse_module(relative_path)
    for node in ast.walk(module_ast):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not isinstance(node.value.func, ast.Name):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                assignments.add((target.id, node.value.func.id))
    return assignments


def _js_function_names(relative_path: str) -> set[str]:
    source = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
    return set(re.findall(r"(?m)^function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source))


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

    def test_graph_geometry_modules_keep_extracted_helper_boundaries(self) -> None:
        edge_routing_classes = _top_level_class_names("ea_node_editor/ui_qml/edge_routing.py")
        edge_routing_functions = _top_level_function_names("ea_node_editor/ui_qml/edge_routing.py")
        graph_surface_metric_classes = _top_level_class_names(
            "ea_node_editor/ui_qml/graph_surface_metrics.py"
        )
        graph_surface_metric_functions = _top_level_function_names(
            "ea_node_editor/ui_qml/graph_surface_metrics.py"
        )
        payload_builder_functions = _top_level_function_names(
            "ea_node_editor/ui_qml/graph_scene_payload_builder.py"
        )
        payload_factory_methods = _class_method_names(
            "ea_node_editor/ui_qml/graph_scene_payload_builder.py",
            "_GraphSceneNodePayloadFactory",
        )
        payload_builder_assignments = _assigned_call_names(
            "ea_node_editor/ui_qml/graph_scene_payload_builder.py"
        )
        performance_policy_functions = _js_function_names(
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasPerformancePolicy.js"
        )

        self.assertTrue(
            {"_EdgeLaneOffsets", "_ResolvedEdgePayloadContext"}.issubset(edge_routing_classes)
        )
        self.assertTrue(
            {
                "_edge_payload_lane_offsets",
                "_build_edge_payload_item",
                "_resolve_edge_payload_context",
                "_resolve_edge_route",
            }.issubset(edge_routing_functions)
        )
        self.assertTrue({"resolved_node_surface_size", "_resolve_flowchart_metric_layout_state", "_build_panel_surface_metrics"}.issubset(graph_surface_metric_functions))
        self.assertIn("_FlowchartMetricLayoutState", graph_surface_metric_classes)
        self.assertTrue(
            {"_resolveModeFlags", "_resolveTransientActivity"}.issubset(
                performance_policy_functions
            )
        )
        self.assertNotIn("membership_candidate_size", payload_builder_functions)
        self.assertIn("membership_candidate_size", payload_factory_methods)
        self.assertIn(("surface_metrics", "node_surface_metrics"), payload_builder_assignments)
