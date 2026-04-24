from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import pyqtSlot

from ea_node_editor.ui.pdf_preview_provider import (
    describe_pdf_preview as build_pdf_preview_description,
)

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


@pyqtSlot()
def request_create_workspace(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_create_workspace()


@pyqtSlot()
def request_create_view(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_create_view()


@pyqtSlot(str)
def request_switch_view(self: "ShellWindow", view_id: str) -> None:
    self.shell_workspace_presenter.request_switch_view(view_id)


@pyqtSlot(str, result=bool)
def request_open_subnode_scope(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.graph_canvas_presenter.request_open_subnode_scope(node_id))


@pyqtSlot(str, result=bool)
def request_open_scope_breadcrumb(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_open_scope_breadcrumb(node_id))


@pyqtSlot()
def request_rename_workspace(self: "ShellWindow") -> None:
    self._rename_active_workspace()


@pyqtSlot(str, result=bool)
def request_rename_workspace_by_id(self: "ShellWindow", workspace_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_rename_workspace_by_id(workspace_id))


@pyqtSlot()
def request_duplicate_workspace(self: "ShellWindow") -> None:
    self._duplicate_active_workspace()


@pyqtSlot()
def request_close_workspace(self: "ShellWindow") -> None:
    self._close_active_workspace()


@pyqtSlot(str, result=bool)
def request_close_workspace_by_id(self: "ShellWindow", workspace_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_close_workspace_by_id(workspace_id))


@pyqtSlot(str, result=bool)
def request_close_view(self: "ShellWindow", view_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_close_view(view_id))


@pyqtSlot(str, result=bool)
def request_rename_view(self: "ShellWindow", view_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_rename_view(view_id))


@pyqtSlot(int, int, result=bool)
def request_move_workspace_tab(self: "ShellWindow", from_index: int, to_index: int) -> bool:
    return bool(self.shell_workspace_presenter.request_move_workspace_tab(from_index, to_index))


@pyqtSlot(int, int, result=bool)
def request_move_view_tab(self: "ShellWindow", from_index: int, to_index: int) -> bool:
    return bool(self.shell_workspace_presenter.request_move_view_tab(from_index, to_index))


@pyqtSlot(result=bool)
def request_undo(self: "ShellWindow") -> bool:
    return bool(self._undo())


@pyqtSlot(result=bool)
def request_redo(self: "ShellWindow") -> bool:
    return bool(self._redo())


@pyqtSlot(str, str, str, str, result=bool)
def request_connect_ports(
    self: "ShellWindow",
    node_a_id: str,
    port_a: str,
    node_b_id: str,
    port_b: str,
) -> bool:
    return bool(self.graph_canvas_presenter.request_connect_ports(node_a_id, port_a, node_b_id, port_b))


@pyqtSlot(str, result=bool)
def request_remove_edge(self: "ShellWindow", edge_id: str) -> bool:
    return bool(self.workspace_library_controller.request_remove_edge(edge_id).payload)


@pyqtSlot(str, result=bool)
def request_ungroup_node(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.workspace_library_controller.request_ungroup_node(node_id).payload)


@pyqtSlot(str, result=bool)
def request_remove_node(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.workspace_library_controller.request_remove_node(node_id).payload)


@pyqtSlot(str, result=str)
def request_add_selected_subnode_pin(self: "ShellWindow", direction: str) -> str:
    return self.shell_inspector_presenter.request_add_selected_subnode_pin(direction)


@pyqtSlot(str, result=bool)
def request_rename_node(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.workspace_library_controller.request_rename_node(node_id).payload)


@pyqtSlot(str, result=bool)
def request_rename_selected_port(self: "ShellWindow", key: str) -> bool:
    return bool(self.workspace_library_controller.request_rename_selected_port(key).payload)


@pyqtSlot(str, result=bool)
def request_remove_selected_port(self: "ShellWindow", key: str) -> bool:
    return bool(self.workspace_library_controller.request_remove_selected_port(key).payload)


@pyqtSlot(str, "QVariant")
def set_selected_node_property(self: "ShellWindow", key: str, value: Any) -> None:
    self.shell_inspector_presenter.set_selected_node_property(key, value)


@pyqtSlot(str, "QVariant", result="QVariantMap")
def describe_pdf_preview(self: "ShellWindow", source: str, page_number: Any) -> dict[str, Any]:
    return build_pdf_preview_description(source, page_number)


@pyqtSlot(str, str, result=str)
def browse_selected_node_property_path(self: "ShellWindow", key: str, current_path: str) -> str:
    return self.shell_inspector_presenter.browse_selected_node_property_path(key, current_path)


@pyqtSlot(str, str, result=str)
def pick_selected_node_property_color(self: "ShellWindow", key: str, current_value: str) -> str:
    return self.shell_inspector_presenter.pick_selected_node_property_color(key, current_value)


@pyqtSlot(str, str, str, result=str)
def browse_node_property_path(self: "ShellWindow", node_id: str, key: str, current_path: str) -> str:
    return self.graph_canvas_presenter.browse_node_property_path(node_id, key, current_path)


@pyqtSlot(str, str, str, result=str)
def pick_node_property_color(self: "ShellWindow", node_id: str, key: str, current_value: str) -> str:
    return self.graph_canvas_presenter.pick_node_property_color(node_id, key, current_value)


def _browse_property_path_dialog(self: "ShellWindow", property_label: str, current_path: str) -> str:
    return self.shell_host_presenter.browse_property_path_dialog(property_label, current_path)


def _pick_property_color_dialog(self: "ShellWindow", property_label: str, current_value: str) -> str:
    return self.shell_host_presenter.pick_property_color_dialog(property_label, current_value)


def _repair_property_path_dialog(
    self: "ShellWindow",
    *,
    node_type_id: str,
    property_key: str,
    property_label: str,
    current_path: str,
) -> str:
    return self.shell_host_presenter.repair_property_path_dialog(
        node_type_id=node_type_id,
        property_key=property_key,
        property_label=property_label,
        current_path=current_path,
    )


@pyqtSlot(str, bool)
def set_selected_port_exposed(self: "ShellWindow", key: str, exposed: bool) -> None:
    self.shell_inspector_presenter.set_selected_port_exposed(key, exposed)


@pyqtSlot(str, str, result=bool)
def set_selected_port_label(self: "ShellWindow", key: str, label: str) -> bool:
    return bool(self.shell_inspector_presenter.set_selected_port_label(key, label))


@pyqtSlot(bool)
def set_selected_node_collapsed(self: "ShellWindow", collapsed: bool) -> None:
    self.shell_inspector_presenter.set_selected_node_collapsed(collapsed)


def _switch_workspace_by_offset(self: "ShellWindow", offset):
    return self.workspace_library_controller.switch_workspace_by_offset(offset)


def _refresh_workspace_tabs(self: "ShellWindow"):
    return self.workspace_library_controller.refresh_workspace_tabs()


def _switch_workspace(self: "ShellWindow", workspace_id):
    return self.workspace_library_controller.switch_workspace(workspace_id)


def _save_active_view_state(self: "ShellWindow"):
    return self.workspace_library_controller.save_active_view_state()


def _restore_active_view_state(self: "ShellWindow"):
    return self.workspace_library_controller.restore_active_view_state()


def _visible_scene_rect(self: "ShellWindow"):
    return self.workspace_library_controller.visible_scene_rect()


def _current_workspace_scene_bounds(self: "ShellWindow"):
    return self.workspace_library_controller.current_workspace_scene_bounds()


def _selection_bounds(self: "ShellWindow"):
    return self.workspace_library_controller.selection_bounds()


def _frame_all(self: "ShellWindow"):
    return self.workspace_library_controller.frame_all()


def _frame_selection(self: "ShellWindow"):
    return self.workspace_library_controller.frame_selection()


def _frame_node(self: "ShellWindow", node_id):
    return self.workspace_library_controller.frame_node(node_id)


def _center_on_node(self: "ShellWindow", node_id):
    return self.workspace_library_controller.center_on_node(node_id)


def _center_on_selection(self: "ShellWindow"):
    return self.workspace_library_controller.center_on_selection()


def _search_graph_nodes(self: "ShellWindow", query, limit=10, enabled_scopes=None):
    return self.workspace_library_controller.search_graph_nodes(
        query,
        limit,
        enabled_scopes=enabled_scopes,
    )


def _jump_to_graph_node(self: "ShellWindow", workspace_id, node_id):
    return self.workspace_library_controller.jump_to_graph_node(workspace_id, node_id)


def _create_view(self: "ShellWindow"):
    return self.workspace_library_controller.create_view()


def _switch_view(self: "ShellWindow", view_id):
    return self.workspace_library_controller.switch_view(view_id)


def _rename_view(self: "ShellWindow", view_id):
    return self.workspace_library_controller.rename_view(view_id)


def _create_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.create_workspace()


def _rename_active_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.rename_active_workspace()


def _duplicate_active_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.duplicate_active_workspace()


def _close_active_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.close_active_workspace()


def _on_workspace_tab_changed(self: "ShellWindow", index):
    return self.workspace_library_controller.on_workspace_tab_changed(index)


def _on_workspace_tab_close(self: "ShellWindow", index):
    return self.workspace_library_controller.on_workspace_tab_close(index)


def _add_node_from_library(self: "ShellWindow", type_id):
    return self.workspace_library_controller.add_node_from_library(type_id)


def _insert_library_node(self: "ShellWindow", type_id, x, y):
    return self.workspace_library_controller.insert_library_node(type_id, x, y)


def _active_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.active_workspace()


def _prompt_connection_candidate(self: "ShellWindow", *, title, label, candidates):
    return self.workspace_library_controller.prompt_connection_candidate(
        title=title,
        label=label,
        candidates=candidates,
    )


def _auto_connect_dropped_node_to_port(
    self: "ShellWindow",
    new_node_id,
    target_node_id,
    target_port_key,
):
    return self.workspace_library_controller.auto_connect_dropped_node_to_port(
        new_node_id,
        target_node_id,
        target_port_key,
    )


def _auto_connect_dropped_node_to_edge(self: "ShellWindow", new_node_id, target_edge_id):
    return self.workspace_library_controller.auto_connect_dropped_node_to_edge(new_node_id, target_edge_id)


def _on_scene_node_selected(self: "ShellWindow", node_id):
    return self.workspace_library_controller.on_scene_node_selected(node_id)


def _on_node_property_changed(self: "ShellWindow", node_id, key, value):
    return self.workspace_library_controller.on_node_property_changed(node_id, key, value)


def _on_port_exposed_changed(self: "ShellWindow", node_id, key, exposed):
    return self.workspace_library_controller.on_port_exposed_changed(node_id, key, exposed)


def _on_node_collapse_changed(self: "ShellWindow", node_id, collapsed):
    return self.workspace_library_controller.on_node_collapse_changed(node_id, collapsed)


def _undo(self: "ShellWindow"):
    return self.workspace_library_controller.undo()


def _redo(self: "ShellWindow"):
    return self.workspace_library_controller.redo()


def _selected_node_context(self: "ShellWindow"):
    return self.workspace_library_controller.selected_node_context()


def _active_workspace_data(self: "ShellWindow"):
    return self.shell_host_presenter._active_workspace_data()


def _passive_node_context(self: "ShellWindow", node_id: str):
    return self.shell_host_presenter._passive_node_context(node_id)


def _flow_edge_context(self: "ShellWindow", edge_id: str):
    return self.shell_host_presenter._flow_edge_context(edge_id)


def _reveal_parent_chain(self: "ShellWindow", workspace_id, node_id):
    return self.workspace_library_controller.reveal_parent_chain(workspace_id, node_id)


def _import_custom_workflow(self: "ShellWindow"):
    return self.workspace_library_controller.import_custom_workflow()


def _export_custom_workflow(self: "ShellWindow"):
    return self.workspace_library_controller.export_custom_workflow()


def _import_node_package(self: "ShellWindow"):
    return self.workspace_library_controller.import_node_package()


def _export_node_package(self: "ShellWindow"):
    return self.workspace_library_controller.export_node_package()


_PROPERTY_EXPORTS = set()
_FORCE_BIND_NAMES = set()
_PRIVATE_EXPORT_NAMES = {"_exported_names", "_should_bind"}


def _exported_names() -> list[str]:
    names = set(_PROPERTY_EXPORTS)
    for name, value in globals().items():
        if name in _PRIVATE_EXPORT_NAMES:
            continue
        if not inspect.isfunction(value) or getattr(value, "__module__", None) != __name__:
            continue
        if name.startswith("_get_"):
            continue
        if name.startswith("_set_") and name not in _FORCE_BIND_NAMES:
            continue
        names.add(name)
    return sorted(names)


def _should_bind(name: str, value: object) -> bool:
    if name in _FORCE_BIND_NAMES:
        return True
    if name.startswith("_qt_") or name.startswith("_get_") or name.startswith("_set_"):
        return False
    return inspect.isfunction(value) or isinstance(value, property)


__all__ = _exported_names()
WINDOW_STATE_FACADE_BINDINGS = {
    name: globals()[name]
    for name in __all__
    if _should_bind(name, globals()[name])
}
