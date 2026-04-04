from __future__ import annotations

from typing import Any

from ea_node_editor.execution.protocol import (
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    UpdateViewerSessionCommand,
    ViewerSessionFailedEvent,
)
from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_OUTPUT_MODE_BOTH,
    DPF_OUTPUT_MODE_MEMORY,
    DPF_VIEWER_LIVE_POLICY_KEEP_LIVE,
    wrap_field_handle_as_fields_container,
)
from ea_node_editor.runtime_contracts import default_viewer_session_id, viewer_event_payload


def viewer_summary_from_field_ref(field_ref) -> dict[str, Any]:  # noqa: ANN001
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


def open_dpf_viewer_session_payload(
    ctx,
    *,
    field_ref,
    model_ref,
    mesh_ref,
    output_mode: str,
    live_policy: str,
) -> dict[str, Any]:  # noqa: ANN001
    wrapped_fields_ref = wrap_field_handle_as_fields_container(
        ctx,
        field_ref,
        node_name="DPF Viewer",
    )
    session_service = ctx.worker_services.viewer_session_service
    session_id = default_viewer_session_id(ctx.workspace_id, ctx.node_id)
    summary = viewer_summary_from_field_ref(field_ref)
    options = {
        "live_mode": "proxy",
        "live_policy": live_policy,
        "keep_live": live_policy == DPF_VIEWER_LIVE_POLICY_KEEP_LIVE,
        "output_profile": output_mode,
        "playback_state": "paused",
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
                    "fields": wrapped_fields_ref,
                    "model": model_ref,
                    **({"mesh": mesh_ref} if mesh_ref is not None else {}),
                },
                camera_state={},
                playback_state=playback_state,
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
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
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
                        backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                        playback_state=playback_state,
                        options={"output_profile": output_mode},
                    )
                )
                if isinstance(updated, ViewerSessionFailedEvent):
                    raise RuntimeError(updated.error)
                session_event = updated

        return viewer_event_payload(session_event)
    finally:
        ctx.release_handle(wrapped_fields_ref)


__all__ = [
    "default_viewer_session_id",
    "open_dpf_viewer_session_payload",
    "viewer_event_payload",
    "viewer_summary_from_field_ref",
]
