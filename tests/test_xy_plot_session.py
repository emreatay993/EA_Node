# Purpose: Verify producer-authorized atomic range writeback and transient state.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_plot_session.py
import copy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.runtime_contracts import ArrayValue, DataTree, Interval1D, PlotProvenance, PlotSignal
from ea_node_editor.ui.xy_plot_session import XYPlotSessionOwner
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from tests.test_plot_value import plot_value


@pytest.fixture
def owner(monkeypatch):
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    node = model.add_node(workspace.workspace_id, "plot.signal", "Signal Plot", 0, 0,
                          properties=registry.default_properties("plot.signal"))
    plot = replace(plot_value(), provenance=PlotProvenance(workspace.workspace_id, node.node_id, "original-run"))
    scene = GraphSceneBridge()
    from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
    scene._history = RuntimeGraphHistory()
    scene.set_workspace(model, registry, workspace.workspace_id)
    current = {"plot": plot}
    monkeypatch.setattr("ea_node_editor.ui.xy_plot_session.current_output_value", lambda *_args: DataTree.from_item(current["plot"]) if current["plot"] else None)
    owner = XYPlotSessionOwner(model_provider=lambda: model, registry_provider=lambda: registry,
        active_workspace_id_provider=lambda: workspace.workspace_id, scene_bridge=scene, run_state=SimpleNamespace())
    owner.observe_graph()
    owner.active = SimpleNamespace(plot=plot)
    return owner, node, plot, current


def event(**extra):
    return {"state": {"ranges": {"x": [0.5, 1.5], "y": [0.2, 1.2]}, "selection": None}, "changed_axes": ["x", "y"], **extra}


def test_one_batch_targets_producer_and_no_initialization_write(owner):
    service, node, plot, _ = owner
    assert service.close_updates(service.active, event(changed_axes=[])) == (node.node_id, {})
    node_id, updates = service.close_updates(service.active, event())
    assert updates == {"x_axis_interval": Interval1D(.5, 1.5), "y_axis_interval": Interval1D(.2, 1.2)}
    original = service.scene.set_node_properties
    service.scene.set_node_properties = Mock(wraps=original)
    service.active = None
    assert service.commit(plot, node_id, updates)
    service.scene.set_node_properties.assert_called_once_with(node.node_id, updates)
    assert node.properties["x_axis_interval"] == Interval1D(.5, 1.5)
    assert len(service.cache) == 1
    workspace, _ = service._node(plot)
    history = service.scene._history
    assert history.undo_depth(workspace.workspace_id) == 1
    assert history.undo_workspace(workspace.workspace_id, workspace) is not None
    restored = workspace.nodes[node.node_id]
    assert restored.properties["x_axis_interval"] is None and restored.properties["y_axis_interval"] is None
    service.observe_graph()
    assert not service.cache
    assert history.redo_workspace(workspace.workspace_id, workspace) is not None
    restored = workspace.nodes[node.node_id]
    assert restored.properties["x_axis_interval"] == Interval1D(.5, 1.5)
    assert restored.properties["y_axis_interval"] == Interval1D(.2, 1.2)


@pytest.mark.parametrize("blocked", ["locked", "sync_off", "stale", "other_plot"])
def test_unauthorized_writeback_is_skipped(owner, blocked):
    service, node, plot, current = owner
    if blocked == "locked": node.locked = True
    if blocked == "sync_off": node.properties["sync_fullscreen_ranges"] = False
    if blocked == "stale": current["plot"] = None
    if blocked == "other_plot": current["plot"] = replace(plot, provenance=replace(plot.provenance, run_id="new"))
    assert service.close_updates(service.active, event())[1] == {}


def test_connected_axis_preserves_fallback_and_reset_is_nullable(owner):
    service, node, plot, _ = owner
    workspace, _ = service._node(plot)
    node.exposed_ports["x_axis_interval"] = True
    workspace.edges["edge"] = SimpleNamespace(enabled=True, target_node_id=node.node_id, target_port_key="x_axis_interval")
    node.properties["x_axis_interval"] = Interval1D(1, 2)
    node.properties["y_axis_interval"] = Interval1D(1, 2)
    assert service.close_updates(service.active, event(automatic=["x", "y"]))[1] == {"y_axis_interval": None}


@pytest.mark.parametrize("axis", ["x", "y"])
def test_axis_fit_clears_only_its_override_in_one_batch(owner, axis):
    service, node, plot, _ = owner
    node.properties.update(x_axis_interval=Interval1D(1, 2), y_axis_interval=Interval1D(3, 4))
    node_id, updates = service.close_updates(service.active, event(changed_axes=[axis], automatic=[axis]))
    assert updates == {f"{axis}_axis_interval": None}
    service.active = None
    assert service.commit(plot, node_id, updates)
    other = "y" if axis == "x" else "x"
    assert node.properties[f"{other}_axis_interval"] == (Interval1D(3, 4) if other == "y" else Interval1D(1, 2))
    assert service.scene._history.undo_depth(plot.provenance.workspace_id) == 1


