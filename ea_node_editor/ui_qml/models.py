from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot


class StatusItemModel(QObject):
    changed = pyqtSignal()

    def __init__(self, icon: str, text: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._icon = icon
        self._text = text

    def set_icon(self, value: str) -> None:
        if self._icon == value:
            return
        self._icon = value
        self.changed.emit()

    def set_text(self, value: str) -> None:
        if self._text == value:
            return
        self._text = value
        self.changed.emit()

    def icon(self) -> str:
        return self._icon

    def text(self) -> str:
        return self._text

    @pyqtProperty(str, notify=changed)
    def icon_value(self) -> str:
        return self._icon

    @pyqtProperty(str, notify=changed)
    def text_value(self) -> str:
        return self._text


class ConsoleModel(QObject):
    output_changed = pyqtSignal()
    errors_changed = pyqtSignal()
    warnings_changed = pyqtSignal()
    counts_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._output_lines: list[str] = []
        self._error_lines: list[str] = []
        self._warning_lines: list[str] = []

    @property
    def warning_count(self) -> int:
        return len(self._warning_lines)

    @property
    def error_count(self) -> int:
        return len(self._error_lines)

    @pyqtProperty(str, notify=output_changed)
    def output_text(self) -> str:
        return "\n".join(self._output_lines)

    @pyqtProperty(str, notify=errors_changed)
    def errors_text(self) -> str:
        return "\n".join(self._error_lines)

    @pyqtProperty(str, notify=warnings_changed)
    def warnings_text(self) -> str:
        return "\n".join(self._warning_lines)

    @pyqtProperty(int, notify=counts_changed)
    def warning_count_value(self) -> int:
        return self.warning_count

    @pyqtProperty(int, notify=counts_changed)
    def error_count_value(self) -> int:
        return self.error_count

    @pyqtSlot()
    def clear_all(self) -> None:
        self._output_lines.clear()
        self._error_lines.clear()
        self._warning_lines.clear()
        self.output_changed.emit()
        self.errors_changed.emit()
        self.warnings_changed.emit()
        self.counts_changed.emit()

    def append_log(self, level: str, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        normalized_level = str(level).lower()
        line = f"[{stamp}] [{normalized_level.upper()}] {message}"
        self._output_lines.append(line)
        self.output_changed.emit()

        if normalized_level == "warning":
            self._warning_lines.append(line)
            self.warnings_changed.emit()
            self.counts_changed.emit()
        elif normalized_level == "error":
            self._error_lines.append(line)
            self.errors_changed.emit()
            self.counts_changed.emit()


class ScriptEditorModel(QObject):
    visibility_changed = pyqtSignal()
    node_changed = pyqtSignal()
    content_changed = pyqtSignal()
    cursor_changed = pyqtSignal()
    dirty_changed = pyqtSignal()
    focus_changed = pyqtSignal()
    script_apply_requested = pyqtSignal(str, str, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._visible = False
        self._floating = False
        self._current_node_id = ""
        self._base_script = ""
        self._script_text = ""
        self._dirty = False
        self._cursor_label = "Ln 1, Col 1 | Sel 0 | Pos 0"
        self._has_focus = False

    @pyqtProperty(bool, notify=visibility_changed)
    def visible(self) -> bool:
        return self._visible

    @pyqtProperty(bool, notify=visibility_changed)
    def floating(self) -> bool:
        return self._floating

    @pyqtProperty(str, notify=node_changed)
    def current_node_id(self) -> str:
        return self._current_node_id

    @pyqtProperty(str, notify=content_changed)
    def script_text(self) -> str:
        return self._script_text

    @pyqtProperty(bool, notify=dirty_changed)
    def dirty(self) -> bool:
        return self._dirty

    @pyqtProperty(str, notify=cursor_changed)
    def cursor_label(self) -> str:
        return self._cursor_label

    @pyqtProperty(bool, notify=focus_changed)
    def has_focus(self) -> bool:
        return self._has_focus

    def set_visible(self, visible: bool) -> None:
        visible = bool(visible)
        if self._visible == visible:
            return
        self._visible = visible
        if not visible:
            self._has_focus = False
            self.focus_changed.emit()
        self.visibility_changed.emit()

    def set_floating(self, floating: bool) -> None:
        floating = bool(floating)
        if self._floating == floating:
            return
        self._floating = floating
        self.visibility_changed.emit()

    def set_node(self, node: Any | None) -> None:
        if node is None or getattr(node, "type_id", "") != "core.python_script":
            self._current_node_id = ""
            self._base_script = ""
            self._set_script_text_internal("")
            self._set_dirty(False)
            self._set_focus(False)
            self.node_changed.emit()
            return

        script = str(getattr(node, "properties", {}).get("script", ""))
        self._current_node_id = str(getattr(node, "node_id", ""))
        self._base_script = script
        self._set_script_text_internal(script)
        self._set_dirty(False)
        self.node_changed.emit()

    @pyqtSlot(str)
    def set_script_text(self, text: str) -> None:
        self._set_script_text_internal(str(text))
        self._set_dirty(bool(self._current_node_id and self._script_text != self._base_script))

    @pyqtSlot()
    def apply(self) -> None:
        if not self._current_node_id:
            return
        self._base_script = self._script_text
        self._set_dirty(False)
        self.script_apply_requested.emit(self._current_node_id, "script", self._script_text)
        self.focus_editor()

    @pyqtSlot()
    def revert(self) -> None:
        if not self._current_node_id:
            return
        self._set_script_text_internal(self._base_script)
        self._set_dirty(False)
        self.focus_editor()

    def focus_editor(self) -> bool:
        active = self._visible and bool(self._current_node_id)
        self._set_focus(active)
        return self._has_focus

    @pyqtSlot(int, int, int, int)
    def set_cursor_metrics(self, line: int, column: int, position: int, selection: int) -> None:
        label = f"Ln {line}, Col {column} | Sel {selection} | Pos {position}"
        if self._cursor_label == label:
            return
        self._cursor_label = label
        self.cursor_changed.emit()

    def _set_focus(self, focused: bool) -> None:
        focused = bool(focused)
        if self._has_focus == focused:
            return
        self._has_focus = focused
        self.focus_changed.emit()

    def _set_dirty(self, dirty: bool) -> None:
        dirty = bool(dirty)
        if self._dirty == dirty:
            return
        self._dirty = dirty
        self.dirty_changed.emit()

    def _set_script_text_internal(self, value: str) -> None:
        if self._script_text == value:
            return
        self._script_text = value
        self.content_changed.emit()


class WorkspaceTabsModel(QObject):
    tabs_changed = pyqtSignal()
    current_index_changed = pyqtSignal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tabs: list[dict[str, Any]] = []
        self._current_index = -1

    @pyqtProperty("QVariantList", notify=tabs_changed)
    def tabs(self) -> list[dict[str, Any]]:
        return list(self._tabs)

    @pyqtProperty(int, notify=current_index_changed)
    def current_index(self) -> int:
        return self._current_index

    def set_tabs(self, tabs: list[dict[str, Any]], current_workspace_id: str) -> None:
        previous_index = self._current_index
        self._tabs = list(tabs)
        next_index = -1
        for index, tab in enumerate(self._tabs):
            if tab.get("workspace_id") == current_workspace_id:
                next_index = index
                break
        self._current_index = next_index
        self.tabs_changed.emit()
        if self._current_index != previous_index:
            self.current_index_changed.emit(self._current_index)

    def count(self) -> int:
        return len(self._tabs)

    def currentIndex(self) -> int:
        return self._current_index

    def setCurrentIndex(self, index: int) -> None:
        if index < 0 or index >= len(self._tabs):
            return
        if self._current_index == index:
            return
        self._current_index = index
        self.current_index_changed.emit(index)

    def tabData(self, index: int) -> str:
        if index < 0 or index >= len(self._tabs):
            return ""
        return str(self._tabs[index].get("workspace_id", ""))

    @pyqtSlot(int)
    def activate_index(self, index: int) -> None:
        self.setCurrentIndex(index)

    @pyqtSlot(str)
    def activate_workspace(self, workspace_id: str) -> None:
        target = str(workspace_id)
        for index, tab in enumerate(self._tabs):
            if tab.get("workspace_id") == target:
                self.setCurrentIndex(index)
                return
