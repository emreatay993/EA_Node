from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.nodes.types import NodeTypeSpec

_LOCKABLE_DATA_TYPES = frozenset({"int", "float", "bool", "str"})


def normalize_locked_ports_mapping(value: Mapping[str, Any] | None) -> dict[str, bool]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): bool(item) for key, item in value.items()}


def is_lockable_data_type(data_type: str) -> bool:
    return str(data_type or "").strip().lower() in _LOCKABLE_DATA_TYPES


def is_port_lockable(spec: NodeTypeSpec, port_key: str) -> bool:
    property_keys = {property_spec.key for property_spec in spec.properties}
    for port in spec.ports:
        if port.key != port_key:
            continue
        return (
            port.direction == "in"
            and port.kind == "data"
            and is_lockable_data_type(port.data_type)
            and port.key in property_keys
        )
    return False


def lockable_port_keys(spec: NodeTypeSpec) -> tuple[str, ...]:
    property_keys = {property_spec.key for property_spec in spec.properties}
    return tuple(
        port.key
        for port in spec.ports
        if (
            port.direction == "in"
            and port.kind == "data"
            and is_lockable_data_type(port.data_type)
            and port.key in property_keys
        )
    )


def property_value_triggers_lock(data_type: str, value: Any) -> bool:
    normalized_data_type = str(data_type or "").strip().lower()
    if normalized_data_type == "bool":
        return value is True
    if normalized_data_type == "str":
        return bool(str(value or "").strip())
    if normalized_data_type == "int":
        if isinstance(value, bool):
            return False
        try:
            return int(value) != 0
        except (TypeError, ValueError):
            return False
    if normalized_data_type == "float":
        if isinstance(value, bool):
            return False
        try:
            return float(value) != 0.0
        except (TypeError, ValueError):
            return False
    return False


def compute_initial_locked_ports(
    spec: NodeTypeSpec,
    properties: Mapping[str, Any] | None = None,
    authored_locked_ports: Mapping[str, Any] | None = None,
) -> dict[str, bool]:
    lock_map = normalize_locked_ports_mapping(authored_locked_ports)
    property_values = dict(properties or {})
    property_defaults = {
        property_spec.key: property_spec.default
        for property_spec in spec.properties
    }

    for port in spec.ports:
        if not is_port_lockable(spec, port.key):
            continue
        if lock_map.get(port.key, False):
            continue
        value = property_values.get(port.key, property_defaults.get(port.key))
        if property_value_triggers_lock(port.data_type, value):
            lock_map[port.key] = True
    return lock_map


__all__ = [
    "compute_initial_locked_ports",
    "is_lockable_data_type",
    "is_port_lockable",
    "lockable_port_keys",
    "normalize_locked_ports_mapping",
    "property_value_triggers_lock",
]
