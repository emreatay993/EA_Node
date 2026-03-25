from __future__ import annotations

import hashlib
import copy
from typing import Any

from ea_node_editor.execution.protocol import (
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    UpdateViewerSessionCommand,
    ViewerSessionFailedEvent,
)
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_FIELD_OPERATION_VALUES,
    DPF_FIELD_OP_CONVERT_LOCATION,
    DPF_FIELD_OP_MIN_MAX,
    DPF_FIELD_OP_NORM,
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_LOCATION_AUTO,
    DPF_LOCATION_VALUES,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MESH_SELECTION_ELEMENT_IDS,
    DPF_MESH_SELECTION_NAMED_SELECTION,
    DPF_MESH_SELECTION_NODE_IDS,
    DPF_MESH_SELECTION_VALUES,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_OUTPUT_MODE_BOTH,
    DPF_NODE_CATEGORY,
    DPF_OUTPUT_MODE_MEMORY,
    DPF_OUTPUT_MODE_STORED,
    DPF_RESULT_FIELD_LOCATION_VALUES,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_TARGET_FIELD_LOCATION_VALUES,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY,
    DPF_VIEWER_LIVE_POLICY_KEEP_LIVE,
    DPF_VIEWER_LIVE_POLICY_VALUES,
    DPF_VIEWER_NODE_TYPE_ID,
    build_mesh_scoping_metadata,
    build_time_scoping_metadata,
    clone_field_handle_with_metadata,
    clone_handle_with_metadata,
    dpf_output_mode_property,
    normalize_dpf_output_mode,
    normalize_dpf_viewer_live_policy,
    normalize_export_artifact_key,
    normalize_export_formats,
    normalize_field_operation,
    normalize_int_values,
    normalize_location_choice,
    normalize_mesh_selection_mode,
    normalize_result_field_location,
    normalize_result_file_path,
    normalize_target_field_location,
    require_dpf_runtime_service,
    resolve_field_handle_and_object,
    resolve_mesh_location,
    resolve_model_handle_and_object,
    resolve_named_selection,
    resolve_single_active_set,
    resolve_time_selection,
    unwrap_single_field_handle,
    wrap_field_handle_as_fields_container,
)
from ea_node_editor.nodes.decorators import node_type
from ea_node_editor.nodes.output_artifacts import (
    artifact_store_for_context,
    default_staging_workspace_root,
    persist_artifact_store,
)
from ea_node_editor.nodes.types import (
    DPF_FIELD_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_VIEW_SESSION_DATA_TYPE,
    NodeResult,
    NodeRenderQualitySpec,
    PortSpec,
    PropertySpec,
)


def _source_value_from_ctx(ctx, *, result_file_key: str, path_key: str, node_name: str) -> Any:  # noqa: ANN001
    result_file_value = ctx.inputs.get(result_file_key)
    if result_file_value is not None:
        return result_file_value

    path_value = ctx.inputs.get(path_key)
    if path_value is not None and str(path_value).strip():
        return normalize_result_file_path(
            ctx,
            input_key=path_key,
            property_key=path_key,
            node_name=node_name,
        )

    return normalize_result_file_path(
        ctx,
        input_key=path_key,
        property_key=path_key,
        node_name=node_name,
    )


def _require_model_input(ctx, *, node_name: str):  # noqa: ANN001
    model_value = ctx.inputs.get("model")
    if model_value is None:
        raise ValueError(f"{node_name} requires a model input.")
    return resolve_model_handle_and_object(ctx, model_value, node_name=node_name)


def _default_export_artifact_key(ctx, field_ref) -> str:  # noqa: ANN001
    result_name = str(field_ref.metadata.get("result_name", "")).strip() or "field"
    set_id = int(field_ref.metadata.get("set_id", 1))
    return f"{ctx.workspace_id}.{ctx.node_id}.{result_name}.set{set_id}"


def _default_viewer_session_id(workspace_id: str, node_id: str) -> str:
    digest = hashlib.sha1(f"{workspace_id}:{node_id}".encode("utf-8")).hexdigest()[:16]
    return f"viewer_session_{digest}"


