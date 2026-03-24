from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Iterable, Protocol

from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.persistence.project_codec import (
    collect_project_artifact_references,
    rewrite_project_artifact_refs,
)
from ea_node_editor.persistence.session_store import SessionAutosaveStore
from ea_node_editor.persistence.utils import merge_defaults
from ea_node_editor.settings import (
    DEFAULT_UI_STATE,
    DEFAULT_WORKFLOW_SETTINGS,
    PROJECT_ARTIFACT_STORE_METADATA_KEY,
)
from ea_node_editor.ui.passive_style_presets import normalize_passive_style_presets
from ea_node_editor.ui.shell.state import ShellProjectSessionState
from ea_node_editor.workspace.manager import WorkspaceManager


class _ProjectSessionHostProtocol(Protocol):
    project_session_state: ShellProjectSessionState
    session_store: SessionAutosaveStore
    registry: Any
    model: GraphModel
    workspace_manager: WorkspaceManager
    runtime_history: Any
    serializer: Any
    workspace_library_controller: Any
    script_editor: Any
    action_toggle_script_editor: Any
    scene: Any
    project_meta_changed: Any

    project_path: str

    def _refresh_recent_projects_menu(self) -> None: ...

    def _prompt_recover_autosave(self): ...

    def isVisible(self) -> bool: ...


