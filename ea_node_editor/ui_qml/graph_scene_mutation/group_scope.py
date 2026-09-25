# Purpose: Scene geometry for Group membership in mutations: drawn and expanded rectangles, identity-aware membership (current or simulated), and Group growth.
# Map: feature_routes/group_backdrops_peek_membership
# Tests: tests/test_group_scope.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping

from ea_node_editor.graph.group_backdrop_geometry import (
    CORNER_CANDIDATE_SIZE,
    GROUP_BACKDROP_WRAP_BOTTOM_PADDING,
    GROUP_BACKDROP_WRAP_PADDING,
    GROUP_BACKDROP_WRAP_TOP_PADDING,
    MEMBERSHIP_RECT_CORNER,
    MEMBERSHIP_RECT_EXPANDED,
    GroupBackdropCandidate,
    GroupBackdropMembership,
    build_group_backdrop_wrap_bounds,
    compute_group_backdrop_membership,
    hidden_node_ids,
    honoured_held_member_ids,
    membership_rect_kind,
    strictly_contains as _strictly_contains,
)
from ea_node_editor.graph.hierarchy import node_scope_path, scope_node_ids
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.graph.transform_layout_ops import LayoutNodeBounds
from ea_node_editor.graph.workspace_state import WorkspaceData

if TYPE_CHECKING:
    from ea_node_editor.nodes.node_specs import NodeTypeSpec

_UPDATE_TOLERANCE = 0.01


def scene_layout_bounds(
    self,
    workspace: WorkspaceData,
    nodes: Iterable[NodeInstance],
    *,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
    expanded: bool = False,
) -> dict[str, LayoutNodeBounds]:
    """Each node's rectangle as the canvas draws it, or with ``expanded`` as it would be drawn expanded.

    A drawn node reads its cached payload; any other node (hidden, just added, or measured expanded) is measured the way
    a payload build sizes it, settings bands included, so Group layout never disagrees with the membership the payloads
    compute. Nodes without a spec are left out.
    """
    bounds: dict[str, LayoutNodeBounds] = {}
    pending: list[NodeInstance] = []
    for node in nodes:
        cached_bounds = None if expanded else _cached_node_layout_bounds(self, node.node_id)
        if cached_bounds is None:
            pending.append(node)
        else:
            bounds[node.node_id] = cached_bounds
    context = self._scene_context
    if pending and context.registry is not None:
        bounds.update(
            context._payload_builder.measure_node_layout_bounds(
                workspace=workspace,
                registry=context.registry,
                nodes=pending,
                workspace_nodes=workspace_nodes,
                show_port_labels=context.graphics_show_port_labels,
                graph_label_pixel_size=context.graphics_graph_label_pixel_size,
                graph_node_icon_pixel_size=context.graphics_node_title_icon_pixel_size,
                expanded=expanded,
            )
        )
    return bounds


def node_layout_bounds(
    self,
    workspace: WorkspaceData,
    node: NodeInstance,
    *,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
    expanded: bool,
) -> LayoutNodeBounds | None:
    """One node's :func:`scene_layout_bounds` (``None`` when its type is unknown)."""
    return scene_layout_bounds(
        self,
        workspace,
        [node],
        workspace_nodes=workspace_nodes,
        expanded=expanded,
    ).get(node.node_id)


def _cached_node_layout_bounds(self, node_id: str) -> LayoutNodeBounds | None:
    cache = self._scene_context._bridge._payload_cache
    if cache.dirty or not self._scene_context._payload_cache_sync.payload_cache_matches_active_view():
        return None
    if not cache.indexes_valid:
        cache.rebuild_indexes()
    status, location = cache.resolve_node_payload_slot(str(node_id or "").strip())
    if status != "ok" or location is None:
        return None
    collection_name, index = location
    collection = cache.nodes if collection_name == "nodes" else cache.backdrop_nodes
    payload = collection[index]
    try:
        x = float(payload.get("x", 0.0))
        y = float(payload.get("y", 0.0))
        width = max(1.0, float(payload.get("width", 0.0)))
        height = max(1.0, float(payload.get("height", 0.0)))
    except (TypeError, ValueError):
        return None
    return LayoutNodeBounds(
        node_id=str(node_id),
        x=x,
        y=y,
        width=width,
        height=height,
    )


def is_group_backdrop_spec(spec: "NodeTypeSpec") -> bool:
    return str(spec.surface_family or "").strip() == "group_backdrop"


