from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSlot

from ea_node_editor.ui_qml.graph_scene_mutation_history import GraphSceneMutationPolicy

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


class GraphScenePolicyBridge(QObject):
    def __init__(self, scene_bridge: GraphSceneBridge, policy: GraphSceneMutationPolicy) -> None:
        super().__init__(scene_bridge)
        self._scene_bridge = scene_bridge
        self._policy = policy

    @property
    def scene_bridge(self) -> GraphSceneBridge:
        return self._scene_bridge

    @pyqtSlot(str, str, str, str, result=bool)
    def are_ports_compatible(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> bool:
        return self._policy.are_ports_compatible(
            source_node_id,
            source_port,
            target_node_id,
            target_port,
        )

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return self._policy.are_port_kinds_compatible(source_kind, target_kind)

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return self._policy.are_data_types_compatible(source_type, target_type)


__all__ = ["GraphScenePolicyBridge"]
