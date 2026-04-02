from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from PyQt6.QtCore import QEvent, QUrl
from PyQt6.QtWidgets import QMessageBox

from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.persistence.artifact_refs import (
    format_managed_artifact_ref,
    format_staged_artifact_ref,
)
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.ui.dialogs.project_save_as_dialog import ProjectSaveAsDialog
from ea_node_editor.ui.shell.window import ShellWindow
from tests.main_window_shell.base import MainWindowShellTestBase

_SCENARIO_ARG = "--scenario"
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _ViewerExecutionClientStub:
    def __init__(self) -> None:
        self.open_calls: list[dict[str, Any]] = []
        self._request_counter = 0

    def _next_request_id(self) -> str:
        self._request_counter += 1
        return f"viewer_open_{self._request_counter}"

    def open_viewer_session(
        self,
        *,
        workspace_id: str,
        node_id: str,
        session_id: str = "",
        backend_id: str = "",
        data_refs: dict[str, Any] | None = None,
        camera_state: dict[str, Any] | None = None,
        playback_state: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        **extra: Any,
    ) -> str:
        request_id = self._next_request_id()
        self.open_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "backend_id": backend_id,
                "data_refs": dict(data_refs or {}),
                "camera_state": dict(camera_state or {}),
                "playback_state": dict(playback_state or {}),
                "summary": dict(summary or {}),
                "options": dict(options or {}),
                "extra": dict(extra),
            }
        )
        return request_id

    def shutdown(self) -> None:
        return None


