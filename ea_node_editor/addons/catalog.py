from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, replace
from typing import Any

from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    addon_state,
    default_app_preferences_document,
    normalize_app_preferences_document,
)
from ea_node_editor.addons.ansys_dpf.metadata import (
    ANSYS_DPF_ADDON_ID,
    ANSYS_DPF_ADDON_MANIFEST,
)
from ea_node_editor.nodes.plugin_contracts import AddOnManifest
from ea_node_editor.nodes.plugin_contracts import AddOnRecord
from ea_node_editor.nodes.plugin_contracts import AddOnState
from ea_node_editor.nodes.plugin_contracts import PluginAvailability
from ea_node_editor.nodes.plugin_contracts import PluginBackendDescriptor

logger = logging.getLogger(__name__)


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
    node_backend_module: str = ""


@dataclass(slots=True, frozen=True)
class AddOnBackendCollection:
    registration: AddOnRegistration
    source: str
    backends: tuple[PluginBackendDescriptor, ...]


REGISTERED_ADDON_REGISTRATIONS = (
    AddOnRegistration(
        manifest=ANSYS_DPF_ADDON_MANIFEST,
        backend_module="ea_node_editor.addons.ansys_dpf.catalog",
        backend_id=ANSYS_DPF_ADDON_ID,
        node_backend_module="ea_node_editor.nodes.builtins.ansys_dpf_catalog",
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


def _addon_backend_module_name(registration: AddOnRegistration, *, for_nodes: bool = False) -> str:
    if for_nodes:
        module_name = str(registration.node_backend_module or "").strip()
        if module_name:
            return module_name
    return str(registration.backend_module).strip()


def _addon_backend_module_names(registration: AddOnRegistration) -> tuple[str, ...]:
    names: list[str] = []
    for module_name in (
        _addon_backend_module_name(registration),
        _addon_backend_module_name(registration, for_nodes=True),
    ):
        if module_name and module_name not in names:
            names.append(module_name)
    return tuple(names)


def import_addon_backend_module(registration: AddOnRegistration, *, for_nodes: bool = False) -> Any:
    module_name = _addon_backend_module_name(registration, for_nodes=for_nodes)
    if not module_name:
        raise ValueError(f"Add-on {registration.manifest.addon_id!r} is missing backend_module")
    return importlib.import_module(module_name)


def _module_plugin_backends(
    module: Any,
    *,
    collection_attr: str = "PLUGIN_BACKENDS",
) -> tuple[PluginBackendDescriptor, ...] | None:
    raw_backends = getattr(module, collection_attr, None)
    if raw_backends is None:
        return None
    try:
        backends = tuple(raw_backends)
    except TypeError as exc:
        raise TypeError(f"{collection_attr} must be an iterable of PluginBackendDescriptor values") from exc
    if any(not isinstance(backend, PluginBackendDescriptor) for backend in backends):
        raise TypeError(f"{collection_attr} entries must be PluginBackendDescriptor values")
    return backends


def load_addon_backend_from_registration(
    registration: AddOnRegistration,
    *,
    for_nodes: bool = False,
) -> tuple[PluginBackendDescriptor | None, Any | None]:
    module_name = _addon_backend_module_name(registration, for_nodes=for_nodes)
    try:
        module = import_addon_backend_module(registration, for_nodes=for_nodes)
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to import add-on backend module %s",
            module_name,
            exc_info=True,
        )
        return None, None

    try:
        backends = _module_plugin_backends(
            module,
            collection_attr=registration.backend_collection_attr,
        ) or ()
    except TypeError:
        logger.warning(
            "Ignoring invalid add-on backend registration from %s",
            module_name,
            exc_info=True,
        )
        return None, module

    for backend in backends:
        if backend.plugin_id == registration.backend_id:
            return backend, module

    logger.warning(
        "Add-on backend %s was not found in %s",
        registration.backend_id,
        module_name,
    )
    return None, module


def _sync_addon_registration_state(
    registration: AddOnRegistration,
    module: Any,
    *,
    store: AppPreferencesStore | None,
) -> None:
    if store is None:
        return
    sync_state_attr = str(registration.sync_state_attr or "").strip()
    if not sync_state_attr:
        return
    sync_state = getattr(module, sync_state_attr, None)
    if callable(sync_state):
        sync_state(store=store)


def _resolve_addon_version(
    manifest: AddOnManifest,
    *,
    module: Any,
    registration: AddOnRegistration,
) -> str:
    version = manifest.version
    version_resolver_attr = str(registration.version_resolver_attr or "").strip()
    if module is None or not version_resolver_attr:
        return version
    version_resolver = getattr(module, version_resolver_attr, None)
    if not callable(version_resolver):
        return version
    try:
        resolved_version = version_resolver()
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to resolve add-on version for %s",
            manifest.addon_id,
            exc_info=True,
        )
        return version
    return str(resolved_version or version)


