# Purpose: Project DPF node properties into task-oriented inspector controls.
# Map: docs/agent_maps/feature_routes/ansys_dpf_operator_viewer_transport.md
# Tests: tests/test_dpf_property_edit_adapter.py
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.addons.property_edit_adapters import (
    PropertyEditAdapterContext,
    PropertyEditRewrite,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MESH_SELECTION_ALL,
    DPF_MESH_SELECTION_ELEMENT_IDS,
    DPF_MESH_SELECTION_NAMED_SELECTION,
    DPF_MESH_SELECTION_NODE_IDS,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
    DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
    DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
    DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
    DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
    DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
)
from ea_node_editor.ui_qml.dpf_metadata_options_service import (
    DpfMetadataOptionsEntry,
    DpfMetadataOptionsSnapshot,
    shared_dpf_metadata_options_service,
)


MetadataProvider = Callable[[str], Mapping[str, Iterable[Any]] | DpfMetadataOptionsSnapshot]
_TIME_SCOPE_FIRST = "first_set"
_TIME_SCOPE_LAST = "last_set"
_TIME_SCOPE_ALL = "all_sets"
_TIME_SCOPE_SET_IDS = "set_ids"
_TIME_SCOPE_TIME_VALUES = "time_values"
_CHOOSE_SCOPE = "choose_scope"
_COMMON_RESULT_NAME_OPTIONS = (
    "displacement",
    "stress",
    "elastic_strain",
    "structural_temperature",
)

_CURATED_NODE_TYPE_IDS = frozenset(
    {
        DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
        DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
        DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
        DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
        DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
        DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
        DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
        DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
        DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
    }
)
_CURATED_SELECTION_NODE_TYPE_IDS = frozenset(
    {
        DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
        DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
        DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
        DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
        DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
        DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
    }
)
_TIME_SCOPE_NODE_TYPE_IDS = frozenset(
    {
        DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
        DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
        DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
        DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
        DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
    }
)
_RESULT_OPTION_NODE_TYPE_IDS = frozenset(
    {
        DPF_RESULT_FIELD_NODE_TYPE_ID,
        *_TIME_SCOPE_NODE_TYPE_IDS,
        DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
    }
)
_NAMED_SELECTION_NODE_TYPE_IDS = frozenset(
    {
        DPF_MESH_SCOPING_NODE_TYPE_ID,
        *_CURATED_SELECTION_NODE_TYPE_IDS,
    }
)
_DIRECT_PATH_NODE_TYPE_IDS = frozenset(
    {
        DPF_RESULT_FILE_NODE_TYPE_ID,
        DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
        DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
        DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
    }
)
_REQUIRED_MODEL_NODE_TYPE_IDS = frozenset(
    {
        DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
        DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
        DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
        DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
    }
)


def _properties(node: Any) -> Mapping[str, Any]:
    value = getattr(node, "properties", {})
    return value if isinstance(value, Mapping) else {}


def _text_property(node: Any, key: str) -> str:
    return str(_properties(node).get(key, "") or "").strip()


def _edge_values(context: PropertyEditAdapterContext) -> tuple[Any, ...]:
    value = context.workspace_edges
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return tuple(value.values())
    return tuple(value)


def _incoming_edge(context: PropertyEditAdapterContext, node: Any, port_key: str) -> Any | None:
    node_id = str(getattr(node, "node_id", "") or "").strip()
    for edge in _edge_values(context):
        if (
            str(getattr(edge, "target_node_id", "") or "").strip() == node_id
            and str(getattr(edge, "target_port_key", "") or "").strip() == port_key
        ):
            return edge
    return None


def _path_from_node(
    context: PropertyEditAdapterContext,
    node: Any | None,
    *,
    visited: frozenset[str] = frozenset(),
) -> str:
    if node is None:
        return ""
    node_id = str(getattr(node, "node_id", "") or "").strip()
    if not node_id or node_id in visited:
        return ""
    node_type_id = str(getattr(node, "type_id", "") or "").strip()
    next_visited = visited | {node_id}
    if node_type_id in _DIRECT_PATH_NODE_TYPE_IDS:
        edge = _incoming_edge(context, node, "path")
        if edge is not None:
            source = (context.workspace_nodes or {}).get(
                str(getattr(edge, "source_node_id", "") or "").strip()
            )
            path = _path_from_node(context, source, visited=next_visited)
            if path:
                return path
        path = context.source_path_for_property("path", node=node)
        if path:
            return path
    if node_type_id == DPF_MODEL_NODE_TYPE_ID:
        for port_key in ("result_file", "path"):
            edge = _incoming_edge(context, node, port_key)
            if edge is None:
                continue
            source = (context.workspace_nodes or {}).get(
                str(getattr(edge, "source_node_id", "") or "").strip()
            )
            path = _path_from_node(context, source, visited=next_visited)
            if path:
                return path
        return context.source_path_for_property("path", node=node)
    if node_type_id == DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID:
        return _path_from_model_input(context, node, visited=next_visited)
    if _text_property(node, "path"):
        return context.source_path_for_property("path", node=node)
    return ""


