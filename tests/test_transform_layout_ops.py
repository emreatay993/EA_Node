from __future__ import annotations

from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.graph.transform_layout_ops import (
    LayoutNodeBounds,
    PortAlignmentConstraint,
    build_alignment_position_updates,
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
