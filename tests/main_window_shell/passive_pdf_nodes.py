from __future__ import annotations

import gc
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QMarginsF, QMetaObject, QPoint, QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QPageLayout, QPageSize, QPdfWriter
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtTest import QTest

from tests.main_window_shell.base import *  # noqa: F401,F403

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DIRECT_ENV = "EA_NODE_EDITOR_PASSIVE_PDF_NODES_DIRECT"
_SUBPROCESS_RUNNER = (
    "import os, sys, unittest; "
    f"os.environ[{_DIRECT_ENV!r}] = '1'; "
    "target = sys.argv[1]; "
    "suite = unittest.defaultTestLoader.loadTestsFromName(target); "
    "result = unittest.TextTestRunner(verbosity=2).run(suite); "
    "sys.exit(0 if result.wasSuccessful() else 1)"
)


class _SubprocessPassivePdfNodeTest(unittest.TestCase):
    __test__ = False

    def __init__(self, target: str) -> None:
        super().__init__(methodName="runTest")
        self._target = target

    def id(self) -> str:
        return self._target

    def __str__(self) -> str:
        return self._target

    def shortDescription(self) -> str:
        return self._target

    def runTest(self) -> None:
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        result = subprocess.run(
            [sys.executable, "-c", _SUBPROCESS_RUNNER, self._target],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        output = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )
        raise AssertionError(
            f"Subprocess passive PDF node test failed for {self._target} "
            f"(exit={result.returncode}).\n{output}"
        )


def _write_pdf(path: Path, *, page_count: int = 2) -> None:
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
    painter = QPainter(writer)
    for page_index in range(page_count):
        if page_index > 0:
            writer.newPage()
        painter.drawText(QRectF(80.0, 120.0, 420.0, 120.0), f"PDF page {page_index + 1}")
    painter.end()
    del painter
    del writer
    gc.collect()


