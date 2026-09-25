from __future__ import annotations

from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.graph.transform_layout_ops import (
    LayoutNodeBounds,
    PortAlignmentConstraint,
    build_alignment_position_updates,
    build_make_room_position_updates,
    build_straighten_connection_position_updates,
)


def _workspace(*node_positions: tuple[str, float, float]) -> WorkspaceData:
    workspace = WorkspaceData(workspace_id="ws", name="Workspace")
    for node_id, x, y in node_positions:
        workspace.nodes[node_id] = NodeInstance(
            node_id=node_id,
            type_id="test.node",
            title=node_id,
            x=x,
            y=y,
        )
    return workspace


def _final_anchor(
    workspace: WorkspaceData,
    updates: dict[str, tuple[float, float]],
    node_id: str,
    axis: str,
    anchor: float,
) -> float:
    node = workspace.nodes[node_id]
    if axis == "x":
        final_x = updates.get(node_id, (node.x, node.y))[0]
        return anchor + (final_x - node.x)
    final_y = updates.get(node_id, (node.x, node.y))[1]
    return anchor + (final_y - node.y)


def test_straighten_horizontal_connection_aligns_port_y() -> None:
    workspace = _workspace(("source", 0.0, 0.0), ("target", 240.0, 80.0))
    updates = build_straighten_connection_position_updates(
        workspace=workspace,
        constraints=[
            PortAlignmentConstraint(
                source_node_id="source",
                target_node_id="target",
                axis="y",
                source_anchor=20.0,
                target_anchor=100.0,
            )
        ],
    )

    assert _final_anchor(workspace, updates, "source", "y", 20.0) == _final_anchor(
        workspace,
        updates,
        "target",
        "y",
        100.0,
    )
    assert updates["source"] == (0.0, 40.0)
    assert updates["target"] == (240.0, 40.0)


def test_straighten_vertical_connection_aligns_port_x() -> None:
    workspace = _workspace(("source", 0.0, 0.0), ("target", 120.0, 240.0))
    updates = build_straighten_connection_position_updates(
        workspace=workspace,
        constraints=[
            PortAlignmentConstraint(
                source_node_id="source",
                target_node_id="target",
                axis="x",
                source_anchor=30.0,
                target_anchor=150.0,
            )
        ],
    )

    assert _final_anchor(workspace, updates, "source", "x", 30.0) == _final_anchor(
        workspace,
        updates,
        "target",
        "x",
        150.0,
    )
    assert updates["source"] == (60.0, 0.0)
    assert updates["target"] == (60.0, 240.0)


def test_straighten_connected_chain_solves_consistently() -> None:
    workspace = _workspace(("a", 0.0, 0.0), ("b", 220.0, 40.0), ("c", 440.0, 90.0))
    updates = build_straighten_connection_position_updates(
        workspace=workspace,
        constraints=[
            PortAlignmentConstraint("a", "b", "y", 10.0, 50.0),
            PortAlignmentConstraint("b", "c", "y", 50.0, 100.0),
        ],
    )

    final_a = _final_anchor(workspace, updates, "a", "y", 10.0)
    final_b = _final_anchor(workspace, updates, "b", "y", 50.0)
    final_c = _final_anchor(workspace, updates, "c", "y", 100.0)
    assert final_a == final_b == final_c


def test_straighten_conflicting_component_is_skipped() -> None:
    workspace = _workspace(("a", 0.0, 0.0), ("b", 200.0, 20.0))
    updates = build_straighten_connection_position_updates(
        workspace=workspace,
        constraints=[
            PortAlignmentConstraint("a", "b", "y", 10.0, 30.0),
            PortAlignmentConstraint("a", "b", "y", 10.0, 80.0),
        ],
    )

    assert updates == {}


def _mixed_size_layout_nodes() -> list[LayoutNodeBounds]:
    return [
        LayoutNodeBounds(node_id="process", x=0.0, y=0.0, width=180.0, height=84.0),
        LayoutNodeBounds(node_id="decision", x=320.0, y=40.0, width=160.0, height=128.0),
        LayoutNodeBounds(node_id="terminal", x=640.0, y=100.0, width=120.0, height=60.0),
    ]


def test_align_center_y_shares_the_selection_vertical_center() -> None:
    nodes = _mixed_size_layout_nodes()
    updates = build_alignment_position_updates(layout_nodes=nodes, alignment="center_y")
    target_center_y = (0.0 + 168.0) * 0.5  # top of process .. bottom of decision
    assert set(updates) == {"process", "decision", "terminal"}
    for node in nodes:
        final_x, final_y = updates[node.node_id]
        assert final_x == node.x
        assert final_y + node.height * 0.5 == target_center_y


def test_align_center_x_shares_the_selection_horizontal_center() -> None:
    nodes = _mixed_size_layout_nodes()
    updates = build_alignment_position_updates(layout_nodes=nodes, alignment=" Center_X ")
    target_center_x = (0.0 + 760.0) * 0.5  # left of process .. right of terminal
    for node in nodes:
        final_x, final_y = updates[node.node_id]
        assert final_y == node.y
        assert final_x + node.width * 0.5 == target_center_x


