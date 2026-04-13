from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, QPointF, QRectF, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.graph.hierarchy import ScopePath, scope_breadcrumb_payload
from ea_node_editor.graph.model import GraphModel, WorkspaceData
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.ui_qml.graph_scene.command_bridge import GraphSceneCommandBridge
from ea_node_editor.ui_qml.graph_scene.context import _GraphSceneContext
from ea_node_editor.ui_qml.graph_scene.policy_bridge import GraphScenePolicyBridge
from ea_node_editor.ui_qml.graph_scene.read_bridge import GraphSceneReadBridge

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
    from ea_node_editor.ui_qml.graph_scene_scope_selection import _NodeItemProxy, _SelectedNodeProxy
    from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge

_SNAP_GRID_SIZE = 20.0


@dataclass
class _GraphScenePayloadCache:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    backdrop_nodes: list[dict[str, Any]] = field(default_factory=list)
    minimap_nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    active_view_id: str = ""
    hide_locked_ports: bool = False
    hide_optional_ports: bool = False
    comment_peek_node_id: str = ""

    def update(
        self,
        *,
        nodes: list[dict[str, Any]],
        backdrop_nodes: list[dict[str, Any]],
        minimap_nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        active_view_id: str | None = None,
        hide_locked_ports: bool | None = None,
        hide_optional_ports: bool | None = None,
        comment_peek_node_id: str | None = None,
    ) -> None:
        self.nodes = nodes
        self.backdrop_nodes = backdrop_nodes
        self.minimap_nodes = minimap_nodes
        self.edges = edges
        if active_view_id is not None:
            self.active_view_id = str(active_view_id or "")
        if hide_locked_ports is not None:
            self.hide_locked_ports = bool(hide_locked_ports)
        if hide_optional_ports is not None:
            self.hide_optional_ports = bool(hide_optional_ports)
        if comment_peek_node_id is not None:
            self.comment_peek_node_id = str(comment_peek_node_id or "")

    def set_active_view_filters(
        self,
        *,
        active_view_id: str,
        hide_locked_ports: bool,
        hide_optional_ports: bool,
    ) -> None:
        self.active_view_id = str(active_view_id or "")
        self.hide_locked_ports = bool(hide_locked_ports)
        self.hide_optional_ports = bool(hide_optional_ports)


class _GraphScenePendingSurfaceAction:
    def __init__(self) -> None:
        self.node_id = ""

    def set(self, node_id: str) -> bool:
        normalized = str(node_id or "")
        if self.node_id == normalized:
            return False
        self.node_id = normalized
        return True

    def consume(self, node_id: str) -> bool:
        normalized = str(node_id or "")
        if not normalized or self.node_id != normalized:
            return False
        self.node_id = ""
        return True


