from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any

from ea_node_editor.settings import SCHEMA_VERSION


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass(slots=True)
class NodeInstance:
    node_id: str
    type_id: str
    title: str
    x: float
    y: float
    collapsed: bool = False
    properties: dict[str, Any] = field(default_factory=dict)
    exposed_ports: dict[str, bool] = field(default_factory=dict)
    visual_style: dict[str, Any] = field(default_factory=dict)
    parent_node_id: str | None = None
    custom_width: float | None = None
    custom_height: float | None = None

    def clone(self) -> "NodeInstance":
        return copy.deepcopy(self)


@dataclass(slots=True)
class EdgeInstance:
    edge_id: str
    source_node_id: str
    source_port_key: str
    target_node_id: str
    target_port_key: str
    label: str = ""
    visual_style: dict[str, Any] = field(default_factory=dict)

    def clone(self) -> "EdgeInstance":
        return copy.deepcopy(self)


@dataclass(slots=True)
class ViewState:
    view_id: str
    name: str
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    scope_path: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkspaceData:
    workspace_id: str
    name: str
    nodes: dict[str, NodeInstance] = field(default_factory=dict)
    edges: dict[str, EdgeInstance] = field(default_factory=dict)
    views: dict[str, ViewState] = field(default_factory=dict)
    active_view_id: str = ""
    dirty: bool = False

    def ensure_default_view(self) -> None:
        if not self.views:
            view = ViewState(view_id=new_id("view"), name="V1")
            self.views[view.view_id] = view
            self.active_view_id = view.view_id
        elif not self.active_view_id:
            self.active_view_id = next(iter(self.views))

    def clone(self, new_workspace_id: str, name: str) -> "WorkspaceData":
        clone_nodes = {node_id: node.clone() for node_id, node in self.nodes.items()}
        clone_edges = {edge_id: edge.clone() for edge_id, edge in self.edges.items()}
        clone_views = copy.deepcopy(self.views)
        duplicate = WorkspaceData(
            workspace_id=new_workspace_id,
            name=name,
            nodes=clone_nodes,
            edges=clone_edges,
            views=clone_views,
            active_view_id=self.active_view_id,
            dirty=True,
        )
        duplicate.ensure_default_view()
        return duplicate


@dataclass(slots=True)
class ProjectData:
    project_id: str
    name: str
    schema_version: int = SCHEMA_VERSION
    active_workspace_id: str = ""
    workspaces: dict[str, WorkspaceData] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def ensure_default_workspace(self) -> WorkspaceData:
        if not self.workspaces:
            workspace = WorkspaceData(workspace_id=new_id("ws"), name="Workspace 1")
            workspace.ensure_default_view()
            self.workspaces[workspace.workspace_id] = workspace
            self.active_workspace_id = workspace.workspace_id
        elif not self.active_workspace_id:
            self.active_workspace_id = next(iter(self.workspaces))
        return self.workspaces[self.active_workspace_id]


