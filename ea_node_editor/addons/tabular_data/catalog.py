from __future__ import annotations

import importlib.util

from ea_node_editor.addons.tabular_data.metadata import (
    TABULAR_DATA_ADDON_ID,
    TABULAR_DATA_ADDON_MANIFEST,
    TABULAR_DATA_DEPENDENCIES,
    TABULAR_DATA_TOOLCHAINS,
)
from ea_node_editor.nodes.plugin_contracts import (
    PluginAvailability,
    PluginBackendDescriptor,
    PluginDescriptor,
)


def _find_spec(module_name: str):
    try:
        return importlib.util.find_spec(module_name)
    except (ImportError, ModuleNotFoundError, ValueError):
        return None


def missing_tabular_data_dependencies() -> tuple[str, ...]:
    return tuple(
        dependency
        for dependency in TABULAR_DATA_DEPENDENCIES
        if _find_spec(dependency) is None
    )


def get_tabular_data_addon_availability() -> PluginAvailability:
    missing = missing_tabular_data_dependencies()
    if missing:
        return PluginAvailability.missing_dependency(
            *missing,
            summary=(
                "The optional Tabular Data add-on requires the tabular dependency extra; "
                "missing modules: " + ", ".join(missing) + "."
            ),
        )
    return PluginAvailability.available(
        summary="The optional tabular dependency stack is installed; Tabular Data can be registered."
    )


def load_tabular_data_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    from ea_node_editor.addons.tabular_data.extraction_nodes import TABULAR_EXTRACTION_NODE_DESCRIPTORS
    from ea_node_editor.addons.tabular_data.input_node import TABULAR_DATA_INPUT_NODE_DESCRIPTORS

    return TABULAR_DATA_INPUT_NODE_DESCRIPTORS + TABULAR_EXTRACTION_NODE_DESCRIPTORS


def create_tabular_property_edit_adapters() -> tuple[object, ...]:
    from ea_node_editor.addons.tabular_data.property_edit_adapter import (
        create_tabular_property_edit_adapters as create_adapters,
    )

    return create_adapters()


TABULAR_DATA_PLUGIN_BACKEND = PluginBackendDescriptor(
    plugin_id=TABULAR_DATA_ADDON_MANIFEST.addon_id,
    display_name=TABULAR_DATA_ADDON_MANIFEST.display_name,
    get_availability=get_tabular_data_addon_availability,
    load_descriptors=load_tabular_data_plugin_descriptors,
    addon_manifest=TABULAR_DATA_ADDON_MANIFEST,
    toolchains=TABULAR_DATA_TOOLCHAINS,
)
PLUGIN_BACKENDS = (TABULAR_DATA_PLUGIN_BACKEND,)

__all__ = [
    "PLUGIN_BACKENDS",
    "TABULAR_DATA_ADDON_ID",
    "TABULAR_DATA_ADDON_MANIFEST",
    "TABULAR_DATA_DEPENDENCIES",
    "TABULAR_DATA_PLUGIN_BACKEND",
    "TABULAR_DATA_TOOLCHAINS",
    "create_tabular_property_edit_adapters",
    "get_tabular_data_addon_availability",
    "load_tabular_data_plugin_descriptors",
    "missing_tabular_data_dependencies",
]
