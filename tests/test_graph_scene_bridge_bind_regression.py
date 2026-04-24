from __future__ import annotations

import importlib
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QObject

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.mutation_service import WorkspaceMutationService, create_workspace_mutation_service
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.plugin_contracts import (
    AddOnManifest,
    AddOnRecord,
    AddOnState,
    PluginAvailability,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

_REPO_ROOT = Path(__file__).resolve().parents[1]
COMMENT_BACKDROP_TYPE_ID = "passive.annotation.comment_backdrop"
LOGGER_TYPE_ID = "core.logger"


class _ExpandCollisionPreferenceSource(QObject):
    def __init__(self, settings: dict[str, object]) -> None:
        super().__init__()
        self.graphics_expand_collision_avoidance = dict(settings)


def _missing_addon_scene_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "proj_missing_addon_scene",
        "name": "Missing Add-On Scene",
        "active_workspace_id": "ws_addon",
        "workspace_order": ["ws_addon"],
        "workspaces": [
            {
                "workspace_id": "ws_addon",
                "name": "Workspace Add-On",
                "active_view_id": "view_addon",
                "views": [
                    {
                        "view_id": "view_addon",
                        "name": "V1",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                    }
                ],
                "nodes": [
                    {
                        "node_id": "node_source",
                        "type_id": "addons.signal.source",
                        "title": "Signal Source",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {"path": "C:/tmp/example.signal"},
                        "exposed_ports": {"signal_out": True, "exec_out": True},
                        "port_labels": {"signal_out": "Saved Signal"},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "node_transform",
                        "type_id": "addons.signal.transform",
                        "title": "Signal Transform",
                        "x": 320.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {"gain": 1.5},
                        "exposed_ports": {"signal_in": False, "signal_out": True},
                        "port_labels": {
                            "signal_in": "Hidden Saved Signal",
                            "signal_out": "Saved Result",
                        },
                        "parent_node_id": None,
                    },
                ],
                "edges": [
                    {
                        "edge_id": "edge_signal_data",
                        "source_node_id": "node_source",
                        "source_port_key": "signal_out",
                        "target_node_id": "node_transform",
                        "target_port_key": "signal_in",
                    }
                ],
            }
        ],
        "metadata": {},
    }


def _test_addon_record() -> AddOnRecord:
    return AddOnRecord(
        manifest=AddOnManifest(
            addon_id="tests.addons.signal_pack",
            display_name="Signal Pack",
            apply_policy="hot_apply",
            version="1.2.3",
            dependencies=("tests.signal.runtime",),
        ),
        state=AddOnState(enabled=True, pending_restart=False),
        availability=PluginAvailability.available(
            summary="Signal Pack is not loaded in this session."
        ),
        provided_node_type_ids=("addons.signal.source", "addons.signal.transform"),
    )


