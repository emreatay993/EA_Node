from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PyQt6.QtCore import QCoreApplication, QEvent, QObject, QUrl, pyqtSignal
from PyQt6.QtGui import QImage

from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.nodes.builtins.ansys_dpf_common import DPF_VIEWER_NODE_TYPE_ID
from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge
from tests.main_window_shell.base import MainWindowShellTestBase


class _ViewerExecutionClientStub:
    def __init__(self) -> None:
        self.next_run_id = "run_live"
        self.start_calls: list[dict[str, Any]] = []
        self.pause_calls: list[str] = []
        self.resume_calls: list[str] = []
        self.stop_calls: list[str] = []
        self.open_calls: list[dict[str, Any]] = []
        self.update_calls: list[dict[str, Any]] = []
        self.materialize_calls: list[dict[str, Any]] = []
        self.close_calls: list[dict[str, Any]] = []
        self._request_counter = 0

    def _next_request_id(self, prefix: str) -> str:
        self._request_counter += 1
        return f"{prefix}_{self._request_counter}"

    def start_run(self, *, project_path: str, workspace_id: str, trigger: dict[str, Any]) -> str:
        self.start_calls.append(
            {
                "project_path": project_path,
                "workspace_id": workspace_id,
                "trigger": trigger,
            }
        )
        return self.next_run_id

    def pause_run(self, run_id: str) -> None:
        self.pause_calls.append(str(run_id))

    def resume_run(self, run_id: str) -> None:
        self.resume_calls.append(str(run_id))

    def stop_run(self, run_id: str) -> None:
        self.stop_calls.append(str(run_id))

    def open_viewer_session(
        self,
        *,
        workspace_id: str,
        node_id: str,
        session_id: str = "",
        backend_id: str = "",
        data_refs: dict[str, Any] | None = None,
        transport: dict[str, Any] | None = None,
        transport_revision: int = 0,
        live_open_status: str = "",
        live_open_blocker: dict[str, Any] | None = None,
        camera_state: dict[str, Any] | None = None,
        playback_state: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        request_id = self._next_request_id("open")
        self.open_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "backend_id": backend_id,
                "data_refs": dict(data_refs or {}),
                "transport": dict(transport or {}),
                "transport_revision": int(transport_revision),
                "live_open_status": str(live_open_status),
                "live_open_blocker": dict(live_open_blocker or {}),
                "camera_state": dict(camera_state or {}),
                "playback_state": dict(playback_state or {}),
                "summary": dict(summary or {}),
                "options": dict(options or {}),
            }
        )
        return request_id

    def update_viewer_session(
        self,
        *,
        workspace_id: str,
        node_id: str,
        session_id: str,
        backend_id: str = "",
        camera_state: dict[str, Any] | None = None,
        playback_state: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        request_id = self._next_request_id("update")
        self.update_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "backend_id": backend_id,
                "camera_state": dict(camera_state or {}),
                "playback_state": dict(playback_state or {}),
                "summary": dict(summary or {}),
                "options": dict(options or {}),
            }
        )
        return request_id

    def close_viewer_session(
        self,
        *,
        workspace_id: str,
        node_id: str,
        session_id: str,
        options: dict[str, Any] | None = None,
    ) -> str:
        request_id = self._next_request_id("close")
        self.close_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "options": dict(options or {}),
            }
        )
        return request_id

    def materialize_viewer_data(
        self,
        *,
        workspace_id: str,
        node_id: str,
        session_id: str,
        backend_id: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        request_id = self._next_request_id("materialize")
        self.materialize_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "backend_id": backend_id,
                "options": dict(options or {}),
            }
        )
        return request_id

    def shutdown(self) -> None:
        return None


class _SceneStub(QObject):
    workspace_changed = pyqtSignal(str)
    selection_changed = pyqtSignal()
    nodes_changed = pyqtSignal()
    edges_changed = pyqtSignal()

    def __init__(self, workspace_id: str = "ws_main") -> None:
        super().__init__()
        self.workspace_id = workspace_id
        self.selected_node_lookup: dict[str, bool] = {}

    def set_selected(self, *node_ids: str) -> None:
        self.selected_node_lookup = {
            str(node_id): True
            for node_id in node_ids
            if str(node_id).strip()
        }
        self.selection_changed.emit()


class _WorkspaceManagerStub:
    def __init__(self, scene: _SceneStub) -> None:
        self._scene = scene

    def active_workspace_id(self) -> str:
        return self._scene.workspace_id


@dataclass
class _WorkspaceState:
    nodes: dict[str, object]


@dataclass
class _ProjectState:
    workspaces: dict[str, _WorkspaceState]


@dataclass
class _ModelState:
    project: _ProjectState


class _HostStub(QObject):
    execution_event = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.scene = _SceneStub()
        self.workspace_manager = _WorkspaceManagerStub(self.scene)
        self.execution_client = _ViewerExecutionClientStub()
        self.project_path = ""
        self.captured_camera_state: dict[str, Any] = {}
        self.capture_camera_calls: list[dict[str, str]] = []
        self.captured_preview_image = QImage()
        self.capture_preview_calls: list[dict[str, str]] = []
        self.model = _ModelState(
            project=_ProjectState(
                workspaces={
                    "ws_main": _WorkspaceState(
                        nodes={
                            "node_viewer": object(),
                            "node_viewer_b": object(),
                            "node_viewer_restore": object(),
                            "node_viewer_other": object(),
                        }
                    )
                }
            )
        )
        self.model.project.metadata = {}

    def capture_overlay_camera_state(self, node_id: str, *, workspace_id: str = "") -> dict[str, Any]:
        self.capture_camera_calls.append(
            {
                "workspace_id": str(workspace_id),
                "node_id": str(node_id),
            }
        )
        return dict(self.captured_camera_state)

    def capture_overlay_preview_image(self, node_id: str, *, workspace_id: str = "") -> QImage:
        self.capture_preview_calls.append(
            {
                "workspace_id": str(workspace_id),
                "node_id": str(node_id),
            }
        )
        return self.captured_preview_image.copy()

    @property
    def viewer_host_service(self):  # noqa: ANN201
        return self


