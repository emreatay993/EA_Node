from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ea_node_editor.ui.dialogs.passive_style_controls import (
    ColorHexFieldControl,
    DEFAULT_LINE_EDIT_STYLE,
    INVALID_LINE_EDIT_STYLE,
    INVALID_SWATCH_STYLE,
    is_valid_hex_color,
    swatch_style,
)
from ea_node_editor.ui.graph_theme import (
    DEFAULT_GRAPH_THEME_ID,
    GRAPH_THEME_REGISTRY,
    create_blank_custom_graph_theme,
    duplicate_graph_theme_as_custom,
    is_custom_graph_theme_id,
    resolve_graph_theme,
    resolve_graph_theme_id,
    serialize_custom_graph_themes,
)
from ea_node_editor.ui.shell.controllers.app_preferences_controller import normalize_graph_theme_settings

_TOKEN_LABEL_EXPANSIONS: dict[str, str] = {
    "bg": "Background",
    "fg": "Foreground",
    "btn": "Button",
}


# ---------------------------------------------------------------------------
# Helper widgets
# ---------------------------------------------------------------------------


class _CollapsibleSection(QWidget):
    """A collapsible section with a toggle header and a content area."""

    def __init__(
        self,
        title: str,
        token_count: int,
        parent: QWidget | None = None,
        *,
        initially_expanded: bool = True,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._token_count = token_count

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toggle_button = QPushButton(self)
        self._toggle_button.setCheckable(True)
        self._toggle_button.setFlat(True)
        self._toggle_button.setFixedHeight(32)
        self._toggle_button.setObjectName("collapsibleSectionHeader")
        self._toggle_button.setStyleSheet(
            "QPushButton#collapsibleSectionHeader {"
            "  text-align: left;"
            "  font-weight: 600;"
            "  padding: 4px 8px;"
            "  border: none;"
            "  border-bottom: 1px solid palette(mid);"
            "}"
            "QPushButton#collapsibleSectionHeader:hover {"
            "  background: rgba(128, 128, 128, 0.1);"
            "}"
        )
        self._toggle_button.toggled.connect(self._on_toggled)
        layout.addWidget(self._toggle_button)

        self._content = QWidget(self)
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 4, 0, 4)
        content_layout.setSpacing(0)
        layout.addWidget(self._content)

        self._toggle_button.setChecked(initially_expanded)
        self._update_header_text(initially_expanded)

    @property
    def content_widget(self) -> QWidget:
        return self._content

    @property
    def expanded(self) -> bool:
        return self._toggle_button.isChecked()

    @expanded.setter
    def expanded(self, value: bool) -> None:
        self._toggle_button.setChecked(value)

    def _on_toggled(self, checked: bool) -> None:
        self._content.setVisible(checked)
        self._update_header_text(checked)

    def _update_header_text(self, expanded: bool) -> None:
        arrow = "\u25BC" if expanded else "\u25B6"
        self._toggle_button.setText(f"  {arrow}  {self._title} ({self._token_count})")


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------


