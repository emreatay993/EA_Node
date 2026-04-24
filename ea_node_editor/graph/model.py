from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field, fields as dataclass_fields
from typing import TYPE_CHECKING, Any

from ea_node_editor.graph.port_locking import normalize_locked_ports_mapping
from ea_node_editor.settings import SCHEMA_VERSION

if TYPE_CHECKING:
    from ea_node_editor.graph.boundary_adapters import GraphBoundaryAdapters
    from ea_node_editor.graph.mutation_service import WorkspaceMutationService, WorkspaceMutationServiceFactory
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


def _try_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_mapping(value: Any, *, strict: bool = False) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None if strict else {}
    return {str(key): item for key, item in value.items()}


def node_instance_from_mapping(
    payload: Mapping[str, Any],
    *,
    node_id_key: str = "node_id",
    strict_payload: bool = False,
) -> NodeInstance | None:
    node_id = _coerce_str(payload.get(node_id_key))
    type_id = _coerce_str(payload.get("type_id"))
    if not node_id or not type_id:
        return None
    x = _try_float(payload.get("x", 0.0))
    y = _try_float(payload.get("y", 0.0))
    if strict_payload and (x is None or y is None):
        return None
    custom_width = None
    if payload.get("custom_width") is not None:
        custom_width = _try_float(payload.get("custom_width"))
        if strict_payload and custom_width is None:
            return None
    custom_height = None
    if payload.get("custom_height") is not None:
        custom_height = _try_float(payload.get("custom_height"))
        if strict_payload and custom_height is None:
            return None
    raw_properties = _as_mapping(payload.get("properties", {}), strict=strict_payload)
    raw_exposed_ports = _as_mapping(payload.get("exposed_ports", {}), strict=strict_payload)
    raw_port_labels = _as_mapping(payload.get("port_labels", {}), strict=strict_payload)
    if raw_properties is None or raw_exposed_ports is None or raw_port_labels is None:
        return None
    raw_locked_ports = payload.get("locked_ports")
    if strict_payload and raw_locked_ports is not None and not isinstance(raw_locked_ports, Mapping):
        return None
    normalized_exposed_ports: dict[str, bool] = {}
    for key, value in raw_exposed_ports.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            if strict_payload:
                return None
            continue
        normalized_exposed_ports[normalized_key] = bool(value)
    parent_node_id = _coerce_str(payload.get("parent_node_id")) or None
    return NodeInstance(
        node_id=node_id,
        type_id=type_id,
        title=_coerce_str(payload.get("title"), type_id),
        x=0.0 if x is None else x,
        y=0.0 if y is None else y,
        collapsed=bool(payload.get("collapsed", False)),
        properties=raw_properties,
        exposed_ports=normalized_exposed_ports,
        locked_ports=normalize_locked_ports_mapping(raw_locked_ports),
        port_labels={str(k): str(v) for k, v in raw_port_labels.items() if str(v).strip()},
        visual_style=_as_mapping(payload.get("visual_style")) or {},
        parent_node_id=parent_node_id,
        custom_width=custom_width,
        custom_height=custom_height,
    )


def node_instance_to_mapping(
    node: "NodeInstance",
    *,
    node_id_key: str = "node_id",
) -> dict[str, Any]:
    return {
        node_id_key: node.node_id,
        "type_id": node.type_id,
        "title": node.title,
        "x": node.x,
        "y": node.y,
        "collapsed": node.collapsed,
        "properties": copy.deepcopy(node.properties),
        "exposed_ports": copy.deepcopy(node.exposed_ports),
        "locked_ports": copy.deepcopy(node.locked_ports),
        "port_labels": copy.deepcopy(node.port_labels),
        "visual_style": copy.deepcopy(node.visual_style),
        "parent_node_id": node.parent_node_id,
        "custom_width": node.custom_width,
        "custom_height": node.custom_height,
    }


