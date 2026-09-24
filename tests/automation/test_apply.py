# Purpose: Shell-free tests for graph.apply: $ref wiring, static validation, one-undo-step pin, atomic rollback, non-atomic partials, scope handling, client facade.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_apply.py
from __future__ import annotations

import time
import unittest
from typing import Any

from ea_node_editor.automation.client_api.apply import ApplyApi, BatchBuilder, ref
from ea_node_editor.automation.errors import (
    APPLY_FAILED,
    INVALID_PARAMS,
    NOT_FOUND,
    UNKNOWN_OP,
)
from ea_node_editor.automation.ops.apply import APPLY, MAX_APPLY_OPS
from tests.automation.harness import build_context, call, expect_error

START = "passive.flowchart.start"
PROCESS = "passive.flowchart.process"
SHELL = "core.subnode"
PIN_OUT = "core.subnode_output"


def _node_add(batch_id: str | None, x: float = 0.0, title: str = "", type_id: str = PROCESS, **extra: Any) -> dict[str, Any]:
    params: dict[str, Any] = {"type_id": type_id, "x": float(x), "y": 0.0, **extra}
    if title:
        params["title"] = title
    entry: dict[str, Any] = {"op": "node.add", "params": params}
    if batch_id is not None:
        entry["id"] = batch_id
    return entry


