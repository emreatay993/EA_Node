from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


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
        self._connect_shell_signal("node_library_changed", self.node_library_changed.emit)
        self._connect_shell_signal(
            "library_pane_reset_requested",
            self.library_pane_reset_requested.emit,
        )
        self._connect_shell_signal("graph_search_changed", self.graph_search_changed.emit)
        self._connect_shell_signal(
            "connection_quick_insert_changed",
            self.connection_quick_insert_changed.emit,
        )
        self._connect_shell_signal("graph_hint_changed", self.graph_hint_changed.emit)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    def _connect_shell_signal(self, signal_name: str, callback) -> None:  # noqa: ANN001
        shell_window = self._shell_window
        if shell_window is None:
            return
        signal = getattr(shell_window, signal_name, None)
        if signal is not None and hasattr(signal, "connect"):
            signal.connect(callback)

    def _shell_value(self, name: str, default):
        shell_window = self._shell_window
        if shell_window is None:
            return default
        return getattr(shell_window, name, default)

    def _call_shell(self, name: str, *args):
        shell_window = self._shell_window
        if shell_window is None:
            return None
        method = getattr(shell_window, name, None)
        if method is None:
            return None
        return method(*args)

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def grouped_node_library_items(self) -> list[dict[str, Any]]:
        items = self._shell_value("grouped_node_library_items", [])
        return list(items) if isinstance(items, list) else []

    @pyqtProperty(bool, notify=graph_search_changed)
    def graph_search_open(self) -> bool:
        return bool(self._shell_value("graph_search_open", False))

    @pyqtProperty(str, notify=graph_search_changed)
    def graph_search_query(self) -> str:
        return str(self._shell_value("graph_search_query", ""))

    @pyqtProperty("QVariantList", notify=graph_search_changed)
    def graph_search_results(self) -> list[dict[str, Any]]:
        items = self._shell_value("graph_search_results", [])
        return list(items) if isinstance(items, list) else []

    @pyqtProperty(int, notify=graph_search_changed)
    def graph_search_highlight_index(self) -> int:
        return int(self._shell_value("graph_search_highlight_index", -1))

    @pyqtProperty(bool, notify=connection_quick_insert_changed)
    def connection_quick_insert_open(self) -> bool:
        return bool(self._shell_value("connection_quick_insert_open", False))

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_x(self) -> float:
        return float(self._shell_value("connection_quick_insert_overlay_x", 0.0))

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_y(self) -> float:
        return float(self._shell_value("connection_quick_insert_overlay_y", 0.0))

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_source_summary(self) -> str:
        return str(self._shell_value("connection_quick_insert_source_summary", ""))

    @pyqtProperty(bool, notify=connection_quick_insert_changed)
    def connection_quick_insert_is_canvas_mode(self) -> bool:
        return bool(self._shell_value("connection_quick_insert_is_canvas_mode", False))

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_query(self) -> str:
        return str(self._shell_value("connection_quick_insert_query", ""))

    @pyqtProperty("QVariantList", notify=connection_quick_insert_changed)
    def connection_quick_insert_results(self) -> list[dict[str, Any]]:
        items = self._shell_value("connection_quick_insert_results", [])
        return list(items) if isinstance(items, list) else []

    @pyqtProperty(int, notify=connection_quick_insert_changed)
    def connection_quick_insert_highlight_index(self) -> int:
        return int(self._shell_value("connection_quick_insert_highlight_index", -1))

    @pyqtProperty(bool, notify=graph_hint_changed)
    def graph_hint_visible(self) -> bool:
        return bool(self._shell_value("graph_hint_visible", False))

    @pyqtProperty(str, notify=graph_hint_changed)
    def graph_hint_message(self) -> str:
        return str(self._shell_value("graph_hint_message", ""))

    @pyqtSlot(str)
    def set_library_query(self, query: str) -> None:
        self._call_shell("set_library_query", query)

    @pyqtSlot(str)
    def request_add_node_from_library(self, type_id: str) -> None:
        self._call_shell("request_add_node_from_library", type_id)

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def request_rename_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(
            self._call_shell(
                "request_rename_custom_workflow_from_library",
                workflow_id,
                workflow_scope,
            )
        )

    @pyqtSlot(str, str, result=bool)
    def request_set_custom_workflow_scope(self, workflow_id: str, workflow_scope: str) -> bool:
        return bool(self._call_shell("request_set_custom_workflow_scope", workflow_id, workflow_scope))

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def request_delete_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(
            self._call_shell(
                "request_delete_custom_workflow_from_library",
                workflow_id,
                workflow_scope,
            )
        )

    @pyqtSlot(str)
    def set_graph_search_query(self, query: str) -> None:
        self._call_shell("set_graph_search_query", query)

    @pyqtSlot(int)
    def request_graph_search_move(self, delta: int) -> None:
        self._call_shell("request_graph_search_move", delta)

    @pyqtSlot(result=bool)
    def request_graph_search_accept(self) -> bool:
        return bool(self._call_shell("request_graph_search_accept"))

    @pyqtSlot()
    def request_close_graph_search(self) -> None:
        self._call_shell("request_close_graph_search")

    @pyqtSlot(int)
    def request_graph_search_highlight(self, index: int) -> None:
        self._call_shell("request_graph_search_highlight", index)

    @pyqtSlot(int, result=bool)
    def request_graph_search_jump(self, index: int) -> bool:
        return bool(self._call_shell("request_graph_search_jump", index))

    @pyqtSlot(str)
    def set_connection_quick_insert_query(self, query: str) -> None:
        self._call_shell("set_connection_quick_insert_query", query)

    @pyqtSlot(int)
    def request_connection_quick_insert_move(self, delta: int) -> None:
        self._call_shell("request_connection_quick_insert_move", delta)

    @pyqtSlot(result=bool)
    def request_connection_quick_insert_accept(self) -> bool:
        return bool(self._call_shell("request_connection_quick_insert_accept"))

    @pyqtSlot()
    def request_close_connection_quick_insert(self) -> None:
        self._call_shell("request_close_connection_quick_insert")

    @pyqtSlot(int)
    def request_connection_quick_insert_highlight(self, index: int) -> None:
        self._call_shell("request_connection_quick_insert_highlight", index)

    @pyqtSlot(int, result=bool)
    def request_connection_quick_insert_choose(self, index: int) -> bool:
        return bool(self._call_shell("request_connection_quick_insert_choose", index))


__all__ = ["ShellLibraryBridge"]
