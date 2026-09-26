# Purpose: Shell-free handler tests for edge.* and structure ops (connect/update/delete, group.wrap, subnode.*, scope, selection, layout arrange/straighten/tidy) with one-undo-step pins.
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
from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.automation.ops.structure import TIDY_NODE_SKIP_REASONS
from tests.automation.harness import build_context, call, expect_error

START = "passive.flowchart.start"
PROCESS = "passive.flowchart.process"
DECISION = "passive.flowchart.decision"
IF_NODE = "core.if"  # data inputs at different heights: one output wired to two of them cannot be straightened
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

    def test_arrow_and_label_layout_keys_accept_aliases_and_normalise(self) -> None:
        result = self.call_one_undo(
            "edge.update",
            {
                "edge_id": self.edge_id,
                "style": {
                    "start_arrow": "OPEN",
                    "end_arrow": "none",
                    "label_fraction": 1.5,
                    "label_rotation": "follow-path",
                },
            },
        )
        self.assertEqual(result["changed"], ["style"])
        self.assertEqual(
            self.context.require_edge(self.edge_id).visual_style,
            {"arrow_tail": "open", "arrow_head": "none", "label_position": 1.0, "label_orientation": "follow_path"},
        )
        persisted = self.call_one_undo(
            "edge.update",
            {"edge_id": self.edge_id, "style": {"label_position": 0.25, "label_orientation": "horizontal"}},
        )
        self.assertEqual(persisted["changed"], ["style"])
        style = self.context.require_edge(self.edge_id).visual_style
        self.assertEqual(style["label_position"], 0.25)
        self.assertNotIn("label_orientation", style)

    def test_reverse_swaps_endpoints_in_place_as_one_undo_step(self) -> None:
        call(
            self.context,
            "edge.update",
            {"edge_id": self.edge_id, "label": "go\nnow", "style": {"label_position": 0.25, "arrow_tail": "open"}},
        )
        before_ids = self.edge_ids()
        result = self.call_one_undo("edge.update", {"edge_id": self.edge_id, "reverse": True})
        self.assertEqual(result["changed"], ["style", "direction"])
        self.assertEqual(self.edge_ids(), before_ids)
        edge = self.context.require_edge(self.edge_id)
        self.assertEqual(
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key),
            (self.step, "left", self.start, "right"),
        )
        self.assertEqual(edge.label, "go\nnow")
        # The label fraction is measured from the new source, so it mirrors to stay in place.
        self.assertEqual(edge.visual_style, {"label_position": 0.75, "arrow_tail": "open"})
        self.assertEqual(result["edge"]["source_node_id"], self.step)

    def test_reverse_rejects_directed_ports_without_applying_other_fields(self) -> None:
        first = self.add(TRIGGER, 0, 200)
        second = self.add(TRIGGER, 300, 200)
        data_edge = self.connect(first, "output", second, "input")["edge_id"]
        before = self.undo_depth()
        error = expect_error(
            self.context,
            "edge.update",
            {"edge_id": data_edge, "reverse": True, "enabled": False},
            PORT_INCOMPATIBLE,
        )
        self.assertEqual(error.details["reason"], "not_reversible")
        edge = self.context.require_edge(data_edge)
        self.assertEqual((edge.source_node_id, edge.target_node_id), (first, second))
        self.assertTrue(edge.enabled)
        self.assertEqual(self.undo_depth(), before)

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

    def test_wrap_rejects_nodes_hidden_in_a_collapsed_group(self) -> None:
        hidden = self.add(PROCESS, 0, 0)
        visible = self.add(PROCESS, 900, 0)
        collapsed = self.call_one_undo("group.wrap", {"node_ids": [hidden]})["group_node_id"]
        self.assertTrue(self.context.scene.set_node_collapsed(collapsed, True))
        before = self.undo_depth()

        error = expect_error(self.context, "group.wrap", {"node_ids": [hidden, visible]}, INVALID_PARAMS)

        self.assertEqual(error.details["skipped_nodes"], [{"node_id": hidden, "reason": "hidden_in_collapsed_group"}])
        self.assertEqual(self.undo_depth(), before)


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

    def _center(self, node_id: str) -> tuple[float, float]:
        x, y, width, height = self.context.node_bounds(node_id)
        return x + width * 0.5, y + height * 0.5

    def test_align_center_y_lines_up_mixed_height_shapes_and_their_side_ports(self) -> None:
        process = self.add(PROCESS, 0, 0)
        decision = self.add(DECISION, 320, 60)
        edge_id = self.connect(process, "right", decision, "left")["edge_id"]
        self.assertNotEqual(self.context.node_bounds(process)[3], self.context.node_bounds(decision)[3])
        result = self.call_one_undo("layout.arrange", {"node_ids": [process, decision], "action": "align_center_y"})
        self.assertEqual(self._center(process)[1], self._center(decision)[1])
        self.assertEqual(result["resized_node_ids"], [])
        self.assertEqual(result["overlapping_node_pairs"], [])
        row = next(row for row in self.scene.edges_model if row["edge_id"] == edge_id)
        self.assertAlmostEqual(float(row["sy"]), float(row["ty"]), delta=1.0)

    def test_align_center_x_stacks_a_centered_column(self) -> None:
        top = self.add(PROCESS, 0, 0)
        bottom = self.add(DECISION, 90, 200)
        self.call_one_undo("layout.arrange", {"node_ids": [top, bottom], "action": "align_center_x"})
        self.assertEqual(self._center(top)[0], self._center(bottom)[0])

    def test_align_reports_overlapping_pairs(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 100, 300)
        result = self.call_one_undo("layout.arrange", {"node_ids": [first, second], "action": "align_top"})
        self.assertEqual(result["overlapping_node_pairs"], [[first, second]])

    def test_match_width_resizes_same_type_passive_nodes_to_the_first_listed(self) -> None:
        wide = self.add(PROCESS, 0, 0)
        narrow = self.add(PROCESS, 400, 0)
        decision = self.add(DECISION, 800, 0)
        call(self.context, "node.update", {"node_id": wide, "width": 320.0})
        result = self.call_one_undo("layout.arrange", {"node_ids": [wide, narrow, decision], "action": "match_width"})
        self.assertEqual(result["resized_node_ids"], [narrow])
        self.assertEqual(result["reference_node_ids"], {PROCESS: wide})
        self.assertEqual(result["ignored_node_ids"], [decision])
        self.assertEqual(result["sizes"][narrow]["width"], 320.0)
        self.assertEqual(self.context.node_bounds(narrow)[2], 320.0)
        repeat = self.call_no_undo("layout.arrange", {"node_ids": [wide, narrow], "action": "match_width"})
        self.assertEqual(repeat["resized_node_ids"], [])

    def test_center_alignment_ignores_snap_to_grid_so_centers_stay_equal(self) -> None:
        process = self.add(PROCESS, 3, 7)
        decision = self.add(DECISION, 331, 61)
        self.call_one_undo(
            "layout.arrange", {"node_ids": [process, decision], "action": "align_center_y", "snap_to_grid": True}
        )
        self.assertEqual(self._center(process)[1], self._center(decision)[1])

    def test_locked_nodes_are_skipped_and_reported(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 300, 40)
        locked = self.add(PROCESS, 600, 80)
        call(self.context, "node.update", {"node_id": locked, "locked": True})
        result = self.call_one_undo("layout.arrange", {"node_ids": [first, second, locked], "action": "align_top"})
        self.assertEqual(result["skipped_nodes"], [{"node_id": locked, "reason": "locked_node"}])
        self.assertEqual(float(self.context.require_node(locked).y), 80.0)
        error = expect_error(self.context, "layout.arrange", {"node_ids": [first, locked], "action": "align_left"}, INVALID_PARAMS)
        self.assertEqual(error.details["skipped_nodes"], [{"node_id": locked, "reason": "locked_node"}])
        self.assertIn("locked=false", error.hint)
        call(self.context, "node.update", {"node_id": first, "width": 300.0})
        matched = self.call_one_undo("layout.arrange", {"node_ids": [first, second, locked], "action": "match_width"})
        self.assertEqual(matched["resized_node_ids"], [second])
        self.assertNotEqual(self.context.node_bounds(locked)[2], 300.0)

    def test_match_height_needs_a_passive_same_type_pair(self) -> None:
        process = self.add(PROCESS, 0, 0)
        decision = self.add(DECISION, 400, 0)
        error = expect_error(
            self.context, "layout.arrange", {"node_ids": [process, decision], "action": "match_height"}, INVALID_PARAMS
        )
        self.assertEqual(error.details["ignored_node_ids"], [process, decision])
        self.assertIn("node_update", error.hint)


