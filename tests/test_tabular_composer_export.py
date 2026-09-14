# Purpose: Prove explicit export scopes, atomic publication and full-dimensional NPY output.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_export.py
import csv
from pathlib import Path
import threading

import numpy as np
import pytest

from ea_node_editor.addons.tabular_data.extraction_nodes import write_table_rows_to_path
from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService
from ea_node_editor.addons.tabular_data.operations import tabular_operation
from ea_node_editor.ui.tabular_composer_export import export_composer_data
from ea_node_editor.ui.tabular_preview_provider import TabularPreviewProvider


def test_visible_selected_and_complete_exports_have_distinct_scopes(tmp_path):
    source = tmp_path / "data.npz"
    np.savez(source, A=np.arange(12), B=np.arange(12) + 100)
    properties = {"path": str(source), "data_view": {"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "A"}, {"member": "B"}]}],
                                                       "query": {"filters": [{"column": "A", "op": "ge", "value": "5"}]}}}
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    preview = TabularPreviewProvider(service_factory=lambda: loader).describe_preview(properties, {"row_limit": 3})
    for scope, selection, count, header in [("visible", {}, 3, ["A", "B"]), ("selection", {"columns": ["B"]}, 3, ["B"]),
                                           ("output", {}, 7, ["A", "B"])]:
        path = tmp_path / f"{scope}.csv"
        result = export_composer_data(properties=properties, project_context=(None, None), preview=preview,
                                      scope=scope, selection=selection, output_path=path, service=loader)
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.reader(stream))
        assert result["rows"] == count
        assert rows[0] == header and len(rows) == count + 1
    assert source.is_file()


def test_failed_or_cancelled_write_preserves_existing_destination(tmp_path):
    target = tmp_path / "result.csv"
    target.write_text("original", encoding="utf-8")
    def broken():
        yield {"A": 1}
        raise ValueError("source failed")
    with pytest.raises(ValueError, match="source failed"):
        write_table_rows_to_path(target, columns=["A"], rows=broken())
    assert target.read_text() == "original"
    event = threading.Event()
    def cancelled():
        yield {"A": 1}
        event.set()
        yield {"A": 2}
    with pytest.raises(InterruptedError), tabular_operation(event):
        write_table_rows_to_path(target, columns=["A"], rows=cancelled())
    assert target.read_text() == "original"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["result.csv"]


def test_nd_npy_export_preserves_dimensions_and_explicit_output_slice(tmp_path):
    source = tmp_path / "array.npy"
    data = np.arange(120).reshape(4, 5, 6)
    np.save(source, data)
    properties = {"path": str(source), "data_view": {"version": 1, "mode": "array", "array_slices": [[1, 2], [2, 2], [1, 4]]}}
    target = tmp_path / "result.npy"
    export_composer_data(properties=properties, project_context=(None, None), preview={}, scope="output", selection={}, output_path=target)
    np.testing.assert_array_equal(np.load(target, allow_pickle=False), data[1:3, 2:4, 1:5])
    np.testing.assert_array_equal(np.load(source, allow_pickle=False), data)
    with pytest.raises(ValueError, match="ND array"):
        export_composer_data(properties=properties, project_context=(None, None), preview={}, scope="output", selection={}, output_path=tmp_path / "bad.csv")


def test_export_refuses_to_overwrite_its_source(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("A\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="different from the source"):
        export_composer_data(properties={"path": str(source)}, project_context=(None, None), preview={}, scope="output", selection={}, output_path=source)
    assert source.read_text() == "A\n1\n"
