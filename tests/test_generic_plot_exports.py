# Purpose: Prove full-fidelity Plot exports and managed artifact publication/cleanup.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_generic_plot_exports.py, tests/test_plot_headless_export.py
from __future__ import annotations

import builtins
import csv
import tempfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from ea_node_editor.addons.tabular_data.input_node import (
    TABULAR_DATA_ARRAY_OUTPUT_KEY,
    TABULAR_DATA_TABLE_OUTPUT_KEY,
    execute_tabular_input,
)
from ea_node_editor.execution import plot_backend
from ea_node_editor.execution.plot_backend import PlotRenderRequest
from ea_node_editor.execution.plot_backend_matplotlib import MATPLOTLIB_PLOT_BACKEND_ID
from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot, RuntimeSnapshotContext
from ea_node_editor.nodes import output_artifacts
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.plot import exports as plot_exports
from ea_node_editor.nodes.builtins.plot.specs import PLOT_NODE_DEFINITION_BY_TYPE_ID
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.runtime_contracts import (
    PATH_DATA_TYPE_ID,
    PLOT_EXPORT_BUNDLE_DATA_TYPE_ID,
    ArraySlice2DRef,
    TabularWindowRef,
)
from ea_node_editor.runtime_contracts.value_refs import RuntimeArtifactRef
from tests.generic_plot_fixtures import _execution_context, _generic_render_request, _tabular_input_context


