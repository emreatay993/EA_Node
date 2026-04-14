from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.graph_theme_defaults import DEFAULT_GRAPH_THEME_ID
from ea_node_editor.persistence.utils import write_json_atomic
from ea_node_editor.settings import (
    APP_PREFERENCES_KIND,
    APP_PREFERENCES_VERSION,
    DEFAULT_APP_PREFERENCES,
    DEFAULT_EDGE_CROSSING_STYLE,
    DEFAULT_EXPAND_COLLISION_AVOIDANCE_GAP_PRESET,
    DEFAULT_EXPAND_COLLISION_AVOIDANCE_LOCAL_RADIUS_PRESET,
    DEFAULT_EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE,
    DEFAULT_EXPAND_COLLISION_AVOIDANCE_SCOPE,
    DEFAULT_EXPAND_COLLISION_AVOIDANCE_STRATEGY,
    DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    DEFAULT_GRAPHICS_PERFORMANCE_MODE,
    DEFAULT_GRID_OVERLAY_STYLE,
    DEFAULT_GRAPHICS_SETTINGS,
    DEFAULT_SOURCE_IMPORT_MODE,
    DEFAULT_SOURCE_IMPORT_SETTINGS,
    EDGE_CROSSING_STYLE_CHOICES,
    EXPAND_COLLISION_AVOIDANCE_GAP_PRESET_CHOICES,
    EXPAND_COLLISION_AVOIDANCE_LOCAL_RADIUS_PRESET_CHOICES,
    EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE_CHOICES,
    EXPAND_COLLISION_AVOIDANCE_SCOPE_CHOICES,
    EXPAND_COLLISION_AVOIDANCE_STRATEGY_CHOICES,
    GRAPH_LABEL_PIXEL_SIZE_MAX,
    GRAPH_LABEL_PIXEL_SIZE_MIN,
    GRAPH_NODE_ICON_PIXEL_SIZE_MAX,
    GRAPHICS_PERFORMANCE_MODE_CHOICES,
    GRID_OVERLAY_STYLE_CHOICES,
    SOURCE_IMPORT_MODE_CHOICES,
    TAB_STRIP_DENSITY_CHOICES,
    app_preferences_path,
)
from ea_node_editor.ui.graph_theme import (
    is_known_graph_theme_id,
    resolve_graph_theme_id,
    serialize_custom_graph_themes,
)
from ea_node_editor.ui.theme import DEFAULT_THEME_ID, is_known_theme_id, resolve_theme_id


_APP_PREFERENCES_MIGRATION_VERSION = 1
_GRAPHICS_PERFORMANCE_MODE_VALUES = {
    str(choice[0]).strip().lower() for choice in GRAPHICS_PERFORMANCE_MODE_CHOICES
}
_GRID_OVERLAY_STYLE_VALUES = {
    str(choice[0]).strip().lower() for choice in GRID_OVERLAY_STYLE_CHOICES
}
_EDGE_CROSSING_STYLE_VALUES = {
    str(choice[0]).strip().lower() for choice in EDGE_CROSSING_STYLE_CHOICES
}
_EXPAND_COLLISION_AVOIDANCE_STRATEGY_VALUES = {
    str(choice[0]).strip().lower() for choice in EXPAND_COLLISION_AVOIDANCE_STRATEGY_CHOICES
}
_EXPAND_COLLISION_AVOIDANCE_SCOPE_VALUES = {
    str(choice[0]).strip().lower() for choice in EXPAND_COLLISION_AVOIDANCE_SCOPE_CHOICES
}
_EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE_VALUES = {
    str(choice[0]).strip().lower() for choice in EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE_CHOICES
}
_EXPAND_COLLISION_AVOIDANCE_LOCAL_RADIUS_PRESET_VALUES = {
    str(choice[0]).strip().lower() for choice in EXPAND_COLLISION_AVOIDANCE_LOCAL_RADIUS_PRESET_CHOICES
}
_EXPAND_COLLISION_AVOIDANCE_GAP_PRESET_VALUES = {
    str(choice[0]).strip().lower() for choice in EXPAND_COLLISION_AVOIDANCE_GAP_PRESET_CHOICES
}
_SOURCE_IMPORT_MODE_VALUES = {
    str(choice[0]).strip().lower() for choice in SOURCE_IMPORT_MODE_CHOICES
}
_TAB_STRIP_DENSITY_VALUES = {str(choice[0]).strip().lower() for choice in TAB_STRIP_DENSITY_CHOICES}


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


