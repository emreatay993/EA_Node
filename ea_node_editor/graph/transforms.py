from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Sequence

from ea_node_editor.graph.effective_ports import (
    effective_ports as resolve_effective_ports,
    find_port,
    is_subnode_pin_type,
)
from ea_node_editor.graph.hierarchy import normalize_scope_path, scope_parent_id, subtree_node_ids
from ea_node_editor.graph.model import EdgeInstance, GraphModel, WorkspaceData
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
    SUBNODE_PIN_KIND_PROPERTY,
    SUBNODE_PIN_KIND_VALUES,
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_PIN_PORT_KEY,
    SUBNODE_TYPE_ID,
)
from ea_node_editor.nodes.registry import NodeRegistry

_PIN_OFFSET_X = 220.0
_PIN_ROW_STEP = 70.0
_FLOW_KINDS = frozenset({"exec", "completed", "failed"})
_FRAGMENT_EXTERNAL_PARENT_PREFIX = "__ea_external_parent__:"


@dataclass(slots=True, frozen=True)
class GroupSubnodeResult:
    shell_node_id: str
    moved_node_ids: tuple[str, ...]
    created_pin_node_ids: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class UngroupSubnodeResult:
    removed_shell_node_id: str
    moved_node_ids: tuple[str, ...]
    removed_pin_node_ids: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class _BoundaryEdge:
    edge: EdgeInstance
    pin_type_id: str
    label: str
    kind: str
    data_type: str


def encode_fragment_external_parent_id(parent_node_id: object) -> str | None:
    normalized_parent_id = str(parent_node_id).strip()
    if not normalized_parent_id:
        return None
    return f"{_FRAGMENT_EXTERNAL_PARENT_PREFIX}{normalized_parent_id}"


def expand_subtree_fragment_node_ids(
    *,
    workspace: WorkspaceData,
    selected_node_ids: Sequence[object],
) -> list[str]:
    normalized_selected: list[str] = []
    seen_selected: set[str] = set()
    for value in selected_node_ids:
        node_id = str(value).strip()
        if not node_id or node_id in seen_selected:
            continue
        if node_id not in workspace.nodes:
            continue
        seen_selected.add(node_id)
        normalized_selected.append(node_id)

    expanded: list[str] = []
    seen_expanded: set[str] = set()
    for node_id in normalized_selected:
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        fragment_ids = [node_id]
        if node.type_id == SUBNODE_TYPE_ID:
            fragment_ids = subtree_node_ids(workspace, [node_id])
        for fragment_id in fragment_ids:
            if fragment_id in seen_expanded or fragment_id not in workspace.nodes:
                continue
            seen_expanded.add(fragment_id)
            expanded.append(fragment_id)
    return expanded


def build_subtree_fragment_payload_data(
    *,
    workspace: WorkspaceData,
    selected_node_ids: Sequence[object],
) -> dict[str, list[dict[str, Any]]] | None:
    fragment_node_ids = expand_subtree_fragment_node_ids(
        workspace=workspace,
        selected_node_ids=selected_node_ids,
    )
    if not fragment_node_ids:
        return None

    selected_node_set = set(fragment_node_ids)
    nodes_payload: list[dict[str, Any]] = []
    for node_id in fragment_node_ids:
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        nodes_payload.append(
            {
                "ref_id": node.node_id,
                "type_id": node.type_id,
                "title": node.title,
                "x": float(node.x),
                "y": float(node.y),
                "collapsed": bool(node.collapsed),
                "properties": copy.deepcopy(node.properties),
                "exposed_ports": dict(node.exposed_ports),
                "visual_style": copy.deepcopy(node.visual_style),
                "parent_node_id": node.parent_node_id,
                "custom_width": float(node.custom_width) if node.custom_width is not None else None,
                "custom_height": float(node.custom_height) if node.custom_height is not None else None,
            }
        )
    if not nodes_payload:
        return None

    edges_payload: list[dict[str, Any]] = []
    workspace_edges = sorted(
        workspace.edges.values(),
        key=lambda edge: edge.edge_id,
    )
    for edge in workspace_edges:
        if edge.source_node_id not in selected_node_set or edge.target_node_id not in selected_node_set:
            continue
        edges_payload.append(
            {
                "source_ref_id": edge.source_node_id,
                "source_port_key": edge.source_port_key,
                "target_ref_id": edge.target_node_id,
                "target_port_key": edge.target_port_key,
                "label": str(edge.label),
                "visual_style": copy.deepcopy(edge.visual_style),
            }
        )
    return {
        "nodes": nodes_payload,
        "edges": edges_payload,
    }


