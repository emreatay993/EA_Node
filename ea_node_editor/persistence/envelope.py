from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

PERSISTENCE_ENVELOPE_KEY = "_persistence_envelope"
LEGACY_RUNTIME_PERSISTENCE_KEY = "_runtime_unresolved_workspaces"

_WORKSPACE_LEGACY_ENVELOPE_KEYS = frozenset({"nodes", "edges", "node_overrides"})


def _copy_overlay_docs(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return {}
    copied: dict[str, dict[str, Any]] = {}
    for raw_key, raw_doc in payload.items():
        key = str(raw_key).strip()
        if not key or key in copied or not isinstance(raw_doc, Mapping):
            continue
        copied[key] = copy.deepcopy(dict(raw_doc))
    return copied


def _copy_doc_sequence_by_id(payload: Any, *, id_key: str) -> dict[str, dict[str, Any]]:
    if payload is None:
        return {}
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes, bytearray)):
        raise ValueError(f"Runtime persistence envelope '{id_key}' entries must be a JSON array.")
    copied: dict[str, dict[str, Any]] = {}
    for raw_doc in payload:
        if not isinstance(raw_doc, Mapping):
            continue
        doc_id = str(raw_doc.get(id_key, "")).strip()
        if not doc_id or doc_id in copied:
            continue
        copied[doc_id] = copy.deepcopy(dict(raw_doc))
    return copied


class ProjectDocumentFlavor(str, Enum):
    RUNTIME = "runtime"
    AUTHORED = "authored"


@dataclass(frozen=True, slots=True)
class ProjectPersistenceWorkspaceEnvelope:
    unresolved_node_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    unresolved_edge_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    authored_node_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_workspace(cls, workspace: Any) -> "ProjectPersistenceWorkspaceEnvelope":
        return cls(
            unresolved_node_docs=_copy_overlay_docs(getattr(workspace, "unresolved_node_docs", None)),
            unresolved_edge_docs=_copy_overlay_docs(getattr(workspace, "unresolved_edge_docs", None)),
            authored_node_overrides=_copy_overlay_docs(getattr(workspace, "authored_node_overrides", None)),
        )

    @classmethod
    def from_metadata(cls, payload: Any) -> "ProjectPersistenceWorkspaceEnvelope":
        if payload is None:
            return cls()
        if not isinstance(payload, Mapping):
            raise ValueError("Runtime persistence workspace envelope must be a JSON object.")
        legacy_keys = sorted(str(key) for key in payload if str(key) in _WORKSPACE_LEGACY_ENVELOPE_KEYS)
        if legacy_keys:
            raise ValueError(
                "Runtime persistence envelope uses legacy keys: "
                + ", ".join(legacy_keys)
                + ". Use unresolved_nodes, unresolved_edges, and authored_node_overrides."
            )
        authored_overrides = payload.get("authored_node_overrides")
        if authored_overrides is not None and not isinstance(authored_overrides, Mapping):
            raise ValueError("Runtime persistence authored_node_overrides must be a JSON object.")
        return cls(
            unresolved_node_docs=_copy_doc_sequence_by_id(payload.get("unresolved_nodes"), id_key="node_id"),
            unresolved_edge_docs=_copy_doc_sequence_by_id(payload.get("unresolved_edges"), id_key="edge_id"),
            authored_node_overrides=_copy_overlay_docs(authored_overrides),
        )

    @property
    def empty(self) -> bool:
        return (
            not self.unresolved_node_docs
            and not self.unresolved_edge_docs
            and not self.authored_node_overrides
        )

    def to_metadata_value(self) -> dict[str, Any]:
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


