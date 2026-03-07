from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


def merge_defaults(values: Any, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(defaults)
    if not isinstance(values, dict):
        return merged
    for key, value in values.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_defaults(value, merged[key])
        else:
            merged[key] = value
    return merged


def coerce_timestamp(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def document_fingerprint(project_doc: dict[str, Any]) -> str:
    return json.dumps(project_doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True),
        encoding="utf-8",
    )
    temp_path.replace(path)
