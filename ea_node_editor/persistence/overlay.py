from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

PERSISTENCE_ENVELOPE_KEY = "_persistence_envelope"
LEGACY_RUNTIME_PERSISTENCE_KEY = "_runtime_unresolved_workspaces"


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


def _copy_overlay_doc_sequence(value: Any, *, id_key: str) -> dict[str, dict[str, Any]]:
    if isinstance(value, Mapping):
        raw_docs = value.values()
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        raw_docs = value
    else:
        return {}
    copied: dict[str, dict[str, Any]] = {}
    for raw_doc in raw_docs:
        if not isinstance(raw_doc, Mapping):
            continue
        copied_doc = copy.deepcopy(dict(raw_doc))
        entry_id = str(copied_doc.get(id_key, "")).strip()
        if not entry_id or entry_id in copied:
            continue
        copied_doc[id_key] = entry_id
        copied[entry_id] = copied_doc
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


@dataclass(slots=True, frozen=True)
class WorkspacePersistenceEnvelope:
    unresolved_node_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    unresolved_edge_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    authored_node_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (
            self.unresolved_node_docs
            or self.unresolved_edge_docs
            or self.authored_node_overrides
        )

    @classmethod
    def from_state(cls, state: WorkspacePersistenceState) -> "WorkspacePersistenceEnvelope":
        return cls(
            unresolved_node_docs=_copy_overlay_docs(state.unresolved_node_docs),
            unresolved_edge_docs=_copy_overlay_docs(state.unresolved_edge_docs),
            authored_node_overrides=_copy_overlay_docs(state.authored_node_overrides),
        )

    @classmethod
    def capture(cls, workspace: "WorkspacePersistenceStateOwner") -> "WorkspacePersistenceEnvelope":
        return cls.from_state(workspace.persistence_state)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "WorkspacePersistenceEnvelope":
        if not isinstance(value, Mapping):
            return cls()
        return cls(
            unresolved_node_docs=_copy_overlay_doc_sequence(
                value.get("unresolved_nodes", value.get("nodes")),
                id_key="node_id",
            ),
            unresolved_edge_docs=_copy_overlay_doc_sequence(
                value.get("unresolved_edges", value.get("edges")),
                id_key="edge_id",
            ),
            authored_node_overrides=_copy_overlay_docs(
                value.get("authored_node_overrides", value.get("node_overrides"))
            ),
        )

    def to_mapping(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.unresolved_node_docs:
            payload["unresolved_nodes"] = [
                copy.deepcopy(self.unresolved_node_docs[node_id])
                for node_id in sorted(self.unresolved_node_docs)
            ]
        if self.unresolved_edge_docs:
            payload["unresolved_edges"] = [
                copy.deepcopy(self.unresolved_edge_docs[edge_id])
                for edge_id in sorted(self.unresolved_edge_docs)
            ]
        if self.authored_node_overrides:
            payload["authored_node_overrides"] = {
                node_id: copy.deepcopy(self.authored_node_overrides[node_id])
                for node_id in sorted(self.authored_node_overrides)
                if self.authored_node_overrides[node_id]
            }
        return payload

    def to_state(self) -> WorkspacePersistenceState:
        state = WorkspacePersistenceState()
        self.apply_to(state)
        return state

    def apply_to(self, state: WorkspacePersistenceState) -> None:
        state.replace_unresolved_node_docs(self.unresolved_node_docs)
        state.replace_unresolved_edge_docs(self.unresolved_edge_docs)
        state.replace_authored_node_overrides(self.authored_node_overrides)


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
