from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_HANDLE_KIND,
    DPF_MODEL_DATA_TYPE,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_TIME_SCOPING_HANDLE_KIND,
)
from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_CURATED_MESH_SELECTION_VALUES,
    DPF_LOCATION_AUTO,
    DPF_MESH_SELECTION_ALL,
    DPF_MESH_SELECTION_NAMED_SELECTION,
    DPF_MESH_SELECTION_NODE_IDS,
    DPF_OUTPUT_MODE_BOTH,
    DPF_RESULT_FIELD_LOCATION_VALUES,
    DPF_TIME_SCOPE_ALL_SETS,
    DPF_TIME_SCOPE_FIRST_SET,
    DPF_TIME_SCOPE_LAST_SET,
    DPF_TIME_SCOPE_SET_IDS,
    DPF_TIME_SCOPE_TIME_VALUES,
    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
    ResolvedTimeSelection,
    build_mesh_scoping_metadata,
    build_time_scoping_metadata,
    clone_handle_with_metadata,
    dpf_output_mode_property,
    dpf_time_scope_mode_property,
    dpf_viewer_view_options_from_properties,
    dpf_viewer_view_property_pack,
    normalize_dpf_output_mode,
    normalize_dpf_time_scope_mode,
    normalize_float_values,
    normalize_int_values,
    normalize_location_choice,
    normalize_result_field_location,
    normalize_result_file_path,
    resolve_mesh_location,
    resolve_named_selection,
    resolve_time_selection,
)
from ea_node_editor.nodes.builtins.ansys_dpf_node_helpers import require_model_input
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import DPF_WORKFLOW_CATEGORY_PATH
from ea_node_editor.nodes.builtins.ansys_dpf_viewer_adapter import open_dpf_viewer_session_payload
from ea_node_editor.nodes.core_data_types import VIEWER_SESSION_DATA_TYPE_ID
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.file_dialog_filters import ANSYS_DPF_RESULT_FILES_FILTER
from ea_node_editor.nodes.node_specs import (
    NodeRenderQualitySpec,
    PortSpec,
    PropertySpec,
)


@dataclass(slots=True, frozen=True)
class _ResolvedMeshSelection:
    scoping_ref: Any | None
    selection_mode: str


@dataclass(slots=True, frozen=True)
class _ResolvedTimeSelection:
    scoping_ref: Any
    set_ids: tuple[int, ...]
    time_values: tuple[float, ...]
    mode: str


def _curated_selection_mode(value: Any) -> str:
    normalized = str(value or DPF_MESH_SELECTION_ALL).strip().lower()
    if normalized not in DPF_CURATED_MESH_SELECTION_VALUES:
        raise ValueError(
            "selection_mode must be one of "
            f"{', '.join(DPF_CURATED_MESH_SELECTION_VALUES)}."
        )
    return normalized


def _model_set_count(model: Any, *, node_name: str) -> int:
    metadata = getattr(model, "metadata", None)
    support = getattr(metadata, "time_freq_support", None)
    n_sets = int(getattr(support, "n_sets", 0))
    if n_sets < 1:
        raise ValueError(f"{node_name} could not resolve a result set from the selected model.")
    return n_sets


def _time_scope_mode(
    properties: Any,
    *,
    default: str,
    node_name: str,
) -> str:
    raw_mode = properties.get("time_scope_mode")
    if str(raw_mode or "").strip():
        return normalize_dpf_time_scope_mode(raw_mode, default=default)

    legacy_set_ids = normalize_int_values("set_ids", properties.get("set_ids"))
    legacy_time_values = normalize_float_values("time_values", properties.get("time_values"))
    if legacy_set_ids and legacy_time_values:
        raise ValueError(
            f"{node_name} has both legacy set_ids and time_values. Choose time_scope_mode "
            "set_ids or time_values and clear the inactive selector."
        )
    if legacy_set_ids:
        return DPF_TIME_SCOPE_SET_IDS
    if legacy_time_values:
        return DPF_TIME_SCOPE_TIME_VALUES
    return normalize_dpf_time_scope_mode(default)


