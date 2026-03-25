from __future__ import annotations

import copy
import json
import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ea_node_editor.execution.dpf_runtime_service import (
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
)
from ea_node_editor.nodes.types import ExecutionContext, PropertySpec, RuntimeHandleRef

DPF_NODE_CATEGORY = "Ansys DPF"
DPF_RESULT_FILE_NODE_TYPE_ID = "dpf.result_file"
DPF_MODEL_NODE_TYPE_ID = "dpf.model"
DPF_MESH_SCOPING_NODE_TYPE_ID = "dpf.scoping.mesh"
DPF_TIME_SCOPING_NODE_TYPE_ID = "dpf.scoping.time"

DPF_OUTPUT_MODE_MEMORY = "memory"
DPF_OUTPUT_MODE_STORED = "stored"
DPF_OUTPUT_MODE_BOTH = "both"
DPF_OUTPUT_MODE_VALUES = (
    DPF_OUTPUT_MODE_MEMORY,
    DPF_OUTPUT_MODE_STORED,
    DPF_OUTPUT_MODE_BOTH,
)

DPF_MESH_SELECTION_NAMED_SELECTION = "named_selection"
DPF_MESH_SELECTION_NODE_IDS = "node_ids"
DPF_MESH_SELECTION_ELEMENT_IDS = "element_ids"
DPF_MESH_SELECTION_VALUES = (
    DPF_MESH_SELECTION_NAMED_SELECTION,
    DPF_MESH_SELECTION_NODE_IDS,
    DPF_MESH_SELECTION_ELEMENT_IDS,
)

DPF_LOCATION_AUTO = "auto"
DPF_LOCATION_NODAL = "Nodal"
DPF_LOCATION_ELEMENTAL = "Elemental"
DPF_LOCATION_VALUES = (
    DPF_LOCATION_AUTO,
    "nodal",
    "elemental",
)

DPF_SCOPING_KIND_MESH = "mesh"
DPF_SCOPING_KIND_TIME = "time"

_TOKEN_SPLIT_PATTERN = re.compile(r"[\s,;]+")


@dataclass(slots=True, frozen=True)
class ResolvedTimeSelection:
    set_ids: tuple[int, ...]
    time_values: tuple[float, ...]


def dpf_output_mode_property(*, default: str = DPF_OUTPUT_MODE_MEMORY) -> PropertySpec:
    return PropertySpec(
        "output_mode",
        "enum",
        normalize_dpf_output_mode(default),
        "Output Mode",
        enum_values=DPF_OUTPUT_MODE_VALUES,
        inspector_editor="enum",
    )


def require_dpf_runtime_service(ctx: ExecutionContext, *, node_name: str) -> Any:
    worker_services = ctx.worker_services
    if worker_services is None:
        raise RuntimeError(f"{node_name} requires worker services.")
    return worker_services.dpf_runtime_service


def normalize_dpf_output_mode(value: Any, *, default: str = DPF_OUTPUT_MODE_MEMORY) -> str:
    normalized_default = str(default or DPF_OUTPUT_MODE_MEMORY).strip().lower()
    if normalized_default not in DPF_OUTPUT_MODE_VALUES:
        normalized_default = DPF_OUTPUT_MODE_MEMORY
    normalized = str(value or normalized_default).strip().lower()
    if normalized not in DPF_OUTPUT_MODE_VALUES:
        raise ValueError(
            "DPF output_mode must be one of "
            f"{', '.join(DPF_OUTPUT_MODE_VALUES)}."
        )
    return normalized


def normalize_result_file_path(
    ctx: ExecutionContext,
    *,
    input_key: str = "path",
    property_key: str = "path",
    node_name: str,
) -> Path:
    for candidate in (ctx.inputs.get(input_key), ctx.properties.get(property_key)):
        path = _resolve_candidate_path(ctx, candidate)
        if path is not None:
            return path
    raise ValueError(f"{node_name} requires a non-empty Mechanical result-file path.")


