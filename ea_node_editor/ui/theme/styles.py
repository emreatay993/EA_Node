from __future__ import annotations

from ea_node_editor.ui.theme.tokens import STITCH_DARK_V1, ThemeTokens


def build_app_stylesheet(tokens: ThemeTokens = STITCH_DARK_V1) -> str:
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
    color: #d0d5de;
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
    border-left: 1px solid {tokens.input_border};
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
    color: #bdc5d3;
}}
QLabel#panelTitle {{
    color: #f0f4fb;
    font-weight: 700;
    letter-spacing: 0.4px;
}}
QWidget#nodeLibraryPanel,
QWidget#inspectorPanel {{
    background: {tokens.panel_bg};
}}
QWidget#workspaceTabStrip {{
    background: #1b1d22;
    border-top: 1px solid {tokens.border};
    border-bottom: 1px solid {tokens.border};
}}
QTabBar::tab {{
    background: #2a2d34;
    color: #d8deea;
    padding: 5px 11px;
    border: 1px solid {tokens.border};
    border-bottom: 0;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: #2f343e;
    color: #f2f4f8;
    border-top: 2px solid {tokens.accent};
}}
QTabBar::tab:hover {{
    background: {tokens.hover};
}}
QTabWidget::pane {{
    border-top: 1px solid {tokens.border};
}}
QWidget#consolePanel {{
    background: #15181d;
    border-top: 1px solid {tokens.border};
}}
QSplitter::handle {{
    background: #272b33;
}}
QSplitter::handle:hover {{
    background: #323742;
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
    background: rgba(255, 255, 255, 0.13);
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
    background: #4d5361;
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar:horizontal {{
    background: {tokens.panel_bg};
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: #4d5361;
    min-width: 20px;
    border-radius: 4px;
}}
"""