def _viewer_opened_event(
    *,
    request_id: str,
    workspace_id: str,
    node_id: str,
    session_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    summary = {
        "cache_state": "live_ready",
        "result_name": "Displacement",
        "set_label": "Set 4",
    }
    summary.update(dict(overrides.pop("summary", {})))
    options = {
        "session_state": "open",
        "cache_state": summary["cache_state"],
        "live_policy": "focus_only",
        "keep_live": False,
        "playback_state": "paused",
        "step_index": 4,
        "live_mode": "full",
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


def _run_named_scenario(name: str) -> int:
    suite = unittest.TestSuite([_ShellProjectSessionControllerScenarios(name)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


class _ShellProjectSessionControllerScenarios(MainWindowShellTestBase):
    __test__ = False

    def tearDown(self) -> None:
        app = self.app
        try:
            super().tearDown()
        finally:
            for widget in list(app.topLevelWidgets()):
                widget.close()
                widget.deleteLater()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            gc.collect()

    def _dispose_secondary_window(self, window: ShellWindow) -> None:
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

    def _attach_unsaved_staged_output(self) -> tuple[str, str, Path]:
        artifact_id = "pending_output"
        staged_ref = format_staged_artifact_ref(artifact_id)
        staging_root = self._session_path.parent / "project_artifact_staging" / "project-123"
        staged_path = staging_root / "outputs" / "run.txt"
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.write_text("staged output", encoding="utf-8")
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=40.0, y=60.0)
        self.window.scene.set_node_property(node_id, "source_path", staged_ref)
        self.window.model.project.metadata["artifact_store"] = {
            "staging_root": {
                "kind": "session_temp",
                "absolute_path": str(staging_root),
            },
            "staged": {
                artifact_id: {
                    "relative_path": "outputs/run.txt",
                    "slot": "process_run.stdout",
                }
            },
        }
        self.app.processEvents()
        return node_id, staged_ref, staged_path

    def _write_session_payload(
        self,
        *,
        project_path: str = "",
        last_manual_save_ts: float = 0.0,
        recent_project_paths: list[str] | None = None,
    ) -> None:
        self._session_path.write_text(
            json.dumps(
                {
                    "project_path": project_path,
                    "last_manual_save_ts": last_manual_save_ts,
                    "recent_project_paths": list(recent_project_paths or []),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def _seed_saved_session_from_current_project(self, filename: str) -> tuple[Path, dict[str, object]]:
        project_path = Path(self._temp_dir.name) / "projects" / filename
        project_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_doc = self.window.serializer.to_document(self.window.model.project)
        self.window.serializer.save_document(str(project_path), baseline_doc)
        saved_path = project_path.with_suffix(".sfe")
        self._write_session_payload(
            project_path=str(saved_path),
            last_manual_save_ts=saved_path.stat().st_mtime,
        )
        return saved_path, baseline_doc

    def _assert_absent_or_current_autosave(self, window: ShellWindow) -> None:
        if not self._autosave_path.exists():
            return
        autosave_doc = json.loads(self._autosave_path.read_text(encoding="utf-8"))
        self.assertEqual(autosave_doc, window.serializer.to_document(window.model.project))

    def test_saved_project_reopen_seeds_run_required_viewer_projection_without_persisting_live_transport(self) -> None:
        self.window.execution_client = _ViewerExecutionClientStub()
        bridge = self.window.viewer_session_bridge
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("dpf.viewer", x=80.0, y=60.0)
        session_id = bridge.open(
            node_id,
            {
                "data_refs": {"fields": {"kind": "handle_ref", "handle_id": "handle::fields"}},
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                "camera_state": {"zoom": 1.5},
                "playback_state": {"state": "paused", "step_index": 4},
                "summary": {
                    "result_name": "Displacement",
                    "set_label": "Set 4",
                },
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

        project_path = Path(self._temp_dir.name) / "projects" / "viewer_projection_restore.sfe"
        project_path.parent.mkdir(parents=True, exist_ok=True)
        self.window.serializer.save_document(str(project_path), self.window.serializer.to_document(self.window.model.project))
        saved_text = project_path.read_text(encoding="utf-8")
        self.assertNotIn(str(bundle_path), saved_text)
        self.assertNotIn("bundle_path", saved_text)
        self.assertTrue(self.window._open_project_path(str(project_path)))
        self.app.processEvents()

        reopened_state = bridge.session_state(node_id)
        self.assertEqual(reopened_state["phase"], "blocked")
        self.assertEqual(reopened_state["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID)
        self.assertEqual(reopened_state["transport_revision"], 9)
        self.assertEqual(reopened_state["live_open_status"], "blocked")
        self.assertTrue(reopened_state["live_open_blocker"]["rerun_required"])
        self.assertEqual(reopened_state["summary"]["live_transport_release_reason"], "project_reload")
        self.assertEqual(
            reopened_state["transport"],
            {"kind": "bundle", "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID},
        )
        self.assertEqual(reopened_state["data_refs"], {})

    def test_session_restore_recovers_workspace_order_active_workspace_and_view_camera(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        second_workspace_id = self.window.workspace_manager.create_workspace("Second")
        third_workspace_id = self.window.workspace_manager.create_workspace("Third")
        self.window.workspace_manager.move_workspace(2, 1)
        self.window._refresh_workspace_tabs()

        self.window._switch_workspace(third_workspace_id)
        third_v2_id = self.window.workspace_manager.create_view(third_workspace_id, name="V2")
        self.window._switch_view(third_v2_id)
        self.window.view.set_zoom(1.65)
        self.window.view.centerOn(222.0, -111.0)
        self.window._persist_session()
        self.app.processEvents()

        expected_order = [
            self.window.workspace_tabs.tabData(index)
            for index in range(self.window.workspace_tabs.count())
        ]
        self.assertEqual(expected_order, [first_workspace_id, third_workspace_id, second_workspace_id])

        restored = ShellWindow()
        restored.resize(1200, 800)
        restored.show()
        self.app.processEvents()
        try:
            restored_order = [
                restored.workspace_tabs.tabData(index)
                for index in range(restored.workspace_tabs.count())
            ]
            self.assertEqual(restored_order, expected_order)
            self.assertEqual(restored.workspace_manager.active_workspace_id(), third_workspace_id)
            self.assertEqual(
                restored.model.project.workspaces[third_workspace_id].active_view_id,
                third_v2_id,
            )
            self.assertAlmostEqual(restored.view.zoom, 1.65, places=2)
            self.assertAlmostEqual(restored.view.center_x, 222.0, delta=3.0)
            self.assertAlmostEqual(restored.view.center_y, -111.0, delta=3.0)
        finally:
            self._dispose_secondary_window(restored)

    def test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.start", x=5.0, y=7.0)
        self.app.processEvents()

        self.window._autosave_tick()
        self.assertTrue(self._autosave_path.exists())
        self.assertTrue(self.window.project_session_state.last_autosave_fingerprint)
        session_payload = json.loads(self._session_path.read_text(encoding="utf-8"))
        self.assertNotIn("project_doc", session_payload)

        autosave_doc = json.loads(self._autosave_path.read_text(encoding="utf-8"))
        workspace_docs = {
            workspace["workspace_id"]: workspace for workspace in autosave_doc.get("workspaces", [])
        }
        self.assertIn(workspace_id, workspace_docs)
        saved_nodes = {node["node_id"] for node in workspace_docs[workspace_id].get("nodes", [])}
        self.assertIn(node_id, saved_nodes)

    def test_session_restore_recovers_unsaved_temp_staged_refs_without_autosave(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id, staged_ref, staged_path = self._attach_unsaved_staged_output()
        self.window._persist_session()
        session_payload = json.loads(self._session_path.read_text(encoding="utf-8"))
        self.assertNotIn("project_doc", session_payload)

        restored = ShellWindow()
        restored.resize(1200, 800)
        restored.show()
        self.app.processEvents()
        try:
            restored_workspace = restored.model.project.workspaces[workspace_id]
            self.assertEqual(restored_workspace.nodes[node_id].properties["source_path"], staged_ref)
            store = ProjectArtifactStore.from_project_metadata(
                project_path=restored.project_path,
                project_metadata=restored.model.project.metadata,
            )
            self.assertEqual(store.resolve_staged_path(staged_ref), staged_path)
        finally:
            self._dispose_secondary_window(restored)

    def test_recovery_prompt_accept_loads_newer_autosave(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        _saved_path, _baseline_doc = self._seed_saved_session_from_current_project("recovery_accept.sfe")

        recovered_node_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        recovered_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(recovered_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(ShellWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.Yes):
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[workspace_id]
                self.assertIn(recovered_node_id, restored_workspace.nodes)
                self._assert_absent_or_current_autosave(restored)
            finally:
                self._dispose_secondary_window(restored)

    def test_recovery_prompt_accept_recovers_unsaved_temp_staged_refs(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        _saved_path, _baseline_doc = self._seed_saved_session_from_current_project("recovery_accept_staged.sfe")
        node_id, staged_ref, staged_path = self._attach_unsaved_staged_output()
        autosave_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(autosave_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(ShellWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.Yes):
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[workspace_id]
                self.assertEqual(restored_workspace.nodes[node_id].properties["source_path"], staged_ref)
                store = ProjectArtifactStore.from_project_metadata(
                    project_path=restored.project_path,
                    project_metadata=restored.model.project.metadata,
                )
                self.assertEqual(store.resolve_staged_path(staged_ref), staged_path)
                self._assert_absent_or_current_autosave(restored)
            finally:
                self._dispose_secondary_window(restored)

    def test_recovery_prompt_reject_keeps_session_state_and_discards_autosave(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        baseline_node_id = self.window.scene.add_node_from_type("core.start", x=10.0, y=10.0)
        _saved_path, _baseline_doc = self._seed_saved_session_from_current_project("recovery_reject.sfe")

        self.window.scene.add_node_from_type("core.logger", x=120.0, y=10.0)
        autosave_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(autosave_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(ShellWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.No):
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[workspace_id]
                self.assertIn(baseline_node_id, restored_workspace.nodes)
                self.assertEqual(len(restored_workspace.nodes), 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                self._dispose_secondary_window(restored)

    def test_recovery_prompt_is_skipped_when_autosave_matches_restored_session(self) -> None:
        saved_path, baseline_doc = self._seed_saved_session_from_current_project("recovery_skip_prompt.sfe")
        self._autosave_path.write_text(
            json.dumps(baseline_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(ShellWindow, "_prompt_recover_autosave") as prompt:
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertEqual(prompt.call_count, 0)
                self.assertEqual(restored.project_path, str(saved_path))
            finally:
                self._dispose_secondary_window(restored)

    def test_restore_session_handles_corrupted_session_and_autosave_files(self) -> None:
        self._session_path.write_text("{bad json", encoding="utf-8")
        self._autosave_path.write_text("{bad json", encoding="utf-8")
        os.utime(self._autosave_path, None)

        with patch.object(ShellWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.Yes):
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertGreaterEqual(len(restored.model.project.workspaces), 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                self._dispose_secondary_window(restored)

    def test_recovery_prompt_is_deferred_until_main_window_is_visible(self) -> None:
        _saved_path, _baseline_doc = self._seed_saved_session_from_current_project("recovery_deferred.sfe")

        self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        recovered_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(recovered_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(ShellWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.No) as prompt:
            restored = ShellWindow()
            self.assertEqual(prompt.call_count, 0)
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertGreaterEqual(prompt.call_count, 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                self._dispose_secondary_window(restored)

    def test_clean_close_discards_staged_scratch_and_clears_unsaved_root_hint(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id, staged_ref, staged_path = self._attach_unsaved_staged_output()

        self.window.close()
        self.app.processEvents()

        self.assertFalse(staged_path.exists())
        self.assertFalse(self._autosave_path.exists())

        with patch.object(ShellWindow, "_prompt_recover_autosave") as prompt:
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[
                    restored.workspace_manager.active_workspace_id()
                ]
                self.assertNotIn(node_id, restored_workspace.nodes)
                store = ProjectArtifactStore.from_project_metadata(
                    project_path=restored.project_path,
                    project_metadata=restored.model.project.metadata,
                )
                self.assertIsNone(store.resolve_staged_path(staged_ref))
                self.assertNotIn("staging_root", restored.model.project.metadata.get("artifact_store", {}))
                self.assertEqual(prompt.call_count, 0)
            finally:
                self._dispose_secondary_window(restored)

    def test_explicit_save_promotes_referenced_staged_refs_and_prunes_orphans(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id, _staged_ref, staged_path = self._attach_unsaved_staged_output()
        save_target = Path(self._temp_dir.name) / "projects" / "saved_project"
        save_target.parent.mkdir(parents=True, exist_ok=True)
        saved_path = save_target.with_suffix(".sfe")
        managed_path = saved_path.with_name("saved_project.data") / "artifacts" / "outputs" / "current.txt"
        managed_path.parent.mkdir(parents=True, exist_ok=True)
        managed_path.write_text("old output", encoding="utf-8")
        orphan_path = saved_path.with_name("saved_project.data") / "assets" / "media" / "unused.png"
        orphan_path.parent.mkdir(parents=True, exist_ok=True)
        orphan_path.write_text("orphan", encoding="utf-8")
        self.window.model.project.metadata["artifact_store"]["artifacts"] = {
            "pending_output": {
                "relative_path": "artifacts/outputs/current.txt",
            },
            "orphan_asset": {
                "relative_path": "assets/media/unused.png",
            },
        }

        with patch.object(
            self.window.project_session_controller._project_files_service,
            "prompt_project_files_action",
            return_value=True,
        ), patch(
            "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=(str(save_target), "EA Project (*.sfe)"),
        ):
            self.window._save_project()
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        saved_doc = json.loads(saved_path.read_text(encoding="utf-8"))
        workspace_doc = next(item for item in saved_doc["workspaces"] if item["workspace_id"] == workspace_id)
        saved_node = next(item for item in workspace_doc["nodes"] if item["node_id"] == node_id)

        self.assertEqual(self.window.project_path, str(saved_path))
        self.assertEqual(
            workspace.nodes[node_id].properties["source_path"],
            format_managed_artifact_ref("pending_output"),
        )
        self.assertEqual(
            saved_node["properties"]["source_path"],
            format_managed_artifact_ref("pending_output"),
        )
        self.assertEqual(managed_path.read_text(encoding="utf-8"), "staged output")
        self.assertFalse(staged_path.exists())
        self.assertFalse(orphan_path.exists())
        self.assertEqual(
            saved_doc["metadata"]["artifact_store"],
            {
                "artifacts": {
                    "pending_output": {
                        "relative_path": "artifacts/outputs/current.txt",
                    }
                },
                "staged": {},
            },
        )

    def test_save_as_default_copy_switches_project_path_and_excludes_staging(self) -> None:
        managed_artifact_id = "managed_image"
        managed_ref = format_managed_artifact_ref(managed_artifact_id)
        source_project = Path(self._temp_dir.name) / "projects" / "source_project.sfe"
        managed_path = source_project.with_name("source_project.data") / "assets" / "media" / "diagram.png"
        managed_path.parent.mkdir(parents=True, exist_ok=True)
        managed_path.write_text("managed image", encoding="utf-8")

        staging_root = self._session_path.parent / "project_artifact_staging" / "save-as-project"
        staged_path = staging_root / "outputs" / "run.txt"
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.write_text("staged output", encoding="utf-8")

        self.window.project_path = str(source_project)
        managed_node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=40.0, y=60.0)
        self.window.scene.set_node_property(managed_node_id, "source_path", managed_ref)
        staged_node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=220.0, y=60.0)
        self.window.scene.set_node_property(staged_node_id, "source_path", format_staged_artifact_ref("pending_output"))
        self.window.model.project.metadata["artifact_store"] = {
            "artifacts": {
                managed_artifact_id: {
                    "relative_path": "assets/media/diagram.png",
                }
            },
            "staging_root": {
                "kind": "session_temp",
                "absolute_path": str(staging_root),
            },
            "staged": {
                "pending_output": {
                    "relative_path": "outputs/run.txt",
                    "slot": "process_run.stdout",
                }
            },
        }

        save_target = Path(self._temp_dir.name) / "copies" / "cloned_project"
        stale_managed_path = save_target.with_suffix(".data") / "artifacts" / "stale.txt"
        stale_managed_path.parent.mkdir(parents=True, exist_ok=True)
        stale_managed_path.write_text("stale", encoding="utf-8")
        stale_staging_path = save_target.with_suffix(".data") / ".staging" / "outputs" / "old.txt"
        stale_staging_path.parent.mkdir(parents=True, exist_ok=True)
        stale_staging_path.write_text("stale staging", encoding="utf-8")

        with patch.object(
            self.window.project_session_controller._project_files_service,
            "prompt_project_files_action",
            return_value=True,
        ), patch(
            "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=(str(save_target), "EA Project (*.sfe)"),
        ), patch.object(
            ProjectSaveAsDialog,
            "exec",
            return_value=ProjectSaveAsDialog.DialogCode.Accepted,
        ), patch.object(
            ProjectSaveAsDialog,
            "selected_mode",
            return_value=ProjectSaveAsDialog.SELF_CONTAINED_COPY,
        ):
            self.window._save_project_as()
        self.app.processEvents()

        saved_path = save_target.with_suffix(".sfe")
        saved_doc = json.loads(saved_path.read_text(encoding="utf-8"))
        copied_managed_path = saved_path.with_name("cloned_project.data") / "assets" / "media" / "diagram.png"
        copied_staging_path = saved_path.with_name("cloned_project.data") / ".staging" / "outputs" / "run.txt"

        self.assertEqual(self.window.action_save_project_as.text(), "Save Project As...")
        self.assertEqual(self.window.project_path, str(saved_path))
        self.assertEqual(copied_managed_path.read_text(encoding="utf-8"), "managed image")
        self.assertFalse(copied_staging_path.exists())
        self.assertFalse(stale_managed_path.exists())
        self.assertFalse(stale_staging_path.exists())
        self.assertTrue(staged_path.exists())
        self.assertEqual(
            saved_doc["metadata"]["artifact_store"],
            {
                "artifacts": {
                    managed_artifact_id: {
                        "relative_path": "assets/media/diagram.png",
                    }
                },
                "staged": {},
            },
        )
        workspace_doc = next(
            item for item in saved_doc["workspaces"] if item["workspace_id"] == self.window.workspace_manager.active_workspace_id()
        )
        saved_nodes = {node["node_id"]: node for node in workspace_doc["nodes"]}
        self.assertEqual(saved_nodes[managed_node_id]["properties"]["source_path"], managed_ref)
        self.assertEqual(
            saved_nodes[staged_node_id]["properties"]["source_path"],
            format_staged_artifact_ref("pending_output"),
        )

    def test_recent_project_paths_are_owned_by_explicit_session_state(self) -> None:
        base_path = self._session_path.with_name("packet_recent")
        paths = [
            str(base_path.with_name("alpha")),
            str(base_path.with_name("beta.sfe")),
            str(base_path.with_name("alpha.sfe")),
        ]

        normalized = self.window.project_session_controller.set_recent_project_paths(paths, persist=False)

        self.assertEqual(normalized, [str(base_path.with_name("alpha.sfe")), str(base_path.with_name("beta.sfe"))])
        self.assertEqual(self.window.project_session_state.recent_project_paths, normalized)
        self.assertEqual(self.window.recent_project_paths, normalized)

    def test_new_project_uses_navigation_controller_surface_without_workspace_library_facade(self) -> None:
        original_save_active_view_state = self.window.workspace_navigation_controller.save_active_view_state
        original_refresh_workspace_tabs = self.window.workspace_navigation_controller.refresh_workspace_tabs
        original_switch_workspace = self.window.workspace_navigation_controller.switch_workspace
        save_calls: list[str] = []
        refresh_calls: list[str] = []
        switch_calls: list[str] = []

        def _record_save_active_view_state() -> None:
            save_calls.append("save")
            original_save_active_view_state()

        def _record_refresh_workspace_tabs() -> None:
            refresh_calls.append("refresh")
            original_refresh_workspace_tabs()

        def _record_switch_workspace(workspace_id: str) -> None:
            switch_calls.append(str(workspace_id))
            original_switch_workspace(workspace_id)

        with (
            patch.object(
                self.window.workspace_navigation_controller,
                "save_active_view_state",
                side_effect=_record_save_active_view_state,
            ),
            patch.object(
                self.window.workspace_navigation_controller,
                "refresh_workspace_tabs",
                side_effect=_record_refresh_workspace_tabs,
            ),
            patch.object(
                self.window.workspace_navigation_controller,
                "switch_workspace",
                side_effect=_record_switch_workspace,
            ),
            patch.object(
                self.window.workspace_library_controller,
                "save_active_view_state",
                side_effect=AssertionError("workspace_library_controller.save_active_view_state should not be used"),
            ),
            patch.object(
                self.window.workspace_library_controller,
                "refresh_workspace_tabs",
                side_effect=AssertionError("workspace_library_controller.refresh_workspace_tabs should not be used"),
            ),
            patch.object(
                self.window.workspace_library_controller,
                "switch_workspace",
                side_effect=AssertionError("workspace_library_controller.switch_workspace should not be used"),
            ),
        ):
            self.window.project_session_controller.new_project()
            self.app.processEvents()

        self.assertGreaterEqual(len(save_calls), 1)
        self.assertGreaterEqual(len(refresh_calls), 1)
        self.assertGreaterEqual(len(switch_calls), 1)
        self.assertEqual(self.window.project_path, "")
        self.assertEqual(self.window.model.project.name, "untitled")

    def test_project_files_menu_action_triggers_dialog(self) -> None:
        with patch.object(self.window.project_session_controller, "show_project_files_dialog") as show_dialog:
            self.window.action_project_files.trigger()
            self.app.processEvents()

        self.assertEqual(self.window.action_project_files.text(), "Project Files...")
        self.assertEqual(show_dialog.call_count, 1)

    def test_save_prompt_receives_project_file_summary_before_saving(self) -> None:
        self._attach_unsaved_staged_output()
        missing_path = str(Path(self._temp_dir.name) / "missing-image.png")
        broken_node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=220.0, y=160.0)
        self.window.scene.set_node_property(broken_node_id, "source_path", missing_path)
        save_target = Path(self._temp_dir.name) / "projects" / "prompted_save"

        with patch.object(
            self.window.project_session_controller._project_files_service,
            "prompt_project_files_action",
            return_value=True,
        ) as prompt, patch(
            "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=(str(save_target), "EA Project (*.sfe)"),
        ):
            self.window._save_project()
        self.app.processEvents()

        self.assertEqual(prompt.call_count, 1)
        snapshot = prompt.call_args.kwargs["snapshot"]
        self.assertEqual(snapshot.staged_count, 1)
        self.assertEqual(snapshot.broken_count, 1)

    def test_open_project_path_can_abort_when_project_files_summary_has_staged_and_broken_entries(self) -> None:
        baseline_node_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=20.0)
        self.app.processEvents()

        project_path = Path(self._temp_dir.name) / "projects" / "open_with_summary.sfe"
        staged_path = project_path.with_name("open_with_summary.data") / ".staging" / "outputs" / "run.txt"
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.write_text("staged output", encoding="utf-8")

        model = GraphModel()
        workspace = model.active_workspace
        model.add_node(
            workspace.workspace_id,
            "passive.media.image_panel",
            "Staged",
            80.0,
            60.0,
            properties={"source_path": format_staged_artifact_ref("pending_output")},
        )
        model.add_node(
            workspace.workspace_id,
            "passive.media.image_panel",
            "Broken",
            220.0,
            60.0,
            properties={"source_path": str(Path(self._temp_dir.name) / "missing-open-image.png")},
        )
        model.project.metadata = {
            "artifact_store": {
                "staged": {
                    "pending_output": {
                        "relative_path": ".staging/outputs/run.txt",
                        "slot": "process_run.stdout",
                    }
                }
            }
        }
        self.window.serializer.save_document(str(project_path), self.window.serializer.to_document(model.project))

        with patch.object(
            self.window.project_session_controller._project_files_service,
            "prompt_project_files_action",
            return_value=False,
        ) as prompt:
            result = self.window._open_project_path(str(project_path))
        self.app.processEvents()

        self.assertFalse(result)
        self.assertEqual(prompt.call_count, 1)
        snapshot = prompt.call_args.kwargs["snapshot"]
        self.assertEqual(snapshot.staged_count, 1)
        self.assertEqual(snapshot.broken_count, 1)
        workspace = self.window.model.project.workspaces[self.window.workspace_manager.active_workspace_id()]
        self.assertIn(baseline_node_id, workspace.nodes)

    def test_recovery_prompt_receives_project_file_summary_for_recovered_project(self) -> None:
        recovered_project_path = Path(self._temp_dir.name) / "projects" / "recovered_project.sfe"
        recovered_staging_path = (
            recovered_project_path.with_name("recovered_project.data") / ".staging" / "outputs" / "run.txt"
        )
        recovered_staging_path.parent.mkdir(parents=True, exist_ok=True)
        recovered_staging_path.write_text("staged output", encoding="utf-8")
        self.window.project_path = str(recovered_project_path)

        recovered_model = GraphModel()
        workspace = recovered_model.active_workspace
        recovered_model.add_node(
            workspace.workspace_id,
            "passive.media.image_panel",
            "Recovered Staged",
            80.0,
            60.0,
            properties={"source_path": format_staged_artifact_ref("pending_output")},
        )
        recovered_model.add_node(
            workspace.workspace_id,
            "passive.media.image_panel",
            "Recovered Broken",
            220.0,
            60.0,
            properties={"source_path": str(Path(self._temp_dir.name) / "missing-recovered-image.png")},
        )
        recovered_model.project.metadata = {
            "artifact_store": {
                "staged": {
                    "pending_output": {
                        "relative_path": ".staging/outputs/run.txt",
                        "slot": "process_run.stdout",
                    }
                }
            }
        }

        with patch.object(
            self.window.project_session_controller._project_files_service,
            "prompt_project_files_action",
            return_value=True,
        ) as prompt:
            choice = self.window.project_session_controller.prompt_recover_autosave(recovered_model.project)

        self.assertEqual(choice, QMessageBox.StandardButton.Yes)
        self.assertEqual(prompt.call_count, 1)
        snapshot = prompt.call_args.kwargs["snapshot"]
        self.assertEqual(snapshot.staged_count, 1)
        self.assertEqual(snapshot.broken_count, 1)


class ShellProjectSessionControllerTests(unittest.TestCase):
    maxDiff = None

    def _run_scenario(self, scenario_name: str) -> None:
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        completed = subprocess.run(
            [sys.executable, "-m", "tests.test_shell_project_session_controller", _SCENARIO_ARG, scenario_name],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        output = "\n".join(
            part
            for part in (completed.stdout.strip(), completed.stderr.strip())
            if part
        )
        self.assertEqual(
            completed.returncode,
            0,
            output or f"Scenario {scenario_name} failed without output.",
        )

    def test_session_restore_recovers_workspace_order_active_workspace_and_view_camera(self) -> None:
        self._run_scenario("test_session_restore_recovers_workspace_order_active_workspace_and_view_camera")

    def test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc(self) -> None:
        self._run_scenario("test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc")

    def test_saved_project_reopen_seeds_run_required_viewer_projection_without_persisting_live_transport(self) -> None:
        self._run_scenario("test_saved_project_reopen_seeds_run_required_viewer_projection_without_persisting_live_transport")

    def test_session_restore_recovers_unsaved_temp_staged_refs_without_autosave(self) -> None:
        self._run_scenario("test_session_restore_recovers_unsaved_temp_staged_refs_without_autosave")

    def test_recovery_prompt_accept_loads_newer_autosave(self) -> None:
        self._run_scenario("test_recovery_prompt_accept_loads_newer_autosave")

    def test_recovery_prompt_accept_recovers_unsaved_temp_staged_refs(self) -> None:
        self._run_scenario("test_recovery_prompt_accept_recovers_unsaved_temp_staged_refs")

    def test_recovery_prompt_reject_keeps_session_state_and_discards_autosave(self) -> None:
        self._run_scenario("test_recovery_prompt_reject_keeps_session_state_and_discards_autosave")

    def test_recovery_prompt_is_skipped_when_autosave_matches_restored_session(self) -> None:
        self._run_scenario("test_recovery_prompt_is_skipped_when_autosave_matches_restored_session")

    def test_restore_session_handles_corrupted_session_and_autosave_files(self) -> None:
        self._run_scenario("test_restore_session_handles_corrupted_session_and_autosave_files")

    def test_recovery_prompt_is_deferred_until_main_window_is_visible(self) -> None:
        self._run_scenario("test_recovery_prompt_is_deferred_until_main_window_is_visible")

    def test_clean_close_discards_staged_scratch_and_clears_unsaved_root_hint(self) -> None:
        self._run_scenario("test_clean_close_discards_staged_scratch_and_clears_unsaved_root_hint")

    def test_explicit_save_promotes_referenced_staged_refs_and_prunes_orphans(self) -> None:
        self._run_scenario("test_explicit_save_promotes_referenced_staged_refs_and_prunes_orphans")

    def test_save_as_default_copy_switches_project_path_and_excludes_staging(self) -> None:
        self._run_scenario("test_save_as_default_copy_switches_project_path_and_excludes_staging")

    def test_recent_project_paths_are_owned_by_explicit_session_state(self) -> None:
        self._run_scenario("test_recent_project_paths_are_owned_by_explicit_session_state")

    def test_new_project_uses_navigation_controller_surface_without_workspace_library_facade(self) -> None:
        self._run_scenario("test_new_project_uses_navigation_controller_surface_without_workspace_library_facade")

    def test_project_files_menu_action_triggers_dialog(self) -> None:
        self._run_scenario("test_project_files_menu_action_triggers_dialog")

    def test_save_prompt_receives_project_file_summary_before_saving(self) -> None:
        self._run_scenario("test_save_prompt_receives_project_file_summary_before_saving")

    def test_open_project_path_can_abort_when_project_files_summary_has_staged_and_broken_entries(self) -> None:
        self._run_scenario("test_open_project_path_can_abort_when_project_files_summary_has_staged_and_broken_entries")

    def test_recovery_prompt_receives_project_file_summary_for_recovered_project(self) -> None:
        self._run_scenario("test_recovery_prompt_receives_project_file_summary_for_recovered_project")


def load_tests(loader, _tests, _pattern):  # noqa: ANN001
    return loader.loadTestsFromTestCase(ShellProjectSessionControllerTests)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == _SCENARIO_ARG:
        raise SystemExit(_run_named_scenario(sys.argv[2]))
    unittest.main()
