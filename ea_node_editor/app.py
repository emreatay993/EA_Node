from __future__ import annotations

import logging
import multiprocessing as mp
import sys
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    default_app_preferences_document,
    normalize_app_preferences_document,
    resolve_startup_theme_id,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.telemetry.startup_profile import is_autoquit, phase, summary
from ea_node_editor.ui.app_icon import apply_application_icon
from ea_node_editor.ui.shell.composition import create_shell_window
from ea_node_editor.ui.splash import OpeningSplash, RegistryLoader
from ea_node_editor.ui.theme.registry import DEFAULT_THEME_ID
from ea_node_editor.ui.theme.styles import build_theme_stylesheet

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow

APP_STYLESHEET = build_theme_stylesheet(DEFAULT_THEME_ID)


def _load_startup_preferences_document(*, store: AppPreferencesStore | None = None) -> dict[str, Any]:
    try:
        return normalize_app_preferences_document((store or AppPreferencesStore()).load_document())
    except Exception:  # noqa: BLE001
        return default_app_preferences_document()


def _startup_theme_id(*, preferences_document: Any = None) -> str:
    if isinstance(preferences_document, dict):
        return resolve_startup_theme_id(graphics=preferences_document.get("graphics"))
    return resolve_startup_theme_id()


def build_and_show_shell_window() -> ShellWindow:
    preferences_document = _load_startup_preferences_document()
    window = create_shell_window(preferences_document=preferences_document)
    window.show()
    return window


def run() -> int:
    startup_preferences_document = _load_startup_preferences_document()
    with phase("run.mp.freeze_support"):
        mp.freeze_support()
    with phase("run.QApplication"):
        app = QApplication(sys.argv)
        app.setApplicationName("COREX Node Editor")
    with phase("run.apply_application_icon"):
        apply_application_icon(app)
    with phase("run.theme_stylesheet"):
        app.setStyleSheet(build_theme_stylesheet(_startup_theme_id(preferences_document=startup_preferences_document)))

    with phase("run.splash_show"):
        splash = OpeningSplash()
        splash.show_centered()

    # Coordinator state: we need both the splash's boot animation to finish
    # AND the background registry build to complete before starting the
    # main-thread shell construction. Whichever arrives second fires _build.
    state: dict[str, object] = {
        "boot_done": False,
        "registry": None,  # NodeRegistry | None (None until arrived or failed)
        "registry_arrived": False,
        "built": False,
    }

    loader = RegistryLoader(preferences_document=startup_preferences_document)

    def _maybe_build() -> None:
        if state["built"] or not state["boot_done"] or not state["registry_arrived"]:
            return
        state["built"] = True
        registry = state["registry"]
        with phase("run.create_shell_window"):
            window = create_shell_window(
                registry=registry,  # type: ignore[arg-type]
                preferences_document=startup_preferences_document,
            )
        splash.finish(window, min_visible_ms=0)
        if is_autoquit():
            QTimer.singleShot(500, lambda: (summary(), app.quit()))

    def _on_boot_completed() -> None:
        state["boot_done"] = True
        _maybe_build()

    def _on_registry_ready(registry: NodeRegistry) -> None:
        state["registry"] = registry
        state["registry_arrived"] = True
        _maybe_build()

    def _on_registry_failed(tb: str) -> None:
        # Fall back to the main-thread build — slow, but keeps the app bootable.
        logger.error("Registry load failed; falling back to main-thread build.\n%s", tb)
        state["registry"] = None
        state["registry_arrived"] = True
        _maybe_build()

    splash.boot_completed.connect(_on_boot_completed)
    loader.ready.connect(_on_registry_ready)
    loader.failed.connect(_on_registry_failed)
    loader.start()

    return app.exec()
