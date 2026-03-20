from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ea_node_editor.persistence.overlay import (
    WorkspacePersistenceState,
    set_workspace_authored_node_overrides,
    set_workspace_unresolved_edge_docs,
    set_workspace_unresolved_node_docs,
)
from ea_node_editor.settings import SCHEMA_VERSION

if TYPE_CHECKING:
    from ea_node_editor.graph.mutation_service import WorkspaceMutationService
    from ea_node_editor.nodes.registry import NodeRegistry


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _coerce_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else default
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def node_instance_from_mapping(payload: Mapping[str, Any]) -> NodeInstance | None:
    node_id = _coerce_str(payload.get("node_id"))
    type_id = _coerce_str(payload.get("type_id"))
    if not node_id or not type_id:
        return None
    parent_node_id = _coerce_str(payload.get("parent_node_id")) or None
    return NodeInstance(
        node_id=node_id,
        type_id=type_id,
        title=_coerce_str(payload.get("title"), type_id),
        x=_coerce_float(payload.get("x"), 0.0),
        y=_coerce_float(payload.get("y"), 0.0),
        collapsed=bool(payload.get("collapsed", False)),
        properties=_as_mapping(payload.get("properties")),
        exposed_ports={key: bool(value) for key, value in _as_mapping(payload.get("exposed_ports")).items()},
        visual_style=_as_mapping(payload.get("visual_style")),
        parent_node_id=parent_node_id,
        custom_width=_coerce_float(payload.get("custom_width")) if payload.get("custom_width") is not None else None,
        custom_height=_coerce_float(payload.get("custom_height")) if payload.get("custom_height") is not None else None,
    )


def node_instance_to_mapping(node: "NodeInstance") -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "type_id": node.type_id,
        "title": node.title,
        "x": node.x,
        "y": node.y,
        "collapsed": node.collapsed,
        "properties": copy.deepcopy(node.properties),
        "exposed_ports": copy.deepcopy(node.exposed_ports),
        "visual_style": copy.deepcopy(node.visual_style),
        "parent_node_id": node.parent_node_id,
        "custom_width": node.custom_width,
        "custom_height": node.custom_height,
    }


def edge_instance_from_mapping(payload: Mapping[str, Any]) -> EdgeInstance | None:
    edge_id = _coerce_str(payload.get("edge_id"))
    source_node_id = _coerce_str(payload.get("source_node_id"))
    source_port_key = _coerce_str(payload.get("source_port_key"))
    target_node_id = _coerce_str(payload.get("target_node_id"))
    target_port_key = _coerce_str(payload.get("target_port_key"))
    if not edge_id or not source_node_id or not source_port_key or not target_node_id or not target_port_key:
        return None
    return EdgeInstance(
        edge_id=edge_id,
        source_node_id=source_node_id,
        source_port_key=source_port_key,
        target_node_id=target_node_id,
        target_port_key=target_port_key,
        label=_coerce_str(payload.get("label")),
        visual_style=_as_mapping(payload.get("visual_style")),
    )


