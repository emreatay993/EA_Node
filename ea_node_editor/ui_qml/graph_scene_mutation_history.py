from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QRectF

import ea_node_editor.ui_qml.graph_scene_mutation.alignment_and_distribution_ops as _alignment_ops
import ea_node_editor.ui_qml.graph_scene_mutation.clipboard_and_fragment_ops as _clipboard_ops
import ea_node_editor.ui_qml.graph_scene_mutation.comment_backdrop_ops as _comment_backdrop_ops
import ea_node_editor.ui_qml.graph_scene_mutation.grouping_and_subnode_ops as _grouping_ops
import ea_node_editor.ui_qml.graph_scene_mutation.policy as _policy
import ea_node_editor.ui_qml.graph_scene_mutation.selection_and_scope_ops as _selection_ops
from ea_node_editor.graph.boundary_adapters import GraphBoundaryAdapters
from ea_node_editor.graph.hierarchy import root_node_ids_for_fragment, subtree_node_ids
from ea_node_editor.graph.model import NodeInstance, WorkspaceData
from ea_node_editor.graph.transforms import (
    LayoutNodeBounds,
    build_subtree_fragment_payload_data,
    collect_layout_node_bounds,
    expand_comment_backdrop_fragment_node_ids,
    fragment_node_from_payload,
    graph_fragment_bounds,
    graph_fragment_payload_is_valid,
    normalize_layout_position_updates,
    snap_coordinate,
)
from ea_node_editor.ui.shell.runtime_clipboard import build_graph_fragment_payload
from ea_node_editor.ui.shell.runtime_history import ACTION_DELETE_SELECTED, ACTION_MOVE_NODE

if TYPE_CHECKING:
    from ea_node_editor.graph.mutation_service import WorkspaceMutationService
    from ea_node_editor.nodes.types import NodeTypeSpec
    from ea_node_editor.ui.shell.runtime_history import WorkspaceSnapshot
    from ea_node_editor.ui_qml.graph_scene.context import _GraphSceneContext
    from ea_node_editor.ui_qml.graph_scene_scope_selection import GraphSceneScopeSelection


class GraphSceneMutationPolicy:
    def __init__(self, scene_context: _GraphSceneContext) -> None:
        self._scene_context = scene_context


