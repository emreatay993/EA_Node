from __future__ import annotations

from ea_node_editor.nodes.builtins.ansys_dpf_curated import (
    DpfWorkflowResultFieldsNodePlugin,
    DpfWorkflowResultSourceNodePlugin,
    DpfWorkflowResultViewerNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_curated_post import (
    DpfWorkflowFieldMathNodePlugin,
    DpfWorkflowMinMaxEnvelopeNodePlugin,
    DpfWorkflowModeShapeViewerNodePlugin,
    DpfWorkflowStressInvariantsNodePlugin,
    DpfWorkflowTableExportNodePlugin,
    DpfWorkflowTimeHistoryProbeNodePlugin,
)
from ea_node_editor.nodes.plugin_contracts import PluginDescriptor


def load_ansys_dpf_curated_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    return (
        PluginDescriptor(
            spec=DpfWorkflowResultSourceNodePlugin().spec(),
            factory=DpfWorkflowResultSourceNodePlugin,
        ),
        PluginDescriptor(
            spec=DpfWorkflowResultFieldsNodePlugin().spec(),
            factory=DpfWorkflowResultFieldsNodePlugin,
        ),
        PluginDescriptor(
            spec=DpfWorkflowResultViewerNodePlugin().spec(),
            factory=DpfWorkflowResultViewerNodePlugin,
        ),
        PluginDescriptor(
            spec=DpfWorkflowMinMaxEnvelopeNodePlugin().spec(),
            factory=DpfWorkflowMinMaxEnvelopeNodePlugin,
        ),
        PluginDescriptor(
            spec=DpfWorkflowTimeHistoryProbeNodePlugin().spec(),
            factory=DpfWorkflowTimeHistoryProbeNodePlugin,
        ),
        PluginDescriptor(
            spec=DpfWorkflowStressInvariantsNodePlugin().spec(),
            factory=DpfWorkflowStressInvariantsNodePlugin,
        ),
        PluginDescriptor(
            spec=DpfWorkflowModeShapeViewerNodePlugin().spec(),
            factory=DpfWorkflowModeShapeViewerNodePlugin,
        ),
        PluginDescriptor(
            spec=DpfWorkflowFieldMathNodePlugin().spec(),
            factory=DpfWorkflowFieldMathNodePlugin,
        ),
        PluginDescriptor(
            spec=DpfWorkflowTableExportNodePlugin().spec(),
            factory=DpfWorkflowTableExportNodePlugin,
        ),
    )


__all__ = [
    "load_ansys_dpf_curated_plugin_descriptors",
]
