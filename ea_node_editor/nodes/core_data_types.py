# Purpose: Declare the runtime-ready core semantic graph-data type contribution.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_registry_validation.py, tests/test_core_value_codecs.py

from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping, Sequence
from numbers import Real

from ea_node_editor.common.payload_tools import (
    INLINE_PAYLOAD_MAX_BYTES,
    copy_json_safe,
)
from ea_node_editor.common.scene_protocol import (
    COREX_SCENE_HANDLE_KIND,
    ENGINEERING_SELECTION_SCHEMA,
)
from ea_node_editor.runtime_contracts import (
    ARRAY_DATA_REF_TYPE_ID,
    ARRAY_SLICE_2D_REF_TYPE_ID,
    ArrayDataRef,
    ArraySlice2DRef,
    BOOLEAN_DATA_TYPE_ID,
    COREX_VIEWER_SESSION_HANDLE_KIND,
    DataTypeFamilySpec,
    DataTypeSpec,
    DOUBLE_DATA_TYPE_ID,
    ENGINEERING_SCENE_DATA_TYPE_ID,
    ENGINEERING_SELECTION_SET_DATA_TYPE_ID,
    GRAPH_ARRAY_DATA_TYPE_ID,
    GRAPH_DATA_TYPE_ID,
    GRAPH_DICTIONARY_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    INTERVAL_1D_GRAPH_DATA_TYPE_ID,
    Interval1D,
    JSON_DATA_TYPE_ID,
    PATH_DATA_TYPE_ID,
    RuntimeArtifactRef,
    RuntimeHandleRef,
    STRING_DATA_TYPE_ID,
    STRING_LIST_DATA_TYPE_ID,
    TABULAR_DATA_REF_TYPE_ID,
    TABULAR_WINDOW_REF_TYPE_ID,
    TabularDataRef,
    TabularWindowRef,
    VIEWER_SESSION_DATA_TYPE_ID,
    coerce_interval_1d,
)

CORE_DATA_TYPE_OWNER_ID = "corex.core_data_types"
CORE_DATA_TYPE_OWNER_VERSION = "1"
CLIPPABLE_GRAPH_DATA_TYPE_ID = "COREX.Common.IClippableGraphDataType"





_RUNTIME_VALUE_MARKER_KEY = "__ea_runtime_value__"


def _is_any(_value: object) -> bool:
    return True


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_real(value: object) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _copy_exact_json_collection_value(value: object) -> object:
    value_type = type(value)
    if value is None or value_type in {bool, int, str}:
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError("graph collection requires finite numbers")
        return value
    if value_type is list:
        return [_copy_exact_json_collection_value(item) for item in value]
    if value_type is dict:
        copied: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str or key == _RUNTIME_VALUE_MARKER_KEY:
                raise TypeError("graph collection contains an invalid key")
            copied[key] = _copy_exact_json_collection_value(item)
        return copied
    raise TypeError("graph collection requires exact built-in JSON values")


def _is_json_container(value: object, container_type: type[object]) -> bool:
    if type(value) is not container_type:
        return False
    try:
        detached = _copy_exact_json_collection_value(value)
        copy_json_safe(
            detached,
            field_name="graph collection",
            max_encoded_bytes=INLINE_PAYLOAD_MAX_BYTES,
        )
    except Exception:
        return False
    return True


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    )


def _is_string_list(value: object) -> bool:
    return _is_sequence(value) and all(isinstance(item, str) for item in value)


def _is_json_value(value: object) -> bool:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return True


def _is_path(value: object) -> bool:
    return isinstance(value, (str, os.PathLike, RuntimeArtifactRef))


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, Real):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValueError(f"cannot coerce {value!r} to Boolean")


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("bool is not an Integer")
    return int(value)  # type: ignore[arg-type]