def _bad_connect(source: str, target: str) -> dict[str, Any]:
    """edge.connect that passes static validation and fails at run time (unknown port -> NOT_FOUND)."""
    return {"op": "edge.connect", "params": {"source_node_id": source, "source_port": "nope", "target_node_id": target, "target_port": "left"}}


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def call(self, op: str, params: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((op, dict(params or {}), dict(kwargs)))
        return {"ok": True}


class _ApplyCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene

    def add(self, type_id: str = PROCESS, x: float = 0.0, y: float = 0.0) -> str:
        return self.scene.add_node_from_type(type_id, float(x), float(y))

    def undo_depth(self) -> int:
        return self.context.runtime_history.undo_depth(self.context.workspace_id())

    def node_ids(self) -> set[str]:
        return set(self.context.active_workspace().nodes)

    def edge_count(self) -> int:
        return len(self.context.active_workspace().edges)

    def apply(self, ops: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
        return call(self.context, "graph.apply", {"ops": ops, **extra})

    def apply_error(self, ops: list[dict[str, Any]], code: str, **extra: Any):
        return expect_error(self.context, "graph.apply", {"ops": ops, **extra}, code)


class HappyPathTests(_ApplyCase):
    def test_docstring_example_builds_the_flowchart_as_one_undo_step(self) -> None:
        example = APPLY.examples[0]
        depth = self.undo_depth()
        result = self.apply(list(example["ops"]), label=example["label"])

        self.assertEqual((result["applied"], result["failed_index"], result["rolled_back"]), (3, -1, False))
        self.assertEqual(sorted(result["ids"]), ["start", "step"])
        start = self.context.require_node(result["ids"]["start"])
        step = self.context.require_node(result["ids"]["step"])
        self.assertEqual((start.type_id, step.type_id), (START, PROCESS))
        self.assertEqual(self.edge_count(), 1)
        edge = next(iter(self.context.active_workspace().edges.values()))
        self.assertEqual((edge.source_node_id, edge.source_port_key), (start.node_id, "right"))
        self.assertEqual((edge.target_node_id, edge.target_port_key), (step.node_id, "left"))

        rows = result["results"]
        self.assertEqual([row["index"] for row in rows], [0, 1, 2])
        self.assertEqual([row["id"] for row in rows], ["start", "step", ""])
        self.assertEqual([row["op"] for row in rows], ["node.add", "node.add", "edge.connect"])
        self.assertTrue(all(row["ok"] for row in rows))
        self.assertEqual(rows[0]["result"]["node_id"], start.node_id)
        self.assertEqual(rows[2]["result"]["edge_id"], edge.edge_id)
        self.assertEqual(self.undo_depth(), depth + 1, "the whole batch is exactly one undo entry")

    def test_nested_field_and_list_index_refs(self) -> None:
        depth = self.undo_depth()
        result = self.apply(
            [
                _node_add("a", 0),
                _node_add("b", 300),
                {"id": "sub", "op": "subnode.create", "params": {"node_ids": ["$a", "$b"], "title": "Inner"}},
                {"id": "pin", "op": "subnode.add_pin", "params": {"shell_node_id": "$sub.shell_node_id", "direction": "out"}},
                {"id": "note", "op": "comment.upsert", "params": {"node_id": "$sub.member_node_ids.0", "body": "first member"}},
                {
                    "id": "link",
                    "op": "link.upsert",
                    "params": {"node_id": "$sub", "kind": "node", "title": "self", "target_node_id": "$sub.shell_node_id"},
                },
            ]
        )
        self.assertEqual(result["failed_index"], -1)
        ids = result["ids"]
        shell = self.context.require_node(ids["sub"])
        self.assertEqual(shell.type_id, SHELL)
        pin = self.context.require_node(ids["pin"])
        self.assertEqual((pin.type_id, pin.parent_node_id), (PIN_OUT, shell.node_id))
        first_member = result["results"][2]["result"]["member_node_ids"][0]
        self.assertIn(first_member, {ids["a"], ids["b"]})
        commented = self.context.require_node(first_member)
        self.assertEqual([record.body for record in commented.comments], ["first member"])
        self.assertEqual(ids["note"], commented.comments[0].comment_id)
        self.assertEqual([record.target_node_id for record in shell.links], [shell.node_id])
        self.assertEqual(ids["link"], shell.links[0].link_id)
        self.assertEqual(self.undo_depth(), depth + 1)

    def test_layout_ops_take_node_and_edge_refs_in_one_undo_step(self) -> None:
        depth = self.undo_depth()
        connect = {"source_port": "right", "target_port": "left"}
        result = self.apply(
            [
                {"id": "a", "op": "node.add", "params": {"type_id": PROCESS, "x": 0.0, "y": 0.0}},
                {"id": "b", "op": "node.add", "params": {"type_id": "passive.flowchart.decision", "x": 320.0, "y": 70.0}},
                {"id": "c", "op": "node.add", "params": {"type_id": PROCESS, "x": 640.0, "y": 150.0}},
                {"id": "ab", "op": "edge.connect", "params": {"source_node_id": "$a", "target_node_id": "$b", **connect}},
                {"id": "bc", "op": "edge.connect", "params": {"source_node_id": "$b", "target_node_id": "$c", **connect}},
                {"op": "layout.arrange", "params": {"node_ids": ["$a", "$b"], "action": "align_center_y"}},
                {"id": "tidy", "op": "layout.straighten", "params": {"edge_ids": ["$ab", "$bc"]}},
            ]
        )
        self.assertEqual(result["failed_index"], -1)
        straightened = result["results"][6]["result"]["straightened_edge_ids"]
        self.assertEqual(sorted(straightened), sorted([result["ids"]["ab"], result["ids"]["bc"]]))
        self.assertEqual(self.undo_depth(), depth + 1)

    def test_literal_dollars_outside_ref_fields_are_untouched_and_double_dollar_unescapes(self) -> None:
        result = self.apply(
            [
                _node_add("n", 0, title="Costs $100 for $n"),
                {"op": "comment.upsert", "params": {"node_id": "$n", "body": "Budget $$100 and $n stays verbatim"}},
            ]
        )
        node = self.context.require_node(result["ids"]["n"])
        self.assertEqual(result["results"][0]["result"]["node"]["title"], "Costs $100 for $n")
        self.assertEqual(node.properties.get("title", node.title), "Costs $100 for $n")
        self.assertEqual([record.body for record in node.comments], ["Budget $$100 and $n stays verbatim"])

        # A "$$"-escaped string in a ref field reaches the handler with one dollar stripped.
        error = self.apply_error([{"op": "node.update", "params": {"node_id": "$$literal-id", "title": "x"}}], APPLY_FAILED)
        self.assertEqual(error.details["error"]["code"], NOT_FOUND)
        self.assertEqual(error.details["error"]["details"]["id"], "$literal-id")


class StaticValidationTests(_ApplyCase):
    def setUp(self) -> None:
        super().setUp()
        self.existing = self.add(PROCESS, 0, 0)
        self.baseline_ids = self.node_ids()
        self.baseline_depth = self.undo_depth()

    def assert_untouched(self) -> None:
        self.assertEqual(self.node_ids(), self.baseline_ids)
        self.assertEqual(self.edge_count(), 0)
        self.assertEqual(self.undo_depth(), self.baseline_depth)

    def test_unknown_op_is_unknown_op_with_index_and_suggestions(self) -> None:
        error = self.apply_error([_node_add("a"), {"op": "node.ad", "params": {}}], UNKNOWN_OP)
        self.assertEqual(error.details["index"], 1)
        self.assertIn("node.add", error.details["suggestions"])
        self.assert_untouched()

    def test_non_apply_ops_are_rejected_with_a_separate_call_hint(self) -> None:
        for forbidden in ("project.save", "graph.apply", "capture.screenshot"):
            with self.subTest(op=forbidden):
                error = self.apply_error([_node_add("a"), {"op": forbidden, "params": {}}], INVALID_PARAMS)
                problems = error.details["problems"]
                self.assertTrue(any(problem.startswith(f"ops[1].op: '{forbidden}'") for problem in problems), problems)
                self.assertIn("separate call", " ".join(problems))
                self.assertIn("separate calls", error.hint)
                self.assertEqual(error.details["blocked_ops"], [forbidden])
        self.assert_untouched()

    def test_forward_self_and_unknown_refs_are_rejected(self) -> None:
        ops = [
            {"op": "edge.connect", "params": {"source_node_id": "$a", "source_port": "right", "target_node_id": "$b", "target_port": "left"}},
            _node_add("a", 0),
            _node_add("b", 300, parent_node_id="$b"),
            {"op": "node.delete", "params": {"node_ids": ["$a", "$ghost"]}},
        ]
        error = self.apply_error(ops, INVALID_PARAMS)
        problems = error.details["problems"]
        self.assertTrue(any(problem.startswith("ops[0].params.source_node_id: '$a'") for problem in problems), problems)
        self.assertTrue(any(problem.startswith("ops[0].params.target_node_id: '$b'") for problem in problems), problems)
        self.assertTrue(any(problem.startswith("ops[2].params.parent_node_id: '$b'") for problem in problems), problems)
        self.assertTrue(any(problem.startswith("ops[3].params.node_ids[1]: '$ghost'") for problem in problems), problems)
        self.assertFalse(any("node_ids[0]" in problem for problem in problems), problems)
        self.assert_untouched()

    def test_bare_ref_to_an_op_without_primary_id_is_rejected(self) -> None:
        ops = [
            {"id": "nav", "op": "scope.navigate", "params": {"target": "root"}},
            _node_add("a", 0, parent_node_id="$nav"),
        ]
        error = self.apply_error(ops, INVALID_PARAMS)
        self.assertTrue(any("ops[1].params.parent_node_id" in problem and "no primary id" in problem for problem in error.details["problems"]))
        self.assert_untouched()

    def test_duplicate_and_malformed_ids_are_rejected(self) -> None:
        error = self.apply_error([_node_add("a"), _node_add("a", 300), _node_add("1bad", 600), _node_add("", 900)], INVALID_PARAMS)
        problems = error.details["problems"]
        self.assertTrue(any(problem.startswith("ops[1].id: 'a' is already used by ops[0]") for problem in problems), problems)
        self.assertTrue(any(problem.startswith("ops[2].id: must match") for problem in problems), problems)
        self.assertTrue(any(problem.startswith("ops[3].id: must match") for problem in problems), problems)
        self.assert_untouched()

    def test_batch_size_limits(self) -> None:
        self.apply_error([_node_add(None)] * (MAX_APPLY_OPS + 1), INVALID_PARAMS)
        self.apply_error([], INVALID_PARAMS)
        self.assert_untouched()

    def test_inner_param_problems_are_reported_together_with_op_prefixes(self) -> None:
        ops = [
            {"id": "a", "op": "node.add", "params": {"type_id": PROCESS}},
            {"op": "edge.connect", "params": {"source_node_id": "$a", "source_port": "right", "target_node_id": "$zzz", "target_port": "left", "bogus": 1}},
        ]
        error = self.apply_error(ops, INVALID_PARAMS)
        problems = error.details["problems"]
        self.assertIn("ops[0].params.x: is required", problems)
        self.assertIn("ops[0].params.y: is required", problems)
        self.assertTrue(any(problem.startswith("ops[1].params.target_node_id: '$zzz'") for problem in problems), problems)
        self.assertIn("ops[1].params.bogus: unexpected parameter", problems)
        self.assert_untouched()


class RuntimeFailureTests(_ApplyCase):
    def setUp(self) -> None:
        super().setUp()
        self.existing = self.add(PROCESS, 0, 0)
        self.scene.clear_selection()
        self.scene.select_node(self.existing, True)
        self.assertEqual(self.context.selected_node_ids(), [self.existing])
        self.baseline_ids = self.node_ids()
        self.baseline_depth = self.undo_depth()
        self.ops = [_node_add("a", 0), _node_add("b", 300), _bad_connect("$a", "$b"), _node_add("c", 600)]

    def test_atomic_failure_rolls_back_and_raises_apply_failed(self) -> None:
        error = self.apply_error(self.ops, APPLY_FAILED)
        details = error.details
        self.assertEqual((details["failed_index"], details["failed_op"], details["failed_id"]), (2, "edge.connect", ""))
        self.assertTrue(details["rolled_back"])
        self.assertEqual(details["applied"], 0)
        self.assertEqual(details["error"]["code"], NOT_FOUND)
        self.assertEqual([row["ok"] for row in details["results"]], [True, True, False])
        self.assertEqual(details["results"][2]["error"]["code"], NOT_FOUND)
        self.assertEqual(details["ids"], {})
        self.assertIn("rolled back", error.hint)

        self.assertEqual(self.node_ids(), self.baseline_ids, "ops 1-2 were rolled back")
        self.assertEqual(self.edge_count(), 0)
        self.assertEqual(self.undo_depth(), self.baseline_depth, "a rolled-back batch records no undo entry")
        self.assertEqual(self.context.runtime_history.redo_depth(self.context.workspace_id()), 0)
        self.assertEqual(self.context.selected_node_ids(), [self.existing])
        self.assertEqual(self.context.scope_path(), [])
        # The workspace is fully usable afterwards: a follow-up mutation is one fresh undo step.
        call(self.context, "node.add", {"type_id": PROCESS, "x": 900, "y": 0})
        self.assertEqual(self.undo_depth(), self.baseline_depth + 1)

    def test_non_atomic_failure_keeps_earlier_ops_and_reports_the_row(self) -> None:
        result = self.apply(self.ops, atomic=False)
        self.assertEqual((result["applied"], result["failed_index"], result["rolled_back"]), (2, 2, False))
        self.assertEqual(sorted(result["ids"]), ["a", "b"])
        rows = result["results"]
        self.assertEqual([row["ok"] for row in rows], [True, True, False])
        self.assertEqual(rows[2]["error"]["code"], NOT_FOUND)
        self.assertEqual(rows[2]["op"], "edge.connect")
        self.assertEqual(self.node_ids() - self.baseline_ids, set(result["ids"].values()))
        self.assertEqual(self.undo_depth(), self.baseline_depth + 1, "the kept ops are one undo entry")

    def test_non_atomic_failure_on_the_first_op_raises_without_rollback(self) -> None:
        error = self.apply_error([_bad_connect(self.existing, self.existing), _node_add("a")], APPLY_FAILED, atomic=False)
        self.assertEqual((error.details["failed_index"], error.details["rolled_back"], error.details["applied"]), (0, False, 0))
        self.assertIn("Nothing was applied", error.hint)
        self.assertEqual(self.node_ids(), self.baseline_ids)
        self.assertEqual(self.undo_depth(), self.baseline_depth)

    def test_ref_path_that_does_not_resolve_fails_at_that_index(self) -> None:
        ops = [_node_add("a"), {"op": "node.update", "params": {"node_id": "$a.node.missing", "title": "x"}}]
        error = self.apply_error(ops, APPLY_FAILED)
        self.assertEqual(error.details["failed_index"], 1)
        self.assertEqual(error.details["error"]["code"], APPLY_FAILED)
        self.assertIn("$a.node.missing", error.details["error"]["message"])
        self.assertEqual(self.node_ids(), self.baseline_ids)
        self.assertEqual(self.undo_depth(), self.baseline_depth)


class ScopeTests(_ApplyCase):
    def test_navigate_inside_batch_then_rollbacks_restore_the_saved_scope(self) -> None:
        c = self.add(PROCESS, 0, 0)
        d = self.add(PROCESS, 300, 0)
        result = self.apply(
            [
                {"id": "sub", "op": "subnode.create", "params": {"node_ids": [c, d], "title": "Inner"}},
                {"op": "scope.navigate", "params": {"target": "node", "node_id": "$sub"}},
                _node_add("inner", 100),
            ]
        )
        shell_id = result["ids"]["sub"]
        inner = self.context.require_node(result["ids"]["inner"])
        self.assertEqual(inner.parent_node_id, shell_id, "ops after scope.navigate act inside the new scope")
        self.assertEqual(result["results"][1]["result"]["scope_path"], [shell_id])
        self.assertEqual(self.context.scope_path(), [shell_id], "a successful batch leaves the scope where it navigated")

        # Still inside the shell: a failing batch that navigated back to root must return to the shell scope.
        ids_before = self.node_ids()
        depth = self.undo_depth()
        error = self.apply_error(
            [{"op": "scope.navigate", "params": {"target": "root"}}, _node_add("x", 900), _bad_connect("$x", "$x")],
            APPLY_FAILED,
        )
        self.assertEqual(error.details["failed_index"], 2)
        self.assertEqual(self.context.scope_path(), [shell_id])
        self.assertEqual(self.node_ids(), ids_before)
        self.assertEqual(self.undo_depth(), depth)

        # From root: create a subnode, navigate into it, add a node there, fail -> back at root, shell gone.
        call(self.context, "scope.navigate", {"target": "root"})
        e = self.add(PROCESS, 0, 400)
        f = self.add(PROCESS, 300, 400)
        ids_before = self.node_ids()
        depth = self.undo_depth()
        error = self.apply_error(
            [
                {"id": "sub2", "op": "subnode.create", "params": {"node_ids": [e, f]}},
                {"op": "scope.navigate", "params": {"target": "node", "node_id": "$sub2"}},
                _node_add("inner2", 100),
                _bad_connect("$inner2", "$inner2"),
            ],
            APPLY_FAILED,
        )
        self.assertEqual(error.details["failed_index"], 3)
        self.assertEqual(error.details["results"][2]["ok"], True)
        self.assertEqual(self.context.scope_path(), [])
        self.assertEqual(self.node_ids(), ids_before)
        self.assertIsNone(self.context.require_node(e).parent_node_id)
        self.assertEqual(self.undo_depth(), depth)


class ThroughputTests(_ApplyCase):
    def test_sixty_node_adds_run_well_under_a_second(self) -> None:
        ops = [_node_add(f"n{i}", i * 20, title=f"Step {i}") for i in range(60)]
        started = time.perf_counter()
        result = self.apply(ops, label="sixty")
        elapsed = time.perf_counter() - started
        self.assertEqual(result["applied"], 60)
        self.assertEqual(len(result["ids"]), 60)
        self.assertEqual(len(self.node_ids()), 60)
        self.assertEqual(self.undo_depth(), 1)
        # Generous bound: a regression guard against pathological slowness, not a benchmark.
        self.assertLess(elapsed, 5.0, f"60-op batch took {elapsed:.3f}s")


class ClientFacadeTests(unittest.TestCase):
    def test_apply_api_builds_catalog_params(self) -> None:
        client = _RecordingClient()
        api = ApplyApi(client)
        ops = [{"id": "a", "op": "node.add", "params": {"type_id": PROCESS, "x": 0, "y": 0}}]
        api.apply(ops)
        api.apply(ops, atomic=False, label="Partial", timeout_s=120)
        self.assertEqual(client.calls[0], ("graph.apply", {"ops": ops, "atomic": True}, {}))
        self.assertEqual(client.calls[1], ("graph.apply", {"ops": ops, "atomic": False, "label": "Partial"}, {"timeout_s": 120.0}))
        self.assertIsNot(client.calls[0][1]["ops"][0], ops[0], "entries are copied, not aliased")

    def test_batch_builder_hands_out_refs_and_runs_through_the_client(self) -> None:
        client = _RecordingClient()
        batch = ApplyApi(client).batch()
        start = batch.add("node.add", {"type_id": START, "x": 0, "y": 0}, id="start")
        step = batch.add("node.add", {"type_id": PROCESS, "x": 320, "y": 0})
        edge = batch.add("edge.connect", {"source_node_id": start, "source_port": "right", "target_node_id": step, "target_port": "left"})
        self.assertEqual((start, step, edge), ("$start", "$op2", "$op3"))
        self.assertEqual(len(batch), 3)
        self.assertEqual([entry["id"] for entry in batch.ops], ["start", "op2", "op3"])
        self.assertEqual(batch.ops[2]["params"]["target_node_id"], "$op2")
        batch.run(label="Build")
        self.assertEqual(client.calls[-1][0], "graph.apply")
        self.assertEqual(client.calls[-1][1], {"ops": batch.ops, "atomic": True, "label": "Build"})
        with self.assertRaises(RuntimeError):
            BatchBuilder().run()
        with self.assertRaises(ValueError):
            batch.add("", {})

    def test_auto_ids_skip_user_supplied_names_and_ref_builds_paths(self) -> None:
        batch = BatchBuilder()
        batch.add("node.add", {}, id="op1")
        self.assertEqual(batch.add("node.add", {}), "$op2")
        self.assertEqual(ref("sub"), "$sub")
        self.assertEqual(ref("$sub", "member_node_ids.0"), "$sub.member_node_ids.0")
        with self.assertRaises(ValueError):
            ref("")


if __name__ == "__main__":
    unittest.main()
