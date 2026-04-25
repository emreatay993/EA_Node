"""DPF operator descriptor catalog import boundary."""

from __future__ import annotations

from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
)
_FOUNDATIONAL_OPERATOR_TYPE_IDS = (
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_FIELD_OPS_NODE_TYPE_ID,
)


def load_ansys_dpf_operator_plugin_descriptors():
    from ea_node_editor.addons.ansys_dpf.operator_catalog import (
        load_ansys_dpf_operator_plugin_descriptors as _load_ansys_dpf_operator_plugin_descriptors,
    )

    descriptors_by_type_id = {
        descriptor.spec.type_id: descriptor
        for descriptor in _load_ansys_dpf_operator_plugin_descriptors()
    }
    return tuple(
        descriptors_by_type_id[type_id]
        for type_id in _FOUNDATIONAL_OPERATOR_TYPE_IDS
        if type_id in descriptors_by_type_id
    )


def _discovered_generated_operator_definitions():
    from ea_node_editor.addons.ansys_dpf.operator_catalog import (
        _discovered_generated_operator_definitions as discovered,
    )

    return discovered()


__all__ = [
    "_discovered_generated_operator_definitions",
    "load_ansys_dpf_operator_plugin_descriptors",
]
