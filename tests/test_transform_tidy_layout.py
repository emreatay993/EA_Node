from __future__ import annotations

import random
import time

import pytest

from ea_node_editor.graph.group_backdrop_geometry import (
    GROUP_BACKDROP_WRAP_PADDING,
    GROUP_BACKDROP_WRAP_TOP_PADDING,
    GroupBackdropCandidate,
    build_group_backdrop_wrap_bounds,
)
from ea_node_editor.graph.transform_layout_ops import (
    LayoutNodeBounds,
    PortAlignmentConstraint,
    build_collision_avoidance_position_updates,
    build_port_alignment_offsets,
)
from ea_node_editor.graph.transform_tidy_layout import (
    DEFAULT_TIDY_COLUMN_GAP,
    DEFAULT_TIDY_ROW_GAP,
    TIDY_DIRECTION_AUTO,
    TIDY_DIRECTION_LEFT_TO_RIGHT,
    TIDY_DIRECTION_TOP_TO_BOTTOM,
    TIDY_MODE_IN_PLACE,
    TidyItem,
    TidySettings,
    TidyWire,
    build_tidy_layout,
    resolve_tidy_direction,
)

PROCESS = (224.0, 84.0)
DECISION = (236.0, 128.0)
START = (180.0, 78.0)
COLUMN_GAP = DEFAULT_TIDY_COLUMN_GAP
ROW_GAP = DEFAULT_TIDY_ROW_GAP
_TRANSPOSED_SIDES = {"left": "top", "top": "left", "right": "bottom", "bottom": "right"}


def _item(item_id: str, x: float, y: float, size: tuple[float, float] = PROCESS, **kwargs) -> TidyItem:
    return TidyItem(item_id=item_id, x=float(x), y=float(y), width=size[0], height=size[1], **kwargs)


def _side_offset(item: TidyItem, side: str) -> tuple[float, float]:
    return {
        "left": (0.0, item.height * 0.5),
        "right": (item.width, item.height * 0.5),
        "top": (item.width * 0.5, 0.0),
        "bottom": (item.width * 0.5, item.height),
    }[side]


def _wire(
    items: list[TidyItem],
    wire_id: str,
    source_id: str,
    target_id: str,
    source_side: str = "right",
    target_side: str = "left",
) -> TidyWire:
    by_id = {item.item_id: item for item in items}
    return TidyWire(
        wire_id=wire_id,
        source_id=source_id,
        target_id=target_id,
        source_side=source_side,
        target_side=target_side,
        source_offset=_side_offset(by_id[source_id], source_side),
        target_offset=_side_offset(by_id[target_id], target_side),
    )


def _layout(items: list[TidyItem], wires: list[TidyWire], **settings):
    return build_tidy_layout(items, wires, TidySettings(**settings))


def _rects(result, items: list[TidyItem]) -> dict[str, tuple[float, float, float, float]]:
    rects: dict[str, tuple[float, float, float, float]] = {}
    for item in items:
        x, y = result.positions.get(item.item_id, (item.x, item.y))
        width, height = result.group_sizes.get(item.item_id, (item.width, item.height))
        rects[item.item_id] = (x, y, width, height)
    return rects


def _center_x(rect: tuple[float, float, float, float]) -> float:
    return rect[0] + rect[2] * 0.5


def _center_y(rect: tuple[float, float, float, float]) -> float:
    return rect[1] + rect[3] * 0.5


def _contains(outer: tuple[float, float, float, float], inner: tuple[float, float, float, float]) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[0] + outer[2] >= inner[0] + inner[2]
        and outer[1] + outer[3] >= inner[1] + inner[3]
    )


def _wrap(rects: list[tuple[str, tuple[float, float, float, float]]], group_ids: set[str] = frozenset()):
    return build_group_backdrop_wrap_bounds(
        [
            GroupBackdropCandidate(
                node_id=item_id,
                scope_path=(),
                is_backdrop=item_id in group_ids,
                x=rect[0],
                y=rect[1],
                width=rect[2],
                height=rect[3],
            )
            for item_id, rect in rects
        ]
    )


# --- direction ---------------------------------------------------------------------------------


def _side_wires(pairs: list[tuple[str, str]]) -> list[TidyWire]:
    return [
        TidyWire(
            wire_id=f"w{index}",
            source_id=f"s{index}",
            target_id=f"t{index}",
            source_side=source_side,
            target_side=target_side,
            source_offset=(0.0, 0.0),
            target_offset=(0.0, 0.0),
        )
        for index, (source_side, target_side) in enumerate(pairs)
    ]


def test_direction_is_detected_from_the_port_sides_the_wires_use() -> None:
    horizontal = _side_wires([("right", "left")] * 3)
    vertical = _side_wires([("bottom", "top")] * 3)
    tie = _side_wires([("right", "left"), ("bottom", "top")])

    assert resolve_tidy_direction(horizontal, TIDY_DIRECTION_AUTO) == TIDY_DIRECTION_LEFT_TO_RIGHT
    assert resolve_tidy_direction(vertical, TIDY_DIRECTION_AUTO) == TIDY_DIRECTION_TOP_TO_BOTTOM
    assert resolve_tidy_direction(tie, TIDY_DIRECTION_AUTO) == TIDY_DIRECTION_LEFT_TO_RIGHT
    assert resolve_tidy_direction([], TIDY_DIRECTION_AUTO) == TIDY_DIRECTION_LEFT_TO_RIGHT


