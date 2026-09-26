# Purpose: Scene swimlane commands (new pools, add/insert/remove/move lanes, assign nodes, lane and pool resizes, orientation) and the settle pass that keeps every pool's lanes stacked and what lanes hold inside them after moves, drops, pastes, expands and deletions, inside the caller's undo step.
# Map: feature_routes/swimlane_pools_lanes
# Tests: tests/test_swimlane_scene_ops.py
# Landmarks: capture_swimlanes; settle_swimlanes; resize_swimlane_frame; initialize_swimlane_pool; create_swimlane_pool; add_swimlane_lane; remove_swimlane_lane; move_swimlane_lane; assign_nodes_to_swimlane_lane; set_swimlane_pool_orientation; swimlane_lane_removal_plan
"""Scene side of swimlane pools.

Pools and lanes are Group backdrops, so the Group area rule already says which lane holds a node and a lane drag
already carries its contents. What this module adds is the stacking rule of a pool (``graph/swimlane_layout.py``):
after anything moved, resized, appeared or vanished, :func:`settle_swimlanes` restacks the pools of the open scope.
Callers take a :func:`capture_swimlanes` snapshot before they mutate, so each lane keeps what it held; only the nodes
a user moved or added on their own are placed by where their centre lands.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ea_node_editor.graph.group_backdrop_geometry import hidden_node_ids
from ea_node_editor.graph.hierarchy import scope_node_ids, scope_parent_id
from ea_node_editor.graph.swimlane_layout import (
    SWIMLANE_CONTENT_PADDING,
    SWIMLANE_DEFAULT_LANE_COUNT,
    SWIMLANE_DEFAULT_LANE_THICKNESS,
    SWIMLANE_DEFAULT_POOL_LENGTH,
    SWIMLANE_LANE_HEADER,
    SWIMLANE_POOL_HEADER,
    SwimlaneLaneState,
    SwimlaneRestack,
    absorb_removed_swimlane_lane,
    is_swimlane_lane_type,
    is_swimlane_pool_type,
    is_swimlane_type,
    new_swimlane_pool_frames,
    normalize_swimlane_orientation,
    order_swimlane_lanes,
    resolve_swimlane_lane_resize,
    resolve_swimlane_pool_resize,
    restack_swimlane_pool,
    swimlane_frame_rect,
    swimlane_lane_index_at,
    swimlane_lane_thickness,
)
from ea_node_editor.graph.transform_layout_ops import LayoutNodeBounds
from ea_node_editor.graph.transform_tidy_layout import DEFAULT_TIDY_COLUMN_GAP
from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.nodes.builtins.passive_annotation import (
    PASSIVE_ANNOTATION_SWIMLANE_LANE_TYPE_ID,
    PASSIVE_ANNOTATION_SWIMLANE_POOL_TYPE_ID,
    SWIMLANE_ORIENTATIONS,
)
from ea_node_editor.ui.shell.runtime_history import (
    ACTION_ADD_SWIMLANE_LANE,
    ACTION_ASSIGN_SWIMLANE_LANE,
    ACTION_CREATE_SWIMLANE_POOL,
    ACTION_EDIT_NODE_PROPERTY,
    ACTION_MOVE_SWIMLANE_LANE,
    ACTION_REMOVE_SWIMLANE_LANE,
    ACTION_RESIZE_NODE,
)
from ea_node_editor.ui_qml.graph_scene_mutation.group_scope import GroupScope, collect_group_scope

_TOLERANCE = 0.01


@dataclass(slots=True)
class SwimlanePoolSnapshot:
    pool_id: str
    orientation: str
    lane_ids: list[str]


@dataclass(slots=True)
class SwimlaneSnapshot:
    """The open scope's pools before a mutation: lanes in stack order and which lane held each top-level item."""

    pools: dict[str, SwimlanePoolSnapshot] = field(default_factory=dict)
    lane_pool: dict[str, str] = field(default_factory=dict)
    item_lane: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class _SwimlaneUpdates:
    positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    geometries: dict[str, tuple[float, float, float, float]] = field(default_factory=dict)
    orientations: dict[str, str] = field(default_factory=dict)

    def changed_ids(self) -> set[str]:
        return set(self.positions) | set(self.geometries) | set(self.orientations)


# --- snapshots ---------------------------------------------------------------------------------------------------


def capture_swimlanes(self, workspace: WorkspaceData | None = None) -> SwimlaneSnapshot | None:
    """The open scope's pools, or ``None`` when it holds no pool or lane (the fast path every caller takes)."""
    workspace = workspace or self._scene_context.workspace_or_none()
    if workspace is None or self._scene_context.registry is None:
        return None
    scope_ids = scope_node_ids(workspace, self._scene_context.scope_path)
    if not _scope_has_swimlanes(workspace, scope_ids):
        return None
    scope = collect_group_scope(self, workspace, scope_ids, dict(workspace.nodes))
    return _snapshot_from_scope(workspace, scope)


def scope_has_swimlanes(self, workspace: WorkspaceData) -> bool:
    """Whether the open scope holds a pool or a lane (cheap: no measuring)."""
    return _scope_has_swimlanes(workspace, scope_node_ids(workspace, self._scene_context.scope_path))


def _scope_has_swimlanes(workspace: WorkspaceData, scope_ids: Iterable[str]) -> bool:
    return any(is_swimlane_type(workspace.nodes[node_id].type_id) for node_id in scope_ids if node_id in workspace.nodes)


