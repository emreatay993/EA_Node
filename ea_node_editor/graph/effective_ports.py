from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from ea_node_editor.graph.model import EdgeInstance, NodeInstance
from ea_node_editor.graph.subnode_contract import (
    SUBNODE_PIN_PORT_KEY,
    is_subnode_pin_type as _is_subnode_pin_type,
    is_subnode_shell_type as _is_subnode_shell_type,
    resolve_subnode_pin_definition,
)
from ea_node_editor.nodes.types import NodeTypeSpec, PortSpec

_FLOW_KINDS = frozenset({"exec", "completed", "failed"})
_CARDINAL_SIDES = ("top", "right", "bottom", "left")
_LAYOUT_INPUT_SIDES = frozenset({"top", "left"})


@dataclass(slots=True, frozen=True)
class EffectivePort:
    key: str
    label: str
    direction: str
    kind: str
    data_type: str
    side: str = ""
    required: bool = False
    exposed: bool = True
    allow_multiple_connections: bool = False


def port_side(port: EffectivePort | PortSpec) -> str:
    side = str(getattr(port, "side", "") or "").strip().lower()
    if side in _CARDINAL_SIDES:
        return side
    return ""


def is_neutral_flow_port(port: EffectivePort | PortSpec) -> bool:
    return (
        str(port.direction) == "neutral"
        and str(port.kind) == "flow"
        and str(port.data_type) == "flow"
        and bool(port_side(port))
    )


def port_layout_direction(port: EffectivePort | PortSpec) -> str:
    if not is_neutral_flow_port(port):
        return str(port.direction)
    return "in" if port_side(port) in _LAYOUT_INPUT_SIDES else "out"


def port_supports_outgoing_edge(port: EffectivePort | PortSpec) -> bool:
    return str(port.direction) == "out" or is_neutral_flow_port(port)


def port_supports_incoming_edge(port: EffectivePort | PortSpec) -> bool:
    return str(port.direction) == "in" or is_neutral_flow_port(port)


def is_subnode_shell_type(type_id: str) -> bool:
    return _is_subnode_shell_type(type_id)


def is_subnode_pin_type(type_id: str) -> bool:
    return _is_subnode_pin_type(type_id)


def are_port_kinds_compatible(source_kind: str, target_kind: str) -> bool:
    if source_kind in _FLOW_KINDS or target_kind in _FLOW_KINDS:
        return source_kind == target_kind
    return True


def are_data_types_compatible(source_type: str, target_type: str) -> bool:
    if source_type == "any" or target_type == "any":
        return True
    return source_type == target_type


def ports_compatible(source_port: EffectivePort | PortSpec, target_port: EffectivePort | PortSpec) -> bool:
    return are_port_kinds_compatible(source_port.kind, target_port.kind) and are_data_types_compatible(
        source_port.data_type,
        target_port.data_type,
    )


def effective_ports(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
) -> tuple[EffectivePort, ...]:
    if is_subnode_shell_type(node.type_id):
        return _subnode_shell_ports(node=node, workspace_nodes=workspace_nodes)
    if is_subnode_pin_type(node.type_id):
        return (_subnode_pin_port(node=node),)
    return tuple(
        EffectivePort(
            key=port.key,
            label=node.port_labels.get(port.key) or port.label or port.key,
            direction=port.direction,
            kind=port.kind,
            data_type=port.data_type,
            side=port.side,
            required=port.required,
            exposed=bool(node.exposed_ports.get(port.key, port.exposed)),
            allow_multiple_connections=bool(port.allow_multiple_connections),
        )
        for port in spec.ports
    )


def find_port(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    port_key: str,
) -> EffectivePort | None:
    for port in effective_ports(node=node, spec=spec, workspace_nodes=workspace_nodes):
        if port.key == port_key:
            return port
    return None


