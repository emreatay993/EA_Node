# Purpose: Project Mechanical selectors from accepted catalogue metadata only.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_property_edit.py

from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ea_node_editor.addons.mechanical.contracts import MODEL_TYPE_ID
from ea_node_editor.addons.property_edit_adapters import PropertyEditAdapterContext
from ea_node_editor.runtime_contracts import DataTree, RuntimeHandleRef, TableValue

_SELECTOR_KINDS = {
    "system": ("system",),
    "query": ("object", "property"),
    "source": ("object", "property"),
    "table": ("table",),
    "objects": ("object",),
    "views": ("view",),
    "environments": ("object",),
}
_INDEX_CACHE: OrderedDict[tuple[str, int], "_CatalogueIndex"] = OrderedDict()
_CACHE_LIMIT = 16
_INVALID = object()


@dataclass(frozen=True, slots=True)
class _CatalogueIndex:
    rows_by_kind: Mapping[str, tuple[tuple[Any, str], ...]]
    complete: bool
    omitted_rows: int | None
    table: TableValue
    locator: tuple[Any, ...]


_LOCATOR_FIELDS = (
    "catalogue_id",
    "producer_node_id",
    "producer_port",
    "producer_path",
    "run_id",
    "session_id",
    "model_revision",
    "producer_iteration",
    "document_id",
    "source_key",
    "system_key",
)


def _scalar(value: Any) -> Any:
    item = getattr(value, "item", None)
    return item() if callable(item) else value


def _table_rows(table: TableValue) -> list[dict[str, Any]]:
    columns = [column.to_pandas_array() for column in table.columns]
    return [
        {name: _scalar(columns[column][row]) for column, name in enumerate(table.column_names)}
        for row in range(table.row_count)
    ]


def _catalogue_index(table: TableValue, rows: list[dict[str, Any]]) -> _CatalogueIndex:
    summary = rows[0]
    key = (str(summary["catalogue_id"]), int(summary["model_revision"]))
    cached = _INDEX_CACHE.get(key)
    if cached is not None and cached.table is table:
        _INDEX_CACHE.move_to_end(key)
        return cached
    rows_by_kind: dict[str, list[tuple[Any, str]]] = {}
    for row in rows[1:]:
        code = row.get("selector_code")
        kind = str(row.get("record_kind") or "")
        if not code or kind not in {"system", "object", "property", "table", "view"}:
            continue
        label = (
            row.get("system_label")
            if kind == "system"
            else row.get("view_name")
            if kind == "view"
            else row.get("property_caption")
            if kind == "property"
            else row.get("table_key")
            if kind == "table"
            else row.get("display_name")
        )
        path = str(row.get("object_path") or "")
        visible = str(label or path or code)
        if path and path != visible:
            visible = f"{visible} — {path}"
        rows_by_kind.setdefault(kind, []).append((code, visible))
    result = _CatalogueIndex(
        rows_by_kind={kind: tuple(values) for kind, values in rows_by_kind.items()},
        complete=bool(summary["catalogue_complete"]),
        omitted_rows=None if summary.get("omitted_rows") is None else int(summary["omitted_rows"]),
        table=table,
        locator=tuple(summary.get(field) for field in _LOCATOR_FIELDS),
    )
    _INDEX_CACHE[key] = result
    _INDEX_CACHE.move_to_end(key)
    while len(_INDEX_CACHE) > _CACHE_LIMIT:
        _INDEX_CACHE.popitem(last=False)
    return result


def _model_values(value: Any) -> tuple[RuntimeHandleRef, ...]:
    values = (
        (item for _path, branch in value.branches for item in branch)
        if isinstance(value, DataTree)
        else (value,)
    )
    return tuple(
        item
        for item in values
        if isinstance(item, RuntimeHandleRef) and item.data_type_id == MODEL_TYPE_ID
    )


def _catalogue_for_model(
    model: RuntimeHandleRef,
    provider: Any,
) -> _CatalogueIndex | object | None:
    metadata = model.metadata
    output = provider(metadata["producer_node_id"], metadata["producer_port"])
    if not isinstance(output, DataTree):
        return None
    try:
        branch = output[tuple(metadata["producer_path"])]
    except (KeyError, TypeError):
        return None
    key = (str(metadata["catalogue_id"]), int(metadata["model_revision"]))
    expected_locator = tuple(
        json.dumps(metadata[field], separators=(",", ":"))
        if field == "producer_path"
        else metadata[field]
        for field in _LOCATOR_FIELDS
    )
    matches: list[_CatalogueIndex | tuple[TableValue, list[dict[str, Any]]]] = []
    for candidate in branch:
        if not isinstance(candidate, TableValue) or not candidate.row_count:
            continue
        cached = next(
            (index for index in _INDEX_CACHE.values() if index.table is candidate),
            None,
        )
        if cached is not None:
            if cached.locator == expected_locator:
                matches.append(cached)
            continue
        rows = _table_rows(candidate)
        summary = rows[0]
        try:
            producer_path = tuple(json.loads(str(summary.get("producer_path"))))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if producer_path == tuple(metadata["producer_path"]) and tuple(
            summary.get(field) for field in _LOCATOR_FIELDS
        ) == expected_locator:
            matches.append((candidate, rows))
    if len(matches) != 1:
        return _INVALID if any(isinstance(item, TableValue) for item in branch) else None
    match = matches[0]
    if isinstance(match, _CatalogueIndex):
        _INDEX_CACHE.move_to_end(key)
        return match
    return _catalogue_index(*match)


