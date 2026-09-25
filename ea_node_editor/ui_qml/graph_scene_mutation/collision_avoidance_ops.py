# Purpose: Make room when something grows (a collapsed item, a Group or a settings group expanding): move the other objects of its level aside, grow the parent Group to fit, and repeat level by level up to the top level.
# Map: feature_routes/group_backdrops_peek_membership
# Tests: tests/test_group_backdrop_identity_membership.py, tests/test_graph_scene_bridge_bind_regression.py
from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from typing import Any

from ea_node_editor.app_preferences import normalize_expand_collision_avoidance_settings
from ea_node_editor.graph.group_backdrop_geometry import lists_to_clear
from ea_node_editor.graph.transform_layout_ops import (
    LayoutNodeBounds,
    build_collision_avoidance_position_updates,
    build_make_room_position_updates,
)
from ea_node_editor.graph.transform_tidy_layout import DEFAULT_TIDY_COLUMN_GAP, DEFAULT_TIDY_ROW_GAP
from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.ui_qml.graph_scene_mutation.group_scope import (
    GroupScope,
    collect_group_scope_for_node,
    grow_group_around,
    node_layout_bounds,
    rect_strictly_contains,
)

_LOCAL_RADIUS_BY_PRESET = {
    "small": 420.0,
    "medium": 760.0,
    "large": 1200.0,
}
_GAP_BY_PRESET = {
    "tight": 16.0,
    "normal": 32.0,
    "loose": 56.0,
}
_MOVE_TOLERANCE = 0.01
_REFUSAL_LOCKED_GROUP = "Can't expand: the locked Group “{title}” would have to grow."
_REFUSAL_NO_ROOM = "Can't expand: there is no room without moving nodes into or out of a Group."
_JOINED_LOCKED_HINT = "Locked node “{node}” joined Group “{group}”."


@dataclass(frozen=True, slots=True)
class ExpandRoomPreparation:
    """Captured before any mutation: the grower's scope and its drawn rectangle before it grows."""

    node_id: str
    scope: GroupScope
    grown_from: LayoutNodeBounds


@dataclass(frozen=True, slots=True)
class ExpandRoomUpdates:
    positions: dict[str, tuple[float, float]]
    geometries: dict[str, tuple[float, float, float, float]]
    joined_locked_node_ids: tuple[str, ...] = ()
    refusal: str = ""  # non-empty = apply nothing
    hint: str = ""  # shown after a successful expand (a locked node joined a Group)


@dataclass(slots=True, frozen=True)
class CollisionObject:
    """One pushable unit of a level: a node, or a Group with everything it contains."""

    object_id: str
    bounds: LayoutNodeBounds
    move_node_ids: tuple[str, ...]
    fixed: bool = False  # holds a locked node: an obstacle, never moved


def prepare_expand_room(self, node_id: str) -> ExpandRoomPreparation | None:
    model = self._scene_context.model
    if model is None or self._scene_context.registry is None:
        return None
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None or node_id not in workspace.nodes:
        return None
    scope = collect_group_scope_for_node(self, workspace, node_id, dict(workspace.nodes))
    grown_from = scope.rects.get(node_id)
    if grown_from is None:
        return None
    return ExpandRoomPreparation(node_id=node_id, scope=scope, grown_from=grown_from)


def expand_collision_avoidance_updates(
    self,
    node_id: str,
    *,
    grown_rect: LayoutNodeBounds | None = None,
    use_current_presentation_bounds: bool = False,
    preparation: ExpandRoomPreparation | None = None,
) -> ExpandRoomUpdates:
    """Positions and Group geometries that make room for ``node_id`` growing (see the Purpose banner).

    ``grown_rect`` is the grower's final rectangle when the caller knows it (an expanding Group grown around its
    strays); else the current presentation bounds (settings groups: the node is already mutated) or its expanded size.
    A non-empty ``refusal`` means nothing may change: a locked Group would have to grow, or membership would change.
    """
    empty = ExpandRoomUpdates(positions={}, geometries={})
    model = self._scene_context.model
    registry = self._scene_context.registry
    if model is None or registry is None:
        return empty
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return empty
    node = workspace.nodes.get(node_id)
    if node is None:
        return empty
    preparation = preparation or prepare_expand_room(self, node_id)
    if preparation is None:
        return empty
    grown_to = grown_rect
    if grown_to is None and use_current_presentation_bounds:
        grown_to = _current_presentation_bounds(self, node_id)
    if grown_to is None:
        spec = registry.spec_or_none(node.type_id)
        if spec is None:
            return empty
        grown_to = node_layout_bounds(self, workspace, node, spec, expanded=True)
    if grown_to is None:
        return empty
    settings = normalize_expand_collision_avoidance_settings(self._scene_context.graphics_expand_collision_avoidance)
    return _make_room_level_by_level(
        workspace,
        preparation.scope,
        node_id=node_id,
        grown_from=preparation.grown_from,
        grown_to=grown_to,
        settings=settings,
        interact_with_locked=bool(self._scope_selection.interact_with_locked_objects),
    )


