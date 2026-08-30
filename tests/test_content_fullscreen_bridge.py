from __future__ import annotations

import base64
import gc
import hashlib
import json
from pathlib import Path
from typing import Any
from unittest import mock

from PyQt6.QtCore import QObject, QPointF, QMarginsF, QRectF, Qt, QUrl
from PyQt6.QtGui import QImage, QPainter, QPageLayout, QPageSize, QPdfWriter
from PyQt6.QtTest import QTest

from ea_node_editor.runtime_contracts.settled_results import SettledPortResult
from ea_node_editor.runtime_contracts.solution_records import (
    NodeSolutionFact,
    SolutionDisposition,
    SolutionFreshness,
    SolutionResidency,
)
from ea_node_editor.runtime_contracts import DataTree
from ea_node_editor.graph.project_state import ProjectData
from ea_node_editor.nodes.builtins.ansys_dpf_common import DPF_VIEWER_NODE_TYPE_ID
from ea_node_editor.nodes.builtins.core import PYTHON_SCRIPT_DEFAULT_SOURCE
from ea_node_editor.nodes.builtins.ansys_dpf_viewer import DpfViewerNodePlugin
from ea_node_editor.nodes.builtins.engineering_viewer import (
    ENGINEERING_VIEWER_NODE_TYPE_ID,
)
from ea_node_editor.nodes.builtins.excalidraw import (
    EXCALIDRAW_BOARD_TYPE_ID,
    EXCALIDRAW_PREVIEW_REF_PROPERTY,
    EXCALIDRAW_STATE_PROPERTY,
)
from ea_node_editor.nodes.builtins.jupyter_notebook import JUPYTER_NOTEBOOK_TYPE_ID
from ea_node_editor.nodes.builtins.passive_mail import (
    PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID,
)
from ea_node_editor.nodes.builtins.media_panel import MEDIA_PANEL_TYPE_ID
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.builtins.web_viewer import WEB_PAGE_VIEWER_TYPE_ID
from ea_node_editor.addons.tabular_data.input_node import (
    TABULAR_DATA_INPUT_NODE_TYPE_ID,
    TABULAR_SELECTED_COLUMNS_PROPERTY,
    TABULAR_TABLE_VIEW_STATE_PROPERTY,
)
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.ui_qml.content_fullscreen_bridge import ContentFullscreenBridge
from ea_node_editor.ui_qml.graph_scene_payload.fullscreen import build_content_fullscreen_media_payload
from ea_node_editor.web_host.bridge import WebSurfaceBridge
from tests.main_window_shell.base import MainWindowShellTestBase


