from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ea_node_editor.app_preferences import normalize_expand_collision_avoidance_settings
from ea_node_editor.graph.comment_backdrop_geometry import (
    CommentBackdropCandidate,
    CommentBackdropMembership,
    build_comment_backdrop_occupied_bounds,
    compute_comment_backdrop_membership,
)
from ea_node_editor.graph.hierarchy import node_scope_path, scope_node_ids
from ea_node_editor.graph.model import NodeInstance, WorkspaceData
from ea_node_editor.graph.transform_layout_ops import (
    LayoutNodeBounds,
    build_expand_collision_avoidance_position_updates,
)

if TYPE_CHECKING:
    from ea_node_editor.nodes.types import NodeTypeSpec

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


@dataclass(slots=True, frozen=True)
class _CollisionObject:
    object_id: str
    bounds: LayoutNodeBounds
    move_node_ids: tuple[str, ...]


def expand_collision_avoidance_updates(self, node_id: str) -> dict[str, tuple[float, float]]:
    settings = normalize_expand_collision_avoidance_settings(
        self._scene_context.graphics_expand_collision_avoidance
    )
    if not bool(settings.get("enabled", True)):
        return {}
    if str(settings.get("strategy", "nearest")).strip().lower() != "nearest":
        return {}
    if str(settings.get("scope", "all_movable")).strip().lower() != "all_movable":
        return {}

    model = self._scene_context.model
    registry = self._scene_context.registry
    if model is None or registry is None:
        return {}
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return {}
    node = workspace.nodes.get(node_id)
    if node is None:
        return {}
    spec = registry.spec_or_none(node.type_id)
    if spec is None:
        return {}

    membership_by_id, comment_backdrop_ids = _comment_backdrop_membership_for_scope(self, workspace, node_id)
    fixed_bounds, fixed_node_ids = _expanded_fixed_bounds(
        self,
        workspace=workspace,
        node=node,
        spec=spec,
        membership_by_id=membership_by_id,
        comment_backdrop_ids=comment_backdrop_ids,
    )
    if fixed_bounds is None:
        return {}

    collision_objects = _collision_objects_for_scope(
        self,
        workspace=workspace,
        expanding_node_id=node_id,
        fixed_node_ids=fixed_node_ids,
        membership_by_id=membership_by_id,
        comment_backdrop_ids=comment_backdrop_ids,
    )
    if not collision_objects:
        return {}

    gap = _gap_for_settings(settings)
    reach_radius = _reach_radius_for_settings(settings)
    object_updates = build_expand_collision_avoidance_position_updates(
        fixed_bounds=fixed_bounds,
        movable_bounds=[item.bounds for item in collision_objects],
        gap=gap,
        reach_radius=reach_radius,
    )
    if not object_updates:
        return {}

    updates: dict[str, tuple[float, float]] = {}
    for collision_object in collision_objects:
        final_position = object_updates.get(collision_object.object_id)
        if final_position is None:
            continue
        dx = float(final_position[0]) - float(collision_object.bounds.x)
        dy = float(final_position[1]) - float(collision_object.bounds.y)
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            continue
        for move_node_id in collision_object.move_node_ids:
            if move_node_id == node_id:
                continue
            moved_node = workspace.nodes.get(move_node_id)
            if moved_node is None:
                continue
            updates[move_node_id] = (float(moved_node.x) + dx, float(moved_node.y) + dy)
    return updates