def _unavailable_addon_availability(
    manifest: AddOnManifest,
    *,
    reason: str = "",
) -> PluginAvailability:
    summary = reason.strip()
    if not summary:
        summary = (
            f"{manifest.display_name} could not initialize its backend metadata; "
            "the add-on remains unavailable."
        )
    return PluginAvailability.missing_dependency(*manifest.dependencies, summary=summary)


def discover_addon_records(*, preferences_document: Any = None) -> tuple[AddOnRecord, ...]:
    normalized_preferences = normalize_app_preferences_document(preferences_document)
    records: list[AddOnRecord] = []

    for registration in registered_addon_registrations():
        manifest = registration.manifest
        backend, module = load_addon_backend_from_registration(registration)

        if backend is None:
            availability = _unavailable_addon_availability(manifest)
        else:
            manifest = backend.addon_manifest or manifest
            try:
                availability = backend.get_availability()
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to resolve add-on availability for %s",
                    manifest.addon_id,
                    exc_info=True,
                )
                availability = _unavailable_addon_availability(
                    manifest,
                    reason=f"{manifest.display_name} failed to resolve add-on availability.",
                )

        state_payload = addon_state(normalized_preferences, manifest.addon_id)
        state = AddOnState(
            enabled=state_payload["enabled"],
            pending_restart=state_payload["pending_restart"],
        )

        provided_node_type_ids: tuple[str, ...] = ()
        if backend is not None and availability.is_available:
            try:
                descriptors = backend.load_descriptors()
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to resolve provided node types for add-on %s",
                    manifest.addon_id,
                    exc_info=True,
                )
            else:
                provided_node_type_ids = tuple(
                    dict.fromkeys(descriptor.spec.type_id for descriptor in descriptors)
                )

        manifest = replace(
            manifest,
            version=_resolve_addon_version(manifest, module=module, registration=registration),
        )
        records.append(
            AddOnRecord(
                manifest=manifest,
                state=state,
                availability=availability,
                provided_node_type_ids=provided_node_type_ids,
            )
        )

    return tuple(records)


def addon_record_by_id(addon_id: str, *, preferences_document: Any = None) -> AddOnRecord | None:
    normalized_addon_id = str(addon_id).strip()
    if not normalized_addon_id:
        return None
    for record in discover_addon_records(preferences_document=preferences_document):
        if record.addon_id == normalized_addon_id:
            return record
    return None


def live_addon_backend_collections(
    *,
    preferences_document: Any = None,
    store: AppPreferencesStore | None = None,
) -> tuple[AddOnBackendCollection, ...]:
    collections: list[AddOnBackendCollection] = []
    for registration in live_addon_registrations(
        preferences_document=preferences_document,
        store=store,
    ):
        source = _addon_backend_module_name(registration, for_nodes=True)
        try:
            module = import_addon_backend_module(registration, for_nodes=True)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to import add-on node backend module %s", source, exc_info=True)
            continue
        _sync_addon_registration_state(registration, module, store=store)
        try:
            backends = _module_plugin_backends(
                module,
                collection_attr=registration.backend_collection_attr,
            ) or ()
        except TypeError:
            logger.warning(
                "Ignoring invalid add-on node backend registration from %s",
                source,
                exc_info=True,
            )
            continue
        if backends:
            collections.append(
                AddOnBackendCollection(
                    registration=registration,
                    source=source,
                    backends=backends,
                )
            )
    return tuple(collections)


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
        _sync_addon_registration_state(
            registration,
            import_addon_backend_module(registration, for_nodes=True),
            store=store,
        )


def invalidate_addon_runtime_caches(addon_id: str) -> bool:
    registration = registered_addon_registration_by_id(addon_id)
    if registration is None:
        return False
    invalidator_attr = str(registration.cache_invalidator_attr or "").strip()
    if not invalidator_attr:
        return False
    invalidated = False
    for module_name in _addon_backend_module_names(registration):
        try:
            module = importlib.import_module(module_name)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to import add-on cache module %s", module_name, exc_info=True)
            continue
        invalidator = getattr(module, invalidator_attr, None)
        if not callable(invalidator):
            continue
        invalidator()
        invalidated = True
    return invalidated


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
    "AddOnBackendCollection",
    "AddOnRegistration",
    "REGISTERED_ADDON_REGISTRATIONS",
    "addon_record_by_id",
    "addon_registration_is_live_enabled",
    "create_live_execution_viewer_backends",
    "create_live_viewer_widget_binders",
    "discover_addon_records",
    "import_addon_backend_module",
    "invalidate_addon_runtime_caches",
    "live_addon_backend_collections",
    "live_addon_registrations",
    "load_addon_backend_from_registration",
    "registered_addon_registration_by_id",
    "registered_addon_registrations",
    "sync_live_addon_state",
]
