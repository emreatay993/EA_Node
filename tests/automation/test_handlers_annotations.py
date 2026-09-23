# Purpose: Shell-free tests for the comment.* / link.* automation handlers and the AnnotationsApi client facade.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_annotations.py
from __future__ import annotations

import unittest
from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.client_api.annotations import AnnotationsApi
from ea_node_editor.automation.errors import AutomationOpError
from ea_node_editor.ui.shell.automation.handlers.annotations import upsert_link
from tests.automation.harness import build_context, call, expect_error

PROCESS = "passive.flowchart.process"


class _AnnotationHandlerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.workspace_id = self.context.workspace_id()
        self.node_id = self.context.scene.add_node_from_type(PROCESS, 0.0, 0.0)

    def undo_depth(self) -> int:
        return int(self.context.runtime_history.undo_depth(self.workspace_id))

    def node(self):
        return self.context.require_node(self.node_id)

    def assert_one_undo_step(self, op: str, params: Mapping[str, Any]) -> dict[str, Any]:
        before = self.undo_depth()
        result = call(self.context, op, params)
        self.assertEqual(self.undo_depth(), before + 1, f"{op} must record exactly one undo entry")
        return result


class CommentHandlerTests(_AnnotationHandlerCase):
    def test_create_comment_returns_record_and_one_undo_step(self) -> None:
        result = self.assert_one_undo_step("comment.upsert", {"node_id": self.node_id, "body": "Check the tolerance"})
        comment = result["comment"]
        self.assertEqual(result["comment_id"], comment["comment_id"])
        self.assertTrue(comment["comment_id"].startswith("comment_"))
        self.assertEqual(comment["body"], "Check the tolerance")
        self.assertEqual(comment["author"], "automation")
        self.assertFalse(comment["resolved"])
        self.assertFalse(comment["pinned"])
        self.assertFalse(comment["unread"], "automation-authored comments are not unread")
        self.assertEqual(comment["parent_id"], "")
        self.assertTrue(comment["created_at"])
        self.assertEqual(comment["updated_at"], comment["created_at"])
        self.assertEqual([record.comment_id for record in self.node().comments], [comment["comment_id"]])
        self.assertEqual(self.context.node_summary(self.node())["comment_count"], 1)

    def test_create_with_explicit_author_and_flags(self) -> None:
        result = call(
            self.context,
            "comment.upsert",
            {"node_id": self.node_id, "body": "Pinned note", "author": "reviewer", "pinned": True, "resolved": True},
        )
        self.assertEqual(result["comment"]["author"], "reviewer")
        self.assertTrue(result["comment"]["pinned"])
        self.assertTrue(result["comment"]["resolved"])

    def test_edit_keeps_author_and_flags_when_omitted(self) -> None:
        created = call(
            self.context,
            "comment.upsert",
            {"node_id": self.node_id, "body": "First draft", "author": "reviewer", "pinned": True},
        )["comment_id"]
        result = self.assert_one_undo_step("comment.upsert", {"node_id": self.node_id, "body": "Second draft", "comment_id": created})
        comment = result["comment"]
        self.assertEqual(result["comment_id"], created)
        self.assertEqual(comment["body"], "Second draft")
        self.assertEqual(comment["author"], "reviewer")
        self.assertTrue(comment["pinned"])
        self.assertFalse(comment["resolved"])
        self.assertEqual(len(self.node().comments), 1)

    def test_resolve_and_pin_through_upsert_are_single_undo_steps(self) -> None:
        created = call(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Open question"})["comment_id"]
        resolved = self.assert_one_undo_step(
            "comment.upsert", {"node_id": self.node_id, "body": "Open question", "comment_id": created, "resolved": True, "pinned": True}
        )
        self.assertTrue(resolved["comment"]["resolved"])
        self.assertTrue(resolved["comment"]["pinned"])
        record = self.node().comments[0]
        self.assertTrue(record.resolved)
        self.assertTrue(record.pinned)
        reopened = self.assert_one_undo_step(
            "comment.upsert", {"node_id": self.node_id, "body": "Open question", "comment_id": created, "resolved": False, "pinned": False}
        )
        self.assertFalse(reopened["comment"]["resolved"])
        self.assertFalse(reopened["comment"]["pinned"])

    def test_reply_requires_existing_parent_on_the_same_node(self) -> None:
        parent = call(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Parent"})["comment_id"]
        error = expect_error(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Orphan", "parent_id": "comment_missing"}, "INVALID_PARAMS")
        self.assertTrue(any("parent_id" in problem for problem in error.details["problems"]))
        reply = self.assert_one_undo_step("comment.upsert", {"node_id": self.node_id, "body": "Reply", "parent_id": parent})
        self.assertEqual(reply["comment"]["parent_id"], parent)
        other_node = self.context.scene.add_node_from_type(PROCESS, 200.0, 0.0)
        expect_error(self.context, "comment.upsert", {"node_id": other_node, "body": "Cross-node", "parent_id": parent}, "INVALID_PARAMS")
        # A reply cannot be re-parented, and a comment cannot be its own parent.
        expect_error(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Reply", "comment_id": reply["comment_id"], "parent_id": reply["comment_id"]}, "INVALID_PARAMS")
        other_parent = call(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Other parent"})["comment_id"]
        expect_error(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Reply", "comment_id": reply["comment_id"], "parent_id": other_parent}, "INVALID_PARAMS")

    def test_remove_comment_cascades_replies_in_one_undo_step(self) -> None:
        parent = call(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Parent"})["comment_id"]
        reply = call(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Reply", "parent_id": parent})["comment_id"]
        keep = call(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Unrelated"})["comment_id"]
        result = self.assert_one_undo_step("comment.remove", {"node_id": self.node_id, "comment_id": parent})
        self.assertTrue(result["removed"])
        self.assertEqual(sorted(result["removed_comment_ids"]), sorted([parent, reply]))
        self.assertEqual([record.comment_id for record in self.node().comments], [keep])
        expect_error(self.context, "comment.remove", {"node_id": self.node_id, "comment_id": parent}, "NOT_FOUND")

    def test_missing_node_comment_and_blank_body_errors(self) -> None:
        missing_node = expect_error(self.context, "comment.upsert", {"node_id": "node_missing", "body": "x"}, "NOT_FOUND")
        self.assertEqual(missing_node.details["kind"], "Node")
        missing_comment = expect_error(self.context, "comment.upsert", {"node_id": self.node_id, "body": "x", "comment_id": "comment_missing"}, "NOT_FOUND")
        self.assertEqual(missing_comment.details["kind"], "Comment")
        expect_error(self.context, "comment.remove", {"node_id": "node_missing", "comment_id": "comment_x"}, "NOT_FOUND")
        blank = expect_error(self.context, "comment.upsert", {"node_id": self.node_id, "body": "   "}, "INVALID_PARAMS")
        self.assertTrue(any("body" in problem for problem in blank.details["problems"]))
        expect_error(self.context, "comment.upsert", {"node_id": self.node_id, "body": ""}, "INVALID_PARAMS")
        expect_error(self.context, "comment.upsert", {"node_id": self.node_id, "body": "x", "bogus": 1}, "INVALID_PARAMS")
        self.assertEqual(self.node().comments, [])

    def test_undo_reverts_the_whole_comment_op(self) -> None:
        call(self.context, "comment.upsert", {"node_id": self.node_id, "body": "Undo me", "pinned": True})
        self.assertEqual(len(self.node().comments), 1)
        workspace = self.context.active_workspace()
        entry = self.context.runtime_history.undo_workspace(self.workspace_id, workspace)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.action_type, "automation:comment.upsert")
        self.assertEqual(self.node().comments, [])


class LinkHandlerTests(_AnnotationHandlerCase):
    def test_create_url_file_folder_links_in_order(self) -> None:
        url = self.assert_one_undo_step("link.upsert", {"node_id": self.node_id, "kind": "url", "title": "Docs", "target": "https://example.com/docs"})
        file_link = self.assert_one_undo_step("link.upsert", {"node_id": self.node_id, "kind": "file", "title": "Report", "target": "C:/reports/a.pdf", "subtitle": "latest"})
        folder = self.assert_one_undo_step("link.upsert", {"node_id": self.node_id, "kind": "folder", "title": "Runs", "target": "C:/runs"})
        self.assertEqual(url["link"]["position"], 0)
        self.assertEqual(file_link["link"]["position"], 1)
        self.assertEqual(folder["link"]["position"], 2)
        self.assertEqual(url["link"]["kind"], "url")
        self.assertEqual(url["link"]["target"], "https://example.com/docs")
        self.assertEqual(file_link["link"]["subtitle"], "latest")
        self.assertEqual(url["link_id"], url["link"]["link_id"])
        self.assertTrue(url["link_id"].startswith("link_"))
        self.assertEqual([record.link_id for record in self.node().links], [url["link_id"], file_link["link_id"], folder["link_id"]])
        self.assertEqual(self.context.node_summary(self.node())["link_count"], 3)

    def test_position_reorders_and_clamps(self) -> None:
        first = call(self.context, "link.upsert", {"node_id": self.node_id, "kind": "url", "title": "A", "target": "https://a"})["link_id"]
        second = call(self.context, "link.upsert", {"node_id": self.node_id, "kind": "url", "title": "B", "target": "https://b"})["link_id"]
        third = self.assert_one_undo_step("link.upsert", {"node_id": self.node_id, "kind": "url", "title": "C", "target": "https://c", "position": 0})
        self.assertEqual(third["link"]["position"], 0)
        self.assertEqual([record.link_id for record in self.node().links], [third["link_id"], first, second])
        moved = self.assert_one_undo_step("link.upsert", {"node_id": self.node_id, "kind": "url", "title": "A", "target": "https://a", "link_id": first, "position": 99})
        self.assertEqual(moved["link"]["position"], 2)
        self.assertEqual([record.link_id for record in self.node().links], [third["link_id"], second, first])
        # Same position is idempotent for ordering while the title edit still lands.
        edited = call(self.context, "link.upsert", {"node_id": self.node_id, "kind": "url", "title": "A2", "target": "https://a", "link_id": first, "position": 2})
        self.assertEqual(edited["link"]["title"], "A2")
        self.assertEqual(edited["link"]["position"], 2)
        self.assertEqual(self.node().links[2].title, "A2")

    def test_edit_requires_existing_link_id(self) -> None:
        error = expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "url", "title": "X", "target": "https://x", "link_id": "link_missing"}, "NOT_FOUND")
        self.assertEqual(error.details["kind"], "Link")
        self.assertEqual(self.node().links, [])

    def test_workspace_links_require_an_existing_workspace(self) -> None:
        result = self.assert_one_undo_step("link.upsert", {"node_id": self.node_id, "kind": "workspace", "title": "Here", "target": self.workspace_id})
        self.assertEqual(result["link"]["target"], self.workspace_id)
        via_field = call(self.context, "link.upsert", {"node_id": self.node_id, "kind": "workspace", "title": "Here too", "target_workspace_id": self.workspace_id})
        self.assertEqual(via_field["link"]["target"], self.workspace_id)
        missing = expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "workspace", "title": "Nope", "target": "ws_missing"}, "NOT_FOUND")
        self.assertEqual(missing.details["kind"], "Workspace")
        expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "workspace", "title": "Blank"}, "INVALID_PARAMS")

    def test_node_links_default_to_the_active_workspace(self) -> None:
        target = self.context.scene.add_node_from_type(PROCESS, 300.0, 0.0)
        result = self.assert_one_undo_step("link.upsert", {"node_id": self.node_id, "kind": "node", "title": "Next step", "target_node_id": target})
        link = result["link"]
        self.assertEqual(link["kind"], "node")
        self.assertEqual(link["target"], target)
        self.assertEqual(link["target_node_id"], target)
        self.assertEqual(link["target_workspace_id"], self.workspace_id)
        via_target = call(self.context, "link.upsert", {"node_id": self.node_id, "kind": "node", "title": "Alias", "target": target})
        self.assertEqual(via_target["link"]["target_node_id"], target)
        missing = expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "node", "title": "Nope", "target_node_id": "node_missing"}, "NOT_FOUND")
        self.assertEqual(missing.details["kind"], "Node")
        expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "node", "title": "Blank"}, "INVALID_PARAMS")

    def test_node_links_across_workspaces(self) -> None:
        second_workspace = self.context.workspace_manager.create_workspace("Second")
        remote = self.context.model.add_node(second_workspace, PROCESS, "Remote", 0.0, 0.0).node_id
        self.context.workspace_manager.set_active_workspace(self.workspace_id)
        self.assertEqual(self.context.workspace_id(), self.workspace_id)
        result = self.assert_one_undo_step(
            "link.upsert",
            {"node_id": self.node_id, "kind": "node", "title": "Remote", "target_node_id": remote, "target_workspace_id": second_workspace},
        )
        self.assertEqual(result["link"]["target_workspace_id"], second_workspace)
        self.assertEqual(result["link"]["target_node_id"], remote)
        record = self.node().links[0]
        self.assertEqual((record.kind, record.target_workspace_id, record.target_node_id), ("node", second_workspace, remote))
        # The remote node does not exist in the active workspace, and unknown workspaces are rejected.
        expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "node", "title": "Wrong ws", "target_node_id": remote}, "NOT_FOUND")
        wrong_workspace = expect_error(
            self.context,
            "link.upsert",
            {"node_id": self.node_id, "kind": "node", "title": "No ws", "target_node_id": remote, "target_workspace_id": "ws_missing"},
            "NOT_FOUND",
        )
        self.assertEqual(wrong_workspace.details["kind"], "Workspace")
        self.assertEqual(len(self.node().links), 1)

    def test_invalid_kind_target_and_title_errors(self) -> None:
        baseline = self.undo_depth()  # add_node_from_type in setUp already recorded one entry
        expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "ftp", "title": "X", "target": "ftp://x"}, "INVALID_PARAMS")
        url = expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "url", "title": "X"}, "INVALID_PARAMS")
        self.assertTrue(any("target" in problem for problem in url.details["problems"]))
        expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "file", "title": "X", "target": "  "}, "INVALID_PARAMS")
        expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "folder", "title": "X"}, "INVALID_PARAMS")
        expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "url", "title": "  ", "target": "https://x"}, "INVALID_PARAMS")
        expect_error(self.context, "link.upsert", {"node_id": self.node_id, "kind": "url", "title": "X", "target": "https://x", "position": -1}, "INVALID_PARAMS")
        expect_error(self.context, "link.upsert", {"node_id": "node_missing", "kind": "url", "title": "X", "target": "https://x"}, "NOT_FOUND")
        self.assertEqual(self.node().links, [])
        self.assertEqual(self.undo_depth(), baseline, "rejected ops must not record undo entries")

    def test_bad_position_is_rejected_before_the_link_is_created(self) -> None:
        # Call the handler directly (as graph.apply batches may) so the handler's own check is exercised.
        existing = call(self.context, "link.upsert", {"node_id": self.node_id, "kind": "url", "title": "A", "target": "https://a"})["link_id"]
        baseline_links = [(record.link_id, record.title) for record in self.node().links]
        baseline_depth = self.undo_depth()
        for bad in (-1, True, "2", 1.5):
            for link_id in ("", existing):
                with self.subTest(position=bad, edit=bool(link_id)):
                    params = {"node_id": self.node_id, "kind": "url", "title": "Changed", "target": "https://x", "position": bad}
                    if link_id:
                        params["link_id"] = link_id
                    with self.assertRaises(AutomationOpError) as raised:
                        upsert_link(self.context, params)
                    self.assertEqual(raised.exception.code, "INVALID_PARAMS")
                    self.assertTrue(any("position" in problem for problem in raised.exception.details["problems"]))
        self.assertEqual([(record.link_id, record.title) for record in self.node().links], baseline_links)
        self.assertEqual(self.undo_depth(), baseline_depth, "a rejected position must not record anything")

    def test_remove_link(self) -> None:
        link_id = call(self.context, "link.upsert", {"node_id": self.node_id, "kind": "url", "title": "Docs", "target": "https://example.com"})["link_id"]
        result = self.assert_one_undo_step("link.remove", {"node_id": self.node_id, "link_id": link_id})
        self.assertEqual(result, {"removed": True})
        self.assertEqual(self.node().links, [])
        missing = expect_error(self.context, "link.remove", {"node_id": self.node_id, "link_id": link_id}, "NOT_FOUND")
        self.assertEqual(missing.details["kind"], "Link")
        expect_error(self.context, "link.remove", {"node_id": "node_missing", "link_id": link_id}, "NOT_FOUND")


