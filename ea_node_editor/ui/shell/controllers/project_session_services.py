from __future__ import annotations

import copy
import shutil
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Protocol

from ea_node_editor.graph.file_issue_state import collect_workspace_file_issue_map
from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.persistence.artifact_store import ProjectArtifactLayout, ProjectArtifactStore
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
from ea_node_editor.ui.dialogs.project_files_dialog import (
    ProjectFilesBrokenEntry,
    ProjectFilesDialog,
    ProjectFilesManagedEntry,
    ProjectFilesSnapshot,
    ProjectFilesStagedEntry,
)
from ea_node_editor.ui.passive_style_presets import normalize_passive_style_presets
from ea_node_editor.ui.shell.state import ShellProjectSessionState
from ea_node_editor.workspace.manager import WorkspaceManager


def normalize_project_path_value(path: str | Path | object) -> str:
    raw_path = str(path).strip()
    if not raw_path:
        return ""
    try:
        return str(Path(raw_path).expanduser().with_suffix(".sfe"))
    except ValueError:
        return ""


def normalized_recent_project_paths_value(
    paths: Iterable[object],
    *,
    limit: int,
) -> list[str]:
    normalized_paths: list[str] = []
    seen_paths: set[str] = set()
    for path in paths:
        normalized_path = normalize_project_path_value(path)
        if not normalized_path or normalized_path in seen_paths:
            continue
        seen_paths.add(normalized_path)
        normalized_paths.append(normalized_path)
        if len(normalized_paths) >= limit:
            break
    return normalized_paths


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
    library_pane_reset_requested: Any
    node_library_changed: Any
    project_path: str

    def _refresh_recent_projects_menu(self) -> None: ...

    def _prompt_recover_autosave(self, recovered_project: ProjectData | None = None): ...

    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str: ...

    def isVisible(self) -> bool: ...


