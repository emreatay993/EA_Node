# Purpose: Prove Plot scene projection, preview invalidation and real QML surface interactions.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_surface_integration.py
# Landmarks: scene payload helpers and assertions; PlotSurfaceInteractionQmlTests
from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

import pytest

from ea_node_editor.execution.plot_backend_matplotlib import MATPLOTLIB_PLOT_BACKEND_ID
from ea_node_editor.execution.plot_backend_pyqtgraph import PYQTGRAPH_PLOT_BACKEND_ID
from ea_node_editor.execution.plot_backend_pyvista import PYVISTA_PLOT_BACKEND_ID

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.graph_scene_payload import GraphScenePayloadBuilder
from ea_node_editor.ui_qml.surface_contracts import surface_spec_payload_for_values
from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    run_qml_probe,
)


class _PlotGraphThemeBridge:
    theme_id = "graph_stitch_dark"

    def __init__(self, *, lightweight_canvas: bool = False) -> None:
        self._parent = SimpleNamespace(graphics_lightweight_canvas=bool(lightweight_canvas))

    def parent(self) -> object:
        return self._parent


def _plot_scene_payload(
    *,
    type_id: str = "plot.bar",
    properties: dict[str, object] | None = None,
    lightweight_canvas: bool = False,
) -> dict[str, object]:
    model = GraphModel()
    registry = build_default_registry()
    workspace_id = model.active_workspace.workspace_id
    node = model.add_node(
        workspace_id,
        type_id,
        registry.get_spec(type_id).display_name,
        64.0,
        96.0,
        properties=properties,
    )
    nodes_payload, _minimap_payload, _edges_payload = GraphScenePayloadBuilder().rebuild_models(
        model=model,
        registry=registry,
        workspace_id=workspace_id,
        scope_path=(),
        graph_theme_bridge=_PlotGraphThemeBridge(lightweight_canvas=lightweight_canvas),
        lightweight_canvas=lightweight_canvas,
    )
    return next(item for item in nodes_payload if item["node_id"] == node.node_id)


def test_plot_nodes_publish_plot_surface_spec_for_live_2d_canvas() -> None:
    payload = _plot_scene_payload(properties={"render_in_canvas": True})

    assert payload["surface_family"] == "plot"
    assert payload["surface_variant"] == "bar"
    assert payload["surface_spec"] == surface_spec_payload_for_values(
        type_id="plot.bar",
        family="plot",
        variant="scatter",
    )
    assert payload["surface_spec"]["component_key"] == "plot"
    assert payload["surface_spec"]["qml_component"] == "plot/GraphPlotSurface.qml"
    assert payload["surface_spec"]["fullscreen"]["content_kind"] == "plot"
    assert payload["surface_spec"]["native_overlay"] == {
        "required": True,
        "target": "body",
        "owner": "plot_host",
    }


def test_plot_surface_payload_preserves_p03_sink_mode_contract() -> None:
    default_payload = _plot_scene_payload()
    disabled_payload = _plot_scene_payload(properties={"render_in_canvas": False})
    enabled_payload = _plot_scene_payload(properties={"render_in_canvas": True})
    lightweight_payload = _plot_scene_payload(
        properties={"render_in_canvas": True},
        lightweight_canvas=True,
    )

    assert default_payload["plot_surface"] == {
        "plot_type": "bar",
        "live_backend_id": "pyqtgraph",
        "render_in_canvas": True,
        "lightweight_canvas": False,
        "embedded_rendering_suppressed": False,
        "embedded_rendering_suppressed_by": [],
    }
    assert default_payload["embedded_rendering_suppressed"] is False
    assert default_payload["embedded_rendering_suppressed_by"] == []
    assert disabled_payload["plot_surface"]["embedded_rendering_suppressed"] is True
    assert disabled_payload["embedded_rendering_suppressed_by"] == ["render_in_canvas"]
    assert enabled_payload["plot_surface"]["embedded_rendering_suppressed"] is False
    assert enabled_payload["embedded_rendering_suppressed_by"] == []

    assert disabled_payload["plot_surface"]["embedded_rendering_suppressed_by"] == ["render_in_canvas"]
    assert lightweight_payload["plot_surface"]["embedded_rendering_suppressed"] is True
    assert lightweight_payload["plot_surface"]["embedded_rendering_suppressed_by"] == [
        "lightweight_canvas"
    ]


def test_plot_surface_exposes_detached_window_action_contract_without_session_action() -> None:
    surface_source = (
        Path(__file__).resolve().parents[1]
        / "ea_node_editor"
        / "ui_qml"
        / "components"
        / "graph"
        / "plot"
        / "GraphPlotSurfaceBody.qml"
    ).read_text(encoding="utf-8")

    assert '"id": "plot_detach"' in surface_source
    assert '"kind": "plot"' in surface_source
    assert "requestDetachedWindow" in surface_source
    assert "open_detached_plot(surface.plotNodeId)" in surface_source
    assert '"id": "plot_add_to_session"' not in surface_source
    assert "requestPlotSession" not in surface_source
    assert "add_plot_to_session(surface.plotNodeId)" not in surface_source


def test_plot_surface_keeps_original_inline_live_preview_policy() -> None:
    surface_source = (
        Path(__file__).resolve().parents[1]
        / "ea_node_editor"
        / "ui_qml"
        / "components"
        / "graph"
        / "plot"
        / "GraphPlotSurfaceBody.qml"
    ).read_text(encoding="utf-8")

    assert "surface.hostSurfaceActive || surface.viewportHoverActive || autoPreviewPulse.running" in surface_source
    assert "auto_preview_active" in surface_source
    assert "readonly property string plotLiveBackendId" in surface_source
    assert 'plotLiveBackendId === "pyqtgraph"' in surface_source
    assert "readonly property bool liveSurfaceSizeViable" in surface_source
    assert "&& surface.liveSurfaceSizeViable" in surface_source
    assert "host.currentViewportZoom()" in surface_source
    assert "readonly property bool externalPresentationActive" not in surface_source
    assert "session_plot_active(surface.plotNodeId)" not in surface_source
    assert "onExternalPresentationActiveChanged" not in surface_source


def test_plot_surface_prefers_cached_real_preview_over_spline_placeholder() -> None:
    surface_source = (
        Path(__file__).resolve().parents[1]
        / "ea_node_editor"
        / "ui_qml"
        / "components"
        / "graph"
        / "plot"
        / "GraphPlotSurfaceBody.qml"
    ).read_text(encoding="utf-8")

    assert "readonly property string cachedPreviewSource" in surface_source
    assert "readonly property bool cachedPreviewVisible" in surface_source
    assert "readonly property bool contentFullscreenOpen" in surface_source
    assert "cached_preview_source(surface.plotNodeId)" in surface_source
    assert "embedded_live_overlay_ready(surface.plotNodeId)" in surface_source
    assert "plot_overlay_revision" in surface_source
    assert "readonly property bool liveOverlayReady" in surface_source
    assert "readonly property bool proxySurfaceActive: !surface.liveOverlayReady" in surface_source
    assert "readonly property bool placeholderPreviewVisible" in surface_source
    assert 'objectName: "graphNodePlotCachedPreviewImage"' in surface_source
    assert 'source: surface._cachedPreviewImageSource' in surface_source
    assert "_clearCachedPreviewImage" in surface_source
    assert "cache: false" in surface_source
    assert "visible: surface.placeholderPreviewVisible" in surface_source


