from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget


class ConsolePanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._warnings = 0
        self._errors = 0

        self.tabs = QTabWidget()
        self.output = QPlainTextEdit()
        self.errors = QPlainTextEdit()
        self.warnings = QPlainTextEdit()
        for edit in (self.output, self.errors, self.warnings):
            edit.setReadOnly(True)
            edit.setMaximumBlockCount(5000)
        self.tabs.addTab(self.output, "Output")
        self.tabs.addTab(self.errors, "Errors")
        self.tabs.addTab(self.warnings, "Warnings")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)

    @property
    def warning_count(self) -> int:
        return self._warnings

    @property
    def error_count(self) -> int:
        return self._errors

    def clear_all(self) -> None:
        self.output.clear()
        self.errors.clear()
        self.warnings.clear()
        self._warnings = 0
        self._errors = 0

    def append_log(self, level: str, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] [{level.upper()}] {message}"
        self.output.appendPlainText(line)
        if level.lower() == "warning":
            self._warnings += 1
            self.warnings.appendPlainText(line)
        elif level.lower() == "error":
            self._errors += 1
            self.errors.appendPlainText(line)

