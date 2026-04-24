from __future__ import annotations

import importlib.util

from ea_node_editor.addons.ansys_dpf.helper_catalog import (
    load_ansys_dpf_helper_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.metadata import (
    ANSYS_DPF_ADDON_ID,
    ANSYS_DPF_ADDON_MANIFEST,
    ANSYS_DPF_DEPENDENCY,
)
from ea_node_editor.addons.ansys_dpf.operator_catalog import (
    load_ansys_dpf_operator_plugin_descriptors,
)
from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    ansys_dpf_plugin_state,
    set_ansys_dpf_plugin_state,
)
from ea_node_editor.nodes.plugin_contracts import (
    PluginAvailability,
    PluginBackendDescriptor,
    PluginDescriptor,
)

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


def _build_ansys_dpf_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    return (
        load_ansys_dpf_helper_plugin_descriptors()
        + load_ansys_dpf_operator_plugin_descriptors()
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
    plugin_id=ANSYS_DPF_ADDON_MANIFEST.addon_id,
    display_name=ANSYS_DPF_ADDON_MANIFEST.display_name,
    get_availability=get_ansys_dpf_plugin_availability,
    load_descriptors=load_ansys_dpf_plugin_descriptors,
    addon_manifest=ANSYS_DPF_ADDON_MANIFEST,
)
PLUGIN_BACKENDS = (ANSYS_DPF_PLUGIN_BACKEND,)


def create_ansys_dpf_execution_viewer_backend(worker_services):
    from ea_node_editor.execution.viewer_backend_dpf import DpfExecutionViewerBackend

    return DpfExecutionViewerBackend(worker_services)


def create_ansys_dpf_viewer_widget_binder():
    from ea_node_editor.ui_qml.dpf_viewer_widget_binder import DpfViewerWidgetBinder

    return DpfViewerWidgetBinder()


__all__ = [
    "ANSYS_DPF_ADDON_ID",
    "ANSYS_DPF_ADDON_MANIFEST",
    "ANSYS_DPF_DEPENDENCY",
    "ANSYS_DPF_PLUGIN_BACKEND",
    "PLUGIN_BACKENDS",
    "create_ansys_dpf_execution_viewer_backend",
    "create_ansys_dpf_viewer_widget_binder",
    "get_ansys_dpf_plugin_availability",
    "invalidate_ansys_dpf_descriptor_cache",
    "load_ansys_dpf_plugin_descriptors",
    "resolve_ansys_dpf_plugin_version",
    "sync_ansys_dpf_plugin_state",
]
