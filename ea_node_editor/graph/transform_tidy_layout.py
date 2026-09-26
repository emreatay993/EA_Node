# Purpose: Pure Tidy layout (auto layered layout + in-place clean-up) over plain item/wire data, with swimlane pools laid out as one unit (layers along the flow, one row per lane); UI-free.
# Map: subsystems/graph_domain.md
# Tests: tests/test_transform_tidy_layout.py, tests/test_swimlane_tidy_layout.py
# Landmarks: TidyItem; build_tidy_layout; _TidyLayoutRun.run; _TidyLayoutRun._resolve_group; _TidyLayoutRun._resolve_swimlane_pool; _auto_layout_placement; _layer_columns; _layer_rows; _in_place_placement; _polished_positions

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
import heapq
import math
import statistics

from ea_node_editor.graph.group_backdrop_geometry import (
    GroupBackdropCandidate,
    build_group_backdrop_wrap_bounds,
)
from ea_node_editor.graph.swimlane_layout import (
    SWIMLANE_CONTENT_PADDING,
    SWIMLANE_LANE_HEADER,
    SWIMLANE_MIN_LANE_LENGTH,
    SWIMLANE_MIN_LANE_THICKNESS,
    SWIMLANE_POOL_HEADER,
    normalize_swimlane_orientation,
)
from ea_node_editor.graph.transform_layout_ops import (
    LayoutNodeBounds,
    PortAlignmentConstraint,
    build_collision_avoidance_position_updates,
    build_port_alignment_offsets,
)

TIDY_MODE_AUTO_LAYOUT = "auto_layout"
TIDY_MODE_IN_PLACE = "in_place"
TIDY_MODES = (TIDY_MODE_AUTO_LAYOUT, TIDY_MODE_IN_PLACE)
TIDY_DIRECTION_AUTO = "auto"
TIDY_DIRECTION_LEFT_TO_RIGHT = "left_to_right"
TIDY_DIRECTION_TOP_TO_BOTTOM = "top_to_bottom"
TIDY_DIRECTIONS = (TIDY_DIRECTION_AUTO, TIDY_DIRECTION_LEFT_TO_RIGHT, TIDY_DIRECTION_TOP_TO_BOTTOM)
DEFAULT_TIDY_COLUMN_GAP = 96.0  # between column bands along the flow (room for short edge labels)
DEFAULT_TIDY_ROW_GAP = 64.0  # between row bands across the flow

_HORIZONTAL_SIDES = frozenset({"left", "right"})
_VERTICAL_SIDES = frozenset({"top", "bottom"})
_TRANSPOSED_SIDES = {"left": "top", "top": "left", "right": "bottom", "bottom": "right"}
# A same-axis wire drawn "backwards" (from an in side to an out side) is reversed before layering.
_BACKWARD_SIDE_PAIRS = frozenset({("left", "right"), ("top", "bottom")})
_POSITION_EPSILON = 1e-9

_Rect = tuple[float, float, float, float]  # x, y, width, height


@dataclass(frozen=True, slots=True)
class TidyItem:
    item_id: str
    x: float  # current top-left + size (collapsed groups: pill size)
    y: float
    width: float
    height: float
    parent_group_id: str | None = None  # direct owning group item in this call (None = top level)
    is_group: bool = False
    rigid: bool = False  # moved as one box; its children are never laid out
    arrangeable: bool = True  # False = unwired annotation: keeps its rectangle
    swimlane_pool: str = ""  # a swimlane pool's orientation: it lays out its lanes' contents as one unit
    swimlane_lane: bool = False  # a lane of its parent pool item (the pool lays it out)


@dataclass(frozen=True, slots=True)
class TidyWire:
    wire_id: str
    source_id: str  # TidyItem ids (the caller already lifted hidden endpoints)
    target_id: str
    source_side: str  # "left" | "right" | "top" | "bottom" | "" (unknown)
    target_side: str
    source_offset: tuple[float, float]  # port anchor relative to the source item's top-left
    target_offset: tuple[float, float]


@dataclass(frozen=True, slots=True)
class TidySettings:
    mode: str = TIDY_MODE_AUTO_LAYOUT
    direction: str = TIDY_DIRECTION_AUTO  # auto | left_to_right | top_to_bottom
    all_advance: bool = False  # every wire advances one column (explicit direction against the drawn one)
    column_gap: float = DEFAULT_TIDY_COLUMN_GAP
    row_gap: float = DEFAULT_TIDY_ROW_GAP


@dataclass(frozen=True, slots=True)
class TidyLayoutResult:
    direction: str  # resolved LR/TB ("" for in_place)
    positions: dict[str, tuple[float, float]]  # new top-left for every item whose position changed
    group_sizes: dict[str, tuple[float, float]]  # new (w, h) for re-laid-out groups whose size changed
    loop_wire_ids: tuple[str, ...]  # back edges ignored for layering
    laid_out_level_count: int  # levels (top + groups) that had >= 2 arrangeable items


@dataclass(frozen=True, slots=True)
class _LevelWire:
    wire_id: str
    source_id: str
    target_id: str
    source_side: str
    target_side: str
    source_offset: tuple[float, float]  # anchor relative to the level item (lifted ends: the real nested port)
    target_offset: tuple[float, float]
    advance: bool = True
    row_bias: int = 0


@dataclass(frozen=True, slots=True)
class _LevelPlacement:
    positions: dict[str, tuple[float, float]]
    rows: dict[str, int]
    columns: dict[str, int]
    loop_wire_ids: frozenset[str]


def resolve_tidy_direction(wires: Sequence[TidyWire], requested: str) -> str:
    """Resolve ``auto`` from the port sides the wires use; explicit directions pass through."""
    direction = _normalized_direction(requested)
    if direction != TIDY_DIRECTION_AUTO:
        return direction
    horizontal = 0
    vertical = 0
    for wire in wires:
        if wire.source_id == wire.target_id:
            continue
        source_side = _normalized_side(wire.source_side)
        target_side = _normalized_side(wire.target_side)
        if source_side in _HORIZONTAL_SIDES and target_side in _HORIZONTAL_SIDES:
            horizontal += 1
        elif source_side in _VERTICAL_SIDES and target_side in _VERTICAL_SIDES:
            vertical += 1
        elif source_side in _VERTICAL_SIDES:
            vertical += 1
        else:
            horizontal += 1
    return TIDY_DIRECTION_TOP_TO_BOTTOM if vertical > horizontal else TIDY_DIRECTION_LEFT_TO_RIGHT


