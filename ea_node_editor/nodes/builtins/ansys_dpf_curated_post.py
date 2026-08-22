from __future__ import annotations

from typing import Any

from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
)
from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_CURATED_MESH_SELECTION_VALUES,
    DPF_FIELD_MATH_OPERATION_VALUES,
    DPF_INVARIANT_VALUES,
    DPF_LOCATION_AUTO,
    DPF_MESH_SELECTION_ALL,
    DPF_MESH_SELECTION_CHOOSE_SCOPE,
    DPF_OUTPUT_MODE_BOTH,
    DPF_OUTPUT_MODE_MEMORY,
    DPF_OUTPUT_MODE_STORED,
    DPF_RESULT_FIELD_LOCATION_VALUES,
    DPF_TIME_HISTORY_MESH_SELECTION_VALUES,
    DPF_TIME_SCOPE_ALL_SETS,
    DPF_VIEWER_DEFORM_SCALE_AUTO,
    DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
    DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
    DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
    DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
    DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
    DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
    dpf_output_mode_property,
    dpf_time_scope_mode_property,
    dpf_viewer_view_options_from_properties,
    dpf_viewer_view_property_pack,
    normalize_dpf_output_mode,
    normalize_export_artifact_key,
    normalize_mesh_selection_mode,
    require_dpf_runtime_service,
    wrap_field_handle_as_fields_container,
)
from ea_node_editor.nodes.builtins.ansys_dpf_curated import (
    _curated_selection_properties,
    _extract_curated_fields,
    _result_file_and_model_from_path,
)
from ea_node_editor.nodes.builtins.ansys_dpf_node_helpers import (
    default_export_artifact_key,
    require_model_input,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import DPF_WORKFLOW_CATEGORY_PATH
from ea_node_editor.nodes.builtins.ansys_dpf_viewer_adapter import open_dpf_viewer_session_payload
from ea_node_editor.nodes.dpf_runtime_contracts import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
)
from ea_node_editor.nodes.core_data_types import VIEWER_SESSION_DATA_TYPE_ID
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.file_dialog_filters import ANSYS_DPF_RESULT_FILES_FILTER
from ea_node_editor.nodes.node_specs import (
    NodeRenderQualitySpec,
    PortSpec,
    PropertySpec,
)
from ea_node_editor.nodes.output_artifacts import (
    artifact_store_for_context,
    default_staging_workspace_root,
    persist_artifact_store,
)
from ea_node_editor.runtime_contracts import RuntimeHandleRef
from ea_node_editor.runtime_contracts.data_tree import resolve_single_run_inputs


def _selection_properties_without_result_name() -> tuple[PropertySpec, ...]:
    return tuple(
        spec
        for spec in _curated_selection_properties(include_path=False)
        if spec.key != "result_name"
    )


def _resolve_fields_container_input(
    ctx,  # noqa: ANN001
    value: Any,
    *,
    node_name: str,
    port_label: str,
) -> RuntimeHandleRef:
    runtime_ref = value if isinstance(value, RuntimeHandleRef) else None
    if runtime_ref is None:
        raise ValueError(
            f"{node_name} requires a DPF field or fields container on input {port_label}."
        )
    if (
        runtime_ref.data_type_id == DPF_FIELDS_CONTAINER_DATA_TYPE
        and runtime_ref.kind == DPF_FIELDS_CONTAINER_HANDLE_KIND
    ):
        return runtime_ref
    if (
        runtime_ref.data_type_id == DPF_FIELD_DATA_TYPE
        and runtime_ref.kind == DPF_FIELD_HANDLE_KIND
    ):
        return wrap_field_handle_as_fields_container(ctx, runtime_ref, node_name=node_name)
    raise TypeError(
        f"{node_name} input {port_label} must be a dpf.field or dpf.fields_container handle."
    )


