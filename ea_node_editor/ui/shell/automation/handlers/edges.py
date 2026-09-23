# Purpose: Edge automation handlers: connect (compatibility, capacity, replace), update (label/style/path/display/enabled), delete.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_structure.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import (
    INVALID_PARAMS,
    NOT_FOUND,
    PORT_INCOMPATIBLE,
    WRONG_SCOPE,
    AutomationOpError,
    invalid_params,
    no_effect,
)
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.graph.effective_ports import (
    effective_ports,
    find_port,
    is_flow_edge_port,
    port_supports_incoming_edge,
    port_supports_outgoing_edge,
)
from ea_node_editor.graph.records import EdgeInstance, NodeInstance
from ea_node_editor.graph.type_forwarding import GraphTypeResolver
from ea_node_editor.passive_style_normalization import normalize_flow_edge_style_payload
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui.shell.automation.handlers.catalog import EDGE_STYLE_ALIASES, EDGE_STYLE_KEYS

EDGE_DISPLAY_MODES = ("default", "faint", "hidden")
_UPDATE_VALUE_FIELDS = ("label", "style", "path_mode", "enabled", "display_mode")


# ----------------------------------------------------------------- helpers


def _resolve_port(context: AutomationContext, node: NodeInstance, port_key: Any) -> Any:
    """Return the effective port (static, dynamic, or subnode-derived) or raise NOT_FOUND listing the keys."""
    key = str(port_key or "").strip()
    workspace = context.active_workspace()
    spec = context.spec_for(node)
    port = find_port(node=node, spec=spec, workspace_nodes=workspace.nodes, port_key=key)
    if port is not None:
        return port
    available = [item.key for item in effective_ports(node=node, spec=spec, workspace_nodes=workspace.nodes)]
    raise AutomationOpError(
        NOT_FOUND,
        f"Port '{key}' does not exist on node '{node.node_id}' ({node.type_id}).",
        hint="Use one of the listed port keys; passive flow nodes expose top|right|bottom|left.",
        details={"node_id": node.node_id, "port": key, "available": available},
    )


def _incompatibility_reason(
    context: AutomationContext,
    source: NodeInstance,
    source_port: Any,
    target: NodeInstance,
    target_port: Any,
) -> str:
    if source.node_id == target.node_id and is_flow_edge_port(source_port) and is_flow_edge_port(target_port):
        return "same_node_flow_edge"
    if not port_supports_outgoing_edge(source_port):
        return "source_port_not_output"
    if not port_supports_incoming_edge(target_port):
        return "target_port_not_input"
    if not bool(source_port.exposed):
        return "source_port_hidden"
    if not bool(target_port.exposed):
        return "target_port_hidden"
    workspace = context.active_workspace()
    resolver = GraphTypeResolver(
        registry=context.registry,
        workspace_nodes=workspace.nodes,
        workspace_edges=workspace.edges.values(),
    )
    compatibility = resolver.compatibility(source.node_id, source_port.key, target_port)
    if compatibility.is_compatible:
        return "rejected_by_policy"
    worst = compatibility.worst_match
    return f"{worst.status}:{worst.reason_code}"


def _incoming_edges(context: AutomationContext, node_id: str, port_key: str) -> list[EdgeInstance]:
    workspace = context.active_workspace()
    return [
        edge
        for edge in workspace.edges.values()
        if edge.target_node_id == node_id and edge.target_port_key == port_key
    ]


def _checked_style(style: Any, *, op: str) -> dict[str, Any]:
    """Map agent aliases onto persisted keys; unknown keys -> INVALID_PARAMS naming the accepted keys."""
    if not isinstance(style, Mapping):
        raise invalid_params(["params.style: must be an object"], op=op)
    mapped = {EDGE_STYLE_ALIASES.get(str(key), str(key)): value for key, value in style.items()}
    unknown = sorted(str(key) for key in style if EDGE_STYLE_ALIASES.get(str(key), str(key)) not in EDGE_STYLE_KEYS)
    if unknown:
        accepted = ", ".join((*EDGE_STYLE_KEYS, *EDGE_STYLE_ALIASES))
        error = invalid_params([f"style.{key}: unknown edge style key (accepted: {accepted})" for key in unknown], op=op)
        error.details.update({"unknown": unknown, "available": list(EDGE_STYLE_KEYS), "aliases": dict(EDGE_STYLE_ALIASES)})
        raise error
    return mapped