def _expanded_fixed_bounds(
    self,
    *,
    workspace: WorkspaceData,
    node: NodeInstance,
    spec: "NodeTypeSpec",
    membership_by_id: dict[str, CommentBackdropMembership],
    comment_backdrop_ids: set[str],
) -> tuple[LayoutNodeBounds | None, set[str]]:
    expanded_bounds = _node_layout_bounds(self, workspace, node, spec, expanded=True)
    if expanded_bounds is None:
        return None, {node.node_id}
    if node.node_id not in comment_backdrop_ids:
        return expanded_bounds, {node.node_id}

    membership = membership_by_id.get(node.node_id)
    if membership is None:
        return expanded_bounds, {node.node_id}
    direct_member_ids = [*membership.member_node_ids, *membership.member_backdrop_ids]
    member_candidates = _comment_candidates_for_node_ids(
        self,
        workspace=workspace,
        node_ids=direct_member_ids,
        expanded=False,
    )
    occupied = build_comment_backdrop_occupied_bounds(
        _candidate_from_bounds(expanded_bounds, is_backdrop=True, workspace=workspace),
        member_candidates,
    )
    fixed_ids = {
        node.node_id,
        *membership.member_node_ids,
        *membership.member_backdrop_ids,
        *membership.contained_node_ids,
        *membership.contained_backdrop_ids,
    }
    return (
        LayoutNodeBounds(
            node_id=node.node_id,
            x=float(occupied.x),
            y=float(occupied.y),
            width=float(occupied.width),
            height=float(occupied.height),
        ),
        fixed_ids,
    )


def _collision_objects_for_scope(
    self,
    *,
    workspace: WorkspaceData,
    expanding_node_id: str,
    fixed_node_ids: set[str],
    membership_by_id: dict[str, CommentBackdropMembership],
    comment_backdrop_ids: set[str],
) -> list[_CollisionObject]:
    registry = self._scene_context.registry
    if registry is None:
        return []
    scope_path = node_scope_path(workspace, expanding_node_id)
    objects: list[_CollisionObject] = []
    moved_node_ids: set[str] = set()
    for candidate_id in scope_node_ids(workspace, scope_path):
        if candidate_id in fixed_node_ids:
            continue
        membership = membership_by_id.get(candidate_id)
        if membership is not None and membership.owner_backdrop_id:
            continue
        node = workspace.nodes.get(candidate_id)
        if node is None:
            continue
        spec = registry.spec_or_none(node.type_id)
        if spec is None:
            continue
        if candidate_id in comment_backdrop_ids:
            object_membership = membership_by_id.get(candidate_id)
            move_ids = _comment_move_ids(candidate_id, object_membership)
            if expanding_node_id in move_ids or fixed_node_ids.intersection(move_ids):
                continue
            bounds = _comment_occupied_bounds_for_node(
                self,
                workspace=workspace,
                node=node,
                membership=object_membership,
                expanded=False,
            )
        else:
            move_ids = (candidate_id,)
            bounds = _node_layout_bounds(self, workspace, node, spec, expanded=False)
        if bounds is None or moved_node_ids.intersection(move_ids):
            continue
        moved_node_ids.update(move_ids)
        objects.append(_CollisionObject(object_id=candidate_id, bounds=bounds, move_node_ids=move_ids))
    return objects


def _comment_move_ids(
    backdrop_id: str,
    membership: CommentBackdropMembership | None,
) -> tuple[str, ...]:
    if membership is None:
        return (backdrop_id,)
    return (
        backdrop_id,
        *membership.contained_backdrop_ids,
        *membership.contained_node_ids,
    )


def _comment_occupied_bounds_for_node(
    self,
    *,
    workspace: WorkspaceData,
    node: NodeInstance,
    membership: CommentBackdropMembership | None,
    expanded: bool,
) -> LayoutNodeBounds | None:
    registry = self._scene_context.registry
    if registry is None:
        return None
    spec = registry.spec_or_none(node.type_id)
    if spec is None:
        return None
    backdrop_bounds = _node_layout_bounds(self, workspace, node, spec, expanded=expanded)
    if backdrop_bounds is None:
        return None
    direct_member_ids = [] if membership is None else [*membership.member_node_ids, *membership.member_backdrop_ids]
    member_candidates = _comment_candidates_for_node_ids(
        self,
        workspace=workspace,
        node_ids=direct_member_ids,
        expanded=False,
    )
    occupied = build_comment_backdrop_occupied_bounds(
        _candidate_from_bounds(backdrop_bounds, is_backdrop=True, workspace=workspace),
        member_candidates,
    )
    return LayoutNodeBounds(
        node_id=node.node_id,
        x=float(occupied.x),
        y=float(occupied.y),
        width=float(occupied.width),
        height=float(occupied.height),
    )


