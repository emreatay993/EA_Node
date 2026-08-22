from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ea_node_editor.addons.tabular_data.loader_cache_service import (
    TabularLoaderCacheService,
    shared_tabular_loader_cache_service,
)
from ea_node_editor.addons.tabular_data.metadata import TABULAR_DATA_ADDON_CATEGORY
from ea_node_editor.nodes.builtins.integrations_common import pick_optional_path
from ea_node_editor.nodes.decorators import plugin_descriptor
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.file_dialog_filters import (
    TABULAR_ARRAY_OUTPUT_FILES_FILTER,
    TABULAR_TABLE_OUTPUT_FILES_FILTER,
)
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec
from ea_node_editor.nodes.output_artifacts import write_managed_output
from ea_node_editor.runtime_contracts import (
    ArrayDataRef,
    ArraySlice2D,
    ArraySlice2DRef,
    ArraySlice2DRequest,
    TabularDataRef,
    TabularDataWindow,
    TabularWindowRef,
    TabularWindowRequest,
    coerce_array_data_ref,
    coerce_array_slice_2d_ref,
    coerce_tabular_data_ref,
    coerce_tabular_window_ref,
)
from ea_node_editor.runtime_contracts.data_tree import resolve_single_run_inputs

TABULAR_TABLE_WINDOW_NODE_TYPE_ID = "tabular.table_filter"
TABULAR_ARRAY_SLICE_2D_NODE_TYPE_ID = "tabular.array_slice_2d"
TABULAR_WRITE_TABLE_WINDOW_NODE_TYPE_ID = "tabular.write_table_filter"
TABULAR_WRITE_ARRAY_SLICE_2D_NODE_TYPE_ID = "tabular.write_array_slice_2d"
TABULAR_MATERIALIZE_TABLE_WINDOW_NODE_TYPE_ID = "tabular.materialize_table_filter"
TABULAR_MATERIALIZE_ARRAY_SLICE_2D_NODE_TYPE_ID = "tabular.materialize_array_slice_2d"

TABULAR_TABLE_WINDOW_DISPLAY_NAME = "Table Filter"
TABULAR_ARRAY_SLICE_2D_DISPLAY_NAME = "Array Slice 2D"
TABULAR_WRITE_TABLE_WINDOW_DISPLAY_NAME = "Write Filtered Table"
TABULAR_WRITE_ARRAY_SLICE_2D_DISPLAY_NAME = "Write Array Slice 2D"
TABULAR_MATERIALIZE_TABLE_WINDOW_DISPLAY_NAME = "Materialize Filtered Table"
TABULAR_MATERIALIZE_ARRAY_SLICE_2D_DISPLAY_NAME = "Materialize Array Slice 2D"

TABULAR_WINDOW_OUTPUT_KEY = "window"
TABULAR_ARRAY_SLICE_2D_OUTPUT_KEY = "slice_2d"

TABLE_WINDOW_ROW_START_PROPERTY = "table_window_row_start"
TABLE_WINDOW_ROW_COUNT_PROPERTY = "table_window_row_count"
TABLE_WINDOW_COLUMN_START_PROPERTY = "table_window_column_start"
TABLE_WINDOW_COLUMN_COUNT_PROPERTY = "table_window_column_count"
TABLE_WINDOW_COLUMNS_PROPERTY = "table_window_columns"
TABLE_WINDOW_SUMMARY_PROPERTY = "table_window_summary"
ARRAY_SLICE_ROW_START_PROPERTY = "array_slice_2d_row_start"
ARRAY_SLICE_ROW_COUNT_PROPERTY = "array_slice_2d_row_count"
ARRAY_SLICE_COLUMN_START_PROPERTY = "array_slice_2d_column_start"
ARRAY_SLICE_COLUMN_COUNT_PROPERTY = "array_slice_2d_column_count"
ARRAY_SLICE_SUMMARY_PROPERTY = "array_slice_2d_summary"

