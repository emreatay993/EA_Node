from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from ea_node_editor.graph.model import NodeInstance, WorkspaceData
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.shell.controllers.result import ControllerResult
from ea_node_editor.ui.shell.controllers.workspace_drop_connect_ops import WorkspaceDropConnectOps
from ea_node_editor.ui.shell.controllers.workspace_edit_ops import WorkspaceEditOps
from ea_node_editor.ui.shell.library_flow import pick_connection_candidate

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class _WorkspaceGraphEditControllerProtocol(Protocol):
    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None: ...

    def resolve_custom_workflow_definition(self, workflow_id: str) -> dict[str, Any] | None: ...

    def active_workspace(self) -> WorkspaceData | None: ...

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None: ...

    def on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None: ...

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None: ...

    def refresh_workspace_tabs(self) -> None: ...

    def _write_graph_fragment_to_clipboard(self, fragment_payload: dict[str, Any]) -> bool: ...

    def _read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None: ...

    def copy_selected_nodes_to_clipboard(self) -> bool: ...

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> ControllerResult[bool]: ...

    def clipboard_fragment_signature(self) -> str: ...

    def set_clipboard_fragment_signature(self, signature: str) -> None: ...

    def clipboard_paste_count(self) -> int: ...

    def set_clipboard_paste_count(self, count: int) -> None: ...

    def prompt_connection_candidate(
        self,
        *,
        title: str,
        label: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None: ...

    def insert_library_node(self, type_id: str, x: float, y: float) -> str: ...


class WorkspaceGraphEditController:
    def __init__(
        self,
        host: ShellWindow,
        controller: _WorkspaceGraphEditControllerProtocol,
    ) -> None:
        self._host = host
        self._controller = controller
        self._drop_connect_ops = WorkspaceDropConnectOps(host, controller)
        self._edit_ops = WorkspaceEditOps(host, controller)
        self._last_clipboard_fragment_signature = ""
        self._clipboard_paste_count = 0

    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None:
        node_id = self._host.scene.selected_node_id()
        if not node_id:
            return None
        workspace = self._host.model.project.workspaces.get(self._host.active_workspace_id)
        if workspace is None:
            return None
        node = workspace.nodes.get(node_id)
        if node is None:
            return None
        spec = self._host.registry.get_spec(node.type_id)
        return node, spec

    def set_selected_node_property(self, key: str, value: Any) -> None:
        self._edit_ops.set_selected_node_property(key, value)

    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        self._edit_ops.set_selected_port_exposed(key, exposed)

    def set_selected_port_label(self, key: str, label: Any) -> bool:
        return self._edit_ops.set_selected_port_label(key, label)

    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        self._edit_ops.set_selected_node_collapsed(collapsed)

    def request_add_selected_subnode_pin(self, direction: str) -> ControllerResult[str]:
        return self._edit_ops.request_add_selected_subnode_pin(direction)

    def add_node_from_library(self, type_id: str) -> None:
        center = self._host.view.mapToScene(self._host.view.viewport().rect().center())
        if self._controller.insert_library_node(type_id, center.x(), center.y()):
            self._controller.refresh_workspace_tabs()

    def insert_library_node(self, type_id: str, x: float, y: float) -> str:
        return self._drop_connect_ops.insert_library_node(type_id, x, y)

    def insert_custom_workflow_snapshot(self, workflow_id: str, x: float, y: float) -> str:
        return self._drop_connect_ops._insert_custom_workflow_snapshot(workflow_id, x, y)

    @staticmethod
    def normalize_custom_workflow_fragment_payload(fragment_payload: Any) -> dict[str, Any] | None:
        return WorkspaceDropConnectOps._normalize_custom_workflow_fragment_payload(fragment_payload)

    @staticmethod
    def retarget_fragment_roots(
        fragment_payload: dict[str, Any],
        *,
        target_parent_id: str | None,
    ) -> dict[str, Any]:
        return WorkspaceDropConnectOps._retarget_fragment_roots(
            fragment_payload,
            target_parent_id=target_parent_id,
        )

    @staticmethod
    def find_inserted_root_subnode_shell_id(
        workspace_nodes: dict[str, NodeInstance],
        inserted_node_ids: set[str],
    ) -> str:
        return WorkspaceDropConnectOps._find_inserted_root_subnode_shell_id(
            workspace_nodes,
            inserted_node_ids,
        )

    def active_workspace(self) -> WorkspaceData | None:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        return self._host.model.project.workspaces.get(workspace_id)

    def clipboard_fragment_signature(self) -> str:
        return self._last_clipboard_fragment_signature

    def set_clipboard_fragment_signature(self, signature: str) -> None:
        self._last_clipboard_fragment_signature = str(signature or "")

    def clipboard_paste_count(self) -> int:
        return int(self._clipboard_paste_count)

    def set_clipboard_paste_count(self, count: int) -> None:
        self._clipboard_paste_count = max(0, int(count))

    def prompt_connection_candidate(
        self,
        *,
        title: str,
        label: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return pick_connection_candidate(
            parent=self._host,
            title=title,
            label=label,
            candidates=candidates,
        )

    def auto_connect_dropped_node_to_port(
        self,
        new_node_id: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        return self._drop_connect_ops.auto_connect_dropped_node_to_port(
            new_node_id,
            target_node_id,
            target_port_key,
        )

    def auto_connect_dropped_node_to_edge(self, new_node_id: str, target_edge_id: str) -> bool:
        return self._drop_connect_ops.auto_connect_dropped_node_to_edge(new_node_id, target_edge_id)

    def on_scene_node_selected(self, node_id: str) -> None:
        workspace = self._host.model.project.workspaces[self._host.workspace_manager.active_workspace_id()]
        node = workspace.nodes.get(node_id)
        self._host.script_editor.set_node(node)
        if self._host.script_editor.visible:
            self._host.script_editor.focus_editor()
        self._host.selected_node_changed.emit()

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None:
        self._edit_ops.on_node_property_changed(node_id, key, value)

    @staticmethod
    def is_direct_child_pin_node(
        node: NodeInstance | None,
        workspace_nodes: dict[str, NodeInstance],
    ) -> bool:
        return WorkspaceEditOps._is_direct_child_pin_node(node, workspace_nodes)

    def on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None:
        self._edit_ops.on_port_exposed_changed(node_id, key, exposed)

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None:
        self._edit_ops.on_node_collapse_changed(node_id, collapsed)

    def connect_selected_nodes(self) -> None:
        self._edit_ops.connect_selected_nodes()

    def duplicate_selected_nodes(self) -> bool:
        return self._edit_ops.duplicate_selected_nodes()

    def group_selected_nodes(self) -> bool:
        return self._edit_ops.group_selected_nodes()

    def ungroup_selected_nodes(self) -> bool:
        return self._edit_ops.ungroup_selected_nodes()

    def run_layout_action(self, action: str | None = None, orientation: str | None = None) -> bool:
        return self._edit_ops.run_layout_action(action, orientation)

    def selected_node_bounds_payload(self) -> list[tuple[float, float, float, float]]:
        return self._edit_ops.selected_node_bounds_payload()

    @staticmethod
    def rectangles_overlap(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        return WorkspaceEditOps.rectangles_overlap(first, second)

    def count_overlap_pairs(self, bounds_payload: list[tuple[float, float, float, float]]) -> int:
        return self._edit_ops.count_overlap_pairs(bounds_payload)

    def align_selection_left(self) -> bool:
        return self._edit_ops.align_selection_left()

    def align_selection_right(self) -> bool:
        return self._edit_ops.align_selection_right()

    def align_selection_top(self) -> bool:
        return self._edit_ops.align_selection_top()

    def align_selection_bottom(self) -> bool:
        return self._edit_ops.align_selection_bottom()

    def distribute_selection_horizontally(self) -> bool:
        return self._edit_ops.distribute_selection_horizontally()

    def distribute_selection_vertically(self) -> bool:
        return self._edit_ops.distribute_selection_vertically()

    def clipboard(self):
        return self._edit_ops.clipboard()

    def write_graph_fragment_to_clipboard(self, fragment_payload: dict[str, Any]) -> bool:
        return self._edit_ops.write_graph_fragment_to_clipboard(fragment_payload)

    def read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None:
        return self._edit_ops.read_graph_fragment_from_clipboard()

    def copy_selected_nodes_to_clipboard(self) -> bool:
        return self._edit_ops.copy_selected_nodes_to_clipboard()

    def cut_selected_nodes_to_clipboard(self) -> bool:
        return self._edit_ops.cut_selected_nodes_to_clipboard()

    def paste_nodes_from_clipboard(self) -> bool:
        return self._edit_ops.paste_nodes_from_clipboard()

    def undo(self) -> bool:
        return self._edit_ops.undo()

    def redo(self) -> bool:
        return self._edit_ops.redo()

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
        return self._drop_connect_ops.request_drop_node_from_library(
            type_id,
            scene_x,
            scene_y,
            target_mode,
            target_node_id,
            target_port_key,
            target_edge_id,
        )

    def request_connect_ports(
        self,
        node_a_id: str,
        port_a: str,
        node_b_id: str,
        port_b: str,
    ) -> ControllerResult[bool]:
        return self._edit_ops.request_connect_ports(node_a_id, port_a, node_b_id, port_b)

    def request_remove_edge(self, edge_id: str) -> ControllerResult[bool]:
        return self._edit_ops.request_remove_edge(edge_id)

    def request_remove_node(self, node_id: str) -> ControllerResult[bool]:
        return self._edit_ops.request_remove_node(node_id)

    def request_rename_node(self, node_id: str) -> ControllerResult[bool]:
        return self._edit_ops.request_rename_node(node_id)

    def request_rename_selected_port(self, key: str) -> ControllerResult[bool]:
        return self._edit_ops.request_rename_selected_port(key)

    def request_remove_selected_port(self, key: str) -> ControllerResult[bool]:
        return self._edit_ops.request_remove_selected_port(key)

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> ControllerResult[bool]:
        return self._edit_ops.request_delete_selected_graph_items(edge_ids)
