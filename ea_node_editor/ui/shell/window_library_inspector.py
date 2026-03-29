from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from ea_node_editor.execution.dpf_runtime.optional_imports import load_dpf_module
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MESH_SELECTION_NAMED_SELECTION,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FILE_NODE_TYPE_ID,
)
from ea_node_editor.custom_workflows import CUSTOM_WORKFLOW_LIBRARY_CATEGORY
from ea_node_editor.graph.effective_ports import (
    are_data_types_compatible,
    are_port_kinds_compatible,
    effective_ports,
    ordered_ports_for_display,
)
from ea_node_editor.graph.file_issue_state import build_file_issue_payload
from ea_node_editor.ui.support.node_presentation import (
    build_property_input_override_state,
    build_inline_property_items,
    build_user_facing_node_instance_number,
)
from ea_node_editor.nodes.types import (
    property_inspector_editor,
    property_visible_in_inspector,
)

_DPF_PATH_LIKE_PORT_KEYS = frozenset({"normalized_path", "written_path", "path"})


def _project_root(project_path: str | None) -> Path | None:
    text = str(project_path or "").strip()
    if not text:
        return None
    candidate = Path(text).expanduser()
    return candidate.parent if candidate.suffix else candidate


def _resolve_candidate_path(value: Any, *, project_path: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        project_root = _project_root(project_path)
        if project_root is not None:
            candidate = project_root / candidate
    return str(candidate.resolve(strict=False))


def _property_text(node: Any, key: str) -> str:
    properties = getattr(node, "properties", {})
    if not isinstance(properties, Mapping):
        return ""
    return str(properties.get(key, "") or "").strip()


def _workspace_edge_values(
    workspace_edges: Mapping[str, Any] | Iterable[Any] | None,
) -> tuple[Any, ...]:
    if workspace_edges is None:
        return ()
    if isinstance(workspace_edges, Mapping):
        return tuple(workspace_edges.values())
    return tuple(workspace_edges)


def _incoming_edge_for_port(
    *,
    node: Any,
    port_key: str,
    workspace_edges: Mapping[str, Any] | Iterable[Any] | None,
) -> Any | None:
    node_id = str(getattr(node, "node_id", "")).strip()
    normalized_port_key = str(port_key or "").strip()
    if not node_id or not normalized_port_key:
        return None
    for edge in _workspace_edge_values(workspace_edges):
        if (
            str(getattr(edge, "target_node_id", "")).strip() == node_id
            and str(getattr(edge, "target_port_key", "")).strip() == normalized_port_key
        ):
            return edge
    return None


def _dedupe_text_values(values: Iterable[Any]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = str(raw_value).strip()
        if not value:
            continue
        normalized = value.casefold()
        if normalized in seen:
            continue
        ordered.append(value)
        seen.add(normalized)
    return tuple(ordered)


def _node_path_property(node: Any, *, project_path: str | None) -> str:
    return _resolve_candidate_path(_property_text(node, "path"), project_path=project_path)


def _resolve_dpf_result_path_from_result_file_node(
    node: Any | None,
    *,
    workspace_nodes: Mapping[str, Any],
    workspace_edges: Mapping[str, Any] | Iterable[Any] | None,
    project_path: str | None,
    visited_node_ids: frozenset[str],
) -> str:
    if node is None:
        return ""
    node_id = str(getattr(node, "node_id", "")).strip()
    if not node_id or node_id in visited_node_ids:
        return ""
    next_visited = visited_node_ids | {node_id}
    path_edge = _incoming_edge_for_port(node=node, port_key="path", workspace_edges=workspace_edges)
    if path_edge is not None:
        source_node = workspace_nodes.get(str(getattr(path_edge, "source_node_id", "")).strip())
        resolved = _resolve_static_path_from_output_source(
            source_node,
            source_port_key=str(getattr(path_edge, "source_port_key", "")).strip(),
            workspace_nodes=workspace_nodes,
            workspace_edges=workspace_edges,
            project_path=project_path,
            visited_node_ids=next_visited,
        )
        if resolved:
            return resolved
    return _node_path_property(node, project_path=project_path)


def _resolve_dpf_result_path_from_model_node(
    node: Any | None,
    *,
    workspace_nodes: Mapping[str, Any],
    workspace_edges: Mapping[str, Any] | Iterable[Any] | None,
    project_path: str | None,
    visited_node_ids: frozenset[str],
) -> str:
    if node is None:
        return ""
    node_id = str(getattr(node, "node_id", "")).strip()
    if not node_id or node_id in visited_node_ids:
        return ""
    next_visited = visited_node_ids | {node_id}
    result_file_edge = _incoming_edge_for_port(node=node, port_key="result_file", workspace_edges=workspace_edges)
    if result_file_edge is not None:
        source_node = workspace_nodes.get(str(getattr(result_file_edge, "source_node_id", "")).strip())
        resolved = _resolve_static_path_from_output_source(
            source_node,
            source_port_key=str(getattr(result_file_edge, "source_port_key", "")).strip(),
            workspace_nodes=workspace_nodes,
            workspace_edges=workspace_edges,
            project_path=project_path,
            visited_node_ids=next_visited,
        )
        if resolved:
            return resolved
    path_edge = _incoming_edge_for_port(node=node, port_key="path", workspace_edges=workspace_edges)
    if path_edge is not None:
        source_node = workspace_nodes.get(str(getattr(path_edge, "source_node_id", "")).strip())
        resolved = _resolve_static_path_from_output_source(
            source_node,
            source_port_key=str(getattr(path_edge, "source_port_key", "")).strip(),
            workspace_nodes=workspace_nodes,
            workspace_edges=workspace_edges,
            project_path=project_path,
            visited_node_ids=next_visited,
        )
        if resolved:
            return resolved
    return _node_path_property(node, project_path=project_path)


def _resolve_static_path_from_output_source(
    node: Any | None,
    *,
    source_port_key: str,
    workspace_nodes: Mapping[str, Any],
    workspace_edges: Mapping[str, Any] | Iterable[Any] | None,
    project_path: str | None,
    visited_node_ids: frozenset[str],
) -> str:
    if node is None:
        return ""
    node_type_id = str(getattr(node, "type_id", "")).strip()
    if node_type_id == DPF_RESULT_FILE_NODE_TYPE_ID:
        return _resolve_dpf_result_path_from_result_file_node(
            node,
            workspace_nodes=workspace_nodes,
            workspace_edges=workspace_edges,
            project_path=project_path,
            visited_node_ids=visited_node_ids,
        )
    if node_type_id == DPF_MODEL_NODE_TYPE_ID:
        return _resolve_dpf_result_path_from_model_node(
            node,
            workspace_nodes=workspace_nodes,
            workspace_edges=workspace_edges,
            project_path=project_path,
            visited_node_ids=visited_node_ids,
        )
    if str(source_port_key or "").strip() in _DPF_PATH_LIKE_PORT_KEYS:
        return _node_path_property(node, project_path=project_path)
    return ""


@lru_cache(maxsize=32)
def _cached_dpf_named_selection_options(result_path: str, _mtime_ns: int) -> tuple[str, ...]:
    try:
        dpf = load_dpf_module(importlib.import_module)
        model = dpf.Model(result_path)
        return _dedupe_text_values(getattr(model.metadata, "available_named_selections", ()))
    except Exception:
        return ()


def _available_dpf_named_selection_options(result_path: str) -> tuple[str, ...]:
    normalized_path = _resolve_candidate_path(result_path, project_path=None)
    if not normalized_path:
        return ()
    try:
        modified_time_ns = int(Path(normalized_path).stat().st_mtime_ns)
    except OSError:
        return ()
    return _cached_dpf_named_selection_options(normalized_path, modified_time_ns)


def _dynamic_property_item_overrides(
    *,
    node: Any,
    prop: Any,
    workspace_nodes: Mapping[str, Any] | None,
    workspace_edges: Mapping[str, Any] | Iterable[Any] | None,
    project_path: str | None,
    dpf_named_selection_provider: Callable[[str], Iterable[str]] | None,
) -> dict[str, Any]:
    if (
        str(getattr(node, "type_id", "")).strip() != DPF_MESH_SCOPING_NODE_TYPE_ID
        or str(getattr(prop, "key", "")).strip() != "named_selection"
    ):
        return {}

    selection_mode = str(
        _property_text(node, "selection_mode") or DPF_MESH_SELECTION_NAMED_SELECTION
    ).strip().lower()
    if selection_mode != DPF_MESH_SELECTION_NAMED_SELECTION:
        return {}

    resolved_workspace_nodes = dict(workspace_nodes or {})
    model_edge = _incoming_edge_for_port(node=node, port_key="model", workspace_edges=workspace_edges)
    result_path = ""
    if model_edge is not None:
        source_node = resolved_workspace_nodes.get(str(getattr(model_edge, "source_node_id", "")).strip())
        result_path = _resolve_static_path_from_output_source(
            source_node,
            source_port_key=str(getattr(model_edge, "source_port_key", "")).strip(),
            workspace_nodes=resolved_workspace_nodes,
            workspace_edges=workspace_edges,
            project_path=project_path,
            visited_node_ids=frozenset(),
        )

    provider = dpf_named_selection_provider or _available_dpf_named_selection_options
    try:
        options = _dedupe_text_values(provider(result_path)) if result_path else ()
    except Exception:
        options = ()
    return {
        "editor_mode": "editable_combo",
        "enum_values": list(options),
        "placeholder_text": "No named selections found" if result_path and not options else "",
    }


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
                    "side": port.side,
                    "exposed": bool(port.exposed),
                }
                for port in ordered_ports_for_display(spec.ports)
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


def build_selected_node_header_data(
    *,
    node: Any,
    spec: Any,
    workflow_nodes: Mapping[str, Any],
) -> dict[str, Any]:
    title = str(getattr(node, "title", "")).strip() or str(getattr(spec, "display_name", "")).strip()
    display_name = str(getattr(spec, "display_name", "")).strip()
    description = str(getattr(spec, "description", "")).strip()
    subtitle = display_name if title != display_name and display_name else description

    instance_number = build_user_facing_node_instance_number(
        node=node,
        workflow_nodes=workflow_nodes,
    )

    metadata_items: list[dict[str, str]] = []
    category = str(getattr(spec, "category", "")).strip()
    if category:
        metadata_items.append({"label": "Category", "value": category})
    metadata_items.append({"label": "ID", "value": str(instance_number)})

    return {
        "title": title,
        "subtitle": subtitle,
        "metadata_items": metadata_items,
    }


def build_selected_node_property_items(
    *,
    node: Any,
    spec: Any,
    subnode_pin_type_ids: set[str],
    workspace_nodes: Mapping[str, Any] | None = None,
    workspace_edges: Mapping[str, Any] | Iterable[Any] | None = None,
    port_connection_counts: Mapping[tuple[str, str], int] | None = None,
    file_issues_by_key: Mapping[str, Any] | None = None,
    project_path: str | None = None,
    dpf_named_selection_provider: Callable[[str], Iterable[str]] | None = None,
) -> list[dict[str, Any]]:
    if node.type_id in subnode_pin_type_ids:
        ordered_keys = ("label", "kind", "data_type")
        ordered_properties = [
            prop
            for key in ordered_keys
            for prop in spec.properties
            if prop.key == key and property_visible_in_inspector(prop)
        ]
    else:
        ordered_properties = [prop for prop in spec.properties if property_visible_in_inspector(prop)]
    issue_lookup = dict(file_issues_by_key or {})
    resolved_workspace_nodes = dict(workspace_nodes or {}) or {str(getattr(node, "node_id", "")).strip(): node}
    resolved_input_ports = {
        port.key: port
        for port in effective_ports(node=node, spec=spec, workspace_nodes=resolved_workspace_nodes)
        if str(port.direction).strip().lower() == "in" and bool(port.exposed)
    }
    items: list[dict[str, Any]] = []
    for prop in ordered_properties:
        item = {
            "key": prop.key,
            "label": prop.label,
            "type": prop.type,
            "value": node.properties.get(prop.key, prop.default),
            "enum_values": list(prop.enum_values),
            "inline_editor": prop.inline_editor,
            "editor_mode": property_inspector_editor(prop),
        }
        item.update(
            _dynamic_property_item_overrides(
                node=node,
                prop=prop,
                workspace_nodes=resolved_workspace_nodes,
                workspace_edges=workspace_edges,
                project_path=project_path,
                dpf_named_selection_provider=dpf_named_selection_provider,
            )
        )
        item.update(
            build_property_input_override_state(
                node=node,
                property_key=prop.key,
                resolved_input_ports=resolved_input_ports,
                port_connection_counts=port_connection_counts,
            )
        )
        item.update(build_file_issue_payload(issue_lookup.get(prop.key)))
        items.append(item)
    return items


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
            "side": port.side,
            "required": bool(port.required),
            "exposed": bool(port.exposed),
        }
        for port in ordered_ports_for_display(
            effective_ports(node=node, spec=spec, workspace_nodes=workspace_nodes)
        )
    ]


