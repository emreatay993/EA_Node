# Purpose: Prepare generic Plot series from values, full sources, and explicit source views.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_generic_plot_preparation.py, tests/test_plot_series_decimation.py, tests/test_tabular_perf_guards.py
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ea_node_editor.nodes.builtins.plot import specs
from ea_node_editor.runtime_contracts import (
    ArrayDataRef,
    ArraySlice2DRef,
    TabularDataRef,
    TabularWindowRef,
    coerce_array_data_ref,
    coerce_array_slice_2d_ref,
    coerce_tabular_data_ref,
    coerce_tabular_window_ref,
)

if TYPE_CHECKING:
    from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService
    from ea_node_editor.runtime_contracts.tabular_data import TabularColumn


def _sequence_value(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def source_column_names(value: object) -> tuple[str, ...]:
    """Keep runtime column strings literal and deduplicate case-sensitively."""
    if value is None:
        return ()
    if isinstance(value, str):
        values: Sequence[object] = (value,)
    elif _sequence_value(value):
        values = value  # type: ignore[assignment]
    else:
        values = (value,)
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _positive_int_or_none(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


def _column_lookup(columns: Sequence[str]) -> dict[str, str]:
    return {column.casefold(): column for column in columns}


def _existing_columns(columns: Sequence[str], requested: Sequence[str]) -> tuple[str, ...]:
    lookup = _column_lookup(columns)
    selected: list[str] = []
    for item in requested:
        column = lookup.get(str(item).casefold())
        if column and column not in selected:
            selected.append(column)
    return tuple(selected)


def _mapping_column(mapping: Mapping[str, Any], key: str, available: Sequence[str]) -> str:
    selected = _existing_columns(available, source_column_names(mapping.get(key)))
    return selected[0] if selected else ""


def _mapping_columns(mapping: Mapping[str, Any], key: str, available: Sequence[str]) -> tuple[str, ...]:
    return _existing_columns(available, source_column_names(mapping.get(key)))


def _format_column_names(columns: Sequence[str], *, limit: int = 8) -> str:
    normalized = tuple(str(column) for column in columns if str(column))
    if not normalized:
        return "none"
    visible = ", ".join(repr(column) for column in normalized[:limit])
    remaining = len(normalized) - limit
    if remaining > 0:
        return f"{visible}, and {remaining} more"
    return visible


def _plot_type_label(plot_type: str) -> str:
    return str(plot_type or "plot").replace("_", " ")


def _missing_columns(available: Sequence[str], requested: Sequence[str]) -> tuple[str, ...]:
    lookup = _column_lookup(available)
    return tuple(column for column in requested if column.casefold() not in lookup)


def _tabular_column_details(available: Sequence[str], all_columns: Sequence[str]) -> str:
    details = f"Loaded columns: {_format_column_names(all_columns)}."
    if tuple(available) != tuple(all_columns):
        details += f" Columns available to this plot: {_format_column_names(available)}."
    return details


def _validate_tabular_columns(
    *,
    plot_type: str,
    source: str,
    requested: Sequence[str],
    available: Sequence[str],
    all_columns: Sequence[str],
) -> None:
    missing = _missing_columns(available, requested)
    if not missing:
        return
    noun = "columns" if len(missing) != 1 else "column"
    raise ValueError(
        f"Tabular {_plot_type_label(plot_type)} plot cannot use {source} {noun} "
        f"{_format_column_names(missing)}. "
        f"{_tabular_column_details(available, all_columns)} {specs.TABULAR_PLOT_DIAGNOSTIC_HINT}"
    )


def _validate_tabular_mapping_keys(
    *,
    plot_type: str,
    mapping: Mapping[str, Any],
    available: Sequence[str],
    all_columns: Sequence[str],
) -> None:
    for key in specs.PLOT_TABULAR_VALIDATION_KEYS[plot_type]:
        _validate_tabular_columns(
            plot_type=plot_type,
            source=f"tabular_mapping.{key}",
            requested=source_column_names(mapping.get(key)),
            available=available,
            all_columns=all_columns,
        )


def _raise_empty_tabular_plot(
    *,
    plot_type: str,
    available: Sequence[str],
    all_columns: Sequence[str],
) -> None:
    raise ValueError(
        f"Tabular {_plot_type_label(plot_type)} plot input has no data rows after parsing. "
        f"{_tabular_column_details(available, all_columns)} "
        "Check Header Row, Skip Rows, and any tabular_mapping row_limit."
    )


def _raise_no_numeric_tabular_columns(
    *,
    plot_type: str,
    available: Sequence[str],
    all_columns: Sequence[str],
) -> None:
    raise ValueError(
        f"Tabular {_plot_type_label(plot_type)} plot needs numeric columns, but none of the "
        "columns available to this plot contain numeric values. "
        f"{_tabular_column_details(available, all_columns)} {specs.TABULAR_PLOT_DIAGNOSTIC_HINT}"
    )


def _raise_empty_tabular_series(
    *,
    plot_type: str,
    columns: Sequence[str],
    available: Sequence[str],
    all_columns: Sequence[str],
) -> None:
    raise ValueError(
        f"Tabular {_plot_type_label(plot_type)} plot produced no numeric points from "
        f"{_format_column_names(columns)}. "
        f"{_tabular_column_details(available, all_columns)} {specs.TABULAR_PLOT_DIAGNOSTIC_HINT}"
    )




def _numeric_value(value: object) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        numeric = float(text)
    except ValueError:
        return None
    if numeric.is_integer():
        return int(numeric)
    return numeric


def _json_safe_plot_cell(value: Any) -> Any:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _column_dtype_is_numeric(dtype: str) -> bool:
    normalized = str(dtype or "").casefold()
    if not normalized or "bool" in normalized:
        return False
    return any(token in normalized for token in ("int", "float", "double", "decimal", "number"))


def _semantic_x_column(
    columns: Sequence[Any],
    numeric_columns: Sequence[str],
    available: Sequence[str],
) -> str:
    numeric = set(numeric_columns)
    by_name = {str(getattr(column, "name", "") or ""): column for column in columns}
    for name in available:
        column = by_name.get(name)
        dtype = str(getattr(column, "dtype", "") or "").casefold() if column is not None else ""
        lowered = name.casefold()
        if name not in numeric and (
            "date" in dtype
            or "time" in dtype
            or "date" in lowered
            or "time" in lowered
            or "index" in lowered
        ):
            return name
    for name in available:
        if name not in numeric:
            return name
    return ""


def _series_label(column: str, fallback: str = "") -> str:
    return str(column or fallback or "series").strip()


def _import_numpy() -> Any:
    import numpy

    return numpy


def _float_array_or_none(np: Any, values: Any) -> Any | None:
    """Coerce one column to float64 (NaN for empty cells) or None when the
    column holds non-numeric values — mirrors ``_column_values_are_numeric``."""

    kind = getattr(getattr(values, "dtype", None), "kind", "O")
    if kind in "iuf":
        return values.astype(np.float64, copy=False)
    if kind == "b":
        return None
    converted = np.empty(len(values), dtype=np.float64)
    for index, value in enumerate(values):
        numeric = _numeric_value(value)
        if numeric is None:
            if value is None or str(value).strip() == "":
                converted[index] = math.nan
                continue
            return None
        converted[index] = float(numeric)
    return converted


def _numeric_arrays_from_columns(
    np: Any,
    schema_columns: Sequence[Any],
    columns_data: Mapping[str, Any],
    available: Sequence[str],
) -> tuple[tuple[str, ...], dict[str, Any]]:
    by_name = {str(getattr(column, "name", "") or ""): column for column in schema_columns}
    numeric: dict[str, Any] = {}
    names: list[str] = []
    for name in available:
        values = columns_data.get(name)
        if values is None:
            continue
        column = by_name.get(name)
        dtype = str(getattr(column, "dtype", "") or "") if column is not None else ""
        coerced = _float_array_or_none(np, values)
        if coerced is None:
            continue
        if _column_dtype_is_numeric(dtype) or bool(np.isfinite(coerced).any()):
            numeric[name] = coerced
            names.append(name)
    return tuple(names), numeric


def _decimation_meta(method: str, original_rows: int, points: int) -> dict[str, Any]:
    return {"method": method, "original_rows": int(original_rows), "points": int(points)}


def _xy_series_from_arrays(
    np: Any,
    *,
    columns_data: Mapping[str, Any],
    numeric_arrays: Mapping[str, Any],
    x_column: str,
    y_column: str,
    max_points: int,
    label: str = "",
) -> dict[str, Any]:
    from ea_node_editor.execution.plot_series_decimation import (
        DECIMATION_METHOD_NONE,
        DECIMATION_METHOD_STRIDE,
        decimate_xy,
        stride_sample_indices,
    )

    y_values = numeric_arrays[y_column]
    total_rows = int(len(y_values))
    series: dict[str, Any] = {"label": _series_label(label or y_column)}
    if x_column and x_column not in numeric_arrays:
        # Label axis: positions stay sequential after dropping empty y cells;
        # the label subset follows the sampled rows.
        labels = columns_data[x_column]
        finite = np.isfinite(y_values)
        kept_y = y_values[finite]
        kept_labels = (
            labels[finite]
            if hasattr(labels, "__getitem__") and hasattr(labels, "dtype")
            else np.asarray(list(labels), dtype=object)[finite]
        )
        if len(kept_y) > max_points:
            indices = stride_sample_indices(len(kept_y), max_points)
            kept_y = kept_y[indices]
            kept_labels = kept_labels[indices]
            method = DECIMATION_METHOD_STRIDE
        else:
            method = DECIMATION_METHOD_NONE
        series.update(
            {
                "x": list(range(len(kept_y))),
                "y": kept_y.tolist(),
                "x_labels": ["" if value is None else str(value) for value in kept_labels.tolist()],
                "decimation": _decimation_meta(method, total_rows, len(kept_y)),
            }
        )
    else:
        x_values = (
            numeric_arrays[x_column]
            if x_column
            else np.arange(total_rows, dtype=np.float64)
        )
        out_x, out_y, meta = decimate_xy(x_values, y_values, max_points)
        series.update({"x": out_x, "y": out_y, "decimation": meta})
    if x_column:
        series["x_column"] = x_column
    series["y_column"] = y_column
    return series


def _values_series_from_arrays(
    np: Any,
    column: str,
    numeric_arrays: Mapping[str, Any],
    max_points: int,
) -> dict[str, Any]:
    from ea_node_editor.execution.plot_series_decimation import (
        DECIMATION_METHOD_NONE,
        DECIMATION_METHOD_STRIDE,
        stride_sample_indices,
    )

    values = numeric_arrays.get(column)
    if values is None:
        return {
            "label": _series_label(column),
            "values": [],
            "value_column": column,
            "decimation": _decimation_meta(DECIMATION_METHOD_NONE, 0, 0),
        }
    total_rows = int(len(values))
    finite = values[np.isfinite(values)]
    if len(finite) > max_points:
        finite = finite[stride_sample_indices(len(finite), max_points)]
        method = DECIMATION_METHOD_STRIDE
    else:
        method = DECIMATION_METHOD_NONE
    return {
        "label": _series_label(column),
        "values": finite.tolist(),
        "value_column": column,
        "decimation": _decimation_meta(method, total_rows, len(finite)),
    }


def _grid_from_arrays(
    np: Any,
    columns: Sequence[str],
    numeric_arrays: Mapping[str, Any],
    total_rows: int,
    max_points: int,
) -> tuple[list[list[float]], dict[str, Any]]:
    from ea_node_editor.execution.plot_series_decimation import (
        DECIMATION_METHOD_NONE,
        DECIMATION_METHOD_STRIDE,
        stride_sample_indices,
    )

    stacked = np.column_stack(
        [
            np.nan_to_num(
                numeric_arrays.get(column, np.zeros(total_rows, dtype=np.float64)),
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )
            for column in columns
        ]
    )
    if stacked.shape[0] > max_points:
        stacked = stacked[stride_sample_indices(stacked.shape[0], max_points)]
        method = DECIMATION_METHOD_STRIDE
    else:
        method = DECIMATION_METHOD_NONE
    return stacked.tolist(), _decimation_meta(method, total_rows, stacked.shape[0])


def _points_from_arrays(
    np: Any,
    columns: Sequence[str],
    numeric_arrays: Mapping[str, Any],
    max_points: int,
) -> tuple[list[list[float]], dict[str, Any]] | None:
    from ea_node_editor.execution.plot_series_decimation import (
        DECIMATION_METHOD_NONE,
        DECIMATION_METHOD_STRIDE,
        stride_sample_indices,
    )

    arrays = [numeric_arrays.get(column) for column in columns[:3]]
    if any(array is None for array in arrays):
        return None
    stacked = np.column_stack(arrays)
    mask = np.isfinite(stacked).all(axis=1)
    total_rows = int(stacked.shape[0])
    stacked = stacked[mask]
    if stacked.shape[0] == 0:
        return None
    if stacked.shape[0] > max_points:
        stacked = stacked[stride_sample_indices(stacked.shape[0], max_points)]
        method = DECIMATION_METHOD_STRIDE
    else:
        method = DECIMATION_METHOD_NONE
    return stacked.tolist(), _decimation_meta(method, total_rows, stacked.shape[0])


def _named_or_numeric_columns(
    available: Sequence[str],
    numeric_columns: Sequence[str],
    names: Sequence[str],
) -> tuple[str, ...]:
    lookup = _column_lookup(available)
    matched: list[str] = []
    for name in names:
        column = lookup.get(name.casefold())
        if column and column not in matched:
            matched.append(column)
    if len(matched) == len(names):
        return tuple(matched)
    return tuple(numeric_columns[: len(names)])


@dataclass(frozen=True, slots=True)
class _TablePlotSelection:
    table_ref: TabularDataRef
    schema_columns: tuple[TabularColumn, ...]
    all_columns: tuple[str, ...]
    available: tuple[str, ...]
    row_offset: int
    row_limit: int | None
    export_columns: tuple[str, ...] | None


def _resolve_table_plot_selection(
    service: TabularLoaderCacheService,
    ref: TabularDataRef | TabularWindowRef,
    *,
    plot_type: str,
    mapping: Mapping[str, Any],
) -> _TablePlotSelection:
    window = isinstance(ref, TabularWindowRef)
    table_ref = ref.table_data if window else ref
    service.ensure_table_ref(table_ref)
    schema = service.schema(table_ref)
    all_columns = tuple(column.name for column in schema.columns)
    if window:
        from ea_node_editor.addons.tabular_data.extraction_nodes import _table_window_request_from_ref

        request = _table_window_request_from_ref(ref)
        source_columns = service.window_columns(table_ref, request)
        row_offset = request.row_offset
        window_limit = request.row_limit if request.row_limit > 0 else None
    else:
        source_columns = all_columns
        row_offset = 0
        window_limit = None

    requested_columns = source_column_names(mapping.get("columns"))
    _validate_tabular_columns(
        plot_type=plot_type,
        source="tabular_mapping.columns",
        requested=requested_columns,
        available=source_columns,
        all_columns=all_columns,
    )
    available = _existing_columns(source_columns, requested_columns) or tuple(source_columns)
    if not available:
        raise ValueError(
            f"Tabular {_plot_type_label(plot_type)} plot input has no columns to plot. "
            f"{_tabular_column_details(available, all_columns)} {specs.TABULAR_PLOT_DIAGNOSTIC_HINT}"
        )
    mapping_limit = _positive_int_or_none(mapping.get("row_limit"))
    limits = [limit for limit in (mapping_limit, window_limit) if limit is not None]
    row_limit = min(limits) if limits else None
    return _TablePlotSelection(
        table_ref=table_ref,
        schema_columns=schema.columns,
        all_columns=all_columns,
        available=available,
        row_offset=row_offset,
        row_limit=row_limit,
        # Direct tables export the full source; windows retain their authored domain.
        export_columns=tuple(source_columns) if window else None,
    )


def _series_from_table_input(
    ref: TabularDataRef | TabularWindowRef,
    *,
    plot_type: str,
    mapping: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    from ea_node_editor.addons.tabular_data.loader_cache_service import shared_tabular_loader_cache_service

    service = shared_tabular_loader_cache_service()
    selection = _resolve_table_plot_selection(service, ref, plot_type=plot_type, mapping=mapping)
    columns_data = service.column_arrays(
        selection.table_ref,
        columns=selection.available,
        row_offset=selection.row_offset,
        row_limit=selection.row_limit,
    )
    series, warnings = _series_from_tabular_columns(
        columns_data=columns_data,
        schema_columns=selection.schema_columns,
        available=selection.available,
        all_columns=selection.all_columns,
        plot_type=plot_type,
        mapping=mapping,
        warnings=(),
    )
    source_ref = {
        "ref": selection.table_ref.to_payload(),
        "row_offset": selection.row_offset,
        "row_limit": selection.row_limit,
    }
    if selection.export_columns is not None:
        source_ref["columns"] = list(selection.export_columns)
    for item in series:
        item.setdefault("source_ref", source_ref)
    return series, warnings


def _series_from_tabular_columns(
    *,
    columns_data: Mapping[str, Any],
    schema_columns: Sequence[Any],
    available: Sequence[str],
    all_columns: Sequence[str],
    plot_type: str,
    mapping: Mapping[str, Any],
    warnings: tuple[str, ...],
    max_points: int = specs.TABULAR_PLOT_MAX_POINTS_PER_SERIES,
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    np = _import_numpy()
    numeric_columns, numeric_arrays = _numeric_arrays_from_columns(
        np, schema_columns, columns_data, available
    )
    total_rows = max((len(values) for values in columns_data.values()), default=0)
    if total_rows == 0:
        _raise_empty_tabular_plot(plot_type=plot_type, available=available, all_columns=all_columns)

    x_column = _mapping_column(mapping, "x", available)
    category_column = _mapping_column(mapping, "category", available)
    y_columns = _mapping_columns(mapping, "y", available)
    value_columns = _mapping_columns(mapping, "values", available)
    z_column = _mapping_column(mapping, "z", available)

    if plot_type == specs.PLOT_TYPE_BAR:
        _validate_tabular_mapping_keys(
            plot_type=plot_type,
            mapping=mapping,
            available=available,
            all_columns=all_columns,
        )
        if not x_column:
            x_column = category_column or _semantic_x_column(schema_columns, numeric_columns, available)
        if not y_columns:
            y_columns = tuple(column for column in numeric_columns if column != x_column)
        if not y_columns and numeric_columns:
            y_columns = (numeric_columns[0],)
            if x_column == y_columns[0]:
                x_column = ""
        if not y_columns:
            _raise_no_numeric_tabular_columns(
                plot_type=plot_type,
                available=available,
                all_columns=all_columns,
            )
        series = tuple(
            _xy_series_from_arrays(
                np,
                columns_data=columns_data,
                numeric_arrays=numeric_arrays,
                x_column=x_column,
                y_column=column,
                max_points=max_points,
            )
            for column in y_columns
        )
        if not any(item.get("y") for item in series):
            _raise_empty_tabular_series(
                plot_type=plot_type,
                columns=y_columns,
                available=available,
                all_columns=all_columns,
            )
        return series, warnings

    if plot_type == specs.PLOT_TYPE_HISTOGRAM:
        _validate_tabular_mapping_keys(
            plot_type=plot_type,
            mapping=mapping,
            available=available,
            all_columns=all_columns,
        )
        columns = value_columns or numeric_columns
        if not columns:
            _raise_no_numeric_tabular_columns(
                plot_type=plot_type,
                available=available,
                all_columns=all_columns,
            )
        series = tuple(
            _values_series_from_arrays(np, column, numeric_arrays, max_points)
            for column in columns
        )
        if not any(item.get("values") for item in series):
            _raise_empty_tabular_series(
                plot_type=plot_type,
                columns=columns,
                available=available,
                all_columns=all_columns,
            )
        return series, warnings

    if plot_type in {specs.PLOT_TYPE_HEATMAP, specs.PLOT_TYPE_CONTOUR, specs.PLOT_TYPE_SURFACE}:
        _validate_tabular_mapping_keys(
            plot_type=plot_type,
            mapping=mapping,
            available=available,
            all_columns=all_columns,
        )
        columns = value_columns or tuple(column for column in numeric_columns if column != z_column)
        if z_column and z_column not in columns:
            columns = (z_column,)
        if not columns:
            _raise_no_numeric_tabular_columns(
                plot_type=plot_type,
                available=available,
                all_columns=all_columns,
            )
        if not any(column in numeric_columns for column in columns):
            _raise_empty_tabular_series(
                plot_type=plot_type,
                columns=columns,
                available=available,
                all_columns=all_columns,
            )
        grid, decimation = _grid_from_arrays(np, columns, numeric_arrays, total_rows, max_points)
        return (
            {
                "label": "tabular grid",
                "values": grid,
                "columns": list(columns),
                "decimation": decimation,
            },
        ), warnings

    if plot_type == specs.PLOT_TYPE_POINT_CLOUD:
        _validate_tabular_mapping_keys(
            plot_type=plot_type,
            mapping=mapping,
            available=available,
            all_columns=all_columns,
        )
        xyz = (
            _mapping_column(mapping, "x", available),
            _mapping_column(mapping, "y", available),
            _mapping_column(mapping, "z", available),
        )
        columns = tuple(column for column in xyz if column) or _named_or_numeric_columns(
            available,
            numeric_columns,
            ("x", "y", "z"),
        )
        if len(columns) < 3:
            raise ValueError(
                "Point cloud auto tabular plotting requires x, y, and z columns. "
                f"{_tabular_column_details(available, all_columns)} {specs.TABULAR_PLOT_DIAGNOSTIC_HINT}"
            )
        sampled = _points_from_arrays(np, columns, numeric_arrays, max_points)
        if sampled is None:
            _raise_empty_tabular_series(
                plot_type=plot_type,
                columns=columns[:3],
                available=available,
                all_columns=all_columns,
            )
        points, decimation = sampled
        return (
            {
                "label": "tabular point cloud",
                "points": points,
                "columns": list(columns[:3]),
                "decimation": decimation,
            },
        ), warnings

    if plot_type == specs.PLOT_TYPE_STREAMLINES:
        _validate_tabular_mapping_keys(
            plot_type=plot_type,
            mapping=mapping,
            available=available,
            all_columns=all_columns,
        )
        columns = _named_or_numeric_columns(available, numeric_columns, ("x", "y", "z"))
        if len(columns) < 3:
            raise ValueError(
                "Streamline auto tabular plotting requires named or mapped x, y, and z columns. "
                f"{_tabular_column_details(available, all_columns)} {specs.TABULAR_PLOT_DIAGNOSTIC_HINT}"
            )
        sampled = _points_from_arrays(np, columns, numeric_arrays, max_points)
        if sampled is None:
            _raise_empty_tabular_series(
                plot_type=plot_type,
                columns=columns[:3],
                available=available,
                all_columns=all_columns,
            )
        points, decimation = sampled
        return (
            {
                "label": "tabular streamlines",
                "points": points,
                "columns": list(columns[:3]),
                "decimation": decimation,
            },
        ), warnings

    from ea_node_editor.execution.plot_backend import normalize_generic_plot_series
    from ea_node_editor.execution.plot_series_decimation import stride_sample_indices

    # Unknown plot types fall back to bounded row mappings.
    indices = stride_sample_indices(total_rows, max_points)
    bounded_rows = [
        {name: _json_safe_plot_cell(columns_data[name][int(index)]) for name in available}
        for index in indices
    ]
    return normalize_generic_plot_series(bounded_rows), warnings




def _array_rows_from_slice_ref(ref: ArraySlice2DRef) -> tuple[tuple[Any, ...], ...]:
    from ea_node_editor.addons.tabular_data.extraction_nodes import load_array_slice_2d

    array_slice = load_array_slice_2d(ref)
    return tuple(tuple(row) for row in array_slice.values)


def _series_from_array_rows(rows: Sequence[Sequence[Any]], *, plot_type: str) -> tuple[dict[str, Any], ...]:
    if not rows:
        return ()
    from ea_node_editor.execution.plot_series_decimation import stride_sample_rows

    rows, decimation = stride_sample_rows(rows, specs.TABULAR_PLOT_MAX_POINTS_PER_SERIES)
    width = max((len(row) for row in rows), default=0)
    if plot_type in {specs.PLOT_TYPE_HEATMAP, specs.PLOT_TYPE_CONTOUR, specs.PLOT_TYPE_SURFACE}:
        return ({"label": "array grid", "values": [list(row) for row in rows], "decimation": decimation},)
    if plot_type == specs.PLOT_TYPE_HISTOGRAM:
        return ({"label": "array values", "values": [value for row in rows for value in row], "decimation": decimation},)
    if plot_type == specs.PLOT_TYPE_POINT_CLOUD and width >= 3:
        return ({"label": "array point cloud", "points": [list(row[:3]) for row in rows], "decimation": decimation},)
    if plot_type == specs.PLOT_TYPE_STREAMLINES and width >= 3:
        return ({"label": "array streamlines", "points": [list(row[:3]) for row in rows], "decimation": decimation},)
    series: list[dict[str, Any]] = []
    for column in range(width):
        values = [row[column] for row in rows if column < len(row)]
        series.append({"label": f"column_{column + 1}", "values": values, "decimation": decimation})
    return tuple(series)


def _series_with_source_ref(
    series: tuple[dict[str, Any], ...],
    source_ref: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    return tuple({**item, "source_ref": dict(source_ref)} for item in series)


def _series_from_array_ref(ref: ArrayDataRef, *, plot_type: str) -> tuple[dict[str, Any], ...]:
    import numpy as np
    from ea_node_editor.addons.tabular_data.loader_cache_service import shared_tabular_loader_cache_service
    from ea_node_editor.addons.tabular_data.source_backends import json_safe_value
    from ea_node_editor.execution.plot_series_decimation import stride_sample_indices

    if len(ref.shape) not in {1, 2}:
        raise ValueError("Build a table with explicit axes before plotting an ND array")
    count, width = ref.shape[0], ref.shape[1] if len(ref.shape) == 2 else 1
    if not count or not width:
        return ()
    grid = plot_type in {specs.PLOT_TYPE_HEATMAP, specs.PLOT_TYPE_CONTOUR, specs.PLOT_TYPE_SURFACE}
    row_budget = max(1, int(specs.TABULAR_PLOT_MAX_POINTS_PER_SERIES ** 0.5)) if grid else specs.TABULAR_PLOT_MAX_POINTS_PER_SERIES
    row_indexes = stride_sample_indices(count, row_budget)
    if grid:
        column_indexes = stride_sample_indices(width, row_budget)
    else:
        used_width = min(width, 3 if plot_type in {specs.PLOT_TYPE_POINT_CLOUD, specs.PLOT_TYPE_STREAMLINES} else width)
        column_indexes = np.arange(used_width)
    values = shared_tabular_loader_cache_service().sample_array(ref, row_indexes, column_indexes)
    rows = tuple(tuple(json_safe_value(value) for value in row) for row in values.tolist())
    series = _series_from_array_rows(rows, plot_type=plot_type)
    for item in series:
        item["decimation"] = {"method": "stride" if len(row_indexes) < count or len(column_indexes) < width else "none",
                              "original_rows": count, "points": len(row_indexes)}
    source_ref = {"kind": "array_ref", "ref": ref.to_payload(), "row_offset": 0, "column_offset": 0,
                  "row_limit": count, "column_limit": width}
    return _series_with_source_ref(series, source_ref)


def _series_from_array_slice_ref(ref: ArraySlice2DRef, *, plot_type: str) -> tuple[dict[str, Any], ...]:
    source_ref = {"kind": "array_slice_2d_ref", "ref": ref.to_payload()}
    return _series_with_source_ref(
        _series_from_array_rows(_array_rows_from_slice_ref(ref), plot_type=plot_type),
        source_ref,
    )


def _coerces_to_tabular_or_array_ref(value: object) -> bool:
    return (
        coerce_tabular_data_ref(value) is not None
        or coerce_array_data_ref(value) is not None
        or coerce_tabular_window_ref(value) is not None
        or coerce_array_slice_2d_ref(value) is not None
    )


def prepare_plot_series(
    value: object,
    *,
    plot_type: str,
    mapping: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    """Prepare values using the caller's read-only, runtime-coerced mapping."""
    table_ref = coerce_tabular_data_ref(value)
    if table_ref is not None:
        return _series_from_table_input(table_ref, plot_type=plot_type, mapping=mapping)
    array_ref = coerce_array_data_ref(value)
    if array_ref is not None:
        return _series_from_array_ref(array_ref, plot_type=plot_type), ()
    window_ref = coerce_tabular_window_ref(value)
    if window_ref is not None:
        return _series_from_table_input(window_ref, plot_type=plot_type, mapping=mapping)
    array_slice_ref = coerce_array_slice_2d_ref(value)
    if array_slice_ref is not None:
        return _series_from_array_slice_ref(array_slice_ref, plot_type=plot_type), ()
    if _sequence_value(value) and any(_coerces_to_tabular_or_array_ref(item) for item in value):  # type: ignore[union-attr]
        series: list[dict[str, Any]] = []
        warnings: list[str] = []
        for item in value:  # type: ignore[union-attr]
            item_series, item_warnings = prepare_plot_series(
                item,
                plot_type=plot_type,
                mapping=mapping,
            )
            series.extend(item_series)
            warnings.extend(item_warnings)
        return tuple(series), tuple(dict.fromkeys(warnings))
    from ea_node_editor.execution.plot_backend import normalize_generic_plot_series

    return normalize_generic_plot_series(value), ()