class MainWindowShellPassivePdfNodesTests(MainWindowShellTestBase):
    def setUp(self) -> None:
        super().setUp()
        self._held_qml_refs: list[QQuickItem] = []

    def tearDown(self) -> None:
        try:
            super().tearDown()
        finally:
            self._held_qml_refs = []
            gc.collect()

    def _hold_qml_ref(self, item: QQuickItem) -> QQuickItem:
        self._held_qml_refs.append(item)
        return item

    def _walk_items(self, item: QQuickItem):
        yield item
        for child in item.childItems():
            yield from self._walk_items(child)

    def _graph_node_card(self, node_id: str) -> QQuickItem:
        graph_canvas = self._graph_canvas_item()
        for item in self._walk_items(graph_canvas):
            if item.objectName() != "graphNodeCard":
                continue
            node_data = item.property("nodeData") or {}
            if str(node_data.get("node_id", "")) == node_id:
                return self._hold_qml_ref(item)
        self.fail(f"Could not find graphNodeCard for node {node_id!r}.")

    def _graph_node_child_with_property(
        self,
        node_id: str,
        object_name: str,
        property_name: str,
        expected_value: str,
    ) -> QQuickItem:
        card = self._graph_node_card(node_id)
        for item in self._walk_items(card):
            if item.objectName() != object_name:
                continue
            if str(item.property(property_name)) == expected_value:
                return self._hold_qml_ref(item)
        self.fail(
            f"Could not find {object_name!r} for node {node_id!r} "
            f"with {property_name!r}={expected_value!r}."
        )

    @staticmethod
    def _item_scene_center(item: QQuickItem) -> QPoint:
        scene_point = item.mapToScene(QPointF(item.width() * 0.5, item.height() * 0.5))
        return QPoint(round(scene_point.x()), round(scene_point.y()))

    def _inspector_property_object(self, object_name: str, property_key: str) -> QQuickItem:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        for item in self._walk_items(root_object):
            if item.objectName() != object_name:
                continue
            if str(item.property("propertyKey")) != property_key:
                continue
            if not bool(item.property("visible")):
                continue
            return self._hold_qml_ref(item)
        self.fail(f"Could not find {object_name!r} for property {property_key!r}.")

    def _selected_property_items(self) -> dict[str, dict]:
        return {item["key"]: item for item in self.window.selected_node_property_items}

    def test_pdf_panel_inspector_exposes_locked_editor_modes(self) -> None:
        node_id = self.window.scene.add_node_from_type("passive.media.pdf_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        items = self._selected_property_items()
        self.assertEqual(items["source_path"]["editor_mode"], "path")
        self.assertEqual(items["page_number"]["editor_mode"], "text")
        self.assertEqual(items["caption"]["editor_mode"], "textarea")

        self._inspector_property_object("inspectorPathEditor", "source_path")
        self._inspector_property_object("inspectorTextareaEditor", "caption")

    def test_pdf_panel_path_editor_browse_commits_selected_path(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.pdf_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        picked_path = Path(self._env.temp_path) / "picked-preview.pdf"
        _write_pdf(picked_path, page_count=2)

        path_editor = self._inspector_property_object("inspectorPathEditor", "source_path")
        browse_button = self._inspector_property_object("inspectorPathBrowseButton", "source_path")

        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName", return_value=(str(picked_path), "")):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        preview_info = self.window.describe_pdf_preview(node.properties["source_path"], node.properties["page_number"])
        self.assertEqual(node.properties["source_path"], str(picked_path))
        self.assertEqual(str(path_editor.property("text")), str(picked_path))
        self.assertEqual(preview_info["state"], "ready")
        self.assertEqual(preview_info["page_count"], 2)

    def test_pdf_panel_inline_path_editor_commits_without_node_drag(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.pdf_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        picked_path = Path(self._env.temp_path) / "graph-inline-picked.pdf"
        _write_pdf(picked_path, page_count=2)

        path_editor = self._graph_node_child_with_property(
            node_id,
            "graphNodeInlinePathEditor",
            "propertyKey",
            "source_path",
        )
        browse_button = self._graph_node_child_with_property(
            node_id,
            "graphNodeInlinePathBrowseButton",
            "propertyKey",
            "source_path",
        )
        self.assertTrue(bool(path_editor.property("visible")))
        self.assertTrue(bool(browse_button.property("visible")))
        workspace = self.window.model.project.workspaces[workspace_id]
        initial_x = float(workspace.nodes[node_id].x)
        initial_y = float(workspace.nodes[node_id].y)

        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName", return_value=(str(picked_path), "")):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = workspace.nodes[node_id]
        preview_info = self.window.describe_pdf_preview(node.properties["source_path"], node.properties["page_number"])
        self.assertEqual(self.window.scene.selected_node_id(), node_id)
        self.assertEqual(node.properties["source_path"], str(picked_path))
        self.assertEqual(str(path_editor.property("text")), str(picked_path))
        self.assertEqual(preview_info["state"], "ready")
        self.assertEqual(preview_info["page_count"], 2)
        self.assertAlmostEqual(float(node.x), initial_x, places=6)
        self.assertAlmostEqual(float(node.y), initial_y, places=6)

    def test_pdf_panel_out_of_range_page_is_rewritten_after_pdf_resolves(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.pdf_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        pdf_path = Path(self._env.temp_path) / "clamped-preview.pdf"
        _write_pdf(pdf_path, page_count=2)

        self.window.set_selected_node_property("source_path", str(pdf_path))
        self.app.processEvents()
        self.window.set_selected_node_property("page_number", "99")
        self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        items = self._selected_property_items()
        preview_info = self.window.describe_pdf_preview(node.properties["source_path"], node.properties["page_number"])

        self.assertEqual(node.properties["page_number"], 2)
        self.assertEqual(items["page_number"]["value"], 2)
        self.assertEqual(preview_info["requested_page_number"], 2)
        self.assertEqual(preview_info["resolved_page_number"], 2)
        self.assertEqual(preview_info["page_count"], 2)


def load_tests(loader, standard_tests, pattern):
    if os.environ.get(_DIRECT_ENV) == "1":
        return standard_tests

    suite = unittest.TestSuite()
    for test_name in sorted(name for name in dir(MainWindowShellPassivePdfNodesTests) if name.startswith("test_")):
        suite.addTest(
            _SubprocessPassivePdfNodeTest(
                f"{MainWindowShellPassivePdfNodesTests.__module__}."
                f"{MainWindowShellPassivePdfNodesTests.__qualname__}.{test_name}"
            )
        )
    return suite