def build_tidy_layout(
    items: Sequence[TidyItem],
    wires: Sequence[TidyWire],
    settings: TidySettings,
) -> TidyLayoutResult:
    """Lay out ``items`` level by level (groups deepest first, then the top level).

    Auto-layout rebuilds a layered arrangement from the wires; in-place clean-up keeps the
    current rows/columns and regularises them. Re-laid-out groups are refitted around their
    children with the standard wrap paddings and their subtrees move with them.
    """
    mode = _normalized_mode(settings.mode)
    requested_direction = _normalized_direction(settings.direction)
    item_by_id = _items_by_id(items)
    valid_wires = _valid_wires(wires, item_by_id)
    if mode == TIDY_MODE_IN_PLACE:
        direction = ""
        all_advance = False
    else:
        direction = resolve_tidy_direction(valid_wires, requested_direction)
        all_advance = bool(settings.all_advance) and requested_direction != TIDY_DIRECTION_AUTO
    run = _TidyLayoutRun(
        item_by_id,
        valid_wires,
        mode=mode,
        transpose=direction == TIDY_DIRECTION_TOP_TO_BOTTOM,
        all_advance=all_advance,
        column_gap=_normalized_gap(settings.column_gap),
        row_gap=_normalized_gap(settings.row_gap),
    )
    return run.run(direction)