class LayoutStraightenTests(_HandlerCase):
    def _row(self, edge_id: str) -> dict[str, Any]:
        return next(row for row in self.scene.edges_model if row["edge_id"] == edge_id)

    def _jagged_chain(self) -> tuple[list[str], list[str]]:
        first = self.add(PROCESS, 0, 0)
        second = self.add(DECISION, 320, 60)
        third = self.add(PROCESS, 640, 130)
        edges = [
            self.connect(first, "right", second, "left")["edge_id"],
            self.connect(second, "right", third, "left")["edge_id"],
        ]
        return [first, second, third], edges

    def test_straighten_moves_nodes_so_right_to_left_wires_run_level(self) -> None:
        nodes, edges = self._jagged_chain()
        for edge_id in edges:
            row = self._row(edge_id)
            self.assertGreater(abs(float(row["sy"]) - float(row["ty"])), 1.0)
        result = self.call_one_undo("layout.straighten", {"node_ids": nodes})
        self.assertEqual(sorted(result["straightened_edge_ids"]), sorted(edges))
        self.assertEqual(result["skipped_edges"], [])
        self.assertTrue(result["moved_node_ids"])
        self.assertEqual(set(result["positions"]), set(result["moved_node_ids"]))
        for edge_id in edges:
            row = self._row(edge_id)
            self.assertAlmostEqual(float(row["sy"]), float(row["ty"]), delta=1.0)
        repeat = self.call_no_undo("layout.straighten", {"node_ids": nodes})
        self.assertEqual(repeat["moved_node_ids"], [])
        self.assertEqual(sorted(repeat["straightened_edge_ids"]), sorted(edges))

    def test_straighten_by_edge_ids_and_whole_scope_default(self) -> None:
        nodes, edges = self._jagged_chain()
        by_edge = self.call_one_undo("layout.straighten", {"edge_ids": [edges[0]]})
        self.assertEqual(by_edge["straightened_edge_ids"], [edges[0]])
        self.assertTrue(set(by_edge["moved_node_ids"]) <= set(nodes[:2]))
        whole = self.call_one_undo("layout.straighten", {})
        self.assertEqual(sorted(whole["straightened_edge_ids"]), sorted(edges))

    def test_straighten_vertical_wires_align_x(self) -> None:
        upper = self.add(PROCESS, 0, 0)
        lower = self.add(DECISION, 90, 240)
        edge_id = self.connect(upper, "bottom", lower, "top")["edge_id"]
        result = self.call_one_undo("layout.straighten", {"node_ids": [upper, lower]})
        self.assertEqual(result["straightened_edge_ids"], [edge_id])
        row = self._row(edge_id)
        self.assertAlmostEqual(float(row["sx"]), float(row["tx"]), delta=1.0)

    def test_straighten_reports_elbows_and_conflicts(self) -> None:
        source = self.add(PROCESS, 0, 0)
        elbow_target = self.add(PROCESS, 320, 300)
        elbow = self.connect(source, "bottom", elbow_target, "left")["edge_id"]
        result = self.call_no_undo("layout.straighten", {"node_ids": [source, elbow_target]})
        self.assertEqual(result["straightened_edge_ids"], [])
        self.assertEqual(
            result["skipped_edges"],
            [{"edge_id": elbow, "reason": "mixed_port_sides", "source_side": "bottom", "target_side": "left"}],
        )

        trigger = self.add(TRIGGER, 0, 600)
        branch = self.add(IF_NODE, 320, 640)
        conflicting = [
            self.connect(trigger, "output", branch, "condition")["edge_id"],
            self.connect(trigger, "output", branch, "true_value")["edge_id"],
        ]
        conflict = self.call_no_undo("layout.straighten", {"node_ids": [trigger, branch]})
        self.assertEqual(conflict["moved_node_ids"], [])
        self.assertEqual(sorted(entry["edge_id"] for entry in conflict["skipped_edges"]), sorted(conflicting))
        self.assertEqual({entry["reason"] for entry in conflict["skipped_edges"]}, {"unresolved_offset"})
        self.assertTrue(all(entry["offset"] > 1.0 for entry in conflict["skipped_edges"]))

    def test_straighten_leaves_collapsed_group_members_in_place(self) -> None:
        inner_a = self.add(PROCESS, 0, 0)
        inner_b = self.add(PROCESS, 320, 40)
        outer = self.add(PROCESS, 320, 900)
        hidden_wire = self.connect(inner_a, "right", inner_b, "left")["edge_id"]
        exit_wire = self.connect(inner_b, "bottom", outer, "top")["edge_id"]
        group = call(self.context, "group.wrap", {"node_ids": [inner_a, inner_b]})["group_node_id"]
        call(self.context, "node.update", {"node_id": group, "collapsed": True})
        positions = {node_id: (self.context.require_node(node_id).x, self.context.require_node(node_id).y) for node_id in (inner_a, inner_b)}
        result = self.call_no_undo("layout.straighten", {})
        for node_id, position in positions.items():
            node = self.context.require_node(node_id)
            self.assertEqual((node.x, node.y), position, "hidden members must not be dragged out of their group")
        reasons = {entry["edge_id"]: entry["reason"] for entry in result["skipped_edges"]}
        self.assertEqual(reasons, {hidden_wire: "hidden_in_collapsed_group", exit_wire: "hidden_in_collapsed_group"})

    def test_straighten_reports_locked_ends(self) -> None:
        first = self.add(PROCESS, 0, 0)
        locked = self.add(PROCESS, 320, 100)
        edge_id = self.connect(first, "right", locked, "left")["edge_id"]
        call(self.context, "node.update", {"node_id": locked, "locked": True})
        result = self.call_no_undo("layout.straighten", {"edge_ids": [edge_id]})
        self.assertEqual(result["moved_node_ids"], [])
        self.assertEqual(result["skipped_edges"], [{"edge_id": edge_id, "reason": "locked_node", "node_id": locked}])

    def test_straighten_rejects_unwired_or_unknown_targets(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 300, 0)
        error = expect_error(self.context, "layout.straighten", {"node_ids": [first, second]}, INVALID_PARAMS)
        self.assertIn("no edge connects", error.message)
        expect_error(self.context, "layout.straighten", {"node_ids": ["node_missing"]}, NOT_FOUND)
        expect_error(self.context, "layout.straighten", {"edge_ids": ["edge_missing"]}, NOT_FOUND)
        expect_error(self.context, "layout.straighten", {"node_ids": []}, INVALID_PARAMS)


