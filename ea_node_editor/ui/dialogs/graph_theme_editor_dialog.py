from __future__ import annotations

import copy
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
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


class GraphThemeEditorDialog(QDialog):
    _THEME_ID_ROLE = Qt.ItemDataRole.UserRole
    _TOKEN_SECTIONS = (
        ("node_tokens", "Node Tokens"),
        ("edge_tokens", "Edge Tokens"),
        ("category_accent_tokens", "Category Accent Tokens"),
        ("port_kind_tokens", "Port Kind Tokens"),
    )

    def __init__(self, initial_settings: Any | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Graph Theme Manager")
        self.setModal(True)
        self.resize(980, 680)

        normalized = normalize_graph_theme_settings(initial_settings)
        self._follow_shell_theme = bool(normalized["follow_shell_theme"])
        self._custom_graph_themes = serialize_custom_graph_themes(normalized["custom_themes"])
        self._selected_theme_id = resolve_graph_theme_id(
            normalized["selected_theme_id"],
            custom_themes=self._custom_graph_themes,
        )
        self._use_selected_requested = False
        self._theme_items: dict[str, QTreeWidgetItem] = {}
        self._token_value_fields: dict[str, dict[str, QLineEdit]] = {}
        self._token_swatch_frames: dict[str, dict[str, QFrame]] = {}

        self._build_ui()
        self._rebuild_theme_tree(selected_theme_id=self._selected_theme_id)

    @property
    def use_selected_requested(self) -> bool:
        return self._use_selected_requested

    def reject(self) -> None:
        self._accept_without_using_selected()

    def graph_theme_settings(self) -> dict[str, Any]:
        custom_themes = serialize_custom_graph_themes(self._custom_graph_themes)
        selected_theme_id = resolve_graph_theme_id(self._selected_theme_id, custom_themes=custom_themes)
        return normalize_graph_theme_settings(
            {
                "follow_shell_theme": False if self._use_selected_requested else self._follow_shell_theme,
                "selected_theme_id": selected_theme_id,
                "custom_themes": copy.deepcopy(custom_themes),
            }
        )

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        header = QLabel(
            "Manage built-in and custom graph themes. Token previews are read-only in this packet; "
            "editing and live apply are deferred to P08.",
            self,
        )
        header.setWordWrap(True)
        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._build_library_panel())
        splitter.addWidget(self._build_preview_panel())
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self._accept_without_using_selected)
        actions.addWidget(self.close_button)
        root.addLayout(actions)

    def _build_library_panel(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.theme_tree = QTreeWidget(panel)
        self.theme_tree.setHeaderHidden(True)
        self.theme_tree.currentItemChanged.connect(self._on_current_item_changed)
        layout.addWidget(self.theme_tree, stretch=1)

        button_grid = QGridLayout()
        button_grid.setContentsMargins(0, 0, 0, 0)
        button_grid.setHorizontalSpacing(6)
        button_grid.setVerticalSpacing(6)

        self.new_button = QPushButton("New", panel)
        self.duplicate_button = QPushButton("Duplicate", panel)
        self.rename_button = QPushButton("Rename", panel)
        self.delete_button = QPushButton("Delete", panel)
        self.use_selected_button = QPushButton("Use Selected", panel)

        self.new_button.clicked.connect(self._create_theme)
        self.duplicate_button.clicked.connect(self._duplicate_selected_theme)
        self.rename_button.clicked.connect(self._rename_selected_theme)
        self.delete_button.clicked.connect(self._delete_selected_theme)
        self.use_selected_button.clicked.connect(self._use_selected_theme)

        button_grid.addWidget(self.new_button, 0, 0)
        button_grid.addWidget(self.duplicate_button, 0, 1)
        button_grid.addWidget(self.rename_button, 1, 0)
        button_grid.addWidget(self.delete_button, 1, 1)
        button_grid.addWidget(self.use_selected_button, 2, 0, 1, 2)
        layout.addLayout(button_grid)
        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        details_group = QGroupBox("Theme Details", panel)
        details_form = QFormLayout(details_group)
        self.theme_name_field = QLineEdit(details_group)
        self.theme_name_field.setReadOnly(True)
        self.theme_id_field = QLineEdit(details_group)
        self.theme_id_field.setReadOnly(True)
        self.theme_mode_field = QLineEdit(details_group)
        self.theme_mode_field.setReadOnly(True)
        details_form.addRow("Name", self.theme_name_field)
        details_form.addRow("Theme ID", self.theme_id_field)
        details_form.addRow("Mode", self.theme_mode_field)
        layout.addWidget(details_group)

        preview_note = QLabel(
            "Preview only. Built-in themes are read-only, and custom token editing is intentionally deferred.",
            panel,
        )
        preview_note.setWordWrap(True)
        layout.addWidget(preview_note)

        preview_scroll = QScrollArea(panel)
        preview_scroll.setWidgetResizable(True)
        preview_content = QWidget(preview_scroll)
        preview_layout = QVBoxLayout(preview_content)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)

        reference_theme = resolve_graph_theme(DEFAULT_GRAPH_THEME_ID)
        for section_name, section_title in self._TOKEN_SECTIONS:
            section_mapping = getattr(reference_theme, section_name).as_dict()
            group_box = QGroupBox(section_title, preview_content)
            form = QFormLayout(group_box)
            value_fields: dict[str, QLineEdit] = {}
            swatch_frames: dict[str, QFrame] = {}
            for token_name in section_mapping:
                row_widget = QWidget(group_box)
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)

                value_field = QLineEdit(row_widget)
                value_field.setReadOnly(True)
                value_field.setObjectName(f"{section_name}_{token_name}_value")
                swatch = QFrame(row_widget)
                swatch.setFixedSize(20, 20)
                swatch.setFrameShape(QFrame.Shape.StyledPanel)
                swatch.setObjectName(f"{section_name}_{token_name}_swatch")

                row_layout.addWidget(value_field, stretch=1)
                row_layout.addWidget(swatch, stretch=0, alignment=Qt.AlignmentFlag.AlignVCenter)
                form.addRow(_token_label(token_name), row_widget)

                value_fields[token_name] = value_field
                swatch_frames[token_name] = swatch

            self._token_value_fields[section_name] = value_fields
            self._token_swatch_frames[section_name] = swatch_frames
            preview_layout.addWidget(group_box)

        preview_layout.addStretch(1)
        preview_scroll.setWidget(preview_content)
        layout.addWidget(preview_scroll, stretch=1)
        return panel

    def _rebuild_theme_tree(self, *, selected_theme_id: object | None = None) -> None:
        selection = resolve_graph_theme_id(
            selected_theme_id if selected_theme_id is not None else self._selected_theme_id,
            custom_themes=self._custom_graph_themes,
        )

        self.theme_tree.blockSignals(True)
        self.theme_tree.clear()
        self._theme_items = {}

        built_in_root = _section_item("Built-in Themes")
        for theme in GRAPH_THEME_REGISTRY.values():
            item = QTreeWidgetItem([theme.label])
            item.setData(0, self._THEME_ID_ROLE, theme.theme_id)
            built_in_root.addChild(item)
            self._theme_items[theme.theme_id] = item
        self.theme_tree.addTopLevelItem(built_in_root)
        built_in_root.setExpanded(True)

        custom_root = _section_item("Custom Themes")
        for theme in self._custom_graph_themes:
            theme_id = str(theme.get("theme_id", "")).strip()
            item = QTreeWidgetItem([str(theme.get("label", theme_id)).strip() or theme_id])
            item.setData(0, self._THEME_ID_ROLE, theme_id)
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
        self._selected_theme_id = str(item.data(0, self._THEME_ID_ROLE) or resolved_theme_id)
        self._sync_preview()

    def _on_current_item_changed(
        self,
        current: QTreeWidgetItem | None,
        _previous: QTreeWidgetItem | None,
    ) -> None:
        theme_id = self._theme_id_from_item(current)
        if theme_id is not None:
            self._selected_theme_id = theme_id
        self._sync_preview()

    def _sync_preview(self) -> None:
        theme = resolve_graph_theme(self._selected_theme_id, custom_themes=self._custom_graph_themes)
        self.theme_name_field.setText(theme.label)
        self.theme_id_field.setText(theme.theme_id)
        self.theme_mode_field.setText(
            "Custom theme (preview only in P07)"
            if is_custom_graph_theme_id(theme.theme_id)
            else "Built-in theme (read-only)"
        )

        for section_name, _section_title in self._TOKEN_SECTIONS:
            tokens = getattr(theme, section_name).as_dict()
            for token_name, token_value in tokens.items():
                self._token_value_fields[section_name][token_name].setText(token_value)
                self._token_swatch_frames[section_name][token_name].setStyleSheet(
                    f"background-color: {token_value}; border: 1px solid #5f6b7a;"
                )

        is_custom = is_custom_graph_theme_id(theme.theme_id)
        has_selection = bool(theme.theme_id)
        self.duplicate_button.setEnabled(has_selection)
        self.use_selected_button.setEnabled(has_selection)
        self.rename_button.setEnabled(is_custom)
        self.delete_button.setEnabled(is_custom)

    def _create_theme(self) -> None:
        created_theme = create_blank_custom_graph_theme(custom_themes=self._custom_graph_themes)
        self._custom_graph_themes.append(created_theme.as_dict())
        self._rebuild_theme_tree(selected_theme_id=created_theme.theme_id)

    def _duplicate_selected_theme(self) -> None:
        source_theme_id = self._selected_theme_id
        created_theme = duplicate_graph_theme_as_custom(source_theme_id, custom_themes=self._custom_graph_themes)
        self._custom_graph_themes.append(created_theme.as_dict())
        self._rebuild_theme_tree(selected_theme_id=created_theme.theme_id)

    def _rename_selected_theme(self) -> None:
        theme_id = self._selected_theme_id
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

    def _delete_selected_theme(self) -> None:
        theme_id = self._selected_theme_id
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
        self._selected_theme_id = resolve_graph_theme_id(theme_id, custom_themes=self._custom_graph_themes)
        self._rebuild_theme_tree(selected_theme_id=self._selected_theme_id)

    def _use_selected_theme(self) -> None:
        self._use_selected_requested = True
        self.accept()

    def _accept_without_using_selected(self) -> None:
        self._use_selected_requested = False
        self.accept()

    def _theme_id_from_item(self, item: QTreeWidgetItem | None) -> str | None:
        if item is None:
            return None
        theme_id = item.data(0, self._THEME_ID_ROLE)
        if theme_id is None:
            return None
        normalized = str(theme_id).strip()
        return normalized or None


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
    return str(token_name).replace("_", " ").title()


__all__ = ["GraphThemeEditorDialog"]
