from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

from ea_node_editor.execution.runtime_dto import RuntimeWorkspace
from ea_node_editor.execution.runtime_value_codec import (
    deserialize_runtime_value,
    serialize_runtime_value,
)
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.persistence.artifact_store import normalize_artifact_store_metadata
from ea_node_editor.persistence.migration import JsonProjectMigration
from ea_node_editor.persistence.overlay import (
    LEGACY_RUNTIME_PERSISTENCE_KEY,
    PERSISTENCE_ENVELOPE_KEY,
)
from ea_node_editor.persistence.project_codec import ProjectPersistenceEnvelope, WorkspacePersistenceEnvelope
from ea_node_editor.settings import PROJECT_ARTIFACT_STORE_METADATA_KEY
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.workspace.ownership import resolve_workspace_ownership

if TYPE_CHECKING:
    from ea_node_editor.graph.model import ProjectData
    from ea_node_editor.nodes.registry import NodeRegistry
    from ea_node_editor.persistence.serializer import JsonProjectSerializer


@dataclass(slots=True, frozen=True)
class RuntimeSnapshot:
    schema_version: int = 0
    project_id: str = ""
    name: str = ""
    active_workspace_id: str = ""
    workspace_order: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    workspaces: tuple[RuntimeWorkspace, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RuntimeSnapshot:
        normalized_payload = deserialize_runtime_value(dict(payload))
        if not isinstance(normalized_payload, Mapping):
            normalized_payload = {}
        workspaces = tuple(
            RuntimeWorkspace.from_mapping(workspace_doc)
            for workspace_doc in normalized_payload.get("workspaces", [])
            if isinstance(workspace_doc, Mapping)
        )
        raw_workspace_order = normalized_payload.get("workspace_order")
        workspace_order = tuple(
            str(item).strip()
            for item in raw_workspace_order
            if str(item).strip()
        ) if isinstance(raw_workspace_order, (list, tuple)) else tuple(
            workspace.workspace_id
            for workspace in workspaces
            if workspace.workspace_id
        )
        return cls(
            schema_version=int(normalized_payload.get("schema_version", 0)),
            project_id=str(normalized_payload.get("project_id", "")).strip(),
            name=str(normalized_payload.get("name", "")),
            active_workspace_id=str(normalized_payload.get("active_workspace_id", "")).strip(),
            workspace_order=workspace_order,
            metadata=(
                copy.deepcopy(normalized_payload.get("metadata"))
                if isinstance(normalized_payload.get("metadata"), Mapping)
                else {}
            ),
            workspaces=workspaces,
        )

    @classmethod
    def from_project_data(cls, project: "ProjectData") -> RuntimeSnapshot:
        metadata = project.metadata if isinstance(project.metadata, Mapping) else {}
        ownership = resolve_workspace_ownership(
            project.workspaces,
            order_sources=(metadata.get("workspace_order"),),
            active_workspace_id=project.active_workspace_id,
        )
        runtime_metadata = JsonProjectMigration.normalize_metadata(metadata, ownership.workspace_order)
        runtime_metadata["artifact_store"] = normalize_artifact_store_metadata(runtime_metadata.get("artifact_store"))
        runtime_metadata.pop(PERSISTENCE_ENVELOPE_KEY, None)
        runtime_metadata.pop(LEGACY_RUNTIME_PERSISTENCE_KEY, None)

        workspaces: list[RuntimeWorkspace] = []
        workspace_envelopes: dict[str, WorkspacePersistenceEnvelope] = {}
        for workspace_id in ownership.workspace_order:
            workspace = project.workspaces[workspace_id]
            persistence_envelope = WorkspacePersistenceEnvelope.capture(workspace)
            workspaces.append(RuntimeWorkspace.from_workspace_data(workspace))
            if not persistence_envelope.is_empty:
                workspace_envelopes[workspace.workspace_id] = persistence_envelope

        runtime_envelope = ProjectPersistenceEnvelope.runtime(workspace_envelopes)
        metadata_value = runtime_envelope.metadata_value()
        if metadata_value is not None:
            runtime_metadata[PERSISTENCE_ENVELOPE_KEY] = metadata_value

        return cls(
            schema_version=SCHEMA_VERSION,
            project_id=project.project_id,
            name=project.name,
            active_workspace_id=ownership.active_workspace_id,
            workspace_order=tuple(ownership.workspace_order),
            metadata=runtime_metadata,
            workspaces=tuple(workspaces),
        )

    def workspace(self, workspace_id: str = "") -> RuntimeWorkspace:
        target_workspace_id = str(workspace_id or self.active_workspace_id).strip()
        for workspace in self.workspaces:
            if workspace.workspace_id == target_workspace_id:
                return workspace
        raise KeyError(f"Workspace not found in runtime snapshot: {target_workspace_id}")

    def to_document(self) -> dict[str, Any]:
        workspaces_by_id = {
            workspace.workspace_id: workspace.to_document()
            for workspace in self.workspaces
            if workspace.workspace_id
        }
        ordered_workspace_ids: list[str] = [
            workspace_id
            for workspace_id in self.workspace_order
            if workspace_id in workspaces_by_id
        ]
        ordered_workspace_ids.extend(
            workspace.workspace_id
            for workspace in self.workspaces
            if workspace.workspace_id and workspace.workspace_id not in ordered_workspace_ids
        )
        payload = {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "name": self.name,
            "active_workspace_id": self.active_workspace_id,
            "workspace_order": ordered_workspace_ids,
            "workspaces": [copy.deepcopy(workspaces_by_id[workspace_id]) for workspace_id in ordered_workspace_ids],
            "metadata": copy.deepcopy(self.metadata),
        }
        serialized = serialize_runtime_value(payload)
        return dict(serialized) if isinstance(serialized, Mapping) else payload


@dataclass(slots=True)
class RuntimeSnapshotContext:
    runtime_snapshot: RuntimeSnapshot | None = None
    project_path: str = ""
    artifact_store: ProjectArtifactStore | None = None

    def __post_init__(self) -> None:
        if self.artifact_store is None:
            self.artifact_store = ProjectArtifactStore.from_project_metadata(
                project_path=self.project_path or None,
                project_metadata=(
                    self.runtime_snapshot.metadata
                    if self.runtime_snapshot is not None
                    else None
                ),
            )

    @classmethod
    def from_snapshot(
        cls,
        runtime_snapshot: RuntimeSnapshot | None,
        *,
        project_path: str = "",
        artifact_store: ProjectArtifactStore | None = None,
    ) -> RuntimeSnapshotContext:
        return cls(
            runtime_snapshot=runtime_snapshot,
            project_path=str(project_path).strip(),
            artifact_store=artifact_store,
        )

    def project_metadata(self) -> dict[str, Any]:
        metadata = (
            copy.deepcopy(self.runtime_snapshot.metadata)
            if self.runtime_snapshot is not None
            else {}
        )
        artifact_store = self.artifact_store
        if artifact_store is None:
            metadata.pop(PROJECT_ARTIFACT_STORE_METADATA_KEY, None)
            return metadata
        metadata[PROJECT_ARTIFACT_STORE_METADATA_KEY] = artifact_store.metadata
        return metadata


def coerce_runtime_snapshot(value: RuntimeSnapshot | Mapping[str, Any] | None) -> RuntimeSnapshot | None:
    if isinstance(value, RuntimeSnapshot):
        return value
    if isinstance(value, Mapping):
        return RuntimeSnapshot.from_mapping(value)
    return None


def build_runtime_snapshot(
    project: "ProjectData",
    *,
    workspace_id: str,
    registry: "NodeRegistry",
    serializer: "JsonProjectSerializer | None" = None,
) -> RuntimeSnapshot:
    from ea_node_editor.graph.normalization import normalize_project_for_registry

    del serializer  # Compatibility parameter retained; runtime snapshots now build directly from domain data.
    project_copy = copy.deepcopy(project)
    normalize_project_for_registry(project_copy, registry)
    snapshot = RuntimeSnapshot.from_project_data(project_copy)
    snapshot.workspace(workspace_id)
    return snapshot


def sanitize_execution_trigger(trigger: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = copy.deepcopy(dict(trigger or {}))
    # `project_doc` is a retired execution trigger field; normal runs carry RuntimeSnapshot separately.
    payload.pop("project_doc", None)
    return payload


__all__ = [
    "RuntimeSnapshot",
    "RuntimeSnapshotContext",
    "build_runtime_snapshot",
    "coerce_runtime_snapshot",
    "sanitize_execution_trigger",
]
