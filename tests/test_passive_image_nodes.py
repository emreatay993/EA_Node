from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor, QImage
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.media_preview_provider import LocalMediaPreviewImageProvider
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics
from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    run_qml_probe,
)


class PassiveImageNodeCatalogTests(unittest.TestCase):
    def test_generated_js_surface_metric_contract_matches_authoritative_json(self) -> None:
        graph_dir = Path(__file__).resolve().parents[1] / "ea_node_editor" / "ui_qml" / "components" / "graph"
        json_payload = json.loads((graph_dir / "GraphNodeSurfaceMetricContract.json").read_text(encoding="utf-8"))
        js_text = (graph_dir / "GraphNodeSurfaceMetricContract.js").read_text(encoding="utf-8")
        match = re.search(
            r"var SURFACE_METRIC_CONTRACT = (\{.*\});\s*function contract",
            js_text,
            re.DOTALL,
        )

        self.assertIsNotNone(match)
        js_payload = json.loads(match.group(1))
        self.assertEqual(js_payload, json_payload)

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
        self.assertEqual(spec.render_quality.weight_class, "heavy")
        self.assertEqual(spec.render_quality.max_performance_strategy, "proxy_surface")
        self.assertEqual(spec.render_quality.supported_quality_tiers, ("full", "proxy"))
        self.assertEqual(
            tuple(prop.key for prop in spec.properties),
            ("source_path", "caption", "fit_mode", "crop_x", "crop_y", "crop_w", "crop_h"),
        )

        source_path = next(prop for prop in spec.properties if prop.key == "source_path")
        caption = next(prop for prop in spec.properties if prop.key == "caption")
        fit_mode = next(prop for prop in spec.properties if prop.key == "fit_mode")
        crop_x = next(prop for prop in spec.properties if prop.key == "crop_x")
        crop_y = next(prop for prop in spec.properties if prop.key == "crop_y")
        crop_w = next(prop for prop in spec.properties if prop.key == "crop_w")
        crop_h = next(prop for prop in spec.properties if prop.key == "crop_h")

        self.assertEqual(source_path.type, "path")
        self.assertEqual(source_path.inline_editor, "path")
        self.assertEqual(caption.type, "str")
        self.assertEqual(caption.inline_editor, "textarea")
        self.assertEqual(caption.inspector_editor, "textarea")
        self.assertEqual(fit_mode.type, "enum")
        self.assertEqual(fit_mode.default, "contain")
        self.assertEqual(fit_mode.enum_values, ("contain", "cover", "original"))
        self.assertEqual(crop_x.type, "float")
        self.assertEqual(crop_x.default, 0.0)
        self.assertFalse(crop_x.inspector_visible)
        self.assertEqual(crop_y.default, 0.0)
        self.assertFalse(crop_y.inspector_visible)
        self.assertEqual(crop_w.default, 1.0)
        self.assertFalse(crop_w.inspector_visible)
        self.assertEqual(crop_h.default, 1.0)
        self.assertFalse(crop_h.inspector_visible)

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

    def test_media_surface_metrics_auto_size_default_height_from_local_image_ratio(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.image_panel")
        with tempfile.TemporaryDirectory() as temp_dir:
            portrait_path = Path(temp_dir) / "portrait.png"
            panorama_path = Path(temp_dir) / "panorama.png"

            portrait = QImage(18, 36, QImage.Format.Format_ARGB32)
            portrait.fill(QColor("#2c85bf"))
            self.assertTrue(portrait.save(str(portrait_path)))

            panorama = QImage(72, 18, QImage.Format.Format_ARGB32)
            panorama.fill(QColor("#173247"))
            self.assertTrue(panorama.save(str(panorama_path)))

            portrait_node = NodeInstance(
                node_id="node_image_panel_portrait",
                type_id=spec.type_id,
                title="Image Panel",
                x=20.0,
                y=30.0,
                properties={"source_path": str(portrait_path), "caption": "", "fit_mode": "contain"},
            )
            panorama_node = NodeInstance(
                node_id="node_image_panel_panorama",
                type_id=spec.type_id,
                title="Image Panel",
                x=20.0,
                y=30.0,
                properties={"source_path": str(panorama_path), "caption": "", "fit_mode": "contain"},
            )

            portrait_metrics = node_surface_metrics(portrait_node, spec, {portrait_node.node_id: portrait_node})
            panorama_metrics = node_surface_metrics(panorama_node, spec, {panorama_node.node_id: panorama_node})

            self.assertAlmostEqual(portrait_metrics.default_height, 592.0, places=6)
            self.assertAlmostEqual(panorama_metrics.default_height, 176.0, places=6)

    def test_media_surface_metrics_reserves_caption_space_in_derived_height(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.image_panel")
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "captioned-image.png"
            image = QImage(18, 36, QImage.Format.Format_ARGB32)
            image.fill(QColor("#2c85bf"))
            self.assertTrue(image.save(str(image_path)))

            without_caption = NodeInstance(
                node_id="node_image_panel_without_caption",
                type_id=spec.type_id,
                title="Image Panel",
                x=20.0,
                y=30.0,
                properties={"source_path": str(image_path), "caption": "", "fit_mode": "contain"},
            )
            with_caption = NodeInstance(
                node_id="node_image_panel_with_caption",
                type_id=spec.type_id,
                title="Image Panel",
                x=20.0,
                y=30.0,
                properties={
                    "source_path": str(image_path),
                    "caption": "This caption should reserve space under the preview.",
                    "fit_mode": "contain",
                },
            )

            without_caption_metrics = node_surface_metrics(without_caption, spec, {without_caption.node_id: without_caption})
            with_caption_metrics = node_surface_metrics(with_caption, spec, {with_caption.node_id: with_caption})

            self.assertGreater(with_caption_metrics.default_height, without_caption_metrics.default_height)

    def test_scene_bridge_recomputes_payload_height_without_persisting_custom_size(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "portrait-image.png"
            image = QImage(18, 36, QImage.Format.Format_ARGB32)
            image.fill(QColor("#2c85bf"))
            self.assertTrue(image.save(str(image_path)))

            node_id = scene.add_node_from_type("passive.media.image_panel", 40.0, 60.0)
            initial_payload = next(item for item in scene.nodes_model if item["node_id"] == node_id)
            self.assertEqual(initial_payload["height"], 236.0)

            scene.set_node_property(node_id, "source_path", str(image_path))

            updated_payload = next(item for item in scene.nodes_model if item["node_id"] == node_id)
            node = model.project.workspaces[workspace_id].nodes[node_id]
            self.assertAlmostEqual(updated_payload["width"], 296.0, places=6)
            self.assertAlmostEqual(updated_payload["height"], 592.0, places=6)
            self.assertIsNone(node.custom_width)
            self.assertIsNone(node.custom_height)

    def test_scene_bridge_batches_crop_property_updates_into_node_state(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        node_id = scene.add_node_from_type("passive.media.image_panel", 40.0, 60.0)

        changed = scene.set_node_properties(
            node_id,
            {
                "crop_x": 0.125,
                "crop_y": 0.2,
                "crop_w": 0.5,
                "crop_h": 0.6,
            },
        )

        self.assertTrue(changed)
        node = model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(
            {key: node.properties[key] for key in ("crop_x", "crop_y", "crop_w", "crop_h")},
            {
                "crop_x": 0.125,
                "crop_y": 0.2,
                "crop_w": 0.5,
                "crop_h": 0.6,
            },
        )


class PassiveImageNodeSurfaceQmlTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
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

            def variant_value(value):
                return value.toVariant() if hasattr(value, "toVariant") else value

            def variant_list(value):
                normalized = variant_value(value)
                if normalized is None:
                    return []
                return list(normalized)
            """,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

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
                assert bool(contain_surface.property("cropToolAvailable"))
                assert cover_surface.property("previewState") == "ready"
                assert cover_surface.property("appliedFitMode") == "cover"
                assert original_surface.property("previewState") == "ready"
                assert original_surface.property("appliedFitMode") == "original"
                assert bool(original_surface.property("originalModeActive"))
            """,
        )

    def test_image_panel_proxy_preview_activates_for_proxy_quality_tier(self) -> None:
        self._run_qml_probe(
            "media-proxy-image",
            """
            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "proxy-image.png"
                make_png(image_path, "#2c85bf")

                payload = image_panel_payload(
                    {
                        "source_path": str(image_path),
                        "caption": "Proxy preview",
                        "fit_mode": "contain",
                    }
                )
                payload["render_quality"] = {
                    "weight_class": "heavy",
                    "max_performance_strategy": "proxy_surface",
                    "supported_quality_tiers": ["full", "proxy"],
                }

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": payload,
                        "snapshotReuseActive": True,
                        "shadowSimplificationActive": True,
                    },
                )
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                proxy_preview = host.findChild(QObject, "graphNodeMediaProxyPreview")
                applied_viewport = host.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                preview_hint = host.findChild(QObject, "graphNodeMediaPreviewHint")
                assert loader is not None
                assert surface is not None
                assert proxy_preview is not None
                assert applied_viewport is not None
                assert preview_hint is not None

                wait_for_preview(surface)

                assert surface.property("previewState") == "ready"
                assert host.property("resolvedQualityTier") == "proxy"
                assert bool(host.property("proxySurfaceRequested"))
                assert bool(surface.property("proxySurfaceActive"))
                assert bool(loader.property("proxySurfaceActive"))
                assert bool(proxy_preview.property("visible"))
                assert not bool(applied_viewport.property("visible"))
                assert not bool(preview_hint.property("visible"))
                assert not bool(surface.property("cropToolAvailable"))
            """,
        )

    def test_crop_rect_applies_render_geometry_for_ready_images(self) -> None:
        self._run_qml_probe(
            "media-crop-render",
            """
            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "cropped-preview.png"
                image = QImage(40, 20, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(image_path),
                                "caption": "",
                                "fit_mode": "contain",
                                "crop_x": 0.25,
                                "crop_y": 0.1,
                                "crop_w": 0.5,
                                "crop_h": 0.4,
                            }
                        ),
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                applied_viewport = host.findChild(QObject, "graphNodeMediaAppliedImageViewport")
                applied_image = host.findChild(QObject, "graphNodeMediaAppliedImage")
                wait_for_preview(surface)

                assert surface.property("previewState") == "ready"
                assert bool(surface.property("hasEffectiveCrop"))
                assert applied_viewport is not None
                assert applied_image is not None
                assert float(surface.property("appliedClipX")) == 10.0
                assert float(surface.property("appliedClipY")) == 2.0
                assert float(surface.property("appliedClipWidth")) == 20.0
                assert float(surface.property("appliedClipHeight")) == 8.0
                assert round(float(applied_viewport.property("x")), 3) == 0.0
                assert round(float(applied_viewport.property("y")), 3) == 36.4
                assert round(float(applied_viewport.property("width")), 3) == 268.0
                assert round(float(applied_viewport.property("height")), 3) == 107.2
                assert round(float(applied_image.property("x")), 3) == -134.0
                assert round(float(applied_image.property("y")), 3) == -26.8
                assert round(float(applied_image.property("width")), 3) == 536.0
                assert round(float(applied_image.property("height")), 3) == 268.0
            """,
        )

    def test_crop_controls_stay_unavailable_for_placeholder_error_and_pdf_states(self) -> None:
        self._run_qml_probe(
            "media-crop-availability",
            """
            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "image.png"
                missing_path = Path(temp_dir) / "missing.png"
                pdf_path = Path(temp_dir) / "sample.pdf"
                make_png(image_path, "#2c85bf")
                pdf_path.write_bytes(b"%PDF-1.4\\n%%EOF\\n")

                placeholder_host = create_component(
                    graph_node_host_qml_path,
                    {"nodeData": image_panel_payload({"source_path": "", "caption": "", "fit_mode": "contain"})},
                )
                error_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {"source_path": str(missing_path), "caption": "", "fit_mode": "contain"}
                        )
                    },
                )
                pdf_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": {
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
                            "visual_style": {},
                            "can_enter_scope": False,
                            "ports": [],
                            "inline_properties": [],
                            "properties": {
                                "source_path": str(pdf_path),
                                "page_number": 1,
                                "caption": "",
                            },
                        }
                    },
                )

                placeholder_surface = placeholder_host.findChild(QObject, "graphNodeMediaSurface")
                error_surface = error_host.findChild(QObject, "graphNodeMediaSurface")
                pdf_surface = pdf_host.findChild(QObject, "graphNodeMediaSurface")
                wait_for_preview(error_surface)
                wait_for_preview(pdf_surface)

                assert not bool(placeholder_surface.property("cropToolAvailable"))
                assert not bool(error_surface.property("cropToolAvailable"))
                assert not bool(pdf_surface.property("cropToolAvailable"))
                assert pdf_surface.findChild(QObject, "graphNodeMediaCropButton") is not None
            """,
        )

    def test_crop_mode_reports_host_interaction_lock(self) -> None:
        self._run_qml_probe(
            "media-crop-lock",
            """
            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "locking-preview.png"
                make_png(image_path, "#2c85bf")

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(image_path),
                                "caption": "",
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                wait_for_preview(surface)
                surface.setProperty("cropModeActive", True)
                app.processEvents()

                assert bool(surface.property("blocksHostInteraction"))
                assert len(variant_list(surface.property("embeddedInteractiveRects"))) == 10
            """,
        )

    def test_crop_controls_publish_direct_embedded_interactive_rects(self) -> None:
        self._run_qml_probe(
            "media-crop-direct-rects",
            """
            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "direct-rects.png"
                make_png(image_path, "#2c85bf")

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(image_path),
                                "caption": "",
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                crop_button = host.findChild(QObject, "graphNodeMediaCropButton")
                wait_for_preview(surface)
                assert surface is not None
                assert crop_button is not None

                window = attach_host_to_window(host)

                hover_host_local_point(window, host, 80.0, 44.0)

                assert bool(crop_button.property("visible"))
                assert len(variant_list(surface.property("embeddedInteractiveRects"))) == 1

                surface.setProperty("cropModeActive", True)
                app.processEvents()

                assert len(variant_list(surface.property("embeddedInteractiveRects"))) == 10

                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
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
