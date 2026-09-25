# Purpose: Offscreen tests for the scene Group-scope geometry used by mutations: scope rectangles, membership, owner changes and Group growth.
# Map: feature_routes/group_backdrops_peek_membership
# Tests: tests/test_group_scope.py
from __future__ import annotations

import unittest

from ea_node_editor.graph.hierarchy import scope_node_ids
from ea_node_editor.graph.transform_layout_ops import LayoutNodeBounds
from ea_node_editor.ui_qml.graph_scene_mutation.group_scope import (
    GroupScope,
    collect_group_scope,
    group_membership_for_scope,
    grow_group_around,
    grow_owner_chain,
    node_layout_bounds,
)
from tests.automation.harness import build_context

GROUP = "passive.annotation.group_backdrop"
PROCESS = "passive.flowchart.process"
LOGGER = "core.logger"
PLOT = "plot.signal"


class _GroupScopeCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene
        self.boundary = self.scene._authoring_boundary  # noqa: SLF001

    def add(self, type_id: str, x: float, y: float) -> str:
        return self.scene.add_node_from_type(type_id, float(x), float(y))

    def group(self, x: float, y: float, width: float, height: float) -> str:
        group_id = self.add(GROUP, x, y)
        self.scene.set_node_geometry(group_id, float(x), float(y), float(width), float(height))
        return group_id

    def collect(self) -> GroupScope:
        workspace = self.context.active_workspace()
        return collect_group_scope(
            self.boundary,
            workspace,
            scope_node_ids(workspace, self.scene._scene_context.scope_path),  # noqa: SLF001
            dict(workspace.nodes),
        )


class GroupScopeCollectTests(_GroupScopeCase):
    def test_scope_measures_expanded_groups_and_owns_members_by_area(self) -> None:
        group = self.group(100.0, 100.0, 400.0, 300.0)
        member = self.add(PROCESS, 160.0, 220.0)
        outside = self.add(PROCESS, 800.0, 220.0)

        scope = self.collect()

        self.assertEqual(scope.group_backdrop_ids, {group})
        self.assertEqual(scope.rects[group], LayoutNodeBounds(group, 100.0, 100.0, 400.0, 300.0))
        self.assertEqual(scope.owner(member), group)
        self.assertIsNone(scope.owner(outside))
        self.assertEqual(scope.contents(group), [member])
        self.assertEqual(scope.direct_members(group), [member])

    def test_owner_changes_report_nodes_entering_or_leaving_a_group(self) -> None:
        group = self.group(100.0, 100.0, 400.0, 300.0)
        member = self.add(PROCESS, 160.0, 220.0)
        outside = self.add(PROCESS, 800.0, 220.0)
        scope = self.collect()

        self.assertEqual(scope.owner_changes(scope.rects), set())
        rects = dict(scope.rects)
        rects[outside] = scope.rects[outside].translated(-620.0, 0.0)
        rects[member] = scope.rects[member].translated(900.0, 0.0)
        self.assertEqual(scope.owner_changes(rects), {member, outside})
        self.assertIsNotNone(group)

    def test_group_membership_for_scope_is_empty_without_groups(self) -> None:
        node = self.add(PROCESS, 0.0, 0.0)
        workspace = self.context.active_workspace()

        self.assertEqual(
            group_membership_for_scope(self.boundary, workspace, node, workspace_nodes=dict(workspace.nodes)),
            ({}, set()),
        )

    def test_node_layout_bounds_measure_a_collapsed_node_drawn_or_expanded(self) -> None:
        logger = self.add(LOGGER, 40.0, 60.0)
        self.scene.set_node_collapsed(logger, True)
        workspace = self.context.active_workspace()
        node = workspace.nodes[logger]

        drawn = node_layout_bounds(self.boundary, workspace, node, expanded=False)
        expanded = node_layout_bounds(self.boundary, workspace, node, expanded=True)

        self.assertEqual((drawn.x, drawn.y), (40.0, 60.0))
        self.assertEqual((expanded.x, expanded.y), (40.0, 60.0))
        self.assertLess(drawn.height, expanded.height)

    def test_a_node_without_a_drawn_payload_is_measured_like_a_payload_build(self) -> None:
        plot = self.add(PLOT, 40.0, 60.0)
        workspace = self.context.active_workspace()
        drawn = node_layout_bounds(self.boundary, workspace, workspace.nodes[plot], expanded=False)
        group = self.group(0.0, 0.0, 600.0, 400.0)
        self.scene.set_node_collapsed(group, True)
        self.assertIn(plot, workspace.nodes[group].held_member_ids)  # hidden now, so no cached payload

        measured = node_layout_bounds(self.boundary, workspace, workspace.nodes[plot], expanded=False)

        # The plot's settings band is part of its drawn height; a plain surface measure leaves it out.
        self.assertEqual(measured, drawn)
        self.assertGreater(measured.height, 100.0)


