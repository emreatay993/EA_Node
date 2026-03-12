from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.settings import (
    APP_PREFERENCES_KIND,
    APP_PREFERENCES_VERSION,
    DEFAULT_GRAPHICS_SETTINGS,
)
from ea_node_editor.ui.shell.controllers.app_preferences_controller import (
    AppPreferencesController,
    AppPreferencesStore,
)


class _RecordingHost:
    def __init__(self) -> None:
        self.applied_graphics: list[dict[str, object]] = []

    def apply_graphics_preferences(self, graphics: dict[str, object]) -> None:
        self.applied_graphics.append(graphics)


class GraphicsSettingsPreferencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._preferences_path = Path(self._temp_dir.name) / "app_preferences.json"
        self._store = AppPreferencesStore(path_provider=lambda: self._preferences_path)
        self._controller = AppPreferencesController(store=self._store)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_missing_file_loads_locked_defaults(self) -> None:
        document = self._controller.load()

        self.assertEqual(document["kind"], APP_PREFERENCES_KIND)
        self.assertEqual(document["version"], APP_PREFERENCES_VERSION)
        self.assertEqual(document["graphics"], DEFAULT_GRAPHICS_SETTINGS)
        self.assertFalse(self._preferences_path.exists())

    def test_invalid_json_file_loads_locked_defaults(self) -> None:
        self._preferences_path.write_text("{not-json", encoding="utf-8")

        document = self._controller.load()

        self.assertEqual(document["graphics"], DEFAULT_GRAPHICS_SETTINGS)

    def test_unsupported_document_metadata_loads_locked_defaults(self) -> None:
        self._preferences_path.write_text(
            json.dumps(
                {
                    "kind": "unexpected",
                    "version": 99,
                    "graphics": {
                        "canvas": {
                            "show_grid": False,
                            "show_minimap": False,
                            "minimap_expanded": False,
                        },
                        "interaction": {
                            "snap_to_grid": True,
                        },
                        "theme": {
                            "theme_id": "stitch_light",
                        },
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        document = self._controller.load()

        self.assertEqual(document["kind"], APP_PREFERENCES_KIND)
        self.assertEqual(document["version"], APP_PREFERENCES_VERSION)
        self.assertEqual(document["graphics"], DEFAULT_GRAPHICS_SETTINGS)

    def test_load_normalizes_invalid_graphics_values(self) -> None:
        self._preferences_path.write_text(
            json.dumps(
                {
                    "kind": APP_PREFERENCES_KIND,
                    "version": APP_PREFERENCES_VERSION,
                    "graphics": {
                        "canvas": {
                            "show_grid": "yes",
                            "show_minimap": False,
                            "minimap_expanded": None,
                        },
                        "interaction": {
                            "snap_to_grid": True,
                        },
                        "theme": {
                            "theme_id": "invalid-theme",
                        },
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        graphics = self._controller.load()["graphics"]

        self.assertEqual(
            graphics,
            {
                "canvas": {
                    "show_grid": True,
                    "show_minimap": False,
                    "minimap_expanded": True,
                },
                "interaction": {
                    "snap_to_grid": True,
                },
                "theme": {
                    "theme_id": "stitch_dark",
                },
            },
        )

    def test_update_graphics_settings_persists_normalized_round_trip(self) -> None:
        graphics = self._controller.update_graphics_settings(
            {
                "canvas": {
                    "show_grid": False,
                    "show_minimap": False,
                },
                "interaction": {
                    "snap_to_grid": True,
                },
                "theme": {
                    "theme_id": "stitch_light",
                },
            }
        )

        self.assertEqual(
            graphics,
            {
                "canvas": {
                    "show_grid": False,
                    "show_minimap": False,
                    "minimap_expanded": True,
                },
                "interaction": {
                    "snap_to_grid": True,
                },
                "theme": {
                    "theme_id": "stitch_light",
                },
            },
        )
        persisted = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["kind"], APP_PREFERENCES_KIND)
        self.assertEqual(persisted["version"], APP_PREFERENCES_VERSION)
        self.assertEqual(persisted["graphics"], graphics)

        reloaded = AppPreferencesController(store=self._store).load()
        self.assertEqual(reloaded, persisted)

    def test_load_into_host_applies_loaded_graphics_settings(self) -> None:
        host = _RecordingHost()

        graphics = self._controller.load_into_host(host)

        self.assertEqual(graphics, DEFAULT_GRAPHICS_SETTINGS)
        self.assertEqual(host.applied_graphics, [DEFAULT_GRAPHICS_SETTINGS])

    def test_set_graphics_settings_can_apply_persisted_values_to_host(self) -> None:
        host = _RecordingHost()

        graphics = self._controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": False,
                    "show_minimap": False,
                    "minimap_expanded": False,
                },
                "interaction": {
                    "snap_to_grid": True,
                },
                "theme": {
                    "theme_id": "stitch_light",
                },
            },
            host=host,
        )

        self.assertEqual(host.applied_graphics, [graphics])
        persisted = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["graphics"], graphics)


if __name__ == "__main__":
    unittest.main()
