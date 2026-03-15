from __future__ import annotations

import gc
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QMarginsF, QMetaObject, QRectF
from PyQt6.QtGui import QPainter, QPageLayout, QPageSize, QPdfWriter
from PyQt6.QtQuick import QQuickItem

from tests.main_window_shell.base import *  # noqa: F401,F403


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
    def _walk_items(self, item: QQuickItem):
        yield item
        for child in item.childItems():
            yield from self._walk_items(child)

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
            return item
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