def _snapshot_from_scope(workspace: WorkspaceData, scope: GroupScope) -> SwimlaneSnapshot:
    snapshot = SwimlaneSnapshot()
    hidden = hidden_node_ids(workspace.nodes)
    for pool_id in _active_pool_ids(workspace, scope, hidden):
        orientation = _orientation(workspace, pool_id)
        lane_ids = [
            member_id
            for member_id in scope.direct_members(pool_id)
            if is_swimlane_lane_type(workspace.nodes[member_id].type_id)
        ]
        order = order_swimlane_lanes([scope.rects[lane_id] for lane_id in lane_ids], orientation)
        snapshot.pools[pool_id] = SwimlanePoolSnapshot(pool_id=pool_id, orientation=orientation, lane_ids=order)
        lane_rects = [scope.rects[lane_id] for lane_id in order]
        for lane_id in order:
            snapshot.lane_pool[lane_id] = pool_id
            for member_id in scope.direct_members(lane_id):
                snapshot.item_lane[member_id] = lane_id
        for member_id in scope.direct_members(pool_id):
            if member_id in snapshot.lane_pool:
                continue
            if not order:
                snapshot.item_lane[member_id] = pool_id  # a lane-less pool holds it itself
                continue
            index = swimlane_lane_index_at(scope.rects[pool_id], orientation, lane_rects, _center(scope.rects[member_id]))
            if index is not None:
                snapshot.item_lane[member_id] = order[index]
    return snapshot


def _pool_item_ids(before: SwimlaneSnapshot, pool_id: str) -> set[str]:
    """Top-level items of a pool in ``before``: what its lanes hold, or what a lane-less pool holds itself."""
    return {
        item_id
        for item_id, owner_id in before.item_lane.items()
        if owner_id == pool_id or before.lane_pool.get(owner_id) == pool_id
    }


# --- the settle pass ---------------------------------------------------------------------------------------------


def settle_swimlanes(
    self,
    workspace: WorkspaceData,
    before: SwimlaneSnapshot | None,
    *,
    moved_ids: Collection[str] = (),
    created_ids: Collection[str] = (),
    stale_ids: Collection[str] = (),
) -> set[str]:
    """Restack the open scope's pools after a mutation (inside the caller's undo step); returns the changed ids.

    A node keeps the lane it had in ``before`` unless it was moved without that lane (``moved_ids``) or is new
    (``created_ids``); then the lane its centre lands in takes it. A lane moved on its own joins the pool (of its
    orientation) its centre lands in, else goes back to its pool; a new lane outside every pool gets a pool of its own.
    ``stale_ids`` are nodes whose drawn size changed since the last payload build (they are measured afresh).
    """
    scope_ids = scope_node_ids(workspace, self._scene_context.scope_path)
    if before is None and not _scope_has_swimlanes(workspace, scope_ids):
        return set()
    before = before or SwimlaneSnapshot()
    created = {str(node_id) for node_id in created_ids}
    wrapped = _wrap_orphan_lanes(self, workspace, before, scope_ids, created)
    if wrapped:
        scope_ids = scope_node_ids(workspace, self._scene_context.scope_path)
        created |= wrapped
    scope = collect_group_scope(self, workspace, scope_ids, dict(workspace.nodes), stale_ids=stale_ids)
    updates = _settle_updates(workspace, scope, before, moved_ids={str(node_id) for node_id in moved_ids}, created=created)
    _apply_updates(self, workspace, updates)
    return updates.changed_ids() | wrapped


def _settle_updates(
    workspace: WorkspaceData,
    scope: GroupScope,
    before: SwimlaneSnapshot,
    *,
    moved_ids: set[str],
    created: set[str],
) -> _SwimlaneUpdates:
    hidden = hidden_node_ids(workspace.nodes)
    pool_ids = _active_pool_ids(workspace, scope, hidden)
    if not pool_ids:
        return _SwimlaneUpdates()
    rects = dict(scope.rects)
    orientation_by_pool = {pool_id: _orientation(workspace, pool_id) for pool_id in pool_ids}
    pool_of = _pool_locator(scope, rects, orientation_by_pool)

    lanes_by_pool: dict[str, list[str]] = {pool_id: [] for pool_id in pool_ids}
    lane_target: dict[str, str] = {}
    snapped_back: set[str] = set()  # dragged off every pool of its orientation: back to its old slot
    for lane_id in sorted(scope.rects):
        node = workspace.nodes.get(lane_id)
        if node is None or lane_id in hidden or not is_swimlane_lane_type(node.type_id):
            continue
        previous = before.lane_pool.get(lane_id)
        if lane_id in created or previous is None:
            target = pool_of(lane_id)
        elif lane_id in moved_ids and previous not in moved_ids:
            target = pool_of(lane_id, orientation=orientation_by_pool.get(previous, _orientation(workspace, lane_id)))
            if target is None:
                target = previous
                snapped_back.add(lane_id)
        else:
            target = previous
        if target is None or target not in lanes_by_pool:
            continue
        lanes_by_pool[target].append(lane_id)
        lane_target[lane_id] = target

    lane_order: dict[str, list[str]] = {}
    for pool_id, lane_ids in lanes_by_pool.items():
        previous_order = before.pools[pool_id].lane_ids if pool_id in before.pools else []
        order = order_swimlane_lanes(
            [rects[lane_id] for lane_id in lane_ids if lane_id not in snapped_back],
            orientation_by_pool[pool_id],
            previous_order=previous_order,
        )
        for lane_id in sorted(
            (lane_id for lane_id in lane_ids if lane_id in snapped_back),
            key=lambda lane_id: previous_order.index(lane_id) if lane_id in previous_order else len(previous_order),
        ):
            index = previous_order.index(lane_id) if lane_id in previous_order else len(order)
            order.insert(min(index, len(order)), lane_id)
        lane_order[pool_id] = order

    # Which lane (or lane-less pool) takes each top-level item; ``placed`` are the ones sorted by where they landed.
    item_lane: dict[str, str] = {}
    placed: set[str] = set()
    pool_items: dict[str, list[str]] = {pool_id: [] for pool_id in pool_ids}
    for node_id in sorted(scope.rects):
        node = workspace.nodes.get(node_id)
        if node is None or node_id in hidden or is_swimlane_lane_type(node.type_id):
            continue
        kept = before.item_lane.get(node_id)
        keep = (
            kept is not None
            and kept in lane_target
            and node_id not in created
            and (node_id not in moved_ids or kept in moved_ids)
        )
        if keep:
            item_lane[node_id] = kept
            continue
        pool_id = pool_of(node_id)
        if pool_id is None or _carried_inside_pool(scope, node_id, pool_id, pool_of, lane_target):
            continue
        order = lane_order[pool_id]
        if not order:
            pool_items[pool_id].append(node_id)
            continue
        index = swimlane_lane_index_at(
            rects[pool_id],
            orientation_by_pool[pool_id],
            [rects[lane_id] for lane_id in order],
            _center(rects[node_id]),
        )
        if index is not None:
            item_lane[node_id] = order[index]
            placed.add(node_id)

    items_by_lane: dict[str, list[str]] = {}
    for node_id, lane_id in item_lane.items():
        items_by_lane.setdefault(lane_id, []).append(node_id)

    updates = _SwimlaneUpdates()
    start_rects = dict(rects)
    for pool_id in _innermost_first(pool_ids, pool_of):
        orientation = orientation_by_pool[pool_id]
        order = lane_order[pool_id]
        own_items = set(pool_items[pool_id]) | {
            item_id for lane_id in order for item_id in items_by_lane.get(lane_id, ())
        }
        restack = restack_swimlane_pool(
            rects[pool_id],
            orientation,
            [
                SwimlaneLaneState(
                    lane_id=lane_id,
                    bounds=rects[lane_id],
                    item_bounds=tuple(rects[item_id] for item_id in items_by_lane.get(lane_id, ())),
                    # A lane joining from a pool of the other orientation keeps its own thickness.
                    thickness=(
                        swimlane_lane_thickness(rects[lane_id], _orientation(workspace, lane_id))
                        if _orientation(workspace, lane_id) != orientation
                        else None
                    ),
                )
                for lane_id in order
            ],
            pool_items=[rects[item_id] for item_id in pool_items[pool_id]],
            placed_item_ids=placed,
        )
        _place_restack(scope, rects, restack, own_items)
        for lane_id in order:
            if _orientation(workspace, lane_id) != orientation:
                updates.orientations[lane_id] = orientation

    _collect_rect_updates(workspace, scope, start_rects, rects, updates)
    return updates