class GroupScopeGrowthTests(_GroupScopeCase):
    def test_grow_owner_chain_grows_nested_owners_around_a_moved_member(self) -> None:
        outer = self.group(0.0, 0.0, 900.0, 700.0)
        inner = self.group(60.0, 60.0, 400.0, 300.0)
        member = self.add(PROCESS, 120.0, 180.0)
        scope = self.collect()
        self.assertEqual(scope.owner(member), inner)
        self.assertEqual(scope.owner(inner), outer)
        rects = dict(scope.rects)
        rects[member] = scope.rects[member].translated(700.0, 0.0)

        grown = grow_owner_chain(self.boundary, self.context.active_workspace(), rects, scope, inner)

        self.assertEqual(grown, {inner, outer})
        self.assertGreater(rects[inner].right, rects[member].right)
        self.assertGreater(rects[outer].right, rects[inner].right)
        self.assertEqual((rects[inner].x, rects[inner].y), (60.0, 60.0))

    def test_grow_owner_chain_refuses_a_locked_owner(self) -> None:
        group = self.group(60.0, 60.0, 400.0, 300.0)
        member = self.add(PROCESS, 120.0, 180.0)
        self.scene.set_node_locked(group, True)
        scope = self.collect()
        rects = dict(scope.rects)
        rects[member] = scope.rects[member].translated(700.0, 0.0)

        self.assertIsNone(grow_owner_chain(self.boundary, self.context.active_workspace(), rects, scope, group))


