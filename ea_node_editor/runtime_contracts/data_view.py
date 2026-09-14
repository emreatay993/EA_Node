# Purpose: Immutable, data-only definitions of single-file table and array views.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_data_view_contract.py
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ea_node_editor.common.payload_tools import copy_json_mapping, validate_payload_fields

DATA_VIEW_VERSION = 1
DATA_VIEW_MAX_BYTES = 48 * 1024  # Leave room for parser and provenance metadata.
DATA_VIEW_OPERATORS = frozenset({
    "eq", "ne", "lt", "le", "gt", "ge", "contains", "not_contains",
    "starts_with", "ends_with", "is_missing", "is_present",
})


def _fields(value: Any, name: str, allowed: set[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    validate_payload_fields(value, label=name, required=frozenset(), optional=frozenset(allowed))
    return dict(value)


def _text(value: Any, name: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"{name} must be {'a string' if empty else 'a nonblank string'}")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{name} must not contain control characters")
    return value


def _integer(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list")
    return value


def _selectors(value: Any, name: str) -> list[str | int]:
    result = []
    for item in _sequence(value, name):
        selected = _integer(item, name) if type(item) is int else _text(item, name)
        if selected in result:
            raise ValueError(f"{name} contains a duplicate column")
        result.append(selected)
    return result


def _axes(value: Any) -> dict[str, Any]:
    axes = _fields(value, "axes", {"row", "column", "fixed"})
    row = _integer(axes.get("row", 0), "row axis")
    column = axes.get("column", 1)
    if column is not None:
        column = _integer(column, "column axis")
        if column == row:
            raise ValueError("Row and column axes must be different")
    fixed = axes.get("fixed", {})
    if not isinstance(fixed, Mapping):
        raise ValueError("Fixed indices must be an object")
    normalized = {}
    for key, index in fixed.items():
        if not isinstance(key, str) or not key.isascii() or not key.isdigit() or str(int(key)) != key:
            raise ValueError("Fixed axis keys must be canonical non-negative integers")
        if int(key) in {row, column}:
            raise ValueError("A displayed axis cannot also have a fixed index")
        normalized[key] = _integer(index, "fixed index")
    return {"row": row, "column": column, "fixed": normalized}


def _block(value: Any, index: int) -> dict[str, Any]:
    data = _fields(value, "value block", {
        "id", "member", "axes", "columns", "labels_member", "labels_column", "names", "prefix", "unit",
    })
    names = data.get("names", {})
    if not isinstance(names, Mapping):
        raise ValueError("Column renames must be an object")
    normalized_names = {_text(key, "source column"): _text(name, "column name") for key, name in names.items()}
    label_column = data.get("labels_column")
    if label_column is not None:
        label_column = _selectors([label_column], "label column")[0]
    return {
        "id": _text(data.get("id", f"block{index + 1}"), "block id"),
        "member": _text(data.get("member", ""), "values member", empty=True),
        "axes": _axes(data.get("axes", {})),
        "columns": _selectors(data.get("columns", []), "block columns"),
        "labels_member": _text(data.get("labels_member", ""), "labels member", empty=True),
        "labels_column": label_column,
        "names": normalized_names,
        "prefix": _text(data.get("prefix", ""), "column prefix", empty=True),
        "unit": _text(data.get("unit", ""), "unit", empty=True),
    }


def _segment(value: Any) -> dict[str, Any]:
    data = _fields(value, "row segment", {"blocks", "coordinate"})
    blocks = [_block(block, index) for index, block in enumerate(_sequence(data.get("blocks", []), "blocks"))]
    if not blocks:
        raise ValueError("A table segment needs at least one values block")
    if len({block["id"] for block in blocks}) != len(blocks):
        raise ValueError("Value block identifiers must be unique within a segment")
    coordinate = data.get("coordinate")
    if coordinate is not None:
        coord = _fields(coordinate, "row coordinate", {"member", "column", "name", "unit"})
        column = coord.get("column")
        coordinate = {
            "member": _text(coord.get("member", ""), "coordinate member", empty=True),
            "column": None if column is None else _selectors([column], "coordinate column")[0],
            "name": _text(coord.get("name", "time"), "coordinate name"),
            "unit": _text(coord.get("unit", ""), "coordinate unit", empty=True),
        }
    return {"blocks": blocks, "coordinate": coordinate}


def _query(value: Any) -> dict[str, Any]:
    data = _fields(value, "output rules", {"match", "filters", "sort"})
    match = data.get("match", "all")
    if match not in {"all", "any"}:
        raise ValueError("Conditions must match all or any")
    predicates = []
    for entry in _sequence(data.get("filters", []), "filters"):
        predicate = _fields(entry, "condition", {"column", "op", "value"})
        op = predicate.get("op", "eq")
        if op not in DATA_VIEW_OPERATORS:
            raise ValueError(f"Unsupported output condition: {op}")
        predicates.append({
            "column": _text(predicate.get("column"), "condition column"),
            "op": op,
            "value": "" if op in {"is_missing", "is_present"} else _text(predicate.get("value", ""), "condition value", empty=True),
        })
    sorts = []
    for entry in _sequence(data.get("sort", []), "sort keys"):
        directive = _fields(entry, "sort key", {"column", "descending"})
        descending = directive.get("descending", False)
        if type(descending) is not bool:
            raise ValueError("Sort direction must be boolean")
        column = _text(directive.get("column"), "sort column")
        if any(item["column"] == column for item in sorts):
            raise ValueError("Sort columns must be unique")
        sorts.append({"column": column, "descending": descending})
    return {"match": match, "filters": predicates, "sort": sorts}


def _normalize(payload: Mapping[str, Any]) -> dict[str, Any]:
    data = _fields(payload, "data view", {"version", "mode", "member", "segments", "query", "output", "array_slices"})
    if type(data.get("version")) is not int or data["version"] != DATA_VIEW_VERSION:
        raise ValueError("Unsupported data-view version")
    mode = data.get("mode", "source")
    if mode not in {"source", "table", "array"}:
        raise ValueError("View mode must be source, table, or array")
    segments = [_segment(item) for item in _sequence(data.get("segments", []), "segments")]
    if mode == "table" and not segments:
        raise ValueError("Build table needs at least one segment")
    if mode != "table" and segments:
        raise ValueError("Only table views can contain composition segments")
    query = _query(data.get("query", {}))
    if mode == "array" and (query["filters"] or query["sort"]):
        raise ValueError("Saved filters and sorting require table mode")
    output = _fields(data.get("output", {}), "output selection", {"row_offset", "row_limit", "columns"})
    output = {
        "row_offset": _integer(output.get("row_offset", 0), "output row offset"),
        "row_limit": _integer(output.get("row_limit", 0), "output row limit"),
        "columns": _selectors(output.get("columns", []), "output columns"),
    }
    slices = []
    for entry in _sequence(data.get("array_slices", []), "array slices"):
        bounds = _sequence(entry, "slice bounds")
        if len(bounds) != 2:
            raise ValueError("Array slices contain offset and limit pairs")
        slices.append([_integer(bounds[0], "slice offset"), _integer(bounds[1], "slice limit")])
    if mode != "array" and slices:
        raise ValueError("Array slices require array mode")
    if mode == "array" and any(output.values()):
        raise ValueError("Raw arrays use array slices, not table output rules")
    return {
        "version": DATA_VIEW_VERSION, "mode": mode,
        "member": _text(data.get("member", ""), "source member", empty=True),
        "segments": segments, "query": query, "output": output, "array_slices": slices,
    }


@dataclass(frozen=True, slots=True, init=False)
class DataViewDefinition:
    """Canonical immutable recipe; dictionaries returned to clients are detached."""

    canonical_json: str

    def __init__(self, payload: Mapping[str, Any] | None = None) -> None:
        value = {"version": DATA_VIEW_VERSION, "mode": "source"} if payload is None else payload
        copied = copy_json_mapping(value, field_name="data view", max_encoded_bytes=DATA_VIEW_MAX_BYTES)
        canonical = _normalize(copied)
        copy_json_mapping(canonical, field_name="data view", max_encoded_bytes=DATA_VIEW_MAX_BYTES)
        object.__setattr__(self, "canonical_json", json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DataViewDefinition:
        return cls(payload)

    def to_payload(self) -> dict[str, Any]:
        return json.loads(self.canonical_json)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()

    @property
    def mode(self) -> str:
        return self.to_payload()["mode"]

    @property
    def member(self) -> str:
        return self.to_payload()["member"]

    @property
    def members(self) -> tuple[str, ...]:
        payload = self.to_payload()
        result = [payload["member"]] if payload["mode"] != "table" else []
        for segment in payload["segments"]:
            for block in segment["blocks"]:
                result.append(block["member"])
                if block["labels_member"]:
                    result.append(block["labels_member"])
            if segment["coordinate"] is not None:
                result.append(segment["coordinate"]["member"])
        return tuple(dict.fromkeys(result))

    @property
    def has_query(self) -> bool:
        query = self.to_payload()["query"]
        return bool(query["filters"] or query["sort"])


def projection_axes(axes: Mapping[str, Any], shape: Sequence[int]) -> tuple[int, int | None, dict[int, int]]:
    """Validate explicit dimensions against metadata, without reading array values."""
    normalized = _axes(axes)
    rank = len(shape)
    row, column = normalized["row"], normalized["column"]
    if rank == 1 and row == 0 and column == 1:
        column = None
    if rank == 0 or row >= rank or column is not None and column >= rank:
        raise ValueError(f"Selected axes do not fit an array of rank {rank}")
    fixed = {int(key): value for key, value in normalized["fixed"].items()}
    remaining = set(range(rank)) - {row, column}
    if set(fixed) != remaining:
        raise ValueError("Choose a fixed index for every axis other than the row and column axes")
    if any(index >= shape[axis] for axis, index in fixed.items()):
        raise ValueError("A fixed index is outside its array dimension")
    return row, column, fixed


__all__ = ["DATA_VIEW_VERSION", "DATA_VIEW_MAX_BYTES", "DATA_VIEW_OPERATORS", "DataViewDefinition", "projection_axes"]