def _data_url(mime_type: str, payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


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


def test_content_fullscreen_media_payload_supports_mail_preview_url(tmp_path: Path) -> None:
    mail_path = tmp_path / "content-fullscreen-message.eml"
    mail_path.write_text(
        "Subject: Fullscreen Mail\r\n"
        "From: sender@example.com\r\n"
        "To: receiver@example.com\r\n"
        "\r\n"
        "Mail body",
        encoding="utf-8",
    )
    registry = build_default_registry()
    spec = registry.get_spec(PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID)
    node = NodeInstance(
        node_id="mail-fullscreen-node",
        type_id=PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID,
        title="Mail Panel",
        x=10.0,
        y=20.0,
        properties={"source_path": str(mail_path)},
    )

    payload = build_content_fullscreen_media_payload(
        workspace_id="workspace-mail",
        node=node,
        spec=spec,
    )

    assert payload["media_kind"] == "mail"
    assert payload["surface_spec"]["fullscreen"]["content_kind"] == "mail"
    assert payload["preview_state"] == "ready"
    assert str(payload["preview_url"]).startswith("file:")
    assert str(payload["resolved_source_url"]).startswith("file:")
    assert payload["metadata"]["subject"] == "Fullscreen Mail"
    assert payload["attachment_summary"] == "No attachments"


class _VideoTrimPresenterRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def request_trim_video_clip_replace(
        self,
        video_node_id: str,
        start_ms: int,
        end_ms: int,
        state: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append(("replace", (video_node_id, start_ms, end_ms, dict(state))))
        return {
            "success": True,
            "created_node_id": "",
            "created_type_id": MEDIA_PANEL_TYPE_ID,
            "source_ref": "project-staged://fullscreen_replace",
            "error": {},
            "request_id": "fullscreen-replace",
        }

    def request_trim_video_clip_copy(
        self,
        video_node_id: str,
        start_ms: int,
        end_ms: int,
        scene_x: float,
        scene_y: float,
        state: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append(("copy", (video_node_id, start_ms, end_ms, scene_x, scene_y, dict(state))))
        return {
            "success": True,
            "created_node_id": "fullscreen-copy",
            "created_type_id": MEDIA_PANEL_TYPE_ID,
            "source_ref": "project-staged://fullscreen_copy",
            "error": {},
            "request_id": "fullscreen-copy",
        }


class _FakeTabularWorkerPool:
    def __init__(self) -> None:
        self.scheduled: list[tuple[str, object]] = []
        self.shutdown_called = False

    def schedule(self, job_key: str, fn) -> bool:  # noqa: ANN001
        self.scheduled.append((job_key, fn))
        return True

    def shutdown(self) -> None:
        self.shutdown_called = True


class ContentFullscreenBridgeTests(MainWindowShellTestBase):
    def _add_dpf_viewer_node(self) -> str:
        if self.window.registry.spec_or_none(DPF_VIEWER_NODE_TYPE_ID) is None:
            self.window.registry.register(DpfViewerNodePlugin)
        return self.window.scene.add_node_from_type(DPF_VIEWER_NODE_TYPE_ID, x=120.0, y=80.0)

    def _add_engineering_viewer_node(self) -> str:
        return self.window.scene.add_node_from_type(
            ENGINEERING_VIEWER_NODE_TYPE_ID,
            x=120.0,
            y=80.0,
        )

    def _write_test_image(self, name: str) -> Path:
        path = Path(self._env.temp_path) / name
        image = QImage(32, 20, QImage.Format.Format_ARGB32)
        image.fill(0xFF336699)
        self.assertTrue(image.save(str(path)))
        return path

    def _write_test_pdf(self, name: str, *, page_count: int = 1) -> Path:
        path = Path(self._env.temp_path) / name
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
        return path

    def _add_image_node(self, *, name: str = "content-fullscreen-image.png") -> str:
        image_path = self._write_test_image(name)
        node_id = self.window.scene.add_node_from_type(MEDIA_PANEL_TYPE_ID, x=120.0, y=80.0)
        self.window.scene.set_exposed_port(node_id, "source", False)
        self.window.scene.set_node_properties(
            node_id,
            {
                "source": str(image_path),
                "fit_mode": "cover",
                "crop_x": 0.1,
                "crop_y": 0.2,
                "crop_w": 0.5,
                "crop_h": 0.6,
                "rotation_degrees": 90,
                "mirror_horizontal": True,
                "mirror_vertical": False,
            },
        )
        self.app.processEvents()
        return node_id

    def _add_video_node(self, *, name: str = "content-fullscreen-video.mp4") -> str:
        video_path = Path(self._env.temp_path) / name
        video_path.write_bytes(b"not a decoded fixture")
        node_id = self.window.scene.add_node_from_type(MEDIA_PANEL_TYPE_ID, x=120.0, y=80.0)
        self.window.scene.set_exposed_port(node_id, "source", False)
        self.window.scene.set_node_properties(
            node_id,
            {
                "source": str(video_path),
                "fit_mode": "cover",
                "auto_play": True,
                "loop": True,
                "muted": True,
                "volume": 0.4,
                "playback_rate": 1.25,
                "position_ms": 3200,
                "timeline_bookmarks": [{"id": "mark-1", "label": "Mark 1", "position_ms": 3000}],
                "clip_enabled": True,
                "clip_start_ms": 2000,
                "clip_end_ms": 6000,
            },
        )
        self.app.processEvents()
        return node_id

    def _add_pdf_node(
        self,
        *,
        name: str = "content-fullscreen-pages.pdf",
        page_count: int = 3,
        page_number: int = 1,
    ) -> str:
        pdf_path = self._write_test_pdf(name, page_count=page_count)
        node_id = self.window.scene.add_node_from_type(MEDIA_PANEL_TYPE_ID, x=120.0, y=80.0)
        self.window.scene.set_exposed_port(node_id, "source", False)
        self.window.scene.set_node_properties(
            node_id,
            {
                "source": str(pdf_path),
                "page_number": page_number,
            },
        )
        self.app.processEvents()
        return node_id

    def _add_excalidraw_node(self) -> tuple[str, dict, dict]:
        node_id = self.window.scene.add_node_from_type(EXCALIDRAW_BOARD_TYPE_ID, x=160.0, y=120.0)
        state = {
            "type": "excalidraw",
            "elements": [{"id": "rect-1", "type": "rectangle", "isDeleted": False}],
            "appState": {"name": "Fullscreen map"},
            "files": {},
        }
        preview_ref = {
            "uri": "saved://excalidraw-preview",
            "mime_type": "image/png",
            "status": "ready",
        }
        self.window.scene.set_node_properties(
            node_id,
            {
                EXCALIDRAW_STATE_PROPERTY: state,
                EXCALIDRAW_PREVIEW_REF_PROPERTY: preview_ref,
            },
        )
        self.app.processEvents()
        return node_id, state, preview_ref

    def _ensure_tabular_function_registered(self) -> None:
        self.assertIsNotNone(
            self.window.registry.spec_or_none(TABULAR_DATA_INPUT_NODE_TYPE_ID)
        )

    def _add_tabular_node(self) -> tuple[str, Path]:
        self._ensure_tabular_function_registered()
        source = Path(self._env.temp_path) / "content-fullscreen-tabular.csv"
        rows = ["station,temp,count"]
        rows.extend(f"S{index},{20 + index / 10:.1f},{index}" for index in range(120))
        source.write_text("\n".join(rows) + "\n", encoding="utf-8")
        node_id = self.window.scene.add_node_from_type(TABULAR_DATA_INPUT_NODE_TYPE_ID, x=180.0, y=120.0)
        self.window.scene.set_node_properties(
            node_id,
            {
                "path": str(source),
                "delimiter": ",",
                "encoding": "utf-8",
                "header_row": 0,
                "skip_rows": 0,
                "schema_hints": {"temp": "float64", "count": "int64"},
            },
        )
        self.app.processEvents()
        return node_id, source

    def _add_web_page_node(self, **properties) -> str:  # noqa: ANN003
        self.assertIsNotNone(self.window.registry.spec_or_none(WEB_PAGE_VIEWER_TYPE_ID))
        node_id = self.window.scene.add_node_from_type(WEB_PAGE_VIEWER_TYPE_ID, x=220.0, y=120.0)
        if properties:
            self.window.scene.set_node_properties(node_id, properties)
        self.app.processEvents()
        return node_id

    def _add_jupyter_node(self, **properties) -> str:  # noqa: ANN003
        self.assertIsNotNone(self.window.registry.spec_or_none(JUPYTER_NOTEBOOK_TYPE_ID))
        node_id = self.window.scene.add_node_from_type(JUPYTER_NOTEBOOK_TYPE_ID, x=240.0, y=140.0)
        if properties:
            self.window.scene.set_node_properties(node_id, properties)
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
        self.assertEqual(bridge.content_kind, "media")
        self.assertEqual(bridge.title, "Media Panel")
        self.assertEqual(bridge.last_error, "")
        self.assertEqual(bridge.viewer_payload, {})

        media_payload = bridge.media_payload
        self.assertEqual(media_payload["media_kind"], "image")
        self.assertEqual(media_payload["workspace_id"], workspace_id)
        self.assertEqual(media_payload["node_id"], node_id)
        self.assertEqual(media_payload["fit_mode"], "cover")
        self.assertAlmostEqual(float(media_payload["crop"]["x"]), 0.1)
        self.assertAlmostEqual(float(media_payload["crop"]["y"]), 0.2)
        self.assertAlmostEqual(float(media_payload["crop"]["width"]), 0.5)
        self.assertAlmostEqual(float(media_payload["crop"]["height"]), 0.6)
        self.assertEqual(media_payload["rotation_degrees"], 90)
        self.assertTrue(media_payload["mirror_horizontal"])
        self.assertFalse(media_payload["mirror_vertical"])
        self.assertEqual(media_payload["source_pixel_width"], 32)
        self.assertEqual(media_payload["source_pixel_height"], 20)
        self.assertTrue(str(media_payload["resolved_source_url"]).startswith("file:"))
        self.assertTrue(str(media_payload["preview_url"]).startswith("image://local-media-preview/preview?source="))

        previous_signal_count = signal_count
        self.window.scene.set_node_properties(
            node_id,
            {
                "fit_mode": "original",
                "crop_x": 0.0,
                "crop_y": 0.0,
                "crop_w": 1.0,
                "crop_h": 1.0,
                "rotation_degrees": 180,
                "mirror_horizontal": False,
                "mirror_vertical": True,
            },
        )
        self.app.processEvents()
        media_payload = bridge.media_payload
        self.assertGreater(signal_count, previous_signal_count)
        self.assertEqual(media_payload["fit_mode"], "original")
        self.assertEqual(media_payload["crop"], {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0})
        self.assertEqual(media_payload["rotation_degrees"], 180)
        self.assertFalse(media_payload["mirror_horizontal"])
        self.assertTrue(media_payload["mirror_vertical"])

        node_payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == node_id)
        self.assertEqual(node_payload["surface_spec"]["component_key"], "media")
        self.assertEqual(media_payload["surface_spec"]["fullscreen"]["content_kind"], "media")
        self.assertIn("stylus", node_payload["surface_spec"]["input_capabilities"]["devices"])
        self.assertNotIn("content_fullscreen", json.dumps(_payload_keys(node_payload)).lower())
        document = self.window.serializer.to_document(self.window.model.project)
        self.assertNotIn("surface_spec", json.dumps(_payload_keys(document)).lower())
        self.assertNotIn("fullscreen", json.dumps(_payload_keys(document)).lower())

    def test_content_fullscreen_media_refreshes_on_exposure_edge_and_execution(self) -> None:
        node_id = self._add_image_node(name="content-fullscreen-refresh.png")
        workspace_id = self.window.workspace_manager.active_workspace_id()
        image_path = Path(self._env.temp_path) / "content-fullscreen-refresh.png"
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        self.assertEqual(bridge.media_payload["source_state"], "ready")

        self.window.scene.set_exposed_port(node_id, "source", True)
        self.app.processEvents()
        self.assertEqual(bridge.media_payload["source_state"], "waiting")
        self.assertEqual(bridge.media_payload["resolved_source_url"], "")
        self.assertEqual(bridge.media_payload["source_ref"], "")

        source_id = self.window.scene.add_node_from_type(
            "io.path_pointer", x=20.0, y=80.0
        )
        self.window.scene.add_edge(source_id, "path", node_id, "source")
        self.app.processEvents()
        self.assertTrue(bridge.media_payload["input_connected"])
        self.assertEqual(bridge.media_payload["source_state"], "waiting")

        self.window.run_state.cached_node_output_records_by_workspace_id = {
            workspace_id: {
                node_id: {
                    "run-1": {
                        "record_id": "run-1",
                        "observed_at_epoch_ms": 1.0,
                        "outputs": {
                            "_surface_source": SettledPortResult(
                                status="value",
                                value=DataTree.from_item(str(image_path)),
                            )
                        },
                    }
                }
            }
        }
        self.window.run_state.node_solution_facts_by_workspace_id = {
            workspace_id: {
                node_id: NodeSolutionFact(
                    project_id=self.window.model.project.project_id,
                    workspace_id=workspace_id,
                    node_id=node_id,
                    freshness=SolutionFreshness.CURRENT,
                    revision=1,
                    retained_record_id="run-1",
                    retained_solution_key="a" * 64,
                    residency=SolutionResidency.SESSION,
                    last_disposition=SolutionDisposition.RECOMPUTED,
                )
            }
        }
        self.window.run_state.node_execution_workspace_id = workspace_id
        self.window.run_state.completed_node_ids.add(node_id)
        self.window.node_execution_state_changed.emit()
        self.app.processEvents()

        self.assertEqual(bridge.media_payload["source_state"], "ready")
        self.assertEqual(bridge.media_payload["authority"], "input")
        self.assertEqual(bridge.media_payload["source_ref"], str(image_path))

        self.window.run_state.completed_node_ids.discard(node_id)
        self.window.run_state.running_node_ids.add(node_id)
        self.window.node_execution_state_changed.emit()
        self.app.processEvents()
        self.assertEqual(bridge.media_payload["source_state"], "running")
        self.assertEqual(bridge.media_payload["resolved_source_url"], "")

    def test_content_fullscreen_bridge_exposes_animated_image_runtime_metadata(self) -> None:
        image_path = Path(__file__).resolve().parent / "fixtures" / "media" / "animated-small.gif"
        node_id = self.window.scene.add_node_from_type(MEDIA_PANEL_TYPE_ID, x=120.0, y=80.0)
        self.window.scene.set_exposed_port(node_id, "source", False)
        self.window.scene.set_node_properties(
            node_id,
            {
                "source": str(image_path),
                "fit_mode": "contain",
                "animation_playback_mode": "pause",
            },
        )
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        media_payload = bridge.media_payload

        self.assertEqual(media_payload["preview_state"], "ready")
        self.assertEqual(media_payload["format"], "gif")
        self.assertEqual(media_payload["frame_count"], 3)
        self.assertTrue(media_payload["animation_supported"])
        self.assertTrue(media_payload["is_animated"])
        self.assertEqual(
            (media_payload["source_pixel_width"], media_payload["source_pixel_height"]),
            (24, 18),
        )
        resolved_path = Path(QUrl(media_payload["resolved_source_url"]).toLocalFile())
        self.assertEqual(resolved_path, image_path)

    def test_content_fullscreen_bridge_opens_pdf_media_with_page_preview_contract(self) -> None:
        pdf_path = Path(__file__).resolve().parent / "fixtures" / "passive_nodes" / "reference_preview.pdf"
        node_id = self.window.scene.add_node_from_type(MEDIA_PANEL_TYPE_ID, x=120.0, y=80.0)
        self.window.scene.set_exposed_port(node_id, "source", False)
        self.window.scene.set_node_properties(
            node_id,
            {
                "source": str(pdf_path),
                "page_number": 1,
            },
        )
        self.app.processEvents()

        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.content_kind, "media")
        media_payload = bridge.media_payload
        self.assertEqual(media_payload["media_kind"], "pdf")
        self.assertEqual(media_payload["surface_spec"]["fullscreen"]["content_kind"], "media")
        self.assertEqual(media_payload["fit_mode"], "contain")
        self.assertEqual(media_payload["page_number"], 1)
        self.assertEqual(media_payload["pdf_preview"]["state"], "ready")
        self.assertEqual(media_payload["resolved_page_number"], 1)
        self.assertTrue(str(media_payload["preview_url"]).startswith("image://local-pdf-preview/preview?"))

    def test_content_fullscreen_bridge_navigates_pdf_pages(self) -> None:
        node_id = self._add_pdf_node(page_count=3, page_number=1)
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertEqual(bridge.content_kind, "media")
        self.assertEqual(bridge.media_payload["pdf_preview"]["page_count"], 3)
        self.assertEqual(bridge.media_payload["resolved_page_number"], 1)

        self.assertTrue(bridge.request_pdf_page_delta(-1))
        self.assertEqual(bridge.media_payload["resolved_page_number"], 1)

        self.assertTrue(bridge.request_pdf_page_delta(1))
        self.assertEqual(bridge.media_payload["page_number"], 2)
        self.assertEqual(bridge.media_payload["resolved_page_number"], 2)

        self.assertTrue(bridge.request_pdf_page_number(99))
        self.assertEqual(bridge.media_payload["page_number"], 3)
        self.assertEqual(bridge.media_payload["resolved_page_number"], 3)

        self.assertTrue(bridge.request_pdf_page_delta(1))
        self.assertEqual(bridge.media_payload["resolved_page_number"], 3)

        self.assertTrue(bridge.request_pdf_page_number(0))
        self.assertEqual(bridge.media_payload["page_number"], 1)
        self.assertEqual(bridge.media_payload["resolved_page_number"], 1)

    def test_content_fullscreen_bridge_opens_video_media_with_playback_contract(self) -> None:
        node_id = self._add_video_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.node_id, node_id)
        self.assertEqual(bridge.workspace_id, workspace_id)
        self.assertEqual(bridge.content_kind, "media")
        media_payload = bridge.media_payload
        self.assertEqual(media_payload["media_kind"], "video")
        self.assertEqual(media_payload["surface_spec"]["fullscreen"]["content_kind"], "media")
        self.assertEqual(media_payload["fit_mode"], "cover")
        self.assertTrue(media_payload["auto_play"])
        self.assertTrue(media_payload["loop"])
        self.assertTrue(media_payload["muted"])
        self.assertEqual(media_payload["volume"], 0.4)
        self.assertEqual(media_payload["playback_rate"], 1.25)
        self.assertEqual(media_payload["position_ms"], 3200)
        self.assertEqual(
            media_payload["timeline_bookmarks"],
            [{"id": "mark-1", "label": "Mark 1", "position_ms": 3000}],
        )
        self.assertTrue(media_payload["clip_enabled"])
        self.assertEqual(media_payload["clip_start_ms"], 2000)
        self.assertEqual(media_payload["clip_end_ms"], 6000)
        self.assertTrue(str(media_payload["resolved_source_url"]).startswith("file:"))
        self.assertEqual(media_payload["preview_url"], "")

    def test_content_fullscreen_bridge_forwards_video_trim_requests(self) -> None:
        node_id = self._add_video_node()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))

        recorder = _VideoTrimPresenterRecorder()
        original_presenter = self.window.graph_canvas_presenter
        self.window.graph_canvas_presenter = recorder
        try:
            replace_result = bridge.request_trim_video_clip_replace(
                {
                    "position_ms": 3400,
                    "playing": True,
                    "muted": True,
                    "volume": 0.25,
                    "playback_rate": 1.5,
                    "loop": True,
                    "fit_mode": "cover",
                    "timeline_bookmarks": [
                        {"id": "in", "label": "In", "position_ms": 2500},
                    ],
                    "clip_enabled": True,
                    "clip_start_ms": 2500,
                    "clip_end_ms": 5500,
                }
            )
            copy_result = bridge.request_trim_video_clip_copy(
                {
                    "clip_enabled": True,
                    "clip_start_ms": 2500,
                    "clip_end_ms": 5500,
                    "timeline_bookmarks": [
                        {"id": "out", "label": "Out", "position_ms": 5000},
                    ],
                }
            )
        finally:
            self.window.graph_canvas_presenter = original_presenter

        self.assertEqual(replace_result["request_id"], "fullscreen-replace")
        self.assertEqual(copy_result["created_node_id"], "fullscreen-copy")
        self.assertEqual(recorder.calls[0][0], "replace")
        self.assertEqual(recorder.calls[0][1][0:3], (node_id, 2500, 5500))
        replace_state = recorder.calls[0][1][3]
        self.assertEqual(replace_state["position_ms"], 3400)
        self.assertEqual(replace_state["timeline_bookmarks"], [{"id": "in", "label": "In", "position_ms": 2500}])
        self.assertEqual(recorder.calls[1][0], "copy")
        self.assertEqual(recorder.calls[1][1][0:5], (node_id, 2500, 5500, 0.0, 0.0))
        copy_state = recorder.calls[1][1][5]
        self.assertEqual(copy_state["timeline_bookmarks"], [{"id": "out", "label": "Out", "position_ms": 5000}])

        self.window.graph_canvas_presenter = object()
        try:
            missing_presenter = bridge.request_trim_video_clip_replace({})
        finally:
            self.window.graph_canvas_presenter = original_presenter
        self.assertEqual(
            missing_presenter["error"]["message"],
            "Graph canvas presenter cannot trim Media Panel video clips.",
        )

        bridge.request_close()
        unavailable = bridge.request_trim_video_clip_copy({})
        self.assertEqual(
            unavailable["error"]["message"],
            "No fullscreen Media Panel in video mode is active.",
        )

    def test_content_fullscreen_bridge_opens_managed_video_media_source(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-managed-video.cxproj"
        self.window.project_path = str(project_path)
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type(MEDIA_PANEL_TYPE_ID, x=120.0, y=80.0)
        self.window.scene.set_exposed_port(node_id, "source", False)

        staging_root = self.window.project_session_controller.ensure_project_staging_root()
        store = self.window.project_session_controller.project_artifact_store()
        paths = store.node_artifact_paths(
            artifact_id="managed_video",
            workspace_id=workspace_id,
            node_id=node_id,
            node_title="Video Panel",
            node_type="Video Panel",
            io_dir="in",
            subdirectory="media",
            filename="managed-video.mp4",
        )
        staged_path = staging_root.joinpath(*Path(paths.staged_relative_path).parts)
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.write_bytes(b"managed video fixture")
        store.register_staged_entry("managed_video", relative_path=paths.staged_relative_path, extra=paths.metadata)
        self.window.model.project.metadata = {
            **dict(self.window.model.project.metadata),
            "artifact_store": store.metadata,
        }
        self.window.scene.set_node_properties(
            node_id,
            {
                "source": store.staged_ref("managed_video"),
                "fit_mode": "contain",
            },
        )
        self.app.processEvents()

        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        media_payload = bridge.media_payload
        self.assertEqual(media_payload["media_kind"], "video")
        self.assertEqual(Path(QUrl(media_payload["resolved_source_url"]).toLocalFile()), staged_path)
        self.assertEqual(media_payload["source_ref"], store.staged_ref("managed_video"))

    def test_content_fullscreen_bridge_accepts_video_remote_source(self) -> None:
        node_id = self.window.scene.add_node_from_type(MEDIA_PANEL_TYPE_ID, x=120.0, y=80.0)
        self.window.scene.set_exposed_port(node_id, "source", False)
        self.window.scene.set_node_properties(
            node_id,
            {
                "source": "https://example.com/video.mp4",
                "fit_mode": "contain",
            },
        )
        self.app.processEvents()
        bridge = self._bridge()

        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))
        self.assertTrue(bridge.open)
        self.assertEqual(bridge.content_kind, "media")
        self.assertEqual(bridge.media_payload["media_kind"], "video")
        self.assertEqual(
            bridge.media_payload["resolved_source_url"],
            "https://example.com/video.mp4",
        )

    def test_content_fullscreen_bridge_hands_off_video_state_and_persists_close_state(self) -> None:
        node_id = self._add_video_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        close_events: list[tuple[str, dict]] = []
        bridge.video_fullscreen_closed.connect(lambda closed_node_id, state: close_events.append((closed_node_id, state)))

        self.assertTrue(
            bridge.request_open_node_with_state(
                node_id,
                {
                    "position_ms": 9000,
                    "playing": True,
                    "muted": False,
                    "volume": 0.75,
                    "playback_rate": 1.5,
                    "loop": False,
                    "fit_mode": "contain",
                    "timeline_bookmarks": [
                        {"id": "intro", "label": "Intro", "position_ms": 1000},
                    ],
                    "clip_enabled": True,
                    "clip_start_ms": 1000,
                    "clip_end_ms": 8000,
                },
            )
        )

        media_payload = bridge.media_payload
        self.assertEqual(media_payload["transient_state"]["position_ms"], 9000)
        self.assertTrue(media_payload["transient_state"]["playing"])
        self.assertEqual(media_payload["transient_state"]["volume"], 0.75)
        self.assertEqual(media_payload["transient_state"]["playback_rate"], 1.5)
        self.assertEqual(
            media_payload["transient_state"]["timeline_bookmarks"],
            [{"id": "intro", "label": "Intro", "position_ms": 1000}],
        )
        self.assertTrue(media_payload["transient_state"]["clip_enabled"])
        self.assertEqual(media_payload["transient_state"]["clip_start_ms"], 1000)
        self.assertEqual(media_payload["transient_state"]["clip_end_ms"], 8000)

        self.assertTrue(
            bridge.request_close_with_state(
                {
                    "position_ms": 12345,
                    "playing": True,
                    "muted": True,
                    "volume": 0.2,
                    "playback_rate": 2.0,
                    "loop": True,
                    "fit_mode": "cover",
                    "timeline_bookmarks": [
                        {"id": "clip-start", "label": "Clip start", "position_ms": 12000},
                    ],
                    "clip_enabled": True,
                    "clip_start_ms": 12000,
                    "clip_end_ms": 15000,
                }
            )
        )

        self.assertFalse(bridge.open)
        self.assertEqual(bridge.media_payload, {})
        workspace = self.window.model.project.workspaces[workspace_id]
        node = workspace.nodes[node_id]
        self.assertEqual(node.properties["position_ms"], 12345)
        self.assertEqual(node.properties["playback_rate"], 2.0)
        self.assertEqual(node.properties["volume"], 0.2)
        self.assertTrue(node.properties["muted"])
        self.assertTrue(node.properties["loop"])
        self.assertEqual(node.properties["fit_mode"], "cover")
        self.assertEqual(
            node.properties["timeline_bookmarks"],
            [{"id": "clip-start", "label": "Clip start", "position_ms": 12000}],
        )
        self.assertTrue(node.properties["clip_enabled"])
        self.assertEqual(node.properties["clip_start_ms"], 12000)
        self.assertEqual(node.properties["clip_end_ms"], 15000)
        self.assertEqual(close_events, [(node_id, {
            "position_ms": 12345,
            "playing": True,
            "muted": True,
            "volume": 0.2,
            "playback_rate": 2.0,
            "loop": True,
            "fit_mode": "cover",
            "timeline_bookmarks": [{"id": "clip-start", "label": "Clip start", "position_ms": 12000}],
            "clip_enabled": True,
            "clip_start_ms": 12000,
            "clip_end_ms": 15000,
        })])

    def test_content_fullscreen_bridge_opens_dpf_viewer_with_session_metadata(self) -> None:
        node_id = self._add_dpf_viewer_node()
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
        self.assertEqual(viewer_payload["surface_spec"]["component_key"], "viewer")
        self.assertTrue(viewer_payload["surface_spec"]["native_overlay"]["required"])
        self.assertIn("viewer.pluginGesture", viewer_payload["surface_spec"]["input_capabilities"]["plugin_gestures"])
        self.assertEqual(viewer_payload["phase"], "closed")
        self.assertIsInstance(viewer_payload["session_state"], dict)
        self.assertIsInstance(viewer_payload["viewer_surface"], dict)

    def test_viewer_fullscreen_target_owns_presentation_hold_until_close(self) -> None:
        node_id = self._add_dpf_viewer_node()
        self.app.processEvents()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        key = (workspace_id, node_id)
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        self.app.processEvents()

        self.assertEqual(self.window.viewer_host_service._fullscreen_hold_key, key)
        self.assertIn(key, self.window.viewer_session_bridge._viewer_presentation_holds)

        self.window.scene.clear_selection()
        self.app.processEvents()
        self.assertIn(key, self.window.viewer_session_bridge._viewer_presentation_holds)

        bridge.request_close()
        self.app.processEvents()

        self.assertIsNone(self.window.viewer_host_service._fullscreen_hold_key)
        self.assertNotIn(key, self.window.viewer_session_bridge._viewer_presentation_holds)

    def test_viewer_host_reset_releases_fullscreen_presentation_hold(self) -> None:
        node_id = self._add_dpf_viewer_node()
        self.app.processEvents()
        key = (self.window.workspace_manager.active_workspace_id(), node_id)
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        self.app.processEvents()
        self.assertIn(key, self.window.viewer_session_bridge._viewer_presentation_holds)

        self.window.viewer_host_service.reset(reason="test_reset")

        self.assertIsNone(self.window.viewer_host_service._fullscreen_hold_key)
        self.assertNotIn(key, self.window.viewer_session_bridge._viewer_presentation_holds)

    def test_viewer_control_bridge_sets_node_scoped_view_options(self) -> None:
        node_id = self._add_dpf_viewer_node()
        self.app.processEvents()

        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        self.assertEqual(bridge.content_kind, "viewer")

        control = self.window.viewer_control_bridge
        change_signals: list[str] = []
        control.viewer_control_changed.connect(change_signals.append)

        sync_calls: list[tuple[Any, ...]] = []
        session_bridge = self.window.viewer_session_bridge
        original_sync = session_bridge.sync_node_property_option
        session_bridge.sync_node_property_option = (  # type: ignore[method-assign]
            lambda *args, **kwargs: sync_calls.append(args) or True
        )
        try:
            self.assertTrue(control.set_viewer_option(node_id, "colormap", "turbo"))
        finally:
            session_bridge.sync_node_property_option = original_sync  # type: ignore[method-assign]

        workspace_id = self.window.workspace_manager.active_workspace_id()

        def node_properties() -> dict[str, Any]:
            return dict(self.window.model.project.workspaces[workspace_id].nodes[node_id].properties)

        self.assertEqual(node_properties()["colormap"], "turbo")
        self.assertGreaterEqual(len(change_signals), 1)
        self.assertEqual(len(sync_calls), 1)
        self.assertEqual(sync_calls[0][0], node_id)
        self.assertEqual(sync_calls[0][1], "colormap")
        self.assertEqual(sync_calls[0][2], "turbo")

        self.assertTrue(control.set_viewer_option(node_id, "show_scalar_bar", "false"))
        self.assertIs(node_properties()["show_scalar_bar"], False)

        self.assertTrue(control.set_viewer_option(node_id, "deform_scale", "-3"))
        self.assertEqual(node_properties()["deform_scale"], "off")

        self.assertFalse(control.set_viewer_option(node_id, "path", "C:/other.rst"))
        self.assertFalse(control.set_viewer_option(node_id, "unknown_key", 1))

        bridge.request_close()
        self.assertTrue(control.set_viewer_option(node_id, "colormap", "jet"))

    def test_viewer_control_bridge_manages_viewer_camera_bookmarks(self) -> None:
        node_id = self._add_engineering_viewer_node()
        self.app.processEvents()

        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        self.assertEqual(bridge.content_kind, "viewer")

        host_service = self.window.viewer_host_service
        original_snapshot = host_service.camera_state_snapshot
        original_apply = host_service.apply_overlay_camera_state
        applied: list[tuple[str, dict[str, Any]]] = []
        host_service.camera_state_snapshot = lambda _node_id: {"zoom": 3.0}  # type: ignore[method-assign]
        host_service.apply_overlay_camera_state = (  # type: ignore[method-assign]
            lambda applied_node_id, state: applied.append((applied_node_id, dict(state))) or True
        )
        try:
            control = self.window.viewer_control_bridge
            self.assertEqual(control.viewer_camera_bookmarks(node_id), [])
            self.assertTrue(control.save_viewer_camera_bookmark(node_id, "Front"))
            bookmarks = control.viewer_camera_bookmarks(node_id)
            self.assertEqual(len(bookmarks), 1)
            self.assertEqual(bookmarks[0]["name"], "Front")
            expected_camera_state = {
                "zoom": 3.0,
                "clip_enabled": False,
                "clip_axis": "x",
                "clip_offset": 0.0,
            }
            self.assertEqual(bookmarks[0]["camera_state"], expected_camera_state)

            workspace_id = self.window.workspace_manager.active_workspace_id()
            stored = self.window.model.project.workspaces[workspace_id].nodes[node_id].properties[
                "camera_bookmarks"
            ]
            self.assertEqual(len(stored), 1)

            self.assertTrue(control.apply_viewer_camera_bookmark(node_id, 0))
            self.assertEqual(applied, [(node_id, expected_camera_state)])
            self.assertFalse(control.apply_viewer_camera_bookmark(node_id, 5))

            self.assertTrue(control.remove_viewer_camera_bookmark(node_id, 0))
            self.assertEqual(control.viewer_camera_bookmarks(node_id), [])
            self.assertFalse(control.remove_viewer_camera_bookmark(node_id, 0))
        finally:
            host_service.camera_state_snapshot = original_snapshot  # type: ignore[method-assign]
            host_service.apply_overlay_camera_state = original_apply  # type: ignore[method-assign]

    def test_engineering_viewer_options_and_saved_selection_are_explicit(self) -> None:
        node_id = self._add_engineering_viewer_node()
        self.app.processEvents()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        control = self.window.viewer_control_bridge

        self.assertTrue(control.set_viewer_option(node_id, "representation", "wireframe"))
        self.assertTrue(control.set_viewer_option(node_id, "primary_opacity", "1.5"))
        self.assertTrue(control.set_viewer_option(node_id, "overlay_opacity", "0.2"))
        self.assertTrue(control.set_viewer_option(node_id, "parallel_projection", True))

        workspace_id = self.window.workspace_manager.active_workspace_id()
        properties = self.window.model.project.workspaces[workspace_id].nodes[node_id].properties
        self.assertEqual(properties["representation"], "wireframe")
        self.assertEqual(properties["primary_opacity"], 1.0)
        self.assertEqual(properties["overlay_opacity"], 0.2)
        self.assertIs(properties["parallel_projection"], True)

        host_service = self.window.viewer_host_service
        original_snapshot = host_service.viewer_selection_snapshot
        original_activate = host_service.activate_viewer_selection
        source_fingerprint = "a" * 64
        selected_entities = [
            {
                "layer_id": "primary",
                "source_fingerprint": source_fingerprint,
                "entity_kind": "cad_face",
                "entity_id": f"part:1/face:{value}",
            }
            for value in (9, 2)
        ]
        activated: list[tuple[str, list[dict[str, str]]]] = []
        host_service.viewer_selection_snapshot = lambda _node_id: {  # type: ignore[method-assign]
            "scene_fingerprint": source_fingerprint,
            "entities": selected_entities,
        }
        host_service.activate_viewer_selection = (  # type: ignore[method-assign]
            lambda selected_node_id, entities: activated.append(
                (selected_node_id, [dict(entity) for entity in entities])
            )
            or True
        )
        try:
            self.assertTrue(control.save_current_viewer_selection(node_id, "Critical faces"))
            saved = control.viewer_saved_selections(node_id)
            self.assertEqual(saved["published_name"], "")
            saved_entities = saved["selections"][0]["entities"]
            self.assertEqual(
                [entity["entity_id"] for entity in saved_entities],
                ["part:1/face:2", "part:1/face:9"],
            )
            self.assertTrue(control.rename_viewer_selection(node_id, 0, "Bolt region"))
            self.assertTrue(control.activate_viewer_selection(node_id, 0))
            self.assertEqual(activated, [(node_id, saved_entities)])
            self.assertTrue(control.publish_viewer_selection(node_id, 0))
            self.assertEqual(control.viewer_saved_selections(node_id)["published_name"], "Bolt region")
            self.assertTrue(control.remove_viewer_selection(node_id, 0))
            self.assertEqual(control.viewer_saved_selections(node_id)["selections"], [])
        finally:
            host_service.viewer_selection_snapshot = original_snapshot  # type: ignore[method-assign]
            host_service.activate_viewer_selection = original_activate  # type: ignore[method-assign]

        self.assertTrue(control.viewer_query_available())
        unavailable = control.query_viewer(node_id, "bounds", {})
        self.assertFalse(unavailable["supported"])
        self.assertIn("not ready", unavailable["explanation"])

    def test_input_reference_documents_viewer_fullscreen_shortcuts(self) -> None:
        from ea_node_editor.ui.dialogs.input_reference_dialog import iter_input_reference_entries

        viewer_entries = {
            entry.input: entry.action
            for entry in iter_input_reference_entries()
            if entry.context == "DPF viewer fullscreen"
        }
        self.assertIn("Space", viewer_entries)
        self.assertIn("Left or Right", viewer_entries)
        self.assertIn("Home", viewer_entries)
        self.assertIn("R", viewer_entries)

    def test_shared_viewer_controls_keep_group_order_overflow_and_saved_view_shortcuts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        controls = (
            repo_root
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "viewer"
            / "ViewerQuickControls.qml"
        ).read_text(encoding="utf-8")
        selection_controls = (
            repo_root
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "viewer"
            / "ViewerSelectionControls.qml"
        ).read_text(encoding="utf-8")
        viewer_tool_button = (
            repo_root
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph"
            / "viewer"
            / "ViewerToolButton.qml"
        ).read_text(encoding="utf-8")
        overlay = (repo_root / "ea_node_editor" / "ui_qml" / "ContentFullscreenOverlay.qml").read_text(
            encoding="utf-8"
        )

        self.assertIn('objectName: "viewerQuickControlsFlickable"', controls)
        self.assertIn('objectName: "viewerQuickControlsLeftChevron"', controls)
        self.assertIn('objectName: "viewerQuickControlsRightChevron"', controls)
        positions = [controls.index(f'text: "{label}"') for label in ("Render mode", "View", "Camera", "Docking")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('objectName: "viewerSavedViewsPopup"', controls)
        self.assertIn("cycle_viewer_camera_bookmark", controls)
        self.assertIn("viewer_camera_bookmark_current_index", controls)
        self.assertIn("property int currentBookmarkIndex: -1", controls)
        self.assertIn("selectedStyle: quickControls.currentBookmarkIndex === index", controls)
        self.assertIn('iconName: "viewer-wireframe"', controls)
        self.assertIn('"viewer-orthographic"', controls)
        self.assertIn('id: renderModeSegments', controls)
        self.assertIn('objectName: "viewerProjectionButton"', controls)
        self.assertIn('iconName: "viewer-fit-selection"', controls)
        self.assertIn('iconName: "viewer-saved-views"', controls)
        self.assertIn('iconName: "viewer-fullscreen"', controls)
        saved_view_positions = [
            controls.index('objectName: "viewerSaveCurrentViewButton"'),
            controls.index("id: savedViewsColumn"),
            controls.index('objectName: "viewerNextSavedViewButton"'),
            controls.index('objectName: "viewerPreviousSavedViewButton"'),
        ]
        self.assertEqual(saved_view_positions, sorted(saved_view_positions))
        self.assertIn("readonly property bool isolateActive: Boolean(selectionSnapshot.isolate_active)", controls)
        self.assertIn("selectedStyle: quickControls.isolateActive", controls)
        self.assertIn("selectionSnapshot.entities", controls)
        self.assertNotIn("selection.entity_ids", controls)
        self.assertIn("Math.min(350, quickControls.width - 16)", controls)
        self.assertIn("themePalette.panel_bg", controls)
        self.assertNotIn("component DisabledHint", controls)
        self.assertIn("Qt.Key_PageUp", overlay)
        self.assertIn("Qt.Key_PageDown", overlay)
        self.assertIn("ViewerComponents.ViewerSelectionControls", overlay)
        self.assertIn('objectName: "viewerSelectionControlsFlickable"', selection_controls)
        self.assertIn('objectName: "viewerSelectionControlsLeftChevron"', selection_controls)
        self.assertIn('objectName: "viewerSelectionControlsRightChevron"', selection_controls)
        for value in (
            "cad_vertex",
            "cad_edge",
            "cad_face",
            "cad_body",
            "fe_node",
            "fe_element_face",
            "fe_element",
        ):
            self.assertIn(f'filterValue: "{value}"', selection_controls)
        self.assertIn("selectionSnapshot.selection_filter", selection_controls)
        self.assertIn("hostServiceRef.set_viewer_selection_filter(nodeId, value)", selection_controls)
        self.assertNotIn('setViewerOption("selection_filter"', selection_controls)
        self.assertIn("entry.available", selection_controls)
        self.assertIn("entry.unsupported_reason", selection_controls)
        self.assertIn("viewer_tangent_selection_angle_degrees()", selection_controls)
        self.assertIn("set_viewer_tangent_selection_angle_degrees", selection_controls)
        self.assertIn("onViewerTangentSelectionAngleChanged", selection_controls)
        self.assertNotIn('setViewerOption("tangent_selection_angle_degrees"', selection_controls)
        self.assertIn('"\\u00B0"', selection_controls)
        self.assertNotIn("Â°", selection_controls)
        self.assertIn("from: 0", selection_controls)
        self.assertIn("to: 90", selection_controls)
        self.assertIn("enabled: root.actionEnabled", viewer_tool_button)
        self.assertIn("HoverHandler", viewer_tool_button)
        self.assertIn("Accessible.checkable: root.checkable", viewer_tool_button)
        self.assertIn("tooltipCategory: root.tooltipCategory", viewer_tool_button)
        self.assertIn("property int buttonHeight: 34", viewer_tool_button)
        self.assertIn('spacing: root.contentKind === "viewer" ? 0 : 8', overlay)

    def test_engineering_viewer_quick_controls_runtime_states_and_overflow(self) -> None:
        node_id = self._add_engineering_viewer_node()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        self.app.processEvents()

        root = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root)
        controls = root.findChild(QObject, "viewerQuickControls")
        self.assertIsNotNone(controls)
        controls.setProperty(
            "sessionState",
            {
                "phase": "open",
                "options": {
                    "representation": "surface",
                    "parallel_projection": False,
                    "show_mesh_edges": False,
                    "show_attribute_colors": False,
                },
                "summary": {
                    "viewer_kind": "engineering_scene",
                    "capabilities": {
                        "playback": False,
                        "supported_render_modes": [
                            "wireframe",
                            "wireframe_visible_edges",
                            "surface",
                            "surface_with_edges",
                        ],
                        "wireframe_visible_edges": True,
                        "topological_edges": True,
                        "mesh_edges": {"available": False, "reason": "No mesh layer."},
                        "attribute_colors": {"available": False, "reason": "No source colors."},
                        "projection": True,
                    },
                },
            },
        )
        controls.setProperty("width", 320.0)
        self.app.processEvents()

        names = (
            "viewerRenderWireframeButton",
            "viewerFitAllButton",
            "viewerProjectionButton",
            "viewerDetachDockButton",
        )
        items = [controls.findChild(QObject, name) for name in names]
        self.assertTrue(all(item is not None for item in items))
        positions = [item.mapToItem(controls, QPointF()).x() for item in items]
        self.assertEqual(positions, sorted(positions))

        shaded = controls.findChild(QObject, "viewerRenderShadedButton")
        mesh_edges = controls.findChild(QObject, "viewerRenderMeshEdgesButton")
        right_chevron = controls.findChild(QObject, "viewerQuickControlsRightChevron")
        flickable = controls.findChild(QObject, "viewerQuickControlsFlickable")
        self.assertTrue(bool(shaded.property("selectedStyle")))
        self.assertEqual(shaded.property("accessibleName"), "Shaded")
        self.assertFalse(bool(mesh_edges.property("actionEnabled")))
        self.assertEqual(mesh_edges.property("accessibleName"), "Show mesh or facet edges")
        self.assertGreater(float(flickable.property("contentWidth")), float(flickable.property("width")))
        self.assertTrue(bool(right_chevron.property("visible")))
        self.assertEqual(int(shaded.property("buttonHeight")), 34)

    def test_content_fullscreen_bridge_opens_python_script_editor_and_retargets_model(self) -> None:
        node_id = self.window.scene.add_node_from_type("core.python_script", x=120.0, y=80.0)
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        workspace.nodes[node_id].properties["script"] = PYTHON_SCRIPT_DEFAULT_SOURCE
        self.app.processEvents()

        bridge = self._bridge()
        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.node_id, node_id)
        self.assertEqual(bridge.workspace_id, workspace_id)
        self.assertEqual(bridge.content_kind, "script_editor")
        self.assertEqual(bridge.media_payload, {})
        self.assertEqual(bridge.viewer_payload, {})
        self.assertEqual(bridge.web_editor_payload, {})
        self.assertEqual(bridge.tabular_payload, {})
        self.assertEqual(self.window.script_editor.current_node_id, node_id)
        self.assertEqual(self.window.script_editor.script_text, PYTHON_SCRIPT_DEFAULT_SOURCE)

    def test_content_fullscreen_script_editor_attaches_syntax_highlighter(self) -> None:
        node_id = self.window.scene.add_node_from_type(
            "core.python_script", x=240.0, y=140.0
        )
        existing_documents = set(self.window.script_highlighter._highlighters)

        self.assertTrue(self.window.content_fullscreen_bridge.request_open_node(node_id))
        self.app.processEvents()

        new_documents = set(self.window.script_highlighter._highlighters) - existing_documents
        self.assertEqual(len(new_documents), 1)
        document, highlighter = self.window.script_highlighter._highlighters[
            new_documents.pop()
        ]
        highlighter.rehighlight()
        colors = {
            color_range.format.foreground().color().name()
            for block_number in range(document.blockCount())
            for color_range in document.findBlockByNumber(block_number).layout().formats()
        }
        self.assertIn("#68a5ff", colors)

    def test_content_fullscreen_script_editor_tab_and_history_stay_local(self) -> None:
        node_id = self.window.scene.add_node_from_type(
            "core.python_script", x=240.0, y=140.0
        )
        self.assertTrue(self.window.content_fullscreen_bridge.request_open_node(node_id))
        self.app.processEvents()
        editor = next(
            item
            for item in self._qml_root_object().findChildren(QObject, "scriptEditorArea")
            if item.isVisible()
        )
        self.window.quick_widget.setFocus()
        editor.setProperty("text", "pass")
        editor.setProperty("cursorPosition", 4)
        editor.forceActiveFocus()

        QTest.keyClick(self.window.quick_widget, Qt.Key.Key_Tab)
        self.app.processEvents()
        self.assertEqual(editor.property("text"), "pass    ")
        self.assertTrue(editor.property("activeFocus"))

        QTest.keyClick(
            self.window.quick_widget,
            Qt.Key.Key_Z,
            Qt.KeyboardModifier.ControlModifier,
        )
        self.app.processEvents()
        self.assertEqual(editor.property("text"), "pass")
        QTest.keyClick(
            self.window.quick_widget,
            Qt.Key.Key_Y,
            Qt.KeyboardModifier.ControlModifier,
        )
        self.app.processEvents()
        self.assertEqual(editor.property("text"), "pass    ")

    def test_content_fullscreen_script_reopen_preserves_same_node_dirty_draft(
        self,
    ) -> None:
        node_id = self.window.scene.add_node_from_type(
            "core.python_script",
            x=120.0,
            y=80.0,
        )
        self.window.scene.focus_node(node_id)
        self.app.processEvents()
        draft = PYTHON_SCRIPT_DEFAULT_SOURCE.replace("payload}", "payload + 1}")
        self.window.script_editor.set_script_text(draft)

        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertEqual(self.window.script_editor.current_node_id, node_id)
        self.assertEqual(self.window.script_editor.script_text, draft)
        self.assertTrue(self.window.script_editor.dirty)

    def test_content_fullscreen_bridge_opens_excalidraw_board_as_web_editor_payload(self) -> None:
        node_id, state, preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.node_id, node_id)
        self.assertEqual(bridge.workspace_id, workspace_id)
        self.assertEqual(bridge.content_kind, "web_editor")
        self.assertEqual(bridge.media_payload, {})
        self.assertEqual(bridge.viewer_payload, {})
        self.assertIsInstance(bridge.web_surface_bridge, WebSurfaceBridge)
        self.assertEqual(bridge.web_surface_bridge.load_state(), state)

        payload = bridge.web_editor_payload
        self.assertEqual(payload["workspace_id"], workspace_id)
        self.assertEqual(payload["node_id"], node_id)
        self.assertEqual(payload["type_id"], EXCALIDRAW_BOARD_TYPE_ID)
        self.assertEqual(payload["title"], "Excalidraw Board")
        self.assertEqual(payload["surface_family"], "web")
        self.assertEqual(payload["surface_variant"], "excalidraw_board")
        self.assertEqual(payload["surface_spec"]["component_key"], "web_excalidraw_board")
        self.assertTrue(payload["surface_spec"]["input_capabilities"]["pressure"])
        self.assertEqual(payload["excalidraw_state"], state)
        self.assertEqual(payload["excalidraw_preview_ref"], preview_ref)
        self.assertTrue(str(payload["asset_url"]).startswith("file:"))
        self.assertTrue(Path(str(payload["asset_path"])).is_file())
        self.assertIn("webengine_available", payload)

    def test_content_fullscreen_bridge_opens_web_page_payload_without_privileged_bridge(self) -> None:
        node_id = self._add_web_page_node(
            start_location="https://example.com/docs",
            browser_state={"zoom_factor": 1.25},
        )
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.node_id, node_id)
        self.assertEqual(bridge.workspace_id, workspace_id)
        self.assertEqual(bridge.content_kind, "web_page")
        self.assertEqual(bridge.media_payload, {})
        self.assertEqual(bridge.viewer_payload, {})
        self.assertEqual(bridge.web_editor_payload, {})
        self.assertEqual(bridge.tabular_payload, {})
        self.assertIsNone(bridge.web_surface_bridge)

        payload = bridge.web_page_payload
        self.assertEqual(payload["workspace_id"], workspace_id)
        self.assertEqual(payload["node_id"], node_id)
        self.assertEqual(payload["type_id"], WEB_PAGE_VIEWER_TYPE_ID)
        self.assertEqual(payload["content_kind"], "web_page")
        self.assertEqual(payload["surface_family"], "web")
        self.assertEqual(payload["surface_variant"], "page_viewer")
        self.assertEqual(payload["surface_spec"]["component_key"], "web_page")
        self.assertEqual(payload["surface_spec"]["qml_component"], "../web/WebPageHost.qml")
        self.assertEqual(payload["surface_spec"]["fullscreen"]["content_kind"], "web_page")
        self.assertEqual(payload["navigation_decision"]["target_url"], "https://example.com/docs")
        self.assertTrue(payload["navigation_decision"]["allowed"])
        self.assertFalse(payload["navigation_decision"]["qwebchannel_allowed"])
        self.assertFalse(payload["qwebchannel_allowed"])
        self.assertNotIn("allowed_origins", payload)
        self.assertNotIn("access_profile", payload)
        self.assertIn("webengine_available", payload)
        self.assertNotIn("excalidraw", json.dumps(_payload_keys(payload)).lower())

    def test_content_fullscreen_bridge_opens_jupyter_live_borrow_shell_only(self) -> None:
        node_id = self._add_jupyter_node(
            notebook_ref="saved://notebook-local",
            server_state={
                "zoom": 1.25,
                "token": "super-secret",
                "url": "http://127.0.0.1:50101/notebooks/x.ipynb",
            },
        )
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.node_id, node_id)
        self.assertEqual(bridge.workspace_id, workspace_id)
        self.assertEqual(bridge.content_kind, "jupyter_notebook")
        self.assertEqual(bridge.media_payload, {})
        self.assertEqual(bridge.viewer_payload, {})
        self.assertEqual(bridge.web_editor_payload, {})
        self.assertEqual(bridge.web_page_payload, {})
        self.assertEqual(bridge.tabular_payload, {})
        self.assertIsNone(bridge.web_surface_bridge)

        serialized_bridge_payloads = json.dumps(
            {
                "media": bridge.media_payload,
                "viewer": bridge.viewer_payload,
                "web_editor": bridge.web_editor_payload,
                "web_page": bridge.web_page_payload,
                "tabular": bridge.tabular_payload,
            },
            sort_keys=True,
        ).lower()
        self.assertNotIn("super-secret", serialized_bridge_payloads)
        self.assertNotIn("127.0.0.1", serialized_bridge_payloads)
        self.assertNotIn("excalidraw", json.dumps(_payload_keys(bridge.web_page_payload)).lower())

    def test_content_fullscreen_bridge_persists_safe_web_page_browser_state(self) -> None:
        node_id = self._add_web_page_node(
            start_location="https://example.com/docs",
            browser_state={"zoom_factor": 1.25},
        )
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        self.assertTrue(
            bridge.save_web_page_browser_state(
                {
                    "current_url": "https://example.com/current",
                    "zoom_factor": 2.75,
                    "page_title": "  Example Docs  ",
                    "cookies": "must not persist",
                    "local_storage": {"must": "not persist"},
                    "page_content": "<html>must not persist</html>",
                }
            )
        )

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(
            workspace.nodes[node_id].properties["browser_state"],
            {
                "current_url": "https://example.com/current",
                "zoom_factor": 2.75,
                "page_title": "Example Docs",
            },
        )
        payload = bridge.web_page_payload
        self.assertEqual(payload["current_location"], "https://example.com/current")
        self.assertEqual(payload["browser_state"]["current_url"], "https://example.com/current")
        self.assertEqual(payload["navigation_decision"]["target_url"], "https://example.com/current")
        self.assertNotIn("cookies", json.dumps(payload["browser_state"], sort_keys=True).lower())
        self.assertNotIn("local_storage", json.dumps(payload["browser_state"], sort_keys=True).lower())
        self.assertNotIn("page_content", json.dumps(payload["browser_state"], sort_keys=True).lower())

    def test_content_fullscreen_bridge_skips_web_page_browser_state_when_disabled(self) -> None:
        node_id = self._add_web_page_node(
            start_location="https://example.com/docs",
            persist_browser_state=False,
            browser_state={
                "current_url": "https://example.com/original",
                "zoom_factor": 1.25,
            },
        )
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        self.assertFalse(
            bridge.save_web_page_browser_state(
                {
                    "current_url": "https://example.com/current",
                    "zoom_factor": 2.75,
                }
            )
        )

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(workspace.nodes[node_id].properties["browser_state"], {})
        payload = bridge.web_page_payload
        self.assertFalse(payload["persist_browser_state"])
        self.assertEqual(payload["browser_state"], {})
        self.assertEqual(payload["current_location"], "https://example.com/docs")

    def test_content_fullscreen_bridge_persists_offline_html_browser_state_as_file_url(self) -> None:
        fixture = Path(__file__).resolve().parent / "fixtures" / "web_page_viewer" / "index.html"
        node_id = self._add_web_page_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        self.assertTrue(
            bridge.save_web_page_browser_state(
                {
                    "current_url": str(fixture),
                    "zoom_factor": 1.5,
                }
            )
        )

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(
            workspace.nodes[node_id].properties["browser_state"],
            {
                "current_url": fixture.resolve().as_uri(),
                "zoom_factor": 1.5,
            },
        )
        payload = bridge.web_page_payload
        self.assertEqual(payload["current_location"], fixture.resolve().as_uri())
        self.assertTrue(payload["navigation_decision"]["allowed"])
        self.assertEqual(payload["navigation_decision"]["origin"], "file://")

    def test_content_fullscreen_bridge_keeps_invalid_web_page_visible_and_bridge_free(self) -> None:
        node_id = self._add_web_page_node(
            start_location="javascript:alert(1)",
        )
        bridge = self._bridge()

        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.content_kind, "web_page")
        self.assertIsNone(bridge.web_surface_bridge)
        payload = bridge.web_page_payload
        self.assertFalse(payload["navigation_decision"]["allowed"])
        self.assertIn("Unsupported web navigation scheme", payload["navigation_decision"]["reason"])

    def test_content_fullscreen_bridge_opens_tabular_payload_as_windowed_preview(self) -> None:
        node_id, source = self._add_tabular_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.can_open_node(node_id))
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertTrue(bridge.open)
        self.assertEqual(bridge.node_id, node_id)
        self.assertEqual(bridge.workspace_id, workspace_id)
        self.assertEqual(bridge.content_kind, "tabular")
        self.assertEqual(bridge.media_payload, {})
        self.assertEqual(bridge.viewer_payload, {})
        self.assertEqual(bridge.web_editor_payload, {})

        payload = bridge.tabular_payload
        self.assertEqual(payload["workspace_id"], workspace_id)
        self.assertEqual(payload["node_id"], node_id)
        self.assertEqual(payload["type_id"], TABULAR_DATA_INPUT_NODE_TYPE_ID)
        self.assertEqual(payload["surface_spec"]["fullscreen"]["content_kind"], "tabular")
        self.assertEqual(payload["surface_spec"]["fullscreen"]["action_kind"], "tabular")
        self.assertEqual(payload["preview_state"], "ready")
        self.assertEqual(payload[TABULAR_TABLE_VIEW_STATE_PROPERTY], {"version": 1, "column_widths": {}})
        self.assertEqual(payload[TABULAR_SELECTED_COLUMNS_PROPERTY], [])
        preview = payload["preview"]
        self.assertEqual(preview["preview_kind"], "table")
        self.assertEqual(preview["source"]["resolved_path"], str(source))
        self.assertEqual(preview["window"]["row_offset"], 0)
        self.assertEqual(preview["window"]["column_offset"], 0)
        self.assertEqual(len(preview["window"]["rows"]), 50)
        self.assertEqual(preview["window"]["columns"], ["station", "temp", "count"])
        self.assertTrue(preview["window"]["bounded"])
        self.assertFalse(preview["window"]["client_side_full_scan"])
        self.assertIn("request_tabular_window", json.dumps(preview["request_contracts"]))

        next_window = bridge.request_tabular_window(
            {"row_offset": 60, "row_limit": 5, "column_offset": 1, "column_limit": 1}
        )
        self.assertEqual(next_window["state"], "ready")
        self.assertEqual(next_window["window"]["row_offset"], 60)
        self.assertEqual(next_window["window"]["columns"], ["temp"])
        self.assertEqual(len(next_window["window"]["rows"]), 5)
        # Managed-cache reads return typed values (float64 via schema hint).
        self.assertEqual(next_window["window"]["rows"][0]["temp"], 26.0)

        document = self.window.serializer.to_document(self.window.model.project)
        self.assertNotIn("tabular_payload", json.dumps(_payload_keys(document)).lower())
        self.assertNotIn("request_tabular_window", json.dumps(document))

    def test_content_fullscreen_bridge_persists_tabular_table_view_state(self) -> None:
        node_id, _source = self._add_tabular_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        state = {
            "version": 1,
            "column_widths": {
                "table:station": 144,
                "array:2": 96,
                "bad": "wide",
            },
        }

        self.assertTrue(bridge.save_tabular_table_view_state(state))
        expected = {
            "version": 1,
            "column_widths": {
                "table:station": 144,
                "array:2": 96,
            },
        }
        self.assertEqual(bridge.tabular_payload[TABULAR_TABLE_VIEW_STATE_PROPERTY], expected)

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[TABULAR_TABLE_VIEW_STATE_PROPERTY], expected)

        document = self.window.serializer.to_document(self.window.model.project)
        serialized = json.dumps(document)
        self.assertIn(TABULAR_TABLE_VIEW_STATE_PROPERTY, serialized)
        self.assertNotIn("tabular_payload", json.dumps(_payload_keys(document)).lower())
        self.assertNotIn("request_tabular_window", serialized)

    def test_content_fullscreen_bridge_persists_tabular_selected_columns(self) -> None:
        node_id, _source = self._add_tabular_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        self.assertTrue(bridge.save_tabular_selected_columns(["station", "temp", "station", ""]))

        expected = ["station", "temp"]
        self.assertEqual(bridge.tabular_payload[TABULAR_SELECTED_COLUMNS_PROPERTY], expected)

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[TABULAR_SELECTED_COLUMNS_PROPERTY], expected)

        serialized = json.dumps(self.window.serializer.to_document(self.window.model.project))
        self.assertIn(TABULAR_SELECTED_COLUMNS_PROPERTY, serialized)

    def test_content_fullscreen_bridge_exports_visible_tabular_rows_after_query(self) -> None:
        node_id, _source = self._add_tabular_node()
        bridge = self._bridge()
        output = Path(self._env.temp_path) / "visible-filtered.csv"
        save_calls: list[dict[str, str]] = []

        def save_file_dialog(**kwargs):  # noqa: ANN001
            save_calls.append({key: str(value) for key, value in kwargs.items()})
            return str(output)

        self.window.shell_host_presenter.save_file_dialog = save_file_dialog
        self.assertTrue(bridge.request_open_node(node_id))

        request = {
            "row_offset": 0,
            "row_limit": 3,
            "column_offset": 0,
            "column_limit": 3,
            "search": "S11",
            "sort": {"column": "count", "descending": True},
        }
        visible = bridge.request_tabular_window(request)
        self.assertEqual(visible["state"], "ready")
        self.assertEqual(visible["window"]["rows"][0]["station"], "S119")

        result = bridge.export_tabular_visible_rows(
            {
                "preview_kind": "table",
                "request": visible["window"]["request"],
            }
        )

        self.assertEqual(result, {"ok": True, "path": str(output), "error": ""})
        self.assertEqual(save_calls[0]["title"], "Export Visible Rows")
        self.assertIn("Table Output", save_calls[0]["file_filter"])
        self.assertEqual(
            output.read_text(encoding="utf-8").splitlines(),
            [
                "station,temp,count",
                "S119,31.9,119",
                "S118,31.8,118",
                "S117,31.7,117",
            ],
        )

        node_export = Path(self._env.temp_path) / "visible-inline.csv"

        def save_file_dialog_for_node(**kwargs):  # noqa: ANN001
            return str(node_export)

        self.window.shell_host_presenter.save_file_dialog = save_file_dialog_for_node
        node_result = bridge.export_tabular_visible_rows_for_node(
            node_id,
            {
                "preview_kind": "table",
                "request": visible["window"]["request"],
            },
        )
        self.assertEqual(node_result["path"], str(node_export))
        self.assertTrue(node_export.exists())

    def test_content_fullscreen_bridge_drops_stale_tabular_window_jobs(self) -> None:
        node_id, _source = self._add_tabular_node()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        fake_pool = _FakeTabularWorkerPool()
        bridge._tabular_preview_worker_pool = fake_pool  # noqa: SLF001
        emitted: list[tuple[str, dict]] = []
        bridge.tabular_window_ready.connect(lambda request_id, payload: emitted.append((request_id, payload)))
        properties = bridge._current_tabular_node_properties()  # noqa: SLF001
        self.assertIsInstance(properties, dict)

        first_id = bridge._schedule_tabular_window_job(  # noqa: SLF001
            properties,
            {"row_offset": 0, "row_limit": 5},
            kind="table",
        )
        second_id = bridge._schedule_tabular_window_job(  # noqa: SLF001
            properties,
            {"row_offset": 5, "row_limit": 5},
            kind="table",
        )
        pending = {
            item["request_id"]: (job_key, item)
            for job_key, item in bridge._pending_tabular_window_jobs.items()  # noqa: SLF001
        }
        pending[first_id][1]["result"].update({"state": "ready", "window": {"row_offset": 0}})
        bridge._on_tabular_preview_job_finished(pending[first_id][0], "")  # noqa: SLF001
        self.assertEqual(emitted, [])

        pending[second_id][1]["result"].update({"state": "ready", "window": {"row_offset": 5}})
        bridge._on_tabular_preview_job_finished(pending[second_id][0], "")  # noqa: SLF001
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0][0], second_id)
        self.assertEqual(emitted[0][1]["request_id"], second_id)
        self.assertEqual(emitted[0][1]["window"]["row_offset"], 5)

    def test_content_fullscreen_bridge_clears_pending_tabular_jobs_on_close(self) -> None:
        node_id, _source = self._add_tabular_node()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        bridge._pending_tabular_payload_job = "payload-job"  # noqa: SLF001
        bridge._pending_tabular_payload_node_id = node_id  # noqa: SLF001
        bridge._latest_tabular_window_request_id = "request-1"  # noqa: SLF001
        bridge._pending_tabular_window_jobs["window-job"] = {  # noqa: SLF001
            "node_id": node_id,
            "request_id": "request-1",
            "result": {"state": "ready"},
        }

        bridge.request_close()
        bridge._on_tabular_preview_job_finished("payload-job", "")  # noqa: SLF001
        bridge._on_tabular_preview_job_finished("window-job", "")  # noqa: SLF001

        self.assertFalse(bridge.open)
        self.assertEqual(bridge._pending_tabular_payload_job, "")  # noqa: SLF001
        self.assertEqual(bridge._pending_tabular_payload_node_id, "")  # noqa: SLF001
        self.assertEqual(bridge._latest_tabular_window_request_id, "")  # noqa: SLF001
        self.assertEqual(bridge._pending_tabular_window_jobs, {})  # noqa: SLF001

    def test_content_fullscreen_bridge_reports_tabular_window_worker_errors(self) -> None:
        node_id, _source = self._add_tabular_node()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        bridge._tabular_preview_worker_pool = _FakeTabularWorkerPool()  # noqa: SLF001
        emitted: list[tuple[str, dict]] = []
        bridge.tabular_window_ready.connect(lambda request_id, payload: emitted.append((request_id, payload)))
        properties = bridge._current_tabular_node_properties()  # noqa: SLF001
        self.assertIsInstance(properties, dict)

        request_id = bridge._schedule_tabular_window_job(  # noqa: SLF001
            properties,
            {"row_offset": 0, "row_limit": 5},
            kind="table",
        )
        pending = {
            item["request_id"]: (job_key, item)
            for job_key, item in bridge._pending_tabular_window_jobs.items()  # noqa: SLF001
        }
        bridge._on_tabular_preview_job_finished(pending[request_id][0], "cache failed")  # noqa: SLF001

        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0][0], request_id)
        self.assertEqual(emitted[0][1]["state"], "error")
        self.assertIn("cache failed", emitted[0][1]["message"])

    def test_content_fullscreen_bridge_rejects_tabular_table_view_state_without_active_tabular_node(self) -> None:
        node_id = self._add_image_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertFalse(bridge.save_tabular_table_view_state({"column_widths": {"table:station": 144}}))
        self.assertFalse(bridge.save_tabular_selected_columns(["station"]))
        self.assertTrue(bridge.request_open_node(node_id))
        self.assertFalse(bridge.save_tabular_table_view_state({"column_widths": {"table:station": 144}}))
        self.assertFalse(bridge.save_tabular_selected_columns(["station"]))

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertNotIn(TABULAR_TABLE_VIEW_STATE_PROPERTY, node.properties)
        self.assertNotIn(TABULAR_SELECTED_COLUMNS_PROPERTY, node.properties)

    def test_content_fullscreen_web_editor_save_updates_excalidraw_state_only(self) -> None:
        node_id, _state, preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(web_bridge, WebSurfaceBridge)

        updated_state = {
            "type": "excalidraw",
            "elements": [{"id": "text-1", "type": "text", "text": "saved"}],
            "appState": {"name": "Saved map", "theme": "light"},
            "files": {},
            "excalidraw_preview_ref": {"should_not": "persist"},
        }
        self.assertTrue(web_bridge.save_state(updated_state))
        self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[EXCALIDRAW_STATE_PROPERTY], updated_state)
        self.assertEqual(node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY], preview_ref)
        self.assertEqual(bridge.web_surface_bridge.load_state(), updated_state)

    def test_content_fullscreen_web_editor_save_uses_project_artifact_callbacks(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-artifact-board.cxproj"
        self.window.project_path = str(project_path)
        node_id, _state, _preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(web_bridge, WebSurfaceBridge)

        image_payload = b"\x89PNG\r\n\x1a\nfullscreen-artifact-image"
        image_hash = hashlib.sha256(image_payload).hexdigest()
        updated_state = {
            "type": "excalidraw",
            "elements": [],
            "appState": {"name": "Artifact save"},
            "files": {
                "file-1": {
                    "mimeType": "image/png",
                    "dataURL": _data_url("image/png", image_payload),
                    "created": 10,
                    "lastRetrieved": 20,
                    "name": "managed.png",
                }
            },
        }

        self.assertTrue(web_bridge.save_state(updated_state))
        self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        saved_file = node.properties[EXCALIDRAW_STATE_PROPERTY]["files"]["file-1"]
        self.assertNotIn("dataURL", saved_file)
        self.assertTrue(saved_file["artifact_ref"].startswith("temp://"))
        self.assertEqual(saved_file["sha256"], image_hash)
        self.assertIn("artifact_store", self.window.model.project.metadata)

        store = ProjectArtifactStore.from_project_metadata(
            project_path=self.window.project_path,
            project_metadata=self.window.model.project.metadata,
        )
        staged_path = store.resolve_staged_path(saved_file["artifact_ref"])
        self.assertIsNotNone(staged_path)
        self.assertEqual(staged_path.read_bytes(), image_payload)
        hydrated = web_bridge.asset_request({"asset_id": "file-1"})
        self.assertTrue(hydrated["ok"])
        self.assertEqual(hydrated["sha256"], image_hash)

    def test_content_fullscreen_web_editor_close_export_persists_preview_ref(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-preview-board.cxproj"
        self.window.project_path = str(project_path)
        node_id, _state, _preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(web_bridge, WebSurfaceBridge)
        before_revision = self.window.model.project.project_document_revision
        metadata_events: list[int] = []
        self.window.project_meta_changed.connect(
            lambda: metadata_events.append(
                self.window.model.project.project_document_revision
            )
        )

        preview_payload = b"\x89PNG\r\n\x1a\nfullscreen-preview"
        preview_hash = hashlib.sha256(preview_payload).hexdigest()
        project = self.window.model.project
        replace_metadata_impl = ProjectData.replace_metadata
        with mock.patch.object(
            ProjectData,
            "replace_metadata",
            autospec=True,
            side_effect=replace_metadata_impl,
        ) as replace_metadata:
            result = web_bridge.export_preview(
                {
                    "dataURL": _data_url("image/png", preview_payload),
                    "width": 640,
                    "height": 360,
                    "name": "fullscreen-preview.png",
                }
            )
            replace_metadata.assert_called_once()

        self.assertTrue(result["ok"])
        bridge.finish_web_editor_close(result)
        self.app.processEvents()

        self.assertFalse(bridge.open)
        self.assertEqual(
            self.window.model.project.project_document_revision,
            before_revision + 1,
        )
        self.assertEqual(metadata_events, [before_revision + 1])
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        preview_ref = node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]
        self.assertEqual(preview_ref["artifact_ref"], result["preview_ref"])
        self.assertEqual(preview_ref["mime_type"], "image/png")
        self.assertEqual(preview_ref["width"], 640)
        self.assertEqual(preview_ref["height"], 360)
        self.assertEqual(preview_ref["size"], len(preview_payload))
        self.assertEqual(preview_ref["sha256"], preview_hash)
        self.assertNotIn("data_url", json.dumps(preview_ref))

        store = ProjectArtifactStore.from_project_metadata(
            project_path=self.window.project_path,
            project_metadata=self.window.model.project.metadata,
        )
        preview_path = store.resolve_staged_path(preview_ref["artifact_ref"])
        self.assertIsNotNone(preview_path)
        self.assertEqual(preview_path.read_bytes(), preview_payload)

    def test_content_fullscreen_web_editor_preview_staging_is_scoped_per_board(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-two-preview-boards.cxproj"
        self.window.project_path = str(project_path)
        first_node_id, _first_state, _first_preview_ref = self._add_excalidraw_node()
        second_node_id, _second_state, _second_preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(first_node_id))
        first_web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(first_web_bridge, WebSurfaceBridge)
        first_payload = b"\x89PNG\r\n\x1a\nfirst-fullscreen-board-preview"
        first_result = first_web_bridge.export_preview(
            {
                "dataURL": _data_url("image/png", first_payload),
                "width": 640,
                "height": 360,
                "name": "first-fullscreen-preview.png",
            }
        )
        self.assertTrue(first_result["ok"])
        bridge.finish_web_editor_close(first_result)
        self.app.processEvents()

        self.assertTrue(bridge.request_open_node(second_node_id))
        second_web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(second_web_bridge, WebSurfaceBridge)
        second_payload = b"\x89PNG\r\n\x1a\nsecond-fullscreen-board-preview"
        second_result = second_web_bridge.export_preview(
            {
                "dataURL": _data_url("image/png", second_payload),
                "width": 640,
                "height": 360,
                "name": "second-fullscreen-preview.png",
            }
        )
        self.assertTrue(second_result["ok"])
        bridge.finish_web_editor_close(second_result)
        self.app.processEvents()

        first_node = self.window.model.project.workspaces[workspace_id].nodes[first_node_id]
        second_node = self.window.model.project.workspaces[workspace_id].nodes[second_node_id]
        first_ref = first_node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]
        second_ref = second_node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]
        self.assertNotEqual(first_ref["artifact_ref"], second_ref["artifact_ref"])

        store = ProjectArtifactStore.from_project_metadata(
            project_path=self.window.project_path,
            project_metadata=self.window.model.project.metadata,
        )
        first_path = store.resolve_staged_path(first_ref["artifact_ref"])
        second_path = store.resolve_staged_path(second_ref["artifact_ref"])
        self.assertIsNotNone(first_path)
        self.assertIsNotNone(second_path)
        self.assertEqual(first_path.read_bytes(), first_payload)
        self.assertEqual(second_path.read_bytes(), second_payload)

    def test_content_fullscreen_web_editor_close_export_persists_scene_state_from_payload(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-close-state-board.cxproj"
        self.window.project_path = str(project_path)
        node_id, _state, _preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(web_bridge, WebSurfaceBridge)

        updated_state = {
            "type": "excalidraw",
            "elements": [{"id": "freehand-1", "type": "freedraw", "isDeleted": False}],
            "appState": {"name": "Close persisted board"},
            "files": {},
        }
        preview_payload = b"\x89PNG\r\n\x1a\nfullscreen-close-state-preview"
        result = web_bridge.export_preview(
            {
                "dataURL": _data_url("image/png", preview_payload),
                "width": 800,
                "height": 480,
                "name": "fullscreen-close-state-preview.png",
                "scene_state": updated_state,
            }
        )

        self.assertTrue(result["ok"])
        self.app.processEvents()
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[EXCALIDRAW_STATE_PROPERTY], updated_state)

        bridge.finish_web_editor_close(result)
        self.app.processEvents()

        self.assertFalse(bridge.open)
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[EXCALIDRAW_STATE_PROPERTY], updated_state)
        self.assertEqual(
            node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]["artifact_ref"],
            result["preview_ref"],
        )

    def test_content_fullscreen_web_editor_export_signal_includes_close_scene_payload(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-close-signal-board.cxproj"
        self.window.project_path = str(project_path)
        node_id, _state, _preview_ref = self._add_excalidraw_node()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(web_bridge, WebSurfaceBridge)

        emitted: list[dict[str, object]] = []
        web_bridge.preview_export_finished.connect(lambda result: emitted.append(result))

        updated_state = {
            "type": "excalidraw",
            "elements": [{"id": "signal-freedraw-1", "type": "freedraw", "isDeleted": False}],
            "appState": {"name": "Signal close payload"},
            "files": {},
        }
        preview_payload = b"\x89PNG\r\n\x1a\nfullscreen-close-signal-preview"
        result = web_bridge.export_preview(
            {
                "dataURL": _data_url("image/png", preview_payload),
                "width": 640,
                "height": 360,
                "name": "fullscreen-close-signal-preview.png",
                "scene_state": updated_state,
            }
        )
        self.app.processEvents()

        self.assertTrue(result["ok"])
        self.assertEqual(result["scene_state"], updated_state)
        self.assertEqual(result["host_payload"]["scene_state"], updated_state)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["preview_ref"], result["preview_ref"])
        self.assertEqual(emitted[0]["scene_state"], updated_state)
        self.assertEqual(emitted[0]["host_payload"]["scene_state"], updated_state)

    def test_content_fullscreen_web_editor_close_materializes_host_payload_without_webchannel(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-host-payload-board.cxproj"
        self.window.project_path = str(project_path)
        node_id, _state, _preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))

        updated_state = {
            "type": "excalidraw",
            "elements": [{"id": "offline-rect-1", "type": "rectangle", "isDeleted": False}],
            "appState": {"name": "Offline close payload"},
            "files": {},
        }
        preview_payload = b"\x89PNG\r\n\x1a\noffline-close-preview"
        preview_hash = hashlib.sha256(preview_payload).hexdigest()

        bridge.finish_web_editor_close(
            {
                "ok": False,
                "error": "Preview export did not return a bridge response.",
                "host_payload": {
                    "dataURL": _data_url("image/png", preview_payload),
                    "width": 512,
                    "height": 320,
                    "name": "offline-close-preview.png",
                    "scene_state": updated_state,
                },
            }
        )
        self.app.processEvents()

        self.assertFalse(bridge.open)
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[EXCALIDRAW_STATE_PROPERTY], updated_state)
        preview_ref = node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]
        self.assertEqual(preview_ref["mime_type"], "image/png")
        self.assertEqual(preview_ref["width"], 512)
        self.assertEqual(preview_ref["height"], 320)
        self.assertEqual(preview_ref["sha256"], preview_hash)

        store = ProjectArtifactStore.from_project_metadata(
            project_path=self.window.project_path,
            project_metadata=self.window.model.project.metadata,
        )
        preview_path = store.resolve_staged_path(preview_ref["artifact_ref"])
        self.assertIsNotNone(preview_path)
        self.assertEqual(preview_path.read_bytes(), preview_payload)

    def test_content_fullscreen_web_editor_close_preview_failure_keeps_last_preview_ref(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-keep-preview-board.cxproj"
        self.window.project_path = str(project_path)
        node_id, _state, _preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(web_bridge, WebSurfaceBridge)

        preview_payload = b"\x89PNG\r\n\x1a\nexisting-close-preview"
        result = web_bridge.export_preview(
            {
                "dataURL": _data_url("image/png", preview_payload),
                "width": 640,
                "height": 360,
                "name": "existing-close-preview.png",
            }
        )
        self.assertTrue(result["ok"])
        self.app.processEvents()
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        preview_ref = node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]

        bridge.finish_web_editor_close({"ok": False, "error": "Preview export timed out."})
        self.app.processEvents()

        self.assertFalse(bridge.open)
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY], preview_ref)

    def test_content_fullscreen_web_editor_close_failure_refreshes_preview_after_edits(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-refresh-preview-board.cxproj"
        self.window.project_path = str(project_path)
        node_id, _state, _preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(web_bridge, WebSurfaceBridge)

        preview_payload = b"\x89PNG\r\n\x1a\ninitial-refresh-preview"
        initial_result = web_bridge.export_preview(
            {
                "dataURL": _data_url("image/png", preview_payload),
                "width": 640,
                "height": 360,
                "name": "initial-refresh-preview.png",
            }
        )
        self.assertTrue(initial_result["ok"])
        self.app.processEvents()
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        initial_preview_ref = node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]

        updated_state = {
            "type": "excalidraw",
            "elements": [
                {
                    "id": "refresh-diamond-1",
                    "type": "diamond",
                    "x": 90,
                    "y": 70,
                    "width": 180,
                    "height": 140,
                    "strokeColor": "#1e1e1e",
                    "backgroundColor": "transparent",
                    "strokeWidth": 2,
                    "opacity": 100,
                    "isDeleted": False,
                },
                {
                    "id": "refresh-arrow-1",
                    "type": "arrow",
                    "x": 290,
                    "y": 135,
                    "width": 170,
                    "height": 60,
                    "points": [[0, 0], [170, 60]],
                    "strokeColor": "#1e1e1e",
                    "backgroundColor": "transparent",
                    "strokeWidth": 2,
                    "opacity": 100,
                    "isDeleted": False,
                },
            ],
            "appState": {"name": "Refresh preview board", "viewBackgroundColor": "#ffffff"},
            "files": {},
        }
        self.assertTrue(web_bridge.save_state(updated_state))
        self.app.processEvents()

        bridge.finish_web_editor_close({"ok": False, "error": "Preview export timed out."})
        self.app.processEvents()

        self.assertFalse(bridge.open)
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[EXCALIDRAW_STATE_PROPERTY], updated_state)
        refreshed_preview_ref = node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]
        self.assertNotEqual(refreshed_preview_ref["artifact_ref"], initial_preview_ref["artifact_ref"])
        self.assertTrue(refreshed_preview_ref["artifact_ref"].startswith("temp://"))
        self.assertEqual(refreshed_preview_ref["mime_type"], "image/png")
        self.assertEqual(refreshed_preview_ref["width"], 640)
        self.assertEqual(refreshed_preview_ref["height"], 360)

        store = ProjectArtifactStore.from_project_metadata(
            project_path=self.window.project_path,
            project_metadata=self.window.model.project.metadata,
        )
        preview_path = store.resolve_staged_path(refreshed_preview_ref["artifact_ref"])
        self.assertIsNotNone(preview_path)
        self.assertTrue(preview_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_content_fullscreen_web_editor_close_failure_generates_missing_preview_ref(self) -> None:
        project_path = Path(self._env.temp_path) / "fullscreen-fallback-preview-board.cxproj"
        self.window.project_path = str(project_path)
        node_id, _state, _preview_ref = self._add_excalidraw_node()
        self.window.scene.set_node_property(node_id, EXCALIDRAW_PREVIEW_REF_PROPERTY, "")
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(web_bridge, WebSurfaceBridge)

        updated_state = {
            "type": "excalidraw",
            "elements": [
                {
                    "id": "fallback-rect-1",
                    "type": "rectangle",
                    "x": 100,
                    "y": 80,
                    "width": 260,
                    "height": 120,
                    "strokeColor": "#1e1e1e",
                    "backgroundColor": "transparent",
                    "strokeWidth": 2,
                    "opacity": 100,
                    "isDeleted": False,
                },
                {
                    "id": "fallback-text-1",
                    "type": "text",
                    "x": 145,
                    "y": 125,
                    "width": 140,
                    "height": 36,
                    "text": "fallback preview",
                    "fontSize": 24,
                    "strokeColor": "#1e1e1e",
                    "backgroundColor": "transparent",
                    "opacity": 100,
                    "isDeleted": False,
                },
            ],
            "appState": {"name": "Fallback preview board", "viewBackgroundColor": "#ffffff"},
            "files": {},
        }
        self.assertTrue(web_bridge.save_state(updated_state))
        self.app.processEvents()

        bridge.finish_web_editor_close({"ok": False, "error": "Preview export timed out."})
        self.app.processEvents()

        self.assertFalse(bridge.open)
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[EXCALIDRAW_STATE_PROPERTY], updated_state)
        preview_ref = node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]
        self.assertTrue(preview_ref["artifact_ref"].startswith("temp://"))
        self.assertEqual(preview_ref["mime_type"], "image/png")
        self.assertEqual(preview_ref["width"], 640)
        self.assertEqual(preview_ref["height"], 360)
        self.assertGreater(preview_ref["size"], 0)
        self.assertTrue(preview_ref["sha256"])
        self.assertNotIn("data_url", json.dumps(preview_ref))
        self.assertNotIn("dataURL", json.dumps(preview_ref))

        store = ProjectArtifactStore.from_project_metadata(
            project_path=self.window.project_path,
            project_metadata=self.window.model.project.metadata,
        )
        preview_path = store.resolve_staged_path(preview_ref["artifact_ref"])
        self.assertIsNotNone(preview_path)
        self.assertTrue(preview_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_content_fullscreen_web_editor_invalid_payload_stays_visible_and_non_mutating(self) -> None:
        node_id, state, preview_ref = self._add_excalidraw_node()
        workspace_id = self.window.workspace_manager.active_workspace_id()
        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))
        web_bridge = bridge.web_surface_bridge
        self.assertIsInstance(web_bridge, WebSurfaceBridge)

        self.assertFalse(web_bridge.save_state("{not-json"))
        self.app.processEvents()

        self.assertTrue(web_bridge.has_error)
        self.assertIn("valid JSON", web_bridge.last_error)
        self.assertTrue(bridge.open)
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties[EXCALIDRAW_STATE_PROPERTY], state)
        self.assertEqual(node.properties[EXCALIDRAW_PREVIEW_REF_PROPERTY], preview_ref)

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
        unsupported_node_id = self.window.scene.add_node_from_type("core.constant", x=420.0, y=80.0)
        missing_source_node_id = self.window.scene.add_node_from_type(MEDIA_PANEL_TYPE_ID, x=620.0, y=80.0)
        self.app.processEvents()

        bridge = self._bridge()
        self.assertTrue(bridge.request_open_node(node_id))

        self.assertFalse(bridge.request_open_node(unsupported_node_id))
        self.assertFalse(bridge.open)
        self.assertIn("does not support", bridge.last_error)

        self.assertTrue(bridge.request_open_node(missing_source_node_id))
        self.assertTrue(bridge.open)
        self.assertEqual(bridge.media_payload["source_state"], "waiting")
        self.assertEqual(bridge.media_payload["resolved_source_url"], "")

    def test_content_fullscreen_bridge_closes_on_node_deletion_shell_wiring(self) -> None:
        node_id = self._add_image_node()
        bridge = self._bridge()

        self.assertTrue(bridge.request_open_node(node_id))
        self.window.scene.remove_workspace_node(node_id)
        self.app.processEvents()

        self.assertFalse(bridge.open)
        self.assertEqual(bridge.node_id, "")
        self.assertEqual(bridge.last_error, "")
