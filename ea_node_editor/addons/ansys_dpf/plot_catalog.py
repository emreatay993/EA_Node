from __future__ import annotations

from ea_node_editor.nodes.builtins.plot.dpf import DPF_PLOT_NODE_DESCRIPTORS
from ea_node_editor.nodes.plugin_contracts import PluginDescriptor


def load_ansys_dpf_plot_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    return DPF_PLOT_NODE_DESCRIPTORS


__all__ = [
    "load_ansys_dpf_plot_plugin_descriptors",
]
