"""Smart-guide snapshot: the pure exclusion rules, the viewport-index reads, and the canvas-state slot.

Purpose: Prove the smart-guide snapshot's moving and candidate rects (drawn measure, viewport-index filtered,
Group ancestors and descendants excluded through owner chains, hidden members owned through the moving or
collapsed Groups' member lists), the candidate cap (row and column band first, then straight-line distance,
ties and output in input order, ranked around the moving rects moved by the offset option, also through the
slot), the trimmed flag and the per-axis drop gaps to the nearest left-out candidate, and that the slot
refreshes a stale index instead of scanning, counting it in refresh_count only, not in the visible-model
query diagnostics.
Map: docs/agent_maps/feature_routes/graph_canvas_input_layers.md
Tests: tests/test_graph_canvas_smart_guide_snapshot.py
"""
from __future__ import annotations

import unittest
from unittest import mock

from ea_node_editor.ui_qml import graph_canvas_viewport_index as viewport_index_module
from ea_node_editor.ui_qml.graph_canvas_state import GraphCanvasStateBridge
from ea_node_editor.ui_qml.graph_canvas_state.smart_guide_snapshot import (
    SMART_GUIDE_CANDIDATE_LIMIT,
    build_smart_guide_snapshot,
    smart_guide_offset,
    smart_guide_query_rect,
)
from ea_node_editor.ui_qml.graph_canvas_viewport_index import GraphCanvasViewportIndex, scene_rect_payload
from ea_node_editor.ui_qml.graph_scene_mutation.group_scope import scene_layout_bounds
from ea_node_editor.ui_qml.graph_surface_metrics import resolved_node_surface_size
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
from tests.automation.harness import build_context, ensure_app

GROUP = "passive.annotation.group_backdrop"
PLOT = "plot.signal"
LOGGER = "core.logger"
VIEWPORT = {"x": -600.0, "y": -400.0, "width": 1200.0, "height": 800.0}


def _payload(node_id: str, x: float, y: float, width: float = 100.0, height: float = 50.0, *, owner: str = "", **extra) -> dict:
    """A node payload: every scene payload names the Group that directly holds it (owner_backdrop_id)."""
    return {"node_id": node_id, "x": x, "y": y, "width": width, "height": height, "owner_backdrop_id": owner, **extra}


def _group(
    node_id: str, x: float, y: float, width: float, height: float, *, owner: str = "", nodes=(), groups=(), collapsed=False
) -> dict:
    return _payload(
        node_id,
        x,
        y,
        width,
        height,
        owner=owner,
        member_node_ids=list(nodes),
        member_backdrop_ids=list(groups),
        collapsed=collapsed,
    )


def _rect(node_id: str, x: float, y: float, width: float = 100.0, height: float = 50.0) -> dict:
    return {"node_id": node_id, "x": x, "y": y, "width": width, "height": height}


class _Unreadable:
    """Group backdrops the builder must not read."""

    def __iter__(self):
        raise AssertionError("the Group member lists were read")


