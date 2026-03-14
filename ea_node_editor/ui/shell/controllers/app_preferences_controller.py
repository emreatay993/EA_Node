from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ea_node_editor.persistence.utils import merge_defaults, write_json_atomic
from ea_node_editor.settings import (
    APP_PREFERENCES_KIND,
    APP_PREFERENCES_VERSION,
    DEFAULT_APP_PREFERENCES,
    DEFAULT_GRAPHICS_SETTINGS,
    app_preferences_path,
)
from ea_node_editor.ui.graph_theme import (
    DEFAULT_GRAPH_THEME_ID,
    create_blank_custom_graph_theme,
    duplicate_graph_theme_as_custom,
    graph_theme_choices as available_graph_theme_choices,
    graph_theme_registry,
    is_custom_graph_theme_id,
    is_known_graph_theme_id,
    normalize_custom_graph_theme_definition,
    resolve_graph_theme_id,
    serialize_custom_graph_themes,
)
from ea_node_editor.ui.theme import DEFAULT_THEME_ID, is_known_theme_id

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow

_APP_PREFERENCES_MIGRATION_VERSION = 1


def default_app_preferences_document() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_APP_PREFERENCES)


def normalize_graph_theme_settings(payload: Any) -> dict[str, Any]:
    defaults = DEFAULT_GRAPHICS_SETTINGS["graph_theme"]
    if not isinstance(payload, Mapping):
        return copy.deepcopy(defaults)

    normalized = copy.deepcopy(defaults)
    normalized["follow_shell_theme"] = _normalize_bool(
        payload.get("follow_shell_theme"),
        defaults["follow_shell_theme"],
    )
    normalized["custom_themes"] = serialize_custom_graph_themes(payload.get("custom_themes"))
    normalized["selected_theme_id"] = _normalize_graph_theme_id(
        payload.get("selected_theme_id"),
        defaults["selected_theme_id"],
        custom_themes=normalized["custom_themes"],
    )
    return normalized


