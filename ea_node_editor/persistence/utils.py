from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def merge_defaults(values: Any, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(defaults)
    if not isinstance(values, Mapping):
        return merged
    for key, value in values.items():
        normalized_key = str(key)
        if (
            normalized_key in merged
            and isinstance(merged[normalized_key], dict)
            and isinstance(value, Mapping)
        ):
            merged[normalized_key] = merge_defaults(dict(value), merged[normalized_key])
        else:
            merged[normalized_key] = copy.deepcopy(value)
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