_TABLE_OUTPUT_SUFFIXES = frozenset({".csv", ".tsv", ".txt", ".jsonl", ".xlsx", ".xlsm"})
_ARRAY_OUTPUT_SUFFIXES = frozenset({".csv", ".tsv", ".txt", ".xlsx", ".xlsm", ".npy"})


def _non_negative_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, normalized)


def _columns_from_value(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        raw_items: Iterable[Any] = value.replace(";", ",").split(",")
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        raw_items = value
    else:
        raw_items = ()
    columns: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        columns.append(name)
    return tuple(columns)


def _stable_ref_id(prefix: str, payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _table_window_request_from_ref(ref: TabularWindowRef) -> TabularWindowRequest:
    return TabularWindowRequest(
        row_offset=ref.row_offset,
        row_limit=ref.row_limit,
        column_offset=ref.column_offset,
        column_limit=ref.column_limit,
        columns=ref.columns,
    )


def _array_slice_request_from_ref(ref: ArraySlice2DRef) -> ArraySlice2DRequest:
    return ArraySlice2DRequest(
        row_offset=ref.row_offset,
        row_limit=ref.row_limit,
        column_offset=ref.column_offset,
        column_limit=ref.column_limit,
    )


def _table_window_ref_from_properties(table_data: TabularDataRef, properties: Mapping[str, Any]) -> TabularWindowRef:
    payload = {
        "table_data": table_data.to_payload(),
        "row_offset": _non_negative_int(properties.get("row_offset"), default=0),
        "row_limit": _non_negative_int(properties.get("row_limit"), default=1000),
        "column_offset": _non_negative_int(properties.get("column_offset"), default=0),
        "column_limit": _non_negative_int(properties.get("column_limit"), default=0),
        "columns": list(_columns_from_value(properties.get("columns", ""))),
    }
    return TabularWindowRef(
        ref_id=_stable_ref_id("table_filter", payload),
        table_data=table_data,
        row_offset=payload["row_offset"],
        row_limit=payload["row_limit"],
        column_offset=payload["column_offset"],
        column_limit=payload["column_limit"],
        columns=tuple(payload["columns"]),
        metadata={"source_ref_id": table_data.ref_id},
    )


def _array_slice_ref_from_properties(array_data: ArrayDataRef, properties: Mapping[str, Any]) -> ArraySlice2DRef:
    payload = {
        "array_data": array_data.to_payload(),
        "row_offset": _non_negative_int(properties.get("row_offset"), default=0),
        "row_limit": _non_negative_int(properties.get("row_limit"), default=1000),
        "column_offset": _non_negative_int(properties.get("column_offset"), default=0),
        "column_limit": _non_negative_int(properties.get("column_limit"), default=100),
    }
    return ArraySlice2DRef(
        ref_id=_stable_ref_id("array_slice_2d", payload),
        array_data=array_data,
        row_offset=payload["row_offset"],
        row_limit=payload["row_limit"],
        column_offset=payload["column_offset"],
        column_limit=payload["column_limit"],
        metadata={"source_ref_id": array_data.ref_id},
    )


def load_table_window(
    ref: TabularWindowRef,
    *,
    service: TabularLoaderCacheService | None = None,
) -> TabularDataWindow:
    loader = service or shared_tabular_loader_cache_service()
    return loader.window(ref.table_data, _table_window_request_from_ref(ref))


def stream_table_window_rows(
    ref: TabularWindowRef,
    *,
    service: TabularLoaderCacheService | None = None,
) -> Iterable[Mapping[str, Any]]:
    loader = service or shared_tabular_loader_cache_service()
    yield from loader.iter_window_rows(ref.table_data, _table_window_request_from_ref(ref))


def table_window_columns(
    ref: TabularWindowRef,
    *,
    service: TabularLoaderCacheService | None = None,
) -> tuple[str, ...]:
    loader = service or shared_tabular_loader_cache_service()
    return loader.window_columns(ref.table_data, _table_window_request_from_ref(ref))


def load_array_slice_2d(
    ref: ArraySlice2DRef,
    *,
    service: TabularLoaderCacheService | None = None,
) -> ArraySlice2D:
    loader = service or shared_tabular_loader_cache_service()
    return loader.slice_2d(ref.array_data, _array_slice_request_from_ref(ref))


def stream_array_slice_2d_rows(
    ref: ArraySlice2DRef,
    *,
    service: TabularLoaderCacheService | None = None,
) -> Iterable[Sequence[Any]]:
    yield from load_array_slice_2d(ref, service=service).values


def _require_openpyxl(node_name: str) -> Any:
    try:
        import openpyxl  # type: ignore
    except Exception as exc:  # noqa: BLE001
        runtime_mode = "packaged" if bool(getattr(sys, "frozen", False)) else "source"
        install_guidance = (
            "Rebuild package with openpyxl installed in the build environment."
            if runtime_mode == "packaged"
            else "Install with: pip install openpyxl"
        )
        raise RuntimeError(
            f"{node_name} requires optional dependency 'openpyxl' for XLSX/XLSM support. "
            f"Runtime mode: {runtime_mode}. CSV remains supported without this dependency. "
            f"{install_guidance}"
        ) from exc
    return openpyxl


def _require_numpy(node_name: str) -> Any:
    try:
        import numpy  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{node_name} requires optional dependency 'numpy' for NPY output.") from exc
    return numpy


def _prepare_explicit_output_path(path: Path, *, node_name: str, suffixes: frozenset[str]) -> str:
    suffix = path.suffix.lower()
    if suffix not in suffixes:
        allowed = ", ".join(sorted(suffixes))
        raise ValueError(
            f"{node_name} supports only {allowed} output formats. "
            f"Received: {path.suffix or '<no extension>'}"
        )
    if path.exists() and path.is_dir():
        raise ValueError(f"{node_name} path must be a file, not a directory: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return suffix


def write_table_rows_to_path(
    path: Path,
    *,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
    node_name: str = TABULAR_WRITE_TABLE_WINDOW_DISPLAY_NAME,
) -> None:
    suffix = _prepare_explicit_output_path(
        path,
        node_name=node_name,
        suffixes=_TABLE_OUTPUT_SUFFIXES,
    )
    normalized_columns = [str(column) for column in columns]
    if suffix in {".csv", ".tsv", ".txt"}:
        delimiter = "," if suffix == ".csv" else "\t"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=normalized_columns, delimiter=delimiter)
            writer.writeheader()
            for row in rows:
                writer.writerow({column: row.get(column) for column in normalized_columns})
        return
    if suffix == ".jsonl":
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(
                    json.dumps(
                        {column: row.get(column) for column in normalized_columns},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        return
    openpyxl = _require_openpyxl(node_name)
    workbook = openpyxl.Workbook()
    try:
        sheet = workbook.active
        sheet.append(normalized_columns)
        for row in rows:
            sheet.append([row.get(column) for column in normalized_columns])
        workbook.save(path)
    finally:
        workbook.close()


def write_array_rows_to_path(
    path: Path,
    *,
    rows: Iterable[Sequence[Any]],
    node_name: str = TABULAR_WRITE_ARRAY_SLICE_2D_DISPLAY_NAME,
) -> None:
    suffix = _prepare_explicit_output_path(
        path,
        node_name=node_name,
        suffixes=_ARRAY_OUTPUT_SUFFIXES,
    )
    if suffix == ".npy":
        numpy = _require_numpy(node_name)
        numpy.save(path, numpy.array([list(row) for row in rows]))
        return
    if suffix in {".csv", ".tsv", ".txt"}:
        delimiter = "," if suffix == ".csv" else "\t"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter=delimiter)
            writer.writerows(rows)
        return
    openpyxl = _require_openpyxl(node_name)
    workbook = openpyxl.Workbook()
    try:
        sheet = workbook.active
        for row in rows:
            sheet.append(list(row))
        workbook.save(path)
    finally:
        workbook.close()


def _write_table_window_to_path(path: Path, ref: TabularWindowRef) -> None:
    suffix = path.suffix.lower()
    loader = shared_tabular_loader_cache_service()
    columns = table_window_columns(ref, service=loader)
    if suffix not in _TABLE_OUTPUT_SUFFIXES:
        _prepare_explicit_output_path(
            path,
            node_name=TABULAR_WRITE_TABLE_WINDOW_DISPLAY_NAME,
            suffixes=_TABLE_OUTPUT_SUFFIXES,
        )
    write_table_rows_to_path(
        path,
        columns=columns,
        rows=stream_table_window_rows(ref, service=loader),
    )


def _write_array_slice_to_path(path: Path, ref: ArraySlice2DRef) -> None:
    array_slice = load_array_slice_2d(ref)
    write_array_rows_to_path(path, rows=array_slice.values)


def _unbounded_table_message(ref: TabularWindowRef) -> str:
    if ref.row_limit == 0 and ref.column_limit == 0:
        return "Materialize Filtered Table is loading all remaining rows and columns into memory."
    if ref.row_limit == 0:
        return "Materialize Filtered Table is loading all remaining rows into memory."
    return "Materialize Filtered Table is loading all remaining columns into memory."


def _unbounded_array_message(ref: ArraySlice2DRef) -> str:
    if ref.row_limit == 0 and ref.column_limit == 0:
        return "Materialize Array Slice 2D is loading all remaining rows and columns into memory."
    if ref.row_limit == 0:
        return "Materialize Array Slice 2D is loading all remaining rows into memory."
    return "Materialize Array Slice 2D is loading all remaining columns into memory."


def _bounds_properties(*, row_limit: int, column_limit: int) -> tuple[PropertySpec, ...]:
    return (
        PropertySpec("row_offset", "int", 0, "Row Offset", inspector_visible=False, group="Selection"),
        PropertySpec("row_limit", "int", row_limit, "Row Limit", inspector_visible=False, group="Selection"),
        PropertySpec("column_offset", "int", 0, "Column Offset", inspector_visible=False, group="Selection"),
        PropertySpec("column_limit", "int", column_limit, "Column Limit", inspector_visible=False, group="Selection"),
    )


class TabularTableWindowNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id=TABULAR_TABLE_WINDOW_NODE_TYPE_ID,
            display_name=TABULAR_TABLE_WINDOW_DISPLAY_NAME,
            category_path=(TABULAR_DATA_ADDON_CATEGORY,),
            icon="integrations/tabular_data.svg",
            description="Creates a lazy filtered-table reference from tabular data.",
            keywords=("table", "filter", "window"),
            ports=(
                PortSpec(
                    "table_data",
                    "in",
                    "data",
                    'COREX.Runtime.TabularDataRef',
                    "Table Data",
                    required=True,
                    description="Lazy tabular source to filter by row, column, and selection settings.",
                ),
                PortSpec(
                    TABULAR_WINDOW_OUTPUT_KEY,
                    "out",
                    "data",
                    'COREX.Runtime.TabularWindowRef',
                    "Window",
                    exposed=True,
                    description="Lazy reference to the selected table window.",
                ),
            ),
            properties=(
                *_bounds_properties(row_limit=1000, column_limit=0),
                PropertySpec("columns", "str", "", "Columns", inspector_visible=False, group="Selection"),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        table_ref = coerce_tabular_data_ref(ctx.inputs.get("table_data"))
        if table_ref is None:
            raise TypeError("Table Filter requires table_data as a tabular_data_ref.")
        return NodeResult(
            outputs={
                TABULAR_WINDOW_OUTPUT_KEY: _table_window_ref_from_properties(table_ref, ctx.properties),
            }
        )


class TabularArraySlice2DNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id=TABULAR_ARRAY_SLICE_2D_NODE_TYPE_ID,
            display_name=TABULAR_ARRAY_SLICE_2D_DISPLAY_NAME,
            category_path=(TABULAR_DATA_ADDON_CATEGORY,),
            icon="integrations/tabular_data.svg",
            description="Creates a lazy 2D array-slice reference from array data.",
            keywords=("array", "slice", "2d"),
            ports=(
                PortSpec(
                    "array_data",
                    "in",
                    "data",
                    'COREX.Runtime.ArrayDataRef',
                    "Array Data",
                    required=True,
                    description="Lazy dense-array source to slice by row and column bounds.",
                ),
                PortSpec(
                    TABULAR_ARRAY_SLICE_2D_OUTPUT_KEY,
                    "out",
                    "data",
                    'COREX.Runtime.ArraySlice2DRef',
                    "Slice 2D",
                    exposed=True,
                    description="Lazy reference to the selected two-dimensional array slice.",
                ),
            ),
            properties=_bounds_properties(row_limit=1000, column_limit=100),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        array_ref = coerce_array_data_ref(ctx.inputs.get("array_data"))
        if array_ref is None:
            raise TypeError("Array Slice 2D requires array_data as an array_data_ref.")
        return NodeResult(
            outputs={
                TABULAR_ARRAY_SLICE_2D_OUTPUT_KEY: _array_slice_ref_from_properties(array_ref, ctx.properties),
            }
        )


class TabularWriteTableWindowNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id=TABULAR_WRITE_TABLE_WINDOW_NODE_TYPE_ID,
            display_name=TABULAR_WRITE_TABLE_WINDOW_DISPLAY_NAME,
            category_path=(TABULAR_DATA_ADDON_CATEGORY,),
            icon="integrations/tabular_data.svg",
            description="Exports a lazy filtered table without materializing it as a list first.",
            keywords=("table", "export", "csv"),
            ports=(
                PortSpec(
                    "window",
                    "in",
                    "data",
                    'COREX.Runtime.TabularWindowRef',
                    "Window",
                    required=True,
                    data_access="tree",
                    description="Lazy filtered-table window to export.",
                ),
                PortSpec(
                    "path",
                    "in",
                    "data",
                    'COREX.DataTypes.Path',
                    "Path",
                    required=False,
                    uses_property_default=True,
                    data_access="tree",
                    description="Optional output path; a managed CSV is created when empty.",
                ),
                PortSpec(
                    "written_path",
                    "out",
                    "data",
                    'COREX.DataTypes.Path',
                    exposed=True,
                    description="Path or managed artifact reference for the exported table.",
                ),
            ),
            properties=(
                PropertySpec(
                    "path",
                    "path",
                    "",
                    "Output Path",
                    inline_editor="path",
                    inspector_editor="path",
                    group="Output",
                    file_filter=TABULAR_TABLE_OUTPUT_FILES_FILTER,
                ),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        ctx.inputs = resolve_single_run_inputs(ctx.inputs, node_name=TABULAR_WRITE_TABLE_WINDOW_DISPLAY_NAME)
        window_ref = coerce_tabular_window_ref(ctx.inputs.get("window"))
        if window_ref is None:
            raise TypeError("Write Filtered Table requires window as a tabular_window_ref.")
        path = pick_optional_path(ctx, input_key="path", property_key="path")
        if path is None:
            result = write_managed_output(
                ctx,
                output_key="written_path",
                default_suffix=".csv",
                managed_subdirectory="tabular/writes",
                write_payload=lambda output_path: _write_table_window_to_path(output_path, window_ref),
            )
            return NodeResult(outputs={"written_path": result.artifact_ref})
        _prepare_explicit_output_path(
            path,
            node_name=TABULAR_WRITE_TABLE_WINDOW_DISPLAY_NAME,
            suffixes=_TABLE_OUTPUT_SUFFIXES,
        )
        _write_table_window_to_path(path, window_ref)
        return NodeResult(outputs={"written_path": str(path)})


class TabularWriteArraySlice2DNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id=TABULAR_WRITE_ARRAY_SLICE_2D_NODE_TYPE_ID,
            display_name=TABULAR_WRITE_ARRAY_SLICE_2D_DISPLAY_NAME,
            category_path=(TABULAR_DATA_ADDON_CATEGORY,),
            icon="integrations/tabular_data.svg",
            description="Exports a lazy 2D array slice without materializing it through a script.",
            keywords=("array", "slice", "export"),
            ports=(
                PortSpec(
                    "slice_2d",
                    "in",
                    "data",
                    'COREX.Runtime.ArraySlice2DRef',
                    "Slice 2D",
                    required=True,
                    data_access="tree",
                    description="Lazy two-dimensional array slice to export.",
                ),
                PortSpec(
                    "path",
                    "in",
                    "data",
                    'COREX.DataTypes.Path',
                    "Path",
                    required=False,
                    uses_property_default=True,
                    data_access="tree",
                    description="Optional output path; a managed CSV is created when empty.",
                ),
                PortSpec(
                    "written_path",
                    "out",
                    "data",
                    'COREX.DataTypes.Path',
                    exposed=True,
                    description="Path or managed artifact reference for the exported array slice.",
                ),
            ),
            properties=(
                PropertySpec(
                    "path",
                    "path",
                    "",
                    "Output Path",
                    inline_editor="path",
                    inspector_editor="path",
                    group="Output",
                    file_filter=TABULAR_ARRAY_OUTPUT_FILES_FILTER,
                ),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        ctx.inputs = resolve_single_run_inputs(ctx.inputs, node_name=TABULAR_WRITE_ARRAY_SLICE_2D_DISPLAY_NAME)
        slice_ref = coerce_array_slice_2d_ref(ctx.inputs.get("slice_2d"))
        if slice_ref is None:
            raise TypeError("Write Array Slice 2D requires slice_2d as an array_slice_2d_ref.")
        path = pick_optional_path(ctx, input_key="path", property_key="path")
        if path is None:
            result = write_managed_output(
                ctx,
                output_key="written_path",
                default_suffix=".csv",
                managed_subdirectory="tabular/writes",
                write_payload=lambda output_path: _write_array_slice_to_path(output_path, slice_ref),
            )
            return NodeResult(outputs={"written_path": result.artifact_ref})
        _prepare_explicit_output_path(
            path,
            node_name=TABULAR_WRITE_ARRAY_SLICE_2D_DISPLAY_NAME,
            suffixes=_ARRAY_OUTPUT_SUFFIXES,
        )
        _write_array_slice_to_path(path, slice_ref)
        return NodeResult(outputs={"written_path": str(path)})


class TabularMaterializeTableWindowNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id=TABULAR_MATERIALIZE_TABLE_WINDOW_NODE_TYPE_ID,
            display_name=TABULAR_MATERIALIZE_TABLE_WINDOW_DISPLAY_NAME,
            category_path=(TABULAR_DATA_ADDON_CATEGORY,),
            icon="integrations/tabular_data.svg",
            description="Loads a filtered table into memory as list[dict] for scripts and debugging.",
            keywords=("table", "materialize", "rows"),
            ports=(
                PortSpec(
                    "window",
                    "in",
                    "data",
                    'COREX.Runtime.TabularWindowRef',
                    "Window",
                    required=True,
                    description="Lazy filtered-table window to materialize.",
                ),
                PortSpec(
                    "rows",
                    "out",
                    "data",
                    'COREX.DataTypes.GraphDictionary',
                    "Rows",
                    exposed=True,
                    data_access="list",
                    description="Materialized table rows represented as dictionaries.",
                ),
            ),
            properties=(),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        window_ref = coerce_tabular_window_ref(ctx.inputs.get("window"))
        if window_ref is None:
            raise TypeError("Materialize Filtered Table requires window as a tabular_window_ref.")
        warnings: tuple[str, ...] = ()
        if window_ref.row_limit == 0 or window_ref.column_limit == 0:
            message = _unbounded_table_message(window_ref)
            ctx.log_warning(message)
            warnings = (message,)
        rows = [dict(row) for row in load_table_window(window_ref).rows]
        return NodeResult(outputs={"rows": rows}, warnings=warnings)


class TabularMaterializeArraySlice2DNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id=TABULAR_MATERIALIZE_ARRAY_SLICE_2D_NODE_TYPE_ID,
            display_name=TABULAR_MATERIALIZE_ARRAY_SLICE_2D_DISPLAY_NAME,
            category_path=(TABULAR_DATA_ADDON_CATEGORY,),
            icon="integrations/tabular_data.svg",
            description="Loads a 2D array slice into memory as list[list] for scripts and debugging.",
            keywords=("array", "materialize", "values"),
            ports=(
                PortSpec(
                    "slice_2d",
                    "in",
                    "data",
                    'COREX.Runtime.ArraySlice2DRef',
                    "Slice 2D",
                    required=True,
                    description="Lazy two-dimensional array slice to materialize.",
                ),
                PortSpec(
                    "values",
                    "out",
                    "data",
                    'COREX.DataTypes.GraphArray',
                    "Values",
                    exposed=True,
                    data_access="list",
                    description="Materialized two-dimensional values represented as nested lists.",
                ),
            ),
            properties=(),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        slice_ref = coerce_array_slice_2d_ref(ctx.inputs.get("slice_2d"))
        if slice_ref is None:
            raise TypeError("Materialize Array Slice 2D requires slice_2d as an array_slice_2d_ref.")
        warnings: tuple[str, ...] = ()
        if slice_ref.row_limit == 0 or slice_ref.column_limit == 0:
            message = _unbounded_array_message(slice_ref)
            ctx.log_warning(message)
            warnings = (message,)
        values = [list(row) for row in load_array_slice_2d(slice_ref).values]
        return NodeResult(outputs={"values": values}, warnings=warnings)


TABULAR_EXTRACTION_NODE_DESCRIPTORS = (
    plugin_descriptor(TabularTableWindowNodePlugin),
    plugin_descriptor(TabularArraySlice2DNodePlugin),
    plugin_descriptor(TabularWriteTableWindowNodePlugin),
    plugin_descriptor(TabularWriteArraySlice2DNodePlugin),
    plugin_descriptor(TabularMaterializeTableWindowNodePlugin),
    plugin_descriptor(TabularMaterializeArraySlice2DNodePlugin),
)

__all__ = [
    "ARRAY_SLICE_COLUMN_COUNT_PROPERTY",
    "ARRAY_SLICE_COLUMN_START_PROPERTY",
    "ARRAY_SLICE_ROW_COUNT_PROPERTY",
    "ARRAY_SLICE_ROW_START_PROPERTY",
    "ARRAY_SLICE_SUMMARY_PROPERTY",
    "TABLE_WINDOW_COLUMN_COUNT_PROPERTY",
    "TABLE_WINDOW_COLUMN_START_PROPERTY",
    "TABLE_WINDOW_COLUMNS_PROPERTY",
    "TABLE_WINDOW_ROW_COUNT_PROPERTY",
    "TABLE_WINDOW_ROW_START_PROPERTY",
    "TABLE_WINDOW_SUMMARY_PROPERTY",
    "TABULAR_ARRAY_SLICE_2D_DISPLAY_NAME",
    "TABULAR_ARRAY_SLICE_2D_NODE_TYPE_ID",
    "TABULAR_ARRAY_SLICE_2D_OUTPUT_KEY",
    "TABULAR_EXTRACTION_NODE_DESCRIPTORS",
    "TABULAR_MATERIALIZE_ARRAY_SLICE_2D_NODE_TYPE_ID",
    "TABULAR_MATERIALIZE_TABLE_WINDOW_NODE_TYPE_ID",
    "TABULAR_TABLE_WINDOW_DISPLAY_NAME",
    "TABULAR_TABLE_WINDOW_NODE_TYPE_ID",
    "TABULAR_WINDOW_OUTPUT_KEY",
    "TABULAR_WRITE_ARRAY_SLICE_2D_NODE_TYPE_ID",
    "TABULAR_WRITE_TABLE_WINDOW_NODE_TYPE_ID",
    "TabularArraySlice2DNodePlugin",
    "TabularMaterializeArraySlice2DNodePlugin",
    "TabularMaterializeTableWindowNodePlugin",
    "TabularTableWindowNodePlugin",
    "TabularWriteArraySlice2DNodePlugin",
    "TabularWriteTableWindowNodePlugin",
    "load_array_slice_2d",
    "load_table_window",
    "stream_array_slice_2d_rows",
    "stream_table_window_rows",
    "table_window_columns",
    "write_array_rows_to_path",
    "write_table_rows_to_path",
]
