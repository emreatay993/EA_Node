from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ea_node_editor.addons.property_edit_adapters import (
    PropertyEditAdapterContext,
    PropertyEditRewrite,
)
from ea_node_editor.addons.tabular_data.extraction_nodes import (
    ARRAY_SLICE_COLUMN_COUNT_PROPERTY,
    ARRAY_SLICE_COLUMN_START_PROPERTY,
    ARRAY_SLICE_ROW_COUNT_PROPERTY,
    ARRAY_SLICE_ROW_START_PROPERTY,
    ARRAY_SLICE_SUMMARY_PROPERTY,
    TABLE_WINDOW_COLUMN_COUNT_PROPERTY,
    TABLE_WINDOW_COLUMN_START_PROPERTY,
    TABLE_WINDOW_COLUMNS_PROPERTY,
    TABLE_WINDOW_ROW_COUNT_PROPERTY,
    TABLE_WINDOW_ROW_START_PROPERTY,
    TABLE_WINDOW_SUMMARY_PROPERTY,
    TABULAR_ARRAY_SLICE_2D_NODE_TYPE_ID,
    TABULAR_TABLE_WINDOW_NODE_TYPE_ID,
)
from ea_node_editor.addons.tabular_data.input_node import (
    TABULAR_ARRAY_COLUMN_COUNT_PROPERTY,
    TABULAR_ARRAY_COLUMN_START_PROPERTY,
    TABULAR_ARRAY_ROW_COUNT_PROPERTY,
    TABULAR_ARRAY_ROW_START_PROPERTY,
    TABULAR_ARRAY_SELECTION_SUMMARY_PROPERTY,
    TABULAR_ARRAY_SLICE_2D_PROPERTY,
    TABULAR_DATA_INPUT_NODE_TYPE_ID,
    tabular_array_column_label_from_offset,
    tabular_array_slice_2d_from_value,
    tabular_array_slice_2d_summary,
    tabular_array_slice_2d_with_property_update,
)

_TABULAR_SELECTION_HELP_TEXT = (
    "Optional. Use this when the file contains multiple sheets, keys, or datasets."
)
_TABLE_WINDOW_PROPERTY_KEYS = frozenset(
    {
        TABLE_WINDOW_ROW_START_PROPERTY,
        TABLE_WINDOW_ROW_COUNT_PROPERTY,
        TABLE_WINDOW_COLUMN_START_PROPERTY,
        TABLE_WINDOW_COLUMN_COUNT_PROPERTY,
        TABLE_WINDOW_COLUMNS_PROPERTY,
    }
)
_ARRAY_SLICE_PROPERTY_KEYS = frozenset(
    {
        ARRAY_SLICE_ROW_START_PROPERTY,
        ARRAY_SLICE_ROW_COUNT_PROPERTY,
        ARRAY_SLICE_COLUMN_START_PROPERTY,
        ARRAY_SLICE_COLUMN_COUNT_PROPERTY,
    }
)


def _node_properties(node: Any) -> Mapping[str, Any]:
    properties = getattr(node, "properties", {})
    return properties if isinstance(properties, Mapping) else {}


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


def _non_negative_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return max(0, default)
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return max(0, default)
    return max(0, normalized)


def _positive_user_row(value: Any, *, default: int) -> int:
    return max(1, _non_negative_int(value, default=default))


def _column_offset_from_user_value(value: Any, *, default: int) -> int:
    text = str(value or "").strip()
    if not text:
        return max(0, int(default))
    try:
        return max(0, int(text) - 1)
    except ValueError:
        pass
    normalized = text.upper()
    if not normalized.isalpha():
        return max(0, int(default))
    offset = 0
    for character in normalized:
        offset = offset * 26 + (ord(character) - ord("A") + 1)
    return max(0, offset - 1)


