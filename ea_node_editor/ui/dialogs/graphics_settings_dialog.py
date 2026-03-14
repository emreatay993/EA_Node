from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from typing import Any

from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QPushButton, QWidget

from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.dialogs.sectioned_settings_dialog import SectionedSettingsDialog
from ea_node_editor.ui.graph_theme import (
    default_graph_theme_id_for_shell_theme,
    graph_theme_choices,
    resolve_graph_theme_id,
)
from ea_node_editor.ui.shell.controllers.app_preferences_controller import (
    normalize_graph_theme_settings,
    normalize_graphics_settings,
)
from ea_node_editor.ui.theme import resolve_theme_id, theme_choices


class GraphicsSettingsDialog(SectionedSettingsDialog):
    _SECTIONS = [
        ("canvas", "Canvas"),
        ("interaction", "Interaction"),
        ("theme", "Theme"),
    ]

    def __init__(
        self,
        initial_settings: dict[str, Any] | None = None,
        parent=None,
        *,
        available_graph_themes: Sequence[tuple[str, str]] | None = None,
        manage_graph_themes_callback: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    ) -> None:
        graph_themes = available_graph_themes or graph_theme_choices()
        self._available_graph_themes = tuple((str(theme_id), str(label)) for theme_id, label in graph_themes)
        if not self._available_graph_themes:
            self._available_graph_themes = graph_theme_choices()
        self._custom_graph_themes = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["custom_themes"])
        self._explicit_graph_theme_id = str(DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["selected_theme_id"])
        self._manage_graph_themes_callback = manage_graph_themes_callback
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
        for theme_id, label in theme_choices():
            self.theme_combo.addItem(label, theme_id)
        self.theme_combo.currentIndexChanged.connect(self._on_shell_theme_changed)
        self.follow_shell_theme_check = QCheckBox("Follow shell theme", page)
        self.follow_shell_theme_check.toggled.connect(self._on_follow_shell_theme_toggled)
        self.graph_theme_combo = QComboBox(page)
        self.graph_theme_combo.currentIndexChanged.connect(self._on_graph_theme_selection_changed)
        for theme_id, label in self._available_graph_themes:
            self.graph_theme_combo.addItem(label, theme_id)
        graph_theme_row = QWidget(page)
        graph_theme_layout = QHBoxLayout(graph_theme_row)
        graph_theme_layout.setContentsMargins(0, 0, 0, 0)
        graph_theme_layout.setSpacing(6)
        graph_theme_layout.addWidget(self.graph_theme_combo, stretch=1)
        self.manage_graph_themes_button = QPushButton("Manage Graph Themes...", graph_theme_row)
        self.manage_graph_themes_button.setEnabled(self._manage_graph_themes_callback is not None)
        self.manage_graph_themes_button.clicked.connect(self._open_graph_theme_manager)
        graph_theme_layout.addWidget(self.manage_graph_themes_button, stretch=0)
        form.addRow("Theme", self.theme_combo)
        form.addRow(self.follow_shell_theme_check)
        form.addRow("Graph theme", graph_theme_row)
        self._sync_graph_theme_combo_enabled()
        return page

    @staticmethod
    def _normalize(initial_settings: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_graphics_settings(initial_settings)
        normalized["theme"]["theme_id"] = resolve_theme_id(normalized["theme"]["theme_id"])
        normalized["graph_theme"]["selected_theme_id"] = resolve_graph_theme_id(
            normalized["graph_theme"]["selected_theme_id"],
            custom_themes=normalized["graph_theme"]["custom_themes"],
        )
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
        self._apply_graph_theme_settings(settings["graph_theme"])

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
                "graph_theme": self._current_graph_theme_settings(),
            }
        )

    def _sync_graph_theme_combo_enabled(self, _checked: bool | None = None) -> None:
        self.graph_theme_combo.setEnabled(not self.follow_shell_theme_check.isChecked())

    def _on_follow_shell_theme_toggled(self, _checked: bool | None = None) -> None:
        if self.follow_shell_theme_check.isChecked():
            self._sync_graph_theme_combo_to_shell_theme()
        else:
            self._set_graph_theme_combo_selection(self._explicit_graph_theme_id)
        self._sync_graph_theme_combo_enabled()

    def _on_shell_theme_changed(self, _index: int) -> None:
        if self.follow_shell_theme_check.isChecked():
            self._sync_graph_theme_combo_to_shell_theme()

    def _on_graph_theme_selection_changed(self, _index: int) -> None:
        if self.follow_shell_theme_check.isChecked():
            return
        graph_theme_id = self.graph_theme_combo.currentData()
        self._explicit_graph_theme_id = resolve_graph_theme_id(
            str(graph_theme_id) if graph_theme_id is not None else "",
            custom_themes=self._custom_graph_themes,
        )

    def _current_graph_theme_settings(self) -> dict[str, Any]:
        graph_theme_id = self._explicit_graph_theme_id if self.follow_shell_theme_check.isChecked() else self.graph_theme_combo.currentData()
        return normalize_graph_theme_settings(
            {
                "follow_shell_theme": self.follow_shell_theme_check.isChecked(),
                "selected_theme_id": str(graph_theme_id) if graph_theme_id is not None else "",
                "custom_themes": copy.deepcopy(self._custom_graph_themes),
            }
        )

    def _apply_graph_theme_settings(self, graph_theme_settings: dict[str, Any]) -> None:
        normalized = normalize_graph_theme_settings(graph_theme_settings)
        self._custom_graph_themes = copy.deepcopy(normalized["custom_themes"])
        self._available_graph_themes = graph_theme_choices(self._custom_graph_themes)
        selected_theme_id = resolve_graph_theme_id(
            normalized["selected_theme_id"],
            custom_themes=self._custom_graph_themes,
        )
        self._explicit_graph_theme_id = selected_theme_id
        self.graph_theme_combo.blockSignals(True)
        self.graph_theme_combo.clear()
        for theme_id, label in self._available_graph_themes:
            self.graph_theme_combo.addItem(label, theme_id)
        self.graph_theme_combo.blockSignals(False)
        self.follow_shell_theme_check.setChecked(normalized["follow_shell_theme"])
        if self.follow_shell_theme_check.isChecked():
            self._sync_graph_theme_combo_to_shell_theme()
        else:
            self._set_graph_theme_combo_selection(selected_theme_id)
            self._sync_graph_theme_combo_enabled()

    def _open_graph_theme_manager(self) -> None:
        if self._manage_graph_themes_callback is None:
            return
        updated_graph_theme = self._manage_graph_themes_callback(self._current_graph_theme_settings())
        if updated_graph_theme is None:
            return
        self._apply_graph_theme_settings(updated_graph_theme)

    def _sync_graph_theme_combo_to_shell_theme(self) -> None:
        self._set_graph_theme_combo_selection(
            default_graph_theme_id_for_shell_theme(self.theme_combo.currentData()),
        )

    def _set_graph_theme_combo_selection(self, theme_id: object) -> None:
        resolved_theme_id = resolve_graph_theme_id(theme_id, custom_themes=self._custom_graph_themes)
        index = self.graph_theme_combo.findData(resolved_theme_id)
        self.graph_theme_combo.blockSignals(True)
        self.graph_theme_combo.setCurrentIndex(index if index >= 0 else 0)
        self.graph_theme_combo.blockSignals(False)
