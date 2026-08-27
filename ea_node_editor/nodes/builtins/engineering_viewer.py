# Purpose: Open neutral CAD/FE scenes in the shared COREX viewer session surface.
# Map: feature_routes/viewer_session_overlay_fullscreen.md
# Tests: tests/test_engineering_viewer_node.py
from __future__ import annotations

from typing import Any

from ea_node_editor.common.scene_protocol import (
    COREX_SCENE_DATA_TYPE,
    COREX_SCENE_HANDLE_KIND,
    ENGINEERING_VIEWER_BACKEND_ID,
    ENGINEERING_SELECTION_DATA_TYPE,
    empty_engineering_selection_set,
    normalize_engineering_selection_set,
    normalize_viewer_opacity,
    normalize_viewer_representation,
)
from ea_node_editor.nodes.builtins.geometry_primitives import (
    OCP_BODY_DATA_TYPE_ID,
    ZONE_DATA_TYPE_ID,
    _resolve_ocp_body,
    _resolve_zone,
    _zone_compound,
)
from ea_node_editor.nodes.core_data_types import VIEWER_SESSION_DATA_TYPE_ID
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.viewer_runtime_contracts import (
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    default_viewer_session_id,
    viewer_session_error,
    viewer_session_failed,
)
from ea_node_editor.runtime_contracts import coerce_runtime_handle_ref

ENGINEERING_VIEWER_NODE_TYPE_ID = "model.viewer"


def _require_scene(value: object, *, label: str):  # noqa: ANN202
    runtime_ref = coerce_runtime_handle_ref(value)
    if (
        runtime_ref is None
        or runtime_ref.data_type_id != COREX_SCENE_DATA_TYPE
        or runtime_ref.kind != COREX_SCENE_HANDLE_KIND
    ):
        raise TypeError(
            f"Model Viewer requires {label} to be an engineering_scene input."
        )
    return runtime_ref


def _scene_fingerprint(scene_ref: Any) -> str:
    source = scene_ref.metadata.get("source")
    if not isinstance(source, dict):
        return ""
    return str(source.get("sha256", "")).strip()


def _prepare_primary_scene(ctx, value: object):  # noqa: ANN001, ANN202
    runtime_ref = coerce_runtime_handle_ref(value)
    if runtime_ref is None:
        return _require_scene(value, label="scene"), None

    if runtime_ref.data_type_id == OCP_BODY_DATA_TYPE_ID:
        native_source_ref, shape = _resolve_ocp_body(ctx, value)
        source_name = "OCPBody"
    elif runtime_ref.data_type_id == ZONE_DATA_TYPE_ID:
        native_source_ref, zone = _resolve_zone(ctx, value)
        shape = _zone_compound(ctx, zone)
        source_name = "Zone"
    else:
        return _require_scene(value, label="scene"), None

    services = ctx.worker_services
    scene_ref = services.prepared_scene_runtime.prepare_cad_shape(
        shape,
        source_identity=(
            f"{native_source_ref.handle_id}:{native_source_ref.worker_generation}"
        ),
        owner_scope=services.run_owner_scope(ctx.run_id),
        source_name=source_name,
    )
    return scene_ref, native_source_ref


def _selection_output_for_scene(
    value: object,
    *,
    layer_fingerprints: dict[str, str],
) -> dict[str, Any]:
    current_layer_fingerprints = {
        str(layer_id).strip(): str(fingerprint).strip().casefold()
        for layer_id, fingerprint in layer_fingerprints.items()
        if str(layer_id).strip() and str(fingerprint).strip()
    }
    current_fingerprint = current_layer_fingerprints.get("primary", "")
    if not current_fingerprint:
        return empty_engineering_selection_set()
    try:
        normalized = normalize_engineering_selection_set(value)
    except (TypeError, ValueError):
        return empty_engineering_selection_set(scene_fingerprint=current_fingerprint)
    if not normalized["selections"]:
        return empty_engineering_selection_set(scene_fingerprint=current_fingerprint)
    if normalized["scene_fingerprint"] != current_fingerprint:
        return empty_engineering_selection_set(scene_fingerprint=current_fingerprint)

    selections = []
    for entry in normalized["selections"]:
        if entry["scene_fingerprint"] != current_fingerprint:
            continue
        entities = [
            entity
            for entity in entry["entities"]
            if current_layer_fingerprints.get(entity["layer_id"])
            == entity["source_fingerprint"]
        ]
        if entities:
            selections.append({**entry, "entities": entities})
    published_name = str(normalized["published_name"])
    if published_name not in {entry["name"] for entry in selections}:
        published_name = ""
    return {
        "schema": normalized["schema"],
        "scene_fingerprint": current_fingerprint,
        "published_name": published_name,
        "selections": selections,
    }


