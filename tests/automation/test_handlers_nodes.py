# Purpose: Shell-free handler tests for node.*, catalog.*, and graph.* automation ops (creation, title trap, update diffing, styles, delete/duplicate, reads) with one-undo-step pins.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_nodes.py
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname

from ea_node_editor.automation.client_api.catalog import CatalogApi
from ea_node_editor.automation.client_api.graph import GraphApi
from ea_node_editor.automation.client_api.nodes import NodesApi
from ea_node_editor.automation.errors import (
    INVALID_PARAMS,
    NO_EFFECT,
    NOT_FOUND,
    NOT_PASSIVE,
    PROPERTY_LOCKED_BY_PORT,
    UNKNOWN_NODE_TYPE,
    WRONG_SCOPE,
    WRONG_WORKSPACE,
)
from tests.automation.harness import build_context, call, expect_error

START = "passive.flowchart.start"
PROCESS = "passive.flowchart.process"
TEXT = "passive.annotation.text"
CONSTANT = "core.constant"  # cheap active node with a real title and a json property
MEDIA = "media.panel"
WEB = "web.page_viewer"
CARD = "passive.flowchart.card"  # flowchart family, but body is separate content (default '')
STICKY = "passive.annotation.sticky_note"
GROUP = "passive.annotation.group_backdrop"


