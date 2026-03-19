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
from scripts.verification_manifest import GUI_TEST_PATHS  # noqa: E402
from scripts.verification_manifest import SLOW_TEST_PATHS  # noqa: E402


# ---------------------------------------------------------------------------
# Centralized pytest selection markers
# ---------------------------------------------------------------------------

_GUI_TEST_PATHS = frozenset(GUI_TEST_PATHS)
_SLOW_TEST_PATHS = frozenset(SLOW_TEST_PATHS)


def _nodeid_test_path(nodeid: str) -> str:
    return nodeid.split("::", 1)[0].replace("\\", "/")


def _add_marker_if_missing(item: pytest.Item, marker_name: str) -> None:
    if item.get_closest_marker(marker_name) is None:
        item.add_marker(getattr(pytest.mark, marker_name))


@pytest.hookimpl(tryfirst=True)
def pytest_ignore_collect(collection_path, path=None, config=None):  # type: ignore[no-untyped-def]
    _ = path, config
    return Path(str(collection_path)).name == "venv"


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    _ = config
    for item in items:
        test_path = _nodeid_test_path(item.nodeid)
        if test_path in _GUI_TEST_PATHS:
            _add_marker_if_missing(item, "gui")
        if test_path in _SLOW_TEST_PATHS:
            _add_marker_if_missing(item, "slow")


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
