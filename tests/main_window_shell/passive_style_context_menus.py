from __future__ import annotations

from unittest.mock import patch

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QColor
from PyQt6.QtQuick import QQuickItem

from ea_node_editor.ui.shell.window import (
    ShellWindow,
    _FLOW_EDGE_STYLE_CLIPBOARD_KIND,
    _PASSIVE_NODE_STYLE_CLIPBOARD_KIND,
    _STYLE_CLIPBOARD_APP_PROPERTY,
)
from tests.main_window_shell.base import SharedMainWindowShellTestBase


def _menu_action_texts(menu: QObject) -> list[str]:
    actions = menu.property("visibleActions") or []
    if hasattr(actions, "toVariant"):
        actions = actions.toVariant()
    texts: list[str] = []
    for action in actions:
        if hasattr(action, "toVariant"):
            action = action.toVariant()
        if isinstance(action, dict):
            texts.append(str(action.get("text", "")))
    return texts


def _color_name(value: object) -> str:
    return QColor(value).name(QColor.NameFormat.HexRgb)


def _named_child_items(root: QObject, object_name: str) -> list[QQuickItem]:
    matches: list[QQuickItem] = []

    def _visit(item: QObject) -> None:
        if not isinstance(item, QQuickItem):
            return
        if item.objectName() == object_name:
            matches.append(item)
        for child in item.childItems():
            _visit(child)

    _visit(root)
    return matches


def _node_card_for(graph_canvas: QObject, node_id: str) -> QQuickItem | None:
    for item in _named_child_items(graph_canvas, "graphNodeCard"):
        node_data = item.property("nodeData")
        if isinstance(node_data, dict) and str(node_data.get("node_id", "")) == str(node_id):
            return item
    return None


def _style_clipboard_property_name(kind: str) -> str:
    return f"{_STYLE_CLIPBOARD_APP_PROPERTY}:{kind}"


