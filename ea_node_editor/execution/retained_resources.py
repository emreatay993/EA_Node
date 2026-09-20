# Purpose: Share retained-source collection, validation, and isolated read bindings across host and worker.
# Map: subsystems/execution.md
# Tests: tests/test_retained_resources.py
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
import threading
import json
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname
from typing import Any

from ea_node_editor.execution.solution_identity import (
    DEFAULT_PROVENANCE_HASH_POLICY, FileProvenance, SolutionIdentityError, hash_file_provenance,
)
from ea_node_editor.runtime_contracts import DataTree, TypedInlineValue
from ea_node_editor.runtime_contracts.retained_resources import RetainedResourceError, RetainedSourceBinding
from ea_node_editor.runtime_contracts.tabular_data import (
    ArrayDataRef, ArraySlice2DRef, TabularDataRef, TabularWindowRef,
    coerce_array_data_ref, coerce_array_slice_2d_ref, coerce_tabular_data_ref, coerce_tabular_window_ref,
)


SourceRef = TabularDataRef | ArrayDataRef
_active_bindings: ContextVar[Mapping[tuple[str, str, str], RetainedSourceBinding]] = ContextVar(
    "retained_source_bindings", default={},
)


def iter_retained_source_refs(value: Any) -> Iterator[SourceRef]:
    """Visit supported bases within wrappers, containers, trees and wire refs."""
    count = 0

    def visit(item: Any, depth: int) -> Iterator[SourceRef]:
        nonlocal count
        count += 1
        if depth > 32 or count > 1_000_000:
            raise RetainedResourceError("retained_resource_limit", "Retained values exceed the traversal limit")
        if isinstance(item, (TabularDataRef, ArrayDataRef)):
            yield item
        elif isinstance(item, TabularWindowRef):
            yield item.table_data
        elif isinstance(item, ArraySlice2DRef):
            yield item.array_data
        elif isinstance(item, TypedInlineValue):
            yield from visit(item.payload, depth + 1)
        elif isinstance(item, Mapping):
            if not isinstance(item, DataTree):
                for coerce in (coerce_tabular_data_ref, coerce_array_data_ref, coerce_tabular_window_ref, coerce_array_slice_2d_ref):
                    ref = coerce(item)
                    if ref is not None:
                        yield from visit(ref, depth + 1)
                        return
            for nested in item.values():
                yield from visit(nested, depth + 1)
        elif isinstance(item, (list, tuple)):
            for nested in item:
                yield from visit(nested, depth + 1)

    yield from visit(value, 0)


class RetainedSourceValidation:
    """One preparation/preflight pass; never retain this cache across requests or reads."""

    def __init__(self, *, cancel_event: threading.Event | None = None) -> None:
        self._provenance: dict[str, FileProvenance] = {}
        self._cancel_event = cancel_event

    def fingerprint(self, ref: SourceRef) -> FileProvenance:
        from ea_node_editor.addons.tabular_data.retained_sources import source_path_from_ref

        path = source_path_from_ref(ref)
        return self.file_fingerprint(path)

    def file_fingerprint(self, path: Path) -> FileProvenance:
        uri = path.as_uri()
        if uri not in self._provenance:
            try:
                self._provenance[uri] = hash_file_provenance(path, cancel_event=self._cancel_event)
            except SolutionIdentityError as exc:
                raise RetainedResourceError(exc.reason_code, str(exc)) from exc
        return self._provenance[uri]

    def bind(self, ref: SourceRef) -> RetainedSourceBinding:
        from ea_node_editor.addons.tabular_data.retained_sources import describe_tabular_source

        descriptor = describe_tabular_source(ref)
        provenance = self.fingerprint(ref)
        return RetainedSourceBinding(
            **descriptor, size_bytes=provenance.size_bytes, sha256=provenance.sha256,
            hash_policy_digest=provenance.policy_digest,
        )

    def validate(self, ref: SourceRef, binding: RetainedSourceBinding) -> None:
        if binding.hash_policy_digest != DEFAULT_PROVENANCE_HASH_POLICY.digest:
            raise RetainedResourceError("retained_source_policy", "The retained source hash policy does not match")
        if self.bind(ref) != binding:
            raise RetainedResourceError("retained_source_changed", "The retained source differs from the accepted output")


def collect_retained_source_bindings(
    value: Any, *, validation: RetainedSourceValidation | None = None,
) -> tuple[RetainedSourceBinding, ...]:
    validation = validation or RetainedSourceValidation()
    bindings: dict[tuple[str, str, str], RetainedSourceBinding] = {}
    for ref in iter_retained_source_refs(value):
        binding = retained_binding_for_ref(ref)
        if binding is None:
            binding = validation.bind(ref)
        else:
            # A forwarding node cannot rebind accepted input data to changed bytes.
            validation.validate(ref, binding)
        previous = bindings.setdefault(binding.key, binding)
        if previous != binding:
            raise RetainedResourceError("retained_source_conflict", "Retained refs share an inconsistent identity")
    return tuple(bindings[key] for key in sorted(bindings))


