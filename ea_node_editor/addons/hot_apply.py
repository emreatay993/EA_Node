from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ea_node_editor.addons.catalog import (
    invalidate_addon_runtime_caches,
    registered_addon_registration_by_id,
)
from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    default_app_preferences_document,
    normalize_app_preferences_document,
    set_addon_state,
)
from ea_node_editor.nodes.bootstrap import build_default_registry

if TYPE_CHECKING:
    from pathlib import Path

    from ea_node_editor.execution.worker_services import WorkerServices
    from ea_node_editor.nodes.registry import NodeRegistry
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewer_host_service import ViewerHostService


@dataclass(slots=True, frozen=True)
class AddOnApplyResult:
    addon_id: str
    enabled: bool
    apply_policy: str
    restart_required: bool
    preferences_document: dict[str, Any]
    registry: "NodeRegistry | None" = None


def apply_addon_enabled_state(
    addon_id: str,
    *,
    enabled: bool,
    app_preferences_store: AppPreferencesStore | None = None,
    preferences_document: Any = None,
    extra_plugin_dirs: list["Path"] | None = None,
    graph_scene_bridge: "GraphSceneBridge | None" = None,
    worker_services: "WorkerServices | None" = None,
    viewer_host_service: "ViewerHostService | None" = None,
    on_registry_rebuilt: Callable[["NodeRegistry"], None] | None = None,
) -> AddOnApplyResult:
    registration = registered_addon_registration_by_id(addon_id)
    if registration is None:
        raise KeyError(f"Unknown add-on id: {addon_id!r}")

    preferences_store = app_preferences_store
    if preferences_store is None and preferences_document is None:
        preferences_store = AppPreferencesStore()

    base_document = (
        normalize_app_preferences_document(preferences_document)
        if preferences_document is not None
        else normalize_app_preferences_document(
            preferences_store.load_document()
            if preferences_store is not None
            else default_app_preferences_document()
        )
    )

    restart_required = registration.manifest.apply_policy != "hot_apply"
    updated_document = set_addon_state(
        base_document,
        registration.manifest.addon_id,
        enabled=enabled,
        pending_restart=restart_required,
    )
    if preferences_store is not None:
        updated_document = preferences_store.persist_document(updated_document)

    if restart_required:
        return AddOnApplyResult(
            addon_id=registration.manifest.addon_id,
            enabled=bool(enabled),
            apply_policy=registration.manifest.apply_policy,
            restart_required=True,
            preferences_document=updated_document,
            registry=None,
        )

    invalidate_addon_runtime_caches(registration.manifest.addon_id)
    rebuilt_registry = build_default_registry(
        extra_plugin_dirs=extra_plugin_dirs,
        app_preferences_store=preferences_store,
        preferences_document=updated_document,
    )
    if callable(on_registry_rebuilt):
        on_registry_rebuilt(rebuilt_registry)
    if graph_scene_bridge is not None:
        graph_scene_bridge.rebuild_registry(rebuilt_registry)
    if worker_services is not None:
        worker_services.rebuild_addon_runtime(preferences_document=updated_document)
    if viewer_host_service is not None:
        viewer_host_service.rebuild_addon_binders(
            preferences_document=updated_document,
            reason=f"addon_apply:{registration.manifest.addon_id}",
        )
    return AddOnApplyResult(
        addon_id=registration.manifest.addon_id,
        enabled=bool(enabled),
        apply_policy=registration.manifest.apply_policy,
        restart_required=False,
        preferences_document=updated_document,
        registry=rebuilt_registry,
    )


__all__ = [
    "AddOnApplyResult",
    "apply_addon_enabled_state",
]
