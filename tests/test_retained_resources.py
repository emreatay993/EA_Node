# Purpose: Prove accepted source bindings and strict read-time table/array integrity.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_retained_resources.py
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
from itertools import islice
import json
import os
from pathlib import Path
import threading

import pytest

from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoadOptions, TabularLoaderCacheService
from ea_node_editor.execution import retained_resources as resources
from ea_node_editor.runtime_contracts import (
    ArrayMaterializationOptions, ArraySlice2DRef, ArraySlice2DRequest, DataTree,
    TabularArrowBatchOptions, TabularWindowRef, TabularWindowRequest,
)
from ea_node_editor.runtime_contracts.retained_resources import RetainedResourceError, RetainedSourceBinding


def _table(tmp_path: Path, *, cache_policy="source_direct"):
    source = tmp_path / "table.csv"
    source.write_text("time,value\n0,21\n1,22\n", encoding="utf-8")
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = loader.open_source(source, TabularLoadOptions(cache_policy=cache_policy))
    return source, loader, ref


def _change_content(source: Path) -> None:
    stamp = source.stat()
    original = source.read_bytes()
    source.write_bytes(original.replace(b"21", b"91").replace(b"22", b"92"))
    os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert source.stat().st_size == stamp.st_size
    assert source.stat().st_mtime_ns == stamp.st_mtime_ns


def test_binding_is_deterministic_typed_and_does_not_materialize(tmp_path, monkeypatch):
    source, loader, ref = _table(tmp_path)
    calls = []
    hash_file = resources.hash_file_provenance

    def count_hash(path, **kwargs):
        calls.append(path)
        return hash_file(path, **kwargs)

    monkeypatch.setattr(resources, "hash_file_provenance", count_hash)
    monkeypatch.setattr(loader, "open_source", lambda *args: pytest.fail("binding must not reopen data"))
    window = TabularWindowRef("window", ref, row_limit=1)
    value = {"second": [window.to_payload()], "first": DataTree.from_item(ref)}
    validation = resources.RetainedSourceValidation()
    bindings = resources.collect_retained_source_bindings(value, validation=validation)
    resources.validate_retained_source_bindings(value, bindings, validation=validation)
    assert len(calls) == 1
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert binding.source_uri == source.resolve().as_uri()
    assert RetainedSourceBinding.from_payload(json.loads(json.dumps(binding.to_payload()))) == binding
    assert resources.collect_retained_source_bindings(dict(reversed(list(value.items())))) == bindings
    assert binding.digest == resources.collect_retained_source_bindings(ref)[0].digest
    assert "retained" not in json.dumps(ref.to_payload())


@pytest.mark.parametrize("change", ["content", "missing"])
def test_binding_rejects_changed_or_missing_sources(tmp_path, change):
    source, _, ref = _table(tmp_path)
    bindings = resources.collect_retained_source_bindings(ref)
    if change == "content":
        _change_content(source)
    else:
        source.unlink()
    with pytest.raises(RetainedResourceError):
        resources.validate_retained_source_bindings(ref, bindings)


@pytest.mark.parametrize("field,value", [
    ("resolver_id", "unknown.resolver"), ("backend_id", "wrong.backend"),
    ("object_id", "other"), ("source_uri", "https://example.invalid/table.csv"),
])
def test_changed_ref_descriptor_is_not_an_accepted_binding(tmp_path, field, value):
    _, _, ref = _table(tmp_path)
    bindings = resources.collect_retained_source_bindings(ref)
    changed = replace(ref, **{field: value})
    with pytest.raises(ValueError):
        resources.validate_retained_source_bindings(changed, bindings)


def test_unknown_resolver_cannot_be_retained(tmp_path):
    _, loader, ref = _table(tmp_path)
    with pytest.raises(RetainedResourceError, match="resolver"):
        resources.collect_retained_source_bindings(replace(ref, resolver_id="unknown"))
    with pytest.raises(RetainedResourceError, match="resolver"):
        loader.ensure_ref_open(replace(ref, resolver_id="unknown"))