def normalize_expand_collision_avoidance_settings(payload: Any) -> dict[str, Any]:
    defaults = DEFAULT_GRAPHICS_SETTINGS["interaction"]["expand_collision_avoidance"]
    if not isinstance(payload, Mapping):
        return copy.deepcopy(defaults)

    normalized = copy.deepcopy(defaults)
    normalized["enabled"] = _normalize_bool(payload.get("enabled"), defaults["enabled"])
    normalized["strategy"] = _normalize_choice(
        payload.get("strategy"),
        defaults["strategy"],
        _EXPAND_COLLISION_AVOIDANCE_STRATEGY_VALUES,
        DEFAULT_EXPAND_COLLISION_AVOIDANCE_STRATEGY,
    )
    normalized["scope"] = _normalize_choice(
        payload.get("scope"),
        defaults["scope"],
        _EXPAND_COLLISION_AVOIDANCE_SCOPE_VALUES,
        DEFAULT_EXPAND_COLLISION_AVOIDANCE_SCOPE,
    )
    normalized["radius_mode"] = _normalize_choice(
        payload.get("radius_mode"),
        defaults["radius_mode"],
        _EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE_VALUES,
        DEFAULT_EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE,
    )
    normalized["local_radius_preset"] = _normalize_choice(
        payload.get("local_radius_preset"),
        defaults["local_radius_preset"],
        _EXPAND_COLLISION_AVOIDANCE_LOCAL_RADIUS_PRESET_VALUES,
        DEFAULT_EXPAND_COLLISION_AVOIDANCE_LOCAL_RADIUS_PRESET,
    )
    normalized["gap_preset"] = _normalize_choice(
        payload.get("gap_preset"),
        defaults["gap_preset"],
        _EXPAND_COLLISION_AVOIDANCE_GAP_PRESET_VALUES,
        DEFAULT_EXPAND_COLLISION_AVOIDANCE_GAP_PRESET,
    )
    normalized["animate"] = _normalize_bool(payload.get("animate"), defaults["animate"])
    return normalized


