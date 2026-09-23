# Purpose: Read-only graph automation handlers: snapshot, node detail, search (T05); also the shared port/property read helpers.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_nodes.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from ea_node_editor.automation.errors import WRONG_WORKSPACE, AutomationOpError
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.graph.effective_ports import EffectivePort, effective_ports
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec
from ea_node_editor.ui.shell.automation.context import AutomationContext

# ----------------------------------------------------------------- shared helpers
# These are imported by handlers/nodes.py and handlers/catalog.py; they only read
# owner state (registry specs, effective ports, workspace edges).


def json_safe(value: Any) -> Any:
    """Return a JSON-serialisable copy (protected values and odd types become strings)."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(item) for item in value]
    return str(value)


def instance_spec(context: AutomationContext, node: NodeInstance) -> NodeTypeSpec | None:
    """The instance-resolved spec (dynamic ports/properties applied) or ``None`` for unknown types."""
    base = context.registry.spec_or_none(node.type_id)
    if base is None:
        return None
    try:
        return context.registry.resolve_spec(node.type_id, node.properties)
    except Exception:  # noqa: BLE001 - fall back to the declared spec when instance resolution rejects the properties
        return base


def effective_port_records(context: AutomationContext, node: NodeInstance) -> tuple[EffectivePort, ...]:
    spec = instance_spec(context, node)
    if spec is None:
        return ()
    workspace = context.active_workspace()
    return effective_ports(node=node, spec=spec, workspace_nodes=workspace.nodes)


def port_summary(port: EffectivePort | PortSpec, connected_edge_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "key": str(port.key),
        "direction": str(port.direction),
        "kind": str(port.kind),
        "data_type": str(port.data_type),
        "label": str(port.label or port.key),
        "side": str(port.side or ""),
        "required": bool(port.required),
        "exposed": bool(port.exposed),
        "allow_multiple_connections": bool(port.allow_multiple_connections),
        "uses_property_default": bool(port.uses_property_default),
        "description": str(port.description or ""),
        "connected_edge_ids": [str(edge_id) for edge_id in (connected_edge_ids or [])],
    }


def port_summaries(context: AutomationContext, node: NodeInstance) -> list[dict[str, Any]]:
    """Effective ports of ``node`` with the ids of the edges attached to each port."""
    edges = context.incident_edges(node.node_id)
    summaries: list[dict[str, Any]] = []
    for port in effective_port_records(context, node):
        connected = [
            edge.edge_id
            for edge in edges
            if (edge.source_node_id == node.node_id and edge.source_port_key == port.key)
            or (edge.target_node_id == node.node_id and edge.target_port_key == port.key)
        ]
        summaries.append(port_summary(port, connected))
    return summaries


def exposed_port_map(context: AutomationContext, node: NodeInstance) -> dict[str, bool]:
    return {str(port.key): bool(port.exposed) for port in effective_port_records(context, node)}


def node_detail_summary(
    context: AutomationContext,
    node: NodeInstance,
    *,
    include_style: bool = False,
    include_properties: bool = False,
) -> dict[str, Any]:
    summary = context.node_summary(node)
    if include_style:
        summary["visual_style"] = json_safe(node.visual_style)
    if include_properties:
        summary["properties"] = json_safe(node.properties)
    return summary


def _display_name(context: AutomationContext, node: NodeInstance) -> str:
    spec = context.registry.spec_or_none(node.type_id)
    return str(spec.display_name) if spec is not None else ""


# --------------------------------------------------------------------- handlers


def get_graph(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    requested = str(params.get("workspace_id") or "").strip()
    active_id = context.workspace_id()
    if requested and requested != active_id:
        raise AutomationOpError(
            WRONG_WORKSPACE,
            f"Workspace '{requested}' is not the active workspace ('{active_id}').",
            details={
                "workspace_id": requested,
                "active_workspace_id": active_id,
                "available": list(context.model.project.workspaces),
            },
        )
    workspace = context.active_workspace()
    scope = str(params.get("scope") or "active")
    include_style = bool(params.get("include_style", False))
    include_properties = bool(params.get("include_properties", False))
    nodes = [node for node in workspace.nodes.values() if scope == "all" or context.in_active_scope(node)]
    node_ids = {node.node_id for node in nodes}
    edges = [
        edge
        for edge in workspace.edges.values()
        if scope == "all" or (edge.source_node_id in node_ids and edge.target_node_id in node_ids)
    ]
    edge_rows: list[dict[str, Any]] = []
    for edge in edges:
        row = context.edge_summary(edge)
        if include_style:
            row["visual_style"] = json_safe(edge.visual_style)
        edge_rows.append(row)
    return {
        "workspace_id": workspace.workspace_id,
        "workspace_name": str(workspace.name),
        "dirty": bool(workspace.dirty),
        "scope": scope,
        "scope_path": context.scope_path(),
        "active_view_id": str(workspace.active_view_id or ""),
        "views": [
            {
                "view_id": str(view.view_id),
                "name": str(view.name),
                "active": str(view.view_id) == str(workspace.active_view_id),
            }
            for view in workspace.views.values()
        ],
        "nodes": [
            node_detail_summary(context, node, include_style=include_style, include_properties=include_properties)
            for node in nodes
        ],
        "edges": edge_rows,
        "selected_node_ids": context.selected_node_ids(),
    }


def get_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    node = context.require_node(str(params["node_id"]))
    spec = context.registry.spec_or_none(node.type_id)
    return {
        "node": context.node_summary(node),
        "display_name": str(spec.display_name) if spec is not None else "",
        "properties": json_safe(node.properties),
        "visual_style": json_safe(node.visual_style),
        "port_labels": {str(key): str(value) for key, value in node.port_labels.items()},
        "exposed_ports": exposed_port_map(context, node),
        "ports": port_summaries(context, node),
        "incident_edges": [context.edge_summary(edge) for edge in context.incident_edges(node.node_id)],
        "links": [json_safe(asdict(link)) for link in node.links],
        "comments": [json_safe(asdict(comment)) for comment in node.comments],
        "in_active_scope": context.in_active_scope(node),
        "custom_width": float(node.custom_width) if node.custom_width is not None else None,
        "custom_height": float(node.custom_height) if node.custom_height is not None else None,
    }


def find_nodes(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    workspace = context.active_workspace()
    query = str(params.get("query") or "").strip().lower()
    type_id = str(params.get("type_id") or "").strip()
    title = params.get("title")
    title_contains = str(params.get("title_contains") or "").strip().lower()
    scope = str(params.get("scope") or "all")
    limit = int(params.get("limit") or 100)
    matches: list[NodeInstance] = []
    for node in workspace.nodes.values():
        if scope == "active" and not context.in_active_scope(node):
            continue
        if type_id and node.type_id != type_id:
            continue
        if title is not None and node.title != str(title):
            continue
        if title_contains and title_contains not in node.title.lower():
            continue
        if query:
            haystack = " ".join((node.title, node.type_id, _display_name(context, node))).lower()
            if query not in haystack:
                continue
        matches.append(node)
    return {
        "nodes": [context.node_summary(node) for node in matches[:limit]],
        "total": len(matches),
    }


HANDLERS = {
    'graph.get': get_graph,
    'graph.get_node': get_node,
    'graph.find_nodes': find_nodes,
}

__all__ = [
    "HANDLERS",
    "effective_port_records",
    "exposed_port_map",
    "instance_spec",
    "json_safe",
    "node_detail_summary",
    "port_summaries",
    "port_summary",
]
