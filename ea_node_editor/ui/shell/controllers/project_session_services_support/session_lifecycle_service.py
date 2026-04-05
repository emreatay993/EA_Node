from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ea_node_editor.graph.model import ProjectData
from ea_node_editor.persistence.session_store import SessionAutosaveStore
from ea_node_editor.ui.shell.controllers.project_session_services_support.project_files_service import (
    ProjectFilesService,
)
from ea_node_editor.ui.shell.controllers.project_session_services_support.shared import (
    _AutosaveRecoveryPromptProtocol,
    _ProjectSessionLifecycleHostProtocol,
    _RecentProjectsMenuProtocol,
    _WorkspaceSessionProtocol,
    normalize_project_path_value,
    normalized_recent_project_paths_value,
)
from ea_node_editor.ui.shell.state import ShellProjectSessionState

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.controllers.project_session_services_support.document_io_service import (
        ProjectDocumentIOService,
    )


class ProjectSessionLifecycleService:
    def __init__(
        self,
        host: _ProjectSessionLifecycleHostProtocol,
        *,
        project_files: ProjectFilesService,
        workspace_session: _WorkspaceSessionProtocol,
        recent_projects_menu: _RecentProjectsMenuProtocol,
        recovery_prompt: _AutosaveRecoveryPromptProtocol,
    ) -> None:
        self._host = host
        self._project_files = project_files
        self._workspace_session = workspace_session
        self._recent_projects_menu = recent_projects_menu
        self._recovery_prompt = recovery_prompt
        self._document_service: ProjectDocumentIOService | None = None

    def bind_document_service(self, document_service: ProjectDocumentIOService) -> None:
        self._document_service = document_service

    @property
    def _session_state(self) -> ShellProjectSessionState:
        return self._host.project_session_state

    def _refresh_recent_projects_menu(self) -> None:
        self._recent_projects_menu.refresh_recent_projects_menu()

    def _sync_session_state(self) -> None:
        self._workspace_session.save_active_view_state()
        self._require_document_service().persist_script_editor_state()

    def _current_project_document(self) -> dict[str, Any]:
        self._sync_session_state()
        return self._host.serializer.to_document(self._host.model.project)

    def _autosave_resume_fingerprint(self) -> str:
        return self._session_state.last_autosave_fingerprint if not self._host.project_path else ""

    def _persist_recent_session_payload(self, *, autosave_resume_fingerprint: str = "") -> None:
        self._host.session_store.persist_session(
            project_path=self._host.project_path,
            last_manual_save_ts=self._session_state.last_manual_save_ts,
            recent_project_paths=list(self._session_state.recent_project_paths),
            autosave_resume_fingerprint=autosave_resume_fingerprint,
        )

    def set_recent_project_paths(self, paths: Iterable[object], *, persist: bool = True) -> list[str]:
        normalized_paths = normalized_recent_project_paths_value(paths, limit=10)
        self._session_state.recent_project_paths = normalized_paths
        self._refresh_recent_projects_menu()
        if persist:
            self.persist_session()
        return normalized_paths

    def add_recent_project_path(self, path: str | Path, *, persist: bool = True) -> list[str]:
        normalized_path = normalize_project_path_value(path)
        if not normalized_path:
            return list(self._session_state.recent_project_paths)
        existing_paths = list(self._session_state.recent_project_paths)
        return self.set_recent_project_paths([normalized_path, *existing_paths], persist=persist)

    def remove_recent_project_path(self, path: str | Path, *, persist: bool = True) -> list[str]:
        normalized_path = normalize_project_path_value(path)
        if not normalized_path:
            return list(self._session_state.recent_project_paths)
        filtered_paths = [item for item in self._session_state.recent_project_paths if item != normalized_path]
        return self.set_recent_project_paths(filtered_paths, persist=persist)

    def clear_recent_projects(self) -> None:
        self.set_recent_project_paths([], persist=True)

    def restore_session(self) -> None:
        session = self._host.session_store.load_session_envelope()
        session_project_path = session.project_path
        self._session_state.last_manual_save_ts = session.last_manual_save_ts
        self.set_recent_project_paths(session.recent_project_paths, persist=False)

        restored = False
        if session_project_path and Path(session_project_path).exists():
            try:
                project = self._host.serializer.load(session_project_path)
                self._require_document_service()._install_project(project, project_path=session_project_path)
                self._session_state.last_manual_save_ts = max(
                    self._session_state.last_manual_save_ts,
                    Path(session_project_path).stat().st_mtime,
                )
                restored = True
            except Exception:  # noqa: BLE001
                self._host.project_path = ""

        if not restored:
            resumed_project = self._host.session_store.load_resume_autosave(
                expected_fingerprint=session.autosave.resume_fingerprint,
            )
            if resumed_project is not None:
                self._require_document_service()._install_project(resumed_project, project_path="")
                restored = True

        recovered_project = self.recover_autosave_if_newer()
        if recovered_project is not None:
            self._require_document_service()._install_project(
                recovered_project,
                project_path=session_project_path if Path(session_project_path).exists() else "",
            )
            restored = True

        if not restored:
            self._host.project_path = ""

        self._require_document_service().ensure_project_metadata_defaults()
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

        if not self._recovery_prompt.is_visible():
            self._session_state.autosave_recovery_deferred = True
            return None

        choice = self._recovery_prompt.prompt_recover_autosave(recovered_project)
        if choice != QMessageBox.StandardButton.Yes:
            self.discard_autosave_snapshot()
            return None

        self.discard_autosave_snapshot()
        return recovered_project

    def prompt_recover_autosave(self, recovered_project: ProjectData | None = None):
        from PyQt6.QtWidgets import QMessageBox

        snapshot = (
            self._project_files.build_project_files_snapshot(
                project=recovered_project,
                project_path=self._host.project_path,
            )
            if recovered_project is not None
            else self._project_files.build_project_files_snapshot()
        )
        accepted = self._project_files.prompt_project_files_action(
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
        if not self._session_state.autosave_recovery_deferred:
            return
        self._session_state.autosave_recovery_deferred = False
        recovered_project = self.recover_autosave_if_newer()
        if recovered_project is None:
            return
        self._require_document_service()._install_project(recovered_project, project_path=self._host.project_path)
        self._require_document_service().ensure_project_metadata_defaults()
        self._workspace_session.refresh_workspace_tabs()
        self._workspace_session.switch_workspace(self._host.model.active_workspace.workspace_id)
        self._require_document_service().restore_script_editor_state()
        document = self._current_project_document()
        self._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(document)
        self.persist_session()

    def autosave_tick(self) -> None:
        try:
            project_doc = self._current_project_document()
            self._session_state.last_autosave_fingerprint = self._host.session_store.autosave_if_changed(
                project_doc=project_doc,
                last_fingerprint=self._session_state.last_autosave_fingerprint,
            )
            self._persist_recent_session_payload(
                autosave_resume_fingerprint=self._autosave_resume_fingerprint(),
            )
        except Exception:  # noqa: BLE001
            return

    def close_session(self) -> None:
        self._project_files.discard_staged_scratch_data()
        try:
            self._sync_session_state()
            self._persist_recent_session_payload(autosave_resume_fingerprint="")
        except Exception:  # noqa: BLE001
            pass
        self.discard_autosave_snapshot()

    def persist_session(self, project_doc: dict[str, Any] | None = None) -> None:
        del project_doc
        try:
            document = self._current_project_document()
            self._session_state.last_autosave_fingerprint = self._host.session_store.autosave_if_changed(
                project_doc=document,
                last_fingerprint=self._session_state.last_autosave_fingerprint,
            )
            self._persist_recent_session_payload(
                autosave_resume_fingerprint=self._autosave_resume_fingerprint(),
            )
        except Exception:  # noqa: BLE001
            return

    def _require_document_service(self) -> ProjectDocumentIOService:
        if self._document_service is None:
            raise RuntimeError("Project document service is not bound.")
        return self._document_service


__all__ = ["ProjectSessionLifecycleService"]