def resolve_model_handle_and_object(
    ctx: ExecutionContext,
    value: Any,
    *,
    node_name: str,
) -> tuple[RuntimeHandleRef, Any]:
    service = require_dpf_runtime_service(ctx, node_name=node_name)
    model_ref = service.load_model(value)
    model = ctx.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
    return model_ref, model


def normalize_int_values(field_name: str, value: Any) -> tuple[int, ...]:
    normalized: list[int] = []
    for item in _iter_tokens(value):
        if isinstance(item, bool):
            raise TypeError(f"{field_name} values must be integers")
        try:
            normalized.append(int(item))
        except (TypeError, ValueError) as exc:
            raise TypeError(f"{field_name} values must be integers") from exc
    return tuple(normalized)


def normalize_float_values(field_name: str, value: Any) -> tuple[float, ...]:
    normalized: list[float] = []
    for item in _iter_tokens(value):
        if isinstance(item, bool):
            raise TypeError(f"{field_name} values must be numeric")
        try:
            normalized.append(float(item))
        except (TypeError, ValueError) as exc:
            raise TypeError(f"{field_name} values must be numeric") from exc
    return tuple(normalized)


def normalize_mesh_selection_mode(value: Any) -> str:
    normalized = str(value or DPF_MESH_SELECTION_NAMED_SELECTION).strip().lower()
    if normalized not in DPF_MESH_SELECTION_VALUES:
        raise ValueError(
            "selection_mode must be one of "
            f"{', '.join(DPF_MESH_SELECTION_VALUES)}."
        )
    return normalized


def normalize_location_choice(value: Any) -> str:
    normalized = str(value or DPF_LOCATION_AUTO).strip().lower()
    if normalized == DPF_LOCATION_AUTO:
        return DPF_LOCATION_AUTO
    if normalized == "nodal":
        return DPF_LOCATION_NODAL
    if normalized == "elemental":
        return DPF_LOCATION_ELEMENTAL
    raise ValueError("location must be one of auto, nodal, or elemental")


def resolve_named_selection(model: Any, value: Any, *, node_name: str) -> tuple[str, Any]:
    requested = str(value or "").strip()
    if not requested:
        raise ValueError(f"{node_name} requires a named_selection when selection_mode is named_selection.")
    available = [
        str(item).strip()
        for item in getattr(model.metadata, "available_named_selections", ())
        if str(item).strip()
    ]
    match = _match_casefolded(requested, available)
    if not match:
        raise ValueError(
            f"{node_name} named selection was not found: {requested!r}."
        )
    return match, model.metadata.named_selection(match)


def resolve_mesh_location(
    *,
    selection_mode: str,
    location_choice: str,
    scoping: Any | None = None,
) -> str:
    if selection_mode == DPF_MESH_SELECTION_NODE_IDS:
        return _validated_location_choice(location_choice, expected=DPF_LOCATION_NODAL)
    if selection_mode == DPF_MESH_SELECTION_ELEMENT_IDS:
        return _validated_location_choice(location_choice, expected=DPF_LOCATION_ELEMENTAL)

    if scoping is None:
        raise ValueError("named-selection mesh scoping requires a DPF scoping object")
    location = str(getattr(scoping, "location", "")).strip()
    if not location:
        raise ValueError("named-selection mesh scoping did not provide a location")
    if location_choice != DPF_LOCATION_AUTO and location_choice != location:
        raise ValueError(
            "location does not match the resolved named-selection scoping location: "
            f"{location_choice!r} != {location!r}"
        )
    return location


