from __future__ import annotations

import copy
from typing import Any

from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QWidget

from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.dialogs.sectioned_settings_dialog import SectionedSettingsDialog

_THEME_CHOICES = (
    ("stitch_dark", "Stitch Dark"),
    ("stitch_light", "Stitch Light"),
)


class GraphicsSettingsDialog(SectionedSettingsDialog):
    _SECTIONS = [
        ("canvas", "Canvas"),
        ("interaction", "Interaction"),
        ("theme", "Theme"),
    ]

    def __init__(self, initial_settings: dict[str, Any] | None = None, parent=None) -> None:
        super().__init__(
            window_title="Graphics Settings",
            header_text="Configure app-wide graphics and interaction defaults.",
            sections=self._SECTIONS,
            section_list_object_name="graphicsSettingsSectionList",
            header_object_name="graphicsSettingsHeader",
            parent=parent,
        )
        self.set_values(initial_settings or {})

    def _build_pages(self) -> None:
        self.add_section_page(self._build_canvas_page())
        self.add_section_page(self._build_interaction_page())
        self.add_section_page(self._build_theme_page())

    def _build_canvas_page(self) -> QWidget:
        page = QWidget(self)
        form = QFormLayout(page)
        self.show_grid_check = QCheckBox("Show grid overlay", page)
        self.show_minimap_check = QCheckBox("Show minimap", page)
        self.minimap_expanded_check = QCheckBox("Expand minimap by default", page)
        form.addRow(self.show_grid_check)
        form.addRow(self.show_minimap_check)
        form.addRow(self.minimap_expanded_check)
        return page

    def _build_interaction_page(self) -> QWidget:
        page = QWidget(self)
        form = QFormLayout(page)
        self.snap_to_grid_check = QCheckBox("Snap nodes to grid during edits", page)
        form.addRow(self.snap_to_grid_check)
        return page

    def _build_theme_page(self) -> QWidget:
        page = QWidget(self)
        form = QFormLayout(page)
        self.theme_combo = QComboBox(page)
        for theme_id, label in _THEME_CHOICES:
            self.theme_combo.addItem(label, theme_id)
        form.addRow("Theme", self.theme_combo)
        return page

    @staticmethod
    def _normalize(initial_settings: dict[str, Any]) -> dict[str, Any]:
        normalized = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)

        canvas = initial_settings.get("canvas")
        if isinstance(canvas, dict):
            for field in ("show_grid", "show_minimap", "minimap_expanded"):
                value = canvas.get(field)
                if isinstance(value, bool):
                    normalized["canvas"][field] = value

        interaction = initial_settings.get("interaction")
        if isinstance(interaction, dict):
            value = interaction.get("snap_to_grid")
            if isinstance(value, bool):
                normalized["interaction"]["snap_to_grid"] = value

        theme = initial_settings.get("theme")
        if isinstance(theme, dict):
            theme_id = str(theme.get("theme_id", "")).strip()
            if any(theme_id == allowed_id for allowed_id, _label in _THEME_CHOICES):
                normalized["theme"]["theme_id"] = theme_id

        return normalized

    def set_values(self, initial_settings: dict[str, Any]) -> None:
        settings = self._normalize(initial_settings)
        self.show_grid_check.setChecked(settings["canvas"]["show_grid"])
        self.show_minimap_check.setChecked(settings["canvas"]["show_minimap"])
        self.minimap_expanded_check.setChecked(settings["canvas"]["minimap_expanded"])
        self.snap_to_grid_check.setChecked(settings["interaction"]["snap_to_grid"])
        theme_id = settings["theme"]["theme_id"]
        index = self.theme_combo.findData(theme_id)
        self.theme_combo.setCurrentIndex(index if index >= 0 else 0)

    def values(self) -> dict[str, Any]:
        theme_id = self.theme_combo.currentData()
        return self._normalize(
            {
                "canvas": {
                    "show_grid": self.show_grid_check.isChecked(),
                    "show_minimap": self.show_minimap_check.isChecked(),
                    "minimap_expanded": self.minimap_expanded_check.isChecked(),
                },
                "interaction": {
                    "snap_to_grid": self.snap_to_grid_check.isChecked(),
                },
                "theme": {
                    "theme_id": str(theme_id) if theme_id is not None else "",
                },
            }
        )

