# Purpose: Register Mechanical semantic contracts without loading Ansys runtimes.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_contracts.py

from __future__ import annotations

from importlib.metadata import distributions

from ea_node_editor.addons.mechanical.contracts import (
    MECHANICAL_CONTRACT_MANIFEST,
    MECHANICAL_DATA_TYPE_FAMILY,
    MECHANICAL_DATA_TYPES,
)
from ea_node_editor.nodes.plugin_contracts import (
    AddOnManifest,
    PluginAvailability,
    PluginBackendDescriptor,
)
from ea_node_editor.addons.mechanical.property_edit import (
    create_mechanical_property_edit_adapters,
)

MECHANICAL_ADDON_ID = "mechanical.corex"
_DEPENDENCIES = ("ansys-mechanical-core", "ansys-workbench-core")

MECHANICAL_ADDON_MANIFEST = AddOnManifest(
    addon_id=MECHANICAL_ADDON_ID,
    display_name="Mechanical",
    apply_policy="hot_apply",
    vendor="COREX",
    version="1.0.0",
    summary="Use typed Mechanical models, objects, properties, views, and tables.",
    details="Provides data-only contracts now; runtime nodes are registered by later catalogue tasks.",
    dependencies=_DEPENDENCIES,
    data_type_families=(MECHANICAL_DATA_TYPE_FAMILY,),
    data_types=MECHANICAL_DATA_TYPES,
)


def get_mechanical_addon_availability() -> PluginAvailability:
    installed = {
        str(distribution.metadata.get("Name", "")).casefold().replace("_", "-")
        for distribution in distributions()
    }
    missing = tuple(
        distribution
        for distribution in _DEPENDENCIES
        if distribution.casefold() not in installed
    )
    if missing:
        return PluginAvailability.missing_dependency(
            *missing,
            summary="Mechanical Python packages are unavailable; no Ansys process was started.",
        )
    return PluginAvailability.available(
        summary="Mechanical Python packages are available; installations are checked when a model opens."
    )


MECHANICAL_PLUGIN_BACKEND = PluginBackendDescriptor(
    plugin_id=MECHANICAL_ADDON_ID,
    display_name=MECHANICAL_ADDON_MANIFEST.display_name,
    get_availability=get_mechanical_addon_availability,
    load_descriptors=lambda: (),
    addon_manifest=MECHANICAL_ADDON_MANIFEST,
    data_type_families=MECHANICAL_CONTRACT_MANIFEST.data_type_families,
    data_types=MECHANICAL_CONTRACT_MANIFEST.data_types,
)
PLUGIN_BACKENDS = (MECHANICAL_PLUGIN_BACKEND,)

__all__ = [
    "MECHANICAL_ADDON_ID",
    "MECHANICAL_ADDON_MANIFEST",
    "MECHANICAL_PLUGIN_BACKEND",
    "PLUGIN_BACKENDS",
    "get_mechanical_addon_availability",
    "create_mechanical_property_edit_adapters",
]
