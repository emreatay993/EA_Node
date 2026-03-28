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

    def test_graph_geometry_modules_keep_extracted_helper_boundaries(self) -> None:
        edge_routing_text = (_REPO_ROOT / "ea_node_editor/ui_qml/edge_routing.py").read_text(encoding="utf-8")
        graph_surface_metrics_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/graph_surface_metrics.py"
        ).read_text(encoding="utf-8")
        performance_policy_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasPerformancePolicy.js"
        ).read_text(encoding="utf-8")
        payload_builder_text = (
            _REPO_ROOT / "ea_node_editor/ui_qml/graph_scene_payload_builder.py"
        ).read_text(encoding="utf-8")

        self.assertIn("class _EdgeLaneOffsets:", edge_routing_text)
        self.assertIn("class _ResolvedEdgePayloadContext:", edge_routing_text)
        self.assertIn("def _edge_payload_lane_offsets(workspace_edges: list[EdgeInstance]) -> _EdgeLaneOffsets:", edge_routing_text)
        self.assertIn("def _build_edge_payload_item(", edge_routing_text)
        self.assertIn("def _resolve_edge_payload_context(", edge_routing_text)
        self.assertIn("def _resolve_edge_route(", edge_routing_text)
        self.assertIn("def resolved_node_surface_size(", graph_surface_metrics_text)
        self.assertIn("class _FlowchartMetricLayoutState:", graph_surface_metrics_text)
        self.assertIn("def _resolve_flowchart_metric_layout_state(", graph_surface_metrics_text)
        self.assertIn("def _build_panel_surface_metrics(", graph_surface_metrics_text)
        self.assertIn("function _resolveModeFlags(", performance_policy_text)
        self.assertIn("function _resolveTransientActivity(", performance_policy_text)
        self.assertIn("def membership_candidate_size(", payload_builder_text)
        self.assertIn("surface_metrics = node_surface_metrics(", payload_builder_text)
