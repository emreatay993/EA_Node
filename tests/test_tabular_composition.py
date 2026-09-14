# Purpose: Compare lazy composed windows, batches, and reopened refs with independent arrays.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composition.py
import numpy as np
import pytest

from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService, TabularLoadOptions
from ea_node_editor.runtime_contracts import TabularWindowRequest, TabularArrowBatchOptions
from ea_node_editor.runtime_contracts.data_view import DataViewDefinition


def open_view(tmp_path, payload, **arrays):
    source = tmp_path / "source.npz"
    np.savez_compressed(source, **arrays)
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    options = TabularLoadOptions(data_view=DataViewDefinition({"version": 1, "mode": "table", **payload}))
    return service, service.open_source(source, options)


def test_labeled_table_and_full_output_are_independent_of_preview(tmp_path):
    expected = np.arange(24).reshape(8, 3)
    service, ref = open_view(tmp_path, {"segments": [{"blocks": [{"member": "values", "labels_member": "labels"}],
                           "coordinate": {"member": "time", "name": "Time", "unit": "s"}}]},
                           values=expected, labels=np.array(["A", "B", "C"]), time=np.arange(8))
    assert (ref.row_count, ref.column_count) == (8, 4)
    window = service.window(ref, TabularWindowRequest(row_offset=3, row_limit=2, column_limit=3))
    assert window.rows == ({"Time": 3, "A": 9, "B": 10}, {"Time": 4, "A": 12, "B": 13})
    np.testing.assert_array_equal(service.column_arrays(ref, columns=["B"])["B"], expected[:, 1])
    fresh = TabularLoaderCacheService(cache_dir=tmp_path / "fresh")
    np.testing.assert_array_equal(fresh.column_arrays(ref, columns=["B"])["B"], expected[:, 1])
    batches = list(service.arrow_batches(ref, TabularArrowBatchOptions(batch_size=3, row_limit=8)))
    assert [batch.num_rows for batch in batches] == [3, 3, 2]


def test_add_columns_requires_equal_rows_and_preserves_integer_precision(tmp_path):
    large = np.array([2**60, 2**60 + 1], dtype=np.int64)
    service, ref = open_view(tmp_path, {"segments": [{"blocks": [{"member": "large"}, {"member": "other"}]}]},
                             large=large, other=np.array([1.5, 2.5]))
    assert service.column_arrays(ref, columns=["large"])["large"].tolist() == large.tolist()
    with pytest.raises(ValueError, match="equal row counts"):
        open_view(tmp_path, {"segments": [{"blocks": [{"member": "large"}, {"member": "other"}]}]},
                  large=large, other=np.arange(3))


def test_append_matches_names_across_reordered_columns_and_promotes_losslessly(tmp_path):
    segments = [{"blocks": [{"member": "first", "labels_member": "labels1"}]},
                {"blocks": [{"member": "second", "labels_member": "labels2"}]}]
    service, ref = open_view(tmp_path, {"segments": segments}, first=np.array([[1, 2]], dtype=np.int16),
                             second=np.array([[4, 3]], dtype=np.int32), labels1=np.array(["A", "B"]), labels2=np.array(["B", "A"]))
    assert service.window(ref, TabularWindowRequest(row_limit=0, column_limit=0)).rows == ({"A": 1, "B": 2}, {"A": 3, "B": 4})
    assert service.schema(ref).columns[0].dtype == "int32"
    with pytest.raises(ValueError, match="lose integer precision"):
        open_view(tmp_path, {"segments": segments}, first=np.array([[2**60, 1]], dtype=np.int64),
                  second=np.array([[1., 2.]]), labels1=np.array(["A", "B"]), labels2=np.array(["B", "A"]))


def test_explicit_nd_axes_and_output_selection(tmp_path):
    data = np.arange(4 * 5 * 6).reshape(4, 5, 6)
    service, ref = open_view(tmp_path, {"segments": [{"blocks": [{"member": "cube", "axes": {"row": 2, "column": 0, "fixed": {"1": 3}}}]}],
                             "output": {"row_offset": 2, "row_limit": 3, "columns": [2, 0]}}, cube=data)
    assert (ref.row_count, ref.column_count) == (3, 2)
    values = service.column_arrays(ref, columns=["Column 3", "Column 1"])
    np.testing.assert_array_equal(values["Column 3"], data[2, 3, 2:5])
    np.testing.assert_array_equal(values["Column 1"], data[0, 3, 2:5])


