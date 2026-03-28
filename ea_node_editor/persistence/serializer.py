from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ea_node_editor.graph.model import ProjectData
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.settings import PROJECT_EXTENSION

from .migration import (
    JsonProjectMigration,
    ProjectSessionMetadata,
    ProjectUiSessionMetadata,
    ScriptEditorSessionState,
)
from .project_codec import JsonProjectCodec
from .utils import document_fingerprint as document_fingerprint_value

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

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "ProjectDocumentSnapshot":
        document = copy.deepcopy(dict(payload)) if isinstance(payload, Mapping) else {}
        return cls(
            document=document,
            fingerprint=document_fingerprint_value(document),
        )


class JsonProjectSerializer:
    def __init__(self, registry: NodeRegistry) -> None:
        self._registry = registry
        self._migration = JsonProjectMigration(self._registry)
        self._codec = JsonProjectCodec(self._registry)

    def load(self, path: str) -> ProjectData:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.from_document(payload)

    def save(self, path: str, project: ProjectData) -> None:
        self.save_document(path, self.to_persistent_document(project))

    def save_document(self, path: str, document: Mapping[str, Any]) -> None:
        target = Path(path)
        if target.suffix.lower() != PROJECT_EXTENSION:
            target = target.with_suffix(PROJECT_EXTENSION)
        target.write_text(
            json.dumps(copy.deepcopy(dict(document)), indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

    def to_document(self, project: ProjectData) -> dict[str, Any]:
        return self._codec.to_document(project)

    def document_snapshot(self, project: ProjectData) -> ProjectDocumentSnapshot:
        return ProjectDocumentSnapshot.from_mapping(self.to_document(project))

    @staticmethod
    def snapshot_from_mapping(payload: Mapping[str, Any] | None) -> ProjectDocumentSnapshot:
        return ProjectDocumentSnapshot.from_mapping(payload)

    def to_persistent_document(self, project: ProjectData) -> dict[str, Any]:
        return self._codec.to_persistent_document(project)

    def from_document(self, payload: dict[str, Any]) -> ProjectData:
        migrated = self.migrate(payload)
        return self._codec.from_document(migrated)

    def migrate(self, raw_doc: dict[str, Any]) -> dict[str, Any]:
        return self._migration.migrate(raw_doc)
