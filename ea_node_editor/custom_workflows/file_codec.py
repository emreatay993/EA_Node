from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .codec import normalize_custom_workflow_metadata

CUSTOM_WORKFLOW_FILE_EXTENSION = ".eawf"
CUSTOM_WORKFLOW_FILE_KIND = "ea-node-editor/custom-workflow"
CUSTOM_WORKFLOW_FILE_VERSION = 1


def normalize_custom_workflow_definition(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    normalized_definitions = normalize_custom_workflow_metadata([value])
    if len(normalized_definitions) != 1:
        return None
    return normalized_definitions[0]


def to_custom_workflow_file_document(definition: Any) -> dict[str, Any]:
    normalized_definition = normalize_custom_workflow_definition(definition)
    if normalized_definition is None:
        raise ValueError("Custom workflow definition is invalid.")
    return {
        "kind": CUSTOM_WORKFLOW_FILE_KIND,
        "version": CUSTOM_WORKFLOW_FILE_VERSION,
        "workflow": normalized_definition,
    }


def from_custom_workflow_file_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ValueError("Custom workflow file must contain a JSON object.")
    if str(document.get("kind", "")).strip() != CUSTOM_WORKFLOW_FILE_KIND:
        raise ValueError("Custom workflow file kind is invalid.")

    try:
        version = int(document.get("version"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Custom workflow file version is invalid.") from exc
    if version != CUSTOM_WORKFLOW_FILE_VERSION:
        raise ValueError(
            f"Unsupported custom workflow file version '{version}'. "
            f"Expected version {CUSTOM_WORKFLOW_FILE_VERSION}."
        )

    normalized_definition = normalize_custom_workflow_definition(document.get("workflow"))
    if normalized_definition is None:
        raise ValueError("Custom workflow file payload is invalid.")
    return normalized_definition


def export_custom_workflow_file(definition: Any, output_path: Path) -> Path:
    output_path = Path(output_path).with_suffix(CUSTOM_WORKFLOW_FILE_EXTENSION)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = to_custom_workflow_file_document(definition)
    output_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def import_custom_workflow_file(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return from_custom_workflow_file_document(payload)
