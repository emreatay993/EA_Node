from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.graph.model import ProjectData
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
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

    @classmethod
    def _normalize_project_path(cls, path: str | Path | object) -> str:
        return normalize_project_path_value(path)

    @classmethod
    def _normalized_recent_project_paths(cls, paths: Iterable[object]) -> list[str]:
        return normalized_recent_project_paths_value(paths, limit=cls._RECENT_PROJECT_LIMIT)

    def set_recent_project_paths(self, paths: Iterable[object], *, persist: bool = True) -> list[str]:
        return self._session_service.set_recent_project_paths(paths, persist=persist)

    def add_recent_project_path(self, path: str | Path, *, persist: bool = True) -> list[str]:
        return self._session_service.add_recent_project_path(path, persist=persist)

    def remove_recent_project_path(self, path: str | Path, *, persist: bool = True) -> list[str]:
        return self._session_service.remove_recent_project_path(path, persist=persist)

    def clear_recent_projects(self) -> None:
        self._session_service.clear_recent_projects()

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
        return self._project_files_service.prompt_project_files_action(
            title=title,
            text=text,
            continue_label=continue_label,
            cancel_standard_button=cancel_standard_button,
            snapshot=snapshot,
            context_key=context_key,
            allow_repair=allow_repair,
            always_prompt=always_prompt,
        )

    def show_project_files_dialog(
        self,
        *,
        snapshot: ProjectFilesSnapshot | None = None,
        allow_repair: bool | None = None,
    ) -> None:
        self._project_files_service.show_project_files_dialog(
            snapshot=snapshot,
            allow_repair=allow_repair,
        )

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
        self._document_service.save_project()

    def save_project_as(self) -> None:
        self._document_service.save_project_as()

    def new_project(self) -> None:
        self._document_service.new_project()

    def open_project(self) -> None:
        self._document_service.open_project()

    def open_project_path(self, path: str | Path, *, show_errors: bool = True) -> bool:
        return self._document_service.open_project_path(path, show_errors=show_errors)

    def restore_session(self) -> None:
        self._session_service.restore_session()

    def discard_autosave_snapshot(self) -> None:
        self._session_service.discard_autosave_snapshot()

    def recover_autosave_if_newer(self) -> ProjectData | None:
        return self._session_service.recover_autosave_if_newer()

    def prompt_recover_autosave(self, recovered_project: ProjectData | None = None):
        return self._session_service.prompt_recover_autosave(recovered_project)

    def process_deferred_autosave_recovery(self) -> None:
        self._session_service.process_deferred_autosave_recovery()

    def autosave_tick(self) -> None:
        self._session_service.autosave_tick()

    def close_session(self) -> None:
        self._session_service.close_session()

    def persist_session(self, project_doc: dict[str, Any] | None = None) -> None:
        self._session_service.persist_session(project_doc)
