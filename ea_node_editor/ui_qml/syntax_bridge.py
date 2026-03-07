from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtQuick import QQuickTextDocument

from ea_node_editor.ui.editor.code_editor import PythonSyntaxHighlighter


class QmlScriptSyntaxBridge(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._highlighter: PythonSyntaxHighlighter | None = None
        self._document = None

    @pyqtSlot(QQuickTextDocument)
    def attach_document(self, text_document: QQuickTextDocument) -> None:
        if text_document is None:
            return
        document = text_document.textDocument()
        if document is None:
            return
        if self._document is document and self._highlighter is not None:
            return
        self._document = document
        self._highlighter = PythonSyntaxHighlighter(document)
        self._highlighter.rehighlight()