def edge_instance_to_mapping(edge: "EdgeInstance") -> dict[str, Any]:
    return {
        "edge_id": edge.edge_id,
        "source_node_id": edge.source_node_id,
        "source_port_key": edge.source_port_key,
        "target_node_id": edge.target_node_id,
        "target_port_key": edge.target_port_key,
        "label": edge.label,
        "visual_style": copy.deepcopy(edge.visual_style),
    }


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
class WorkspaceSnapshot:
    name: str
    nodes: dict[str, NodeInstance]
    edges: dict[str, EdgeInstance]
    views: dict[str, ViewState]
    active_view_id: str
    dirty: bool
    persistence_state: WorkspacePersistenceState = field(default_factory=WorkspacePersistenceState)

    @property
    def unresolved_node_docs(self) -> dict[str, dict[str, Any]]:
        return self.persistence_state.unresolved_node_docs

    @property
    def unresolved_edge_docs(self) -> dict[str, dict[str, Any]]:
        return self.persistence_state.unresolved_edge_docs

    @property
    def authored_node_overrides(self) -> dict[str, dict[str, Any]]:
        return self.persistence_state.authored_node_overrides

    @classmethod
    def capture(cls, workspace: WorkspaceData) -> "WorkspaceSnapshot":
        return cls(
            name=str(workspace.name),
            nodes={node_id: node.clone() for node_id, node in workspace.nodes.items()},
            edges={edge_id: edge.clone() for edge_id, edge in workspace.edges.items()},
            views=copy.deepcopy(workspace.views),
            active_view_id=str(workspace.active_view_id),
            dirty=bool(workspace.dirty),
            persistence_state=workspace.capture_persistence_state(),
        )

    def restore(self, workspace: WorkspaceData) -> None:
        workspace.name = str(self.name)
        workspace.nodes = {node_id: node.clone() for node_id, node in self.nodes.items()}
        workspace.edges = {edge_id: edge.clone() for edge_id, edge in self.edges.items()}
        workspace.views = copy.deepcopy(self.views)
        workspace.active_view_id = str(self.active_view_id)
        workspace.dirty = bool(self.dirty)
        workspace.restore_persistence_state(self.persistence_state)
        workspace.ensure_default_view()
        if workspace.active_view_id not in workspace.views:
            workspace.active_view_id = next(iter(workspace.views))


@dataclass(slots=True)
class WorkspaceData:
    workspace_id: str
    name: str
    nodes: dict[str, NodeInstance] = field(default_factory=dict)
    edges: dict[str, EdgeInstance] = field(default_factory=dict)
    views: dict[str, ViewState] = field(default_factory=dict)
    active_view_id: str = ""
    dirty: bool = False
    persistence_state: WorkspacePersistenceState = field(
        default_factory=WorkspacePersistenceState,
        repr=False,
        compare=False,
    )

    def ensure_default_view(self) -> None:
        if not self.views:
            view = ViewState(view_id=new_id("view"), name="V1")
            self.views[view.view_id] = view
            self.active_view_id = view.view_id
        elif not self.active_view_id:
            self.active_view_id = next(iter(self.views))

    @property
    def unresolved_node_docs(self) -> dict[str, dict[str, Any]]:
        return self.persistence_state.unresolved_node_docs

    @unresolved_node_docs.setter
    def unresolved_node_docs(self, value: Mapping[str, Any] | None) -> None:
        set_workspace_unresolved_node_docs(self, value)

    @property
    def unresolved_edge_docs(self) -> dict[str, dict[str, Any]]:
        return self.persistence_state.unresolved_edge_docs

    @unresolved_edge_docs.setter
    def unresolved_edge_docs(self, value: Mapping[str, Any] | None) -> None:
        set_workspace_unresolved_edge_docs(self, value)

    @property
    def authored_node_overrides(self) -> dict[str, dict[str, Any]]:
        return self.persistence_state.authored_node_overrides

    @authored_node_overrides.setter
    def authored_node_overrides(self, value: Mapping[str, Any] | None) -> None:
        set_workspace_authored_node_overrides(self, value)

    def capture_persistence_state(self) -> WorkspacePersistenceState:
        return self.persistence_state.clone()

    def restore_persistence_state(self, state: WorkspacePersistenceState) -> None:
        self.persistence_state = state.clone()

    def capture_snapshot(self) -> WorkspaceSnapshot:
        return WorkspaceSnapshot.capture(self)

    def restore_snapshot(self, snapshot: WorkspaceSnapshot) -> None:
        snapshot.restore(self)

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
        duplicate.restore_persistence_state(self.capture_persistence_state())
        duplicate.ensure_default_view()
        return duplicate