def _make_room_level_by_level(
    workspace: WorkspaceData,
    scope: GroupScope,
    *,
    node_id: str,
    grown_from: LayoutNodeBounds,
    grown_to: LayoutNodeBounds,
    settings: Mapping[str, Any],
    interact_with_locked: bool,
) -> ExpandRoomUpdates:
    push_enabled = bool(settings.get("enabled", True)) and (
        str(settings.get("scope", "all_movable")).strip().lower() == "all_movable"
    )
    nearest = str(settings.get("strategy", "make_room")).strip().lower() == "nearest"
    gap = _gap_for_settings(settings)

    def is_locked(candidate_id: str) -> bool:
        candidate = workspace.nodes.get(candidate_id)
        return candidate is not None and bool(candidate.locked) and not interact_with_locked

    rects = dict(scope.rects)
    rects[node_id] = grown_to
    frozen = {node_id, *scope.contents(node_id)}
    moved_objects: dict[str, CollisionObject] = {}
    geometries: dict[str, tuple[float, float, float, float]] = {}
    joined_locked: dict[str, str] = {}  # locked object -> the Group it joins
    grower, grower_from, grower_to = node_id, grown_from, grown_to
    visited_growers = {node_id}
    while True:
        owner_id = scope.owner(grower)
        if owner_id in visited_growers:
            break  # corrupted lists formed an owner cycle
        objects = level_collision_objects(scope, rects, owner_id, frozen, is_locked=is_locked)
        final = {item.object_id: item.bounds for item in objects}
        movable = [item for item in objects if not item.fixed]
        obstacles = [item.bounds for item in objects if item.fixed]
        if push_enabled and movable:
            if nearest:
                reach = _reach_radius_for_settings(settings) if owner_id is None else None
                _place(final, build_collision_avoidance_position_updates(
                    fixed_bounds=[grower_to, *obstacles],
                    movable_bounds=[item.bounds for item in movable],
                    gap=gap,
                    reach_radius=reach,
                ))
            else:
                _make_room_pushes(final, movable, obstacles, grower_from, grower_to, gap)
        if grower in scope.group_backdrop_ids:
            # Whatever would end up inside a growing Group joins it: move it out (even with the push off); a locked
            # object stays and joins.
            intruders = [
                final[item.object_id]
                for item in movable
                if rect_strictly_contains(grower_to, scope.membership_rect(item.object_id, final[item.object_id]))
            ]
            if intruders:
                _place(final, build_collision_avoidance_position_updates(
                    fixed_bounds=[grower_to, *obstacles],
                    movable_bounds=intruders,
                    gap=gap,
                ))
            joined_locked.update(
                (item.object_id, grower)
                for item in objects
                if item.fixed and rect_strictly_contains(grower_to, scope.membership_rect(item.object_id, item.bounds))
            )
        changed = [grower]
        for item in movable:
            new_bounds = final[item.object_id]
            dx = new_bounds.x - item.bounds.x
            dy = new_bounds.y - item.bounds.y
            if abs(dx) < _MOVE_TOLERANCE and abs(dy) < _MOVE_TOLERANCE:
                continue
            for move_id in item.move_node_ids:
                if move_id in rects:
                    rects[move_id] = rects[move_id].translated(dx, dy)
            moved_objects[item.object_id] = item
            changed.append(item.object_id)
        if owner_id is None:
            break
        if owner_id in scope.expanded_rects:
            # The grower is held by a collapsed Group (Peek, automation): grow its expanded size right and down only, so
            # its pill (at its top-left) never moves; a member left or above stays a held stray.
            owner_to = grow_group_around(
                scope,
                rects,
                owner_id,
                changed,
                base_rect=scope.expanded_rects[owner_id],
                keep_top_left=True,
            )
            if owner_to is not None:
                if is_locked(owner_id):
                    return _refused(_REFUSAL_LOCKED_GROUP.format(title=_title(workspace, owner_id)))
                geometries[owner_id] = (owner_to.x, owner_to.y, owner_to.width, owner_to.height)
            break
        owner_to = grow_group_around(scope, rects, owner_id, changed)
        if owner_to is None:
            break
        if is_locked(owner_id):
            return _refused(_REFUSAL_LOCKED_GROUP.format(title=_title(workspace, owner_id)))
        geometries[owner_id] = (owner_to.x, owner_to.y, owner_to.width, owner_to.height)
        visited_growers.add(owner_id)
        grower, grower_from, grower_to = owner_id, rects[owner_id], owner_to
        rects[owner_id] = owner_to
        frozen.update((owner_id, *scope.contents(owner_id)))

    expanding_group = node_id in scope.collapsed_ids
    final_membership = scope.membership_at(
        rects,
        list_overrides={group_id: None for group_id in lists_to_clear(workspace.nodes, node_id)} if expanding_group else None,
        collapsed_overrides={node_id: False} if expanding_group else None,
    )
    # Allowed owner changes: a joined locked object moves into the Group it joins, and a node the expanding Group held
    # becomes a geometric member of that Group or of a Group inside it. Anything else would move a node into or out of
    # another Group.
    held = set(scope.member_lists.get(node_id, ())) if expanding_group else set()
    for changed_id, membership in final_membership.items():
        new_owner = membership.owner_backdrop_id or None
        if new_owner == scope.owner(changed_id):
            continue
        if joined_locked.get(changed_id) == new_owner:
            continue
        if changed_id in held and (new_owner == node_id or new_owner in held):
            continue
        return _refused(_REFUSAL_NO_ROOM)

    positions: dict[str, tuple[float, float]] = {}
    for item in moved_objects.values():
        for move_id in item.move_node_ids:
            node = workspace.nodes.get(move_id)
            if node is None or move_id in geometries:
                continue
            dx = rects[item.object_id].x - item.bounds.x
            dy = rects[item.object_id].y - item.bounds.y
            positions[move_id] = (float(node.x) + dx, float(node.y) + dy)
    joined_ids = tuple(sorted(joined_locked))
    return ExpandRoomUpdates(
        positions=positions,
        geometries=geometries,
        joined_locked_node_ids=joined_ids,
        hint=(
            _JOINED_LOCKED_HINT.format(
                node=_title(workspace, joined_ids[0]),
                group=_title(workspace, joined_locked[joined_ids[0]]),
            )
            if joined_ids
            else ""
        ),
    )