def test_forwarding_does_not_rebind_an_accepted_source_after_mutation(tmp_path):
    source, _, ref = _table(tmp_path)
    bindings = resources.collect_retained_source_bindings(ref)
    with resources.retained_source_binding_scope(bindings):
        assert resources.collect_retained_source_bindings(TabularWindowRef("forwarded", ref)) == bindings
        _change_content(source)
        with pytest.raises(RetainedResourceError):
            resources.collect_retained_source_bindings(TabularWindowRef("forwarded", ref))


def test_binding_hashing_honors_cancellation(tmp_path):
    _, _, ref = _table(tmp_path)
    event = threading.Event()
    event.set()
    with pytest.raises(RetainedResourceError, match="cancelled"):
        resources.collect_retained_source_bindings(ref, validation=resources.RetainedSourceValidation(cancel_event=event))


def test_options_and_content_are_committed_and_wire_is_strict(tmp_path):
    _, _, ref = _table(tmp_path)
    binding, = resources.collect_retained_source_bindings(ref)
    changed = replace(ref, metadata={**ref.metadata, "load_options": {**ref.metadata["load_options"], "skip_rows": 1}})
    with pytest.raises(RetainedResourceError):
        resources.validate_retained_source_bindings(changed, [binding])
    assert replace(binding, sha256="f" * 64).digest != binding.digest
    with pytest.raises(ValueError, match="canonical"):
        replace(binding, options_json=json.dumps(json.loads(binding.options_json), indent=2))
    with pytest.raises(ValueError, match="unexpected"):
        RetainedSourceBinding.from_payload({**binding.to_payload(), "extra": True})


def test_consumed_subset_does_not_inspect_unconsumed_missing_source(tmp_path):
    source, _, ref = _table(tmp_path)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    _, _, other = _table(other_dir)
    bindings = resources.collect_retained_source_bindings([ref, other])
    source.unlink()
    consumed = resources.bindings_for_value(other, bindings)
    resources.validate_retained_source_bindings(other, consumed)
    with pytest.raises(RetainedResourceError):
        resources.validate_retained_source_bindings([ref, other], bindings)


def test_strict_reads_reject_late_changes_even_in_a_fresh_loader(tmp_path):
    source, loader, ref = _table(tmp_path)
    bindings = resources.collect_retained_source_bindings(ref)
    with resources.retained_source_binding_scope(bindings):
        assert loader.rows(ref, TabularWindowRequest(row_limit=1, column_limit=2))[0]["value"] == "21"
        _change_content(source)
        for reader in (loader, TabularLoaderCacheService(cache_dir=tmp_path / "fresh-cache")):
            with pytest.raises(RetainedResourceError):
                reader.rows(ref, TabularWindowRequest(row_limit=1, column_limit=2))
            with pytest.raises(RetainedResourceError):
                reader.ensure_ref_open(ref)


def test_source_change_during_a_read_is_rejected_before_return(tmp_path, monkeypatch):
    source, loader, ref = _table(tmp_path)
    bindings = resources.collect_retained_source_bindings(ref)
    read = loader._read_text_window

    def mutate_during_read(*args):
        result = read(*args)
        _change_content(source)
        return result

    monkeypatch.setattr(loader, "_read_text_window", mutate_during_read)
    with resources.retained_source_binding_scope(bindings), pytest.raises(RetainedResourceError):
        loader.window(ref, TabularWindowRequest(row_limit=1, column_limit=2))


def test_lazy_reads_validate_at_consumption_and_completion(tmp_path):
    source, loader, ref = _table(tmp_path)
    bindings = resources.collect_retained_source_bindings(ref)
    with resources.retained_source_binding_scope(bindings):
        iterator = loader.iter_window_rows(ref, TabularWindowRequest(row_limit=2, column_limit=2))
        assert next(iterator)["value"] == "21"
        _change_content(source)
        with pytest.raises(RetainedResourceError):
            list(iterator)
        late_iterator = loader.arrow_batches(ref, TabularArrowBatchOptions(row_limit=2, batch_size=1))
        with pytest.raises(RetainedResourceError):
            next(late_iterator)


