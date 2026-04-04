from __future__ import annotations

from PyQt6.QtCore import QObject

from ea_node_editor.graph.boundary_adapters import build_graph_boundary_adapters
from ea_node_editor.ui.pdf_preview_provider import clamp_pdf_page_number
from ea_node_editor.ui_qml.edge_routing import node_size
from ea_node_editor.ui_qml.graph_scene import (
    GraphSceneBridgeBase,
    GraphSceneCommandBridge,
    GraphScenePolicyBridge,
    GraphSceneReadBridge,
    _GraphScenePayloadCache,
    _GraphScenePendingSurfaceAction,
)
from ea_node_editor.ui_qml.graph_scene.context import _GraphSceneContext
from ea_node_editor.ui_qml.graph_scene_mutation_history import (
    GraphSceneMutationHistory,
    GraphSceneMutationPolicy,
)
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from ea_node_editor.ui_qml.graph_scene_scope_selection import GraphSceneScopeSelection


class GraphSceneBridge(GraphSceneBridgeBase):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._boundary_adapters = build_graph_boundary_adapters(
            node_size_resolver=node_size,
            clamp_pdf_page_number_resolver=clamp_pdf_page_number,
        )
        self._model = None
        self._registry = None
        self._history = None
        self._payload_builder = GraphScenePayloadBuilder(boundary_adapters=self._boundary_adapters)
        self._scene_context = _GraphSceneContext(self, payload_builder=self._payload_builder)
        self._scope_selection = GraphSceneScopeSelection(self._scene_context)
        self._authoring_boundary = GraphSceneMutationHistory(
            self._scene_context,
            self._scope_selection,
            boundary_adapters=self._boundary_adapters,
        )
        self._policy_boundary = GraphSceneMutationPolicy(self._scene_context)
        self._workspace_id = ""
        self._scope_path = ()
        self._selected_node_ids = []
        self._selected_node_lookup = {}
        self._payload_cache = _GraphScenePayloadCache()
        self._graph_theme_bridge = None
        self._pending_surface_action = _GraphScenePendingSurfaceAction()
        self._state_bridge = GraphSceneReadBridge(self)
        self._command_bridge = GraphSceneCommandBridge(
            self,
            scope_selection=self._scope_selection,
            authoring_boundary=self._authoring_boundary,
            pending_surface_action=self._pending_surface_action,
        )
        self._policy_bridge = GraphScenePolicyBridge(self, self._policy_boundary)


__all__ = [
    "GraphSceneBridge",
    "GraphSceneCommandBridge",
    "GraphScenePolicyBridge",
    "GraphSceneReadBridge",
]
