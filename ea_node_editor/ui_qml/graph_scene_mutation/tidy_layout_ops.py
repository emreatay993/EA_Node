# Purpose: Scene Tidy command: collect drawn items/wires, run the pure Tidy layout, refit group backdrops, guard membership, push neighbours, apply as one undo step.
# Map: feature_routes/graph_actions_and_context_menus
# Tests: tests/test_graph_scene_tidy_layout.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ea_node_editor.app_preferences import normalize_expand_collision_avoidance_settings
from ea_node_editor.graph.hierarchy import scope_node_ids
from ea_node_editor.graph.records import EdgeInstance
from ea_node_editor.graph.transform_layout_ops import (
    LayoutNodeBounds,
    build_collision_avoidance_position_updates,
)
from ea_node_editor.graph.transform_tidy_layout import (
    DEFAULT_TIDY_COLUMN_GAP,
    DEFAULT_TIDY_ROW_GAP,
    TIDY_DIRECTION_AUTO,
    TIDY_DIRECTIONS,
    TIDY_MODE_AUTO_LAYOUT,
    TIDY_MODE_IN_PLACE,
    TIDY_MODES,
    TidyItem,
    TidyLayoutResult,
    TidySettings,
    TidyWire,
    build_tidy_layout,
    resolve_tidy_direction,
)
from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.ui.shell.runtime_history import ACTION_MOVE_NODE
from ea_node_editor.ui_qml.graph_geometry.route_endpoints import port_scene_pos
from ea_node_editor.ui_qml.graph_scene_mutation.alignment_and_distribution_ops import _straighten_port_side
from ea_node_editor.ui_qml.graph_scene_mutation.collision_avoidance_ops import (
    _gap_for_settings,
    _reach_radius_for_settings,
    level_collision_objects,
)
from ea_node_editor.ui_qml.graph_scene_mutation.group_scope import (
    GroupScope,
    collect_group_scope,
    grow_owner_chain,
)

_ANNOTATION_TYPE_PREFIX = "passive.annotation."
_UPDATE_TOLERANCE = 0.01
_WIRE_SIDES = frozenset({"left", "right", "top", "bottom"})
_TOP_BLOCK_ID = "\x00tidy_block"


@dataclass(slots=True)
class _TidyPartition:
    """Tidy items sharing one owner outside the tidy set (``None`` = top level), laid out in one call."""

    owner_id: str | None
    items: list[TidyItem] = field(default_factory=list)
    wires: list[TidyWire] = field(default_factory=list)
    node_ids: set[str] = field(default_factory=set)  # items plus the hidden members of their collapsed groups


