from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    default_app_preferences_document,
    normalize_app_preferences_document,
    normalize_expand_collision_avoidance_settings,
    normalize_graph_theme_settings,
    normalize_graphics_settings,
    normalize_source_import_mode,
    normalize_source_import_settings,
)
from ea_node_editor.graph_theme_defaults import DEFAULT_GRAPH_THEME_ID
from ea_node_editor.persistence.utils import merge_defaults
from ea_node_editor.settings import app_preferences_path
from ea_node_editor.ui.graph_theme import (
    create_blank_custom_graph_theme,
    duplicate_graph_theme_as_custom,
    graph_theme_choices as available_graph_theme_choices,
    graph_theme_registry,
    is_custom_graph_theme_id,
    is_known_graph_theme_id,
    normalize_custom_graph_theme_definition,
)

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class AppPreferencesController:
    def __init__(
        self,
        *,
        store: AppPreferencesStore | None = None,
        preloaded_document: Any | None = None,
    ) -> None:
        self._store = store or AppPreferencesStore(path_provider=app_preferences_path)
        self._document: dict[str, Any] | None = (
            normalize_app_preferences_document(preloaded_document)
            if preloaded_document is not None
            else None
        )

    def load(self, *, reload_from_store: bool = False) -> dict[str, Any]:
        if reload_from_store or self._document is None:
            self._document = self._store.load_document()
        return copy.deepcopy(self._document)

    def load_into_host(self, host: ShellWindow, *, reload_from_store: bool = False) -> dict[str, Any]:
        self.load(reload_from_store=reload_from_store)
        return self.apply_graphics_settings_to_host(host)

    def document(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document())

    def graphics_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document()["graphics"])

    def graph_theme_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self.graphics_settings()["graph_theme"])

    def source_import_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document()["source_import"])

    def source_import_mode(self) -> str:
        settings = self.source_import_settings()
        return normalize_source_import_mode(settings.get("default_mode"))

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

    def set_source_import_mode(self, mode: Any) -> str:
        document = self._ensure_document()
        document["source_import"] = normalize_source_import_settings({"default_mode": mode})
        self.persist()
        return self.source_import_mode()

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
    "normalize_expand_collision_avoidance_settings",
    "normalize_graph_theme_settings",
    "normalize_graphics_settings",
    "normalize_source_import_mode",
    "normalize_source_import_settings",
]