def _connected_value(context: PropertyEditAdapterContext, port_key: str) -> Any:
    if context.current_output_provider is None:
        return None
    for edge in context.workspace_edges.values() if isinstance(context.workspace_edges, Mapping) else context.workspace_edges or ():
        if (
            edge.target_node_id == context.node.node_id
            and edge.target_port_key == port_key
            and getattr(edge, "enabled", True)
        ):
            return context.current_output_provider(edge.source_node_id, edge.source_port_key)
    return None


class MechanicalPropertyEditAdapter:
    def rewrite_property_edit(self, context: PropertyEditAdapterContext, *, key: str, value: Any):
        return None

    def build_property_items(
        self,
        context: PropertyEditAdapterContext,
        items: Iterable[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        result = [dict(item) for item in items]
        if not str(getattr(context.node, "type_id", "")).startswith("mechanical."):
            return result
        indexes: list[_CatalogueIndex] = []
        invalid = False
        if getattr(context.node, "type_id", "") == "mechanical.open_model":
            own = context.current_output_provider(context.node.node_id, "info") if context.current_output_provider else None
            for _path, branch in own.branches if isinstance(own, DataTree) else ():
                for table in branch:
                    if isinstance(table, TableValue) and table.row_count:
                        rows = _table_rows(table)
                        summary = rows[0]
                        if summary.get("producer_node_id") == context.node.node_id and summary.get("producer_port") == "info":
                            indexes.append(_catalogue_index(table, rows))
        else:
            for model in _model_values(_connected_value(context, "model")):
                index = _catalogue_for_model(model, context.current_output_provider)
                if index is _INVALID:
                    invalid = True
                elif index is not None:
                    indexes.append(index)
        for item in result:
            item_key = str(item.get("key") or "")
            if item_key == "mode":
                item.update(
                    enum_codes=["background", "interactive"],
                    enum_values=["Background", "Interactive"],
                    exact_selectors=True,
                )
                continue
            if item_key == "version":
                from ea_node_editor.addons.mechanical.catalog import mechanical_release_choices
                releases = mechanical_release_choices()
                item.update(
                    enum_codes=[0, *releases],
                    enum_values=[
                        "Auto · 2026 R1 or newer",
                        *(f"20{code // 10:02d} R{code % 10} ({code})" for code in releases),
                    ],
                    exact_selectors=True,
                )
                continue
            kinds = _SELECTOR_KINDS.get(item_key)
            if not kinds:
                continue
            options: list[tuple[Any, str]] = []
            for index in indexes:
                for kind in kinds:
                    options.extend(index.rows_by_kind.get(kind, ()))
            item.update(
                enum_codes=[code for code, _label in options],
                enum_values=[label for _code, label in options],
                exact_selectors=True,
                searchable=True,
                placeholder_text=(
                    "Accepted metadata unavailable"
                    if not indexes
                    else str(item.get("placeholder_text") or "Type or choose a value")
                ),
            )
            if item.get("editor_mode") == "chip_list" or item.get("inline_editor") == "list":
                item.update(
                    list_item_enum_codes=list(item["enum_codes"]),
                    list_item_enum_values=list(item["enum_values"]),
                )
            incomplete = [index for index in indexes if not index.complete]
            if incomplete:
                omitted = sum(index.omitted_rows or 0 for index in incomplete)
                notice = (
                    f"Suggestions are incomplete ({omitted} omitted rows)."
                    if omitted
                    else "Suggestions are incomplete."
                )
                item["metadata_notice"] = notice
                item["placeholder_text"] = notice
                item["help_text"] = " ".join(filter(None, (item.get("help_text"), notice)))
            elif invalid:
                item["metadata_notice"] = "Accepted metadata is invalid."
                item["placeholder_text"] = item["metadata_notice"]
        return result


def create_mechanical_property_edit_adapters() -> tuple[MechanicalPropertyEditAdapter, ...]:
    return (MechanicalPropertyEditAdapter(),)


__all__ = ["MechanicalPropertyEditAdapter", "create_mechanical_property_edit_adapters"]
