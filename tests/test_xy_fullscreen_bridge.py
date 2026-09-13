# Purpose: Prove Media Panel plot source identity and fullscreen lifecycle integration.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_fullscreen_bridge.py
from dataclasses import replace
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.runtime_contracts import DataTree, PlotProvenance, Interval1D
from ea_node_editor.runtime_contracts.settled_results import SettledPortResult
from ea_node_editor.runtime_contracts.solution_records import NodeSolutionFact, SolutionDisposition, SolutionFreshness, SolutionResidency
from ea_node_editor.ui.shell.state import ShellRunState
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui_qml.content_fullscreen_bridge import ContentFullscreenBridge
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from tests.test_plot_value import plot_value


class Events(QObject):
    changed = pyqtSignal()


@pytest.fixture
def setup(monkeypatch):
    app = QApplication.instance() or QApplication(["xy-bridge-test"])
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    producer = model.add_node(workspace.workspace_id, "plot.signal", "Signal Plot", 0, 0,
                              properties=registry.default_properties("plot.signal"))
    panel = model.add_node(workspace.workspace_id, "media.panel", "Media Panel", 100, 0,
                           properties=registry.default_properties("media.panel"))
    model.add_edge(workspace.workspace_id, producer.node_id, "image", panel.node_id, "source")
    plot = replace(plot_value(), provenance=PlotProvenance(workspace.workspace_id, producer.node_id, "original-run"))
    state = ShellRunState()
    state.node_execution_workspace_id = workspace.workspace_id
    state.completed_node_ids = {producer.node_id, panel.node_id}
    state.cached_node_output_records_by_workspace_id[workspace.workspace_id] = {}
    state.node_solution_facts_by_workspace_id[workspace.workspace_id] = {}
    for node, port in ((producer, "image"), (panel, "_surface_source")):
        record_id = "record-" + node.node_id
        state.cached_node_output_records_by_workspace_id[workspace.workspace_id][node.node_id] = {record_id: {
            "record_id": record_id, "outputs_available": True,
            "outputs": {port: SettledPortResult(status="value", value=DataTree.from_item(plot))},
        }}
        state.node_solution_facts_by_workspace_id[workspace.workspace_id][node.node_id] = NodeSolutionFact(
            project_id=model.project.project_id, workspace_id=workspace.workspace_id, node_id=node.node_id,
            freshness=SolutionFreshness.CURRENT, revision=1, retained_record_id=record_id,
            retained_solution_key="a"*64, residency=SolutionResidency.SESSION,
            last_disposition=SolutionDisposition.REUSED,
        )
    scene = GraphSceneBridge()
    scene._history = RuntimeGraphHistory()
    scene.set_workspace(model, registry, workspace.workspace_id)
    events = Events()
    monkeypatch.setattr("ea_node_editor.ui.media_panel_source.image_value_preview_source", lambda value: "image://preview/plot")
    bridge = ContentFullscreenBridge(model_provider=lambda: model, registry_provider=lambda: registry,
        active_workspace_id_provider=lambda: workspace.workspace_id, project_context_provider=lambda: (None, {}),
        scene_bridge=scene, viewer_session_bridge=SimpleNamespace(), run_state=state,
        execution_state_changed_signal=events.changed, script_editor=None, save_file_dialog=lambda **kwargs: "",
        trim_video_clip_replace=lambda *args: {}, trim_video_clip_copy=lambda *args: {},
        create_web_surface_artifact_service=lambda *args: None)
    yield SimpleNamespace(app=app, bridge=bridge, model=model, workspace=workspace, producer=producer, panel=panel,
                          scene=scene, state=state, events=events, plot=plot)
    bridge.shutdown()
    app.processEvents()


def test_unchanged_refresh_keeps_session_and_forced_running_discards_pending(setup):
    s = setup
    assert s.bridge.request_open_node(s.panel.node_id)
    session = s.bridge.xy_plot_bridge
    assert session is not None and s.bridge.content_kind == "media"
    assert s.bridge.media_payload["media_kind"] == "plot"
    assert "signals" not in repr(s.bridge.media_payload)
    s.scene.nodes_changed.emit()
    assert s.bridge.xy_plot_bridge is session
    s.state.running_node_ids = {s.producer.node_id}
    s.events.changed.emit()
    assert s.bridge.xy_plot_bridge is None and session.retired
    assert s.bridge.open and s.bridge.media_payload["source_state"] == "running"
    s.bridge._on_xy_close(session, {"state": {"ranges": {"x": [1, 2]}}, "changed_axes": ["x"]})
    assert s.producer.properties["x_axis_interval"] is None


def test_normal_close_retires_before_one_batch_and_reopening_restores_state(setup):
    s = setup
    assert s.bridge.request_open_node(s.panel.node_id)
    session = s.bridge.xy_plot_bridge
    observed = []
    s.scene.nodes_changed.connect(lambda: observed.append((s.bridge.open, s.bridge.xy_plot_bridge)))
    event = {"state": {"ranges": {"x": [.2, 1.2], "y": [.3, 1.3]}, "selection": {"polygon": [[0,0],[1,0],[1,1]]}},
             "changed_axes": ["x", "y"], "automatic": []}
    s.bridge._on_xy_close(session, event)
    assert not s.bridge.open and session.retired
    assert observed and all(value == (False, None) for value in observed)
    assert s.scene._history.undo_depth(s.workspace.workspace_id) == 1
    assert s.producer.properties["x_axis_interval"] == Interval1D(.2, 1.2)
    assert len(s.bridge._xy_owner.cache) == 1


def test_renderer_failure_and_deleted_producer_retire_callbacks(setup):
    s = setup
    s.bridge.request_open_node(s.panel.node_id)
    old = s.bridge.xy_plot_bridge
    old.host_failed("renderer lost")
    assert old.retired and s.bridge.xy_plot_bridge is None
    assert s.bridge.media_payload["source_state"] == "failed"
    s.scene.nodes_changed.emit()
    assert s.bridge.xy_plot_bridge is None
    s.bridge.request_close()
    s.bridge.request_open_node(s.panel.node_id)
    session = s.bridge.xy_plot_bridge
    s.workspace.nodes.pop(s.producer.node_id)
    s.events.changed.emit()
    assert session.retired and s.bridge.xy_plot_bridge is None
    assert s.bridge.media_payload["source_state"] == "stale"