def _comment_backdrop_membership_for_scope(
    self,
    workspace: WorkspaceData,
    node_id: str,
) -> tuple[dict[str, CommentBackdropMembership], set[str]]:
    registry = self._scene_context.registry
    if registry is None:
        return {}, set()
    candidates: list[CommentBackdropCandidate] = []
    comment_backdrop_ids: set[str] = set()
    scope_path = node_scope_path(workspace, node_id)
    for candidate_id in scope_node_ids(workspace, scope_path):
        node = workspace.nodes.get(candidate_id)
        if node is None:
            continue
        spec = registry.spec_or_none(node.type_id)
        if spec is None:
            continue
        is_backdrop = _is_comment_backdrop_spec(spec)
        if is_backdrop:
            comment_backdrop_ids.add(candidate_id)
        bounds = _node_layout_bounds(
            self,
            workspace,
            node,
            spec,
            expanded=is_backdrop,
        )
        if bounds is None:
            continue
        candidates.append(_candidate_from_bounds(bounds, is_backdrop=is_backdrop, workspace=workspace))
    return compute_comment_backdrop_membership(candidates), comment_backdrop_ids


def _comment_candidates_for_node_ids(
    self,
    *,
    workspace: WorkspaceData,
    node_ids: list[str],
    expanded: bool,
) -> list[CommentBackdropCandidate]:
    registry = self._scene_context.registry
    if registry is None:
        return []
    candidates: list[CommentBackdropCandidate] = []
    for node_id in node_ids:
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        spec = registry.spec_or_none(node.type_id)
        if spec is None:
            continue
        bounds = _node_layout_bounds(self, workspace, node, spec, expanded=expanded)
        if bounds is None:
            continue
        candidates.append(
            _candidate_from_bounds(
                bounds,
                is_backdrop=_is_comment_backdrop_spec(spec),
                workspace=workspace,
            )
        )
    return candidates


def _node_layout_bounds(
    self,
    workspace: WorkspaceData,
    node: NodeInstance,
    spec: "NodeTypeSpec",
    *,
    expanded: bool,
) -> LayoutNodeBounds | None:
    probe = node.clone()
    if expanded:
        probe.collapsed = False
    workspace_nodes = dict(workspace.nodes)
    workspace_nodes[node.node_id] = probe
    try:
        width, height = self._boundary_adapters.node_size(
            probe,
            spec,
            workspace_nodes,
            show_port_labels=self._scene_context.graphics_show_port_labels,
        )
    except Exception:  # noqa: BLE001
        return None
    return LayoutNodeBounds(
        node_id=node.node_id,
        x=float(node.x),
        y=float(node.y),
        width=max(1.0, float(width)),
        height=max(1.0, float(height)),
    )


def _candidate_from_bounds(
    bounds: LayoutNodeBounds,
    *,
    is_backdrop: bool,
    workspace: WorkspaceData,
) -> CommentBackdropCandidate:
    return CommentBackdropCandidate(
        node_id=bounds.node_id,
        scope_path=node_scope_path(workspace, bounds.node_id),
        is_backdrop=is_backdrop,
        x=float(bounds.x),
        y=float(bounds.y),
        width=float(bounds.width),
        height=float(bounds.height),
    )


def _is_comment_backdrop_spec(spec: "NodeTypeSpec") -> bool:
    return str(spec.surface_family or "").strip() == "comment_backdrop"


def _gap_for_settings(settings: dict[str, Any]) -> float:
    preset = str(settings.get("gap_preset", "normal")).strip().lower()
    return _GAP_BY_PRESET.get(preset, _GAP_BY_PRESET["normal"])


def _reach_radius_for_settings(settings: dict[str, Any]) -> float | None:
    radius_mode = str(settings.get("radius_mode", "local")).strip().lower()
    if radius_mode == "unbounded":
        return None
    preset = str(settings.get("local_radius_preset", "medium")).strip().lower()
    return _LOCAL_RADIUS_BY_PRESET.get(preset, _LOCAL_RADIUS_BY_PRESET["medium"])


__all__ = ["expand_collision_avoidance_updates"]
