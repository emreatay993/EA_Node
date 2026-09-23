# Purpose: Node automation handlers: add/text/media/web, update, style, delete, duplicate (T05); every mutation goes through GraphSceneBridge and is verified after.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_nodes.py
from __future__ import annotations

import copy
import tempfile
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.automation.errors import (
    NO_EFFECT,
    NOT_FOUND,
    PROPERTY_LOCKED_BY_PORT,
    WRONG_SCOPE,
    AutomationOpError,
    invalid_params,
    no_effect,
    not_found,
)
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.builtins.media_panel import MEDIA_PANEL_TYPE_ID
from ea_node_editor.nodes.builtins.passive_annotation import PASSIVE_ANNOTATION_TEXT_TYPE_ID
from ea_node_editor.nodes.builtins.web_viewer import (
    WEB_PAGE_VIEWER_DISPLAY_MODE_PROPERTY,
    WEB_PAGE_VIEWER_DISPLAY_MODES,
    WEB_PAGE_VIEWER_START_LOCATION_PROPERTY,
    WEB_PAGE_VIEWER_TYPE_ID,
)
from ea_node_editor.nodes.file_dialog_filters import media_kind_from_source
from ea_node_editor.nodes.node_specs import NodeTypeSpec
from ea_node_editor.passive_style_normalization import normalize_passive_node_style_payload
from ea_node_editor.settings import PROJECT_NODE_INPUTS_DIRNAME
from ea_node_editor.text_style import (
    TEXT_STYLE_FORMATS,
    normalize_text_annotation_style_payload,
    rich_text_format_property_key,
    rich_text_style_property_key,
)
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui.shell.automation.handlers.catalog import (
    NODE_STYLE_ALIASES,
    NODE_STYLE_KEYS,
    TEXT_STYLE_ALIASES,
    TEXT_STYLE_KEYS,
    lookup_style_preset,
    title_is_property_backed,
)
from ea_node_editor.ui.shell.automation.handlers.graph_read import (
    effective_port_records,
    exposed_port_map,
    instance_spec,
    json_safe,
)

_MISSING = object()
_UPDATE_FIELDS = (
    "title",
    "x",
    "y",
    "width",
    "height",
    "properties",
    "port_labels",
    "exposed_ports",
    "collapsed",
    "locked",
)
_SCALAR_STATE_FIELDS = ("title", "x", "y", "width", "height", "collapsed", "locked")
_MAPPED_STATE_FIELDS = ("properties", "port_labels", "exposed_ports")
_GRADIENT_DEPENDENT_KEYS = frozenset({"gradient_color", "gradient_direction"})
_MEDIA_PASSTHROUGH_KEYS = ("fit_mode", "show_title", "show_frame")
_INLINE_HTML_DIRNAME = "automation"


# ------------------------------------------------------------------ helpers


def _invalid(op: str, problems: list[str], **details: Any) -> AutomationOpError:
    error = invalid_params(problems, op=op)
    error.details.update(details)
    return error


def _unique_ids(values: Any) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        node_id = str(value or "").strip()
        if node_id and node_id not in seen:
            seen.add(node_id)
            ordered.append(node_id)
    return ordered


def _parent_for_creation(context: AutomationContext, op: str, params: Mapping[str, Any]) -> str | None:
    """Graph ops act in the open scope: an explicit parent must be that scope's shell."""
    requested = str(params.get("parent_node_id") or "").strip()
    scope_parent = context.scope_parent_id()
    if not requested:
        return scope_parent
    if context.node_or_none(requested) is None:
        raise not_found("Node", requested)
    if requested != scope_parent:
        raise AutomationOpError(
            WRONG_SCOPE,
            f"parent_node_id '{requested}' is not the open scope (current parent: {scope_parent or 'root'}).",
            details={"op": op, "parent_node_id": requested, "scope_path": context.scope_path()},
        )
    return scope_parent