def group_membership_for_scope(
    self,
    workspace: WorkspaceData,
    node_id: str,
    *,
    workspace_nodes: dict[str, NodeInstance],
) -> tuple[dict[str, GroupBackdropMembership], set[str]]:
    """Current membership of ``node_id``'s scope (``({}, set())`` when the scope holds no Group)."""
    registry = self._scene_context.registry
    if registry is None:
        return {}, set()
    scoped_node_ids = scope_node_ids(workspace, node_scope_path(workspace, node_id))
    if not any(
        (spec := registry.spec_or_none(workspace.nodes[candidate_id].type_id)) is not None
        and is_group_backdrop_spec(spec)
        for candidate_id in scoped_node_ids
    ):
        return {}, set()
    scope = collect_group_scope(self, workspace, scoped_node_ids, workspace_nodes)
    return scope.membership, scope.group_backdrop_ids


@dataclass(slots=True)
class GroupScope:
    """Every node of one scope at its drawn rectangle, plus the Group membership those rectangles give.

    ``rects`` is what layout sees: a collapsed Group is its pill, except an older collapsed Group without a member
    list, which keeps its expanded rectangle (today's area rule reserves it). ``expanded_rects`` holds each collapsed
    Group's expanded rectangle. ``member_lists`` are the honoured lists (identity Groups).
    """

    rects: dict[str, LayoutNodeBounds]
    expanded_rects: dict[str, LayoutNodeBounds]
    specs: dict[str, "NodeTypeSpec"]
    group_backdrop_ids: set[str]
    collapsed_ids: set[str]
    member_lists: dict[str, tuple[str, ...]]
    membership: dict[str, GroupBackdropMembership] = field(default_factory=dict)

    def owner(self, node_id: str) -> str | None:
        membership = self.membership.get(node_id)
        return (membership.owner_backdrop_id or None) if membership is not None else None

    def contents(self, backdrop_id: str) -> list[str]:
        membership = self.membership.get(backdrop_id)
        if membership is None:
            return []
        return [*membership.contained_node_ids, *membership.contained_backdrop_ids]

    def direct_members(self, backdrop_id: str) -> list[str]:
        membership = self.membership.get(backdrop_id)
        if membership is None:
            return []
        return [*membership.member_node_ids, *membership.member_backdrop_ids]

    def owns_by_identity(self, backdrop_id: str) -> bool:
        return backdrop_id in self.member_lists

    def membership_rect(self, node_id: str, rect: LayoutNodeBounds) -> LayoutNodeBounds:
        """The rectangle ``node_id`` takes part in membership with at ``rect`` (a listed collapsed Group: its corner)."""
        if node_id in self.collapsed_ids and node_id in self.member_lists:
            return LayoutNodeBounds(node_id, rect.x, rect.y, CORNER_CANDIDATE_SIZE, CORNER_CANDIDATE_SIZE)
        return rect

    def candidates(
        self,
        rects: Mapping[str, LayoutNodeBounds],
        *,
        list_overrides: Mapping[str, tuple[str, ...] | None] | None = None,
        collapsed_overrides: Mapping[str, bool] | None = None,
    ) -> list[GroupBackdropCandidate]:
        """Membership candidates for ``rects``; the overrides simulate list changes and collapse toggles."""
        list_overrides = list_overrides or {}
        collapsed_overrides = collapsed_overrides or {}
        candidates: list[GroupBackdropCandidate] = []
        for node_id, rect in rects.items():
            is_backdrop = node_id in self.group_backdrop_ids
            held = list_overrides[node_id] if node_id in list_overrides else self.member_lists.get(node_id)
            collapsed = collapsed_overrides.get(node_id, node_id in self.collapsed_ids)
            kind = membership_rect_kind(
                _CollapsedStub(node_id, collapsed),
                is_backdrop=is_backdrop,
                list_honoured=held is not None,
            )
            corner = kind == MEMBERSHIP_RECT_CORNER
            candidates.append(
                GroupBackdropCandidate(
                    node_id=node_id,
                    scope_path=(),
                    is_backdrop=is_backdrop,
                    x=rect.x,
                    y=rect.y,
                    width=CORNER_CANDIDATE_SIZE if corner else rect.width,
                    height=CORNER_CANDIDATE_SIZE if corner else rect.height,
                    held_member_ids=held if is_backdrop else None,
                )
            )
        return candidates

    def membership_at(
        self,
        rects: Mapping[str, LayoutNodeBounds],
        *,
        list_overrides: Mapping[str, tuple[str, ...] | None] | None = None,
        collapsed_overrides: Mapping[str, bool] | None = None,
    ) -> dict[str, GroupBackdropMembership]:
        if not self.group_backdrop_ids:
            return {}
        return compute_group_backdrop_membership(
            self.candidates(rects, list_overrides=list_overrides, collapsed_overrides=collapsed_overrides)
        )

    def owner_changes(
        self,
        rects: Mapping[str, LayoutNodeBounds],
        *,
        list_overrides: Mapping[str, tuple[str, ...] | None] | None = None,
        collapsed_overrides: Mapping[str, bool] | None = None,
    ) -> set[str]:
        """Nodes whose owning Group would change at ``rects`` (and the simulated list/collapse changes)."""
        final_membership = self.membership_at(
            rects,
            list_overrides=list_overrides,
            collapsed_overrides=collapsed_overrides,
        )
        return {
            node_id
            for node_id, membership in final_membership.items()
            if (membership.owner_backdrop_id or None) != self.owner(node_id)
        }


