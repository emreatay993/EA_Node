# Purpose: Exercise real cursor placement, editing, paging and gesture coexistence.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_probe_qml.py
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from ea_node_editor.runtime_contracts import ArrayValue, PlotSignal


@pytest.mark.gui
@pytest.mark.parametrize("case", ["numeric", "datetime_log", "restored"])
def test_cursor_probe_desktop(case):
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None); env.pop("QT_QUICK_BACKEND", None)
    result = subprocess.run([sys.executable, "-u", "-m", "tests.test_xy_probe_qml", "--probe", case],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr


def transform(value, case):
    x = value.signals[0].x.to_numpy()
    y = np.sin(x * 8)
    y[3000:3010] = np.nan
    settings = replace(value.settings, show_legend=True, labels=("Measured signal",))
    if case == "datetime_log":
        start = np.datetime64("2026-01-01", "ms")
        dates = start + np.rint(x * 1000).astype('timedelta64[ms]')
        origin = float(start.astype(np.int64))
        settings = replace(settings, x_bounds=(origin + 10000, origin + 90000), logarithmic_y_axis=True)
        signal = PlotSignal("signal-0", ArrayValue.from_numpy(dates), ArrayValue.from_numpy(np.exp(y)), x_kind="datetime")
    else:
        signal = replace(value.signals[0], y=ArrayValue.from_numpy(y))
    return replace(value, signals=(signal,), settings=settings)


def exercise(h, case):
    from PyQt6.QtCore import QPoint, QPointF, Qt
    from PyQt6.QtGui import QImage, QWheelEvent
    from PyQt6.QtTest import QTest
    from ea_node_editor.web_host.xy_probes import query_probe
    e, click, spin = h.evaluate, h.click, h.spin
    def point(selector, dx=0, dy=0):
        xy = e("(()=>{const r=document.querySelector(" + json.dumps(selector) + ").getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
        return QPoint(round(xy[0] + dx), round(xy[1] + dy))
    def canvas_point(u, v):
        xy = e(f"(()=>{{const r=document.querySelector('[data-xy-slot=canvas]').getBoundingClientRect();return [r.x+r.width*{u},r.y+r.height*{v}]}})()")
        return QPoint(round(xy[0]), round(xy[1]))
    def settled():
        spin(lambda: e("document.getElementById('probe-results').getAttribute('aria-busy')==='false' && !!document.getElementById('probe-status').dataset.revision"), 'probe results')
    def choose(axis):
        e(f"(()=>{{const s=document.getElementById('probe-active');s.value='{axis}';s.dispatchEvent(new Event('change',{{bubbles:true}}));}})();true")
    def enter(text):
        click('#probe-position')
        QTest.keyClick(h.qml_window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClicks(h.widget, text)
        QTest.keyClick(h.qml_window, Qt.Key.Key_Return)
    def place(axis, u, v):
        click('[data-menu=probe]'); click(f'[data-command=probe-{axis}]')
        assert e("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == 'none'
        p = canvas_point(u, v)
        QTest.mouseMove(h.qml_window, p)
        QTest.mouseClick(h.qml_window, Qt.MouseButton.LeftButton, pos=p)
        spin(lambda: e(f'corexXY.probeState().positions.{axis}') is not None, 'pinned ' + axis)
        settled()

    # Inspect actual rendered pixels before any selection/probe overlay exists.
    # This catches epoch coordinates collapsing in float32 even when the DOM
    # ranges and full-source worker queries are correct.
    if case != 'restored':
        QTest.qWait(150)
        frame = h.widget.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        pixels = np.frombuffer(frame.bits().asstring(frame.sizeInBytes()), dtype=np.uint8).reshape(frame.height(), frame.bytesPerLine() // 4, 4)
        x, y, w, height = e("(()=>{const r=document.querySelector('[data-xy-slot=canvas]').getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()")
        scale = frame.width() / e('innerWidth')
        crop = pixels[round((y + height * .1) * scale):round((y + height * .7) * scale), round(x * scale):round((x + w) * scale), :3]
        blue = np.all(np.abs(crop.astype(np.int16) - [31, 119, 180]) < 12, axis=2)
        assert np.count_nonzero(np.any(blue, axis=0)) > crop.shape[1] * .5, 'Native traces must span the time/numeric viewport'

    base = e('corexXY.state()')
    if case == 'restored':
        expected = {'positions': {'x': 35.5, 'y': .2}, 'active': 'y', 'method': 'nearest'}
        assert e('corexXY.probeState()') == expected
        settled()
        assert e("document.getElementById('inspection').hidden")
        assert e("document.querySelectorAll('.probe-overlay [data-probe-handle]').length") == 2
        h.session.request_close(); spin(lambda: bool(h.closed), 'restored probe close')
        assert h.closed[0]['probe_state'] == expected and h.closed[0]['changed_axes'] == []
        print('PASS: restored probes without initialization writeback', flush=True)
        return
    x0, x1 = base['ranges']['x']
    y0, y1 = base['ranges']['y']
    polygon = [[x0 + (x1 - x0) * u, y0 + (y1 - y0) * v]
               for u, v in ((.25, .25), (.75, .25), (.75, .75), (.25, .75))]
    e('corexXY.applyState(' + json.dumps({'selection': {'polygon': polygon}}) + ')')
    spin(lambda: bool(e('corexXY.selection && corexXY.selection.count > 0')), 'existing selection')
    selected = e('corexXY.state().selection')
    e("window.probeViewEvents=0;document.querySelector('.corex-xy-chart').addEventListener('xy:view_change',()=>window.probeViewEvents++);true")
    click('[data-action=zoom]')
    place('x', .4, .5)
    assert e("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == 'zoom'
    assert e("document.getElementById('probe-panel').hidden") is False
    state = e('corexXY.probeState()')
    result = query_probe(h.plot, {"axis": "x", "position": state['positions']['x'], "method": "intersections", "ranges": base['ranges'], "revision": 1})
    assert int(e("document.getElementById('probe-status').dataset.total")) == result['total'] == 1
    assert float(e("document.querySelector('#probe-results tbody tr').cells[3].textContent")) == pytest.approx(result['rows'][0]['y'], rel=1e-8)
    place('y', .5, .5)
    assert int(e("document.getElementById('probe-status').dataset.total")) > 50
    assert e("document.querySelectorAll('#probe-results tbody tr').length") == 50
    assert e("document.querySelectorAll('.probe-overlay circle').length") == 50
    assert e("document.querySelectorAll('.probe-overlay [data-probe-handle]').length") == 2
    click('#probe-next'); settled()
    assert e("document.getElementById('probe-status').dataset.page") == '1'
    h.capture('probes_' + case)
    click('#inspection-close')
    before = e('corexXY.probeState()')
    p = point('[data-probe-handle=y]')
    QTest.mousePress(h.qml_window, Qt.MouseButton.LeftButton, pos=p)
    QTest.mouseMove(h.qml_window, p + QPoint(0, 24), delay=60)
    QTest.mouseRelease(h.qml_window, Qt.MouseButton.LeftButton, pos=p + QPoint(0, 24))
    spin(lambda: e('corexXY.probeState().positions.y') != before['positions']['y'], 'dragged handle')
    assert e("document.getElementById('inspection').hidden"), 'Dragging must respect a collapsed drawer'
    before = e('corexXY.probeState()')
    p = point('[data-probe-handle=y]')
    QTest.mousePress(h.qml_window, Qt.MouseButton.LeftButton, pos=p)
    QTest.mouseMove(h.qml_window, p + QPoint(0, 24), delay=60)
    QTest.keyClick(h.qml_window, Qt.Key.Key_Escape)
    QTest.mouseRelease(h.qml_window, Qt.MouseButton.LeftButton, pos=p + QPoint(0, 24))
    spin(lambda: e('corexXY.probeState().positions') == before['positions'], 'cancelled drag')
    click('[data-menu=probe]'); click('[data-command=probe-x]')
    QTest.mouseMove(h.qml_window, canvas_point(.6, .5))
    QTest.keyClick(h.qml_window, Qt.Key.Key_Escape)
    assert e('corexXY.probeState().positions') == before['positions'] and not h.session.closing
    click('[data-menu=probe]'); click('[data-command=probe-x]')
    click('[data-action=pan]')
    assert e("document.querySelector('[data-xy-slot=canvas]').dataset.xyDragmode") == 'pan'
    assert e('corexXY.probeState().positions') == before['positions']
    click('[data-menu=probe]'); click('[data-command=probe-results]')
    choose('x')
    saved = e('corexXY.probeState().positions.x')
    enter('2026-02-30T00:00:00Z' if case == 'datetime_log' else 'not-a-number')
    spin(lambda: bool(e("document.getElementById('probe-validation').textContent")), 'input error')
    assert e('corexXY.probeState().positions.x') == saved
    entered = '2026-01-01T00:00:45.123456Z' if case == 'datetime_log' else '45.25'
    if case == 'numeric':
        enter('25.04'); settled()
        assert int(e("document.getElementById('probe-status').dataset.total")) == 0, 'Interpolation must not bridge a missing-data gap'
    enter(entered); settled()
    assert not e("document.getElementById('probe-validation').textContent")
    assert e('corexXY.state().ranges') == base['ranges']
    assert e('window.probeViewEvents') == 0, 'Probe-only actions must not change axes'
    assert e('corexXY.state().selection') == selected, 'Probe gestures must preserve native selection geometry'
    click('#selection-tab')
    assert e("document.getElementById('selection-panel').hidden") is False
    assert e('corexXY.selection.count') > 0
    click('#probes-tab')
    click('[data-menu=probe]'); click('[data-command=probe-nearest]'); settled()
    assert e("document.querySelector('#probe-results tbody tr').cells[1].textContent") == 'Nearest sample'
    assert e('corexXY.probeState().method') == 'nearest'
    if case == 'datetime_log':
        choose('y'); saved = e('corexXY.probeState().positions.y'); enter('0')
        spin(lambda: bool(e("document.getElementById('probe-validation').textContent")), 'log input error')
        assert e('corexXY.probeState().positions.y') == saved
        QTest.keyClick(h.qml_window, Qt.Key.Key_Escape)
    else:
        # Legend toggles are native UI operations and invalidate probe results.
        click('[data-menu=probe]'); click('[data-command=probe-intersections]'); settled()
        click('[data-xy-slot=legend_item]'); settled()
        assert int(e("document.getElementById('probe-status').dataset.total")) == 0
        click('[data-xy-slot=legend_item]'); settled()
        assert int(e("document.getElementById('probe-status').dataset.total")) == 1

    # Pan with the middle button while both cursor positions remain anchored.
    anchors = e('corexXY.probeState().positions')
    p = canvas_point(.35, .6)
    QTest.mousePress(h.qml_window, Qt.MouseButton.MiddleButton, pos=p)
    QTest.mouseMove(h.qml_window, p + QPoint(30, 10), delay=70)
    QTest.mouseRelease(h.qml_window, Qt.MouseButton.MiddleButton, pos=p + QPoint(30, 10))
    spin(lambda: e('corexXY.state().ranges') != base['ranges'], 'middle pan with probes')
    assert e('corexXY.probeState().positions') == anchors
    e('corexXY.applyState(' + json.dumps({'ranges': base['ranges']}) + ')')
    spin(lambda: e('corexXY.state().ranges') == base['ranges'], 'restored test view')
    settled()
    if case == 'numeric':
        p = canvas_point(.3, .4)
        wheel = QWheelEvent(QPointF(p), QPointF(h.qml_window.mapToGlobal(p)), QPoint(), QPoint(0, 120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        h.app.sendEvent(h.qml_window, wheel)
        spin(lambda: e('corexXY.state().ranges') != base['ranges'], 'wheel zoom with probes')
        assert e('corexXY.probeState().positions') == anchors
        click('[data-fit=data]'); click('[data-fit=limits]')
        spin(lambda: e('corexXY.state().ranges') == base['ranges'], 'fits with probes')
        assert e('corexXY.probeState().positions') == anchors
        click('[data-menu=selection]'); click('[data-command=select]')
        begin, end = canvas_point(.15, .3), canvas_point(.25, .6)
        QTest.mousePress(h.qml_window, Qt.MouseButton.LeftButton, pos=begin)
        QTest.mouseMove(h.qml_window, end, delay=60)
        QTest.mouseRelease(h.qml_window, Qt.MouseButton.LeftButton, pos=end)
        spin(lambda: e('corexXY.state().selection') != selected, 'native selection around cursor handles')
        assert e('corexXY.probeState().positions') == anchors
        size = h.window.size()
        h.window.resize(900, 780)
        spin(lambda: e('innerWidth') == 900, 'resized probe view')
        assert e('corexXY.probeState().positions') == anchors
        assert e("(()=>{const a=document.querySelector('.probe-overlay').getBoundingClientRect(),b=document.querySelector('[data-xy-slot=canvas]').getBoundingClientRect();return Math.abs(a.width-b.width)<1&&Math.abs(a.left-b.left)<1})()")
        h.window.resize(size)
        spin(lambda: e('innerWidth') == 1140, 'original probe size')
    # Off-screen positions remain editable and never move the view automatically.
    choose('x')
    outside = '2026-01-02T00:00:00Z' if case == 'datetime_log' else '1000'
    enter(outside); settled()
    assert 'outside the visible window' in e("document.getElementById('probe-status').textContent")
    assert e('corexXY.state().ranges') == base['ranges']
    enter(entered); settled()
    click('[data-menu=appearance]'); click('#menu-appearance [data-toolbar-style=icons_only]')
    h.capture('probes_icons_' + case)
    if case == 'numeric':
        saved = e('corexXY.probeState().positions')
        click('[data-menu=probe]')
        h.capture('probes_menu')
        click('[data-command=probe-clear]')
        assert json.loads(e('JSON.stringify(corexXY.probeState().positions)')) == {'x': None, 'y': None}
        choose('x'); enter(str(saved['x'])); choose('y'); enter(str(saved['y'])); settled()
    expected = e('corexXY.probeState()')
    h.session.request_close()
    spin(lambda: bool(h.closed), 'probe close flush')
    assert h.closed[0]['probe_state'] == expected
    assert h.closed[0]['changed_axes'] == [] and h.closed[0]['automatic'] == []
    print('PASS: pinned probes, fields, gaps/visibility, paging, cancellation, navigation, UTC/log and separate close state: ' + case, flush=True)


if __name__ == '__main__':
    from tests.test_xy_plot_qml import _probe
    selected = sys.argv[-1]
    initial = {'positions': {'x': 35.5, 'y': .2}, 'active': 'y', 'method': 'nearest'} if selected == 'restored' else None
    _probe(narrow=selected == 'datetime_log', exercise=lambda h: exercise(h, selected),
           plot_transform=lambda p: transform(p, selected), initial_probes=initial)