def _make_room_pushes(
    final: dict[str, LayoutNodeBounds],
    movable: list[CollisionObject],
    obstacles: list[LayoutNodeBounds],
    grower_from: LayoutNodeBounds,
    grower_to: LayoutNodeBounds,
    gap: float,
) -> None:
    shifted = build_make_room_position_updates(
        grown_from=grower_from,
        grown_to=grower_to,
        movable_bounds=[item.bounds for item in movable],
        gap=gap,
        keep_gap_x=DEFAULT_TIDY_COLUMN_GAP,
        keep_gap_y=DEFAULT_TIDY_ROW_GAP,
    )
    _place(final, shifted)
    # Pass 1: a shifted box never lands on a locked obstacle.
    hitting = [final[object_id] for object_id in sorted(shifted) if _near_any(final[object_id], obstacles, gap)]
    if hitting:
        _place(final, build_collision_avoidance_position_updates(
            fixed_bounds=[grower_to, *obstacles],
            movable_bounds=hitting,
            gap=gap,
        ))
    # Pass 2: what the shift left in place and still crowds the grower, an obstacle or a shifted box moves to its
    # nearest free spot; the shifted boxes are blockers (they already moved).
    unshifted = [final[item.object_id] for item in movable if item.object_id not in shifted]
    if unshifted:
        _place(final, build_collision_avoidance_position_updates(
            fixed_bounds=[grower_to, *obstacles, *(final[object_id] for object_id in sorted(shifted))],
            movable_bounds=unshifted,
            gap=gap,
        ))


