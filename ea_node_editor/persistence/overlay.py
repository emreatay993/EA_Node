from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


def _copy_overlay_docs(value: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    copied: dict[str, dict[str, Any]] = {}
    for raw_key, raw_doc in value.items():
        key = str(raw_key).strip()
        if not key or not isinstance(raw_doc, Mapping):
            continue
        copied[key] = copy.deepcopy(dict(raw_doc))
    return copied


@dataclass(slots=True)
class WorkspacePersistenceState:
    unresolved_node_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    unresolved_edge_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    authored_node_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    def clone(self) -> "WorkspacePersistenceState":
        return WorkspacePersistenceState(
            unresolved_node_docs=_copy_overlay_docs(self.unresolved_node_docs),
            unresolved_edge_docs=_copy_overlay_docs(self.unresolved_edge_docs),
            authored_node_overrides=_copy_overlay_docs(self.authored_node_overrides),
        )

    @classmethod
    def capture(cls, workspace: WorkspacePersistenceStateOwner) -> "WorkspacePersistenceState":
        return workspace.persistence_state.clone()

    def restore(self, workspace: WorkspacePersistenceStateOwner) -> None:
        workspace.persistence_state = self.clone()

    def replace_unresolved_node_docs(self, value: Mapping[str, Any] | None) -> None:
        self.unresolved_node_docs = _copy_overlay_docs(value)

    def replace_unresolved_edge_docs(self, value: Mapping[str, Any] | None) -> None:
        self.unresolved_edge_docs = _copy_overlay_docs(value)

    def replace_authored_node_overrides(self, value: Mapping[str, Any] | None) -> None:
        self.authored_node_overrides = _copy_overlay_docs(value)

    def remove_node_references(self, node_id: str) -> None:
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return
        self.unresolved_node_docs.pop(normalized_node_id, None)
        self.authored_node_overrides.pop(normalized_node_id, None)
        for edge_id, edge_doc in list(self.unresolved_edge_docs.items()):
            if (
                str(edge_doc.get("source_node_id", "")).strip() == normalized_node_id
                or str(edge_doc.get("target_node_id", "")).strip() == normalized_node_id
            ):
                del self.unresolved_edge_docs[edge_id]
        for child_node_id, override in list(self.authored_node_overrides.items()):
            if str(override.get("parent_node_id", "")).strip() == normalized_node_id:
                del self.authored_node_overrides[child_node_id]


class WorkspacePersistenceStateOwner(Protocol):
    persistence_state: WorkspacePersistenceState


def workspace_persistence_overlay(workspace: WorkspacePersistenceStateOwner) -> WorkspacePersistenceState:
    return workspace.persistence_state


def copy_workspace_persistence_overlay(
    source: WorkspacePersistenceStateOwner,
    target: WorkspacePersistenceStateOwner,
) -> WorkspacePersistenceState:
    overlay = source.persistence_state.clone()
    target.persistence_state = overlay
    return overlay


def set_workspace_unresolved_node_docs(workspace: WorkspacePersistenceStateOwner, value: Mapping[str, Any] | None) -> None:
    workspace.persistence_state.replace_unresolved_node_docs(value)


def set_workspace_unresolved_edge_docs(workspace: WorkspacePersistenceStateOwner, value: Mapping[str, Any] | None) -> None:
    workspace.persistence_state.replace_unresolved_edge_docs(value)


def set_workspace_authored_node_overrides(
    workspace: WorkspacePersistenceStateOwner,
    value: Mapping[str, Any] | None,
) -> None:
    workspace.persistence_state.replace_authored_node_overrides(value)
