"""Compatibility exports for the packet-owned DPF built-in split."""

from __future__ import annotations

from ea_node_editor.nodes.builtins import ansys_dpf_catalog

_CATALOG_EXPORTS = {
    "ANSYS_DPF_DEPENDENCY",
    "ANSYS_DPF_NODE_PLUGINS",
    "ANSYS_DPF_PLUGIN_BACKEND",
    "ANSYS_DPF_PLUGIN_DESCRIPTORS",
    "PLUGIN_BACKENDS",
    "PLUGIN_DESCRIPTORS",
    "get_ansys_dpf_plugin_availability",
    "load_ansys_dpf_plugin_descriptors",
}
_COMPUTE_EXPORTS = {
    "DpfExportNodePlugin",
    "DpfFieldOpsNodePlugin",
    "DpfMeshExtractNodePlugin",
    "DpfMeshScopingNodePlugin",
    "DpfModelNodePlugin",
    "DpfResultFieldNodePlugin",
    "DpfResultFileNodePlugin",
    "DpfTimeScopingNodePlugin",
}


def __getattr__(name: str):
    if name in _CATALOG_EXPORTS:
        return getattr(ansys_dpf_catalog, name)
    if name in _COMPUTE_EXPORTS:
        from ea_node_editor.nodes.builtins import ansys_dpf_compute

        return getattr(ansys_dpf_compute, name)
    if name == "DpfViewerNodePlugin":
        from ea_node_editor.nodes.builtins import ansys_dpf_viewer

        return ansys_dpf_viewer.DpfViewerNodePlugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ANSYS_DPF_DEPENDENCY",
    "ANSYS_DPF_NODE_PLUGINS",
    "ANSYS_DPF_PLUGIN_BACKEND",
    "ANSYS_DPF_PLUGIN_DESCRIPTORS",
    "PLUGIN_BACKENDS",
    "PLUGIN_DESCRIPTORS",
    "DpfExportNodePlugin",
    "DpfFieldOpsNodePlugin",
    "DpfMeshExtractNodePlugin",
    "DpfMeshScopingNodePlugin",
    "DpfModelNodePlugin",
    "DpfResultFieldNodePlugin",
    "DpfResultFileNodePlugin",
    "DpfTimeScopingNodePlugin",
    "DpfViewerNodePlugin",
    "get_ansys_dpf_plugin_availability",
    "load_ansys_dpf_plugin_descriptors",
]
