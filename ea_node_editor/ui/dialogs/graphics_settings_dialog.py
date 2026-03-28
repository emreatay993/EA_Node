from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ea_node_editor.settings import (
    DEFAULT_GRAPHICS_SETTINGS,
    GRAPHICS_PERFORMANCE_MODE_CHOICES,
    GRID_OVERLAY_STYLE_CHOICES,
    TAB_STRIP_DENSITY_CHOICES,
)
from ea_node_editor.ui.dialogs.sectioned_settings_dialog import SectionedSettingsDialog
from ea_node_editor.ui.graph_theme import (
    default_graph_theme_id_for_shell_theme,
    graph_theme_choices,
    resolve_graph_theme,
    resolve_graph_theme_id,
)
from ea_node_editor.ui.graph_theme.preview_widget import GraphThemePreviewWidget, ShadowPreviewWidget
from ea_node_editor.ui.shell.controllers.app_preferences_controller import (
    normalize_graph_theme_settings,
    normalize_graphics_settings,
)
from ea_node_editor.ui.theme import resolve_theme_id, theme_choices


class _ClickableOptionCard(QWidget):
    clicked = pyqtSignal()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class GraphicsSettingsDialog(SectionedSettingsDialog):
    _SECTIONS = [
        ("canvas", "Canvas"),
        ("interaction", "Interaction"),
        ("performance", "Performance"),
        ("theme", "Theme"),
        ("layout", "Layout"),
    ]
    _PERFORMANCE_MODE_COPY = {
        "full_fidelity": "Keeps normal visual quality and applies only invisible structural optimizations.",
        "max_performance": "Temporarily simplifies whole-canvas rendering during pan, zoom, and burst edits; idle quality restores automatically.",
    }
    _PERFORMANCE_MODE_BUTTON_NAMES = {
        "full_fidelity": "graphicsSettingsFullFidelityModeRadio",
        "max_performance": "graphicsSettingsMaxPerformanceModeRadio",
    }
    _PERFORMANCE_MODE_OPTION_NAMES = {
        "full_fidelity": "graphicsSettingsFullFidelityModeOption",
        "max_performance": "graphicsSettingsMaxPerformanceModeOption",
    }
    _PERFORMANCE_MODE_COPY_NAMES = {
        "full_fidelity": "graphicsSettingsFullFidelityModeCopy",
        "max_performance": "graphicsSettingsMaxPerformanceModeCopy",
    }

    def __init__(
        self,
        initial_settings: dict[str, Any] | None = None,
        parent=None,
        *,
        available_graph_themes: Sequence[tuple[str, str]] | None = None,
        manage_graph_themes_callback: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
        active_renderer_label: str | None = None,
    ) -> None:
        graph_themes = available_graph_themes or graph_theme_choices()
        self._available_graph_themes = tuple((str(theme_id), str(label)) for theme_id, label in graph_themes)
        if not self._available_graph_themes:
            self._available_graph_themes = graph_theme_choices()
        self._custom_graph_themes = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["custom_themes"])
        self._explicit_graph_theme_id = str(DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["selected_theme_id"])
        self._manage_graph_themes_callback = manage_graph_themes_callback
        self._active_renderer_label = self._normalize_active_renderer_label(active_renderer_label)
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
        self.add_section_page(self._build_performance_page())
        self.add_section_page(self._build_theme_page())
        self.add_section_page(self._build_layout_page())

    @staticmethod
    def _make_section_card(parent: QWidget) -> tuple[QWidget, QVBoxLayout]:
        """Return (card_widget, inner_layout) with the settingsCard styling."""
        card = QWidget(parent)
        card.setProperty("settingsCard", True)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(14, 10, 14, 10)
        inner.setSpacing(6)
        return card, inner

    @staticmethod
    def _make_section_title(text: str, parent: QWidget) -> QLabel:
        label = QLabel(text, parent)
        label.setProperty("settingsSectionTitle", True)
        return label

    @staticmethod
    def _normalize_active_renderer_label(value: Any) -> str:
        normalized = str(value or "").strip()
        return normalized or "Unavailable"

    def _build_canvas_page(self) -> QWidget:
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(12)

        # ── Overlay section ──
        outer.addWidget(self._make_section_title("Overlay", page))
        overlay_card, overlay_lay = self._make_section_card(page)
        self.show_grid_check = QCheckBox("Show grid overlay", overlay_card)
        self.show_grid_check.toggled.connect(self._sync_grid_style_visibility)
        self._grid_style_container = QWidget(overlay_card)
        grid_style_form = QFormLayout(self._grid_style_container)
        grid_style_form.setContentsMargins(20, 4, 0, 0)
        grid_style_form.setHorizontalSpacing(10)
        grid_style_form.setVerticalSpacing(0)
        self.grid_style_combo = QComboBox(self._grid_style_container)
        self.grid_style_combo.setObjectName("graphicsSettingsGridStyleCombo")
        for grid_style_id, label in GRID_OVERLAY_STYLE_CHOICES:
            self.grid_style_combo.addItem(label, grid_style_id)
        grid_style_form.addRow("Grid style", self.grid_style_combo)
        self.show_minimap_check = QCheckBox("Show minimap", overlay_card)
        self.show_port_labels_check = QCheckBox("Show port labels", overlay_card)
        self.show_port_labels_check.setObjectName("graphicsSettingsShowPortLabelsCheck")
        self.minimap_expanded_check = QCheckBox("Expand minimap by default", overlay_card)
        overlay_lay.addWidget(self.show_grid_check)
        overlay_lay.addWidget(self._grid_style_container)
        overlay_lay.addWidget(self.show_minimap_check)
        overlay_lay.addWidget(self.show_port_labels_check)
        self.minimap_expanded_check.setContentsMargins(20, 0, 0, 0)
        overlay_lay.addWidget(self.minimap_expanded_check)
        outer.addWidget(overlay_card)

        # ── Node Shadow section ──
        outer.addWidget(self._make_section_title("Node Shadow", page))
        shadow_card, shadow_lay = self._make_section_card(page)
        self.node_shadow_check = QCheckBox("Show node shadow", shadow_card)
        shadow_lay.addWidget(self.node_shadow_check)

        # Shadow detail sliders (visible when shadows are on)
        self._shadow_settings_container = QWidget(shadow_card)
        shadow_form = QFormLayout(self._shadow_settings_container)
        shadow_form.setContentsMargins(4, 6, 0, 0)
        shadow_form.setVerticalSpacing(8)

        self.shadow_strength_slider = self._build_slider(0, 100, shadow_card)
        self.shadow_softness_slider = self._build_slider(0, 100, shadow_card)
        self.shadow_offset_slider = self._build_slider(0, 20, shadow_card)

        shadow_form.addRow("Strength", self._slider_with_value(self.shadow_strength_slider))
        shadow_form.addRow("Softness", self._slider_with_value(self.shadow_softness_slider))
        shadow_form.addRow("Offset", self._slider_with_value(self.shadow_offset_slider))

        defaults = DEFAULT_GRAPHICS_SETTINGS["canvas"]
        initial_theme = resolve_graph_theme(
            DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["selected_theme_id"],
        )
        self._shadow_preview = ShadowPreviewWidget(
            initial_theme,
            defaults["shadow_strength"],
            defaults["shadow_softness"],
            defaults["shadow_offset"],
            self._shadow_settings_container,
        )
        shadow_form.addRow(self._shadow_preview)

        self.shadow_strength_slider.valueChanged.connect(self._update_shadow_preview)
        self.shadow_softness_slider.valueChanged.connect(self._update_shadow_preview)
        self.shadow_offset_slider.valueChanged.connect(self._update_shadow_preview)

        shadow_lay.addWidget(self._shadow_settings_container)
        outer.addWidget(shadow_card)

        self.node_shadow_check.toggled.connect(self._sync_shadow_settings_visibility)

        outer.addStretch(1)
        return page

    @staticmethod
    def _build_slider(lo: int, hi: int, parent: QWidget) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal, parent)
        slider.setRange(lo, hi)
        slider.setSingleStep(1)
        slider.setPageStep(10)
        return slider

    @staticmethod
    def _slider_with_value(slider: QSlider) -> QWidget:
        row = QWidget(slider.parent())
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(slider, stretch=1)
        label = QLabel(str(slider.value()), row)
        label.setFixedWidth(28)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(lambda v, lbl=label: lbl.setText(str(v)))
        layout.addWidget(label)
        return row

    def _sync_shadow_settings_visibility(self) -> None:
        self._shadow_settings_container.setVisible(self.node_shadow_check.isChecked())

    def _sync_grid_style_visibility(self) -> None:
        grid_style_container = getattr(self, "_grid_style_container", None)
        if grid_style_container is None:
            return
        grid_style_container.setVisible(self.show_grid_check.isChecked())

    def _update_shadow_preview(self) -> None:
        preview = getattr(self, "_shadow_preview", None)
        if preview is None:
            return
        preview.set_shadow(
            self.shadow_strength_slider.value(),
            self.shadow_softness_slider.value(),
            self.shadow_offset_slider.value(),
        )

    def _build_interaction_page(self) -> QWidget:
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(12)

        outer.addWidget(self._make_section_title("Snapping", page))
        card, card_lay = self._make_section_card(page)
        self.snap_to_grid_check = QCheckBox("Snap nodes to grid during edits", card)
        card_lay.addWidget(self.snap_to_grid_check)
        outer.addWidget(card)

        outer.addStretch(1)
        return page

    def _build_performance_page(self) -> QWidget:
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(12)

        outer.addWidget(self._make_section_title("Renderer", page))
        renderer_card, renderer_lay = self._make_section_card(page)
        renderer_form = QFormLayout()
        renderer_form.setContentsMargins(0, 0, 0, 0)
        renderer_form.setVerticalSpacing(8)
        self.active_renderer_value_label = QLabel(self._active_renderer_label, renderer_card)
        self.active_renderer_value_label.setObjectName("graphicsSettingsActiveRendererValue")
        self.active_renderer_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        renderer_form.addRow("Active renderer", self.active_renderer_value_label)
        renderer_lay.addLayout(renderer_form)
        outer.addWidget(renderer_card)

        outer.addWidget(self._make_section_title("Performance", page))
        performance_card, performance_lay = self._make_section_card(page)
        self.performance_mode_summary_label = QLabel(
            "Choose the app-wide graphics mode used across the shell and graph canvas.",
            performance_card,
        )
        self.performance_mode_summary_label.setObjectName("graphicsSettingsPerformanceModeSummary")
        self.performance_mode_summary_label.setWordWrap(True)
        performance_lay.addWidget(self.performance_mode_summary_label)
        performance_lay.setSpacing(8)

        self.performance_mode_group = QButtonGroup(performance_card)
        self.performance_mode_group.setExclusive(True)
        self.performance_mode_buttons: dict[str, QRadioButton] = {}
        self.performance_mode_option_cards: dict[str, QWidget] = {}
        self.performance_mode_copy_labels: dict[str, QLabel] = {}
        for mode_id, label in GRAPHICS_PERFORMANCE_MODE_CHOICES:
            option = _ClickableOptionCard(performance_card)
            option.setObjectName(self._PERFORMANCE_MODE_OPTION_NAMES.get(mode_id, ""))
            option.setProperty("performanceModeOption", True)
            option.setProperty("performanceModeSelected", False)
            option.setCursor(Qt.CursorShape.PointingHandCursor)
            option_layout = QVBoxLayout(option)
            option_layout.setContentsMargins(12, 10, 12, 10)
            option_layout.setSpacing(4)

            button = QRadioButton(label, option)
            button.setObjectName(self._PERFORMANCE_MODE_BUTTON_NAMES.get(mode_id, ""))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.performance_mode_group.addButton(button)
            self.performance_mode_buttons[mode_id] = button
            self.performance_mode_option_cards[mode_id] = option
            if mode_id == "full_fidelity":
                self.full_fidelity_mode_button = button
                self.full_fidelity_mode_option = option
            elif mode_id == "max_performance":
                self.max_performance_mode_button = button
                self.max_performance_mode_option = option
            option_layout.addWidget(button)

            copy_label = QLabel(self._PERFORMANCE_MODE_COPY.get(mode_id, ""), option)
            copy_label.setObjectName(self._PERFORMANCE_MODE_COPY_NAMES.get(mode_id, ""))
            copy_label.setWordWrap(True)
            copy_label.setIndent(24)
            copy_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.performance_mode_copy_labels[mode_id] = copy_label
            if mode_id == "full_fidelity":
                self.full_fidelity_mode_copy_label = copy_label
            elif mode_id == "max_performance":
                self.max_performance_mode_copy_label = copy_label
            option_layout.addWidget(copy_label)
            option.clicked.connect(lambda button=button: button.setChecked(True))
            button.toggled.connect(
                lambda checked, option=option: self._set_performance_mode_option_selected(option, checked)
            )

            performance_lay.addWidget(option)
        outer.addWidget(performance_card)

        outer.addStretch(1)
        return page

    def _build_theme_page(self) -> QWidget:
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(12)

        # ── Shell Theme section ──
        outer.addWidget(self._make_section_title("Shell Theme", page))
        shell_card, shell_lay = self._make_section_card(page)
        shell_form = QFormLayout()
        shell_form.setContentsMargins(0, 0, 0, 0)
        shell_form.setVerticalSpacing(8)
        self.theme_combo = QComboBox(shell_card)
        for theme_id, label in theme_choices():
            self.theme_combo.addItem(label, theme_id)
        self.theme_combo.currentIndexChanged.connect(self._on_shell_theme_changed)
        shell_form.addRow("Theme", self.theme_combo)
        shell_lay.addLayout(shell_form)
        outer.addWidget(shell_card)

        # ── Graph Theme section ──
        outer.addWidget(self._make_section_title("Graph Theme", page))
        graph_card, graph_lay = self._make_section_card(page)
        self.follow_shell_theme_check = QCheckBox("Follow shell theme", graph_card)
        self.follow_shell_theme_check.toggled.connect(self._on_follow_shell_theme_toggled)
        graph_lay.addWidget(self.follow_shell_theme_check)

        graph_form = QFormLayout()
        graph_form.setContentsMargins(0, 4, 0, 0)
        graph_form.setVerticalSpacing(8)
        self.graph_theme_combo = QComboBox(graph_card)
        self.graph_theme_combo.currentIndexChanged.connect(self._on_graph_theme_selection_changed)
        for theme_id, label in self._available_graph_themes:
            self.graph_theme_combo.addItem(label, theme_id)
        graph_theme_row = QWidget(graph_card)
        graph_theme_layout = QHBoxLayout(graph_theme_row)
        graph_theme_layout.setContentsMargins(0, 0, 0, 0)
        graph_theme_layout.setSpacing(6)
        graph_theme_layout.addWidget(self.graph_theme_combo, stretch=1)
        self.manage_graph_themes_button = QPushButton("Manage Graph Themes...", graph_theme_row)
        self.manage_graph_themes_button.setEnabled(self._manage_graph_themes_callback is not None)
        self.manage_graph_themes_button.clicked.connect(self._open_graph_theme_manager)
        graph_theme_layout.addWidget(self.manage_graph_themes_button, stretch=0)
        graph_form.addRow("Graph theme", graph_theme_row)
        graph_lay.addLayout(graph_form)

        initial_theme = resolve_graph_theme(
            self.graph_theme_combo.currentData() or "",
            custom_themes=self._custom_graph_themes,
        )
        self._graph_theme_preview = GraphThemePreviewWidget(initial_theme, graph_card)
        graph_lay.addWidget(self._graph_theme_preview)
        outer.addWidget(graph_card)

        self._sync_graph_theme_combo_enabled()

        outer.addStretch(1)
        return page

    def _build_layout_page(self) -> QWidget:
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(12)

        outer.addWidget(self._make_section_title("Shell Layout", page))
        card, card_lay = self._make_section_card(page)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(8)
        self.tab_strip_density_combo = QComboBox(card)
        for density_id, label in TAB_STRIP_DENSITY_CHOICES:
            self.tab_strip_density_combo.addItem(label, density_id)
        form.addRow("Tab strip density", self.tab_strip_density_combo)
        card_lay.addLayout(form)
        outer.addWidget(card)

        outer.addStretch(1)
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
        grid_style_id = settings["canvas"]["grid_style"]
        grid_style_index = self.grid_style_combo.findData(grid_style_id)
        self.grid_style_combo.setCurrentIndex(grid_style_index if grid_style_index >= 0 else 0)
        self._sync_grid_style_visibility()
        self.show_minimap_check.setChecked(settings["canvas"]["show_minimap"])
        self.show_port_labels_check.setChecked(settings["canvas"]["show_port_labels"])
        self.minimap_expanded_check.setChecked(settings["canvas"]["minimap_expanded"])
        self.node_shadow_check.setChecked(settings["canvas"]["node_shadow"])
        self.shadow_strength_slider.setValue(settings["canvas"]["shadow_strength"])
        self.shadow_softness_slider.setValue(settings["canvas"]["shadow_softness"])
        self.shadow_offset_slider.setValue(settings["canvas"]["shadow_offset"])
        self._sync_shadow_settings_visibility()
        self.snap_to_grid_check.setChecked(settings["interaction"]["snap_to_grid"])
        self._set_graphics_performance_mode(settings["performance"]["mode"])
        density_id = settings["shell"]["tab_strip_density"]
        density_index = self.tab_strip_density_combo.findData(density_id)
        self.tab_strip_density_combo.setCurrentIndex(density_index if density_index >= 0 else 0)
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
                    "grid_style": str(
                        self.grid_style_combo.currentData() or DEFAULT_GRAPHICS_SETTINGS["canvas"]["grid_style"]
                    ),
                    "show_minimap": self.show_minimap_check.isChecked(),
                    "show_port_labels": self.show_port_labels_check.isChecked(),
                    "minimap_expanded": self.minimap_expanded_check.isChecked(),
                    "node_shadow": self.node_shadow_check.isChecked(),
                    "shadow_strength": self.shadow_strength_slider.value(),
                    "shadow_softness": self.shadow_softness_slider.value(),
                    "shadow_offset": self.shadow_offset_slider.value(),
                },
                "interaction": {
                    "snap_to_grid": self.snap_to_grid_check.isChecked(),
                },
                "performance": {
                    "mode": self._graphics_performance_mode(),
                },
                "shell": {
                    "tab_strip_density": str(self.tab_strip_density_combo.currentData() or ""),
                },
                "theme": {
                    "theme_id": str(theme_id) if theme_id is not None else "",
                },
                "graph_theme": self._current_graph_theme_settings(),
            }
        )

    def _set_graphics_performance_mode(self, mode: str) -> None:
        button = self.performance_mode_buttons.get(str(mode))
        if button is None:
            button = self.performance_mode_buttons.get(DEFAULT_GRAPHICS_SETTINGS["performance"]["mode"])
        if button is not None:
            button.setChecked(True)

    def _graphics_performance_mode(self) -> str:
        for mode_id, button in self.performance_mode_buttons.items():
            if button.isChecked():
                return mode_id
        return str(DEFAULT_GRAPHICS_SETTINGS["performance"]["mode"])

    @staticmethod
    def _set_performance_mode_option_selected(option: QWidget, selected: bool) -> None:
        option.setProperty("performanceModeSelected", selected)
        style = option.style()
        if style is not None:
            style.unpolish(option)
            style.polish(option)
        option.update()

    def _sync_graph_theme_combo_enabled(self, _checked: bool | None = None) -> None:
        self.graph_theme_combo.setEnabled(not self.follow_shell_theme_check.isChecked())

    def _update_graph_theme_preview(self) -> None:
        preview = getattr(self, "_graph_theme_preview", None)
        if preview is None:
            return
        theme_id = self.graph_theme_combo.currentData()
        if theme_id is None:
            return
        theme = resolve_graph_theme(str(theme_id), custom_themes=self._custom_graph_themes)
        preview.set_theme(theme)
        shadow_preview = getattr(self, "_shadow_preview", None)
        if shadow_preview is not None:
            shadow_preview.set_theme(theme)

    def _on_follow_shell_theme_toggled(self, _checked: bool | None = None) -> None:
        if self.follow_shell_theme_check.isChecked():
            self._sync_graph_theme_combo_to_shell_theme()
        else:
            self._set_graph_theme_combo_selection(self._explicit_graph_theme_id)
        self._sync_graph_theme_combo_enabled()
        self._update_graph_theme_preview()

    def _on_shell_theme_changed(self, _index: int) -> None:
        if self.follow_shell_theme_check.isChecked():
            self._sync_graph_theme_combo_to_shell_theme()
        self._update_graph_theme_preview()

    def _on_graph_theme_selection_changed(self, _index: int) -> None:
        if self.follow_shell_theme_check.isChecked():
            return
        graph_theme_id = self.graph_theme_combo.currentData()
        self._explicit_graph_theme_id = resolve_graph_theme_id(
            str(graph_theme_id) if graph_theme_id is not None else "",
            custom_themes=self._custom_graph_themes,
        )
        self._update_graph_theme_preview()

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
        self._update_graph_theme_preview()

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
