from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtGui import QImage

from ea_node_editor.nodes.builtins.ansys_dpf_common import DPF_VIEWER_NODE_TYPE_ID
from ea_node_editor.nodes.builtins.passive_media import (
    PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID,
    PASSIVE_MEDIA_PDF_PANEL_TYPE_ID,
)
from ea_node_editor.ui_qml.content_fullscreen_bridge import ContentFullscreenBridge
from tests.main_window_shell.base import MainWindowShellTestBase


def _payload_keys(value) -> list[str]:  # noqa: ANN001
    if isinstance(value, dict):
        keys: list[str] = []
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(_payload_keys(item))
        return keys
    if isinstance(value, list):
        keys = []
        for item in value:
            keys.extend(_payload_keys(item))
        return keys
    return []


class ContentFullscreenBridgeTests(MainWindowShellTestBase):
    def _write_test_image(self, name: str) -> Path:
        path = Path(self._env.temp_path) / name
        image = QImage(32, 20, QImage.Format.Format_ARGB32)
        image.fill(0xFF336699)
        self.assertTrue(image.save(str(path)))
        return path

    def _add_image_node(self, *, name: str = "content-fullscreen-image.png") -> str:
        image_path = self._write_test_image(name)
        node_id = self.window.scene.add_node_from_type(PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID, x=120.0, y=80.0)
        self.window.scene.set_node_properties(
            node_id,
            {
                "source_path": str(image_path),
                "fit_mode": "cover",
                "caption": "Fullscreen caption",
                "crop_x": 0.1,
                "crop_y": 0.2,
                "crop_w": 0.5,
                "crop_h": 0.6,
            },
        )
        self.app.processEvents()
        return node_id

    def _bridge(self) -> ContentFullscreenBridge:
        bridge = self.window.content_fullscreen_bridge
        self.assertIsInstance(bridge, ContentFullscreenBridge)
        return bridge

    def test_content_fullscreen_bridge_opens_image_media_with_preview_contract(self) -> None:
        node_id = self._add_image_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        signal_count = 0

        def _record_change() -> None:
            nonlocal signal_count
            signal_count += 1

        bridge.content_fullscreen_changed.connect(_record_change)

        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertEqual(signal_count, 1)
        self.assertTrue(bridge.open)
        self.assertEqual(bridge.node_id, node_id)
        self.assertEqual(bridge.workspace_id, workspace_id)
        self.assertEqual(bridge.content_kind, "image")
        self.assertEqual(bridge.title, "Image Panel")
        self.assertEqual(bridge.last_error, "")
        self.assertEqual(bridge.viewer_payload, {})

        media_payload = bridge.media_payload
        self.assertEqual(media_payload["media_kind"], "image")
        self.assertEqual(media_payload["workspace_id"], workspace_id)
        self.assertEqual(media_payload["node_id"], node_id)
        self.assertEqual(media_payload["fit_mode"], "cover")
        self.assertEqual(media_payload["caption"], "Fullscreen caption")
        self.assertAlmostEqual(float(media_payload["crop"]["x"]), 0.1)
        self.assertAlmostEqual(float(media_payload["crop"]["y"]), 0.2)
        self.assertAlmostEqual(float(media_payload["crop"]["width"]), 0.5)
        self.assertAlmostEqual(float(media_payload["crop"]["height"]), 0.6)
        self.assertEqual(media_payload["source_pixel_width"], 32)
        self.assertEqual(media_payload["source_pixel_height"], 20)
        self.assertTrue(str(media_payload["resolved_source_url"]).startswith("file:"))
        self.assertTrue(str(media_payload["preview_url"]).startswith("image://local-media-preview/preview?source="))

        previous_signal_count = signal_count
        self.window.scene.set_node_properties(
            node_id,
            {
                "fit_mode": "original",
                "caption": "Updated fullscreen caption",
                "crop_x": 0.0,
                "crop_y": 0.0,
                "crop_w": 1.0,
                "crop_h": 1.0,
            },
        )
        self.app.processEvents()
        media_payload = bridge.media_payload
        self.assertGreater(signal_count, previous_signal_count)
        self.assertEqual(media_payload["fit_mode"], "original")
        self.assertEqual(media_payload["caption"], "Updated fullscreen caption")
        self.assertEqual(media_payload["crop"], {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0})

        node_payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == node_id)
        self.assertNotIn("content_fullscreen", json.dumps(_payload_keys(node_payload)).lower())
        document = self.window.serializer.to_document(self.window.model.project)
        self.assertNotIn("fullscreen", json.dumps(_payload_keys(document)).lower())

    def test_content_fullscreen_bridge_opens_pdf_media_with_page_preview_contract(self) -> None:
        pdf_path = Path(__file__).resolve().parent / "fixtures" / "passive_nodes" / "reference_preview.pdf"
        node_id = self.window.scene.add_node_from_type(PASSIVE_MEDIA_PDF_PANEL_TYPE_ID, x=120.0, y=80.0)
        self.window.scene.set_node_properties(
            node_id,
            {
                "source_path": str(pdf_path),
                "page_number": 1,
                "caption": "PDF caption",
            },
        )
        self.app.processEvents()

        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.content_kind, "pdf")
        media_payload = bridge.media_payload
        self.assertEqual(media_payload["media_kind"], "pdf")
        self.assertEqual(media_payload["fit_mode"], "contain")
        self.assertEqual(media_payload["page_number"], 1)
        self.assertEqual(media_payload["caption"], "PDF caption")
        self.assertEqual(media_payload["pdf_preview"]["state"], "ready")
        self.assertEqual(media_payload["resolved_page_number"], 1)
        self.assertTrue(str(media_payload["preview_url"]).startswith("image://local-pdf-preview/preview?"))

    def test_content_fullscreen_bridge_opens_dpf_viewer_with_session_metadata(self) -> None:
        node_id = self.window.scene.add_node_from_type(DPF_VIEWER_NODE_TYPE_ID, x=120.0, y=80.0)
        self.app.processEvents()

        bridge = self._bridge()
        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.content_kind, "viewer")
        self.assertEqual(bridge.media_payload, {})
        viewer_payload = bridge.viewer_payload
        self.assertEqual(viewer_payload["workspace_id"], self.window.workspace_manager.active_workspace_id())
        self.assertEqual(viewer_payload["node_id"], node_id)
        self.assertEqual(viewer_payload["type_id"], DPF_VIEWER_NODE_TYPE_ID)
        self.assertEqual(viewer_payload["phase"], "closed")
        self.assertIsInstance(viewer_payload["session_state"], dict)
        self.assertIsInstance(viewer_payload["viewer_surface"], dict)

    def test_content_fullscreen_bridge_replaces_and_toggles_single_active_node(self) -> None:
        first_node_id = self._add_image_node(name="content-fullscreen-first.png")
        second_node_id = self._add_image_node(name="content-fullscreen-second.png")
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(first_node_id))
        self.assertEqual(bridge.node_id, first_node_id)

        self.assertTrue(bridge.request_open_node(second_node_id))
        self.assertTrue(bridge.open)
        self.assertEqual(bridge.node_id, second_node_id)

        self.assertTrue(bridge.request_toggle_for_node(second_node_id))
        self.assertFalse(bridge.open)
        self.assertEqual(bridge.node_id, "")
        self.assertEqual(bridge.media_payload, {})

    def test_content_fullscreen_bridge_rejects_ineligible_nodes_and_clears_active_state(self) -> None:
        node_id = self._add_image_node()
        unsupported_node_id = self.window.scene.add_node_from_type("core.start", x=420.0, y=80.0)
        missing_source_node_id = self.window.scene.add_node_from_type(PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID, x=620.0, y=80.0)
        self.app.processEvents()

        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertFalse(bridge.request_open_node(unsupported_node_id))
        self.assertFalse(bridge.open)
        self.assertIn("does not support", bridge.last_error)

        self.assertFalse(bridge.request_open_node(missing_source_node_id))
        self.assertFalse(bridge.open)
        self.assertIn("source path", bridge.last_error)

    def test_content_fullscreen_bridge_closes_on_workspace_switch_and_node_deletion(self) -> None:
        node_id = self._add_image_node()
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        self.window.scene.remove_workspace_node(node_id)
        self.app.processEvents()
        self.assertFalse(bridge.open)

        node_id = self._add_image_node(name="content-fullscreen-before-workspace-switch.png")
        self.assertTrue(bridge.request_open_node(node_id))
        next_workspace_id = self.window.workspace_manager.create_workspace("Fullscreen Other")
        self.window.runtime_history.clear_workspace(next_workspace_id)
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(next_workspace_id)
        self.app.processEvents()

        self.assertFalse(bridge.open)
        self.assertEqual(bridge.node_id, "")
        self.assertEqual(bridge.last_error, "")