def _path_from_model_input(
    context: PropertyEditAdapterContext,
    node: Any,
    *,
    visited: frozenset[str] = frozenset(),
) -> str:
    edge = _incoming_edge(context, node, "model")
    if edge is None:
        return ""
    source = (context.workspace_nodes or {}).get(
        str(getattr(edge, "source_node_id", "") or "").strip()
    )
    return _path_from_node(context, source, visited=visited)


def resolve_dpf_result_path(context: PropertyEditAdapterContext) -> str:
    node_type_id = str(getattr(context.node, "type_id", "") or "").strip()
    if node_type_id in _DIRECT_PATH_NODE_TYPE_IDS:
        path = _path_from_node(context, context.node)
        if path:
            return str(Path(path).expanduser())
    path = _path_from_model_input(context, context.node)
    return str(Path(path).expanduser()) if path else ""


def _metadata_from_mapping(
    result_path: str,
    values: Mapping[str, Iterable[Any]],
) -> DpfMetadataOptionsSnapshot:
    def texts(key: str) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values.get(key, ()):
            text = str(value or "").strip()
            folded = text.casefold()
            if text and folded not in seen:
                seen.add(folded)
                result.append(text)
        return tuple(result)

    entry = DpfMetadataOptionsEntry(
        signature=result_path,
        revision=1,
        result_path=result_path,
        result_names=texts("result_name"),
        set_ids=texts("set_ids"),
        time_values=texts("time_values"),
        named_selections=texts("named_selection"),
    )
    return DpfMetadataOptionsSnapshot(state="ready", signature=result_path, revision=1, entry=entry)