def _normalized_library_ports(item: dict[str, Any]) -> list[dict[str, Any]]:
    ports = item.get("ports", [])
    if not isinstance(ports, list):
        return []
    return [port for port in ports if isinstance(port, dict)]


def _library_item_matches_query(item: dict[str, Any], *, query: str, compatible_ports: list[dict[str, Any]]) -> bool:
    normalized_query = str(query).strip().lower()
    if not normalized_query:
        return True
    haystack = " ".join(
        [
            str(item.get("type_id", "")),
            str(item.get("display_name", "")),
            str(item.get("category", "")),
            str(item.get("description", "")),
            " ".join(str(port.get("key", "")) for port in compatible_ports),
            " ".join(str(port.get("label", "")) for port in compatible_ports),
        ]
    ).lower()
    return normalized_query in haystack


def _is_neutral_flow_library_port(port: dict[str, Any]) -> bool:
    direction = str(port.get("direction", "")).strip().lower()
    kind = str(port.get("kind", "")).strip().lower()
    data_type = str(port.get("data_type", "")).strip().lower()
    return direction == "neutral" and kind == "flow" and data_type == "flow"


def _compatible_library_ports(
    item: dict[str, Any],
    *,
    source_direction: str,
    source_kind: str,
    source_data_type: str,
) -> list[dict[str, Any]]:
    normalized_source_direction = str(source_direction).strip().lower()
    normalized_source_kind = str(source_kind).strip().lower()
    normalized_source_data_type = str(source_data_type).strip().lower() or "any"
    source_is_neutral_flow = (
        normalized_source_direction == "neutral"
        and normalized_source_kind == "flow"
        and normalized_source_data_type == "flow"
    )
    compatible_ports: list[dict[str, Any]] = []
    for port in _normalized_library_ports(item):
        direction = str(port.get("direction", "")).strip().lower()
        kind = str(port.get("kind", "")).strip().lower()
        data_type = str(port.get("data_type", "")).strip().lower() or "any"
        if source_is_neutral_flow:
            if not _is_neutral_flow_library_port(port):
                continue
        elif normalized_source_direction == "out":
            if direction != "in":
                continue
            if not are_port_kinds_compatible(source_kind, kind):
                continue
            if not are_data_types_compatible(source_data_type, data_type):
                continue
        elif normalized_source_direction == "in":
            if direction != "out":
                continue
            if not are_port_kinds_compatible(kind, source_kind):
                continue
            if not are_data_types_compatible(data_type, source_data_type):
                continue
        else:
            continue
        compatible_ports.append(port)
    return compatible_ports


