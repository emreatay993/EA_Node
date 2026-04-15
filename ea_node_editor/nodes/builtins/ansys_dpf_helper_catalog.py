from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
    normalize_dpf_descriptor_spec,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_HELPERS_SUPPORT_CATEGORY_PATH,
    DPF_INPUTS_CATEGORY_PATH,
    DPF_VIEWER_CATEGORY_PATH,
    DPF_WORKFLOW_CATEGORY_PATH,
)
from ea_node_editor.nodes.plugin_contracts import NodePlugin, PluginDescriptor


def _load_ansys_dpf_helper_plugin_factories() -> tuple[Callable[[], NodePlugin], ...]:
    from ea_node_editor.nodes.builtins.ansys_dpf_compute import (
        DpfExportNodePlugin,
        DpfMeshExtractNodePlugin,
        DpfMeshScopingNodePlugin,
        DpfModelNodePlugin,
        DpfResultFileNodePlugin,
        DpfTimeScopingNodePlugin,
    )
    from ea_node_editor.nodes.builtins.ansys_dpf_viewer import DpfViewerNodePlugin

    return (
        DpfResultFileNodePlugin,
        DpfModelNodePlugin,
        DpfMeshScopingNodePlugin,
        DpfTimeScopingNodePlugin,
        DpfMeshExtractNodePlugin,
        DpfExportNodePlugin,
        DpfViewerNodePlugin,
    )


_HELPER_CATEGORY_PATHS = {
    DPF_RESULT_FILE_NODE_TYPE_ID: DPF_INPUTS_CATEGORY_PATH,
    DPF_MODEL_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_MESH_SCOPING_NODE_TYPE_ID: DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_TIME_SCOPING_NODE_TYPE_ID: DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_MESH_EXTRACT_NODE_TYPE_ID: DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_EXPORT_NODE_TYPE_ID: DPF_HELPERS_SUPPORT_CATEGORY_PATH,
    DPF_VIEWER_NODE_TYPE_ID: DPF_VIEWER_CATEGORY_PATH,
}


def _build_helper_descriptor(factory: Callable[[], NodePlugin]) -> PluginDescriptor:
    normalized_spec = normalize_dpf_descriptor_spec(factory().spec())
    return PluginDescriptor(
        spec=replace(
            normalized_spec,
            category_path=_HELPER_CATEGORY_PATHS[normalized_spec.type_id],
        ),
        factory=factory,
    )


def load_ansys_dpf_helper_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    return tuple(_build_helper_descriptor(factory) for factory in _load_ansys_dpf_helper_plugin_factories())


__all__ = [
    "load_ansys_dpf_helper_plugin_descriptors",
]