class _TidyLayoutRun:
    def __init__(
        self,
        item_by_id: Mapping[str, TidyItem],
        wires: Sequence[TidyWire],
        *,
        mode: str,
        transpose: bool,
        all_advance: bool,
        column_gap: float,
        row_gap: float,
    ) -> None:
        self._items = item_by_id
        self._wires = wires
        self._mode = mode
        self._transpose = transpose
        self._all_advance = all_advance
        self._column_gap = column_gap
        self._row_gap = row_gap
        self._parent = _sanitized_parents(item_by_id)
        self._children: dict[str | None, list[str]] = {}
        for item_id in sorted(item_by_id):
            self._children.setdefault(self._parent[item_id], []).append(item_id)
        self._rects: dict[str, _Rect] = {item_id: _item_rect(item) for item_id, item in item_by_id.items()}
        self._offsets: dict[str, tuple[float, float]] = {}
        self._loop_wire_ids: set[str] = set()
        self._laid_out_level_count = 0

    def run(self, direction: str) -> TidyLayoutResult:
        groups = [item_id for item_id in sorted(self._items) if self._items[item_id].is_group]
        for group_id in sorted(groups, key=lambda group_id: (-self._depth(group_id), group_id)):
            if self._is_pool_lane(group_id):
                continue  # its pool lays it out
            if self._items[group_id].swimlane_pool:
                self._resolve_swimlane_pool(group_id)
            else:
                self._resolve_group(group_id)
        final_positions = self._resolve_top_level()
        positions: dict[str, tuple[float, float]] = {}
        for item_id in sorted(self._items):
            item = self._items[item_id]
            final_x, final_y = final_positions[item_id]
            if abs(final_x - item.x) > _POSITION_EPSILON or abs(final_y - item.y) > _POSITION_EPSILON:
                positions[item_id] = (final_x, final_y)
        group_sizes: dict[str, tuple[float, float]] = {}
        for group_id in groups:
            item = self._items[group_id]
            _x, _y, width, height = self._rects[group_id]
            if abs(width - item.width) > _POSITION_EPSILON or abs(height - item.height) > _POSITION_EPSILON:
                group_sizes[group_id] = (width, height)
        return TidyLayoutResult(
            direction=direction,
            positions=positions,
            group_sizes=group_sizes,
            loop_wire_ids=tuple(sorted(self._loop_wire_ids)),
            laid_out_level_count=self._laid_out_level_count,
        )

    def _depth(self, item_id: str) -> int:
        depth = 0
        parent_id = self._parent[item_id]
        while parent_id is not None:
            depth += 1
            parent_id = self._parent[parent_id]
        return depth

    def _is_frozen(self, group_id: str) -> bool:
        current: str | None = group_id
        while current is not None:
            item = self._items[current]
            if item.rigid or (item.is_group and not item.arrangeable):
                return True
            current = self._parent[current]
        return False

    def _resolve_group(self, group_id: str) -> None:
        children = self._children.get(group_id, [])
        if not children:
            return
        arrangeable = [child_id for child_id in children if self._items[child_id].arrangeable]
        if self._is_frozen(group_id) or len(arrangeable) < 2:
            self._keep_group_block(group_id, children)
            return
        level_positions = self._layout_level(group_id, children, arrangeable)
        child_rects = {
            child_id: (*level_positions.get(child_id, self._rects[child_id][:2]), *self._rects[child_id][2:])
            for child_id in children
        }
        child_rects.update(self._clear_fixed_children(children, child_rects))
        box = build_group_backdrop_wrap_bounds(
            [
                GroupBackdropCandidate(
                    node_id=child_id,
                    scope_path=(),
                    is_backdrop=self._items[child_id].is_group,
                    x=rect[0],
                    y=rect[1],
                    width=rect[2],
                    height=rect[3],
                )
                for child_id, rect in child_rects.items()
            ]
        )
        if box is not None:
            self._rects[group_id] = (box.x, box.y, box.width, box.height)
        group_x, group_y = self._rects[group_id][:2]
        for child_id, rect in child_rects.items():
            self._offsets[child_id] = (rect[0] - group_x, rect[1] - group_y)

    def _is_pool_lane(self, item_id: str) -> bool:
        parent_id = self._parent[item_id]
        return bool(
            self._items[item_id].swimlane_lane and parent_id is not None and self._items[parent_id].swimlane_pool
        )

    def _resolve_swimlane_pool(self, pool_id: str) -> None:
        """Lay out a pool's lanes as one unit: layer columns along the flow shared by every lane, one row per lane.

        Two items of one lane in the same column stack across it. Lanes are sized to what they hold and stacked with
        no gap; the pool keeps its top-left. Groups and pools inside lanes were laid out first and move as blocks;
        an item the pool holds outside every lane keeps its place.
        """
        children = self._children.get(pool_id, [])
        lanes = [child_id for child_id in children if self._items[child_id].swimlane_lane]
        if self._is_frozen(pool_id):
            for lane_id in lanes:
                self._keep_group_block(lane_id, self._children.get(lane_id, []))
            self._keep_group_block(pool_id, children)
            return
        vertical = normalize_swimlane_orientation(self._items[pool_id].swimlane_pool) == "vertical"

        def frame(rect: _Rect) -> _Rect:
            return (rect[1], rect[0], rect[3], rect[2]) if vertical else rect

        pool_u, pool_v, _pool_length, _pool_thickness = frame(self._rects[pool_id])
        lanes.sort(key=lambda lane_id: (frame(self._rects[lane_id])[1] + frame(self._rects[lane_id])[3] * 0.5, lane_id))
        stragglers = [child_id for child_id in children if child_id not in lanes]
        bands: list[tuple[str | None, list[str]]] = (
            [(lane_id, list(self._children.get(lane_id, []))) for lane_id in lanes] if lanes else [(None, stragglers)]
        )
        members = [member_id for _band_id, band_members in bands for member_id in band_members]
        self._laid_out_level_count += 1
        frames = {member_id: frame(self._rects[member_id]) for member_id in members}
        wired = [member_id for member_id in members if self._items[member_id].arrangeable]
        wires = self._swimlane_pool_wires(pool_id, set(lanes), set(wired), vertical)
        columns = self._swimlane_columns(wired, frames, wires)
        # Loose items (unwired, or annotations) take the lowest free columns of their lane.
        for _band_id, band_members in bands:
            used = {columns[member_id] for member_id in band_members if member_id in columns}
            next_column = 0
            for member_id in sorted(
                (member_id for member_id in band_members if member_id not in columns),
                key=lambda member_id: (frames[member_id][0], frames[member_id][1], member_id),
            ):
                while next_column in used:
                    next_column += 1
                columns[member_id] = next_column
                used.add(next_column)
        column_ids = sorted({columns[member_id] for member_id in members})
        column_index = {column: index for index, column in enumerate(column_ids)}
        widths = [0.0] * len(column_ids)
        for member_id in members:
            column = column_index[columns[member_id]]
            widths[column] = max(widths[column], frames[member_id][2])
        lane_u0 = pool_u + SWIMLANE_POOL_HEADER
        content_u0 = lane_u0 + (SWIMLANE_LANE_HEADER if lanes else 0.0) + SWIMLANE_CONTENT_PADDING
        column_lefts = _band_starts(content_u0, widths, self._column_gap)
        content_end = column_lefts[-1] + widths[-1] if widths else content_u0
        pool_end = max(content_end + SWIMLANE_CONTENT_PADDING, lane_u0 + SWIMLANE_MIN_LANE_LENGTH)

        cursor = pool_v
        band_rects: list[_Rect] = []
        member_frames: dict[str, _Rect] = {}
        for _band_id, band_members in bands:
            stacks: dict[int, list[str]] = {}
            for member_id in sorted(
                band_members,
                key=lambda member_id: (frames[member_id][1] + frames[member_id][3] * 0.5, frames[member_id][0], member_id),
            ):
                stacks.setdefault(column_index[columns[member_id]], []).append(member_id)
            stack_heights = {
                column: sum(frames[member_id][3] for member_id in stack) + self._row_gap * (len(stack) - 1)
                for column, stack in stacks.items()
            }
            content_height = max(stack_heights.values(), default=0.0)
            thickness = max(SWIMLANE_MIN_LANE_THICKNESS, content_height + 2.0 * SWIMLANE_CONTENT_PADDING)
            top = cursor + (thickness - content_height) * 0.5
            for column, stack in stacks.items():
                v = top + (content_height - stack_heights[column]) * 0.5
                for member_id in stack:
                    _u, _v, width, height = frames[member_id]
                    member_frames[member_id] = (column_lefts[column] + (widths[column] - width) * 0.5, v, width, height)
                    v += height + self._row_gap
            band_rects.append((lane_u0, cursor, pool_end - lane_u0, thickness))
            cursor += thickness

        self._rects[pool_id] = frame((pool_u, pool_v, pool_end - pool_u, cursor - pool_v))
        pool_x, pool_y = self._rects[pool_id][:2]
        for (band_id, band_members), band_rect in zip(bands, band_rects):
            origin_x, origin_y = pool_x, pool_y
            if band_id is not None:
                self._rects[band_id] = frame(band_rect)
                origin_x, origin_y = self._rects[band_id][:2]
                self._offsets[band_id] = (origin_x - pool_x, origin_y - pool_y)
            for member_id in band_members:
                x, y, _width, _height = frame(member_frames[member_id])
                self._offsets[member_id] = (x - origin_x, y - origin_y)
        for straggler_id in stragglers if lanes else ():
            x, y = self._rects[straggler_id][:2]
            self._offsets[straggler_id] = (x - pool_x, y - pool_y)

    def _swimlane_pool_wires(
        self,
        pool_id: str,
        lane_ids: set[str],
        member_ids: set[str],
        vertical: bool,
    ) -> list[_LevelWire]:
        """The wires between items of one pool's lanes, lifted to those items, in the pool's horizontal frame."""

        def member_of(item_id: str) -> str | None:
            current = item_id
            while True:
                parent_id = self._parent[current]
                if parent_id is None:
                    return None
                if parent_id == pool_id or parent_id in lane_ids:
                    return current if current in member_ids else None
                current = parent_id

        def side(value: str) -> str:
            normalized = _normalized_side(value)
            return _TRANSPOSED_SIDES.get(normalized, normalized) if vertical else normalized

        level_wires: list[_LevelWire] = []
        for wire in self._wires:
            source_id = member_of(wire.source_id)
            target_id = member_of(wire.target_id)
            if source_id is None or target_id is None or source_id == target_id:
                continue
            level_wires.append(
                _LevelWire(
                    wire_id=wire.wire_id,
                    source_id=source_id,
                    target_id=target_id,
                    source_side=side(wire.source_side),
                    target_side=side(wire.target_side),
                    source_offset=(0.0, 0.0),
                    target_offset=(0.0, 0.0),
                )
            )
        return level_wires

    def _swimlane_columns(
        self,
        member_ids: Sequence[str],
        frames: Mapping[str, _Rect],
        wires: Sequence[_LevelWire],
    ) -> dict[str, int]:
        """Layer columns of a pool's wired items (auto layout), or their current columns kept in order (in place)."""
        if self._mode == TIDY_MODE_IN_PLACE:
            columns: dict[str, int] = {}
            column_first: list[str] = []
            for member_id in sorted(
                member_ids,
                key=lambda member_id: (frames[member_id][0] + frames[member_id][2] * 0.5, member_id),
            ):
                if column_first:
                    first = column_first[-1]
                    overlap = _axis_overlap(frames[member_id], frames[first], axis=0)
                    if overlap >= 0.5 * min(frames[member_id][2], frames[first][2]):
                        columns[member_id] = len(column_first) - 1
                        continue
                column_first.append(member_id)
                columns[member_id] = len(column_first) - 1
            return columns
        classified = [_classified_wire(_forward_wire(wire), all_advance=self._all_advance) for wire in wires]
        wired_ids = [
            member_id
            for member_id in member_ids
            if any(member_id in (wire.source_id, wire.target_id) for wire in classified)
        ]
        loop_wire_ids = _loop_wire_ids(wired_ids, frames, classified)
        self._loop_wire_ids.update(loop_wire_ids)
        acyclic = [wire for wire in classified if wire.wire_id not in loop_wire_ids]
        return _layer_columns(wired_ids, frames, acyclic)

    def _clear_fixed_children(
        self,
        children: Sequence[str],
        child_rects: Mapping[str, _Rect],
    ) -> dict[str, _Rect]:
        """Inside a group nothing else moves an unwired annotation, so push it out of the laid-out members' way."""
        fixed_ids = [child_id for child_id in children if not self._items[child_id].arrangeable]
        if not fixed_ids:
            return {}
        updates = build_collision_avoidance_position_updates(
            fixed_bounds=[
                LayoutNodeBounds(child_id, *child_rects[child_id])
                for child_id in children
                if self._items[child_id].arrangeable
            ],
            movable_bounds=[LayoutNodeBounds(child_id, *child_rects[child_id]) for child_id in fixed_ids],
            gap=0.5 * min(self._column_gap, self._row_gap),
        )
        return {child_id: (x, y, *child_rects[child_id][2:]) for child_id, (x, y) in updates.items()}

    def _keep_group_block(self, group_id: str, children: Sequence[str]) -> None:
        # Not re-laid out: the group keeps its rectangle and its children their offsets. A nested
        # group that was refitted may have outgrown it, so the block only ever grows to contain it.
        if any(self._rects[child_id] != _item_rect(self._items[child_id]) for child_id in children):
            box = build_group_backdrop_wrap_bounds(
                [
                    GroupBackdropCandidate(
                        node_id=child_id,
                        scope_path=(),
                        is_backdrop=self._items[child_id].is_group,
                        x=self._rects[child_id][0],
                        y=self._rects[child_id][1],
                        width=self._rects[child_id][2],
                        height=self._rects[child_id][3],
                    )
                    for child_id in children
                ]
            )
            if box is not None:
                x, y, width, height = self._rects[group_id]
                left = min(x, box.x)
                top = min(y, box.y)
                right = max(x + width, box.x + box.width)
                bottom = max(y + height, box.y + box.height)
                self._rects[group_id] = (left, top, right - left, bottom - top)
        group_x, group_y = self._rects[group_id][:2]
        for child_id in children:
            child_x, child_y = self._rects[child_id][:2]
            self._offsets[child_id] = (child_x - group_x, child_y - group_y)

    def _resolve_top_level(self) -> dict[str, tuple[float, float]]:
        top_ids = self._children.get(None, [])
        arrangeable = [item_id for item_id in top_ids if self._items[item_id].arrangeable]
        level_positions = self._layout_level(None, top_ids, arrangeable) if len(arrangeable) >= 2 else {}
        final_positions = {
            item_id: level_positions.get(item_id, self._rects[item_id][:2]) for item_id in top_ids
        }
        pending = list(top_ids)
        while pending:
            parent_id = pending.pop()
            parent_x, parent_y = final_positions[parent_id]
            for child_id in self._children.get(parent_id, ()):
                offset_x, offset_y = self._offsets[child_id]
                final_positions[child_id] = (parent_x + offset_x, parent_y + offset_y)
                pending.append(child_id)
        return final_positions

    def _layout_level(
        self,
        level_parent_id: str | None,
        children: Sequence[str],
        arrangeable: Sequence[str],
    ) -> dict[str, tuple[float, float]]:
        self._laid_out_level_count += 1
        frame_rects = {child_id: self._to_frame(self._rects[child_id]) for child_id in children}
        level_wires = self._lift_wires(level_parent_id, set(arrangeable))
        if self._mode == TIDY_MODE_IN_PLACE:
            placement = _in_place_placement(
                arrangeable,
                frame_rects,
                column_gap=self._column_gap,
                row_gap=self._row_gap,
            )
        else:
            placement = _auto_layout_placement(
                arrangeable,
                frame_rects,
                level_wires,
                all_advance=self._all_advance,
                column_gap=self._column_gap,
                row_gap=self._row_gap,
            )
        self._loop_wire_ids.update(placement.loop_wire_ids)
        positions = _polished_positions(
            placement,
            frame_rects,
            level_wires,
            movable_ids=set(arrangeable),
            level_ids=children,
        )
        return {item_id: self._from_frame(position) for item_id, position in positions.items()}

    def _lift_wires(self, level_parent_id: str | None, arrangeable: Collection[str]) -> list[_LevelWire]:
        level_wires: list[_LevelWire] = []
        for wire in self._wires:
            source_id = self._level_child(wire.source_id, level_parent_id)
            target_id = self._level_child(wire.target_id, level_parent_id)
            if source_id is None or target_id is None or source_id == target_id:
                continue
            if source_id not in arrangeable or target_id not in arrangeable:
                continue
            level_wires.append(
                _LevelWire(
                    wire_id=wire.wire_id,
                    source_id=source_id,
                    target_id=target_id,
                    source_side=self._frame_side(wire.source_side),
                    target_side=self._frame_side(wire.target_side),
                    source_offset=self._frame_offset(self._nested_offset(wire.source_id, source_id, wire.source_offset)),
                    target_offset=self._frame_offset(self._nested_offset(wire.target_id, target_id, wire.target_offset)),
                )
            )
        return level_wires

    def _nested_offset(self, endpoint_id: str, level_item_id: str, port_offset: Sequence[float]) -> tuple[float, float]:
        """Port anchor relative to ``level_item_id``: a lifted end adds the child offsets of every group on the way up."""
        x, y = float(port_offset[0]), float(port_offset[1])
        current = endpoint_id
        while current != level_item_id:
            offset_x, offset_y = self._offsets[current]
            x += offset_x
            y += offset_y
            current = self._parent[current]
        return (x, y)

    def _level_child(self, item_id: str, level_parent_id: str | None) -> str | None:
        current = item_id
        while True:
            parent_id = self._parent[current]
            if parent_id == level_parent_id:
                return current
            if parent_id is None:
                return None
            current = parent_id

    def _to_frame(self, rect: _Rect) -> _Rect:
        x, y, width, height = rect
        return (y, x, height, width) if self._transpose else rect

    def _from_frame(self, position: tuple[float, float]) -> tuple[float, float]:
        return (position[1], position[0]) if self._transpose else position

    def _frame_side(self, side: str) -> str:
        normalized = _normalized_side(side)
        return _TRANSPOSED_SIDES.get(normalized, normalized) if self._transpose else normalized

    def _frame_offset(self, offset: Sequence[float]) -> tuple[float, float]:
        dx, dy = float(offset[0]), float(offset[1])
        return (dy, dx) if self._transpose else (dx, dy)


