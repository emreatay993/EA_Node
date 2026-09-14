# Purpose: Correlate worker generation preparation independently of workflow execution.
# Map: subsystems/execution.md
# Tests: tests/test_generation_readiness.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ea_node_editor.execution.registry_agreement import (
    RegistryAgreement,
    _sha256_digest,
)
from ea_node_editor.execution.transport_fields import string_value


def _request_id(value: str) -> str:
    result = string_value(value, field_name="request_id").strip()
    if not result or len(result) > 256 or not result.isprintable():
        raise ValueError("generation request_id must be bounded printable text")
    return result


@dataclass(frozen=True, slots=True)
class PrepareGenerationCommand:
    request_id: str
    agreement: RegistryAgreement
    type: Literal["prepare_generation"] = "prepare_generation"

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _request_id(self.request_id))
        if type(self.agreement) is not RegistryAgreement:
            raise TypeError("generation preparation requires a RegistryAgreement")
        if self.type != "prepare_generation":
            raise ValueError("invalid generation command type")


@dataclass(frozen=True, slots=True)
class GenerationPreparedEvent:
    request_id: str
    registry_contract_fingerprint: str
    runtime_registry_fingerprint: str
    build_fingerprint: str
    type: Literal["generation_prepared"] = "generation_prepared"

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _request_id(self.request_id))
        for name in (
            "registry_contract_fingerprint",
            "runtime_registry_fingerprint",
            "build_fingerprint",
        ):
            object.__setattr__(
                self, name, _sha256_digest(getattr(self, name), field_name=name)
            )
        if self.type != "generation_prepared":
            raise ValueError("invalid generation event type")


@dataclass(frozen=True, slots=True)
class GenerationPreparationFailedEvent:
    request_id: str
    error: str
    type: Literal["generation_preparation_failed"] = "generation_preparation_failed"

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _request_id(self.request_id))
        object.__setattr__(self, "error", string_value(self.error, field_name="error"))
        if not self.error.strip():
            raise ValueError("generation failure requires an error")
        if self.type != "generation_preparation_failed":
            raise ValueError("invalid generation failure type")
