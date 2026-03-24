from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ea_node_editor.graph.hierarchy import normalize_scope_path
from ea_node_editor.graph.model import (
    ProjectData,
    ViewState,
    WorkspacePersistenceState,
    WorkspaceData,
    edge_instance_from_mapping,
    edge_instance_to_mapping,
    node_instance_from_mapping,
    node_instance_to_mapping,
    sanitize_workspace_parent_links,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.artifact_refs import (
    ManagedArtifactRef,
    StagedArtifactRef,
    parse_artifact_ref,
)
from ea_node_editor.persistence.artifact_store import normalize_artifact_store_metadata
from ea_node_editor.persistence.migration import JsonProjectMigration
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.workspace.ownership import resolve_workspace_ownership, sync_project_workspace_ownership

_RUNTIME_PRESERVATION_KEY = "_runtime_unresolved_workspaces"
_COMMENT_BACKDROP_RUNTIME_MEMBERSHIP_KEYS = (
    "owner_backdrop_id",
    "backdrop_depth",
    "member_node_ids",
    "member_backdrop_ids",
    "contained_node_ids",
    "contained_backdrop_ids",
)


@dataclass(frozen=True, slots=True)
class ProjectArtifactReferenceSet:
    managed_ids: frozenset[str]
    staged_ids: frozenset[str]


def collect_project_artifact_references(payload: Any) -> ProjectArtifactReferenceSet:
    managed_ids: set[str] = set()
    staged_ids: set[str] = set()
    _collect_project_artifact_references(payload, managed_ids=managed_ids, staged_ids=staged_ids)
    return ProjectArtifactReferenceSet(
        managed_ids=frozenset(managed_ids),
        staged_ids=frozenset(staged_ids),
    )


def _collect_project_artifact_references(
    payload: Any,
    *,
    managed_ids: set[str],
    staged_ids: set[str],
) -> None:
    if isinstance(payload, str):
        parsed = parse_artifact_ref(payload)
        if isinstance(parsed, ManagedArtifactRef):
            managed_ids.add(parsed.artifact_id)
        elif isinstance(parsed, StagedArtifactRef):
            staged_ids.add(parsed.artifact_id)
        return
    if isinstance(payload, Mapping):
        for value in payload.values():
            _collect_project_artifact_references(value, managed_ids=managed_ids, staged_ids=staged_ids)
        return
    if isinstance(payload, list | tuple | set | frozenset):
        for value in payload:
            _collect_project_artifact_references(value, managed_ids=managed_ids, staged_ids=staged_ids)


def rewrite_project_artifact_refs(payload: Any, replacements: Mapping[str, str]) -> Any:
    replacement_map = {
        str(source): str(target)
        for source, target in replacements.items()
        if str(source).strip() and str(target).strip()
    }
    if not replacement_map:
        return copy.deepcopy(payload)
    return _rewrite_project_artifact_refs(payload, replacements=replacement_map)


def _rewrite_project_artifact_refs(payload: Any, *, replacements: Mapping[str, str]) -> Any:
    if isinstance(payload, str):
        return replacements.get(payload, payload)
    if isinstance(payload, Mapping):
        return {
            copy.deepcopy(key): _rewrite_project_artifact_refs(value, replacements=replacements)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_rewrite_project_artifact_refs(value, replacements=replacements) for value in payload]
    if isinstance(payload, tuple):
        return tuple(_rewrite_project_artifact_refs(value, replacements=replacements) for value in payload)
    if isinstance(payload, set):
        return {_rewrite_project_artifact_refs(value, replacements=replacements) for value in payload}
    if isinstance(payload, frozenset):
        return frozenset(_rewrite_project_artifact_refs(value, replacements=replacements) for value in payload)
    return copy.deepcopy(payload)


class JsonProjectCodec:
    def __init__(self, registry: NodeRegistry | None = None) -> None:
        self._registry = registry

    @staticmethod
    def _copy_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(dict(mapping))

    @classmethod
    def _copy_node_mapping(cls, mapping: Mapping[str, Any]) -> dict[str, Any]:
        copied = cls._copy_mapping(mapping)
        for key in _COMMENT_BACKDROP_RUNTIME_MEMBERSHIP_KEYS:
            copied.pop(key, None)
        return copied

    def to_document(self, project: ProjectData) -> dict[str, Any]:
        return self._to_document(project, include_unresolved=False)

    def to_persistent_document(self, project: ProjectData) -> dict[str, Any]:
        return self._to_document(project, include_unresolved=True)

    def _to_document(self, project: ProjectData, *, include_unresolved: bool) -> dict[str, Any]:
        metadata = project.metadata if isinstance(project.metadata, Mapping) else {}
        ownership = resolve_workspace_ownership(
            project.workspaces,
            order_sources=(metadata.get("workspace_order"),),
            active_workspace_id=project.active_workspace_id,
        )
        metadata = JsonProjectMigration.normalize_metadata(metadata, ownership.workspace_order)
        metadata["artifact_store"] = normalize_artifact_store_metadata(metadata.get("artifact_store"))
        metadata.pop(_RUNTIME_PRESERVATION_KEY, None)

        workspaces: list[dict[str, Any]] = []
        runtime_preservation: dict[str, dict[str, Any]] = {}
        for workspace_id in ownership.workspace_order:
            workspace = project.workspaces[workspace_id]
            persistence_state = workspace.capture_persistence_state()
            workspace.ensure_default_view()
            active_view_id = workspace.active_view_id
            if active_view_id not in workspace.views:
                active_view_id = next(iter(workspace.views))
            workspaces.append(
                {
                    "workspace_id": workspace.workspace_id,
                    "name": workspace.name,
                    "dirty": workspace.dirty,
                    "active_view_id": active_view_id,
                    "views": [
                        {
                            "view_id": view.view_id,
                            "name": view.name,
                            "zoom": view.zoom,
                            "pan_x": view.pan_x,
                            "pan_y": view.pan_y,
                            "scope_path": list(normalize_scope_path(workspace, view.scope_path)),
                        }
                        for view in workspace.views.values()
                    ],
                    "nodes": self._workspace_node_docs(
                        workspace,
                        persistence_state=persistence_state,
                        include_unresolved=include_unresolved,
                    ),
                    "edges": self._workspace_edge_docs(
                        workspace,
                        persistence_state=persistence_state,
                        include_unresolved=include_unresolved,
                    ),
                }
            )
            if not include_unresolved:
                sidecar = self._workspace_runtime_preservation(persistence_state)
                if sidecar:
                    runtime_preservation[workspace.workspace_id] = sidecar
        if runtime_preservation:
            metadata[_RUNTIME_PRESERVATION_KEY] = runtime_preservation
        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": project.project_id,
            "name": project.name,
            "active_workspace_id": ownership.active_workspace_id,
            "workspace_order": ownership.workspace_order,
            "workspaces": workspaces,
            "metadata": metadata,
        }

    def from_document(self, payload: dict[str, Any]) -> ProjectData:
        project = ProjectData(
            project_id=payload.get("project_id", "proj_unknown"),
            name=payload.get("name", "untitled"),
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
            active_workspace_id=payload.get("active_workspace_id", ""),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata"), Mapping) else {},
        )
        for ws_doc in payload.get("workspaces", []):
            if not isinstance(ws_doc, Mapping):
                continue
            workspace_id = ws_doc.get("workspace_id")
            workspace_name = ws_doc.get("name")
            if not workspace_id or not workspace_name:
                continue
            workspace = WorkspaceData(
                workspace_id=str(workspace_id),
                name=str(workspace_name),
                active_view_id=ws_doc.get("active_view_id", ""),
                dirty=bool(ws_doc.get("dirty", False)),
            )
            for view_doc in ws_doc.get("views", []):
                if not isinstance(view_doc, Mapping):
                    continue
                view_id = view_doc.get("view_id")
                if not view_id:
                    continue
                view = ViewState(
                    view_id=str(view_id),
                    name=view_doc.get("name", "V"),
                    zoom=float(view_doc.get("zoom", 1.0)),
                    pan_x=float(view_doc.get("pan_x", 0.0)),
                    pan_y=float(view_doc.get("pan_y", 0.0)),
                    scope_path=[
                        str(item).strip()
                        for item in view_doc.get("scope_path", [])
                        if str(item).strip()
                    ],
                )
                workspace.views[view.view_id] = view
            workspace.ensure_default_view()
            if workspace.active_view_id not in workspace.views:
                workspace.active_view_id = next(iter(workspace.views))
            runtime_sidecar = self._workspace_runtime_preservation_payload(
                payload=payload,
                workspace_id=workspace.workspace_id,
            )
            persistence_state = WorkspacePersistenceState()
            for node_doc in ws_doc.get("nodes", []):
                if not isinstance(node_doc, Mapping):
                    continue
                node_id = str(node_doc.get("node_id", "")).strip()
                type_id = str(node_doc.get("type_id", "")).strip()
                if not node_id or not type_id:
                    continue
                sanitized_node_doc = self._copy_node_mapping(node_doc)
                if self._registry is not None and self._registry.spec_or_none(type_id) is None:
                    persistence_state.unresolved_node_docs[node_id] = sanitized_node_doc
                    continue
                node = node_instance_from_mapping(sanitized_node_doc)
                if node is None:
                    continue
                workspace.nodes[node.node_id] = node
            for node_doc in runtime_sidecar.get("nodes", []):
                if not isinstance(node_doc, Mapping):
                    continue
                node_id = str(node_doc.get("node_id", "")).strip()
                type_id = str(node_doc.get("type_id", "")).strip()
                sanitized_node_doc = self._copy_node_mapping(node_doc)
                if (
                    not node_id
                    or not type_id
                    or node_id in persistence_state.unresolved_node_docs
                    or node_id in workspace.nodes
                ):
                    continue
                persistence_state.unresolved_node_docs[node_id] = sanitized_node_doc
            valid_node_ids = set(workspace.nodes) | set(persistence_state.unresolved_node_docs)
            for edge_doc in ws_doc.get("edges", []):
                if not isinstance(edge_doc, Mapping):
                    continue
                edge_id = str(edge_doc.get("edge_id", "")).strip()
                source_node_id = str(edge_doc.get("source_node_id", "")).strip()
                target_node_id = str(edge_doc.get("target_node_id", "")).strip()
                if not edge_id or not source_node_id or not target_node_id:
                    continue
                if source_node_id not in valid_node_ids or target_node_id not in valid_node_ids:
                    continue
                if (
                    self._registry is not None
                    and (
                        source_node_id in persistence_state.unresolved_node_docs
                        or target_node_id in persistence_state.unresolved_node_docs
                    )
                ):
                    persistence_state.unresolved_edge_docs[edge_id] = self._copy_mapping(edge_doc)
                    continue
                edge = edge_instance_from_mapping(edge_doc)
                if edge is None:
                    continue
                workspace.edges[edge.edge_id] = edge
            for edge_doc in runtime_sidecar.get("edges", []):
                if not isinstance(edge_doc, Mapping):
                    continue
                edge_id = str(edge_doc.get("edge_id", "")).strip()
                if (
                    not edge_id
                    or edge_id in persistence_state.unresolved_edge_docs
                    or edge_id in workspace.edges
                ):
                    continue
                persistence_state.unresolved_edge_docs[edge_id] = self._copy_mapping(edge_doc)
            for node_id, override_doc in self._authored_node_override_payload(runtime_sidecar).items():
                if node_id not in workspace.nodes:
                    continue
                persistence_state.authored_node_overrides[node_id] = override_doc
            sanitize_workspace_parent_links(workspace, persistence_state)
            workspace.restore_persistence_state(persistence_state)
            for view in workspace.views.values():
                view.scope_path = list(normalize_scope_path(workspace, view.scope_path))
            project.workspaces[workspace.workspace_id] = workspace
        project.ensure_default_workspace()
        ownership = sync_project_workspace_ownership(
            project,
            order_sources=(payload.get("workspace_order"),),
        )
        project.metadata = JsonProjectMigration.normalize_metadata(project.metadata, ownership.workspace_order)
        project.metadata["artifact_store"] = normalize_artifact_store_metadata(project.metadata.get("artifact_store"))
        return project

    def _workspace_node_docs(
        self,
        workspace: WorkspaceData,
        *,
        persistence_state: WorkspacePersistenceState,
        include_unresolved: bool,
    ) -> list[dict[str, Any]]:
        node_docs_by_id = {
            node.node_id: self._merge_authored_node_override(
                node_instance_to_mapping(node),
                persistence_state.authored_node_overrides.get(node.node_id) if include_unresolved else None,
            )
            for node in sorted(workspace.nodes.values(), key=lambda item: item.node_id)
        }
        if include_unresolved:
            for node_id in sorted(persistence_state.unresolved_node_docs):
                if node_id in node_docs_by_id:
                    continue
                node_doc = persistence_state.unresolved_node_docs[node_id]
                if not isinstance(node_doc, Mapping):
                    continue
                node_docs_by_id[node_id] = self._copy_node_mapping(node_doc)
        return [node_docs_by_id[node_id] for node_id in sorted(node_docs_by_id)]

    def _workspace_edge_docs(
        self,
        workspace: WorkspaceData,
        *,
        persistence_state: WorkspacePersistenceState,
        include_unresolved: bool,
    ) -> list[dict[str, Any]]:
        edge_docs_by_id = {
            edge.edge_id: edge_instance_to_mapping(edge)
            for edge in sorted(workspace.edges.values(), key=lambda item: item.edge_id)
        }
        if include_unresolved:
            for edge_id in sorted(persistence_state.unresolved_edge_docs):
                if edge_id in edge_docs_by_id:
                    continue
                edge_doc = persistence_state.unresolved_edge_docs[edge_id]
                if not isinstance(edge_doc, Mapping):
                    continue
                edge_docs_by_id[edge_id] = self._copy_mapping(edge_doc)
        return [edge_docs_by_id[edge_id] for edge_id in sorted(edge_docs_by_id)]

    def _workspace_runtime_preservation(self, persistence_state: WorkspacePersistenceState) -> dict[str, Any]:
        sidecar: dict[str, Any] = {}
        unresolved_nodes = persistence_state.unresolved_node_docs
        unresolved_edges = persistence_state.unresolved_edge_docs
        authored_overrides = persistence_state.authored_node_overrides
        if unresolved_nodes:
            sidecar["nodes"] = [
                self._copy_node_mapping(unresolved_nodes[node_id])
                for node_id in sorted(unresolved_nodes)
            ]
        if unresolved_edges:
            sidecar["edges"] = [
                self._copy_mapping(unresolved_edges[edge_id])
                for edge_id in sorted(unresolved_edges)
            ]
        if authored_overrides:
            sidecar["node_overrides"] = {
                node_id: self._copy_mapping(override)
                for node_id, override in sorted(authored_overrides.items())
                if override
            }
        return sidecar

    @staticmethod
    def _workspace_runtime_preservation_payload(
        *,
        payload: Mapping[str, Any],
        workspace_id: str,
    ) -> dict[str, Any]:
        metadata = payload.get("metadata")
        if not isinstance(metadata, Mapping):
            return {}
        runtime_preservation = metadata.get(_RUNTIME_PRESERVATION_KEY)
        if not isinstance(runtime_preservation, Mapping):
            return {}
        workspace_payload = runtime_preservation.get(workspace_id)
        if not isinstance(workspace_payload, Mapping):
            return {}
        return dict(workspace_payload)

    @staticmethod
    def _authored_node_override_payload(sidecar: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        raw_overrides = sidecar.get("node_overrides")
        if not isinstance(raw_overrides, Mapping):
            return {}
        return {
            str(node_id): copy.deepcopy(dict(override))
            for node_id, override in raw_overrides.items()
            if str(node_id).strip() and isinstance(override, Mapping)
        }

    @staticmethod
    def _merge_authored_node_override(
        node_doc: dict[str, Any],
        override_doc: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        merged = copy.deepcopy(node_doc)
        if isinstance(override_doc, Mapping):
            merged.update(copy.deepcopy(dict(override_doc)))
        for key in _COMMENT_BACKDROP_RUNTIME_MEMBERSHIP_KEYS:
            merged.pop(key, None)
        return merged
