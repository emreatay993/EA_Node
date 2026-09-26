"""Evaluate the smart-guide engine in a QJSEngine and check its snaps, guide lines and gap markers.

Purpose: Prove GraphCanvasSmartGuideEngine.js alignment, equal-spacing and resize snaps, the guide
lines and gap markers it reports, the equal-spacing band limit, that its skyline search agrees with a
walk at every mark level and a corrupt skyline ends the sweep instead of hanging, and that a resolve call
stays far below a linear scan of the candidates and costs a tall moving rect no more beside many rows
than beside few.
Map: docs/agent_maps/feature_routes/graph_canvas_input_layers.md
Tests: tests/test_graph_canvas_smart_guide_engine.py
Landmarks: _EngineCase; MoveAlignmentTests; MoveSpacingTests; MoveGuideInvariantTests; SpacingBandLimitTests; BandQueryTests; SlotMarkTests; SkylineSearchTests; SweepSafetyTests; ResizeTests; SmartGuidePerformanceTests
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import threading
import time
import unittest

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtQml import QJSEngine


SOURCE = Path(__file__).resolve().parents[1] / "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSmartGuideEngine.js"
THRESHOLD = 8.0


def rect(node_id: str, x: float, y: float, width: float, height: float) -> dict:
    return {"node_id": node_id, "x": x, "y": y, "width": width, "height": height}


def box(left: float, top: float, right: float, bottom: float) -> dict:
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def line(axis: str, value: float, start: float, end: float) -> dict:
    return {"axis": axis, "value": value, "start": start, "end": end}


def gap(axis: str, start: float, end: float, cross_start: float, cross_end: float) -> dict:
    """A gap marker: [cross_start, cross_end] is the cross span its two rects share inside the moving rect's
    band, and `cross` its middle."""
    return {
        "axis": axis,
        "start": start,
        "end": end,
        "cross": (cross_start + cross_end) / 2,
        "crossStart": cross_start,
        "crossEnd": cross_end,
        "size": end - start,
    }


class _EngineCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])
        cls.engine = QJSEngine()
        result = cls.engine.evaluate(SOURCE.read_text(encoding="utf-8").replace(".pragma library", ""), str(SOURCE))
        if result.isError():
            raise AssertionError(result.toString())

    def evaluate(self, expression: str):
        result = self.engine.evaluate(expression)
        self.assertFalse(result.isError(), result.toString())
        return result.toVariant()

    def move(self, candidates: list[dict], base: dict, dx: float = 0.0, dy: float = 0.0, **options) -> dict:
        options.setdefault("threshold", THRESHOLD)
        args = json.dumps([candidates, base, dx, dy, options])
        return self.evaluate(f"(function(a) {{ return resolveMove(buildIndex(a[0]), a[1], a[2], a[3], a[4]); }})({args})")

    def resize(self, candidates: list[dict], resized: dict, **spec) -> dict:
        spec.setdefault("threshold", THRESHOLD)
        spec.setdefault("movingLeft", False)
        spec.setdefault("movingTop", False)
        args = json.dumps([candidates, resized, spec])
        return self.evaluate(f"(function(a) {{ return resolveResize(buildIndex(a[0]), a[1], a[2]); }})({args})")

    def assert_snap(self, result: dict, dx: float, dy: float, snapped_x: bool, snapped_y: bool) -> None:
        self.assertAlmostEqual(result["dx"], dx, places=9)
        self.assertAlmostEqual(result["dy"], dy, places=9)
        self.assertEqual((result["snappedX"], result["snappedY"]), (snapped_x, snapped_y))


class MoveAlignmentTests(_EngineCase):
    def test_left_edge_snaps_to_a_candidate_left_edge(self) -> None:
        result = self.move([rect("a", 0, 0, 100, 50)], box(3, 200, 83, 240))

        self.assert_snap(result, -3, 0, True, False)
        self.assertEqual(result["lines"], [line("x", 0, 0, 240)])
        self.assertEqual(result["gaps"], [])

    def test_right_edge_abuts_a_candidate_left_edge(self) -> None:
        result = self.move([rect("a", 200, 0, 100, 50)], box(40, 30, 196, 90))

        self.assert_snap(result, 4, 0, True, False)
        self.assertEqual(result["lines"], [line("x", 200, 0, 90)])

    def test_centres_snap_together(self) -> None:
        result = self.move([rect("a", 0, 0, 100, 50)], box(18, 200, 78, 240))

        self.assert_snap(result, 2, 0, True, False)
        self.assertEqual(result["lines"], [line("x", 50, 0, 240)])

    def test_no_snap_beyond_the_threshold(self) -> None:
        result = self.move([rect("a", 0, 0, 100, 50)], box(9, 200, 69, 240))

        self.assert_snap(result, 0, 0, False, False)
        self.assertEqual(result["lines"], [])

    def test_threshold_is_inclusive(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50)]

        self.assert_snap(self.move(candidates, box(8, 200, 68, 240)), -8, 0, True, False)
        self.assert_snap(self.move(candidates, box(8.01, 200, 68.01, 240)), 0, 0, False, False)
        # The drag offset counts: the rect lands 8 past the edge.
        self.assert_snap(self.move(candidates, box(0, 200, 60, 240), dx=8), 0, 0, True, False)

    def test_threshold_is_inclusive_above_the_edge_too(self) -> None:
        # Left edge 92 is 8 below the candidate's right edge 100, the nearest value above it.
        candidates = [rect("a", 0, 0, 100, 50)]

        self.assert_snap(self.move(candidates, box(92, 200, 152, 240)), 8, 0, True, False)
        self.assert_snap(self.move(candidates, box(91.99, 200, 151.99, 240)), 0, 0, False, False)

    def test_both_axes_snap_at_once(self) -> None:
        result = self.move([rect("a", 0, 0, 100, 50)], box(3, 55, 63, 95))

        self.assert_snap(result, -3, -5, True, True)
        self.assertEqual(result["lines"], [line("x", 0, 0, 90), line("y", 50, 0, 100)])

    def test_merged_lines_span_every_aligned_candidate(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50), rect("b", 0, 300, 100, 50)]

        result = self.move(candidates, box(2, 140, 102, 190))

        self.assert_snap(result, -2, 0, True, False)
        self.assertEqual(result["lines"], [line("x", 0, 0, 350), line("x", 50, 0, 350), line("x", 100, 0, 350)])
        self.assertEqual(result["gaps"], [])

    def test_lines_merge_candidates_that_share_a_value(self) -> None:
        # Two candidates share the left edge 0: one line spans both and the moving rect.
        candidates = [rect("a", 0, 0, 100, 50), rect("b", 0, 400, 60, 30), rect("c", 500, 100, 80, 40)]

        result = self.move(candidates, box(3, 200, 43, 240))

        self.assertEqual([entry for entry in result["lines"] if entry["axis"] == "x"], [line("x", 0, 0, 430)])


class MoveAxisLockTests(_EngineCase):
    def test_horizontal_lock_keeps_dy_and_reports_only_exact_y_alignments(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50)]

        near = self.move(candidates, box(3, 3, 63, 33), axisLock="horizontal")
        exact = self.move(candidates, box(3, 0, 63, 40), dy=0.3, axisLock="horizontal")

        # Unlocked, the near case snaps Y too (top 3 -> 0).
        self.assert_snap(self.move(candidates, box(3, 3, 63, 33)), -3, -3, True, True)
        self.assert_snap(near, -3, 0, True, False)
        self.assertEqual([entry["axis"] for entry in near["lines"]], ["x"])
        self.assert_snap(exact, -3, 0.3, True, False)
        self.assertIn(line("y", 0, 0, 100), exact["lines"])

    def test_vertical_lock_keeps_dx_and_reports_only_exact_x_alignments(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50)]

        result = self.move(candidates, box(103, 53, 163, 93), axisLock="vertical")

        self.assert_snap(self.move(candidates, box(103, 53, 163, 93)), -3, -3, True, True)
        self.assert_snap(result, 0, -3, False, True)
        self.assertEqual(result["lines"], [line("y", 50, 0, 163)])


class MoveSpacingTests(_EngineCase):
    def test_equal_spacing_centres_between_two_neighbours(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50), rect("c", 300, 0, 100, 50)]

        result = self.move(candidates, box(153, 12, 253, 62))

        self.assert_snap(result, -3, 0, True, False)
        self.assertEqual(result["lines"], [])
        self.assertEqual(result["gaps"], [gap("x", 100, 150, 12, 50), gap("x", 250, 300, 12, 50)])

    def test_equal_spacing_repeats_an_existing_gap_after_a_row(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50), rect("b", 140, 0, 100, 50)]

        result = self.move(candidates, box(284, 12, 384, 62))

        self.assert_snap(result, -4, 0, True, False)
        # Every marker crosses the part of its rects' shared span inside the moving rect's band (y 12..50).
        self.assertEqual(result["gaps"], [gap("x", 240, 280, 12, 50), gap("x", 100, 140, 12, 50)])

    def test_equal_spacing_repeats_an_existing_gap_before_a_row(self) -> None:
        candidates = [rect("b", 140, 0, 100, 50), rect("c", 280, 0, 100, 50)]

        result = self.move(candidates, box(4, 12, 104, 62))

        self.assert_snap(result, -4, 0, True, False)
        self.assertEqual(result["gaps"], [gap("x", 100, 140, 12, 50), gap("x", 240, 280, 12, 50)])

    def test_vertical_equal_spacing_repeats_a_column_gap(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50), rect("b", 0, 90, 100, 50)]

        result = self.move(candidates, box(20, 184, 60, 224))

        self.assert_snap(result, 0, -4, False, True)
        self.assertEqual(result["gaps"], [gap("y", 140, 180, 20, 60), gap("y", 50, 90, 20, 60)])

    def test_alignment_wins_a_tie_with_spacing(self) -> None:
        # Spacing wants left 280 (delta -3); the far candidate "d" offers left 286 (delta +3).
        candidates = [rect("a", 0, 0, 100, 50), rect("b", 140, 0, 100, 50), rect("d", 286, 500, 100, 50)]

        result = self.move(candidates, box(283, 12, 383, 62))

        self.assert_snap(result, 3, 0, True, False)
        self.assertIn(line("x", 286, 12, 550), result["lines"])
        self.assertEqual(result["gaps"], [])

    def test_spacing_wins_when_closer(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50), rect("b", 140, 0, 100, 50), rect("d", 286, 500, 100, 50)]

        result = self.move(candidates, box(282, 12, 382, 62))

        self.assert_snap(result, -2, 0, True, False)
        self.assertEqual(result["lines"], [])
        self.assertEqual(result["gaps"], [gap("x", 240, 280, 12, 50), gap("x", 100, 140, 12, 50)])

    def test_spacing_can_be_turned_off(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50), rect("c", 300, 0, 100, 50)]

        result = self.move(candidates, box(153, 12, 253, 62), spacing=False)

        self.assert_snap(result, 0, 0, False, False)
        self.assertEqual(result["gaps"], [])

    def test_a_gap_the_moving_rect_sits_in_is_not_an_existing_gap(self) -> None:
        # Internal row query: a..b counts as a band gap until the moving rect sits in it.
        candidates = json.dumps([rect("a", 0, 0, 100, 50), rect("b", 300, 0, 100, 50)])
        gap_count = "(function(moving) {{ return rowAround(buildIndex({0}), AXIS_X, moving, 0.5, 0.5, {{}}).gapCount; }})"

        self.assertEqual(self.evaluate(gap_count.format(candidates) + f"({json.dumps(box(450, 12, 550, 62))})"), 1)
        self.assertEqual(self.evaluate(gap_count.format(candidates) + f"({json.dumps(box(150, 12, 250, 62))})"), 0)

    def test_a_rect_lying_over_a_gap_hides_it(self) -> None:
        # c covers the whole space between a and b, so a..b (140) is no gap; only c..b (20) is.
        candidates = [rect("a", 0, 0, 100, 50), rect("c", 80, 0, 140, 50), rect("b", 240, 0, 100, 50)]

        hidden = self.move(candidates, box(484, 0, 584, 50))
        real = self.move(candidates, box(364, 0, 464, 50))

        self.assert_snap(hidden, 0, 0, False, True)
        self.assertEqual(hidden["gaps"], [])
        self.assert_snap(real, -4, 0, True, True)
        self.assertEqual(real["gaps"], [gap("x", 340, 360, 0, 50), gap("x", 220, 240, 0, 50)])

    def test_a_rect_between_two_others_over_part_of_their_span_splits_their_gap(self) -> None:
        # m sits between a and c over the top half of the span they share, so a..c (200) is no gap;
        # a..m and m..c (50 each) are.
        candidates = [rect("a", 0, 0, 100, 100), rect("m", 150, 0, 100, 50), rect("c", 300, 0, 100, 100)]

        hidden = self.move(candidates, box(604, 0, 704, 100))
        real = self.move(candidates, box(454, 0, 554, 100))

        self.assert_snap(hidden, 0, 0, False, True)
        self.assertEqual(hidden["gaps"], [])
        self.assert_snap(real, -4, 0, True, True)
        self.assertEqual(real["gaps"], [gap("x", 400, 450, 0, 100), gap("x", 250, 300, 0, 50), gap("x", 100, 150, 0, 50)])

    def test_a_rect_between_two_others_over_the_far_part_of_their_span_splits_their_gap_too(self) -> None:
        # The mirror case: m covers the bottom half of the span a and c share, which ends where theirs does.
        candidates = [rect("a", 0, 0, 100, 100), rect("m", 150, 50, 100, 50), rect("c", 300, 0, 100, 100)]

        hidden = self.move(candidates, box(604, 0, 704, 100))
        real = self.move(candidates, box(454, 0, 554, 100))

        self.assert_snap(hidden, 0, 0, False, True)
        self.assertEqual(hidden["gaps"], [])
        self.assert_snap(real, -4, 0, True, True)
        self.assertEqual(real["gaps"], [gap("x", 400, 450, 0, 100), gap("x", 250, 300, 50, 100), gap("x", 100, 150, 50, 100)])

    def test_gap_markers_carry_the_cross_span_their_rects_share(self) -> None:
        # a (y 0..60) and b (y 30..90) start at different heights. Inside the moving rect's band (y 10..100)
        # a..b share y 30..60, and b..rect share all of b there, y 30..90.
        candidates = [rect("a", 0, 0, 100, 60), rect("b", 140, 30, 100, 60)]

        result = self.move(candidates, box(284, 10, 384, 100), axisLock="horizontal")

        self.assert_snap(result, -4, 0, True, False)
        self.assertEqual(result["gaps"], [gap("x", 240, 280, 30, 90), gap("x", 100, 140, 30, 60)])

    def test_gaps_pair_only_rects_that_share_a_row(self) -> None:
        # Row 1 has a 50 gap and row 2 a 60 gap; a2..b1 (10) crosses rows and is no gap.
        candidates = [
            rect("a1", 0, 0, 100, 50), rect("b1", 150, 0, 100, 50),
            rect("a2", 40, 60, 100, 50), rect("b2", 200, 60, 100, 50),
        ]

        across = self.move(candidates, box(313, 0, 413, 110))
        in_row = self.move(candidates, box(357, 60, 457, 110))

        self.assert_snap(across, 0, 0, False, True)
        self.assertEqual([entry for entry in across["gaps"] if entry["axis"] == "x"], [])
        self.assert_snap(in_row, 3, 0, True, True)
        self.assertEqual([entry for entry in in_row["gaps"] if entry["axis"] == "x"],
                         [gap("x", 300, 360, 60, 110), gap("x", 140, 200, 60, 110)])

    def test_a_group_border_hides_the_gap_from_a_node_inside_it(self) -> None:
        # n1 sits inside Group g, so n1..n2 (380) is covered by the Group; g..n2 (100) is the real gap.
        candidates = [rect("g", 0, 0, 400, 200), rect("n1", 20, 40, 100, 50), rect("n2", 500, 40, 100, 50)]

        across = self.move(candidates, box(984, 40, 1084, 90))
        real = self.move(candidates, box(704, 40, 804, 90))

        self.assert_snap(across, 0, 0, False, True)
        self.assertEqual(across["gaps"], [])
        self.assert_snap(real, -4, 0, True, True)
        self.assertEqual([entry for entry in real["gaps"] if entry["axis"] == "x"],
                         [gap("x", 600, 700, 40, 90), gap("x", 400, 500, 40, 90)])

    def test_a_group_the_moving_rect_is_inside_hides_none_of_its_members(self) -> None:
        # Dragged inside Group g, the rect repeats n1..n2 (100) after n2: g holds the rect, so it is left out
        # of equal spacing, where it would cover both members. It still gives alignment lines.
        candidates = [rect("g", 0, 0, 1000, 300), rect("n1", 100, 100, 100, 50), rect("n2", 300, 100, 100, 50)]

        result = self.move(candidates, box(504, 100, 604, 150))
        at_the_border = self.move(candidates, box(3, 100, 53, 150))

        self.assert_snap(result, -4, 0, True, True)
        self.assertEqual(result["gaps"], [gap("x", 400, 500, 100, 150), gap("x", 200, 300, 100, 150)])
        self.assert_snap(at_the_border, -3, 0, True, True)
        self.assertIn(line("x", 0, 0, 300), at_the_border["lines"])

    def test_a_group_holds_a_rect_on_its_edge(self) -> None:
        # The rect lies along g's top edge, so g still holds it and n1..n2 (100) shows.
        candidates = [rect("g", 0, 0, 1000, 300), rect("n1", 100, 0, 100, 50), rect("n2", 300, 0, 100, 50)]

        result = self.move(candidates, box(504, 0, 604, 50))

        self.assert_snap(result, -4, 0, True, True)
        self.assertEqual(result["gaps"], [gap("x", 400, 500, 0, 50), gap("x", 200, 300, 0, 50)])

    def test_whether_a_group_holds_the_rect_is_decided_where_the_drag_puts_it(self) -> None:
        # The rect pokes out of g's top (-3) until its Y snap (+3) settles it inside. Containment is judged
        # once, at the input offset, so g still covers n1..n2 there and no equal-spacing marker shows.
        candidates = [rect("g", 0, 0, 1000, 300), rect("n1", 100, 10, 100, 30), rect("n2", 300, 10, 100, 30)]

        result = self.move(candidates, box(500, -3, 600, 47))

        self.assert_snap(result, 0, 3, False, True)
        self.assertEqual(result["gaps"], [])

    def test_a_group_the_moving_rect_is_outside_still_hides_its_members(self) -> None:
        # Outside g, the rect repeats g..k (100) after k, and g still covers n1..n2.
        candidates = [
            rect("g", 0, 0, 1000, 300), rect("n1", 100, 100, 100, 50), rect("n2", 300, 100, 100, 50),
            rect("k", 1100, 100, 100, 50),
        ]

        result = self.move(candidates, box(1304, 100, 1404, 150))

        self.assert_snap(result, -4, 0, True, True)
        self.assertEqual(result["gaps"], [gap("x", 1200, 1300, 100, 150), gap("x", 1000, 1100, 100, 150)])

    def test_a_row_the_moving_rect_only_touches_does_not_attract(self) -> None:
        # The moving top edge touches the row's bottom edge: no overlap, so no band and no centring (-3).
        candidates = [rect("a", 0, 0, 100, 50), rect("c", 300, 0, 100, 50)]

        result = self.move(candidates, box(153, 50, 253, 100))

        self.assert_snap(result, 0, 0, False, True)
        self.assertEqual([entry for entry in result["gaps"] if entry["axis"] == "x"], [])

    def test_gaps_no_wider_than_the_line_tolerance_never_attract(self) -> None:
        # a..b is a 0.3 gap: spacing would pull the rect to 200.6 (-4.4); it abuts b at 200.3 (-4.7) instead.
        candidates = [rect("a", 0, 0, 100, 50), rect("b", 100.3, 0, 100, 50)]

        result = self.move(candidates, box(205, 0, 305, 50))

        self.assertAlmostEqual(result["dx"], -4.7, places=9)
        self.assertIn(line("x", 100.3 + 100, 0, 50), result["lines"])  # b's right edge, summed as the engine does
        self.assertEqual(result["gaps"], [])

    def test_a_neighbour_overlapping_by_less_than_the_threshold_still_counts(self) -> None:
        # d overlaps the moving rect by 2 on its upper half, so d is the neighbour before it and the rect
        # abuts d (+2). Ignoring d would make a (lower half) the neighbour, and e..f (102) would pull the
        # rect to a + 102 (-1).
        candidates = [
            rect("d", 155, 0, 50, 40), rect("a", 0, 60, 100, 40),
            rect("e", 1000, 0, 100, 100), rect("f", 1202, 0, 100, 100),
        ]

        result = self.move(candidates, box(203, 0, 303, 100))

        self.assert_snap(result, 2, 0, True, True)
        self.assertIn(line("x", 205, 0, 100), result["lines"])

    def test_a_neighbour_after_overlapping_by_less_than_the_threshold_still_counts(self) -> None:
        # The mirror case: d overlaps the rect by 2 on its upper half, so d is the neighbour after it and the
        # rect abuts d (-2). Ignoring d would make a (lower half) the neighbour, and e..f (104) would pull the
        # rect to a - 104 (-1).
        candidates = [
            rect("d", 295, 0, 50, 40), rect("a", 400, 60, 100, 40),
            rect("e", -1000, 0, 100, 100), rect("f", -796, 0, 100, 100),
        ]

        result = self.move(candidates, box(197, 0, 297, 100))

        self.assert_snap(result, -2, 0, True, True)
        self.assertIn(line("x", 295, 0, 100), result["lines"])

    def test_the_moving_rect_hides_a_band_rect_ending_where_it_ends(self) -> None:
        # E ends at x 200 like the rect: on that tie the rect takes over E's part of the skyline, so R sees
        # the rect, not E, and rect..R (100) repeats p..q. (E stops short of the rect's bottom edge, so it
        # does not hold the rect and stays in the band.)
        candidates = [
            rect("E", 50, 0, 150, 90), rect("R", 300, 0, 100, 100),
            rect("p", 1000, 0, 100, 100), rect("q", 1200, 0, 100, 100),
        ]

        result = self.move(candidates, box(100, 0, 200, 100))

        self.assert_snap(result, 0, 0, True, True)
        self.assertEqual(result["gaps"], [gap("x", 200, 300, 0, 100), gap("x", 1100, 1200, 0, 100)])

    def test_a_band_rect_ending_where_an_earlier_one_ends_does_not_hide_it(self) -> None:
        # B ends at x 200 like A, which spans all of C's height: A keeps that height, so C sees A across
        # y 0..100 and a..c is the gap the rect repeats. Were B to take over y 0..50, C would see B there
        # instead and A nowhere.
        candidates = [rect("A", 0, 0, 200, 100), rect("B", 100, 0, 100, 50), rect("C", 300, 0, 100, 100)]

        result = self.move(candidates, box(504, 0, 604, 100))

        self.assert_snap(result, -4, 0, True, True)
        self.assertEqual(result["gaps"], [gap("x", 400, 500, 0, 100), gap("x", 200, 300, 0, 100)])

    def test_the_neighbour_before_on_a_tie_is_the_earlier_band_rect(self) -> None:
        # A (y 0..50) and B (y 60..100) both end at x 100 and both show fully beside the rect: A, first in
        # the band, is its neighbour before, so the marker crosses A's height.
        candidates = [
            rect("A", 0, 0, 100, 50), rect("B", 0, 60, 100, 40),
            rect("p", 500, 0, 100, 100), rect("q", 700, 0, 100, 100),
        ]

        result = self.move(candidates, box(204, 0, 304, 100))

        self.assert_snap(result, -4, 0, True, True)
        self.assertEqual(result["gaps"], [gap("x", 100, 200, 0, 50), gap("x", 600, 700, 0, 100)])

    def test_a_centred_slot_needs_more_than_the_line_tolerance_on_each_side(self) -> None:
        # a and b leave 1 free around the rect: 0.5 a side is no wider than the line tolerance, so there is
        # no centred slot (-0.125); the right edge abuts b (+0.375) instead. Binary-exact values.
        candidates = [rect("a", 0, 0, 100, 50), rect("b", 201, 0, 100, 50)]

        result = self.move(candidates, box(100.625, 0, 200.625, 50))

        self.assert_snap(result, 0.375, 0, True, True)
        self.assertIn(line("x", 201, 0, 50), result["lines"])
        self.assertEqual([entry for entry in result["gaps"] if entry["axis"] == "x"], [])

    def test_centring_needs_room_between_the_neighbours(self) -> None:
        # a and b sit 93 apart around a 100 wide rect, so there is no centred slot. Centring anyway would
        # pull the rect 0.5 left, where c..rect then matches p..q (40) and would look justified.
        candidates = [
            rect("a", 0, 0, 100, 40), rect("b", 193, 0, 100, 40), rect("c", -43.5, 60, 100, 40),
            rect("p", 1000, 0, 100, 100), rect("q", 1140, 0, 100, 100),
        ]

        result = self.move(candidates, box(97, 0, 197, 100))

        self.assert_snap(result, 3, 0, True, True)
        self.assertEqual([entry for entry in result["gaps"] if entry["axis"] == "x"], [])

    def test_gap_markers_cap_at_six_per_axis_nearest_first(self) -> None:
        row = [rect(f"n{index}", index * 70, 0, 50, 50) for index in range(9)]

        result = self.move(row, box(632, 0, 682, 50))

        self.assert_snap(result, -2, 0, True, True)
        expected = [gap("x", 610, 630, 0, 50)] + [gap("x", 70 * k + 50, 70 * (k + 1), 0, 50) for k in (7, 6, 5, 4, 3)]
        self.assertEqual(result["gaps"], expected)

    def test_markers_tied_on_distance_and_start_are_ordered_by_their_cross_position(self) -> None:
        # Three identical rows: each row gap ties with the same gap in the other rows on distance and start, so
        # their cross position orders them. Past the cap of six only two of the three 190..210 gaps stay: those
        # of the top two rows. (The engine's sort is not stable from ten items on, so it cannot decide.)
        rows = [rect(f"n{row}_{column}", column * 70, row * 100, 50, 50) for row in range(3) for column in range(5)]

        result = self.move(rows, box(348, 0, 398, 250))

        self.assert_snap(result, 2, 0, True, True)
        expected = [gap("x", 330, 350, 0, 50)]
        expected += [gap("x", 260, 280, 100 * row, 100 * row + 50) for row in range(3)]
        expected += [gap("x", 190, 210, 100 * row, 100 * row + 50) for row in range(2)]
        self.assertEqual([entry for entry in result["gaps"] if entry["axis"] == "x"], expected)


class MoveGuideInvariantTests(_EngineCase):
    """An axis only snaps (and moves) when a line or gap marker on it holds at the returned offset."""

    def test_a_spacing_snap_the_other_axis_undoes_is_dropped(self) -> None:
        # Spacing centres the rect between a and c (-3), but aligning its top with their bottoms (+3) moves it
        # out of their row, so no guide would show the X snap.
        row = [rect("a", 0, 0, 100, 50), rect("c", 300, 0, 100, 50)]

        result = self.move(row, box(153, 47, 253, 97))

        self.assert_snap(result, 0, 3, False, True)
        self.assertEqual(result["lines"], [line("y", 50, 0, 400)])
        self.assertEqual(result["gaps"], [])

    def test_the_mirror_case_drops_the_vertical_spacing_snap(self) -> None:
        column = [rect("a", 0, 0, 100, 50), rect("c", 0, 250, 100, 50)]

        result = self.move(column, box(97, 122, 197, 172))

        self.assert_snap(result, 3, 0, True, False)
        self.assertEqual(result["lines"], [line("x", 100, 0, 300)])
        self.assertEqual(result["gaps"], [])

    def test_a_dropped_spacing_snap_falls_back_to_the_axis_alignment_snap(self) -> None:
        # As above, but k's left edge offers an X alignment 5 away: it was farther than centring (-3) and
        # takes over once centring is dropped.
        candidates = [rect("a", 0, 0, 100, 50), rect("c", 300, 0, 100, 50), rect("k", 148, 400, 50, 50)]

        result = self.move(candidates, box(153, 47, 253, 97))

        self.assert_snap(result, -5, 3, True, True)
        self.assertEqual(result["lines"], [line("x", 148, 50, 450), line("y", 50, 0, 400)])

    def test_every_snapped_axis_shows_a_guide_at_the_returned_offset(self) -> None:
        rng = random.Random(20260926)
        layouts = []
        for _ in range(60):
            grid = rng.choice([0.0, 1.0, 5.0, 10.0, 20.0])

            def value(low: float, high: float) -> float:
                sample = rng.uniform(low, high)
                return round(sample / grid) * grid if grid else sample

            candidates = [
                rect(f"n{index}", value(0, 600), value(0, 600), max(1.0, value(10, 160)), max(1.0, value(10, 160)))
                for index in range(rng.randint(2, 40))
            ]
            if rng.random() < 0.2:
                candidates.append(rect("tall", value(-100, 700), -200.0, max(1.0, value(20, 60)), 1000.0))
            moves = []
            for _ in range(50):
                left, top = value(-50, 650), value(-50, 650)
                moves.append([
                    box(left, top, left + max(1.0, value(10, 170)), top + max(1.0, value(10, 170))),
                    rng.uniform(-4, 4),
                    rng.uniform(-4, 4),
                    rng.choice([8.0, 4.0, 12.0]),
                    rng.choice(["", "", "", "horizontal", "vertical"]),
                    rng.random() > 0.1,
                ])
            layouts.append([candidates, moves])

        report = self.evaluate(
            "(function(layouts) {"
            " var report = {checked: 0, snapped: 0, withGaps: 0, failures: []};"
            " function shown(result, axis) {"
            "  for (var i = 0; i < result.lines.length; ++i) if (result.lines[i].axis === axis) return true;"
            "  for (var j = 0; j < result.gaps.length; ++j) if (result.gaps[j].axis === axis) return true;"
            "  return false; }"
            " for (var l = 0; l < layouts.length; ++l) {"
            "  var index = buildIndex(layouts[l][0]); var moves = layouts[l][1];"
            "  for (var m = 0; m < moves.length; ++m) {"
            "   var move = moves[m];"
            "   var result = resolveMove(index, move[0], move[1], move[2],"
            "                            {threshold: move[3], axisLock: move[4], spacing: move[5]});"
            "   if (result.gaps.length > 0) ++report.withGaps;"
            "   var axes = [['x', result.snappedX, result.dx - move[1], 'vertical'],"
            "               ['y', result.snappedY, result.dy - move[2], 'horizontal']];"
            "   for (var a = 0; a < axes.length; ++a) {"
            "    var axis = axes[a]; var problem = '';"
            "    if (axis[1] && !shown(result, axis[0])) problem = 'snapped without a guide';"
            "    else if (Math.abs(axis[2]) > move[3] + 1e-9) problem = 'moved beyond the threshold';"
            "    else if (!axis[1] && axis[2] !== 0) problem = 'moved without snapping';"
            "    else if (move[4] === axis[3] && axis[1]) problem = 'snapped a locked axis';"
            "    if (problem) report.failures.push([problem, axis[0], l, m]);"
            "    if (axis[1]) ++report.snapped;"
            "    ++report.checked; } } }"
            " report.failures = report.failures.slice(0, 5); return report; })"
            f"({json.dumps(layouts)})"
        )

        self.assertEqual(report["failures"], [], "[problem, axis, layout, move]")
        self.assertEqual(report["checked"], 60 * 50 * 2)
        self.assertGreater(report["snapped"], report["checked"] // 5)
        self.assertGreater(report["withGaps"], 0)


class SpacingBandLimitTests(_EngineCase):
    """An axis whose band holds more than SPACING_BAND_LIMIT rects gets no equal spacing; alignment still snaps."""

    def band_layout(self, fillers: int) -> list[dict]:
        # A row with 20 gaps, `fillers` thin rects far to its left in the same band (y 0..50), and a rect below
        # whose left edge 358 offers an X alignment 5 away from the moving rect at 353.
        row = [rect(f"n{column}", column * 70, 0, 50, 50) for column in range(5)]
        filler = [rect(f"f{index}", -10000 + index * 2, 10, 1, 10) for index in range(fillers)]
        return row + filler + [rect("aligned", 358, 500, 50, 50)]

    def row_markers(self) -> list[dict]:
        return [gap("x", 330, 350, 0, 50)] + [gap("x", 70 * k + 50, 70 * (k + 1), 0, 50) for k in (3, 2, 1, 0)]

    def test_the_limit_is_256_band_rects(self) -> None:
        self.assertEqual(self.evaluate("SPACING_BAND_LIMIT"), 256)

    def test_a_band_at_the_limit_still_gets_equal_spacing(self) -> None:
        layout = self.band_layout(251)
        band = self.evaluate(f"bandAround(buildIndex({json.dumps(layout)}), AXIS_X, {json.dumps(box(353, 0, 403, 50))}, 0, {{}})")

        result = self.move(layout, box(353, 0, 403, 50))
        # With a threshold of 4, the rect already at the row's gap does not align (358 is 8 away).
        at_the_gap = self.move(layout, box(350, 0, 400, 50), threshold=4)

        self.assertEqual(band, 256)
        # Spacing (-3) beats the alignment 5 away.
        self.assert_snap(result, -3, 0, True, True)
        self.assertEqual([entry for entry in result["gaps"] if entry["axis"] == "x"], self.row_markers())
        self.assertEqual([entry for entry in at_the_gap["gaps"] if entry["axis"] == "x"], self.row_markers())

    def test_a_band_past_the_limit_gets_no_equal_spacing_but_still_aligns(self) -> None:
        layout = self.band_layout(252)
        band = self.evaluate(f"bandAround(buildIndex({json.dumps(layout)}), AXIS_X, {json.dumps(box(353, 0, 403, 50))}, 0, {{}})")

        result = self.move(layout, box(353, 0, 403, 50))
        at_the_gap = self.move(layout, box(350, 0, 400, 50), threshold=4)

        self.assertEqual(band, 257)
        # No spacing snap and no gap markers on X; the alignment 5 away snaps and shows its line.
        self.assert_snap(result, 5, 0, True, True)
        self.assertIn(line("x", 358, 0, 550), result["lines"])
        self.assertEqual([entry for entry in result["gaps"] if entry["axis"] == "x"], [])
        # Even where the gap already matches the row's, no marker shows.
        self.assert_snap(at_the_gap, 0, 0, False, True)
        self.assertEqual([entry for entry in at_the_gap["gaps"] if entry["axis"] == "x"], [])

    def test_a_group_that_holds_the_rect_counts_towards_the_limit(self) -> None:
        # The limit counts the whole band, a Group backdrop holding the moving rect included, although the
        # sweep then leaves that Group out.
        group = rect("group", -20000, -100, 22000, 700)
        at_the_limit = self.move(self.band_layout(250) + [group], box(353, 0, 403, 50))
        past_the_limit = self.move(self.band_layout(251) + [group], box(353, 0, 403, 50))

        self.assert_snap(at_the_limit, -3, 0, True, True)
        self.assertEqual([entry for entry in at_the_limit["gaps"] if entry["axis"] == "x"], self.row_markers())
        self.assert_snap(past_the_limit, 5, 0, True, True)
        self.assertEqual([entry for entry in past_the_limit["gaps"] if entry["axis"] == "x"], [])


class BandQueryTests(_EngineCase):
    def test_a_band_lists_exactly_the_rects_it_overlaps_in_low_edge_order(self) -> None:
        # sortedBand reads a band whose ranks lie close together back from rank marks and sorts any other;
        # call after call, either way, it lists exactly the rects overlapping the interval, by left edge.
        rng = random.Random(20260928)
        candidates = [
            rect(f"n{index}", rng.uniform(0, 1000), rng.uniform(0, 1000), rng.uniform(10, 200), rng.uniform(10, 200))
            for index in range(80)
        ]
        intervals = []
        for _ in range(30):
            low = rng.uniform(-100, 1000)
            intervals.append([low, low + (rng.uniform(600, 1200) if rng.random() < 0.5 else rng.uniform(1, 40))])

        bands = self.evaluate(
            "(function(a) { var index = buildIndex(a[0]); var out = [];"
            " for (var i = 0; i < a[1].length; ++i) { var count = sortedBand(index, AXIS_X, a[1][i][0], a[1][i][1]);"
            "  out.push(index.scratch.bandIds.x.slice(0, count)); }"
            f" return out; }})({json.dumps([candidates, intervals])})"
        )

        dense = 0
        for (low, high), band in zip(intervals, bands):
            expected = sorted(
                (index for index, entry in enumerate(candidates) if entry["y"] + entry["height"] > low and entry["y"] < high),
                key=lambda index: (candidates[index]["x"], index),
            )
            self.assertEqual([int(entry) for entry in band], expected, (low, high))
            ranks = sorted(sorted(range(len(candidates)), key=lambda index: (candidates[index]["x"], index)).index(index)
                           for index in expected)
            dense += bool(ranks) and ranks[-1] - ranks[0] < 8 * len(ranks)
        self.assertGreater(dense, 5)
        self.assertLess(dense, len(intervals) - 5)


class SlotMarkTests(_EngineCase):
    def test_marks_find_the_highest_mark_at_or_below_a_position_at_every_level(self) -> None:
        # slotMarks keeps a bit per slot and, on each level above, a bit per word below that holds a mark; a
        # sweep searches levels 2 and up through markAtOrBelow. Slot counts of 1000, 5000, 70000 and 1.1 million
        # give two to five levels. Marks toggle at random and next to word and level boundaries, and after each
        # toggle markAtOrBelow, from every level, must name the highest marked slot of the same set kept sorted.
        report = self.evaluate(r"""(function() {
            var seed = 20260929;
            function random(count) { seed = (seed * 1103515245 + 12345) % 2147483648; return seed % count; }
            var report = {levels: [], checks: 0, climbs: 0, failures: []};
            var sizes = [1000, 5000, 70000, 1100000];
            for (var z = 0; z < sizes.length; ++z) {
                var slots = sizes[z];
                var levels = slotMarks(slots);
                report.levels.push(levels.length);
                var marked = [];
                // Positions of the sorted marks at or below `slot`.
                var upTo = function(slot) {
                    var low = 0, high = marked.length;
                    while (low < high) { var mid = (low + high) >> 1; if (marked[mid] <= slot) low = mid + 1; else high = mid; }
                    return low;
                };
                var span = function(level) { return Math.pow(32, level); };
                var pick = function() {
                    if (random(3) === 0)
                        return random(slots);
                    // Next to a word or block boundary, where searches climb and descend.
                    var size = span(1 + random(levels.length - 1));
                    var at = size * random(Math.ceil(slots / size)) + random(3) - 1;
                    return Math.min(slots - 1, Math.max(0, at));
                };
                var check = function(level, position) {
                    var last = Math.min(slots - 1, (position + 1) * span(level) - 1);
                    var below = upTo(last);
                    var want = position < 0 || below === 0 ? -1 : marked[below - 1];
                    var got = markAtOrBelow(levels, level, position);
                    ++report.checks;
                    if (level === 0 && want >= 0 && (want >> 5) !== (position >> 5))
                        ++report.climbs;
                    if (got !== want && report.failures.length < 5)
                        report.failures.push([slots, level, position, got, want]);
                };
                var consistent = function() {
                    for (var l = 1; l < levels.length; ++l) {
                        for (var w = 0; w < levels[l - 1].length; ++w) {
                            if (((levels[l][w >> 5] & (1 << (w & 31))) !== 0) !== (levels[l - 1][w] !== 0))
                                return false;
                        }
                    }
                    return true;
                };
                for (var step = 0; step < 700; ++step) {
                    var slot = pick();
                    var at = upTo(slot);
                    if (at > 0 && marked[at - 1] === slot) {
                        unmark(levels, 0, slot);
                        marked.splice(at - 1, 1);
                    } else {
                        mark(levels, 0, slot);
                        marked.splice(at, 0, slot);
                    }
                    for (var query = 0; query < 4; ++query) {
                        var level = random(levels.length);
                        var positions = Math.ceil(slots / span(level));
                        var near = marked.length > 0 ? marked[random(marked.length)] + random(3) - 1 : 0;
                        var position = random(2) === 0 ? random(positions) : Math.floor(Math.max(0, Math.min(slots - 1, near)) / span(level));
                        check(level, position);
                    }
                    check(0, slots - 1);
                    check(0, -1);
                    if (step % 100 === 0 && !consistent() && report.failures.length < 5)
                        report.failures.push([slots, "levels disagree after step", step]);
                }
                // One low mark below long runs of empty words and blocks: every search climbs to the top.
                clearMarks(levels);
                mark(levels, 0, 3);
                marked = [3];
                for (var probe = 0; probe < 40; ++probe)
                    check(0, probe === 0 ? slots - 1 : random(slots));
                if (!consistent())
                    report.failures.push([slots, "levels disagree after clearing"]);
            }
            return report;
        })()""")

        self.assertEqual(report["levels"], [2, 3, 4, 5])
        self.assertEqual(report["failures"], [], "[slots, level, position, found, wanted]")
        self.assertGreater(report["climbs"], 500)


class SkylineSearchTests(_EngineCase):
    def test_walking_and_marking_the_skyline_give_the_same_results(self) -> None:
        # A sweep walks a short skyline to the segment under a span start and, past WALK_SEGMENTS segments,
        # looks it up in marks of the segment starts. Forcing either search must change no result.
        rng = random.Random(20260927)
        layouts = []
        for layout in range(24):
            if layout % 2:
                columns, rows = rng.randint(3, 14), rng.randint(3, 14)
                candidates = [
                    rect(f"n{column}_{row}", column * 240.0 + rng.uniform(-30, 30), row * 140.0 + rng.uniform(-30, 30),
                         200.0, 100.0)
                    for column in range(columns)
                    for row in range(rows)
                ]
                width, height = columns * 240.0, rows * 140.0
            else:
                width = height = 600.0
                candidates = [
                    rect(f"n{index}", rng.uniform(0, width), rng.uniform(0, height), rng.uniform(10, 150), rng.uniform(10, 150))
                    for index in range(rng.randint(5, 60))
                ]
                candidates.append(rect("group", 50.0, 50.0, 400.0, 400.0))
            moves = []
            for _ in range(20):
                left, top = rng.uniform(0, width), rng.uniform(0, height)
                tall = rng.random() < 0.5
                moves.append([
                    box(left, top, left + rng.uniform(40, 240), top + (rng.uniform(0.3, 0.9) * height if tall else rng.uniform(30, 150))),
                    rng.uniform(-4, 4),
                    rng.uniform(-4, 4),
                ])
            layouts.append([candidates, moves])

        default = self.assert_searches_agree(layouts)

        self.assertGreater(sum('"gaps":[{' in result for result in default), len(default) // 10)

    def test_walking_and_marking_agree_where_a_search_crosses_an_emptied_block_of_slots(self) -> None:
        # Past 511 rects the marks have a third level, a bit per block of 1024 slots. The 1000 rects far above
        # the band take the lowest slots, so the band's edges get slots 2001 (T's top) to 2086 (T's bottom):
        # the rows r at 2002-2025 in block 1 (up to 2047), the lowest rows s in block 2. Tall T, swept after
        # the rows r, covers them all and empties block 1, whose level-2 bit must clear. The lowest row s,
        # swept next from slot 2084, finds no mark at or below it in its block (T's split, 2086, lies above
        # it) and drops to level 2, where only block 0 still holds a mark (the skyline's first segment, now
        # T's). The band holds 43 rects, under SPACING_BAND_LIMIT.
        far = [rect(f"f{index}", -200000.0 - 300.0 * (index % 7), -60000.0 + index * 20.0, 100.0, 10.0)
               for index in range(1000)]
        tall = [rect("T", 0.0, -3100.0, 1000.0, 1850.0)]
        upper = [rect(f"r{index}", -200.0, -3000.0 + index * 20.0, 300.0, 10.0) for index in range(12)]
        lower = [rect(f"s{index}", 1100.0, -1300.0 - index * 20.0, 200.0, 10.0) for index in range(30)]
        moves = [[box(1400.0 + shift, -3050.0, 1500.0 + shift, -1200.0), dx, dy]
                 for shift, dx, dy in ((3.0, 0.0, 0.0), (-2.0, 0.5, 1.0), (5.0, -1.0, -2.0), (0.0, 2.0, 3.0), (7.0, 0.0, 0.0))]
        candidates = far + tall + upper + lower
        band = self.evaluate(f"bandAround(buildIndex({json.dumps(candidates)}), AXIS_X, {json.dumps(moves[0][0])}, 0, {{}})")

        default = self.assert_searches_agree([[candidates, moves]])

        self.assertEqual(band, 43)
        # Each move repeats T..s (100) after the rows s: the searches above decide what the rect sees.
        self.assertTrue(all('"gaps":[{"axis":"x","start":1300,"end":1400' in result for result in default), default[0])

    def assert_searches_agree(self, layouts: list) -> list[str]:
        """resolveMove results over `layouts` ([candidates, [[base, dx, dy], ...]]) must not change when every
        sweep walks its skyline (WALK_SEGMENTS Infinity) or marks it from the start (0); returns the default run."""
        default, marked, walked = self.evaluate(
            "(function(layouts) { var saved = WALK_SEGMENTS; var runs = [];"
            " try { var limits = [saved, 0, Infinity];"
            "  for (var k = 0; k < limits.length; ++k) { WALK_SEGMENTS = limits[k]; var results = [];"
            "   for (var l = 0; l < layouts.length; ++l) { var index = buildIndex(layouts[l][0]);"
            "    for (var m = 0; m < layouts[l][1].length; ++m) { var move = layouts[l][1][m];"
            "     results.push(JSON.stringify(resolveMove(index, move[0], move[1], move[2], {threshold: 8}))); } }"
            "   runs.push(results); }"
            " } finally { WALK_SEGMENTS = saved; }"
            " return runs; })"
            f"({json.dumps(layouts)})"
        )
        self.assertEqual(marked, default)
        self.assertEqual(walked, default)
        return default


class SweepSafetyTests(_EngineCase):
    """A corrupt skyline or mark set ends the sweep: no hang, no spacing on that axis, clear marks after it."""

    # Thin rows t at the far left give the X sweep more than WALK_SEGMENTS segments, so the items after the
    # ninth find their segment through the marks; p and q before them leave a gap in the sweep before any
    # search. The moving rect at 353 wants spacing after the row n (-3) over the alignment with `aligned` (+5).
    ROW = [rect(f"n{column}", column * 70, 0, 50, 50) for column in range(5)] + [rect("aligned", 358, 500, 50, 50)]
    THIN_ROWS = ([rect("p", -3000, 0, 100, 50), rect("q", -2800, 0, 100, 50)]
                 + [rect(f"t{index}", -1000, 2 + 4 * index, 100, 2) for index in range(11)])

    def evaluate_with_watchdog(self, expression: str, seconds: float = 10.0):
        """Evaluate, interrupting the engine after `seconds` so that a hung sweep fails the test instead of
        stalling the run."""
        timer = threading.Timer(seconds, self.engine.setInterrupted, [True])
        timer.start()
        try:
            result = self.engine.evaluate(expression)
        finally:
            timer.cancel()
            interrupted = self.engine.isInterrupted()
            self.engine.setInterrupted(False)
        self.assertFalse(interrupted, "the sweep ran until the watchdog interrupted it")
        self.assertFalse(result.isError(), result.toString())
        return result.toVariant()

    def assert_corruption_ends_the_sweep(self, layout: list[dict], moving: dict, corrupt: str) -> None:
        """`corrupt` is the body of a JS function(index) that corrupts a fresh index of `layout`. resolveMove on
        it must return promptly with no equal spacing on X, so the alignment 5 away snaps, and leave every mark
        clear, so the next call matches a clean index; rowAround on it must report no neighbours and no gaps, not
        even p..q, found before the corrupt search."""
        fresh = self.move(layout, moving)
        self.assert_snap(fresh, -3, 0, True, True)
        self.assertEqual(len([entry for entry in fresh["gaps"] if entry["axis"] == "x"]), 5)

        started = time.perf_counter()
        report = self.evaluate_with_watchdog(
            "(function(layout, moving) {"
            f" function corrupt(index) {{ {corrupt} return index; }}"
            " function clear(index) { var marks = index.scratch.marks;"
            "  for (var l = 0; l < marks.length; ++l) for (var w = 0; w < marks[l].length; ++w)"
            "   if (marks[l][w] !== 0) return false;"
            "  return true; }"
            " var index = corrupt(buildIndex(layout));"
            " var result = resolveMove(index, moving, 0, 0, {threshold: 8});"
            " var clearAfterMove = clear(index);"
            " var again = resolveMove(index, moving, 0, 0, {threshold: 8});"
            " var rowIndex = corrupt(buildIndex(layout));"
            " var row = rowAround(rowIndex, AXIS_X, moving, 8, 0.5, {});"
            " return {result: result, clearAfterMove: clearAfterMove, again: again, row: row,"
            "  clearAfterRow: clear(rowIndex)}; })"
            f"({json.dumps(layout)}, {json.dumps(moving)})"
        )
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 2.0)
        self.assert_snap(report["result"], 5, 0, True, True)
        self.assertIn(line("x", 358, 0, 550), report["result"]["lines"])
        self.assertEqual([entry for entry in report["result"]["gaps"] if entry["axis"] == "x"], [])
        self.assertEqual(report["row"], {"before": -1, "after": -1, "gapCount": 0})
        self.assertTrue(report["clearAfterMove"])
        self.assertTrue(report["clearAfterRow"])
        self.assertEqual(report["again"], fresh)

    def test_a_corrupt_mark_ends_the_sweep_instead_of_hanging(self) -> None:
        # Row t10 starts at y 42. A stale mark on its slot, whose segment points back at itself from y 41,
        # would keep the sweep editing that segment forever; one starting at y 1000 lies past the span it is
        # found for, so the sweep would silently skip the row.
        for planted_start in (41, 1000):
            with self.subTest(planted_start=planted_start):
                self.assert_corruption_ends_the_sweep(
                    self.THIN_ROWS + self.ROW, box(353, 0, 403, 50),
                    "var slot = index.y.loSlot[index.nodeIds.indexOf('t10')];"
                    f" index.scratch.segmentStarts[slot] = {planted_start}; index.scratch.segmentNext[slot] = slot;"
                    " mark(index.scratch.marks, 0, slot);")

    def test_a_corrupt_upper_mark_ends_the_sweep_too(self) -> None:
        # Rect x (y 300..320) is swept right after the thin rows t, whose segment starts all lie in the first
        # 31 slots. Its span starts at slot 71, and the rects b swept after it hold the slots 37..70 between.
        # A stale level-1 mark for the empty second word of slots would lead its search to slot 31, which
        # starts no segment in this sweep but may hold one from a sweep of the other axis (the skyline arrays
        # serve both): here y 50 to the end, which would hide x without using up the step budget.
        layout = (self.THIN_ROWS + self.ROW + [rect("x", -500, 300, 100, 20)]
                  + [rect(f"b{index}", -400, 60 + 6 * index, 100, 3) for index in range(17)])
        self.assertEqual(self.evaluate(f"(function() {{ var index = buildIndex({json.dumps(layout)});"
                                       " return index.y.loSlot[index.nodeIds.indexOf('x')]; })()"), 71)

        self.assert_corruption_ends_the_sweep(
            layout, box(353, 0, 403, 400),
            "index.scratch.marks[1][0] |= 2; index.scratch.segmentStarts[31] = 50;"
            " index.scratch.segmentNext[31] = index.scratch.segmentNext.length - 1;")


class MoveInputTests(_EngineCase):
    def test_empty_index_returns_the_input_offset(self) -> None:
        empty = {"dx": 5, "dy": 6, "snappedX": False, "snappedY": False, "lines": [], "gaps": []}

        self.assertEqual(self.move([], box(0, 0, 10, 10), 5, 6), empty)
        invalid = [rect("nan", float("nan"), 0, 10, 10), rect("flat", 0, 0, 10, 0), rect("neg", 0, 0, -5, 10)]
        self.assertEqual(self.move(invalid, box(0, 0, 10, 10), 5, 6), empty)
        self.assertEqual(self.evaluate("buildIndex(null).count"), 0)

    def test_invalid_base_or_threshold_returns_the_input_offset(self) -> None:
        candidates = [rect("a", 0, 0, 100, 50)]

        self.assert_snap(self.move(candidates, box(3, 0, 3, 40), 1, 2), 1, 2, False, False)
        self.assert_snap(self.move(candidates, box(3, 0, 63, 40), 1, 2, threshold=0), 1, 2, False, False)

    def test_union_rect_covers_every_real_rect(self) -> None:
        rects = [rect("a", 10, 20, 30, 40), rect("b", -5, 50, 10, 10), rect("flat", 500, 500, 0, 5)]

        self.assertEqual(self.evaluate(f"unionRect({json.dumps(rects)})"), box(-5, 20, 40, 60))
        self.assertIsNone(self.evaluate("unionRect([])"))


class ResizeTests(_EngineCase):
    def test_free_right_edge_snaps_to_a_candidate_edge(self) -> None:
        result = self.resize([rect("a", 300, 0, 100, 50)], box(100, 100, 296, 180), minWidth=40, minHeight=40)

        self.assertEqual(result["rect"], box(100, 100, 300, 180))
        self.assertEqual((result["snappedX"], result["snappedY"]), (True, False))
        self.assertEqual(result["lines"], [line("x", 300, 0, 180)])

    def test_free_bottom_edge_snaps_to_a_candidate_edge(self) -> None:
        result = self.resize([rect("a", 0, 300, 100, 50)], box(200, 100, 280, 296))

        self.assertEqual(result["rect"], box(200, 100, 280, 300))
        self.assertEqual((result["snappedX"], result["snappedY"]), (False, True))
        self.assertEqual(result["lines"], [line("y", 300, 0, 280)])

    def test_top_left_handle_moves_its_own_edges(self) -> None:
        result = self.resize([rect("a", 0, 0, 100, 50)], box(103, 53, 200, 150), movingLeft=True, movingTop=True)

        self.assertEqual(result["rect"], box(100, 50, 200, 150))
        self.assertEqual(result["lines"], [line("x", 100, 0, 150), line("y", 50, 0, 200)])

    def test_resize_snaps_edges_not_centres(self) -> None:
        # Right edge 146 is 4 from the candidate centre 150 but 54 from its edges.
        result = self.resize([rect("a", 100, 300, 100, 50)], box(0, 0, 146, 80))

        self.assertEqual(result["rect"], box(0, 0, 146, 80))
        self.assertFalse(result["snappedX"])

    def test_a_snap_below_the_minimum_size_is_refused(self) -> None:
        narrow = self.resize([rect("a", 154, 0, 20, 50)], box(100, 100, 160, 180), minWidth=60, minHeight=40)
        short = self.resize([rect("b", 0, 134, 20, 50)], box(100, 100, 160, 140), minWidth=40, minHeight=40)

        self.assertEqual(narrow["rect"], box(100, 100, 160, 180))
        self.assertEqual((narrow["snappedX"], narrow["lines"]), (False, []))
        self.assertEqual(short["rect"], box(100, 100, 160, 140))
        self.assertEqual((short["snappedY"], short["lines"]), (False, []))

    def test_the_nearest_edge_that_keeps_the_minimum_wins(self) -> None:
        # 157 (-3) would leave width 57 < 58; 165 (+5) is within the threshold and keeps width 65.
        candidates = [rect("a", 120, 300, 37, 20), rect("b", 165, 400, 30, 20)]

        result = self.resize(candidates, box(100, 100, 160, 180), minWidth=58)

        self.assertEqual(result["rect"], box(100, 100, 165, 180))
        self.assertEqual((result["snappedX"], result["snappedY"]), (True, False))
        self.assertEqual(result["lines"], [line("x", 165, 100, 420)])

    def test_aspect_ratio_falls_back_to_the_other_axis(self) -> None:
        # X is closer (197, -3) but its width 197 breaks minWidth 199; Y (104, +4) gives 208 x 104.
        candidates = [rect("x", 197, 500, 20, 20), rect("y", 500, 104, 20, 20)]

        result = self.resize(candidates, box(0, 0, 200, 100), aspectRatio=2, minWidth=199)

        self.assertEqual(result["rect"], box(0, 0, 208, 104))
        self.assertEqual((result["snappedX"], result["snappedY"]), (False, True))
        self.assertEqual(result["lines"], [line("y", 104, 0, 520)])

    def test_aspect_ratio_driven_by_the_x_edge(self) -> None:
        result = self.resize([rect("a", 200, 300, 50, 50)], box(0, 0, 196, 98), aspectRatio=2)

        self.assertEqual(result["rect"], box(0, 0, 200, 100))
        self.assertEqual((result["snappedX"], result["snappedY"]), (True, False))
        self.assertEqual(result["lines"], [line("x", 200, 0, 350)])

    def test_aspect_ratio_driven_by_the_y_edge(self) -> None:
        # The Y edge is closer (2 vs 5); the derived right edge 200 misses the candidate edge 201.
        result = self.resize([rect("a", 300, 100, 50, 50), rect("b", 201, 400, 40, 40)], box(0, 0, 196, 98), aspectRatio=2)

        self.assertEqual(result["rect"], box(0, 0, 200, 100))
        self.assertEqual((result["snappedX"], result["snappedY"]), (False, True))
        self.assertEqual(result["lines"], [line("y", 100, 0, 350)])

    def test_aspect_ratio_keeps_the_fixed_corner(self) -> None:
        result = self.resize([rect("a", -50, 300, 50, 50)], box(4, 2, 200, 100), movingLeft=True, movingTop=True, aspectRatio=2)

        self.assertEqual(result["rect"], box(0, 0, 200, 100))
        self.assertEqual(result["lines"], [line("x", 0, 0, 350)])

    def test_aspect_ratio_snap_that_breaks_a_minimum_is_refused(self) -> None:
        result = self.resize([rect("a", 204, 300, 50, 50)], box(0, 0, 210, 105), aspectRatio=2, minHeight=104)

        self.assertEqual(result["rect"], box(0, 0, 210, 105))
        self.assertEqual((result["snappedX"], result["snappedY"], result["lines"]), (False, False, []))

    def test_horizontal_only_ignores_vertical_candidates(self) -> None:
        candidates = [rect("a", 200, 300, 50, 50), rect("b", 300, 100, 50, 50)]

        free = self.resize(candidates, box(0, 0, 196, 98), horizontalOnly=True)
        locked = self.resize(candidates, box(0, 0, 196, 98), horizontalOnly=True, aspectRatio=2)

        for result in (free, locked):
            self.assertEqual(result["rect"], box(0, 0, 200, 98))
            self.assertEqual((result["snappedX"], result["snappedY"]), (True, False))

    def test_empty_index_returns_the_input_rect(self) -> None:
        result = self.resize([], box(0, 0, 196, 98), aspectRatio=2)

        self.assertEqual(result, {"rect": box(0, 0, 196, 98), "snappedX": False, "snappedY": False, "lines": []})


class SmartGuidePerformanceTests(_EngineCase):
    """Timings take the best of three rounds so a transient load spike on the machine cannot fail them."""

    ROUNDS = 3
    GRID_MOVES = 40

    def build_layout(self, name: str, count: int, side: float, *, outliers: bool = False) -> None:
        """`count` random rects in a `side` square as `{name}Index`, with 1000 moving rects as `{name}Bases`.

        `outliers` adds one rect as tall and one as wide as the whole layout, like big Group backdrops.
        """
        rng = random.Random(20260925)
        candidates = [
            rect(f"n{index}", rng.uniform(0, side), rng.uniform(0, side), rng.uniform(80, 240), rng.uniform(40, 200))
            for index in range(count)
        ]
        if outliers:
            candidates += [rect("tall", -100.0, -100.0, 60.0, side + 400.0), rect("wide", -100.0, -300.0, side + 400.0, 60.0)]
        bases = []
        for _ in range(1000):
            left, top = rng.uniform(0, side), rng.uniform(0, side)
            bases.append(box(left, top, left + rng.uniform(80, 240), top + rng.uniform(40, 200)))
        self.evaluate(f"var {name}Index = buildIndex({json.dumps(candidates)}); var {name}Bases = {json.dumps(bases)}; true")

    def build_grid(self, name: str, columns: int, rows: int) -> None:
        """A `columns` x `rows` grid of jittered 200 x 100 rects as `{name}Index`, with GRID_MOVES moving rects
        900 wide and 80% as tall as the grid (a dragged column or Group) as `{name}Bases`."""
        rng = random.Random(3)
        candidates = [
            rect(f"n{column}_{row}", column * 240.0 + rng.uniform(-30, 30), row * 140.0 + rng.uniform(-30, 30), 200.0, 100.0)
            for column in range(columns)
            for row in range(rows)
        ]
        height = rows * 140.0
        bases = []
        for _ in range(self.GRID_MOVES):
            left, top = rng.uniform(0, columns * 240.0), rng.uniform(0, height * 0.2)
            bases.append(box(left, top, left + 900.0, top + height * 0.8))
        self.evaluate(f"var {name}Index = buildIndex({json.dumps(candidates)}); var {name}Bases = {json.dumps(bases)}; true")

    def build_comb(self, name: str, rows: int) -> None:
        """`rows` thin rows reaching far along X, then as many full-height slivers inside them that reach less, as
        `{name}Index`, with ten tall moving rects beside them as `{name}Bases`: a band of 2 * `rows` rects where
        every sliver visits every row's skyline segment without raising it."""
        candidates = [rect(f"row{index}", 0.0, index * 10.0, 5000.0, 6.0) for index in range(rows)]
        candidates += [rect(f"sliver{index}", 10.0 + index * 5.0, -5.0, 3.0, rows * 10.0 + 10.0) for index in range(rows)]
        bases = [box(6000.0 + shift, 0.0, 6100.0 + shift, rows * 10.0) for shift in range(10)]
        self.evaluate(f"var {name}Index = buildIndex({json.dumps(candidates)}); var {name}Bases = {json.dumps(bases)}; true")

    def time_layout(self, name: str) -> tuple[float, int]:
        """Seconds for the resolveMove calls over layout `name` (one per base), and the guides they reported."""
        loop = (
            f"(function() {{ var guides = 0; for (var i = 0; i < {name}Bases.length; ++i) {{"
            f" var r = resolveMove({name}Index, {name}Bases[i], 3.0, -2.0, {{threshold: 8, axisLock: '', spacing: true}});"
            " guides += r.lines.length + r.gaps.length; } return guides; })()"
        )
        started = time.perf_counter()
        guides = self.evaluate(loop)
        return time.perf_counter() - started, int(guides)

    def drop_layouts(self, *names: str) -> None:
        # The engine's garbage collector marks every live object, so no layout outlives its test.
        self.evaluate("".join(f"{name}Index = null; {name}Bases = null; " for name in names) + "true")
        self.engine.collectGarbage()

    def test_resolve_move_over_5000_candidates_stays_within_budget(self) -> None:
        # 5000 random rects hold far more candidates than a viewport does: alignment snaps on almost every
        # call and each band holds about 30 rects. This measured about 105 ms alone and up to 115 ms after
        # the scene suites in one process; a linear nearest-edge search measured 2.4 s. A single O(n) pass
        # per call (a linear band scan measured 0.45 s) is the scaling test's job.
        self.build_layout("budget", 5000, 40000.0)
        try:
            timings = [self.time_layout("budget") for _ in range(self.ROUNDS)]
        finally:
            self.drop_layouts("budget")
        elapsed = min(seconds for seconds, _guides in timings)

        print(f"\nsmart guides: 1000 resolveMove calls over 5000 candidates took {elapsed * 1000.0:.1f} ms")
        self.assertGreater(timings[0][1], 0)
        self.assertLess(elapsed, 0.5)

    def test_resolve_move_cost_does_not_grow_with_the_candidate_count(self) -> None:
        # Scaling both sides by 20 keeps the band populations and edge densities of 500 rects at 10000, so
        # only work that grows with n can separate the two timings. Rounds interleave over one heap. Each
        # layout also holds a rect as tall and one as wide as the whole layout: windowing every band query
        # by the largest extent let those two widen each query to nearly all rects (measured 5.1x here). A
        # linear band scan measured 5.0x and one O(n) pass per call 7.1x; the engine measured 1.1-1.2x.
        self.build_layout("small", 500, 20000.0, outliers=True)
        self.build_layout("large", 10000, 400000.0, outliers=True)
        try:
            rounds = [(self.time_layout("small"), self.time_layout("large")) for _ in range(self.ROUNDS)]
        finally:
            self.drop_layouts("small", "large")
        small = min(small_run[0] for small_run, _large_run in rounds)
        large = min(large_run[0] for _small_run, large_run in rounds)

        print(f"\nsmart guides: 1000 resolveMove calls took {small * 1000.0:.1f} ms over 500 candidates and "
              f"{large * 1000.0:.1f} ms over 10000 at the same band density ({large / small:.2f}x)")
        self.assertGreater(min(rounds[0][0][1], rounds[0][1][1]), 0)
        self.assertLess(large / small, 2.5)

    def test_a_tall_moving_rect_beside_many_rows_costs_no_more_than_beside_few(self) -> None:
        # A moving rect 80% as tall as a grid sweeps every rect in the rows it spans. The same 1600 rects as
        # 100 columns x 16 rows or as 16 columns x 100 rows give it bands of about 1300 rects, but beside
        # the tall grid the sweep's skyline holds about six times the segments. Rewriting the whole skyline
        # for each band rect made the tall grid 3.4x slower (19 ms a call), and walking the skyline to each
        # span's first segment 2.0x; finding that segment in the marks measured 0.9x (1.8 ms a call), like
        # the pre-sweep engine (1.2x, 1.6 ms). Those bands lie far past SPACING_BAND_LIMIT, so the limit is
        # lifted here to time the sweep itself.
        saved = self.evaluate("SPACING_BAND_LIMIT")
        self.evaluate("SPACING_BAND_LIMIT = Infinity; true")
        try:
            self.build_grid("wide", 100, 16)
            self.build_grid("tall", 16, 100)
            rounds = [(self.time_layout("wide"), self.time_layout("tall")) for _ in range(self.ROUNDS)]
        finally:
            self.drop_layouts("wide", "tall")
            self.evaluate(f"SPACING_BAND_LIMIT = {saved}; true")
        wide = min(wide_run[0] for wide_run, _tall_run in rounds)
        tall = min(tall_run[0] for _wide_run, tall_run in rounds)
        per_call_ms = tall / self.GRID_MOVES * 1000.0

        print(f"\nsmart guides: a tall moving rect took {wide / self.GRID_MOVES * 1000.0:.2f} ms a call beside "
              f"100 x 16 rects and {per_call_ms:.2f} ms beside 16 x 100 ({tall / wide:.2f}x)")
        self.assertGreater(min(rounds[0][0][1], rounds[0][1][1]), 0)
        self.assertLess(tall / wide, 1.5)
        self.assertLess(per_call_ms, 8.0)

    def test_the_band_limit_bounds_the_worst_band(self) -> None:
        # In a comb every sliver visits every row's segment without raising it, so the sweep grows with the
        # square of the band. At SPACING_BAND_LIMIT (128 rows and 128 slivers) this measured about 5 ms a call.
        # With 800 of each it measured 200 ms before the limit; past the limit the band gets no equal spacing
        # and the call measured 0.5 ms, less than at the limit.
        self.build_comb("atLimit", 128)
        self.build_comb("pastLimit", 800)
        try:
            bands = self.evaluate("[bandAround(atLimitIndex, AXIS_X, atLimitBases[0], 0, {}),"
                                  " bandAround(pastLimitIndex, AXIS_X, pastLimitBases[0], 0, {})]")
            rounds = [(self.time_layout("atLimit"), self.time_layout("pastLimit")) for _ in range(self.ROUNDS)]
        finally:
            self.drop_layouts("atLimit", "pastLimit")
        at_limit_ms = min(at_run[0] for at_run, _past_run in rounds) / 10 * 1000.0
        past_limit_ms = min(past_run[0] for _at_run, past_run in rounds) / 10 * 1000.0

        print(f"\nsmart guides: a comb band took {at_limit_ms:.2f} ms a call at the limit (256 rects) and "
              f"{past_limit_ms:.2f} ms past it (1600 rects)")
        self.assertEqual(bands, [256, 1600])
        self.assertLess(at_limit_ms, 20.0)
        self.assertLess(past_limit_ms, at_limit_ms)


if __name__ == "__main__":
    unittest.main()