def _pool_locator(
    scope: GroupScope,
    rects: Mapping[str, LayoutNodeBounds],
    orientation_by_pool: Mapping[str, str],
):
    """``pool_of(node_id, orientation=None)``: the innermost active pool holding the node's centre.

    Pools inside the node (its contents) never count, so a Group around a whole pool does not land in it; with
    ``orientation`` only pools of that orientation count.
    """
    by_area = sorted(orientation_by_pool, key=lambda pool_id: (rects[pool_id].width * rects[pool_id].height, pool_id))

    def pool_of(node_id: str, *, orientation: str | None = None) -> str | None:
        rect = rects.get(node_id)
        if rect is None:
            return None
        inside = set(scope.contents(node_id)) if node_id in scope.group_backdrop_ids else set()
        x, y = _center(rect)
        for pool_id in by_area:
            if pool_id == node_id or pool_id in inside:
                continue
            pool_rect = rects[pool_id]
            if not (pool_rect.left <= x <= pool_rect.right and pool_rect.top <= y <= pool_rect.bottom):
                continue
            if orientation is not None and orientation_by_pool[pool_id] != orientation:
                continue
            return pool_id
        return None

    return pool_of


def _carried_inside_pool(
    scope: GroupScope,
    node_id: str,
    pool_id: str,
    pool_of,
    lane_ids: Collection[str],
) -> bool:
    """True when a Group or a nested pool inside ``pool_id`` holds ``node_id``, which then moves with that holder.

    Lanes never carry here: they are what the item is being sorted into.
    """
    seen = {node_id}
    owner_id = scope.owner(node_id)
    while owner_id is not None and owner_id not in seen and owner_id != pool_id:
        seen.add(owner_id)
        if owner_id not in lane_ids and pool_of(owner_id) == pool_id:
            return True
        owner_id = scope.owner(owner_id)
    return False


def _innermost_first(pool_ids: Sequence[str], pool_of) -> list[str]:
    def depth(pool_id: str) -> int:
        count = 0
        seen = {pool_id}
        current = pool_of(pool_id)
        while current is not None and current not in seen:
            count += 1
            seen.add(current)
            current = pool_of(current)
        return count

    return sorted(pool_ids, key=lambda pool_id: (-depth(pool_id), pool_id))


def _place_restack(
    scope: GroupScope,
    rects: dict[str, LayoutNodeBounds],
    restack: SwimlaneRestack,
    own_items: set[str],
) -> None:
    """Write a restack into ``rects``: the pool and lanes take their new frames, items move with what they carry."""
    rects[restack.pool.node_id] = restack.pool
    for lane_rect in restack.lanes:
        rects[lane_rect.node_id] = lane_rect
    for item_id, (dx, dy) in restack.item_offsets.items():
        moved = [item_id]
        if item_id in scope.group_backdrop_ids:
            moved.extend(content_id for content_id in scope.contents(item_id) if content_id not in own_items)
        for moved_id in moved:
            if moved_id in rects:
                rects[moved_id] = rects[moved_id].translated(dx, dy)


def _collect_rect_updates(
    workspace: WorkspaceData,
    scope: GroupScope,
    start_rects: Mapping[str, LayoutNodeBounds],
    rects: Mapping[str, LayoutNodeBounds],
    updates: _SwimlaneUpdates,
) -> None:
    for node_id, rect in rects.items():
        start = start_rects.get(node_id)
        node = workspace.nodes.get(node_id)
        if start is None or node is None:
            continue
        if is_swimlane_type(node.type_id) and node_id not in scope.collapsed_ids:
            if (
                abs(rect.x - start.x) >= _TOLERANCE
                or abs(rect.y - start.y) >= _TOLERANCE
                or abs(rect.width - start.width) >= _TOLERANCE
                or abs(rect.height - start.height) >= _TOLERANCE
                or node.custom_width is None
                or node.custom_height is None
            ):
                updates.geometries[node_id] = (rect.x, rect.y, rect.width, rect.height)
            continue
        dx = rect.x - start.x
        dy = rect.y - start.y
        if abs(dx) >= _TOLERANCE or abs(dy) >= _TOLERANCE:
            updates.positions[node_id] = (float(node.x) + dx, float(node.y) + dy)


