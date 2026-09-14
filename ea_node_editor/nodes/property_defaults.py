# Purpose: Own immutable declaration defaults without retaining mutable user aliases.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_registry_immutability.py
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from ea_node_editor.runtime_contracts import (
    ImageValue,
    Interval1D,
    RuntimeArtifactRef,
    TypedInlineValue,
)

_SCALARS = (type(None), bool, int, float, str, bytes)
_RECORDS = (ImageValue, Interval1D, RuntimeArtifactRef, TypedInlineValue)


@dataclass(frozen=True, slots=True, eq=False)
class PropertyDefaultTemplate:
    """A captured value tree; container kinds survive independent materialization."""

    kind: str
    value: Any

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PropertyDefaultTemplate):
            return NotImplemented
        if self.kind != other.kind:
            return False
        if self.kind == "dict":
            return dict(self.value) == dict(other.value)
        if self.kind in {"set", "frozenset"}:
            return frozenset(self.value) == frozenset(other.value)
        return self.value == other.value

    def __hash__(self) -> int:
        value = (
            frozenset(self.value)
            if self.kind in {"dict", "set", "frozenset"}
            else self.value
        )
        return hash((self.kind, value))

    @classmethod
    def capture(cls, value: Any) -> PropertyDefaultTemplate:
        return _capture(value, set())

    def materialize(self) -> Any:
        if self.kind == "scalar":
            return self.value
        if self.kind == "record":
            record_type, values = self.value
            return record_type(**{key: item.materialize() for key, item in values})
        if self.kind == "dict":
            return {key.materialize(): item.materialize() for key, item in self.value}
        items = (item.materialize() for item in self.value)
        return {"list": list, "tuple": tuple, "set": set, "frozenset": frozenset}[
            self.kind
        ](items)


def _capture(value: Any, active: set[int]) -> PropertyDefaultTemplate:
    value_type = type(value)
    if value_type in _SCALARS:
        return PropertyDefaultTemplate("scalar", value)
    if id(value) in active:
        raise ValueError("Property defaults cannot contain cycles")
    active.add(id(value))
    try:
        if value_type in _RECORDS:
            return PropertyDefaultTemplate(
                "record",
                (
                    value_type,
                    tuple(
                        (field.name, _capture(getattr(value, field.name), active))
                        for field in fields(value)
                        if field.init
                    ),
                ),
            )
        if value_type is dict:
            return PropertyDefaultTemplate(
                "dict",
                tuple(
                    (_capture(key, active), _capture(item, active))
                    for key, item in value.items()
                ),
            )
        if value_type in (list, tuple, set, frozenset):
            return PropertyDefaultTemplate(
                value_type.__name__, tuple(_capture(item, active) for item in value)
            )
        raise TypeError(f"Unsupported property default type: {value_type.__name__}")
    finally:
        active.remove(id(value))