def _metadata_sequence_sample(metadata: dict[str, Any], key: str) -> list[Any]:
    value = metadata.get(key, metadata.get(f"{key}_sample", ()))
    if not isinstance(value, (list, tuple)):
        return []
    return list(value)


def _metadata_sequence_count(
    metadata: dict[str, Any],
    key: str,
    sample: list[Any],
) -> int:
    try:
        return max(0, int(metadata.get(f"{key}_count", len(sample))))
    except (TypeError, ValueError):
        return len(sample)


def _viewer_summary(primary_ref: Any, overlay_ref: Any | None) -> dict[str, Any]:
    point_arrays = _metadata_sequence_sample(primary_ref.metadata, "point_arrays")
    cell_arrays = _metadata_sequence_sample(primary_ref.metadata, "cell_arrays")
    point_array_count = _metadata_sequence_count(
        primary_ref.metadata,
        "point_arrays",
        point_arrays,
    )
    cell_array_count = _metadata_sequence_count(
        primary_ref.metadata,
        "cell_arrays",
        cell_arrays,
    )
    source = primary_ref.metadata.get("source")
    source = source if isinstance(source, dict) else {}
    hierarchy = [
        dict(item)
        for item in _metadata_sequence_sample(
            primary_ref.metadata,
            "hierarchy",
        )
        if isinstance(item, dict)
    ]
    hierarchy_count = _metadata_sequence_count(
        primary_ref.metadata,
        "hierarchy",
        hierarchy,
    )
    capabilities = {
        "attribute_colors": False,
        "body_edges": False,
        "camera": True,
        "camera_bookmarks": True,
        "clipping": True,
        "deformation": False,
        "export_3d": True,
        "live_field_controls": False,
        "live_query_transport": True,
        "measure": True,
        "mesh_edges": True,
        "minmax": bool(point_array_count or cell_array_count),
        "model_tree": bool(hierarchy_count),
        "playback": False,
        "probe": bool(point_array_count or cell_array_count),
        "saved_selections": True,
        "scalar_results": bool(point_array_count or cell_array_count),
        "scene_layers": True,
        "selection_isolate": True,
        "fit_selection": True,
        "orientation_triad": True,
        "projection": True,
        "topological_edges": False,
        "view_cube": True,
        "wireframe_visible_edges": True,
        "world_axes": True,
    }
    scene_layers = [
        {
            "role": "primary",
            "name": str(source.get("source_path", ""))
            .rsplit("\\", 1)[-1]
            .rsplit("/", 1)[-1]
            or "Primary",
            "length_unit": str(primary_ref.metadata.get("length_unit", "")),
        }
    ]
    if overlay_ref is not None:
        overlay_source = overlay_ref.metadata.get("source")
        overlay_source = overlay_source if isinstance(overlay_source, dict) else {}
        scene_layers.append(
            {
                "role": "overlay",
                "name": str(overlay_source.get("source_path", ""))
                .rsplit("\\", 1)[-1]
                .rsplit("/", 1)[-1]
                or "Overlay",
                "length_unit": str(overlay_ref.metadata.get("length_unit", "")),
            }
        )
        hierarchy.extend(
            {
                **dict(item),
                "role": "overlay",
            }
            for item in _metadata_sequence_sample(
                overlay_ref.metadata,
                "hierarchy",
            )
            if isinstance(item, dict)
        )
        capabilities["model_tree"] = capabilities["model_tree"] or bool(
            _metadata_sequence_count(
                overlay_ref.metadata,
                "hierarchy",
                _metadata_sequence_sample(
                    overlay_ref.metadata,
                    "hierarchy",
                ),
            )
        )
    for item in hierarchy:
        item.setdefault("role", "primary")
    return {
        "viewer_kind": "engineering_scene",
        "source_kind": str(primary_ref.metadata.get("source_kind", "")),
        "capabilities": capabilities,
        "scene_layers": scene_layers,
        "model_tree": hierarchy,
        "result_name": (point_arrays + cell_arrays)[0]
        if point_arrays or cell_arrays
        else "Geometry",
        "location": (
            "Point/Cell"
            if point_array_count and cell_array_count
            else "Point"
            if point_array_count
            else "Cell"
            if cell_array_count
            else ""
        ),
        "unit": str(primary_ref.metadata.get("length_unit", "")),
        "scene_fingerprint": _scene_fingerprint(primary_ref),
    }