def _default_property_value(spec: NodeTypeSpec, key: str) -> Any:
    for prop in spec.properties:
        if prop.key == key:
            return prop.make_default()
    return None


def _body_tracks_title(spec: NodeTypeSpec) -> bool:
    """True for flowchart shapes whose visible label is ``properties["body"]``.

    GraphFlowchartNodeSurface renders ``body`` inside the shape (falling back to the
    title only when body is empty), and the shape-label types default body to the
    shape name (process: title == body == "Process"). Card / callout / tick /
    timestamp / ... declare an empty or template body, suppress the title fallback,
    and treat body as separate content, so they never track the title.
    """
    if str(spec.surface_family or "") != "flowchart":
        return False
    default_body = _default_property_value(spec, "body")
    return (
        isinstance(default_body, str)
        and bool(default_body.strip())
        and default_body == _default_property_value(spec, "title")
    )


def _body_follows_title(spec: NodeTypeSpec, node: NodeInstance) -> bool:
    """A label-tracking body follows a title change unless the user customised it."""
    if not _body_tracks_title(spec):
        return False
    body = str(node.properties.get("body") or "")
    tracked = {"", str(node.title), str(node.properties.get("title") or ""), str(_default_property_value(spec, "body") or "")}
    return body.strip() == "" or body in tracked


def _spec_property_keys(context: AutomationContext, spec: NodeTypeSpec, overrides: Mapping[str, Any]) -> set[str]:
    merged = context.registry.default_properties(spec.type_id)
    merged.update(overrides)
    try:
        resolved = context.registry.resolve_spec(spec.type_id, merged)
    except Exception:  # noqa: BLE001 - unknown override keys make instance resolution fail; validate against the base spec
        resolved = spec
    return {prop.key for prop in resolved.properties}


def _create_node(
    context: AutomationContext,
    op: str,
    *,
    type_id: str,
    params: Mapping[str, Any],
    properties: Mapping[str, Any] | None,
    exposed_port_overrides: dict[str, bool] | None = None,
    after_create: Any = None,
) -> NodeInstance:
    """Shared node.add* core: validate, create through the scene, verify the record exists and carries the title.

    Title trap: for flowchart / annotation / group_backdrop families the rendered
    title is ``properties["title"]`` and ``_create_node_from_type`` re-syncs
    ``node.title`` from that property right after creation, discarding
    ``initial_title``. Those families therefore get the title as a property
    override; every other type uses ``initial_title``. Flowchart shape-label
    types also get ``body`` = title (their in-shape label) unless the caller
    passed ``properties.body`` explicitly.
    """
    spec = context.spec_for(type_id)
    parent_node_id = _parent_for_creation(context, op, params)
    overrides: dict[str, Any] = {str(key): value for key, value in dict(properties or {}).items()}
    initial_title: str | None = None
    normalized_title = ""
    if params.get("title") is not None:
        normalized_title = str(params["title"]).strip()
        if not normalized_title:
            raise _invalid(op, ["title: must not be blank"])
        if title_is_property_backed(spec):
            overrides["title"] = normalized_title
            if "body" not in overrides and _body_tracks_title(spec):
                overrides["body"] = normalized_title
        else:
            initial_title = normalized_title
    known_keys = _spec_property_keys(context, spec, overrides)
    unknown = sorted(key for key in overrides if key not in known_keys)
    if unknown:
        raise _invalid(
            op,
            [f"properties.{key}: unknown property for {spec.type_id}" for key in unknown],
            available=sorted(known_keys),
        )
    width = params.get("width")
    height = params.get("height")
    before_ids = context.node_id_set()
    node_id = context.scene.create_node_from_type(
        type_id=spec.type_id,
        x=float(params["x"]),
        y=float(params["y"]),
        parent_node_id=parent_node_id,
        select_node=bool(params.get("select", False)),
        property_overrides=overrides or None,
        exposed_port_overrides=exposed_port_overrides,
        initial_title=initial_title,
        custom_width=float(width) if width is not None else None,
        custom_height=float(height) if height is not None else None,
        after_create=after_create,
    )
    node = context.node_or_none(str(node_id or ""))
    if node is None:
        raise no_effect(
            op,
            "the scene did not create the node",
            details={"type_id": spec.type_id, "new_node_ids": context.new_ids_since(before_ids)},
        )
    if normalized_title and node.title != normalized_title:
        raise no_effect(
            op,
            f"title '{normalized_title}' was not applied (node title is '{node.title}')",
            details={"node_id": node.node_id, "type_id": spec.type_id},
        )
    return node


