from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QPointF, QRectF

from ea_node_editor.graph.hierarchy import (
    ScopePath,
    breadcrumb_scope_path,
    is_node_in_scope,
    node_scope_path,
    normalize_scope_path,
    scope_node_ids,
    subnode_scope_path,
)
from ea_node_editor.graph.model import NodeInstance, ViewState, WorkspaceData
from ea_node_editor.nodes.builtins.subnode import is_subnode_shell_type
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui_qml.edge_routing import node_size, port_scene_pos

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

_MINIMAP_EMPTY_BOUNDS = QRectF(-1600.0, -900.0, 3200.0, 1800.0)
_MINIMAP_PADDING = 220.0
_MINIMAP_MIN_WIDTH = 3200.0
_MINIMAP_MIN_HEIGHT = 1800.0


@dataclass(slots=True)
class _SelectedNodeProxy:
    node: NodeInstance


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


class GraphSceneScopeSelection:
    def __init__(self, bridge: GraphSceneBridge) -> None:
        self._bridge = bridge
        self.workspace_id = ""
        self.scope_path: ScopePath = ()
        self.selected_node_ids: list[str] = []
        self.selected_node_lookup: dict[str, bool] = {}

    def workspace_or_none(self) -> WorkspaceData | None:
        if self._bridge._model is None or not self.workspace_id:
            return None
        return self._bridge._model.project.workspaces.get(self.workspace_id)

    @staticmethod
    def active_view_state(workspace: WorkspaceData) -> ViewState | None:
        workspace.ensure_default_view()
        if not workspace.active_view_id:
            return None
        return workspace.views.get(workspace.active_view_id)

    def normalized_selected_node_ids(
        self,
        workspace: WorkspaceData | None,
        node_ids: list[str],
    ) -> list[str]:
        if workspace is None:
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for node_id in node_ids:
            normalized_node_id = str(node_id).strip()
            if not normalized_node_id or normalized_node_id in seen:
                continue
            if normalized_node_id not in workspace.nodes:
                continue
            if not is_node_in_scope(workspace, normalized_node_id, self.scope_path):
                continue
            seen.add(normalized_node_id)
            normalized.append(normalized_node_id)
        return normalized

    @staticmethod
    def selected_node_lookup_for_ids(node_ids: list[str]) -> dict[str, bool]:
        return {node_id: True for node_id in node_ids}

    def set_selected_node_ids(
        self,
        node_ids: list[str],
        *,
        workspace: WorkspaceData | None = None,
        emit_signals: bool = True,
    ) -> bool:
        resolved_workspace = workspace if workspace is not None else self.workspace_or_none()
        normalized_node_ids = self.normalized_selected_node_ids(resolved_workspace, node_ids)
        selected_lookup = self.selected_node_lookup_for_ids(normalized_node_ids)
        selection_changed = normalized_node_ids != self.selected_node_ids
        lookup_changed = selected_lookup != self.selected_node_lookup
        if not selection_changed and not lookup_changed:
            return False
        self.selected_node_ids = normalized_node_ids
        self.selected_node_lookup = selected_lookup
        if emit_signals:
            self._bridge.selection_changed.emit()
            self._bridge.node_selected.emit(self.selected_node_id() or "")
        return True

    def apply_scope_path(
        self,
        workspace: WorkspaceData,
        scope_path: ScopePath,
        *,
        persist: bool = True,
        emit_scope_changed: bool = True,
        emit_selection_changed: bool = True,
    ) -> bool:
        normalized_scope = normalize_scope_path(workspace, scope_path)
        changed = normalized_scope != self.scope_path
        self.scope_path = normalized_scope
        if persist:
            view_state = self.active_view_state(workspace)
            if view_state is not None:
                view_state.scope_path = list(normalized_scope)
        selection_changed = self.set_selected_node_ids(
            self.selected_node_ids,
            workspace=workspace,
            emit_signals=emit_selection_changed,
        )
        if changed:
            self._bridge._rebuild_models()
            if emit_scope_changed:
                self._bridge.scope_changed.emit()
        elif selection_changed and emit_selection_changed:
            # Selection no longer lives in the node payload, so no model rebuild is needed here.
            pass
        return changed

    def restore_scope_path_from_view(self, workspace: WorkspaceData) -> None:
        view_state = self.active_view_state(workspace)
        scope_path: ScopePath = ()
        if view_state is not None:
            scope_path = normalize_scope_path(workspace, view_state.scope_path)
            if list(scope_path) != view_state.scope_path:
                view_state.scope_path = list(scope_path)
        self.scope_path = scope_path

    def sync_scope_with_active_view(self) -> bool:
        workspace = self.workspace_or_none()
        if workspace is None:
            return False
        view_state = self.active_view_state(workspace)
        target_scope: ScopePath = ()
        if view_state is not None:
            target_scope = normalize_scope_path(workspace, view_state.scope_path)
        return self.apply_scope_path(workspace, target_scope)

    def open_subnode_scope(self, node_id: str) -> bool:
        workspace = self.workspace_or_none()
        if workspace is None:
            return False
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return False
        node = workspace.nodes.get(normalized_node_id)
        if node is None or not is_subnode_shell_type(node.type_id):
            return False
        if not is_node_in_scope(workspace, normalized_node_id, self.scope_path):
            return False
        return self.apply_scope_path(workspace, subnode_scope_path(workspace, normalized_node_id))

    def open_scope_for_node(self, node_id: str) -> bool:
        workspace = self.workspace_or_none()
        if workspace is None:
            return False
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id or normalized_node_id not in workspace.nodes:
            return False
        return self.apply_scope_path(workspace, node_scope_path(workspace, normalized_node_id))

    def navigate_scope_parent(self) -> bool:
        workspace = self.workspace_or_none()
        if workspace is None or not self.scope_path:
            return False
        return self.apply_scope_path(workspace, self.scope_path[:-1])

    def navigate_scope_root(self) -> bool:
        workspace = self.workspace_or_none()
        if workspace is None or not self.scope_path:
            return False
        return self.apply_scope_path(workspace, ())

    def navigate_scope_to(self, node_id: str) -> bool:
        workspace = self.workspace_or_none()
        if workspace is None:
            return False
        next_scope = breadcrumb_scope_path(workspace, self.scope_path, node_id)
        return self.apply_scope_path(workspace, next_scope)

    def set_workspace(self, workspace_id: str) -> None:
        self.workspace_id = str(workspace_id)
        workspace = self._bridge._model.project.workspaces[self.workspace_id]
        self.restore_scope_path_from_view(workspace)
        self.set_selected_node_ids([], workspace=workspace)
        self._bridge._rebuild_models()
        self._bridge.workspace_changed.emit(self.workspace_id)
        self._bridge.scope_changed.emit()

    def refresh_workspace_from_model(self, workspace_id: str) -> None:
        if self._bridge._model is None:
            return
        normalized_workspace_id = str(workspace_id).strip()
        if not normalized_workspace_id or normalized_workspace_id != self.workspace_id:
            return
        workspace = self._bridge._model.project.workspaces.get(self.workspace_id)
        if workspace is None:
            return
        normalized_scope = normalize_scope_path(workspace, self.scope_path)
        if normalized_scope != self.scope_path:
            self.apply_scope_path(
                workspace,
                normalized_scope,
                persist=True,
                emit_scope_changed=False,
            )
            self._bridge.scope_changed.emit()
        else:
            self.set_selected_node_ids(self.selected_node_ids, workspace=workspace)
            self._bridge._rebuild_models()

    def selected_node_id(self) -> str | None:
        workspace = self.workspace_or_none()
        if workspace is None:
            return None
        for node_id in reversed(self.selected_node_ids):
            if node_id in workspace.nodes and is_node_in_scope(workspace, node_id, self.scope_path):
                return node_id
        return None

    def selected_items(self) -> list[_SelectedNodeProxy]:
        workspace = self._bridge.current_workspace()
        selected: list[_SelectedNodeProxy] = []
        for node_id in self.selected_node_ids:
            node = workspace.nodes.get(node_id)
            if node is not None and is_node_in_scope(workspace, node_id, self.scope_path):
                selected.append(_SelectedNodeProxy(node=node))
        return selected

    def workspace_scene_bounds(self) -> QRectF | None:
        workspace = self.workspace_or_none()
        if workspace is None:
            return None
        visible_node_ids = scope_node_ids(workspace, self.scope_path)
        if not visible_node_ids:
            return None
        return self.bounds_for_node_ids(visible_node_ids)

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

    @staticmethod
    def rect_payload(rect: QRectF) -> dict[str, float]:
        normalized = QRectF(rect).normalized()
        return {
            "x": float(normalized.x()),
            "y": float(normalized.y()),
            "width": float(max(0.0, normalized.width())),
            "height": float(max(0.0, normalized.height())),
        }

    def workspace_scene_bounds_map(self) -> dict[str, float]:
        return self.rect_payload(self.workspace_scene_bounds_with_fallback())

    def selection_bounds(self) -> QRectF | None:
        workspace = self.workspace_or_none()
        if workspace is None:
            return None
        selected_node_ids = self.selected_node_ids_in_workspace(workspace)
        if not selected_node_ids:
            return None
        return self.bounds_for_node_ids(selected_node_ids)

    def clear_selection(self) -> None:
        self.set_selected_node_ids([])

    def select_node(self, node_id: str, additive: bool = False) -> None:
        if not node_id:
            self.clear_selection()
            return
        workspace = self.workspace_or_none()
        if workspace is None:
            return
        if self._bridge._node(node_id) is None:
            return
        if not is_node_in_scope(workspace, node_id, self.scope_path):
            return
        if additive:
            if node_id in self.selected_node_ids:
                next_selected = [value for value in self.selected_node_ids if value != node_id]
            else:
                next_selected = [*self.selected_node_ids, node_id]
        else:
            next_selected = [node_id]
        self.set_selected_node_ids(next_selected, workspace=workspace)

    def select_nodes_in_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        additive: bool = False,
    ) -> None:
        if self._bridge._model is None or self._bridge._registry is None or not self.workspace_id:
            return

        workspace = self._bridge.current_workspace()
        visible_node_ids = set(scope_node_ids(workspace, self.scope_path))
        min_x = min(float(x1), float(x2))
        max_x = max(float(x1), float(x2))
        min_y = min(float(y1), float(y2))
        max_y = max(float(y1), float(y2))

        hit_ids: list[str] = []
        for node_id, node in workspace.nodes.items():
            if node_id not in visible_node_ids:
                continue
            spec = self._bridge._registry.get_spec(node.type_id)
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
                for node_id in self.selected_node_ids
                if node_id in workspace.nodes and node_id in visible_node_ids
            ]
            for node_id in hit_ids:
                if node_id not in next_selected:
                    next_selected.append(node_id)
        else:
            next_selected = hit_ids

        if next_selected == self.selected_node_ids:
            return

        self.set_selected_node_ids(next_selected, workspace=workspace)

    def node_item(self, node_id: str) -> _NodeItemProxy | None:
        if self._bridge._model is None:
            return None
        workspace = self._bridge._model.project.workspaces.get(self.workspace_id)
        if workspace is None or self._bridge._registry is None:
            return None
        node = workspace.nodes.get(node_id)
        if node is None:
            return None
        if not is_node_in_scope(workspace, node_id, self.scope_path):
            return None
        spec = self._bridge._registry.get_spec(node.type_id)
        return _NodeItemProxy(node=node, spec=spec, workspace_nodes=workspace.nodes)

    def node_bounds(self, node_id: str) -> QRectF | None:
        item = self.node_item(node_id)
        if item is None:
            return None
        return QRectF(item.sceneBoundingRect())

    def bounds_for_node_ids(self, node_ids: list[str]) -> QRectF | None:
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

    def selected_node_ids_in_workspace(self, workspace: WorkspaceData) -> list[str]:
        selected_node_ids: list[str] = []
        selected_node_set: set[str] = set()
        for node_id in self.selected_node_ids:
            if node_id not in workspace.nodes or node_id in selected_node_set:
                continue
            if not is_node_in_scope(workspace, node_id, self.scope_path):
                continue
            selected_node_set.add(node_id)
            selected_node_ids.append(node_id)
        return selected_node_ids


__all__ = [
    "GraphSceneScopeSelection",
    "_NodeItemProxy",
    "_SelectedNodeProxy",
]
