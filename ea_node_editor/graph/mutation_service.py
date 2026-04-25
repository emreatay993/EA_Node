from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, Sequence

from ea_node_editor.graph.comment_backdrop_geometry import (
    COMMENT_BACKDROP_WRAP_MIN_HEIGHT,
    COMMENT_BACKDROP_WRAP_MIN_WIDTH,
    COMMENT_BACKDROP_WRAP_PADDING,
    CommentBackdropCandidate,
    CommentBackdropWrapResult,
    build_comment_backdrop_wrap_bounds,
)
from ea_node_editor.graph.boundary_adapters import GraphBoundaryAdapters, fallback_graph_boundary_adapters
from ea_node_editor.graph.hierarchy import normalize_scope_path, node_scope_path, scope_parent_id
from ea_node_editor.graph.model import EdgeInstance, GraphModel, NodeInstance, ViewState, WorkspaceData
from ea_node_editor.graph.transform_fragment_ops import _insert_graph_fragment_operation
from ea_node_editor.graph.transform_grouping_ops import (
    GroupSubnodeResult,
    UngroupSubnodeResult,
    _group_selection_into_subnode_operation,
    _ungroup_subnode_operation,
)
from ea_node_editor.nodes.builtins.passive_annotation import PASSIVE_ANNOTATION_COMMENT_BACKDROP_TYPE_ID

if TYPE_CHECKING:
    from ea_node_editor.graph.normalization import ValidatedGraphMutation
    from ea_node_editor.graph.model import GraphModel
    from ea_node_editor.nodes.registry import NodeRegistry


class WorkspaceMutationServiceFactory(Protocol):
    def __call__(
        self,
        *,
        model: GraphModel,
        workspace_id: str,
        registry: NodeRegistry | None = None,
        boundary_adapters: GraphBoundaryAdapters | None = None,
    ) -> "WorkspaceMutationService": ...


def create_workspace_mutation_service(
    *,
    model: GraphModel,
    workspace_id: str,
    registry: NodeRegistry | None = None,
    boundary_adapters: GraphBoundaryAdapters | None = None,
) -> "WorkspaceMutationService":
    service_kwargs: dict[str, Any] = {}
    if boundary_adapters is not None:
        service_kwargs["boundary_adapters"] = boundary_adapters
    return WorkspaceMutationService(
        model=model,
        workspace_id=workspace_id,
        registry=registry,
        **service_kwargs,
    )


