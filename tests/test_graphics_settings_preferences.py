from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.app_preferences import resolve_startup_theme_id
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

    def test_unsupported_document_metadata_loads_locked_defaults(self) -> None:
        self._preferences_path.write_text(
            json.dumps(
                {
                    "kind": "unexpected",
                    "version": 99,
                    "graphics": {
                        "canvas": {"show_grid": False},
                        "theme": {"theme_id": "stitch_light"},
                    },
                }
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
                            "grid_style": "dots",
                            "edge_crossing_style": "crossing-bridges",
                            "show_minimap": False,
                            "show_port_labels": "no",
                            "minimap_expanded": None,
                            "node_shadow": "no",
                            "shadow_strength": 101,
                            "shadow_softness": 25,
                            "shadow_offset": -1,
                        },
                        "interaction": {
                            "snap_to_grid": True,
                        },
                        "performance": {
                            "mode": "warp_speed",
                        },
                        "shell": {
                            "tab_strip_density": "dense",
                        },
                        "theme": {
                            "theme_id": "invalid-theme",
                        },
                        "graph_theme": {
                            "follow_shell_theme": False,
                            "selected_theme_id": "missing-theme",
                            "custom_themes": "bad",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        graphics = self._controller.load()["graphics"]

        self.assertEqual(graphics["canvas"]["show_grid"], True)
        self.assertEqual(graphics["canvas"]["grid_style"], "lines")
        self.assertEqual(
            graphics["canvas"]["edge_crossing_style"],
            DEFAULT_GRAPHICS_SETTINGS["canvas"]["edge_crossing_style"],
        )
        self.assertEqual(graphics["canvas"]["show_minimap"], False)
        self.assertEqual(graphics["canvas"]["show_port_labels"], True)
        self.assertEqual(graphics["canvas"]["minimap_expanded"], True)
        self.assertEqual(graphics["canvas"]["node_shadow"], True)
        self.assertEqual(graphics["canvas"]["shadow_strength"], DEFAULT_GRAPHICS_SETTINGS["canvas"]["shadow_strength"])
        self.assertEqual(graphics["canvas"]["shadow_softness"], 25)
        self.assertEqual(graphics["canvas"]["shadow_offset"], DEFAULT_GRAPHICS_SETTINGS["canvas"]["shadow_offset"])
        self.assertEqual(graphics["interaction"]["snap_to_grid"], True)
        self.assertEqual(graphics["performance"]["mode"], DEFAULT_GRAPHICS_SETTINGS["performance"]["mode"])
        self.assertEqual(graphics["shell"]["tab_strip_density"], DEFAULT_GRAPHICS_SETTINGS["shell"]["tab_strip_density"])
        self.assertEqual(graphics["theme"]["theme_id"], DEFAULT_GRAPHICS_SETTINGS["theme"]["theme_id"])
        self.assertFalse(graphics["graph_theme"]["follow_shell_theme"])
        self.assertEqual(
            graphics["graph_theme"]["selected_theme_id"],
            DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["selected_theme_id"],
        )
        self.assertEqual(graphics["graph_theme"]["custom_themes"], [])

    def test_set_graphics_settings_persists_and_applies_values_to_host(self) -> None:
        host = _RecordingHost()

        graphics = self._controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": False,
                    "grid_style": "POINTS",
                    "edge_crossing_style": " GAP_BREAK ",
                    "show_minimap": False,
                    "show_port_labels": False,
                    "minimap_expanded": False,
                    "node_shadow": False,
                    "shadow_strength": 15,
                    "shadow_softness": 25,
                    "shadow_offset": 3,
                },
                "interaction": {
                    "snap_to_grid": True,
                },
                "performance": {
                    "mode": " MAX_PERFORMANCE ",
                },
                "shell": {
                    "tab_strip_density": "regular",
                },
                "theme": {
                    "theme_id": "stitch_light",
                },
                "graph_theme": {
                    "follow_shell_theme": False,
                    "selected_theme_id": "graph_stitch_light",
                    "custom_themes": [],
                },
            },
            host=host,
        )

        self.assertEqual(host.applied_graphics, [graphics])
        self.assertEqual(graphics["canvas"]["grid_style"], "points")
        self.assertEqual(graphics["canvas"]["edge_crossing_style"], "gap_break")
        self.assertFalse(graphics["canvas"]["show_port_labels"])
        self.assertEqual(graphics["performance"]["mode"], "max_performance")
        persisted = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["kind"], APP_PREFERENCES_KIND)
        self.assertEqual(persisted["version"], APP_PREFERENCES_VERSION)
        self.assertEqual(persisted["graphics"], graphics)
        reloaded = AppPreferencesController(store=self._store).load()
        self.assertEqual(reloaded, persisted)

    def test_graph_typography_preferences_default_schema_and_legacy_payload_compatibility(self) -> None:
        defaults = self._controller.load()["graphics"]

        self.assertEqual(defaults["typography"]["graph_label_pixel_size"], 10)

        self._preferences_path.write_text(
            json.dumps(
                {
                    "kind": APP_PREFERENCES_KIND,
                    "version": APP_PREFERENCES_VERSION,
                    "graphics": {
                        "canvas": {
                            "show_grid": False,
                        },
                        "theme": {
                            "theme_id": "stitch_light",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        graphics = AppPreferencesController(store=self._store).load()["graphics"]

        self.assertFalse(graphics["canvas"]["show_grid"])
        self.assertEqual(graphics["theme"]["theme_id"], "stitch_light")
        self.assertEqual(graphics["typography"]["graph_label_pixel_size"], 10)

    def test_graph_typography_preferences_clamp_invalid_values_without_disturbing_other_graphics(self) -> None:
        cases = (
            ("missing", {}, 10),
            ("non-integer", {"graph_label_pixel_size": "11"}, 10),
            ("low", {"graph_label_pixel_size": 3}, 8),
            ("high", {"graph_label_pixel_size": 27}, 18),
        )

        for _label, typography_payload, expected in cases:
            with self.subTest(case=_label):
                self._preferences_path.write_text(
                    json.dumps(
                        {
                            "kind": APP_PREFERENCES_KIND,
                            "version": APP_PREFERENCES_VERSION,
                            "graphics": {
                                "canvas": {
                                    "show_grid": False,
                                },
                                "typography": typography_payload,
                            },
                        }
                    ),
                    encoding="utf-8",
                )

                graphics = AppPreferencesController(store=self._store).load()["graphics"]

                self.assertFalse(graphics["canvas"]["show_grid"])
                self.assertEqual(
                    graphics["typography"]["graph_label_pixel_size"],
                    expected,
                )

    def test_graph_typography_preferences_persist_nested_block_on_save(self) -> None:
        graphics = self._controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": False,
                },
                "typography": {
                    "graph_label_pixel_size": 17,
                },
            }
        )

        persisted = json.loads(self._preferences_path.read_text(encoding="utf-8"))

        self.assertEqual(graphics["typography"]["graph_label_pixel_size"], 17)
        self.assertEqual(
            persisted["graphics"]["typography"],
            {"graph_label_pixel_size": 17},
        )
        self.assertEqual(
            AppPreferencesController(store=self._store).load()["graphics"]["typography"],
            {"graph_label_pixel_size": 17},
        )

    def test_graph_typography_preferences_load_into_host_applies_normalized_size(self) -> None:
        host = _RecordingHost()
        self._preferences_path.write_text(
            json.dumps(
                {
                    "kind": APP_PREFERENCES_KIND,
                    "version": APP_PREFERENCES_VERSION,
                    "graphics": {
                        "typography": {
                            "graph_label_pixel_size": 22,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        resolved = self._controller.load_into_host(host)

        self.assertEqual(host.applied_graphics, [resolved])
        self.assertEqual(resolved["typography"]["graph_label_pixel_size"], 18)

    def test_startup_theme_resolution_reads_preferences_store_without_controller(self) -> None:
        self._preferences_path.write_text(
            json.dumps(
                {
                    "kind": APP_PREFERENCES_KIND,
                    "version": APP_PREFERENCES_VERSION,
                    "graphics": {
                        "theme": {
                            "theme_id": "stitch_light",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        self.assertEqual(resolve_startup_theme_id(store=self._store), "stitch_light")


if __name__ == "__main__":
    unittest.main()
