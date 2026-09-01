from __future__ import annotations

from typing import Any

from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_OUTPUT_MODE_BOTH,
    DPF_OUTPUT_MODE_MEMORY,
    DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY,
    normalize_dpf_viewer_view_options,
    wrap_field_handle_as_fields_container,
)
from ea_node_editor.nodes.viewer_runtime_contracts import (
    DPF_EXECUTION_VIEWER_BACKEND_ID,
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    UpdateViewerSessionCommand,
    default_viewer_session_id,
    viewer_session_error,
    viewer_session_failed,
)
from ea_node_editor.runtime_contracts import coerce_runtime_handle_ref


def _first_int_metadata(metadata: dict[str, Any], singular_key: str, plural_key: str) -> int:
    value = metadata.get(singular_key)
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = 0
    if normalized > 0:
        return normalized
    values = metadata.get(plural_key)
    if values is None:
        values = metadata.get(f"{plural_key}_sample")
    if isinstance(values, (list, tuple)) and values:
        try:
            return int(values[0])
        except (TypeError, ValueError):
            return 0
    return 0


def _first_float_metadata(metadata: dict[str, Any], singular_key: str, plural_key: str) -> float | None:
    value = metadata.get(singular_key)
    if value is None:
        values = metadata.get(plural_key)
        if values is None:
            values = metadata.get(f"{plural_key}_sample")
        if isinstance(values, (list, tuple)) and values:
            value = values[0]
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def viewer_summary_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "result_name": str(metadata.get("result_name", "")).strip(),
    }
    field_count = metadata.get("field_count")
    try:
        normalized_field_count = int(field_count)
    except (TypeError, ValueError):
        normalized_field_count = 0
    if normalized_field_count > 0:
        summary["field_count"] = normalized_field_count
    normalized_set_id = _first_int_metadata(metadata, "set_id", "set_ids")
    if normalized_set_id > 0:
        summary["set_id"] = normalized_set_id
        summary["set_label"] = f"Set {normalized_set_id}"
        summary["step_index"] = max(0, normalized_set_id - 1)
    normalized_time_value = _first_float_metadata(metadata, "time_value", "time_values")
    if normalized_time_value is not None:
        summary["time_value"] = normalized_time_value
        summary["time_label"] = f"{normalized_time_value:g}"
    unit = str(metadata.get("unit", "") or "").strip()
    if unit:
        summary["unit"] = unit
    location = str(metadata.get("location", "") or "").strip()
    if location:
        summary["location"] = location
    time_values = metadata.get("time_values")
    if isinstance(time_values, (list, tuple)) and time_values:
        normalized_time_values: list[float] = []
        for value in time_values:
            try:
                normalized_time_values.append(float(value))
            except (TypeError, ValueError):
                normalized_time_values = []
                break
        if normalized_time_values:
            summary["time_values"] = normalized_time_values
    value_ranges = metadata.get("value_ranges")
    if isinstance(value_ranges, (list, tuple)) and value_ranges:
        normalized_ranges = [dict(entry) for entry in value_ranges if isinstance(entry, dict)]
        if len(normalized_ranges) == len(value_ranges):
            summary["value_ranges"] = normalized_ranges
    return summary


def viewer_summary_from_field_ref(field_ref) -> dict[str, Any]:  # noqa: ANN001
    return viewer_summary_from_metadata(dict(field_ref.metadata))


def open_dpf_viewer_session_payload(
    ctx,
    *,
    field_ref=None,
    fields_ref=None,
    model_ref,
    mesh_ref,
    output_mode: str,
    show_mesh_edges: bool = False,
    view_options: dict[str, Any] | None = None,
) -> dict[str, Any]:  # noqa: ANN001
    normalized_view_options = normalize_dpf_viewer_view_options(
        view_options
        if view_options is not None
        else {DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY: bool(show_mesh_edges)}
    )
    release_fields_ref = False
    if fields_ref is None:
        source_ref = coerce_runtime_handle_ref(field_ref)
        if (
            source_ref is not None
            and source_ref.data_type_id == DPF_FIELDS_CONTAINER_DATA_TYPE
            and source_ref.kind == DPF_FIELDS_CONTAINER_HANDLE_KIND
        ):
            fields_ref = source_ref
        else:
            fields_ref = wrap_field_handle_as_fields_container(
                ctx,
                field_ref,
                node_name="DPF Viewer",
            )
            release_fields_ref = True
    runtime_fields_ref = coerce_runtime_handle_ref(fields_ref)
    if (
        runtime_fields_ref is None
        or runtime_fields_ref.data_type_id != DPF_FIELDS_CONTAINER_DATA_TYPE
        or runtime_fields_ref.kind != DPF_FIELDS_CONTAINER_HANDLE_KIND
    ):
        raise TypeError("DPF Viewer requires a dpf.field or dpf.fields_container handle input.")
    session_service = getattr(ctx.worker_services, "viewer_session_service", None)
    if session_service is None:
        raise RuntimeError("DPF Viewer requires viewer session services.")
    session_id = default_viewer_session_id(ctx.workspace_id, ctx.node_id)
    summary = viewer_summary_from_metadata(dict(runtime_fields_ref.metadata))
    options = {
        "live_mode": "proxy",
        "output_profile": output_mode,
        "playback_state": "paused",
        **normalized_view_options,
        "step_index": int(summary.get("step_index", 0)),
    }
    playback_state = {
        "state": "paused",
        "step_index": int(summary.get("step_index", 0)),
    }
    try:
        opened = session_service.open_session(
            OpenViewerSessionCommand(
                workspace_id=ctx.workspace_id,
                node_id=ctx.node_id,
                session_id=session_id,
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                data_refs={
                    "fields": runtime_fields_ref,
                    "model": model_ref,
                    **({"mesh": mesh_ref} if mesh_ref is not None else {}),
                },
                camera_state={},
                playback_state=playback_state,
                summary=summary,
                options=options,
            )
        )
        if viewer_session_failed(opened):
            raise RuntimeError(viewer_session_error(opened))

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
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                    options={
                        "output_profile": materialize_output_mode,
                        "live_mode": "proxy",
                        **normalized_view_options,
                    },
                )
            )
            if viewer_session_failed(materialized):
                raise RuntimeError(viewer_session_error(materialized))
            if materialize_output_mode != output_mode:
                updated = session_service.update_session(
                    UpdateViewerSessionCommand(
                        workspace_id=ctx.workspace_id,
                        node_id=ctx.node_id,
                        session_id=session_id,
                        backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                        playback_state=playback_state,
                        options={
                            "output_profile": output_mode,
                            **normalized_view_options,
                        },
                    )
                )
                if viewer_session_failed(updated):
                    raise RuntimeError(viewer_session_error(updated))

        return session_service.session_handle(ctx.workspace_id, session_id)
    finally:
        if release_fields_ref:
            ctx.release_handle(runtime_fields_ref)


__all__ = [
    "default_viewer_session_id",
    "open_dpf_viewer_session_payload",
    "viewer_summary_from_field_ref",
    "viewer_summary_from_metadata",
]