class ProjectSessionController:
    _RECENT_PROJECT_LIMIT = 10

    def __init__(self, host: _ProjectSessionHostProtocol) -> None:
        self._host = host

    @property
    def _session_state(self) -> ShellProjectSessionState:
        return self._host.project_session_state

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
        self._session_state.recent_project_paths = normalized_paths
        self._refresh_recent_projects_menu()
        if persist:
            self.persist_session()
        return normalized_paths

    def add_recent_project_path(self, path: str | Path, *, persist: bool = True) -> list[str]:
        normalized_path = self._normalize_project_path(path)
        if not normalized_path:
            return list(self._session_state.recent_project_paths)
        existing_paths = list(self._session_state.recent_project_paths)
        return self.set_recent_project_paths([normalized_path, *existing_paths], persist=persist)

    def remove_recent_project_path(self, path: str | Path, *, persist: bool = True) -> list[str]:
        normalized_path = self._normalize_project_path(path)
        if not normalized_path:
            return list(self._session_state.recent_project_paths)
        filtered_paths = [item for item in self._session_state.recent_project_paths if item != normalized_path]
        return self.set_recent_project_paths(filtered_paths, persist=persist)

    def clear_recent_projects(self) -> None:
        self.set_recent_project_paths([], persist=True)

    def project_artifact_store(self) -> ProjectArtifactStore:
        metadata = self._host.model.project.metadata if isinstance(self._host.model.project.metadata, dict) else {}
        return ProjectArtifactStore.from_project_metadata(
            project_path=self._host.project_path,
            project_metadata=metadata,
        )

    def _set_project_artifact_store(self, store: ProjectArtifactStore) -> None:
        metadata = self._host.model.project.metadata if isinstance(self._host.model.project.metadata, dict) else {}
        updated_metadata = dict(metadata)
        updated_metadata[PROJECT_ARTIFACT_STORE_METADATA_KEY] = store.metadata
        self._host.model.project.metadata = updated_metadata

    def ensure_project_staging_root(self) -> Path:
        store = self.project_artifact_store()
        staging_root = store.ensure_staging_root(
            temporary_root_parent=self._host.session_store.staging_workspace_root(),
        )
        self._set_project_artifact_store(store)
        return staging_root

    def discard_staged_scratch_data(self) -> None:
        store = self.project_artifact_store()
        store.discard_staged_payloads()
        self._set_project_artifact_store(store)

    def ensure_project_metadata_defaults(self) -> None:
        metadata = self._host.model.project.metadata if isinstance(self._host.model.project.metadata, dict) else {}
        metadata["ui"] = merge_defaults(metadata.get("ui"), DEFAULT_UI_STATE)
        metadata["ui"]["passive_style_presets"] = normalize_passive_style_presets(
            metadata["ui"].get("passive_style_presets")
        )
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
            self._session_state.last_manual_save_ts = resolved_path.stat().st_mtime
        except OSError:
            self._session_state.last_manual_save_ts = time.time()
        self.discard_autosave_snapshot()
        self._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
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
        saved_path = Path(path).with_suffix(".sfe")
        self._host.workspace_library_controller.save_active_view_state()
        persistent_document = self._host.serializer.to_persistent_document(self._host.model.project)
        artifact_refs = collect_project_artifact_references(persistent_document)
        store = ProjectArtifactStore.from_project_metadata(
            project_path=saved_path,
            project_metadata=self._host.model.project.metadata,
        )
        promotion = store.commit_referenced_artifacts(
            referenced_managed_ids=artifact_refs.managed_ids,
            referenced_staged_ids=artifact_refs.staged_ids,
        )
        updated_document = rewrite_project_artifact_refs(
            persistent_document,
            promotion.ref_replacements,
        )
        document_metadata = (
            dict(updated_document.get("metadata", {}))
            if isinstance(updated_document.get("metadata"), dict)
            else {}
        )
        document_metadata[PROJECT_ARTIFACT_STORE_METADATA_KEY] = store.metadata
        updated_document["metadata"] = document_metadata
        self._host.serializer.save_document(str(saved_path), updated_document)
        self._rewrite_live_project_artifact_refs(promotion.ref_replacements)
        self._set_project_artifact_store(store)
        self._host.project_path = str(saved_path)
        try:
            self._session_state.last_manual_save_ts = saved_path.stat().st_mtime
        except OSError:
            self._session_state.last_manual_save_ts = time.time()
        for workspace in self._host.model.project.workspaces.values():
            workspace.dirty = False
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self.discard_autosave_snapshot()
        self._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self.add_recent_project_path(str(saved_path), persist=False)
        self.persist_session()
        self._host.project_meta_changed.emit()

    def _rewrite_live_project_artifact_refs(self, replacements: dict[str, str]) -> None:
        if not replacements:
            return
        project = self._host.model.project
        project.metadata = rewrite_project_artifact_refs(project.metadata, replacements)
        for workspace in project.workspaces.values():
            for node in workspace.nodes.values():
                node.properties = rewrite_project_artifact_refs(node.properties, replacements)
            state = workspace.capture_persistence_state()
            state.replace_unresolved_node_docs(
                {
                    node_id: rewrite_project_artifact_refs(node_doc, replacements)
                    for node_id, node_doc in state.unresolved_node_docs.items()
                }
            )
            state.replace_unresolved_edge_docs(
                {
                    edge_id: rewrite_project_artifact_refs(edge_doc, replacements)
                    for edge_id, edge_doc in state.unresolved_edge_docs.items()
                }
            )
            state.replace_authored_node_overrides(
                {
                    node_id: rewrite_project_artifact_refs(override_doc, replacements)
                    for node_id, override_doc in state.authored_node_overrides.items()
                }
            )
            workspace.restore_persistence_state(state)

    def new_project(self) -> None:
        project = ProjectData(project_id="proj_local", name="untitled")
        self._install_project(project, project_path="")
        self.ensure_project_metadata_defaults()
        self._session_state.last_manual_save_ts = 0.0
        self.discard_autosave_snapshot()
        self._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
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
        session = self._host.session_store.load_session_payload()
        session_project_path = str(session.get("project_path", "")).strip()
        self._session_state.last_manual_save_ts = SessionAutosaveStore.coerce_timestamp(
            session.get("last_manual_save_ts", 0.0)
        )
        self.set_recent_project_paths(session.get("recent_project_paths", []), persist=False)

        restored = False
        if session_project_path and Path(session_project_path).exists():
            try:
                project = self._host.serializer.load(session_project_path)
                self._install_project(project, project_path=session_project_path)
                self._session_state.last_manual_save_ts = max(
                    self._session_state.last_manual_save_ts,
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
        self._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self._refresh_recent_projects_menu()
        self._host.project_meta_changed.emit()

    def discard_autosave_snapshot(self) -> None:
        self._host.session_store.discard_autosave_snapshot()
        self._session_state.last_autosave_fingerprint = ""

    def recover_autosave_if_newer(self) -> ProjectData | None:
        from PyQt6.QtWidgets import QMessageBox

        recovered_project = self._host.session_store.load_recoverable_autosave(
            current_project_doc=self._host.serializer.to_document(self._host.model.project),
            project_path=self._host.project_path,
            last_manual_save_ts=self._session_state.last_manual_save_ts,
        )
        if recovered_project is None:
            return None

        if not self._host.isVisible():
            self._session_state.autosave_recovery_deferred = True
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
        if not self._session_state.autosave_recovery_deferred:
            return
        self._session_state.autosave_recovery_deferred = False
        recovered_project = self.recover_autosave_if_newer()
        if recovered_project is None:
            return
        self._install_project(recovered_project, project_path=self._host.project_path)
        self.ensure_project_metadata_defaults()
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self._host.workspace_library_controller.switch_workspace(self._host.workspace_manager.active_workspace_id())
        self.restore_script_editor_state()
        self._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self.persist_session()

    def autosave_tick(self) -> None:
        try:
            self._host.workspace_library_controller.save_active_view_state()
            project_doc = self._host.serializer.to_document(self._host.model.project)
            self._session_state.last_autosave_fingerprint = self._host.session_store.autosave_if_changed(
                project_doc=project_doc,
                last_fingerprint=self._session_state.last_autosave_fingerprint,
            )
            self.persist_session(project_doc=project_doc)
        except Exception:  # noqa: BLE001
            return

    def close_session(self) -> None:
        self.discard_staged_scratch_data()
        self.discard_autosave_snapshot()
        self.persist_session()

    def persist_session(self, project_doc: dict[str, Any] | None = None) -> None:
        self._host.workspace_library_controller.save_active_view_state()
        self.persist_script_editor_state()
        document = project_doc if isinstance(project_doc, dict) else self._host.serializer.to_document(self._host.model.project)
        try:
            self._host.session_store.persist_session(
                project_path=self._host.project_path,
                last_manual_save_ts=self._session_state.last_manual_save_ts,
                project_doc=document,
                recent_project_paths=list(self._session_state.recent_project_paths),
            )
        except Exception:  # noqa: BLE001
            return
