from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable, Protocol

from ea_node_editor.graph.model import ProjectData
from ea_node_editor.persistence.serializer import ProjectDocumentSnapshot
from ea_node_editor.settings import autosave_project_path, recent_session_path
from ea_node_editor.persistence.utils import (
    coerce_timestamp as coerce_timestamp_value,
    document_fingerprint as document_fingerprint_value,
    write_json_atomic,
)


class _SerializerProtocol(Protocol):
    def load(self, path: str) -> ProjectData:
        ...

    def to_document(self, project: ProjectData) -> dict[str, Any]:
        ...


class SessionAutosaveStore:
    def __init__(
        self,
        *,
        serializer: _SerializerProtocol,
        session_path_provider: Callable[[], Path] = recent_session_path,
        autosave_path_provider: Callable[[], Path] = autosave_project_path,
    ) -> None:
        self._serializer = serializer
        self._session_path_provider = session_path_provider
        self._autosave_path_provider = autosave_path_provider

    def load_session_payload(self) -> dict[str, Any]:
        session_path = self._session_path_provider()
        if not session_path.exists():
            return {}
        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
        return payload if isinstance(payload, dict) else {}

    def _coerce_snapshot(
        self,
        *,
        project_snapshot: ProjectDocumentSnapshot | Mapping[str, Any] | None = None,
        project_doc: Mapping[str, Any] | None = None,
    ) -> ProjectDocumentSnapshot:
        if isinstance(project_snapshot, ProjectDocumentSnapshot):
            return project_snapshot
        if isinstance(project_snapshot, Mapping):
            return ProjectDocumentSnapshot.from_mapping(project_snapshot)
        return ProjectDocumentSnapshot.from_mapping(project_doc)

    def _project_snapshot(self, project: ProjectData) -> ProjectDocumentSnapshot:
        return ProjectDocumentSnapshot.from_mapping(self._serializer.to_document(project))

    def persist_session(
        self,
        *,
        project_path: str,
        last_manual_save_ts: float,
        recent_project_paths: list[str],
        project_doc: Mapping[str, Any] | None = None,
        project_snapshot: ProjectDocumentSnapshot | Mapping[str, Any] | None = None,
    ) -> None:
        snapshot = self._coerce_snapshot(project_snapshot=project_snapshot, project_doc=project_doc)
        session_payload = {
            "project_path": project_path,
            "last_manual_save_ts": last_manual_save_ts,
            "project_doc": snapshot.document,
            "recent_project_paths": recent_project_paths,
        }
        write_json_atomic(self._session_path_provider(), session_payload)

    def discard_autosave_snapshot(self) -> None:
        autosave_path = self._autosave_path_provider()
        if not autosave_path.exists():
            return
        try:
            autosave_path.unlink()
        except OSError:
            return

    def autosave_if_changed(
        self,
        *,
        last_fingerprint: str,
        project_doc: Mapping[str, Any] | None = None,
        project_snapshot: ProjectDocumentSnapshot | Mapping[str, Any] | None = None,
    ) -> str:
        snapshot = self._coerce_snapshot(project_snapshot=project_snapshot, project_doc=project_doc)
        if snapshot.fingerprint == last_fingerprint:
            return last_fingerprint
        write_json_atomic(self._autosave_path_provider(), snapshot.document)
        return snapshot.fingerprint

    def load_recoverable_autosave(
        self,
        *,
        project_path: str,
        last_manual_save_ts: float,
        current_project_doc: Mapping[str, Any] | None = None,
        current_project_snapshot: ProjectDocumentSnapshot | Mapping[str, Any] | None = None,
    ) -> ProjectData | None:
        current_snapshot = self._coerce_snapshot(
            project_snapshot=current_project_snapshot,
            project_doc=current_project_doc,
        )
        autosave_path = self._autosave_path_provider()
        if not autosave_path.exists():
            return None

        try:
            autosave_ts = autosave_path.stat().st_mtime
        except OSError:
            return None

        manual_save_ts = last_manual_save_ts
        if project_path and Path(project_path).exists():
            try:
                manual_save_ts = max(manual_save_ts, Path(project_path).stat().st_mtime)
            except OSError:
                pass
        if autosave_ts <= manual_save_ts:
            return None

        try:
            recovered_project = self._serializer.load(str(autosave_path))
        except Exception:  # noqa: BLE001
            self.discard_autosave_snapshot()
            return None

        recovered_snapshot = self._project_snapshot(recovered_project)
        if current_snapshot.fingerprint == recovered_snapshot.fingerprint:
            self.discard_autosave_snapshot()
            return None

        return recovered_project

    @staticmethod
    def coerce_timestamp(value: Any) -> float:
        return coerce_timestamp_value(value)

    @staticmethod
    def document_fingerprint(project_doc: Mapping[str, Any] | ProjectDocumentSnapshot) -> str:
        if isinstance(project_doc, ProjectDocumentSnapshot):
            return project_doc.fingerprint
        return document_fingerprint_value(dict(project_doc))
