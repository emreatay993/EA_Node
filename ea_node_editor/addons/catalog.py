from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    addon_state,
    default_app_preferences_document,
    normalize_app_preferences_document,
)
from ea_node_editor.nodes.plugin_contracts import AddOnManifest

ANSYS_DPF_ADDON_ID = "ea_node_editor.builtins.ansys_dpf"


@dataclass(slots=True, frozen=True)
class AddOnRegistration:
    manifest: AddOnManifest
    backend_module: str
    backend_id: str
    backend_collection_attr: str = "PLUGIN_BACKENDS"
    version_resolver_attr: str = ""
    sync_state_attr: str = ""
    cache_invalidator_attr: str = ""
    viewer_backend_factory_attr: str = ""
    viewer_widget_binder_factory_attr: str = ""


REGISTERED_ADDON_REGISTRATIONS = (
    AddOnRegistration(
        manifest=AddOnManifest(
            addon_id=ANSYS_DPF_ADDON_ID,
            display_name="ANSYS DPF",
            apply_policy="hot_apply",
            vendor="Ansys",
            summary="Enable ANSYS DPF helper, operator, and viewer nodes when ansys.dpf.core is installed.",
            details=(
                "Provides the ANSYS DPF node family used for local result-file inspection, "
                "operator execution, and viewer workflows."
            ),
            dependencies=("ansys.dpf.core",),
        ),
        backend_module="ea_node_editor.addons.ansys_dpf.catalog",
        backend_id=ANSYS_DPF_ADDON_ID,
        version_resolver_attr="resolve_ansys_dpf_plugin_version",
        sync_state_attr="sync_ansys_dpf_plugin_state",
        cache_invalidator_attr="invalidate_ansys_dpf_descriptor_cache",
        viewer_backend_factory_attr="create_ansys_dpf_execution_viewer_backend",
        viewer_widget_binder_factory_attr="create_ansys_dpf_viewer_widget_binder",
    ),
)


def registered_addon_registrations() -> tuple[AddOnRegistration, ...]:
    return REGISTERED_ADDON_REGISTRATIONS


def registered_addon_registration_by_id(addon_id: str) -> AddOnRegistration | None:
    normalized_addon_id = str(addon_id).strip()
    if not normalized_addon_id:
        return None
    for registration in REGISTERED_ADDON_REGISTRATIONS:
        if registration.manifest.addon_id == normalized_addon_id:
            return registration
    return None


def _resolved_preferences_document(
    *,
    preferences_document: Any = None,
    store: AppPreferencesStore | None = None,
) -> dict[str, Any]:
    if preferences_document is not None:
        return normalize_app_preferences_document(preferences_document)
    if store is not None:
        return normalize_app_preferences_document(store.load_document())
    return default_app_preferences_document()


def addon_registration_is_live_enabled(
    registration: AddOnRegistration,
    *,
    preferences_document: Any = None,
    store: AppPreferencesStore | None = None,
) -> bool:
    if registration.manifest.apply_policy != "hot_apply":
        return True
    normalized_preferences = _resolved_preferences_document(
        preferences_document=preferences_document,
        store=store,
    )
    state = addon_state(normalized_preferences, registration.manifest.addon_id)
    return bool(state["enabled"])


def live_addon_registrations(
    *,
    preferences_document: Any = None,
    store: AppPreferencesStore | None = None,
) -> tuple[AddOnRegistration, ...]:
    normalized_preferences = _resolved_preferences_document(
        preferences_document=preferences_document,
        store=store,
    )
    return tuple(
        registration
        for registration in REGISTERED_ADDON_REGISTRATIONS
        if addon_registration_is_live_enabled(
            registration,
            preferences_document=normalized_preferences,
        )
    )


def import_addon_backend_module(registration: AddOnRegistration) -> Any:
    module_name = str(registration.backend_module).strip()
    if not module_name:
        raise ValueError(f"Add-on {registration.manifest.addon_id!r} is missing backend_module")
    return importlib.import_module(module_name)


def sync_live_addon_state(
    *,
    store: AppPreferencesStore | None = None,
    preferences_document: Any = None,
) -> None:
    if store is None:
        return
    for registration in live_addon_registrations(
        preferences_document=preferences_document,
        store=store,
    ):
        sync_state_attr = str(registration.sync_state_attr or "").strip()
        if not sync_state_attr:
            continue
        sync_state = getattr(import_addon_backend_module(registration), sync_state_attr, None)
        if callable(sync_state):
            sync_state(store=store)


def invalidate_addon_runtime_caches(addon_id: str) -> bool:
    registration = registered_addon_registration_by_id(addon_id)
    if registration is None:
        return False
    invalidator_attr = str(registration.cache_invalidator_attr or "").strip()
    if not invalidator_attr:
        return False
    invalidator = getattr(import_addon_backend_module(registration), invalidator_attr, None)
    if not callable(invalidator):
        return False
    invalidator()
    return True


def create_live_execution_viewer_backends(
    worker_services: Any,
    *,
    preferences_document: Any = None,
    store: AppPreferencesStore | None = None,
) -> tuple[Any, ...]:
    backends: list[Any] = []
    for registration in live_addon_registrations(
        preferences_document=preferences_document,
        store=store,
    ):
        factory_attr = str(registration.viewer_backend_factory_attr or "").strip()
        if not factory_attr:
            continue
        factory = getattr(import_addon_backend_module(registration), factory_attr, None)
        if callable(factory):
            backends.append(factory(worker_services))
    return tuple(backends)


def create_live_viewer_widget_binders(
    *,
    preferences_document: Any = None,
    store: AppPreferencesStore | None = None,
) -> tuple[tuple[str, Any], ...]:
    binders: list[tuple[str, Any]] = []
    for registration in live_addon_registrations(
        preferences_document=preferences_document,
        store=store,
    ):
        factory_attr = str(registration.viewer_widget_binder_factory_attr or "").strip()
        if not factory_attr:
            continue
        factory = getattr(import_addon_backend_module(registration), factory_attr, None)
        if callable(factory):
            binder = factory()
            backend_id = str(getattr(binder, "backend_id", "") or registration.backend_id).strip()
            if backend_id:
                binders.append((backend_id, binder))
    return tuple(binders)


__all__ = [
    "ANSYS_DPF_ADDON_ID",
    "AddOnRegistration",
    "REGISTERED_ADDON_REGISTRATIONS",
    "addon_registration_is_live_enabled",
    "create_live_execution_viewer_backends",
    "create_live_viewer_widget_binders",
    "import_addon_backend_module",
    "invalidate_addon_runtime_caches",
    "live_addon_registrations",
    "registered_addon_registration_by_id",
    "registered_addon_registrations",
    "sync_live_addon_state",
]