def tidy_layout(
    self,
    node_ids: list[Any] | None,
    *,
    mode: str = TIDY_MODE_AUTO_LAYOUT,
    direction: str = TIDY_DIRECTION_AUTO,
    column_gap: float = DEFAULT_TIDY_COLUMN_GAP,
    row_gap: float = DEFAULT_TIDY_ROW_GAP,
) -> dict[str, Any] | None:
    """Tidy ``node_ids`` (``None`` = every drawn node of the open scope) as one undo step.

    Returns ``None`` when nothing can be tidied, else an outcome dict (see ``_outcome``).
    """
    normalized_mode = _normalized_choice(mode, TIDY_MODES, "mode")
    normalized_direction = _normalized_choice(direction, TIDY_DIRECTIONS, "direction")
    model = self._scene_context.model
    registry = self._scene_context.registry
    if model is None or registry is None:
        return None
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return None

    bridge = self._scene_context._bridge
    drawn_ids = {str(row.get("node_id", "")) for row in bridge.nodes_model}
    drawn_ids.update(str(row.get("node_id", "")) for row in bridge.backdrop_nodes_model)
    rows_by_edge_id = {str(row.get("edge_id", "")): row for row in bridge.edges_model}
    scope_ids = scope_node_ids(workspace, self._scene_context.scope_path)
    if node_ids is None:
        requested_ids = [node_id for node_id in scope_ids if node_id in drawn_ids]
    else:
        requested_ids = _unique_node_ids(node_ids)
    selected_ids = self._scope_selection.normalized_selected_node_ids(
        workspace,
        [node_id for node_id in requested_ids if node_id in drawn_ids],
    )
    if not selected_ids:
        return None

    workspace_nodes = dict(workspace.nodes)
    scope = collect_group_scope(self, workspace, scope_ids, workspace_nodes)
    tidy_ids, fixed_obstacle_ids = _expand_tidy_set(self, workspace, scope, selected_ids)
    item_ids = {node_id for node_id in tidy_ids if node_id in drawn_ids}
    partitions = _build_partitions(
        self,
        workspace,
        scope,
        item_ids,
        rows_by_edge_id,
    )
    if not partitions:
        return None

    all_wires = [wire for partition in partitions.values() for wire in partition.wires]
    auto_direction = resolve_tidy_direction(all_wires, TIDY_DIRECTION_AUTO)
    resolved_direction = auto_direction if normalized_direction == TIDY_DIRECTION_AUTO else normalized_direction
    settings = TidySettings(
        mode=normalized_mode,
        direction=resolved_direction,
        all_advance=normalized_direction not in (TIDY_DIRECTION_AUTO, auto_direction),
        column_gap=float(column_gap),
        row_gap=float(row_gap),
    )
    results = {
        owner_id: build_tidy_layout(partition.items, partition.wires, settings)
        for owner_id, partition in partitions.items()
    }
    if all(result.laid_out_level_count == 0 for result in results.values()):
        return None

    collision_settings = normalize_expand_collision_avoidance_settings(
        self._scene_context.graphics_expand_collision_avoidance
    )
    push_enabled = _push_enabled(collision_settings)
    gap = _gap_for_settings(collision_settings)
    tidy_node_ids = {node_id for partition in partitions.values() for node_id in partition.node_ids}
    final_rects = dict(scope.rects)
    final_expanded_rects: dict[str, LayoutNodeBounds] = {}  # collapsed owners grown around peeked members
    accepted: list[str | None] = []
    rejected_ids: set[str] = set()
    grown_owner_ids: set[str] = set()
    # Blocks inside unselected Groups first (deepest first) so their owners have grown before the top-level
    # block is kept clear of them.
    for owner_id in sorted(partitions, key=lambda key: _partition_order(scope, key)):
        partition = partitions[owner_id]
        tentative = dict(final_rects)
        _apply_partition_result(tentative, scope, partition, results[owner_id])
        _clear_fixed_obstacles(
            workspace,
            scope,
            tentative,
            partition,
            tidy_node_ids=tidy_node_ids,
            gap=gap,
        )
        tentative_expanded_rects = dict(final_expanded_rects)
        grown = grow_owner_chain(
            self,
            workspace,
            tentative,
            scope,
            owner_id,
            expanded_rects=tentative_expanded_rects,
        )
        if grown is None:
            rejected_ids.update(partition.node_ids)
            continue
        final_rects = tentative
        final_expanded_rects = tentative_expanded_rects
        grown_owner_ids.update(grown)
        accepted.append(owner_id)

    accepted_ids = {node_id for owner_id in accepted for node_id in partitions[owner_id].node_ids}
    pushed_ids = (
        _push_neighbours(
            workspace,
            scope,
            final_rects,
            collision_settings,
            top_partition=partitions.get(None) if None in accepted else None,
            fixed_ids=accepted_ids | grown_owner_ids,
            block_owner_ids={_top_level_ancestor(scope, owner_id) for owner_id in accepted if owner_id is not None},
        )
        if push_enabled
        else set()
    )

    arranged_ids = {
        item.item_id
        for owner_id in accepted
        if results[owner_id].laid_out_level_count > 0
        for item in partitions[owner_id].items
        if item.arrangeable
    }
    requested_known = {node_id for node_id in requested_ids if node_id in workspace.nodes}
    skipped_ids = (requested_known - accepted_ids) | fixed_obstacle_ids | rejected_ids
    loop_edge_ids = {wire_id for owner_id in accepted for wire_id in results[owner_id].loop_wire_ids}
    outcome_direction = "" if normalized_mode == TIDY_MODE_IN_PLACE else resolved_direction

    conflicts = scope.owner_changes(final_rects)
    if conflicts:
        return _outcome(
            changed=False,
            mode=normalized_mode,
            direction=outcome_direction,
            arranged=arranged_ids,
            skipped=skipped_ids,
            loop_edges=loop_edge_ids,
            conflicts=conflicts,
        )

    position_updates, geometry_updates = _node_updates(workspace, scope, final_rects)
    for group_id, rect in final_expanded_rects.items():
        position_updates.pop(group_id, None)
        geometry_updates[group_id] = (rect.x, rect.y, rect.width, rect.height)
    moved_ids = {
        node_id
        for node_id in (*position_updates, *geometry_updates)
        if abs(final_rects[node_id].x - scope.rects[node_id].x) >= _UPDATE_TOLERANCE
        or abs(final_rects[node_id].y - scope.rects[node_id].y) >= _UPDATE_TOLERANCE
    }
    changed = bool(position_updates or geometry_updates)
    if changed:
        history_group = self._scene_context.grouped_history_action(
            ACTION_MOVE_NODE,
            workspace,
            commit_if=lambda: changed,
        )
        mutations = self._record_mutations()
        with history_group:
            for node_id, (x, y) in position_updates.items():
                mutations.set_node_position(node_id, x, y)
            for node_id, (x, y, width, height) in geometry_updates.items():
                mutations.set_node_geometry(node_id, x, y, width, height)
        self._scene_context.rebuild_models()
    return _outcome(
        changed=changed,
        mode=normalized_mode,
        direction=outcome_direction,
        arranged=arranged_ids,
        moved=moved_ids & accepted_ids,
        resized=set(geometry_updates),
        pushed=(moved_ids & pushed_ids) - accepted_ids,
        skipped=skipped_ids,
        loop_edges=loop_edge_ids,
    )


