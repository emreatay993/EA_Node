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
from ea_node_editor.graph.model import GraphModel, NodeInstance, WorkspaceData, WorkspaceSnapshot
from ea_node_editor.graph.normalization import build_graph_fragment_payload, normalize_project_for_registry
from ea_node_editor.graph.transform_fragment_ops import (
    build_subtree_fragment_payload_data,
    encode_fragment_external_parent_id,
)
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_FIELD_OPS_VARIANT_NORM,
    DPF_NODE_CATEGORY_PATH,
    DPF_RESULT_FIELD_OPERATOR_VARIANT_KEY,
    DPF_TIME_SELECTION_EXCLUSIVE_GROUP,
)
from ea_node_editor.nodes.builtins.core import CORE_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.hpc import HPC_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.integrations import INTEGRATION_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_annotation import PASSIVE_ANNOTATION_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_flowchart import PASSIVE_FLOWCHART_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_media import PASSIVE_MEDIA_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_planning import PASSIVE_PLANNING_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.subnode import SUBNODE_NODE_DESCRIPTORS
from ea_node_editor.nodes import execution_context as node_execution_context
from ea_node_editor.nodes import node_specs, plugin_contracts, runtime_refs, types as node_types
from ea_node_editor.nodes.decorators import node_type
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import (
    DPF_MODEL_DATA_TYPE,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DpfOperatorSourceSpec,
    DpfOperatorVariantSpec,
    DpfPinSourceSpec,
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
    def test_workspace_models_do_not_expose_persistence_overlay_state(self) -> None:
        self.assertNotIn("persistence_state", WorkspaceData.__dataclass_fields__)
        self.assertNotIn("persistence_state", WorkspaceSnapshot.__dataclass_fields__)
        self.assertNotIn("unresolved_node_docs", WorkspaceData.__dataclass_fields__)
        self.assertNotIn("unresolved_edge_docs", WorkspaceData.__dataclass_fields__)
        self.assertNotIn("authored_node_overrides", WorkspaceData.__dataclass_fields__)

        workspace = WorkspaceData(workspace_id="ws_test", name="Workspace")
        snapshot = workspace.capture_snapshot()

        for owner in (workspace, snapshot):
            self.assertFalse(hasattr(owner, "capture_persistence_state"))
            self.assertFalse(hasattr(owner, "restore_persistence_state"))
            self.assertFalse(hasattr(owner, "unresolved_node_docs"))
            self.assertFalse(hasattr(owner, "unresolved_edge_docs"))
            self.assertFalse(hasattr(owner, "authored_node_overrides"))

    def test_duplicate_workspace_receives_independent_live_graph_copy(self) -> None:
        model = GraphModel()
        source = model.active_workspace
        node = model.add_node(
            source.workspace_id,
            "core.logger",
            "Logger",
            10.0,
            20.0,
            properties={"message": "source"},
        )

        duplicate = model.duplicate_workspace(source.workspace_id)
        duplicate_node = duplicate.nodes[node.node_id]

        self.assertEqual(duplicate_node.properties, {"message": "source"})
        duplicate_node.properties["message"] = "duplicate"
        self.assertEqual(source.nodes[node.node_id].properties, {"message": "source"})

    def test_workspace_snapshot_restores_live_graph_state_only(self) -> None:
        workspace = WorkspaceData(workspace_id="ws_test", name="Workspace")
        node = NodeInstance(
            node_id="node_logger",
            type_id="core.logger",
            title="Logger",
            x=10.0,
            y=20.0,
        )
        workspace.nodes[node.node_id] = node

        snapshot = workspace.capture_snapshot()

        workspace.nodes[node.node_id].title = "Changed"

        workspace.restore_snapshot(snapshot)

        self.assertEqual(workspace.nodes[node.node_id].title, "Logger")

    def test_workspace_snapshot_equality_tracks_live_graph_state(self) -> None:
        workspace = WorkspaceData(workspace_id="ws_test", name="Workspace")
        before = workspace.capture_snapshot()

        workspace.nodes["node_logger"] = NodeInstance(
            node_id="node_logger",
            type_id="core.logger",
            title="Logger",
            x=10.0,
            y=20.0,
        )
        after = workspace.capture_snapshot()

        self.assertNotEqual(before, after)

    def test_register_rejects_duplicate_port_keys(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.dup_ports",
            display_name="Dup Ports",
            category_path=("Tests",),
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
            category_path=("Tests",),
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

    def test_title_icon_contract_keeps_icon_authoring_field_and_descriptor_provenance(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.title_icon_descriptor",
            display_name="Title Icon Descriptor",
            category_path=("Tests",),
            icon="icons/title.svg",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(),
        )
        provenance = PluginProvenance(
            kind="file",
            source_path=Path("C:/packet/tests/plugin.py"),
        )

        registry.register_descriptor(
            PluginDescriptor(
                spec=spec,
                factory=_factory(spec),
                provenance=provenance,
            )
        )

        descriptor = registry.get_descriptor(spec.type_id)
        self.assertEqual(registry.get_spec(spec.type_id).icon, "icons/title.svg")
        self.assertEqual(descriptor.spec.icon, "icons/title.svg")
        self.assertEqual(descriptor.provenance, provenance)

    def test_nodes_types_is_curated_sdk_surface_and_nodes_package_uses_focused_modules(self) -> None:
        self.assertEqual(node_types.NodeTypeSpec.__module__, "ea_node_editor.nodes.node_specs")
        self.assertEqual(node_types.PortSpec.__module__, "ea_node_editor.nodes.node_specs")
        self.assertEqual(node_types.DpfOperatorSourceSpec.__module__, "ea_node_editor.nodes.node_specs")
        self.assertEqual(node_types.DpfPinSourceSpec.__module__, "ea_node_editor.nodes.node_specs")
        self.assertEqual(node_types.ExecutionContext.__module__, "ea_node_editor.nodes.execution_context")
        self.assertEqual(node_types.NodeResult.__module__, "ea_node_editor.nodes.execution_context")
        self.assertEqual(node_types.RuntimeArtifactRef.__module__, "ea_node_editor.nodes.runtime_refs")
        self.assertEqual(node_types.RuntimeHandleRef.__module__, "ea_node_editor.nodes.runtime_refs")
        self.assertEqual(node_types.PluginDescriptor.__module__, "ea_node_editor.nodes.plugin_contracts")
        self.assertEqual(node_types.PluginProvenance.__module__, "ea_node_editor.nodes.plugin_contracts")
        self.assertIs(node_types.NodeTypeSpec, node_specs.NodeTypeSpec)
        self.assertIs(node_types.DpfOperatorSourceSpec, node_specs.DpfOperatorSourceSpec)
        self.assertIs(node_types.DpfPinSourceSpec, node_specs.DpfPinSourceSpec)
        self.assertIs(node_types.ExecutionContext, node_execution_context.ExecutionContext)
        self.assertIs(node_types.RuntimeArtifactRef, runtime_refs.RuntimeArtifactRef)
        self.assertIs(node_types.PluginDescriptor, plugin_contracts.PluginDescriptor)
        self.assertNotIn("category_key", node_types.__all__)
        self.assertNotIn("category_path_matches_prefix", node_types.__all__)
        self.assertNotIn("inline_property_specs", node_types.__all__)
        self.assertNotIn("property_has_inline_editor", node_types.__all__)
        self.assertNotIn("property_inspector_editor", node_types.__all__)
        self.assertNotIn("property_visible_in_inspector", node_types.__all__)

        nodes_root = Path(__file__).resolve().parents[1] / "ea_node_editor" / "nodes"
        offenders = []
        for source_path in nodes_root.rglob("*.py"):
            if source_path.name == "types.py":
                continue
            text = source_path.read_text(encoding="utf-8")
            if "from ea_node_editor.nodes.types import" in text or "from .types import" in text:
                offenders.append(str(source_path.relative_to(nodes_root.parent.parent)))

        allowed_offenders = {"ea_node_editor\\nodes\\builtins\\ansys_dpf_helper_adapters.py"}
        self.assertEqual(sorted(set(offenders) - allowed_offenders), [])

    def test_default_builtin_catalog_is_registered_from_descriptor_records(self) -> None:
        descriptor_tables = (
            CORE_NODE_DESCRIPTORS,
            INTEGRATION_NODE_DESCRIPTORS,
            HPC_NODE_DESCRIPTORS,
            SUBNODE_NODE_DESCRIPTORS,
            PASSIVE_FLOWCHART_NODE_DESCRIPTORS,
            PASSIVE_PLANNING_NODE_DESCRIPTORS,
            PASSIVE_ANNOTATION_NODE_DESCRIPTORS,
            PASSIVE_MEDIA_NODE_DESCRIPTORS,
        )
        descriptors = [descriptor for table in descriptor_tables for descriptor in table]

        self.assertTrue(descriptors)
        self.assertTrue(all(isinstance(descriptor, PluginDescriptor) for descriptor in descriptors))
        self.assertEqual(len({descriptor.spec.type_id for descriptor in descriptors}), len(descriptors))
        self.assertIn("core.start", {descriptor.spec.type_id for descriptor in descriptors})
        self.assertIn("io.path_pointer", {descriptor.spec.type_id for descriptor in descriptors})

    def test_nested_category_sdk_node_type_spec_accepts_one_level_path(self) -> None:
        spec = NodeTypeSpec(
            type_id="tests.category_one_level",
            display_name="Category One Level",
            category_path=("  Tests  ",),
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(),
        )

        self.assertEqual(spec.category_path, ("Tests",))
        self.assertEqual(spec.category, "Tests")
        self.assertIsInstance(type(spec).category, property)
        self.assertIsNone(type(spec).category.fset)

    def test_nested_category_sdk_node_type_spec_accepts_ten_level_path(self) -> None:
        category_path = tuple(f"Level {index}" for index in range(1, 11))
        spec = NodeTypeSpec(
            type_id="tests.category_ten_level",
            display_name="Category Ten Level",
            category_path=category_path,
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(),
        )

        self.assertEqual(spec.category_path, category_path)
        self.assertEqual(
            spec.category,
            "Level 1 > Level 2 > Level 3 > Level 4 > Level 5 > "
            "Level 6 > Level 7 > Level 8 > Level 9 > Level 10",
        )

    def test_nested_category_sdk_node_type_spec_rejects_eleven_level_path(self) -> None:
        with self.assertRaises(ValueError):
            NodeTypeSpec(
                type_id="tests.category_eleven_level",
                display_name="Category Eleven Level",
                category_path=tuple(f"Level {index}" for index in range(1, 12)),
                icon="",
                ports=(PortSpec("value", "out", "data", "any"),),
                properties=(),
            )

    def test_nested_category_sdk_node_type_spec_rejects_empty_segments(self) -> None:
        for category_path in ((), ("",), ("  ",), ("Tests", ""), ("Tests", "  ")):
            with self.subTest(category_path=category_path):
                with self.assertRaises(ValueError):
                    NodeTypeSpec(
                        type_id="tests.category_empty_segment",
                        display_name="Category Empty Segment",
                        category_path=category_path,
                        icon="",
                        ports=(PortSpec("value", "out", "data", "any"),),
                        properties=(),
                    )

    def test_register_rejects_invalid_enum_default(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.bad_enum",
            display_name="Bad Enum",
            category_path=("Tests",),
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

    def test_explicit_text_editor_metadata_preserves_supported_editor(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.text_editor",
            display_name="Text Editor",
            category_path=("Tests",),
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(
                PropertySpec(
                    "notes",
                    "str",
                    "Ready",
                    "Notes",
                    inline_editor="text",
                    inspector_editor="text",
                ),
            ),
            runtime_behavior="passive",
            surface_family="annotation",
        )

        registry.register(_factory(spec))

        registered = registry.get_spec(spec.type_id)
        property_spec = registered.properties[0]
        self.assertEqual(node_specs.property_inspector_editor(property_spec), "text")
        self.assertEqual(node_specs.inline_property_specs(registered), (property_spec,))
        self.assertEqual(node_specs.inline_property_specs(registered)[0].inline_editor, "text")

    def test_untagged_string_properties_still_resolve_to_text_editor(self) -> None:
        property_spec = PropertySpec(
            "accent_color",
            "str",
            "#336699",
            "Accent Color",
        )
        spec = NodeTypeSpec(
            type_id="tests.untyped_color_text",
            display_name="Untagged Color Text",
            category_path=("Tests",),
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(property_spec,),
        )

        self.assertEqual(node_specs.property_inspector_editor(property_spec), "text")
        self.assertEqual(node_specs.inline_property_specs(spec), ())

    def test_register_accepts_dpf_source_metadata_contract(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.dpf.result_field_metadata",
            display_name="DPF Result Field Metadata",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "model",
                    "in",
                    "data",
                    DPF_MODEL_DATA_TYPE,
                    source_metadata=DpfPinSourceSpec(
                        pin_name="data_sources",
                        pin_direction="input",
                        value_origin="port",
                        value_key="model",
                        data_type=DPF_MODEL_DATA_TYPE,
                        presence="required",
                        omission_semantics="disallowed",
                    ),
                ),
                PortSpec(
                    "time_scoping",
                    "in",
                    "data",
                    DPF_SCOPING_DATA_TYPE,
                    source_metadata=DpfPinSourceSpec(
                        pin_name="time_scoping",
                        pin_direction="input",
                        value_origin="port",
                        value_key="time_scoping",
                        data_type=DPF_SCOPING_DATA_TYPE,
                        exclusive_group=DPF_TIME_SELECTION_EXCLUSIVE_GROUP,
                    ),
                ),
                PortSpec(
                    "field",
                    "out",
                    "data",
                    "dpf_field",
                    source_metadata=DpfPinSourceSpec(
                        pin_name="fields_container",
                        pin_direction="output",
                        value_origin="port",
                        value_key="field",
                        data_type="dpf_field",
                        variant_keys=(DPF_RESULT_FIELD_OPERATOR_VARIANT_KEY,),
                    ),
                ),
            ),
            properties=(
                PropertySpec(
                    "location",
                    "enum",
                    "auto",
                    "Location",
                    enum_values=("auto", "nodal"),
                    source_metadata=DpfPinSourceSpec(
                        pin_name="requested_location",
                        pin_direction="input",
                        value_origin="property",
                        value_key="location",
                        data_type="dpf_field",
                        omission_semantics="operator_default",
                    ),
                ),
            ),
            source_metadata=DpfOperatorSourceSpec(
                variants=(
                    DpfOperatorVariantSpec(
                        key=DPF_RESULT_FIELD_OPERATOR_VARIANT_KEY,
                        operator_name_template="result.{result_name}",
                    ),
                ),
            ),
        )

        registry.register(_factory(spec))

        registered = registry.get_spec(spec.type_id)
        self.assertEqual(
            registered.source_metadata.variants[0].operator_name_template,
            "result.{result_name}",
        )
        self.assertEqual(
            registered.ports[1].source_metadata.exclusive_group,
            DPF_TIME_SELECTION_EXCLUSIVE_GROUP,
        )
        self.assertEqual(
            registered.properties[0].source_metadata.omission_semantics,
            "operator_default",
        )

    def test_register_accepts_callable_dpf_source_metadata_contract(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.dpf.helper.data_sources_mutator",
            display_name="DPF Data Sources Mutator",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "receiver",
                    "in",
                    "data",
                    node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
                    accepted_data_types=(
                        DPF_MODEL_DATA_TYPE,
                        node_specs.DPF_DATA_SOURCES_DATA_TYPE,
                    ),
                    source_metadata=DpfPinSourceSpec(
                        pin_name="self",
                        pin_direction="input",
                        value_origin="port",
                        value_key="receiver",
                        data_type=node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
                        accepted_data_types=(
                            DPF_MODEL_DATA_TYPE,
                            node_specs.DPF_DATA_SOURCES_DATA_TYPE,
                        ),
                        callable_binding=node_specs.DpfCallableBindingSpec("receiver"),
                    ),
                ),
                PortSpec(
                    "result_path",
                    "in",
                    "data",
                    "path",
                    source_metadata=DpfPinSourceSpec(
                        pin_name="result_path",
                        pin_direction="input",
                        value_origin="port",
                        value_key="result_path",
                        data_type="path",
                        callable_binding=node_specs.DpfCallableBindingSpec("parameter", "result_path"),
                    ),
                ),
                PortSpec(
                    "updated_receiver",
                    "out",
                    "data",
                    node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
                    accepted_data_types=(node_specs.DPF_DATA_SOURCES_DATA_TYPE,),
                    source_metadata=DpfPinSourceSpec(
                        pin_name="return_value",
                        pin_direction="output",
                        value_origin="port",
                        value_key="updated_receiver",
                        data_type=node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
                        accepted_data_types=(node_specs.DPF_DATA_SOURCES_DATA_TYPE,),
                        callable_binding=node_specs.DpfCallableBindingSpec("return_value"),
                    ),
                ),
            ),
            properties=(
                PropertySpec(
                    "server",
                    "str",
                    "localhost",
                    "Server",
                    source_metadata=DpfPinSourceSpec(
                        pin_name="server",
                        pin_direction="input",
                        value_origin="property",
                        value_key="server",
                        data_type="str",
                        callable_binding=node_specs.DpfCallableBindingSpec("parameter", "server"),
                    ),
                ),
            ),
            source_metadata=node_specs.DpfCallableSourceSpec(
                callable_name="DataSources.set_result_file_path",
                callable_kind="mutator",
                source_path="ansys.dpf.core.data_sources.DataSources.set_result_file_path",
                family_path=("Inputs", "Result Setup"),
                stability="core",
            ),
        )

        registry.register(_factory(spec))

        registered = registry.get_spec(spec.type_id)
        self.assertEqual(registered.source_metadata.callable_kind, "mutator")
        self.assertEqual(registered.source_metadata.family_path, ("Inputs", "Result Setup"))
        self.assertEqual(
            registered.ports[0].accepted_data_types,
            (DPF_MODEL_DATA_TYPE, node_specs.DPF_DATA_SOURCES_DATA_TYPE),
        )
        self.assertEqual(
            registered.ports[2].source_metadata.callable_binding.binding_kind,
            "return_value",
        )

    def test_register_rejects_port_source_metadata_without_node_source_metadata(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.dpf.port_source_without_node_source",
            display_name="DPF Port Source Without Node Source",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "model",
                    "in",
                    "data",
                    DPF_MODEL_DATA_TYPE,
                    source_metadata=DpfPinSourceSpec(
                        pin_name="data_sources",
                        pin_direction="input",
                        value_origin="port",
                        value_key="model",
                        data_type=DPF_MODEL_DATA_TYPE,
                        presence="required",
                        omission_semantics="disallowed",
                    ),
                ),
            ),
            properties=(),
        )

        with self.assertRaises(ValueError):
            registry.register(_factory(spec))

    def test_register_rejects_invalid_dpf_source_metadata_shape(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.dpf.invalid_source_metadata",
            display_name="DPF Invalid Source Metadata",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "field",
                    "in",
                    "data",
                    "dpf_field",
                    source_metadata=DpfPinSourceSpec(
                        pin_name="fields_container",
                        pin_direction="input",
                        value_origin="property",
                        value_key="field",
                        data_type="dpf_field",
                        presence="required",
                        omission_semantics="disallowed",
                        variant_keys=(DPF_FIELD_OPS_VARIANT_NORM, "missing_variant"),
                    ),
                ),
            ),
            properties=(),
            source_metadata=DpfOperatorSourceSpec(
                variants=(
                    DpfOperatorVariantSpec(
                        key=DPF_FIELD_OPS_VARIANT_NORM,
                        operator_name="math.norm_fc",
                    ),
                ),
            ),
        )

        with self.assertRaises(ValueError):
            registry.register(_factory(spec))

    def test_register_rejects_dpf_source_metadata_with_mismatched_accepted_data_types(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.dpf.accepted_type_mismatch",
            display_name="DPF Accepted Type Mismatch",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "receiver",
                    "in",
                    "data",
                    node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
                    accepted_data_types=(
                        DPF_MODEL_DATA_TYPE,
                        node_specs.DPF_DATA_SOURCES_DATA_TYPE,
                    ),
                    source_metadata=DpfPinSourceSpec(
                        pin_name="self",
                        pin_direction="input",
                        value_origin="port",
                        value_key="receiver",
                        data_type=node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
                        accepted_data_types=(DPF_MODEL_DATA_TYPE,),
                        callable_binding=node_specs.DpfCallableBindingSpec("receiver"),
                    ),
                ),
            ),
            properties=(),
            source_metadata=node_specs.DpfCallableSourceSpec(
                callable_name="DataSources",
                callable_kind="constructor",
            ),
        )

        with self.assertRaises(ValueError):
            registry.register(_factory(spec))

    def test_register_rejects_non_serializable_json_default(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.bad_json_default",
            display_name="Bad Json Default",
            category_path=("Tests",),
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
            category_path=("Tests",),
            icon="",
            ports=(PortSpec("value", "out", "data", "any"),),
            properties=(),
            runtime_behavior="passive",
            surface_family="diagram",  # type: ignore[arg-type]
        )
        with self.assertRaises(ValueError):
            registry.register(_factory(spec))

    def test_register_accepts_neutral_flowchart_ports_with_matching_cardinal_side(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.neutral_flowchart",
            display_name="Neutral Flowchart",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "top",
                    "neutral",
                    "flow",
                    "flow",
                    side="top",
                    allow_multiple_connections=True,
                ),
                PortSpec(
                    "right",
                    "neutral",
                    "flow",
                    "flow",
                    side="right",
                    allow_multiple_connections=True,
                ),
            ),
            properties=(),
            runtime_behavior="passive",
            surface_family="flowchart",
            surface_variant="process",
        )

        registry.register(_factory(spec))

        registered = registry.get_spec("tests.neutral_flowchart")
        self.assertEqual(tuple(port.direction for port in registered.ports), ("neutral", "neutral"))
        self.assertEqual(tuple(port.side for port in registered.ports), ("top", "right"))

    def test_register_accepts_neutral_ports_on_passive_non_flowchart_nodes(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.passive_neutral_annotation",
            display_name="Passive Neutral Annotation",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "top",
                    "neutral",
                    "flow",
                    "flow",
                    side="top",
                    allow_multiple_connections=True,
                ),
            ),
            properties=(),
            runtime_behavior="passive",
            surface_family="annotation",
        )

        registry.register(_factory(spec))

        registered = registry.get_spec(spec.type_id)
        self.assertEqual(tuple(port.direction for port in registered.ports), ("neutral",))
        self.assertEqual(tuple(port.side for port in registered.ports), ("top",))

    def test_register_rejects_neutral_ports_on_active_nodes(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.bad_neutral_active",
            display_name="Bad Neutral Active",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "top",
                    "neutral",
                    "flow",
                    "flow",
                    side="top",
                    allow_multiple_connections=True,
                ),
            ),
            properties=(),
            surface_family="standard",
        )

        with self.assertRaises(ValueError):
            registry.register(_factory(spec))

    def test_register_rejects_neutral_ports_without_matching_cardinal_key(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.bad_neutral_side",
            display_name="Bad Neutral Side",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "branch",
                    "neutral",
                    "flow",
                    "flow",
                    side="right",
                    allow_multiple_connections=True,
                ),
            ),
            properties=(),
            surface_family="flowchart",
            surface_variant="decision",
        )

        with self.assertRaises(ValueError):
            registry.register(_factory(spec))

    def test_node_type_spec_defaults_render_quality_contract(self) -> None:
        spec = NodeTypeSpec(
            type_id="tests.render_quality_defaults",
            display_name="Render Quality Defaults",
            category_path=("Tests",),
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
            category_path=("Tests",),
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
                category_path=("Tests",),
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
            category_path=("Tests",),
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
            category_path=("Tests",),
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

    def test_normalize_project_for_registry_prunes_unknown_nodes_without_sidecars(self) -> None:
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
        self.assertIsNone(workspace.nodes[child_node.node_id].parent_node_id)
        self.assertEqual(set(workspace.edges), {valid_edge.edge_id})
        self.assertFalse(hasattr(workspace, "unresolved_node_docs"))
        self.assertFalse(hasattr(workspace, "unresolved_edge_docs"))
        self.assertFalse(hasattr(workspace, "authored_node_overrides"))
        self.assertNotIn(mixed_edge.edge_id, workspace.edges)

    def test_normalize_project_for_registry_prunes_missing_addon_without_placeholder_contract(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        addon_node = NodeInstance(
            node_id="node_signal_transform",
            type_id="addons.signal.transform",
            title="Signal Transform",
            x=120.0,
            y=40.0,
            collapsed=True,
            properties={"gain": 2.0},
            exposed_ports={"signal_in": True, "signal_out": True},
            visual_style={"fill": "#225588"},
        )
        workspace.nodes[addon_node.node_id] = addon_node

        normalize_project_for_registry(model.project, registry)

        self.assertNotIn(addon_node.node_id, workspace.nodes)
        self.assertFalse(hasattr(workspace, "unresolved_node_docs"))

    def test_normalize_project_for_registry_keeps_directed_neutral_flowchart_edges(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        source = model.add_node(workspace.workspace_id, "passive.flowchart.process", "Process", 20.0, 30.0)
        target = model.add_node(workspace.workspace_id, "passive.flowchart.process", "Process", 320.0, 30.0)
        edge = model.add_edge(
            workspace.workspace_id,
            source.node_id,
            "right",
            target.node_id,
            "left",
        )

        normalize_project_for_registry(model.project, registry)

        self.assertIn(edge.edge_id, workspace.edges)
        kept_edge = workspace.edges[edge.edge_id]
        self.assertEqual(kept_edge.source_port_key, "right")
        self.assertEqual(kept_edge.target_port_key, "left")

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

    def test_validated_mutation_service_round_trips_subnode_grouping_through_split_ops(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        mutations = model.validated_mutations(workspace.workspace_id, registry)

        start = mutations.add_node(type_id="core.start", title="Start", x=0.0, y=0.0)
        logger = mutations.add_node(type_id="core.logger", title="Logger", x=220.0, y=0.0)
        end = mutations.add_node(type_id="core.end", title="End", x=520.0, y=0.0)

        mutations.add_edge(
            source_node_id=start.node_id,
            source_port_key="exec_out",
            target_node_id=logger.node_id,
            target_port_key="exec_in",
        )
        mutations.add_edge(
            source_node_id=logger.node_id,
            source_port_key="exec_out",
            target_node_id=end.node_id,
            target_port_key="exec_in",
        )

        grouped = mutations.group_selection_into_subnode(
            selected_node_ids=[start.node_id, logger.node_id],
            scope_path=[],
            shell_x=140.0,
            shell_y=40.0,
        )

        self.assertIsNotNone(grouped)
        assert grouped is not None
        self.assertEqual(workspace.nodes[grouped.shell_node_id].type_id, SUBNODE_TYPE_ID)
        self.assertEqual(workspace.nodes[start.node_id].parent_node_id, grouped.shell_node_id)
        self.assertEqual(workspace.nodes[logger.node_id].parent_node_id, grouped.shell_node_id)
        self.assertEqual(len(grouped.created_pin_node_ids), 1)
        self.assertTrue(
            any(
                edge.source_node_id == grouped.shell_node_id
                and edge.target_node_id == end.node_id
                and edge.target_port_key == "exec_in"
                for edge in workspace.edges.values()
            )
        )

        ungrouped = model.mutation_service(workspace.workspace_id).ungroup_subnode(
            shell_node_id=grouped.shell_node_id
        )

        self.assertIsNotNone(ungrouped)
        assert ungrouped is not None
        self.assertEqual(ungrouped.removed_shell_node_id, grouped.shell_node_id)
        self.assertCountEqual(ungrouped.removed_pin_node_ids, grouped.created_pin_node_ids)
        self.assertNotIn(grouped.shell_node_id, workspace.nodes)
        self.assertIsNone(workspace.nodes[start.node_id].parent_node_id)
        self.assertIsNone(workspace.nodes[logger.node_id].parent_node_id)
        self.assertTrue(
            any(
                edge.source_node_id == start.node_id
                and edge.source_port_key == "exec_out"
                and edge.target_node_id == logger.node_id
                and edge.target_port_key == "exec_in"
                for edge in workspace.edges.values()
            )
        )
        self.assertTrue(
            any(
                edge.source_node_id == logger.node_id
                and edge.source_port_key == "exec_out"
                and edge.target_node_id == end.node_id
                and edge.target_port_key == "exec_in"
                for edge in workspace.edges.values()
            )
        )

    def test_graph_fragment_insert_remaps_subnode_shell_pin_port_keys(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        mutations = model.validated_mutations(workspace.workspace_id, registry)

        start = mutations.add_node(type_id="core.start", title="Start", x=0.0, y=0.0)
        logger = mutations.add_node(type_id="core.logger", title="Logger", x=220.0, y=0.0)
        end = mutations.add_node(type_id="core.end", title="End", x=520.0, y=0.0)
        mutations.add_edge(
            source_node_id=start.node_id,
            source_port_key="exec_out",
            target_node_id=logger.node_id,
            target_port_key="exec_in",
        )
        mutations.add_edge(
            source_node_id=logger.node_id,
            source_port_key="exec_out",
            target_node_id=end.node_id,
            target_port_key="exec_in",
        )
        grouped = mutations.group_selection_into_subnode(
            selected_node_ids=[start.node_id, logger.node_id],
            scope_path=[],
            shell_x=140.0,
            shell_y=40.0,
        )
        self.assertIsNotNone(grouped)
        assert grouped is not None
        original_pin_id = grouped.created_pin_node_ids[0]
        fragment_data = build_subtree_fragment_payload_data(
            workspace=workspace,
            selected_node_ids=[grouped.shell_node_id, end.node_id],
        )
        self.assertIsNotNone(fragment_data)
        assert fragment_data is not None
        fragment_payload = build_graph_fragment_payload(nodes=fragment_data["nodes"], edges=fragment_data["edges"])

        before_node_ids = set(workspace.nodes)
        inserted_node_ids = model.mutation_service(workspace.workspace_id).insert_graph_fragment(
            fragment_payload=fragment_payload,
            delta_x=800.0,
            delta_y=0.0,
        )

        self.assertTrue(inserted_node_ids)
        inserted_node_id_set = set(inserted_node_ids)
        self.assertTrue(inserted_node_id_set.isdisjoint(before_node_ids))
        inserted_shell_id = next(
            node_id
            for node_id in inserted_node_id_set
            if workspace.nodes[node_id].type_id == SUBNODE_TYPE_ID
        )
        inserted_pin_id = next(
            node_id
            for node_id in inserted_node_id_set
            if workspace.nodes[node_id].type_id == SUBNODE_OUTPUT_TYPE_ID
        )
        inserted_end_id = next(
            node_id
            for node_id in inserted_node_id_set
            if workspace.nodes[node_id].type_id == "core.end"
        )
        self.assertNotEqual(inserted_pin_id, original_pin_id)
        self.assertTrue(
            any(
                edge.source_node_id == inserted_shell_id
                and edge.source_port_key == inserted_pin_id
                and edge.target_node_id == inserted_end_id
                and edge.target_port_key == "exec_in"
                for edge in workspace.edges.values()
            )
        )

    def test_encoded_fragment_parent_keeps_external_parent_when_ids_collide(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        mutations = model.validated_mutations(workspace.workspace_id, registry)
        parent = mutations.add_node(type_id="core.logger", title="Parent", x=0.0, y=0.0)
        fragment_payload = build_graph_fragment_payload(
            nodes=[
                {
                    "ref_id": parent.node_id,
                    "type_id": "core.logger",
                    "title": "Child",
                    "x": 120.0,
                    "y": 80.0,
                    "collapsed": False,
                    "properties": {},
                    "locked_ports": {},
                    "exposed_ports": {},
                    "visual_style": {},
                    "parent_node_id": encode_fragment_external_parent_id(parent.node_id),
                    "custom_width": None,
                    "custom_height": None,
                }
            ],
            edges=[],
        )

        inserted_node_ids = model.mutation_service(workspace.workspace_id).insert_graph_fragment(
            fragment_payload=fragment_payload,
            delta_x=0.0,
            delta_y=0.0,
        )

        self.assertEqual(len(inserted_node_ids), 1)
        inserted = workspace.nodes[inserted_node_ids[0]]
        self.assertEqual(inserted.parent_node_id, parent.node_id)
        self.assertNotEqual(inserted.parent_node_id, inserted.node_id)

    def test_default_registry_accepts_foundational_dpf_port_types_in_filters(self) -> None:
        registry = build_default_registry()

        category_specs = registry.filter_nodes(category_path=DPF_NODE_CATEGORY_PATH)
        result_file_specs = registry.filter_nodes(data_type=DPF_RESULT_FILE_DATA_TYPE, direction="out")
        model_specs = registry.filter_nodes(data_type=DPF_MODEL_DATA_TYPE, direction="out")
        scoping_specs = registry.filter_nodes(data_type=DPF_SCOPING_DATA_TYPE, direction="out")

        self.assertTrue(
            {
                "dpf.result_file",
                "dpf.model",
                "dpf.scoping.mesh",
                "dpf.scoping.time",
                "dpf.viewer",
                "dpf.result_field",
                "dpf.export",
                "dpf.field_ops",
                "dpf.mesh_extract",
            }.issubset({spec.type_id for spec in category_specs})
        )
        self.assertIn("dpf.result_file", [spec.type_id for spec in result_file_specs])
        self.assertIn("dpf.model", [spec.type_id for spec in model_specs])
        self.assertTrue(
            {"dpf.scoping.mesh", "dpf.scoping.time"}.issubset(
                {spec.type_id for spec in scoping_specs}
            )
        )

    def test_filter_nodes_matches_ports_through_accepted_dpf_data_types(self) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.dpf.helper.multi_input",
            display_name="DPF Multi Input",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "receiver",
                    "in",
                    "data",
                    node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
                    accepted_data_types=(
                        DPF_MODEL_DATA_TYPE,
                        node_specs.DPF_DATA_SOURCES_DATA_TYPE,
                    ),
                ),
                PortSpec("result", "out", "data", node_specs.DPF_OBJECT_HANDLE_DATA_TYPE),
            ),
            properties=(),
        )
        registry.register(_factory(spec))

        model_matches = registry.filter_nodes(data_type=DPF_MODEL_DATA_TYPE, direction="in")
        data_sources_matches = registry.filter_nodes(
            data_type=node_specs.DPF_DATA_SOURCES_DATA_TYPE,
            direction="in",
        )
        object_handle_matches = registry.filter_nodes(
            data_type=node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
            direction="out",
        )

        self.assertEqual([match.type_id for match in model_matches], [spec.type_id])
        self.assertEqual([match.type_id for match in data_sources_matches], [spec.type_id])
        self.assertEqual([match.type_id for match in object_handle_matches], [spec.type_id])


if __name__ == "__main__":
    unittest.main()
