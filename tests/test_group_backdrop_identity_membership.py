# Purpose: Offscreen scene tests for identity membership of collapsed Groups: freeze/clear lists, corner containment, level-by-level make room on expand, locks, guard, strays, Peek, carry, marquee, delete, subnode, fill-in, removal publication, membership kept by targeted payload updates, and wrapping at the drawn size.
# Map: feature_routes/group_backdrops_peek_membership
# Tests: tests/test_group_backdrop_identity_membership.py
from __future__ import annotations

import copy
import unittest
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui.graph_interactions import GraphInteractions
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_scene_mutation.node_creation_batch import NodeCreationRequest
from tests.automation.harness import build_context

GROUP = "passive.annotation.group_backdrop"
PROCESS = "passive.flowchart.process"
LOGGER = "core.logger"
PLOT = "plot.signal"
_NEAREST = {"enabled": True, "strategy": "nearest", "strategy_revision": 2}


class _GraphicsPreferences(QObject):
    graphics_preferences_changed = pyqtSignal()

    def __init__(self, expand_collision_avoidance: dict[str, Any]) -> None:
        super().__init__()
        self.graphics_expand_collision_avoidance = expand_collision_avoidance


class _IdentityCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene
        self._preferences: _GraphicsPreferences | None = None

    # ------------------------------------------------------------------ building
    def add(self, type_id: str, x: float, y: float, title: str = "") -> str:
        node_id = self.scene.add_node_from_type(type_id, float(x), float(y))
        if title:
            self.scene.set_node_title(node_id, title)
        return node_id

    def group(self, x: float, y: float, width: float, height: float, title: str = "") -> str:
        group_id = self.add(GROUP, x, y, title)
        self.scene.set_node_geometry(group_id, float(x), float(y), float(width), float(height))
        return group_id

    def prefs(self, settings: dict[str, Any]) -> None:
        self._preferences = _GraphicsPreferences(settings)
        self.scene.bind_graphics_preferences_source(self._preferences)

    # ------------------------------------------------------------------ reading
    def node(self, node_id: str) -> NodeInstance:
        return self.context.active_workspace().nodes[node_id]

    def position(self, node_id: str) -> tuple[float, float]:
        node = self.node(node_id)
        return (float(node.x), float(node.y))

    def group_rect(self, group_id: str) -> tuple[float, float, float, float]:
        node = self.node(group_id)
        return (float(node.x), float(node.y), float(node.custom_width), float(node.custom_height))

    def drawn(self) -> set[str]:
        return {str(row["node_id"]) for row in (*self.scene.nodes_model, *self.scene.backdrop_nodes_model)}

    def row(self, node_id: str) -> dict[str, Any]:
        return next(row for row in (*self.scene.nodes_model, *self.scene.backdrop_nodes_model) if row["node_id"] == node_id)

    def owner(self, node_id: str) -> str:
        return str(self.row(node_id)["owner_backdrop_id"])

    @contextmanager
    def counting_full_rebuilds(self) -> Iterator[list[str]]:
        rebuilds: list[str] = []
        scene_context = self.scene._scene_context  # noqa: SLF001
        original_rebuild_models = scene_context.rebuild_models

        def _counting_rebuild_models() -> None:
            rebuilds.append("rebuild")
            original_rebuild_models()

        scene_context.rebuild_models = _counting_rebuild_models
        try:
            yield rebuilds
        finally:
            scene_context.rebuild_models = original_rebuild_models

    def assert_group_contains_drawn(self, group_id: str, node_id: str) -> None:
        drawn = self.scene.node_bounds(node_id)
        x, y, width, height = self.group_rect(group_id)
        self.assertTrue(
            x < drawn.x() and drawn.x() + drawn.width() < x + width
            and y < drawn.y() and drawn.y() + drawn.height() < y + height,
            (drawn, (x, y, width, height)),
        )

    def undo_depth(self) -> int:
        return self.context.runtime_history.undo_depth(self.context.workspace_id())

    def undo(self) -> None:
        workspace = self.context.active_workspace()
        self.assertIsNotNone(self.context.runtime_history.undo_workspace(workspace.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(workspace.workspace_id)

    def redo(self) -> None:
        workspace = self.context.active_workspace()
        self.assertIsNotNone(self.context.runtime_history.redo_workspace(workspace.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(workspace.workspace_id)

    def collapse(self, node_id: str) -> None:
        self.assertTrue(self.scene.set_node_collapsed(node_id, True))

    def expand(self, node_id: str) -> None:
        if not self.scene.set_node_collapsed(node_id, False):
            self.fail(f"expand refused: {self.scene.take_expand_refusal_reason()}")

    def snapshot(self) -> dict[str, tuple[Any, ...]]:
        return {
            node_id: (node.x, node.y, node.custom_width, node.custom_height, node.collapsed, node.held_member_ids,
                      node.expanded_settings_group_ids)
            for node_id, node in self.context.active_workspace().nodes.items()
        }


class CollapseFreezeTests(_IdentityCase):
    def test_collapse_freezes_the_subtree_for_the_group_and_every_expanded_group_inside_as_one_undo_step(self) -> None:
        outer = self.group(0, 0, 1000, 700, "Outer")
        inner = self.group(60, 120, 400, 300, "Inner")
        first = self.add(PROCESS, 100, 200)
        second = self.add(PROCESS, 600, 200)
        depth = self.undo_depth()

        self.collapse(outer)

        self.assertEqual(self.undo_depth(), depth + 1)
        self.assertEqual(self.node(outer).held_member_ids, tuple(sorted([inner, first, second])))
        self.assertEqual(self.node(inner).held_member_ids, (first,))
        self.assertEqual(self.drawn(), {outer})

        self.undo()
        self.assertFalse(self.node(outer).collapsed)
        self.assertIsNone(self.node(outer).held_member_ids)
        self.assertIsNone(self.node(inner).held_member_ids)
        self.assertEqual(self.drawn(), {outer, inner, first, second})

        self.redo()
        self.assertEqual(self.node(outer).held_member_ids, tuple(sorted([inner, first, second])))
        self.assertEqual(self.node(inner).held_member_ids, (first,))
        self.assertEqual(self.drawn(), {outer})

    def test_nodes_over_a_hidden_area_stay_drawn_and_ownerless(self) -> None:
        parent = self.group(0, 0, 1600, 1000, "Parent")
        nested = self.group(100, 150, 600, 400, "Nested")
        self.add(PROCESS, 200, 300)
        top = self.group(2000, 0, 600, 400, "Top")
        self.add(PROCESS, 2100, 200)
        self.collapse(nested)
        self.collapse(top)

        inside_parent = self.add(PROCESS, 300, 350)
        at_top_level = self.add(PROCESS, 2100, 150)

        self.assertTrue({inside_parent, at_top_level} <= self.drawn())
        self.assertEqual(self.owner(inside_parent), parent)
        self.assertEqual(self.owner(at_top_level), "")
        self.assertNotIn(inside_parent, self.node(nested).held_member_ids)
        self.assertNotIn(at_top_level, self.node(top).held_member_ids)

    def test_collapsed_group_belongs_to_its_parent_by_its_pill_corner(self) -> None:
        simulation = self.group(0, 0, 900, 500, "Simulation")
        meshing = self.group(100, 120, 700, 300, "Meshing")
        self.add(PROCESS, 160, 250)
        self.collapse(meshing)
        # Meshing's expanded area now sticks out of Simulation; its pill's top-left corner does not.
        self.scene.set_node_geometry(simulation, 0.0, 0.0, 400.0, 300.0)

        self.assertEqual(self.owner(meshing), simulation)

        self.scene.set_node_title(meshing, "M" * 120)
        pill = self.scene.node_bounds(meshing)
        self.assertGreater(pill.width(), 400.0)
        self.assertEqual(self.owner(meshing), simulation)


class ExpandMakeRoomTests(_IdentityCase):
    def _row_in_a_parent(self) -> dict[str, str]:
        parent = self.group(0, 0, 560, 400, "Parent")
        meshing = self.group(40, 120, 500, 300, "Meshing")
        member = self.add(PROCESS, 80, 200)
        self.collapse(meshing)
        solve = self.add(PROCESS, 266, 120)
        report = self.add(PROCESS, 656, 120)
        return {"parent": parent, "meshing": meshing, "member": member, "solve": solve, "report": report}

    def test_expand_shifts_the_row_inside_the_parent_grows_it_on_crossed_sides_and_shifts_the_top_level_row(self) -> None:
        ids = self._row_in_a_parent()
        self.assertEqual(self.owner(ids["solve"]), ids["parent"])
        self.assertEqual(self.owner(ids["report"]), "")
        depth = self.undo_depth()
        before = self.snapshot()

        self.expand(ids["meshing"])

        self.assertEqual(self.undo_depth(), depth + 1)
        # Meshing's expanded right edge is 540: the 96 px gap after it is kept, and no more.
        self.assertEqual(self.position(ids["solve"]), (636.0, 120.0))
        self.assertEqual(self.group_rect(ids["parent"]), (0.0, 0.0, 892.0, 476.0))
        self.assertEqual(self.position(ids["report"]), (988.0, 120.0))
        self.assertEqual(self.position(ids["member"]), (80.0, 200.0))
        self.assertEqual(self.owner(ids["member"]), ids["meshing"])
        self.assertEqual(self.owner(ids["solve"]), ids["parent"])
        self.assertEqual(self.owner(ids["meshing"]), ids["parent"])
        self.assertIsNone(self.node(ids["meshing"]).held_member_ids)

        after = self.snapshot()
        self.undo()
        self.assertEqual(self.snapshot(), before)
        self.redo()
        self.assertEqual(self.snapshot(), after)

        self.collapse(ids["meshing"])
        self.expand(ids["meshing"])
        self.assertEqual(self.position(ids["solve"]), (636.0, 120.0))
        self.assertEqual(self.position(ids["report"]), (988.0, 120.0))
        self.assertEqual(self.group_rect(ids["parent"]), (0.0, 0.0, 892.0, 476.0))

    def test_three_levels_cascade_to_the_top_level(self) -> None:
        grand = self.group(0, 0, 700, 500, "Grand")
        parent = self.group(20, 60, 600, 400, "Parent")
        meshing = self.group(60, 120, 500, 300, "Meshing")
        self.add(PROCESS, 100, 200)
        self.collapse(meshing)
        # Parents fitted tightly around the pill (Group minimum size 260 x 180).
        self.scene.set_node_geometry(parent, 20.0, 60.0, 260.0, 180.0)
        self.scene.set_node_geometry(grand, 0.0, 0.0, 300.0, 280.0)
        after_grand = self.add(PROCESS, 396, 60)
        self.assertEqual((self.owner(meshing), self.owner(parent)), (parent, grand))
        depth = self.undo_depth()

        self.expand(meshing)

        self.assertEqual(self.undo_depth(), depth + 1)
        self.assertEqual(self.group_rect(parent), (20.0, 60.0, 572.0, 416.0))
        self.assertEqual(self.group_rect(grand), (0.0, 0.0, 624.0, 532.0))
        self.assertEqual(self.position(after_grand), (720.0, 60.0))
        self.assertEqual((self.owner(meshing), self.owner(parent)), (parent, grand))

    def test_nearest_applies_the_reach_radius_at_the_top_level_only(self) -> None:
        def far_displacement(nested: bool) -> float:
            self.setUp()
            self.prefs({**_NEAREST, "radius_mode": "local", "local_radius_preset": "small"})
            if nested:
                self.group(0, 0, 2400, 900, "Parent")
            expanding = self.group(100, 100, 420, 260)
            wide = self.group(470, 180, 700, 180)
            far = self.add(LOGGER, 1100, 200)
            self.collapse(expanding)
            before = self.position(far)
            self.expand(expanding)
            self.assertNotEqual(self.position(wide), (470.0, 180.0))
            after = self.position(far)
            return abs(after[0] - before[0]) + abs(after[1] - before[1])

        self.assertEqual(far_displacement(nested=False), 0.0)
        self.assertGreater(far_displacement(nested=True), 10.0)

    def test_push_off_keeps_overlaps_but_moves_intruders_out_and_still_grows_parents(self) -> None:
        self.prefs({"enabled": False})
        parent = self.group(0, 0, 700, 400, "Parent")
        meshing = self.group(40, 120, 500, 300, "Meshing")
        self.add(PROCESS, 80, 200)
        self.collapse(meshing)
        intruder = self.add(PROCESS, 300, 140)
        overlapping = self.add(PROCESS, 520, 300)

        self.expand(meshing)

        x, y = self.position(intruder)
        self.assertFalse(40 <= x and x + 224 <= 540 and 120 <= y and y + 84 <= 420, (x, y))
        self.assertEqual(self.owner(intruder), parent)
        self.assertEqual(self.position(overlapping), (520.0, 300.0))
        self.assertGreater(self.group_rect(parent)[3], 400.0)


class ExpandLockTests(_IdentityCase):
    def test_a_locked_neighbour_never_moves(self) -> None:
        self.group(0, 0, 1200, 600, "Parent")
        meshing = self.group(40, 120, 500, 300, "Meshing")
        self.add(PROCESS, 80, 200)
        self.collapse(meshing)
        locked = self.add(PROCESS, 400, 300)
        self.scene.set_node_locked(locked, True)
        row = self.add(PROCESS, 266, 120)

        self.expand(meshing)

        self.assertEqual(self.position(locked), (400.0, 300.0))
        self.assertNotEqual(self.position(row), (266.0, 120.0))

    def test_a_locked_intruder_stays_and_joins_with_a_hint(self) -> None:
        self.group(0, 0, 1200, 600, "Parent")
        meshing = self.group(40, 120, 500, 300, "Meshing")
        self.add(PROCESS, 80, 200)
        self.collapse(meshing)
        locked = self.add(PROCESS, 266, 160, "Pinned")
        self.scene.set_node_locked(locked, True)

        self.expand(meshing)

        self.assertEqual(self.position(locked), (266.0, 160.0))
        self.assertEqual(self.owner(locked), meshing)
        self.assertEqual(self.scene.take_expand_refusal_reason(), "Locked node “Pinned” joined Group “Meshing”.")

    def test_a_locked_parent_that_would_have_to_grow_refuses_and_changes_nothing(self) -> None:
        parent = self.group(0, 0, 560, 400, "Parent")
        meshing = self.group(40, 120, 500, 300, "Meshing")
        self.add(PROCESS, 80, 200)
        self.collapse(meshing)
        self.add(PROCESS, 266, 120)
        self.scene.set_node_locked(parent, True)
        depth = self.undo_depth()
        before = self.snapshot()

        self.assertFalse(self.scene.set_node_collapsed(meshing, False))

        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.undo_depth(), depth)
        self.assertEqual(
            self.scene.take_expand_refusal_reason(),
            "Can't expand: the locked Group “Parent” would have to grow.",
        )
        self.assertEqual(self.scene.take_expand_refusal_reason(), "")


class ExpandGuardAndStrayTests(_IdentityCase):
    def test_making_room_that_would_move_a_node_into_another_group_is_refused(self) -> None:
        self.prefs({"enabled": False})
        expanding = self.group(0, 0, 400, 260)
        self.collapse(expanding)
        self.group(0, 280, 400, 200, "Below")
        dropped = self.add(PROCESS, 20, 150)
        depth = self.undo_depth()
        before = self.snapshot()

        self.assertFalse(self.scene.set_node_collapsed(expanding, False))

        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.undo_depth(), depth)
        self.assertEqual(self.position(dropped), (20.0, 150.0))
        self.assertEqual(
            self.scene.take_expand_refusal_reason(),
            "Can't expand: there is no room without moving nodes into or out of a Group.",
        )

    def test_a_stray_that_would_end_up_in_another_group_refuses_the_expand(self) -> None:
        expanding = self.group(0, 0, 400, 300, "G")
        stray = self.add(PROCESS, 40, 120)
        self.collapse(expanding)
        self.assertTrue(self.scene.open_comment_peek(expanding))
        self.scene.move_node(stray, 1000.0, 100.0)
        self.scene.close_comment_peek()
        # Growing G around its stray would put the stray inside A as well, and A (locked) is the innermost Group.
        other = self.group(950, 50, 400, 300, "A")
        self.scene.set_node_locked(other, True)
        depth = self.undo_depth()
        before = self.snapshot()

        self.assertFalse(self.scene.set_node_collapsed(expanding, False))

        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.undo_depth(), depth)
        self.assertEqual(
            self.scene.take_expand_refusal_reason(),
            "Can't expand: there is no room without moving nodes into or out of a Group.",
        )

    def test_a_collapsed_group_whose_pill_corner_lands_in_the_expanded_area_is_moved_out(self) -> None:
        self.prefs({"enabled": False})
        expanding = self.group(0, 0, 420, 260, "G")
        self.add(PROCESS, 20, 120)
        self.collapse(expanding)
        other = self.group(350, 150, 300, 200, "C2")
        self.add(PROCESS, 380, 250)
        self.collapse(other)
        # The pill sticks out past G's expanded right edge (420), but its corner lies inside: an intruder.
        self.assertGreater(self.scene.node_bounds(other).right(), 420.0)

        self.expand(expanding)

        self.assertEqual(self.position(other), (452.0, 150.0))
        self.assertEqual(self.owner(other), "")

    def test_strays_keep_their_groups_and_the_groups_grow_around_them(self) -> None:
        outer = self.group(0, 0, 900, 600, "Outer")
        inner = self.group(60, 100, 400, 300, "Inner")
        stray_in_inner = self.add(PROCESS, 100, 200)
        stray_in_outer = self.add(PROCESS, 600, 200)
        self.collapse(outer)
        self.scene.move_node(stray_in_inner, 300.0, 700.0)
        self.scene.move_node(stray_in_outer, 1000.0, 200.0)

        self.expand(outer)

        self.assertEqual(self.owner(stray_in_inner), inner)
        self.assertEqual(self.owner(inner), outer)
        self.assertEqual(self.owner(stray_in_outer), outer)
        self.assertEqual(self.group_rect(inner), (60.0, 100.0, 496.0, 740.0))
        self.assertEqual(self.group_rect(outer), (0.0, 0.0, 1256.0, 896.0))


class GrowingNodeRegressionTests(_IdentityCase):
    def test_expanding_a_collapsed_logger_in_a_tight_group_grows_the_group_and_keeps_it_a_member(self) -> None:
        logger = self.add(LOGGER, 40, 120)
        self.collapse(logger)
        group = self.scene.wrap_node_ids_in_group_backdrop([logger])
        sibling = self.add(PROCESS, 400, 150)
        self.assertEqual(self.owner(logger), group)

        self.expand(logger)

        self.assertEqual(self.owner(logger), group)
        x, y, width, height = self.group_rect(group)
        self.assertGreaterEqual(x + width, 40 + 210)
        self.assertGreaterEqual(y + height, 120 + 174)
        self.assertGreaterEqual(self.position(sibling)[0], x + width)

    def test_opening_every_plot_settings_group_grows_the_group_and_moves_the_sibling_below(self) -> None:
        group = self.group(60, 0, 320, 500)
        plot = self.add(PLOT, 80, 120)
        below = self.add(PROCESS, 80, 300)
        spec = self.context.registry.get_spec(PLOT)

        for settings_group in spec.settings_groups:
            self.assertTrue(self.scene.set_node_settings_group_expanded(plot, settings_group.group_id, True))
            self.assertEqual(self.owner(plot), group)
            self.assertEqual(self.owner(below), group)

        plot_bounds = self.scene.node_bounds(plot)
        self.assertGreater(plot_bounds.height(), 1000.0)
        self.assertGreaterEqual(self.position(below)[1], plot_bounds.y() + plot_bounds.height())
        self.assertGreaterEqual(sum(self.group_rect(group)[1::2]), plot_bounds.y() + plot_bounds.height())

    def test_a_refused_settings_toggle_leaves_the_model_and_undo_stack_untouched(self) -> None:
        group = self.group(60, 0, 320, 300)
        plot = self.add(PLOT, 80, 120)
        self.scene.set_node_locked(group, True)
        depth = self.undo_depth()
        before = self.snapshot()

        self.assertFalse(self.scene.set_node_settings_group_expanded(plot, "general_options", True))

        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.undo_depth(), depth)
        self.assertIn("would have to grow", self.scene.take_expand_refusal_reason())

    def test_expanding_a_collapsed_plot_in_a_tight_group_grows_the_group_around_its_settings_band(self) -> None:
        for open_settings in (False, True):
            with self.subTest(open_settings=open_settings):
                self.setUp()
                plot = self.add(PLOT, 40, 120)
                if open_settings:
                    for settings_group in self.context.registry.get_spec(PLOT).settings_groups:
                        self.assertTrue(self.scene.set_node_settings_group_expanded(plot, settings_group.group_id, True))
                self.collapse(plot)
                group = self.scene.wrap_node_ids_in_group_backdrop([plot])

                self.expand(plot)

                # The expanded size includes the settings band that a plain surface measure leaves out.
                self.assertEqual(self.owner(plot), group)
                self.assert_group_contains_drawn(group, plot)