class MainWindowShellPassiveStyleContextMenuTests(SharedMainWindowShellTestBase):
    def test_passive_node_context_menu_exposes_style_actions_only_for_passive_nodes(self) -> None:
        graph_canvas = self._graph_canvas_item()
        node_context_popup = graph_canvas.findChild(QObject, "graphCanvasNodeContextPopup")
        self.assertIsNotNone(node_context_popup)

        passive_id = self.window.scene.add_node_from_type("passive.planning.task_card", 120.0, 80.0)
        standard_id = self.window.scene.add_node_from_type("core.logger", 420.0, 80.0)
        self.app.processEvents()

        graph_canvas.setProperty("nodeContextNodeId", passive_id)
        self.app.processEvents()
        passive_actions = _menu_action_texts(node_context_popup)
        self.assertIn("Edit Style...", passive_actions)
        self.assertIn("Reset Style", passive_actions)
        self.assertIn("Copy Style", passive_actions)
        self.assertIn("Paste Style", passive_actions)

        graph_canvas.setProperty("nodeContextNodeId", standard_id)
        self.app.processEvents()
        standard_actions = _menu_action_texts(node_context_popup)
        self.assertNotIn("Edit Style...", standard_actions)
        self.assertNotIn("Reset Style", standard_actions)
        self.assertNotIn("Copy Style", standard_actions)
        self.assertNotIn("Paste Style", standard_actions)
        graph_canvas.setProperty("nodeContextNodeId", "")
        graph_canvas.setProperty("nodeContextVisible", False)
        self.app.processEvents()

    def test_flow_edge_context_menu_exposes_flow_style_actions_only_for_flow_edges(self) -> None:
        graph_canvas = self._graph_canvas_item()
        edge_context_popup = graph_canvas.findChild(QObject, "graphCanvasEdgeContextPopup")
        self.assertIsNotNone(edge_context_popup)

        source_id = self.window.scene.add_node_from_type("passive.flowchart.process", 80.0, 60.0)
        target_id = self.window.scene.add_node_from_type("passive.flowchart.decision", 360.0, 60.0)
        flow_edge_id = self.window.scene.add_edge(source_id, "right", target_id, "left")

        constant_id = self.window.scene.add_node_from_type("core.constant", 80.0, 260.0)
        branch_id = self.window.scene.add_node_from_type("core.branch", 380.0, 260.0)
        data_edge_id = self.window.scene.add_edge(constant_id, "as_text", branch_id, "condition")
        self.app.processEvents()

        graph_canvas.setProperty("edgeContextEdgeId", flow_edge_id)
        self.app.processEvents()
        flow_actions = _menu_action_texts(edge_context_popup)
        self.assertIn("Edit Flow Edge...", flow_actions)
        self.assertIn("Edit Label...", flow_actions)
        self.assertIn("Reset Style", flow_actions)
        self.assertIn("Copy Style", flow_actions)
        self.assertIn("Paste Style", flow_actions)

        graph_canvas.setProperty("edgeContextEdgeId", data_edge_id)
        self.app.processEvents()
        data_actions = _menu_action_texts(edge_context_popup)
        self.assertNotIn("Edit Flow Edge...", data_actions)
        self.assertNotIn("Edit Label...", data_actions)
        self.assertNotIn("Reset Style", data_actions)
        self.assertNotIn("Copy Style", data_actions)
        self.assertNotIn("Paste Style", data_actions)
        graph_canvas.setProperty("edgeContextEdgeId", "")
        graph_canvas.setProperty("edgeContextVisible", False)
        self.app.processEvents()

    def test_passive_node_style_slots_apply_copy_paste_and_reset_only_for_passive_nodes(self) -> None:
        workspace = self.window.model.project.workspaces[self.window.workspace_manager.active_workspace_id()]
        clipboard = self.app.clipboard()
        source_id = self.window.scene.add_node_from_type("passive.annotation.sticky_note", 120.0, 80.0)
        target_id = self.window.scene.add_node_from_type("passive.annotation.callout", 420.0, 80.0)
        standard_id = self.window.scene.add_node_from_type("core.logger", 720.0, 80.0)
        self.app.processEvents()

        style_payload = {
            "fill_color": "#FFEAA7",
            "border_color": "#7F5539",
            "text_color": "#1F2933",
            "accent_color": "#E17055",
            "border_width": 2.0,
            "corner_radius": 18.0,
            "font_size": 13,
            "font_weight": "bold",
        }

        with patch.object(ShellWindow, "edit_passive_node_style", return_value=style_payload):
            self.assertTrue(self.window.request_edit_passive_node_style(source_id))

        self.assertEqual(workspace.nodes[source_id].visual_style, style_payload)
        self.assertFalse(self.window.request_edit_passive_node_style(standard_id))
        graph_canvas = self._graph_canvas_item()
        styled_card = _node_card_for(graph_canvas, source_id)
        self.assertIsNotNone(styled_card)
        self.assertEqual(_color_name(styled_card.property("color")), "#ffeaa7")
        self.assertEqual(_color_name(styled_card.property("headerTextColor")), "#1f2933")
        self.assertEqual(int(round(float(styled_card.property("radius")))), 18)

        clipboard.setText("external clipboard text")
        self.assertTrue(self.window.request_copy_passive_node_style(source_id))
        self.assertEqual(clipboard.text(), "external clipboard text")
        self.assertTrue(self.window.request_paste_passive_node_style(target_id))
        self.assertEqual(workspace.nodes[target_id].visual_style, style_payload)

        self.assertTrue(self.window.request_reset_passive_node_style(target_id))
        self.assertEqual(workspace.nodes[target_id].visual_style, {})
        self.app.setProperty(_style_clipboard_property_name(_PASSIVE_NODE_STYLE_CLIPBOARD_KIND), "")
        clipboard.setText(
            '{"kind":"passive-node-style","version":1,"style":{"fill_color":"#FFEAA7","border_width":2}}'
        )
        self.assertFalse(self.window.request_paste_passive_node_style(target_id))
        self.assertEqual(workspace.nodes[target_id].visual_style, {})
        self.assertFalse(self.window.request_copy_passive_node_style(standard_id))
        self.assertFalse(self.window.request_paste_passive_node_style(standard_id))

    def test_flow_edge_style_slots_apply_copy_paste_reset_and_label_only_for_flow_edges(self) -> None:
        workspace = self.window.model.project.workspaces[self.window.workspace_manager.active_workspace_id()]
        clipboard = self.app.clipboard()
        source_id = self.window.scene.add_node_from_type("passive.flowchart.process", 80.0, 60.0)
        target_id = self.window.scene.add_node_from_type("passive.flowchart.decision", 360.0, 60.0)
        flow_edge_id = self.window.scene.add_edge(source_id, "right", target_id, "left")
        sibling_edge_id = self.window.scene.add_edge(source_id, "bottom", target_id, "top")

        constant_id = self.window.scene.add_node_from_type("core.constant", 80.0, 260.0)
        branch_id = self.window.scene.add_node_from_type("core.branch", 380.0, 260.0)
        data_edge_id = self.window.scene.add_edge(constant_id, "as_text", branch_id, "condition")
        self.app.processEvents()

        style_payload = {
            "stroke_color": "#224466",
            "stroke_width": 3.5,
            "stroke_pattern": "dashed",
            "arrow_head": "open",
            "label_text_color": "#F0F4FB",
            "label_background_color": "#223344",
        }

        clipboard.setText("external clipboard text")
        with patch.object(ShellWindow, "edit_flow_edge_style", return_value=style_payload):
            self.assertTrue(self.window.request_edit_flow_edge_style(flow_edge_id))

        self.assertEqual(workspace.edges[flow_edge_id].visual_style, style_payload)
        self.assertEqual(clipboard.text(), "external clipboard text")
        edge_payload = {item["edge_id"]: item for item in self.window.scene.edges_model}
        self.assertEqual(edge_payload[flow_edge_id]["flow_style"], style_payload)
        self.assertFalse(self.window.request_edit_flow_edge_style(data_edge_id))

        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Primary Path", True)):
            self.assertTrue(self.window.request_edit_flow_edge_label(flow_edge_id))
        self.assertEqual(workspace.edges[flow_edge_id].label, "Primary Path")
        self.assertFalse(self.window.request_edit_flow_edge_label(data_edge_id))

        self.assertTrue(self.window.request_copy_flow_edge_style(flow_edge_id))
        self.assertEqual(clipboard.text(), "external clipboard text")
        clipboard.setText("clipboard should stay untouched")
        self.assertTrue(self.window.request_paste_flow_edge_style(sibling_edge_id))
        self.assertEqual(workspace.edges[sibling_edge_id].visual_style, style_payload)
        self.assertEqual(clipboard.text(), "clipboard should stay untouched")

        self.assertTrue(self.window.request_reset_flow_edge_style(sibling_edge_id))
        self.assertEqual(workspace.edges[sibling_edge_id].visual_style, {})
        self.app.setProperty(_style_clipboard_property_name(_FLOW_EDGE_STYLE_CLIPBOARD_KIND), "")
        clipboard.setText(
            '{"kind":"flow-edge-style","version":1,"style":{"stroke_pattern":"dashed","arrow_head":"open"}}'
        )
        self.assertFalse(self.window.request_paste_flow_edge_style(sibling_edge_id))
        self.assertEqual(workspace.edges[sibling_edge_id].visual_style, {})
        self.assertFalse(self.window.request_copy_flow_edge_style(data_edge_id))
        self.assertFalse(self.window.request_paste_flow_edge_style(data_edge_id))