def _viewer_event_payload(event: object) -> dict[str, Any]:
    return {
        "workspace_id": str(getattr(event, "workspace_id", "")).strip(),
        "node_id": str(getattr(event, "node_id", "")).strip(),
        "session_id": str(getattr(event, "session_id", "")).strip(),
        "data_refs": copy.deepcopy(getattr(event, "data_refs", {})),
        "summary": copy.deepcopy(getattr(event, "summary", {})),
        "options": copy.deepcopy(getattr(event, "options", {})),
    }


def _viewer_summary_from_field_ref(field_ref) -> dict[str, Any]:  # noqa: ANN001
    metadata = field_ref.metadata
    summary: dict[str, Any] = {
        "result_name": str(metadata.get("result_name", "")).strip(),
    }
    set_id = metadata.get("set_id")
    try:
        normalized_set_id = int(set_id)
    except (TypeError, ValueError):
        normalized_set_id = 0
    if normalized_set_id > 0:
        summary["set_id"] = normalized_set_id
        summary["set_label"] = f"Set {normalized_set_id}"
        summary["step_index"] = max(0, normalized_set_id - 1)
    time_value = metadata.get("time_value")
    try:
        normalized_time_value = float(time_value) if time_value is not None else None
    except (TypeError, ValueError):
        normalized_time_value = None
    if normalized_time_value is not None:
        summary["time_value"] = normalized_time_value
        summary["time_label"] = f"{normalized_time_value:g}"
    return summary


