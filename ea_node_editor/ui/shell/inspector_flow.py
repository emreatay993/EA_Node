from __future__ import annotations

import json
from typing import Any


def coerce_editor_input_value(prop_type: str, value: Any, default: Any) -> Any:
    if prop_type == "bool":
        return bool(value)
    if prop_type == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    if prop_type == "float":
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    if prop_type == "json":
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return default
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return default
        return value
    return str(value)
