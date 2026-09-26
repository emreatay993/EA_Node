from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    default_app_preferences_document,
    normalize_app_preferences_document,
    normalize_expand_collision_avoidance_settings,
    normalize_graphics_settings,
    normalize_node_library_usage,
    normalize_passive_node_library_display_mode,
    normalize_plot_default_backend_per_type,
    normalize_plot_settings,
    normalize_python_runtime_settings,
    normalize_source_import_mode,
    normalize_source_import_settings,
    normalize_selected_run_settings,
    normalize_solution_settings,
    normalize_tooltip_delay_ms,
)
from ea_node_editor.common.payload_tools import merge_defaults
from ea_node_editor.settings import app_preferences_path
from ea_node_editor.text_style import record_recent_text_color
from ea_node_editor.ui.shell.tooltip_policy import (
    is_configurable_tooltip_category,
    normalize_tooltip_category_name,
    normalize_tooltip_category_preferences,
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

    def store(self) -> AppPreferencesStore:
        return self._store

    def replace_document(self, document: Any) -> dict[str, Any]:
        self._document = normalize_app_preferences_document(document)
        return copy.deepcopy(self._document)

    def persist_document(self, document: Any) -> dict[str, Any]:
        normalized = normalize_app_preferences_document(document)
        persisted = self._store.persist_document(normalized)
        self._document = normalize_app_preferences_document(persisted)
        return copy.deepcopy(self._document)

    def graphics_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document()["graphics"])

    def plot_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self.graphics_settings()["plot"])

    def plot_default_backend_per_type(self) -> dict[str, str]:
        return copy.deepcopy(self.plot_settings()["plot_default_backend_per_type"])

    def source_import_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document()["source_import"])

    def source_import_mode(self) -> str:
        settings = self.source_import_settings()
        return normalize_source_import_mode(settings.get("default_mode"))

    def selected_run_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self._ensure_document()["selected_run"])

    def selected_run_preview_before_run(self) -> bool:
        settings = self.selected_run_settings()
        return bool(normalize_selected_run_settings(settings).get("preview_before_run", True))

    def solution_default_mode(self) -> str:
        settings = normalize_solution_settings(self._ensure_document().get("solution"))
        return settings["default_mode"]

    def python_runtime_settings(self) -> dict[str, str]:
        return normalize_python_runtime_settings(self._ensure_document().get("python_runtime"))

    def default_python_executable(self) -> str:
        return self.python_runtime_settings()["default_executable"]

    def set_default_python_executable(self, value: Any) -> str:
        document = copy.deepcopy(self._ensure_document())
        document["python_runtime"] = normalize_python_runtime_settings(
            {"default_executable": value}
        )
        persisted = self.persist_document(document)
        return persisted["python_runtime"]["default_executable"]

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
        document["graphics"] = normalize_graphics_settings(
            self._preserve_current_tooltip_categories(graphics, document.get("graphics"))
        )
        self.persist()
        resolved = self.graphics_settings()
        if host is not None:
            host.apply_graphics_preferences(resolved)
        return resolved

    def update_graphics_settings(self, updates: Any, *, host: ShellWindow | None = None) -> dict[str, Any]:
        current = self.graphics_settings()
        merged = merge_defaults(updates, current)
        return self.set_graphics_settings(merged, host=host)

    def set_graphics_show_port_labels(self, show_port_labels: bool, *, host: ShellWindow | None = None) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"canvas": {"show_port_labels": bool(show_port_labels)}},
            host=host,
        )

    def set_graphics_tooltip_categories(
        self,
        categories: Any,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"shell": {"tooltip_categories": normalize_tooltip_category_preferences(categories)}},
            host=host,
        )

    def set_graphics_tooltip_category_enabled(
        self,
        category: object,
        enabled: bool,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        normalized_category = normalize_tooltip_category_name(category)
        if not is_configurable_tooltip_category(normalized_category):
            return self.graphics_settings()
        shell = self.graphics_settings().get("shell", {})
        current_categories = normalize_tooltip_category_preferences(
            shell.get("tooltip_categories") if isinstance(shell, Mapping) else None
        )
        current_categories[normalized_category] = bool(enabled)
        return self.set_graphics_tooltip_categories(current_categories, host=host)

    def set_graphics_tooltip_delay_ms(
        self,
        delay_ms: Any,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"shell": {"tooltip_delay_ms": normalize_tooltip_delay_ms(delay_ms)}},
            host=host,
        )

    def set_graphics_floating_toolbar_style(self, style: str, *, host: ShellWindow | None = None) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"canvas": {"floating_toolbar_style": str(style)}},
            host=host,
        )

    def set_graphics_floating_toolbar_size(self, size: str, *, host: ShellWindow | None = None) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"canvas": {"floating_toolbar_size": str(size)}},
            host=host,
        )

    def set_graphics_selection_toolbar_mode(self, mode: str, *, host: ShellWindow | None = None) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"canvas": {"selection_toolbar_mode": str(mode)}},
            host=host,
        )

    def set_graphics_node_comment_editor_default(
        self,
        value: str,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"canvas": {"node_comment_editor_default": str(value)}},
            host=host,
        )

    def set_graphics_selection_toolbar_minimal_menu_trigger(
        self,
        trigger: str,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"canvas": {"selection_toolbar_minimal_menu_trigger": str(trigger)}},
            host=host,
        )

    def set_passive_node_library_display_mode(
        self,
        mode: str,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {
                "shell": {
                    "passive_node_library_display_mode": (
                        normalize_passive_node_library_display_mode(mode)
                    )
                }
            },
            host=host,
        )

    def record_recent_text_color(
        self,
        color: Any,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        typography = self.graphics_settings().get("typography", {})
        current = typography.get("recent_text_colors") if isinstance(typography, Mapping) else []
        recent_colors = record_recent_text_color(current, color)
        return self.update_graphics_settings(
            {"typography": {"recent_text_colors": recent_colors}},
            host=host,
        )

    def node_library_usage(self) -> list[str]:
        shell = self.graphics_settings().get("shell", {})
        value = shell.get("node_library_usage") if isinstance(shell, Mapping) else None
        return normalize_node_library_usage(value)

    def record_node_library_usage(self, type_id: str) -> list[str]:
        normalized_type_id = type_id.strip()
        if not normalized_type_id:
            return self.node_library_usage()
        usage = normalize_node_library_usage([*self.node_library_usage(), normalized_type_id])
        self.update_graphics_settings({"shell": {"node_library_usage": usage}})
        return usage

    def set_graphics_canvas_import_mode(
        self,
        mode: str,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"interaction": {"canvas_import_mode": mode}},
            host=host,
        )

    def set_graphics_smart_guides_enabled(
        self,
        enabled: bool,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {"interaction": {"smart_guides": bool(enabled)}},
            host=host,
        )

    def set_graphics_expand_collision_avoidance(
        self,
        settings: Any,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {
                "interaction": {
                    "expand_collision_avoidance": normalize_expand_collision_avoidance_settings(settings),
                }
            },
            host=host,
        )

    def set_plot_lightweight_canvas(
        self,
        lightweight_canvas: Any,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {
                "plot": {
                    "lightweight_canvas": bool(lightweight_canvas),
                }
            },
            host=host,
        )

    def set_plot_default_backend_per_type(
        self,
        defaults: Any,
        *,
        host: ShellWindow | None = None,
    ) -> dict[str, Any]:
        return self.update_graphics_settings(
            {
                "plot": {
                    "plot_default_backend_per_type": normalize_plot_default_backend_per_type(defaults),
                }
            },
            host=host,
        )

    def set_source_import_mode(self, mode: Any) -> str:
        document = self._ensure_document()
        document["source_import"] = normalize_source_import_settings({"default_mode": mode})
        self.persist()
        return self.source_import_mode()

    def set_solution_default_mode(self, mode: Any) -> str:
        document = self._ensure_document()
        document["solution"] = normalize_solution_settings({"default_mode": mode})
        self.persist()
        return self.solution_default_mode()

    def set_selected_run_preview_before_run(self, enabled: Any) -> bool:
        document = self._ensure_document()
        document["selected_run"] = normalize_selected_run_settings({"preview_before_run": enabled})
        self.persist()
        return self.selected_run_preview_before_run()

    def persist(self) -> dict[str, Any]:
        return self.persist_document(self._ensure_document())

    def _ensure_document(self) -> dict[str, Any]:
        if self._document is None:
            self._document = self._store.load_document()
        return self._document

    def _preserve_current_tooltip_categories(self, graphics: Any, current_graphics: Any) -> Any:
        if not isinstance(graphics, Mapping):
            return graphics
        current_shell = current_graphics.get("shell", {}) if isinstance(current_graphics, Mapping) else {}
        current_categories = normalize_tooltip_category_preferences(
            current_shell.get("tooltip_categories") if isinstance(current_shell, Mapping) else None
        )
        graphics_payload = copy.deepcopy(dict(graphics))
        shell_payload = graphics_payload.get("shell")
        if isinstance(shell_payload, Mapping):
            if "tooltip_categories" in shell_payload:
                return graphics_payload
            shell_copy = copy.deepcopy(dict(shell_payload))
            shell_copy["tooltip_categories"] = current_categories
            graphics_payload["shell"] = shell_copy
            return graphics_payload
        if "shell" not in graphics_payload:
            graphics_payload["shell"] = {"tooltip_categories": current_categories}
        return graphics_payload


__all__ = [
    "AppPreferencesController",
    "AppPreferencesStore",
    "default_app_preferences_document",
    "normalize_app_preferences_document",
    "normalize_expand_collision_avoidance_settings",
    "normalize_graphics_settings",
    "normalize_plot_settings",
    "normalize_source_import_mode",
    "normalize_source_import_settings",
]