def normalize_graphics_settings(payload: Any) -> dict[str, Any]:
    defaults = DEFAULT_GRAPHICS_SETTINGS
    if not isinstance(payload, Mapping):
        return copy.deepcopy(defaults)

    canvas_payload = payload.get("canvas")
    interaction_payload = payload.get("interaction")
    performance_payload = payload.get("performance")
    shell_payload = payload.get("shell")
    theme_payload = payload.get("theme")
    typography_payload = payload.get("typography")
    graph_theme_payload = payload.get("graph_theme")

    normalized = copy.deepcopy(defaults)
    if isinstance(canvas_payload, Mapping):
        normalized["canvas"]["show_grid"] = _normalize_bool(
            canvas_payload.get("show_grid"),
            defaults["canvas"]["show_grid"],
        )
        normalized["canvas"]["grid_style"] = normalize_grid_overlay_style(
            canvas_payload.get("grid_style"),
            defaults["canvas"]["grid_style"],
        )
        normalized["canvas"]["edge_crossing_style"] = normalize_edge_crossing_style(
            canvas_payload.get("edge_crossing_style"),
            defaults["canvas"]["edge_crossing_style"],
        )
        normalized["canvas"]["show_minimap"] = _normalize_bool(
            canvas_payload.get("show_minimap"),
            defaults["canvas"]["show_minimap"],
        )
        normalized["canvas"]["show_port_labels"] = _normalize_bool(
            canvas_payload.get("show_port_labels"),
            defaults["canvas"]["show_port_labels"],
        )
        normalized["canvas"]["minimap_expanded"] = _normalize_bool(
            canvas_payload.get("minimap_expanded"),
            defaults["canvas"]["minimap_expanded"],
        )
        normalized["canvas"]["node_shadow"] = _normalize_bool(
            canvas_payload.get("node_shadow"),
            defaults["canvas"]["node_shadow"],
        )
        normalized["canvas"]["shadow_strength"] = _normalize_int(
            canvas_payload.get("shadow_strength"),
            defaults["canvas"]["shadow_strength"],
            0,
            100,
        )
        normalized["canvas"]["shadow_softness"] = _normalize_int(
            canvas_payload.get("shadow_softness"),
            defaults["canvas"]["shadow_softness"],
            0,
            100,
        )
        normalized["canvas"]["shadow_offset"] = _normalize_int(
            canvas_payload.get("shadow_offset"),
            defaults["canvas"]["shadow_offset"],
            0,
            20,
        )
    if isinstance(interaction_payload, Mapping):
        normalized["interaction"]["snap_to_grid"] = _normalize_bool(
            interaction_payload.get("snap_to_grid"),
            defaults["interaction"]["snap_to_grid"],
        )
        normalized["interaction"]["expand_collision_avoidance"] = (
            normalize_expand_collision_avoidance_settings(
                interaction_payload.get("expand_collision_avoidance")
            )
        )
    if isinstance(performance_payload, Mapping):
        normalized["performance"]["mode"] = normalize_graphics_performance_mode(
            performance_payload.get("mode"),
            defaults["performance"]["mode"],
        )
    if isinstance(shell_payload, Mapping):
        normalized["shell"]["tab_strip_density"] = _normalize_tab_strip_density(
            shell_payload.get("tab_strip_density"),
            defaults["shell"]["tab_strip_density"],
        )
        normalized["shell"]["show_tooltips"] = _normalize_bool(
            shell_payload.get("show_tooltips"),
            defaults["shell"]["show_tooltips"],
        )
    if isinstance(theme_payload, Mapping):
        normalized["theme"]["theme_id"] = _normalize_theme_id(
            theme_payload.get("theme_id"),
            defaults["theme"]["theme_id"],
        )
    if isinstance(typography_payload, Mapping):
        graph_label_pixel_size = normalize_graph_label_pixel_size(
            typography_payload.get("graph_label_pixel_size"),
            defaults["typography"]["graph_label_pixel_size"],
        )
        graph_node_icon_pixel_size_override = normalize_graph_node_icon_pixel_size_override(
            typography_payload.get("graph_node_icon_pixel_size_override")
        )
        normalized["typography"]["graph_label_pixel_size"] = graph_label_pixel_size
        normalized["typography"]["graph_node_icon_pixel_size_override"] = graph_node_icon_pixel_size_override
    normalized["graph_theme"] = normalize_graph_theme_settings(graph_theme_payload)
    return normalized


