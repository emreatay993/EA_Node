from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, QPointF, QRectF, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.graph.model import GraphModel, NodeInstance, WorkspaceData
from ea_node_editor.graph.rules import (
    are_data_types_compatible,
    are_port_kinds_compatible,
    default_port,
    find_port,
    is_port_exposed,
    port_data_type,
    port_direction,
    port_kind,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.shell.runtime_history import (
    ACTION_ADD_EDGE,
    ACTION_ADD_NODE,
    ACTION_EDIT_PROPERTY,
    ACTION_MOVE_NODE,
    ACTION_REMOVE_EDGE,
    ACTION_REMOVE_NODE,
    ACTION_RENAME_NODE,
    ACTION_TOGGLE_COLLAPSED,
    ACTION_TOGGLE_EXPOSED_PORT,
)
from ea_node_editor.ui_qml.edge_routing import build_edge_payload, category_accent, node_size, port_scene_pos

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory, WorkspaceSnapshot

_MISSING = object()


@dataclass(slots=True)
class _SelectedNodeProxy:
    node: NodeInstance


class _NodeItemProxy:
    def __init__(self, node: NodeInstance, spec: NodeTypeSpec) -> None:
        self.node = node
        self.spec = spec

    def sceneBoundingRect(self) -> QRectF:
        width, height = node_size(self.node, self.spec)
        return QRectF(self.node.x, self.node.y, width, height)

    def port_scene_pos(self, port_key: str) -> QPointF:
        return port_scene_pos(self.node, self.spec, port_key)


class GraphSceneBridge(QObject):
    node_selected = pyqtSignal(str)
    workspace_changed = pyqtSignal(str)
    nodes_changed = pyqtSignal()
    edges_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model: GraphModel | None = None
        self._registry: NodeRegistry | None = None
        self._history: RuntimeGraphHistory | None = None
        self._workspace_id = ""
        self._selected_node_ids: list[str] = []
        self._nodes_payload: list[dict[str, Any]] = []
        self._edges_payload: list[dict[str, Any]] = []

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @pyqtProperty("QVariantList", notify=nodes_changed)
    def nodes_model(self) -> list[dict[str, Any]]:
        return self._nodes_payload

    @pyqtProperty("QVariantList", notify=edges_changed)
    def edges_model(self) -> list[dict[str, Any]]:
        return self._edges_payload

    @pyqtProperty(str, notify=node_selected)
    def selected_node_id_value(self) -> str:
        selected = self.selected_node_id()
        return selected or ""

    def bind_runtime_history(self, history: RuntimeGraphHistory | None) -> None:
        self._history = history

    def _require_bound(self) -> tuple[GraphModel, NodeRegistry]:
        if self._model is None or self._registry is None:
            raise RuntimeError("Scene is not bound")
        return self._model, self._registry

    def set_workspace(self, model: GraphModel, registry: NodeRegistry, workspace_id: str) -> None:
        self._model = model
        self._registry = registry
        self._workspace_id = workspace_id
        self._selected_node_ids = []

        self._rebuild_models()
        self.workspace_changed.emit(workspace_id)
        self.node_selected.emit("")

    def current_workspace(self) -> WorkspaceData:
        if self._model is None:
            raise RuntimeError("Scene has no graph model")
        return self._model.project.workspaces[self._workspace_id]

    def refresh_workspace_from_model(self, workspace_id: str) -> None:
        if self._model is None:
            return
        normalized_workspace_id = str(workspace_id).strip()
        if not normalized_workspace_id or normalized_workspace_id != self._workspace_id:
            return
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return
        self._selected_node_ids = [node_id for node_id in self._selected_node_ids if node_id in workspace.nodes]
        self._rebuild_models()
        self.node_selected.emit(self.selected_node_id() or "")

    def selected_node_id(self) -> str | None:
        for node_id in reversed(self._selected_node_ids):
            if self._node(node_id) is not None:
                return node_id
        return None

    def selectedItems(self) -> list[_SelectedNodeProxy]:
        workspace = self.current_workspace()
        selected: list[_SelectedNodeProxy] = []
        for node_id in self._selected_node_ids:
            node = workspace.nodes.get(node_id)
            if node is not None:
                selected.append(_SelectedNodeProxy(node=node))
        return selected

    def workspace_scene_bounds(self) -> QRectF | None:
        if self._model is None or not self._workspace_id:
            return None
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None or not workspace.nodes:
            return None
        return self._bounds_for_node_ids(list(workspace.nodes))

    def selection_bounds(self) -> QRectF | None:
        if not self._selected_node_ids:
            return None
        return self._bounds_for_node_ids(self._selected_node_ids)

    def clearSelection(self) -> None:
        if not self._selected_node_ids:
            return
        self._selected_node_ids = []
        self._rebuild_models()
        self.node_selected.emit("")

    @pyqtSlot()
    def clear_selection(self) -> None:
        self.clearSelection()

    @pyqtSlot(str)
    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        if not node_id:
            self.clearSelection()
            return
        if self._node(node_id) is None:
            return
        if additive:
            if node_id in self._selected_node_ids:
                self._selected_node_ids = [value for value in self._selected_node_ids if value != node_id]
            else:
                self._selected_node_ids.append(node_id)
        else:
            self._selected_node_ids = [node_id]
        self._rebuild_models()
        self.node_selected.emit(self.selected_node_id() or "")

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
        if self._model is None or self._registry is None or not self._workspace_id:
            return

        workspace = self.current_workspace()
        min_x = min(float(x1), float(x2))
        max_x = max(float(x1), float(x2))
        min_y = min(float(y1), float(y2))
        max_y = max(float(y1), float(y2))

        hit_ids: list[str] = []
        for node_id, node in workspace.nodes.items():
            spec = self._registry.get_spec(node.type_id)
            width, height = node_size(node, spec)
            node_min_x = float(node.x)
            node_max_x = node_min_x + width
            node_min_y = float(node.y)
            node_max_y = node_min_y + height
            if node_max_x < min_x or node_min_x > max_x or node_max_y < min_y or node_min_y > max_y:
                continue
            hit_ids.append(node_id)

        if additive:
            next_selected = [node_id for node_id in self._selected_node_ids if node_id in workspace.nodes]
            for node_id in hit_ids:
                if node_id not in next_selected:
                    next_selected.append(node_id)
        else:
            next_selected = hit_ids

        if next_selected == self._selected_node_ids:
            return

        self._selected_node_ids = next_selected
        self._rebuild_models()
        self.node_selected.emit(self.selected_node_id() or "")

    def node_item(self, node_id: str) -> _NodeItemProxy | None:
        node = self._node(node_id)
        if node is None or self._registry is None:
            return None
        spec = self._registry.get_spec(node.type_id)
        return _NodeItemProxy(node=node, spec=spec)

    def node_bounds(self, node_id: str) -> QRectF | None:
        item = self.node_item(node_id)
        if item is None:
            return None
        return QRectF(item.sceneBoundingRect())

    def edge_item(self, edge_id: str) -> dict[str, Any] | None:
        workspace = self.current_workspace()
        edge = workspace.edges.get(edge_id)
        if edge is None:
            return None
        return {
            "edge_id": edge.edge_id,
            "source_node_id": edge.source_node_id,
            "source_port_key": edge.source_port_key,
            "target_node_id": edge.target_node_id,
            "target_port_key": edge.target_port_key,
        }

    @pyqtSlot(str, float, float, result=str)
    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        model, registry = self._require_bound()
        history_before = self._capture_history_snapshot()
        spec = registry.get_spec(type_id)
        node = model.add_node(
            self._workspace_id,
            type_id=type_id,
            title=spec.display_name,
            x=float(x),
            y=float(y),
            properties=registry.default_properties(type_id),
            exposed_ports={port.key: port.exposed for port in spec.ports},
        )
        self._selected_node_ids = [node.node_id]
        self._rebuild_models()
        self.node_selected.emit(node.node_id)
        self._record_history(ACTION_ADD_NODE, history_before)
        return node.node_id

    @pyqtSlot(str, str, str, str, result=bool)
    def are_ports_compatible(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> bool:
        if self._registry is None:
            return False
        source_node = self._node(source_node_id)
        target_node = self._node(target_node_id)
        if source_node is None or target_node is None:
            return False
        source_spec = self._registry.get_spec(source_node.type_id)
        target_spec = self._registry.get_spec(target_node.type_id)
        try:
            source_kind = port_kind(source_spec, source_port)
            target_kind = port_kind(target_spec, target_port)
            source_dt = port_data_type(source_spec, source_port)
            target_dt = port_data_type(target_spec, target_port)
        except KeyError:
            return False
        return are_port_kinds_compatible(source_kind, target_kind) and are_data_types_compatible(source_dt, target_dt)

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return are_port_kinds_compatible(str(source_kind), str(target_kind))

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return are_data_types_compatible(str(source_type), str(target_type))

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
        model, registry = self._require_bound()
        history_before = self._capture_history_snapshot()
        source_node = self._node_or_raise(source_node_id)
        target_node = self._node_or_raise(target_node_id)
        source_spec = registry.get_spec(source_node.type_id)
        target_spec = registry.get_spec(target_node.type_id)

        if port_direction(source_spec, source_port) != "out":
            raise ValueError(f"Source port must be an output: {source_node_id}.{source_port}")
        if port_direction(target_spec, target_port) != "in":
            raise ValueError(f"Target port must be an input: {target_node_id}.{target_port}")
        source_kind = port_kind(source_spec, source_port)
        target_kind = port_kind(target_spec, target_port)
        if not are_port_kinds_compatible(source_kind, target_kind):
            raise ValueError(f"Incompatible port kinds: {source_kind} -> {target_kind}.")
        if not is_port_exposed(source_node, source_spec, source_port):
            raise ValueError(f"Source port is hidden: {source_node_id}.{source_port}")
        if not is_port_exposed(target_node, target_spec, target_port):
            raise ValueError(f"Target port is hidden: {target_node_id}.{target_port}")

        existing = self._find_model_edge_id(source_node_id, source_port, target_node_id, target_port)
        if existing:
            return existing

        edge = model.add_edge(
            self._workspace_id,
            source_node_id=source_node_id,
            source_port_key=source_port,
            target_node_id=target_node_id,
            target_port_key=target_port,
        )
        self._rebuild_models()
        self._record_history(ACTION_ADD_EDGE, history_before)
        return edge.edge_id

    @pyqtSlot(str, str, result=str)
    def connect_nodes(self, node_a_id: str, node_b_id: str) -> str:
        model, registry = self._require_bound()
        workspace = model.project.workspaces[self._workspace_id]
        node_a = workspace.nodes[node_a_id]
        node_b = workspace.nodes[node_b_id]
        spec_a = registry.get_spec(node_a.type_id)
        spec_b = registry.get_spec(node_b.type_id)

        a_to_b = (default_port(node_a, spec_a, "out"), default_port(node_b, spec_b, "in"))
        b_to_a = (default_port(node_b, spec_b, "out"), default_port(node_a, spec_a, "in"))

        can_a_to_b = all(a_to_b)
        can_b_to_a = all(b_to_a)
        if can_a_to_b and (not can_b_to_a or node_a.x <= node_b.x):
            return self.add_edge(node_a_id, a_to_b[0], node_b_id, a_to_b[1])
        if can_b_to_a:
            return self.add_edge(node_b_id, b_to_a[0], node_a_id, b_to_a[1])
        raise ValueError("Selected nodes do not have compatible out/in ports.")

    def remove_edge(self, edge_id: str) -> None:
        if self._model is None:
            return
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None or edge_id not in workspace.edges:
            return
        history_before = self._capture_history_snapshot()
        self._model.remove_edge(self._workspace_id, edge_id)
        self._rebuild_models()
        self._record_history(ACTION_REMOVE_EDGE, history_before)

    def remove_node(self, node_id: str) -> None:
        if self._model is None:
            return
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None or node_id not in workspace.nodes:
            return
        history_before = self._capture_history_snapshot()
        self._model.remove_node(self._workspace_id, node_id)
        self._selected_node_ids = [value for value in self._selected_node_ids if value != node_id]
        self._rebuild_models()
        if not self._selected_node_ids:
            self.node_selected.emit("")
        self._record_history(ACTION_REMOVE_NODE, history_before)

    @pyqtSlot(str)
    def focus_node_slot(self, node_id: str) -> None:
        self.focus_node(node_id)

    def focus_node(self, node_id: str) -> QPointF | None:
        item = self.node_item(node_id)
        if item is None:
            return None
        self._selected_node_ids = [node_id]
        self._rebuild_models()
        self.node_selected.emit(node_id)
        return item.sceneBoundingRect().center()

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        if self._model is None:
            return
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return
        node = workspace.nodes.get(node_id)
        if node is None:
            return
        normalized_collapsed = bool(collapsed)
        if bool(node.collapsed) == normalized_collapsed:
            return
        history_before = self._capture_history_snapshot()
        self._model.set_node_collapsed(self._workspace_id, node_id, normalized_collapsed)
        self._rebuild_models()
        self._record_history(ACTION_TOGGLE_COLLAPSED, history_before)

    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        if self._model is None or self._registry is None:
            return
        workspace = self._model.project.workspaces[self._workspace_id]
        node = workspace.nodes[node_id]
        normalized = self._registry.normalize_property_value(node.type_id, key, value)
        current_value = node.properties.get(key, _MISSING)
        if current_value is not _MISSING and current_value == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._model.set_node_property(self._workspace_id, node_id, key, normalized)
        self._rebuild_models()
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def set_node_title(self, node_id: str, title: str) -> None:
        if self._model is None:
            return
        node = self._node(node_id)
        if node is None:
            return
        normalized = str(title).strip()
        if not normalized:
            return
        if node.title == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._model.set_node_title(self._workspace_id, node_id, normalized)
        self._rebuild_models()
        self._record_history(ACTION_RENAME_NODE, history_before)

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> None:
        if self._model is None or self._registry is None:
            return
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return
        node = workspace.nodes.get(node_id)
        if node is None:
            return
        spec = self._registry.get_spec(node.type_id)
        port = find_port(spec, key)
        if port is None:
            return
        normalized_exposed = bool(exposed)
        current_exposed = bool(node.exposed_ports.get(key, port.exposed))
        if current_exposed == normalized_exposed:
            return
        history_before = self._capture_history_snapshot()
        self._model.set_exposed_port(self._workspace_id, node_id, key, normalized_exposed)
        if not normalized_exposed:
            affected_edges = [
                edge_id
                for edge_id, edge in workspace.edges.items()
                if (edge.source_node_id == node_id and edge.source_port_key == key)
                or (edge.target_node_id == node_id and edge.target_port_key == key)
            ]
            for edge_id in affected_edges:
                self._model.remove_edge(self._workspace_id, edge_id)
        self._rebuild_models()
        self._record_history(ACTION_TOGGLE_EXPOSED_PORT, history_before)

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        if self._model is None:
            return
        node = self._node(node_id)
        if node is None:
            return
        final_x = float(x)
        final_y = float(y)
        if float(node.x) == final_x and float(node.y) == final_y:
            return
        history_before = self._capture_history_snapshot()
        self._model.set_node_position(self._workspace_id, node_id, final_x, final_y)
        self._rebuild_models()
        self._record_history(ACTION_MOVE_NODE, history_before)

    def _node(self, node_id: str) -> NodeInstance | None:
        if self._model is None:
            return None
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return None
        return workspace.nodes.get(node_id)

    def _node_or_raise(self, node_id: str) -> NodeInstance:
        node = self._node(node_id)
        if node is None:
            raise KeyError(f"Unknown scene node: {node_id}")
        return node

    def _find_model_edge_id(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> str | None:
        if self._model is None:
            return None
        workspace = self._model.project.workspaces[self._workspace_id]
        for edge in workspace.edges.values():
            if (
                edge.source_node_id == source_node_id
                and edge.source_port_key == source_port
                and edge.target_node_id == target_node_id
                and edge.target_port_key == target_port
            ):
                return edge.edge_id
        return None

    def _bounds_for_node_ids(self, node_ids: list[str]) -> QRectF | None:
        bounds: QRectF | None = None
        for node_id in node_ids:
            node_bounds = self.node_bounds(node_id)
            if node_bounds is None:
                continue
            if bounds is None:
                bounds = QRectF(node_bounds)
                continue
            bounds = bounds.united(node_bounds)
        return bounds

    def _capture_history_snapshot(self) -> WorkspaceSnapshot | None:
        if self._history is None or self._model is None or not self._workspace_id:
            return None
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return None
        return self._history.capture_workspace(workspace)

    def _record_history(self, action_type: str, before_snapshot: WorkspaceSnapshot | None) -> None:
        if self._history is None or self._model is None or before_snapshot is None or not self._workspace_id:
            return
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return
        self._history.record_action(self._workspace_id, action_type, before_snapshot, workspace)

    def _rebuild_models(self) -> None:
        if self._model is None or self._registry is None or not self._workspace_id:
            self._nodes_payload = []
            self._edges_payload = []
            self.nodes_changed.emit()
            self.edges_changed.emit()
            return

        workspace = self._model.project.workspaces[self._workspace_id]
        workspace_edges = list(workspace.edges.values())
        port_connection_counts: dict[tuple[str, str], int] = {}
        for edge in workspace_edges:
            source_key = (edge.source_node_id, edge.source_port_key)
            target_key = (edge.target_node_id, edge.target_port_key)
            port_connection_counts[source_key] = port_connection_counts.get(source_key, 0) + 1
            port_connection_counts[target_key] = port_connection_counts.get(target_key, 0) + 1

        nodes_payload: list[dict[str, Any]] = []
        node_specs: dict[str, NodeTypeSpec] = {}

        for node_id, node in workspace.nodes.items():
            spec = self._registry.get_spec(node.type_id)
            node_specs[node_id] = spec
            width, height = node_size(node, spec)
            ports_payload: list[dict[str, Any]] = []
            for port in spec.ports:
                exposed = bool(node.exposed_ports.get(port.key, port.exposed))
                if not exposed:
                    continue
                connection_count = port_connection_counts.get((node.node_id, port.key), 0)
                ports_payload.append(
                    {
                        "key": port.key,
                        "direction": port.direction,
                        "kind": port.kind,
                        "data_type": port.data_type,
                        "exposed": exposed,
                        "connection_count": int(connection_count),
                        "connected": bool(connection_count),
                    }
                )
            nodes_payload.append(
                {
                    "node_id": node.node_id,
                    "type_id": node.type_id,
                    "title": node.title,
                    "x": float(node.x),
                    "y": float(node.y),
                    "width": float(width),
                    "height": float(height),
                    "accent": category_accent(spec.category),
                    "collapsed": bool(node.collapsed),
                    "selected": node.node_id in self._selected_node_ids,
                    "ports": ports_payload,
                }
            )

        edges_payload = build_edge_payload(
            workspace_edges=workspace_edges,
            workspace_nodes=workspace.nodes,
            node_specs=node_specs,
        )

        self._nodes_payload = nodes_payload
        self._edges_payload = edges_payload
        self.nodes_changed.emit()
        self.edges_changed.emit()


__all__ = ["GraphSceneBridge"]
