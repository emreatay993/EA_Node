# Purpose: Correlate one worker-generation preparation and retire late responses.
# Map: subsystems/execution.md
# Tests: tests/test_generation_readiness.py
from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass, field
import threading
from typing import Any, Mapping
import uuid

from ea_node_editor.execution.generation_messages import GenerationPreparedEvent
from ea_node_editor.execution.registry_agreement import RegistryAgreement


@dataclass(frozen=True, slots=True)
class GenerationPreparation:
    request_id: str
    physical_generation: int
    agreement: RegistryAgreement
    _completion: Future[GenerationPreparedEvent] = field(repr=False, compare=False)

    def result(self, timeout: float | None = None) -> GenerationPreparedEvent:
        return self._completion.result(timeout)

    @property
    def done(self) -> bool:
        return self._completion.done()


class GenerationReadiness:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: GenerationPreparation | None = None
        self._phase = "empty"

    def begin(
        self, generation: int, agreement: RegistryAgreement
    ) -> tuple[GenerationPreparation, bool]:
        if (
            type(generation) is not int
            or generation <= 0
            or type(agreement) is not RegistryAgreement
        ):
            raise ValueError(
                "readiness requires a physical generation and an owned agreement"
            )
        with self._lock:
            current = self._current
            if (
                current is not None
                and current.physical_generation == generation
                and current.agreement == agreement
                and self._phase in {"pending", "ready"}
            ):
                return current, False
            if self._phase == "pending":
                raise RuntimeError("another worker generation is being prepared")
            current = GenerationPreparation(
                f"generation_{uuid.uuid4().hex}", generation, agreement, Future()
            )
            self._current, self._phase = current, "pending"
            return current, True

    def receive(self, payload: Mapping[str, Any], generation: int) -> bool:
        event_type = payload.get("type")
        if event_type not in {
            "generation_prepared",
            "generation_preparation_failed",
            "protocol_error",
        }:
            return False
        with self._lock:
            current = self._current
            if (
                current is None
                or payload.get("request_id") != current.request_id
                or generation != current.physical_generation
                or self._phase != "pending"
            ):
                return event_type != "protocol_error"
            error = None
            event = None
            if event_type == "generation_prepared":
                event = GenerationPreparedEvent(**dict(payload))
                if (
                    event.registry_contract_fingerprint
                    != current.agreement.registry_contract_fingerprint
                    or event.runtime_registry_fingerprint
                    != current.agreement.runtime_registry_fingerprint
                ):
                    error = RuntimeError(
                        "worker generation readiness agreement changed"
                    )
            else:
                error = RuntimeError(
                    str(payload.get("error", "Worker generation preparation failed"))
                )
            self._phase = "failed" if error is not None else "ready"
        # Future callbacks never run while the readiness state lock is held.
        if error is not None:
            current._completion.set_exception(error)
        else:
            current._completion.set_result(event)
        return True

    def retire(self, reason: str, *, generation: int | None = None) -> None:
        with self._lock:
            if generation is not None and (
                self._current is None or self._current.physical_generation != generation
            ):
                return
            pending = self._current if self._phase == "pending" else None
            self._current, self._phase = None, "empty"
        if pending is not None:
            pending._completion.set_exception(RuntimeError(reason))
