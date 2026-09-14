# Purpose: Prove saved queries apply completely and identically to every table consumer.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_saved_queries.py
import sys

import numpy as np

from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService, TabularLoadOptions
from ea_node_editor.runtime_contracts import TabularWindowRequest, TabularArrowBatchOptions
from ea_node_editor.runtime_contracts.data_view import DataViewDefinition


def test_saved_filter_sort_then_range_and_columns_are_shared_by_all_reads(tmp_path):
    source = tmp_path / "source.npz"
    np.savez(source, time=np.arange(8), temperature=np.array([25., 50., 45., 50., np.nan, 39., 60., 48.]))
    view = DataViewDefinition({"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "time"}, {"member": "temperature"}]}],
                              "query": {"filters": [{"column": "temperature", "op": "gt", "value": "40"}],
                                        "sort": [{"column": "temperature", "descending": True}]},
                              "output": {"row_offset": 1, "row_limit": 3, "columns": ["time", "temperature"]}})
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(data_view=view))
    expected = ({"time": 1, "temperature": 50.}, {"time": 3, "temperature": 50.}, {"time": 7, "temperature": 48.})
    assert service.window(ref, TabularWindowRequest(row_limit=0, column_limit=0)).rows == expected
    assert tuple(service.iter_window_rows(ref, TabularWindowRequest(row_limit=0, column_limit=0))) == expected
    assert service.column_arrays(ref, columns=["time"])["time"].tolist() == [1, 3, 7]
    assert service.schema(ref).row_count == 3
    batches = list(service.arrow_batches(ref, TabularArrowBatchOptions(row_limit=20, batch_size=2)))
    assert [batch.num_rows for batch in batches] == [2, 1]
    assert "duckdb" not in sys.modules
    fresh = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    assert fresh.window(ref, TabularWindowRequest(row_limit=0, column_limit=0)).rows == expected


def test_saved_query_has_no_preview_scan_cap_and_preserves_large_integer_comparison(tmp_path):
    source = tmp_path / "large.npz"
    data = np.arange(210_001, dtype=np.int64) + 2**60
    np.savez_compressed(source, number=data)
    view = DataViewDefinition({"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "number"}]}],
                              "query": {"filters": [{"column": "number", "op": "gt", "value": str(int(data[-3]))}]}})
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(data_view=view))
    assert service.column_arrays(ref, columns=["number"])["number"].tolist() == data[-2:].tolist()


def test_missing_any_and_empty_result(tmp_path):
    source = tmp_path / "source.npz"
    np.savez(source, values=np.array([1., np.nan, 3., np.inf]))
    definition = {"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "values"}]}],
                  "query": {"match": "any", "filters": [{"column": "values", "op": "is_missing"},
                                                          {"column": "values", "op": "eq", "value": "3"}],
                            "sort": [{"column": "values", "descending": True}]}}
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(data_view=DataViewDefinition(definition)))
    values = service.column_arrays(ref, columns=["values"])["values"]
    assert values[0] == 3 and len(values) == 3
    definition["query"] = {"filters": [{"column": "values", "op": "gt", "value": "100"}]}
    ref = service.open_source(source, TabularLoadOptions(data_view=DataViewDefinition(definition)))
    assert service.window(ref, TabularWindowRequest(row_limit=20, column_limit=20)).rows == ()
    assert service.schema(ref).row_count == 0


def test_datetime_and_text_conditions_keep_typed_literals(tmp_path):
    source = tmp_path / "source.npz"
    stamps = np.array(["2026-01-01T00:00:00.000000001", "2026-01-02T00:00:00.000000002"], dtype="datetime64[ns]")
    np.savez(source, dates=stamps, names=np.array(["alpha", "beta"]))
    view = DataViewDefinition({"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "dates"}, {"member": "names"}]}],
                              "query": {"filters": [{"column": "dates", "op": "gt", "value": "2026-01-01T12:00:00"},
                                                     {"column": "names", "op": "contains", "value": "BETA"}]}})
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(data_view=view))
    np.testing.assert_array_equal(service.column_arrays(ref, columns=["dates"])["dates"], stamps[1:])


def test_cancelled_query_does_not_publish_output(tmp_path):
    import threading
    import pytest
    from ea_node_editor.addons.tabular_data.saved_queries import ensure_saved_query

    source = tmp_path / "source.npz"
    np.savez(source, values=np.arange(10))
    view = DataViewDefinition({"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "values"}]}],
                              "query": {"sort": [{"column": "values"}]}})
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(data_view=view))
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(InterruptedError):
        ensure_saved_query(service, service._table_records[ref.ref_id], cancel_event=cancelled)
    assert not list((tmp_path / "cache" / "views").glob("*.parquet"))


def test_query_worker_ignores_foreign_python_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONHOME", str(tmp_path / "foreign-python"))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "foreign-stdlib"))
    source = tmp_path / "source.npz"
    np.savez(source, values=np.arange(4))
    definition = DataViewDefinition({"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "values"}]}],
                                     "query": {"sort": [{"column": "values", "descending": True}]}})
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(data_view=definition))
    assert service.column_arrays(ref, columns=["values"])["values"].tolist() == [3, 2, 1, 0]


def test_saved_query_does_not_read_unused_value_members(tmp_path, monkeypatch):
    source = tmp_path / "source.npz"
    np.savez(source, A=np.arange(10), B=np.arange(10))
    definition = DataViewDefinition({"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "A"}, {"member": "B"}]}],
                                     "query": {"filters": [{"column": "A", "op": "gt", "value": "4"}]}, "output": {"columns": ["A"]}})
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(data_view=definition))
    original = service._open_array
    def read(record):
        assert record.object_id != "B"
        return original(record)
    monkeypatch.setattr(service, "_open_array", read)
    assert service.column_arrays(ref, columns=["A"])["A"].tolist() == [5, 6, 7, 8, 9]


def test_timezone_nanoseconds_survive_query_and_preview(tmp_path):
    import pandas as pd
    from ea_node_editor.runtime_contracts import TabularWindowRequest

    source = tmp_path / "dates.parquet"
    dates = pd.to_datetime(["2026-01-01T07:00:00.000000001Z", "2026-01-01T07:00:00.000000002Z"], utc=True)
    pd.DataFrame({"time": dates, "value": [1, 2]}).to_parquet(source)
    definition = DataViewDefinition({"version": 1, "mode": "source", "query": {"filters": [
        {"column": "time", "op": "gt", "value": "2026-01-01T10:00:00.000000001+03:00"}]}})
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(data_view=definition))
    assert service.column_arrays(ref, columns=["value"])["value"].tolist() == [2]
    values = service.column_arrays(ref, columns=["time"])["time"]
    np.testing.assert_array_equal(values, dates[1:].to_numpy(dtype="datetime64[ns]"))
    window = service.window(ref, TabularWindowRequest(row_limit=1, column_limit=2))
    assert window.rows[0]["time"] == "2026-01-01T07:00:00.000000002+00:00"