def test_datetime_bounds_are_atomic_and_external_edits_invalidate_cache(owner):
    service, node, plot, current = owner
    signal = PlotSignal("signal-0", ArrayValue.from_numpy(np.array(['2026-01-01', '2026-01-02', '2026-01-03'], dtype='datetime64[ms]')), plot.signals[0].y, x_kind="datetime")
    plot = replace(plot, signals=(signal,))
    current["plot"] = plot
    service.active.plot = plot
    node_id, updates = service.close_updates(service.active, event(changed_axes=["x"]))
    assert updates == {"x_datetime_start": "1970-01-01T00:00:00.000500Z", "x_datetime_end": "1970-01-01T00:00:00.001500Z"}
    node.properties["title"] = "external"
    service.observe_graph()
    assert not service.cache


@pytest.mark.parametrize("axes", [None, [{}], ["z"]])
def test_malformed_close_axes_discard_writeback(owner, axes):
    service, _, _, _ = owner
    assert service.close_updates(service.active, event(changed_axes=axes)) == ("", {})
    assert not service.cache


def test_retained_current_running_producer_cannot_sync(owner):
    service, node, plot, _ = owner
    service.run_state.node_execution_workspace_id = plot.provenance.workspace_id
    service.run_state.running_node_ids = {node.node_id}
    assert not service.accepted(plot)
    assert service.close_updates(service.active, event()) == ("", {})


def test_close_notification_connection_changes_are_rechecked_before_commit(owner):
    service, node, plot, _ = owner
    node_id, updates = service.close_updates(service.active, event())
    service.active = None
    workspace, _ = service._node(plot)
    node.exposed_ports["x_axis_interval"] = True
    workspace.edges["edge"] = SimpleNamespace(enabled=True, target_node_id=node.node_id, target_port_key="x_axis_interval")
    service.scene.set_node_properties = Mock(return_value=True)
    service.commit(plot, node_id, updates)
    service.scene.set_node_properties.assert_called_once_with(node_id, {"y_axis_interval": Interval1D(.2, 1.2)})


def test_acknowledged_cache_rebase_is_consumed_before_external_input_ranges(owner, monkeypatch):
    service, node, plot, current = owner
    node_id, updates = service.close_updates(service.active, event())
    service.active = None
    assert service.commit(plot, node_id, updates)
    replacement = replace(plot, settings=replace(plot.settings, x_bounds=(.5, 1.5), y_bounds=(.2, 1.2)))
    current["plot"] = replacement
    monkeypatch.setattr("ea_node_editor.ui.xy_plot_session.XYPlotSession", lambda plot, initial, *args, **kwargs:
                        SimpleNamespace(plot=plot, initial=initial, toolbar_style_requested=Mock()))
    reopened = service.open(replacement, "panel")
    assert reopened.initial["ranges"]["x"] == [.5, 1.5]
    assert "expected_bounds" not in next(iter(service.cache.values()))
    service.active = None
    external = replace(replacement, settings=replace(replacement.settings, x_bounds=(100, 200)))
    current["plot"] = external
    reopened = service.open(external, "panel")
    assert reopened.initial["ranges"]["x"] == [100, 200]
    assert not service.cache


@pytest.mark.parametrize("existing,automatic", [
    (("1970-01-01T00:00:00.000500Z", "1970-01-01T00:00:00.002000Z"), []),
    (("1970-01-01T00:00:00.000100Z", "1970-01-01T00:00:00.001500Z"), []),
    (("", "1970-01-01T00:00:00.001500Z"), ["x"]),
])
def test_datetime_partial_changes_commit_from_merged_bounds(owner, existing, automatic):
    service, node, plot, current = owner
    signal = PlotSignal("signal-0", ArrayValue.from_numpy(np.array([0, 1, 2], dtype='datetime64[ms]')), plot.signals[0].y, x_kind="datetime")
    plot = replace(plot, signals=(signal,))
    current["plot"] = plot
    service.active.plot = plot
    node.properties.update(x_datetime_start=existing[0], x_datetime_end=existing[1])
    node_id, updates = service.close_updates(service.active, event(changed_axes=["x"], automatic=automatic))
    service.active = None
    assert service.commit(plot, node_id, updates)
    assert node.properties["x_datetime_start"] == ("" if automatic else "1970-01-01T00:00:00.000500Z")
    assert node.properties["x_datetime_end"] == ("" if automatic else "1970-01-01T00:00:00.001500Z")
