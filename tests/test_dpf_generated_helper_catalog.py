from __future__ import annotations

import unittest

from ea_node_editor.addons.ansys_dpf.helper_catalog import (
    load_ansys_dpf_helper_plugin_descriptors,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_HELPERS_FACTORIES_CATEGORY_PATH,
    DPF_HELPERS_MODELS_CATEGORY_PATH,
    DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_INPUTS_CATEGORY_PATH,
    DPF_VIEWER_CATEGORY_PATH,
    DPF_WORKFLOW_CATEGORY_PATH,
)
from ea_node_editor.nodes.node_specs import (
    DPF_DATA_SOURCES_DATA_TYPE,
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_OBJECT_HANDLE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_STREAMS_CONTAINER_DATA_TYPE,
    DPF_WORKFLOW_DATA_TYPE,
)

_FOUNDATIONAL_HELPER_TYPE_IDS = (
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
)
_GENERATED_HELPER_TYPE_IDS = (
    "dpf.helper.data_sources.data_sources",
    "dpf.helper.data_sources.set_result_file_path",
    "dpf.helper.data_sources.add_upstream",
    "dpf.helper.streams_container.streams_container",
    "dpf.helper.model.model",
    "dpf.helper.workflow.workflow",
    "dpf.helper.fields_factory.field_from_array",
    "dpf.helper.fields_factory.create_scalar_field",
    "dpf.helper.fields_container_factory.over_time_freq_fields_container",
    "dpf.helper.mesh_scoping_factory.nodal_scoping",
    "dpf.helper.time_freq_scoping_factory.scoping_on_all_time_freqs",
)


