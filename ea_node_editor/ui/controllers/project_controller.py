"""Handles project lifecycle: new, open, save, autosave, and session persistence."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import (
    AUTOSAVE_INTERVAL_MS,
    DEFAULT_UI_STATE,
    DEFAULT_WORKFLOW_SETTINGS,
    autosave_project_path,
    recent_session_path,
)
from ea_node_editor.workspace.manager import WorkspaceManager

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class ProjectController(QObject):
    project_changed = pyqtSignal()
    workspace_needs_refresh = pyqtSignal()

    def __init__(
        self,
        model: GraphModel,
        serializer: JsonProjectSerializer,
        workspace_manager: WorkspaceManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.serializer = serializer
        self.workspace_manager = workspace_manager
        self.project_path = ""
        self._last_manual_save_ts = 0.0
        self._last_autosave_fingerprint = ""
        self._autosave_recovery_deferred = False

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self.autosave_timer.timeout.connect(self._autosave_tick)

    def start_autosave(self) -> None:
        self.autosave_timer.start()

    def stop_autosave(self) -> None:
        self.autosave_timer.stop()

    @staticmethod
    def merge_defaults(values: Any, defaults: dict[str, Any]) -> dict[str, Any]:
        merged = json.loads(json.dumps(defaults))
        if not isinstance(values, dict):
            return merged
        for key, value in values.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = ProjectController.merge_defaults(value, merged[key])
            else:
                merged[key] = value
        return merged

    def ensure_project_metadata_defaults(self) -> None:
        metadata = self.model.project.metadata if isinstance(self.model.project.metadata, dict) else {}
        metadata["ui"] = self.merge_defaults(metadata.get("ui"), DEFAULT_UI_STATE)
        metadata["workflow_settings"] = self.merge_defaults(
            metadata.get("workflow_settings"), DEFAULT_WORKFLOW_SETTINGS,
        )
        self.model.project.metadata = metadata

    def workflow_settings_payload(self) -> dict[str, Any]:
        self.ensure_project_metadata_defaults()
        return self.merge_defaults(
            self.model.project.metadata.get("workflow_settings", {}),
            DEFAULT_WORKFLOW_SETTINGS,
        )

    def new_project(self) -> None:
        self.model = GraphModel(ProjectData(project_id="proj_local", name="untitled"))
        self.workspace_manager = WorkspaceManager(self.model)
        self.ensure_project_metadata_defaults()
        self.project_path = ""
        self._last_manual_save_ts = 0.0
        self._discard_autosave_snapshot()
        self._last_autosave_fingerprint = self._document_fingerprint(
            self.serializer.to_document(self.model.project)
        )
        self.project_changed.emit()

    def save_project(self, parent_widget: QWidget) -> None:
        path = self.project_path
        if not path:
            path, _ = QFileDialog.getSaveFileName(parent_widget, "Save Project", "", "EA Project (*.sfe)")
        if not path:
            return
        self.serializer.save(path, self.model.project)
        saved_path = Path(path).with_suffix(".sfe")
        self.project_path = str(saved_path)
        try:
            self._last_manual_save_ts = saved_path.stat().st_mtime
        except OSError:
            self._last_manual_save_ts = time.time()
        for workspace in self.model.project.workspaces.values():
            workspace.dirty = False
        self._discard_autosave_snapshot()
        self._last_autosave_fingerprint = self._document_fingerprint(
            self.serializer.to_document(self.model.project)
        )
        self.persist_session()
        self.project_changed.emit()

    def open_project(self, parent_widget: QWidget) -> bool:
        path, _ = QFileDialog.getOpenFileName(parent_widget, "Open Project", "", "EA Project (*.sfe)")
        if not path:
            return False
        try:
            project = self.serializer.load(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(parent_widget, "Open Project", f"Could not open project file.\n{exc}")
            return False
        resolved_path = Path(path).with_suffix(".sfe")
        self.model = GraphModel(project)
        self.workspace_manager = WorkspaceManager(self.model)
        self.ensure_project_metadata_defaults()
        self.project_path = str(resolved_path)
        try:
            self._last_manual_save_ts = resolved_path.stat().st_mtime
        except OSError:
            self._last_manual_save_ts = time.time()
        self._discard_autosave_snapshot()
        self._last_autosave_fingerprint = self._document_fingerprint(
            self.serializer.to_document(self.model.project)
        )
        self.persist_session()
        self.project_changed.emit()
        return True

    def restore_session(self) -> None:
        session = self._load_session_payload()
        session_project_path = str(session.get("project_path", "")).strip()
        self._last_manual_save_ts = self._coerce_timestamp(session.get("last_manual_save_ts", 0.0))

        restored = False
        if session_project_path and Path(session_project_path).exists():
            try:
                project = self.serializer.load(session_project_path)
                self.model = GraphModel(project)
                self.workspace_manager = WorkspaceManager(self.model)
                self.project_path = session_project_path
                self._last_manual_save_ts = max(
                    self._last_manual_save_ts,
                    Path(session_project_path).stat().st_mtime,
                )
                restored = True
            except Exception:  # noqa: BLE001
                self.project_path = ""

        if not restored:
            doc = session.get("project_doc")
            if isinstance(doc, dict):
                try:
                    project = self.serializer.from_document(doc)
                    self.model = GraphModel(project)
                    self.workspace_manager = WorkspaceManager(self.model)
                    self.project_path = ""
                    restored = True
                except Exception:  # noqa: BLE001
                    self.project_path = ""

        if not restored:
            self.project_path = ""

        self.ensure_project_metadata_defaults()
        self._last_autosave_fingerprint = self._document_fingerprint(
            self.serializer.to_document(self.model.project)
        )

    def persist_session(self, project_doc: dict[str, Any] | None = None) -> None:
        document = project_doc if isinstance(project_doc, dict) else self.serializer.to_document(self.model.project)
        session = {
            "project_path": self.project_path,
            "last_manual_save_ts": self._last_manual_save_ts,
            "project_doc": document,
        }
        try:
            self._write_json_atomic(recent_session_path(), session)
        except Exception:  # noqa: BLE001
            return

    def _autosave_tick(self) -> None:
        try:
            project_doc = self.serializer.to_document(self.model.project)
            fingerprint = self._document_fingerprint(project_doc)
            if fingerprint == self._last_autosave_fingerprint:
                return
            self._write_json_atomic(autosave_project_path(), project_doc)
            self._last_autosave_fingerprint = fingerprint
            self.persist_session(project_doc=project_doc)
        except Exception:  # noqa: BLE001
            return

    def _discard_autosave_snapshot(self) -> None:
        try:
            path = autosave_project_path()
            if path.exists():
                path.unlink()
        except OSError:
            pass
        self._last_autosave_fingerprint = ""

    @staticmethod
    def _document_fingerprint(project_doc: dict[str, Any]) -> str:
        return json.dumps(project_doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f"{path.name}.tmp")
        temp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )
        temp_path.replace(path)

    @staticmethod
    def _load_session_payload() -> dict[str, Any]:
        session_path = recent_session_path()
        if not session_path.exists():
            return {}
        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _coerce_timestamp(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
