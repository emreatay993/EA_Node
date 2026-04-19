"""QObject bridge exposing DPF operator help to QML.

Modeled on [ShellInspectorBridge](../ui_qml/shell_inspector_bridge.py). The
bridge holds the currently-displayed Markdown and title and exposes a slot to
resolve a node id through the catalog's shared spec lookup into the
corresponding operator spec page.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtQuick import QQuickTextDocument

from ea_node_editor.help.dpf_operator_docs import (
    is_dpf_operator_type_id,
    markdown_for_node,
    markdown_for_type_id,
)

_PARAGRAPH_TOP_MARGIN = 10.0
_PARAGRAPH_BOTTOM_MARGIN = 10.0

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class HelpBridge(QObject):
    help_changed = pyqtSignal()
    help_visible_changed = pyqtSignal()
    help_tab_requested = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: "ShellWindow | None" = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._markdown: str = ""
        self._title: str = ""
        self._type_id: str = ""
        self._visible: bool = False

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @pyqtProperty(str, notify=help_changed)
    def markdown(self) -> str:
        return self._markdown

    @pyqtProperty(str, notify=help_changed)
    def title(self) -> str:
        return self._title

    @pyqtProperty(str, notify=help_changed)
    def type_id(self) -> str:
        return self._type_id

    @pyqtProperty(bool, notify=help_changed)
    def has_help(self) -> bool:
        return bool(self._markdown)

    @pyqtProperty(bool, notify=help_visible_changed)
    def visible(self) -> bool:
        return self._visible

    @pyqtSlot(str, result=bool)
    def show_help_for_node(self, node_id: str) -> bool:
        if self._shell_window is None or not node_id:
            return False
        resolved = markdown_for_node(self._shell_window, str(node_id))
        if resolved is None:
            return False
        markdown, type_id, display_name = resolved
        self._apply(markdown=markdown, type_id=type_id, title=display_name)
        self._set_visible(True)
        return True

    @pyqtSlot(result=bool)
    def show_help_for_selected_node(self) -> bool:
        self.help_tab_requested.emit()
        scene = getattr(getattr(self._shell_window, "scene", None), "selected_node_id", None)
        if scene is None or not callable(scene):
            return False
        node_id = str(scene() or "")
        if not node_id:
            return False
        if not self.can_show_help_for_node(node_id):
            return False
        return self.show_help_for_node(node_id)

    @pyqtSlot(result=bool)
    def can_show_help_for_selected_node(self) -> bool:
        if self._shell_window is None:
            return False
        scene = getattr(self._shell_window, "scene", None)
        if scene is None:
            return False
        node_id = str(getattr(scene, "selected_node_id", lambda: "")() or "")
        return self.can_show_help_for_node(node_id)

    @pyqtSlot(str, result=bool)
    def show_help_for_type(self, type_id: str) -> bool:
        if self._shell_window is None:
            return False
        registry = getattr(self._shell_window, "registry", None)
        if registry is None:
            return False
        if not is_dpf_operator_type_id(type_id):
            return False
        markdown = markdown_for_type_id(str(type_id), registry)
        if markdown is None:
            return False
        spec = registry.spec_or_none(str(type_id))
        display_name = str(getattr(spec, "display_name", "") or type_id)
        self._apply(markdown=markdown, type_id=str(type_id), title=display_name)
        self._set_visible(True)
        return True

    @pyqtSlot(str, result=bool)
    def can_show_help_for_node(self, node_id: str) -> bool:
        if self._shell_window is None or not node_id:
            return False
        return markdown_for_node(self._shell_window, str(node_id)) is not None

    @pyqtSlot()
    def close_help(self) -> None:
        self._set_visible(False)

    @pyqtSlot(QQuickTextDocument)
    def apply_document_spacing(self, quick_doc: QQuickTextDocument | None) -> None:
        """Loosen paragraph margins on the help TextArea's document.

        Qt's built-in Markdown renderer uses very tight default block margins,
        which collapses the blank lines between short paragraphs (e.g. each
        entry in the Scripting section) visually. Walking the blocks and
        setting top/bottom margin restores the spacing implied by the source.
        """
        if quick_doc is None:
            return
        doc = quick_doc.textDocument()
        if doc is None:
            return
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        block = doc.begin()
        while block.isValid():
            fmt = block.blockFormat()
            fmt.setTopMargin(_PARAGRAPH_TOP_MARGIN)
            fmt.setBottomMargin(_PARAGRAPH_BOTTOM_MARGIN)
            cursor.setPosition(block.position())
            cursor.setBlockFormat(fmt)
            block = block.next()
        cursor.endEditBlock()

    def _apply(self, *, markdown: str, type_id: str, title: str) -> None:
        changed = (
            markdown != self._markdown
            or type_id != self._type_id
            or title != self._title
        )
        self._markdown = markdown
        self._type_id = type_id
        self._title = title
        if changed:
            self.help_changed.emit()

    def _set_visible(self, visible: bool) -> None:
        if self._visible == visible:
            return
        self._visible = visible
        self.help_visible_changed.emit()


__all__ = ["HelpBridge"]
