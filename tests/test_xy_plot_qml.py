# Purpose: Exercise the production XY QML WebEngine host with native Qt input.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_plot_qml.py
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.parametrize("narrow", [False, True])
def test_production_xy_qml_host(narrow):
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None)
    env.pop("QT_QUICK_BACKEND", None)
    result = subprocess.run([sys.executable, "-m", "tests.test_xy_plot_qml", "--probe"] + (["--narrow"] if narrow else []),
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr


def _probe(narrow=False, *, exercise=None, plot_transform=None, initial_probes=None):
    print("XY QML probe: imports", flush=True)
    import json
    import time
    from dataclasses import replace
    from types import SimpleNamespace
    import numpy as np
    from PyQt6.QtCore import Q_ARG, QMetaObject, QObject, QPoint, Qt, QUrl, qInstallMessageHandler
    from PyQt6.QtQml import QQmlComponent
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
    from PyQt6.QtTest import QTest
    from ea_node_editor.app import prepare_qt_application_attributes
    from ea_node_editor.ui_qml.qml_host_factory import create_shell_qml_host
    from ea_node_editor.runtime_contracts import ArrayValue, PlotSignal
    from ea_node_editor.ui.xy_plot_session import XYPlotSession, session_presentation
    from tests.test_plot_value import plot_value

    print("XY QML probe: initialize Qt", flush=True)
    prepare_qt_application_attributes()
    app = QApplication(["corex-xy-qml-probe"])
    qInstallMessageHandler(lambda kind, context, message: print("Qt:", message, flush=True))
    print("XY QML probe: create session", flush=True)
    parent = QObject()
    rng = np.random.default_rng(7)
    x = np.linspace(0, 100, 12000)
    y = np.sin(x) + rng.normal(0, .1, len(x))
    base = plot_value()
    plot = replace(base, signals=(PlotSignal("signal-0", ArrayValue.from_numpy(x), ArrayValue.from_numpy(y)),),
                   settings=replace(base.settings, marker_sizes=(3,), x_bounds=(10, 90)))
    if plot_transform:
        plot = plot_transform(plot)
    initial_view = {"ranges": {axis: list(value) for axis, value in
                    {"x": plot.settings.x_bounds, "y": plot.settings.y_bounds}.items() if value}, "selection": None}
    session = XYPlotSession(plot, initial_view, "Ranges sync on close.", parent, probe_state=initial_probes)
    print("XY QML probe: create QML", flush=True)
    errors, closed, style_changes = [], [], []
    session.toolbar_style_requested.connect(style_changes.append)
    session.failed.connect(errors.append)
    session.close_ready.connect(closed.append)
    window = QWidget()
    window.setWindowTitle("COREX XY fullscreen verification")
    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    qml_host = create_shell_qml_host(window, host_kind="qquickwidget")
    layout.addWidget(qml_host.container_widget)
    engine = qml_host.engine()
    component = QQmlComponent(engine)
    source = b'''import QtQuick 2.15
import "components/web"
Item {
 id: root; width: 1000; height: 720
 property var payload: ({}); property var bridge: null; property string result: ""
 function evaluate(code) { plot.webEngineItem.runJavaScript(code, function(value) { root.result=JSON.stringify(value === undefined ? null : value); }); }
 XYPlotHost { id: plot; anchors.fill: parent; payload: root.payload; sessionBridge: root.bridge }
}'''
    component.setData(source, QUrl.fromLocalFile(str(Path.cwd() / "ea_node_editor/ui_qml/xy_probe.qml")))
    host_width = 360 if narrow else 1140
    root = component.createWithInitialProperties({"width": host_width, "height": 810, "payload": session_presentation(session), "bridge": session})
    print("XY QML probe: show window", flush=True)
    if root is None:
        print([error.toString() for error in component.errors()], flush=True)
        session.retire(); session.thread.wait(); session.dispose()
        raise AssertionError("QML component unavailable")
    qml_host.widget.setContent(QUrl(), component, root)
    qml_host.set_resize_mode_to_root_object()
    window.resize(host_width, 810)
    window.show()
    window.raise_()
    window.activateWindow()
    qml_window = qml_host.quick_window()
    assert QTest.qWaitForWindowActive(window, 5000), "The desktop rendering probe must be active"
    print("XY QML probe: window shown", flush=True)

    def spin(predicate, label, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            app.processEvents()
            if errors: raise AssertionError(errors)
            if predicate(): return
            QTest.qWait(20)
        raise AssertionError(label)

    def evaluate(code):
        root.setProperty("result", "")
        assert QMetaObject.invokeMethod(root, "evaluate", Q_ARG("QVariant", code)) is None
        spin(lambda: root.property("result") != "", "JS result")
        return json.loads(root.property("result"))

    def click(selector):
        rect = evaluate(f"(()=>{{const e=document.querySelector({json.dumps(selector)});if(!e)throw Error('missing control');const r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];}})()")
        QTest.mouseClick(qml_window, Qt.MouseButton.LeftButton, pos=QPoint(round(rect[0]), round(rect[1])))
        QTest.qWait(100)

    def animation_frame(label):
        evaluate("window.probeFrame=false;requestAnimationFrame(()=>window.probeFrame=true);true")
        spin(lambda: evaluate("window.probeFrame"), label, timeout=3)

    def capture(name):
        if os.environ.get("COREX_XY_CAPTURE") == "1":
            if 'tooltip' not in name:
                QTest.mouseMove(qml_window, QPoint(2, 400))
            animation_frame("capture frame")
            target = Path.cwd() / "artifacts" / f"xy_ui_{name}.png"
            assert qml_host.container_widget.grab().save(str(target))

    def assert_layout():
        bounds = evaluate("[...document.querySelectorAll('#toolbar > div > button')].map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]})")
        assert len(bounds) == 10 and all(0 <= r[0] < r[2] <= host_width for r in bounds), bounds
        for index, left in enumerate(bounds):
            for right in bounds[index+1:]:
                assert left[2] <= right[0] or right[2] <= left[0] or left[3] <= right[1] or right[3] <= left[1], bounds
        assert evaluate("document.querySelector('#toolbar').getBoundingClientRect().bottom <= document.querySelector('#chart').getBoundingClientRect().top")
        assert evaluate("document.querySelector('#chart').getBoundingClientRect().height > innerHeight * .6")
        assert evaluate("[...document.querySelectorAll('#toolbar .tool-icon use')].every(e=>document.querySelector(e.getAttribute('href')))")
        assert evaluate("getComputedStyle(document.querySelector('[data-xy-slot=modebar]')).display") == 'none'

    try:
        host = root.findChild(QObject, "xyPlotHost")
        spin(lambda: host.property("webEngineItem") is not None, "WebEngine host creation")
        spin(lambda: bool(evaluate("Boolean(window.corexXY && window.corexXY.ready)")), "XY readiness")
        spin(lambda: evaluate("[innerWidth,innerHeight]") == [host_width, 810], "positive browser viewport")
        if exercise:
            exercise(SimpleNamespace(plot=plot, session=session, closed=closed, host=host, window=window,
                qml_window=qml_window, widget=qml_host.container_widget, evaluate=evaluate, click=click,
                spin=spin, capture=capture, app=app, narrow=narrow))
            return
        state = evaluate("corexXY.state()")
        animation_frame("frame after mount")
        assert state["ranges"]["x"] == [10, 90], state
        assert evaluate("corexXY.home().ranges.x[0]") < 10
        assert_layout()
        assert evaluate("document.getElementById('inspection').hidden")
        capture('compact_names' if narrow else 'names')
        if not narrow:
            status_height = evaluate("document.getElementById('statusbar').getBoundingClientRect().height")
            assert status_height <= 42, evaluate("({viewport:[innerWidth,innerHeight],items:[...document.querySelectorAll('#statusbar,#statusbar > *, .status-actions > *')].map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return [e.id,r.width,r.height,s.font,s.minWidth,s.flex]})})")
        original_view = evaluate('corexXY.state()')
        click('[data-menu=appearance]')
        menu_bounds = evaluate("(()=>{const r=document.getElementById('menu-appearance').getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]})()")
        assert 0 <= menu_bounds[0] < menu_bounds[2] <= host_width and 0 <= menu_bounds[1] < menu_bounds[3] <= 810
        capture('compact_display_menu' if narrow else 'display_menu')
        click('#menu-appearance [data-toolbar-style=icons_only]')
        assert evaluate('document.body.dataset.toolbarStyle') == 'icons_only'
        assert evaluate("[...document.querySelectorAll('#toolbar .tool-label')].every(e=>getComputedStyle(e).display==='none')")
        assert evaluate('corexXY.state()') == original_view
        assert style_changes == ['icons_only']
        assert_layout()
        capture('compact_icons' if narrow else 'icons')
        point = evaluate("(()=>{const r=document.querySelector('[data-fit=x]').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
        QTest.mouseMove(qml_window, QPoint(round(point[0]), round(point[1])))
        spin(lambda: evaluate("!document.getElementById('plot-tooltip').hidden"), 'icon tooltip')
        assert 'Fit all data on X' in evaluate("document.getElementById('plot-tooltip').textContent")
        capture('compact_tooltip' if narrow else 'tooltip')
        click('[data-menu=appearance]')
        QTest.keyClick(qml_window, Qt.Key.Key_Escape)
        spin(lambda: evaluate("document.getElementById('menu-appearance').hidden"), 'appearance menu dismissal')
        assert not session.closing
        assert evaluate("document.activeElement.dataset.menu") == 'appearance'
        QTest.keyClick(qml_window, Qt.Key.Key_Down)
        spin(lambda: evaluate('document.activeElement.dataset.toolbarStyle') == 'icons_with_names', 'keyboard menu focus')
        QTest.keyClick(qml_window, Qt.Key.Key_Return)
        spin(lambda: evaluate('document.body.dataset.toolbarStyle') == 'icons_with_names', 'keyboard display choice')
        assert evaluate('corexXY.state()') == original_view
        evaluate("corexXY.applyState({selection:{polygon:[[20,-.5],[80,-.5],[80,.5],[20,.5]]}})")
        spin(lambda: bool(evaluate('corexXY.selection && corexXY.selection.count > 0')), 'selection details')
        assert evaluate("document.getElementById('inspection').hidden")
        click('#selection-toggle')
        assert not evaluate("document.getElementById('inspection').hidden")
        assert evaluate("document.querySelectorAll('#sample-rows tbody tr').length") == 8
        assert evaluate("document.getElementById('inspection').getBoundingClientRect().height") <= 251
        capture('compact_details' if narrow else 'details')
        QTest.keyClick(qml_window, Qt.Key.Key_Escape)
        spin(lambda: evaluate("document.getElementById('inspection').hidden"), 'selection drawer dismissal')
        assert not session.closing
        evaluate("corexXY.applyState({selection:{polygon:[[200,0],[210,0],[210,1],[200,1]]}})")
        spin(lambda: evaluate('corexXY.selection.count') == 0, 'empty selection')
        assert not evaluate("document.getElementById('clear').disabled")
        click('#clear')
        assert evaluate('corexXY.state().selection') is None
        assert evaluate("document.getElementById('selection-count').textContent") == 'No selection'
        if narrow:
            session.request_close()
            spin(lambda: bool(closed), 'compact close')
            assert closed[0]['changed_axes'] == [] and closed[0]['automatic'] == []
            print('PASS: compact toolbar, both display styles, tooltips, keyboard menus and bounded selection details', flush=True)
            return
        click('[data-action="pan"]')
        animation_frame("frame after pan pause")
        assert evaluate("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == "none"
        click('[data-action="pan"]')
        animation_frame("frame after pan resume")
        click('[data-menu="selection"]')
        animation_frame("frame after menu open")
        rects = evaluate("[...document.querySelectorAll('#menu-selection button')].map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})")
        assert len(rects) >= 3 and all(rect[2] > 100 and rect[3] >= 20 for rect in rects), rects
        assert all(rects[i][1] + rects[i][3] <= rects[i+1][1] + 1 for i in range(len(rects)-1)), rects
        QTest.keyClick(qml_window, Qt.Key.Key_Escape)
        QTest.qWait(80)
        assert not session.closing, "Escape must close menu before fullscreen"
        click('[data-action="pan"]')
        click('[data-action="pan"]')
        # Native Qt pointer events cross the QML WebEngine surface.
        QTest.mousePress(qml_window, Qt.MouseButton.LeftButton, pos=QPoint(500, 360))
        QTest.mouseMove(qml_window, QPoint(620, 380), delay=50)
        QTest.mouseRelease(qml_window, Qt.MouseButton.LeftButton, pos=QPoint(620, 380))
        QTest.qWait(200)
        moved = evaluate("corexXY.state()")
        assert moved["ranges"] != state["ranges"], moved
        evaluate("corexXY.applyState({selection:{polygon:[[20,-.5],[80,-.5],[80,.5],[20,.5]]}})")
        spin(lambda: bool(evaluate("corexXY.selection && corexXY.selection.count>0")), "canonical selection")
        selection = evaluate("corexXY.state().selection")
        for tool in ("select", "zoom"):
            # Choose the visible host tool, then middle-drag without clicking Pan.
            if tool == "select":
                click('[data-menu=selection]'); click('[data-command=select]')
            else:
                click('[data-action=zoom]')
            prior = evaluate("corexXY.state().ranges")
            QTest.mousePress(qml_window, Qt.MouseButton.MiddleButton, pos=QPoint(500, 280))
            QTest.mouseMove(qml_window, QPoint(570, 300), delay=50)
            QTest.mouseRelease(qml_window, Qt.MouseButton.MiddleButton, pos=QPoint(570, 300))
            QTest.qWait(150)
            assert evaluate("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == tool
            assert evaluate("corexXY.state().ranges") != prior
            assert evaluate("corexXY.state().selection") == selection
        prior = evaluate("corexXY.state().ranges")
        QTest.mousePress(qml_window, Qt.MouseButton.MiddleButton, pos=QPoint(500, 280))
        QTest.mouseMove(qml_window, QPoint(570, 300), delay=50)
        QTest.keyClick(qml_window, Qt.Key.Key_Escape)
        QTest.mouseRelease(qml_window, Qt.MouseButton.MiddleButton, pos=QPoint(570, 300))
        QTest.qWait(150)
        assert evaluate("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == "zoom"
        assert evaluate("corexXY.state().ranges") == prior
        assert not session.closing
        for axis in ("x", "y"):
            click('[data-menu=selection]'); click(f'[data-command=select-{axis}]')
            QTest.mousePress(qml_window, Qt.MouseButton.LeftButton, pos=QPoint(350, 200))
            QTest.mouseMove(qml_window, QPoint(650, 320), delay=50)
            QTest.mouseRelease(qml_window, Qt.MouseButton.LeftButton, pos=QPoint(650, 320))
            QTest.qWait(150)
            selected = evaluate("corexXY.state().selection")
            assert selected["range"]["mode"] == axis
            evaluate("corexXY.applyState({selection:null})")
            evaluate("corexXY.applyState(" + json.dumps({"selection": selected}) + ")")
            assert evaluate("corexXY.state().selection") == selected
        if os.environ.get("COREX_XY_CAPTURE") == "1":
            target = Path.cwd() / "artifacts/xy_fullscreen_qml.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            assert qml_host.container_widget.grab().save(str(target))
        evaluate("document.querySelector('[data-xy-slot=canvas]').focus(); true")
        QTest.keyClick(qml_window, Qt.Key.Key_Escape)
        spin(lambda: bool(closed), "close flush")
        assert closed[0].get("changed_axes"), (closed, evaluate("({ready:corexXY.ready, visibility:document.visibilityState, focus:document.hasFocus(), state:corexXY.state()})"), session._pending)
        assert closed[0]["state"]["selection"]["range"]["mode"] == "y", closed
        # A real second host starts with authored ranges equal to the full-data
        # home. Fit must request automatic ranges even if XY emits no view delta.
        home_ranges = evaluate("corexXY.home().ranges")
        for mixed_axis in (False, True):
            initial_ranges = json.loads(json.dumps(home_ranges))
            if mixed_axis:
                low, high = initial_ranges["y"]
                initial_ranges["y"] = [low + .1*(high-low), high - .1*(high-low)]
            root.setProperty("bridge", None)
            session.retire(); session.thread.wait(); session.dispose()
            closed.clear()
            authored_plot = replace(plot, settings=replace(plot.settings, x_bounds=tuple(initial_ranges["x"]), y_bounds=tuple(initial_ranges["y"])))
            session = XYPlotSession(authored_plot, {"ranges": initial_ranges, "selection": None}, "Reset verification", parent)
            session.failed.connect(errors.append); session.close_ready.connect(closed.append)
            root.setProperty("payload", session_presentation(session)); root.setProperty("bridge", session)
            spin(lambda: host.property("webEngineItem") is not None, "replacement WebEngine")
            spin(lambda: bool(evaluate("Boolean(window.corexXY && window.corexXY.ready)")), "replacement XY readiness")
            click('[data-fit=data]')
            QTest.qWait(100)
            session.request_close()
            spin(lambda: bool(closed), "home reset flush")
            assert set(closed[0]["automatic"]) == {"x", "y"}, closed
        # Reopened views may differ from authored limits. Exercise each visible
        # control with native clicks, including a repeated zero-delta fit.
        dates = np.datetime64('2026-01-01', 'ms') + np.arange(len(x)) * np.timedelta64(1, 's')
        date_ms = dates.astype('int64')
        date_plot = replace(plot, signals=(PlotSignal('signal-0', ArrayValue.from_numpy(dates),
                            ArrayValue.from_numpy(np.geomspace(1, 1000, len(x))), x_kind='datetime'),),
                            settings=replace(plot.settings, logarithmic_y_axis=True,
                            x_bounds=(float(date_ms[2000]), float(date_ms[10000])), y_bounds=(10, 100)))
        for mode, fit_plot in [('x', plot), ('y', plot), ('data', plot), ('limits', plot),
                               ('data', date_plot), ('limits', date_plot)]:
            initial_ranges = ({'x': [float(date_ms[3000]), float(date_ms[8000])], 'y': [20, 50]}
                              if fit_plot is date_plot else {'x': [20, 60], 'y': [-.4, .6]})
            x0, x1 = initial_ranges['x']; y0, y1 = initial_ranges['y']
            kept_selection = {'polygon': [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}
            root.setProperty('bridge', None)
            session.retire(); session.thread.wait(); session.dispose()
            closed.clear()
            session = XYPlotSession(fit_plot, {'ranges': initial_ranges, 'selection': kept_selection}, 'Fit verification', parent)
            session.failed.connect(errors.append); session.close_ready.connect(closed.append)
            root.setProperty('payload', session_presentation(session)); root.setProperty('bridge', session)
            spin(lambda: host.property('webEngineItem') is not None, 'fit WebEngine')
            spin(lambda: bool(evaluate('Boolean(window.corexXY && window.corexXY.ready)')), 'fit XY readiness')
            data_ranges = evaluate('corexXY.home().ranges')
            click('[data-action=zoom]')
            if mode == 'limits':
                click('[data-fit=data]')  # Restoring limits must cancel pending automatic edits.
            click(f'[data-fit={mode}]')
            click(f'[data-fit={mode}]')
            expected = dict(initial_ranges)
            axes = [mode] if mode in ('x', 'y') else ['x', 'y']
            for axis in axes:
                authored_bounds = getattr(fit_plot.settings, f'{axis}_bounds')
                expected[axis] = list(authored_bounds) if mode == 'limits' and authored_bounds else data_ranges[axis]
            fitted = evaluate('corexXY.state()')
            assert fitted['ranges'] == expected, (mode, fitted, expected)
            assert fitted['selection'] == kept_selection
            assert evaluate("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == 'zoom'
            session.request_close()
            spin(lambda: bool(closed), 'fit close flush')
            expected_axes = set() if mode == 'limits' else set(axes)
            assert set(closed[0]['automatic']) == expected_axes, (mode, closed)
            assert set(closed[0]['changed_axes']) == expected_axes, (mode, closed)
            assert closed[0]['state']['ranges'] == expected
        # Capability changes stay engine-owned; line-only plots expose the
        # reason selection is unavailable without offering a dead action.
        root.setProperty('bridge', None)
        session.retire(); session.thread.wait(); session.dispose()
        closed.clear()
        line_plot = replace(plot, settings=replace(plot.settings, marker_shapes=(0,)))
        session = XYPlotSession(line_plot, {'ranges': {}, 'selection': None}, 'Local view', parent)
        session.failed.connect(errors.append); session.close_ready.connect(closed.append)
        root.setProperty('payload', session_presentation(session)); root.setProperty('bridge', session)
        spin(lambda: host.property('webEngineItem') is not None, 'line-only WebEngine')
        spin(lambda: bool(evaluate('Boolean(window.corexXY && window.corexXY.ready)')), 'line-only readiness')
        assert evaluate("document.querySelector('[data-action=selection]').disabled")
        point = evaluate("(()=>{const r=document.querySelector('[data-action=selection]').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
        QTest.mouseMove(qml_window, QPoint(round(point[0]), round(point[1])))
        spin(lambda: evaluate("!document.getElementById('plot-tooltip').hidden"), 'disabled selection explanation')
        assert 'marker samples' in evaluate("document.getElementById('plot-tooltip').textContent")
        session.request_close()
        spin(lambda: bool(closed), 'line-only close')
        assert closed[0]['changed_axes'] == []
        print("PASS: production QQuickWidget host, top toolbar/display styles/tooltips/keyboard, compact readouts/drawer, native gestures, capability gating, selection and numeric/datetime/log fit/close behavior.", flush=True)
    finally:
        session.retire()
        session.thread.wait()
        qml_host.teardown()
        window.close()
        app.processEvents()
        session.dispose()
        window.deleteLater()
        app.processEvents()


if __name__ == "__main__":
    try:
        _probe(narrow="--narrow" in sys.argv)
    except BaseException:
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