class PeekTests(_IdentityCase):
    def test_expanding_a_peeked_member_grows_the_expanded_size_and_keeps_the_pill(self) -> None:
        logger = self.add(LOGGER, 40, 120)
        self.collapse(logger)
        group = self.scene.wrap_node_ids_in_group_backdrop([logger])
        outside = self.add(PROCESS, 400, 0)
        self.collapse(group)
        pill = self.scene.node_bounds(group)
        rect_before = self.group_rect(group)
        self.assertTrue(self.scene.open_comment_peek(group))

        self.expand(logger)

        rect_after = self.group_rect(group)
        self.assertEqual(rect_after[:2], rect_before[:2])
        self.assertGreater(rect_after[2] * rect_after[3], rect_before[2] * rect_before[3])
        self.assertEqual(self.position(outside), (400.0, 0.0))
        self.scene.close_comment_peek()
        self.assertEqual(self.scene.node_bounds(group), pill)
        self.assertNotIn(logger, self.drawn())

    def test_growing_a_peeked_member_never_moves_the_pill_out_of_its_parent(self) -> None:
        parent = self.group(0, 60, 900, 800, "Parent")
        held = self.group(100, 150, 600, 500, "W")
        logger = self.add(LOGGER, 140, 200)
        self.collapse(logger)
        below = self.add(PROCESS, 140, 215)  # overlaps the logger's expanded body; its nearest free spot is above W
        self.collapse(held)
        self.assertEqual(self.owner(held), parent)
        rect_before = self.group_rect(held)
        pill = self.scene.node_bounds(held)
        self.assertTrue(self.scene.open_comment_peek(held))

        self.expand(logger)

        # A collapsed Group grows right and down only: the pushed node above it becomes a stray it still holds.
        self.assertEqual(self.group_rect(held)[:2], rect_before[:2])
        self.assertIn(below, self.node(held).held_member_ids)
        self.scene.close_comment_peek()
        self.assertEqual(self.scene.node_bounds(held), pill)
        self.assertEqual(self.owner(held), parent)

    def test_tidying_peeked_members_keeps_the_pill_in_place_and_in_its_parent(self) -> None:
        outer = self.group(0, 20, 1600, 900, "Q")
        held = self.group(100, 60, 900, 500, "P")
        first = self.add(PROCESS, 150, 100)  # closer to P's top than the wrap padding
        second = self.add(PROCESS, 700, 400)
        self.collapse(held)
        self.assertEqual(self.owner(held), outer)
        self.assertTrue(self.scene.open_comment_peek(held))

        outcome = self.scene.tidy_layout([first, second])

        self.assertTrue(outcome["changed"])
        self.assertEqual(list(outcome["membership_conflict_node_ids"]), [])
        self.assertEqual(self.group_rect(held)[:2], (100.0, 60.0))
        self.scene.close_comment_peek()
        self.assertEqual(self.owner(held), outer)

    def test_a_node_added_during_peek_joins_the_peeked_group_and_stays_hidden_after(self) -> None:
        group = self.group(0, 0, 600, 400, "G")
        self.add(PROCESS, 40, 120)
        self.collapse(group)
        self.assertTrue(self.scene.open_comment_peek(group))

        added = self.add(PROCESS, 50, 250)

        self.assertIn(added, self.node(group).held_member_ids)
        self.assertIn(added, self.drawn())
        self.scene.close_comment_peek()
        self.assertNotIn(added, self.drawn())

    def test_nodes_created_in_a_batch_during_peek_join_the_peeked_group(self) -> None:
        group = self.group(0, 0, 900, 600, "G")
        self.add(PROCESS, 40, 120)
        self.collapse(group)
        self.assertTrue(self.scene.open_comment_peek(group))

        results = self.scene.command_bridge.create_nodes_batch(
            (NodeCreationRequest(type_id=PROCESS, x=300.0, y=300.0, parent_node_id=None),)
        )

        added = results[0].node_id
        self.assertIn(added, self.node(group).held_member_ids)
        self.assertIn(added, self.drawn())
        self.scene.close_comment_peek()
        self.assertNotIn(added, self.drawn())

    def test_grouping_peeked_members_into_a_subnode_keeps_lists_in_scope_and_holds_the_shell(self) -> None:
        group = self.group(0, 0, 900, 600, "G")
        first = self.add(PROCESS, 40, 120)
        inner = self.group(400, 100, 400, 300, "E")
        second = self.add(PROCESS, 440, 200)
        self.collapse(group)
        self.assertTrue(self.scene.open_comment_peek(group))
        self.scene.clear_selection()
        self.scene.select_node(inner, True)
        self.scene.select_node(first, True)

        self.assertTrue(self.scene.group_selected_nodes())

        shell = self.context.selected_node_ids()[0]
        self.assertEqual({self.node(inner).parent_node_id, self.node(first).parent_node_id}, {shell})
        # G keeps only ids of its own scope and holds the new shell; E is no longer hidden, so it lists nothing.
        self.assertEqual(self.node(group).held_member_ids, tuple(sorted([shell, second])))
        self.assertIsNone(self.node(inner).held_member_ids)
        self.scene.close_comment_peek()
        self.assertEqual(self.drawn(), {group})

    def test_ungrouping_a_peeked_subnode_holds_and_selects_the_restored_nodes(self) -> None:
        group = self.group(0, 0, 900, 600, "G")
        first = self.add(PROCESS, 40, 120)
        second = self.add(PROCESS, 400, 300)
        self.scene.clear_selection()
        self.scene.select_node(first, True)
        self.scene.select_node(second, True)
        self.assertTrue(self.scene.group_selected_nodes())
        shell = self.context.selected_node_ids()[0]
        self.collapse(group)
        self.assertEqual(self.node(group).held_member_ids, (shell,))
        self.assertTrue(self.scene.open_comment_peek(group))
        self.scene.clear_selection()
        self.scene.select_node(shell, False)

        self.assertTrue(self.scene.ungroup_selected_subnode())

        self.assertEqual(set(self.context.selected_node_ids()), {first, second})
        self.assertEqual(self.node(group).held_member_ids, tuple(sorted([first, second])))
        self.assertTrue({first, second} <= self.drawn())
        self.scene.close_comment_peek()
        self.assertEqual(self.drawn(), {group})

    def test_wrapping_a_peeked_member_holds_lists_and_selects_the_new_group(self) -> None:
        group = self.group(0, 0, 900, 600, "G")
        member = self.add(PROCESS, 40, 120)
        self.collapse(group)
        self.assertTrue(self.scene.open_comment_peek(group))

        wrapped = self.scene.wrap_node_ids_in_group_backdrop([member])

        self.assertIn(wrapped, self.node(group).held_member_ids)
        self.assertEqual(self.node(wrapped).held_member_ids, (member,))
        self.assertIn(wrapped, self.drawn())
        self.assertEqual(self.context.selected_node_ids(), [wrapped])
        self.scene.close_comment_peek()
        self.assertEqual(self.drawn(), {group})


