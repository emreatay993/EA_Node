from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from ea_node_editor.graph.comment_backdrop_geometry import (
    CommentBackdropCandidate,
    CommentBackdropMembership,
    build_comment_backdrop_occupied_bounds,
    compute_comment_backdrop_membership,
)
from ea_node_editor.graph.boundary_adapters import GraphBoundaryAdapters, fallback_graph_boundary_adapters
from ea_node_editor.graph.hierarchy import ScopePath
from ea_node_editor.graph.effective_ports import effective_ports, ordered_ports_for_display
from ea_node_editor.graph.hierarchy import is_node_in_scope, node_scope_path, scope_edges, scope_node_ids
from ea_node_editor.graph.transform_layout_ops import LayoutNodeBounds
from ea_node_editor.graph.input_semantics import (
    driven_by_input_reason,
    inactive_input_source_key,
)
from ea_node_editor.graph.model import (
    GraphModel,
    WorkspaceData,
    edge_instance_from_mapping,
    node_instance_from_mapping,
)
from ea_node_editor.graph.port_locking import lockable_port_keys
from ea_node_editor.nodes.builtins.ansys_dpf_catalog import (
    ANSYS_DPF_DEPENDENCY,
    get_ansys_dpf_plugin_availability,
    load_ansys_dpf_plugin_descriptors,
)
from ea_node_editor.nodes.builtins.subnode import is_subnode_shell_type
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec, PortSpec
from ea_node_editor.settings import (
    DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    GRAPH_LABEL_PIXEL_SIZE_MAX,
    GRAPH_LABEL_PIXEL_SIZE_MIN,
)
from ea_node_editor.ui.graph_theme import (
    DEFAULT_GRAPH_THEME_ID,
    GraphThemeDefinition,
    resolve_category_accent,
    resolve_graph_theme,
)
from ea_node_editor.ui.support.node_presentation import build_inline_property_items
from ea_node_editor.ui_qml.edge_routing import build_edge_payload
from ea_node_editor.ui_qml.graph_geometry.standard_metrics import (
    node_surface_metrics as standard_node_surface_metrics,
    resolved_node_surface_size as resolved_standard_node_surface_size,
)
from ea_node_editor.ui_qml.graph_surface_metrics import (
    node_surface_metrics as default_node_surface_metrics,
    viewer_surface_contract_payload,
)

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge


class _GraphSceneThemeResolver:
    @staticmethod
    def active_graph_theme(graph_theme_bridge: GraphThemeBridge | None) -> GraphThemeDefinition:
        if graph_theme_bridge is None:
            return resolve_graph_theme(DEFAULT_GRAPH_THEME_ID)
        return resolve_graph_theme(graph_theme_bridge.theme)


def _normalize_graph_label_pixel_size(value: object) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return DEFAULT_GRAPH_LABEL_PIXEL_SIZE
    return max(GRAPH_LABEL_PIXEL_SIZE_MIN, min(numeric, GRAPH_LABEL_PIXEL_SIZE_MAX))


def _graph_typography_source(graph_theme_bridge: GraphThemeBridge | None) -> object | None:
    if graph_theme_bridge is None:
        return None
    host = graph_theme_bridge.parent()
    if host is None:
        return None
    presenter = getattr(host, "graph_canvas_presenter", None)
    return presenter if presenter is not None else host


def _graph_label_pixel_size(graph_theme_bridge: GraphThemeBridge | None) -> int:
    source = _graph_typography_source(graph_theme_bridge)
    if source is None:
        return DEFAULT_GRAPH_LABEL_PIXEL_SIZE
    return _normalize_graph_label_pixel_size(
        getattr(source, "graphics_graph_label_pixel_size", DEFAULT_GRAPH_LABEL_PIXEL_SIZE)
    )


def _is_standard_surface(spec: NodeTypeSpec) -> bool:
    family = str(spec.surface_family or "standard").strip() or "standard"
    return family == "standard"


@dataclass(slots=True, frozen=True)
class _PlaceholderNodeContext:
    spec: NodeTypeSpec
    unavailable_reason: str


def _placeholder_unavailable_reason() -> str:
    availability = get_ansys_dpf_plugin_availability()
    if availability.is_available:
        return ""
    if availability.summary:
        return availability.summary
    if availability.missing_dependencies:
        return ", ".join(availability.missing_dependencies)
    return f"{ANSYS_DPF_DEPENDENCY} is unavailable."