def resolve_time_selection(
    *,
    model: Any | None,
    set_ids_value: Any,
    time_values_value: Any,
    require_any: bool,
    node_name: str,
) -> ResolvedTimeSelection:
    set_ids = normalize_int_values("set_ids", set_ids_value)
    time_values = normalize_float_values("time_values", time_values_value)
    if time_values and model is None:
        raise ValueError(f"{node_name} requires a model input when time_values are provided.")

    if model is not None:
        n_sets = int(getattr(model.metadata.time_freq_support, "n_sets", 0))
        for set_id in set_ids:
            if set_id < 1 or set_id > n_sets:
                raise ValueError(
                    f"{node_name} set_ids must stay within 1..{n_sets} for the selected model."
                )

    resolved_set_ids = list(set_ids)
    if time_values:
        available_values = _model_time_values(model)
        for requested in time_values:
            resolved_set_ids.append(_match_time_value_to_set_id(requested, available_values, node_name=node_name))

    unique_set_ids: list[int] = []
    seen: set[int] = set()
    for set_id in resolved_set_ids:
        if set_id in seen:
            continue
        unique_set_ids.append(set_id)
        seen.add(set_id)

    if require_any and not unique_set_ids:
        raise ValueError(f"{node_name} requires at least one set_ids or time_values entry.")
    return ResolvedTimeSelection(set_ids=tuple(unique_set_ids), time_values=time_values)


def build_mesh_scoping_metadata(
    *,
    model_ref: RuntimeHandleRef | None,
    selection_mode: str,
    location: str,
    ids: Iterable[int],
    named_selection: str = "",
    time_selection: ResolvedTimeSelection | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "scoping_kind": DPF_SCOPING_KIND_MESH,
        "selection_mode": selection_mode,
        "location": location,
        "ids": [int(item) for item in ids],
    }
    if model_ref is not None:
        metadata["model_handle_id"] = model_ref.handle_id
    if named_selection:
        metadata["named_selection"] = named_selection
    if time_selection is not None:
        metadata["set_ids"] = [int(item) for item in time_selection.set_ids]
        metadata["time_values"] = [float(item) for item in time_selection.time_values]
    return metadata


def build_time_scoping_metadata(
    *,
    model_ref: RuntimeHandleRef | None,
    time_selection: ResolvedTimeSelection,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "scoping_kind": DPF_SCOPING_KIND_TIME,
        "selection_mode": _time_selection_mode(time_selection),
        "set_ids": [int(item) for item in time_selection.set_ids],
        "time_values": [float(item) for item in time_selection.time_values],
    }
    if model_ref is not None:
        metadata["model_handle_id"] = model_ref.handle_id
    return metadata


def clone_handle_with_metadata(
    ctx: ExecutionContext,
    runtime_ref: RuntimeHandleRef,
    *,
    expected_kind: str,
    metadata: dict[str, Any],
    release_original: bool = False,
) -> RuntimeHandleRef:
    resolved = ctx.resolve_handle(runtime_ref, expected_kind=expected_kind)
    combined_metadata = copy.deepcopy(dict(runtime_ref.metadata))
    combined_metadata.update(copy.deepcopy(metadata))
    cloned_ref = ctx.register_handle(
        resolved,
        kind=expected_kind,
        owner_scope=runtime_ref.owner_scope,
        metadata=combined_metadata,
    )
    if release_original and runtime_ref.owner_scope == f"run:{ctx.run_id}":
        ctx.release_handle(runtime_ref)
    return cloned_ref


def is_result_file_handle(value: Any) -> bool:
    runtime_ref = _runtime_handle_ref(value)
    return runtime_ref is not None and runtime_ref.kind == DPF_RESULT_FILE_HANDLE_KIND


def is_model_handle(value: Any) -> bool:
    runtime_ref = _runtime_handle_ref(value)
    return runtime_ref is not None and runtime_ref.kind == DPF_MODEL_HANDLE_KIND


def is_mesh_scoping_handle(value: Any) -> bool:
    runtime_ref = _runtime_handle_ref(value)
    return runtime_ref is not None and runtime_ref.kind == DPF_MESH_SCOPING_HANDLE_KIND


def is_time_scoping_handle(value: Any) -> bool:
    runtime_ref = _runtime_handle_ref(value)
    return runtime_ref is not None and runtime_ref.kind == DPF_TIME_SCOPING_HANDLE_KIND


def _resolve_candidate_path(ctx: ExecutionContext, value: Any) -> Path | None:
    if value is None:
        return None
    resolved = ctx.resolve_path_value(value)
    if resolved is not None:
        return resolved.expanduser().resolve(strict=False)

    text = str(value).strip()
    if not text:
        return None
    candidate = Path(text).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)

    project_root = _project_root(ctx.project_path)
    if project_root is not None:
        return (project_root / candidate).resolve(strict=False)
    return candidate.resolve(strict=False)


