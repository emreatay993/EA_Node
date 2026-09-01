from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ea_node_editor.addons.ansys_dpf.plot_catalog import (
    load_ansys_dpf_plot_plugin_descriptors,
)
from ea_node_editor.execution.plot_backend import (
    PlotRenderRequest,
    normalize_dpf_plot_frame_selector,
)
from ea_node_editor.execution import plot_backend
from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshotContext
from ea_node_editor.execution.worker_services import WorkerServices
from tests.typed_handle_support import dpf_worker_services
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes import output_artifacts
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MESH_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
)
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.plot import dpf as dpf_plot
from ea_node_editor.nodes.builtins.plot.dpf import (
    DPF_PLOT_ANIMATE_PROPERTY,
    DPF_PLOT_CATEGORY_PATH,
    DPF_PLOT_FRAME_SELECTOR_PROPERTY,
    DPF_PLOT_NODE_TYPE_IDS,
)
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.ui_qml.graph_scene_payload import GraphScenePayloadBuilder

EXPECTED_DPF_PLOT_TYPE_IDS = (
    "dpf.plot.line",
    "dpf.plot.scatter",
    "dpf.plot.bar",
    "dpf.plot.histogram",
    "dpf.plot.heatmap",
    "dpf.plot.contour",
    "dpf.plot.surface",
    "dpf.plot.point_cloud",
    "dpf.plot.streamlines",
)


class _FakeField:
    def __init__(
        self,
        data,
        *,  # noqa: ANN001
        ids: list[int] | None = None,
        location: str = "Nodal",
        unit: str = "mm",
    ) -> None:
        self.data = data
        self.location = location
        self.unit = unit
        self.component_count = len(data[0]) if data and isinstance(data[0], list) else 1
        self.scoping = SimpleNamespace(ids=list(ids or range(1, len(data) + 1)), size=len(data))


class _FakeFieldsContainer:
    labels = ("time",)

    def __init__(self, fields: list[_FakeField], label_spaces: list[dict[str, int]]) -> None:
        self._fields = list(fields)
        self._label_spaces = [dict(item) for item in label_spaces]

    def __len__(self) -> int:
        return len(self._fields)

    def __getitem__(self, index: int) -> _FakeField:
        return self._fields[index]

    def get_label_space(self, index: int) -> dict[str, int]:
        return dict(self._label_spaces[index])


class _FakeMesh:
    unit = "mm"

    def __init__(self) -> None:
        self.nodes = SimpleNamespace(
            n_nodes=3,
            coordinates_field=SimpleNamespace(data=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]]),
        )
        self.elements = SimpleNamespace(n_elements=1)


class _PlotGraphThemeBridge:
    theme = "graph_stitch_dark"

    def parent(self) -> object | None:
        return None


def _descriptor(type_id: str):
    return next(
        descriptor
        for descriptor in load_ansys_dpf_plot_plugin_descriptors()
        if descriptor.spec.type_id == type_id
    )


def _execution_context(
    *,
    inputs: dict[str, object] | None = None,
    properties: dict[str, object] | None = None,
    services: WorkerServices | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        run_id="run_dpf_plot_contract",
        node_id="node_dpf_plot",
        workspace_id="ws_dpf_plot",
        inputs=dict(inputs or {}),
        properties=dict(properties or {}),
        emit_log=lambda _level, _message: None,
        worker_services=services or dpf_worker_services(),
    )