def test_center_alignment_needs_two_nodes_and_a_known_mode() -> None:
    nodes = _mixed_size_layout_nodes()
    assert build_alignment_position_updates(layout_nodes=nodes[:1], alignment="center_y") == {}
    assert build_alignment_position_updates(layout_nodes=nodes, alignment="middle") == {}


_PILL = LayoutNodeBounds(node_id="grower", x=0.0, y=0.0, width=130.0, height=36.0)
_EXPANDED = LayoutNodeBounds(node_id="grower", x=0.0, y=0.0, width=420.0, height=260.0)


def _box(node_id: str, x: float, y: float, width: float = 100.0, height: float = 50.0) -> LayoutNodeBounds:
    return LayoutNodeBounds(node_id=node_id, x=x, y=y, width=width, height=height)


def _make_room(
    boxes: list[LayoutNodeBounds],
    grown_from: LayoutNodeBounds = _PILL,
    grown_to: LayoutNodeBounds = _EXPANDED,
) -> dict[str, tuple[float, float]]:
    return build_make_room_position_updates(
        grown_from=grown_from,
        grown_to=grown_to,
        movable_bounds=boxes,
        gap=32.0,
        keep_gap_x=96.0,
        keep_gap_y=64.0,
    )


def test_make_room_shifts_the_row_after_the_grower_right_only_as_needed() -> None:
    # The first box sat 100 px after the pill: it keeps the capped 96 px gap, and the whole row moves with it.
    updates = _make_room([_box("first", 230.0, 10.0), _box("second", 520.0, 20.0), _box("far", 900.0, 0.0)])
    assert updates == {"first": (516.0, 10.0), "second": (806.0, 20.0), "far": (1186.0, 0.0)}

    # A row already clear of the expanded rectangle (plus the kept gap) stays.
    assert _make_room([_box("clear", 600.0, 0.0)]) == {}


def test_make_room_keeps_a_smaller_original_gap_and_never_moves_more_than_the_growth() -> None:
    updates = _make_room([_box("tight", 150.0, 0.0)])
    assert updates == {"tight": (440.0, 0.0)}  # 20 px kept after the expanded edge; shift = growth (290)


def test_make_room_moves_the_column_below_down() -> None:
    grown_to = LayoutNodeBounds(node_id="grower", x=0.0, y=0.0, width=130.0, height=260.0)
    updates = _make_room([_box("below", 0.0, 100.0, 130.0, 50.0), _box("beside", 400.0, 100.0)], grown_to=grown_to)
    assert updates == {"below": (0.0, 324.0)}  # 64 px kept under the grown edge


def test_make_room_moves_a_diagonal_box_right_and_leaves_boxes_outside_both_bands() -> None:
    updates = _make_room([_box("diagonal", 300.0, 150.0), _box("outside", 500.0, 400.0)])
    assert set(updates) == {"diagonal"}
    assert updates["diagonal"][1] == 150.0
    assert updates["diagonal"][0] > 300.0


def test_make_room_mirrors_growth_to_the_left_and_up() -> None:
    grown_from = LayoutNodeBounds(node_id="grower", x=500.0, y=500.0, width=130.0, height=36.0)
    grown_to = LayoutNodeBounds(node_id="grower", x=300.0, y=300.0, width=330.0, height=236.0)
    updates = _make_room(
        [_box("left", 300.0, 510.0, 100.0, 30.0), _box("above", 520.0, 300.0, 80.0, 40.0)],
        grown_from=grown_from,
        grown_to=grown_to,
    )
    assert updates == {"left": (104.0, 510.0), "above": (520.0, 196.0)}


def test_make_room_tops_a_tight_gap_up_to_the_kept_gap_once_then_stays() -> None:
    # 20 px after the pill: the first expand keeps those 20 px, the next one tops the gap up to the kept 96 px
    # (a one-time move of 76 px, never more than the growth), and from then on the row does not move.
    first_expand = _make_room([_box("tight", 150.0, 0.0)])
    assert first_expand == {"tight": (440.0, 0.0)}
    second_expand = _make_room([_box("tight", *first_expand["tight"])])
    assert second_expand == {"tight": (516.0, 0.0)}
    assert _make_room([_box("tight", *second_expand["tight"])]) == {}


def test_make_room_does_not_drift_on_a_repeated_expand_after_a_collapse() -> None:
    for gap_before in (96.0, 150.0):
        row = [_box("first", 130.0 + gap_before, 10.0), _box("second", 500.0 + gap_before, 10.0)]
        first_expand = _make_room(row)
        assert first_expand
        moved = [_box(box.node_id, *first_expand[box.node_id]) for box in row]
        assert _make_room(moved) == {}, gap_before

