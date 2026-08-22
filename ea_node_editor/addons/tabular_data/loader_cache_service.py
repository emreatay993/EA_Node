# Purpose: Tabular add-on loader + parquet cache service — load options, source
#          stats, large-data materialization, and parquet cache keys/entries.
# Map: feature_routes/tabular_data_addon_preview
# Tests: tests/test_tabular_cache_service.py
# Landmarks: TabularLoaderCacheService, TabularLoadOptions, ParquetCacheKey, ParquetCacheEntry
from __future__ import annotations

import csv
import hashlib
import importlib
import json
import math
import os
import queue
import sys
import threading
from urllib.parse import urlparse
from urllib.request import url2pathname
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ea_node_editor.addons.tabular_data.policy import (
    CACHE_POLICY_APP_MANAGED_PARQUET,
    CACHE_POLICY_SOURCE_DIRECT,
    DEFAULT_TABULAR_BACKEND_POLICY,
    TabularBackendPolicy,
)
from ea_node_editor.runtime_contracts import (
    ArrayDataRef,
    ArrayMaterializationOptions,
    ArraySlice2D,
    ArraySlice2DRequest,
    TabularArrowBatchOptions,
    TabularColumn,
    TabularDataRef,
    TabularDataWindow,
    TabularMaterializationOptions,
    TabularSchema,
    TabularWindowRequest,
)
from ea_node_editor.settings import (
    TABULAR_DATA_CACHE_MAX_BYTES,
    TABULAR_DATA_INLINE_CONVERSION_BYTES,
    tabular_data_cache_dir,
)

def _preload_native_tabular_runtime() -> None:
    """Eagerly load every pyarrow native submodule used by this service.

    Lazily importing additional pyarrow extension DLLs (pyarrow.dataset via
    read_table, pyarrow._fs via ParquetWriter, ...) after a Qt Quick engine
    has run access-violates on Windows (observed with pyarrow 24.0 + PyQt6:
    the DLL static initializers corrupt the process and the next native call
    crashes). This module imports at registry build time — before any QML
    engine exists — so preloading here makes all later use safe. Best-effort:
    environments without the optional dependency keep working and report it
    through the normal _import_optional path.
    """

    if _running_in_pyinstaller_build_analysis():
        return

    for module_name in (
        "pyarrow",
        "pyarrow.compute",
        "pyarrow.csv",
        "pyarrow.dataset",
        "pyarrow.fs",
        "pyarrow.parquet",
    ):
        try:
            importlib.import_module(module_name)
        except Exception:  # noqa: BLE001 - optional dependency may be absent
            return


def _running_in_pyinstaller_build_analysis() -> bool:
    """Return true while PyInstaller's isolated analysis child imports app modules."""

    return any(name == "PyInstaller" or name.startswith("PyInstaller.") for name in sys.modules)


_preload_native_tabular_runtime()

TABULAR_CACHE_RESOLVER_ID = "tabular.cache"
SUPPORTED_FORMAT_IDS = ("csv", "tsv", "txt", "xlsx", "xlsm", "parquet", "hdf5", "npy", "npz")
TEXT_FORMAT_IDS = frozenset({"csv", "tsv", "txt"})
EXCEL_FORMAT_IDS = frozenset({"xlsx", "xlsm"})
ARRAY_FORMAT_IDS = frozenset({"hdf5", "npy", "npz"})
HDF5_SUFFIXES = frozenset({".h5", ".hdf5", ".hdf"})

# Sort/filter/search previews must scan the source to be correct, but a preview
# must stay responsive. Cap the rows scanned per query and report truncation so
# the surface can tell the user results are limited to the first N source rows.
PREVIEW_QUERY_SCAN_ROW_CAP = 200_000
_NUMERIC_TEXT_PATTERN = r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"


class TabularLoaderError(RuntimeError):
    recoverable = True


class MissingTabularDependencyError(TabularLoaderError):
    def __init__(self, *, format_id: str, dependency: str, purpose: str) -> None:
        self.format_id = format_id
        self.dependency = dependency
        self.purpose = purpose
        super().__init__(
            f"The {format_id} loader requires optional dependency {dependency!r} for {purpose}."
        )


class UnsupportedTabularFormatError(TabularLoaderError):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Unsupported tabular data format for {path.name!r}.")


class SelectionRequiredError(TabularLoaderError):
    def __init__(self, *, format_id: str, choices: Sequence["SelectableObject"]) -> None:
        self.format_id = format_id
        self.choices = tuple(choices)
        names = ", ".join(choice.object_id for choice in self.choices)
        super().__init__(f"The {format_id} source contains multiple objects; select one of: {names}.")


class LargeDataMaterializationError(TabularLoaderError):
    def __init__(self, message: str, *, size_bytes: int) -> None:
        self.size_bytes = size_bytes
        super().__init__(message)


class TabularCacheNotReadyError(TabularLoaderError):
    """The managed parquet cache for a source is not built yet.

    Raised instead of converting inline when conversion is not allowed on the
    calling thread (large sources on the UI thread). Callers translate this
    into a loading state and trigger conversion on a worker.
    """

    def __init__(self, *, source_path: Path, size_bytes: int) -> None:
        self.source_path = source_path
        self.size_bytes = size_bytes
        super().__init__(
            f"The managed cache for {source_path.name!r} is still being prepared."
        )


@dataclass(slots=True, frozen=True)
class TabularLoadOptions:
    delimiter: str | None = None
    encoding: str = "utf-8"
    header_row: int | None = 0
    skip_rows: int = 0
    schema_hints: Mapping[str, str] = field(default_factory=dict)
    selected_object: str = ""
    allow_npz_archive_preview: bool = False
    cache_policy: str = CACHE_POLICY_APP_MANAGED_PARQUET

    def __post_init__(self) -> None:
        delimiter = self.delimiter
        if delimiter == "\\t":
            delimiter = "\t"
        if delimiter is not None:
            delimiter = str(delimiter)
            if not delimiter:
                delimiter = None
            elif len(delimiter) != 1:
                raise ValueError("delimiter must be a single character")
        encoding = str(self.encoding or "utf-8").strip() or "utf-8"
        header_row = _normalize_optional_non_negative_int("header_row", self.header_row)
        skip_rows = _normalize_non_negative_int("skip_rows", self.skip_rows)
        hints = {
            str(key).strip(): str(value).strip()
            for key, value in dict(self.schema_hints or {}).items()
            if str(key).strip() and str(value).strip()
        }
        cache_policy = str(self.cache_policy or "").strip()
        if cache_policy not in {CACHE_POLICY_APP_MANAGED_PARQUET, CACHE_POLICY_SOURCE_DIRECT}:
            cache_policy = CACHE_POLICY_APP_MANAGED_PARQUET
        object.__setattr__(self, "delimiter", delimiter)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "header_row", header_row)
        object.__setattr__(self, "skip_rows", skip_rows)
        object.__setattr__(self, "schema_hints", hints)
        object.__setattr__(self, "selected_object", str(self.selected_object or "").strip())
        object.__setattr__(self, "allow_npz_archive_preview", bool(self.allow_npz_archive_preview))
        object.__setattr__(self, "cache_policy", cache_policy)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "TabularLoadOptions":
        if not isinstance(payload, Mapping):
            return cls()
        return cls(
            delimiter=payload.get("delimiter"),
            encoding=str(payload.get("encoding", "utf-8") or "utf-8"),
            header_row=payload.get("header_row", 0),
            skip_rows=payload.get("skip_rows", 0),
            schema_hints=payload.get("schema_hints") if isinstance(payload.get("schema_hints"), Mapping) else {},
            selected_object=str(payload.get("selected_object", "") or ""),
            allow_npz_archive_preview=bool(payload.get("allow_npz_archive_preview", False)),
            cache_policy=str(payload.get("cache_policy", "") or ""),
        )

    def with_selected_object(self, selected_object: str) -> "TabularLoadOptions":
        return replace(self, selected_object=selected_object)

    def to_cache_payload(self) -> dict[str, Any]:
        return {
            "delimiter": self.delimiter,
            "encoding": self.encoding,
            "header_row": self.header_row,
            "skip_rows": self.skip_rows,
            "schema_hints": dict(sorted(self.schema_hints.items())),
            "selected_object": self.selected_object,
            "allow_npz_archive_preview": self.allow_npz_archive_preview,
            "cache_policy": self.cache_policy,
        }

    @property
    def uses_managed_cache(self) -> bool:
        return self.cache_policy != CACHE_POLICY_SOURCE_DIRECT


@dataclass(slots=True, frozen=True)
class SourceStats:
    size_bytes: int
    mtime_ns: int


@dataclass(slots=True, frozen=True)
class SelectableObject:
    object_id: str
    display_name: str
    kind: str
    row_count: int | None = None
    column_count: int | None = None
    shape: tuple[int, ...] = ()
    dtype: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "object_id": self.object_id,
            "display_name": self.display_name,
            "kind": self.kind,
        }
        if self.row_count is not None:
            payload["row_count"] = self.row_count
        if self.column_count is not None:
            payload["column_count"] = self.column_count
        if self.shape:
            payload["shape"] = list(self.shape)
        if self.dtype:
            payload["dtype"] = self.dtype
        if self.metadata:
            payload["metadata"] = _json_safe_mapping(self.metadata)
        return payload


@dataclass(slots=True, frozen=True)
class SourceScanResult:
    source_path: Path
    format_id: str
    objects: tuple[SelectableObject, ...]
    selected_object_id: str = ""
    requires_selection: bool = False
    size_bytes: int = 0
    size_class: str = ""
    warnings: tuple[str, ...] = ()

    @property
    def selected_object(self) -> SelectableObject | None:
        if not self.selected_object_id:
            return None
        for item in self.objects:
            if item.object_id == self.selected_object_id:
                return item
        return None

    def to_payload(self) -> dict[str, Any]:
        return {
            "source_path": str(self.source_path),
            "format_id": self.format_id,
            "objects": [item.to_payload() for item in self.objects],
            "selected_object_id": self.selected_object_id,
            "requires_selection": self.requires_selection,
            "size_bytes": self.size_bytes,
            "size_class": self.size_class,
            "warnings": list(self.warnings),
        }


@dataclass(slots=True, frozen=True)
class ParquetCacheKey:
    key: str
    payload: Mapping[str, Any]


@dataclass(slots=True, frozen=True)
class ParquetCacheEntry:
    key: str
    cache_path: Path
    metadata_path: Path
    metadata: Mapping[str, Any]


@dataclass(slots=True, frozen=True)
class _TableRecord:
    source_path: Path
    format_id: str
    options: TabularLoadOptions
    object_id: str
    backend_id: str
    columns: tuple[TabularColumn, ...]
    row_count: int | None
    size_bytes: int
    warnings: tuple[str, ...]
    stats: SourceStats = SourceStats(size_bytes=0, mtime_ns=0)


@dataclass(slots=True, frozen=True)
class _ArrayRecord:
    source_path: Path
    format_id: str
    options: TabularLoadOptions
    object_id: str
    backend_id: str
    shape: tuple[int, ...]
    dtype: str
    size_bytes: int
    warnings: tuple[str, ...]
    stats: SourceStats = SourceStats(size_bytes=0, mtime_ns=0)


_SCAN_CACHE_LIMIT = 64

# Native parquet/duckdb calls need more stack than the UI thread has left when
# graph-scene payload sync runs deep inside QML engine frames (observed access
# violations constructing ParquetWriter/ParquetFile there). Heavy reads and
# conversions therefore dispatch to this worker pool when invoked on the main
# thread; callers block on the result, so synchronous semantics are unchanged.
_io_executor_guard = threading.Lock()
_io_executor: Any = None


def _tabular_io_executor() -> Any:
    global _io_executor
    with _io_executor_guard:
        if _io_executor is None:
            from concurrent.futures import ThreadPoolExecutor

            _io_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tabular-io")
        return _io_executor