def _mode_shape_mode_number(value: Any, *, node_name: str) -> int:
    text = str(value if value is not None else "").strip() or "1"
    try:
        mode = int(float(text)) if "." in text else int(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{node_name} mode must be a positive integer mode number.") from exc
    if mode < 1:
        raise ValueError(f"{node_name} mode must be a positive integer mode number.")
    return mode


def _mode_frequency(model: Any, mode: int) -> float | None:
    try:
        frequencies = list(model.metadata.time_freq_support.time_frequencies.data)
    except Exception:
        return None
    index = mode - 1
    if 0 <= index < len(frequencies):
        return float(frequencies[index])
    return None


@builtin_node_type(
    type_id=DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
    display_name="DPF Min/Max Envelope",
    category_path=DPF_WORKFLOW_CATEGORY_PATH,
    description=(
        "Extracts a scoped result over selected sets (all sets by default) and reduces it to "
        "per-entity min/max envelope fields, per-set extremes, and the overall extreme with its "
        "entity location. Vector results are norm-reduced; reduce tensors with DPF Stress "
        "Invariants first."
    ),
    surface_family="dpf_workflow",
    ports=(
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=True),
        PortSpec("envelope_min", "out", "data", DPF_FIELD_DATA_TYPE, exposed=True),
        PortSpec("envelope_max", "out", "data", DPF_FIELD_DATA_TYPE, exposed=True),
        PortSpec("fields", "out", "data", DPF_FIELDS_CONTAINER_DATA_TYPE, exposed=True),
        PortSpec("per_set_table", "out", "data", 'COREX.DataTypes.Any', exposed=True),
        PortSpec("summary", "out", "data", 'COREX.DataTypes.Any', exposed=True),
    ),
    properties=_curated_selection_properties(
        include_path=False,
        time_scope_default=DPF_TIME_SCOPE_ALL_SETS,
    ),
)
class DpfWorkflowMinMaxEnvelopeNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        node_name = "DPF Min/Max Envelope"
        model_ref, model = require_model_input(ctx, node_name=node_name)
        fields_ref, _, _ = _extract_curated_fields(
            ctx,
            model_ref=model_ref,
            model=model,
            node_name=node_name,
            default_time_scope_mode=DPF_TIME_SCOPE_ALL_SETS,
        )
        service = require_dpf_runtime_service(ctx, node_name=node_name)
        envelope = service.compute_min_max_envelope(
            fields_ref,
            model=model_ref,
            run_id=ctx.run_id,
        )
        return NodeResult(
            outputs={
                "envelope_min": envelope.envelope_min,
                "envelope_max": envelope.envelope_max,
                "fields": fields_ref,
                "per_set_table": [dict(row) for row in envelope.per_set_rows],
                "summary": dict(envelope.overall),
            }
        )


@builtin_node_type(
    type_id=DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
    display_name="DPF Time History Probe",
    category_path=DPF_WORKFLOW_CATEGORY_PATH,
    description=(
        "Probes a result at a named selection or explicit entity ids across selected sets "
        "(all sets by default) and shapes one curve per entity for the DPF plot nodes, with "
        "real time/frequency values on the X axis."
    ),
    surface_family="dpf_workflow",
    ports=(
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=True),
        PortSpec("series", "out", "data", DPF_FIELDS_CONTAINER_DATA_TYPE, exposed=True),
        PortSpec("table", "out", "data", 'COREX.DataTypes.Any', exposed=True),
        PortSpec("time_values", "out", "data", 'COREX.DataTypes.Any', exposed=True),
    ),
    properties=(
        PropertySpec("result_name", "str", "displacement", "Result Type", group="Selection"),
        PropertySpec(
            "selection_mode",
            "enum",
            DPF_MESH_SELECTION_CHOOSE_SCOPE,
            "Scoping",
            enum_values=DPF_TIME_HISTORY_MESH_SELECTION_VALUES,
            inspector_editor="enum",
            group="Selection",
        ),
        PropertySpec("named_selection", "str", "", "Named Selection", group="Selection"),
        PropertySpec("node_ids", "str", "", "Node IDs", inspector_editor="textarea", group="Selection"),
        PropertySpec("element_ids", "str", "", "Element IDs", inspector_editor="textarea", group="Selection"),
        PropertySpec(
            "location",
            "enum",
            DPF_LOCATION_AUTO,
            "Location",
            enum_values=DPF_RESULT_FIELD_LOCATION_VALUES,
            inspector_editor="enum",
            group="Selection",
        ),
        dpf_time_scope_mode_property(default=DPF_TIME_SCOPE_ALL_SETS),
        PropertySpec("set_ids", "str", "", "Set IDs", inspector_editor="textarea", group="Time"),
        PropertySpec("time_values", "str", "", "Time Values", inspector_editor="textarea", group="Time"),
    ),
)
class DpfWorkflowTimeHistoryProbeNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        node_name = "DPF Time History Probe"
        selection_mode = str(
            ctx.properties.get("selection_mode") or DPF_MESH_SELECTION_CHOOSE_SCOPE
        ).strip().lower()
        if selection_mode == DPF_MESH_SELECTION_CHOOSE_SCOPE:
            raise ValueError(
                f"{node_name} requires a scope. Choose a named selection, node IDs, or element IDs."
            )
        normalize_mesh_selection_mode(selection_mode)
        model_ref, model = require_model_input(ctx, node_name=node_name)
        fields_ref, _, _ = _extract_curated_fields(
            ctx,
            model_ref=model_ref,
            model=model,
            node_name=node_name,
            default_time_scope_mode=DPF_TIME_SCOPE_ALL_SETS,
        )
        service = require_dpf_runtime_service(ctx, node_name=node_name)
        history = service.build_time_history_series(
            fields_ref,
            model=model_ref,
            run_id=ctx.run_id,
        )
        return NodeResult(
            outputs={
                "series": history.series,
                "table": [dict(row) for row in history.rows],
                "time_values": [float(value) for value in history.time_values],
            }
        )