def _text_style_properties(content_key: str, style: Any, *, op: str) -> dict[str, Any]:
    """Map an agent text-style dict onto the rich-text slot property keys of ``content_key``."""
    if style is None:
        return {}
    if not isinstance(style, Mapping):
        raise _invalid(op, ["style: must be an object"])
    mapped = {TEXT_STYLE_ALIASES.get(str(key), str(key)): value for key, value in style.items()}
    unknown = sorted(key for key in mapped if key not in TEXT_STYLE_KEYS)
    if unknown:
        raise _invalid(
            op,
            [f"style.{key}: unknown text style key" for key in unknown],
            available=list(TEXT_STYLE_KEYS),
            aliases=dict(TEXT_STYLE_ALIASES),
        )
    normalized = normalize_text_annotation_style_payload(mapped)
    result = {rich_text_style_property_key(content_key, key): value for key, value in normalized.items()}
    if "format" in mapped:
        text_format = str(mapped["format"] or "").strip().lower()
        if text_format not in TEXT_STYLE_FORMATS:
            raise _invalid(op, [f"style.format: must be one of {list(TEXT_STYLE_FORMATS)}"])
        result[rich_text_format_property_key(content_key)] = text_format
    return result


def _normalize_node_style(style: Any, *, op: str) -> dict[str, Any]:
    """Validate a passive node style payload against the owner's key set (unknown/invalid -> INVALID_PARAMS)."""
    if not isinstance(style, Mapping):
        raise _invalid(op, ["style: must be an object"])
    mapped = {NODE_STYLE_ALIASES.get(str(key), str(key)): value for key, value in style.items()}
    unknown = sorted(key for key in mapped if key not in NODE_STYLE_KEYS)
    if unknown:
        raise _invalid(
            op,
            [f"style.{key}: unknown node style key" for key in unknown],
            available=list(NODE_STYLE_KEYS),
            aliases=dict(NODE_STYLE_ALIASES),
        )
    normalized = normalize_passive_node_style_payload(mapped)
    gradient_disabled = mapped.get("gradient_enabled") is False
    dropped = sorted(
        key
        for key in mapped
        if key not in normalized and not (gradient_disabled and key in _GRADIENT_DEPENDENT_KEYS)
    )
    if dropped:
        raise _invalid(
            op,
            [f"style.{key}: value {mapped[key]!r} was rejected by the style normaliser" for key in dropped],
            hint_keys=list(NODE_STYLE_KEYS),
        )
    return normalized


def _node_state(context: AutomationContext, node: NodeInstance) -> dict[str, Any]:
    bounds = context.node_bounds(node.node_id)
    width = bounds[2] if bounds is not None else (float(node.custom_width) if node.custom_width is not None else None)
    height = bounds[3] if bounds is not None else (float(node.custom_height) if node.custom_height is not None else None)
    return {
        "title": node.title,
        "x": float(node.x),
        "y": float(node.y),
        "width": width,
        "height": height,
        "collapsed": bool(node.collapsed),
        "locked": bool(node.locked),
        "properties": copy.deepcopy(node.properties),
        "port_labels": dict(node.port_labels),
        "exposed_ports": exposed_port_map(context, node),
    }


