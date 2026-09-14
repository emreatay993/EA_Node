# Purpose: Bound compilation reuse without exposing mutable cached workspaces.
# Map: subsystems/execution.md
# Tests: tests/test_execution_submission.py
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from functools import cached_property
import copy
import hashlib
import json
import threading

from ea_node_editor.execution.compiler import compile_runtime_snapshot
from ea_node_editor.execution.runtime_dto import RuntimeWorkspace
from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot
from ea_node_editor.execution.solution_identity import canonical_digest
from ea_node_editor.nodes.registry import NodeRegistry


@dataclass(frozen=True, slots=True)
class CompiledSnapshot:
    workspace: RuntimeWorkspace
    _identity: _SnapshotIdentity

    @property
    def snapshot_fingerprint(self) -> str:
        return self._identity.fingerprint

    @property
    def encoded_size(self) -> int:
        return len(self._identity.encoded)


@dataclass(frozen=True)
class _SnapshotIdentity:
    encoded: bytes

    @cached_property
    def fingerprint(self) -> str:
        # The wire projection is already validated JSON. Invalidation needs
        # only topology; preparation computes this commitment outside the GUI
        # thread, once for the entry shared with final dispatch validation.
        return canonical_digest(json.loads(self.encoded))


class CompiledSnapshotCache:
    """Keep at most two private compilations; callers receive their own DTOs."""

    def __init__(
        self, *, max_entries: int = 2, max_bytes: int = 64 * 1024 * 1024
    ) -> None:
        if (
            type(max_entries) is not int
            or type(max_bytes) is not int
            or min(max_entries, max_bytes) < 0
        ):
            raise ValueError(
                "compiled snapshot cache limits must be non-negative integers"
            )
        self._max_entries = max_entries
        self._max_bytes = max_bytes
        self._entries: OrderedDict[tuple[NodeRegistry, str, str], CompiledSnapshot] = (
            OrderedDict()
        )
        self._lock = threading.Lock()
        self._epoch = 0

    def get(
        self, snapshot: RuntimeSnapshot, *, workspace_id: str, registry: NodeRegistry
    ) -> CompiledSnapshot:
        if not registry.is_frozen:
            raise ValueError("compiled snapshots require a frozen registry")
        payload = snapshot.to_document(catalog=registry.data_types)
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        key = (registry, workspace_id, hashlib.sha256(encoded).hexdigest())
        with self._lock:
            epoch = self._epoch
            cached = self._entries.get(key)
            if cached is not None:
                self._entries.move_to_end(key)
        if cached is None:
            # No compilation or user-provided metadata resolver runs under the cache lock.
            cached = CompiledSnapshot(
                compile_runtime_snapshot(
                    snapshot, workspace_id=workspace_id, registry=registry
                ),
                _SnapshotIdentity(encoded),
            )
            if len(encoded) <= self._max_bytes and self._max_entries > 0:
                with self._lock:
                    if epoch == self._epoch:
                        self._entries[key] = cached
                        self._entries.move_to_end(key)
                        while (
                            len(self._entries) > self._max_entries
                            or sum(item.encoded_size for item in self._entries.values())
                            > self._max_bytes
                        ):
                            self._entries.popitem(last=False)
        return CompiledSnapshot(
            copy.deepcopy(cached.workspace),
            cached._identity,
        )

    def clear(self) -> None:
        with self._lock:
            self._epoch += 1
            self._entries.clear()

    def retire_workspace(self, workspace_id: str) -> None:
        with self._lock:
            self._epoch += 1
            for key in tuple(self._entries):
                if key[1] == workspace_id:
                    del self._entries[key]

    @property
    def entry_count(self) -> int:
        with self._lock:
            return len(self._entries)

    @property
    def encoded_bytes(self) -> int:
        with self._lock:
            return sum(item.encoded_size for item in self._entries.values())