class CarryTests(_IdentityCase):
    def _nested_collapsed(self) -> dict[str, str]:
        group = self.group(0, 0, 600, 400, "G")
        inner = self.group(40, 120, 300, 200, "Inner")
        first = self.add(PROCESS, 60, 200)
        second = self.add(PROCESS, 360, 150)
        self.collapse(inner)
        self.collapse(group)
        return {"group": group, "inner": inner, "first": first, "second": second}

    def test_move_node_carries_every_held_member(self) -> None:
        ids = self._nested_collapsed()
        before = {key: self.position(node_id) for key, node_id in ids.items()}

        self.scene.move_node(ids["group"], 100.0, 50.0)

        for key, node_id in ids.items():
            self.assertEqual(self.position(node_id), (before[key][0] + 100.0, before[key][1] + 50.0), key)

    def test_move_node_carries_what_an_expanded_group_holds_in_one_undo_step(self) -> None:
        ids = {"group": self.group(0, 0, 900, 500, "G"), "inner": self.group(40, 120, 400, 300, "Inner")}
        ids["first"] = self.add(PROCESS, 80, 200)
        ids["second"] = self.add(PROCESS, 560, 150)
        outside = self.add(PROCESS, 1200, 150)
        before = {key: self.position(node_id) for key, node_id in ids.items()}
        depth = self.undo_depth()

        self.scene.move_node(ids["group"], 100.0, 50.0)

        for key, node_id in ids.items():
            self.assertEqual(self.position(node_id), (before[key][0] + 100.0, before[key][1] + 50.0), key)
        self.assertEqual(self.position(outside), (1200.0, 150.0))
        self.assertEqual(
            (self.owner(ids["inner"]), self.owner(ids["first"]), self.owner(ids["second"])),
            (ids["group"], ids["inner"], ids["group"]),
        )
        self.assertEqual(self.undo_depth(), depth + 1)
        self.undo()
        for key, node_id in ids.items():
            self.assertEqual(self.position(node_id), before[key], key)

    def test_move_nodes_by_delta_moves_each_member_once(self) -> None:
        ids = self._nested_collapsed()
        before = {key: self.position(node_id) for key, node_id in ids.items()}

        self.assertTrue(self.scene.move_nodes_by_delta([ids["group"], ids["inner"]], 10.0, 10.0))

        for key, node_id in ids.items():
            self.assertEqual(self.position(node_id), (before[key][0] + 10.0, before[key][1] + 10.0), key)

    def test_align_carries_held_members(self) -> None:
        ids = self._nested_collapsed()
        anchor = self.add(PROCESS, -300, 600)
        before = {key: self.position(node_id) for key, node_id in ids.items()}
        self.scene.clear_selection()
        self.scene.select_node(ids["group"], True)
        self.scene.select_node(anchor, True)

        self.assertTrue(self.scene.align_selected_nodes("left"))

        for key, node_id in ids.items():
            self.assertEqual(self.position(node_id), (before[key][0] - 300.0, before[key][1]), key)