@node_type(
    type_id=DPF_RESULT_FILE_NODE_TYPE_ID,
    display_name="DPF Result File",
    category=DPF_NODE_CATEGORY,
    icon="database",
    description="Normalizes a Mechanical result-file path and returns a worker-local DPF handle.",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("path", "in", "data", "path", required=False),
        PortSpec("result_file", "out", "data", DPF_RESULT_FILE_DATA_TYPE, exposed=True),
        PortSpec("normalized_path", "out", "data", "path", exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(
        PropertySpec("path", "path", "", "Result File"),
        dpf_output_mode_property(),
    ),
)
class DpfResultFileNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        normalize_dpf_output_mode(ctx.properties.get("output_mode"))
        result_path = normalize_result_file_path(ctx, node_name="DPF Result File")
        result_ref = require_dpf_runtime_service(ctx, node_name="DPF Result File").load_result_file(result_path)
        return NodeResult(
            outputs={
                "result_file": result_ref,
                "normalized_path": str(result_path),
                "exec_out": True,
            }
        )


@node_type(
    type_id=DPF_MODEL_NODE_TYPE_ID,
    display_name="DPF Model",
    category=DPF_NODE_CATEGORY,
    icon="cube",
    description="Loads a DPF model from a Mechanical result-file handle or path.",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("result_file", "in", "data", DPF_RESULT_FILE_DATA_TYPE, required=False),
        PortSpec("path", "in", "data", "path", required=False),
        PortSpec("model", "out", "data", DPF_MODEL_DATA_TYPE, exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(
        PropertySpec("path", "path", "", "Result File"),
        dpf_output_mode_property(),
    ),
)
class DpfModelNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        normalize_dpf_output_mode(ctx.properties.get("output_mode"))
        source_value = _source_value_from_ctx(
            ctx,
            result_file_key="result_file",
            path_key="path",
            node_name="DPF Model",
        )
        model_ref = require_dpf_runtime_service(ctx, node_name="DPF Model").load_model(source_value)
        return NodeResult(outputs={"model": model_ref, "exec_out": True})


@node_type(
    type_id=DPF_MESH_SCOPING_NODE_TYPE_ID,
    display_name="DPF Mesh Scoping",
    category=DPF_NODE_CATEGORY,
    icon="filter",
    description="Builds a worker-local DPF mesh scoping from named selections or raw mesh ids.",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=False),
        PortSpec("scoping", "out", "data", DPF_SCOPING_DATA_TYPE, exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(
        PropertySpec(
            "selection_mode",
            "enum",
            DPF_MESH_SELECTION_NAMED_SELECTION,
            "Selection Mode",
            enum_values=DPF_MESH_SELECTION_VALUES,
            inspector_editor="enum",
        ),
        PropertySpec("named_selection", "str", "", "Named Selection"),
        PropertySpec("node_ids", "str", "", "Node IDs", inspector_editor="textarea"),
        PropertySpec("element_ids", "str", "", "Element IDs", inspector_editor="textarea"),
        PropertySpec(
            "location",
            "enum",
            DPF_LOCATION_AUTO,
            "Location",
            enum_values=DPF_LOCATION_VALUES,
            inspector_editor="enum",
        ),
        PropertySpec("set_ids", "str", "", "Set IDs", inspector_editor="textarea"),
        PropertySpec("time_values", "str", "", "Time Values", inspector_editor="textarea"),
        dpf_output_mode_property(),
    ),
)
class DpfMeshScopingNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        normalize_dpf_output_mode(ctx.properties.get("output_mode"))
        selection_mode = normalize_mesh_selection_mode(ctx.properties.get("selection_mode"))
        location_choice = normalize_location_choice(ctx.properties.get("location"))
        model_value = ctx.inputs.get("model")
        model_ref = None
        model = None
        if model_value is not None:
            model_ref, model = resolve_model_handle_and_object(
                ctx,
                model_value,
                node_name="DPF Mesh Scoping",
            )

        time_selection = resolve_time_selection(
            model=model,
            set_ids_value=ctx.properties.get("set_ids"),
            time_values_value=ctx.properties.get("time_values"),
            require_any=False,
            node_name="DPF Mesh Scoping",
        )
        service = require_dpf_runtime_service(ctx, node_name="DPF Mesh Scoping")

        if selection_mode == DPF_MESH_SELECTION_NAMED_SELECTION:
            if model is None:
                raise ValueError("DPF Mesh Scoping requires a model input for named selections.")
            named_selection, scoping = resolve_named_selection(
                model,
                ctx.properties.get("named_selection"),
                node_name="DPF Mesh Scoping",
            )
            location = resolve_mesh_location(
                selection_mode=selection_mode,
                location_choice=location_choice,
                scoping=scoping,
            )
            scoping_ref = ctx.register_handle(
                scoping,
                kind=DPF_MESH_SCOPING_HANDLE_KIND,
                metadata=build_mesh_scoping_metadata(
                    model_ref=model_ref,
                    selection_mode=selection_mode,
                    location=location,
                    ids=getattr(scoping, "ids", ()),
                    named_selection=named_selection,
                    time_selection=time_selection,
                ),
            )
            return NodeResult(outputs={"scoping": scoping_ref, "exec_out": True})

        property_key = "node_ids" if selection_mode == DPF_MESH_SELECTION_NODE_IDS else "element_ids"
        ids = normalize_int_values(property_key, ctx.properties.get(property_key))
        if not ids:
            raise ValueError(f"DPF Mesh Scoping requires {property_key} for selection_mode {selection_mode}.")
        location = resolve_mesh_location(
            selection_mode=selection_mode,
            location_choice=location_choice,
        )
        base_ref = service.create_mesh_scoping(ids, location=location, run_id=ctx.run_id)
        scoping_ref = clone_handle_with_metadata(
            ctx,
            base_ref,
            expected_kind=DPF_MESH_SCOPING_HANDLE_KIND,
            metadata=build_mesh_scoping_metadata(
                model_ref=model_ref,
                selection_mode=selection_mode,
                location=location,
                ids=ids,
                time_selection=time_selection,
            ),
            release_original=True,
        )
        return NodeResult(outputs={"scoping": scoping_ref, "exec_out": True})


@node_type(
    type_id=DPF_TIME_SCOPING_NODE_TYPE_ID,
    display_name="DPF Time Scoping",
    category=DPF_NODE_CATEGORY,
    icon="clock",
    description="Builds a worker-local DPF time scoping from set ids or explicit time values.",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=False),
        PortSpec("scoping", "out", "data", DPF_SCOPING_DATA_TYPE, exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(
        PropertySpec("set_ids", "str", "", "Set IDs", inspector_editor="textarea"),
        PropertySpec("time_values", "str", "", "Time Values", inspector_editor="textarea"),
        dpf_output_mode_property(),
    ),
)
class DpfTimeScopingNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        normalize_dpf_output_mode(ctx.properties.get("output_mode"))
        model_value = ctx.inputs.get("model")
        model_ref = None
        model = None
        if model_value is not None:
            model_ref, model = resolve_model_handle_and_object(
                ctx,
                model_value,
                node_name="DPF Time Scoping",
            )

        time_selection = resolve_time_selection(
            model=model,
            set_ids_value=ctx.properties.get("set_ids"),
            time_values_value=ctx.properties.get("time_values"),
            require_any=True,
            node_name="DPF Time Scoping",
        )
        base_ref = require_dpf_runtime_service(ctx, node_name="DPF Time Scoping").create_time_scoping(
            time_selection.set_ids,
            model=model_ref if model_ref is not None else None,
            run_id=ctx.run_id,
        )
        scoping_ref = clone_handle_with_metadata(
            ctx,
            base_ref,
            expected_kind=DPF_TIME_SCOPING_HANDLE_KIND,
            metadata=build_time_scoping_metadata(
                model_ref=model_ref,
                time_selection=time_selection,
            ),
            release_original=True,
        )
        return NodeResult(outputs={"scoping": scoping_ref, "exec_out": True})


@node_type(
    type_id=DPF_RESULT_FIELD_NODE_TYPE_ID,
    display_name="DPF Result Field",
    category=DPF_NODE_CATEGORY,
    icon="query_stats",
    description="Extracts a single active-set DPF field from a Mechanical result model.",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=False),
        PortSpec("mesh_scoping", "in", "data", DPF_SCOPING_DATA_TYPE, required=False),
        PortSpec("time_scoping", "in", "data", DPF_SCOPING_DATA_TYPE, required=False),
        PortSpec("field", "out", "data", DPF_FIELD_DATA_TYPE, exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(
        PropertySpec("result_name", "str", "displacement", "Result Name"),
        PropertySpec(
            "location",
            "enum",
            DPF_LOCATION_AUTO,
            "Location",
            enum_values=DPF_RESULT_FIELD_LOCATION_VALUES,
            inspector_editor="enum",
        ),
        PropertySpec("set_ids", "str", "", "Set IDs", inspector_editor="textarea"),
        PropertySpec("time_values", "str", "", "Time Values", inspector_editor="textarea"),
        dpf_output_mode_property(),
    ),
)
class DpfResultFieldNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        output_mode = normalize_dpf_output_mode(ctx.properties.get("output_mode"))
        model_ref, model = _require_model_input(ctx, node_name="DPF Result Field")
        active_set = resolve_single_active_set(
            ctx,
            model=model,
            time_scoping_value=ctx.inputs.get("time_scoping"),
            set_ids_value=ctx.properties.get("set_ids"),
            time_values_value=ctx.properties.get("time_values"),
            node_name="DPF Result Field",
        )
        location = normalize_result_field_location(ctx.properties.get("location"))
        service = require_dpf_runtime_service(ctx, node_name="DPF Result Field")
        fields_ref = service.extract_result_fields(
            model=model_ref,
            result_name=ctx.properties.get("result_name"),
            set_ids=[active_set.set_id],
            time_scoping=active_set.time_scoping_ref,
            mesh_scoping=ctx.inputs.get("mesh_scoping"),
            location="" if location == DPF_LOCATION_AUTO else location,
            run_id=ctx.run_id,
        )
        field_ref = unwrap_single_field_handle(
            ctx,
            fields_ref,
            node_name="DPF Result Field",
            release_original=True,
        )
        field_ref = clone_field_handle_with_metadata(
            ctx,
            field_ref,
            node_name="DPF Result Field",
            source_metadata={
                **field_ref.metadata,
                "output_mode": output_mode,
                "model_handle_id": model_ref.handle_id,
                "set_id": active_set.set_id,
                "set_ids": [active_set.set_id],
                **({"time_value": active_set.time_value, "time_values": [active_set.time_value]} if active_set.time_value is not None else {}),
                **({"mesh_scoping_handle_id": ctx.inputs["mesh_scoping"].handle_id} if hasattr(ctx.inputs.get("mesh_scoping"), "handle_id") else {}),
                **({"time_scoping_handle_id": active_set.time_scoping_ref.handle_id} if active_set.time_scoping_ref is not None else {}),
            },
            release_original=True,
        )
        return NodeResult(outputs={"field": field_ref, "exec_out": True})


@node_type(
    type_id=DPF_FIELD_OPS_NODE_TYPE_ID,
    display_name="DPF Field Ops",
    category=DPF_NODE_CATEGORY,
    icon="calculate",
    description="Applies norm, location conversion, or min/max reductions to a single DPF field.",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("field", "in", "data", DPF_FIELD_DATA_TYPE, required=False),
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=False),
        PortSpec("field_out", "out", "data", DPF_FIELD_DATA_TYPE, exposed=True),
        PortSpec("field_min", "out", "data", DPF_FIELD_DATA_TYPE, exposed=True),
        PortSpec("field_max", "out", "data", DPF_FIELD_DATA_TYPE, exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(
        PropertySpec(
            "operation",
            "enum",
            DPF_FIELD_OP_NORM,
            "Operation",
            enum_values=DPF_FIELD_OPERATION_VALUES,
            inspector_editor="enum",
        ),
        PropertySpec(
            "location",
            "enum",
            "nodal",
            "Target Location",
            enum_values=DPF_TARGET_FIELD_LOCATION_VALUES,
            inspector_editor="enum",
        ),
        dpf_output_mode_property(),
    ),
)
class DpfFieldOpsNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        normalize_dpf_output_mode(ctx.properties.get("output_mode"))
        operation = normalize_field_operation(ctx.properties.get("operation"))
        input_field_ref, _ = resolve_field_handle_and_object(
            ctx,
            ctx.inputs.get("field"),
            node_name="DPF Field Ops",
        )
        wrapped_fields_ref = wrap_field_handle_as_fields_container(
            ctx,
            input_field_ref,
            node_name="DPF Field Ops",
        )
        service = require_dpf_runtime_service(ctx, node_name="DPF Field Ops")
        outputs: dict[str, Any] = {"exec_out": True}
        try:
            if operation == DPF_FIELD_OP_NORM:
                normalized_ref = service.compute_field_norm(wrapped_fields_ref, run_id=ctx.run_id)
                outputs["field_out"] = unwrap_single_field_handle(
                    ctx,
                    normalized_ref,
                    node_name="DPF Field Ops",
                    operation=operation,
                    release_original=True,
                )
                return NodeResult(outputs=outputs)

            if operation == DPF_FIELD_OP_CONVERT_LOCATION:
                model_ref, _ = _require_model_input(ctx, node_name="DPF Field Ops")
                target_location = normalize_target_field_location(ctx.properties.get("location"))
                converted_ref = service.convert_fields_location(
                    wrapped_fields_ref,
                    model=model_ref,
                    location=target_location,
                    run_id=ctx.run_id,
                )
                outputs["field_out"] = unwrap_single_field_handle(
                    ctx,
                    converted_ref,
                    node_name="DPF Field Ops",
                    operation=operation,
                    requested_location=target_location,
                    release_original=True,
                )
                return NodeResult(outputs=outputs)

            field_range = service.reduce_fields_min_max(wrapped_fields_ref, run_id=ctx.run_id)
            minimum_metadata = dict(input_field_ref.metadata)
            minimum_metadata.update(field_range.minimum.metadata)
            maximum_metadata = dict(input_field_ref.metadata)
            maximum_metadata.update(field_range.maximum.metadata)
            outputs["field_min"] = clone_field_handle_with_metadata(
                ctx,
                field_range.minimum,
                node_name="DPF Field Ops",
                source_metadata=minimum_metadata,
                release_original=True,
            )
            outputs["field_max"] = clone_field_handle_with_metadata(
                ctx,
                field_range.maximum,
                node_name="DPF Field Ops",
                source_metadata=maximum_metadata,
                release_original=True,
            )
            return NodeResult(outputs=outputs)
        finally:
            ctx.release_handle(wrapped_fields_ref)


@node_type(
    type_id=DPF_MESH_EXTRACT_NODE_TYPE_ID,
    display_name="DPF Mesh Extract",
    category=DPF_NODE_CATEGORY,
    icon="hub",
    description="Extracts a worker-local DPF mesh from a model, optionally using a mesh scoping.",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=False),
        PortSpec("mesh_scoping", "in", "data", DPF_SCOPING_DATA_TYPE, required=False),
        PortSpec("mesh", "out", "data", DPF_MESH_DATA_TYPE, exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(
        PropertySpec("nodes_only", "bool", False, "Nodes Only"),
        dpf_output_mode_property(),
    ),
)
class DpfMeshExtractNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        normalize_dpf_output_mode(ctx.properties.get("output_mode"))
        model_ref, _ = _require_model_input(ctx, node_name="DPF Mesh Extract")
        mesh_ref = require_dpf_runtime_service(ctx, node_name="DPF Mesh Extract").extract_mesh(
            model=model_ref,
            mesh_scoping=ctx.inputs.get("mesh_scoping"),
            nodes_only=bool(ctx.properties.get("nodes_only", False)),
            run_id=ctx.run_id,
        )
        return NodeResult(outputs={"mesh": mesh_ref, "exec_out": True})


@node_type(
    type_id=DPF_EXPORT_NODE_TYPE_ID,
    display_name="DPF Export",
    category=DPF_NODE_CATEGORY,
    icon="download",
    description="Materializes a single DPF field into staged export artifacts and optional in-memory datasets.",
    ports=(
        PortSpec("exec_in", "in", "exec", "exec", required=False),
        PortSpec("field", "in", "data", DPF_FIELD_DATA_TYPE, required=False),
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=False),
        PortSpec("mesh", "in", "data", DPF_MESH_DATA_TYPE, required=False),
        PortSpec("dataset", "out", "data", "any", exposed=True),
        PortSpec("exports", "out", "data", "any", exposed=True),
        PortSpec("csv", "out", "data", "path", exposed=True),
        PortSpec("png", "out", "data", "path", exposed=True),
        PortSpec("vtu", "out", "data", "path", exposed=True),
        PortSpec("vtm", "out", "data", "path", exposed=True),
        PortSpec("exec_out", "out", "exec", "exec", exposed=True),
    ),
    properties=(
        PropertySpec("artifact_key", "str", "", "Artifact Key"),
        PropertySpec("export_formats", "str", "csv", "Export Formats"),
        dpf_output_mode_property(default=DPF_OUTPUT_MODE_STORED),
    ),
)
class DpfExportNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        output_mode = normalize_dpf_output_mode(
            ctx.properties.get("output_mode"),
            default=DPF_OUTPUT_MODE_STORED,
        )
        model_ref, _ = _require_model_input(ctx, node_name="DPF Export")
        field_ref, _ = resolve_field_handle_and_object(
            ctx,
            ctx.inputs.get("field"),
            node_name="DPF Export",
        )
        wrapped_fields_ref = wrap_field_handle_as_fields_container(
            ctx,
            field_ref,
            node_name="DPF Export",
        )
        service = require_dpf_runtime_service(ctx, node_name="DPF Export")
        outputs: dict[str, Any] = {"exec_out": True}
        try:
            export_formats = ()
            artifact_store = None
            temporary_root_parent = None
            artifact_key = ""
            if output_mode != DPF_OUTPUT_MODE_MEMORY:
                export_formats = normalize_export_formats(ctx.properties.get("export_formats"))
                if not export_formats:
                    raise ValueError("DPF Export requires at least one export format in stored or both mode.")
                artifact_store = artifact_store_for_context(ctx)
                temporary_root_parent = None
                if artifact_store.layout is None:
                    temporary_root_parent = default_staging_workspace_root()
                artifact_key = normalize_export_artifact_key(
                    ctx.properties.get("artifact_key"),
                    fallback=_default_export_artifact_key(ctx, field_ref),
                )

            materialization = service.materialize_viewer_dataset(
                wrapped_fields_ref,
                model=model_ref,
                output_profile=output_mode,
                mesh=ctx.inputs.get("mesh"),
                artifact_store=artifact_store,
                artifact_key=artifact_key,
                export_formats=export_formats,
                temporary_root_parent=temporary_root_parent,
                run_id=ctx.run_id,
            )
            if artifact_store is not None:
                persist_artifact_store(ctx, artifact_store)

            if materialization.dataset_ref is not None:
                outputs["dataset"] = materialization.dataset_ref
            if materialization.artifacts:
                outputs["exports"] = dict(materialization.artifacts)
                for export_format, artifact_ref in materialization.artifacts.items():
                    outputs[export_format] = artifact_ref
            return NodeResult(outputs=outputs)
        finally:
            ctx.release_handle(wrapped_fields_ref)


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
        model_ref, _ = _require_model_input(ctx, node_name="DPF Viewer")
        field_ref, _ = resolve_field_handle_and_object(
            ctx,
            ctx.inputs.get("field"),
            node_name="DPF Viewer",
        )
        wrapped_fields_ref = wrap_field_handle_as_fields_container(
            ctx,
            field_ref,
            node_name="DPF Viewer",
        )
        mesh_ref = ctx.inputs.get("mesh")
        session_service = ctx.worker_services.viewer_session_service
        session_id = _default_viewer_session_id(ctx.workspace_id, ctx.node_id)
        summary = _viewer_summary_from_field_ref(field_ref)
        options = {
            "live_mode": "proxy",
            "live_policy": live_policy,
            "keep_live": live_policy == DPF_VIEWER_LIVE_POLICY_KEEP_LIVE,
            "output_profile": output_mode,
            "playback_state": "paused",
            "step_index": int(summary.get("step_index", 0)),
        }
        try:
            opened = session_service.open_session(
                OpenViewerSessionCommand(
                    workspace_id=ctx.workspace_id,
                    node_id=ctx.node_id,
                    session_id=session_id,
                    data_refs={
                        "fields": wrapped_fields_ref,
                        "model": model_ref,
                        **({"mesh": mesh_ref} if mesh_ref is not None else {}),
                    },
                    summary=summary,
                    options=options,
                )
            )
            if isinstance(opened, ViewerSessionFailedEvent):
                raise RuntimeError(opened.error)

            session_event = opened
            if output_mode in {DPF_OUTPUT_MODE_MEMORY, DPF_OUTPUT_MODE_BOTH}:
                materialize_output_mode = (
                    DPF_OUTPUT_MODE_MEMORY
                    if output_mode == DPF_OUTPUT_MODE_BOTH
                    else output_mode
                )
                materialized = session_service.materialize_data(
                    MaterializeViewerDataCommand(
                        workspace_id=ctx.workspace_id,
                        node_id=ctx.node_id,
                        session_id=session_id,
                        options={
                            "output_profile": materialize_output_mode,
                            "live_mode": "proxy",
                        },
                    )
                )
                if isinstance(materialized, ViewerSessionFailedEvent):
                    raise RuntimeError(materialized.error)
                session_event = materialized
                if materialize_output_mode != output_mode:
                    updated = session_service.update_session(
                        UpdateViewerSessionCommand(
                            workspace_id=ctx.workspace_id,
                            node_id=ctx.node_id,
                            session_id=session_id,
                            options={"output_profile": output_mode},
                        )
                    )
                    if isinstance(updated, ViewerSessionFailedEvent):
                        raise RuntimeError(updated.error)
                    session_event = updated

            return NodeResult(
                outputs={
                    "session": _viewer_event_payload(session_event),
                    "exec_out": True,
                }
            )
        finally:
            ctx.release_handle(wrapped_fields_ref)


ANSYS_DPF_NODE_PLUGINS = (
    DpfResultFileNodePlugin,
    DpfModelNodePlugin,
    DpfMeshScopingNodePlugin,
    DpfTimeScopingNodePlugin,
    DpfResultFieldNodePlugin,
    DpfFieldOpsNodePlugin,
    DpfMeshExtractNodePlugin,
    DpfExportNodePlugin,
    DpfViewerNodePlugin,
)


__all__ = [
    "ANSYS_DPF_NODE_PLUGINS",
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
