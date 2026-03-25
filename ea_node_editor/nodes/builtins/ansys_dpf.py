from __future__ import annotations

from typing import Any

from ea_node_editor.execution.dpf_runtime_service import (
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_LOCATION_AUTO,
    DPF_LOCATION_VALUES,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MESH_SELECTION_ELEMENT_IDS,
    DPF_MESH_SELECTION_NAMED_SELECTION,
    DPF_MESH_SELECTION_NODE_IDS,
    DPF_MESH_SELECTION_VALUES,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_NODE_CATEGORY,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    build_mesh_scoping_metadata,
    build_time_scoping_metadata,
    clone_handle_with_metadata,
    dpf_output_mode_property,
    normalize_dpf_output_mode,
    normalize_int_values,
    normalize_location_choice,
    normalize_mesh_selection_mode,
    normalize_result_file_path,
    require_dpf_runtime_service,
    resolve_mesh_location,
    resolve_model_handle_and_object,
    resolve_named_selection,
    resolve_time_selection,
)
from ea_node_editor.nodes.decorators import node_type
from ea_node_editor.nodes.types import (
    DPF_MODEL_DATA_TYPE,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    NodeResult,
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


ANSYS_DPF_NODE_PLUGINS = (
    DpfResultFileNodePlugin,
    DpfModelNodePlugin,
    DpfMeshScopingNodePlugin,
    DpfTimeScopingNodePlugin,
)


__all__ = [
    "ANSYS_DPF_NODE_PLUGINS",
    "DpfMeshScopingNodePlugin",
    "DpfModelNodePlugin",
    "DpfResultFileNodePlugin",
    "DpfTimeScopingNodePlugin",
]
