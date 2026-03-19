from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

from ea_node_editor.execution.runtime_dto import RuntimeWorkspace

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
        workspaces = tuple(
            RuntimeWorkspace.from_mapping(workspace_doc)
            for workspace_doc in payload.get("workspaces", [])
            if isinstance(workspace_doc, Mapping)
        )
        raw_workspace_order = payload.get("workspace_order")
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
            schema_version=int(payload.get("schema_version", 0)),
            project_id=str(payload.get("project_id", "")).strip(),
            name=str(payload.get("name", "")),
            active_workspace_id=str(payload.get("active_workspace_id", "")).strip(),
            workspace_order=workspace_order,
            metadata=copy.deepcopy(payload.get("metadata")) if isinstance(payload.get("metadata"), Mapping) else {},
            workspaces=workspaces,
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
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "name": self.name,
            "active_workspace_id": self.active_workspace_id,
            "workspace_order": ordered_workspace_ids,
            "workspaces": [copy.deepcopy(workspaces_by_id[workspace_id]) for workspace_id in ordered_workspace_ids],
            "metadata": copy.deepcopy(self.metadata),
        }


def coerce_runtime_snapshot(value: RuntimeSnapshot | Mapping[str, Any] | None) -> RuntimeSnapshot | None:
    if isinstance(value, RuntimeSnapshot):
        return value
    if isinstance(value, Mapping):
        return RuntimeSnapshot.from_mapping(value)
    return None


def runtime_snapshot_from_project_document(project_doc: Mapping[str, Any]) -> RuntimeSnapshot:
    return RuntimeSnapshot.from_mapping(project_doc)


def build_runtime_snapshot(
    project: "ProjectData",
    *,
    workspace_id: str,
    registry: "NodeRegistry",
    serializer: "JsonProjectSerializer | None" = None,
) -> RuntimeSnapshot:
    from ea_node_editor.graph.normalization import normalize_project_for_registry
    from ea_node_editor.persistence.serializer import JsonProjectSerializer

    project_copy = copy.deepcopy(project)
    normalize_project_for_registry(project_copy, registry)
    project_serializer = serializer or JsonProjectSerializer(registry)
    runtime_project_doc = project_serializer.to_document(project_copy)
    snapshot = RuntimeSnapshot.from_mapping(runtime_project_doc)
    snapshot.workspace(workspace_id)
    return snapshot


def build_execution_trigger(
    trigger: Mapping[str, Any] | None,
    runtime_snapshot: RuntimeSnapshot | None,
) -> dict[str, Any]:
    payload = copy.deepcopy(dict(trigger or {}))
    if runtime_snapshot is None:
        return payload
    if (
        str(payload.get("kind", "")).strip() == "manual"
        and "workflow_settings" in payload
        and "project_doc" not in payload
    ):
        payload["project_doc"] = runtime_snapshot.to_document()
    return payload


__all__ = [
    "RuntimeSnapshot",
    "build_execution_trigger",
    "build_runtime_snapshot",
    "coerce_runtime_snapshot",
    "runtime_snapshot_from_project_document",
]
