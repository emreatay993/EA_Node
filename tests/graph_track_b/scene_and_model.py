from __future__ import annotations

import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QObject, QRectF, QMetaObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QFontMetricsF
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.hierarchy import subtree_node_ids
from ea_node_editor.graph.model import GraphModel, ViewState
from ea_node_editor.graph.mutation_service import WorkspaceMutationService
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.decorators import node_type
from ea_node_editor.nodes.types import ExecutionContext, NodeResult, PortSpec
from ea_node_editor.ui.graph_interactions import GraphInteractions
from ea_node_editor.ui.shell.runtime_history import (
    ACTION_ADD_NODE,
    ACTION_EDIT_PROPERTY,
    ACTION_RENAME_NODE,
    RuntimeGraphHistory,
)
from ea_node_editor.ui.graph_theme import (
    GRAPH_CATEGORY_ACCENT_TOKENS_V1,
    GRAPH_STITCH_DARK_EDGE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1,
    resolve_graph_theme,
)
from ea_node_editor.ui.theme import STITCH_DARK_V1, STITCH_LIGHT_V1
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

_GRAPH_CANVAS_QML_PATH = (
    Path(__file__).resolve().parents[2] / "ea_node_editor" / "ui_qml" / "components" / "GraphCanvas.qml"
)
_NODE_CARD_QML_PATH = (
    Path(__file__).resolve().parents[2]
    / "ea_node_editor"
    / "ui_qml"
    / "components"
    / "graph"
    / "NodeCard.qml"
)


@node_type(
    type_id="tests.track_b_flowchart_decision",
    display_name="Decision",
    category="Tests",
    icon="branch",
    ports=(
        PortSpec("top", "neutral", "flow", "flow", side="top", allow_multiple_connections=True),
        PortSpec("right", "neutral", "flow", "flow", side="right", allow_multiple_connections=True),
        PortSpec("bottom", "neutral", "flow", "flow", side="bottom", allow_multiple_connections=True),
        PortSpec("left", "neutral", "flow", "flow", side="left", allow_multiple_connections=True),
    ),
    properties=(),
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="decision",
)
class _TrackBFlowchartDecisionNode:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id="tests.track_b_flowchart_connector",
    display_name="Connector",
    category="Tests",
    icon="circle",
    ports=(
        PortSpec("top", "neutral", "flow", "flow", side="top", allow_multiple_connections=True),
        PortSpec("right", "neutral", "flow", "flow", side="right", allow_multiple_connections=True),
        PortSpec("bottom", "neutral", "flow", "flow", side="bottom", allow_multiple_connections=True),
        PortSpec("left", "neutral", "flow", "flow", side="left", allow_multiple_connections=True),
    ),
    properties=(),
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="connector",
)
class _TrackBFlowchartConnectorNode:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


def _color_name(value: object, *, include_alpha: bool = False) -> str:
    name_format = QColor.NameFormat.HexArgb if include_alpha else QColor.NameFormat.HexRgb
    return QColor(value).name(name_format)


def _alpha_color_name(value: str, alpha: float) -> str:
    color = QColor(value)
    color.setAlphaF(alpha)
    return _color_name(color, include_alpha=True)


class _GraphCanvasPreferenceBridge(QObject):
    graphics_preferences_changed = pyqtSignal()
    snap_to_grid_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._graphics_show_grid = True
        self._graphics_grid_style = "lines"
        self._graphics_show_minimap = True
        self._graphics_minimap_expanded = True
        self._graphics_show_port_labels = True
        self._snap_to_grid_enabled = False
        self.minimap_update_history: list[bool] = []

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_grid(self) -> bool:
        return bool(self._graphics_show_grid)

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_grid_style(self) -> str:
        return str(self._graphics_grid_style)

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_minimap(self) -> bool:
        return bool(self._graphics_show_minimap)

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_minimap_expanded(self) -> bool:
        return bool(self._graphics_minimap_expanded)

    @pyqtProperty(bool, notify=snap_to_grid_changed)
    def snap_to_grid_enabled(self) -> bool:
        return bool(self._snap_to_grid_enabled)

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_port_labels(self) -> bool:
        return bool(self._graphics_show_port_labels)

    @pyqtProperty(float, constant=True)
    def snap_grid_size(self) -> float:
        return 20.0

    def set_graphics_show_grid_value(self, value: bool) -> None:
        normalized = bool(value)
        if self._graphics_show_grid == normalized:
            return
        self._graphics_show_grid = normalized
        self.graphics_preferences_changed.emit()

    def set_graphics_grid_style_value(self, value: str) -> None:
        normalized = str(value or "lines").strip().lower()
        if normalized not in {"lines", "points"}:
            normalized = "lines"
        if self._graphics_grid_style == normalized:
            return
        self._graphics_grid_style = normalized
        self.graphics_preferences_changed.emit()

    def set_graphics_show_minimap_value(self, value: bool) -> None:
        normalized = bool(value)
        if self._graphics_show_minimap == normalized:
            return
        self._graphics_show_minimap = normalized
        self.graphics_preferences_changed.emit()

    def set_graphics_minimap_expanded_value(self, value: bool) -> None:
        normalized = bool(value)
        if self._graphics_minimap_expanded == normalized:
            return
        self._graphics_minimap_expanded = normalized
        self.graphics_preferences_changed.emit()

    def set_graphics_show_port_labels_value(self, value: bool) -> None:
        normalized = bool(value)
        if self._graphics_show_port_labels == normalized:
            return
        self._graphics_show_port_labels = normalized
        self.graphics_preferences_changed.emit()

    def set_snap_to_grid_enabled_value(self, value: bool) -> None:
        normalized = bool(value)
        if self._snap_to_grid_enabled == normalized:
            return
        self._snap_to_grid_enabled = normalized
        self.snap_to_grid_changed.emit()

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        normalized = bool(expanded)
        self.minimap_update_history.append(normalized)
        if self._graphics_minimap_expanded == normalized:
            return
        self._graphics_minimap_expanded = normalized
        self.graphics_preferences_changed.emit()


