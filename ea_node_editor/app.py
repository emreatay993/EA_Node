from __future__ import annotations

import multiprocessing as mp
import sys
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QApplication

from ea_node_editor.app_preferences import resolve_startup_theme_id
from ea_node_editor.ui.shell.composition import create_shell_window
from ea_node_editor.ui.theme import DEFAULT_THEME_ID, build_theme_stylesheet

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow

APP_STYLESHEET = build_theme_stylesheet(DEFAULT_THEME_ID)


def _startup_theme_id() -> str:
    return resolve_startup_theme_id()


def build_and_show_shell_window() -> ShellWindow:
    window = create_shell_window()
    window.show()
    return window


def run() -> int:
    mp.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("COREX Node Editor")
    app.setStyleSheet(build_theme_stylesheet(_startup_theme_id()))
    build_and_show_shell_window()
    return app.exec()