def test_mixed_wires_count_on_the_source_side_axis_and_explicit_direction_wins() -> None:
    mixed = _side_wires([("bottom", "left"), ("bottom", "left"), ("right", "top"), ("", "top")])

    # bottom->left twice counts vertical; right->top and an unknown source side count horizontal.
    assert resolve_tidy_direction(mixed[:3], TIDY_DIRECTION_AUTO) == TIDY_DIRECTION_TOP_TO_BOTTOM
    assert resolve_tidy_direction(mixed, TIDY_DIRECTION_AUTO) == TIDY_DIRECTION_LEFT_TO_RIGHT
    vertical = _side_wires([("bottom", "top")] * 3)
    assert resolve_tidy_direction(vertical, TIDY_DIRECTION_LEFT_TO_RIGHT) == TIDY_DIRECTION_LEFT_TO_RIGHT
    assert resolve_tidy_direction([], TIDY_DIRECTION_TOP_TO_BOTTOM) == TIDY_DIRECTION_TOP_TO_BOTTOM


def test_unknown_mode_or_direction_is_rejected() -> None:
    items = [_item("a", 0, 0), _item("b", 400, 0)]
    with pytest.raises(ValueError):
        resolve_tidy_direction([], "diagonal")
    with pytest.raises(ValueError):
        _layout(items, [], mode="shuffle")
    with pytest.raises(ValueError):
        _layout(items, [], direction="sideways")
    with pytest.raises(ValueError):
        _layout([*items, _item("a", 10, 10)], [])


# --- auto layout --------------------------------------------------------------------------------


def test_left_to_right_chain_shares_one_row_with_column_gaps_from_the_original_anchor() -> None:
    items = [
        _item("a", 40, 210, START),
        _item("b", 330, 120, PROCESS),
        _item("c", 610, 260, DECISION),
        _item("d", 900, 150, PROCESS),
    ]
    wires = [_wire(items, "ab", "a", "b"), _wire(items, "bc", "b", "c"), _wire(items, "cd", "c", "d")]

    result = _layout(items, wires)
    rects = _rects(result, items)

    assert result.direction == TIDY_DIRECTION_LEFT_TO_RIGHT
    assert result.laid_out_level_count == 1
    assert {_center_y(rect) for rect in rects.values()} == {120.0 + DECISION[1] * 0.5}
    ordered = [rects[item_id] for item_id in ("a", "b", "c", "d")]
    for left, right in zip(ordered, ordered[1:]):
        assert right[0] - (left[0] + left[2]) == pytest.approx(COLUMN_GAP)
    assert min(rect[0] for rect in rects.values()) == 40.0
    assert min(rect[1] for rect in rects.values()) == 120.0
    assert [rect[0] for rect in ordered] == [40.0, 316.0, 636.0, 968.0]


def test_decision_branch_drops_into_the_next_row_of_the_same_column() -> None:
    items = [
        _item("a", 0, 0, START),
        _item("d", 300, 40, DECISION),
        _item("e", 600, 10, PROCESS),
        _item("f", 310, 260, PROCESS),
    ]
    wires = [
        _wire(items, "ad", "a", "d"),
        _wire(items, "de", "d", "e"),
        _wire(items, "df", "d", "f", "bottom", "top"),
    ]

    rects = _rects(_layout(items, wires), items)

    assert _center_x(rects["f"]) == pytest.approx(_center_x(rects["d"]))
    assert rects["f"][1] == pytest.approx(0.0 + DECISION[1] + ROW_GAP)
    assert _center_y(rects["e"]) == pytest.approx(_center_y(rects["d"]))
    assert _center_y(rects["a"]) == pytest.approx(_center_y(rects["d"]))


def _assert_branch_directly_below(rects, parent_id: str, child_id: str, other_ids: tuple[str, ...]) -> None:
    parent, child = rects[parent_id], rects[child_id]
    assert _center_x(child) == pytest.approx(_center_x(parent))
    assert child[1] == pytest.approx(parent[1] + DECISION[1] + ROW_GAP)
    for other_id in other_ids:
        other = rects[other_id]
        in_column = other[0] < parent[0] + parent[2] and other[0] + other[2] > parent[0]
        between = other[1] < child[1] and other[1] + other[3] > parent[1] + parent[3]
        assert not (in_column and between), f"{other_id} sits on the {parent_id} -> {child_id} branch wire"