def _apply_updates(self, workspace: WorkspaceData, updates: _SwimlaneUpdates) -> None:
    if not updates.changed_ids():
        return
    mutations = self._record_mutations()
    for node_id, (x, y, width, height) in updates.geometries.items():
        if node_id in workspace.nodes:
            mutations.set_node_geometry(node_id, x, y, width, height)
    for node_id, (x, y) in updates.positions.items():
        if node_id in workspace.nodes and node_id not in updates.geometries:
            mutations.set_node_position(node_id, x, y)
    if updates.orientations:
        validated = self._validated_mutations()
        for node_id, orientation in updates.orientations.items():
            if node_id in workspace.nodes:
                validated.set_node_properties(node_id, {"orientation": orientation})


def _wrap_orphan_lanes(
    self,
    workspace: WorkspaceData,
    before: SwimlaneSnapshot,
    scope_ids: Sequence[str],
    created: set[str],
) -> set[str]:
    """Give each new lane that landed outside every pool a pool of its own (lanes live in pools)."""
    orphan_ids = [
        node_id
        for node_id in scope_ids
        if node_id in created
        and node_id in workspace.nodes
        and is_swimlane_lane_type(workspace.nodes[node_id].type_id)
        and node_id not in before.lane_pool
    ]
    if not orphan_ids:
        return set()
    scope = collect_group_scope(self, workspace, list(scope_ids), dict(workspace.nodes))
    hidden = hidden_node_ids(workspace.nodes)
    pool_ids = _active_pool_ids(workspace, scope, hidden)
    pool_of = _pool_locator(scope, scope.rects, pool_ids)
    new_pool_ids: set[str] = set()
    for lane_id in orphan_ids:
        if pool_of(lane_id) is not None or lane_id not in scope.rects:
            continue
        lane_rect = scope.rects[lane_id]
        orientation = _orientation(workspace, lane_id)
        frame = swimlane_frame_rect(lane_rect, orientation)
        pool_frame = LayoutNodeBounds("", frame.x - SWIMLANE_POOL_HEADER, frame.y, frame.width + SWIMLANE_POOL_HEADER, frame.height)
        pool_rect = swimlane_frame_rect(pool_frame, orientation)
        pool_id = _add_swimlane_node(
            self,
            workspace,
            PASSIVE_ANNOTATION_SWIMLANE_POOL_TYPE_ID,
            pool_rect,
            orientation=orientation,
            parent_node_id=workspace.nodes[lane_id].parent_node_id,
        )
        new_pool_ids.add(pool_id)
    return new_pool_ids


# --- resizing ----------------------------------------------------------------------------------------------------


def resize_swimlane_frame(self, node_id: str, x: float, y: float, width: float, height: float) -> bool | None:
    """Resize a lane or an expanded pool the swimlane way (one undo step); ``None`` for any other node."""
    workspace = self._scene_context.workspace_or_none()
    if workspace is None or node_id not in workspace.nodes:
        return None
    node = workspace.nodes[node_id]
    if not is_swimlane_type(node.type_id) or bool(node.collapsed):
        return None
    before = capture_swimlanes(self, workspace)
    if before is None:
        return None
    pool_id = node_id if is_swimlane_pool_type(node.type_id) else before.lane_pool.get(node_id)
    if pool_id is None or pool_id not in before.pools:
        return None
    scope = collect_group_scope(self, workspace, scope_node_ids(workspace, self._scene_context.scope_path), dict(workspace.nodes))
    pool_snapshot = before.pools[pool_id]
    lanes = _lane_states(scope, before, pool_snapshot)
    requested = LayoutNodeBounds(node_id, float(x), float(y), float(width), float(height))
    pool_rect = scope.rects[pool_id]
    if node_id == pool_id:
        request = resolve_swimlane_pool_resize(
            pool_rect,
            pool_snapshot.orientation,
            lanes,
            requested,
            pool_items=[scope.rects[item_id] for item_id in _pool_own_items(before, pool_id)],
        )
    else:
        request = resolve_swimlane_lane_resize(pool_rect, pool_snapshot.orientation, lanes, node_id, requested)
    if request is None:
        return None
    restack = restack_swimlane_pool(
        pool_rect,
        pool_snapshot.orientation,
        request.lanes,
        pool_items=[scope.rects[item_id] for item_id in _pool_own_items(before, pool_id)],
        stack_start=request.stack_start,
        cross_start=request.cross_start,
        cross_end=request.cross_end,
        pool_thickness=request.pool_thickness,
    )
    rects = dict(scope.rects)
    start_rects = dict(scope.rects)
    own_items = _pool_item_ids(before, pool_id)
    _place_restack(scope, rects, restack, own_items)
    updates = _SwimlaneUpdates()
    _collect_rect_updates(workspace, scope, start_rects, rects, updates)
    if not updates.changed_ids():
        return False
    history_group = self._scene_context.grouped_history_action(ACTION_RESIZE_NODE, workspace)
    with history_group:
        _apply_updates(self, workspace, updates)
        # An outer pool holding this one restacks around its new size.
        settle_swimlanes(self, workspace, before)
    self._scene_context.rebuild_models()
    return True


def _lane_states(scope: GroupScope, before: SwimlaneSnapshot, pool: SwimlanePoolSnapshot) -> list[SwimlaneLaneState]:
    items_by_lane: dict[str, list[str]] = {}
    for item_id, lane_id in before.item_lane.items():
        items_by_lane.setdefault(lane_id, []).append(item_id)
    return [
        SwimlaneLaneState(
            lane_id=lane_id,
            bounds=scope.rects[lane_id],
            item_bounds=tuple(scope.rects[item_id] for item_id in sorted(items_by_lane.get(lane_id, ())) if item_id in scope.rects),
        )
        for lane_id in pool.lane_ids
        if lane_id in scope.rects
    ]


def _pool_own_items(before: SwimlaneSnapshot, pool_id: str) -> list[str]:
    """What a lane-less pool holds itself (a pool with lanes hands everything to its lanes)."""
    pool = before.pools.get(pool_id)
    if pool is None or pool.lane_ids:
        return []
    return [item_id for item_id, owner_id in before.item_lane.items() if owner_id == pool_id]


# --- pools -------------------------------------------------------------------------------------------------------