@dataclass(frozen=True, slots=True)
class ProjectPersistenceEnvelope:
    document_flavor: ProjectDocumentFlavor = ProjectDocumentFlavor.RUNTIME
    workspace_envelopes: dict[str, ProjectPersistenceWorkspaceEnvelope] = field(default_factory=dict)

    @classmethod
    def runtime(
        cls,
        workspace_envelopes: Mapping[str, object] | None = None,
    ) -> "ProjectPersistenceEnvelope":
        normalized: dict[str, ProjectPersistenceWorkspaceEnvelope] = {}
        if isinstance(workspace_envelopes, Mapping):
            for raw_workspace_id, raw_envelope in workspace_envelopes.items():
                workspace_id = str(raw_workspace_id).strip()
                if not workspace_id:
                    continue
                if isinstance(raw_envelope, ProjectPersistenceWorkspaceEnvelope):
                    envelope = raw_envelope
                else:
                    envelope = ProjectPersistenceWorkspaceEnvelope.from_metadata(raw_envelope)
                if not envelope.empty:
                    normalized[workspace_id] = envelope
        return cls(
            document_flavor=ProjectDocumentFlavor.RUNTIME,
            workspace_envelopes=normalized,
        )

    @classmethod
    def from_workspaces(
        cls,
        workspaces: Mapping[str, Any],
        *,
        workspace_order: Sequence[str] | None = None,
    ) -> "ProjectPersistenceEnvelope":
        ordered_ids = [
            workspace_id
            for workspace_id in (str(item).strip() for item in (workspace_order or ()))
            if workspace_id in workspaces
        ]
        ordered_ids.extend(
            workspace_id
            for workspace_id in sorted(str(item).strip() for item in workspaces)
            if workspace_id and workspace_id not in ordered_ids
        )
        envelopes: dict[str, ProjectPersistenceWorkspaceEnvelope] = {}
        for workspace_id in ordered_ids:
            envelope = ProjectPersistenceWorkspaceEnvelope.from_workspace(workspaces[workspace_id])
            if not envelope.empty:
                envelopes[workspace_id] = envelope
        return cls.runtime(envelopes)

    @classmethod
    def from_metadata_value(cls, payload: Any) -> "ProjectPersistenceEnvelope":
        if payload is None:
            return cls.runtime()
        if not isinstance(payload, Mapping):
            raise ValueError("Runtime persistence envelope metadata must be a JSON object.")
        flavor_value = str(payload.get("document_flavor", ProjectDocumentFlavor.RUNTIME.value)).strip()
        if not flavor_value:
            flavor_value = ProjectDocumentFlavor.RUNTIME.value
        try:
            flavor = ProjectDocumentFlavor(flavor_value)
        except ValueError as exc:
            raise ValueError(f"Unsupported persistence document flavor: {flavor_value}") from exc
        if flavor is not ProjectDocumentFlavor.RUNTIME:
            return cls(document_flavor=flavor)
        raw_workspaces = payload.get("workspaces")
        if raw_workspaces is None:
            return cls.runtime()
        if not isinstance(raw_workspaces, Mapping):
            raise ValueError("Runtime persistence envelope workspaces must be a JSON object.")
        return cls.runtime(raw_workspaces)

    @classmethod
    def from_document(cls, payload: Mapping[str, Any]) -> "ProjectPersistenceEnvelope":
        metadata = payload.get("metadata")
        if not isinstance(metadata, Mapping):
            return cls.runtime()
        if LEGACY_RUNTIME_PERSISTENCE_KEY in metadata:
            raise ValueError(
                "Legacy runtime persistence metadata is not supported. "
                "Persist the current workspace graph shape instead."
            )
        return cls.from_metadata_value(metadata.get(PERSISTENCE_ENVELOPE_KEY))

    def metadata_value(self) -> dict[str, Any] | None:
        if self.document_flavor is not ProjectDocumentFlavor.RUNTIME or not self.workspace_envelopes:
            return None
        workspaces = {
            workspace_id: envelope.to_metadata_value()
            for workspace_id, envelope in sorted(self.workspace_envelopes.items())
            if not envelope.empty
        }
        if not workspaces:
            return None
        return {
            "document_flavor": ProjectDocumentFlavor.RUNTIME.value,
            "workspaces": workspaces,
        }

    def workspace_envelope(self, workspace_id: str) -> ProjectPersistenceWorkspaceEnvelope:
        return self.workspace_envelopes.get(
            str(workspace_id).strip(),
            ProjectPersistenceWorkspaceEnvelope(),
        )


def install_workspace_persistence_envelope(
    workspace: Any,
    envelope: ProjectPersistenceWorkspaceEnvelope,
) -> None:
    for attr_name in ("unresolved_node_docs", "unresolved_edge_docs", "authored_node_overrides"):
        if hasattr(workspace, attr_name):
            delattr(workspace, attr_name)
    if envelope.unresolved_node_docs:
        setattr(workspace, "unresolved_node_docs", copy.deepcopy(envelope.unresolved_node_docs))
    if envelope.unresolved_edge_docs:
        setattr(workspace, "unresolved_edge_docs", copy.deepcopy(envelope.unresolved_edge_docs))
    if envelope.authored_node_overrides:
        setattr(workspace, "authored_node_overrides", copy.deepcopy(envelope.authored_node_overrides))


__all__ = [
    "LEGACY_RUNTIME_PERSISTENCE_KEY",
    "PERSISTENCE_ENVELOPE_KEY",
    "ProjectDocumentFlavor",
    "ProjectPersistenceEnvelope",
    "ProjectPersistenceWorkspaceEnvelope",
    "install_workspace_persistence_envelope",
]
