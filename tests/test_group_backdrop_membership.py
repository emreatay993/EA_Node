from __future__ import annotations

from collections.abc import Callable
import unittest

from ea_node_editor.graph.group_backdrop_geometry import (
    CORNER_CANDIDATE_SIZE,
    GROUP_BACKDROP_WRAP_BOTTOM_PADDING,
    GroupBackdropCandidate,
    build_group_backdrop_wrap_bounds,
    compute_group_backdrop_membership,
    held_member_position_updates,
    hidden_node_ids,
    honoured_held_member_ids,
    lists_to_clear,
    lists_to_freeze,
    membership_rect_kind,
)
from ea_node_editor.graph.group_backdrop_mutation_ops import wrap_selection_in_group_backdrop
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.graph.subnode_contract import SUBNODE_TYPE_ID
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

GROUP_BACKDROP_TYPE_ID = "passive.annotation.group_backdrop"
LOGGER_TYPE_ID = "core.logger"


class GroupBackdropGeometryTests(unittest.TestCase):
    def test_compute_membership_prefers_smallest_full_container_in_same_scope(self) -> None:
        membership = compute_group_backdrop_membership(
            [
                GroupBackdropCandidate("outer", (), True, 0.0, 0.0, 420.0, 320.0),
                GroupBackdropCandidate("inner", (), True, 60.0, 50.0, 200.0, 160.0),
                GroupBackdropCandidate("inner_node", (), False, 100.0, 100.0, 40.0, 40.0),
                GroupBackdropCandidate("outer_node", (), False, 300.0, 120.0, 40.0, 40.0),
                GroupBackdropCandidate("partial_node", (), False, 390.0, 100.0, 60.0, 60.0),
                GroupBackdropCandidate("other_scope_node", ("subnode",), False, 80.0, 80.0, 40.0, 40.0),
            ]
        )

        self.assertIsNone(membership["outer"].owner_backdrop_id)
        self.assertEqual(membership["outer"].backdrop_depth, 0)
        self.assertEqual(membership["outer"].member_node_ids, ("outer_node",))
        self.assertEqual(membership["outer"].member_backdrop_ids, ("inner",))
        self.assertEqual(membership["outer"].contained_node_ids, ("inner_node", "outer_node"))
        self.assertEqual(membership["outer"].contained_backdrop_ids, ("inner",))

        self.assertEqual(membership["inner"].owner_backdrop_id, "outer")
        self.assertEqual(membership["inner"].backdrop_depth, 1)
        self.assertEqual(membership["inner"].member_node_ids, ("inner_node",))
        self.assertEqual(membership["inner"].member_backdrop_ids, ())
        self.assertEqual(membership["inner"].contained_node_ids, ("inner_node",))
        self.assertEqual(membership["inner"].contained_backdrop_ids, ())

        self.assertEqual(membership["inner_node"].owner_backdrop_id, "inner")
        self.assertEqual(membership["inner_node"].backdrop_depth, 2)
        self.assertEqual(membership["outer_node"].owner_backdrop_id, "outer")
        self.assertEqual(membership["outer_node"].backdrop_depth, 1)
        self.assertIsNone(membership["partial_node"].owner_backdrop_id)
        self.assertEqual(membership["partial_node"].backdrop_depth, 0)
        self.assertIsNone(membership["other_scope_node"].owner_backdrop_id)
        self.assertEqual(membership["other_scope_node"].backdrop_depth, 0)

    def test_wrap_bounds_enforce_minimum_width_and_bottom_padding(self) -> None:
        bounds = build_group_backdrop_wrap_bounds(
            [
                GroupBackdropCandidate("node", (), False, 100.0, 200.0, 50.0, 30.0),
            ]
        )

        self.assertIsNotNone(bounds)
        assert bounds is not None
        self.assertEqual(bounds.x, 5.0)
        self.assertEqual(bounds.y, 104.0)
        self.assertEqual(bounds.width, 240.0)
        self.assertEqual(bounds.height, 182.0)
        self.assertEqual(bounds.y + bounds.height - 230.0, GROUP_BACKDROP_WRAP_BOTTOM_PADDING)

    def test_wrap_bounds_preserve_padding_when_selection_exceeds_minimum(self) -> None:
        bounds = build_group_backdrop_wrap_bounds(
            [
                GroupBackdropCandidate("first", (), False, 100.0, 100.0, 210.0, 132.0),
                GroupBackdropCandidate("second", (), False, 380.0, 250.0, 210.0, 132.0),
            ]
        )

        self.assertIsNotNone(bounds)
        assert bounds is not None
        self.assertEqual(bounds.x, 68.0)
        self.assertEqual(bounds.y, 4.0)
        self.assertEqual(bounds.width, 554.0)
        self.assertEqual(bounds.height, 434.0)
        self.assertEqual(bounds.y + bounds.height - 382.0, GROUP_BACKDROP_WRAP_BOTTOM_PADDING)


