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
from ea_node_editor.nodes.builtins.ansys_dpf_viewer import DpfViewerNodePlugin


__all__ = [
    "DpfExportNodePlugin",
    "DpfFieldOpsNodePlugin",
    "DpfMeshExtractNodePlugin",
    "DpfMeshScopingNodePlugin",
    "DpfModelNodePlugin",
    "DpfResultFieldNodePlugin",
    "DpfResultFileNodePlugin",
    "DpfTimeScopingNodePlugin",
    "DpfViewerNodePlugin",
    "DpfWorkflowFieldMathNodePlugin",
    "DpfWorkflowMinMaxEnvelopeNodePlugin",
    "DpfWorkflowModeShapeViewerNodePlugin",
    "DpfWorkflowResultFieldsNodePlugin",
    "DpfWorkflowResultSourceNodePlugin",
    "DpfWorkflowResultViewerNodePlugin",
    "DpfWorkflowStressInvariantsNodePlugin",
    "DpfWorkflowTableExportNodePlugin",
    "DpfWorkflowTimeHistoryProbeNodePlugin",
]
