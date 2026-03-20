from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QRectF

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.shell.controllers.result import ControllerResult
from ea_node_editor.ui.shell.controllers.workflow_library_controller import WorkflowLibraryController
from ea_node_editor.ui.shell.controllers.workspace_graph_edit_controller import WorkspaceGraphEditController
from ea_node_editor.ui.shell.controllers.workspace_navigation_controller import WorkspaceNavigationController
from ea_node_editor.ui.shell.controllers.workspace_package_io_controller import WorkspacePackageIOController

_GRAPH_SEARCH_LIMIT = 10


class _WorkflowLibraryCapability:
    def __init__(self, controller: "WorkspaceLibraryController") -> None:
        self._controller = controller

    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None:
        return self._controller.selected_node_context()

    def active_workspace(self):
        return self._controller.active_workspace()


class _WorkspaceNavigationCapability:
    def __init__(self, controller: "WorkspaceLibraryController") -> None:
        self._controller = controller

    def save_active_view_state(self) -> None:
        self._controller.save_active_view_state()

    def restore_active_view_state(self) -> None:
        self._controller.restore_active_view_state()

    def refresh_workspace_tabs(self) -> None:
        self._controller.refresh_workspace_tabs()

    def switch_workspace(self, workspace_id: str) -> None:
        self._controller.switch_workspace(workspace_id)

    def rename_workspace_by_id(self, workspace_id: str) -> bool:
        return self._controller.rename_workspace_by_id(workspace_id)

    def on_workspace_tab_close(self, index: int) -> None:
        self._controller.on_workspace_tab_close(index)

    def reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]:
        return self._controller.reveal_parent_chain(workspace_id, node_id)

    def center_on_node(self, node_id: str) -> bool:
        return self._controller.center_on_node(node_id)

    def center_on_selection(self) -> bool:
        return self._controller.center_on_selection()


