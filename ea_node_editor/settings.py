from __future__ import annotations

import os
from pathlib import Path

from ea_node_editor.graph_theme_defaults import DEFAULT_GRAPH_THEME_ID

APP_NAME = "COREX Node Editor"
APP_ID = "com.corex.node_editor"
APP_DATA_DIR_NAME = "COREX_Node_Editor"
LEGACY_APP_DATA_DIR_NAME = "EA_Node_Editor"
PROJECT_EXTENSION = ".sfe"
PROJECT_DATA_DIR_SUFFIX = ".data"
PROJECT_ARTIFACT_STORE_METADATA_KEY = "artifact_store"
PROJECT_MANAGED_ASSETS_DIRNAME = "assets"
PROJECT_MANAGED_ARTIFACTS_DIRNAME = "artifacts"
PROJECT_ARTIFACT_STAGING_DIRNAME = ".staging"
PROJECT_ARTIFACT_RECOVERY_DIRNAME = "recovery"
PROJECT_ARTIFACT_SESSION_STAGING_DIRNAME = "project_artifact_staging"
SCHEMA_VERSION = 4
AUTOSAVE_INTERVAL_MS = 30_000
APP_PREFERENCES_KIND = "ea-node-editor/app-preferences"
APP_PREFERENCES_VERSION = 3

DEFAULT_WORKFLOW_SETTINGS = {
    "general": {
        "project_name": "",
        "author": "",
        "description": "",
    },
    "solver_config": {
        "enable_parallel": True,
        "thread_count": 8,
        "memory_limit_gb": 12,
    },
    "environment": {
        "python_path": "",
        "working_directory": "",
    },
    "plugins": {
        "enabled": [],
    },
    "logging": {
        "level": "info",
        "capture_console": True,
    },
}

DEFAULT_UI_STATE = {
    "script_editor": {
        "visible": False,
        "floating": False,
    },
    "passive_style_presets": {
        "node_presets": [],
        "edge_presets": [],
    },
}

TAB_STRIP_DENSITY_CHOICES = (
    ("compact", "Compact"),
    ("regular", "Regular"),
)

PROPERTY_PANE_VARIANT_CHOICES = (
    ("smart_groups", "Smart Groups"),
    ("accordion_cards", "Accordion Cards"),
    ("palette", "Palette"),
)
DEFAULT_PROPERTY_PANE_VARIANT = "smart_groups"

GRAPHICS_PERFORMANCE_MODE_CHOICES = (
    ("full_fidelity", "Full Fidelity"),
    ("max_performance", "Max Performance"),
)
GRID_OVERLAY_STYLE_CHOICES = (
    ("lines", "Lines"),
    ("points", "Points"),
)
FLOATING_TOOLBAR_STYLE_CHOICES = (
    ("compact_pill", "Compact pill"),
    ("segmented_bar", "Segmented bar"),
    ("minimal_ghost", "Minimal ghost"),
)
FLOATING_TOOLBAR_SIZE_CHOICES = (
    ("small", "Small"),
    ("medium", "Medium"),
    ("large", "Large"),
)
EDGE_CROSSING_STYLE_CHOICES = (
    ("none", "None"),
    ("gap_break", "Gap break"),
)
EXPAND_COLLISION_AVOIDANCE_STRATEGY_CHOICES = (
    ("nearest", "Nearest"),
)
EXPAND_COLLISION_AVOIDANCE_SCOPE_CHOICES = (
    ("all_movable", "All movable items"),
)
EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE_CHOICES = (
    ("local", "Local"),
    ("unbounded", "Unbounded"),
)
EXPAND_COLLISION_AVOIDANCE_LOCAL_RADIUS_PRESET_CHOICES = (
    ("small", "Small"),
    ("medium", "Medium"),
    ("large", "Large"),
)
EXPAND_COLLISION_AVOIDANCE_GAP_PRESET_CHOICES = (
    ("tight", "Tight"),
    ("normal", "Normal"),
    ("loose", "Loose"),
)
SOURCE_IMPORT_MODE_CHOICES = (
    ("managed_copy", "Managed Copy"),
    ("external_link", "External Link"),
)

DEFAULT_GRAPHICS_PERFORMANCE_MODE = GRAPHICS_PERFORMANCE_MODE_CHOICES[0][0]
DEFAULT_GRID_OVERLAY_STYLE = GRID_OVERLAY_STYLE_CHOICES[0][0]
DEFAULT_FLOATING_TOOLBAR_STYLE = FLOATING_TOOLBAR_STYLE_CHOICES[0][0]
DEFAULT_FLOATING_TOOLBAR_SIZE = FLOATING_TOOLBAR_SIZE_CHOICES[0][0]
DEFAULT_EDGE_CROSSING_STYLE = EDGE_CROSSING_STYLE_CHOICES[0][0]
DEFAULT_EXPAND_COLLISION_AVOIDANCE_STRATEGY = EXPAND_COLLISION_AVOIDANCE_STRATEGY_CHOICES[0][0]
DEFAULT_EXPAND_COLLISION_AVOIDANCE_SCOPE = EXPAND_COLLISION_AVOIDANCE_SCOPE_CHOICES[0][0]
DEFAULT_EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE = EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE_CHOICES[0][0]
DEFAULT_EXPAND_COLLISION_AVOIDANCE_LOCAL_RADIUS_PRESET = "medium"
DEFAULT_EXPAND_COLLISION_AVOIDANCE_GAP_PRESET = "normal"
DEFAULT_SOURCE_IMPORT_MODE = SOURCE_IMPORT_MODE_CHOICES[0][0]
GRAPH_LABEL_PIXEL_SIZE_MIN = 8
GRAPH_LABEL_PIXEL_SIZE_MAX = 18
GRAPH_NODE_ICON_PIXEL_SIZE_MAX = 50
DEFAULT_GRAPH_LABEL_PIXEL_SIZE = 10

