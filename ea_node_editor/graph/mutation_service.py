from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence

from ea_node_editor.graph.model import EdgeInstance, GraphModel, NodeInstance, ViewState, WorkspaceData
from ea_node_editor.graph.transforms import (
    GroupSubnodeResult,
    UngroupSubnodeResult,
    _group_selection_into_subnode_transaction,
    _insert_graph_fragment_transaction,
    _ungroup_subnode_transaction,
)
from ea_node_editor.ui.pdf_preview_provider import clamp_pdf_page_number

if TYPE_CHECKING:
    from ea_node_editor.graph.normalization import ValidatedGraphMutation
    from ea_node_editor.nodes.registry import NodeRegistry


@dataclass(slots=True)
class WorkspaceMutationService:
    model: GraphModel
    workspace_id: str
    registry: NodeRegistry | None = None

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
        workspace = self.workspace
        workspace.ensure_default_view()
        view_state = workspace.views.get(workspace.active_view_id)
        if view_state is None:
            workspace.active_view_id = next(iter(workspace.views))
            view_state = workspace.views[workspace.active_view_id]
        return view_state

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
        return self.model.create_view(
            self.workspace_id,
            name=name,
            source_view_id=source_view_id,
        )

    def set_active_view(self, view_id: str) -> None:
        self.model.set_active_view(self.workspace_id, view_id)

    def close_view(self, view_id: str) -> None:
        self.model.close_view(self.workspace_id, view_id)

    def rename_view(self, view_id: str, new_name: str) -> None:
        self.model.rename_view(self.workspace_id, view_id, new_name)

    def move_view(self, from_index: int, to_index: int) -> None:
        self.model.move_view(self.workspace_id, from_index, to_index)

    def add_node(
        self,
        *,
        type_id: str,
        title: str,
        x: float,
        y: float,
        properties: dict[str, object] | None = None,
        exposed_ports: dict[str, bool] | None = None,
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
            visual_style=visual_style,
            parent_node_id=parent_node_id,
        )
        self._normalize_pdf_panel_page_number(node.node_id, validated)
        return node

    def add_node_raw(
        self,
        *,
        type_id: str,
        title: str,
        x: float,
        y: float,
        properties: dict[str, object] | None = None,
        exposed_ports: dict[str, bool] | None = None,
        visual_style: dict[str, object] | None = None,
        parent_node_id: str | None = None,
    ) -> NodeInstance:
        node = self.model.add_node(
            self.workspace_id,
            type_id=type_id,
            title=title,
            x=float(x),
            y=float(y),
            properties=None if properties is None else dict(properties),
            exposed_ports=None if exposed_ports is None else dict(exposed_ports),
            visual_style=None if visual_style is None else dict(visual_style),
        )
        self.set_node_parent_raw(node.node_id, parent_node_id)
        return node

    def set_node_parent(self, node_id: str, parent_node_id: str | None) -> bool:
        return self._validated().set_node_parent(node_id, parent_node_id)

    def set_node_parent_raw(self, node_id: str, parent_node_id: str | None) -> bool:
        node = self.workspace.nodes[node_id]
        normalized_parent_id = str(parent_node_id or "").strip() or None
        if node.parent_node_id == normalized_parent_id:
            return False
        node.parent_node_id = normalized_parent_id
        self.workspace.dirty = True
        return True

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

    def add_edge_raw(
        self,
        *,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
        label: str = "",
        visual_style: dict[str, object] | None = None,
    ) -> EdgeInstance:
        return self.model.add_edge(
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

    def remove_edge(self, edge_id: str) -> None:
        self._validated().remove_edge(edge_id)

    def remove_edge_raw(self, edge_id: str) -> None:
        self.model.remove_edge(self.workspace_id, edge_id)

    def remove_node(self, node_id: str) -> None:
        self._validated().remove_node(node_id)

    def remove_node_raw(self, node_id: str) -> None:
        self.model.remove_node(self.workspace_id, node_id)

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        self._validated().set_node_collapsed(node_id, collapsed)

    def set_node_position(self, node_id: str, x: float, y: float) -> None:
        self._validated().set_node_position(node_id, x, y)

    def set_node_geometry(
        self,
        node_id: str,
        x: float,
        y: float,
        width: float | None,
        height: float | None,
    ) -> None:
        self._validated().set_node_geometry(node_id, x, y, width, height)

    def set_node_fragment_state(
        self,
        node_id: str,
        *,
        collapsed: bool,
        custom_width: float | None,
        custom_height: float | None,
    ) -> None:
        node = self.workspace.nodes[node_id]
        node.collapsed = bool(collapsed)
        node.custom_width = custom_width
        node.custom_height = custom_height
        self.workspace.dirty = True

    def set_node_title(self, node_id: str, title: str) -> None:
        self._validated().set_node_title(node_id, title)

    def set_node_visual_style(self, node_id: str, visual_style: dict[str, object] | None) -> None:
        self._validated().set_node_visual_style(node_id, visual_style)

    def set_edge_label(self, edge_id: str, label: str) -> None:
        self._validated().set_edge_label(edge_id, label)

    def set_edge_visual_style(self, edge_id: str, visual_style: dict[str, object] | None) -> None:
        self._validated().set_edge_visual_style(edge_id, visual_style)

    def insert_graph_fragment(
        self,
        *,
        fragment_payload: dict[str, Any],
        delta_x: float,
        delta_y: float,
    ) -> list[str]:
        return _insert_graph_fragment_transaction(
            mutations=self,
            workspace=self.workspace,
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
        return _group_selection_into_subnode_transaction(
            mutations=self,
            registry=self.registry,
            workspace=self.workspace,
            selected_node_ids=selected_node_ids,
            scope_path=scope_path,
            shell_x=shell_x,
            shell_y=shell_y,
        )

    def ungroup_subnode(self, *, shell_node_id: object) -> UngroupSubnodeResult | None:
        return _ungroup_subnode_transaction(
            mutations=self,
            workspace=self.workspace,
            shell_node_id=shell_node_id,
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
        resolved_page_number = clamp_pdf_page_number(
            str(node.properties.get("source_path", "") or ""),
            node.properties.get("page_number"),
        )
        if resolved_page_number is None:
            return False
        if node.properties.get("page_number") == resolved_page_number:
            return False
        (validated or self._validated()).set_node_property(node_id, "page_number", resolved_page_number)
        return True
