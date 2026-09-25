# Purpose: Offscreen, shell-free tests for the scene Tidy command (auto-layout / clean up in place) incl. groups, locks, push, membership guard and undo.
# Map: feature_routes/graph_actions_and_context_menus
# Tests: tests/test_graph_scene_tidy_layout.py
from __future__ import annotations

import unittest
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.graph.transform_tidy_layout import DEFAULT_TIDY_COLUMN_GAP
from tests.automation.harness import build_context, call

START = "passive.flowchart.start"
PROCESS = "passive.flowchart.process"
DECISION = "passive.flowchart.decision"
NOTE = "passive.annotation.sticky_note"


class _GraphicsPreferences(QObject):
    graphics_preferences_changed = pyqtSignal()

    def __init__(self, expand_collision_avoidance: dict[str, Any]) -> None:
        super().__init__()
        self.graphics_expand_collision_avoidance = expand_collision_avoidance


class _TidySceneCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene
        self._preferences: _GraphicsPreferences | None = None

    def add(self, type_id: str, x: float, y: float) -> str:
        return self.scene.add_node_from_type(type_id, float(x), float(y))

    def wire(self, source: str, source_port: str, target: str, target_port: str) -> str:
        return self.scene.add_edge(source, source_port, target, target_port)

    def node(self, node_id: str):
        return self.context.active_workspace().nodes[node_id]

    def position(self, node_id: str) -> tuple[float, float]:
        node = self.node(node_id)
        return (float(node.x), float(node.y))

    def bounds(self, node_id: str) -> tuple[float, float, float, float]:
        rect = self.scene.node_bounds(node_id)
        return (rect.x(), rect.y(), rect.width(), rect.height())

    def edge_row(self, edge_id: str) -> dict[str, Any]:
        return next(row for row in self.scene.edges_model if row["edge_id"] == edge_id)

    def backdrop_row(self, backdrop_id: str) -> dict[str, Any]:
        return next(row for row in self.scene.backdrop_nodes_model if row["node_id"] == backdrop_id)

    def undo_depth(self) -> int:
        return self.context.runtime_history.undo_depth(self.context.workspace_id())

    def disable_push(self) -> None:
        self._preferences = _GraphicsPreferences({"enabled": False})
        self.scene.bind_graphics_preferences_source(self._preferences)

    def tidy_one_undo(self, node_ids: list[str] | None, **options: Any) -> dict[str, Any]:
        before = self.undo_depth()
        outcome = self.scene.tidy_layout(node_ids, **options)
        self.assertIsNotNone(outcome)
        self.assertTrue(outcome["changed"])
        self.assertEqual(self.undo_depth(), before + 1, "a tidy must record exactly one undo entry")
        return outcome

    def tidy_no_undo(self, node_ids: list[str] | None, **options: Any) -> dict[str, Any] | None:
        before = self.undo_depth()
        outcome = self.scene.tidy_layout(node_ids, **options)
        self.assertEqual(self.undo_depth(), before, "a tidy that changes nothing must not record undo")
        return outcome

    def assert_contains(self, outer_id: str, inner_id: str) -> None:
        ox, oy, ow, oh = self.bounds(outer_id)
        ix, iy, iw, ih = self.bounds(inner_id)
        self.assertTrue(
            ox <= ix and oy <= iy and ox + ow >= ix + iw and oy + oh >= iy + ih,
            f"{inner_id} {self.bounds(inner_id)} must stay inside {outer_id} {self.bounds(outer_id)}",
        )


