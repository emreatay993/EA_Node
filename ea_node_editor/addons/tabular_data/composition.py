# Purpose: Compile and read lazy table views from one file's physical members.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composition.py
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ea_node_editor.runtime_contracts import ArrayDataRef, ArrayMaterializationOptions, TabularColumn, TabularDataRef
from ea_node_editor.runtime_contracts.data_view import DataViewDefinition, projection_axes


@dataclass(frozen=True, slots=True)
class ViewBlock:
    ref: TabularDataRef | ArrayDataRef
    columns: tuple[TabularColumn, ...]
    positions: tuple[int, ...]
    rows: int
    axes: tuple[int, int | None, dict[int, int]] | None = None


@dataclass(frozen=True, slots=True)
class ViewSegment:
    blocks: tuple[ViewBlock, ...]
    rows: int


@dataclass(frozen=True, slots=True)
class CompiledView:
    definition: DataViewDefinition
    segments: tuple[ViewSegment, ...]
    base_columns: tuple[TabularColumn, ...]
    columns: tuple[TabularColumn, ...]
    total_rows: int
    row_offset: int
    row_count: int
    query_path: Path | None = None


def _position(selector: str | int, names: Sequence[str]) -> int:
    if type(selector) is int:
        if 0 <= selector < len(names):
            return selector
        raise ValueError(f"Column position {selector + 1} is outside the source")
    if names.count(selector) != 1:
        raise ValueError(f"Column {selector!r} is missing or ambiguous")
    return names.index(selector)


def _dtype(dtype: str) -> Any:
    import numpy as np

    aliases = {"string": "str", "large_string": "str", "bool": "bool", "boolean": "bool", "int": "int64"}
    if dtype.startswith("timestamp["):
        unit = dtype.split("[", 1)[1].split("]", 1)[0].split(",", 1)[0]
        return np.dtype(f"datetime64[{unit}]")
    if dtype.startswith("date32"):
        return np.dtype("datetime64[D]")
    if dtype.startswith("date64"):
        return np.dtype("datetime64[ms]")
    try:
        return np.dtype(aliases.get(dtype, dtype))
    except TypeError as exc:
        raise ValueError(f"Unsupported composed column type {dtype!r}") from exc


def arrow_type(dtype: str):
    import pyarrow as pa
    if dtype.startswith("timestamp["):
        parts = dtype.split("[", 1)[1].rstrip("]").split(",")
        zone = next((part.strip()[3:] for part in parts[1:] if part.strip().startswith("tz=")), None)
        return pa.timestamp(parts[0].strip(), tz=zone)
    if dtype == "large_string":
        return pa.large_string()
    if dtype.startswith("date32"):
        return pa.date32()
    if dtype.startswith("date64"):
        return pa.date64()
    return pa.from_numpy_dtype(_dtype(dtype))


def view_scalar_json(value, column):
    from ea_node_editor.addons.tabular_data.source_backends import json_safe_value
    if "tz=" in column.dtype and value is not None:
        import numpy as np
        import pandas as pd
        if np.isnat(value):
            return None
        zone = column.dtype.split("tz=", 1)[1].rstrip("]").strip()
        return pd.Timestamp(value).tz_localize("UTC").tz_convert(zone).isoformat()
    return json_safe_value(value)


def _promote(left: str, right: str) -> str:
    import numpy as np

    if left == right:
        return left
    a, b = _dtype(left), _dtype(right)
    if a.kind in "US" and b.kind in "US":
        return "string"
    if a.kind == b.kind == "M":
        if a != b:
            raise ValueError("Appended datetime columns require matching precision")
        return str(a)
    if a.kind not in "iuf" or b.kind not in "iuf":
        raise ValueError(f"Cannot append incompatible types {left} and {right}")
    result = np.result_type(a, b)
    if result.kind == "f":
        precision = np.finfo(result).nmant + 1
        for item in (a, b):
            if item.kind in "iu" and item.itemsize * 8 - (item.kind == "i") > precision:
                raise ValueError(f"Appending {left} and {right} would lose integer precision")
    if not np.can_cast(a, result, casting="safe") or not np.can_cast(b, result, casting="safe"):
        raise ValueError(f"Appending {left} and {right} would lose values")
    return str(result)


