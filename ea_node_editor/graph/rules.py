from __future__ import annotations

from typing import Iterable

from ea_node_editor.graph.effective_ports import (
    port_accepted_data_types as effective_port_accepted_data_types,
    port_layout_direction,
    port_side as _port_side,
    ports_compatible as effective_ports_compatible,
)
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec, PortSpec


def find_port(spec: NodeTypeSpec, port_key: str) -> PortSpec | None:
    for port in spec.ports:
        if port.key == port_key:
            return port
    return None


def port_direction(spec: NodeTypeSpec, port_key: str) -> str:
    port = find_port(spec, port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return port_layout_direction(port)


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


def port_accepted_data_types(spec: NodeTypeSpec, port_key: str) -> tuple[str, ...]:
    port = find_port(spec, port_key)
    if port is None:
        return ("any",)
    return effective_port_accepted_data_types(port)


def ports_compatible(source_port: PortSpec, target_port: PortSpec) -> bool:
    return effective_ports_compatible(source_port, target_port)


def is_port_exposed(node: NodeInstance, spec: NodeTypeSpec, port_key: str) -> bool:
    port = find_port(spec, port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return bool(port.required or node.exposed_ports.get(port.key, port.exposed))


def default_port(node: NodeInstance, spec: NodeTypeSpec, direction: str) -> str | None:
    for port in spec.ports:
        if port_layout_direction(port) != direction:
            continue
        if bool(port.required or node.exposed_ports.get(port.key, port.exposed)):
            return port.key
    return None


def visible_ports(node: NodeInstance, spec: NodeTypeSpec) -> tuple[list[PortSpec], list[PortSpec]]:
    in_ports: list[PortSpec] = []
    out_ports: list[PortSpec] = []
    for port in spec.ports:
        if not bool(port.required or node.exposed_ports.get(port.key, port.exposed)):
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
    direction: str,
    candidates: Iterable[PortSpec],
) -> PortSpec | None:
    for port in spec.ports:
        if port_layout_direction(port) != direction:
            continue
        if not is_port_exposed(node, spec, port.key):
            continue
        for candidate in candidates:
            if ports_compatible(candidate, port):
                return port
    return None


def port_side(spec: NodeTypeSpec, port_key: str) -> str:
    port = find_port(spec, port_key)
    if port is None:
        raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
    return _port_side(port)


__all__ = [
    "default_port",
    "find_port",
    "first_compatible_port",
    "port_accepted_data_types",
    "is_port_exposed",
    "port_data_type",
    "port_direction",
    "port_kind",
    "port_side",
    "ports_compatible",
    "visible_ports",
]
