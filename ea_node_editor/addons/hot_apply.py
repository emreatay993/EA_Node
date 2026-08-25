from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Protocol

from ea_node_editor.addons.catalog import (
    invalidate_addon_runtime_caches,
    registered_addon_registration_by_id,
)
from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    addon_state,
    default_app_preferences_document,
    normalize_app_preferences_document,
    set_addon_state,
)

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


class AddOnRuntimeCoordinator(Protocol):
    def rebuild_after_addon_apply(
        self,
        *,
        addon_id: str,
        preferences_document: Any,
        app_preferences_store: AppPreferencesStore | None = None,
        extra_plugin_dirs: list["Path"] | None = None,
    ) -> "NodeRegistry":
        ...


@dataclass(slots=True)
class AddOnRuntimeRebuildCoordinator:
    """Standalone service rebuild helper; the live shell uses its guarded coordinator."""

    graph_scene_bridge: "GraphSceneBridge | None" = None
    worker_services: "WorkerServices | None" = None
    viewer_host_service: "ViewerHostService | None" = None
    on_registry_rebuilt: Callable[["NodeRegistry"], None] | None = None

    def rebuild_after_addon_apply(
        self,
        *,
        addon_id: str,
        preferences_document: Any,
        app_preferences_store: AppPreferencesStore | None = None,
        extra_plugin_dirs: list["Path"] | None = None,
    ) -> "NodeRegistry":
        normalized_document = normalize_app_preferences_document(preferences_document)
        invalidate_addon_runtime_caches(addon_id)
        from ea_node_editor.nodes.bootstrap import build_default_registry

        rebuilt_registry = build_default_registry(
            extra_plugin_dirs=extra_plugin_dirs,
            app_preferences_store=app_preferences_store,
            preferences_document=normalized_document,
        )
        accepted_enabled = dict(rebuilt_registry.addon_runtime_config()).get(
            addon_id
        )
        requested_enabled = bool(addon_state(normalized_document, addon_id)["enabled"])
        if accepted_enabled is not requested_enabled:
            raise RuntimeError("Add-on registry identity does not match preferences")
        rebuilt_registry.contract_fingerprint()
        if self.worker_services is not None:
            self.worker_services.rebuild_addon_runtime(preferences_document=normalized_document)
        if self.viewer_host_service is not None:
            self.viewer_host_service.rebuild_addon_binders(
                preferences_document=normalized_document,
                reason=f"addon_apply:{addon_id}",
            )
        if self.graph_scene_bridge is not None:
            self.graph_scene_bridge.replace_registry(rebuilt_registry)
        if callable(self.on_registry_rebuilt):
            self.on_registry_rebuilt(rebuilt_registry)
        return rebuilt_registry


def persist_addon_enabled_state(
    addon_id: str,
    *,
    enabled: bool,
    app_preferences_store: AppPreferencesStore | None = None,
    preferences_document: Any = None,
) -> AddOnApplyResult:
    """Persist add-on enabled state without rebuilding runtime services."""
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

    return AddOnApplyResult(
        addon_id=registration.manifest.addon_id,
        enabled=bool(enabled),
        apply_policy=registration.manifest.apply_policy,
        restart_required=restart_required,
        preferences_document=updated_document,
        registry=None,
    )


def rebuild_hot_apply_runtime(
    addon_id: str,
    *,
    preferences_document: Any,
    app_preferences_store: AppPreferencesStore | None = None,
    extra_plugin_dirs: list["Path"] | None = None,
    graph_scene_bridge: "GraphSceneBridge | None" = None,
    worker_services: "WorkerServices | None" = None,
    viewer_host_service: "ViewerHostService | None" = None,
    on_registry_rebuilt: Callable[["NodeRegistry"], None] | None = None,
    runtime_coordinator: AddOnRuntimeCoordinator | None = None,
) -> "NodeRegistry":
    registration = registered_addon_registration_by_id(addon_id)
    if registration is None:
        raise KeyError(f"Unknown add-on id: {addon_id!r}")
    if registration.manifest.apply_policy != "hot_apply":
        raise ValueError(f"Add-on {addon_id!r} requires restart and cannot be hot-applied")

    normalized_document = normalize_app_preferences_document(preferences_document)
    coordinator = runtime_coordinator or AddOnRuntimeRebuildCoordinator(
        graph_scene_bridge=graph_scene_bridge,
        worker_services=worker_services,
        viewer_host_service=viewer_host_service,
        on_registry_rebuilt=on_registry_rebuilt,
    )
    return coordinator.rebuild_after_addon_apply(
        addon_id=registration.manifest.addon_id,
        preferences_document=normalized_document,
        app_preferences_store=app_preferences_store,
        extra_plugin_dirs=extra_plugin_dirs,
    )


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
    runtime_coordinator: AddOnRuntimeCoordinator | None = None,
) -> AddOnApplyResult:
    preferences_store = app_preferences_store
    if preferences_store is None and preferences_document is None:
        preferences_store = AppPreferencesStore()

    base_document = (
        preferences_document
        if preferences_document is not None
        else (
            preferences_store.load_document()
            if preferences_store is not None
            else default_app_preferences_document()
        )
    )
    staged = persist_addon_enabled_state(
        addon_id,
        enabled=enabled,
        preferences_document=base_document,
    )

    if staged.restart_required:
        preferences_document = (
            preferences_store.persist_document(staged.preferences_document)
            if preferences_store is not None
            else staged.preferences_document
        )
        return replace(staged, preferences_document=preferences_document)

    rebuilt_registry = rebuild_hot_apply_runtime(
        staged.addon_id,
        preferences_document=staged.preferences_document,
        app_preferences_store=preferences_store,
        extra_plugin_dirs=extra_plugin_dirs,
        graph_scene_bridge=graph_scene_bridge,
        worker_services=worker_services,
        viewer_host_service=viewer_host_service,
        on_registry_rebuilt=on_registry_rebuilt,
        runtime_coordinator=runtime_coordinator,
    )
    persisted_document = (
        preferences_store.persist_document(staged.preferences_document)
        if preferences_store is not None
        else staged.preferences_document
    )
    return replace(
        staged,
        preferences_document=persisted_document,
        registry=rebuilt_registry,
    )


__all__ = [
    "AddOnApplyResult",
    "AddOnRuntimeCoordinator",
    "AddOnRuntimeRebuildCoordinator",
    "apply_addon_enabled_state",
    "persist_addon_enabled_state",
    "rebuild_hot_apply_runtime",
]
