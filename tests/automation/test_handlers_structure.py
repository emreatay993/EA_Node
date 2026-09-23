# Purpose: Shell-free handler tests for edge.* and structure ops (connect/update/delete, group.wrap, subnode.*, scope, selection, layout) with one-undo-step pins.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_structure.py
from __future__ import annotations

import unittest
from typing import Any

from ea_node_editor.automation.client_api.edges import EdgesApi
from ea_node_editor.automation.client_api.structure import StructureApi
from ea_node_editor.automation.errors import (
    INVALID_PARAMS,
    NO_EFFECT,
    NOT_FOUND,
    PORT_INCOMPATIBLE,
    WRONG_SCOPE,
)
from tests.automation.harness import build_context, call, expect_error

START = "passive.flowchart.start"
PROCESS = "passive.flowchart.process"
TRIGGER = "core.trigger"  # cheap active node: one single-connection data input, one data output
GROUP = "passive.annotation.group_backdrop"
SHELL = "core.subnode"
PIN_IN = "core.subnode_input"
PIN_OUT = "core.subnode_output"


class _HandlerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene

    def add(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        return self.scene.add_node_from_type(type_id, float(x), float(y))

    def undo_depth(self) -> int:
        return self.context.runtime_history.undo_depth(self.context.workspace_id())

    def call_one_undo(self, op: str, params: dict[str, Any]) -> dict[str, Any]:
        before = self.undo_depth()
        result = call(self.context, op, params)
        self.assertEqual(self.undo_depth(), before + 1, f"{op} must add exactly one undo entry")
        return result

    def call_no_undo(self, op: str, params: dict[str, Any]) -> dict[str, Any]:
        before = self.undo_depth()
        result = call(self.context, op, params)
        self.assertEqual(self.undo_depth(), before, f"{op} must not add undo entries")
        return result

    def connect(self, source: str, sport: str, target: str, tport: str, **extra: Any) -> dict[str, Any]:
        params = {"source_node_id": source, "source_port": sport, "target_node_id": target, "target_port": tport, **extra}
        return call(self.context, "edge.connect", params)

    def edge_ids(self) -> list[str]:
        return list(self.context.active_workspace().edges)


class EdgeConnectTests(_HandlerCase):
    def test_connect_passive_right_to_left_adds_one_edge_and_one_undo_step(self) -> None:
        start = self.add(START, 0, 0)
        step = self.add(PROCESS, 300, 0)
        result = self.call_one_undo(
            "edge.connect",
            {"source_node_id": start, "source_port": "right", "target_node_id": step, "target_port": "left"},
        )
        edge = self.context.require_edge(result["edge_id"])
        self.assertEqual((edge.source_node_id, edge.source_port_key), (start, "right"))
        self.assertEqual((edge.target_node_id, edge.target_port_key), (step, "left"))
        self.assertEqual(result["replaced_edge_ids"], [])
        self.assertEqual(result["edge"]["kind"], "flow")
        self.assertTrue(result["edge"]["enabled"])
        self.assertEqual(self.edge_ids(), [edge.edge_id])

    def test_connect_reports_missing_nodes_and_ports(self) -> None:
        start = self.add(START)
        step = self.add(PROCESS, 300, 0)
        missing_node = expect_error(
            self.context,
            "edge.connect",
            {"source_node_id": "node_missing", "source_port": "right", "target_node_id": step, "target_port": "left"},
            NOT_FOUND,
        )
        self.assertEqual(missing_node.details["id"], "node_missing")
        missing_port = expect_error(
            self.context,
            "edge.connect",
            {"source_node_id": start, "source_port": "east", "target_node_id": step, "target_port": "left"},
            NOT_FOUND,
        )
        self.assertEqual(missing_port.details["port"], "east")
        self.assertEqual(sorted(missing_port.details["available"]), ["bottom", "left", "right", "top"])
        self.assertEqual(self.edge_ids(), [])

    def test_connect_flow_port_to_data_port_is_port_incompatible(self) -> None:
        start = self.add(START)
        trigger = self.add(TRIGGER, 300, 0)
        before = self.undo_depth()
        error = expect_error(
            self.context,
            "edge.connect",
            {"source_node_id": start, "source_port": "right", "target_node_id": trigger, "target_port": "input"},
            PORT_INCOMPATIBLE,
        )
        self.assertIn("port_kind_mismatch", error.details["reason"])
        self.assertEqual(error.details["target_port"], "input")
        self.assertEqual(self.edge_ids(), [])
        self.assertEqual(self.undo_depth(), before)

    def test_connect_occupied_single_input_requires_replace_existing(self) -> None:
        first = self.add(TRIGGER, 0, 0)
        second = self.add(TRIGGER, 0, 200)
        sink = self.add(TRIGGER, 400, 100)
        existing = self.connect(first, "output", sink, "input")["edge_id"]

        error = expect_error(
            self.context,
            "edge.connect",
            {"source_node_id": second, "source_port": "output", "target_node_id": sink, "target_port": "input"},
            PORT_INCOMPATIBLE,
        )
        self.assertEqual(error.details["reason"], "target_port_occupied")
        self.assertEqual(error.details["occupied_by"], [existing])
        self.assertIn("replace_existing", error.hint)
        self.assertEqual(self.edge_ids(), [existing])

        result = self.call_one_undo(
            "edge.connect",
            {
                "source_node_id": second,
                "source_port": "output",
                "target_node_id": sink,
                "target_port": "input",
                "replace_existing": True,
            },
        )
        self.assertEqual(result["replaced_edge_ids"], [existing])
        self.assertIsNone(self.context.edge_or_none(existing))
        edge = self.context.require_edge(result["edge_id"])
        self.assertEqual(edge.source_node_id, second)
        self.assertEqual(self.edge_ids(), [edge.edge_id])
        self.assertEqual(result["edge"]["kind"], "data")

    def test_connect_appends_on_multi_connection_passive_ports(self) -> None:
        start = self.add(START, 0, 0)
        other = self.add(PROCESS, 0, 300)
        step = self.add(PROCESS, 400, 150)
        first = self.connect(start, "right", step, "left")["edge_id"]
        second = self.connect(other, "right", step, "left")
        self.assertEqual(second["replaced_edge_ids"], [])
        self.assertEqual(sorted(self.edge_ids()), sorted([first, second["edge_id"]]))

    def test_connect_duplicate_edge_is_no_effect(self) -> None:
        start = self.add(START)
        step = self.add(PROCESS, 300, 0)
        existing = self.connect(start, "right", step, "left")["edge_id"]
        error = expect_error(
            self.context,
            "edge.connect",
            {"source_node_id": start, "source_port": "right", "target_node_id": step, "target_port": "left"},
            NO_EFFECT,
        )
        self.assertEqual(error.details["edge_id"], existing)
        self.assertEqual(self.edge_ids(), [existing])

    def test_connect_applies_label_and_aliased_style_in_one_undo_step(self) -> None:
        start = self.add(START)
        step = self.add(PROCESS, 300, 0)
        result = self.call_one_undo(
            "edge.connect",
            {
                "source_node_id": start,
                "source_port": "right",
                "target_node_id": step,
                "target_port": "left",
                "label": "yes",
                "style": {
                    "color": "#ff0000",
                    "width": 3,
                    "pattern": "dashed",
                    "path_mode": "pipe",
                    "display_mode": "faint",
                },
            },
        )
        edge = self.context.require_edge(result["edge_id"])
        self.assertEqual(edge.label, "yes")
        self.assertEqual(
            edge.visual_style,
            {
                "stroke_color": "#ff0000",
                "stroke_width": 3.0,
                "stroke_pattern": "dashed",
                "path_mode": "pipe",
                "display_mode": "faint",
            },
        )
        self.assertEqual(result["edge"]["label"], "yes")
        self.assertEqual(result["style"], edge.visual_style)

    def test_connect_rejects_unknown_style_keys_before_creating_the_edge(self) -> None:
        start = self.add(START)
        step = self.add(PROCESS, 300, 0)
        before = self.undo_depth()
        error = expect_error(
            self.context,
            "edge.connect",
            {
                "source_node_id": start,
                "source_port": "right",
                "target_node_id": step,
                "target_port": "left",
                "label": "yes",
                "style": {"color": "#ff0000", "bogus": "x", "thickness": 2},
            },
            INVALID_PARAMS,
        )
        self.assertEqual(error.details["unknown"], ["bogus", "thickness"])
        self.assertTrue(any(problem.startswith("style.bogus") and "stroke_color" in problem for problem in error.details["problems"]))
        self.assertIn("stroke_color", error.details["available"])
        self.assertEqual(error.details["aliases"]["color"], "stroke_color")
        self.assertEqual(self.edge_ids(), [])
        self.assertEqual(self.undo_depth(), before)


class EdgeUpdateTests(_HandlerCase):
    def setUp(self) -> None:
        super().setUp()
        self.start = self.add(START)
        self.step = self.add(PROCESS, 300, 0)
        self.edge_id = self.connect(self.start, "right", self.step, "left")["edge_id"]

    def test_update_reports_changed_fields_then_no_effect_on_repeat(self) -> None:
        params = {
            "edge_id": self.edge_id,
            "label": "ok",
            "enabled": False,
            "path_mode": "bezier",
            "display_mode": "faint",
            "style": {"color": "#00ff00"},
        }
        result = self.call_one_undo("edge.update", params)
        self.assertEqual(result["changed"], ["label", "style", "path_mode", "display_mode", "enabled"])
        edge = self.context.require_edge(self.edge_id)
        self.assertEqual(edge.label, "ok")
        self.assertFalse(edge.enabled)
        self.assertEqual(edge.visual_style, {"stroke_color": "#00ff00", "path_mode": "bezier", "display_mode": "faint"})
        self.assertFalse(result["edge"]["enabled"])
        before = self.undo_depth()
        error = expect_error(self.context, "edge.update", params, NO_EFFECT)
        self.assertEqual(error.details["edge_id"], self.edge_id)
        self.assertEqual(self.undo_depth(), before)

    def test_update_rejects_unknown_style_keys_before_any_change(self) -> None:
        before_depth = self.undo_depth()
        error = expect_error(
            self.context,
            "edge.update",
            {"edge_id": self.edge_id, "label": "changed", "enabled": False, "style": {"width": 2, "glow": True}},
            INVALID_PARAMS,
        )
        self.assertEqual(error.details["unknown"], ["glow"])
        edge = self.context.require_edge(self.edge_id)
        self.assertEqual((edge.label, edge.enabled, edge.visual_style), ("", True, {}))
        self.assertEqual(self.undo_depth(), before_depth)

    def test_update_requires_a_field_and_a_known_edge(self) -> None:
        expect_error(self.context, "edge.update", {"edge_id": self.edge_id}, INVALID_PARAMS)
        expect_error(self.context, "edge.update", {"edge_id": self.edge_id, "clear_style": False}, INVALID_PARAMS)
        expect_error(self.context, "edge.update", {"edge_id": "edge_missing", "label": "x"}, NOT_FOUND)

    def test_clear_flags_replace_style_and_drop_label(self) -> None:
        call(self.context, "edge.update", {"edge_id": self.edge_id, "label": "old", "style": {"color": "#123456", "path_mode": "pipe"}})
        replaced = self.call_one_undo("edge.update", {"edge_id": self.edge_id, "clear_style": True, "style": {"width": 2}})
        self.assertEqual(replaced["changed"], ["style", "path_mode"])
        self.assertEqual(self.context.require_edge(self.edge_id).visual_style, {"stroke_width": 2.0})
        cleared = self.call_one_undo("edge.update", {"edge_id": self.edge_id, "clear_label": True, "clear_style": True})
        self.assertEqual(cleared["changed"], ["label", "style"])
        edge = self.context.require_edge(self.edge_id)
        self.assertEqual((edge.label, edge.visual_style), ("", {}))

    def test_path_mode_auto_removes_the_key(self) -> None:
        call(self.context, "edge.update", {"edge_id": self.edge_id, "path_mode": "pipe"})
        result = self.call_one_undo("edge.update", {"edge_id": self.edge_id, "path_mode": "auto"})
        self.assertEqual(result["changed"], ["path_mode"])
        self.assertNotIn("path_mode", self.context.require_edge(self.edge_id).visual_style)

    def test_display_mode_via_param_and_style_key(self) -> None:
        hidden = self.call_one_undo("edge.update", {"edge_id": self.edge_id, "display_mode": "hidden"})
        self.assertEqual(hidden["changed"], ["display_mode"])
        self.assertEqual(self.context.require_edge(self.edge_id).visual_style, {"display_mode": "hidden"})
        via_style = self.call_one_undo("edge.update", {"edge_id": self.edge_id, "style": {"display_mode": "faint", "color": "#abcdef"}})
        self.assertEqual(via_style["changed"], ["style", "display_mode"])
        self.assertEqual(
            self.context.require_edge(self.edge_id).visual_style,
            {"stroke_color": "#abcdef", "display_mode": "faint"},
        )
        default = self.call_one_undo("edge.update", {"edge_id": self.edge_id, "display_mode": "default"})
        self.assertEqual(default["changed"], ["display_mode"])
        self.assertEqual(self.context.require_edge(self.edge_id).visual_style, {"stroke_color": "#abcdef"})


class EdgeDeleteTests(_HandlerCase):
    def test_delete_removes_every_listed_edge_in_one_undo_step(self) -> None:
        start = self.add(START, 0, 0)
        step = self.add(PROCESS, 300, 0)
        end = self.add(PROCESS, 600, 0)
        first = self.connect(start, "right", step, "left")["edge_id"]
        second = self.connect(step, "right", end, "left")["edge_id"]
        expect_error(self.context, "edge.delete", {"edge_ids": [first, "edge_missing"]}, NOT_FOUND)
        self.assertEqual(sorted(self.edge_ids()), sorted([first, second]))
        result = self.call_one_undo("edge.delete", {"edge_ids": [first, second, first]})
        self.assertEqual(result["deleted_edge_ids"], [first, second])
        self.assertEqual(self.edge_ids(), [])


class GroupWrapTests(_HandlerCase):
    def test_wrap_creates_titled_group_backdrop_in_one_undo_step(self) -> None:
        start = self.add(START, 0, 0)
        step = self.add(PROCESS, 300, 0)
        result = self.call_one_undo("group.wrap", {"node_ids": [start, step], "title": "Stage 1"})
        group = self.context.require_node(result["group_node_id"])
        self.assertEqual(group.type_id, GROUP)
        self.assertEqual(group.title, "Stage 1")
        self.assertEqual(group.properties.get("title"), "Stage 1")
        self.assertIsNone(group.parent_node_id)
        self.assertEqual(result["member_node_ids"], [start, step])
        self.assertEqual(result["group"]["title"], "Stage 1")
        expect_error(self.context, "group.wrap", {"node_ids": [start, "node_missing"]}, NOT_FOUND)


class SubnodeLifecycleTests(_HandlerCase):
    def test_create_navigate_add_pin_and_ungroup(self) -> None:
        head = self.add(PROCESS, 0, 400)
        middle = self.add(PROCESS, 300, 400)
        tail = self.add(PROCESS, 600, 400)
        self.connect(head, "right", middle, "left")
        self.connect(middle, "right", tail, "left")

        created = self.call_one_undo("subnode.create", {"node_ids": [middle, tail], "title": "Inner"})
        shell_id = created["shell_node_id"]
        shell = self.context.require_node(shell_id)
        self.assertEqual(shell.type_id, SHELL)
        self.assertEqual(shell.title, "Inner")
        self.assertIsNone(shell.parent_node_id)
        self.assertEqual(sorted(created["member_node_ids"]), sorted([middle, tail]))
        self.assertEqual(len(created["input_pin_ids"]), 1, "the head->middle edge crosses the boundary")
        self.assertEqual(created["output_pin_ids"], [])
        self.assertEqual(self.context.require_node(created["input_pin_ids"][0]).type_id, PIN_IN)
        self.assertEqual(self.context.require_node(middle).parent_node_id, shell_id)

        entered = self.call_no_undo("scope.navigate", {"target": "node", "node_id": shell_id})
        self.assertEqual(entered["scope_path"], [shell_id])
        self.assertEqual(self.context.scope_path(), [shell_id])
        expect_error(self.context, "group.wrap", {"node_ids": [head]}, WRONG_SCOPE)

        pin = self.call_one_undo("subnode.add_pin", {"shell_node_id": shell_id, "direction": "out"})
        pin_node = self.context.require_node(pin["pin_node_id"])
        self.assertEqual((pin_node.type_id, pin_node.parent_node_id), (PIN_OUT, shell_id))
        expect_error(self.context, "subnode.add_pin", {"shell_node_id": head, "direction": "in"}, INVALID_PARAMS)

        parent = self.call_no_undo("scope.navigate", {"target": "parent"})
        self.assertEqual(parent["scope_path"], [])
        expect_error(self.context, "scope.navigate", {"target": "root"}, NO_EFFECT)
        expect_error(self.context, "scope.navigate", {"target": "node", "node_id": head}, INVALID_PARAMS)
        expect_error(self.context, "scope.navigate", {"target": "node", "node_id": "node_missing"}, NOT_FOUND)
        expect_error(self.context, "scope.navigate", {"target": "node"}, INVALID_PARAMS)
        self.call_no_undo("scope.navigate", {"target": "node", "node_id": shell_id})
        self.assertEqual(self.call_no_undo("scope.navigate", {"target": "root"})["scope_path"], [])

        expect_error(self.context, "subnode.ungroup", {"shell_node_id": head}, INVALID_PARAMS)
        ungrouped = self.call_one_undo("subnode.ungroup", {"shell_node_id": shell_id})
        self.assertEqual(sorted(ungrouped["restored_node_ids"]), sorted([middle, tail]))
        self.assertIsNone(self.context.node_or_none(shell_id))
        self.assertIsNone(self.context.node_or_none(pin["pin_node_id"]))
        self.assertIsNone(self.context.require_node(middle).parent_node_id)

    def test_create_requires_two_distinct_nodes(self) -> None:
        node = self.add(PROCESS)
        expect_error(self.context, "subnode.create", {"node_ids": [node, node]}, INVALID_PARAMS)
        expect_error(self.context, "subnode.create", {"node_ids": [node, "node_missing"]}, NOT_FOUND)


class SelectionTests(_HandlerCase):
    def test_replace_add_and_clear_modes(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 300, 0)
        third = self.add(PROCESS, 600, 0)
        self.assertEqual(self.call_no_undo("selection.set", {"node_ids": [first]})["selected_node_ids"], [first])
        added = self.call_no_undo("selection.set", {"node_ids": [second], "mode": "add"})
        self.assertEqual(sorted(added["selected_node_ids"]), sorted([first, second]))
        replaced = self.call_no_undo("selection.set", {"node_ids": [third], "mode": "replace"})
        self.assertEqual(replaced["selected_node_ids"], [third])
        again = self.call_no_undo("selection.set", {"node_ids": [third], "mode": "add"})
        self.assertEqual(again["selected_node_ids"], [third], "adding an already selected node keeps it selected")
        self.assertEqual(self.call_no_undo("selection.set", {"mode": "clear"})["selected_node_ids"], [])
        self.assertEqual(self.context.selected_node_ids(), [])
        expect_error(self.context, "selection.set", {"node_ids": ["node_missing"]}, NOT_FOUND)
        expect_error(self.context, "selection.set", {"node_ids": [], "mode": "replace"}, INVALID_PARAMS)


class LayoutArrangeTests(_HandlerCase):
    def test_align_top_then_distribute_horizontal(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 300, 40)
        third = self.add(PROCESS, 700, 80)
        aligned = self.call_one_undo("layout.arrange", {"node_ids": [first, second, third], "action": "align_top"})
        workspace = self.context.active_workspace()
        tops = {float(workspace.nodes[node_id].y) for node_id in (first, second, third)}
        self.assertEqual(len(tops), 1)
        self.assertTrue(aligned["moved_node_ids"])
        self.assertTrue(set(aligned["moved_node_ids"]) <= {first, second, third})
        repeat = self.call_no_undo("layout.arrange", {"node_ids": [first, second, third], "action": "align_top"})
        self.assertEqual(repeat["moved_node_ids"], [])
        distributed = self.call_one_undo(
            "layout.arrange", {"node_ids": [first, second, third], "action": "distribute_horizontal"}
        )
        self.assertEqual(distributed["moved_node_ids"], [second])
        self.assertEqual(float(workspace.nodes[first].x), 0.0)
        self.assertEqual(float(workspace.nodes[third].x), 700.0)
        self.assertEqual(set(distributed["positions"]), {first, second, third})

    def test_arrange_requires_two_distinct_nodes_in_scope(self) -> None:
        node = self.add(PROCESS)
        expect_error(self.context, "layout.arrange", {"node_ids": [node, node], "action": "align_left"}, INVALID_PARAMS)
        expect_error(self.context, "layout.arrange", {"node_ids": [node, "node_missing"], "action": "align_left"}, NOT_FOUND)


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(self, op: str, params: dict[str, Any] | None = None, **_kwargs: Any) -> dict[str, Any]:
        self.calls.append((op, dict(params or {})))
        return {"ok": True}


class ClientFacadeTests(unittest.TestCase):
    def test_edges_facade_builds_catalog_params(self) -> None:
        client = _RecordingClient()
        api = EdgesApi(client)
        api.connect("a", "right", "b", "left", label="yes", style={"color": "#ff0000"})
        api.update("e", enabled=False, clear_label=True)
        api.set_display_mode("e", "faint")
        api.delete("e")
        api.delete(["e1", "e2"])
        self.assertEqual(
            client.calls,
            [
                (
                    "edge.connect",
                    {
                        "source_node_id": "a",
                        "source_port": "right",
                        "target_node_id": "b",
                        "target_port": "left",
                        "replace_existing": False,
                        "label": "yes",
                        "style": {"color": "#ff0000"},
                    },
                ),
                ("edge.update", {"edge_id": "e", "enabled": False, "clear_label": True}),
                ("edge.update", {"edge_id": "e", "display_mode": "faint"}),
                ("edge.delete", {"edge_ids": ["e"]}),
                ("edge.delete", {"edge_ids": ["e1", "e2"]}),
            ],
        )

    def test_structure_facade_builds_catalog_params(self) -> None:
        client = _RecordingClient()
        api = StructureApi(client)
        api.wrap_group(["a", "b"], title="Stage")
        api.create_subnode(["a", "b"])
        api.add_output_pin("shell")
        api.open_subnode("shell")
        api.navigate_root()
        api.select("a")
        api.clear_selection()
        api.align(["a", "b"], "top")
        api.distribute(["a", "b"], "vertical", snap_to_grid=True)
        api.ungroup_subnode("shell")
        self.assertEqual(
            client.calls,
            [
                ("group.wrap", {"node_ids": ["a", "b"], "title": "Stage"}),
                ("subnode.create", {"node_ids": ["a", "b"]}),
                ("subnode.add_pin", {"shell_node_id": "shell", "direction": "out"}),
                ("scope.navigate", {"target": "node", "node_id": "shell"}),
                ("scope.navigate", {"target": "root"}),
                ("selection.set", {"mode": "replace", "node_ids": ["a"]}),
                ("selection.set", {"mode": "clear"}),
                ("layout.arrange", {"node_ids": ["a", "b"], "action": "align_top", "snap_to_grid": False}),
                ("layout.arrange", {"node_ids": ["a", "b"], "action": "distribute_vertical", "snap_to_grid": True}),
                ("subnode.ungroup", {"shell_node_id": "shell"}),
            ],
        )


if __name__ == "__main__":
    unittest.main()
