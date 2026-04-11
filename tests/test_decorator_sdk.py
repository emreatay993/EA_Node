from __future__ import annotations

import unittest

from ea_node_editor.nodes.category_paths import (
    category_display,
    category_key,
    category_path_matches_prefix,
    normalize_category_path,
)
from ea_node_editor.nodes.decorators import (
    in_port,
    node_type,
    out_port,
    prop_bool,
    prop_enum,
    prop_float,
    prop_int,
    prop_json,
    prop_str,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import ExecutionContext, NodeResult


@node_type(
    type_id="tests.decorated",
    display_name="Decorated Node",
    category_path=("Tests",),
    icon="code",
    ports=(
        in_port("input_value", data_type="int", required=True),
        out_port("result", data_type="int"),
    ),
    properties=(
        prop_int("gain", 2, "Gain"),
        prop_str("name", "demo", "Name"),
        prop_json("payload", {"ok": True}, "Payload"),
    ),
)
class _DecoratedPlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        value = int(ctx.inputs.get("input_value", 0))
        gain = int(ctx.properties.get("gain", 1))
        return NodeResult(outputs={"result": value * gain})


class DecoratorSdkTests(unittest.TestCase):
    def test_nested_category_sdk_decorator_accepts_single_level_path(self) -> None:
        registry = NodeRegistry()

        @node_type(
            type_id="tests.decorated_single_category_path",
            display_name="Decorated Single Category Path",
            category_path=("  Tests  ",),
            icon="code",
            ports=(),
            properties=(),
        )
        class _DecoratedSingleCategoryPathPlugin:
            def execute(self, _ctx: ExecutionContext) -> NodeResult:
                return NodeResult()

        registry.register(lambda: _DecoratedSingleCategoryPathPlugin())
        spec = registry.get_spec("tests.decorated_single_category_path")

        self.assertEqual(spec.category_path, ("Tests",))
        self.assertEqual(spec.category, "Tests")

    def test_nested_category_sdk_helpers_normalize_display_key_and_prefix_match(self) -> None:
        path = (" Parent ", "Child", "Leaf ")

        self.assertEqual(normalize_category_path(path), ("Parent", "Child", "Leaf"))
        self.assertEqual(category_display(path), "Parent > Child > Leaf")
        self.assertEqual(category_key(path), category_key(("Parent", "Child", "Leaf")))
        self.assertNotEqual(category_key(path), category_display(path))
        self.assertTrue(category_path_matches_prefix(path, ("Parent", "Child")))
        self.assertFalse(category_path_matches_prefix(path, ("Parent", "Other")))

    def test_port_helpers_preserve_direction_and_connection_flags(self) -> None:
        inbound = in_port("incoming", kind="flow", data_type="flow", allow_multiple_connections=True)
        outbound = out_port("outgoing", kind="failed", data_type="any", exposed=False)

        self.assertEqual(inbound.direction, "in")
        self.assertEqual(inbound.kind, "flow")
        self.assertEqual(inbound.data_type, "flow")
        self.assertTrue(inbound.allow_multiple_connections)

        self.assertEqual(outbound.direction, "out")
        self.assertEqual(outbound.kind, "failed")
        self.assertEqual(outbound.data_type, "any")
        self.assertFalse(outbound.exposed)

    def test_property_helpers_build_expected_specs(self) -> None:
        enabled = prop_bool("enabled", True, "Enabled", inspector_editor="toggle")
        threshold = prop_float("threshold", 1.5, "Threshold")
        mode = prop_enum("mode", "fast", "Mode", values=("fast", "safe"), inspector_editor="enum")

        self.assertEqual(enabled.type, "bool")
        self.assertTrue(enabled.default)
        self.assertEqual(enabled.inspector_editor, "toggle")

        self.assertEqual(threshold.type, "float")
        self.assertAlmostEqual(float(threshold.default), 1.5, places=3)

        self.assertEqual(mode.type, "enum")
        self.assertEqual(mode.default, "fast")
        self.assertEqual(mode.enum_values, ("fast", "safe"))

    def test_decorator_builds_valid_spec_and_executes(self) -> None:
        registry = NodeRegistry()
        registry.register(_DecoratedPlugin)
        spec = registry.get_spec("tests.decorated")

        self.assertEqual(spec.display_name, "Decorated Node")
        self.assertEqual(spec.ports[0].key, "input_value")
        self.assertTrue(spec.ports[0].required)
        self.assertEqual(spec.properties[0].key, "gain")

        plugin = registry.create("tests.decorated")
        result = plugin.execute(
            ExecutionContext(
                run_id="run",
                node_id="node",
                workspace_id="ws",
                inputs={"input_value": 4},
                properties={"gain": 3},
                emit_log=lambda _level, _message: None,
            )
        )
        self.assertEqual(result.outputs["result"], 12)

    def test_decorator_defaults_are_registry_normalized(self) -> None:
        registry = NodeRegistry()
        registry.register(_DecoratedPlugin)

        defaults = registry.default_properties("tests.decorated")

        self.assertEqual(defaults["gain"], 2)
        self.assertEqual(defaults["name"], "demo")
        self.assertEqual(defaults["payload"], {"ok": True})


if __name__ == "__main__":
    unittest.main()
