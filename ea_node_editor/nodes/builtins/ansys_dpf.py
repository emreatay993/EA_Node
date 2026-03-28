"""Compatibility exports for the packet-owned DPF built-in split."""

from __future__ import annotations

from ea_node_editor.nodes.builtins.ansys_dpf_catalog import (
    ANSYS_DPF_NODE_PLUGINS,
    ANSYS_DPF_PLUGIN_DESCRIPTORS,
    PLUGIN_DESCRIPTORS,
)
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

__all__ = [
    "ANSYS_DPF_NODE_PLUGINS",
    "ANSYS_DPF_PLUGIN_DESCRIPTORS",
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
]
