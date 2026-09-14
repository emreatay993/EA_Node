# Purpose: Render an explicitly chosen ND array plane without changing the authored output.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_session.py
from __future__ import annotations

from ea_node_editor.addons.tabular_data.input_node import tabular_load_options_from_node_properties
from ea_node_editor.addons.tabular_data.source_backends import SelectionRequiredError, json_safe_value
from ea_node_editor.runtime_contracts import ArrayDataRef
from ea_node_editor.runtime_contracts.data_view import projection_axes


def describe_raw_plane(provider, properties, request, axes):
    options = tabular_load_options_from_node_properties(properties)
    if options.data_view.mode == "table":
        return None
    resolution = provider._resolver().resolve(str(properties.get("path", "")))
    if resolution.absolute_path is None or not resolution.absolute_path.is_file():
        return None
    service = provider._service_factory()
    try:
        ref = service.open_source(resolution.absolute_path, options)
    except SelectionRequiredError:
        return None
    if not isinstance(ref, ArrayDataRef) or len(ref.shape) <= 2:
        return None
    payload = {"state": "array_axes_required", "message": "Choose row/column axes and fixed indices for the preview plane.",
               "preview_kind": "array", "array": {"shape": list(ref.shape), "dtype": ref.dtype, "object_id": ref.object_id},
               "ref": ref.to_payload(), "metadata": dict(service.metadata(ref))}
    try:
        row_axis, column_axis, fixed = projection_axes(axes, ref.shape)
    except ValueError:
        return payload
    import numpy as np

    row_offset = max(0, int(request.get("row_offset", 0)))
    column_offset = max(0, int(request.get("column_offset", 0)))
    row_limit = max(1, min(500, int(request.get("row_limit", 50))))
    column_limit = max(1, min(200, int(request.get("column_limit", 50))))
    selection = [slice(None)] * len(ref.shape)
    for axis, index in fixed.items():
        selection[axis] = index
    selection[row_axis] = slice(row_offset, row_offset + row_limit)
    if column_axis is not None:
        selection[column_axis] = slice(column_offset, column_offset + column_limit)
    array = service._open_array(service._array_record(ref))
    selected = np.array(array[tuple(selection)], copy=True)
    if column_axis is not None and row_axis > column_axis:
        selected = selected.T
    if selected.ndim == 1:
        selected = selected[:, None]
    payload.update(state="ready", message="Array preview plane is ready.", slice_2d={
        "shape": [ref.shape[row_axis], ref.shape[column_axis] if column_axis is not None else 1],
        "dtype": ref.dtype, "row_offset": row_offset, "column_offset": column_offset,
        "values": [[json_safe_value(value) for value in row] for row in selected.tolist()],
        "bounded": True, "request": dict(request),
    })
    return payload