class GraphSceneMutationHistory:
    def __init__(
        self,
        scene_context: _GraphSceneContext,
        scope_selection: GraphSceneScopeSelection,
        *,
        boundary_adapters: GraphBoundaryAdapters,
    ) -> None:
        self._scene_context = scene_context
        self._scope_selection = scope_selection
        self._boundary_adapters = boundary_adapters

    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        return _selection_ops.set_node_property(self, node_id, key, value)

    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool:
        return _alignment_ops.move_nodes_by_delta(self, node_ids, dx, dy)

    def delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:
        model = self._scene_context.model
        registry = self._scene_context.registry
        if model is None or registry is None:
            return False
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None:
            return False

        requested_edge_ids: list[str] = []
        seen_edge_ids: set[str] = set()
        for value in edge_ids:
            edge_id = str(value).strip()
            if not edge_id or edge_id in seen_edge_ids:
                continue
            seen_edge_ids.add(edge_id)
            requested_edge_ids.append(edge_id)

        removable_node_ids = self._removable_node_ids_for_fragment(workspace)
        if not requested_edge_ids and not removable_node_ids:
            return False

        mutations = self._mutation_boundary()
        removed_any = False
        history_group = self._scene_context.grouped_history_action(ACTION_DELETE_SELECTED, workspace)
        with history_group:
            for edge_id in requested_edge_ids:
                if edge_id not in workspace.edges:
                    continue
                mutations.remove_edge(edge_id)
                removed_any = True
            for node_id in reversed(removable_node_ids):
                if node_id not in workspace.nodes:
                    continue
                mutations.remove_node(node_id)
                removed_any = True
        if not removed_any:
            return False

        remaining_selected = [node_id for node_id in self._scene_context.selected_node_ids if node_id in workspace.nodes]
        self._scope_selection.set_selected_node_ids(remaining_selected, workspace=workspace)
        self._scene_context.rebuild_models()
        return True

    def notify_selected_node_context_updated(self, node_id: str) -> None:
        normalized_node_id = str(node_id or "").strip()
        if normalized_node_id and normalized_node_id in self._scene_context.selected_node_lookup:
            self._scene_context.emit_node_selected(normalized_node_id)

    @staticmethod
    def _normalize_title_value(title: Any) -> str:
        return str(title).strip()

    def _normalized_title_update(self, node: NodeInstance, title: Any) -> str | None:
        normalized = self._normalize_title_value(title)
        return None if not normalized or node.title == normalized else normalized

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

    def _node(self, node_id: str) -> NodeInstance | None:
        return self._scene_context.node(node_id)

    def _node_or_raise(self, node_id: str) -> NodeInstance:
        return self._scene_context.node_or_raise(node_id)

    def _mutation_boundary(self) -> WorkspaceMutationService:
        model, registry = self._scene_context.require_bound()
        return model.mutation_service(
            self._scene_context.workspace_id,
            registry=registry,
            boundary_adapters=self._boundary_adapters,
        )

    def _authoring_transactions(self) -> WorkspaceMutationService | None:
        model = self._scene_context.model
        if model is None:
            return None
        return model.mutation_service(
            self._scene_context.workspace_id,
            registry=self._scene_context.registry,
            boundary_adapters=self._boundary_adapters,
        )

    def _find_model_edge_id(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str | None:
        return self._scene_context.find_model_edge_id(source_node_id, source_port, target_node_id, target_port)

    def _selected_node_ids_in_workspace(self, workspace: WorkspaceData) -> list[str]:
        return self._scope_selection.selected_node_ids_in_workspace(workspace)

    def _expanded_selected_node_ids_for_fragment(self, workspace: WorkspaceData) -> list[str]:
        selected_node_ids = self._selected_node_ids_in_workspace(workspace)
        if not selected_node_ids:
            return []
        return expand_comment_backdrop_fragment_node_ids(
            workspace=workspace,
            selected_node_ids=selected_node_ids,
            backdrop_payloads=self._scene_context.backdrop_nodes_payload,
        )

    def _removable_node_ids_for_fragment(self, workspace: WorkspaceData) -> list[str]:
        selected_node_ids = self._expanded_selected_node_ids_for_fragment(workspace)
        if not selected_node_ids:
            return []
        return subtree_node_ids(workspace, root_node_ids_for_fragment(workspace, selected_node_ids))

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
            size_resolver=partial(
                self._boundary_adapters.node_size,
                show_port_labels=self._scene_context.graphics_show_port_labels,
            ),
        )

    @staticmethod
    def _snap_coordinate(value: float, grid_size: float) -> float:
        return snap_coordinate(value, grid_size, default_step=_alignment_ops.SNAP_GRID_SIZE)

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
            default_grid_size=_alignment_ops.SNAP_GRID_SIZE,
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
    def _build_subgraph_fragment_payload(workspace: WorkspaceData, node_ids: list[str]) -> dict[str, Any] | None:
        fragment_data = build_subtree_fragment_payload_data(workspace=workspace, selected_node_ids=node_ids)
        if fragment_data is None:
            return None
        return build_graph_fragment_payload(nodes=fragment_data["nodes"], edges=fragment_data["edges"])

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
            size_resolver=partial(
                self._boundary_adapters.node_size,
                show_port_labels=self._scene_context.graphics_show_port_labels,
            ),
        )
        return None if bounds is None else QRectF(bounds.x, bounds.y, bounds.width, bounds.height)

    def _fragment_types_and_ports_are_valid(self, fragment_payload: dict[str, Any]) -> bool:
        registry = self._scene_context.registry
        if registry is None:
            return False
        return graph_fragment_payload_is_valid(fragment_payload=fragment_payload, registry=registry)

    def _insert_fragment(self, fragment_payload: dict[str, Any], *, action_type: str, delta_x: float, delta_y: float) -> list[str]:
        model = self._scene_context.model
        if model is None:
            return []
        workspace = model.project.workspaces.get(self._scene_context.workspace_id)
        if workspace is None or not self._fragment_types_and_ports_are_valid(fragment_payload):
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