def _resolve_time_scoping(
    ctx,  # noqa: ANN001
    *,
    model_ref: Any,
    model: Any,
    node_name: str,
    set_ids_override: tuple[int, ...] = (),
    default_mode: str = DPF_TIME_SCOPE_FIRST_SET,
) -> _ResolvedTimeSelection:
    if set_ids_override:
        n_sets = _model_set_count(model, node_name=node_name)
        for set_id in set_ids_override:
            if int(set_id) < 1 or int(set_id) > n_sets:
                raise ValueError(
                    f"{node_name} set_ids must stay within 1..{n_sets} for the selected model."
                )
        time_selection = ResolvedTimeSelection(
            tuple(int(set_id) for set_id in set_ids_override), ()
        )
        time_scope_mode = DPF_TIME_SCOPE_SET_IDS
    else:
        time_scope_mode = _time_scope_mode(
            ctx.properties,
            default=default_mode,
            node_name=node_name,
        )
        n_sets = _model_set_count(model, node_name=node_name)
        if time_scope_mode == DPF_TIME_SCOPE_FIRST_SET:
            time_selection = ResolvedTimeSelection((1,), ())
        elif time_scope_mode == DPF_TIME_SCOPE_LAST_SET:
            time_selection = ResolvedTimeSelection((n_sets,), ())
        elif time_scope_mode == DPF_TIME_SCOPE_ALL_SETS:
            time_selection = ResolvedTimeSelection(tuple(range(1, n_sets + 1)), ())
        elif time_scope_mode == DPF_TIME_SCOPE_SET_IDS:
            if not normalize_int_values("set_ids", ctx.properties.get("set_ids")):
                raise ValueError(
                    f"{node_name} requires set_ids when time_scope_mode is set_ids."
                )
            time_selection = resolve_time_selection(
                model=model,
                set_ids_value=ctx.properties.get("set_ids"),
                time_values_value=None,
                require_any=True,
                node_name=node_name,
            )
        else:
            if not normalize_float_values("time_values", ctx.properties.get("time_values")):
                raise ValueError(
                    f"{node_name} requires time_values when time_scope_mode is time_values."
                )
            time_selection = resolve_time_selection(
                model=model,
                set_ids_value=None,
                time_values_value=ctx.properties.get("time_values"),
                require_any=True,
                node_name=node_name,
            )
    resolved_set_ids = time_selection.set_ids
    service = ctx.worker_services.dpf_runtime_service
    base_ref = service.create_time_scoping(
        resolved_set_ids,
        model=model_ref,
        run_id=ctx.run_id,
    )
    metadata_selection = ResolvedTimeSelection(resolved_set_ids, time_selection.time_values)
    metadata = build_time_scoping_metadata(
        model_ref=model_ref,
        time_selection=metadata_selection,
    )
    metadata["time_scope_mode"] = time_scope_mode
    scoping_ref = clone_handle_with_metadata(
        ctx,
        base_ref,
        expected_kind=DPF_TIME_SCOPING_HANDLE_KIND,
        metadata=metadata,
        release_original=True,
    )
    return _ResolvedTimeSelection(
        scoping_ref=scoping_ref,
        set_ids=resolved_set_ids,
        time_values=time_selection.time_values,
        mode=time_scope_mode,
    )


def _resolve_mesh_selection(
    ctx,
    *,
    model_ref: Any,
    model: Any,
    time_selection: _ResolvedTimeSelection,
    node_name: str,
) -> _ResolvedMeshSelection:  # noqa: ANN001
    selection_mode = _curated_selection_mode(ctx.properties.get("selection_mode"))
    if selection_mode == DPF_MESH_SELECTION_ALL:
        return _ResolvedMeshSelection(scoping_ref=None, selection_mode=selection_mode)

    location_choice = normalize_location_choice(ctx.properties.get("location"))
    service = ctx.worker_services.dpf_runtime_service
    metadata_time_selection = ResolvedTimeSelection(
        time_selection.set_ids,
        time_selection.time_values,
    )

    if selection_mode == DPF_MESH_SELECTION_NAMED_SELECTION:
        named_selection, scoping = resolve_named_selection(
            model,
            ctx.properties.get("named_selection"),
            node_name=node_name,
        )
        location = resolve_mesh_location(
            selection_mode=selection_mode,
            location_choice=location_choice,
            scoping=scoping,
        )
        scoping_ref = ctx.register_handle(
            scoping,
            data_type_id=DPF_SCOPING_DATA_TYPE,
            kind=DPF_MESH_SCOPING_HANDLE_KIND,
            metadata=build_mesh_scoping_metadata(
                model_ref=model_ref,
                selection_mode=selection_mode,
                location=location,
                ids=getattr(scoping, "ids", ()),
                named_selection=named_selection,
                time_selection=metadata_time_selection,
            ),
        )
        return _ResolvedMeshSelection(scoping_ref=scoping_ref, selection_mode=selection_mode)

    property_key = "node_ids" if selection_mode == DPF_MESH_SELECTION_NODE_IDS else "element_ids"
    ids = normalize_int_values(property_key, ctx.properties.get(property_key))
    if not ids:
        raise ValueError(f"{node_name} requires {property_key} for selection_mode {selection_mode}.")
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
            time_selection=metadata_time_selection,
        ),
        release_original=True,
    )
    return _ResolvedMeshSelection(scoping_ref=scoping_ref, selection_mode=selection_mode)


