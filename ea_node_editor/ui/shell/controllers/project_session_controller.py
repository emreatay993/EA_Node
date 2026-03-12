from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.persistence.session_store import SessionAutosaveStore
from ea_node_editor.persistence.utils import merge_defaults
from ea_node_editor.settings import DEFAULT_UI_STATE, DEFAULT_WORKFLOW_SETTINGS
from ea_node_editor.workspace.manager import WorkspaceManager

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class ProjectSessionController:
    _RECENT_PROJECT_LIMIT = 10

    def __init__(self, host: ShellWindow) -> None:
        self._host = host

    @classmethod
    def _normalize_project_path(cls, path: str | Path | object) -> str:
        raw_path = str(path).strip()
        if not raw_path:
            return ""
        try:
            return str(Path(raw_path).expanduser().with_suffix(".sfe"))
        except ValueError:
            return ""

    @classmethod
    def _normalized_recent_project_paths(cls, paths: Iterable[object]) -> list[str]:
        normalized_paths: list[str] = []
        seen_paths: set[str] = set()
        for path in paths:
            normalized_path = cls._normalize_project_path(path)
            if not normalized_path or normalized_path in seen_paths:
                continue
            seen_paths.add(normalized_path)
            normalized_paths.append(normalized_path)
            if len(normalized_paths) >= cls._RECENT_PROJECT_LIMIT:
                break
        return normalized_paths

    def _refresh_recent_projects_menu(self) -> None:
        refresh_menu = getattr(self._host, "_refresh_recent_projects_menu", None)
        if callable(refresh_menu):
            refresh_menu()

    def set_recent_project_paths(self, paths: Iterable[object], *, persist: bool = True) -> list[str]:
        normalized_paths = self._normalized_recent_project_paths(paths)
        self._host.recent_project_paths = normalized_paths
        self._refresh_recent_projects_menu()
        if persist:
            self.persist_session()
        return normalized_paths

    def add_recent_project_path(self, path: str | Path, *, persist: bool = True) -> list[str]:
        normalized_path = self._normalize_project_path(path)
        if not normalized_path:
            return list(self._host.recent_project_paths)
        existing_paths = list(self._host.recent_project_paths)
        return self.set_recent_project_paths([normalized_path, *existing_paths], persist=persist)

    def remove_recent_project_path(self, path: str | Path, *, persist: bool = True) -> list[str]:
        normalized_path = self._normalize_project_path(path)
        if not normalized_path:
            return list(self._host.recent_project_paths)
        filtered_paths = [item for item in self._host.recent_project_paths if item != normalized_path]
        return self.set_recent_project_paths(filtered_paths, persist=persist)

    def clear_recent_projects(self) -> None:
        self.set_recent_project_paths([], persist=True)

    def ensure_project_metadata_defaults(self) -> None:
        metadata = self._host.model.project.metadata if isinstance(self._host.model.project.metadata, dict) else {}
        metadata["ui"] = merge_defaults(metadata.get("ui"), DEFAULT_UI_STATE)
        metadata["workflow_settings"] = merge_defaults(
            metadata.get("workflow_settings"),
            DEFAULT_WORKFLOW_SETTINGS,
        )
        self._host.model.project.metadata = metadata

    def workflow_settings_payload(self) -> dict[str, Any]:
        self.ensure_project_metadata_defaults()
        return merge_defaults(
            self._host.model.project.metadata.get("workflow_settings", {}),
            DEFAULT_WORKFLOW_SETTINGS,
        )

    def persist_script_editor_state(self) -> None:
        self.ensure_project_metadata_defaults()
        self._host.model.project.metadata["ui"]["script_editor"] = {
            "visible": self._host.script_editor.visible,
            "floating": self._host.script_editor.floating,
        }

    def restore_script_editor_state(self) -> None:
        self.ensure_project_metadata_defaults()
        state = self._host.model.project.metadata["ui"].get("script_editor", {})
        selected_node_id = self._host.scene.selected_node_id() or ""
        can_show_editor = bool(selected_node_id)
        visible = bool(state.get("visible", False)) and can_show_editor
        floating = bool(state.get("floating", False))
        self._host.script_editor.set_floating(floating)
        self._host.script_editor.set_visible(visible)
        self._host.action_toggle_script_editor.setChecked(visible)

    def show_workflow_settings_dialog(self) -> None:
        from ea_node_editor.ui.dialogs.workflow_settings_dialog import WorkflowSettingsDialog

        self.ensure_project_metadata_defaults()
        dialog = WorkflowSettingsDialog(
            initial_settings=self._host.model.project.metadata.get("workflow_settings", {}),
            parent=self._host,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self._host.model.project.metadata["workflow_settings"] = dialog.values()
        self.persist_session()

    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        target_visible = bool(checked) if checked is not None else not self._host.script_editor.visible
        self._host.script_editor.set_visible(target_visible)
        self._host.action_toggle_script_editor.setChecked(target_visible)
        self.persist_script_editor_state()
        if target_visible:
            node_id = self._host.scene.selected_node_id()
            if node_id:
                workspace = self._host.model.project.workspaces[self._host.workspace_manager.active_workspace_id()]
                self._host.script_editor.set_node(workspace.nodes.get(node_id))
            self._host.script_editor.focus_editor()

    def _install_project(self, project: ProjectData, *, project_path: str) -> None:
        normalize_project_for_registry(project, self._host.registry)
        self._host.model = GraphModel(project)
        self._host.workspace_manager = WorkspaceManager(self._host.model)
        self._host.runtime_history.clear_all()
        self._host.project_path = project_path
        self._host.library_pane_reset_requested.emit()
        # Refresh library-bound QML models immediately after project swap.
        self._host.node_library_changed.emit()

    def _finalize_loaded_project(self, project: ProjectData, *, project_path: str) -> None:
        resolved_path = Path(project_path)
        self._install_project(project, project_path=str(resolved_path))
        self.ensure_project_metadata_defaults()
        try:
            self._host._last_manual_save_ts = resolved_path.stat().st_mtime
        except OSError:
            self._host._last_manual_save_ts = time.time()
        self.discard_autosave_snapshot()
        self._host._last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self.add_recent_project_path(str(resolved_path), persist=False)
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self._host.workspace_library_controller.switch_workspace(self._host.workspace_manager.active_workspace_id())
        self.restore_script_editor_state()
        self.persist_session()
        self._host.project_meta_changed.emit()

    def save_project(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path = self._host.project_path
        if not path:
            path, _ = QFileDialog.getSaveFileName(self._host, "Save Project", "", "EA Project (*.sfe)")
        if not path:
            return
        self._host.workspace_library_controller.save_active_view_state()
        self._host.serializer.save(path, self._host.model.project)
        saved_path = Path(path).with_suffix(".sfe")
        self._host.project_path = str(saved_path)
        try:
            self._host._last_manual_save_ts = saved_path.stat().st_mtime
        except OSError:
            self._host._last_manual_save_ts = time.time()
        for workspace in self._host.model.project.workspaces.values():
            workspace.dirty = False
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self.discard_autosave_snapshot()
        self._host._last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self.add_recent_project_path(str(saved_path), persist=False)
        self.persist_session()
        self._host.project_meta_changed.emit()

    def new_project(self) -> None:
        project = ProjectData(project_id="proj_local", name="untitled")
        self._install_project(project, project_path="")
        self.ensure_project_metadata_defaults()
        self._host._last_manual_save_ts = 0.0
        self.discard_autosave_snapshot()
        self._host._last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self._host.workspace_library_controller.switch_workspace(self._host.workspace_manager.active_workspace_id())
        self.restore_script_editor_state()
        self.persist_session()
        self._host.project_meta_changed.emit()

    def open_project(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self._host, "Open Project", "", "EA Project (*.sfe)")
        if not path:
            return
        self.open_project_path(path, show_errors=True)

    def open_project_path(self, path: str | Path, *, show_errors: bool = True) -> bool:
        from PyQt6.QtWidgets import QMessageBox

        normalized_path = self._normalize_project_path(path)
        if not normalized_path:
            return False
        resolved_path = Path(normalized_path)
        if not resolved_path.exists():
            self.remove_recent_project_path(normalized_path, persist=False)
            self.persist_session()
            if show_errors:
                QMessageBox.warning(self._host, "Open Project", f"Project file not found.\n{resolved_path}")
            return False
        try:
            project = self._host.serializer.load(str(resolved_path))
        except Exception as exc:  # noqa: BLE001
            if show_errors:
                QMessageBox.warning(self._host, "Open Project", f"Could not open project file.\n{exc}")
            return False
        self._finalize_loaded_project(project, project_path=str(resolved_path))
        return True

    def restore_session(self) -> None:
        session = self._host._session_store.load_session_payload()
        session_project_path = str(session.get("project_path", "")).strip()
        self._host._last_manual_save_ts = SessionAutosaveStore.coerce_timestamp(session.get("last_manual_save_ts", 0.0))
        self.set_recent_project_paths(session.get("recent_project_paths", []), persist=False)

        restored = False
        if session_project_path and Path(session_project_path).exists():
            try:
                project = self._host.serializer.load(session_project_path)
                self._install_project(project, project_path=session_project_path)
                self._host._last_manual_save_ts = max(
                    self._host._last_manual_save_ts,
                    Path(session_project_path).stat().st_mtime,
                )
                restored = True
            except Exception:  # noqa: BLE001
                self._host.project_path = ""

        if not restored:
            doc = session.get("project_doc")
            if isinstance(doc, dict):
                try:
                    project = self._host.serializer.from_document(doc)
                    self._install_project(project, project_path="")
                    restored = True
                except Exception:  # noqa: BLE001
                    self._host.project_path = ""

        recovered_project = self.recover_autosave_if_newer()
        if recovered_project is not None:
            self._install_project(
                recovered_project,
                project_path=session_project_path if Path(session_project_path).exists() else "",
            )
            restored = True

        if not restored:
            self._host.project_path = ""

        self.ensure_project_metadata_defaults()
        if self._host.project_path:
            self.add_recent_project_path(self._host.project_path, persist=False)
        self._host._last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self._refresh_recent_projects_menu()
        self._host.project_meta_changed.emit()

    def discard_autosave_snapshot(self) -> None:
        self._host._session_store.discard_autosave_snapshot()
        self._host._last_autosave_fingerprint = ""

    def recover_autosave_if_newer(self) -> ProjectData | None:
        from PyQt6.QtWidgets import QMessageBox

        recovered_project = self._host._session_store.load_recoverable_autosave(
            current_project_doc=self._host.serializer.to_document(self._host.model.project),
            project_path=self._host.project_path,
            last_manual_save_ts=self._host._last_manual_save_ts,
        )
        if recovered_project is None:
            return None

        if not self._host.isVisible():
            self._host._autosave_recovery_deferred = True
            return None

        choice = self._host._prompt_recover_autosave()
        if choice != QMessageBox.StandardButton.Yes:
            self.discard_autosave_snapshot()
            return None

        self.discard_autosave_snapshot()
        return recovered_project

    def prompt_recover_autosave(self) -> QMessageBox.StandardButton:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QMessageBox

        dialog = QMessageBox(self._host)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle("Recover Autosave")
        dialog.setText("A newer autosave snapshot is available. Recover it?")
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.Yes)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        return QMessageBox.StandardButton(dialog.exec())

    def process_deferred_autosave_recovery(self) -> None:
        if not self._host._autosave_recovery_deferred:
            return
        self._host._autosave_recovery_deferred = False
        recovered_project = self.recover_autosave_if_newer()
        if recovered_project is None:
            return
        self._install_project(recovered_project, project_path=self._host.project_path)
        self.ensure_project_metadata_defaults()
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self._host.workspace_library_controller.switch_workspace(self._host.workspace_manager.active_workspace_id())
        self.restore_script_editor_state()
        self._host._last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self.persist_session()

    def autosave_tick(self) -> None:
        try:
            self._host.workspace_library_controller.save_active_view_state()
            project_doc = self._host.serializer.to_document(self._host.model.project)
            self._host._last_autosave_fingerprint = self._host._session_store.autosave_if_changed(
                project_doc=project_doc,
                last_fingerprint=self._host._last_autosave_fingerprint,
            )
            self.persist_session(project_doc=project_doc)
        except Exception:  # noqa: BLE001
            return

    def persist_session(self, project_doc: dict[str, Any] | None = None) -> None:
        self._host.workspace_library_controller.save_active_view_state()
        self.persist_script_editor_state()
        document = project_doc if isinstance(project_doc, dict) else self._host.serializer.to_document(self._host.model.project)
        try:
            self._host._session_store.persist_session(
                project_path=self._host.project_path,
                last_manual_save_ts=self._host._last_manual_save_ts,
                project_doc=document,
                recent_project_paths=list(self._host.recent_project_paths),
            )
        except Exception:  # noqa: BLE001
            return
