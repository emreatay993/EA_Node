from __future__ import annotations

import pathlib

from ea_node_editor.ui.theme.registry import DEFAULT_THEME_ID, resolve_theme_tokens
from ea_node_editor.ui.theme.tokens import ThemeTokens

_ICONS_DIR = pathlib.Path(__file__).resolve().parent / "icons"


def _icon_path(name: str) -> str:
    """Return a forward-slash absolute path suitable for Qt stylesheet url()."""
    return str(_ICONS_DIR / name).replace("\\", "/")


def build_app_stylesheet(tokens: ThemeTokens) -> str:
    # Resolve icon file paths based on the theme's icon variant
    check_icon = _icon_path(f"check-{tokens.icon_variant}.svg")
    chevron_icon = _icon_path(f"chevron-down-{tokens.icon_variant}.svg")

    return f"""
QMainWindow {{
    background: {tokens.app_bg};
    color: {tokens.app_fg};
}}
QWidget {{
    background: {tokens.app_bg};
    color: {tokens.app_fg};
    font-family: 'Segoe UI';
    font-size: 12px;
}}
QMenuBar {{
    background: {tokens.toolbar_bg};
    color: {tokens.app_fg};
    border-bottom: 1px solid {tokens.border};
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 11px;
}}
QMenuBar::item:selected {{
    background: {tokens.hover};
}}
QMenu {{
    background: {tokens.panel_alt_bg};
    color: {tokens.app_fg};
    border: 1px solid {tokens.border};
}}
QMenu::item {{
    padding: 5px 18px;
}}
QMenu::item:selected {{
    background: {tokens.accent_strong};
}}
QToolBar#mainToolbar {{
    background: {tokens.toolbar_bg};
    border-bottom: 1px solid {tokens.border};
    spacing: 5px;
    padding: 3px 6px;
}}
QToolButton {{
    background: {tokens.panel_alt_bg};
    border: 1px solid {tokens.border};
    border-radius: 3px;
    padding: 4px 9px;
    color: {tokens.app_fg};
}}
QToolButton:hover {{
    background: {tokens.hover};
}}
QToolButton:pressed {{
    background: {tokens.pressed};
}}
QPushButton {{
    background: {tokens.panel_alt_bg};
    border: 1px solid {tokens.border};
    border-radius: 3px;
    padding: 4px 8px;
    color: {tokens.app_fg};
}}
QPushButton:hover {{
    background: {tokens.hover};
}}
QPushButton:pressed {{
    background: {tokens.pressed};
}}
QPushButton#workspaceAddButton {{
    padding: 0;
    font-weight: 600;
}}
QPushButton#viewButton {{
    padding: 4px 10px;
}}
QLabel#zoomLabel {{
    color: {tokens.muted_fg};
    padding-left: 4px;
}}
QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox,
QPlainTextEdit,
QListWidget,
QTreeWidget {{
    background: {tokens.input_bg};
    border: 1px solid {tokens.input_border};
    color: {tokens.input_fg};
    padding: 3px;
    selection-background-color: {tokens.accent_strong};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 24px;
    border-left: 1px solid {tokens.input_border};
    background: transparent;
}}
QComboBox::down-arrow {{
    image: url({chevron_icon});
    width: 12px;
    height: 12px;
}}
QCheckBox {{
    spacing: 8px;
    padding: 3px 0;
    background: transparent;
}}
QRadioButton {{
    spacing: 8px;
    padding: 3px 0;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {tokens.input_border};
    border-radius: 4px;
    background: {tokens.input_bg};
}}
QCheckBox::indicator:hover {{
    border-color: {tokens.accent};
    background: {tokens.hover};
}}
QCheckBox::indicator:checked {{
    background: {tokens.accent_strong};
    border-color: {tokens.accent_strong};
    image: url({check_icon});
}}
QCheckBox::indicator:checked:hover {{
    background: {tokens.accent};
    border-color: {tokens.accent};
    image: url({check_icon});
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {tokens.input_border};
    border-radius: 8px;
    background: {tokens.input_bg};
}}
QRadioButton::indicator:hover {{
    border-color: {tokens.accent};
    background: {tokens.hover};
}}
QRadioButton::indicator:checked {{
    border: 5px solid {tokens.accent_strong};
    border-radius: 8px;
    background: {tokens.input_bg};
}}
QRadioButton::indicator:checked:hover {{
    border-color: {tokens.accent};
    background: {tokens.input_bg};
}}
QSlider {{
    background: transparent;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {tokens.input_border};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {tokens.accent};
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {tokens.accent_strong};
}}
QSlider::sub-page:horizontal {{
    background: {tokens.accent_strong};
    border-radius: 2px;
}}
QLabel {{
    background: transparent;
    border: none;
}}
QWidget[settingsCard="true"] {{
    background: {tokens.panel_alt_bg};
    border: 1px solid {tokens.border};
    border-radius: 8px;
}}
QWidget[performanceModeOption="true"] {{
    background: {tokens.input_bg};
    border: 1px solid {tokens.input_border};
    border-radius: 6px;
}}
QWidget[performanceModeOption="true"]:hover {{
    background: {tokens.hover};
    border-color: {tokens.accent};
}}
QWidget[performanceModeOption="true"][performanceModeSelected="true"] {{
    background: {tokens.panel_alt_bg};
    border-color: {tokens.accent_strong};
}}
QLabel[settingsSectionTitle="true"] {{
    font-weight: 600;
    font-size: 11px;
    color: {tokens.muted_fg};
    padding: 0 0 2px 2px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background: transparent;
    border: none;
}}
QGroupBox {{
    border: 1px solid {tokens.border};
    margin-top: 8px;
    padding-top: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 2px;
    color: {tokens.group_title_fg};
}}
QLabel#panelTitle {{
    color: {tokens.panel_title_fg};
    font-weight: 700;
    letter-spacing: 0.4px;
}}
QWidget#nodeLibraryPanel,
QWidget#inspectorPanel {{
    background: {tokens.panel_bg};
}}
QWidget#workspaceTabStrip {{
    background: {tokens.panel_bg};
    border-top: 1px solid {tokens.border};
    border-bottom: 1px solid {tokens.border};
}}
QTabBar::tab {{
    background: {tokens.tab_bg};
    color: {tokens.tab_fg};
    padding: 5px 11px;
    border: 1px solid {tokens.border};
    border-bottom: 0;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {tokens.tab_selected_bg};
    color: {tokens.tab_selected_fg};
    border-top: 2px solid {tokens.accent};
}}
QTabBar::tab:hover {{
    background: {tokens.hover};
}}
QTabWidget::pane {{
    border-top: 1px solid {tokens.border};
}}
QWidget#consolePanel {{
    background: {tokens.console_bg};
    border-top: 1px solid {tokens.border};
}}
QSplitter::handle {{
    background: {tokens.splitter_handle};
}}
QSplitter::handle:hover {{
    background: {tokens.splitter_handle_hover};
}}
QStatusBar#mainStatusBar {{
    background: {tokens.status_bg};
    color: {tokens.status_fg};
    min-height: 26px;
    border-top: 1px solid {tokens.status_border};
}}
QStatusBar#mainStatusBar QLabel {{
    color: {tokens.status_fg};
}}
QStatusBar#mainStatusBar > QWidget {{
    color: {tokens.status_fg};
}}
QStatusBar#mainStatusBar > QWidget[clickable="true"]:hover {{
    background: {tokens.status_hover_bg};
    border-radius: 3px;
}}
QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}
QDockWidget::title {{
    background: {tokens.toolbar_bg};
    text-align: left;
    padding-left: 8px;
    border-bottom: 1px solid {tokens.border};
}}
QScrollBar:vertical {{
    background: {tokens.panel_bg};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {tokens.scrollbar_handle};
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar:horizontal {{
    background: {tokens.panel_bg};
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {tokens.scrollbar_handle};
    min-width: 20px;
    border-radius: 4px;
}}
"""


def build_theme_stylesheet(theme_id: object = DEFAULT_THEME_ID) -> str:
    return build_app_stylesheet(resolve_theme_tokens(theme_id))
