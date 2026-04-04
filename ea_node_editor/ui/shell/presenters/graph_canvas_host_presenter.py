from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject

from ea_node_editor.ui.pdf_preview_provider import describe_pdf_preview

from .contracts import _GraphCanvasHostPresenterHostProtocol, _presenter_parent


class GraphCanvasHostPresenter(QObject):
    def __init__(
        self,
        host: _GraphCanvasHostPresenterHostProtocol,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(_presenter_parent(host, parent))
        self._host = host

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:
        result = self._host.workspace_library_controller.request_delete_selected_graph_items(edge_ids)
        return bool(result.payload)

    def request_navigate_scope_parent(self) -> bool:
        return bool(self._host.search_scope_controller.navigate_scope(self._host.scene.navigate_scope_parent))

    def request_navigate_scope_root(self) -> bool:
        return bool(self._host.search_scope_controller.navigate_scope(self._host.scene.navigate_scope_root))

    def set_graph_cursor_shape(self, cursor_shape: int) -> None:
        self._host.shell_host_presenter.set_graph_cursor_shape(cursor_shape)

    def clear_graph_cursor_shape(self) -> None:
        self._host.shell_host_presenter.clear_graph_cursor_shape()

    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]:
        return describe_pdf_preview(source, page_number)

    def request_edit_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_edit_flow_edge_style(edge_id))

    def request_edit_flow_edge_label(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_edit_flow_edge_label(edge_id))

    def request_reset_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_reset_flow_edge_style(edge_id))

    def request_copy_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_copy_flow_edge_style(edge_id))

    def request_paste_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_paste_flow_edge_style(edge_id))

    def request_remove_edge(self, edge_id: str) -> bool:
        result = self._host.workspace_library_controller.request_remove_edge(edge_id)
        return bool(result.payload)

    def request_edit_passive_node_style(self, node_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_edit_passive_node_style(node_id))

    def request_reset_passive_node_style(self, node_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_reset_passive_node_style(node_id))

    def request_copy_passive_node_style(self, node_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_copy_passive_node_style(node_id))

    def request_paste_passive_node_style(self, node_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_paste_passive_node_style(node_id))

    def request_rename_node(self, node_id: str) -> bool:
        result = self._host.workspace_library_controller.request_rename_node(node_id)
        return bool(result.payload)

    def request_ungroup_node(self, node_id: str) -> bool:
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return False
        self._host.scene.select_node(normalized_node_id)
        return bool(self._host.workspace_library_controller.ungroup_selected_nodes())

    def request_remove_node(self, node_id: str) -> bool:
        result = self._host.workspace_library_controller.request_remove_node(node_id)
        return bool(result.payload)


__all__ = ["GraphCanvasHostPresenter"]