class _FakeClient:
    def __init__(self, responses: Mapping[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._responses = dict(responses or {})

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((op, dict(params or {})))
        return dict(self._responses.get(op, {}))


class AnnotationsApiTests(unittest.TestCase):
    def test_comment_and_reply_build_minimal_params(self) -> None:
        client = _FakeClient()
        api = AnnotationsApi(client)
        api.comment("node_1", "Hello")
        api.reply("node_1", "comment_1", "Reply", author="bot")
        api.comment_upsert("node_1", "Edit", comment_id="comment_1", resolved=False, pinned=None)
        api.comment_remove("node_1", "comment_1")
        self.assertEqual(
            client.calls,
            [
                ("comment.upsert", {"node_id": "node_1", "body": "Hello"}),
                ("comment.upsert", {"node_id": "node_1", "body": "Reply", "parent_id": "comment_1", "author": "bot"}),
                ("comment.upsert", {"node_id": "node_1", "body": "Edit", "comment_id": "comment_1", "resolved": False}),
                ("comment.remove", {"node_id": "node_1", "comment_id": "comment_1"}),
            ],
        )

    def test_resolve_reads_the_comment_then_upserts_resolved(self) -> None:
        client = _FakeClient(
            {"graph.get_node": {"comments": [{"comment_id": "comment_1", "body": "Fix me", "author": "reviewer", "pinned": True}]}}
        )
        AnnotationsApi(client).resolve("node_1", "comment_1")
        self.assertEqual(client.calls[0], ("graph.get_node", {"node_id": "node_1"}))
        self.assertEqual(
            client.calls[1],
            ("comment.upsert", {"node_id": "node_1", "body": "Fix me", "comment_id": "comment_1", "author": "reviewer", "resolved": True, "pinned": True}),
        )

    def test_resolve_accepts_id_key_and_raises_not_found(self) -> None:
        client = _FakeClient({"graph.get_node": {"comments": [{"id": "comment_2", "body": "Alt"}]}})
        AnnotationsApi(client).resolve("node_1", "comment_2")
        self.assertEqual(client.calls[1][1]["comment_id"], "comment_2")
        with self.assertRaises(AutomationOpError) as raised:
            AnnotationsApi(_FakeClient({"graph.get_node": {"comments": []}})).resolve("node_1", "comment_9")
        self.assertEqual(raised.exception.code, "NOT_FOUND")

    def test_link_sugar_builds_kind_specific_params(self) -> None:
        client = _FakeClient()
        api = AnnotationsApi(client)
        api.link_url("node_1", "Docs", "https://example.com", position=0)
        api.link_file("node_1", "Report", "C:/a.pdf", subtitle="latest")
        api.link_folder("node_1", "Runs", "C:/runs")
        api.link_workspace("node_1", "Other", "ws_2")
        api.link_node("node_1", "Next", "node_2")
        api.link_node("node_1", "Remote", "node_3", "ws_2", link_id="link_1")
        api.link_remove("node_1", "link_1")
        self.assertEqual(
            client.calls,
            [
                ("link.upsert", {"node_id": "node_1", "kind": "url", "title": "Docs", "target": "https://example.com", "position": 0}),
                ("link.upsert", {"node_id": "node_1", "kind": "file", "title": "Report", "target": "C:/a.pdf", "subtitle": "latest"}),
                ("link.upsert", {"node_id": "node_1", "kind": "folder", "title": "Runs", "target": "C:/runs"}),
                ("link.upsert", {"node_id": "node_1", "kind": "workspace", "title": "Other", "target": "ws_2"}),
                ("link.upsert", {"node_id": "node_1", "kind": "node", "title": "Next", "target_node_id": "node_2"}),
                ("link.upsert", {"node_id": "node_1", "kind": "node", "title": "Remote", "target_node_id": "node_3", "target_workspace_id": "ws_2", "link_id": "link_1"}),
                ("link.remove", {"node_id": "node_1", "link_id": "link_1"}),
            ],
        )


if __name__ == "__main__":
    unittest.main()