def _auto_layout_placement(
    item_ids: Sequence[str],
    rects: Mapping[str, _Rect],
    wires: Sequence[_LevelWire],
    *,
    all_advance: bool,
    column_gap: float,
    row_gap: float,
) -> _LevelPlacement:
    classified = [_classified_wire(_forward_wire(wire), all_advance=all_advance) for wire in wires]
    wired_ids = {wire.source_id for wire in classified} | {wire.target_id for wire in classified}
    placed_ids = [item_id for item_id in item_ids if item_id in wired_ids]
    loose_ids = [item_id for item_id in item_ids if item_id not in wired_ids]
    loop_wire_ids = _loop_wire_ids(placed_ids, rects, classified)
    acyclic = [wire for wire in classified if wire.wire_id not in loop_wire_ids]
    columns = _layer_columns(placed_ids, rects, acyclic)
    rows = _layer_rows(placed_ids, rects, acyclic, columns)
    anchor_x = min(rects[item_id][0] for item_id in item_ids)
    anchor_y = min(rects[item_id][1] for item_id in item_ids)
    positions, rows, columns, band_top = _grid_positions(
        placed_ids,
        rects,
        rows,
        columns,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
        column_gap=column_gap,
        row_gap=row_gap,
    )
    if loose_ids:
        band_height = max(rects[item_id][3] for item_id in loose_ids)
        cursor_x = anchor_x
        for item_id in sorted(loose_ids, key=lambda item_id: (rects[item_id][0], rects[item_id][1], item_id)):
            _x, _y, width, height = rects[item_id]
            positions[item_id] = (cursor_x, band_top + (band_height - height) * 0.5)
            cursor_x += width + column_gap
    return _LevelPlacement(
        positions=positions,
        rows=rows,
        columns=columns,
        loop_wire_ids=frozenset(loop_wire_ids),
    )