def _result_file_and_model_from_path(ctx, *, node_name: str):  # noqa: ANN001
    result_path = normalize_result_file_path(ctx, node_name=node_name)
    service = ctx.worker_services.dpf_runtime_service
    result_file_ref = service.load_result_file(result_path, run_id=ctx.run_id)
    model_ref = service.load_model(result_file_ref, run_id=ctx.run_id)
    return (
        result_path,
        result_file_ref,
        model_ref,
        ctx.resolve_handle(
            model_ref,
            expected_data_type=DPF_MODEL_DATA_TYPE,
            expected_kind=DPF_MODEL_HANDLE_KIND,
        ),
    )


def _clone_fields_with_curated_metadata(
    ctx,
    fields_ref: Any,
    *,
    model_ref: Any,
    mesh_selection: _ResolvedMeshSelection,
    time_selection: _ResolvedTimeSelection,
) -> Any:  # noqa: ANN001
    metadata = dict(fields_ref.metadata)
    metadata.update(
        {
            "model_handle_id": model_ref.handle_id,
            "selection_mode": mesh_selection.selection_mode,
            "time_scope_mode": time_selection.mode,
            "set_ids": [int(item) for item in time_selection.set_ids],
            "time_values": [float(item) for item in time_selection.time_values],
            "time_scoping_handle_id": time_selection.scoping_ref.handle_id,
        }
    )
    if mesh_selection.scoping_ref is not None:
        metadata["mesh_scoping_handle_id"] = mesh_selection.scoping_ref.handle_id
    return clone_handle_with_metadata(
        ctx,
        fields_ref,
        expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        metadata=metadata,
        release_original=True,
    )


def _extract_curated_fields(
    ctx,  # noqa: ANN001
    *,
    model_ref: Any,
    model: Any,
    node_name: str,
    result_name_override: str = "",
    set_ids_override: tuple[int, ...] = (),
    default_time_scope_mode: str = DPF_TIME_SCOPE_FIRST_SET,
):
    time_selection = _resolve_time_scoping(
        ctx,
        model_ref=model_ref,
        model=model,
        node_name=node_name,
        set_ids_override=set_ids_override,
        default_mode=default_time_scope_mode,
    )
    mesh_selection = _resolve_mesh_selection(
        ctx,
        model_ref=model_ref,
        model=model,
        time_selection=time_selection,
        node_name=node_name,
    )
    location = normalize_result_field_location(ctx.properties.get("location"))
    service = ctx.worker_services.dpf_runtime_service
    fields_ref = service.extract_result_fields(
        model=model_ref,
        result_name=result_name_override or ctx.properties.get("result_name"),
        time_scoping=time_selection.scoping_ref,
        mesh_scoping=mesh_selection.scoping_ref,
        location="" if location == DPF_LOCATION_AUTO else location,
        run_id=ctx.run_id,
    )
    fields_ref = _clone_fields_with_curated_metadata(
        ctx,
        fields_ref,
        model_ref=model_ref,
        mesh_selection=mesh_selection,
        time_selection=time_selection,
    )
    return fields_ref, mesh_selection, time_selection


def _result_source_properties() -> tuple[PropertySpec, ...]:
    return (
        PropertySpec(
            "path",
            "path",
            "",
            "Result File",
            group="Source",
            file_filter=ANSYS_DPF_RESULT_FILES_FILTER,
        ),
    )


