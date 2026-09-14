# Purpose: Prepare and reopen complete output queries without importing DuckDB in Qt.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_saved_queries.py
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from dataclasses import replace
from typing import Any

from ea_node_editor.addons.tabular_data.composition import _dtype, arrow_type, view_batches
from ea_node_editor.execution.managed_runtime import resolve_addon_runtime_paths
from ea_node_editor.settings import TABULAR_DATA_CACHE_MAX_BYTES


def ensure_saved_query(service: Any, record: Any, *, cancel_event: threading.Event | None = None) -> Any:
    from ea_node_editor.addons.tabular_data.operations import current_cancel_event

    cancel_event = cancel_event or current_cancel_event()
    if record.view is None or not record.view.definition.has_query or record.view.query_path is not None:
        return record
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq

    view = record.view
    key = service._ref_id("query", record) + ("_" + record.content_sha256 if record.content_sha256 else "")
    directory = service.cache_dir / "views"
    destination = directory / (key + ".parquet")
    with service._conversion_locks_guard:
        lock = service._conversion_locks.setdefault(key, threading.Lock())
    with lock:
        if not destination.is_file():
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=key + "-", dir=directory) as working:
                temporary_dir = Path(working)
                input_path = temporary_dir / "input.parquet"
                output_path = temporary_dir / "output.parquet"
                all_names = tuple(column.name for column in view.base_columns)
                rules = view.definition.to_payload()["query"]
                needed = {column.name for column in view.columns} | {rule["column"] for rule in (*rules["filters"], *rules["sort"])}
                selected = [(i, column) for i, column in enumerate(view.base_columns) if column.name in needed]
                needed_names = tuple(column.name for _, column in selected)
                schema = pa.schema([pa.field(f"c{i}", pa.int64() if _dtype(column.dtype).kind == "M" else arrow_type(column.dtype))
                                    for i, column in selected] + [pa.field("__row_ordinal", pa.int64())])
                ordinal = 0
                with pq.ParquetWriter(input_path, schema) as writer:
                    for batch in view_batches(service, view, columns=needed_names, base=True):
                        if cancel_event is not None and cancel_event.is_set():
                            raise InterruptedError("Data query cancelled")
                        columns = []
                        for i in range(len(needed_names)):
                            values = batch.column(i)
                            if pa.types.is_date32(values.type):
                                values = values.cast(pa.int32())
                            columns.append(values.cast(schema.field(i).type))
                        columns.append(pa.array(np.arange(ordinal, ordinal + batch.num_rows, dtype=np.int64)))
                        writer.write_batch(pa.RecordBatch.from_arrays(columns, schema=schema))
                        ordinal += batch.num_rows
                        service._reserve_member_cache(0)
                remaining_budget = TABULAR_DATA_CACHE_MAX_BYTES - service.cache_usage_bytes()
                if remaining_budget <= 0:
                    raise ValueError("Composed query exceeds the managed cache budget")
                request = {
                    "definition": view.definition.to_payload(), "columns": list(all_names),
                    "column_types": {column.name: column.dtype for column in view.base_columns},
                    "input_path": str(input_path), "output_path": str(output_path),
                    "temporary_directory": str(temporary_dir / "spill"),
                    "temporary_budget": str(max(1, remaining_budget // 2)) + "B",
                }
                runtime = resolve_addon_runtime_paths()
                process = subprocess.Popen(
                    [str(runtime.python_executable), "-I", "-m", "ea_node_editor.addons.tabular_data.query_worker"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                try:
                    encoded = json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
                    while True:
                        if cancel_event is not None and cancel_event.is_set():
                            raise InterruptedError("Data query cancelled")
                        try:
                            stdout, stderr = process.communicate(input=encoded, timeout=0.1)
                            break
                        except subprocess.TimeoutExpired:
                            encoded = None
                    response = json.loads(stdout.decode("utf-8")) if stdout else {}
                    if process.returncode or not response.get("ok"):
                        raise ValueError(response.get("error") or stderr.decode("utf-8", errors="replace")[:2000] or "Data query worker failed")
                    current = service._source_stats(record.source_path)
                    if current != record.stats:
                        raise ValueError("Source changed while preparing the configured output")
                    service._reserve_member_cache(0)
                    os.replace(output_path, destination)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.communicate()
        with pq.ParquetFile(destination) as parquet:
            count = parquet.metadata.num_rows
    return replace(record, row_count=count, view=replace(view, query_path=destination, row_count=count, row_offset=0))


def read_query_arrays(view: Any, *, row_offset: int, row_limit: int, columns: tuple[str, ...]) -> dict[str, Any]:
    import numpy as np
    import pyarrow.parquet as pq
    from ea_node_editor.addons.tabular_data.loader_cache_service import _exact_arrow_numpy

    original = tuple(column.name for column in view.base_columns)
    names = {name: f"c{original.index(name)}" for name in columns}
    wanted = list(names.values())
    count = min(row_limit or view.row_count, max(0, view.row_count - row_offset))
    chunks: dict[str, list[Any]] = {name: [] for name in columns}
    start = 0
    with pq.ParquetFile(view.query_path) as parquet:
        for group in range(parquet.metadata.num_row_groups):
            rows = parquet.metadata.row_group(group).num_rows
            local_start = max(0, row_offset - start)
            local_stop = min(rows, row_offset + count - start)
            if local_start < local_stop:
                table = parquet.read_row_group(group, columns=wanted).slice(local_start, local_stop - local_start)
                for name, internal in names.items():
                    chunks[name].append(_exact_arrow_numpy(table.column(internal)))
            start += rows
            if start >= row_offset + count:
                break
    types = {column.name: column.dtype for column in view.columns}
    result = {}
    for name, values in chunks.items():
        dtype = _dtype(types[name])
        merged = np.concatenate(values) if values else np.array([], dtype=dtype)
        if dtype.kind == "M" and len(merged):
            integers = np.array([np.iinfo(np.int64).min if value is None else int(value) for value in merged], dtype=np.int64) if merged.dtype.kind == "O" else merged.astype(np.int64, copy=False)
            merged = integers.view(dtype)
        result[name] = merged
    return result
