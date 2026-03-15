from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QSize
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.media_preview_provider import LocalMediaPreviewImageProvider
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics

_REPO_ROOT = Path(__file__).resolve().parents[1]


class PassiveImageNodeCatalogTests(unittest.TestCase):
    def test_default_registry_registers_locked_image_panel_spec(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.image_panel")

        self.assertEqual(spec.display_name, "Image Panel")
        self.assertEqual(spec.category, "Media")
        self.assertEqual(spec.runtime_behavior, "passive")
        self.assertEqual(spec.surface_family, "media")
        self.assertEqual(spec.surface_variant, "image_panel")
        self.assertFalse(spec.collapsible)
        self.assertEqual(spec.ports, ())
        self.assertEqual(tuple(prop.key for prop in spec.properties), ("source_path", "caption", "fit_mode"))

        source_path = next(prop for prop in spec.properties if prop.key == "source_path")
        caption = next(prop for prop in spec.properties if prop.key == "caption")
        fit_mode = next(prop for prop in spec.properties if prop.key == "fit_mode")

        self.assertEqual(source_path.type, "path")
        self.assertEqual(source_path.inline_editor, "path")
        self.assertEqual(caption.type, "str")
        self.assertEqual(caption.inline_editor, "textarea")
        self.assertEqual(caption.inspector_editor, "textarea")
        self.assertEqual(fit_mode.type, "enum")
        self.assertEqual(fit_mode.default, "contain")
        self.assertEqual(fit_mode.enum_values, ("contain", "cover", "original"))

    def test_media_surface_metrics_use_locked_image_panel_defaults(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.image_panel")
        node = NodeInstance(
            node_id="node_image_panel",
            type_id=spec.type_id,
            title="Image Panel",
            x=20.0,
            y=30.0,
        )

        metrics = node_surface_metrics(node, spec, {node.node_id: node})

        self.assertEqual(metrics.default_width, 296.0)
        self.assertEqual(metrics.default_height, 236.0)
        self.assertEqual(metrics.min_width, 220.0)
        self.assertEqual(metrics.min_height, 176.0)
        self.assertEqual(metrics.title_top, 12.0)
        self.assertEqual(metrics.title_height, 24.0)
        self.assertEqual(metrics.body_top, 44.0)
        self.assertEqual(metrics.body_bottom_margin, 12.0)
        self.assertTrue(metrics.use_host_chrome)
        self.assertFalse(metrics.show_header_background)
        self.assertFalse(metrics.show_accent_bar)


class PassiveImageNodeSurfaceQmlTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        script = textwrap.dedent(
            """
            import tempfile
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl
            from PyQt6.QtGui import QColor, QImage
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.ui.media_preview_provider import (
                LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
                LocalMediaPreviewImageProvider,
            )
            from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
            from ea_node_editor.ui_qml.theme_bridge import ThemeBridge

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())
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

            def wait_for_preview(surface, attempts=40):
                for _index in range(attempts):
                    app.processEvents()
                    if str(surface.property("previewState")) in {"ready", "error"}:
                        return

            def image_panel_payload(properties):
                return {
                    "node_id": "node_image_panel_surface_test",
                    "type_id": "passive.media.image_panel",
                    "title": "Image Panel",
                    "x": 100.0,
                    "y": 110.0,
                    "width": 296.0,
                    "height": 236.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": "media",
                    "surface_variant": "image_panel",
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [],
                    "inline_properties": [],
                    "properties": properties,
                }

            def make_png(path, color_name):
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor(color_name))
                assert image.save(str(path))
            """
        ) + "\n" + textwrap.dedent(body)
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
            self.fail(f"{label} probe failed with exit code {result.returncode}\n{details}")

    def test_graph_node_host_loads_media_surface_family(self) -> None:
        self._run_qml_probe(
            "media-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": image_panel_payload(
                        {
                            "source_path": "",
                            "caption": "",
                            "fit_mode": "contain",
                        }
                    ),
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeMediaSurface")
            assert loader is not None
            assert surface is not None
            assert loader.property("loadedSurfaceKey") == "media"
            assert float(loader.property("contentHeight")) > 0.0
            assert surface.property("previewState") == "placeholder"
            """,
        )

    def test_empty_path_uses_placeholder_state(self) -> None:
        self._run_qml_probe(
            "media-placeholder",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": image_panel_payload(
                        {
                            "source_path": "   ",
                            "caption": "",
                            "fit_mode": "contain",
                        }
                    ),
                },
            )
            surface = host.findChild(QObject, "graphNodeMediaSurface")
            assert surface is not None
            assert surface.property("previewState") == "placeholder"
            assert surface.property("resolvedSourceUrl") == ""
            assert not bool(surface.property("captionVisible"))
            """,
        )

    def test_valid_local_png_enters_ready_state_and_maps_fit_modes(self) -> None:
        self._run_qml_probe(
            "media-ready",
            """
            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "preview image.png"
                make_png(image_path, "#2c85bf")

                contain_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(image_path),
                                "caption": "Preview caption",
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                cover_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": QUrl.fromLocalFile(str(image_path)).toString(),
                                "caption": "",
                                "fit_mode": "cover",
                            }
                        ),
                    },
                )
                original_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(image_path),
                                "caption": "",
                                "fit_mode": "original",
                            }
                        ),
                    },
                )

                contain_surface = contain_host.findChild(QObject, "graphNodeMediaSurface")
                cover_surface = cover_host.findChild(QObject, "graphNodeMediaSurface")
                original_surface = original_host.findChild(QObject, "graphNodeMediaSurface")
                wait_for_preview(contain_surface)
                wait_for_preview(cover_surface)
                wait_for_preview(original_surface)

                assert contain_surface.property("previewState") == "ready"
                assert bool(contain_surface.property("captionVisible"))
                assert str(contain_surface.property("resolvedSourceUrl")).startswith("file:///")
                assert contain_surface.property("appliedFitMode") == "contain"
                assert cover_surface.property("previewState") == "ready"
                assert cover_surface.property("appliedFitMode") == "cover"
                assert original_surface.property("previewState") == "ready"
                assert original_surface.property("appliedFitMode") == "original"
                assert bool(original_surface.property("originalModeActive"))
            """,
        )

    def test_missing_invalid_and_non_local_sources_fail_cleanly(self) -> None:
        self._run_qml_probe(
            "media-error",
            """
            with tempfile.TemporaryDirectory() as temp_dir:
                invalid_image_path = Path(temp_dir) / "invalid-image.png"
                invalid_image_path.write_text("not a real image", encoding="utf-8")
                missing_image_path = Path(temp_dir) / "missing-image.png"

                missing_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(missing_image_path),
                                "caption": "",
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                invalid_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(invalid_image_path),
                                "caption": "",
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                remote_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": "https://example.com/test.png",
                                "caption": "",
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                relative_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": "images/test.png",
                                "caption": "",
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )

                missing_surface = missing_host.findChild(QObject, "graphNodeMediaSurface")
                invalid_surface = invalid_host.findChild(QObject, "graphNodeMediaSurface")
                remote_surface = remote_host.findChild(QObject, "graphNodeMediaSurface")
                relative_surface = relative_host.findChild(QObject, "graphNodeMediaSurface")
                wait_for_preview(missing_surface)
                wait_for_preview(invalid_surface)

                assert missing_surface.property("previewState") == "error"
                assert invalid_surface.property("previewState") == "error"
                assert remote_surface.property("previewState") == "error"
                assert relative_surface.property("previewState") == "error"
                assert remote_surface.property("resolvedSourceUrl") == ""
                assert relative_surface.property("resolvedSourceUrl") == ""
            """,
        )


class LocalMediaPreviewProviderTests(unittest.TestCase):
    def test_provider_enables_auto_transform_for_local_images(self) -> None:
        calls: list[tuple[str, object]] = []

        class FakeReader:
            def __init__(self, filename: str) -> None:
                calls.append(("init", filename))

            def setAutoTransform(self, value: bool) -> None:
                calls.append(("setAutoTransform", value))

            def setDecideFormatFromContent(self, value: bool) -> None:
                calls.append(("setDecideFormatFromContent", value))

            def read(self):
                calls.append(("read", None))
                from PyQt6.QtGui import QColor, QImage

                image = QImage(8, 6, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                return image

        provider = LocalMediaPreviewImageProvider()
        with patch("ea_node_editor.ui.media_preview_provider.QImageReader", FakeReader):
            with patch("ea_node_editor.ui.media_preview_provider.Path.exists", return_value=True):
                with patch("ea_node_editor.ui.media_preview_provider.Path.is_file", return_value=True):
                    image, size = provider.requestImage(
                        "preview?source=file%3A%2F%2F%2FC%3A%2Ftmp%2Forientation-test.jpg",
                        QSize(),
                    )

        self.assertFalse(image.isNull())
        self.assertEqual(size.width(), 8)
        self.assertEqual(size.height(), 6)
        self.assertIn(("setAutoTransform", True), calls)
        self.assertIn(("setDecideFormatFromContent", True), calls)
        self.assertIn(("read", None), calls)


if __name__ == "__main__":
    unittest.main()