def _binding_index(bindings: Sequence[RetainedSourceBinding]) -> dict[tuple[str, str, str], RetainedSourceBinding]:
    indexed: dict[tuple[str, str, str], RetainedSourceBinding] = {}
    for binding in bindings:
        if not isinstance(binding, RetainedSourceBinding):
            raise TypeError("Retained source bindings must be typed contracts")
        if indexed.setdefault(binding.key, binding) != binding:
            raise RetainedResourceError("retained_source_conflict", "Retained refs share an inconsistent identity")
    return indexed


def _ref_key(ref: SourceRef) -> tuple[str, str, str]:
    return ref.resolver_id, "table" if isinstance(ref, TabularDataRef) else "array", ref.ref_id


def bindings_for_value(value: Any, bindings: Sequence[RetainedSourceBinding]) -> tuple[RetainedSourceBinding, ...]:
    """Select a consumed subset without inspecting unconsumed source files."""
    indexed = _binding_index(bindings)
    keys = {_ref_key(ref) for ref in iter_retained_source_refs(value)}
    if not keys <= indexed.keys():
        raise RetainedResourceError("retained_source_unbound", "An accepted source reference has no binding")
    return tuple(indexed[key] for key in sorted(keys))


def validate_retained_source_bindings(
    value: Any, bindings: Sequence[RetainedSourceBinding], *, validation: RetainedSourceValidation | None = None,
) -> None:
    validation = validation or RetainedSourceValidation()
    indexed = _binding_index(bindings)
    visited = set()
    for ref in iter_retained_source_refs(value):
        key = _ref_key(ref)
        if key not in indexed:
            raise RetainedResourceError("retained_source_unbound", "An accepted source reference has no binding")
        validation.validate(ref, indexed[key])
        visited.add(key)
    if visited != indexed.keys():
        raise RetainedResourceError("retained_source_unused", "A retained source binding has no matching value")


def file_source_provenance_binding(path: Path, fingerprint: FileProvenance) -> RetainedSourceBinding:
    """Describe declared file dependence without claiming ownership of the file."""
    uri = path.absolute().as_uri()
    return RetainedSourceBinding(
        ref_kind="file", ref_id=hashlib.sha256(uri.encode("utf-8")).hexdigest(),
        resolver_id="corex.file_provenance", backend_id="file", source_uri=uri,
        object_id="file", options_json="{}", backend_policy_revision="content_only_no_links_v1",
        size_bytes=fingerprint.size_bytes, sha256=fingerprint.sha256,
        hash_policy_digest=fingerprint.policy_digest,
    )


def validate_source_provenance_bindings(
    bindings: Sequence[RetainedSourceBinding], *, validation: RetainedSourceValidation | None = None,
) -> None:
    """Validate source versions inherited by detached results without materializing data."""
    validation = validation or RetainedSourceValidation()
    for binding in _binding_index(bindings).values():
        if binding.ref_kind == "file":
            parsed = urlsplit(binding.source_uri)
            if parsed.scheme != "file" or parsed.query or parsed.fragment:
                raise RetainedResourceError("retained_source_descriptor", "File provenance requires a canonical file URI")
            path = Path(url2pathname(("//" + parsed.netloc if parsed.netloc else "") + parsed.path))
            if not path.is_absolute() or path.as_uri() != binding.source_uri:
                raise RetainedResourceError("retained_source_descriptor", "File provenance requires an absolute canonical path")
            if file_source_provenance_binding(path, validation.file_fingerprint(path)) != binding:
                raise RetainedResourceError("retained_source_changed", "The declared source file changed")
            continue
        from ea_node_editor.addons.tabular_data.retained_sources import source_path_from_ref
        from ea_node_editor.addons.tabular_data.source_backends import detect_format_id

        ref_type = TabularDataRef if binding.ref_kind == "table" else ArrayDataRef
        ref = ref_type(
            ref_id=binding.ref_id, resolver_id=binding.resolver_id,
            backend_id=binding.backend_id, source_uri=binding.source_uri,
            object_id=binding.object_id,
        )
        ref = ref_type(
            ref_id=binding.ref_id, resolver_id=binding.resolver_id,
            backend_id=binding.backend_id, source_uri=binding.source_uri,
            object_id=binding.object_id,
            metadata={
                "load_options": json.loads(binding.options_json),
                "backend_policy_revision": binding.backend_policy_revision,
                "format_id": detect_format_id(source_path_from_ref(ref)),
            },
        )
        validation.validate(ref, binding)


@contextmanager
def retained_source_binding_scope(bindings: Sequence[RetainedSourceBinding]) -> Iterator[None]:
    """Install only this run's accepted bindings; caller validates payloads first."""
    token = _active_bindings.set(_binding_index(bindings))
    try:
        yield
    finally:
        _active_bindings.reset(token)


def retained_binding_for_ref(ref: SourceRef) -> RetainedSourceBinding | None:
    return _active_bindings.get().get(_ref_key(ref))