def _placeholder_spec_from_live_spec(spec: NodeTypeSpec) -> NodeTypeSpec:
    return NodeTypeSpec(
        type_id=spec.type_id,
        display_name=spec.display_name,
        category_path=spec.category_path,
        icon=spec.icon,
        ports=spec.ports,
        properties=(),
        collapsible=spec.collapsible,
        description=spec.description,
        runtime_behavior="passive",
        surface_family="standard",
    )


@lru_cache(maxsize=1)
def _dpf_placeholder_specs_by_type_id() -> dict[str, NodeTypeSpec]:
    try:
        return {
            descriptor.spec.type_id: _placeholder_spec_from_live_spec(descriptor.spec)
            for descriptor in load_ansys_dpf_plugin_descriptors()
        }
    except Exception:  # noqa: BLE001
        return {}


def _fallback_placeholder_spec(
    *,
    node_id: str,
    node_doc: Mapping[str, Any],
    unresolved_edge_docs: Mapping[str, Mapping[str, Any]],
) -> NodeTypeSpec:
    port_labels = {
        str(key).strip(): str(value).strip()
        for key, value in dict(node_doc.get("port_labels", {})).items()
        if str(key).strip() and str(value).strip()
    }
    exposed_ports = {
        str(key).strip(): bool(value)
        for key, value in dict(node_doc.get("exposed_ports", {})).items()
        if str(key).strip()
    }
    incoming_port_keys: set[str] = set()
    outgoing_port_keys: set[str] = set()
    for edge_doc in unresolved_edge_docs.values():
        if str(edge_doc.get("source_node_id", "")).strip() == node_id:
            port_key = str(edge_doc.get("source_port_key", "")).strip()
            if port_key:
                outgoing_port_keys.add(port_key)
        if str(edge_doc.get("target_node_id", "")).strip() == node_id:
            port_key = str(edge_doc.get("target_port_key", "")).strip()
            if port_key:
                incoming_port_keys.add(port_key)

    port_specs: list[PortSpec] = []
    port_keys = sorted(set(port_labels) | set(exposed_ports) | incoming_port_keys | outgoing_port_keys)
    for port_key in port_keys:
        direction = "in" if port_key in incoming_port_keys and port_key not in outgoing_port_keys else "out"
        port_specs.append(
            PortSpec(
                key=port_key,
                direction=direction,
                kind="data",
                data_type="any",
                label=port_labels.get(port_key, port_key),
                exposed=exposed_ports.get(port_key, port_key in incoming_port_keys or port_key in outgoing_port_keys),
                allow_multiple_connections=direction != "in",
                side="left" if direction == "in" else "right",
            )
        )

    title = str(node_doc.get("title", "")).strip()
    type_id = str(node_doc.get("type_id", "")).strip() or f"dpf.placeholder.{node_id}"
    return NodeTypeSpec(
        type_id=type_id,
        display_name=title or type_id,
        category_path=("Ansys DPF",),
        icon="warning",
        ports=tuple(port_specs),
        properties=(),
        runtime_behavior="passive",
        surface_family="standard",
    )


def _placeholder_context_for_node(
    *,
    node_id: str,
    node_doc: Mapping[str, Any],
    unresolved_edge_docs: Mapping[str, Mapping[str, Any]],
) -> _PlaceholderNodeContext | None:
    type_id = str(node_doc.get("type_id", "")).strip()
    if not type_id:
        return None
    spec = _dpf_placeholder_specs_by_type_id().get(type_id)
    if spec is None and not type_id.casefold().startswith("dpf."):
        return None
    if spec is None:
        spec = _fallback_placeholder_spec(
            node_id=node_id,
            node_doc=node_doc,
            unresolved_edge_docs=unresolved_edge_docs,
        )
    return _PlaceholderNodeContext(
        spec=spec,
        unavailable_reason=_placeholder_unavailable_reason(),
    )


