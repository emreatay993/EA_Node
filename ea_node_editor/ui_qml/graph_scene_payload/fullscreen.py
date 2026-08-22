from __future__ import annotations

"""Fullscreen content payload builders (media / web editor / web page / plot)."""


import copy
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any


from ea_node_editor.nodes.builtins.passive_media import (
    PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID,
    PASSIVE_MEDIA_PDF_PANEL_TYPE_ID,
    PASSIVE_MEDIA_VIDEO_PANEL_TYPE_ID,
)
from ea_node_editor.nodes.builtins.excalidraw import (
    EXCALIDRAW_PREVIEW_REF_PROPERTY,
    EXCALIDRAW_STATE_PROPERTY,
)
from ea_node_editor.nodes.builtins.jupyter_notebook import (
    JUPYTER_NOTEBOOK_AUTOSTART_PROPERTY,
    JUPYTER_NOTEBOOK_FRONTEND_PROPERTY,
    JUPYTER_NOTEBOOK_KERNEL_NAME_PROPERTY,
    JUPYTER_NOTEBOOK_NOTEBOOK_REF_PROPERTY,
    JUPYTER_NOTEBOOK_SERVER_STATE_PROPERTY,
    normalize_jupyter_notebook_properties,
)
from ea_node_editor.nodes.builtins.web_viewer import (
    WEB_PAGE_VIEWER_BROWSER_STATE_PROPERTY,
    WEB_PAGE_VIEWER_DISPLAY_MODE_PROPERTY,
    WEB_PAGE_VIEWER_PERSIST_BROWSER_STATE_PROPERTY,
    normalize_web_page_viewer_display_mode,
    normalize_web_page_viewer_properties,
    web_page_viewer_browser_state_persistence_enabled,
)
from ea_node_editor.jupyter_host import check_jupyter_available
from ea_node_editor.nodes.node_specs import NodeTypeSpec
from ea_node_editor.ui.media_preview_provider import describe_local_image
from ea_node_editor.ui.mail_preview_provider import describe_mail_preview
from ea_node_editor.ui.pdf_preview_provider import describe_pdf_preview
from ea_node_editor.ui_qml.surface_contracts import (
    surface_spec_payload_for_node_type,
    surface_spec_payload_for_values,
)
from ea_node_editor.web_host.assets import (
    resolve_excalidraw_host_index_path,
    resolve_excalidraw_host_index_url,
)
from ea_node_editor.web_host.bridge import MAX_SCENE_STATE_PAYLOAD_BYTES
from ea_node_editor.web_host.navigation_policy import is_project_artifact_location
from ea_node_editor.web_host.webengine import check_webengine_available

if TYPE_CHECKING:
    from ea_node_editor.graph.records import NodeInstance

from ea_node_editor.ui_qml.graph_scene_payload.normalize import (
    PLOT_CONTENT_KIND,
    WEB_PAGE_CONTENT_KIND,
    _bool_property,
    _bounded_float_property,
    _image_preview_source_url,
    _int_property,
    _mapping_value,
    _non_negative_int_property,
    _normalized_crop_rect,
    _normalized_fit_mode,
    _normalized_image_rotation_degrees,
    _normalized_json_object,
    _normalized_preview_ref,
    _normalized_unfocused_behavior,
    _normalized_video_fit_mode,
    _normalized_video_timeline_bookmarks,
    _resolved_local_file_source_url,
    _resolved_web_page_navigation_location,
    _surface_spec_payload_for_node,
    _web_page_navigation_decision_payload,
)
from ea_node_editor.ui_qml.graph_scene_payload.kinds.plot import (
    _plot_embedded_render_policy,
    _plot_type_from_node_payload,
)