GraphSceneMutationPolicy.are_ports_compatible = _policy.are_ports_compatible
GraphSceneMutationPolicy.are_port_kinds_compatible = staticmethod(_policy.are_port_kinds_compatible)
GraphSceneMutationPolicy.are_data_types_compatible = staticmethod(_policy.are_data_types_compatible)

GraphSceneMutationHistory.add_node_from_type = _selection_ops.add_node_from_type
GraphSceneMutationHistory.add_subnode_shell_pin = _grouping_ops.add_subnode_shell_pin
GraphSceneMutationHistory.create_node_from_type = _selection_ops.create_node_from_type
GraphSceneMutationHistory.add_edge = _selection_ops.add_edge
GraphSceneMutationHistory.connect_nodes = _selection_ops.connect_nodes
GraphSceneMutationHistory.remove_edge = _selection_ops.remove_edge
GraphSceneMutationHistory.remove_node_with_policy = _selection_ops.remove_node_with_policy
GraphSceneMutationHistory.remove_node = _selection_ops.remove_node
GraphSceneMutationHistory.remove_workspace_node = _selection_ops.remove_workspace_node
GraphSceneMutationHistory.focus_node = _selection_ops.focus_node
GraphSceneMutationHistory.set_node_collapsed = _selection_ops.set_node_collapsed
GraphSceneMutationHistory.set_node_properties = _selection_ops.set_node_properties
GraphSceneMutationHistory.normalize_node_visual_style = staticmethod(_selection_ops.normalize_node_visual_style)
GraphSceneMutationHistory.set_node_visual_style = _selection_ops.set_node_visual_style
GraphSceneMutationHistory.clear_node_visual_style = _selection_ops.clear_node_visual_style
GraphSceneMutationHistory.set_node_title = _selection_ops.set_node_title
GraphSceneMutationHistory.normalize_edge_label = staticmethod(_selection_ops.normalize_edge_label)
GraphSceneMutationHistory.set_edge_label = _selection_ops.set_edge_label
GraphSceneMutationHistory.clear_edge_label = _selection_ops.clear_edge_label
GraphSceneMutationHistory.normalize_edge_visual_style = staticmethod(_selection_ops.normalize_edge_visual_style)
GraphSceneMutationHistory.set_edge_visual_style = _selection_ops.set_edge_visual_style
GraphSceneMutationHistory.clear_edge_visual_style = _selection_ops.clear_edge_visual_style
GraphSceneMutationHistory.set_exposed_port = _selection_ops.set_exposed_port
GraphSceneMutationHistory.set_node_port_label = _selection_ops.set_node_port_label
GraphSceneMutationHistory.move_node = _alignment_ops.move_node
GraphSceneMutationHistory.resize_node = _alignment_ops.resize_node
GraphSceneMutationHistory.set_node_geometry = _alignment_ops.set_node_geometry
GraphSceneMutationHistory.align_selected_nodes = _alignment_ops.align_selected_nodes
GraphSceneMutationHistory.distribute_selected_nodes = _alignment_ops.distribute_selected_nodes
GraphSceneMutationHistory.wrap_nodes_in_comment_backdrop = _comment_backdrop_ops.wrap_nodes_in_comment_backdrop
GraphSceneMutationHistory.wrap_selected_nodes_in_comment_backdrop = _comment_backdrop_ops.wrap_selected_nodes_in_comment_backdrop
GraphSceneMutationHistory.group_selected_nodes = _grouping_ops.group_selected_nodes
GraphSceneMutationHistory.ungroup_selected_subnode = _grouping_ops.ungroup_selected_subnode
GraphSceneMutationHistory.duplicate_selected_subgraph = _clipboard_ops.duplicate_selected_subgraph
GraphSceneMutationHistory.serialize_selected_subgraph_fragment = _clipboard_ops.serialize_selected_subgraph_fragment
GraphSceneMutationHistory.fragment_bounds_center = _clipboard_ops.fragment_bounds_center
GraphSceneMutationHistory.paste_subgraph_fragment = _clipboard_ops.paste_subgraph_fragment

__all__ = ["GraphSceneMutationHistory", "GraphSceneMutationPolicy"]
