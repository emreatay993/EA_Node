from __future__ import annotations

import unittest

from ea_node_editor.graph import effective_ports
from ea_node_editor.nodes import node_specs
from ea_node_editor.nodes.node_specs import DpfPinSourceSpec, PortSpec


class DpfContractTests(unittest.TestCase):
    def test_normalize_dpf_type_id_preserves_specialized_object_families(self) -> None:
        self.assertEqual(node_specs.normalize_dpf_type_id("model"), node_specs.DPF_MODEL_DATA_TYPE)
        self.assertEqual(
            node_specs.normalize_dpf_type_id("ansys.dpf.core.meshed_region.MeshedRegion"),
            node_specs.DPF_MESH_DATA_TYPE,
        )
        self.assertEqual(
            node_specs.normalize_dpf_type_id("ansys.dpf.core.data_sources.DataSources"),
            node_specs.DPF_DATA_SOURCES_DATA_TYPE,
        )
        self.assertEqual(
            node_specs.normalize_dpf_type_id("ansys.dpf.core.workflow.Workflow"),
            node_specs.DPF_WORKFLOW_DATA_TYPE,
        )

    def test_normalize_dpf_type_id_falls_back_to_generic_object_handle(self) -> None:
        self.assertEqual(
            node_specs.normalize_dpf_type_id("ansys.dpf.core.custom.magic.CustomCarrier"),
            node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
        )

    def test_port_accepted_data_types_fall_back_to_primary_data_type_when_unset(self) -> None:
        port = PortSpec("result", "out", "data", node_specs.DPF_MODEL_DATA_TYPE)

        self.assertEqual(
            effective_ports.port_accepted_data_types(port),
            (node_specs.DPF_MODEL_DATA_TYPE,),
        )

    def test_ports_compatible_accept_declared_target_accepted_data_types(self) -> None:
        source = PortSpec("model", "out", "data", node_specs.DPF_MODEL_DATA_TYPE)
        target = PortSpec(
            "receiver",
            "in",
            "data",
            node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
            accepted_data_types=(
                node_specs.DPF_MODEL_DATA_TYPE,
                node_specs.DPF_DATA_SOURCES_DATA_TYPE,
            ),
        )

        self.assertTrue(effective_ports.ports_compatible(source, target))
        self.assertFalse(
            effective_ports.ports_compatible(
                PortSpec("field", "out", "data", node_specs.DPF_FIELD_DATA_TYPE),
                target,
            )
        )

    def test_callable_source_metadata_preserves_family_and_stability_tags(self) -> None:
        metadata = node_specs.DpfCallableSourceSpec(
            callable_name="fields_factory.create_scalar_field",
            callable_kind="factory",
            source_path="ansys.dpf.core.fields_factory.create_scalar_field",
            family_path=("Helpers", "Factories"),
            stability="advanced",
        )

        self.assertEqual(metadata.callable_kind, "factory")
        self.assertEqual(metadata.family_path, ("Helpers", "Factories"))
        self.assertEqual(metadata.stability, "advanced")

    def test_callable_parameter_binding_requires_a_binding_name(self) -> None:
        with self.assertRaises(ValueError):
            node_specs.DpfCallableBindingSpec("parameter")

    def test_dpf_pin_source_metadata_tracks_accepted_data_types_for_multi_type_inputs(self) -> None:
        source = DpfPinSourceSpec(
            pin_name="self",
            pin_direction="input",
            value_origin="port",
            value_key="receiver",
            data_type=node_specs.DPF_OBJECT_HANDLE_DATA_TYPE,
            accepted_data_types=(
                node_specs.DPF_MODEL_DATA_TYPE,
                node_specs.DPF_DATA_SOURCES_DATA_TYPE,
            ),
            callable_binding=node_specs.DpfCallableBindingSpec("receiver"),
        )

        self.assertEqual(
            source.accepted_data_types,
            (node_specs.DPF_MODEL_DATA_TYPE, node_specs.DPF_DATA_SOURCES_DATA_TYPE),
        )
        self.assertEqual(source.callable_binding.binding_kind, "receiver")


if __name__ == "__main__":
    unittest.main()
