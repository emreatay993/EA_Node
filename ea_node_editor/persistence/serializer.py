from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ea_node_editor.graph.model import ProjectData
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.settings import PROJECT_EXTENSION

from .migration import JsonProjectMigration
from .project_codec import JsonProjectCodec


class JsonProjectSerializer:
    def __init__(self, registry: NodeRegistry) -> None:
        self._registry = registry
        self._migration = JsonProjectMigration(self._registry)
        self._codec = JsonProjectCodec()

    def load(self, path: str) -> ProjectData:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.from_document(payload)

    def save(self, path: str, project: ProjectData) -> None:
        target = Path(path)
        if target.suffix.lower() != PROJECT_EXTENSION:
            target = target.with_suffix(PROJECT_EXTENSION)
        doc = self.to_document(project)
        target.write_text(
            json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

    def to_document(self, project: ProjectData) -> dict[str, Any]:
        return self._codec.to_document(project)

    def from_document(self, payload: dict[str, Any]) -> ProjectData:
        migrated = self.migrate(payload)
        return self._codec.from_document(migrated)

    def migrate(self, raw_doc: dict[str, Any]) -> dict[str, Any]:
        return self._migration.migrate(raw_doc)
