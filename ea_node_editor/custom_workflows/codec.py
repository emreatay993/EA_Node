from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

@dataclass(slots=True)
class CustomWorkflowDefinition:
    workflow_id: str
    name: str
    description: str = ""
    revision: int = 1
    ports: list[dict[str, Any]] = field(default_factory=list)
    fragment: dict[str, Any] = field(default_factory=dict)


def normalize_custom_workflow_metadata(value: Any) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    raw_items = value if isinstance(value, list) else []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        workflow_id = str(raw_item.get("workflow_id", "")).strip()
        name = str(raw_item.get("name", "")).strip()
        if not workflow_id or not name or workflow_id in seen_ids:
            continue
        seen_ids.add(workflow_id)
        fragment = copy.deepcopy(raw_item.get("fragment", {}))
        if not isinstance(fragment, dict):
            continue
        ports = copy.deepcopy(raw_item.get("ports", []))
        if not isinstance(ports, list):
            ports = []
        definitions.append(
            {
                "workflow_id": workflow_id,
                "name": name,
                "description": str(raw_item.get("description", "")).strip(),
                "revision": _coerce_int(raw_item.get("revision", 1), default=1),
                "ports": _normalize_port_preview_list(ports),
                "fragment": fragment,
            }
        )
    return definitions


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_port_preview_list(items: list[Any]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        label = str(item.get("label", "")).strip() or key
        direction = str(item.get("direction", "")).strip()
        kind = str(item.get("kind", "")).strip()
        data_type = str(item.get("data_type", "")).strip() or "any"
        if not key or direction not in {"in", "out"} or not kind:
            continue
        preview.append(
            {
                "key": key,
                "label": label,
                "direction": direction,
                "kind": kind,
                "data_type": data_type,
            }
        )
    return preview
