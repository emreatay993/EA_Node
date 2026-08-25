# Purpose: Provide the dependency-free public function-plugin authoring surface.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_plugin_declaration.py

from __future__ import annotations

from collections.abc import Mapping as _Mapping
from collections.abc import Sequence as _Sequence
from collections.abc import Set as _Set
from difflib import get_close_matches as _get_close_matches
from types import MappingProxyType as _MappingProxyType


Any = "COREX.DataTypes.Any"
Image = "COREX.DataTypes.Image"
Color = "COREX.DataTypes.Color"
Interval = "COREX.DataTypes.Interval1D"


def _identity_decorator(*_args: object, **_kwargs: object):
    def decorate(function):
        return function

    return decorate


def node(function=None, **_metadata: object):
    if callable(function) and not _metadata:
        return function
    return _identity_decorator()


input = _identity_decorator
output = _identity_decorator
text = _identity_decorator
text_area = _identity_decorator
number = _identity_decorator
switch = _identity_decorator
dropdown = _identity_decorator
slider = _identity_decorator
color = _identity_decorator
path = _identity_decorator
interval = _identity_decorator
list = _identity_decorator


def _unknown_setting_message(name: object, known_names: object) -> str:
    token = str(name)[:128]
    candidates = tuple(str(item) for item in known_names)
    suggestion = _get_close_matches(token, candidates, n=1, cutoff=0.6)
    suffix = f" Did you mean {suggestion[0]!r}?" if suggestion else ""
    return f"Unknown setting {token!r}.{suffix}"


def _deep_freeze(value: object) -> object:
    if isinstance(value, _Mapping):
        return _MappingProxyType(
            {key: _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, _Sequence) and not isinstance(value, (str, bytes)):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, _Set):
        return frozenset(_deep_freeze(item) for item in value)
    return value


def _deep_mutable(value: object) -> object:
    if isinstance(value, _Mapping):
        return {key: _deep_mutable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_deep_mutable(item) for item in value]
    if isinstance(value, frozenset):
        return {_deep_mutable(item) for item in value}
    return value


class _Settings:
    __slots__ = ("_values",)

    def __init__(self, values: _Mapping[str, object]) -> None:
        object.__setattr__(self, "_values", _deep_freeze(dict(values)))

    def __getattr__(self, name: str) -> object:
        values = object.__getattribute__(self, "_values")
        try:
            return values[name]
        except KeyError as exc:
            raise AttributeError(_unknown_setting_message(name, values)) from exc

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("Settings is immutable")

    def to_dict(self) -> dict[str, object]:
        values = object.__getattribute__(self, "_values")
        return _deep_mutable(values)  # type: ignore[return-value]


__all__ = [
    "node",
    "input",
    "output",
    "text",
    "text_area",
    "number",
    "switch",
    "dropdown",
    "slider",
    "color",
    "path",
    "interval",
    "list",
    "Any",
    "Image",
    "Color",
    "Interval",
]
