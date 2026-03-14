"""Shared pytest fixtures for the EA Node Editor test suite."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# Must be set before any Qt import.
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ea_node_editor.app import APP_STYLESHEET  # noqa: E402


# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create (or reuse) a single QApplication for the entire test session."""
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(APP_STYLESHEET)
    yield app


# ---------------------------------------------------------------------------
# Shell window test environment
# ---------------------------------------------------------------------------

class ShellTestEnvironment:
    """Reusable helper that manages the temp dir + four path patches
    required by every test that creates a ``ShellWindow``.

    Usage in unittest-style tests::

        class MyTests(unittest.TestCase):
            def setUp(self):
                self._env = ShellTestEnvironment()
                self._env.start()
                ...

            def tearDown(self):
                self._env.stop()
    """

    _PATCH_TARGETS = (
        "ea_node_editor.ui.shell.window.recent_session_path",
        "ea_node_editor.ui.shell.window.autosave_project_path",
        "ea_node_editor.ui.shell.controllers.app_preferences_controller.app_preferences_path",
        "ea_node_editor.custom_workflows.global_store.global_custom_workflows_path",
    )
    _FILE_NAMES = (
        "last_session.json",
        "autosave.sfe",
        "app_preferences.json",
        "custom_workflows_global.json",
    )

    def __init__(self) -> None:
        self._temp_dir: tempfile.TemporaryDirectory | None = None
        self._patches: list[patch] = []

    def start(self) -> Path:
        """Create the temp directory, start all patches, return the temp path."""
        self._temp_dir = tempfile.TemporaryDirectory()
        temp = Path(self._temp_dir.name)
        self._patches = [
            patch(target, return_value=temp / fname)
            for target, fname in zip(self._PATCH_TARGETS, self._FILE_NAMES)
        ]
        for p in self._patches:
            p.start()
        return temp

    def stop(self) -> None:
        """Stop all patches and clean up the temp directory."""
        for p in self._patches:
            p.stop()
        self._patches.clear()
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None

    @property
    def temp_path(self) -> Path:
        assert self._temp_dir is not None
        return Path(self._temp_dir.name)

    @property
    def session_path(self) -> Path:
        return self.temp_path / "last_session.json"

    @property
    def autosave_path(self) -> Path:
        return self.temp_path / "autosave.sfe"

    @property
    def app_preferences_path(self) -> Path:
        return self.temp_path / "app_preferences.json"

    @property
    def global_custom_workflows_path(self) -> Path:
        return self.temp_path / "custom_workflows_global.json"
