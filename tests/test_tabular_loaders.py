from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

import ea_node_editor.addons.tabular_data.loader_cache_service as loader_module
from ea_node_editor.addons.tabular_data.loader_cache_service import (
    MissingTabularDependencyError,
    SelectionRequiredError,
    TabularLoadOptions,
    TabularLoaderCacheService,
    supported_format_ids,
)
from ea_node_editor.runtime_contracts import (
    ArrayDataRef,
    ArraySlice2DRequest,
    TabularDataRef,
    TabularMaterializationOptions,
    TabularWindowRequest,
)


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _run_python_probe(code: str, *args: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code), *args],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert completed.returncode == 0, (
        f"Probe exited {completed.returncode}\n"
        f"STDOUT:\n{completed.stdout}\n"
        f"STDERR:\n{completed.stderr}"
    )


def test_supported_format_registry_matches_p03_scope() -> None:
    assert supported_format_ids() == (
        "csv",
        "tsv",
        "txt",
        "xlsx",
        "xlsm",
        "parquet",
        "hdf5",
        "npy",
        "npz",
    )


@pytest.mark.parametrize(
    ("filename", "contents", "options", "expected_columns", "expected_second_value"),
    [
        (
            "weather.csv",
            "# generated\nstation,temp\nA,21.5\nB,22.0\n",
            TabularLoadOptions(skip_rows=1, schema_hints={"temp": "float64"}),
            ("station", "temp"),
            22.0,
        ),
        (
            "weather.tsv",
            "station\ttemp\nA\t21.5\nB\t22.0\n",
            TabularLoadOptions(),
            ("station", "temp"),
            22.0,
        ),
        (
            "weather.txt",
            "station|temp\nA|21.5\nB|22.0\n",
            TabularLoadOptions(delimiter="|"),
            ("station", "temp"),
            22.0,
        ),
    ],
)
def test_text_loaders_infer_or_honor_options_and_return_bounded_windows(
    tmp_path: Path,
    filename: str,
    contents: str,
    options: TabularLoadOptions,
    expected_columns: tuple[str, str],
    expected_second_value: float,
) -> None:
    source = tmp_path / filename
    source.write_text(contents, encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")

    scan = service.scan_source(source, options)
    assert scan.selected_object_id == "table"
    assert scan.requires_selection is False
    # Open never scans the source for row counts; they backfill from the
    # managed parquet cache after the first read.
    assert scan.objects[0].row_count is None

    ref = service.open_source(source, options)
    assert isinstance(ref, TabularDataRef)
    assert ref.resolver_id == "tabular.cache"
    assert ref.backend_id == "python_text_stream"
    assert ref.row_count is None

    window = service.window(ref, TabularWindowRequest(row_offset=1, row_limit=1, column_limit=2))
    assert window.columns == expected_columns
    assert window.rows == ({"station": "B", "temp": expected_second_value},)
    assert window.total_rows == 2

    schema = service.schema(ref)
    assert tuple(column.name for column in schema.columns) == expected_columns
    assert schema.row_count == 2
    if "temp" in options.schema_hints:
        assert schema.columns[1].dtype == "float64"


def test_txt_delimiter_detection_reads_only_the_first_4096_characters(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    source = tmp_path / "large.txt"
    source.write_text("a|b\n" * 5000, encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    real_open = Path.open
    read_sizes: list[int] = []

    class _TrackingReader:
        def __init__(self, handle):  # noqa: ANN001
            self._handle = handle

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *args):  # noqa: ANN002, ANN204
            self._handle.close()

        def read(self, size: int = -1) -> str:
            read_sizes.append(size)
            return self._handle.read(size)

    def tracking_open(path: Path, *args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        handle = real_open(path, *args, **kwargs)
        if path == source and args and args[0] == "r":
            return _TrackingReader(handle)
        return handle

    monkeypatch.setattr(Path, "open", tracking_open)

    delimiter = service._resolve_text_delimiter(source, "txt", TabularLoadOptions())

    assert delimiter == "|"
    assert read_sizes == [4096]


def test_text_materialization_without_cached_row_count_reads_all_rows(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    source = tmp_path / "weather.csv"
    source.write_text("station,temp\nA,21.5\nB,22.0\n", encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")

    ref = service.open_source(source)
    assert isinstance(ref, TabularDataRef)
    assert ref.row_count is None

    frame = service.to_pandas(ref, TabularMaterializationOptions(allow_full_materialization=True))

    assert list(frame["station"]) == ["A", "B"]
    assert list(frame["temp"]) == [21.5, 22.0]


def test_text_loader_supports_headerless_files(tmp_path: Path) -> None:
    source = tmp_path / "raw.txt"
    source.write_text("A|21.5\nB|22.0\n", encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")

    ref = service.open_source(source, TabularLoadOptions(delimiter="|", header_row=None))
    window = service.window(ref, TabularWindowRequest(row_limit=2, column_limit=2))

    assert isinstance(ref, TabularDataRef)
    assert window.columns == ("column_1", "column_2")
    assert window.rows == (
        {"column_1": "A", "column_2": 21.5},
        {"column_1": "B", "column_2": 22.0},
    )


def test_tabular_ref_reopens_from_source_uri_and_load_options(tmp_path: Path) -> None:
    source = tmp_path / "raw.txt"
    source.write_text("A|21.5\nB|22.0\n", encoding="utf-8")
    original = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = original.open_source(source, TabularLoadOptions(delimiter="|", header_row=None))
    fresh = TabularLoaderCacheService(cache_dir=tmp_path / "cache")

    fresh.ensure_table_ref(ref)
    window = fresh.window(ref, TabularWindowRequest(row_limit=2, column_limit=2))

    assert window.columns == ("column_1", "column_2")
    assert window.rows == (
        {"column_1": "A", "column_2": 21.5},
        {"column_1": "B", "column_2": 22.0},
    )


def test_existing_tabular_ref_reopens_when_source_schema_changes(tmp_path: Path) -> None:
    source = tmp_path / "changing.csv"
    source.write_text("time,temp\n0,21.5\n", encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source)

    assert tuple(column.name for column in service.schema(ref).columns) == ("time", "temp")

    source.write_text("time,temp,pressure\n1,22.0,101.3\n", encoding="utf-8")
    window = service.window(ref, TabularWindowRequest(row_limit=1, column_limit=0))

    assert window.columns == ("time", "temp", "pressure")
    assert window.rows == ({"time": 1, "temp": 22.0, "pressure": 101.3},)


def test_parquet_arrow_batches_stream_before_exhausting_source(tmp_path: Path) -> None:
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    produced = 0

    def fake_iter(_record, _options, _path):  # noqa: ANN001
        nonlocal produced
        for index in range(20):
            produced += 1
            yield {"batch": index}

    service._iter_parquet_batches = fake_iter  # type: ignore[method-assign]
    iterator = service._iter_parquet_batches_safely(object(), object(), tmp_path / "dummy.parquet")  # type: ignore[arg-type]
    try:
        first = next(iterator)
        time.sleep(0.05)
        assert first == {"batch": 0}
        assert produced < 20
    finally:
        iterator.close()


def test_excel_loader_requires_selection_for_multi_sheet_workbook_and_streams_selected_sheet(
    tmp_path: Path,
) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    source = tmp_path / "book.xlsx"
    workbook = openpyxl.Workbook()
    workbook.active.title = "First"
    workbook["First"].append(["name", "value"])
    workbook["First"].append(["alpha", 1])
    second = workbook.create_sheet("Second")
    second.append(["name", "value"])
    second.append(["beta", 2])
    workbook.save(source)

    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    scan = service.scan_source(source)

    assert scan.requires_selection is True
    assert tuple(item.object_id for item in scan.objects) == ("First", "Second")
    with pytest.raises(SelectionRequiredError):
        service.open_source(source)

    ref = service.open_source(source, TabularLoadOptions(selected_object="Second"))
    window = service.window(ref, TabularWindowRequest(row_limit=1, column_limit=2))
    assert isinstance(ref, TabularDataRef)
    assert ref.object_id == "Second"
    assert window.rows == ({"name": "beta", "value": 2},)


def test_npy_loader_uses_mmap_backed_array_refs_and_bounded_slices(tmp_path: Path) -> None:
    numpy = pytest.importorskip("numpy")
    source = tmp_path / "array.npy"
    numpy.save(source, numpy.arange(12, dtype=numpy.float64).reshape(3, 4))
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")

    ref = service.open_source(source)
    result = service.slice_2d(ref, ArraySlice2DRequest(row_offset=1, row_limit=1, column_offset=1, column_limit=2))

    assert isinstance(ref, ArrayDataRef)
    assert ref.backend_id == "npy_mmap"
    assert ref.metadata["format_id"] == "npy"
    assert ref.shape == (3, 4)
    assert ref.dtype == "float64"
    assert result.values == ((5.0, 6.0),)


def test_npz_loader_requires_key_selection_and_treats_archive_as_array_source(tmp_path: Path) -> None:
    numpy = pytest.importorskip("numpy")
    source = tmp_path / "archive.npz"
    numpy.savez(source, first=numpy.arange(4).reshape(2, 2), second=numpy.arange(6).reshape(3, 2))
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")

    scan = service.scan_source(source)
    assert scan.requires_selection is True
    assert tuple(item.object_id for item in scan.objects) == ("first", "second")
    with pytest.raises(SelectionRequiredError):
        service.open_source(source)

    ref = service.open_source(source, TabularLoadOptions(selected_object="second"))
    result = service.slice_2d(ref, ArraySlice2DRequest(row_limit=2, column_limit=1))
    assert isinstance(ref, ArrayDataRef)
    assert ref.backend_id == "npz_archive"
    assert ref.shape == (3, 2)
    assert result.values == ((0,), (2,))


def test_parquet_loader_lane_loads_tiny_fixture_or_reports_recoverable_dependency_error(
    tmp_path: Path,
) -> None:
    source = tmp_path / "table.parquet"
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")

    if not _module_available("pyarrow"):
        source.write_bytes(b"not parquet")
        with pytest.raises(MissingTabularDependencyError) as exc_info:
            service.scan_source(source)
        assert exc_info.value.format_id == "parquet"
        assert exc_info.value.dependency == "pyarrow"
        assert exc_info.value.recoverable is True
        return

    _run_python_probe(
        """
        import sys
        from pathlib import Path

        import pyarrow
        import pyarrow.parquet as pq

        from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService
        from ea_node_editor.runtime_contracts import TabularDataRef, TabularWindowRequest

        root = Path(sys.argv[1])
        source = root / "table.parquet"
        pq.write_table(pyarrow.table({"name": ["alpha", "beta"], "value": [1, 2]}), source)

        service = TabularLoaderCacheService(cache_dir=root / "cache")
        ref = service.open_source(source)
        window = service.window(ref, TabularWindowRequest(row_limit=1, column_limit=2))

        assert isinstance(ref, TabularDataRef)
        assert ref.metadata["format_id"] == "parquet"
        assert window.rows == ({"name": "alpha", "value": 1},)
        """,
        str(tmp_path),
    )


def test_hdf5_loader_lane_loads_tiny_fixture_or_reports_recoverable_dependency_error(
    tmp_path: Path,
) -> None:
    source = tmp_path / "arrays.h5"
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")

    if not _module_available("h5py"):
        source.write_bytes(b"not hdf5")
        with pytest.raises(MissingTabularDependencyError) as exc_info:
            service.scan_source(source)
        assert exc_info.value.format_id == "hdf5"
        assert exc_info.value.dependency == "h5py"
        assert exc_info.value.recoverable is True
        return

    h5py = pytest.importorskip("h5py")
    numpy = pytest.importorskip("numpy")
    with h5py.File(source, "w") as handle:
        handle.create_dataset("matrix", data=numpy.arange(6).reshape(3, 2))

    ref = service.open_source(source)
    result = service.slice_2d(ref, ArraySlice2DRequest(row_offset=1, row_limit=2, column_limit=2))
    assert isinstance(ref, ArrayDataRef)
    assert ref.backend_id == "hdf5_dataset"
    assert ref.object_id == "matrix"
    assert result.values == ((2, 3), (4, 5))


_QUERY_CSV = (
    "station,temp,country\n"
    "Charlie,30,US\n"
    "alpha,21.5,FR\n"
    "Bravo,21.5,US\n"
    "delta,9,DE\n"
)


def _stations(window) -> list[str]:  # noqa: ANN001
    return [str(row["station"]) for row in window.rows]


def _open_query_table(tmp_path: Path) -> tuple[TabularLoaderCacheService, TabularDataRef]:
    source = tmp_path / "query.csv"
    source.write_text(_QUERY_CSV, encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source)
    assert isinstance(ref, TabularDataRef)
    return service, ref


def _base_request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "row_offset": 0,
        "row_limit": 50,
        "column_offset": 0,
        "column_limit": 50,
    }
    request.update(overrides)
    return request


def test_preview_window_sorts_text_source_by_numeric_column_both_directions(tmp_path: Path) -> None:
    service, ref = _open_query_table(tmp_path)

    ascending = service.preview_window(ref, _base_request(sort={"column": "temp", "descending": False}))
    descending = service.preview_window(ref, _base_request(sort={"column": "temp", "descending": True}))

    assert _stations(ascending) == ["delta", "alpha", "Bravo", "Charlie"]
    assert _stations(descending) == ["Charlie", "alpha", "Bravo", "delta"]
    assert ascending.total_rows == 4
    assert ascending.total_columns == 3


def test_preview_window_applies_free_text_filter_and_search(tmp_path: Path) -> None:
    service, ref = _open_query_table(tmp_path)

    filtered = service.preview_window(ref, _base_request(filters={"text": "US"}))
    searched = service.preview_window(ref, _base_request(search="21.5"))

    assert sorted(_stations(filtered)) == ["Bravo", "Charlie"]
    assert filtered.total_rows == 2
    assert sorted(_stations(searched)) == ["Bravo", "alpha"]
    assert searched.total_rows == 2


def test_preview_window_applies_row_and_column_window_after_sort(tmp_path: Path) -> None:
    service, ref = _open_query_table(tmp_path)

    window = service.preview_window(
        ref,
        _base_request(row_offset=1, row_limit=2, column_limit=2, sort={"column": "temp"}),
    )

    assert _stations(window) == ["alpha", "Bravo"]
    assert window.columns == ("station", "temp")
    assert "country" not in window.rows[0]
    assert window.row_offset == 1
    assert window.total_rows == 4


def test_preview_window_supports_multi_key_sort_and_numeric_filter(tmp_path: Path) -> None:
    service, ref = _open_query_table(tmp_path)

    multi_sorted = service.preview_window(
        ref,
        _base_request(sort=[{"column": "temp"}, {"column": "station", "descending": True}]),
    )
    gte_filtered = service.preview_window(
        ref,
        _base_request(filters=[{"column": "temp", "op": "gte", "value": "21.5"}]),
    )
    gt_filtered = service.preview_window(
        ref,
        _base_request(filters=[{"column": "temp", "op": "gt", "value": "21.5"}]),
    )

    assert _stations(multi_sorted) == ["delta", "Bravo", "alpha", "Charlie"]
    assert sorted(_stations(gte_filtered)) == ["Bravo", "Charlie", "alpha"]
    assert gte_filtered.total_rows == 3
    assert _stations(gt_filtered) == ["Charlie"]


def test_preview_window_reports_scan_truncation_for_source_direct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Managed-cache sources query via duckdb without a scan cap; the bounded
    # python scan (and its truncation metadata) remains for source_direct.
    source = tmp_path / "query.csv"
    source.write_text(_QUERY_CSV, encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = service.open_source(source, TabularLoadOptions(cache_policy="source_direct"))
    monkeypatch.setattr(loader_module, "PREVIEW_QUERY_SCAN_ROW_CAP", 2)

    window = service.preview_window(ref, _base_request(sort={"column": "station"}))

    assert window.total_rows == 2
    assert window.metadata["query_scan_truncated"] is True
    assert window.metadata["query_scanned_rows"] == 2


def test_preview_window_arrow_query_matches_python_scan(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    source = tmp_path / "query.csv"
    source.write_text(_QUERY_CSV, encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    managed_ref = service.open_source(source)
    direct_ref = service.open_source(source, TabularLoadOptions(cache_policy="source_direct"))

    requests = [
        _base_request(sort={"column": "temp", "descending": False}),
        _base_request(sort={"column": "temp", "descending": True}),
        _base_request(filters={"text": "US"}, sort={"column": "station"}),
        _base_request(search="21.5", sort={"column": "station"}),
        _base_request(filters=[{"column": "temp", "op": "gte", "value": "21.5"}], sort={"column": "station"}),
        _base_request(filters=[{"column": "station", "op": "startswith", "value": "b"}]),
        _base_request(filters=[{"column": "station", "op": "endswith", "value": "a"}], sort={"column": "station"}),
        _base_request(filters=[{"column": "country", "op": "not_contains", "value": "us"}], sort={"column": "station"}),
        _base_request(filters=[{"column": "station", "op": "eq", "value": " BRAVO "}]),
    ]
    for request in requests:
        managed = service.preview_window(managed_ref, dict(request))
        direct = service.preview_window(direct_ref, dict(request))
        assert managed.metadata.get("query_backend") == "arrow"
        assert _stations(managed) == _stations(direct), request
        assert managed.total_rows == direct.total_rows, request


def test_preview_window_arrow_query_matches_python_scan_for_numeric_strings(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    source = tmp_path / "codes.csv"
    source.write_text("code,label\n100,A\n3,B\n20,C\n", encoding="utf-8")
    options = TabularLoadOptions(schema_hints={"code": "string"})
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    managed_ref = service.open_source(source, options)
    direct_ref = service.open_source(
        source,
        TabularLoadOptions(schema_hints={"code": "string"}, cache_policy="source_direct"),
    )

    request = _base_request(
        filters=[{"column": "code", "op": "gt", "value": "20"}],
        sort={"column": "code"},
    )

    managed = service.preview_window(managed_ref, request)
    direct = service.preview_window(direct_ref, request)

    assert managed.metadata.get("query_backend") == "arrow"
    assert managed.rows == direct.rows == ({"code": "100", "label": "A"},)
    assert managed.total_rows == direct.total_rows == 1


def test_preview_window_arrow_query_cache_skips_full_table_read_when_too_large(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pyarrow = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    source = tmp_path / "wide.parquet"
    pq.write_table(
        pyarrow.table(
            {
                "station": ["A", "B", "C"],
                "temp": [21.5, 22.0, 23.0],
                "payload": ["x" * 64, "y" * 64, "z" * 64],
            }
        ),
        source,
    )
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    monkeypatch.setattr(service, "_QUERY_TABLE_CACHE_MAX_BYTES", 1)
    original_read_table = pq.read_table
    read_columns: list[object] = []

    def tracking_read_table(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        read_columns.append(kwargs.get("columns"))
        return original_read_table(*args, **kwargs)

    monkeypatch.setattr(pq, "read_table", tracking_read_table)
    ref = service.open_source(source)

    window = service.preview_window(ref, _base_request(columns=["station", "temp"], sort={"column": "temp"}))

    assert _stations(window) == ["A", "B", "C"]
    assert read_columns == [["station", "temp"]]


def test_managed_cache_eviction_preserves_entry_returned_to_caller(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("pyarrow")
    source = tmp_path / "weather.csv"
    source.write_text("station,temp\nA,21.5\nB,22.0\n", encoding="utf-8")
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    original_enforce = service.enforce_cache_size_limit

    def tiny_enforce(*, preserve_paths=None):  # noqa: ANN001, ANN202
        return original_enforce(max_bytes=1, preserve_paths=preserve_paths)

    monkeypatch.setattr(service, "enforce_cache_size_limit", tiny_enforce)
    ref = service.open_source(source)

    window = service.window(ref, TabularWindowRequest(row_limit=2, column_limit=2))

    assert window.rows == ({"station": "A", "temp": 21.5}, {"station": "B", "temp": 22.0})
    assert list((tmp_path / "cache").glob("*/*.parquet"))


def test_preview_window_parquet_lane_or_reports_dependency(tmp_path: Path) -> None:
    source = tmp_path / "query.parquet"
    service = TabularLoaderCacheService(cache_dir=tmp_path / "cache")

    if not _module_available("pyarrow"):
        source.write_bytes(b"not parquet")
        with pytest.raises(MissingTabularDependencyError):
            service.scan_source(source)
        return

    _run_python_probe(
        """
        import sys
        from pathlib import Path

        import pyarrow
        import pyarrow.parquet as pq

        from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService

        root = Path(sys.argv[1])
        source = root / "query.parquet"
        pq.write_table(
            pyarrow.table(
                {
                    "station": ["Charlie", "alpha", "Bravo", "delta"],
                    "temp": [30.0, 21.5, 21.5, 9.0],
                    "country": ["US", "FR", "US", "DE"],
                }
            ),
            source,
        )
        service = TabularLoaderCacheService(cache_dir=root / "cache")
        ref = service.open_source(source)

        ascending = service.preview_window(ref, {"sort": {"column": "temp"}})
        filtered = service.preview_window(ref, {"filters": {"text": "US"}})

        assert [str(row["station"]) for row in ascending.rows] == ["delta", "alpha", "Bravo", "Charlie"]
        assert sorted(str(row["station"]) for row in filtered.rows) == ["Bravo", "Charlie"]
        assert filtered.total_rows == 2
        """,
        str(tmp_path),
    )