def build_subnode_custom_workflow_snapshot_data(
    *,
    workspace: WorkspaceData,
    registry: NodeRegistry,
    shell_node_id: object,
) -> dict[str, Any] | None:
    normalized_shell_node_id = str(shell_node_id).strip()
    if not normalized_shell_node_id:
        return None
    shell_node = workspace.nodes.get(normalized_shell_node_id)
    if shell_node is None or shell_node.type_id != SUBNODE_TYPE_ID:
        return None
    try:
        shell_spec = registry.get_spec(shell_node.type_id)
    except KeyError:
        return None

    fragment_payload = build_subtree_fragment_payload_data(
        workspace=workspace,
        selected_node_ids=[normalized_shell_node_id],
    )
    if fragment_payload is None:
        return None

    ports_payload: list[dict[str, Any]] = []
    for port in resolve_effective_ports(
        node=shell_node,
        spec=shell_spec,
        workspace_nodes=workspace.nodes,
    ):
        ports_payload.append(
            {
                "key": port.key,
                "label": port.label,
                "direction": port.direction,
                "kind": port.kind,
                "data_type": port.data_type,
                "exposed": bool(port.exposed),
            }
        )

    return {
        "ports": ports_payload,
        "fragment": fragment_payload,
    }


def insert_graph_fragment(
    *,
    model: GraphModel,
    workspace_id: str,
    fragment_payload: dict[str, Any],
    delta_x: float,
    delta_y: float,
) -> list[str]:
    workspace = model.project.workspaces.get(str(workspace_id).strip())
    if workspace is None:
        return []

    nodes_payload = fragment_payload.get("nodes")
    edges_payload = fragment_payload.get("edges")
    if not isinstance(nodes_payload, list) or not isinstance(edges_payload, list):
        return []

    node_id_map: dict[str, str] = {}
    inserted_node_ids: list[str] = []

    for node_payload in nodes_payload:
        if not isinstance(node_payload, dict):
            continue
        source_node_id = str(node_payload.get("ref_id", "")).strip()
        type_id = str(node_payload.get("type_id", "")).strip()
        if not source_node_id or not type_id:
            continue
        created = model.add_node(
            workspace.workspace_id,
            type_id=type_id,
            title=str(node_payload.get("title", "")),
            x=float(node_payload.get("x", 0.0)) + float(delta_x),
            y=float(node_payload.get("y", 0.0)) + float(delta_y),
            properties=dict(node_payload.get("properties", {})),
            exposed_ports=dict(node_payload.get("exposed_ports", {})),
            visual_style=copy.deepcopy(node_payload.get("visual_style", {})),
        )
        created.collapsed = bool(node_payload.get("collapsed", False))
        created.custom_width = (
            float(node_payload["custom_width"]) if node_payload.get("custom_width") is not None else None
        )
        created.custom_height = (
            float(node_payload["custom_height"]) if node_payload.get("custom_height") is not None else None
        )
        node_id_map[source_node_id] = created.node_id
        inserted_node_ids.append(created.node_id)

    if not inserted_node_ids:
        return []

    for node_payload in nodes_payload:
        if not isinstance(node_payload, dict):
            continue
        source_node_id = str(node_payload.get("ref_id", "")).strip()
        inserted_node_id = node_id_map.get(source_node_id)
        if not inserted_node_id:
            continue
        inserted_node = workspace.nodes.get(inserted_node_id)
        if inserted_node is None:
            continue
        inserted_node.parent_node_id = _remap_fragment_parent_id(
            source_parent_id=node_payload.get("parent_node_id"),
            node_id_map=node_id_map,
            workspace=workspace,
        )

    for edge_payload in edges_payload:
        if not isinstance(edge_payload, dict):
            continue
        source_ref_id = str(edge_payload.get("source_ref_id", "")).strip()
        target_ref_id = str(edge_payload.get("target_ref_id", "")).strip()
        source_port_key = str(edge_payload.get("source_port_key", "")).strip()
        target_port_key = str(edge_payload.get("target_port_key", "")).strip()
        if not source_ref_id or not target_ref_id or not source_port_key or not target_port_key:
            continue
        source_node_id = node_id_map.get(source_ref_id)
        target_node_id = node_id_map.get(target_ref_id)
        if not source_node_id or not target_node_id:
            continue
        source_port_key = _remap_fragment_edge_port_key(
            workspace=workspace,
            node_id_map=node_id_map,
            endpoint_node_id=source_node_id,
            port_key=source_port_key,
        )
        target_port_key = _remap_fragment_edge_port_key(
            workspace=workspace,
            node_id_map=node_id_map,
            endpoint_node_id=target_node_id,
            port_key=target_port_key,
        )
        try:
            model.add_edge(
                workspace.workspace_id,
                source_node_id=source_node_id,
                source_port_key=source_port_key,
                target_node_id=target_node_id,
                target_port_key=target_port_key,
                label=str(edge_payload.get("label", "")),
                visual_style=copy.deepcopy(edge_payload.get("visual_style", {})),
            )
        except ValueError:
            continue
    return inserted_node_ids


