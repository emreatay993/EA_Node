from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Collection, Mapping, Sequence

from ea_node_editor.graph.workspace_state import WorkspaceData

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

    @property
    def center_x(self) -> float:
        return self.x + (self.width * 0.5)

    @property
    def center_y(self) -> float:
        return self.y + (self.height * 0.5)

    def translated(self, dx: float, dy: float) -> "LayoutNodeBounds":
        return LayoutNodeBounds(
            node_id=self.node_id,
            x=self.x + float(dx),
            y=self.y + float(dy),
            width=self.width,
            height=self.height,
        )

    def inflated(self, amount: float) -> "LayoutNodeBounds":
        normalized = max(0.0, float(amount))
        return LayoutNodeBounds(
            node_id=self.node_id,
            x=self.x - normalized,
            y=self.y - normalized,
            width=self.width + (normalized * 2.0),
            height=self.height + (normalized * 2.0),
        )


@dataclass(slots=True, frozen=True)
class PortAlignmentConstraint:
    source_node_id: str
    target_node_id: str
    axis: str
    source_anchor: float
    target_anchor: float


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
    if normalized_alignment not in {"left", "right", "top", "bottom", "center_x", "center_y"}:
        return {}
    if len(layout_nodes) < 2:
        return {}

    updates: dict[str, tuple[float, float]] = {}
    if normalized_alignment == "center_x":
        # Shared horizontal center of the selection bounds: stacks the nodes into a centered column.
        target_center_x = (min(node.left for node in layout_nodes) + max(node.right for node in layout_nodes)) * 0.5
        for node in layout_nodes:
            updates[node.node_id] = (target_center_x - (node.width * 0.5), node.y)
    elif normalized_alignment == "center_y":
        # Shared vertical center of the selection bounds: a row whose side ports line up.
        target_center_y = (min(node.top for node in layout_nodes) + max(node.bottom for node in layout_nodes)) * 0.5
        for node in layout_nodes:
            updates[node.node_id] = (node.x, target_center_y - (node.height * 0.5))
    elif normalized_alignment == "left":
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


def build_straighten_connection_position_updates(
    *,
    workspace: WorkspaceData,
    constraints: Sequence[PortAlignmentConstraint],
    tolerance: float = 0.01,
) -> dict[str, tuple[float, float]]:
    offsets = build_port_alignment_offsets(
        node_ids=set(workspace.nodes),
        constraints=constraints,
        tolerance=tolerance,
    )
    updates: dict[str, tuple[float, float]] = {}
    for node_id, (dx, dy) in offsets.items():
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        updates[node_id] = (float(node.x) + dx, float(node.y) + dy)
    return updates


def build_port_alignment_offsets(
    *,
    node_ids: Collection[str],
    constraints: Sequence[PortAlignmentConstraint],
    tolerance: float = 0.01,
) -> dict[str, tuple[float, float]]:
    """Return the ``(dx, dy)`` each node must move so constrained port anchors line up.

    Each connected component of constraints is solved per axis and shifted by its median so
    the nodes move as little as possible; a component whose constraints conflict is left alone.
    """
    known_node_ids = node_ids if isinstance(node_ids, (set, frozenset)) else set(node_ids)
    offsets: dict[str, list[float]] = {}
    for axis_index, axis in enumerate(("x", "y")):
        axis_offsets = _straighten_axis_offsets(
            known_node_ids=known_node_ids,
            constraints=constraints,
            axis=axis,
            tolerance=tolerance,
        )
        for node_id, delta in axis_offsets.items():
            offsets.setdefault(node_id, [0.0, 0.0])[axis_index] = delta
    return {node_id: (delta[0], delta[1]) for node_id, delta in offsets.items()}


