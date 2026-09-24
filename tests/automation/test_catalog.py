# Purpose: Pin the op catalog shape: 48 ops, unique names/tools, schema validity, ref_fields, validator semantics, JSON snapshot.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

import json
import unittest

from ea_node_editor.automation import op_catalog
from ea_node_editor.automation.errors import AutomationOpError
from ea_node_editor.automation.op_model import (
    apply_defaults,
    object_schema,
    string_schema,
    validate_params,
)

# Frozen MCP tool surface (plan table: 46 typed tools + graph_apply; layout_straighten added 2026-09-24).
EXPECTED_MCP_TOOLS = (
    "corex_status", "corex_history", "corex_quit",
    "catalog_list_node_types", "catalog_describe_node_type", "catalog_style_schema",
    "graph_get", "graph_get_node", "graph_find_nodes",
    "node_add", "node_add_text", "node_add_media", "node_add_web_panel",
    "node_update", "node_set_style", "node_delete", "node_duplicate",
    "edge_connect", "edge_update", "edge_delete",
    "group_wrap", "subnode_create", "subnode_ungroup", "subnode_add_pin",
    "scope_navigate", "selection_set", "layout_arrange", "layout_straighten",
    "comment_upsert", "comment_remove", "link_upsert", "link_remove",
    "workspace_list", "workspace_create", "workspace_update", "workspace_close",
    "view_create", "view_update", "view_close", "view_set_camera",
    "project_open", "project_save", "project_stage_file",
    "run_start", "run_status", "run_control",
    "capture_screenshot",
    "graph_apply",
)


def _schema_property_paths(schema: dict) -> set[str]:
    """All dotted param paths declared by an object schema ('a', 'a.b', 'ids[]')."""
    paths: set[str] = set()

    def walk(node: dict, prefix: str) -> None:
        for key, sub in (node.get("properties") or {}).items():
            path = f"{prefix}{key}"
            paths.add(path)
            if isinstance(sub, dict):
                if sub.get("type") == "array" and isinstance(sub.get("items"), dict):
                    paths.add(path + "[]")
                    walk(sub["items"], path + "[].")
                walk(sub, path + ".")

    walk(schema, "")
    return paths


class CatalogShapeTests(unittest.TestCase):
    def test_catalog_has_48_ops_with_unique_names_and_tools(self) -> None:
        ops = op_catalog.all_ops()
        self.assertEqual(len(ops), 48)
        names = [op.name for op in ops]
        self.assertEqual(len(names), len(set(names)))
        tools = [op.mcp_tool for op in ops if op.mcp_tool]
        self.assertEqual(len(tools), len(set(tools)))
        self.assertEqual(tuple(tools), EXPECTED_MCP_TOOLS)

    def test_domains_match_the_plan_table(self) -> None:
        by_domain = {domain: len(ops) for domain, ops in op_catalog.ops_by_domain().items()}
        self.assertEqual(
            by_domain,
            {
                "app": 3,
                "catalog": 3,
                "graph": 3,
                "node": 8,
                "edge": 3,
                "structure": 8,
                "annotations": 4,
                "workspace": 8,
                "project": 3,
                "run": 3,
                "capture": 1,
                "apply": 1,
            },
        )

    def test_every_op_has_object_schemas_summary_and_flags(self) -> None:
        for op in op_catalog.all_ops():
            with self.subTest(op=op.name):
                self.assertTrue(op.summary.strip())
                self.assertEqual(op.params.get("type"), "object")
                self.assertEqual(op.result.get("type"), "object")
                self.assertFalse(op.params.get("additionalProperties", False), "params must be closed")
                if op.apply_allowed:
                    self.assertNotEqual(op.name, "graph.apply")
                if op.mutates_graph:
                    self.assertTrue(op.mcp_tool)

    def test_ref_fields_point_at_declared_params(self) -> None:
        for op in op_catalog.all_ops():
            declared = _schema_property_paths(op.params)
            for ref_field in op.ref_fields:
                with self.subTest(op=op.name, ref_field=ref_field):
                    self.assertIn(ref_field, declared)

    def test_apply_allowed_ops_cover_graph_authoring_but_not_project_or_run(self) -> None:
        allowed = {op.name for op in op_catalog.apply_allowed_ops()}
        self.assertIn("node.add", allowed)
        self.assertIn("edge.connect", allowed)
        self.assertIn("group.wrap", allowed)
        self.assertIn("comment.upsert", allowed)
        for forbidden in ("graph.apply", "project.save", "project.open", "run.start", "app.quit", "workspace.close", "capture.screenshot"):
            self.assertNotIn(forbidden, allowed)

    def test_catalog_json_is_serialisable_and_lists_tools(self) -> None:
        payload = op_catalog.catalog_json()
        text = json.dumps(payload)
        restored = json.loads(text)
        self.assertEqual(restored["protocol"], 1)
        self.assertEqual(len(restored["ops"]), 48)
        self.assertEqual(restored["mcp_tools"]["graph_apply"], "graph.apply")
        self.assertEqual(restored["mcp_tools"]["corex_status"], "app.status")

    def test_op_lookup_by_name_and_tool(self) -> None:
        self.assertEqual(op_catalog.op_by_name("node.add").mcp_tool, "node_add")
        self.assertEqual(op_catalog.op_for_mcp_tool("node_add").name, "node.add")
        self.assertIsNone(op_catalog.op_for_mcp_tool("nope"))
        self.assertIsNone(op_catalog.op_or_none("node.nope"))
        with self.assertRaises(AutomationOpError) as raised:
            op_catalog.op_by_name("node.ad")
        self.assertEqual(raised.exception.code, "UNKNOWN_OP")
        self.assertIn("node.add", raised.exception.details["suggestions"])

    def test_validate_op_params_fills_defaults_and_rejects_unknown_keys(self) -> None:
        op = op_catalog.op_by_name("catalog.list_node_types")
        filled = op_catalog.validate_op_params(op, {})
        self.assertEqual(filled["runtime_behavior"], "any")
        self.assertEqual(filled["limit"], 200)
        with self.assertRaises(AutomationOpError) as raised:
            op_catalog.validate_op_params(op, {"limit": 0, "bogus": 1})
        problems = raised.exception.details["problems"]
        self.assertTrue(any("limit" in problem for problem in problems))
        self.assertTrue(any("bogus" in problem for problem in problems))

    def test_required_params_are_enforced(self) -> None:
        op = op_catalog.op_by_name("edge.connect")
        with self.assertRaises(AutomationOpError) as raised:
            op_catalog.validate_op_params(op, {"source_node_id": "a"})
        problems = raised.exception.details["problems"]
        self.assertTrue(any("target_node_id" in problem for problem in problems))