class ProjectFilesService:
    def __init__(self, host: _ProjectSessionHostProtocol) -> None:
        self._host = host

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
        from PyQt6.QtWidgets import QWidget

        return self._host if isinstance(self._host, QWidget) else None

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
            self._host.workspace_library_controller.switch_workspace(workspace_id)
        try:
            repaired_value = self._host.browse_node_property_path(
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
                self._host.workspace_library_controller.switch_workspace(current_workspace_id)


class ProjectSessionLifecycleService:
    def __init__(self, host: _ProjectSessionHostProtocol, *, project_files: ProjectFilesService) -> None:
        self._host = host
        self._project_files = project_files
        self._document_service: ProjectDocumentIOService | None = None

    def bind_document_service(self, document_service: "ProjectDocumentIOService") -> None:
        self._document_service = document_service

    @property
    def _session_state(self) -> ShellProjectSessionState:
        return self._host.project_session_state

    def _refresh_recent_projects_menu(self) -> None:
        refresh_menu = getattr(self._host, "_refresh_recent_projects_menu", None)
        if callable(refresh_menu):
            refresh_menu()

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
                self._require_document_service()._install_project(project, project_path=session_project_path)
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
                    self._require_document_service()._install_project(project, project_path="")
                    restored = True
                except Exception:  # noqa: BLE001
                    self._host.project_path = ""

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

        if not self._host.isVisible():
            self._session_state.autosave_recovery_deferred = True
            return None

        choice = self._host._prompt_recover_autosave(recovered_project)
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
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self._host.workspace_library_controller.switch_workspace(self._host.workspace_manager.active_workspace_id())
        self._require_document_service().restore_script_editor_state()
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
        self._project_files.discard_staged_scratch_data()
        self.discard_autosave_snapshot()
        self.persist_session()

    def persist_session(self, project_doc: dict[str, Any] | None = None) -> None:
        self._host.workspace_library_controller.save_active_view_state()
        self._require_document_service().persist_script_editor_state()
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

    def _require_document_service(self) -> "ProjectDocumentIOService":
        if self._document_service is None:
            raise RuntimeError("Project document service is not bound.")
        return self._document_service


class ProjectDocumentIOService:
    def __init__(
        self,
        host: _ProjectSessionHostProtocol,
        *,
        project_files: ProjectFilesService,
        session: ProjectSessionLifecycleService,
    ) -> None:
        self._host = host
        self._project_files = project_files
        self._session = session

    @staticmethod
    def _delete_save_as_sidecar_path(path: Path) -> None:
        if not path.exists():
            return
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
            return
        path.unlink(missing_ok=True)

    @classmethod
    def _copy_save_as_payload(cls, source_path: Path, destination_path: Path) -> None:
        if source_path == destination_path:
            return
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        cls._delete_save_as_sidecar_path(destination_path)
        if source_path.is_dir() and not source_path.is_symlink():
            shutil.copytree(source_path, destination_path)
            return
        shutil.copy2(source_path, destination_path)

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
        self._session.persist_session()

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
        self._host.node_library_changed.emit()

    def _finalize_loaded_project(self, project: ProjectData, *, project_path: str) -> None:
        resolved_path = Path(project_path)
        self._install_project(project, project_path=str(resolved_path))
        self.ensure_project_metadata_defaults()
        try:
            self._session._session_state.last_manual_save_ts = resolved_path.stat().st_mtime
        except OSError:
            self._session._session_state.last_manual_save_ts = time.time()
        self._session.discard_autosave_snapshot()
        self._session._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self._session.add_recent_project_path(str(resolved_path), persist=False)
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self._host.workspace_library_controller.switch_workspace(self._host.workspace_manager.active_workspace_id())
        self.restore_script_editor_state()
        self._session.persist_session()
        self._host.project_meta_changed.emit()

    def _default_save_as_path(self) -> str:
        current_project_path = normalize_project_path_value(self._host.project_path)
        if current_project_path:
            return current_project_path
        project_name = str(getattr(self._host.model.project, "name", "")).strip() or "untitled"
        return str(Path(project_name).with_suffix(".sfe"))

    def _reset_save_as_destination_sidecar(self, saved_path: Path) -> None:
        layout = ProjectArtifactLayout.from_project_path(saved_path)
        for sidecar_path in (layout.assets_root, layout.artifacts_root, layout.staging_root):
            self._delete_save_as_sidecar_path(sidecar_path)

    def _build_save_as_artifact_store_metadata(
        self,
        *,
        saved_path: Path,
        source_document: Mapping[str, Any],
        referenced_managed_ids: Iterable[object],
        copy_managed_data: bool,
    ) -> dict[str, Any]:
        source_metadata = (
            dict(source_document.get("metadata", {}))
            if isinstance(source_document.get("metadata"), Mapping)
            else {}
        )
        source_store = ProjectArtifactStore.from_project_metadata(
            project_path=self._host.project_path,
            project_metadata=source_metadata,
        )
        normalized_source_metadata = source_store.metadata
        destination_layout = ProjectArtifactLayout.from_project_path(saved_path)
        destination_metadata = {
            str(key): copy.deepcopy(value)
            for key, value in normalized_source_metadata.items()
            if str(key) not in {PROJECT_ARTIFACT_STORE_METADATA_KEY, "artifacts", "staged", "staging_root"}
        }
        destination_metadata["artifacts"] = {}
        destination_metadata["staged"] = {}

        self._reset_save_as_destination_sidecar(saved_path)

        normalized_managed_ids = sorted(
            {
                str(artifact_id).strip()
                for artifact_id in referenced_managed_ids
                if str(artifact_id).strip()
            }
        )
        for artifact_id in normalized_managed_ids:
            managed_entry = source_store.managed_entry(artifact_id)
            if managed_entry is None:
                continue
            destination_metadata["artifacts"][artifact_id] = managed_entry.to_metadata_entry()
            if not copy_managed_data:
                continue
            source_path = source_store.resolve_managed_path(artifact_id)
            if source_path is None or not source_path.exists():
                continue
            destination_path = destination_layout.absolute_path_for_relative(managed_entry.relative_path)
            self._copy_save_as_payload(source_path, destination_path)
        return destination_metadata

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

    def save_project(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtWidgets import QMessageBox

        snapshot = self._project_files.build_project_files_snapshot()
        if not self._project_files.prompt_project_files_action(
            title="Save Project",
            text=self._project_files._project_files_prompt_headline(snapshot),
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
        self._project_files._set_project_artifact_store(store)
        self._host.project_path = str(saved_path)
        try:
            self._session._session_state.last_manual_save_ts = saved_path.stat().st_mtime
        except OSError:
            self._session._session_state.last_manual_save_ts = time.time()
        for workspace in self._host.model.project.workspaces.values():
            workspace.dirty = False
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self._session.discard_autosave_snapshot()
        self._session._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self._session.add_recent_project_path(str(saved_path), persist=False)
        self._session.persist_session()
        self._host.project_meta_changed.emit()

    def save_project_as(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtWidgets import QMessageBox

        from ea_node_editor.ui.dialogs.project_save_as_dialog import ProjectSaveAsDialog

        snapshot = self._project_files.build_project_files_snapshot()
        if not self._project_files.prompt_project_files_action(
            title="Save Project As",
            text=self._project_files._project_files_prompt_headline(snapshot),
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
        normalized_path = normalize_project_path_value(path)
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

        current_project_path = normalize_project_path_value(self._host.project_path)
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
            self._session._session_state.last_manual_save_ts = saved_path.stat().st_mtime
        except OSError:
            self._session._session_state.last_manual_save_ts = time.time()
        for workspace in self._host.model.project.workspaces.values():
            workspace.dirty = False
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self._session.discard_autosave_snapshot()
        self._session._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self._session.add_recent_project_path(str(saved_path), persist=False)
        self._session.persist_session()
        self._host.project_meta_changed.emit()

    def new_project(self) -> None:
        project = ProjectData(project_id="proj_local", name="untitled")
        self._install_project(project, project_path="")
        self.ensure_project_metadata_defaults()
        self._session._session_state.last_manual_save_ts = 0.0
        self._session.discard_autosave_snapshot()
        self._session._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self._host.workspace_library_controller.refresh_workspace_tabs()
        self._host.workspace_library_controller.switch_workspace(self._host.workspace_manager.active_workspace_id())
        self.restore_script_editor_state()
        self._session.persist_session()
        self._host.project_meta_changed.emit()

    def open_project(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self._host, "Open Project", "", "EA Project (*.sfe)")
        if not path:
            return
        self.open_project_path(path, show_errors=True)

    def open_project_path(self, path: str | Path, *, show_errors: bool = True) -> bool:
        from PyQt6.QtWidgets import QMessageBox

        normalized_path = normalize_project_path_value(path)
        if not normalized_path:
            return False
        resolved_path = Path(normalized_path)
        if not resolved_path.exists():
            self._session.remove_recent_project_path(normalized_path, persist=False)
            self._session.persist_session()
            if show_errors:
                QMessageBox.warning(self._host, "Open Project", f"Project file not found.\n{resolved_path}")
            return False
        try:
            project = self._host.serializer.load(str(resolved_path))
        except Exception as exc:  # noqa: BLE001
            if show_errors:
                QMessageBox.warning(self._host, "Open Project", f"Could not open project file.\n{exc}")
            return False
        snapshot = self._project_files.build_project_files_snapshot(project=project, project_path=resolved_path)
        if not self._project_files.prompt_project_files_action(
            title="Open Project",
            text=self._project_files._project_files_prompt_headline(snapshot),
            continue_label="Open Project",
            cancel_standard_button=QMessageBox.StandardButton.Cancel,
            snapshot=snapshot,
            context_key="open",
            allow_repair=False,
        ):
            return False
        self._finalize_loaded_project(project, project_path=str(resolved_path))
        return True