@pytest.mark.parametrize("method", ["iter_window_rows", "arrow_batches"])
def test_mutation_during_first_batch_never_reaches_a_partial_consumer(tmp_path, monkeypatch, method):
    source, loader, ref = _table(tmp_path)
    bindings = resources.collect_retained_source_bindings(ref)
    read = loader._iter_text_records

    def changed_rows(*args):
        _change_content(source)
        yield from read(*args)

    monkeypatch.setattr(loader, "_iter_text_records", changed_rows)
    request = (
        TabularWindowRequest(row_limit=2, column_limit=2) if method == "iter_window_rows"
        else TabularArrowBatchOptions(row_limit=2, batch_size=1)
    )
    observed = []
    with resources.retained_source_binding_scope(bindings):
        stream = getattr(loader, method)(ref, request)
        with pytest.raises(RetainedResourceError):
            observed.extend(islice(stream, 1))
    assert observed == []


def test_retained_row_iteration_validates_bounded_batches_not_every_scalar_row(tmp_path, monkeypatch):
    source, loader, ref = _table(tmp_path)
    source.write_text("time,value\n" + "".join(f"{i},21\n" for i in range(5000)), encoding="utf-8")
    ref = loader.open_source(source, TabularLoadOptions(cache_policy="source_direct"))
    bindings = resources.collect_retained_source_bindings(ref)
    calls = []
    hash_file = resources.hash_file_provenance

    def count_hash(*args, **kwargs):
        calls.append(args[0])
        return hash_file(*args, **kwargs)

    monkeypatch.setattr(resources, "hash_file_provenance", count_hash)
    with resources.retained_source_binding_scope(bindings):
        rows = list(loader.iter_window_rows(ref, TabularWindowRequest(row_limit=5000, column_limit=2)))
    assert len(rows) == 5000
    assert 3 <= len(calls) <= 6


@pytest.mark.parametrize("backing", ["virtual", "external_storage"])
def test_retained_hdf5_rejects_data_outside_container_but_fresh_loads_work(tmp_path, backing):
    h5py = pytest.importorskip("h5py")
    np = pytest.importorskip("numpy")
    source = tmp_path / "container.h5"
    if backing == "virtual":
        external = tmp_path / "external.h5"
        with h5py.File(external, "w") as handle:
            handle.create_dataset("values", data=np.arange(6).reshape(2, 3))
        layout = h5py.VirtualLayout(shape=(2, 3), dtype="i8")
        layout[:] = h5py.VirtualSource(str(external), "values", shape=(2, 3))
        with h5py.File(source, "w") as handle:
            handle.create_virtual_dataset("values", layout)
    else:
        with h5py.File(source, "w") as handle:
            dataset = handle.create_dataset("values", shape=(2, 3), dtype="i8", external=[(str(tmp_path / "raw.bin"), 0, h5py.h5f.UNLIMITED)])
            dataset[:] = np.arange(6).reshape(2, 3)
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = loader.open_source(source)
    assert loader.slice_2d(ref, ArraySlice2DRequest(row_limit=1, column_limit=2)).values == ((0, 1),)
    with pytest.raises(RetainedResourceError, match="Externally backed"):
        resources.collect_retained_source_bindings(ref)