class SmartGuideSnapshotBuilderTests(unittest.TestCase):
    # outer holds inner and "sibling"; inner holds "moving" and "neighbour"; "far" and "other" are free.
    NODES = [
        _payload("moving", 20, 20, owner="inner"),
        _payload("neighbour", 200, 20, owner="inner"),
        _payload("sibling", 600, 20, owner="outer"),
        _payload("far", 2000, 0),
    ]
    GROUPS = [
        _group("outer", 0, 0, 1000, 600, nodes=["sibling"], groups=["inner"]),
        _group("inner", 10, 10, 500, 300, owner="outer", nodes=["moving", "neighbour"]),
        _group("other", 1500, 0, 300, 200),
    ]

    def build(self, node_ids, nodes=None, groups=None, candidates=None, backdrops=None) -> dict:
        nodes = self.NODES if nodes is None else nodes
        groups = self.GROUPS if groups is None else groups
        by_id = {payload["node_id"]: payload for payload in [*nodes, *groups]}
        return build_smart_guide_snapshot(
            node_ids,
            payload_for=by_id.get,
            candidate_payloads=[*nodes, *groups] if candidates is None else candidates,
            backdrop_payloads=groups if backdrops is None else backdrops,
        )

    @staticmethod
    def candidate_ids(snapshot: dict) -> list[str]:
        return [rect["node_id"] for rect in snapshot["candidates"]]

    def test_a_moving_node_drops_itself_and_every_group_that_holds_it(self) -> None:
        snapshot = self.build(["moving"])

        self.assertEqual(snapshot["moving"], [_rect("moving", 20, 20)])
        self.assertEqual(self.candidate_ids(snapshot), ["neighbour", "sibling", "far", "other"])

    def test_a_moving_group_drops_everything_it_holds(self) -> None:
        self.assertEqual(self.candidate_ids(self.build(["outer"])), ["far", "other"])

    def test_a_moving_nested_group_drops_its_contents_and_its_holders(self) -> None:
        snapshot = self.build(["inner"])

        self.assertEqual(snapshot["moving"], [_rect("inner", 10, 10, 500, 300)])
        self.assertEqual(self.candidate_ids(snapshot), ["sibling", "far", "other"])

    def test_owner_chains_leave_the_group_member_lists_unread(self) -> None:
        # Every moving node has a payload, so owners come from owner_backdrop_id chains alone.
        for node_ids, expected in (
            (["moving"], ["neighbour", "sibling", "far", "other"]),
            (["inner"], ["sibling", "far", "other"]),
            (["outer", "far"], ["other"]),
        ):
            self.assertEqual(self.candidate_ids(self.build(node_ids, backdrops=_Unreadable())), expected)

    def test_a_hidden_member_of_a_collapsed_group_has_no_moving_rect(self) -> None:
        # A collapsed Group lists its members, but hidden members have no payload.
        nodes = [_payload("visible", 400, 0, owner="collapsed"), _payload("free", 900, 0)]
        groups = [_group("collapsed", 0, 0, 130, 36, nodes=["hidden", "visible"], collapsed=True)]

        snapshot = self.build(["hidden", "free"], nodes=nodes, groups=groups)

        self.assertEqual(snapshot["moving"], [_rect("free", 900, 0)])
        self.assertEqual(self.candidate_ids(snapshot), ["visible"])

    def test_a_hidden_member_drops_every_group_above_its_collapsed_group(self) -> None:
        # The member lists name the hidden node's collapsed Group; that Group's payload names the next one.
        nodes = [
            _payload("visible", 400, 0, owner="collapsed"),
            _payload("sibling", 700, 0, owner="outer"),
            _payload("free", 1900, 0),
        ]
        groups = [
            _group("outer", -50, -50, 1000, 400, nodes=["sibling"], groups=["collapsed"]),
            _group("collapsed", 0, 0, 130, 36, owner="outer", nodes=["hidden", "visible"], collapsed=True),
        ]

        snapshot = self.build(["hidden"], nodes=nodes, groups=groups)

        self.assertEqual(snapshot["moving"], [])
        self.assertEqual(self.candidate_ids(snapshot), ["visible", "sibling", "free"])

    def test_a_dragged_collapsed_group_names_its_hidden_members_itself(self) -> None:
        # Dragging a collapsed Group moves its hidden members too. The Group's own member lists name their
        # owner, so the scope's other Groups stay unread.
        nodes = [_payload("sibling", 700, 0, owner="outer"), _payload("free", 1900, 0)]
        groups = [
            _group("outer", -50, -50, 1000, 400, nodes=["sibling"], groups=["collapsed"]),
            _group("collapsed", 0, 0, 130, 36, owner="outer", nodes=["hidden", "also_hidden"], collapsed=True),
        ]

        snapshot = self.build(["collapsed", "hidden", "also_hidden"], nodes=nodes, groups=groups, backdrops=_Unreadable())

        self.assertEqual(snapshot["moving"], [_rect("collapsed", 0, 0, 130, 36)])
        self.assertEqual(self.candidate_ids(snapshot), ["sibling", "free"])

    def test_only_collapsed_groups_can_name_a_hidden_member(self) -> None:
        # Only a collapsed Group hides members, so a stale list in an expanded Group names no owner: the
        # hidden node's Group is the collapsed one, and the expanded Group stays a candidate.
        nodes = [_payload("free", 900, 0)]
        groups = [
            _group("expanded", 300, 300, 400, 200, nodes=["hidden"]),
            _group("collapsed", 0, 0, 130, 36, nodes=["hidden"], collapsed=True),
        ]

        snapshot = self.build(["hidden"], nodes=nodes, groups=groups)

        self.assertEqual(snapshot["moving"], [])
        self.assertEqual(self.candidate_ids(snapshot), ["free", "expanded"])

    def test_candidates_are_deduped_in_stable_order(self) -> None:
        candidates = [_payload("b", 0, 0), _payload("a", 10, 0), _payload("b", 99, 99), {"x": 1, "y": 2}, "junk"]

        snapshot = self.build(["moving", "moving", "missing"], candidates=candidates)

        self.assertEqual(snapshot["moving"], [_rect("moving", 20, 20)])
        self.assertEqual(snapshot["candidates"], [_rect("b", 0, 0), _rect("a", 10, 0)])

    def test_rects_floor_their_size_at_one_like_the_viewport_index(self) -> None:
        snapshot = self.build([], candidates=[_payload("thin", 5, 6, 0.25, -3)])

        self.assertEqual(snapshot["candidates"], [_rect("thin", 5, 6, 1.0, 1.0)])

    def test_owner_cycles_terminate(self) -> None:
        # Hand-edited data can make two Groups hold each other.
        nodes = [_payload("n", 20, 20, owner="g2"), _payload("free", 900, 0)]
        groups = [
            _group("g1", 0, 0, 300, 300, owner="g2", groups=["g2"]),
            _group("g2", 10, 10, 200, 200, owner="g1", groups=["g1"], nodes=["n", "hidden"], collapsed=True),
        ]

        self.assertEqual(self.candidate_ids(self.build(["n"], nodes=nodes, groups=groups)), ["free"])
        self.assertEqual(self.candidate_ids(self.build(["g1"], nodes=nodes, groups=groups)), ["free"])
        self.assertEqual(self.candidate_ids(self.build(["hidden"], nodes=nodes, groups=groups)), ["n", "free"])

    def test_query_rect_needs_finite_values_and_a_positive_size(self) -> None:
        self.assertEqual(smart_guide_query_rect({"x": 1, "y": 2, "width": 3, "height": 4}), (1.0, 2.0, 3.0, 4.0))
        for invalid in (
            {},
            None,
            {"x": 1, "y": 2, "width": 0, "height": 4},
            {"x": float("nan"), "y": 2, "width": 3, "height": 4},
            {"x": 1, "y": 2, "width": float("inf"), "height": 4},
            {"x": 1e308, "y": 2, "width": 1e308, "height": 4},
            {"x": "a", "y": 2, "width": 3, "height": 4},
        ):
            self.assertIsNone(smart_guide_query_rect(invalid), invalid)


