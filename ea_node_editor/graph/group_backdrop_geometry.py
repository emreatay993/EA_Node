# Purpose: Pure Group geometry: area membership for expanded Groups, identity membership for collapsed and hidden Groups, wrap bounds, and the held-member carry.
# Map: feature_routes/group_backdrops_peek_membership
# Tests: tests/test_group_backdrop_membership.py
from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, fields
from typing import Any, Sequence

from ea_node_editor.graph.hierarchy import ScopePath

GROUP_BACKDROP_WRAP_PADDING = 32.0
# Keep a visible gap after active-node shadow overflow.
GROUP_BACKDROP_WRAP_BOTTOM_PADDING = 56.0
GROUP_BACKDROP_WRAP_TOP_PADDING = 96.0
GROUP_BACKDROP_WRAP_MIN_WIDTH = 240.0
GROUP_BACKDROP_WRAP_MIN_HEIGHT = 160.0
# A collapsed Group with a member list counts as this square at its top-left when deciding which Group holds it, so a
# long title (a wider pill), a rename or a bigger font never ejects it from its parent.
CORNER_CANDIDATE_SIZE = 1.0

MEMBERSHIP_RECT_DRAWN = "drawn"
MEMBERSHIP_RECT_EXPANDED = "expanded"
MEMBERSHIP_RECT_CORNER = "corner"


@dataclass(slots=True, frozen=True)
class GroupBackdropCandidate:
    node_id: str
    scope_path: ScopePath
    is_backdrop: bool
    x: float
    y: float
    width: float
    height: float
    held_member_ids: tuple[str, ...] | None = None  # honoured list = identity Group; None = claims by area

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(slots=True, frozen=True)
class GroupBackdropMembership:
    owner_backdrop_id: str | None = None
    backdrop_depth: int = 0
    member_node_ids: tuple[str, ...] = ()
    member_backdrop_ids: tuple[str, ...] = ()
    contained_node_ids: tuple[str, ...] = ()
    contained_backdrop_ids: tuple[str, ...] = ()


# The membership a scene payload projects for every node (the GroupBackdropMembership fields): derived from geometry and
# stored lists each time, never stored in a document.
GROUP_BACKDROP_MEMBERSHIP_FIELDS = tuple(field.name for field in fields(GroupBackdropMembership))


@dataclass(slots=True, frozen=True)
class GroupBackdropBounds:
    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True, frozen=True)
class GroupBackdropWrapResult:
    backdrop_node_id: str
    wrapped_node_ids: tuple[str, ...]
    scope_path: ScopePath
    x: float
    y: float
    width: float
    height: float


def honoured_held_member_ids(
    node: Any,
    *,
    is_backdrop: bool,
    collapsed_lists_contain: Callable[[str], bool],
) -> tuple[str, ...] | None:
    """A collapsed Group's list, or an expanded Group's list while a collapsed Group lists it; else None."""
    held_member_ids = getattr(node, "held_member_ids", None)
    if not is_backdrop or held_member_ids is None:
        return None
    if bool(getattr(node, "collapsed", False)) or collapsed_lists_contain(str(node.node_id)):
        return tuple(held_member_ids)
    return None


def membership_rect_kind(node: Any, *, is_backdrop: bool, list_honoured: bool) -> str:
    """Which rectangle a node takes part in membership with.

    ``"expanded"`` for a collapsed Group without a list (older data: today's area rule), ``"corner"`` for a collapsed
    Group with a list (a ``CORNER_CANDIDATE_SIZE`` square at its top-left), ``"drawn"`` for everything else.
    """
    if not is_backdrop or not bool(getattr(node, "collapsed", False)):
        return MEMBERSHIP_RECT_DRAWN
    return MEMBERSHIP_RECT_CORNER if list_honoured else MEMBERSHIP_RECT_EXPANDED


def hidden_node_ids(
    workspace_nodes: Mapping[str, Any],
    *,
    treat_as_expanded: Collection[str] = (),
) -> set[str]:
    """Ids listed by a collapsed Group (not drawn outside Peek); ``treat_as_expanded`` Groups list nothing."""
    expanded_ids = set(treat_as_expanded)
    hidden: set[str] = set()
    for node_id, node in workspace_nodes.items():
        held_member_ids = getattr(node, "held_member_ids", None)
        if held_member_ids is None or node_id in expanded_ids or not bool(getattr(node, "collapsed", False)):
            continue
        hidden.update(member_id for member_id in held_member_ids if member_id in workspace_nodes)
    return hidden


