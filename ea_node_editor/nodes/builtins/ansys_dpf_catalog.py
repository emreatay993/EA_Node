from __future__ import annotations

import importlib.util
from collections.abc import Callable

from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    ansys_dpf_plugin_state,
    set_ansys_dpf_plugin_state,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import normalize_dpf_descriptor_spec
from ea_node_editor.nodes.plugin_contracts import (
    NodePlugin,
    PluginAvailability,
    PluginBackendDescriptor,
    PluginDescriptor,
)

ANSYS_DPF_DEPENDENCY = "ansys.dpf.core"
_CACHED_DESCRIPTOR_VERSION: str | None = None
_CACHED_PLUGIN_DESCRIPTORS: tuple[PluginDescriptor, ...] | None = None


def _find_spec(module_name: str):
    try:
        return importlib.util.find_spec(module_name)
    except (ImportError, ModuleNotFoundError, ValueError):
        return None


def get_ansys_dpf_plugin_availability() -> PluginAvailability:
    if _find_spec(ANSYS_DPF_DEPENDENCY) is None:
        return PluginAvailability.missing_dependency(
            ANSYS_DPF_DEPENDENCY,
            summary="ansys.dpf.core is not installed; the DPF node family remains unavailable.",
        )
    return PluginAvailability.available(
        summary="ansys.dpf.core is installed; the DPF node family can be registered.",
    )


def resolve_ansys_dpf_plugin_version() -> str:
    if _find_spec(ANSYS_DPF_DEPENDENCY) is None:
        return ""
    try:
        import ansys.dpf.core as dpf
    except (ImportError, ModuleNotFoundError, ValueError):
        return ""
    return str(getattr(dpf, "__version__", ""))


def _load_ansys_dpf_node_plugin_factories() -> tuple[Callable[[], NodePlugin], ...]:
    from ea_node_editor.nodes.builtins.ansys_dpf_compute import (
        DpfExportNodePlugin,
        DpfFieldOpsNodePlugin,
        DpfMeshExtractNodePlugin,
        DpfMeshScopingNodePlugin,
        DpfModelNodePlugin,
        DpfResultFieldNodePlugin,
        DpfResultFileNodePlugin,
        DpfTimeScopingNodePlugin,
    )
    from ea_node_editor.nodes.builtins.ansys_dpf_viewer import DpfViewerNodePlugin

    return (
        DpfResultFileNodePlugin,
        DpfModelNodePlugin,
        DpfMeshScopingNodePlugin,
        DpfTimeScopingNodePlugin,
        DpfResultFieldNodePlugin,
        DpfFieldOpsNodePlugin,
        DpfMeshExtractNodePlugin,
        DpfExportNodePlugin,
        DpfViewerNodePlugin,
    )


def _build_ansys_dpf_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    return tuple(
        PluginDescriptor(spec=normalize_dpf_descriptor_spec(factory().spec()), factory=factory)
        for factory in _load_ansys_dpf_node_plugin_factories()
    )


def invalidate_ansys_dpf_descriptor_cache() -> None:
    global _CACHED_DESCRIPTOR_VERSION, _CACHED_PLUGIN_DESCRIPTORS
    _CACHED_DESCRIPTOR_VERSION = None
    _CACHED_PLUGIN_DESCRIPTORS = None


def load_ansys_dpf_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    global _CACHED_DESCRIPTOR_VERSION, _CACHED_PLUGIN_DESCRIPTORS
    version = resolve_ansys_dpf_plugin_version()
    if _CACHED_PLUGIN_DESCRIPTORS is not None and _CACHED_DESCRIPTOR_VERSION == version:
        return _CACHED_PLUGIN_DESCRIPTORS

    descriptors = _build_ansys_dpf_plugin_descriptors()
    _CACHED_PLUGIN_DESCRIPTORS = descriptors
    _CACHED_DESCRIPTOR_VERSION = version
    return descriptors


def sync_ansys_dpf_plugin_state(
    *,
    store: AppPreferencesStore | None = None,
) -> dict[str, object]:
    preferences_store = store or AppPreferencesStore()
    document = preferences_store.load_document()
    if not get_ansys_dpf_plugin_availability().is_available:
        return document

    version = resolve_ansys_dpf_plugin_version()
    persisted_state = ansys_dpf_plugin_state(document)
    current_version = persisted_state["version"]
    cached_version = persisted_state["catalog_cache_version"]
    if cached_version != version:
        invalidate_ansys_dpf_descriptor_cache()
        load_ansys_dpf_plugin_descriptors()

    updated_document = set_ansys_dpf_plugin_state(
        document,
        version=version,
        catalog_cache_version=version,
    )
    if current_version != version or cached_version != version:
        return preferences_store.persist_document(updated_document)
    return updated_document


ANSYS_DPF_PLUGIN_BACKEND = PluginBackendDescriptor(
    plugin_id="ea_node_editor.builtins.ansys_dpf",
    display_name="ANSYS DPF",
    get_availability=get_ansys_dpf_plugin_availability,
    load_descriptors=load_ansys_dpf_plugin_descriptors,
)
PLUGIN_BACKENDS = (ANSYS_DPF_PLUGIN_BACKEND,)


def _descriptors_or_empty() -> tuple[PluginDescriptor, ...]:
    if not get_ansys_dpf_plugin_availability().is_available:
        return ()
    return load_ansys_dpf_plugin_descriptors()


def __getattr__(name: str):
    if name in {"ANSYS_DPF_PLUGIN_DESCRIPTORS", "PLUGIN_DESCRIPTORS"}:
        return _descriptors_or_empty()
    if name == "ANSYS_DPF_NODE_PLUGINS":
        return tuple(descriptor.factory for descriptor in _descriptors_or_empty())
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
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
