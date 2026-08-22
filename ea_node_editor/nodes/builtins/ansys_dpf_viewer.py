from __future__ import annotations

from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
)
from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_OUTPUT_MODE_BOTH,
    DPF_VIEWER_CATEGORY_PATH,
    DPF_VIEWER_NODE_TYPE_ID,
    dpf_output_mode_property,
    dpf_viewer_view_options_from_properties,
    dpf_viewer_view_property_pack,
    normalize_dpf_output_mode,
)
from ea_node_editor.nodes.builtins.ansys_dpf_node_helpers import require_model_input
from ea_node_editor.nodes.builtins.ansys_dpf_viewer_adapter import open_dpf_viewer_session_payload
from ea_node_editor.nodes.core_data_types import VIEWER_SESSION_DATA_TYPE_ID
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.node_specs import (
    NodeRenderQualitySpec,
    PortSpec,
)


@builtin_node_type(
    type_id=DPF_VIEWER_NODE_TYPE_ID,
    display_name="DPF Viewer",
    category_path=DPF_VIEWER_CATEGORY_PATH,
    description="Caches a DPF viewer session and its proxy/live dataset state through the worker session service.",
    ports=(
        PortSpec(
            "field",
            "in",
            "data",
            DPF_FIELD_DATA_TYPE,
            required=False,
            accepted_data_types=(DPF_FIELD_DATA_TYPE, DPF_FIELDS_CONTAINER_DATA_TYPE),
        ),
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=True),
        PortSpec("mesh", "in", "data", DPF_MESH_DATA_TYPE, required=False),
        PortSpec("session", "out", "data", VIEWER_SESSION_DATA_TYPE_ID, exposed=True),
    ),
    properties=(
        dpf_output_mode_property(default=DPF_OUTPUT_MODE_BOTH),
        *dpf_viewer_view_property_pack(),
    ),
    surface_family="viewer",
    render_quality=NodeRenderQualitySpec(
        supported_quality_tiers=("full", "proxy"),
    ),
)
class DpfViewerNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        output_mode = normalize_dpf_output_mode(
            ctx.properties.get("output_mode"),
            default=DPF_OUTPUT_MODE_BOTH,
        )
        view_options = dpf_viewer_view_options_from_properties(ctx.properties)
        model_ref, _ = require_model_input(ctx, node_name="DPF Viewer")
        session_payload = open_dpf_viewer_session_payload(
            ctx,
            field_ref=ctx.inputs.get("field"),
            model_ref=model_ref,
            mesh_ref=ctx.inputs.get("mesh"),
            output_mode=output_mode,
            view_options=view_options,
        )
        return NodeResult(outputs={"session": session_payload})


__all__ = ["DpfViewerNodePlugin"]