def _outcome(
    *,
    changed: bool,
    mode: str,
    direction: str,
    arranged: set[str],
    moved: set[str] = frozenset(),
    resized: set[str] = frozenset(),
    pushed: set[str] = frozenset(),
    skipped: set[str] = frozenset(),
    loop_edges: set[str] = frozenset(),
    conflicts: set[str] = frozenset(),
) -> dict[str, Any]:
    return {
        "changed": bool(changed),
        "mode": mode,
        "direction": direction,
        "arranged_node_ids": sorted(arranged),
        "moved_node_ids": sorted(moved),
        "resized_group_ids": sorted(resized),
        "pushed_node_ids": sorted(pushed),
        "skipped_node_ids": sorted(skipped),
        "loop_edge_ids": sorted(loop_edges),
        "membership_conflict_node_ids": sorted(conflicts),
    }


def _expand_tidy_set(
    self,
    workspace: WorkspaceData,
    scope: GroupScope,
    selected_ids: list[str],
) -> tuple[set[str], set[str]]:
    """A selected Group backdrop pulls in its contents; one holding a node the user cannot select stays put."""
    tidy_ids = {node_id for node_id in selected_ids if node_id in scope.rects}
    fixed_obstacle_ids: set[str] = set()
    for backdrop_id in sorted(tidy_ids & scope.group_backdrop_ids):
        contents = scope.contents(backdrop_id)
        if not contents:
            continue
        selectable = set(self._scope_selection.normalized_selected_node_ids(workspace, contents))
        if any(node_id not in selectable for node_id in contents):
            fixed_obstacle_ids.add(backdrop_id)
            fixed_obstacle_ids.update(contents)
        else:
            tidy_ids.update(node_id for node_id in contents if node_id in scope.rects)
    return tidy_ids - fixed_obstacle_ids, fixed_obstacle_ids


