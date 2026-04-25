from __future__ import annotations

import copy
import shutil
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.persistence.artifact_store import ProjectArtifactLayout, ProjectArtifactStore
from ea_node_editor.persistence.envelope import (
    ProjectPersistenceWorkspaceEnvelope,
    install_workspace_persistence_envelope,
)
from ea_node_editor.persistence.project_codec import (
    collect_project_artifact_references,
    rewrite_project_artifact_refs,
)
from ea_node_editor.persistence.serializer import ProjectSessionMetadata
from ea_node_editor.persistence.session_store import SessionAutosaveStore
from ea_node_editor.settings import PROJECT_ARTIFACT_STORE_METADATA_KEY
from ea_node_editor.ui.shell.controllers.project_session_services_support.project_files_service import (
    ProjectFilesService,
)
from ea_node_editor.ui.shell.controllers.project_session_services_support.session_lifecycle_service import (
    ProjectSessionLifecycleService,
)
from ea_node_editor.ui.shell.controllers.project_session_services_support.shared import (
    _ProjectDocumentIOHostProtocol,
    _ProjectSessionHostProtocol,
    _ScriptEditorPanelProtocol,
    _ViewerProjectLoaderProtocol,
    _WorkspaceSessionProtocol,
    normalize_project_path_value,
)
from ea_node_editor.ui.shell.workspace_flow import ShellWorkspaceManagerAdapter
from ea_node_editor.workspace.manager import WorkspaceManager


