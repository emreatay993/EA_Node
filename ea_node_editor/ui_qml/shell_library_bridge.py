from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


class ShellLibraryBridge(QObject):
    node_library_changed = pyqtSignal()
    library_pane_reset_requested = pyqtSignal(name="libraryPaneResetRequested")
    graph_search_changed = pyqtSignal()
    connection_quick_insert_changed = pyqtSignal()
    graph_hint_changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: "ShellWindow | None" = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window

        self._grouped_node_library_items: Callable[[], list[dict[str, Any]]] = lambda: []
        self._graph_search_open: Callable[[], bool] = lambda: False
        self._graph_search_query: Callable[[], str] = lambda: ""
        self._graph_search_results: Callable[[], list[dict[str, Any]]] = lambda: []
        self._graph_search_highlight_index: Callable[[], int] = lambda: -1
        self._connection_quick_insert_open: Callable[[], bool] = lambda: False
        self._connection_quick_insert_overlay_x: Callable[[], float] = lambda: 0.0
        self._connection_quick_insert_overlay_y: Callable[[], float] = lambda: 0.0
        self._connection_quick_insert_source_summary: Callable[[], str] = lambda: ""
        self._connection_quick_insert_is_canvas_mode: Callable[[], bool] = lambda: False
        self._connection_quick_insert_query: Callable[[], str] = lambda: ""
        self._connection_quick_insert_results: Callable[[], list[dict[str, Any]]] = lambda: []
        self._connection_quick_insert_highlight_index: Callable[[], int] = lambda: -1
        self._graph_hint_visible: Callable[[], bool] = lambda: False
        self._graph_hint_message: Callable[[], str] = lambda: ""

        self._set_library_query: Callable[[str], None] = lambda _query: None
        self._request_add_node_from_library: Callable[[str], None] = lambda _type_id: None
        self._request_rename_custom_workflow_from_library: Callable[[str, str], bool] = (
            lambda _workflow_id, _workflow_scope: False
        )
        self._request_set_custom_workflow_scope: Callable[[str, str], bool] = (
            lambda _workflow_id, _workflow_scope: False
        )
        self._request_delete_custom_workflow_from_library: Callable[[str, str], bool] = (
            lambda _workflow_id, _workflow_scope: False
        )
        self._set_graph_search_query: Callable[[str], None] = lambda _query: None
        self._request_graph_search_move: Callable[[int], None] = lambda _delta: None
        self._request_graph_search_accept: Callable[[], bool] = lambda: False
        self._request_close_graph_search: Callable[[], None] = lambda: None
        self._request_graph_search_highlight: Callable[[int], None] = lambda _index: None
        self._request_graph_search_jump: Callable[[int], bool] = lambda _index: False
        self._set_connection_quick_insert_query: Callable[[str], None] = lambda _query: None
        self._request_connection_quick_insert_move: Callable[[int], None] = lambda _delta: None
        self._request_connection_quick_insert_accept: Callable[[], bool] = lambda: False
        self._request_close_connection_quick_insert: Callable[[], None] = lambda: None
        self._request_connection_quick_insert_highlight: Callable[[int], None] = lambda _index: None
        self._request_connection_quick_insert_choose: Callable[[int], bool] = lambda _index: False

        if shell_window is not None:
            # Capture the shell-facing contract once so the bridge avoids string-based dispatch.
            self._grouped_node_library_items = lambda: _copy_list(shell_window.grouped_node_library_items)
            self._graph_search_open = lambda: bool(shell_window.graph_search_open)
            self._graph_search_query = lambda: str(shell_window.graph_search_query)
            self._graph_search_results = lambda: _copy_list(shell_window.graph_search_results)
            self._graph_search_highlight_index = lambda: int(shell_window.graph_search_highlight_index)
            self._connection_quick_insert_open = lambda: bool(shell_window.connection_quick_insert_open)
            self._connection_quick_insert_overlay_x = lambda: float(shell_window.connection_quick_insert_overlay_x)
            self._connection_quick_insert_overlay_y = lambda: float(shell_window.connection_quick_insert_overlay_y)
            self._connection_quick_insert_source_summary = (
                lambda: str(shell_window.connection_quick_insert_source_summary)
            )
            self._connection_quick_insert_is_canvas_mode = (
                lambda: bool(shell_window.connection_quick_insert_is_canvas_mode)
            )
            self._connection_quick_insert_query = lambda: str(shell_window.connection_quick_insert_query)
            self._connection_quick_insert_results = (
                lambda: _copy_list(shell_window.connection_quick_insert_results)
            )
            self._connection_quick_insert_highlight_index = (
                lambda: int(shell_window.connection_quick_insert_highlight_index)
            )
            self._graph_hint_visible = lambda: bool(shell_window.graph_hint_visible)
            self._graph_hint_message = lambda: str(shell_window.graph_hint_message)

            self._set_library_query = shell_window.set_library_query
            self._request_add_node_from_library = shell_window.request_add_node_from_library
            self._request_rename_custom_workflow_from_library = (
                shell_window.request_rename_custom_workflow_from_library
            )
            self._request_set_custom_workflow_scope = shell_window.request_set_custom_workflow_scope
            self._request_delete_custom_workflow_from_library = (
                shell_window.request_delete_custom_workflow_from_library
            )
            self._set_graph_search_query = shell_window.set_graph_search_query
            self._request_graph_search_move = shell_window.request_graph_search_move
            self._request_graph_search_accept = shell_window.request_graph_search_accept
            self._request_close_graph_search = shell_window.request_close_graph_search
            self._request_graph_search_highlight = shell_window.request_graph_search_highlight
            self._request_graph_search_jump = shell_window.request_graph_search_jump
            self._set_connection_quick_insert_query = shell_window.set_connection_quick_insert_query
            self._request_connection_quick_insert_move = shell_window.request_connection_quick_insert_move
            self._request_connection_quick_insert_accept = shell_window.request_connection_quick_insert_accept
            self._request_close_connection_quick_insert = shell_window.request_close_connection_quick_insert
            self._request_connection_quick_insert_highlight = (
                shell_window.request_connection_quick_insert_highlight
            )
            self._request_connection_quick_insert_choose = shell_window.request_connection_quick_insert_choose

            shell_window.node_library_changed.connect(self.node_library_changed.emit)
            shell_window.library_pane_reset_requested.connect(self.library_pane_reset_requested.emit)
            shell_window.graph_search_changed.connect(self.graph_search_changed.emit)
            shell_window.connection_quick_insert_changed.connect(self.connection_quick_insert_changed.emit)
            shell_window.graph_hint_changed.connect(self.graph_hint_changed.emit)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def grouped_node_library_items(self) -> list[dict[str, Any]]:
        return self._grouped_node_library_items()

    @pyqtProperty(bool, notify=graph_search_changed)
    def graph_search_open(self) -> bool:
        return self._graph_search_open()

    @pyqtProperty(str, notify=graph_search_changed)
    def graph_search_query(self) -> str:
        return self._graph_search_query()

    @pyqtProperty("QVariantList", notify=graph_search_changed)
    def graph_search_results(self) -> list[dict[str, Any]]:
        return self._graph_search_results()

    @pyqtProperty(int, notify=graph_search_changed)
    def graph_search_highlight_index(self) -> int:
        return self._graph_search_highlight_index()

    @pyqtProperty(bool, notify=connection_quick_insert_changed)
    def connection_quick_insert_open(self) -> bool:
        return self._connection_quick_insert_open()

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_x(self) -> float:
        return self._connection_quick_insert_overlay_x()

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_y(self) -> float:
        return self._connection_quick_insert_overlay_y()

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_source_summary(self) -> str:
        return self._connection_quick_insert_source_summary()

    @pyqtProperty(bool, notify=connection_quick_insert_changed)
    def connection_quick_insert_is_canvas_mode(self) -> bool:
        return self._connection_quick_insert_is_canvas_mode()

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_query(self) -> str:
        return self._connection_quick_insert_query()

    @pyqtProperty("QVariantList", notify=connection_quick_insert_changed)
    def connection_quick_insert_results(self) -> list[dict[str, Any]]:
        return self._connection_quick_insert_results()

    @pyqtProperty(int, notify=connection_quick_insert_changed)
    def connection_quick_insert_highlight_index(self) -> int:
        return self._connection_quick_insert_highlight_index()

    @pyqtProperty(bool, notify=graph_hint_changed)
    def graph_hint_visible(self) -> bool:
        return self._graph_hint_visible()

    @pyqtProperty(str, notify=graph_hint_changed)
    def graph_hint_message(self) -> str:
        return self._graph_hint_message()

    @pyqtSlot(str)
    def set_library_query(self, query: str) -> None:
        self._set_library_query(query)

    @pyqtSlot(str)
    def request_add_node_from_library(self, type_id: str) -> None:
        self._request_add_node_from_library(type_id)

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def request_rename_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(self._request_rename_custom_workflow_from_library(workflow_id, workflow_scope))

    @pyqtSlot(str, str, result=bool)
    def request_set_custom_workflow_scope(self, workflow_id: str, workflow_scope: str) -> bool:
        return bool(self._request_set_custom_workflow_scope(workflow_id, workflow_scope))

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def request_delete_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(self._request_delete_custom_workflow_from_library(workflow_id, workflow_scope))

    @pyqtSlot(str)
    def set_graph_search_query(self, query: str) -> None:
        self._set_graph_search_query(query)

    @pyqtSlot(int)
    def request_graph_search_move(self, delta: int) -> None:
        self._request_graph_search_move(delta)

    @pyqtSlot(result=bool)
    def request_graph_search_accept(self) -> bool:
        return bool(self._request_graph_search_accept())

    @pyqtSlot()
    def request_close_graph_search(self) -> None:
        self._request_close_graph_search()

    @pyqtSlot(int)
    def request_graph_search_highlight(self, index: int) -> None:
        self._request_graph_search_highlight(index)

    @pyqtSlot(int, result=bool)
    def request_graph_search_jump(self, index: int) -> bool:
        return bool(self._request_graph_search_jump(index))

    @pyqtSlot(str)
    def set_connection_quick_insert_query(self, query: str) -> None:
        self._set_connection_quick_insert_query(query)

    @pyqtSlot(int)
    def request_connection_quick_insert_move(self, delta: int) -> None:
        self._request_connection_quick_insert_move(delta)

    @pyqtSlot(result=bool)
    def request_connection_quick_insert_accept(self) -> bool:
        return bool(self._request_connection_quick_insert_accept())

    @pyqtSlot()
    def request_close_connection_quick_insert(self) -> None:
        self._request_close_connection_quick_insert()

    @pyqtSlot(int)
    def request_connection_quick_insert_highlight(self, index: int) -> None:
        self._request_connection_quick_insert_highlight(index)

    @pyqtSlot(int, result=bool)
    def request_connection_quick_insert_choose(self, index: int) -> bool:
        return bool(self._request_connection_quick_insert_choose(index))


__all__ = ["ShellLibraryBridge"]