class GroupScopeIdentityTests(_GroupScopeCase):
    def test_a_collapsed_group_is_its_pill_keeps_its_expanded_rect_and_owns_by_identity(self) -> None:
        group = self.group(100.0, 100.0, 400.0, 300.0)
        member = self.add(PROCESS, 160.0, 220.0)
        self.scene.set_node_collapsed(group, True)

        scope = self.collect()

        self.assertEqual((scope.rects[group].width, scope.rects[group].height), (130.0, 36.0))
        self.assertEqual(scope.expanded_rects[group], LayoutNodeBounds(group, 100.0, 100.0, 400.0, 300.0))
        self.assertEqual(scope.member_lists[group], (member,))
        self.assertTrue(scope.owns_by_identity(group))
        self.assertEqual(scope.owner(member), group)
        candidates = {candidate.node_id: candidate for candidate in scope.candidates(scope.rects)}
        self.assertEqual((candidates[group].x, candidates[group].y), (100.0, 100.0))
        self.assertEqual((candidates[group].width, candidates[group].height), (1.0, 1.0))
        self.assertEqual(candidates[group].held_member_ids, (member,))
        self.assertIsNone(candidates[member].held_member_ids)
        self.assertEqual(candidates[member].width, scope.rects[member].width)

    def test_an_older_collapsed_group_without_a_list_keeps_its_expanded_rect_and_owns_by_area(self) -> None:
        group = self.group(100.0, 100.0, 400.0, 300.0)
        member = self.add(PROCESS, 160.0, 220.0)
        self.scene.set_node_collapsed(group, True)
        self.context.active_workspace().nodes[group].held_member_ids = None

        scope = self.collect()

        self.assertEqual(scope.rects[group], LayoutNodeBounds(group, 100.0, 100.0, 400.0, 300.0))
        self.assertFalse(scope.owns_by_identity(group))
        self.assertEqual(scope.owner(member), group)

    def test_membership_at_and_owner_changes_simulate_list_and_collapse_changes(self) -> None:
        group = self.group(100.0, 100.0, 400.0, 300.0)
        self.add(PROCESS, 160.0, 220.0)
        self.scene.set_node_collapsed(group, True)
        dropped = self.add(PROCESS, 200.0, 150.0)
        scope = self.collect()
        self.assertIsNone(scope.owner(dropped))
        self.assertEqual(scope.owner_changes(scope.rects), set())
        expanded_rects = dict(scope.rects)
        expanded_rects[group] = scope.expanded_rects[group]

        expanded_changes = scope.owner_changes(
            expanded_rects,
            list_overrides={group: None},
            collapsed_overrides={group: False},
        )
        membership = scope.membership_at(
            expanded_rects,
            list_overrides={group: None},
            collapsed_overrides={group: False},
        )

        self.assertEqual(expanded_changes, {dropped})
        self.assertEqual(membership[dropped].owner_backdrop_id, group)

    def test_grow_group_around_grows_only_the_sides_a_member_crosses(self) -> None:
        group = self.group(0.0, 0.0, 400.0, 300.0)
        member = self.add(PROCESS, 40.0, 100.0)
        outside = self.add(PROCESS, 900.0, 100.0)
        scope = self.collect()
        rects = dict(scope.rects)

        rects[member] = LayoutNodeBounds(member, 300.0, 100.0, 224.0, 84.0)
        self.assertEqual(grow_group_around(scope, rects, group, [member]), LayoutNodeBounds(group, 0.0, 0.0, 556.0, 300.0))
        rects[member] = LayoutNodeBounds(member, 40.0, 4.0, 224.0, 84.0)
        self.assertIsNone(grow_group_around(scope, rects, group, [member]), "near the top but inside: no growth")
        rects[member] = LayoutNodeBounds(member, 40.0, -20.0, 224.0, 84.0)
        self.assertEqual(grow_group_around(scope, rects, group, [member]), LayoutNodeBounds(group, 0.0, -116.0, 400.0, 416.0))
        rects[member] = LayoutNodeBounds(member, 40.0, 250.0, 100.0, 60.0)
        base = LayoutNodeBounds(group, 0.0, 0.0, 200.0, 200.0)
        self.assertEqual(
            grow_group_around(scope, rects, group, [member], base_rect=base),
            LayoutNodeBounds(group, 0.0, 0.0, 200.0, 366.0),
        )
        self.assertIsNone(grow_group_around(scope, rects, group, [outside]), "a non-member never grows the Group")

    def test_grow_owner_chain_grows_a_collapsed_owners_expanded_rect_and_stops(self) -> None:
        outer = self.group(0.0, 0.0, 1200.0, 800.0)
        inner = self.group(60.0, 60.0, 400.0, 300.0)
        member = self.add(PROCESS, 100.0, 150.0)
        self.scene.set_node_collapsed(inner, True)
        scope = self.collect()
        self.assertEqual(scope.owner(inner), outer)
        rects = dict(scope.rects)
        rects[member] = scope.rects[member].translated(500.0, 0.0)
        expanded_rects: dict[str, LayoutNodeBounds] = {}

        grown = grow_owner_chain(
            self.boundary,
            self.context.active_workspace(),
            rects,
            scope,
            inner,
            expanded_rects=expanded_rects,
        )

        self.assertEqual(grown, {inner})
        grown_rect = expanded_rects[inner]
        self.assertTrue(
            grown_rect.left <= rects[member].left
            and grown_rect.top <= rects[member].top
            and grown_rect.right > rects[member].right
            and grown_rect.bottom > rects[member].bottom,
            grown_rect,
        )
        self.assertEqual(rects[inner], scope.rects[inner], "the pill does not change")
        self.assertEqual(rects[outer], scope.rects[outer], "the chain stops at the collapsed owner")


if __name__ == "__main__":
    unittest.main()
