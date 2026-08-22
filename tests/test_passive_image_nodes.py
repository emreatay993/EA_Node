from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QObject, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QImage
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.media_preview_provider import (
    LocalMediaPreviewImageProvider,
    describe_local_image,
    set_media_preview_project_context_provider,
)
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics
from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    run_qml_probe,
)


class _GraphicsPreferenceSource(QObject):
    graphics_preferences_changed = pyqtSignal()

    def __init__(self, appearance: dict[str, bool], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._appearance = dict(appearance)

    @property
    def graphics_image_node_default_appearance(self) -> dict[str, bool]:
        return dict(self._appearance)

    @property
    def graphics_show_port_labels(self) -> bool:
        return True


class _SceneHost(QObject):
    def __init__(self, appearance: dict[str, bool]) -> None:
        super().__init__()
        self.graph_canvas_presenter = _GraphicsPreferenceSource(appearance, self)


class PassiveImageNodeCatalogTests(unittest.TestCase):
    _EXPECTED_CARDINAL_PORTS = (
        ("top", "neutral", True, "top"),
        ("right", "neutral", True, "right"),
        ("bottom", "neutral", True, "bottom"),
        ("left", "neutral", True, "left"),
    )

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
        self.assertEqual(
            tuple((port.key, port.direction, port.allow_multiple_connections, port.side) for port in spec.ports),
            self._EXPECTED_CARDINAL_PORTS,
        )
        self.assertEqual(spec.render_quality.supported_quality_tiers, ("full", "proxy"))
        self.assertEqual(
            tuple(prop.key for prop in spec.properties),
            (
                "source_path",
                "fit_mode",
                "animation_playback_mode",
                "lock_aspect_ratio",
                "show_title",
                "show_frame",
                "crop_x",
                "crop_y",
                "crop_w",
                "crop_h",
                "rotation_degrees",
                "mirror_horizontal",
                "mirror_vertical",
            ),
        )

        source_path = next(prop for prop in spec.properties if prop.key == "source_path")
        fit_mode = next(prop for prop in spec.properties if prop.key == "fit_mode")
        lock_aspect_ratio = next(prop for prop in spec.properties if prop.key == "lock_aspect_ratio")
        animation_playback_mode = next(prop for prop in spec.properties if prop.key == "animation_playback_mode")
        show_title = next(prop for prop in spec.properties if prop.key == "show_title")
        show_frame = next(prop for prop in spec.properties if prop.key == "show_frame")
        crop_x = next(prop for prop in spec.properties if prop.key == "crop_x")
        crop_y = next(prop for prop in spec.properties if prop.key == "crop_y")
        crop_w = next(prop for prop in spec.properties if prop.key == "crop_w")
        crop_h = next(prop for prop in spec.properties if prop.key == "crop_h")
        rotation_degrees = next(prop for prop in spec.properties if prop.key == "rotation_degrees")
        mirror_horizontal = next(prop for prop in spec.properties if prop.key == "mirror_horizontal")
        mirror_vertical = next(prop for prop in spec.properties if prop.key == "mirror_vertical")

        self.assertEqual(source_path.type, "path")
        self.assertEqual(source_path.inline_editor, "path")
        self.assertEqual(fit_mode.type, "enum")
        self.assertEqual(fit_mode.default, "contain")
        self.assertEqual(fit_mode.enum_values, ("contain", "cover", "original"))
        self.assertEqual(lock_aspect_ratio.type, "bool")
        self.assertFalse(lock_aspect_ratio.default)
        self.assertFalse(lock_aspect_ratio.inspector_visible)
        self.assertEqual(animation_playback_mode.type, "enum")
        self.assertEqual(animation_playback_mode.default, "auto")
        self.assertEqual(animation_playback_mode.enum_values, ("auto", "play", "pause"))
        self.assertFalse(animation_playback_mode.inspector_visible)
        self.assertEqual(show_title.type, "bool")
        self.assertTrue(show_title.default)
        self.assertFalse(show_title.inspector_visible)
        self.assertEqual(show_frame.type, "bool")
        self.assertTrue(show_frame.default)
        self.assertFalse(show_frame.inspector_visible)
        self.assertEqual(crop_x.type, "float")
        self.assertEqual(crop_x.default, 0.0)
        self.assertFalse(crop_x.inspector_visible)
        self.assertEqual(crop_y.default, 0.0)
        self.assertFalse(crop_y.inspector_visible)
        self.assertEqual(crop_w.default, 1.0)
        self.assertFalse(crop_w.inspector_visible)
        self.assertEqual(crop_h.default, 1.0)
        self.assertFalse(crop_h.inspector_visible)
        self.assertEqual(rotation_degrees.type, "int")
        self.assertEqual(rotation_degrees.default, 0)
        self.assertFalse(rotation_degrees.inspector_visible)
        self.assertEqual(mirror_horizontal.type, "bool")
        self.assertFalse(mirror_horizontal.default)
        self.assertFalse(mirror_horizontal.inspector_visible)
        self.assertEqual(mirror_vertical.type, "bool")
        self.assertFalse(mirror_vertical.default)
        self.assertFalse(mirror_vertical.inspector_visible)

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
            self._EXPECTED_CARDINAL_PORTS,
        )
        self.assertEqual(spec.render_quality.supported_quality_tiers, ("full", "proxy"))
        self.assertEqual(
            tuple(prop.key for prop in spec.properties),
            (
                "source_path",
                "page_number",
                "show_title",
                "show_frame",
            ),
        )

        properties = {prop.key: prop for prop in spec.properties}
        self.assertEqual(properties["source_path"].type, "path")
        self.assertEqual(properties["source_path"].inline_editor, "path")
        self.assertEqual(properties["page_number"].default, 1)
        self.assertEqual(properties["show_title"].type, "bool")
        self.assertTrue(properties["show_title"].default)
        self.assertFalse(properties["show_title"].inspector_visible)
        self.assertEqual(properties["show_frame"].type, "bool")
        self.assertTrue(properties["show_frame"].default)
        self.assertFalse(properties["show_frame"].inspector_visible)

    def test_default_registry_registers_locked_video_panel_spec(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.video_panel")

        self.assertEqual(spec.display_name, "Video Panel")
        self.assertEqual(spec.category, "Media")
        self.assertEqual(spec.runtime_behavior, "passive")
        self.assertEqual(spec.surface_family, "media")
        self.assertEqual(spec.surface_variant, "video_panel")
        self.assertFalse(spec.collapsible)
        self.assertEqual(
            tuple((port.key, port.direction, port.allow_multiple_connections, port.side) for port in spec.ports),
            self._EXPECTED_CARDINAL_PORTS,
        )
        self.assertEqual(spec.render_quality.supported_quality_tiers, ("full", "proxy"))
        self.assertEqual(
            tuple(prop.key for prop in spec.properties),
            (
                "source_path",
                "fit_mode",
                "show_title",
                "show_frame",
                "auto_play",
                "loop",
                "muted",
                "volume",
                "playback_rate",
                "position_ms",
                "timeline_bookmarks",
                "clip_enabled",
                "clip_start_ms",
                "clip_end_ms",
                "unfocused_behavior",
            ),
        )

        properties = {prop.key: prop for prop in spec.properties}
        self.assertEqual(properties["source_path"].type, "path")
        self.assertEqual(properties["source_path"].inline_editor, "path")
        self.assertEqual(properties["fit_mode"].enum_values, ("contain", "cover"))
        self.assertEqual(properties["show_title"].type, "bool")
        self.assertTrue(properties["show_title"].default)
        self.assertFalse(properties["show_title"].inspector_visible)
        self.assertEqual(properties["show_frame"].type, "bool")
        self.assertTrue(properties["show_frame"].default)
        self.assertFalse(properties["show_frame"].inspector_visible)
        self.assertFalse(properties["auto_play"].default)
        self.assertFalse(properties["loop"].default)
        self.assertFalse(properties["muted"].default)
        self.assertEqual(properties["volume"].default, 1.0)
        self.assertEqual(properties["playback_rate"].default, 1.0)
        self.assertEqual(properties["position_ms"].default, 0)
        self.assertFalse(properties["position_ms"].inspector_visible)
        self.assertEqual(properties["timeline_bookmarks"].type, "json")
        self.assertEqual(properties["timeline_bookmarks"].default, [])
        self.assertTrue(properties["timeline_bookmarks"].inspector_visible)
        self.assertEqual(properties["clip_enabled"].type, "bool")
        self.assertFalse(properties["clip_enabled"].default)
        self.assertTrue(properties["clip_enabled"].inspector_visible)
        self.assertEqual(properties["clip_start_ms"].type, "int")
        self.assertEqual(properties["clip_start_ms"].default, 0)
        self.assertTrue(properties["clip_start_ms"].inspector_visible)
        self.assertEqual(properties["clip_end_ms"].type, "int")
        self.assertEqual(properties["clip_end_ms"].default, 0)
        self.assertTrue(properties["clip_end_ms"].inspector_visible)
        self.assertEqual(properties["unfocused_behavior"].default, "pause_keep_loaded")
        self.assertEqual(properties["unfocused_behavior"].enum_values, ("pause_keep_loaded", "keep_playing"))
        self.assertFalse(properties["unfocused_behavior"].inspector_visible)

    def test_default_registry_registers_locked_mail_panel_spec(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.mail_panel")

        self.assertEqual(spec.display_name, "Mail Panel")
        self.assertEqual(spec.category, "Media")
        self.assertEqual(spec.runtime_behavior, "passive")
        self.assertEqual(spec.surface_family, "media")
        self.assertEqual(spec.surface_variant, "mail_panel")
        self.assertFalse(spec.collapsible)
        self.assertEqual(
            tuple((port.key, port.direction, port.allow_multiple_connections, port.side) for port in spec.ports),
            self._EXPECTED_CARDINAL_PORTS,
        )
        self.assertEqual(spec.render_quality.supported_quality_tiers, ("full", "proxy"))
        self.assertEqual(tuple(prop.key for prop in spec.properties), ("source_path", "show_title", "show_frame"))

        properties = {prop.key: prop for prop in spec.properties}
        self.assertEqual(properties["source_path"].type, "path")
        self.assertEqual(properties["source_path"].inline_editor, "path")
        self.assertIn("*.eml", str(properties["source_path"].file_filter))
        self.assertIn("*.msg", str(properties["source_path"].file_filter))
        self.assertIn("*.oft", str(properties["source_path"].file_filter))
        self.assertEqual(properties["show_title"].type, "bool")
        self.assertTrue(properties["show_title"].default)
        self.assertFalse(properties["show_title"].inspector_visible)
        self.assertEqual(properties["show_frame"].type, "bool")
        self.assertTrue(properties["show_frame"].default)
        self.assertFalse(properties["show_frame"].inspector_visible)

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
        self.assertNotIn("show_header_background", metrics.to_payload())
        self.assertNotIn("show_accent_bar", metrics.to_payload())

    def test_media_surface_metrics_use_fixed_video_defaults(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.video_panel")
        node = NodeInstance(
            node_id="node_video_panel",
            type_id=spec.type_id,
            title="Video Panel",
            x=20.0,
            y=30.0,
            properties={"source_path": r"C:\fixtures\clip.mp4", "fit_mode": "contain"},
        )

        metrics = node_surface_metrics(node, spec, {node.node_id: node})

        self.assertEqual(metrics.default_width, 340.0)
        self.assertEqual(metrics.default_height, 288.0)
        self.assertEqual(metrics.min_width, 260.0)
        self.assertEqual(metrics.min_height, 216.0)
        self.assertEqual(metrics.body_top, 44.0)
        self.assertEqual(metrics.body_bottom_margin, 12.0)
        self.assertTrue(metrics.use_host_chrome)
        self.assertNotIn("show_header_background", metrics.to_payload())
        self.assertNotIn("show_accent_bar", metrics.to_payload())

    def test_media_surface_metrics_use_fixed_mail_defaults(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.mail_panel")
        node = NodeInstance(
            node_id="node_mail_panel",
            type_id=spec.type_id,
            title="Mail Panel",
            x=20.0,
            y=30.0,
            properties={"source_path": r"C:\fixtures\message.eml"},
        )

        metrics = node_surface_metrics(node, spec, {node.node_id: node})

        self.assertEqual(metrics.default_width, 360.0)
        self.assertEqual(metrics.default_height, 300.0)
        self.assertEqual(metrics.min_width, 260.0)
        self.assertEqual(metrics.min_height, 210.0)
        self.assertEqual(metrics.body_top, 44.0)
        self.assertEqual(metrics.body_bottom_margin, 12.0)
        self.assertTrue(metrics.use_host_chrome)
        self.assertNotIn("show_header_background", metrics.to_payload())
        self.assertNotIn("show_accent_bar", metrics.to_payload())

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
                properties={"source_path": str(portrait_path), "fit_mode": "contain"},
            )
            panorama_node = NodeInstance(
                node_id="node_image_panel_panorama",
                type_id=spec.type_id,
                title="Image Panel",
                x=20.0,
                y=30.0,
                properties={"source_path": str(panorama_path), "fit_mode": "contain"},
            )

            portrait_metrics = node_surface_metrics(portrait_node, spec, {portrait_node.node_id: portrait_node})
            panorama_metrics = node_surface_metrics(panorama_node, spec, {panorama_node.node_id: panorama_node})

            self.assertAlmostEqual(portrait_metrics.default_height, 592.0, places=6)
            self.assertAlmostEqual(panorama_metrics.default_height, 176.0, places=6)

    def test_media_surface_metrics_swap_default_image_panel_size_for_quarter_turns(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.media.image_panel")
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "portrait.png"
            image = QImage(18, 36, QImage.Format.Format_ARGB32)
            image.fill(QColor("#2c85bf"))
            self.assertTrue(image.save(str(image_path)))

            rotated_node = NodeInstance(
                node_id="node_image_panel_rotated",
                type_id=spec.type_id,
                title="Image Panel",
                x=20.0,
                y=30.0,
                properties={
                    "source_path": str(image_path),
                    "fit_mode": "contain",
                    "rotation_degrees": 90,
                },
            )
            half_turn_node = NodeInstance(
                node_id="node_image_panel_half_turn",
                type_id=spec.type_id,
                title="Image Panel",
                x=20.0,
                y=30.0,
                properties={
                    "source_path": str(image_path),
                    "fit_mode": "contain",
                    "rotation_degrees": 180,
                },
            )

            rotated_metrics = node_surface_metrics(rotated_node, spec, {rotated_node.node_id: rotated_node})
            half_turn_metrics = node_surface_metrics(half_turn_node, spec, {half_turn_node.node_id: half_turn_node})

            self.assertAlmostEqual(rotated_metrics.default_width, 564.0, places=6)
            self.assertAlmostEqual(rotated_metrics.default_height, 324.0, places=6)
            self.assertAlmostEqual(half_turn_metrics.default_width, 296.0, places=6)
            self.assertAlmostEqual(half_turn_metrics.default_height, 592.0, places=6)

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

    def test_scene_bridge_recomputes_image_panel_default_size_after_rotation(self) -> None:
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
            scene.set_node_property(node_id, "source_path", str(image_path))
            scene.set_node_property(node_id, "rotation_degrees", 90)

            updated_payload = next(item for item in scene.nodes_model if item["node_id"] == node_id)
            node = model.project.workspaces[workspace_id].nodes[node_id]
            self.assertAlmostEqual(updated_payload["width"], 564.0, places=6)
            self.assertAlmostEqual(updated_payload["height"], 324.0, places=6)
            self.assertIsNone(node.custom_width)
            self.assertIsNone(node.custom_height)

    def test_scene_bridge_create_node_from_type_can_seed_image_panel_custom_size(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        node_id = scene.create_node_from_type(
            type_id="passive.media.image_panel",
            x=40.0,
            y=60.0,
            parent_node_id=None,
            select_node=True,
            custom_width=512.0,
            custom_height=384.0,
        )

        node = model.project.workspaces[workspace_id].nodes[node_id]
        payload = next(item for item in scene.nodes_model if item["node_id"] == node_id)
        self.assertAlmostEqual(float(node.custom_width or 0.0), 512.0, places=6)
        self.assertAlmostEqual(float(node.custom_height or 0.0), 384.0, places=6)
        self.assertAlmostEqual(float(payload["width"]), 512.0, places=6)
        self.assertAlmostEqual(float(payload["height"]), 384.0, places=6)

    def test_scene_bridge_create_node_from_type_can_seed_initial_title(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        node_id = scene.create_node_from_type(
            type_id="core.python_script",
            x=40.0,
            y=60.0,
            parent_node_id=None,
            select_node=True,
            initial_title="Packet Script",
        )

        node = model.project.workspaces[workspace_id].nodes[node_id]
        payload = next(item for item in scene.nodes_model if item["node_id"] == node_id)
        self.assertEqual(node.title, "Packet Script")
        self.assertEqual(payload["title"], "Packet Script")

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

    def test_scene_bridge_applies_image_node_graphics_defaults_on_create(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        host = _SceneHost({"show_title": False, "show_frame": False})
        scene = GraphSceneBridge(parent=host)
        scene.set_workspace(model, registry, workspace_id)

        node_id = scene.add_node_from_type("passive.media.image_panel", 40.0, 60.0)

        node = model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(
            {key: node.properties[key] for key in ("show_title", "show_frame")},
            {"show_title": False, "show_frame": False},
        )


class PassiveImageNodeSurfaceQmlTests(unittest.TestCase):
    def test_video_surface_applies_timestamp_after_zero_initial_position(self) -> None:
        source = (
            Path.cwd()
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "passive"
            / "GraphVideoPanelSurface.qml"
        ).read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", " ", source)

        self.assertIn(
            "if (!initialPositionApplied) { _applyInitialPosition(); return; }",
            normalized,
        )
        self.assertIn(
            "if (storedPositionMs <= 0) { _seekTo(_initialThumbnailPositionMs()); _primeThumbnailFrame(); initialPositionApplied = true; _syncSeekSlider(); return; }",
            normalized,
        )

    def test_video_surfaces_seek_initial_thumbnail_frame_for_zero_position(self) -> None:
        inline_source = (
            Path.cwd()
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "passive"
            / "GraphVideoPanelSurface.qml"
        ).read_text(encoding="utf-8")
        fullscreen_source = (
            Path.cwd()
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "passive"
            / "GraphVideoPanelFullscreenSurface.qml"
        ).read_text(encoding="utf-8")
        inline_normalized = re.sub(r"\s+", " ", inline_source)
        fullscreen_normalized = re.sub(r"\s+", " ", fullscreen_source)

        self.assertIn(
            "if (storedPositionMs <= 0) { _seekTo(_initialThumbnailPositionMs()); _primeThumbnailFrame(); initialPositionApplied = true; _syncSeekSlider(); return; }",
            inline_normalized,
        )
        self.assertIn(
            "_seekTo(storedPositionMs); _primeThumbnailFrame(); initialPositionApplied = true;",
            inline_normalized,
        )
        self.assertIn(
            "function _initialThumbnailPositionMs() { if (clipRangeActive && clipStartMs > 0) return clipStartMs; return 1; }",
            inline_normalized,
        )
        self.assertIn(
            "_seekTo(_initialThumbnailPositionMs()); _primeThumbnailFrame(); initialPositionApplied = true;",
            fullscreen_normalized,
        )
        self.assertIn(
            "function _initialThumbnailPositionMs() { if (initialPositionMs > 0) return initialPositionMs; if (clipRangeActive && clipStartValue > 0) return clipStartValue; return 1; }",
            fullscreen_normalized,
        )

    def test_video_surfaces_prime_thumbnail_frame_without_autoplay_persistence(self) -> None:
        inline_source = (
            Path.cwd()
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "passive"
            / "GraphVideoPanelSurface.qml"
        ).read_text(encoding="utf-8")
        fullscreen_source = (
            Path.cwd()
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "passive"
            / "GraphVideoPanelFullscreenSurface.qml"
        ).read_text(encoding="utf-8")
        inline_normalized = re.sub(r"\s+", " ", inline_source)
        fullscreen_normalized = re.sub(r"\s+", " ", fullscreen_source)

        self.assertIn("muted: surface.muted || surface.thumbnailPrimerActive", inline_source)
        self.assertIn(
            "if (surface.thumbnailPrimerActive || surface.thumbnailPrimerPauseCommitGuard) { surface.thumbnailPrimerPauseCommitGuard = false; thumbnailPrimerPauseGuardTimer.stop(); return; } surface._commitPosition(position);",
            inline_normalized,
        )
        self.assertIn("_seekTo(_initialThumbnailPositionMs()); _primeThumbnailFrame();", inline_normalized)
        self.assertIn(
            "function _primeThumbnailFrame() { if (artifactRenameReleaseActive) return; if (thumbnailPrimerComplete || thumbnailPrimerActive) return;",
            inline_normalized,
        )
        self.assertIn(
            "thumbnailPrimerPauseCommitGuard = true; thumbnailPrimerPauseGuardTimer.restart(); player.pause(); thumbnailPrimerActive = false;",
            inline_normalized,
        )

        self.assertIn("muted: root.mutedValue || root.thumbnailPrimerActive", fullscreen_source)
        self.assertIn("root._primeThumbnailFrame();", fullscreen_source)
        self.assertIn("_seekTo(_initialThumbnailPositionMs()); _primeThumbnailFrame();", fullscreen_normalized)
        self.assertIn(
            "function _primeThumbnailFrame() { if (thumbnailPrimerComplete || thumbnailPrimerActive) return;",
            fullscreen_normalized,
        )
        self.assertIn(
            "if (initialPositionMs > 0 || shouldResumePlaying || errorActive) return;",
            fullscreen_normalized,
        )

    def test_video_fullscreen_playback_controls_include_rewind_and_loop_cluster(self) -> None:
        source = (
            Path.cwd()
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "passive"
            / "GraphVideoPanelFullscreenSurface.qml"
        ).read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", " ", source)

        self.assertIn('objectName: "contentFullscreenVideoRewindButton"', source)
        self.assertIn('iconName: "video-rewind"', source)
        self.assertIn("onClicked: root.rewindToStart()", source)
        self.assertIn("function rewindToStart() { _seekTo(0); }", normalized)

        control_order = [
            'objectName: "contentFullscreenVideoPlayButton"',
            'objectName: "contentFullscreenVideoRewindButton"',
            'objectName: "contentFullscreenVideoBackButton"',
            'objectName: "contentFullscreenVideoForwardButton"',
            'objectName: "contentFullscreenVideoLoopButton"',
            'objectName: "contentFullscreenVideoMuteButton"',
        ]
        positions = [source.index(marker) for marker in control_order]
        self.assertEqual(positions, sorted(positions))

    def test_video_surface_retries_thumbnail_primer_after_source_url_changes(self) -> None:
        source = (
            Path.cwd()
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "passive"
            / "GraphVideoPanelSurface.qml"
        ).read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", " ", source)

        self.assertIn("var expectedSourceUrl = resolvedSourceUrl;", source)
        self.assertIn(
            "Qt.callLater(function() { if (surface.resolvedSourceUrl !== expectedSourceUrl) return; "
            "surface._applyInitialPosition(); surface._maybeAutoPlay(); });",
            normalized,
        )

    def test_video_surface_refreshes_saved_source_after_artifact_rename(self) -> None:
        self._run_qml_probe(
            "video_surface_refreshes_saved_source_after_artifact_rename",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
            from PyQt6.QtQuick import QQuickItem

            class RenameCommandBridge(QObject):
                managedArtifactRenameReleaseRequested = pyqtSignal(str)
                managedArtifactRenameReleaseFinished = pyqtSignal(str)

            class RenameCanvasItem(QQuickItem):
                def __init__(self):
                    super().__init__()
                    self.bridge = RenameCommandBridge(self)
                    self.resolved_source_url = "file:///C:/fixtures/old/clip.mp4"
                    self.resolve_calls = []

                @pyqtProperty(QObject, constant=True)
                def canvasCommandBridgeRef(self):
                    return self.bridge

                @pyqtSlot(str, result=str)
                def resolveNodeSurfaceLocalFileSource(self, source):
                    self.resolve_calls.append(str(source or ""))
                    return self.resolved_source_url

            def video_panel_payload():
                return {
                    "node_id": "node_video_panel_rename_refresh_test",
                    "type_id": "passive.media.video_panel",
                    "title": "Video Panel",
                    "x": 100.0,
                    "y": 110.0,
                    "width": 340.0,
                    "height": 288.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": "media",
                    "surface_variant": "video_panel",
                    "surface_spec": surface_spec_payload_for_values(
                        type_id="passive.media.video_panel",
                        family="media",
                        variant="video_panel",
                    ),
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [],
                    "inline_properties": [],
                    "properties": {
                        "source_path": "saved://managed_video",
                        "fit_mode": "contain",
                        "auto_play": False,
                        "loop": False,
                        "muted": False,
                        "volume": 1.0,
                        "playback_rate": 1.0,
                        "position_ms": 0,
                    },
                }

            canvas = RenameCanvasItem()
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": video_panel_payload(), "canvasItem": canvas},
            )
            surface = host.findChild(QObject, "graphNodeVideoSurface")
            assert surface is not None
            assert surface.property("resolvedSourceUrl") == "file:///C:/fixtures/old/clip.mp4"

            canvas.bridge.managedArtifactRenameReleaseRequested.emit("node_video_panel_rename_refresh_test")
            app.processEvents()
            assert bool(surface.property("artifactRenameReleaseActive"))
            assert surface.property("effectiveResolvedSourceUrl") == ""

            canvas.resolved_source_url = "file:///C:/fixtures/new/clip.mp4"
            canvas.bridge.managedArtifactRenameReleaseFinished.emit("node_video_panel_rename_refresh_test")
            for _index in range(6):
                app.processEvents()

            assert not bool(surface.property("artifactRenameReleaseActive"))
            assert surface.property("resolvedSourceUrl") == "file:///C:/fixtures/new/clip.mp4"
            assert surface.property("effectiveResolvedSourceUrl") == "file:///C:/fixtures/new/clip.mp4"
            assert bool(surface.property("thumbnailPrimerActive"))
            assert canvas.resolve_calls.count("saved://managed_video") >= 2
            """,
        )

    def test_video_surface_capture_frame_request_sends_host_size(self) -> None:
        source = (
            Path.cwd()
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "passive"
            / "GraphVideoPanelSurface.qml"
        ).read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", " ", source)

        self.assertIn(
            "var size = _capturedFrameImageNodeSize();",
            normalized,
        )
        self.assertIn(
            "bridge.request_create_video_frame_image_node( nodeId, capturePath, position, point.x, point.y, size.width, size.height );",
            normalized,
        )

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
            from ea_node_editor.ui_qml.surface_contracts import surface_spec_payload_for_values
            from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
            from tests.qt_wait import wait_for_condition_or_raise

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

            def wait_for_preview(surface, timeout_ms=5000):
                wait_for_condition_or_raise(
                    lambda: str(surface.property("previewState")) in {"ready", "error"},
                    timeout_ms=timeout_ms,
                    app=app,
                    timeout_message="Timed out waiting for media preview to settle.",
                )

            def image_panel_payload(properties):
                node_properties = {
                    "show_title": True,
                    "show_frame": True,
                }
                node_properties.update(properties)
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
                    "surface_spec": surface_spec_payload_for_values(
                        type_id="passive.media.image_panel",
                        family="media",
                        variant="image_panel",
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
                    "properties": node_properties,
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
            assert len(named_child_items(host, "graphNodeInputPortMouseArea")) == 2
            assert len(named_child_items(host, "graphNodeOutputPortMouseArea")) == 2
            assert not any(item.isVisible() for item in named_child_items(host, "graphNodeInputPortLabel"))
            assert not any(item.isVisible() for item in named_child_items(host, "graphNodeOutputPortLabel"))
            """,
        )

    def test_mail_panel_placeholder_keeps_host_interaction_and_declares_fullscreen_action(self) -> None:
        self._run_qml_probe(
            "mail-panel-placeholder-interaction-and-fullscreen",
            """
            from PyQt6.QtCore import pyqtSlot

            class ContentFullscreenBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.calls = []

                @pyqtSlot(str, "QVariantMap", result=bool)
                def request_toggle_for_node_with_state(self, node_id, state):
                    self.calls.append((str(node_id or ""), dict(state or {})))
                    return True

            fullscreen_bridge = ContentFullscreenBridgeStub()
            engine.rootContext().setContextProperty("contentFullscreenBridge", fullscreen_bridge)

            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": {
                        "node_id": "node_mail_panel_ready_preview",
                        "type_id": "passive.media.mail_panel",
                        "title": "Mail Panel",
                        "x": 100.0,
                        "y": 110.0,
                        "width": 360.0,
                        "height": 300.0,
                        "accent": "#2F89FF",
                        "collapsed": False,
                        "selected": False,
                        "runtime_behavior": "passive",
                        "surface_family": "media",
                        "surface_variant": "mail_panel",
                        "surface_spec": surface_spec_payload_for_values(
                            type_id="passive.media.mail_panel",
                            family="media",
                            variant="mail_panel",
                        ),
                        "visual_style": {},
                        "can_enter_scope": False,
                        "ports": [],
                        "inline_properties": [],
                        "properties": {
                            "source_path": "",
                            "show_title": True,
                            "show_frame": True,
                        },
                    },
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeMailSurface")
            assert loader is not None
            assert surface is not None

            assert str(surface.property("previewState")) == "placeholder"
            assert not bool(surface.property("blocksHostInteraction"))
            assert not bool(loader.property("blocksHostInteraction"))
            action = next(action for action in variant_list(surface.property("surfaceActions")) if action["id"] == "fullscreen")
            assert not bool(action["enabled"])
            assert not bool(surface.dispatchSurfaceAction("fullscreen"))
            assert fullscreen_bridge.calls == []
            """,
        )

    def test_graph_node_host_loads_video_panel_surface_controls_and_source_policy(self) -> None:
        self._run_qml_probe(
            "video-media-host",
            """
            from PyQt6.QtCore import pyqtSlot
            from PyQt6.QtQuick import QQuickItem

            class ContentFullscreenBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.calls = []

                @pyqtSlot(str, "QVariantMap", result=bool)
                def request_toggle_for_node_with_state(self, node_id, state):
                    self.calls.append((str(node_id or ""), dict(state or {})))
                    return True

            class VideoRepairCanvasItem(QQuickItem):
                def __init__(self, repaired_path):
                    super().__init__()
                    self.repaired_path = str(repaired_path)
                    self.last_browse_args = None
                    self.resolved_source_url = "file:///C:/fixtures/clip.mp4"
                    self.last_resolve_source = None

                @pyqtSlot(str, str, str, result=str)
                @pyqtSlot(str, str, str, str, result=str)
                def browseNodePropertyPath(self, node_id, key, current_path, source_mode=""):
                    normalized_source_mode = str(source_mode or "")
                    self.last_browse_args = (
                        str(node_id or ""),
                        str(key or ""),
                        str(current_path or ""),
                        normalized_source_mode,
                    ) if normalized_source_mode else (
                        str(node_id or ""),
                        str(key or ""),
                        str(current_path or ""),
                    )
                    return self.repaired_path

                @pyqtSlot(str, result=str)
                def resolveNodeSurfaceLocalFileSource(self, source):
                    self.last_resolve_source = str(source or "")
                    return self.resolved_source_url

            fullscreen_bridge = ContentFullscreenBridgeStub()
            engine.rootContext().setContextProperty("contentFullscreenBridge", fullscreen_bridge)

            def video_panel_payload(properties, *, selected=False, node_id="node_video_panel_surface_test"):
                return {
                    "node_id": node_id,
                    "type_id": "passive.media.video_panel",
                    "title": "Video Panel",
                    "x": 100.0,
                    "y": 110.0,
                    "width": 340.0,
                    "height": 288.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": selected,
                    "runtime_behavior": "passive",
                    "surface_family": "media",
                    "surface_variant": "video_panel",
                    "surface_spec": surface_spec_payload_for_values(
                        type_id="passive.media.video_panel",
                        family="media",
                        variant="video_panel",
                    ),
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [],
                    "inline_properties": [],
                    "properties": properties,
                }

            placeholder_browse_canvas = VideoRepairCanvasItem(r"C:\\fixtures\\clip.mp4")
            placeholder_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": video_panel_payload(
                        {
                            "source_path": "",
                            "fit_mode": "contain",
                            "auto_play": False,
                            "loop": False,
                            "muted": False,
                            "volume": 1.0,
                            "playback_rate": 1.0,
                            "position_ms": 0,
                            "unfocused_behavior": "pause_keep_loaded",
                        }
                    ),
                    "canvasItem": placeholder_browse_canvas,
                },
            )

            loader = placeholder_host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = placeholder_host.findChild(QObject, "graphNodeVideoSurface")
            seek_slider = placeholder_host.findChild(QObject, "graphNodeVideoSeekSlider")
            seek_strip = placeholder_host.findChild(QObject, "graphNodeVideoControls")
            assert loader is not None
            assert surface is not None
            assert seek_slider is not None
            assert seek_strip is not None
            assert loader.property("loadedSurfaceKey") == "media"
            assert "GraphVideoPanelSurface.qml" in str(loader.property("loadedSurfaceSource"))
            assert surface.property("previewState") == "placeholder"
            assert surface.property("resolvedSourceUrl") == ""
            assert float(seek_strip.property("width")) <= float(surface.property("width"))
            assert float(seek_slider.property("width")) > 0.0
            assert placeholder_host.findChild(QObject, "graphNodeVideoPlayButton") is None
            assert placeholder_host.findChild(QObject, "graphNodeVideoBackButton") is None
            assert placeholder_host.findChild(QObject, "graphNodeVideoForwardButton") is None
            assert placeholder_host.findChild(QObject, "graphNodeVideoMuteButton") is None
            assert placeholder_host.findChild(QObject, "graphNodeVideoRateCombo") is None
            assert placeholder_host.findChild(QObject, "graphNodeVideoLoopButton") is None
            assert placeholder_host.findChild(QObject, "graphNodeVideoFitButton") is None
            assert placeholder_host.findChild(QObject, "graphNodeVideoFullscreenButton") is None
            assert placeholder_host.findChild(QObject, "graphNodeVideoRepairButton") is None
            placeholder_actions = variant_list(surface.property("surfaceActions"))
            assert [action["id"] for action in placeholder_actions] == [
                "editSource",
                "toggle_content_only",
                "toggle_title",
                "toggle_frame",
            ]
            assert placeholder_actions[0]["icon"] == "search"
            assert placeholder_actions[1]["icon"] == "content-only"
            assert placeholder_actions[2]["icon"] == "title-heading"
            assert placeholder_actions[3]["icon"] == "frame-corners"
            assert placeholder_actions[0]["popover_layout"] == "source_storage"
            source_storage_actions = variant_list(placeholder_actions[0]["popoverActions"])
            assert [action["id"] for action in source_storage_actions] == [
                "editSourceExternalLink",
                "editSourceManagedCopy",
            ]
            assert source_storage_actions[0]["toolbar_text"] == "External"
            assert source_storage_actions[0]["source_mode"] == "external_link"
            assert bool(source_storage_actions[0]["checked"])
            assert source_storage_actions[1]["toolbar_text"] == "Internal"
            assert source_storage_actions[1]["source_mode"] == "managed_copy"

            commits = []
            placeholder_host.inlinePropertyCommitted.connect(
                lambda node_id, key, value: commits.append((node_id, key, variant_value(value)))
            )
            assert bool(surface.dispatchSurfaceAction("editSource"))
            assert placeholder_browse_canvas.last_browse_args == (
                "node_video_panel_surface_test",
                "source_path",
                "",
                "external_link",
            )
            assert commits == [
                ("node_video_panel_surface_test", "source_path", r"C:\\fixtures\\clip.mp4"),
            ]
            commits.clear()
            assert bool(surface.dispatchSurfaceAction("editSourceExternalLink"))
            assert placeholder_browse_canvas.last_browse_args == (
                "node_video_panel_surface_test",
                "source_path",
                "",
                "external_link",
            )
            assert commits == [
                ("node_video_panel_surface_test", "source_path", r"C:\\fixtures\\clip.mp4"),
            ]
            commits.clear()
            assert bool(surface.dispatchSurfaceAction("editSourceManagedCopy"))
            assert placeholder_browse_canvas.last_browse_args == (
                "node_video_panel_surface_test",
                "source_path",
                "",
                "managed_copy",
            )
            assert commits == [
                ("node_video_panel_surface_test", "source_path", r"C:\\fixtures\\clip.mp4"),
            ]

            managed_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": video_panel_payload(
                        {
                            "source_path": "temp://managed_video",
                            "fit_mode": "contain",
                            "auto_play": False,
                            "loop": False,
                            "muted": False,
                            "volume": 1.0,
                            "playback_rate": 1.0,
                            "position_ms": 0,
                            "unfocused_behavior": "pause_keep_loaded",
                        },
                        node_id="node_video_panel_managed_surface_test",
                    ),
                    "canvasItem": placeholder_browse_canvas,
                },
            )
            managed_surface = managed_host.findChild(QObject, "graphNodeVideoSurface")
            assert managed_surface is not None
            assert managed_surface.property("resolvedSourceUrl") == "file:///C:/fixtures/clip.mp4"
            assert not bool(managed_surface.property("sourceRejected"))
            assert placeholder_browse_canvas.last_resolve_source == "temp://managed_video"
            managed_actions = variant_list(managed_surface.property("surfaceActions"))
            managed_storage_actions = variant_list(managed_actions[0]["popoverActions"])
            assert not bool(managed_storage_actions[0].get("checked", False))
            assert bool(managed_storage_actions[1]["checked"])
            managed_commits = []
            managed_host.inlinePropertyCommitted.connect(
                lambda node_id, key, value: managed_commits.append((node_id, key, variant_value(value)))
            )
            placeholder_browse_canvas.repaired_path = "temp://managed_video_replacement"
            assert bool(managed_surface.dispatchSurfaceAction("editSource"))
            assert placeholder_browse_canvas.last_browse_args == (
                "node_video_panel_managed_surface_test",
                "source_path",
                "temp://managed_video",
                "managed_copy",
            )
            assert managed_commits == [
                ("node_video_panel_managed_surface_test", "source_path", "temp://managed_video_replacement"),
            ]

            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
                video_path = Path(temp_dir) / "clip.mp4"
                video_path.write_bytes(b"not a real video but a local path")
                repaired_path = Path(temp_dir) / "repaired.mp4"
                repair_canvas = VideoRepairCanvasItem(repaired_path)
                local_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": video_panel_payload(
                            {
                                "source_path": str(video_path),
                                "fit_mode": "contain",
                                "auto_play": False,
                                "loop": False,
                                "muted": False,
                                "volume": 1.0,
                                "playback_rate": 1.0,
                                "position_ms": 0,
                                "unfocused_behavior": "keep_playing",
                            },
                            selected=True,
                            node_id="node_video_panel_local_surface_test",
                        ),
                    },
                )
                remote_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": video_panel_payload(
                            {
                                "source_path": "https://example.com/video.mp4",
                                "fit_mode": "cover",
                                "auto_play": False,
                                "loop": True,
                                "muted": True,
                                "volume": 0.25,
                                "playback_rate": 1.5,
                                "position_ms": 1200,
                                "unfocused_behavior": "keep_playing",
                            },
                            node_id="node_video_panel_remote_surface_test",
                        ),
                        "canvasItem": repair_canvas,
                    },
                )

                local_surface = local_host.findChild(QObject, "graphNodeVideoSurface")
                assert local_surface is not None
                local_actions = variant_list(local_surface.property("surfaceActions"))
                local_action_ids = [action["id"] for action in local_actions]
                expected_local_actions = [
                    "editSource",
                    "internalizeSource",
                    "toggle_content_only",
                    "toggle_title",
                    "toggle_frame",
                    "playPause",
                    "rewindToStart",
                    "seekBack10",
                    "seekForward10",
                    "loop",
                    "bookmarks",
                    "captureFrame",
                    "timestampAnnotation",
                    "clipRange",
                    "mute",
                    "fitMode",
                    "fullscreen",
                ]
                assert local_action_ids[:len(expected_local_actions)] == expected_local_actions, local_action_ids
                local_actions_by_id = {action["id"]: action for action in local_actions}
                assert local_actions_by_id["internalizeSource"]["icon"] == "internalize-source"
                assert bool(local_actions_by_id["internalizeSource"]["enabled"])
                assert local_actions_by_id["playPause"]["icon"] in {"run", "pause"}
                assert local_actions_by_id["rewindToStart"]["icon"] == "video-rewind"
                assert local_actions_by_id["seekBack10"]["icon"] == "video-seek-back-10"
                assert local_actions_by_id["seekForward10"]["icon"] == "video-seek-forward-10"
                assert local_actions_by_id["loop"]["icon"] == "video-loop"
                assert local_actions_by_id["bookmarks"]["icon"] == "video-bookmarks"
                assert local_actions_by_id["bookmarks"]["popover_layout"] == "video_bookmarks"
                assert local_actions_by_id["bookmarks"]["popoverActions"][0]["id"] == "videoBookmarkAdd"
                assert local_actions_by_id["bookmarks"]["popoverActions"][0]["icon"] == "video-bookmark-add"
                assert local_actions_by_id["captureFrame"]["icon"] == "video-capture-frame"
                assert local_actions_by_id["timestampAnnotation"]["icon"] == "video-timestamp-note"
                assert local_actions_by_id["clipRange"]["icon"] == "video-clip-range"
                assert [action["id"] for action in local_actions_by_id["clipRange"]["popoverActions"]] == [
                    "videoClipToggle",
                    "videoClipSetIn",
                    "videoClipSetOut",
                    "videoClipReplaceTrimmed",
                    "videoClipSaveTrimmedCopy",
                    "videoClipClear",
                ]
                assert [action["icon"] for action in local_actions_by_id["clipRange"]["popoverActions"]] == [
                    "video-clip-range",
                    "video-clip-in",
                    "video-clip-out",
                    "video-trim-save",
                    "video-trim-save",
                    "x",
                ]
                assert local_actions_by_id["mute"]["icon"] in {"volume", "volume-muted"}
                assert local_actions_by_id["fitMode"]["icon"] == "video-fill"
                assert bool(local_actions_by_id["fullscreen"]["enabled"])

                local_commits = []
                local_host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: local_commits.append((node_id, key, variant_value(value)))
                )
                assert bool(local_surface.dispatchSurfaceAction("playPause"))
                assert bool(local_surface.dispatchSurfaceAction("rewindToStart"))
                assert bool(local_surface.dispatchSurfaceAction("seekBack10"))
                assert bool(local_surface.dispatchSurfaceAction("seekForward10"))
                assert bool(local_surface.dispatchSurfaceAction("videoBookmarkAdd"))
                assert bool(local_surface.dispatchSurfaceAction("videoClipSetIn"))
                assert bool(local_surface.dispatchSurfaceAction("videoClipSetOut"))
                assert bool(local_surface.dispatchSurfaceAction("mute"))
                assert bool(local_surface.dispatchSurfaceAction("loop"))
                assert bool(local_surface.dispatchSurfaceAction("fitMode"))
                assert bool(local_surface.dispatchSurfaceAction("fullscreen"))
                assert fullscreen_bridge.calls
                assert fullscreen_bridge.calls[-1][0] == "node_video_panel_local_surface_test"
                assert any(call[1] == "timeline_bookmarks" for call in local_commits)
                assert ("node_video_panel_local_surface_test", "clip_enabled", True) in local_commits
                assert ("node_video_panel_local_surface_test", "muted", True) in local_commits
                assert ("node_video_panel_local_surface_test", "loop", True) in local_commits
                assert ("node_video_panel_local_surface_test", "fit_mode", "cover") in local_commits

                remote_surface = remote_host.findChild(QObject, "graphNodeVideoSurface")
                assert remote_surface is not None
                assert bool(remote_surface.property("sourceRejected"))
                assert remote_surface.property("previewState") == "error"
                assert remote_surface.property("resolvedSourceUrl") == ""
                remote_actions = variant_list(remote_surface.property("surfaceActions"))
                action_ids = [action["id"] for action in remote_actions]
                assert action_ids == [
                    "editSource",
                    "toggle_content_only",
                    "toggle_title",
                    "toggle_frame",
                    "repair",
                ]
                assert bool(next(action for action in remote_actions if action["id"] == "repair")["enabled"])

                remote_commits = []
                remote_host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: remote_commits.append((node_id, key, variant_value(value)))
                )
                assert bool(remote_surface.dispatchSurfaceAction("repair"))
                assert repair_canvas.last_browse_args is not None
                assert repair_canvas.last_browse_args[0] == "node_video_panel_remote_surface_test"
                assert repair_canvas.last_browse_args[1] == "source_path"
                assert repair_canvas.last_browse_args[2].startswith("ea-file-repair:")
                assert remote_commits == [
                    ("node_video_panel_remote_surface_test", "source_path", str(repaired_path))
                ]
            """,
        )

    def test_video_position_persistence_does_not_select_node_on_blur_pause(self) -> None:
        self._run_qml_probe(
            "video-position-persistence-selection-neutral",
            """
            from PyQt6.QtCore import pyqtProperty, pyqtSlot
            from PyQt6.QtQuick import QQuickItem

            class SceneCommandBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.set_node_properties_calls = []
                    self.set_node_property_calls = []

                @pyqtSlot(str)
                @pyqtSlot(str, bool)
                def select_node(self, node_id, additive=False):
                    self.select_calls.append((str(node_id or ""), bool(additive)))

                @pyqtSlot(str, "QVariantMap", result=bool)
                def set_node_properties(self, node_id, properties):
                    self.set_node_properties_calls.append((str(node_id or ""), dict(properties or {})))
                    return True

                @pyqtSlot(str, str, "QVariant")
                def set_node_property(self, node_id, key, value):
                    self.set_node_property_calls.append(
                        (str(node_id or ""), str(key or ""), variant_value(value))
                    )

            class PlaybackCanvasItem(QQuickItem):
                def __init__(self, scene_command_bridge):
                    super().__init__()
                    self._scene_command_bridge = scene_command_bridge

                @pyqtProperty(QObject, constant=True)
                def sceneCommandBridge(self):
                    return self._scene_command_bridge

            def video_panel_payload():
                return {
                    "node_id": "node_video_position_persistence",
                    "type_id": "passive.media.video_panel",
                    "title": "Video Panel",
                    "x": 100.0,
                    "y": 110.0,
                    "width": 340.0,
                    "height": 288.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": "media",
                    "surface_variant": "video_panel",
                    "surface_spec": surface_spec_payload_for_values(
                        type_id="passive.media.video_panel",
                        family="media",
                        variant="video_panel",
                    ),
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [],
                    "inline_properties": [],
                    "properties": {
                        "source_path": "",
                        "fit_mode": "contain",
                        "auto_play": False,
                        "loop": False,
                        "muted": False,
                        "volume": 1.0,
                        "playback_rate": 1.0,
                        "position_ms": 0,
                        "unfocused_behavior": "pause_keep_loaded",
                    },
                }

            scene_command_bridge = SceneCommandBridgeStub()
            canvas_item = PlaybackCanvasItem(scene_command_bridge)
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": video_panel_payload(),
                    "canvasItem": canvas_item,
                },
            )
            surface = host.findChild(QObject, "graphNodeVideoSurface")
            assert surface is not None

            inline_commits = []
            host.inlinePropertyCommitted.connect(
                lambda node_id, key, value: inline_commits.append((node_id, key, variant_value(value)))
            )

            assert bool(surface._commitPosition(2500))
            app.processEvents()

            assert scene_command_bridge.select_calls == []
            assert scene_command_bridge.set_node_properties_calls == [
                ("node_video_position_persistence", {"position_ms": 2500})
            ]
            assert scene_command_bridge.set_node_property_calls == []
            assert inline_commits == []
            """,
        )

    def test_video_play_action_allows_refocus_before_selection_binding_updates(self) -> None:
        self._run_qml_probe(
            "video-play-refocus-selection-lag",
            """
            def video_panel_payload():
                return {
                    "node_id": "node_video_refocus_play",
                    "type_id": "passive.media.video_panel",
                    "title": "Video Panel",
                    "x": 100.0,
                    "y": 110.0,
                    "width": 340.0,
                    "height": 288.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": "media",
                    "surface_variant": "video_panel",
                    "surface_spec": surface_spec_payload_for_values(
                        type_id="passive.media.video_panel",
                        family="media",
                        variant="video_panel",
                    ),
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [],
                    "inline_properties": [],
                    "properties": {
                        "source_path": r"C:\\fixtures\\clip.mp4",
                        "fit_mode": "contain",
                        "auto_play": False,
                        "loop": False,
                        "muted": False,
                        "volume": 1.0,
                        "playback_rate": 1.0,
                        "position_ms": 0,
                        "unfocused_behavior": "pause_keep_loaded",
                    },
                }

            host = create_component(graph_node_host_qml_path, {"nodeData": video_panel_payload()})
            surface = host.findChild(QObject, "graphNodeVideoSurface")
            assert surface is not None
            assert bool(surface.property("validSourceActive"))
            assert bool(surface.property("hostPlaybackAllowed"))

            assert bool(surface.dispatchSurfaceAction("playPause"))
            """,
        )

    def test_video_inline_playback_is_not_gated_by_canvas_selection(self) -> None:
        self._run_qml_probe(
            "video-inline-playback-selection-independent",
            """
            from PyQt6.QtCore import pyqtProperty, pyqtSignal
            from PyQt6.QtQuick import QQuickItem

            class SceneBridgeStub(QObject):
                selectedNodeLookupChanged = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._selected_node_lookup = {}

                @pyqtProperty("QVariantMap", notify=selectedNodeLookupChanged)
                def selected_node_lookup(self):
                    return dict(self._selected_node_lookup)

                def select_only(self, node_id):
                    self._selected_node_lookup = {str(node_id or ""): True}
                    self.selectedNodeLookupChanged.emit()

            class SelectionCanvasItem(QQuickItem):
                def __init__(self, scene_bridge):
                    super().__init__()
                    self._scene_bridge = scene_bridge

                @pyqtProperty(QObject, constant=True)
                def sceneBridge(self):
                    return self._scene_bridge

            def video_panel_payload(node_id):
                return {
                    "node_id": node_id,
                    "type_id": "passive.media.video_panel",
                    "title": "Video Panel",
                    "x": 100.0,
                    "y": 110.0,
                    "width": 340.0,
                    "height": 288.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": "media",
                    "surface_variant": "video_panel",
                    "surface_spec": surface_spec_payload_for_values(
                        type_id="passive.media.video_panel",
                        family="media",
                        variant="video_panel",
                    ),
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [],
                    "inline_properties": [],
                    "properties": {
                        "source_path": r"C:\\fixtures\\clip.mp4",
                        "fit_mode": "contain",
                        "auto_play": False,
                        "loop": False,
                        "muted": False,
                        "volume": 1.0,
                        "playback_rate": 1.0,
                        "position_ms": 0,
                        "unfocused_behavior": "pause_keep_loaded",
                    },
                }

            scene_bridge = SceneBridgeStub()
            canvas_item = SelectionCanvasItem(scene_bridge)
            first_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": video_panel_payload("first_video_panel"),
                    "canvasItem": canvas_item,
                },
            )
            second_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": video_panel_payload("second_video_panel"),
                    "canvasItem": canvas_item,
                },
            )
            first_surface = first_host.findChild(QObject, "graphNodeVideoSurface")
            second_surface = second_host.findChild(QObject, "graphNodeVideoSurface")
            assert first_surface is not None
            assert second_surface is not None

            scene_bridge.select_only("first_video_panel")
            app.processEvents()
            assert bool(first_host.property("isSelected"))
            assert not bool(second_host.property("isSelected"))
            assert bool(first_surface.property("hostPlaybackAllowed"))
            assert bool(second_surface.property("hostPlaybackAllowed"))

            scene_bridge.select_only("second_video_panel")
            app.processEvents()
            assert not bool(first_host.property("isSelected"))
            assert bool(second_host.property("isSelected"))
            assert bool(first_surface.property("hostPlaybackAllowed"))
            assert bool(second_surface.property("hostPlaybackAllowed"))
            """,
        )

    def test_image_node_toolbar_actions_toggle_chrome_properties(self) -> None:
        self._run_qml_probe(
            "media-appearance-toolbar",
            """
            from PyQt6.QtCore import pyqtSlot
            from PyQt6.QtQuick import QQuickItem

            class MediaBrowseCanvasItem(QQuickItem):
                def __init__(self, selected_path):
                    super().__init__()
                    self.selected_path = str(selected_path)
                    self.last_browse_args = None

                @pyqtSlot(str, str, str, result=str)
                @pyqtSlot(str, str, str, str, result=str)
                def browseNodePropertyPath(self, node_id, key, current_path, source_mode=""):
                    self.last_browse_args = (
                        str(node_id or ""),
                        str(key or ""),
                        str(current_path or ""),
                        str(source_mode or ""),
                    )
                    return self.selected_path

            canvas_item = MediaBrowseCanvasItem(r"C:\\fixtures\\external-image.png")
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": image_panel_payload(
                        {
                            "source_path": "",
                            "fit_mode": "contain",
                        }
                    ),
                    "canvasItem": canvas_item,
                },
            )
            surface = host.findChild(QObject, "graphNodeMediaSurface")
            assert surface is not None

            actions = variant_list(surface.property("surfaceActions"))
            action_ids = [action["id"] for action in actions]
            assert action_ids[:4] == ["editSource", "toggle_content_only", "toggle_title", "toggle_frame"]
            source_action = next(action for action in actions if action["id"] == "editSource")
            assert source_action["icon"] == "search"
            source_storage_actions = variant_list(source_action["popoverActions"])
            assert bool(source_storage_actions[0]["checked"])
            assert not bool(source_storage_actions[1].get("checked", False))
            assert next(action for action in actions if action["id"] == "toggle_content_only")["label"] == "Content only"
            assert next(action for action in actions if action["id"] == "toggle_title")["label"] == "Hide title"
            assert next(action for action in actions if action["id"] == "toggle_frame")["label"] == "Hide frame"

            commits = []
            host.inlinePropertyCommitted.connect(lambda node_id, key, value: commits.append((node_id, key, value)))
            assert bool(surface.dispatchSurfaceAction("editSource"))
            assert canvas_item.last_browse_args == (
                "node_image_panel_surface_test",
                "source_path",
                "",
                "external_link",
            )
            assert commits == [
                ("node_image_panel_surface_test", "source_path", r"C:\\fixtures\\external-image.png"),
            ]
            commits.clear()
            assert bool(surface.dispatchSurfaceAction("toggle_content_only"))
            assert commits[-2:] == [
                ("node_image_panel_surface_test", "show_title", False),
                ("node_image_panel_surface_test", "show_frame", False),
            ]

            managed_canvas_item = MediaBrowseCanvasItem("temp://managed_image_replacement")
            managed_payload = image_panel_payload(
                {
                    "source_path": "temp://managed_image",
                    "fit_mode": "contain",
                }
            )
            managed_payload["node_id"] = "node_image_panel_managed_surface_test"
            managed_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": managed_payload,
                    "canvasItem": managed_canvas_item,
                },
            )
            managed_surface = managed_host.findChild(QObject, "graphNodeMediaSurface")
            assert managed_surface is not None
            managed_actions = variant_list(managed_surface.property("surfaceActions"))
            managed_source_action = next(action for action in managed_actions if action["id"] == "editSource")
            managed_storage_actions = variant_list(managed_source_action["popoverActions"])
            assert not bool(managed_storage_actions[0].get("checked", False))
            assert bool(managed_storage_actions[1]["checked"])
            managed_commits = []
            managed_host.inlinePropertyCommitted.connect(
                lambda node_id, key, value: managed_commits.append((node_id, key, value))
            )
            assert bool(managed_surface.dispatchSurfaceAction("editSource"))
            assert managed_canvas_item.last_browse_args == (
                "node_image_panel_managed_surface_test",
                "source_path",
                "temp://managed_image",
                "managed_copy",
            )
            assert managed_commits == [
                ("node_image_panel_managed_surface_test", "source_path", "temp://managed_image_replacement"),
            ]

            content_only_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": image_panel_payload(
                        {
                            "source_path": "",
                            "fit_mode": "contain",
                            "show_title": False,
                            "show_frame": False,
                        }
                    ),
                },
            )
            content_surface = content_only_host.findChild(QObject, "graphNodeMediaSurface")
            header = content_only_host.findChild(QObject, "graphNodeHeaderLayer")
            preview = content_only_host.findChild(QObject, "graphNodeMediaPreviewViewport")
            assert bool(content_only_host.property("imageNodeContentOnlyActive"))
            assert not bool(content_only_host.property("imageNodeTitleVisible"))
            assert not bool(content_only_host.property("imageNodeFrameVisible"))
            assert not bool(content_only_host.property("_useHostChrome"))
            assert not bool(content_only_host.property("_backgroundShadowVisible"))
            assert not bool(header.property("headerTitleVisible"))
            assert bool(content_surface.property("imageContentOnlyActive"))
            assert not bool(preview.property("viewportFrameVisible"))
            assert next(
                action
                for action in variant_list(content_surface.property("surfaceActions"))
                if action["id"] == "toggle_content_only"
            )["label"] == "Show chrome"
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
                            "fit_mode": "contain",
                        }
                    ),
                },
            )
            surface = host.findChild(QObject, "graphNodeMediaSurface")
            assert surface is not None
            assert surface.property("previewState") == "placeholder"
            assert surface.property("resolvedSourceUrl") == ""
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
                assert str(contain_surface.property("resolvedSourceUrl")).startswith("file:///")
                assert contain_surface.property("appliedFitMode") == "contain"
                assert bool(contain_surface.property("cropToolAvailable"))
                preview_image = contain_host.findChild(QObject, "graphNodeMediaPreviewImage")
                applied_image = contain_host.findChild(QObject, "graphNodeMediaAppliedImage")
                assert preview_image is not None
                assert applied_image is not None
                preview_source = preview_image.property("source")
                applied_source = applied_image.property("source")
                preview_source_text = preview_source.toString() if hasattr(preview_source, "toString") else str(preview_source)
                applied_source_text = applied_source.toString() if hasattr(applied_source, "toString") else str(applied_source)
                assert preview_source_text == "", preview_source_text
                assert applied_source_text, applied_source_text
                assert cover_surface.property("previewState") == "ready"
                assert cover_surface.property("appliedFitMode") == "cover"
                assert original_surface.property("previewState") == "ready"
                assert original_surface.property("appliedFitMode") == "original"
                assert bool(original_surface.property("originalModeActive"))
            """,
        )

    def test_image_panel_toolbar_rotate_and_mirror_actions_persist_hidden_state(self) -> None:
        self._run_qml_probe(
            "media-image-transform-toolbar",
            """
            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "transformable-image.png"
                image = QImage(32, 20, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(image_path),
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                transform_frame = host.findChild(QObject, "graphNodeMediaAppliedImageTransformFrame")
                mirror_frame = host.findChild(QObject, "graphNodeMediaAppliedImageMirrorFrame")
                assert surface is not None
                assert transform_frame is not None
                assert mirror_frame is not None
                wait_for_preview(surface)

                actions = variant_list(surface.property("surfaceActions"))
                action_ids = [action["id"] for action in actions]
                actions_by_id = {action["id"]: action for action in actions}
                transform_start = action_ids.index("crop")
                assert action_ids[transform_start : transform_start + 6] == [
                    "crop",
                    "save_crop_image",
                    "lock_aspect_ratio",
                    "rotate_clockwise",
                    "mirror_horizontal",
                    "mirror_vertical",
                ]
                assert actions_by_id["save_crop_image"]["icon"] == "crop"
                assert not bool(actions_by_id["save_crop_image"]["enabled"])
                assert actions_by_id["lock_aspect_ratio"]["icon"] == "lock"
                assert actions_by_id["rotate_clockwise"]["icon"] == "rotate-clockwise"
                assert actions_by_id["mirror_horizontal"]["icon"] == "flip-horizontal"
                assert actions_by_id["mirror_vertical"]["icon"] == "flip-vertical"
                assert bool(actions_by_id["lock_aspect_ratio"]["enabled"])
                assert bool(actions_by_id["rotate_clockwise"]["enabled"])
                assert bool(actions_by_id["mirror_horizontal"]["enabled"])
                assert bool(actions_by_id["mirror_vertical"]["enabled"])
                assert not bool(actions_by_id["lock_aspect_ratio"].get("checked", False))
                assert not bool(actions_by_id["rotate_clockwise"].get("checked", False))
                assert not bool(actions_by_id["mirror_horizontal"].get("checked", False))
                assert not bool(actions_by_id["mirror_vertical"].get("checked", False))
                assert float(transform_frame.property("rotation")) == 0.0

                commits = []
                host.inlinePropertyCommitted.connect(
                    lambda node_id, key, value: commits.append((node_id, key, variant_value(value)))
                )
                assert bool(surface.dispatchSurfaceAction("lock_aspect_ratio"))
                assert bool(surface.dispatchSurfaceAction("rotate_clockwise"))
                assert bool(surface.dispatchSurfaceAction("mirror_horizontal"))
                assert bool(surface.dispatchSurfaceAction("mirror_vertical"))
                assert commits == [
                    ("node_image_panel_surface_test", "lock_aspect_ratio", True),
                    ("node_image_panel_surface_test", "rotation_degrees", 90),
                    ("node_image_panel_surface_test", "mirror_horizontal", True),
                    ("node_image_panel_surface_test", "mirror_vertical", True),
                ]

                transformed_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(image_path),
                                "fit_mode": "contain",
                                "lock_aspect_ratio": True,
                                "rotation_degrees": 90,
                                "mirror_horizontal": True,
                                "mirror_vertical": True,
                            }
                        ),
                    },
                )
                transformed_surface = transformed_host.findChild(QObject, "graphNodeMediaSurface")
                transformed_frame = transformed_host.findChild(QObject, "graphNodeMediaAppliedImageTransformFrame")
                assert transformed_surface is not None
                assert transformed_frame is not None
                wait_for_preview(transformed_surface)

                assert int(transformed_surface.property("appliedImageRotationDegrees")) == 90
                assert bool(transformed_surface.property("appliedImageMirrorHorizontal"))
                assert bool(transformed_surface.property("appliedImageMirrorVertical"))
                assert bool(transformed_surface.property("imageAspectRatioLocked"))
                assert float(transformed_frame.property("rotation")) == 90.0
                transformed_actions = {
                    action["id"]: action
                    for action in variant_list(transformed_surface.property("surfaceActions"))
                }
                assert bool(transformed_actions["lock_aspect_ratio"].get("checked", False))
                assert bool(transformed_actions["rotate_clockwise"].get("checked", False))
                assert bool(transformed_actions["mirror_horizontal"].get("checked", False))
                assert bool(transformed_actions["mirror_vertical"].get("checked", False))

                transformed_surface.setProperty("cropModeActive", True)
                app.processEvents()
                crop_actions = {
                    action["id"]: action
                    for action in variant_list(transformed_surface.property("surfaceActions"))
                }
                assert not bool(crop_actions["lock_aspect_ratio"]["enabled"])
                assert not bool(crop_actions["rotate_clockwise"]["enabled"])
                assert not bool(crop_actions["save_crop_image"]["enabled"])
                assert not bool(crop_actions["mirror_horizontal"]["enabled"])
                assert not bool(crop_actions["mirror_vertical"]["enabled"])
                assert not bool(transformed_surface.dispatchSurfaceAction("lock_aspect_ratio"))
                assert not bool(transformed_surface.dispatchSurfaceAction("rotate_clockwise"))
            """,
        )

    def test_image_panel_overlay_geometry_and_fullscreen_dispatch_are_guarded(self) -> None:
        self._run_qml_probe(
            "media-overlay-fullscreen-guardrails",
            """
            from PyQt6.QtCore import Q_ARG, QMetaObject, pyqtSlot

            class ContentFullscreenBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.toggle_calls = []

                @pyqtSlot(str, result=bool)
                def request_toggle_for_node(self, node_id):
                    self.toggle_calls.append(str(node_id or ""))
                    return True

            bridge = ContentFullscreenBridgeStub()
            engine.rootContext().setContextProperty("contentFullscreenBridge", bridge)

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "overlay-guardrail.png"
                image = QImage(48, 32, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {
                                "source_path": str(image_path),
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                preview = host.findChild(QObject, "graphNodeMediaPreviewViewport")
                assert surface is not None
                assert preview is not None
                wait_for_preview(surface)
                assert surface.property("previewState") == "ready"

                assert surface.property("overlayPreviewKind") == "image"
                assert bool(surface.property("overlayPreviewVisible"))
                content_rect = surface.property("overlayContentRect")
                source_clip = surface.property("overlaySourceClipRect")
                assert round(float(content_rect.width()), 3) > 0.0
                assert round(float(content_rect.height()), 3) > 0.0
                assert round(float(source_clip.width()), 3) == 48.0
                assert round(float(source_clip.height()), 3) == 32.0

                def fullscreen_action():
                    return next(
                        action
                        for action in variant_list(surface.property("surfaceActions"))
                        if action["id"] == "fullscreen"
                    )

                assert bool(fullscreen_action()["enabled"])
                QMetaObject.invokeMethod(
                    surface,
                    "dispatchSurfaceAction",
                    Q_ARG("QVariant", "fullscreen"),
                )
                app.processEvents()
                assert bridge.toggle_calls == ["node_image_panel_surface_test"]

                surface.setProperty("cropModeActive", True)
                app.processEvents()
                assert not bool(surface.property("overlayPreviewVisible"))
                assert not bool(fullscreen_action()["enabled"])
                QMetaObject.invokeMethod(
                    surface,
                    "dispatchSurfaceAction",
                    Q_ARG("QVariant", "fullscreen"),
                )
                app.processEvents()
                assert bridge.toggle_calls == ["node_image_panel_surface_test"]
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
                        "fit_mode": "contain",
                    }
                )
                payload["render_quality"] = {
                    "supported_quality_tiers": ["full", "proxy"],
                }

                host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": payload,
                        "snapshotReuseActive": True,
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
                    {"nodeData": image_panel_payload({"source_path": "", "fit_mode": "contain"})},
                )
                error_host = create_component(
                    graph_node_host_qml_path,
                    {
                        "nodeData": image_panel_payload(
                            {"source_path": str(missing_path), "fit_mode": "contain"}
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
                            "surface_spec": surface_spec_payload_for_values(
                                type_id="passive.media.pdf_panel",
                                family="media",
                                variant="pdf_panel",
                            ),
                            "visual_style": {},
                            "can_enter_scope": False,
                            "ports": [],
                            "inline_properties": [],
                            "properties": {
                                "source_path": str(pdf_path),
                                "page_number": 1,
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
                assert pdf_surface.findChild(QObject, "graphNodeMediaCropButton") is None
                pdf_action_ids = [
                    action["id"]
                    for action in variant_list(pdf_surface.property("surfaceActions"))
                ]
                assert "crop" not in pdf_action_ids
                assert "rotate_clockwise" not in pdf_action_ids
                assert "mirror_horizontal" not in pdf_action_ids
                assert "mirror_vertical" not in pdf_action_ids
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
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                wait_for_preview(surface)
                surface.setProperty("cropModeActive", True)
                wait_for_condition_or_raise(
                    lambda: len(variant_list(surface.property("embeddedInteractiveRects"))) == 11,
                    timeout_ms=2000,
                    app=app,
                    timeout_message="Timed out waiting for crop interaction rectangles.",
                )

                assert bool(surface.property("blocksHostInteraction"))
                assert len(variant_list(surface.property("embeddedInteractiveRects"))) == 11
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
                                "fit_mode": "contain",
                            }
                        ),
                    },
                )
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                wait_for_preview(surface)
                assert surface is not None
                assert host.findChild(QObject, "graphNodeMediaCropButton") is None

                window = attach_host_to_window(host)

                hover_host_local_point(window, host, 80.0, 44.0)

                crop_action = next(
                    action
                    for action in variant_list(surface.property("surfaceActions"))
                    if action["id"] == "crop"
                )
                assert bool(crop_action["enabled"])
                assert variant_list(surface.property("embeddedInteractiveRects")) == []

                surface.setProperty("cropModeActive", True)
                wait_for_condition_or_raise(
                    lambda: len(variant_list(surface.property("embeddedInteractiveRects"))) == 11,
                    timeout_ms=2000,
                    app=app,
                    timeout_message="Timed out waiting for crop interaction rectangles.",
                )

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

    def test_animated_image_playback_follows_selection_viewport_and_saved_mode(self) -> None:
        self._run_qml_probe(
            "animated-image-playback-policy",
            """
            from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot
            from PyQt6.QtQuick import QQuickItem
            from PyQt6.QtTest import QTest

            from ea_node_editor.ui.media_preview_provider import describe_local_image

            class SceneBridgeStub(QObject):
                selectedNodeLookupChanged = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._selected_node_lookup = {}

                @pyqtProperty("QVariantMap", notify=selectedNodeLookupChanged)
                def selected_node_lookup(self):
                    return dict(self._selected_node_lookup)

                def select_only(self, node_id):
                    self._selected_node_lookup = {str(node_id or ""): True} if node_id else {}
                    self.selectedNodeLookupChanged.emit()

            class AnimationPrefs(QObject):
                imageNodeAutoplayAnimationsChanged = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self._autoplay = True

                @pyqtProperty(bool, notify=imageNodeAutoplayAnimationsChanged)
                def imageNodeAutoplayAnimations(self):
                    return self._autoplay

                def set_autoplay(self, value):
                    self._autoplay = bool(value)
                    self.imageNodeAutoplayAnimationsChanged.emit()

            class ImageCanvasItem(QQuickItem):
                def __init__(self, scene_bridge):
                    super().__init__()
                    self._scene_bridge = scene_bridge
                    self._prefs = AnimationPrefs()

                @pyqtProperty(QObject, constant=True)
                def sceneBridge(self):
                    return self._scene_bridge

                @pyqtProperty(QObject, constant=True)
                def prefs(self):
                    return self._prefs

                @pyqtSlot(str, result="QVariantMap")
                def describeNodeSurfaceImagePreview(self, source):
                    return describe_local_image(str(source or ""))

            fixture = repo_root / "tests" / "fixtures" / "media" / "animated-small.gif"

            def wait_until(predicate, attempts=60):
                for _index in range(attempts):
                    app.processEvents()
                    if predicate():
                        return True
                    QTest.qWait(10)
                return bool(predicate())

            scene_bridge = SceneBridgeStub()
            scene_bridge.select_only("node_image_panel_surface_test")
            canvas_item = ImageCanvasItem(scene_bridge)
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": image_panel_payload(
                        {
                            "source_path": str(fixture),
                            "fit_mode": "contain",
                        }
                    ),
                    "canvasItem": canvas_item,
                    "visibleSceneRectPayload": {"x": 0.0, "y": 0.0, "width": 1000.0, "height": 1000.0},
                },
            )
            surface = host.findChild(QObject, "graphNodeMediaSurface")
            animated_image = host.findChild(QObject, "graphNodeMediaAppliedAnimatedImage")
            assert surface is not None
            assert animated_image is not None

            for _index in range(30):
                app.processEvents()
                QTest.qWait(10)
                if surface.property("animationPlaying"):
                    break

            assert surface.property("previewState") == "ready"
            assert surface.property("animationPlaybackMode") == "auto"
            assert bool(surface.property("imageIsAnimated"))
            assert bool(surface.property("imageAnimationSupported"))
            assert int(surface.property("animationFrameCount")) == 3
            assert bool(host.property("inVisibleViewport"))
            assert bool(surface.property("animationShouldPlay"))
            assert bool(surface.property("animationPlaying"))
            playback_action = next(
                action
                for action in variant_list(surface.property("surfaceActions"))
                if action["id"] == "animationPlayback"
            )
            assert playback_action["icon"] == "run"
            playback_modes = variant_list(playback_action["popoverActions"])
            assert [action["id"] for action in playback_modes] == [
                "animationPlaybackAuto",
                "animationPlaybackPlay",
                "animationPlaybackPause",
            ]
            assert bool(playback_modes[0]["checked"])
            playback_commits = []
            host.inlinePropertyCommitted.connect(
                lambda node_id, key, value: playback_commits.append((node_id, key, value))
            )
            assert bool(surface.dispatchSurfaceAction("animationPlaybackPause"))
            assert playback_commits[-1] == (
                "node_image_panel_surface_test",
                "animation_playback_mode",
                "pause",
            )

            scene_bridge.select_only("")
            assert wait_until(lambda: not bool(surface.property("animationPlaying")))
            assert not bool(surface.property("animationShouldPlay"))
            assert not bool(surface.property("animationPlaying"))
            assert int(surface.property("animationCurrentFrame")) == 0
            assert host.findChild(QObject, "graphNodeMediaAppliedAnimatedImage") is animated_image

            scene_bridge.select_only("node_image_panel_surface_test")
            assert wait_until(lambda: bool(surface.property("animationPlaying")))
            canvas_item.prefs.set_autoplay(False)
            assert wait_until(lambda: not bool(surface.property("animationModePermitsPlayback")))
            assert not bool(surface.property("animationPlaying"))
            assert int(surface.property("animationCurrentFrame")) == 0
            canvas_item.prefs.set_autoplay(True)
            assert wait_until(lambda: bool(surface.property("animationPlaying")))
            host.setProperty(
                "visibleSceneRectPayload",
                {"x": 5000.0, "y": 5000.0, "width": 200.0, "height": 200.0},
            )
            assert wait_until(lambda: not bool(host.property("inVisibleViewport")))
            assert not bool(surface.property("animationShouldPlay"))
            assert not bool(surface.property("animationPlaying"))
            assert int(surface.property("animationCurrentFrame")) == 0
            assert host.findChild(QObject, "graphNodeMediaAppliedAnimatedImage") is animated_image

            host.setProperty(
                "visibleSceneRectPayload",
                {"x": 0.0, "y": 0.0, "width": 1000.0, "height": 1000.0},
            )
            assert wait_until(lambda: bool(host.property("inVisibleViewport")))
            assert wait_until(lambda: bool(surface.property("animationPlaying")))
            assert bool(surface.property("animationShouldPlay"))
            assert host.findChild(QObject, "graphNodeMediaAppliedAnimatedImage") is animated_image

            paused_payload = image_panel_payload(
                {
                    "source_path": str(fixture),
                    "fit_mode": "contain",
                    "animation_playback_mode": "pause",
                }
            )
            paused_payload["node_id"] = "node_image_panel_paused_test"
            scene_bridge.select_only("node_image_panel_paused_test")
            paused_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": paused_payload,
                    "canvasItem": canvas_item,
                    "visibleSceneRectPayload": {"x": 0.0, "y": 0.0, "width": 1000.0, "height": 1000.0},
                },
            )
            paused_surface = paused_host.findChild(QObject, "graphNodeMediaSurface")
            for _index in range(20):
                app.processEvents()
                QTest.qWait(10)
                if paused_surface.property("previewState") == "ready":
                    break
            assert paused_surface.property("animationPlaybackMode") == "pause"
            assert bool(paused_surface.property("imageIsAnimated"))
            assert not bool(paused_surface.property("animationShouldPlay"))
            assert not bool(paused_surface.property("animationPlaying"))
            paused_action = next(
                action
                for action in variant_list(paused_surface.property("surfaceActions"))
                if action["id"] == "animationPlayback"
            )
            paused_modes = variant_list(paused_action["popoverActions"])
            assert paused_action["icon"] == "pause"
            assert bool(paused_modes[2]["checked"])

            canvas_item.prefs.set_autoplay(False)
            play_payload = image_panel_payload(
                {
                    "source_path": str(fixture),
                    "fit_mode": "contain",
                    "animation_playback_mode": "play",
                }
            )
            play_payload["node_id"] = "node_image_panel_play_test"
            scene_bridge.select_only("node_image_panel_play_test")
            play_host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": play_payload,
                    "canvasItem": canvas_item,
                    "visibleSceneRectPayload": {"x": 0.0, "y": 0.0, "width": 1000.0, "height": 1000.0},
                },
            )
            play_surface = play_host.findChild(QObject, "graphNodeMediaSurface")
            for _index in range(30):
                app.processEvents()
                QTest.qWait(10)
                if play_surface.property("animationPlaying"):
                    break
            assert play_surface.property("animationPlaybackMode") == "play"
            assert not bool(play_surface.property("animationAutoplayEnabled"))
            assert bool(play_surface.property("animationModePermitsPlayback"))
            assert bool(play_surface.property("animationPlaying"))
            """,
        )


class LocalMediaPreviewProviderTests(unittest.TestCase):
    def test_describe_local_image_classifies_static_animated_and_corrupt_fixtures(self) -> None:
        fixture_root = Path(__file__).resolve().parent / "fixtures" / "media"

        animated_gif = describe_local_image(str(fixture_root / "animated-small.gif"))
        large_gif = describe_local_image(str(fixture_root / "animated-large.gif"))
        single_frame = describe_local_image(str(fixture_root / "single-frame.gif"))
        animated_webp = describe_local_image(str(fixture_root / "animated.webp"))
        corrupt = describe_local_image(str(fixture_root / "corrupt.gif"))
        missing = describe_local_image(str(fixture_root / "missing.gif"))
        placeholder = describe_local_image("")

        self.assertEqual(animated_gif["state"], "ready")
        self.assertEqual(animated_gif["format"], "gif")
        self.assertEqual(animated_gif["frame_count"], 3)
        self.assertTrue(animated_gif["animation_supported"])
        self.assertTrue(animated_gif["is_animated"])
        self.assertTrue(animated_gif["resolved_source_url"].startswith("file:///"))
        self.assertEqual(
            (animated_gif["source_pixel_width"], animated_gif["source_pixel_height"]),
            (24, 18),
        )

        self.assertEqual(large_gif["frame_count"], 4)
        self.assertEqual(
            (large_gif["source_pixel_width"], large_gif["source_pixel_height"]),
            (1600, 1200),
        )
        self.assertEqual(single_frame["state"], "ready")
        self.assertEqual(single_frame["format"], "gif")
        self.assertEqual(single_frame["frame_count"], 1)
        self.assertFalse(single_frame["is_animated"])

        self.assertEqual(animated_webp["state"], "ready")
        self.assertEqual(animated_webp["format"], "webp")
        self.assertEqual(animated_webp["frame_count"], 3)
        self.assertTrue(animated_webp["animation_supported"])
        self.assertTrue(animated_webp["is_animated"])

        self.assertEqual(corrupt["state"], "error")
        self.assertFalse(corrupt["is_animated"])
        self.assertTrue(corrupt["message"])
        self.assertEqual(missing["state"], "error")
        self.assertEqual(placeholder["state"], "placeholder")

    def test_describe_local_image_resolves_managed_animated_media_to_file_url(self) -> None:
        fixture = Path(__file__).resolve().parent / "fixtures" / "media" / "animated-small.gif"
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "animated-project.cxproj"
            managed_path = (
                project_path.with_name("animated-project.data")
                / "nodes"
                / "Image Panel [11111111]"
                / "in"
                / "media"
                / "managed.gif"
            )
            managed_path.parent.mkdir(parents=True)
            shutil.copyfile(fixture, managed_path)
            set_media_preview_project_context_provider(
                lambda: (
                    project_path,
                    {
                        "artifact_store": {
                            "artifacts": {
                                "managed_animation": {
                                    "relative_path": "nodes/Image Panel [11111111]/in/media/managed.gif"
                                },
                            }
                        }
                    },
                )
            )
            try:
                description = describe_local_image("saved://managed_animation")
            finally:
                set_media_preview_project_context_provider(None)

        self.assertEqual(description["state"], "ready")
        self.assertTrue(description["is_animated"])
        self.assertEqual(description["frame_count"], 3)
        self.assertTrue(description["resolved_source_url"].startswith("file:///"))
        self.assertIn("animated-project.data/nodes/", description["resolved_source_url"])

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