def _curated_selection_properties(
    *,
    include_path: bool,
    time_scope_default: str = DPF_TIME_SCOPE_FIRST_SET,
    output_mode_default: str | None = None,
) -> tuple[PropertySpec, ...]:
    source = (
        PropertySpec(
            "path",
            "path",
            "",
            "Result File",
            group="Source",
            file_filter=ANSYS_DPF_RESULT_FILES_FILTER,
        ),
    ) if include_path else ()
    selection = (
        PropertySpec("result_name", "str", "displacement", "Result Type", group="Selection"),
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
        dpf_time_scope_mode_property(default=time_scope_default),
        PropertySpec("set_ids", "str", "", "Set IDs", inspector_editor="textarea", group="Time"),
        PropertySpec("time_values", "str", "", "Time Values", inspector_editor="textarea", group="Time"),
    )
    output = (
        (dpf_output_mode_property(default=output_mode_default),)
        if output_mode_default is not None
        else ()
    )
    return source + selection + output


@builtin_node_type(
    type_id=DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
    display_name="DPF Result Source",
    category_path=DPF_WORKFLOW_CATEGORY_PATH,
    description="Loads a Mechanical result file and model from one .rst or .rth path.",
    surface_family="dpf_workflow",
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
        PortSpec("normalized_path", "out", "data", 'COREX.DataTypes.Path', exposed=True),
    ),
    properties=_result_source_properties(),
)
class DpfWorkflowResultSourceNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        result_path, result_file_ref, model_ref, _ = _result_file_and_model_from_path(
            ctx,
            node_name="DPF Result Source",
        )
        return NodeResult(
            outputs={
                "result_file": result_file_ref,
                "model": model_ref,
                "normalized_path": str(result_path),
            }
        )


@builtin_node_type(
    type_id=DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
    display_name="DPF Result Fields",
    category_path=DPF_WORKFLOW_CATEGORY_PATH,
    description="Extracts a result type with built-in time and mesh scoping controls.",
    surface_family="dpf_workflow",
    ports=(
        PortSpec("model", "in", "data", DPF_MODEL_DATA_TYPE, required=True),
        PortSpec("fields", "out", "data", DPF_FIELDS_CONTAINER_DATA_TYPE, exposed=True),
        PortSpec("mesh_scoping", "out", "data", DPF_SCOPING_DATA_TYPE, exposed=True),
        PortSpec("time_scoping", "out", "data", DPF_SCOPING_DATA_TYPE, exposed=True),
    ),
    properties=_curated_selection_properties(include_path=False),
)
class DpfWorkflowResultFieldsNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        model_ref, model = require_model_input(ctx, node_name="DPF Result Fields")
        fields_ref, mesh_selection, time_selection = _extract_curated_fields(
            ctx,
            model_ref=model_ref,
            model=model,
            node_name="DPF Result Fields",
        )
        outputs: dict[str, Any] = {
            "fields": fields_ref,
            "time_scoping": time_selection.scoping_ref,
        }
        if mesh_selection.scoping_ref is not None:
            outputs["mesh_scoping"] = mesh_selection.scoping_ref
        return NodeResult(outputs=outputs)


@builtin_node_type(
    type_id=DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
    display_name="DPF Result Viewer",
    category_path=DPF_WORKFLOW_CATEGORY_PATH,
    description="Loads a result file, extracts a scoped result, and opens the embedded DPF Viewer.",
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
        PortSpec("normalized_path", "out", "data", 'COREX.DataTypes.Path', exposed=True),
    ),
    properties=(
        *_curated_selection_properties(include_path=True, output_mode_default=DPF_OUTPUT_MODE_BOTH),
        *dpf_viewer_view_property_pack(),
    ),
    surface_family="viewer",
    render_quality=NodeRenderQualitySpec(
        supported_quality_tiers=("full", "proxy"),
    ),
)
class DpfWorkflowResultViewerNodePlugin:
    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        output_mode = normalize_dpf_output_mode(
            ctx.properties.get("output_mode"),
            default=DPF_OUTPUT_MODE_BOTH,
        )
        view_options = dpf_viewer_view_options_from_properties(ctx.properties)
        result_path, result_file_ref, model_ref, model = _result_file_and_model_from_path(
            ctx,
            node_name="DPF Result Viewer",
        )
        fields_ref, mesh_selection, time_selection = _extract_curated_fields(
            ctx,
            model_ref=model_ref,
            model=model,
            node_name="DPF Result Viewer",
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
        if mesh_selection.scoping_ref is not None:
            outputs["mesh_scoping"] = mesh_selection.scoping_ref
        if mesh_ref is not None:
            outputs["mesh"] = mesh_ref
        return NodeResult(outputs=outputs)


__all__ = [
    "DpfWorkflowResultFieldsNodePlugin",
    "DpfWorkflowResultSourceNodePlugin",
    "DpfWorkflowResultViewerNodePlugin",
]