class MarqueeDeleteSubnodeTests(_IdentityCase):
    def test_marquee_skips_hidden_members_but_selects_a_visible_node_over_a_hidden_area(self) -> None:
        group = self.group(0, 0, 600, 400)
        hidden = self.add(PROCESS, 40, 120)
        self.collapse(group)
        visible = self.add(PROCESS, 300, 200)

        self.scene.select_nodes_in_rect(-50.0, -50.0, 700.0, 500.0, False)

        selected = set(self.context.selected_node_ids())
        self.assertIn(visible, selected)
        self.assertNotIn(hidden, selected)

    def test_removing_a_collapsed_group_lets_its_hidden_expanded_groups_own_by_area_again(self) -> None:
        outer = self.group(0, 0, 900, 600, "Outer")
        inner = self.group(60, 100, 400, 300, "Inner")
        member = self.add(PROCESS, 100, 200)
        self.collapse(outer)
        self.assertEqual(self.node(inner).held_member_ids, (member,))

        self.scene.remove_node(outer)

        self.assertIsNone(self.node(inner).held_member_ids)
        self.assertEqual(self.drawn(), {inner, member})
        self.assertEqual(self.owner(member), inner)
        self.assertEqual(self.owner(inner), "")

    def test_grouping_into_a_subnode_moves_a_collapsed_group_with_its_held_members(self) -> None:
        group = self.group(0, 0, 600, 400, "G")
        first = self.add(PROCESS, 40, 120)
        second = self.add(PROCESS, 300, 200)
        self.collapse(group)
        other = self.add(PROCESS, 800, 100)
        self.scene.clear_selection()
        self.scene.select_node(group, True)
        self.scene.select_node(other, True)

        self.assertTrue(self.scene.group_selected_nodes())

        shell = self.context.selected_node_ids()[0]
        for node_id in (group, first, second, other):
            self.assertEqual(self.node(node_id).parent_node_id, shell, node_id)
        self.assertEqual(self.node(group).held_member_ids, tuple(sorted([first, second])))