def _columns_from_value(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_items: Iterable[Any] = value.replace(";", ",").split(",")
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        raw_items = value
    else:
        raw_items = ()
    columns: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        columns.append(text)
    return columns


def _base_item(
    *,
    key: str,
    label: str,
    value: Any,
    type_: str = "str",
    editor_mode: str = "text",
    group: str = "Selection",
    dirty: bool = False,
    enum_values: Iterable[str] = (),
    help_text: str = "",
    placeholder_text: str = "",
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "key": key,
        "label": label,
        "type": type_,
        "value": value,
        "enum_values": list(enum_values),
        "inline_editor": "",
        "editor_mode": editor_mode,
        "group": group,
        "dirty": bool(dirty),
    }
    if help_text:
        item["help_text"] = help_text
    if placeholder_text:
        item["placeholder_text"] = placeholder_text
    return item


def _bounds_from_node(node: Any, *, row_limit_default: int, column_limit_default: int) -> dict[str, int]:
    properties = _node_properties(node)
    return {
        "row_offset": _non_negative_int(properties.get("row_offset"), default=0),
        "row_limit": _non_negative_int(properties.get("row_limit"), default=row_limit_default),
        "column_offset": _non_negative_int(properties.get("column_offset"), default=0),
        "column_limit": _non_negative_int(properties.get("column_limit"), default=column_limit_default),
    }


def _rows_summary(row_offset: int, row_limit: int) -> str:
    start = row_offset + 1
    if row_limit == 0:
        return f"Rows {start} onward"
    return f"Rows {start}-{row_offset + row_limit}"


def _columns_summary(column_offset: int, column_limit: int, columns: list[str] | None = None) -> str:
    if columns:
        preview = ", ".join(columns[:4])
        suffix = "" if len(columns) <= 4 else f" +{len(columns) - 4} more"
        return f"Columns {preview}{suffix}"
    start = tabular_array_column_label_from_offset(column_offset)
    if column_limit == 0:
        return f"Columns {start} onward"
    end = tabular_array_column_label_from_offset(column_offset + column_limit - 1)
    return f"Columns {start}-{end}"


def _table_window_property_items(node: Any) -> list[dict[str, Any]]:
    bounds = _bounds_from_node(node, row_limit_default=1000, column_limit_default=0)
    columns = _columns_from_value(_node_properties(node).get("columns", ""))
    summary = f"{_rows_summary(bounds['row_offset'], bounds['row_limit'])}, {_columns_summary(bounds['column_offset'], bounds['column_limit'], columns)}"
    return [
        _base_item(
            key=TABLE_WINDOW_COLUMNS_PROPERTY,
            label="Selected Columns",
            type_="list",
            value=columns,
            editor_mode="chip_list",
            dirty=bool(columns),
            placeholder_text="Search columns",
            help_text="Leave empty to select columns by position.",
        ),
        _base_item(
            key=TABLE_WINDOW_ROW_START_PROPERTY,
            label="Start Row",
            type_="int",
            value=bounds["row_offset"] + 1,
            dirty=bounds["row_offset"] != 0,
            help_text="Rows are numbered from 1.",
        ),
        _base_item(
            key=TABLE_WINDOW_ROW_COUNT_PROPERTY,
            label="Number of Rows",
            type_="int",
            value=bounds["row_limit"],
            dirty=bounds["row_limit"] != 1000,
            help_text="Enter 0 for all remaining rows.",
        ),
        _base_item(
            key=TABLE_WINDOW_COLUMN_START_PROPERTY,
            label="Start Column",
            value=tabular_array_column_label_from_offset(bounds["column_offset"]),
            dirty=bounds["column_offset"] != 0,
            help_text="Use spreadsheet letters such as A or AA, or enter a column number.",
        ),
        _base_item(
            key=TABLE_WINDOW_COLUMN_COUNT_PROPERTY,
            label="Number of Columns",
            type_="int",
            value=bounds["column_limit"],
            dirty=bounds["column_limit"] != 0,
            help_text="Enter 0 for all remaining columns.",
        ),
        _base_item(
            key=TABLE_WINDOW_SUMMARY_PROPERTY,
            label="Preview",
            value=summary,
            editor_mode="summary",
            dirty=False,
        ),
    ]


def _array_slice_property_items(node: Any) -> list[dict[str, Any]]:
    bounds = _bounds_from_node(node, row_limit_default=1000, column_limit_default=100)
    summary = f"{_rows_summary(bounds['row_offset'], bounds['row_limit'])}, {_columns_summary(bounds['column_offset'], bounds['column_limit'])}"
    return [
        _base_item(
            key=ARRAY_SLICE_ROW_START_PROPERTY,
            label="Start Row",
            type_="int",
            value=bounds["row_offset"] + 1,
            dirty=bounds["row_offset"] != 0,
            help_text="Rows are numbered from 1.",
        ),
        _base_item(
            key=ARRAY_SLICE_ROW_COUNT_PROPERTY,
            label="Number of Rows",
            type_="int",
            value=bounds["row_limit"],
            dirty=bounds["row_limit"] != 1000,
            help_text="Enter 0 for all remaining rows.",
        ),
        _base_item(
            key=ARRAY_SLICE_COLUMN_START_PROPERTY,
            label="Start Column",
            value=tabular_array_column_label_from_offset(bounds["column_offset"]),
            dirty=bounds["column_offset"] != 0,
            help_text="Use spreadsheet letters such as A or AA, or enter a column number.",
        ),
        _base_item(
            key=ARRAY_SLICE_COLUMN_COUNT_PROPERTY,
            label="Number of Columns",
            type_="int",
            value=bounds["column_limit"],
            dirty=bounds["column_limit"] != 100,
            help_text="Enter 0 for all remaining columns.",
        ),
        _base_item(
            key=ARRAY_SLICE_SUMMARY_PROPERTY,
            label="Preview",
            value=summary,
            editor_mode="summary",
            dirty=False,
        ),
    ]


def _rewrite_table_window_property(node: Any, key: str, value: Any) -> PropertyEditRewrite | None:
    if key not in _TABLE_WINDOW_PROPERTY_KEYS:
        return None
    properties = _node_properties(node)
    if key == TABLE_WINDOW_COLUMNS_PROPERTY:
        return PropertyEditRewrite("columns", ", ".join(_columns_from_value(value)))
    if key == TABLE_WINDOW_ROW_START_PROPERTY:
        return PropertyEditRewrite(
            "row_offset",
            _positive_user_row(value, default=_non_negative_int(properties.get("row_offset"), default=0) + 1) - 1,
        )
    if key == TABLE_WINDOW_ROW_COUNT_PROPERTY:
        return PropertyEditRewrite("row_limit", _non_negative_int(value, default=1000))
    if key == TABLE_WINDOW_COLUMN_START_PROPERTY:
        return PropertyEditRewrite(
            "column_offset",
            _column_offset_from_user_value(
                value,
                default=_non_negative_int(properties.get("column_offset"), default=0),
            ),
        )
    if key == TABLE_WINDOW_COLUMN_COUNT_PROPERTY:
        return PropertyEditRewrite("column_limit", _non_negative_int(value, default=0))
    return None


def _rewrite_array_slice_property(node: Any, key: str, value: Any) -> PropertyEditRewrite | None:
    if key not in _ARRAY_SLICE_PROPERTY_KEYS:
        return None
    properties = _node_properties(node)
    if key == ARRAY_SLICE_ROW_START_PROPERTY:
        return PropertyEditRewrite(
            "row_offset",
            _positive_user_row(value, default=_non_negative_int(properties.get("row_offset"), default=0) + 1) - 1,
        )
    if key == ARRAY_SLICE_ROW_COUNT_PROPERTY:
        return PropertyEditRewrite("row_limit", _non_negative_int(value, default=1000))
    if key == ARRAY_SLICE_COLUMN_START_PROPERTY:
        return PropertyEditRewrite(
            "column_offset",
            _column_offset_from_user_value(
                value,
                default=_non_negative_int(properties.get("column_offset"), default=0),
            ),
        )
    if key == ARRAY_SLICE_COLUMN_COUNT_PROPERTY:
        return PropertyEditRewrite("column_limit", _non_negative_int(value, default=100))
    return None




class TabularDataPropertyEditAdapter:
    def _node_type_id(self, context: PropertyEditAdapterContext) -> str:
        return str(getattr(context.node, "type_id", "")).strip()

    def _is_tabular_input(self, context: PropertyEditAdapterContext) -> bool:
        return self._node_type_id(context) == TABULAR_DATA_INPUT_NODE_TYPE_ID

    def rewrite_property_edit(
        self,
        context: PropertyEditAdapterContext,
        *,
        key: str,
        value: Any,
    ) -> PropertyEditRewrite | None:
        node_type_id = self._node_type_id(context)
        if node_type_id == TABULAR_TABLE_WINDOW_NODE_TYPE_ID:
            return _rewrite_table_window_property(context.node, str(key or "").strip(), value)
        if node_type_id == TABULAR_ARRAY_SLICE_2D_NODE_TYPE_ID:
            return _rewrite_array_slice_property(context.node, str(key or "").strip(), value)
        return None

    def build_property_items(
        self,
        context: PropertyEditAdapterContext,
        items: Iterable[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        node_type_id = self._node_type_id(context)
        if node_type_id == TABULAR_TABLE_WINDOW_NODE_TYPE_ID:
            return [dict(item) for item in items] + _table_window_property_items(context.node)
        if node_type_id == TABULAR_ARRAY_SLICE_2D_NODE_TYPE_ID:
            return [dict(item) for item in items] + _array_slice_property_items(context.node)
        result = [dict(item) for item in items]
        if node_type_id == TABULAR_DATA_INPUT_NODE_TYPE_ID:
            properties = _node_properties(context.node)
            view = properties.get("data_view", {})
            mode = str(view.get("mode", "source")) if isinstance(view, Mapping) else "invalid"
            title = str(properties.get("data_view_name", "") or "Data view")
            result.append(_base_item(key="data_view_summary", label="Configured Output",
                                     value=f"{title} ({mode})", editor_mode="summary",
                                     help_text="Use Configure data on the node to change sources, mapping and output rules."))
            if properties.get("data_view_migration_notice"):
                result.append(_base_item(key="data_view_notice", label="Selection Review", editor_mode="summary",
                                         value="Old preview limits no longer limit output. Review in Configure data."))
        return result


def create_tabular_property_edit_adapters() -> tuple[TabularDataPropertyEditAdapter, ...]:
    return (TabularDataPropertyEditAdapter(),)


__all__ = [
    "TabularDataPropertyEditAdapter",
    "create_tabular_property_edit_adapters",
]
