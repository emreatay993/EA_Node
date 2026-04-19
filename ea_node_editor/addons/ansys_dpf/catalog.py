from __future__ import annotations

from ea_node_editor.addons.ansys_dpf.metadata import (
    ANSYS_DPF_ADDON_ID,
    ANSYS_DPF_ADDON_MANIFEST,
    ANSYS_DPF_DEPENDENCY,
)
from ea_node_editor.nodes.builtins import ansys_dpf_catalog as _compat_catalog
from ea_node_editor.nodes.builtins.ansys_dpf_catalog import (
    ANSYS_DPF_PLUGIN_BACKEND,
    PLUGIN_BACKENDS,
    get_ansys_dpf_plugin_availability,
    invalidate_ansys_dpf_descriptor_cache,
    load_ansys_dpf_plugin_descriptors,
    resolve_ansys_dpf_plugin_version,
    sync_ansys_dpf_plugin_state,
)


def __getattr__(name: str):
    if name in {
        "ANSYS_DPF_NODE_PLUGINS",
        "ANSYS_DPF_PLUGIN_DESCRIPTORS",
        "PLUGIN_DESCRIPTORS",
    }:
        return getattr(_compat_catalog, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ANSYS_DPF_ADDON_ID",
    "ANSYS_DPF_ADDON_MANIFEST",
    "ANSYS_DPF_DEPENDENCY",
    "ANSYS_DPF_NODE_PLUGINS",
    "ANSYS_DPF_PLUGIN_BACKEND",
    "ANSYS_DPF_PLUGIN_DESCRIPTORS",
    "PLUGIN_BACKENDS",
    "PLUGIN_DESCRIPTORS",
    "get_ansys_dpf_plugin_availability",
    "invalidate_ansys_dpf_descriptor_cache",
    "load_ansys_dpf_plugin_descriptors",
    "resolve_ansys_dpf_plugin_version",
    "sync_ansys_dpf_plugin_state",
]
