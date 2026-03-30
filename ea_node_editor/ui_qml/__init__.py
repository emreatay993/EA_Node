from __future__ import annotations

import os
import sys


def _configure_qquick_controls_runtime() -> None:
    if sys.platform != "win32":
        return
    if os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        return
    # PyQt6 6.11 on Windows can miss the Windows Quick Controls style runtime DLL.
    # Pin a built-in style for all QML bridge imports unless the caller explicitly overrides it.
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"


_configure_qquick_controls_runtime()

from ea_node_editor.ui_qml.console_model import ConsoleModel
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.script_editor_model import ScriptEditorModel
from ea_node_editor.ui_qml.status_model import StatusItemModel
from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
from ea_node_editor.ui_qml.workspace_tabs_model import WorkspaceTabsModel

__all__ = [
    "ConsoleModel",
    "GraphThemeBridge",
    "GraphSceneBridge",
    "ViewportBridge",
    "ScriptEditorModel",
    "StatusItemModel",
    "ThemeBridge",
    "WorkspaceTabsModel",
]