def test_dpf_plot_catalog_declares_v1_mirrors_and_typed_ports() -> None:
    descriptors = load_ansys_dpf_plot_plugin_descriptors()

    assert DPF_PLOT_NODE_TYPE_IDS == EXPECTED_DPF_PLOT_TYPE_IDS
    assert tuple(descriptor.spec.type_id for descriptor in descriptors) == EXPECTED_DPF_PLOT_TYPE_IDS
    for descriptor in descriptors:
        spec = descriptor.spec
        assert spec.category_path == DPF_PLOT_CATEGORY_PATH
        assert spec.category_path == ("Ansys DPF", "Plot")
        assert spec.runtime_behavior == "active"
        assert spec.surface_family == "standard"
        assert spec.surface_variant == spec.type_id.removeprefix("dpf.plot.")
        assert "DPF Field handles" in spec.description
        assert "DPF FieldsContainer handles" in spec.description

        ports = {port.key: port for port in spec.ports}
        assert ports["series"].data_type == DPF_FIELDS_CONTAINER_DATA_TYPE
        assert ports["series"].accepted_data_types == (DPF_FIELD_DATA_TYPE, DPF_FIELDS_CONTAINER_DATA_TYPE)
        assert ports["series"].required
        assert ports["series"].data_access == "list"
        assert not ports["series"].allow_multiple_connections
        assert ports["mesh"].data_type == DPF_MESH_DATA_TYPE
        assert ports["scoping"].data_type == DPF_SCOPING_DATA_TYPE
        assert "render_request" not in ports
        assert ports["static_export"].label == "Image Export"

        properties = {prop.key: prop for prop in spec.properties}
        assert properties[DPF_PLOT_FRAME_SELECTOR_PROPERTY].default == "1"
        assert properties[DPF_PLOT_FRAME_SELECTOR_PROPERTY].type == "str"
        assert properties[DPF_PLOT_ANIMATE_PROPERTY].default is False
        assert properties[DPF_PLOT_ANIMATE_PROPERTY].type == "bool"
        assert properties["static_export_format"].label == "Image Export Format"


def test_dpf_plot_frame_selector_resolves_time_label_spaces() -> None:
    selection = normalize_dpf_plot_frame_selector(
        "3",
        frame_count=2,
        label_spaces=({"time": 1}, {"time": 3}),
    )

    assert selection.selected_indices == (1,)
    assert selection.selected_set_ids == (3,)
    assert selection.available_set_ids == (1, 3)


def test_dpf_plot_field_handle_builds_internal_render_request() -> None:
    services = dpf_worker_services()
    field_ref = services.register_handle(
        _FakeField([1.0, 2.5, 4.0], ids=[10, 20, 30]),
        data_type_id=DPF_FIELD_DATA_TYPE,
        kind=DPF_FIELD_HANDLE_KIND,
        run_id="run_dpf_plot_contract",
        metadata={"result_name": "displacement", "set_id": 1},
    )
    plugin = _descriptor("dpf.plot.line").factory()

    ctx = _execution_context(
        inputs={"series": field_ref},
        properties={"title": "DPF Line", "x_label": "node", "y_label": "U"},
        services=services,
    )
    result = plugin.execute(ctx)
    render_request, _properties = plugin._build_render_request(ctx)  # noqa: SLF001

    assert result.outputs == {}
    assert isinstance(render_request, PlotRenderRequest)
    assert render_request.plot_type == "line"
    assert render_request.title == "DPF Line"
    assert render_request.series == (
        {
            "label": "displacement set 1",
            "x": [10, 20, 30],
            "y": [1.0, 2.5, 4.0],
            "values": [1.0, 2.5, 4.0],
            "metadata": {
                "result_name": "displacement",
                "set_id": 1,
                "series_index": 0,
                "location": "Nodal",
                "component_count": 1,
                "entity_count": 3,
                "unit": "mm",
                "source_handle_id": field_ref.handle_id,
                "source_handle_kind": DPF_FIELD_HANDLE_KIND,
            },
        },
    )
    assert render_request.options["dpf"]["family"] == "dpf.plot"
    assert render_request.options["dpf"]["selected_frame_count"] == 1


def test_dpf_plot_fields_container_uses_frame_selector_and_animation_metadata() -> None:
    services = dpf_worker_services()
    fields_container_ref = services.register_handle(
        _FakeFieldsContainer(
            [
                _FakeField([1.0, 2.0], ids=[1, 2]),
                _FakeField([3.0, 5.0], ids=[1, 2]),
            ],
            [{"time": 1}, {"time": 3}],
        ),
        data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
        kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        run_id="run_dpf_plot_contract",
        metadata={"result_name": "stress"},
    )
    plugin = _descriptor("dpf.plot.scatter").factory()

    ctx = _execution_context(
        inputs={"series": fields_container_ref},
        properties={DPF_PLOT_FRAME_SELECTOR_PROPERTY: "3", DPF_PLOT_ANIMATE_PROPERTY: True},
        services=services,
    )
    render_request, _properties = plugin._build_render_request(ctx)  # noqa: SLF001

    assert render_request.series[0]["values"] == [3.0, 5.0]
    assert render_request.series[0]["metadata"]["frame_index"] == 1
    assert render_request.series[0]["metadata"]["set_id"] == 3
    assert render_request.options["animate"] is True
    assert render_request.options["dpf"]["animation"] == {
        "enabled": True,
        "frames": [
            {"frame_index": 0, "set_id": 1, "label_space": {"time": 1}},
            {"frame_index": 1, "set_id": 3, "label_space": {"time": 3}},
        ],
        "frame_count": 2,
    }