def _connected_tabular_plot_model(tmp_path: Path, *, filename: str = "weather.csv"):
    source = tmp_path / filename
    source.write_text("time,temp\n0,21.5\n1,22.0\n", encoding="utf-8")
    model = GraphModel()
    registry = build_default_registry()
    workspace_id = model.active_workspace.workspace_id
    tabular = model.add_node(
        workspace_id,
        "tabular.input",
        "Tabular",
        32.0,
        64.0,
        properties={"path": str(source)},
    )
    plot = model.add_node(
        workspace_id,
        "plot.bar",
        "Bar Plot",
        360.0,
        64.0,
        properties={"tabular_mapping": {"x": "time", "y": ["temp"]}},
    )
    edge = model.add_edge(workspace_id, tabular.node_id, "table_data", plot.node_id, "series")
    return source, model, registry, workspace_id, tabular, plot, edge


def _full_plot_payload(
    model: GraphModel,
    registry,
    workspace_id: str,
    plot_node_id: str,
) -> dict[str, object]:
    nodes_payload, _minimap_payload, _edges_payload = GraphScenePayloadBuilder().rebuild_models(
        model=model,
        registry=registry,
        workspace_id=workspace_id,
        scope_path=(),
        graph_theme_bridge=_PlotGraphThemeBridge(),
    )
    return next(item for item in nodes_payload if item["node_id"] == plot_node_id)


def _targeted_plot_payload(
    model: GraphModel,
    registry,
    workspace_id: str,
    plot_node_id: str,
    *,
    previous_payload: dict[str, object],
    changed_fields: set[str] | None,
) -> dict[str, object]:
    nodes_payload, _backdrop_nodes_payload, _minimap_payload = (
        GraphScenePayloadBuilder().build_node_payloads_for_ids(
            model=model,
            registry=registry,
            workspace_id=workspace_id,
            scope_path=(),
            node_ids={plot_node_id},
            graph_theme_bridge=_PlotGraphThemeBridge(),
            previous_payloads_by_id={plot_node_id: previous_payload},
            changed_fields_by_node_id=(
                {plot_node_id: changed_fields} if changed_fields is not None else None
            ),
        )
    )
    return next(item for item in nodes_payload if item["node_id"] == plot_node_id)


def test_generic_plot_scene_payload_reports_resolved_live_backend_id() -> None:
    line_payload = _plot_scene_payload(type_id="plot.bar")
    surface_payload = _plot_scene_payload(type_id="plot.surface")
    matplotlib_payload = _plot_scene_payload(
        type_id="plot.bar",
        properties={"backend": MATPLOTLIB_PLOT_BACKEND_ID},
    )

    assert line_payload["plot_surface"]["live_backend_id"] == PYQTGRAPH_PLOT_BACKEND_ID
    assert surface_payload["plot_surface"]["plot_type"] == "surface"
    assert surface_payload["plot_surface"]["live_backend_id"] == PYVISTA_PLOT_BACKEND_ID
    assert matplotlib_payload["plot_surface"]["live_backend_id"] == MATPLOTLIB_PLOT_BACKEND_ID


def test_generic_plot_scene_payload_projects_connected_tabular_auto_preview(tmp_path: Path) -> None:
    source = tmp_path / "weather.csv"
    source.write_text("time,temp\n0,21.5\n1,22.0\n", encoding="utf-8")
    model = GraphModel()
    registry = build_default_registry()
    workspace_id = model.active_workspace.workspace_id
    tabular = model.add_node(
        workspace_id,
        "tabular.input",
        "Tabular",
        32.0,
        64.0,
        properties={"path": str(source)},
    )
    plot = model.add_node(
        workspace_id,
        "plot.bar",
        "Bar Plot",
        360.0,
        64.0,
        properties={"tabular_mapping": {"x": "time", "y": ["temp"]}},
    )
    model.add_edge(workspace_id, tabular.node_id, "table_data", plot.node_id, "series")

    nodes_payload, _minimap_payload, _edges_payload = GraphScenePayloadBuilder().rebuild_models(
        model=model,
        registry=registry,
        workspace_id=workspace_id,
        scope_path=(),
        graph_theme_bridge=_PlotGraphThemeBridge(),
    )

    payload = next(item for item in nodes_payload if item["node_id"] == plot.node_id)
    plot_surface = payload["plot_surface"]
    assert plot_surface["auto_preview"] is True
    assert plot_surface["auto_preview_source_node_id"] == tabular.node_id
    # Scene payloads carry only the staleness signature; the render request is
    # built asynchronously and cached outside the payload.
    assert plot_surface["series_signature"]
    assert "render_request" not in plot_surface
    assert plot_surface["auto_preview_pending"] is True
    assert plot_surface["render_revision"] == 0

    from ea_node_editor.ui_qml.graph_scene_payload.kinds.plot import (
        _plot_series_source_descriptor,
    )
    from ea_node_editor.ui_qml.plot_auto_preview_service import (
        build_plot_render_request_payload,
        shared_plot_render_request_cache,
    )

    workspace = model.project.workspaces[workspace_id]
    descriptor = _plot_series_source_descriptor(
        node=workspace.nodes[plot.node_id],
        workspace=workspace,
        graph_theme_bridge=None,
    )
    request_payload, warnings = build_plot_render_request_payload(
        node_type_id="plot.bar",
        properties={**workspace.nodes[plot.node_id].properties},
        source_descriptor=descriptor,
    )
    assert warnings == ()
    assert request_payload["plot_type"] == "bar"
    series_payload = [
        {key: value for key, value in item.items() if key not in {"decimation", "source_ref"}}
        for item in request_payload["series"]
    ]
    assert series_payload == [
        {
            "label": "temp",
            "x": [0, 1],
            "y": [21.5, 22],
            "x_column": "time",
            "y_column": "temp",
        }
    ]

    shared_plot_render_request_cache().store(
        workspace_id,
        plot.node_id,
        signature=plot_surface["series_signature"],
        request_payload=request_payload,
    )
    nodes_payload, _minimap_payload, _edges_payload = GraphScenePayloadBuilder().rebuild_models(
        model=model,
        registry=registry,
        workspace_id=workspace_id,
        scope_path=(),
        graph_theme_bridge=_PlotGraphThemeBridge(),
    )
    refreshed = next(item for item in nodes_payload if item["node_id"] == plot.node_id)
    assert refreshed["plot_surface"]["auto_preview_active"] is True
    assert refreshed["plot_surface"]["render_revision"] > 0


