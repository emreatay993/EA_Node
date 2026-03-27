from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, QPointF, QRectF, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.graph.hierarchy import (
    ScopePath,
    scope_breadcrumb_payload,
)
from ea_node_editor.graph.boundary_adapters import set_graph_boundary_adapters
from ea_node_editor.graph.model import GraphModel, NodeInstance, WorkspaceData
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.graph_theme import GraphThemeDefinition
from ea_node_editor.ui.pdf_preview_provider import clamp_pdf_page_number
from ea_node_editor.ui_qml.edge_routing import node_size
from ea_node_editor.ui_qml.graph_scene_mutation_history import GraphSceneMutationHistory
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from ea_node_editor.ui_qml.graph_scene_scope_selection import (
    GraphSceneScopeSelection,
    _NodeItemProxy,
    _SelectedNodeProxy,
)

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory, WorkspaceSnapshot
    from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge

_SNAP_GRID_SIZE = 20.0


def _surface_title_sync_enabled(spec: NodeTypeSpec) -> bool:
    family = str(spec.surface_family or "").strip()
    return family in {"flowchart", "planning", "annotation"} and any(
        prop.key == "title" for prop in spec.properties
    )


def _synced_surface_title(node: NodeInstance, spec: NodeTypeSpec) -> str:
    if not _surface_title_sync_enabled(spec):
        return str(node.title).strip() or str(spec.display_name).strip()
    title = str(node.properties.get("title", "")).strip()
    return title or str(spec.display_name).strip()


def _sync_surface_title(node: NodeInstance, spec: NodeTypeSpec) -> None:
    if not _surface_title_sync_enabled(spec):
        return
    node.title = _synced_surface_title(node, spec)