def test_dpf_point_cloud_plot_adapts_mesh_and_scoping_metadata() -> None:
    services = dpf_worker_services()
    field_ref = services.register_handle(
        _FakeField([[0.1], [0.2], [0.3]], ids=[1, 2, 3]),
        data_type_id=DPF_FIELD_DATA_TYPE,
        kind=DPF_FIELD_HANDLE_KIND,
        run_id="run_dpf_plot_contract",
        metadata={"result_name": "temperature"},
    )
    mesh_ref = services.register_handle(
        _FakeMesh(),
        data_type_id=DPF_MESH_DATA_TYPE,
        kind=DPF_MESH_HANDLE_KIND,
        run_id="run_dpf_plot_contract",
        metadata={"model_handle_id": "model-1"},
    )
    scoping_ref = services.register_handle(
        SimpleNamespace(ids=[1, 2, 3], location="Nodal"),
        data_type_id=DPF_SCOPING_DATA_TYPE,
        kind=DPF_MESH_SCOPING_HANDLE_KIND,
        run_id="run_dpf_plot_contract",
        metadata={"ids": [1, 2, 3], "location": "Nodal"},
    )
    plugin = _descriptor("dpf.plot.point_cloud").factory()

    ctx = _execution_context(
        inputs={"series": field_ref, "mesh": mesh_ref, "scoping": scoping_ref},
        services=services,
    )
    render_request, _properties = plugin._build_render_request(ctx)  # noqa: SLF001

    assert render_request.plot_type == "point_cloud"
    assert render_request.series[0]["points"] == [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
    ]
    assert render_request.series[0]["scalars"] == [0.1, 0.2, 0.3]
    assert render_request.options["dpf"]["mesh"]["handle_id"] == mesh_ref.handle_id
    assert render_request.options["dpf"]["mesh"]["node_count"] == 3
    assert render_request.options["dpf"]["scoping"]["handle_id"] == scoping_ref.handle_id
    assert render_request.options["dpf"]["scoping"]["ids"] == [1, 2, 3]


def test_dpf_plot_scene_payload_publishes_plot_surface_and_animation_properties() -> None:
    registry = build_default_registry()
    if registry.spec_or_none("dpf.plot.scatter") is None:
        pytest.skip("ansys.dpf.core is not installed")
    model = GraphModel()
    workspace_id = model.active_workspace.workspace_id
    node = model.add_node(
        workspace_id,
        "dpf.plot.scatter",
        "DPF Scatter Plot",
        64.0,
        96.0,
        properties={
            "render_in_canvas": True,
            DPF_PLOT_FRAME_SELECTOR_PROPERTY: "all",
            DPF_PLOT_ANIMATE_PROPERTY: True,
        },
    )

    nodes_payload, _minimap_payload, _edges_payload = GraphScenePayloadBuilder().rebuild_models(
        model=model,
        registry=registry,
        workspace_id=workspace_id,
        scope_path=(),
        graph_theme_bridge=_PlotGraphThemeBridge(),
    )
    payload = next(item for item in nodes_payload if item["node_id"] == node.node_id)

    assert payload["surface_family"] == "plot"
    assert payload["surface_variant"] == "scatter"
    assert payload["plot_surface"]["plot_type"] == "scatter"
    assert payload["plot_surface"]["live_backend_id"] == "pyqtgraph"
    assert payload["plot_surface"]["embedded_rendering_suppressed"] is False
    assert payload["properties"][DPF_PLOT_FRAME_SELECTOR_PROPERTY] == "all"
    assert payload["properties"][DPF_PLOT_ANIMATE_PROPERTY] is True


