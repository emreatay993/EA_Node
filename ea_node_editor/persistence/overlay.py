from __future__ import annotations

import copy
import weakref
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


def _copy_overlay_docs(value: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    copied: dict[str, dict[str, Any]] = {}
    for raw_key, raw_doc in value.items():
        key = str(raw_key).strip()
        if not key or not isinstance(raw_doc, Mapping):
            continue
        copied[key] = copy.deepcopy(dict(raw_doc))
    return copied


@dataclass(slots=True)
class UnresolvedPluginOverlay:
    node_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    edge_docs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def clone(self) -> "UnresolvedPluginOverlay":
        return UnresolvedPluginOverlay(
            node_docs=_copy_overlay_docs(self.node_docs),
            edge_docs=_copy_overlay_docs(self.edge_docs),
        )


@dataclass(slots=True)
class AuthoredNodeOverrideOverlay:
    node_docs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def clone(self) -> "AuthoredNodeOverrideOverlay":
        return AuthoredNodeOverrideOverlay(node_docs=_copy_overlay_docs(self.node_docs))


@dataclass(slots=True)
class WorkspacePersistenceOverlay:
    unresolved_plugins: UnresolvedPluginOverlay = field(default_factory=UnresolvedPluginOverlay)
    authored_node_overrides: AuthoredNodeOverrideOverlay = field(default_factory=AuthoredNodeOverrideOverlay)

    def clone(self) -> "WorkspacePersistenceOverlay":
        return WorkspacePersistenceOverlay(
            unresolved_plugins=self.unresolved_plugins.clone(),
            authored_node_overrides=self.authored_node_overrides.clone(),
        )


_WORKSPACE_OVERLAYS: dict[int, tuple[weakref.ReferenceType[object], WorkspacePersistenceOverlay]] = {}


def _overlay_ref(workspace: object, overlay: WorkspacePersistenceOverlay) -> tuple[weakref.ReferenceType[object], WorkspacePersistenceOverlay]:
    workspace_id = id(workspace)
    ref = weakref.ref(workspace, lambda _ref, workspace_id=workspace_id: _WORKSPACE_OVERLAYS.pop(workspace_id, None))
    return ref, overlay


def workspace_persistence_overlay(workspace: object) -> WorkspacePersistenceOverlay:
    workspace_id = id(workspace)
    existing = _WORKSPACE_OVERLAYS.get(workspace_id)
    if existing is not None:
        ref, overlay = existing
        if ref() is workspace:
            return overlay
    overlay = WorkspacePersistenceOverlay()
    _WORKSPACE_OVERLAYS[workspace_id] = _overlay_ref(workspace, overlay)
    return overlay


def copy_workspace_persistence_overlay(source: object, target: object) -> WorkspacePersistenceOverlay:
    overlay = workspace_persistence_overlay(source).clone()
    _WORKSPACE_OVERLAYS[id(target)] = _overlay_ref(target, overlay)
    return overlay


def set_workspace_unresolved_node_docs(workspace: object, value: Mapping[str, Any] | None) -> None:
    workspace_persistence_overlay(workspace).unresolved_plugins.node_docs = _copy_overlay_docs(value)


def set_workspace_unresolved_edge_docs(workspace: object, value: Mapping[str, Any] | None) -> None:
    workspace_persistence_overlay(workspace).unresolved_plugins.edge_docs = _copy_overlay_docs(value)


def set_workspace_authored_node_overrides(workspace: object, value: Mapping[str, Any] | None) -> None:
    workspace_persistence_overlay(workspace).authored_node_overrides.node_docs = _copy_overlay_docs(value)
