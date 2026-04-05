from __future__ import annotations

from pathlib import Path

from ea_node_editor.graph.file_issue_state import collect_workspace_file_issue_map
from ea_node_editor.graph.model import ProjectData
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.settings import PROJECT_ARTIFACT_STORE_METADATA_KEY
from ea_node_editor.ui.dialogs.project_files_dialog import (
    ProjectFilesBrokenEntry,
    ProjectFilesDialog,
    ProjectFilesManagedEntry,
    ProjectFilesSnapshot,
    ProjectFilesStagedEntry,
)
from ea_node_editor.ui.shell.controllers.project_session_services_support.shared import (
    _NodePropertyPathBrowserProtocol,
    _ProjectFilesHostProtocol,
    _ProjectSessionHostProtocol,
    _WorkspaceSessionProtocol,
    normalize_project_path_value,
)


class ProjectFilesService:
    def __init__(
        self,
        host: _ProjectFilesHostProtocol,
        *,
        dialog_parent_source: _ProjectSessionHostProtocol,
        path_browser: _NodePropertyPathBrowserProtocol,
        workspace_session: _WorkspaceSessionProtocol,
    ) -> None:
        self._host = host
        self._dialog_parent_source = dialog_parent_source
        self._path_browser = path_browser
        self._workspace_session = workspace_session

    @staticmethod
    def _count_text(count: int, noun: str) -> str:
        suffix = "" if count == 1 else "s"
        return f"{count} {noun}{suffix}"

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

    def build_project_files_snapshot(
        self,
        *,
        project: ProjectData | None = None,
        project_path: str | Path | None = None,
    ) -> ProjectFilesSnapshot:
        current_project = project if project is not None else self._host.model.project
        resolved_project_path = normalize_project_path_value(
            project_path if project_path is not None else self._host.project_path
        )
        metadata = current_project.metadata if isinstance(current_project.metadata, dict) else {}
        store = ProjectArtifactStore.from_project_metadata(
            project_path=resolved_project_path,
            project_metadata=metadata,
        )
        layout = store.layout

        managed_entries = tuple(
            ProjectFilesManagedEntry(
                artifact_id=entry.artifact_id,
                relative_path=entry.relative_path,
                absolute_path=str(resolved_path) if resolved_path is not None else "",
                exists=bool(resolved_path is not None and resolved_path.exists() and resolved_path.is_file()),
            )
            for entry in store.state.artifacts.values()
            for resolved_path in (store.resolve_managed_path(entry.artifact_id),)
        )
        staged_entries = tuple(
            ProjectFilesStagedEntry(
                artifact_id=entry.artifact_id,
                relative_path=entry.relative_path or "",
                absolute_path=str(resolved_path) if resolved_path is not None else "",
                slot=entry.slot or "",
                exists=bool(resolved_path is not None and resolved_path.exists() and resolved_path.is_file()),
            )
            for entry in store.state.staged.values()
            for resolved_path in (store.resolve_staged_path(entry.artifact_id),)
        )

        broken_entries: list[ProjectFilesBrokenEntry] = []
        for workspace in current_project.workspaces.values():
            issue_map = collect_workspace_file_issue_map(
                workspace=workspace,
                registry=self._host.registry,
                project_path=resolved_project_path or None,
                project_metadata=metadata,
            )
            for (_node_id, _property_key), issue in sorted(
                issue_map.items(),
                key=lambda item: (
                    str(workspace.name or workspace.workspace_id),
                    str(item[1].node_id),
                    str(item[1].property_key),
                ),
            ):
                node = workspace.nodes.get(issue.node_id)
                broken_entries.append(
                    ProjectFilesBrokenEntry(
                        workspace_id=str(workspace.workspace_id),
                        workspace_name=str(workspace.name),
                        node_id=str(issue.node_id),
                        node_title=str(node.title) if node is not None else str(issue.node_id),
                        property_key=str(issue.property_key),
                        property_label=str(issue.property_label),
                        current_value=str(issue.property_value),
                        issue_kind=str(issue.issue_kind),
                        source_kind=str(issue.source_kind),
                        source_mode=str(issue.source_mode),
                        message=str(issue.message),
                    )
                )

        staging_root_path = ""
        if store.state.staged:
            if layout is not None:
                staging_root_path = str(layout.staging_root)
            elif store.staging_root_hint is not None:
                staging_root_path = str(store.staging_root_hint.as_path())

        return ProjectFilesSnapshot(
            project_path=resolved_project_path,
            data_root_path=str(layout.sidecar_root) if layout is not None else "",
            staging_root_path=staging_root_path,
            managed_entries=managed_entries,
            staged_entries=staged_entries,
            broken_entries=tuple(broken_entries),
        )

    @staticmethod
    def _project_files_prompt_headline(snapshot: ProjectFilesSnapshot) -> str:
        if snapshot.staged_count and snapshot.broken_count:
            return "This project contains staged data and broken file entries."
        if snapshot.staged_count:
            return "This project contains staged data."
        return "This project contains broken file entries."

    @classmethod
    def _project_files_prompt_details(cls, *, context_key: str, snapshot: ProjectFilesSnapshot) -> str:
        lines = [snapshot.summary_text]
        if snapshot.staged_count:
            staged_text = cls._count_text(snapshot.staged_count, "staged item").capitalize()
            if context_key in {"save", "save_as"}:
                lines.append(
                    f"{staged_text} stays scratch data until a project save commits the referenced items to the sibling .data folder."
                )
            elif context_key == "open":
                lines.append(
                    f"{staged_text} is still scratch data. Save the project after opening if you want it committed to the sibling .data folder."
                )
            else:
                lines.append(
                    f"{staged_text} will be restored as scratch data if you recover this autosave."
                )
        if snapshot.broken_count:
            broken_text = cls._count_text(snapshot.broken_count, "broken file entry").capitalize()
            lines.append(f"{broken_text} will remain unresolved until repaired.")
        lines.append("Choose Project Files... to inspect the full list.")
        return "\n\n".join(lines)

    def _dialog_parent(self):
        return self._dialog_parent_source.dialog_parent()

    def prompt_project_files_action(
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
        dialog = ProjectFilesDialog(
            snapshot=current_snapshot,
            repair_callback=self.repair_project_file_issue if repair_enabled else None,
            refresh_snapshot_callback=self.build_project_files_snapshot if repair_enabled else None,
            parent=self._dialog_parent(),
        )
        dialog.exec()

    def repair_project_file_issue(self, issue: ProjectFilesBrokenEntry) -> bool:
        workspace_id = str(issue.workspace_id or "").strip()
        current_workspace_id = str(self._host.workspace_manager.active_workspace_id() or "").strip()
        if not workspace_id or workspace_id not in self._host.model.project.workspaces:
            return False
        switched_workspace = workspace_id != current_workspace_id
        if switched_workspace:
            self._workspace_session.switch_workspace(workspace_id)
        try:
            repaired_value = self._path_browser.browse_node_property_path(
                issue.node_id,
                issue.property_key,
                issue.repair_request,
            )
            if not repaired_value:
                return False
            self._host.scene.set_node_property(issue.node_id, issue.property_key, repaired_value)
            return True
        finally:
            if switched_workspace and current_workspace_id:
                self._workspace_session.switch_workspace(current_workspace_id)


__all__ = ["ProjectFilesService"]