def port_direction(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    port_key: str,
) -> str:
    port = find_port(node=node, spec=spec, workspace_nodes=workspace_nodes, port_key=port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return port_layout_direction(port)


def port_kind(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    port_key: str,
) -> str:
    port = find_port(node=node, spec=spec, workspace_nodes=workspace_nodes, port_key=port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return port.kind


def port_data_type(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    port_key: str,
) -> str:
    port = find_port(node=node, spec=spec, workspace_nodes=workspace_nodes, port_key=port_key)
    if port is None:
        return "any"
    return port.data_type


def is_port_exposed(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    port_key: str,
) -> bool:
    port = find_port(node=node, spec=spec, workspace_nodes=workspace_nodes, port_key=port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return bool(port.exposed)


def port_allows_multiple_connections(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    port_key: str,
) -> bool:
    port = find_port(node=node, spec=spec, workspace_nodes=workspace_nodes, port_key=port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return bool(port.allow_multiple_connections)


def target_port_has_capacity(
    *,
    edges: Iterable[EdgeInstance],
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    port_key: str,
) -> bool:
    port = find_port(node=node, spec=spec, workspace_nodes=workspace_nodes, port_key=port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    if not port_supports_incoming_edge(port):
        raise ValueError(f"Port {port_key} does not accept incoming edges on node type {spec.type_id}")
    if port.allow_multiple_connections:
        return True
    for edge in edges:
        if edge.target_node_id == node.node_id and edge.target_port_key == port_key:
            return False
    return True


def default_port(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    direction: str,
) -> str | None:
    for port in effective_ports(node=node, spec=spec, workspace_nodes=workspace_nodes):
        if port_layout_direction(port) != direction:
            continue
        if port.exposed:
            return port.key
    return None


def visible_ports(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
) -> tuple[list[EffectivePort], list[EffectivePort]]:
    in_ports: list[EffectivePort] = []
    out_ports: list[EffectivePort] = []
    for port in effective_ports(node=node, spec=spec, workspace_nodes=workspace_nodes):
        if not port.exposed:
            continue
        if port_layout_direction(port) == "in":
            in_ports.append(port)
        else:
            out_ports.append(port)
    return in_ports, out_ports


def first_compatible_port(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    direction: str,
    candidates: Iterable[EffectivePort | PortSpec],
) -> EffectivePort | None:
    in_ports, out_ports = visible_ports(node=node, spec=spec, workspace_nodes=workspace_nodes)
    ports = in_ports if direction == "in" else out_ports
    for port in ports:
        for candidate in candidates:
            if ports_compatible(candidate, port):
                return port
    return None


def preferred_connection_port(
    *,
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    direction: str,
    peer_node: NodeInstance,
) -> str | None:
    neutral_ports = [
        port
        for port in effective_ports(node=node, spec=spec, workspace_nodes=workspace_nodes)
        if port.exposed and is_neutral_flow_port(port)
    ]
    if not neutral_ports:
        return default_port(
            node=node,
            spec=spec,
            workspace_nodes=workspace_nodes,
            direction=direction,
        )

    for side in _ordered_cardinal_sides_toward(node=node, peer_node=peer_node):
        for port in neutral_ports:
            if port.side == side:
                return port.key
    return neutral_ports[0].key


def _ordered_cardinal_sides_toward(*, node: NodeInstance, peer_node: NodeInstance) -> tuple[str, ...]:
    dx = float(peer_node.x) - float(node.x)
    dy = float(peer_node.y) - float(node.y)

    if abs(dx) >= abs(dy):
        primary = "right" if dx >= 0.0 else "left"
        secondary = "bottom" if dy >= 0.0 else "top"
    else:
        primary = "bottom" if dy >= 0.0 else "top"
        secondary = "right" if dx >= 0.0 else "left"

    ordered = [
        primary,
        secondary,
        _opposite_side(secondary),
        _opposite_side(primary),
    ]
    seen: set[str] = set()
    result: list[str] = []
    for side in ordered:
        if side in seen:
            continue
        seen.add(side)
        result.append(side)
    return tuple(result)


def _opposite_side(side: str) -> str:
    if side == "top":
        return "bottom"
    if side == "right":
        return "left"
    if side == "bottom":
        return "top"
    return "right"


def _subnode_shell_ports(
    *,
    node: NodeInstance,
    workspace_nodes: Mapping[str, NodeInstance],
) -> tuple[EffectivePort, ...]:
    child_pins: list[NodeInstance] = []
    for candidate in workspace_nodes.values():
        if candidate.parent_node_id != node.node_id:
            continue
        if not is_subnode_pin_type(candidate.type_id):
            continue
        child_pins.append(candidate)
    child_pins.sort(key=lambda candidate: (float(candidate.y), float(candidate.x), candidate.node_id))

    ports: list[EffectivePort] = []
    for pin_node in child_pins:
        pin_definition = resolve_subnode_pin_definition(
            pin_node.type_id,
            pin_node.properties,
        )
        shell_direction = pin_definition.shell_port_direction
        shell_key = pin_node.node_id
        ports.append(
            EffectivePort(
                key=shell_key,
                label=pin_definition.label,
                direction=shell_direction,
                kind=pin_definition.kind,
                data_type=pin_definition.data_type,
                required=shell_direction == "in",
                exposed=bool(node.exposed_ports.get(shell_key, True)),
                allow_multiple_connections=False,
            )
        )
    return tuple(ports)


def _subnode_pin_port(*, node: NodeInstance) -> EffectivePort:
    pin_definition = resolve_subnode_pin_definition(
        node.type_id,
        node.properties,
    )
    return EffectivePort(
        key=SUBNODE_PIN_PORT_KEY,
        label=pin_definition.label,
        direction=pin_definition.pin_port_direction,
        kind=pin_definition.kind,
        data_type=pin_definition.data_type,
        required=pin_definition.pin_port_direction == "in",
        exposed=bool(node.exposed_ports.get(SUBNODE_PIN_PORT_KEY, True)),
        allow_multiple_connections=False,
    )


__all__ = [
    "EffectivePort",
    "are_data_types_compatible",
    "are_port_kinds_compatible",
    "default_port",
    "effective_ports",
    "find_port",
    "first_compatible_port",
    "is_port_exposed",
    "is_neutral_flow_port",
    "port_allows_multiple_connections",
    "port_layout_direction",
    "port_side",
    "is_subnode_pin_type",
    "is_subnode_shell_type",
    "port_data_type",
    "port_direction",
    "port_kind",
    "port_supports_incoming_edge",
    "port_supports_outgoing_edge",
    "preferred_connection_port",
    "ports_compatible",
    "target_port_has_capacity",
    "visible_ports",
]
