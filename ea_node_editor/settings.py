from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "EA Node Editor"
APP_ID = "com.ea.node_editor"
PROJECT_EXTENSION = ".sfe"
SCHEMA_VERSION = 2
AUTOSAVE_INTERVAL_MS = 30_000

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


def autosave_project_path() -> Path:
    return user_data_dir() / f"autosave{PROJECT_EXTENSION}"


def plugins_dir() -> Path:
    plugin_path = user_data_dir() / "plugins"
    plugin_path.mkdir(parents=True, exist_ok=True)
    return plugin_path
