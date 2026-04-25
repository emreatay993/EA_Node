from __future__ import annotations

import copy
import importlib
import json
import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ea_node_editor.nodes.dpf_runtime_contracts import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
)
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.nodes.node_specs import (
    DPF_DATA_SOURCES_DATA_TYPE,
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_OBJECT_HANDLE_DATA_TYPE,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_STREAMS_CONTAINER_DATA_TYPE,
    DPF_VIEW_SESSION_DATA_TYPE,
    DPF_WORKFLOW_DATA_TYPE,
    DpfOperatorSelectorCondition,
    DpfOperatorSourceSpec,
    DpfOperatorVariantSpec,
    DpfPinSourceSpec,
    NodeTypeSpec,
    PropertySpec,
    normalize_dpf_type_id,
)
from ea_node_editor.runtime_contracts import RuntimeHandleRef

DPF_NODE_CATEGORY = "Ansys DPF"
DPF_NODE_CATEGORY_PATH = (DPF_NODE_CATEGORY,)
DPF_COMPUTE_CATEGORY_PATH = (DPF_NODE_CATEGORY, "Compute")
DPF_VIEWER_CATEGORY_PATH = (DPF_NODE_CATEGORY, "Viewer")
DPF_RESULT_FILE_NODE_TYPE_ID = "dpf.result_file"
DPF_MODEL_NODE_TYPE_ID = "dpf.model"
DPF_MESH_SCOPING_NODE_TYPE_ID = "dpf.scoping.mesh"
DPF_TIME_SCOPING_NODE_TYPE_ID = "dpf.scoping.time"
DPF_RESULT_FIELD_NODE_TYPE_ID = "dpf.result_field"
DPF_FIELD_OPS_NODE_TYPE_ID = "dpf.field_ops"
DPF_MESH_EXTRACT_NODE_TYPE_ID = "dpf.mesh_extract"
DPF_EXPORT_NODE_TYPE_ID = "dpf.export"
DPF_VIEWER_NODE_TYPE_ID = "dpf.viewer"

DPF_OUTPUT_MODE_MEMORY = "memory"
DPF_OUTPUT_MODE_STORED = "stored"
DPF_OUTPUT_MODE_BOTH = "both"
DPF_OUTPUT_MODE_VALUES = (
    DPF_OUTPUT_MODE_MEMORY,
    DPF_OUTPUT_MODE_STORED,
    DPF_OUTPUT_MODE_BOTH,
)

DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY = "focus_only"
DPF_VIEWER_LIVE_POLICY_KEEP_LIVE = "keep_live"
DPF_VIEWER_LIVE_POLICY_VALUES = (
    DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY,
    DPF_VIEWER_LIVE_POLICY_KEEP_LIVE,
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
DPF_FIELD_LOCATION_ELEMENTAL_NODAL = "ElementalNodal"
DPF_RESULT_FIELD_LOCATION_VALUES = (
    DPF_LOCATION_AUTO,
    "nodal",
    "elemental",
    "elemental_nodal",
)
DPF_TARGET_FIELD_LOCATION_VALUES = (
    "nodal",
    "elemental",
    "elemental_nodal",
)

DPF_FIELD_OP_NORM = "norm"
DPF_FIELD_OP_CONVERT_LOCATION = "convert_location"
DPF_FIELD_OP_MIN_MAX = "min_max"
DPF_FIELD_OPERATION_VALUES = (
    DPF_FIELD_OP_NORM,
    DPF_FIELD_OP_CONVERT_LOCATION,
    DPF_FIELD_OP_MIN_MAX,
)

DPF_EXPORT_FORMAT_VALUES = ("csv", "png", "vtu", "vtm")

DPF_SCOPING_KIND_MESH = "mesh"
DPF_SCOPING_KIND_TIME = "time"

_TOKEN_SPLIT_PATTERN = re.compile(r"[\s,;]+")
_INVALID_ARTIFACT_TOKEN_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(slots=True, frozen=True)
class ResolvedTimeSelection:
    set_ids: tuple[int, ...]
    time_values: tuple[float, ...]


@dataclass(slots=True, frozen=True)
class ResolvedActiveSet:
    set_id: int
    time_value: float | None
    time_scoping_ref: RuntimeHandleRef | None = None


DPF_TIME_SELECTION_EXCLUSIVE_GROUP = "time_selection"
DPF_RESULT_FIELD_OPERATOR_VARIANT_KEY = "result"
DPF_FIELD_OPS_VARIANT_NORM = "norm"
DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL = "convert_location.nodal"
DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL = "convert_location.elemental"
DPF_FIELD_OPS_VARIANT_MIN_MAX = "min_max"

DPF_NODE_SOURCE_METADATA_BY_TYPE_ID: dict[str, DpfOperatorSourceSpec] = {
    DPF_RESULT_FIELD_NODE_TYPE_ID: DpfOperatorSourceSpec(
        variants=(
            DpfOperatorVariantSpec(
                key=DPF_RESULT_FIELD_OPERATOR_VARIANT_KEY,
                operator_name_template="result.{result_name}",
            ),
        ),
    ),
    DPF_FIELD_OPS_NODE_TYPE_ID: DpfOperatorSourceSpec(
        variants=(
            DpfOperatorVariantSpec(
                key=DPF_FIELD_OPS_VARIANT_NORM,
                operator_name="math.norm_fc",
                selector_conditions=(
                    DpfOperatorSelectorCondition(
                        property_key="operation",
                        values=(DPF_FIELD_OP_NORM,),
                    ),
                ),
            ),
            DpfOperatorVariantSpec(
                key=DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL,
                operator_name="averaging.to_nodal_fc",
                selector_conditions=(
                    DpfOperatorSelectorCondition(
                        property_key="operation",
                        values=(DPF_FIELD_OP_CONVERT_LOCATION,),
                    ),
                    DpfOperatorSelectorCondition(
                        property_key="location",
                        values=("nodal",),
                    ),
                ),
            ),
            DpfOperatorVariantSpec(
                key=DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL,
                operator_name="averaging.to_elemental_fc",
                selector_conditions=(
                    DpfOperatorSelectorCondition(
                        property_key="operation",
                        values=(DPF_FIELD_OP_CONVERT_LOCATION,),
                    ),
                    DpfOperatorSelectorCondition(
                        property_key="location",
                        values=("elemental",),
                    ),
                ),
            ),
            DpfOperatorVariantSpec(
                key=DPF_FIELD_OPS_VARIANT_MIN_MAX,
                operator_name="min_max.min_max_fc",
                selector_conditions=(
                    DpfOperatorSelectorCondition(
                        property_key="operation",
                        values=(DPF_FIELD_OP_MIN_MAX,),
                    ),
                ),
            ),
        ),
    ),
}

DPF_PORT_SOURCE_METADATA_BY_TYPE_ID: dict[str, dict[str, DpfPinSourceSpec]] = {
    DPF_RESULT_FIELD_NODE_TYPE_ID: {
        "model": DpfPinSourceSpec(
            pin_name="data_sources",
            pin_direction="input",
            value_origin="port",
            value_key="model",
            data_type=DPF_MODEL_DATA_TYPE,
            presence="required",
            omission_semantics="disallowed",
        ),
        "mesh_scoping": DpfPinSourceSpec(
            pin_name="mesh_scoping",
            pin_direction="input",
            value_origin="port",
            value_key="mesh_scoping",
            data_type=DPF_SCOPING_DATA_TYPE,
            presence="optional",
            omission_semantics="skip",
        ),
        "time_scoping": DpfPinSourceSpec(
            pin_name="time_scoping",
            pin_direction="input",
            value_origin="port",
            value_key="time_scoping",
            data_type=DPF_SCOPING_DATA_TYPE,
            presence="optional",
            omission_semantics="skip",
            exclusive_group=DPF_TIME_SELECTION_EXCLUSIVE_GROUP,
        ),
        "field": DpfPinSourceSpec(
            pin_name="fields_container",
            pin_direction="output",
            value_origin="port",
            value_key="field",
            data_type=DPF_FIELD_DATA_TYPE,
        ),
    },
    DPF_FIELD_OPS_NODE_TYPE_ID: {
        "field": DpfPinSourceSpec(
            pin_name="fields_container",
            pin_direction="input",
            value_origin="port",
            value_key="field",
            data_type=DPF_FIELD_DATA_TYPE,
            presence="required",
            omission_semantics="disallowed",
            variant_keys=(
                DPF_FIELD_OPS_VARIANT_NORM,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL,
                DPF_FIELD_OPS_VARIANT_MIN_MAX,
            ),
        ),
        "model": DpfPinSourceSpec(
            pin_name="mesh",
            pin_direction="input",
            value_origin="port",
            value_key="model",
            data_type=DPF_MODEL_DATA_TYPE,
            presence="required",
            omission_semantics="disallowed",
            variant_keys=(
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL,
            ),
        ),
        "field_out": DpfPinSourceSpec(
            pin_name="fields_container",
            pin_direction="output",
            value_origin="port",
            value_key="field_out",
            data_type=DPF_FIELD_DATA_TYPE,
            variant_keys=(
                DPF_FIELD_OPS_VARIANT_NORM,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL,
            ),
        ),
        "field_min": DpfPinSourceSpec(
            pin_name="field_min",
            pin_direction="output",
            value_origin="port",
            value_key="field_min",
            data_type=DPF_FIELD_DATA_TYPE,
            variant_keys=(DPF_FIELD_OPS_VARIANT_MIN_MAX,),
        ),
        "field_max": DpfPinSourceSpec(
            pin_name="field_max",
            pin_direction="output",
            value_origin="port",
            value_key="field_max",
            data_type=DPF_FIELD_DATA_TYPE,
            variant_keys=(DPF_FIELD_OPS_VARIANT_MIN_MAX,),
        ),
    },
}

DPF_PROPERTY_SOURCE_METADATA_BY_TYPE_ID: dict[str, dict[str, DpfPinSourceSpec]] = {
    DPF_RESULT_FIELD_NODE_TYPE_ID: {
        "location": DpfPinSourceSpec(
            pin_name="requested_location",
            pin_direction="input",
            value_origin="property",
            value_key="location",
            data_type=DPF_FIELD_DATA_TYPE,
            presence="optional",
            omission_semantics="operator_default",
        ),
        "set_ids": DpfPinSourceSpec(
            pin_name="time_scoping",
            pin_direction="input",
            value_origin="property",
            value_key="set_ids",
            data_type=DPF_SCOPING_DATA_TYPE,
            presence="optional",
            omission_semantics="skip",
            exclusive_group=DPF_TIME_SELECTION_EXCLUSIVE_GROUP,
        ),
        "time_values": DpfPinSourceSpec(
            pin_name="time_scoping",
            pin_direction="input",
            value_origin="property",
            value_key="time_values",
            data_type=DPF_SCOPING_DATA_TYPE,
            presence="optional",
            omission_semantics="skip",
            exclusive_group=DPF_TIME_SELECTION_EXCLUSIVE_GROUP,
        ),
    },
}


def normalize_dpf_descriptor_spec(spec: NodeTypeSpec) -> NodeTypeSpec:
    node_source = DPF_NODE_SOURCE_METADATA_BY_TYPE_ID.get(spec.type_id)
    port_sources = DPF_PORT_SOURCE_METADATA_BY_TYPE_ID.get(spec.type_id, {})
    property_sources = DPF_PROPERTY_SOURCE_METADATA_BY_TYPE_ID.get(spec.type_id, {})
    if node_source is None and not port_sources and not property_sources:
        return spec
    return replace(
        spec,
        ports=tuple(
            replace(
                port,
                source_metadata=port_sources.get(port.key, port.source_metadata),
            )
            for port in spec.ports
        ),
        properties=tuple(
            replace(
                prop,
                source_metadata=property_sources.get(prop.key, prop.source_metadata),
            )
            for prop in spec.properties
        ),
        source_metadata=node_source if node_source is not None else spec.source_metadata,
    )


def normalize_dpf_live_type_name(type_name: object) -> str:
    normalized = str(type_name or "").strip().lower()
    if not normalized:
        return DPF_OBJECT_HANDLE_DATA_TYPE
    if normalized == "bool":
        return "bool"
    if normalized == "int32":
        return "int"
    if normalized == "double":
        return "float"
    if normalized == "string":
        return "str"
    if normalized.startswith("vector<"):
        return "json"
    if normalized.startswith("enum ") or normalized.endswith("_enum"):
        return "int"
    if normalized == "any":
        return "any"
    if normalized == "fields_container":
        return DPF_FIELDS_CONTAINER_DATA_TYPE
    if normalized == "data_sources":
        return DPF_DATA_SOURCES_DATA_TYPE
    if normalized == "streams_container":
        return DPF_STREAMS_CONTAINER_DATA_TYPE
    if normalized == "workflow":
        return DPF_WORKFLOW_DATA_TYPE
    if "meshed_region" in normalized or normalized == "mesh":
        return DPF_MESH_DATA_TYPE
    canonical = normalize_dpf_type_id(normalized)
    if canonical != DPF_OBJECT_HANDLE_DATA_TYPE:
        return canonical
    return DPF_OBJECT_HANDLE_DATA_TYPE


def humanize_dpf_symbol_name(value: object) -> str:
    token = re.sub(r"[^0-9A-Za-z]+", " ", str(value or "").strip().replace("_", " "))
    token = re.sub(r"\s+", " ", token).strip()
    if not token:
        return "DPF Value"
    return " ".join(part.capitalize() for part in token.split(" "))


def dpf_output_mode_property(
    *, default: str = DPF_OUTPUT_MODE_MEMORY, group: str = "Post"
) -> PropertySpec:
    return PropertySpec(
        "output_mode",
        "enum",
        normalize_dpf_output_mode(default),
        "Output Mode",
        enum_values=DPF_OUTPUT_MODE_VALUES,
        inspector_editor="enum",
        group=group,
    )


def require_dpf_runtime_service(ctx: ExecutionContext, *, node_name: str) -> Any:
    worker_services = ctx.worker_services
    if worker_services is None:
        raise RuntimeError(f"{node_name} requires worker services.")
    service = getattr(worker_services, "dpf_runtime_service", None)
    if service is None:
        raise RuntimeError(f"{node_name} requires DPF runtime services.")
    return service


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


def normalize_dpf_viewer_live_policy(
    value: Any,
    *,
    default: str = DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY,
) -> str:
    normalized_default = str(default or DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY).strip().lower()
    if normalized_default not in DPF_VIEWER_LIVE_POLICY_VALUES:
        normalized_default = DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY
    normalized = str(value or normalized_default).strip().lower()
    if normalized not in DPF_VIEWER_LIVE_POLICY_VALUES:
        raise ValueError(
            "viewer_live_policy must be one of "
            f"{', '.join(DPF_VIEWER_LIVE_POLICY_VALUES)}."
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


def normalize_result_field_location(value: Any) -> str:
    normalized = str(value or DPF_LOCATION_AUTO).strip().lower()
    if normalized == DPF_LOCATION_AUTO:
        return DPF_LOCATION_AUTO
    if normalized == "nodal":
        return DPF_LOCATION_NODAL
    if normalized == "elemental":
        return DPF_LOCATION_ELEMENTAL
    if normalized in {"elemental_nodal", "elementalnodal"}:
        return DPF_FIELD_LOCATION_ELEMENTAL_NODAL
    raise ValueError("location must be one of auto, nodal, elemental, or elemental_nodal")


def normalize_target_field_location(value: Any) -> str:
    normalized = normalize_result_field_location(value)
    if normalized == DPF_LOCATION_AUTO:
        raise ValueError("location must be one of nodal, elemental, or elemental_nodal")
    return normalized


def normalize_field_operation(value: Any) -> str:
    normalized = str(value or DPF_FIELD_OP_NORM).strip().lower()
    if normalized not in DPF_FIELD_OPERATION_VALUES:
        raise ValueError(
            "operation must be one of "
            f"{', '.join(DPF_FIELD_OPERATION_VALUES)}."
        )
    return normalized


def normalize_export_formats(value: Any) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in _iter_tokens(value):
        token = str(item).strip().lower()
        if not token:
            continue
        if token not in DPF_EXPORT_FORMAT_VALUES:
            raise ValueError(
                "export_formats must contain only "
                f"{', '.join(DPF_EXPORT_FORMAT_VALUES)}."
            )
        if token in seen:
            continue
        normalized.append(token)
        seen.add(token)
    return tuple(normalized)


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


def resolve_field_handle_and_object(
    ctx: ExecutionContext,
    value: Any,
    *,
    node_name: str,
) -> tuple[RuntimeHandleRef, Any]:
    runtime_ref = _runtime_handle_ref(value)
    if runtime_ref is None or runtime_ref.kind != DPF_FIELD_HANDLE_KIND:
        raise TypeError(f"{node_name} requires a dpf.field handle input.")
    field_value = ctx.resolve_handle(runtime_ref, expected_kind=DPF_FIELD_HANDLE_KIND)
    return runtime_ref, field_value


def resolve_single_active_set(
    ctx: ExecutionContext,
    *,
    model: Any,
    time_scoping_value: Any,
    set_ids_value: Any,
    time_values_value: Any,
    node_name: str,
) -> ResolvedActiveSet:
    if time_scoping_value is not None:
        runtime_ref = _runtime_handle_ref(time_scoping_value)
        if runtime_ref is None or runtime_ref.kind != DPF_TIME_SCOPING_HANDLE_KIND:
            raise TypeError(f"{node_name} requires a dpf.time_scoping handle when time_scoping is connected.")
        scoping = ctx.resolve_handle(runtime_ref, expected_kind=DPF_TIME_SCOPING_HANDLE_KIND)
        set_ids = _dedupe_ints(getattr(scoping, "ids", ()))
        if len(set_ids) != 1:
            raise ValueError(f"{node_name} supports exactly one active set per execution.")
        set_id = set_ids[0]
        return ResolvedActiveSet(
            set_id=set_id,
            time_value=_model_time_value_for_set_id(model, set_id),
            time_scoping_ref=runtime_ref,
        )

    time_selection = resolve_time_selection(
        model=model,
        set_ids_value=set_ids_value,
        time_values_value=time_values_value,
        require_any=False,
        node_name=node_name,
    )
    if not time_selection.set_ids:
        n_sets = int(getattr(model.metadata.time_freq_support, "n_sets", 0))
        if n_sets < 1:
            raise ValueError(f"{node_name} could not resolve an active set from the selected model.")
        return ResolvedActiveSet(set_id=1, time_value=_model_time_value_for_set_id(model, 1))
    if len(time_selection.set_ids) != 1:
        raise ValueError(f"{node_name} supports exactly one active set per execution.")
    set_id = int(time_selection.set_ids[0])
    return ResolvedActiveSet(
        set_id=set_id,
        time_value=_model_time_value_for_set_id(model, set_id),
    )


def wrap_field_handle_as_fields_container(
    ctx: ExecutionContext,
    value: Any,
    *,
    node_name: str,
) -> RuntimeHandleRef:
    field_ref, field_value = resolve_field_handle_and_object(ctx, value, node_name=node_name)
    dpf = _dpf_module()
    fields_container = dpf.FieldsContainer()
    fields_container.set_labels(["time"])
    fields_container.add_field({"time": _field_set_id(field_ref.metadata)}, field_value)
    metadata = copy.deepcopy(dict(field_ref.metadata))
    metadata.setdefault("set_ids", [_field_set_id(field_ref.metadata)])
    metadata.setdefault("field_count", 1)
    metadata.setdefault("result_name", str(field_ref.metadata.get("result_name", "")).strip())
    return ctx.register_handle(
        fields_container,
        kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        metadata=metadata,
    )


def unwrap_single_field_handle(
    ctx: ExecutionContext,
    value: Any,
    *,
    node_name: str,
    operation: str = "",
    requested_location: str = "",
    release_original: bool = False,
) -> RuntimeHandleRef:
    runtime_ref = _runtime_handle_ref(value)
    if runtime_ref is None or runtime_ref.kind != DPF_FIELDS_CONTAINER_HANDLE_KIND:
        raise TypeError(f"{node_name} requires a dpf.fields_container handle.")
    fields_container = ctx.resolve_handle(runtime_ref, expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND)
    if len(fields_container) != 1:
        raise ValueError(f"{node_name} requires a single active field.")

    metadata = build_field_handle_metadata(
        fields_container[0],
        source_metadata=runtime_ref.metadata,
        source_ref=runtime_ref,
        set_id=_fields_container_set_id(fields_container, runtime_ref.metadata),
        time_value=_field_time_value(runtime_ref.metadata),
        operation=operation or str(runtime_ref.metadata.get("operation", "")).strip(),
        requested_location=requested_location,
    )
    field_ref = ctx.register_handle(
        fields_container[0],
        kind=DPF_FIELD_HANDLE_KIND,
        metadata=metadata,
    )
    if release_original and runtime_ref.owner_scope == f"run:{ctx.run_id}":
        ctx.release_handle(runtime_ref)
    return field_ref


def clone_field_handle_with_metadata(
    ctx: ExecutionContext,
    value: Any,
    *,
    node_name: str,
    source_metadata: dict[str, Any],
    release_original: bool = False,
) -> RuntimeHandleRef:
    runtime_ref, field_value = resolve_field_handle_and_object(ctx, value, node_name=node_name)
    cloned_ref = ctx.register_handle(
        field_value,
        kind=DPF_FIELD_HANDLE_KIND,
        metadata=build_field_handle_metadata(
            field_value,
            source_metadata=source_metadata,
            source_ref=runtime_ref,
            set_id=_field_set_id(source_metadata),
            time_value=_field_time_value(source_metadata),
        ),
    )
    if release_original and runtime_ref.owner_scope == f"run:{ctx.run_id}":
        ctx.release_handle(runtime_ref)
    return cloned_ref


def build_field_handle_metadata(
    field_value: Any,
    *,
    source_metadata: dict[str, Any] | None = None,
    source_ref: RuntimeHandleRef | None = None,
    model_ref: RuntimeHandleRef | None = None,
    mesh_scoping: Any = None,
    time_scoping: Any = None,
    result_name: str = "",
    set_id: int | None = None,
    time_value: float | None = None,
    operation: str = "",
    requested_location: str = "",
) -> dict[str, Any]:
    metadata = copy.deepcopy(dict(source_metadata or {}))
    metadata.update(
        {
            "location": str(getattr(field_value, "location", "")),
            "component_count": int(getattr(field_value, "component_count", 0)),
            "entity_count": int(getattr(getattr(field_value, "scoping", None), "size", 0)),
            "unit": str(getattr(field_value, "unit", "") or ""),
            "field_count": 1,
        }
    )
    resolved_result_name = result_name or str(metadata.get("result_name", "")).strip()
    if resolved_result_name:
        metadata["result_name"] = resolved_result_name
    resolved_set_id = set_id if set_id is not None else _field_set_id(metadata)
    if resolved_set_id:
        metadata["set_id"] = int(resolved_set_id)
        metadata["set_ids"] = [int(resolved_set_id)]
    if time_value is None:
        time_value = _field_time_value(metadata)
    if time_value is not None:
        metadata["time_value"] = float(time_value)
        metadata["time_values"] = [float(time_value)]
    if source_ref is not None:
        metadata["source_handle_id"] = source_ref.handle_id
    if model_ref is not None:
        metadata["model_handle_id"] = model_ref.handle_id
    else:
        model_handle_id = str(metadata.get("model_handle_id", "")).strip()
        if model_handle_id:
            metadata["model_handle_id"] = model_handle_id
    mesh_scoping_handle_id = _handle_id_or_empty(mesh_scoping)
    if mesh_scoping_handle_id:
        metadata["mesh_scoping_handle_id"] = mesh_scoping_handle_id
    time_scoping_handle_id = _handle_id_or_empty(time_scoping)
    if time_scoping_handle_id:
        metadata["time_scoping_handle_id"] = time_scoping_handle_id
    if operation:
        metadata["operation"] = operation
    if requested_location:
        metadata["requested_location"] = requested_location
    return metadata


def normalize_export_artifact_key(value: Any, *, fallback: str) -> str:
    normalized = _INVALID_ARTIFACT_TOKEN_CHARS.sub("_", str(value or "").strip()).strip("._-")
    if normalized:
        return normalized
    fallback_key = _INVALID_ARTIFACT_TOKEN_CHARS.sub("_", str(fallback).strip()).strip("._-")
    if fallback_key:
        return fallback_key
    raise ValueError("artifact_key must contain at least one valid token character")


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


def _model_time_value_for_set_id(model: Any, set_id: int) -> float | None:
    time_values = _model_time_values(model)
    index = int(set_id) - 1
    if index < 0 or index >= len(time_values):
        return None
    return float(time_values[index])


def _time_selection_mode(time_selection: ResolvedTimeSelection) -> str:
    modes: list[str] = []
    if time_selection.set_ids:
        modes.append("set_ids")
    if time_selection.time_values:
        modes.append("time_values")
    return "+".join(modes) if modes else "set_ids"


def _fields_container_set_id(fields_container: Any, metadata: dict[str, Any]) -> int:
    set_id = _field_set_id(metadata)
    if set_id:
        return set_id
    if len(fields_container) == 0:
        return 1
    try:
        label_space = fields_container.get_label_space(0)
    except Exception:
        return 1
    try:
        return int(label_space.get("time", 1))
    except (TypeError, ValueError, AttributeError):
        return 1


def _field_set_id(metadata: dict[str, Any]) -> int:
    set_id = metadata.get("set_id")
    if set_id is not None:
        try:
            return int(set_id)
        except (TypeError, ValueError):
            pass
    set_ids = metadata.get("set_ids")
    if isinstance(set_ids, Sequence) and not isinstance(set_ids, (str, bytes, bytearray)) and set_ids:
        try:
            return int(set_ids[0])
        except (TypeError, ValueError):
            pass
    return 1


def _field_time_value(metadata: dict[str, Any]) -> float | None:
    time_value = metadata.get("time_value")
    if time_value is not None:
        try:
            return float(time_value)
        except (TypeError, ValueError):
            pass
    time_values = metadata.get("time_values")
    if isinstance(time_values, Sequence) and not isinstance(time_values, (str, bytes, bytearray)) and time_values:
        try:
            return float(time_values[0])
        except (TypeError, ValueError):
            pass
    return None


def _dedupe_ints(values: Iterable[Any]) -> tuple[int, ...]:
    resolved: list[int] = []
    seen: set[int] = set()
    for raw_value in values:
        value = int(raw_value)
        if value in seen:
            continue
        resolved.append(value)
        seen.add(value)
    return tuple(resolved)


def _handle_id_or_empty(value: Any) -> str:
    runtime_ref = _runtime_handle_ref(value)
    return runtime_ref.handle_id if runtime_ref is not None else ""


def _dpf_module() -> Any:
    try:
        return importlib.import_module("ansys.dpf.core")
    except ModuleNotFoundError as exc:
        raise RuntimeError("ansys.dpf.core is required for DPF field operations.") from exc


def _runtime_handle_ref(value: Any) -> RuntimeHandleRef | None:
    if isinstance(value, RuntimeHandleRef):
        return value
    return None


__all__ = [
    "DPF_EXPORT_FORMAT_VALUES",
    "DPF_EXPORT_NODE_TYPE_ID",
    "DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL",
    "DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL",
    "DPF_FIELD_OPS_VARIANT_MIN_MAX",
    "DPF_FIELD_OPS_VARIANT_NORM",
    "DPF_FIELD_LOCATION_ELEMENTAL_NODAL",
    "DPF_FIELD_OPERATION_VALUES",
    "DPF_FIELD_OP_CONVERT_LOCATION",
    "DPF_FIELD_OP_MIN_MAX",
    "DPF_FIELD_OP_NORM",
    "DPF_FIELD_OPS_NODE_TYPE_ID",
    "DPF_COMPUTE_CATEGORY_PATH",
    "DPF_LOCATION_AUTO",
    "DPF_LOCATION_ELEMENTAL",
    "DPF_LOCATION_NODAL",
    "DPF_LOCATION_VALUES",
    "DPF_MESH_SCOPING_NODE_TYPE_ID",
    "DPF_MESH_EXTRACT_NODE_TYPE_ID",
    "DPF_MESH_SELECTION_ELEMENT_IDS",
    "DPF_MESH_SELECTION_NAMED_SELECTION",
    "DPF_MESH_SELECTION_NODE_IDS",
    "DPF_MESH_SELECTION_VALUES",
    "DPF_MODEL_NODE_TYPE_ID",
    "DPF_NODE_CATEGORY",
    "DPF_NODE_CATEGORY_PATH",
    "DPF_OUTPUT_MODE_BOTH",
    "DPF_OUTPUT_MODE_MEMORY",
    "DPF_OUTPUT_MODE_STORED",
    "DPF_OUTPUT_MODE_VALUES",
    "DPF_VIEWER_LIVE_POLICY_FOCUS_ONLY",
    "DPF_VIEWER_LIVE_POLICY_KEEP_LIVE",
    "DPF_VIEWER_LIVE_POLICY_VALUES",
    "DPF_VIEWER_NODE_TYPE_ID",
    "DPF_VIEWER_CATEGORY_PATH",
    "DPF_RESULT_FIELD_LOCATION_VALUES",
    "DPF_RESULT_FIELD_OPERATOR_VARIANT_KEY",
    "DPF_RESULT_FIELD_NODE_TYPE_ID",
    "DPF_RESULT_FILE_NODE_TYPE_ID",
    "DPF_SCOPING_KIND_MESH",
    "DPF_SCOPING_KIND_TIME",
    "DPF_TARGET_FIELD_LOCATION_VALUES",
    "DPF_TIME_SELECTION_EXCLUSIVE_GROUP",
    "DPF_TIME_SCOPING_NODE_TYPE_ID",
    "DPF_NODE_SOURCE_METADATA_BY_TYPE_ID",
    "DPF_PORT_SOURCE_METADATA_BY_TYPE_ID",
    "DPF_PROPERTY_SOURCE_METADATA_BY_TYPE_ID",
    "ResolvedActiveSet",
    "ResolvedTimeSelection",
    "build_mesh_scoping_metadata",
    "build_field_handle_metadata",
    "build_time_scoping_metadata",
    "clone_field_handle_with_metadata",
    "clone_handle_with_metadata",
    "dpf_output_mode_property",
    "is_mesh_scoping_handle",
    "is_model_handle",
    "is_result_file_handle",
    "is_time_scoping_handle",
    "normalize_dpf_output_mode",
    "normalize_dpf_live_type_name",
    "normalize_dpf_viewer_live_policy",
    "normalize_export_artifact_key",
    "normalize_export_formats",
    "normalize_float_values",
    "normalize_field_operation",
    "normalize_int_values",
    "normalize_location_choice",
    "normalize_mesh_selection_mode",
    "normalize_dpf_descriptor_spec",
    "normalize_result_file_path",
    "normalize_result_field_location",
    "normalize_target_field_location",
    "require_dpf_runtime_service",
    "resolve_field_handle_and_object",
    "resolve_mesh_location",
    "resolve_model_handle_and_object",
    "resolve_named_selection",
    "resolve_single_active_set",
    "resolve_time_selection",
    "humanize_dpf_symbol_name",
    "unwrap_single_field_handle",
    "wrap_field_handle_as_fields_container",
]
