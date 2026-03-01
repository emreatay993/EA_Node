from __future__ import annotations

import unittest

from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PortSpec, PropertySpec


class _Plugin:
    def __init__(self, spec: NodeTypeSpec) -> None:
        self._spec = spec

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, _ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult()


def _factory(spec: NodeTypeSpec):
    return lambda: _Plugin(spec)


class RegistryValidationTests(unittest.TestCase):
    def test_register_rejects_duplicate_port_keys(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.dup_ports",
            display_name="Dup Ports",
            category="Tests",
            icon="",
            ports=(
                PortSpec("value", "out", "data", "any"),
                PortSpec("value", "in", "data", "any"),
            ),
            properties=(),
        )
        with self.assertRaises(ValueError):
            registry.register(_factory(spec))

    def test_register_rejects_invalid_enum_default(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.bad_enum",
            display_name="Bad Enum",
            category="Tests",
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(
                PropertySpec(
                    "level",
                    "enum",
                    "fatal",
                    "Level",
                    enum_values=("info", "warning", "error"),
                ),
            ),
        )
        with self.assertRaises(ValueError):
            registry.register(_factory(spec))

    def test_register_rejects_non_serializable_json_default(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.bad_json_default",
            display_name="Bad Json Default",
            category="Tests",
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(PropertySpec("payload", "json", {"obj": object()}, "Payload"),),
        )
        with self.assertRaises(ValueError):
            registry.register(_factory(spec))

    def test_default_properties_are_deep_copied_per_instance(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.deep_copy",
            display_name="Deep Copy",
            category="Tests",
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(PropertySpec("payload", "json", {"items": []}, "Payload"),),
        )
        registry.register(_factory(spec))

        first = registry.default_properties("tests.deep_copy")
        second = registry.default_properties("tests.deep_copy")
        first["payload"]["items"].append("x")

        self.assertEqual(second["payload"], {"items": []})

    def test_normalize_property_value_falls_back_to_default_on_invalid_input(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.normalize",
            display_name="Normalize",
            category="Tests",
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(
                PropertySpec("count", "int", 7, "Count"),
                PropertySpec("enabled", "bool", False, "Enabled"),
            ),
        )
        registry.register(_factory(spec))

        self.assertEqual(registry.normalize_property_value("tests.normalize", "count", "15"), 15)
        self.assertEqual(registry.normalize_property_value("tests.normalize", "count", "bad"), 7)
        self.assertFalse(registry.normalize_property_value("tests.normalize", "enabled", "true"))


if __name__ == "__main__":
    unittest.main()
