"""Compatibility exports for the runtime value contract codec.

Runtime value DTOs and wire serialization are owned by
``ea_node_editor.runtime_contracts``. Execution modules may keep importing this
path for compatibility, but no execution behavior lives here.
"""

from __future__ import annotations

from ea_node_editor.runtime_contracts import (
    RuntimeValueRef,
    deserialize_runtime_value,
    serialize_runtime_value,
)


__all__ = [
    "RuntimeValueRef",
    "deserialize_runtime_value",
    "serialize_runtime_value",
]
