from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, QPointF, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.ui_qml.graph_scene_mutation_history import GraphSceneMutationHistory

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

_SNAP_GRID_SIZE = 20.0


class GraphSceneCommandBridge(QObject):
    pending_surface_action_changed = pyqtSignal()

    def __init__(
        self,
        scene_bridge: GraphSceneBridge,
        *,
        scope_selection: Any,
        authoring_boundary: GraphSceneMutationHistory,
        pending_surface_action: Any,
    ) -> None:
        super().__init__(scene_bridge)
        self._scene_bridge = scene_bridge
        self._scope_selection = scope_selection
        self._authoring_boundary = authoring_boundary
        self._pending_surface_action = pending_surface_action
        scene_bridge.pending_surface_action_changed.connect(self.pending_surface_action_changed.emit)

    @property
    def scene_bridge(self) -> GraphSceneBridge:
        return self._scene_bridge

    @pyqtProperty(str, notify=pending_surface_action_changed)
    def pending_surface_action_node_id(self) -> str:
        return self._pending_surface_action.node_id

    def clearSelection(self) -> None:
        self._scope_selection.clear_selection()

    @pyqtSlot()
    def clear_selection(self) -> None:
        self._scope_selection.clear_selection()

    @pyqtSlot(str)
    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        self._scope_selection.select_node(node_id, additive=additive)

    @pyqtSlot(float, float, float, float)
    @pyqtSlot(float, float, float, float, bool)
    def select_nodes_in_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        additive: bool = False,
    ) -> None:
        self._scope_selection.select_nodes_in_rect(
            x1,
            y1,
            x2,
            y2,
            additive=additive,
        )

    @pyqtSlot(str)
    def set_pending_surface_action(self, node_id: str) -> None:
        if self._pending_surface_action.set(node_id):
            self._scene_bridge.pending_surface_action_changed.emit()

    @pyqtSlot(str, result=bool)
    def consume_pending_surface_action(self, node_id: str) -> bool:
        if self._pending_surface_action.consume(node_id):
            self._scene_bridge.pending_surface_action_changed.emit()
            return True
        return False

    @pyqtSlot(str, float, float, result=str)
    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        return self._authoring_boundary.add_node_from_type(type_id, x, y)

    @pyqtSlot(str, str, float, float, result=str)
    def add_path_pointer_node(self, path: str, mode: str, x: float = 0.0, y: float = 0.0) -> str:
        node_id = self._authoring_boundary.add_node_from_type("io.path_pointer", x, y)
        self._authoring_boundary.set_node_properties(
            node_id,
            {
                "path": str(path or ""),
                "mode": str(mode or "file").strip() or "file",
            },
        )
        return node_id

    @pyqtSlot(str, float, float, result=str)
    def add_folder_explorer_node(self, current_path: str, x: float = 0.0, y: float = 0.0) -> str:
        node_id = self._authoring_boundary.add_node_from_type("io.folder_explorer", x, y)
        self._authoring_boundary.set_node_property(node_id, "current_path", str(current_path or ""))
        return node_id

    def add_subnode_shell_pin(self, shell_node_id: str, pin_type_id: str) -> str:
        return self._authoring_boundary.add_subnode_shell_pin(shell_node_id, pin_type_id)

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
        return self._authoring_boundary.add_edge(source_node_id, source_port, target_node_id, target_port)

    @pyqtSlot(str, str, result=str)
    def connect_nodes(self, node_a_id: str, node_b_id: str) -> str:
        return self._authoring_boundary.connect_nodes(node_a_id, node_b_id)

    def remove_edge(self, edge_id: str) -> None:
        self._authoring_boundary.remove_edge(edge_id)

    def remove_node(self, node_id: str) -> None:
        self._authoring_boundary.remove_node(node_id)

    def remove_workspace_node(self, node_id: str) -> bool:
        return self._authoring_boundary.remove_workspace_node(node_id)

    @pyqtSlot(str)
    def focus_node_slot(self, node_id: str) -> None:
        self.focus_node(node_id)

    def focus_node(self, node_id: str) -> QPointF | None:
        return self._authoring_boundary.focus_node(node_id)

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        self._authoring_boundary.set_node_collapsed(node_id, collapsed)

    @pyqtSlot(str, str, str)
    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None:
        self._authoring_boundary.set_node_port_label(node_id, port_key, label)

    @pyqtSlot(str, str, "QVariant")
    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        self._authoring_boundary.set_node_property(node_id, key, value)

    @pyqtSlot(str, "QVariantMap", result=bool)
    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool:
        return self._authoring_boundary.set_node_properties(node_id, values)

    @pyqtSlot("QVariant", result="QVariantMap")
    def normalize_node_visual_style(self, visual_style: Any) -> dict[str, Any]:
        return self._authoring_boundary.normalize_node_visual_style(visual_style)

    @pyqtSlot(str, "QVariant")
    def set_node_visual_style(self, node_id: str, visual_style: Any) -> None:
        self._authoring_boundary.set_node_visual_style(node_id, visual_style)

    @pyqtSlot(str)
    def clear_node_visual_style(self, node_id: str) -> None:
        self._authoring_boundary.clear_node_visual_style(node_id)

    def set_node_title(self, node_id: str, title: str) -> None:
        self._authoring_boundary.set_node_title(node_id, title)

    @pyqtSlot("QVariant", result=str)
    def normalize_edge_label(self, label: Any) -> str:
        return self._authoring_boundary.normalize_edge_label(label)

    @pyqtSlot(str, "QVariant")
    def set_edge_label(self, edge_id: str, label: Any) -> None:
        self._authoring_boundary.set_edge_label(edge_id, label)

    @pyqtSlot(str)
    def clear_edge_label(self, edge_id: str) -> None:
        self._authoring_boundary.clear_edge_label(edge_id)

    @pyqtSlot("QVariant", result="QVariantMap")
    def normalize_edge_visual_style(self, visual_style: Any) -> dict[str, Any]:
        return self._authoring_boundary.normalize_edge_visual_style(visual_style)

    @pyqtSlot(str, "QVariant")
    def set_edge_visual_style(self, edge_id: str, visual_style: Any) -> None:
        self._authoring_boundary.set_edge_visual_style(edge_id, visual_style)

    @pyqtSlot(str)
    def clear_edge_visual_style(self, edge_id: str) -> None:
        self._authoring_boundary.clear_edge_visual_style(edge_id)

    @pyqtSlot(str, str, bool, result=bool)
    def set_port_locked(self, node_id: str, key: str, locked: bool) -> bool:
        return self._authoring_boundary.set_port_locked(node_id, key, locked)

    @pyqtSlot(bool, result=bool)
    def set_hide_locked_ports(self, hide_locked_ports: bool) -> bool:
        return self._authoring_boundary.set_hide_locked_ports(hide_locked_ports)

    @pyqtSlot(bool, result=bool)
    def set_hide_optional_ports(self, hide_optional_ports: bool) -> bool:
        return self._authoring_boundary.set_hide_optional_ports(hide_optional_ports)

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> None:
        self._authoring_boundary.set_exposed_port(node_id, key, exposed)

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        self._authoring_boundary.move_node(node_id, x, y)

    @pyqtSlot(str, float, float)
    def resize_node(self, node_id: str, width: float, height: float) -> None:
        self._authoring_boundary.resize_node(node_id, width, height)

    @pyqtSlot(str, float, float, float, float)
    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        self._authoring_boundary.set_node_geometry(node_id, x, y, width, height)

    @pyqtSlot("QVariantList", float, float, result=bool)
    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool:
        return self._authoring_boundary.move_nodes_by_delta(node_ids, dx, dy)

    def align_selected_nodes(
        self,
        alignment: str,
        *,
        snap_to_grid: bool = False,
        grid_size: float = _SNAP_GRID_SIZE,
    ) -> bool:
        return self._authoring_boundary.align_selected_nodes(
            alignment,
            snap_to_grid=snap_to_grid,
            grid_size=grid_size,
        )

    def distribute_selected_nodes(
        self,
        orientation: str,
        *,
        snap_to_grid: bool = False,
        grid_size: float = _SNAP_GRID_SIZE,
    ) -> bool:
        return self._authoring_boundary.distribute_selected_nodes(
            orientation,
            snap_to_grid=snap_to_grid,
            grid_size=grid_size,
        )

    @pyqtSlot("QVariantList", result=str)
    def wrap_node_ids_in_comment_backdrop(self, node_ids: list[Any]) -> str:
        return self._authoring_boundary.wrap_nodes_in_comment_backdrop(node_ids)

    @pyqtSlot(result=bool)
    def wrap_selected_nodes_in_comment_backdrop(self) -> bool:
        return self._authoring_boundary.wrap_selected_nodes_in_comment_backdrop()

    @pyqtSlot(result=bool)
    def group_selected_nodes(self) -> bool:
        return self._authoring_boundary.group_selected_nodes()

    @pyqtSlot(result=bool)
    def ungroup_selected_subnode(self) -> bool:
        return self._authoring_boundary.ungroup_selected_subnode()

    @pyqtSlot(result=bool)
    def duplicate_selected_subgraph(self) -> bool:
        return self._authoring_boundary.duplicate_selected_subgraph()

    def serialize_selected_subgraph_fragment(self) -> dict[str, Any] | None:
        return self._authoring_boundary.serialize_selected_subgraph_fragment()

    def fragment_bounds_center(self, fragment_payload: Any) -> tuple[float, float] | None:
        return self._authoring_boundary.fragment_bounds_center(fragment_payload)

    def paste_subgraph_fragment(self, fragment_payload: Any, center_x: float, center_y: float) -> bool:
        return self._authoring_boundary.paste_subgraph_fragment(fragment_payload, center_x, center_y)

    def delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:
        return self._authoring_boundary.delete_selected_graph_items(edge_ids)


__all__ = ["GraphSceneCommandBridge"]
