from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, Protocol

from ea_node_editor.graph.effective_ports import are_port_kinds_compatible, find_port
from ea_node_editor.graph.hierarchy import root_node_ids_for_fragment, subtree_node_ids
from ea_node_editor.graph.model import NodeInstance, WorkspaceData
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.ui.shell.runtime_history import ACTION_DELETE_SELECTED

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory


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
    def __init__(
        self,
        scene: _GraphSceneLike,
        registry: NodeRegistry,
        history: RuntimeGraphHistory | None = None,
    ) -> None:
        self._scene = scene
        self._registry = registry
        self._history = history

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

        port_a = self._port(workspace, node_a, source_port_key)
        port_b = self._port(workspace, node_b, target_port_key)
        if port_a is None or port_b is None:
            return GraphActionResult(False, "One or more ports are missing.")
        direction_a = port_a.direction
        direction_b = port_b.direction
        if direction_a == direction_b:
            return GraphActionResult(False, "Ports must have opposite directions.")
        kind_a = port_a.kind
        kind_b = port_b.kind
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
        history_group = nullcontext()
        if self._history is not None:
            history_group = self._history.grouped_action(
                workspace.workspace_id,
                ACTION_DELETE_SELECTED,
                workspace,
            )

        with history_group:
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

            removable_roots = root_node_ids_for_fragment(workspace, selected_node_ids)
            removable_ids = subtree_node_ids(workspace, removable_roots)
            for removable_node_id in reversed(removable_ids):
                if removable_node_id not in workspace.nodes:
                    continue
                self._scene.remove_node(removable_node_id)
                removed_any = True

        if not removed_any:
            return GraphActionResult(False, "No selected graph items to remove.")
        return GraphActionResult(True)

    def _port(self, workspace: WorkspaceData, node: NodeInstance, port_key: str):
        try:
            spec = self._registry.get_spec(node.type_id)
        except KeyError:
            return None
        return find_port(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
            port_key=port_key,
        )

    @staticmethod
    def _are_port_kinds_compatible(source_kind: str, target_kind: str) -> bool:
        return are_port_kinds_compatible(source_kind, target_kind)