def _build_partitions(
    self,
    workspace: WorkspaceData,
    scope: GroupScope,
    item_ids: set[str],
    rows_by_edge_id: Mapping[str, Mapping[str, Any]],
) -> dict[str | None, _TidyPartition]:
    def parent_item(node_id: str) -> str | None:
        owner_id = scope.owner(node_id)
        return owner_id if owner_id in item_ids else None

    def partition_key(node_id: str) -> str | None:
        owner_id = scope.owner(node_id)
        seen = {node_id}
        while owner_id is not None and owner_id in item_ids and owner_id not in seen:
            seen.add(owner_id)
            owner_id = scope.owner(owner_id)
        return owner_id

    def level_ancestor(node_id: str, level_parent_id: str | None) -> str | None:
        current = node_id
        seen = {node_id}
        while parent_item(current) != level_parent_id:
            current = parent_item(current)
            if current is None or current in seen:
                return None
            seen.add(current)
        return current

    # A collapsed Group is one rigid item at its pill (``scope.rects``) carrying what it holds.
    rigid_ids = item_ids & scope.collapsed_ids
    proxy_item_by_node_id: dict[str, str] = {}
    for rigid_id in sorted(rigid_ids):
        for content_id in scope.contents(rigid_id):
            proxy_item_by_node_id.setdefault(content_id, rigid_id)

    def resolve_endpoint(node_id: str) -> str | None:
        return node_id if node_id in item_ids else proxy_item_by_node_id.get(node_id)

    resolved_edges: list[tuple[EdgeInstance, str, str]] = []
    for edge_id in sorted(workspace.edges):
        edge = workspace.edges[edge_id]
        source_item = resolve_endpoint(edge.source_node_id)
        target_item = resolve_endpoint(edge.target_node_id)
        if source_item is None or target_item is None or source_item == target_item:
            continue
        if partition_key(source_item) != partition_key(target_item):
            continue
        resolved_edges.append((edge, source_item, target_item))

    def wired_at_own_level(node_id: str) -> bool:
        level_parent_id = parent_item(node_id)
        for _edge, source_item, target_item in resolved_edges:
            if node_id == source_item:
                other = level_ancestor(target_item, level_parent_id)
            elif node_id == target_item:
                other = level_ancestor(source_item, level_parent_id)
            else:
                continue
            if other is not None and other != node_id:
                return True
        return False

    partitions: dict[str | None, _TidyPartition] = {}
    for node_id in sorted(item_ids):
        node = workspace.nodes[node_id]
        rect = scope.rects[node_id]
        is_group = node_id in scope.group_backdrop_ids
        type_id = str(node.type_id or "")
        unwired_annotation = (
            not is_group and type_id.startswith(_ANNOTATION_TYPE_PREFIX) and not wired_at_own_level(node_id)
        )
        owner_id = partition_key(node_id)
        partition = partitions.setdefault(owner_id, _TidyPartition(owner_id=owner_id))
        partition.items.append(
            TidyItem(
                item_id=node_id,
                x=rect.x,
                y=rect.y,
                width=rect.width,
                height=rect.height,
                parent_group_id=parent_item(node_id),
                is_group=is_group,
                rigid=node_id in rigid_ids,
                arrangeable=not unwired_annotation,
            )
        )
        partition.node_ids.add(node_id)
        if node_id in rigid_ids:
            partition.node_ids.update(content_id for content_id in scope.contents(node_id) if content_id in scope.rects)

    for edge, source_item, target_item in resolved_edges:
        row = rows_by_edge_id.get(edge.edge_id)
        source_side = _wire_side(workspace, scope, row, edge, "source")
        target_side = _wire_side(workspace, scope, row, edge, "target")
        partitions[partition_key(source_item)].wires.append(
            TidyWire(
                wire_id=edge.edge_id,
                source_id=source_item,
                target_id=target_item,
                source_side=source_side,
                target_side=target_side,
                source_offset=_wire_offset(self, workspace, scope, row, edge, "source", source_item, source_side),
                target_offset=_wire_offset(self, workspace, scope, row, edge, "target", target_item, target_side),
            )
        )
    return partitions