def _forward_wire(wire: _LevelWire) -> _LevelWire:
    if (wire.source_side, wire.target_side) not in _BACKWARD_SIDE_PAIRS:
        return wire
    return replace(
        wire,
        source_id=wire.target_id,
        target_id=wire.source_id,
        source_side=wire.target_side,
        target_side=wire.source_side,
        source_offset=wire.target_offset,
        target_offset=wire.source_offset,
    )


def _classified_wire(wire: _LevelWire, *, all_advance: bool) -> _LevelWire:
    if all_advance:
        return replace(wire, advance=True, row_bias=0)
    if wire.source_side == "bottom" and wire.target_side == "top":
        return replace(wire, advance=False, row_bias=0)
    row_bias = 1 if wire.source_side == "bottom" or wire.target_side == "top" else 0
    return replace(wire, advance=True, row_bias=row_bias)


def _loop_wire_ids(
    item_ids: Sequence[str],
    rects: Mapping[str, _Rect],
    wires: Sequence[_LevelWire],
) -> set[str]:
    outgoing: dict[str, list[_LevelWire]] = {item_id: [] for item_id in item_ids}
    has_incoming: set[str] = set()
    for wire in wires:
        outgoing[wire.source_id].append(wire)
        has_incoming.add(wire.target_id)
    for item_wires in outgoing.values():
        item_wires.sort(key=lambda wire: (rects[wire.target_id][0], rects[wire.target_id][1], wire.wire_id))
    ordered = sorted(item_ids, key=lambda item_id: (rects[item_id][0], rects[item_id][1], item_id))
    start_order = [item_id for item_id in ordered if item_id not in has_incoming]
    start_order.extend(item_id for item_id in ordered if item_id in has_incoming)

    loop_wire_ids: set[str] = set()
    on_stack: set[str] = set()
    visited: set[str] = set()
    for root_id in start_order:
        if root_id in visited:
            continue
        visited.add(root_id)
        on_stack.add(root_id)
        stack = [(root_id, iter(outgoing[root_id]))]
        while stack:
            item_id, pending_wires = stack[-1]
            descended = False
            for wire in pending_wires:
                if wire.target_id in on_stack:
                    loop_wire_ids.add(wire.wire_id)
                elif wire.target_id not in visited:
                    visited.add(wire.target_id)
                    on_stack.add(wire.target_id)
                    stack.append((wire.target_id, iter(outgoing[wire.target_id])))
                    descended = True
                    break
            if not descended:
                on_stack.discard(item_id)
                stack.pop()
    return loop_wire_ids


