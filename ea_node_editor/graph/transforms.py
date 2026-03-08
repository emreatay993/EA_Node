from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ea_node_editor.graph.effective_ports import find_port, is_subnode_pin_type
from ea_node_editor.graph.hierarchy import normalize_scope_path, scope_parent_id
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
        key=lambda edge: (
            edge.target_node_id,
            edge.target_port_key,
            edge.source_node_id,
            edge.source_port_key,
            edge.edge_id,
        )
    )
    outgoing.sort(
        key=lambda edge: (
            edge.source_node_id,
            edge.source_port_key,
            edge.target_node_id,
            edge.target_port_key,
            edge.edge_id,
        )
    )
    return incoming, outgoing


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
    "group_selection_into_subnode",
    "ungroup_subnode",
]
