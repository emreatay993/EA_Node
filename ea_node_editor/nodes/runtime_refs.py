from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from ea_node_editor.persistence.artifact_refs import (
    ManagedArtifactRef,
    StagedArtifactRef,
    format_managed_artifact_ref,
    format_staged_artifact_ref,
    parse_artifact_ref,
)

RuntimeArtifactScope = Literal["managed", "staged"]

_RUNTIME_VALUE_MARKER_KEY = "__ea_runtime_value__"
_RUNTIME_ARTIFACT_MARKER_VALUE = "artifact_ref"
_RUNTIME_HANDLE_MARKER_VALUE = "handle_ref"


def _copy_metadata_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): copy.deepcopy(item) for key, item in value.items()}


def _normalize_required_runtime_string(field_name: str, value: object) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _normalize_worker_generation(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("worker_generation must be an integer")
    try:
        generation = int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("worker_generation must be an integer") from exc
    if generation < 0:
        raise ValueError("worker_generation must be >= 0")
    return generation


@dataclass(slots=True, frozen=True)
class RuntimeArtifactRef:
    ref: str
    artifact_id: str
    scope: RuntimeArtifactScope
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        parsed = parse_artifact_ref(self.ref)
        if self.scope == "managed":
            if not isinstance(parsed, ManagedArtifactRef):
                raise ValueError(f"Runtime artifact ref is not managed: {self.ref!r}")
            normalized_ref = parsed.as_string()
        elif self.scope == "staged":
            if not isinstance(parsed, StagedArtifactRef):
                raise ValueError(f"Runtime artifact ref is not staged: {self.ref!r}")
            normalized_ref = parsed.as_string()
        else:
            raise ValueError(f"Unsupported runtime artifact scope: {self.scope!r}")

        if self.artifact_id != parsed.artifact_id:
            raise ValueError(
                "Runtime artifact ref artifact_id does not match the ref payload: "
                f"{self.artifact_id!r} != {parsed.artifact_id!r}"
            )

        object.__setattr__(self, "ref", normalized_ref)
        object.__setattr__(self, "metadata", _copy_metadata_mapping(self.metadata))

    @classmethod
    def managed(
        cls,
        artifact_id: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeArtifactRef:
        return cls(
            ref=format_managed_artifact_ref(artifact_id),
            artifact_id=str(artifact_id).strip(),
            scope="managed",
            metadata=_copy_metadata_mapping(metadata),
        )

    @classmethod
    def staged(
        cls,
        artifact_id: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeArtifactRef:
        return cls(
            ref=format_staged_artifact_ref(artifact_id),
            artifact_id=str(artifact_id).strip(),
            scope="staged",
            metadata=_copy_metadata_mapping(metadata),
        )

    @classmethod
    def from_artifact_ref(
        cls,
        value: object,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeArtifactRef:
        parsed = parse_artifact_ref(value)
        if isinstance(parsed, ManagedArtifactRef):
            return cls.managed(parsed.artifact_id, metadata=metadata)
        if isinstance(parsed, StagedArtifactRef):
            return cls.staged(parsed.artifact_id, metadata=metadata)
        raise ValueError(f"Unsupported runtime artifact ref value: {value!r}")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> RuntimeArtifactRef | None:
        if str(payload.get(_RUNTIME_VALUE_MARKER_KEY, "")).strip() != _RUNTIME_ARTIFACT_MARKER_VALUE:
            return None
        metadata = payload.get("metadata")
        ref_value = str(payload.get("ref", "")).strip()
        if not ref_value:
            return None
        runtime_ref = cls.from_artifact_ref(
            ref_value,
            metadata=metadata if isinstance(metadata, Mapping) else None,
        )
        payload_scope = str(payload.get("scope", "")).strip()
        payload_artifact_id = str(payload.get("artifact_id", "")).strip()
        if payload_scope and payload_scope != runtime_ref.scope:
            raise ValueError(
                "Runtime artifact ref payload scope does not match the ref value: "
                f"{payload_scope!r} != {runtime_ref.scope!r}"
            )
        if payload_artifact_id and payload_artifact_id != runtime_ref.artifact_id:
            raise ValueError(
                "Runtime artifact ref payload artifact_id does not match the ref value: "
                f"{payload_artifact_id!r} != {runtime_ref.artifact_id!r}"
            )
        return runtime_ref

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_ARTIFACT_MARKER_VALUE,
            "ref": self.ref,
            "artifact_id": self.artifact_id,
            "scope": self.scope,
        }
        if self.metadata:
            payload["metadata"] = _copy_metadata_mapping(self.metadata)
        return payload

    def __str__(self) -> str:
        return self.ref


@dataclass(slots=True, frozen=True)
class RuntimeHandleRef:
    handle_id: str
    kind: str
    owner_scope: str
    worker_generation: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "handle_id",
            _normalize_required_runtime_string("handle_id", self.handle_id),
        )
        object.__setattr__(self, "kind", _normalize_required_runtime_string("kind", self.kind))
        object.__setattr__(
            self,
            "owner_scope",
            _normalize_required_runtime_string("owner_scope", self.owner_scope),
        )
        object.__setattr__(
            self,
            "worker_generation",
            _normalize_worker_generation(self.worker_generation),
        )
        object.__setattr__(self, "metadata", _copy_metadata_mapping(self.metadata))

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> RuntimeHandleRef | None:
        if str(payload.get(_RUNTIME_VALUE_MARKER_KEY, "")).strip() != _RUNTIME_HANDLE_MARKER_VALUE:
            return None
        if "worker_generation" not in payload:
            raise ValueError("Runtime handle ref payload is missing worker_generation")
        return cls(
            handle_id=payload.get("handle_id", ""),
            kind=payload.get("kind", ""),
            owner_scope=payload.get("owner_scope", ""),
            worker_generation=payload.get("worker_generation", 0),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else None,
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_HANDLE_MARKER_VALUE,
            "handle_id": self.handle_id,
            "kind": self.kind,
            "owner_scope": self.owner_scope,
            "worker_generation": self.worker_generation,
        }
        if self.metadata:
            payload["metadata"] = _copy_metadata_mapping(self.metadata)
        return payload


def coerce_runtime_artifact_ref(value: object) -> RuntimeArtifactRef | None:
    if isinstance(value, RuntimeArtifactRef):
        return value
    if isinstance(value, Mapping):
        payload_ref = RuntimeArtifactRef.from_payload(value)
        if payload_ref is not None:
            return payload_ref
    parsed = parse_artifact_ref(value)
    if isinstance(parsed, ManagedArtifactRef):
        return RuntimeArtifactRef.managed(parsed.artifact_id)
    if isinstance(parsed, StagedArtifactRef):
        return RuntimeArtifactRef.staged(parsed.artifact_id)
    return None


def coerce_runtime_handle_ref(value: object) -> RuntimeHandleRef | None:
    if isinstance(value, RuntimeHandleRef):
        return value
    if isinstance(value, Mapping):
        return RuntimeHandleRef.from_payload(value)
    return None


def serialize_runtime_value(value: Any) -> Any:
    from ea_node_editor.execution.runtime_value_codec import serialize_runtime_value as _serialize_runtime_value

    return _serialize_runtime_value(value)


def deserialize_runtime_value(value: Any) -> Any:
    from ea_node_editor.execution.runtime_value_codec import deserialize_runtime_value as _deserialize_runtime_value

    return _deserialize_runtime_value(value)


__all__ = [
    "RuntimeArtifactRef",
    "RuntimeArtifactScope",
    "RuntimeHandleRef",
    "coerce_runtime_artifact_ref",
    "coerce_runtime_handle_ref",
    "deserialize_runtime_value",
    "serialize_runtime_value",
]