def _node(node_id: str, x: float = 0.0, y: float = 0.0, **fields: object) -> NodeInstance:
    return NodeInstance(node_id=node_id, type_id=GROUP_BACKDROP_TYPE_ID, title=node_id, x=x, y=y, **fields)


def _corner(node_id: str, x: float, y: float, held: tuple[str, ...]) -> GroupBackdropCandidate:
    """A collapsed Group with a list: identity, measured as the corner square at its top-left."""
    return GroupBackdropCandidate(node_id, (), True, x, y, CORNER_CANDIDATE_SIZE, CORNER_CANDIDATE_SIZE, held)


class GroupBackdropIdentityMembershipTests(unittest.TestCase):
    def test_collapsed_group_owns_its_listed_members_even_strays_and_claims_nothing_by_area(self) -> None:
        membership = compute_group_backdrop_membership(
            [
                _corner("group", 0.0, 0.0, ("inside", "stray")),
                GroupBackdropCandidate("inside", (), False, 40.0, 60.0, 100.0, 40.0),
                GroupBackdropCandidate("stray", (), False, 900.0, 60.0, 100.0, 40.0),
                GroupBackdropCandidate("over_hidden_area", (), False, 200.0, 80.0, 100.0, 40.0),
            ]
        )

        self.assertEqual(membership["inside"].owner_backdrop_id, "group")
        self.assertEqual(membership["stray"].owner_backdrop_id, "group")
        self.assertIsNone(membership["over_hidden_area"].owner_backdrop_id)
        self.assertEqual(membership["group"].member_node_ids, ("inside", "stray"))
        self.assertEqual(membership["group"].contained_node_ids, ("inside", "stray"))
        self.assertEqual(membership["stray"].backdrop_depth, 1)

    def test_unlisted_node_over_a_hidden_area_belongs_to_the_visible_parent(self) -> None:
        membership = compute_group_backdrop_membership(
            [
                GroupBackdropCandidate("parent", (), True, 0.0, 0.0, 1000.0, 800.0),
                _corner("collapsed", 100.0, 100.0, ("held",)),
                GroupBackdropCandidate("held", (), False, 150.0, 200.0, 100.0, 40.0),
                GroupBackdropCandidate("dropped", (), False, 180.0, 160.0, 100.0, 40.0),
            ]
        )

        self.assertEqual(membership["collapsed"].owner_backdrop_id, "parent")
        self.assertEqual(membership["held"].owner_backdrop_id, "collapsed")
        self.assertEqual(membership["held"].backdrop_depth, 2)
        self.assertEqual(membership["dropped"].owner_backdrop_id, "parent")
        self.assertEqual(membership["parent"].member_node_ids, ("dropped",))
        self.assertEqual(membership["parent"].member_backdrop_ids, ("collapsed",))
        self.assertEqual(membership["parent"].contained_node_ids, ("dropped", "held"))

    def test_nested_holders_hold_by_identity_and_the_innermost_listing_group_wins(self) -> None:
        membership = compute_group_backdrop_membership(
            [
                _corner("simulation", 0.0, 0.0, ("meshing", "mesh", "check", "setup", "pre", "pre_node")),
                _corner("meshing", 400.0, 0.0, ("mesh", "check")),
                # An expanded Group hidden inside a collapsed one keeps an honoured list of its own.
                GroupBackdropCandidate("pre", (), True, 0.0, 400.0, 300.0, 200.0, ("pre_node",)),
                GroupBackdropCandidate("setup", (), False, 40.0, 40.0, 100.0, 40.0),
                GroupBackdropCandidate("mesh", (), False, 5000.0, 40.0, 100.0, 40.0),
                GroupBackdropCandidate("check", (), False, 5200.0, 40.0, 100.0, 40.0),
                GroupBackdropCandidate("pre_node", (), False, 40.0, 440.0, 100.0, 40.0),
            ]
        )

        self.assertIsNone(membership["simulation"].owner_backdrop_id)
        self.assertEqual(membership["meshing"].owner_backdrop_id, "simulation")
        self.assertEqual(membership["pre"].owner_backdrop_id, "simulation")
        self.assertEqual(membership["setup"].owner_backdrop_id, "simulation")
        self.assertEqual(membership["mesh"].owner_backdrop_id, "meshing")
        self.assertEqual(membership["check"].owner_backdrop_id, "meshing")
        self.assertEqual(membership["pre_node"].owner_backdrop_id, "pre")
        self.assertEqual(membership["mesh"].backdrop_depth, 2)
        self.assertEqual(membership["simulation"].member_backdrop_ids, ("meshing", "pre"))
        self.assertEqual(membership["simulation"].member_node_ids, ("setup",))
        self.assertEqual(membership["simulation"].contained_node_ids, ("check", "mesh", "pre_node", "setup"))

    def test_corner_containment_keeps_a_pill_wider_than_its_parent_inside(self) -> None:
        membership = compute_group_backdrop_membership(
            [
                GroupBackdropCandidate("parent", (), True, 0.0, 0.0, 400.0, 300.0),
                # Drawn, this pill would be 737 px wide; only its top-left corner decides the parent.
                _corner("long_title", 50.0, 50.0, ()),
                _corner("outside", 400.0, 50.0, ()),
            ]
        )

        self.assertEqual(membership["long_title"].owner_backdrop_id, "parent")
        self.assertIsNone(membership["outside"].owner_backdrop_id)

    def test_membership_rect_kind_and_honoured_lists(self) -> None:
        collapsed_listed = _node("collapsed_listed", collapsed=True, held_member_ids=("a",))
        collapsed_older = _node("collapsed_older", collapsed=True)
        expanded_hidden = _node("expanded_hidden", held_member_ids=("b",))
        expanded_orphan = _node("expanded_orphan", held_member_ids=("c",))
        hidden = {"expanded_hidden"}.__contains__

        self.assertEqual(honoured_held_member_ids(collapsed_listed, is_backdrop=True, collapsed_lists_contain=hidden), ("a",))
        self.assertIsNone(honoured_held_member_ids(collapsed_older, is_backdrop=True, collapsed_lists_contain=hidden))
        self.assertEqual(honoured_held_member_ids(expanded_hidden, is_backdrop=True, collapsed_lists_contain=hidden), ("b",))
        # Its collapsed holder is gone: the stale list is not honoured and the Group claims by area again.
        self.assertIsNone(honoured_held_member_ids(expanded_orphan, is_backdrop=True, collapsed_lists_contain=hidden))
        self.assertIsNone(honoured_held_member_ids(collapsed_listed, is_backdrop=False, collapsed_lists_contain=hidden))

        self.assertEqual(membership_rect_kind(collapsed_listed, is_backdrop=True, list_honoured=True), "corner")
        self.assertEqual(membership_rect_kind(collapsed_older, is_backdrop=True, list_honoured=False), "expanded")
        self.assertEqual(membership_rect_kind(expanded_hidden, is_backdrop=True, list_honoured=True), "drawn")
        self.assertEqual(membership_rect_kind(collapsed_listed, is_backdrop=False, list_honoured=False), "drawn")

        membership = compute_group_backdrop_membership(
            [
                GroupBackdropCandidate("expanded_orphan", (), True, 0.0, 0.0, 400.0, 300.0, None),
                GroupBackdropCandidate("c", (), False, 1000.0, 0.0, 100.0, 40.0),
                GroupBackdropCandidate("inside", (), False, 40.0, 60.0, 100.0, 40.0),
            ]
        )
        self.assertIsNone(membership["c"].owner_backdrop_id)
        self.assertEqual(membership["inside"].owner_backdrop_id, "expanded_orphan")

    def test_dangling_self_and_cross_scope_ids_are_ignored(self) -> None:
        membership = compute_group_backdrop_membership(
            [
                _corner("group", 0.0, 0.0, ("missing", "group", "other_scope", "member")),
                GroupBackdropCandidate("other_scope", ("shell",), False, 40.0, 40.0, 100.0, 40.0),
                GroupBackdropCandidate("member", (), False, 40.0, 40.0, 100.0, 40.0),
            ]
        )

        self.assertIsNone(membership["group"].owner_backdrop_id)
        self.assertIsNone(membership["other_scope"].owner_backdrop_id)
        self.assertEqual(membership["group"].member_node_ids, ("member",))
        self.assertEqual(membership["group"].contained_node_ids, ("member",))

    def test_list_cycles_cannot_hang_membership(self) -> None:
        membership = compute_group_backdrop_membership(
            [
                _corner("first", 0.0, 0.0, ("second", "node")),
                _corner("second", 400.0, 0.0, ("first", "node")),
                GroupBackdropCandidate("node", (), False, 40.0, 40.0, 100.0, 40.0),
            ]
        )

        self.assertEqual(membership["first"].owner_backdrop_id, "second")
        self.assertEqual(membership["second"].owner_backdrop_id, "first")
        self.assertIn(membership["node"].owner_backdrop_id, {"first", "second"})
        self.assertGreaterEqual(membership["node"].backdrop_depth, 1)
        self.assertEqual(membership["first"].contained_backdrop_ids, ("second",))
        self.assertIn("node", (*membership["first"].contained_node_ids, *membership["second"].contained_node_ids))

    def test_hidden_node_ids_freeze_and_clear_follow_the_collapsed_lists(self) -> None:
        nodes = {
            "sim": _node("sim", collapsed=True, held_member_ids=("inner", "a", "b")),
            "inner": _node("inner", held_member_ids=("a",)),
            "a": _node("a"),
            "b": _node("b"),
            "free": _node("free"),
        }

        self.assertEqual(hidden_node_ids(nodes), {"inner", "a", "b"})
        self.assertEqual(hidden_node_ids(nodes, treat_as_expanded=("sim",)), set())
        self.assertEqual(lists_to_clear(nodes, "sim"), {"sim", "inner"})

        nodes["outer"] = _node("outer", collapsed=True, held_member_ids=("sim", "inner", "a", "b"))
        # Still hidden inside another collapsed Group: every list stays.
        self.assertEqual(lists_to_clear(nodes, "sim"), set())
        self.assertEqual(lists_to_clear(nodes, "free"), set())

        expanded = {
            "sim": _node("sim"),
            "inner": _node("inner"),
            "done": _node("done", collapsed=True, held_member_ids=("x",)),
            "a": _node("a"),
            "b": _node("b"),
            "x": _node("x"),
        }
        membership = compute_group_backdrop_membership(
            [
                GroupBackdropCandidate("sim", (), True, 0.0, 0.0, 1000.0, 800.0),
                GroupBackdropCandidate("inner", (), True, 20.0, 20.0, 400.0, 300.0),
                _corner("done", 500.0, 20.0, ("x",)),
                GroupBackdropCandidate("a", (), False, 40.0, 120.0, 100.0, 40.0),
                GroupBackdropCandidate("b", (), False, 600.0, 400.0, 100.0, 40.0),
                GroupBackdropCandidate("x", (), False, 3000.0, 400.0, 100.0, 40.0),
            ]
        )

        self.assertEqual(
            lists_to_freeze("sim", membership, expanded),
            {"sim": ("a", "b", "done", "inner", "x"), "inner": ("a",)},
        )

    def test_held_member_position_updates_carry_each_listed_member_once(self) -> None:
        nodes = {
            "group": _node("group", 100.0, 100.0, collapsed=True, held_member_ids=("a", "b", "elsewhere")),
            "other": _node("other", 900.0, 100.0, collapsed=True, held_member_ids=("b",)),
            "expanded": _node("expanded", 0.0, 0.0),
            "a": _node("a", 150.0, 160.0),
            "b": _node("b", 300.0, 200.0),
            "elsewhere": _node("elsewhere", 10.0, 10.0, parent_node_id="shell"),
        }

        carried = held_member_position_updates(
            nodes,
            {"group": (110.0, 105.0), "a": (170.0, 170.0), "other": (900.0, 300.0), "expanded": (5.0, 5.0)},
        )

        self.assertEqual(carried, {"b": (310.0, 205.0)})
        self.assertEqual(held_member_position_updates(nodes, {"group": (100.0, 100.0)}), {})


class GroupBackdropSceneIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.workspace_id = self.model.active_workspace.workspace_id
        self.scene = GraphSceneBridge()
        self.scene.set_workspace(self.model, self.registry, self.workspace_id)

    def test_wrap_selected_nodes_is_a_noop_without_selection(self) -> None:
        self.assertFalse(self.scene.wrap_selected_nodes_in_group_backdrop())

    def _scene_payload(self, node_id: str) -> dict[str, object]:
        for payload in [*self.scene.nodes_model, *self.scene.backdrop_nodes_model]:
            if str(payload["node_id"]) == str(node_id):
                return payload
        raise AssertionError(f"Node payload {node_id!r} was not found.")

    def _install_rebuild_recorder(self) -> tuple[list[str], Callable[[], None]]:
        rebuild_calls: list[str] = []
        original_rebuild_models = self.scene._scene_context.rebuild_models

        def _recording_rebuild_models() -> None:
            rebuild_calls.append("rebuild")
            original_rebuild_models()

        self.scene._scene_context.rebuild_models = _recording_rebuild_models
        return rebuild_calls, original_rebuild_models

    def _workspace_group_backdrop_ids(self) -> list[str]:
        workspace = self.model.project.workspaces[self.workspace_id]
        return [
            node_id
            for node_id, node in workspace.nodes.items()
            if node.type_id == GROUP_BACKDROP_TYPE_ID
        ]

    def _add_workspace_node(
        self,
        type_id: str,
        x: float,
        y: float,
        *,
        parent_node_id: str | None = None,
    ) -> str:
        service = self.model.validated_mutations(self.workspace_id, self.registry)
        spec = self.registry.get_spec(type_id)
        node = service.add_node(
            type_id=type_id,
            title=spec.display_name,
            x=float(x),
            y=float(y),
            properties=self.registry.default_properties(type_id),
            exposed_ports={port.key: port.exposed for port in spec.ports},
            parent_node_id=parent_node_id,
        )
        return node.node_id

    def test_scene_membership_rebuilds_after_bridge_move_and_explicit_refresh(self) -> None:
        logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 180.0, 140.0)
        backdrop_id = self.scene.add_node_from_type(GROUP_BACKDROP_TYPE_ID, 100.0, 100.0)
        self.scene.set_node_geometry(backdrop_id, 100.0, 100.0, 400.0, 260.0)

        logger_payload = self._scene_payload(logger_id)
        backdrop_payload = self._scene_payload(backdrop_id)
        self.assertEqual(logger_payload["owner_backdrop_id"], backdrop_id)
        self.assertEqual(logger_payload["backdrop_depth"], 1)
        self.assertEqual(backdrop_payload["member_node_ids"], [logger_id])
        self.assertEqual(backdrop_payload["contained_node_ids"], [logger_id])

        self.scene.move_node(logger_id, 520.0, 520.0)
        logger_payload = self._scene_payload(logger_id)
        backdrop_payload = self._scene_payload(backdrop_id)
        self.assertEqual(logger_payload["owner_backdrop_id"], "")
        self.assertEqual(logger_payload["backdrop_depth"], 0)
        self.assertEqual(backdrop_payload["member_node_ids"], [])
        self.assertEqual(backdrop_payload["contained_node_ids"], [])

        self.model.set_node_position(self.workspace_id, logger_id, 180.0, 140.0)
        self.scene.refresh_workspace_from_model(self.workspace_id)
        logger_payload = self._scene_payload(logger_id)
        backdrop_payload = self._scene_payload(backdrop_id)
        self.assertEqual(logger_payload["owner_backdrop_id"], backdrop_id)
        self.assertEqual(logger_payload["backdrop_depth"], 1)
        self.assertEqual(backdrop_payload["member_node_ids"], [logger_id])
        self.assertEqual(backdrop_payload["contained_node_ids"], [logger_id])

    def test_move_inside_group_backdrop_publishes_delta_without_full_rebuild(self) -> None:
        logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 180.0, 140.0)
        backdrop_id = self.scene.add_node_from_type(GROUP_BACKDROP_TYPE_ID, 100.0, 100.0)
        self.scene.set_node_geometry(backdrop_id, 100.0, 100.0, 400.0, 260.0)
        self.assertEqual(self._scene_payload(logger_id)["owner_backdrop_id"], backdrop_id)

        rebuild_calls, original_rebuild_models = self._install_rebuild_recorder()
        try:
            self.scene.move_node(logger_id, 220.0, 150.0)
        finally:
            self.scene._scene_context.rebuild_models = original_rebuild_models

        self.assertEqual(rebuild_calls, [])
        logger_payload = self._scene_payload(logger_id)
        backdrop_payload = self._scene_payload(backdrop_id)
        self.assertEqual(logger_payload["owner_backdrop_id"], backdrop_id)
        self.assertEqual(logger_payload["backdrop_depth"], 1)
        self.assertEqual(backdrop_payload["member_node_ids"], [logger_id])
        self.assertEqual(backdrop_payload["contained_node_ids"], [logger_id])

        node_delta = getattr(self.scene.state_bridge, "node_delta_payload", {})
        self.assertEqual(node_delta["kind"], "node_delta")
        self.assertEqual(node_delta["reason"], "node_position_delta")
        self.assertTrue(node_delta["visibility_may_change"])
        self.assertEqual([payload["node_id"] for payload in node_delta["nodes"]], [logger_id])
        self.assertEqual([payload["node_id"] for payload in node_delta["backdrop_nodes"]], [backdrop_id])

    def test_move_out_of_group_backdrop_keeps_membership_rebuild(self) -> None:
        logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 180.0, 140.0)
        backdrop_id = self.scene.add_node_from_type(GROUP_BACKDROP_TYPE_ID, 100.0, 100.0)
        self.scene.set_node_geometry(backdrop_id, 100.0, 100.0, 400.0, 260.0)
        self.assertEqual(self._scene_payload(logger_id)["owner_backdrop_id"], backdrop_id)

        rebuild_calls, original_rebuild_models = self._install_rebuild_recorder()
        try:
            self.scene.move_node(logger_id, 520.0, 520.0)
        finally:
            self.scene._scene_context.rebuild_models = original_rebuild_models

        self.assertGreaterEqual(len(rebuild_calls), 1)
        logger_payload = self._scene_payload(logger_id)
        backdrop_payload = self._scene_payload(backdrop_id)
        self.assertEqual(logger_payload["owner_backdrop_id"], "")
        self.assertEqual(logger_payload["backdrop_depth"], 0)
        self.assertEqual(backdrop_payload["member_node_ids"], [])
        self.assertEqual(backdrop_payload["contained_node_ids"], [])

    def test_collapsed_group_backdrop_move_keeps_full_rebuild(self) -> None:
        logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 180.0, 150.0)
        backdrop_id = self.scene.add_node_from_type(GROUP_BACKDROP_TYPE_ID, 100.0, 100.0)
        self.scene.set_node_geometry(backdrop_id, 100.0, 100.0, 460.0, 300.0)
        self.scene.set_node_collapsed(backdrop_id, True)

        rebuild_calls, original_rebuild_models = self._install_rebuild_recorder()
        try:
            self.scene.move_node(logger_id, 220.0, 160.0)
        finally:
            self.scene._scene_context.rebuild_models = original_rebuild_models

        self.assertGreaterEqual(len(rebuild_calls), 1)

    def test_comment_peek_move_keeps_full_rebuild(self) -> None:
        logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 180.0, 150.0)
        backdrop_id = self.scene.add_node_from_type(GROUP_BACKDROP_TYPE_ID, 100.0, 100.0)
        self.scene.set_node_geometry(backdrop_id, 100.0, 100.0, 460.0, 300.0)
        self.scene.set_node_collapsed(backdrop_id, True)
        self.assertTrue(self.scene.open_comment_peek(backdrop_id))
        self.assertEqual(self.scene.active_comment_peek_node_id, backdrop_id)

        rebuild_calls, original_rebuild_models = self._install_rebuild_recorder()
        try:
            self.scene.move_node(logger_id, 220.0, 160.0)
        finally:
            self.scene._scene_context.rebuild_models = original_rebuild_models

        self.assertGreaterEqual(len(rebuild_calls), 1)

    def test_wrap_node_ids_in_group_backdrop_creates_padded_group_backdrop_and_keeps_membership_derived(self) -> None:
        first_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 100.0, 100.0)
        second_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 380.0, 250.0)
        expected_bounds = build_group_backdrop_wrap_bounds(
            [
                GroupBackdropCandidate(
                    first_id,
                    (),
                    False,
                    float(self._scene_payload(first_id)["x"]),
                    float(self._scene_payload(first_id)["y"]),
                    float(self._scene_payload(first_id)["width"]),
                    float(self._scene_payload(first_id)["height"]),
                ),
                GroupBackdropCandidate(
                    second_id,
                    (),
                    False,
                    float(self._scene_payload(second_id)["x"]),
                    float(self._scene_payload(second_id)["y"]),
                    float(self._scene_payload(second_id)["width"]),
                    float(self._scene_payload(second_id)["height"]),
                ),
            ]
        )

        backdrop_id = self.scene.wrap_node_ids_in_group_backdrop([first_id, second_id])

        self.assertTrue(backdrop_id)
        self.assertEqual(self.scene.selected_node_id_value, backdrop_id)
        self.assertIsNotNone(expected_bounds)
        assert expected_bounds is not None

        workspace = self.model.project.workspaces[self.workspace_id]
        backdrop = workspace.nodes[backdrop_id]
        self.assertEqual(backdrop.type_id, GROUP_BACKDROP_TYPE_ID)
        self.assertEqual(backdrop.title, "")
        self.assertEqual(backdrop.properties, {"title": ""})
        self.assertEqual(backdrop.x, expected_bounds.x)
        self.assertEqual(backdrop.y, expected_bounds.y)
        self.assertEqual(backdrop.custom_width, expected_bounds.width)
        self.assertEqual(backdrop.custom_height, expected_bounds.height)

        first_payload = self._scene_payload(first_id)
        second_payload = self._scene_payload(second_id)
        backdrop_payload = self._scene_payload(backdrop_id)
        self.assertEqual(first_payload["owner_backdrop_id"], backdrop_id)
        self.assertEqual(second_payload["owner_backdrop_id"], backdrop_id)
        self.assertEqual(first_payload["backdrop_depth"], 1)
        self.assertEqual(second_payload["backdrop_depth"], 1)
        self.assertEqual(backdrop_payload["owner_backdrop_id"], "")
        self.assertEqual(backdrop_payload["backdrop_depth"], 0)
        self.assertEqual(backdrop_payload["member_node_ids"], sorted([first_id, second_id]))
        self.assertEqual(backdrop_payload["member_backdrop_ids"], [])
        self.assertEqual(backdrop_payload["contained_node_ids"], sorted([first_id, second_id]))
        self.assertEqual(backdrop_payload["contained_backdrop_ids"], [])

        document = JsonProjectSerializer(self.registry).to_document(self.model.project)
        workspace_doc = next(item for item in document["workspaces"] if item["workspace_id"] == self.workspace_id)
        backdrop_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == backdrop_id)
        first_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == first_id)
        for node_doc in (backdrop_doc, first_doc):
            for key in (
                "owner_backdrop_id",
                "backdrop_depth",
                "member_node_ids",
                "member_backdrop_ids",
                "contained_node_ids",
                "contained_backdrop_ids",
            ):
                self.assertNotIn(key, node_doc)

    def test_collapsed_group_backdrop_payload_projects_expanded_occupied_bounds(self) -> None:
        logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 180.0, 150.0)
        backdrop_id = self.scene.add_node_from_type(GROUP_BACKDROP_TYPE_ID, 100.0, 100.0)
        self.scene.set_node_geometry(backdrop_id, 100.0, 100.0, 460.0, 300.0)
        self.assertEqual(self._scene_payload(logger_id)["owner_backdrop_id"], backdrop_id)

        self.scene.set_node_collapsed(backdrop_id, True)

        backdrop_payload = self._scene_payload(backdrop_id)
        occupied = backdrop_payload["expanded_occupied_bounds"]
        self.assertGreater(float(occupied["width"]), float(backdrop_payload["width"]))
        self.assertGreater(float(occupied["height"]), float(backdrop_payload["height"]))
        self.assertAlmostEqual(float(occupied["x"]), 100.0, places=6)
        self.assertAlmostEqual(float(occupied["y"]), 100.0, places=6)
        self.assertAlmostEqual(float(occupied["width"]), 460.0, places=6)
        self.assertAlmostEqual(float(occupied["height"]), 300.0, places=6)

    def test_wrap_selection_fits_the_drawn_sizes_it_is_given(self) -> None:
        logger_id = self._add_workspace_node(LOGGER_TYPE_ID, 100.0, 100.0)
        expected = build_group_backdrop_wrap_bounds(
            [GroupBackdropCandidate(logger_id, (), False, 100.0, 100.0, 300.0, 500.0)]
        )

        result = wrap_selection_in_group_backdrop(
            model=self.model,
            registry=self.registry,
            workspace_id=self.workspace_id,
            selected_node_ids=[logger_id],
            scope_path=(),
            node_sizes={logger_id: (300.0, 500.0)},
        )

        assert result is not None and expected is not None
        self.assertEqual(
            (result.x, result.y, result.width, result.height),
            (expected.x, expected.y, expected.width, expected.height),
        )

    def test_wrap_selection_transaction_rejects_cross_scope_node_sets(self) -> None:
        root_logger_id = self._add_workspace_node(LOGGER_TYPE_ID, 40.0, 40.0)
        shell_id = self._add_workspace_node(SUBNODE_TYPE_ID, 220.0, 120.0)
        child_logger_id = self._add_workspace_node(LOGGER_TYPE_ID, 20.0, 20.0, parent_node_id=shell_id)

        result = wrap_selection_in_group_backdrop(
            model=self.model,
            registry=self.registry,
            workspace_id=self.workspace_id,
            selected_node_ids=[root_logger_id, child_logger_id],
            scope_path=(),
        )

        self.assertIsNone(result)
        self.assertEqual(self._workspace_group_backdrop_ids(), [])


if __name__ == "__main__":
    unittest.main()
