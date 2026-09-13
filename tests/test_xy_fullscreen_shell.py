# Purpose: Prove real COREX graph execution, fullscreen XY writeback and project reopening.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_fullscreen_shell.py
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest


@pytest.mark.gui
def test_xy_fullscreen_through_real_shell():
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None)
    env.pop("QT_QUICK_BACKEND", None)
    result = subprocess.run(
        [sys.executable, "-u", "-m", "tests.test_xy_fullscreen_shell", "--probe"],
        cwd=Path(__file__).resolve().parents[1], env=env,
        capture_output=True, text=True, timeout=240,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _probe(project_path: Path):
    import copy
    import json
    import time

    from ea_node_editor.addons.tabular_data.loader_cache_service import _preload_native_tabular_runtime
    _preload_native_tabular_runtime()
    from ea_node_editor.app import prepare_qt_application_attributes, _register_bundled_application_fonts
    prepare_qt_application_attributes()
    from PyQt6.QtCore import Q_ARG, QMetaObject, QObject, QPointF, QUrl
    from PyQt6.QtQml import QQmlComponent
    from PyQt6.QtQuick import QQuickItem
    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    from ea_node_editor.app_preferences import default_app_preferences_document
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from ea_node_editor.runtime_contracts import PlotValue
    from ea_node_editor.ui.media_panel_source import resolve_media_panel_source
    from ea_node_editor.ui.support.solution_output_cache import current_output_value
    from ea_node_editor.ui.shell.composition import create_shell_window
    from scripts.generate_signal_plot_scientific_example import generate_example

    app = QApplication(["corex-xy-shell-probe"])
    _register_bundled_application_fonts()
    registry = build_default_registry(include_public_plugins=False)
    generate_example(project_path)
    preferences = default_app_preferences_document()
    preferences["solution"] = {"default_mode": "manual"}
    window = create_shell_window(registry=registry, preferences_document=preferences)
    window.resize(1500, 950)
    window.show()
    print("Shell probe: real COREX window created", flush=True)
    run_events = []
    window.execution_event.connect(lambda event: run_events.append(event.get("type")))
    bridge = window.content_fullscreen_bridge
    component = QQmlComponent(window.qml_host.engine())
    component.setData(b'''import QtQml 2.15
QtObject {
 property var target: null
 property string result: ""
 function evaluate(code) {
   target.runJavaScript(code, function(value) { result = JSON.stringify({value: value === undefined ? null : value}); });
 }
}''', QUrl())
    proxy = component.create()
    assert proxy is not None, [e.toString() for e in component.errors()]

    def spin(predicate, label, timeout=60):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            app.processEvents()
            if predicate():
                return
            if label == "graph completion" and not window.run_state.active_run_id and window.console_panel.error_count:
                raise AssertionError(window.console_panel.errors_text)
            QTest.qWait(25)
        raise AssertionError(f"Timeout: {label}; runs={run_events[-12:]}; error={bridge.last_error}; console={window.console_panel.errors_text}")

    def current(port_node, port):
        tree = current_output_value(window.run_state, workspace_id, port_node, port)
        if tree is None or tree.item_count != 1:
            return None
        return next(item for _path, items in tree.branches for item in items)

    def producer():
        return window.model.project.workspaces[workspace_id].nodes[producer_id]

    def run_graph():
        before = len(run_events)
        window.run_controller.run_workflow()
        print("Shell probe: run requested", window.run_state.active_run_id,
              window.run_state.engine_state_value, run_events[before:], flush=True)
        assert window.run_state.active_run_id, window.console_panel.errors_text or window.console_panel.output_text
        spin(lambda: not window.run_state.active_run_id and isinstance(current(panel_id, "_surface_source"), PlotValue),
             "graph completion")
        assert not window.run_state.failed_node_ids

    def evaluate(code):
        proxy.setProperty("result", "")
        QMetaObject.invokeMethod(proxy, "evaluate", Q_ARG("QVariant", code))
        spin(lambda: bool(proxy.property("result")), "JavaScript response", timeout=15)
        return json.loads(proxy.property("result"))["value"]

    def expand():
        before = len(run_events)
        assert bridge.request_open_node(panel_id), bridge.last_error
        assert bridge.content_kind == "media" and bridge.media_payload["media_kind"] == "plot"
        host = None

        def loaded():
            nonlocal host
            host = next((item for item in window.qml_host.root_object().findChildren(QObject, "xyPlotHost")
                         if item.property("sessionBridge") is bridge.xy_plot_bridge), None)
            return host is not None and host.property("webEngineItem") is not None

        spin(loaded, "fullscreen host")
        proxy.setProperty("target", host.property("webEngineItem"))
        expected_url = json.dumps(bridge.xy_plot_bridge.asset_url)
        spin(lambda: evaluate("Boolean(location.href === " + expected_url + " && window.corexXY && corexXY.ready)"), "XY readiness")
        assert len(run_events) == before, "Expansion must not execute upstream nodes"
        return host

    def middle_pan(host):
        web = host.findChild(QQuickItem, "xyPlotWebEngineView")
        assert web is not None
        rect = evaluate("(()=>{const r=document.querySelector('[data-xy-slot=canvas]').getBoundingClientRect();return [r.x+r.width*.55,r.y+r.height*.5];})()")
        point = web.mapToScene(QPointF(*rect))
        target = window.qml_host.quick_window()
        start = point.toPoint()
        end = (point + QPointF(80, 0)).toPoint()
        before = evaluate("corexXY.state().ranges.x")
        QTest.mousePress(target, Qt.MouseButton.MiddleButton, pos=start)
        QTest.mouseMove(target, end, delay=80)
        QTest.mouseRelease(target, Qt.MouseButton.MiddleButton, pos=end)
        spin(lambda: evaluate("corexXY.state().ranges.x") != before, "native middle-pan change")

    def click_tool(host, selector):
        web = host.findChild(QQuickItem, "xyPlotWebEngineView")
        rect = evaluate("(()=>{const r=document.querySelector(" + json.dumps(selector) + ").getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})()")
        point = web.mapToScene(QPointF(*rect)).toPoint()
        QTest.mouseClick(window.qml_host.quick_window(), Qt.MouseButton.LeftButton, pos=point)
        QTest.qWait(100)

    def place_probe(host):
        click_tool(host, '[data-menu=probe]')
        click_tool(host, '[data-command=probe-x]')
        web = host.findChild(QQuickItem, "xyPlotWebEngineView")
        location = evaluate("(()=>{const r=document.querySelector('[data-xy-slot=canvas]').getBoundingClientRect();return [r.x+r.width*.45,r.y+r.height*.5]})()")
        QTest.mouseClick(window.qml_host.quick_window(), Qt.MouseButton.LeftButton,
                         pos=web.mapToScene(QPointF(*location)).toPoint())
        spin(lambda: evaluate("corexXY.probeState().positions.x") is not None, "shell probe placement")
        spin(lambda: evaluate("document.getElementById('probe-status').dataset.total !== undefined"), "shell probe results")
        return probe_state()

    def probe_state():
        # Serialize inside Chromium: Qt's object conversion drops null properties.
        return json.loads(evaluate("JSON.stringify(corexXY.probeState())"))

    try:
        assert window.project_session_controller.open_project_path(project_path, show_errors=False)
        workspace_id = window.model.active_workspace.workspace_id
        workspace = window.model.active_workspace
        producer_id = next(n.node_id for n in workspace.nodes.values() if n.type_id == "plot.signal" and n.title == "csv signals")
        panel_id = next(e.target_node_id for e in workspace.edges.values() if e.source_node_id == producer_id)
        assert current(panel_id, "_surface_source") is None
        run_graph()
        plot = current(panel_id, "_surface_source")
        assert plot.provenance.node_id == producer_id and len(plot.signals[0].x.to_numpy()) == 256
        resolution = resolve_media_panel_source(node=workspace.nodes[panel_id], workspace=workspace,
                                                run_state=window.run_state, project_path=project_path,
                                                project_metadata=window.model.project.metadata)
        assert resolution.media_kind == "plot" and resolution.preview_source_url.startswith("image://")
        print("Shell probe: Signal Plot -> Media Panel retained full PlotValue and PNG preview", flush=True)

        history_before = window.runtime_history.undo_depth(workspace_id)
        host = expand()
        original_state = evaluate("corexXY.state()")
        original_width = evaluate("innerWidth")
        original_session = bridge.xy_plot_bridge
        previous_events = len(run_events)
        window.resize(1300, 850)
        spin(lambda: 0 < evaluate("innerWidth") < original_width, "fullscreen resize")
        evaluate("window.resizedFrame=false;requestAnimationFrame(()=>window.resizedFrame=true);true")
        spin(lambda: evaluate("window.resizedFrame"), "render frame after shell resize")
        assert evaluate("corexXY.state()") == original_state
        click_tool(host, '[data-menu=appearance]')
        click_tool(host, '#menu-appearance [data-toolbar-style=icons_only]')
        spin(lambda: evaluate("document.body.dataset.toolbarStyle") == "icons_only", "toolbar display change")
        from ea_node_editor.settings import app_preferences_path
        saved_preferences = json.loads(app_preferences_path().read_text(encoding="utf-8"))
        assert saved_preferences["graphics"]["plot"]["xy_toolbar_style"] == "icons_only"
        assert bridge.xy_plot_bridge is original_session and len(run_events) == previous_events
        assert window.runtime_history.undo_depth(workspace_id) == history_before
        assert evaluate("corexXY.state()") == original_state
        print("Shell probe: resized live plot; toolbar style persisted without rerun, session replacement or graph edit", flush=True)
        properties_before_probe = copy.deepcopy(producer().properties)
        stored_probe = place_probe(host)
        bridge.request_close()
        spin(lambda: not bridge.open, "probe-only close")
        assert producer().properties == properties_before_probe
        assert window.runtime_history.undo_depth(workspace_id) == history_before
        assert len(run_events) == previous_events and current(panel_id, "_surface_source") is not None
        host = expand()
        assert probe_state() == stored_probe
        print("Shell probe: probe-only close has no graph edit/run; unchanged plot restores cursor state", flush=True)
        middle_pan(host)
        bridge.request_close()
        spin(lambda: not bridge.open, "normal fullscreen close")
        assert producer().properties["x_axis_interval"] is not None
        assert window.runtime_history.undo_depth(workspace_id) == history_before + 1
        assert not window.run_state.active_run_id and current(panel_id, "_surface_source") is None
        assert window.request_undo()
        assert producer().properties["x_axis_interval"] is None
        assert window.request_redo()
        assert producer().properties["x_axis_interval"] is not None
        print("Shell probe: Manual close writes one undoable range edit; undo/redo work", flush=True)

        run_graph()
        window.run_controller.set_auto_run_enabled(True)
        old_signature = current(panel_id, "_surface_source").settings_signature
        host = expand()
        assert evaluate("document.body.dataset.toolbarStyle") == "icons_only"
        actual = probe_state()['positions']
        assert actual == {"x": None, "y": None}, ("Undo/redo invalidates conflicting inspection state", actual)
        stored_probe = place_probe(host)
        middle_pan(host)
        bridge.request_close()
        spin(lambda: not bridge.open, "Auto fullscreen close")
        spin(lambda: not window.run_state.active_run_id and isinstance(current(panel_id, "_surface_source"), PlotValue)
             and current(panel_id, "_surface_source").settings_signature != old_signature, "Auto rerun")
        print("Shell probe: Auto close reruns the normal graph and refreshes the preview", flush=True)

        expand()
        assert probe_state() == stored_probe, "Acknowledged range-only changes preserve probes"
        bridge.request_close()
        spin(lambda: not bridge.open, "restored Auto inspection close")

        window.run_controller.set_auto_run_enabled(False)
        assert window.project_session_controller.save_project()
        assert "\"__ea_runtime_value__\": \"plot_value\"" not in project_path.read_text(encoding="utf-8")
        assert window.project_session_controller.new_project()
        assert window.project_session_controller.open_project_path(project_path, show_errors=False)
        assert current(panel_id, "_surface_source") is None
        assert not bridge._xy_owner.cache
        run_graph()
        expand()
        assert probe_state()['positions'] == {"x": None, "y": None}
        bridge.request_close()
        spin(lambda: not bridge.open, "final close")
        print("PASS: real shell Manual/Auto, middle pan, single undo, refreshed preview and rerun after reopen", flush=True)
    finally:
        proxy.deleteLater()
        window.close()
        app.processEvents()


if __name__ == "__main__" and "--probe" in sys.argv:
    os.environ.pop("QT_QPA_PLATFORM", None)
    os.environ.pop("QT_QUICK_BACKEND", None)
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    with tempfile.TemporaryDirectory(prefix="corex-xy-shell-") as temporary:
        os.environ["APPDATA"] = str(Path(temporary) / "profile")
        _probe(Path(temporary) / "example.cxproj")