def _bound_physical_ref(service, path, options, content_sha256):
    """Build from fresh metadata and SHA-keyed caches inside an accepted read."""
    from ea_node_editor.addons.tabular_data.source_backends import TEXT_FORMAT_IDS, detect_format_id

    scan = service._scan_uncached(path, detect_format_id(path), options, service._source_stats(path))
    selected = service._resolve_selected_object(scan, options)
    options = options.with_selected_object(selected.object_id)
    if scan.format_id in TEXT_FORMAT_IDS:
        selected = replace(selected, row_count=service._cached_parquet_row_count(path, options, content_sha256=content_sha256))
    table = selected.kind == "table"
    builder = service._build_table_record if table else service._build_array_record
    record = replace(builder(scan, selected, options), content_sha256=content_sha256)
    ref_id = service._ref_id("table" if table else "array", record) + "_" + content_sha256
    records = service._table_records if table else service._array_records
    with service._records_lock:
        records[ref_id] = record
    fields = dict(ref_id=ref_id, resolver_id=service.resolver_id, backend_id=record.backend_id,
                  source_uri=path.as_uri(), object_id=record.object_id,
                  metadata=service._record_metadata(record.format_id, record.size_bytes, record.warnings, options=options))
    return TabularDataRef(**fields, row_count=record.row_count, column_count=len(record.columns)) if table else ArrayDataRef(**fields, shape=record.shape, dtype=record.dtype)


def compile_view(service: Any, path: Any, options: Any, *, content_sha256: str = "") -> CompiledView:
    from ea_node_editor.addons.tabular_data.source_backends import TabularCacheNotReadyError

    view = options.data_view
    if not isinstance(view, DataViewDefinition):
        raise ValueError("A data-view definition is required")
    recipe = view.to_payload()
    members: dict[str, TabularDataRef | ArrayDataRef] = {}

    def physical(member: str) -> TabularDataRef | ArrayDataRef:
        if member in members:
            return members[member]
        physical_options = replace(options, selected_object=member, data_view=None)
        ref = (_bound_physical_ref(service, path, physical_options, content_sha256) if content_sha256
               else service.open_source(path, physical_options))
        members[member] = ref
        return ref

    def block_info(block: Mapping[str, Any]) -> ViewBlock:
        ref = physical(block["member"])
        axes = None
        if isinstance(ref, ArrayDataRef):
            axes = projection_axes(block["axes"], ref.shape)
            rows = ref.shape[axes[0]]
            width = ref.shape[axes[1]] if axes[1] is not None else 1
            names = tuple((ref.object_id if width == 1 else f"Column {i + 1}") for i in range(width))
            columns = tuple(TabularColumn(name, ref.dtype) for name in names)
        else:
            schema = service.column_schema(ref)
            if schema.row_count is None:
                # Typed text/Excel metadata may only become exact after its managed cache is prepared.
                record = service._table_record(ref)
                service._ensure_record_parquet_cache(ref, record)
                schema = service.schema(ref)
            if schema.row_count is None:
                raise TabularCacheNotReadyError(source_path=path, size_bytes=path.stat().st_size)
            rows, columns = schema.row_count, schema.columns
            names = tuple(c.name for c in columns)
        if block["labels_member"]:
            label_ref = physical(block["labels_member"])
            if isinstance(label_ref, ArrayDataRef):
                if len(label_ref.shape) != 1 or label_ref.shape[0] != len(columns):
                    raise ValueError(f"{block['labels_member']} must contain {len(columns)} column labels")
                labels = service.to_numpy(label_ref, ArrayMaterializationOptions(max_elements=len(columns)))
            else:
                label_schema = service.column_schema(label_ref)
                if label_schema.row_count != len(columns):
                    raise ValueError(f"{block['labels_member']} must contain {len(columns)} column labels")
                selected = block["labels_column"]
                if selected is None:
                    if len(label_schema.columns) != 1:
                        raise ValueError("Choose a column from the labels dataset")
                    selected = 0
                labels = service.column_arrays(label_ref, columns=[selected], row_limit=len(columns))[selected]
            from ea_node_editor.addons.tabular_data.source_backends import json_safe_value
            names = tuple("" if json_safe_value(value) is None else str(json_safe_value(value)) for value in labels)
        selected = tuple(_position(value, names) for value in block["columns"]) if block["columns"] else tuple(range(len(columns)))
        renamed = block["names"]
        result = tuple(TabularColumn(
            block["prefix"] + renamed.get(str(i), renamed.get(names[i], names[i])), columns[i].dtype,
            columns[i].nullable, {**columns[i].metadata, "view_column_id": f"{block['id']}:{i}", "unit": block["unit"] or columns[i].metadata.get("unit", "")},
        ) for i in selected)
        return ViewBlock(ref, result, selected, rows, axes)

    segments = []
    all_columns: tuple[TabularColumn, ...] = ()
    for segment_data in recipe["segments"]:
        blocks = [block_info(block) for block in segment_data["blocks"]]
        rows = blocks[0].rows
        if any(block.rows != rows for block in blocks):
            raise ValueError("Add columns requires equal row counts; rows are matched by position")
        coordinate = segment_data["coordinate"]
        if coordinate is not None:
            coord_ref = physical(coordinate["member"])
            coordinate_axis = 1 if isinstance(coord_ref, ArrayDataRef) and len(coord_ref.shape) == 2 else None
            coord_recipe = {"id": "coordinate", "member": coordinate["member"], "axes": {"row": 0, "column": coordinate_axis, "fixed": {}},
                            "columns": [] if coordinate["column"] is None else [coordinate["column"]], "labels_member": "", "labels_column": None,
                            "names": {}, "prefix": "", "unit": coordinate["unit"]}
            coord = block_info(coord_recipe)
            if len(coord.columns) != 1 or coord.rows != rows:
                raise ValueError(f"Row coordinate must be one column with {rows} values")
            coord = replace(coord, columns=(replace(coord.columns[0], name=coordinate["name"]),))
            blocks.insert(0, coord)
        columns = tuple(column for block in blocks for column in block.columns)
        names = tuple(column.name for column in columns)
        if not names or any(not name.strip() for name in names) or len(set(names)) != len(names):
            raise ValueError("Output column names must be unique and nonblank; rename columns or add a block prefix")
        if not segments:
            all_columns = columns
        else:
            first_names = tuple(c.name for c in all_columns)
            if set(first_names) != set(names):
                missing = sorted(set(first_names) - set(names))
                extra = sorted(set(names) - set(first_names))
                raise ValueError(f"Append rows column mismatch: missing {missing}; extra {extra}")
            by_name = {column.name: column for column in columns}
            promoted = []
            for column in all_columns:
                other = by_name[column.name]
                if column.metadata.get("unit", "") != other.metadata.get("unit", ""):
                    raise ValueError(f"Units do not match for appended column {column.name!r}")
                promoted.append(replace(column, dtype=_promote(column.dtype, other.dtype), nullable=column.nullable or other.nullable))
            all_columns = tuple(promoted)
        segments.append(ViewSegment(tuple(blocks), rows))
    total = sum(segment.rows for segment in segments)
    output = recipe["output"]
    names = tuple(c.name for c in all_columns)
    columns = tuple(all_columns[_position(value, names)] for value in output["columns"]) if output["columns"] else all_columns
    for rule in (*recipe["query"]["filters"], *recipe["query"]["sort"]):
        _position(rule["column"], names)
    offset = min(output["row_offset"], total)
    rows = min(output["row_limit"] or total, total - offset)
    return CompiledView(view, tuple(segments), all_columns, columns, total, offset, rows)


