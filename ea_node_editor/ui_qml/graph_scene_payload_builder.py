from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from ea_node_editor.graph.comment_backdrop_geometry import (
    CommentBackdropCandidate,
    CommentBackdropMembership,
    compute_comment_backdrop_membership,
)
from ea_node_editor.graph.hierarchy import ScopePath
from ea_node_editor.graph.effective_ports import effective_ports, ordered_ports_for_display
from ea_node_editor.graph.hierarchy import is_node_in_scope, node_scope_path, scope_edges, scope_node_ids
from ea_node_editor.graph.model import GraphModel, WorkspaceData
from ea_node_editor.nodes.builtins.subnode import is_subnode_shell_type
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.graph_theme import (
    DEFAULT_GRAPH_THEME_ID,
    GraphThemeDefinition,
    resolve_category_accent,
    resolve_graph_theme,
)
from ea_node_editor.ui.support.node_presentation import build_inline_property_items
from ea_node_editor.ui.pdf_preview_provider import clamp_pdf_page_number
from ea_node_editor.ui_qml.edge_routing import build_edge_payload, node_size
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge


class GraphScenePayloadBuilder:
    def edge_item(
        self,
        *,
        workspace: WorkspaceData,
        scope_path: ScopePath,
        edge_id: str,
    ) -> dict[str, Any] | None:
        edge = workspace.edges.get(edge_id)
        if edge is None:
            return None
        if not is_node_in_scope(workspace, edge.source_node_id, scope_path):
            return None
        if not is_node_in_scope(workspace, edge.target_node_id, scope_path):
            return None
        return {
            "edge_id": edge.edge_id,
            "source_node_id": edge.source_node_id,
            "source_port_key": edge.source_port_key,
            "target_node_id": edge.target_node_id,
            "target_port_key": edge.target_port_key,
            "label": str(edge.label),
            "visual_style": copy.deepcopy(edge.visual_style),
        }

    def rebuild_models(
        self,
        *,
        model: GraphModel | None,
        registry: NodeRegistry | None,
        workspace_id: str,
        scope_path: ScopePath,
        graph_theme_bridge: GraphThemeBridge | None,
        show_port_labels: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        nodes_payload, _backdrop_nodes_payload, minimap_nodes_payload, edges_payload = self.rebuild_partitioned_models(
            model=model,
            registry=registry,
            workspace_id=workspace_id,
            scope_path=scope_path,
            graph_theme_bridge=graph_theme_bridge,
            show_port_labels=show_port_labels,
        )
        return nodes_payload, minimap_nodes_payload, edges_payload

    def rebuild_partitioned_models(
        self,
        *,
        model: GraphModel | None,
        registry: NodeRegistry | None,
        workspace_id: str,
        scope_path: ScopePath,
        graph_theme_bridge: GraphThemeBridge | None,
        show_port_labels: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        if model is None or registry is None or not workspace_id:
            return [], [], [], []

        workspace = model.project.workspaces[workspace_id]
        return self._build_payload_models(
            workspace=workspace,
            registry=registry,
            scope_path=scope_path,
            graph_theme=self.active_graph_theme(graph_theme_bridge),
            show_port_labels=show_port_labels,
        )

    def normalize_pdf_panel_pages(
        self,
        *,
        model: GraphModel,
        registry: NodeRegistry,
        workspace: WorkspaceData,
    ) -> None:
        # Payload normalization is read-only; PDF page clamping happens on ephemeral payload copies.
        del model
        del registry
        del workspace

    @staticmethod
    def active_graph_theme(graph_theme_bridge: GraphThemeBridge | None) -> GraphThemeDefinition:
        if graph_theme_bridge is None:
            return resolve_graph_theme(DEFAULT_GRAPH_THEME_ID)
        return resolve_graph_theme(graph_theme_bridge.theme)

    def _build_payload_models(
        self,
        *,
        workspace: WorkspaceData,
        registry: NodeRegistry,
        scope_path: ScopePath,
        graph_theme: GraphThemeDefinition,
        show_port_labels: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        visible_node_ids = scope_node_ids(workspace, scope_path)
        workspace_edges = scope_edges(workspace, scope_path)
        port_connection_counts = self._port_connection_counts(workspace_edges)

        nodes_payload: list[dict[str, Any]] = []
        backdrop_nodes_payload: list[dict[str, Any]] = []
        minimap_nodes_payload: list[dict[str, Any]] = []
        node_specs: dict[str, NodeTypeSpec] = {}
        node_payload_by_id: dict[str, dict[str, Any]] = {}
        comment_backdrop_ids: set[str] = set()
        membership_candidates: list[CommentBackdropCandidate] = []

        for node_id in visible_node_ids:
            node = workspace.nodes[node_id]
            spec = registry.get_spec(node.type_id)
            node_specs[node_id] = spec
            payload_node = self._payload_node(node, spec)
            node_payload = self._build_node_payload(
                node=payload_node,
                spec=spec,
                workspace=workspace,
                port_connection_counts=port_connection_counts,
                graph_theme=graph_theme,
                show_port_labels=show_port_labels,
            )
            node_payload_by_id[node_id] = node_payload
            is_comment_backdrop = self._is_comment_backdrop_spec(spec)
            if is_comment_backdrop:
                comment_backdrop_ids.add(node_id)
            membership_candidates.append(
                CommentBackdropCandidate(
                    node_id=node_id,
                    scope_path=node_scope_path(workspace, node_id),
                    is_backdrop=is_comment_backdrop,
                    x=float(node_payload["x"]),
                    y=float(node_payload["y"]),
                    width=float(node_payload["width"]),
                    height=float(node_payload["height"]),
                )
            )
            minimap_nodes_payload.append(
                self._build_minimap_node_payload(
                    node=payload_node,
                    spec=spec,
                    workspace=workspace,
                    show_port_labels=show_port_labels,
                )
            )

        membership_by_node_id = compute_comment_backdrop_membership(membership_candidates)
        for node_id in visible_node_ids:
            node_payload = node_payload_by_id[node_id]
            is_comment_backdrop = node_id in comment_backdrop_ids
            self._apply_comment_backdrop_membership_payload(
                node_payload,
                membership_by_node_id.get(node_id),
                is_comment_backdrop=is_comment_backdrop,
            )
            if is_comment_backdrop:
                backdrop_nodes_payload.append(node_payload)
            else:
                nodes_payload.append(node_payload)

        edges_payload = build_edge_payload(
            graph_theme=graph_theme,
            workspace_edges=workspace_edges,
            workspace_nodes=workspace.nodes,
            node_specs=node_specs,
            show_port_labels=show_port_labels,
        )
        return nodes_payload, backdrop_nodes_payload, minimap_nodes_payload, edges_payload

    @staticmethod
    def _is_comment_backdrop_spec(spec: NodeTypeSpec) -> bool:
        return str(spec.surface_family or "").strip() == "comment_backdrop"

    @staticmethod
    def _apply_comment_backdrop_membership_payload(
        node_payload: dict[str, Any],
        membership: CommentBackdropMembership | None,
        *,
        is_comment_backdrop: bool,
    ) -> None:
        node_payload["owner_backdrop_id"] = str(membership.owner_backdrop_id or "") if membership is not None else ""
        node_payload["backdrop_depth"] = int(membership.backdrop_depth) if membership is not None else 0
        if membership is None or not is_comment_backdrop:
            node_payload["member_node_ids"] = []
            node_payload["member_backdrop_ids"] = []
            node_payload["contained_node_ids"] = []
            node_payload["contained_backdrop_ids"] = []
            return
        node_payload["member_node_ids"] = list(membership.member_node_ids)
        node_payload["member_backdrop_ids"] = list(membership.member_backdrop_ids)
        node_payload["contained_node_ids"] = list(membership.contained_node_ids)
        node_payload["contained_backdrop_ids"] = list(membership.contained_backdrop_ids)

    @staticmethod
    def _port_connection_counts(workspace_edges: list[Any]) -> dict[tuple[str, str], int]:
        counts: dict[tuple[str, str], int] = {}
        for edge in workspace_edges:
            source_key = (edge.source_node_id, edge.source_port_key)
            target_key = (edge.target_node_id, edge.target_port_key)
            counts[source_key] = counts.get(source_key, 0) + 1
            counts[target_key] = counts.get(target_key, 0) + 1
        return counts

    def _build_node_payload(
        self,
        *,
        node,
        spec: NodeTypeSpec,
        workspace: WorkspaceData,
        port_connection_counts: dict[tuple[str, str], int],
        graph_theme: GraphThemeDefinition,
        show_port_labels: bool = True,
    ) -> dict[str, Any]:
        surface_metrics = node_surface_metrics(
            node,
            spec,
            workspace.nodes,
            show_port_labels=show_port_labels,
        )
        width, height = node_size(
            node,
            spec,
            workspace.nodes,
            show_port_labels=show_port_labels,
        )
        inline_properties_payload = build_inline_property_items(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
            port_connection_counts=port_connection_counts,
        )
        return {
            "node_id": node.node_id,
            "type_id": node.type_id,
            "title": node.title,
            "properties": copy.deepcopy(node.properties),
            "x": float(node.x),
            "y": float(node.y),
            "width": float(width),
            "height": float(height),
            "accent": resolve_category_accent(graph_theme, spec.category),
            "collapsed": bool(node.collapsed),
            "runtime_behavior": spec.runtime_behavior,
            "surface_family": spec.surface_family,
            "surface_variant": spec.surface_variant,
            "render_quality": spec.render_quality.to_payload(),
            "surface_metrics": surface_metrics.to_payload(),
            "visual_style": copy.deepcopy(node.visual_style),
            "can_enter_scope": is_subnode_shell_type(node.type_id),
            "ports": self._build_ports_payload(
                node=node,
                spec=spec,
                workspace=workspace,
                port_connection_counts=port_connection_counts,
            ),
            "inline_properties": inline_properties_payload,
        }

    def _payload_node(self, node, spec: NodeTypeSpec):
        properties = self._payload_properties(node=node, spec=spec)
        if properties == node.properties:
            return node
        payload_node = node.clone()
        payload_node.properties = properties
        return payload_node

    @staticmethod
    def _payload_properties(*, node, spec: NodeTypeSpec) -> dict[str, Any]:
        properties = copy.deepcopy(node.properties)
        if str(spec.surface_family or "").strip() != "media":
            return properties
        if str(spec.surface_variant or "").strip() != "pdf_panel":
            return properties
        resolved_page_number = clamp_pdf_page_number(
            str(properties.get("source_path", "") or ""),
            properties.get("page_number"),
        )
        if resolved_page_number is not None:
            properties["page_number"] = resolved_page_number
        return properties

    def _build_minimap_node_payload(
        self,
        *,
        node,
        spec: NodeTypeSpec,
        workspace: WorkspaceData,
        show_port_labels: bool = True,
    ) -> dict[str, float | str]:
        width, height = node_size(
            node,
            spec,
            workspace.nodes,
            show_port_labels=show_port_labels,
        )
        return {
            "node_id": node.node_id,
            "x": float(node.x),
            "y": float(node.y),
            "width": float(width),
            "height": float(height),
        }

    def _build_ports_payload(
        self,
        *,
        node,
        spec: NodeTypeSpec,
        workspace: WorkspaceData,
        port_connection_counts: dict[tuple[str, str], int],
    ) -> list[dict[str, Any]]:
        ports_payload: list[dict[str, Any]] = []
        visible_ports = [
            port
            for port in effective_ports(
                node=node,
                spec=spec,
                workspace_nodes=workspace.nodes,
            )
            if port.exposed
        ]
        for port in ordered_ports_for_display(visible_ports):
            connection_count = port_connection_counts.get((node.node_id, port.key), 0)
            ports_payload.append(
                {
                    "key": port.key,
                    "label": port.label,
                    "direction": port.direction,
                    "kind": port.kind,
                    "data_type": port.data_type,
                    "side": port.side,
                    "exposed": bool(port.exposed),
                    "allow_multiple_connections": bool(port.allow_multiple_connections),
                    "connection_count": int(connection_count),
                    "connected": bool(connection_count),
                }
            )
        return ports_payload


__all__ = ["GraphScenePayloadBuilder"]
