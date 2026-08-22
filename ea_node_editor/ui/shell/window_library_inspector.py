from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ea_node_editor.addons.catalog import create_live_property_edit_adapters
from ea_node_editor.addons.property_edit_adapters import (
    AddOnPropertyEditAdapter,
    PropertyEditAdapterContext,
    build_property_items_with_adapters,
)
from ea_node_editor.nodes.category_paths import (
    CategoryPath,
    category_display,
    category_key,
    category_path_ancestors,
    category_path_matches_prefix,
    normalize_category_path,
)
from ea_node_editor.custom_workflows import CUSTOM_WORKFLOW_LIBRARY_CATEGORY
from ea_node_editor.graph.effective_ports import (
    effective_ports,
    ordered_ports_for_display,
    ports_compatible,
)
from ea_node_editor.graph.file_issue_state import (
    EXTERNAL_LINK_MODE,
    MANAGED_COPY_MODE,
    build_file_issue_payload,
    preferred_repair_mode_for_value,
    repair_modes_for_node_property,
)
from ea_node_editor.ui.support.node_presentation import (
    build_property_input_override_state,
    build_inline_property_items,
    build_user_facing_node_instance_number,
    project_port_data_type_presentation,
    qml_safe_spec_property_value,
)
from ea_node_editor.nodes.node_specs import (
    PortSpec,
    property_inspector_editor,
    property_visible_in_inspector,
)
from ea_node_editor.runtime_contracts import (
    BOOLEAN_DATA_TYPE_ID,
    DataTypeCatalog,
    DOUBLE_DATA_TYPE_ID,
    GRAPH_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    JSON_DATA_TYPE_ID,
    PATH_DATA_TYPE_ID,
    STRING_DATA_TYPE_ID,
)

_PATH_LIKE_PORT_KEYS = frozenset({"normalized_path", "written_path", "path"})
_DEFAULT_LIBRARY_CATEGORY = "Other"
_CUSTOM_WORKFLOW_LIBRARY_CATEGORY_PATH = (CUSTOM_WORKFLOW_LIBRARY_CATEGORY,)
_FOLDER_PATH_PROPERTIES_BY_TYPE = frozenset(
    {
        ("io.folder_explorer", "current_path"),
    }
)
_GRAPH_SURFACE_METRIC_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "ui_qml"
    / "components"
    / "graph"
    / "GraphNodeSurfaceMetricContract.json"
)
_FALLBACK_FLOWCHART_LIBRARY_ASPECT_RATIOS = {
    "start": 152.0 / 78.0,
    "end": 152.0 / 78.0,
    "process": 156.0 / 84.0,
    "decision": 192.0 / 128.0,
    "document": 176.0 / 104.0,
    "connector": 1.0,
    "input_output": 182.0 / 94.0,
    "predefined_process": 182.0 / 94.0,
    "database": 180.0 / 128.0,
    "card": 132.0 / 200.0,
    "callout": 196.0 / 120.0,
    "multi_document": 176.0 / 128.0,
    "tick": 1.0,
    "timestamp": 220.0 / 72.0,
    "message": 160.0 / 112.0,
    "isometric_cube": 1.0,
    "cube": 220.0 / 132.0,
    "actor": 116.0 / 156.0,
    "star": 1.0,
    "x": 1.0,
}


def _positive_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return None
    return numeric