def lists_to_freeze(
    group_id: str,
    membership: Mapping[str, GroupBackdropMembership],
    workspace_nodes: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    """Lists a collapsing Group writes: its contained subtree, and each expanded Group inside it its own."""
    group_membership = membership.get(group_id)
    if group_membership is None:
        return {group_id: ()}
    lists = {group_id: _contained_ids(group_membership)}
    for backdrop_id in group_membership.contained_backdrop_ids:
        backdrop = workspace_nodes.get(backdrop_id)
        # A collapsed Group inside keeps its own list; an expanded one (re)gets its contained subtree, which equals its
        # list when that list is honoured and repairs a stale one.
        if backdrop is None or bool(backdrop.collapsed):
            continue
        backdrop_membership = membership.get(backdrop_id)
        lists[backdrop_id] = () if backdrop_membership is None else _contained_ids(backdrop_membership)
    return lists


def lists_to_clear(workspace_nodes: Mapping[str, Any], group_id: str) -> set[str]:
    """Lists an expanding Group drops: its own (unless still hidden) and those of the Groups it lists that end up
    neither collapsed nor hidden."""
    hidden_after = hidden_node_ids(workspace_nodes, treat_as_expanded=(group_id,))
    group = workspace_nodes.get(group_id)
    if group is None or getattr(group, "held_member_ids", None) is None:
        return set()
    cleared = set() if group_id in hidden_after else {group_id}
    for member_id in group.held_member_ids:
        member = workspace_nodes.get(member_id)
        if member is None or getattr(member, "held_member_ids", None) is None:
            continue
        if bool(member.collapsed) or member_id in hidden_after:
            continue
        cleared.add(member_id)
    return cleared


def held_member_position_updates(
    workspace_nodes: Mapping[str, Any],
    position_updates: Mapping[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    """Positions for the members that moved Groups hold by identity (moving a collapsed Group moves what it holds).

    Only ids that are not already moved are carried, so a caller that moves some members itself never moves them
    twice; with overlapping lists the first moved Group (sorted) wins.
    """
    hidden = hidden_node_ids(workspace_nodes)
    carried: dict[str, tuple[float, float]] = {}
    for node_id in sorted(position_updates):
        node = workspace_nodes.get(node_id)
        held_member_ids = honoured_held_member_ids(
            node,
            is_backdrop=True,
            collapsed_lists_contain=hidden.__contains__,
        ) if node is not None else None
        if not held_member_ids:
            continue
        new_x, new_y = position_updates[node_id]
        dx = float(new_x) - float(node.x)
        dy = float(new_y) - float(node.y)
        if dx == 0.0 and dy == 0.0:
            continue
        for member_id in held_member_ids:
            member = workspace_nodes.get(member_id)
            if member is None or member_id in position_updates or member_id in carried:
                continue
            if member.parent_node_id != node.parent_node_id:
                continue
            carried[member_id] = (float(member.x) + dx, float(member.y) + dy)
    return carried


def compute_group_backdrop_membership(
    candidates: Sequence[GroupBackdropCandidate],
) -> dict[str, GroupBackdropMembership]:
    """Direct owner, depth and members per candidate.

    A Group with a list (``held_member_ids``) is an identity Group: it owns exactly the listed candidates of its scope
    (the innermost listing Group holds a candidate) and claims nothing by area. A Group without a list owns by area:
    the smallest one that strictly contains a candidate held at the same level.
    """
    candidate_by_id = {candidate.node_id: candidate for candidate in candidates}
    backdrop_candidates = [candidate for candidate in candidates if candidate.is_backdrop]
    identity_backdrops = [backdrop for backdrop in backdrop_candidates if backdrop.held_member_ids is not None]

    listing: dict[str, list[str]] = {}
    for backdrop in identity_backdrops:
        for member_id in dict.fromkeys(backdrop.held_member_ids or ()):
            member = candidate_by_id.get(member_id)
            if member is None or member_id == backdrop.node_id or member.scope_path != backdrop.scope_path:
                continue
            listing.setdefault(member_id, []).append(backdrop.node_id)
    holder_by_id: dict[str, str] = {
        member_id: min(
            listing_ids,
            key=lambda backdrop_id: (
                -len(listing.get(backdrop_id, ())),
                _owner_sort_key(candidate_by_id[backdrop_id]),
            ),
        )
        for member_id, listing_ids in listing.items()
    }

    area_backdrops = [backdrop for backdrop in backdrop_candidates if backdrop.held_member_ids is None]
    direct_owner_by_id: dict[str, str | None] = {}
    for candidate in candidates:
        holder_id = holder_by_id.get(candidate.node_id)
        containing_backdrops = [
            backdrop
            for backdrop in area_backdrops
            if holder_by_id.get(backdrop.node_id) == holder_id and _can_directly_own(backdrop, candidate)
        ]
        direct_owner_by_id[candidate.node_id] = (
            min(containing_backdrops, key=_owner_sort_key).node_id if containing_backdrops else holder_id
        )

    direct_node_members: dict[str, list[str]] = {backdrop.node_id: [] for backdrop in backdrop_candidates}
    direct_backdrop_members: dict[str, list[str]] = {backdrop.node_id: [] for backdrop in backdrop_candidates}
    for candidate in candidates:
        owner_id = direct_owner_by_id.get(candidate.node_id)
        if not owner_id:
            continue
        if candidate.is_backdrop:
            direct_backdrop_members.setdefault(owner_id, []).append(candidate.node_id)
        else:
            direct_node_members.setdefault(owner_id, []).append(candidate.node_id)

    for member_ids in direct_node_members.values():
        member_ids.sort()
    for member_ids in direct_backdrop_members.values():
        member_ids.sort()

    def depth_for(node_id: str) -> int:
        # Visited guard: hand-edited lists could form an owner cycle.
        depth = 0
        seen = {node_id}
        owner_id = direct_owner_by_id.get(node_id)
        while owner_id and owner_id not in seen:
            depth += 1
            seen.add(owner_id)
            owner_id = direct_owner_by_id.get(owner_id)
        return depth

    contained_cache: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}

    def contained_for(backdrop_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        # Visited guard (hand-edited lists could form an owner cycle); finished inner Groups are reused.
        cached = contained_cache.get(backdrop_id)
        if cached is not None:
            return cached
        contained_node_ids: set[str] = set()
        contained_backdrop_ids: set[str] = set()
        seen = {backdrop_id}
        pending = [backdrop_id]
        while pending:
            current_id = pending.pop()
            contained_node_ids.update(direct_node_members.get(current_id, ()))
            for member_id in direct_backdrop_members.get(current_id, ()):
                if member_id in seen:
                    continue
                seen.add(member_id)
                contained_backdrop_ids.add(member_id)
                inner = contained_cache.get(member_id)
                if inner is None:
                    pending.append(member_id)
                else:
                    contained_node_ids.update(inner[0])
                    contained_backdrop_ids.update(inner[1])
                    seen.update(inner[1])
        contained_backdrop_ids.discard(backdrop_id)
        result = (tuple(sorted(contained_node_ids)), tuple(sorted(contained_backdrop_ids)))
        contained_cache[backdrop_id] = result
        return result

    # Innermost Groups first, so every outer Group reuses its inner Groups' finished contents.
    for backdrop in sorted(backdrop_candidates, key=lambda candidate: -depth_for(candidate.node_id)):
        contained_for(backdrop.node_id)

    membership_by_id: dict[str, GroupBackdropMembership] = {}
    for candidate in candidates:
        member_node_ids: tuple[str, ...] = ()
        member_backdrop_ids: tuple[str, ...] = ()
        contained_node_ids: tuple[str, ...] = ()
        contained_backdrop_ids: tuple[str, ...] = ()
        if candidate.is_backdrop:
            member_node_ids = tuple(direct_node_members.get(candidate.node_id, ()))
            member_backdrop_ids = tuple(direct_backdrop_members.get(candidate.node_id, ()))
            contained_node_ids, contained_backdrop_ids = contained_for(candidate.node_id)
        membership_by_id[candidate.node_id] = GroupBackdropMembership(
            owner_backdrop_id=direct_owner_by_id.get(candidate.node_id),
            backdrop_depth=depth_for(candidate.node_id),
            member_node_ids=member_node_ids,
            member_backdrop_ids=member_backdrop_ids,
            contained_node_ids=contained_node_ids,
            contained_backdrop_ids=contained_backdrop_ids,
        )
    return membership_by_id


def build_group_backdrop_wrap_bounds(
    candidates: Sequence[GroupBackdropCandidate],
    *,
    padding: float = GROUP_BACKDROP_WRAP_PADDING,
    top_padding: float = GROUP_BACKDROP_WRAP_TOP_PADDING,
    min_width: float = GROUP_BACKDROP_WRAP_MIN_WIDTH,
    min_height: float = GROUP_BACKDROP_WRAP_MIN_HEIGHT,
) -> GroupBackdropBounds | None:
    if not candidates:
        return None

    left = min(candidate.x for candidate in candidates)
    top = min(candidate.y for candidate in candidates)
    right = max(candidate.right for candidate in candidates)
    bottom = max(candidate.bottom for candidate in candidates)

    padded_x = float(left) - float(padding)
    padded_y = float(top) - float(top_padding)
    padded_width = (float(right) - float(left)) + (float(padding) * 2.0)
    padded_height = (float(bottom) - float(top)) + float(top_padding) + GROUP_BACKDROP_WRAP_BOTTOM_PADDING

    final_width = max(float(min_width), padded_width)
    final_height = max(float(min_height), padded_height)
    final_x = padded_x - ((final_width - padded_width) * 0.5)
    final_y = padded_y - ((final_height - padded_height) * 0.5)
    return GroupBackdropBounds(
        x=final_x,
        y=final_y,
        width=final_width,
        height=final_height,
    )


def build_group_backdrop_occupied_bounds(
    backdrop: GroupBackdropCandidate,
    direct_members: Sequence[GroupBackdropCandidate],
) -> GroupBackdropBounds:
    candidates = [backdrop, *list(direct_members)]
    left = min(candidate.x for candidate in candidates)
    top = min(candidate.y for candidate in candidates)
    right = max(candidate.right for candidate in candidates)
    bottom = max(candidate.bottom for candidate in candidates)
    return GroupBackdropBounds(
        x=float(left),
        y=float(top),
        width=float(right) - float(left),
        height=float(bottom) - float(top),
    )


def _contained_ids(membership: GroupBackdropMembership) -> tuple[str, ...]:
    return tuple(sorted((*membership.contained_node_ids, *membership.contained_backdrop_ids)))


def _owner_sort_key(backdrop: GroupBackdropCandidate) -> tuple[float, float, float, float, float, str]:
    return (
        float(backdrop.area),
        float(backdrop.width),
        float(backdrop.height),
        float(backdrop.x),
        float(backdrop.y),
        backdrop.node_id,
    )


def _can_directly_own(owner: GroupBackdropCandidate, candidate: GroupBackdropCandidate) -> bool:
    if not owner.is_backdrop or owner.node_id == candidate.node_id:
        return False
    if owner.scope_path != candidate.scope_path:
        return False
    return strictly_contains(owner, candidate)


def strictly_contains(owner: GroupBackdropCandidate, candidate: GroupBackdropCandidate) -> bool:
    if owner.width <= 0.0 or owner.height <= 0.0:
        return False
    if candidate.width <= 0.0 or candidate.height <= 0.0:
        return False
    if owner.x > candidate.x or owner.y > candidate.y:
        return False
    if owner.right < candidate.right or owner.bottom < candidate.bottom:
        return False
    return (
        owner.x < candidate.x
        or owner.y < candidate.y
        or owner.right > candidate.right
        or owner.bottom > candidate.bottom
    )


__all__ = [
    "CORNER_CANDIDATE_SIZE",
    "GROUP_BACKDROP_MEMBERSHIP_FIELDS",
    "GROUP_BACKDROP_WRAP_MIN_HEIGHT",
    "GROUP_BACKDROP_WRAP_MIN_WIDTH",
    "GROUP_BACKDROP_WRAP_BOTTOM_PADDING",
    "GROUP_BACKDROP_WRAP_PADDING",
    "GROUP_BACKDROP_WRAP_TOP_PADDING",
    "MEMBERSHIP_RECT_CORNER",
    "MEMBERSHIP_RECT_DRAWN",
    "MEMBERSHIP_RECT_EXPANDED",
    "GroupBackdropBounds",
    "GroupBackdropCandidate",
    "GroupBackdropMembership",
    "GroupBackdropWrapResult",
    "build_group_backdrop_occupied_bounds",
    "build_group_backdrop_wrap_bounds",
    "compute_group_backdrop_membership",
    "held_member_position_updates",
    "hidden_node_ids",
    "honoured_held_member_ids",
    "lists_to_clear",
    "lists_to_freeze",
    "membership_rect_kind",
    "strictly_contains",
]
