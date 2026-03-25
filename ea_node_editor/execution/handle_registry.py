from __future__ import annotations

import copy
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ea_node_editor.nodes.types import RuntimeHandleRef, coerce_runtime_handle_ref


def _copy_metadata_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): copy.deepcopy(item)
        for key, item in value.items()
    }


def _normalize_non_empty_string(field_name: str, value: object) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _normalize_worker_generation(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("worker_generation must be an integer")
    try:
        generation = int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("worker_generation must be an integer") from exc
    if generation < 0:
        raise ValueError("worker_generation must be >= 0")
    return generation


class StaleHandleError(LookupError):
    """Raised when a runtime handle ref no longer matches live worker state."""


@dataclass(slots=True)
class _HandleRecord:
    value: Any
    kind: str
    owner_scope: str
    metadata: dict[str, Any] = field(default_factory=dict)
    ref_count: int = 1

    def to_ref(self, handle_id: str, *, worker_generation: int) -> RuntimeHandleRef:
        return RuntimeHandleRef(
            handle_id=handle_id,
            kind=self.kind,
            owner_scope=self.owner_scope,
            worker_generation=worker_generation,
            metadata=self.metadata,
        )


class HandleRegistry:
    def __init__(self, *, worker_generation: int = 1) -> None:
        self._worker_generation = _normalize_worker_generation(worker_generation)
        self._records: dict[str, _HandleRecord] = {}
        self._owner_index: dict[str, set[str]] = defaultdict(set)

    @property
    def worker_generation(self) -> int:
        return self._worker_generation

    @property
    def active_handle_count(self) -> int:
        return len(self._records)

    def register(
        self,
        value: Any,
        *,
        kind: str,
        owner_scope: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef:
        normalized_kind = _normalize_non_empty_string("kind", kind)
        normalized_owner_scope = _normalize_non_empty_string("owner_scope", owner_scope)
        handle_id = uuid4().hex
        record = _HandleRecord(
            value=value,
            kind=normalized_kind,
            owner_scope=normalized_owner_scope,
            metadata=_copy_metadata_mapping(metadata),
        )
        self._records[handle_id] = record
        self._owner_index[normalized_owner_scope].add(handle_id)
        return record.to_ref(handle_id, worker_generation=self._worker_generation)

    def acquire(self, value: object) -> RuntimeHandleRef:
        handle_id, _, record = self._resolve_record(value)
        record.ref_count += 1
        return record.to_ref(handle_id, worker_generation=self._worker_generation)

    def resolve(self, value: object, *, expected_kind: str = "") -> Any:
        _, runtime_ref, record = self._resolve_record(value)
        if expected_kind:
            normalized_expected_kind = _normalize_non_empty_string("expected_kind", expected_kind)
            if normalized_expected_kind != record.kind or runtime_ref.kind != normalized_expected_kind:
                raise TypeError(
                    "Runtime handle kind mismatch: "
                    f"expected {normalized_expected_kind!r}, got {record.kind!r}"
                )
        return record.value

    def release(self, value: object) -> bool:
        handle_id, _, record = self._resolve_record(value)
        record.ref_count -= 1
        if record.ref_count > 0:
            return False
        self._discard_handle(handle_id, record.owner_scope)
        return True

    def ref_count(self, value: object) -> int:
        _, _, record = self._resolve_record(value)
        return record.ref_count

    def promote(
        self,
        value: object,
        *,
        owner_scope: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef:
        handle_id, _, record = self._resolve_record(value)
        normalized_owner_scope = _normalize_non_empty_string("owner_scope", owner_scope)
        previous_owner_scope = record.owner_scope
        if normalized_owner_scope != previous_owner_scope:
            self._owner_index[previous_owner_scope].discard(handle_id)
            if not self._owner_index[previous_owner_scope]:
                self._owner_index.pop(previous_owner_scope, None)
            record.owner_scope = normalized_owner_scope
            self._owner_index[normalized_owner_scope].add(handle_id)
        if metadata is not None:
            record.metadata = _copy_metadata_mapping(metadata)
        return record.to_ref(handle_id, worker_generation=self._worker_generation)

    def release_owner_scope(self, owner_scope: str) -> int:
        normalized_owner_scope = _normalize_non_empty_string("owner_scope", owner_scope)
        handle_ids = tuple(self._owner_index.get(normalized_owner_scope, ()))
        for handle_id in handle_ids:
            self._discard_handle(handle_id, normalized_owner_scope)
        return len(handle_ids)

    def reset(self) -> int:
        released_count = len(self._records)
        self._records.clear()
        self._owner_index.clear()
        self._worker_generation += 1
        return released_count

    def _discard_handle(self, handle_id: str, owner_scope: str) -> None:
        self._records.pop(handle_id, None)
        owner_handles = self._owner_index.get(owner_scope)
        if owner_handles is None:
            return
        owner_handles.discard(handle_id)
        if not owner_handles:
            self._owner_index.pop(owner_scope, None)

    def _resolve_record(self, value: object) -> tuple[str, RuntimeHandleRef, _HandleRecord]:
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is None:
            raise TypeError("Runtime handle operations require a RuntimeHandleRef payload.")
        if runtime_ref.worker_generation != self._worker_generation:
            raise StaleHandleError(
                "Runtime handle ref worker_generation is stale: "
                f"{runtime_ref.worker_generation} != {self._worker_generation}"
            )
        record = self._records.get(runtime_ref.handle_id)
        if record is None:
            raise StaleHandleError(f"Runtime handle ref is stale or unknown: {runtime_ref.handle_id!r}")
        if runtime_ref.owner_scope != record.owner_scope:
            raise StaleHandleError(
                "Runtime handle ref owner_scope is stale: "
                f"{runtime_ref.owner_scope!r} != {record.owner_scope!r}"
            )
        if runtime_ref.kind != record.kind:
            raise StaleHandleError(
                "Runtime handle ref kind is stale: "
                f"{runtime_ref.kind!r} != {record.kind!r}"
            )
        return runtime_ref.handle_id, runtime_ref, record


__all__ = [
    "HandleRegistry",
    "StaleHandleError",
]