def _layer_columns(
    item_ids: Sequence[str],
    rects: Mapping[str, _Rect],
    wires: Sequence[_LevelWire],
) -> dict[str, int]:
    outgoing: dict[str, list[_LevelWire]] = {item_id: [] for item_id in item_ids}
    incoming_count = {item_id: 0 for item_id in item_ids}
    for wire in wires:
        outgoing[wire.source_id].append(wire)
        incoming_count[wire.target_id] += 1
    columns = {item_id: 0 for item_id in item_ids}
    remaining = dict(incoming_count)
    ready = [(rects[item_id][0], rects[item_id][1], item_id) for item_id in item_ids if remaining[item_id] == 0]
    heapq.heapify(ready)
    while ready:
        _x, _y, item_id = heapq.heappop(ready)
        for wire in outgoing[item_id]:
            target_id = wire.target_id
            columns[target_id] = max(columns[target_id], columns[item_id] + (1 if wire.advance else 0))
            remaining[target_id] -= 1
            if remaining[target_id] == 0:
                heapq.heappush(ready, (rects[target_id][0], rects[target_id][1], target_id))
    # Source pull: a root sits right before the successor it feeds instead of in column 0.
    for item_id in item_ids:
        if incoming_count[item_id] or not outgoing[item_id]:
            continue
        advance_columns = [columns[wire.target_id] - 1 for wire in outgoing[item_id] if wire.advance]
        branch_columns = [columns[wire.target_id] for wire in outgoing[item_id] if not wire.advance]
        terms = [min(values) for values in (advance_columns, branch_columns) if values]
        columns[item_id] = max(0, min(terms))
    return columns


def _layer_rows(
    item_ids: Sequence[str],
    rects: Mapping[str, _Rect],
    wires: Sequence[_LevelWire],
    columns: Mapping[str, int],
) -> dict[str, int]:
    components = _weak_components(item_ids, wires)
    components.sort(
        key=lambda component: (
            min(rects[item_id][1] for item_id in component),
            min(rects[item_id][0] for item_id in component),
            min(component),
        )
    )
    incoming: dict[str, list[_LevelWire]] = {item_id: [] for item_id in item_ids}
    outgoing: dict[str, list[_LevelWire]] = {item_id: [] for item_id in item_ids}
    for wire in wires:
        incoming[wire.target_id].append(wire)
        outgoing[wire.source_id].append(wire)
    branch_children = {
        item_id: sorted(
            (wire for wire in outgoing[item_id] if not wire.advance),
            key=lambda wire: (rects[wire.target_id][0], rects[wire.target_id][1], wire.wire_id),
        )
        for item_id in item_ids
    }

    rows: dict[str, int] = {}
    row_offset = 0
    for component in components:
        component_rows: dict[str, int] = {}
        occupied: set[tuple[int, int]] = set()
        # The cell straight below a node is kept for its first branch child in the same column, so a later
        # node cannot take it and push the branch down across that node.
        reserved_for: dict[tuple[int, int], str] = {}
        reserved_cell: dict[str, tuple[int, int]] = {}
        max_row = -1
        remaining = {item_id: len(incoming[item_id]) for item_id in component}
        placed_desired: dict[str, int] = {}

        def desired_row(item_id: str) -> int:
            cached = placed_desired.get(item_id)
            if cached is not None:
                return cached
            return 0 if max_row < 0 else max_row + 1

        def mark_ready(item_id: str) -> None:
            branch_rows = [component_rows[wire.source_id] + 1 for wire in incoming[item_id] if not wire.advance]
            advance_rows = [
                component_rows[wire.source_id] + wire.row_bias for wire in incoming[item_id] if wire.advance
            ]
            if branch_rows:
                placed_desired[item_id] = max(branch_rows)
            elif advance_rows:
                placed_desired[item_id] = _lower_median(advance_rows)
            ready.add(item_id)

        ready: set[str] = set()
        for item_id in component:
            if remaining[item_id] == 0:
                ready.add(item_id)
        while ready:
            # Within a column the node wanting the higher row goes first (then the drawn position), so a
            # decision is placed before whatever would otherwise take the cell below it.
            item_id = min(
                ready,
                key=lambda item_id: (
                    columns[item_id],
                    desired_row(item_id),
                    rects[item_id][1] + rects[item_id][3] * 0.5,
                    rects[item_id][0] + rects[item_id][2] * 0.5,
                    item_id,
                ),
            )
            ready.discard(item_id)
            column = columns[item_id]
            row = desired_row(item_id)
            own_cell = reserved_cell.pop(item_id, None)
            if own_cell is not None:
                del reserved_for[own_cell]
            while (column, row) in occupied or (column, row) in reserved_for:
                row += 1
            component_rows[item_id] = row
            occupied.add((column, row))
            max_row = max(max_row, row)
            below = (column, row + 1)
            if below not in occupied and below not in reserved_for:
                for wire in branch_children[item_id]:
                    child_id = wire.target_id
                    if columns[child_id] == column and child_id not in component_rows and child_id not in reserved_cell:
                        reserved_for[below] = child_id
                        reserved_cell[child_id] = below
                        break
            for wire in outgoing[item_id]:
                remaining[wire.target_id] -= 1
                if remaining[wire.target_id] == 0:
                    mark_ready(wire.target_id)
        for item_id, row in component_rows.items():
            rows[item_id] = row + row_offset
        row_offset += max_row + 1
    return rows


def _weak_components(item_ids: Sequence[str], wires: Sequence[_LevelWire]) -> list[list[str]]:
    parent = {item_id: item_id for item_id in item_ids}

    def find(item_id: str) -> str:
        root = item_id
        while parent[root] != root:
            root = parent[root]
        while parent[item_id] != root:
            parent[item_id], item_id = root, parent[item_id]
        return root

    for wire in wires:
        source_root = find(wire.source_id)
        target_root = find(wire.target_id)
        if source_root != target_root:
            parent[max(source_root, target_root)] = min(source_root, target_root)
    grouped: dict[str, list[str]] = {}
    for item_id in item_ids:
        grouped.setdefault(find(item_id), []).append(item_id)
    return list(grouped.values())


