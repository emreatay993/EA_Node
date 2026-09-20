# Purpose: Transfer worker-owned output leases without reader-thread round trips.
# Map: subsystems/execution.md
# Tests: tests/test_process_solution_resources.py
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
import threading
from typing import Any
from uuid import uuid4

from ea_node_editor.runtime_contracts import DataTree, RuntimeHandleRef
from ea_node_editor.runtime_contracts.value_codec import deserialize_runtime_value, serialize_runtime_value

MAX_OFFER_HANDLES = 4096
MAX_WORKER_LEASES = 16384


def _identity(value: Any) -> str:
    if type(value) is not str or not value or len(value) > 256 or value != value.strip():
        raise ValueError("solution resource identity must be bounded nonempty text")
    return value


def _generation(value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError("solution resource generation must be positive")
    return value


@dataclass(frozen=True, slots=True)
class SolutionResourceOffer:
    offer_id: str
    run_id: str
    workspace_id: str
    node_id: str
    generation: int
    sequence: int
    handles: tuple[tuple[RuntimeHandleRef, RuntimeHandleRef], ...]

    def __post_init__(self) -> None:
        for name in ("offer_id", "run_id", "workspace_id", "node_id"):
            _identity(getattr(self, name))
        _generation(self.generation)
        _generation(self.sequence)
        if type(self.handles) is not tuple or not 0 < len(self.handles) <= MAX_OFFER_HANDLES:
            raise ValueError("solution resource offer exceeds its handle budget")
        for pair in self.handles:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("solution resource offer requires handle pairs")
            original, leased = pair
            if type(original) is not RuntimeHandleRef or type(leased) is not RuntimeHandleRef:
                raise ValueError("solution resource offer requires exact handle refs")
            if leased.owner_scope != f"solution-offer:{self.offer_id}" or replace(
                leased, owner_scope=original.owner_scope
            ) != original:
                raise ValueError("solution resource offer changed handle identity")

    def to_payload(self, catalog: Any) -> dict[str, Any]:
        return {
            "offer_id": self.offer_id, "run_id": self.run_id,
            "workspace_id": self.workspace_id, "node_id": self.node_id,
            "generation": self.generation, "sequence": self.sequence,
            "handles": [[serialize_runtime_value(a, catalog=catalog),
                         serialize_runtime_value(b, catalog=catalog)] for a, b in self.handles],
        }

    @classmethod
    def from_payload(cls, payload: Any, catalog: Any) -> SolutionResourceOffer:
        fields = {"offer_id", "run_id", "workspace_id", "node_id", "generation", "sequence", "handles"}
        if type(payload) is not dict or set(payload) != fields:
            raise ValueError("invalid solution resource offer fields")
        handles = payload["handles"]
        if type(handles) is not list or not 0 < len(handles) <= MAX_OFFER_HANDLES:
            raise ValueError("invalid solution resource offer handles")
        pairs = []
        for pair in handles:
            if type(pair) is not list or len(pair) != 2:
                raise ValueError("invalid solution resource offer handle pair")
            pairs.append(tuple(deserialize_runtime_value(item, catalog=catalog) for item in pair))
        return cls(**{key: payload[key] for key in fields - {"handles"}}, handles=tuple(pairs))


@dataclass(frozen=True, slots=True)
class SolutionResourceCommand:
    offer_id: str
    run_id: str
    workspace_id: str
    node_id: str
    generation: int
    action: str
    indices: tuple[int, ...]
    type: str = field(default="solution_resources", init=False)

    def __post_init__(self) -> None:
        for name in ("offer_id", "run_id", "workspace_id", "node_id"):
            _identity(getattr(self, name))
        _generation(self.generation)
        if self.action not in {"settle", "release"}:
            raise ValueError("invalid solution resource action")
        if (type(self.indices) is not tuple or len(self.indices) > MAX_OFFER_HANDLES
                or any(type(i) is not int or not 0 <= i < MAX_OFFER_HANDLES for i in self.indices)
                or len(set(self.indices)) != len(self.indices)):
            raise ValueError("invalid solution resource indices")

    @classmethod
    def for_offer(cls, offer: SolutionResourceOffer, action: str, indices: tuple[int, ...]):
        return cls(offer.offer_id, offer.run_id, offer.workspace_id, offer.node_id,
                   offer.generation, action, indices)

    def to_payload(self) -> dict[str, Any]:
        return {"type": self.type, "offer_id": self.offer_id, "run_id": self.run_id,
                "workspace_id": self.workspace_id, "node_id": self.node_id,
                "generation": self.generation, "action": self.action,
                "indices": list(self.indices)}

    @classmethod
    def from_payload(cls, payload: Any):
        fields = {"type", "offer_id", "run_id", "workspace_id", "node_id", "generation", "action", "indices"}
        if (type(payload) is not dict or set(payload) != fields
                or payload["type"] != "solution_resources" or type(payload["indices"]) is not list):
            raise ValueError("invalid solution resource command fields")
        return cls(**{key: payload[key] for key in fields - {"type", "indices"}},
                   indices=tuple(payload["indices"]))


def iter_solution_handles(value: Any):
    if isinstance(value, RuntimeHandleRef):
        yield value
    elif isinstance(value, DataTree):
        for _, items in value.branches:
            for item in items:
                yield from iter_solution_handles(item)
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from iter_solution_handles(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from iter_solution_handles(item)


@dataclass(slots=True)
class _WorkerOffer:
    offer: SolutionResourceOffer
    live: set[int]
    settled: bool = False


class WorkerSolutionResources:
    """Offers retain exact registry leases until host adoption or rejection.

    All calls run on the process worker's command/execution thread. Accepted
    entries are owned by SolutionStore; ordinary pre-run workspace retirement
    only retires abandoned offers, never those accepted entries.
    """

    def __init__(self, registry: Any) -> None:
        self._registry = registry
        self._offers: dict[str, _WorkerOffer] = {}
        self._sequence = 0

    def stage(self, outputs: Mapping[str, Any], *, run_id: str, workspace_id: str,
              node_id: str, generation: int) -> SolutionResourceOffer | None:
        refs = []
        for result in outputs.values():
            if result.status == "value":
                for ref in iter_solution_handles(result.value):
                    refs.append(ref)
                    if len(refs) > MAX_OFFER_HANDLES:
                        return None
        if not refs or sum(len(entry.live) for entry in self._offers.values()) + len(refs) > MAX_WORKER_LEASES:
            return None
        offer_id = uuid4().hex
        scope = f"solution-offer:{offer_id}"
        self._sequence += 1
        try:
            pairs = tuple((ref, self._registry.lease(ref, owner_scope=scope)) for ref in refs)
            offer = SolutionResourceOffer(offer_id, run_id, workspace_id, node_id, generation, self._sequence, pairs)
        except (LookupError, TypeError, ValueError, RuntimeError):
            self._registry.release_owner_scope(scope)
            return None
        self._offers[offer_id] = _WorkerOffer(offer, set(range(len(pairs))))
        return offer

    def apply(self, command: SolutionResourceCommand) -> None:
        entry = self._offers.get(command.offer_id)
        if entry is None:
            return  # Late or duplicate release cannot acquire another lease.
        expected = SolutionResourceCommand.for_offer(entry.offer, command.action, command.indices)
        if command != expected or any(index >= len(entry.offer.handles) for index in command.indices):
            raise ValueError("solution resource command does not match its offer")
        indices = set(command.indices)
        if command.action == "settle":
            if entry.settled:
                return  # Replayed settlement never resurrects released entries.
            release = entry.live - indices
            entry.settled = True
        else:
            release = entry.live & indices
        for index in release:
            self._registry.release(entry.offer.handles[index][1])
            entry.live.remove(index)
        if not entry.live:
            self._offers.pop(command.offer_id, None)

    def retire_unclaimed(self, workspace_id: str) -> None:
        for entry in tuple(self._offers.values()):
            if entry.offer.workspace_id == workspace_id and not entry.settled:
                self.apply(SolutionResourceCommand.for_offer(entry.offer, "settle", ()))

    def validate_retained(self, value: RuntimeHandleRef) -> None:
        entry = self._offers.get(value.owner_scope.removeprefix("solution-offer:"))
        if entry is None or not entry.settled or not any(
            entry.offer.handles[index][1] == value for index in entry.live
        ):
            raise ValueError("current output handle has no accepted worker lease")
        self._registry.resolve(value)

    def reset(self) -> None:
        # HandleRegistry.reset owns disposal and generation advancement.
        self._offers.clear()


@dataclass(frozen=True, slots=True)
class ProcessSolutionLease:
    owner: Any
    offer_id: str
    index: int
    generation: int
    value: RuntimeHandleRef


@dataclass(slots=True)
class _HostOffer:
    offer: SolutionResourceOffer
    generation: int
    leases: dict[int, ProcessSolutionLease] = field(default_factory=dict)
    claimed: set[int] = field(default_factory=set)
    settled: bool = False


class ClientSolutionResources:
    """Claims are local; ordered one-way commands transfer/release worker leases."""

    def __init__(self, send: Any, on_failure: Any = None) -> None:
        self._send = send
        self._on_failure = on_failure
        self._lock = threading.RLock()
        self._local = threading.local()
        self._offers: dict[str, _HostOffer] = {}
        self._generation = 0
        self._sequence = 0

    @contextmanager
    def dispatch(self, offer: SolutionResourceOffer | None, *, generation: int,
                 run_id: str, workspace_id: str, node_id: str):
        entry = None
        previous = getattr(self._local, "entry", None)
        with self._lock:
            if offer is not None:
                if (offer.generation != generation or offer.run_id != run_id
                        or offer.workspace_id != workspace_id or offer.node_id != node_id):
                    raise ValueError("solution resource offer has wrong event identity")
                if generation > self._generation:
                    self._generation, self._sequence = generation, 0
                if (generation == self._generation and offer.sequence > self._sequence
                        and offer.offer_id not in self._offers):
                    self._sequence = offer.sequence
                    entry = _HostOffer(offer, generation)
                    self._offers[offer.offer_id] = entry
            self._local.entry = entry
        try:
            yield
        except BaseException:
            with self._lock:
                if entry is not None:
                    entry.leases.clear()
            raise
        finally:
            delivery_failed = False
            with self._lock:
                self._local.entry = previous
                if entry is not None and self._offers.get(entry.offer.offer_id) is entry:
                    indices = tuple(sorted(entry.leases))
                    command = SolutionResourceCommand.for_offer(entry.offer, "settle", indices)
                    # Serialize release with settlement so concurrent invalidation
                    # cannot enqueue a release before the transfer acknowledgment.
                    entry.settled = True
                    try:
                        self._send(command, generation)
                    except Exception:
                        delivery_failed = True
                    finally:
                        if not entry.leases:
                            self._offers.pop(entry.offer.offer_id, None)
            if delivery_failed and self._on_failure is not None:
                self._on_failure(generation)

    def claim(self, run_id: str, value: RuntimeHandleRef, generation: int):
        with self._lock:
            entry = getattr(self._local, "entry", None)
            if (entry is None or entry.settled or entry.generation != generation
                    or entry.offer.run_id != run_id
                    or self._offers.get(entry.offer.offer_id) is not entry):
                return None
            for index, (original, leased) in enumerate(entry.offer.handles):
                if index not in entry.claimed and original == value:
                    lease = ProcessSolutionLease(self, entry.offer.offer_id, index, generation, leased)
                    entry.claimed.add(index)
                    entry.leases[index] = lease
                    return leased, lease
        return None

    def release(self, lease: ProcessSolutionLease) -> None:
        delivery_failed = False
        with self._lock:
            entry = self._offers.get(lease.offer_id)
            if (lease.owner is not self or entry is None or entry.generation != lease.generation
                    or entry.leases.get(lease.index) is not lease):
                return
            entry.leases.pop(lease.index)
            if entry.settled:
                try:
                    self._send(SolutionResourceCommand.for_offer(entry.offer, "release", (lease.index,)),
                               entry.generation)
                except Exception:
                    delivery_failed = True
                finally:
                    if not entry.leases:
                        self._offers.pop(lease.offer_id, None)
        if delivery_failed and self._on_failure is not None:
            self._on_failure(lease.generation)

    def reset(self) -> None:
        with self._lock:
            self._offers.clear()
            self._generation = self._sequence = 0

    def retire_generation(self, generation: int) -> None:
        with self._lock:
            for key, entry in tuple(self._offers.items()):
                if entry.generation == generation:
                    self._offers.pop(key)