class GraphModelTrackBTests(unittest.TestCase):
    def test_add_move_connect_remove_node_operations(self) -> None:
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        source = model.add_node(workspace_id, "core.start", "Start", 0.0, 0.0)
        target = model.add_node(workspace_id, "core.end", "End", 300.0, 80.0)

        model.set_node_position(workspace_id, source.node_id, 25.0, 45.0)
        moved = model.project.workspaces[workspace_id].nodes[source.node_id]
        self.assertEqual((moved.x, moved.y), (25.0, 45.0))

        edge = model.add_edge(workspace_id, source.node_id, "exec_out", target.node_id, "exec_in")
        duplicate = model.add_edge(workspace_id, source.node_id, "exec_out", target.node_id, "exec_in")
        self.assertEqual(edge.edge_id, duplicate.edge_id)
        self.assertEqual(len(model.project.workspaces[workspace_id].edges), 1)

        model.remove_node(workspace_id, source.node_id)
        workspace = model.project.workspaces[workspace_id]
        self.assertNotIn(source.node_id, workspace.nodes)
        self.assertEqual(workspace.edges, {})

    def test_validated_mutation_boundary_prunes_subnode_edges_when_pin_kind_changes(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        mutations = model.validated_mutations(workspace.workspace_id, registry)
        self.assertIsInstance(mutations, WorkspaceMutationService)

        def _add_node(
            type_id: str,
            title: str,
            x: float,
            y: float,
            *,
            parent_node_id: str | None = None,
        ):
            spec = registry.get_spec(type_id)
            return mutations.add_node(
                type_id=type_id,
                title=title,
                x=x,
                y=y,
                properties=registry.default_properties(type_id),
                exposed_ports={port.key: port.exposed for port in spec.ports},
                parent_node_id=parent_node_id,
            )

        source = _add_node("core.start", "Start", 0.0, 0.0)
        shell = _add_node("core.subnode", "Shell", 240.0, 40.0)
        pin_in = _add_node("core.subnode_input", "Input", 40.0, 80.0, parent_node_id=shell.node_id)
        inner = _add_node("core.logger", "Inner", 320.0, 140.0, parent_node_id=shell.node_id)

        mutations.set_node_property(pin_in.node_id, "kind", "exec")
        mutations.set_exposed_port(shell.node_id, pin_in.node_id, True)

        shell_edge = mutations.add_edge(
            source_node_id=source.node_id,
            source_port_key="exec_out",
            target_node_id=shell.node_id,
            target_port_key=pin_in.node_id,
        )
        inner_edge = mutations.add_edge(
            source_node_id=pin_in.node_id,
            source_port_key="pin",
            target_node_id=inner.node_id,
            target_port_key="exec_in",
        )

        self.assertIn(shell_edge.edge_id, workspace.edges)
        self.assertIn(inner_edge.edge_id, workspace.edges)

        mutations.set_node_property(pin_in.node_id, "kind", "data")

        self.assertNotIn(shell_edge.edge_id, workspace.edges)
        self.assertNotIn(inner_edge.edge_id, workspace.edges)
        self.assertEqual(workspace.nodes[pin_in.node_id].properties["kind"], "data")

    def test_workspace_mutation_service_manages_view_state_without_registry(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        service = model.mutation_service(workspace.workspace_id)

        changed = service.save_active_view_state(
            zoom=1.25,
            pan_x=125.0,
            pan_y=220.0,
        )

        self.assertTrue(changed)
        active_view = service.active_view_state()
        self.assertAlmostEqual(active_view.zoom, 1.25, places=6)
        self.assertAlmostEqual(active_view.pan_x, 125.0, places=6)
        self.assertAlmostEqual(active_view.pan_y, 220.0, places=6)

        created_view = service.create_view(
            name="Review",
            source_view_id=active_view.view_id,
        )
        self.assertEqual(workspace.active_view_id, created_view.view_id)
        self.assertEqual(created_view.name, "Review")
        self.assertAlmostEqual(created_view.zoom, 1.25, places=6)
        self.assertAlmostEqual(created_view.pan_x, 125.0, places=6)
        self.assertAlmostEqual(created_view.pan_y, 220.0, places=6)

        service.set_active_view(active_view.view_id)
        self.assertEqual(workspace.active_view_id, active_view.view_id)

    def test_workspace_mutation_service_clamps_pdf_panel_page_numbers_on_property_updates(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        service = model.validated_mutations(workspace.workspace_id, registry)
        spec = registry.get_spec("passive.media.pdf_panel")
        node = service.add_node(
            type_id=spec.type_id,
            title=spec.display_name,
            x=40.0,
            y=60.0,
            properties=registry.default_properties(spec.type_id),
            exposed_ports={port.key: port.exposed for port in spec.ports},
        )

        with patch("ea_node_editor.graph.mutation_service.clamp_pdf_page_number", return_value=2):
            source_path = service.set_node_property(node.node_id, "source_path", "/tmp/clamped.pdf")
            page_updates = service.set_node_properties(node.node_id, {"page_number": 99})

        self.assertEqual(source_path, "/tmp/clamped.pdf")
        self.assertEqual(page_updates, {"page_number": 2})
        self.assertEqual(workspace.nodes[node.node_id].properties["page_number"], 2)

    def test_graph_scene_payload_builder_normalization_path_is_read_only_while_payload_clamps_pdf_pages(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        spec = registry.get_spec("passive.media.pdf_panel")
        node = model.add_node(
            workspace.workspace_id,
            spec.type_id,
            spec.display_name,
            40.0,
            60.0,
            properties={
                **registry.default_properties(spec.type_id),
                "source_path": "/tmp/clamped.pdf",
                "page_number": 99,
            },
            exposed_ports={port.key: port.exposed for port in spec.ports},
        )
        builder = GraphScenePayloadBuilder()

        with patch("ea_node_editor.ui_qml.graph_scene_payload_builder.clamp_pdf_page_number", return_value=2):
            builder.normalize_pdf_panel_pages(
                model=model,
                registry=registry,
                workspace=workspace,
            )
            self.assertEqual(workspace.nodes[node.node_id].properties["page_number"], 99)
            nodes_payload, _minimap_payload, _edges_payload = builder.rebuild_models(
                model=model,
                registry=registry,
                workspace_id=workspace.workspace_id,
                scope_path=(),
                graph_theme_bridge=None,
            )

        payload = next(item for item in nodes_payload if item["node_id"] == node.node_id)
        self.assertEqual(workspace.nodes[node.node_id].properties["page_number"], 99)
        self.assertEqual(payload["properties"]["page_number"], 2)


class GraphSceneBridgeTrackBTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.workspace_id = self.model.active_workspace.workspace_id
        self.preference_bridge = _GraphCanvasPreferenceBridge()
        self.scene = GraphSceneBridge(self.preference_bridge)
        self.scene.set_workspace(self.model, self.registry, self.workspace_id)
        self.view = ViewportBridge()
        self.view.set_viewport_size(1280.0, 720.0)

    def test_selection_signal_reports_select_and_clear(self) -> None:
        node_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        events: list[str] = []
        self.scene.node_selected.connect(events.append)

        self.scene.focus_node(node_id)
        self.assertEqual(events[-1], node_id)

        self.scene.clearSelection()
        self.assertEqual(events[-1], "")

    def test_selection_only_updates_do_not_rebuild_models(self) -> None:
        node_a = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        node_b = self.scene.add_node_from_type("core.end", 320.0, 40.0)
        node_c = self.scene.add_node_from_type("core.logger", 640.0, 80.0)

        baseline_nodes = copy.deepcopy(self.scene.nodes_model)
        baseline_minimap = copy.deepcopy(self.scene.minimap_nodes_model)
        nodes_changed: list[str] = []
        edges_changed: list[str] = []
        selection_events: list[dict[str, bool]] = []
        node_selected_events: list[str] = []
        self.scene.nodes_changed.connect(lambda: nodes_changed.append("nodes"))
        self.scene.edges_changed.connect(lambda: edges_changed.append("edges"))
        self.scene.selection_changed.connect(
            lambda: selection_events.append(dict(self.scene.selected_node_lookup))
        )
        self.scene.node_selected.connect(node_selected_events.append)

        self.scene.select_node(node_b)
        self.assertEqual(self.scene.selected_node_id(), node_b)
        self.assertEqual(self.scene.selected_node_lookup, {node_b: True})
        self.assertEqual(selection_events[-1], {node_b: True})
        self.assertEqual(node_selected_events[-1], node_b)
        self.assertEqual(nodes_changed, [])
        self.assertEqual(edges_changed, [])
        self.assertEqual(self.scene.nodes_model, baseline_nodes)
        self.assertEqual(self.scene.minimap_nodes_model, baseline_minimap)

        selection_count_before = len(selection_events)
        node_selected_count_before = len(node_selected_events)
        self.scene.select_node(node_b)
        self.assertEqual(len(selection_events), selection_count_before)
        self.assertEqual(len(node_selected_events), node_selected_count_before)
        self.assertEqual(nodes_changed, [])
        self.assertEqual(edges_changed, [])

        self.scene.select_node(node_a, True)
        self.assertEqual(self.scene.selected_node_lookup, {node_b: True, node_a: True})
        self.assertEqual(selection_events[-1], {node_b: True, node_a: True})
        self.assertEqual(node_selected_events[-1], node_a)
        self.assertEqual(nodes_changed, [])
        self.assertEqual(edges_changed, [])
        self.assertEqual(self.scene.nodes_model, baseline_nodes)
        self.assertEqual(self.scene.minimap_nodes_model, baseline_minimap)

        self.scene.clearSelection()
        self.assertEqual(self.scene.selected_node_lookup, {})
        self.assertEqual(selection_events[-1], {})
        self.assertEqual(node_selected_events[-1], "")
        self.assertEqual(nodes_changed, [])
        self.assertEqual(edges_changed, [])
        self.assertEqual(self.scene.nodes_model, baseline_nodes)
        self.assertEqual(self.scene.minimap_nodes_model, baseline_minimap)

        focused_center = self.scene.focus_node(node_c)
        self.assertIsNotNone(focused_center)
        self.assertEqual(self.scene.selected_node_id(), node_c)
        self.assertEqual(self.scene.selected_node_lookup, {node_c: True})
        self.assertEqual(selection_events[-1], {node_c: True})
        self.assertEqual(node_selected_events[-1], node_c)
        self.assertEqual(nodes_changed, [])
        self.assertEqual(edges_changed, [])
        self.assertEqual(self.scene.nodes_model, baseline_nodes)
        self.assertEqual(self.scene.minimap_nodes_model, baseline_minimap)

    def test_connect_move_and_remove_keep_model_and_scene_in_sync(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.end", 320.0, 40.0)
        edge_id = self.scene.connect_nodes(source_id, target_id)

        self.scene.move_node(source_id, 120.0, 90.0)

        workspace = self.model.project.workspaces[self.workspace_id]
        source_model = workspace.nodes[source_id]
        self.assertAlmostEqual(source_model.x, 120.0, places=4)
        self.assertAlmostEqual(source_model.y, 90.0, places=4)

        self.scene.remove_edge(edge_id)
        self.assertNotIn(edge_id, workspace.edges)
        self.assertIsNone(self.scene.edge_item(edge_id))

        new_edge_id = self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.scene.remove_node(source_id)
        self.assertNotIn(source_id, workspace.nodes)
        self.assertNotIn(new_edge_id, workspace.edges)
        self.assertIsNone(self.scene.node_item(source_id))
        self.assertIsNone(self.scene.edge_item(new_edge_id))

    def test_resize_node_clamps_to_surface_minimum_and_records_history(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        node_id = self.scene.add_node_from_type("core.logger", 20.0, 30.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        history.clear_workspace(self.workspace_id)

        self.scene.resize_node(node_id, 10.0, 5.0)

        node = workspace.nodes[node_id]
        self.assertEqual(history.undo_depth(self.workspace_id), 1)
        self.assertGreaterEqual(float(node.custom_width or 0.0), 120.0)
        self.assertGreaterEqual(float(node.custom_height or 0.0), 50.0)

        payload = next(item for item in self.scene.nodes_model if item["node_id"] == node_id)
        self.assertAlmostEqual(payload["width"], float(node.custom_width or 0.0), places=6)
        self.assertAlmostEqual(payload["height"], float(node.custom_height or 0.0), places=6)

        self.assertIsNotNone(history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertIsNone(workspace.nodes[node_id].custom_width)
        self.assertIsNone(workspace.nodes[node_id].custom_height)

    def test_collapse_expand_updates_node_payload(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        self.scene.set_node_collapsed(source_id, True)

        payload = {item["node_id"]: item for item in self.scene.nodes_model}
        self.assertTrue(payload[source_id]["collapsed"])
        self.assertLess(payload[source_id]["width"], 150.0)

        self.scene.set_node_collapsed(source_id, False)
        payload = {item["node_id"]: item for item in self.scene.nodes_model}
        self.assertFalse(payload[source_id]["collapsed"])

    def test_scene_payloads_include_node_and_edge_visual_metadata_contracts(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.end", 320.0, 40.0)
        edge_id = self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[source_id].visual_style = {"fill": "#102030", "badge": {"shape": "pill"}}
        workspace.edges[edge_id].label = "Primary path"
        workspace.edges[edge_id].visual_style = {"stroke": "dashed", "arrow": {"kind": "none"}}

        self.scene.refresh_workspace_from_model(self.workspace_id)

        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}

        self.assertEqual(node_payload[source_id]["runtime_behavior"], "active")
        self.assertEqual(node_payload[source_id]["surface_family"], "standard")
        self.assertEqual(node_payload[source_id]["surface_variant"], "")
        surface_metrics = node_payload[source_id]["surface_metrics"]
        self.assertEqual(surface_metrics["default_width"], 210.0)
        self.assertAlmostEqual(
            surface_metrics["min_width"],
            max(
                surface_metrics["standard_title_full_width"],
                surface_metrics["standard_port_label_min_width"],
            ),
            places=6,
        )
        self.assertEqual(surface_metrics["min_height"], 50.0)
        self.assertEqual(surface_metrics["standard_left_label_width"], 0.0)
        self.assertGreater(surface_metrics["standard_right_label_width"], 0.0)
        self.assertEqual(surface_metrics["standard_port_gutter"], 21.5)
        self.assertEqual(surface_metrics["standard_center_gap"], 24.0)
        self.assertEqual(
            node_payload[source_id]["visual_style"],
            {"fill": "#102030", "badge": {"shape": "pill"}},
        )
        self.assertEqual(edge_payload[edge_id]["label"], "Primary path")
        self.assertEqual(
            edge_payload[edge_id]["visual_style"],
            {"stroke": "dashed", "arrow": {"kind": "none"}},
        )
        self.assertEqual(edge_payload[edge_id]["source_port_kind"], "exec")
        self.assertEqual(edge_payload[edge_id]["target_port_kind"], "exec")

    def test_standard_node_min_width_tracks_port_label_visibility_preference(self) -> None:
        node_id = self.scene.add_node_from_type("core.logger", 40.0, 60.0)
        self.scene.set_node_port_label(node_id, "message", "Primary Input Payload")
        self.scene.set_node_port_label(node_id, "exec_out", "Dispatch Result Token")

        self.preference_bridge.set_graphics_show_port_labels_value(False)
        self.scene.refresh_workspace_from_model(self.workspace_id)
        payload_by_id = {item["node_id"]: item for item in self.scene.nodes_model}
        off_metrics = payload_by_id[node_id]["surface_metrics"]

        self.preference_bridge.set_graphics_show_port_labels_value(True)
        self.scene.refresh_workspace_from_model(self.workspace_id)
        payload_by_id = {item["node_id"]: item for item in self.scene.nodes_model}
        on_metrics = payload_by_id[node_id]["surface_metrics"]

        self.assertAlmostEqual(off_metrics["min_width"], off_metrics["standard_title_full_width"], places=6)
        self.assertGreater(on_metrics["min_width"], off_metrics["min_width"])
        self.assertGreater(on_metrics["standard_left_label_width"], 0.0)
        self.assertGreater(on_metrics["standard_right_label_width"], 0.0)
        self.assertGreater(on_metrics["standard_port_label_min_width"], on_metrics["standard_title_full_width"])
        self.assertAlmostEqual(
            on_metrics["min_width"],
            max(
                on_metrics["standard_title_full_width"],
                on_metrics["standard_port_label_min_width"],
            ),
            places=6,
        )

    def test_standard_node_min_width_contract_matches_qt_label_widths(self) -> None:
        node_id = self.scene.add_node_from_type("core.logger", 40.0, 60.0)
        self.scene.set_node_port_label(node_id, "message", "message")
        self.scene.set_node_port_label(node_id, "exec_out", "exec_out")

        self.preference_bridge.set_graphics_show_port_labels_value(True)
        self.scene.refresh_workspace_from_model(self.workspace_id)
        payload_by_id = {item["node_id"]: item for item in self.scene.nodes_model}
        metrics = payload_by_id[node_id]["surface_metrics"]

        font = QFont(self.app.font())
        font.setPixelSize(10)
        font_metrics = QFontMetricsF(font)
        expected_left_width = float(font_metrics.horizontalAdvance("message") + 2.0)
        expected_right_width = float(font_metrics.horizontalAdvance("exec_out") + 2.0)
        expected_port_label_min_width = (
            expected_left_width
            + expected_right_width
            + (float(metrics["standard_port_gutter"]) * 2.0)
            + float(metrics["standard_center_gap"])
        )

        self.assertGreaterEqual(float(metrics["standard_left_label_width"]), expected_left_width - 0.5)
        self.assertGreaterEqual(float(metrics["standard_right_label_width"]), expected_right_width - 0.5)
        self.assertGreaterEqual(float(metrics["standard_port_label_min_width"]), expected_port_label_min_width - 1.0)
        self.assertGreaterEqual(float(metrics["min_width"]), expected_port_label_min_width - 1.0)

    def test_standard_node_rendered_width_and_resize_clamp_share_preference_aware_min_width(self) -> None:
        node_id = self.scene.add_node_from_type("core.logger", 40.0, 60.0)
        self.scene.set_node_port_label(node_id, "message", "Primary Input Payload")
        self.scene.set_node_port_label(node_id, "exec_out", "Dispatch Result Token")
        workspace = self.model.project.workspaces[self.workspace_id]
        node = workspace.nodes[node_id]

        self.preference_bridge.set_graphics_show_port_labels_value(False)
        self.scene.refresh_workspace_from_model(self.workspace_id)
        payload_by_id = {item["node_id"]: item for item in self.scene.nodes_model}
        off_payload = payload_by_id[node_id]
        off_width = float(off_payload["surface_metrics"]["min_width"]) + 18.0

        self.scene.set_node_geometry(
            node_id,
            float(node.x),
            float(node.y),
            off_width,
            float(off_payload["height"]),
        )
        payload_by_id = {item["node_id"]: item for item in self.scene.nodes_model}
        off_payload = payload_by_id[node_id]
        self.assertAlmostEqual(off_payload["width"], off_width, places=6)
        self.assertAlmostEqual(float(workspace.nodes[node_id].custom_width or 0.0), off_width, places=6)

        self.preference_bridge.set_graphics_show_port_labels_value(True)
        self.scene.refresh_workspace_from_model(self.workspace_id)
        payload_by_id = {item["node_id"]: item for item in self.scene.nodes_model}
        on_payload = payload_by_id[node_id]
        on_min_width = float(on_payload["surface_metrics"]["min_width"])

        self.assertGreater(on_min_width, off_width)
        self.assertAlmostEqual(on_payload["width"], on_min_width, places=6)
        self.assertAlmostEqual(float(workspace.nodes[node_id].custom_width or 0.0), off_width, places=6)

        self.scene.resize_node(node_id, off_width - 40.0, float(on_payload["height"]))
        payload_by_id = {item["node_id"]: item for item in self.scene.nodes_model}
        resized_payload = payload_by_id[node_id]

        self.assertAlmostEqual(resized_payload["surface_metrics"]["min_width"], on_min_width, places=6)
        self.assertAlmostEqual(resized_payload["width"], on_min_width, places=6)
        self.assertAlmostEqual(float(workspace.nodes[node_id].custom_width or 0.0), on_min_width, places=6)

    def test_style_mutations_update_payload_and_record_history(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.end", 320.0, 40.0)
        edge_id = self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        history.clear_workspace(self.workspace_id)

        self.scene.set_node_visual_style(source_id, {"fill": "#102030", "badge": {"shape": "pill"}})
        self.scene.set_edge_label(edge_id, "Primary path")
        self.scene.set_edge_visual_style(edge_id, {"stroke": "dashed", "arrow": {"kind": "none"}})

        self.assertEqual(history.undo_depth(self.workspace_id), 3)

        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}
        self.assertEqual(
            node_payload[source_id]["visual_style"],
            {"fill": "#102030", "badge": {"shape": "pill"}},
        )
        self.assertEqual(edge_payload[edge_id]["label"], "Primary path")
        self.assertEqual(
            edge_payload[edge_id]["visual_style"],
            {"stroke": "dashed", "arrow": {"kind": "none"}},
        )

    def test_flowchart_scene_payloads_publish_family_metrics_and_shape_aware_anchors(self) -> None:
        self.registry.register(_TrackBFlowchartDecisionNode)
        self.registry.register(_TrackBFlowchartConnectorNode)

        source_id = self.scene.add_node_from_type("tests.track_b_flowchart_decision", 20.0, 30.0)
        target_id = self.scene.add_node_from_type("tests.track_b_flowchart_connector", 360.0, 90.0)
        edge_id = self.scene.add_edge(source_id, "right", target_id, "left")

        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}[edge_id]
        source_payload = node_payload[source_id]

        self.assertEqual(source_payload["surface_family"], "flowchart")
        self.assertEqual(source_payload["surface_variant"], "decision")
        self.assertFalse(bool(source_payload["surface_metrics"]["use_host_chrome"]))
        self.assertTrue(bool(source_payload["surface_metrics"]["title_centered"]))
        self.assertGreaterEqual(source_payload["surface_metrics"]["min_height"], 120.0)
        self.assertGreaterEqual(source_payload["width"], 220.0)
        self.assertEqual(edge_payload["source_port_side"], "right")
        self.assertEqual(edge_payload["target_port_side"], "left")
        self.assertAlmostEqual(edge_payload["sx"], source_payload["x"] + source_payload["width"] - 0.5, places=4)
        self.assertAlmostEqual(edge_payload["sy"], source_payload["y"] + source_payload["height"] * 0.5, places=4)

    def test_builtin_flowchart_catalog_nodes_keep_display_titles_and_cardinal_neutral_ports(self) -> None:
        decision_id = self.scene.add_node_from_type("passive.flowchart.decision", 20.0, 30.0)
        end_id = self.scene.add_node_from_type("passive.flowchart.end", 360.0, 90.0)
        edge_id = self.scene.add_edge(decision_id, "right", end_id, "left")

        workspace = self.model.project.workspaces[self.workspace_id]
        self.assertEqual(workspace.nodes[decision_id].title, "Decision")
        self.assertEqual(workspace.nodes[end_id].title, "End")

        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}[edge_id]
        decision_ports = {port["key"]: port for port in node_payload[decision_id]["ports"]}

        self.assertEqual(set(decision_ports), {"top", "right", "bottom", "left"})
        self.assertTrue(all(port["direction"] == "neutral" for port in decision_ports.values()))
        self.assertEqual(decision_ports["right"]["label"], "right")
        self.assertEqual(decision_ports["left"]["label"], "left")
        self.assertEqual(decision_ports["right"]["kind"], "flow")
        self.assertEqual(decision_ports["left"]["data_type"], "flow")
        self.assertEqual(edge_payload["source_port_kind"], "flow")
        self.assertEqual(edge_payload["target_port_kind"], "flow")

    def test_connect_nodes_selects_facing_cardinal_ports_for_neutral_flowchart_nodes(self) -> None:
        horizontal_source_id = self.scene.add_node_from_type("passive.flowchart.process", 20.0, 30.0)
        horizontal_target_id = self.scene.add_node_from_type("passive.flowchart.process", 360.0, 90.0)
        vertical_source_id = self.scene.add_node_from_type("passive.flowchart.process", 720.0, 40.0)
        vertical_target_id = self.scene.add_node_from_type("passive.flowchart.process", 720.0, 320.0)

        horizontal_edge_id = self.scene.connect_nodes(horizontal_source_id, horizontal_target_id)
        vertical_edge_id = self.scene.connect_nodes(vertical_source_id, vertical_target_id)

        workspace = self.model.project.workspaces[self.workspace_id]
        horizontal_edge = workspace.edges[horizontal_edge_id]
        vertical_edge = workspace.edges[vertical_edge_id]

        self.assertEqual(horizontal_edge.source_node_id, horizontal_source_id)
        self.assertEqual(horizontal_edge.source_port_key, "right")
        self.assertEqual(horizontal_edge.target_node_id, horizontal_target_id)
        self.assertEqual(horizontal_edge.target_port_key, "left")
        self.assertEqual(vertical_edge.source_node_id, vertical_source_id)
        self.assertEqual(vertical_edge.source_port_key, "bottom")
        self.assertEqual(vertical_edge.target_node_id, vertical_target_id)
        self.assertEqual(vertical_edge.target_port_key, "top")

    def test_connect_nodes_selects_facing_cardinal_ports_for_non_flowchart_passive_nodes(self) -> None:
        planning_source_id = self.scene.add_node_from_type("passive.planning.task_card", 20.0, 30.0)
        planning_target_id = self.scene.add_node_from_type("passive.planning.task_card", 360.0, 90.0)
        note_source_id = self.scene.add_node_from_type("passive.annotation.sticky_note", 720.0, 40.0)
        note_target_id = self.scene.add_node_from_type("passive.annotation.sticky_note", 720.0, 320.0)

        planning_edge_id = self.scene.connect_nodes(planning_source_id, planning_target_id)
        note_edge_id = self.scene.connect_nodes(note_source_id, note_target_id)

        workspace = self.model.project.workspaces[self.workspace_id]
        planning_edge = workspace.edges[planning_edge_id]
        note_edge = workspace.edges[note_edge_id]

        self.assertEqual(planning_edge.source_node_id, planning_source_id)
        self.assertEqual(planning_edge.source_port_key, "right")
        self.assertEqual(planning_edge.target_node_id, planning_target_id)
        self.assertEqual(planning_edge.target_port_key, "left")
        self.assertEqual(note_edge.source_node_id, note_source_id)
        self.assertEqual(note_edge.source_port_key, "bottom")
        self.assertEqual(note_edge.target_node_id, note_target_id)
        self.assertEqual(note_edge.target_port_key, "top")

    def test_non_flowchart_passive_edge_payloads_publish_cardinal_side_metadata(self) -> None:
        source_id = self.scene.add_node_from_type("passive.planning.task_card", 20.0, 30.0)
        target_id = self.scene.add_node_from_type("passive.media.image_panel", 360.0, 90.0)
        edge_id = self.scene.add_edge(source_id, "right", target_id, "left")

        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}[edge_id]

        self.assertEqual(node_payload[source_id]["surface_family"], "planning")
        self.assertEqual(node_payload[target_id]["surface_family"], "media")
        self.assertEqual(edge_payload["source_port_side"], "right")
        self.assertEqual(edge_payload["target_port_side"], "left")

    def test_connect_ports_reverses_stored_flowchart_arrow_when_neutral_click_order_reverses(self) -> None:
        forward_source_id = self.scene.add_node_from_type("passive.flowchart.process", 20.0, 30.0)
        forward_target_id = self.scene.add_node_from_type("passive.flowchart.process", 360.0, 90.0)
        reverse_source_id = self.scene.add_node_from_type("passive.flowchart.process", 720.0, 40.0)
        reverse_target_id = self.scene.add_node_from_type("passive.flowchart.process", 1060.0, 120.0)

        interactions = GraphInteractions(self.scene, self.registry)
        self.assertTrue(interactions.connect_ports(forward_source_id, "right", forward_target_id, "left").ok)
        self.assertTrue(interactions.connect_ports(reverse_target_id, "left", reverse_source_id, "right").ok)

        workspace = self.model.project.workspaces[self.workspace_id]
        edge_by_source_target = {
            (edge.source_node_id, edge.target_node_id): edge
            for edge in workspace.edges.values()
        }
        forward_edge = edge_by_source_target[(forward_source_id, forward_target_id)]
        reverse_edge = edge_by_source_target[(reverse_target_id, reverse_source_id)]

        self.assertEqual(forward_edge.source_port_key, "right")
        self.assertEqual(forward_edge.target_port_key, "left")
        self.assertEqual(reverse_edge.source_port_key, "left")
        self.assertEqual(reverse_edge.target_port_key, "right")

    def test_connect_ports_rejects_same_node_flowchart_flow_edge(self) -> None:
        node_id = self.scene.add_node_from_type("passive.flowchart.process", 20.0, 30.0)

        interactions = GraphInteractions(self.scene, self.registry)
        result = interactions.connect_ports(node_id, "right", node_id, "bottom")

        self.assertFalse(result.ok)
        self.assertEqual(result.message, "Flow edges cannot connect ports on the same node.")
        workspace = self.model.project.workspaces[self.workspace_id]
        self.assertEqual(len(workspace.edges), 0)

    def test_planning_and_annotation_scene_payloads_publish_properties_and_keep_titles_synced(self) -> None:
        task_id = self.scene.add_node_from_type("passive.planning.task_card", 40.0, 60.0)
        note_id = self.scene.add_node_from_type("passive.annotation.sticky_note", 340.0, 80.0)

        self.scene.set_node_property(task_id, "title", "Ship parser")
        self.scene.set_node_property(task_id, "body", "Finalize validation and release notes.")
        self.scene.set_node_property(task_id, "owner", "Platform")
        self.scene.set_node_property(task_id, "due_date", "2026-03-31")
        self.scene.set_node_property(task_id, "status", "in_progress")
        self.scene.set_node_title(note_id, "Release note")
        self.scene.set_node_property(note_id, "body", "Track follow-up messaging for the rollout.")

        workspace = self.model.project.workspaces[self.workspace_id]
        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        task_payload = node_payload[task_id]
        note_payload = node_payload[note_id]

        self.assertEqual(workspace.nodes[task_id].title, "Ship parser")
        self.assertEqual(workspace.nodes[note_id].title, "Release note")
        self.assertEqual(workspace.nodes[note_id].properties["title"], "Release note")

        self.assertEqual(task_payload["surface_family"], "planning")
        self.assertEqual(task_payload["surface_variant"], "task_card")
        self.assertEqual(task_payload["title"], "Ship parser")
        self.assertEqual(task_payload["properties"]["owner"], "Platform")
        self.assertEqual(task_payload["properties"]["status"], "in_progress")
        self.assertGreaterEqual(task_payload["surface_metrics"]["min_height"], 148.0)
        self.assertTrue(bool(task_payload["surface_metrics"]["use_host_chrome"]))
        self.assertEqual(note_payload["surface_family"], "annotation")
        self.assertEqual(note_payload["surface_variant"], "sticky_note")
        self.assertEqual(note_payload["title"], "Release note")
        self.assertEqual(note_payload["properties"]["body"], "Track follow-up messaging for the rollout.")
        self.assertGreaterEqual(note_payload["surface_metrics"]["min_width"], 176.0)

    def test_batch_title_updates_keep_titles_synced_for_passive_nodes_and_canonical_for_standard_and_subnode_nodes(self) -> None:
        task_id = self.scene.add_node_from_type("passive.planning.task_card", 40.0, 60.0)
        logger_id = self.scene.add_node_from_type("core.logger", 340.0, 80.0)
        shell_id = self.scene.add_node_from_type("core.subnode", 640.0, 100.0)

        self.assertFalse(self.scene.set_node_properties(shell_id, {"title": "   "}))
        self.assertTrue(
            self.scene.set_node_properties(
                task_id,
                {
                    "title": "Ship parser",
                    "owner": "Platform",
                },
            )
        )
        self.assertTrue(
            self.scene.set_node_properties(
                logger_id,
                {
                    "title": "Primary Logger",
                    "message": "Updated from batch",
                },
            )
        )
        self.assertTrue(self.scene.set_node_properties(shell_id, {"title": "Nested Workflow"}))

        workspace = self.model.project.workspaces[self.workspace_id]
        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}

        task_node = workspace.nodes[task_id]
        logger_node = workspace.nodes[logger_id]
        shell_node = workspace.nodes[shell_id]

        self.assertEqual(task_node.title, "Ship parser")
        self.assertEqual(task_node.properties["title"], "Ship parser")
        self.assertEqual(task_node.properties["owner"], "Platform")
        self.assertEqual(logger_node.title, "Primary Logger")
        self.assertEqual(logger_node.properties["message"], "Updated from batch")
        self.assertNotIn("title", logger_node.properties)
        self.assertEqual(shell_node.title, "Nested Workflow")
        self.assertNotIn("title", shell_node.properties)

        self.assertEqual(node_payload[task_id]["title"], "Ship parser")
        self.assertEqual(node_payload[task_id]["properties"]["title"], "Ship parser")
        self.assertEqual(node_payload[logger_id]["title"], "Primary Logger")
        self.assertNotIn("title", node_payload[logger_id]["properties"])
        self.assertEqual(node_payload[shell_id]["title"], "Nested Workflow")
        self.assertNotIn("title", node_payload[shell_id]["properties"])

    def test_title_property_mutations_use_rename_history_for_single_title_and_property_history_for_batches(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        node_id = self.scene.add_node_from_type("core.logger", 40.0, 60.0)
        history.clear_workspace(self.workspace_id)

        self.scene.set_node_property(node_id, "title", "Logger Alpha")

        self.assertEqual(history.undo_depth(self.workspace_id), 1)
        self.assertEqual(history._undo_stacks[self.workspace_id][-1].action_type, ACTION_RENAME_NODE)
        history.clear_workspace(self.workspace_id)

        self.assertTrue(self.scene.set_node_properties(node_id, {"title": "Logger Beta"}))

        self.assertEqual(history.undo_depth(self.workspace_id), 1)
        self.assertEqual(history._undo_stacks[self.workspace_id][-1].action_type, ACTION_RENAME_NODE)
        history.clear_workspace(self.workspace_id)

        self.assertTrue(
            self.scene.set_node_properties(
                node_id,
                {
                    "title": "Logger Gamma",
                    "message": "Updated from batch",
                },
            )
        )

        self.assertEqual(history.undo_depth(self.workspace_id), 1)
        self.assertEqual(history._undo_stacks[self.workspace_id][-1].action_type, ACTION_EDIT_PROPERTY)

    def test_hiding_connected_port_removes_edges_immediately(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.python_script", 320.0, 30.0)
        edge_id = self.scene.add_edge(source_id, "trigger", target_id, "payload")

        self.scene.set_exposed_port(source_id, "trigger", False)

        workspace = self.model.project.workspaces[self.workspace_id]
        self.assertNotIn(edge_id, workspace.edges)
        self.assertIsNone(self.scene.edge_item(edge_id))

    def test_graph_theme_bridge_rebuilds_scene_payload_semantics(self) -> None:
        graph_theme_bridge = GraphThemeBridge(theme_id="graph_stitch_dark")
        self.scene.bind_graph_theme_bridge(graph_theme_bridge)
        nodes_changed: list[str] = []
        edges_changed: list[str] = []
        self.scene.nodes_changed.connect(lambda: nodes_changed.append("nodes"))
        self.scene.edges_changed.connect(lambda: edges_changed.append("edges"))

        start_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        constant_id = self.scene.add_node_from_type("core.constant", 220.0, 0.0)
        branch_id = self.scene.add_node_from_type("core.branch", 480.0, 0.0)
        edge_id = self.scene.add_edge(constant_id, "as_text", branch_id, "condition")

        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}
        self.assertEqual(node_payload[start_id]["accent"], GRAPH_CATEGORY_ACCENT_TOKENS_V1.core)
        self.assertTrue(edge_payload[edge_id]["data_type_warning"])
        self.assertEqual(edge_payload[edge_id]["color"], GRAPH_STITCH_DARK_EDGE_TOKENS_V1.warning_stroke)

        nodes_count_before = len(nodes_changed)
        edges_count_before = len(edges_changed)
        graph_theme_bridge.apply_theme("graph_stitch_light")

        self.assertGreater(len(nodes_changed), nodes_count_before)
        self.assertGreater(len(edges_changed), edges_count_before)
        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}
        self.assertEqual(edge_payload[edge_id]["color"], GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1.warning_stroke)

    def test_graph_theme_bridge_accepts_custom_theme_payloads_and_rebuilds_scene(self) -> None:
        custom_theme = copy.deepcopy(resolve_graph_theme("graph_stitch_dark").as_dict())
        custom_theme["theme_id"] = "custom_graph_theme_deadbeef"
        custom_theme["label"] = "Ocean Wire"
        custom_theme["category_accent_tokens"]["core"] = "#44AAFF"
        custom_theme["edge_tokens"]["warning_stroke"] = "#11AA66"

        graph_theme_bridge = GraphThemeBridge(theme_id=custom_theme)
        self.scene.bind_graph_theme_bridge(graph_theme_bridge)
        nodes_changed: list[str] = []
        edges_changed: list[str] = []
        self.scene.nodes_changed.connect(lambda: nodes_changed.append("nodes"))
        self.scene.edges_changed.connect(lambda: edges_changed.append("edges"))

        start_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        constant_id = self.scene.add_node_from_type("core.constant", 220.0, 0.0)
        branch_id = self.scene.add_node_from_type("core.branch", 480.0, 0.0)
        edge_id = self.scene.add_edge(constant_id, "as_text", branch_id, "condition")

        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}
        self.assertEqual(node_payload[start_id]["accent"], "#44AAFF")
        self.assertEqual(edge_payload[edge_id]["color"], "#11AA66")

        custom_theme["category_accent_tokens"]["core"] = "#C955CC"
        custom_theme["edge_tokens"]["warning_stroke"] = "#1188CC"
        nodes_count_before = len(nodes_changed)
        edges_count_before = len(edges_changed)
        graph_theme_bridge.apply_theme(custom_theme)

        self.assertGreater(len(nodes_changed), nodes_count_before)
        self.assertGreater(len(edges_changed), edges_count_before)
        node_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}
        self.assertEqual(node_payload[start_id]["accent"], "#C955CC")
        self.assertEqual(edge_payload[edge_id]["color"], "#1188CC")

    def test_connect_nodes_uses_only_currently_exposed_ports(self) -> None:
        source_id = self.scene.add_node_from_type("core.constant", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.logger", 320.0, 30.0)
        self.scene.set_exposed_port(source_id, "value", False)
        self.scene.set_exposed_port(source_id, "as_text", False)

        with self.assertRaises(ValueError):
            self.scene.connect_nodes(source_id, target_id)

    def test_add_edge_rejects_exec_to_data_kind_mismatch(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.logger", 320.0, 30.0)

        with self.assertRaises(ValueError):
            self.scene.add_edge(source_id, "exec_out", target_id, "message")

    def test_add_edge_rejects_second_incoming_connection_for_single_input_port(self) -> None:
        first_source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        second_source_id = self.scene.add_node_from_type("core.start", 0.0, 120.0)
        target_id = self.scene.add_node_from_type("core.end", 320.0, 30.0)

        self.scene.add_edge(first_source_id, "exec_out", target_id, "exec_in")

        with self.assertRaises(ValueError):
            self.scene.add_edge(second_source_id, "exec_out", target_id, "exec_in")

    def test_pin_kind_change_prunes_invalid_shell_edge_immediately(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        shell_id = self.scene.add_node_from_type("core.subnode", 240.0, 30.0)
        pin_in = self.scene.add_subnode_shell_pin(shell_id, "core.subnode_input")

        self.scene.set_node_property(pin_in, "kind", "exec")
        edge_id = self.scene.add_edge(source_id, "exec_out", shell_id, pin_in)

        workspace = self.model.project.workspaces[self.workspace_id]
        self.assertIn(edge_id, workspace.edges)

        self.scene.set_node_property(pin_in, "kind", "data")

        self.assertNotIn(edge_id, workspace.edges)
        self.assertEqual(self.scene.edges_model, [])

    def test_subnode_shell_ports_follow_direct_pin_sort_and_pin_properties(self) -> None:
        shell_id = self.scene.add_node_from_type("core.subnode", 200.0, 120.0)
        pin_in_exec = self.scene.add_node_from_type("core.subnode_input", 30.0, 10.0)
        pin_in_data = self.scene.add_node_from_type("core.subnode_input", 30.0, 10.0)
        pin_out_data = self.scene.add_node_from_type("core.subnode_output", 90.0, 10.0)
        pin_out_failed = self.scene.add_node_from_type("core.subnode_output", 20.0, 50.0)
        non_pin_child = self.scene.add_node_from_type("core.logger", 60.0, 15.0)
        nested_pin = self.scene.add_node_from_type("core.subnode_input", 15.0, 5.0)

        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[pin_in_exec].parent_node_id = shell_id
        workspace.nodes[pin_in_data].parent_node_id = shell_id
        workspace.nodes[pin_out_data].parent_node_id = shell_id
        workspace.nodes[pin_out_failed].parent_node_id = shell_id
        workspace.nodes[non_pin_child].parent_node_id = shell_id
        workspace.nodes[nested_pin].parent_node_id = non_pin_child

        self.scene.set_node_property(pin_in_exec, "label", "Exec In")
        self.scene.set_node_property(pin_in_exec, "kind", "exec")
        self.scene.set_node_property(pin_in_exec, "data_type", "str")
        self.scene.set_node_property(pin_in_data, "label", "Flag In")
        self.scene.set_node_property(pin_in_data, "kind", "data")
        self.scene.set_node_property(pin_in_data, "data_type", "bool")
        self.scene.set_node_property(pin_out_data, "label", "Result Out")
        self.scene.set_node_property(pin_out_data, "kind", "data")
        self.scene.set_node_property(pin_out_data, "data_type", "float")
        self.scene.set_node_property(pin_out_failed, "label", "Failure Out")
        self.scene.set_node_property(pin_out_failed, "kind", "failed")
        self.scene.set_node_property(pin_out_failed, "data_type", "str")
        self.scene.refresh_workspace_from_model(self.workspace_id)

        root_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        shell_ports = root_payload[shell_id]["ports"]
        direct_pins = [pin_in_exec, pin_in_data, pin_out_data, pin_out_failed]
        expected_order = sorted(
            direct_pins,
            key=lambda node_id: (
                float(workspace.nodes[node_id].y),
                float(workspace.nodes[node_id].x),
                node_id,
            ),
        )
        self.assertEqual([port["key"] for port in shell_ports], expected_order)
        self.assertEqual(len(shell_ports), 4)

        shell_port_by_key = {port["key"]: port for port in shell_ports}
        self.assertEqual(shell_port_by_key[pin_in_exec]["label"], "Exec In")
        self.assertEqual(shell_port_by_key[pin_in_exec]["direction"], "in")
        self.assertEqual(shell_port_by_key[pin_in_exec]["kind"], "exec")
        self.assertEqual(shell_port_by_key[pin_in_exec]["data_type"], "any")
        self.assertEqual(shell_port_by_key[pin_in_data]["label"], "Flag In")
        self.assertEqual(shell_port_by_key[pin_in_data]["direction"], "in")
        self.assertEqual(shell_port_by_key[pin_in_data]["data_type"], "bool")
        self.assertEqual(shell_port_by_key[pin_out_data]["label"], "Result Out")
        self.assertEqual(shell_port_by_key[pin_out_data]["direction"], "out")
        self.assertEqual(shell_port_by_key[pin_out_data]["data_type"], "float")
        self.assertEqual(shell_port_by_key[pin_out_failed]["label"], "Failure Out")
        self.assertEqual(shell_port_by_key[pin_out_failed]["direction"], "out")
        self.assertEqual(shell_port_by_key[pin_out_failed]["kind"], "failed")
        self.assertEqual(shell_port_by_key[pin_out_failed]["data_type"], "any")

        self.assertNotIn(pin_in_exec, root_payload)
        self.assertTrue(self.scene.open_subnode_scope(shell_id))

        nested_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        self.assertIn(pin_in_exec, nested_payload)
        pin_payload = nested_payload[pin_in_exec]["ports"]
        self.assertEqual(len(pin_payload), 1)
        self.assertEqual(pin_payload[0]["key"], "pin")
        self.assertEqual(pin_payload[0]["label"], "Exec In")
        self.assertEqual(pin_payload[0]["kind"], "exec")
        self.assertEqual(pin_payload[0]["data_type"], "any")

    def test_add_subnode_shell_pin_uses_unique_labels_and_exposes_shell_ports(self) -> None:
        shell_id = self.scene.add_node_from_type("core.subnode", 200.0, 120.0)
        first_input_id = self.scene.add_subnode_shell_pin(shell_id, "core.subnode_input")
        second_input_id = self.scene.add_subnode_shell_pin(shell_id, "core.subnode_input")
        output_id = self.scene.add_subnode_shell_pin(shell_id, "core.subnode_output")

        workspace = self.model.project.workspaces[self.workspace_id]
        shell_node = workspace.nodes[shell_id]
        self.assertTrue(first_input_id)
        self.assertTrue(second_input_id)
        self.assertTrue(output_id)
        self.assertEqual(workspace.nodes[first_input_id].parent_node_id, shell_id)
        self.assertEqual(workspace.nodes[second_input_id].parent_node_id, shell_id)
        self.assertEqual(workspace.nodes[output_id].parent_node_id, shell_id)
        self.assertEqual(workspace.nodes[first_input_id].properties["label"], "Input")
        self.assertEqual(workspace.nodes[second_input_id].properties["label"], "Input 2")
        self.assertEqual(workspace.nodes[output_id].properties["label"], "Output")
        self.assertTrue(bool(shell_node.exposed_ports[first_input_id]))
        self.assertTrue(bool(shell_node.exposed_ports[second_input_id]))
        self.assertTrue(bool(shell_node.exposed_ports[output_id]))
        self.assertLess(float(workspace.nodes[first_input_id].x), float(workspace.nodes[output_id].x))
        self.assertLess(float(workspace.nodes[first_input_id].y), float(workspace.nodes[second_input_id].y))

        shell_payload = next(item for item in self.scene.nodes_model if item["node_id"] == shell_id)
        shell_ports = {port["key"]: port for port in shell_payload["ports"]}
        self.assertEqual(shell_ports[first_input_id]["label"], "Input")
        self.assertEqual(shell_ports[second_input_id]["label"], "Input 2")
        self.assertEqual(shell_ports[output_id]["label"], "Output")

    def test_scope_navigation_filters_nodes_edges_and_assigns_new_nodes_to_active_scope(self) -> None:
        shell_id = self.scene.add_node_from_type("core.subnode", 200.0, 120.0)
        root_source_id = self.scene.add_node_from_type("core.start", 20.0, 30.0)
        root_target_id = self.scene.add_node_from_type("core.end", 520.0, 30.0)
        pin_in = self.scene.add_node_from_type("core.subnode_input", 30.0, 30.0)
        pin_out = self.scene.add_node_from_type("core.subnode_output", 90.0, 30.0)
        nested_logger = self.scene.add_node_from_type("core.logger", 160.0, 120.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[pin_in].parent_node_id = shell_id
        workspace.nodes[pin_out].parent_node_id = shell_id
        workspace.nodes[nested_logger].parent_node_id = shell_id
        self.scene.set_node_property(pin_in, "kind", "exec")
        self.scene.set_node_property(pin_out, "kind", "exec")
        self.scene.refresh_workspace_from_model(self.workspace_id)

        # Root scope only shows direct workspace children.
        root_node_ids = {item["node_id"] for item in self.scene.nodes_model}
        self.assertEqual(root_node_ids, {shell_id, root_source_id, root_target_id})
        self.assertEqual(self.scene.active_scope_path, [])
        self.assertEqual([item["node_id"] for item in self.scene.scope_breadcrumb_model], [""])

        self.scene.add_edge(root_source_id, "exec_out", root_target_id, "exec_in")
        self.scene.add_edge(root_source_id, "exec_out", shell_id, pin_in)
        self.assertEqual({item["edge_id"] for item in self.scene.edges_model}, set(workspace.edges))

        self.assertTrue(self.scene.open_subnode_scope(shell_id))
        self.assertEqual(self.scene.active_scope_path, [shell_id])
        breadcrumb_ids = [item["node_id"] for item in self.scene.scope_breadcrumb_model]
        self.assertEqual(breadcrumb_ids, ["", shell_id])

        nested_node_ids = {item["node_id"] for item in self.scene.nodes_model}
        self.assertEqual(nested_node_ids, {pin_in, pin_out, nested_logger})
        self.assertEqual(self.scene.edges_model, [])

        created_inside_scope = self.scene.add_node_from_type("core.constant", 300.0, 150.0)
        self.assertEqual(workspace.nodes[created_inside_scope].parent_node_id, shell_id)

        self.assertTrue(self.scene.navigate_scope_parent())
        self.assertEqual(self.scene.active_scope_path, [])
        self.assertFalse(self.scene.navigate_scope_parent())
        self.assertFalse(self.scene.navigate_scope_root())

    def test_connect_nodes_uses_dynamic_subnode_default_ports(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 20.0, 30.0)
        shell_id = self.scene.add_node_from_type("core.subnode", 260.0, 30.0)
        target_id = self.scene.add_node_from_type("core.end", 520.0, 30.0)
        pin_in = self.scene.add_node_from_type("core.subnode_input", 40.0, 40.0)
        pin_out = self.scene.add_node_from_type("core.subnode_output", 80.0, 40.0)

        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[pin_in].parent_node_id = shell_id
        workspace.nodes[pin_out].parent_node_id = shell_id
        self.scene.set_node_property(pin_in, "kind", "exec")
        self.scene.set_node_property(pin_out, "kind", "exec")
        self.scene.refresh_workspace_from_model(self.workspace_id)

        edge_into_shell_id = self.scene.connect_nodes(source_id, shell_id)
        edge_out_of_shell_id = self.scene.connect_nodes(shell_id, target_id)

        edge_into_shell = workspace.edges[edge_into_shell_id]
        edge_out_of_shell = workspace.edges[edge_out_of_shell_id]
        self.assertEqual(edge_into_shell.source_node_id, source_id)
        self.assertEqual(edge_into_shell.source_port_key, "exec_out")
        self.assertEqual(edge_into_shell.target_node_id, shell_id)
        self.assertEqual(edge_into_shell.target_port_key, pin_in)
        self.assertEqual(edge_out_of_shell.source_node_id, shell_id)
        self.assertEqual(edge_out_of_shell.source_port_key, pin_out)
        self.assertEqual(edge_out_of_shell.target_node_id, target_id)
        self.assertEqual(edge_out_of_shell.target_port_key, "exec_in")

    def test_workspace_and_selection_bounds_helpers(self) -> None:
        node_a = self.scene.add_node_from_type("core.start", 10.0, 20.0)
        node_b = self.scene.add_node_from_type("core.end", 340.0, 160.0)

        workspace_bounds = self.scene.workspace_scene_bounds()
        self.assertIsNotNone(workspace_bounds)
        node_a_bounds = self.scene.node_bounds(node_a)
        node_b_bounds = self.scene.node_bounds(node_b)
        self.assertIsNotNone(node_a_bounds)
        self.assertIsNotNone(node_b_bounds)
        expected_workspace_bounds = node_a_bounds.united(node_b_bounds)
        self.assertAlmostEqual(workspace_bounds.x(), expected_workspace_bounds.x(), places=6)
        self.assertAlmostEqual(workspace_bounds.y(), expected_workspace_bounds.y(), places=6)
        self.assertAlmostEqual(workspace_bounds.width(), expected_workspace_bounds.width(), places=6)
        self.assertAlmostEqual(workspace_bounds.height(), expected_workspace_bounds.height(), places=6)

        self.scene.select_node(node_b)
        selection_bounds = self.scene.selection_bounds()
        self.assertIsNotNone(selection_bounds)
        self.assertAlmostEqual(selection_bounds.x(), node_b_bounds.x(), places=6)
        self.assertAlmostEqual(selection_bounds.y(), node_b_bounds.y(), places=6)
        self.assertAlmostEqual(selection_bounds.width(), node_b_bounds.width(), places=6)
        self.assertAlmostEqual(selection_bounds.height(), node_b_bounds.height(), places=6)

        self.scene.clear_selection()
        self.assertIsNone(self.scene.selection_bounds())

    def test_minimap_payload_tracks_selection_and_fallback_bounds(self) -> None:
        empty_bounds = self.scene.workspace_scene_bounds_payload
        self.assertAlmostEqual(empty_bounds["x"], -1600.0, places=6)
        self.assertAlmostEqual(empty_bounds["y"], -900.0, places=6)
        self.assertAlmostEqual(empty_bounds["width"], 3200.0, places=6)
        self.assertAlmostEqual(empty_bounds["height"], 1800.0, places=6)
        self.assertEqual(self.scene.minimap_nodes_model, [])

        node_a = self.scene.add_node_from_type("core.start", 30.0, 40.0)
        node_b = self.scene.add_node_from_type("core.end", 390.0, 200.0)
        self.scene.select_node(node_b)

        minimap_payload = {item["node_id"]: item for item in self.scene.minimap_nodes_model}
        self.assertIn(node_a, minimap_payload)
        self.assertIn(node_b, minimap_payload)
        self.assertNotIn("selected", minimap_payload[node_a])
        self.assertNotIn("selected", minimap_payload[node_b])
        self.assertEqual(self.scene.selected_node_lookup, {node_b: True})

        workspace_bounds = self.scene.workspace_scene_bounds_payload
        node_a_bounds = self.scene.node_bounds(node_a)
        node_b_bounds = self.scene.node_bounds(node_b)
        self.assertIsNotNone(node_a_bounds)
        self.assertIsNotNone(node_b_bounds)
        expected_workspace_bounds = node_a_bounds.united(node_b_bounds)
        self.assertLessEqual(workspace_bounds["x"], expected_workspace_bounds.x())
        self.assertLessEqual(workspace_bounds["y"], expected_workspace_bounds.y())
        self.assertGreaterEqual(workspace_bounds["x"] + workspace_bounds["width"], expected_workspace_bounds.x() + expected_workspace_bounds.width())
        self.assertGreaterEqual(
            workspace_bounds["y"] + workspace_bounds["height"],
            expected_workspace_bounds.y() + expected_workspace_bounds.height(),
        )
        self.assertGreaterEqual(workspace_bounds["width"], 3200.0)
        self.assertGreaterEqual(workspace_bounds["height"], 1800.0)

    def test_move_nodes_by_delta_moves_group_with_single_history_entry(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        node_a = self.scene.add_node_from_type("core.start", 20.0, 30.0)
        node_b = self.scene.add_node_from_type("core.end", 360.0, 170.0)
        history.clear_workspace(self.workspace_id)
        workspace = self.model.project.workspaces[self.workspace_id]

        before_dx = workspace.nodes[node_b].x - workspace.nodes[node_a].x
        before_dy = workspace.nodes[node_b].y - workspace.nodes[node_a].y

        moved = self.scene.move_nodes_by_delta([node_a, node_b], 55.0, -25.0)
        self.assertTrue(moved)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 75.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_a].y, 5.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 415.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].y, 145.0, places=6)

        after_dx = workspace.nodes[node_b].x - workspace.nodes[node_a].x
        after_dy = workspace.nodes[node_b].y - workspace.nodes[node_a].y
        self.assertAlmostEqual(before_dx, after_dx, places=6)
        self.assertAlmostEqual(before_dy, after_dy, places=6)

        self.assertIsNotNone(history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 20.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_a].y, 30.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 360.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].y, 170.0, places=6)

        self.assertIsNotNone(history.redo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 75.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_a].y, 5.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 415.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].y, 145.0, places=6)

    def test_layout_actions_align_and_distribute_selected_nodes_with_grouped_history(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        node_a = self.scene.add_node_from_type("core.start", 40.0, 20.0)
        node_b = self.scene.add_node_from_type("core.end", 320.0, 210.0)
        node_c = self.scene.add_node_from_type("core.logger", 640.0, 80.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        self.scene.select_node(node_a, False)
        self.scene.select_node(node_b, True)
        self.scene.select_node(node_c, True)
        history.clear_workspace(self.workspace_id)

        moved = self.scene.align_selected_nodes("left")
        self.assertTrue(moved)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        left_edges = []
        for node_id in (node_a, node_b, node_c):
            bounds = self.scene.node_bounds(node_id)
            self.assertIsNotNone(bounds)
            left_edges.append(bounds.x())
        for left in left_edges[1:]:
            self.assertAlmostEqual(left, left_edges[0], places=6)

        self.assertIsNotNone(history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 320.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_c].x, 640.0, places=6)

        self.assertIsNotNone(history.redo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_c].x, 40.0, places=6)

        self.model.set_node_position(self.workspace_id, node_a, 10.0, 30.0)
        self.model.set_node_position(self.workspace_id, node_b, 290.0, 120.0)
        self.model.set_node_position(self.workspace_id, node_c, 700.0, 260.0)
        self.scene.refresh_workspace_from_model(self.workspace_id)
        history.clear_workspace(self.workspace_id)

        before_sorted = sorted(
            (self.scene.node_bounds(node_id) for node_id in (node_a, node_b, node_c)),
            key=lambda bounds: float(bounds.x()) if bounds is not None else 0.0,
        )
        self.assertTrue(all(bounds is not None for bounds in before_sorted))
        moved = self.scene.distribute_selected_nodes("horizontal")
        self.assertTrue(moved)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        after_sorted = sorted(
            (self.scene.node_bounds(node_id) for node_id in (node_a, node_b, node_c)),
            key=lambda bounds: float(bounds.x()) if bounds is not None else 0.0,
        )
        self.assertTrue(all(bounds is not None for bounds in after_sorted))
        first_before = before_sorted[0]
        last_before = before_sorted[-1]
        first_after = after_sorted[0]
        last_after = after_sorted[-1]
        self.assertIsNotNone(first_before)
        self.assertIsNotNone(last_before)
        self.assertIsNotNone(first_after)
        self.assertIsNotNone(last_after)
        self.assertAlmostEqual(first_after.x(), first_before.x(), places=6)
        self.assertAlmostEqual(last_after.x(), last_before.x(), places=6)

        gap_01 = after_sorted[1].x() - (after_sorted[0].x() + after_sorted[0].width())
        gap_12 = after_sorted[2].x() - (after_sorted[1].x() + after_sorted[1].width())
        self.assertAlmostEqual(gap_01, gap_12, places=6)

    def test_layout_actions_snap_to_grid_and_small_selections_are_safe_noops(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        node_a = self.scene.add_node_from_type("core.start", 13.0, 17.0)
        node_b = self.scene.add_node_from_type("core.end", 171.0, 83.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        history.clear_workspace(self.workspace_id)

        self.scene.select_node(node_a, False)
        self.assertFalse(self.scene.align_selected_nodes("left"))
        self.assertFalse(self.scene.distribute_selected_nodes("horizontal"))
        self.assertEqual(history.undo_depth(self.workspace_id), 0)

        self.scene.select_node(node_b, True)
        moved = self.scene.align_selected_nodes("top", snap_to_grid=True)
        self.assertTrue(moved)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        for node_id in (node_a, node_b):
            node = workspace.nodes[node_id]
            self.assertAlmostEqual(float(node.x) / 20.0, round(float(node.x) / 20.0), places=6)
            self.assertAlmostEqual(float(node.y) / 20.0, round(float(node.y) / 20.0), places=6)

        self.assertIsNotNone(history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 13.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_a].y, 17.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 171.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].y, 83.0, places=6)

    def test_duplicate_selected_subgraph_offsets_nodes_and_internal_edges_only(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        source_id = self.scene.add_node_from_type("core.start", 10.0, 20.0)
        target_id = self.scene.add_node_from_type("core.end", 280.0, 40.0)
        external_id = self.scene.add_node_from_type("core.python_script", 520.0, 80.0)
        self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.scene.add_edge(source_id, "trigger", external_id, "payload")
        self.scene.select_node(source_id, False)
        self.scene.select_node(target_id, True)
        history.clear_workspace(self.workspace_id)

        duplicated = self.scene.duplicate_selected_subgraph()
        self.assertTrue(duplicated)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        workspace = self.model.project.workspaces[self.workspace_id]
        self.assertEqual(len(workspace.nodes), 5)
        self.assertEqual(len(workspace.edges), 3)

        duplicated_ids = [item.node.node_id for item in self.scene.selectedItems()]
        self.assertEqual(len(duplicated_ids), 2)
        self.assertNotIn(source_id, duplicated_ids)
        self.assertNotIn(target_id, duplicated_ids)

        source_node = workspace.nodes[source_id]
        target_node = workspace.nodes[target_id]
        duplicated_source_id = ""
        duplicated_target_id = ""
        for node_id in duplicated_ids:
            node = workspace.nodes[node_id]
            if (
                node.type_id == source_node.type_id
                and node.title == source_node.title
                and abs(node.x - (source_node.x + 40.0)) < 1e-6
                and abs(node.y - (source_node.y + 40.0)) < 1e-6
            ):
                duplicated_source_id = node_id
            if (
                node.type_id == target_node.type_id
                and node.title == target_node.title
                and abs(node.x - (target_node.x + 40.0)) < 1e-6
                and abs(node.y - (target_node.y + 40.0)) < 1e-6
            ):
                duplicated_target_id = node_id
        self.assertTrue(duplicated_source_id)
        self.assertTrue(duplicated_target_id)

        duplicated_internal_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == duplicated_source_id
            and edge.target_node_id == duplicated_target_id
            and edge.source_port_key == "exec_out"
            and edge.target_port_key == "exec_in"
        ]
        self.assertEqual(len(duplicated_internal_edges), 1)
        duplicated_external_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == duplicated_source_id and edge.source_port_key == "trigger"
        ]
        self.assertEqual(duplicated_external_edges, [])

    def test_paste_subgraph_fragment_centers_selection_and_records_single_history_entry(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        source_id = self.scene.add_node_from_type("core.start", 10.0, 20.0)
        target_id = self.scene.add_node_from_type("core.end", 280.0, 40.0)
        self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        workspace = self.model.project.workspaces[self.workspace_id]
        self.scene.select_node(source_id, False)
        self.scene.select_node(target_id, True)
        fragment = self.scene.serialize_selected_subgraph_fragment()
        self.assertIsNotNone(fragment)
        history.clear_workspace(self.workspace_id)

        pasted = self.scene.paste_subgraph_fragment(fragment, 620.0, 240.0)
        self.assertTrue(pasted)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        pasted_ids = [item.node.node_id for item in self.scene.selectedItems()]
        self.assertEqual(len(pasted_ids), 2)
        self.assertEqual({source_id, target_id} & set(pasted_ids), set())
        self.assertEqual(len(workspace.nodes), 4)
        self.assertEqual(len(workspace.edges), 2)

        selection_bounds = self.scene.selection_bounds()
        self.assertIsNotNone(selection_bounds)
        assert selection_bounds is not None
        self.assertAlmostEqual(selection_bounds.center().x(), 620.0, places=6)
        self.assertAlmostEqual(selection_bounds.center().y(), 240.0, places=6)

        pasted_edge_count = len(
            [
                edge
                for edge in workspace.edges.values()
                if edge.source_node_id in pasted_ids and edge.target_node_id in pasted_ids
            ]
        )
        self.assertEqual(pasted_edge_count, 1)

        self.assertIsNotNone(history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertEqual(len(workspace.nodes), 2)
        self.assertEqual(len(workspace.edges), 1)

    def test_duplicate_selected_subgraph_treats_selected_subnode_shell_as_subtree_root(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        shell_id = self.scene.add_node_from_type("core.subnode", 120.0, 80.0)
        nested_logger_id = self.scene.add_node_from_type("core.logger", 320.0, 120.0)
        nested_constant_id = self.scene.add_node_from_type("core.constant", 80.0, 220.0)
        deep_script_id = self.scene.add_node_from_type("core.python_script", 520.0, 260.0)
        external_logger_id = self.scene.add_node_from_type("core.logger", 780.0, 140.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[nested_logger_id].parent_node_id = shell_id
        workspace.nodes[nested_constant_id].parent_node_id = shell_id
        workspace.nodes[deep_script_id].parent_node_id = nested_logger_id
        self.scene.refresh_workspace_from_model(self.workspace_id)

        self.model.add_edge(self.workspace_id, nested_constant_id, "as_text", nested_logger_id, "message")
        self.model.add_edge(self.workspace_id, nested_logger_id, "exec_out", deep_script_id, "exec_in")
        self.model.add_edge(self.workspace_id, nested_constant_id, "value", external_logger_id, "message")
        self.scene.refresh_workspace_from_model(self.workspace_id)

        original_subtree = subtree_node_ids(workspace, [shell_id])
        original_subtree_set = set(original_subtree)
        original_internal_edge_count = len(
            [
                edge
                for edge in workspace.edges.values()
                if edge.source_node_id in original_subtree_set and edge.target_node_id in original_subtree_set
            ]
        )

        self.scene.select_node(shell_id, False)
        history.clear_workspace(self.workspace_id)
        duplicated = self.scene.duplicate_selected_subgraph()
        self.assertTrue(duplicated)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        duplicated_shell_ids = [
            node_id
            for node_id, node in workspace.nodes.items()
            if node.type_id == "core.subnode"
            and node.parent_node_id is None
            and node_id != shell_id
            and abs(float(node.x) - (float(workspace.nodes[shell_id].x) + 40.0)) < 1e-6
            and abs(float(node.y) - (float(workspace.nodes[shell_id].y) + 40.0)) < 1e-6
        ]
        self.assertEqual(len(duplicated_shell_ids), 1)
        duplicated_shell_id = duplicated_shell_ids[0]

        duplicated_subtree = subtree_node_ids(workspace, [duplicated_shell_id])
        duplicated_subtree_set = set(duplicated_subtree)
        self.assertEqual(len(duplicated_subtree), len(original_subtree))
        self.assertEqual(original_subtree_set & duplicated_subtree_set, set())

        duplicated_internal_edge_count = len(
            [
                edge
                for edge in workspace.edges.values()
                if edge.source_node_id in duplicated_subtree_set and edge.target_node_id in duplicated_subtree_set
            ]
        )
        self.assertEqual(duplicated_internal_edge_count, original_internal_edge_count)

        duplicated_external_edges = [
            edge
            for edge in workspace.edges.values()
            if (
                edge.source_node_id in duplicated_subtree_set and edge.target_node_id not in duplicated_subtree_set
            )
            or (
                edge.target_node_id in duplicated_subtree_set and edge.source_node_id not in duplicated_subtree_set
            )
        ]
        self.assertEqual(duplicated_external_edges, [])

    def test_focus_move_and_connect_are_restricted_to_active_scope(self) -> None:
        shell_id = self.scene.add_node_from_type("core.subnode", 180.0, 120.0)
        root_source_id = self.scene.add_node_from_type("core.start", 40.0, 40.0)
        nested_logger_id = self.scene.add_node_from_type("core.logger", 120.0, 80.0)
        nested_target_id = self.scene.add_node_from_type("core.python_script", 340.0, 100.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[nested_logger_id].parent_node_id = shell_id
        workspace.nodes[nested_target_id].parent_node_id = shell_id
        self.scene.refresh_workspace_from_model(self.workspace_id)

        self.assertIsNone(self.scene.focus_node(nested_logger_id))
        self.assertFalse(self.scene.move_nodes_by_delta([nested_logger_id], 40.0, 25.0))
        self.assertAlmostEqual(workspace.nodes[nested_logger_id].x, 120.0, places=6)
        self.assertAlmostEqual(workspace.nodes[nested_logger_id].y, 80.0, places=6)

        with self.assertRaises(ValueError):
            self.scene.add_edge(root_source_id, "trigger", nested_logger_id, "message")

        self.assertTrue(self.scene.open_scope_for_node(nested_logger_id))
        focused_center = self.scene.focus_node(nested_logger_id)
        self.assertIsNotNone(focused_center)
        self.assertEqual(self.scene.active_scope_path, [shell_id])
        self.assertTrue(self.scene.move_nodes_by_delta([nested_logger_id, nested_target_id], 15.0, -10.0))

    def test_group_selected_nodes_creates_subnode_pins_and_single_history_entry(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        source_id = self.scene.add_node_from_type("core.start", 20.0, 40.0)
        grouped_logger_id = self.scene.add_node_from_type("core.logger", 320.0, 60.0)
        grouped_constant_id = self.scene.add_node_from_type("core.constant", 220.0, 190.0)
        target_id = self.scene.add_node_from_type("core.end", 640.0, 90.0)
        external_script_id = self.scene.add_node_from_type("core.python_script", 700.0, 230.0)

        self.scene.add_edge(source_id, "exec_out", grouped_logger_id, "exec_in")
        self.scene.add_edge(grouped_constant_id, "as_text", grouped_logger_id, "message")
        self.scene.add_edge(grouped_logger_id, "exec_out", target_id, "exec_in")
        self.scene.add_edge(grouped_constant_id, "value", external_script_id, "payload")
        workspace = self.model.project.workspaces[self.workspace_id]

        self.scene.select_node(grouped_logger_id, False)
        self.scene.select_node(grouped_constant_id, True)
        history.clear_workspace(self.workspace_id)

        grouped = self.scene.group_selected_nodes()
        self.assertTrue(grouped)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        shell_id = self.scene.selected_node_id()
        self.assertIsNotNone(shell_id)
        assert shell_id is not None
        shell_node = workspace.nodes[shell_id]
        self.assertEqual(shell_node.type_id, "core.subnode")
        self.assertIsNone(shell_node.parent_node_id)
        self.assertEqual(workspace.nodes[grouped_logger_id].parent_node_id, shell_id)
        self.assertEqual(workspace.nodes[grouped_constant_id].parent_node_id, shell_id)

        pin_ids = [
            node_id
            for node_id, node in workspace.nodes.items()
            if node.parent_node_id == shell_id and node.type_id in {"core.subnode_input", "core.subnode_output"}
        ]
        self.assertEqual(len(pin_ids), 3)
        shell_payload = next(item for item in self.scene.nodes_model if item["node_id"] == shell_id)
        shell_port_labels = {str(port.get("label", "")) for port in shell_payload["ports"]}
        self.assertEqual(shell_port_labels, {"exec_in", "exec_out", "value"})

        grouped_ids = {grouped_logger_id, grouped_constant_id}
        outer_ids = {source_id, target_id, external_script_id}
        for edge in workspace.edges.values():
            self.assertFalse(edge.source_node_id in outer_ids and edge.target_node_id in grouped_ids)
            self.assertFalse(edge.source_node_id in grouped_ids and edge.target_node_id in outer_ids)

        edge_tuples = {
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key)
            for edge in workspace.edges.values()
        }
        incoming_shell_edges = [edge for edge in edge_tuples if edge[0] == source_id and edge[2] == shell_id]
        self.assertEqual(len(incoming_shell_edges), 1)
        outgoing_shell_target_edges = [edge for edge in edge_tuples if edge[0] == shell_id and edge[2] == target_id]
        self.assertEqual(len(outgoing_shell_target_edges), 1)
        outgoing_shell_script_edges = [
            edge
            for edge in edge_tuples
            if edge[0] == shell_id and edge[2] == external_script_id and edge[3] == "payload"
        ]
        self.assertEqual(len(outgoing_shell_script_edges), 1)

    def test_group_selected_nodes_orders_outgoing_shell_ports_by_external_target_geometry(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        branch_id = self.scene.add_node_from_type("core.branch", 260.0, 80.0)
        constant_id = self.scene.add_node_from_type("core.constant", 120.0, 120.0)
        top_end_id = self.scene.add_node_from_type("core.end", 760.0, 20.0)
        bottom_end_id = self.scene.add_node_from_type("core.end", 760.0, 340.0)
        self.scene.add_edge(constant_id, "value", branch_id, "condition")
        self.scene.add_edge(branch_id, "true_out", top_end_id, "exec_in")
        self.scene.add_edge(branch_id, "false_out", bottom_end_id, "exec_in")
        workspace = self.model.project.workspaces[self.workspace_id]

        self.scene.select_node(branch_id, False)
        self.scene.select_node(constant_id, True)
        history.clear_workspace(self.workspace_id)
        self.assertTrue(self.scene.group_selected_nodes())
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        shell_id = self.scene.selected_node_id()
        self.assertIsNotNone(shell_id)
        assert shell_id is not None
        shell_payload = next(item for item in self.scene.nodes_model if item["node_id"] == shell_id)
        shell_port_keys = [str(port["key"]) for port in shell_payload["ports"]]

        target_y_by_port: dict[str, float] = {}
        for edge in workspace.edges.values():
            if edge.source_node_id != shell_id:
                continue
            if edge.source_port_key not in shell_port_keys:
                continue
            target_y_by_port[edge.source_port_key] = float(workspace.nodes[edge.target_node_id].y)

        ordered_target_y = [target_y_by_port[port_key] for port_key in shell_port_keys]
        self.assertEqual(ordered_target_y, sorted(ordered_target_y))

    def test_ungroup_selected_subnode_restores_wiring_and_single_history_entry(self) -> None:
        self.scene.bind_runtime_history(RuntimeGraphHistory())
        source_id = self.scene.add_node_from_type("core.start", 20.0, 40.0)
        grouped_logger_id = self.scene.add_node_from_type("core.logger", 320.0, 60.0)
        grouped_constant_id = self.scene.add_node_from_type("core.constant", 220.0, 190.0)
        target_id = self.scene.add_node_from_type("core.end", 640.0, 90.0)
        external_script_id = self.scene.add_node_from_type("core.python_script", 700.0, 230.0)

        self.scene.add_edge(source_id, "exec_out", grouped_logger_id, "exec_in")
        self.scene.add_edge(grouped_constant_id, "as_text", grouped_logger_id, "message")
        self.scene.add_edge(grouped_logger_id, "exec_out", target_id, "exec_in")
        self.scene.add_edge(grouped_constant_id, "value", external_script_id, "payload")
        workspace = self.model.project.workspaces[self.workspace_id]
        expected_edges = {
            (source_id, "exec_out", grouped_logger_id, "exec_in"),
            (grouped_constant_id, "as_text", grouped_logger_id, "message"),
            (grouped_logger_id, "exec_out", target_id, "exec_in"),
            (grouped_constant_id, "value", external_script_id, "payload"),
        }

        self.scene.select_node(grouped_logger_id, False)
        self.scene.select_node(grouped_constant_id, True)
        self.assertTrue(self.scene.group_selected_nodes())

        shell_id = self.scene.selected_node_id()
        self.assertIsNotNone(shell_id)
        assert shell_id is not None
        pin_ids_before = {
            node_id
            for node_id, node in workspace.nodes.items()
            if node.parent_node_id == shell_id and node.type_id in {"core.subnode_input", "core.subnode_output"}
        }
        self.assertTrue(pin_ids_before)

        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        history.clear_workspace(self.workspace_id)

        self.scene.select_node(shell_id, False)
        ungrouped = self.scene.ungroup_selected_subnode()
        self.assertTrue(ungrouped)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        self.assertNotIn(shell_id, workspace.nodes)
        for pin_id in pin_ids_before:
            self.assertNotIn(pin_id, workspace.nodes)
        self.assertEqual(workspace.nodes[grouped_logger_id].parent_node_id, None)
        self.assertEqual(workspace.nodes[grouped_constant_id].parent_node_id, None)

        edge_tuples = {
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key)
            for edge in workspace.edges.values()
        }
        self.assertEqual(edge_tuples, expected_edges)

    def test_group_selected_nodes_rejects_mixed_scope_selection(self) -> None:
        root_node_id = self.scene.add_node_from_type("core.start", 40.0, 40.0)
        shell_id = self.scene.add_node_from_type("core.subnode", 260.0, 120.0)
        nested_node_id = self.scene.add_node_from_type("core.logger", 280.0, 180.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[nested_node_id].parent_node_id = shell_id
        self.scene.refresh_workspace_from_model(self.workspace_id)

        self.scene._selected_node_ids = [root_node_id, nested_node_id]
        self.assertFalse(self.scene.group_selected_nodes())
        self.assertEqual(
            len([node for node in workspace.nodes.values() if node.type_id == "core.subnode"]),
            1,
        )


if __name__ == "__main__":
    unittest.main()