def _remap_fragment_parent_id(
    *,
    source_parent_id: object,
    node_id_map: dict[str, str],
    workspace: WorkspaceData,
) -> str | None:
    if source_parent_id is None:
        return None
    normalized_parent_id = str(source_parent_id).strip()
    if not normalized_parent_id:
        return None
    external_parent_id = _decode_fragment_external_parent_id(normalized_parent_id)
    if external_parent_id is not None:
        if external_parent_id in workspace.nodes:
            return external_parent_id
        return None
    if normalized_parent_id in node_id_map:
        return node_id_map[normalized_parent_id]
    if normalized_parent_id in workspace.nodes:
        return normalized_parent_id
    return None


def _decode_fragment_external_parent_id(encoded_parent_id: str) -> str | None:
    if not encoded_parent_id.startswith(_FRAGMENT_EXTERNAL_PARENT_PREFIX):
        return None
    normalized_parent_id = encoded_parent_id[len(_FRAGMENT_EXTERNAL_PARENT_PREFIX) :].strip()
    return normalized_parent_id or None


def _remap_fragment_edge_port_key(
    *,
    workspace: WorkspaceData,
    node_id_map: dict[str, str],
    endpoint_node_id: str,
    port_key: str,
) -> str:
    endpoint_node = workspace.nodes.get(endpoint_node_id)
    if endpoint_node is None:
        return port_key
    # Subnode shell edge port keys are child pin node ids; remap those ids with the fragment map.
    if endpoint_node.type_id != SUBNODE_TYPE_ID:
        return port_key
    return node_id_map.get(port_key, port_key)


