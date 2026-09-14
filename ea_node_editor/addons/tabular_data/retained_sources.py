# Purpose: Describe the concrete Tabular source contract without opening or materializing data.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_retained_resources.py
from __future__ import annotations

from contextvars import ContextVar
from functools import partial, wraps
import inspect
from itertools import islice
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from ea_node_editor.addons.tabular_data.policy import DEFAULT_TABULAR_BACKEND_POLICY
from ea_node_editor.addons.tabular_data.source_backends import TabularLoadOptions, detect_format_id, import_optional
from ea_node_editor.runtime_contracts.retained_resources import RetainedResourceError, canonical_options_json
from ea_node_editor.runtime_contracts.tabular_data import ArrayDataRef, TabularDataRef


TABULAR_CACHE_RESOLVER_ID = "tabular.cache"
_active_reads: ContextVar[frozenset[str]] = ContextVar("retained_tabular_reads", default=frozenset())


def retained_read_is_active(binding_digest: str) -> bool:
    return binding_digest in _active_reads.get()


def guarded_retained_read(method=None, *, batch_items: int = 1):
    """Validate a detached stream batch before any of its items reach a consumer."""
    if method is None:
        return partial(guarded_retained_read, batch_items=batch_items)
    from ea_node_editor.execution.retained_resources import RetainedSourceValidation, retained_binding_for_ref

    if inspect.isgeneratorfunction(method):
        @wraps(method)
        def stream(self, ref, *args, **kwargs):
            binding = retained_binding_for_ref(ref)
            if binding is None or retained_read_is_active(binding.digest):
                yield from method(self, ref, *args, **kwargs)
                return
            self.ensure_ref_open(ref)
            iterator = iter(method(self, ref, *args, **kwargs))
            try:
                while True:
                    token = _active_reads.set(_active_reads.get() | {binding.digest})
                    try:
                        batch = list(islice(iterator, batch_items))
                    finally:
                        _active_reads.reset(token)
                    # In particular, a caller consuming just next()/islice() must
                    # never observe bytes changed while the backend filled a batch.
                    RetainedSourceValidation().validate(ref, binding)
                    if not batch:
                        break
                    yield from batch
            finally:
                iterator.close()
                RetainedSourceValidation().validate(ref, binding)
        return stream

    @wraps(method)
    def read(self, ref, *args, **kwargs):
        binding = retained_binding_for_ref(ref)
        if binding is None or retained_read_is_active(binding.digest):
            return method(self, ref, *args, **kwargs)
        self.ensure_ref_open(ref)
        token = _active_reads.set(_active_reads.get() | {binding.digest})
        try:
            result = method(self, ref, *args, **kwargs)
        finally:
            _active_reads.reset(token)
        RetainedSourceValidation().validate(ref, binding)
        return result
    return read


def source_path_from_ref(ref: TabularDataRef | ArrayDataRef) -> Path:
    source_uri = str(ref.source_uri or "").strip()
    if not source_uri:
        raise ValueError(f"Cannot reopen tabular ref {ref.ref_id!r} without source_uri.")
    parsed = urlparse(source_uri)
    if parsed.scheme and parsed.scheme != "file":
        raise ValueError(f"Unsupported tabular ref source URI scheme: {parsed.scheme!r}.")
    if parsed.scheme == "file":
        netloc = f"//{parsed.netloc}" if parsed.netloc else ""
        return Path(url2pathname(netloc + parsed.path)).expanduser().resolve()
    return Path(source_uri).expanduser().resolve()


def load_options_from_ref(ref: TabularDataRef | ArrayDataRef) -> TabularLoadOptions:
    options = TabularLoadOptions.from_mapping(ref.metadata.get("load_options"))
    return options.with_selected_object(ref.object_id) if ref.object_id else options


def describe_tabular_source(ref: TabularDataRef | ArrayDataRef) -> dict[str, str]:
    if ref.resolver_id != TABULAR_CACHE_RESOLVER_ID:
        raise RetainedResourceError("retained_resolver_unknown", "The retained source resolver is unsupported")
    path = source_path_from_ref(ref)
    # Admit only the shipped source adapter, with explicit parser and backend policy facts.
    format_id = detect_format_id(path)
    if ref.metadata.get("format_id") != format_id:
        raise RetainedResourceError("retained_source_descriptor", "The retained source format does not match")
    policy_revision = ref.metadata.get("backend_policy_revision")
    if policy_revision != DEFAULT_TABULAR_BACKEND_POLICY.revision:
        raise RetainedResourceError("retained_source_policy", "The retained source backend policy is unsupported")
    if not isinstance(ref.metadata.get("load_options"), dict) or not ref.object_id:
        raise RetainedResourceError("retained_source_descriptor", "The retained source parser options are missing")
    if format_id == "hdf5":
        _require_contained_hdf5_dataset(path, ref.object_id)
    return {
        "ref_kind": "table" if isinstance(ref, TabularDataRef) else "array",
        "ref_id": ref.ref_id,
        "resolver_id": ref.resolver_id,
        "backend_id": ref.backend_id,
        "source_uri": path.as_uri(),
        "object_id": ref.object_id,
        "options_json": canonical_options_json(load_options_from_ref(ref).to_cache_payload()),
        "backend_policy_revision": policy_revision,
    }


def _require_contained_hdf5_dataset(path: Path, object_id: str) -> None:
    """Inspect dataset metadata only; a single-file binding excludes external data."""
    h5py = import_optional("h5py", format_id="hdf5", purpose="retained source validation")
    try:
        with h5py.File(path, "r") as handle:
            item = handle
            for part in object_id.split("/"):
                if not part:
                    continue
                # Do not dereference links to another file, including indirect
                # links reached through a soft-link target or a linked group.
                if not isinstance(item, h5py.Group) or not isinstance(item.get(part, getlink=True), h5py.HardLink):
                    raise RetainedResourceError("retained_source_dependency", "Retained HDF5 datasets require a direct in-file path")
                item = item[part]
            if not isinstance(item, h5py.Dataset):
                raise RetainedResourceError("retained_source_descriptor", "The retained HDF5 object is not a dataset")
            if item.is_virtual or item.external:
                raise RetainedResourceError("retained_source_dependency", "Externally backed HDF5 datasets cannot be retained")
    except (OSError, KeyError) as exc:
        raise RetainedResourceError("retained_source_unavailable", "The retained HDF5 dataset could not be inspected") from exc
