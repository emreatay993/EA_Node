from __future__ import annotations

import unittest
from pathlib import Path

from ea_node_editor.graph.subnode_contract import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_PIN_PORT_KEY,
    SUBNODE_TYPE_ID,
    default_subnode_pin_label,
    resolve_subnode_pin_definition,
)
from ea_node_editor.graph.model import GraphModel, NodeInstance, WorkspaceData
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.decorators import node_type
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import (
    NodeResult,
    NodeRenderQualitySpec,
    NodeTypeSpec,
    PluginDescriptor,
    PluginProvenance,
    PortSpec,
    PropertySpec,
)


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
    def test_workspace_data_owns_explicit_persistence_state_and_preserves_compatibility_properties(self) -> None:
        self.assertIn("persistence_state", WorkspaceData.__dataclass_fields__)
        self.assertNotIn("unresolved_node_docs", WorkspaceData.__dataclass_fields__)
        self.assertNotIn("unresolved_edge_docs", WorkspaceData.__dataclass_fields__)
        self.assertNotIn("authored_node_overrides", WorkspaceData.__dataclass_fields__)

        workspace = WorkspaceData(workspace_id="ws_test", name="Workspace")
        workspace.persistence_state.replace_unresolved_node_docs(
            {"node_missing": {"type_id": "plugin.missing"}}
        )
        workspace.persistence_state.replace_unresolved_edge_docs(
            {"edge_missing": {"source_node_id": "node_missing"}}
        )
        workspace.persistence_state.replace_authored_node_overrides(
            {"node_known": {"parent_node_id": "node_missing"}}
        )

        self.assertEqual(workspace.unresolved_node_docs["node_missing"]["type_id"], "plugin.missing")
        self.assertEqual(workspace.unresolved_edge_docs["edge_missing"]["source_node_id"], "node_missing")
        self.assertEqual(
            workspace.authored_node_overrides["node_known"]["parent_node_id"],
            "node_missing",
        )

    def test_duplicate_workspace_receives_independent_persistence_state_copy(self) -> None:
        model = GraphModel()
        source = model.active_workspace
        source.persistence_state.replace_unresolved_node_docs(
            {"node_missing": {"type_id": "plugin.missing"}}
        )
        source.persistence_state.replace_unresolved_edge_docs(
            {"edge_missing": {"source_node_id": "node_missing", "target_node_id": "node_known"}}
        )
        source.persistence_state.replace_authored_node_overrides(
            {"node_known": {"parent_node_id": "node_missing"}}
        )

        duplicate = model.duplicate_workspace(source.workspace_id)

        self.assertIsNot(duplicate.persistence_state, source.persistence_state)
        self.assertEqual(
            duplicate.persistence_state.unresolved_node_docs,
            source.persistence_state.unresolved_node_docs,
        )
        duplicate.persistence_state.unresolved_node_docs["node_missing"]["type_id"] = "plugin.changed"
        self.assertEqual(
            source.persistence_state.unresolved_node_docs["node_missing"]["type_id"],
            "plugin.missing",
        )

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

    def test_register_descriptor_stores_spec_without_instantiating_factory(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.descriptor",
            display_name="Descriptor",
            category="Tests",
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(),
        )
        factory_calls = 0

        def _descriptor_factory() -> _Plugin:
            nonlocal factory_calls
            factory_calls += 1
            return _Plugin(spec)

        provenance = PluginProvenance(
            kind="file",
            source_path=Path("C:/packet/tests/descriptor.py"),
        )
        registry.register_descriptor(
            PluginDescriptor(
                spec=spec,
                factory=_descriptor_factory,
                provenance=provenance,
            )
        )

        self.assertEqual(factory_calls, 0)
        self.assertEqual(registry.get_spec("tests.descriptor").display_name, "Descriptor")
        self.assertEqual(registry.get_descriptor("tests.descriptor").provenance, provenance)
        self.assertEqual(registry.all_descriptors()[0].provenance, provenance)
        self.assertEqual(registry.create("tests.descriptor").spec().type_id, "tests.descriptor")
        self.assertEqual(factory_calls, 1)

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

    def test_node_type_spec_defaults_render_quality_contract(self) -> None:
        spec = NodeTypeSpec(
            type_id="tests.render_quality_defaults",
            display_name="Render Quality Defaults",
            category="Tests",
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(),
        )

        self.assertEqual(spec.render_quality, NodeRenderQualitySpec())
        self.assertEqual(spec.render_quality.weight_class, "standard")
        self.assertEqual(spec.render_quality.max_performance_strategy, "generic_fallback")
        self.assertEqual(spec.render_quality.supported_quality_tiers, ("full",))

    def test_decorator_authored_nodes_publish_normalized_render_quality_contract(self) -> None:
        registry = NodeRegistry()

        @node_type(
            type_id="tests.decorated_render_quality",
            display_name="Decorated Render Quality",
            category="Tests",
            icon="",
            ports=(),
            properties=(),
            render_quality={
                "weight_class": "heavy",
                "max_performance_strategy": "proxy_surface",
                "supported_quality_tiers": ["full", "proxy", "proxy"],
            },
        )
        class _DecoratedRenderQualityNode:
            def execute(self, _ctx) -> NodeResult:  # noqa: ANN001
                return NodeResult()

        registry.register(lambda: _DecoratedRenderQualityNode())

        spec = registry.get_spec("tests.decorated_render_quality")
        self.assertEqual(spec.render_quality.weight_class, "heavy")
        self.assertEqual(spec.render_quality.max_performance_strategy, "proxy_surface")
        self.assertEqual(spec.render_quality.supported_quality_tiers, ("full", "proxy"))

    def test_render_quality_rejects_invalid_weight_class(self) -> None:
        with self.assertRaises(ValueError):
            NodeTypeSpec(
                type_id="tests.bad_render_quality",
                display_name="Bad Render Quality",
                category="Tests",
                icon="",
                ports=(PortSpec("value", "out", "data", "any"),),
                properties=(),
                render_quality={"weight_class": "ultra"},  # type: ignore[arg-type]
            )

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
        child_node = model.add_node(workspace.workspace_id, "core.logger", "Child", 200.0, 80.0)
        child_node.parent_node_id = unknown_node.node_id

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
        self.assertIsNone(workspace.nodes[child_node.node_id].parent_node_id)
        self.assertEqual(
            workspace.authored_node_overrides[child_node.node_id],
            {"parent_node_id": unknown_node.node_id},
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

    def test_default_registry_preserves_promoted_subnode_contract(self) -> None:
        registry = build_default_registry()

        shell_spec = registry.get_spec(SUBNODE_TYPE_ID)
        input_spec = registry.get_spec(SUBNODE_INPUT_TYPE_ID)
        output_spec = registry.get_spec(SUBNODE_OUTPUT_TYPE_ID)

        self.assertEqual(shell_spec.type_id, SUBNODE_TYPE_ID)
        self.assertEqual(input_spec.type_id, SUBNODE_INPUT_TYPE_ID)
        self.assertEqual(output_spec.type_id, SUBNODE_OUTPUT_TYPE_ID)
        self.assertEqual(input_spec.ports[0].key, SUBNODE_PIN_PORT_KEY)
        self.assertEqual(output_spec.ports[0].key, SUBNODE_PIN_PORT_KEY)

        exec_input = resolve_subnode_pin_definition(
            SUBNODE_INPUT_TYPE_ID,
            {"label": "Exec In", "kind": "exec", "data_type": "str"},
        )
        data_output = resolve_subnode_pin_definition(
            SUBNODE_OUTPUT_TYPE_ID,
            {"label": "Result", "kind": "data", "data_type": "float"},
        )

        self.assertEqual(default_subnode_pin_label(SUBNODE_INPUT_TYPE_ID), "Input")
        self.assertEqual(default_subnode_pin_label(SUBNODE_OUTPUT_TYPE_ID), "Output")
        self.assertEqual(exec_input.label, "Exec In")
        self.assertEqual(exec_input.pin_port_direction, "out")
        self.assertEqual(exec_input.shell_port_direction, "in")
        self.assertEqual(exec_input.kind, "exec")
        self.assertEqual(exec_input.data_type, "any")
        self.assertEqual(data_output.label, "Result")
        self.assertEqual(data_output.pin_port_direction, "in")
        self.assertEqual(data_output.shell_port_direction, "out")
        self.assertEqual(data_output.kind, "data")
        self.assertEqual(data_output.data_type, "float")


if __name__ == "__main__":
    unittest.main()
