# Purpose: Define immutable source bindings committed with accepted runtime outputs.
# Map: subsystems/supporting_runtime_assets.md
# Tests: tests/test_retained_resources.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any

from ea_node_editor.common.payload_tools import REF_METADATA_MAX_BYTES, copy_json_mapping, validate_payload_fields


class RetainedResourceError(ValueError):
    """A retained value cannot be used under its accepted source identity."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RetainedSourceBinding:
    """Internal integrity metadata; deliberately separate from authored refs."""

    ref_kind: str
    ref_id: str
    resolver_id: str
    backend_id: str
    source_uri: str
    object_id: str
    options_json: str
    backend_policy_revision: str
    size_bytes: int
    sha256: str
    hash_policy_digest: str

    def __post_init__(self) -> None:
        for name in ("ref_kind", "ref_id", "resolver_id", "backend_id", "source_uri", "object_id", "backend_policy_revision"):
            value = getattr(self, name)
            if type(value) is not str or not value or value != value.strip():
                raise ValueError(f"Retained source {name} must be a non-empty trimmed string")
        if self.ref_kind not in {"table", "array"}:
            raise ValueError("Retained source ref_kind must be table or array")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise ValueError("Retained source size_bytes must be non-negative")
        for name in ("sha256", "hash_policy_digest"):
            value = getattr(self, name)
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError(f"Retained source {name} must be a SHA-256 digest")
        if type(self.options_json) is not str:
            raise TypeError("Retained source options_json must be a string")
        options = copy_json_mapping(
            json.loads(self.options_json), field_name="retained source options",
            max_encoded_bytes=REF_METADATA_MAX_BYTES,
        )
        if canonical_options_json(options) != self.options_json:
            raise ValueError("Retained source options_json must be canonical")

    @property
    def key(self) -> tuple[str, str, str]:
        return self.resolver_id, self.ref_kind, self.ref_id

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical_options_json(self.to_payload()).encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> RetainedSourceBinding:
        validate_payload_fields(payload, label="Retained source binding", required=frozenset(cls.__dataclass_fields__))
        return cls(**payload)


def canonical_options_json(options: Mapping[str, Any]) -> str:
    return json.dumps(options, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
