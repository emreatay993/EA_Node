# Purpose: Stream full-fidelity Plot data and publish paired managed export artifacts.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_generic_plot_exports.py, tests/test_plot_headless_export.py
from __future__ import annotations

import copy
import csv
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ea_node_editor.nodes.builtins.plot import data_series, specs
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.nodes.output_artifacts import (
    allocate_managed_output,
    artifact_store_for_context,
    persist_artifact_store,
    register_staged_path_artifact,
)
from ea_node_editor.runtime_contracts import (
    ArraySlice2DRequest,
    coerce_array_data_ref,
    coerce_array_slice_2d_ref,
    coerce_tabular_data_ref,
)

if TYPE_CHECKING:
    from ea_node_editor.execution.plot_backend import PlotExportResult, PlotRenderRequest


def _default_backend_per_type(definition: specs.PlotNodeDefinition) -> dict[str, str]:
    return {
        "default": specs.MATPLOTLIB_PLOT_BACKEND_ID,
        definition.plot_type: specs.MATPLOTLIB_PLOT_BACKEND_ID,
    }


def _export_format(properties: Mapping[str, Any], key: str, default: str) -> str:
    normalized = str(properties.get(key, default) or default).strip().lower().lstrip(".")
    return normalized or default


def _runtime_artifact_metadata(result: PlotExportResult | None) -> dict[str, Any]:
    if result is None:
        return {}
    return {
        "backend_id": result.backend_id,
        "format": result.format,
        "metadata": copy.deepcopy(result.metadata),
    }


def archive_plot_exports(
    ctx: ExecutionContext,
    render_request: PlotRenderRequest,
    properties: Mapping[str, Any],
    *,
    definition: specs.PlotNodeDefinition,
) -> dict[str, Any]:
    from ea_node_editor.execution.plot_backend import (
        PlotDataExportRequest,
        PlotStaticExportRequest,
        create_plot_backend_registry,
    )

    backend_id = str(properties.get("backend", "") or "").strip() or specs.AUTO_PLOT_BACKEND_ID
    registry = create_plot_backend_registry()
    default_backend_per_type = _default_backend_per_type(definition)
    static_backend = registry.resolve(
        backend_id,
        plot_type=definition.plot_type,
        surface=specs.PLOT_SURFACE_STATIC_EXPORT,
        plot_default_backend_per_type=default_backend_per_type,
        require_headless_safe=True,
    )
    data_backend = registry.resolve(
        backend_id,
        plot_type=definition.plot_type,
        surface=specs.PLOT_SURFACE_DATA_EXPORT,
        plot_default_backend_per_type=default_backend_per_type,
        require_headless_safe=True,
    )

    static_format = _export_format(properties, "static_export_format", "png")
    data_format = _export_format(properties, "data_export_format", "csv")
    static_result: PlotExportResult | None = None
    data_result: PlotExportResult | None = None

    def write_static(output_path):
        nonlocal static_result
        static_result = static_backend.export_static(
            PlotStaticExportRequest(
                render_request=render_request,
                output_path=output_path,
                format=static_format,
            )
        )

    def write_data(output_path):
        nonlocal data_result
        source = _uniform_csv_source(render_request, data_format)
        data_result = _write_full_fidelity_tabular_export(source, output_path, data_format)
        if data_result is None:
            data_result = _write_full_fidelity_array_export(source, output_path, data_format)
        if data_result is not None:
            return
        data_result = data_backend.export_data(
            PlotDataExportRequest(
                render_request=render_request,
                output_path=output_path,
                format=data_format,
            )
        )

    store = artifact_store_for_context(ctx)
    touched_relative_paths: list[str] = []
    registered_ids: list[str] = []
    try:
        static_target = allocate_managed_output(
            ctx,
            output_key="static_export",
            default_suffix=f".{static_format}",
            managed_subdirectory="plots",
        )
        touched_relative_paths.append(static_target.relative_path)
        write_static(static_target.path)
        registered_ids.append(static_target.artifact_id)
        static_ref = register_staged_path_artifact(
            ctx,
            store=store,
            artifact_id=static_target.artifact_id,
            payload_path=static_target.path,
            relative_path=static_target.relative_path,
            slot=static_target.slot,
            format=static_target.format,
            entry_metadata=static_target.entry_metadata,
        )

        data_target = allocate_managed_output(
            ctx,
            output_key="data_export",
            default_suffix=f".{data_format}",
            managed_subdirectory="plots",
        )
        touched_relative_paths.append(data_target.relative_path)
        write_data(data_target.path)
        registered_ids.append(data_target.artifact_id)
        data_ref = register_staged_path_artifact(
            ctx,
            store=store,
            artifact_id=data_target.artifact_id,
            payload_path=data_target.path,
            relative_path=data_target.relative_path,
            slot=data_target.slot,
            format=data_target.format,
            entry_metadata=data_target.entry_metadata,
        )
        persist_artifact_store(ctx, store)
    except BaseException:
        try:
            store.discard_staged_entries(registered_ids)
        except BaseException:
            pass
        try:
            store.discard_staged_paths(touched_relative_paths)
        except BaseException:
            pass
        try:
            persist_artifact_store(ctx, store)
        except BaseException:
            pass
        raise
    return {
        "static_export": static_ref,
        "data_export": data_ref,
        "exports": {
            "static_export": static_ref,
            "data_export": data_ref,
            "static_metadata": _runtime_artifact_metadata(static_result),
            "data_metadata": _runtime_artifact_metadata(data_result),
        },
    }


