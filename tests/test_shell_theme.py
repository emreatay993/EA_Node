from __future__ import annotations

import json
import copy
from unittest.mock import patch

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialog

from ea_node_editor.app import APP_STYLESHEET
from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.dialogs.graphics_settings_dialog import GraphicsSettingsDialog
from ea_node_editor.ui.shell.window import ShellWindow
from ea_node_editor.ui.theme import STITCH_DARK_V1, STITCH_LIGHT_V1, build_theme_stylesheet
from tests.main_window_shell.base import MainWindowShellTestBase
from tests.test_main_window_shell import _named_child_items


def _color_name(value: object, *, include_alpha: bool = False) -> str:
    name_format = QColor.NameFormat.HexArgb if include_alpha else QColor.NameFormat.HexRgb
    return QColor(value).name(name_format)


def _alpha_color_name(value: str, alpha: float) -> str:
    color = QColor(value)
    color.setAlphaF(alpha)
    return _color_name(color, include_alpha=True)


class ShellThemeTests(MainWindowShellTestBase):

    def _recreate_window(self) -> None:
        self.window.close()
        self.app.processEvents()
        self.window = ShellWindow()
        self.window.resize(1200, 800)
        self.window.show()
        self.app.processEvents()

    def _apply_theme(self, theme_id: str) -> None:
        self.window.app_preferences_controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": True,
                    "show_minimap": True,
                    "minimap_expanded": True,
                },
                "interaction": {
                    "snap_to_grid": False,
                },
                "theme": {
                    "theme_id": theme_id,
                },
            },
            host=self.window,
        )
        self.app.processEvents()

    def test_stylesheet_is_generated_from_stitch_tokens(self) -> None:
        self.assertIn("#60CDFF", APP_STYLESHEET)
        self.assertIn("QStatusBar#mainStatusBar", APP_STYLESHEET)
        self.assertIn("QDockWidget::title", APP_STYLESHEET)

    def test_theme_bridge_is_exposed_and_runtime_theme_changes_apply_stylesheet(self) -> None:
        bridge = self.window.quick_widget.rootContext().contextProperty("themeBridge")
        graph_theme_bridge = self.window.quick_widget.rootContext().contextProperty("graphThemeBridge")

        self.assertIsNotNone(bridge)
        self.assertIsNotNone(graph_theme_bridge)
        self.assertEqual(bridge.theme_id, "stitch_dark")
        self.assertEqual(graph_theme_bridge.theme_id, "graph_stitch_dark")
        self.assertEqual(bridge.palette["panel_bg"], self.window.theme_bridge.palette["panel_bg"])

        self.window.app_preferences_controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": True,
                    "show_minimap": True,
                    "minimap_expanded": True,
                },
                "interaction": {
                    "snap_to_grid": False,
                },
                "theme": {
                    "theme_id": "stitch_light",
                },
            },
            host=self.window,
        )
        self.app.processEvents()

        self.assertEqual(self.window.active_theme_id, "stitch_light")
        self.assertEqual(self.window.theme_bridge.theme_id, "stitch_light")
        self.assertEqual(self.window.graph_theme_bridge.theme_id, "graph_stitch_light")
        self.assertEqual(self.window.theme_bridge.token("canvas_bg"), STITCH_LIGHT_V1.canvas_bg)
        self.assertEqual(self.app.styleSheet(), build_theme_stylesheet("stitch_light"))
        self.assertIn(STITCH_LIGHT_V1.panel_bg, self.app.styleSheet())

    def test_shell_qml_surfaces_follow_runtime_theme_palette(self) -> None:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        library_pane = root_object.findChild(QObject, "libraryPane")
        quick_insert_overlay = root_object.findChild(QObject, "connectionQuickInsertOverlay")
        graph_hint_overlay = root_object.findChild(QObject, "graphHintOverlay")

        self.assertIsNotNone(library_pane)
        self.assertIsNotNone(quick_insert_overlay)
        self.assertIsNotNone(graph_hint_overlay)
        self.assertEqual(_color_name(root_object.property("color")), STITCH_DARK_V1.app_bg)
        self.assertEqual(_color_name(library_pane.property("color")), STITCH_DARK_V1.panel_alt_bg)
        self.assertEqual(_color_name(quick_insert_overlay.property("color")), STITCH_DARK_V1.panel_alt_bg)
        self.assertEqual(
            _color_name(graph_hint_overlay.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_DARK_V1.panel_bg, 0.8),
        )

        self.window.app_preferences_controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": True,
                    "show_minimap": True,
                    "minimap_expanded": True,
                },
                "interaction": {
                    "snap_to_grid": False,
                },
                "theme": {
                    "theme_id": "stitch_light",
                },
            },
            host=self.window,
        )
        self.app.processEvents()

        self.assertEqual(_color_name(root_object.property("color")), STITCH_LIGHT_V1.app_bg)
        self.assertEqual(_color_name(library_pane.property("color")), STITCH_LIGHT_V1.panel_alt_bg)
        self.assertEqual(_color_name(quick_insert_overlay.property("color")), STITCH_LIGHT_V1.panel_alt_bg)
        self.assertEqual(
            _color_name(graph_hint_overlay.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_LIGHT_V1.panel_bg, 0.8),
        )

    def test_canvas_qml_surfaces_follow_runtime_theme_palette(self) -> None:
        graph_canvas = self.window.quick_widget.rootObject().findChild(QObject, "graphCanvas")
        background = graph_canvas.findChild(QObject, "graphCanvasBackground")
        minimap_overlay = graph_canvas.findChild(QObject, "graphCanvasMinimapOverlay")
        minimap_toggle = graph_canvas.findChild(QObject, "graphCanvasMinimapToggle")
        drop_preview = graph_canvas.findChild(QObject, "graphCanvasDropPreview")
        edge_layer = graph_canvas.findChild(QObject, "graphCanvasEdgeLayer")
        marquee_rect = graph_canvas.findChild(QObject, "graphCanvasMarqueeRect")

        self.assertIsNotNone(graph_canvas)
        self.assertIsNotNone(background)
        self.assertIsNotNone(minimap_overlay)
        self.assertIsNotNone(minimap_toggle)
        self.assertIsNotNone(drop_preview)
        self.assertIsNotNone(edge_layer)
        self.assertIsNotNone(marquee_rect)

        self.assertEqual(_color_name(background.property("backgroundFillColor")), STITCH_DARK_V1.canvas_bg)
        self.assertEqual(
            _color_name(minimap_overlay.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_DARK_V1.panel_bg, 0.64),
        )
        self.assertEqual(_color_name(minimap_toggle.property("color")), STITCH_DARK_V1.toolbar_bg)
        self.assertEqual(
            _color_name(drop_preview.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_DARK_V1.panel_bg, 0.66),
        )
        self.assertEqual(
            _color_name(edge_layer.property("selectedStrokeColor")),
            self.window.graph_theme_bridge.edge_palette["selected_stroke"],
        )
        self.assertEqual(
            _color_name(edge_layer.property("invalidDragStrokeColor")),
            self.window.graph_theme_bridge.edge_palette["invalid_drag_stroke"],
        )
        self.assertEqual(_color_name(edge_layer.property("flowDefaultStrokeColor")), STITCH_DARK_V1.muted_fg)
        self.assertEqual(_color_name(edge_layer.property("flowDefaultLabelTextColor")), STITCH_DARK_V1.panel_title_fg)
        self.assertEqual(
            _color_name(edge_layer.property("flowDefaultLabelBackgroundColor")),
            STITCH_DARK_V1.panel_bg,
        )
        self.assertEqual(
            _color_name(marquee_rect.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_DARK_V1.accent, 0.2),
        )

        self.window.app_preferences_controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": True,
                    "show_minimap": True,
                    "minimap_expanded": True,
                },
                "interaction": {
                    "snap_to_grid": False,
                },
                "theme": {
                    "theme_id": "stitch_light",
                },
            },
            host=self.window,
        )
        self.app.processEvents()

        self.assertEqual(_color_name(background.property("backgroundFillColor")), STITCH_LIGHT_V1.canvas_bg)
        self.assertEqual(
            _color_name(minimap_overlay.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_LIGHT_V1.panel_bg, 0.64),
        )
        self.assertEqual(_color_name(minimap_toggle.property("color")), STITCH_LIGHT_V1.toolbar_bg)
        self.assertEqual(
            _color_name(drop_preview.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_LIGHT_V1.panel_bg, 0.66),
        )
        self.assertEqual(
            _color_name(edge_layer.property("selectedStrokeColor")),
            self.window.graph_theme_bridge.edge_palette["selected_stroke"],
        )
        self.assertEqual(
            _color_name(edge_layer.property("invalidDragStrokeColor")),
            self.window.graph_theme_bridge.edge_palette["invalid_drag_stroke"],
        )
        self.assertEqual(_color_name(edge_layer.property("flowDefaultStrokeColor")), STITCH_LIGHT_V1.muted_fg)
        self.assertEqual(_color_name(edge_layer.property("flowDefaultLabelTextColor")), STITCH_LIGHT_V1.panel_title_fg)
        self.assertEqual(
            _color_name(edge_layer.property("flowDefaultLabelBackgroundColor")),
            STITCH_LIGHT_V1.panel_bg,
        )
        self.assertEqual(
            _color_name(marquee_rect.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_LIGHT_V1.accent, 0.2),
        )

    def test_canvas_qml_node_shadow_follows_runtime_graphics_settings(self) -> None:
        self.window.scene.add_node_from_type("core.logger", 120.0, 140.0)
        self.app.processEvents()

        graph_canvas = self._graph_canvas_item()
        node_cards = _named_child_items(graph_canvas, "graphNodeCard")
        self.assertEqual(len(node_cards), 1)
        node_card = node_cards[0]
        shadow_item = node_card.findChild(QObject, "graphNodeShadow")
        self.assertIsNotNone(shadow_item)

        self.assertTrue(bool(shadow_item.property("visible")))

        self.window.app_preferences_controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": True,
                    "show_minimap": True,
                    "minimap_expanded": True,
                    "node_shadow": False,
                    "shadow_strength": 15,
                    "shadow_softness": 25,
                    "shadow_offset": 3,
                },
                "interaction": {
                    "snap_to_grid": False,
                },
                "theme": {
                    "theme_id": "stitch_dark",
                },
            },
            host=self.window,
        )
        self.app.processEvents()

        self.assertFalse(bool(shadow_item.property("visible")))

        self.window.app_preferences_controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": True,
                    "show_minimap": True,
                    "minimap_expanded": True,
                    "node_shadow": True,
                    "shadow_strength": 15,
                    "shadow_softness": 25,
                    "shadow_offset": 3,
                },
                "interaction": {
                    "snap_to_grid": False,
                },
                "theme": {
                    "theme_id": "stitch_dark",
                },
            },
            host=self.window,
        )
        self.app.processEvents()

        self.assertTrue(bool(shadow_item.property("visible")))

        offset = shadow_item.property("offset")
        self.assertAlmostEqual(float(offset.x()), 0.0, places=3)
        self.assertAlmostEqual(float(offset.y()), 3.0, places=3)
        self.assertAlmostEqual(float(shadow_item.property("blur")), 0.25, places=3)
        self.assertAlmostEqual(float(shadow_item.property("spread")), 0.15, places=3)

        shadow_color = QColor(shadow_item.property("color"))
        self.assertEqual(shadow_color.alpha(), int(15 * 255 / 100))

    def test_inspector_cards_and_tabs_follow_runtime_theme_palette(self) -> None:
        node_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        root_object = self.window.quick_widget.rootObject()
        inspector_pane = root_object.findChild(QObject, "inspectorPane")
        node_definition_card = root_object.findChild(QObject, "inspectorNodeDefinitionCard")
        port_management_card = root_object.findChild(QObject, "inspectorPortManagementCard")
        inputs_tab = root_object.findChild(QObject, "inspectorInputsTab")
        outputs_tab = root_object.findChild(QObject, "inspectorOutputsTab")

        self.assertIsNotNone(inspector_pane)
        self.assertIsNotNone(node_definition_card)
        self.assertIsNotNone(port_management_card)
        self.assertIsNotNone(inputs_tab)
        self.assertIsNotNone(outputs_tab)

        self.assertEqual(_color_name(node_definition_card.property("color")), STITCH_DARK_V1.inspector_card_bg)
        self.assertEqual(_color_name(port_management_card.property("color")), STITCH_DARK_V1.inspector_card_bg)
        self.assertTrue(bool(inputs_tab.property("selectedStyle")))
        self.assertEqual(_color_name(inputs_tab.property("fillColor")), STITCH_DARK_V1.inspector_selected_bg)

        inspector_pane.setProperty("activePortDirection", "out")
        self.app.processEvents()

        self.assertTrue(bool(outputs_tab.property("selectedStyle")))
        self.assertEqual(_color_name(outputs_tab.property("fillColor")), STITCH_DARK_V1.inspector_selected_bg)

        self._apply_theme("stitch_light")

        self.assertEqual(_color_name(node_definition_card.property("color")), STITCH_LIGHT_V1.inspector_card_bg)
        self.assertEqual(_color_name(port_management_card.property("color")), STITCH_LIGHT_V1.inspector_card_bg)
        self.assertEqual(_color_name(outputs_tab.property("fillColor")), STITCH_LIGHT_V1.inspector_selected_bg)

    def test_persisted_theme_is_applied_when_shell_starts(self) -> None:
        self.window.app_preferences_controller.set_graphics_settings(
            {
                "canvas": {
                    "show_grid": True,
                    "show_minimap": True,
                    "minimap_expanded": True,
                },
                "interaction": {
                    "snap_to_grid": False,
                },
                "theme": {
                    "theme_id": "stitch_light",
                },
            }
        )
        self.app.setStyleSheet(APP_STYLESHEET)

        self._recreate_window()

        self.assertEqual(self.window.active_theme_id, "stitch_light")
        self.assertEqual(self.window.theme_bridge.theme_id, "stitch_light")
        self.assertEqual(self.app.styleSheet(), build_theme_stylesheet("stitch_light"))

    def test_script_editor_action_is_wired_in_qml_shell(self) -> None:
        self.assertFalse(self.window.script_editor.visible)
        self.window.action_toggle_script_editor.trigger()
        self.app.processEvents()
        self.assertTrue(self.window.script_editor.visible)
        self.assertTrue(self.window.action_toggle_script_editor.isChecked())
        metadata = self.window.model.project.metadata
        self.assertTrue(metadata["ui"]["script_editor"]["visible"])

    def test_workflow_settings_action_exists(self) -> None:
        self.assertIsNotNone(self.window.action_workflow_settings)
        self.assertEqual(self.window.action_workflow_settings.text(), "Workflow Settings")

    def test_graphics_settings_action_persists_preferences_and_updates_shell_state(self) -> None:
        self.assertIsNotNone(self.window.action_graphics_settings)
        self.assertEqual(self.window.action_graphics_settings.text(), "Graphics Settings")
        self.assertEqual(len(self.window.action_graphics_settings.shortcuts()), 0)

        updated_graphics = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
        updated_graphics["canvas"]["show_grid"] = False
        updated_graphics["canvas"]["show_minimap"] = False
        updated_graphics["canvas"]["minimap_expanded"] = False
        updated_graphics["interaction"]["snap_to_grid"] = True
        updated_graphics["theme"]["theme_id"] = "stitch_light"

        with patch.object(GraphicsSettingsDialog, "exec", return_value=QDialog.DialogCode.Accepted), patch.object(
            GraphicsSettingsDialog,
            "values",
            return_value=updated_graphics,
        ):
            self.window.show_graphics_settings_dialog()
        self.app.processEvents()

        self.assertFalse(self.window.graphics_show_grid)
        self.assertFalse(self.window.graphics_show_minimap)
        self.assertFalse(self.window.graphics_minimap_expanded)
        self.assertTrue(self.window.snap_to_grid_enabled)
        self.assertTrue(self.window.action_snap_to_grid.isChecked())
        self.assertEqual(self.window.active_theme_id, "stitch_light")

        persisted = json.loads(self._app_preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["graphics"], updated_graphics)


if __name__ == "__main__":
    unittest.main()
