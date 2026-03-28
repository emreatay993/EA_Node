from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.nodes.types import property_has_inline_editor

_INLINE_PROPERTY_OVERRIDE_PORT_PRECEDENCE: dict[tuple[str, str], tuple[str, ...]] = {
    ("dpf.model", "path"): ("result_file", "path"),
}


def _inline_property_presentation(
    *,
    node: Any,
    property_key: str,
    property_value: Any,
) -> dict[str, Any]:
    if str(getattr(node, "type_id", "")).strip() != "io.process_run":
        return {}
    if str(property_key).strip() != "output_mode":
        return {}

    output_mode = str(property_value or "memory").strip().lower()
    if output_mode == "stored":
        return {
            "status_chip_text": "Stored transcripts",
            "status_chip_variant": "stored",
            "status_chip_description": "stdout/stderr emit staged artifact refs",
        }
    return {
        "status_chip_text": "Inline capture",
        "status_chip_variant": "memory",
        "status_chip_description": "stdout/stderr stay inline strings",
    }


def _overriding_input_port(
    *,
    node: Any,
    property_key: str,
    resolved_input_ports: Mapping[str, Any],
    port_connection_counts: Mapping[tuple[str, str], int],
) -> Any | None:
    node_id = str(getattr(node, "node_id", "")).strip()
    node_type_id = str(getattr(node, "type_id", "")).strip()
    candidate_port_keys = _INLINE_PROPERTY_OVERRIDE_PORT_PRECEDENCE.get(
        (node_type_id, property_key),
        (property_key,),
    )
    for port_key in candidate_port_keys:
        port = resolved_input_ports.get(port_key)
        if port is None:
            continue
        if port_connection_counts.get((node_id, port_key), 0) > 0:
            return port
    return None


def build_property_input_override_state(
    *,
    node: Any,
    property_key: str,
    resolved_input_ports: Mapping[str, Any],
    port_connection_counts: Mapping[tuple[str, str], int] | None = None,
) -> dict[str, Any]:
    overriding_input_port = _overriding_input_port(
        node=node,
        property_key=property_key,
        resolved_input_ports=resolved_input_ports,
        port_connection_counts=port_connection_counts or {},
    )
    return {
        "overridden_by_input": overriding_input_port is not None,
        "input_port_label": (
            str(overriding_input_port.label or overriding_input_port.key)
            if overriding_input_port is not None
            else ""
        ),
    }


def build_user_facing_node_instance_number(
    *,
    node: Any,
    workflow_nodes: Mapping[str, Any],
) -> int:
    instance_number = 1
    node_type_id = str(getattr(node, "type_id", "")).strip()
    node_id = str(getattr(node, "node_id", "")).strip()
    if not node_type_id or not node_id:
        return instance_number

    matching_count = 0
    for workflow_node in workflow_nodes.values():
        if str(getattr(workflow_node, "type_id", "")).strip() != node_type_id:
            continue
        matching_count += 1
        if str(getattr(workflow_node, "node_id", "")).strip() == node_id:
            return matching_count
    return instance_number


def build_inline_property_items(
    *,
    node: Any,
    spec: Any,
    workspace_nodes: Mapping[str, Any],
    port_connection_counts: Mapping[tuple[str, str], int] | None = None,
) -> list[dict[str, Any]]:
    counts = port_connection_counts or {}
    resolved_input_ports = {
        port.key: port
        for port in effective_ports(node=node, spec=spec, workspace_nodes=workspace_nodes)
        if str(port.direction).strip().lower() == "in" and bool(port.exposed)
    }
    items: list[dict[str, Any]] = []
    for prop in spec.properties:
        if not property_has_inline_editor(prop):
            continue
        property_value = node.properties.get(prop.key, prop.default)
        overriding_input_port = _overriding_input_port(
            node=node,
            property_key=prop.key,
            resolved_input_ports=resolved_input_ports,
            port_connection_counts=counts,
        )
        items.append(
            {
                "key": prop.key,
                "label": prop.label,
                "type": prop.type,
                "value": property_value,
                "enum_values": list(prop.enum_values),
                "inline_editor": prop.inline_editor,
                **build_property_input_override_state(
                    node=node,
                    property_key=prop.key,
                    resolved_input_ports=resolved_input_ports,
                    port_connection_counts=counts,
                ),
                **_inline_property_presentation(
                    node=node,
                    property_key=prop.key,
                    property_value=property_value,
                ),
            }
        )
    return items


__all__ = [
    "build_property_input_override_state",
    "build_inline_property_items",
    "build_user_facing_node_instance_number",
]
