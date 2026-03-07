from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from ea_node_editor.graph.model import WorkspaceData
from ea_node_editor.nodes.registry import NodeRegistry


@dataclass(slots=True)
class GraphActionResult:
    ok: bool
    message: str = ""


class _GraphSceneLike(Protocol):
    def current_workspace(self) -> WorkspaceData: ...

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str: ...

    def remove_edge(self, edge_id: str) -> None: ...

    def remove_node(self, node_id: str) -> None: ...

    def set_node_title(self, node_id: str, title: str) -> None: ...

    def selectedItems(self) -> list[Any]: ...


class GraphInteractions:
    def __init__(self, scene: _GraphSceneLike, registry: NodeRegistry) -> None:
        self._scene = scene
        self._registry = registry

    def connect_ports(
        self,
        node_a_id: str,
        port_a_key: str,
        node_b_id: str,
        port_b_key: str,
    ) -> GraphActionResult:
        source_node_id = str(node_a_id).strip()
        source_port_key = str(port_a_key).strip()
        target_node_id = str(node_b_id).strip()
        target_port_key = str(port_b_key).strip()
        if not source_node_id or not source_port_key or not target_node_id or not target_port_key:
            return GraphActionResult(False, "Port connection request is incomplete.")

        workspace = self._scene.current_workspace()
        node_a = workspace.nodes.get(source_node_id)
        node_b = workspace.nodes.get(target_node_id)
        if node_a is None or node_b is None:
            return GraphActionResult(False, "One or more nodes are missing.")

        direction_a = self._port_direction(node_a.type_id, source_port_key)
        direction_b = self._port_direction(node_b.type_id, target_port_key)
        if direction_a is None or direction_b is None:
            return GraphActionResult(False, "One or more ports are missing.")
        if direction_a == direction_b:
            return GraphActionResult(False, "Ports must have opposite directions.")
        kind_a = self._port_kind(node_a.type_id, source_port_key)
        kind_b = self._port_kind(node_b.type_id, target_port_key)
        if kind_a is None or kind_b is None:
            return GraphActionResult(False, "One or more ports are missing.")
        if not self._are_port_kinds_compatible(kind_a, kind_b):
            return GraphActionResult(
                False,
                f"Incompatible port kinds: {kind_a} -> {kind_b}.",
            )

        if direction_a == "out":
            source_node_id, source_port_key, target_node_id, target_port_key = (
                source_node_id,
                source_port_key,
                target_node_id,
                target_port_key,
            )
        else:
            source_node_id, source_port_key, target_node_id, target_port_key = (
                target_node_id,
                target_port_key,
                source_node_id,
                source_port_key,
            )

        try:
            self._scene.add_edge(source_node_id, source_port_key, target_node_id, target_port_key)
        except (KeyError, ValueError) as exc:
            return GraphActionResult(False, str(exc))
        return GraphActionResult(True)

    def remove_edge(self, edge_id: str) -> GraphActionResult:
        normalized_edge_id = str(edge_id).strip()
        if not normalized_edge_id:
            return GraphActionResult(False, "Connection id is required.")
        workspace = self._scene.current_workspace()
        if normalized_edge_id not in workspace.edges:
            return GraphActionResult(False, "Connection not found.")
        self._scene.remove_edge(normalized_edge_id)
        return GraphActionResult(True)

    def remove_node(self, node_id: str) -> GraphActionResult:
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return GraphActionResult(False, "Node id is required.")
        workspace = self._scene.current_workspace()
        if normalized_node_id not in workspace.nodes:
            return GraphActionResult(False, "Node not found.")
        self._scene.remove_node(normalized_node_id)
        return GraphActionResult(True)

    def rename_node(self, node_id: str, title: str) -> GraphActionResult:
        normalized_node_id = str(node_id).strip()
        normalized_title = str(title).strip()
        if not normalized_node_id:
            return GraphActionResult(False, "Node id is required.")
        if not normalized_title:
            return GraphActionResult(False, "Node title cannot be empty.")

        workspace = self._scene.current_workspace()
        node = workspace.nodes.get(normalized_node_id)
        if node is None:
            return GraphActionResult(False, "Node not found.")
        if node.title == normalized_title:
            return GraphActionResult(True)
        self._scene.set_node_title(normalized_node_id, normalized_title)
        return GraphActionResult(True)

    def delete_selected_items(self, edge_ids: Iterable[Any]) -> GraphActionResult:
        workspace = self._scene.current_workspace()
        removed_any = False

        requested_edge_ids: list[str] = []
        seen_edge_ids: set[str] = set()
        for value in edge_ids:
            edge_id = str(value).strip()
            if not edge_id or edge_id in seen_edge_ids:
                continue
            seen_edge_ids.add(edge_id)
            requested_edge_ids.append(edge_id)

        for edge_id in requested_edge_ids:
            if edge_id not in workspace.edges:
                continue
            self._scene.remove_edge(edge_id)
            removed_any = True

        selected_node_ids: list[str] = []
        seen_node_ids: set[str] = set()
        for item in self._scene.selectedItems():
            node = getattr(item, "node", None)
            node_id = getattr(node, "node_id", "")
            normalized_node_id = str(node_id).strip()
            if not normalized_node_id or normalized_node_id in seen_node_ids:
                continue
            seen_node_ids.add(normalized_node_id)
            selected_node_ids.append(normalized_node_id)

        for node_id in selected_node_ids:
            if node_id not in workspace.nodes:
                continue
            self._scene.remove_node(node_id)
            removed_any = True

        if not removed_any:
            return GraphActionResult(False, "No selected graph items to remove.")
        return GraphActionResult(True)

    def _port_direction(self, type_id: str, port_key: str) -> str | None:
        try:
            spec = self._registry.get_spec(type_id)
        except KeyError:
            return None
        for port in spec.ports:
            if port.key == port_key:
                return port.direction
        return None

    def _port_kind(self, type_id: str, port_key: str) -> str | None:
        try:
            spec = self._registry.get_spec(type_id)
        except KeyError:
            return None
        for port in spec.ports:
            if port.key == port_key:
                return port.kind
        return None

    @staticmethod
    def _are_port_kinds_compatible(source_kind: str, target_kind: str) -> bool:
        if source_kind == "exec" or target_kind == "exec":
            return source_kind == "exec" and target_kind == "exec"
        return True