class SchemaValidatorTests(unittest.TestCase):
    def test_type_enum_range_and_length_checks(self) -> None:
        schema = object_schema(
            {
                "name": string_schema(min_length=1, enum=("a", "b")),
                "count": {"type": "integer", "minimum": 1, "maximum": 3},
                "flag": {"type": "boolean"},
                "ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "either": {"type": ["string", "null"]},
            },
            required=("name",),
        )
        self.assertEqual(validate_params(schema, {"name": "a", "count": 2, "flag": True, "ids": ["x"], "either": None}), [])
        problems = validate_params(schema, {"name": "c", "count": 0, "flag": "yes", "ids": [], "either": 3, "extra": 1})
        joined = "\n".join(problems)
        self.assertIn("params.name: must be one of", joined)
        self.assertIn("params.count: must be >= 1", joined)
        self.assertIn("params.flag: expected boolean", joined)
        self.assertIn("params.ids: must contain at least 1", joined)
        self.assertIn("params.either: expected string or null", joined)
        self.assertIn("params.extra: unexpected parameter", joined)

    def test_bool_is_not_a_number_and_pattern_applies(self) -> None:
        schema = object_schema({"n": {"type": "number"}, "s": {"type": "string", "pattern": r"^\$\w+$"}})
        self.assertEqual(validate_params(schema, {"n": 1.5, "s": "$ok"}), [])
        problems = validate_params(schema, {"n": True, "s": "nope"})
        self.assertEqual(len(problems), 2)

    def test_apply_defaults_is_recursive_and_non_mutating(self) -> None:
        schema = object_schema(
            {
                "mode": string_schema(default="x"),
                "inner": object_schema({"z": {"type": "integer", "default": 7}}),
                "rows": {"type": "array", "items": object_schema({"k": {"type": "string", "default": "d"}})},
            }
        )
        original = {"inner": {}, "rows": [{}]}
        filled = apply_defaults(schema, original)
        self.assertEqual(filled, {"inner": {"z": 7}, "rows": [{"k": "d"}], "mode": "x"})
        self.assertEqual(original, {"inner": {}, "rows": [{}]})

    def test_one_of_branches(self) -> None:
        schema = {"oneOf": [{"type": "string"}, object_schema({"a": {"type": "integer"}}, required=("a",))]}
        self.assertEqual(validate_params(schema, "text"), [])
        self.assertEqual(validate_params(schema, {"a": 1}), [])
        self.assertTrue(validate_params(schema, {"b": 1}))


if __name__ == "__main__":
    unittest.main()