def _coerce_double(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("bool is not a Number")
    return float(value)  # type: ignore[arg-type]


def _coerce_path(value: object) -> object:
    if isinstance(value, RuntimeArtifactRef):
        return value
    return os.fspath(value) if isinstance(value, os.PathLike) else str(value)


def _is_engineering_scene(value: object) -> bool:
    return (
        isinstance(value, RuntimeHandleRef)
        and value.data_type_id == ENGINEERING_SCENE_DATA_TYPE_ID
        and value.kind == COREX_SCENE_HANDLE_KIND
    )


def _is_engineering_selection(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("schema") == ENGINEERING_SELECTION_SCHEMA
        and isinstance(value.get("selections"), list)
    )


def _is_viewer_session(value: object) -> bool:
    return (
        isinstance(value, RuntimeHandleRef)
        and value.data_type_id == VIEWER_SESSION_DATA_TYPE_ID
        and value.kind == COREX_VIEWER_SESSION_HANDLE_KIND
    )
























CORE_DATA_TYPE_FAMILIES = (
    DataTypeFamilySpec("graph", "Graph Data", "data.graph", "data"),
    DataTypeFamilySpec("scalar", "Scalar", "data.scalar", "data"),
    DataTypeFamilySpec("container", "Collection", "data.collection", "data"),
    DataTypeFamilySpec("interval", "Interval", "data.interval", "data"),
    DataTypeFamilySpec("corex_data", "COREX Data", "data.corex", "data"),
    DataTypeFamilySpec("runtime_ref", "Runtime Reference", "data.runtime", "link"),
    DataTypeFamilySpec("engineering", "Engineering", "data.engineering", "model"),
    DataTypeFamilySpec("viewer", "Viewer", "data.viewer", "viewer"),
)

_GRAPH_PARENT = (GRAPH_DATA_TYPE_ID,)

CORE_DATA_TYPES = (
    DataTypeSpec(
        GRAPH_DATA_TYPE_ID,
        "Graph Data",
        "graph",
        _is_any,
        abstract=True,
        carriers=frozenset({"native", "inline", "handle", "artifact"}),
    ),
    DataTypeSpec(
        BOOLEAN_DATA_TYPE_ID,
        "Boolean",
        "scalar",
        lambda value: isinstance(value, bool),
        _coerce_bool,
        parents=_GRAPH_PARENT,
        persistence="inline",
    ),
    DataTypeSpec(
        INTEGER_DATA_TYPE_ID,
        "Integer",
        "scalar",
        _is_int,
        _coerce_int,
        parents=_GRAPH_PARENT,
        persistence="inline",
    ),
    DataTypeSpec(
        DOUBLE_DATA_TYPE_ID,
        "Number",
        "scalar",
        _is_real,
        _coerce_double,
        parents=_GRAPH_PARENT,
        persistence="inline",
    ),
    DataTypeSpec(
        STRING_DATA_TYPE_ID,
        "Text",
        "scalar",
        lambda value: isinstance(value, str),
        str,
        parents=_GRAPH_PARENT,
        persistence="inline",
    ),
    DataTypeSpec(
        GRAPH_DICTIONARY_DATA_TYPE_ID,
        "Dictionary",
        "container",
        lambda value: _is_json_container(value, dict),
        parents=_GRAPH_PARENT,
    ),
    DataTypeSpec(
        GRAPH_ARRAY_DATA_TYPE_ID,
        "Array",
        "container",
        lambda value: _is_json_container(value, list),
        parents=_GRAPH_PARENT,
    ),
    DataTypeSpec(
        INTERVAL_1D_GRAPH_DATA_TYPE_ID,
        "Interval 1D",
        "interval",
        lambda value: isinstance(value, Interval1D),
        coerce_interval_1d,
        parents=_GRAPH_PARENT,
        carriers=frozenset({"inline"}),
        persistence="inline",
    ),
    DataTypeSpec(
        PATH_DATA_TYPE_ID,
        "Path",
        "corex_data",
        _is_path,
        _coerce_path,
        parents=_GRAPH_PARENT,
        carriers=frozenset({"native", "artifact"}),
    ),
    DataTypeSpec(
        JSON_DATA_TYPE_ID,
        "JSON",
        "corex_data",
        _is_json_value,
        parents=_GRAPH_PARENT,
        persistence="inline",
    ),
    DataTypeSpec(
        STRING_LIST_DATA_TYPE_ID,
        "Text List",
        "corex_data",
        _is_string_list,
        parents=_GRAPH_PARENT,
        persistence="inline",
    ),
    DataTypeSpec(
        ARRAY_DATA_REF_TYPE_ID,
        "Array Data",
        "runtime_ref",
        lambda value: isinstance(value, ArrayDataRef),
        parents=_GRAPH_PARENT,
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        ARRAY_SLICE_2D_REF_TYPE_ID,
        "Array Slice 2D",
        "runtime_ref",
        lambda value: isinstance(value, ArraySlice2DRef),
        parents=_GRAPH_PARENT,
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        TABULAR_DATA_REF_TYPE_ID,
        "Tabular Data",
        "runtime_ref",
        lambda value: isinstance(value, TabularDataRef),
        parents=_GRAPH_PARENT,
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        TABULAR_WINDOW_REF_TYPE_ID,
        "Tabular Window",
        "runtime_ref",
        lambda value: isinstance(value, TabularWindowRef),
        parents=_GRAPH_PARENT,
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        CLIPPABLE_GRAPH_DATA_TYPE_ID,
        "Clippable Graph Data",
        "engineering",
        _is_any,
        parents=_GRAPH_PARENT,
        abstract=True,
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        ENGINEERING_SCENE_DATA_TYPE_ID,
        "Engineering Scene",
        "engineering",
        _is_engineering_scene,
        parents=(CLIPPABLE_GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        ENGINEERING_SELECTION_SET_DATA_TYPE_ID,
        "Engineering Selection Set",
        "engineering",
        _is_engineering_selection,
        parents=_GRAPH_PARENT,
        persistence="inline",
    ),
    DataTypeSpec(
        VIEWER_SESSION_DATA_TYPE_ID,
        "Viewer Session",
        "viewer",
        _is_viewer_session,
        parents=_GRAPH_PARENT,
        carriers=frozenset({"handle"}),
    ),
)

CORE_DATA_CONVERSIONS = ()

__all__ = [
    "ARRAY_DATA_REF_TYPE_ID",
    "ARRAY_SLICE_2D_REF_TYPE_ID",
    "BOOLEAN_DATA_TYPE_ID",
    "CLIPPABLE_GRAPH_DATA_TYPE_ID",
    "CORE_DATA_CONVERSIONS",
    "CORE_DATA_TYPE_FAMILIES",
    "CORE_DATA_TYPE_OWNER_ID",
    "CORE_DATA_TYPE_OWNER_VERSION",
    "CORE_DATA_TYPES",
    "DOUBLE_DATA_TYPE_ID",
    "ENGINEERING_SCENE_DATA_TYPE_ID",
    "ENGINEERING_SELECTION_SET_DATA_TYPE_ID",
    "GRAPH_ARRAY_DATA_TYPE_ID",
    "GRAPH_DATA_TYPE_ID",
    "GRAPH_DICTIONARY_DATA_TYPE_ID",
    "INTEGER_DATA_TYPE_ID",
    "INTERVAL_1D_GRAPH_DATA_TYPE_ID",
    "JSON_DATA_TYPE_ID",
    "PATH_DATA_TYPE_ID",
    "STRING_DATA_TYPE_ID",
    "STRING_LIST_DATA_TYPE_ID",
    "TABULAR_DATA_REF_TYPE_ID",
    "TABULAR_WINDOW_REF_TYPE_ID",
    "VIEWER_SESSION_DATA_TYPE_ID",
]