def _straighten_axis_offsets(
    *,
    known_node_ids: Collection[str],
    constraints: Sequence[PortAlignmentConstraint],
    axis: str,
    tolerance: float,
) -> dict[str, float]:
    adjacency: dict[str, list[tuple[str, float]]] = {}
    for constraint in constraints:
        if str(constraint.axis).strip().lower() != axis:
            continue
        source_id = str(constraint.source_node_id).strip()
        target_id = str(constraint.target_node_id).strip()
        if not source_id or not target_id or source_id == target_id:
            continue
        if source_id not in known_node_ids or target_id not in known_node_ids:
            continue
        required_delta = float(constraint.source_anchor) - float(constraint.target_anchor)
        if not math.isfinite(required_delta):
            continue
        adjacency.setdefault(source_id, []).append((target_id, required_delta))
        adjacency.setdefault(target_id, []).append((source_id, -required_delta))

    offsets: dict[str, float] = {}
    visited: set[str] = set()
    for root_id in sorted(adjacency):
        if root_id in visited:
            continue
        relative, conflicted = _solve_straighten_axis_component(
            adjacency,
            root_id,
            tolerance=tolerance,
        )
        visited.update(relative)
        if conflicted:
            continue
        shift = -_median(tuple(relative.values()))
        for node_id, value in relative.items():
            delta = value + shift
            if abs(delta) > tolerance:
                offsets[node_id] = delta
    return offsets


def _solve_straighten_axis_component(
    adjacency: Mapping[str, Sequence[tuple[str, float]]],
    root_id: str,
    *,
    tolerance: float,
) -> tuple[dict[str, float], bool]:
    assigned = {root_id: 0.0}
    stack = [root_id]
    conflicted = False
    while stack:
        node_id = stack.pop()
        base = assigned[node_id]
        for neighbor_id, delta in adjacency.get(node_id, ()):
            target = base + delta
            existing = assigned.get(neighbor_id)
            if existing is None:
                assigned[neighbor_id] = target
                stack.append(neighbor_id)
            elif abs(existing - target) > tolerance:
                conflicted = True
    return assigned, conflicted


def _median(values: Sequence[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) * 0.5


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


def build_make_room_position_updates(
    *,
    grown_from: LayoutNodeBounds,
    grown_to: LayoutNodeBounds,
    movable_bounds: Sequence[LayoutNodeBounds],
    gap: float,
    keep_gap_x: float,
    keep_gap_y: float,
) -> dict[str, tuple[float, float]]:
    """Shift the row after a grown box right (and the column below it down; mirrored left/up) just enough.

    Every box of a row or column moves by the same amount, so rows stay straight. The first box keeps its original
    gap to the grower, capped at ``max(gap, keep_gap_x)`` horizontally / ``max(gap, keep_gap_y)`` vertically, and no
    box moves further than the growth on that side (repeated expand/collapse of a laid-out row does not drift).
    Boxes outside the grower's row and column bands stay.
    """
    normalized_gap = max(0.0, float(gap))
    cap_x = max(normalized_gap, float(keep_gap_x))
    cap_y = max(normalized_gap, float(keep_gap_y))

    def in_rows(bounds: LayoutNodeBounds) -> bool:
        return bounds.top < grown_to.bottom + normalized_gap and bounds.bottom > grown_to.top - normalized_gap

    def in_columns(bounds: LayoutNodeBounds) -> bool:
        return bounds.left < grown_to.right + normalized_gap and bounds.right > grown_to.left - normalized_gap

    boxes = [bounds for bounds in movable_bounds if bounds.node_id]
    claimed: set[str] = set()

    def claim(predicate: Callable[[LayoutNodeBounds], bool]) -> list[LayoutNodeBounds]:
        members = [bounds for bounds in boxes if bounds.node_id not in claimed and predicate(bounds)]
        claimed.update(bounds.node_id for bounds in members)
        return members

    row_after = claim(lambda bounds: bounds.left >= grown_from.right - 0.5 and in_rows(bounds))
    column_below = claim(lambda bounds: bounds.top >= grown_from.bottom - 0.5 and in_columns(bounds))
    row_before = claim(lambda bounds: bounds.right <= grown_from.left + 0.5 and in_rows(bounds))
    column_above = claim(lambda bounds: bounds.bottom <= grown_from.top + 0.5 and in_columns(bounds))

    updates: dict[str, tuple[float, float]] = {}

    def shift(members: list[LayoutNodeBounds], dx: float, dy: float) -> None:
        if dx == 0.0 and dy == 0.0:
            return
        for bounds in members:
            updates[bounds.node_id] = (bounds.x + dx, bounds.y + dy)

    if row_after:
        first = min(bounds.left for bounds in row_after)
        keep = min(first - grown_from.right, cap_x)
        shift(row_after, _clamp(grown_to.right + keep - first, 0.0, grown_to.right - grown_from.right), 0.0)
    if column_below:
        first = min(bounds.top for bounds in column_below)
        keep = min(first - grown_from.bottom, cap_y)
        shift(column_below, 0.0, _clamp(grown_to.bottom + keep - first, 0.0, grown_to.bottom - grown_from.bottom))
    if row_before:
        last = max(bounds.right for bounds in row_before)
        keep = min(grown_from.left - last, cap_x)
        shift(row_before, -_clamp(last - (grown_to.left - keep), 0.0, grown_from.left - grown_to.left), 0.0)
    if column_above:
        last = max(bounds.bottom for bounds in column_above)
        keep = min(grown_from.top - last, cap_y)
        shift(column_above, 0.0, -_clamp(last - (grown_to.top - keep), 0.0, grown_from.top - grown_to.top))
    return updates


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(float(value), max(low, high)))