def _wire_side(
    workspace: WorkspaceData,
    scope: GroupScope,
    row: Mapping[str, Any] | None,
    edge: EdgeInstance,
    end: str,
) -> str:
    """Side the drawn wire leaves from (port side, else anchor side), else the owner's in/out fallback."""
    if row is not None:
        for key in (f"{end}_port_side", f"{end}_anchor_side"):
            side = str(row.get(key) or "").strip().lower()
            if side in _WIRE_SIDES:
                return side
    node_id = edge.source_node_id if end == "source" else edge.target_node_id
    node = workspace.nodes.get(node_id)
    spec = scope.specs.get(node_id)
    if node is None or spec is None:
        return ""
    return _straighten_port_side(
        node=node,
        spec=spec,
        workspace_nodes=workspace.nodes,
        port_key=edge.source_port_key if end == "source" else edge.target_port_key,
    )


def _wire_offset(
    self,
    workspace: WorkspaceData,
    scope: GroupScope,
    row: Mapping[str, Any] | None,
    edge: EdgeInstance,
    end: str,
    item_id: str,
    side: str,
) -> tuple[float, float]:
    """Wire anchor relative to its item's top-left: the drawn anchor when the wire is drawn.

    A member hidden in a collapsed Group is drawn to the collapsed pill (the item's rectangle), whose anchor slides
    toward the other end; the centre of the pill side the port faces is the anchor a straightened wire keeps, so Tidy
    stays repeatable.
    """
    item_rect = scope.rects[item_id]
    endpoint_id = edge.source_node_id if end == "source" else edge.target_node_id
    if endpoint_id != item_id:
        pill = item_rect
        return {
            "left": (0.0, pill.height * 0.5),
            "right": (pill.width, pill.height * 0.5),
            "top": (pill.width * 0.5, 0.0),
            "bottom": (pill.width * 0.5, pill.height),
        }.get(side, (pill.width * 0.5, pill.height * 0.5))
    if row is not None:
        prefix = "s" if end == "source" else "t"
        try:
            return (float(row[f"{prefix}x"]) - item_rect.x, float(row[f"{prefix}y"]) - item_rect.y)
        except (KeyError, TypeError, ValueError):
            pass
    node_id = edge.source_node_id if end == "source" else edge.target_node_id
    node = workspace.nodes.get(node_id)
    spec = scope.specs.get(node_id)
    if node is not None and spec is not None:
        try:
            point = port_scene_pos(
                node,
                spec,
                edge.source_port_key if end == "source" else edge.target_port_key,
                workspace.nodes,
                show_port_labels=self._scene_context.graphics_show_port_labels,
                graph_label_pixel_size=self._scene_context.graphics_graph_label_pixel_size,
                graph_node_icon_pixel_size=self._scene_context.graphics_node_title_icon_pixel_size,
            )
        except (KeyError, ValueError):
            point = None
        if point is not None:
            return (float(point.x()) - item_rect.x, float(point.y()) - item_rect.y)
    return (item_rect.width * 0.5, item_rect.height * 0.5)


def _partition_order(scope: GroupScope, owner_id: str | None) -> tuple[int, int, str]:
    if owner_id is None:
        return (1, 0, "")
    depth = 0
    seen = {owner_id}
    current = scope.owner(owner_id)
    while current is not None and current not in seen:
        depth += 1
        seen.add(current)
        current = scope.owner(current)
    return (0, -depth, owner_id)


def _top_level_ancestor(scope: GroupScope, node_id: str) -> str:
    current = node_id
    seen = {node_id}
    owner_id = scope.owner(current)
    while owner_id is not None and owner_id not in seen:
        seen.add(owner_id)
        current = owner_id
        owner_id = scope.owner(current)
    return current


