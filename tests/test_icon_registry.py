from __future__ import annotations

import unittest

from ea_node_editor.ui.icon_registry import (
    DEFAULT_ICON_COLOR,
    UiIconRegistryBridge,
    icon_names,
    icon_path,
)


class IconRegistryTests(unittest.TestCase):
    def test_known_icons_resolve_to_existing_files(self) -> None:
        for name in ("crop", "open-session", "run", "pause", "resume", "stop", "step", "focus", "keep-live", "pin", "more"):
            self.assertIn(name, icon_names())
            self.assertTrue(icon_path(name).is_file(), name)

    def test_bridge_exposes_label_and_provider_url(self) -> None:
        bridge = UiIconRegistryBridge()
        self.assertTrue(bridge.has("run"))
        self.assertEqual(bridge.label("run"), "Run")
        self.assertTrue(bridge.has("open-session"))
        self.assertEqual(bridge.label("open-session"), "Open Session")

        source = bridge.sourceSized("pause", 20, DEFAULT_ICON_COLOR)
        self.assertEqual(source, "image://ui-icons/pause?size=20&color=%23D8DEEA")

    def test_unknown_icons_fail_closed(self) -> None:
        bridge = UiIconRegistryBridge()
        self.assertFalse(bridge.has("missing"))
        self.assertEqual(bridge.label("missing"), "missing")
        self.assertEqual(bridge.sourceSized("missing", 16, DEFAULT_ICON_COLOR), "")


if __name__ == "__main__":
    unittest.main()