def _list_value(value: Any) -> list[str]:
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    for delimiter in (";", "\n"):
        text = text.replace(delimiter, ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def _selection_summary(node: Any) -> tuple[str, bool]:
    mode = _text_property(node, "selection_mode") or DPF_MESH_SELECTION_ALL
    if mode == _CHOOSE_SCOPE:
        return "Choose scope", True
    if mode == DPF_MESH_SELECTION_ALL:
        return "Whole model", False
    if mode == DPF_MESH_SELECTION_NAMED_SELECTION:
        value = _text_property(node, "named_selection")
        return (value or "Choose named selection", not bool(value))
    if mode == DPF_MESH_SELECTION_NODE_IDS:
        values = _list_value(_properties(node).get("node_ids", ""))
        return (f"{len(values)} node IDs" if values else "Choose node IDs", not bool(values))
    if mode == DPF_MESH_SELECTION_ELEMENT_IDS:
        values = _list_value(_properties(node).get("element_ids", ""))
        return (f"{len(values)} element IDs" if values else "Choose element IDs", not bool(values))
    return mode.replace("_", " ").title(), False


def _time_summary(node: Any) -> tuple[str, bool]:
    mode = _text_property(node, "time_scope_mode")
    if not mode:
        return "", False
    if mode == _TIME_SCOPE_FIRST:
        return "First set", False
    if mode == _TIME_SCOPE_LAST:
        return "Last set", False
    if mode == _TIME_SCOPE_ALL:
        return "All sets", False
    key = "set_ids" if mode == _TIME_SCOPE_SET_IDS else "time_values"
    values = _list_value(_properties(node).get(key, ""))
    label = "sets" if key == "set_ids" else "time values"
    return (f"{len(values)} {label}" if values else f"Choose {label}", not bool(values))


def _has_input(context: PropertyEditAdapterContext, key: str) -> bool:
    return _incoming_edge(context, context.node, key) is not None


def _workflow_summary_item(context: PropertyEditAdapterContext) -> dict[str, Any]:
    node = context.node
    node_type_id = str(getattr(node, "type_id", "") or "").strip()
    parts: list[str] = []
    incomplete = False
    path = resolve_dpf_result_path(context)
    if node_type_id in _DIRECT_PATH_NODE_TYPE_IDS:
        parts.append(Path(path).name if path else "Choose result file")
        incomplete = not bool(path)
    result_name = _text_property(node, "result_name")
    if result_name:
        parts.append(result_name.replace("_", " ").title())
    if node_type_id in _CURATED_SELECTION_NODE_TYPE_IDS:
        selection, missing = _selection_summary(node)
        parts.append(selection)
        incomplete = incomplete or missing
    time_label, missing_time = _time_summary(node)
    if time_label:
        parts.append(time_label)
        incomplete = incomplete or missing_time
    location = _text_property(node, "location")
    if location:
        parts.append(location.replace("_", " ").title())
    if node_type_id == DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID:
        parts.insert(0, (_text_property(node, "invariant") or "von_mises").replace("_", " ").title())
    if node_type_id == DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID:
        operation = (_text_property(node, "operation") or "add").replace("_", " ").title()
        parts.append(operation)
        incomplete = incomplete or not _has_input(context, "a")
        if _text_property(node, "operation") != "scale":
            incomplete = incomplete or not _has_input(context, "b")
    if node_type_id in _REQUIRED_MODEL_NODE_TYPE_IDS:
        incomplete = incomplete or not _has_input(context, "model")
    if node_type_id == DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID:
        incomplete = incomplete or not _has_input(context, "fields") or not _has_input(context, "model")
    return {
        "key": "dpf_workflow_summary",
        "label": "Workflow",
        "type": "str",
        "value": " · ".join(part for part in parts if part) or "Configure this DPF task",
        "enum_values": [],
        "inline_editor": "",
        "editor_mode": "summary",
        "group": "Setup",
        "dirty": False,
        "attention_required": incomplete,
        "group_default_open": incomplete,
        "help_text": "Complete the highlighted setup before running." if incomplete else "Ready to run.",
    }


class AnsysDpfPropertyEditAdapter:
    def __init__(self, *, metadata_provider: MetadataProvider | None = None) -> None:
        self._metadata_provider = metadata_provider

    def _snapshot(
        self,
        context: PropertyEditAdapterContext,
        result_path: str,
    ) -> DpfMetadataOptionsSnapshot:
        if not result_path:
            return DpfMetadataOptionsSnapshot(state="empty")
        if self._metadata_provider is not None:
            value = self._metadata_provider(result_path)
            if isinstance(value, DpfMetadataOptionsSnapshot):
                return value
            return _metadata_from_mapping(result_path, value)
        return shared_dpf_metadata_options_service().request_options(
            workspace_id=context.workspace_id,
            node_id=str(getattr(context.node, "node_id", "") or ""),
            result_path=result_path,
        )

    def rewrite_property_edit(
        self,
        context: PropertyEditAdapterContext,
        *,
        key: str,
        value: Any,
    ) -> PropertyEditRewrite | None:
        normalized_key = str(key or "").strip()
        if normalized_key == "path" and self._metadata_provider is None:
            shared_dpf_metadata_options_service().invalidate_all()
            return None
        if normalized_key not in {"set_ids", "time_values"}:
            return None
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
            return PropertyEditRewrite(normalized_key, ", ".join(_list_value(value)))
        return None

    def build_property_items(
        self,
        context: PropertyEditAdapterContext,
        items: Iterable[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        node = context.node
        node_type_id = str(getattr(node, "type_id", "") or "").strip()
        if (
            node_type_id not in _CURATED_NODE_TYPE_IDS
            and node_type_id not in _RESULT_OPTION_NODE_TYPE_IDS
            and node_type_id not in _NAMED_SELECTION_NODE_TYPE_IDS
        ):
            return [dict(item) for item in items]

        result_path = resolve_dpf_result_path(context)
        snapshot = self._snapshot(context, result_path)
        selection_mode = _text_property(node, "selection_mode") or DPF_MESH_SELECTION_ALL
        time_scope_mode = _text_property(node, "time_scope_mode")
        operation = _text_property(node, "operation") or "add"
        scalar_range_mode = _text_property(node, "scalar_range_mode") or "auto"
        result: list[dict[str, Any]] = []
        if node_type_id in _CURATED_NODE_TYPE_IDS:
            result.append(_workflow_summary_item(context))

        selection_keys = {
            "named_selection": DPF_MESH_SELECTION_NAMED_SELECTION,
            "node_ids": DPF_MESH_SELECTION_NODE_IDS,
            "element_ids": DPF_MESH_SELECTION_ELEMENT_IDS,
        }
        for raw_item in items:
            item = dict(raw_item)
            key = str(item.get("key", "") or "").strip()
            required_mode = selection_keys.get(key)
            if node_type_id in _CURATED_SELECTION_NODE_TYPE_IDS and required_mode is not None:
                if selection_mode != required_mode:
                    continue
            if node_type_id in _TIME_SCOPE_NODE_TYPE_IDS:
                if key == "set_ids" and time_scope_mode != _TIME_SCOPE_SET_IDS:
                    continue
                if key == "time_values" and time_scope_mode != _TIME_SCOPE_TIME_VALUES:
                    continue
            if node_type_id == DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID and key == "scalar":
                if operation != "scale":
                    continue
            if key in {"scalar_range_min", "scalar_range_max"} and scalar_range_mode != "custom":
                continue
            if key == "output_mode":
                item["group"] = "Advanced"

            option_key = "set_ids" if key == "mode" else key
            if node_type_id in _RESULT_OPTION_NODE_TYPE_IDS and key in {
                "result_name",
                "set_ids",
                "time_values",
                "mode",
            }:
                self._apply_metadata_options(
                    item,
                    snapshot,
                    option_key,
                    bool(result_path),
                    missing_path_placeholder=(
                        "Set a modal result file to load modes"
                        if key == "mode"
                        else (
                            f"Connect a DPF model to load {'result names' if key == 'result_name' else 'set IDs' if key == 'set_ids' else 'time values'}"
                            if node_type_id == DPF_RESULT_FIELD_NODE_TYPE_ID
                            else ""
                        )
                    ),
                )
            if (
                node_type_id in _NAMED_SELECTION_NODE_TYPE_IDS
                and key == "named_selection"
                and selection_mode == DPF_MESH_SELECTION_NAMED_SELECTION
            ):
                self._apply_metadata_options(item, snapshot, "named_selection", bool(result_path))
            if node_type_id in _TIME_SCOPE_NODE_TYPE_IDS and key in {"set_ids", "time_values"}:
                item["editor_mode"] = "chip_list"
                item["value"] = _list_value(item.get("value", ""))
                if item.get("metadata_state") == "ready":
                    item["placeholder_text"] = (
                        "Add set ID" if key == "set_ids" else "Add time value"
                    )
            if key == "selection_mode" and selection_mode == _CHOOSE_SCOPE:
                item["attention_required"] = True
                item["help_text"] = "Choose a named selection, node IDs, or element IDs."
            result.append(item)
        return result

    @staticmethod
    def _apply_metadata_options(
        item: dict[str, Any],
        snapshot: DpfMetadataOptionsSnapshot,
        option_key: str,
        has_path: bool,
        missing_path_placeholder: str = "",
    ) -> None:
        entry = snapshot.entry
        metadata_options = entry.option_values(option_key) if entry is not None else ()
        options = metadata_options
        if option_key == "result_name" and not metadata_options:
            options = _COMMON_RESULT_NAME_OPTIONS
        item["editor_mode"] = "editable_combo"
        item["enum_values"] = list(options)
        item["metadata_state"] = (
            "empty" if snapshot.state == "ready" and not metadata_options else snapshot.state
        )
        label = {
            "result_name": "result names",
            "set_ids": "set IDs",
            "time_values": "time values",
            "named_selection": "named selections",
        }.get(option_key, "values")
        if str(item.get("key", "")) == "mode":
            label = "modes"
        if snapshot.state == "loading":
            item["placeholder_text"] = "Loading DPF metadata..."
        elif snapshot.state == "error":
            item["placeholder_text"] = f"Metadata unavailable; enter {label} manually"
            item["help_text"] = f"{snapshot.error} Edit or reselect the result path to retry.".strip()
        elif not has_path:
            item["placeholder_text"] = (
                missing_path_placeholder or f"Choose or connect a result file to load {label}"
            )
        elif not metadata_options:
            item["placeholder_text"] = f"No {label} found"
        else:
            item["placeholder_text"] = ""


def create_ansys_dpf_property_edit_adapters() -> tuple[AnsysDpfPropertyEditAdapter, ...]:
    return (AnsysDpfPropertyEditAdapter(),)


__all__ = [
    "AnsysDpfPropertyEditAdapter",
    "create_ansys_dpf_property_edit_adapters",
    "resolve_dpf_result_path",
]