@pytest.fixture
def archive_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Use real artifact storage with a lightweight observable export backend."""
    store = ProjectArtifactStore(project_path=None, metadata=None)
    store.ensure_staging_root(temporary_root_parent=tmp_path)
    resolver = ProjectArtifactResolver(project_path=None, artifact_store=store)
    ctx = _execution_context(
        runtime_snapshot_context=RuntimeSnapshotContext.from_snapshot(None, artifact_store=store),
        path_resolver=resolver.resolve_to_path,
    )
    events: list[str] = []

    def export_static(request):
        events.append("static")
        request.output_path.write_bytes(b"static")
        return plot_backend.PlotExportResult("test", request.output_path, request.format)

    def export_data(request):
        events.append("fallback")
        request.output_path.write_bytes(b"fallback")
        return plot_backend.PlotExportResult("test", request.output_path, request.format)

    backend = SimpleNamespace(export_static=export_static, export_data=export_data)
    monkeypatch.setattr(
        plot_backend,
        "create_plot_backend_registry",
        lambda: SimpleNamespace(resolve=lambda *_args, **_kwargs: backend),
    )
    return ctx, store, resolver, events


def test_window_export_preserves_admitted_columns_offset_and_effective_limit(
    tmp_path: Path,
    archive_environment,
) -> None:
    ctx, _store, resolver, events = archive_environment
    source = tmp_path / "window.csv"
    source.write_text("time,value,other\n0,10,100\n1,11,101\n2,12,102\n3,13,103\n", encoding="utf-8")
    table = execute_tabular_input(_tabular_input_context(source)).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]
    window = TabularWindowRef("window", table, row_offset=1, row_limit=3, columns=("time", "value", "other"))
    request = _generic_render_request(
        series_input=window,
        properties={"tabular_mapping": {"x": "time", "y": ["value"], "row_limit": 2}},
    )

    result = plot_exports.archive_plot_exports(
        ctx, request, {}, definition=PLOT_NODE_DEFINITION_BY_TYPE_ID["plot.bar"]
    )

    with resolver.resolve_to_path(result["data_export"].ref).open(newline="", encoding="utf-8") as stream:
        assert list(csv.reader(stream)) == [["time", "value", "other"], ["1", "11", "101"], ["2", "12", "102"]]
    assert events == ["static"]
    assert result["exports"]["data_metadata"]["backend_id"] == "tabular_full_fidelity"


def test_array_slice_export_scans_shared_provenance_once_and_streams_authored_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    archive_environment,
) -> None:
    from ea_node_editor.addons.tabular_data.loader_cache_service import shared_tabular_loader_cache_service

    numpy = pytest.importorskip("numpy")
    ctx, _store, resolver, events = archive_environment
    source = tmp_path / "sliced.npy"
    numpy.save(source, numpy.arange(4505 * 3).reshape(4505, 3))
    array = execute_tabular_input(_tabular_input_context(source)).outputs[TABULAR_DATA_ARRAY_OUTPUT_KEY]
    view = ArraySlice2DRef("slice", array, row_offset=2, row_limit=4500, column_offset=1, column_limit=2)
    request = _generic_render_request(series_input=view)
    comparisons = []

    class ObservedSource(dict):
        def __ne__(self, other):
            comparisons.append(other)
            return super().__ne__(other)

    provenance = ObservedSource(request.series[0]["source_ref"])
    series = {**request.series[0], "source_ref": provenance}
    request = replace(request, series=(series, series))
    service = shared_tabular_loader_cache_service()
    real_slice = service.slice_2d
    reads = []

    def observe_slice(ref, selection):
        reads.append(selection)
        return real_slice(ref, selection)

    monkeypatch.setattr(service, "slice_2d", observe_slice)
    result = plot_exports.archive_plot_exports(
        ctx, request, {}, definition=PLOT_NODE_DEFINITION_BY_TYPE_ID["plot.bar"]
    )

    assert len(comparisons) == 1
    assert [(read.row_offset, read.row_limit, read.column_offset, read.column_limit) for read in reads] == [
        (2, 4096, 1, 2), (4098, 404, 1, 2)
    ]
    with resolver.resolve_to_path(result["data_export"].ref).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows[0] == ["column_1", "column_2"]
    assert len(rows) == 4501
    assert rows[1] == ["7", "8"]
    assert rows[-1] == ["13504", "13505"]
    assert events == ["static"]


@pytest.mark.parametrize("case", ["missing", "mixed", "non_csv", "without_pyarrow"])
def test_ineligible_full_source_exports_fall_back_to_selected_data_backend(
    case: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    archive_environment,
) -> None:
    from ea_node_editor.addons.tabular_data.loader_cache_service import shared_tabular_loader_cache_service

    ctx, _store, resolver, events = archive_environment
    source = tmp_path / "fallback.csv"
    source.write_text("time,value\n0,10\n1,11\n", encoding="utf-8")
    table = execute_tabular_input(_tabular_input_context(source)).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]
    request = _generic_render_request(series_input=table)
    properties = {}
    if case == "missing":
        request = replace(request, series=({"values": [1, 2]},))
    elif case == "mixed":
        request = replace(request, series=(request.series[0], {
            **request.series[0],
            "source_ref": {**request.series[0]["source_ref"], "row_offset": 1},
        }))
    elif case == "non_csv":
        properties["data_export_format"] = "json"
    else:
        real_import = builtins.__import__

        def without_pyarrow(name, *args, **kwargs):
            if name == "pyarrow" or name.startswith("pyarrow."):
                raise ModuleNotFoundError(name)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", without_pyarrow)

    def unexpected_read(*_args, **_kwargs):
        raise AssertionError("fallback must not materialize the source")

    service = shared_tabular_loader_cache_service()
    monkeypatch.setattr(service, "arrow_batches", unexpected_read)
    monkeypatch.setattr(service, "slice_2d", unexpected_read)
    result = plot_exports.archive_plot_exports(
        ctx, request, properties, definition=PLOT_NODE_DEFINITION_BY_TYPE_ID["plot.bar"]
    )
    assert events == ["static", "fallback"]
    assert resolver.resolve_to_path(result["data_export"].ref).read_bytes() == b"fallback"
    assert result["exports"]["data_metadata"]["backend_id"] == "test"


def test_archive_base_exception_attempts_all_cleanup_stages_and_preserves_original(
    monkeypatch: pytest.MonkeyPatch,
    archive_environment,
) -> None:
    ctx, store, _resolver, events = archive_environment
    marker = KeyboardInterrupt("archive interrupted")

    def fail_registration(*_args, **_kwargs):
        monkeypatch.setattr(store, "discard_staged_entries", reject_entries)
        monkeypatch.setattr(store, "discard_staged_paths", reject_paths)
        monkeypatch.setattr(plot_exports, "persist_artifact_store", reject_persistence)
        raise marker

    def reject_entries(ids):
        assert len(ids) == 1
        events.append("entries")
        raise KeyboardInterrupt("entry cleanup interrupted")

    def reject_paths(paths):
        assert len(paths) == 1
        events.append("paths")
        raise KeyboardInterrupt("path cleanup interrupted")

    def reject_persistence(*_args):
        events.append("persist")
        raise KeyboardInterrupt("persistence interrupted")

    monkeypatch.setattr(plot_exports, "register_staged_path_artifact", fail_registration)

    with pytest.raises(KeyboardInterrupt) as caught:
        plot_exports.archive_plot_exports(
            ctx, PlotRenderRequest("bar", series=({"values": [1, 2]},)), {},
            definition=PLOT_NODE_DEFINITION_BY_TYPE_ID["plot.bar"],
        )
    assert caught.value is marker
    assert events == ["static", "entries", "paths", "persist"]


def test_generic_plot_node_archive_export_writes_static_and_data_artifacts() -> None:
    registry = build_default_registry()
    plugin = registry.create("plot.bar")

    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "plot_node_contracts.cxproj"
        runtime_snapshot = RuntimeSnapshot(schema_version=1, project_id="project_plot_contract", metadata={})
        artifact_store = ProjectArtifactStore.from_project_metadata(
            project_path=project_path,
            project_metadata=runtime_snapshot.metadata,
        )
        runtime_snapshot_context = RuntimeSnapshotContext.from_snapshot(
            runtime_snapshot,
            project_path=str(project_path),
            artifact_store=artifact_store,
        )
        resolver = ProjectArtifactResolver(project_path=project_path, artifact_store=artifact_store)
        properties = registry.normalize_properties(
            "plot.bar",
            {
                "title": "Archived Line",
                "archive_export_on_run": True,
                "static_export_format": "png",
                "data_export_format": "csv",
            },
        )

        result = plugin.execute(
            _execution_context(
                inputs={"series": {"label": "sample", "values": [1.0, 2.5, 4.0]}},
                properties=properties,
                project_path=project_path,
                runtime_snapshot=runtime_snapshot,
                runtime_snapshot_context=runtime_snapshot_context,
                path_resolver=resolver.resolve_to_path,
            )
        )

        static_ref = result.outputs["static_export"]
        data_ref = result.outputs["data_export"]
        assert isinstance(static_ref, RuntimeArtifactRef)
        assert isinstance(data_ref, RuntimeArtifactRef)
        assert static_ref.data_type_id == PATH_DATA_TYPE_ID
        assert data_ref.data_type_id == PATH_DATA_TYPE_ID
        assert static_ref.schema_version == 1
        assert data_ref.schema_version == 1
        assert static_ref.format == "png"
        assert data_ref.format == "csv"
        assert static_ref.metadata == {}
        assert data_ref.metadata == {}
        static_path = resolver.resolve_to_path(static_ref.ref)
        data_path = resolver.resolve_to_path(data_ref.ref)
        assert static_path is not None
        assert data_path is not None
        assert static_path.read_bytes().startswith(b"\x89PNG")
        assert "sample" in data_path.read_text(encoding="utf-8")
        assert result.outputs["exports"]["static_metadata"]["backend_id"] == MATPLOTLIB_PLOT_BACKEND_ID
        assert result.outputs["exports"]["data_metadata"]["metadata"]["row_count"] == 3
        registry.data_types.validate_output(PLOT_EXPORT_BUNDLE_DATA_TYPE_ID, result.outputs["exports"])


def test_generic_plot_archive_second_registration_failure_rolls_back_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ProjectArtifactStore(project_path=None, metadata=None)
    root = store.ensure_staging_root(temporary_root_parent=tmp_path)
    root_hint = store.metadata["staging_root"]
    sentinel = root / "unrelated.keep"
    sentinel.write_text("keep", encoding="utf-8")
    snapshot_context = RuntimeSnapshotContext.from_snapshot(
        None,
        artifact_store=store,
    )
    resolver = ProjectArtifactResolver(project_path=None, artifact_store=store)
    ctx = _execution_context(
        runtime_snapshot_context=snapshot_context,
        path_resolver=resolver.resolve_to_path,
    )

    def export_result(request):  # noqa: ANN001
        request.output_path.write_bytes(request.format.encode("ascii"))
        return SimpleNamespace(
            backend_id="test",
            format=request.format,
            metadata={},
        )

    backend = SimpleNamespace(
        export_static=export_result,
        export_data=export_result,
    )
    monkeypatch.setattr(
        plot_backend,
        "create_plot_backend_registry",
        lambda: SimpleNamespace(resolve=lambda *_args, **_kwargs: backend),
    )
    definition = PLOT_NODE_DEFINITION_BY_TYPE_ID["plot.bar"]
    request = PlotRenderRequest(
        plot_type="bar",
        series=({"label": "sample", "x": [0, 1], "y": [1.0, 2.0]},),
    )
    properties = {
        "backend": "auto",
        "static_export_format": "png",
        "data_export_format": "csv",
    }
    seeded = plot_exports.archive_plot_exports(ctx, request, properties, definition=definition)
    seeded_refs = (seeded["static_export"], seeded["data_export"])
    seeded_ids = tuple(ref.artifact_id for ref in seeded_refs)
    seeded_paths = tuple(store.resolve_staged_path(artifact_id) for artifact_id in seeded_ids)
    assert all(path is not None and path.is_file() for path in seeded_paths)
    seeded_entries = tuple(store.staged_entry(artifact_id) for artifact_id in seeded_ids)
    assert all(entry is not None for entry in seeded_entries)
    seeded_descriptors = tuple(
        entry.extra["runtime_artifact"]
        for entry in seeded_entries
        if entry is not None
    )

    unrelated_target = output_artifacts.allocate_managed_output(
        ctx,
        output_key="unrelated",
        default_suffix=".bin",
        managed_subdirectory="plots",
    )
    unrelated_target.path.write_bytes(b"unrelated bytes")
    unrelated_ref = output_artifacts.register_staged_path_artifact(
        ctx,
        store=store,
        artifact_id=unrelated_target.artifact_id,
        payload_path=unrelated_target.path,
        relative_path=unrelated_target.relative_path,
        slot=unrelated_target.slot,
        format=unrelated_target.format,
        entry_metadata=unrelated_target.entry_metadata,
    )
    unrelated_descriptor = store.staged_entry(unrelated_ref.artifact_id)
    assert unrelated_descriptor is not None
    unrelated_descriptor = unrelated_descriptor.extra["runtime_artifact"]

    real_register = plot_exports.register_staged_path_artifact
    attempted_ids: list[str] = []
    marker = RuntimeError("generic second registration marker")

    def fail_second_registration(context, **kwargs):  # noqa: ANN001
        runtime_ref = real_register(context, **kwargs)
        artifact_id = kwargs["artifact_id"]
        entry = store.staged_entry(artifact_id)
        assert entry is not None
        assert entry.extra["runtime_artifact"] == runtime_ref.to_descriptor()
        attempted_ids.append(artifact_id)
        if len(attempted_ids) == 2:
            raise marker
        return runtime_ref

    monkeypatch.setattr(
        plot_exports,
        "register_staged_path_artifact",
        fail_second_registration,
    )

    with pytest.raises(RuntimeError) as caught:
        plot_exports.archive_plot_exports(ctx, request, properties, definition=definition)

    assert caught.value is marker
    assert tuple(attempted_ids) == seeded_ids
    assert all(store.staged_entry(artifact_id) is None for artifact_id in seeded_ids)
    assert all(path is not None and not path.exists() for path in seeded_paths)
    remaining_staged = store.metadata.get("staged", {})
    assert set(remaining_staged) == {unrelated_ref.artifact_id}
    remaining_descriptors = tuple(
        entry["runtime_artifact"]
        for entry in remaining_staged.values()
    )
    assert all(descriptor not in remaining_descriptors for descriptor in seeded_descriptors)
    assert store.staged_entry(unrelated_ref.artifact_id).extra["runtime_artifact"] == unrelated_descriptor
    assert unrelated_target.path.read_bytes() == b"unrelated bytes"
    assert store.active_staging_root() == root
    assert store.metadata["staging_root"] == root_hint
    assert sentinel.read_text(encoding="utf-8") == "keep"

    monkeypatch.setattr(
        plot_exports,
        "register_staged_path_artifact",
        real_register,
    )
    strict_seeded = plot_exports.archive_plot_exports(ctx, request, properties, definition=definition)
    strict_ids = (
        strict_seeded["static_export"].artifact_id,
        strict_seeded["data_export"].artifact_id,
    )
    strict_paths = tuple(store.resolve_staged_path(artifact_id) for artifact_id in strict_ids)
    assert all(path is not None and path.is_file() for path in strict_paths)

    strict_marker = RuntimeError("generic strict cleanup marker")
    strict_attempted_ids: list[str] = []
    strict_relative_paths: list[str] = []
    discard_entry_calls: list[tuple[str, ...]] = []
    discard_path_calls: list[tuple[str, ...]] = []
    raw_unlink_calls: list[Path] = []
    real_discard_paths = store.discard_staged_paths
    cleanup_patch = pytest.MonkeyPatch()

    def reject_registered_entries(artifact_ids):  # noqa: ANN001
        discard_entry_calls.append(tuple(artifact_ids))
        raise ValueError("strict entry cleanup rejection")

    def strict_discard_paths(relative_paths):  # noqa: ANN001
        requested = tuple(relative_paths)
        discard_path_calls.append(requested)
        return real_discard_paths(requested)

    def reject_raw_unlink(path, *_args, **_kwargs):  # noqa: ANN001
        raw_unlink_calls.append(Path(path))
        raise AssertionError("raw unlink bypassed store validation")

    def fail_after_strict_registration(context, **kwargs):  # noqa: ANN001
        runtime_ref = real_register(context, **kwargs)
        artifact_id = kwargs["artifact_id"]
        entry = store.staged_entry(artifact_id)
        assert entry is not None
        assert entry.extra["runtime_artifact"] == runtime_ref.to_descriptor()
        strict_attempted_ids.append(artifact_id)
        strict_relative_paths.append(kwargs["relative_path"])
        if len(strict_attempted_ids) == 2:
            cleanup_patch.setattr(
                store,
                "discard_staged_entries",
                reject_registered_entries,
            )
            cleanup_patch.setattr(
                store,
                "discard_staged_paths",
                strict_discard_paths,
            )
            cleanup_patch.setattr(Path, "unlink", reject_raw_unlink)
            raise strict_marker
        return runtime_ref

    monkeypatch.setattr(
        plot_exports,
        "register_staged_path_artifact",
        fail_after_strict_registration,
    )
    try:
        with pytest.raises(RuntimeError) as strict_caught:
            plot_exports.archive_plot_exports(ctx, request, properties, definition=definition)
    finally:
        cleanup_patch.undo()

    assert strict_caught.value is strict_marker
    assert tuple(strict_attempted_ids) == strict_ids
    assert discard_entry_calls == [strict_ids]
    assert discard_path_calls == [tuple(strict_relative_paths)]
    assert raw_unlink_calls == []
    assert all(store.staged_entry(artifact_id) is not None for artifact_id in strict_ids)
    assert all(path is not None and path.is_file() for path in strict_paths)
    assert set(store.metadata.get("staged", {})) == {
        *strict_ids,
        unrelated_ref.artifact_id,
    }
    assert unrelated_target.path.read_bytes() == b"unrelated bytes"
    assert store.active_staging_root() == root
    assert store.metadata["staging_root"] == root_hint
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_tabular_plot_archive_export_streams_all_source_columns(tmp_path: Path) -> None:
    registry = build_default_registry()
    plugin = registry.create("plot.bar")
    project_path = tmp_path / "plot_full_source_export.cxproj"
    source = tmp_path / "weather.csv"
    rows = ["time,temp,pressure"]
    rows.extend(f"{index},{20.0 + index * 0.01:.2f},{100.0 + index * 0.1:.1f}" for index in range(4500))
    source.write_text("\n".join(rows) + "\n", encoding="utf-8")
    runtime_snapshot = RuntimeSnapshot(schema_version=1, project_id="project_plot_contract", metadata={})
    artifact_store = ProjectArtifactStore.from_project_metadata(
        project_path=project_path,
        project_metadata=runtime_snapshot.metadata,
    )
    runtime_snapshot_context = RuntimeSnapshotContext.from_snapshot(
        runtime_snapshot,
        project_path=str(project_path),
        artifact_store=artifact_store,
    )
    resolver = ProjectArtifactResolver(project_path=project_path, artifact_store=artifact_store)
    table_ref = execute_tabular_input(
        _tabular_input_context(source)
    ).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]
    properties = registry.normalize_properties(
        "plot.bar",
        {
            "archive_export_on_run": True,
            "data_export_format": "csv",
            "tabular_mapping": {"x": "time", "y": ["temp"]},
        },
    )

    result = plugin.execute(
        _execution_context(
            inputs={"series": table_ref},
            properties=properties,
            project_path=project_path,
            runtime_snapshot=runtime_snapshot,
            runtime_snapshot_context=runtime_snapshot_context,
            path_resolver=resolver.resolve_to_path,
        )
    )

    data_path = resolver.resolve_to_path(result.outputs["data_export"].ref)
    assert data_path is not None
    exported_lines = data_path.read_text(encoding="utf-8").splitlines()
    assert exported_lines[0] == '"time","temp","pressure"'
    assert len(exported_lines) == 4501
    metadata = result.outputs["exports"]["data_metadata"]
    assert metadata["backend_id"] == "tabular_full_fidelity"
    assert metadata["metadata"]["row_count"] == 4500
    assert metadata["metadata"]["column_count"] == 3
    assert metadata["metadata"]["columns"] == ["time", "temp", "pressure"]


def test_array_plot_archive_export_streams_all_source_rows(tmp_path: Path) -> None:
    numpy = pytest.importorskip("numpy")
    registry = build_default_registry()
    plugin = registry.create("plot.bar")
    project_path = tmp_path / "plot_array_full_source_export.cxproj"
    source = tmp_path / "points.npy"
    numpy.save(source, numpy.array([[float(index), float(index * 2)] for index in range(4500)]))
    runtime_snapshot = RuntimeSnapshot(schema_version=1, project_id="project_plot_contract", metadata={})
    artifact_store = ProjectArtifactStore.from_project_metadata(
        project_path=project_path,
        project_metadata=runtime_snapshot.metadata,
    )
    runtime_snapshot_context = RuntimeSnapshotContext.from_snapshot(
        runtime_snapshot,
        project_path=str(project_path),
        artifact_store=artifact_store,
    )
    resolver = ProjectArtifactResolver(project_path=project_path, artifact_store=artifact_store)
    array_ref = execute_tabular_input(
        _tabular_input_context(source, array_slice_2d={"row_limit": 4500, "column_limit": 2})
    ).outputs[TABULAR_DATA_ARRAY_OUTPUT_KEY]
    properties = registry.normalize_properties(
        "plot.bar",
        {
            "archive_export_on_run": True,
            "data_export_format": "csv",
        },
    )

    result = plugin.execute(
        _execution_context(
            inputs={"series": array_ref},
            properties=properties,
            project_path=project_path,
            runtime_snapshot=runtime_snapshot,
            runtime_snapshot_context=runtime_snapshot_context,
            path_resolver=resolver.resolve_to_path,
            node_type_id="plot.bar",
        )
    )

    data_path = resolver.resolve_to_path(result.outputs["data_export"].ref)
    assert data_path is not None
    exported_lines = data_path.read_text(encoding="utf-8").splitlines()
    assert exported_lines[0] == "column_1,column_2"
    assert len(exported_lines) == 4501
    metadata = result.outputs["exports"]["data_metadata"]
    assert metadata["backend_id"] == "array_full_fidelity"
    assert metadata["metadata"]["row_count"] == 4500
    assert metadata["metadata"]["column_count"] == 2