@dataclass(slots=True, frozen=True)
class _CollapsedStub:
    node_id: str
    collapsed: bool


def collect_group_scope(
    self,
    workspace: WorkspaceData,
    scope_ids: list[str],
    workspace_nodes: dict[str, NodeInstance],
) -> GroupScope:
    registry = self._scene_context.registry
    hidden = hidden_node_ids(workspace.nodes)
    rects: dict[str, LayoutNodeBounds] = {}
    expanded_rects: dict[str, LayoutNodeBounds] = {}
    specs: dict[str, "NodeTypeSpec"] = {}
    group_backdrop_ids: set[str] = set()
    collapsed_ids: set[str] = set()
    member_lists: dict[str, tuple[str, ...]] = {}
    scoped: list[tuple[NodeInstance, "NodeTypeSpec"]] = []
    for node_id in scope_ids:
        node = workspace.nodes.get(node_id)
        spec = registry.spec_or_none(node.type_id) if node is not None and registry is not None else None
        if node is not None and spec is not None:
            scoped.append((node, spec))
    drawn_by_id = scene_layout_bounds(self, workspace, [node for node, _spec in scoped], workspace_nodes=workspace_nodes)
    expanded_by_id = scene_layout_bounds(
        self,
        workspace,
        [node for node, spec in scoped if is_group_backdrop_spec(spec) and bool(node.collapsed)],
        workspace_nodes=workspace_nodes,
        expanded=True,
    )
    for node, spec in scoped:
        node_id = node.node_id
        is_backdrop = is_group_backdrop_spec(spec)
        drawn = drawn_by_id.get(node_id)
        if drawn is None:
            continue
        held = honoured_held_member_ids(node, is_backdrop=is_backdrop, collapsed_lists_contain=hidden.__contains__)
        rect = drawn
        if is_backdrop and bool(node.collapsed):
            expanded_rects[node_id] = expanded_by_id.get(node_id, drawn)
            collapsed_ids.add(node_id)
            if membership_rect_kind(node, is_backdrop=True, list_honoured=held is not None) == MEMBERSHIP_RECT_EXPANDED:
                rect = expanded_rects[node_id]
        rects[node_id] = rect
        specs[node_id] = spec
        if is_backdrop:
            group_backdrop_ids.add(node_id)
        if held is not None:
            member_lists[node_id] = held
    scope = GroupScope(
        rects=rects,
        expanded_rects=expanded_rects,
        specs=specs,
        group_backdrop_ids=group_backdrop_ids,
        collapsed_ids=collapsed_ids,
        member_lists=member_lists,
    )
    scope.membership = scope.membership_at(rects)
    return scope


def collect_group_scope_for_node(
    self,
    workspace: WorkspaceData,
    node_id: str,
    workspace_nodes: dict[str, NodeInstance],
) -> GroupScope:
    return collect_group_scope(
        self,
        workspace,
        scope_node_ids(workspace, node_scope_path(workspace, node_id)),
        workspace_nodes,
    )


def rect_strictly_contains(outer: LayoutNodeBounds, inner: LayoutNodeBounds) -> bool:
    """The membership containment test of ``group_backdrop_geometry`` for layout rectangles."""
    return _strictly_contains(membership_candidate(outer, True), membership_candidate(inner, False))


