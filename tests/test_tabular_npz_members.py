# Purpose: Prove header-only archive discovery and atomic selected-member reuse.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_npz_members.py
import zipfile

import numpy as np
import pytest

from ea_node_editor.addons.tabular_data.npz_members import NpzMemberCache, catalogue_npz
from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService, TabularLoadOptions
from ea_node_editor.runtime_contracts import ArraySlice2DRequest


def test_scan_reads_headers_without_numpy_loading_arrays(tmp_path, monkeypatch):
    source = tmp_path / "archive.npz"
    np.savez_compressed(source, values=np.arange(12).reshape(4, 3), metadata=np.zeros(4_000_000, dtype=np.uint8))
    monkeypatch.setattr(np, "load", lambda *a, **kw: pytest.fail("Metadata discovery must not materialize arrays"))
    members = catalogue_npz(source)
    assert [(m["member"], m["shape"]) for m in members] == [("values", (4, 3)), ("metadata", (4_000_000,))]
    assert members[1]["nbytes"] == 4_000_000


def test_bad_or_object_member_does_not_hide_good_arrays(tmp_path):
    source = tmp_path / "archive.npz"
    np.savez(source, good=np.arange(3), unsafe=np.array([{"x": 1}], dtype=object))
    with zipfile.ZipFile(source, "a") as archive:
        archive.writestr("broken.npy", b"not numpy")
    members = catalogue_npz(source)
    assert [m["supported"] for m in members] == [True, False, False]
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = loader.open_source(source, TabularLoadOptions(selected_object="good"))
    assert loader.slice_2d(ref, ArraySlice2DRequest(row_limit=2, column_limit=1)).values == ((0,), (1,))
    with pytest.raises(RuntimeError, match="pickle"):
        loader.open_source(source, TabularLoadOptions(selected_object="unsafe"))


def test_selected_member_is_decompressed_once_and_reopened_readonly(tmp_path, monkeypatch):
    source = tmp_path / "archive.npz"
    np.savez_compressed(source, values=np.arange(12).reshape(4, 3))
    cache = NpzMemberCache(tmp_path / "cache", max_bytes=1_000_000)
    first = cache.open(source, "values")
    assert not first.flags.writeable
    monkeypatch.setattr(zipfile, "ZipFile", lambda *a, **kw: pytest.fail("Warm member reopened the archive"))
    second = cache.open(source, "values")
    np.testing.assert_array_equal(first, second)


def test_same_stat_content_binding_uses_distinct_cache_entries(tmp_path):
    source = tmp_path / "archive.npz"
    np.savez(source, values=np.arange(3))
    cache = NpzMemberCache(tmp_path / "cache", max_bytes=1_000_000)
    cache.open(source, "values", content_sha256="one")
    cache.open(source, "values", content_sha256="two")
    assert len(list((tmp_path / "cache").glob("*.npy"))) == 2


def test_cancelled_extraction_never_publishes_a_partial_member(tmp_path):
    source = tmp_path / "archive.npz"
    np.savez_compressed(source, values=np.zeros(2_000_000))
    cache = NpzMemberCache(tmp_path / "cache", max_bytes=30_000_000)
    calls = 0
    def check():
        nonlocal calls
        calls += 1
        if calls == 3:
            raise InterruptedError("cancelled")
    with pytest.raises(InterruptedError):
        cache.open(source, "values", check_cancelled=check)
    assert not list((tmp_path / "cache").iterdir())


def test_duplicate_member_names_fail_without_ambiguous_lookup(tmp_path):
    source = tmp_path / "archive.npz"
    np.savez(source, Values=np.arange(3), values=np.arange(3))
    assert len(catalogue_npz(source)) == 2
    with zipfile.ZipFile(source, "a") as archive, pytest.warns(UserWarning):
        archive.writestr("Values.npy", b"duplicate")
    with pytest.raises(ValueError, match="duplicate"):
        catalogue_npz(source)
