from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.graph.hierarchy import normalize_scope_path
from ea_node_editor.graph.model import (
    EdgeInstance,
    NodeInstance,
    ProjectData,
    ViewState,
    WorkspaceData,
)
from ea_node_editor.persistence.migration import JsonProjectMigration
from ea_node_editor.settings import SCHEMA_VERSION


class JsonProjectCodec:
    def to_document(self, project: ProjectData) -> dict[str, Any]:
        workspace_order: list[str] = []
        for workspace_id in JsonProjectMigration.as_list(project.metadata.get("workspace_order")):
            normalized_id = self._coerce_str(workspace_id)
            if normalized_id and normalized_id in project.workspaces and normalized_id not in workspace_order:
                workspace_order.append(normalized_id)
        for workspace_id in sorted(project.workspaces):
            if workspace_id not in workspace_order:
                workspace_order.append(workspace_id)

        active_workspace_id = project.active_workspace_id
        if active_workspace_id not in project.workspaces:
            active_workspace_id = workspace_order[0] if workspace_order else ""

        metadata = JsonProjectMigration.normalize_metadata(project.metadata, workspace_order)

        workspaces: list[dict[str, Any]] = []
        for workspace_id in workspace_order:
            workspace = project.workspaces[workspace_id]
            workspace.ensure_default_view()
            active_view_id = workspace.active_view_id
            if active_view_id not in workspace.views:
                active_view_id = sorted(workspace.views)[0]
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
                        for view in sorted(
                            workspace.views.values(), key=lambda item: item.view_id
                        )
                    ],
                    "nodes": [
                        {
                            "node_id": node.node_id,
                            "type_id": node.type_id,
                            "title": node.title,
                            "x": node.x,
                            "y": node.y,
                            "collapsed": node.collapsed,
                            "properties": node.properties,
                            "exposed_ports": node.exposed_ports,
                            "parent_node_id": node.parent_node_id,
                        }
                        for node in sorted(
                            workspace.nodes.values(), key=lambda item: item.node_id
                        )
                    ],
                    "edges": [
                        {
                            "edge_id": edge.edge_id,
                            "source_node_id": edge.source_node_id,
                            "source_port_key": edge.source_port_key,
                            "target_node_id": edge.target_node_id,
                            "target_port_key": edge.target_port_key,
                        }
                        for edge in sorted(
                            workspace.edges.values(), key=lambda item: item.edge_id
                        )
                    ],
                }
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": project.project_id,
            "name": project.name,
            "active_workspace_id": active_workspace_id,
            "workspace_order": workspace_order,
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
            for node_doc in ws_doc.get("nodes", []):
                if not isinstance(node_doc, Mapping):
                    continue
                node_id = node_doc.get("node_id")
                type_id = node_doc.get("type_id")
                if not node_id or not type_id:
                    continue
                node = NodeInstance(
                    node_id=str(node_id),
                    type_id=str(type_id),
                    title=node_doc.get("title", str(type_id)),
                    x=float(node_doc.get("x", 0.0)),
                    y=float(node_doc.get("y", 0.0)),
                    collapsed=bool(node_doc.get("collapsed", False)),
                    properties=dict(node_doc.get("properties", {})),
                    exposed_ports=dict(node_doc.get("exposed_ports", {})),
                    parent_node_id=node_doc.get("parent_node_id"),
                )
                workspace.nodes[node.node_id] = node
            for edge_doc in ws_doc.get("edges", []):
                if not isinstance(edge_doc, Mapping):
                    continue
                edge_id = edge_doc.get("edge_id")
                source_node_id = edge_doc.get("source_node_id")
                source_port_key = edge_doc.get("source_port_key")
                target_node_id = edge_doc.get("target_node_id")
                target_port_key = edge_doc.get("target_port_key")
                if (
                    not edge_id
                    or not source_node_id
                    or not source_port_key
                    or not target_node_id
                    or not target_port_key
                ):
                    continue
                edge = EdgeInstance(
                    edge_id=str(edge_id),
                    source_node_id=str(source_node_id),
                    source_port_key=str(source_port_key),
                    target_node_id=str(target_node_id),
                    target_port_key=str(target_port_key),
                )
                workspace.edges[edge.edge_id] = edge
            for view in workspace.views.values():
                view.scope_path = list(normalize_scope_path(workspace, view.scope_path))
            project.workspaces[workspace.workspace_id] = workspace
        project.ensure_default_workspace()
        workspace_order = payload.get("workspace_order")
        if not isinstance(workspace_order, list):
            workspace_order = project.metadata.get("workspace_order", [])
        normalized_order: list[str] = []
        for workspace_id in workspace_order:
            if workspace_id in project.workspaces and workspace_id not in normalized_order:
                normalized_order.append(workspace_id)
        for workspace_id in project.workspaces:
            if workspace_id not in normalized_order:
                normalized_order.append(workspace_id)
        project.metadata = JsonProjectMigration.normalize_metadata(project.metadata, normalized_order)
        if project.active_workspace_id not in project.workspaces and normalized_order:
            project.active_workspace_id = normalized_order[0]
        return project

    @staticmethod
    def _coerce_str(value: Any, default: str = "") -> str:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else default
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default
