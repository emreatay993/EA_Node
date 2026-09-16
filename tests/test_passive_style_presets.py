from __future__ import annotations

import unittest

from ea_node_editor.ui.passive_style_presets import (
    PassiveStylePresetCatalog,
    built_in_style_presets,
)


class PassiveStylePresetCatalogTests(unittest.TestCase):
    def test_flowchart_classic_preset_matches_polished_defaults(self) -> None:
        built_ins = built_in_style_presets("node")
        flowchart_classic = next(entry for entry in built_ins if entry["preset_id"] == "builtin_node_flowchart_classic")

        self.assertTrue(flowchart_classic["read_only"])
        self.assertEqual(
            flowchart_classic["style"],
            {
                "fill_color": "#F5FAFD",
                "border_color": "#61798B",
                "text_color": "#173247",
                "border_width": 2.0,
                "font_weight": "bold",
            },
        )

    def test_catalog_exposes_read_only_starters_without_serializing_them(self) -> None:
        catalog = PassiveStylePresetCatalog("node", [])

        built_ins = built_in_style_presets("node")
        edge_built_ins = built_in_style_presets("edge")
        retired_keys = {
            "accent_color",
            "header_color",
            "header_gradient_enabled",
            "header_gradient_color",
            "header_gradient_direction",
        }

        self.assertTrue(built_ins)
        self.assertTrue(edge_built_ins)
        self.assertTrue(all(retired_keys.isdisjoint(entry["style"]) for entry in built_ins))
        self.assertEqual(catalog.user_presets(), [])
        self.assertEqual(catalog.entries()[: len(built_ins)], built_ins)
        self.assertTrue(all(entry.get("read_only") for entry in built_ins))

        saved = catalog.save_new(
            "Project Accent",
            {
                "fill_color": "#112233",
                "border_width": "2.5",
                "gradient_enabled": True,
                "gradient_color": "#334455",
                "gradient_direction": "west",
                "header_gradient_enabled": False,
                "header_gradient_color": "#556677",
                "header_gradient_direction": "east",
                "accent_color": "#778899",
                "header_color": "#AABBCC",
            },
        )
        assert saved is not None

        self.assertFalse(saved.get("read_only"))
        self.assertRegex(saved["preset_id"], r"^node_preset_[0-9a-f]{8}$")
        self.assertEqual(
            catalog.user_presets(),
            [
                {
                    "preset_id": saved["preset_id"],
                    "name": "Project Accent",
                    "style": {
                        "fill_color": "#112233",
                        "border_width": 2.5,
                        "gradient_enabled": True,
                        "gradient_color": "#334455",
                        "gradient_direction": "west",
                    },
                }
            ],
        )

    def test_built_in_node_presets_are_distinct_so_style_matching_is_unambiguous(self) -> None:
        built_ins = built_in_style_presets("node")

        ids = [entry["preset_id"] for entry in built_ins]
        names = [entry["name"] for entry in built_ins]
        styles = [entry["style"] for entry in built_ins]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(styles), len({tuple(sorted(style.items())) for style in styles}))
        catalog = PassiveStylePresetCatalog("node", [])
        for entry in built_ins:
            self.assertEqual(catalog.matching_preset_id(entry["style"]), entry["preset_id"])

    def test_built_in_node_presets_keep_readable_text_and_visible_borders(self) -> None:
        # Pale fills barely contrast with light canvases, so the border carries the node edge (WCAG 1.4.11 3:1)
        # and text must stay comfortably readable (WCAG AAA 7:1).
        for entry in built_in_style_presets("node"):
            style = entry["style"]
            with self.subTest(preset=entry["name"]):
                fill = style["fill_color"]
                self.assertGreaterEqual(_contrast_ratio(style["text_color"], fill), 7.0)
                self.assertGreaterEqual(_contrast_ratio(style["border_color"], fill), 3.0)


def _relative_luminance(hex_color: str) -> float:
    digits = hex_color.lstrip("#")[-6:]
    channels = [int(digits[index : index + 2], 16) / 255.0 for index in (0, 2, 4)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


if __name__ == "__main__":
    unittest.main()