def test_generic_plot_auto_preview_reuses_surface_for_node_title_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ea_node_editor.ui_qml.graph_scene_payload.kinds import plot as plot_payload_kind
    from ea_node_editor.ui_qml.plot_auto_preview_service import (
        reset_shared_plot_render_request_cache,
        shared_plot_render_request_cache,
    )

    reset_shared_plot_render_request_cache()
    _source, model, registry, workspace_id, _tabular, plot, _edge = _connected_tabular_plot_model(
        tmp_path
    )
    initial_payload = _full_plot_payload(model, registry, workspace_id, plot.node_id)
    initial_surface = initial_payload["plot_surface"]
    cache_entry = shared_plot_render_request_cache().store(
        workspace_id,
        plot.node_id,
        signature=initial_surface["series_signature"],
        request_payload={"plot_type": "line", "series": []},
    )
    active_payload = _full_plot_payload(model, registry, workspace_id, plot.node_id)
    active_surface = active_payload["plot_surface"]
    assert active_surface["render_revision"] == cache_entry.revision

    descriptor_calls = 0
    original_descriptor = plot_payload_kind._plot_series_source_descriptor

    def counting_descriptor(**kwargs):
        nonlocal descriptor_calls
        descriptor_calls += 1
        return original_descriptor(**kwargs)

    monkeypatch.setattr(plot_payload_kind, "_plot_series_source_descriptor", counting_descriptor)
    stable_payload = _targeted_plot_payload(
        model,
        registry,
        workspace_id,
        plot.node_id,
        previous_payload=active_payload,
        changed_fields=set(),
    )
    assert descriptor_calls == 1
    assert stable_payload["plot_surface"] == active_surface

    descriptor_calls = 0
    model.set_node_title(workspace_id, plot.node_id, "Renamed Plot Node")
    renamed_payload = _targeted_plot_payload(
        model,
        registry,
        workspace_id,
        plot.node_id,
        previous_payload=active_payload,
        changed_fields={"node.title"},
    )

    assert descriptor_calls == 0
    assert renamed_payload["title"] == "Renamed Plot Node"
    assert renamed_payload["plot_surface"] == active_surface
    assert renamed_payload["plot_surface"] is not active_surface


def test_generic_plot_auto_preview_recomputes_for_render_title_source_edge_and_file_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ea_node_editor.ui_qml.graph_scene_payload.kinds import plot as plot_payload_kind
    from ea_node_editor.ui_qml.plot_auto_preview_service import reset_shared_plot_render_request_cache

    reset_shared_plot_render_request_cache()
    _source, model, registry, workspace_id, _tabular, plot, edge = _connected_tabular_plot_model(
        tmp_path
    )
    initial_payload = _full_plot_payload(model, registry, workspace_id, plot.node_id)
    initial_signature = initial_payload["plot_surface"]["series_signature"]

    descriptor_calls = 0
    original_descriptor = plot_payload_kind._plot_series_source_descriptor

    def counting_descriptor(**kwargs):
        nonlocal descriptor_calls
        descriptor_calls += 1
        return original_descriptor(**kwargs)

    monkeypatch.setattr(plot_payload_kind, "_plot_series_source_descriptor", counting_descriptor)
    model.set_node_property(workspace_id, plot.node_id, "title", "Render Title")
    title_payload = _targeted_plot_payload(
        model,
        registry,
        workspace_id,
        plot.node_id,
        previous_payload=initial_payload,
        changed_fields={"properties.title"},
    )
    title_signature = title_payload["plot_surface"]["series_signature"]
    assert descriptor_calls == 1
    assert title_signature != initial_signature

    second_source = tmp_path / "weather_2.csv"
    second_source.write_text("time,temp\n0,18.0\n1,19.0\n", encoding="utf-8")
    second_tabular = model.add_node(
        workspace_id,
        "tabular.input",
        "Tabular 2",
        32.0,
        220.0,
        properties={"path": str(second_source)},
    )
    model.remove_edge(workspace_id, edge.edge_id)
    model.add_edge(workspace_id, second_tabular.node_id, "table_data", plot.node_id, "series")
    descriptor_calls = 0
    retargeted_payload = _targeted_plot_payload(
        model,
        registry,
        workspace_id,
        plot.node_id,
        previous_payload=title_payload,
        changed_fields=None,
    )
    retargeted_surface = retargeted_payload["plot_surface"]
    assert descriptor_calls == 1
    assert retargeted_surface["series_signature"] != title_signature
    assert retargeted_surface["auto_preview_source_node_id"] == second_tabular.node_id

    second_source.write_text("time,temp\n0,18.0\n1,19.0\n2,20.0\n", encoding="utf-8")
    descriptor_calls = 0
    file_changed_payload = _targeted_plot_payload(
        model,
        registry,
        workspace_id,
        plot.node_id,
        previous_payload=retargeted_payload,
        changed_fields=None,
    )
    assert descriptor_calls == 1
    assert file_changed_payload["plot_surface"]["series_signature"] != retargeted_surface["series_signature"]


def test_generic_plot_scene_payload_projects_connected_table_window_auto_preview(
    tmp_path: Path,
) -> None:
    source = tmp_path / "weather.csv"
    source.write_text("time,temp,pressure\n0,21.5,100.0\n1,22.0,101.5\n", encoding="utf-8")
    model = GraphModel()
    registry = build_default_registry()
    workspace_id = model.active_workspace.workspace_id
    tabular = model.add_node(
        workspace_id,
        "tabular.input",
        "Tabular",
        32.0,
        64.0,
        properties={"path": str(source)},
    )
    table_window = model.add_node(
        workspace_id,
        "tabular.table_filter",
        "Table Filter",
        220.0,
        64.0,
        properties={"columns": "time,temp", "row_limit": 0},
    )
    plot = model.add_node(
        workspace_id,
        "plot.bar",
        "Bar Plot",
        420.0,
        64.0,
        properties={"tabular_mapping": {"x": "time", "y": ["temp"]}},
    )
    model.add_edge(workspace_id, tabular.node_id, "table_data", table_window.node_id, "table_data")
    model.add_edge(workspace_id, table_window.node_id, "window", plot.node_id, "series")

    nodes_payload, _minimap_payload, _edges_payload = GraphScenePayloadBuilder().rebuild_models(
        model=model,
        registry=registry,
        workspace_id=workspace_id,
        scope_path=(),
        graph_theme_bridge=_PlotGraphThemeBridge(),
    )

    payload = next(item for item in nodes_payload if item["node_id"] == plot.node_id)
    plot_surface = payload["plot_surface"]
    assert plot_surface["auto_preview"] is True
    assert plot_surface["auto_preview_pending"] is True
    assert plot_surface["auto_preview_source_node_id"] == table_window.node_id
    assert plot_surface["series_signature"]
    assert "render_request" not in plot_surface

    from ea_node_editor.ui_qml.graph_scene_payload.kinds.plot import (
        _plot_series_source_descriptor,
    )
    from ea_node_editor.ui_qml.plot_auto_preview_service import (
        build_plot_render_request_payload,
    )

    workspace = model.project.workspaces[workspace_id]
    descriptor = _plot_series_source_descriptor(
        node=workspace.nodes[plot.node_id],
        workspace=workspace,
        graph_theme_bridge=None,
    )
    assert descriptor["kind"] == "table_filter"
    request_payload, _warnings = build_plot_render_request_payload(
        node_type_id="plot.bar",
        properties={**workspace.nodes[plot.node_id].properties},
        source_descriptor=descriptor,
    )
    series_payload = [
        {key: value for key, value in item.items() if key not in {"decimation", "source_ref"}}
        for item in request_payload["series"]
    ]
    assert series_payload == [
        {
            "label": "temp",
            "x": [0, 1],
            "y": [21.5, 22],
            "x_column": "time",
            "y_column": "temp",
        }
    ]


class PlotSurfaceInteractionQmlTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

    def test_selected_plot_surface_uses_cached_preview_during_transient_interaction(self) -> None:
        self._run_qml_probe(
            "plot-surface-transient-interaction-preview",
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            class PlotHostServiceStub(QObject):
                activeOverlayCountChanged = pyqtSignal()
                previewCacheRevisionChanged = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.calls = []
                    self._active_nodes = set()
                    self._preview_cache_revision = 1

                @pyqtProperty(int, notify=activeOverlayCountChanged)
                def active_overlay_count(self):
                    return len(self._active_nodes)

                @pyqtProperty(int, notify=previewCacheRevisionChanged)
                def preview_cache_revision(self):
                    return self._preview_cache_revision

                @pyqtSlot(str, bool)
                def set_embedded_interaction_active(self, node_id, active):
                    normalized = str(node_id)
                    enabled = bool(active)
                    self.calls.append((normalized, enabled))
                    before_count = len(self._active_nodes)
                    if enabled:
                        self._active_nodes.add(normalized)
                    else:
                        self._active_nodes.discard(normalized)
                        self._preview_cache_revision += 1
                        self.previewCacheRevisionChanged.emit()
                    if len(self._active_nodes) != before_count:
                        self.activeOverlayCountChanged.emit()

                @pyqtSlot(str, result=str)
                def cached_preview_source(self, node_id):
                    return "image://plot-preview-cache/ws/" + str(node_id)

                @pyqtSlot(str, result=bool)
                def embedded_live_overlay_ready(self, node_id):
                    return str(node_id) in self._active_nodes

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            service = PlotHostServiceStub()
            engine.rootContext().setContextProperty("plotHostService", service)

            plot_dir = Path.cwd() / "ea_node_editor" / "ui_qml" / "components" / "graph" / "plot"
            qml = '''
            import QtQuick 2.15

            Item {
                id: root
                width: 360
                height: 260

                Item {
                    id: probeHost
                    objectName: "probeHost"
                    property bool hoverActive: false
                    property bool isSelected: true
                    property bool viewportInteractionCacheActive: false
                    property bool hostDragActive: false
                    property var nodeData: ({
                        "node_id": "node-plot",
                        "surface_variant": "line",
                        "plot_surface": {
                            "plot_type": "line",
                            "live_backend_id": "pyqtgraph",
                            "embedded_rendering_suppressed": false
                        }
                    })
                    property var surfaceMetrics: ({
                        "body_left_margin": 0.0,
                        "body_top": 0.0,
                        "body_right_margin": 0.0,
                        "body_height": 220.0
                    })
                    property real resolvedCornerRadius: 6.0
                    property color inlineInputBackgroundColor: "#18202d"
                    property color selectedOutlineColor: "#5da9ff"
                    property color outlineColor: "#414a5d"
                    property color inlineDrivenTextColor: "#aeb8ce"
                    property color surfaceColor: "#1f2431"
                    property color headerTextColor: "#eef3ff"
                    property int nodeTextRenderType: Text.CurveRendering
                    property bool surfaceFullscreenAvailable: false
                    function surfaceFullscreenAction(_enabled, _primary) { return null; }
                    function requestSurfaceContentFullscreen() { return false; }
                }

                GraphPlotSurfaceBody {
                    id: surface
                    objectName: "graphNodePlotSurfaceProbe"
                    anchors.fill: parent
                    host: probeHost
                }
            }
            '''
            component = QQmlComponent(engine)
            component.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(plot_dir / "PlotSurfaceProbe.qml")))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load plot surface probe:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate plot surface probe:\\n" + errors)

            def settle(cycles=8):
                for _index in range(cycles):
                    app.processEvents()

            window = attach_host_to_window(probe)
            settle()
            host = probe.findChild(QObject, "probeHost")
            surface = probe.findChild(QObject, "graphNodePlotSurfaceProbe")
            assert host is not None
            assert surface is not None

            assert bool(surface.property("liveSurfaceActive"))
            assert bool(surface.property("liveOverlayReady"))
            assert not bool(surface.property("proxySurfaceActive"))
            assert len(variant_list(surface.property("embeddedInteractiveRects"))) == 1
            assert "node-plot" in service._active_nodes

            actions = variant_list(surface.property("surfaceActions"))
            probe.setProperty("visible", False)
            settle()
            assert not surface.property("liveSurfaceActive"), "Hidden plot kept live surface active"
            assert "node-plot" not in service._active_nodes, "Hidden plot stayed active in service"
            assert variant_list(surface.property("surfaceActions")) == actions, "Hidden plot lost its actions"
            probe.setProperty("visible", True)
            settle()
            assert surface.property("liveSurfaceActive"), "Showing plot did not restore live activity"

            host.setProperty("viewportInteractionCacheActive", True)
            settle()
            assert not bool(surface.property("liveSurfaceActive"))
            assert not bool(surface.property("liveOverlayReady"))
            assert bool(surface.property("proxySurfaceActive"))
            assert bool(surface.property("cachedPreviewVisible"))
            assert variant_list(surface.property("embeddedInteractiveRects")) == []
            assert "node-plot" not in service._active_nodes

            host.setProperty("viewportInteractionCacheActive", False)
            settle()
            assert bool(surface.property("liveSurfaceActive"))
            assert bool(surface.property("liveOverlayReady"))
            assert not bool(surface.property("proxySurfaceActive"))
            assert "node-plot" in service._active_nodes

            host.setProperty("hostDragActive", True)
            settle()
            assert not bool(surface.property("liveSurfaceActive"))
            assert bool(surface.property("proxySurfaceActive"))
            assert "node-plot" not in service._active_nodes

            dispose_host_window(probe, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_plot_surface_live_preview_requires_viable_screen_size(self) -> None:
        self._run_qml_probe(
            "plot-surface-live-preview-size-gate",
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            class PlotHostServiceStub(QObject):
                activeOverlayCountChanged = pyqtSignal()
                previewCacheRevisionChanged = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._active_nodes = set()
                    self.calls = []

                @pyqtProperty(int, notify=activeOverlayCountChanged)
                def active_overlay_count(self):
                    return len(self._active_nodes)

                @pyqtProperty(int, notify=previewCacheRevisionChanged)
                def preview_cache_revision(self):
                    return 0

                @pyqtSlot(str, bool)
                def set_embedded_interaction_active(self, node_id, active):
                    normalized = str(node_id)
                    enabled = bool(active)
                    self.calls.append((normalized, enabled))
                    before_count = len(self._active_nodes)
                    if enabled:
                        self._active_nodes.add(normalized)
                    else:
                        self._active_nodes.discard(normalized)
                    if len(self._active_nodes) != before_count:
                        self.activeOverlayCountChanged.emit()

                @pyqtSlot(str, result=str)
                def cached_preview_source(self, node_id):
                    return ""

                @pyqtSlot(str, result=bool)
                def embedded_live_overlay_ready(self, node_id):
                    return str(node_id) in self._active_nodes

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            service = PlotHostServiceStub()
            engine.rootContext().setContextProperty("plotHostService", service)

            plot_dir = Path.cwd() / "ea_node_editor" / "ui_qml" / "components" / "graph" / "plot"
            qml = '''
            import QtQuick 2.15

            Item {
                id: root
                width: 360
                height: 260

                Item {
                    id: probeHost
                    objectName: "probeHost"
                    property bool hoverActive: false
                    property bool isSelected: true
                    property bool viewportInteractionCacheActive: false
                    property bool hostDragActive: false
                    property real currentZoom: 0.5
                    property var nodeData: ({
                        "node_id": "node-plot",
                        "surface_variant": "line",
                        "plot_surface": {
                            "plot_type": "line",
                            "live_backend_id": "pyqtgraph",
                            "embedded_rendering_suppressed": false
                        }
                    })
                    property var surfaceMetrics: ({
                        "body_left_margin": 0.0,
                        "body_top": 0.0,
                        "body_right_margin": 0.0,
                        "body_height": 220.0
                    })
                    property real resolvedCornerRadius: 6.0
                    property color inlineInputBackgroundColor: "#18202d"
                    property color selectedOutlineColor: "#5da9ff"
                    property color outlineColor: "#414a5d"
                    property color inlineDrivenTextColor: "#aeb8ce"
                    property color surfaceColor: "#1f2431"
                    property color headerTextColor: "#eef3ff"
                    property int nodeTextRenderType: Text.CurveRendering
                    property bool surfaceFullscreenAvailable: false
                    function surfaceFullscreenAction(_enabled, _primary) { return null; }
                    function requestSurfaceContentFullscreen() { return false; }
                    function currentViewportZoom() { return currentZoom; }
                }

                GraphPlotSurfaceBody {
                    id: surface
                    objectName: "graphNodePlotSurfaceProbe"
                    anchors.fill: parent
                    host: probeHost
                }
            }
            '''
            component = QQmlComponent(engine)
            component.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(plot_dir / "PlotSurfaceSizeGateProbe.qml")))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load plot surface probe:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate plot surface probe:\\n" + errors)

            def settle(cycles=8):
                for _index in range(cycles):
                    app.processEvents()

            settle()
            host = probe.findChild(QObject, "probeHost")
            surface = probe.findChild(QObject, "graphNodePlotSurfaceProbe")
            assert host is not None
            assert surface is not None

            assert not bool(surface.property("liveSurfaceSizeViable"))
            assert not bool(surface.property("liveSurfaceActive"))
            assert "node-plot" not in service._active_nodes

            host.setProperty("currentZoom", 1.0)
            settle()
            assert bool(surface.property("liveSurfaceSizeViable"))
            assert bool(surface.property("liveSurfaceActive"))
            assert "node-plot" in service._active_nodes

            host.setProperty("currentZoom", 0.25)
            settle()
            assert not bool(surface.property("liveSurfaceSizeViable"))
            assert not bool(surface.property("liveSurfaceActive"))
            assert "node-plot" not in service._active_nodes
            assert ("node-plot", False) in service.calls

            probe.deleteLater()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_plot_surface_size_gate_is_pyqtgraph_only(self) -> None:
        self._run_qml_probe(
            "plot-surface-live-preview-size-gate-backend-aware",
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            class PlotHostServiceStub(QObject):
                activeOverlayCountChanged = pyqtSignal()
                previewCacheRevisionChanged = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._active_nodes = set()

                @pyqtProperty(int, notify=activeOverlayCountChanged)
                def active_overlay_count(self):
                    return len(self._active_nodes)

                @pyqtProperty(int, notify=previewCacheRevisionChanged)
                def preview_cache_revision(self):
                    return 0

                @pyqtSlot(str, bool)
                def set_embedded_interaction_active(self, node_id, active):
                    normalized = str(node_id)
                    before_count = len(self._active_nodes)
                    if bool(active):
                        self._active_nodes.add(normalized)
                    else:
                        self._active_nodes.discard(normalized)
                    if len(self._active_nodes) != before_count:
                        self.activeOverlayCountChanged.emit()

                @pyqtSlot(str, result=str)
                def cached_preview_source(self, node_id):
                    return ""

                @pyqtSlot(str, result=bool)
                def embedded_live_overlay_ready(self, node_id):
                    return str(node_id) in self._active_nodes

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            service = PlotHostServiceStub()
            engine.rootContext().setContextProperty("plotHostService", service)

            plot_dir = Path.cwd() / "ea_node_editor" / "ui_qml" / "components" / "graph" / "plot"
            qml = '''
            import QtQuick 2.15

            Item {
                id: root
                width: 360
                height: 260

                Item {
                    id: probeHost
                    objectName: "probeHost"
                    property bool hoverActive: false
                    property bool isSelected: true
                    property bool viewportInteractionCacheActive: false
                    property bool hostDragActive: false
                    property real currentZoom: 0.25
                    property var nodeData: ({
                        "node_id": "node-plot",
                        "surface_variant": "surface",
                        "plot_surface": {
                            "plot_type": "surface",
                            "live_backend_id": "pyvista",
                            "embedded_rendering_suppressed": false
                        }
                    })
                    property var surfaceMetrics: ({
                        "body_left_margin": 0.0,
                        "body_top": 0.0,
                        "body_right_margin": 0.0,
                        "body_height": 220.0
                    })
                    property real resolvedCornerRadius: 6.0
                    property color inlineInputBackgroundColor: "#18202d"
                    property color selectedOutlineColor: "#5da9ff"
                    property color outlineColor: "#414a5d"
                    property color inlineDrivenTextColor: "#aeb8ce"
                    property color surfaceColor: "#1f2431"
                    property color headerTextColor: "#eef3ff"
                    property int nodeTextRenderType: Text.CurveRendering
                    property bool surfaceFullscreenAvailable: false
                    function surfaceFullscreenAction(_enabled, _primary) { return null; }
                    function requestSurfaceContentFullscreen() { return false; }
                    function currentViewportZoom() { return currentZoom; }
                }

                GraphPlotSurfaceBody {
                    id: surface
                    objectName: "graphNodePlotSurfaceProbe"
                    anchors.fill: parent
                    host: probeHost
                }
            }
            '''
            component = QQmlComponent(engine)
            component.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(plot_dir / "PlotSurfaceBackendGateProbe.qml")))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load plot surface probe:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate plot surface probe:\\n" + errors)

            def settle(cycles=8):
                for _index in range(cycles):
                    app.processEvents()

            settle()
            surface = probe.findChild(QObject, "graphNodePlotSurfaceProbe")
            assert surface is not None

            assert not bool(surface.property("liveSurfaceSizeGateRequired"))
            assert bool(surface.property("liveSurfaceSizeViable"))
            assert bool(surface.property("liveSurfaceActive"))
            assert "node-plot" in service._active_nodes

            probe.deleteLater()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_plot_surface_blanks_cached_image_on_node_change_and_fullscreen_open(self) -> None:
        self._run_qml_probe(
            "plot-surface-cached-image-blanking",
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            class PlotHostServiceStub(QObject):
                activeOverlayCountChanged = pyqtSignal()
                plotOverlayRevisionChanged = pyqtSignal()
                previewCacheRevisionChanged = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.calls = []
                    self._preview_cache_revision = 1

                @pyqtProperty(int, notify=activeOverlayCountChanged)
                def active_overlay_count(self):
                    return 0

                @pyqtProperty(int, notify=plotOverlayRevisionChanged)
                def plot_overlay_revision(self):
                    return 0

                @pyqtProperty(int, notify=previewCacheRevisionChanged)
                def preview_cache_revision(self):
                    return self._preview_cache_revision

                @pyqtSlot(str, bool)
                def set_embedded_interaction_active(self, node_id, active):
                    self.calls.append((str(node_id), bool(active)))

                @pyqtSlot(str, result=str)
                def cached_preview_source(self, node_id):
                    return "image://plot-preview-cache/ws/" + str(node_id)

                @pyqtSlot(str, result=bool)
                def embedded_live_overlay_ready(self, node_id):
                    return False

            class FullscreenBridgeStub(QObject):
                contentFullscreenChanged = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._open = False

                @pyqtProperty(bool, notify=contentFullscreenChanged)
                def open(self):
                    return self._open

                def set_open(self, value):
                    self._open = bool(value)
                    self.contentFullscreenChanged.emit()

            def source_text(item):
                value = item.property("source")
                return value.toString() if hasattr(value, "toString") else str(value)

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            service = PlotHostServiceStub()
            fullscreen_bridge = FullscreenBridgeStub()
            engine.rootContext().setContextProperty("plotHostService", service)
            engine.rootContext().setContextProperty("contentFullscreenBridge", fullscreen_bridge)

            plot_dir = Path.cwd() / "ea_node_editor" / "ui_qml" / "components" / "graph" / "plot"
            qml = '''
            import QtQuick 2.15

            Item {
                id: root
                width: 360
                height: 260

                Item {
                    id: probeHost
                    objectName: "probeHost"
                    property bool hoverActive: false
                    property bool isSelected: true
                    property bool viewportInteractionCacheActive: false
                    property bool hostDragActive: false
                    property var nodeData: ({
                        "node_id": "plot-a",
                        "surface_variant": "line",
                        "plot_surface": {
                            "plot_type": "line",
                            "live_backend_id": "pyqtgraph",
                            "embedded_rendering_suppressed": false
                        }
                    })
                    property var surfaceMetrics: ({
                        "body_left_margin": 0.0,
                        "body_top": 0.0,
                        "body_right_margin": 0.0,
                        "body_height": 220.0
                    })
                    property real resolvedCornerRadius: 6.0
                    property color inlineInputBackgroundColor: "#18202d"
                    property color selectedOutlineColor: "#5da9ff"
                    property color outlineColor: "#414a5d"
                    property color inlineDrivenTextColor: "#aeb8ce"
                    property color surfaceColor: "#1f2431"
                    property color headerTextColor: "#eef3ff"
                    property int nodeTextRenderType: Text.CurveRendering
                    property bool surfaceFullscreenAvailable: false
                    function surfaceFullscreenAction(_enabled, _primary) { return null; }
                    function requestSurfaceContentFullscreen() { return false; }
                }

                GraphPlotSurfaceBody {
                    id: surface
                    objectName: "graphNodePlotSurfaceProbe"
                    anchors.fill: parent
                    host: probeHost
                }
            }
            '''
            component = QQmlComponent(engine)
            component.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(plot_dir / "PlotSurfaceBlankingProbe.qml")))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load plot surface probe:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate plot surface probe:\\n" + errors)

            def settle(cycles=8):
                for _index in range(cycles):
                    app.processEvents()

            settle()
            host = probe.findChild(QObject, "probeHost")
            surface = probe.findChild(QObject, "graphNodePlotSurfaceProbe")
            cached_image = probe.findChild(QObject, "graphNodePlotCachedPreviewImage")
            assert host is not None
            assert surface is not None
            assert cached_image is not None

            assert bool(surface.property("cachedPreviewVisible"))
            assert source_text(cached_image).endswith("/plot-a")
            assert ("plot-a", True) in service.calls

            host.setProperty("nodeData", {
                "node_id": "plot-b",
                "surface_variant": "line",
                "plot_surface": {
                    "plot_type": "line",
                    "live_backend_id": "pyqtgraph",
                    "embedded_rendering_suppressed": False,
                },
            })
            assert source_text(cached_image) == ""
            assert ("plot-a", False) in service.calls
            settle()
            assert bool(surface.property("cachedPreviewVisible"))
            assert source_text(cached_image).endswith("/plot-b")

            fullscreen_bridge.set_open(True)
            settle()
            assert not bool(surface.property("cachedPreviewVisible"))
            assert not bool(surface.property("placeholderPreviewVisible"))
            assert source_text(cached_image) == ""
            assert ("plot-b", False) in service.calls

            probe.deleteLater()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_plot_surface_rechecks_overlay_readiness_when_revision_changes_but_count_does_not(self) -> None:
        self._run_qml_probe(
            "plot-surface-overlay-revision-refresh",
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            class PlotHostServiceStub(QObject):
                activeOverlayCountChanged = pyqtSignal()
                plotOverlayRevisionChanged = pyqtSignal()
                previewCacheRevisionChanged = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._plot_overlay_revision = 1
                    self._preview_cache_revision = 1
                    self._ready_nodes = set()
                    self.ready_calls = []

                @pyqtProperty(int, notify=activeOverlayCountChanged)
                def active_overlay_count(self):
                    return 1

                @pyqtProperty(int, notify=plotOverlayRevisionChanged)
                def plot_overlay_revision(self):
                    return self._plot_overlay_revision

                @pyqtProperty(int, notify=previewCacheRevisionChanged)
                def preview_cache_revision(self):
                    return self._preview_cache_revision

                @pyqtSlot(str, bool)
                def set_embedded_interaction_active(self, node_id, active):
                    pass

                @pyqtSlot(str, result=str)
                def cached_preview_source(self, node_id):
                    return "image://plot-preview-cache/ws/" + str(node_id)

                @pyqtSlot(str, result=bool)
                def embedded_live_overlay_ready(self, node_id):
                    normalized = str(node_id)
                    self.ready_calls.append(normalized)
                    return normalized in self._ready_nodes

                def mark_ready(self, node_id):
                    self._ready_nodes.add(str(node_id))
                    self._plot_overlay_revision += 1
                    self.plotOverlayRevisionChanged.emit()

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            service = PlotHostServiceStub()
            engine.rootContext().setContextProperty("plotHostService", service)

            plot_dir = Path.cwd() / "ea_node_editor" / "ui_qml" / "components" / "graph" / "plot"
            qml = '''
            import QtQuick 2.15

            Item {
                id: root
                width: 360
                height: 260

                Item {
                    id: probeHost
                    objectName: "probeHost"
                    property bool hoverActive: true
                    property bool isSelected: false
                    property bool viewportInteractionCacheActive: false
                    property bool hostDragActive: false
                    property var nodeData: ({
                        "node_id": "node-plot",
                        "surface_variant": "line",
                        "plot_surface": {
                            "plot_type": "line",
                            "live_backend_id": "pyqtgraph",
                            "embedded_rendering_suppressed": false
                        }
                    })
                    property var surfaceMetrics: ({
                        "body_left_margin": 0.0,
                        "body_top": 0.0,
                        "body_right_margin": 0.0,
                        "body_height": 220.0
                    })
                    property real resolvedCornerRadius: 6.0
                    property color inlineInputBackgroundColor: "#18202d"
                    property color selectedOutlineColor: "#5da9ff"
                    property color outlineColor: "#414a5d"
                    property color inlineDrivenTextColor: "#aeb8ce"
                    property color surfaceColor: "#1f2431"
                    property color headerTextColor: "#eef3ff"
                    property int nodeTextRenderType: Text.CurveRendering
                    property bool surfaceFullscreenAvailable: false
                    function surfaceFullscreenAction(_enabled, _primary) { return null; }
                    function requestSurfaceContentFullscreen() { return false; }
                }

                GraphPlotSurfaceBody {
                    id: surface
                    objectName: "graphNodePlotSurfaceProbe"
                    anchors.fill: parent
                    host: probeHost
                }
            }
            '''
            component = QQmlComponent(engine)
            component.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(plot_dir / "PlotSurfaceRevisionProbe.qml")))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load plot surface probe:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate plot surface probe:\\n" + errors)

            def settle(cycles=8):
                for _index in range(cycles):
                    app.processEvents()

            settle()
            surface = probe.findChild(QObject, "graphNodePlotSurfaceProbe")
            assert surface is not None
            assert not bool(surface.property("liveOverlayReady"))
            calls_before = len(service.ready_calls)

            service.mark_ready("node-plot")
            settle()

            assert bool(surface.property("liveOverlayReady"))
            assert len(service.ready_calls) > calls_before

            probe.deleteLater()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_wheel_zoom_controller_enters_cache_window_for_live_plots_and_viewers(self) -> None:
        self._run_qml_probe(
            "plot-wheel-zoom-viewport-cache-eligibility",
            """
            from pathlib import Path

            from PyQt6.QtCore import QUrl
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()

            graph_canvas_dir = Path.cwd() / "ea_node_editor" / "ui_qml" / "components" / "graph_canvas"
            qml = '''
            import QtQuick 2.15
            import QtQml 2.15

            Item {
                id: root

                QtObject {
                    id: activePlotBridge
                    property var nodes_model: [{
                        "surface_family": "plot",
                        "plot_surface": {"embedded_rendering_suppressed": false}
                    }]
                }
                Item {
                    id: activePlotCanvas
                    property var sceneStateBridge: activePlotBridge
                }
                GraphCanvasViewportController {
                    id: activePlotController
                    canvasItem: activePlotCanvas
                }
                property bool activePlotCache: activePlotController.shouldUseViewportInteractionQualityForWheelZoom()

                QtObject {
                    id: suppressedPlotBridge
                    property var nodes_model: [{
                        "surface_family": "plot",
                        "plot_surface": {"embedded_rendering_suppressed": true}
                    }]
                }
                Item {
                    id: suppressedPlotCanvas
                    property var sceneStateBridge: suppressedPlotBridge
                }
                GraphCanvasViewportController {
                    id: suppressedPlotController
                    canvasItem: suppressedPlotCanvas
                }
                property bool suppressedPlotCache: suppressedPlotController.shouldUseViewportInteractionQualityForWheelZoom()

                QtObject {
                    id: activeViewerBridge
                    property var nodes_model: [{
                        "surface_family": "viewer",
                        "viewer_surface": {"live_surface_supported": true}
                    }]
                }
                Item {
                    id: activeViewerCanvas
                    property var sceneStateBridge: activeViewerBridge
                }
                GraphCanvasViewportController {
                    id: activeViewerController
                    canvasItem: activeViewerCanvas
                }
                property bool activeViewerCache: activeViewerController.shouldUseViewportInteractionQualityForWheelZoom()

                QtObject {
                    id: nonPlotBridge
                    property var nodes_model: [{
                        "surface_family": "media",
                        "render_quality": {"supported_quality_tiers": ["full", "proxy"]}
                    }]
                }
                Item {
                    id: nonPlotCanvas
                    property var sceneStateBridge: nonPlotBridge
                }
                GraphCanvasViewportController {
                    id: nonPlotController
                    canvasItem: nonPlotCanvas
                }
                property bool nonPlotCache: nonPlotController.shouldUseViewportInteractionQualityForWheelZoom()
            }
            '''
            component = QQmlComponent(engine)
            component.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(graph_canvas_dir / "ViewportControllerProbe.qml")))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load viewport controller probe:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate viewport controller probe:\\n" + errors)
            app.processEvents()

            assert bool(probe.property("activePlotCache"))
            assert not bool(probe.property("suppressedPlotCache"))
            assert bool(probe.property("activeViewerCache"))
            assert not bool(probe.property("nonPlotCache"))

            probe.deleteLater()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_live_surface_deactivation_survives_synchronous_state_flip_without_binding_loop(self) -> None:
        self._run_qml_probe(
            "plot-surface-embedded-interaction-no-binding-loop",
            """
            from pathlib import Path

            from PyQt6.QtCore import (
                QObject,
                QUrl,
                pyqtProperty,
                pyqtSignal,
                pyqtSlot,
                qInstallMessageHandler,
            )
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            qt_messages = []

            def capture_qt_message(_message_type, _context, message):
                qt_messages.append(str(message))

            previous_message_handler = qInstallMessageHandler(capture_qt_message)

            class PlotHostServiceStub(QObject):
                # Mirrors the real PlotHostService signal wiring: a single
                # state_changed notifies plot_overlay_revision and
                # active_overlay_count, and a separate preview_cache_changed
                # notifies preview_cache_revision. Deactivation re-emits both
                # synchronously, the same way _capture_cached_live_state_for_key
                # and _release_inactive_embedded_overlay do in production.
                state_changed = pyqtSignal()
                preview_cache_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.calls = []
                    self._active_nodes = set()
                    self._preview_cache_revision = 0
                    self._plot_overlay_revision = 0

                @pyqtProperty(int, notify=state_changed)
                def active_overlay_count(self):
                    return len(self._active_nodes)

                @pyqtProperty(int, notify=state_changed)
                def plot_overlay_revision(self):
                    return self._plot_overlay_revision

                @pyqtProperty(int, notify=preview_cache_changed)
                def preview_cache_revision(self):
                    return self._preview_cache_revision

                @pyqtSlot(str, bool)
                def set_embedded_interaction_active(self, node_id, active):
                    normalized = str(node_id)
                    enabled = bool(active)
                    self.calls.append((normalized, enabled))
                    if enabled:
                        self._active_nodes.add(normalized)
                        return
                    if normalized not in self._active_nodes:
                        return
                    self._active_nodes.discard(normalized)
                    self._preview_cache_revision += 1
                    self.preview_cache_changed.emit()
                    self._plot_overlay_revision += 1
                    self.state_changed.emit()

                @pyqtSlot(str, result=str)
                def cached_preview_source(self, node_id):
                    return "image://plot-preview-cache/ws/" + str(node_id)

                @pyqtSlot(str, result=bool)
                def embedded_live_overlay_ready(self, node_id):
                    return str(node_id) in self._active_nodes

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            service = PlotHostServiceStub()
            engine.rootContext().setContextProperty("plotHostService", service)

            plot_dir = Path.cwd() / "ea_node_editor" / "ui_qml" / "components" / "graph" / "plot"
            qml = '''
            import QtQuick 2.15

            Item {
                id: root
                width: 360
                height: 260

                Item {
                    id: probeHost
                    objectName: "probeHost"
                    property bool hoverActive: false
                    property bool isSelected: true
                    property bool viewportInteractionCacheActive: false
                    property bool hostDragActive: false
                    property var nodeData: ({
                        "node_id": "node-plot",
                        "surface_variant": "line",
                        "plot_surface": {
                            "plot_type": "line",
                            "live_backend_id": "pyqtgraph",
                            "embedded_rendering_suppressed": false
                        }
                    })
                    property var surfaceMetrics: ({
                        "body_left_margin": 0.0,
                        "body_top": 0.0,
                        "body_right_margin": 0.0,
                        "body_height": 220.0
                    })
                    property real resolvedCornerRadius: 6.0
                    property color inlineInputBackgroundColor: "#18202d"
                    property color selectedOutlineColor: "#5da9ff"
                    property color outlineColor: "#414a5d"
                    property color inlineDrivenTextColor: "#aeb8ce"
                    property color surfaceColor: "#1f2431"
                    property color headerTextColor: "#eef3ff"
                    property int nodeTextRenderType: Text.CurveRendering
                    property bool surfaceFullscreenAvailable: false
                    function surfaceFullscreenAction(_enabled, _primary) { return null; }
                    function requestSurfaceContentFullscreen() { return false; }
                }

                GraphPlotSurfaceBody {
                    id: surface
                    objectName: "graphNodePlotSurfaceProbe"
                    anchors.fill: parent
                    host: probeHost
                }
            }
            '''
            component = QQmlComponent(engine)
            component.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(plot_dir / "PlotSurfaceBindingLoopProbe.qml")))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load plot surface probe:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate plot surface probe:\\n" + errors)

            def settle(cycles=8):
                for _index in range(cycles):
                    app.processEvents()

            try:
                settle()
                host = probe.findChild(QObject, "probeHost")
                surface = probe.findChild(QObject, "graphNodePlotSurfaceProbe")
                assert host is not None
                assert surface is not None
                assert bool(surface.property("liveSurfaceActive"))
                assert "node-plot" in service._active_nodes
                qt_messages.clear()

                # A transient-interaction change handler (onLiveSurfaceActiveChanged)
                # calls _syncEmbeddedInteraction synchronously, which deactivates the
                # embedded overlay and re-emits state_changed/preview_cache_changed
                # from inside that same call. That must not re-enter a binding that
                # is still being evaluated.
                host.setProperty("viewportInteractionCacheActive", True)
                settle()

                assert not bool(surface.property("liveSurfaceActive"))
                assert "node-plot" not in service._active_nodes
                assert service.calls[-1] == ("node-plot", False)

                host.setProperty("viewportInteractionCacheActive", False)
                settle()
                assert bool(surface.property("liveSurfaceActive"))
                assert "node-plot" in service._active_nodes
            finally:
                probe.deleteLater()
                engine.deleteLater()
                app.processEvents()
                qInstallMessageHandler(previous_message_handler)

            binding_loop_messages = [
                message for message in qt_messages if "Binding loop detected" in message
            ]
            assert not binding_loop_messages, qt_messages
            """,
        )

    def test_plot_surface_confirms_cached_preview_swap_to_host_service(self) -> None:
        self._run_qml_probe(
            "plot-surface-preview-swap-confirmation",
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            class PlotHostServiceStub(QObject):
                state_changed = pyqtSignal()
                preview_cache_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.preview_swap_calls = []
                    self._preview_cache_revision = 1

                @pyqtProperty(int, notify=state_changed)
                def active_overlay_count(self):
                    return 0

                @pyqtProperty(int, notify=state_changed)
                def plot_overlay_revision(self):
                    return 0

                @pyqtProperty(int, notify=preview_cache_changed)
                def preview_cache_revision(self):
                    return self._preview_cache_revision

                @pyqtSlot(str, bool)
                def set_embedded_interaction_active(self, node_id, active):
                    pass

                @pyqtSlot(str, result=str)
                def cached_preview_source(self, node_id):
                    return (
                        "image://plot-preview-cache/preview?workspace=ws-plot&node="
                        + str(node_id)
                        + "&revision="
                        + str(self._preview_cache_revision)
                    )

                @pyqtSlot(str, result=bool)
                def embedded_live_overlay_ready(self, node_id):
                    return False

                @pyqtSlot(str, str)
                def notify_cached_preview_swapped(self, node_id, source):
                    self.preview_swap_calls.append((str(node_id), str(source)))

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            service = PlotHostServiceStub()
            engine.rootContext().setContextProperty("plotHostService", service)

            plot_dir = Path.cwd() / "ea_node_editor" / "ui_qml" / "components" / "graph" / "plot"
            qml = '''
            import QtQuick 2.15

            Item {
                id: root
                width: 360
                height: 260

                Item {
                    id: probeHost
                    objectName: "probeHost"
                    property bool hoverActive: false
                    property bool isSelected: false
                    property bool viewportInteractionCacheActive: false
                    property bool hostDragActive: false
                    property var nodeData: ({
                        "node_id": "node-plot",
                        "surface_variant": "line",
                        "plot_surface": {
                            "plot_type": "line",
                            "live_backend_id": "pyqtgraph",
                            "embedded_rendering_suppressed": false
                        }
                    })
                    property var surfaceMetrics: ({
                        "body_left_margin": 0.0,
                        "body_top": 0.0,
                        "body_right_margin": 0.0,
                        "body_height": 220.0
                    })
                    property real resolvedCornerRadius: 6.0
                    property color inlineInputBackgroundColor: "#18202d"
                    property color selectedOutlineColor: "#5da9ff"
                    property color outlineColor: "#414a5d"
                    property color inlineDrivenTextColor: "#aeb8ce"
                    property color surfaceColor: "#1f2431"
                    property color headerTextColor: "#eef3ff"
                    property int nodeTextRenderType: Text.CurveRendering
                    property bool surfaceFullscreenAvailable: false
                    function surfaceFullscreenAction(_enabled, _primary) { return null; }
                    function requestSurfaceContentFullscreen() { return false; }
                }

                GraphPlotSurfaceBody {
                    id: surface
                    objectName: "graphNodePlotSurfaceProbe"
                    anchors.fill: parent
                    host: probeHost
                }
            }
            '''
            component = QQmlComponent(engine)
            component.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(plot_dir / "PlotSurfacePreviewSwapProbe.qml")))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load plot surface probe:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate plot surface probe:\\n" + errors)

            def settle(cycles=8):
                for _index in range(cycles):
                    app.processEvents()

            def image_source_text(image):
                value = image.property("source")
                return value.toString() if hasattr(value, "toString") else str(value)

            try:
                settle()
                surface = probe.findChild(QObject, "graphNodePlotSurfaceProbe")
                cached_image = probe.findChild(QObject, "graphNodePlotCachedPreviewImage")
                assert surface is not None
                assert cached_image is not None
                assert bool(surface.property("cachedPreviewVisible"))
                initial_source = service.cached_preview_source("node-plot")
                assert service.preview_swap_calls[-1] == (
                    "node-plot",
                    initial_source,
                ), service.preview_swap_calls

                # A live-exit capture publishes a new revision; the surface
                # must confirm the swapped source back to the host service.
                service._preview_cache_revision += 1
                service.preview_cache_changed.emit()
                settle()

                swapped_source = service.cached_preview_source("node-plot")
                assert swapped_source != initial_source
                assert service.preview_swap_calls[-1] == (
                    "node-plot",
                    swapped_source,
                ), service.preview_swap_calls
                assert image_source_text(cached_image) == swapped_source
            finally:
                probe.deleteLater()
                engine.deleteLater()
                app.processEvents()
            """,
        )
