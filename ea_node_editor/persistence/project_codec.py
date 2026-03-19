from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from ea_node_editor.graph.hierarchy import normalize_scope_path
from ea_node_editor.graph.model import (
    ProjectData,
    ViewState,
    WorkspaceData,
    edge_instance_from_mapping,
    edge_instance_to_mapping,
    node_instance_from_mapping,
    node_instance_to_mapping,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.migration import JsonProjectMigration
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.workspace.ownership import resolve_workspace_ownership, sync_project_workspace_ownership

_RUNTIME_PRESERVATION_KEY = "_runtime_unresolved_workspaces"


class JsonProjectCodec:
    def __init__(self, registry: NodeRegistry | None = None) -> None:
        self._registry = registry

    @staticmethod
    def _copy_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(dict(mapping))

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
        metadata.pop(_RUNTIME_PRESERVATION_KEY, None)

        workspaces: list[dict[str, Any]] = []
        runtime_preservation: dict[str, dict[str, Any]] = {}
        for workspace_id in ownership.workspace_order:
            workspace = project.workspaces[workspace_id]
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
                    "nodes": self._workspace_node_docs(workspace, include_unresolved=include_unresolved),
                    "edges": self._workspace_edge_docs(workspace, include_unresolved=include_unresolved),
                }
            )
            if not include_unresolved:
                sidecar = self._workspace_runtime_preservation(workspace)
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
            for node_doc in ws_doc.get("nodes", []):
                if not isinstance(node_doc, Mapping):
                    continue
                node_id = str(node_doc.get("node_id", "")).strip()
                type_id = str(node_doc.get("type_id", "")).strip()
                if not node_id or not type_id:
                    continue
                if self._registry is not None and self._registry.spec_or_none(type_id) is None:
                    workspace.unresolved_node_docs[node_id] = self._copy_mapping(node_doc)
                    continue
                node = node_instance_from_mapping(node_doc)
                if node is None:
                    continue
                workspace.nodes[node.node_id] = node
            for node_doc in runtime_sidecar.get("nodes", []):
                if not isinstance(node_doc, Mapping):
                    continue
                node_id = str(node_doc.get("node_id", "")).strip()
                type_id = str(node_doc.get("type_id", "")).strip()
                if not node_id or not type_id or node_id in workspace.unresolved_node_docs or node_id in workspace.nodes:
                    continue
                workspace.unresolved_node_docs[node_id] = self._copy_mapping(node_doc)
            valid_node_ids = set(workspace.nodes) | set(workspace.unresolved_node_docs)
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
                        source_node_id in workspace.unresolved_node_docs
                        or target_node_id in workspace.unresolved_node_docs
                    )
                ):
                    workspace.unresolved_edge_docs[edge_id] = self._copy_mapping(edge_doc)
                    continue
                edge = edge_instance_from_mapping(edge_doc)
                if edge is None:
                    continue
                workspace.edges[edge.edge_id] = edge
            for edge_doc in runtime_sidecar.get("edges", []):
                if not isinstance(edge_doc, Mapping):
                    continue
                edge_id = str(edge_doc.get("edge_id", "")).strip()
                if not edge_id or edge_id in workspace.unresolved_edge_docs or edge_id in workspace.edges:
                    continue
                workspace.unresolved_edge_docs[edge_id] = self._copy_mapping(edge_doc)
            for node_id, override_doc in self._authored_node_override_payload(runtime_sidecar).items():
                if node_id not in workspace.nodes:
                    continue
                workspace.authored_node_overrides[node_id] = override_doc
            self._sanitize_live_parent_links(workspace)
            for view in workspace.views.values():
                view.scope_path = list(normalize_scope_path(workspace, view.scope_path))
            project.workspaces[workspace.workspace_id] = workspace
        project.ensure_default_workspace()
        ownership = sync_project_workspace_ownership(
            project,
            order_sources=(payload.get("workspace_order"),),
        )
        project.metadata = JsonProjectMigration.normalize_metadata(project.metadata, ownership.workspace_order)
        return project

    def _workspace_node_docs(self, workspace: WorkspaceData, *, include_unresolved: bool) -> list[dict[str, Any]]:
        node_docs_by_id = {
            node.node_id: self._merge_authored_node_override(
                node_instance_to_mapping(node),
                workspace.authored_node_overrides.get(node.node_id) if include_unresolved else None,
            )
            for node in sorted(workspace.nodes.values(), key=lambda item: item.node_id)
        }
        if include_unresolved:
            for node_id in sorted(workspace.unresolved_node_docs):
                if node_id in node_docs_by_id:
                    continue
                node_doc = workspace.unresolved_node_docs[node_id]
                if not isinstance(node_doc, Mapping):
                    continue
                node_docs_by_id[node_id] = self._copy_mapping(node_doc)
        return [node_docs_by_id[node_id] for node_id in sorted(node_docs_by_id)]

    def _workspace_edge_docs(self, workspace: WorkspaceData, *, include_unresolved: bool) -> list[dict[str, Any]]:
        edge_docs_by_id = {
            edge.edge_id: edge_instance_to_mapping(edge)
            for edge in sorted(workspace.edges.values(), key=lambda item: item.edge_id)
        }
        if include_unresolved:
            for edge_id in sorted(workspace.unresolved_edge_docs):
                if edge_id in edge_docs_by_id:
                    continue
                edge_doc = workspace.unresolved_edge_docs[edge_id]
                if not isinstance(edge_doc, Mapping):
                    continue
                edge_docs_by_id[edge_id] = self._copy_mapping(edge_doc)
        return [edge_docs_by_id[edge_id] for edge_id in sorted(edge_docs_by_id)]

    def _workspace_runtime_preservation(self, workspace: WorkspaceData) -> dict[str, Any]:
        sidecar: dict[str, Any] = {}
        if workspace.unresolved_node_docs:
            sidecar["nodes"] = [
                self._copy_mapping(workspace.unresolved_node_docs[node_id])
                for node_id in sorted(workspace.unresolved_node_docs)
            ]
        if workspace.unresolved_edge_docs:
            sidecar["edges"] = [
                self._copy_mapping(workspace.unresolved_edge_docs[edge_id])
                for edge_id in sorted(workspace.unresolved_edge_docs)
            ]
        if workspace.authored_node_overrides:
            sidecar["node_overrides"] = {
                node_id: self._copy_mapping(override)
                for node_id, override in sorted(workspace.authored_node_overrides.items())
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
        return merged

    @staticmethod
    def _sanitize_live_parent_links(workspace: WorkspaceData) -> None:
        for node in workspace.nodes.values():
            parent_id = str(node.parent_node_id or "").strip() or None
            override_parent_id = (
                str(workspace.authored_node_overrides.get(node.node_id, {}).get("parent_node_id", "")).strip()
                or None
            )
            if parent_id is None:
                if override_parent_id in workspace.unresolved_node_docs:
                    continue
                workspace.authored_node_overrides.pop(node.node_id, None)
                continue
            if parent_id == node.node_id:
                node.parent_node_id = None
                workspace.authored_node_overrides.pop(node.node_id, None)
                continue
            if parent_id in workspace.nodes:
                workspace.authored_node_overrides.pop(node.node_id, None)
                continue
            if parent_id in workspace.unresolved_node_docs:
                workspace.authored_node_overrides[node.node_id] = {"parent_node_id": parent_id}
            else:
                workspace.authored_node_overrides.pop(node.node_id, None)
            node.parent_node_id = None