def _changed_fields(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    changed = [field for field in _SCALAR_STATE_FIELDS if before[field] != after[field]]
    for group in _MAPPED_STATE_FIELDS:
        keys = set(before[group]) | set(after[group])
        changed.extend(
            f"{group}.{key}"
            for key in sorted(keys)
            if before[group].get(key, _MISSING) != after[group].get(key, _MISSING)
        )
    return changed


def _require_effective_port(context: AutomationContext, node: NodeInstance, port_key: Any) -> str:
    key = str(port_key or "").strip()
    available = sorted(exposed_port_map(context, node))
    if key not in available:
        raise AutomationOpError(
            NOT_FOUND,
            f"Port '{key}' does not exist on node '{node.node_id}' ({node.type_id}).",
            hint="Call graph.get_node to list the node's effective ports.",
            details={"node_id": node.node_id, "port": key, "available": available},
        )
    return key


def _port_locked_property_keys(context: AutomationContext, node: NodeInstance, keys: list[str]) -> list[str]:
    """Properties the inspector would grey out: exposed input port with the same key that has an edge.

    The media panel additionally refuses ``source`` edits while its source port is
    exposed (ValidatedGraphMutation._guard_exposed_media_source_updates).
    """
    exposed_inputs = {port.key for port in effective_port_records(context, node) if port.direction == "in" and port.exposed}
    connected = {
        edge.target_port_key for edge in context.incident_edges(node.node_id) if edge.target_node_id == node.node_id
    }
    locked = [key for key in keys if key in exposed_inputs and key in connected]
    if (
        node.type_id == MEDIA_PANEL_TYPE_ID
        and "source" in keys
        and "source" not in locked
        and bool(node.exposed_ports.get("source", True))
    ):
        locked.append("source")
    return locked


def _validated_property_updates(
    context: AutomationContext,
    op: str,
    node: NodeInstance,
    spec: NodeTypeSpec,
    values: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Check keys and port locks without mutating; return ``(plain, sensitive)`` property updates."""
    items = {str(key): value for key, value in values.items()}
    keys = list(items)
    spec_props = {prop.key: prop for prop in spec.properties}
    unknown = sorted(key for key in keys if key not in spec_props and key != "title")
    if unknown:
        raise _invalid(
            op,
            [f"properties.{key}: unknown property for {node.type_id}" for key in unknown],
            node_id=node.node_id,
            available=sorted(spec_props),
        )
    locked = _port_locked_property_keys(context, node, keys)
    if locked:
        raise AutomationOpError(
            PROPERTY_LOCKED_BY_PORT,
            f"Properties {locked} on node '{node.node_id}' are driven by a connected or exposed input port.",
            details={"node_id": node.node_id, "keys": locked},
        )
    plain: dict[str, Any] = {}
    sensitive: dict[str, Any] = {}
    for key, value in items.items():
        prop = spec_props.get(key)
        (sensitive if prop is not None and bool(prop.sensitive) else plain)[key] = value
    return plain, sensitive


def _ineligible_state_reasons(spec: NodeTypeSpec, node: NodeInstance, params: Mapping[str, Any]) -> list[str]:
    """collapsed / locked requests the owner would silently ignore for this node type."""
    reasons: list[str] = []
    if "collapsed" in params and bool(params["collapsed"]) != bool(node.collapsed) and not spec.collapsible:
        reasons.append(f"{node.type_id} is not collapsible")
    if "locked" in params and bool(params["locked"]) != bool(node.locked) and not str(node.type_id).startswith("passive."):
        reasons.append("only passive.* nodes can be locked")
    return reasons


def _stage_inline_html(context: AutomationContext, html: str) -> str:
    session = context.project_session
    if session is None:
        root = Path(tempfile.gettempdir()) / "corex_automation"
    else:
        root = Path(session.ensure_project_staging_root()) / _INLINE_HTML_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{uuid.uuid4().hex}.html"
    target.write_text(html, encoding="utf-8")
    return target.resolve().as_uri()


def _fragment_id_map(
    context: AutomationContext,
    fragment: Mapping[str, Any],
    new_ids: list[str],
    offset_x: float,
    offset_y: float,
) -> dict[str, str]:
    """original id -> pasted id; insertion order equals fragment order, verified by type, else matched by geometry."""
    entries = [entry for entry in fragment.get("nodes", []) if isinstance(entry, Mapping)]
    workspace = context.active_workspace()
    new_set = set(new_ids)
    ordered = [node_id for node_id in context.selected_node_ids() if node_id in new_set]
    if len(ordered) == len(entries) == len(new_ids):
        candidate = {str(entry.get("ref_id") or ""): new_id for entry, new_id in zip(entries, ordered)}
        if all(
            workspace.nodes[new_id].type_id == str(entry.get("type_id") or "")
            for entry, new_id in zip(entries, ordered)
        ):
            return candidate
    id_map: dict[str, str] = {}
    remaining = list(new_ids)
    for entry in entries:
        ref_id = str(entry.get("ref_id") or "")
        expected_x = float(entry.get("x", 0.0)) + offset_x
        expected_y = float(entry.get("y", 0.0)) + offset_y
        expected_type = str(entry.get("type_id") or "")
        for new_id in remaining:
            candidate_node = workspace.nodes[new_id]
            if (
                candidate_node.type_id == expected_type
                and abs(float(candidate_node.x) - expected_x) < 1e-3
                and abs(float(candidate_node.y) - expected_y) < 1e-3
            ):
                id_map[ref_id] = new_id
                remaining.remove(new_id)
                break
    return id_map


# ----------------------------------------------------------------- handlers


def add_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    node = _create_node(
        context,
        "node.add",
        type_id=str(params["type_id"]),
        params=params,
        properties=params.get("properties"),
    )
    return {"node_id": node.node_id, "node": context.node_summary(node)}


def add_text_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "node.add_text"
    spec = context.spec_for(PASSIVE_ANNOTATION_TEXT_TYPE_ID)
    keys = {prop.key for prop in spec.properties}
    content_key = "text" if "text" in keys else "body"
    properties: dict[str, Any] = {
        content_key: str(params["markdown"]),
        rich_text_format_property_key(content_key): str(params.get("format") or "markdown"),
    }
    properties.update(_text_style_properties(content_key, params.get("style"), op=op))
    node = _create_node(context, op, type_id=spec.type_id, params=params, properties=properties)
    return {"node_id": node.node_id, "node": context.node_summary(node), "content_key": content_key}


def add_media_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "node.add_media"
    source = Path(str(params["path"])).expanduser()
    if not source.is_file():
        raise _invalid(op, [f"path: '{params['path']}' is not an existing file"])
    resolved = source.resolve()
    spec = context.spec_for(MEDIA_PANEL_TYPE_ID)
    properties: dict[str, Any] = {key: params[key] for key in _MEDIA_PASSTHROUGH_KEYS if key in params}
    fit_modes = next((tuple(prop.enum_values) for prop in spec.properties if prop.key == "fit_mode"), ())
    if "fit_mode" in properties and str(properties["fit_mode"]) not in fit_modes:
        raise _invalid(op, [f"fit_mode: must be one of {list(fit_modes)}"])
    session = context.project_session
    staged: dict[str, str] = {}
    after_create = None
    if session is None:
        # Shell-free harness: no project artifact store, keep the absolute path.
        properties["source"] = str(resolved)
    else:
        kind = media_kind_from_source(str(resolved)) or "media"

        def after_create(node: NodeInstance, mutations: Any) -> bool | None:  # noqa: ANN401 - owner-typed callback
            ref = session.stage_node_artifact_file(
                resolved,
                artifact_prefix=f"{kind}_source",
                io_dir=PROJECT_NODE_INPUTS_DIRNAME,
                subdirectory="media",
                filename=resolved.name,
                node_id=node.node_id,
                node_title=node.title,
                node_type=str(spec.display_name),
            )
            if not ref:
                return False  # the scene rolls the node back
            staged["ref"] = str(ref)
            mutations.set_node_properties(node.node_id, {"source": str(ref)})
            return None

    try:
        # Like canvas import, an authored media source starts with its input port
        # unexposed; an exposed source port makes the property port-driven.
        node = _create_node(
            context,
            op,
            type_id=spec.type_id,
            params=params,
            properties=properties,
            exposed_port_overrides={"source": False},
            after_create=after_create,
        )
    except AutomationOpError as exc:
        if session is not None and exc.code == NO_EFFECT and "ref" not in staged:
            raise no_effect(op, "staging the media file into the project failed", details={"path": str(resolved)}) from exc
        raise
    artifact_ref = staged.get("ref", "")
    stored = str(node.properties.get("source") or "")
    if session is not None and stored != artifact_ref:
        raise no_effect(op, "the staged media reference was not applied", details={"node_id": node.node_id, "source": stored})
    return {
        "node_id": node.node_id,
        "node": context.node_summary(node),
        "artifact_ref": artifact_ref,
        "source": stored,
    }


def add_web_panel_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "node.add_web_panel"
    url = str(params.get("url") or "").strip()
    html = params.get("html")
    has_html = html is not None
    if bool(url) == has_html:
        raise _invalid(op, ["provide exactly one of url or html"])
    if has_html and not str(html).strip():
        raise _invalid(op, ["html: must not be empty"])
    properties: dict[str, Any] = {}
    display_mode = params.get("display_mode")
    if display_mode is not None:
        normalized_mode = str(display_mode).strip().lower()
        if normalized_mode not in WEB_PAGE_VIEWER_DISPLAY_MODES:
            raise _invalid(op, [f"display_mode: must be one of {list(WEB_PAGE_VIEWER_DISPLAY_MODES)}"])
        properties[WEB_PAGE_VIEWER_DISPLAY_MODE_PROPERTY] = normalized_mode
    if has_html:
        url = _stage_inline_html(context, str(html))
    properties[WEB_PAGE_VIEWER_START_LOCATION_PROPERTY] = url
    node = _create_node(context, op, type_id=WEB_PAGE_VIEWER_TYPE_ID, params=params, properties=properties)
    stored = str(node.properties.get(WEB_PAGE_VIEWER_START_LOCATION_PROPERTY) or "")
    if stored != url:
        raise no_effect(op, "start_location was not applied", details={"node_id": node.node_id, "url": url, "stored": stored})
    return {"node_id": node.node_id, "node": context.node_summary(node), "url": url}


def update_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "node.update"
    node = context.require_node(str(params["node_id"]))
    requested = [field for field in _UPDATE_FIELDS if field in params]
    if not requested:
        raise _invalid(op, [f"provide at least one field to change: {', '.join(_UPDATE_FIELDS)}"])
    spec = instance_spec(context, node) or context.spec_for(node)
    node_id = node.node_id

    # Validate every requested field before the first scene mutation: a rejected
    # update leaves the node untouched and records no undo entry.
    title: str | None = None
    if "title" in params:
        title = str(params["title"]).strip()
        if not title:
            raise _invalid(op, ["title: must not be blank"])
    moves = "x" in params or "y" in params
    resizes = "width" in params or "height" in params
    if moves or resizes:
        context.require_node_in_scope(node_id)
    explicit_properties = dict(params.get("properties") or {})
    plain_properties: dict[str, Any] = {}
    sensitive_properties: dict[str, Any] = {}
    if params.get("properties") is not None:
        plain_properties, sensitive_properties = _validated_property_updates(context, op, node, spec, explicit_properties)
    if title is not None and "body" not in explicit_properties and _body_follows_title(spec, node):
        # Shape-label flowchart types show body in the shape; keep it in step with the title.
        plain_properties["body"] = title
    port_label_updates = [
        (_require_effective_port(context, node, raw_key), "" if label is None else str(label))
        for raw_key, label in dict(params.get("port_labels") or {}).items()
    ]
    exposed_port_updates = [
        (_require_effective_port(context, node, raw_key), bool(flag))
        for raw_key, flag in dict(params.get("exposed_ports") or {}).items()
    ]
    ineligible = _ineligible_state_reasons(spec, node, params)
    if ineligible:
        raise no_effect(
            op,
            "; ".join(ineligible),
            details={"node_id": node_id, "requested": requested, "reasons": ineligible},
        )

    scene = context.scene
    before = _node_state(context, node)
    if title is not None:
        # set_node_title writes node.title and, for property-backed families, properties["title"].
        scene.set_node_title(node_id, title)
    if moves:
        scene.move_node(node_id, float(params.get("x", node.x)), float(params.get("y", node.y)))
    if resizes:
        width = float(params.get("width", before["width"] or 0.0))
        height = float(params.get("height", before["height"] or 0.0))
        scene.resize_node(node_id, width, height)
    for key, value in sensitive_properties.items():
        scene.set_node_secret(node_id, key, str(value))
    if plain_properties:
        scene.set_node_properties(node_id, plain_properties)
    for key, label in port_label_updates:
        scene.set_node_port_label(node_id, key, label)
    for key, flag in exposed_port_updates:
        scene.set_exposed_port(node_id, key, flag)
    if "collapsed" in params:
        scene.set_node_collapsed(node_id, bool(params["collapsed"]))
    if "locked" in params:
        scene.set_node_locked(node_id, bool(params["locked"]))
    node = context.require_node(node_id)
    after = _node_state(context, node)
    changed = _changed_fields(before, after)
    if not changed:
        raise no_effect(
            op,
            "none of the requested fields changed",
            details={
                "node_id": node_id,
                "requested": requested,
                "reasons": ["every requested value already matched the node state"],
            },
        )
    return {"node_id": node_id, "changed": changed, "node": context.node_summary(node)}


def set_node_style(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "node.set_style"
    node = context.require_node(str(params["node_id"]))
    context.require_passive(node)
    style = params.get("style")
    preset = str(params.get("preset") or "").strip()
    replace = bool(params.get("replace", False))
    clear = bool(params.get("clear", False))
    propagate = bool(params.get("propagate", False))
    if style is None and not preset and not clear and not propagate:
        raise _invalid(op, ["provide style, preset, clear=true, or propagate=true"])
    if clear and (style is not None or preset):
        raise _invalid(op, ["clear=true cannot be combined with style or preset"])
    scene = context.scene
    node_id = node.node_id
    before = copy.deepcopy(node.visual_style)
    own_changed = False
    if clear:
        if before:
            scene.clear_node_visual_style(node_id)
            if node.visual_style:
                raise no_effect(op, "the style override was not cleared", details={"node_id": node_id, "visual_style": json_safe(node.visual_style)})
            own_changed = True
    else:
        payload: dict[str, Any] = {}
        if preset:
            payload.update(normalize_passive_node_style_payload(lookup_style_preset(context, "node", preset).get("style")))
        if style is not None:
            payload.update(_normalize_node_style(style, op=op))
        if payload or (replace and style is not None):
            target = normalize_passive_node_style_payload(dict(payload) if replace else {**before, **payload})
            if target != before:
                scene.set_node_visual_style(node_id, target)
                if node.visual_style != target:
                    raise no_effect(
                        op,
                        "the scene did not apply the style",
                        details={"node_id": node_id, "expected": target, "actual": json_safe(node.visual_style)},
                    )
                own_changed = True
    propagated: list[str] = []
    if propagate:
        workspace = context.active_workspace()
        snapshot = {
            other_id: copy.deepcopy(other.visual_style) for other_id, other in workspace.nodes.items() if other_id != node_id
        }
        scene.propagate_passive_node_style(node_id)
        propagated = sorted(
            other_id
            for other_id, previous in snapshot.items()
            if other_id in workspace.nodes and workspace.nodes[other_id].visual_style != previous
        )
    if not own_changed and not propagated:
        if clear:
            reason = "the node has no style override to clear"
        elif propagate and style is None and not preset:
            reason = "no connected passive node needed this style"
        else:
            reason = "the node already had exactly this style"
        raise no_effect(op, reason, details={"node_id": node_id, "visual_style": json_safe(node.visual_style)})
    return {"node_id": node_id, "visual_style": json_safe(node.visual_style), "propagated_to": propagated}


def delete_nodes(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "node.delete"
    node_ids = _unique_ids(params["node_ids"])
    if not node_ids:
        raise _invalid(op, ["node_ids: must contain at least one id"])
    context.require_nodes(node_ids)
    workspace = context.active_workspace()
    before_nodes = set(workspace.nodes)
    before_edges = set(workspace.edges)
    for node_id in node_ids:
        if node_id not in workspace.nodes:
            continue  # already removed as part of an earlier node's subtree
        context.scene.remove_workspace_node(node_id)
        if node_id in workspace.nodes:
            raise no_effect(op, f"node '{node_id}' was not removed", details={"node_id": node_id})
    removed = before_nodes - set(workspace.nodes)
    deleted = [*node_ids, *sorted(removed - set(node_ids))]
    return {
        "deleted_node_ids": deleted,
        "removed_edge_ids": sorted(before_edges - set(workspace.edges)),
    }


def duplicate_nodes(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "node.duplicate"
    node_ids = _unique_ids(params["node_ids"])
    if not node_ids:
        raise _invalid(op, ["node_ids: must contain at least one id"])
    for node in context.require_nodes(node_ids):
        context.require_node_in_scope(node.node_id)
    offset_x = float(params.get("offset_x", 40.0))
    offset_y = float(params.get("offset_y", 40.0))
    scene = context.scene
    with context.with_selection(node_ids):
        unselectable = sorted(set(node_ids) - set(context.selected_node_ids()))
        fragment = scene.serialize_selected_subgraph_fragment()
    if unselectable:
        # Locked passive nodes are skipped by select_node unless the user enabled
        # "interact with locked objects"; refuse rather than duplicate a subset.
        raise no_effect(
            op,
            "some nodes cannot be selected for duplication (locked nodes must be unlocked first)",
            details={"node_ids": node_ids, "unselectable": unselectable},
        )
    if not fragment:
        raise no_effect(op, "the selection produced no fragment", details={"node_ids": node_ids})
    center = scene.fragment_bounds_center(fragment)
    if center is None:
        raise no_effect(op, "the fragment has no bounds", details={"node_ids": node_ids})
    before_ids = context.node_id_set()
    pasted = scene.paste_subgraph_fragment(fragment, float(center[0]) + offset_x, float(center[1]) + offset_y)
    new_ids = context.new_ids_since(before_ids)
    if not pasted or not new_ids:
        raise no_effect(op, "the fragment was not pasted", details={"node_ids": node_ids})
    id_map = _fragment_id_map(context, fragment, new_ids, offset_x, offset_y)
    return {
        "node_ids": [id_map.get(node_id, "") for node_id in node_ids],
        "id_map": id_map,
        "new_node_ids": new_ids,
    }


HANDLERS = {
    'node.add': add_node,
    'node.add_text': add_text_node,
    'node.add_media': add_media_node,
    'node.add_web_panel': add_web_panel_node,
    'node.update': update_node,
    'node.set_style': set_node_style,
    'node.delete': delete_nodes,
    'node.duplicate': duplicate_nodes,
}

__all__ = ["HANDLERS"]