class RemovalPublicationTests(_IdentityCase):
    """A removal that changes membership or visibility is drawn at once, without waiting for a later rebuild."""

    def test_context_menu_remove_of_a_collapsed_group_draws_what_it_held_and_undo_redo_restore_it(self) -> None:
        outer = self.group(0, 0, 900, 600, "Outer")
        inner = self.group(60, 100, 400, 300, "Inner")
        member = self.add(PROCESS, 100, 200)
        loose = self.add(PROCESS, 600, 200)
        self.collapse(outer)
        # The context-menu Remove Node action runs this interaction (workspace_edit_controller.request_remove_node).
        interactions = GraphInteractions(self.scene, self.context.registry, self.context.runtime_history)

        self.assertTrue(interactions.remove_node(outer).ok)

        self.assertEqual(self.drawn(), {inner, member, loose})
        self.assertEqual((self.owner(member), self.owner(inner), self.owner(loose)), (inner, "", ""))
        self.undo()
        self.assertEqual(self.drawn(), {outer})
        self.assertEqual(self.node(inner).held_member_ids, (member,))
        self.redo()
        self.assertEqual(self.drawn(), {inner, member, loose})
        self.assertIsNone(self.node(inner).held_member_ids)
        self.assertEqual(self.owner(member), inner)

    def test_redoing_the_removal_of_a_collapsed_group_draws_what_it_held(self) -> None:
        group = self.group(0, 0, 600, 400, "G")
        first = self.add(PROCESS, 40, 120)
        second = self.add(PROCESS, 300, 200)
        self.collapse(group)
        self.scene.remove_node(group)
        self.assertEqual(self.drawn(), {first, second})
        self.undo()
        self.assertEqual(self.drawn(), {group})

        # Only the Group differs between the snapshots, so redo replays the removal as a topology delta.
        self.redo()

        self.assertEqual(self.drawn(), {first, second})

    def test_removing_an_expanded_group_rehomes_its_members(self) -> None:
        parent = self.group(0, 0, 1200, 800, "Parent")
        group = self.group(100, 120, 600, 400, "G")
        member = self.add(PROCESS, 160, 240)

        self.scene.remove_node(group)

        self.assertEqual(self.owner(member), parent)
        self.assertEqual(self.row(parent)["member_node_ids"], [member])
        self.assertEqual(self.row(parent)["member_backdrop_ids"], [])

    def test_removing_a_member_drops_it_from_its_groups_lists(self) -> None:
        parent = self.group(0, 0, 1200, 800, "Parent")
        group = self.group(100, 120, 600, 400, "G")
        member = self.add(PROCESS, 160, 240)
        other = self.add(PROCESS, 420, 240)

        self.scene.remove_node(member)

        self.assertEqual(self.row(group)["member_node_ids"], [other])
        self.assertEqual(self.row(parent)["contained_node_ids"], [other])

    def test_deleting_a_selected_collapsed_group_removes_what_it_holds_and_updates_its_parent(self) -> None:
        parent = self.group(0, 0, 1200, 800, "Parent")
        group = self.group(100, 120, 600, 400, "G")
        inner = self.group(140, 240, 300, 200, "Inner")
        member = self.add(PROCESS, 180, 320)
        sibling = self.add(PROCESS, 800, 240)
        self.collapse(group)
        self.scene.clear_selection()
        self.scene.select_node(group, False)

        self.assertTrue(self.scene.delete_selected_graph_items([]))

        self.assertFalse({group, inner, member} & set(self.context.active_workspace().nodes))
        self.assertEqual(self.drawn(), {parent, sibling})
        self.assertEqual(self.row(parent)["member_node_ids"], [sibling])
        self.assertEqual(self.row(parent)["member_backdrop_ids"], [])
        self.assertEqual(self.row(parent)["contained_node_ids"], [sibling])

    def test_removing_a_node_outside_every_group_keeps_the_targeted_delta(self) -> None:
        self.group(0, 0, 600, 400, "G")
        self.add(PROCESS, 40, 120)
        free = self.add(PROCESS, 900, 120)

        with self.counting_full_rebuilds() as rebuilds:
            self.scene.remove_node(free)

        self.assertEqual(rebuilds, [])
        self.assertNotIn(free, self.drawn())


