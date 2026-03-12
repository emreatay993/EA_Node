from __future__ import annotations

import multiprocessing as mp
import sys

from PyQt6.QtWidgets import QApplication

from ea_node_editor.ui.shell.window import ShellWindow
from ea_node_editor.ui.shell.controllers.app_preferences_controller import AppPreferencesController
from ea_node_editor.ui.theme import DEFAULT_THEME_ID, build_theme_stylesheet, resolve_theme_id

APP_STYLESHEET = build_theme_stylesheet(DEFAULT_THEME_ID)


def _startup_theme_id() -> str:
    try:
        graphics = AppPreferencesController().graphics_settings()
    except Exception:  # noqa: BLE001
        return DEFAULT_THEME_ID
    theme = graphics.get("theme", {}) if isinstance(graphics, dict) else {}
    return resolve_theme_id(theme.get("theme_id", DEFAULT_THEME_ID))


def run() -> int:
    mp.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("EA Node Editor")
    app.setStyleSheet(build_theme_stylesheet(_startup_theme_id()))
    window = ShellWindow()
    window.show()
    return app.exec()
