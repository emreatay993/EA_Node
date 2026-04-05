from __future__ import annotations

import importlib
import unittest
from pathlib import Path
from unittest.mock import patch

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.mutation_service import WorkspaceMutationService, create_workspace_mutation_service
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

_REPO_ROOT = Path(__file__).resolve().parents[1]


class GraphSceneBridgeBindRegressionTests(unittest.TestCase):
    def test_scene_bridge_routes_fragment_and_delete_flows_through_authoring_boundary(self) -> None:
        support_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene" / "state_support.py"
        ).read_text(encoding="utf-8")
        helper_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_mutation_history.py"
        ).read_text(encoding="utf-8")

        self.assertIn("return self._command_bridge.duplicate_selected_subgraph()", support_text)
        self.assertIn("return self._command_bridge.serialize_selected_subgraph_fragment()", support_text)
        self.assertIn("return self._command_bridge.paste_subgraph_fragment(fragment_payload, center_x, center_y)", support_text)
        self.assertIn("return self._command_bridge.delete_selected_graph_items(edge_ids)", support_text)
        self.assertIn("def delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:", helper_text)
        self.assertIn("mutations = self._mutation_boundary()", helper_text)
        self.assertIn("def _expanded_selected_node_ids_for_fragment(self, workspace: WorkspaceData) -> list[str]:", helper_text)

    def test_scene_bridge_keeps_payload_cache_and_pending_surface_action_state_in_focused_helpers(self) -> None:
        bridge_text = (_REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_bridge.py").read_text(encoding="utf-8")
        package_root = _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene"
        state_support_text = (package_root / "state_support.py").read_text(encoding="utf-8")
        read_text = (package_root / "read_bridge.py").read_text(encoding="utf-8")
        command_text = (package_root / "command_bridge.py").read_text(encoding="utf-8")
        policy_text = (package_root / "policy_bridge.py").read_text(encoding="utf-8")
        context_text = (package_root / "context.py").read_text(encoding="utf-8")
        package_text = (package_root / "__init__.py").read_text(encoding="utf-8")

        self.assertTrue(package_root.is_dir())
        self.assertLessEqual(len(bridge_text.splitlines()), 300)
        self.assertIn("from ea_node_editor.ui_qml.graph_scene import (", bridge_text)
        self.assertIn("self._payload_cache = _GraphScenePayloadCache()", bridge_text)
        self.assertIn("self._pending_surface_action = _GraphScenePendingSurfaceAction()", bridge_text)
        self.assertIn("self._state_bridge = GraphSceneReadBridge(self)", bridge_text)
        self.assertIn("self._command_bridge = GraphSceneCommandBridge(", bridge_text)
        self.assertIn("self._policy_bridge = GraphScenePolicyBridge(self, self._policy_boundary)", bridge_text)
        self.assertIn("class _GraphScenePayloadCache:", state_support_text)
        self.assertIn("class _GraphScenePendingSurfaceAction:", state_support_text)
        self.assertIn("class GraphSceneBridgeBase(QObject):", state_support_text)
        self.assertIn("class GraphSceneReadBridge(QObject):", read_text)
        self.assertIn("class GraphSceneCommandBridge(QObject):", command_text)
        self.assertIn("class GraphScenePolicyBridge(QObject):", policy_text)
        self.assertIn("class _GraphSceneContext:", context_text)
        self.assertIn("self._bridge._payload_cache.update(", context_text)
        self.assertIn("GraphSceneBridgeBase", package_text)
        self.assertIn("GraphSceneCommandBridge", package_text)
        self.assertIn("GraphScenePolicyBridge", package_text)
        self.assertIn("GraphSceneReadBridge", package_text)

    def test_mutation_history_collapses_property_geometry_structure_and_fragment_flows_into_one_boundary(self) -> None:
        helper_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_mutation_history.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("class _GraphScenePropertyMutations:", helper_text)
        self.assertNotIn("class _GraphSceneGeometryMutations:", helper_text)
        self.assertNotIn("class _GraphSceneStructureMutations:", helper_text)
        self.assertNotIn("class _GraphSceneFragmentMutations:", helper_text)
        self.assertIn("class GraphSceneMutationPolicy:", helper_text)
        self.assertIn("class GraphSceneMutationHistory:", helper_text)
        self.assertIn("def set_node_property(self, node_id: str, key: str, value: Any) -> None:", helper_text)
        self.assertIn("def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool:", helper_text)
        self.assertIn("def _mutation_boundary(self) -> WorkspaceMutationService:", helper_text)
        self.assertIn("return model.mutation_service(", helper_text)
        self.assertNotIn("return WorkspaceMutationService(", helper_text)
        self.assertIn("boundary_adapters=self._boundary_adapters", helper_text)

    def test_mutation_history_facade_stays_within_packet_budget_and_helper_split(self) -> None:
        ui_qml_dir = _REPO_ROOT / "ea_node_editor" / "ui_qml"
        package_root = ui_qml_dir / "graph_scene_mutation"
        facade_path = ui_qml_dir / "graph_scene_mutation_history.py"
        facade_text = facade_path.read_text(encoding="utf-8")
        helper_paths = {
            "__init__.py": package_root / "__init__.py",
            "policy.py": package_root / "policy.py",
            "selection_and_scope_ops.py": package_root / "selection_and_scope_ops.py",
            "clipboard_and_fragment_ops.py": package_root / "clipboard_and_fragment_ops.py",
            "alignment_and_distribution_ops.py": package_root / "alignment_and_distribution_ops.py",
            "grouping_and_subnode_ops.py": package_root / "grouping_and_subnode_ops.py",
            "comment_backdrop_ops.py": package_root / "comment_backdrop_ops.py",
        }

        self.assertTrue(package_root.is_dir())
        for snippet in (
            "graph_scene_mutation.policy",
            "graph_scene_mutation.selection_and_scope_ops",
            "graph_scene_mutation.clipboard_and_fragment_ops",
            "graph_scene_mutation.alignment_and_distribution_ops",
            "graph_scene_mutation.grouping_and_subnode_ops",
            "graph_scene_mutation.comment_backdrop_ops",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, facade_text)
        self.assertLessEqual(len(facade_text.splitlines()), 350)

        for helper_name, helper_path in helper_paths.items():
            with self.subTest(helper=helper_name):
                self.assertTrue(helper_path.exists(), msg=f"missing helper {helper_name}")

        module = importlib.import_module("ea_node_editor.ui_qml.graph_scene_mutation_history")
        self.assertEqual(
            module.GraphSceneMutationPolicy.are_ports_compatible.__module__,
            "ea_node_editor.ui_qml.graph_scene_mutation.policy",
        )
        self.assertEqual(
            module.GraphSceneMutationHistory.add_node_from_type.__module__,
            "ea_node_editor.ui_qml.graph_scene_mutation.selection_and_scope_ops",
        )
        self.assertEqual(
            module.GraphSceneMutationHistory.move_node.__module__,
            "ea_node_editor.ui_qml.graph_scene_mutation.alignment_and_distribution_ops",
        )
        self.assertEqual(
            module.GraphSceneMutationHistory.group_selected_nodes.__module__,
            "ea_node_editor.ui_qml.graph_scene_mutation.grouping_and_subnode_ops",
        )
        self.assertEqual(
            module.GraphSceneMutationHistory.wrap_nodes_in_comment_backdrop.__module__,
            "ea_node_editor.ui_qml.graph_scene_mutation.comment_backdrop_ops",
        )
        self.assertEqual(
            module.GraphSceneMutationHistory.duplicate_selected_subgraph.__module__,
            "ea_node_editor.ui_qml.graph_scene_mutation.clipboard_and_fragment_ops",
        )

    def test_graph_canvas_bridges_resolve_split_scene_sources_without_losing_scene_compatibility(self) -> None:
        bridge_text = (_REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_bridge.py").read_text(encoding="utf-8")
        support_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene" / "state_support.py"
        ).read_text(encoding="utf-8")
        state_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_canvas_state_bridge.py"
        ).read_text(encoding="utf-8")
        command_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_canvas_command_bridge.py"
        ).read_text(encoding="utf-8")
        canvas_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "GraphCanvas.qml"
        ).read_text(encoding="utf-8")

        self.assertIn("GraphSceneBridgeBase", bridge_text)
        self.assertIn("def state_bridge(self) -> GraphSceneReadBridge:", support_text)
        self.assertIn("def command_bridge(self) -> GraphSceneCommandBridge:", support_text)
        self.assertIn("def policy_bridge(self) -> GraphScenePolicyBridge:", support_text)
        self.assertIn("def _resolve_scene_state_source(scene_bridge: object | None)", state_text)
        self.assertIn("def _resolve_scene_policy_source(scene_bridge: object | None)", state_text)
        self.assertIn("def _resolve_scene_command_source(scene_bridge: object | None)", command_text)
        self.assertIn("def _resolve_scene_policy_source(scene_bridge: object | None)", command_text)
        self.assertIn("readonly property var sceneStateBridge: rootBindings.sceneStateBridge", canvas_text)
        self.assertIn("readonly property var sceneCommandBridge: rootBindings.sceneCommandBridge", canvas_text)
        self.assertIn("sceneBridge: root.sceneStateBridge", canvas_text)
        self.assertIn("sceneCommandBridge: root.sceneCommandBridge", canvas_text)

        scene = GraphSceneBridge()
        canvas_state_bridge = GraphCanvasStateBridge(scene_bridge=scene)
        canvas_command_bridge = GraphCanvasCommandBridge(scene_bridge=scene)

        self.assertIs(canvas_state_bridge.scene_bridge, scene)
        self.assertIs(canvas_state_bridge.scene_state_source, scene.state_bridge)
        self.assertIs(canvas_state_bridge.scene_policy_source, scene.policy_bridge)
        self.assertIs(canvas_command_bridge.scene_bridge, scene)
        self.assertIs(canvas_command_bridge.scene_command_source, scene.command_bridge)
        self.assertIs(canvas_command_bridge.scene_policy_source, scene.policy_bridge)

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

    def test_scene_mutations_route_through_model_mutation_service_factory(self) -> None:
        registry = build_default_registry()
        calls: list[tuple[GraphModel, str, object, object | None]] = []

        def _factory(
            *,
            model: GraphModel,
            workspace_id: str,
            registry=None,
            boundary_adapters=None,
        ) -> WorkspaceMutationService:
            calls.append((model, workspace_id, registry, boundary_adapters))
            return create_workspace_mutation_service(
                model=model,
                workspace_id=workspace_id,
                registry=registry,
                boundary_adapters=boundary_adapters,
            )

        model = GraphModel(mutation_service_factory=_factory)
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        self.assertTrue(scene.add_node_from_type("core.start", 0.0, 0.0))

        self.assertGreaterEqual(len(calls), 1)
        self.assertIs(calls[0][0], model)
        self.assertEqual(calls[0][1], workspace_id)
        self.assertIs(calls[0][2], registry)
        self.assertIsNotNone(calls[0][3])

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