class TabularLoaderCacheService:
    resolver_id = TABULAR_CACHE_RESOLVER_ID

    def __init__(
        self,
        *,
        cache_dir: Path | str | os.PathLike[str] | None = None,
        policy: TabularBackendPolicy = DEFAULT_TABULAR_BACKEND_POLICY,
    ) -> None:
        self.policy = policy
        self.cache_dir = Path(cache_dir) if cache_dir is not None else tabular_data_cache_dir()
        self._table_records: dict[str, _TableRecord] = {}
        self._array_records: dict[str, _ArrayRecord] = {}
        self._records_lock = threading.RLock()
        self._scan_cache: dict[str, SourceScanResult] = {}
        self._query_table_cache: dict[str, Any] | None = None
        self._conversion_locks: dict[str, threading.Lock] = {}
        self._conversion_locks_guard = threading.Lock()
        # Until async preview surfaces exist, interactive callers may convert
        # inline on the UI thread; the async preview layer flips this off so
        # large conversions always happen on workers.
        self.ui_thread_conversion_allowed = True

    def scan_source(
        self,
        source_path: Path | str | os.PathLike[str],
        options: TabularLoadOptions | Mapping[str, Any] | None = None,
    ) -> SourceScanResult:
        normalized_options = _coerce_options(options)
        path = self._resolve_path(source_path)
        format_id = detect_format_id(path)
        stats = self._source_stats(path)
        cache_key = json.dumps(
            {
                "path": str(path),
                "mtime_ns": stats.mtime_ns,
                "size": stats.size_bytes,
                "options": normalized_options.to_cache_payload(),
                "policy": self.policy.revision,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._records_lock:
            cached = self._scan_cache.get(cache_key)
        if cached is not None:
            return cached
        scan = self._scan_uncached(path, format_id, normalized_options, stats)
        with self._records_lock:
            if cache_key not in self._scan_cache and len(self._scan_cache) >= _SCAN_CACHE_LIMIT:
                self._scan_cache.pop(next(iter(self._scan_cache)), None)
            self._scan_cache[cache_key] = scan
        return scan

    def _scan_uncached(
        self,
        path: Path,
        format_id: str,
        normalized_options: TabularLoadOptions,
        stats: SourceStats,
    ) -> SourceScanResult:
        if format_id in TEXT_FORMAT_IDS:
            return self._scan_text(path, format_id, normalized_options, stats)
        if format_id in EXCEL_FORMAT_IDS:
            return self._scan_excel(path, format_id, normalized_options, stats)
        if format_id == "parquet":
            return self._scan_parquet(path, normalized_options, stats)
        if format_id == "hdf5":
            return self._scan_hdf5(path, normalized_options, stats)
        if format_id == "npy":
            return self._scan_npy(path, normalized_options, stats)
        if format_id == "npz":
            return self._scan_npz(path, normalized_options, stats)
        raise UnsupportedTabularFormatError(path)

    def open_source(
        self,
        source_path: Path | str | os.PathLike[str],
        options: TabularLoadOptions | Mapping[str, Any] | None = None,
    ) -> TabularDataRef | ArrayDataRef:
        normalized_options = _coerce_options(options)
        scan = self.scan_source(source_path, normalized_options)
        selected = self._resolve_selected_object(scan, normalized_options)
        options_with_selection = normalized_options.with_selected_object(selected.object_id)
        if selected.kind == "table":
            record = self._build_table_record(scan, selected, options_with_selection)
            ref_id = self._ref_id("table", record)
            with self._records_lock:
                existing = self._table_records.get(ref_id)
                if existing is not None and existing.row_count is not None and record.row_count is None:
                    record = existing
                self._table_records[ref_id] = record
            return TabularDataRef(
                ref_id=ref_id,
                resolver_id=self.resolver_id,
                backend_id=record.backend_id,
                source_uri=_path_uri(record.source_path),
                object_id=record.object_id,
                row_count=record.row_count,
                column_count=len(record.columns),
                metadata=self._record_metadata(
                    record.format_id,
                    record.size_bytes,
                    record.warnings,
                    options=record.options,
                ),
            )
        record = self._build_array_record(scan, selected, options_with_selection)
        ref_id = self._ref_id("array", record)
        with self._records_lock:
            self._array_records[ref_id] = record
        return ArrayDataRef(
            ref_id=ref_id,
            resolver_id=self.resolver_id,
            backend_id=record.backend_id,
            source_uri=_path_uri(record.source_path),
            object_id=record.object_id,
            shape=record.shape,
            dtype=record.dtype,
            metadata=self._record_metadata(
                record.format_id,
                record.size_bytes,
                record.warnings,
                options=record.options,
            ),
        )

    def ensure_ref_open(self, ref: TabularDataRef | ArrayDataRef) -> TabularDataRef | ArrayDataRef:
        if isinstance(ref, TabularDataRef):
            return self.ensure_table_ref(ref)
        return self.ensure_array_ref(ref)

    def ensure_table_ref(self, ref: TabularDataRef) -> TabularDataRef:
        with self._records_lock:
            record = self._table_records.get(ref.ref_id)
            if record is not None and self._record_source_is_current(record):
                return ref
        reopened = self.open_source(_source_path_from_ref(ref), _load_options_from_ref(ref))
        if not isinstance(reopened, TabularDataRef):
            raise TypeError("tabular ref reopened as an array source")
        if reopened.ref_id != ref.ref_id:
            with self._records_lock:
                self._table_records[ref.ref_id] = self._table_records[reopened.ref_id]
        return ref

    def ensure_array_ref(self, ref: ArrayDataRef) -> ArrayDataRef:
        with self._records_lock:
            record = self._array_records.get(ref.ref_id)
            if record is not None and self._record_source_is_current(record):
                return ref
        reopened = self.open_source(_source_path_from_ref(ref), _load_options_from_ref(ref))
        if not isinstance(reopened, ArrayDataRef):
            raise TypeError("array ref reopened as a table source")
        if reopened.ref_id != ref.ref_id:
            with self._records_lock:
                self._array_records[ref.ref_id] = self._array_records[reopened.ref_id]
        return ref

    def schema(self, ref: TabularDataRef) -> TabularSchema:
        self.ensure_table_ref(ref)
        record = self._table_record(ref)
        if (
            record.row_count is None
            and (record.format_id in TEXT_FORMAT_IDS or record.format_id in EXCEL_FORMAT_IDS)
            and record.options.uses_managed_cache
        ):
            cached_count = self._cached_parquet_row_count(record.source_path, record.options)
            if cached_count is not None:
                updated = replace(record, row_count=cached_count)
                with self._records_lock:
                    for ref_id, existing in list(self._table_records.items()):
                        if existing is record:
                            self._table_records[ref_id] = updated
                record = updated
        return TabularSchema(
            columns=record.columns,
            row_count=record.row_count,
            metadata=self._record_metadata(
                record.format_id,
                record.size_bytes,
                record.warnings,
                options=record.options,
            ),
        )

    def metadata(self, ref: TabularDataRef | ArrayDataRef) -> Mapping[str, Any]:
        if isinstance(ref, TabularDataRef):
            self.ensure_table_ref(ref)
            record = self._table_record(ref)
            payload = self._record_metadata(
                record.format_id,
                record.size_bytes,
                record.warnings,
                options=record.options,
            )
            payload["row_count"] = record.row_count
            payload["column_count"] = len(record.columns)
            return payload
        self.ensure_array_ref(ref)
        record = self._array_record(ref)
        payload = self._record_metadata(
            record.format_id,
            record.size_bytes,
            record.warnings,
            options=record.options,
        )
        payload["shape"] = list(record.shape)
        payload["dtype"] = record.dtype
        return payload

    def window(self, ref: TabularDataRef, request: TabularWindowRequest) -> TabularDataWindow:
        self.ensure_table_ref(ref)
        record = self._table_record(ref)
        if record.format_id in TEXT_FORMAT_IDS or record.format_id in EXCEL_FORMAT_IDS:
            if record.options.uses_managed_cache:
                entry = self._ensure_record_parquet_cache(ref, record)
                record = self._table_record(ref)
                return self._read_parquet_window(record, request, parquet_path=entry.cache_path)
            if record.format_id in TEXT_FORMAT_IDS:
                return self._read_text_window(record, request)
            return self._read_excel_window(record, request)
        if record.format_id == "parquet":
            return self._read_parquet_window(record, request)
        if record.format_id == "hdf5":
            return self._read_hdf5_table_window(record, request)
        raise UnsupportedTabularFormatError(record.source_path)

    def preview_window(self, ref: TabularDataRef, request: Mapping[str, Any]) -> TabularDataWindow:
        self.ensure_table_ref(ref)
        record = self._table_record(ref)
        request_map = dict(request) if isinstance(request, Mapping) else {}
        row_offset = _query_int(request_map.get("row_offset"), default=0, minimum=0)
        row_limit = _query_int(request_map.get("row_limit"), default=50, minimum=1)
        column_offset = _query_int(request_map.get("column_offset"), default=0, minimum=0)
        column_limit = _query_int(request_map.get("column_limit"), default=50, minimum=1)
        requested_columns = tuple(
            str(name).strip()
            for name in _as_sequence(request_map.get("columns"))
            if str(name).strip()
        )
        all_columns = tuple(column.name for column in record.columns)
        column_window = TabularWindowRequest(
            row_offset=row_offset,
            row_limit=row_limit,
            column_offset=column_offset,
            column_limit=column_limit,
            columns=requested_columns,
        )
        selected_columns = _select_columns(all_columns, column_window)

        predicates = _collect_query_predicates(
            request_map.get("filters"),
            request_map.get("filter"),
            request_map.get("search"),
        )
        sort_directives = _normalize_sort_directives(request_map.get("sort"))

        if selected_columns:
            parquet_path: Path | None = None
            if record.format_id == "parquet":
                parquet_path = record.source_path
            elif (
                record.format_id in TEXT_FORMAT_IDS or record.format_id in EXCEL_FORMAT_IDS
            ) and record.options.uses_managed_cache:
                parquet_path = self._ensure_record_parquet_cache(ref, record).cache_path
                record = self._table_record(ref)
            if parquet_path is not None:
                arrow_window = self._preview_window_arrow(
                    record,
                    parquet_path,
                    selected_columns=selected_columns,
                    all_columns=all_columns,
                    predicates=predicates,
                    sort_directives=sort_directives,
                    row_offset=row_offset,
                    row_limit=row_limit,
                    column_offset=column_offset,
                )
                if arrow_window is not None:
                    return arrow_window

        matched: list[dict[str, Any]] = []
        scanned = 0
        truncated = False
        for source_row in self._iter_all_table_records(record):
            if scanned >= PREVIEW_QUERY_SCAN_ROW_CAP:
                truncated = True
                break
            scanned += 1
            if _row_passes_predicates(source_row, predicates, selected_columns):
                matched.append(source_row)

        for column, descending in reversed(sort_directives):
            matched.sort(
                key=lambda row, _column=column: _query_sort_key(row.get(_column)),
                reverse=descending,
            )

        total_rows = len(matched)
        windowed = matched[row_offset : row_offset + row_limit]
        rows = tuple(
            {column: source_row.get(column) for column in selected_columns}
            for source_row in windowed
        )
        metadata = self._record_metadata(record.format_id, record.size_bytes, record.warnings)
        if truncated:
            metadata["query_scan_truncated"] = True
            metadata["query_scanned_rows"] = scanned
        return TabularDataWindow(
            columns=selected_columns,
            rows=rows,
            row_offset=row_offset,
            column_offset=column_offset,
            total_rows=total_rows,
            total_columns=len(all_columns),
            metadata=metadata,
        )

    def _preview_window_arrow(
        self,
        record: _TableRecord,
        parquet_path: Path,
        *,
        selected_columns: tuple[str, ...],
        all_columns: tuple[str, ...],
        predicates: Sequence["_QueryFilter"],
        sort_directives: tuple[tuple[str, bool], ...],
        row_offset: int,
        row_limit: int,
        column_offset: int,
    ) -> TabularDataWindow | None:
        """Sort/filter/search the cache parquet with pyarrow.compute.

        duckdb was the obvious engine here, but loading it into a process
        that already runs Qt/QML and pyarrow access-violates on Windows
        (duckdb 1.5.2 + pyarrow 24.0 + PyQt6); arrow compute kernels are
        proven safe in-shell and stay within the interactive budgets.
        """

        try:
            pyarrow = importlib.import_module("pyarrow")
            pa_compute = importlib.import_module("pyarrow.compute")
            pq = importlib.import_module("pyarrow.parquet")
        except ModuleNotFoundError:
            return None

        def run_query() -> tuple[int, tuple[dict[str, Any], ...]]:
            needed: list[str] = list(selected_columns)
            for predicate in predicates:
                if predicate.column and predicate.column in all_columns and predicate.column not in needed:
                    needed.append(predicate.column)
            for column, _descending in sort_directives:
                if column in all_columns and column not in needed:
                    needed.append(column)
            cached = self._query_table_for(pq, parquet_path, needed)
            if cached is not None:
                table, text_views = cached
            else:
                table, text_views = pq.read_table(parquet_path, columns=needed), {}

            def full_text_view(column_name: str) -> Any:
                view = text_views.get(column_name)
                if view is None:
                    view = _arrow_text_view(pyarrow, pa_compute, table.column(column_name))
                    text_views[column_name] = view
                return view

            mask = None
            for predicate in predicates:
                predicate_mask = _arrow_predicate_mask(
                    pyarrow, pa_compute, table, predicate, selected_columns, full_text_view
                )
                mask = predicate_mask if mask is None else pa_compute.and_kleene(mask, predicate_mask)
            filtered = table
            if mask is not None:
                filtered = table.filter(pa_compute.fill_null(mask, False))
            total = int(filtered.num_rows)

            applicable_sorts = [
                (column, descending)
                for column, descending in sort_directives
                if column in filtered.column_names
            ]
            if applicable_sorts and total > 1:
                augmented = filtered
                sort_keys: list[tuple[str, str]] = []
                for index, (column, descending) in enumerate(applicable_sorts):
                    field_type = filtered.schema.field(column).type
                    key_names = (column,)
                    if pyarrow.types.is_string(field_type) or pyarrow.types.is_large_string(field_type):
                        text_values = full_text_view(column) if filtered is table else _arrow_text_view(
                            pyarrow, pa_compute, filtered.column(column)
                        )
                        key_names = (
                            f"__sort_kind_{index}",
                            f"__sort_numeric_{index}",
                            f"__sort_text_{index}",
                        )
                        for key_name, key_values in zip(
                            key_names,
                            _arrow_query_sort_columns(pyarrow, pa_compute, filtered.column(column), text_values),
                            strict=True,
                        ):
                            augmented = augmented.append_column(key_name, key_values)
                    sort_keys.extend(
                        (key_name, "descending" if descending else "ascending")
                        for key_name in key_names
                    )
                null_placement = "at_start" if applicable_sorts[0][1] else "at_end"
                indices = pa_compute.sort_indices(
                    augmented, sort_keys=sort_keys, null_placement=null_placement
                )
                # Take only the requested page through the sorted order —
                # materializing the full sorted table costs seconds at
                # gigabyte scale while a page is 50 rows.
                page_indices = indices.slice(row_offset, row_limit if row_limit > 0 else None)
                page = filtered.select(list(selected_columns)).take(page_indices)
            else:
                page = filtered.select(list(selected_columns)).slice(
                    row_offset, row_limit if row_limit > 0 else None
                )
            rows = tuple(_json_safe_mapping(row) for row in page.to_pylist())
            return total, rows

        total_rows, rows = self._run_io(run_query)
        metadata = self._record_metadata(record.format_id, record.size_bytes, record.warnings)
        metadata["query_backend"] = "arrow"
        return TabularDataWindow(
            columns=selected_columns,
            rows=rows,
            row_offset=row_offset,
            column_offset=column_offset,
            total_rows=total_rows,
            total_columns=len(all_columns),
            metadata=metadata,
        )

    # Interactive sort/search re-queries the same parquet repeatedly while the
    # user types; keep ONE table (plus lazily lowered text views) in memory so
    # repeat queries skip the parquet read and the per-query string casts.
    _QUERY_TABLE_CACHE_MAX_BYTES = 1_536 * 1024 * 1024

    def _query_table_for(
        self,
        pq: Any,
        parquet_path: Path,
        needed: Sequence[str],
    ) -> tuple[Any, dict[str, Any]] | None:
        try:
            stat = parquet_path.stat()
        except OSError:
            return None
        stamp = (str(parquet_path), int(stat.st_mtime_ns), int(stat.st_size))
        with self._records_lock:
            entry = self._query_table_cache
            if (
                entry is not None
                and entry["stamp"] == stamp
                and set(needed) <= set(entry["table"].column_names)
            ):
                return entry["table"], entry["text_views"]
        estimate = self._query_table_cache_size_estimate(pq, parquet_path, needed)
        if estimate is not None and estimate > self._QUERY_TABLE_CACHE_MAX_BYTES:
            return None
        table = pq.read_table(parquet_path, columns=list(needed))
        if int(getattr(table, "nbytes", 0)) > self._QUERY_TABLE_CACHE_MAX_BYTES:
            return None
        entry = {"stamp": stamp, "table": table, "text_views": {}}
        with self._records_lock:
            self._query_table_cache = entry
        return table, entry["text_views"]

    def _query_table_cache_size_estimate(
        self,
        pq: Any,
        parquet_path: Path,
        needed: Sequence[str],
    ) -> int | None:
        try:
            parquet_file = pq.ParquetFile(parquet_path)
            metadata = parquet_file.metadata
            schema_names = list(getattr(metadata.schema, "names", []) or [])
            needed_set = set(needed)
            needed_indexes = {
                index for index, name in enumerate(schema_names) if name in needed_set
            }
            if not needed_indexes:
                return 0
            total = 0
            for row_group_index in range(int(metadata.num_row_groups)):
                row_group = metadata.row_group(row_group_index)
                for column_index in needed_indexes:
                    column = row_group.column(column_index)
                    total += int(getattr(column, "total_uncompressed_size", 0) or 0)
            return total or None
        except Exception:  # noqa: BLE001 - best-effort guard before cache read
            return None

    def _iter_all_table_records(self, record: _TableRecord) -> Iterable[dict[str, Any]]:
        if record.format_id in TEXT_FORMAT_IDS:
            delimiter = self._resolve_text_delimiter(record.source_path, record.format_id, record.options)
            columns = tuple(column.name for column in record.columns)
            yield from self._iter_text_records(record.source_path, record.options, delimiter, columns)
            return
        if record.format_id in EXCEL_FORMAT_IDS:
            openpyxl = _import_optional("openpyxl", format_id=record.format_id, purpose="workbook query preview")
            workbook = openpyxl.load_workbook(record.source_path, read_only=True, data_only=True)
            try:
                worksheet = workbook[record.object_id]
                columns = tuple(column.name for column in record.columns)
                yield from _worksheet_records(worksheet, record.options, columns)
            finally:
                workbook.close()
            return
        if record.format_id == "parquet":
            pq = _import_optional("pyarrow.parquet", format_id="parquet", purpose="Parquet query preview")
            columns = [column.name for column in record.columns]
            parquet_file = pq.ParquetFile(record.source_path)
            for batch in parquet_file.iter_batches(batch_size=4096, columns=columns):
                for row in batch.to_pylist():
                    yield _json_safe_mapping(row)
            return
        if record.format_id == "hdf5":
            h5py = _import_optional("h5py", format_id="hdf5", purpose="HDF5 query preview")
            columns = tuple(column.name for column in record.columns)
            with h5py.File(record.source_path, "r") as handle:
                dataset = handle[record.object_id]
                total = int(dataset.shape[0]) if dataset.shape else 0
                step = 4096
                for start in range(0, total, step):
                    chunk = dataset[start : min(start + step, total)]
                    for item in chunk:
                        yield {column: _json_safe_value(item[column]) for column in columns}
            return
        raise UnsupportedTabularFormatError(record.source_path)

    def rows(self, ref: TabularDataRef, request: TabularWindowRequest) -> Sequence[Mapping[str, Any]]:
        return self.window(ref, request).rows

    def window_columns(self, ref: TabularDataRef, request: TabularWindowRequest) -> tuple[str, ...]:
        self.ensure_table_ref(ref)
        record = self._table_record(ref)
        columns = tuple(column.name for column in record.columns)
        return _select_columns(columns, request)

    def iter_window_rows(
        self,
        ref: TabularDataRef,
        request: TabularWindowRequest,
    ) -> Iterable[Mapping[str, Any]]:
        self.ensure_table_ref(ref)
        record = self._table_record(ref)
        selected_columns = self.window_columns(ref, request)
        if (
            record.format_id in TEXT_FORMAT_IDS or record.format_id in EXCEL_FORMAT_IDS
        ) and record.options.uses_managed_cache:
            parquet_path = self._ensure_record_parquet_cache(ref, record).cache_path
            record = self._table_record(ref)
            batch_options = TabularArrowBatchOptions(
                row_limit=request.row_limit if request.row_limit > 0 else (record.row_count or 2_147_483_647),
                batch_size=4096,
                row_offset=request.row_offset,
                columns=selected_columns,
            )
            for batch in self._iter_parquet_batches(record, batch_options, parquet_path):
                for row in batch.to_pylist():
                    yield _json_safe_mapping(row)
            return
        emitted = 0
        for row_index, source_row in enumerate(self._iter_all_table_records(record)):
            if row_index < request.row_offset:
                continue
            yield {column: source_row.get(column) for column in selected_columns}
            emitted += 1
            if request.row_limit > 0 and emitted >= request.row_limit:
                return

    def arrow_batches(self, ref: TabularDataRef, options: TabularArrowBatchOptions) -> Iterable[Any]:
        self.ensure_table_ref(ref)
        record = self._table_record(ref)
        parquet_path: Path | None = None
        if record.format_id == "parquet":
            parquet_path = record.source_path
        elif (
            record.format_id in TEXT_FORMAT_IDS or record.format_id in EXCEL_FORMAT_IDS
        ) and record.options.uses_managed_cache:
            parquet_path = self._ensure_record_parquet_cache(ref, record).cache_path
            record = self._table_record(ref)
        if parquet_path is not None:
            yield from self._iter_parquet_batches_safely(record, options, parquet_path)
            return
        request = TabularWindowRequest(
            row_offset=options.row_offset,
            row_limit=options.row_limit,
            column_limit=len(options.columns) if options.columns else len(record.columns),
            columns=options.columns,
        )
        rows = list(self.rows(ref, request))
        if rows:
            yield rows

    def _iter_parquet_batches(
        self,
        record: _TableRecord,
        options: TabularArrowBatchOptions,
        parquet_path: Path,
    ) -> Iterable[Any]:
        pq = _import_optional("pyarrow.parquet", format_id="parquet", purpose="Arrow batch reads")
        columns = tuple(options.columns) if options.columns else tuple(column.name for column in record.columns)
        remaining_skip = options.row_offset
        remaining_take = options.row_limit
        with pq.ParquetFile(parquet_path) as parquet_file:
            for batch in parquet_file.iter_batches(batch_size=options.batch_size, columns=list(columns)):
                if remaining_skip >= batch.num_rows:
                    remaining_skip -= batch.num_rows
                    continue
                if remaining_skip:
                    batch = batch.slice(remaining_skip)
                    remaining_skip = 0
                if batch.num_rows > remaining_take:
                    batch = batch.slice(0, remaining_take)
                remaining_take -= batch.num_rows
                yield batch
                if remaining_take <= 0:
                    return

    def _iter_parquet_batches_safely(
        self,
        record: _TableRecord,
        options: TabularArrowBatchOptions,
        parquet_path: Path,
    ) -> Iterable[Any]:
        """Stream parquet batches while keeping native reads off the UI stack."""

        if threading.current_thread() is not threading.main_thread():
            yield from self._iter_parquet_batches(record, options, parquet_path)
            return

        sentinel = object()
        stop = threading.Event()
        batches: queue.Queue[Any] = queue.Queue(maxsize=4)

        def put(item: Any) -> None:
            while not stop.is_set():
                try:
                    batches.put(item, timeout=0.1)
                    return
                except queue.Full:
                    continue

        def produce() -> None:
            try:
                for batch in self._iter_parquet_batches(record, options, parquet_path):
                    put(batch)
                    if stop.is_set():
                        return
            except Exception as exc:  # noqa: BLE001 - reraised on the caller thread
                put(exc)
            finally:
                put(sentinel)

        future = _tabular_io_executor().submit(produce)
        try:
            while True:
                item = batches.get()
                if item is sentinel:
                    future.result()
                    return
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            stop.set()

    def to_pandas(self, ref: TabularDataRef, options: TabularMaterializationOptions) -> Any:
        self.ensure_table_ref(ref)
        record = self._table_record(ref)
        self._enforce_table_materialization_gate(record, options)
        pandas = _import_optional("pandas", format_id=record.format_id, purpose="pandas materialization")
        rows = self.window(ref, _window_request_from_materialization(record, options)).rows
        return pandas.DataFrame(list(rows))

    def to_polars(self, ref: TabularDataRef, options: TabularMaterializationOptions) -> Any:
        self.ensure_table_ref(ref)
        record = self._table_record(ref)
        self._enforce_table_materialization_gate(record, options)
        polars = _import_optional("polars", format_id=record.format_id, purpose="Polars materialization")
        rows = self.window(ref, _window_request_from_materialization(record, options)).rows
        return polars.DataFrame(list(rows))

    def to_numpy(self, ref: TabularDataRef | ArrayDataRef, options: TabularMaterializationOptions | ArrayMaterializationOptions) -> Any:
        numpy = _import_optional("numpy", format_id="numpy", purpose="NumPy materialization")
        if isinstance(ref, TabularDataRef):
            if not isinstance(options, TabularMaterializationOptions):
                raise TypeError("tabular refs require TabularMaterializationOptions")
            self.ensure_table_ref(ref)
            record = self._table_record(ref)
            self._enforce_table_materialization_gate(record, options)
            rows = self.window(ref, _window_request_from_materialization(record, options)).rows
            return numpy.array([list(row.values()) for row in rows], dtype=object)
        if not isinstance(options, ArrayMaterializationOptions):
            raise TypeError("array refs require ArrayMaterializationOptions")
        self.ensure_array_ref(ref)
        record = self._array_record(ref)
        self._enforce_array_materialization_gate(record, options)
        return self._read_array_materialized(record, options)

    def slice_2d(self, ref: ArrayDataRef, request: ArraySlice2DRequest) -> ArraySlice2D:
        self.ensure_array_ref(ref)
        record = self._array_record(ref)
        values = self._read_array_slice(record, request)
        return ArraySlice2D(
            values=values,
            row_offset=request.row_offset,
            column_offset=request.column_offset,
            shape=record.shape,
            dtype=record.dtype,
            metadata=self._record_metadata(record.format_id, record.size_bytes, record.warnings),
        )

    def parquet_cache_key(
        self,
        source_path: Path | str | os.PathLike[str],
        options: TabularLoadOptions | Mapping[str, Any] | None = None,
        *,
        selected_object: str = "",
    ) -> ParquetCacheKey:
        normalized_options = _coerce_options(options)
        path = self._resolve_path(source_path)
        stats = self._source_stats(path)
        selected = selected_object.strip() or normalized_options.selected_object
        payload = {
            "source_path": str(path),
            "source_mtime_ns": stats.mtime_ns,
            "source_size_bytes": stats.size_bytes,
            "parser_options": normalized_options.to_cache_payload(),
            "selected_object": selected,
            "backend_policy_revision": self.policy.revision,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return ParquetCacheKey(hashlib.sha256(raw).hexdigest(), payload)

    def parquet_cache_paths(self, key: str) -> tuple[Path, Path]:
        safe_key = str(key).strip().lower()
        if not safe_key:
            raise ValueError("cache key must be non-empty")
        bucket = self.cache_dir / safe_key[:2]
        return bucket / f"{safe_key}.parquet", bucket / f"{safe_key}.json"

    def ensure_parquet_cache(
        self,
        source_path: Path | str | os.PathLike[str],
        options: TabularLoadOptions | Mapping[str, Any] | None = None,
        *,
        selected_object: str = "",
    ) -> ParquetCacheEntry:
        normalized_options = _coerce_options(options)
        cache_key = self.parquet_cache_key(
            source_path,
            normalized_options,
            selected_object=selected_object,
        )
        cache_path, metadata_path = self.parquet_cache_paths(cache_key.key)
        if cache_path.is_file() and metadata_path.is_file():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            return ParquetCacheEntry(cache_key.key, cache_path, metadata_path, metadata)
        with self._conversion_lock(cache_key.key):
            if cache_path.is_file() and metadata_path.is_file():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                return ParquetCacheEntry(cache_key.key, cache_path, metadata_path, metadata)
            _import_optional("pyarrow.parquet", format_id="parquet_cache", purpose="managed Parquet cache")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = cache_path.with_name(f"{cache_path.name}.tmp-{os.getpid()}-{threading.get_ident()}")
            try:
                self._run_io(
                    self._write_parquet_cache,
                    self._resolve_path(source_path),
                    normalized_options.with_selected_object(selected_object or normalized_options.selected_object),
                    temp_path,
                )
                os.replace(temp_path, cache_path)
            finally:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass
            metadata = {
                "kind": "tabular_data_parquet_cache",
                "key": cache_key.key,
                "payload": cache_key.payload,
                "cache_path": str(cache_path),
                "backend_policy_revision": self.policy.revision,
                "row_count": self._parquet_row_count(cache_path),
            }
            metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        self.enforce_cache_size_limit(preserve_paths=(cache_path,))
        return ParquetCacheEntry(cache_key.key, cache_path, metadata_path, metadata)

    @staticmethod
    def _run_io(fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Run heavy native I/O off the main thread (see _tabular_io_executor)."""

        if threading.current_thread() is threading.main_thread():
            return _tabular_io_executor().submit(fn, *args, **kwargs).result()
        return fn(*args, **kwargs)

    def _record_source_is_current(self, record: _TableRecord | _ArrayRecord) -> bool:
        try:
            return self._source_stats(record.source_path) == record.stats
        except OSError:
            return False

    def _conversion_lock(self, cache_key: str) -> threading.Lock:
        with self._conversion_locks_guard:
            lock = self._conversion_locks.get(cache_key)
            if lock is None:
                lock = threading.Lock()
                self._conversion_locks[cache_key] = lock
            return lock

    def _parquet_row_count(self, parquet_path: Path) -> int | None:
        def read_count() -> int | None:
            try:
                pq = _import_optional("pyarrow.parquet", format_id="parquet_cache", purpose="managed Parquet cache")
                with pq.ParquetFile(parquet_path) as parquet_file:
                    return int(parquet_file.metadata.num_rows)
            except Exception:  # noqa: BLE001 - row counts are best-effort metadata
                return None

        return self._run_io(read_count)

    def _ensure_record_parquet_cache(self, ref: TabularDataRef, record: _TableRecord) -> ParquetCacheEntry:
        cache_key = self.parquet_cache_key(
            record.source_path,
            record.options,
            selected_object=record.object_id,
        )
        cache_path, metadata_path = self.parquet_cache_paths(cache_key.key)
        if not (cache_path.is_file() and metadata_path.is_file()) and not self._conversion_allowed(record):
            raise TabularCacheNotReadyError(source_path=record.source_path, size_bytes=record.size_bytes)
        entry = self.ensure_parquet_cache(
            record.source_path,
            record.options,
            selected_object=record.object_id,
        )
        self._backfill_record_from_cache(ref, record, entry)
        return entry

    def _conversion_allowed(self, record: _TableRecord) -> bool:
        if self.ui_thread_conversion_allowed:
            return True
        if record.size_bytes <= TABULAR_DATA_INLINE_CONVERSION_BYTES:
            return True
        return threading.current_thread() is not threading.main_thread()

    def _backfill_record_from_cache(
        self,
        ref: TabularDataRef,
        record: _TableRecord,
        entry: ParquetCacheEntry,
    ) -> None:
        """Backfill row count and typed column dtypes once the cache exists."""

        needs_row_count = record.row_count is None
        needs_dtypes = any(not column.dtype for column in record.columns)
        if not needs_row_count and not needs_dtypes:
            return

        def read_metadata() -> tuple[int, dict[str, str]] | None:
            try:
                pq = _import_optional("pyarrow.parquet", format_id="parquet_cache", purpose="managed Parquet cache")
                with pq.ParquetFile(entry.cache_path) as parquet_file:
                    return (
                        int(parquet_file.metadata.num_rows),
                        {field.name: str(field.type) for field in parquet_file.schema_arrow},
                    )
            except Exception:  # noqa: BLE001 - backfill is best-effort
                return None

        metadata = self._run_io(read_metadata)
        if metadata is None:
            return
        row_count, arrow_types = metadata
        columns = tuple(
            TabularColumn(column.name, column.dtype or arrow_types.get(column.name, ""), column.nullable)
            for column in record.columns
        )
        updated = replace(record, row_count=row_count, columns=columns)
        with self._records_lock:
            for ref_id, existing in list(self._table_records.items()):
                if existing is record:
                    self._table_records[ref_id] = updated

    def _scan_text(
        self,
        path: Path,
        format_id: str,
        options: TabularLoadOptions,
        stats: SourceStats,
    ) -> SourceScanResult:
        delimiter = self._resolve_text_delimiter(path, format_id, options)
        columns = self._text_columns(path, options, delimiter)
        # Row counts are never computed by scanning the source: they backfill
        # from the managed parquet cache metadata once it exists.
        item = SelectableObject(
            object_id="table",
            display_name=path.name,
            kind="table",
            row_count=self._cached_parquet_row_count(path, options.with_selected_object("table")),
            column_count=len(columns),
            metadata={"delimiter": delimiter, "encoding": options.encoding},
        )
        return self._single_object_scan(path, format_id, item, stats)

    def _cached_parquet_row_count(
        self,
        path: Path,
        options: TabularLoadOptions,
    ) -> int | None:
        if not options.uses_managed_cache:
            return None
        try:
            cache_key = self.parquet_cache_key(path, options)
            _cache_path, metadata_path = self.parquet_cache_paths(cache_key.key)
            if not metadata_path.is_file():
                return None
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        row_count = metadata.get("row_count")
        return int(row_count) if isinstance(row_count, int) else None

    def _scan_excel(
        self,
        path: Path,
        format_id: str,
        options: TabularLoadOptions,
        stats: SourceStats,
    ) -> SourceScanResult:
        openpyxl = _import_optional("openpyxl", format_id=format_id, purpose="workbook sheet scanning")
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            objects = tuple(
                SelectableObject(
                    object_id=sheet_name,
                    display_name=sheet_name,
                    kind="table",
                    row_count=_excel_data_row_count(workbook[sheet_name], options),
                    column_count=int(workbook[sheet_name].max_column or 0),
                )
                for sheet_name in workbook.sheetnames
            )
        finally:
            workbook.close()
        return self._object_scan(path, format_id, objects, options, stats)

    def _scan_parquet(
        self,
        path: Path,
        options: TabularLoadOptions,
        stats: SourceStats,
    ) -> SourceScanResult:
        pq = _import_optional("pyarrow.parquet", format_id="parquet", purpose="Parquet metadata scanning")

        def read_metadata() -> tuple[int, int]:
            with pq.ParquetFile(path) as parquet_file:
                return int(parquet_file.metadata.num_rows), len(parquet_file.schema.names)

        row_count, column_count = self._run_io(read_metadata)
        item = SelectableObject(
            object_id="table",
            display_name=path.name,
            kind="table",
            row_count=row_count,
            column_count=column_count,
        )
        return self._object_scan(path, "parquet", (item,), options, stats)

    def _scan_hdf5(
        self,
        path: Path,
        options: TabularLoadOptions,
        stats: SourceStats,
    ) -> SourceScanResult:
        h5py = _import_optional("h5py", format_id="hdf5", purpose="HDF5 dataset scanning")
        objects: list[SelectableObject] = []
        with h5py.File(path, "r") as handle:
            def visitor(name: str, item: Any) -> None:
                if not isinstance(item, h5py.Dataset):
                    return
                shape = tuple(int(value) for value in (item.shape or ()))
                dtype = str(item.dtype)
                if item.dtype.names:
                    objects.append(
                        SelectableObject(
                            object_id=name,
                            display_name=name,
                            kind="table",
                            row_count=shape[0] if shape else None,
                            column_count=len(item.dtype.names),
                            dtype=dtype,
                        )
                    )
                    return
                objects.append(
                    SelectableObject(
                        object_id=name,
                        display_name=name,
                        kind="array",
                        shape=shape,
                        dtype=dtype,
                    )
                )

            handle.visititems(visitor)
        return self._object_scan(path, "hdf5", tuple(objects), options, stats)

    def _scan_npy(
        self,
        path: Path,
        options: TabularLoadOptions,
        stats: SourceStats,
    ) -> SourceScanResult:
        numpy = _import_optional("numpy", format_id="npy", purpose="NPY metadata scanning")
        array = numpy.load(path, mmap_mode="r", allow_pickle=False)
        item = SelectableObject(
            object_id="array",
            display_name=path.name,
            kind="array",
            shape=tuple(int(value) for value in array.shape),
            dtype=str(array.dtype),
            metadata={"mmap": True},
        )
        return self._object_scan(path, "npy", (item,), options, stats)

    def _scan_npz(
        self,
        path: Path,
        options: TabularLoadOptions,
        stats: SourceStats,
    ) -> SourceScanResult:
        numpy = _import_optional("numpy", format_id="npz", purpose="NPZ archive scanning")
        objects: list[SelectableObject] = []
        with numpy.load(path, allow_pickle=False) as archive:
            for key in archive.files:
                if stats.size_bytes > self.policy.large_warning_bytes:
                    objects.append(
                        SelectableObject(
                            object_id=key,
                            display_name=key,
                            kind="array",
                            metadata={"archive_only": True},
                        )
                    )
                    continue
                array = archive[key]
                objects.append(
                    SelectableObject(
                        object_id=key,
                        display_name=key,
                        kind="array",
                        shape=tuple(int(value) for value in array.shape),
                        dtype=str(array.dtype),
                        metadata={"archive_only": True},
                    )
                )
        return self._object_scan(path, "npz", tuple(objects), options, stats)

    def _object_scan(
        self,
        path: Path,
        format_id: str,
        objects: tuple[SelectableObject, ...],
        options: TabularLoadOptions,
        stats: SourceStats,
    ) -> SourceScanResult:
        usable = tuple(objects)
        selected = ""
        requires_selection = False
        if options.selected_object:
            selected = options.selected_object
        elif len(usable) == 1:
            selected = usable[0].object_id
        elif len(usable) > 1:
            requires_selection = True
        return SourceScanResult(
            source_path=path,
            format_id=format_id,
            objects=usable,
            selected_object_id=selected,
            requires_selection=requires_selection,
            size_bytes=stats.size_bytes,
            size_class=self.policy.classify_size(stats.size_bytes),
            warnings=self.policy.warnings_for_size(stats.size_bytes),
        )

    def _single_object_scan(
        self,
        path: Path,
        format_id: str,
        item: SelectableObject,
        stats: SourceStats,
    ) -> SourceScanResult:
        return SourceScanResult(
            source_path=path,
            format_id=format_id,
            objects=(item,),
            selected_object_id=item.object_id,
            requires_selection=False,
            size_bytes=stats.size_bytes,
            size_class=self.policy.classify_size(stats.size_bytes),
            warnings=self.policy.warnings_for_size(stats.size_bytes),
        )

    def _resolve_selected_object(
        self,
        scan: SourceScanResult,
        options: TabularLoadOptions,
    ) -> SelectableObject:
        selected_object_id = options.selected_object or scan.selected_object_id
        if scan.requires_selection and not selected_object_id:
            raise SelectionRequiredError(format_id=scan.format_id, choices=scan.objects)
        for item in scan.objects:
            if item.object_id == selected_object_id:
                if scan.format_id == "npz" and scan.size_bytes > self.policy.large_warning_bytes and not options.allow_npz_archive_preview:
                    raise LargeDataMaterializationError(
                        "Large NPZ archives are treated as import/export archives; preview requires explicit opt-in.",
                        size_bytes=scan.size_bytes,
                    )
                return item
        raise SelectionRequiredError(format_id=scan.format_id, choices=scan.objects)

    def _build_table_record(
        self,
        scan: SourceScanResult,
        selected: SelectableObject,
        options: TabularLoadOptions,
    ) -> _TableRecord:
        if scan.format_id in TEXT_FORMAT_IDS:
            delimiter = self._resolve_text_delimiter(scan.source_path, scan.format_id, options)
            columns = self._tabular_columns(self._text_columns(scan.source_path, options, delimiter), options)
            row_count = selected.row_count
        elif scan.format_id in EXCEL_FORMAT_IDS:
            columns, row_count = self._excel_columns(scan.source_path, selected.object_id, options)
        elif scan.format_id == "parquet":
            columns, row_count = self._parquet_columns(scan.source_path)
        elif scan.format_id == "hdf5":
            columns, row_count = self._hdf5_table_columns(scan.source_path, selected.object_id)
        else:
            raise UnsupportedTabularFormatError(scan.source_path)
        return _TableRecord(
            source_path=scan.source_path,
            format_id=scan.format_id,
            options=options,
            object_id=selected.object_id,
            backend_id=self.policy.choose_table_backend(scan.format_id, scan.size_bytes),
            columns=columns,
            row_count=row_count,
            size_bytes=scan.size_bytes,
            warnings=scan.warnings,
            stats=self._source_stats(scan.source_path),
        )

    def _build_array_record(
        self,
        scan: SourceScanResult,
        selected: SelectableObject,
        options: TabularLoadOptions,
    ) -> _ArrayRecord:
        shape = selected.shape
        dtype = selected.dtype
        if scan.format_id == "npz" and not shape:
            numpy = _import_optional("numpy", format_id="npz", purpose="NPZ selected array metadata")
            with numpy.load(scan.source_path, allow_pickle=False) as archive:
                array = archive[selected.object_id]
                shape = tuple(int(value) for value in array.shape)
                dtype = str(array.dtype)
        return _ArrayRecord(
            source_path=scan.source_path,
            format_id=scan.format_id,
            options=options,
            object_id=selected.object_id,
            backend_id=self.policy.choose_array_backend(scan.format_id, scan.size_bytes),
            shape=tuple(int(value) for value in shape),
            dtype=str(dtype),
            size_bytes=scan.size_bytes,
            warnings=scan.warnings,
            stats=self._source_stats(scan.source_path),
        )

    def _read_text_window(self, record: _TableRecord, request: TabularWindowRequest) -> TabularDataWindow:
        delimiter = self._resolve_text_delimiter(record.source_path, record.format_id, record.options)
        columns = tuple(column.name for column in record.columns)
        selected_columns = _select_columns(columns, request)
        rows: list[dict[str, Any]] = []
        for row_index, row in enumerate(self._iter_text_records(record.source_path, record.options, delimiter, columns)):
            if row_index < request.row_offset:
                continue
            rows.append({column: row.get(column) for column in selected_columns})
            if request.row_limit > 0 and len(rows) >= request.row_limit:
                break
        return TabularDataWindow(
            columns=selected_columns,
            rows=tuple(rows),
            row_offset=request.row_offset,
            column_offset=request.column_offset,
            total_rows=record.row_count,
            total_columns=len(columns),
            metadata=self._record_metadata(record.format_id, record.size_bytes, record.warnings),
        )

    def _read_excel_window(self, record: _TableRecord, request: TabularWindowRequest) -> TabularDataWindow:
        openpyxl = _import_optional("openpyxl", format_id=record.format_id, purpose="workbook preview")
        workbook = openpyxl.load_workbook(record.source_path, read_only=True, data_only=True)
        try:
            worksheet = workbook[record.object_id]
            columns = tuple(column.name for column in record.columns)
            selected_columns = _select_columns(columns, request)
            rows: list[dict[str, Any]] = []
            for row_index, row in enumerate(_worksheet_records(worksheet, record.options, columns)):
                if row_index < request.row_offset:
                    continue
                rows.append({column: row.get(column) for column in selected_columns})
                if request.row_limit > 0 and len(rows) >= request.row_limit:
                    break
        finally:
            workbook.close()
        return TabularDataWindow(
            columns=selected_columns,
            rows=tuple(rows),
            row_offset=request.row_offset,
            column_offset=request.column_offset,
            total_rows=record.row_count,
            total_columns=len(columns),
            metadata=self._record_metadata(record.format_id, record.size_bytes, record.warnings),
        )

    def _read_parquet_window(
        self,
        record: _TableRecord,
        request: TabularWindowRequest,
        *,
        parquet_path: Path | None = None,
    ) -> TabularDataWindow:
        return self._run_io(self._read_parquet_window_impl, record, request, parquet_path=parquet_path)

    def _read_parquet_window_impl(
        self,
        record: _TableRecord,
        request: TabularWindowRequest,
        *,
        parquet_path: Path | None = None,
    ) -> TabularDataWindow:
        pq = _import_optional("pyarrow.parquet", format_id="parquet", purpose="bounded Parquet preview")
        columns = tuple(column.name for column in record.columns)
        selected_columns = _select_columns(columns, request)
        rows: list[dict[str, Any]] = []
        remaining_skip = request.row_offset
        remaining_take = request.row_limit
        with pq.ParquetFile(parquet_path or record.source_path) as parquet_file:
            row_groups = self._row_groups_for_window(parquet_file, request)
            if row_groups is not None:
                skipped_rows, group_indexes = row_groups
                remaining_skip -= skipped_rows
                batches = parquet_file.iter_batches(
                    batch_size=max(request.row_limit, 4096) if request.row_limit > 0 else 4096,
                    columns=list(selected_columns),
                    row_groups=group_indexes,
                )
            else:
                batches = parquet_file.iter_batches(
                    batch_size=max(request.row_limit, 4096) if request.row_limit > 0 else 4096,
                    columns=list(selected_columns),
                )
            for batch in batches:
                if remaining_skip >= batch.num_rows:
                    remaining_skip -= batch.num_rows
                    continue
                if remaining_skip:
                    batch = batch.slice(remaining_skip)
                    remaining_skip = 0
                if remaining_take > 0 and batch.num_rows > remaining_take:
                    batch = batch.slice(0, remaining_take)
                rows.extend(_json_safe_mapping(row) for row in batch.to_pylist())
                if remaining_take > 0:
                    remaining_take -= batch.num_rows
                if request.row_limit > 0 and len(rows) >= request.row_limit:
                    break
        return TabularDataWindow(
            columns=selected_columns,
            rows=tuple(rows),
            row_offset=request.row_offset,
            column_offset=request.column_offset,
            total_rows=record.row_count,
            total_columns=len(columns),
            metadata=self._record_metadata(record.format_id, record.size_bytes, record.warnings),
        )

    @staticmethod
    def _row_groups_for_window(
        parquet_file: Any,
        request: TabularWindowRequest,
    ) -> tuple[int, list[int]] | None:
        """Pick the row groups covering the requested window so deep pages are
        O(page) instead of O(offset). Returns (rows before the first selected
        group, group indexes) or None when the whole file must stream."""

        if request.row_limit <= 0:
            return None
        try:
            metadata = parquet_file.metadata
            group_count = int(metadata.num_row_groups)
        except Exception:  # noqa: BLE001 - metadata access is best-effort
            return None
        if group_count <= 1:
            return None
        start = request.row_offset
        stop = request.row_offset + request.row_limit
        cursor = 0
        skipped = 0
        selected: list[int] = []
        for index in range(group_count):
            group_rows = int(metadata.row_group(index).num_rows)
            group_start = cursor
            group_stop = cursor + group_rows
            cursor = group_stop
            if group_stop <= start:
                skipped += group_rows
                continue
            if group_start >= stop:
                break
            selected.append(index)
        if not selected:
            return 0, []
        return skipped, selected

    def _read_hdf5_table_window(self, record: _TableRecord, request: TabularWindowRequest) -> TabularDataWindow:
        h5py = _import_optional("h5py", format_id="hdf5", purpose="bounded HDF5 table preview")
        columns = tuple(column.name for column in record.columns)
        selected_columns = _select_columns(columns, request)
        rows: list[dict[str, Any]] = []
        with h5py.File(record.source_path, "r") as handle:
            dataset = handle[record.object_id]
            stop = (
                int(dataset.shape[0])
                if request.row_limit == 0
                else min(request.row_offset + request.row_limit, dataset.shape[0])
            )
            values = dataset[request.row_offset:stop]
            for item in values:
                rows.append({column: _json_safe_value(item[column]) for column in selected_columns})
        return TabularDataWindow(
            columns=selected_columns,
            rows=tuple(rows),
            row_offset=request.row_offset,
            column_offset=request.column_offset,
            total_rows=record.row_count,
            total_columns=len(columns),
            metadata=self._record_metadata(record.format_id, record.size_bytes, record.warnings),
        )

    def _read_array_slice(self, record: _ArrayRecord, request: ArraySlice2DRequest) -> tuple[tuple[Any, ...], ...]:
        array = self._open_array(record)
        values = _slice_array_2d(array, request)
        return _array_values_to_rows(values)

    def _read_array_materialized(self, record: _ArrayRecord, options: ArrayMaterializationOptions) -> Any:
        array = self._open_array(record)
        if options.slices:
            slices = tuple(slice(offset, offset + limit) for offset, limit in options.slices)
            return array[slices]
        if options.max_elements is not None:
            return array.reshape(-1)[: options.max_elements]
        return array[:]

    def _open_array(self, record: _ArrayRecord) -> Any:
        numpy = _import_optional("numpy", format_id=record.format_id, purpose="array preview")
        if record.format_id == "npy":
            return numpy.load(record.source_path, mmap_mode="r", allow_pickle=False)
        if record.format_id == "npz":
            if record.size_bytes > self.policy.large_warning_bytes and not record.options.allow_npz_archive_preview:
                raise LargeDataMaterializationError(
                    "Large NPZ archives require explicit preview opt-in.",
                    size_bytes=record.size_bytes,
                )
            archive = numpy.load(record.source_path, allow_pickle=False)
            return archive[record.object_id]
        if record.format_id == "hdf5":
            h5py = _import_optional("h5py", format_id="hdf5", purpose="HDF5 array preview")
            handle = h5py.File(record.source_path, "r")
            return _Hdf5ArrayHandle(handle, record.object_id)
        raise UnsupportedTabularFormatError(record.source_path)

    def _write_parquet_cache(self, source_path: Path, options: TabularLoadOptions, cache_path: Path) -> None:
        format_id = detect_format_id(source_path)
        if format_id == "parquet":
            _copy_file(source_path, cache_path)
            return
        if format_id in TEXT_FORMAT_IDS:
            self._write_text_parquet_cache(source_path, format_id, options, cache_path)
            return
        if format_id in EXCEL_FORMAT_IDS:
            self._write_excel_parquet_cache(source_path, format_id, options, cache_path)
            return
        raise UnsupportedTabularFormatError(source_path)

    def _write_text_parquet_cache(
        self,
        source_path: Path,
        format_id: str,
        options: TabularLoadOptions,
        cache_path: Path,
    ) -> None:
        delimiter = self._resolve_text_delimiter(source_path, format_id, options)
        columns = self._text_columns(source_path, options, delimiter)
        try:
            self._write_text_parquet_cache_arrow(source_path, options, cache_path, delimiter, columns)
        except MissingTabularDependencyError:
            raise
        except Exception:  # noqa: BLE001 - exotic quoting/encodings fall back to the python csv reader
            if cache_path.exists():
                try:
                    cache_path.unlink()
                except OSError:
                    pass
            self._write_text_parquet_cache_python(source_path, options, cache_path, delimiter, columns)

    # Block size for the chunked CSV-to-parquet conversion. Each block parses
    # independently via pyarrow.csv.read_csv, so peak memory stays bounded for
    # multi-gigabyte sources while parsing runs at arrow speed.
    _ARROW_CSV_BLOCK_BYTES = 32 * 1024 * 1024

    # Chunking splits the byte stream on b"\n", which is only correct for
    # encodings where that byte unambiguously means newline.
    _NEWLINE_SAFE_ENCODINGS = frozenset(
        {"utf-8", "utf8", "utf-8-sig", "ascii", "latin-1", "latin1", "iso-8859-1", "cp1252"}
    )

    def _write_text_parquet_cache_arrow(
        self,
        source_path: Path,
        options: TabularLoadOptions,
        cache_path: Path,
        delimiter: str,
        columns: tuple[str, ...],
    ) -> None:
        """Convert text sources to parquet via chunked pyarrow.csv.read_csv.

        Deliberately NOT pyarrow.csv.open_csv: the streaming reader's
        background readahead thread corrupts PyQt6/QML processes on Windows
        (observed access violations in later QML work with pyarrow 24.0).
        Instead, line-aligned byte blocks are parsed independently with the
        non-streaming reader; the first block fixes the schema for the rest.
        Typed columns at I/O speed; column names mirror the python reader
        (normalized/deduplicated header) by consuming the raw header lines and
        supplying explicit names.
        """

        pyarrow = _import_optional("pyarrow", format_id="parquet_cache", purpose="managed text-to-Parquet cache")
        pa_csv = _import_optional("pyarrow.csv", format_id="parquet_cache", purpose="managed text-to-Parquet cache")
        pq = _import_optional("pyarrow.parquet", format_id="parquet_cache", purpose="managed text-to-Parquet cache")

        if str(options.encoding).strip().lower() not in self._NEWLINE_SAFE_ENCODINGS:
            raise ValueError(
                f"chunked arrow csv conversion requires a newline-safe encoding, got {options.encoding!r}"
            )

        skip_rows = options.skip_rows
        if options.header_row is not None:
            skip_rows += options.header_row + 1
        parse_options = pa_csv.ParseOptions(delimiter=delimiter)
        column_types: dict[str, Any] = {}
        for name in columns:
            hint = options.schema_hints.get(name, "")
            if not hint:
                continue
            try:
                column_types[name] = pyarrow.type_for_alias(hint)
            except (KeyError, ValueError):
                continue

        def read_block(block: bytes) -> Any:
            read_options = pa_csv.ReadOptions(encoding=options.encoding, column_names=list(columns))
            convert_options = pa_csv.ConvertOptions(column_types=column_types) if column_types else None
            return pa_csv.read_csv(
                pyarrow.BufferReader(block),
                read_options=read_options,
                parse_options=parse_options,
                convert_options=convert_options,
            )

        writer = None
        schema = None
        try:
            for block in self._iter_line_aligned_blocks(source_path, skip_rows=skip_rows):
                table = read_block(block)
                if writer is None:
                    schema = table.schema
                    # Lock every column's type so later blocks parse
                    # consistently with the first.
                    column_types.update({field.name: field.type for field in schema})
                    writer = pq.ParquetWriter(cache_path, schema)
                elif table.schema != schema:
                    table = table.cast(schema)
                writer.write_table(table)
            if writer is None:
                table = pyarrow.Table.from_pylist([], schema=pyarrow.schema([(name, pyarrow.string()) for name in columns]))
                pq.write_table(table, cache_path)
        finally:
            if writer is not None:
                writer.close()

    @classmethod
    def _iter_line_aligned_blocks(cls, source_path: Path, *, skip_rows: int) -> Iterable[bytes]:
        """Yield byte blocks of roughly _ARROW_CSV_BLOCK_BYTES ending on b"\\n"."""

        with source_path.open("rb") as handle:
            for _ in range(skip_rows):
                if not handle.readline():
                    return
            remainder = b""
            while True:
                block = handle.read(cls._ARROW_CSV_BLOCK_BYTES)
                if not block:
                    if remainder.strip():
                        yield remainder
                    return
                block = remainder + block
                cut = block.rfind(b"\n")
                while cut < 0:
                    extra = handle.read(cls._ARROW_CSV_BLOCK_BYTES)
                    if not extra:
                        break
                    block += extra
                    cut = block.rfind(b"\n")
                if cut < 0:
                    if block.strip():
                        yield block
                    return
                payload, remainder = block[: cut + 1], block[cut + 1 :]
                if payload.strip():
                    yield payload

    def _write_text_parquet_cache_python(
        self,
        source_path: Path,
        options: TabularLoadOptions,
        cache_path: Path,
        delimiter: str,
        columns: tuple[str, ...],
    ) -> None:
        pyarrow = _import_optional("pyarrow", format_id="parquet_cache", purpose="managed text-to-Parquet cache")
        pq = _import_optional("pyarrow.parquet", format_id="parquet_cache", purpose="managed text-to-Parquet cache")
        writer = None
        batch_rows: list[dict[str, Any]] = []
        try:
            for row in self._iter_text_records(source_path, options, delimiter, columns):
                batch_rows.append(row)
                if len(batch_rows) >= 4096:
                    table = pyarrow.Table.from_pylist(batch_rows, schema=None)
                    writer = _write_parquet_batch(pq, writer, cache_path, table)
                    batch_rows = []
            if batch_rows:
                table = pyarrow.Table.from_pylist(batch_rows, schema=None)
                writer = _write_parquet_batch(pq, writer, cache_path, table)
            if writer is None:
                table = pyarrow.Table.from_pylist([], schema=pyarrow.schema([(name, pyarrow.string()) for name in columns]))
                pq.write_table(table, cache_path)
        finally:
            if writer is not None:
                writer.close()

    def _write_excel_parquet_cache(
        self,
        source_path: Path,
        format_id: str,
        options: TabularLoadOptions,
        cache_path: Path,
    ) -> None:
        pyarrow = _import_optional("pyarrow", format_id="parquet_cache", purpose="managed Excel-to-Parquet cache")
        pq = _import_optional("pyarrow.parquet", format_id="parquet_cache", purpose="managed Excel-to-Parquet cache")
        selected = options.selected_object
        if not selected:
            scan = self.scan_source(source_path, options)
            selected = self._resolve_selected_object(scan, options).object_id
        openpyxl = _import_optional("openpyxl", format_id=format_id, purpose="workbook cache conversion")
        workbook = openpyxl.load_workbook(source_path, read_only=True, data_only=True)
        writer = None
        batch_rows: list[dict[str, Any]] = []
        try:
            worksheet = workbook[selected]
            columns, _row_count = self._excel_columns(source_path, selected, options)
            names = tuple(column.name for column in columns)
            for row in _worksheet_records(worksheet, options, names):
                batch_rows.append(row)
                if len(batch_rows) >= 4096:
                    table = pyarrow.Table.from_pylist(batch_rows, schema=None)
                    writer = _write_parquet_batch(pq, writer, cache_path, table)
                    batch_rows = []
            if batch_rows:
                table = pyarrow.Table.from_pylist(batch_rows, schema=None)
                writer = _write_parquet_batch(pq, writer, cache_path, table)
            if writer is None:
                table = pyarrow.Table.from_pylist([], schema=pyarrow.schema([(name, pyarrow.string()) for name in names]))
                pq.write_table(table, cache_path)
        finally:
            workbook.close()
            if writer is not None:
                writer.close()

    def _resolve_text_delimiter(self, path: Path, format_id: str, options: TabularLoadOptions) -> str:
        if options.delimiter:
            return options.delimiter
        if format_id == "tsv":
            return "\t"
        if format_id == "csv":
            return ","
        try:
            with path.open("r", encoding=options.encoding, errors="replace") as handle:
                sample = handle.read(4096)
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            return dialect.delimiter
        except Exception:
            return "\t" if path.suffix.lower() == ".tsv" else ","

    def _text_columns(self, path: Path, options: TabularLoadOptions, delimiter: str) -> tuple[str, ...]:
        with path.open("r", encoding=options.encoding, newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            for _ in range(options.skip_rows):
                next(reader, None)
            if options.header_row is None:
                first_row = next(reader, [])
                return _generated_columns(len(first_row))
            for _ in range(options.header_row):
                next(reader, None)
            header = next(reader, [])
            return _normalize_column_names(header)

    def _iter_text_records(
        self,
        path: Path,
        options: TabularLoadOptions,
        delimiter: str,
        columns: Sequence[str],
    ) -> Iterable[dict[str, Any]]:
        with path.open("r", encoding=options.encoding, newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            for _ in range(options.skip_rows):
                next(reader, None)
            if options.header_row is None:
                first_row = next(reader, None)
                if first_row is not None:
                    yield _row_to_mapping(columns, first_row)
            else:
                for _ in range(options.header_row):
                    next(reader, None)
                next(reader, None)
            for row in reader:
                yield _row_to_mapping(columns, row)

    def _excel_columns(self, path: Path, sheet_name: str, options: TabularLoadOptions) -> tuple[tuple[TabularColumn, ...], int | None]:
        openpyxl = _import_optional("openpyxl", format_id=detect_format_id(path), purpose="workbook schema")
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            worksheet = workbook[sheet_name]
            names = _worksheet_columns(worksheet, options)
            row_count = _excel_data_row_count(worksheet, options)
            return self._tabular_columns(names, options), row_count
        finally:
            workbook.close()

    def _parquet_columns(self, path: Path) -> tuple[tuple[TabularColumn, ...], int | None]:
        pq = _import_optional("pyarrow.parquet", format_id="parquet", purpose="Parquet schema")

        def read_schema() -> tuple[tuple[TabularColumn, ...], int]:
            with pq.ParquetFile(path) as parquet_file:
                schema = parquet_file.schema_arrow
                columns = tuple(TabularColumn(field.name, str(field.type), field.nullable) for field in schema)
                return columns, int(parquet_file.metadata.num_rows)

        return self._run_io(read_schema)

    def _hdf5_table_columns(self, path: Path, object_id: str) -> tuple[tuple[TabularColumn, ...], int | None]:
        h5py = _import_optional("h5py", format_id="hdf5", purpose="HDF5 table schema")
        with h5py.File(path, "r") as handle:
            dataset = handle[object_id]
            names = tuple(dataset.dtype.names or ())
            columns = tuple(TabularColumn(name, str(dataset.dtype.fields[name][0])) for name in names)
            row_count = int(dataset.shape[0]) if dataset.shape else None
            return columns, row_count

    def _tabular_columns(self, names: Sequence[str], options: TabularLoadOptions) -> tuple[TabularColumn, ...]:
        return tuple(
            TabularColumn(name, options.schema_hints.get(name, ""), True)
            for name in names
        )

    def _table_record(self, ref: TabularDataRef) -> _TableRecord:
        record = self._table_records.get(ref.ref_id)
        if record is None:
            raise KeyError(f"Unknown tabular data ref {ref.ref_id!r}.")
        return record

    def _array_record(self, ref: ArrayDataRef) -> _ArrayRecord:
        record = self._array_records.get(ref.ref_id)
        if record is None:
            raise KeyError(f"Unknown array data ref {ref.ref_id!r}.")
        return record

    def _enforce_table_materialization_gate(
        self,
        record: _TableRecord,
        options: TabularMaterializationOptions,
    ) -> None:
        if (
            self.policy.requires_explicit_materialization(record.size_bytes)
            and not options.allow_full_materialization
            and options.row_limit is None
            and options.column_limit is None
            and not options.columns
        ):
            raise LargeDataMaterializationError(
                "Full table materialization above 5 GiB requires explicit allow_full_materialization.",
                size_bytes=record.size_bytes,
            )

    def _enforce_array_materialization_gate(
        self,
        record: _ArrayRecord,
        options: ArrayMaterializationOptions,
    ) -> None:
        if (
            self.policy.requires_explicit_materialization(record.size_bytes)
            and not options.allow_full_materialization
            and options.max_elements is None
            and not options.slices
        ):
            raise LargeDataMaterializationError(
                "Full array materialization above 5 GiB requires explicit allow_full_materialization.",
                size_bytes=record.size_bytes,
            )

    def _record_metadata(
        self,
        format_id: str,
        size_bytes: int,
        warnings: Sequence[str],
        *,
        options: TabularLoadOptions | None = None,
    ) -> dict[str, Any]:
        payload = {
            "format_id": format_id,
            "size_bytes": size_bytes,
            "size_class": self.policy.classify_size(size_bytes),
            "warnings": list(warnings),
            "backend_policy_revision": self.policy.revision,
        }
        if options is not None:
            payload["load_options"] = options.to_cache_payload()
        return payload

    def _ref_id(self, kind: str, record: _TableRecord | _ArrayRecord) -> str:
        payload = {
            "kind": kind,
            "source_path": str(record.source_path),
            "format_id": record.format_id,
            "object_id": record.object_id,
            "options": record.options.to_cache_payload(),
            "size_bytes": record.size_bytes,
            "mtime_ns": record.stats.mtime_ns,
            "policy_revision": self.policy.revision,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return f"{kind}_{hashlib.sha256(raw).hexdigest()[:24]}"

    def _resolve_path(self, source_path: Path | str | os.PathLike[str]) -> Path:
        path = Path(source_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def _source_stats(self, path: Path) -> SourceStats:
        stat = path.stat()
        return SourceStats(size_bytes=int(stat.st_size), mtime_ns=int(stat.st_mtime_ns))

    def sweep_stale_cache_entries(self) -> int:
        """Delete cache entries written under a different backend policy revision."""

        removed = 0
        for metadata_path in self.cache_dir.glob("*/*.json"):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if str(metadata.get("backend_policy_revision", "")) == self.policy.revision:
                continue
            cache_path = metadata_path.with_suffix(".parquet")
            for stale in (cache_path, metadata_path):
                try:
                    stale.unlink(missing_ok=True)
                    removed += 1
                except OSError:
                    continue
        return removed

    def enforce_cache_size_limit(
        self,
        max_bytes: int = TABULAR_DATA_CACHE_MAX_BYTES,
        *,
        preserve_paths: Sequence[Path] | None = None,
    ) -> int:
        """Evict least-recently-used cache entries past the size cap."""

        preserved = {
            Path(path).resolve(strict=False)
            for path in (preserve_paths or ())
        }
        entries: list[tuple[float, int, Path, Path]] = []
        total = 0
        for cache_path in self.cache_dir.glob("*/*.parquet"):
            try:
                stat = cache_path.stat()
            except OSError:
                continue
            size = int(stat.st_size)
            total += size
            entries.append((stat.st_mtime, size, cache_path, cache_path.with_suffix(".json")))
        if total <= max_bytes:
            return 0
        removed = 0
        for _mtime, size, cache_path, metadata_path in sorted(entries):
            if total <= max_bytes:
                break
            if cache_path.resolve(strict=False) in preserved:
                continue
            try:
                cache_path.unlink(missing_ok=True)
                metadata_path.unlink(missing_ok=True)
            except OSError:
                continue
            total -= size
            removed += 1
        return removed


_shared_service_guard = threading.Lock()
_shared_service: TabularLoaderCacheService | None = None
_shared_ui_thread_conversion_allowed = True


def set_shared_tabular_ui_thread_conversion_allowed(allowed: bool) -> None:
    """Configure the shared service without forcing its first allocation."""

    global _shared_ui_thread_conversion_allowed
    with _shared_service_guard:
        _shared_ui_thread_conversion_allowed = bool(allowed)
        if _shared_service is not None:
            _shared_service.ui_thread_conversion_allowed = _shared_ui_thread_conversion_allowed


def shared_tabular_loader_cache_service() -> TabularLoaderCacheService:
    """Process-wide tabular loader service.

    One shared instance keeps table/array records, scan results, and the
    managed parquet cache warm across execution, previews, and scene payload
    builds. Thread-safe; the first call sweeps cache entries written under a
    previous backend policy revision.
    """

    global _shared_service
    with _shared_service_guard:
        if _shared_service is None:
            service = TabularLoaderCacheService()
            service.ui_thread_conversion_allowed = _shared_ui_thread_conversion_allowed
            try:
                service.sweep_stale_cache_entries()
            except OSError:
                pass
            _shared_service = service
        return _shared_service


def reset_shared_tabular_loader_cache_service() -> None:
    """Drop the process-wide service (test isolation hook)."""

    global _shared_service, _shared_ui_thread_conversion_allowed
    with _shared_service_guard:
        _shared_service = None
        _shared_ui_thread_conversion_allowed = True


class _Hdf5ArrayHandle:
    def __init__(self, handle: Any, object_id: str) -> None:
        self._handle = handle
        self._dataset = handle[object_id]

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(int(value) for value in self._dataset.shape)

    def __getitem__(self, item: Any) -> Any:
        try:
            return self._dataset[item]
        finally:
            self._handle.close()


def detect_format_id(path: Path | str | os.PathLike[str]) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in {".csv", ".tsv", ".txt", ".xlsx", ".xlsm", ".parquet", ".npy", ".npz"}:
        return suffix[1:]
    if suffix in HDF5_SUFFIXES:
        return "hdf5"
    raise UnsupportedTabularFormatError(Path(path))


def supported_format_ids() -> tuple[str, ...]:
    return SUPPORTED_FORMAT_IDS


def scan_tabular_source(
    source_path: Path | str | os.PathLike[str],
    options: TabularLoadOptions | Mapping[str, Any] | None = None,
    *,
    cache_dir: Path | str | os.PathLike[str] | None = None,
    policy: TabularBackendPolicy = DEFAULT_TABULAR_BACKEND_POLICY,
) -> SourceScanResult:
    return TabularLoaderCacheService(cache_dir=cache_dir, policy=policy).scan_source(source_path, options)


def open_tabular_source(
    source_path: Path | str | os.PathLike[str],
    options: TabularLoadOptions | Mapping[str, Any] | None = None,
    *,
    cache_dir: Path | str | os.PathLike[str] | None = None,
    policy: TabularBackendPolicy = DEFAULT_TABULAR_BACKEND_POLICY,
) -> tuple[TabularLoaderCacheService, TabularDataRef | ArrayDataRef]:
    service = TabularLoaderCacheService(cache_dir=cache_dir, policy=policy)
    return service, service.open_source(source_path, options)


def _coerce_options(options: TabularLoadOptions | Mapping[str, Any] | None) -> TabularLoadOptions:
    if isinstance(options, TabularLoadOptions):
        return options
    return TabularLoadOptions.from_mapping(options)


def _source_path_from_ref(ref: TabularDataRef | ArrayDataRef) -> Path:
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


def _load_options_from_ref(ref: TabularDataRef | ArrayDataRef) -> TabularLoadOptions:
    metadata = ref.metadata if isinstance(ref.metadata, Mapping) else {}
    load_options = metadata.get("load_options")
    options = TabularLoadOptions.from_mapping(load_options if isinstance(load_options, Mapping) else None)
    if ref.object_id:
        return options.with_selected_object(ref.object_id)
    return options


def _normalize_optional_non_negative_int(field_name: str, value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer")
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be an integer") from exc
    if normalized < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return normalized


def _normalize_non_negative_int(field_name: str, value: Any) -> int:
    normalized = _normalize_optional_non_negative_int(field_name, value)
    if normalized is None:
        raise ValueError(f"{field_name} must be an integer")
    return normalized


def _import_optional(module_name: str, *, format_id: str, purpose: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        missing_name = exc.name or module_name
        if missing_name == module_name or module_name.startswith(f"{missing_name}."):
            raise MissingTabularDependencyError(
                format_id=format_id,
                dependency=missing_name,
                purpose=purpose,
            ) from exc
        raise


def _normalize_column_names(values: Sequence[Any]) -> tuple[str, ...]:
    names: list[str] = []
    seen: dict[str, int] = {}
    for index, value in enumerate(values):
        base = str(value).strip() if value is not None else ""
        if not base:
            base = f"column_{index + 1}"
        count = seen.get(base, 0) + 1
        seen[base] = count
        names.append(base if count == 1 else f"{base}_{count}")
    return tuple(names)


def _generated_columns(count: int) -> tuple[str, ...]:
    return tuple(f"column_{index + 1}" for index in range(max(0, int(count))))


def _row_to_mapping(columns: Sequence[str], values: Sequence[Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for index, column in enumerate(columns):
        value = values[index] if index < len(values) else None
        row[column] = _json_safe_value(value)
    return row


def _worksheet_columns(worksheet: Any, options: TabularLoadOptions) -> tuple[str, ...]:
    rows = worksheet.iter_rows(values_only=True)
    for _ in range(options.skip_rows):
        next(rows, None)
    if options.header_row is None:
        first_row = next(rows, None) or ()
        return _generated_columns(len(first_row))
    for _ in range(options.header_row):
        next(rows, None)
    header = next(rows, None) or ()
    return _normalize_column_names(header)


def _worksheet_records(
    worksheet: Any,
    options: TabularLoadOptions,
    columns: Sequence[str],
) -> Iterable[dict[str, Any]]:
    rows = worksheet.iter_rows(values_only=True)
    for _ in range(options.skip_rows):
        next(rows, None)
    if options.header_row is None:
        first_row = next(rows, None)
        if first_row is not None:
            yield _row_to_mapping(columns, first_row)
    else:
        for _ in range(options.header_row):
            next(rows, None)
        next(rows, None)
    for row in rows:
        yield _row_to_mapping(columns, row)


def _excel_data_row_count(worksheet: Any, options: TabularLoadOptions) -> int | None:
    max_row = worksheet.max_row
    if max_row is None:
        return None
    header_rows = 0 if options.header_row is None else options.header_row + 1
    return max(0, int(max_row) - options.skip_rows - header_rows)


def _select_columns(columns: Sequence[str], request: TabularWindowRequest) -> tuple[str, ...]:
    available = tuple(columns)
    if request.columns:
        selected = tuple(column for column in request.columns if column in available)
        return selected if request.column_limit == 0 else selected[: request.column_limit]
    if request.column_limit == 0:
        return available[request.column_offset:]
    return available[request.column_offset : request.column_offset + request.column_limit]


@dataclass(slots=True, frozen=True)
class _QueryFilter:
    column: str | None
    op: str
    value: str


def _query_int(value: Any, *, default: int, minimum: int) -> int:
    if isinstance(value, bool):
        return max(minimum, default)
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return max(minimum, default)
    return max(minimum, normalized)


def _as_sequence(value: Any) -> tuple[Any, ...]:
    if value is None or isinstance(value, (str, bytes, Mapping)):
        return ()
    if isinstance(value, Sequence):
        return tuple(value)
    return ()


def _sort_descending(entry: Mapping[str, Any]) -> bool:
    if "descending" in entry:
        return bool(entry.get("descending"))
    direction = str(entry.get("direction", "")).strip().lower()
    return direction in {"desc", "descending"}


def _normalize_sort_directives(value: Any) -> tuple[tuple[str, bool], ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, Mapping):
        entries: tuple[Any, ...] = (value,)
    elif isinstance(value, str):
        text = value.strip()
        return ((text, False),) if text else ()
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        entries = tuple(value)
    else:
        return ()
    directives: list[tuple[str, bool]] = []
    for entry in entries:
        if isinstance(entry, Mapping):
            column = str(entry.get("column", "")).strip()
            if column:
                directives.append((column, _sort_descending(entry)))
        elif isinstance(entry, str) and entry.strip():
            directives.append((entry.strip(), False))
    return tuple(directives)


def _structured_filter(entry: Mapping[str, Any]) -> _QueryFilter | None:
    column = str(entry.get("column", "")).strip()
    op = str(entry.get("op", "contains")).strip().lower() or "contains"
    raw_value = entry.get("value", entry.get("text", ""))
    value_text = "" if raw_value is None else str(raw_value)
    if not column and not value_text.strip():
        return None
    return _QueryFilter(column or None, op, value_text)


def _filter_predicates(value: Any) -> tuple[_QueryFilter, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        text = value.strip()
        return (_QueryFilter(None, "contains", text),) if text else ()
    if isinstance(value, Mapping):
        if {"column", "op", "value"} & set(value):
            single = _structured_filter(value)
            return (single,) if single is not None else ()
        if "text" in value:
            text = str(value.get("text", "")).strip()
            return (_QueryFilter(None, "contains", text),) if text else ()
        predicates: list[_QueryFilter] = []
        for key, raw in value.items():
            cell = "" if raw is None else str(raw).strip()
            if cell:
                predicates.append(_QueryFilter(str(key).strip() or None, "contains", cell))
        return tuple(predicates)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        predicates = []
        for item in value:
            if isinstance(item, Mapping):
                single = _structured_filter(item)
                if single is not None:
                    predicates.append(single)
            elif isinstance(item, str) and item.strip():
                predicates.append(_QueryFilter(None, "contains", item.strip()))
        return tuple(predicates)
    return ()


def _collect_query_predicates(
    filters_value: Any,
    filter_value: Any,
    search_value: Any,
) -> tuple[_QueryFilter, ...]:
    predicates: list[_QueryFilter] = []
    for raw in (filters_value, filter_value):
        predicates.extend(_filter_predicates(raw))
    search_text = "" if search_value is None else str(search_value).strip()
    if search_text:
        predicates.append(_QueryFilter(None, "contains", search_text))
    return tuple(predicates)


def _cell_text(cell: Any) -> str:
    return "" if cell is None else str(cell)


def _compare_cell(text: str, op: str, target: str) -> bool:
    try:
        left: Any = float(text)
        right: Any = float(target)
    except (TypeError, ValueError):
        left, right = text.lower(), target.lower()
    if op == "gt":
        return left > right
    if op == "gte":
        return left >= right
    if op == "lt":
        return left < right
    return left <= right


def _cell_op(cell: Any, op: str, target: str) -> bool:
    text = _cell_text(cell)
    if op in {"gt", "gte", "lt", "lte"}:
        return _compare_cell(text, op, target)
    lowered = text.lower()
    needle = target.lower()
    if op in {"equals", "eq"}:
        return lowered.strip() == needle.strip()
    if op == "startswith":
        return lowered.startswith(needle)
    if op == "endswith":
        return lowered.endswith(needle)
    return needle in lowered


def _predicate_matches(
    row: Mapping[str, Any],
    predicate: _QueryFilter,
    selected_columns: Sequence[str],
) -> bool:
    if predicate.column:
        cells: tuple[Any, ...] = (row.get(predicate.column),)
    else:
        cells = tuple(row.get(column) for column in selected_columns)
    if predicate.op == "not_contains":
        needle = predicate.value.lower()
        return all(needle not in _cell_text(cell).lower() for cell in cells)
    return any(_cell_op(cell, predicate.op, predicate.value) for cell in cells)


def _row_passes_predicates(
    row: Mapping[str, Any],
    predicates: Sequence[_QueryFilter],
    selected_columns: Sequence[str],
) -> bool:
    return all(
        _predicate_matches(row, predicate, selected_columns)
        for predicate in predicates
    )


def _arrow_text_view(pyarrow: Any, pa_compute: Any, column: Any) -> Any:
    """Lowercased string view of a column (mirrors ``_cell_text().lower()``)."""

    if not (pyarrow.types.is_string(column.type) or pyarrow.types.is_large_string(column.type)):
        column = pa_compute.cast(column, pyarrow.string())
    return pa_compute.utf8_lower(column)


def _arrow_numeric_text_values(pyarrow: Any, pa_compute: Any, text_view: Any) -> tuple[Any, Any]:
    trimmed = pa_compute.utf8_trim_whitespace(text_view)
    numeric_mask = pa_compute.fill_null(
        pa_compute.match_substring_regex(trimmed, _NUMERIC_TEXT_PATTERN),
        False,
    )
    numeric_text = pa_compute.if_else(
        numeric_mask,
        trimmed,
        pyarrow.scalar(None, type=pyarrow.string()),
    )
    return numeric_mask, pa_compute.cast(numeric_text, pyarrow.float64())


def _arrow_query_sort_columns(pyarrow: Any, pa_compute: Any, column: Any, text_view: Any) -> tuple[Any, Any, Any]:
    trimmed = pa_compute.utf8_trim_whitespace(text_view)
    empty_mask = pa_compute.equal(trimmed, "")
    numeric_mask, numeric_values = _arrow_numeric_text_values(pyarrow, pa_compute, text_view)
    valid_mask = pa_compute.is_valid(column)
    text_mask = pa_compute.and_kleene(
        valid_mask,
        pa_compute.and_kleene(pa_compute.invert(empty_mask), pa_compute.invert(numeric_mask)),
    )
    kind = pa_compute.if_else(
        numeric_mask,
        pyarrow.scalar(0),
        pa_compute.if_else(text_mask, pyarrow.scalar(1), pyarrow.scalar(2)),
    )
    numeric_key = pa_compute.fill_null(numeric_values, 0.0)
    text_key = pa_compute.if_else(text_mask, trimmed, pyarrow.scalar("", type=pyarrow.string()))
    return kind, numeric_key, text_key


def _arrow_cell_op_mask(
    pyarrow: Any,
    pa_compute: Any,
    column: Any,
    op: str,
    value: str,
    text_view: Any,
) -> Any:
    """Boolean mask mirror of ``_cell_op`` for one column/value pair.

    ``text_view`` is the (possibly cached) lowercased string view of the
    column — see ``_query_table_for``.
    """

    needle = value.lower()
    if op in {"gt", "gte", "lt", "lte"}:
        compare = {
            "gt": pa_compute.greater,
            "gte": pa_compute.greater_equal,
            "lt": pa_compute.less,
            "lte": pa_compute.less_equal,
        }[op]
        numeric_target: float | None
        try:
            numeric_target = float(value)
        except (TypeError, ValueError):
            numeric_target = None
        is_numeric_column = (
            pyarrow.types.is_integer(column.type)
            or pyarrow.types.is_floating(column.type)
            or pyarrow.types.is_decimal(column.type)
        )
        if is_numeric_column and numeric_target is not None and math.isfinite(numeric_target):
            return compare(column, numeric_target)
        if numeric_target is not None and math.isfinite(numeric_target):
            numeric_mask, numeric_values = _arrow_numeric_text_values(pyarrow, pa_compute, text_view)
            return pa_compute.if_else(
                numeric_mask,
                compare(numeric_values, numeric_target),
                compare(text_view, needle),
            )
        return compare(text_view, needle)
    if op in {"equals", "eq"}:
        return pa_compute.equal(pa_compute.utf8_trim_whitespace(text_view), needle.strip())
    if op == "startswith":
        return pa_compute.starts_with(text_view, needle)
    if op == "endswith":
        return pa_compute.ends_with(text_view, needle)
    return pa_compute.match_substring(text_view, needle)


def _arrow_predicate_mask(
    pyarrow: Any,
    pa_compute: Any,
    table: Any,
    predicate: "_QueryFilter",
    selected_columns: Sequence[str],
    text_view_for: Any,
) -> Any:
    """Boolean mask mirror of ``_predicate_matches``."""

    columns = (predicate.column,) if predicate.column else tuple(selected_columns)
    columns = tuple(column for column in columns if column in table.column_names)
    if not columns:
        if predicate.op == "not_contains":
            return pa_compute.cast(pyarrow.array([True] * table.num_rows), pyarrow.bool_())
        return pa_compute.cast(pyarrow.array([False] * table.num_rows), pyarrow.bool_())
    if predicate.op == "not_contains":
        mask = None
        for column in columns:
            contains = pa_compute.fill_null(
                pa_compute.match_substring(text_view_for(column), predicate.value.lower()),
                False,
            )
            inverted = pa_compute.invert(contains)
            mask = inverted if mask is None else pa_compute.and_(mask, inverted)
        return mask
    mask = None
    for column in columns:
        cell_mask = pa_compute.fill_null(
            _arrow_cell_op_mask(
                pyarrow,
                pa_compute,
                table.column(column),
                predicate.op,
                predicate.value,
                text_view_for(column),
            ),
            False,
        )
        mask = cell_mask if mask is None else pa_compute.or_(mask, cell_mask)
    return mask


def _query_sort_key(value: Any) -> tuple[int, float, str]:
    if value is None:
        return (2, 0.0, "")
    if isinstance(value, bool):
        return (0, float(value), "")
    if isinstance(value, (int, float)):
        numeric = float(value)
        return (0, numeric, "") if math.isfinite(numeric) else (2, 0.0, "")
    text = str(value).strip()
    if not text:
        return (2, 0.0, "")
    try:
        return (0, float(text), "")
    except ValueError:
        return (1, 0.0, text.lower())


def _window_request_from_materialization(
    record: _TableRecord,
    options: TabularMaterializationOptions,
) -> TabularWindowRequest:
    if options.row_limit is not None:
        row_limit = options.row_limit
    elif record.row_count is not None:
        row_limit = record.row_count
    else:
        row_limit = 0
    column_limit = options.column_limit if options.column_limit is not None else len(record.columns)
    return TabularWindowRequest(
        row_limit=row_limit,
        column_limit=column_limit,
        columns=options.columns,
    )


def _slice_array_2d(array: Any, request: ArraySlice2DRequest) -> Any:
    shape = tuple(int(value) for value in getattr(array, "shape", ()))
    row_stop = None if request.row_limit == 0 else request.row_offset + request.row_limit
    column_stop = None if request.column_limit == 0 else request.column_offset + request.column_limit
    if len(shape) == 0:
        return [[array[()]]]
    if len(shape) == 1:
        return array[request.row_offset:row_stop]
    base = (
        slice(request.row_offset, row_stop),
        slice(request.column_offset, column_stop),
    )
    if len(shape) > 2:
        base = base + tuple(0 for _ in shape[2:])
    return array[base]


def _array_values_to_rows(values: Any) -> tuple[tuple[Any, ...], ...]:
    shape = tuple(int(value) for value in getattr(values, "shape", ()))
    if len(shape) == 0:
        return ((_json_safe_value(values.item() if hasattr(values, "item") else values),),)
    if len(shape) == 1:
        return tuple((_json_safe_value(value),) for value in values.tolist())
    return tuple(
        tuple(_json_safe_value(value) for value in row)
        for row in values.tolist()
    )


def _json_safe_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe_value(value) for key, value in payload.items()}


def _json_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "item"):
        return _json_safe_value(value.item())
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value]
    return str(value)


def _path_uri(path: Path) -> str:
    try:
        return path.as_uri()
    except ValueError:
        return path.resolve().as_uri()


def _copy_file(source_path: Path, cache_path: Path) -> None:
    import shutil

    shutil.copy2(source_path, cache_path)


def _write_parquet_batch(pq: Any, writer: Any, cache_path: Path, table: Any) -> Any:
    if writer is None:
        writer = pq.ParquetWriter(cache_path, table.schema)
    writer.write_table(table)
    return writer


__all__ = [
    "ARRAY_FORMAT_IDS",
    "EXCEL_FORMAT_IDS",
    "HDF5_SUFFIXES",
    "LargeDataMaterializationError",
    "MissingTabularDependencyError",
    "ParquetCacheEntry",
    "ParquetCacheKey",
    "SUPPORTED_FORMAT_IDS",
    "SelectableObject",
    "SelectionRequiredError",
    "SourceScanResult",
    "SourceStats",
    "TABULAR_CACHE_RESOLVER_ID",
    "TEXT_FORMAT_IDS",
    "TabularCacheNotReadyError",
    "TabularLoadOptions",
    "TabularLoaderCacheService",
    "TabularLoaderError",
    "UnsupportedTabularFormatError",
    "detect_format_id",
    "open_tabular_source",
    "reset_shared_tabular_loader_cache_service",
    "scan_tabular_source",
    "set_shared_tabular_ui_thread_conversion_allowed",
    "shared_tabular_loader_cache_service",
    "supported_format_ids",
]