def normalize_graphics_settings(payload: Any) -> dict[str, Any]:
    defaults = DEFAULT_GRAPHICS_SETTINGS
    if not isinstance(payload, Mapping):
        return copy.deepcopy(defaults)

    canvas_payload = payload.get("canvas")
    interaction_payload = payload.get("interaction")
    theme_payload = payload.get("theme")
    graph_theme_payload = payload.get("graph_theme")

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
        normalized["canvas"]["node_shadow"] = _normalize_bool(
            canvas_payload.get("node_shadow"),
            defaults["canvas"]["node_shadow"],
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
    normalized["graph_theme"] = normalize_graph_theme_settings(graph_theme_payload)
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

    if kind != APP_PREFERENCES_KIND:
        return normalized
    if version not in {_APP_PREFERENCES_MIGRATION_VERSION, APP_PREFERENCES_VERSION}:
        return normalized

    normalized["graphics"] = normalize_graphics_settings(payload.get("graphics"))
    return normalized


class AppPreferencesStore:
    def __init__(
        self,
        *,
        path_provider: Callable[[], Path] | None = None,
    ) -> None:
        self._path_provider = path_provider or app_preferences_path

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

    def load_into_host(self, host: ShellWindow) -> dict[str, Any]:
        self._document = self._store.load_document()
        return self.apply_graphics_settings_to_host(host)

    def document(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document())

    def graphics_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document()["graphics"])

    def graph_theme_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self.graphics_settings()["graph_theme"])

    def graph_theme_choices(self) -> tuple[tuple[str, str], ...]:
        settings = self.graph_theme_settings()
        return available_graph_theme_choices(settings.get("custom_themes"))

    def custom_graph_themes(self) -> list[dict[str, object]]:
        settings = self.graph_theme_settings()
        custom_themes = settings.get("custom_themes")
        if not isinstance(custom_themes, list):
            return []
        return copy.deepcopy(custom_themes)

    def apply_graphics_settings_to_host(
        self,
        host: ShellWindow,
        graphics: Any | None = None,
    ) -> dict[str, Any]:
        resolved = self.graphics_settings() if graphics is None else normalize_graphics_settings(graphics)
        host.apply_graphics_preferences(resolved)
        return copy.deepcopy(resolved)

    def set_graphics_settings(self, graphics: Any, *, host: ShellWindow | None = None) -> dict[str, Any]:
        document = self._ensure_document()
        document["graphics"] = normalize_graphics_settings(graphics)
        self.persist()
        resolved = self.graphics_settings()
        if host is not None:
            host.apply_graphics_preferences(resolved)
        return resolved

    def update_graphics_settings(self, updates: Any, *, host: ShellWindow | None = None) -> dict[str, Any]:
        current = self.graphics_settings()
        merged = merge_defaults(updates, current)
        return self.set_graphics_settings(merged, host=host)

    def create_blank_custom_graph_theme(
        self,
        *,
        label: object | None = None,
        host: ShellWindow | None = None,
    ) -> dict[str, object]:
        settings = self.graph_theme_settings()
        theme = create_blank_custom_graph_theme(
            custom_themes=settings.get("custom_themes"),
            label=label,
        )
        updated_settings = copy.deepcopy(settings)
        updated_settings["custom_themes"] = [*self.custom_graph_themes(), theme.as_dict()]
        saved_settings = self._set_graph_theme_settings(updated_settings, host=host)
        return _find_custom_theme(saved_settings.get("custom_themes"), theme.theme_id) or theme.as_dict()

    def duplicate_graph_theme(
        self,
        theme_id: object,
        *,
        label: object | None = None,
        host: ShellWindow | None = None,
    ) -> dict[str, object] | None:
        settings = self.graph_theme_settings()
        custom_themes = settings.get("custom_themes")
        if not is_known_graph_theme_id(theme_id, custom_themes=custom_themes):
            return None
        theme = duplicate_graph_theme_as_custom(
            theme_id,
            custom_themes=custom_themes,
            label=label,
        )
        updated_settings = copy.deepcopy(settings)
        updated_settings["custom_themes"] = [*self.custom_graph_themes(), theme.as_dict()]
        saved_settings = self._set_graph_theme_settings(updated_settings, host=host)
        return _find_custom_theme(saved_settings.get("custom_themes"), theme.theme_id) or theme.as_dict()

    def rename_custom_graph_theme(
        self,
        theme_id: object,
        label: object,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, object] | None:
        normalized_theme_id = str(theme_id).strip().lower()
        if not is_custom_graph_theme_id(normalized_theme_id):
            return None
        existing_theme = _find_custom_theme(self.custom_graph_themes(), normalized_theme_id)
        if existing_theme is None:
            return None
        existing_theme["label"] = label
        return self.save_custom_graph_theme(existing_theme, host=host)

    def delete_custom_graph_theme(self, theme_id: object, *, host: ShellWindow | None = None) -> bool:
        normalized_theme_id = str(theme_id).strip().lower()
        if not is_custom_graph_theme_id(normalized_theme_id):
            return False

        settings = self.graph_theme_settings()
        current_custom_themes = self.custom_graph_themes()
        updated_custom_themes = [
            theme
            for theme in current_custom_themes
            if str(theme.get("theme_id", "")).strip().lower() != normalized_theme_id
        ]
        if len(updated_custom_themes) == len(current_custom_themes):
            return False

        updated_settings = copy.deepcopy(settings)
        updated_settings["custom_themes"] = updated_custom_themes
        if str(updated_settings.get("selected_theme_id", "")).strip().lower() == normalized_theme_id:
            updated_settings["selected_theme_id"] = DEFAULT_GRAPH_THEME_ID
        self._set_graph_theme_settings(updated_settings, host=host)
        return True

    def save_custom_graph_theme(
        self,
        theme: Any,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, object]:
        settings = self.graph_theme_settings()
        current_custom_themes = self.custom_graph_themes()
        existing_theme_id = str(_theme_identity(theme)).strip().lower()
        existing_index = _find_custom_theme_index(current_custom_themes, existing_theme_id)

        retained_custom_themes = current_custom_themes
        if existing_index >= 0:
            retained_custom_themes = [
                existing_theme
                for index, existing_theme in enumerate(current_custom_themes)
                if index != existing_index
            ]

        normalized_theme = normalize_custom_graph_theme_definition(
            theme,
            reserved_theme_ids=graph_theme_registry(retained_custom_themes),
        )
        saved_theme = normalized_theme.as_dict()
        if existing_index >= 0:
            retained_custom_themes.insert(existing_index, saved_theme)
        else:
            retained_custom_themes.append(saved_theme)

        updated_settings = copy.deepcopy(settings)
        updated_settings["custom_themes"] = retained_custom_themes
        if existing_index >= 0 and existing_theme_id == str(settings.get("selected_theme_id", "")).strip().lower():
            updated_settings["selected_theme_id"] = normalized_theme.theme_id

        saved_settings = self._set_graph_theme_settings(updated_settings, host=host)
        return _find_custom_theme(saved_settings.get("custom_themes"), normalized_theme.theme_id) or saved_theme

    def persist(self) -> dict[str, Any]:
        self._document = self._store.persist_document(self._ensure_document())
        return copy.deepcopy(self._document)

    def _ensure_document(self) -> dict[str, Any]:
        if self._document is None:
            self._document = self._store.load_document()
        return self._document

    def _set_graph_theme_settings(
        self,
        graph_theme_settings: Any,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        graphics = self.graphics_settings()
        graphics["graph_theme"] = normalize_graph_theme_settings(graph_theme_settings)
        return self.set_graphics_settings(graphics, host=host)["graph_theme"]


def _normalize_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _normalize_theme_id(value: Any, default: str) -> str:
    normalized = str(value).strip()
    if is_known_theme_id(normalized):
        return normalized
    if is_known_theme_id(default):
        return default
    return DEFAULT_THEME_ID


def _normalize_graph_theme_id(value: Any, default: str, *, custom_themes: Any = None) -> str:
    normalized = str(value).strip()
    if is_known_graph_theme_id(normalized, custom_themes=custom_themes):
        return normalized
    resolved_default = resolve_graph_theme_id(default, custom_themes=custom_themes)
    if is_known_graph_theme_id(resolved_default, custom_themes=custom_themes):
        return resolved_default
    return DEFAULT_GRAPH_THEME_ID


def _find_custom_theme(custom_themes: Any, theme_id: object) -> dict[str, object] | None:
    normalized_theme_id = str(theme_id).strip().lower()
    if not isinstance(custom_themes, list):
        return None
    for theme in custom_themes:
        if not isinstance(theme, Mapping):
            continue
        if str(theme.get("theme_id", "")).strip().lower() == normalized_theme_id:
            return copy.deepcopy(dict(theme))
    return None


def _find_custom_theme_index(custom_themes: Any, theme_id: object) -> int:
    normalized_theme_id = str(theme_id).strip().lower()
    if not isinstance(custom_themes, list):
        return -1
    for index, theme in enumerate(custom_themes):
        if not isinstance(theme, Mapping):
            continue
        if str(theme.get("theme_id", "")).strip().lower() == normalized_theme_id:
            return index
    return -1


def _theme_identity(theme: Any) -> Any:
    if isinstance(theme, Mapping):
        return theme.get("theme_id")
    return getattr(theme, "theme_id", theme)


__all__ = [
    "AppPreferencesController",
    "AppPreferencesStore",
    "default_app_preferences_document",
    "normalize_app_preferences_document",
    "normalize_graph_theme_settings",
    "normalize_graphics_settings",
]
