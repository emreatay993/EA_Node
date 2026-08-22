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
from ea_node_editor.nodes.builtins.plot.signal import (
    SIGNAL_PLOT_NODE_DESCRIPTOR,
    SIGNAL_PLOT_TYPE_ID,
    SignalPlotNodePlugin,
)

PLOT_NODE_DESCRIPTORS = (*PLOT_NODE_DESCRIPTORS, SIGNAL_PLOT_NODE_DESCRIPTOR)
PLOT_NODE_TYPE_IDS = (*PLOT_NODE_TYPE_IDS, SIGNAL_PLOT_TYPE_ID)

__all__ = [
    "DPF_PLOT_CATEGORY_PATH",
    "DPF_PLOT_NODE_DESCRIPTORS",
    "DPF_PLOT_NODE_TYPE_IDS",
    "DpfPlotNodePlugin",
    "GenericPlotNodePlugin",
    "PLOT_NODE_CATEGORY_PATH",
    "PLOT_NODE_DESCRIPTORS",
    "PLOT_NODE_TYPE_IDS",
    "SIGNAL_PLOT_NODE_DESCRIPTOR",
    "SIGNAL_PLOT_TYPE_ID",
    "SignalPlotNodePlugin",
]