@builtin_node_type(
    type_id=DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
    display_name="DPF Stress Invariants",
    category_path=DPF_WORKFLOW_CATEGORY_PATH,
    description=(
        "Extracts the stress tensor with built-in time and mesh scoping and derives a stress "
        "invariant: von Mises, principal S1/S2/S3, intensity, or max shear."
    ),
    surface_family="dpf_workflow",
    ports=(
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=True),
        PortSpec("fields", "out", "data", DPF_FIELDS_CONTAINER_DATA_TYPE, exposed=True),
        PortSpec("mesh_scoping", "out", "data", DPF_SCOPING_DATA_TYPE, exposed=True),
        PortSpec("time_scoping", "out", "data", DPF_SCOPING_DATA_TYPE, exposed=True),
    ),
    properties=(
        PropertySpec(
            "invariant",
            "enum",
            "von_mises",
            "Invariant",
            enum_values=DPF_INVARIANT_VALUES,
            inspector_editor="enum",
            group="Selection",
        ),
        *_selection_properties_without_result_name(),
    ),
)
class DpfWorkflowStressInvariantsNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        node_name = "DPF Stress Invariants"
        model_ref, model = require_model_input(ctx, node_name=node_name)
        fields_ref, mesh_selection, time_selection = _extract_curated_fields(
            ctx,
            model_ref=model_ref,
            model=model,
            node_name=node_name,
            result_name_override="stress",
        )
        service = require_dpf_runtime_service(ctx, node_name=node_name)
        invariant_ref = service.compute_invariant(
            fields_ref,
            invariant=ctx.properties.get("invariant"),
            run_id=ctx.run_id,
        )
        outputs: dict[str, Any] = {
            "fields": invariant_ref,
            "time_scoping": time_selection.scoping_ref,
        }
        if mesh_selection.scoping_ref is not None:
            outputs["mesh_scoping"] = mesh_selection.scoping_ref
        return NodeResult(outputs=outputs)


