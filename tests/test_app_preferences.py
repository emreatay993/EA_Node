from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    ansys_dpf_plugin_state,
    default_app_preferences_document,
    set_ansys_dpf_plugin_state,
)
from ea_node_editor.settings import APP_PREFERENCES_KIND, APP_PREFERENCES_VERSION


class AppPreferencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._preferences_path = Path(self._temp_dir.name) / "app_preferences.json"
        self._store = AppPreferencesStore(path_provider=lambda: self._preferences_path)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_missing_document_defaults_ansys_dpf_plugin_state_to_empty_versions(self) -> None:
        document = self._store.load_document()

        self.assertEqual(document["kind"], APP_PREFERENCES_KIND)
        self.assertEqual(document["version"], APP_PREFERENCES_VERSION)
        self.assertEqual(
            ansys_dpf_plugin_state(document),
            {
                "version": "",
                "catalog_cache_version": "",
            },
        )

    def test_invalid_ansys_dpf_plugin_state_normalizes_to_empty_versions(self) -> None:
        self._preferences_path.write_text(
            json.dumps(
                {
                    "kind": APP_PREFERENCES_KIND,
                    "version": APP_PREFERENCES_VERSION,
                    "plugins": {
                        "ansys_dpf": {
                            "version": None,
                            "catalog_cache_version": {"unexpected": "mapping"},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        document = self._store.load_document()

        self.assertEqual(
            ansys_dpf_plugin_state(document),
            {
                "version": "",
                "catalog_cache_version": "",
            },
        )

    def test_set_ansys_dpf_plugin_state_round_trips_exact_version_string(self) -> None:
        exact_version = "0.15.0.dev1+build.42"
        document = set_ansys_dpf_plugin_state(
            default_app_preferences_document(),
            version=exact_version,
            catalog_cache_version=exact_version,
        )

        self._store.persist_document(document)

        persisted = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["plugins"]["ansys_dpf"]["version"], exact_version)
        self.assertEqual(persisted["plugins"]["ansys_dpf"]["catalog_cache_version"], exact_version)
        self.assertEqual(
            ansys_dpf_plugin_state(self._store.load_document()),
            {
                "version": exact_version,
                "catalog_cache_version": exact_version,
            },
        )


if __name__ == "__main__":
    unittest.main()
