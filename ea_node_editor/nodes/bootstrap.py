from __future__ import annotations

from pathlib import Path

from ea_node_editor.nodes.builtins.core import (
    BranchNodePlugin,
    ConstantNodePlugin,
    EndNodePlugin,
    LoggerNodePlugin,
    OnFailureNodePlugin,
    PythonScriptNodePlugin,
    StartNodePlugin,
)
from ea_node_editor.nodes.builtins.hpc import (
    HPCFetchResultNodePlugin,
    HPCMonitorNodePlugin,
    HPCOnStatusNodePlugin,
    HPCSubmitNodePlugin,
)
from ea_node_editor.nodes.builtins.subnode import (
    SubnodeInputNodePlugin,
    SubnodeNodePlugin,
    SubnodeOutputNodePlugin,
)
from ea_node_editor.nodes.builtins.integrations_email import EmailSendNodePlugin
from ea_node_editor.nodes.builtins.integrations_file_io import FileReadNodePlugin, FileWriteNodePlugin
from ea_node_editor.nodes.builtins.integrations_process import ProcessRunNodePlugin
from ea_node_editor.nodes.builtins.integrations_spreadsheet import (
    ExcelReadNodePlugin,
    ExcelWriteNodePlugin,
)
from ea_node_editor.nodes.registry import NodeRegistry


def build_default_registry(extra_plugin_dirs: list[Path] | None = None) -> NodeRegistry:
    registry = NodeRegistry()
    registry.register(StartNodePlugin)
    registry.register(EndNodePlugin)
    registry.register(ConstantNodePlugin)
    registry.register(LoggerNodePlugin)
    registry.register(PythonScriptNodePlugin)
    registry.register(ExcelReadNodePlugin)
    registry.register(ExcelWriteNodePlugin)
    registry.register(FileReadNodePlugin)
    registry.register(FileWriteNodePlugin)
    registry.register(EmailSendNodePlugin)
    registry.register(ProcessRunNodePlugin)
    registry.register(OnFailureNodePlugin)
    registry.register(BranchNodePlugin)
    registry.register(HPCSubmitNodePlugin)
    registry.register(HPCMonitorNodePlugin)
    registry.register(HPCOnStatusNodePlugin)
    registry.register(HPCFetchResultNodePlugin)
    registry.register(SubnodeNodePlugin)
    registry.register(SubnodeInputNodePlugin)
    registry.register(SubnodeOutputNodePlugin)

    from ea_node_editor.nodes.plugin_loader import discover_and_load_plugins

    discover_and_load_plugins(registry, extra_dirs=extra_plugin_dirs)
    return registry