def build_content_fullscreen_media_payload(
    *,
    workspace_id: str,
    node: "NodeInstance",
    spec: NodeTypeSpec,
    project_path: str | None = None,
    project_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    properties = copy.deepcopy(node.properties)
    source_path = str(properties.get("source_path", "") or "").strip()
    surface_variant = str(spec.surface_variant or "").strip()
    payload: dict[str, Any] = {
        "workspace_id": str(workspace_id or ""),
        "node_id": str(node.node_id),
        "type_id": str(node.type_id),
        "title": str(node.title or spec.display_name),
        "display_name": str(spec.display_name),
        "surface_family": str(spec.surface_family or ""),
        "surface_variant": surface_variant,
        "surface_spec": surface_spec_payload_for_node_type(type_id=node.type_id, spec=spec),
        "source_path": source_path,
        "properties": properties,
    }
    if node.type_id == PASSIVE_MEDIA_PDF_PANEL_TYPE_ID:
        page_number = _int_property(properties.get("page_number"), 1)
        pdf_preview = describe_pdf_preview(source_path, page_number)
        payload.update(
            {
                "media_kind": "pdf",
                "fit_mode": "contain",
                "page_number": page_number,
                "pdf_preview": pdf_preview,
                "resolved_page_number": int(pdf_preview.get("resolved_page_number", page_number) or page_number),
                "preview_url": str(pdf_preview.get("preview_url", "") or ""),
                "resolved_source_url": str(pdf_preview.get("resolved_source_url", "") or ""),
            }
        )
        return payload

    if node.type_id == PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID:
        mail_preview = describe_mail_preview(source_path)
        metadata = mail_preview.get("metadata")
        attachments = mail_preview.get("attachments")
        payload.update(
            {
                "media_kind": "mail",
                "fit_mode": "contain",
                "mail_preview": mail_preview,
                "preview_url": str(mail_preview.get("preview_url", "") or ""),
                "resolved_source_url": str(mail_preview.get("resolved_source_url", "") or ""),
                "preview_state": str(mail_preview.get("state", "") or ""),
                "preview_message": str(mail_preview.get("message", "") or ""),
                "metadata": copy.deepcopy(dict(metadata)) if isinstance(metadata, Mapping) else {},
                "attachments": copy.deepcopy(list(attachments)) if isinstance(attachments, list) else [],
                "attachment_summary": str(mail_preview.get("attachment_summary", "") or "No attachments"),
            }
        )
        return payload

    if node.type_id == PASSIVE_MEDIA_VIDEO_PANEL_TYPE_ID:
        payload.update(
            {
                "media_kind": "video",
                "fit_mode": _normalized_video_fit_mode(properties.get("fit_mode")),
                "resolved_source_url": _resolved_local_file_source_url(
                    source_path,
                    project_path=project_path,
                    project_metadata=project_metadata,
                ),
                "preview_url": "",
                "auto_play": _bool_property(properties.get("auto_play"), False),
                "loop": _bool_property(properties.get("loop"), False),
                "muted": _bool_property(properties.get("muted"), False),
                "volume": _bounded_float_property(properties.get("volume"), 1.0, minimum=0.0, maximum=1.0),
                "playback_rate": _bounded_float_property(
                    properties.get("playback_rate"),
                    1.0,
                    minimum=0.25,
                    maximum=4.0,
                ),
                "position_ms": _non_negative_int_property(properties.get("position_ms"), 0),
                "timeline_bookmarks": _normalized_video_timeline_bookmarks(
                    properties.get("timeline_bookmarks")
                ),
                "clip_enabled": _bool_property(properties.get("clip_enabled"), False),
                "clip_start_ms": _non_negative_int_property(properties.get("clip_start_ms"), 0),
                "clip_end_ms": _non_negative_int_property(properties.get("clip_end_ms"), 0),
                "unfocused_behavior": _normalized_unfocused_behavior(properties.get("unfocused_behavior")),
                "transient_state": {},
            }
        )
        return payload

    resolved_source_url = _resolved_local_file_source_url(
        source_path,
        project_path=project_path,
        project_metadata=project_metadata,
    )
    image_preview = describe_local_image(resolved_source_url or source_path)
    resolved_source_url = str(image_preview.get("resolved_source_url", "") or resolved_source_url)
    payload.update(
        {
            "media_kind": "image",
            "fit_mode": _normalized_fit_mode(properties.get("fit_mode")),
            "crop": _normalized_crop_rect(properties),
            "rotation_degrees": _normalized_image_rotation_degrees(properties.get("rotation_degrees")),
            "mirror_horizontal": _bool_property(properties.get("mirror_horizontal"), False),
            "mirror_vertical": _bool_property(properties.get("mirror_vertical"), False),
            "preview_url": _image_preview_source_url(resolved_source_url),
            "resolved_source_url": resolved_source_url,
            "preview_state": str(image_preview.get("state", "") or ""),
            "preview_message": str(image_preview.get("message", "") or ""),
            "format": str(image_preview.get("format", "") or ""),
            "source_pixel_width": int(image_preview.get("source_pixel_width", 0) or 0),
            "source_pixel_height": int(image_preview.get("source_pixel_height", 0) or 0),
            "frame_count": int(image_preview.get("frame_count", 0) or 0),
            "animation_supported": bool(image_preview.get("animation_supported", False)),
            "is_animated": bool(image_preview.get("is_animated", False)),
        }
    )
    return payload


def build_content_fullscreen_web_editor_payload(
    *,
    workspace_id: str,
    node: "NodeInstance",
    spec: NodeTypeSpec,
) -> dict[str, Any]:
    properties = copy.deepcopy(node.properties)
    availability = check_webengine_available()
    asset_path = ""
    asset_url = ""
    asset_error = ""
    try:
        resolved_path = resolve_excalidraw_host_index_path()
        asset_path = str(resolved_path)
        asset_url = resolve_excalidraw_host_index_url()
    except Exception as exc:  # noqa: BLE001
        asset_error = str(exc)
    return {
        "workspace_id": str(workspace_id or ""),
        "node_id": str(node.node_id),
        "type_id": str(node.type_id),
        "title": str(node.title or spec.display_name),
        "display_name": str(spec.display_name),
        "surface_family": str(spec.surface_family or ""),
        "surface_variant": str(spec.surface_variant or ""),
        "surface_spec": surface_spec_payload_for_node_type(type_id=node.type_id, spec=spec),
        "asset_path": asset_path,
        "asset_url": asset_url,
        "asset_error": asset_error,
        "excalidraw_state": _normalized_json_object(
            properties.get(EXCALIDRAW_STATE_PROPERTY, {})
        ),
        "excalidraw_preview_ref": _normalized_preview_ref(
            properties.get(EXCALIDRAW_PREVIEW_REF_PROPERTY, "")
        ),
        "state_property_key": EXCALIDRAW_STATE_PROPERTY,
        "preview_ref_property_key": EXCALIDRAW_PREVIEW_REF_PROPERTY,
        "webengine_available": bool(availability.available),
        "webengine_reason": str(availability.reason or ""),
        "webengine_module_name": str(availability.module_name or ""),
        "webengine_exception_type": str(availability.exception_type or ""),
        "max_payload_bytes": MAX_SCENE_STATE_PAYLOAD_BYTES,
    }


def build_content_fullscreen_web_page_payload(
    *,
    workspace_id: str,
    node: "NodeInstance",
    spec: NodeTypeSpec,
    project_path: str | None = None,
    project_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    properties = normalize_web_page_viewer_properties(copy.deepcopy(node.properties))
    availability = check_webengine_available()
    start_location = str(properties.get("start_location", "") or "").strip()
    persist_browser_state = web_page_viewer_browser_state_persistence_enabled(
        properties.get(WEB_PAGE_VIEWER_PERSIST_BROWSER_STATE_PROPERTY, True)
    )
    browser_state = (
        _normalized_json_object(properties.get(WEB_PAGE_VIEWER_BROWSER_STATE_PROPERTY, {}))
        if persist_browser_state
        else {}
    )
    browser_state_location = str(
        browser_state.get("current_url")
        or browser_state.get("current_location")
        or browser_state.get("url")
        or ""
    ).strip()
    current_location = (
        start_location
        if is_project_artifact_location(start_location)
        else (browser_state_location or start_location)
    )
    navigation_location = _resolved_web_page_navigation_location(
        current_location,
        project_path=project_path,
        project_metadata=project_metadata,
    )
    payload: dict[str, Any] = {
        "workspace_id": str(workspace_id or ""),
        "node_id": str(node.node_id),
        "type_id": str(node.type_id),
        "content_kind": WEB_PAGE_CONTENT_KIND,
        "title": str(node.title or spec.display_name),
        "display_name": str(spec.display_name),
        "surface_family": str(spec.surface_family or ""),
        "surface_variant": str(spec.surface_variant or ""),
        "surface_spec": _surface_spec_payload_for_node(type_id=node.type_id, spec=spec),
        "start_location": start_location,
        "current_location": current_location,
        "navigation_location": navigation_location,
        "display_mode": normalize_web_page_viewer_display_mode(
            properties.get(WEB_PAGE_VIEWER_DISPLAY_MODE_PROPERTY)
        ),
        "persist_browser_state": persist_browser_state,
        "browser_state": browser_state,
        "properties": properties,
        "navigation_decision": _web_page_navigation_decision_payload(navigation_location),
        "qwebchannel_allowed": False,
    }
    payload.update(availability.as_payload())
    return payload


JUPYTER_NOTEBOOK_CONTENT_KIND = "jupyter_notebook"


def build_jupyter_notebook_payload(
    *,
    workspace_id: str,
    node: "NodeInstance",
    spec: NodeTypeSpec,
    project_path: str | None = None,
    project_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the Jupyter-notebook surface payload.

    Pure data assembly: this NEVER starts the Jupyter server (it runs on the
    payload-build thread and in headless tests). The live, tokened localhost URL
    is built at runtime by the server bridge from ``notebook_ref`` and is
    deliberately never serialized into the scene payload or the project file.
    """

    properties = normalize_jupyter_notebook_properties(copy.deepcopy(node.properties))
    notebook_ref = str(properties.get(JUPYTER_NOTEBOOK_NOTEBOOK_REF_PROPERTY, "") or "").strip()
    notebook_location = _resolved_local_file_source_url(
        notebook_ref,
        project_path=project_path,
        project_metadata=project_metadata,
    )
    server_state = _normalized_json_object(
        properties.get(JUPYTER_NOTEBOOK_SERVER_STATE_PROPERTY, {})
    )
    payload: dict[str, Any] = {
        "workspace_id": str(workspace_id or ""),
        "node_id": str(node.node_id),
        "type_id": str(node.type_id),
        "content_kind": JUPYTER_NOTEBOOK_CONTENT_KIND,
        "title": str(node.title or spec.display_name),
        "display_name": str(spec.display_name),
        "surface_family": str(spec.surface_family or ""),
        "surface_variant": str(spec.surface_variant or ""),
        "surface_spec": _surface_spec_payload_for_node(type_id=node.type_id, spec=spec),
        "notebook_ref": notebook_ref,
        "notebook_location": notebook_location,
        "frontend": str(properties.get(JUPYTER_NOTEBOOK_FRONTEND_PROPERTY, "") or ""),
        "kernel_name": str(properties.get(JUPYTER_NOTEBOOK_KERNEL_NAME_PROPERTY, "") or ""),
        "autostart": _bool_property(properties.get(JUPYTER_NOTEBOOK_AUTOSTART_PROPERTY), True),
        "server_state": server_state,
        "properties": properties,
        "qwebchannel_allowed": False,
    }
    payload.update(check_jupyter_available().as_payload())
    payload.update(check_webengine_available().as_payload())
    return payload


def build_content_fullscreen_plot_payload(
    *,
    workspace_id: str,
    node: "NodeInstance",
    spec: NodeTypeSpec,
    scene_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    plot_type = _plot_type_from_node_payload(node=node, spec=spec)
    payload_surface = _mapping_value(scene_payload.get("plot_surface")) if isinstance(scene_payload, Mapping) else {}
    if not payload_surface:
        payload_surface = _plot_embedded_render_policy(
            node=node,
            spec=spec,
            graph_theme_bridge=None,
        ) or {}
    surface_spec = surface_spec_payload_for_values(
        type_id=node.type_id,
        family="plot",
        variant=plot_type,
    )
    return {
        "workspace_id": str(workspace_id or ""),
        "node_id": str(node.node_id),
        "type_id": str(node.type_id),
        "content_kind": PLOT_CONTENT_KIND,
        "title": str(node.title or spec.display_name),
        "display_name": str(spec.display_name),
        "surface_family": "plot",
        "surface_variant": plot_type,
        "surface_spec": surface_spec,
        "properties": copy.deepcopy(node.properties),
        "plot_surface": copy.deepcopy(payload_surface),
    }
