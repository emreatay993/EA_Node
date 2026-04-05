from __future__ import annotations

from typing import Any

from ea_node_editor.graph.hierarchy import is_node_in_scope
from ea_node_editor.graph.transforms import (
    build_alignment_position_updates,
    build_distribution_position_updates,
)
from ea_node_editor.ui.shell.runtime_history import ACTION_MOVE_NODE, ACTION_RESIZE_NODE
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics

SNAP_GRID_SIZE = 20.0


def move_node(self, node_id: str, x: float, y: float) -> None:
    model = self._scene_context.model
    if model is None:
        return
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return
    if not is_node_in_scope(workspace, node_id, self._scene_context.scope_path):
        return
    node = self._node(node_id)
    if node is None:
        return
    final_x = float(x)
    final_y = float(y)
    if float(node.x) == final_x and float(node.y) == final_y:
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().set_node_position(node_id, final_x, final_y)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_MOVE_NODE, history_before)


def resize_node(self, node_id: str, width: float, height: float) -> None:
    node = self._node(node_id)
    if node is None:
        return
    self.set_node_geometry(node_id, float(node.x), float(node.y), width, height)


def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
    model = self._scene_context.model
    registry = self._scene_context.registry
    if model is None:
        return
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return
    node = self._node(node_id)
    if node is None:
        return
    if not is_node_in_scope(workspace, node_id, self._scene_context.scope_path):
        return
    spec = registry.get_spec(node.type_id) if registry is not None else None
    min_width = 0.0
    min_height = 0.0
    if spec is not None:
        metrics = node_surface_metrics(
            node,
            spec,
            workspace.nodes,
            show_port_labels=self._scene_context.graphics_show_port_labels,
        )
        min_width = float(metrics.min_width)
        min_height = float(metrics.min_height)
    final_x = float(x)
    final_y = float(y)
    final_w = max(min_width, float(width))
    final_h = max(min_height, float(height))
    if (
        float(node.x) == final_x
        and float(node.y) == final_y
        and node.custom_width == final_w
        and node.custom_height == final_h
    ):
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().set_node_geometry(node_id, final_x, final_y, final_w, final_h)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_RESIZE_NODE, history_before)


def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool:
    model = self._scene_context.model
    if model is None:
        return False
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return False

    unique_node_ids: list[str] = []
    seen_node_ids: set[str] = set()
    for value in node_ids:
        node_id = str(value).strip()
        if not node_id or node_id in seen_node_ids or node_id not in workspace.nodes:
            continue
        if not is_node_in_scope(workspace, node_id, self._scene_context.scope_path):
            continue
        seen_node_ids.add(node_id)
        unique_node_ids.append(node_id)
    if not unique_node_ids:
        return False

    delta_x = float(dx)
    delta_y = float(dy)
    if abs(delta_x) < 0.01 and abs(delta_y) < 0.01:
        return False

    history_group = self._scene_context.grouped_history_action(ACTION_MOVE_NODE, workspace)
    moved_any = False
    mutations = self._mutation_boundary()
    with history_group:
        for node_id in unique_node_ids:
            node = workspace.nodes.get(node_id)
            if node is None:
                continue
            final_x = float(node.x) + delta_x
            final_y = float(node.y) + delta_y
            if float(node.x) == final_x and float(node.y) == final_y:
                continue
            mutations.set_node_position(node_id, final_x, final_y)
            moved_any = True

    if not moved_any:
        return False
    self._scene_context.rebuild_models()
    return True


def align_selected_nodes(
    self,
    alignment: str,
    *,
    snap_to_grid: bool = False,
    grid_size: float = SNAP_GRID_SIZE,
) -> bool:
    workspace, selected = self._selected_layout_metrics()
    if workspace is None:
        return False
    updates = build_alignment_position_updates(layout_nodes=selected, alignment=alignment)
    return self._apply_layout_updates(
        workspace,
        updates,
        snap_to_grid=snap_to_grid,
        grid_size=grid_size,
    )


def distribute_selected_nodes(
    self,
    orientation: str,
    *,
    snap_to_grid: bool = False,
    grid_size: float = SNAP_GRID_SIZE,
) -> bool:
    workspace, selected = self._selected_layout_metrics()
    if workspace is None:
        return False
    updates = build_distribution_position_updates(layout_nodes=selected, orientation=orientation)
    return self._apply_layout_updates(
        workspace,
        updates,
        snap_to_grid=snap_to_grid,
        grid_size=grid_size,
    )


__all__ = [
    "SNAP_GRID_SIZE",
    "align_selected_nodes",
    "distribute_selected_nodes",
    "move_node",
    "move_nodes_by_delta",
    "resize_node",
    "set_node_geometry",
]