@pytest.mark.parametrize("linked_group", [False, True])
def test_retained_hdf5_rejects_external_links_before_dereferencing(tmp_path, linked_group):
    h5py = pytest.importorskip("h5py")
    np = pytest.importorskip("numpy")
    source = tmp_path / "container.h5"
    external = tmp_path / "external.h5"
    with h5py.File(external, "w") as handle:
        handle.create_dataset("group/values", data=np.arange(6).reshape(2, 3))
    with h5py.File(source, "w") as handle:
        handle.create_dataset("local", data=np.arange(6).reshape(2, 3))
        handle["linked"] = h5py.ExternalLink(str(external), "group" if linked_group else "group/values")
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = loader.open_source(source, TabularLoadOptions(selected_object="local"))
    # The ordinary scanner exposes only local objects; forged/forwarded refs
    # must not smuggle a linked object past single-file binding validation.
    linked = replace(ref, object_id="linked/values" if linked_group else "linked")
    with pytest.raises(RetainedResourceError, match="in-file path"):
        resources.collect_retained_source_bindings(linked)
    bindings = resources.collect_retained_source_bindings(ref)
    with resources.retained_source_binding_scope(bindings):
        assert loader.slice_2d(ref, ArraySlice2DRequest(row_limit=1, column_limit=2)).values == ((0, 1),)


def test_ordinary_loader_reopening_remains_available_outside_binding_scope(tmp_path):
    source, loader, ref = _table(tmp_path)
    bindings = resources.collect_retained_source_bindings(ref)
    source.write_text("time,value,new\n0,99,1\n", encoding="utf-8")
    with resources.retained_source_binding_scope(bindings), pytest.raises(RetainedResourceError):
        loader.window(ref, TabularWindowRequest(row_limit=1, column_limit=3))
    assert loader.window(ref, TabularWindowRequest(row_limit=1, column_limit=3)).rows[0]["new"] == "1"


def test_bound_cache_never_uses_stat_keyed_old_content(tmp_path):
    pytest.importorskip("pyarrow")
    source, loader, ref = _table(tmp_path, cache_policy="app_managed_parquet")
    request = TabularWindowRequest(row_limit=2, column_limit=2)
    assert loader.window(ref, request).rows[0]["value"] == 21
    old_bindings = resources.collect_retained_source_bindings(ref)
    _change_content(source)
    # Identical size/mtime produces the same legacy ID, but a new retained commitment.
    new_ref = loader.open_source(source)
    assert ref.ref_id == new_ref.ref_id
    bindings = resources.collect_retained_source_bindings(new_ref)
    assert old_bindings != bindings
    with resources.retained_source_binding_scope(bindings):
        assert loader.window(new_ref, request).rows[0]["value"] == 91
    with resources.retained_source_binding_scope(old_bindings), pytest.raises(RetainedResourceError):
        loader.window(ref, request)


def test_array_wrapper_and_materialization_are_source_bound(tmp_path):
    np = pytest.importorskip("numpy")
    source = tmp_path / "array.npy"
    np.save(source, np.arange(6).reshape(2, 3))
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = loader.open_source(source)
    wrapper = ArraySlice2DRef("slice", ref, row_limit=1, column_limit=2)
    bindings = resources.collect_retained_source_bindings({"nested": [wrapper.to_payload()]})
    with resources.retained_source_binding_scope(bindings):
        result = loader.to_numpy(ref, ArrayMaterializationOptions(max_elements=2))
        assert not isinstance(result, np.memmap)
        assert result.tolist() == [0, 1]
        np.save(source, np.full((2, 3), 9))
        assert result.tolist() == [0, 1]
        with pytest.raises(RetainedResourceError):
            loader.slice_2d(ref, ArraySlice2DRequest(row_limit=1, column_limit=2))


def test_binding_scopes_are_isolated_and_follow_internal_io_dispatch(tmp_path):
    _, loader, ref = _table(tmp_path)
    binding, = resources.collect_retained_source_bindings(ref)
    barrier = threading.Barrier(2)

    def observe(bindings):
        with resources.retained_source_binding_scope(bindings):
            barrier.wait(timeout=5)
            return resources.retained_binding_for_ref(ref)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(observe, [binding])
        second = executor.submit(observe, [])
        assert first.result(timeout=10) == binding
        assert second.result(timeout=10) is None
    with resources.retained_source_binding_scope([binding]):
        assert loader._run_io(resources.retained_binding_for_ref, ref) == binding
    assert resources.retained_binding_for_ref(ref) is None
