from __future__ import annotations

from ea_node_editor.nodes.builtins.plot.generic import (
    PLOT_NODE_CATEGORY_PATH,
    PLOT_NODE_DESCRIPTORS,
    PLOT_NODE_TYPE_IDS,
    GenericPlotNodePlugin,
)
from ea_node_editor.nodes.builtins.plot.dpf import (
    DPF_PLOT_CATEGORY_PATH,
    DPF_PLOT_NODE_DESCRIPTORS,
    DPF_PLOT_NODE_TYPE_IDS,
    DpfPlotNodePlugin,
)

__all__ = [
    "DPF_PLOT_CATEGORY_PATH",
    "DPF_PLOT_NODE_DESCRIPTORS",
    "DPF_PLOT_NODE_TYPE_IDS",
    "DpfPlotNodePlugin",
    "GenericPlotNodePlugin",
    "PLOT_NODE_CATEGORY_PATH",
    "PLOT_NODE_DESCRIPTORS",
    "PLOT_NODE_TYPE_IDS",
]