class TargetedPayloadMembershipTests(_IdentityCase):
    """Rename, lock, comment and link rebuild one payload, which keeps the owner and member fields."""

    def setUp(self) -> None:
        super().setUp()
        self.parent = self.group(0, 0, 1200, 800, "Parent")
        self.inner = self.group(100, 120, 600, 400, "Inner")
        self.member = self.add(PROCESS, 160, 240)

    def assert_membership_kept(self) -> None:
        member, inner, parent = self.row(self.member), self.row(self.inner), self.row(self.parent)
        self.assertEqual((member["owner_backdrop_id"], member["backdrop_depth"]), (self.inner, 2))
        self.assertEqual((inner["owner_backdrop_id"], inner["backdrop_depth"]), (self.parent, 1))
        self.assertEqual((inner["member_node_ids"], inner["contained_node_ids"]), ([self.member], [self.member]))
        self.assertEqual((parent["member_backdrop_ids"], parent["contained_backdrop_ids"]), ([self.inner], [self.inner]))
        self.assertEqual(parent["contained_node_ids"], [self.member])

    def check_targeted_edit(self, edit: Callable[[str], object]) -> None:
        for node_id in (self.member, self.inner):
            with self.subTest(node_id=node_id), self.counting_full_rebuilds() as rebuilds:
                edit(node_id)
                self.assertEqual(rebuilds, [])  # still the one-payload update
                self.assert_membership_kept()

    def test_rename_keeps_owner_and_member_fields(self) -> None:
        self.check_targeted_edit(lambda node_id: self.scene.set_node_title(node_id, f"Renamed {node_id}"))

    def test_lock_keeps_owner_and_member_fields(self) -> None:
        self.check_targeted_edit(lambda node_id: self.scene.set_node_locked(node_id, True))

    def test_comment_keeps_owner_and_member_fields(self) -> None:
        self.check_targeted_edit(lambda node_id: self.scene.upsert_node_comment(node_id, "", "Check the mesh."))

    def test_link_keeps_owner_and_member_fields(self) -> None:
        self.check_targeted_edit(
            lambda node_id: self.scene.upsert_node_link(node_id, "", "url", "Docs", "https://example.com/docs")
        )

    def test_undoing_a_rename_keeps_owner_and_member_fields(self) -> None:
        self.scene.set_node_title(self.inner, "Renamed")

        self.undo()

        self.assertEqual(self.node(self.inner).title, "Inner")
        self.assert_membership_kept()

    def test_editing_a_peeked_group_keeps_its_members_selectable(self) -> None:
        group = self.group(1400, 0, 600, 400, "Peeked")
        held = self.add(PROCESS, 1440, 120)
        self.collapse(group)
        self.assertTrue(self.scene.open_comment_peek(group))

        self.scene.upsert_node_comment(group, "", "Look inside.")
        self.scene.upsert_node_link(group, "", "url", "Docs", "https://example.com/docs")

        # Peek draws and selects only what the peeked Group's payload lists.
        self.assertEqual(self.row(group)["member_node_ids"], [held])
        self.scene.clear_selection()
        self.scene.select_node(held, False)
        self.assertEqual(self.context.selected_node_ids(), [held])