def test_branch_keeps_the_cell_below_its_decision_against_a_second_root() -> None:
    # r feeds e and is pulled into the decision's column; drawn above d, it used to be placed first and take the
    # cell below d, pushing the "no" branch f a row down so its wire crossed r.
    items = [
        _item("a", 0, 200, START),
        _item("d", 300, 180, DECISION),
        _item("e", 650, 190),
        _item("f", 310, 450),
        _item("r", 320, -100),
    ]
    wires = [
        _wire(items, "ad", "a", "d"),
        _wire(items, "de", "d", "e"),
        _wire(items, "df", "d", "f", "bottom", "top"),
        _wire(items, "re", "r", "e"),
    ]

    rects = _rects(_layout(items, wires), items)

    _assert_branch_directly_below(rects, "d", "f", ("r", "a", "e"))
    assert _center_y(rects["e"]) == pytest.approx(_center_y(rects["d"]))


def test_branch_keeps_the_cell_below_its_decision_against_an_elbow_neighbour() -> None:
    # q hangs off p's bottom port (one column on, one row down) and is drawn above d, so it used to claim the cell
    # below d before d was even placed.
    items = [
        _item("p", 0, 100),
        _item("d", 320, 200, DECISION),
        _item("q", 330, -80),
        _item("f", 325, 450),
        _item("e", 700, 200),
    ]
    wires = [
        _wire(items, "pd", "p", "d"),
        _wire(items, "pq", "p", "q", "bottom", "left"),
        _wire(items, "df", "d", "f", "bottom", "top"),
        _wire(items, "de", "d", "e"),
    ]

    rects = _rects(_layout(items, wires), items)

    _assert_branch_directly_below(rects, "d", "f", ("q", "p", "e"))
    assert rects["q"][1] > rects["f"][1]


def _flowchart_with_optional_loop(*, with_loop: bool) -> tuple[list[TidyItem], list[TidyWire]]:
    items = [
        _item("s", 0, 30, START),
        _item("b", 260, 0, PROCESS),
        _item("d", 560, 50, DECISION),
        _item("e", 880, 20, PROCESS),
        _item("f", 600, 300, PROCESS),
    ]
    wires = [
        _wire(items, "sb", "s", "b"),
        _wire(items, "bd", "b", "d"),
        _wire(items, "de", "d", "e"),
        _wire(items, "df", "d", "f", "bottom", "top"),
    ]
    if with_loop:
        wires.append(_wire(items, "loop", "f", "b", "left", "bottom"))
    return items, wires


def test_loop_back_wire_is_reported_and_does_not_change_the_layout() -> None:
    items, wires = _flowchart_with_optional_loop(with_loop=True)
    plain_items, plain_wires = _flowchart_with_optional_loop(with_loop=False)

    looped = _layout(items, wires)
    plain = _layout(plain_items, plain_wires)

    assert looped.loop_wire_ids == ("loop",)
    assert plain.loop_wire_ids == ()
    assert looped.positions == plain.positions


def test_backwards_drawn_same_axis_wire_lays_out_like_the_forward_one() -> None:
    items = [_item("a", 0, 100), _item("b", 300, 0), _item("c", 600, 200)]
    forward = [_wire(items, "ab", "a", "b"), _wire(items, "bc", "b", "c")]
    backward = [_wire(items, "ab", "a", "b"), _wire(items, "bc", "c", "b", "left", "right")]

    assert _layout(items, backward).positions == _layout(items, forward).positions


def _transposed_input(items: list[TidyItem], wires: list[TidyWire]) -> tuple[list[TidyItem], list[TidyWire]]:
    transposed_items = [
        TidyItem(
            item_id=item.item_id,
            x=item.y,
            y=item.x,
            width=item.height,
            height=item.width,
            parent_group_id=item.parent_group_id,
            is_group=item.is_group,
            rigid=item.rigid,
            arrangeable=item.arrangeable,
        )
        for item in items
    ]
    transposed_wires = [
        TidyWire(
            wire_id=wire.wire_id,
            source_id=wire.source_id,
            target_id=wire.target_id,
            source_side=_TRANSPOSED_SIDES[wire.source_side],
            target_side=_TRANSPOSED_SIDES[wire.target_side],
            source_offset=(wire.source_offset[1], wire.source_offset[0]),
            target_offset=(wire.target_offset[1], wire.target_offset[0]),
        )
        for wire in wires
    ]
    return transposed_items, transposed_wires


def test_top_to_bottom_is_the_transpose_of_left_to_right() -> None:
    items, wires = _flowchart_with_optional_loop(with_loop=True)
    items.append(_item("loose", 200, 500, START))

    left_to_right = _layout(items, wires, direction=TIDY_DIRECTION_LEFT_TO_RIGHT)
    top_to_bottom = _layout(*_transposed_input(items, wires), direction=TIDY_DIRECTION_TOP_TO_BOTTOM)

    assert top_to_bottom.direction == TIDY_DIRECTION_TOP_TO_BOTTOM
    assert top_to_bottom.loop_wire_ids == left_to_right.loop_wire_ids
    assert top_to_bottom.positions == {
        item_id: (y, x) for item_id, (x, y) in left_to_right.positions.items()
    }


