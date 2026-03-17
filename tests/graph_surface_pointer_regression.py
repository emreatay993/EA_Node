from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]

QML_POINTER_REGRESSION_HELPERS = textwrap.dedent(
    """
    from PyQt6.QtCore import QPoint, QPointF, Qt
    from PyQt6.QtQuick import QQuickItem, QQuickWindow
    from PyQt6.QtTest import QTest

    def variant_value(value):
        return value.toVariant() if hasattr(value, "toVariant") else value

    def variant_list(value):
        normalized = variant_value(value)
        if normalized is None:
            return []
        return list(normalized)

    def rect_field(rect, key):
        normalized = variant_value(rect)
        if isinstance(normalized, dict):
            return float(normalized[key])
        try:
            value = normalized[key]
        except Exception:
            value = getattr(normalized, key)
        value = variant_value(value)
        return float(value() if callable(value) else value)

    def walk_items(item):
        if isinstance(item, QQuickItem):
            yield item
            for child in item.childItems():
                yield from walk_items(child)

    def named_item(root, object_name, property_key=None):
        for child in walk_items(root):
            if child.objectName() != object_name:
                continue
            if property_key is None or str(child.property("propertyKey")) == property_key:
                return child
        raise AssertionError(f"Missing object {object_name!r} propertyKey={property_key!r}")

    def named_child_items(root, object_name):
        return [child for child in walk_items(root) if child.objectName() == object_name]

    def item_scene_point(item, x_factor=0.5, y_factor=0.5):
        scene_point = item.mapToScene(QPointF(item.width() * x_factor, item.height() * y_factor))
        return QPoint(round(scene_point.x()), round(scene_point.y()))

    def host_scene_point(host, local_x, local_y):
        scene_point = host.mapToScene(QPointF(local_x, local_y))
        return QPoint(round(scene_point.x()), round(scene_point.y()))

    def settle_events(cycles=1):
        for _index in range(max(1, int(cycles))):
            app.processEvents()

    def attach_host_to_window(host, width=480, height=360):
        window = QQuickWindow()
        window.resize(int(width), int(height))
        host.setParentItem(window.contentItem())
        window.show()
        app.processEvents()
        return window

    def dispose_host_window(host, window):
        if window is not None:
            window.close()
        if host is not None:
            host.setParentItem(None)
            host.deleteLater()
        if window is not None:
            window.deleteLater()
        app.processEvents()

    def hover_host_local_point(window, host, local_x, local_y, settle_cycles=5):
        point = host_scene_point(host, local_x, local_y)
        QTest.mouseMove(window, point)
        settle_events(settle_cycles)
        return point

    def host_pointer_events(host):
        clicked = []
        opened = []
        contexts = []
        host.nodeClicked.connect(lambda node_id, additive: clicked.append((node_id, additive)))
        host.nodeOpenRequested.connect(lambda node_id: opened.append(node_id))
        host.nodeContextRequested.connect(
            lambda node_id, local_x, local_y: contexts.append((node_id, local_x, local_y))
        )
        return {"clicked": clicked, "opened": opened, "contexts": contexts}

    def mouse_click(window, point, button=Qt.MouseButton.LeftButton):
        QTest.mouseClick(window, button, Qt.KeyboardModifier.NoModifier, point)
        app.processEvents()

    def mouse_double_click(window, point, button=Qt.MouseButton.LeftButton):
        QTest.mouseDClick(window, button, Qt.KeyboardModifier.NoModifier, point)
        app.processEvents()

    def assert_host_pointer_routing(
        host,
        window,
        control_point,
        body_point,
        expected_node_id,
        expected_body_local=None,
    ):
        events = host_pointer_events(host)

        mouse_click(window, control_point)
        mouse_double_click(window, control_point)
        mouse_click(window, control_point, Qt.MouseButton.RightButton)

        assert events["clicked"] == []
        assert events["opened"] == []
        assert events["contexts"] == []

        mouse_click(window, body_point)
        mouse_double_click(window, body_point)
        mouse_click(window, body_point, Qt.MouseButton.RightButton)

        assert len(events["clicked"]) >= 1
        assert all(entry == (expected_node_id, False) for entry in events["clicked"])
        assert events["opened"] == [expected_node_id]
        assert len(events["contexts"]) == 1
        assert events["contexts"][0][0] == expected_node_id

        if expected_body_local is not None:
            expected_x, expected_y = expected_body_local
            assert abs(float(events["contexts"][0][1]) - float(expected_x)) < 0.5
            assert abs(float(events["contexts"][0][2]) - float(expected_y)) < 0.5
    """
)