def group_selection_into_subnode(
    *,
    model: GraphModel,
    registry: NodeRegistry,
    workspace_id: str,
    selected_node_ids: Sequence[object],
    scope_path: Sequence[object] | None,
    shell_x: float,
    shell_y: float,
) -> GroupSubnodeResult | None:
    workspace = model.project.workspaces.get(str(workspace_id).strip())
    if workspace is None:
        return None

    normalized_scope = normalize_scope_path(workspace, scope_path)
    expected_parent_id = scope_parent_id(normalized_scope)
    roots = _normalize_selected_roots(
        workspace=workspace,
        selected_node_ids=selected_node_ids,
        expected_parent_id=expected_parent_id,
    )
    if len(roots) < 2:
        return None
    if not _roots_share_parent(workspace=workspace, node_ids=roots):
        return None

    selected_set = set(roots)
    incoming_edges, outgoing_edges = _boundary_edges(
        workspace=workspace,
        selected_node_ids=selected_set,
    )
    incoming_boundary = [
        _build_boundary_edge(
            edge=edge,
            pin_type_id=SUBNODE_INPUT_TYPE_ID,
            registry=registry,
            workspace=workspace,
            inner_node_id=edge.target_node_id,
            inner_port_key=edge.target_port_key,
        )
        for edge in incoming_edges
    ]
    outgoing_boundary = [
        _build_boundary_edge(
            edge=edge,
            pin_type_id=SUBNODE_OUTPUT_TYPE_ID,
            registry=registry,
            workspace=workspace,
            inner_node_id=edge.source_node_id,
            inner_port_key=edge.source_port_key,
        )
        for edge in outgoing_edges
    ]

    shell_defaults = registry.default_properties(SUBNODE_TYPE_ID)
    shell_spec = registry.get_spec(SUBNODE_TYPE_ID)
    shell = model.add_node(
        workspace.workspace_id,
        type_id=SUBNODE_TYPE_ID,
        title=shell_spec.display_name,
        x=float(shell_x),
        y=float(shell_y),
        properties=shell_defaults,
        exposed_ports={},
    )
    shell.parent_node_id = expected_parent_id

    for node_id in roots:
        node = workspace.nodes.get(node_id)
        if node is not None:
            node.parent_node_id = shell.node_id

    created_pin_ids: list[str] = []

    for index, boundary in enumerate(incoming_boundary):
        pin_id = _create_boundary_pin(
            model=model,
            registry=registry,
            workspace=workspace,
            workspace_id=workspace.workspace_id,
            shell_node_id=shell.node_id,
            pin_type_id=boundary.pin_type_id,
            x=float(shell_x) - _PIN_OFFSET_X,
            y=float(shell_y) + (index * _PIN_ROW_STEP),
            label=boundary.label,
            kind=boundary.kind,
            data_type=boundary.data_type,
        )
        created_pin_ids.append(pin_id)
        model.remove_edge(workspace.workspace_id, boundary.edge.edge_id)
        model.add_edge(
            workspace.workspace_id,
            source_node_id=boundary.edge.source_node_id,
            source_port_key=boundary.edge.source_port_key,
            target_node_id=shell.node_id,
            target_port_key=pin_id,
        )
        model.add_edge(
            workspace.workspace_id,
            source_node_id=pin_id,
            source_port_key=SUBNODE_PIN_PORT_KEY,
            target_node_id=boundary.edge.target_node_id,
            target_port_key=boundary.edge.target_port_key,
        )

    for index, boundary in enumerate(outgoing_boundary):
        pin_id = _create_boundary_pin(
            model=model,
            registry=registry,
            workspace=workspace,
            workspace_id=workspace.workspace_id,
            shell_node_id=shell.node_id,
            pin_type_id=boundary.pin_type_id,
            x=float(shell_x) + _PIN_OFFSET_X,
            y=float(shell_y) + (index * _PIN_ROW_STEP),
            label=boundary.label,
            kind=boundary.kind,
            data_type=boundary.data_type,
        )
        created_pin_ids.append(pin_id)
        model.remove_edge(workspace.workspace_id, boundary.edge.edge_id)
        model.add_edge(
            workspace.workspace_id,
            source_node_id=boundary.edge.source_node_id,
            source_port_key=boundary.edge.source_port_key,
            target_node_id=pin_id,
            target_port_key=SUBNODE_PIN_PORT_KEY,
        )
        model.add_edge(
            workspace.workspace_id,
            source_node_id=shell.node_id,
            source_port_key=pin_id,
            target_node_id=boundary.edge.target_node_id,
            target_port_key=boundary.edge.target_port_key,
        )

    return GroupSubnodeResult(
        shell_node_id=shell.node_id,
        moved_node_ids=tuple(roots),
        created_pin_node_ids=tuple(created_pin_ids),
    )


