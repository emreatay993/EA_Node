from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, Callable

from PyQt6.QtCore import QPointF, QRectF

from ea_node_editor.graph.effective_ports import (
    are_data_types_compatible,
    are_port_kinds_compatible,
    default_port,
    find_port,
    port_data_type,
    port_kind,
    target_port_has_capacity,
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
    group_selection_into_subnode,
    insert_graph_fragment,
    normalize_layout_position_updates,
    plan_subnode_shell_pin_addition,
    snap_coordinate,
    ungroup_subnode,
)
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_PIN_LABEL_PROPERTY,
    is_subnode_shell_type,
)
from ea_node_editor.nodes.registry import NodeRegistry
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
    from ea_node_editor.ui.shell.runtime_history import WorkspaceSnapshot
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

_MISSING = object()
_DUPLICATE_OFFSET_X = 40.0
_DUPLICATE_OFFSET_Y = 40.0
_SNAP_GRID_SIZE = 20.0


class GraphSceneMutationHistory:
    def __init__(self, bridge: GraphSceneBridge) -> None:
        self._bridge = bridge

    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        return self._create_node_from_type(
            type_id=type_id,
            x=float(x),
            y=float(y),
            parent_node_id=scope_parent_id(self._bridge._scope_path),
            select_node=True,
        )

    def add_subnode_shell_pin(self, shell_node_id: str, pin_type_id: str) -> str:
        if self._bridge._model is None or self._bridge._registry is None:
            return ""
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
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

        def _configure_pin(node: NodeInstance, _workspace: WorkspaceData, _registry: NodeRegistry) -> None:
            node.properties[SUBNODE_PIN_LABEL_PROPERTY] = plan.label
            shell_node.exposed_ports[node.node_id] = True

        return self._create_node_from_type(
            type_id=plan.pin_type_id,
            x=plan.x,
            y=plan.y,
            parent_node_id=shell_node.node_id,
            select_node=False,
            configure_node=_configure_pin,
        )

    def _create_node_from_type(
        self,
        *,
        type_id: str,
        x: float,
        y: float,
        parent_node_id: str | None,
        select_node: bool,
        configure_node: Callable[[NodeInstance, WorkspaceData, NodeRegistry], None] | None = None,
    ) -> str:
        model, registry = self._bridge._require_bound()
        workspace = model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return ""
        history_before = self._capture_history_snapshot()
        spec = registry.get_spec(type_id)
        node = model.add_node(
            self._bridge._workspace_id,
            type_id=type_id,
            title=spec.display_name,
            x=float(x),
            y=float(y),
            properties=registry.default_properties(type_id),
            exposed_ports={port.key: port.exposed for port in spec.ports},
        )
        node.parent_node_id = parent_node_id
        if configure_node is not None:
            configure_node(node, workspace, registry)
        self._bridge._sync_surface_title(node, spec)
        if select_node:
            self._bridge._set_selected_node_ids([node.node_id], workspace=workspace)
        self._bridge._rebuild_models()
        self._record_history(ACTION_ADD_NODE, history_before)
        return node.node_id

    def are_ports_compatible(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> bool:
        if self._bridge._registry is None or self._bridge._model is None:
            return False
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return False
        source_node = self._node(source_node_id)
        target_node = self._node(target_node_id)
        if source_node is None or target_node is None:
            return False
        source_spec = self._bridge._registry.get_spec(source_node.type_id)
        target_spec = self._bridge._registry.get_spec(target_node.type_id)
        try:
            source_kind = port_kind(
                node=source_node,
                spec=source_spec,
                workspace_nodes=workspace.nodes,
                port_key=source_port,
            )
            target_kind = port_kind(
                node=target_node,
                spec=target_spec,
                workspace_nodes=workspace.nodes,
                port_key=target_port,
            )
            source_dt = port_data_type(
                node=source_node,
                spec=source_spec,
                workspace_nodes=workspace.nodes,
                port_key=source_port,
            )
            target_dt = port_data_type(
                node=target_node,
                spec=target_spec,
                workspace_nodes=workspace.nodes,
                port_key=target_port,
            )
        except KeyError:
            return False
        return are_port_kinds_compatible(source_kind, target_kind) and are_data_types_compatible(
            source_dt,
            target_dt,
        )

    @staticmethod
    def are_port_kinds_compatible(source_kind: str, target_kind: str) -> bool:
        return are_port_kinds_compatible(str(source_kind), str(target_kind))

    @staticmethod
    def are_data_types_compatible(source_type: str, target_type: str) -> bool:
        return are_data_types_compatible(str(source_type), str(target_type))

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
        model, registry = self._bridge._require_bound()
        history_before = self._capture_history_snapshot()
        workspace = model.project.workspaces[self._bridge._workspace_id]
        source_node = self._node_or_raise(source_node_id)
        target_node = self._node_or_raise(target_node_id)
        if not is_node_in_scope(workspace, source_node_id, self._bridge._scope_path) or not is_node_in_scope(
            workspace,
            target_node_id,
            self._bridge._scope_path,
        ):
            raise ValueError("Connections are only allowed for nodes in the active scope.")
        source_spec = registry.get_spec(source_node.type_id)
        target_spec = registry.get_spec(target_node.type_id)
        source_port_doc = find_port(
            node=source_node,
            spec=source_spec,
            workspace_nodes=workspace.nodes,
            port_key=source_port,
        )
        if source_port_doc is None:
            raise KeyError(f"Port {source_port} not found on node type {source_spec.type_id}")
        target_port_doc = find_port(
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace.nodes,
            port_key=target_port,
        )
        if target_port_doc is None:
            raise KeyError(f"Port {target_port} not found on node type {target_spec.type_id}")

        if source_port_doc.direction != "out":
            raise ValueError(f"Source port must be an output: {source_node_id}.{source_port}")
        if target_port_doc.direction != "in":
            raise ValueError(f"Target port must be an input: {target_node_id}.{target_port}")
        source_kind = source_port_doc.kind
        target_kind = target_port_doc.kind
        if not are_port_kinds_compatible(source_kind, target_kind):
            raise ValueError(f"Incompatible port kinds: {source_kind} -> {target_kind}.")
        if not source_port_doc.exposed:
            raise ValueError(f"Source port is hidden: {source_node_id}.{source_port}")
        if not target_port_doc.exposed:
            raise ValueError(f"Target port is hidden: {target_node_id}.{target_port}")

        existing = self._find_model_edge_id(source_node_id, source_port, target_node_id, target_port)
        if existing:
            return existing
        if not target_port_has_capacity(
            edges=workspace.edges.values(),
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace.nodes,
            port_key=target_port,
        ):
            raise ValueError(f"Target input port already has a connection: {target_node_id}.{target_port}")

        edge = model.add_edge(
            self._bridge._workspace_id,
            source_node_id=source_node_id,
            source_port_key=source_port,
            target_node_id=target_node_id,
            target_port_key=target_port,
        )
        self._bridge._rebuild_models()
        self._record_history(ACTION_ADD_EDGE, history_before)
        return edge.edge_id

    def connect_nodes(self, node_a_id: str, node_b_id: str) -> str:
        model, registry = self._bridge._require_bound()
        workspace = model.project.workspaces[self._bridge._workspace_id]
        if not is_node_in_scope(workspace, node_a_id, self._bridge._scope_path) or not is_node_in_scope(
            workspace,
            node_b_id,
            self._bridge._scope_path,
        ):
            raise ValueError("Selected nodes must be in the active scope.")
        node_a = workspace.nodes[node_a_id]
        node_b = workspace.nodes[node_b_id]
        spec_a = registry.get_spec(node_a.type_id)
        spec_b = registry.get_spec(node_b.type_id)

        a_to_b = (
            default_port(
                node=node_a,
                spec=spec_a,
                workspace_nodes=workspace.nodes,
                direction="out",
            ),
            default_port(
                node=node_b,
                spec=spec_b,
                workspace_nodes=workspace.nodes,
                direction="in",
            ),
        )
        b_to_a = (
            default_port(
                node=node_b,
                spec=spec_b,
                workspace_nodes=workspace.nodes,
                direction="out",
            ),
            default_port(
                node=node_a,
                spec=spec_a,
                workspace_nodes=workspace.nodes,
                direction="in",
            ),
        )

        can_a_to_b = all(a_to_b)
        can_b_to_a = all(b_to_a)
        if can_a_to_b and (not can_b_to_a or node_a.x <= node_b.x):
            return self.add_edge(node_a_id, a_to_b[0], node_b_id, a_to_b[1])
        if can_b_to_a:
            return self.add_edge(node_b_id, b_to_a[0], node_a_id, b_to_a[1])
        raise ValueError("Selected nodes do not have compatible out/in ports.")

    def remove_edge(self, edge_id: str) -> None:
        if self._bridge._model is None:
            return
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None or edge_id not in workspace.edges:
            return
        edge = workspace.edges.get(edge_id)
        if edge is None:
            return
        if not is_node_in_scope(workspace, edge.source_node_id, self._bridge._scope_path):
            return
        if not is_node_in_scope(workspace, edge.target_node_id, self._bridge._scope_path):
            return
        history_before = self._capture_history_snapshot()
        self._bridge._model.remove_edge(self._bridge._workspace_id, edge_id)
        self._bridge._rebuild_models()
        self._record_history(ACTION_REMOVE_EDGE, history_before)

    def _remove_node(self, node_id: str, *, require_visible: bool) -> bool:
        if self._bridge._model is None:
            return False
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None or node_id not in workspace.nodes:
            return False
        if require_visible and not is_node_in_scope(workspace, node_id, self._bridge._scope_path):
            return False
        history_before = self._capture_history_snapshot()
        self._bridge._model.remove_node(self._bridge._workspace_id, node_id)
        self._bridge._set_selected_node_ids(
            [value for value in self._bridge._selected_node_ids if value != node_id],
            workspace=workspace,
        )
        self._bridge._rebuild_models()
        self._record_history(ACTION_REMOVE_NODE, history_before)
        return True

    def remove_node(self, node_id: str) -> None:
        self._remove_node(node_id, require_visible=True)

    def remove_workspace_node(self, node_id: str) -> bool:
        return self._remove_node(node_id, require_visible=False)

    def focus_node(self, node_id: str) -> QPointF | None:
        item = self._bridge.node_item(node_id)
        if item is None:
            return None
        selection_changed = self._bridge._set_selected_node_ids([node_id])
        if not selection_changed:
            self._bridge.node_selected.emit(node_id)
        return item.sceneBoundingRect().center()

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        if self._bridge._model is None:
            return
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return
        node = workspace.nodes.get(node_id)
        if node is None:
            return
        normalized_collapsed = bool(collapsed)
        if bool(node.collapsed) == normalized_collapsed:
            return
        history_before = self._capture_history_snapshot()
        self._bridge._model.set_node_collapsed(
            self._bridge._workspace_id,
            node_id,
            normalized_collapsed,
        )
        self._bridge._rebuild_models()
        self._record_history(ACTION_TOGGLE_COLLAPSED, history_before)

    def _notify_selected_node_context_updated(self, node_id: str) -> None:
        normalized_node_id = str(node_id or "").strip()
        if normalized_node_id and normalized_node_id in self._bridge._selected_node_lookup:
            self._bridge.node_selected.emit(normalized_node_id)

    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        if self._bridge._model is None or self._bridge._registry is None:
            return
        workspace = self._bridge._model.project.workspaces[self._bridge._workspace_id]
        node = workspace.nodes[node_id]
        spec = self._bridge._registry.get_spec(node.type_id)
        normalized = self._bridge._registry.normalize_property_value(node.type_id, key, value)
        current_value = node.properties.get(key, _MISSING)
        if current_value is not _MISSING and current_value == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._bridge._model.set_node_property(self._bridge._workspace_id, node_id, key, normalized)
        if key == "title":
            self._bridge._sync_surface_title(node, spec)
        self._bridge._rebuild_models()
        self._notify_selected_node_context_updated(node_id)
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool:
        if self._bridge._model is None or self._bridge._registry is None:
            return False
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return False
        node = workspace.nodes.get(node_id)
        if node is None:
            return False
        spec = self._bridge._registry.get_spec(node.type_id)
        normalized_updates: dict[str, Any] = {}
        for raw_key, raw_value in dict(values or {}).items():
            key = str(raw_key or "")
            if not key:
                continue
            try:
                normalized = self._bridge._registry.normalize_property_value(node.type_id, key, raw_value)
            except KeyError:
                continue
            current_value = node.properties.get(key, _MISSING)
            if current_value is not _MISSING and current_value == normalized:
                continue
            normalized_updates[key] = normalized
        if not normalized_updates:
            return False

        history_before = self._capture_history_snapshot()
        for key, normalized in normalized_updates.items():
            self._bridge._model.set_node_property(self._bridge._workspace_id, node_id, key, normalized)
        if "title" in normalized_updates:
            self._bridge._sync_surface_title(node, spec)
        self._bridge._rebuild_models()
        self._notify_selected_node_context_updated(node_id)
        self._record_history(ACTION_EDIT_PROPERTY, history_before)
        return True

    @staticmethod
    def normalize_node_visual_style(visual_style: Any) -> dict[str, Any]:
        return normalize_visual_style_payload(visual_style)

    def set_node_visual_style(self, node_id: str, visual_style: Any) -> None:
        if self._bridge._model is None:
            return
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return
        node = workspace.nodes.get(node_id)
        if node is None:
            return
        normalized = normalize_visual_style_payload(visual_style)
        if node.visual_style == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._bridge._model.set_node_visual_style(self._bridge._workspace_id, node_id, normalized)
        self._bridge._rebuild_models()
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def clear_node_visual_style(self, node_id: str) -> None:
        self.set_node_visual_style(node_id, {})

    def set_node_title(self, node_id: str, title: str) -> None:
        if self._bridge._model is None or self._bridge._registry is None:
            return
        node = self._node(node_id)
        if node is None:
            return
        spec = self._bridge._registry.get_spec(node.type_id)
        normalized = str(title).strip()
        if not normalized:
            return
        if node.title == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._bridge._model.set_node_title(self._bridge._workspace_id, node_id, normalized)
        if self._bridge._surface_title_sync_enabled(spec):
            node.properties["title"] = normalized
        self._bridge._rebuild_models()
        self._record_history(ACTION_RENAME_NODE, history_before)

    @staticmethod
    def normalize_edge_label(label: Any) -> str:
        return normalize_edge_label(label)

    def set_edge_label(self, edge_id: str, label: Any) -> None:
        if self._bridge._model is None:
            return
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return
        edge = workspace.edges.get(edge_id)
        if edge is None:
            return
        normalized = normalize_edge_label(label)
        if edge.label == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._bridge._model.set_edge_label(self._bridge._workspace_id, edge_id, normalized)
        self._bridge._rebuild_models()
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def clear_edge_label(self, edge_id: str) -> None:
        self.set_edge_label(edge_id, "")

    @staticmethod
    def normalize_edge_visual_style(visual_style: Any) -> dict[str, Any]:
        return normalize_visual_style_payload(visual_style)

    def set_edge_visual_style(self, edge_id: str, visual_style: Any) -> None:
        if self._bridge._model is None:
            return
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return
        edge = workspace.edges.get(edge_id)
        if edge is None:
            return
        normalized = normalize_visual_style_payload(visual_style)
        if edge.visual_style == normalized:
            return
        history_before = self._capture_history_snapshot()
        self._bridge._model.set_edge_visual_style(self._bridge._workspace_id, edge_id, normalized)
        self._bridge._rebuild_models()
        self._record_history(ACTION_EDIT_PROPERTY, history_before)

    def clear_edge_visual_style(self, edge_id: str) -> None:
        self.set_edge_visual_style(edge_id, {})

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> None:
        if self._bridge._model is None or self._bridge._registry is None:
            return
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return
        node = workspace.nodes.get(node_id)
        if node is None:
            return
        spec = self._bridge._registry.get_spec(node.type_id)
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
        self._bridge._model.set_exposed_port(self._bridge._workspace_id, node_id, key, normalized_exposed)
        if not normalized_exposed:
            affected_edges = [
                edge_id
                for edge_id, edge in workspace.edges.items()
                if (edge.source_node_id == node_id and edge.source_port_key == key)
                or (edge.target_node_id == node_id and edge.target_port_key == key)
            ]
            for edge_id in affected_edges:
                self._bridge._model.remove_edge(self._bridge._workspace_id, edge_id)
        self._bridge._rebuild_models()
        self._record_history(ACTION_TOGGLE_EXPOSED_PORT, history_before)

    def move_node(self, node_id: str, x: float, y: float) -> None:
        if self._bridge._model is None:
            return
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return
        if not is_node_in_scope(workspace, node_id, self._bridge._scope_path):
            return
        node = self._node(node_id)
        if node is None:
            return
        final_x = float(x)
        final_y = float(y)
        if float(node.x) == final_x and float(node.y) == final_y:
            return
        history_before = self._capture_history_snapshot()
        self._bridge._model.set_node_position(self._bridge._workspace_id, node_id, final_x, final_y)
        self._bridge._rebuild_models()
        self._record_history(ACTION_MOVE_NODE, history_before)

    def resize_node(self, node_id: str, width: float, height: float) -> None:
        node = self._node(node_id)
        if node is None:
            return
        self.set_node_geometry(node_id, float(node.x), float(node.y), width, height)

    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        if self._bridge._model is None:
            return
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return
        node = self._node(node_id)
        if node is None:
            return
        if not is_node_in_scope(workspace, node_id, self._bridge._scope_path):
            return
        spec = self._bridge._registry.get_spec(node.type_id) if self._bridge._registry is not None else None
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
        self._bridge._model.set_node_geometry(
            self._bridge._workspace_id,
            node_id,
            final_x,
            final_y,
            final_w,
            final_h,
        )
        self._bridge._rebuild_models()
        self._record_history(ACTION_RESIZE_NODE, history_before)

    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool:
        if self._bridge._model is None:
            return False
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return False

        unique_node_ids: list[str] = []
        seen_node_ids: set[str] = set()
        for value in node_ids:
            node_id = str(value).strip()
            if not node_id or node_id in seen_node_ids or node_id not in workspace.nodes:
                continue
            if not is_node_in_scope(workspace, node_id, self._bridge._scope_path):
                continue
            seen_node_ids.add(node_id)
            unique_node_ids.append(node_id)
        if not unique_node_ids:
            return False

        delta_x = float(dx)
        delta_y = float(dy)
        if abs(delta_x) < 0.01 and abs(delta_y) < 0.01:
            return False

        history_group = nullcontext()
        if self._bridge._history is not None:
            history_group = self._bridge._history.grouped_action(
                self._bridge._workspace_id,
                ACTION_MOVE_NODE,
                workspace,
            )

        moved_any = False
        with history_group:
            for node_id in unique_node_ids:
                node = workspace.nodes.get(node_id)
                if node is None:
                    continue
                final_x = float(node.x) + delta_x
                final_y = float(node.y) + delta_y
                if float(node.x) == final_x and float(node.y) == final_y:
                    continue
                self._bridge._model.set_node_position(self._bridge._workspace_id, node_id, final_x, final_y)
                moved_any = True

        if not moved_any:
            return False
        self._bridge._rebuild_models()
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
        if self._bridge._model is None or self._bridge._registry is None:
            return False
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return False
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if len(selected_node_ids) < 2:
            return False
        selection_bounds = self._bridge._scope_selection.bounds_for_node_ids(selected_node_ids)
        if selection_bounds is None:
            return False

        history_group = nullcontext()
        if self._bridge._history is not None:
            history_group = self._bridge._history.grouped_action(
                self._bridge._workspace_id,
                ACTION_ADD_NODE,
                workspace,
            )

        grouped = None
        with history_group:
            grouped = group_selection_into_subnode(
                model=self._bridge._model,
                registry=self._bridge._registry,
                workspace_id=self._bridge._workspace_id,
                selected_node_ids=selected_node_ids,
                scope_path=self._bridge._scope_path,
                shell_x=selection_bounds.x(),
                shell_y=selection_bounds.y(),
            )
        if grouped is None:
            return False

        self._bridge._set_selected_node_ids([grouped.shell_node_id], workspace=workspace)
        self._bridge._rebuild_models()
        return True

    def ungroup_selected_subnode(self) -> bool:
        if self._bridge._model is None:
            return False
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return False
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if len(selected_node_ids) != 1:
            return False
        shell_node_id = selected_node_ids[0]

        history_group = nullcontext()
        if self._bridge._history is not None:
            history_group = self._bridge._history.grouped_action(
                self._bridge._workspace_id,
                ACTION_REMOVE_NODE,
                workspace,
            )

        ungrouped = None
        with history_group:
            ungrouped = ungroup_subnode(
                model=self._bridge._model,
                workspace_id=self._bridge._workspace_id,
                shell_node_id=shell_node_id,
            )
        if ungrouped is None:
            return False

        self._bridge._set_selected_node_ids(list(ungrouped.moved_node_ids), workspace=workspace)
        self._bridge._rebuild_models()
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
        self._bridge._set_selected_node_ids(duplicated_node_ids)
        self._bridge._rebuild_models()
        return True

    def serialize_selected_subgraph_fragment(self) -> dict[str, Any] | None:
        if self._bridge._model is None:
            return None
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return None
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if not selected_node_ids:
            return None
        return self._build_subgraph_fragment_payload(workspace, selected_node_ids)

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

        self._bridge._set_selected_node_ids(pasted_node_ids)
        self._bridge._rebuild_models()
        return True

    def _node(self, node_id: str) -> NodeInstance | None:
        if self._bridge._model is None:
            return None
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return None
        return workspace.nodes.get(node_id)

    def _node_or_raise(self, node_id: str) -> NodeInstance:
        node = self._node(node_id)
        if node is None:
            raise KeyError(f"Unknown scene node: {node_id}")
        return node

    def _find_model_edge_id(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> str | None:
        if self._bridge._model is None:
            return None
        workspace = self._bridge._model.project.workspaces[self._bridge._workspace_id]
        for edge in workspace.edges.values():
            if (
                edge.source_node_id == source_node_id
                and edge.source_port_key == source_port
                and edge.target_node_id == target_node_id
                and edge.target_port_key == target_port
            ):
                return edge.edge_id
        return None

    def _selected_node_ids_in_workspace(self, workspace: WorkspaceData) -> list[str]:
        return self._bridge._scope_selection.selected_node_ids_in_workspace(workspace)

    def _selected_layout_metrics(self) -> tuple[WorkspaceData | None, list[LayoutNodeBounds]]:
        if self._bridge._model is None or self._bridge._registry is None:
            return None, []
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return None, []
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if not selected_node_ids:
            return workspace, []
        return workspace, collect_layout_node_bounds(
            workspace=workspace,
            node_ids=selected_node_ids,
            spec_lookup=self._bridge._registry.get_spec,
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
        if self._bridge._model is None or not updates:
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

        history_group = nullcontext()
        if self._bridge._history is not None:
            history_group = self._bridge._history.grouped_action(
                self._bridge._workspace_id,
                ACTION_MOVE_NODE,
                workspace,
            )

        with history_group:
            for node_id, (final_x, final_y) in final_positions.items():
                self._bridge._model.set_node_position(self._bridge._workspace_id, node_id, final_x, final_y)
        self._bridge._rebuild_models()
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
        if self._bridge._registry is None:
            return None
        bounds = graph_fragment_bounds(
            nodes_payload=nodes_payload,
            registry=self._bridge._registry,
            size_resolver=node_size,
        )
        if bounds is None:
            return None
        return QRectF(bounds.x, bounds.y, bounds.width, bounds.height)

    def _fragment_types_and_ports_are_valid(self, fragment_payload: dict[str, Any]) -> bool:
        if self._bridge._registry is None:
            return False
        return graph_fragment_payload_is_valid(
            fragment_payload=fragment_payload,
            registry=self._bridge._registry,
        )

    def _insert_fragment(
        self,
        fragment_payload: dict[str, Any],
        *,
        action_type: str,
        delta_x: float,
        delta_y: float,
    ) -> list[str]:
        if self._bridge._model is None:
            return []
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return []
        if not self._fragment_types_and_ports_are_valid(fragment_payload):
            return []

        history_group = nullcontext()
        if self._bridge._history is not None:
            history_group = self._bridge._history.grouped_action(
                self._bridge._workspace_id,
                action_type,
                workspace,
            )

        with history_group:
            return insert_graph_fragment(
                model=self._bridge._model,
                workspace_id=self._bridge._workspace_id,
                fragment_payload=fragment_payload,
                delta_x=delta_x,
                delta_y=delta_y,
            )

    def _capture_history_snapshot(self) -> WorkspaceSnapshot | None:
        if self._bridge._history is None or self._bridge._model is None or not self._bridge._workspace_id:
            return None
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return None
        return self._bridge._history.capture_workspace(workspace)

    def _record_history(self, action_type: str, before_snapshot: WorkspaceSnapshot | None) -> None:
        if (
            self._bridge._history is None
            or self._bridge._model is None
            or before_snapshot is None
            or not self._bridge._workspace_id
        ):
            return
        workspace = self._bridge._model.project.workspaces.get(self._bridge._workspace_id)
        if workspace is None:
            return
        self._bridge._history.record_action(
            self._bridge._workspace_id,
            action_type,
            before_snapshot,
            workspace,
        )


__all__ = ["GraphSceneMutationHistory"]
