from __future__ import annotations

import multiprocessing as mp
import sys

from PyQt6.QtWidgets import QApplication

from ea_node_editor.app_preferences import resolve_startup_theme_id
from ea_node_editor.ui.shell.window import ShellWindow
from ea_node_editor.ui.theme import DEFAULT_THEME_ID, build_theme_stylesheet

APP_STYLESHEET = build_theme_stylesheet(DEFAULT_THEME_ID)


def _startup_theme_id() -> str:
    return resolve_startup_theme_id()


def build_and_show_shell_window() -> ShellWindow:
    window = ShellWindow()
    window.show()
    return window


def run() -> int:
    mp.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("EA Node Editor")
    app.setStyleSheet(build_theme_stylesheet(_startup_theme_id()))
    build_and_show_shell_window()
    return app.exec()