class GraphModel:
    def __init__(self, project: ProjectData | None = None) -> None:
        self.project = project or ProjectData(project_id=new_id("proj"), name="untitled")
        self.project.ensure_default_workspace()

    @property
    def active_workspace(self) -> WorkspaceData:
        self.project.ensure_default_workspace()
        return self.project.workspaces[self.project.active_workspace_id]

    def create_workspace(self, name: str | None = None) -> WorkspaceData:
        index = len(self.project.workspaces) + 1
        workspace = WorkspaceData(workspace_id=new_id("ws"), name=name or f"Workspace {index}")
        workspace.ensure_default_view()
        self.project.workspaces[workspace.workspace_id] = workspace
        self.project.active_workspace_id = workspace.workspace_id
        return workspace

    def duplicate_workspace(self, workspace_id: str) -> WorkspaceData:
        source = self.project.workspaces[workspace_id]
        duplicated = source.clone(new_workspace_id=new_id("ws"), name=f"{source.name} Copy")
        self.project.workspaces[duplicated.workspace_id] = duplicated
        self.project.active_workspace_id = duplicated.workspace_id
        return duplicated

    def close_workspace(self, workspace_id: str) -> None:
        if workspace_id not in self.project.workspaces:
            return
        if len(self.project.workspaces) == 1:
            raise ValueError("Cannot close the last workspace")
        del self.project.workspaces[workspace_id]
        if self.project.active_workspace_id == workspace_id:
            self.project.active_workspace_id = next(iter(self.project.workspaces))

    def rename_workspace(self, workspace_id: str, new_name: str) -> None:
        self.project.workspaces[workspace_id].name = new_name

    def set_active_workspace(self, workspace_id: str) -> None:
        if workspace_id not in self.project.workspaces:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        self.project.active_workspace_id = workspace_id

    def create_view(
        self,
        workspace_id: str,
        name: str | None = None,
        *,
        source_view_id: str | None = None,
    ) -> ViewState:
        workspace = self.project.workspaces[workspace_id]
        source_view = workspace.views.get(source_view_id) if source_view_id else None
        view = ViewState(
            view_id=new_id("view"),
            name=name or f"V{len(workspace.views) + 1}",
            zoom=source_view.zoom if source_view is not None else 1.0,
            pan_x=source_view.pan_x if source_view is not None else 0.0,
            pan_y=source_view.pan_y if source_view is not None else 0.0,
            scope_path=list(source_view.scope_path) if source_view is not None else [],
        )
        workspace.views[view.view_id] = view
        workspace.active_view_id = view.view_id
        return view

    def set_active_view(self, workspace_id: str, view_id: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        if view_id not in workspace.views:
            raise KeyError(f"Unknown view: {view_id}")
        workspace.active_view_id = view_id

    def close_view(self, workspace_id: str, view_id: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.ensure_default_view()
        if view_id not in workspace.views:
            return
        if len(workspace.views) == 1:
            raise ValueError("Cannot close the last view")
        ordered_view_ids = list(workspace.views)
        close_index = ordered_view_ids.index(view_id)
        was_active = workspace.active_view_id == view_id
        del workspace.views[view_id]
        if not was_active:
            return
        remaining_view_ids = list(workspace.views)
        next_index = min(max(close_index, 0), len(remaining_view_ids) - 1)
        workspace.active_view_id = remaining_view_ids[next_index]

    def rename_view(self, workspace_id: str, view_id: str, new_name: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        if view_id not in workspace.views:
            raise KeyError(f"Unknown view: {view_id}")
        workspace.views[view_id].name = new_name

    def move_view(self, workspace_id: str, from_index: int, to_index: int) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.ensure_default_view()
        if len(workspace.views) < 2:
            return
        if from_index < 0 or from_index >= len(workspace.views):
            return
        to_index = max(0, min(to_index, len(workspace.views) - 1))
        if from_index == to_index:
            return
        ordered_views = list(workspace.views.items())
        moved_view_id, moved_view = ordered_views.pop(from_index)
        ordered_views.insert(to_index, (moved_view_id, moved_view))
        workspace.views = dict(ordered_views)

    def add_node(
        self,
        workspace_id: str,
        type_id: str,
        title: str,
        x: float,
        y: float,
        properties: dict[str, Any] | None = None,
        exposed_ports: dict[str, bool] | None = None,
        visual_style: dict[str, Any] | None = None,
    ) -> NodeInstance:
        workspace = self.project.workspaces[workspace_id]
        node = NodeInstance(
            node_id=new_id("node"),
            type_id=type_id,
            title=title,
            x=x,
            y=y,
            properties=properties or {},
            exposed_ports=exposed_ports or {},
            visual_style=copy.deepcopy(visual_style or {}),
        )
        workspace.nodes[node.node_id] = node
        workspace.dirty = True
        return node

    def remove_node(self, workspace_id: str, node_id: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        if node_id not in workspace.nodes:
            return
        del workspace.nodes[node_id]
        for edge_id in list(workspace.edges):
            edge = workspace.edges[edge_id]
            if edge.source_node_id == node_id or edge.target_node_id == node_id:
                del workspace.edges[edge_id]
        workspace.dirty = True

    def set_node_position(self, workspace_id: str, node_id: str, x: float, y: float) -> None:
        workspace = self.project.workspaces[workspace_id]
        node = workspace.nodes[node_id]
        node.x = x
        node.y = y
        workspace.dirty = True

    def set_node_geometry(
        self,
        workspace_id: str,
        node_id: str,
        x: float,
        y: float,
        width: float | None,
        height: float | None,
    ) -> None:
        workspace = self.project.workspaces[workspace_id]
        node = workspace.nodes[node_id]
        node.x = x
        node.y = y
        node.custom_width = width
        node.custom_height = height
        workspace.dirty = True

    def set_node_size(self, workspace_id: str, node_id: str, width: float | None, height: float | None) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].custom_width = width
        workspace.nodes[node_id].custom_height = height
        workspace.dirty = True

    def set_node_collapsed(self, workspace_id: str, node_id: str, collapsed: bool) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].collapsed = collapsed
        workspace.dirty = True

    def set_node_property(self, workspace_id: str, node_id: str, key: str, value: Any) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].properties[key] = value
        workspace.dirty = True

    def set_node_title(self, workspace_id: str, node_id: str, title: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].title = title
        workspace.dirty = True

    def set_node_visual_style(self, workspace_id: str, node_id: str, visual_style: dict[str, Any] | None) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].visual_style = copy.deepcopy(visual_style or {})
        workspace.dirty = True

    def set_exposed_port(self, workspace_id: str, node_id: str, key: str, exposed: bool) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].exposed_ports[key] = exposed
        workspace.dirty = True

    def add_edge(
        self,
        workspace_id: str,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
        label: str = "",
        visual_style: dict[str, Any] | None = None,
    ) -> EdgeInstance:
        workspace = self.project.workspaces[workspace_id]
        if source_node_id not in workspace.nodes:
            raise KeyError(f"Unknown source node: {source_node_id}")
        if target_node_id not in workspace.nodes:
            raise KeyError(f"Unknown target node: {target_node_id}")
        for existing in workspace.edges.values():
            if (
                existing.source_node_id == source_node_id
                and existing.source_port_key == source_port_key
                and existing.target_node_id == target_node_id
                and existing.target_port_key == target_port_key
            ):
                return existing
        edge = EdgeInstance(
            edge_id=new_id("edge"),
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
            label=str(label),
            visual_style=copy.deepcopy(visual_style or {}),
        )
        workspace.edges[edge.edge_id] = edge
        workspace.dirty = True
        return edge

    def set_edge_label(self, workspace_id: str, edge_id: str, label: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.edges[edge_id].label = str(label)
        workspace.dirty = True

    def set_edge_visual_style(self, workspace_id: str, edge_id: str, visual_style: dict[str, Any] | None) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.edges[edge_id].visual_style = copy.deepcopy(visual_style or {})
        workspace.dirty = True

    def remove_edge(self, workspace_id: str, edge_id: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        if edge_id in workspace.edges:
            del workspace.edges[edge_id]
            workspace.dirty = True