def test_label_mismatch_and_duplicate_names_fail_explicitly(tmp_path):
    payload = {"segments": [{"blocks": [{"member": "values", "labels_member": "labels"}]}]}
    with pytest.raises(ValueError, match="3 column labels"):
        open_view(tmp_path, payload, values=np.zeros((4, 3)), labels=np.array(["A", "B"]))
    with pytest.raises(ValueError, match="unique"):
        open_view(tmp_path, payload, values=np.zeros((4, 3)), labels=np.array(["A", "B", "A"]))


def test_native_table_composition_uses_same_service(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("Time,A,B\n0,10,20\n1,11,21\n", encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    view = DataViewDefinition({"version": 1, "mode": "table", "segments": [{"blocks": [{"columns": ["B", "A"]}],
                               "coordinate": {"member": "table", "column": "Time", "name": "Time"}}]})
    ref = service.open_source(source, TabularLoadOptions(data_view=view))
    assert service.window(ref, TabularWindowRequest(row_limit=0, column_limit=0)).rows == ({"Time": 0, "B": 20, "A": 10}, {"Time": 1, "B": 21, "A": 11})
    assert list(service.iter_window_rows(ref, TabularWindowRequest(row_limit=0, column_limit=0))) == [{"Time": 0, "B": 20, "A": 10}, {"Time": 1, "B": 21, "A": 11}]
    assert service.preview_window(ref, {"columns": ["B"], "search": "21"}).rows == ({"B": 21},)


def test_raw_array_slice_survives_reopen(tmp_path):
    from ea_node_editor.runtime_contracts import ArrayMaterializationOptions

    source = tmp_path / "source.npy"
    values = np.arange(120).reshape(4, 5, 6)
    np.save(source, values)
    view = DataViewDefinition({"version": 1, "mode": "array", "array_slices": [[1, 2], [2, 0], [1, 4]]})
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(data_view=view))
    assert ref.shape == (2, 3, 4)
    fresh = TabularLoaderCacheService(cache_dir=tmp_path / "fresh")
    np.testing.assert_array_equal(fresh.to_numpy(ref, ArrayMaterializationOptions(max_elements=24)), values[1:3, 2:, 1:5].reshape(-1))


def test_retained_composition_rejects_same_stat_mutation_and_reopens_fresh(tmp_path):
    import os
    from ea_node_editor.execution import retained_resources as resources
    from ea_node_editor.runtime_contracts.retained_resources import RetainedResourceError

    source = tmp_path / "source.npz"
    np.savez(source, values=np.arange(6).reshape(3, 2))
    options = TabularLoadOptions(data_view=DataViewDefinition({"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "values"}]}]}))
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = loader.open_source(source, options)
    bindings = resources.collect_retained_source_bindings(ref)
    fresh = TabularLoaderCacheService(cache_dir=tmp_path / "fresh")
    with resources.retained_source_binding_scope(bindings):
        assert fresh.window(ref, TabularWindowRequest(row_limit=1, column_limit=1)).rows == ({"Column 1": 0},)
        stamp = source.stat()
        np.savez(source, values=np.arange(6, 12).reshape(3, 2))
        os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        assert source.stat().st_size == stamp.st_size
        with pytest.raises(RetainedResourceError):
            fresh.window(ref, TabularWindowRequest(row_limit=1, column_limit=1))


def test_new_content_binding_does_not_reuse_old_same_stat_row_counts(tmp_path):
    import os
    from ea_node_editor.execution import retained_resources as resources

    source = tmp_path / "changing.csv"
    source.write_bytes(b"A\n10\n20\n")
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    options = TabularLoadOptions(data_view=DataViewDefinition({"version": 1, "mode": "table", "segments": [{"blocks": [{}]}]}))
    ref = loader.open_source(source, options)
    assert loader.schema(ref).row_count == 2
    stamp = source.stat()
    source.write_bytes(b"A\n1\n2\n3\n")
    os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert source.stat().st_size == stamp.st_size
    current = loader.open_source(source, options)
    bindings = resources.collect_retained_source_bindings(current)
    with resources.retained_source_binding_scope(bindings):
        assert loader.schema(current).row_count == 3
        assert loader.column_arrays(current, columns=["A"])["A"].tolist() == [1, 2, 3]