def ungroup_subnode(
    *,
    model: GraphModel,
    workspace_id: str,
    shell_node_id: object,
) -> UngroupSubnodeResult | None:
    workspace = model.project.workspaces.get(str(workspace_id).strip())
    if workspace is None:
        return None

    normalized_shell_id = str(shell_node_id).strip()
    if not normalized_shell_id:
        return None
    shell = workspace.nodes.get(normalized_shell_id)
    if shell is None or shell.type_id != SUBNODE_TYPE_ID:
        return None

    direct_children = [
        node
        for node in workspace.nodes.values()
        if node.parent_node_id == normalized_shell_id
    ]
    direct_children.sort(key=lambda node: (float(node.y), float(node.x), node.node_id))

    pin_nodes = [node for node in direct_children if is_subnode_pin_type(node.type_id)]
    moved_nodes = [node for node in direct_children if not is_subnode_pin_type(node.type_id)]

    rewired_edges: set[tuple[str, str, str, str]] = set()
    for pin_node in pin_nodes:
        if pin_node.type_id == SUBNODE_INPUT_TYPE_ID:
            outer_edges = [
                edge
                for edge in workspace.edges.values()
                if edge.target_node_id == normalized_shell_id
                and edge.target_port_key == pin_node.node_id
            ]
            inner_edges = [
                edge
                for edge in workspace.edges.values()
                if edge.source_node_id == pin_node.node_id
                and edge.source_port_key == SUBNODE_PIN_PORT_KEY
            ]
            outer_edges.sort(key=_edge_sort_key)
            inner_edges.sort(key=_edge_sort_key)
            for outer in outer_edges:
                for inner in inner_edges:
                    rewired_edges.add(
                        (
                            outer.source_node_id,
                            outer.source_port_key,
                            inner.target_node_id,
                            inner.target_port_key,
                        )
                    )
        else:
            inner_edges = [
                edge
                for edge in workspace.edges.values()
                if edge.target_node_id == pin_node.node_id
                and edge.target_port_key == SUBNODE_PIN_PORT_KEY
            ]
            outer_edges = [
                edge
                for edge in workspace.edges.values()
                if edge.source_node_id == normalized_shell_id
                and edge.source_port_key == pin_node.node_id
            ]
            inner_edges.sort(key=_edge_sort_key)
            outer_edges.sort(key=_edge_sort_key)
            for inner in inner_edges:
                for outer in outer_edges:
                    rewired_edges.add(
                        (
                            inner.source_node_id,
                            inner.source_port_key,
                            outer.target_node_id,
                            outer.target_port_key,
                        )
                    )

    for node in moved_nodes:
        node.parent_node_id = shell.parent_node_id

    for pin_node in pin_nodes:
        model.remove_node(workspace.workspace_id, pin_node.node_id)
    model.remove_node(workspace.workspace_id, normalized_shell_id)

    for source_node_id, source_port_key, target_node_id, target_port_key in sorted(rewired_edges):
        if source_node_id not in workspace.nodes or target_node_id not in workspace.nodes:
            continue
        try:
            model.add_edge(
                workspace.workspace_id,
                source_node_id=source_node_id,
                source_port_key=source_port_key,
                target_node_id=target_node_id,
                target_port_key=target_port_key,
            )
        except (KeyError, ValueError):
            continue

    return UngroupSubnodeResult(
        removed_shell_node_id=normalized_shell_id,
        moved_node_ids=tuple(node.node_id for node in moved_nodes),
        removed_pin_node_ids=tuple(node.node_id for node in pin_nodes),
    )