class GraphSceneBridgeBase(QObject):
    node_selected = pyqtSignal(str)
    workspace_changed = pyqtSignal(str)
    scope_changed = pyqtSignal()
    nodes_changed = pyqtSignal()
    edges_changed = pyqtSignal()
    selection_changed = pyqtSignal()
    pending_surface_action_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._graphics_preference_signal_source: object | None = None
        self._bind_graphics_preference_signal_source()

    def _graphics_preference_source(self) -> object | None:
        host = self.parent()
        if host is None:
            return None
        presenter = getattr(host, "graph_canvas_presenter", None)
        return presenter if presenter is not None else host

    def _bind_graphics_preference_signal_source(self) -> None:
        source = self._graphics_preference_source()
        if self._graphics_preference_signal_source is source:
            return
        if self._graphics_preference_signal_source is not None:
            try:
                self._graphics_preference_signal_source.graphics_preferences_changed.disconnect(
                    self._on_graphics_preferences_changed
                )
            except (AttributeError, RuntimeError, TypeError):
                pass
        self._graphics_preference_signal_source = source
        if self._graphics_preference_signal_source is not None:
            try:
                self._graphics_preference_signal_source.graphics_preferences_changed.connect(
                    self._on_graphics_preferences_changed
                )
            except AttributeError:
                self._graphics_preference_signal_source = None

    def _active_view_filter_state(self) -> tuple[str, bool, bool]:
        workspace = self._workspace_or_none()
        if workspace is None:
            return "", False, False
        active_view = workspace.views.get(workspace.active_view_id)
        if active_view is None:
            active_view = next(iter(workspace.views.values()), None)
        if active_view is None:
            return "", False, False
        return (
            str(active_view.view_id),
            bool(active_view.hide_locked_ports),
            bool(active_view.hide_optional_ports),
        )

    def _ensure_payload_cache_current(self) -> None:
        active_view_id, hide_locked_ports, hide_optional_ports = self._active_view_filter_state()
        comment_peek_node_id = self._scope_selection.validated_comment_peek_node_id()
        if (
            self._payload_cache.active_view_id == active_view_id
            and self._payload_cache.hide_locked_ports == hide_locked_ports
            and self._payload_cache.hide_optional_ports == hide_optional_ports
            and self._payload_cache.comment_peek_node_id == comment_peek_node_id
        ):
            return
        (
            nodes_payload,
            backdrop_nodes_payload,
            minimap_nodes_payload,
            edges_payload,
        ) = self._scene_context._payload_builder.rebuild_partitioned_models(
            model=self._scene_context.model,
            registry=self._scene_context.registry,
            workspace_id=self._scene_context.workspace_id,
            scope_path=self._scene_context.scope_path,
            comment_peek_node_id=comment_peek_node_id,
            graph_theme_bridge=self._scene_context.graph_theme_bridge,
            show_port_labels=self._scene_context.graphics_show_port_labels,
        )
        self._payload_cache.update(
            nodes=nodes_payload,
            backdrop_nodes=backdrop_nodes_payload,
            minimap_nodes=minimap_nodes_payload,
            edges=edges_payload,
            active_view_id=active_view_id,
            hide_locked_ports=hide_locked_ports,
            hide_optional_ports=hide_optional_ports,
            comment_peek_node_id=comment_peek_node_id,
        )

    @property
    def graphics_show_port_labels(self) -> bool:
        source = self._graphics_preference_source()
        if source is None:
            return True
        return bool(getattr(source, "graphics_show_port_labels", True))

    @property
    def _workspace_id(self) -> str:
        return self._scope_selection.workspace_id

    @_workspace_id.setter
    def _workspace_id(self, value: str) -> None:
        self._scope_selection.workspace_id = str(value or "")

    @property
    def _scope_path(self) -> ScopePath:
        return self._scope_selection.scope_path

    @_scope_path.setter
    def _scope_path(self, value: ScopePath) -> None:
        self._scope_selection.scope_path = tuple(str(node_id) for node_id in tuple(value or ()))

    @property
    def _selected_node_ids(self) -> list[str]:
        return self._scope_selection.selected_node_ids

    @_selected_node_ids.setter
    def _selected_node_ids(self, value: list[str]) -> None:
        self._scope_selection.selected_node_ids = [str(node_id) for node_id in list(value or [])]

    @property
    def _selected_node_lookup(self) -> dict[str, bool]:
        return self._scope_selection.selected_node_lookup

    @_selected_node_lookup.setter
    def _selected_node_lookup(self, value: dict[str, bool]) -> None:
        self._scope_selection.selected_node_lookup = {
            str(node_id): bool(selected) for node_id, selected in dict(value or {}).items()
        }

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @property
    def state_bridge(self) -> GraphSceneReadBridge:
        return self._state_bridge

    @property
    def command_bridge(self) -> GraphSceneCommandBridge:
        return self._command_bridge

    @property
    def policy_bridge(self) -> GraphScenePolicyBridge:
        return self._policy_bridge

    @pyqtProperty("QVariantList", notify=nodes_changed)
    def nodes_model(self) -> list[dict[str, Any]]:
        self._ensure_payload_cache_current()
        return self._payload_cache.nodes

    @pyqtProperty("QVariantList", notify=nodes_changed)
    def backdrop_nodes_model(self) -> list[dict[str, Any]]:
        self._ensure_payload_cache_current()
        return self._payload_cache.backdrop_nodes

    @pyqtProperty("QVariantList", notify=edges_changed)
    def edges_model(self) -> list[dict[str, Any]]:
        self._ensure_payload_cache_current()
        return self._payload_cache.edges

    @pyqtProperty(str, notify=pending_surface_action_changed)
    def pending_surface_action_node_id(self) -> str:
        return self._command_bridge.pending_surface_action_node_id

    @pyqtSlot(str)
    def set_pending_surface_action(self, node_id: str) -> None:
        self._command_bridge.set_pending_surface_action(node_id)

    @pyqtSlot(str, result=bool)
    def consume_pending_surface_action(self, node_id: str) -> bool:
        return self._command_bridge.consume_pending_surface_action(node_id)

    @pyqtProperty("QVariantList", notify=nodes_changed)
    def minimap_nodes_model(self) -> list[dict[str, Any]]:
        self._ensure_payload_cache_current()
        return self._payload_cache.minimap_nodes

    @pyqtProperty("QVariantMap", notify=nodes_changed)
    def workspace_scene_bounds_payload(self) -> dict[str, float]:
        return self._rect_payload(self.workspace_scene_bounds_with_fallback())

    @pyqtProperty(str, notify=node_selected)
    def selected_node_id_value(self) -> str:
        selected = self.selected_node_id()
        return selected or ""

    @pyqtProperty("QVariantMap", notify=selection_changed)
    def selected_node_lookup(self) -> dict[str, bool]:
        return self._selected_node_lookup

    @pyqtProperty("QVariantList", notify=scope_changed)
    def active_scope_path(self) -> list[str]:
        return list(self._scope_path)

    @pyqtProperty("QVariantList", notify=scope_changed)
    def scope_breadcrumb_model(self) -> list[dict[str, str]]:
        workspace = self._workspace_or_none()
        if workspace is None:
            return []
        return scope_breadcrumb_payload(workspace, self._scope_path)

    @pyqtProperty(bool, notify=scope_changed)
    def can_navigate_scope_parent(self) -> bool:
        return bool(self._scope_path)

    @pyqtProperty(str, notify=nodes_changed)
    def active_comment_peek_node_id(self) -> str:
        return self._scope_selection.validated_comment_peek_node_id()

    @pyqtProperty(bool, notify=nodes_changed)
    def comment_peek_active(self) -> bool:
        return bool(self.active_comment_peek_node_id)

    def _workspace_or_none(self) -> WorkspaceData | None:
        return self._scene_context.workspace_or_none()

    @pyqtSlot(result=bool)
    def sync_scope_with_active_view(self) -> bool:
        return self._scope_selection.sync_scope_with_active_view()

    @pyqtSlot(str, result=bool)
    def open_subnode_scope(self, node_id: str) -> bool:
        return self._scope_selection.open_subnode_scope(node_id)

    @pyqtSlot(str, result=bool)
    def can_open_comment_peek(self, node_id: str) -> bool:
        return self._scope_selection.can_open_comment_peek(node_id)

    @pyqtSlot(str, result=bool)
    def open_comment_peek(self, node_id: str) -> bool:
        return self._scope_selection.open_comment_peek(node_id)

    @pyqtSlot(result=bool)
    def close_comment_peek(self) -> bool:
        return self._scope_selection.close_comment_peek()

    @pyqtSlot(str, result=bool)
    def open_scope_for_node(self, node_id: str) -> bool:
        return self._scope_selection.open_scope_for_node(node_id)

    @pyqtSlot(result=bool)
    def navigate_scope_parent(self) -> bool:
        return self._scope_selection.navigate_scope_parent()

    @pyqtSlot(result=bool)
    def navigate_scope_root(self) -> bool:
        return self._scope_selection.navigate_scope_root()

    @pyqtSlot(str, result=bool)
    def navigate_scope_to(self, node_id: str) -> bool:
        return self._scope_selection.navigate_scope_to(node_id)

    def bind_runtime_history(self, history: RuntimeGraphHistory | None) -> None:
        self._history = history

    def bind_graph_theme_bridge(self, graph_theme_bridge: GraphThemeBridge | None) -> None:
        self._bind_graphics_preference_signal_source()
        if self._graph_theme_bridge is graph_theme_bridge:
            return
        if self._graph_theme_bridge is not None:
            try:
                self._graph_theme_bridge.changed.disconnect(self._on_graph_theme_changed)
            except (RuntimeError, TypeError):
                pass
        self._graph_theme_bridge = graph_theme_bridge
        if self._graph_theme_bridge is not None:
            self._graph_theme_bridge.changed.connect(self._on_graph_theme_changed)
        self._scene_context.rebuild_models()

    def _on_graph_theme_changed(self) -> None:
        self._scene_context.rebuild_models()

    def _on_graphics_preferences_changed(self) -> None:
        self._scene_context.rebuild_models()

    def set_workspace(self, model: GraphModel, registry: NodeRegistry, workspace_id: str) -> None:
        self._model = model
        self._registry = registry
        self._scope_selection.set_workspace(workspace_id)

    def current_workspace(self) -> WorkspaceData:
        return self._scene_context.current_workspace()

    def refresh_workspace_from_model(self, workspace_id: str) -> None:
        self._scope_selection.refresh_workspace_from_model(workspace_id)

    def selected_node_id(self) -> str | None:
        return self._scope_selection.selected_node_id()

    def selectedItems(self) -> list[_SelectedNodeProxy]:
        return self._scope_selection.selected_items()

    def workspace_scene_bounds(self) -> QRectF | None:
        return self._scope_selection.workspace_scene_bounds()

    def workspace_scene_bounds_with_fallback(self) -> QRectF:
        return self._scope_selection.workspace_scene_bounds_with_fallback()

    def _rect_payload(self, rect: QRectF) -> dict[str, float]:
        return self._scope_selection.rect_payload(rect)

    @pyqtSlot(result="QVariantMap")
    def workspace_scene_bounds_map(self) -> dict[str, float]:
        return self._scope_selection.workspace_scene_bounds_map()

    def selection_bounds(self) -> QRectF | None:
        return self._scope_selection.selection_bounds()

    def clearSelection(self) -> None:
        self._command_bridge.clearSelection()

    @pyqtSlot()
    def clear_selection(self) -> None:
        self._command_bridge.clear_selection()

    @pyqtSlot(str)
    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        self._command_bridge.select_node(node_id, additive=additive)

    @pyqtSlot(float, float, float, float)
    @pyqtSlot(float, float, float, float, bool)
    def select_nodes_in_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        additive: bool = False,
    ) -> None:
        self._command_bridge.select_nodes_in_rect(x1, y1, x2, y2, additive)

    def node_item(self, node_id: str) -> _NodeItemProxy | None:
        return self._scope_selection.node_item(node_id)

    def node_bounds(self, node_id: str) -> QRectF | None:
        return self._scope_selection.node_bounds(node_id)

    def edge_item(self, edge_id: str) -> dict[str, Any] | None:
        return self._scene_context.edge_item(edge_id)

    @pyqtSlot(str, float, float, result=str)
    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        return self._command_bridge.add_node_from_type(type_id, x, y)

    def add_subnode_shell_pin(self, shell_node_id: str, pin_type_id: str) -> str:
        return self._command_bridge.add_subnode_shell_pin(shell_node_id, pin_type_id)

    @pyqtSlot(str, str, str, str, result=bool)
    def are_ports_compatible(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> bool:
        return self._policy_bridge.are_ports_compatible(
            source_node_id,
            source_port,
            target_node_id,
            target_port,
        )

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return self._policy_bridge.are_port_kinds_compatible(source_kind, target_kind)

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return self._policy_bridge.are_data_types_compatible(source_type, target_type)

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
        return self._command_bridge.add_edge(source_node_id, source_port, target_node_id, target_port)

    @pyqtSlot(str, str, result=str)
    def connect_nodes(self, node_a_id: str, node_b_id: str) -> str:
        return self._command_bridge.connect_nodes(node_a_id, node_b_id)

    def remove_edge(self, edge_id: str) -> None:
        self._command_bridge.remove_edge(edge_id)

    def _remove_node(self, node_id: str, *, require_visible: bool) -> bool:
        return self._authoring_boundary.remove_node_with_policy(node_id, require_visible=require_visible)

    def remove_node(self, node_id: str) -> None:
        self._command_bridge.remove_node(node_id)

    def remove_workspace_node(self, node_id: str) -> bool:
        return self._command_bridge.remove_workspace_node(node_id)

    @pyqtSlot(str)
    def focus_node_slot(self, node_id: str) -> None:
        self._command_bridge.focus_node_slot(node_id)

    def focus_node(self, node_id: str) -> QPointF | None:
        return self._command_bridge.focus_node(node_id)

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        self._command_bridge.set_node_collapsed(node_id, collapsed)

    @pyqtSlot(str, str, str)
    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None:
        self._command_bridge.set_node_port_label(node_id, port_key, label)

    @pyqtSlot(str, str, "QVariant")
    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        self._command_bridge.set_node_property(node_id, key, value)

    @pyqtSlot(str, "QVariantMap", result=bool)
    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool:
        return self._command_bridge.set_node_properties(node_id, values)

    @pyqtSlot("QVariant", result="QVariantMap")
    def normalize_node_visual_style(self, visual_style: Any) -> dict[str, Any]:
        return self._command_bridge.normalize_node_visual_style(visual_style)

    @pyqtSlot(str, "QVariant")
    def set_node_visual_style(self, node_id: str, visual_style: Any) -> None:
        self._command_bridge.set_node_visual_style(node_id, visual_style)

    @pyqtSlot(str)
    def clear_node_visual_style(self, node_id: str) -> None:
        self._command_bridge.clear_node_visual_style(node_id)

    def set_node_title(self, node_id: str, title: str) -> None:
        self._command_bridge.set_node_title(node_id, title)

    @pyqtSlot("QVariant", result=str)
    def normalize_edge_label(self, label: Any) -> str:
        return self._command_bridge.normalize_edge_label(label)

    @pyqtSlot(str, "QVariant")
    def set_edge_label(self, edge_id: str, label: Any) -> None:
        self._command_bridge.set_edge_label(edge_id, label)

    @pyqtSlot(str)
    def clear_edge_label(self, edge_id: str) -> None:
        self._command_bridge.clear_edge_label(edge_id)

    @pyqtSlot("QVariant", result="QVariantMap")
    def normalize_edge_visual_style(self, visual_style: Any) -> dict[str, Any]:
        return self._command_bridge.normalize_edge_visual_style(visual_style)

    @pyqtSlot(str, "QVariant")
    def set_edge_visual_style(self, edge_id: str, visual_style: Any) -> None:
        self._command_bridge.set_edge_visual_style(edge_id, visual_style)

    @pyqtSlot(str)
    def clear_edge_visual_style(self, edge_id: str) -> None:
        self._command_bridge.clear_edge_visual_style(edge_id)

    @pyqtSlot(str, str, bool, result=bool)
    def set_port_locked(self, node_id: str, key: str, locked: bool) -> bool:
        return self._command_bridge.set_port_locked(node_id, key, locked)

    @pyqtSlot(bool, result=bool)
    def set_hide_locked_ports(self, hide_locked_ports: bool) -> bool:
        return self._command_bridge.set_hide_locked_ports(hide_locked_ports)

    @pyqtSlot(bool, result=bool)
    def set_hide_optional_ports(self, hide_optional_ports: bool) -> bool:
        return self._command_bridge.set_hide_optional_ports(hide_optional_ports)

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> None:
        self._command_bridge.set_exposed_port(node_id, key, exposed)

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        self._command_bridge.move_node(node_id, x, y)

    @pyqtSlot(str, float, float)
    def resize_node(self, node_id: str, width: float, height: float) -> None:
        self._command_bridge.resize_node(node_id, width, height)

    @pyqtSlot(str, float, float, float, float)
    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        self._command_bridge.set_node_geometry(node_id, x, y, width, height)

    @pyqtSlot("QVariantList", float, float, result=bool)
    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool:
        return self._command_bridge.move_nodes_by_delta(node_ids, dx, dy)

    def align_selected_nodes(self, alignment: str, *, snap_to_grid: bool = False, grid_size: float = _SNAP_GRID_SIZE) -> bool:
        return self._command_bridge.align_selected_nodes(
            alignment,
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
        return self._command_bridge.distribute_selected_nodes(
            orientation,
            snap_to_grid=snap_to_grid,
            grid_size=grid_size,
        )

    @pyqtSlot("QVariantList", result=str)
    def wrap_node_ids_in_comment_backdrop(self, node_ids: list[Any]) -> str:
        return self._command_bridge.wrap_node_ids_in_comment_backdrop(node_ids)

    @pyqtSlot(result=bool)
    def wrap_selected_nodes_in_comment_backdrop(self) -> bool:
        return self._command_bridge.wrap_selected_nodes_in_comment_backdrop()

    @pyqtSlot(result=bool)
    def group_selected_nodes(self) -> bool:
        return self._command_bridge.group_selected_nodes()

    @pyqtSlot(result=bool)
    def ungroup_selected_subnode(self) -> bool:
        return self._command_bridge.ungroup_selected_subnode()

    @pyqtSlot(result=bool)
    def duplicate_selected_subgraph(self) -> bool:
        return self._command_bridge.duplicate_selected_subgraph()

    def serialize_selected_subgraph_fragment(self) -> dict[str, Any] | None:
        return self._command_bridge.serialize_selected_subgraph_fragment()

    def fragment_bounds_center(self, fragment_payload: Any) -> tuple[float, float] | None:
        return self._command_bridge.fragment_bounds_center(fragment_payload)

    def paste_subgraph_fragment(self, fragment_payload: Any, center_x: float, center_y: float) -> bool:
        return self._command_bridge.paste_subgraph_fragment(fragment_payload, center_x, center_y)

    def delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:
        return self._command_bridge.delete_selected_graph_items(edge_ids)


__all__ = [
    "GraphSceneBridgeBase",
    "_GraphScenePayloadCache",
    "_GraphScenePendingSurfaceAction",
]