def initialize_swimlane_pool(
    self,
    workspace: WorkspaceData,
    pool_id: str,
    *,
    lane_titles: Sequence[str] | None = None,
    lane_thickness: float = SWIMLANE_DEFAULT_LANE_THICKNESS,
    length: float = SWIMLANE_DEFAULT_POOL_LENGTH,
) -> list[str]:
    """Give a new pool its lanes and frames (inside the caller's undo step); returns the lane ids in order."""
    pool = workspace.nodes.get(pool_id)
    if pool is None or not is_swimlane_pool_type(pool.type_id):
        return []
    orientation = _orientation(workspace, pool_id)
    titles = list(lane_titles) if lane_titles is not None else [
        f"Lane {index + 1}" for index in range(SWIMLANE_DEFAULT_LANE_COUNT)
    ]
    lane_ids = [
        _add_swimlane_node(
            self,
            workspace,
            PASSIVE_ANNOTATION_SWIMLANE_LANE_TYPE_ID,
            LayoutNodeBounds("", float(pool.x), float(pool.y), 1.0, 1.0),
            orientation=orientation,
            parent_node_id=pool.parent_node_id,
            title=str(title),
        )
        for title in titles
    ]
    frames = new_swimlane_pool_frames(
        float(pool.x),
        float(pool.y),
        orientation,
        lane_ids,
        pool_id=pool_id,
        lane_thickness=lane_thickness,
        length=length,
    )
    mutations = self._record_mutations()
    mutations.set_node_geometry(pool_id, frames.pool.x, frames.pool.y, frames.pool.width, frames.pool.height)
    for lane_rect in frames.lanes:
        mutations.set_node_geometry(lane_rect.node_id, lane_rect.x, lane_rect.y, lane_rect.width, lane_rect.height)
    return lane_ids


def create_swimlane_pool(
    self,
    *,
    x: float,
    y: float,
    orientation: str = "",
    title: str = "",
    lane_titles: Sequence[str] | None = None,
    lane_thickness: float = SWIMLANE_DEFAULT_LANE_THICKNESS,
    length: float = SWIMLANE_DEFAULT_POOL_LENGTH,
) -> tuple[str, list[str]]:
    """Add a pool with its lanes at (``x``, ``y``) in the open scope as one undo step; returns (pool id, lane ids)."""
    workspace = self._scene_context.workspace_or_none()
    if workspace is None or self._scene_context.registry is None:
        return "", []
    normalized_orientation = normalize_swimlane_orientation(orientation)
    lane_ids: list[str] = []
    pool_id = ""
    history_group = self._scene_context.grouped_history_action(
        ACTION_CREATE_SWIMLANE_POOL,
        workspace,
        commit_if=lambda: bool(pool_id),
    )
    with history_group:
        pool_id = _add_swimlane_node(
            self,
            workspace,
            PASSIVE_ANNOTATION_SWIMLANE_POOL_TYPE_ID,
            LayoutNodeBounds("", float(x), float(y), 1.0, 1.0),
            orientation=normalized_orientation,
            parent_node_id=scope_parent_id(self._scene_context.scope_path),
            title=str(title).strip() or None,
        )
        lane_ids = initialize_swimlane_pool(
            self,
            workspace,
            pool_id,
            lane_titles=lane_titles,
            lane_thickness=lane_thickness,
            length=length,
        )
    self._scene_context.rebuild_models()
    self._scope_selection.set_selected_node_ids([pool_id], workspace=workspace)
    return pool_id, lane_ids


def set_swimlane_pool_orientation(self, pool_id: str, orientation: str) -> bool:
    """Turn a pool's lanes from rows to columns or back (one undo step).

    Every lane keeps its thickness and order, and every node keeps its place along the flow and across its lane:
    what ran left to right in a lane now runs top to bottom in the same lane.
    """
    workspace = self._scene_context.workspace_or_none()
    normalized = str(orientation or "").strip().lower()
    if workspace is None or normalized not in SWIMLANE_ORIENTATIONS or pool_id not in workspace.nodes:
        return False
    pool = workspace.nodes[pool_id]
    if not is_swimlane_pool_type(pool.type_id) or _orientation(workspace, pool_id) == normalized:
        return False
    before = capture_swimlanes(self, workspace)
    history_group = self._scene_context.grouped_history_action(ACTION_EDIT_NODE_PROPERTY, workspace)
    with history_group:
        if before is not None and pool_id in before.pools and not bool(pool.collapsed):
            _transpose_pool(self, workspace, before, pool_id, normalized)
        self._validated_mutations().set_node_properties(pool_id, {"orientation": normalized})
        settle_swimlanes(self, workspace, capture_swimlanes(self, workspace))
    self._scene_context.rebuild_models()
    return True


