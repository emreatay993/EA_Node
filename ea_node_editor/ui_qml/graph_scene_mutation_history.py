from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PyQt6.QtCore import QPointF, QRectF

from ea_node_editor.graph.effective_ports import (
    find_port,
    preferred_connection_port,
    ports_compatible,
)
from ea_node_editor.graph.hierarchy import is_node_in_scope, scope_parent_id
from ea_node_editor.graph.model import NodeInstance, WorkspaceData
from ea_node_editor.graph.transforms import (
    LayoutNodeBounds,
    build_alignment_position_updates,
    build_distribution_position_updates,
    build_subtree_fragment_payload_data,
    collect_layout_node_bounds,
    fragment_node_from_payload,
    graph_fragment_bounds,
    graph_fragment_payload_is_valid,
    normalize_layout_position_updates,
    plan_subnode_shell_pin_addition,
    snap_coordinate,
)
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_PIN_PORT_KEY,
    is_subnode_pin_type,
    is_subnode_shell_type,
)
from ea_node_editor.ui.shell.runtime_clipboard import (
    build_graph_fragment_payload,
    normalize_edge_label,
    normalize_graph_fragment_payload,
    normalize_visual_style_payload,
)
from ea_node_editor.ui.shell.runtime_history import (
    ACTION_ADD_EDGE,
    ACTION_ADD_NODE,
    ACTION_EDIT_PROPERTY,
    ACTION_MOVE_NODE,
    ACTION_REMOVE_EDGE,
    ACTION_REMOVE_NODE,
    ACTION_RENAME_NODE,
    ACTION_RESIZE_NODE,
    ACTION_TOGGLE_COLLAPSED,
    ACTION_TOGGLE_EXPOSED_PORT,
)
from ea_node_editor.ui_qml.edge_routing import node_size
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics

if TYPE_CHECKING:
    from ea_node_editor.graph.mutation_service import WorkspaceMutationService
    from ea_node_editor.graph.normalization import ValidatedGraphMutation
    from ea_node_editor.nodes.types import NodeTypeSpec
    from ea_node_editor.ui.shell.runtime_history import WorkspaceSnapshot
    from ea_node_editor.ui_qml.graph_scene_bridge import _GraphSceneContext
    from ea_node_editor.ui_qml.graph_scene_scope_selection import GraphSceneScopeSelection

_MISSING = object()
_DUPLICATE_OFFSET_X = 40.0
_DUPLICATE_OFFSET_Y = 40.0
_SNAP_GRID_SIZE = 20.0