class _WorkspaceGraphEditCapability:
    def __init__(self, controller: "WorkspaceLibraryController") -> None:
        self._controller = controller

    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None:
        return self._controller.selected_node_context()

    def resolve_custom_workflow_definition(self, workflow_id: str) -> dict[str, Any] | None:
        return self._controller.resolve_custom_workflow_definition(workflow_id)

    def active_workspace(self):
        return self._controller.active_workspace()

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None:
        self._controller.workspace_graph_edit_controller.on_node_property_changed(node_id, key, value)

    def on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None:
        self._controller.workspace_graph_edit_controller.on_port_exposed_changed(node_id, key, exposed)

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None:
        self._controller.workspace_graph_edit_controller.on_node_collapse_changed(node_id, collapsed)

    def refresh_workspace_tabs(self) -> None:
        self._controller.refresh_workspace_tabs()

    def _write_graph_fragment_to_clipboard(self, fragment_payload: dict[str, Any]) -> bool:
        return self._controller._write_graph_fragment_to_clipboard(fragment_payload)

    def _read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None:
        return self._controller._read_graph_fragment_from_clipboard()

    def copy_selected_nodes_to_clipboard(self) -> bool:
        return self._controller.copy_selected_nodes_to_clipboard()

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> ControllerResult[bool]:
        return self._controller.request_delete_selected_graph_items(edge_ids)

    def clipboard_fragment_signature(self) -> str:
        return self._controller.clipboard_fragment_signature()

    def set_clipboard_fragment_signature(self, signature: str) -> None:
        self._controller.set_clipboard_fragment_signature(signature)

    def clipboard_paste_count(self) -> int:
        return self._controller.clipboard_paste_count()

    def set_clipboard_paste_count(self, count: int) -> None:
        self._controller.set_clipboard_paste_count(count)

    def prompt_connection_candidate(
        self,
        *,
        title: str,
        label: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return self._controller.prompt_connection_candidate(
            title=title,
            label=label,
            candidates=candidates,
        )

    def insert_library_node(self, type_id: str, x: float, y: float) -> str:
        return self._controller.insert_library_node(type_id, x, y)


class _WorkspacePackageIOCapability:
    def __init__(self, controller: "WorkspaceLibraryController") -> None:
        self._controller = controller

    def _custom_workflow_definitions(self) -> list[dict[str, Any]]:
        return self._controller._custom_workflow_definitions()

    def _set_custom_workflow_definitions(self, definitions: list[dict[str, Any]]) -> None:
        self._controller._set_custom_workflow_definitions(definitions)

    def _prompt_custom_workflow_export_definition(
        self,
        definitions: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return self._controller._prompt_custom_workflow_export_definition(definitions)


class WorkspaceLibraryController:
    def __init__(self, host) -> None:  # noqa: ANN001
        self._host = host
        self._custom_workflow_capability = _WorkflowLibraryCapability(self)
        self._navigation_capability = _WorkspaceNavigationCapability(self)
        self._edit_command_capability = _WorkspaceGraphEditCapability(self)
        self._import_export_capability = _WorkspacePackageIOCapability(self)
        self.workflow_library_controller = WorkflowLibraryController(host, self._custom_workflow_capability)
        self.workspace_navigation_controller = WorkspaceNavigationController(host, self._navigation_capability)
        self.workspace_graph_edit_controller = WorkspaceGraphEditController(host, self._edit_command_capability)
        self.workspace_package_io_controller = WorkspacePackageIOController(host, self._import_export_capability)

    def _project_metadata(self) -> dict[str, Any]:
        return self.workflow_library_controller.project_metadata()

    def _custom_workflow_definitions(self) -> list[dict[str, Any]]:
        return self.workflow_library_controller.custom_workflow_definitions()

    def _set_custom_workflow_definitions(self, definitions: list[dict[str, Any]]) -> None:
        self.workflow_library_controller.set_custom_workflow_definitions(definitions)

    @staticmethod
    def _global_custom_workflow_definitions() -> list[dict[str, Any]]:
        return WorkflowLibraryController.global_custom_workflow_definitions()

    @staticmethod
    def _set_global_custom_workflow_definitions(definitions: list[dict[str, Any]]) -> None:
        WorkflowLibraryController.set_global_custom_workflow_definitions(definitions)

    @staticmethod
    def _upsert_workflow_definition_by_id(
        definitions: list[dict[str, Any]],
        definition: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return WorkflowLibraryController.upsert_workflow_definition_by_id(definitions, definition)

    @staticmethod
    def _rename_workflow_definition_by_id(
        definitions: list[dict[str, Any]],
        workflow_id: str,
        new_name: str,
    ) -> list[dict[str, Any]] | None:
        return WorkflowLibraryController.rename_workflow_definition_by_id(
            definitions,
            workflow_id,
            new_name,
        )

    def custom_workflow_library_items(self) -> list[dict[str, Any]]:
        return self.workflow_library_controller.custom_workflow_library_items()

    def resolve_custom_workflow_definition(self, workflow_id: str) -> dict[str, Any] | None:
        return self.workflow_library_controller.resolve_custom_workflow_definition(workflow_id)

    def set_custom_workflow_scope(self, workflow_id: str, workflow_scope: str) -> ControllerResult[bool]:
        return self.workflow_library_controller.set_custom_workflow_scope(workflow_id, workflow_scope)

    def delete_custom_workflow(self, workflow_id: str, workflow_scope: str = "") -> ControllerResult[bool]:
        return self.workflow_library_controller.delete_custom_workflow(workflow_id, workflow_scope)

    def rename_custom_workflow(self, workflow_id: str, workflow_scope: str = "") -> ControllerResult[bool]:
        return self.workflow_library_controller.rename_custom_workflow(workflow_id, workflow_scope)

    def publish_custom_workflow_from_selected_subnode(self) -> ControllerResult[bool]:
        return self.workflow_library_controller.publish_custom_workflow_from_selected_subnode()

    def publish_custom_workflow_from_current_scope(self) -> ControllerResult[bool]:
        return self.workflow_library_controller.publish_custom_workflow_from_current_scope()

    def publish_custom_workflow_from_node(self, node_id: str) -> ControllerResult[bool]:
        return self.workflow_library_controller.publish_custom_workflow_from_node(node_id)

    def _publish_custom_workflow_from_shell(self, shell_node_id: str) -> ControllerResult[bool]:
        return self.workflow_library_controller.publish_custom_workflow_from_shell(shell_node_id)

    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None:
        return self.workspace_graph_edit_controller.selected_node_context()

    def set_selected_node_property(self, key: str, value: Any) -> None:
        self.workspace_graph_edit_controller.set_selected_node_property(key, value)

    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        self.workspace_graph_edit_controller.set_selected_port_exposed(key, exposed)

    def set_selected_port_label(self, key: str, label: Any) -> bool:
        return self.workspace_graph_edit_controller.set_selected_port_label(key, label)

    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        self.workspace_graph_edit_controller.set_selected_node_collapsed(collapsed)

    def request_add_selected_subnode_pin(self, direction: str) -> ControllerResult[str]:
        return self.workspace_graph_edit_controller.request_add_selected_subnode_pin(direction)

    def switch_workspace_by_offset(self, offset: int) -> None:
        self.workspace_navigation_controller.switch_workspace_by_offset(offset)

    def refresh_workspace_tabs(self) -> None:
        self.workspace_navigation_controller.refresh_workspace_tabs()

    def switch_workspace(self, workspace_id: str) -> None:
        self.workspace_navigation_controller.switch_workspace(workspace_id)

    def move_workspace(self, from_index: int, to_index: int) -> bool:
        return self.workspace_navigation_controller.move_workspace(from_index, to_index)

    def save_active_view_state(self) -> None:
        self.workspace_navigation_controller.save_active_view_state()

    def restore_active_view_state(self) -> None:
        self.workspace_navigation_controller.restore_active_view_state()

    def visible_scene_rect(self) -> QRectF:
        return self.workspace_navigation_controller.visible_scene_rect()

    def current_workspace_scene_bounds(self) -> QRectF | None:
        return self.workspace_navigation_controller.current_workspace_scene_bounds()

    def selection_bounds(self) -> QRectF | None:
        return self.workspace_navigation_controller.selection_bounds()

    def frame_all(self) -> bool:
        return self.workspace_navigation_controller.frame_all()

    def frame_selection(self) -> bool:
        return self.workspace_navigation_controller.frame_selection()

    def frame_node(self, node_id: str) -> bool:
        return self.workspace_navigation_controller.frame_node(node_id)

    def center_on_node(self, node_id: str) -> bool:
        return self.workspace_navigation_controller.center_on_node(node_id)

    def center_on_selection(self) -> bool:
        return self.workspace_navigation_controller.center_on_selection()

    def _frame_scene_bounds(self, bounds: QRectF | None) -> bool:
        return self.workspace_navigation_controller.frame_scene_bounds(bounds)

    @staticmethod
    def _graph_search_rank(
        query: str,
        *,
        title: str,
        display_name: str,
        type_id: str,
    ) -> int | None:
        return WorkspaceNavigationController.graph_search_rank(
            query,
            title=title,
            display_name=display_name,
            type_id=type_id,
        )

    def search_graph_nodes(
        self,
        query: str,
        limit: int = _GRAPH_SEARCH_LIMIT,
    ) -> list[dict[str, Any]]:
        return self.workspace_navigation_controller.search_graph_nodes(query, limit)

    def jump_to_graph_node(self, workspace_id: str, node_id: str) -> bool:
        return self.workspace_navigation_controller.jump_to_graph_node(workspace_id, node_id)

    def create_view(self) -> None:
        self.workspace_navigation_controller.create_view()

    def switch_view(self, view_id: str) -> None:
        self.workspace_navigation_controller.switch_view(view_id)

    def create_workspace(self) -> None:
        self.workspace_navigation_controller.create_workspace()

    def rename_active_workspace(self) -> None:
        self.workspace_navigation_controller.rename_active_workspace()

    def rename_workspace_by_id(self, workspace_id: str) -> bool:
        return self.workspace_navigation_controller.rename_workspace_by_id(workspace_id)

    def duplicate_active_workspace(self) -> None:
        self.workspace_navigation_controller.duplicate_active_workspace()

    def close_active_workspace(self) -> None:
        self.workspace_navigation_controller.close_active_workspace()

    def close_workspace_by_id(self, workspace_id: str) -> bool:
        return self.workspace_navigation_controller.close_workspace_by_id(workspace_id)

    def close_view(self, view_id: str) -> bool:
        return self.workspace_navigation_controller.close_view(view_id)

    def rename_view(self, view_id: str) -> bool:
        return self.workspace_navigation_controller.rename_view(view_id)

    def move_view(self, from_index: int, to_index: int) -> bool:
        return self.workspace_navigation_controller.move_view(from_index, to_index)

    def on_workspace_tab_changed(self, index: int) -> None:
        self.workspace_navigation_controller.on_workspace_tab_changed(index)

    def on_workspace_tab_close(self, index: int) -> None:
        self.workspace_navigation_controller.on_workspace_tab_close(index)

    def add_node_from_library(self, type_id: str) -> None:
        self.workspace_graph_edit_controller.add_node_from_library(type_id)

    def insert_library_node(self, type_id: str, x: float, y: float) -> str:
        return self.workspace_graph_edit_controller.insert_library_node(type_id, x, y)

    def _insert_custom_workflow_snapshot(self, workflow_id: str, x: float, y: float) -> str:
        return self.workspace_graph_edit_controller.insert_custom_workflow_snapshot(workflow_id, x, y)

    @staticmethod
    def _normalize_custom_workflow_fragment_payload(fragment_payload: Any) -> dict[str, Any] | None:
        return WorkspaceGraphEditController.normalize_custom_workflow_fragment_payload(fragment_payload)

    @staticmethod
    def _retarget_fragment_roots(
        fragment_payload: dict[str, Any],
        *,
        target_parent_id: str | None,
    ) -> dict[str, Any]:
        return WorkspaceGraphEditController.retarget_fragment_roots(
            fragment_payload,
            target_parent_id=target_parent_id,
        )

    @staticmethod
    def _find_inserted_root_subnode_shell_id(
        workspace_nodes: dict[str, NodeInstance],
        inserted_node_ids: set[str],
    ) -> str:
        return WorkspaceGraphEditController.find_inserted_root_subnode_shell_id(
            workspace_nodes,
            inserted_node_ids,
        )

    def active_workspace(self):
        return self.workspace_graph_edit_controller.active_workspace()

    def clipboard_fragment_signature(self) -> str:
        return self.workspace_graph_edit_controller.clipboard_fragment_signature()

    def set_clipboard_fragment_signature(self, signature: str) -> None:
        self.workspace_graph_edit_controller.set_clipboard_fragment_signature(signature)

    def clipboard_paste_count(self) -> int:
        return self.workspace_graph_edit_controller.clipboard_paste_count()

    def set_clipboard_paste_count(self, count: int) -> None:
        self.workspace_graph_edit_controller.set_clipboard_paste_count(count)

    def prompt_connection_candidate(
        self,
        *,
        title: str,
        label: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return self.workspace_graph_edit_controller.prompt_connection_candidate(
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
        return self.workspace_graph_edit_controller.auto_connect_dropped_node_to_port(
            new_node_id,
            target_node_id,
            target_port_key,
        )

    def auto_connect_dropped_node_to_edge(self, new_node_id: str, target_edge_id: str) -> bool:
        return self.workspace_graph_edit_controller.auto_connect_dropped_node_to_edge(
            new_node_id,
            target_edge_id,
        )

    def on_scene_node_selected(self, node_id: str) -> None:
        self.workspace_graph_edit_controller.on_scene_node_selected(node_id)

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None:
        self.workspace_graph_edit_controller.on_node_property_changed(node_id, key, value)

    @staticmethod
    def _is_direct_child_pin_node(
        node: NodeInstance | None,
        workspace_nodes: dict[str, NodeInstance],
    ) -> bool:
        return WorkspaceGraphEditController.is_direct_child_pin_node(node, workspace_nodes)

    def on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None:
        self.workspace_graph_edit_controller.on_port_exposed_changed(node_id, key, exposed)

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None:
        self.workspace_graph_edit_controller.on_node_collapse_changed(node_id, collapsed)

    def connect_selected_nodes(self) -> None:
        self.workspace_graph_edit_controller.connect_selected_nodes()

    def duplicate_selected_nodes(self) -> bool:
        return self.workspace_graph_edit_controller.duplicate_selected_nodes()

    def group_selected_nodes(self) -> bool:
        return self.workspace_graph_edit_controller.group_selected_nodes()

    def ungroup_selected_nodes(self) -> bool:
        return self.workspace_graph_edit_controller.ungroup_selected_nodes()

    def _run_layout_action(self, action: str | None = None, orientation: str | None = None) -> bool:
        return self.workspace_graph_edit_controller.run_layout_action(action, orientation)

    def _selected_node_bounds_payload(self) -> list[tuple[float, float, float, float]]:
        return self.workspace_graph_edit_controller.selected_node_bounds_payload()

    @staticmethod
    def _rectangles_overlap(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        return WorkspaceGraphEditController.rectangles_overlap(first, second)

    def _count_overlap_pairs(self, bounds_payload: list[tuple[float, float, float, float]]) -> int:
        return self.workspace_graph_edit_controller.count_overlap_pairs(bounds_payload)

    def align_selection_left(self) -> bool:
        return self.workspace_graph_edit_controller.align_selection_left()

    def align_selection_right(self) -> bool:
        return self.workspace_graph_edit_controller.align_selection_right()

    def align_selection_top(self) -> bool:
        return self.workspace_graph_edit_controller.align_selection_top()

    def align_selection_bottom(self) -> bool:
        return self.workspace_graph_edit_controller.align_selection_bottom()

    def distribute_selection_horizontally(self) -> bool:
        return self.workspace_graph_edit_controller.distribute_selection_horizontally()

    def distribute_selection_vertically(self) -> bool:
        return self.workspace_graph_edit_controller.distribute_selection_vertically()

    def _clipboard(self):
        return self.workspace_graph_edit_controller.clipboard()

    def _write_graph_fragment_to_clipboard(self, fragment_payload: dict[str, Any]) -> bool:
        return self.workspace_graph_edit_controller.write_graph_fragment_to_clipboard(fragment_payload)

    def _read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None:
        return self.workspace_graph_edit_controller.read_graph_fragment_from_clipboard()

    def copy_selected_nodes_to_clipboard(self) -> bool:
        return self.workspace_graph_edit_controller.copy_selected_nodes_to_clipboard()

    def cut_selected_nodes_to_clipboard(self) -> bool:
        return self.workspace_graph_edit_controller.cut_selected_nodes_to_clipboard()

    def paste_nodes_from_clipboard(self) -> bool:
        return self.workspace_graph_edit_controller.paste_nodes_from_clipboard()

    def undo(self) -> bool:
        return self.workspace_graph_edit_controller.undo()

    def redo(self) -> bool:
        return self.workspace_graph_edit_controller.redo()

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
        return self.workspace_graph_edit_controller.request_drop_node_from_library(
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
        return self.workspace_graph_edit_controller.request_connect_ports(
            node_a_id,
            port_a,
            node_b_id,
            port_b,
        )

    def request_remove_edge(self, edge_id: str) -> ControllerResult[bool]:
        return self.workspace_graph_edit_controller.request_remove_edge(edge_id)

    def request_remove_node(self, node_id: str) -> ControllerResult[bool]:
        return self.workspace_graph_edit_controller.request_remove_node(node_id)

    def request_rename_node(self, node_id: str) -> ControllerResult[bool]:
        return self.workspace_graph_edit_controller.request_rename_node(node_id)

    def request_rename_selected_port(self, key: str) -> ControllerResult[bool]:
        return self.workspace_graph_edit_controller.request_rename_selected_port(key)

    def request_remove_selected_port(self, key: str) -> ControllerResult[bool]:
        return self.workspace_graph_edit_controller.request_remove_selected_port(key)

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> ControllerResult[bool]:
        return self.workspace_graph_edit_controller.request_delete_selected_graph_items(edge_ids)

    def focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None:
        self.workspace_navigation_controller.focus_failed_node(workspace_id, node_id, error)

    def reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]:
        return self.workspace_navigation_controller.reveal_parent_chain(workspace_id, node_id)

    @staticmethod
    def _custom_workflow_export_label(definition: dict[str, Any]) -> str:
        return WorkspacePackageIOController.custom_workflow_export_label(definition)

    @staticmethod
    def _custom_workflow_default_filename(name: object) -> str:
        return WorkspacePackageIOController.custom_workflow_default_filename(name)

    def import_custom_workflow(self) -> None:
        self.workspace_package_io_controller.import_custom_workflow()

    def export_custom_workflow(self) -> None:
        self.workspace_package_io_controller.export_custom_workflow()

    def _prompt_custom_workflow_export_definition(
        self,
        definitions: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return self.workspace_package_io_controller.prompt_custom_workflow_export_definition(definitions)

    def import_node_package(self) -> None:
        self.workspace_package_io_controller.import_node_package()

    def export_node_package(self) -> None:
        self.workspace_package_io_controller.export_node_package()