def test_components_stack_by_position_and_loose_items_fill_a_final_band() -> None:
    items = [
        _item("x1", 0, 300),
        _item("x2", 300, 320),
        _item("y1", 0, 0),
        _item("y2", 300, 20),
        _item("loose", 700, 500),
        _item("note", 900, 900, (160.0, 60.0), arrangeable=False),
    ]
    wires = [_wire(items, "x", "x1", "x2"), _wire(items, "y", "y1", "y2")]

    result = _layout(items, wires)
    rects = _rects(result, items)

    assert "note" not in result.positions
    assert _center_y(rects["y1"]) == _center_y(rects["y2"]) == 42.0
    second_row_top = PROCESS[1] + ROW_GAP
    assert rects["x1"][1] == rects["x2"][1] == second_row_top
    assert rects["loose"][1] == second_row_top + PROCESS[1] + ROW_GAP
    assert rects["loose"][0] == 0.0
    assert rects["x1"][0] == rects["y1"][0] == 0.0
    assert rects["x2"][0] == rects["y2"][0] == PROCESS[0] + COLUMN_GAP


def test_all_advance_forces_a_top_to_bottom_drawn_chain_into_a_single_row() -> None:
    items = [_item("a", 0, 0), _item("b", 20, 200), _item("c", -10, 400)]
    wires = [_wire(items, "ab", "a", "b", "bottom", "top"), _wire(items, "bc", "b", "c", "bottom", "top")]

    forced = _rects(_layout(items, wires, direction=TIDY_DIRECTION_LEFT_TO_RIGHT, all_advance=True), items)
    branched = _rects(_layout(items, wires, direction=TIDY_DIRECTION_LEFT_TO_RIGHT), items)

    assert len({_center_y(rect) for rect in forced.values()}) == 1
    assert forced["a"][0] < forced["b"][0] < forced["c"][0]
    assert len({_center_x(rect) for rect in branched.values()}) == 1
    assert branched["a"][1] < branched["b"][1] < branched["c"][1]


def test_all_advance_is_ignored_when_the_direction_is_auto() -> None:
    items = [_item("a", 0, 0), _item("b", 20, 200)]
    wires = [_wire(items, "ab", "a", "b", "bottom", "top")]

    result = _layout(items, wires, all_advance=True)
    rects = _rects(result, items)

    assert result.direction == TIDY_DIRECTION_TOP_TO_BOTTOM
    assert _center_x(rects["a"]) == _center_x(rects["b"])


def test_source_pull_places_a_root_right_before_the_node_it_feeds() -> None:
    items = [
        _item("a", 0, 0),
        _item("b", 300, 0),
        _item("c", 600, 0),
        _item("d", 900, 0),
        _item("r", 0, 400),
    ]
    wires = [
        _wire(items, "ab", "a", "b"),
        _wire(items, "bc", "b", "c"),
        _wire(items, "cd", "c", "d"),
        _wire(items, "rd", "r", "d"),
    ]

    rects = _rects(_layout(items, wires), items)

    assert _center_x(rects["r"]) == _center_x(rects["c"])
    assert rects["r"][1] == PROCESS[1] + ROW_GAP


# --- groups -------------------------------------------------------------------------------------


def _chain_group_input() -> tuple[list[TidyItem], list[TidyWire]]:
    items = [
        _item("g", 0, 0, (1000.0, 400.0), is_group=True),
        _item("m1", 40, 120, parent_group_id="g"),
        _item("m2", 400, 200, parent_group_id="g"),
        _item("m3", 700, 110, parent_group_id="g"),
        _item("note", 300, 320, (160.0, 60.0), parent_group_id="g", arrangeable=False),
        _item("outside", -400, 150, START),
    ]
    wires = [
        _wire(items, "m12", "m1", "m2"),
        _wire(items, "m23", "m2", "m3"),
        _wire(items, "in", "outside", "m1"),
    ]
    return items, wires


def test_group_members_are_laid_out_inside_a_refitted_backdrop() -> None:
    items, wires = _chain_group_input()

    result = _layout(items, wires)
    rects = _rects(result, items)

    assert result.laid_out_level_count == 2
    assert len({_center_y(rects[member_id]) for member_id in ("m1", "m2", "m3")}) == 1
    box = _wrap([(child_id, rects[child_id]) for child_id in ("m1", "m2", "m3", "note")])
    assert rects["g"] == pytest.approx((box.x, box.y, box.width, box.height))
    assert "g" in result.group_sizes
    for child_id in ("m1", "m2", "m3", "note"):
        assert _contains(rects["g"], rects[child_id])
    # The members are anchored at their original top-left (40, 110) and the unwired note keeps
    # (300, 320), so the refitted box starts at (40 - 32, 110 - 96); the note keeps that offset.
    assert rects["note"][0] - rects["g"][0] == pytest.approx(300.0 - (40.0 - GROUP_BACKDROP_WRAP_PADDING))
    assert rects["note"][1] - rects["g"][1] == pytest.approx(320.0 - (110.0 - GROUP_BACKDROP_WRAP_TOP_PADDING))
    # The outside item feeds the group block, so the group sits one column to its right, and the wire into the
    # nested member runs straight: the block and the outside item are shifted so the two ports share one line.
    assert rects["g"][0] == pytest.approx(rects["outside"][0] + START[0] + COLUMN_GAP)
    assert _center_y(rects["outside"]) == pytest.approx(_center_y(rects["m1"]))


