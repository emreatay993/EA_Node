from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ea_node_editor.settings import user_data_dir

from .codec import normalize_custom_workflow_metadata

_GLOBAL_CUSTOM_WORKFLOW_STORE_KIND = "ea-node-editor/custom-workflow-library"
_GLOBAL_CUSTOM_WORKFLOW_STORE_VERSION = 1
_GLOBAL_CUSTOM_WORKFLOW_STORE_FILENAME = "custom_workflows_global.json"


def global_custom_workflows_path() -> Path:
    return user_data_dir() / _GLOBAL_CUSTOM_WORKFLOW_STORE_FILENAME


def load_global_custom_workflow_definitions() -> list[dict[str, Any]]:
    path = global_custom_workflows_path()
    if not path.exists():
        return []
    try:
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if isinstance(raw_payload, dict):
        try:
            version = int(raw_payload.get("version", 0) or 0)
        except (TypeError, ValueError):
            return []
        if (
            str(raw_payload.get("kind", "")).strip() != _GLOBAL_CUSTOM_WORKFLOW_STORE_KIND
            or version != _GLOBAL_CUSTOM_WORKFLOW_STORE_VERSION
        ):
            return []
        definitions_payload = raw_payload.get("custom_workflows", [])
    else:
        definitions_payload = raw_payload
    return normalize_custom_workflow_metadata(definitions_payload)


def save_global_custom_workflow_definitions(definitions: Any) -> list[dict[str, Any]]:
    normalized = normalize_custom_workflow_metadata(definitions)
    path = global_custom_workflows_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "kind": _GLOBAL_CUSTOM_WORKFLOW_STORE_KIND,
        "version": _GLOBAL_CUSTOM_WORKFLOW_STORE_VERSION,
        "custom_workflows": normalized,
    }
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return normalized
