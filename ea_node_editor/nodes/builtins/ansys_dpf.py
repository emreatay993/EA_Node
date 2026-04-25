from __future__ import annotations

from ea_node_editor.nodes.builtins.ansys_dpf_compute import (
    DpfExportNodePlugin,
    DpfFieldOpsNodePlugin,
    DpfMeshExtractNodePlugin,
    DpfMeshScopingNodePlugin,
    DpfModelNodePlugin,
    DpfResultFieldNodePlugin,
    DpfResultFileNodePlugin,
    DpfTimeScopingNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_viewer import DpfViewerNodePlugin


def __getattr__(name: str):
    if name in {"ANSYS_DPF_NODE_PLUGINS", "ANSYS_DPF_PLUGIN_DESCRIPTORS"}:
        from ea_node_editor.nodes.builtins import ansys_dpf_catalog

        return getattr(ansys_dpf_catalog, name)
    raise AttributeError(name)


__all__ = [
    "ANSYS_DPF_NODE_PLUGINS",
    "ANSYS_DPF_PLUGIN_DESCRIPTORS",
    "DpfExportNodePlugin",
    "DpfFieldOpsNodePlugin",
    "DpfMeshExtractNodePlugin",
    "DpfMeshScopingNodePlugin",
    "DpfModelNodePlugin",
    "DpfResultFieldNodePlugin",
    "DpfResultFileNodePlugin",
    "DpfTimeScopingNodePlugin",
    "DpfViewerNodePlugin",
]