def _apply_partition_result(
    rects: dict[str, LayoutNodeBounds],
    scope: GroupScope,
    partition: _TidyPartition,
    result: TidyLayoutResult,
) -> None:
    for item in partition.items:
        position = result.positions.get(item.item_id)
        size = result.group_sizes.get(item.item_id)
        if position is None and size is None:
            continue
        original = rects[item.item_id]
        x, y = position if position is not None else (original.x, original.y)
        width, height = size if size is not None else (original.width, original.height)
        rects[item.item_id] = LayoutNodeBounds(node_id=item.item_id, x=x, y=y, width=width, height=height)
        if item.rigid and position is not None:
            dx = x - original.x
            dy = y - original.y
            for content_id in scope.contents(item.item_id):
                if content_id in rects:
                    rects[content_id] = rects[content_id].translated(dx, dy)


def _clear_fixed_obstacles(
    workspace: WorkspaceData,
    scope: GroupScope,
    rects: dict[str, LayoutNodeBounds],
    partition: _TidyPartition,
    *,
    tidy_node_ids: set[str],
    gap: float,
) -> None:
    """Shift a partition's laid-out block off the siblings nothing will move out of its way.

    Inside a Group nothing is pushed, so every other member is an obstacle. At the top level ordinary neighbours
    are left to the neighbour push (or, with it off, may be overlapped); only what the push never moves stays an
    obstacle: locked content and the backdrops that hold other tidied nodes (they grew first). Unwired annotations
    of the partition keep their place.
    """
    anchored_ids = {item.item_id for item in partition.items if item.parent_group_id is None and not item.arrangeable}
    block_rects = [
        rects[item.item_id] for item in partition.items if item.parent_group_id is None and item.arrangeable
    ]
    if not block_rects:
        return
    obstacles: list[LayoutNodeBounds] = []
    for node_id, rect in rects.items():
        if node_id in partition.node_ids or scope.owner(node_id) != partition.owner_id:
            continue
        if partition.owner_id is None and not _holds_fixed_content(workspace, scope, node_id, tidy_node_ids):
            continue
        obstacles.append(rect)
    if not obstacles or not any(
        block.left < obstacle.right + gap
        and block.right > obstacle.left - gap
        and block.top < obstacle.bottom + gap
        and block.bottom > obstacle.top - gap
        for block in block_rects
        for obstacle in obstacles
    ):
        return
    left = min(rect.left for rect in block_rects)
    top = min(rect.top for rect in block_rects)
    block = LayoutNodeBounds(
        node_id=_TOP_BLOCK_ID,
        x=left,
        y=top,
        width=max(rect.right for rect in block_rects) - left,
        height=max(rect.bottom for rect in block_rects) - top,
    )
    moved = build_collision_avoidance_position_updates(fixed_bounds=obstacles, movable_bounds=[block], gap=gap)
    if _TOP_BLOCK_ID not in moved:
        return
    dx = moved[_TOP_BLOCK_ID][0] - block.x
    dy = moved[_TOP_BLOCK_ID][1] - block.y
    for node_id in partition.node_ids - anchored_ids:
        if node_id in rects:
            rects[node_id] = rects[node_id].translated(dx, dy)


def _holds_fixed_content(workspace: WorkspaceData, scope: GroupScope, node_id: str, tidy_node_ids: set[str]) -> bool:
    """True for what the neighbour push never moves: locked content and backdrops holding tidied nodes."""
    ids = (node_id, *scope.contents(node_id)) if node_id in scope.group_backdrop_ids else (node_id,)
    return any(
        member_id in tidy_node_ids or bool(getattr(workspace.nodes.get(member_id), "locked", False))
        for member_id in ids
    )


def _push_enabled(settings: Mapping[str, Any]) -> bool:
    # Tidy's own push ignores the expand strategy (it always moves each neighbour to its nearest free spot).
    return (
        bool(settings.get("enabled", True))
        and str(settings.get("scope", "all_movable")).strip().lower() == "all_movable"
    )