def run_qml_probe(test_case: unittest.TestCase, label: str, *blocks: str) -> None:
    script = "\n".join(textwrap.dedent(block).strip("\n") for block in blocks if block)
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        details = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
        test_case.fail(f"{label} probe failed with exit code {result.returncode}\n{details}")


def assert_no_graph_surface_pointer_regressions(test_case: unittest.TestCase) -> None:
    failures = graph_surface_pointer_audit_failures()
    if failures:
        test_case.fail("\n\n".join(failures))


def graph_surface_pointer_audit_failures() -> list[str]:
    graph_dir = _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "graph"
    passive_dir = graph_dir / "passive"
    surface_files = [
        graph_dir / "GraphInlinePropertiesLayer.qml",
        graph_dir / "GraphStandardNodeSurface.qml",
        *sorted(passive_dir.glob("*Surface.qml")),
    ]
    failures: list[str] = []

    hover_proxy_matches = _search_pattern(
        r"hoverActionHitRect|graphNodeSurfaceHoverActionButton",
        [graph_dir, passive_dir],
    )
    if hover_proxy_matches:
        failures.append(
            "Removed hover-proxy compatibility shims reappeared:\n"
            + "\n".join(hover_proxy_matches)
        )

    tap_handler_matches = _search_pattern(r"\\bTapHandler\\s*\\{", surface_files)
    if tap_handler_matches:
        failures.append(
            "Unexpected TapHandler usage in graph-surface QML:\n"
            + "\n".join(tap_handler_matches)
        )

    unexpected_mouse_areas: list[str] = []
    for path in surface_files:
        matches = _search_pattern(r"\\bMouseArea\\s*\\{", [path])
        if not matches:
            continue
        if path.name == "GraphMediaPanelSurface.qml":
            if len(matches) != 1:
                unexpected_mouse_areas.append(
                    f"{path.relative_to(_REPO_ROOT)}: expected exactly one crop-handle MouseArea, found {len(matches)}"
                )
            text = path.read_text(encoding="utf-8")
            if 'objectName: "graphNodeMediaCropHandleMouseArea"' not in text:
                unexpected_mouse_areas.append(
                    f"{path.relative_to(_REPO_ROOT)}: allowed crop-handle MouseArea objectName is missing"
                )
            if "targetItem: handleMouseArea" not in text:
                unexpected_mouse_areas.append(
                    f"{path.relative_to(_REPO_ROOT)}: crop-handle MouseArea is no longer tied to GraphSurfaceInteractiveRegion"
                )
            continue
        unexpected_mouse_areas.extend(matches)

    if unexpected_mouse_areas:
        failures.append(
            "Unexpected raw MouseArea usage in graph-surface QML:\n"
            + "\n".join(unexpected_mouse_areas)
        )

    return failures


def _expand_scan_paths(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(sorted(path.rglob("*.qml")))
        else:
            expanded.append(path)
    return expanded


def _search_pattern(pattern: str, paths: list[Path]) -> list[str]:
    if shutil.which("rg"):
        result = subprocess.run(
            ["rg", "-n", pattern, *[str(path) for path in paths]],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode not in (0, 1):
            raise AssertionError(
                f"rg audit failed for pattern {pattern!r} with exit code {result.returncode}: {result.stderr.strip()}"
            )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    compiled = re.compile(pattern)
    matches: list[str] = []
    for path in _expand_scan_paths(paths):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if compiled.search(line):
                matches.append(f"{path.relative_to(_REPO_ROOT)}:{line_number}:{line.strip()}")
    return matches
