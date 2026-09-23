# Purpose: Prove the COREX_SESSION_STATE_DIR seam scopes autosave / last-session / staging per spawned instance
#          while app-wide preferences stay in the user data dir.
# Map: feature_routes/automation_api_mcp
# Tests: tests/test_settings_session_state_dir.py
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from ea_node_editor import settings
from ea_node_editor.persistence.session_store import SessionAutosaveStore

_ENV = settings.SESSION_STATE_DIR_ENV_VAR


def _environment(tmp_path: Path, override: str | None) -> dict[str, str]:
    values = {"APPDATA": str(tmp_path / "appdata")}
    if override is not None:
        values[_ENV] = override
    return values


def test_override_is_honoured_created_and_scopes_session_paths(tmp_path: Path) -> None:
    override = tmp_path / "spawned" / "instance-1"
    assert not override.exists()

    with patch.dict(os.environ, _environment(tmp_path, str(override)), clear=False):
        assert settings.session_state_dir() == override
        assert override.is_dir()
        assert settings.recent_session_path() == override / "last_session.json"
        assert (
            settings.autosave_project_path()
            == override / f"autosave{settings.PROJECT_EXTENSION}"
        )
        # The default staging root derives from the session path, so it is isolated too.
        assert (
            SessionAutosaveStore(serializer=object()).staging_workspace_root()
            == override / settings.PROJECT_ARTIFACT_SESSION_STAGING_DIRNAME
        )
        # App-wide state stays on the user data dir.
        user_dir = settings.user_data_dir()
        assert user_dir != override
        assert settings.app_preferences_path() == user_dir / "app_preferences.json"
        assert settings.plugins_dir().parent == user_dir
        assert settings.plugin_generations_dir().parent.parent == user_dir


def test_blank_override_is_ignored(tmp_path: Path) -> None:
    with patch.dict(os.environ, _environment(tmp_path, "   "), clear=False):
        user_dir = settings.user_data_dir()
        assert settings.session_state_dir() == user_dir
        assert settings.recent_session_path() == user_dir / "last_session.json"
        assert (
            settings.autosave_project_path()
            == user_dir / f"autosave{settings.PROJECT_EXTENSION}"
        )


def test_unset_override_falls_back_to_user_data_dir(tmp_path: Path) -> None:
    with patch.dict(os.environ, _environment(tmp_path, None), clear=False):
        os.environ.pop(_ENV, None)
        user_dir = settings.user_data_dir()
        assert settings.session_state_dir() == user_dir
        assert settings.recent_session_path().parent == user_dir
        assert settings.autosave_project_path().parent == user_dir
        assert settings.app_preferences_path().parent == user_dir