def _grid_positions(
    item_ids: Sequence[str],
    rects: Mapping[str, _Rect],
    rows: Mapping[str, int],
    columns: Mapping[str, int],
    *,
    anchor_x: float,
    anchor_y: float,
    column_gap: float,
    row_gap: float,
) -> tuple[dict[str, tuple[float, float]], dict[str, int], dict[str, int], float]:
    """Centre every item in its (column, row) cell; returns positions, compacted rows/columns, next band top."""
    column_index = {column: index for index, column in enumerate(sorted({columns[item_id] for item_id in item_ids}))}
    row_index = {row: index for index, row in enumerate(sorted({rows[item_id] for item_id in item_ids}))}
    widths = [0.0] * len(column_index)
    heights = [0.0] * len(row_index)
    for item_id in item_ids:
        _x, _y, width, height = rects[item_id]
        column = column_index[columns[item_id]]
        row = row_index[rows[item_id]]
        widths[column] = max(widths[column], width)
        heights[row] = max(heights[row], height)
    column_lefts = _band_starts(anchor_x, widths, column_gap)
    row_tops = _band_starts(anchor_y, heights, row_gap)
    positions: dict[str, tuple[float, float]] = {}
    for item_id in item_ids:
        _x, _y, width, height = rects[item_id]
        column = column_index[columns[item_id]]
        row = row_index[rows[item_id]]
        positions[item_id] = (
            column_lefts[column] + (widths[column] - width) * 0.5,
            row_tops[row] + (heights[row] - height) * 0.5,
        )
    next_band_top = row_tops[-1] + heights[-1] + row_gap if heights else anchor_y
    return (
        positions,
        {item_id: row_index[rows[item_id]] for item_id in item_ids},
        {item_id: column_index[columns[item_id]] for item_id in item_ids},
        next_band_top,
    )


def _band_starts(anchor: float, sizes: Sequence[float], gap: float) -> list[float]:
    starts: list[float] = []
    cursor = anchor
    for size in sizes:
        starts.append(cursor)
        cursor += size + gap
    return starts


def _in_place_placement(
    item_ids: Sequence[str],
    rects: Mapping[str, _Rect],
    *,
    column_gap: float,
    row_gap: float,
) -> _LevelPlacement:
    def center_x(item_id: str) -> float:
        return rects[item_id][0] + rects[item_id][2] * 0.5

    def center_y(item_id: str) -> float:
        return rects[item_id][1] + rects[item_id][3] * 0.5

    # An item joins the current row when it overlaps the row's first item vertically by at least half of the
    # smaller height (the row's smallest so far or its own). For equal heights this is |centre_y difference| <= h/2;
    # for mixed heights it keeps a 128 px decision beside an 84 px process with the same top edge in one row.
    row_groups: list[list[str]] = []
    for item_id in sorted(item_ids, key=lambda item_id: (center_y(item_id), center_x(item_id), item_id)):
        if row_groups:
            row = row_groups[-1]
            row_min_height = min(rects[member_id][3] for member_id in row)
            if _axis_overlap(rects[item_id], rects[row[0]], axis=1) >= 0.5 * min(rects[item_id][3], row_min_height):
                row.append(item_id)
                continue
        row_groups.append([item_id])
    rows = {item_id: index for index, row in enumerate(row_groups) for item_id in row}

    column_groups: list[list[str]] = []
    for item_id in sorted(item_ids, key=lambda item_id: (center_x(item_id), center_y(item_id), item_id)):
        if column_groups:
            column = column_groups[-1]
            column_min_width = min(rects[member_id][2] for member_id in column)
            shares_row = any(rows[member_id] == rows[item_id] for member_id in column)
            if not shares_row and _axis_overlap(rects[item_id], rects[column[0]], axis=0) >= 0.5 * min(
                rects[item_id][2], column_min_width
            ):
                column.append(item_id)
                continue
        column_groups.append([item_id])
    columns = {item_id: index for index, column in enumerate(column_groups) for item_id in column}

    # Gaps are measured between cells (median centre +- half the largest size), not between item edges: the
    # straightening polish shifts items inside their cells, so edge gaps would shrink on every rerun.
    row_gap_used = _clean_up_gap(
        [_cell_band([center_y(item_id) for item_id in row], max(rects[item_id][3] for item_id in row)) for row in row_groups],
        row_gap,
    )
    column_gap_used = _clean_up_gap(
        [
            _cell_band([center_x(item_id) for item_id in column], max(rects[item_id][2] for item_id in column))
            for column in column_groups
        ],
        column_gap,
    )
    positions, rows, columns, _band_top = _grid_positions(
        item_ids,
        rects,
        rows,
        columns,
        anchor_x=min(rects[item_id][0] for item_id in item_ids),
        anchor_y=min(rects[item_id][1] for item_id in item_ids),
        column_gap=column_gap_used,
        row_gap=row_gap_used,
    )
    return _LevelPlacement(positions=positions, rows=rows, columns=columns, loop_wire_ids=frozenset())


def _cell_band(centers: Sequence[float], size: float) -> tuple[float, float]:
    center = statistics.median(centers)
    return (center - size * 0.5, center + size * 0.5)


def _clean_up_gap(bands: Sequence[tuple[float, float]], default_gap: float) -> float:
    gaps = [
        next_band[0] - band[1]
        for band, next_band in zip(bands, bands[1:])
        if next_band[0] - band[1] > 0.0
    ]
    current = statistics.median(gaps) if gaps else default_gap
    return min(max(current, default_gap), 3.0 * default_gap)