def sanitize_workspace_parent_links(
    workspace: WorkspaceData,
    persistence_state: WorkspacePersistenceState | None = None,
) -> WorkspacePersistenceState:
    state = persistence_state or workspace.capture_persistence_state()
    unresolved_nodes = state.unresolved_node_docs
    authored_overrides = state.authored_node_overrides
    for node in workspace.nodes.values():
        parent_id = str(node.parent_node_id or "").strip() or None
        override_parent_id = (
            str(authored_overrides.get(node.node_id, {}).get("parent_node_id", "")).strip()
            or None
        )
        if parent_id is None:
            if override_parent_id in unresolved_nodes:
                continue
            authored_overrides.pop(node.node_id, None)
            continue
        if parent_id == node.node_id:
            node.parent_node_id = None
            authored_overrides.pop(node.node_id, None)
            continue
        if parent_id in workspace.nodes:
            authored_overrides.pop(node.node_id, None)
            continue
        if parent_id in unresolved_nodes:
            authored_overrides[node.node_id] = {"parent_node_id": parent_id}
        else:
            authored_overrides.pop(node.node_id, None)
        node.parent_node_id = None
    if persistence_state is None:
        workspace.restore_persistence_state(state)
    return state


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

    def mutation_service(
        self,
        workspace_id: str,
        registry: "NodeRegistry | None" = None,
    ) -> "WorkspaceMutationService":
        if workspace_id not in self.project.workspaces:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        from ea_node_editor.graph.mutation_service import WorkspaceMutationService

        return WorkspaceMutationService(
            model=self,
            workspace_id=workspace_id,
            registry=registry,
        )

    def validated_mutations(self, workspace_id: str, registry: "NodeRegistry") -> "WorkspaceMutationService":
        return self.mutation_service(workspace_id, registry=registry)

    def _create_workspace_record(self, name: str | None = None) -> WorkspaceData:
        index = len(self.project.workspaces) + 1
        workspace = WorkspaceData(workspace_id=new_id("ws"), name=name or f"Workspace {index}")
        workspace.ensure_default_view()
        self.project.workspaces[workspace.workspace_id] = workspace
        return workspace

    def create_workspace(self, name: str | None = None) -> WorkspaceData:
        workspace = self._create_workspace_record(name=name)
        self._set_active_workspace_id(workspace.workspace_id)
        return workspace

    def _duplicate_workspace_record(self, workspace_id: str) -> WorkspaceData:
        source = self.project.workspaces[workspace_id]
        duplicated = source.clone(new_workspace_id=new_id("ws"), name=f"{source.name} Copy")
        self.project.workspaces[duplicated.workspace_id] = duplicated
        return duplicated

    def duplicate_workspace(self, workspace_id: str) -> WorkspaceData:
        duplicated = self._duplicate_workspace_record(workspace_id)
        self._set_active_workspace_id(duplicated.workspace_id)
        return duplicated

    def _close_workspace_record(self, workspace_id: str) -> None:
        if workspace_id not in self.project.workspaces:
            return
        if len(self.project.workspaces) == 1:
            raise ValueError("Cannot close the last workspace")
        del self.project.workspaces[workspace_id]

    def close_workspace(self, workspace_id: str) -> None:
        was_active = self.project.active_workspace_id == workspace_id
        self._close_workspace_record(workspace_id)
        if was_active and self.project.workspaces:
            self._set_active_workspace_id(next(iter(self.project.workspaces)))

    def _rename_workspace_record(self, workspace_id: str, new_name: str) -> None:
        self.project.workspaces[workspace_id].name = new_name

    def rename_workspace(self, workspace_id: str, new_name: str) -> None:
        self._rename_workspace_record(workspace_id, new_name)

    def _set_active_workspace_id(self, workspace_id: str) -> None:
        if workspace_id not in self.project.workspaces:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        self.project.active_workspace_id = workspace_id

    def set_active_workspace(self, workspace_id: str) -> None:
        self._set_active_workspace_id(workspace_id)

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
        if node_id in workspace.nodes:
            del workspace.nodes[node_id]
        state = workspace.capture_persistence_state()
        state.remove_node_references(node_id)
        workspace.restore_persistence_state(state)
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