class TidyFlowchartTests(_TidySceneCase):
    def _flowchart(self) -> tuple[dict[str, str], dict[str, str]]:
        nodes = {
            "start": self.add(START, 0, 40),
            "step": self.add(PROCESS, 300, 0),
            "check": self.add(DECISION, 620, 90),
            "done": self.add(PROCESS, 950, 30),
            "fix": self.add(PROCESS, 640, 380),
        }
        edges = {
            "start_step": self.wire(nodes["start"], "right", nodes["step"], "left"),
            "step_check": self.wire(nodes["step"], "right", nodes["check"], "left"),
            "check_done": self.wire(nodes["check"], "right", nodes["done"], "left"),
            "check_fix": self.wire(nodes["check"], "bottom", nodes["fix"], "top"),
            "loop": self.wire(nodes["fix"], "left", nodes["step"], "bottom"),
        }
        return nodes, edges

    def test_left_to_right_flowchart_gets_straight_rows_a_straight_branch_and_one_undo_step(self) -> None:
        nodes, edges = self._flowchart()

        outcome = self.tidy_one_undo(list(nodes.values()))

        self.assertEqual(outcome["mode"], "auto_layout")
        self.assertEqual(outcome["direction"], "left_to_right")
        self.assertEqual(outcome["loop_edge_ids"], [edges["loop"]])
        self.assertEqual(outcome["arranged_node_ids"], sorted(nodes.values()))
        self.assertEqual(outcome["moved_node_ids"], sorted(nodes.values()))
        self.assertEqual(outcome["skipped_node_ids"], [])
        self.assertEqual(outcome["membership_conflict_node_ids"], [])
        for key in ("start_step", "step_check", "check_done"):
            row = self.edge_row(edges[key])
            self.assertLessEqual(abs(float(row["sy"]) - float(row["ty"])), 1.0, key)
        branch = self.edge_row(edges["check_fix"])
        self.assertLessEqual(abs(float(branch["sx"]) - float(branch["tx"])), 1.0)
        self.assertEqual(min(self.position(node_id)[0] for node_id in nodes.values()), 0.0)
        self.assertEqual(min(self.position(node_id)[1] for node_id in nodes.values()), 0.0)

        repeat = self.tidy_no_undo(list(nodes.values()))
        self.assertIsNotNone(repeat)
        self.assertFalse(repeat["changed"])
        self.assertEqual(repeat["moved_node_ids"], [])

    def test_explicit_top_to_bottom_stacks_a_left_to_right_chain(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 320, 60)
        third = self.add(PROCESS, 640, 20)
        self.wire(first, "right", second, "left")
        self.wire(second, "right", third, "left")

        outcome = self.tidy_one_undo([first, second, third], direction="top_to_bottom")

        self.assertEqual(outcome["direction"], "top_to_bottom")
        self.assertEqual({self.position(node_id)[0] for node_id in (first, second, third)}, {0.0})
        tops = [self.position(node_id)[1] for node_id in (first, second, third)]
        self.assertEqual(tops, sorted(tops))

    def test_whole_graph_in_place_clean_up_snaps_a_jittered_grid(self) -> None:
        grid = [
            [self.add(PROCESS, 0, 5), self.add(PROCESS, 320, -10), self.add(PROCESS, 640, 12)],
            [self.add(PROCESS, 10, 300), self.add(PROCESS, 330, 285), self.add(PROCESS, 650, 310)],
        ]

        outcome = self.tidy_one_undo(None, mode="in_place")

        self.assertEqual(outcome["mode"], "in_place")
        self.assertEqual(outcome["direction"], "")
        for row in grid:
            self.assertEqual(len({self.position(node_id)[1] for node_id in row}), 1)
            lefts = [self.position(node_id)[0] for node_id in row]
            self.assertEqual(lefts, sorted(lefts))

    def test_unknown_mode_or_direction_raises(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 300, 0)
        with self.assertRaises(ValueError):
            self.scene.tidy_layout([first, second], mode="shuffle")
        with self.assertRaises(ValueError):
            self.scene.tidy_layout([first, second], direction="diagonal")

    def test_fewer_than_two_arrangeable_nodes_returns_none(self) -> None:
        lone = self.add(PROCESS, 0, 0)
        note = self.add(NOTE, 400, 0)

        self.assertIsNone(self.tidy_no_undo([lone]))
        self.assertIsNone(self.tidy_no_undo([lone, note]))
        self.assertIsNone(self.tidy_no_undo([]))