def _project_root(project_path: str) -> Path | None:
    text = str(project_path or "").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if path.suffix:
        return path.parent
    return path


def _iter_tokens(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, Sequence) and not isinstance(parsed, (str, bytes, bytearray)):
            return tuple(parsed)
        if parsed is not None and not isinstance(parsed, dict):
            return (parsed,)
        return tuple(token for token in _TOKEN_SPLIT_PATTERN.split(text) if token)
    return (value,)


def _match_casefolded(requested: str, values: Iterable[str]) -> str:
    normalized_requested = requested.casefold()
    for value in values:
        if value.casefold() == normalized_requested:
            return value
    return ""


def _validated_location_choice(location_choice: str, *, expected: str) -> str:
    if location_choice == DPF_LOCATION_AUTO:
        return expected
    if location_choice != expected:
        raise ValueError(f"location must resolve to {expected}")
    return expected


def _model_time_values(model: Any | None) -> tuple[float, ...]:
    if model is None:
        return ()
    support = getattr(model.metadata, "time_freq_support", None)
    frequencies = getattr(support, "time_frequencies", None)
    data = getattr(frequencies, "data", ())
    return tuple(float(value) for value in data)


def _match_time_value_to_set_id(value: float, available_values: tuple[float, ...], *, node_name: str) -> int:
    for index, candidate in enumerate(available_values, start=1):
        if math.isclose(float(value), float(candidate), rel_tol=1e-6, abs_tol=1e-9):
            return index
    raise ValueError(
        f"{node_name} time_values entry {value!r} did not match any available model set/time value."
    )


def _time_selection_mode(time_selection: ResolvedTimeSelection) -> str:
    modes: list[str] = []
    if time_selection.set_ids:
        modes.append("set_ids")
    if time_selection.time_values:
        modes.append("time_values")
    return "+".join(modes) if modes else "set_ids"


def _runtime_handle_ref(value: Any) -> RuntimeHandleRef | None:
    if isinstance(value, RuntimeHandleRef):
        return value
    return None


__all__ = [
    "DPF_LOCATION_AUTO",
    "DPF_LOCATION_ELEMENTAL",
    "DPF_LOCATION_NODAL",
    "DPF_LOCATION_VALUES",
    "DPF_MESH_SCOPING_NODE_TYPE_ID",
    "DPF_MESH_SELECTION_ELEMENT_IDS",
    "DPF_MESH_SELECTION_NAMED_SELECTION",
    "DPF_MESH_SELECTION_NODE_IDS",
    "DPF_MESH_SELECTION_VALUES",
    "DPF_MODEL_NODE_TYPE_ID",
    "DPF_NODE_CATEGORY",
    "DPF_OUTPUT_MODE_BOTH",
    "DPF_OUTPUT_MODE_MEMORY",
    "DPF_OUTPUT_MODE_STORED",
    "DPF_OUTPUT_MODE_VALUES",
    "DPF_RESULT_FILE_NODE_TYPE_ID",
    "DPF_SCOPING_KIND_MESH",
    "DPF_SCOPING_KIND_TIME",
    "DPF_TIME_SCOPING_NODE_TYPE_ID",
    "ResolvedTimeSelection",
    "build_mesh_scoping_metadata",
    "build_time_scoping_metadata",
    "clone_handle_with_metadata",
    "dpf_output_mode_property",
    "is_mesh_scoping_handle",
    "is_model_handle",
    "is_result_file_handle",
    "is_time_scoping_handle",
    "normalize_dpf_output_mode",
    "normalize_float_values",
    "normalize_int_values",
    "normalize_location_choice",
    "normalize_mesh_selection_mode",
    "normalize_result_file_path",
    "require_dpf_runtime_service",
    "resolve_mesh_location",
    "resolve_model_handle_and_object",
    "resolve_named_selection",
    "resolve_time_selection",
]