def test_nested_groups_are_laid_out_deepest_first_and_stay_nested() -> None:
    items = [
        _item("outer", 0, 0, (1200.0, 700.0), is_group=True),
        _item("inner", 40, 100, (700.0, 400.0), is_group=True, parent_group_id="outer"),
        _item("p", 900, 300, parent_group_id="outer"),
        _item("i1", 80, 200, parent_group_id="inner"),
        _item("i2", 400, 260, parent_group_id="inner"),
    ]
    wires = [_wire(items, "i12", "i1", "i2"), _wire(items, "i2p", "i2", "p")]

    result = _layout(items, wires)
    rects = _rects(result, items)

    assert result.laid_out_level_count == 2
    assert _contains(rects["outer"], rects["inner"])
    assert _contains(rects["outer"], rects["p"])
    assert _contains(rects["inner"], rects["i1"])
    assert _contains(rects["inner"], rects["i2"])
    # inner: members at x 80 and 400 (width 224) -> box (80-32, 200-96, 544+64, 84+96+56). At the outer level the
    # lifted wire i2 -> p is straightened: the member row sits 20 px below the block's centre (96 px title padding),
    # so the solver splits 20 px between the block and p, then the level is shifted back to its anchored top-left.
    assert rects["inner"] == pytest.approx((48.0, 104.0, 608.0, 236.0))
    assert rects["p"][1] == pytest.approx(200.0)
    assert _center_y(rects["i2"]) == pytest.approx(_center_y(rects["p"]))
    # outer: inner block then p one column gap to its right (x 752) -> box around (48..976, 104..340).
    assert rects["outer"] == pytest.approx((16.0, 8.0, 992.0, 388.0))
    assert rects["p"][0] - (rects["inner"][0] + rects["inner"][2]) == pytest.approx(COLUMN_GAP)


def test_top_to_bottom_group_keeps_its_title_padding_on_top() -> None:
    items = [
        _item("g", 0, 0, (400.0, 900.0), is_group=True),
        _item("m1", 40, 120, parent_group_id="g"),
        _item("m2", 60, 400, parent_group_id="g"),
        _item("m3", 30, 650, parent_group_id="g"),
    ]
    wires = [
        _wire(items, "m12", "m1", "m2", "bottom", "top"),
        _wire(items, "m23", "m2", "m3", "bottom", "top"),
    ]

    result = _layout(items, wires)
    rects = _rects(result, items)

    assert result.direction == TIDY_DIRECTION_TOP_TO_BOTTOM
    member_tops = [rects[member_id][1] for member_id in ("m1", "m2", "m3")]
    member_lefts = [rects[member_id][0] for member_id in ("m1", "m2", "m3")]
    assert rects["g"][1] == pytest.approx(min(member_tops) - GROUP_BACKDROP_WRAP_TOP_PADDING)
    assert rects["g"][0] == pytest.approx(min(member_lefts) - GROUP_BACKDROP_WRAP_PADDING)
    assert len({_center_x(rects[member_id]) for member_id in ("m1", "m2", "m3")}) == 1


def test_group_with_one_arrangeable_child_keeps_its_size_and_child_offsets() -> None:
    items = [
        _item("g", 0, 0, (400.0, 300.0), is_group=True),
        _item("m", 40, 120, parent_group_id="g"),
        _item("note", 200, 220, (120.0, 50.0), parent_group_id="g", arrangeable=False),
        _item("outside", -500, 400, START),
    ]
    wires = [_wire(items, "in", "outside", "m")]

    result = _layout(items, wires)
    rects = _rects(result, items)

    assert result.laid_out_level_count == 1
    assert "g" not in result.group_sizes
    assert "g" in result.positions
    for child_id, original in (("m", (40.0, 120.0)), ("note", (200.0, 220.0))):
        assert rects[child_id][0] - rects["g"][0] == pytest.approx(original[0])
        assert rects[child_id][1] - rects["g"][1] == pytest.approx(original[1])


def test_unwired_annotation_inside_a_group_is_pushed_off_the_laid_out_members() -> None:
    items = [
        _item("g", -40, -100, (600.0, 700.0), is_group=True),
        _item("s1", 0, 0, parent_group_id="g"),
        _item("s2", 0, 200, parent_group_id="g"),
        _item("s3", 0, 400, parent_group_id="g"),
        _item("note", 300, 0, (228.0, 152.0), parent_group_id="g", arrangeable=False),
    ]
    wires = [_wire(items, "s12", "s1", "s2"), _wire(items, "s23", "s2", "s3")]

    rects = _rects(_layout(items, wires), items)

    for step_id in ("s1", "s2", "s3"):
        note, step = rects["note"], rects[step_id]
        assert not (
            note[0] < step[0] + step[2]
            and note[0] + note[2] > step[0]
            and note[1] < step[1] + step[3]
            and note[1] + note[3] > step[1]
        ), step_id
    assert _contains(rects["g"], rects["note"])