class TidyGroupTests(_TidySceneCase):
    def test_group_members_are_laid_out_inside_their_refitted_backdrop_and_undo_restores_it(self) -> None:
        start = self.add(START, 0, 40)
        first = self.add(PROCESS, 400, 0)
        second = self.add(PROCESS, 720, 150)
        self.wire(start, "right", first, "left")
        self.wire(first, "right", second, "left")
        group = self.scene.wrap_node_ids_in_group_backdrop([first, second])
        members_before = self.backdrop_row(group)["member_node_ids"]
        group_before = self.bounds(group)
        positions_before = {node_id: self.position(node_id) for node_id in (start, first, second, group)}

        outcome = self.tidy_one_undo([start, group])

        self.assertEqual(outcome["resized_group_ids"], [group])
        self.assertEqual(sorted(self.backdrop_row(group)["member_node_ids"]), sorted(members_before))
        self.assertNotEqual(self.bounds(group), group_before)
        self.assert_contains(group, first)
        self.assert_contains(group, second)
        self.assertEqual(self.position(first)[1], self.position(second)[1])

        workspace = self.context.active_workspace()
        self.assertIsNotNone(self.context.runtime_history.undo_workspace(workspace.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(workspace.workspace_id)
        for node_id, position in positions_before.items():
            self.assertEqual(self.position(node_id), position)
        self.assertEqual(self.bounds(group), group_before)

    def test_collapsed_group_moves_rigidly_with_its_hidden_members(self) -> None:
        outside = self.add(PROCESS, 0, 0)
        first = self.add(PROCESS, 500, 400)
        second = self.add(PROCESS, 820, 430)
        self.wire(first, "right", second, "left")
        self.wire(outside, "right", first, "left")
        group = self.scene.wrap_node_ids_in_group_backdrop([first, second])
        self.scene.set_node_collapsed(group, True)
        group_before = self.position(group)
        members_before = {node_id: self.position(node_id) for node_id in (first, second)}

        outcome = self.tidy_one_undo([outside, group])

        dx = self.position(group)[0] - group_before[0]
        dy = self.position(group)[1] - group_before[1]
        self.assertNotEqual((dx, dy), (0.0, 0.0))
        for node_id, (x, y) in members_before.items():
            self.assertEqual(self.position(node_id), (x + dx, y + dy))
        self.assertIn(first, outcome["moved_node_ids"])
        self.assertEqual(outcome["resized_group_ids"], [])
        self.assertEqual(sorted(self.backdrop_row(group)["member_node_ids"]), sorted([first, second]))

    def test_wires_across_group_boundaries_run_straight_and_a_second_tidy_changes_nothing(self) -> None:
        start = self.add(START, 0, 300)
        first = self.add(PROCESS, 400, 120)
        second = self.add(PROCESS, 720, 260)
        middle = self.add(PROCESS, 1200, 500)
        hidden_first = self.add(PROCESS, 1700, 100)
        hidden_second = self.add(PROCESS, 2000, 160)
        crossing = [
            self.wire(start, "right", first, "left"),
            self.wire(second, "right", middle, "left"),
            self.wire(middle, "right", hidden_first, "left"),
        ]
        self.wire(first, "right", second, "left")
        self.wire(hidden_first, "right", hidden_second, "left")
        self.scene.wrap_node_ids_in_group_backdrop([first, second])
        collapsed = self.scene.wrap_node_ids_in_group_backdrop([hidden_first, hidden_second])
        self.scene.set_node_collapsed(collapsed, True)

        self.tidy_one_undo(None)

        for edge_id in crossing:
            row = self.edge_row(edge_id)
            self.assertLessEqual(abs(float(row["sy"]) - float(row["ty"])), 1.0, edge_id)
        repeat = self.tidy_no_undo(None)
        self.assertIsNotNone(repeat)
        self.assertFalse(repeat["changed"])

    def _collapsed_group_between(self, start: str, end: str, x: float, y: float) -> str:
        first = self.add(PROCESS, x, y)
        second = self.add(PROCESS, x + 320, y + 40)
        self.wire(first, "right", second, "left")
        self.wire(start, "right", first, "left")
        self.wire(second, "right", end, "left")
        group = self.scene.wrap_node_ids_in_group_backdrop([first, second])
        self.scene.set_node_collapsed(group, True)
        return group

    def assert_pill_gap(self, group: str, next_node: str) -> None:
        pill_x, _pill_y, pill_width, _pill_height = self.bounds(group)
        self.assertAlmostEqual(self.position(next_node)[0] - (pill_x + pill_width), DEFAULT_TIDY_COLUMN_GAP, delta=0.5)

    def test_collapsed_group_is_laid_out_at_its_pill_size_at_every_level(self) -> None:
        # Top level: start -> collapsed Group -> end.
        start = self.add(START, 0, 40)
        end = self.add(PROCESS, 1700, 0)
        top_group = self._collapsed_group_between(start, end, 500, 300)
        # Inside a Group: the same chain, wrapped in a parent Group.
        inner_start = self.add(START, 0, 1200)
        inner_end = self.add(PROCESS, 1700, 1200)
        nested_group = self._collapsed_group_between(inner_start, inner_end, 500, 1400)
        parent = self.scene.wrap_node_ids_in_group_backdrop([inner_start, nested_group, inner_end])
        self.assertEqual(self.backdrop_row(nested_group)["owner_backdrop_id"], parent)

        outcome = self.tidy_one_undo(None)

        self.assertEqual(outcome["membership_conflict_node_ids"], [])
        self.assert_pill_gap(top_group, end)
        self.assert_pill_gap(nested_group, inner_end)
        # The parent is fitted around the laid-out members (pill included), not around the hidden area.
        parent_x, parent_y, parent_width, parent_height = self.bounds(parent)
        members = [self.bounds(node_id) for node_id in (inner_start, nested_group, inner_end)]
        self.assertAlmostEqual(parent_x + parent_width, max(x + w for x, _y, w, _h in members) + 32.0, delta=0.5)
        self.assertAlmostEqual(parent_x, min(x for x, _y, _w, _h in members) - 32.0, delta=0.5)
        self.assertEqual(self.backdrop_row(nested_group)["owner_backdrop_id"], parent)
        self.assertLess(parent_width, 1200.0)

        repeat = self.tidy_no_undo(None)
        self.assertIsNotNone(repeat)
        self.assertFalse(repeat["changed"])

    def test_nodes_over_a_hidden_area_are_not_a_membership_conflict(self) -> None:
        member = self.add(PROCESS, 40, 120)
        group = self.scene.wrap_node_ids_in_group_backdrop([member])
        self.scene.set_node_geometry(group, 0.0, 0.0, 900.0, 600.0)
        self.scene.set_node_collapsed(group, True)
        first = self.add(PROCESS, 200, 250)
        second = self.add(PROCESS, 520, 400)
        self.wire(first, "right", second, "left")

        outcome = self.tidy_one_undo([first, second])

        self.assertEqual(outcome["membership_conflict_node_ids"], [])
        self.assertEqual(sorted(outcome["arranged_node_ids"]), sorted([first, second]))
        for node_id in (first, second):
            row = next(row for row in self.scene.nodes_model if row["node_id"] == node_id)
            self.assertEqual(row["owner_backdrop_id"], "")
        self.assertEqual(self.context.active_workspace().nodes[group].held_member_ids, (member,))

    def test_partial_group_selection_grows_the_owner_chain(self) -> None:
        first = self.add(PROCESS, 100, 100)
        second = self.add(PROCESS, 110, 260)
        third = self.add(PROCESS, 90, 420)
        self.wire(first, "right", second, "left")
        self.wire(second, "right", third, "left")
        inner = self.scene.wrap_node_ids_in_group_backdrop([first, second, third])
        outer = self.scene.wrap_node_ids_in_group_backdrop([inner])
        self.assertEqual(self.backdrop_row(outer)["member_backdrop_ids"], [inner])
        inner_before = self.bounds(inner)
        outer_before = self.bounds(outer)

        outcome = self.tidy_one_undo([first, second, third])

        self.assertEqual(sorted(outcome["resized_group_ids"]), sorted([inner, outer]))
        self.assertGreater(self.bounds(inner)[2], inner_before[2])
        self.assertGreater(self.bounds(outer)[2], outer_before[2])
        for node_id in (first, second, third):
            self.assert_contains(inner, node_id)
        self.assert_contains(outer, inner)
        self.assertEqual(sorted(self.backdrop_row(inner)["member_node_ids"]), sorted([first, second, third]))
        self.assertEqual(self.backdrop_row(outer)["member_backdrop_ids"], [inner])

    def test_nodes_that_would_enter_an_unselected_group_abort_the_tidy(self) -> None:
        self.disable_push()
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 0, 400)
        self.wire(first, "right", second, "left")
        occupant = self.add(PROCESS, 500, 150)
        group = self.scene.wrap_node_ids_in_group_backdrop([occupant])
        self.scene.set_node_geometry(group, 280.0, -60.0, 700.0, 400.0)
        positions_before = {node_id: self.position(node_id) for node_id in (first, second)}

        outcome = self.tidy_no_undo([first, second])

        self.assertIsNotNone(outcome)
        self.assertFalse(outcome["changed"])
        self.assertIn(second, outcome["membership_conflict_node_ids"])
        self.assertEqual(outcome["moved_node_ids"], [])
        for node_id, position in positions_before.items():
            self.assertEqual(self.position(node_id), position)


def _overlaps(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    return (
        first[0] < second[0] + second[2]
        and first[0] + first[2] > second[0]
        and first[1] < second[1] + second[3]
        and first[1] + first[3] > second[1]
    )


class TidyObstacleTests(_TidySceneCase):
    def test_top_level_block_steps_off_a_group_that_grew_around_selected_members(self) -> None:
        first_member = self.add(PROCESS, 0, 300)
        second_member = self.add(PROCESS, 0, 450)
        self.wire(first_member, "right", second_member, "left")
        group = self.scene.wrap_node_ids_in_group_backdrop([first_member, second_member])
        first_top = self.add(PROCESS, 400, 300)
        second_top = self.add(PROCESS, 400, 450)
        self.wire(first_top, "right", second_top, "left")

        outcome = self.tidy_one_undo([first_member, second_member, first_top, second_top])

        self.assertIn(group, outcome["resized_group_ids"])
        for node_id in (first_top, second_top):
            self.assertFalse(_overlaps(self.bounds(group), self.bounds(node_id)), node_id)
        self.assertEqual(sorted(self.backdrop_row(group)["member_node_ids"]), sorted([first_member, second_member]))

    def test_tidied_nodes_do_not_land_on_a_locked_node_or_a_group_holding_one(self) -> None:
        chain = [self.add(PROCESS, 0, y) for y in (0, 200, 400, 600)]
        for source, target in zip(chain, chain[1:]):
            self.wire(source, "right", target, "left")
        locked = self.add(PROCESS, 330, 20)
        self.scene.set_node_locked(locked, True)
        member = self.add(PROCESS, 1000, 150)
        locked_member = self.add(PROCESS, 1000, 300)
        fixed_group = self.scene.wrap_node_ids_in_group_backdrop([member, locked_member])
        self.scene.set_node_locked(locked_member, True)

        self.tidy_one_undo(chain)

        for node_id in chain:
            self.assertFalse(_overlaps(self.bounds(node_id), self.bounds(locked)), node_id)
            self.assertFalse(_overlaps(self.bounds(node_id), self.bounds(fixed_group)), node_id)

    def test_push_leaves_a_note_in_an_empty_cell_alone(self) -> None:
        start = self.add(START, 0, 0)
        step = self.add(PROCESS, 300, 0)
        check = self.add(DECISION, 620, -20)
        done = self.add(PROCESS, 960, 0)
        fix = self.add(PROCESS, 626, 250)
        self.wire(start, "right", step, "left")
        self.wire(step, "right", check, "left")
        self.wire(check, "right", done, "left")
        self.wire(check, "bottom", fix, "top")
        note = self.add(NOTE, 960, 200)
        before = self.bounds(note)

        outcome = self.tidy_one_undo(None)

        self.assertEqual(self.bounds(note), before)
        self.assertNotIn(note, outcome["pushed_node_ids"])
        self.assertNotIn(note, outcome["moved_node_ids"])

    def test_a_pushed_note_clears_both_the_new_row_and_a_grown_group(self) -> None:
        first_top = self.add(PROCESS, 0, 0)
        second_top = self.add(PROCESS, 0, 150)
        self.wire(first_top, "right", second_top, "left")
        first_member = self.add(PROCESS, 0, 300)
        second_member = self.add(PROCESS, 0, 450)
        self.wire(first_member, "right", second_member, "left")
        group = self.scene.wrap_node_ids_in_group_backdrop([first_member, second_member])
        note = self.add(NOTE, 300, 120)

        outcome = self.tidy_one_undo([first_top, second_top, first_member, second_member])

        self.assertEqual(outcome["pushed_node_ids"], [note])
        for node_id in (first_top, second_top, group):
            self.assertFalse(_overlaps(self.bounds(note), self.bounds(node_id)), node_id)

    def test_an_unselected_group_does_not_grow_when_its_selected_member_stays(self) -> None:
        self.disable_push()
        member = self.add(PROCESS, 1000, 100)
        other_member = self.add(PROCESS, 1000, 300)
        group = self.scene.wrap_node_ids_in_group_backdrop([member, other_member])
        self.scene.move_node(other_member, 1020.0, 300.0)
        group_before = self.bounds(group)
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 30, 200)
        self.wire(first, "right", second, "left")

        outcome = self.tidy_one_undo([first, second, member])

        self.assertEqual(self.bounds(group), group_before)
        self.assertEqual(outcome["resized_group_ids"], [])
        self.assertNotIn(member, outcome["skipped_node_ids"])


class TidyLockTests(_TidySceneCase):
    def test_locked_node_is_skipped_and_left_in_place(self) -> None:
        first = self.add(PROCESS, 0, 0)
        locked = self.add(PROCESS, 300, 200)
        third = self.add(PROCESS, 600, 60)
        fourth = self.add(PROCESS, 900, 150)
        self.wire(first, "right", third, "left")
        self.wire(third, "right", fourth, "left")
        self.scene.set_node_locked(locked, True)
        locked_before = self.position(locked)

        outcome = self.tidy_one_undo([first, locked, third, fourth])

        self.assertEqual(self.position(locked), locked_before)
        self.assertIn(locked, outcome["skipped_node_ids"])
        self.assertNotIn(locked, outcome["arranged_node_ids"])

    def test_group_holding_a_locked_member_is_a_fixed_obstacle(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 320, 200)
        self.wire(first, "right", second, "left")
        member = self.add(PROCESS, 900, 500)
        locked_member = self.add(PROCESS, 1200, 560)
        group = self.scene.wrap_node_ids_in_group_backdrop([member, locked_member])
        self.scene.set_node_locked(locked_member, True)
        group_before = self.bounds(group)
        member_before = self.position(member)

        outcome = self.tidy_one_undo([first, second, group])

        self.assertEqual(self.bounds(group), group_before)
        self.assertEqual(self.position(member), member_before)
        self.assertTrue({group, member, locked_member} <= set(outcome["skipped_node_ids"]))


class TidyNeighbourPushTests(_TidySceneCase):
    def _stack_and_neighbour(self) -> tuple[list[str], str]:
        chain = [self.add(PROCESS, 0, 0), self.add(PROCESS, 0, 200), self.add(PROCESS, 0, 400)]
        self.wire(chain[0], "right", chain[1], "left")
        self.wire(chain[1], "right", chain[2], "left")
        neighbour = self.add(PROCESS, 600, 20)
        return chain, neighbour

    def test_neighbour_in_the_way_is_pushed_when_collision_avoidance_is_on(self) -> None:
        chain, neighbour = self._stack_and_neighbour()
        before = self.position(neighbour)

        outcome = self.tidy_one_undo(chain)

        self.assertEqual(outcome["pushed_node_ids"], [neighbour])
        self.assertNotEqual(self.position(neighbour), before)
        nx, ny, nw, nh = self.bounds(neighbour)
        for node_id in chain:
            x, y, w, h = self.bounds(node_id)
            self.assertFalse(nx < x + w and nx + nw > x and ny < y + h and ny + nh > y, node_id)

    def test_neighbour_stays_when_collision_avoidance_is_off(self) -> None:
        self.disable_push()
        chain, neighbour = self._stack_and_neighbour()
        before = self.position(neighbour)

        outcome = self.tidy_one_undo(chain)

        self.assertEqual(outcome["pushed_node_ids"], [])
        self.assertEqual(self.position(neighbour), before)


class TidyScopeTests(_TidySceneCase):
    def test_whole_scope_tidy_inside_a_subnode_touches_only_that_scope(self) -> None:
        inner_first = self.add(PROCESS, 0, 600)
        inner_second = self.add(PROCESS, 40, 800)
        self.wire(inner_first, "right", inner_second, "left")
        shell = call(self.context, "subnode.create", {"node_ids": [inner_first, inner_second]})["shell_node_id"]
        root_first = self.add(PROCESS, 0, 0)
        root_second = self.add(PROCESS, 30, 260)
        self.wire(root_first, "right", root_second, "left")
        root_before = {node_id: self.position(node_id) for node_id in (root_first, root_second, shell)}
        self.assertTrue(self.scene.open_subnode_scope(shell))

        outcome = self.tidy_one_undo(None)

        self.assertEqual(sorted(outcome["arranged_node_ids"]), sorted([inner_first, inner_second]))
        self.assertEqual(self.position(inner_first)[1], self.position(inner_second)[1])
        for node_id, position in root_before.items():
            self.assertEqual(self.position(node_id), position)


if __name__ == "__main__":
    unittest.main()
