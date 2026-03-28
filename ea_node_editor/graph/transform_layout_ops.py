from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Mapping, Sequence

from ea_node_editor.graph.model import NodeInstance, WorkspaceData
from ea_node_editor.nodes.types import NodeTypeSpec

_DEFAULT_LAYOUT_GRID_SIZE = 20.0


@dataclass(slots=True, frozen=True)
class LayoutNodeBounds:
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


def collect_layout_node_bounds(
    *,
    workspace: WorkspaceData,
    node_ids: Sequence[str],
    spec_lookup: Callable[[str], NodeTypeSpec],
    size_resolver: Callable[[NodeInstance, NodeTypeSpec, Mapping[str, NodeInstance]], tuple[float, float]],
) -> list[LayoutNodeBounds]:
    layout_nodes: list[LayoutNodeBounds] = []
    for node_id in node_ids:
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        spec = spec_lookup(node.type_id)
        width, height = size_resolver(node, spec, workspace.nodes)
        layout_nodes.append(
            LayoutNodeBounds(
                node_id=node_id,
                x=float(node.x),
                y=float(node.y),
                width=float(width),
                height=float(height),
            )
        )
    return layout_nodes


def snap_coordinate(value: float, grid_size: float, *, default_step: float = _DEFAULT_LAYOUT_GRID_SIZE) -> float:
    step = float(grid_size)
    if not math.isfinite(step) or step <= 0.0:
        step = float(default_step)
    target = float(value)
    if not math.isfinite(target):
        return 0.0
    return round(target / step) * step


def build_alignment_position_updates(
    *,
    layout_nodes: Sequence[LayoutNodeBounds],
    alignment: str,
) -> dict[str, tuple[float, float]]:
    normalized_alignment = str(alignment).strip().lower()
    if normalized_alignment not in {"left", "right", "top", "bottom"}:
        return {}
    if len(layout_nodes) < 2:
        return {}

    updates: dict[str, tuple[float, float]] = {}
    if normalized_alignment == "left":
        target_left = min(node.left for node in layout_nodes)
        for node in layout_nodes:
            updates[node.node_id] = (target_left, node.y)
    elif normalized_alignment == "right":
        target_right = max(node.right for node in layout_nodes)
        for node in layout_nodes:
            updates[node.node_id] = (target_right - node.width, node.y)
    elif normalized_alignment == "top":
        target_top = min(node.top for node in layout_nodes)
        for node in layout_nodes:
            updates[node.node_id] = (node.x, target_top)
    else:
        target_bottom = max(node.bottom for node in layout_nodes)
        for node in layout_nodes:
            updates[node.node_id] = (node.x, target_bottom - node.height)
    return updates


def build_distribution_position_updates(
    *,
    layout_nodes: Sequence[LayoutNodeBounds],
    orientation: str,
) -> dict[str, tuple[float, float]]:
    normalized_orientation = str(orientation).strip().lower()
    if normalized_orientation not in {"horizontal", "vertical"}:
        return {}
    if len(layout_nodes) < 3:
        return {}

    updates: dict[str, tuple[float, float]] = {}
    if normalized_orientation == "horizontal":
        ordered = sorted(layout_nodes, key=lambda node: (node.left, node.top, node.node_id))
        total_span = ordered[-1].right - ordered[0].left
        total_size = sum(node.width for node in ordered)
        gap = (total_span - total_size) / float(len(ordered) - 1)
        cursor = ordered[0].right + gap
        for node in ordered[1:-1]:
            updates[node.node_id] = (cursor, node.y)
            cursor += node.width + gap
    else:
        ordered = sorted(layout_nodes, key=lambda node: (node.top, node.left, node.node_id))
        total_span = ordered[-1].bottom - ordered[0].top
        total_size = sum(node.height for node in ordered)
        gap = (total_span - total_size) / float(len(ordered) - 1)
        cursor = ordered[0].bottom + gap
        for node in ordered[1:-1]:
            updates[node.node_id] = (node.x, cursor)
            cursor += node.height + gap
    return updates


def normalize_layout_position_updates(
    *,
    workspace: WorkspaceData,
    updates: Mapping[str, tuple[float, float]],
    snap_to_grid: bool,
    grid_size: float,
    default_grid_size: float = _DEFAULT_LAYOUT_GRID_SIZE,
) -> dict[str, tuple[float, float]]:
    final_positions: dict[str, tuple[float, float]] = {}
    for node_id, (x_value, y_value) in updates.items():
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        final_x = float(x_value)
        final_y = float(y_value)
        if snap_to_grid:
            final_x = snap_coordinate(final_x, grid_size, default_step=default_grid_size)
            final_y = snap_coordinate(final_y, grid_size, default_step=default_grid_size)
        if float(node.x) == final_x and float(node.y) == final_y:
            continue
        final_positions[node_id] = (final_x, final_y)
    return final_positions


__all__ = [
    "LayoutNodeBounds",
    "build_alignment_position_updates",
    "build_distribution_position_updates",
    "collect_layout_node_bounds",
    "normalize_layout_position_updates",
    "snap_coordinate",
]