@builtin_node_type(
    type_id=DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
    display_name="DPF Mode Shape Viewer",
    category_path=DPF_WORKFLOW_CATEGORY_PATH,
    description=(
        "Loads a modal result file, extracts the displacement mode shape for a chosen mode "
        "number, reports its natural frequency, and opens the embedded DPF Viewer."
    ),
    ports=(
        PortSpec(
            "path",
            "in",
            "data",
            'COREX.DataTypes.Path',
            required=True,
            uses_property_default=True,
            exposed=False,
        ),
        PortSpec("result_file", "out", "data", DPF_RESULT_FILE_DATA_TYPE, exposed=True),
        PortSpec("model", "out", "data", DPF_MODEL_DATA_TYPE, exposed=True),
        PortSpec("fields", "out", "data", DPF_FIELDS_CONTAINER_DATA_TYPE, exposed=True),
        PortSpec("mesh_scoping", "out", "data", DPF_SCOPING_DATA_TYPE, exposed=True),
        PortSpec("time_scoping", "out", "data", DPF_SCOPING_DATA_TYPE, exposed=True),
        PortSpec("mesh", "out", "data", DPF_MESH_DATA_TYPE, exposed=True),
        PortSpec("session", "out", "data", VIEWER_SESSION_DATA_TYPE_ID, exposed=True),
        PortSpec("frequency", "out", "data", 'COREX.DataTypes.Double', exposed=True),
        PortSpec("normalized_path", "out", "data", 'COREX.DataTypes.Path', exposed=True),
    ),
    properties=(
        PropertySpec(
            "path",
            "path",
            "",
            "Result File",
            group="Source",
            file_filter=ANSYS_DPF_RESULT_FILES_FILTER,
        ),
        PropertySpec("mode", "str", "1", "Mode", group="Selection"),
        PropertySpec(
            "selection_mode",
            "enum",
            DPF_MESH_SELECTION_ALL,
            "Scoping",
            enum_values=DPF_CURATED_MESH_SELECTION_VALUES,
            inspector_editor="enum",
            group="Selection",
        ),
        PropertySpec("named_selection", "str", "", "Named Selection", group="Selection"),
        PropertySpec("node_ids", "str", "", "Node IDs", inspector_editor="textarea", group="Selection"),
        PropertySpec("element_ids", "str", "", "Element IDs", inspector_editor="textarea", group="Selection"),
        PropertySpec(
            "location",
            "enum",
            DPF_LOCATION_AUTO,
            "Location",
            enum_values=DPF_RESULT_FIELD_LOCATION_VALUES,
            inspector_editor="enum",
            group="Selection",
        ),
        dpf_output_mode_property(default=DPF_OUTPUT_MODE_BOTH),
        *dpf_viewer_view_property_pack(
            deform_scale_default=DPF_VIEWER_DEFORM_SCALE_AUTO,
        ),
    ),
    surface_family="viewer",
    render_quality=NodeRenderQualitySpec(
        supported_quality_tiers=("full", "proxy"),
    ),
)
class DpfWorkflowModeShapeViewerNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        node_name = "DPF Mode Shape Viewer"
        output_mode = normalize_dpf_output_mode(
            ctx.properties.get("output_mode"),
            default=DPF_OUTPUT_MODE_BOTH,
        )
        view_options = dpf_viewer_view_options_from_properties(ctx.properties)
        mode = _mode_shape_mode_number(ctx.properties.get("mode"), node_name=node_name)
        result_path, result_file_ref, model_ref, model = _result_file_and_model_from_path(
            ctx,
            node_name=node_name,
        )
        fields_ref, mesh_selection, time_selection = _extract_curated_fields(
            ctx,
            model_ref=model_ref,
            model=model,
            node_name=node_name,
            result_name_override="displacement",
            set_ids_override=(mode,),
        )
        mesh_ref = None
        if mesh_selection.scoping_ref is not None:
            mesh_ref = ctx.worker_services.dpf_runtime_service.extract_mesh(
                model=model_ref,
                mesh_scoping=mesh_selection.scoping_ref,
                run_id=ctx.run_id,
            )
        session_payload = open_dpf_viewer_session_payload(
            ctx,
            fields_ref=fields_ref,
            model_ref=model_ref,
            mesh_ref=mesh_ref,
            output_mode=output_mode,
            view_options=view_options,
        )
        outputs: dict[str, Any] = {
            "result_file": result_file_ref,
            "model": model_ref,
            "fields": fields_ref,
            "time_scoping": time_selection.scoping_ref,
            "session": session_payload,
            "normalized_path": str(result_path),
        }
        frequency = _mode_frequency(model, mode)
        if frequency is not None:
            outputs["frequency"] = frequency
        if mesh_selection.scoping_ref is not None:
            outputs["mesh_scoping"] = mesh_selection.scoping_ref
        if mesh_ref is not None:
            outputs["mesh"] = mesh_ref
        return NodeResult(outputs=outputs)


@builtin_node_type(
    type_id=DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
    display_name="DPF Field Math",
    category_path=DPF_WORKFLOW_CATEGORY_PATH,
    description=(
        "Combines two DPF results component-wise (add, subtract, multiply, divide) or scales "
        "input A by a constant, without wiring raw DPF variadic operator pins."
    ),
    surface_family="dpf_workflow",
    ports=(
        PortSpec(
            "a",
            "in",
            "data",
            DPF_FIELDS_CONTAINER_DATA_TYPE,
            label="A",
            required=True,
            accepted_data_types=(DPF_FIELD_DATA_TYPE, DPF_FIELDS_CONTAINER_DATA_TYPE),
        ),
        PortSpec(
            "b",
            "in",
            "data",
            DPF_FIELDS_CONTAINER_DATA_TYPE,
            label="B",
            required=False,
            accepted_data_types=(DPF_FIELD_DATA_TYPE, DPF_FIELDS_CONTAINER_DATA_TYPE),
        ),
        PortSpec("fields", "out", "data", DPF_FIELDS_CONTAINER_DATA_TYPE, exposed=True),
    ),
    properties=(
        PropertySpec(
            "operation",
            "enum",
            "add",
            "Operation",
            enum_values=DPF_FIELD_MATH_OPERATION_VALUES,
            inspector_editor="enum",
            group="Post",
        ),
        PropertySpec("scalar", "float", 1.0, "Scalar", group="Post"),
    ),
)
class DpfWorkflowFieldMathNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        node_name = "DPF Field Math"
        a_ref = _resolve_fields_container_input(
            ctx,
            ctx.inputs.get("a"),
            node_name=node_name,
            port_label="A",
        )
        b_value = ctx.inputs.get("b")
        b_ref = None
        if b_value is not None:
            b_ref = _resolve_fields_container_input(
                ctx,
                b_value,
                node_name=node_name,
                port_label="B",
            )
        service = require_dpf_runtime_service(ctx, node_name=node_name)
        result_ref = service.combine_fields_containers(
            a_ref,
            b_ref,
            operation=ctx.properties.get("operation"),
            scalar=float(ctx.properties.get("scalar", 1.0)),
            run_id=ctx.run_id,
        )
        return NodeResult(outputs={"fields": result_ref})


