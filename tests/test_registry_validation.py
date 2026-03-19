from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel, NodeInstance
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.nodes.bootstrap import build_default_registry
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

    def test_register_rejects_invalid_surface_family(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.bad_surface",
            display_name="Bad Surface",
            category="Tests",
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(),
            runtime_behavior="passive",
            surface_family="diagram",  # type: ignore[arg-type]
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

    def test_normalize_property_value_and_properties_fall_back_to_defaults(self) -> None:
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

        self.assertEqual(
            registry.normalize_properties("tests.normalize", {"count": "15"}, include_defaults=False),
            {"count": 15},
        )
        self.assertEqual(
            registry.normalize_properties("tests.normalize", {"count": "15"}, include_defaults=True),
            {"count": 15, "enabled": False},
        )

    def test_normalize_project_for_registry_preserves_unresolved_sidecar_payloads(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace

        known_source = model.add_node(workspace.workspace_id, "core.start", "Start", 0.0, 0.0)
        known_target = model.add_node(workspace.workspace_id, "core.end", "End", 320.0, 0.0)
        unknown_node = NodeInstance(
            node_id="node_unknown",
            type_id="plugin.missing_step",
            title="Missing Step",
            x=160.0,
            y=0.0,
            collapsed=True,
            properties={"threshold": 0.5},
            exposed_ports={"plugin_in": True},
            visual_style={"fill": "#556677"},
        )
        workspace.nodes[unknown_node.node_id] = unknown_node

        valid_edge = model.add_edge(
            workspace.workspace_id,
            known_source.node_id,
            "exec_out",
            known_target.node_id,
            "exec_in",
        )
        mixed_edge = model.add_edge(
            workspace.workspace_id,
            unknown_node.node_id,
            "plugin_out",
            known_target.node_id,
            "exec_in",
        )

        normalize_project_for_registry(model.project, registry)

        self.assertNotIn(unknown_node.node_id, workspace.nodes)
        self.assertEqual(set(workspace.unresolved_node_docs), {unknown_node.node_id})
        self.assertEqual(
            workspace.unresolved_node_docs[unknown_node.node_id]["visual_style"],
            {"fill": "#556677"},
        )
        self.assertEqual(set(workspace.edges), {valid_edge.edge_id})
        self.assertEqual(set(workspace.unresolved_edge_docs), {mixed_edge.edge_id})
        self.assertEqual(
            workspace.unresolved_edge_docs[mixed_edge.edge_id],
            {
                "edge_id": mixed_edge.edge_id,
                "source_node_id": unknown_node.node_id,
                "source_port_key": "plugin_out",
                "target_node_id": known_target.node_id,
                "target_port_key": "exec_in",
                "label": "",
                "visual_style": {},
            },
        )


if __name__ == "__main__":
    unittest.main()