def _polished_positions(
    placement: _LevelPlacement,
    rects: Mapping[str, _Rect],
    wires: Sequence[_LevelWire],
    *,
    movable_ids: Collection[str],
    level_ids: Sequence[str],
) -> dict[str, tuple[float, float]]:
    """Straighten same-row / same-column wires unless that creates an overlap.

    Group items move as whole blocks, so a wire into a group member is straightened by shifting the block.
    """
    positions = placement.positions
    constraints: list[PortAlignmentConstraint] = []
    for wire in wires:
        if wire.wire_id in placement.loop_wire_ids:
            continue
        source_id, target_id = wire.source_id, wire.target_id
        if source_id not in movable_ids or target_id not in movable_ids:
            continue
        source_row = placement.rows.get(source_id)
        source_column = placement.columns.get(source_id)
        source_x, source_y = positions[source_id]
        target_x, target_y = positions[target_id]
        if (
            source_row is not None
            and source_row == placement.rows.get(target_id)
            and wire.source_side in _HORIZONTAL_SIDES
            and wire.target_side in _HORIZONTAL_SIDES
        ):
            constraints.append(
                PortAlignmentConstraint(
                    source_node_id=source_id,
                    target_node_id=target_id,
                    axis="y",
                    source_anchor=source_y + wire.source_offset[1],
                    target_anchor=target_y + wire.target_offset[1],
                )
            )
        elif (
            source_column is not None
            and source_column == placement.columns.get(target_id)
            and wire.source_side in _VERTICAL_SIDES
            and wire.target_side in _VERTICAL_SIDES
        ):
            constraints.append(
                PortAlignmentConstraint(
                    source_node_id=source_id,
                    target_node_id=target_id,
                    axis="x",
                    source_anchor=source_x + wire.source_offset[0],
                    target_anchor=target_x + wire.target_offset[0],
                )
            )
    if not constraints:
        return positions
    offsets = build_port_alignment_offsets(node_ids=movable_ids, constraints=constraints)
    if not offsets:
        return positions
    polished = dict(positions)
    for item_id, (dx, dy) in offsets.items():
        x, y = positions[item_id]
        polished[item_id] = (x + dx, y + dy)
    # Keep the block's top-left where the placement anchored it; otherwise a repeated Tidy would re-anchor at the
    # polished corner and drift by the polish offsets every time.
    shift_x = min(x for x, _y in positions.values()) - min(x for x, _y in polished.values())
    shift_y = min(y for _x, y in positions.values()) - min(y for _x, y in polished.values())
    if shift_x or shift_y:
        polished = {item_id: (x + shift_x, y + shift_y) for item_id, (x, y) in polished.items()}

    def rect_at(position_map: Mapping[str, tuple[float, float]], item_id: str) -> _Rect:
        x, y, width, height = rects[item_id]
        position = position_map.get(item_id)
        return (x, y, width, height) if position is None else (position[0], position[1], width, height)

    moved_ids = sorted(item_id for item_id, position in polished.items() if position != positions[item_id])
    for moved_id in moved_ids:
        for other_id in level_ids:
            if other_id == moved_id:
                continue
            if _rects_overlap(rect_at(polished, moved_id), rect_at(polished, other_id)) and not _rects_overlap(
                rect_at(positions, moved_id), rect_at(positions, other_id)
            ):
                return positions
    return polished


def _axis_overlap(first: _Rect, second: _Rect, *, axis: int) -> float:
    """Length of the overlap of two rectangles along x (``axis=0``) or y (``axis=1``); negative when apart."""
    start = max(first[axis], second[axis])
    end = min(first[axis] + first[axis + 2], second[axis] + second[axis + 2])
    return end - start


def _rects_overlap(first: _Rect, second: _Rect) -> bool:
    return (
        first[0] < second[0] + second[2]
        and first[0] + first[2] > second[0]
        and first[1] < second[1] + second[3]
        and first[1] + first[3] > second[1]
    )


def _lower_median(values: Sequence[int]) -> int:
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]


def _item_rect(item: TidyItem) -> _Rect:
    return (float(item.x), float(item.y), float(item.width), float(item.height))


def _items_by_id(items: Sequence[TidyItem]) -> dict[str, TidyItem]:
    item_by_id: dict[str, TidyItem] = {}
    for item in items:
        if item.item_id in item_by_id:
            raise ValueError(f"Duplicate tidy item id: {item.item_id!r}")
        item_by_id[item.item_id] = item
    return item_by_id


def _valid_wires(wires: Sequence[TidyWire], item_by_id: Mapping[str, TidyItem]) -> list[TidyWire]:
    wire_by_id: dict[str, TidyWire] = {}
    for wire in sorted(wires, key=_wire_sort_key):
        if wire.source_id not in item_by_id or wire.target_id not in item_by_id:
            continue
        if wire.source_id == wire.target_id:
            continue
        wire_by_id.setdefault(wire.wire_id, wire)
    return [wire_by_id[wire_id] for wire_id in sorted(wire_by_id)]


def _wire_sort_key(wire: TidyWire) -> tuple[object, ...]:
    return (
        wire.wire_id,
        wire.source_id,
        wire.target_id,
        str(wire.source_side),
        str(wire.target_side),
        tuple(float(value) for value in wire.source_offset),
        tuple(float(value) for value in wire.target_offset),
    )


def _sanitized_parents(item_by_id: Mapping[str, TidyItem]) -> dict[str, str | None]:
    parents: dict[str, str | None] = {}
    for item_id, item in item_by_id.items():
        parent = item_by_id.get(item.parent_group_id) if item.parent_group_id is not None else None
        valid = parent is not None and parent.is_group and item.parent_group_id != item_id
        parents[item_id] = item.parent_group_id if valid else None
    for item_id in sorted(parents):
        path = {item_id}
        child_id = item_id
        parent_id = parents[item_id]
        while parent_id is not None:
            if parent_id in path:
                parents[child_id] = None
                break
            path.add(parent_id)
            child_id = parent_id
            parent_id = parents[parent_id]
    return parents


def _normalized_mode(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized not in TIDY_MODES:
        raise ValueError(f"Unknown tidy mode: {mode!r}")
    return normalized


def _normalized_direction(direction: str) -> str:
    normalized = str(direction or "").strip().lower()
    if normalized not in TIDY_DIRECTIONS:
        raise ValueError(f"Unknown tidy direction: {direction!r}")
    return normalized


def _normalized_side(side: str) -> str:
    normalized = str(side or "").strip().lower()
    return normalized if normalized in _HORIZONTAL_SIDES or normalized in _VERTICAL_SIDES else ""


def _normalized_gap(gap: float) -> float:
    value = float(gap)
    if not math.isfinite(value):
        raise ValueError(f"Tidy gaps must be finite, got {gap!r}")
    return max(0.0, value)


__all__ = [
    "DEFAULT_TIDY_COLUMN_GAP",
    "DEFAULT_TIDY_ROW_GAP",
    "TIDY_DIRECTIONS",
    "TIDY_DIRECTION_AUTO",
    "TIDY_DIRECTION_LEFT_TO_RIGHT",
    "TIDY_DIRECTION_TOP_TO_BOTTOM",
    "TIDY_MODES",
    "TIDY_MODE_AUTO_LAYOUT",
    "TIDY_MODE_IN_PLACE",
    "TidyItem",
    "TidyLayoutResult",
    "TidySettings",
    "TidyWire",
    "build_tidy_layout",
    "resolve_tidy_direction",
]
