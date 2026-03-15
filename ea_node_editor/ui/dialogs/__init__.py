from __future__ import annotations

from importlib import import_module
from typing import Any

_DIALOG_MODULES = {
    "FlowEdgeStyleDialog": "ea_node_editor.ui.dialogs.flow_edge_style_dialog",
    "GraphThemeEditorDialog": "ea_node_editor.ui.dialogs.graph_theme_editor_dialog",
    "GraphicsSettingsDialog": "ea_node_editor.ui.dialogs.graphics_settings_dialog",
    "PassiveNodeStyleDialog": "ea_node_editor.ui.dialogs.passive_node_style_dialog",
    "SectionedSettingsDialog": "ea_node_editor.ui.dialogs.sectioned_settings_dialog",
    "WorkflowSettingsDialog": "ea_node_editor.ui.dialogs.workflow_settings_dialog",
}

__all__ = list(_DIALOG_MODULES)


def __getattr__(name: str) -> Any:
    module_path = _DIALOG_MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_path)
    return getattr(module, name)