def _uniform_csv_source(
    render_request: PlotRenderRequest,
    data_format: str,
) -> Mapping[str, Any] | None:
    """Return one shared source only when a full-fidelity CSV export is possible."""
    if data_format != "csv":
        return None
    series = render_request.series
    if not series:
        return None
    sources = [item.get("source_ref") for item in series]
    if any(not isinstance(source, Mapping) for source in sources):
        return None
    first = sources[0]
    if any(source != first for source in sources[1:]):
        return None
    return first


def _write_full_fidelity_tabular_export(
    first: Mapping[str, Any] | None,
    output_path: Any,
    data_format: str,
) -> "PlotExportResult | None":
    """Stream the full source table for the data export.

    Plot surfaces consume decimated series; the data export must reproduce
    every source row. When all series originate from one tabular ref, the
    export streams that ref through the shared loader service instead of
    writing the decimated points.
    """

    if first is None:
        return None
    ref = coerce_tabular_data_ref(first.get("ref"))
    if ref is None:
        return None

    from ea_node_editor.addons.tabular_data.loader_cache_service import (
        shared_tabular_loader_cache_service,
    )
    from ea_node_editor.execution.plot_backend import PlotExportResult
    from ea_node_editor.runtime_contracts import TabularArrowBatchOptions

    try:
        import pyarrow
        import pyarrow.csv as pa_csv
    except ModuleNotFoundError:
        return None

    service = shared_tabular_loader_cache_service()
    service.ensure_table_ref(ref)
    schema = service.schema(ref)
    schema_columns = tuple(column.name for column in schema.columns)
    requested_columns = data_series.source_column_names(first.get("columns"))
    columns = tuple(name for name in requested_columns if name in schema_columns) or schema_columns
    if not columns:
        return None
    row_limit = first.get("row_limit")
    exported_rows = 0
    options = TabularArrowBatchOptions(
        row_limit=int(row_limit) if isinstance(row_limit, int) and row_limit > 0 else 2_147_483_647,
        batch_size=65_536,
        row_offset=int(first.get("row_offset") or 0),
        columns=columns,
    )
    writer = None
    try:
        for batch in service.arrow_batches(ref, options):
            if isinstance(batch, list):
                batch = pyarrow.Table.from_pylist(
                    [{name: row.get(name) for name in columns} for row in batch]
                )
            if writer is None:
                writer = pa_csv.CSVWriter(str(output_path), batch.schema)
            writer.write(batch)
            exported_rows += int(getattr(batch, "num_rows", 0) or 0)
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        return None
    return PlotExportResult(
        backend_id="tabular_full_fidelity",
        output_path=output_path,
        format=data_format,
        metadata={
            "row_count": exported_rows,
            "column_count": len(columns),
            "columns": list(columns),
            "source": "tabular_ref",
        },
    )


def _write_full_fidelity_array_export(
    first: Mapping[str, Any] | None,
    output_path: Any,
    data_format: str,
) -> "PlotExportResult | None":
    if first is None:
        return None

    kind = str(first.get("kind", "") or "")
    if kind == "array_ref":
        ref = coerce_array_data_ref(first.get("ref"))
        if ref is None:
            return None
        base = ref
        row_offset = column_offset = 0
        row_limit = ref.shape[0]
        column_count = ref.shape[1] if len(ref.shape) > 1 else 1
    elif kind == "array_slice_2d_ref":
        ref = coerce_array_slice_2d_ref(first.get("ref"))
        if ref is None:
            return None
        base = ref.array_data
        row_offset, column_offset = ref.row_offset, ref.column_offset
        row_limit = min(ref.row_limit or base.shape[0], max(0, base.shape[0] - row_offset))
        width = base.shape[1] if len(base.shape) > 1 else 1
        column_count = min(ref.column_limit or width, max(0, width - column_offset))
    else:
        return None

    from ea_node_editor.execution.plot_backend import PlotExportResult

    if column_count <= 0:
        return None
    from ea_node_editor.addons.tabular_data.loader_cache_service import shared_tabular_loader_cache_service
    from ea_node_editor.addons.tabular_data.exporting import atomic_tabular_output
    from ea_node_editor.addons.tabular_data.operations import check_cancelled

    service = shared_tabular_loader_cache_service()
    columns = [f"column_{index + 1}" for index in range(column_count)]
    exported_rows = 0
    with atomic_tabular_output(output_path) as temporary, temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        for offset in range(row_offset, row_offset + row_limit, 4096):
            check_cancelled()
            window = service.slice_2d(base, ArraySlice2DRequest(row_offset=offset, row_limit=min(4096, row_offset + row_limit - offset),
                                                              column_offset=column_offset, column_limit=column_count))
            writer.writerows(window.values)
            exported_rows += len(window.values)
    return PlotExportResult(
        backend_id="array_full_fidelity",
        output_path=output_path,
        format=data_format,
        metadata={
            "row_count": exported_rows,
            "column_count": column_count,
            "columns": columns,
            "source": kind,
        },
    )
