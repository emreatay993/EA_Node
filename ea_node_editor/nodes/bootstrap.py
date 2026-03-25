from __future__ import annotations

from pathlib import Path

from ea_node_editor.nodes.builtins.ansys_dpf import ANSYS_DPF_NODE_PLUGINS
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
from ea_node_editor.nodes.builtins.passive_annotation import PASSIVE_ANNOTATION_NODE_PLUGINS
from ea_node_editor.nodes.builtins.passive_flowchart import PASSIVE_FLOWCHART_NODE_PLUGINS
from ea_node_editor.nodes.builtins.passive_media import PASSIVE_MEDIA_NODE_PLUGINS
from ea_node_editor.nodes.builtins.passive_planning import PASSIVE_PLANNING_NODE_PLUGINS
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
    for plugin in ANSYS_DPF_NODE_PLUGINS:
        registry.register(plugin)
    for plugin in PASSIVE_FLOWCHART_NODE_PLUGINS:
        registry.register(plugin)
    for plugin in PASSIVE_PLANNING_NODE_PLUGINS:
        registry.register(plugin)
    for plugin in PASSIVE_ANNOTATION_NODE_PLUGINS:
        registry.register(plugin)
    for plugin in PASSIVE_MEDIA_NODE_PLUGINS:
        registry.register(plugin)

    from ea_node_editor.nodes.plugin_loader import discover_and_load_plugins

    discover_and_load_plugins(registry, extra_dirs=extra_plugin_dirs)
    return registry