def _normalize_selected_roots(
    *,
    workspace: WorkspaceData,
    selected_node_ids: Sequence[object],
    expected_parent_id: str | None,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in selected_node_ids:
        node_id = str(value).strip()
        if not node_id or node_id in seen:
            continue
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        if node.parent_node_id != expected_parent_id:
            continue
        seen.add(node_id)
        normalized.append(node_id)
    return normalized


def _roots_share_parent(*, workspace: WorkspaceData, node_ids: Sequence[str]) -> bool:
    parent_values = {
        workspace.nodes[node_id].parent_node_id
        for node_id in node_ids
        if node_id in workspace.nodes
    }
    return len(parent_values) == 1


def _boundary_edges(
    *,
    workspace: WorkspaceData,
    selected_node_ids: set[str],
) -> tuple[list[EdgeInstance], list[EdgeInstance]]:
    incoming: list[EdgeInstance] = []
    outgoing: list[EdgeInstance] = []
    for edge in workspace.edges.values():
        source_in = edge.source_node_id in selected_node_ids
        target_in = edge.target_node_id in selected_node_ids
        if source_in and not target_in:
            outgoing.append(edge)
        elif target_in and not source_in:
            incoming.append(edge)
    incoming.sort(
        key=lambda edge: _incoming_boundary_sort_key(workspace, edge),
    )
    outgoing.sort(
        key=lambda edge: _outgoing_boundary_sort_key(workspace, edge),
    )
    return incoming, outgoing


def _incoming_boundary_sort_key(
    workspace: WorkspaceData,
    edge: EdgeInstance,
) -> tuple[float, float, float, float, str, str, str]:
    source_y, source_x = _node_sort_position(workspace, edge.source_node_id)
    target_y, target_x = _node_sort_position(workspace, edge.target_node_id)
    return (
        source_y,
        source_x,
        target_y,
        target_x,
        edge.source_port_key,
        edge.target_port_key,
        edge.edge_id,
    )


def _outgoing_boundary_sort_key(
    workspace: WorkspaceData,
    edge: EdgeInstance,
) -> tuple[float, float, float, float, str, str, str]:
    source_y, source_x = _node_sort_position(workspace, edge.source_node_id)
    target_y, target_x = _node_sort_position(workspace, edge.target_node_id)
    return (
        target_y,
        target_x,
        source_y,
        source_x,
        edge.target_port_key,
        edge.source_port_key,
        edge.edge_id,
    )


def _node_sort_position(workspace: WorkspaceData, node_id: str) -> tuple[float, float]:
    node = workspace.nodes.get(node_id)
    if node is None:
        return (0.0, 0.0)
    return (float(node.y), float(node.x))


def _build_boundary_edge(
    *,
    edge: EdgeInstance,
    pin_type_id: str,
    registry: NodeRegistry,
    workspace: WorkspaceData,
    inner_node_id: str,
    inner_port_key: str,
) -> _BoundaryEdge:
    label, kind, data_type = _pin_signature_for_inner_port(
        registry=registry,
        workspace=workspace,
        node_id=inner_node_id,
        port_key=inner_port_key,
    )
    return _BoundaryEdge(
        edge=edge,
        pin_type_id=pin_type_id,
        label=label,
        kind=kind,
        data_type=data_type,
    )


def _pin_signature_for_inner_port(
    *,
    registry: NodeRegistry,
    workspace: WorkspaceData,
    node_id: str,
    port_key: str,
) -> tuple[str, str, str]:
    default_label = str(port_key).strip() or "Port"
    default_signature = (default_label, "data", "any")
    node = workspace.nodes.get(node_id)
    if node is None:
        return default_signature
    try:
        spec = registry.get_spec(node.type_id)
    except KeyError:
        return default_signature

    port = find_port(
        node=node,
        spec=spec,
        workspace_nodes=workspace.nodes,
        port_key=port_key,
    )
    if port is None:
        return default_signature

    label = str(port.label).strip() or default_label
    kind = str(port.kind).strip().lower()
    if kind not in set(SUBNODE_PIN_KIND_VALUES):
        kind = "data"

    data_type = str(port.data_type).strip().lower() or "any"
    if kind in _FLOW_KINDS:
        data_type = "any"
    return label, kind, data_type


def _create_boundary_pin(
    *,
    model: GraphModel,
    registry: NodeRegistry,
    workspace: WorkspaceData,
    workspace_id: str,
    shell_node_id: str,
    pin_type_id: str,
    x: float,
    y: float,
    label: str,
    kind: str,
    data_type: str,
) -> str:
    pin_spec = registry.get_spec(pin_type_id)
    pin_defaults = registry.default_properties(pin_type_id)
    pin = model.add_node(
        workspace_id,
        type_id=pin_type_id,
        title=pin_spec.display_name,
        x=float(x),
        y=float(y),
        properties=pin_defaults,
        exposed_ports={},
    )
    pin.parent_node_id = shell_node_id
    pin.properties[SUBNODE_PIN_LABEL_PROPERTY] = str(label).strip() or pin_defaults.get(SUBNODE_PIN_LABEL_PROPERTY, "")

    normalized_kind = str(kind).strip().lower()
    if normalized_kind not in set(SUBNODE_PIN_KIND_VALUES):
        normalized_kind = "data"
    pin.properties[SUBNODE_PIN_KIND_PROPERTY] = normalized_kind

    normalized_data_type = str(data_type).strip().lower() or "any"
    if normalized_kind in _FLOW_KINDS:
        normalized_data_type = "any"
    pin.properties[SUBNODE_PIN_DATA_TYPE_PROPERTY] = normalized_data_type

    # Keep shell ports exposed by default when deriving pins from a grouped boundary.
    workspace.nodes[shell_node_id].exposed_ports[pin.node_id] = True
    return pin.node_id


def _edge_sort_key(edge: EdgeInstance) -> tuple[str, str, str, str, str]:
    return (
        edge.source_node_id,
        edge.source_port_key,
        edge.target_node_id,
        edge.target_port_key,
        edge.edge_id,
    )


__all__ = [
    "GroupSubnodeResult",
    "UngroupSubnodeResult",
    "build_subnode_custom_workflow_snapshot_data",
    "build_subtree_fragment_payload_data",
    "encode_fragment_external_parent_id",
    "expand_subtree_fragment_node_ids",
    "group_selection_into_subnode",
    "insert_graph_fragment",
    "ungroup_subnode",
]