def _open_engineering_viewer_session(
    ctx,
    *,
    scene_ref: Any,
    overlay_ref: Any | None,
    native_source_ref: Any | None = None,
):  # noqa: ANN001, ANN202
    service = getattr(ctx.worker_services, "viewer_session_service", None)
    if service is None:
        raise RuntimeError("Model Viewer requires viewer session services.")
    session_id = default_viewer_session_id(ctx.workspace_id, ctx.node_id)
    options = {
        "live_mode": "proxy",
        "playback_state": "paused",
        "step_index": 0,
        "show_mesh_edges": bool(ctx.properties.get("show_mesh_edges", False)),
        "show_attribute_colors": bool(
            ctx.properties.get("show_attribute_colors", False)
        ),
        "show_orientation_triad": bool(
            ctx.properties.get("show_orientation_triad", True)
        ),
        "show_view_cube": bool(ctx.properties.get("show_view_cube", True)),
        "show_world_axes": bool(ctx.properties.get("show_world_axes", False)),
        "viewer_background": str(
            ctx.properties.get("viewer_background", "theme") or "theme"
        ),
        "representation": normalize_viewer_representation(
            ctx.properties.get("representation")
        ),
        "primary_opacity": normalize_viewer_opacity(
            ctx.properties.get("primary_opacity"), default=1.0
        ),
        "overlay_opacity": normalize_viewer_opacity(
            ctx.properties.get("overlay_opacity"), default=0.35
        ),
        "parallel_projection": bool(ctx.properties.get("parallel_projection", False)),
        "overlay_color": str(
            ctx.properties.get("overlay_color", "#ff9f43") or "#ff9f43"
        ),
        "clip_enabled": bool(ctx.properties.get("clip_enabled", False)),
        "clip_axis": str(ctx.properties.get("clip_axis", "x") or "x"),
        "clip_offset": float(ctx.properties.get("clip_offset", 0.0) or 0.0),
    }
    data_refs = {"scene": scene_ref}
    if native_source_ref is not None:
        data_refs["native_source"] = native_source_ref
    if overlay_ref is not None:
        data_refs["overlay"] = overlay_ref
    opened = service.open_session(
        OpenViewerSessionCommand(
            workspace_id=ctx.workspace_id,
            node_id=ctx.node_id,
            session_id=session_id,
            backend_id=ENGINEERING_VIEWER_BACKEND_ID,
            data_refs=data_refs,
            playback_state={"state": "paused", "step_index": 0},
            summary=_viewer_summary(scene_ref, overlay_ref),
            options=options,
        )
    )
    if viewer_session_failed(opened):
        raise RuntimeError(viewer_session_error(opened))
    materialized = service.materialize_data(
        MaterializeViewerDataCommand(
            workspace_id=ctx.workspace_id,
            node_id=ctx.node_id,
            session_id=session_id,
            backend_id=ENGINEERING_VIEWER_BACKEND_ID,
            options={"output_profile": "memory"},
        )
    )
    if viewer_session_failed(materialized):
        raise RuntimeError(viewer_session_error(materialized))
    return service.session_handle(ctx.workspace_id, session_id)


def execute_engineering_viewer(ctx) -> NodeResult:  # noqa: ANN001
    scene_ref, native_source_ref = _prepare_primary_scene(
        ctx,
        ctx.inputs.get("scene"),
    )
    overlay_value = ctx.inputs.get("overlay")
    overlay_ref = (
        _require_scene(overlay_value, label="overlay")
        if overlay_value is not None
        else None
    )
    layer_fingerprints = {"primary": _scene_fingerprint(scene_ref)}
    if overlay_ref is not None:
        layer_fingerprints["overlay"] = _scene_fingerprint(overlay_ref)
    selections = _selection_output_for_scene(
        ctx.properties.get("saved_selections"),
        layer_fingerprints=layer_fingerprints,
    )
    session_payload = _open_engineering_viewer_session(
        ctx,
        scene_ref=scene_ref,
        overlay_ref=overlay_ref,
        native_source_ref=native_source_ref,
    )
    return NodeResult(
        outputs={
            "session": session_payload,
            "selections": selections,
        }
    )


__all__ = [
    "ENGINEERING_VIEWER_NODE_TYPE_ID",
    "execute_engineering_viewer",
]
