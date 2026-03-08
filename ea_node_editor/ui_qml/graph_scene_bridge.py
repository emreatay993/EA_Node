from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
import math
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, QPointF, QRectF, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.graph.effective_ports import (
    are_data_types_compatible,
    are_port_kinds_compatible,
    default_port,
    effective_ports,
    find_port,
    is_port_exposed,
    port_data_type,
    port_direction,
    port_kind,
)
from ea_node_editor.graph.hierarchy import (
    ScopePath,
    breadcrumb_scope_path,
    is_node_in_scope,
    node_scope_path,
    normalize_scope_path,
    scope_breadcrumb_payload,
    scope_edges,
    scope_node_ids,
    scope_parent_id,
    subnode_scope_path,
)
from ea_node_editor.graph.model import GraphModel, NodeInstance, ViewState, WorkspaceData
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.shell.runtime_clipboard import (
    build_graph_fragment_payload,
    normalize_graph_fragment_payload,
)
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
_MINIMAP_EMPTY_BOUNDS = QRectF(-1600.0, -900.0, 3200.0, 1800.0)
_MINIMAP_PADDING = 220.0
_MINIMAP_MIN_WIDTH = 3200.0
_MINIMAP_MIN_HEIGHT = 1800.0
_DUPLICATE_OFFSET_X = 40.0
_DUPLICATE_OFFSET_Y = 40.0
_SNAP_GRID_SIZE = 20.0


@dataclass(slots=True)
class _SelectedNodeProxy:
    node: NodeInstance


@dataclass(slots=True)
class _LayoutNodeMetrics:
    node_id: str
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height


class _NodeItemProxy:
    def __init__(
        self,
        node: NodeInstance,
        spec: NodeTypeSpec,
        workspace_nodes: dict[str, NodeInstance],
    ) -> None:
        self.node = node
        self.spec = spec
        self.workspace_nodes = workspace_nodes

    def sceneBoundingRect(self) -> QRectF:
        width, height = node_size(self.node, self.spec, self.workspace_nodes)
        return QRectF(self.node.x, self.node.y, width, height)

    def port_scene_pos(self, port_key: str) -> QPointF:
        return port_scene_pos(self.node, self.spec, port_key, self.workspace_nodes)


