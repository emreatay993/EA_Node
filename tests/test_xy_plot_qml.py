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
def test_production_xy_qml_host():
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None)
    env.pop("QT_QUICK_BACKEND", None)
    result = subprocess.run([sys.executable, "-m", "tests.test_xy_plot_qml", "--probe"],
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr


def _probe():
    print("XY QML probe: imports", flush=True)
    import json
    import time
    from dataclasses import replace
    import numpy as np
    from PyQt6.QtCore import Q_ARG, QMetaObject, QObject, QPoint, Qt, QUrl, qInstallMessageHandler
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtQml import QQmlComponent, QQmlEngine
    from PyQt6.QtQuick import QQuickWindow
    from PyQt6.QtTest import QTest
    from PyQt6.QtWebEngineQuick import QtWebEngineQuick
    from ea_node_editor.runtime_contracts import ArrayValue, PlotSignal
    from ea_node_editor.ui.xy_plot_session import XYPlotSession, session_presentation
    from tests.test_plot_value import plot_value

    print("XY QML probe: initialize Qt", flush=True)
    QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    QtWebEngineQuick.initialize()
    app = QGuiApplication(["corex-xy-qml-probe"])
    qInstallMessageHandler(lambda kind, context, message: print("Qt:", message, flush=True))
    print("XY QML probe: create session", flush=True)
    parent = QObject()
    rng = np.random.default_rng(7)
    x = np.linspace(0, 100, 12000)
    y = np.sin(x) + rng.normal(0, .1, len(x))
    base = plot_value()
    plot = replace(base, signals=(PlotSignal("signal-0", ArrayValue.from_numpy(x), ArrayValue.from_numpy(y)),),
                   settings=replace(base.settings, marker_sizes=(3,), x_bounds=(10, 90)))
    session = XYPlotSession(plot, {"ranges": {"x": [10, 90]}, "selection": None}, "Ranges sync on close.", parent)
    print("XY QML probe: create QML", flush=True)
    errors, closed = [], []
    session.failed.connect(errors.append)
    session.close_ready.connect(closed.append)
    engine = QQmlEngine()
    component = QQmlComponent(engine)
    source = b'''import QtQuick 2.15
import "components/web"
Item {
 id: root; width: 1000; height: 720
 property var payload: ({}); property var bridge: null; property string result: ""
 function evaluate(code) { plot.webEngineItem.runJavaScript(code, function(value) { root.result=JSON.stringify(value); }); }
 XYPlotHost { id: plot; anchors.fill: parent; payload: root.payload; sessionBridge: root.bridge }
}'''
    component.setData(source, QUrl.fromLocalFile(str(Path.cwd() / "ea_node_editor/ui_qml/xy_probe.qml")))
    root = component.createWithInitialProperties({"payload": session_presentation(session), "bridge": session})
    print("XY QML probe: show window", flush=True)
    if root is None:
        print([error.toString() for error in component.errors()], flush=True)
        session.retire(); session.thread.wait(); session.dispose()
        raise AssertionError("QML component unavailable")
    window = QQuickWindow()
    print("XY QML probe: window constructed", flush=True)
    window.setTitle("COREX XY fullscreen verification")
    window.resize(1000, 720)
    root.setParentItem(window.contentItem())
    window.show()
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
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(round(rect[0]), round(rect[1])))
        QTest.qWait(100)

    try:
        host = root.findChild(QObject, "xyPlotHost")
        spin(lambda: host.property("webEngineItem") is not None, "WebEngine host creation")
        spin(lambda: bool(evaluate("Boolean(window.corexXY && window.corexXY.ready)")), "XY readiness")
        state = evaluate("corexXY.state()")
        assert state["ranges"]["x"] == [10, 90], state
        assert evaluate("corexXY.home().ranges.x[0]") < 10
        before = evaluate("(()=>{const c=document.querySelector('canvas');return [c.width,c.height]})()")
        window.resize(1140, 810)
        root.setWidth(1140); root.setHeight(810)
        QTest.qWait(200)
        after = evaluate("(()=>{const c=document.querySelector('canvas');return [c.width,c.height]})()")
        assert after[0] > before[0] and after[1] > before[1], (before, after)
        # The visible fit controls wrap, rather than collide or escape the host.
        window.resize(360, 810); root.setWidth(360)
        QTest.qWait(100)
        fit_rects = evaluate("[...document.querySelectorAll('[data-fit]')].map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom,e.disabled]})")
        assert len(fit_rects) == 4 and all(0 <= r[0] < r[2] <= 360 and not r[4] for r in fit_rects), fit_rects
        for index, left in enumerate(fit_rects):
            for right in fit_rects[index+1:]:
                assert left[2] <= right[0] or right[2] <= left[0] or left[3] <= right[1] or right[3] <= left[1], fit_rects
        window.resize(1140, 810); root.setWidth(1140)
        QTest.qWait(100)
        click('[data-xy-modebar-action="pan"]')
        assert evaluate("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == "none"
        click('[data-xy-modebar-action="pan"]')
        click('[data-xy-modebar-select-trigger]')
        rects = evaluate("[...document.querySelectorAll('[data-xy-modebar-select-menu] button')].map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})")
        assert len(rects) >= 3 and all(rect[2] > 100 and rect[3] >= 20 for rect in rects), rects
        assert all(rects[i][1] + rects[i][3] <= rects[i+1][1] + 1 for i in range(len(rects)-1)), rects
        QTest.keyClick(window, Qt.Key.Key_Escape)
        QTest.qWait(80)
        assert not session.closing, "Escape must close menu before fullscreen"
        click('[data-xy-modebar-action="pan"]')
        click('[data-xy-modebar-action="pan"]')
        # Native Qt pointer events cross the QML WebEngine surface.
        QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(500, 360))
        QTest.mouseMove(window, QPoint(620, 380), delay=50)
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(620, 380))
        QTest.qWait(200)
        moved = evaluate("corexXY.state()")
        assert moved["ranges"] != state["ranges"], moved
        evaluate("corexXY.applyState({selection:{polygon:[[20,-.5],[80,-.5],[80,.5],[20,.5]]}})")
        spin(lambda: bool(evaluate("corexXY.selection && corexXY.selection.count>0")), "canonical selection")
        selection = evaluate("corexXY.state().selection")
        for tool in ("select", "zoom"):
            # Choose the actual native tool, then middle-drag without clicking Pan.
            evaluate("document.querySelector('[data-xy-modebar-" + ("select-item" if tool == "select" else "menu-item") + "=\"" + tool + "\"]').click(); true")
            prior = evaluate("corexXY.state().ranges")
            QTest.mousePress(window, Qt.MouseButton.MiddleButton, pos=QPoint(500, 280))
            QTest.mouseMove(window, QPoint(570, 300), delay=50)
            QTest.mouseRelease(window, Qt.MouseButton.MiddleButton, pos=QPoint(570, 300))
            QTest.qWait(150)
            assert evaluate("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == tool
            assert evaluate("corexXY.state().ranges") != prior
            assert evaluate("corexXY.state().selection") == selection
        prior = evaluate("corexXY.state().ranges")
        QTest.mousePress(window, Qt.MouseButton.MiddleButton, pos=QPoint(500, 280))
        QTest.mouseMove(window, QPoint(570, 300), delay=50)
        QTest.keyClick(window, Qt.Key.Key_Escape)
        QTest.mouseRelease(window, Qt.MouseButton.MiddleButton, pos=QPoint(570, 300))
        QTest.qWait(150)
        assert evaluate("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == "zoom"
        assert evaluate("corexXY.state().ranges") == prior
        assert not session.closing
        for axis in ("x", "y"):
            evaluate(f"document.querySelector('[data-xy-modebar-select-item=\"select-{axis}\"]').click(); true")
            QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(350, 200))
            QTest.mouseMove(window, QPoint(650, 320), delay=50)
            QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(650, 320))
            QTest.qWait(150)
            selected = evaluate("corexXY.state().selection")
            assert selected["range"]["mode"] == axis
            evaluate("corexXY.applyState({selection:null})")
            evaluate("corexXY.applyState(" + json.dumps({"selection": selected}) + ")")
            assert evaluate("corexXY.state().selection") == selected
        if os.environ.get("COREX_XY_CAPTURE") == "1":
            target = Path.cwd() / "artifacts/xy_fullscreen_qml.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            assert window.grabWindow().save(str(target))
        evaluate("document.querySelector('[data-xy-slot=canvas]').focus(); true")
        QTest.keyClick(window, Qt.Key.Key_Escape)
        spin(lambda: bool(closed), "close flush")
        assert closed[0]["changed_axes"], closed
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
            evaluate("document.querySelector('[data-xy-modebar-menu-item=fit]').click(); true")
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
            evaluate("document.querySelector('[data-xy-modebar-menu-item=zoom]').click(); true")
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
        print("PASS: QML render, authored/home view, resize, native Pan toggle/drag, middle-drag with select/zoom and Escape cancellation, expanded menu/Escape, canonical selection, close flush, axis/data/authored fits with datetime/log ranges and wrapped controls.", flush=True)
    finally:
        session.retire()
        session.thread.wait()
        root.deleteLater()
        window.close()
        app.processEvents()
        session.dispose()
        engine.deleteLater()
        app.processEvents()


if __name__ == "__main__":
    try:
        _probe()
    except BaseException:
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
