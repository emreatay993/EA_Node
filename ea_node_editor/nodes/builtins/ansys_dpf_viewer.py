from __future__ import annotations

from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_NODE_CATEGORY,
    DPF_OUTPUT_MODE_BOTH,
    DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY,
    DPF_VIEWER_LIVE_POLICY_VALUES,
    DPF_VIEWER_NODE_TYPE_ID,
    dpf_output_mode_property,
    normalize_dpf_output_mode,
    normalize_dpf_viewer_live_policy,
    resolve_field_handle_and_object,
)
from ea_node_editor.nodes.builtins.ansys_dpf_node_helpers import require_model_input
from ea_node_editor.nodes.builtins.ansys_dpf_viewer_adapter import open_dpf_viewer_session_payload
from ea_node_editor.nodes.decorators import node_type
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.node_specs import (
    DPF_FIELD_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_VIEW_SESSION_DATA_TYPE,
    NodeRenderQualitySpec,
    PortSpec,
    PropertySpec,
)


@node_type(
    type_id=DPF_VIEWER_NODE_TYPE_ID,
    display_name="DPF Viewer",
    category=DPF_NODE_CATEGORY,
    icon="monitor",
    description="Caches a DPF viewer session and its proxy/live dataset state through the worker session service.",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("field", "in", "data", DPF_FIELD_DATA_TYPE, required=False),
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=False),
        PortSpec("mesh", "in", "data", DPF_MESH_DATA_TYPE, required=False),
        PortSpec("session", "out", "data", DPF_VIEW_SESSION_DATA_TYPE, exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(
        PropertySpec(
            "viewer_live_policy",
            "enum",
            DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY,
            "Viewer Live Policy",
            enum_values=DPF_VIEWER_LIVE_POLICY_VALUES,
            inspector_editor="enum",
        ),
        dpf_output_mode_property(default=DPF_OUTPUT_MODE_BOTH),
    ),
    surface_family="viewer",
    render_quality=NodeRenderQualitySpec(
        weight_class="heavy",
        max_performance_strategy="proxy_surface",
        supported_quality_tiers=("full", "proxy"),
    ),
)
class DpfViewerNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        output_mode = normalize_dpf_output_mode(
            ctx.properties.get("output_mode"),
            default=DPF_OUTPUT_MODE_BOTH,
        )
        live_policy = normalize_dpf_viewer_live_policy(
            ctx.properties.get("viewer_live_policy"),
            default=DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY,
        )
        model_ref, _ = require_model_input(ctx, node_name="DPF Viewer")
        field_ref, _ = resolve_field_handle_and_object(
            ctx,
            ctx.inputs.get("field"),
            node_name="DPF Viewer",
        )
        session_payload = open_dpf_viewer_session_payload(
            ctx,
            field_ref=field_ref,
            model_ref=model_ref,
            mesh_ref=ctx.inputs.get("mesh"),
            output_mode=output_mode,
            live_policy=live_policy,
        )
        return NodeResult(outputs={"session": session_payload, "exec_out": True})


__all__ = ["DpfViewerNodePlugin"]
