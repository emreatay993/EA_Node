from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.ui.editor.code_editor import PythonCodeEditor


class ScriptEditorDock(QDockWidget):
    script_apply_requested = pyqtSignal(str, str, object)

    def __init__(self, parent=None) -> None:
        super().__init__("Python Script Editor", parent)
        self.setObjectName("scriptEditorDock")
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFloating(False)

        self._node_id = ""
        self._base_script = ""
        self._dirty = False

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.title_label = QLabel("No Python Script node selected", container)
        self.title_label.setObjectName("scriptEditorTitle")
        self.editor = PythonCodeEditor(container)
        self.editor.setPlaceholderText(
            "# Select a Python Script node to edit its script property.\n"
            "output_data = input_data\n"
        )

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)
        self.modified_label = QLabel("Saved", container)
        self.cursor_label = QLabel("Ln 1, Col 1 | Sel 0 | Pos 0", container)
        self.revert_button = QPushButton("Revert", container)
        self.apply_button = QPushButton("Apply", container)
        button_row.addWidget(self.modified_label)
        button_row.addWidget(self.cursor_label)
        button_row.addStretch(1)
        button_row.addWidget(self.revert_button)
        button_row.addWidget(self.apply_button)

        layout.addWidget(self.title_label)
        layout.addWidget(self.editor, stretch=1)
        layout.addLayout(button_row)
        self.setWidget(container)

        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.caret_diagnostics_changed.connect(self._update_cursor_label)
        self.revert_button.clicked.connect(self._revert)
        self.apply_button.clicked.connect(self._apply)
        self._set_enabled(False)
        self._update_cursor_label(1, 1, 0, 0)

    @property
    def current_node_id(self) -> str:
        return self._node_id

    def set_node(self, node: NodeInstance | None) -> None:
        if node is None or node.type_id != "core.python_script":
            self._node_id = ""
            self._base_script = ""
            self.title_label.setText("No Python Script node selected")
            self.editor.blockSignals(True)
            self.editor.setPlainText("")
            self.editor.blockSignals(False)
            self._set_enabled(False)
            self._set_dirty(False)
            self._refresh_caret_label()
            return

        script = str(node.properties.get("script", ""))
        self._node_id = node.node_id
        self._base_script = script
        self.title_label.setText(f"{node.title} ({node.node_id})")
        self.editor.blockSignals(True)
        self.editor.setPlainText(script)
        self.editor.blockSignals(False)
        self._set_enabled(True)
        self._set_dirty(False)
        self._refresh_caret_label()
        if self.isVisible():
            self.focus_editor()

    def _set_enabled(self, enabled: bool) -> None:
        self.editor.setEnabled(enabled)
        self.revert_button.setEnabled(enabled)
        self.apply_button.setEnabled(enabled)

    def _on_text_changed(self) -> None:
        if not self._node_id:
            self._set_dirty(False)
            return
        self._set_dirty(self.editor.toPlainText() != self._base_script)

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.modified_label.setText("*Modified" if dirty else "Saved")
        self.apply_button.setEnabled(bool(self._node_id and dirty))
        self.revert_button.setEnabled(bool(self._node_id and dirty))

    def _update_cursor_label(self, line: int, column: int, position: int, selection: int) -> None:
        self.cursor_label.setText(f"Ln {line}, Col {column} | Sel {selection} | Pos {position}")

    def _revert(self) -> None:
        if not self._node_id:
            return
        self.editor.blockSignals(True)
        self.editor.setPlainText(self._base_script)
        self.editor.blockSignals(False)
        self._set_dirty(False)
        self._refresh_caret_label()
        self.focus_editor()

    def _apply(self) -> None:
        if not self._node_id:
            return
        text = self.editor.toPlainText()
        self._base_script = text
        self._set_dirty(False)
        self.script_apply_requested.emit(self._node_id, "script", text)
        self.focus_editor()

    def focus_editor(self) -> bool:
        if not self.isVisible() or not self.editor.isEnabled():
            return False
        self.editor.setFocus(Qt.FocusReason.OtherFocusReason)
        return self.editor.hasFocus()

    def _refresh_caret_label(self) -> None:
        cursor = self.editor.textCursor()
        self._update_cursor_label(
            cursor.blockNumber() + 1,
            cursor.columnNumber() + 1,
            cursor.position(),
            abs(cursor.anchor() - cursor.position()),
        )