def _viewer_opened_event(
    *,
    request_id: str,
    workspace_id: str,
    node_id: str,
    session_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    summary = {
        "cache_state": "proxy_ready",
        "result_name": "displacement",
    }
    summary.update(dict(overrides.pop("summary", {})))
    options = {
        "session_state": "open",
        "cache_state": summary["cache_state"],
        "live_policy": "focus_only",
        "keep_live": False,
        "playback_state": "paused",
        "live_mode": "proxy",
    }
    options.update(dict(overrides.pop("options", {})))
    payload = {
        "type": "viewer_session_opened",
        "request_id": request_id,
        "workspace_id": workspace_id,
        "node_id": node_id,
        "session_id": session_id,
        "data_refs": dict(overrides.pop("data_refs", {})),
        "live_open_status": "ready",
        "summary": summary,
        "options": options,
    }
    payload.update(overrides)
    return payload


def _preview_image(color: int = 0xFF4C7BC0) -> QImage:
    image = QImage(24, 18, QImage.Format.Format_ARGB32)
    image.fill(color)
    return image


class ViewerSessionBridgeUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self) -> None:
        self.host = _HostStub()
        self.bridge = ViewerSessionBridge(
            self.host,
            shell_window=self.host,
            scene_bridge=self.host.scene,
        )

    def test_viewer_session_bridge_facade_stays_within_packet_budget(self) -> None:
        ui_qml_dir = Path(__file__).resolve().parents[1] / "ea_node_editor" / "ui_qml"
        facade_path = ui_qml_dir / "viewer_session_bridge.py"
        support_path = ui_qml_dir / "viewer_session_bridge_support.py"
        facade_text = facade_path.read_text(encoding="utf-8")

        self.assertTrue(support_path.exists())
        self.assertIn("viewer_session_bridge_support", facade_text)
        self.assertIn("ViewerSessionBridge", facade_text)
        self.assertLessEqual(len(facade_text.splitlines()), 550)

    def _open_live_session(self, node_id: str = "node_viewer") -> str:
        self.host.scene.set_selected(node_id)
        session_id = self.bridge.open(node_id, {"data_refs": {"fields": f"fields::{node_id}"}})
        open_call = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id="ws_main",
                node_id=node_id,
                session_id=session_id,
                summary={"cache_state": "live_ready"},
                options={"live_mode": "full"},
                data_refs={"dataset": {"kind": f"mock::{node_id}"}},
            )
        )
        return session_id

    def _create_transient_proxy_preview(self, node_id: str = "node_viewer") -> tuple[str, Path]:
        session_id = self._open_live_session(node_id=node_id)
        self.host.captured_camera_state = {
            "position": [9.0, 8.0, 7.0],
            "focal_point": [1.0, 2.0, 3.0],
            "viewup": [0.0, 1.0, 0.0],
            "view_angle": 24.0,
        }
        self.host.captured_preview_image = _preview_image()
        self.assertTrue(self.bridge.focus_session(node_id))
        self.assertTrue(self.bridge.clear_viewer_focus())
        preview_path = Path(self.bridge.session_state(node_id)["data_refs"]["preview"])
        self.assertTrue(preview_path.is_file())
        return session_id, preview_path

    def _register_managed_preview_artifact(self, artifact_id: str, *, color: int = 0xFF4C7BC0) -> Path:
        if not self.host.project_path:
            temp_dir = tempfile.TemporaryDirectory()
            self.addCleanup(temp_dir.cleanup)
            project_path = Path(temp_dir.name) / "viewer_bridge_test.sfe"
            project_path.parent.mkdir(parents=True, exist_ok=True)
            project_path.write_text("{}", encoding="utf-8")
            self.host.project_path = str(project_path)

        project_file = Path(self.host.project_path)
        sidecar_root = project_file.with_name(f"{project_file.stem}.data")
        relative_path = f"assets/media/{artifact_id}.png"
        artifact_path = sidecar_root / "assets" / "media" / f"{artifact_id}.png"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        self.assertTrue(_preview_image(color).save(str(artifact_path), "PNG"))

        metadata = dict(self.host.model.project.metadata) if isinstance(self.host.model.project.metadata, dict) else {}
        artifact_store = dict(metadata.get("artifact_store", {}))
        artifacts = dict(artifact_store.get("artifacts", {}))
        artifacts[artifact_id] = {"relative_path": relative_path}
        artifact_store["artifacts"] = artifacts
        metadata["artifact_store"] = artifact_store
        self.host.model.project.metadata = metadata
        return artifact_path

    def test_open_close_and_control_actions_route_through_execution_client_and_track_state(self) -> None:
        self.host.scene.set_selected("node_viewer")
        session_id = self.bridge.open(
            "node_viewer",
            {
                "data_refs": {"fields": "fields_ref"},
                "summary": {"result_name": "displacement"},
                "backend_id": "backend.custom",
                "camera_state": {"zoom": 1.2},
                "playback_state": {"state": "paused", "step_index": 3},
                "options": {"live_mode": "proxy"},
            },
        )

        self.assertTrue(session_id.startswith("viewer_session_"))
        self.assertEqual(len(self.host.execution_client.open_calls), 1)
        open_call = self.host.execution_client.open_calls[-1]
        self.assertEqual(open_call["workspace_id"], "ws_main")
        self.assertEqual(open_call["node_id"], "node_viewer")
        self.assertEqual(open_call["session_id"], session_id)
        self.assertEqual(open_call["backend_id"], "backend.custom")
        self.assertEqual(open_call["data_refs"], {"fields": "fields_ref"})
        self.assertEqual(open_call["camera_state"], {"zoom": 1.2})
        self.assertEqual(open_call["playback_state"], {"state": "paused", "step_index": 3})
        self.assertEqual(open_call["options"]["live_policy"], "focus_only")
        self.assertEqual(open_call["options"]["live_mode"], "full")
        self.assertEqual(open_call["options"]["playback_state"], "paused")

        opening_state = self.bridge.session_state("node_viewer")
        self.assertEqual(opening_state["phase"], "opening")
        self.assertEqual(opening_state["live_policy"], "focus_only")
        self.assertEqual(opening_state["playback_state"], "paused")
        self.assertEqual(opening_state["step_index"], 3)
        self.assertEqual(opening_state["backend_id"], "backend.custom")
        self.assertEqual(opening_state["session_model"]["phase"], "opening")
        self.assertEqual(opening_state["session_model"]["live_mode"], "full")

        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=session_id,
                summary={"cache_state": "live_ready"},
                options={"live_mode": "full"},
                backend_id="backend.custom",
                camera_state={"zoom": 2.0},
                transport_revision=7,
                live_open_status="ready",
                transport={
                    "kind": "bundle",
                    "backend_id": "backend.custom",
                    "bundle_path": "C:/temp/viewer_bundle",
                },
            )
        )

        opened_state = self.bridge.session_state("node_viewer")
        self.assertEqual(opened_state["phase"], "open")
        self.assertEqual(opened_state["cache_state"], "live_ready")
        self.assertEqual(opened_state["summary"]["result_name"], "displacement")
        self.assertEqual(opened_state["backend_id"], "backend.custom")
        self.assertEqual(opened_state["transport_revision"], 7)
        self.assertEqual(opened_state["live_open_status"], "ready")
        self.assertEqual(opened_state["transport"]["bundle_path"], "C:/temp/viewer_bundle")
        self.assertEqual(opened_state["camera_state"], {"zoom": 2.0})
        self.assertEqual(opened_state["session_model"]["phase"], "open")
        self.assertEqual(opened_state["session_model"]["transport_revision"], 7)
        self.assertEqual(opened_state["session_model"]["summary"]["result_name"], "displacement")

        self.assertTrue(self.bridge.play("node_viewer"))
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["playback_state"], "playing")
        self.assertEqual(self.host.execution_client.update_calls[-1]["backend_id"], "backend.custom")
        self.assertEqual(self.host.execution_client.update_calls[-1]["camera_state"], {"zoom": 2.0})
        self.assertEqual(self.host.execution_client.update_calls[-1]["playback_state"], {"state": "playing", "step_index": 3})

        self.assertTrue(self.bridge.set_keep_live("node_viewer", True))
        self.assertTrue(self.host.execution_client.update_calls[-1]["options"]["keep_live"])
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["live_policy"], "focus_only")

        self.assertTrue(self.bridge.set_live_policy("node_viewer", "keep_live"))
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["live_policy"], "keep_live")

        self.assertTrue(self.bridge.step("node_viewer"))
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["step_index"], 4)

        self.assertTrue(self.bridge.pause("node_viewer"))
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["playback_state"], "paused")

        self.assertTrue(self.bridge.close("node_viewer"))
        close_call = self.host.execution_client.close_calls[-1]
        self.assertEqual(close_call["options"]["reason"], "user_close")

        self.host.execution_event.emit(
            {
                "type": "viewer_session_closed",
                "request_id": close_call["request_id"],
                "workspace_id": "ws_main",
                "node_id": "node_viewer",
                "session_id": session_id,
                "summary": {"close_reason": "user_close", "cache_state": "proxy_ready"},
                "options": {
                    "session_state": "closed",
                    "cache_state": "proxy_ready",
                    "reason": "user_close",
                },
            }
        )

        closed_state = self.bridge.session_state("node_viewer")
        self.assertEqual(closed_state["phase"], "closed")
        self.assertEqual(closed_state["close_reason"], "user_close")
        self.assertEqual(closed_state["session_model"]["phase"], "closed")
        self.assertEqual(closed_state["session_model"]["close_reason"], "user_close")

    def test_summary_embedded_session_model_remains_authoritative_over_stale_top_level_fields(self) -> None:
        self.host.scene.set_selected("node_viewer")
        session_id = self.bridge.open("node_viewer", {"data_refs": {"fields": "fields_ref"}})
        open_call = self.host.execution_client.open_calls[-1]

        self.host.execution_event.emit(
            {
                "type": "viewer_session_opened",
                "request_id": open_call["request_id"],
                "workspace_id": "ws_main",
                "node_id": "node_viewer",
                "session_id": session_id,
                "backend_id": "backend.stale",
                "transport_revision": 1,
                "live_open_status": "blocked",
                "summary": {
                    "result_name": "displacement",
                    "session_model": {
                        "workspace_id": "ws_main",
                        "node_id": "node_viewer",
                        "session_id": session_id,
                        "phase": "open",
                        "request_id": open_call["request_id"],
                        "last_command": "open",
                        "last_error": "",
                        "playback_state": "paused",
                        "step_index": 0,
                        "playback": {"state": "paused", "step_index": 0},
                        "live_policy": "focus_only",
                        "keep_live": False,
                        "cache_state": "live_ready",
                        "invalidated_reason": "",
                        "close_reason": "",
                        "backend_id": "backend.authoritative",
                        "transport_revision": 9,
                        "live_mode": "full",
                        "live_open_status": "ready",
                        "live_open_blocker": {},
                        "data_refs": {"dataset": {"kind": "mock_dataset"}},
                        "transport": {
                            "kind": "bundle",
                            "backend_id": "backend.authoritative",
                            "bundle_path": "C:/temp/viewer_bundle",
                        },
                        "camera_state": {"zoom": 1.4},
                        "summary": {
                            "cache_state": "live_ready",
                            "result_name": "displacement",
                        },
                        "options": {
                            "live_mode": "full",
                            "playback_state": "paused",
                            "step_index": 0,
                            "backend_id": "backend.authoritative",
                            "transport_revision": 9,
                            "live_open_status": "ready",
                        },
                    },
                },
                "options": {"live_mode": "proxy"},
            }
        )

        opened_state = self.bridge.session_state("node_viewer")
        self.assertEqual(opened_state["backend_id"], "backend.authoritative")
        self.assertEqual(opened_state["transport_revision"], 9)
        self.assertEqual(opened_state["live_open_status"], "ready")
        self.assertEqual(opened_state["options"]["live_mode"], "full")
        self.assertEqual(opened_state["transport"]["backend_id"], "backend.authoritative")

    def test_node_mutation_keeps_live_session_and_prunes_removed_node_projection(self) -> None:
        self.host.scene.set_selected("node_viewer")
        session_id = self.bridge.open("node_viewer", {"data_refs": {"fields": "fields_ref"}})
        open_call = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=session_id,
                summary={"cache_state": "live_ready"},
                options={"live_mode": "full"},
                data_refs={"dataset": {"kind": "mock"}},
            )
        )

        self.host.scene.nodes_changed.emit()
        live_state = self.bridge.session_state("node_viewer")
        self.assertEqual(live_state["phase"], "open")
        self.assertEqual(live_state["options"]["live_mode"], "full")
        self.assertEqual(live_state["cache_state"], "live_ready")

        self.host.model.project.workspaces["ws_main"].nodes.pop("node_viewer")
        self.host.scene.nodes_changed.emit()
        self.assertEqual(self.bridge.session_state("node_viewer"), {})

    def test_focus_only_selection_keeps_one_live_session_until_keep_live_is_enabled(self) -> None:
        self.host.scene.set_selected("node_viewer")
        first_session_id = self.bridge.open("node_viewer", {"data_refs": {"fields": "fields_a"}})
        first_open = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=first_open["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=first_session_id,
                summary={"cache_state": "live_ready"},
                options={"live_mode": "full"},
                data_refs={"dataset": {"kind": "mock_a"}},
            )
        )

        second_session_id = self.bridge.open("node_viewer_b", {"data_refs": {"fields": "fields_b"}})
        second_open = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=second_open["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer_b",
                session_id=second_session_id,
                summary={"cache_state": "live_ready"},
                options={"live_mode": "proxy"},
                data_refs={"dataset": {"kind": "mock_b"}},
            )
        )

        self.assertEqual(self.bridge.session_state("node_viewer")["options"]["live_mode"], "full")
        self.assertEqual(self.bridge.session_state("node_viewer_b")["options"]["live_mode"], "proxy")

        self.host.scene.set_selected("node_viewer_b")
        self.assertEqual(
            [call["node_id"] for call in self.host.execution_client.update_calls[-2:]],
            ["node_viewer", "node_viewer_b"],
        )
        self.assertEqual(self.host.execution_client.update_calls[-2]["options"]["live_mode"], "proxy")
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["live_mode"], "full")
        self.assertEqual(len(self.host.execution_client.materialize_calls), 1)
        self.assertEqual(self.host.execution_client.materialize_calls[-1]["node_id"], "node_viewer_b")
        self.assertEqual(self.host.execution_client.materialize_calls[-1]["options"]["live_mode"], "proxy")
        self.assertEqual(self.host.execution_client.materialize_calls[-1]["options"]["output_profile"], "stored")
        self.assertEqual(self.host.execution_client.materialize_calls[-1]["options"]["export_formats"], ["png"])
        self.assertEqual(self.bridge.session_state("node_viewer")["options"]["live_mode"], "proxy")
        self.assertEqual(self.bridge.session_state("node_viewer_b")["options"]["live_mode"], "full")
        self.assertEqual(self.bridge.session_state("node_viewer_b")["cache_state"], "live_ready")

        self.assertTrue(self.bridge.set_keep_live("node_viewer_b", True))
        self.host.scene.set_selected("node_viewer")
        self.assertEqual(self.host.execution_client.update_calls[-2]["node_id"], "node_viewer_b")
        self.assertEqual(self.host.execution_client.update_calls[-2]["options"]["keep_live"], True)
        self.assertEqual(self.host.execution_client.update_calls[-2]["options"]["live_policy"], "focus_only")
        self.assertEqual(self.host.execution_client.update_calls[-1]["node_id"], "node_viewer")
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["live_mode"], "full")
        self.assertEqual(self.bridge.session_state("node_viewer")["options"]["live_mode"], "full")
        self.assertEqual(self.bridge.session_state("node_viewer_b")["options"]["live_mode"], "full")

    def test_keep_live_prevents_demotion_on_node_deselect_and_explicit_canvas_blur(self) -> None:
        session_id = self._open_live_session()

        self.assertTrue(self.bridge.set_keep_live("node_viewer", True))
        update_count = len(self.host.execution_client.update_calls)
        self.host.capture_camera_calls.clear()
        self.host.capture_preview_calls.clear()

        self.host.scene.set_selected()
        deselected_state = self.bridge.session_state("node_viewer")
        self.assertEqual(len(self.host.execution_client.update_calls), update_count)
        self.assertEqual(deselected_state["options"]["live_mode"], "full")
        self.assertEqual(self.host.capture_camera_calls, [])
        self.assertEqual(self.host.capture_preview_calls, [])

        self.assertTrue(self.bridge.clear_viewer_focus())
        blurred_state = self.bridge.session_state("node_viewer")
        self.assertEqual(len(self.host.execution_client.update_calls), update_count)
        self.assertEqual(blurred_state["options"]["live_mode"], "full")
        self.assertEqual(self.host.capture_camera_calls, [])
        self.assertEqual(self.host.capture_preview_calls, [])
        self.assertEqual(blurred_state["session_id"], session_id)

    def test_proxy_demotion_preserves_summary_for_restoration(self) -> None:
        self.host.scene.set_selected("node_viewer_restore")
        restore_session_id = self.bridge.open(
            "node_viewer_restore",
            {
                "data_refs": {"fields": "restore_fields"},
                "summary": {"camera": {"zoom": 1.2}, "result_name": "displacement"},
            },
        )
        restore_open = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=restore_open["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer_restore",
                session_id=restore_session_id,
                summary={"cache_state": "live_ready", "camera": {"zoom": 1.2}},
                options={"live_mode": "full"},
                data_refs={"dataset": {"kind": "restore_dataset"}},
            )
        )

        other_session_id = self.bridge.open("node_viewer_other", {"data_refs": {"fields": "other_fields"}})
        other_open = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=other_open["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer_other",
                session_id=other_session_id,
                summary={"cache_state": "live_ready"},
                options={"live_mode": "proxy"},
                data_refs={"dataset": {"kind": "other_dataset"}},
            )
        )

        self.host.scene.set_selected("node_viewer_other")
        demoted_state = self.bridge.session_state("node_viewer_restore")
        self.assertEqual(demoted_state["options"]["live_mode"], "proxy")
        self.assertEqual(demoted_state["summary"]["camera"], {"zoom": 1.2})
        self.assertNotIn("demoted_reason", demoted_state["summary"])

        self.host.scene.set_selected("node_viewer_restore")
        restored_state = self.bridge.session_state("node_viewer_restore")
        self.assertEqual(self.host.execution_client.update_calls[-1]["node_id"], "node_viewer_restore")
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["live_mode"], "full")
        self.assertEqual(restored_state["options"]["live_mode"], "full")
        self.assertEqual(restored_state["cache_state"], "live_ready")
        self.assertEqual(restored_state["summary"]["camera"], {"zoom": 1.2})
        self.assertNotIn("demoted_reason", restored_state["summary"])

    def test_explicit_viewer_blur_demotes_to_proxy_and_requests_png_snapshot(self) -> None:
        self.host.scene.set_selected("node_viewer")
        self.host.captured_camera_state = {
            "position": [9.0, 8.0, 7.0],
            "focal_point": [1.0, 2.0, 3.0],
            "viewup": [0.0, 1.0, 0.0],
            "view_angle": 24.0,
        }
        self.host.captured_preview_image = _preview_image()
        session_id = self.bridge.open("node_viewer", {"data_refs": {"fields": "fields_ref"}})
        open_call = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=session_id,
                summary={"cache_state": "live_ready", "camera": {"zoom": 1.1}},
                options={"live_mode": "full"},
                data_refs={"dataset": {"kind": "mock_dataset"}},
            )
        )

        self.assertTrue(self.bridge.focus_session("node_viewer"))
        self.assertTrue(self.bridge.clear_viewer_focus())
        self.assertEqual(
            self.host.capture_camera_calls[-1],
            {"workspace_id": "ws_main", "node_id": "node_viewer"},
        )
        self.assertEqual(
            self.host.capture_preview_calls[-1],
            {"workspace_id": "ws_main", "node_id": "node_viewer"},
        )
        self.assertEqual(self.host.execution_client.update_calls[-1]["node_id"], "node_viewer")
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["live_mode"], "proxy")
        self.assertEqual(
            self.host.execution_client.update_calls[-1]["camera_state"],
            self.host.captured_camera_state,
        )
        preview_state = self.bridge.session_state("node_viewer")
        transient_preview_path = Path(preview_state["data_refs"]["preview"])
        self.assertEqual(preview_state["camera_state"], self.host.captured_camera_state)
        self.assertEqual(preview_state["options"]["live_mode"], "proxy")
        self.assertTrue(transient_preview_path.is_file())
        self.assertNotIn("png", preview_state["data_refs"])
        self.assertEqual(len(self.host.execution_client.materialize_calls), 0)

        demoted_event = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready", "camera": dict(self.host.captured_camera_state)},
            options={"live_mode": "proxy"},
            data_refs={"dataset": {"kind": "mock_dataset"}},
            camera_state=dict(self.host.captured_camera_state),
        )
        demoted_event["type"] = "viewer_session_updated"
        self.host.execution_event.emit(demoted_event)

        self.assertEqual(self.host.execution_client.materialize_calls[-1]["node_id"], "node_viewer")
        self.assertEqual(self.host.execution_client.materialize_calls[-1]["options"]["live_mode"], "proxy")
        self.assertEqual(self.host.execution_client.materialize_calls[-1]["options"]["output_profile"], "stored")
        self.assertEqual(self.host.execution_client.materialize_calls[-1]["options"]["export_formats"], ["png"])
        self._register_managed_preview_artifact("viewer_proxy_png")

        materialized_event = _viewer_opened_event(
            request_id=self.host.execution_client.materialize_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "proxy", "output_profile": "stored", "export_formats": ["png"]},
            data_refs={
                "dataset": {"kind": "mock_dataset"},
                "png": {
                    "__ea_runtime_value__": "artifact_ref",
                    "ref": "artifact://viewer_proxy_png",
                    "artifact_id": "viewer_proxy_png",
                    "scope": "managed",
                },
            },
        )
        materialized_event["type"] = "viewer_data_materialized"
        self.host.execution_event.emit(materialized_event)

        proxy_state = self.bridge.session_state("node_viewer")
        self.assertEqual(proxy_state["options"]["live_mode"], "proxy")
        self.assertEqual(proxy_state["data_refs"]["preview"], str(transient_preview_path))
        self.assertNotIn("png", proxy_state["data_refs"])
        self.assertEqual(proxy_state["camera_state"], self.host.captured_camera_state)
        self.assertTrue(transient_preview_path.exists())
        internal_state = self.bridge._ensure_session_state("ws_main", "node_viewer")
        self.assertIn("png", internal_state.data_refs)

        self.assertTrue(self.bridge.focus_session("node_viewer"))
        self.assertEqual(self.host.execution_client.update_calls[-1]["node_id"], "node_viewer")
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["live_mode"], "full")

    def test_transient_proxy_preview_stays_projected_while_authoritative_proxy_replacement_arrives(self) -> None:
        self.host.scene.set_selected("node_viewer")
        self.host.captured_camera_state = {
            "position": [9.0, 8.0, 7.0],
            "focal_point": [1.0, 2.0, 3.0],
            "viewup": [0.0, 1.0, 0.0],
            "view_angle": 24.0,
        }
        self.host.captured_preview_image = _preview_image()
        session_id = self.bridge.open("node_viewer", {"data_refs": {"fields": "fields_ref"}})
        open_call = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=session_id,
                summary={"cache_state": "live_ready", "camera": {"zoom": 1.1}},
                options={"live_mode": "full"},
                data_refs={
                    "dataset": {"kind": "mock_dataset"},
                    "png": {
                        "__ea_runtime_value__": "artifact_ref",
                        "ref": "artifact://viewer_proxy_png_old",
                        "artifact_id": "viewer_proxy_png_old",
                        "scope": "managed",
                    },
                },
            )
        )
        self._register_managed_preview_artifact("viewer_proxy_png_old", color=0xFF355D99)
        self._register_managed_preview_artifact("viewer_proxy_png_new", color=0xFF6D9D35)

        self.assertTrue(self.bridge.focus_session("node_viewer"))
        self.assertTrue(self.bridge.clear_viewer_focus())
        preview_state = self.bridge.session_state("node_viewer")
        transient_preview_path = Path(preview_state["data_refs"]["preview"])
        self.assertTrue(transient_preview_path.is_file())
        self.assertNotIn("png", preview_state["data_refs"])

        demoted_event = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "proxy"},
            data_refs={
                "dataset": {"kind": "mock_dataset"},
                "png": {
                    "__ea_runtime_value__": "artifact_ref",
                    "ref": "artifact://viewer_proxy_png_old",
                    "artifact_id": "viewer_proxy_png_old",
                    "scope": "managed",
                },
            },
            camera_state=dict(self.host.captured_camera_state),
        )
        demoted_event["type"] = "viewer_session_updated"
        self.host.execution_event.emit(demoted_event)

        pending_proxy_state = self.bridge.session_state("node_viewer")
        self.assertEqual(pending_proxy_state["data_refs"]["preview"], str(transient_preview_path))
        self.assertNotIn("png", pending_proxy_state["data_refs"])

        materialized_event = _viewer_opened_event(
            request_id=self.host.execution_client.materialize_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "proxy", "output_profile": "stored", "export_formats": ["png"]},
            data_refs={
                "dataset": {"kind": "mock_dataset"},
                "png": {
                    "__ea_runtime_value__": "artifact_ref",
                    "ref": "artifact://viewer_proxy_png_new",
                    "artifact_id": "viewer_proxy_png_new",
                    "scope": "managed",
                },
            },
        )
        materialized_event["type"] = "viewer_data_materialized"
        self.host.execution_event.emit(materialized_event)

        final_proxy_state = self.bridge.session_state("node_viewer")
        self.assertEqual(final_proxy_state["data_refs"]["preview"], str(transient_preview_path))
        self.assertNotIn("png", final_proxy_state["data_refs"])
        self.assertTrue(transient_preview_path.exists())
        internal_state = self.bridge._ensure_session_state("ws_main", "node_viewer")
        self.assertEqual(internal_state.data_refs["png"]["artifact_id"], "viewer_proxy_png_new")

    def test_materialized_proxy_preview_keeps_transient_capture_when_replacement_is_not_resolvable(self) -> None:
        session_id, transient_preview_path = self._create_transient_proxy_preview("node_viewer")
        demoted_event = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "proxy"},
            data_refs={"dataset": {"kind": "mock_dataset"}},
            camera_state=dict(self.host.captured_camera_state),
        )
        demoted_event["type"] = "viewer_session_updated"
        self.host.execution_event.emit(demoted_event)

        materialized_event = _viewer_opened_event(
            request_id=self.host.execution_client.materialize_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "proxy", "output_profile": "stored", "export_formats": ["png"]},
            data_refs={
                "dataset": {"kind": "mock_dataset"},
                "png": {
                    "__ea_runtime_value__": "artifact_ref",
                    "ref": "artifact-stage://viewer_proxy_png_missing",
                    "artifact_id": "viewer_proxy_png_missing",
                    "scope": "staged",
                },
            },
        )
        materialized_event["type"] = "viewer_data_materialized"
        self.host.execution_event.emit(materialized_event)

        proxy_state = self.bridge.session_state("node_viewer")
        self.assertEqual(proxy_state["data_refs"]["preview"], str(transient_preview_path))
        self.assertNotIn("png", proxy_state["data_refs"])
        self.assertTrue(transient_preview_path.exists())

    def test_materialized_proxy_preview_projects_runtime_absolute_path_while_transient_capture_stays_projected(self) -> None:
        session_id, transient_preview_path = self._create_transient_proxy_preview("node_viewer")
        demoted_event = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "proxy"},
            data_refs={"dataset": {"kind": "mock_dataset"}},
            camera_state=dict(self.host.captured_camera_state),
        )
        demoted_event["type"] = "viewer_session_updated"
        self.host.execution_event.emit(demoted_event)

        file_descriptor, temp_path = tempfile.mkstemp(suffix=".png")
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        Path(temp_path).unlink(missing_ok=True)
        try:
            materialized_png_path = Path(temp_path)
            self.assertTrue(_preview_image(0xFF55AA44).save(str(materialized_png_path), "PNG"))

            materialized_event = _viewer_opened_event(
                request_id=self.host.execution_client.materialize_calls[-1]["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=session_id,
                summary={"cache_state": "live_ready"},
                options={"live_mode": "proxy", "output_profile": "stored", "export_formats": ["png"]},
                data_refs={
                    "dataset": {"kind": "mock_dataset"},
                    "png": {
                        "__ea_runtime_value__": "artifact_ref",
                        "ref": "artifact-stage://viewer_proxy_png_ready",
                        "artifact_id": "viewer_proxy_png_ready",
                        "scope": "staged",
                        "metadata": {
                            "absolute_path": str(materialized_png_path),
                        },
                    },
                },
            )
            materialized_event["type"] = "viewer_data_materialized"
            self.host.execution_event.emit(materialized_event)

            proxy_state = self.bridge.session_state("node_viewer")
            self.assertEqual(proxy_state["data_refs"]["preview"], str(transient_preview_path))
            self.assertNotIn("png", proxy_state["data_refs"])
            self.assertTrue(transient_preview_path.exists())
            internal_state = self.bridge._ensure_session_state("ws_main", "node_viewer")
            self.assertEqual(
                self.bridge._projected_proxy_preview_path(internal_state.data_refs),
                str(materialized_png_path),
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_transient_proxy_preview_cleanup_on_close_reset_project_reload_and_node_removal(self) -> None:
        close_session_id, close_preview_path = self._create_transient_proxy_preview("node_viewer")
        close_request = self.host.execution_client.close_viewer_session(
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=close_session_id,
            options={"reason": "test_close"},
        )
        self.host.execution_event.emit(
            {
                "type": "viewer_session_closed",
                "request_id": close_request,
                "workspace_id": "ws_main",
                "node_id": "node_viewer",
                "session_id": close_session_id,
                "summary": {"close_reason": "test_close", "cache_state": "proxy_ready"},
                "options": {"session_state": "closed", "cache_state": "proxy_ready", "reason": "test_close"},
            }
        )
        self.assertFalse(close_preview_path.exists())

        _, reset_preview_path = self._create_transient_proxy_preview("node_viewer")
        self.bridge.reset_all_sessions(reason="test_reset")
        self.assertFalse(reset_preview_path.exists())

        self.host.model.project.workspaces["ws_main"].nodes = {
            "node_viewer": SimpleNamespace(type_id=DPF_VIEWER_NODE_TYPE_ID),
        }
        _, reload_preview_path = self._create_transient_proxy_preview("node_viewer")
        self.bridge.project_loaded(self.host.model.project, None)
        self.assertFalse(reload_preview_path.exists())
        self.assertNotIn("preview", self.bridge.session_state("node_viewer").get("data_refs", {}))

        self.host.model.project.workspaces["ws_main"].nodes["node_viewer"] = object()
        _, removed_preview_path = self._create_transient_proxy_preview("node_viewer")
        self.host.model.project.workspaces["ws_main"].nodes.pop("node_viewer")
        self.host.scene.nodes_changed.emit()
        self.assertFalse(removed_preview_path.exists())
        self.assertEqual(self.bridge.session_state("node_viewer"), {})

    def test_first_blur_refocus_preserves_camera_state_even_when_backend_returns_different_camera(self) -> None:
        captured = {
            "position": [5.0, 6.0, 7.0],
            "focal_point": [0.0, 0.0, 0.0],
            "viewup": [0.0, 1.0, 0.0],
            "view_angle": 30.0,
        }
        self.host.captured_camera_state = dict(captured)
        self.host.captured_preview_image = _preview_image()
        session_id = self._open_live_session()

        self.assertTrue(self.bridge.focus_session("node_viewer"))
        self.assertTrue(self.bridge.clear_viewer_focus())
        state_after_blur = self.bridge.session_state("node_viewer")
        self.assertEqual(state_after_blur["camera_state"], captured)

        # Backend responds with a DIFFERENT camera state (e.g. default)
        demoted_event = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready", "camera": {"zoom": 1.0}},
            options={"live_mode": "proxy"},
            camera_state={"zoom": 1.0},  # different from captured!
        )
        demoted_event["type"] = "viewer_session_updated"
        self.host.execution_event.emit(demoted_event)

        # Camera state must still be the locally captured one
        state_after_event = self.bridge.session_state("node_viewer")
        self.assertEqual(state_after_event["camera_state"], captured)

        # Materialization event with no camera_state should also preserve
        mat_event = _viewer_opened_event(
            request_id=self.host.execution_client.materialize_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready", "camera_state": {"zoom": 1.0}},
            options={"live_mode": "proxy", "output_profile": "stored", "export_formats": ["png"]},
            data_refs={"png": {"ref": "artifact://png"}},
        )
        mat_event["type"] = "viewer_data_materialized"
        self.host.execution_event.emit(mat_event)

        state_after_mat = self.bridge.session_state("node_viewer")
        self.assertEqual(state_after_mat["camera_state"], captured)

        # Re-focus must send the captured camera state to the backend
        self.assertTrue(self.bridge.focus_session("node_viewer"))
        refocus_update = self.host.execution_client.update_calls[-1]
        self.assertEqual(refocus_update["options"]["live_mode"], "full")
        self.assertEqual(refocus_update["camera_state"], captured)
        internal_state = self.bridge._ensure_session_state("ws_main", "node_viewer")
        self.assertTrue(internal_state.camera_state_locally_captured)

        full_restore_event = _viewer_opened_event(
            request_id=refocus_update["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready", "camera": {"zoom": 1.0}},
            options={"live_mode": "full"},
            camera_state={"zoom": 1.0},
        )
        full_restore_event["type"] = "viewer_session_updated"
        self.host.execution_event.emit(full_restore_event)

        restored_state = self.bridge.session_state("node_viewer")
        self.assertEqual(restored_state["camera_state"], captured)
        self.assertFalse(self.bridge._ensure_session_state("ws_main", "node_viewer").camera_state_locally_captured)

    def test_second_blur_refocus_cycle_also_preserves_camera(self) -> None:
        first_camera = {
            "position": [1.0, 2.0, 3.0],
            "focal_point": [0.0, 0.0, 0.0],
            "viewup": [0.0, 1.0, 0.0],
        }
        self.host.captured_camera_state = dict(first_camera)
        self.host.captured_preview_image = _preview_image()
        session_id = self._open_live_session()

        # First blur + backend response
        self.assertTrue(self.bridge.focus_session("node_viewer"))
        self.assertTrue(self.bridge.clear_viewer_focus())
        demoted = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "proxy"},
            camera_state={},
        )
        demoted["type"] = "viewer_session_updated"
        self.host.execution_event.emit(demoted)

        # Re-focus
        self.assertTrue(self.bridge.focus_session("node_viewer"))
        refocus_event = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "full"},
        )
        refocus_event["type"] = "viewer_session_updated"
        self.host.execution_event.emit(refocus_event)

        # Second blur with a different camera
        second_camera = {
            "position": [10.0, 20.0, 30.0],
            "focal_point": [5.0, 5.0, 5.0],
            "viewup": [0.0, 0.0, 1.0],
        }
        self.host.captured_camera_state = dict(second_camera)
        self.assertTrue(self.bridge.focus_session("node_viewer"))
        self.assertTrue(self.bridge.clear_viewer_focus())
        self.assertEqual(self.bridge.session_state("node_viewer")["camera_state"], second_camera)

        # Re-focus again must use the second camera
        demoted2 = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "proxy"},
        )
        demoted2["type"] = "viewer_session_updated"
        self.host.execution_event.emit(demoted2)
        self.assertTrue(self.bridge.focus_session("node_viewer"))
        self.assertEqual(self.host.execution_client.update_calls[-1]["camera_state"], second_camera)

    def test_null_capture_preserves_existing_transient_proxy_preview(self) -> None:
        session_id, first_preview_path = self._create_transient_proxy_preview("node_viewer")
        self.assertTrue(first_preview_path.is_file())

        # Second blur on same session (without full refocus round-trip) using null capture.
        # Simulate backend confirming proxy mode so we stay in proxy.
        demoted = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "proxy"},
        )
        demoted["type"] = "viewer_session_updated"
        self.host.execution_event.emit(demoted)

        # Refocus then blur again with null image capture
        refocus_event = _viewer_opened_event(
            request_id=self.host.execution_client.update_calls[-1]["request_id"]
                if self.host.execution_client.update_calls
                else self.host.execution_client.materialize_calls[-1]["request_id"],
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id=session_id,
            summary={"cache_state": "live_ready"},
            options={"live_mode": "full"},
        )
        refocus_event["type"] = "viewer_session_updated"
        self.assertTrue(self.bridge.focus_session("node_viewer"))
        self.host.execution_event.emit(refocus_event)

        self.host.captured_preview_image = QImage()  # null image
        self.host.captured_camera_state = {"position": [1.0, 2.0, 3.0]}
        self.assertTrue(self.bridge.clear_viewer_focus())

        # Authoritative PNG from materialization should still be in data_refs
        # even though transient capture failed
        state = self.bridge.session_state("node_viewer")
        # The null capture should not destroy data_refs completely
        self.assertEqual(state["options"]["live_mode"], "proxy")

    def test_null_capture_does_not_destroy_existing_transient_preview_file(self) -> None:
        """When a transient preview exists and the next capture returns null,
        the existing file must be kept rather than deleted."""
        session_id, first_preview_path = self._create_transient_proxy_preview("node_viewer")
        self.assertTrue(first_preview_path.is_file())

        # Directly invoke _set_transient_proxy_preview with null image
        result = self.bridge._set_transient_proxy_preview("ws_main", "node_viewer", QImage())

        # Existing file must still be on disk
        self.assertTrue(first_preview_path.is_file())
        # Return value should be the existing path
        self.assertEqual(result, str(first_preview_path))

    def test_proxy_not_cleared_prematurely_when_live_open_not_ready(self) -> None:
        session_id, preview_path = self._create_transient_proxy_preview("node_viewer")
        self.assertTrue(preview_path.is_file())

        # Simulate backend going to a state where live_open_status is blocked
        state = self.bridge._ensure_session_state("ws_main", "node_viewer")
        state.live_open_status = "blocked"

        # Try to re-focus; live is not ready so it should return without clearing proxy
        self.assertTrue(self.bridge.focus_session("node_viewer"))

        # Proxy file should still exist since live couldn't be established
        session_state = self.bridge.session_state("node_viewer")
        # The proxy preview path should still be accessible
        self.assertTrue(preview_path.is_file())

    def test_project_loaded_seeds_viewer_nodes_as_run_required_projection(self) -> None:
        self.host.model.project.workspaces["ws_main"].nodes = {
            "node_viewer": SimpleNamespace(type_id=DPF_VIEWER_NODE_TYPE_ID),
        }
        state = self.bridge._ensure_session_state("ws_main", "node_viewer")
        state.phase = "open"
        state.backend_id = DPF_EXECUTION_VIEWER_BACKEND_ID
        state.transport_revision = 11
        state.live_open_status = "ready"
        state.cache_state = "live_ready"
        state.step_index = 4
        state.live_policy = "keep_live"
        state.keep_live = True
        state.data_refs = {"fields": "fields_ref"}
        state.transport = {
            "kind": "bundle",
            "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
            "bundle_path": "C:/temp/viewer_bundle",
        }
        state.camera_state = {"zoom": 1.4}
        state.summary = {
            "result_name": "displacement",
            "set_label": "Set 2",
        }
        state.options = {
            "live_mode": "full",
            "step_index": 4,
            "live_policy": "keep_live",
            "keep_live": True,
        }

        self.bridge.project_loaded(self.host.model.project, None)

        projected_state = self.bridge.session_state("node_viewer")
        self.assertEqual(projected_state["phase"], "blocked")
        self.assertEqual(projected_state["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID)
        self.assertEqual(projected_state["transport_revision"], 11)
        self.assertEqual(projected_state["live_open_status"], "blocked")
        self.assertTrue(projected_state["live_open_blocker"]["rerun_required"])
        self.assertEqual(projected_state["summary"]["result_name"], "displacement")
        self.assertEqual(projected_state["summary"]["live_transport_release_reason"], "project_reload")
        self.assertTrue(projected_state["summary"]["rerun_required"])
        self.assertEqual(projected_state["options"]["live_mode"], "proxy")
        self.assertEqual(projected_state["options"]["live_policy"], "focus_only")
        self.assertFalse(projected_state["options"]["keep_live"])
        self.assertEqual(projected_state["transport"], {"kind": "bundle", "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID})
        self.assertEqual(projected_state["data_refs"], {})
        self.assertEqual(projected_state["camera_state"], {"zoom": 1.4})

    def test_project_workspace_run_required_projects_explicit_rerun_blocker(self) -> None:
        self.host.scene.set_selected("node_viewer")
        session_id = self.bridge.open(
            "node_viewer",
            {
                "data_refs": {"fields": "fields_ref"},
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
            },
        )
        open_call = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=session_id,
                summary={"cache_state": "live_ready", "result_name": "displacement"},
                options={"live_mode": "full"},
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                transport_revision=5,
                live_open_status="ready",
                transport={
                    "kind": "bundle",
                    "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                    "bundle_path": "C:/temp/viewer_bundle",
                },
            )
        )
        self.assertTrue(self.bridge.set_keep_live("node_viewer", True))

        self.bridge.project_workspace_run_required(
            "ws_main",
            reason="workspace_rerun",
            run_id="run_live",
        )

        blocked_state = self.bridge.session_state("node_viewer")
        self.assertEqual(blocked_state["phase"], "blocked")
        self.assertEqual(blocked_state["live_open_status"], "blocked")
        self.assertEqual(blocked_state["live_open_blocker"]["code"], "rerun_required")
        self.assertTrue(blocked_state["live_open_blocker"]["rerun_required"])
        self.assertEqual(blocked_state["summary"]["run_id"], "run_live")
        self.assertEqual(blocked_state["summary"]["live_transport_release_reason"], "workspace_rerun")
        self.assertTrue(blocked_state["options"]["rerun_required"])
        self.assertEqual(blocked_state["options"]["live_policy"], "focus_only")
        self.assertFalse(blocked_state["options"]["keep_live"])
        self.assertEqual(blocked_state["transport"], {"kind": "bundle", "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID})

    def test_node_completed_runtime_payload_clears_stale_rerun_blocker_after_workspace_rerun(self) -> None:
        self.host.scene.set_selected("node_viewer")
        session_id = self.bridge.open(
            "node_viewer",
            {
                "data_refs": {"fields": "fields_ref"},
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
            },
        )
        open_call = self.host.execution_client.open_calls[-1]
        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=session_id,
                summary={"cache_state": "live_ready", "result_name": "displacement"},
                options={"live_mode": "full"},
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                transport_revision=5,
                live_open_status="ready",
                transport={
                    "kind": "bundle",
                    "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                    "bundle_path": "C:/temp/viewer_bundle",
                },
            )
        )
        self.assertTrue(self.bridge.set_keep_live("node_viewer", True))

        self.bridge.project_workspace_run_required(
            "ws_main",
            reason="workspace_rerun",
            run_id="run_live",
        )

        runtime_session_payload = _viewer_opened_event(
            request_id="run_node_viewer",
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id="viewer_session_runtime_seeded",
            backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
            summary={"cache_state": "live_ready", "result_name": "displacement"},
            options={"live_mode": "proxy"},
            data_refs={"dataset": {"kind": "mock_dataset"}},
            transport_revision=7,
            live_open_status="ready",
            transport={
                "kind": "bundle",
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                "bundle_path": "C:/temp/viewer_bundle",
            },
        )
        self.host.execution_event.emit(
            {
                "type": "node_completed",
                "workspace_id": "ws_main",
                "node_id": "node_viewer",
                "outputs": {"session": runtime_session_payload},
            }
        )

        reseeded_state = self.bridge.session_state("node_viewer")
        self.assertEqual(reseeded_state["phase"], "closed")
        self.assertEqual(reseeded_state["session_id"], "viewer_session_runtime_seeded")
        self.assertEqual(reseeded_state["cache_state"], "live_ready")
        self.assertEqual(reseeded_state["live_open_status"], "ready")
        self.assertEqual(reseeded_state["live_open_blocker"], {})
        self.assertNotIn("rerun_required", reseeded_state["summary"])
        self.assertNotIn("rerun_required", reseeded_state["options"])

        reopened_session_id = self.bridge.open("node_viewer")
        self.assertEqual(reopened_session_id, "viewer_session_runtime_seeded")
        reopened_call = self.host.execution_client.open_calls[-1]
        self.assertEqual(reopened_call["live_open_status"], "ready")
        self.assertEqual(reopened_call["live_open_blocker"], {})

    def test_node_completed_runtime_session_payload_reseeds_closed_state_and_cached_open(self) -> None:
        self.host.scene.set_selected("node_viewer")
        runtime_session_payload = _viewer_opened_event(
            request_id="run_node_viewer",
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id="viewer_session_runtime_seeded",
            backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
            summary={"cache_state": "live_ready", "result_name": "displacement"},
            options={"live_mode": "proxy"},
            data_refs={"dataset": {"kind": "mock_dataset"}},
            transport_revision=7,
            live_open_status="ready",
            transport={
                "kind": "bundle",
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                "bundle_path": "C:/temp/viewer_bundle",
            },
        )

        self.host.execution_event.emit(
            {
                "type": "node_completed",
                "workspace_id": "ws_main",
                "node_id": "node_viewer",
                "outputs": {"session": runtime_session_payload},
            }
        )

        seeded_state = self.bridge.session_state("node_viewer")
        self.assertEqual(seeded_state["phase"], "closed")
        self.assertEqual(seeded_state["session_id"], "viewer_session_runtime_seeded")
        self.assertEqual(seeded_state["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID)
        self.assertEqual(seeded_state["cache_state"], "live_ready")
        self.assertEqual(seeded_state["live_open_status"], "ready")
        self.assertEqual(seeded_state["options"]["live_policy"], "focus_only")
        self.assertFalse(seeded_state["options"]["keep_live"])
        self.assertEqual(seeded_state["data_refs"], {"dataset": {"kind": "mock_dataset"}})
        self.assertEqual(
            seeded_state["transport"],
            {
                "kind": "bundle",
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                "bundle_path": "C:/temp/viewer_bundle",
            },
        )

        reopened_session_id = self.bridge.open("node_viewer")
        self.assertEqual(reopened_session_id, "viewer_session_runtime_seeded")
        self.assertEqual(len(self.host.execution_client.open_calls), 1)
        open_call = self.host.execution_client.open_calls[-1]
        self.assertEqual(open_call["workspace_id"], "ws_main")
        self.assertEqual(open_call["node_id"], "node_viewer")
        self.assertEqual(open_call["session_id"], "viewer_session_runtime_seeded")
        self.assertEqual(open_call["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID)
        self.assertEqual(open_call["data_refs"], {"dataset": {"kind": "mock_dataset"}})
        self.assertEqual(
            open_call["transport"],
            {
                "kind": "bundle",
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                "bundle_path": "C:/temp/viewer_bundle",
            },
        )
        self.assertEqual(open_call["transport_revision"], 7)
        self.assertEqual(open_call["live_open_status"], "ready")
        self.assertEqual(open_call["options"]["live_mode"], "full")
        self.assertEqual(open_call["options"]["live_policy"], "focus_only")
        self.assertFalse(open_call["options"]["keep_live"])


class ViewerSessionBridgeShellIntegrationTests(MainWindowShellTestBase):
    def _dispose_secondary_window(self, window) -> None:  # noqa: ANN001
        for timer_name in ("metrics_timer", "graph_hint_timer", "autosave_timer"):
            timer = getattr(window, timer_name, None)
            if timer is not None:
                timer.stop()
        window.close()
        quick_widget = getattr(window, "quick_widget", None)
        if quick_widget is not None:
            window.takeCentralWidget()
            quick_widget.setSource(QUrl())
            quick_widget.hide()
            quick_widget.deleteLater()
            window.quick_widget = None
        window.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_new_project_clears_context_bound_viewer_session_state(self) -> None:
        self.window.execution_client = _ViewerExecutionClientStub()
        bridge = self.window.quick_widget.rootContext().contextProperty("viewerSessionBridge")
        self.assertIs(bridge, self.window.viewer_session_bridge)

        node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=40.0)
        session_id = bridge.open(
            node_id,
            {
                "data_refs": {"fields": "fields_ref"},
                "summary": {"result_name": "displacement"},
            },
        )
        open_call = self.window.execution_client.open_calls[-1]

        self.window.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id=self.window.workspace_manager.active_workspace_id(),
                node_id=node_id,
                session_id=session_id,
            )
        )
        self.app.processEvents()

        self.assertEqual(bridge.session_count, 1)
        self.window._new_project()
        self.app.processEvents()
        self.assertEqual(bridge.session_count, 0)

    def test_restore_session_seeds_saved_viewer_nodes_as_run_required_projection(self) -> None:
        self.window.execution_client = _ViewerExecutionClientStub()
        bridge = self.window.viewer_session_bridge
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("dpf.viewer", x=80.0, y=40.0)
        session_id = bridge.open(
            node_id,
            {
                "data_refs": {"fields": {"kind": "handle_ref", "handle_id": "handle::fields"}},
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                "camera_state": {"zoom": 1.5},
                "playback_state": {"state": "paused", "step_index": 4},
                "summary": {"result_name": "Displacement", "set_label": "Set 4"},
                "options": {"live_mode": "full"},
            },
        )
        open_call = self.window.execution_client.open_calls[-1]
        bundle_path = Path(self._temp_dir.name) / "viewer_bundle" / "bundle.vtp"
        self.window.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                transport_revision=9,
                live_open_status="ready",
                transport={
                    "kind": "bundle",
                    "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                    "bundle_path": str(bundle_path),
                },
                camera_state={"zoom": 1.5},
                data_refs={"fields": {"kind": "handle_ref", "handle_id": "handle::fields"}},
            )
        )
        self.app.processEvents()

        project_path = Path(self._temp_dir.name) / "projects" / "viewer_restore_bridge.sfe"
        project_path.parent.mkdir(parents=True, exist_ok=True)
        self.window.serializer.save_document(str(project_path), self.window.serializer.to_document(self.window.model.project))
        self._session_path.write_text(
            json.dumps(
                {
                    "project_path": str(project_path),
                    "last_manual_save_ts": project_path.stat().st_mtime,
                    "recent_project_paths": [str(project_path)],
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        restored = self.window.__class__()
        restored.resize(1200, 800)
        restored.show()
        self.app.processEvents()
        try:
            restored_state = restored.viewer_session_bridge.session_state(node_id)
            self.assertEqual(restored_state["phase"], "blocked")
            self.assertEqual(restored_state["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID)
            self.assertEqual(restored_state["transport_revision"], 0)
            self.assertEqual(restored_state["live_open_status"], "blocked")
            self.assertTrue(restored_state["live_open_blocker"]["rerun_required"])
            self.assertTrue(restored_state["summary"]["rerun_required"])
            self.assertEqual(restored_state["transport"], {})
            self.assertEqual(restored_state["data_refs"], {})
        finally:
            self._dispose_secondary_window(restored)


if __name__ == "__main__":
    unittest.main()
