from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

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
        data_refs: dict[str, Any] | None = None,
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
                "data_refs": dict(data_refs or {}),
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
        data_refs: dict[str, Any] | None = None,
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
                "data_refs": dict(data_refs or {}),
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
        options: dict[str, Any] | None = None,
    ) -> str:
        request_id = self._next_request_id("materialize")
        self.materialize_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
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
        "summary": summary,
        "options": options,
    }
    payload.update(overrides)
    return payload


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

    def test_open_close_and_control_actions_route_through_execution_client_and_track_state(self) -> None:
        self.host.scene.set_selected("node_viewer")
        session_id = self.bridge.open(
            "node_viewer",
            {
                "data_refs": {"fields": "fields_ref"},
                "summary": {"result_name": "displacement"},
                "options": {"live_mode": "proxy"},
            },
        )

        self.assertTrue(session_id.startswith("viewer_session_"))
        self.assertEqual(len(self.host.execution_client.open_calls), 1)
        open_call = self.host.execution_client.open_calls[-1]
        self.assertEqual(open_call["workspace_id"], "ws_main")
        self.assertEqual(open_call["node_id"], "node_viewer")
        self.assertEqual(open_call["session_id"], session_id)
        self.assertEqual(open_call["data_refs"], {"fields": "fields_ref"})
        self.assertEqual(open_call["options"]["live_policy"], "focus_only")
        self.assertEqual(open_call["options"]["live_mode"], "full")
        self.assertEqual(open_call["options"]["playback_state"], "paused")

        opening_state = self.bridge.session_state("node_viewer")
        self.assertEqual(opening_state["phase"], "opening")
        self.assertEqual(opening_state["live_policy"], "focus_only")
        self.assertEqual(opening_state["playback_state"], "paused")

        self.host.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=session_id,
                summary={"cache_state": "live_ready"},
                options={"live_mode": "full"},
            )
        )

        opened_state = self.bridge.session_state("node_viewer")
        self.assertEqual(opened_state["phase"], "open")
        self.assertEqual(opened_state["cache_state"], "live_ready")
        self.assertEqual(opened_state["summary"]["result_name"], "displacement")

        self.assertTrue(self.bridge.play("node_viewer"))
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["playback_state"], "playing")

        self.assertTrue(self.bridge.set_keep_live("node_viewer", True))
        self.assertTrue(self.host.execution_client.update_calls[-1]["options"]["keep_live"])

        self.assertTrue(self.bridge.set_live_policy("node_viewer", "keep_live"))
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["live_policy"], "keep_live")

        self.assertTrue(self.bridge.step("node_viewer"))
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["step_index"], 1)

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

    def test_node_mutation_keeps_live_session_and_removed_node_invalidates_it(self) -> None:
        self.host.scene.set_selected("node_viewer")
        session_id = self.bridge.open("node_viewer")
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
        invalidated_state = self.bridge.session_state("node_viewer")
        self.assertEqual(invalidated_state["phase"], "invalidated")
        self.assertEqual(invalidated_state["invalidated_reason"], "graph_mutation")
        self.assertEqual(invalidated_state["cache_state"], "invalidated")

    def test_focus_only_selection_keeps_one_live_session_until_keep_live_is_enabled(self) -> None:
        self.host.scene.set_selected("node_viewer")
        first_session_id = self.bridge.open("node_viewer")
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

        second_session_id = self.bridge.open("node_viewer_b")
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
        self.assertEqual(self.host.execution_client.materialize_calls, [])
        self.assertEqual(self.bridge.session_state("node_viewer")["options"]["live_mode"], "proxy")
        self.assertEqual(self.bridge.session_state("node_viewer_b")["options"]["live_mode"], "full")
        self.assertEqual(self.bridge.session_state("node_viewer_b")["cache_state"], "live_ready")

        self.assertTrue(self.bridge.set_keep_live("node_viewer_b", True))
        self.host.scene.set_selected("node_viewer")
        self.assertEqual(self.host.execution_client.update_calls[-2]["node_id"], "node_viewer_b")
        self.assertEqual(self.host.execution_client.update_calls[-2]["options"]["keep_live"], True)
        self.assertEqual(self.host.execution_client.update_calls[-1]["node_id"], "node_viewer")
        self.assertEqual(self.host.execution_client.update_calls[-1]["options"]["live_mode"], "full")
        self.assertEqual(self.bridge.session_state("node_viewer")["options"]["live_mode"], "full")
        self.assertEqual(self.bridge.session_state("node_viewer_b")["options"]["live_mode"], "full")

    def test_proxy_demotion_preserves_summary_for_restoration(self) -> None:
        self.host.scene.set_selected("node_viewer_restore")
        restore_session_id = self.bridge.open(
            "node_viewer_restore",
            {
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

        other_session_id = self.bridge.open("node_viewer_other")
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


class ViewerSessionBridgeShellIntegrationTests(MainWindowShellTestBase):
    def test_new_project_clears_context_bound_viewer_session_state(self) -> None:
        self.window.execution_client = _ViewerExecutionClientStub()
        bridge = self.window.quick_widget.rootContext().contextProperty("viewerSessionBridge")
        self.assertIs(bridge, self.window.viewer_session_bridge)

        node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=40.0)
        session_id = bridge.open(node_id, {"summary": {"result_name": "displacement"}})
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


if __name__ == "__main__":
    unittest.main()