def _transpose_pool(
    self,
    workspace: WorkspaceData,
    before: SwimlaneSnapshot,
    pool_id: str,
    orientation: str,
) -> None:
    """Rebuild a pool in ``orientation``: each lane keeps its thickness, each item its offsets along the flow and
    across its lane (measured from the lane's content corner)."""
    scope = collect_group_scope(self, workspace, scope_node_ids(workspace, self._scene_context.scope_path), dict(workspace.nodes))
    snapshot = before.pools[pool_id]
    old = snapshot.orientation
    pool_rect = scope.rects[pool_id]
    old_frame_pool = swimlane_frame_rect(pool_rect, old)
    thickness = {lane_id: swimlane_lane_thickness(scope.rects[lane_id], old) for lane_id in snapshot.lane_ids}
    length = old_frame_pool.width
    frames = new_swimlane_pool_frames(
        pool_rect.x,
        pool_rect.y,
        orientation,
        snapshot.lane_ids,
        pool_id=pool_id,
        lane_thickness=SWIMLANE_DEFAULT_LANE_THICKNESS,
        length=length,
    )
    # new_swimlane_pool_frames gives every lane one thickness; restack with each lane's own.
    lane_states = []
    for lane_rect in frames.lanes:
        lane_states.append(
            SwimlaneLaneState(lane_id=lane_rect.node_id, bounds=lane_rect, thickness=thickness[lane_rect.node_id])
        )
    stacked = restack_swimlane_pool(frames.pool, orientation, lane_states)
    new_lane_rects = {lane_rect.node_id: lane_rect for lane_rect in stacked.lanes}
    rects = dict(scope.rects)
    mutations = self._record_mutations()
    for lane_id in snapshot.lane_ids:
        old_lane = swimlane_frame_rect(scope.rects[lane_id], old)
        new_lane = swimlane_frame_rect(new_lane_rects[lane_id], orientation)
        for item_id, owner_lane in before.item_lane.items():
            if owner_lane != lane_id or item_id not in rects:
                continue
            item = swimlane_frame_rect(rects[item_id], old)
            # Keep the item's centre at the same (flow, across) offset from its lane's corner, in the new frame.
            center_u = item.x + item.width * 0.5 - old_lane.x
            center_v = item.y + item.height * 0.5 - old_lane.y
            real = rects[item_id]
            new_item_frame = swimlane_frame_rect(real, orientation)
            target = LayoutNodeBounds(
                item_id,
                new_lane.x + center_u - new_item_frame.width * 0.5,
                new_lane.y + center_v - new_item_frame.height * 0.5,
                new_item_frame.width,
                new_item_frame.height,
            )
            target_real = swimlane_frame_rect(target, orientation)
            dx = target_real.x - real.x
            dy = target_real.y - real.y
            moved = [item_id]
            if item_id in scope.group_backdrop_ids:
                moved.extend(scope.contents(item_id))
            for moved_id in moved:
                node = workspace.nodes.get(moved_id)
                if node is not None:
                    mutations.set_node_position(moved_id, float(node.x) + dx, float(node.y) + dy)
        lane_rect = new_lane_rects[lane_id]
        mutations.set_node_geometry(lane_id, lane_rect.x, lane_rect.y, lane_rect.width, lane_rect.height)
    mutations.set_node_geometry(pool_id, stacked.pool.x, stacked.pool.y, stacked.pool.width, stacked.pool.height)
    validated = self._validated_mutations()
    for lane_id in snapshot.lane_ids:
        validated.set_node_properties(lane_id, {"orientation": orientation})


# --- lanes -------------------------------------------------------------------------------------------------------


def add_swimlane_lane(self, pool_id: str, index: int | None = None, title: str = "") -> str:
    """Add a lane to an expanded pool at ``index`` (``None`` = after the last) as one undo step; returns its id."""
    workspace = self._scene_context.workspace_or_none()
    before = capture_swimlanes(self, workspace) if workspace is not None else None
    if workspace is None or before is None or pool_id not in before.pools:
        return ""
    snapshot = before.pools[pool_id]
    position = len(snapshot.lane_ids) if index is None else max(0, min(int(index), len(snapshot.lane_ids)))
    lane_id = ""
    history_group = self._scene_context.grouped_history_action(
        ACTION_ADD_SWIMLANE_LANE,
        workspace,
        commit_if=lambda: bool(lane_id),
    )
    with history_group:
        pool = workspace.nodes[pool_id]
        lane_id = _add_swimlane_node(
            self,
            workspace,
            PASSIVE_ANNOTATION_SWIMLANE_LANE_TYPE_ID,
            LayoutNodeBounds("", float(pool.x), float(pool.y), 1.0, 1.0),
            orientation=snapshot.orientation,
            parent_node_id=pool.parent_node_id,
            title=str(title).strip() or f"Lane {len(snapshot.lane_ids) + 1}",
        )
        scope = collect_group_scope(self, workspace, scope_node_ids(workspace, self._scene_context.scope_path), dict(workspace.nodes))
        lanes = _lane_states(scope, before, snapshot)
        placeholder = scope.rects.get(lane_id, LayoutNodeBounds(lane_id, pool.x, pool.y, 1.0, 1.0))
        lanes.insert(
            position,
            SwimlaneLaneState(lane_id=lane_id, bounds=placeholder, thickness=SWIMLANE_DEFAULT_LANE_THICKNESS),
        )
        _restack_and_apply(self, workspace, scope, before, pool_id, lanes)
    self._scene_context.rebuild_models()
    self._scope_selection.set_selected_node_ids([lane_id], workspace=workspace)
    return lane_id


def insert_swimlane_lane(self, lane_id: str, *, after: bool) -> str:
    """Add a lane next to ``lane_id`` (before or after it); returns the new lane id."""
    workspace = self._scene_context.workspace_or_none()
    before = capture_swimlanes(self, workspace) if workspace is not None else None
    if before is None or lane_id not in before.lane_pool:
        return ""
    pool_id = before.lane_pool[lane_id]
    index = before.pools[pool_id].lane_ids.index(lane_id) + (1 if after else 0)
    return add_swimlane_lane(self, pool_id, index)


def remove_swimlane_lane(self, lane_id: str) -> bool:
    """Remove a lane as one undo step: the lane before it (else after it) takes its band, so nothing else moves."""
    workspace = self._scene_context.workspace_or_none()
    before = capture_swimlanes(self, workspace) if workspace is not None else None
    if workspace is None or before is None or lane_id not in before.lane_pool:
        return False
    history_group = self._scene_context.grouped_history_action(ACTION_REMOVE_SWIMLANE_LANE, workspace)
    with history_group:
        plan = swimlane_lane_removal_plan(self, workspace, [lane_id], before=before)
        _apply_updates(self, workspace, plan)
        incident = {
            edge.edge_id
            for edge in workspace.edges.values()
            if lane_id in (edge.source_node_id, edge.target_node_id)
        }
        self._record_mutations().remove_node(lane_id, incident_edge_ids=incident)
    self._scope_selection.set_selected_node_ids(
        [node_id for node_id in self._scene_context.selected_node_ids if node_id in workspace.nodes],
        workspace=workspace,
    )
    self._scene_context.rebuild_models()
    return True


