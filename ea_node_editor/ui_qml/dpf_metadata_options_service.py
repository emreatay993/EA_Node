# Purpose: Load lightweight DPF result metadata off the UI thread for inspector selectors.
# Map: docs/agent_maps/feature_routes/ansys_dpf_operator_viewer_transport.md
# Tests: tests/test_dpf_metadata_options_service.py
from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot


_CACHE_LIMIT = 32
_ConsumerKey = tuple[str, str]
MetadataLoader = Callable[[str], Mapping[str, Iterable[Any]]]


def _dedupe_text(values: Iterable[Any]) -> tuple[str, ...]:
    resolved: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        folded = text.casefold()
        if not text or folded in seen:
            continue
        seen.add(folded)
        resolved.append(text)
    return tuple(resolved)


def _result_names(result_info: Any) -> tuple[str, ...]:
    available = getattr(result_info, "available_results", ())
    if isinstance(available, Mapping):
        values: Iterable[Any] = available.values()
    elif available is None:
        values = ()
    else:
        values = available
    names: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            candidate = value.get("name") or value.get("scripting_name") or value.get("operator_name")
        else:
            candidate = getattr(value, "name", "") or getattr(value, "operator_name", "")
        names.append(str(candidate or ""))
    return _dedupe_text(names)


def load_dpf_metadata_options(result_path: str) -> dict[str, tuple[str, ...]]:
    """Open one result model and return inspector-safe metadata only."""

    import importlib

    from ea_node_editor.execution.dpf_runtime.optional_imports import load_dpf_module

    dpf = load_dpf_module(importlib.import_module)
    model = dpf.Model(result_path)
    metadata = getattr(model, "metadata", None)
    support = getattr(metadata, "time_freq_support", None)
    try:
        set_count = int(getattr(support, "n_sets", 0) or 0)
    except (TypeError, ValueError):
        set_count = 0
    frequencies = getattr(getattr(support, "time_frequencies", None), "data", None)
    if frequencies is None:
        frequencies = ()
    named_selections = getattr(metadata, "available_named_selections", None)
    if named_selections is None:
        named_selections = ()
    return {
        "result_name": _result_names(getattr(metadata, "result_info", None)),
        "set_ids": tuple(str(value) for value in range(1, set_count + 1)),
        "time_values": _dedupe_text(
            str(float(value)) if isinstance(value, (int, float)) else str(value)
            for value in frequencies
        ),
        "named_selection": _dedupe_text(named_selections),
    }


@dataclass(frozen=True, slots=True)
class DpfMetadataOptionsEntry:
    signature: str
    revision: int
    result_path: str
    result_names: tuple[str, ...] = ()
    set_ids: tuple[str, ...] = ()
    time_values: tuple[str, ...] = ()
    named_selections: tuple[str, ...] = ()
    error: str = ""

    def option_values(self, key: str) -> tuple[str, ...]:
        return {
            "result_name": self.result_names,
            "set_ids": self.set_ids,
            "time_values": self.time_values,
            "named_selection": self.named_selections,
            "mode": self.set_ids,
        }.get(str(key or "").strip(), ())


@dataclass(frozen=True, slots=True)
class DpfMetadataOptionsSnapshot:
    state: str
    signature: str = ""
    revision: int = 0
    entry: DpfMetadataOptionsEntry | None = None
    error: str = ""


class DpfMetadataOptionsCache:
    def __init__(self, *, limit: int = _CACHE_LIMIT) -> None:
        self._limit = max(1, int(limit))
        self._entries: dict[str, DpfMetadataOptionsEntry] = {}
        self._revision = 0
        self._lock = threading.Lock()

    def get(self, signature: str) -> DpfMetadataOptionsEntry | None:
        with self._lock:
            entry = self._entries.pop(str(signature), None)
            if entry is not None:
                self._entries[entry.signature] = entry
            return entry

    def store(
        self,
        *,
        signature: str,
        result_path: str,
        options: Mapping[str, Iterable[Any]] | None = None,
        error: str = "",
    ) -> DpfMetadataOptionsEntry:
        values = dict(options or {})
        with self._lock:
            self._revision += 1
            entry = DpfMetadataOptionsEntry(
                signature=str(signature),
                revision=self._revision,
                result_path=str(result_path),
                result_names=_dedupe_text(values.get("result_name", ())),
                set_ids=_dedupe_text(values.get("set_ids", ())),
                time_values=_dedupe_text(values.get("time_values", ())),
                named_selections=_dedupe_text(values.get("named_selection", ())),
                error=str(error or "").strip(),
            )
            self._entries.pop(entry.signature, None)
            self._entries[entry.signature] = entry
            while len(self._entries) > self._limit:
                self._entries.pop(next(iter(self._entries)), None)
            return entry

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def discard(self, signature: str) -> None:
        with self._lock:
            self._entries.pop(str(signature), None)


class _MetadataSignals(QObject):
    finished = pyqtSignal(str, str, str, dict, str, bool)
    """(request_key, signature, result_path, options, error, unchanged)"""


