from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _source_attr(source: object | None, name: str, default: Any) -> Any:
    if source is None:
        return default
    return getattr(source, name, default)


def _invoke(source: object | None, name: str, *args, default: Any = None) -> Any:
    callback = getattr(source, name, None) if source is not None else None
    if not callable(callback):
        return default
    return callback(*args)


def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
    signal = getattr(source, name, None) if source is not None else None
    if signal is not None and hasattr(signal, "connect"):
        signal.connect(slot)


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
        self._library_source = getattr(shell_window, "shell_library_presenter", shell_window)

        _connect_signal(self._library_source, "node_library_changed", self.node_library_changed.emit)
        _connect_signal(
            self._library_source,
            "library_pane_reset_requested",
            self.library_pane_reset_requested.emit,
        )
        _connect_signal(self._library_source, "graph_search_changed", self.graph_search_changed.emit)
        _connect_signal(
            self._library_source,
            "connection_quick_insert_changed",
            self.connection_quick_insert_changed.emit,
        )
        _connect_signal(self._library_source, "graph_hint_changed", self.graph_hint_changed.emit)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def grouped_node_library_items(self) -> list[dict[str, Any]]:
        return _copy_list(_source_attr(self._library_source, "grouped_node_library_items", []))

    @pyqtProperty(bool, notify=graph_search_changed)
    def graph_search_open(self) -> bool:
        return bool(_source_attr(self._library_source, "graph_search_open", False))

    @pyqtProperty(str, notify=graph_search_changed)
    def graph_search_query(self) -> str:
        return str(_source_attr(self._library_source, "graph_search_query", ""))

    @pyqtProperty("QVariantList", notify=graph_search_changed)
    def graph_search_results(self) -> list[dict[str, Any]]:
        return _copy_list(_source_attr(self._library_source, "graph_search_results", []))

    @pyqtProperty(int, notify=graph_search_changed)
    def graph_search_highlight_index(self) -> int:
        return int(_source_attr(self._library_source, "graph_search_highlight_index", -1))

    @pyqtProperty(bool, notify=connection_quick_insert_changed)
    def connection_quick_insert_open(self) -> bool:
        return bool(_source_attr(self._library_source, "connection_quick_insert_open", False))

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_x(self) -> float:
        return float(_source_attr(self._library_source, "connection_quick_insert_overlay_x", 0.0))

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_y(self) -> float:
        return float(_source_attr(self._library_source, "connection_quick_insert_overlay_y", 0.0))

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_source_summary(self) -> str:
        return str(_source_attr(self._library_source, "connection_quick_insert_source_summary", ""))

    @pyqtProperty(bool, notify=connection_quick_insert_changed)
    def connection_quick_insert_is_canvas_mode(self) -> bool:
        return bool(_source_attr(self._library_source, "connection_quick_insert_is_canvas_mode", False))

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_query(self) -> str:
        return str(_source_attr(self._library_source, "connection_quick_insert_query", ""))

    @pyqtProperty("QVariantList", notify=connection_quick_insert_changed)
    def connection_quick_insert_results(self) -> list[dict[str, Any]]:
        return _copy_list(_source_attr(self._library_source, "connection_quick_insert_results", []))

    @pyqtProperty(int, notify=connection_quick_insert_changed)
    def connection_quick_insert_highlight_index(self) -> int:
        return int(_source_attr(self._library_source, "connection_quick_insert_highlight_index", -1))

    @pyqtProperty(bool, notify=graph_hint_changed)
    def graph_hint_visible(self) -> bool:
        return bool(_source_attr(self._library_source, "graph_hint_visible", False))

    @pyqtProperty(str, notify=graph_hint_changed)
    def graph_hint_message(self) -> str:
        return str(_source_attr(self._library_source, "graph_hint_message", ""))

    @pyqtSlot(str)
    def set_library_query(self, query: str) -> None:
        _invoke(self._library_source, "set_library_query", query)

    @pyqtSlot(str)
    def request_add_node_from_library(self, type_id: str) -> None:
        _invoke(self._library_source, "request_add_node_from_library", type_id)

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def request_rename_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(
            _invoke(
                self._library_source,
                "request_rename_custom_workflow_from_library",
                workflow_id,
                workflow_scope,
                default=False,
            )
        )

    @pyqtSlot(str, str, result=bool)
    def request_set_custom_workflow_scope(self, workflow_id: str, workflow_scope: str) -> bool:
        return bool(
            _invoke(
                self._library_source,
                "request_set_custom_workflow_scope",
                workflow_id,
                workflow_scope,
                default=False,
            )
        )

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def request_delete_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(
            _invoke(
                self._library_source,
                "request_delete_custom_workflow_from_library",
                workflow_id,
                workflow_scope,
                default=False,
            )
        )

    @pyqtSlot(str)
    def set_graph_search_query(self, query: str) -> None:
        _invoke(self._library_source, "set_graph_search_query", query)

    @pyqtSlot(int)
    def request_graph_search_move(self, delta: int) -> None:
        _invoke(self._library_source, "request_graph_search_move", delta)

    @pyqtSlot(result=bool)
    def request_graph_search_accept(self) -> bool:
        return bool(_invoke(self._library_source, "request_graph_search_accept", default=False))

    @pyqtSlot()
    def request_close_graph_search(self) -> None:
        _invoke(self._library_source, "request_close_graph_search")

    @pyqtSlot(int)
    def request_graph_search_highlight(self, index: int) -> None:
        _invoke(self._library_source, "request_graph_search_highlight", index)

    @pyqtSlot(int, result=bool)
    def request_graph_search_jump(self, index: int) -> bool:
        return bool(_invoke(self._library_source, "request_graph_search_jump", index, default=False))

    @pyqtSlot(str)
    def set_connection_quick_insert_query(self, query: str) -> None:
        _invoke(self._library_source, "set_connection_quick_insert_query", query)

    @pyqtSlot(int)
    def request_connection_quick_insert_move(self, delta: int) -> None:
        _invoke(self._library_source, "request_connection_quick_insert_move", delta)

    @pyqtSlot(result=bool)
    def request_connection_quick_insert_accept(self) -> bool:
        return bool(
            _invoke(self._library_source, "request_connection_quick_insert_accept", default=False)
        )

    @pyqtSlot()
    def request_close_connection_quick_insert(self) -> None:
        _invoke(self._library_source, "request_close_connection_quick_insert")

    @pyqtSlot(int)
    def request_connection_quick_insert_highlight(self, index: int) -> None:
        _invoke(self._library_source, "request_connection_quick_insert_highlight", index)

    @pyqtSlot(int, result=bool)
    def request_connection_quick_insert_choose(self, index: int) -> bool:
        return bool(
            _invoke(self._library_source, "request_connection_quick_insert_choose", index, default=False)
        )


__all__ = ["ShellLibraryBridge"]
