# Purpose: Export a draft's visible, selected or complete configured data on a worker.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_export.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from ea_node_editor.addons.tabular_data.exporting import atomic_tabular_output
from ea_node_editor.addons.tabular_data.extraction_nodes import write_array_rows_to_path, write_table_rows_to_path
from ea_node_editor.addons.tabular_data.input_node import tabular_load_options_from_node_properties
from ea_node_editor.addons.tabular_data.operations import check_cancelled
from ea_node_editor.addons.tabular_data.source_backends import json_safe_value
from ea_node_editor.runtime_contracts import ArrayDataRef, ArrayMaterializationOptions, ArraySlice2DRequest, TabularDataRef, TabularWindowRequest
from ea_node_editor.ui.tabular_preview_provider import TabularPreviewProvider


def export_composer_data(*, properties: dict[str, Any], project_context: Any, preview: dict[str, Any],
                         scope: str, selection: dict[str, Any], output_path: Path, service=None) -> dict[str, Any]:
    provider = TabularPreviewProvider(project_context_provider=lambda: project_context,
                                     service_factory=(lambda: service) if service is not None else None)
    source = provider._resolver().resolve(str(properties.get("path", ""))).absolute_path
    if source is None or not source.is_file():
        raise ValueError("The source file is unavailable")
    if output_path.resolve() == source.resolve():
        raise ValueError("Choose an output file different from the source file")
    if scope not in {"visible", "selection", "output"}:
        raise ValueError("Unknown export scope")
    stamp = source.stat()
    loader = service or provider._service_factory()
    ref = loader.open_source(source, tabular_load_options_from_node_properties(properties))
    written = 0

    def checked(rows):
        nonlocal written
        for row in rows:
            check_cancelled()
            written += 1
            yield row
        current = source.stat()
        if (current.st_size, current.st_mtime_ns) != (stamp.st_size, stamp.st_mtime_ns):
            raise ValueError("Source changed during export; no output was published")

    if scope == "output":
        if isinstance(ref, TabularDataRef):
            columns = tuple(column.name for column in loader.schema(ref).columns)
            rows = loader.iter_window_rows(ref, TabularWindowRequest(row_limit=0, column_limit=0))
            write_table_rows_to_path(output_path, columns=columns, rows=checked(rows))
        elif output_path.suffix.lower() == ".npy":
            written = _export_array_npy(loader, ref, output_path, source, stamp)
        else:
            if len(ref.shape) > 2:
                raise ValueError("Export an ND array as NPY, or build a table with explicit axes")
            def array_rows():
                count = ref.shape[0] if ref.shape else 1
                width = ref.shape[1] if len(ref.shape) > 1 else 1
                for offset in range(0, count, 4096):
                    yield from loader.slice_2d(ref, ArraySlice2DRequest(row_offset=offset, row_limit=min(4096, count - offset), column_limit=width)).values
            write_array_rows_to_path(output_path, rows=checked(array_rows()))
    else:
        if preview.get("state") != "ready":
            raise ValueError("The preview is not ready")
        array = preview.get("preview_kind") == "array"
        window = preview.get("slice_2d" if array else "window", {})
        values = window.get("values" if array else "rows", [])
        columns = ([f"C{window.get('column_offset', 0) + i}" for i in range(len(values[0]) if values else 0)]
                   if array else list(window.get("columns", [])))
        indexes = list(range(len(columns)))
        if scope == "selection":
            selected_columns = selection.get("columns", [])
            if selected_columns:
                if any(name not in columns for name in selected_columns):
                    raise ValueError("Selected columns are no longer visible")
                indexes = [columns.index(name) for name in selected_columns]
            else:
                row, column = selection.get("row", -1), selection.get("column", -1)
                if not 0 <= row < len(values) or not 0 <= column < len(columns):
                    raise ValueError("Select a visible cell or column before exporting")
                values = [values[row]]
                indexes = [column]
        selected_names = [columns[i] for i in indexes]
        if array:
            write_array_rows_to_path(output_path, rows=checked([[row[i] for i in indexes] for row in values]))
        else:
            write_table_rows_to_path(output_path, columns=selected_names,
                                     rows=checked([{name: json_safe_value(row.get(name)) for name in selected_names} for row in values]))
    return {"ok": True, "path": str(output_path), "rows": written, "scope": scope}


def _export_array_npy(loader, ref: ArrayDataRef, output_path: Path, source: Path, stamp) -> int:
    import numpy as np

    with atomic_tabular_output(output_path) as temporary:
        target = np.lib.format.open_memmap(temporary, mode="w+", dtype=np.dtype(ref.dtype), shape=ref.shape)
        try:
            if not ref.shape:
                target[()] = loader.to_numpy(ref, ArrayMaterializationOptions(max_elements=1)).reshape(-1)[0]
            else:
                import math
                budget = 8 * 1024 * 1024
                item_size = np.dtype(ref.dtype).itemsize
                if item_size > budget:
                    raise ValueError("One array cell exceeds the bounded export buffer")
                axis = 0
                while axis < len(ref.shape) - 1 and math.prod(ref.shape[axis + 1:]) * item_size > budget:
                    axis += 1
                per_item = max(1, math.prod(ref.shape[axis + 1:]) * item_size)
                step = max(1, min(4096, budget // per_item))
                for prefix in np.ndindex(ref.shape[:axis]):
                    for offset in range(0, ref.shape[axis], step):
                        check_cancelled()
                        count = min(step, ref.shape[axis] - offset)
                        slices = tuple((index, 1) for index in prefix) + ((offset, count),) + tuple((0, size) for size in ref.shape[axis + 1:])
                        values = loader.to_numpy(ref, ArrayMaterializationOptions(slices=slices))
                        destination = prefix + (slice(offset, offset + count),) + tuple(slice(None) for _ in ref.shape[axis + 1:])
                        target[destination] = values.reshape((count,) + ref.shape[axis + 1:])
            target.flush()
        finally:
            del target
        current = source.stat()
        if (current.st_size, current.st_mtime_ns) != (stamp.st_size, stamp.st_mtime_ns):
            raise ValueError("Source changed during export; no output was published")
    return ref.shape[0] if ref.shape else 1
