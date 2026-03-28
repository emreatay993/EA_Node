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
APP_PREFERENCES_VERSION = 2

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

GRAPHICS_PERFORMANCE_MODE_CHOICES = (
    ("full_fidelity", "Full Fidelity"),
    ("max_performance", "Max Performance"),
)
GRID_OVERLAY_STYLE_CHOICES = (
    ("lines", "Lines"),
    ("points", "Points"),
)
SOURCE_IMPORT_MODE_CHOICES = (
    ("managed_copy", "Managed Copy"),
    ("external_link", "External Link"),
)

DEFAULT_GRAPHICS_PERFORMANCE_MODE = GRAPHICS_PERFORMANCE_MODE_CHOICES[0][0]
DEFAULT_GRID_OVERLAY_STYLE = GRID_OVERLAY_STYLE_CHOICES[0][0]
DEFAULT_SOURCE_IMPORT_MODE = SOURCE_IMPORT_MODE_CHOICES[0][0]

DEFAULT_GRAPHICS_SETTINGS = {
    "canvas": {
        "show_grid": True,
        "grid_style": DEFAULT_GRID_OVERLAY_STYLE,
        "show_minimap": True,
        "show_port_labels": True,
        "minimap_expanded": True,
        "node_shadow": True,
        "shadow_strength": 70,
        "shadow_softness": 50,
        "shadow_offset": 4,
    },
    "interaction": {
        "snap_to_grid": False,
    },
    "performance": {
        "mode": DEFAULT_GRAPHICS_PERFORMANCE_MODE,
    },
    "shell": {
        "tab_strip_density": "compact",
    },
    "theme": {
        "theme_id": "stitch_dark",
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

DEFAULT_APP_PREFERENCES = {
    "kind": APP_PREFERENCES_KIND,
    "version": APP_PREFERENCES_VERSION,
    "graphics": DEFAULT_GRAPHICS_SETTINGS,
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