def _payload_workspace_projection(
    workspace: WorkspaceData,
) -> tuple[WorkspaceData, dict[str, _PlaceholderNodeContext]]:
    persistence_state = workspace.capture_persistence_state()
    if not (
        persistence_state.unresolved_node_docs
        or persistence_state.unresolved_edge_docs
        or persistence_state.authored_node_overrides
    ):
        return workspace, {}

    payload_workspace = WorkspaceData(
        workspace_id=workspace.workspace_id,
        name=workspace.name,
        nodes={node_id: node.clone() for node_id, node in workspace.nodes.items()},
        edges={edge_id: edge.clone() for edge_id, edge in workspace.edges.items()},
        views=copy.deepcopy(workspace.views),
        active_view_id=workspace.active_view_id,
        dirty=workspace.dirty,
    )
    placeholder_context_by_id: dict[str, _PlaceholderNodeContext] = {}

    for node_id, node_doc in persistence_state.unresolved_node_docs.items():
        if node_id in payload_workspace.nodes or not isinstance(node_doc, Mapping):
            continue
        context = _placeholder_context_for_node(
            node_id=node_id,
            node_doc=node_doc,
            unresolved_edge_docs=persistence_state.unresolved_edge_docs,
        )
        if context is None:
            continue
        node = node_instance_from_mapping(node_doc)
        if node is None:
            continue
        if not str(node.title).strip():
            node.title = context.spec.display_name
        payload_workspace.nodes[node.node_id] = node
        placeholder_context_by_id[node.node_id] = context

    for node in payload_workspace.nodes.values():
        override_doc = persistence_state.authored_node_overrides.get(node.node_id)
        if not isinstance(override_doc, Mapping):
            continue
        parent_node_id = str(override_doc.get("parent_node_id", "")).strip() or None
        if parent_node_id is None or parent_node_id == node.node_id:
            continue
        if parent_node_id in payload_workspace.nodes:
            node.parent_node_id = parent_node_id

    for edge_id, edge_doc in persistence_state.unresolved_edge_docs.items():
        if edge_id in payload_workspace.edges or not isinstance(edge_doc, Mapping):
            continue
        edge = edge_instance_from_mapping(edge_doc)
        if edge is None:
            continue
        if edge.source_node_id not in payload_workspace.nodes or edge.target_node_id not in payload_workspace.nodes:
            continue
        payload_workspace.edges[edge.edge_id] = edge

    return payload_workspace, placeholder_context_by_id