def level_collision_objects(
    scope: GroupScope,
    rects: Mapping[str, LayoutNodeBounds],
    owner_id: str | None,
    frozen_ids: Collection[str],
    *,
    is_locked: Callable[[str], bool],
) -> list[CollisionObject]:
    """The top-most objects owned by ``owner_id`` (``None`` = top level), each at its drawn rectangle.

    A Group carries everything it contains (a collapsed Group is its pill and carries what it holds). Objects in, or
    holding something in, ``frozen_ids`` are skipped; objects holding a locked node are fixed.
    """
    frozen = set(frozen_ids)
    objects: list[CollisionObject] = []
    for object_id in sorted(scope.rects):
        if object_id in frozen or scope.owner(object_id) != owner_id or object_id not in rects:
            continue
        move_ids = (object_id, *scope.contents(object_id)) if object_id in scope.group_backdrop_ids else (object_id,)
        if frozen.intersection(move_ids):
            continue
        objects.append(
            CollisionObject(
                object_id=object_id,
                bounds=rects[object_id],
                move_node_ids=move_ids,
                fixed=any(is_locked(move_id) for move_id in move_ids),
            )
        )
    return objects


def _place(final: dict[str, LayoutNodeBounds], updates: Mapping[str, tuple[float, float]]) -> None:
    for object_id, (x, y) in updates.items():
        bounds = final[object_id]
        final[object_id] = LayoutNodeBounds(node_id=object_id, x=float(x), y=float(y), width=bounds.width, height=bounds.height)


def _near_any(bounds: LayoutNodeBounds, blockers: list[LayoutNodeBounds], gap: float) -> bool:
    return any(
        bounds.left < blocker.right + gap
        and bounds.right > blocker.left - gap
        and bounds.top < blocker.bottom + gap
        and bounds.bottom > blocker.top - gap
        for blocker in blockers
    )


def _refused(reason: str) -> ExpandRoomUpdates:
    return ExpandRoomUpdates(positions={}, geometries={}, refusal=reason)


def _title(workspace: WorkspaceData, node_id: str) -> str:
    node = workspace.nodes.get(node_id)
    return (str(node.title).strip() if node is not None else "") or "Group"


def _current_presentation_bounds(self, node_id: str) -> LayoutNodeBounds | None:
    context = self._scene_context
    model = context.model
    registry = context.registry
    workspace = context.workspace_or_none()
    if model is None or registry is None or workspace is None:
        return None
    try:
        nodes, backdrops, _minimap = context._payload_builder.build_node_payloads_for_ids(
            model=model,
            registry=registry,
            workspace_id=workspace.workspace_id,
            scope_path=context.scope_path,
            node_ids={node_id},
            graph_theme_bridge=context.graph_theme_bridge,
            show_port_labels=context.graphics_show_port_labels,
            graph_label_pixel_size=context.graphics_graph_label_pixel_size,
            graph_node_icon_pixel_size=context.graphics_node_title_icon_pixel_size,
            lightweight_canvas=context.graphics_lightweight_canvas,
        )
    except Exception:  # noqa: BLE001
        return None
    payload = next(
        (item for item in (*nodes, *backdrops) if str(item.get("node_id", "")) == node_id),
        None,
    )
    if payload is None:
        return None
    try:
        return LayoutNodeBounds(
            node_id=node_id,
            x=float(payload["x"]),
            y=float(payload["y"]),
            width=max(1.0, float(payload["width"])),
            height=max(1.0, float(payload["height"])),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _gap_for_settings(settings: Mapping[str, Any]) -> float:
    preset = str(settings.get("gap_preset", "normal")).strip().lower()
    return _GAP_BY_PRESET.get(preset, _GAP_BY_PRESET["normal"])


def _reach_radius_for_settings(settings: Mapping[str, Any]) -> float | None:
    radius_mode = str(settings.get("radius_mode", "local")).strip().lower()
    if radius_mode == "unbounded":
        return None
    preset = str(settings.get("local_radius_preset", "medium")).strip().lower()
    return _LOCAL_RADIUS_BY_PRESET.get(preset, _LOCAL_RADIUS_BY_PRESET["medium"])


__all__ = [
    "CollisionObject",
    "ExpandRoomPreparation",
    "ExpandRoomUpdates",
    "expand_collision_avoidance_updates",
    "level_collision_objects",
    "prepare_expand_room",
]