class GraphSceneBridge(QObject):
    node_selected = pyqtSignal(str)
    workspace_changed = pyqtSignal(str)
    scope_changed = pyqtSignal()
    nodes_changed = pyqtSignal()
    edges_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model: GraphModel | None = None
        self._registry: NodeRegistry | None = None
        self._history: RuntimeGraphHistory | None = None
        self._workspace_id = ""
        self._scope_path: ScopePath = ()
        self._selected_node_ids: list[str] = []
        self._nodes_payload: list[dict[str, Any]] = []
        self._minimap_nodes_payload: list[dict[str, Any]] = []
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

    @pyqtProperty("QVariantList", notify=nodes_changed)
    def minimap_nodes_model(self) -> list[dict[str, Any]]:
        return self._minimap_nodes_payload

    @pyqtProperty("QVariantMap", notify=nodes_changed)
    def workspace_scene_bounds_payload(self) -> dict[str, float]:
        return self._rect_payload(self.workspace_scene_bounds_with_fallback())

    @pyqtProperty(str, notify=node_selected)
    def selected_node_id_value(self) -> str:
        selected = self.selected_node_id()
        return selected or ""

    @pyqtProperty("QVariantList", notify=scope_changed)
    def active_scope_path(self) -> list[str]:
        return list(self._scope_path)

    @pyqtProperty("QVariantList", notify=scope_changed)
    def scope_breadcrumb_model(self) -> list[dict[str, str]]:
        workspace = self._workspace_or_none()
        if workspace is None:
            return []
        return scope_breadcrumb_payload(workspace, self._scope_path)

    @pyqtProperty(bool, notify=scope_changed)
    def can_navigate_scope_parent(self) -> bool:
        return bool(self._scope_path)

    def _workspace_or_none(self) -> WorkspaceData | None:
        if self._model is None or not self._workspace_id:
            return None
        return self._model.project.workspaces.get(self._workspace_id)

    def _active_view_state(self, workspace: WorkspaceData) -> ViewState | None:
        workspace.ensure_default_view()
        if not workspace.active_view_id:
            return None
        return workspace.views.get(workspace.active_view_id)

    def _apply_scope_path(
        self,
        workspace: WorkspaceData,
        scope_path: ScopePath,
        *,
        persist: bool = True,
        emit_scope_changed: bool = True,
        emit_selection_changed: bool = True,
    ) -> bool:
        normalized_scope = normalize_scope_path(workspace, scope_path)
        changed = normalized_scope != self._scope_path
        self._scope_path = normalized_scope
        if persist:
            view_state = self._active_view_state(workspace)
            if view_state is not None:
                view_state.scope_path = list(normalized_scope)
        selected_before = self.selected_node_id() or ""
        self._selected_node_ids = [node_id for node_id in self._selected_node_ids if is_node_in_scope(workspace, node_id, normalized_scope)]
        selected_after = self.selected_node_id() or ""
        if changed:
            self._rebuild_models()
            if emit_scope_changed:
                self.scope_changed.emit()
        elif selected_before != selected_after:
            self._rebuild_models()
        if emit_selection_changed and (changed or selected_before != selected_after):
            self.node_selected.emit(selected_after)
        return changed

    def _restore_scope_path_from_view(self, workspace: WorkspaceData) -> None:
        view_state = self._active_view_state(workspace)
        scope_path = ()
        if view_state is not None:
            scope_path = normalize_scope_path(workspace, view_state.scope_path)
            if list(scope_path) != view_state.scope_path:
                view_state.scope_path = list(scope_path)
        self._scope_path = scope_path

    @pyqtSlot(result=bool)
    def sync_scope_with_active_view(self) -> bool:
        workspace = self._workspace_or_none()
        if workspace is None:
            return False
        view_state = self._active_view_state(workspace)
        target_scope: ScopePath = ()
        if view_state is not None:
            target_scope = normalize_scope_path(workspace, view_state.scope_path)
        return self._apply_scope_path(workspace, target_scope)

    @pyqtSlot(str, result=bool)
    def open_subnode_scope(self, node_id: str) -> bool:
        workspace = self._workspace_or_none()
        if workspace is None:
            return False
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return False
        node = workspace.nodes.get(normalized_node_id)
        if node is None:
            return False
        if node.type_id != "core.subnode":
            return False
        if not is_node_in_scope(workspace, normalized_node_id, self._scope_path):
            return False
        return self._apply_scope_path(workspace, subnode_scope_path(workspace, normalized_node_id))

    @pyqtSlot(str, result=bool)
    def open_scope_for_node(self, node_id: str) -> bool:
        workspace = self._workspace_or_none()
        if workspace is None:
            return False
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id or normalized_node_id not in workspace.nodes:
            return False
        return self._apply_scope_path(workspace, node_scope_path(workspace, normalized_node_id))

    @pyqtSlot(result=bool)
    def navigate_scope_parent(self) -> bool:
        workspace = self._workspace_or_none()
        if workspace is None:
            return False
        if not self._scope_path:
            return False
        return self._apply_scope_path(workspace, self._scope_path[:-1])

    @pyqtSlot(result=bool)
    def navigate_scope_root(self) -> bool:
        workspace = self._workspace_or_none()
        if workspace is None:
            return False
        if not self._scope_path:
            return False
        return self._apply_scope_path(workspace, ())

    @pyqtSlot(str, result=bool)
    def navigate_scope_to(self, node_id: str) -> bool:
        workspace = self._workspace_or_none()
        if workspace is None:
            return False
        next_scope = breadcrumb_scope_path(workspace, self._scope_path, node_id)
        return self._apply_scope_path(workspace, next_scope)

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
        workspace = self._model.project.workspaces[self._workspace_id]
        self._restore_scope_path_from_view(workspace)

        self._rebuild_models()
        self.workspace_changed.emit(workspace_id)
        self.scope_changed.emit()
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
        normalized_scope = normalize_scope_path(workspace, self._scope_path)
        if normalized_scope != self._scope_path:
            self._apply_scope_path(
                workspace,
                normalized_scope,
                persist=True,
                emit_scope_changed=False,
                emit_selection_changed=False,
            )
            self.scope_changed.emit()
        else:
            self._selected_node_ids = [node_id for node_id in self._selected_node_ids if node_id in workspace.nodes]
            self._selected_node_ids = [node_id for node_id in self._selected_node_ids if is_node_in_scope(workspace, node_id, self._scope_path)]
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
        if workspace is None:
            return None
        visible_node_ids = scope_node_ids(workspace, self._scope_path)
        if not visible_node_ids:
            return None
        return self._bounds_for_node_ids(visible_node_ids)

    def workspace_scene_bounds_with_fallback(self) -> QRectF:
        bounds = self.workspace_scene_bounds()
        if bounds is None:
            return QRectF(_MINIMAP_EMPTY_BOUNDS)
        normalized = QRectF(bounds).normalized()
        if not normalized.isValid() or normalized.width() <= 0.0 or normalized.height() <= 0.0:
            return QRectF(_MINIMAP_EMPTY_BOUNDS)
        padded = normalized.adjusted(-_MINIMAP_PADDING, -_MINIMAP_PADDING, _MINIMAP_PADDING, _MINIMAP_PADDING)
        width = max(float(padded.width()), _MINIMAP_MIN_WIDTH)
        height = max(float(padded.height()), _MINIMAP_MIN_HEIGHT)
        center = padded.center()
        return QRectF(
            float(center.x()) - (width * 0.5),
            float(center.y()) - (height * 0.5),
            width,
            height,
        )

    def _rect_payload(self, rect: QRectF) -> dict[str, float]:
        normalized = QRectF(rect).normalized()
        return {
            "x": float(normalized.x()),
            "y": float(normalized.y()),
            "width": float(max(0.0, normalized.width())),
            "height": float(max(0.0, normalized.height())),
        }

    @pyqtSlot(result="QVariantMap")
    def workspace_scene_bounds_map(self) -> dict[str, float]:
        return self._rect_payload(self.workspace_scene_bounds_with_fallback())

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
        workspace = self._workspace_or_none()
        if workspace is None:
            return
        if self._node(node_id) is None:
            return
        if not is_node_in_scope(workspace, node_id, self._scope_path):
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
        visible_node_ids = set(scope_node_ids(workspace, self._scope_path))
        min_x = min(float(x1), float(x2))
        max_x = max(float(x1), float(x2))
        min_y = min(float(y1), float(y2))
        max_y = max(float(y1), float(y2))

        hit_ids: list[str] = []
        for node_id, node in workspace.nodes.items():
            if node_id not in visible_node_ids:
                continue
            spec = self._registry.get_spec(node.type_id)
            width, height = node_size(node, spec, workspace.nodes)
            node_min_x = float(node.x)
            node_max_x = node_min_x + width
            node_min_y = float(node.y)
            node_max_y = node_min_y + height
            if node_max_x < min_x or node_min_x > max_x or node_max_y < min_y or node_min_y > max_y:
                continue
            hit_ids.append(node_id)

        if additive:
            next_selected = [
                node_id
                for node_id in self._selected_node_ids
                if node_id in workspace.nodes and node_id in visible_node_ids
            ]
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
        if self._model is None:
            return None
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return None
        node = workspace.nodes.get(node_id)
        if node is None or self._registry is None:
            return None
        spec = self._registry.get_spec(node.type_id)
        return _NodeItemProxy(node=node, spec=spec, workspace_nodes=workspace.nodes)

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
        visible_node_ids = set(scope_node_ids(workspace, self._scope_path))
        if edge.source_node_id not in visible_node_ids or edge.target_node_id not in visible_node_ids:
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
        node.parent_node_id = scope_parent_id(self._scope_path)
        self._selected_node_ids = [node.node_id]
        self._rebuild_models()
        self.node_selected.emit(node.node_id)
        self._record_history(ACTION_ADD_NODE, history_before)
        return node.node_id

    @pyqtSlot(str, str, str, str, result=bool)
    def are_ports_compatible(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> bool:
        if self._registry is None or self._model is None:
            return False
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return False
        source_node = self._node(source_node_id)
        target_node = self._node(target_node_id)
        if source_node is None or target_node is None:
            return False
        source_spec = self._registry.get_spec(source_node.type_id)
        target_spec = self._registry.get_spec(target_node.type_id)
        try:
            source_kind = port_kind(
                node=source_node,
                spec=source_spec,
                workspace_nodes=workspace.nodes,
                port_key=source_port,
            )
            target_kind = port_kind(
                node=target_node,
                spec=target_spec,
                workspace_nodes=workspace.nodes,
                port_key=target_port,
            )
            source_dt = port_data_type(
                node=source_node,
                spec=source_spec,
                workspace_nodes=workspace.nodes,
                port_key=source_port,
            )
            target_dt = port_data_type(
                node=target_node,
                spec=target_spec,
                workspace_nodes=workspace.nodes,
                port_key=target_port,
            )
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
        workspace = model.project.workspaces[self._workspace_id]
        source_node = self._node_or_raise(source_node_id)
        target_node = self._node_or_raise(target_node_id)
        source_spec = registry.get_spec(source_node.type_id)
        target_spec = registry.get_spec(target_node.type_id)

        if (
            port_direction(
                node=source_node,
                spec=source_spec,
                workspace_nodes=workspace.nodes,
                port_key=source_port,
            )
            != "out"
        ):
            raise ValueError(f"Source port must be an output: {source_node_id}.{source_port}")
        if (
            port_direction(
                node=target_node,
                spec=target_spec,
                workspace_nodes=workspace.nodes,
                port_key=target_port,
            )
            != "in"
        ):
            raise ValueError(f"Target port must be an input: {target_node_id}.{target_port}")
        source_kind = port_kind(
            node=source_node,
            spec=source_spec,
            workspace_nodes=workspace.nodes,
            port_key=source_port,
        )
        target_kind = port_kind(
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace.nodes,
            port_key=target_port,
        )
        if not are_port_kinds_compatible(source_kind, target_kind):
            raise ValueError(f"Incompatible port kinds: {source_kind} -> {target_kind}.")
        if not is_port_exposed(
            node=source_node,
            spec=source_spec,
            workspace_nodes=workspace.nodes,
            port_key=source_port,
        ):
            raise ValueError(f"Source port is hidden: {source_node_id}.{source_port}")
        if not is_port_exposed(
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace.nodes,
            port_key=target_port,
        ):
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

        a_to_b = (
            default_port(
                node=node_a,
                spec=spec_a,
                workspace_nodes=workspace.nodes,
                direction="out",
            ),
            default_port(
                node=node_b,
                spec=spec_b,
                workspace_nodes=workspace.nodes,
                direction="in",
            ),
        )
        b_to_a = (
            default_port(
                node=node_b,
                spec=spec_b,
                workspace_nodes=workspace.nodes,
                direction="out",
            ),
            default_port(
                node=node_a,
                spec=spec_a,
                workspace_nodes=workspace.nodes,
                direction="in",
            ),
        )

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
        port = find_port(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
            port_key=key,
        )
        if port is None:
            return
        normalized_exposed = bool(exposed)
        current_exposed = bool(port.exposed)
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

    @pyqtSlot("QVariantList", float, float, result=bool)
    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool:
        if self._model is None:
            return False
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return False

        unique_node_ids: list[str] = []
        seen_node_ids: set[str] = set()
        for value in node_ids:
            node_id = str(value).strip()
            if not node_id or node_id in seen_node_ids or node_id not in workspace.nodes:
                continue
            seen_node_ids.add(node_id)
            unique_node_ids.append(node_id)
        if not unique_node_ids:
            return False

        delta_x = float(dx)
        delta_y = float(dy)
        if abs(delta_x) < 0.01 and abs(delta_y) < 0.01:
            return False

        history_group = nullcontext()
        if self._history is not None:
            history_group = self._history.grouped_action(
                self._workspace_id,
                ACTION_MOVE_NODE,
                workspace,
            )

        moved_any = False
        with history_group:
            for node_id in unique_node_ids:
                node = workspace.nodes.get(node_id)
                if node is None:
                    continue
                final_x = float(node.x) + delta_x
                final_y = float(node.y) + delta_y
                if float(node.x) == final_x and float(node.y) == final_y:
                    continue
                self._model.set_node_position(self._workspace_id, node_id, final_x, final_y)
                moved_any = True

        if not moved_any:
            return False
        self._rebuild_models()
        return True

    def align_selected_nodes(self, alignment: str, *, snap_to_grid: bool = False, grid_size: float = _SNAP_GRID_SIZE) -> bool:
        normalized_alignment = str(alignment).strip().lower()
        if normalized_alignment not in {"left", "right", "top", "bottom"}:
            return False
        workspace, selected = self._selected_layout_metrics()
        if workspace is None or len(selected) < 2:
            return False

        updates: dict[str, tuple[float, float]] = {}
        if normalized_alignment == "left":
            target_left = min(node.left for node in selected)
            for node in selected:
                updates[node.node_id] = (target_left, node.y)
        elif normalized_alignment == "right":
            target_right = max(node.right for node in selected)
            for node in selected:
                updates[node.node_id] = (target_right - node.width, node.y)
        elif normalized_alignment == "top":
            target_top = min(node.top for node in selected)
            for node in selected:
                updates[node.node_id] = (node.x, target_top)
        else:
            target_bottom = max(node.bottom for node in selected)
            for node in selected:
                updates[node.node_id] = (node.x, target_bottom - node.height)
        return self._apply_layout_updates(workspace, updates, snap_to_grid=snap_to_grid, grid_size=grid_size)

    def distribute_selected_nodes(
        self,
        orientation: str,
        *,
        snap_to_grid: bool = False,
        grid_size: float = _SNAP_GRID_SIZE,
    ) -> bool:
        normalized_orientation = str(orientation).strip().lower()
        if normalized_orientation not in {"horizontal", "vertical"}:
            return False
        workspace, selected = self._selected_layout_metrics()
        if workspace is None or len(selected) < 3:
            return False

        updates: dict[str, tuple[float, float]] = {}
        if normalized_orientation == "horizontal":
            ordered = sorted(selected, key=lambda node: (node.left, node.top, node.node_id))
            total_span = ordered[-1].right - ordered[0].left
            total_size = sum(node.width for node in ordered)
            gap = (total_span - total_size) / float(len(ordered) - 1)
            cursor = ordered[0].right + gap
            for node in ordered[1:-1]:
                updates[node.node_id] = (cursor, node.y)
                cursor += node.width + gap
        else:
            ordered = sorted(selected, key=lambda node: (node.top, node.left, node.node_id))
            total_span = ordered[-1].bottom - ordered[0].top
            total_size = sum(node.height for node in ordered)
            gap = (total_span - total_size) / float(len(ordered) - 1)
            cursor = ordered[0].bottom + gap
            for node in ordered[1:-1]:
                updates[node.node_id] = (node.x, cursor)
                cursor += node.height + gap
        return self._apply_layout_updates(workspace, updates, snap_to_grid=snap_to_grid, grid_size=grid_size)

    @pyqtSlot(result=bool)
    def duplicate_selected_subgraph(self) -> bool:
        fragment_payload = self.serialize_selected_subgraph_fragment()
        normalized_fragment = normalize_graph_fragment_payload(fragment_payload)
        if normalized_fragment is None:
            return False
        duplicated_node_ids = self._insert_fragment(
            normalized_fragment,
            action_type=ACTION_ADD_NODE,
            delta_x=_DUPLICATE_OFFSET_X,
            delta_y=_DUPLICATE_OFFSET_Y,
        )
        if not duplicated_node_ids:
            return False
        self._selected_node_ids = duplicated_node_ids
        self._rebuild_models()
        self.node_selected.emit(self.selected_node_id() or "")
        return True

    def serialize_selected_subgraph_fragment(self) -> dict[str, Any] | None:
        if self._model is None:
            return None
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return None
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if not selected_node_ids:
            return None
        return self._build_subgraph_fragment_payload(workspace, selected_node_ids)

    def paste_subgraph_fragment(self, fragment_payload: Any, center_x: float, center_y: float) -> bool:
        normalized_fragment = normalize_graph_fragment_payload(fragment_payload)
        if normalized_fragment is None:
            return False

        fragment_bounds = self._fragment_bounds(normalized_fragment["nodes"])
        if fragment_bounds is None:
            return False

        delta_x = float(center_x) - fragment_bounds.center().x()
        delta_y = float(center_y) - fragment_bounds.center().y()
        pasted_node_ids = self._insert_fragment(
            normalized_fragment,
            action_type=ACTION_ADD_NODE,
            delta_x=delta_x,
            delta_y=delta_y,
        )
        if not pasted_node_ids:
            return False

        self._selected_node_ids = pasted_node_ids
        self._rebuild_models()
        self.node_selected.emit(self.selected_node_id() or "")
        return True

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

    def _selected_node_ids_in_workspace(self, workspace: WorkspaceData) -> list[str]:
        selected_node_ids: list[str] = []
        selected_node_set: set[str] = set()
        for node_id in self._selected_node_ids:
            if node_id not in workspace.nodes or node_id in selected_node_set:
                continue
            if not is_node_in_scope(workspace, node_id, self._scope_path):
                continue
            selected_node_set.add(node_id)
            selected_node_ids.append(node_id)
        return selected_node_ids

    def _selected_layout_metrics(self) -> tuple[WorkspaceData | None, list[_LayoutNodeMetrics]]:
        if self._model is None or self._registry is None:
            return None, []
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return None, []
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if not selected_node_ids:
            return workspace, []
        layout_nodes: list[_LayoutNodeMetrics] = []
        for node_id in selected_node_ids:
            node = workspace.nodes.get(node_id)
            if node is None:
                continue
            spec = self._registry.get_spec(node.type_id)
            width, height = node_size(node, spec, workspace.nodes)
            layout_nodes.append(
                _LayoutNodeMetrics(
                    node_id=node_id,
                    x=float(node.x),
                    y=float(node.y),
                    width=float(width),
                    height=float(height),
                )
            )
        return workspace, layout_nodes

    @staticmethod
    def _snap_coordinate(value: float, grid_size: float) -> float:
        step = float(grid_size)
        if not math.isfinite(step) or step <= 0.0:
            step = _SNAP_GRID_SIZE
        target = float(value)
        if not math.isfinite(target):
            return 0.0
        return round(target / step) * step

    def _apply_layout_updates(
        self,
        workspace: WorkspaceData,
        updates: dict[str, tuple[float, float]],
        *,
        snap_to_grid: bool,
        grid_size: float,
    ) -> bool:
        if self._model is None or not updates:
            return False

        final_positions: dict[str, tuple[float, float]] = {}
        for node_id, (x_value, y_value) in updates.items():
            node = workspace.nodes.get(node_id)
            if node is None:
                continue
            final_x = float(x_value)
            final_y = float(y_value)
            if snap_to_grid:
                final_x = self._snap_coordinate(final_x, grid_size)
                final_y = self._snap_coordinate(final_y, grid_size)
            if float(node.x) == final_x and float(node.y) == final_y:
                continue
            final_positions[node_id] = (final_x, final_y)

        if not final_positions:
            return False

        history_group = nullcontext()
        if self._history is not None:
            history_group = self._history.grouped_action(
                self._workspace_id,
                ACTION_MOVE_NODE,
                workspace,
            )

        with history_group:
            for node_id, (final_x, final_y) in final_positions.items():
                self._model.set_node_position(self._workspace_id, node_id, final_x, final_y)
        self._rebuild_models()
        return True

    def _build_subgraph_fragment_payload(
        self,
        workspace: WorkspaceData,
        node_ids: list[str],
    ) -> dict[str, Any] | None:
        selected_node_set = set(node_ids)
        nodes_payload: list[dict[str, Any]] = []
        for node_id in node_ids:
            node = workspace.nodes.get(node_id)
            if node is None:
                continue
            nodes_payload.append(
                {
                    "ref_id": node.node_id,
                    "type_id": node.type_id,
                    "title": node.title,
                    "x": float(node.x),
                    "y": float(node.y),
                    "collapsed": bool(node.collapsed),
                    "properties": dict(node.properties),
                    "exposed_ports": dict(node.exposed_ports),
                    "parent_node_id": node.parent_node_id,
                }
            )
        if not nodes_payload:
            return None

        edges_payload: list[dict[str, str]] = []
        for edge in workspace.edges.values():
            if edge.source_node_id not in selected_node_set or edge.target_node_id not in selected_node_set:
                continue
            edges_payload.append(
                {
                    "source_ref_id": edge.source_node_id,
                    "source_port_key": edge.source_port_key,
                    "target_ref_id": edge.target_node_id,
                    "target_port_key": edge.target_port_key,
                }
            )
        return build_graph_fragment_payload(nodes=nodes_payload, edges=edges_payload)

    def _fragment_bounds(self, nodes_payload: list[dict[str, Any]]) -> QRectF | None:
        if self._registry is None:
            return None
        fragment_nodes: dict[str, NodeInstance] = {}
        node_specs: dict[str, NodeTypeSpec] = {}
        for node_payload in nodes_payload:
            ref_id = str(node_payload.get("ref_id", "")).strip()
            type_id = str(node_payload.get("type_id", "")).strip()
            if not ref_id or not type_id:
                return None
            try:
                node_specs[ref_id] = self._registry.get_spec(type_id)
            except KeyError:
                return None
            node = NodeInstance(
                node_id=ref_id,
                type_id=type_id,
                title=str(node_payload.get("title", "")),
                x=float(node_payload.get("x", 0.0)),
                y=float(node_payload.get("y", 0.0)),
                collapsed=bool(node_payload.get("collapsed", False)),
                properties=dict(node_payload.get("properties", {})),
                exposed_ports=dict(node_payload.get("exposed_ports", {})),
                parent_node_id=node_payload.get("parent_node_id"),
            )
            fragment_nodes[ref_id] = node

        bounds: QRectF | None = None
        for node_id, node in fragment_nodes.items():
            spec = node_specs[node_id]
            width, height = node_size(node, spec, fragment_nodes)
            node_rect = QRectF(float(node.x), float(node.y), float(width), float(height))
            if bounds is None:
                bounds = QRectF(node_rect)
            else:
                bounds = bounds.united(node_rect)
        return bounds

    def _fragment_types_and_ports_are_valid(self, fragment_payload: dict[str, Any]) -> bool:
        if self._registry is None:
            return False

        node_specs: dict[str, NodeTypeSpec] = {}
        fragment_nodes: dict[str, NodeInstance] = {}
        for node_payload in fragment_payload["nodes"]:
            ref_id = str(node_payload.get("ref_id", "")).strip()
            type_id = str(node_payload.get("type_id", "")).strip()
            if not ref_id or not type_id:
                return False
            try:
                node_specs[ref_id] = self._registry.get_spec(type_id)
            except KeyError:
                return False
            fragment_nodes[ref_id] = NodeInstance(
                node_id=ref_id,
                type_id=type_id,
                title=str(node_payload.get("title", "")),
                x=float(node_payload.get("x", 0.0)),
                y=float(node_payload.get("y", 0.0)),
                collapsed=bool(node_payload.get("collapsed", False)),
                properties=dict(node_payload.get("properties", {})),
                exposed_ports=dict(node_payload.get("exposed_ports", {})),
                parent_node_id=node_payload.get("parent_node_id"),
            )

        for edge_payload in fragment_payload["edges"]:
            source_ref_id = str(edge_payload.get("source_ref_id", "")).strip()
            target_ref_id = str(edge_payload.get("target_ref_id", "")).strip()
            source_port_key = str(edge_payload.get("source_port_key", "")).strip()
            target_port_key = str(edge_payload.get("target_port_key", "")).strip()
            source_node = fragment_nodes.get(source_ref_id)
            target_node = fragment_nodes.get(target_ref_id)
            source_spec = node_specs.get(source_ref_id)
            target_spec = node_specs.get(target_ref_id)
            if source_node is None or target_node is None or source_spec is None or target_spec is None:
                return False
            source_port = find_port(
                node=source_node,
                spec=source_spec,
                workspace_nodes=fragment_nodes,
                port_key=source_port_key,
            )
            target_port = find_port(
                node=target_node,
                spec=target_spec,
                workspace_nodes=fragment_nodes,
                port_key=target_port_key,
            )
            if source_port is None or target_port is None:
                return False
            if source_port.direction != "out" or target_port.direction != "in":
                return False
        return True

    def _insert_fragment(
        self,
        fragment_payload: dict[str, Any],
        *,
        action_type: str,
        delta_x: float,
        delta_y: float,
    ) -> list[str]:
        if self._model is None:
            return []
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return []
        if not self._fragment_types_and_ports_are_valid(fragment_payload):
            return []

        node_id_map: dict[str, str] = {}
        inserted_node_ids: list[str] = []

        history_group = nullcontext()
        if self._history is not None:
            history_group = self._history.grouped_action(
                self._workspace_id,
                action_type,
                workspace,
            )

        with history_group:
            for node_payload in fragment_payload["nodes"]:
                source_node_id = str(node_payload["ref_id"]).strip()
                created = self._model.add_node(
                    self._workspace_id,
                    type_id=str(node_payload["type_id"]),
                    title=str(node_payload["title"]),
                    x=float(node_payload["x"]) + float(delta_x),
                    y=float(node_payload["y"]) + float(delta_y),
                    properties=dict(node_payload["properties"]),
                    exposed_ports=dict(node_payload["exposed_ports"]),
                )
                created.collapsed = bool(node_payload["collapsed"])
                node_id_map[source_node_id] = created.node_id
                inserted_node_ids.append(created.node_id)

            for node_payload in fragment_payload["nodes"]:
                source_node_id = str(node_payload["ref_id"]).strip()
                inserted_node_id = node_id_map.get(source_node_id)
                if not inserted_node_id:
                    continue
                inserted_node = workspace.nodes.get(inserted_node_id)
                if inserted_node is None:
                    continue
                source_parent_id = node_payload.get("parent_node_id")
                if source_parent_id is None:
                    inserted_node.parent_node_id = None
                    continue
                normalized_parent_id = str(source_parent_id).strip()
                if not normalized_parent_id:
                    inserted_node.parent_node_id = None
                elif normalized_parent_id in node_id_map:
                    inserted_node.parent_node_id = node_id_map[normalized_parent_id]
                elif normalized_parent_id in workspace.nodes:
                    inserted_node.parent_node_id = normalized_parent_id
                else:
                    inserted_node.parent_node_id = None

            for edge_payload in fragment_payload["edges"]:
                source_node_id = node_id_map.get(str(edge_payload["source_ref_id"]).strip())
                target_node_id = node_id_map.get(str(edge_payload["target_ref_id"]).strip())
                if not source_node_id or not target_node_id:
                    continue
                try:
                    self._model.add_edge(
                        self._workspace_id,
                        source_node_id=source_node_id,
                        source_port_key=str(edge_payload["source_port_key"]),
                        target_node_id=target_node_id,
                        target_port_key=str(edge_payload["target_port_key"]),
                    )
                except ValueError:
                    continue
        return inserted_node_ids

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
            self._minimap_nodes_payload = []
            self._edges_payload = []
            self.nodes_changed.emit()
            self.edges_changed.emit()
            return

        workspace = self._model.project.workspaces[self._workspace_id]
        visible_node_ids = scope_node_ids(workspace, self._scope_path)
        visible_nodes = {node_id: workspace.nodes[node_id] for node_id in visible_node_ids}
        workspace_edges = scope_edges(workspace, self._scope_path)
        port_connection_counts: dict[tuple[str, str], int] = {}
        for edge in workspace_edges:
            source_key = (edge.source_node_id, edge.source_port_key)
            target_key = (edge.target_node_id, edge.target_port_key)
            port_connection_counts[source_key] = port_connection_counts.get(source_key, 0) + 1
            port_connection_counts[target_key] = port_connection_counts.get(target_key, 0) + 1

        nodes_payload: list[dict[str, Any]] = []
        minimap_nodes_payload: list[dict[str, Any]] = []
        node_specs: dict[str, NodeTypeSpec] = {}

        for node_id in visible_node_ids:
            node = workspace.nodes[node_id]
            spec = self._registry.get_spec(node.type_id)
            node_specs[node_id] = spec
            width, height = node_size(node, spec, workspace.nodes)
            resolved_ports = effective_ports(
                node=node,
                spec=spec,
                workspace_nodes=workspace.nodes,
            )
            ports_payload: list[dict[str, Any]] = []
            for port in resolved_ports:
                if not port.exposed:
                    continue
                connection_count = port_connection_counts.get((node.node_id, port.key), 0)
                ports_payload.append(
                    {
                        "key": port.key,
                        "label": port.label,
                        "direction": port.direction,
                        "kind": port.kind,
                        "data_type": port.data_type,
                        "exposed": bool(port.exposed),
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
                    "can_enter_scope": node.type_id == "core.subnode",
                    "ports": ports_payload,
                }
            )
            minimap_nodes_payload.append(
                {
                    "node_id": node.node_id,
                    "x": float(node.x),
                    "y": float(node.y),
                    "width": float(width),
                    "height": float(height),
                    "selected": node.node_id in self._selected_node_ids,
                }
            )

        edges_payload = build_edge_payload(
            workspace_edges=workspace_edges,
            workspace_nodes=workspace.nodes,
            node_specs=node_specs,
        )

        self._nodes_payload = nodes_payload
        self._minimap_nodes_payload = minimap_nodes_payload
        self._edges_payload = edges_payload
        self.nodes_changed.emit()
        self.edges_changed.emit()


__all__ = ["GraphSceneBridge"]