class WrapDrawnSizeTests(_IdentityCase):
    """A wrap fits the Group to the nodes as drawn, settings bands included, so the Group owns them."""

    def test_wrapping_a_plot_makes_a_group_that_owns_it(self) -> None:
        plot = self.add(PLOT, 100, 100)

        group = self.scene.wrap_node_ids_in_group_backdrop([plot])

        self.assertEqual(self.owner(plot), group)
        self.assert_group_contains_drawn(group, plot)

    def test_wrapping_a_plot_with_its_settings_groups_open_makes_a_group_that_owns_it(self) -> None:
        plot = self.add(PLOT, 100, 100)
        for settings_group in self.context.registry.get_spec(PLOT).settings_groups:
            self.assertTrue(self.scene.set_node_settings_group_expanded(plot, settings_group.group_id, True))
        self.assertGreater(self.scene.node_bounds(plot).height(), 1000.0)

        group = self.scene.wrap_node_ids_in_group_backdrop([plot])

        self.assertEqual(self.owner(plot), group)
        self.assert_group_contains_drawn(group, plot)


class FillInTests(unittest.TestCase):
    def test_older_documents_get_the_area_list_without_an_edit(self) -> None:
        context = build_context()
        scene = context.scene
        group = scene.add_node_from_type(GROUP, 0.0, 0.0)
        scene.set_node_geometry(group, 0.0, 0.0, 600.0, 400.0)
        inside = scene.add_node_from_type(PROCESS, 40.0, 120.0)
        scene.add_node_from_type(PROCESS, 900.0, 120.0)
        scene.set_node_collapsed(group, True)
        registry = context.registry
        serializer = JsonProjectSerializer(registry)
        document = serializer.to_document(context.stored_model.project)
        for workspace_doc in document["workspaces"]:
            for node_doc in workspace_doc["nodes"]:
                node_doc.pop("held_member_ids", None)

        project = serializer.from_document(document)
        workspace_id = context.workspace_id()
        workspace = project.workspaces[workspace_id]
        self.assertIsNone(workspace.nodes[group].held_member_ids)
        workspace.dirty = False
        model = GraphModel(project)
        history = RuntimeGraphHistory()
        fresh_scene = GraphSceneBridge()
        fresh_scene.bind_runtime_history(history)
        fresh_scene.set_workspace(model, registry, workspace_id)

        self.assertEqual(workspace.nodes[group].held_member_ids, (inside,))
        self.assertFalse(workspace.dirty)
        self.assertEqual(history.undo_depth(workspace_id), 0)
        drawn = {str(row["node_id"]) for row in (*fresh_scene.nodes_model, *fresh_scene.backdrop_nodes_model)}
        self.assertNotIn(inside, drawn)
        self.assertIn(group, drawn)

    def test_pasting_an_older_fragment_captures_no_bystanders(self) -> None:
        context = build_context()
        scene = context.scene
        group = scene.add_node_from_type(GROUP, 0.0, 0.0)
        scene.set_node_geometry(group, 0.0, 0.0, 600.0, 400.0)
        member = scene.add_node_from_type(PROCESS, 40.0, 120.0)
        scene.set_node_collapsed(group, True)
        scene.clear_selection()
        scene.select_node(group, False)
        fragment = copy.deepcopy(scene.serialize_selected_subgraph_fragment())
        self.assertIsNotNone(fragment)
        for node_payload in fragment["nodes"]:
            node_payload.pop("held_member_ids", None)
        bystander = scene.add_node_from_type(PROCESS, 2040.0, 1120.0)
        bystander_group = scene.add_node_from_type(GROUP, 2300.0, 1200.0)
        scene.set_node_geometry(bystander_group, 2300.0, 1200.0, 260.0, 200.0)
        before = set(context.active_workspace().nodes)

        self.assertTrue(scene.paste_subgraph_fragment(fragment, 2300.0, 1200.0))

        nodes = context.active_workspace().nodes
        pasted = set(nodes) - before
        pasted_group = next(node_id for node_id in pasted if nodes[node_id].type_id == GROUP)
        held = nodes[pasted_group].held_member_ids
        self.assertIsNotNone(held)
        self.assertTrue(set(held) <= pasted)
        self.assertNotIn(bystander, held)
        self.assertNotIn(member, held)
        # The expanded bystander Group lies inside the pasted Group's area; it was not pasted, so it keeps no list.
        pasted_node = nodes[pasted_group]
        self.assertTrue(
            pasted_node.x <= 2300.0
            and 2560.0 <= pasted_node.x + pasted_node.custom_width
            and pasted_node.y <= 1200.0
            and 1400.0 <= pasted_node.y + pasted_node.custom_height
        )
        self.assertNotIn(bystander_group, held)
        self.assertIsNone(nodes[bystander_group].held_member_ids)


if __name__ == "__main__":
    unittest.main()
