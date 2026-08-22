from __future__ import annotations

from contextlib import contextmanager
import gc
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch
from urllib.parse import quote

from PyQt6.QtCore import QMarginsF, QRectF, QSize, QUrl
from PyQt6.QtGui import QPainter, QPageLayout, QPageSize, QPdfWriter
from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.artifact_refs import format_managed_artifact_ref
from ea_node_editor.persistence.artifact_refs import format_staged_artifact_ref
from ea_node_editor.ui import pdf_preview_provider as pdf_preview_provider_module
from ea_node_editor.ui.pdf_preview_provider import (
    LOCAL_PDF_PREVIEW_PROVIDER_ID,
    LocalPdfPreviewImageProvider,
    clamp_pdf_page_number,
    describe_pdf_preview,
    set_pdf_preview_project_context_provider,
)
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics

_REPO_ROOT = Path(__file__).resolve().parents[1]
_QML_PROBE_TIMEOUT_SECONDS = 180


def _normalize_partial_process_output(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace").strip()
    return str(value or "").strip()


def _write_pdf(path: Path, *, page_count: int = 1, landscape: bool = False) -> None:
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(
        QPageLayout.Orientation.Landscape if landscape else QPageLayout.Orientation.Portrait
    )
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


@contextmanager
def _pdf_preview_project_context(
    *,
    project_path: Path | None,
    project_metadata: dict[str, object] | None,
):
    set_pdf_preview_project_context_provider(lambda: (project_path, project_metadata))
    try:
        yield
    finally:
        set_pdf_preview_project_context_provider(None)


class PassivePdfNodeCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_default_registry_registers_locked_pdf_panel_spec(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.pdf_panel")

        self.assertEqual(spec.display_name, "PDF Panel")
        self.assertEqual(spec.category, "Media")
        self.assertEqual(spec.runtime_behavior, "passive")
        self.assertEqual(spec.surface_family, "media")
        self.assertEqual(spec.surface_variant, "pdf_panel")
        self.assertFalse(spec.collapsible)
        self.assertEqual(
            tuple((port.key, port.direction, port.allow_multiple_connections, port.side) for port in spec.ports),
            (
                ("top", "neutral", True, "top"),
                ("right", "neutral", True, "right"),
                ("bottom", "neutral", True, "bottom"),
                ("left", "neutral", True, "left"),
            ),
        )
        self.assertEqual(spec.render_quality.supported_quality_tiers, ("full", "proxy"))
        self.assertEqual(
            tuple(prop.key for prop in spec.properties),
            ("source_path", "page_number", "show_title", "show_frame"),
        )

        source_path = next(prop for prop in spec.properties if prop.key == "source_path")
        page_number = next(prop for prop in spec.properties if prop.key == "page_number")

        self.assertEqual(source_path.type, "path")
        self.assertEqual(source_path.inline_editor, "path")
        self.assertEqual(page_number.type, "int")
        self.assertEqual(page_number.default, 1)

    def test_media_surface_metrics_use_locked_pdf_panel_defaults(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.pdf_panel")
        node = NodeInstance(
            node_id="node_pdf_panel",
            type_id=spec.type_id,
            title="PDF Panel",
            x=20.0,
            y=30.0,
        )

        metrics = node_surface_metrics(node, spec, {node.node_id: node})

        self.assertEqual(metrics.default_width, 268.0)
        self.assertEqual(metrics.default_height, 396.0)
        self.assertEqual(metrics.min_width, 228.0)
        self.assertEqual(metrics.min_height, 320.0)
        self.assertEqual(metrics.title_top, 12.0)
        self.assertEqual(metrics.title_height, 24.0)
        self.assertEqual(metrics.body_top, 44.0)
        self.assertEqual(metrics.body_bottom_margin, 12.0)
        self.assertTrue(metrics.use_host_chrome)
        self.assertNotIn("show_header_background", metrics.to_payload())
        self.assertNotIn("show_accent_bar", metrics.to_payload())

    def test_media_surface_metrics_auto_size_default_height_from_local_pdf_ratio(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.pdf_panel")
        with tempfile.TemporaryDirectory() as temp_dir:
            portrait_path = Path(temp_dir) / "portrait.pdf"
            landscape_path = Path(temp_dir) / "landscape.pdf"
            _write_pdf(portrait_path, landscape=False)
            _write_pdf(landscape_path, landscape=True)

            portrait_node = NodeInstance(
                node_id="node_pdf_panel_portrait",
                type_id=spec.type_id,
                title="PDF Panel",
                x=20.0,
                y=30.0,
                properties={"source_path": str(portrait_path), "page_number": 1},
            )
            landscape_node = NodeInstance(
                node_id="node_pdf_panel_landscape",
                type_id=spec.type_id,
                title="PDF Panel",
                x=20.0,
                y=30.0,
                properties={"source_path": str(landscape_path), "page_number": 1},
            )

            portrait_metrics = node_surface_metrics(portrait_node, spec, {portrait_node.node_id: portrait_node})
            landscape_metrics = node_surface_metrics(landscape_node, spec, {landscape_node.node_id: landscape_node})

            self.assertGreater(portrait_metrics.default_height, landscape_metrics.default_height)
            self.assertAlmostEqual(portrait_metrics.default_height, 395.6302521008403, places=5)
            self.assertAlmostEqual(landscape_metrics.default_height, 320.0, places=6)

    def test_media_surface_metrics_auto_size_default_height_from_managed_pdf_ref(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.pdf_panel")
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "artifact_demo.cxproj"
            managed_pdf_path = (
                project_path.with_name("artifact_demo.data")
                / "nodes"
                / "PDF Panel [11111111]"
                / "in"
                / "media"
                / "portrait.pdf"
            )
            managed_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            _write_pdf(managed_pdf_path, landscape=False)

            managed_node = NodeInstance(
                node_id="node_pdf_panel_managed_portrait",
                type_id=spec.type_id,
                title="PDF Panel",
                x=20.0,
                y=30.0,
                properties={
                    "source_path": format_managed_artifact_ref("portrait_pdf"),
                    "page_number": 1,
                },
            )

            with _pdf_preview_project_context(
                project_path=project_path,
                project_metadata={
                    "artifact_store": {
                        "artifacts": {
                            "portrait_pdf": {"relative_path": "nodes/PDF Panel [11111111]/in/media/portrait.pdf"},
                        }
                    }
                },
            ):
                managed_metrics = node_surface_metrics(managed_node, spec, {managed_node.node_id: managed_node})

            self.assertAlmostEqual(managed_metrics.default_height, 395.6302521008403, places=5)

    def test_scene_bridge_silently_clamps_out_of_range_pdf_pages(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "clamped.pdf"
            _write_pdf(pdf_path, page_count=2)

            node_id = scene.add_node_from_type("passive.media.pdf_panel", 40.0, 60.0)
            scene.set_node_property(node_id, "source_path", str(pdf_path))
            scene.set_node_property(node_id, "page_number", 99)

            node = model.project.workspaces[workspace_id].nodes[node_id]
            payload = next(item for item in scene.nodes_model if item["node_id"] == node_id)

            self.assertEqual(node.properties["page_number"], 2)
            self.assertEqual(payload["properties"]["page_number"], 2)

    def test_scene_bridge_silently_clamps_out_of_range_managed_pdf_pages(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "artifact_demo.cxproj"
            managed_pdf_path = project_path.with_name("artifact_demo.data") / "nodes" / "PDF Panel [11111111]" / "in" / "media" / "clamped.pdf"
            managed_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            _write_pdf(managed_pdf_path, page_count=2)

            with _pdf_preview_project_context(
                project_path=project_path,
                project_metadata={
                    "artifact_store": {
                        "artifacts": {
                            "managed_pdf": {"relative_path": "nodes/PDF Panel [11111111]/in/media/clamped.pdf"},
                        }
                    }
                },
            ):
                node_id = scene.add_node_from_type("passive.media.pdf_panel", 40.0, 60.0)
                scene.set_node_property(node_id, "source_path", format_managed_artifact_ref("managed_pdf"))
                scene.set_node_property(node_id, "page_number", 99)

            node = model.project.workspaces[workspace_id].nodes[node_id]
            payload = next(item for item in scene.nodes_model if item["node_id"] == node_id)

            self.assertEqual(node.properties["page_number"], 2)
            self.assertEqual(payload["properties"]["page_number"], 2)


class PdfPreviewProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_describe_preview_reads_only_requested_page_size_for_large_pdf(self) -> None:
        class _FakePageSize:
            def width(self) -> float:
                return 612.0

            def height(self) -> float:
                return 792.0

        page_size_calls: list[int] = []

        class _FakePdfDocument:
            class Error:
                None_ = "none"

            def __init__(self, _parent) -> None:  # noqa: ANN001
                pass

            def load(self, _path_text: str) -> str:
                return self.Error.None_

            def pageCount(self) -> int:
                return 400

            def pagePointSize(self, page_index: int) -> _FakePageSize:
                page_size_calls.append(page_index)
                return _FakePageSize()

            def close(self) -> None:
                pass

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "large.pdf"
            pdf_path.write_bytes(b"%PDF fake")
            pdf_preview_provider_module._cached_pdf_page_count.cache_clear()
            pdf_preview_provider_module._cached_pdf_page_point_size.cache_clear()
            try:
                with patch.object(pdf_preview_provider_module, "QPdfDocument", _FakePdfDocument):
                    info = pdf_preview_provider_module.describe_pdf_preview(str(pdf_path), 399)
            finally:
                pdf_preview_provider_module._cached_pdf_page_count.cache_clear()
                pdf_preview_provider_module._cached_pdf_page_point_size.cache_clear()

        self.assertEqual(info["state"], "ready")
        self.assertEqual(info["page_count"], 400)
        self.assertEqual(info["resolved_page_number"], 399)
        self.assertEqual(page_size_calls, [398])

    def test_describe_preview_and_provider_render_single_page_preview(self) -> None:
        provider = LocalPdfPreviewImageProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "preview.pdf"
            _write_pdf(pdf_path, page_count=2)

            info = describe_pdf_preview(str(pdf_path), 9)
            self.assertEqual(info["state"], "ready")
            self.assertEqual(info["page_count"], 2)
            self.assertEqual(info["requested_page_number"], 9)
            self.assertEqual(info["resolved_page_number"], 2)
            self.assertTrue(str(info["preview_url"]).startswith(f"image://{LOCAL_PDF_PREVIEW_PROVIDER_ID}/"))
            self.assertEqual(clamp_pdf_page_number(str(pdf_path), 9), 2)

            image, size = provider.requestImage(
                f"preview?source={quote(str(pdf_path), safe='')}&page=9",
                QSize(220, 220),
            )

        self.assertFalse(image.isNull())
        self.assertGreater(size.width(), 0)
        self.assertGreater(size.height(), 0)
        self.assertLessEqual(size.width(), 220)
        self.assertLessEqual(size.height(), 220)
        paper_pixel = image.pixelColor(0, 0)
        self.assertEqual(paper_pixel.alpha(), 255)
        self.assertGreaterEqual(paper_pixel.red(), 250)
        self.assertGreaterEqual(paper_pixel.green(), 250)
        self.assertGreaterEqual(paper_pixel.blue(), 250)

    def test_describe_preview_and_provider_render_managed_pdf_ref(self) -> None:
        provider = LocalPdfPreviewImageProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "artifact_demo.cxproj"
            managed_pdf_path = project_path.with_name("artifact_demo.data") / "nodes" / "PDF Panel [11111111]" / "in" / "media" / "preview.pdf"
            managed_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            _write_pdf(managed_pdf_path, page_count=2)
            managed_ref = format_managed_artifact_ref("preview_pdf")

            with _pdf_preview_project_context(
                project_path=project_path,
                project_metadata={
                    "artifact_store": {
                        "artifacts": {
                            "preview_pdf": {"relative_path": "nodes/PDF Panel [11111111]/in/media/preview.pdf"},
                        }
                    }
                },
            ):
                info = describe_pdf_preview(managed_ref, 9)
                self.assertEqual(info["state"], "ready")
                self.assertEqual(info["page_count"], 2)
                self.assertEqual(info["requested_page_number"], 9)
                self.assertEqual(info["resolved_page_number"], 2)
                self.assertEqual(Path(QUrl(info["resolved_source_url"]).toLocalFile()), managed_pdf_path)
                self.assertTrue(str(info["preview_url"]).startswith(f"image://{LOCAL_PDF_PREVIEW_PROVIDER_ID}/"))
                self.assertEqual(clamp_pdf_page_number(managed_ref, 9), 2)

                image, size = provider.requestImage(
                    f"preview?source={quote(managed_ref, safe='')}&page=9",
                    QSize(220, 220),
                )

        self.assertFalse(image.isNull())
        self.assertGreater(size.width(), 0)
        self.assertGreater(size.height(), 0)
        self.assertLessEqual(size.width(), 220)
        self.assertLessEqual(size.height(), 220)

    def test_describe_preview_and_provider_render_staged_pdf_ref(self) -> None:
        provider = LocalPdfPreviewImageProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "artifact_demo.cxproj"
            staged_pdf_path = (
                project_path.with_name("artifact_demo.data")
                / "nodes"
                / "PDF Panel [11111111]"
                / "tmp"
                / "in"
                / "media"
                / "preview.pdf"
            )
            staged_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            _write_pdf(staged_pdf_path, page_count=2)
            staged_ref = format_staged_artifact_ref("preview_pdf")

            with _pdf_preview_project_context(
                project_path=project_path,
                project_metadata={
                    "artifact_store": {
                        "staged": {
                            "preview_pdf": {"relative_path": "nodes/PDF Panel [11111111]/tmp/in/media/preview.pdf"},
                        }
                    }
                },
            ):
                info = describe_pdf_preview(staged_ref, 9)
                self.assertEqual(info["state"], "ready")
                self.assertEqual(info["page_count"], 2)
                self.assertEqual(info["requested_page_number"], 9)
                self.assertEqual(info["resolved_page_number"], 2)
                self.assertEqual(Path(QUrl(info["resolved_source_url"]).toLocalFile()), staged_pdf_path)
                self.assertTrue(str(info["preview_url"]).startswith(f"image://{LOCAL_PDF_PREVIEW_PROVIDER_ID}/"))
                self.assertEqual(clamp_pdf_page_number(staged_ref, 9), 2)

                image, size = provider.requestImage(
                    f"preview?source={quote(staged_ref, safe='')}&page=9",
                    QSize(220, 220),
                )

        self.assertFalse(image.isNull())
        self.assertGreater(size.width(), 0)
        self.assertGreater(size.height(), 0)
        self.assertLessEqual(size.width(), 220)
        self.assertLessEqual(size.height(), 220)

    def test_missing_invalid_and_non_local_sources_return_error_imagery(self) -> None:
        provider = LocalPdfPreviewImageProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "invalid.pdf"
            invalid_path.write_text("not a pdf", encoding="utf-8")
            missing_path = Path(temp_dir) / "missing.pdf"

            missing_info = describe_pdf_preview(str(missing_path), 1)
            invalid_info = describe_pdf_preview(str(invalid_path), 1)
            remote_info = describe_pdf_preview("https://example.com/manual.pdf", 1)
            relative_info = describe_pdf_preview("docs/manual.pdf", 1)

            self.assertEqual(missing_info["state"], "error")
            self.assertEqual(invalid_info["state"], "error")
            self.assertEqual(remote_info["state"], "error")
            self.assertEqual(relative_info["state"], "error")

            for image_id in (
                f"preview?source={quote(str(missing_path), safe='')}&page=1",
                f"preview?source={quote(str(invalid_path), safe='')}&page=1",
                f"preview?source={quote('https://example.com/manual.pdf', safe='')}&page=1",
                f"preview?source={quote('docs/manual.pdf', safe='')}&page=1",
            ):
                image, size = provider.requestImage(image_id, QSize(180, 240))
                self.assertFalse(image.isNull())
                self.assertEqual(size.width(), 180)
                self.assertEqual(size.height(), 240)

    def test_provider_releases_file_handle_after_render(self) -> None:
        provider = LocalPdfPreviewImageProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "handle.pdf"
            renamed_path = Path(temp_dir) / "handle-renamed.pdf"
            _write_pdf(pdf_path, page_count=1)

            image, _size = provider.requestImage(
                f"preview?source={quote(str(pdf_path), safe='')}&page=1",
                QSize(200, 280),
            )
            self.assertFalse(image.isNull())

            pdf_path.rename(renamed_path)
            renamed_path.unlink()


class PassivePdfNodeSurfaceQmlTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        script = textwrap.dedent(
            """
            import gc
            import tempfile
            from pathlib import Path

            from PyQt6.QtCore import QMarginsF, QObject, QRectF, QUrl, pyqtSlot
            from PyQt6.QtGui import QPainter, QPageLayout, QPageSize, QPdfWriter
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtQuick import QQuickItem
            from PyQt6.QtTest import QTest
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.persistence.artifact_refs import format_managed_artifact_ref
            from ea_node_editor.persistence.artifact_refs import format_staged_artifact_ref
            from ea_node_editor.ui.pdf_preview_provider import (
                LOCAL_PDF_PREVIEW_PROVIDER_ID,
                LocalPdfPreviewImageProvider,
                describe_pdf_preview,
                set_pdf_preview_project_context_provider,
            )
            from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
            from ea_node_editor.ui_qml.surface_contracts import surface_spec_payload_for_values
            from ea_node_editor.ui_qml.theme_bridge import ThemeBridge

            app = QApplication.instance() or QApplication([])

            class PdfCanvasItem(QQuickItem):
                @pyqtSlot(str, "QVariant", result="QVariantMap")
                def describeNodeSurfacePdfPreview(self, source, page_number):
                    return describe_pdf_preview(source, page_number)

            engine = QQmlEngine()
            engine.addImageProvider(LOCAL_PDF_PREVIEW_PROVIDER_ID, LocalPdfPreviewImageProvider())
            engine.rootContext().setContextProperty("themeBridge", ThemeBridge(theme_id="stitch_dark"))
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridge(theme_id="graph_stitch_dark"))

            repo_root = Path.cwd()
            graph_node_host_qml_path = repo_root / "ea_node_editor" / "ui_qml" / "components" / "graph" / "GraphNodeHost.qml"

            def create_component(path, initial_properties):
                component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
                if component.status() != QQmlComponent.Status.Ready:
                    errors = "\\n".join(error.toString() for error in component.errors())
                    raise AssertionError(f"Failed to load {path.name}:\\n{errors}")
                if hasattr(component, "createWithInitialProperties"):
                    obj = component.createWithInitialProperties(initial_properties)
                else:
                    obj = component.create()
                    for key, value in initial_properties.items():
                        obj.setProperty(key, value)
                if obj is None:
                    errors = "\\n".join(error.toString() for error in component.errors())
                    raise AssertionError(f"Failed to instantiate {path.name}:\\n{errors}")
                app.processEvents()
                return obj

            def named_child_items(root, object_name):
                matches = []

                def visit(item):
                    if not hasattr(item, "childItems"):
                        return
                    if item.objectName() == object_name:
                        matches.append(item)
                    for child in item.childItems():
                        visit(child)

                visit(root)
                return matches

            def variant_value(value):
                return value.toVariant() if hasattr(value, "toVariant") else value

            def variant_list(value):
                normalized = variant_value(value)
                if normalized is None:
                    return []
                return list(normalized)

            def wait_for_preview(surface, attempts=50):
                for _index in range(attempts):
                    app.processEvents()
                    state = str(surface.property("previewState"))
                    if state in {"ready", "error"}:
                        return
                    QTest.qWait(20)
                raise AssertionError(
                    f"Timed out waiting for PDF preview; state={surface.property('previewState')}"
                )

            def wait_for_pdf_page_count(surface, page_count, attempts=80):
                for _index in range(attempts):
                    app.processEvents()
                    if int(surface.property("pdfPageCount") or 0) == page_count:
                        return
                raise AssertionError(
                    f"Expected pdfPageCount {page_count}, got {surface.property('pdfPageCount')}"
                )

            def pdf_panel_payload(properties):
                return {
                    "node_id": "node_pdf_panel_surface_test",
                    "type_id": "passive.media.pdf_panel",
                    "title": "PDF Panel",
                    "x": 100.0,
                    "y": 110.0,
                    "width": 268.0,
                    "height": 396.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": "media",
                    "surface_variant": "pdf_panel",
                    "surface_spec": surface_spec_payload_for_values(
                        type_id="passive.media.pdf_panel",
                        family="media",
                        variant="pdf_panel",
                    ),
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [
                        {
                            "key": "top",
                            "label": "top",
                            "direction": "neutral",
                            "kind": "flow",
                            "data_type": "flow",
                            "side": "top",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "right",
                            "label": "right",
                            "direction": "neutral",
                            "kind": "flow",
                            "data_type": "flow",
                            "side": "right",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "bottom",
                            "label": "bottom",
                            "direction": "neutral",
                            "kind": "flow",
                            "data_type": "flow",
                            "side": "bottom",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "left",
                            "label": "left",
                            "direction": "neutral",
                            "kind": "flow",
                            "data_type": "flow",
                            "side": "left",
                            "exposed": True,
                            "connected": False,
                        },
                    ],
                    "inline_properties": [],
                    "properties": properties,
                }

            def make_pdf(path, page_count=1):
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
            """
        )
        completion_marker = "__COREX_PDF_QML_PROBE_COMPLETED__"
        script = (
            script
            + "\n"
            + textwrap.dedent(body)
            + f"\nprint({completion_marker!r}, flush=True)\nimport os\nos._exit(0)\n"
        )
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        command = [sys.executable, "-c", script]
        started_at = time.monotonic()
        try:
            result = subprocess.run(
                command,
                cwd=_REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=_QML_PROBE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - started_at
            stdout = _normalize_partial_process_output(exc.stdout)
            stderr = _normalize_partial_process_output(exc.stderr)
            self.fail(
                f"{label} probe timed out after {_QML_PROBE_TIMEOUT_SECONDS} seconds "
                f"(elapsed={elapsed:.3f}s)\n"
                f"command: {command!r}\n"
                f"stdout: {stdout or '<empty>'}\n"
                f"stderr: {stderr or '<empty>'}"
            )
        if result.returncode == 0:
            return
        details = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
        self.fail(f"{label} probe failed with exit code {result.returncode}\n{details}")

    def test_qml_probe_timeout_reports_partial_output(self) -> None:
        timeout = subprocess.TimeoutExpired(
            ["python", "-c", "probe"],
            _QML_PROBE_TIMEOUT_SECONDS,
            output=b"partial stdout",
            stderr=b"partial stderr",
        )
        with (
            patch.object(subprocess, "run", side_effect=timeout),
            patch.object(time, "monotonic", side_effect=[10.0, 190.25]),
            self.assertRaises(AssertionError) as caught,
        ):
            self._run_qml_probe("pdf-timeout", "pass")

        message = str(caught.exception)
        self.assertIn("pdf-timeout probe timed out after 180 seconds (elapsed=180.250s)", message)
        self.assertIn(f"command: [{sys.executable!r}, '-c', ", message)
        self.assertIn("partial stdout", message)
        self.assertIn("partial stderr", message)

    def test_graph_node_host_loads_pdf_panel_surface_states_and_badge(self) -> None:
        self._run_qml_probe(
            "pdf-surface",
            """
            placeholder_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": pdf_panel_payload(
                        {
                            "source_path": "",
                            "page_number": 1,
                        }
                    ),
                },
            )
            placeholder_surface = placeholder_host.findChild(QObject, "graphNodeMediaSurface")
            assert placeholder_surface is not None
            assert placeholder_surface.property("previewState") == "placeholder"
            assert len(named_child_items(placeholder_host, "graphNodeInputPortMouseArea")) == 2
            assert len(named_child_items(placeholder_host, "graphNodeOutputPortMouseArea")) == 2
            assert not any(item.isVisible() for item in named_child_items(placeholder_host, "graphNodeInputPortLabel"))
            assert not any(item.isVisible() for item in named_child_items(placeholder_host, "graphNodeOutputPortLabel"))

            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
                pdf_path = Path(temp_dir) / "ready.pdf"
                make_pdf(pdf_path, page_count=2)
                ready_canvas = PdfCanvasItem()

                ready_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "canvasItem": ready_canvas,
                        "nodeData": pdf_panel_payload(
                            {
                                "source_path": str(pdf_path),
                                "page_number": 9,
                            }
                        ),
                    },
                )
                ready_surface = ready_host.findChild(QObject, "graphNodeMediaSurface")
                badge = ready_host.findChild(QObject, "graphNodeMediaPageBadge")
                hint = ready_host.findChild(QObject, "graphNodeMediaPreviewHint")
                wait_for_pdf_page_count(ready_surface, 2)
                ready_state = str(ready_surface.property("previewState"))
                assert ready_state in {"placeholder", "ready"}, ready_state
                assert ready_surface.property("resolvedSourceUrl").startswith("file:///")
                assert ready_surface.property("pdfPageCount") == 2
                assert ready_surface.property("pdfResolvedPageNumber") == 2
                assert badge is not None
                assert hint is not None
                if ready_state == "ready":
                    assert bool(badge.property("visible"))
                    assert not bool(hint.property("visible"))
                ready_actions = variant_list(ready_surface.property("surfaceActions"))
                navigation_action = next(action for action in ready_actions if action["id"] == "pdf_page_navigation")
                assert navigation_action["label"] == "Navigate"
                assert navigation_action["icon"] == "navigate"
                assert navigation_action["popover_layout"] == "pdf_page"
                assert navigation_action["page_value"] == 2
                assert navigation_action["page_max"] == 2
                assert [action["id"] for action in navigation_action["popoverActions"]] == [
                    "pdf_page_previous",
                    "pdf_page_next",
                ]

            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
                project_path = Path(temp_dir) / "artifact_demo.cxproj"
                managed_pdf_path = project_path.with_name("artifact_demo.data") / "nodes" / "PDF Panel [11111111]" / "in" / "media" / "managed.pdf"
                managed_pdf_path.parent.mkdir(parents=True, exist_ok=True)
                make_pdf(managed_pdf_path, page_count=2)
                set_pdf_preview_project_context_provider(
                    lambda: (
                        project_path,
                        {
                            "artifact_store": {
                                "artifacts": {
                                    "managed_pdf": {"relative_path": "nodes/PDF Panel [11111111]/in/media/managed.pdf"},
                                }
                            }
                        },
                    )
                )
                managed_canvas = PdfCanvasItem()

                managed_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "canvasItem": managed_canvas,
                        "nodeData": pdf_panel_payload(
                            {
                                "source_path": format_managed_artifact_ref("managed_pdf"),
                                "page_number": 9,
                            }
                        ),
                    },
                )
                managed_surface = managed_host.findChild(QObject, "graphNodeMediaSurface")
                wait_for_pdf_page_count(managed_surface, 2)
                managed_state = str(managed_surface.property("previewState"))
                assert managed_state in {"placeholder", "ready"}, managed_state
                assert managed_surface.property("resolvedSourceUrl").startswith("file:///")
                assert managed_surface.property("pdfPageCount") == 2
                assert managed_surface.property("pdfResolvedPageNumber") == 2
                set_pdf_preview_project_context_provider(None)

            error_canvas = PdfCanvasItem()
            error_host = create_component(
                graph_node_host_qml_path,
                {
                    "canvasItem": error_canvas,
                    "nodeData": pdf_panel_payload(
                        {
                            "source_path": "https://example.com/remote.pdf",
                            "page_number": 1,
                        }
                    ),
                },
            )
            error_surface = error_host.findChild(QObject, "graphNodeMediaSurface")
            wait_for_preview(error_surface)
            assert error_surface.property("previewState") == "error"
            assert error_surface.property("resolvedSourceUrl") == ""
            """,
        )

    def test_pdf_panel_keeps_current_page_visible_while_next_page_preview_loads(self) -> None:
        self._run_qml_probe(
            "pdf-page-navigation-retains-current-preview",
            """
            import time

            from PyQt6.QtCore import QSize, pyqtSlot
            from PyQt6.QtGui import QImage
            from PyQt6.QtQuick import QQuickImageProvider, QQuickItem
            from PyQt6.QtTest import QTest

            class SlowPdfPageProvider(QQuickImageProvider):
                def __init__(self):
                    super().__init__(QQuickImageProvider.ImageType.Image)
                    self.requests = []

                def requestImage(self, image_id, requested_size):
                    image_key = str(image_id or "")
                    self.requests.append(image_key)
                    if "page2" in image_key:
                        time.sleep(0.35)
                    image = QImage(32, 44, QImage.Format.Format_ARGB32)
                    image.fill(0xFF79B7D8 if "page1" in image_key else 0xFFD8A679)
                    return image, QSize(image.width(), image.height())

            class SlowPdfCanvasItem(QQuickItem):
                @pyqtSlot(str, "QVariant", result="QVariantMap")
                def describeNodeSurfacePdfPreview(self, source, page_number):
                    page = max(1, min(2, int(float(page_number or 1))))
                    return {
                        "state": "ready",
                        "message": f"Page {page} of 2.",
                        "resolved_source_url": "file:///C:/fixtures/manual.pdf",
                        "preview_url": f"image://slow-pdf-page-preview/page{page}",
                        "page_count": 2,
                        "requested_page_number": page,
                        "resolved_page_number": page,
                        "file_stamp_token": "fixture",
                        "page_point_width": 320.0,
                        "page_point_height": 440.0,
                    }

            provider = SlowPdfPageProvider()
            engine.addImageProvider("slow-pdf-page-preview", provider)
            canvas = SlowPdfCanvasItem()
            host = create_component(
                graph_node_host_qml_path,
                {
                    "canvasItem": canvas,
                    "nodeData": pdf_panel_payload(
                        {
                            "source_path": "C:/fixtures/manual.pdf",
                            "page_number": 1,
                        }
                    ),
                },
            )
            surface = host.findChild(QObject, "graphNodeMediaSurface")
            viewport = host.findChild(QObject, "graphNodeMediaPreviewViewport")
            hint = host.findChild(QObject, "graphNodeMediaPreviewHint")
            preview_image = host.findChild(QObject, "graphNodeMediaPreviewImage")
            assert surface is not None
            assert viewport is not None
            assert hint is not None
            assert preview_image is not None

            def commit_pdf_property(_node_id, key, value):
                payload = dict(host.property("nodeData") or {})
                properties = dict(payload.get("properties") or {})
                properties[str(key)] = variant_value(value)
                payload["properties"] = properties
                host.setProperty("nodeData", payload)

            host.inlinePropertyCommitted.connect(commit_pdf_property)

            wait_for_preview(surface)
            assert surface.property("previewState") == "ready", surface.property("previewState")
            assert not bool(hint.property("visible")), hint.property("visible")
            assert "page1" in str(preview_image.property("source")), preview_image.property("source")

            assert bool(surface.dispatchSurfaceAction("pdf_page_next"))
            app.processEvents()

            assert surface.property("pdfResolvedPageNumber") == 2, surface.property("pdfResolvedPageNumber")
            assert surface.property("previewState") == "ready", surface.property("previewState")
            assert not bool(hint.property("visible")), hint.property("visible")
            assert "page1" in str(preview_image.property("source")), {
                "source": str(preview_image.property("source")),
                "pending": str(viewport.property("pendingPdfPreviewSource") or ""),
            }

            for _index in range(80):
                app.processEvents()
                if "page2" in str(preview_image.property("source")):
                    break
                QTest.qWait(20)
            assert "page2" in str(preview_image.property("source")), {
                "source": str(preview_image.property("source")),
                "surface_preview": surface.property("previewSourceUrl"),
                "requests": provider.requests,
            }
            assert surface.property("previewState") == "ready", surface.property("previewState")
            assert not bool(hint.property("visible")), hint.property("visible")
            assert any("page2" in request for request in provider.requests), provider.requests
            """,
        )

    def test_pdf_panel_promotes_internal_preview_after_page_navigation(self) -> None:
        self._run_qml_probe(
            "pdf-internal-page-navigation-promotes-preview",
            """
            from PyQt6.QtTest import QTest

            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
                project_path = Path(temp_dir) / "artifact_demo.cxproj"
                internal_relative_path = (
                    "workspaces/Workspace 1 [11111111]/"
                    "nodes/PDF Panel [22222222]/tmp/in/media/internal.pdf"
                )
                internal_pdf_path = project_path.with_name("artifact_demo.data") / internal_relative_path
                internal_pdf_path.parent.mkdir(parents=True, exist_ok=True)
                make_pdf(internal_pdf_path, page_count=3)
                internal_ref = format_staged_artifact_ref("internal_pdf")
                set_pdf_preview_project_context_provider(
                    lambda: (
                        project_path,
                        {
                            "artifact_store": {
                                "staged": {
                                    "internal_pdf": {"relative_path": internal_relative_path},
                                }
                            }
                        },
                    )
                )

                try:
                    canvas = PdfCanvasItem()
                    host = create_component(
                        graph_node_host_qml_path,
                        {
                            "canvasItem": canvas,
                            "nodeData": pdf_panel_payload(
                                {
                                    "source_path": internal_ref,
                                    "page_number": 1,
                                }
                            ),
                        },
                    )
                    surface = host.findChild(QObject, "graphNodeMediaSurface")
                    viewport = host.findChild(QObject, "graphNodeMediaPreviewViewport")
                    preview_image = host.findChild(QObject, "graphNodeMediaPreviewImage")
                    assert surface is not None
                    assert viewport is not None
                    assert preview_image is not None

                    def commit_pdf_property(_node_id, key, value):
                        payload = dict(host.property("nodeData") or {})
                        properties = dict(payload.get("properties") or {})
                        properties[str(key)] = variant_value(value)
                        payload["properties"] = properties
                        host.setProperty("nodeData", payload)

                    host.inlinePropertyCommitted.connect(commit_pdf_property)

                    wait_for_pdf_page_count(surface, 3)
                    assert surface.property("pdfResolvedPageNumber") == 1
                    assert "page=1" in str(surface.property("previewSourceUrl")), surface.property("previewSourceUrl")

                    for _index in range(80):
                        app.processEvents()
                        displayed = str(viewport.property("displayedPdfPreviewSource") or "")
                        image_source = str(preview_image.property("source") or "")
                        if "page=1" in displayed and "page=1" in image_source:
                            break
                        QTest.qWait(20)
                    assert "page=1" in str(viewport.property("displayedPdfPreviewSource") or ""), {
                        "displayed": str(viewport.property("displayedPdfPreviewSource") or ""),
                        "preview": str(surface.property("previewSourceUrl") or ""),
                        "image": str(preview_image.property("source") or ""),
                    }

                    assert bool(surface.dispatchSurfaceAction("pdf_page_next"))
                    app.processEvents()

                    node_payload = dict(host.property("nodeData") or {})
                    node_properties = dict(node_payload.get("properties") or {})
                    assert int(node_properties.get("page_number") or 0) == 2, node_properties
                    assert surface.property("pdfResolvedPageNumber") == 2, surface.property("pdfResolvedPageNumber")
                    assert "page=2" in str(surface.property("previewSourceUrl")), surface.property("previewSourceUrl")

                    for _index in range(100):
                        app.processEvents()
                        displayed = str(viewport.property("displayedPdfPreviewSource") or "")
                        pending = str(viewport.property("pendingPdfPreviewSource") or "")
                        if "page=2" in displayed and not pending:
                            break
                        QTest.qWait(20)

                    assert "page=2" in str(viewport.property("displayedPdfPreviewSource") or ""), {
                        "displayed": str(viewport.property("displayedPdfPreviewSource") or ""),
                        "pending": str(viewport.property("pendingPdfPreviewSource") or ""),
                        "preview": str(surface.property("previewSourceUrl") or ""),
                        "image": str(preview_image.property("source") or ""),
                    }
                    assert str(viewport.property("pendingPdfPreviewSource") or "") == ""
                finally:
                    set_pdf_preview_project_context_provider(None)
            """,
        )

    def test_graph_node_host_accepts_explicit_stale_pdf_page_count_refresh_without_property_edit(self) -> None:
        self._run_qml_probe(
            "pdf-surface-refresh",
            """
            class StaleFirstPdfCanvasItem(PdfCanvasItem):
                def __init__(self):
                    super().__init__()
                    self.calls = 0

                @pyqtSlot(str, "QVariant", result="QVariantMap")
                def describeNodeSurfacePdfPreview(self, source, page_number):
                    self.calls += 1
                    info = dict(describe_pdf_preview(source, page_number))
                    if self.calls == 1 and info.get("state") == "ready":
                        info["page_count"] = 1
                        info["resolved_page_number"] = 1
                    return info

            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
                pdf_path = Path(temp_dir) / "refresh.pdf"
                make_pdf(pdf_path, page_count=2)
                canvas = StaleFirstPdfCanvasItem()
                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "canvasItem": canvas,
                        "nodeData": pdf_panel_payload(
                            {
                                "source_path": str(pdf_path),
                                "page_number": 1,
                            }
                        ),
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                wait_for_pdf_page_count(surface, 1)
                assert surface.property("pdfResolvedPageNumber") == 1
                assert canvas.calls == 1
                assert bool(surface._refreshPdfPreviewInfo())
                wait_for_pdf_page_count(surface, 2)
                assert surface.property("pdfResolvedPageNumber") == 1
                assert canvas.calls >= 2
            """,
        )

    def test_pdf_panel_proxy_preview_activates_for_proxy_quality_tier(self) -> None:
        self._run_qml_probe(
            "pdf-proxy-surface",
            """
            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
                pdf_path = Path(temp_dir) / "proxy.pdf"
                make_pdf(pdf_path, page_count=2)

                registry = build_default_registry()
                model = GraphModel()
                workspace_id = model.active_workspace.workspace_id
                scene = GraphSceneBridge()
                scene.set_workspace(model, registry, workspace_id)
                node_id = scene.add_node_from_type("passive.media.pdf_panel", 100.0, 110.0)
                scene.set_node_property(node_id, "source_path", str(pdf_path))
                scene.set_node_property(node_id, "page_number", 9)
                payload = next(item for item in scene.nodes_model if item["node_id"] == node_id)
                payload["render_quality"] = {
                    "supported_quality_tiers": ["full", "proxy"],
                }
                pdf_canvas = PdfCanvasItem()

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "canvasItem": pdf_canvas,
                        "nodeData": payload,
                    },
                )
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                preview_image = host.findChild(QObject, "graphNodeMediaPreviewImage")
                proxy_preview = host.findChild(QObject, "graphNodeMediaProxyPreview")
                proxy_detail = host.findChild(QObject, "graphNodeMediaProxyPreviewDetail")
                badge = host.findChild(QObject, "graphNodeMediaPageBadge")
                assert loader is not None
                assert surface is not None
                assert preview_image is not None
                assert proxy_preview is not None
                assert proxy_detail is not None
                assert badge is not None

                wait_for_pdf_page_count(surface, 2)
                idle_state = {
                    "preview_state": surface.property("previewState"),
                    "preview_visible": bool(preview_image.property("visible")),
                    "host_quality": host.property("resolvedQualityTier"),
                    "proxy_requested": bool(host.property("proxySurfaceRequested")),
                }
                assert host.property("resolvedQualityTier") == "full", idle_state
                assert not bool(host.property("proxySurfaceRequested")), idle_state
                assert surface.property("pdfPageCount") == 2, idle_state
                assert surface.property("pdfResolvedPageNumber") == 2, idle_state

                host.setProperty("snapshotReuseActive", True)
                for _index in range(40):
                    app.processEvents()
                    if bool(surface.property("proxySurfaceActive")):
                        break

                proxy_state = {
                    "preview_state": surface.property("previewState"),
                    "host_quality": host.property("resolvedQualityTier"),
                    "proxy_requested": bool(host.property("proxySurfaceRequested")),
                    "surface_proxy_active": bool(surface.property("proxySurfaceActive")),
                    "loader_proxy_active": bool(loader.property("proxySurfaceActive")),
                    "proxy_visible": bool(proxy_preview.property("visible")),
                    "preview_visible": bool(preview_image.property("visible")),
                    "badge_visible": bool(badge.property("visible")),
                    "detail_text": str(proxy_detail.property("text")),
                }
                assert surface.property("previewState") == "ready", proxy_state
                assert host.property("resolvedQualityTier") == "proxy", proxy_state
                assert bool(host.property("proxySurfaceRequested")), proxy_state
                assert bool(surface.property("proxySurfaceActive")), proxy_state
                assert bool(loader.property("proxySurfaceActive")), proxy_state
                assert bool(proxy_preview.property("visible")), proxy_state
                assert not bool(preview_image.property("visible")), proxy_state
                assert bool(badge.property("visible")), proxy_state
                assert "Page 2 of 2" in str(proxy_detail.property("text")), proxy_state
            """,
        )


if __name__ == "__main__":
    unittest.main()