class _RecordingClient:
    """Stand-in for CorexClient.call: records (op, params) and answers with a stub."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(self, op: str, params: dict[str, Any] | None = None, **_kwargs: Any) -> dict[str, Any]:
        self.calls.append((op, dict(params or {})))
        return {"ok": True}


class _NodeHandlerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene

    def undo_depth(self) -> int:
        return self.context.runtime_history.undo_depth(self.context.workspace_id())

    def call_one_undo(self, op: str, params: dict[str, Any]) -> dict[str, Any]:
        before = self.undo_depth()
        result = call(self.context, op, params)
        self.assertEqual(self.undo_depth(), before + 1, f"{op} must record exactly one undo entry")
        return result

    def call_no_undo(self, op: str, params: dict[str, Any]) -> dict[str, Any]:
        before = self.undo_depth()
        result = call(self.context, op, params)
        self.assertEqual(self.undo_depth(), before, f"{op} must not record an undo entry")
        return result

    def add(self, type_id: str, x: float = 0.0, y: float = 0.0, **extra: Any) -> str:
        return self.call_one_undo("node.add", {"type_id": type_id, "x": x, "y": y, **extra})["node_id"]

    def node(self, node_id: str):  # noqa: ANN201 - NodeInstance
        return self.context.require_node(node_id)


class NodeAddTests(_NodeHandlerCase):
    def test_add_passive_node_applies_title_size_and_returns_summary(self) -> None:
        result = self.call_one_undo(
            "node.add", {"type_id": PROCESS, "x": 320, "y": 120, "title": "Mesh the part", "width": 320, "height": 140}
        )
        node = self.node(result["node_id"])
        # Title trap: flowchart titles live in properties["title"]; node.title is a synced mirror.
        self.assertEqual(node.title, "Mesh the part")
        self.assertEqual(node.properties["title"], "Mesh the part")
        summary = result["node"]
        self.assertEqual(summary["type_id"], PROCESS)
        self.assertEqual((summary["x"], summary["y"]), (320.0, 120.0))
        self.assertEqual((summary["width"], summary["height"]), (320.0, 140.0))
        self.assertEqual(summary["runtime_behavior"], "passive")
        self.assertEqual(summary["parent_node_id"], "")
        json.dumps(result)

    def test_add_active_node_uses_initial_title_and_select_flag(self) -> None:
        result = self.call_one_undo("node.add", {"type_id": CONSTANT, "x": 0, "y": 0, "title": "K", "select": True})
        self.assertEqual(self.node(result["node_id"]).title, "K")
        self.assertEqual(self.context.selected_node_ids(), [result["node_id"]])
        unselected = self.call_one_undo("node.add", {"type_id": CONSTANT, "x": 0, "y": 200})
        self.assertNotIn(unselected["node_id"], self.context.selected_node_ids())

    def test_add_property_overrides_and_errors(self) -> None:
        result = self.call_one_undo(
            "node.add", {"type_id": "io.path_pointer", "x": 0, "y": 0, "properties": {"path": "C:/data", "mode": "folder"}}
        )
        node = self.node(result["node_id"])
        self.assertEqual(node.properties["mode"], "folder")
        self.assertEqual(node.properties["path"], "C:/data")
        error = expect_error(self.context, "node.add", {"type_id": "passive.flowchart.proces", "x": 0, "y": 0}, UNKNOWN_NODE_TYPE)
        self.assertIn(PROCESS, error.details["suggestions"])
        expect_error(self.context, "node.add", {"type_id": PROCESS, "x": 0, "y": 0, "properties": {"nope": 1}}, INVALID_PARAMS)
        expect_error(self.context, "node.add", {"type_id": PROCESS, "x": 0, "y": 0, "title": "  "}, INVALID_PARAMS)
        anchor = self.add(START)
        error = expect_error(self.context, "node.add", {"type_id": PROCESS, "x": 0, "y": 0, "parent_node_id": anchor}, WRONG_SCOPE)
        self.assertEqual(error.details["parent_node_id"], anchor)
        expect_error(self.context, "node.add", {"type_id": PROCESS, "x": 0, "y": 0, "parent_node_id": "node_missing"}, NOT_FOUND)

    def test_add_text_stores_markdown_format_and_style(self) -> None:
        result = self.call_one_undo(
            "node.add_text",
            {"markdown": "# Hello", "x": 10, "y": 20, "format": "plain", "style": {"color": "#ff0000", "font_size": 24, "italic": True}},
        )
        node = self.node(result["node_id"])
        self.assertEqual(node.type_id, TEXT)
        self.assertEqual(result["content_key"], "text")
        self.assertEqual(node.properties["text"], "# Hello")
        self.assertEqual(node.properties["format"], "plain")
        self.assertEqual(node.properties["text_color"], "#FF0000")
        self.assertEqual(node.properties["font_size"], 24)
        self.assertTrue(node.properties["italic"])
        expect_error(self.context, "node.add_text", {"markdown": "x", "x": 0, "y": 0, "style": {"bogus": 1}}, INVALID_PARAMS)
        expect_error(self.context, "node.add_text", {"markdown": "x", "x": 0, "y": 0, "style": {"format": "html"}}, INVALID_PARAMS)

    def test_add_media_without_project_session_keeps_absolute_path(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="corex_t05_"))
        image = folder / "pic.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)
        result = self.call_one_undo("node.add_media", {"path": str(image), "x": 5, "y": 6, "fit_mode": "cover", "show_frame": False})
        node = self.node(result["node_id"])
        self.assertEqual(node.type_id, MEDIA)
        self.assertEqual(Path(node.properties["source"]), image.resolve())
        self.assertEqual(result["artifact_ref"], "")
        self.assertEqual(node.properties["fit_mode"], "cover")
        self.assertFalse(node.properties["show_frame"])
        # The authored source is not port-driven: the input port starts unexposed like canvas import.
        self.assertFalse(node.exposed_ports["source"])
        expect_error(self.context, "node.add_media", {"path": str(folder / "missing.png"), "x": 0, "y": 0}, INVALID_PARAMS)
        expect_error(self.context, "node.add_media", {"path": str(image), "x": 0, "y": 0, "fit_mode": "stretchy"}, INVALID_PARAMS)

    def test_add_web_panel_url_xor_html(self) -> None:
        by_url = self.call_one_undo("node.add_web_panel", {"x": 0, "y": 0, "url": "https://example.com", "display_mode": "fit_page"})
        node = self.node(by_url["node_id"])
        self.assertEqual(node.type_id, WEB)
        self.assertEqual(node.properties["start_location"], "https://example.com")
        self.assertEqual(node.properties["display_mode"], "fit_page")
        self.assertEqual(by_url["url"], "https://example.com")
        by_html = self.call_one_undo("node.add_web_panel", {"x": 0, "y": 400, "html": "<h1>Hi</h1>"})
        self.assertTrue(by_html["url"].startswith("file:"))
        staged = Path(url2pathname(urlparse(by_html["url"]).path))
        self.assertTrue(staged.is_file())
        self.assertEqual(staged.read_text(encoding="utf-8"), "<h1>Hi</h1>")
        self.assertEqual(self.node(by_html["node_id"]).properties["start_location"], by_html["url"])
        expect_error(self.context, "node.add_web_panel", {"x": 0, "y": 0}, INVALID_PARAMS)
        expect_error(self.context, "node.add_web_panel", {"x": 0, "y": 0, "url": "https://x", "html": "<p>"}, INVALID_PARAMS)
        expect_error(self.context, "node.add_web_panel", {"x": 0, "y": 0, "html": "   "}, INVALID_PARAMS)
        expect_error(self.context, "node.add_web_panel", {"x": 0, "y": 0, "url": "https://x", "display_mode": "bogus"}, INVALID_PARAMS)


class NodeUpdateTests(_NodeHandlerCase):
    def test_title_update_is_verified_for_passive_and_active_nodes(self) -> None:
        passive = self.add(PROCESS, title="Mesh")
        result = self.call_one_undo("node.update", {"node_id": passive, "title": "Mesh the part"})
        # The in-shape label (body) of a flowchart shape follows its title (F15).
        self.assertEqual(result["changed"], ["title", "properties.body", "properties.title"])
        node = self.node(passive)
        self.assertEqual((node.title, node.properties["title"]), ("Mesh the part", "Mesh the part"))
        self.assertEqual(node.properties["body"], "Mesh the part")
        self.assertEqual(result["node"]["title"], "Mesh the part")
        active = self.add(CONSTANT, title="K")
        result = self.call_one_undo("node.update", {"node_id": active, "title": "K2"})
        self.assertEqual(result["changed"], ["title"])
        self.assertEqual(self.node(active).title, "K2")
        expect_error(self.context, "node.update", {"node_id": passive, "title": "Mesh the part"}, NO_EFFECT)
        expect_error(self.context, "node.update", {"node_id": passive, "title": ""}, INVALID_PARAMS)
        expect_error(self.context, "node.update", {"node_id": passive}, INVALID_PARAMS)
        expect_error(self.context, "node.update", {"node_id": "node_missing", "title": "x"}, NOT_FOUND)

    def test_geometry_collapse_and_lock_updates(self) -> None:
        node_id = self.add(PROCESS, x=300, y=0)
        result = self.call_one_undo("node.update", {"node_id": node_id, "x": 310, "width": 400, "height": 200})
        self.assertEqual(result["changed"], ["x", "width", "height"])
        node = self.node(node_id)
        self.assertEqual((node.x, node.y), (310.0, 0.0))
        self.assertEqual((node.custom_width, node.custom_height), (400.0, 200.0))
        self.assertEqual(self.context.node_bounds(node_id), (310.0, 0.0, 400.0, 200.0))
        result = self.call_one_undo("node.update", {"node_id": node_id, "y": 50})
        self.assertEqual(result["changed"], ["y"])
        error = expect_error(self.context, "node.update", {"node_id": node_id, "collapsed": True}, NO_EFFECT)
        self.assertIn("not collapsible", " ".join(error.details["reasons"]))
        result = self.call_one_undo("node.update", {"node_id": node_id, "locked": True})
        self.assertEqual(result["changed"], ["locked"])
        self.assertTrue(self.node(node_id).locked)
        active = self.add(CONSTANT)
        error = expect_error(self.context, "node.update", {"node_id": active, "locked": True}, NO_EFFECT)
        self.assertIn("passive", " ".join(error.details["reasons"]))

    def test_sizes_are_drawn_sizes_in_a_view_that_hides_optional_ports(self) -> None:
        viewer = self.add(WEB)
        self.assertTrue(self.scene.set_hide_optional_ports(True))
        result = self.call_one_undo("node.update", {"node_id": viewer, "height": 400})
        self.assertEqual(result["changed"], ["height"])
        self.assertEqual(result["node"]["height"], 400.0)
        # A width-only update keeps the height the node is drawn at.
        result = self.call_one_undo("node.update", {"node_id": viewer, "width": 500})
        self.assertEqual(result["changed"], ["width"])
        self.assertEqual(self.context.node_bounds(viewer)[2:], (500.0, 400.0))

    def test_property_updates_diff_and_reject_unknown_keys(self) -> None:
        node_id = self.add(PROCESS)
        result = self.call_one_undo("node.update", {"node_id": node_id, "properties": {"body": "Do it"}})
        self.assertEqual(result["changed"], ["properties.body"])
        self.assertEqual(self.node(node_id).properties["body"], "Do it")
        expect_error(self.context, "node.update", {"node_id": node_id, "properties": {"body": "Do it"}}, NO_EFFECT)
        error = expect_error(self.context, "node.update", {"node_id": node_id, "properties": {"zzz": 1}}, INVALID_PARAMS)
        self.assertIn("body", error.details["available"])
        active = self.add(CONSTANT)
        result = self.call_one_undo("node.update", {"node_id": active, "properties": {"value": {"value": 5}}})
        self.assertEqual(result["changed"], ["properties.value"])
        self.assertEqual(self.node(active).properties["value"], {"value": 5})

    def test_port_driven_property_is_locked_until_port_is_unexposed(self) -> None:
        media = self.add(MEDIA)  # plain node.add keeps the media source port exposed (UI default)
        self.assertTrue(self.node(media).exposed_ports["source"])
        error = expect_error(self.context, "node.update", {"node_id": media, "properties": {"source": "C:/x.png"}}, PROPERTY_LOCKED_BY_PORT)
        self.assertEqual(error.details["keys"], ["source"])
        result = self.call_one_undo("node.update", {"node_id": media, "exposed_ports": {"source": False}})
        self.assertIn("exposed_ports.source", result["changed"])
        result = self.call_one_undo("node.update", {"node_id": media, "properties": {"source": "C:/x.png"}})
        self.assertEqual(result["changed"], ["properties.source"])
        # A connected input port also locks the property it drives.
        constant = self.add(CONSTANT, x=-300)
        self.scene.set_exposed_port(media, "source", True)
        self.scene.add_edge(constant, "value", media, "source")
        self.assertEqual(len(self.context.incident_edges(media)), 1)
        expect_error(self.context, "node.update", {"node_id": media, "properties": {"source": "C:/y.png"}}, PROPERTY_LOCKED_BY_PORT)

    def test_port_labels_require_existing_ports(self) -> None:
        node_id = self.add(PROCESS)
        result = self.call_one_undo("node.update", {"node_id": node_id, "port_labels": {"right": "yes"}})
        self.assertEqual(result["changed"], ["port_labels.right"])
        self.assertEqual(self.node(node_id).port_labels["right"], "yes")
        result = self.call_one_undo("node.update", {"node_id": node_id, "port_labels": {"right": ""}})
        self.assertEqual(result["changed"], ["port_labels.right"])
        self.assertNotIn("right", self.node(node_id).port_labels)
        error = expect_error(self.context, "node.update", {"node_id": node_id, "port_labels": {"nope": "x"}}, NOT_FOUND)
        self.assertEqual(sorted(error.details["available"]), ["bottom", "left", "right", "top"])
        expect_error(self.context, "node.update", {"node_id": node_id, "exposed_ports": {"nope": True}}, NOT_FOUND)


class NodeUpdateAtomicityTests(_NodeHandlerCase):
    """A rejected node.update validates before its first mutation: node untouched, no undo entry."""

    @staticmethod
    def _state(node: Any) -> dict[str, Any]:
        return {
            "title": node.title,
            "x": node.x,
            "y": node.y,
            "size": (node.custom_width, node.custom_height),
            "properties": copy.deepcopy(node.properties),
            "port_labels": dict(node.port_labels),
            "exposed_ports": dict(node.exposed_ports),
            "collapsed": node.collapsed,
            "locked": node.locked,
        }

    def assert_rejected_untouched(self, node_id: str, params: dict[str, Any], code: str) -> Any:
        before_state = self._state(self.node(node_id))
        before_depth = self.undo_depth()
        error = expect_error(self.context, "node.update", {"node_id": node_id, **params}, code)
        self.assertEqual(self._state(self.node(node_id)), before_state, f"{code}: the node must be untouched")
        self.assertEqual(self.undo_depth(), before_depth, f"{code}: no undo entry may be recorded")
        return error

    def test_wrong_scope_move_rejects_the_whole_update(self) -> None:
        start = self.add(START, 0, 0, title="Inner")
        constant = self.add(CONSTANT, 0, 300)
        self.scene.clear_selection()
        self.scene.select_node(start, True)
        self.scene.select_node(constant, True)
        self.assertTrue(self.scene.group_selected_nodes())
        self.assertTrue(self.node(start).parent_node_id, "start now lives inside a subnode shell")
        self.assert_rejected_untouched(start, {"title": "Renamed", "x": 999, "port_labels": {"right": "out"}}, WRONG_SCOPE)

    def test_unknown_port_key_rejects_the_whole_update(self) -> None:
        node_id = self.add(PROCESS, title="Mesh")
        error = self.assert_rejected_untouched(
            node_id, {"title": "Renamed", "x": 50, "port_labels": {"right": "yes", "nope": "x"}}, NOT_FOUND
        )
        self.assertEqual(error.details["port"], "nope")
        self.assert_rejected_untouched(node_id, {"title": "Renamed", "exposed_ports": {"left": False, "nope": True}}, NOT_FOUND)

    def test_unknown_property_key_rejects_the_whole_update(self) -> None:
        node_id = self.add(PROCESS, title="Mesh")
        error = self.assert_rejected_untouched(
            node_id, {"title": "Renamed", "x": 50, "width": 400, "properties": {"body": "new", "zzz": 1}}, INVALID_PARAMS
        )
        self.assertIn("body", error.details["available"])

    def test_port_locked_property_rejects_the_whole_update(self) -> None:
        media = self.add(MEDIA)  # plain node.add keeps the source port exposed
        error = self.assert_rejected_untouched(
            media, {"title": "Renamed", "x": 40, "port_labels": {"source": "in"}, "properties": {"source": "C:/x.png"}}, PROPERTY_LOCKED_BY_PORT
        )
        self.assertEqual(error.details["keys"], ["source"])

    def test_ineligible_collapse_or_lock_rejects_the_whole_update(self) -> None:
        process = self.add(PROCESS, title="Mesh")
        error = self.assert_rejected_untouched(process, {"title": "Renamed", "collapsed": True}, NO_EFFECT)
        self.assertIn("not collapsible", " ".join(error.details["reasons"]))
        active = self.add(CONSTANT, title="K")
        error = self.assert_rejected_untouched(active, {"title": "K2", "locked": True}, NO_EFFECT)
        self.assertIn("passive", " ".join(error.details["reasons"]))
        # Requesting the state a node already has is not an eligibility problem.
        result = self.call_one_undo("node.update", {"node_id": active, "title": "K2", "locked": False})
        self.assertEqual(result["changed"], ["title"])

    def test_refused_expand_rejects_the_whole_update(self) -> None:
        # Expanding the collapsed Group would have to grow its locked parent: nothing may change.
        parent = self.add(GROUP, 0, 0, title="Parent")
        self.scene.set_node_geometry(parent, 0.0, 0.0, 560.0, 400.0)
        inner = self.add(GROUP, 40, 120, title="Inner")
        self.scene.set_node_geometry(inner, 40.0, 120.0, 500.0, 300.0)
        self.add(PROCESS, 80, 200)
        self.assertTrue(self.scene.set_node_collapsed(inner, True))
        self.assertTrue(self.scene.set_node_locked(parent, True))

        error = self.assert_rejected_untouched(inner, {"title": "Renamed", "collapsed": False}, NO_EFFECT)

        self.assertIn("locked Group “Parent” would have to grow", " ".join(error.details["reasons"]))

    def test_expand_refused_after_the_same_updates_move_rolls_the_move_back(self) -> None:
        # Where it sits the Group can expand; the move lands its pill in a locked Group its expand would have to grow.
        group = self.add(GROUP, 0, 0, title="G")
        self.scene.set_node_geometry(group, 0.0, 0.0, 400.0, 300.0)
        member = self.add(PROCESS, 40, 120)
        self.assertTrue(self.scene.set_node_collapsed(group, True))
        locked = self.add(GROUP, 1000, 0, title="Locked")
        self.scene.set_node_geometry(locked, 1000.0, 0.0, 300.0, 200.0)
        self.assertTrue(self.scene.set_node_locked(locked, True))
        member_before = (self.node(member).x, self.node(member).y)

        error = self.assert_rejected_untouched(group, {"x": 1020.0, "y": 40.0, "collapsed": False}, NO_EFFECT)

        self.assertIn("locked Group “Locked” would have to grow", " ".join(error.details["reasons"]))
        self.assertEqual((self.node(member).x, self.node(member).y), member_before)

    def test_move_contents_false_is_rejected_off_an_expanded_group(self) -> None:
        plain = self.add(PROCESS, title="Mesh")
        self.assert_rejected_untouched(plain, {"title": "Renamed", "x": 50, "move_contents": False}, INVALID_PARAMS)
        member = self.add(PROCESS, 0, 300)
        group = call(self.context, "group.wrap", {"node_ids": [member]})["group_node_id"]
        self.assertTrue(self.scene.set_node_collapsed(group, True))
        error = self.assert_rejected_untouched(group, {"x": 900, "move_contents": False}, INVALID_PARAMS)
        self.assertIn("collapsed Group always moves with what it holds", " ".join(error.details["problems"]))


class NodeUpdateGroupMoveTests(_NodeHandlerCase):
    """Moving a Group backdrop with node.update carries what it holds, like dragging it on the canvas."""

    def position(self, node_id: str) -> tuple[float, float]:
        node = self.node(node_id)
        return (float(node.x), float(node.y))

    def wrap(self, node_ids: list[str], title: str = "G") -> str:
        return call(self.context, "group.wrap", {"node_ids": node_ids, "title": title})["group_node_id"]

    def members(self, group_id: str) -> list[str]:
        row = next(row for row in self.scene.backdrop_nodes_model if row["node_id"] == group_id)
        return sorted([*row["member_node_ids"], *row["member_backdrop_ids"]])

    def canvas_drag_node_ids(self, group_id: str) -> list[str]:
        """What GraphCanvasSceneState.dragNodeIdsForAnchor adds to a Group drag, read from the same backdrop rows."""
        rows = {row["node_id"]: row for row in self.scene.backdrop_nodes_model}
        collected: list[str] = []

        def descend(backdrop_id: str) -> None:
            row = rows.get(backdrop_id)
            if row is None:
                return
            for node_id in [*row["member_node_ids"], *row["member_backdrop_ids"]]:
                if node_id not in collected:
                    collected.append(node_id)
            for nested_id in row["member_backdrop_ids"]:
                descend(nested_id)

        descend(group_id)
        return sorted(collected)

    def assert_shifted(self, before: dict[str, tuple[float, float]], dx: float, dy: float) -> None:
        for node_id, (x, y) in before.items():
            self.assertEqual(self.position(node_id), (x + dx, y + dy), node_id)

    def test_moving_an_expanded_group_carries_its_members_in_one_undo_step(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 320, 40)
        group = self.wrap([first, second])
        before = {node_id: self.position(node_id) for node_id in (group, first, second)}

        result = self.call_one_undo("node.update", {"node_id": group, "x": before[group][0] + 600})

        self.assertEqual(result["changed"], ["x"])
        self.assertEqual(result["carried_node_ids"], sorted([first, second]))
        self.assert_shifted(before, 600.0, 0.0)
        self.assertEqual(self.members(group), sorted([first, second]))
        workspace = self.context.active_workspace()
        self.assertIsNotNone(self.context.runtime_history.undo_workspace(workspace.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(workspace.workspace_id)
        self.assert_shifted(before, 0.0, 0.0)

    def test_moving_an_outer_group_carries_nested_groups_and_their_nodes(self) -> None:
        inner_first = self.add(PROCESS, 0, 0)
        inner_second = self.add(PROCESS, 320, 0)
        inner = self.wrap([inner_first, inner_second], "Inner")
        lone = self.add(PROCESS, 0, 400)
        outer = self.wrap([inner, lone], "Outer")
        before = {node_id: self.position(node_id) for node_id in (outer, inner, inner_first, inner_second, lone)}

        result = self.call_one_undo(
            "node.update", {"node_id": outer, "x": before[outer][0] + 500, "y": before[outer][1] + 100}
        )

        self.assertEqual(result["carried_node_ids"], sorted([inner, inner_first, inner_second, lone]))
        self.assert_shifted(before, 500.0, 100.0)
        self.assertEqual(self.members(outer), sorted([inner, lone]))
        self.assertEqual(self.members(inner), sorted([inner_first, inner_second]))

    def test_carried_nodes_are_what_a_canvas_drag_moves(self) -> None:
        hidden_first = self.add(PROCESS, 0, 0)
        hidden_second = self.add(PROCESS, 320, 0)
        inner = self.wrap([hidden_first, hidden_second], "Inner")
        locked = self.add(PROCESS, 0, 400)
        outer = self.wrap([inner, locked], "Outer")
        call(self.context, "node.update", {"node_id": locked, "locked": True})
        call(self.context, "node.update", {"node_id": inner, "collapsed": True})
        expected = self.canvas_drag_node_ids(outer)
        self.assertEqual(expected, sorted([inner, hidden_first, hidden_second, locked]))
        before = {node_id: self.position(node_id) for node_id in (outer, *expected)}

        result = self.call_one_undo("node.update", {"node_id": outer, "x": before[outer][0] + 300})

        self.assertEqual(result["carried_node_ids"], expected)
        self.assert_shifted(before, 300.0, 0.0)

    def test_move_with_a_new_size_carries_by_default(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 320, 0)
        group = self.wrap([first, second])
        width = float(self.node(group).custom_width)
        before = {node_id: self.position(node_id) for node_id in (first, second)}

        result = self.call_one_undo(
            "node.update", {"node_id": group, "x": self.position(group)[0] + 500, "width": width + 200}
        )

        self.assertEqual(result["changed"], ["x", "width"])
        self.assertEqual(result["carried_node_ids"], sorted([first, second]))
        self.assert_shifted(before, 500.0, 0.0)
        self.assertEqual(self.members(group), sorted([first, second]))

    def test_move_contents_false_grows_the_frame_left_around_a_neighbour(self) -> None:
        neighbour = self.add(PROCESS, -330, 30)
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 320, 0)
        group = self.wrap([first, second])
        x, y = self.position(group)
        width = float(self.node(group).custom_width)
        before = {node_id: self.position(node_id) for node_id in (neighbour, first, second)}

        result = self.call_one_undo(
            "node.update", {"node_id": group, "x": x - 450, "width": width + 450, "move_contents": False}
        )

        self.assertEqual(result["changed"], ["x", "width"])
        self.assertEqual(result["carried_node_ids"], [])
        self.assert_shifted(before, 0.0, 0.0)
        self.assertEqual((self.position(group), float(self.node(group).custom_width)), ((x - 450, y), width + 450))
        self.assertEqual(self.members(group), sorted([neighbour, first, second]))

    def test_move_contents_false_moves_only_the_frame(self) -> None:
        member = self.add(PROCESS, 0, 0)
        group = self.wrap([member])
        x, y = self.position(group)

        result = self.call_one_undo("node.update", {"node_id": group, "x": x + 40, "move_contents": False})

        self.assertEqual((result["changed"], result["carried_node_ids"]), (["x"], []))
        self.assertEqual((self.position(group), self.position(member)), ((x + 40, y), (0.0, 0.0)))

    def test_a_node_added_earlier_in_the_same_batch_is_carried(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 600, 300)
        group = self.wrap([first, second])
        x = self.position(group)[0]

        result = self.call_one_undo(
            "graph.apply",
            {
                "ops": [
                    {"id": "added", "op": "node.add", "params": {"type_id": PROCESS, "x": 300, "y": 150}},
                    {"op": "node.update", "params": {"node_id": group, "x": x + 400}},
                ]
            },
        )

        added = result["ids"]["added"]
        self.assertEqual(result["results"][1]["result"]["carried_node_ids"], sorted([added, first, second]))
        self.assertEqual(self.position(added), (700.0, 150.0))

    def test_moving_a_collapsed_group_reports_its_hidden_members(self) -> None:
        first = self.add(PROCESS, 0, 0)
        second = self.add(PROCESS, 320, 0)
        group = self.wrap([first, second])
        self.assertTrue(self.scene.set_node_collapsed(group, True))
        before = {node_id: self.position(node_id) for node_id in (group, first, second)}

        result = self.call_one_undo("node.update", {"node_id": group, "y": before[group][1] + 250})

        self.assertEqual(result["carried_node_ids"], sorted([first, second]))
        self.assert_shifted(before, 0.0, 250.0)

    def test_moving_other_nodes_carries_nothing(self) -> None:
        node_id = self.add(PROCESS, 0, 0)
        result = self.call_one_undo("node.update", {"node_id": node_id, "x": 120})
        self.assertEqual(result["carried_node_ids"], [])


class FlowchartBodyLabelTests(_NodeHandlerCase):
    """F15: flowchart shape-label types render ``body`` in the shape; it follows the title."""

    def test_add_with_title_sets_the_in_shape_label(self) -> None:
        node = self.node(self.add(PROCESS, title="Mesh the part"))
        self.assertEqual((node.title, node.properties["title"], node.properties["body"]), ("Mesh the part",) * 3)

    def test_explicit_body_in_add_wins(self) -> None:
        node = self.node(self.add(PROCESS, title="Mesh", properties={"body": "Custom label"}))
        self.assertEqual(node.title, "Mesh")
        self.assertEqual(node.properties["body"], "Custom label")

    def test_update_title_on_an_untouched_node_updates_the_body(self) -> None:
        node_id = self.add(PROCESS)  # default title == default body == "Process"
        self.assertEqual(self.node(node_id).properties["body"], "Process")
        result = self.call_one_undo("node.update", {"node_id": node_id, "title": "Solve"})
        self.assertIn("properties.body", result["changed"])
        self.assertEqual(self.node(node_id).properties["body"], "Solve")

    def test_update_title_keeps_a_customised_body(self) -> None:
        node_id = self.add(PROCESS, title="Mesh")
        self.call_one_undo("node.update", {"node_id": node_id, "properties": {"body": "Hand-written note"}})
        result = self.call_one_undo("node.update", {"node_id": node_id, "title": "Mesh v2"})
        self.assertEqual(result["changed"], ["title", "properties.title"])
        self.assertEqual(self.node(node_id).properties["body"], "Hand-written note")

    def test_explicit_body_in_update_wins(self) -> None:
        node_id = self.add(PROCESS, title="Mesh")
        self.call_one_undo("node.update", {"node_id": node_id, "title": "Mesh v2", "properties": {"body": "Other"}})
        node = self.node(node_id)
        self.assertEqual((node.title, node.properties["body"]), ("Mesh v2", "Other"))

    def test_annotation_and_content_body_types_are_unaffected(self) -> None:
        sticky = self.add(STICKY, title="Note")
        self.assertEqual(self.node(sticky).properties["body"], "")
        self.call_one_undo("node.update", {"node_id": sticky, "title": "Note 2"})
        self.assertEqual(self.node(sticky).properties["body"], "")
        card = self.add(CARD, title="Card A")  # card renders body as separate content
        self.assertEqual(self.node(card).properties["body"], "")
        self.call_one_undo("node.update", {"node_id": card, "title": "Card B"})
        self.assertEqual(self.node(card).properties["body"], "")


class NodeStyleTests(_NodeHandlerCase):
    def setUp(self) -> None:
        super().setUp()
        self.start = self.add(START, 0, 0)
        self.process = self.add(PROCESS, 300, 0)
        self.scene.add_edge(self.start, "right", self.process, "left")

    def test_merge_replace_clear_and_presets(self) -> None:
        result = self.call_one_undo("node.set_style", {"node_id": self.process, "style": {"fill_color": "#FF8800"}})
        self.assertEqual(result["visual_style"], {"fill_color": "#FF8800"})
        result = self.call_one_undo("node.set_style", {"node_id": self.process, "style": {"border_width": 3}})
        self.assertEqual(result["visual_style"], {"fill_color": "#FF8800", "border_width": 3.0})
        self.assertEqual(self.node(self.process).visual_style, {"fill_color": "#FF8800", "border_width": 3.0})
        result = self.call_one_undo("node.set_style", {"node_id": self.process, "style": {"text_color": "#000000"}, "replace": True})
        self.assertEqual(result["visual_style"], {"text_color": "#000000"})
        expect_error(self.context, "node.set_style", {"node_id": self.process, "style": {"text_color": "#000000"}}, NO_EFFECT)
        result = self.call_one_undo("node.set_style", {"node_id": self.process, "preset": "Flowchart Classic", "replace": True})
        self.assertEqual(result["visual_style"]["fill_color"], "#F5FAFD")
        self.assertEqual(result["visual_style"]["font_weight"], "bold")
        by_id = self.call_one_undo("node.set_style", {"node_id": self.start, "preset": "builtin_node_rounded_amber"})
        self.assertEqual(by_id["visual_style"]["corner_radius"], 18.0)
        error = expect_error(self.context, "node.set_style", {"node_id": self.process, "preset": "Nope"}, NOT_FOUND)
        self.assertTrue(error.details["available"])
        result = self.call_one_undo("node.set_style", {"node_id": self.process, "clear": True})
        self.assertEqual(result["visual_style"], {})
        self.assertEqual(self.node(self.process).visual_style, {})
        expect_error(self.context, "node.set_style", {"node_id": self.process, "clear": True}, NO_EFFECT)
        expect_error(self.context, "node.set_style", {"node_id": self.process, "clear": True, "style": {"fill_color": "#FFFFFF"}}, INVALID_PARAMS)
        expect_error(self.context, "node.set_style", {"node_id": self.process}, INVALID_PARAMS)

    def test_style_validation_and_not_passive(self) -> None:
        expect_error(self.context, "node.set_style", {"node_id": self.process, "style": {"opacity": 0.5}}, INVALID_PARAMS)
        expect_error(self.context, "node.set_style", {"node_id": self.process, "style": {"fill_color": "red"}}, INVALID_PARAMS)
        result = self.call_one_undo(
            "node.set_style",
            {"node_id": self.process, "style": {"fill_color": "#FFFFFF", "fill_color_end": "#000000", "gradient_enabled": True}},
        )
        self.assertEqual(result["visual_style"]["gradient_color"], "#000000")
        self.assertTrue(result["visual_style"]["gradient_enabled"])
        active = self.add(CONSTANT, 0, 400)
        expect_error(self.context, "node.set_style", {"node_id": active, "style": {"fill_color": "#FFFFFF"}}, NOT_PASSIVE)

    def test_propagate_reports_affected_connected_passive_nodes(self) -> None:
        self.call_one_undo("node.set_style", {"node_id": self.process, "style": {"fill_color": "#FF8800", "border_width": 2}})
        loose = self.add(PROCESS, 600, 400)  # passive but not connected: owner leaves it untouched
        result = self.call_one_undo("node.set_style", {"node_id": self.process, "propagate": True})
        self.assertEqual(result["propagated_to"], [self.start])
        self.assertEqual(self.node(self.start).visual_style, self.node(self.process).visual_style)
        self.assertEqual(self.node(loose).visual_style, {})
        expect_error(self.context, "node.set_style", {"node_id": self.process, "propagate": True}, NO_EFFECT)
        combined = self.call_one_undo(
            "node.set_style", {"node_id": self.process, "style": {"border_width": 5}, "propagate": True}
        )
        self.assertEqual(combined["visual_style"]["border_width"], 5.0)
        self.assertEqual(combined["propagated_to"], [self.start])


class NodeDeleteDuplicateTests(_NodeHandlerCase):
    def setUp(self) -> None:
        super().setUp()
        self.start = self.add(START, 0, 0)
        self.process = self.add(PROCESS, 300, 0)
        self.edge_id = self.scene.add_edge(self.start, "right", self.process, "left")

    def test_delete_reports_removed_edges_and_requires_all_ids_first(self) -> None:
        error = expect_error(self.context, "node.delete", {"node_ids": [self.start, "node_missing", "node_other"]}, NOT_FOUND)
        self.assertEqual(error.details["id"], "node_missing")
        self.assertIn(self.start, self.context.active_workspace().nodes)
        result = self.call_one_undo("node.delete", {"node_ids": [self.start]})
        self.assertEqual(result["deleted_node_ids"], [self.start])
        self.assertEqual(result["removed_edge_ids"], [self.edge_id])
        self.assertNotIn(self.start, self.context.active_workspace().nodes)
        self.assertNotIn(self.edge_id, self.context.active_workspace().edges)
        other = self.add(CONSTANT, 0, 400)
        result = self.call_one_undo("node.delete", {"node_ids": [self.process, other, other]})
        self.assertEqual(result["deleted_node_ids"], [self.process, other])
        self.assertEqual(self.context.active_workspace().nodes, {})

    def test_duplicate_maps_ids_and_offsets_positions(self) -> None:
        edges_before = len(self.context.active_workspace().edges)
        result = self.call_one_undo("node.duplicate", {"node_ids": [self.process, self.start], "offset_x": 50, "offset_y": 60})
        self.assertEqual(len(result["node_ids"]), 2)
        self.assertEqual(result["id_map"], {self.process: result["node_ids"][0], self.start: result["node_ids"][1]})
        for original_id, new_id in result["id_map"].items():
            original, copy_node = self.node(original_id), self.node(new_id)
            self.assertNotEqual(original_id, new_id)
            self.assertEqual(copy_node.type_id, original.type_id)
            self.assertEqual(copy_node.title, original.title)
            self.assertAlmostEqual(copy_node.x - original.x, 50.0, places=3)
            self.assertAlmostEqual(copy_node.y - original.y, 60.0, places=3)
        self.assertEqual(len(self.context.active_workspace().edges), edges_before + 1)
        self.assertEqual(sorted(result["new_node_ids"]), sorted(result["id_map"].values()))
        expect_error(self.context, "node.duplicate", {"node_ids": ["node_missing"]}, NOT_FOUND)
        self.call_one_undo("node.update", {"node_id": self.process, "locked": True})
        error = expect_error(self.context, "node.duplicate", {"node_ids": [self.start, self.process]}, NO_EFFECT)
        self.assertEqual(error.details["unselectable"], [self.process])


class CatalogHandlerTests(_NodeHandlerCase):
    def test_list_node_types_filters_sorts_and_counts(self) -> None:
        everything = self.call_no_undo("catalog.list_node_types", {})
        self.assertGreater(everything["total"], 100)
        self.assertEqual(len(everything["node_types"]), min(everything["total"], 200))
        keys = [(tuple(row["category_path"]), row["display_name"].lower(), row["type_id"]) for row in everything["node_types"]]
        self.assertEqual(keys, sorted(keys))
        self.assertNotIn("core.subnode_input", [row["type_id"] for row in everything["node_types"]])
        passive = self.call_no_undo("catalog.list_node_types", {"runtime_behavior": "passive", "limit": 5})
        self.assertEqual(len(passive["node_types"]), 5)
        self.assertGreater(passive["total"], 5)
        self.assertTrue(all(row["runtime_behavior"] == "passive" for row in passive["node_types"]))
        decision = self.call_no_undo("catalog.list_node_types", {"category": "Flowchart", "query": "decision"})
        self.assertEqual([row["type_id"] for row in decision["node_types"]], ["passive.flowchart.decision"])
        self.assertEqual(decision["total"], 1)
        row = decision["node_types"][0]
        self.assertEqual(row["category_path"], ["Flowchart"])
        self.assertIn("flowchart", row["keywords"])

    def test_describe_node_type_shapes(self) -> None:
        process = self.call_no_undo("catalog.describe_node_type", {"type_id": PROCESS})
        self.assertEqual([port["key"] for port in process["ports"]], ["top", "right", "bottom", "left"])
        self.assertTrue(all(port["direction"] == "neutral" and port["kind"] == "flow" for port in process["ports"]))
        self.assertTrue(process["resizable"])
        self.assertFalse(process["collapsible"])
        self.assertTrue(process["title_is_property"])
        self.assertGreater(process["default_size"]["width"], 0)
        self.assertGreater(process["min_size"]["height"], 0)
        properties = {prop["key"]: prop for prop in process["properties"]}
        self.assertEqual(properties["title"]["default"], "Process")
        self.assertEqual(properties["body_format"]["enum_values"], ["markdown", "plain"])
        constant = self.call_no_undo("catalog.describe_node_type", {"type_id": CONSTANT})
        self.assertFalse(constant["resizable"])
        self.assertFalse(constant["title_is_property"])
        self.assertTrue(constant["collapsible"])
        media = self.call_no_undo("catalog.describe_node_type", {"type_id": MEDIA})
        self.assertTrue(media["resizable"])
        self.assertIn("source", {port["key"] for port in media["ports"]})
        error = expect_error(self.context, "catalog.describe_node_type", {"type_id": "passive.flowchart.nope"}, UNKNOWN_NODE_TYPE)
        self.assertIn(PROCESS, error.details["suggestions"])
        json.dumps(process)

    def test_style_schema_lists_owner_keys_and_presets(self) -> None:
        schema = self.call_no_undo("catalog.style_schema", {})
        self.assertIn("fill_color", schema["node_style"]["keys"])
        self.assertIn("gradient_color", schema["node_style"]["keys"])
        self.assertNotIn("opacity", schema["node_style"]["keys"])
        self.assertNotIn("accent_color", schema["node_style"]["keys"])
        self.assertEqual(schema["node_style"]["enums"]["font_weight"], ["normal", "bold"])
        self.assertEqual(schema["node_style"]["aliases"], {"fill_color_end": "gradient_color"})
        self.assertIn("stroke_color", schema["edge_style"]["keys"])
        self.assertEqual(schema["edge_style"]["enums"]["display_mode"], ["default", "faint", "hidden"])
        self.assertEqual(
            schema["edge_style"]["aliases"],
            {
                "color": "stroke_color",
                "width": "stroke_width",
                "pattern": "stroke_pattern",
                "end_arrow": "arrow_head",
                "start_arrow": "arrow_tail",
                "label_color": "label_text_color",
                "label_background": "label_background_color",
                "label_fraction": "label_position",
                "label_rotation": "label_orientation",
            },
        )
        for arrow_key in ("arrow_head", "arrow_tail"):
            self.assertEqual(schema["edge_style"]["enums"][arrow_key], ["filled", "open", "none"])
        self.assertEqual(schema["edge_style"]["enums"]["label_orientation"], ["horizontal", "follow_path"])
        self.assertIn("label_position", schema["edge_style"]["keys"])
        self.assertTrue(set(schema["edge_style"]["aliases"].values()) <= set(schema["edge_style"]["keys"]))
        self.assertIn("format", schema["text_style"]["keys"])
        self.assertIn("text_color", schema["text_style"]["keys"])
        self.assertEqual(schema["text_style"]["aliases"], {"color": "text_color"})
        node_presets = schema["presets"]["node"]
        self.assertTrue(node_presets)
        self.assertEqual(set(node_presets[0]), {"preset_id", "name", "style", "read_only"})
        self.assertIn("Flowchart Classic", [preset["name"] for preset in node_presets])
        self.assertTrue(schema["presets"]["edge"])
        json.dumps(schema)

    def test_project_presets_are_merged_from_metadata(self) -> None:
        self.context.model.project.replace_metadata(
            {"ui": {"passive_style_presets": {"node_presets": [{"name": "Team Orange", "style": {"fill_color": "#FF8800"}}]}}}
        )
        schema = self.call_no_undo("catalog.style_schema", {})
        custom = [preset for preset in schema["presets"]["node"] if preset["name"] == "Team Orange"]
        self.assertEqual(len(custom), 1)
        self.assertFalse(custom[0]["read_only"])
        node_id = self.add(PROCESS)
        result = self.call_one_undo("node.set_style", {"node_id": node_id, "preset": "team orange"})
        self.assertEqual(result["visual_style"], {"fill_color": "#FF8800"})


class GraphReadTests(_NodeHandlerCase):
    def test_get_graph_snapshot_and_wrong_workspace(self) -> None:
        start = self.add(START, 0, 0, title="Begin")
        process = self.add(PROCESS, 300, 0)
        edge_id = self.scene.add_edge(start, "right", process, "left")
        self.scene.set_node_visual_style(process, {"fill_color": "#FF8800"})
        snapshot = self.call_no_undo("graph.get", {})
        self.assertEqual(snapshot["workspace_id"], self.context.workspace_id())
        self.assertTrue(snapshot["workspace_name"])
        self.assertTrue(snapshot["dirty"])
        self.assertEqual(snapshot["scope_path"], [])
        self.assertEqual([node["node_id"] for node in snapshot["nodes"]], [start, process])
        self.assertEqual([edge["edge_id"] for edge in snapshot["edges"]], [edge_id])
        self.assertEqual(snapshot["edges"][0]["kind"], "flow")
        self.assertEqual(len(snapshot["views"]), 1)
        self.assertTrue(snapshot["views"][0]["active"])
        self.assertEqual(snapshot["views"][0]["view_id"], snapshot["active_view_id"])
        self.assertNotIn("visual_style", snapshot["nodes"][1])
        detailed = self.call_no_undo("graph.get", {"include_style": True, "include_properties": True})
        self.assertEqual(detailed["nodes"][1]["visual_style"], {"fill_color": "#FF8800"})
        self.assertEqual(detailed["nodes"][0]["properties"]["title"], "Begin")
        self.assertIn("visual_style", detailed["edges"][0])
        error = expect_error(self.context, "graph.get", {"workspace_id": "ws_nope"}, WRONG_WORKSPACE)
        self.assertEqual(error.details["available"], [self.context.workspace_id()])
        same = self.call_no_undo("graph.get", {"workspace_id": self.context.workspace_id()})
        self.assertEqual(len(same["nodes"]), 2)
        json.dumps(detailed)

    def test_scope_active_hides_subnode_children(self) -> None:
        start = self.add(START, 0, 0)
        constant = self.add(CONSTANT, 0, 300)
        outside = self.add(PROCESS, 600, 0)
        self.scene.clear_selection()
        self.scene.select_node(start, True)
        self.scene.select_node(constant, True)
        self.assertTrue(self.scene.group_selected_nodes())
        shell_id = self.node(start).parent_node_id
        self.assertTrue(shell_id)
        active = self.call_no_undo("graph.get", {"scope": "active"})
        active_ids = {node["node_id"] for node in active["nodes"]}
        self.assertIn(outside, active_ids)
        self.assertIn(shell_id, active_ids)
        self.assertNotIn(start, active_ids)
        everything = self.call_no_undo("graph.get", {"scope": "all"})
        by_id = {node["node_id"]: node for node in everything["nodes"]}
        self.assertEqual(by_id[start]["parent_node_id"], shell_id)
        self.assertEqual(by_id[outside]["parent_node_id"], "")
        detail = self.call_no_undo("graph.get_node", {"node_id": start})
        self.assertFalse(detail["in_active_scope"])
        found = self.call_no_undo("graph.find_nodes", {"type_id": START, "scope": "active"})
        self.assertEqual(found["total"], 0)
        found = self.call_no_undo("graph.find_nodes", {"type_id": START})
        self.assertEqual([node["node_id"] for node in found["nodes"]], [start])

    def test_get_node_detail_and_find_nodes(self) -> None:
        start = self.add(START, 0, 0, title="Begin")
        process = self.add(PROCESS, 300, 0, title="Mesh the part")
        edge_id = self.scene.add_edge(start, "right", process, "left")
        self.scene.set_node_port_label(process, "left", "in")
        detail = self.call_no_undo("graph.get_node", {"node_id": process})
        self.assertEqual(detail["node"]["title"], "Mesh the part")
        self.assertEqual(detail["display_name"], "Process")
        self.assertEqual(detail["properties"]["title"], "Mesh the part")
        self.assertEqual(detail["port_labels"], {"left": "in"})
        self.assertEqual(detail["exposed_ports"], {"top": True, "right": True, "bottom": True, "left": True})
        ports = {port["key"]: port for port in detail["ports"]}
        self.assertEqual(ports["left"]["connected_edge_ids"], [edge_id])
        self.assertEqual(ports["left"]["label"], "in")
        self.assertEqual(ports["right"]["connected_edge_ids"], [])
        self.assertEqual([edge["edge_id"] for edge in detail["incident_edges"]], [edge_id])
        self.assertEqual(detail["links"], [])
        self.assertEqual(detail["comments"], [])
        self.assertTrue(detail["in_active_scope"])
        expect_error(self.context, "graph.get_node", {"node_id": "node_missing"}, NOT_FOUND)
        by_title = self.call_no_undo("graph.find_nodes", {"title": "Begin"})
        self.assertEqual([node["node_id"] for node in by_title["nodes"]], [start])
        contains = self.call_no_undo("graph.find_nodes", {"title_contains": "MESH"})
        self.assertEqual([node["node_id"] for node in contains["nodes"]], [process])
        query = self.call_no_undo("graph.find_nodes", {"query": "flowchart", "limit": 1})
        self.assertEqual(len(query["nodes"]), 1)
        self.assertEqual(query["total"], 2)
        nothing = self.call_no_undo("graph.find_nodes", {"type_id": CONSTANT})
        self.assertEqual((nothing["nodes"], nothing["total"]), ([], 0))
        json.dumps(detail)


class ClientFacadeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = _RecordingClient()
        self.nodes = NodesApi(self.client)  # type: ignore[arg-type]
        self.catalog = CatalogApi(self.client)  # type: ignore[arg-type]
        self.graph = GraphApi(self.client)  # type: ignore[arg-type]

    def last(self) -> tuple[str, dict[str, Any]]:
        return self.client.calls[-1]

    def test_node_facade_builds_catalog_params(self) -> None:
        self.nodes.add(PROCESS, 1, 2, title="Mesh", select=True)
        self.assertEqual(self.last(), ("node.add", {"type_id": PROCESS, "x": 1.0, "y": 2.0, "title": "Mesh", "select": True}))
        self.nodes.add_text("# Hi", 0, 0, format="plain", style={"color": "#FF0000"}, width=200)
        self.assertEqual(
            self.last(),
            ("node.add_text", {"markdown": "# Hi", "x": 0.0, "y": 0.0, "width": 200.0, "format": "plain", "style": {"color": "#FF0000"}}),
        )
        self.nodes.add_media("C:/pic.png", 3, 4, fit_mode="cover", show_title=False)
        self.assertEqual(self.last(), ("node.add_media", {"path": "C:/pic.png", "x": 3.0, "y": 4.0, "fit_mode": "cover", "show_title": False}))
        self.nodes.add_web_panel(0, 0, url="https://example.com", display_mode="fit_page")
        self.assertEqual(self.last(), ("node.add_web_panel", {"x": 0.0, "y": 0.0, "url": "https://example.com", "display_mode": "fit_page"}))
        self.nodes.add_web_panel(0, 0, html="<p>hi</p>")
        self.assertEqual(self.last()[1]["html"], "<p>hi</p>")
        self.nodes.update("node_1", title="T", x=5, properties={"body": "b"}, port_labels={"right": "r"}, exposed_ports={"left": False}, locked=True)
        self.assertEqual(
            self.last(),
            (
                "node.update",
                {
                    "node_id": "node_1",
                    "title": "T",
                    "x": 5.0,
                    "properties": {"body": "b"},
                    "port_labels": {"right": "r"},
                    "exposed_ports": {"left": False},
                    "locked": True,
                },
            ),
        )
        self.nodes.set_style("node_1", {"fill_color": "#FFFFFF"}, replace=True)
        self.assertEqual(
            self.last(),
            ("node.set_style", {"node_id": "node_1", "replace": True, "clear": False, "propagate": False, "style": {"fill_color": "#FFFFFF"}}),
        )
        self.nodes.set_style("node_1", preset="Flowchart Classic", propagate=True)
        self.assertEqual(self.last()[1]["preset"], "Flowchart Classic")
        self.assertNotIn("style", self.last()[1])
        self.nodes.delete("node_1")
        self.assertEqual(self.last(), ("node.delete", {"node_ids": ["node_1"]}))
        self.nodes.duplicate(["node_1", "node_2"], offset_x=10)
        self.assertEqual(self.last(), ("node.duplicate", {"node_ids": ["node_1", "node_2"], "offset_x": 10.0}))

    def test_node_facade_sugar(self) -> None:
        self.nodes.add_path_pointer("C:/data", 1, 2, mode="folder", title="Data")
        self.assertEqual(
            self.last(),
            ("node.add", {"type_id": "io.path_pointer", "x": 1.0, "y": 2.0, "title": "Data", "properties": {"path": "C:/data", "mode": "folder"}}),
        )
        self.nodes.add_path_pointer("C:/f.txt", 0, 0)
        self.assertEqual(self.last()[1]["properties"], {"path": "C:/f.txt", "mode": "file"})
        self.nodes.add_panel(7, 8, width=300)
        self.assertEqual(self.last(), ("node.add", {"type_id": "data.panel", "x": 7.0, "y": 8.0, "width": 300.0}))
        self.nodes.set_text_style("node_1", font_size=20, color="#FF0000", format="plain")
        self.assertEqual(
            self.last(),
            ("node.update", {"node_id": "node_1", "properties": {"body_font_size": 20, "body_text_color": "#FF0000", "body_format": "plain"}}),
        )
        self.nodes.set_text_style("node_2", content_key="text", italic=True)
        self.assertEqual(self.last()[1]["properties"], {"italic": True})

    def test_catalog_and_graph_facades(self) -> None:
        self.catalog.list_node_types(query="flow", runtime_behavior="passive", limit=10)
        self.assertEqual(self.last(), ("catalog.list_node_types", {"query": "flow", "runtime_behavior": "passive", "limit": 10}))
        self.catalog.describe_node_type(PROCESS)
        self.assertEqual(self.last(), ("catalog.describe_node_type", {"type_id": PROCESS}))
        self.catalog.style_schema()
        self.assertEqual(self.last(), ("catalog.style_schema", {}))
        self.graph.get(scope="all", include_style=True)
        self.assertEqual(self.last(), ("graph.get", {"scope": "all", "include_style": True}))
        self.graph.get_node("node_1")
        self.assertEqual(self.last(), ("graph.get_node", {"node_id": "node_1"}))
        self.graph.find_nodes(title_contains="mesh", limit=5)
        self.assertEqual(self.last(), ("graph.find_nodes", {"title_contains": "mesh", "limit": 5}))


if __name__ == "__main__":
    unittest.main()
