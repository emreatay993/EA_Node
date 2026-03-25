from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from typing import Any, TypeAlias

from ea_node_editor.nodes.types import (
    RuntimeArtifactRef,
    RuntimeHandleRef,
    coerce_runtime_artifact_ref,
    coerce_runtime_handle_ref,
)

RuntimeValueRef: TypeAlias = RuntimeArtifactRef | RuntimeHandleRef

_RUNTIME_VALUE_MARKER_KEY = "__ea_runtime_value__"
_RUNTIME_ARTIFACT_MARKER_VALUE = "artifact_ref"
_RUNTIME_HANDLE_MARKER_VALUE = "handle_ref"


def _extract_runtime_marker(payload: Mapping[str, Any]) -> str | None:
    if _RUNTIME_VALUE_MARKER_KEY not in payload:
        return None
    marker = payload.get(_RUNTIME_VALUE_MARKER_KEY)
    if not isinstance(marker, str):
        raise ValueError("Runtime value marker must be a non-empty string")
    normalized_marker = marker.strip()
    if not normalized_marker:
        raise ValueError("Runtime value marker must be a non-empty string")
    return normalized_marker


def _coerce_runtime_value_ref(payload: Mapping[str, Any]) -> RuntimeValueRef | None:
    marker = _extract_runtime_marker(payload)
    if marker is None:
        return None
    if marker == _RUNTIME_ARTIFACT_MARKER_VALUE:
        runtime_ref = coerce_runtime_artifact_ref(payload)
        if runtime_ref is None:
            raise ValueError("Runtime artifact ref payload is incomplete")
        return runtime_ref
    if marker == _RUNTIME_HANDLE_MARKER_VALUE:
        runtime_ref = coerce_runtime_handle_ref(payload)
        if runtime_ref is None:
            raise ValueError("Runtime handle ref payload is incomplete")
        return runtime_ref
    raise ValueError(f"Unsupported runtime value marker: {marker!r}")


def serialize_runtime_value(value: Any) -> Any:
    if isinstance(value, (RuntimeArtifactRef, RuntimeHandleRef)):
        return value.to_payload()
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field_info.name: serialize_runtime_value(getattr(value, field_info.name))
            for field_info in fields(value)
        }
    if isinstance(value, Mapping):
        payload_ref = _coerce_runtime_value_ref(value)
        if payload_ref is not None:
            return payload_ref.to_payload()
        return {
            str(key): serialize_runtime_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [serialize_runtime_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(serialize_runtime_value(item) for item in value)
    if isinstance(value, set):
        return {serialize_runtime_value(item) for item in value}
    if isinstance(value, frozenset):
        return frozenset(serialize_runtime_value(item) for item in value)
    return copy.deepcopy(value)


def deserialize_runtime_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        payload_ref = _coerce_runtime_value_ref(value)
        if payload_ref is not None:
            return payload_ref
        return {
            str(key): deserialize_runtime_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [deserialize_runtime_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(deserialize_runtime_value(item) for item in value)
    if isinstance(value, set):
        return {deserialize_runtime_value(item) for item in value}
    if isinstance(value, frozenset):
        return frozenset(deserialize_runtime_value(item) for item in value)
    return copy.deepcopy(value)


__all__ = [
    "RuntimeValueRef",
    "deserialize_runtime_value",
    "serialize_runtime_value",
]
