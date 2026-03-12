from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.persistence.utils import merge_defaults, write_json_atomic
from ea_node_editor.settings import (
    APP_PREFERENCES_KIND,
    APP_PREFERENCES_VERSION,
    DEFAULT_APP_PREFERENCES,
    DEFAULT_GRAPHICS_SETTINGS,
    app_preferences_path,
)

_ALLOWED_THEME_IDS = frozenset({"stitch_dark", "stitch_light"})


def default_app_preferences_document() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_APP_PREFERENCES)


def normalize_graphics_settings(payload: Any) -> dict[str, Any]:
    defaults = DEFAULT_GRAPHICS_SETTINGS
    if not isinstance(payload, Mapping):
        return copy.deepcopy(defaults)

    canvas_payload = payload.get("canvas")
    interaction_payload = payload.get("interaction")
    theme_payload = payload.get("theme")

    normalized = copy.deepcopy(defaults)
    if isinstance(canvas_payload, Mapping):
        normalized["canvas"]["show_grid"] = _normalize_bool(
            canvas_payload.get("show_grid"),
            defaults["canvas"]["show_grid"],
        )
        normalized["canvas"]["show_minimap"] = _normalize_bool(
            canvas_payload.get("show_minimap"),
            defaults["canvas"]["show_minimap"],
        )
        normalized["canvas"]["minimap_expanded"] = _normalize_bool(
            canvas_payload.get("minimap_expanded"),
            defaults["canvas"]["minimap_expanded"],
        )
    if isinstance(interaction_payload, Mapping):
        normalized["interaction"]["snap_to_grid"] = _normalize_bool(
            interaction_payload.get("snap_to_grid"),
            defaults["interaction"]["snap_to_grid"],
        )
    if isinstance(theme_payload, Mapping):
        normalized["theme"]["theme_id"] = _normalize_theme_id(
            theme_payload.get("theme_id"),
            defaults["theme"]["theme_id"],
        )
    return normalized


def normalize_app_preferences_document(payload: Any) -> dict[str, Any]:
    normalized = default_app_preferences_document()
    if not isinstance(payload, Mapping):
        return normalized

    kind = str(payload.get("kind", "")).strip()
    try:
        version = int(payload.get("version", 0) or 0)
    except (TypeError, ValueError):
        return normalized

    if kind != APP_PREFERENCES_KIND or version != APP_PREFERENCES_VERSION:
        return normalized

    normalized["graphics"] = normalize_graphics_settings(payload.get("graphics"))
    return normalized


class AppPreferencesStore:
    def __init__(
        self,
        *,
        path_provider: Callable[[], Path] = app_preferences_path,
    ) -> None:
        self._path_provider = path_provider

    def load_document(self) -> dict[str, Any]:
        path = self._path_provider()
        if not path.exists():
            return default_app_preferences_document()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return default_app_preferences_document()
        return normalize_app_preferences_document(payload)

    def persist_document(self, document: Any) -> dict[str, Any]:
        normalized = normalize_app_preferences_document(document)
        write_json_atomic(self._path_provider(), normalized)
        return normalized


class AppPreferencesController:
    def __init__(
        self,
        *,
        store: AppPreferencesStore | None = None,
    ) -> None:
        self._store = store or AppPreferencesStore()
        self._document: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        self._document = self._store.load_document()
        return copy.deepcopy(self._document)

    def document(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document())

    def graphics_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document()["graphics"])

    def set_graphics_settings(self, graphics: Any) -> dict[str, Any]:
        document = self._ensure_document()
        document["graphics"] = normalize_graphics_settings(graphics)
        self.persist()
        return self.graphics_settings()

    def update_graphics_settings(self, updates: Any) -> dict[str, Any]:
        current = self.graphics_settings()
        merged = merge_defaults(updates, current)
        return self.set_graphics_settings(merged)

    def persist(self) -> dict[str, Any]:
        self._document = self._store.persist_document(self._ensure_document())
        return copy.deepcopy(self._document)

    def _ensure_document(self) -> dict[str, Any]:
        if self._document is None:
            self._document = self._store.load_document()
        return self._document


def _normalize_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _normalize_theme_id(value: Any, default: str) -> str:
    normalized = str(value).strip()
    if normalized in _ALLOWED_THEME_IDS:
        return normalized
    return default


__all__ = [
    "AppPreferencesController",
    "AppPreferencesStore",
    "default_app_preferences_document",
    "normalize_app_preferences_document",
    "normalize_graphics_settings",
]