class GraphSceneBridgeBindRegressionTests(unittest.TestCase):
    def test_scene_bridge_projects_missing_addon_nodes_as_read_only_placeholder_payloads(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        with patch(
            "ea_node_editor.persistence.overlay.discover_addon_records",
            return_value=(_test_addon_record(),),
        ):
            project = serializer.from_document(_missing_addon_scene_payload())
            model = GraphModel(project)
            scene = GraphSceneBridge()
            scene.set_workspace(model, NodeRegistry(), "ws_addon")
            nodes_by_id = {payload["node_id"]: payload for payload in scene.nodes_model}
            edges_by_id = {payload["edge_id"]: payload for payload in scene.edges_model}

        self.assertEqual(set(nodes_by_id), {"node_source", "node_transform"})
        self.assertEqual(set(edges_by_id), {"edge_signal_data"})
        self.assertTrue(nodes_by_id["node_transform"]["unresolved"])
        self.assertTrue(nodes_by_id["node_transform"]["read_only"])
        self.assertEqual(nodes_by_id["node_transform"]["addon_id"], "tests.addons.signal_pack")
        self.assertEqual(nodes_by_id["node_transform"]["addon_display_name"], "Signal Pack")
        self.assertEqual(nodes_by_id["node_transform"]["addon_version"], "1.2.3")
        self.assertEqual(nodes_by_id["node_transform"]["addon_apply_policy"], "hot_apply")
        self.assertEqual(nodes_by_id["node_transform"]["addon_status"], "installed")
        self.assertEqual(
            nodes_by_id["node_transform"]["unavailable_reason"],
            "Signal Pack is not loaded in this session.",
        )
        self.assertEqual(
            {
                port["key"]: port["label"]
                for port in nodes_by_id["node_source"]["ports"]
            }["signal_out"],
            "Saved Signal",
        )
        transform_ports = {
            port["key"]: port["label"]
            for port in nodes_by_id["node_transform"]["ports"]
        }
        self.assertNotIn("signal_in", transform_ports)
        self.assertEqual(transform_ports["signal_out"], "Saved Result")
        self.assertEqual(
            nodes_by_id["node_transform"]["locked_state"],
            {
                "is_locked": True,
                "reason": "missing_addon",
                "label": "Requires add-on",
                "summary": "Signal Pack is not loaded in this session.",
                "focus_addon_id": "tests.addons.signal_pack",
            },
        )

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

    def test_scene_bridge_exposes_port_lock_and_view_filter_slots_through_split_command_surface(self) -> None:
        package_root = _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene"
        command_text = (package_root / "command_bridge.py").read_text(encoding="utf-8")
        state_support_text = (package_root / "state_support.py").read_text(encoding="utf-8")
        helper_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_mutation_history.py"
        ).read_text(encoding="utf-8")
        selection_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_mutation" / "selection_and_scope_ops.py"
        ).read_text(encoding="utf-8")

        for snippet, text in (
            ("def set_port_locked(self, node_id: str, key: str, locked: bool) -> bool:", command_text),
            ("def set_hide_locked_ports(self, hide_locked_ports: bool) -> bool:", command_text),
            ("def set_hide_optional_ports(self, hide_optional_ports: bool) -> bool:", command_text),
            ("def set_port_locked(self, node_id: str, key: str, locked: bool) -> bool:", state_support_text),
            ("def set_hide_locked_ports(self, hide_locked_ports: bool) -> bool:", state_support_text),
            ("def set_hide_optional_ports(self, hide_optional_ports: bool) -> bool:", state_support_text),
            ("GraphSceneMutationHistory.set_port_locked = _selection_ops.set_port_locked", helper_text),
            ("GraphSceneMutationHistory.set_hide_locked_ports = _selection_ops.set_hide_locked_ports", helper_text),
            ("GraphSceneMutationHistory.set_hide_optional_ports = _selection_ops.set_hide_optional_ports", helper_text),
            ("def set_port_locked(self, node_id: str, key: str, locked: bool) -> bool:", selection_text),
            ("def set_hide_locked_ports(self, hide_locked_ports: bool) -> bool:", selection_text),
            ("def set_hide_optional_ports(self, hide_optional_ports: bool) -> bool:", selection_text),
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, text)

        scene = GraphSceneBridge()
        scene_meta = scene.metaObject()
        command_meta = scene.command_bridge.metaObject()
        for signature in (
            b"set_port_locked(QString,QString,bool)",
            b"set_hide_locked_ports(bool)",
            b"set_hide_optional_ports(bool)",
        ):
            with self.subTest(signature=signature):
                self.assertGreaterEqual(scene_meta.indexOfMethod(signature), 0)
                self.assertGreaterEqual(command_meta.indexOfMethod(signature), 0)

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
            "collision_avoidance_ops.py": package_root / "collision_avoidance_ops.py",
            "grouping_and_subnode_ops.py": package_root / "grouping_and_subnode_ops.py",
            "comment_backdrop_ops.py": package_root / "comment_backdrop_ops.py",
        }

        self.assertTrue(package_root.is_dir())
        for snippet in (
            "graph_scene_mutation.policy",
            "graph_scene_mutation.selection_and_scope_ops",
            "graph_scene_mutation.clipboard_and_fragment_ops",
            "graph_scene_mutation.alignment_and_distribution_ops",
            "graph_scene_mutation.collision_avoidance_ops",
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
            module.GraphSceneMutationHistory.expand_collision_avoidance_updates.__module__,
            "ea_node_editor.ui_qml.graph_scene_mutation.collision_avoidance_ops",
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
        facade_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_canvas_bridge.py"
        ).read_text(encoding="utf-8")
        canvas_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "GraphCanvas.qml"
        ).read_text(encoding="utf-8")
        root_bindings_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "graph_canvas" / "GraphCanvasRootBindings.qml"
        ).read_text(encoding="utf-8")
        context_menus_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "graph_canvas" / "GraphCanvasContextMenus.qml"
        ).read_text(encoding="utf-8")
        node_delegate_text = (
            _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "graph_canvas" / "GraphCanvasNodeDelegate.qml"
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
        self.assertIn("readonly property var graphActionBridgeRef: rootBindings.graphActionBridgeRef", canvas_text)
        self.assertIn("sceneBridge: root.sceneStateBridge", canvas_text)
        self.assertIn("sceneCommandBridge: root.sceneCommandBridge", canvas_text)
        self.assertIn("graphActionBridge: root.graphActionBridge", canvas_text)
        self.assertIn("graphActionBridge: root.graphActionBridgeRef", canvas_text)
        self.assertIn("property var graphActionBridge: null", root_bindings_text)
        self.assertIn("readonly property var graphActionBridgeRef: root.graphActionBridge || null", root_bindings_text)
        self.assertIn("root.graphActionBridge.trigger_graph_action(actionId, payload || ({}))", context_menus_text)
        self.assertIn("graphActionBridge.trigger_graph_action(actionId, payload)", node_delegate_text)
        self.assertIn("payload.inline_title_edit = true", node_delegate_text)
        for retired_snippet in (
            "def request_wrap_selected_nodes_in_comment_backdrop",
            "def request_edit_flow_edge_style",
            "def request_remove_edge",
            "def request_publish_custom_workflow_from_node",
            "def request_edit_passive_node_style",
            "def request_rename_node",
            "def request_ungroup_node",
            "def request_remove_node",
            "def request_duplicate_node",
            "def request_open_comment_peek",
        ):
            with self.subTest(retired_snippet=retired_snippet):
                self.assertNotIn(retired_snippet, command_text)
                self.assertNotIn(retired_snippet, facade_text)

        scene = GraphSceneBridge()
        canvas_state_bridge = GraphCanvasStateBridge(scene_bridge=scene)
        canvas_command_bridge = GraphCanvasCommandBridge(scene_bridge=scene)

        self.assertIs(canvas_state_bridge.scene_bridge, scene)
        self.assertIs(canvas_state_bridge.scene_state_source, scene.state_bridge)
        self.assertIs(canvas_state_bridge.scene_policy_source, scene.policy_bridge)
        self.assertIs(canvas_command_bridge.scene_bridge, scene)
        self.assertIs(canvas_command_bridge.scene_command_source, scene.command_bridge)
        self.assertIs(canvas_command_bridge.scene_policy_source, scene.policy_bridge)
        command_meta = canvas_command_bridge.metaObject()
        for signature in (
            b"request_open_subnode_scope(QString)",
            b"request_close_comment_peek()",
            b"request_delete_selected_graph_items(QVariantList)",
            b"set_node_geometry(QString,double,double,double,double)",
        ):
            with self.subTest(retained_command_signature=signature):
                self.assertGreaterEqual(command_meta.indexOfMethod(signature), 0)
        for signature in (
            b"request_edit_flow_edge_style(QString)",
            b"request_remove_edge(QString)",
            b"request_publish_custom_workflow_from_node(QString)",
            b"request_edit_passive_node_style(QString)",
            b"request_remove_node(QString)",
            b"request_duplicate_node(QString)",
            b"request_wrap_selected_nodes_in_comment_backdrop()",
            b"request_open_comment_peek(QString)",
        ):
            with self.subTest(retired_command_signature=signature):
                self.assertLess(command_meta.indexOfMethod(signature), 0)

    def test_graph_canvas_state_bridge_defaults_view_filters_before_scene_binding(self) -> None:
        scene = GraphSceneBridge()
        canvas_state_bridge = GraphCanvasStateBridge(scene_bridge=scene)

        self.assertFalse(canvas_state_bridge.hide_locked_ports)
        self.assertFalse(canvas_state_bridge.hide_optional_ports)

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

    def test_expand_collision_avoidance_moves_nearby_objects_in_toggle_history_group(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)
        history = RuntimeGraphHistory()
        scene.bind_runtime_history(history)

        backdrop_id = scene.add_node_from_type(COMMENT_BACKDROP_TYPE_ID, 100.0, 100.0)
        scene.set_node_geometry(backdrop_id, 100.0, 100.0, 420.0, 260.0)
        inner_id = scene.add_node_from_type(LOGGER_TYPE_ID, 160.0, 160.0)
        blocker_id = scene.add_node_from_type(LOGGER_TYPE_ID, 470.0, 180.0)
        scene.set_node_collapsed(backdrop_id, True)
        history.clear_workspace(workspace_id)

        workspace = model.project.workspaces[workspace_id]
        inner_before = (float(workspace.nodes[inner_id].x), float(workspace.nodes[inner_id].y))
        blocker_before = (float(workspace.nodes[blocker_id].x), float(workspace.nodes[blocker_id].y))

        scene.set_node_collapsed(backdrop_id, False)

        self.assertFalse(workspace.nodes[backdrop_id].collapsed)
        self.assertEqual(history.undo_depth(workspace_id), 1)
        self.assertAlmostEqual(float(workspace.nodes[backdrop_id].x), 100.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[backdrop_id].y), 100.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].x), inner_before[0], places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].y), inner_before[1], places=6)
        self.assertGreater(float(workspace.nodes[blocker_id].x), blocker_before[0] + 10.0)

        blocker_after_expand = (float(workspace.nodes[blocker_id].x), float(workspace.nodes[blocker_id].y))
        self.assertIsNotNone(history.undo_workspace(workspace_id, workspace))
        scene.refresh_workspace_from_model(workspace_id)
        self.assertTrue(workspace.nodes[backdrop_id].collapsed)
        self.assertAlmostEqual(float(workspace.nodes[blocker_id].x), blocker_before[0], places=6)
        self.assertAlmostEqual(float(workspace.nodes[blocker_id].y), blocker_before[1], places=6)

        self.assertIsNotNone(history.redo_workspace(workspace_id, workspace))
        scene.refresh_workspace_from_model(workspace_id)
        self.assertFalse(workspace.nodes[backdrop_id].collapsed)
        self.assertAlmostEqual(float(workspace.nodes[blocker_id].x), blocker_after_expand[0], places=6)
        self.assertAlmostEqual(float(workspace.nodes[blocker_id].y), blocker_after_expand[1], places=6)

        scene.set_node_collapsed(backdrop_id, True)
        self.assertTrue(workspace.nodes[backdrop_id].collapsed)
        self.assertAlmostEqual(float(workspace.nodes[blocker_id].x), blocker_after_expand[0], places=6)
        self.assertAlmostEqual(float(workspace.nodes[blocker_id].y), blocker_after_expand[1], places=6)

    def test_expand_collision_avoidance_respects_disabled_preference(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        preferences = _ExpandCollisionPreferenceSource({"enabled": False})
        scene = GraphSceneBridge(preferences)
        scene.set_workspace(model, registry, workspace_id)

        expanding_id = scene.add_node_from_type(LOGGER_TYPE_ID, 100.0, 100.0)
        blocker_id = scene.add_node_from_type(LOGGER_TYPE_ID, 240.0, 100.0)
        scene.set_node_collapsed(expanding_id, True)
        workspace = model.project.workspaces[workspace_id]
        blocker_before = (float(workspace.nodes[blocker_id].x), float(workspace.nodes[blocker_id].y))

        scene.set_node_collapsed(expanding_id, False)

        self.assertFalse(workspace.nodes[expanding_id].collapsed)
        self.assertAlmostEqual(float(workspace.nodes[blocker_id].x), blocker_before[0], places=6)
        self.assertAlmostEqual(float(workspace.nodes[blocker_id].y), blocker_before[1], places=6)

    def test_expand_collision_avoidance_reach_setting_controls_chain_displacement(self) -> None:
        local_workspace = self._expand_collision_reach_workspace(
            {
                "enabled": True,
                "strategy": "nearest",
                "scope": "all_movable",
                "radius_mode": "local",
                "local_radius_preset": "small",
                "gap_preset": "normal",
                "animate": False,
            }
        )
        unbounded_workspace = self._expand_collision_reach_workspace(
            {
                "enabled": True,
                "strategy": "nearest",
                "scope": "all_movable",
                "radius_mode": "unbounded",
                "local_radius_preset": "small",
                "gap_preset": "normal",
                "animate": False,
            }
        )

        self.assertAlmostEqual(float(local_workspace["far_after_x"]), float(local_workspace["far_before_x"]), places=6)
        self.assertGreater(float(unbounded_workspace["far_after_x"]), float(unbounded_workspace["far_before_x"]) + 10.0)

    def _expand_collision_reach_workspace(self, settings: dict[str, object]) -> dict[str, float]:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        preferences = _ExpandCollisionPreferenceSource(settings)
        scene = GraphSceneBridge(preferences)
        scene.set_workspace(model, registry, workspace_id)

        expanding_id = scene.add_node_from_type(COMMENT_BACKDROP_TYPE_ID, 100.0, 100.0)
        scene.set_node_geometry(expanding_id, 100.0, 100.0, 420.0, 260.0)
        wide_blocker_id = scene.add_node_from_type(COMMENT_BACKDROP_TYPE_ID, 470.0, 180.0)
        scene.set_node_geometry(wide_blocker_id, 470.0, 180.0, 700.0, 180.0)
        far_blocker_id = scene.add_node_from_type(LOGGER_TYPE_ID, 1100.0, 200.0)
        scene.set_node_collapsed(expanding_id, True)

        workspace = model.project.workspaces[workspace_id]
        far_before_x = float(workspace.nodes[far_blocker_id].x)
        scene.set_node_collapsed(expanding_id, False)

        return {
            "far_before_x": far_before_x,
            "far_after_x": float(workspace.nodes[far_blocker_id].x),
        }


if __name__ == "__main__":
    unittest.main()