class _GraphSceneNodePayloadFactory:
    def __init__(self, boundary_adapters: GraphBoundaryAdapters) -> None:
        self._boundary_adapters = boundary_adapters

    @staticmethod
    def _surface_metrics(
        *,
        node,
        spec: NodeTypeSpec,
        workspace_nodes: dict[str, Any],
        show_port_labels: bool,
        graph_label_pixel_size: int,
    ):
        if _is_standard_surface(spec):
            return standard_node_surface_metrics(
                node,
                spec,
                workspace_nodes,
                show_port_labels=show_port_labels,
                graph_label_pixel_size=graph_label_pixel_size,
            )
        return default_node_surface_metrics(
            node,
            spec,
            workspace_nodes,
            show_port_labels=show_port_labels,
        )

    def _resolved_payload_node(
        self,
        *,
        node,
        spec: NodeTypeSpec,
        workspace_nodes: dict[str, Any],
        show_port_labels: bool,
        graph_label_pixel_size: int,
    ):
        payload_node = self.payload_node(node, spec)
        if not _is_standard_surface(spec):
            return payload_node
        if payload_node is node:
            payload_node = node.clone()
        surface_metrics = self._surface_metrics(
            node=payload_node,
            spec=spec,
            workspace_nodes=workspace_nodes,
            show_port_labels=show_port_labels,
            graph_label_pixel_size=graph_label_pixel_size,
        )
        width, height = resolved_standard_node_surface_size(
            payload_node,
            spec,
            workspace_nodes,
            show_port_labels=show_port_labels,
            surface_metrics=surface_metrics,
            graph_label_pixel_size=graph_label_pixel_size,
        )
        payload_node.custom_width = float(width)
        payload_node.custom_height = float(height)
        return payload_node

    def build_node_payload(
        self,
        *,
        node,
        spec: NodeTypeSpec,
        workspace: WorkspaceData,
        workspace_nodes: dict[str, Any],
        port_connection_counts: dict[tuple[str, str], int],
        graph_theme: GraphThemeDefinition,
        placeholder_context: _PlaceholderNodeContext | None = None,
        hide_locked_ports: bool = False,
        hide_optional_ports: bool = False,
        show_port_labels: bool = True,
        graph_label_pixel_size: int = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    ) -> dict[str, Any]:
        surface_metrics = self._surface_metrics(
            node=node,
            spec=spec,
            workspace_nodes=workspace_nodes,
            show_port_labels=show_port_labels,
            graph_label_pixel_size=graph_label_pixel_size,
        )
        width, height = self._boundary_adapters.node_size(
            node,
            spec,
            workspace_nodes,
            show_port_labels=show_port_labels,
        )
        inline_properties_payload = []
        if placeholder_context is None:
            inline_properties_payload = build_inline_property_items(
                node=node,
                spec=spec,
                workspace_nodes=workspace_nodes,
                port_connection_counts=port_connection_counts,
            )
        payload = {
            "node_id": node.node_id,
            "type_id": node.type_id,
            "title": node.title,
            "display_name": spec.display_name,
            "properties": copy.deepcopy(node.properties),
            "x": float(node.x),
            "y": float(node.y),
            "width": float(width),
            "height": float(height),
            "accent": resolve_category_accent(graph_theme, spec.category_path),
            "collapsed": bool(node.collapsed),
            "runtime_behavior": spec.runtime_behavior,
            "surface_family": spec.surface_family,
            "surface_variant": spec.surface_variant,
            "render_quality": spec.render_quality.to_payload(),
            "surface_metrics": surface_metrics.to_payload(),
            "visual_style": copy.deepcopy(node.visual_style),
            "can_enter_scope": is_subnode_shell_type(node.type_id),
            "unresolved": placeholder_context is not None,
            "read_only": placeholder_context is not None,
            "unavailable_reason": (
                placeholder_context.unavailable_reason
                if placeholder_context is not None
                else ""
            ),
            "ports": self.build_ports_payload(
                node=node,
                spec=spec,
                workspace=workspace,
                workspace_nodes=workspace_nodes,
                port_connection_counts=port_connection_counts,
                hide_locked_ports=hide_locked_ports,
                hide_optional_ports=hide_optional_ports,
            ),
            "inline_properties": inline_properties_payload,
        }
        if str(spec.surface_family or "").strip() == "viewer":
            payload["viewer_surface"] = viewer_surface_contract_payload(
                width=width,
                height=height,
                surface_metrics=surface_metrics,
            )
        return payload

    def payload_node(self, node, spec: NodeTypeSpec):
        properties = self.payload_properties(node=node, spec=spec)
        if properties == node.properties:
            return node
        payload_node = node.clone()
        payload_node.properties = properties
        return payload_node

    def payload_properties(self, *, node, spec: NodeTypeSpec) -> dict[str, Any]:
        properties = copy.deepcopy(node.properties)
        if str(spec.surface_family or "").strip() != "media":
            return properties
        if str(spec.surface_variant or "").strip() != "pdf_panel":
            return properties
        resolved_page_number = self._boundary_adapters.clamp_pdf_page_number(
            str(properties.get("source_path", "") or ""),
            properties.get("page_number"),
        )
        if resolved_page_number is not None:
            properties["page_number"] = resolved_page_number
        return properties

    def build_minimap_node_payload(
        self,
        *,
        node,
        spec: NodeTypeSpec,
        workspace: WorkspaceData,
        workspace_nodes: dict[str, Any],
        show_port_labels: bool = True,
    ) -> dict[str, float | str]:
        width, height = self._boundary_adapters.node_size(
            node,
            spec,
            workspace_nodes,
            show_port_labels=show_port_labels,
        )
        return {
            "node_id": node.node_id,
            "x": float(node.x),
            "y": float(node.y),
            "width": float(width),
            "height": float(height),
        }

    def build_ports_payload(
        self,
        *,
        node,
        spec: NodeTypeSpec,
        workspace: WorkspaceData,
        workspace_nodes: dict[str, Any],
        port_connection_counts: dict[tuple[str, str], int],
        hide_locked_ports: bool,
        hide_optional_ports: bool,
    ) -> list[dict[str, Any]]:
        ports_payload: list[dict[str, Any]] = []
        lockable_keys = frozenset(lockable_port_keys(spec))
        visible_ports = [
            port
            for port in effective_ports(
                node=node,
                spec=spec,
                workspace_nodes=workspace_nodes,
            )
            if port.exposed
            and (not hide_locked_ports or not port.locked)
            and (not hide_optional_ports or port.required)
        ]
        connected_input_port_keys = {
            str(port.key)
            for port in visible_ports
            if str(port.direction).strip().lower() == "in"
            and port_connection_counts.get((node.node_id, port.key), 0) > 0
        }
        for port in ordered_ports_for_display(visible_ports):
            connection_count = port_connection_counts.get((node.node_id, port.key), 0)
            inactive_source_key = ""
            if str(port.direction).strip().lower() == "in":
                inactive_source_key = (
                    inactive_input_source_key(str(node.type_id), str(port.key), connected_input_port_keys) or ""
                )
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
                    "locked": bool(port.locked),
                    "lockable": str(port.key) in lockable_keys,
                    "optional": not bool(port.required),
                    "inactive": bool(inactive_source_key),
                    "inactive_source_key": inactive_source_key,
                    "inactive_reason": driven_by_input_reason(inactive_source_key),
                }
            )
        return ports_payload

    @staticmethod
    def is_comment_backdrop_spec(spec: NodeTypeSpec) -> bool:
        return str(spec.surface_family or "").strip() == "comment_backdrop"

    def membership_candidate_size(
        self,
        *,
        node,
        spec: NodeTypeSpec,
        workspace: WorkspaceData,
        workspace_nodes: dict[str, Any],
        is_comment_backdrop: bool,
        show_port_labels: bool = True,
        graph_label_pixel_size: int = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    ) -> tuple[float, float]:
        if not is_comment_backdrop:
            return self._boundary_adapters.node_size(
                node,
                spec,
                workspace_nodes,
                show_port_labels=show_port_labels,
            )
        surface_metrics = self._surface_metrics(
            node=node,
            spec=spec,
            workspace_nodes=workspace_nodes,
            show_port_labels=show_port_labels,
            graph_label_pixel_size=graph_label_pixel_size,
        )
        # Backdrop membership keeps the expanded surface envelope so collapsed
        # backdrops still own and serialize their descendants.
        width = node.custom_width if node.custom_width is not None else surface_metrics.default_width
        height = node.custom_height if node.custom_height is not None else surface_metrics.default_height
        return max(float(surface_metrics.min_width), float(width)), float(height)

    def layout_bounds(
        self,
        *,
        node,
        spec: NodeTypeSpec,
        workspace_nodes: dict[str, Any],
        show_port_labels: bool = True,
        graph_label_pixel_size: int = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
        expanded: bool = False,
    ) -> LayoutNodeBounds:
        payload_node = node.clone()
        if expanded:
            payload_node.collapsed = False
        scoped_nodes = dict(workspace_nodes)
        scoped_nodes[node.node_id] = payload_node
        resolved_node = self._resolved_payload_node(
            node=payload_node,
            spec=spec,
            workspace_nodes=scoped_nodes,
            show_port_labels=show_port_labels,
            graph_label_pixel_size=graph_label_pixel_size,
        )
        scoped_nodes[node.node_id] = resolved_node
        width, height = self._boundary_adapters.node_size(
            resolved_node,
            spec,
            scoped_nodes,
            show_port_labels=show_port_labels,
        )
        return LayoutNodeBounds(
            node_id=node.node_id,
            x=float(node.x),
            y=float(node.y),
            width=max(1.0, float(width)),
            height=max(1.0, float(height)),
        )