def _push_neighbours(
    workspace: WorkspaceData,
    scope: GroupScope,
    rects: dict[str, LayoutNodeBounds],
    settings: Mapping[str, Any],
    *,
    top_partition: _TidyPartition | None,
    fixed_ids: set[str],
    block_owner_ids: set[str],
) -> set[str]:
    """Push top-level neighbours off the tidied nodes (each rectangle, not their bounding box) in one pass."""
    if not fixed_ids:
        return set()
    fixed = [rects[owner_id] for owner_id in sorted(block_owner_ids)]
    unwired_annotation_ids: list[str] = []
    if top_partition is not None:
        fixed.extend(
            rects[item.item_id]
            for item in top_partition.items
            if item.parent_group_id is None and item.arrangeable
        )
        unwired_annotation_ids = [
            item.item_id for item in top_partition.items if item.parent_group_id is None and not item.arrangeable
        ]
    if not fixed:
        return set()
    objects: list[tuple[str, LayoutNodeBounds, tuple[str, ...]]] = [
        (collision_object.object_id, collision_object.bounds, collision_object.move_node_ids)
        for collision_object in level_collision_objects(
            scope,
            scope.rects,
            None,
            fixed_ids,
            is_locked=lambda _node_id: False,
        )
    ]
    objects.extend((node_id, rects[node_id], (node_id,)) for node_id in unwired_annotation_ids)
    objects = [
        entry
        for entry in objects
        if not any(bool(getattr(workspace.nodes.get(node_id), "locked", False)) for node_id in entry[2])
    ]
    if not objects:
        return set()
    updates = build_collision_avoidance_position_updates(
        fixed_bounds=fixed,
        movable_bounds=[bounds for _object_id, bounds, _move_ids in objects],
        gap=_gap_for_settings(settings),
        reach_radius=_reach_radius_for_settings(settings),
    )
    pushed_ids: set[str] = set()
    for object_id, bounds, move_ids in objects:
        final_position = updates.get(object_id)
        if final_position is None:
            continue
        dx = float(final_position[0]) - bounds.x
        dy = float(final_position[1]) - bounds.y
        if abs(dx) < _UPDATE_TOLERANCE and abs(dy) < _UPDATE_TOLERANCE:
            continue
        for node_id in move_ids:
            if node_id in rects:
                rects[node_id] = rects[node_id].translated(dx, dy)
                pushed_ids.add(node_id)
    return pushed_ids


def _node_updates(
    workspace: WorkspaceData,
    scope: GroupScope,
    rects: Mapping[str, LayoutNodeBounds],
) -> tuple[dict[str, tuple[float, float]], dict[str, tuple[float, float, float, float]]]:
    position_updates: dict[str, tuple[float, float]] = {}
    geometry_updates: dict[str, tuple[float, float, float, float]] = {}
    for node_id in sorted(rects):
        rect = rects[node_id]
        original = scope.rects[node_id]
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        resized = node_id in scope.group_backdrop_ids and (
            abs(rect.width - original.width) >= _UPDATE_TOLERANCE
            or abs(rect.height - original.height) >= _UPDATE_TOLERANCE
        )
        if resized:
            geometry_updates[node_id] = (rect.x, rect.y, rect.width, rect.height)
        elif abs(rect.x - float(node.x)) >= _UPDATE_TOLERANCE or abs(rect.y - float(node.y)) >= _UPDATE_TOLERANCE:
            position_updates[node_id] = (rect.x, rect.y)
    return position_updates, geometry_updates


def _unique_node_ids(values: list[Any]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        node_id = str(value or "").strip()
        if node_id and node_id not in seen:
            seen.add(node_id)
            unique.append(node_id)
    return unique


def _normalized_choice(value: str, choices: tuple[str, ...], label: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in choices:
        raise ValueError(f"Unknown tidy {label}: {value!r}")
    return normalized


__all__ = ["tidy_layout"]