def _read_block(service: Any, block: ViewBlock, offset: int, rows: int, wanted: set[str]) -> dict[str, Any]:
    import numpy as np

    chosen = [(column, position) for column, position in zip(block.columns, block.positions, strict=True) if column.name in wanted]
    if not chosen:
        return {}
    if isinstance(block.ref, TabularDataRef):
        arrays = service.column_arrays(block.ref, columns=tuple(position for _, position in chosen), row_offset=offset, row_limit=rows)
        return {column.name: arrays[position] for column, position in chosen}
    row_axis, column_axis, fixed = block.axes
    array = service._open_array(service._array_record(block.ref))
    slices: list[Any] = [slice(None)] * len(block.ref.shape)
    for axis, index in fixed.items():
        slices[axis] = index
    slices[row_axis] = slice(offset, offset + rows)
    if column_axis is None:
        return {chosen[0][0].name: np.array(array[tuple(slices)], copy=True)}
    result = {}
    for column, position in chosen:
        slices[column_axis] = position
        result[column.name] = np.array(array[tuple(slices)], copy=True)
    return result


def read_view_arrays(service: Any, view: CompiledView, *, row_offset: int, row_limit: int,
                     columns: Sequence[str], base: bool = False) -> dict[str, Any]:
    import numpy as np

    if view.query_path is not None and not base:
        from ea_node_editor.addons.tabular_data.saved_queries import read_query_arrays

        return read_query_arrays(view, row_offset=row_offset, row_limit=row_limit, columns=tuple(columns))

    archive_members = {}
    for segment in view.segments:
        for block in segment.blocks:
            if isinstance(block.ref, ArrayDataRef) and block.ref.metadata.get("format_id") == "npz" and any(column.name in columns for column in block.columns):
                archive_members[block.ref.object_id] = int(np.prod(block.ref.shape, dtype=object)) * np.dtype(block.ref.dtype).itemsize + 128
    if sum(archive_members.values()) > service._npz_member_cache.max_bytes:
        raise ValueError("Selected NPZ arrays exceed the managed cache budget; choose fewer sources or extract them as NPY files")

    offset = row_offset + (0 if base else view.row_offset)
    available = view.total_rows if base else view.row_count
    count = min(row_limit or available, max(0, available - row_offset))
    chunks: dict[str, list[Any]] = {name: [] for name in columns}
    start = 0
    for segment in view.segments:
        from ea_node_editor.addons.tabular_data.operations import check_cancelled

        check_cancelled()
        local_start = max(0, offset - start)
        local_stop = min(segment.rows, offset + count - start)
        if local_start < local_stop:
            for block in segment.blocks:
                for name, values in _read_block(service, block, local_start, local_stop - local_start, set(columns)).items():
                    chunks[name].append(values)
        start += segment.rows
        if start >= offset + count:
            break
    types = {column.name: column.dtype for column in view.base_columns}
    result = {}
    for name, arrays in chunks.items():
        if arrays:
            result[name] = np.concatenate(arrays) if len(arrays) > 1 else arrays[0]
            target = _dtype(types[name])
            if target.kind not in "USO" and result[name].dtype.kind != "O":
                result[name] = result[name].astype(target, copy=False)
        else:
            dtype = _dtype(types[name])
            result[name] = np.array([], dtype=dtype)
    return result