def test_dpf_plot_time_history_metadata_drives_time_axis_and_entity_labels() -> None:
    services = dpf_worker_services()
    container = _FakeFieldsContainer(
        [
            _FakeField([1.0, 2.0], ids=[1, 2]),
            _FakeField([3.0, 5.0], ids=[1, 2]),
        ],
        [{"entity": 11175}, {"entity": 11176}],
    )
    container.labels = ("entity",)
    series_ref = services.register_handle(
        container,
        data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
        kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        run_id="run_dpf_plot_contract",
        metadata={
            "result_name": "displacement",
            "operation": "time_history",
            "x_axis": "time",
            "time_values": [0.5, 1.5],
            "entity_ids": [11175, 11176],
        },
    )
    plugin = _descriptor("dpf.plot.line").factory()

    ctx = _execution_context(
        inputs={"series": series_ref},
        properties={DPF_PLOT_FRAME_SELECTOR_PROPERTY: "all"},
        services=services,
    )
    render_request, _properties = plugin._build_render_request(ctx)  # noqa: SLF001

    assert len(render_request.series) == 2
    assert render_request.series[0]["x"] == [0.5, 1.5]
    assert render_request.series[1]["x"] == [0.5, 1.5]
    assert render_request.series[0]["label"] == "displacement time_history entity 11175"
    assert render_request.series[1]["label"] == "displacement time_history entity 11176"


def test_dpf_plot_time_axis_metadata_requires_marker_and_length_match() -> None:
    services = dpf_worker_services()
    mismatched_ref = services.register_handle(
        _FakeFieldsContainer(
            [_FakeField([1.0, 2.0], ids=[7, 9])],
            [{"time": 1}],
        ),
        data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
        kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        run_id="run_dpf_plot_contract",
        metadata={"result_name": "displacement", "x_axis": "time", "time_values": [0.5]},
    )
    unmarked_ref = services.register_handle(
        _FakeFieldsContainer(
            [_FakeField([1.0, 2.0], ids=[7, 9])],
            [{"time": 1}],
        ),
        data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
        kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        run_id="run_dpf_plot_contract",
        metadata={"result_name": "displacement", "time_values": [0.5, 1.5]},
    )
    plugin = _descriptor("dpf.plot.line").factory()

    for series_ref in (mismatched_ref, unmarked_ref):
        ctx = _execution_context(
            inputs={"series": series_ref},
            properties={DPF_PLOT_FRAME_SELECTOR_PROPERTY: "all"},
            services=services,
        )
        render_request, _properties = plugin._build_render_request(ctx)  # noqa: SLF001
        assert render_request.series[0]["x"] == [7, 9]


def test_dpf_plot_archive_second_registration_failure_rolls_back_pair(
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
    ctx = ExecutionContext(
        run_id="run_dpf_plot_rollback",
        node_id="node_dpf_plot",
        workspace_id="ws_dpf_plot",
        inputs={},
        properties={},
        emit_log=lambda _level, _message: None,
        runtime_snapshot_context=snapshot_context,
        path_resolver=resolver.resolve_to_path,
        worker_services=dpf_worker_services(),
        node_type_id="dpf.plot.line",
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
    plugin = _descriptor("dpf.plot.line").factory()
    request = PlotRenderRequest(
        plot_type="line",
        series=({"label": "sample", "x": [0, 1], "y": [1.0, 2.0]},),
    )
    properties = {
        "backend": "auto",
        "static_export_format": "png",
        "data_export_format": "csv",
    }
    seeded = plugin._archive_exports(ctx, request, properties)  # noqa: SLF001
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

    real_register = dpf_plot.register_staged_path_artifact
    attempted_ids: list[str] = []
    marker = RuntimeError("DPF second registration marker")

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
        dpf_plot,
        "register_staged_path_artifact",
        fail_second_registration,
    )

    with pytest.raises(RuntimeError) as caught:
        plugin._archive_exports(ctx, request, properties)  # noqa: SLF001

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
        dpf_plot,
        "register_staged_path_artifact",
        real_register,
    )
    strict_seeded = plugin._archive_exports(ctx, request, properties)  # noqa: SLF001
    strict_ids = (
        strict_seeded["static_export"].artifact_id,
        strict_seeded["data_export"].artifact_id,
    )
    strict_paths = tuple(store.resolve_staged_path(artifact_id) for artifact_id in strict_ids)
    assert all(path is not None and path.is_file() for path in strict_paths)

    strict_marker = RuntimeError("DPF strict cleanup marker")
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
        dpf_plot,
        "register_staged_path_artifact",
        fail_after_strict_registration,
    )
    try:
        with pytest.raises(RuntimeError) as strict_caught:
            plugin._archive_exports(ctx, request, properties)  # noqa: SLF001
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
