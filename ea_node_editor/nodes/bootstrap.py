from __future__ import annotations

from pathlib import Path
from typing import Any

from ea_node_editor.nodes.builtins.core import CORE_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.hpc import HPC_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.integrations import INTEGRATION_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_annotation import PASSIVE_ANNOTATION_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_flowchart import PASSIVE_FLOWCHART_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_media import PASSIVE_MEDIA_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_planning import PASSIVE_PLANNING_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.subnode import SUBNODE_NODE_DESCRIPTORS
from ea_node_editor.nodes.registry import NodeRegistry


BUILTIN_NODE_DESCRIPTORS = (
    *CORE_NODE_DESCRIPTORS[:5],
    *INTEGRATION_NODE_DESCRIPTORS,
    *CORE_NODE_DESCRIPTORS[5:],
    *HPC_NODE_DESCRIPTORS,
    *SUBNODE_NODE_DESCRIPTORS,
    *PASSIVE_FLOWCHART_NODE_DESCRIPTORS,
    *PASSIVE_PLANNING_NODE_DESCRIPTORS,
    *PASSIVE_ANNOTATION_NODE_DESCRIPTORS,
    *PASSIVE_MEDIA_NODE_DESCRIPTORS,
)


def build_default_registry(
    extra_plugin_dirs: list[Path] | None = None,
    *,
    app_preferences_store: Any = None,
    preferences_document: Any = None,
) -> NodeRegistry:
    registry = NodeRegistry()
    registry.register_descriptors(BUILTIN_NODE_DESCRIPTORS)

    from ea_node_editor.addons.catalog import live_addon_backend_collections
    from ea_node_editor.nodes.plugin_loader import discover_and_load_plugins, register_plugin_backends

    for addon_backends in live_addon_backend_collections(
        preferences_document=preferences_document,
        store=app_preferences_store,
    ):
        register_plugin_backends(
            addon_backends.backends,
            registry,
            addon_backends.source,
        )
    discover_and_load_plugins(registry, extra_dirs=extra_plugin_dirs)
    return registry
