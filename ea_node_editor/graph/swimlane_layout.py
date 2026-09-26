# Purpose: Pure swimlane geometry: the stacked-lane rule of a pool (restack, near-side nudges, far-side growth), which lane holds a point, edge-aware lane and pool resizes, removing a lane, and new-pool frames; UI-free.
# Map: feature_routes/swimlane_pools_lanes
# Tests: tests/test_swimlane_layout.py
"""Swimlane geometry, computed in a horizontal frame.

A horizontal pool has its title band on the left and stacks its lanes top to bottom; each lane has its role band on
its own left and every lane spans the pool's width. A vertical pool is the same picture transposed (title bands on
top, lanes stacked left to right), so every function here works in the horizontal frame: ``u`` runs along the flow
(x of a horizontal pool) and ``v`` along the stack (its y). Lanes are Group backdrops, so which lane holds a node is the
Group area rule; these functions only keep the lanes stacked and the lane contents inside their lanes.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ea_node_editor.graph.transform_layout_ops import LayoutNodeBounds
from ea_node_editor.nodes.builtins.passive_annotation import (
    PASSIVE_ANNOTATION_SWIMLANE_LANE_TYPE_ID,
    PASSIVE_ANNOTATION_SWIMLANE_POOL_TYPE_ID,
    SWIMLANE_ORIENTATION_HORIZONTAL,
    SWIMLANE_ORIENTATION_VERTICAL,
    SWIMLANE_ORIENTATIONS,
)

SWIMLANE_POOL_HEADER = 40.0  # thickness of the pool's title band
SWIMLANE_LANE_HEADER = 40.0  # thickness of a lane's role band
SWIMLANE_CONTENT_PADDING = 24.0  # kept between a lane's edges (and its role band) and what it holds
SWIMLANE_DEFAULT_LANE_THICKNESS = 200.0
SWIMLANE_DEFAULT_POOL_LENGTH = 1200.0  # along the flow, title band included
SWIMLANE_DEFAULT_LANE_COUNT = 3
SWIMLANE_MIN_LANE_THICKNESS = 120.0
SWIMLANE_MIN_LANE_LENGTH = 320.0  # along the flow, role band included
_TOLERANCE = 0.01


@dataclass(frozen=True, slots=True)
class SwimlaneLaneState:
    """One lane going into a restack.

    ``bounds`` is the reference band: the lane is laid out at its stack position and everything it holds moves by the
    difference between that position and ``bounds``' stack start. ``item_bounds`` are the lane's top-level items (a
    Group counts once and carries what it holds). ``thickness`` asks for a size along the stack axis (``None`` keeps
    the reference band's).
    """

    lane_id: str
    bounds: LayoutNodeBounds
    item_bounds: tuple[LayoutNodeBounds, ...] = ()
    thickness: float | None = None


@dataclass(frozen=True, slots=True)
class SwimlaneRestack:
    pool: LayoutNodeBounds
    lanes: tuple[LayoutNodeBounds, ...]  # in stack order
    item_offsets: dict[str, tuple[float, float]]  # non-zero (dx, dy) per top-level item


@dataclass(frozen=True, slots=True)
class SwimlaneRestackRequest:
    """Arguments of :func:`restack_swimlane_pool` a resize resolves to (every edge clamped to what the lanes hold)."""

    lanes: tuple[SwimlaneLaneState, ...]
    stack_start: float
    cross_start: float
    cross_end: float
    pool_thickness: float | None = None  # a lane-less pool's size along the stack axis


def normalize_swimlane_orientation(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in SWIMLANE_ORIENTATIONS else SWIMLANE_ORIENTATION_HORIZONTAL


def is_swimlane_pool_type(type_id: object) -> bool:
    return str(type_id or "").strip() == PASSIVE_ANNOTATION_SWIMLANE_POOL_TYPE_ID


def is_swimlane_lane_type(type_id: object) -> bool:
    return str(type_id or "").strip() == PASSIVE_ANNOTATION_SWIMLANE_LANE_TYPE_ID


def is_swimlane_type(type_id: object) -> bool:
    return is_swimlane_pool_type(type_id) or is_swimlane_lane_type(type_id)


def swimlane_stack_center(rect: LayoutNodeBounds, orientation: str) -> float:
    """Where ``rect`` sits along the stack axis (y centre of a horizontal pool's lane, x centre of a vertical one's)."""
    return rect.center_x if _is_vertical(orientation) else rect.center_y


def swimlane_lane_thickness(rect: LayoutNodeBounds, orientation: str) -> float:
    return rect.width if _is_vertical(orientation) else rect.height


def restack_swimlane_pool(
    pool: LayoutNodeBounds,
    orientation: str,
    lanes: Sequence[SwimlaneLaneState],
    *,
    pool_items: Sequence[LayoutNodeBounds] = (),
    stack_start: float | None = None,
    cross_start: float | None = None,
    cross_end: float | None = None,
    pool_thickness: float | None = None,
    placed_item_ids: Collection[str] = (),
) -> SwimlaneRestack:
    """Stack ``lanes`` in their given order and fit the pool and lanes around what they hold.

    The pool keeps its start (or ``stack_start`` / ``cross_start``: its edges along the stack and the flow axis) and
    its flow length (or ``cross_end``: where every lane ends along the flow). Lanes follow each other with no gap and
    all span the flow length. An item crossing a lane's start side (its role band, or its top in a horizontal pool) is
    nudged in; an item crossing an end side makes its lane thicker or every lane longer. ``placed_item_ids`` were just
    dropped into their lanes: across the lane they are nudged fully inside when they fit, so a drop near a lane's edge
    does not push the lanes after it. ``pool_items`` are what a lane-less pool holds itself.
    """
    vertical = _is_vertical(orientation)
    frame_pool = _to_frame(pool, vertical)
    u0 = frame_pool.x if cross_start is None else float(cross_start)
    v0 = frame_pool.y if stack_start is None else float(stack_start)
    lane_u0 = u0 + SWIMLANE_POOL_HEADER
    content_u0 = lane_u0 + (SWIMLANE_LANE_HEADER if lanes else 0.0) + SWIMLANE_CONTENT_PADDING

    frame_lanes = [
        (lane, _to_frame(lane.bounds, vertical), [_to_frame(item, vertical) for item in lane.item_bounds])
        for lane in lanes
    ]
    frame_pool_items = [_to_frame(item, vertical) for item in pool_items]
    # A lane moved along the flow (dragged sideways, or joining another pool) comes back in line with the pool's lanes
    # and brings what it holds; a resized flow edge (``cross_start``) moves no item.
    lane_shift_u = {
        lane.lane_id: (frame_pool.x + SWIMLANE_POOL_HEADER) - band.x for lane, band, _items in frame_lanes
    }
    shift_u = {item.node_id: lane_shift_u[lane.lane_id] for lane, _band, items in frame_lanes for item in items}
    all_items = [item for _lane, _band, items in frame_lanes for item in items] + frame_pool_items
    nudge_u = {
        item.node_id: max(0.0, content_u0 - (item.x + shift_u.get(item.node_id, 0.0))) for item in all_items
    }
    u_end = frame_pool.right if cross_end is None else float(cross_end)
    u_end = max(u_end, lane_u0 + SWIMLANE_MIN_LANE_LENGTH)
    for item in all_items:
        u_end = max(
            u_end,
            item.right + shift_u.get(item.node_id, 0.0) + nudge_u[item.node_id] + SWIMLANE_CONTENT_PADDING,
        )

    offsets: dict[str, tuple[float, float]] = {}

    def record(item: LayoutNodeBounds, du: float, dv: float) -> None:
        if abs(du) >= _TOLERANCE or abs(dv) >= _TOLERANCE:
            offsets[item.node_id] = _offset_from_frame(du, dv, vertical)

    lane_rects: list[LayoutNodeBounds] = []
    if frame_lanes:
        cursor = v0
        placed = set(placed_item_ids)
        for lane, band, items in frame_lanes:
            thickness = float(lane.thickness) if lane.thickness is not None else band.height
            top_limit = band.y + SWIMLANE_CONTENT_PADDING
            nudge_v = {item.node_id: max(0.0, top_limit - item.y) for item in items}
            for item in items:
                bottom_limit = band.y + thickness - SWIMLANE_CONTENT_PADDING
                if item.node_id in placed and item.bottom > bottom_limit and item.height <= bottom_limit - top_limit:
                    nudge_v[item.node_id] = bottom_limit - item.bottom
            for item in items:
                thickness = max(thickness, item.bottom + nudge_v[item.node_id] - band.y + SWIMLANE_CONTENT_PADDING)
            thickness = max(thickness, SWIMLANE_MIN_LANE_THICKNESS)
            shift = cursor - band.y
            lane_rects.append(
                _from_frame(LayoutNodeBounds(lane.lane_id, lane_u0, cursor, u_end - lane_u0, thickness), vertical)
            )
            for item in items:
                record(item, shift_u[item.node_id] + nudge_u[item.node_id], shift + nudge_v[item.node_id])
            cursor += thickness
        pool_stack_size = cursor - v0
    else:
        pool_stack_size = float(pool_thickness) if pool_thickness is not None else frame_pool.height
        top_limit = v0 + SWIMLANE_CONTENT_PADDING
        for item in frame_pool_items:
            nudge_v = max(0.0, top_limit - item.y)
            pool_stack_size = max(pool_stack_size, item.bottom + nudge_v - v0 + SWIMLANE_CONTENT_PADDING)
            record(item, nudge_u[item.node_id], nudge_v)
        pool_stack_size = max(pool_stack_size, SWIMLANE_MIN_LANE_THICKNESS)

    new_pool = _from_frame(LayoutNodeBounds(pool.node_id, u0, v0, u_end - u0, pool_stack_size), vertical)
    return SwimlaneRestack(pool=new_pool, lanes=tuple(lane_rects), item_offsets=offsets)


def swimlane_lane_index_at(
    pool: LayoutNodeBounds,
    orientation: str,
    lane_bounds: Sequence[LayoutNodeBounds],
    point: tuple[float, float],
) -> int | None:
    """Index of the lane whose band holds ``point`` (a centre), or ``None`` when the pool does not hold it.

    The pool's title band counts too: its lane is the one level with the point. A pool without lanes holds nothing.
    """
    if not lane_bounds:
        return None
    x, y = float(point[0]), float(point[1])
    if not (pool.left <= x <= pool.right and pool.top <= y <= pool.bottom):
        return None
    vertical = _is_vertical(orientation)
    stack_value = x if vertical else y
    for index, lane in enumerate(lane_bounds):
        frame_lane = _to_frame(lane, vertical)
        if stack_value < frame_lane.bottom:
            return index
    return len(lane_bounds) - 1


def order_swimlane_lanes(
    lanes: Sequence[LayoutNodeBounds],
    orientation: str,
    *,
    previous_order: Sequence[str] = (),
) -> list[str]:
    """Lane ids by position along the stack axis; ties keep ``previous_order``."""
    rank = {lane_id: index for index, lane_id in enumerate(previous_order)}
    return [
        lane.node_id
        for lane in sorted(
            lanes,
            key=lambda lane: (
                round(swimlane_stack_center(lane, orientation), 3),
                rank.get(lane.node_id, len(rank)),
                lane.node_id,
            ),
        )
    ]


def absorb_removed_swimlane_lane(
    lanes: Sequence[SwimlaneLaneState],
    removed_lane_id: str,
    orientation: str,
) -> list[SwimlaneLaneState]:
    """The lanes left once ``removed_lane_id`` goes: its neighbour (the lane before it, else after) takes its band.

    The neighbour's reference band becomes both bands, so nothing it or the removed lane held moves and the pool keeps
    its size.
    """
    index = next((position for position, lane in enumerate(lanes) if lane.lane_id == removed_lane_id), None)
    if index is None:
        return list(lanes)
    remaining = [lane for lane in lanes if lane.lane_id != removed_lane_id]
    if not remaining:
        return []
    removed = lanes[index]
    neighbour_index = index - 1 if index > 0 else 0
    neighbour = remaining[neighbour_index]
    vertical = _is_vertical(orientation)
    removed_band = _to_frame(removed.bounds, vertical)
    neighbour_band = _to_frame(neighbour.bounds, vertical)
    neighbour_thickness = neighbour.thickness if neighbour.thickness is not None else neighbour_band.height
    removed_thickness = removed.thickness if removed.thickness is not None else removed_band.height
    top = min(neighbour_band.y, removed_band.y)
    union = LayoutNodeBounds(
        neighbour.lane_id,
        neighbour_band.x,
        top,
        neighbour_band.width,
        neighbour_thickness + removed_thickness,
    )
    remaining[neighbour_index] = SwimlaneLaneState(
        lane_id=neighbour.lane_id,
        bounds=_from_frame(union, vertical),
        item_bounds=(*neighbour.item_bounds, *removed.item_bounds),
        thickness=neighbour_thickness + removed_thickness,
    )
    return remaining


def resolve_swimlane_lane_resize(
    pool: LayoutNodeBounds,
    orientation: str,
    lanes: Sequence[SwimlaneLaneState],
    lane_id: str,
    requested: LayoutNodeBounds,
) -> SwimlaneRestackRequest | None:
    """What resizing one lane to ``requested`` does to its pool (``None`` when ``lane_id`` is not one of ``lanes``).

    Along the stack axis the lane takes the requested size: a moved start edge shifts the lanes before it (and the
    pool start) with it, a moved end edge the lanes after it. Along the flow every lane and the pool follow. Edges stop
    where the lanes' contents begin, and at the minimum lane size.
    """
    vertical = _is_vertical(orientation)
    index = next((position for position, lane in enumerate(lanes) if lane.lane_id == lane_id), None)
    if index is None:
        return None
    frame_pool = _to_frame(pool, vertical)
    lane = lanes[index]
    band = _to_frame(lane.bounds, vertical)
    wanted = _to_frame(requested, vertical)
    own_items = [_to_frame(item, vertical) for item in lane.item_bounds]
    new_top, new_bottom = _clamped_span(
        wanted.y,
        wanted.bottom,
        start_moved=abs(wanted.y - band.y) >= _TOLERANCE,
        items_start=min((item.y for item in own_items), default=None),
        items_end=max((item.bottom for item in own_items), default=None),
        minimum=SWIMLANE_MIN_LANE_THICKNESS,
    )
    resized = SwimlaneLaneState(
        lane_id=lane.lane_id,
        bounds=_from_frame(LayoutNodeBounds(lane.lane_id, band.x, new_top, band.width, new_bottom - new_top), vertical),
        item_bounds=lane.item_bounds,
        thickness=new_bottom - new_top,
    )
    cross_start, cross_end = _clamped_cross_span(
        wanted.x - SWIMLANE_POOL_HEADER,
        wanted.right,
        start_moved=abs(wanted.x - band.x) >= _TOLERANCE,
        items=[_to_frame(item, vertical) for other in lanes for item in other.item_bounds],
        has_lanes=True,
    )
    return SwimlaneRestackRequest(
        lanes=tuple(resized if position == index else other for position, other in enumerate(lanes)),
        stack_start=frame_pool.y + (new_top - band.y),
        cross_start=cross_start,
        cross_end=cross_end,
    )


def resolve_swimlane_pool_resize(
    pool: LayoutNodeBounds,
    orientation: str,
    lanes: Sequence[SwimlaneLaneState],
    requested: LayoutNodeBounds,
    *,
    pool_items: Sequence[LayoutNodeBounds] = (),
) -> SwimlaneRestackRequest:
    """What resizing a pool to ``requested`` does: a moved stack edge resizes the first or last lane, the flow edges
    move every lane. Edges stop where contents begin, and at the minimum sizes."""
    vertical = _is_vertical(orientation)
    frame_pool = _to_frame(pool, vertical)
    wanted = _to_frame(requested, vertical)
    start_moved = abs(wanted.y - frame_pool.y) >= _TOLERANCE
    end_moved = abs(wanted.bottom - frame_pool.bottom) >= _TOLERANCE
    all_items = [_to_frame(item, vertical) for lane in lanes for item in lane.item_bounds]
    all_items.extend(_to_frame(item, vertical) for item in pool_items)
    cross_start, cross_end = _clamped_cross_span(
        wanted.x,
        wanted.right,
        start_moved=abs(wanted.x - frame_pool.x) >= _TOLERANCE,
        items=all_items,
        has_lanes=bool(lanes),
    )
    if not lanes:
        new_top, new_bottom = _clamped_span(
            wanted.y,
            wanted.bottom,
            start_moved=start_moved,
            items_start=min((item.y for item in all_items), default=None),
            items_end=max((item.bottom for item in all_items), default=None),
            minimum=SWIMLANE_MIN_LANE_THICKNESS,
        )
        return SwimlaneRestackRequest(
            lanes=(),
            stack_start=new_top,
            cross_start=cross_start,
            cross_end=cross_end,
            pool_thickness=new_bottom - new_top,
        )
    states = list(lanes)
    new_top = frame_pool.y
    if start_moved:
        first = states[0]
        band = _to_frame(first.bounds, vertical)
        first_items = [_to_frame(item, vertical) for item in first.item_bounds]
        new_top, _end = _clamped_span(
            wanted.y,
            band.bottom,
            start_moved=True,
            items_start=min((item.y for item in first_items), default=None),
            items_end=None,
            minimum=SWIMLANE_MIN_LANE_THICKNESS,
        )
        states[0] = _with_band(first, band.x, new_top, band.width, band.bottom - new_top, vertical)
    if end_moved:
        last = states[-1]
        band = _to_frame(last.bounds, vertical)
        last_items = [_to_frame(item, vertical) for item in last.item_bounds]
        _start, new_bottom = _clamped_span(
            band.y,
            band.y + (float(last.thickness) if last.thickness is not None else band.height)
            + (wanted.bottom - frame_pool.bottom),
            start_moved=False,
            items_start=None,
            items_end=max((item.bottom for item in last_items), default=None),
            minimum=SWIMLANE_MIN_LANE_THICKNESS,
        )
        states[-1] = _with_band(last, band.x, band.y, band.width, new_bottom - band.y, vertical)
    return SwimlaneRestackRequest(
        lanes=tuple(states),
        stack_start=new_top,
        cross_start=cross_start,
        cross_end=cross_end,
    )


def new_swimlane_pool_frames(
    x: float,
    y: float,
    orientation: str,
    lane_ids: Sequence[str],
    *,
    pool_id: str = "",
    lane_thickness: float = SWIMLANE_DEFAULT_LANE_THICKNESS,
    length: float = SWIMLANE_DEFAULT_POOL_LENGTH,
) -> SwimlaneRestack:
    """A pool at (``x``, ``y``) and its lanes, each ``lane_thickness`` thick, ``length`` long along the flow."""
    vertical = _is_vertical(orientation)
    thickness = max(float(lane_thickness), SWIMLANE_MIN_LANE_THICKNESS)
    frame_pool = LayoutNodeBounds(pool_id, float(y), float(x), 0.0, 0.0) if vertical else LayoutNodeBounds(
        pool_id, float(x), float(y), 0.0, 0.0
    )
    lanes = [
        SwimlaneLaneState(
            lane_id=lane_id,
            bounds=_from_frame(LayoutNodeBounds(lane_id, 0.0, frame_pool.y, 0.0, thickness), vertical),
            thickness=thickness,
        )
        for lane_id in lane_ids
    ]
    return restack_swimlane_pool(
        _from_frame(frame_pool, vertical),
        orientation,
        lanes,
        cross_end=frame_pool.x + max(float(length), SWIMLANE_POOL_HEADER + SWIMLANE_MIN_LANE_LENGTH),
        pool_thickness=thickness,
    )


def swimlane_pool_lane_ids_from_records(
    workspace_nodes: Mapping[str, Any],
    pool_ids: Iterable[str],
) -> list[str]:
    """Lanes whose stored frames lie in the given pools (each lane counts for the smallest pool around it).

    Pools and lanes always store their size, so their records alone decide this; copying or removing a pool takes
    its lanes along.
    """
    frames: dict[str, LayoutNodeBounds] = {}
    for node_id, node in workspace_nodes.items():
        if not is_swimlane_type(getattr(node, "type_id", "")):
            continue
        width = getattr(node, "custom_width", None)
        height = getattr(node, "custom_height", None)
        if width is None or height is None:
            continue
        frames[node_id] = LayoutNodeBounds(node_id, float(node.x), float(node.y), float(width), float(height))
    pools = [
        node_id
        for node_id in frames
        if is_swimlane_pool_type(workspace_nodes[node_id].type_id) and not bool(getattr(workspace_nodes[node_id], "collapsed", False))
    ]
    wanted = {str(pool_id) for pool_id in pool_ids}
    lane_ids: list[str] = []
    for lane_id, lane in sorted(frames.items()):
        lane_node = workspace_nodes[lane_id]
        if not is_swimlane_lane_type(lane_node.type_id):
            continue
        holders = [
            pool_id
            for pool_id in pools
            if workspace_nodes[pool_id].parent_node_id == lane_node.parent_node_id
            and _rect_contains(frames[pool_id], lane)
        ]
        if not holders:
            continue
        holder = min(holders, key=lambda pool_id: (frames[pool_id].width * frames[pool_id].height, pool_id))
        if holder in wanted:
            lane_ids.append(lane_id)
    return lane_ids


def _rect_contains(outer: LayoutNodeBounds, inner: LayoutNodeBounds) -> bool:
    return (
        outer.left - _TOLERANCE <= inner.left
        and outer.top - _TOLERANCE <= inner.top
        and inner.right <= outer.right + _TOLERANCE
        and inner.bottom <= outer.bottom + _TOLERANCE
    )


def swimlane_frame_rect(rect: LayoutNodeBounds, orientation: str) -> LayoutNodeBounds:
    """``rect`` in the horizontal frame (transposed for a vertical pool); its own inverse."""
    return _to_frame(rect, _is_vertical(orientation))


def _with_band(
    lane: SwimlaneLaneState,
    u: float,
    v: float,
    length: float,
    thickness: float,
    vertical: bool,
) -> SwimlaneLaneState:
    return SwimlaneLaneState(
        lane_id=lane.lane_id,
        bounds=_from_frame(LayoutNodeBounds(lane.lane_id, u, v, length, thickness), vertical),
        item_bounds=lane.item_bounds,
        thickness=thickness,
    )


def _clamped_span(
    start: float,
    end: float,
    *,
    start_moved: bool,
    items_start: float | None,
    items_end: float | None,
    minimum: float,
) -> tuple[float, float]:
    """A band's (start, end) after a resize: never past what it holds (plus padding), never below ``minimum``."""
    new_start = float(start)
    new_end = float(end)
    if items_start is not None:
        new_start = min(new_start, items_start - SWIMLANE_CONTENT_PADDING)
    if items_end is not None:
        new_end = max(new_end, items_end + SWIMLANE_CONTENT_PADDING)
    if new_end - new_start < minimum:
        if start_moved:
            new_start = new_end - minimum
        else:
            new_end = new_start + minimum
    return new_start, new_end


def _clamped_cross_span(
    pool_start: float,
    lanes_end: float,
    *,
    start_moved: bool,
    items: Sequence[LayoutNodeBounds],
    has_lanes: bool,
) -> tuple[float, float]:
    """The pool's flow start and the lanes' flow end after a resize, kept clear of the title and role bands."""
    band = SWIMLANE_POOL_HEADER + (SWIMLANE_LANE_HEADER if has_lanes else 0.0) + SWIMLANE_CONTENT_PADDING
    new_start = float(pool_start)
    new_end = float(lanes_end)
    if items:
        new_start = min(new_start, min(item.x for item in items) - band)
        new_end = max(new_end, max(item.right for item in items) + SWIMLANE_CONTENT_PADDING)
    minimum = SWIMLANE_POOL_HEADER + SWIMLANE_MIN_LANE_LENGTH
    if new_end - new_start < minimum:
        if start_moved:
            new_start = new_end - minimum
        else:
            new_end = new_start + minimum
    return new_start, new_end


def _is_vertical(orientation: str) -> bool:
    return normalize_swimlane_orientation(orientation) == SWIMLANE_ORIENTATION_VERTICAL


def _to_frame(rect: LayoutNodeBounds, vertical: bool) -> LayoutNodeBounds:
    if not vertical:
        return rect
    return LayoutNodeBounds(rect.node_id, rect.y, rect.x, rect.height, rect.width)


_from_frame = _to_frame  # transposing is its own inverse


def _offset_from_frame(du: float, dv: float, vertical: bool) -> tuple[float, float]:
    return (dv, du) if vertical else (du, dv)


__all__ = [
    "SWIMLANE_CONTENT_PADDING",
    "SWIMLANE_DEFAULT_LANE_COUNT",
    "SWIMLANE_DEFAULT_LANE_THICKNESS",
    "SWIMLANE_DEFAULT_POOL_LENGTH",
    "SWIMLANE_LANE_HEADER",
    "SWIMLANE_MIN_LANE_LENGTH",
    "SWIMLANE_MIN_LANE_THICKNESS",
    "SWIMLANE_POOL_HEADER",
    "SwimlaneLaneState",
    "SwimlaneRestack",
    "SwimlaneRestackRequest",
    "absorb_removed_swimlane_lane",
    "is_swimlane_lane_type",
    "is_swimlane_pool_type",
    "is_swimlane_type",
    "new_swimlane_pool_frames",
    "normalize_swimlane_orientation",
    "order_swimlane_lanes",
    "resolve_swimlane_lane_resize",
    "resolve_swimlane_pool_resize",
    "restack_swimlane_pool",
    "swimlane_frame_rect",
    "swimlane_lane_index_at",
    "swimlane_lane_thickness",
    "swimlane_pool_lane_ids_from_records",
    "swimlane_stack_center",
]
