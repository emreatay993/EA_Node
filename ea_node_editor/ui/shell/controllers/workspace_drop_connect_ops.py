from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Protocol

from ea_node_editor.custom_workflows import parse_custom_workflow_type_id
from ea_node_editor.graph.effective_ports import effective_ports, find_port, ports_compatible
from ea_node_editor.graph.hierarchy import scope_parent_id
from ea_node_editor.graph.model import NodeInstance, WorkspaceData
from ea_node_editor.graph.transforms import encode_fragment_external_parent_id
from ea_node_editor.nodes.builtins.subnode import SUBNODE_TYPE_ID
from ea_node_editor.ui.shell.controllers.result import ControllerResult
from ea_node_editor.ui.shell.library_flow import input_port_is_available
from ea_node_editor.ui.shell.runtime_clipboard import (
    build_graph_fragment_payload,
    normalize_graph_fragment_payload,
)
from ea_node_editor.ui.shell.runtime_history import ACTION_ADD_NODE

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class _WorkspaceDropConnectControllerProtocol(Protocol):
    def resolve_custom_workflow_definition(self, workflow_id: str) -> dict[str, Any] | None: ...

    def active_workspace(self) -> WorkspaceData | None: ...

    def prompt_connection_candidate(
        self,
        *,
        title: str,
        label: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None: ...

    def refresh_workspace_tabs(self) -> None: ...


class WorkspaceDropConnectOps:
    def __init__(
        self,
        host: ShellWindow,
        controller: _WorkspaceDropConnectControllerProtocol,
    ) -> None:
        self._host = host
        self._controller = controller

    def insert_library_node(self, type_id: str, x: float, y: float) -> str:
        normalized_type = str(type_id).strip()
        if not normalized_type:
            return ""
        custom_workflow_id = parse_custom_workflow_type_id(normalized_type)
        if custom_workflow_id:
            return self._insert_custom_workflow_snapshot(custom_workflow_id, float(x), float(y))
        try:
            return self._host.scene.add_node_from_type(normalized_type, x=float(x), y=float(y))
        except (KeyError, RuntimeError, ValueError):
            return ""

    def _insert_custom_workflow_snapshot(self, workflow_id: str, x: float, y: float) -> str:
        workspace = self._controller.active_workspace()
        if workspace is None:
            return ""
        definition = self._controller.resolve_custom_workflow_definition(workflow_id)
        if definition is None:
            return ""
        fragment_payload = self._normalize_custom_workflow_fragment_payload(definition.get("fragment"))
        if fragment_payload is None:
            return ""

        target_parent_id = scope_parent_id(self._host.scene.active_scope_path)
        scoped_fragment_payload = self._retarget_fragment_roots(
            fragment_payload,
            target_parent_id=target_parent_id,
        )

        before_node_ids = set(workspace.nodes)
        if not self._host.scene.paste_subgraph_fragment(scoped_fragment_payload, float(x), float(y)):
            return ""
        inserted_node_ids = set(workspace.nodes).difference(before_node_ids)
        if not inserted_node_ids:
            return ""

        shell_node_id = self._find_inserted_root_subnode_shell_id(workspace.nodes, inserted_node_ids)
        if shell_node_id:
            return shell_node_id
        selected_node_id = self._host.scene.selected_node_id() or ""
        if selected_node_id in inserted_node_ids:
            return selected_node_id
        return sorted(inserted_node_ids)[0]

    @staticmethod
    def _normalize_custom_workflow_fragment_payload(fragment_payload: Any) -> dict[str, Any] | None:
        if not isinstance(fragment_payload, dict):
            return None
        normalized_fragment = normalize_graph_fragment_payload(fragment_payload)
        if normalized_fragment is not None:
            return normalized_fragment
        nodes_payload = fragment_payload.get("nodes")
        edges_payload = fragment_payload.get("edges")
        if not isinstance(nodes_payload, list) or not isinstance(edges_payload, list):
            return None
        return normalize_graph_fragment_payload(
            build_graph_fragment_payload(
                nodes=copy.deepcopy(nodes_payload),
                edges=copy.deepcopy(edges_payload),
            )
        )

    @staticmethod
    def _retarget_fragment_roots(
        fragment_payload: dict[str, Any],
        *,
        target_parent_id: str | None,
    ) -> dict[str, Any]:
        rewritten = copy.deepcopy(fragment_payload)
        nodes_payload = rewritten.get("nodes")
        if not isinstance(nodes_payload, list):
            return rewritten
        fragment_node_ids = {
            str(node_payload.get("ref_id", "")).strip()
            for node_payload in nodes_payload
            if isinstance(node_payload, dict)
        }
        for node_payload in nodes_payload:
            if not isinstance(node_payload, dict):
                continue
            normalized_parent = str(node_payload.get("parent_node_id", "")).strip()
            if normalized_parent and normalized_parent in fragment_node_ids:
                continue
            if target_parent_id and target_parent_id in fragment_node_ids:
                node_payload["parent_node_id"] = encode_fragment_external_parent_id(target_parent_id)
            else:
                node_payload["parent_node_id"] = target_parent_id
        return rewritten

    @staticmethod
    def _find_inserted_root_subnode_shell_id(
        workspace_nodes: dict[str, NodeInstance],
        inserted_node_ids: set[str],
    ) -> str:
        shell_candidates: list[NodeInstance] = []
        for node_id in inserted_node_ids:
            node = workspace_nodes.get(node_id)
            if node is None or node.type_id != SUBNODE_TYPE_ID:
                continue
            parent_id = str(node.parent_node_id).strip() if node.parent_node_id is not None else ""
            if parent_id and parent_id in inserted_node_ids:
                continue
            shell_candidates.append(node)
        if not shell_candidates:
            return ""
        shell_candidates.sort(key=lambda node: (float(node.y), float(node.x), node.node_id))
        return shell_candidates[0].node_id

    def auto_connect_dropped_node_to_port(
        self,
        new_node_id: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        workspace = self._controller.active_workspace()
        if workspace is None:
            return False

        new_node = workspace.nodes.get(new_node_id)
        target_node = workspace.nodes.get(target_node_id)
        if new_node is None or target_node is None:
            return False

        new_spec = self._host.registry.get_spec(new_node.type_id)
        target_spec = self._host.registry.get_spec(target_node.type_id)
        target_port = find_port(
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace.nodes,
            port_key=str(target_port_key).strip(),
        )
        if target_port is None:
            return False

        new_ports = [
            port
            for port in effective_ports(
                node=new_node,
                spec=new_spec,
                workspace_nodes=workspace.nodes,
            )
            if port.exposed
        ]
        candidates: list[dict[str, Any]] = []
        if target_port.direction == "in":
            if not input_port_is_available(workspace, target_node.node_id, target_port.key):
                return False
            for port in new_ports:
                if port.direction != "out":
                    continue
                if not ports_compatible(port, target_port):
                    continue
                candidates.append(
                    {
                        "source_node_id": new_node.node_id,
                        "source_port_key": port.key,
                        "target_node_id": target_node.node_id,
                        "target_port_key": target_port.key,
                        "label": (
                            f"{new_spec.display_name}.{port.label or port.key} -> "
                            f"{target_spec.display_name}.{target_port.label or target_port.key}"
                        ),
                    }
                )
        elif target_port.direction == "out":
            for port in new_ports:
                if port.direction != "in":
                    continue
                if not ports_compatible(target_port, port):
                    continue
                candidates.append(
                    {
                        "source_node_id": target_node.node_id,
                        "source_port_key": target_port.key,
                        "target_node_id": new_node.node_id,
                        "target_port_key": port.key,
                        "label": (
                            f"{target_spec.display_name}.{target_port.label or target_port.key} -> "
                            f"{new_spec.display_name}.{port.label or port.key}"
                        ),
                    }
                )
        else:
            return False

        selected = self._controller.prompt_connection_candidate(
            title="Auto-Connect Port",
            label="Choose connection:",
            candidates=candidates,
        )
        if selected is None:
            return False

        try:
            self._host.scene.add_edge(
                selected["source_node_id"],
                selected["source_port_key"],
                selected["target_node_id"],
                selected["target_port_key"],
            )
            return True
        except (KeyError, ValueError):
            return False

    def auto_connect_dropped_node_to_edge(self, new_node_id: str, target_edge_id: str) -> bool:
        workspace = self._controller.active_workspace()
        if workspace is None:
            return False
        edge = workspace.edges.get(target_edge_id)
        new_node = workspace.nodes.get(new_node_id)
        if edge is None or new_node is None:
            return False

        source_node = workspace.nodes.get(edge.source_node_id)
        target_node = workspace.nodes.get(edge.target_node_id)
        if source_node is None or target_node is None:
            return False

        source_spec = self._host.registry.get_spec(source_node.type_id)
        target_spec = self._host.registry.get_spec(target_node.type_id)
        new_spec = self._host.registry.get_spec(new_node.type_id)
        source_port = find_port(
            node=source_node,
            spec=source_spec,
            workspace_nodes=workspace.nodes,
            port_key=str(edge.source_port_key).strip(),
        )
        target_port = find_port(
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace.nodes,
            port_key=str(edge.target_port_key).strip(),
        )
        if source_port is None or target_port is None:
            return False

        new_ports = [
            port
            for port in effective_ports(
                node=new_node,
                spec=new_spec,
                workspace_nodes=workspace.nodes,
            )
            if port.exposed
        ]
        candidate_inputs = [
            port
            for port in new_ports
            if port.direction == "in"
            and ports_compatible(source_port, port)
        ]
        candidate_outputs = [
            port
            for port in new_ports
            if port.direction == "out"
            and ports_compatible(port, target_port)
        ]

        candidates: list[dict[str, Any]] = []
        for input_port in candidate_inputs:
            for output_port in candidate_outputs:
                candidates.append(
                    {
                        "new_input_port": input_port.key,
                        "new_output_port": output_port.key,
                        "label": (
                            f"{source_spec.display_name}.{source_port.label or source_port.key} -> "
                            f"{new_spec.display_name}.{input_port.label or input_port.key}, "
                            f"{new_spec.display_name}.{output_port.label or output_port.key} -> "
                            f"{target_spec.display_name}.{target_port.label or target_port.key}"
                        ),
                    }
                )

        selected = self._controller.prompt_connection_candidate(
            title="Auto-Insert On Edge",
            label="Choose inserted wiring:",
            candidates=candidates,
        )
        if selected is None:
            return False

        original = {
            "source_node_id": edge.source_node_id,
            "source_port_key": edge.source_port_key,
            "target_node_id": edge.target_node_id,
            "target_port_key": edge.target_port_key,
        }
        created_edge_ids: list[str] = []
        removed_original = False
        try:
            self._host.scene.remove_edge(target_edge_id)
            removed_original = True
            first_id = self._host.scene.add_edge(
                original["source_node_id"],
                original["source_port_key"],
                new_node_id,
                selected["new_input_port"],
            )
            created_edge_ids.append(first_id)
            second_id = self._host.scene.add_edge(
                new_node_id,
                selected["new_output_port"],
                original["target_node_id"],
                original["target_port_key"],
            )
            created_edge_ids.append(second_id)
            return True
        except (KeyError, ValueError):
            for edge_id in created_edge_ids:
                self._host.scene.remove_edge(edge_id)
            if removed_original:
                try:
                    self._host.scene.add_edge(
                        original["source_node_id"],
                        original["source_port_key"],
                        original["target_node_id"],
                        original["target_port_key"],
                    )
                except (KeyError, ValueError):
                    pass
            return False

    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
    ) -> ControllerResult[bool]:
        workspace = self._controller.active_workspace()
        if workspace is None:
            return ControllerResult(False, "Workspace not found.", payload=False)

        with self._host.runtime_history.grouped_action(
            workspace.workspace_id,
            ACTION_ADD_NODE,
            workspace,
        ):
            created_node_id = self.insert_library_node(type_id, scene_x, scene_y)
            if not created_node_id:
                return ControllerResult(False, "Node could not be created.", payload=False)

            mode = str(target_mode).strip().lower()
            if mode == "port":
                self.auto_connect_dropped_node_to_port(
                    created_node_id,
                    str(target_node_id).strip(),
                    str(target_port_key).strip(),
                )
            elif mode == "edge":
                self.auto_connect_dropped_node_to_edge(
                    created_node_id,
                    str(target_edge_id).strip(),
                )

        self._controller.refresh_workspace_tabs()
        return ControllerResult(True, payload=True)
