"""Handles inspector panel logic: selected node properties, port exposure, collapse."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from ea_node_editor.graph.model import GraphModel, NodeInstance
    from ea_node_editor.nodes.registry import NodeRegistry
    from ea_node_editor.nodes.types import NodeTypeSpec
    from ea_node_editor.ui_qml.graph_bridge import QmlGraphScene
    from ea_node_editor.workspace.manager import WorkspaceManager


class InspectorController(QObject):
    selected_node_changed = pyqtSignal()

    def __init__(
        self,
        model: GraphModel,
        registry: NodeRegistry,
        scene: QmlGraphScene,
        workspace_manager: WorkspaceManager,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self._registry = registry
        self._scene = scene
        self._workspace_manager = workspace_manager

    def update_model(self, model: GraphModel, workspace_manager: WorkspaceManager) -> None:
        self._model = model
        self._workspace_manager = workspace_manager

    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None:
        node_id = self._scene.selected_node_id()
        if not node_id:
            return None
        workspace = self._model.project.workspaces.get(self._workspace_manager.active_workspace_id())
        if workspace is None:
            return None
        node = workspace.nodes.get(node_id)
        if node is None:
            return None
        spec = self._registry.get_spec(node.type_id)
        return node, spec

    def selected_node_summary(self) -> str:
        selected = self.selected_node_context()
        if selected is None:
            return "No node selected"
        node, spec = selected
        return f"{spec.display_name}\nID: {node.node_id}\nType: {node.type_id}"

    def selected_node_property_items(self) -> list[dict[str, Any]]:
        selected = self.selected_node_context()
        if selected is None:
            return []
        node, spec = selected
        return [
            {
                "key": prop.key,
                "label": prop.label,
                "type": prop.type,
                "value": node.properties.get(prop.key, prop.default),
                "enum_values": list(prop.enum_values),
            }
            for prop in spec.properties
        ]

    def selected_node_port_items(self) -> list[dict[str, Any]]:
        selected = self.selected_node_context()
        if selected is None:
            return []
        node, spec = selected
        return [
            {
                "key": port.key,
                "direction": port.direction,
                "kind": port.kind,
                "data_type": port.data_type,
                "required": bool(port.required),
                "exposed": bool(node.exposed_ports.get(port.key, port.exposed)),
            }
            for port in spec.ports
        ]

    def set_property(self, node_id: str, key: str, value: Any) -> None:
        self._scene.set_node_property(node_id, key, value)
        self.selected_node_changed.emit()

    def set_port_exposed(self, node_id: str, key: str, exposed: bool) -> None:
        self._scene.set_exposed_port(node_id, key, exposed)
        self.selected_node_changed.emit()

    def set_collapsed(self, node_id: str, collapsed: bool) -> None:
        self._scene.set_node_collapsed(node_id, collapsed)
        self.selected_node_changed.emit()

    @staticmethod
    def coerce_editor_input_value(prop_type: str, value: Any, default: Any) -> Any:
        if prop_type == "bool":
            return bool(value)
        if prop_type == "int":
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        if prop_type == "float":
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
        if prop_type == "json":
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return default
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return default
            return value
        return str(value)
