from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    ansys_dpf_plugin_state,
    default_app_preferences_document,
    normalize_floating_toolbar_style,
    normalize_graphics_settings,
    normalize_property_pane_variant,
    set_ansys_dpf_plugin_state,
)
from ea_node_editor.settings import (
    APP_PREFERENCES_KIND,
    APP_PREFERENCES_VERSION,
    DEFAULT_FLOATING_TOOLBAR_STYLE,
    DEFAULT_PROPERTY_PANE_VARIANT,
)


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


class FloatingToolbarStyleNormalizationTests(unittest.TestCase):
    def test_known_values_pass_through_case_insensitive(self) -> None:
        self.assertEqual(normalize_floating_toolbar_style("compact_pill"), "compact_pill")
        self.assertEqual(normalize_floating_toolbar_style(" SEGMENTED_BAR "), "segmented_bar")
        self.assertEqual(normalize_floating_toolbar_style("Minimal_Ghost"), "minimal_ghost")

    def test_unknown_value_falls_back_to_default(self) -> None:
        self.assertEqual(
            normalize_floating_toolbar_style("bubble_row"),
            DEFAULT_FLOATING_TOOLBAR_STYLE,
        )
        self.assertEqual(
            normalize_floating_toolbar_style(None),
            DEFAULT_FLOATING_TOOLBAR_STYLE,
        )

    def test_unknown_value_with_valid_override_default_uses_override(self) -> None:
        self.assertEqual(
            normalize_floating_toolbar_style("bogus", "segmented_bar"),
            "segmented_bar",
        )


class PropertyPaneVariantNormalizationTests(unittest.TestCase):
    def test_known_values_pass_through_case_insensitive(self) -> None:
        self.assertEqual(normalize_property_pane_variant("smart_groups"), "smart_groups")
        self.assertEqual(normalize_property_pane_variant(" ACCORDION_CARDS "), "accordion_cards")
        self.assertEqual(normalize_property_pane_variant("Palette"), "palette")

    def test_unknown_value_falls_back_to_default(self) -> None:
        self.assertEqual(
            normalize_property_pane_variant("bogus_layout"),
            DEFAULT_PROPERTY_PANE_VARIANT,
        )
        self.assertEqual(
            normalize_property_pane_variant(None),
            DEFAULT_PROPERTY_PANE_VARIANT,
        )

    def test_graphics_settings_fills_default_when_absent(self) -> None:
        normalized = normalize_graphics_settings({"shell": {}})
        self.assertEqual(
            normalized["shell"]["property_pane_variant"],
            DEFAULT_PROPERTY_PANE_VARIANT,
        )

    def test_graphics_settings_rejects_unknown_variant(self) -> None:
        normalized = normalize_graphics_settings(
            {"shell": {"property_pane_variant": "floating_bubbles"}}
        )
        self.assertEqual(
            normalized["shell"]["property_pane_variant"],
            DEFAULT_PROPERTY_PANE_VARIANT,
        )

    def test_graphics_settings_preserves_known_variant(self) -> None:
        normalized = normalize_graphics_settings(
            {"shell": {"property_pane_variant": "palette"}}
        )
        self.assertEqual(normalized["shell"]["property_pane_variant"], "palette")


if __name__ == "__main__":
    unittest.main()
