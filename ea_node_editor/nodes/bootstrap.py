from __future__ import annotations

import importlib
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


def _addon_backend_module_for_nodes(registration: Any) -> Any:
    module_name = str(registration.backend_module).strip()
    if module_name == "ea_node_editor.addons.ansys_dpf.catalog":
        module_name = "ea_node_editor.nodes.builtins.ansys_dpf_catalog"
    return importlib.import_module(module_name)


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

    from ea_node_editor.nodes.plugin_loader import discover_and_load_plugins, register_plugin_backends
    from ea_node_editor.addons.catalog import live_addon_registrations

    for registration in live_addon_registrations(
        preferences_document=preferences_document,
        store=app_preferences_store,
    ):
        module = _addon_backend_module_for_nodes(registration)
        sync_state_attr = str(registration.sync_state_attr or "").strip()
        if app_preferences_store is not None and sync_state_attr:
            sync_state = getattr(module, sync_state_attr, None)
            if callable(sync_state):
                sync_state(store=app_preferences_store)
        backends = getattr(module, registration.backend_collection_attr, ())
        register_plugin_backends(
            backends,
            registry,
            str(registration.backend_module).strip(),
        )
    discover_and_load_plugins(registry, extra_dirs=extra_plugin_dirs)
    return registry
