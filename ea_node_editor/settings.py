from __future__ import annotations

import os
from pathlib import Path

from ea_node_editor.ui.graph_theme import DEFAULT_GRAPH_THEME_ID

APP_NAME = "EA Node Editor"
APP_ID = "com.ea.node_editor"
PROJECT_EXTENSION = ".sfe"
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

DEFAULT_GRAPHICS_SETTINGS = {
    "canvas": {
        "show_grid": True,
        "show_minimap": True,
        "minimap_expanded": True,
        "node_shadow": True,
        "shadow_strength": 70,
        "shadow_softness": 50,
        "shadow_offset": 4,
    },
    "interaction": {
        "snap_to_grid": False,
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

DEFAULT_APP_PREFERENCES = {
    "kind": APP_PREFERENCES_KIND,
    "version": APP_PREFERENCES_VERSION,
    "graphics": DEFAULT_GRAPHICS_SETTINGS,
}


def user_data_dir() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        base_dir = Path(app_data)
    else:
        base_dir = Path.home() / ".config"
    data_dir = base_dir / "EA_Node_Editor"
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