def test_rigid_group_only_translates_with_its_children() -> None:
    items = [
        _item("a", 0, 0),
        _item("r", 500, 500, (300.0, 200.0), is_group=True, rigid=True),
        _item("c1", 520, 600, parent_group_id="r"),
        _item("c2", 650, 610, parent_group_id="r"),
    ]
    wires = [_wire(items, "ar", "a", "r"), _wire(items, "c12", "c1", "c2")]

    result = _layout(items, wires)
    rects = _rects(result, items)

    assert result.laid_out_level_count == 1
    assert result.group_sizes == {}
    dx = rects["r"][0] - 500.0
    dy = rects["r"][1] - 500.0
    assert (dx, dy) != (0.0, 0.0)
    assert rects["c1"][:2] == pytest.approx((520.0 + dx, 600.0 + dy))
    assert rects["c2"][:2] == pytest.approx((650.0 + dx, 610.0 + dy))


def test_fewer_than_two_arrangeable_items_lays_out_nothing() -> None:
    items = [_item("a", 0, 0), _item("note", 300, 0, arrangeable=False)]

    result = _layout(items, [])

    assert result.laid_out_level_count == 0
    assert result.positions == {}
    assert result.group_sizes == {}


def test_wires_to_unknown_items_and_self_wires_are_ignored() -> None:
    items = [_item("a", 0, 0), _item("b", 50, 300)]
    stray = [
        _wire(items, "ab", "a", "b"),
        TidyWire("ghost", "a", "missing", "right", "left", (0.0, 0.0), (0.0, 0.0)),
        TidyWire("self", "a", "a", "right", "left", (0.0, 0.0), (0.0, 0.0)),
    ]

    assert _layout(items, stray).positions == _layout(items, stray[:1]).positions


# --- clean up in place --------------------------------------------------------------------------


def test_in_place_clean_up_snaps_jittered_rows_and_keeps_their_order() -> None:
    items = [
        _item("p1", 0, 5),
        _item("p2", 320, -10),
        _item("p3", 640, 12),
        _item("q1", 10, 300),
        _item("q2", 330, 285),
        _item("q3", 650, 310),
    ]

    result = _layout(items, [], mode=TIDY_MODE_IN_PLACE)
    rects = _rects(result, items)

    assert result.direction == ""
    assert result.laid_out_level_count == 1
    assert {_center_y(rects[item_id]) for item_id in ("p1", "p2", "p3")} == {-10.0 + 42.0}
    assert {_center_y(rects[item_id]) for item_id in ("q1", "q2", "q3")} == {266.0 + 42.0}
    # Gaps are measured between cells (median centre +- half the tallest height): rows centred at 47 and 342 leave
    # 211 px, clamped to 3 x 64 = 192; columns centred at 117 / 437 / 757 leave 96 px (the default minimum).
    assert rects["q1"][1] - (rects["p1"][1] + PROCESS[1]) == 192.0
    assert [rects[item_id][0] for item_id in ("p1", "p2", "p3")] == [0.0, 320.0, 640.0]
    assert [rects[item_id][0] for item_id in ("q1", "q2", "q3")] == [0.0, 320.0, 640.0]


def test_in_place_clean_up_centres_a_vertical_stack_and_separates_same_row_items() -> None:
    stack = [_item("s1", 0, 0), _item("s2", 15, 150), _item("s3", -10, 300)]
    stacked = _rects(_layout(stack, [], mode=TIDY_MODE_IN_PLACE), stack)
    assert {_center_x(rect) for rect in stacked.values()} == {-10.0 + 112.0}
    assert [stacked[item_id][1] for item_id in ("s1", "s2", "s3")] == [0.0, 150.0, 300.0]

    crowded = [_item("left", 0, 0), _item("right", 100, 0)]
    separated = _rects(_layout(crowded, [], mode=TIDY_MODE_IN_PLACE), crowded)
    assert separated["left"][0] == 0.0
    assert separated["right"][0] == PROCESS[0] + COLUMN_GAP
    assert separated["left"][1] == separated["right"][1] == 0.0


def test_in_place_clean_up_keeps_mixed_height_shapes_placed_by_their_top_edge_in_one_row() -> None:
    # Placed by top-left, a 128 px decision's centre sits 22 px below an 84 px process's; with some jitter the
    # centres differ by 52 / 55 px (more than half the smaller height, 42 px), yet the shapes overlap vertically by
    # 54 / 51 px and clearly share a row.
    items = [
        _item("p1", 0, 0),
        _item("d1", 320, 30, DECISION),
        _item("p2", 700, 10),
        _item("p3", 0, 300),
        _item("d2", 330, 333, DECISION),
    ]

    rects = _rects(_layout(items, [], mode=TIDY_MODE_IN_PLACE), items)

    assert len({_center_y(rects[item_id]) for item_id in ("p1", "d1", "p2")}) == 1
    assert len({_center_y(rects[item_id]) for item_id in ("p3", "d2")}) == 1
    assert _center_y(rects["p1"]) < _center_y(rects["p3"])
    assert _center_x(rects["d1"]) == _center_x(rects["d2"])


