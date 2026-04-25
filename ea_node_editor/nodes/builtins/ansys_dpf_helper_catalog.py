"""DPF helper descriptor catalog import boundary."""

from __future__ import annotations

from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
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


def load_ansys_dpf_helper_plugin_descriptors():
    from ea_node_editor.addons.ansys_dpf.helper_catalog import (
        load_ansys_dpf_helper_plugin_descriptors as _load_ansys_dpf_helper_plugin_descriptors,
    )

    descriptors_by_type_id = {
        descriptor.spec.type_id: descriptor
        for descriptor in _load_ansys_dpf_helper_plugin_descriptors()
    }
    return tuple(
        descriptors_by_type_id[type_id]
        for type_id in _FOUNDATIONAL_HELPER_TYPE_IDS
        if type_id in descriptors_by_type_id
    )


__all__ = [
    "load_ansys_dpf_helper_plugin_descriptors",
]