DEFAULT_EXPAND_COLLISION_AVOIDANCE_SETTINGS = {
    "enabled": True,
    "strategy": DEFAULT_EXPAND_COLLISION_AVOIDANCE_STRATEGY,
    "scope": DEFAULT_EXPAND_COLLISION_AVOIDANCE_SCOPE,
    "radius_mode": DEFAULT_EXPAND_COLLISION_AVOIDANCE_RADIUS_MODE,
    "local_radius_preset": DEFAULT_EXPAND_COLLISION_AVOIDANCE_LOCAL_RADIUS_PRESET,
    "gap_preset": DEFAULT_EXPAND_COLLISION_AVOIDANCE_GAP_PRESET,
    "animate": True,
}

DEFAULT_GRAPHICS_SETTINGS = {
    "canvas": {
        "show_grid": True,
        "grid_style": DEFAULT_GRID_OVERLAY_STYLE,
        "edge_crossing_style": DEFAULT_EDGE_CROSSING_STYLE,
        "show_minimap": True,
        "show_port_labels": True,
        "minimap_expanded": True,
        "node_shadow": True,
        "shadow_strength": 70,
        "shadow_softness": 50,
        "shadow_offset": 4,
        "floating_toolbar_style": DEFAULT_FLOATING_TOOLBAR_STYLE,
        "floating_toolbar_size": DEFAULT_FLOATING_TOOLBAR_SIZE,
    },
    "interaction": {
        "snap_to_grid": False,
        "expand_collision_avoidance": DEFAULT_EXPAND_COLLISION_AVOIDANCE_SETTINGS,
    },
    "performance": {
        "mode": DEFAULT_GRAPHICS_PERFORMANCE_MODE,
    },
    "shell": {
        "tab_strip_density": "compact",
        "property_pane_variant": DEFAULT_PROPERTY_PANE_VARIANT,
        "show_tooltips": True,
    },
    "theme": {
        "theme_id": "stitch_dark",
    },
    "typography": {
        "graph_label_pixel_size": DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
        "graph_node_icon_pixel_size_override": None,
    },
    "graph_theme": {
        "follow_shell_theme": True,
        "selected_theme_id": DEFAULT_GRAPH_THEME_ID,
        "custom_themes": [],
    },
}

DEFAULT_SOURCE_IMPORT_SETTINGS = {
    "default_mode": DEFAULT_SOURCE_IMPORT_MODE,
}

DEFAULT_ANSYS_DPF_PLUGIN_SETTINGS = {
    "version": "",
    "catalog_cache_version": "",
}

DEFAULT_ADDON_STATE = {
    "enabled": True,
    "pending_restart": False,
}

DEFAULT_ADDON_SETTINGS = {
    "states": {},
}

DEFAULT_PLUGIN_SETTINGS = {
    "ansys_dpf": DEFAULT_ANSYS_DPF_PLUGIN_SETTINGS,
}

DEFAULT_APP_PREFERENCES = {
    "kind": APP_PREFERENCES_KIND,
    "version": APP_PREFERENCES_VERSION,
    "graphics": DEFAULT_GRAPHICS_SETTINGS,
    "addons": DEFAULT_ADDON_SETTINGS,
    "plugins": DEFAULT_PLUGIN_SETTINGS,
    "source_import": DEFAULT_SOURCE_IMPORT_SETTINGS,
}


def user_data_dir() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        base_dir = Path(app_data)
    else:
        base_dir = Path.home() / ".config"
    preferred_dir = base_dir / APP_DATA_DIR_NAME
    legacy_dir = base_dir / LEGACY_APP_DATA_DIR_NAME
    data_dir = preferred_dir if preferred_dir.exists() or not legacy_dir.exists() else legacy_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def recent_session_path() -> Path:
    return user_data_dir() / "last_session.json"


def app_preferences_path() -> Path:
    return user_data_dir() / "app_preferences.json"


def autosave_project_path() -> Path:
    return user_data_dir() / f"autosave{PROJECT_EXTENSION}"


def plugins_dir() -> Path:
    plugin_path = user_data_dir() / "plugins"
    plugin_path.mkdir(parents=True, exist_ok=True)
    return plugin_path
