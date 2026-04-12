from __future__ import annotations

from contextlib import contextmanager, nullcontext
from typing import TYPE_CHECKING, Any

from ea_node_editor.app_preferences import normalize_expand_collision_avoidance_settings
from ea_node_editor.graph.hierarchy import ScopePath
from ea_node_editor.graph.model import GraphModel, NodeInstance, WorkspaceData
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.graph_theme import GraphThemeDefinition
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory, WorkspaceSnapshot
    from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


def _surface_title_sync_enabled(spec: NodeTypeSpec) -> bool:
    family = str(spec.surface_family or "").strip()
    return family in {"flowchart", "planning", "annotation", "comment_backdrop"} and any(
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
    def graphics_expand_collision_avoidance(self) -> dict[str, Any]:
        source = self._bridge._graphics_preference_source()
        value = None if source is None else getattr(source, "graphics_expand_collision_avoidance", None)
        return normalize_expand_collision_avoidance_settings(value)

    @property
    def backdrop_nodes_payload(self) -> list[dict[str, Any]]:
        return self._bridge._payload_cache.backdrop_nodes

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
        self._bridge._payload_cache.update(
            nodes=nodes_payload,
            backdrop_nodes=backdrop_nodes_payload,
            minimap_nodes=minimap_nodes_payload,
            edges=edges_payload,
        )
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

    def _invalidate_cached_node_elapsed_for_history_action(
        self,
        workspace_id: str,
        action_type: str,
        *,
        before_snapshot: WorkspaceSnapshot | None,
        after_snapshot: WorkspaceSnapshot | None,
    ) -> None:
        host = self._bridge.parent()
        hook = getattr(host, "invalidate_cached_node_elapsed_for_history_action", None)
        if not callable(hook):
            return
        hook(
            workspace_id,
            action_type,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

    def record_history(self, action_type: str, before_snapshot: WorkspaceSnapshot | None) -> None:
        workspace = self.workspace_or_none()
        if self.history is None or workspace is None or before_snapshot is None:
            return
        if not self.history.record_action(
            self.workspace_id,
            action_type,
            before_snapshot,
            workspace,
        ):
            return
        self._invalidate_cached_node_elapsed_for_history_action(
            self.workspace_id,
            action_type,
            before_snapshot=before_snapshot,
            after_snapshot=self.history.capture_workspace(workspace),
        )

    @contextmanager
    def grouped_history_action(self, action_type: str, workspace: WorkspaceData):
        if self.history is None or not self.workspace_id:
            with nullcontext():
                yield
            return
        before_snapshot = self.history.capture_workspace(workspace)
        before_depth = self.history.undo_depth(self.workspace_id)
        with self.history.grouped_action(
            self.workspace_id,
            action_type,
            workspace,
        ):
            yield
        if self.history.undo_depth(self.workspace_id) <= before_depth:
            return
        self._invalidate_cached_node_elapsed_for_history_action(
            self.workspace_id,
            action_type,
            before_snapshot=before_snapshot,
            after_snapshot=self.history.capture_workspace(workspace),
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


__all__ = ["_GraphSceneContext"]