def view_batches(service: Any, view: CompiledView, *, columns: Sequence[str], row_offset: int = 0,
                 row_limit: int = 0, batch_size: int = 65536, base: bool = False) -> Iterator[Any]:
    import pyarrow as pa

    available = view.total_rows if base else view.row_count
    dtypes = {column.name: column.dtype for column in view.base_columns}
    stop = min(available, row_offset + row_limit) if row_limit else available
    for offset in range(row_offset, stop, batch_size):
        arrays = read_view_arrays(service, view, row_offset=offset, row_limit=min(batch_size, stop - offset), columns=columns, base=base)
        yield pa.RecordBatch.from_arrays([pa.array(arrays[name], type=arrow_type(dtypes[name])) for name in columns], names=list(columns))


def needs_composition(view: DataViewDefinition | None) -> bool:
    if view is None or view.mode == "array":
        return False
    return view.mode == "table" or view.has_query or any(view.to_payload()["output"].values())


def composed_record(service: Any, path: Any, options: Any, *, content_sha256: str = "") -> Any:
    from ea_node_editor.addons.tabular_data.source_backends import TableRecord, detect_format_id

    definition = options.data_view
    if definition.mode == "source":
        payload = definition.to_payload()
        payload["mode"] = "table"
        payload["segments"] = [{"blocks": [{"member": definition.member or options.selected_object}]}]
        definition = DataViewDefinition(payload)
    compiled = compile_view(service, path, replace(options, data_view=definition), content_sha256=content_sha256)
    stats = service._source_stats(path)
    return TableRecord(source_path=path, format_id=detect_format_id(path), options=options,
                       object_id="view:" + options.data_view.digest, backend_id="tabular_composed",
                       columns=compiled.columns, row_count=None if definition.has_query else compiled.row_count,
                       size_bytes=stats.size_bytes, warnings=service.policy.warnings_for_size(stats.size_bytes),
                       stats=stats, content_sha256=content_sha256, view=compiled)


def open_composed_source(service: Any, path: Any, options: Any) -> TabularDataRef:
    from ea_node_editor.common.payload_tools import REF_METADATA_MAX_BYTES
    import json

    record = composed_record(service, path, options)
    ref_id = service._ref_id("table", record)
    with service._records_lock:
        service._table_records[ref_id] = record
    metadata = service._record_metadata(record.format_id, record.size_bytes, record.warnings, options=record.options)
    metadata["column_schema"] = [column.to_payload() for column in record.columns]
    if len(json.dumps(metadata, ensure_ascii=False).encode("utf-8")) > REF_METADATA_MAX_BYTES:
        del metadata["column_schema"]
    return TabularDataRef(ref_id=ref_id, resolver_id=service.resolver_id, backend_id=record.backend_id,
                          source_uri=path.as_uri(), object_id=record.object_id, row_count=record.row_count,
                          column_count=len(record.columns), metadata=metadata)