def build_collision_avoidance_position_updates(
    *,
    fixed_bounds: Sequence[LayoutNodeBounds],
    movable_bounds: Sequence[LayoutNodeBounds],
    gap: float,
    reach_radius: float | None = None,
) -> dict[str, tuple[float, float]]:
    """Move each movable box that crowds a fixed or already-placed box to its nearest free spot.

    Boxes are resolved nearest-first; a moved box becomes a blocker for the rest. With ``reach_radius`` only
    boxes within that distance of a fixed box are considered.
    """
    fixed = list(fixed_bounds)
    if not fixed:
        return {}
    normalized_gap = max(0.0, float(gap))
    reach_bounds = [bounds.inflated(float(reach_radius)) for bounds in fixed] if reach_radius is not None else None
    remaining = {
        bounds.node_id: bounds
        for bounds in movable_bounds
        if bounds.node_id and bounds.width > 0.0 and bounds.height > 0.0
    }
    resolved_bounds = list(fixed)
    updates: dict[str, tuple[float, float]] = {}

    while remaining:
        colliding = [
            (
                min(_bounds_distance(bounds, fixed_box) for fixed_box in fixed),
                bounds.node_id,
                bounds,
            )
            for bounds in remaining.values()
            if (reach_bounds is None or any(_rects_intersect(bounds, reach) for reach in reach_bounds))
            and _first_intersecting_bounds(bounds, resolved_bounds, normalized_gap) is not None
        ]
        if not colliding:
            break
        _distance, node_id, bounds = min(colliding, key=lambda item: (item[0], item[1]))
        final_bounds = _separate_from_bounds(bounds, resolved_bounds, normalized_gap)
        if final_bounds.x != bounds.x or final_bounds.y != bounds.y:
            updates[node_id] = (final_bounds.x, final_bounds.y)
        resolved_bounds.append(final_bounds)
        remaining.pop(node_id, None)
    return updates


