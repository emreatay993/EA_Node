from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.settings import (
    APP_PREFERENCES_KIND,
    APP_PREFERENCES_VERSION,
    DEFAULT_SOURCE_IMPORT_MODE,
    DEFAULT_SOURCE_IMPORT_SETTINGS,
)
from ea_node_editor.ui.shell.controllers.app_preferences_controller import (
    AppPreferencesController,
    AppPreferencesStore,
)


class SourceImportPreferencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._preferences_path = Path(self._temp_dir.name) / "app_preferences.json"
        self._store = AppPreferencesStore(path_provider=lambda: self._preferences_path)
        self._controller = AppPreferencesController(store=self._store)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_missing_document_defaults_source_import_mode_to_managed_copy(self) -> None:
        document = self._controller.load()

        self.assertEqual(document["kind"], APP_PREFERENCES_KIND)
        self.assertEqual(document["version"], APP_PREFERENCES_VERSION)
        self.assertEqual(document["source_import"], DEFAULT_SOURCE_IMPORT_SETTINGS)
        self.assertEqual(self._controller.source_import_mode(), DEFAULT_SOURCE_IMPORT_MODE)

    def test_invalid_source_import_mode_normalizes_to_managed_copy(self) -> None:
        self._preferences_path.write_text(
            json.dumps(
                {
                    "kind": APP_PREFERENCES_KIND,
                    "version": APP_PREFERENCES_VERSION,
                    "source_import": {
                        "default_mode": "archive_everything",
                    },
                }
            ),
            encoding="utf-8",
        )

        document = self._controller.load()

        self.assertEqual(document["source_import"], DEFAULT_SOURCE_IMPORT_SETTINGS)
        self.assertEqual(self._controller.source_import_mode(), DEFAULT_SOURCE_IMPORT_MODE)

    def test_set_source_import_mode_persists_external_link_and_round_trips(self) -> None:
        mode = self._controller.set_source_import_mode(" EXTERNAL_LINK ")

        self.assertEqual(mode, "external_link")
        persisted = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(
            persisted["source_import"],
            {
                "default_mode": "external_link",
            },
        )
        reloaded_controller = AppPreferencesController(store=self._store)
        self.assertEqual(reloaded_controller.source_import_mode(), "external_link")
        self.assertEqual(
            reloaded_controller.load()["source_import"],
            {
                "default_mode": "external_link",
            },
        )


if __name__ == "__main__":
    unittest.main()