def normalize_source_import_settings(payload: Any) -> dict[str, Any]:
    defaults = DEFAULT_SOURCE_IMPORT_SETTINGS
    if not isinstance(payload, Mapping):
        return copy.deepcopy(defaults)

    normalized = copy.deepcopy(defaults)
    normalized["default_mode"] = normalize_source_import_mode(
        payload.get("default_mode"),
        defaults["default_mode"],
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

    if kind != APP_PREFERENCES_KIND:
        return normalized
    if version not in {_APP_PREFERENCES_MIGRATION_VERSION, APP_PREFERENCES_VERSION}:
        return normalized

    normalized["graphics"] = normalize_graphics_settings(payload.get("graphics"))
    normalized["source_import"] = normalize_source_import_settings(payload.get("source_import"))
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


def resolve_startup_theme_id(
    *,
    store: AppPreferencesStore | None = None,
    graphics: Any | None = None,
) -> str:
    try:
        resolved_graphics = normalize_graphics_settings(graphics)
        if graphics is None:
            document = (store or AppPreferencesStore()).load_document()
            resolved_graphics = normalize_graphics_settings(document.get("graphics"))
    except Exception:  # noqa: BLE001
        return DEFAULT_THEME_ID

    theme = resolved_graphics.get("theme", {})
    if not isinstance(theme, Mapping):
        return DEFAULT_THEME_ID
    return resolve_theme_id(theme.get("theme_id", DEFAULT_THEME_ID))


def _normalize_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _normalize_int(value: Any, default: int, lo: int, hi: int) -> int:
    if isinstance(value, int) and lo <= value <= hi:
        return value
    return default


def normalize_graph_label_pixel_size(
    value: Any,
    default: int = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(GRAPH_LABEL_PIXEL_SIZE_MIN, min(value, GRAPH_LABEL_PIXEL_SIZE_MAX))
    return default


def normalize_graph_node_icon_pixel_size_override(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return max(GRAPH_LABEL_PIXEL_SIZE_MIN, min(value, GRAPH_NODE_ICON_PIXEL_SIZE_MAX))
    return None


def effective_graph_node_icon_pixel_size(
    graph_label_pixel_size: Any,
    graph_node_icon_pixel_size_override: Any,
) -> int:
    normalized_override = normalize_graph_node_icon_pixel_size_override(
        graph_node_icon_pixel_size_override
    )
    if normalized_override is not None:
        return normalized_override
    return normalize_graph_label_pixel_size(graph_label_pixel_size)


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


def _normalize_tab_strip_density(value: Any, default: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in _TAB_STRIP_DENSITY_VALUES:
        return normalized
    resolved_default = str(default).strip().lower()
    if resolved_default in _TAB_STRIP_DENSITY_VALUES:
        return resolved_default
    return str(DEFAULT_GRAPHICS_SETTINGS["shell"]["tab_strip_density"])


def _normalize_choice(value: Any, default: str, choices: set[str], fallback: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in choices:
        return normalized
    resolved_default = str(default).strip().lower()
    if resolved_default in choices:
        return resolved_default
    return fallback


def normalize_graphics_performance_mode(value: Any, default: str = DEFAULT_GRAPHICS_PERFORMANCE_MODE) -> str:
    normalized = str(value).strip().lower()
    if normalized in _GRAPHICS_PERFORMANCE_MODE_VALUES:
        return normalized
    resolved_default = str(default).strip().lower()
    if resolved_default in _GRAPHICS_PERFORMANCE_MODE_VALUES:
        return resolved_default
    return DEFAULT_GRAPHICS_PERFORMANCE_MODE


def normalize_grid_overlay_style(value: Any, default: str = DEFAULT_GRID_OVERLAY_STYLE) -> str:
    normalized = str(value).strip().lower()
    if normalized in _GRID_OVERLAY_STYLE_VALUES:
        return normalized
    resolved_default = str(default).strip().lower()
    if resolved_default in _GRID_OVERLAY_STYLE_VALUES:
        return resolved_default
    return DEFAULT_GRID_OVERLAY_STYLE


def normalize_edge_crossing_style(value: Any, default: str = DEFAULT_EDGE_CROSSING_STYLE) -> str:
    normalized = str(value).strip().lower()
    if normalized in _EDGE_CROSSING_STYLE_VALUES:
        return normalized
    resolved_default = str(default).strip().lower()
    if resolved_default in _EDGE_CROSSING_STYLE_VALUES:
        return resolved_default
    return DEFAULT_EDGE_CROSSING_STYLE


def normalize_source_import_mode(value: Any, default: str = DEFAULT_SOURCE_IMPORT_MODE) -> str:
    normalized = str(value).strip().lower()
    if normalized in _SOURCE_IMPORT_MODE_VALUES:
        return normalized
    resolved_default = str(default).strip().lower()
    if resolved_default in _SOURCE_IMPORT_MODE_VALUES:
        return resolved_default
    return DEFAULT_SOURCE_IMPORT_MODE


__all__ = [
    "AppPreferencesStore",
    "default_app_preferences_document",
    "normalize_app_preferences_document",
    "normalize_edge_crossing_style",
    "normalize_expand_collision_avoidance_settings",
    "normalize_graph_label_pixel_size",
    "effective_graph_node_icon_pixel_size",
    "normalize_graph_node_icon_pixel_size_override",
    "normalize_graph_theme_settings",
    "normalize_grid_overlay_style",
    "normalize_graphics_performance_mode",
    "normalize_graphics_settings",
    "normalize_source_import_mode",
    "normalize_source_import_settings",
    "resolve_startup_theme_id",
]