def _separate_from_bounds(
    bounds: LayoutNodeBounds,
    blockers: Sequence[LayoutNodeBounds],
    gap: float,
) -> LayoutNodeBounds:
    resolved = bounds
    for _attempt in range(max(1, len(blockers) * 4)):
        blocker = _first_intersecting_bounds(resolved, blockers, gap)
        if blocker is None:
            return resolved
        dx, dy = _nearest_separation_delta(resolved, blocker, gap)
        if dx == 0.0 and dy == 0.0:
            return resolved
        resolved = resolved.translated(dx, dy)
    if _first_intersecting_bounds(resolved, blockers, gap) is None:
        return resolved
    # Squeezed between blockers, the nearest-blocker steps can bounce back and forth; take the smallest single-axis
    # move from the original spot that clears every blocker instead (if there is one).
    return _nearest_clear_bounds(bounds, blockers, gap) or resolved


def _nearest_clear_bounds(
    bounds: LayoutNodeBounds,
    blockers: Sequence[LayoutNodeBounds],
    gap: float,
) -> LayoutNodeBounds | None:
    candidates: list[tuple[float, float, float, LayoutNodeBounds]] = []
    for blocker in blockers:
        for dx, dy in (
            (blocker.left - gap - bounds.right, 0.0),
            (blocker.right + gap - bounds.left, 0.0),
            (0.0, blocker.top - gap - bounds.bottom),
            (0.0, blocker.bottom + gap - bounds.top),
        ):
            candidate = bounds.translated(dx, dy)
            if _first_intersecting_bounds(candidate, blockers, gap) is None:
                candidates.append((abs(dx) + abs(dy), dx, dy, candidate))
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item[0], item[1], item[2]))[3]


def _first_intersecting_bounds(
    bounds: LayoutNodeBounds,
    blockers: Sequence[LayoutNodeBounds],
    gap: float,
) -> LayoutNodeBounds | None:
    candidates = [
        blocker
        for blocker in blockers
        if blocker.node_id != bounds.node_id and _rects_intersect(bounds, blocker.inflated(gap))
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda blocker: (
            _bounds_distance(bounds, blocker),
            blocker.node_id,
        ),
    )


def _nearest_separation_delta(
    bounds: LayoutNodeBounds,
    blocker: LayoutNodeBounds,
    gap: float,
) -> tuple[float, float]:
    moves = [
        ("left", blocker.left - gap - bounds.right, 0.0),
        ("right", blocker.right + gap - bounds.left, 0.0),
        ("up", 0.0, blocker.top - gap - bounds.bottom),
        ("down", 0.0, blocker.bottom + gap - bounds.top),
    ]
    preferred = _preferred_separation_sides(bounds, blocker)
    side, dx, dy = min(
        moves,
        key=lambda item: (
            abs(item[1]) + abs(item[2]),
            0 if item[0] in preferred else 1,
            item[0],
        ),
    )
    del side
    return float(dx), float(dy)


def _preferred_separation_sides(bounds: LayoutNodeBounds, blocker: LayoutNodeBounds) -> set[str]:
    dx = bounds.center_x - blocker.center_x
    dy = bounds.center_y - blocker.center_y
    preferred = {"right" if dx >= 0.0 else "left"}
    preferred.add("down" if dy >= 0.0 else "up")
    return preferred


def _rects_intersect(first: LayoutNodeBounds, second: LayoutNodeBounds) -> bool:
    return (
        first.left < second.right
        and first.right > second.left
        and first.top < second.bottom
        and first.bottom > second.top
    )


def _bounds_distance(first: LayoutNodeBounds, second: LayoutNodeBounds) -> float:
    dx = first.center_x - second.center_x
    dy = first.center_y - second.center_y
    return (dx * dx) + (dy * dy)


__all__ = [
    "LayoutNodeBounds",
    "PortAlignmentConstraint",
    "build_alignment_position_updates",
    "build_collision_avoidance_position_updates",
    "build_distribution_position_updates",
    "build_make_room_position_updates",
    "build_port_alignment_offsets",
    "build_straighten_connection_position_updates",
    "normalize_layout_position_updates",
    "snap_coordinate",
]