class GraphThemeEditorDialog(QDialog):
    _THEME_ID_ROLE = Qt.ItemDataRole.UserRole
    _TOKEN_SECTIONS = (
        ("node_tokens", "Node Tokens"),
        ("edge_tokens", "Edge Tokens"),
        ("category_accent_tokens", "Category Accent Tokens"),
        ("port_kind_tokens", "Port Kind Tokens"),
    )

    def __init__(
        self,
        initial_settings: Any | None = None,
        parent=None,
        *,
        live_apply_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Graph Theme Manager")
        self.setModal(True)
        self.resize(1040, 720)

        normalized = normalize_graph_theme_settings(initial_settings)
        self._follow_shell_theme = bool(normalized["follow_shell_theme"])
        self._custom_graph_themes = serialize_custom_graph_themes(normalized["custom_themes"])
        self._explicit_theme_id = resolve_graph_theme_id(
            normalized["selected_theme_id"],
            custom_themes=self._custom_graph_themes,
        )
        self._preview_theme_id = self._explicit_theme_id
        self._live_apply_callback = live_apply_callback
        self._use_selected_requested = False
        self._theme_items: dict[str, QTreeWidgetItem] = {}
        self._token_value_fields: dict[str, dict[str, QLineEdit]] = {}
        self._token_swatch_frames: dict[str, dict[str, QFrame]] = {}
        self._suppress_token_sync = False
        self._collapsed_sections: dict[str, bool] = {}
        self._collapsible_sections: dict[str, _CollapsibleSection] = {}

        self._build_ui()
        self._rebuild_theme_tree(selected_theme_id=self._preview_theme_id)

    @property
    def use_selected_requested(self) -> bool:
        return self._use_selected_requested

    @property
    def theme_name_field(self) -> QLabel:
        """Backward-compatible accessor (tests)."""
        return self._top_bar_name

    @property
    def theme_id_field(self) -> QLabel:
        """Backward-compatible accessor (tests)."""
        return self._top_bar_id

    @property
    def theme_mode_field(self) -> QLabel:
        """Backward-compatible accessor (tests)."""
        return self._top_bar_status

    def reject(self) -> None:
        self._accept_without_using_selected()

    def graph_theme_settings(self) -> dict[str, Any]:
        custom_themes = serialize_custom_graph_themes(self._custom_graph_themes)
        selected_theme_id = resolve_graph_theme_id(self._explicit_theme_id, custom_themes=custom_themes)
        return normalize_graph_theme_settings(
            {
                "follow_shell_theme": self._follow_shell_theme,
                "selected_theme_id": selected_theme_id,
                "custom_themes": copy.deepcopy(custom_themes),
            }
        )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        # --- Top bar ---
        top_bar = self._build_top_bar()
        root.addWidget(top_bar)

        sep1 = _h_separator()
        root.addWidget(sep1)

        # --- Splitter ---
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._build_library_panel())
        splitter.addWidget(self._build_preview_panel())
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

        sep2 = _h_separator()
        root.addWidget(sep2)

        # --- Bottom bar ---
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 8, 0, 0)

        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self._accept_without_using_selected)
        bottom_bar.addWidget(self.close_button)

        bottom_bar.addStretch(1)

        self.use_selected_button = QPushButton("Use Selected", self)
        self.use_selected_button.setObjectName("primaryButton")
        self.use_selected_button.setStyleSheet(
            "QPushButton#primaryButton {"
            "  background: #1D8CE0;"
            "  color: #ffffff;"
            "  border: 1px solid #60CDFF;"
            "  padding: 6px 20px;"
            "  font-weight: 600;"
            "  border-radius: 3px;"
            "}"
            "QPushButton#primaryButton:hover {"
            "  background: #2998E8;"
            "}"
            "QPushButton#primaryButton:pressed {"
            "  background: #1578C0;"
            "}"
            "QPushButton#primaryButton:disabled {"
            "  background: #555555;"
            "  color: #999999;"
            "  border: 1px solid #666666;"
            "}"
        )
        self.use_selected_button.setToolTip("Set this theme as the active graph theme")
        self.use_selected_button.clicked.connect(self._use_selected_theme)
        bottom_bar.addWidget(self.use_selected_button)
        root.addLayout(bottom_bar)

    def _build_top_bar(self) -> QWidget:
        bar = QWidget(self)
        bar.setFixedHeight(44)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        self._top_bar_name = QLabel(bar)
        name_font = self._top_bar_name.font()
        name_font.setPointSize(11)
        name_font.setBold(True)
        self._top_bar_name.setFont(name_font)
        layout.addWidget(self._top_bar_name)

        self._top_bar_id = QLabel(bar)
        self._top_bar_id.setStyleSheet("color: #8899aa; font-size: 11px;")
        layout.addWidget(self._top_bar_id)

        layout.addStretch(1)

        self._top_bar_status = QLabel(bar)
        self._top_bar_status.setStyleSheet(
            "background: rgba(128, 128, 128, 0.15);"
            "padding: 2px 10px;"
            "border-radius: 10px;"
            "font-size: 11px;"
        )
        layout.addWidget(self._top_bar_status)

        return bar

    def _build_library_panel(self) -> QWidget:
        panel = QWidget(self)
        panel.setMinimumWidth(240)
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 8, 0)
        layout.setSpacing(8)

        title = QLabel("Themes", panel)
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.theme_tree = QTreeWidget(panel)
        self.theme_tree.setHeaderHidden(True)
        self.theme_tree.setIndentation(16)
        self.theme_tree.setAlternatingRowColors(False)
        self.theme_tree.setRootIsDecorated(True)
        self.theme_tree.currentItemChanged.connect(self._on_current_item_changed)
        layout.addWidget(self.theme_tree, stretch=1)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self.new_button = QPushButton("+ New", panel)
        self.duplicate_button = QPushButton("Duplicate", panel)
        row1.addWidget(self.new_button)
        row1.addWidget(self.duplicate_button)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.rename_button = QPushButton("Rename", panel)
        self.delete_button = QPushButton("Delete", panel)
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.setStyleSheet(
            "QPushButton#dangerButton:hover { color: #C75050; }"
        )
        row2.addWidget(self.rename_button)
        row2.addWidget(self.delete_button)
        layout.addLayout(row2)

        self.new_button.clicked.connect(self._create_theme)
        self.duplicate_button.clicked.connect(self._duplicate_selected_theme)
        self.rename_button.clicked.connect(self._rename_selected_theme)
        self.delete_button.clicked.connect(self._delete_selected_theme)

        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 0, 0)
        layout.setSpacing(6)

        self.preview_note = QLabel(panel)
        self.preview_note.setWordWrap(True)
        self.preview_note.setStyleSheet("color: #8899aa; font-size: 11px; padding: 2px 0;")
        layout.addWidget(self.preview_note)

        self.validation_message = QLabel("Fix invalid colors before closing. Use #RRGGBB or #AARRGGBB.", panel)
        self.validation_message.setWordWrap(True)
        self.validation_message.setStyleSheet("color: #C75050;")
        self.validation_message.hide()
        layout.addWidget(self.validation_message)

        preview_scroll = QScrollArea(panel)
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setFrameShape(QFrame.Shape.NoFrame)
        preview_content = QWidget(preview_scroll)
        preview_layout = QVBoxLayout(preview_content)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(4)

        reference_theme = resolve_graph_theme(DEFAULT_GRAPH_THEME_ID)
        for section_name, section_title in self._TOKEN_SECTIONS:
            section_mapping = getattr(reference_theme, section_name).as_dict()
            token_count = len(section_mapping)

            initially_expanded = self._collapsed_sections.get(section_name, True)
            collapsible = _CollapsibleSection(
                section_title, token_count, preview_content, initially_expanded=initially_expanded
            )
            self._collapsible_sections[section_name] = collapsible

            form = QFormLayout()
            form.setContentsMargins(8, 4, 8, 4)
            form.setSpacing(6)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            value_fields: dict[str, QLineEdit] = {}
            swatch_frames: dict[str, QFrame] = {}
            for token_name in section_mapping:
                control = ColorHexFieldControl(
                    collapsible.content_widget,
                    allow_empty=False,
                    color_dialog_title=f"Pick color for {_token_label(token_name)}",
                )
                control.setObjectNames(
                    value_name=f"{section_name}_{token_name}_value",
                    swatch_name=f"{section_name}_{token_name}_swatch",
                )
                control.valueChanged.connect(
                    lambda text, current_section=section_name, current_token=token_name: self._on_token_text_changed(
                        current_section,
                        current_token,
                        text,
                    )
                )
                form.addRow(_token_label(token_name), control)

                value_fields[token_name] = control.line_edit
                swatch_frames[token_name] = control.swatch

            self._token_value_fields[section_name] = value_fields
            self._token_swatch_frames[section_name] = swatch_frames
            collapsible.content_widget.layout().addLayout(form)
            preview_layout.addWidget(collapsible)

        preview_layout.addStretch(1)
        preview_scroll.setWidget(preview_content)
        layout.addWidget(preview_scroll, stretch=1)
        return panel

    # ------------------------------------------------------------------
    # Theme tree
    # ------------------------------------------------------------------

    def _rebuild_theme_tree(self, *, selected_theme_id: object | None = None) -> None:
        selection = resolve_graph_theme_id(
            selected_theme_id if selected_theme_id is not None else self._preview_theme_id,
            custom_themes=self._custom_graph_themes,
        )

        self.theme_tree.blockSignals(True)
        self.theme_tree.clear()
        self._theme_items = {}

        active_id = resolve_graph_theme_id(self._explicit_theme_id, custom_themes=self._custom_graph_themes)
        bold_font = QFont()
        bold_font.setBold(True)
        muted_brush = QBrush(QColor("#8899aa"))

        built_in_root = _section_item("Built-in Themes")
        built_in_root.setForeground(0, muted_brush)
        for theme in GRAPH_THEME_REGISTRY.values():
            label = theme.label
            if theme.theme_id == active_id:
                label += " (active)"
            item = QTreeWidgetItem([label])
            item.setData(0, self._THEME_ID_ROLE, theme.theme_id)
            if theme.theme_id == active_id:
                item.setFont(0, bold_font)
            built_in_root.addChild(item)
            self._theme_items[theme.theme_id] = item
        self.theme_tree.addTopLevelItem(built_in_root)
        built_in_root.setExpanded(True)

        custom_root = _section_item("Custom Themes")
        custom_root.setForeground(0, muted_brush)
        for theme in self._custom_graph_themes:
            theme_id = str(theme.get("theme_id", "")).strip()
            label = str(theme.get("label", theme_id)).strip() or theme_id
            if theme_id == active_id:
                label += " (active)"
            item = QTreeWidgetItem([label])
            item.setData(0, self._THEME_ID_ROLE, theme_id)
            if theme_id == active_id:
                item.setFont(0, bold_font)
            custom_root.addChild(item)
            self._theme_items[theme_id] = item
        self.theme_tree.addTopLevelItem(custom_root)
        custom_root.setExpanded(True)
        self.theme_tree.blockSignals(False)

        self._select_theme_item(selection)

    def _select_theme_item(self, theme_id: object) -> None:
        resolved_theme_id = resolve_graph_theme_id(theme_id, custom_themes=self._custom_graph_themes)
        item = self._theme_items.get(resolved_theme_id)
        if item is None and self._theme_items:
            item = next(iter(self._theme_items.values()))
        if item is None:
            self._sync_preview()
            return
        self.theme_tree.setCurrentItem(item)
        self._preview_theme_id = str(item.data(0, self._THEME_ID_ROLE) or resolved_theme_id)
        self._sync_preview()

    def _on_current_item_changed(
        self,
        current: QTreeWidgetItem | None,
        _previous: QTreeWidgetItem | None,
    ) -> None:
        theme_id = self._theme_id_from_item(current)
        if theme_id is not None:
            self._preview_theme_id = theme_id
        self._sync_preview()

    # ------------------------------------------------------------------
    # Preview sync
    # ------------------------------------------------------------------

    def _sync_preview(self) -> None:
        theme = resolve_graph_theme(self._preview_theme_id, custom_themes=self._custom_graph_themes)
        is_custom = is_custom_graph_theme_id(theme.theme_id)
        is_active_explicit = self._is_active_explicit_custom_theme(theme.theme_id)

        # Top bar
        self._top_bar_name.setText(theme.label)
        self._top_bar_id.setText(theme.theme_id)
        if is_active_explicit:
            self._top_bar_status.setText("Custom theme (editable, active explicit theme)")
        elif is_custom:
            self._top_bar_status.setText("Custom theme (editable)")
        else:
            self._top_bar_status.setText("Built-in theme (read-only)")

        # Context note
        self.preview_note.setText(
            "Duplicate a built-in theme to create an editable copy."
            if not is_custom
            else "Editing tokens applies live when this is the active theme."
        )

        # Token fields
        self._suppress_token_sync = True
        try:
            for section_name, _section_title in self._TOKEN_SECTIONS:
                tokens = getattr(theme, section_name).as_dict()
                for token_name, token_value in tokens.items():
                    field = self._token_value_fields[section_name][token_name]
                    field.setReadOnly(not is_custom)
                    if not is_custom:
                        field.setStyleSheet("background: rgba(128, 128, 128, 0.08);")
                    else:
                        field.setStyleSheet(DEFAULT_LINE_EDIT_STYLE)
                    field.setText(token_value)

                    swatch = self._token_swatch_frames[section_name][token_name]
                    if hasattr(swatch, "editable"):
                        swatch.editable = is_custom
                    self._set_token_swatch(section_name, token_name, token_value)
        finally:
            self._suppress_token_sync = False

        self.validation_message.setVisible(False)

        has_selection = bool(theme.theme_id)
        self.duplicate_button.setEnabled(has_selection)
        self.use_selected_button.setEnabled(has_selection)
        self.rename_button.setEnabled(is_custom)
        self.delete_button.setEnabled(is_custom)

    # ------------------------------------------------------------------
    # Theme CRUD
    # ------------------------------------------------------------------

    def _create_theme(self) -> None:
        created_theme = create_blank_custom_graph_theme(custom_themes=self._custom_graph_themes)
        self._custom_graph_themes.append(created_theme.as_dict())
        self._rebuild_theme_tree(selected_theme_id=created_theme.theme_id)

    def _duplicate_selected_theme(self) -> None:
        source_theme_id = self._preview_theme_id
        created_theme = duplicate_graph_theme_as_custom(source_theme_id, custom_themes=self._custom_graph_themes)
        self._custom_graph_themes.append(created_theme.as_dict())
        self._rebuild_theme_tree(selected_theme_id=created_theme.theme_id)

    def _rename_selected_theme(self) -> None:
        theme_id = self._preview_theme_id
        index = _custom_theme_index(self._custom_graph_themes, theme_id)
        if index < 0:
            return
        current_label = str(self._custom_graph_themes[index].get("label", "")).strip()
        label, accepted = QInputDialog.getText(
            self,
            "Rename Graph Theme",
            "Theme name:",
            text=current_label,
        )
        if not accepted:
            return
        normalized_label = str(label).strip()
        if not normalized_label:
            return
        self._custom_graph_themes[index]["label"] = normalized_label
        self._rebuild_theme_tree(selected_theme_id=theme_id)
        self._maybe_live_apply(theme_id)

    def _delete_selected_theme(self) -> None:
        theme_id = self._preview_theme_id
        index = _custom_theme_index(self._custom_graph_themes, theme_id)
        if index < 0:
            return
        label = str(self._custom_graph_themes[index].get("label", theme_id)).strip() or str(theme_id)
        choice = QMessageBox.question(
            self,
            "Delete Graph Theme",
            f"Delete the custom graph theme '{label}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        del self._custom_graph_themes[index]
        if str(self._explicit_theme_id).strip().lower() == str(theme_id).strip().lower():
            self._explicit_theme_id = resolve_graph_theme_id(self._explicit_theme_id, custom_themes=self._custom_graph_themes)
        self._preview_theme_id = resolve_graph_theme_id(theme_id, custom_themes=self._custom_graph_themes)
        self._rebuild_theme_tree(selected_theme_id=self._preview_theme_id)

    def _use_selected_theme(self) -> None:
        if not self._validate_current_theme_before_save():
            return
        self._use_selected_requested = True
        self._follow_shell_theme = False
        self._explicit_theme_id = resolve_graph_theme_id(self._preview_theme_id, custom_themes=self._custom_graph_themes)
        self.accept()

    def _accept_without_using_selected(self) -> None:
        if not self._validate_current_theme_before_save():
            return
        self._use_selected_requested = False
        self.accept()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_current_theme_before_save(self) -> bool:
        theme = resolve_graph_theme(self._preview_theme_id, custom_themes=self._custom_graph_themes)
        if not is_custom_graph_theme_id(theme.theme_id):
            return True
        for section_name, _section_title in self._TOKEN_SECTIONS:
            for token_name, field in self._token_value_fields[section_name].items():
                if is_valid_hex_color(field.text()):
                    continue
                self.validation_message.setVisible(True)
                QMessageBox.warning(
                    self,
                    "Invalid Graph Theme Color",
                    "Custom theme colors must use #RRGGBB or #AARRGGBB before the theme can be saved.",
                )
                field.setStyleSheet(INVALID_LINE_EDIT_STYLE)
                self._token_swatch_frames[section_name][token_name].setStyleSheet(INVALID_SWATCH_STYLE)
                field.setFocus(Qt.FocusReason.OtherFocusReason)
                return False
        self.validation_message.setVisible(False)
        return True

    # ------------------------------------------------------------------
    # Token editing
    # ------------------------------------------------------------------

    def _on_token_text_changed(self, section_name: str, token_name: str, text: str) -> None:
        if self._suppress_token_sync:
            return
        theme_id = self._preview_theme_id
        theme_index = _custom_theme_index(self._custom_graph_themes, theme_id)
        if theme_index < 0:
            return

        field = self._token_value_fields[section_name][token_name]
        swatch = self._token_swatch_frames[section_name][token_name]
        normalized = str(text).strip()
        if not is_valid_hex_color(normalized):
            field.setStyleSheet(INVALID_LINE_EDIT_STYLE)
            swatch.setStyleSheet(INVALID_SWATCH_STYLE)
            self._sync_validation_message()
            return

        field.setStyleSheet(DEFAULT_LINE_EDIT_STYLE)
        section_tokens = self._custom_graph_themes[theme_index].get(section_name)
        if not isinstance(section_tokens, dict):
            section_tokens = {}
            self._custom_graph_themes[theme_index][section_name] = section_tokens
        section_tokens[token_name] = normalized
        swatch.setStyleSheet(swatch_style(normalized))
        self._sync_validation_message()
        self._maybe_live_apply(theme_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _maybe_live_apply(self, theme_id: object) -> None:
        if self._live_apply_callback is None:
            return
        if not self._is_active_explicit_custom_theme(theme_id):
            return
        self._live_apply_callback(self.graph_theme_settings())

    def _is_active_explicit_custom_theme(self, theme_id: object) -> bool:
        if self._follow_shell_theme:
            return False
        resolved_theme_id = resolve_graph_theme_id(theme_id, custom_themes=self._custom_graph_themes)
        explicit_theme_id = resolve_graph_theme_id(self._explicit_theme_id, custom_themes=self._custom_graph_themes)
        return is_custom_graph_theme_id(resolved_theme_id) and resolved_theme_id == explicit_theme_id

    def _set_token_swatch(self, section_name: str, token_name: str, token_value: str) -> None:
        self._token_swatch_frames[section_name][token_name].setStyleSheet(swatch_style(token_value))

    def _sync_validation_message(self) -> None:
        theme = resolve_graph_theme(self._preview_theme_id, custom_themes=self._custom_graph_themes)
        if not is_custom_graph_theme_id(theme.theme_id):
            self.validation_message.setVisible(False)
            return
        has_invalid_field = any(
            not is_valid_hex_color(field.text())
            for fields in self._token_value_fields.values()
            for field in fields.values()
        )
        self.validation_message.setVisible(has_invalid_field)

    def _theme_id_from_item(self, item: QTreeWidgetItem | None) -> str | None:
        if item is None:
            return None
        theme_id = item.data(0, self._THEME_ID_ROLE)
        if theme_id is None:
            return None
        normalized = str(theme_id).strip()
        return normalized or None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _custom_theme_index(custom_themes: list[dict[str, object]], theme_id: object) -> int:
    normalized_theme_id = str(theme_id).strip().lower()
    for index, theme in enumerate(custom_themes):
        if str(theme.get("theme_id", "")).strip().lower() == normalized_theme_id:
            return index
    return -1


def _section_item(label: str) -> QTreeWidgetItem:
    item = QTreeWidgetItem([label])
    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
    return item


def _token_label(token_name: str) -> str:
    parts = str(token_name).split("_")
    expanded = [_TOKEN_LABEL_EXPANSIONS.get(p, p) for p in parts]
    return " ".join(expanded).title()


def _h_separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFrameShadow(QFrame.Shadow.Plain)
    sep.setFixedHeight(1)
    sep.setStyleSheet("color: rgba(128, 128, 128, 0.3);")
    return sep


__all__ = ["GraphThemeEditorDialog"]
