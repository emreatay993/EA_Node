from __future__ import annotations

import unittest

from ea_node_editor.nodes.decorators import in_port, node_type, out_port, prop_int, prop_json, prop_str
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import ExecutionContext, NodeResult


@node_type(
    type_id="tests.decorated",
    display_name="Decorated Node",
    category="Tests",
    icon="code",
    ports=(
        in_port("input_value", data_type="int"),
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


class DecoratorSdkRc2Tests(unittest.TestCase):
    def test_decorator_builds_valid_spec_and_executes(self) -> None:
        registry = NodeRegistry()
        registry.register(_DecoratedPlugin)
        spec = registry.get_spec("tests.decorated")
        self.assertEqual(spec.display_name, "Decorated Node")
        self.assertEqual(spec.ports[0].key, "input_value")
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