@lru_cache(maxsize=1)
def _flowchart_library_aspect_ratios() -> dict[str, float]:
    ratios = dict(_FALLBACK_FLOWCHART_LIBRARY_ASPECT_RATIOS)
    try:
        contract = json.loads(
            _GRAPH_SURFACE_METRIC_CONTRACT_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return ratios

    flowchart = contract.get("flowchart", {})
    variants = flowchart.get("variants", {}) if isinstance(flowchart, Mapping) else {}
    if not isinstance(variants, Mapping):
        return ratios

    for variant, metrics in variants.items():
        if not isinstance(metrics, Mapping):
            continue
        default_width = _positive_float(metrics.get("default_width"))
        min_height = _positive_float(metrics.get("min_height"))
        if default_width is None or min_height is None:
            continue
        ratios[str(variant)] = default_width / min_height
    return ratios


def _flowchart_library_aspect_ratio(surface_variant: str) -> float:
    return float(_flowchart_library_aspect_ratios().get(surface_variant, 1.7))


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


def _resolve_static_path_from_output_source(
    node: Any | None,
    *,
    source_port_key: str,
    project_path: str | None,
) -> str:
    if node is None:
        return ""
    if str(source_port_key or "").strip() in _PATH_LIKE_PORT_KEYS:
        return _resolve_candidate_path(
            _property_text(node, "path"), project_path=project_path
        )
    return ""


def _source_path_for_node_property(
    *,
    node: Any,
    property_key: str,
    workspace_nodes: Mapping[str, Any],
    workspace_edges: Mapping[str, Any] | Iterable[Any] | None,
    project_path: str | None,
) -> str:
    normalized_property_key = str(property_key or "").strip()
    if not normalized_property_key:
        return ""
    raw_node_path = _property_text(node, normalized_property_key)
    if raw_node_path:
        if "://" in raw_node_path or Path(raw_node_path).expanduser().is_absolute():
            return raw_node_path
        return _resolve_candidate_path(raw_node_path, project_path=project_path)
    path_edge = _incoming_edge_for_port(
        node=node,
        port_key=normalized_property_key,
        workspace_edges=workspace_edges,
    )
    if path_edge is None:
        return ""
    source_node = workspace_nodes.get(
        str(getattr(path_edge, "source_node_id", "")).strip()
    )
    return _resolve_static_path_from_output_source(
        source_node,
        source_port_key=str(getattr(path_edge, "source_port_key", "")).strip(),
        project_path=project_path,
    )


def _path_property_dialog_mode(*, node: Any, prop: Any) -> str:
    node_type_id = str(getattr(node, "type_id", "")).strip()
    property_key = str(getattr(prop, "key", "")).strip()
    if (node_type_id, property_key) == ("web.page_viewer", "start_location"):
        return "file"

    if str(getattr(prop, "type", "")).strip() != "path":
        return ""

    if (node_type_id, property_key) in _FOLDER_PATH_PROPERTIES_BY_TYPE:
        return "folder"

    if node_type_id == "io.path_pointer" and property_key == "path":
        properties = getattr(node, "properties", None)
        if hasattr(properties, "get"):
            mode = str(properties.get("mode", "file")).strip().lower()
            if mode == "folder":
                return "folder"

    return "file"


def _path_property_source_modes(*, node: Any, prop: Any) -> tuple[str, ...]:
    node_type_id = str(getattr(node, "type_id", "")).strip()
    property_key = str(getattr(prop, "key", "")).strip()
    if (node_type_id, property_key) == ("web.page_viewer", "start_location"):
        return (MANAGED_COPY_MODE, EXTERNAL_LINK_MODE)

    if str(getattr(prop, "type", "")).strip() != "path":
        return ()
    return repair_modes_for_node_property(
        node_type_id,
        property_key,
    )


def _category_sort_key(path: Iterable[str]) -> tuple[tuple[str, ...], CategoryPath]:
    normalized_path = normalize_category_path(tuple(path))
    return tuple(segment.casefold() for segment in normalized_path), normalized_path


def _category_metadata(path: Iterable[str]) -> dict[str, Any]:
    normalized_path = normalize_category_path(tuple(path))
    display = category_display(normalized_path)
    key = category_key(normalized_path)
    return {
        "category_path": normalized_path,
        "category_key": key,
        "category_display": display,
        "root_category": normalized_path[0],
        "category": display,
    }


def _category_path_from_item(item: Mapping[str, Any]) -> CategoryPath:
    raw_path = item.get("category_path")
    if raw_path is not None and not isinstance(raw_path, str):
        try:
            return normalize_category_path(tuple(raw_path))
        except (TypeError, ValueError):
            pass

    fallback_category = str(
        item.get("category_display")
        or item.get("category")
        or (
            CUSTOM_WORKFLOW_LIBRARY_CATEGORY
            if str(item.get("library_source", "")).strip() == "custom_workflow"
            else _DEFAULT_LIBRARY_CATEGORY
        )
    ).strip()
    return normalize_category_path((fallback_category or _DEFAULT_LIBRARY_CATEGORY,))


def _project_library_item_payload(
    item: Mapping[str, Any],
    *,
    data_type_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(item)
    payload.update(_category_metadata(_category_path_from_item(payload)))
    ports = payload.get("ports", [])
    projected_ports: list[Any] = []
    for port in ports if isinstance(ports, list) else ():
        if not isinstance(port, Mapping):
            projected_ports.append(port)
            continue
        projected_port = dict(port)
        if data_type_projection is not None or "catalog_generation" not in port:
            projected_port.update(
                project_port_data_type_presentation(
                    data_type=port.get("data_type", ""),
                    accepted_data_types=tuple(
                        port.get("accepted_data_types", ()) or ()
                    ),
                    data_access=port.get("data_access", "item"),
                    kind=port.get("kind", "data"),
                    projection=data_type_projection,
                )
            )
        projected_ports.append(projected_port)
    payload["ports"] = projected_ports
    library_visual = payload.get("library_visual")
    payload["library_visual"] = (
        dict(library_visual)
        if isinstance(library_visual, Mapping)
        else {"kind": "none"}
    )
    return payload


def _library_visual_from_spec(spec: Any) -> dict[str, Any]:
    runtime_behavior = str(getattr(spec, "runtime_behavior", "") or "").strip().lower()
    surface_family = str(getattr(spec, "surface_family", "") or "").strip().lower()
    surface_variant = str(getattr(spec, "surface_variant", "") or "").strip().lower()
    icon = str(getattr(spec, "icon", "") or "").strip()
    visual: dict[str, Any] = {
        "kind": "none",
        "runtime_behavior": runtime_behavior,
        "surface_family": surface_family,
        "surface_variant": surface_variant,
        "shape_id": "",
        "icon": icon,
    }
    if runtime_behavior != "passive":
        if icon:
            visual["kind"] = "catalog_icon"
        return visual
    if surface_family == "flowchart" and surface_variant:
        visual["kind"] = "flowchart_shape"
        visual["shape_id"] = surface_variant
        visual["icon"] = ""
        visual["aspect_ratio"] = _flowchart_library_aspect_ratio(surface_variant)
        return visual
    if icon:
        visual["kind"] = "catalog_icon"
    return visual


def _is_passive_library_item(item: Mapping[str, Any]) -> bool:
    return str(item.get("runtime_behavior", "") or "").strip().lower() == "passive"


def _category_filter_prefix(value: str) -> CategoryPath | None:
    normalized_value = str(value or "").strip()
    if not normalized_value:
        return None
    try:
        decoded = json.loads(normalized_value)
    except json.JSONDecodeError:
        return None
    if isinstance(decoded, list):
        try:
            return normalize_category_path(tuple(decoded))
        except (TypeError, ValueError):
            return None
    return None


def _item_matches_category_filter(item: Mapping[str, Any], category: str) -> bool:
    normalized_category = str(category or "").strip()
    if not normalized_category:
        return True

    item_path = _category_path_from_item(item)
    prefix = _category_filter_prefix(normalized_category)
    if prefix is not None:
        return category_path_matches_prefix(item_path, prefix)

    category_display_filter = normalized_category.casefold()
    return any(
        category_display(ancestor).casefold() == category_display_filter
        for ancestor in category_path_ancestors(item_path)
    )


def _ancestor_category_keys(path: Iterable[str], *, include_self: bool) -> list[str]:
    ancestors = list(category_path_ancestors(normalize_category_path(tuple(path))))
    if not include_self:
        ancestors = ancestors[:-1]
    return [category_key(ancestor) for ancestor in ancestors]


def _category_row(path: Iterable[str]) -> dict[str, Any]:
    normalized_path = normalize_category_path(tuple(path))
    payload = _category_metadata(normalized_path)
    payload.update(
        {
            "kind": "category",
            "label": normalized_path[-1],
            "depth": len(normalized_path) - 1,
            "ancestor_category_keys": _ancestor_category_keys(
                normalized_path, include_self=False
            ),
        }
    )
    return payload


def _node_row(item: Mapping[str, Any]) -> dict[str, Any]:
    payload = _project_library_item_payload(item)
    category_path = _category_path_from_item(payload)
    payload.update(
        {
            "kind": "node",
            "label": str(payload.get("display_name", "")).strip(),
            "depth": len(category_path),
            "ancestor_category_keys": _ancestor_category_keys(
                category_path, include_self=True
            ),
        }
    )
    return payload


def _registry_library_item_from_spec(spec: Any) -> dict[str, Any]:
    return {
        "type_id": spec.type_id,
        "display_name": spec.display_name,
        **_category_metadata(spec.category_path),
        "icon": spec.icon,
        "runtime_behavior": str(getattr(spec, "runtime_behavior", "") or ""),
        "surface_family": str(getattr(spec, "surface_family", "") or ""),
        "surface_variant": str(getattr(spec, "surface_variant", "") or ""),
        "library_visual": _library_visual_from_spec(spec),
        "description": spec.description,
        "keywords": list(getattr(spec, "keywords", ()) or ()),
        "library_source": "node_registry",
        "ports": [
            {
                "key": port.key,
                "label": str(getattr(port, "label", "") or port.key),
                "description": str(getattr(port, "description", "") or ""),
                "direction": port.direction,
                "kind": port.kind,
                "data_type": port.data_type,
                "data_access": str(
                    getattr(port, "data_access", "item") or "item"
                ),
                "accepted_data_types": list(
                    getattr(port, "accepted_data_types", ()) or ()
                ),
                "side": port.side,
                "exposed": bool(port.exposed),
            }
            for port in ordered_ports_for_display(spec.ports)
        ],
    }


def build_registry_library_items(
    *,
    registry_specs: Iterable[Any] = (),
    data_type_projection: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        _project_library_item_payload(
            _registry_library_item_from_spec(spec),
            data_type_projection=data_type_projection,
        )
        for spec in registry_specs
    ]


def build_combined_library_items(
    *,
    registry_items: Iterable[dict[str, Any]],
    custom_workflow_items: Iterable[dict[str, Any]],
    data_type_projection: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    items = [
        _project_library_item_payload(
            item,
            data_type_projection=data_type_projection,
        )
        for item in registry_items
    ]
    items.extend(
        _project_library_item_payload(
            item,
            data_type_projection=data_type_projection,
        )
        for item in custom_workflow_items
    )
    items.sort(
        key=lambda item: (
            _category_sort_key(_category_path_from_item(item)),
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
    if not _item_matches_category_filter(item, category):
        return False

    ports = item.get("ports", [])
    normalized_ports = ports if isinstance(ports, list) else []

    if data_type or direction:
        matches_port = False
        for port in normalized_ports:
            if not isinstance(port, dict):
                continue
            port_direction = str(port.get("direction", "")).strip().lower()
            if direction and port_direction != direction:
                continue
            if data_type and not any(
                declared_type.casefold() == data_type.casefold()
                for declared_type in _library_port_declared_data_types(port)
            ):
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
            str(item.get("category_display", "")),
            str(item.get("description", "")),
            " ".join(
                str(port.get("key", ""))
                for port in normalized_ports
                if isinstance(port, dict)
            ),
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
    normalized_category = str(category).strip()
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


def build_grouped_library_items(
    *, filtered_items: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    trie: dict[str, Any] = {"path": (), "children": {}, "items": []}
    for item in filtered_items:
        payload = _project_library_item_payload(item)
        node = trie
        current_path: CategoryPath = ()
        for segment in _category_path_from_item(payload):
            current_path = (*current_path, segment)
            children = node["children"]
            node = children.setdefault(
                segment, {"path": current_path, "children": {}, "items": []}
            )
        node["items"].append(payload)

    payload: list[dict[str, Any]] = []

    def _append_node(node: dict[str, Any]) -> None:
        path = node["path"]
        if path:
            payload.append(_category_row(path))
        for child_segment in sorted(
            node["children"],
            key=lambda segment: (str(segment).casefold(), str(segment)),
        ):
            _append_node(node["children"][child_segment])
        for node_item in sorted(
            node["items"],
            key=lambda item: (
                str(item.get("display_name", "")).casefold(),
                str(item.get("type_id", "")).casefold(),
            ),
        ):
            payload.append(_node_row(node_item))

    _append_node(trie)
    return payload


def _passive_icon_grid_row(
    *,
    category_path: CategoryPath,
    items: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    effective_path = category_path or (_DEFAULT_LIBRARY_CATEGORY,)
    payload = _category_metadata(effective_path)
    payload.update(
        {
            "kind": "passive_icon_grid",
            "label": "",
            "depth": len(effective_path),
            "ancestor_category_keys": _ancestor_category_keys(
                effective_path, include_self=True
            ),
            "items": [_node_row(item) for item in items],
        }
    )
    return payload


def build_display_library_items(
    *,
    filtered_items: Iterable[dict[str, Any]],
    passive_node_library_display_mode: str,
) -> list[dict[str, Any]]:
    if str(passive_node_library_display_mode).strip().lower() != "icon":
        return build_grouped_library_items(filtered_items=filtered_items)

    trie: dict[str, Any] = {"path": (), "children": {}, "items": []}
    for item in filtered_items:
        payload = _project_library_item_payload(item)
        node = trie
        current_path: CategoryPath = ()
        for segment in _category_path_from_item(payload):
            current_path = (*current_path, segment)
            children = node["children"]
            node = children.setdefault(
                segment, {"path": current_path, "children": {}, "items": []}
            )
        node["items"].append(payload)

    payload: list[dict[str, Any]] = []

    def _sort_key(item: Mapping[str, Any]) -> tuple[str, str]:
        return (
            str(item.get("display_name", "")).casefold(),
            str(item.get("type_id", "")).casefold(),
        )

    def _append_node(node: dict[str, Any]) -> None:
        path = node["path"]
        if path:
            payload.append(_category_row(path))
        for child_segment in sorted(
            node["children"],
            key=lambda segment: (str(segment).casefold(), str(segment)),
        ):
            _append_node(node["children"][child_segment])
        sorted_items = sorted(node["items"], key=_sort_key)
        passive_items = [
            item for item in sorted_items if _is_passive_library_item(item)
        ]
        for node_item in sorted_items:
            if _is_passive_library_item(node_item):
                continue
            payload.append(_node_row(node_item))
        if passive_items:
            payload.append(
                _passive_icon_grid_row(category_path=path, items=passive_items)
            )

    _append_node(trie)
    return payload


def build_library_category_options(
    *,
    combined_items: Iterable[dict[str, Any]],
    registry_categories: Iterable[Any],
) -> list[dict[str, Any]]:
    paths: set[CategoryPath] = set()
    display_lookup: dict[str, set[CategoryPath]] = {}

    def _add_path(path: Iterable[str]) -> None:
        normalized_path = normalize_category_path(tuple(path))
        for ancestor in category_path_ancestors(normalized_path):
            paths.add(ancestor)
            display_lookup.setdefault(category_display(ancestor).casefold(), set()).add(
                ancestor
            )

    for item in combined_items:
        item_path = _category_path_from_item(item)
        _add_path(item_path)

    for raw_category in registry_categories:
        if isinstance(raw_category, str):
            normalized_category = raw_category.strip()
            if not normalized_category:
                continue
            matched_paths = display_lookup.get(normalized_category.casefold())
            if matched_paths:
                for path in matched_paths:
                    _add_path(path)
            else:
                _add_path(normalize_category_path((normalized_category,)))
            continue
        try:
            normalized_path = normalize_category_path(tuple(raw_category))
        except (TypeError, ValueError):
            continue
        _add_path(normalized_path)

    _add_path(_CUSTOM_WORKFLOW_LIBRARY_CATEGORY_PATH)
    return [{"label": "All Categories", "value": ""}] + [
        {
            "label": category_display(path),
            "value": category_key(path),
            "category_path": path,
            "category_key": category_key(path),
            "depth": len(path) - 1,
            "root_category": path[0],
        }
        for path in sorted(paths, key=_category_sort_key)
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
        type_id
        for spec in registry_specs
        for port in spec.ports
        for type_id in (
            str(port.data_type).strip(),
            *(
                str(value).strip()
                for value in (
                    getattr(port, "accepted_data_types", ()) or ()
                )
            ),
        )
        if type_id
    }
    for item in custom_workflow_items:
        ports = item.get("ports", [])
        if not isinstance(ports, list):
            continue
        for port in ports:
            if not isinstance(port, dict):
                continue
            data_types.update(_library_port_declared_data_types(port))
    return [{"label": "Any Data Type", "value": ""}] + [
        {"label": data_type, "value": data_type}
        for data_type in sorted(data_types, key=lambda value: (value.casefold(), value))
    ]


def build_pin_data_type_options(
    *,
    registry_specs: Iterable[Any],
    workspaces: Iterable[Any],
    subnode_pin_type_ids: set[str],
    subnode_pin_data_type_property: str,
) -> list[str]:
    suggested = {
        GRAPH_DATA_TYPE_ID,
        STRING_DATA_TYPE_ID,
        INTEGER_DATA_TYPE_ID,
        DOUBLE_DATA_TYPE_ID,
        BOOLEAN_DATA_TYPE_ID,
        JSON_DATA_TYPE_ID,
        PATH_DATA_TYPE_ID,
    }
    suggested.update(
        type_id
        for spec in registry_specs
        for port in spec.ports
        for type_id in (
            str(port.data_type).strip(),
            *(
                str(value).strip()
                for value in (
                    getattr(port, "accepted_data_types", ()) or ()
                )
            ),
        )
        if type_id
    )
    for workspace in workspaces:
        for node in workspace.nodes.values():
            if node.type_id not in subnode_pin_type_ids:
                continue
            value = str(
                node.properties.get(subnode_pin_data_type_property, "")
            ).strip()
            if value:
                suggested.add(value)
    ordered = [GRAPH_DATA_TYPE_ID]
    suggested.discard(GRAPH_DATA_TYPE_ID)
    ordered.extend(sorted(suggested, key=lambda value: (value.casefold(), value)))
    return ordered


def build_selected_node_header_data(
    *,
    node: Any,
    spec: Any,
    workflow_nodes: Mapping[str, Any],
) -> dict[str, Any]:
    title = (
        str(getattr(node, "title", "")).strip()
        or str(getattr(spec, "display_name", "")).strip()
    )
    display_name = str(getattr(spec, "display_name", "")).strip()
    description = str(getattr(spec, "description", "")).strip()
    subtitle = display_name if title != display_name and display_name else description

    instance_number = build_user_facing_node_instance_number(
        node=node,
        workflow_nodes=workflow_nodes,
    )

    metadata_items: list[dict[str, str]] = []
    category = str(getattr(spec, "category", "")).strip()
    category_path = getattr(spec, "category_path", None)
    if category_path is not None:
        try:
            category = category_display(category_path)
        except (TypeError, ValueError):
            pass
    if category:
        metadata_items.append({"label": "Category", "value": category})
    metadata_items.append({"label": "ID", "value": str(instance_number)})

    return {
        "title": title,
        "subtitle": subtitle,
        "metadata_items": metadata_items,
    }


_LINK_KIND_META = {
    "url": ("Web", "world-www", "#3BA9F5"),
    "file": ("File", "file-text", "#8B7CF6"),
    "folder": ("Folder", "folder", "#F2B84B"),
    "workspace": ("Workspace", "layout-dashboard", "#64C88A"),
    "node": ("Node", "hierarchy-2", "#60CDFF"),
}


def _link_target_breadcrumb(
    *,
    kind: str,
    target: str,
    workspace_nodes: Mapping[str, Any],
    workspaces: Mapping[str, Any],
    target_workspace_id: str = "",
    target_node_id: str = "",
) -> str:
    if kind == "url":
        parsed = urlparse(target)
        return parsed.netloc or target
    if kind in {"file", "folder"}:
        try:
            return Path(target).name or target
        except (OSError, ValueError):
            return target
    if kind == "node":
        normalized_node_id = str(target_node_id or target).strip()
        normalized_workspace_id = str(target_workspace_id or "").strip()
        target_workspace = (
            workspaces.get(normalized_workspace_id) if normalized_workspace_id else None
        )
        target_nodes = (
            getattr(target_workspace, "nodes", None)
            if target_workspace is not None
            else None
        )
        target_node = (
            target_nodes.get(normalized_node_id)
            if isinstance(target_nodes, Mapping)
            else workspace_nodes.get(normalized_node_id)
        )
        if target_node is None:
            return "Missing node"
        parts: list[str] = []
        workspace_name = str(getattr(target_workspace, "name", "") or "").strip()
        if workspace_name:
            parts.append(workspace_name)
        title = str(
            getattr(target_node, "title", "")
            or getattr(target_node, "type_id", "")
            or normalized_node_id
        )
        parts.append(title)
        return " - ".join(parts)
    if kind == "workspace":
        target_workspace = workspaces.get(target)
        if target_workspace is None:
            return "Missing workspace"
        return str(getattr(target_workspace, "name", "") or target)
    return target


def build_selected_node_link_items(
    *,
    node: Any,
    workspace_nodes: Mapping[str, Any] | None = None,
    workspaces: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_nodes = dict(workspace_nodes or {})
    resolved_workspaces = dict(workspaces or {})
    links = list(getattr(node, "links", []) or [])
    items: list[dict[str, Any]] = []
    for index, link in enumerate(links):
        kind = str(getattr(link, "kind", "") or "url").strip().lower() or "url"
        type_label, icon, type_color = _LINK_KIND_META.get(kind, _LINK_KIND_META["url"])
        target = str(getattr(link, "target", "") or "").strip()
        target_node_id = str(getattr(link, "target_node_id", "") or "").strip()
        target_workspace_id = str(
            getattr(link, "target_workspace_id", "") or ""
        ).strip()
        title = str(getattr(link, "title", "") or "").strip() or target or type_label
        subtitle = str(getattr(link, "subtitle", "") or "").strip()
        breadcrumb = subtitle or _link_target_breadcrumb(
            kind=kind,
            target=target,
            workspace_nodes=resolved_nodes,
            workspaces=resolved_workspaces,
            target_workspace_id=target_workspace_id,
            target_node_id=target_node_id,
        )
        items.append(
            {
                "id": str(getattr(link, "link_id", "") or "").strip(),
                "kind": kind,
                "title": title,
                "target": target,
                "target_node_id": target_node_id,
                "target_workspace_id": target_workspace_id,
                "subtitle": subtitle,
                "type_label": type_label,
                "breadcrumb": breadcrumb,
                "icon": icon,
                "type_color": type_color,
                "index": index,
                "can_move_up": index > 0,
                "can_move_down": index < len(links) - 1,
            }
        )
    return items


def build_selected_node_property_items(
    *,
    node: Any,
    spec: Any,
    subnode_pin_type_ids: set[str],
    workspace_id: str = "",
    workspace_nodes: Mapping[str, Any] | None = None,
    workspace_edges: Mapping[str, Any] | Iterable[Any] | None = None,
    port_connection_counts: Mapping[tuple[str, str], int] | None = None,
    file_issues_by_key: Mapping[str, Any] | None = None,
    project_path: str | None = None,
    project_metadata: Mapping[str, Any] | None = None,
    property_edit_adapters: Iterable[AddOnPropertyEditAdapter] | None = None,
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
        ordered_properties = [
            prop for prop in spec.properties if property_visible_in_inspector(prop)
        ]
    issue_lookup = dict(file_issues_by_key or {})
    resolved_workspace_nodes = dict(workspace_nodes or {}) or {
        str(getattr(node, "node_id", "")).strip(): node
    }
    adapters = (
        tuple(property_edit_adapters)
        if property_edit_adapters is not None
        else create_live_property_edit_adapters()
    )
    adapter_context = PropertyEditAdapterContext(
        node=node,
        spec=spec,
        workspace_id=str(workspace_id or ""),
        workspace_nodes=resolved_workspace_nodes,
        workspace_edges=workspace_edges,
        project_path=project_path,
        project_metadata=project_metadata,
        source_path_resolver=lambda source_node, property_key: (
            _source_path_for_node_property(
                node=source_node,
                property_key=property_key,
                workspace_nodes=resolved_workspace_nodes,
                workspace_edges=workspace_edges,
                project_path=project_path,
            )
        ),
    )
    resolved_input_ports = {
        port.key: port
        for port in effective_ports(
            node=node, spec=spec, workspace_nodes=resolved_workspace_nodes
        )
        if str(port.direction).strip().lower() == "in" and bool(port.exposed)
    }
    presentation_by_key = {
        str(item["key"]): item
        for item in build_inline_property_items(
            node=node,
            spec=spec,
            workspace_nodes=resolved_workspace_nodes,
            port_connection_counts=port_connection_counts,
        )
    }
    items: list[dict[str, Any]] = []
    sensitive_scope_keys = {
        str(getattr(candidate, "sensitive_scope_key", "") or "")
        for candidate in spec.properties
        if bool(getattr(candidate, "sensitive", False))
        and str(getattr(candidate, "sensitive_scope_key", "") or "")
    }
    for prop in ordered_properties:
        current_value = node.properties.get(prop.key, prop.default)
        safe_current_value = qml_safe_spec_property_value(prop, current_value)
        presentation = presentation_by_key.get(str(prop.key))
        item = {
            "key": prop.key,
            "label": prop.label,
            "type": prop.type,
            "value": safe_current_value,
            "display_value": safe_current_value,
            "enum_values": list(prop.enum_values),
            "inline_editor": prop.inline_editor,
            "editor_mode": (
                "interval_slider"
                if str(prop.inline_editor) == "interval_slider"
                else property_inspector_editor(prop)
            ),
            "group": getattr(prop, "group", "") or "Properties",
            "dirty": current_value != prop.default,
            "sensitive": bool(getattr(prop, "sensitive", False)),
            "sensitive_scope_key": str(
                getattr(prop, "sensitive_scope_key", "") or ""
            ),
            "reprotects_sensitive_properties": prop.key in sensitive_scope_keys,
        }
        help_text = str(getattr(prop, "description", "") or "")
        if help_text:
            item["help_text"] = help_text
        path_dialog_mode = _path_property_dialog_mode(node=node, prop=prop)
        if path_dialog_mode:
            item["path_dialog_mode"] = path_dialog_mode
        path_source_modes = _path_property_source_modes(node=node, prop=prop)
        if path_source_modes:
            item["path_source_modes"] = list(path_source_modes)
            item["path_supports_managed_copy"] = MANAGED_COPY_MODE in path_source_modes
            item["path_supports_external_link"] = (
                EXTERNAL_LINK_MODE in path_source_modes
            )
            item["path_current_source_mode"] = preferred_repair_mode_for_value(
                str(current_value or ""),
                project_path=project_path,
                project_metadata=project_metadata,
                fallback_mode=EXTERNAL_LINK_MODE,
                allowed_modes=path_source_modes,
            )
        if presentation is not None:
            item.update(presentation)
        else:
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
    return build_property_items_with_adapters(adapters, adapter_context, items)


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
            "accepted_data_types": list(port.accepted_data_types),
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


def _library_port_declared_data_types(port: Mapping[str, Any]) -> tuple[str, ...]:
    primary = str(port.get("data_type", "")).strip() or GRAPH_DATA_TYPE_ID
    raw_accepted = port.get("accepted_data_types", ())
    accepted = (
        raw_accepted
        if isinstance(raw_accepted, (list, tuple))
        else ()
    )
    return tuple(
        dict.fromkeys(
            (
                primary,
                *(str(value).strip() for value in accepted if str(value).strip()),
            )
        )
    )


def _library_item_matches_query(
    item: dict[str, Any], *, query: str, compatible_ports: list[dict[str, Any]]
) -> bool:
    normalized_query = str(query).strip().lower()
    if not normalized_query:
        return True
    haystack = " ".join(
        [
            str(item.get("type_id", "")),
            str(item.get("display_name", "")),
            str(item.get("category", "")),
            str(item.get("category_display", "")),
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


def _library_port_spec(port: Mapping[str, Any]) -> PortSpec:
    declared_types = _library_port_declared_data_types(port)
    return PortSpec(
        key=str(port.get("key", "")).strip(),
        direction=str(port.get("direction", "")).strip().lower(),
        kind=str(port.get("kind", "")).strip().lower(),
        data_type=declared_types[0],
        label=str(port.get("label", "")).strip(),
        exposed=bool(port.get("exposed", True)),
        accepted_data_types=declared_types[1:],
    )


def _compatible_library_ports(
    item: dict[str, Any],
    *,
    data_types: DataTypeCatalog,
    source_direction: str,
    source_kind: str,
    source_data_type: str,
    source_accepted_data_types: Iterable[str] = (),
) -> list[dict[str, Any]]:
    normalized_source_direction = str(source_direction).strip().lower()
    normalized_source_kind = str(source_kind).strip().lower()
    normalized_source_data_type = (
        str(source_data_type).strip() or GRAPH_DATA_TYPE_ID
    )
    normalized_source_accepted_data_types = tuple(
        str(value).strip()
        for value in source_accepted_data_types
        if str(value).strip()
    )
    source_is_neutral_flow = (
        normalized_source_direction == "neutral"
        and normalized_source_kind == "flow"
        and normalized_source_data_type == "flow"
    )
    source_port = PortSpec(
        key="source",
        direction=normalized_source_direction,
        kind=normalized_source_kind,
        data_type=normalized_source_data_type,
        accepted_data_types=normalized_source_accepted_data_types,
    )
    compatible_ports: list[dict[str, Any]] = []
    for port in _normalized_library_ports(item):
        candidate_port = _library_port_spec(port)
        if not candidate_port.exposed:
            continue
        if source_is_neutral_flow:
            if not _is_neutral_flow_library_port(port):
                continue
        elif normalized_source_direction == "out":
            if candidate_port.direction != "in":
                continue
            if not ports_compatible(
                source_port,
                candidate_port,
                data_types=data_types,
            ):
                continue
        elif normalized_source_direction == "in":
            if candidate_port.direction != "out":
                continue
            if not ports_compatible(
                candidate_port,
                source_port,
                data_types=data_types,
            ):
                continue
        else:
            continue
        compatible_ports.append(port)
    return compatible_ports


def _connection_quick_insert_rank(
    query: str, *, display_name: str, type_id: str
) -> int:
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
    data_types: DataTypeCatalog,
    query: str,
    source_direction: str,
    source_kind: str,
    source_data_type: str,
    source_accepted_data_types: Iterable[str] = (),
    limit: int = 12,
) -> list[dict[str, Any]]:
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for item in combined_items:
        compatible_ports = _compatible_library_ports(
            item,
            data_types=data_types,
            source_direction=source_direction,
            source_kind=source_kind,
            source_data_type=source_data_type,
            source_accepted_data_types=source_accepted_data_types,
        )
        if not compatible_ports:
            continue
        if not _library_item_matches_query(
            item, query=query, compatible_ports=compatible_ports
        ):
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
    ranked.sort(
        key=lambda entry: (entry[0], entry[1], str(entry[2].get("type_id", "")).lower())
    )
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
        if not _library_item_matches_query(
            item, query=normalized_query, compatible_ports=[]
        ):
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
    ranked.sort(
        key=lambda entry: (entry[0], entry[1], str(entry[2].get("type_id", "")).lower())
    )
    capped = max(1, int(limit))
    return [entry[2] for entry in ranked[:capped]]


def rank_node_library_usage(
    *,
    combined_items: Iterable[dict[str, Any]],
    usage: Iterable[str],
    limit: int = 5,
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    last_used: dict[str, int] = {}
    for index, type_id in enumerate(usage):
        normalized_type_id = str(type_id).strip()
        if not normalized_type_id:
            continue
        counts[normalized_type_id] = counts.get(normalized_type_id, 0) + 1
        last_used[normalized_type_id] = index
    available = {
        str(item.get("type_id", "")).strip(): item
        for item in combined_items
        if str(item.get("library_source", "")).strip() == "node_registry"
    }
    ranked_type_ids = sorted(
        (type_id for type_id in counts if type_id in available),
        key=lambda type_id: (
            -counts[type_id],
            -last_used[type_id],
            str(available[type_id].get("display_name", "")).casefold(),
            type_id,
        ),
    )
    return [
        dict(available[type_id]) for type_id in ranked_type_ids[: max(0, int(limit))]
    ]