def _persisted_style(style: Mapping[str, Any]) -> dict[str, Any]:
    """Normalise persisted-key style values and keep a non-default display_mode."""
    mapped = dict(style)
    display_mode = str(mapped.pop("display_mode", "") or "").strip().lower()
    normalized = normalize_flow_edge_style_payload(mapped)
    if display_mode in EDGE_DISPLAY_MODES and display_mode != "default":
        normalized["display_mode"] = display_mode
    return normalized


def _edge_state(edge: EdgeInstance) -> dict[str, Any]:
    return {"label": edge.label, "enabled": bool(edge.enabled), "visual_style": dict(edge.visual_style)}


def _changed_fields(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    changed: list[str] = []
    if before["label"] != after["label"]:
        changed.append("label")
    before_style = dict(before["visual_style"])
    after_style = dict(after["visual_style"])
    display_changed = before_style.pop("display_mode", "default") != after_style.pop("display_mode", "default")
    path_changed = before_style.pop("path_mode", "auto") != after_style.pop("path_mode", "auto")
    if before_style != after_style:
        changed.append("style")
    if path_changed:
        changed.append("path_mode")
    if display_changed:
        changed.append("display_mode")
    if before["enabled"] != after["enabled"]:
        changed.append("enabled")
    return changed


def _endpoint_labels(source: NodeInstance, source_key: str, target: NodeInstance, target_key: str) -> dict[str, Any]:
    return {
        "source_node_id": source.node_id,
        "source_port": source_key,
        "target_node_id": target.node_id,
        "target_port": target_key,
    }


def _edge_result(context: AutomationContext, edge: EdgeInstance) -> dict[str, Any]:
    return {"edge_id": edge.edge_id, "edge": context.edge_summary(edge), "style": dict(edge.visual_style)}


# ---------------------------------------------------------------- handlers


def connect_edge(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    source = context.require_node_in_scope(str(params["source_node_id"]))
    target = context.require_node_in_scope(str(params["target_node_id"]))
    source_port = _resolve_port(context, source, params["source_port"])
    target_port = _resolve_port(context, target, params["target_port"])
    replace_existing = bool(params.get("replace_existing", False))
    endpoints = _endpoint_labels(source, source_port.key, target, target_port.key)
    style = params.get("style")
    # Checked before the edge exists so a bad style key never leaves a half-configured edge.
    persisted_style = _persisted_style(_checked_style(style, op="edge.connect")) if style else {}
    scene = context.scene

    if not scene.are_ports_compatible(source.node_id, source_port.key, target.node_id, target_port.key):
        reason = _incompatibility_reason(context, source_port=source_port, source=source, target=target, target_port=target_port)
        raise AutomationOpError(
            PORT_INCOMPATIBLE,
            f"Cannot connect {source.node_id}.{source_port.key} -> {target.node_id}.{target_port.key}: {reason}.",
            details={"reason": reason, **endpoints},
        )

    occupying = _incoming_edges(context, target.node_id, target_port.key)
    duplicate = next(
        (
            edge
            for edge in occupying
            if edge.source_node_id == source.node_id and edge.source_port_key == source_port.key
        ),
        None,
    )
    if duplicate is not None:
        raise no_effect(
            "edge.connect",
            f"an identical edge already exists ({duplicate.edge_id})",
            details={"edge_id": duplicate.edge_id, **endpoints},
        )
    allow_multiple = bool(target_port.allow_multiple_connections)
    if occupying and not allow_multiple and not replace_existing:
        raise AutomationOpError(
            PORT_INCOMPATIBLE,
            f"Target port {target.node_id}.{target_port.key} accepts one connection and is already connected.",
            hint="Pass replace_existing=true to rewire the occupied input, or pick another input port.",
            details={
                "reason": "target_port_occupied",
                "occupied_by": [edge.edge_id for edge in occupying],
                **endpoints,
            },
        )

    # append keeps sibling edges on multi-connection inputs; the owner replaces every
    # edge on the target port when append is off, which is exactly replace_existing.
    append_requested = (not replace_existing) and allow_multiple
    before_edge_ids = set(context.active_workspace().edges)
    try:
        edge_id = str(
            scene.add_edge(source.node_id, source_port.key, target.node_id, target_port.key, append_requested) or ""
        ).strip()
    except (KeyError, ValueError) as exc:
        raise AutomationOpError(
            PORT_INCOMPATIBLE,
            f"COREX rejected the connection: {exc}",
            details={"reason": str(exc), **endpoints},
        ) from exc
    edge = context.edge_or_none(edge_id)
    if edge is None or edge_id in before_edge_ids:
        raise no_effect("edge.connect", "the graph did not add a new edge", details={"edge_id": edge_id, **endpoints})
    replaced_edge_ids = sorted(before_edge_ids - set(context.active_workspace().edges))

    label = params.get("label")
    if label is not None and str(label).strip():
        scene.set_edge_label(edge_id, str(label))
    if persisted_style:
        scene.set_edge_visual_style(edge_id, persisted_style)

    edge = context.require_edge(edge_id)
    return {**_edge_result(context, edge), "replaced_edge_ids": replaced_edge_ids}


def update_edge(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    edge = context.require_edge(str(params["edge_id"]))
    edge_id = edge.edge_id
    clear_style = bool(params.get("clear_style", False))
    clear_label = bool(params.get("clear_label", False))
    supplied = [field for field in _UPDATE_VALUE_FIELDS if params.get(field) is not None]
    if not supplied and not clear_style and not clear_label:
        raise AutomationOpError(
            INVALID_PARAMS,
            "edge.update needs at least one of label, style, path_mode, enabled, display_mode, clear_style, clear_label.",
            details={"edge_id": edge_id, "problems": ["no update field supplied"]},
        )
    style = params.get("style")
    checked_style = _checked_style(style, op="edge.update") if style is not None else None
    before = _edge_state(edge)
    scene = context.scene

    if clear_label:
        scene.clear_edge_label(edge_id)
    label = params.get("label")
    if label is not None:
        scene.set_edge_label(edge_id, str(label))

    path_mode = params.get("path_mode")
    if clear_style or checked_style is not None or path_mode is not None:
        merged: dict[str, Any] = {} if clear_style else dict(edge.visual_style)
        if checked_style:
            merged.update(checked_style)
        if path_mode is not None:
            merged["path_mode"] = str(path_mode)
        persisted = _persisted_style(merged)
        if persisted != dict(edge.visual_style):
            scene.set_edge_visual_style(edge_id, persisted)

    display_mode = params.get("display_mode")
    if display_mode is not None:
        scene.set_edges_display_mode([edge_id], str(display_mode))

    enabled = params.get("enabled")
    if enabled is not None:
        scene.set_edge_enabled(edge_id, bool(enabled))

    edge_after = context.edge_or_none(edge_id)
    if edge_after is None:
        raise no_effect("edge.update", "the edge no longer exists after the update", details={"edge_id": edge_id})
    changed = _changed_fields(before, _edge_state(edge_after))
    if not changed:
        raise no_effect(
            "edge.update",
            "every requested value already matched the edge",
            details={"edge_id": edge_id, "requested": supplied + [flag for flag in ("clear_style", "clear_label") if params.get(flag)]},
        )
    return {**_edge_result(context, edge_after), "changed": changed}


def delete_edges(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    edge_ids: list[str] = []
    for value in params["edge_ids"]:
        edge_id = str(value or "").strip()
        if edge_id and edge_id not in edge_ids:
            edge_ids.append(edge_id)
    edges = [context.require_edge(edge_id) for edge_id in edge_ids]
    for edge in edges:
        for node_id in (edge.source_node_id, edge.target_node_id):
            node = context.require_node(node_id)
            if not context.in_active_scope(node):
                raise AutomationOpError(
                    WRONG_SCOPE,
                    f"Edge '{edge.edge_id}' touches node '{node_id}' outside the open scope.",
                    details={"edge_id": edge.edge_id, "node_id": node_id, "scope_path": context.scope_path()},
                )
    before_edge_ids = set(context.active_workspace().edges)
    for edge in edges:
        if context.edge_or_none(edge.edge_id) is not None:
            context.scene.remove_edge(edge.edge_id)
    remaining = [edge_id for edge_id in edge_ids if context.edge_or_none(edge_id) is not None]
    if remaining:
        raise no_effect("edge.delete", "the scene kept some edges", details={"remaining_edge_ids": remaining})
    cascaded = sorted(before_edge_ids - set(context.active_workspace().edges) - set(edge_ids))
    return {"deleted_edge_ids": [*edge_ids, *cascaded]}


HANDLERS = {
    'edge.connect': connect_edge,
    'edge.update': update_edge,
    'edge.delete': delete_edges,
}

__all__ = ["EDGE_DISPLAY_MODES", "HANDLERS"]