class SmartGuideCandidateLimitTests(unittest.TestCase):
    """Past the limit the builder keeps the candidates most relevant to the moving rect (moved by the offset)."""

    MOVING = _payload("moving", 0, 0)  # 100 x 50: rows y 0..50, columns x 0..100

    def build(self, candidates, *, limit, offset=(0.0, 0.0), moving=MOVING) -> dict:
        payloads = [*([moving] if moving else []), *candidates]
        by_id = {payload["node_id"]: payload for payload in payloads}
        return build_smart_guide_snapshot(
            ["moving"],
            payload_for=by_id.get,
            candidate_payloads=payloads,
            backdrop_payloads=[],
            offset=offset,
            candidate_limit=limit,
        )

    def kept(self, candidates, *, limit, offset=(0.0, 0.0), moving=MOVING) -> list[str]:
        return [rect["node_id"] for rect in self.build(candidates, limit=limit, offset=offset, moving=moving)["candidates"]]

    def test_the_limit_is_128_by_default(self) -> None:
        candidates = [_payload(f"n{order}", 200.0 + order * 150.0, 300.0) for order in range(SMART_GUIDE_CANDIDATE_LIMIT + 1)]
        by_id = {payload["node_id"]: payload for payload in [self.MOVING, *candidates]}

        def default_build(payloads):
            return build_smart_guide_snapshot(
                ["moving"], payload_for=by_id.get, candidate_payloads=payloads, backdrop_payloads=[]
            )["candidates"]

        self.assertEqual(SMART_GUIDE_CANDIDATE_LIMIT, 128)
        self.assertEqual(len(default_build(candidates[:-1])), 128)
        # The 129th (the farthest) goes; the rest keep their input order.
        self.assertEqual(
            [rect["node_id"] for rect in default_build(candidates)], [payload["node_id"] for payload in candidates[:-1]]
        )

    def test_up_to_the_limit_every_candidate_stays_in_input_order(self) -> None:
        candidates = [_payload("far", 5000, 5000), _payload("near", 150, 0), _payload("mid", 900, 900)]

        self.assertEqual(self.kept(candidates, limit=3), ["far", "near", "mid"])
        self.assertEqual(self.kept(candidates, limit=None), ["far", "near", "mid"])

    def test_row_and_column_neighbours_outrank_nearer_diagonal_ones(self) -> None:
        candidates = [
            _payload("diagonal", 150, 100),  # 50 right and 50 below: 70.7 away, in neither band
            _payload("row", 1000, 20),  # overlaps the rows, 900 to the right
            _payload("column", 30, 700),  # overlaps the columns, 650 below
            _payload("corner", 101, 51),  # 1 right and 1 below: nearest of all, still in neither band
        ]

        self.assertEqual(self.kept(candidates, limit=2), ["row", "column"])
        self.assertEqual(self.kept(candidates, limit=3), ["row", "column", "corner"])

    def test_band_neighbours_rank_by_their_gap_along_the_other_axis(self) -> None:
        candidates = [
            _payload("row_far", 700, 0),  # gap 600 along x
            _payload("column_near", 0, 150),  # gap 100 along y
            _payload("row_left", -400, 10),  # gap 300 along x
            _payload("row_near", 150, 40),  # gap 50 along x
            _payload("column_far", 50, -900),  # gap 850 along y
        ]

        self.assertEqual(self.kept(candidates, limit=3), ["column_near", "row_left", "row_near"])

    def test_the_others_rank_by_rect_to_rect_distance(self) -> None:
        candidates = [
            _payload("far", 500, 500),  # 400 x 450: 602
            _payload("near", 200, 80),  # 100 x 30: 104
            _payload("mid", -300, -250),  # 200 x 200: 283
        ]

        self.assertEqual(self.kept(candidates, limit=2), ["near", "mid"])
        # The straight-line distance, not the sum of the two gaps: 100 x 100 is 141 away (200 summed) and
        # 150 x 10 is 150 away (160 summed).
        diagonal = [_payload("sideways", 250, 60), _payload("diagonal", 200, 150)]
        self.assertEqual(self.kept(diagonal, limit=1), ["diagonal"])

    def test_touching_is_not_sharing_a_band(self) -> None:
        # "touching" meets the moving rect's bottom edge (no overlap); "band" overlaps the rows, 20 farther.
        candidates = [_payload("touching", 300, 50), _payload("band", 320, 49)]

        self.assertEqual(self.kept(candidates, limit=1), ["band"])

    def test_ties_keep_the_earlier_candidate(self) -> None:
        # Four row neighbours 100 away and four diagonal ones at the same distance: input order decides.
        row = [_payload("row_a", 200, 0), _payload("row_b", -200, 0), _payload("row_c", 200, 25), _payload("row_d", -200, 25)]
        diagonal = [_payload("diag_a", 180, 110), _payload("diag_b", -180, -110)]

        self.assertEqual(self.kept([*row, *diagonal], limit=3), ["row_a", "row_b", "row_c"])
        self.assertEqual(self.kept([*reversed(row), *diagonal], limit=3), ["row_d", "row_c", "row_b"])
        self.assertEqual(self.kept([*row, *diagonal], limit=5), ["row_a", "row_b", "row_c", "row_d", "diag_a"])
        self.assertEqual(self.kept([*row, *reversed(diagonal)], limit=5), ["row_a", "row_b", "row_c", "row_d", "diag_b"])

    def test_the_ranking_follows_the_offset_and_the_moving_rect_stays_put(self) -> None:
        candidates = [
            _payload("start_row", 400, 0),
            _payload("start_column", 0, 400),
            _payload("end_row", 3400, 2000),
            _payload("end_column", 3000, 2600),
        ]

        at_start = self.build(candidates, limit=2)
        at_end = self.build(candidates, limit=2, offset=(3000.0, 2000.0))

        self.assertEqual([rect["node_id"] for rect in at_start["candidates"]], ["start_row", "start_column"])
        self.assertEqual([rect["node_id"] for rect in at_end["candidates"]], ["end_row", "end_column"])
        self.assertEqual(at_end["moving"], [_rect("moving", 0, 0)])
        # Each axis moves by its own offset: 3000 along one axis alone puts the rect beside "row" (x) or
        # "column" (y); the same offset on both axes would put it 50 from "far" instead.
        axis_candidates = [_payload("row", 3400, 10), _payload("column", 20, 3400), _payload("far", 3020, 2900)]
        self.assertEqual(self.kept(axis_candidates, limit=1, offset=(3000.0, 0.0)), ["row"])
        self.assertEqual(self.kept(axis_candidates, limit=1, offset=(0.0, 3000.0)), ["column"])
        self.assertEqual(self.kept(axis_candidates, limit=1, offset=(3000.0, 3000.0)), ["far"])

    def test_the_union_of_every_moving_rect_is_ranked_around(self) -> None:
        # Two moving rects, a (0, 0) and b (1000, 500): their union spans x 0..1100 and y 0..550.
        nodes = [_payload("a", 0, 0), _payload("b", 1000, 500)]
        candidates = [
            _payload("a_diagonal", -150, -100),  # 70.7 from a, in neither band of the union
            _payload("b_row", 1500, 510),  # in the union's rows (b's alone), 400 right of it
            _payload("a_column", 20, 900),  # in the union's columns (a's alone), 350 below it
        ]
        by_id = {payload["node_id"]: payload for payload in [*nodes, *candidates]}

        def kept(limit: int) -> list[str]:
            snapshot = build_smart_guide_snapshot(
                ["a", "b"], payload_for=by_id.get, candidate_payloads=candidates, backdrop_payloads=[], candidate_limit=limit
            )
            return [rect["node_id"] for rect in snapshot["candidates"]]

        # Ranked around b alone, b_row would come first; around a alone, a_diagonal would beat b_row.
        self.assertEqual(kept(1), ["a_column"])
        self.assertEqual(kept(2), ["b_row", "a_column"])

    def test_without_a_moving_rect_the_first_candidates_stay(self) -> None:
        candidates = [_payload("far", 5000, 5000), _payload("near", 150, 0), _payload("mid", 900, 900)]

        self.assertEqual(self.kept(candidates, limit=2, moving=None), ["far", "near"])

    def test_excluded_candidates_take_no_place_under_the_limit(self) -> None:
        # The moving node's own Group is left out before the limit applies, so both free nodes stay.
        group = _group("group", -50, -50, 400, 300, nodes=["moving"])
        moving = _payload("moving", 0, 0, owner="group")
        candidates = [group, _payload("free_a", 5000, 0), _payload("free_b", 0, 5000)]

        self.assertEqual(self.kept(candidates, limit=2, moving=moving), ["free_a", "free_b"])

    def test_an_untrimmed_snapshot_says_so_and_names_no_drop_gaps(self) -> None:
        candidates = [_payload("near", 150, 0), _payload("far", 900, 900)]

        # Holding exactly as many candidates as the limit leaves none out.
        for limit in (None, 3, 2):
            snapshot = self.build(candidates, limit=limit)
            self.assertEqual(len(snapshot["candidates"]), 2, limit)
            self.assertIs(snapshot["trimmed"], False, limit)
            self.assertNotIn("dropGapX", snapshot)
            self.assertNotIn("dropGapY", snapshot)

    def test_a_trimmed_snapshot_names_the_smallest_gap_to_a_left_out_candidate_along_each_axis(self) -> None:
        # Ranked at the offset (1000, 0) the moving rect spans x 1000..1100 and y 0..50.
        candidates = [
            _payload("row", 1500, 10),  # kept: in the row band, 400 away along x
            _payload("column", 1020, 700),  # kept: in the column band, 650 away along y
            _payload("diagonal", 1300, 300),  # left out: 200 along x, 250 along y
            _payload("low_left", -400, 90),  # left out: 1300 along x, 40 along y
            _payload("high_up", 1150, -900),  # left out: 50 along x, 850 along y
        ]

        snapshot = self.build(candidates, limit=2, offset=(1000.0, 0.0))

        self.assertEqual([rect["node_id"] for rect in snapshot["candidates"]], ["row", "column"])
        self.assertIs(snapshot["trimmed"], True)
        # Each axis takes its own nearest left-out candidate; the kept ones (both 0 along one axis) do not count.
        self.assertEqual((snapshot["dropGapX"], snapshot["dropGapY"]), (50.0, 40.0))
        # The gaps are measured from the union at the offset: at the stored rect (x 0..100) "low_left" is
        # the nearest and stays, and "column" (920 x 650) and "diagonal" (1200 x 250) set the gaps.
        at_start = self.build(candidates, limit=2)
        self.assertEqual([rect["node_id"] for rect in at_start["candidates"]], ["row", "low_left"])
        self.assertEqual((at_start["dropGapX"], at_start["dropGapY"]), (920.0, 250.0))
        # A left-out candidate that overlaps the union along an axis is 0 away along it.
        only_row = self.build(candidates, limit=1, offset=(1000.0, 0.0))
        self.assertEqual([rect["node_id"] for rect in only_row["candidates"]], ["row"])
        self.assertEqual((only_row["dropGapX"], only_row["dropGapY"]), (0.0, 40.0))

    def test_the_drop_gaps_cover_a_short_group_left_out_between_two_tall_ones(self) -> None:
        # Tall A and B start 10 below the moving rect's rows and short H lies between them far below: ranked
        # at the start, the limit keeps A and B and leaves H out. Equal spacing along x reads the rects that
        # overlap the moving rect along y, so once the drag reaches H's rows it would measure the A-B gap
        # straight through H. The drop gaps say how soon H can join: 940 along y, the gap from the moving
        # rect's bottom (50) to H's top (990), and 250 along x.
        moving = _payload("moving", 0, 0)
        candidates = [
            _payload("A", 200, 60, 100, 2440),
            _payload("H", 350, 990, 50, 80),
            _payload("B", 450, 60, 100, 2440),
        ]

        snapshot = self.build(candidates, limit=2, moving=moving)

        self.assertEqual([rect["node_id"] for rect in snapshot["candidates"]], ["A", "B"])
        self.assertIs(snapshot["trimmed"], True)
        self.assertEqual((snapshot["dropGapX"], snapshot["dropGapY"]), (250.0, 940.0))
        # Ranked where the drag reaches H's rows, H shares the moving rect's row band and stays.
        there = self.build(candidates, limit=2, moving=moving, offset=(700.0, 1000.0))
        self.assertIn("H", [rect["node_id"] for rect in there["candidates"]])

    def test_offset_options_read_finite_numbers_only(self) -> None:
        self.assertEqual(smart_guide_offset({"offset_x": 12.5, "offset_y": "-3"}), (12.5, -3.0))
        for invalid in ({}, None, "junk", {"offset_x": float("nan"), "offset_y": float("inf")}, {"offset_x": "a", "offset_y": None}):
            self.assertEqual(smart_guide_offset(invalid), (0.0, 0.0), invalid)
        self.assertEqual(smart_guide_offset({"offset_y": 7}), (0.0, 7.0))