class GraphSceneMutationHistory:
    def __init__(
        self,
        scene_context: _GraphSceneContext,
        scope_selection: GraphSceneScopeSelection,
    ) -> None:
        self._scene_context = scene_context
        self._scope_selection = scope_selection

    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        return self.create_node_from_type(
            type_id=type_id,
            x=float(x),
            y=float(y),
            parent_node_id=scope_parent_id(self._scene_context.scope_path),
            select_node=True,
        )

    def add_subnode_shell_pin(self, shell_node_id: str, pin_type_id: str) -> str:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None or registry is None:
            return ""
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return ""
        shell_node = workspace.nodes.get(str(shell_node_id).strip())
        if shell_node is None or not is_subnode_shell_type(shell_node.type_id):
            return ""
        plan = plan_subnode_shell_pin_addition(
            workspace=workspace,
            shell_node_id=shell_node_id,
            pin_type_id=pin_type_id,
        )
        if plan is None:
            return ""

        def _after_create(node: NodeInstance, mutations: ValidatedGraphMutation) -> None:
            mutations.set_exposed_port(shell_node.node_id, node.node_id, True)

        return self.create_node_from_type(
            type_id=plan.pin_type_id,
            x=plan.x,
            y=plan.y,
            parent_node_id=shell_node.node_id,
            select_node=False,
            property_overrides={SUBNODE_PIN_LABEL_PROPERTY: plan.label},
            after_create=_after_create,
        )

    def create_node_from_type(
        self,
        *,
        type_id: str,
        x: float,
        y: float,
        parent_node_id: str | None,
        select_node: bool,
        property_overrides: dict[str, Any] | None = None,
        after_create: Callable[[NodeInstance, ValidatedGraphMutation], None] | None = None,
    ) -> str:
        model, registry = self._scene_context.require_bound()
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return ""
        history_before = self._capture_history_snapshot()
        spec = registry.get_spec(type_id)
        mutations = self._mutation_boundary()
        properties = registry.default_properties(type_id)
        if property_overrides:
            properties.update(
                {
                    str(key): registry.normalize_property_value(type_id, key, value)
                    for key, value in property_overrides.items()
                }
            )
        node = mutations.add_node(
            type_id=type_id,
            title=spec.display_name,
            x=float(x),
            y=float(y),
            properties=properties,
            exposed_ports={port.key: port.exposed for port in spec.ports},
            parent_node_id=parent_node_id,
        )
        if after_create is not None:
            after_create(node, mutations)
        self._scene_context.sync_surface_title(node, spec)
        if select_node:
            self._scope_selection.set_selected_node_ids([node.node_id], workspace=workspace)
        self._scene_context.rebuild_models()
        self._record_history(ACTION_ADD_NODE, history_before)
        return node.node_id

    def are_ports_compatible(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> bool:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if registry is None or model is None:
            return False
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return False
        source_node = self._node(source_node_id)
        target_node = self._node(target_node_id)
        if source_node is None or target_node is None:
            return False
        source_spec = registry.get_spec(source_node.type_id)
        target_spec = registry.get_spec(target_node.type_id)
        source_port_doc = find_port(
            node=source_node,
            spec=source_spec,
            workspace_nodes=workspace.nodes,
            port_key=source_port,
        )
        target_port_doc = find_port(
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace.nodes,
            port_key=target_port,
        )
        if source_port_doc is None or target_port_doc is None:
            return False
        return ports_compatible(source_port_doc, target_port_doc)

    @staticmethod
    def are_port_kinds_compatible(source_kind: str, target_kind: str) -> bool:
        from ea_node_editor.graph.effective_ports import are_port_kinds_compatible

        return are_port_kinds_compatible(str(source_kind), str(target_kind))

    @staticmethod
    def are_data_types_compatible(source_type: str, target_type: str) -> bool:
        from ea_node_editor.graph.effective_ports import are_data_types_compatible

        return are_data_types_compatible(str(source_type), str(target_type))

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
        model, _registry = self._scene_context.require_bound()
        history_before = self._capture_history_snapshot()
        workspace = model.project.workspaces[self._scene_context.workspace_id]
        if not is_node_in_scope(workspace, source_node_id, self._scene_context.scope_path) or not is_node_in_scope(
            workspace,
            target_node_id,
            self._scene_context.scope_path,
        ):
            raise ValueError("Connections are only allowed for nodes in the active scope.")
        edge = self._mutation_boundary().add_edge(
            source_node_id=source_node_id,
            source_port_key=source_port,
            target_node_id=target_node_id,
            target_port_key=target_port,
        )
        self._scene_context.rebuild_models()
        self._record_history(ACTION_ADD_EDGE, history_before)
        return edge.edge_id

    def connect_nodes(self, node_a_id: str, node_b_id: str) -> str:
        model, registry = self._scene_context.require_bound()
        workspace = model.project.workspaces[self._scene_context.workspace_id]
        if not is_node_in_scope(workspace, node_a_id, self._scene_context.scope_path) or not is_node_in_scope(
            workspace,
            node_b_id,
            self._scene_context.scope_path,
        ):
            raise ValueError("Selected nodes must be in the active scope.")
        node_a = workspace.nodes[node_a_id]
        node_b = workspace.nodes[node_b_id]
        spec_a = registry.get_spec(node_a.type_id)
        spec_b = registry.get_spec(node_b.type_id)

        a_to_b = (
            preferred_connection_port(
                node=node_a,
                spec=spec_a,
                workspace_nodes=workspace.nodes,
                direction="out",
                peer_node=node_b,
            ),
            preferred_connection_port(
                node=node_b,
                spec=spec_b,
                workspace_nodes=workspace.nodes,
                direction="in",
                peer_node=node_a,
            ),
        )
        b_to_a = (
            preferred_connection_port(
                node=node_b,
                spec=spec_b,
                workspace_nodes=workspace.nodes,
                direction="out",
                peer_node=node_a,
            ),
            preferred_connection_port(
                node=node_a,
                spec=spec_a,
                workspace_nodes=workspace.nodes,
                direction="in",
                peer_node=node_b,
            ),
        )

        can_a_to_b = all(a_to_b)
        can_b_to_a = all(b_to_a)
        prefer_a_to_b = float(node_a.x) < float(node_b.x) or (
            float(node_a.x) == float(node_b.x) and float(node_a.y) <= float(node_b.y)
        )
        if can_a_to_b and (not can_b_to_a or prefer_a_to_b):
            return self.add_edge(node_a_id, a_to_b[0], node_b_id, a_to_b[1])
        if can_b_to_a:
            return self.add_edge(node_b_id, b_to_a[0], node_a_id, b_to_a[1])
        raise ValueError("Selected nodes do not have compatible out/in ports.")

    def remove_edge(self, edge_id: str) -> None:
        model = self._scene_context.model
        if model is None:
            return
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None or edge_id not in workspace.edges:
            return
        edge = workspace.edges.get(edge_id)
        if edge is None:
            return
        if not is_node_in_scope(workspace, edge.source_node_id, self._scene_context.scope_path):
            return
        if not is_node_in_scope(workspace, edge.target_node_id, self._scene_context.scope_path):
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().remove_edge(edge_id)
        self._scene_context.rebuild_models()
        self._record_history(ACTION_REMOVE_EDGE, history_before)

    def remove_node_with_policy(self, node_id: str, *, require_visible: bool) -> bool:
        model = self._scene_context.model
        if model is None:
            return False
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None or node_id not in workspace.nodes:
            return False
        if require_visible and not is_node_in_scope(workspace, node_id, self._scene_context.scope_path):
            return False
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().remove_node(node_id)
        self._scope_selection.set_selected_node_ids(
            [value for value in self._scene_context.selected_node_ids if value != node_id],
            workspace=workspace,
        )
        self._scene_context.rebuild_models()
        self._record_history(ACTION_REMOVE_NODE, history_before)
        return True

    def remove_node(self, node_id: str) -> None:
        self.remove_node_with_policy(node_id, require_visible=True)

    def remove_workspace_node(self, node_id: str) -> bool:
        return self.remove_node_with_policy(node_id, require_visible=False)

    def focus_node(self, node_id: str) -> QPointF | None:
        item = self._scope_selection.node_item(node_id)
        if item is None:
            return None
        selection_changed = self._scope_selection.set_selected_node_ids([node_id])
        if not selection_changed:
            self._scene_context.emit_node_selected(node_id)
        return item.sceneBoundingRect().center()

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        model = self._scene_context.model
        if model is None:
            return
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return
        node = workspace.nodes.get(node_id)
        if node is None:
            return
        normalized_collapsed = bool(collapsed)
        if bool(node.collapsed) == normalized_collapsed:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_node_collapsed(node_id, normalized_collapsed)
        self._scene_context.rebuild_models()
        self._record_history(ACTION_TOGGLE_COLLAPSED, history_before)

    def notify_selected_node_context_updated(self, node_id: str) -> None:
        normalized_node_id = str(node_id or "").strip()
        if normalized_node_id and normalized_node_id in self._scene_context.selected_node_lookup:
            self._scene_context.emit_node_selected(normalized_node_id)

    @staticmethod
    def _normalize_title_value(title: Any) -> str:
        return str(title).strip()

    def _normalized_title_update(self, node: NodeInstance, title: Any) -> str | None:
        normalized = self._normalize_title_value(title)
        if not normalized:
            return None
        if node.title == normalized:
            return None
        return normalized

    def _apply_title_update(
        self,
        node_id: str,
        node: NodeInstance,
        spec: NodeTypeSpec,
        normalized_title: str,
    ) -> None:
        self._mutation_boundary().set_node_title(node_id, normalized_title)
        if self._scene_context.surface_title_sync_enabled(spec):
            node.properties["title"] = normalized_title

    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None or registry is None:
            return
        workspace = model.project.workspaces[self._scene_context.workspace_id]
        node = workspace.nodes[node_id]
        spec = registry.get_spec(node.type_id)
        if key == "title":
            normalized_title = self._normalized_title_update(node, value)
            if normalized_title is None:
                return
            history_before = self._capture_history_snapshot()
            self._apply_title_update(node_id, node, spec, normalized_title)
            self._scene_context.rebuild_models()
            self.notify_selected_node_context_updated(node_id)
            self._record_history(ACTION_RENAME_NODE, history_before)
            return
        normalized = registry.normalize_property_value(node.type_id, key, value)
        current_value = node.properties.get(key, _MISSING)
        if current_value is not _MISSING and current_value == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_node_property(node_id, key, normalized)
        self._scene_context.rebuild_models()
        self.notify_selected_node_context_updated(node_id)
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None or registry is None:
            return False
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return False
        node = workspace.nodes.get(node_id)
        if node is None:
            return False
        spec = registry.get_spec(node.type_id)
        normalized_updates: dict[str, Any] = {}
        normalized_title = None
        for raw_key, raw_value in dict(values or {}).items():
            key = str(raw_key or "")
            if not key:
                continue
            if key == "title":
                normalized_title = self._normalized_title_update(node, raw_value)
                continue
            try:
                normalized = registry.normalize_property_value(node.type_id, key, raw_value)
            except KeyError:
                continue
            current_value = node.properties.get(key, _MISSING)
            if current_value is not _MISSING and current_value == normalized:
                continue
            normalized_updates[key] = normalized
        if not normalized_updates and normalized_title is None:
            return False

        history_before = self._capture_history_snapshot()
        if normalized_title is not None and not normalized_updates:
            self._apply_title_update(node_id, node, spec, normalized_title)
            self._scene_context.rebuild_models()
            self.notify_selected_node_context_updated(node_id)
            self._record_history(ACTION_RENAME_NODE, history_before)
            return True
        self._mutation_boundary().set_node_properties(node_id, normalized_updates)
        if normalized_title is not None:
            self._apply_title_update(node_id, node, spec, normalized_title)
        self._scene_context.rebuild_models()
        self.notify_selected_node_context_updated(node_id)
        self._record_history(ACTION_EDIT_PROPERTY, history_before)
        return True

    @staticmethod
    def normalize_node_visual_style(visual_style: Any) -> dict[str, Any]:
        return normalize_visual_style_payload(visual_style)

    def set_node_visual_style(self, node_id: str, visual_style: Any) -> None:
        model = self._scene_context.model
        if model is None:
            return
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return
        node = workspace.nodes.get(node_id)
        if node is None:
            return
        normalized = normalize_visual_style_payload(visual_style)
        if node.visual_style == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_node_visual_style(node_id, normalized)
        self._scene_context.rebuild_models()
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def clear_node_visual_style(self, node_id: str) -> None:
        self.set_node_visual_style(node_id, {})

    def set_node_title(self, node_id: str, title: str) -> None:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None or registry is None:
            return
        node = self._node(node_id)
        if node is None:
            return
        spec = registry.get_spec(node.type_id)
        normalized = self._normalized_title_update(node, title)
        if normalized is None:
            return
        history_before = self._capture_history_snapshot()
        self._apply_title_update(node_id, node, spec, normalized)
        self._scene_context.rebuild_models()
        self._record_history(ACTION_RENAME_NODE, history_before)

    @staticmethod
    def normalize_edge_label(label: Any) -> str:
        return normalize_edge_label(label)

    def set_edge_label(self, edge_id: str, label: Any) -> None:
        model = self._scene_context.model
        if model is None:
            return
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return
        edge = workspace.edges.get(edge_id)
        if edge is None:
            return
        normalized = normalize_edge_label(label)
        if edge.label == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_edge_label(edge_id, normalized)
        self._scene_context.rebuild_models()
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def clear_edge_label(self, edge_id: str) -> None:
        self.set_edge_label(edge_id, "")

    @staticmethod
    def normalize_edge_visual_style(visual_style: Any) -> dict[str, Any]:
        return normalize_visual_style_payload(visual_style)

    def set_edge_visual_style(self, edge_id: str, visual_style: Any) -> None:
        model = self._scene_context.model
        if model is None:
            return
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return
        edge = workspace.edges.get(edge_id)
        if edge is None:
            return
        normalized = normalize_visual_style_payload(visual_style)
        if edge.visual_style == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_edge_visual_style(edge_id, normalized)
        self._scene_context.rebuild_models()
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def clear_edge_visual_style(self, edge_id: str) -> None:
        self.set_edge_visual_style(edge_id, {})

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> None:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None or registry is None:
            return
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return
        node = workspace.nodes.get(node_id)
        if node is None:
            return
        spec = registry.get_spec(node.type_id)
        port = find_port(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
            port_key=key,
        )
        if port is None:
            return
        normalized_exposed = bool(exposed)
        current_exposed = bool(port.exposed)
        if current_exposed == normalized_exposed:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_exposed_port(node_id, key, normalized_exposed)
        self._scene_context.rebuild_models()
        self._record_history(ACTION_TOGGLE_EXPOSED_PORT, history_before)

    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None or registry is None:
            return
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return
        node = workspace.nodes.get(node_id)
        if node is None:
            return
        normalized_label = str(label or "").strip()

        if is_subnode_shell_type(node.type_id):
            pin_node = workspace.nodes.get(str(port_key or "").strip())
            if pin_node is None or str(pin_node.parent_node_id or "").strip() != str(node.node_id):
                return
            current_label = str(pin_node.properties.get(SUBNODE_PIN_LABEL_PROPERTY, "")).strip()
            if not normalized_label or normalized_label == current_label:
                return
            history_before = self._capture_history_snapshot()
            self._mutation_boundary().set_node_property(pin_node.node_id, SUBNODE_PIN_LABEL_PROPERTY, normalized_label)
            self._scene_context.rebuild_models()
            self.notify_selected_node_context_updated(node.node_id)
            self._record_history(ACTION_EDIT_PROPERTY, history_before)
            return

        if is_subnode_pin_type(node.type_id) and str(port_key or "").strip() == SUBNODE_PIN_PORT_KEY:
            current_label = str(node.properties.get(SUBNODE_PIN_LABEL_PROPERTY, "")).strip()
            if not normalized_label or normalized_label == current_label:
                return
            history_before = self._capture_history_snapshot()
            self._mutation_boundary().set_node_property(node.node_id, SUBNODE_PIN_LABEL_PROPERTY, normalized_label)
            self._scene_context.rebuild_models()
            self.notify_selected_node_context_updated(node.node_id)
            self._record_history(ACTION_EDIT_PROPERTY, history_before)
            return

        current_label = node.port_labels.get(port_key, "")
        if normalized_label == current_label:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_port_label(node_id, port_key, normalized_label)
        self._scene_context.rebuild_models()
        self.notify_selected_node_context_updated(node_id)
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def move_node(self, node_id: str, x: float, y: float) -> None:
        model = self._scene_context.model
        if model is None:
            return
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return
        if not is_node_in_scope(workspace, node_id, self._scene_context.scope_path):
            return
        node = self._node(node_id)
        if node is None:
            return
        final_x = float(x)
        final_y = float(y)
        if float(node.x) == final_x and float(node.y) == final_y:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_node_position(node_id, final_x, final_y)
        self._scene_context.rebuild_models()
        self._record_history(ACTION_MOVE_NODE, history_before)

    def resize_node(self, node_id: str, width: float, height: float) -> None:
        node = self._node(node_id)
        if node is None:
            return
        self.set_node_geometry(node_id, float(node.x), float(node.y), width, height)

    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None:
            return
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return
        node = self._node(node_id)
        if node is None:
            return
        if not is_node_in_scope(workspace, node_id, self._scene_context.scope_path):
            return
        spec = registry.get_spec(node.type_id) if registry is not None else None
        min_width = 120.0
        min_height = 50.0
        if spec is not None:
            metrics = node_surface_metrics(node, spec, workspace.nodes)
            min_width = float(metrics.min_width)
            min_height = float(metrics.min_height)
        final_x = float(x)
        final_y = float(y)
        final_w = max(min_width, float(width))
        final_h = max(min_height, float(height))
        if (
            float(node.x) == final_x
            and float(node.y) == final_y
            and node.custom_width == final_w
            and node.custom_height == final_h
        ):
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_node_geometry(
            node_id,
            final_x,
            final_y,
            final_w,
            final_h,
        )
        self._scene_context.rebuild_models()
        self._record_history(ACTION_RESIZE_NODE, history_before)

    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool:
        model = self._scene_context.model
        if model is None:
            return False
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return False

        unique_node_ids: list[str] = []
        seen_node_ids: set[str] = set()
        for value in node_ids:
            node_id = str(value).strip()
            if not node_id or node_id in seen_node_ids or node_id not in workspace.nodes:
                continue
            if not is_node_in_scope(workspace, node_id, self._scene_context.scope_path):
                continue
            seen_node_ids.add(node_id)
            unique_node_ids.append(node_id)
        if not unique_node_ids:
            return False

        delta_x = float(dx)
        delta_y = float(dy)
        if abs(delta_x) < 0.01 and abs(delta_y) < 0.01:
            return False

        history_group = self._scene_context.grouped_history_action(ACTION_MOVE_NODE, workspace)

        moved_any = False
        mutations = self._mutation_boundary()
        with history_group:
            for node_id in unique_node_ids:
                node = workspace.nodes.get(node_id)
                if node is None:
                    continue
                final_x = float(node.x) + delta_x
                final_y = float(node.y) + delta_y
                if float(node.x) == final_x and float(node.y) == final_y:
                    continue
                mutations.set_node_position(node_id, final_x, final_y)
                moved_any = True

        if not moved_any:
            return False
        self._scene_context.rebuild_models()
        return True

    def align_selected_nodes(
        self,
        alignment: str,
        *,
        snap_to_grid: bool = False,
        grid_size: float = _SNAP_GRID_SIZE,
    ) -> bool:
        workspace, selected = self._selected_layout_metrics()
        if workspace is None:
            return False
        updates = build_alignment_position_updates(
            layout_nodes=selected,
            alignment=alignment,
        )
        return self._apply_layout_updates(
            workspace,
            updates,
            snap_to_grid=snap_to_grid,
            grid_size=grid_size,
        )

    def distribute_selected_nodes(
        self,
        orientation: str,
        *,
        snap_to_grid: bool = False,
        grid_size: float = _SNAP_GRID_SIZE,
    ) -> bool:
        workspace, selected = self._selected_layout_metrics()
        if workspace is None:
            return False
        updates = build_distribution_position_updates(
            layout_nodes=selected,
            orientation=orientation,
        )
        return self._apply_layout_updates(
            workspace,
            updates,
            snap_to_grid=snap_to_grid,
            grid_size=grid_size,
        )

    def group_selected_nodes(self) -> bool:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None or registry is None:
            return False
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return False
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if len(selected_node_ids) < 2:
            return False
        selection_bounds = self._scope_selection.bounds_for_node_ids(selected_node_ids)
        if selection_bounds is None:
            return False
        transactions = self._authoring_transactions()
        if transactions is None:
            return False

        history_group = self._scene_context.grouped_history_action(ACTION_ADD_NODE, workspace)

        grouped = None
        with history_group:
            grouped = transactions.group_selection_into_subnode(
                selected_node_ids=selected_node_ids,
                scope_path=self._scene_context.scope_path,
                shell_x=selection_bounds.x(),
                shell_y=selection_bounds.y(),
            )
        if grouped is None:
            return False

        self._scope_selection.set_selected_node_ids([grouped.shell_node_id], workspace=workspace)
        self._scene_context.rebuild_models()
        return True

    def ungroup_selected_subnode(self) -> bool:
        model = self._scene_context.model
        if model is None:
            return False
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return False
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if len(selected_node_ids) != 1:
            return False
        shell_node_id = selected_node_ids[0]
        transactions = self._authoring_transactions()
        if transactions is None:
            return False

        history_group = self._scene_context.grouped_history_action(ACTION_REMOVE_NODE, workspace)

        ungrouped = None
        with history_group:
            ungrouped = transactions.ungroup_subnode(
                shell_node_id=shell_node_id,
            )
        if ungrouped is None:
            return False

        self._scope_selection.set_selected_node_ids(list(ungrouped.moved_node_ids), workspace=workspace)
        self._scene_context.rebuild_models()
        return True

    def duplicate_selected_subgraph(self) -> bool:
        fragment_payload = self.serialize_selected_subgraph_fragment()
        normalized_fragment = normalize_graph_fragment_payload(fragment_payload)
        if normalized_fragment is None:
            return False
        duplicated_node_ids = self._insert_fragment(
            normalized_fragment,
            action_type=ACTION_ADD_NODE,
            delta_x=_DUPLICATE_OFFSET_X,
            delta_y=_DUPLICATE_OFFSET_Y,
        )
        if not duplicated_node_ids:
            return False
        self._scope_selection.set_selected_node_ids(duplicated_node_ids)
        self._scene_context.rebuild_models()
        return True

    def serialize_selected_subgraph_fragment(self) -> dict[str, Any] | None:
        model = self._scene_context.model
        if model is None:
            return None
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return None
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if not selected_node_ids:
            return None
        return self._build_subgraph_fragment_payload(workspace, selected_node_ids)

    def fragment_bounds_center(self, fragment_payload: Any) -> tuple[float, float] | None:
        normalized = normalize_graph_fragment_payload(fragment_payload)
        if normalized is None:
            return None
        bounds = self._fragment_bounds(normalized["nodes"])
        if bounds is None:
            return None
        return (bounds.center().x(), bounds.center().y())

    def paste_subgraph_fragment(self, fragment_payload: Any, center_x: float, center_y: float) -> bool:
        normalized_fragment = normalize_graph_fragment_payload(fragment_payload)
        if normalized_fragment is None:
            return False

        fragment_bounds = self._fragment_bounds(normalized_fragment["nodes"])
        if fragment_bounds is None:
            return False

        delta_x = float(center_x) - fragment_bounds.center().x()
        delta_y = float(center_y) - fragment_bounds.center().y()
        pasted_node_ids = self._insert_fragment(
            normalized_fragment,
            action_type=ACTION_ADD_NODE,
            delta_x=delta_x,
            delta_y=delta_y,
        )
        if not pasted_node_ids:
            return False

        self._scope_selection.set_selected_node_ids(pasted_node_ids)
        self._scene_context.rebuild_models()
        return True

    def _node(self, node_id: str) -> NodeInstance | None:
        return self._scene_context.node(node_id)

    def _node_or_raise(self, node_id: str) -> NodeInstance:
        return self._scene_context.node_or_raise(node_id)

    def _mutation_boundary(self) -> WorkspaceMutationService:
        model, registry = self._scene_context.require_bound()
        return model.validated_mutations(self._scene_context.workspace_id, registry)

    def _authoring_transactions(self) -> WorkspaceMutationService | None:
        model = self._scene_context.model
        if model is None:
            return None
        return model.mutation_service(
            self._scene_context.workspace_id,
            registry=self._scene_context.registry,
        )

    def _find_model_edge_id(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> str | None:
        return self._scene_context.find_model_edge_id(
            source_node_id,
            source_port,
            target_node_id,
            target_port,
        )

    def _selected_node_ids_in_workspace(self, workspace: WorkspaceData) -> list[str]:
        return self._scope_selection.selected_node_ids_in_workspace(workspace)

    def _selected_layout_metrics(self) -> tuple[WorkspaceData | None, list[LayoutNodeBounds]]:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None or registry is None:
            return None, []
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return None, []
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if not selected_node_ids:
            return workspace, []
        return workspace, collect_layout_node_bounds(
            workspace=workspace,
            node_ids=selected_node_ids,
            spec_lookup=registry.get_spec,
            size_resolver=node_size,
        )

    @staticmethod
    def _snap_coordinate(value: float, grid_size: float) -> float:
        return snap_coordinate(value, grid_size, default_step=_SNAP_GRID_SIZE)

    def _apply_layout_updates(
        self,
        workspace: WorkspaceData,
        updates: dict[str, tuple[float, float]],
        *,
        snap_to_grid: bool,
        grid_size: float,
    ) -> bool:
        model = self._scene_context.model
        if model is None or not updates:
            return False

        final_positions = normalize_layout_position_updates(
            workspace=workspace,
            updates=updates,
            snap_to_grid=snap_to_grid,
            grid_size=grid_size,
            default_grid_size=_SNAP_GRID_SIZE,
        )
        if not final_positions:
            return False

        history_group = self._scene_context.grouped_history_action(ACTION_MOVE_NODE, workspace)

        mutations = self._mutation_boundary()
        with history_group:
            for node_id, (final_x, final_y) in final_positions.items():
                mutations.set_node_position(node_id, final_x, final_y)
        self._scene_context.rebuild_models()
        return True

    @staticmethod
    def _build_subgraph_fragment_payload(
        workspace: WorkspaceData,
        node_ids: list[str],
    ) -> dict[str, Any] | None:
        fragment_data = build_subtree_fragment_payload_data(
            workspace=workspace,
            selected_node_ids=node_ids,
        )
        if fragment_data is None:
            return None
        return build_graph_fragment_payload(
            nodes=fragment_data["nodes"],
            edges=fragment_data["edges"],
        )

    @staticmethod
    def _node_from_fragment_payload(node_payload: dict[str, Any]) -> NodeInstance:
        return fragment_node_from_payload(node_payload)

    def _fragment_bounds(self, nodes_payload: list[dict[str, Any]]) -> QRectF | None:
        registry = self._scene_context.registry
        if registry is None:
            return None
        bounds = graph_fragment_bounds(
            nodes_payload=nodes_payload,
            registry=registry,
            size_resolver=node_size,
        )
        if bounds is None:
            return None
        return QRectF(bounds.x, bounds.y, bounds.width, bounds.height)

    def _fragment_types_and_ports_are_valid(self, fragment_payload: dict[str, Any]) -> bool:
        registry = self._scene_context.registry
        if registry is None:
            return False
        return graph_fragment_payload_is_valid(
            fragment_payload=fragment_payload,
            registry=registry,
        )

    def _insert_fragment(
        self,
        fragment_payload: dict[str, Any],
        *,
        action_type: str,
        delta_x: float,
        delta_y: float,
    ) -> list[str]:
        model = self._scene_context.model
        if model is None:
            return []
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return []
        if not self._fragment_types_and_ports_are_valid(fragment_payload):
            return []
        transactions = self._authoring_transactions()
        if transactions is None:
            return []

        history_group = self._scene_context.grouped_history_action(action_type, workspace)

        with history_group:
            return transactions.insert_graph_fragment(
                fragment_payload=fragment_payload,
                delta_x=delta_x,
                delta_y=delta_y,
            )

    def _capture_history_snapshot(self) -> WorkspaceSnapshot | None:
        return self._scene_context.capture_history_snapshot()

    def _record_history(self, action_type: str, before_snapshot: WorkspaceSnapshot | None) -> None:
        self._scene_context.record_history(action_type, before_snapshot)


__all__ = ["GraphSceneMutationHistory"]
