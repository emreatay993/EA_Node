from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ea_node_editor.custom_workflows import CUSTOM_WORKFLOW_LIBRARY_CATEGORY
from ea_node_editor.graph.effective_ports import effective_ports


def build_registry_library_items(*, registry_specs: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        {
            "type_id": spec.type_id,
            "display_name": spec.display_name,
            "category": spec.category,
            "icon": spec.icon,
            "description": spec.description,
            "library_source": "node_registry",
            "ports": [
                {
                    "key": port.key,
                    "label": port.key,
                    "direction": port.direction,
                    "kind": port.kind,
                    "data_type": port.data_type,
                    "exposed": bool(port.exposed),
                }
                for port in spec.ports
            ],
        }
        for spec in registry_specs
    ]


def build_combined_library_items(
    *,
    registry_items: Iterable[dict[str, Any]],
    custom_workflow_items: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    items = list(registry_items)
    items.extend(custom_workflow_items)
    items.sort(
        key=lambda item: (
            str(item.get("category", "")).lower(),
            str(item.get("display_name", "")).lower(),
            str(item.get("type_id", "")).lower(),
        )
    )
    return items


def library_item_matches_filters(
    item: dict[str, Any],
    *,
    query: str,
    category: str,
    data_type: str,
    direction: str,
) -> bool:
    item_category = str(item.get("category", "")).strip().lower()
    if category and item_category != category:
        return False

    ports = item.get("ports", [])
    normalized_ports = ports if isinstance(ports, list) else []

    if data_type or direction:
        matches_port = False
        for port in normalized_ports:
            if not isinstance(port, dict):
                continue
            port_direction = str(port.get("direction", "")).strip().lower()
            port_data_type = str(port.get("data_type", "")).strip().lower()
            if direction and port_direction != direction:
                continue
            if data_type and port_data_type != data_type:
                continue
            matches_port = True
            break
        if not matches_port:
            return False

    if not query:
        return True
    text_haystack = " ".join(
        [
            str(item.get("type_id", "")),
            str(item.get("display_name", "")),
            str(item.get("category", "")),
            str(item.get("description", "")),
            " ".join(str(port.get("key", "")) for port in normalized_ports if isinstance(port, dict)),
        ]
    ).lower()
    return query in text_haystack


def build_filtered_library_items(
    *,
    combined_items: Iterable[dict[str, Any]],
    query: str,
    category: str,
    data_type: str,
    direction: str,
) -> list[dict[str, Any]]:
    normalized_query = str(query).strip().lower()
    normalized_category = str(category).strip().lower()
    normalized_data_type = str(data_type).strip().lower()
    normalized_direction = str(direction).strip().lower()
    return [
        item
        for item in combined_items
        if library_item_matches_filters(
            item,
            query=normalized_query,
            category=normalized_category,
            data_type=normalized_data_type,
            direction=normalized_direction,
        )
    ]


def build_grouped_library_items(*, filtered_items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in filtered_items:
        category = str(item.get("category", "Other"))
        groups.setdefault(category, []).append(item)
    payload: list[dict[str, Any]] = []
    for category in sorted(groups):
        payload.append({"kind": "category", "category": category, "label": category})
        for node_item in groups[category]:
            payload.append(
                {
                    "kind": "node",
                    "category": category,
                    "type_id": node_item["type_id"],
                    "display_name": node_item["display_name"],
                    "icon": node_item.get("icon", ""),
                    "description": node_item["description"],
                    "ports": list(node_item.get("ports", [])),
                    "library_source": node_item.get("library_source", "node_registry"),
                    "workflow_id": node_item.get("workflow_id", ""),
                    "revision": node_item.get("revision", 1),
                    "workflow_scope": node_item.get("workflow_scope", "local"),
                }
            )
    return payload


def build_library_category_options(
    *,
    combined_items: Iterable[dict[str, Any]],
    registry_categories: Iterable[str],
) -> list[dict[str, str]]:
    categories = {
        str(item.get("category", "")).strip()
        for item in combined_items
        if str(item.get("category", "")).strip()
    }
    categories.update(str(category) for category in registry_categories)
    categories.add(CUSTOM_WORKFLOW_LIBRARY_CATEGORY)
    return [{"label": "All Categories", "value": ""}] + [
        {"label": category, "value": category} for category in sorted(categories)
    ]


def build_library_direction_options() -> list[dict[str, str]]:
    return [
        {"label": "Any Port Direction", "value": ""},
        {"label": "Input", "value": "in"},
        {"label": "Output", "value": "out"},
    ]


def build_library_data_type_options(
    *,
    registry_specs: Iterable[Any],
    custom_workflow_items: Iterable[dict[str, Any]],
) -> list[dict[str, str]]:
    data_types = {
        str(port.data_type).strip().lower()
        for spec in registry_specs
        for port in spec.ports
        if str(port.data_type).strip()
    }
    for item in custom_workflow_items:
        ports = item.get("ports", [])
        if not isinstance(ports, list):
            continue
        for port in ports:
            if not isinstance(port, dict):
                continue
            data_type = str(port.get("data_type", "")).strip().lower()
            if data_type:
                data_types.add(data_type)
    return [{"label": "Any Data Type", "value": ""}] + [
        {"label": data_type, "value": data_type} for data_type in sorted(data_types)
    ]


def build_pin_data_type_options(
    *,
    registry_specs: Iterable[Any],
    workspaces: Iterable[Any],
    subnode_pin_type_ids: set[str],
    subnode_pin_data_type_property: str,
) -> list[str]:
    suggested = {"any", "str", "int", "float", "bool", "json", "path"}
    suggested.update(
        str(port.data_type).strip().lower()
        for spec in registry_specs
        for port in spec.ports
        if str(port.data_type).strip()
    )
    for workspace in workspaces:
        for node in workspace.nodes.values():
            if node.type_id not in subnode_pin_type_ids:
                continue
            value = str(node.properties.get(subnode_pin_data_type_property, "")).strip().lower()
            if value:
                suggested.add(value)
    ordered: list[str] = []
    if "any" in suggested:
        ordered.append("any")
        suggested.remove("any")
    ordered.extend(sorted(suggested))
    return ordered


def build_selected_node_property_items(
    *,
    node: Any,
    spec: Any,
    subnode_pin_type_ids: set[str],
) -> list[dict[str, Any]]:
    if node.type_id in subnode_pin_type_ids:
        ordered_keys = ("label", "kind", "data_type")
        ordered_properties = [prop for key in ordered_keys for prop in spec.properties if prop.key == key]
    else:
        ordered_properties = list(spec.properties)
    return [
        {
            "key": prop.key,
            "label": prop.label,
            "type": prop.type,
            "value": node.properties.get(prop.key, prop.default),
            "enum_values": list(prop.enum_values),
        }
        for prop in ordered_properties
    ]


def build_selected_node_port_items(
    *,
    node: Any,
    spec: Any,
    workspace_nodes: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "key": port.key,
            "label": port.label,
            "direction": port.direction,
            "kind": port.kind,
            "data_type": port.data_type,
            "required": bool(port.required),
            "exposed": bool(port.exposed),
        }
        for port in effective_ports(node=node, spec=spec, workspace_nodes=workspace_nodes)
    ]