@dataclass(slots=True)
class WorkspaceMutationService:
    model: GraphModel
    workspace_id: str
    registry: NodeRegistry | None = None
    boundary_adapters: GraphBoundaryAdapters = field(default_factory=fallback_graph_boundary_adapters)

    _PDF_PANEL_PROPERTY_KEYS = frozenset({"page_number", "source_path"})

    @property
    def workspace(self) -> WorkspaceData:
        return self.model.project.workspaces[self.workspace_id]

    def _validated(self) -> "ValidatedGraphMutation":
        if self.registry is None:
            raise RuntimeError("Node registry is required for validated graph mutations.")
        from ea_node_editor.graph.normalization import ValidatedGraphMutation

        return ValidatedGraphMutation(
            model=self.model,
            workspace_id=self.workspace_id,
            registry=self.registry,
        )

    def active_view_state(self) -> ViewState:
        return self.workspace.active_view_state()

    def save_active_view_state(self, *, zoom: float, pan_x: float, pan_y: float) -> bool:
        view_state = self.active_view_state()
        normalized_zoom = float(zoom)
        normalized_pan_x = float(pan_x)
        normalized_pan_y = float(pan_y)
        if (
            float(view_state.zoom) == normalized_zoom
            and float(view_state.pan_x) == normalized_pan_x
            and float(view_state.pan_y) == normalized_pan_y
        ):
            return False
        view_state.zoom = normalized_zoom
        view_state.pan_x = normalized_pan_x
        view_state.pan_y = normalized_pan_y
        return True

    def create_view(
        self,
        name: str | None = None,
        *,
        source_view_id: str | None = None,
    ) -> ViewState:
        return self.model._create_view_record(
            self.workspace_id,
            name=name,
            source_view_id=source_view_id,
        )

    def set_active_view(self, view_id: str) -> None:
        self.model._set_active_view_record(self.workspace_id, view_id)

    def close_view(self, view_id: str) -> None:
        self.model._close_view_record(self.workspace_id, view_id)

    def rename_view(self, view_id: str, new_name: str) -> None:
        self.model._rename_view_record(self.workspace_id, view_id, new_name)

    def move_view(self, from_index: int, to_index: int) -> None:
        self.model._move_view_record(self.workspace_id, from_index, to_index)

    def set_view_hide_locked_ports(self, hide_locked_ports: bool) -> bool:
        view_state = self.active_view_state()
        normalized = bool(hide_locked_ports)
        if bool(view_state.hide_locked_ports) == normalized:
            return False
        view_state.hide_locked_ports = normalized
        self.workspace.mark_dirty()
        return True

    def set_view_hide_optional_ports(self, hide_optional_ports: bool) -> bool:
        view_state = self.active_view_state()
        normalized = bool(hide_optional_ports)
        if bool(view_state.hide_optional_ports) == normalized:
            return False
        view_state.hide_optional_ports = normalized
        self.workspace.mark_dirty()
        return True

    def add_node(
        self,
        *,
        type_id: str,
        title: str,
        x: float,
        y: float,
        properties: dict[str, object] | None = None,
        exposed_ports: dict[str, bool] | None = None,
        locked_ports: dict[str, bool] | None = None,
        visual_style: dict[str, object] | None = None,
        parent_node_id: str | None = None,
    ) -> NodeInstance:
        validated = self._validated()
        node = validated.add_node(
            type_id=type_id,
            title=title,
            x=x,
            y=y,
            properties=properties,
            exposed_ports=exposed_ports,
            locked_ports=locked_ports,
            visual_style=visual_style,
            parent_node_id=parent_node_id,
        )
        self._normalize_pdf_panel_page_number(node.node_id, validated)
        return node

    # Packet-owned transform operations use these low-level record writers when a
    # multi-step structural edit must stage graph state before the validated layer
    # re-exposes the final graph shape.
    def _add_node_record(
        self,
        *,
        type_id: str,
        title: str,
        x: float,
        y: float,
        properties: dict[str, object] | None = None,
        exposed_ports: dict[str, bool] | None = None,
        locked_ports: dict[str, bool] | None = None,
        visual_style: dict[str, object] | None = None,
        parent_node_id: str | None = None,
    ) -> NodeInstance:
        node = self.model._add_node_record(
            self.workspace_id,
            type_id=type_id,
            title=title,
            x=float(x),
            y=float(y),
            properties=None if properties is None else dict(properties),
            exposed_ports=None if exposed_ports is None else dict(exposed_ports),
            locked_ports=locked_ports,
            visual_style=None if visual_style is None else dict(visual_style),
        )
        self._set_node_parent_record(node.node_id, parent_node_id)
        return node

    def set_node_parent(self, node_id: str, parent_node_id: str | None) -> bool:
        return self._validated().set_node_parent(node_id, parent_node_id)

    def _set_node_parent_record(self, node_id: str, parent_node_id: str | None) -> bool:
        return self.model._set_node_parent_record(self.workspace_id, node_id, parent_node_id)

    def add_edge(
        self,
        *,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
        label: str = "",
        visual_style: dict[str, object] | None = None,
    ) -> EdgeInstance:
        return self._validated().add_edge(
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
            label=label,
            visual_style=visual_style,
        )

    def _add_edge_record(
        self,
        *,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
        label: str = "",
        visual_style: dict[str, object] | None = None,
    ) -> EdgeInstance:
        return self.model._add_edge_record(
            self.workspace_id,
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
            label=label,
            visual_style=None if visual_style is None else dict(visual_style),
        )

    def ports_compatible(
        self,
        *,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        return self._validated().ports_compatible(
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
        )

    def set_node_property(self, node_id: str, key: str, value: object) -> object:
        validated = self._validated()
        normalized = validated.set_node_property(node_id, key, value)
        if key in self._PDF_PANEL_PROPERTY_KEYS and self._normalize_pdf_panel_page_number(node_id, validated):
            if key == "page_number":
                return self.workspace.nodes[node_id].properties.get("page_number")
            return normalized
        return normalized

    def set_node_properties(self, node_id: str, values: dict[str, object]) -> dict[str, object]:
        validated = self._validated()
        normalized_updates = validated.set_node_properties(node_id, values)
        if not normalized_updates:
            return {}
        if self._PDF_PANEL_PROPERTY_KEYS & normalized_updates.keys():
            if self._normalize_pdf_panel_page_number(node_id, validated):
                normalized_updates["page_number"] = self.workspace.nodes[node_id].properties.get("page_number")
        return normalized_updates

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> bool:
        return self._validated().set_exposed_port(node_id, key, exposed)

    def set_locked_port(self, node_id: str, key: str, locked: bool) -> bool:
        return self._validated().set_locked_port(node_id, key, locked)

    def set_port_label(self, node_id: str, port_key: str, label: str) -> None:
        self.model._set_port_label_record(self.workspace_id, node_id, port_key, label)

    def remove_edge(self, edge_id: str) -> None:
        self._remove_edge_record(edge_id)

    def _remove_edge_record(self, edge_id: str) -> None:
        self.model._remove_edge_record(self.workspace_id, edge_id)

    def remove_node(self, node_id: str) -> None:
        self._remove_node_record(node_id)

    def _remove_node_record(self, node_id: str) -> None:
        self.model._remove_node_record(self.workspace_id, node_id)

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        self.model._set_node_collapsed_record(self.workspace_id, node_id, collapsed)

    def set_node_position(self, node_id: str, x: float, y: float) -> None:
        self.model._set_node_position_record(self.workspace_id, node_id, x, y)

    def set_node_geometry(
        self,
        node_id: str,
        x: float,
        y: float,
        width: float | None,
        height: float | None,
    ) -> None:
        self.model._set_node_geometry_record(self.workspace_id, node_id, x, y, width, height)

    def _set_node_fragment_state_record(
        self,
        node_id: str,
        *,
        collapsed: bool,
        custom_width: float | None,
        custom_height: float | None,
    ) -> None:
        self.model._set_node_fragment_state_record(
            self.workspace_id,
            node_id,
            collapsed=collapsed,
            custom_width=custom_width,
            custom_height=custom_height,
        )

    def set_node_title(self, node_id: str, title: str) -> None:
        self.model._set_node_title_record(self.workspace_id, node_id, title)

    def set_node_visual_style(self, node_id: str, visual_style: dict[str, object] | None) -> None:
        self.model._set_node_visual_style_record(
            self.workspace_id,
            node_id,
            None if visual_style is None else dict(visual_style),
        )

    def set_edge_label(self, edge_id: str, label: str) -> None:
        self.model._set_edge_label_record(self.workspace_id, edge_id, label)

    def set_edge_visual_style(self, edge_id: str, visual_style: dict[str, object] | None) -> None:
        self.model._set_edge_visual_style_record(
            self.workspace_id,
            edge_id,
            None if visual_style is None else dict(visual_style),
        )

    def insert_graph_fragment(
        self,
        *,
        fragment_payload: dict[str, Any],
        delta_x: float,
        delta_y: float,
    ) -> list[str]:
        return _insert_graph_fragment_operation(
            mutations=self,
            fragment_payload=fragment_payload,
            delta_x=delta_x,
            delta_y=delta_y,
        )

    def group_selection_into_subnode(
        self,
        *,
        selected_node_ids: Sequence[object],
        scope_path: Sequence[object] | None,
        shell_x: float,
        shell_y: float,
    ) -> GroupSubnodeResult | None:
        if self.registry is None:
            raise RuntimeError("Node registry is required for subnode grouping transactions.")
        return _group_selection_into_subnode_operation(
            mutations=self,
            selected_node_ids=selected_node_ids,
            scope_path=scope_path,
            shell_x=shell_x,
            shell_y=shell_y,
        )

    def ungroup_subnode(self, *, shell_node_id: object) -> UngroupSubnodeResult | None:
        return _ungroup_subnode_operation(
            mutations=self,
            shell_node_id=shell_node_id,
        )

    def wrap_selection_in_comment_backdrop(
        self,
        *,
        selected_node_ids: Sequence[object],
        scope_path: Sequence[object] | None,
    ) -> CommentBackdropWrapResult | None:
        if self.registry is None:
            raise RuntimeError("Node registry is required for comment backdrop wrapping transactions.")

        workspace = self.workspace
        normalized_scope = normalize_scope_path(workspace, scope_path)
        selected_candidates: list[CommentBackdropCandidate] = []
        wrapped_node_ids: list[str] = []
        seen_node_ids: set[str] = set()

        for value in selected_node_ids:
            node_id = str(value).strip()
            if not node_id or node_id in seen_node_ids:
                continue
            node = workspace.nodes.get(node_id)
            if node is None:
                return None
            if node_scope_path(workspace, node_id) != normalized_scope:
                return None
            spec = self.registry.get_spec(node.type_id)
            width, height = self.boundary_adapters.node_size(node, spec, workspace.nodes)
            selected_candidates.append(
                CommentBackdropCandidate(
                    node_id=node_id,
                    scope_path=normalized_scope,
                    is_backdrop=(str(spec.surface_family or "").strip() == "comment_backdrop"),
                    x=float(node.x),
                    y=float(node.y),
                    width=float(width),
                    height=float(height),
                )
            )
            wrapped_node_ids.append(node_id)
            seen_node_ids.add(node_id)

        if not selected_candidates:
            return None

        bounds = build_comment_backdrop_wrap_bounds(
            selected_candidates,
            padding=COMMENT_BACKDROP_WRAP_PADDING,
            min_width=COMMENT_BACKDROP_WRAP_MIN_WIDTH,
            min_height=COMMENT_BACKDROP_WRAP_MIN_HEIGHT,
        )
        if bounds is None:
            return None

        backdrop_spec = self.registry.get_spec(PASSIVE_ANNOTATION_COMMENT_BACKDROP_TYPE_ID)
        backdrop = self.add_node(
            type_id=PASSIVE_ANNOTATION_COMMENT_BACKDROP_TYPE_ID,
            title=backdrop_spec.display_name,
            x=float(bounds.x),
            y=float(bounds.y),
            properties=self.registry.default_properties(PASSIVE_ANNOTATION_COMMENT_BACKDROP_TYPE_ID),
            exposed_ports={port.key: port.exposed for port in backdrop_spec.ports},
            parent_node_id=scope_parent_id(normalized_scope),
        )
        self.set_node_geometry(
            backdrop.node_id,
            float(bounds.x),
            float(bounds.y),
            float(bounds.width),
            float(bounds.height),
        )
        return CommentBackdropWrapResult(
            backdrop_node_id=backdrop.node_id,
            wrapped_node_ids=tuple(wrapped_node_ids),
            scope_path=normalized_scope,
            x=float(bounds.x),
            y=float(bounds.y),
            width=float(bounds.width),
            height=float(bounds.height),
        )

    def normalize_pdf_panel_pages(self) -> bool:
        if self.registry is None:
            return False
        validated = self._validated()
        changed = False
        for node_id in list(self.workspace.nodes):
            changed = self._normalize_pdf_panel_page_number(node_id, validated) or changed
        return changed

    def _normalize_pdf_panel_page_number(
        self,
        node_id: str,
        validated: "ValidatedGraphMutation | None" = None,
    ) -> bool:
        if self.registry is None:
            return False
        node = self.workspace.nodes.get(node_id)
        if node is None:
            return False
        spec = self.registry.spec_or_none(node.type_id)
        if spec is None:
            return False
        if str(spec.surface_family or "").strip() != "media":
            return False
        if str(spec.surface_variant or "").strip() != "pdf_panel":
            return False
        resolved_page_number = self.boundary_adapters.clamp_pdf_page_number(
            str(node.properties.get("source_path", "") or ""),
            node.properties.get("page_number"),
        )
        if resolved_page_number is None:
            return False
        if node.properties.get("page_number") == resolved_page_number:
            return False
        (validated or self._validated()).set_node_property(node_id, "page_number", resolved_page_number)
        return True