@builtin_node_type(
    type_id=DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
    display_name="DPF Table Export",
    category_path=DPF_WORKFLOW_CATEGORY_PATH,
    description=(
        "Tabulates a DPF result as one row per entity and set (entity id, nodal coordinates, "
        "time, components, magnitude) and stages it as a CSV artifact."
    ),
    surface_family="dpf_workflow",
    ports=(
        PortSpec(
            "fields",
            "in",
            "data",
            DPF_FIELDS_CONTAINER_DATA_TYPE,
            required=True,
            data_access="tree",
            accepted_data_types=(DPF_FIELD_DATA_TYPE, DPF_FIELDS_CONTAINER_DATA_TYPE),
        ),
        PortSpec(
            "model",
            "in",
            "data",
            DPF_MODEL_DATA_TYPE,
            required=True,
            data_access="tree",
        ),
        PortSpec("csv", "out", "data", 'COREX.DataTypes.Path', exposed=True),
        PortSpec("table", "out", "data", 'COREX.DataTypes.Any', exposed=True),
        PortSpec("exports", "out", "data", 'COREX.DataTypes.Any', exposed=True),
    ),
    properties=(
        PropertySpec("artifact_key", "str", "", "Artifact Key", group="Post"),
        PropertySpec(
            "include_coordinates",
            "bool",
            True,
            "Include Coordinates",
            inspector_editor="toggle",
            group="Post",
        ),
        dpf_output_mode_property(default=DPF_OUTPUT_MODE_STORED),
    ),
)
class DpfWorkflowTableExportNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        node_name = "DPF Table Export"
        ctx.inputs = resolve_single_run_inputs(ctx.inputs, node_name=node_name)
        output_mode = normalize_dpf_output_mode(
            ctx.properties.get("output_mode"),
            default=DPF_OUTPUT_MODE_STORED,
        )
        model_ref, _ = require_model_input(ctx, node_name=node_name)
        fields_ref = _resolve_fields_container_input(
            ctx,
            ctx.inputs.get("fields"),
            node_name=node_name,
            port_label="fields",
        )
        service = require_dpf_runtime_service(ctx, node_name=node_name)

        artifact_store = None
        temporary_root_parent = None
        artifact_key = ""
        if output_mode != DPF_OUTPUT_MODE_MEMORY:
            artifact_store = artifact_store_for_context(ctx)
            if artifact_store.layout is None:
                temporary_root_parent = default_staging_workspace_root()
            artifact_key = normalize_export_artifact_key(
                ctx.properties.get("artifact_key"),
                fallback=default_export_artifact_key(ctx, fields_ref),
            )

        result = service.export_field_table(
            fields_ref,
            model=model_ref,
            artifact_store=artifact_store,
            artifact_key=artifact_key,
            include_coordinates=bool(ctx.properties.get("include_coordinates", True)),
            output_profile=output_mode,
            temporary_root_parent=temporary_root_parent,
            node_workspace_id=ctx.workspace_id,
            node_workspace_name=ctx.workspace_name,
            node_id=ctx.node_id,
            node_title=ctx.node_title,
            node_type=ctx.node_type_display_name or ctx.node_type_id,
        )
        if artifact_store is not None:
            persist_artifact_store(ctx, artifact_store)

        outputs: dict[str, Any] = {
            "table": [dict(row) for row in result.rows],
        }
        if result.csv_artifact is not None:
            outputs["csv"] = result.csv_artifact
            outputs["exports"] = {"csv": result.csv_artifact}
        return NodeResult(outputs=outputs)


__all__ = [
    "DpfWorkflowFieldMathNodePlugin",
    "DpfWorkflowMinMaxEnvelopeNodePlugin",
    "DpfWorkflowModeShapeViewerNodePlugin",
    "DpfWorkflowStressInvariantsNodePlugin",
    "DpfWorkflowTableExportNodePlugin",
    "DpfWorkflowTimeHistoryProbeNodePlugin",
]
