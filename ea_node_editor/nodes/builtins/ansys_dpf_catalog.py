from __future__ import annotations

from collections.abc import Callable

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
from ea_node_editor.nodes.plugin_contracts import NodePlugin, PluginDescriptor


def _descriptor(factory: Callable[[], NodePlugin]) -> PluginDescriptor:
    return PluginDescriptor(spec=factory().spec(), factory=factory)


ANSYS_DPF_PLUGIN_DESCRIPTORS = (
    _descriptor(DpfResultFileNodePlugin),
    _descriptor(DpfModelNodePlugin),
    _descriptor(DpfMeshScopingNodePlugin),
    _descriptor(DpfTimeScopingNodePlugin),
    _descriptor(DpfResultFieldNodePlugin),
    _descriptor(DpfFieldOpsNodePlugin),
    _descriptor(DpfMeshExtractNodePlugin),
    _descriptor(DpfExportNodePlugin),
    _descriptor(DpfViewerNodePlugin),
)
PLUGIN_DESCRIPTORS = ANSYS_DPF_PLUGIN_DESCRIPTORS
ANSYS_DPF_NODE_PLUGINS = tuple(descriptor.factory for descriptor in ANSYS_DPF_PLUGIN_DESCRIPTORS)


__all__ = [
    "ANSYS_DPF_NODE_PLUGINS",
    "ANSYS_DPF_PLUGIN_DESCRIPTORS",
    "PLUGIN_DESCRIPTORS",
]