class _NoPushPreferences(QObject):
    graphics_preferences_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.graphics_expand_collision_avoidance = {"enabled": False}


class LayoutTidyTests(_HandlerCase):
    def _row(self, edge_id: str) -> dict[str, Any]:
        return next(row for row in self.scene.edges_model if row["edge_id"] == edge_id)

    def _center(self, node_id: str) -> tuple[float, float]:
        x, y, width, height = self.context.node_bounds(node_id)
        return x + width * 0.5, y + height * 0.5

    def _position(self, node_id: str) -> tuple[float, float]:
        node = self.context.require_node(node_id)
        return float(node.x), float(node.y)

    def _jagged_chain(self) -> tuple[list[str], list[str]]:
        first = self.add(PROCESS, 0, 0)
        second = self.add(DECISION, 400, 90)
        third = self.add(PROCESS, 700, -60)
        edges = [
            self.connect(first, "right", second, "left")["edge_id"],
            self.connect(second, "right", third, "left")["edge_id"],
        ]
        return [first, second, third], edges

    def test_tidy_lays_a_jagged_chain_out_left_to_right_in_one_undo_step(self) -> None:
        nodes, edges = self._jagged_chain()
        result = self.call_one_undo("layout.tidy", {"node_ids": nodes})
        self.assertTrue(result["changed"])
        self.assertEqual((result["mode"], result["direction"]), ("auto_layout", "left_to_right"))
        self.assertEqual(result["arranged_node_ids"], sorted(nodes))
        self.assertTrue(result["moved_node_ids"])
        self.assertTrue(set(result["moved_node_ids"]) <= set(nodes))
        self.assertEqual(set(result["positions"]), set(result["moved_node_ids"]))
        self.assertEqual(sorted(result["straightened_edge_ids"]), sorted(edges))
        empty_keys = (
            "skipped_edges",
            "skipped_nodes",
            "loop_edge_ids",
            "pushed_node_ids",
            "membership_conflict_node_ids",
            "overlapping_node_pairs",
        )
        for key in empty_keys:
            with self.subTest(key=key):
                self.assertEqual(result[key], [])
        centers = [self._center(node_id) for node_id in nodes]
        self.assertAlmostEqual(centers[0][1], centers[1][1], delta=0.01)
        self.assertAlmostEqual(centers[1][1], centers[2][1], delta=0.01)
        self.assertLess(centers[0][0], centers[1][0])
        self.assertLess(centers[1][0], centers[2][0])
        for edge_id in edges:
            row = self._row(edge_id)
            self.assertAlmostEqual(float(row["sy"]), float(row["ty"]), delta=1.0)
        repeat = self.call_no_undo("layout.tidy", {"node_ids": nodes})
        self.assertFalse(repeat["changed"])
        self.assertEqual(repeat["moved_node_ids"], [])
        self.assertEqual(sorted(repeat["straightened_edge_ids"]), sorted(edges))

    def test_tidy_passes_column_and_row_gaps_through(self) -> None:
        source = self.add(PROCESS, 0, 0)
        advance = self.add(PROCESS, 500, 70)
        branch = self.add(PROCESS, 60, 420)
        self.connect(source, "right", advance, "left")
        branch_edge = self.connect(source, "bottom", branch, "top")["edge_id"]
        result = self.call_one_undo("layout.tidy", {"node_ids": [source, advance, branch], "column_gap": 150, "row_gap": 100})
        self.assertEqual(result["direction"], "left_to_right")
        sx, sy, sw, sh = self.context.node_bounds(source)
        ax, _ay, _aw, _ah = self.context.node_bounds(advance)
        _bx, by, _bw, _bh = self.context.node_bounds(branch)
        self.assertAlmostEqual(ax - (sx + sw), 150.0, delta=0.01)
        self.assertAlmostEqual(by - (sy + sh), 100.0, delta=0.01)
        self.assertAlmostEqual(self._center(source)[0], self._center(branch)[0], delta=0.01)
        self.assertIn(branch_edge, result["straightened_edge_ids"])

    def test_tidy_top_to_bottom_stacks_a_vertical_chain_in_one_column(self) -> None:
        upper = self.add(PROCESS, 0, 0)
        middle = self.add(DECISION, 90, 260)
        lower = self.add(PROCESS, -60, 520)
        edges = [
            self.connect(upper, "bottom", middle, "top")["edge_id"],
            self.connect(middle, "bottom", lower, "top")["edge_id"],
        ]
        nodes = [upper, middle, lower]
        result = self.call_one_undo("layout.tidy", {"node_ids": nodes, "direction": "top_to_bottom"})
        self.assertEqual(result["direction"], "top_to_bottom")
        centers = [self._center(node_id) for node_id in nodes]
        self.assertAlmostEqual(centers[0][0], centers[1][0], delta=0.01)
        self.assertAlmostEqual(centers[1][0], centers[2][0], delta=0.01)
        self.assertLess(centers[0][1], centers[1][1])
        self.assertLess(centers[1][1], centers[2][1])
        self.assertEqual(sorted(result["straightened_edge_ids"]), sorted(edges))
        for edge_id in edges:
            row = self._row(edge_id)
            self.assertAlmostEqual(float(row["sx"]), float(row["tx"]), delta=1.0)
        # The default direction detects top_to_bottom from the bottom->top wires, so nothing moves again.
        repeat = self.call_no_undo("layout.tidy", {"node_ids": nodes})
        self.assertEqual((repeat["direction"], repeat["changed"]), ("top_to_bottom", False))

    def test_tidy_in_place_snaps_a_jittered_grid_onto_shared_centers(self) -> None:
        rows = (
            [self.add(PROCESS, 0, 0), self.add(PROCESS, 330, 14), self.add(PROCESS, 650, -9)],
            [self.add(PROCESS, 12, 220), self.add(PROCESS, 318, 205), self.add(PROCESS, 661, 231)],
        )
        nodes = [node_id for row in rows for node_id in row]
        result = self.call_one_undo("layout.tidy", {"node_ids": nodes, "mode": "in_place"})
        self.assertEqual((result["mode"], result["direction"]), ("in_place", ""))
        self.assertTrue(result["changed"])
        for row in rows:
            centers = [self._center(node_id) for node_id in row]
            self.assertEqual(len({round(center_y, 3) for _center_x, center_y in centers}), 1, "a row shares one center line")
            self.assertEqual([center_x for center_x, _center_y in centers], sorted(center_x for center_x, _center_y in centers))
        for column in zip(*rows):
            self.assertEqual(len({round(self._center(node_id)[0], 3) for node_id in column}), 1, "a column shares one center line")
        self.assertLess(self._center(rows[0][0])[1], self._center(rows[1][0])[1])

    def test_tidy_defaults_to_the_whole_scope_and_reports_locked_nodes(self) -> None:
        nodes, edges = self._jagged_chain()
        locked = self.add(PROCESS, 0, 900)
        call(self.context, "node.update", {"node_id": locked, "locked": True})
        result = self.call_one_undo("layout.tidy", {})
        self.assertEqual(result["arranged_node_ids"], sorted(nodes))
        self.assertEqual(result["skipped_nodes"], [{"node_id": locked, "reason": "locked_node"}])
        self.assertEqual(self._position(locked), (0.0, 900.0))
        self.assertEqual(sorted(result["straightened_edge_ids"]), sorted(edges))

    def test_tidy_keeps_group_members_inside_their_refitted_backdrop(self) -> None:
        inner_a = self.add(PROCESS, 0, 0)
        inner_b = self.add(PROCESS, 330, 70)
        outer = self.add(PROCESS, 900, 400)
        inner_wire = self.connect(inner_a, "right", inner_b, "left")["edge_id"]
        self.connect(inner_b, "right", outer, "left")
        group = call(self.context, "group.wrap", {"node_ids": [inner_a, inner_b]})["group_node_id"]
        result = self.call_one_undo("layout.tidy", {})
        self.assertEqual(set(result["arranged_node_ids"]), {inner_a, inner_b, outer, group})
        self.assertIn(group, result["resized_group_ids"])
        self.assertIn(inner_wire, result["straightened_edge_ids"])
        self.assertEqual(result["overlapping_node_pairs"], [])
        row = next(row for row in self.scene.backdrop_nodes_model if row["node_id"] == group)
        self.assertEqual(sorted(row["member_node_ids"]), sorted([inner_a, inner_b]))
        gx, gy, gw, gh = self.context.node_bounds(group)
        for node_id in (inner_a, inner_b):
            x, y, w, h = self.context.node_bounds(node_id)
            self.assertTrue(gx <= x and gy <= y and x + w <= gx + gw and y + h <= gy + gh, f"{node_id} left the Group")
        ox, oy, ow, oh = self.context.node_bounds(outer)
        self.assertFalse(ox < gx + gw and ox + ow > gx and oy < gy + gh and oy + oh > gy, "outer node overlaps the Group")

    def test_tidy_moves_a_collapsed_group_with_its_hidden_members(self) -> None:
        feeder = self.add(PROCESS, -400, -500)
        inner_a = self.add(PROCESS, 0, 0)
        inner_b = self.add(PROCESS, 320, 40)
        self.connect(feeder, "right", inner_a, "left")
        self.connect(inner_a, "right", inner_b, "left")
        group = call(self.context, "group.wrap", {"node_ids": [inner_a, inner_b]})["group_node_id"]
        call(self.context, "node.update", {"node_id": group, "collapsed": True})
        before = {node_id: self._position(node_id) for node_id in (group, inner_a, inner_b)}
        members_before = next(row for row in self.scene.backdrop_nodes_model if row["node_id"] == group)["member_node_ids"]
        self.assertEqual(sorted(members_before), sorted([inner_a, inner_b]))
        result = self.call_one_undo("layout.tidy", {})
        self.assertEqual(result["skipped_nodes"], [], "hidden members of a tidied collapsed Group are not skipped")
        self.assertIn(group, result["arranged_node_ids"])
        self.assertTrue({group, inner_a, inner_b} <= set(result["moved_node_ids"]))
        after = {node_id: self._position(node_id) for node_id in before}
        delta = (after[group][0] - before[group][0], after[group][1] - before[group][1])
        for node_id in (inner_a, inner_b):
            with self.subTest(node_id=node_id):
                self.assertAlmostEqual(after[node_id][0] - before[node_id][0], delta[0], delta=0.01)
                self.assertAlmostEqual(after[node_id][1] - before[node_id][1], delta[1], delta=0.01)
                self.assertEqual(result["positions"][node_id], {"x": after[node_id][0], "y": after[node_id][1]})
        row = next(row for row in self.scene.backdrop_nodes_model if row["node_id"] == group)
        self.assertEqual(sorted(row["member_node_ids"]), sorted([inner_a, inner_b]))
        # A hidden member listed together with its collapsed Group moves with the Group, so it is not skipped.
        repeat = self.call_no_undo("layout.tidy", {"node_ids": [feeder, group, inner_a]})
        self.assertEqual((repeat["changed"], repeat["skipped_nodes"]), (False, []))

    def test_tidy_reports_groups_that_hold_a_locked_node(self) -> None:
        free = self.add(PROCESS, 0, 0)
        held = self.add(PROCESS, 330, 60)
        group = call(self.context, "group.wrap", {"node_ids": [free, held]})["group_node_id"]
        call(self.context, "node.update", {"node_id": held, "locked": True})
        first = self.add(PROCESS, 0, 700)
        second = self.add(PROCESS, 330, 760)
        self.connect(first, "right", second, "left")
        fixed = {node_id: self._position(node_id) for node_id in (free, held, group)}
        result = self.call_one_undo("layout.tidy", {})
        self.assertEqual(result["arranged_node_ids"], sorted([first, second]))
        reasons = {entry["node_id"]: entry["reason"] for entry in result["skipped_nodes"]}
        self.assertEqual(reasons, {held: "locked_node", free: "locked_group", group: "locked_group"})
        self.assertTrue(set(reasons.values()) <= set(TIDY_NODE_SKIP_REASONS))
        for node_id, position in fixed.items():
            self.assertEqual(self._position(node_id), position, f"{node_id} belongs to a fixed Group")

    def test_tidy_refuses_to_move_nodes_into_a_group(self) -> None:
        # With "avoid overlaps" off nothing is pushed aside, so the member-less backdrop covering the spot
        # auto-layout gives the target would swallow it: the membership guard rejects the whole tidy.
        preferences = _NoPushPreferences()
        self.scene.bind_graphics_preferences_source(preferences)
        source = self.add(PROCESS, 0, 0)
        target = self.add(PROCESS, 2600, 40)
        self.connect(source, "right", target, "left")
        backdrop = self.add(GROUP, 200, -300)
        call(self.context, "node.update", {"node_id": backdrop, "width": 2000.0, "height": 800.0})
        before = {node_id: self._position(node_id) for node_id in (source, target, backdrop)}
        depth = self.undo_depth()
        error = expect_error(self.context, "layout.tidy", {"node_ids": [source, target]}, NO_EFFECT)
        self.assertEqual(error.details["membership_conflict_node_ids"], [target])
        self.assertEqual(error.details["op"], "layout.tidy")
        self.assertIn("into or out of a Group", error.message)
        self.assertEqual(self.undo_depth(), depth)
        self.assertEqual({node_id: self._position(node_id) for node_id in before}, before)

    def test_tidy_keeps_the_new_block_off_a_locked_backdrop(self) -> None:
        source = self.add(PROCESS, 0, 0)
        target = self.add(PROCESS, 2600, 40)
        self.connect(source, "right", target, "left")
        # A locked backdrop is never pushed, so the tidied block itself steps around it instead of landing inside.
        backdrop = self.add(GROUP, 200, -300)
        call(self.context, "node.update", {"node_id": backdrop, "width": 2000.0, "height": 800.0, "locked": True})
        backdrop_before = self.context.node_bounds(backdrop)
        result = self.call_one_undo("layout.tidy", {"node_ids": [source, target]})
        self.assertEqual(result["membership_conflict_node_ids"], [])
        self.assertEqual(self.context.node_bounds(backdrop), backdrop_before)
        bx, by, bw, bh = backdrop_before
        for node_id in (source, target):
            x, y, w, h = self.context.node_bounds(node_id)
            self.assertFalse(x < bx + bw and x + w > bx and y < by + bh and y + h > by, f"{node_id} overlaps the backdrop")
        self.assertAlmostEqual(self._center(source)[1], self._center(target)[1], delta=0.01)

    def test_tidy_explains_nodes_that_sit_on_different_group_levels(self) -> None:
        outside = self.add(PROCESS, 0, 0)
        member = self.add(PROCESS, 600, 300)
        other_member = self.add(PROCESS, 600, 600)
        call(self.context, "group.wrap", {"node_ids": [member, other_member]})
        self.connect(outside, "right", member, "left")
        depth = self.undo_depth()
        error = expect_error(self.context, "layout.tidy", {"node_ids": [outside, member]}, INVALID_PARAMS)
        self.assertEqual(error.message, "layout.tidy: no two of the given nodes can be laid out together.")
        self.assertIn("Group backdrop", error.hint)
        self.assertEqual(error.details, {"skipped_nodes": []})
        self.assertEqual(self.undo_depth(), depth)

    def test_tidy_needs_two_usable_nodes_and_valid_params(self) -> None:
        first = self.add(PROCESS, 0, 0)
        locked = self.add(PROCESS, 320, 100)
        call(self.context, "node.update", {"node_id": locked, "locked": True})
        depth = self.undo_depth()
        error = expect_error(self.context, "layout.tidy", {"node_ids": [first, locked]}, INVALID_PARAMS)
        self.assertEqual(error.message, "layout.tidy: fewer than two nodes can be tidied.")
        self.assertIn("details.skipped_nodes", error.hint)
        self.assertEqual(error.details, {"skipped_nodes": [{"node_id": locked, "reason": "locked_node"}]})
        self.assertEqual(self.undo_depth(), depth)
        self.assertEqual(self._position(first), (0.0, 0.0))
        expect_error(self.context, "layout.tidy", {"node_ids": [first]}, INVALID_PARAMS)
        expect_error(self.context, "layout.tidy", {"node_ids": [first, "node_missing"]}, NOT_FOUND)
        expect_error(self.context, "layout.tidy", {"mode": "sideways"}, INVALID_PARAMS)
        expect_error(self.context, "layout.tidy", {"column_gap": 8}, INVALID_PARAMS)


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
        api.reverse("e")
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
                ("edge.update", {"edge_id": "e", "reverse": True}),
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
        api.align(["a", "b"], "center_y")
        api.match_size(["a", "b"], "width")
        api.straighten()
        api.straighten(["a", "b"], edge_ids="e")
        api.tidy()
        api.tidy(["a", "b"], mode="in_place")
        api.tidy("a", direction="top_to_bottom", column_gap=120, row_gap=48)
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
                ("layout.arrange", {"node_ids": ["a", "b"], "action": "align_center_y", "snap_to_grid": False}),
                ("layout.arrange", {"node_ids": ["a", "b"], "action": "match_width"}),
                ("layout.straighten", {}),
                ("layout.straighten", {"node_ids": ["a", "b"], "edge_ids": ["e"]}),
                ("layout.tidy", {"mode": "auto_layout", "direction": "auto"}),
                ("layout.tidy", {"mode": "in_place", "direction": "auto", "node_ids": ["a", "b"]}),
                (
                    "layout.tidy",
                    {"mode": "auto_layout", "direction": "top_to_bottom", "node_ids": ["a"], "column_gap": 120.0, "row_gap": 48.0},
                ),
                ("subnode.ungroup", {"shell_node_id": "shell"}),
            ],
        )


if __name__ == "__main__":
    unittest.main()