class _MetadataRunnable(QRunnable):
    def __init__(
        self,
        *,
        signals: _MetadataSignals,
        request_key: str,
        result_path: str,
        known_signature: str,
        loader: MetadataLoader,
    ) -> None:
        super().__init__()
        self._signals = signals
        self._request_key = request_key
        self._result_path = result_path
        self._known_signature = known_signature
        self._loader = loader

    def run(self) -> None:  # noqa: D102 - QRunnable contract
        try:
            resolved_path = str(Path(self._result_path).expanduser().resolve(strict=False))
            modified_ns = int(Path(resolved_path).stat().st_mtime_ns)
            signature = f"{resolved_path}|{modified_ns}"
            unchanged = bool(self._known_signature and signature == self._known_signature)
            options = {} if unchanged else dict(self._loader(resolved_path))
            error = ""
        except Exception as exc:  # noqa: BLE001 - shown in the inspector
            resolved_path = self._result_path
            signature = f"{self._request_key}|unavailable"
            options, error, unchanged = {}, str(exc), False
        self._signals.finished.emit(
            self._request_key,
            signature,
            resolved_path,
            options,
            error,
            unchanged,
        )


class DpfMetadataOptionsService(QObject):
    options_ready = pyqtSignal(str, str, int)
    """(workspace_id, node_id, metadata_revision)"""

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        cache: DpfMetadataOptionsCache | None = None,
        loader: MetadataLoader = load_dpf_metadata_options,
        max_threads: int = 2,
        freshness_interval_s: float = 1.0,
    ) -> None:
        super().__init__(parent)
        self._cache = cache or DpfMetadataOptionsCache()
        self._loader = loader
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(max(1, int(max_threads)))
        self._signals = _MetadataSignals(self)
        self._signals.finished.connect(self._on_finished)
        self._freshness_interval_s = max(0.0, float(freshness_interval_s))
        self._latest_requests: dict[_ConsumerKey, str] = {}
        self._path_signatures: dict[str, str] = {}
        self._last_checked_at: dict[str, float] = {}
        self._in_flight: dict[str, set[_ConsumerKey]] = {}
        self._shutdown = False

    @property
    def cache(self) -> DpfMetadataOptionsCache:
        return self._cache

    def request_options(
        self,
        *,
        workspace_id: str,
        node_id: str,
        result_path: str,
    ) -> DpfMetadataOptionsSnapshot:
        if self._shutdown:
            return DpfMetadataOptionsSnapshot(state="error", error="DPF metadata service is stopped.")
        request_key = str(result_path or "").strip()
        if not request_key:
            return DpfMetadataOptionsSnapshot(state="empty")
        consumer = (str(workspace_id or ""), str(node_id or ""))
        self._latest_requests[consumer] = request_key
        known_signature = self._path_signatures.get(request_key, "")
        entry = self._cache.get(known_signature) if known_signature else None
        due_for_check = (
            time.monotonic() - self._last_checked_at.get(request_key, 0.0)
            >= self._freshness_interval_s
        )
        consumers = self._in_flight.get(request_key)
        if consumers is not None:
            consumers.add(consumer)
        elif entry is None or due_for_check:
            self._in_flight[request_key] = {consumer}
            self._thread_pool.start(
                _MetadataRunnable(
                    signals=self._signals,
                    request_key=request_key,
                    result_path=request_key,
                    known_signature=known_signature,
                    loader=self._loader,
                )
            )
        if entry is not None:
            return DpfMetadataOptionsSnapshot(
                state="error" if entry.error else "ready",
                signature=entry.signature,
                revision=entry.revision,
                entry=entry,
                error=entry.error,
            )
        return DpfMetadataOptionsSnapshot(state="loading", signature=known_signature)

    def invalidate_all(self) -> None:
        self._cache.clear()
        self._path_signatures.clear()
        self._last_checked_at.clear()

    def shutdown(self) -> None:
        self._shutdown = True
        self._thread_pool.clear()
        self._thread_pool.waitForDone(2000)
        self._latest_requests.clear()
        self._path_signatures.clear()
        self._last_checked_at.clear()
        self._in_flight.clear()

    @pyqtSlot(str, str, str, dict, str, bool)
    def _on_finished(
        self,
        request_key: str,
        signature: str,
        result_path: str,
        options: dict,
        error: str,
        unchanged: bool,
    ) -> None:
        consumers = self._in_flight.pop(request_key, set())
        if self._shutdown:
            return
        self._last_checked_at[request_key] = time.monotonic()
        if unchanged:
            return
        entry = self._cache.store(
            signature=signature,
            result_path=result_path,
            options=options,
            error=error,
        )
        previous_signature = self._path_signatures.get(request_key, "")
        if previous_signature and previous_signature != signature:
            self._cache.discard(previous_signature)
        self._path_signatures[request_key] = signature
        for workspace_id, node_id in consumers:
            if self._latest_requests.get((workspace_id, node_id)) != request_key:
                continue
            self.options_ready.emit(workspace_id, node_id, entry.revision)


_shared_service: DpfMetadataOptionsService | None = None


def shared_dpf_metadata_options_service() -> DpfMetadataOptionsService:
    global _shared_service
    if _shared_service is None:
        _shared_service = DpfMetadataOptionsService()
    return _shared_service


def existing_dpf_metadata_options_service() -> DpfMetadataOptionsService | None:
    return _shared_service


def reset_shared_dpf_metadata_options_service() -> None:
    global _shared_service
    if _shared_service is not None:
        _shared_service.shutdown()
    _shared_service = None


__all__ = [
    "DpfMetadataOptionsCache",
    "DpfMetadataOptionsEntry",
    "DpfMetadataOptionsService",
    "DpfMetadataOptionsSnapshot",
    "existing_dpf_metadata_options_service",
    "load_dpf_metadata_options",
    "reset_shared_dpf_metadata_options_service",
    "shared_dpf_metadata_options_service",
]
