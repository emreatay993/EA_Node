from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import QFrame, QPushButton, QTreeWidgetItem, QVBoxLayout, QWidget

from ea_node_editor.ui.graph_theme import (
    GRAPH_THEME_REGISTRY,
    is_custom_graph_theme_id,
    resolve_graph_theme,
    resolve_graph_theme_id,
)

if TYPE_CHECKING:
    from ea_node_editor.ui.graph_theme import GraphThemeDefinition

_TOKEN_LABEL_EXPANSIONS: dict[str, str] = {
    "bg": "Background",
    "fg": "Foreground",
    "btn": "Button",
}


@dataclass(frozen=True, slots=True)
class GraphThemePreviewMetadata:
    theme: GraphThemeDefinition
    is_custom: bool
    is_active_explicit: bool
    status_text: str
    preview_note: str


class CollapsibleSection(QWidget):
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


def build_theme_tree_items(
    *,
    custom_graph_themes: list[dict[str, object]],
    explicit_theme_id: object,
    theme_id_role: Qt.ItemDataRole,
) -> tuple[list[QTreeWidgetItem], dict[str, QTreeWidgetItem]]:
    theme_items: dict[str, QTreeWidgetItem] = {}
    active_id = resolve_graph_theme_id(explicit_theme_id, custom_themes=custom_graph_themes)
    bold_font = QFont()
    bold_font.setBold(True)
    muted_brush = QBrush(QColor("#8899aa"))

    built_in_root = section_item("Built-in Themes")
    built_in_root.setForeground(0, muted_brush)
    for theme in GRAPH_THEME_REGISTRY.values():
        item = _theme_tree_item(theme.theme_id, theme.label, active_id, bold_font, theme_id_role)
        built_in_root.addChild(item)
        theme_items[theme.theme_id] = item
    built_in_root.setExpanded(True)

    custom_root = section_item("Custom Themes")
    custom_root.setForeground(0, muted_brush)
    for theme in custom_graph_themes:
        theme_id = str(theme.get("theme_id", "")).strip()
        label = str(theme.get("label", theme_id)).strip() or theme_id
        item = _theme_tree_item(theme_id, label, active_id, bold_font, theme_id_role)
        custom_root.addChild(item)
        theme_items[theme_id] = item
    custom_root.setExpanded(True)
    return [built_in_root, custom_root], theme_items


def resolve_preview_metadata(
    *,
    preview_theme_id: object,
    explicit_theme_id: object,
    custom_graph_themes: list[dict[str, object]],
    follow_shell_theme: bool,
) -> GraphThemePreviewMetadata:
    theme = resolve_graph_theme(preview_theme_id, custom_themes=custom_graph_themes)
    is_custom = is_custom_graph_theme_id(theme.theme_id)
    is_active_explicit = is_active_explicit_custom_theme(
        theme_id=theme.theme_id,
        explicit_theme_id=explicit_theme_id,
        custom_graph_themes=custom_graph_themes,
        follow_shell_theme=follow_shell_theme,
    )
    if is_active_explicit:
        status_text = "Custom theme (editable, active explicit theme)"
    elif is_custom:
        status_text = "Custom theme (editable)"
    else:
        status_text = "Built-in theme (read-only)"
    preview_note = (
        "Duplicate a built-in theme to create an editable copy."
        if not is_custom
        else "Editing tokens applies live when this is the active theme."
    )
    return GraphThemePreviewMetadata(
        theme=theme,
        is_custom=is_custom,
        is_active_explicit=is_active_explicit,
        status_text=status_text,
        preview_note=preview_note,
    )


def custom_theme_index(custom_themes: list[dict[str, object]], theme_id: object) -> int:
    normalized_theme_id = str(theme_id).strip().lower()
    for index, theme in enumerate(custom_themes):
        if str(theme.get("theme_id", "")).strip().lower() == normalized_theme_id:
            return index
    return -1


def is_active_explicit_custom_theme(
    *,
    theme_id: object,
    explicit_theme_id: object,
    custom_graph_themes: list[dict[str, object]],
    follow_shell_theme: bool,
) -> bool:
    if follow_shell_theme:
        return False
    resolved_theme_id = resolve_graph_theme_id(theme_id, custom_themes=custom_graph_themes)
    resolved_explicit_theme_id = resolve_graph_theme_id(explicit_theme_id, custom_themes=custom_graph_themes)
    return is_custom_graph_theme_id(resolved_theme_id) and resolved_theme_id == resolved_explicit_theme_id


def section_item(label: str) -> QTreeWidgetItem:
    item = QTreeWidgetItem([label])
    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
    return item


def token_label(token_name: str) -> str:
    parts = str(token_name).split("_")
    expanded = [_TOKEN_LABEL_EXPANSIONS.get(part, part) for part in parts]
    return " ".join(expanded).title()


def h_separator() -> QFrame:
    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setFrameShadow(QFrame.Shadow.Plain)
    separator.setFixedHeight(1)
    separator.setStyleSheet("color: rgba(128, 128, 128, 0.3);")
    return separator


def _theme_tree_item(
    theme_id: str,
    label: str,
    active_id: str,
    bold_font: QFont,
    theme_id_role: Qt.ItemDataRole,
) -> QTreeWidgetItem:
    item_label = f"{label} (active)" if theme_id == active_id else label
    item = QTreeWidgetItem([item_label])
    item.setData(0, theme_id_role, theme_id)
    if theme_id == active_id:
        item.setFont(0, bold_font)
    return item


__all__ = [
    "CollapsibleSection",
    "GraphThemePreviewMetadata",
    "build_theme_tree_items",
    "custom_theme_index",
    "h_separator",
    "is_active_explicit_custom_theme",
    "resolve_preview_metadata",
    "section_item",
    "token_label",
]