def swimlane_lane_removal_plan(
    self,
    workspace: WorkspaceData,
    removed_ids: Iterable[str],
    *,
    before: SwimlaneSnapshot | None = None,
) -> _SwimlaneUpdates:
    """Frames that close the gaps of lanes about to be removed (pools being removed too are left alone)."""
    removed = {str(node_id) for node_id in removed_ids}
    before = before if before is not None else capture_swimlanes(self, workspace)
    updates = _SwimlaneUpdates()
    if before is None:
        return updates
    scope = collect_group_scope(self, workspace, scope_node_ids(workspace, self._scene_context.scope_path), dict(workspace.nodes))
    for pool_id, pool in before.pools.items():
        if pool_id in removed or not removed.intersection(pool.lane_ids):
            continue
        lanes = _lane_states(scope, before, pool)
        for lane_id in pool.lane_ids:
            if lane_id in removed:
                lanes = absorb_removed_swimlane_lane(lanes, lane_id, pool.orientation)
        restack = restack_swimlane_pool(
            scope.rects[pool_id],
            pool.orientation,
            lanes,
            pool_items=[scope.rects[item_id] for item_id, lane_id in before.item_lane.items() if lane_id in removed and not lanes and item_id in scope.rects],
        )
        rects = dict(scope.rects)
        own_items = _pool_item_ids(before, pool_id)
        _place_restack(scope, rects, restack, own_items)
        _collect_rect_updates(workspace, scope, scope.rects, rects, updates)
    for node_id in removed:
        updates.geometries.pop(node_id, None)
        updates.positions.pop(node_id, None)
    return updates


def close_removed_swimlane_lanes(self, workspace: WorkspaceData, removed_ids: Iterable[str]) -> set[str]:
    """Before lanes are removed (inside the caller's undo step): their neighbours take their bands. Returns the
    ids whose frames changed."""
    removed = [str(node_id) for node_id in removed_ids]
    if not any(
        node_id in workspace.nodes and is_swimlane_lane_type(workspace.nodes[node_id].type_id) for node_id in removed
    ):
        return set()
    plan = swimlane_lane_removal_plan(self, workspace, removed)
    _apply_updates(self, workspace, plan)
    return plan.changed_ids()


def swimlane_pool_lane_ids(self, workspace: WorkspaceData, pool_ids: Iterable[str]) -> list[str]:
    """The lanes of the given expanded pools (removing or copying a pool takes its lanes along)."""
    wanted = {str(pool_id) for pool_id in pool_ids}
    before = capture_swimlanes(self, workspace)
    if before is None:
        return []
    return [lane_id for pool_id in sorted(wanted & set(before.pools)) for lane_id in before.pools[pool_id].lane_ids]


def move_swimlane_lane(self, lane_id: str, offset: int) -> bool:
    """Move a lane ``offset`` places along its pool's stack (negative = up or left) as one undo step."""
    workspace = self._scene_context.workspace_or_none()
    before = capture_swimlanes(self, workspace) if workspace is not None else None
    if workspace is None or before is None or lane_id not in before.lane_pool or int(offset) == 0:
        return False
    pool_id = before.lane_pool[lane_id]
    order = list(before.pools[pool_id].lane_ids)
    current = order.index(lane_id)
    target = max(0, min(current + int(offset), len(order) - 1))
    if target == current:
        return False
    order.insert(target, order.pop(current))
    history_group = self._scene_context.grouped_history_action(ACTION_MOVE_SWIMLANE_LANE, workspace)
    with history_group:
        scope = collect_group_scope(self, workspace, scope_node_ids(workspace, self._scene_context.scope_path), dict(workspace.nodes))
        states = {state.lane_id: state for state in _lane_states(scope, before, before.pools[pool_id])}
        _restack_and_apply(self, workspace, scope, before, pool_id, [states[item] for item in order])
    self._scene_context.rebuild_models()
    return True


def assign_nodes_to_swimlane_lane(self, node_ids: Sequence[Any], lane_id: str) -> list[str]:
    """Move nodes into a lane as one undo step, after what the lane already holds along the flow and centred across
    it; the lane and pool grow to fit. Returns the ids placed (a Group carries what it holds)."""
    workspace = self._scene_context.workspace_or_none()
    before = capture_swimlanes(self, workspace) if workspace is not None else None
    if workspace is None or before is None or lane_id not in before.lane_pool:
        return []
    pool_id = before.lane_pool[lane_id]
    orientation = before.pools[pool_id].orientation
    requested = [
        node_id
        for node_id in dict.fromkeys(str(value).strip() for value in node_ids)
        if node_id in workspace.nodes
        and not is_swimlane_type(workspace.nodes[node_id].type_id)
        and before.item_lane.get(node_id) != lane_id
    ]
    if not requested:
        return []
    scope = collect_group_scope(self, workspace, scope_node_ids(workspace, self._scene_context.scope_path), dict(workspace.nodes))
    lane_frame = swimlane_frame_rect(scope.rects[lane_id], orientation)
    requested_set = set(requested)
    held = [
        swimlane_frame_rect(scope.rects[item_id], orientation)
        for item_id, owner in before.item_lane.items()
        if owner == lane_id and item_id in scope.rects and item_id not in requested_set
    ]
    cursor = max(
        (item.right + DEFAULT_TIDY_COLUMN_GAP for item in held),
        default=lane_frame.x + SWIMLANE_LANE_HEADER + SWIMLANE_CONTENT_PADDING,
    )
    center_v = lane_frame.y + lane_frame.height * 0.5
    positions: dict[str, tuple[float, float]] = {}
    placed: list[str] = []
    for node_id in requested:
        rect = scope.rects.get(node_id)
        if rect is None:
            continue
        frame = swimlane_frame_rect(rect, orientation)
        target = swimlane_frame_rect(
            LayoutNodeBounds(node_id, cursor, center_v - frame.height * 0.5, frame.width, frame.height),
            orientation,
        )
        dx = target.x - rect.x
        dy = target.y - rect.y
        cursor += frame.width + DEFAULT_TIDY_COLUMN_GAP
        moved = [node_id]
        if node_id in scope.group_backdrop_ids:
            moved.extend(scope.contents(node_id))
        for moved_id in moved:
            node = workspace.nodes.get(moved_id)
            if node is not None and moved_id not in positions:
                positions[moved_id] = (float(node.x) + dx, float(node.y) + dy)
        placed.append(node_id)
    if not positions:
        return []
    history_group = self._scene_context.grouped_history_action(ACTION_ASSIGN_SWIMLANE_LANE, workspace)
    with history_group:
        mutations = self._record_mutations()
        for node_id, (x, y) in positions.items():
            mutations.set_node_position(node_id, x, y)
        settle_swimlanes(self, workspace, before, moved_ids=positions)
    self._scene_context.rebuild_models()
    return placed