class _GraphSceneBackdropPartitioner:
    def __init__(self, node_payload_factory: _GraphSceneNodePayloadFactory) -> None:
        self._node_payload_factory = node_payload_factory

    @staticmethod
    def active_view_port_filters(workspace: WorkspaceData) -> tuple[bool, bool]:
        if not workspace.views:
            return False, False
        active_view = workspace.views.get(workspace.active_view_id)
        if active_view is None:
            active_view = next(iter(workspace.views.values()), None)
        if active_view is None:
            return False, False
        return bool(active_view.hide_locked_ports), bool(active_view.hide_optional_ports)

    def build_payload_models(
        self,
        *,
        workspace: WorkspaceData,
        registry: NodeRegistry,
        scope_path: ScopePath,
        graph_theme: GraphThemeDefinition,
        comment_peek_node_id: str = "",
        placeholder_context_by_id: Mapping[str, _PlaceholderNodeContext] | None = None,
        graph_label_pixel_size: int = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
        show_port_labels: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        visible_node_ids = scope_node_ids(workspace, scope_path)
        comment_peek_node_id = str(comment_peek_node_id or "").strip()
        workspace_edges = scope_edges(workspace, scope_path)
        port_connection_counts = self.port_connection_counts(workspace_edges)
        workspace_nodes = dict(workspace.nodes)
        placeholder_context_by_id = dict(placeholder_context_by_id or {})
        hide_locked_ports, hide_optional_ports = self.active_view_port_filters(workspace)

        nodes_payload: list[dict[str, Any]] = []
        backdrop_nodes_payload: list[dict[str, Any]] = []
        minimap_nodes_payload: list[dict[str, Any]] = []
        node_specs: dict[str, NodeTypeSpec] = {}
        node_payload_by_id: dict[str, dict[str, Any]] = {}
        minimap_payload_by_id: dict[str, dict[str, float | str]] = {}
        comment_backdrop_ids: set[str] = set()
        membership_candidates: list[CommentBackdropCandidate] = []

        for node_id in visible_node_ids:
            node = workspace.nodes[node_id]
            placeholder_context = placeholder_context_by_id.get(node_id)
            spec = registry.spec_or_none(node.type_id)
            if spec is None and placeholder_context is not None:
                spec = placeholder_context.spec
            if spec is None:
                continue
            node_specs[node_id] = spec
            payload_node = self._node_payload_factory._resolved_payload_node(
                node=node,
                spec=spec,
                workspace_nodes=workspace_nodes,
                show_port_labels=show_port_labels,
                graph_label_pixel_size=graph_label_pixel_size,
            )
            workspace_nodes[node_id] = payload_node
            node_payload = self._node_payload_factory.build_node_payload(
                node=payload_node,
                spec=spec,
                workspace=workspace,
                workspace_nodes=workspace_nodes,
                port_connection_counts=port_connection_counts,
                graph_theme=graph_theme,
                placeholder_context=placeholder_context,
                hide_locked_ports=hide_locked_ports,
                hide_optional_ports=hide_optional_ports,
                show_port_labels=show_port_labels,
                graph_label_pixel_size=graph_label_pixel_size,
            )
            node_payload_by_id[node_id] = node_payload
            is_comment_backdrop = self._node_payload_factory.is_comment_backdrop_spec(spec)
            if is_comment_backdrop:
                comment_backdrop_ids.add(node_id)
            membership_width, membership_height = self._node_payload_factory.membership_candidate_size(
                node=payload_node,
                spec=spec,
                workspace=workspace,
                workspace_nodes=workspace_nodes,
                is_comment_backdrop=is_comment_backdrop,
                show_port_labels=show_port_labels,
                graph_label_pixel_size=graph_label_pixel_size,
            )
            membership_candidates.append(
                CommentBackdropCandidate(
                    node_id=node_id,
                    scope_path=node_scope_path(workspace, node_id),
                    is_backdrop=is_comment_backdrop,
                    x=float(node_payload["x"]),
                    y=float(node_payload["y"]),
                    width=float(membership_width),
                    height=float(membership_height),
                )
            )
            minimap_payload_by_id[node_id] = self._node_payload_factory.build_minimap_node_payload(
                node=payload_node,
                spec=spec,
                workspace=workspace,
                workspace_nodes=workspace_nodes,
                show_port_labels=show_port_labels,
            )

        membership_by_node_id = compute_comment_backdrop_membership(membership_candidates)
        comment_peek_visible_node_ids = self.comment_peek_visible_node_ids(
            comment_peek_node_id=comment_peek_node_id,
            visible_node_ids=visible_node_ids,
            membership_by_node_id=membership_by_node_id,
            workspace=workspace,
            comment_backdrop_ids=comment_backdrop_ids,
        )
        render_node_ids = set(comment_peek_visible_node_ids) if comment_peek_visible_node_ids else set(visible_node_ids)
        self.apply_expanded_occupied_bounds_payload(
            node_payload_by_id=node_payload_by_id,
            node_specs=node_specs,
            workspace=workspace,
            workspace_nodes=workspace_nodes,
            membership_by_node_id=membership_by_node_id,
            comment_backdrop_ids=comment_backdrop_ids,
            show_port_labels=show_port_labels,
            graph_label_pixel_size=graph_label_pixel_size,
        )
        collapsed_proxy_backdrop_by_node_id = self.collapsed_proxy_backdrop_by_node_id(
            visible_node_ids=visible_node_ids,
            membership_by_node_id=membership_by_node_id,
            workspace=workspace,
            comment_backdrop_ids=comment_backdrop_ids,
            comment_peek_node_id=comment_peek_node_id if comment_peek_visible_node_ids else "",
        )
        for node_id in visible_node_ids:
            if node_id not in render_node_ids:
                continue
            if collapsed_proxy_backdrop_by_node_id.get(node_id):
                continue
            if node_id not in node_payload_by_id or node_id not in minimap_payload_by_id:
                continue
            node_payload = node_payload_by_id[node_id]
            is_comment_backdrop = node_id in comment_backdrop_ids
            self.apply_comment_backdrop_membership_payload(
                node_payload,
                membership_by_node_id.get(node_id),
                is_comment_backdrop=is_comment_backdrop,
            )
            if is_comment_backdrop:
                backdrop_nodes_payload.append(node_payload)
            else:
                nodes_payload.append(node_payload)
            minimap_nodes_payload.append(minimap_payload_by_id[node_id])

        render_workspace_edges = [
            edge
            for edge in workspace_edges
            if edge.source_node_id in render_node_ids and edge.target_node_id in render_node_ids
        ]
        edges_payload = build_edge_payload(
            graph_theme=graph_theme,
            workspace_edges=render_workspace_edges,
            workspace_nodes=workspace_nodes,
            node_specs=node_specs,
            collapsed_proxy_backdrop_by_node_id=collapsed_proxy_backdrop_by_node_id,
            show_port_labels=show_port_labels,
        )
        return nodes_payload, backdrop_nodes_payload, minimap_nodes_payload, edges_payload

    @staticmethod
    def comment_peek_visible_node_ids(
        *,
        comment_peek_node_id: str,
        visible_node_ids: list[str],
        membership_by_node_id: dict[str, CommentBackdropMembership],
        workspace: WorkspaceData,
        comment_backdrop_ids: set[str],
    ) -> set[str]:
        normalized = str(comment_peek_node_id or "").strip()
        if not normalized or normalized not in visible_node_ids or normalized not in comment_backdrop_ids:
            return set()
        node = workspace.nodes.get(normalized)
        if node is None or not bool(node.collapsed):
            return set()
        membership = membership_by_node_id.get(normalized)
        direct_member_ids = [] if membership is None else [*membership.member_node_ids, *membership.member_backdrop_ids]
        visible_set = set(visible_node_ids)
        return {
            node_id
            for node_id in [normalized, *direct_member_ids]
            if node_id in visible_set and node_id in workspace.nodes
        }

    @staticmethod
    def collapsed_proxy_backdrop_by_node_id(
        *,
        visible_node_ids: list[str],
        membership_by_node_id: dict[str, CommentBackdropMembership],
        workspace: WorkspaceData,
        comment_backdrop_ids: set[str],
        comment_peek_node_id: str = "",
    ) -> dict[str, str]:
        collapsed_backdrop_ids = {
            node_id
            for node_id in comment_backdrop_ids
            if bool(workspace.nodes.get(node_id) is not None and workspace.nodes[node_id].collapsed)
        }
        if comment_peek_node_id:
            collapsed_backdrop_ids.discard(str(comment_peek_node_id))
        owner_backdrop_by_node_id = {
            node_id: str(membership.owner_backdrop_id or "")
            for node_id, membership in membership_by_node_id.items()
        }
        proxy_backdrop_by_node_id: dict[str, str] = {}
        for node_id in visible_node_ids:
            proxy_backdrop_id = ""
            owner_backdrop_id = owner_backdrop_by_node_id.get(node_id, "")
            while owner_backdrop_id:
                if owner_backdrop_id in collapsed_backdrop_ids:
                    proxy_backdrop_id = owner_backdrop_id
                owner_backdrop_id = owner_backdrop_by_node_id.get(owner_backdrop_id, "")
            proxy_backdrop_by_node_id[node_id] = proxy_backdrop_id
        return proxy_backdrop_by_node_id

    @staticmethod
    def apply_comment_backdrop_membership_payload(
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

    def apply_expanded_occupied_bounds_payload(
        self,
        *,
        node_payload_by_id: dict[str, dict[str, Any]],
        node_specs: dict[str, NodeTypeSpec],
        workspace: WorkspaceData,
        workspace_nodes: dict[str, Any],
        membership_by_node_id: dict[str, CommentBackdropMembership],
        comment_backdrop_ids: set[str],
        show_port_labels: bool,
        graph_label_pixel_size: int,
    ) -> None:
        for node_id, node_payload in node_payload_by_id.items():
            node = workspace.nodes.get(node_id)
            spec = node_specs.get(node_id)
            if node is None or spec is None:
                continue
            bounds = self._node_payload_factory.layout_bounds(
                node=node,
                spec=spec,
                workspace_nodes=workspace_nodes,
                show_port_labels=show_port_labels,
                graph_label_pixel_size=graph_label_pixel_size,
                expanded=True,
            )
            if node_id in comment_backdrop_ids:
                membership = membership_by_node_id.get(node_id)
                direct_member_ids = (
                    []
                    if membership is None
                    else [*membership.member_node_ids, *membership.member_backdrop_ids]
                )
                member_candidates = [
                    self._payload_candidate(
                        member_payload,
                        is_backdrop=str(member_id) in comment_backdrop_ids,
                        workspace=workspace,
                    )
                    for member_id in direct_member_ids
                    if (member_payload := node_payload_by_id.get(member_id)) is not None
                ]
                occupied = build_comment_backdrop_occupied_bounds(
                    self._bounds_candidate(bounds, is_backdrop=True, workspace=workspace),
                    member_candidates,
                )
                node_payload["expanded_occupied_bounds"] = {
                    "x": float(occupied.x),
                    "y": float(occupied.y),
                    "width": float(occupied.width),
                    "height": float(occupied.height),
                }
                continue
            node_payload["expanded_occupied_bounds"] = {
                "x": float(bounds.x),
                "y": float(bounds.y),
                "width": float(bounds.width),
                "height": float(bounds.height),
            }

    @staticmethod
    def _bounds_candidate(
        bounds: LayoutNodeBounds,
        *,
        is_backdrop: bool,
        workspace: WorkspaceData,
    ) -> CommentBackdropCandidate:
        return CommentBackdropCandidate(
            node_id=str(bounds.node_id),
            scope_path=node_scope_path(workspace, str(bounds.node_id)),
            is_backdrop=is_backdrop,
            x=float(bounds.x),
            y=float(bounds.y),
            width=float(bounds.width),
            height=float(bounds.height),
        )

    @staticmethod
    def _payload_candidate(
        node_payload: dict[str, Any],
        *,
        is_backdrop: bool,
        workspace: WorkspaceData,
    ) -> CommentBackdropCandidate:
        node_id = str(node_payload.get("node_id", ""))
        return CommentBackdropCandidate(
            node_id=node_id,
            scope_path=node_scope_path(workspace, node_id),
            is_backdrop=is_backdrop,
            x=float(node_payload.get("x", 0.0)),
            y=float(node_payload.get("y", 0.0)),
            width=float(node_payload.get("width", 1.0)),
            height=float(node_payload.get("height", 1.0)),
        )

    @staticmethod
    def port_connection_counts(workspace_edges: list[Any]) -> dict[tuple[str, str], int]:
        counts: dict[tuple[str, str], int] = {}
        for edge in workspace_edges:
            source_key = (edge.source_node_id, edge.source_port_key)
            target_key = (edge.target_node_id, edge.target_port_key)
            counts[source_key] = counts.get(source_key, 0) + 1
            counts[target_key] = counts.get(target_key, 0) + 1
        return counts


class GraphScenePayloadBuilder:
    def __init__(self, boundary_adapters: GraphBoundaryAdapters | None = None) -> None:
        self.boundary_adapters = boundary_adapters or fallback_graph_boundary_adapters()
        self._theme_resolver = _GraphSceneThemeResolver()
        self._node_payload_factory = _GraphSceneNodePayloadFactory(self.boundary_adapters)
        self._backdrop_partitioner = _GraphSceneBackdropPartitioner(self._node_payload_factory)

    def edge_item(
        self,
        *,
        workspace: WorkspaceData,
        scope_path: ScopePath,
        edge_id: str,
    ) -> dict[str, Any] | None:
        payload_workspace, _placeholder_context_by_id = _payload_workspace_projection(workspace)
        edge = payload_workspace.edges.get(edge_id)
        if edge is None:
            return None
        if not is_node_in_scope(payload_workspace, edge.source_node_id, scope_path):
            return None
        if not is_node_in_scope(payload_workspace, edge.target_node_id, scope_path):
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
        comment_peek_node_id: str = "",
        show_port_labels: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        nodes_payload, _backdrop_nodes_payload, minimap_nodes_payload, edges_payload = self.rebuild_partitioned_models(
            model=model,
            registry=registry,
            workspace_id=workspace_id,
            scope_path=scope_path,
            comment_peek_node_id=comment_peek_node_id,
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
        comment_peek_node_id: str = "",
        show_port_labels: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        if model is None or registry is None or not workspace_id:
            return [], [], [], []

        workspace, placeholder_context_by_id = _payload_workspace_projection(
            model.project.workspaces[workspace_id]
        )
        graph_label_pixel_size = _graph_label_pixel_size(graph_theme_bridge)
        return self._backdrop_partitioner.build_payload_models(
            workspace=workspace,
            registry=registry,
            scope_path=scope_path,
            comment_peek_node_id=comment_peek_node_id,
            graph_theme=self.active_graph_theme(graph_theme_bridge),
            placeholder_context_by_id=placeholder_context_by_id,
            graph_label_pixel_size=graph_label_pixel_size,
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

    def active_graph_theme(self, graph_theme_bridge: GraphThemeBridge | None) -> GraphThemeDefinition:
        return self._theme_resolver.active_graph_theme(graph_theme_bridge)


__all__ = ["GraphScenePayloadBuilder"]