class DpfGeneratedHelperCatalogTests(unittest.TestCase):
    def test_generated_helper_catalog_appends_curated_first_wave_helper_ids(self) -> None:
        descriptors = load_ansys_dpf_helper_plugin_descriptors()
        type_ids = tuple(descriptor.spec.type_id for descriptor in descriptors)

        self.assertEqual(type_ids[: len(_FOUNDATIONAL_HELPER_TYPE_IDS)], _FOUNDATIONAL_HELPER_TYPE_IDS)
        self.assertEqual(type_ids[len(_FOUNDATIONAL_HELPER_TYPE_IDS) :], _GENERATED_HELPER_TYPE_IDS)

    def test_generated_helper_category_paths_cover_curated_workflow_roles(self) -> None:
        descriptors = {
            descriptor.spec.type_id: descriptor.spec
            for descriptor in load_ansys_dpf_helper_plugin_descriptors()
        }

        self.assertEqual(descriptors["dpf.helper.data_sources.data_sources"].category_path, (*DPF_INPUTS_CATEGORY_PATH, "Result Setup"))
        self.assertEqual(descriptors["dpf.helper.data_sources.set_result_file_path"].category_path, (*DPF_INPUTS_CATEGORY_PATH, "Result Setup"))
        self.assertEqual(descriptors["dpf.helper.data_sources.add_upstream"].category_path, (*DPF_INPUTS_CATEGORY_PATH, "Result Setup"))
        self.assertEqual(descriptors["dpf.helper.streams_container.streams_container"].category_path, DPF_HELPERS_CONTAINERS_CATEGORY_PATH)
        self.assertEqual(descriptors["dpf.helper.model.model"].category_path, DPF_HELPERS_MODELS_CATEGORY_PATH)
        self.assertEqual(descriptors["dpf.helper.workflow.workflow"].category_path, (*DPF_WORKFLOW_CATEGORY_PATH, "Build"))
        self.assertEqual(descriptors["dpf.helper.fields_factory.field_from_array"].category_path, DPF_HELPERS_FACTORIES_CATEGORY_PATH)
        self.assertEqual(descriptors["dpf.helper.fields_factory.create_scalar_field"].category_path, DPF_HELPERS_FACTORIES_CATEGORY_PATH)
        self.assertEqual(descriptors["dpf.helper.fields_container_factory.over_time_freq_fields_container"].category_path, DPF_HELPERS_CONTAINERS_CATEGORY_PATH)
        self.assertEqual(descriptors["dpf.helper.mesh_scoping_factory.nodal_scoping"].category_path, DPF_HELPERS_SCOPING_CATEGORY_PATH)
        self.assertEqual(descriptors["dpf.helper.time_freq_scoping_factory.scoping_on_all_time_freqs"].category_path, DPF_HELPERS_SCOPING_CATEGORY_PATH)
        self.assertEqual(descriptors[DPF_VIEWER_NODE_TYPE_ID].category_path, DPF_VIEWER_CATEGORY_PATH)

    def test_generated_helper_samples_publish_callable_source_metadata_contracts(self) -> None:
        descriptors = {
            descriptor.spec.type_id: descriptor.spec
            for descriptor in load_ansys_dpf_helper_plugin_descriptors()
        }

        data_sources = descriptors["dpf.helper.data_sources.data_sources"]
        data_sources_ports = {port.key: port for port in data_sources.ports}
        data_sources_properties = {prop.key: prop for prop in data_sources.properties}
        self.assertEqual(data_sources.source_metadata.callable_kind, "constructor")
        self.assertEqual(data_sources.source_metadata.source_path, "ansys.dpf.core.data_sources.DataSources")
        self.assertEqual(data_sources.source_metadata.family_path, ("Inputs", "Result Setup"))
        self.assertEqual(data_sources_ports["data_sources"].data_type, DPF_DATA_SOURCES_DATA_TYPE)
        self.assertEqual(
            data_sources_ports["data_sources"].source_metadata.callable_binding.binding_kind,
            "return_value",
        )
        self.assertEqual(data_sources_properties["result_path"].source_metadata.callable_binding.binding_name, "result_path")

        data_sources_mutator = descriptors["dpf.helper.data_sources.set_result_file_path"]
        mutator_ports = {port.key: port for port in data_sources_mutator.ports}
        self.assertEqual(data_sources_mutator.source_metadata.callable_kind, "mutator")
        self.assertEqual(
            data_sources_mutator.source_metadata.source_path,
            "ansys.dpf.core.data_sources.DataSources.set_result_file_path",
        )
        self.assertEqual(mutator_ports["receiver"].data_type, DPF_OBJECT_HANDLE_DATA_TYPE)
        self.assertEqual(mutator_ports["receiver"].accepted_data_types, (DPF_DATA_SOURCES_DATA_TYPE,))
        self.assertEqual(
            mutator_ports["receiver"].source_metadata.callable_binding.binding_kind,
            "receiver",
        )
        self.assertEqual(mutator_ports["updated_receiver"].data_type, DPF_OBJECT_HANDLE_DATA_TYPE)

        add_upstream = descriptors["dpf.helper.data_sources.add_upstream"]
        add_upstream_ports = {port.key: port for port in add_upstream.ports}
        add_upstream_properties = {prop.key: prop for prop in add_upstream.properties}
        self.assertEqual(add_upstream.source_metadata.callable_kind, "mutator")
        self.assertEqual(
            add_upstream.source_metadata.source_path,
            "ansys.dpf.core.data_sources.DataSources.add_upstream",
        )
        self.assertEqual(add_upstream_ports["receiver"].accepted_data_types, (DPF_DATA_SOURCES_DATA_TYPE,))
        self.assertEqual(
            add_upstream_ports["receiver"].source_metadata.callable_binding.binding_kind,
            "receiver",
        )
        self.assertTrue(add_upstream_ports["upstream_data_sources"].required)
        self.assertEqual(
            add_upstream_ports["upstream_data_sources"].accepted_data_types,
            (DPF_DATA_SOURCES_DATA_TYPE,),
        )
        self.assertEqual(
            add_upstream_ports["upstream_data_sources"].source_metadata.callable_binding.binding_name,
            "upstream_data_sources",
        )
        self.assertEqual(add_upstream_ports["updated_receiver"].data_type, DPF_OBJECT_HANDLE_DATA_TYPE)
        self.assertEqual(add_upstream_properties["result_key"].type, "str")

        model = descriptors["dpf.helper.model.model"]
        model_ports = {port.key: port for port in model.ports}
        self.assertEqual(model.source_metadata.callable_name, "Model")
        self.assertTrue(model_ports["data_sources"].required)
        self.assertEqual(model_ports["data_sources"].data_type, DPF_DATA_SOURCES_DATA_TYPE)
        self.assertEqual(model_ports["model"].data_type, DPF_MODEL_DATA_TYPE)

        field_from_array = descriptors["dpf.helper.fields_factory.field_from_array"]
        field_from_array_ports = {port.key: port for port in field_from_array.ports}
        self.assertEqual(field_from_array.source_metadata.callable_kind, "factory")
        self.assertEqual(field_from_array_ports["arr"].data_type, "json")
        self.assertEqual(field_from_array_ports["field"].data_type, DPF_FIELD_DATA_TYPE)

        fields_container = descriptors["dpf.helper.fields_container_factory.over_time_freq_fields_container"]
        fields_container_ports = {port.key: port for port in fields_container.ports}
        self.assertEqual(fields_container_ports["field"].data_type, DPF_FIELD_DATA_TYPE)
        self.assertEqual(fields_container_ports["fields_container"].data_type, DPF_FIELDS_CONTAINER_DATA_TYPE)

        time_freq = descriptors["dpf.helper.time_freq_scoping_factory.scoping_on_all_time_freqs"]
        time_freq_ports = {port.key: port for port in time_freq.ports}
        self.assertEqual(time_freq_ports["obj"].data_type, DPF_OBJECT_HANDLE_DATA_TYPE)
        self.assertEqual(
            time_freq_ports["obj"].accepted_data_types,
            (DPF_MODEL_DATA_TYPE, DPF_DATA_SOURCES_DATA_TYPE),
        )
        self.assertEqual(time_freq_ports["scoping"].data_type, DPF_SCOPING_DATA_TYPE)

        workflow = descriptors["dpf.helper.workflow.workflow"]
        workflow_ports = {port.key: port for port in workflow.ports}
        self.assertEqual(workflow_ports["workflow"].data_type, DPF_WORKFLOW_DATA_TYPE)

        streams = descriptors["dpf.helper.streams_container.streams_container"]
        streams_ports = {port.key: port for port in streams.ports}
        self.assertEqual(streams_ports["streams_container"].data_type, DPF_STREAMS_CONTAINER_DATA_TYPE)


if __name__ == "__main__":
    unittest.main()
