from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.mutation_service import WorkspaceMutationService
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

_REPO_ROOT = Path(__file__).resolve().parents[1]


class GraphSceneBridgeBindRegressionTests(unittest.TestCase):
    def test_scene_bridge_routes_fragment_and_delete_flows_through_mutation_history_helper(self) -> None:
        bridge_text = (_REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_bridge.py").read_text(encoding="utf-8")
        helper_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_mutation_history.py"
        ).read_text(encoding="utf-8")

        self.assertIn("return self._mutation_history.duplicate_selected_subgraph()", bridge_text)
        self.assertIn("return self._mutation_history.serialize_selected_subgraph_fragment()", bridge_text)
        self.assertIn("return self._mutation_history.paste_subgraph_fragment(fragment_payload, center_x, center_y)", bridge_text)
        self.assertIn("return self._mutation_history.delete_selected_graph_items(edge_ids)", bridge_text)
        self.assertIn("def delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:", helper_text)
        self.assertIn("def _expanded_selected_node_ids_for_fragment(self, workspace: WorkspaceData) -> list[str]:", helper_text)

    def test_set_workspace_does_not_mutate_node_properties_or_exposed_ports(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        node = model.add_node(
            workspace_id,
            "core.logger",
            "Logger",
            0.0,
            0.0,
            properties={"message": 123},
            exposed_ports={},
        )

        original_properties = dict(node.properties)
        original_exposed = dict(node.exposed_ports)

        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        workspace_node = model.project.workspaces[workspace_id].nodes[node.node_id]
        self.assertEqual(workspace_node.properties, original_properties)
        self.assertEqual(workspace_node.exposed_ports, original_exposed)

    def test_set_workspace_does_not_prune_preexisting_invalid_model_edges(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        source = model.add_node(workspace_id, "core.start", "Start", 0.0, 0.0)
        target = model.add_node(workspace_id, "core.logger", "Logger", 240.0, 0.0)
        edge = model.add_edge(workspace_id, source.node_id, "exec_out", target.node_id, "message")

        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        self.assertIn(edge.edge_id, model.project.workspaces[workspace_id].edges)

    def test_group_selected_nodes_delegates_to_workspace_mutation_service_transaction(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)
        node_a = scene.add_node_from_type("core.start", 0.0, 0.0)
        node_b = scene.add_node_from_type("core.logger", 240.0, 80.0)
        scene.select_node(node_a, False)
        scene.select_node(node_b, True)

        original = WorkspaceMutationService.group_selection_into_subnode
        calls: list[tuple[str, set[str], tuple[str, ...]]] = []

        def _spy(
            service: WorkspaceMutationService,
            *,
            selected_node_ids: list[object],
            scope_path: tuple[object, ...],
            shell_x: float,
            shell_y: float,
        ):
            calls.append((service.workspace_id, {str(node_id) for node_id in selected_node_ids}, tuple(scope_path)))
            return original(
                service,
                selected_node_ids=selected_node_ids,
                scope_path=scope_path,
                shell_x=shell_x,
                shell_y=shell_y,
            )

        with patch.object(WorkspaceMutationService, "group_selection_into_subnode", autospec=True) as patched:
            patched.side_effect = _spy
            self.assertTrue(scene.group_selected_nodes())

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], workspace_id)
        self.assertEqual(calls[0][1], {node_a, node_b})
        self.assertEqual(calls[0][2], ())

    def test_fragment_rewrites_delegate_to_workspace_mutation_service_transaction(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)
        source_id = scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = scene.add_node_from_type("core.logger", 240.0, 80.0)
        scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        scene.select_node(source_id, False)
        scene.select_node(target_id, True)
        fragment = scene.serialize_selected_subgraph_fragment()
        self.assertIsNotNone(fragment)
        assert fragment is not None

        original = WorkspaceMutationService.insert_graph_fragment
        calls: list[tuple[str, int, int, float, float]] = []

        def _spy(
            service: WorkspaceMutationService,
            *,
            fragment_payload: dict[str, object],
            delta_x: float,
            delta_y: float,
        ):
            calls.append(
                (
                    service.workspace_id,
                    len(fragment_payload["nodes"]),
                    len(fragment_payload["edges"]),
                    float(delta_x),
                    float(delta_y),
                )
            )
            return original(
                service,
                fragment_payload=fragment_payload,
                delta_x=delta_x,
                delta_y=delta_y,
            )

        with patch.object(WorkspaceMutationService, "insert_graph_fragment", autospec=True) as patched:
            patched.side_effect = _spy
            self.assertTrue(scene.duplicate_selected_subgraph())
            self.assertTrue(scene.paste_subgraph_fragment(fragment, 620.0, 240.0))

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][:3], (workspace_id, 2, 1))
        self.assertEqual(calls[0][3:], (40.0, 40.0))
        self.assertEqual(calls[1][:3], (workspace_id, 2, 1))

    def test_ungroup_selected_subnode_delegates_to_workspace_mutation_service_transaction(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)
        node_a = scene.add_node_from_type("core.start", 0.0, 0.0)
        node_b = scene.add_node_from_type("core.logger", 240.0, 80.0)
        scene.select_node(node_a, False)
        scene.select_node(node_b, True)
        self.assertTrue(scene.group_selected_nodes())
        shell_id = scene.selected_node_id()
        self.assertTrue(shell_id)

        original = WorkspaceMutationService.ungroup_subnode
        calls: list[tuple[str, str]] = []

        def _spy(
            service: WorkspaceMutationService,
            *,
            shell_node_id: str,
        ):
            calls.append((service.workspace_id, str(shell_node_id)))
            return original(service, shell_node_id=shell_node_id)

        with patch.object(WorkspaceMutationService, "ungroup_subnode", autospec=True) as patched:
            patched.side_effect = _spy
            self.assertTrue(scene.ungroup_selected_subnode())

        self.assertEqual(calls, [(workspace_id, str(shell_id))])


if __name__ == "__main__":
    unittest.main()
