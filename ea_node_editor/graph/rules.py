from __future__ import annotations

from typing import Iterable

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec, PortSpec

_FLOW_KINDS = {"exec", "completed", "failed"}


def find_port(spec: NodeTypeSpec, port_key: str) -> PortSpec | None:
    for port in spec.ports:
        if port.key == port_key:
            return port
    return None


def port_direction(spec: NodeTypeSpec, port_key: str) -> str:
    port = find_port(spec, port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return port.direction


def port_kind(spec: NodeTypeSpec, port_key: str) -> str:
    port = find_port(spec, port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return port.kind


def port_data_type(spec: NodeTypeSpec, port_key: str) -> str:
    port = find_port(spec, port_key)
    if port is None:
        return "any"
    return port.data_type


def are_port_kinds_compatible(source_kind: str, target_kind: str) -> bool:
    if source_kind in _FLOW_KINDS or target_kind in _FLOW_KINDS:
        return source_kind == target_kind
    return True


def are_data_types_compatible(source_type: str, target_type: str) -> bool:
    if source_type == "any" or target_type == "any":
        return True
    return source_type == target_type


def ports_compatible(source_port: PortSpec, target_port: PortSpec) -> bool:
    return are_port_kinds_compatible(source_port.kind, target_port.kind) and are_data_types_compatible(
        source_port.data_type,
        target_port.data_type,
    )


def is_port_exposed(node: NodeInstance, spec: NodeTypeSpec, port_key: str) -> bool:
    port = find_port(spec, port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return bool(node.exposed_ports.get(port.key, port.exposed))


def default_port(node: NodeInstance, spec: NodeTypeSpec, direction: str) -> str | None:
    for port in spec.ports:
        if port.direction != direction:
            continue
        if bool(node.exposed_ports.get(port.key, port.exposed)):
            return port.key
    return None


def visible_ports(node: NodeInstance, spec: NodeTypeSpec) -> tuple[list[PortSpec], list[PortSpec]]:
    in_ports: list[PortSpec] = []
    out_ports: list[PortSpec] = []
    for port in spec.ports:
        if not bool(node.exposed_ports.get(port.key, port.exposed)):
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
    direction: str,
    candidates: Iterable[PortSpec],
) -> PortSpec | None:
    for port in spec.ports:
        if port.direction != direction:
            continue
        if not is_port_exposed(node, spec, port.key):
            continue
        for candidate in candidates:
            if ports_compatible(candidate, port):
                return port
    return None