def grow_group_around(
    scope: GroupScope,
    rects: Mapping[str, LayoutNodeBounds],
    group_id: str,
    changed_member_ids: Iterable[str],
    *,
    base_rect: LayoutNodeBounds | None = None,
    keep_top_left: bool = False,
) -> LayoutNodeBounds | None:
    """Grow only the sides of ``group_id`` that a changed direct member crosses, each by its wrap padding.

    Unlike wrapping there is no minimum size and no centring, so a member near the top that stays inside never pushes
    the title edge up. ``keep_top_left`` grows right and down only (a collapsed Group: its pill sits at the top-left).
    ``None`` when no changed member crosses a side that may grow.
    """
    base = base_rect if base_rect is not None else rects[group_id]
    direct_members = set(scope.direct_members(group_id))
    left, top, right, bottom = base.left, base.top, base.right, base.bottom
    for member_id in changed_member_ids:
        rect = rects.get(member_id)
        if rect is None or member_id == group_id or member_id not in direct_members:
            continue
        if rect.left < base.left - _UPDATE_TOLERANCE and not keep_top_left:
            left = min(left, rect.left - GROUP_BACKDROP_WRAP_PADDING)
        if rect.top < base.top - _UPDATE_TOLERANCE and not keep_top_left:
            top = min(top, rect.top - GROUP_BACKDROP_WRAP_TOP_PADDING)
        if rect.right > base.right + _UPDATE_TOLERANCE:
            right = max(right, rect.right + GROUP_BACKDROP_WRAP_PADDING)
        if rect.bottom > base.bottom + _UPDATE_TOLERANCE:
            bottom = max(bottom, rect.bottom + GROUP_BACKDROP_WRAP_BOTTOM_PADDING)
    if (left, top, right, bottom) == (base.left, base.top, base.right, base.bottom):
        return None
    return LayoutNodeBounds(node_id=group_id, x=left, y=top, width=right - left, height=bottom - top)


def grow_owner_chain(
    self,
    workspace: WorkspaceData,
    rects: dict[str, LayoutNodeBounds],
    scope: GroupScope,
    owner_id: str | None,
    *,
    expanded_rects: dict[str, LayoutNodeBounds] | None = None,
) -> set[str] | None:
    """Grow an unselected owner (and its owners) around members that moved or grew.

    A collapsed owner (Tidy on the members of a peeked Group) grows its expanded rectangle in ``expanded_rects``
    instead of its pill, right and down only (written as its custom size, so the pill at its top-left never moves),
    and the chain stops there. Returns the grown ids, or ``None`` when a Group that would have to grow cannot be moved
    (it is locked).
    """
    grown: set[str] = set()
    current = owner_id
    visited: set[str] = set()
    while current is not None and current not in visited:
        visited.add(current)
        changed_rects = [
            rects[member_id]
            for member_id in scope.direct_members(current)
            if member_id in rects and rects[member_id] != scope.rects[member_id]
        ]
        box = build_group_backdrop_wrap_bounds(
            [membership_candidate(rect, rect.node_id in scope.group_backdrop_ids) for rect in changed_rects]
        )
        collapsed = current in scope.expanded_rects
        if collapsed:
            rect = (expanded_rects or {}).get(current, scope.expanded_rects[current])
        else:
            rect = rects[current]
        if box is None:
            break
        left = rect.left if collapsed else min(rect.left, box.x)
        top = rect.top if collapsed else min(rect.top, box.y)
        right = max(rect.right, box.x + box.width)
        bottom = max(rect.bottom, box.y + box.height)
        if (
            rect.left - left <= _UPDATE_TOLERANCE
            and rect.top - top <= _UPDATE_TOLERANCE
            and right - rect.right <= _UPDATE_TOLERANCE
            and bottom - rect.bottom <= _UPDATE_TOLERANCE
        ):
            break
        if not self._scope_selection.normalized_selected_node_ids(workspace, [current]):
            return None
        grown_rect = LayoutNodeBounds(node_id=current, x=left, y=top, width=right - left, height=bottom - top)
        grown.add(current)
        if collapsed:
            if expanded_rects is not None:
                expanded_rects[current] = grown_rect
            break
        rects[current] = grown_rect
        current = scope.owner(current)
    return grown


def membership_candidate(rect: LayoutNodeBounds, is_backdrop: bool) -> GroupBackdropCandidate:
    return GroupBackdropCandidate(
        node_id=rect.node_id,
        scope_path=(),
        is_backdrop=is_backdrop,
        x=rect.x,
        y=rect.y,
        width=rect.width,
        height=rect.height,
    )


__all__ = [
    "GroupScope",
    "collect_group_scope",
    "collect_group_scope_for_node",
    "group_membership_for_scope",
    "grow_group_around",
    "grow_owner_chain",
    "is_group_backdrop_spec",
    "membership_candidate",
    "node_layout_bounds",
    "rect_strictly_contains",
    "scene_layout_bounds",
]