def _connection_quick_insert_rank(query: str, *, display_name: str, type_id: str) -> int:
    normalized_query = str(query).strip().lower()
    if not normalized_query:
        return 100
    name = str(display_name).strip().lower()
    node_type_id = str(type_id).strip().lower()
    if name == normalized_query:
        return 0
    if name.startswith(normalized_query):
        return 10
    if normalized_query in name:
        return 20
    if node_type_id.startswith(normalized_query):
        return 30
    if normalized_query in node_type_id:
        return 40
    return 100


def build_connection_quick_insert_items(
    *,
    combined_items: Iterable[dict[str, Any]],
    query: str,
    source_direction: str,
    source_kind: str,
    source_data_type: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for item in combined_items:
        compatible_ports = _compatible_library_ports(
            item,
            source_direction=source_direction,
            source_kind=source_kind,
            source_data_type=source_data_type,
        )
        if not compatible_ports:
            continue
        if not _library_item_matches_query(item, query=query, compatible_ports=compatible_ports):
            continue
        payload = dict(item)
        payload["compatible_ports"] = compatible_ports
        payload["compatible_port_labels"] = [
            str(port.get("label", "")).strip() or str(port.get("key", "")).strip()
            for port in compatible_ports
        ]
        payload["compatible_port_count"] = len(compatible_ports)
        normalized_source_direction = str(source_direction).strip().lower()
        if normalized_source_direction == "out":
            payload["compatible_direction"] = "in"
        elif normalized_source_direction == "in":
            payload["compatible_direction"] = "out"
        else:
            payload["compatible_direction"] = "neutral"
        ranked.append(
            (
                _connection_quick_insert_rank(
                    query,
                    display_name=str(item.get("display_name", "")),
                    type_id=str(item.get("type_id", "")),
                )
                + max(0, len(compatible_ports) - 1),
                str(item.get("display_name", "")).lower(),
                payload,
            )
        )
    ranked.sort(key=lambda entry: (entry[0], entry[1], str(entry[2].get("type_id", "")).lower()))
    capped = max(1, int(limit))
    return [entry[2] for entry in ranked[:capped]]


def build_canvas_quick_insert_items(
    *,
    combined_items: Iterable[dict[str, Any]],
    query: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    normalized_query = str(query).strip()
    if not normalized_query:
        return []
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for item in combined_items:
        if not _library_item_matches_query(item, query=normalized_query, compatible_ports=[]):
            continue
        payload = dict(item)
        payload["compatible_ports"] = []
        payload["compatible_port_labels"] = []
        payload["compatible_port_count"] = 0
        payload["compatible_direction"] = ""
        ranked.append(
            (
                _connection_quick_insert_rank(
                    normalized_query,
                    display_name=str(item.get("display_name", "")),
                    type_id=str(item.get("type_id", "")),
                ),
                str(item.get("display_name", "")).lower(),
                payload,
            )
        )
    ranked.sort(key=lambda entry: (entry[0], entry[1], str(entry[2].get("type_id", "")).lower()))
    capped = max(1, int(limit))
    return [entry[2] for entry in ranked[:capped]]