class ViewportIndexReadHelperTests(unittest.TestCase):
    @staticmethod
    def index_with(payloads: list[dict]) -> GraphCanvasViewportIndex:
        index = GraphCanvasViewportIndex()
        index.query(
            workspace_id="workspace",
            model_revision=1,
            source_loader=lambda: payloads,
            visible_rect=(0.0, 0.0, 10.0, 10.0),
            active_node_ids=set(),
        )
        return index

    def test_read_helpers_query_the_grid_without_touching_diagnostics(self) -> None:
        payloads = [_payload("a", 0, 0), _payload("b", 600, 0), _payload("c", 5000, 5000), _payload("d", 100, 40)]
        index = self.index_with(payloads)
        before = index.diagnostics.as_payload()

        hits = index.payloads_intersecting((50.0, 20.0, 600.0, 100.0))

        self.assertEqual([payload["node_id"] for payload in hits], ["a", "b", "d"])
        self.assertEqual(index.diagnostics.as_payload(), before)
        self.assertIs(index.payload_for(" c "), payloads[2])
        self.assertIsNone(index.payload_for("missing"))
        self.assertEqual(index.payloads(), payloads)
        self.assertEqual(index.payloads_intersecting(None), [])
        self.assertTrue(index.is_current(workspace_id="workspace", model_revision=1))
        self.assertFalse(index.is_current(workspace_id="workspace", model_revision=2))
        self.assertFalse(index.is_current(workspace_id="other", model_revision=1))

    def test_refresh_rebuilds_a_stale_index_without_a_query(self) -> None:
        payloads = [_payload("a", 0, 0), _payload("b", 600, 0)]
        index = self.index_with(payloads)
        before = index.diagnostics.as_payload()
        moved = [_payload("a", 0, 0), _payload("b", 5000, 0)]

        self.assertFalse(index.refresh(workspace_id="workspace", model_revision=1, source_loader=lambda: moved))
        self.assertIs(index.payload_for("b"), payloads[1])
        self.assertEqual(index.diagnostics.as_payload(), before)
        self.assertTrue(index.refresh(workspace_id="workspace", model_revision=2, source_loader=lambda: moved))

        self.assertIs(index.payload_for("b"), moved[1])
        self.assertEqual([payload["node_id"] for payload in index.payloads_intersecting((0.0, 0.0, 1000.0, 100.0))], ["a"])
        self.assertTrue(index.is_current(workspace_id="workspace", model_revision=2))
        # Only refresh_count counts the rebuild; the query diagnostics describe viewport queries alone.
        self.assertEqual(before["refresh_count"], 0)
        self.assertEqual(index.diagnostics.as_payload(), {**before, "refresh_count": 1})

    def test_a_small_rect_reads_only_the_cells_it_covers(self) -> None:
        payloads = [_payload(f"n{order}", (order % 50) * 600.0, (order // 50) * 600.0) for order in range(2500)]
        index = self.index_with(payloads)

        with mock.patch.object(
            viewport_index_module, "rects_intersect", wraps=viewport_index_module.rects_intersect
        ) as rects_intersect:
            hits = index.payloads_intersecting((0.0, 0.0, 1000.0, 1000.0))

        self.assertEqual([payload["node_id"] for payload in hits], ["n0", "n1", "n50", "n51"])
        self.assertEqual(rects_intersect.call_count, 4)

    def test_a_rect_wider_than_the_grid_walks_the_occupied_cells(self) -> None:
        payloads = [_payload(f"n{order}", order * 700.0, (order % 3) * 900.0) for order in range(20)]
        index = self.index_with(payloads)

        self.assertEqual(index.payloads_intersecting((-1e9, -1e9, 2e9, 2e9)), payloads)
        self.assertEqual(
            index.payloads_intersecting((-1e9, -1e9, 1e9 + 5000.0, 2e9)),
            [payload for payload in payloads if payload["x"] < 5000.0],
        )
        self.assertEqual(index.payloads_intersecting((0.0, 0.0, float("inf"), 10.0)), [])


class SmartGuideSnapshotSlotTests(unittest.TestCase):
    """The GraphCanvasStateBridge slot over a real GraphSceneBridge and ViewportBridge."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = ensure_app()  # held: build_context drops the QApplication it creates outside pytest

    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene
        self.view = ViewportBridge()
        self.view.set_viewport_size(VIEWPORT["width"], VIEWPORT["height"])
        self.view.set_view_state(1.0, 0.0, 0.0)
        self.bridge = GraphCanvasStateBridge(scene_bridge=self.scene, view_bridge=self.view)
        self.assertEqual(self.bridge.visible_scene_rect_payload, VIEWPORT)

    def add(self, type_id: str, x: float, y: float) -> str:
        return self.scene.add_node_from_type(type_id, float(x), float(y))

    def group(self, x: float, y: float, width: float, height: float) -> str:
        group_id = self.add(GROUP, x, y)
        self.scene.set_node_geometry(group_id, float(x), float(y), float(width), float(height))
        return group_id

    def snapshot(self, node_ids: list[str], rect: object = None, options: dict | None = None) -> dict:
        return self.bridge.smart_guide_snapshot(list(node_ids), VIEWPORT if rect is None else rect, options or {})

    @staticmethod
    def candidate_ids(snapshot: dict) -> set[str]:
        return {rect["node_id"] for rect in snapshot["candidates"]}

    def drawn(self, node_id: str) -> dict:
        workspace = self.context.active_workspace()
        bounds = scene_layout_bounds(self.scene._authoring_boundary, workspace, [workspace.nodes[node_id]])[node_id]  # noqa: SLF001
        return _rect(node_id, bounds.x, bounds.y, bounds.width, bounds.height)

    def test_candidates_come_from_the_query_rect_and_far_nodes_stay_out(self) -> None:
        plot = self.add(PLOT, 0, 0)
        logger = self.add(LOGGER, 400, 0)
        far = self.add(LOGGER, 9000, 9000)

        in_view = self.snapshot([plot])
        covering = self.snapshot([plot], {"x": -1000.0, "y": -1000.0, "width": 11000.0, "height": 11000.0})

        self.assertEqual(self.candidate_ids(in_view), {logger})
        self.assertEqual(self.candidate_ids(covering), {logger, far})
        self.assertEqual(in_view["moving"], [self.drawn(plot)])
        self.assertIs(in_view["trimmed"], False)
        self.assertNotIn("dropGapX", in_view)

    def test_rects_are_the_drawn_measure_not_the_plain_surface_measure(self) -> None:
        plot = self.add(PLOT, 40, 60)
        logger = self.add(LOGGER, 400, 0)
        workspace = self.context.active_workspace()
        spec = self.context.registry.get_spec(PLOT)
        surface_height = resolved_node_surface_size(workspace.nodes[plot], spec, workspace.nodes)[1]

        moving = self.snapshot([plot])["moving"]
        as_candidate = [rect for rect in self.snapshot([logger])["candidates"] if rect["node_id"] == plot]

        # The plot's settings band is part of its drawn height; the plain surface measure leaves it out.
        self.assertEqual(moving, [self.drawn(plot)])
        self.assertEqual(as_candidate, [self.drawn(plot)])
        self.assertGreater(moving[0]["height"] - surface_height, 50.0)

    def test_group_ancestors_and_descendants_are_excluded(self) -> None:
        plot = self.add(PLOT, -200, -200)
        held = self.add(LOGGER, 400, 0)
        outside = self.add(LOGGER, -560, 200)
        outer = self.group(-300, -300, 1100, 800)
        inner = self.group(-250, -250, 500, 400)
        backdrops = {payload["node_id"]: payload for payload in self.bridge.visible_backdrop_nodes_payloads}
        self.assertEqual((backdrops[inner]["member_node_ids"], backdrops[outer]["member_backdrop_ids"]), ([plot], [inner]))
        self.assertEqual(backdrops[outer]["member_node_ids"], [held])

        self.assertEqual(self.candidate_ids(self.snapshot([plot])), {held, outside})
        self.assertEqual(self.candidate_ids(self.snapshot([inner])), {held, outside})
        self.assertEqual(self.candidate_ids(self.snapshot([outer])), {outside})
        self.assertEqual(self.snapshot([inner])["moving"], [self.drawn(inner)])

    def test_a_hidden_member_of_a_collapsed_group_is_skipped(self) -> None:
        plot = self.add(PLOT, -200, -200)
        outside = self.add(LOGGER, 300, 0)
        group = self.group(-250, -250, 400, 300)
        self.assertTrue(self.scene.set_node_collapsed(group, True))

        snapshot = self.snapshot([plot, outside])

        self.assertEqual(snapshot["moving"], [self.drawn(outside)])
        self.assertEqual(self.candidate_ids(snapshot), set())

    def test_an_invalid_rect_falls_back_to_the_exact_visible_query_rect(self) -> None:
        plot = self.add(PLOT, 0, 0)
        just_outside = self.add(LOGGER, 800, 0)
        self.add(LOGGER, 9000, 9000)
        exact = scene_rect_payload(self.bridge._exact_visible_scene_query_rect())  # noqa: SLF001

        self.assertEqual(self.candidate_ids(self.snapshot([plot])), set())
        for invalid in ({}, {"x": float("nan"), "y": 0.0, "width": 10.0, "height": 10.0}, {"x": 0, "y": 0, "width": 0, "height": 5}):
            self.assertEqual(self.snapshot([plot], invalid), self.snapshot([plot], exact))
            self.assertEqual(self.candidate_ids(self.snapshot([plot], invalid)), {just_outside})

    def test_a_moving_node_outside_the_query_rect_keeps_its_rect(self) -> None:
        far = self.add(LOGGER, 9000, 9000)
        near = self.add(LOGGER, 0, 0)

        snapshot = self.snapshot([far])

        self.assertEqual(snapshot["moving"], [self.drawn(far)])
        self.assertEqual(self.candidate_ids(snapshot), {near})

    def test_past_the_limit_the_slot_keeps_the_candidates_nearest_the_moving_rect_at_the_offset(self) -> None:
        limit = SMART_GUIDE_CANDIDATE_LIMIT
        plot = self.add(PLOT, -560, -380)
        # More loggers than the limit, packed near the plot, and one in the far corner of the viewport.
        packed = [self.add(LOGGER, -560 + 20 * (order % 20), -200 + 20 * (order // 20)) for order in range(limit + 3)]
        far = self.add(LOGGER, 450, 300)

        at_start = self.snapshot([plot])
        near_far = self.snapshot([plot], options={"offset_x": 1000.0, "offset_y": 680.0})

        self.assertEqual((len(at_start["candidates"]), len(near_far["candidates"])), (limit, limit))
        # At the plot's own place the far logger ranks last and goes; moved beside it, it ranks first.
        self.assertNotIn(far, self.candidate_ids(at_start))
        self.assertIn(far, self.candidate_ids(near_far))
        self.assertEqual(len(self.candidate_ids(near_far) & set(packed)), limit - 1)
        # Both say they were trimmed and how far the nearest left-out candidate lies along each axis, from
        # the moving union moved by the offset.
        union = self.drawn(plot)
        for snapshot, (offset_x, offset_y) in ((at_start, (0.0, 0.0)), (near_far, (1000.0, 680.0))):
            kept = self.candidate_ids(snapshot)
            dropped = [self.drawn(node_id) for node_id in [*packed, far] if node_id not in kept]
            left, top = union["x"] + offset_x, union["y"] + offset_y
            right, bottom = left + union["width"], top + union["height"]
            self.assertIs(snapshot["trimmed"], True)
            self.assertEqual(
                (snapshot["dropGapX"], snapshot["dropGapY"]),
                (
                    min(max(0.0, rect["x"] - right, left - rect["x"] - rect["width"]) for rect in dropped),
                    min(max(0.0, rect["y"] - bottom, top - rect["y"] - rect["height"]) for rect in dropped),
                ),
            )
        # Only the ranking moves: the moving rect stays where the plot is, and the kept rects keep the order
        # the viewport index hands them over in.
        self.assertEqual(near_far["moving"], [self.drawn(plot)])
        query = tuple(float(VIEWPORT[key]) for key in ("x", "y", "width", "height"))
        index_order = {
            payload["node_id"]: position
            for position, payload in enumerate(self.bridge._visible_node_index.payloads_intersecting(query))  # noqa: SLF001
        }
        for snapshot in (at_start, near_far):
            kept = [rect["node_id"] for rect in snapshot["candidates"]]
            self.assertEqual(kept, sorted(kept, key=index_order.__getitem__))

    def test_a_stale_index_is_rebuilt_and_holds_every_payload_of_the_scope(self) -> None:
        plot = self.add(PLOT, 0, 0)
        logger = self.add(LOGGER, 400, 0)
        far = self.add(LOGGER, 9000, 9000)
        group = self.group(-300, 250, 400, 300)
        self.snapshot([plot])
        node_index = self.bridge._visible_node_index  # noqa: SLF001
        backdrop_index = self.bridge._visible_backdrop_index  # noqa: SLF001

        # A drag commit arrives as a targeted position delta: the visible models update in place and the
        # indexes wait for the next viewport query.
        self.scene.move_node(logger, 420.0, 30.0)
        revision = self.bridge._node_model_revision  # noqa: SLF001
        workspace_id = self.context.active_workspace().workspace_id
        self.assertFalse(node_index.is_current(workspace_id=workspace_id, model_revision=revision))
        self.assertEqual(node_index._records_by_node_id[logger].rect[:2], (400.0, 0.0))  # noqa: SLF001

        diagnostics = self.bridge.visible_scene_model_diagnostics
        with mock.patch.object(GraphCanvasViewportIndex, "_rebuild", autospec=True, side_effect=GraphCanvasViewportIndex._rebuild) as rebuild:  # noqa: SLF001
            candidates = self.snapshot([plot])["candidates"]
            self.assertEqual(rebuild.call_count, 2)  # both indexes share the node-model revision
            self.snapshot([plot])
            self.assertEqual(rebuild.call_count, 2)  # current indexes are only queried

        # The refresh is no viewport query: the visible-model diagnostics do not move, and only each index's
        # refresh_count (summed at the top level) counts it, once.
        after = self.bridge.visible_scene_model_diagnostics
        for index_name in ("nodes", "backdrops"):
            for key in ("query_count", "rebuild_count", "cache_hits", "cache_misses", "visible_count", "full_count"):
                self.assertEqual((index_name, key, after[index_name][key]), (index_name, key, diagnostics[index_name][key]))
            self.assertEqual(after[index_name]["refresh_count"], diagnostics[index_name]["refresh_count"] + 1)
        self.assertEqual(after["refresh_count"], diagnostics["refresh_count"] + 2)
        self.assertIn(self.drawn(logger), candidates)
        self.assertEqual(self.drawn(logger)["x"], 420.0)
        self.assertEqual(set(node_index._records_by_node_id), {plot, logger, far})  # noqa: SLF001
        self.assertEqual(set(backdrop_index._records_by_node_id), {group})  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