def edge_instance_from_mapping(
    payload: Mapping[str, Any],
    *,
    edge_id_key: str | None = "edge_id",
    source_node_id_key: str = "source_node_id",
    target_node_id_key: str = "target_node_id",
    require_edge_id: bool = True,
) -> EdgeInstance | None:
    edge_id = _coerce_str(payload.get(edge_id_key)) if edge_id_key is not None else ""
    source_node_id = _coerce_str(payload.get(source_node_id_key))
    source_port_key = _coerce_str(payload.get("source_port_key"))
    target_node_id = _coerce_str(payload.get(target_node_id_key))
    target_port_key = _coerce_str(payload.get("target_port_key"))
    if (
        (require_edge_id and not edge_id)
        or not source_node_id
        or not source_port_key
        or not target_node_id
        or not target_port_key
    ):
        return None
    return EdgeInstance(
        edge_id=edge_id,
        source_node_id=source_node_id,
        source_port_key=source_port_key,
        target_node_id=target_node_id,
        target_port_key=target_port_key,
        label=_coerce_str(payload.get("label")),
        visual_style=_as_mapping(payload.get("visual_style")) or {},
    )


def edge_instance_to_mapping(
    edge: "EdgeInstance",
    *,
    edge_id_key: str | None = "edge_id",
    source_node_id_key: str = "source_node_id",
    target_node_id_key: str = "target_node_id",
) -> dict[str, Any]:
    payload = {
        source_node_id_key: edge.source_node_id,
        "source_port_key": edge.source_port_key,
        target_node_id_key: edge.target_node_id,
        "target_port_key": edge.target_port_key,
        "label": edge.label,
        "visual_style": copy.deepcopy(edge.visual_style),
    }
    if edge_id_key is not None:
        payload = {edge_id_key: edge.edge_id, **payload}
    return payload


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
    locked_ports: dict[str, bool] = field(default_factory=dict)
    port_labels: dict[str, str] = field(default_factory=dict)
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
    hide_locked_ports: bool = False
    hide_optional_ports: bool = False

@dataclass(eq=False)
class WorkspaceSnapshot:
    name: str
    nodes: dict[str, NodeInstance]
    edges: dict[str, EdgeInstance]
    views: dict[str, ViewState]
    active_view_id: str
    dirty: bool
    extra_state: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def capture(cls, workspace: WorkspaceData) -> "WorkspaceSnapshot":
        return cls(
            name=str(workspace.name),
            nodes={node_id: node.clone() for node_id, node in workspace.nodes.items()},
            edges={edge_id: edge.clone() for edge_id, edge in workspace.edges.items()},
            views=copy.deepcopy(workspace.views),
            active_view_id=str(workspace.active_view_id),
            dirty=bool(workspace.dirty),
            extra_state=_workspace_extra_state(workspace),
        )

    def restore(self, workspace: WorkspaceData) -> None:
        workspace.name = str(self.name)
        workspace.nodes = {node_id: node.clone() for node_id, node in self.nodes.items()}
        workspace.edges = {edge_id: edge.clone() for edge_id, edge in self.edges.items()}
        workspace.views = copy.deepcopy(self.views)
        workspace.active_view_id = str(self.active_view_id)
        workspace.dirty = bool(self.dirty)
        _restore_workspace_extra_state(workspace, self.extra_state)
        workspace.ensure_default_view()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkspaceSnapshot):
            return NotImplemented
        return (
            self.name == other.name
            and self.nodes == other.nodes
            and self.edges == other.edges
            and self.views == other.views
            and self.active_view_id == other.active_view_id
            and self.dirty == other.dirty
            and self.extra_state == other.extra_state
        )


@dataclass
class WorkspaceData:
    workspace_id: str
    name: str
    nodes: dict[str, NodeInstance] = field(default_factory=dict)
    edges: dict[str, EdgeInstance] = field(default_factory=dict)
    views: dict[str, ViewState] = field(default_factory=dict)
    active_view_id: str = ""
    dirty: bool = False

    def ensure_default_view(self) -> None:
        self.active_view_state()

    def active_view_state(self) -> ViewState:
        if not self.views:
            view = ViewState(view_id=new_id("view"), name="V1")
            self.views[view.view_id] = view
            self.active_view_id = view.view_id
            return view
        if not self.active_view_id or self.active_view_id not in self.views:
            self.active_view_id = next(iter(self.views))
        return self.views[self.active_view_id]

    def mark_dirty(self) -> None:
        self.dirty = True

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
        duplicate.ensure_default_view()
        return duplicate


def _workspace_declared_state_names() -> set[str]:
    return {item.name for item in dataclass_fields(WorkspaceData)}


