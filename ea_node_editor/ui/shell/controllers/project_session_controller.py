from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any
import time

from ea_node_editor.graph.model import ProjectData
from ea_node_editor.persistence.artifact_store import ProjectArtifactLayout, ProjectArtifactStore
from ea_node_editor.persistence.project_codec import collect_project_artifact_references, rewrite_project_artifact_refs
from ea_node_editor.persistence.session_store import SessionAutosaveStore
from ea_node_editor.settings import PROJECT_ARTIFACT_STORE_METADATA_KEY
from ea_node_editor.ui.dialogs.project_files_dialog import ProjectFilesBrokenEntry, ProjectFilesSnapshot
from ea_node_editor.ui.shell.controllers.project_session_services import (
    ProjectDocumentIOService,
    ProjectFilesService,
    ProjectSessionLifecycleService,
    normalize_project_path_value,
    normalized_recent_project_paths_value,
)


class ProjectSessionController:
    _RECENT_PROJECT_LIMIT = 10

    def __init__(self, host: Any) -> None:
        self._host = host
        self._project_files_service = ProjectFilesService(host)
        self._session_service = ProjectSessionLifecycleService(host, project_files=self._project_files_service)
        self._document_service = ProjectDocumentIOService(
            host,
            project_files=self._project_files_service,
            session=self._session_service,
        )
        self._session_service.bind_document_service(self._document_service)

    @property
    def _session_state(self):
        return self._host.project_session_state

    @classmethod
    def _normalize_project_path(cls, path: str | Path | object) -> str:
        return normalize_project_path_value(path)

    @classmethod
    def _normalized_recent_project_paths(cls, paths: Iterable[object]) -> list[str]:
        return normalized_recent_project_paths_value(paths, limit=cls._RECENT_PROJECT_LIMIT)

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
        return self._project_files_service.project_artifact_store()

    def _set_project_artifact_store(self, store: ProjectArtifactStore) -> None:
        self._project_files_service._set_project_artifact_store(store)

    def ensure_project_staging_root(self) -> Path:
        return self._project_files_service.ensure_project_staging_root()

    def discard_staged_scratch_data(self) -> None:
        self._project_files_service.discard_staged_scratch_data()

    def ensure_project_metadata_defaults(self) -> None:
        self._document_service.ensure_project_metadata_defaults()

    def workflow_settings_payload(self) -> dict[str, Any]:
        return self._document_service.workflow_settings_payload()

    def persist_script_editor_state(self) -> None:
        self._document_service.persist_script_editor_state()

    def restore_script_editor_state(self) -> None:
        self._document_service.restore_script_editor_state()

    def show_workflow_settings_dialog(self) -> None:
        self._document_service.show_workflow_settings_dialog()

    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        self._document_service.set_script_editor_panel_visible(checked)

    def _install_project(self, project: ProjectData, *, project_path: str) -> None:
        self._document_service._install_project(project, project_path=project_path)

    def _finalize_loaded_project(self, project: ProjectData, *, project_path: str) -> None:
        self._document_service._finalize_loaded_project(project, project_path=project_path)

    def _default_save_as_path(self) -> str:
        return self._document_service._default_save_as_path()

    @staticmethod
    def _delete_save_as_sidecar_path(path: Path) -> None:
        ProjectDocumentIOService._delete_save_as_sidecar_path(path)

    @classmethod
    def _copy_save_as_payload(cls, source_path: Path, destination_path: Path) -> None:
        ProjectDocumentIOService._copy_save_as_payload(source_path, destination_path)

    def _reset_save_as_destination_sidecar(self, saved_path: Path) -> None:
        self._document_service._reset_save_as_destination_sidecar(saved_path)

    def build_project_files_snapshot(
        self,
        *,
        project: ProjectData | None = None,
        project_path: str | Path | None = None,
    ) -> ProjectFilesSnapshot:
        return self._project_files_service.build_project_files_snapshot(
            project=project,
            project_path=project_path,
        )

    @staticmethod
    def _count_text(count: int, noun: str) -> str:
        return ProjectFilesService._count_text(count, noun)

    @staticmethod
    def _project_files_prompt_headline(snapshot: ProjectFilesSnapshot) -> str:
        return ProjectFilesService._project_files_prompt_headline(snapshot)

    @classmethod
    def _project_files_prompt_details(cls, *, context_key: str, snapshot: ProjectFilesSnapshot) -> str:
        return ProjectFilesService._project_files_prompt_details(context_key=context_key, snapshot=snapshot)

    def _dialog_parent(self):
        from PyQt6.QtWidgets import QWidget

        return self._host if isinstance(self._host, QWidget) else None

    def _prompt_project_files_action(
        self,
        *,
        title: str,
        text: str,
        continue_label: str,
        cancel_standard_button,
        snapshot: ProjectFilesSnapshot,
        context_key: str,
        allow_repair: bool,
        always_prompt: bool = False,
    ) -> bool:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QMessageBox

        while True:
            if not always_prompt and not snapshot.has_prompt_context:
                return True

            dialog = QMessageBox(self._dialog_parent())
            dialog.setWindowTitle(title)
            dialog.setIcon(QMessageBox.Icon.Warning if snapshot.broken_count else QMessageBox.Icon.Information)
            dialog.setText(text)
            if snapshot.has_prompt_context:
                dialog.setInformativeText(self._project_files_prompt_details(context_key=context_key, snapshot=snapshot))
            continue_button = dialog.addButton(continue_label, QMessageBox.ButtonRole.AcceptRole)
            details_button = None
            if snapshot.has_prompt_context:
                details_button = dialog.addButton("Project Files...", QMessageBox.ButtonRole.ActionRole)
            dialog.addButton(cancel_standard_button)
            dialog.setDefaultButton(continue_button)
            dialog.setWindowModality(Qt.WindowModality.WindowModal)
            dialog.exec()
            if details_button is not None and dialog.clickedButton() is details_button:
                self.show_project_files_dialog(snapshot=snapshot, allow_repair=allow_repair)
                if allow_repair:
                    snapshot = self.build_project_files_snapshot()
                continue
            return dialog.clickedButton() is continue_button

    def show_project_files_dialog(
        self,
        *,
        snapshot: ProjectFilesSnapshot | None = None,
        allow_repair: bool | None = None,
    ) -> None:
        current_snapshot = snapshot if snapshot is not None else self.build_project_files_snapshot()
        repair_enabled = bool(allow_repair) if allow_repair is not None else snapshot is None
        from ea_node_editor.ui.dialogs.project_files_dialog import ProjectFilesDialog

        dialog = ProjectFilesDialog(
            snapshot=current_snapshot,
            repair_callback=self._repair_project_file_issue if repair_enabled else None,
            refresh_snapshot_callback=self.build_project_files_snapshot if repair_enabled else None,
            parent=self._dialog_parent(),
        )
        dialog.exec()

    def _repair_project_file_issue(self, issue: ProjectFilesBrokenEntry) -> bool:
        return self._project_files_service.repair_project_file_issue(issue)

    def _build_save_as_artifact_store_metadata(
        self,
        *,
        saved_path: Path,
        source_document: Mapping[str, Any],
        referenced_managed_ids: Iterable[object],
        copy_managed_data: bool,
    ) -> dict[str, Any]:
        return self._document_service._build_save_as_artifact_store_metadata(
            saved_path=saved_path,
            source_document=source_document,
            referenced_managed_ids=referenced_managed_ids,
            copy_managed_data=copy_managed_data,
        )

    def _rewrite_live_project_artifact_refs(self, replacements: dict[str, str]) -> None:
        self._document_service._rewrite_live_project_artifact_refs(replacements)

    def save_project(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtWidgets import QMessageBox

        snapshot = self.build_project_files_snapshot()
        if not self._prompt_project_files_action(
            title="Save Project",
            text=self._project_files_prompt_headline(snapshot),
            continue_label="Save Project",
            cancel_standard_button=QMessageBox.StandardButton.Cancel,
            snapshot=snapshot,
            context_key="save",
            allow_repair=True,
        ):
            return

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

    def save_project_as(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtWidgets import QMessageBox

        from ea_node_editor.ui.dialogs.project_save_as_dialog import ProjectSaveAsDialog

        snapshot = self.build_project_files_snapshot()
        if not self._prompt_project_files_action(
            title="Save Project As",
            text=self._project_files_prompt_headline(snapshot),
            continue_label="Continue",
            cancel_standard_button=QMessageBox.StandardButton.Cancel,
            snapshot=snapshot,
            context_key="save_as",
            allow_repair=True,
        ):
            return

        path, _ = QFileDialog.getSaveFileName(
            self._host,
            "Save Project As",
            self._default_save_as_path(),
            "EA Project (*.sfe)",
        )
        normalized_path = self._normalize_project_path(path)
        if not normalized_path:
            return

        saved_path = Path(normalized_path)
        persistent_document = self._host.serializer.to_persistent_document(self._host.model.project)
        artifact_refs = collect_project_artifact_references(persistent_document)
        dialog = ProjectSaveAsDialog(
            referenced_managed_count=len(artifact_refs.managed_ids),
            referenced_staged_count=len(artifact_refs.staged_ids),
            parent=self._host,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        current_project_path = self._normalize_project_path(self._host.project_path)
        if current_project_path and saved_path == Path(current_project_path):
            self.save_project()
            return

        copy_managed_data = dialog.selected_mode() == ProjectSaveAsDialog.SELF_CONTAINED_COPY

        self._host.workspace_library_controller.save_active_view_state()
        updated_document = copy.deepcopy(persistent_document)
        document_metadata = (
            dict(updated_document.get("metadata", {}))
            if isinstance(updated_document.get("metadata"), Mapping)
            else {}
        )
        document_metadata[PROJECT_ARTIFACT_STORE_METADATA_KEY] = self._build_save_as_artifact_store_metadata(
            saved_path=saved_path,
            source_document=updated_document,
            referenced_managed_ids=artifact_refs.managed_ids,
            copy_managed_data=copy_managed_data,
        )
        updated_document["metadata"] = document_metadata
        saved_path.parent.mkdir(parents=True, exist_ok=True)
        self._host.serializer.save_document(str(saved_path), updated_document)

        self._host.model.project.metadata = copy.deepcopy(document_metadata)
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

    def new_project(self) -> None:
        self._document_service.new_project()

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
        snapshot = self.build_project_files_snapshot(project=project, project_path=resolved_path)
        if not self._prompt_project_files_action(
            title="Open Project",
            text=self._project_files_prompt_headline(snapshot),
            continue_label="Open Project",
            cancel_standard_button=QMessageBox.StandardButton.Cancel,
            snapshot=snapshot,
            context_key="open",
            allow_repair=False,
        ):
            return False
        self._finalize_loaded_project(project, project_path=str(resolved_path))
        return True

    def restore_session(self) -> None:
        self._session_service.restore_session()

    def discard_autosave_snapshot(self) -> None:
        self._session_service.discard_autosave_snapshot()

    def recover_autosave_if_newer(self) -> ProjectData | None:
        return self._session_service.recover_autosave_if_newer()

    def prompt_recover_autosave(self, recovered_project: ProjectData | None = None):
        from PyQt6.QtWidgets import QMessageBox

        snapshot = (
            self.build_project_files_snapshot(
                project=recovered_project,
                project_path=self._host.project_path,
            )
            if recovered_project is not None
            else self.build_project_files_snapshot()
        )
        accepted = self._prompt_project_files_action(
            title="Recover Autosave",
            text="A newer autosave snapshot is available. Recover it?",
            continue_label="Recover",
            cancel_standard_button=QMessageBox.StandardButton.No,
            snapshot=snapshot,
            context_key="recover",
            allow_repair=False,
            always_prompt=True,
        )
        return QMessageBox.StandardButton.Yes if accepted else QMessageBox.StandardButton.No

    def process_deferred_autosave_recovery(self) -> None:
        self._session_service.process_deferred_autosave_recovery()

    def autosave_tick(self) -> None:
        self._session_service.autosave_tick()

    def close_session(self) -> None:
        self._session_service.close_session()

    def persist_session(self, project_doc: dict[str, Any] | None = None) -> None:
        self._session_service.persist_session(project_doc=project_doc)
