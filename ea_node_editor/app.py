from __future__ import annotations

import multiprocessing as mp
import sys

from PyQt6.QtWidgets import QApplication

from ea_node_editor.ui.shell.window import ShellWindow
from ea_node_editor.ui.theme import STITCH_DARK_V1, build_app_stylesheet

APP_STYLESHEET = build_app_stylesheet(STITCH_DARK_V1)


def run() -> int:
    mp.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("EA Node Editor")
    app.setStyleSheet(APP_STYLESHEET)
    window = ShellWindow()
    window.show()
    return app.exec()