def _restack_and_apply(
    self,
    workspace: WorkspaceData,
    scope: GroupScope,
    before: SwimlaneSnapshot,
    pool_id: str,
    lanes: Sequence[SwimlaneLaneState],
) -> None:
    pool = before.pools[pool_id]
    restack = restack_swimlane_pool(scope.rects[pool_id], pool.orientation, lanes)
    rects = dict(scope.rects)
    own_items = _pool_item_ids(before, pool_id)
    _place_restack(scope, rects, restack, own_items)
    updates = _SwimlaneUpdates()
    _collect_rect_updates(workspace, scope, scope.rects, rects, updates)
    _apply_updates(self, workspace, updates)
    settle_swimlanes(self, workspace, _with_lanes(before, pool_id, [lane.lane_id for lane in lanes]))


def _with_lanes(before: SwimlaneSnapshot, pool_id: str, lane_ids: Sequence[str]) -> SwimlaneSnapshot:
    """``before`` with a pool's lane list replaced (a lane just added joins the pool it was added to)."""
    pools = dict(before.pools)
    pools[pool_id] = SwimlanePoolSnapshot(pool_id=pool_id, orientation=before.pools[pool_id].orientation, lane_ids=list(lane_ids))
    lane_pool = dict(before.lane_pool)
    lane_pool.update({lane_id: pool_id for lane_id in lane_ids})
    return SwimlaneSnapshot(pools=pools, lane_pool=lane_pool, item_lane=dict(before.item_lane))


def describe_swimlane_pools(self) -> list[dict[str, Any]]:
    """The open scope's pools: orientation and each lane in stack order with what it holds (read-only).

    ``node_ids`` are a lane's top-level items (a Group counts once); ``contained_node_ids`` adds what those hold. A
    collapsed pool is listed without lanes (expand it to see them).
    """
    workspace = self._scene_context.workspace_or_none()
    if workspace is None or self._scene_context.registry is None:
        return []
    scope_ids = scope_node_ids(workspace, self._scene_context.scope_path)
    if not _scope_has_swimlanes(workspace, scope_ids):
        return []
    scope = collect_group_scope(self, workspace, scope_ids, dict(workspace.nodes))
    snapshot = _snapshot_from_scope(workspace, scope)
    hidden = hidden_node_ids(workspace.nodes)
    described: list[dict[str, Any]] = []
    for pool_id in sorted(scope_ids):
        node = workspace.nodes.get(pool_id)
        if node is None or pool_id in hidden or not is_swimlane_pool_type(node.type_id):
            continue
        pool = snapshot.pools.get(pool_id)
        lanes = []
        for lane_id in pool.lane_ids if pool is not None else ():
            lane = workspace.nodes[lane_id]
            lanes.append(
                {
                    "lane_node_id": lane_id,
                    "title": str(lane.title),
                    "node_ids": sorted(item_id for item_id, owner in snapshot.item_lane.items() if owner == lane_id),
                    "contained_node_ids": sorted(scope.contents(lane_id)),
                }
            )
        described.append(
            {
                "pool_node_id": pool_id,
                "title": str(node.title),
                "orientation": _orientation(workspace, pool_id),
                "collapsed": bool(node.collapsed),
                "lane_node_ids": [lane["lane_node_id"] for lane in lanes],
                "lanes": lanes,
            }
        )
    return described


# --- helpers -----------------------------------------------------------------------------------------------------


def _add_swimlane_node(
    self,
    workspace: WorkspaceData,
    type_id: str,
    rect: LayoutNodeBounds,
    *,
    orientation: str,
    parent_node_id: str | None,
    title: str | None = None,
) -> str:
    registry = self._scene_context.registry
    spec = registry.get_spec(type_id)
    properties = registry.default_properties(type_id)
    properties["orientation"] = normalize_swimlane_orientation(orientation)
    if title:
        properties["title"] = str(title)
    node = self._validated_mutations().add_node(
        type_id=type_id,
        title=str(properties.get("title", spec.display_name)),
        x=float(rect.x),
        y=float(rect.y),
        properties=properties,
        exposed_ports={port.key: port.exposed for port in spec.ports},
        parent_node_id=parent_node_id,
        custom_width=float(rect.width),
        custom_height=float(rect.height),
    )
    self._scene_context.sync_surface_title(node, spec)
    return node.node_id


def _active_pool_ids(workspace: WorkspaceData, scope: GroupScope, hidden: Collection[str]) -> list[str]:
    """Expanded, drawn pools of the scope (a collapsed pool is a pill holding its lanes; nothing to stack)."""
    return sorted(
        node_id
        for node_id in scope.group_backdrop_ids
        if node_id in workspace.nodes
        and node_id not in hidden
        and node_id not in scope.collapsed_ids
        and is_swimlane_pool_type(workspace.nodes[node_id].type_id)
    )


def _orientation(workspace: WorkspaceData, node_id: str) -> str:
    node = workspace.nodes.get(node_id)
    return normalize_swimlane_orientation(node.properties.get("orientation") if node is not None else None)


def _center(rect: LayoutNodeBounds) -> tuple[float, float]:
    return (rect.center_x, rect.center_y)


__all__ = [
    "SwimlanePoolSnapshot",
    "SwimlaneSnapshot",
    "add_swimlane_lane",
    "assign_nodes_to_swimlane_lane",
    "capture_swimlanes",
    "close_removed_swimlane_lanes",
    "create_swimlane_pool",
    "describe_swimlane_pools",
    "initialize_swimlane_pool",
    "insert_swimlane_lane",
    "move_swimlane_lane",
    "remove_swimlane_lane",
    "resize_swimlane_frame",
    "scope_has_swimlanes",
    "set_swimlane_pool_orientation",
    "settle_swimlanes",
    "swimlane_lane_removal_plan",
    "swimlane_pool_lane_ids",
]