def test_in_place_clean_up_with_offset_data_ports_is_repeatable() -> None:
    # Straightening shifts the items inside their row cells; gaps are measured between cells, so a rerun of the
    # clean-up must not creep the rows together.
    items = [_item("a", 0, 0, (160.0, 40.0)), _item("b", 300, 0, (210.0, 92.0))]
    items += [_item("d", 0, 300, (160.0, 40.0)), _item("e", 300, 300, (210.0, 92.0))]
    wires = [
        TidyWire("ab", "a", "b", "right", "left", (147.0, 20.0), (13.0, 39.0)),
        TidyWire("de", "d", "e", "right", "left", (147.0, 20.0), (13.0, 60.0)),
    ]
    first = _layout(items, wires, mode=TIDY_MODE_IN_PLACE)
    tidied = [
        _item(item.item_id, *first.positions.get(item.item_id, (item.x, item.y)), (item.width, item.height))
        for item in items
    ]

    assert first.positions
    assert _layout(tidied, wires, mode=TIDY_MODE_IN_PLACE).positions == {}


def test_in_place_clean_up_gap_is_clamped_to_three_times_the_default() -> None:
    items = [_item("a", 0, 0), _item("b", 0, 1000)]

    rects = _rects(_layout(items, [], mode=TIDY_MODE_IN_PLACE), items)

    assert rects["b"][1] - (rects["a"][1] + PROCESS[1]) == 3.0 * ROW_GAP


# --- polish -------------------------------------------------------------------------------------


def test_polish_straightens_offset_data_ports_in_one_row() -> None:
    items = [_item("a", 0, 0, (200.0, 120.0)), _item("b", 400, 50, (200.0, 120.0))]
    wires = [TidyWire("ab", "a", "b", "right", "left", (200.0, 30.0), (0.0, 60.0))]

    rects = _rects(_layout(items, wires), items)

    assert rects["a"][1] + 30.0 == pytest.approx(rects["b"][1] + 60.0)
    # The solver splits the 30 px between both nodes; the level then keeps its anchored top edge (y = 0).
    assert rects["a"][1] == pytest.approx(30.0)
    assert rects["b"][1] == pytest.approx(0.0)


def test_polish_is_discarded_when_it_would_create_an_overlap() -> None:
    items = [
        _item("a", 0, 0, (200.0, 120.0)),
        _item("b", 400, 0, (200.0, 120.0)),
        _item("d", 0, 200, PROCESS),
    ]
    wires = [
        TidyWire("ab", "a", "b", "right", "left", (200.0, 5.0), (0.0, 115.0)),
        TidyWire("ad", "a", "d", "bottom", "top", (100.0, 120.0), (112.0, 0.0)),
    ]

    rects = _rects(_layout(items, wires, row_gap=16.0), items)

    assert rects["a"][1] == rects["b"][1] == 0.0
    assert rects["d"][1] == 120.0 + 16.0
    assert rects["a"][1] + 5.0 != rects["b"][1] + 115.0


# --- determinism and performance ----------------------------------------------------------------


def test_a_second_tidy_of_a_polished_layout_changes_nothing() -> None:
    # Polish moves the topmost item; without re-anchoring the level, each rerun would drift by the polish offsets.
    items = [_item("a", 0, 0, (200.0, 120.0)), _item("b", 400, 50, (200.0, 120.0))]
    wires = [TidyWire("ab", "a", "b", "right", "left", (200.0, 30.0), (0.0, 60.0))]
    first = _layout(items, wires)
    tidied = [
        _item(item.item_id, *first.positions.get(item.item_id, (item.x, item.y)), (item.width, item.height))
        for item in items
    ]

    assert _layout(tidied, wires).positions == {}

    group_items, group_wires = _chain_group_input()
    grouped = _layout(group_items, group_wires)
    regrouped_items = [
        TidyItem(
            item_id=item.item_id,
            x=grouped.positions.get(item.item_id, (item.x, item.y))[0],
            y=grouped.positions.get(item.item_id, (item.x, item.y))[1],
            width=grouped.group_sizes.get(item.item_id, (item.width, item.height))[0],
            height=grouped.group_sizes.get(item.item_id, (item.width, item.height))[1],
            parent_group_id=item.parent_group_id,
            is_group=item.is_group,
            rigid=item.rigid,
            arrangeable=item.arrangeable,
        )
        for item in group_items
    ]
    regrouped = _layout(regrouped_items, group_wires)
    assert all(abs(dx) < 1e-6 and abs(dy) < 1e-6 for dx, dy in (
        (x - item.x, y - item.y)
        for item in regrouped_items
        for x, y in [regrouped.positions.get(item.item_id, (item.x, item.y))]
    ))
    assert all(
        abs(width - item.width) < 1e-6 and abs(height - item.height) < 1e-6
        for item in regrouped_items
        for width, height in [regrouped.group_sizes.get(item.item_id, (item.width, item.height))]
    )