def _workspace_extra_state(workspace: WorkspaceData) -> dict[str, Any]:
    declared_names = _workspace_declared_state_names()
    return {
        key: copy.deepcopy(value)
        for key, value in vars(workspace).items()
        if key not in declared_names
    }


def _restore_workspace_extra_state(workspace: WorkspaceData, extra_state: Mapping[str, Any]) -> None:
    declared_names = _workspace_declared_state_names()
    for key in list(vars(workspace)):
        if key not in declared_names:
            delattr(workspace, key)
    for key, value in dict(extra_state or {}).items():
        if key not in declared_names:
            setattr(workspace, key, copy.deepcopy(value))


def sanitize_workspace_parent_links(workspace: WorkspaceData) -> None:
    for node in workspace.nodes.values():
        parent_id = str(node.parent_node_id or "").strip() or None
        if parent_id is None:
            continue
        if parent_id == node.node_id:
            node.parent_node_id = None
            continue
        if parent_id not in workspace.nodes:
            node.parent_node_id = None


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
        elif not self.active_workspace_id or self.active_workspace_id not in self.workspaces:
            self.active_workspace_id = next(iter(self.workspaces))
        return self.workspaces[self.active_workspace_id]


class GraphModel:
    def __init__(
        self,
        project: ProjectData | None = None,
        *,
        mutation_service_factory: "WorkspaceMutationServiceFactory | None" = None,
    ) -> None:
        self.project = project or ProjectData(project_id=new_id("proj"), name="untitled")
        self._mutation_service_factory = mutation_service_factory
        self.project.ensure_default_workspace()

    @property
    def active_workspace(self) -> WorkspaceData:
        self.project.ensure_default_workspace()
        return self.project.workspaces[self.project.active_workspace_id]

    def _resolved_mutation_service_factory(self) -> "WorkspaceMutationServiceFactory":
        if self._mutation_service_factory is None:
            from ea_node_editor.graph.mutation_service import create_workspace_mutation_service

            self._mutation_service_factory = create_workspace_mutation_service
        return self._mutation_service_factory

    def mutation_service(
        self,
        workspace_id: str,
        registry: "NodeRegistry | None" = None,
        *,
        boundary_adapters: "GraphBoundaryAdapters | None" = None,
    ) -> "WorkspaceMutationService":
        if workspace_id not in self.project.workspaces:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        return self._resolved_mutation_service_factory()(
            model=self,
            workspace_id=workspace_id,
            registry=registry,
            boundary_adapters=boundary_adapters,
        )

    def validated_mutations(
        self,
        workspace_id: str,
        registry: "NodeRegistry",
        *,
        boundary_adapters: "GraphBoundaryAdapters | None" = None,
    ) -> "WorkspaceMutationService":
        return self.mutation_service(
            workspace_id,
            registry=registry,
            boundary_adapters=boundary_adapters,
        )

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

    def _create_view_record(
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
            hide_locked_ports=source_view.hide_locked_ports if source_view is not None else False,
            hide_optional_ports=source_view.hide_optional_ports if source_view is not None else False,
        )
        workspace.views[view.view_id] = view
        workspace.active_view_id = view.view_id
        return view

    def create_view(
        self,
        workspace_id: str,
        name: str | None = None,
        *,
        source_view_id: str | None = None,
    ) -> ViewState:
        return self.mutation_service(workspace_id).create_view(
            name=name,
            source_view_id=source_view_id,
        )

    def _set_active_view_record(self, workspace_id: str, view_id: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.ensure_default_view()
        if view_id not in workspace.views:
            raise KeyError(f"Unknown view: {view_id}")
        workspace.active_view_id = view_id

    def set_active_view(self, workspace_id: str, view_id: str) -> None:
        self.mutation_service(workspace_id).set_active_view(view_id)

    def _close_view_record(self, workspace_id: str, view_id: str) -> None:
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

    def close_view(self, workspace_id: str, view_id: str) -> None:
        self.mutation_service(workspace_id).close_view(view_id)

    def _rename_view_record(self, workspace_id: str, view_id: str, new_name: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.ensure_default_view()
        if view_id not in workspace.views:
            raise KeyError(f"Unknown view: {view_id}")
        workspace.views[view_id].name = new_name

    def rename_view(self, workspace_id: str, view_id: str, new_name: str) -> None:
        self.mutation_service(workspace_id).rename_view(view_id, new_name)

    def _move_view_record(self, workspace_id: str, from_index: int, to_index: int) -> None:
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

    def move_view(self, workspace_id: str, from_index: int, to_index: int) -> None:
        self.mutation_service(workspace_id).move_view(from_index, to_index)

    def _add_node_record(
        self,
        workspace_id: str,
        *,
        type_id: str = "",
        title: str = "",
        x: float = 0.0,
        y: float = 0.0,
        properties: dict[str, Any] | None = None,
        exposed_ports: dict[str, bool] | None = None,
        locked_ports: dict[str, bool] | None = None,
        port_labels: dict[str, str] | None = None,
        visual_style: dict[str, Any] | None = None,
        parent_node_id: str | None = None,
        collapsed: bool = False,
        custom_width: float | None = None,
        custom_height: float | None = None,
    ) -> NodeInstance:
        workspace = self.project.workspaces[workspace_id]
        record = NodeInstance(
            node_id=new_id("node"),
            type_id=type_id,
            title=title,
            x=float(x),
            y=float(y),
            collapsed=bool(collapsed),
            properties=copy.deepcopy(properties or {}),
            exposed_ports=dict(exposed_ports or {}),
            locked_ports=normalize_locked_ports_mapping(locked_ports),
            port_labels={str(key): str(value) for key, value in dict(port_labels or {}).items()},
            visual_style=copy.deepcopy(visual_style or {}),
            parent_node_id=str(parent_node_id).strip() if parent_node_id else None,
            custom_width=custom_width,
            custom_height=custom_height,
        )
        workspace.nodes[record.node_id] = record
        workspace.mark_dirty()
        return record

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
        return self._add_node_record(
            workspace_id,
            type_id=type_id,
            title=title,
            x=x,
            y=y,
            properties=properties,
            exposed_ports=exposed_ports,
            visual_style=visual_style,
        )

    def _remove_node_record(self, workspace_id: str, node_id: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        if node_id in workspace.nodes:
            del workspace.nodes[node_id]
        for edge_id in list(workspace.edges):
            edge = workspace.edges[edge_id]
            if edge.source_node_id == node_id or edge.target_node_id == node_id:
                del workspace.edges[edge_id]
        workspace.mark_dirty()

    def remove_node(self, workspace_id: str, node_id: str) -> None:
        self._remove_node_record(workspace_id, node_id)

    def _set_node_position_record(self, workspace_id: str, node_id: str, x: float, y: float) -> None:
        workspace = self.project.workspaces[workspace_id]
        node = workspace.nodes[node_id]
        node.x = x
        node.y = y
        workspace.mark_dirty()

    def set_node_position(self, workspace_id: str, node_id: str, x: float, y: float) -> None:
        self._set_node_position_record(workspace_id, node_id, x, y)

    def _set_node_geometry_record(
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
        workspace.mark_dirty()

    def set_node_geometry(
        self,
        workspace_id: str,
        node_id: str,
        x: float,
        y: float,
        width: float | None,
        height: float | None,
    ) -> None:
        self._set_node_geometry_record(workspace_id, node_id, x, y, width, height)

    def _set_node_size_record(
        self,
        workspace_id: str,
        node_id: str,
        width: float | None,
        height: float | None,
    ) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].custom_width = width
        workspace.nodes[node_id].custom_height = height
        workspace.mark_dirty()

    def set_node_size(self, workspace_id: str, node_id: str, width: float | None, height: float | None) -> None:
        self._set_node_size_record(workspace_id, node_id, width, height)

    def _set_node_collapsed_record(self, workspace_id: str, node_id: str, collapsed: bool) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].collapsed = collapsed
        workspace.mark_dirty()

    def set_node_collapsed(self, workspace_id: str, node_id: str, collapsed: bool) -> None:
        self._set_node_collapsed_record(workspace_id, node_id, collapsed)

    def _set_node_property_record(self, workspace_id: str, node_id: str, key: str, value: Any) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].properties[key] = value
        workspace.mark_dirty()

    def set_node_property(self, workspace_id: str, node_id: str, key: str, value: Any) -> None:
        self._set_node_property_record(workspace_id, node_id, key, value)

    def _set_node_title_record(self, workspace_id: str, node_id: str, title: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].title = title
        workspace.mark_dirty()

    def set_node_title(self, workspace_id: str, node_id: str, title: str) -> None:
        self._set_node_title_record(workspace_id, node_id, title)

    def _set_node_visual_style_record(
        self,
        workspace_id: str,
        node_id: str,
        visual_style: dict[str, Any] | None,
    ) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].visual_style = copy.deepcopy(visual_style or {})
        workspace.mark_dirty()

    def set_node_visual_style(self, workspace_id: str, node_id: str, visual_style: dict[str, Any] | None) -> None:
        self._set_node_visual_style_record(workspace_id, node_id, visual_style)

    def _set_exposed_port_record(self, workspace_id: str, node_id: str, key: str, exposed: bool) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.nodes[node_id].exposed_ports[key] = exposed
        workspace.mark_dirty()

    def set_exposed_port(self, workspace_id: str, node_id: str, key: str, exposed: bool) -> None:
        self._set_exposed_port_record(workspace_id, node_id, key, exposed)

    def _set_node_parent_record(self, workspace_id: str, node_id: str, parent_node_id: str | None) -> bool:
        workspace = self.project.workspaces[workspace_id]
        node = workspace.nodes[node_id]
        normalized_parent_id = str(parent_node_id or "").strip() or None
        if node.parent_node_id == normalized_parent_id:
            return False
        node.parent_node_id = normalized_parent_id
        workspace.mark_dirty()
        return True

    def _set_port_label_record(self, workspace_id: str, node_id: str, port_key: str, label: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        node = workspace.nodes[node_id]
        if label:
            node.port_labels[port_key] = label
        else:
            node.port_labels.pop(port_key, None)
        workspace.mark_dirty()

    def set_port_label(self, workspace_id: str, node_id: str, port_key: str, label: str) -> None:
        self._set_port_label_record(workspace_id, node_id, port_key, label)

    def _add_edge_record(
        self,
        workspace_id: str,
        *,
        source_node_id: str = "",
        source_port_key: str = "",
        target_node_id: str = "",
        target_port_key: str = "",
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
        record = EdgeInstance(
            edge_id=new_id("edge"),
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
            label=str(label),
            visual_style=copy.deepcopy(visual_style or {}),
        )
        workspace.edges[record.edge_id] = record
        workspace.mark_dirty()
        return record

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
        return self._add_edge_record(
            workspace_id,
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
            label=label,
            visual_style=visual_style,
        )

    def _set_edge_label_record(self, workspace_id: str, edge_id: str, label: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.edges[edge_id].label = str(label)
        workspace.mark_dirty()

    def set_edge_label(self, workspace_id: str, edge_id: str, label: str) -> None:
        self._set_edge_label_record(workspace_id, edge_id, label)

    def _set_edge_visual_style_record(
        self,
        workspace_id: str,
        edge_id: str,
        visual_style: dict[str, Any] | None,
    ) -> None:
        workspace = self.project.workspaces[workspace_id]
        workspace.edges[edge_id].visual_style = copy.deepcopy(visual_style or {})
        workspace.mark_dirty()

    def set_edge_visual_style(self, workspace_id: str, edge_id: str, visual_style: dict[str, Any] | None) -> None:
        self._set_edge_visual_style_record(workspace_id, edge_id, visual_style)

    def _remove_edge_record(self, workspace_id: str, edge_id: str) -> None:
        workspace = self.project.workspaces[workspace_id]
        if edge_id in workspace.edges:
            del workspace.edges[edge_id]
            workspace.mark_dirty()

    def remove_edge(self, workspace_id: str, edge_id: str) -> None:
        self._remove_edge_record(workspace_id, edge_id)

    def _set_node_fragment_state_record(
        self,
        workspace_id: str,
        node_id: str,
        *,
        collapsed: bool,
        custom_width: float | None,
        custom_height: float | None,
    ) -> None:
        workspace = self.project.workspaces[workspace_id]
        node = workspace.nodes[node_id]
        node.collapsed = bool(collapsed)
        node.custom_width = custom_width
        node.custom_height = custom_height
        workspace.mark_dirty()