class _GraphSceneContext:
    def __init__(self, bridge: GraphSceneBridge, payload_builder: GraphScenePayloadBuilder) -> None:
        self._bridge = bridge
        self._payload_builder = payload_builder
        self.workspace_id = ""
        self.scope_path: ScopePath = ()
        self.selected_node_ids: list[str] = []
        self.selected_node_lookup: dict[str, bool] = {}

    @property
    def model(self) -> GraphModel | None:
        return self._bridge._model

    @property
    def registry(self) -> NodeRegistry | None:
        return self._bridge._registry

    @property
    def history(self) -> RuntimeGraphHistory | None:
        return self._bridge._history

    @property
    def graph_theme_bridge(self) -> GraphThemeBridge | None:
        return self._bridge._graph_theme_bridge

    @property
    def graphics_show_port_labels(self) -> bool:
        return self._bridge.graphics_show_port_labels

    @property
    def backdrop_nodes_payload(self) -> list[dict[str, Any]]:
        return self._bridge._backdrop_nodes_payload

    def require_bound(self) -> tuple[GraphModel, NodeRegistry]:
        if self.model is None or self.registry is None:
            raise RuntimeError("Scene is not bound")
        return self.model, self.registry

    def workspace_or_none(self) -> WorkspaceData | None:
        if self.model is None or not self.workspace_id:
            return None
        return self.model.project.workspaces.get(self.workspace_id)

    def current_workspace(self) -> WorkspaceData:
        if self.model is None:
            raise RuntimeError("Scene has no graph model")
        return self.model.project.workspaces[self.workspace_id]

    def node(self, node_id: str) -> NodeInstance | None:
        workspace = self.workspace_or_none()
        if workspace is None:
            return None
        return workspace.nodes.get(node_id)

    def node_or_raise(self, node_id: str) -> NodeInstance:
        node = self.node(node_id)
        if node is None:
            raise KeyError(f"Unknown scene node: {node_id}")
        return node

    def find_model_edge_id(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> str | None:
        workspace = self.workspace_or_none()
        if workspace is None:
            return None
        for edge in workspace.edges.values():
            if (
                edge.source_node_id == source_node_id
                and edge.source_port_key == source_port
                and edge.target_node_id == target_node_id
                and edge.target_port_key == target_port
            ):
                return edge.edge_id
        return None

    def edge_item(self, edge_id: str) -> dict[str, Any] | None:
        workspace = self.workspace_or_none()
        if workspace is None:
            return None
        return self._payload_builder.edge_item(
            workspace=workspace,
            scope_path=self.scope_path,
            edge_id=edge_id,
        )

    def rebuild_models(self) -> None:
        (
            nodes_payload,
            backdrop_nodes_payload,
            minimap_nodes_payload,
            edges_payload,
        ) = self._payload_builder.rebuild_partitioned_models(
            model=self.model,
            registry=self.registry,
            workspace_id=self.workspace_id,
            scope_path=self.scope_path,
            graph_theme_bridge=self.graph_theme_bridge,
            show_port_labels=self.graphics_show_port_labels,
        )
        self._bridge._nodes_payload = nodes_payload
        self._bridge._backdrop_nodes_payload = backdrop_nodes_payload
        self._bridge._minimap_nodes_payload = minimap_nodes_payload
        self._bridge._edges_payload = edges_payload
        self._bridge.nodes_changed.emit()
        self._bridge.edges_changed.emit()

    def normalize_pdf_panel_pages(self, workspace: WorkspaceData) -> None:
        if self.model is None or self.registry is None:
            return
        self._payload_builder.normalize_pdf_panel_pages(
            model=self.model,
            registry=self.registry,
            workspace=workspace,
        )

    def active_graph_theme(self) -> GraphThemeDefinition:
        return self._payload_builder.active_graph_theme(self.graph_theme_bridge)

    def capture_history_snapshot(self) -> WorkspaceSnapshot | None:
        workspace = self.workspace_or_none()
        if self.history is None or workspace is None:
            return None
        return self.history.capture_workspace(workspace)

    def record_history(self, action_type: str, before_snapshot: WorkspaceSnapshot | None) -> None:
        workspace = self.workspace_or_none()
        if self.history is None or workspace is None or before_snapshot is None:
            return
        self.history.record_action(
            self.workspace_id,
            action_type,
            before_snapshot,
            workspace,
        )

    def grouped_history_action(self, action_type: str, workspace: WorkspaceData):
        if self.history is None or not self.workspace_id:
            return nullcontext()
        return self.history.grouped_action(
            self.workspace_id,
            action_type,
            workspace,
        )

    def emit_workspace_changed(self) -> None:
        self._bridge.workspace_changed.emit(self.workspace_id)

    def emit_scope_changed(self) -> None:
        self._bridge.scope_changed.emit()

    def emit_selection_changed(self, node_id: str) -> None:
        self._bridge.selection_changed.emit()
        self._bridge.node_selected.emit(node_id)

    def emit_node_selected(self, node_id: str) -> None:
        self._bridge.node_selected.emit(node_id)

    @staticmethod
    def surface_title_sync_enabled(spec: NodeTypeSpec) -> bool:
        return _surface_title_sync_enabled(spec)

    @staticmethod
    def synced_surface_title(node: NodeInstance, spec: NodeTypeSpec) -> str:
        return _synced_surface_title(node, spec)

    @staticmethod
    def sync_surface_title(node: NodeInstance, spec: NodeTypeSpec) -> None:
        _sync_surface_title(node, spec)


class GraphSceneBridge(QObject):
    node_selected = pyqtSignal(str)
    workspace_changed = pyqtSignal(str)
    scope_changed = pyqtSignal()
    nodes_changed = pyqtSignal()
    edges_changed = pyqtSignal()
    selection_changed = pyqtSignal()
    pending_surface_action_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._install_graph_boundary_adapters()
        self._model: GraphModel | None = None
        self._registry: NodeRegistry | None = None
        self._history: RuntimeGraphHistory | None = None
        self._payload_builder = GraphScenePayloadBuilder()
        self._scene_context = _GraphSceneContext(self, payload_builder=self._payload_builder)
        self._scope_selection = GraphSceneScopeSelection(self._scene_context)
        self._mutation_history = GraphSceneMutationHistory(self._scene_context, self._scope_selection)
        self._workspace_id = ""
        self._scope_path: ScopePath = ()
        self._selected_node_ids: list[str] = []
        self._selected_node_lookup: dict[str, bool] = {}
        self._nodes_payload: list[dict[str, Any]] = []
        self._backdrop_nodes_payload: list[dict[str, Any]] = []
        self._minimap_nodes_payload: list[dict[str, Any]] = []
        self._edges_payload: list[dict[str, Any]] = []
        self._graph_theme_bridge: GraphThemeBridge | None = None
        self._pending_surface_action_node_id: str = ""

    def _install_graph_boundary_adapters(self) -> None:
        set_graph_boundary_adapters(
            node_size_resolver=node_size,
            clamp_pdf_page_number_resolver=clamp_pdf_page_number,
        )

    def _graphics_preference_source(self) -> object | None:
        host = self.parent()
        if host is None:
            return None
        presenter = getattr(host, "graph_canvas_presenter", None)
        return presenter if presenter is not None else host

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

    @pyqtProperty("QVariantList", notify=nodes_changed)
    def nodes_model(self) -> list[dict[str, Any]]:
        return self._nodes_payload

    @pyqtProperty("QVariantList", notify=nodes_changed)
    def backdrop_nodes_model(self) -> list[dict[str, Any]]:
        return self._backdrop_nodes_payload

    @pyqtProperty("QVariantList", notify=edges_changed)
    def edges_model(self) -> list[dict[str, Any]]:
        return self._edges_payload

    @pyqtProperty(str, notify=pending_surface_action_changed)
    def pending_surface_action_node_id(self) -> str:
        return self._pending_surface_action_node_id

    @pyqtSlot(str)
    def set_pending_surface_action(self, node_id: str) -> None:
        if self._pending_surface_action_node_id != node_id:
            self._pending_surface_action_node_id = node_id
            self.pending_surface_action_changed.emit()

    @pyqtSlot(str, result=bool)
    def consume_pending_surface_action(self, node_id: str) -> bool:
        if self._pending_surface_action_node_id == node_id and node_id:
            self._pending_surface_action_node_id = ""
            self.pending_surface_action_changed.emit()
            return True
        return False

    @pyqtProperty("QVariantList", notify=nodes_changed)
    def minimap_nodes_model(self) -> list[dict[str, Any]]:
        return self._minimap_nodes_payload

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

    def _workspace_or_none(self) -> WorkspaceData | None:
        return self._scene_context.workspace_or_none()

    def _active_view_state(self, workspace: WorkspaceData):
        return self._scope_selection.active_view_state(workspace)

    def _normalized_selected_node_ids(
        self,
        workspace: WorkspaceData | None,
        node_ids: list[str],
    ) -> list[str]:
        return self._scope_selection.normalized_selected_node_ids(workspace, node_ids)

    def _selected_node_lookup_for_ids(self, node_ids: list[str]) -> dict[str, bool]:
        return self._scope_selection.selected_node_lookup_for_ids(node_ids)

    def _set_selected_node_ids(
        self,
        node_ids: list[str],
        *,
        workspace: WorkspaceData | None = None,
        emit_signals: bool = True,
    ) -> bool:
        return self._scope_selection.set_selected_node_ids(
            node_ids,
            workspace=workspace,
            emit_signals=emit_signals,
        )

    def _apply_scope_path(
        self,
        workspace: WorkspaceData,
        scope_path: ScopePath,
        *,
        persist: bool = True,
        emit_scope_changed: bool = True,
        emit_selection_changed: bool = True,
    ) -> bool:
        return self._scope_selection.apply_scope_path(
            workspace,
            scope_path,
            persist=persist,
            emit_scope_changed=emit_scope_changed,
            emit_selection_changed=emit_selection_changed,
        )

    def _restore_scope_path_from_view(self, workspace: WorkspaceData) -> None:
        self._scope_selection.restore_scope_path_from_view(workspace)

    @pyqtSlot(result=bool)
    def sync_scope_with_active_view(self) -> bool:
        return self._scope_selection.sync_scope_with_active_view()

    @pyqtSlot(str, result=bool)
    def open_subnode_scope(self, node_id: str) -> bool:
        return self._scope_selection.open_subnode_scope(node_id)

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

    def _require_bound(self) -> tuple[GraphModel, NodeRegistry]:
        return self._scene_context.require_bound()

    def set_workspace(self, model: GraphModel, registry: NodeRegistry, workspace_id: str) -> None:
        self._install_graph_boundary_adapters()
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
        self._scope_selection.clear_selection()

    @pyqtSlot()
    def clear_selection(self) -> None:
        self._scope_selection.clear_selection()

    @pyqtSlot(str)
    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        self._scope_selection.select_node(node_id, additive=additive)

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
        self._scope_selection.select_nodes_in_rect(
            x1,
            y1,
            x2,
            y2,
            additive=additive,
        )

    def node_item(self, node_id: str) -> _NodeItemProxy | None:
        return self._scope_selection.node_item(node_id)

    def node_bounds(self, node_id: str) -> QRectF | None:
        return self._scope_selection.node_bounds(node_id)

    def edge_item(self, edge_id: str) -> dict[str, Any] | None:
        return self._scene_context.edge_item(edge_id)

    @pyqtSlot(str, float, float, result=str)
    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        return self._mutation_history.add_node_from_type(type_id, x, y)

    def add_subnode_shell_pin(self, shell_node_id: str, pin_type_id: str) -> str:
        return self._mutation_history.add_subnode_shell_pin(shell_node_id, pin_type_id)

    def _create_node_from_type(
        self,
        *,
        type_id: str,
        x: float,
        y: float,
        parent_node_id: str | None,
        select_node: bool,
        configure_node=None,
    ) -> str:
        return self._mutation_history.create_node_from_type(
            type_id=type_id,
            x=x,
            y=y,
            parent_node_id=parent_node_id,
            select_node=select_node,
            configure_node=configure_node,
        )

    @pyqtSlot(str, str, str, str, result=bool)
    def are_ports_compatible(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> bool:
        return self._mutation_history.are_ports_compatible(
            source_node_id,
            source_port,
            target_node_id,
            target_port,
        )

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return self._mutation_history.are_port_kinds_compatible(source_kind, target_kind)

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return self._mutation_history.are_data_types_compatible(source_type, target_type)

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
        return self._mutation_history.add_edge(source_node_id, source_port, target_node_id, target_port)

    @pyqtSlot(str, str, result=str)
    def connect_nodes(self, node_a_id: str, node_b_id: str) -> str:
        return self._mutation_history.connect_nodes(node_a_id, node_b_id)

    def remove_edge(self, edge_id: str) -> None:
        self._mutation_history.remove_edge(edge_id)

    def _remove_node(self, node_id: str, *, require_visible: bool) -> bool:
        return self._mutation_history.remove_node_with_policy(node_id, require_visible=require_visible)

    def remove_node(self, node_id: str) -> None:
        self._mutation_history.remove_node(node_id)

    def remove_workspace_node(self, node_id: str) -> bool:
        return self._mutation_history.remove_workspace_node(node_id)

    @pyqtSlot(str)
    def focus_node_slot(self, node_id: str) -> None:
        self.focus_node(node_id)

    def focus_node(self, node_id: str) -> QPointF | None:
        return self._mutation_history.focus_node(node_id)

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        self._mutation_history.set_node_collapsed(node_id, collapsed)

    def _notify_selected_node_context_updated(self, node_id: str) -> None:
        self._mutation_history.notify_selected_node_context_updated(node_id)

    @pyqtSlot(str, str, str)
    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None:
        self._mutation_history.set_node_port_label(node_id, port_key, label)

    @pyqtSlot(str, str, "QVariant")
    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        self._mutation_history.set_node_property(node_id, key, value)

    @pyqtSlot(str, "QVariantMap", result=bool)
    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool:
        return self._mutation_history.set_node_properties(node_id, values)

    @pyqtSlot("QVariant", result="QVariantMap")
    def normalize_node_visual_style(self, visual_style: Any) -> dict[str, Any]:
        return self._mutation_history.normalize_node_visual_style(visual_style)

    @pyqtSlot(str, "QVariant")
    def set_node_visual_style(self, node_id: str, visual_style: Any) -> None:
        self._mutation_history.set_node_visual_style(node_id, visual_style)

    @pyqtSlot(str)
    def clear_node_visual_style(self, node_id: str) -> None:
        self._mutation_history.clear_node_visual_style(node_id)

    def set_node_title(self, node_id: str, title: str) -> None:
        self._mutation_history.set_node_title(node_id, title)

    @pyqtSlot("QVariant", result=str)
    def normalize_edge_label(self, label: Any) -> str:
        return self._mutation_history.normalize_edge_label(label)

    @pyqtSlot(str, "QVariant")
    def set_edge_label(self, edge_id: str, label: Any) -> None:
        self._mutation_history.set_edge_label(edge_id, label)

    @pyqtSlot(str)
    def clear_edge_label(self, edge_id: str) -> None:
        self._mutation_history.clear_edge_label(edge_id)

    @pyqtSlot("QVariant", result="QVariantMap")
    def normalize_edge_visual_style(self, visual_style: Any) -> dict[str, Any]:
        return self._mutation_history.normalize_edge_visual_style(visual_style)

    @pyqtSlot(str, "QVariant")
    def set_edge_visual_style(self, edge_id: str, visual_style: Any) -> None:
        self._mutation_history.set_edge_visual_style(edge_id, visual_style)

    @pyqtSlot(str)
    def clear_edge_visual_style(self, edge_id: str) -> None:
        self._mutation_history.clear_edge_visual_style(edge_id)

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> None:
        self._mutation_history.set_exposed_port(node_id, key, exposed)

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        self._mutation_history.move_node(node_id, x, y)

    @pyqtSlot(str, float, float)
    def resize_node(self, node_id: str, width: float, height: float) -> None:
        self._mutation_history.resize_node(node_id, width, height)

    @pyqtSlot(str, float, float, float, float)
    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        self._mutation_history.set_node_geometry(node_id, x, y, width, height)

    @pyqtSlot("QVariantList", float, float, result=bool)
    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool:
        return self._mutation_history.move_nodes_by_delta(node_ids, dx, dy)

    def align_selected_nodes(self, alignment: str, *, snap_to_grid: bool = False, grid_size: float = _SNAP_GRID_SIZE) -> bool:
        return self._mutation_history.align_selected_nodes(
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
        return self._mutation_history.distribute_selected_nodes(
            orientation,
            snap_to_grid=snap_to_grid,
            grid_size=grid_size,
        )

    @pyqtSlot("QVariantList", result=str)
    def wrap_node_ids_in_comment_backdrop(self, node_ids: list[Any]) -> str:
        return self._mutation_history.wrap_nodes_in_comment_backdrop(node_ids)

    @pyqtSlot(result=bool)
    def wrap_selected_nodes_in_comment_backdrop(self) -> bool:
        return self._mutation_history.wrap_selected_nodes_in_comment_backdrop()

    @pyqtSlot(result=bool)
    def group_selected_nodes(self) -> bool:
        return self._mutation_history.group_selected_nodes()

    @pyqtSlot(result=bool)
    def ungroup_selected_subnode(self) -> bool:
        return self._mutation_history.ungroup_selected_subnode()

    @pyqtSlot(result=bool)
    def duplicate_selected_subgraph(self) -> bool:
        return self._mutation_history.duplicate_selected_subgraph()

    def serialize_selected_subgraph_fragment(self) -> dict[str, Any] | None:
        return self._mutation_history.serialize_selected_subgraph_fragment()

    def fragment_bounds_center(self, fragment_payload: Any) -> tuple[float, float] | None:
        return self._mutation_history.fragment_bounds_center(fragment_payload)

    def paste_subgraph_fragment(self, fragment_payload: Any, center_x: float, center_y: float) -> bool:
        return self._mutation_history.paste_subgraph_fragment(fragment_payload, center_x, center_y)

    def delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:
        return self._mutation_history.delete_selected_graph_items(edge_ids)

    def _node(self, node_id: str) -> NodeInstance | None:
        return self._scene_context.node(node_id)

    def _node_or_raise(self, node_id: str) -> NodeInstance:
        return self._scene_context.node_or_raise(node_id)

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

    def _bounds_for_node_ids(self, node_ids: list[str]) -> QRectF | None:
        return self._scope_selection.bounds_for_node_ids(node_ids)

    def _rebuild_models(self) -> None:
        self._scene_context.rebuild_models()

    def _normalize_pdf_panel_pages(self, workspace: WorkspaceData) -> None:
        self._scene_context.normalize_pdf_panel_pages(workspace)

    def _active_graph_theme(self) -> GraphThemeDefinition:
        return self._scene_context.active_graph_theme()

    @staticmethod
    def _surface_title_sync_enabled(spec: NodeTypeSpec) -> bool:
        return _surface_title_sync_enabled(spec)

    @classmethod
    def _synced_surface_title(cls, node: NodeInstance, spec: NodeTypeSpec) -> str:
        return _synced_surface_title(node, spec)

    @classmethod
    def _sync_surface_title(cls, node: NodeInstance, spec: NodeTypeSpec) -> None:
        _sync_surface_title(node, spec)


__all__ = ["GraphSceneBridge"]