def test_layout_is_independent_of_input_order() -> None:
    for items, wires in (_flowchart_with_optional_loop(with_loop=True), _chain_group_input()):
        expected = _layout(items, wires)
        generator = random.Random(7)
        for _attempt in range(5):
            shuffled_items = list(items)
            shuffled_wires = list(wires)
            generator.shuffle(shuffled_items)
            generator.shuffle(shuffled_wires)
            assert _layout(shuffled_items, shuffled_wires) == expected
            assert _layout(shuffled_items, shuffled_wires, mode=TIDY_MODE_IN_PLACE) == _layout(
                items, wires, mode=TIDY_MODE_IN_PLACE
            )


def _random_graph(item_count: int, wire_count: int, seed: int) -> tuple[list[TidyItem], list[TidyWire]]:
    generator = random.Random(seed)
    items = [
        _item(f"n{index:03d}", generator.uniform(0, 4000), generator.uniform(0, 3000), PROCESS)
        for index in range(item_count)
    ]
    sides = [("right", "left"), ("bottom", "top"), ("bottom", "left"), ("left", "bottom")]
    wires = []
    for index in range(wire_count):
        source, target = generator.sample(range(item_count), 2)
        source_side, target_side = sides[index % len(sides)]
        wires.append(_wire(items, f"w{index:03d}", items[source].item_id, items[target].item_id, source_side, target_side))
    return items, wires


def test_large_graph_lays_out_quickly_without_overlaps() -> None:
    items, wires = _random_graph(300, 400, seed=11)

    started = time.perf_counter()
    result = _layout(items, wires)
    elapsed = time.perf_counter() - started

    assert elapsed < 0.5
    assert result.laid_out_level_count == 1
    rects = list(_rects(result, items).values())
    for index, first in enumerate(rects):
        for second in rects[index + 1 :]:
            assert not (
                first[0] < second[0] + second[2]
                and first[0] + first[2] > second[0]
                and first[1] < second[1] + second[3]
                and first[1] + first[3] > second[1]
            )


# --- collision avoidance with several blockers --------------------------------------------------


def test_collision_avoidance_clears_every_fixed_box_even_when_squeezed_between_two() -> None:
    row = LayoutNodeBounds("row", 320.0, 0.0, 224.0, 84.0)
    grown_group = LayoutNodeBounds("group", -32.0, 204.0, 608.0, 386.0)
    note = LayoutNodeBounds("note", 300.0, 120.0, 228.0, 152.0)

    updates = build_collision_avoidance_position_updates(
        fixed_bounds=[grown_group, row], movable_bounds=[note], gap=32.0
    )

    moved = note.translated(updates["note"][0] - note.x, updates["note"][1] - note.y)
    for blocker in (row, grown_group):
        inflated = blocker.inflated(32.0)
        assert not (
            moved.left < inflated.right
            and moved.right > inflated.left
            and moved.top < inflated.bottom
            and moved.bottom > inflated.top
        ), blocker.node_id


def test_collision_avoidance_moves_crowding_boxes_off_a_single_fixed_box() -> None:
    fixed = LayoutNodeBounds("fixed", 0.0, 0.0, 300.0, 200.0)
    movable = [LayoutNodeBounds("a", 250.0, 50.0, 100.0, 60.0), LayoutNodeBounds("b", -60.0, 150.0, 100.0, 60.0)]

    updates = build_collision_avoidance_position_updates(
        fixed_bounds=[fixed], movable_bounds=movable, gap=16.0, reach_radius=400.0
    )

    assert set(updates) == {"a", "b"}
    inflated = fixed.inflated(16.0)
    for box in movable:
        moved = box.translated(updates[box.node_id][0] - box.x, updates[box.node_id][1] - box.y)
        assert not (
            moved.left < inflated.right
            and moved.right > inflated.left
            and moved.top < inflated.bottom
            and moved.bottom > inflated.top
        ), box.node_id
    assert build_collision_avoidance_position_updates(fixed_bounds=[], movable_bounds=movable, gap=16.0) == {}


# --- port alignment solver ----------------------------------------------------------------------


def test_port_alignment_offsets_split_the_move_and_skip_unknown_or_conflicting_nodes() -> None:
    aligned = build_port_alignment_offsets(
        node_ids={"a", "b"},
        constraints=[PortAlignmentConstraint("a", "b", "y", 30.0, 60.0)],
    )
    assert aligned == {"a": (0.0, 15.0), "b": (0.0, -15.0)}

    assert build_port_alignment_offsets(
        node_ids={"a"},
        constraints=[PortAlignmentConstraint("a", "b", "y", 30.0, 60.0)],
    ) == {}

    conflicting = [
        PortAlignmentConstraint("a", "b", "x", 0.0, 10.0),
        PortAlignmentConstraint("b", "c", "x", 0.0, 10.0),
        PortAlignmentConstraint("a", "c", "x", 0.0, 0.0),
    ]
    assert build_port_alignment_offsets(node_ids={"a", "b", "c"}, constraints=conflicting) == {}
