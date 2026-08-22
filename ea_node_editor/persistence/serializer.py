from __future__ import annotations

import copy
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ea_node_editor.graph.project_state import ProjectData
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.settings import PROJECT_EXTENSION

from .migration import (
    JsonProjectMigration,
    ProjectSessionMetadata,
    ProjectUiSessionMetadata,
    ScriptEditorSessionState,
)
from .image_blobs import (
    externalize_project_images,
    hydrate_project_images,
    prune_project_images,
    tracked_project_image_digests,
)
from .project_codec import JsonProjectCodec
from ea_node_editor.common.payload_tools import (
    document_fingerprint as document_fingerprint_value,
    encode_json_payload,
)

__all__ = [
    "JsonProjectSerializer",
    "ProjectDocumentSnapshot",
    "ProjectSessionMetadata",
    "ProjectUiSessionMetadata",
    "ScriptEditorSessionState",
]


@dataclass(frozen=True, slots=True)
class ProjectDocumentSnapshot:
    document: dict[str, Any]
    fingerprint: str
    encoded_payload: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "ProjectDocumentSnapshot":
        document = copy.deepcopy(dict(payload)) if isinstance(payload, Mapping) else {}
        encoded_payload = encode_json_payload(document)
        return cls(
            document=document,
            fingerprint=document_fingerprint_value(document, encoded_payload=encoded_payload),
            encoded_payload=encoded_payload,
        )

    @classmethod
    def from_owned_document(cls, document: dict[str, Any] | None) -> "ProjectDocumentSnapshot":
        owned_document = document if isinstance(document, dict) else {}
        encoded_payload = encode_json_payload(owned_document)
        return cls(
            document=owned_document,
            fingerprint=document_fingerprint_value(owned_document, encoded_payload=encoded_payload),
            encoded_payload=encoded_payload,
        )


class JsonProjectSerializer:
    def __init__(self, registry: NodeRegistry) -> None:
        self._registry = registry
        self._migration = JsonProjectMigration(self._registry)
        self._codec = JsonProjectCodec(self._registry)

    def load(self, path: str) -> ProjectData:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        payload = hydrate_project_images(payload, project_path=path, catalog=self._registry.data_types)
        return self.from_document(payload)

    def save(self, path: str, project: ProjectData) -> None:
        self.save_document(path, self.to_persistent_document(project))

    def save_document(self, path: str, document: Mapping[str, Any]) -> None:
        self._codec.validate_persistent_document(document)
        target = Path(path)
        if target.suffix.lower() != PROJECT_EXTENSION:
            target = target.with_suffix(PROJECT_EXTENSION)
        previous_digests = frozenset()
        if target.is_file():
            try:
                previous = json.loads(target.read_text(encoding="utf-8"))
                if isinstance(previous, Mapping):
                    previous_digests = tracked_project_image_digests(previous)
            except (OSError, TypeError, ValueError):
                pass
        prepared = externalize_project_images(
            document,
            project_path=target,
            catalog=self._registry.data_types,
        )
        retained_digests = tracked_project_image_digests(prepared)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        temporary_path = Path(temporary)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(encode_json_payload(prepared))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)
        try:
            prune_project_images(
                project_path=target,
                tracked_digests=previous_digests,
                retained_digests=retained_digests,
            )
        except Exception:  # noqa: BLE001 - pruning is post-commit and best effort.
            pass

    def to_document(self, project: ProjectData) -> dict[str, Any]:
        return self._codec.to_document(project)

    def document_snapshot(self, project: ProjectData) -> ProjectDocumentSnapshot:
        return self.snapshot_from_owned_document(self.to_document(project))

    @staticmethod
    def snapshot_from_mapping(payload: Mapping[str, Any] | None) -> ProjectDocumentSnapshot:
        return ProjectDocumentSnapshot.from_mapping(payload)

    @staticmethod
    def snapshot_from_owned_document(document: dict[str, Any] | None) -> ProjectDocumentSnapshot:
        return ProjectDocumentSnapshot.from_owned_document(document)

    def to_persistent_document(self, project: ProjectData) -> dict[str, Any]:
        return self._codec.to_persistent_document(project)

    def from_document(self, payload: dict[str, Any]) -> ProjectData:
        migrated = self.migrate(payload)
        project = self.from_migrated_document(migrated)
        project.migration_report = self._migration.last_report
        project.migration_source_schema_version = self._migration.source_schema_version
        if project.migration_report:
            for workspace in project.workspaces.values():
                workspace.dirty = True
        return project

    def from_migrated_document(self, payload: dict[str, Any]) -> ProjectData:
        return self._codec.from_document(payload)

    @property
    def last_load_phase_timings_ms(self) -> dict[str, float]:
        return dict(self._codec.last_load_phase_timings_ms)

    def migrate(self, raw_doc: dict[str, Any]) -> dict[str, Any]:
        return self._migration.migrate(raw_doc)
