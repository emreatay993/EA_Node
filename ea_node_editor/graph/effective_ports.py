from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from ea_node_editor.graph.model import EdgeInstance, NodeInstance
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
from ea_node_editor.nodes.types import NodeTypeSpec, PortSpec

_FLOW_KINDS = frozenset({"exec", "completed", "failed"})


@dataclass(slots=True, frozen=True)
class EffectivePort:
    key: str
    label: str
    direction: str
    kind: str
    data_type: str
    required: bool = False
    exposed: bool = True
    allow_multiple_connections: bool = False


def is_subnode_shell_type(type_id: str) -> bool:
    return str(type_id) == SUBNODE_TYPE_ID


def is_subnode_pin_type(type_id: str) -> bool:
    return str(type_id) in {SUBNODE_INPUT_TYPE_ID, SUBNODE_OUTPUT_TYPE_ID}


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
            label=port.key,
            direction=port.direction,
            kind=port.kind,
            data_type=port.data_type,
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
    return port.direction


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
    if port.direction != "in":
        raise ValueError(f"Port {port_key} is not an input on node type {spec.type_id}")
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
        if port.direction != direction:
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
        if port.direction == "in":
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
        pin_port = _subnode_pin_port(node=pin_node)
        shell_direction = "in" if pin_node.type_id == SUBNODE_INPUT_TYPE_ID else "out"
        shell_key = pin_node.node_id
        ports.append(
            EffectivePort(
                key=shell_key,
                label=pin_port.label,
                direction=shell_direction,
                kind=pin_port.kind,
                data_type=pin_port.data_type,
                required=shell_direction == "in",
                exposed=bool(node.exposed_ports.get(shell_key, True)),
                allow_multiple_connections=bool(pin_port.allow_multiple_connections),
            )
        )
    return tuple(ports)


def _subnode_pin_port(*, node: NodeInstance) -> EffectivePort:
    default_label = "Input" if node.type_id == SUBNODE_INPUT_TYPE_ID else "Output"
    label = str(node.properties.get(SUBNODE_PIN_LABEL_PROPERTY, default_label)).strip() or default_label

    kind_value = str(node.properties.get(SUBNODE_PIN_KIND_PROPERTY, "data")).strip().lower()
    if kind_value not in set(SUBNODE_PIN_KIND_VALUES):
        kind_value = "data"
    data_type = str(node.properties.get(SUBNODE_PIN_DATA_TYPE_PROPERTY, "any")).strip().lower() or "any"
    if kind_value in _FLOW_KINDS:
        data_type = "any"

    direction = "out" if node.type_id == SUBNODE_INPUT_TYPE_ID else "in"
    return EffectivePort(
        key=SUBNODE_PIN_PORT_KEY,
        label=label,
        direction=direction,
        kind=kind_value,
        data_type=data_type,
        required=direction == "in",
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
    "port_allows_multiple_connections",
    "is_subnode_pin_type",
    "is_subnode_shell_type",
    "port_data_type",
    "port_direction",
    "port_kind",
    "ports_compatible",
    "target_port_has_capacity",
    "visible_ports",
]