class ProjectDocumentIOService:
    def __init__(
        self,
        host: _ProjectDocumentIOHostProtocol,
        *,
        project_files: ProjectFilesService,
        session: ProjectSessionLifecycleService,
        dialog_parent_source: _ProjectSessionHostProtocol,
        workspace_session: _WorkspaceSessionProtocol,
        script_editor_panel: _ScriptEditorPanelProtocol,
        viewer_project_loader: _ViewerProjectLoaderProtocol,
    ) -> None:
        self._host = host
        self._project_files = project_files
        self._session = session
        self._dialog_parent_source = dialog_parent_source
        self._workspace_session = workspace_session
        self._script_editor_panel = script_editor_panel
        self._viewer_project_loader = viewer_project_loader

    def _dialog_parent(self) -> object | None:
        return self._dialog_parent_source.dialog_parent()

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
        session_metadata = ProjectSessionMetadata.from_mapping(self._host.model.project.metadata)
        self._host.model.project.metadata = session_metadata.to_mapping()

    def workflow_settings_payload(self) -> dict[str, Any]:
        session_metadata = ProjectSessionMetadata.from_mapping(self._host.model.project.metadata)
        self._host.model.project.metadata = session_metadata.to_mapping()
        return copy.deepcopy(session_metadata.workflow_settings)

    def persist_script_editor_state(self) -> None:
        session_metadata = ProjectSessionMetadata.from_mapping(self._host.model.project.metadata)
        self._host.model.project.metadata = session_metadata.with_script_editor_state(
            visible=self._script_editor_panel.visible,
            floating=self._script_editor_panel.floating,
        ).to_mapping()

    def restore_script_editor_state(self) -> None:
        session_metadata = ProjectSessionMetadata.from_mapping(self._host.model.project.metadata)
        self._host.model.project.metadata = session_metadata.to_mapping()
        state = session_metadata.ui.script_editor
        selected_node_id = self._host.scene.selected_node_id() or ""
        can_show_editor = bool(selected_node_id)
        visible = state.visible and can_show_editor
        floating = state.floating
        self._script_editor_panel.set_floating(floating)
        self._script_editor_panel.set_visible(visible)
        self._script_editor_panel.set_checked(visible)

    def _project_viewer_bridge_loaded(self, *, reseed_on_next_reset: bool) -> None:
        self._viewer_project_loader.project_loaded(
            self._host.model.project,
            self._host.registry,
            reseed_on_next_reset=reseed_on_next_reset,
        )

    def _clear_node_elapsed_timing_state_for_project_install(self) -> None:
        run_state = getattr(self._host, "run_state", None)
        if run_state is None:
            return
        changed = False
        started_at_lookup = getattr(run_state, "running_node_started_at_epoch_ms_by_node_id", None)
        if isinstance(started_at_lookup, dict) and started_at_lookup:
            started_at_lookup.clear()
            changed = True
        cached_elapsed_lookup = getattr(run_state, "cached_node_elapsed_ms_by_workspace_id", None)
        if isinstance(cached_elapsed_lookup, dict) and cached_elapsed_lookup:
            cached_elapsed_lookup.clear()
            changed = True
        if not changed:
            return
        commit_state_change = getattr(self._host, "_commit_node_execution_state_change", None)
        if callable(commit_state_change):
            commit_state_change()
            return
        run_state.node_execution_revision = int(getattr(run_state, "node_execution_revision", 0)) + 1
        state_changed_signal = getattr(self._host, "node_execution_state_changed", None)
        emit = getattr(state_changed_signal, "emit", None)
        if callable(emit):
            emit()

    def show_workflow_settings_dialog(self) -> None:
        from ea_node_editor.ui.dialogs.workflow_settings_dialog import WorkflowSettingsDialog

        session_metadata = ProjectSessionMetadata.from_mapping(self._host.model.project.metadata)
        self._host.model.project.metadata = session_metadata.to_mapping()
        dialog = WorkflowSettingsDialog(
            initial_settings=copy.deepcopy(session_metadata.workflow_settings),
            parent=self._dialog_parent(),
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self._host.model.project.metadata = session_metadata.with_workflow_settings(dialog.values()).to_mapping()
        self._session.persist_session()

    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        target_visible = bool(checked) if checked is not None else not self._script_editor_panel.visible
        self._script_editor_panel.set_visible(target_visible)
        self._script_editor_panel.set_checked(target_visible)
        self.persist_script_editor_state()
        if target_visible:
            node_id = self._host.scene.selected_node_id()
            if node_id:
                workspace = self._host.model.project.workspaces[self._host.workspace_manager.active_workspace_id()]
                self._script_editor_panel.set_node(workspace.nodes.get(node_id))
            self._script_editor_panel.focus_editor()

    def _install_project(
        self,
        project: ProjectData,
        *,
        project_path: str,
        reseed_viewer_projection_on_next_reset: bool = False,
    ) -> None:
        self._clear_node_elapsed_timing_state_for_project_install()
        normalize_project_for_registry(project, self._host.registry)
        self._host.model = GraphModel(project)
        self._host.workspace_manager = ShellWorkspaceManagerAdapter(WorkspaceManager(self._host.model), self._host.model)
        self._host.runtime_history.clear_all()
        self._host.project_path = project_path
        self._project_viewer_bridge_loaded(
            reseed_on_next_reset=reseed_viewer_projection_on_next_reset,
        )
        self._host.library_pane_reset_requested.emit()
        self._host.node_library_changed.emit()

    def _finalize_loaded_project(self, project: ProjectData, *, project_path: str) -> None:
        resolved_path = Path(project_path)
        self._install_project(
            project,
            project_path=str(resolved_path),
            reseed_viewer_projection_on_next_reset=True,
        )
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
        self._workspace_session.refresh_workspace_tabs()
        self._workspace_session.switch_workspace(self._host.model.active_workspace.workspace_id)
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
            envelope = ProjectPersistenceWorkspaceEnvelope.from_workspace(workspace)
            install_workspace_persistence_envelope(
                workspace,
                ProjectPersistenceWorkspaceEnvelope(
                    unresolved_node_docs={
                        node_id: rewrite_project_artifact_refs(node_doc, replacements)
                        for node_id, node_doc in envelope.unresolved_node_docs.items()
                    },
                    unresolved_edge_docs={
                        edge_id: rewrite_project_artifact_refs(edge_doc, replacements)
                        for edge_id, edge_doc in envelope.unresolved_edge_docs.items()
                    },
                    authored_node_overrides={
                        node_id: rewrite_project_artifact_refs(override_doc, replacements)
                        for node_id, override_doc in envelope.authored_node_overrides.items()
                    },
                ),
            )

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
            path, _ = QFileDialog.getSaveFileName(self._dialog_parent(), "Save Project", "", "EA Project (*.sfe)")
        if not path:
            return
        saved_path = Path(path).with_suffix(".sfe")
        self._workspace_session.save_active_view_state()
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
        self._workspace_session.refresh_workspace_tabs()
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
            self._dialog_parent(),
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
            parent=self._dialog_parent(),
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        current_project_path = normalize_project_path_value(self._host.project_path)
        if current_project_path and saved_path == Path(current_project_path):
            self.save_project()
            return

        copy_managed_data = dialog.selected_mode() == ProjectSaveAsDialog.SELF_CONTAINED_COPY

        self._workspace_session.save_active_view_state()
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
        self._workspace_session.refresh_workspace_tabs()
        self._session.discard_autosave_snapshot()
        self._session._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self._session.add_recent_project_path(str(saved_path), persist=False)
        self._session.persist_session()
        self._host.project_meta_changed.emit()

    def new_project(self) -> None:
        project = ProjectData(project_id="proj_local", name="untitled")
        self._install_project(
            project,
            project_path="",
            reseed_viewer_projection_on_next_reset=True,
        )
        self.ensure_project_metadata_defaults()
        self._session._session_state.last_manual_save_ts = 0.0
        self._session.discard_autosave_snapshot()
        self._session._session_state.last_autosave_fingerprint = SessionAutosaveStore.document_fingerprint(
            self._host.serializer.to_document(self._host.model.project)
        )
        self._workspace_session.refresh_workspace_tabs()
        self._workspace_session.switch_workspace(self._host.model.active_workspace.workspace_id)
        self.restore_script_editor_state()
        self._session.persist_session()
        self._host.project_meta_changed.emit()

    def open_project(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self._dialog_parent(), "Open Project", "", "EA Project (*.sfe)")
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
                QMessageBox.warning(self._dialog_parent(), "Open Project", f"Project file not found.\n{resolved_path}")
            return False
        try:
            project = self._host.serializer.load(str(resolved_path))
        except Exception as exc:  # noqa: BLE001
            if show_errors:
                QMessageBox.warning(self._dialog_parent(), "Open Project", f"Could not open project file.\n{exc}")
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


__all__ = ["ProjectDocumentIOService"]
