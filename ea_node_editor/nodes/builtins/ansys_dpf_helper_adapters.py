from __future__ import annotations

import importlib
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ea_node_editor.execution.dpf_runtime_service import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_LOCATION_NODAL,
    DPF_MESH_SELECTION_NODE_IDS,
    ResolvedTimeSelection,
    build_field_handle_metadata,
    build_mesh_scoping_metadata,
    build_time_scoping_metadata,
    normalize_int_values,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_HELPERS_FACTORIES_CATEGORY_PATH,
    DPF_HELPERS_MODELS_CATEGORY_PATH,
    DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_INPUTS_CATEGORY_PATH,
    DPF_WORKFLOW_CATEGORY_PATH,
)
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.node_specs import (
    DPF_DATA_SOURCES_DATA_TYPE,
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_OBJECT_HANDLE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_STREAMS_CONTAINER_DATA_TYPE,
    DPF_WORKFLOW_DATA_TYPE,
    DpfCallableBindingSpec,
    DpfCallableSourceSpec,
    DpfPinSourceSpec,
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
)
from ea_node_editor.nodes.types import ExecutionContext, RuntimeHandleRef

_EXEC_IN_PORT = PortSpec("exec_in", "in", "exec", "exec", required=False)
_EXEC_OUT_PORT = PortSpec("exec_out", "out", "exec", "exec", exposed=True)
_HELPER_TYPE_ID_PREFIX = "dpf.helper"
_HELPER_ICON = "dpf/ansys.svg"
_SANITIZE_RE = re.compile(r"[^0-9a-zA-Z_]+")
_INPUT_RESULT_SETUP_CATEGORY_PATH = (*DPF_INPUTS_CATEGORY_PATH, "Result Setup")
_INPUT_RESULT_SETUP_FAMILY_PATH = ("Inputs", "Result Setup")
_WORKFLOW_BUILD_CATEGORY_PATH = (*DPF_WORKFLOW_CATEGORY_PATH, "Build")
_WORKFLOW_BUILD_FAMILY_PATH = ("Workflow", "Build")


@dataclass(slots=True, frozen=True)
class GeneratedDpfHelperDefinition:
    spec: NodeTypeSpec
    execute: Callable[[ExecutionContext], NodeResult]


def _sanitize_token(value: object, *, default: str) -> str:
    text = re.sub(r"(?<!^)(?=[A-Z])", "_", str(value or "").strip())
    token = _SANITIZE_RE.sub("_", text.lower())
    token = re.sub(r"_+", "_", token).strip("_")
    return token or default


def _helper_type_id(module_name: str, callable_name: str) -> str:
    return ".".join(
        (
            _HELPER_TYPE_ID_PREFIX,
            _sanitize_token(module_name, default="helper"),
            _sanitize_token(callable_name, default="callable"),
        )
    )


def _dpf_module() -> Any:
    try:
        return importlib.import_module("ansys.dpf.core")
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError("ansys.dpf.core is required for DPF helper nodes.") from exc


def _optional_path(
    ctx: ExecutionContext,
    value: Any,
) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    resolved = ctx.resolve_path_value(value)
    if resolved is not None:
        return resolved.resolve(strict=False)
    return Path(text).expanduser().resolve(strict=False)


def _resolve_runtime_ref(
    ctx: ExecutionContext,
    value: Any,
    *,
    expected_kind: str = "",
    allowed_data_types: Sequence[str] = (),
    node_name: str,
) -> tuple[Any, RuntimeHandleRef]:
    if not isinstance(value, RuntimeHandleRef):
        raise TypeError(f"{node_name} requires a runtime handle input.")
    resolved = ctx.resolve_handle(value, expected_kind=expected_kind)
    if allowed_data_types:
        data_type = str(value.metadata.get("dpf_data_type", "")).strip()
        if data_type not in allowed_data_types:
            raise TypeError(
                f"{node_name} requires one of {', '.join(allowed_data_types)}."
            )
    return resolved, value


def _register_object_handle(
    ctx: ExecutionContext,
    value: Any,
    *,
    data_type: str,
    metadata: dict[str, Any] | None = None,
) -> RuntimeHandleRef:
    resolved_metadata = {"dpf_data_type": data_type}
    if metadata:
        resolved_metadata.update(metadata)
    return ctx.register_handle(
        value,
        kind=DPF_OBJECT_HANDLE_DATA_TYPE,
        metadata=resolved_metadata,
    )


def _port_source(
    pin_name: str,
    *,
    direction: str,
    value_key: str,
    data_type: str,
    presence: str = "optional",
    omission_semantics: str = "skip",
    accepted_data_types: tuple[str, ...] = (),
    callable_binding: DpfCallableBindingSpec | None = None,
) -> DpfPinSourceSpec:
    return DpfPinSourceSpec(
        pin_name=pin_name,
        pin_direction="input" if direction == "in" else "output",
        value_origin="port",
        value_key=value_key,
        data_type=data_type,
        presence=presence,
        omission_semantics=omission_semantics,
        accepted_data_types=accepted_data_types,
        callable_binding=callable_binding,
    )


def _property_source(
    pin_name: str,
    *,
    value_key: str,
    data_type: str,
    binding_name: str,
    omission_semantics: str = "skip",
) -> DpfPinSourceSpec:
    return DpfPinSourceSpec(
        pin_name=pin_name,
        pin_direction="input",
        value_origin="property",
        value_key=value_key,
        data_type=data_type,
        presence="optional",
        omission_semantics=omission_semantics,
        callable_binding=DpfCallableBindingSpec("parameter", binding_name),
    )


def _field_from_value(value: Any) -> list[Any]:
    if value is None:
        raise TypeError("DPF Field From Array requires an array input.")
    candidate = value
    if isinstance(candidate, str):
        text = candidate.strip()
        if not text:
            raise TypeError("DPF Field From Array requires a non-empty array input.")
        try:
            candidate = json.loads(text)
        except json.JSONDecodeError as exc:
            raise TypeError("DPF Field From Array array input must be JSON-compatible.") from exc
    if isinstance(candidate, Sequence) and not isinstance(candidate, (bytes, bytearray, str)):
        return list(candidate)
    raise TypeError("DPF Field From Array requires a list-like array input.")


def _time_values_for_model(model: Any, *, count: int) -> tuple[float, ...]:
    support = getattr(model.metadata, "time_freq_support", None)
    frequencies = getattr(support, "time_frequencies", None)
    data = tuple(float(value) for value in tuple(getattr(frequencies, "data", ())))
    if not data:
        return tuple(float(index) for index in range(1, count + 1))
    return data[:count]


def _execute_data_sources_constructor(ctx: ExecutionContext) -> NodeResult:
    dpf = _dpf_module()
    result_path = _optional_path(ctx, ctx.properties.get("result_path"))
    key = str(ctx.properties.get("key", "") or "").strip()
    kwargs: dict[str, Any] = {}
    if result_path is not None:
        kwargs["result_path"] = str(result_path)
    if key:
        kwargs["key"] = key
    data_sources = dpf.DataSources(**kwargs)
    data_sources_ref = _register_object_handle(
        ctx,
        data_sources,
        data_type=DPF_DATA_SOURCES_DATA_TYPE,
        metadata={"result_path": str(result_path) if result_path is not None else "", "key": key},
    )
    return NodeResult(outputs={"data_sources": data_sources_ref, "exec_out": True})


def _execute_data_sources_set_result_file_path(ctx: ExecutionContext) -> NodeResult:
    data_sources, data_sources_ref = _resolve_runtime_ref(
        ctx,
        ctx.inputs.get("receiver"),
        expected_kind=DPF_OBJECT_HANDLE_DATA_TYPE,
        allowed_data_types=(DPF_DATA_SOURCES_DATA_TYPE,),
        node_name="DPF Set Result File Path",
    )
    result_path = _optional_path(ctx, ctx.inputs.get("result_path"))
    if result_path is None:
        raise ValueError("DPF Set Result File Path requires a result_path input.")
    key = str(ctx.properties.get("key", "") or "").strip()
    data_sources.set_result_file_path(str(result_path), key=key)
    return NodeResult(outputs={"updated_receiver": data_sources_ref, "exec_out": True})


def _execute_streams_container_constructor(ctx: ExecutionContext) -> NodeResult:
    dpf = _dpf_module()
    streams_container = dpf.StreamsContainer()
    streams_ref = _register_object_handle(
        ctx,
        streams_container,
        data_type=DPF_STREAMS_CONTAINER_DATA_TYPE,
    )
    return NodeResult(outputs={"streams_container": streams_ref, "exec_out": True})


def _execute_model_constructor(ctx: ExecutionContext) -> NodeResult:
    dpf = _dpf_module()
    data_sources, data_sources_ref = _resolve_runtime_ref(
        ctx,
        ctx.inputs.get("data_sources"),
        expected_kind=DPF_OBJECT_HANDLE_DATA_TYPE,
        allowed_data_types=(DPF_DATA_SOURCES_DATA_TYPE,),
        node_name="DPF Helper Model",
    )
    model = dpf.Model(data_sources)
    model_ref = ctx.register_handle(
        model,
        kind=DPF_MODEL_HANDLE_KIND,
        metadata={"data_sources_handle_id": data_sources_ref.handle_id},
    )
    return NodeResult(outputs={"model": model_ref, "exec_out": True})


def _execute_workflow_constructor(ctx: ExecutionContext) -> NodeResult:
    dpf = _dpf_module()
    workflow = dpf.Workflow()
    workflow_ref = _register_object_handle(
        ctx,
        workflow,
        data_type=DPF_WORKFLOW_DATA_TYPE,
    )
    return NodeResult(outputs={"workflow": workflow_ref, "exec_out": True})


def _execute_field_from_array(ctx: ExecutionContext) -> NodeResult:
    dpf = _dpf_module()
    array_value = _field_from_value(ctx.inputs.get("arr"))
    field = dpf.fields_factory.field_from_array(array_value)
    field_ref = ctx.register_handle(
        field,
        kind=DPF_FIELD_HANDLE_KIND,
        metadata=build_field_handle_metadata(field, result_name="field_from_array"),
    )
    return NodeResult(outputs={"field": field_ref, "exec_out": True})


def _execute_create_scalar_field(ctx: ExecutionContext) -> NodeResult:
    dpf = _dpf_module()
    num_entities = int(ctx.properties.get("num_entities", 1) or 1)
    location = str(ctx.properties.get("location", DPF_LOCATION_NODAL) or DPF_LOCATION_NODAL).strip()
    field = dpf.fields_factory.create_scalar_field(num_entities, location=location)
    field_ref = ctx.register_handle(
        field,
        kind=DPF_FIELD_HANDLE_KIND,
        metadata=build_field_handle_metadata(field, result_name="create_scalar_field"),
    )
    return NodeResult(outputs={"field": field_ref, "exec_out": True})


def _execute_over_time_freq_fields_container(ctx: ExecutionContext) -> NodeResult:
    dpf = _dpf_module()
    field, field_ref = _resolve_runtime_ref(
        ctx,
        ctx.inputs.get("field"),
        expected_kind=DPF_FIELD_HANDLE_KIND,
        node_name="DPF Over Time Freq Fields Container",
    )
    time_freq_unit = str(ctx.properties.get("time_freq_unit", "") or "").strip() or None
    fields_container = dpf.fields_container_factory.over_time_freq_fields_container(
        [field],
        time_freq_unit=time_freq_unit,
    )
    fields_container_ref = ctx.register_handle(
        fields_container,
        kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        metadata={
            "source_handle_id": field_ref.handle_id,
            "field_count": len(fields_container),
            "time_freq_unit": time_freq_unit or "",
        },
    )
    return NodeResult(outputs={"fields_container": fields_container_ref, "exec_out": True})


def _execute_nodal_scoping(ctx: ExecutionContext) -> NodeResult:
    dpf = _dpf_module()
    node_ids = normalize_int_values("node_ids", ctx.properties.get("node_ids"))
    if not node_ids:
        raise ValueError("DPF Nodal Scoping requires at least one node id.")
    scoping = dpf.mesh_scoping_factory.nodal_scoping(node_ids)
    scoping_ref = ctx.register_handle(
        scoping,
        kind=DPF_MESH_SCOPING_HANDLE_KIND,
        metadata=build_mesh_scoping_metadata(
            model_ref=None,
            selection_mode=DPF_MESH_SELECTION_NODE_IDS,
            location=DPF_LOCATION_NODAL,
            ids=node_ids,
        ),
    )
    return NodeResult(outputs={"scoping": scoping_ref, "exec_out": True})


def _execute_scoping_on_all_time_freqs(ctx: ExecutionContext) -> NodeResult:
    dpf = _dpf_module()
    receiver_value = ctx.inputs.get("obj")
    if not isinstance(receiver_value, RuntimeHandleRef):
        raise TypeError("DPF All Time Freq Scoping requires a runtime handle input.")
    model_ref: RuntimeHandleRef | None = None
    if receiver_value.kind == DPF_MODEL_HANDLE_KIND:
        model_ref = receiver_value
        model = ctx.resolve_handle(receiver_value, expected_kind=DPF_MODEL_HANDLE_KIND)
        receiver = model
    elif receiver_value.kind == DPF_OBJECT_HANDLE_DATA_TYPE:
        receiver = ctx.resolve_handle(receiver_value, expected_kind=DPF_OBJECT_HANDLE_DATA_TYPE)
        receiver_data_type = str(receiver_value.metadata.get("dpf_data_type", "")).strip()
        if receiver_data_type != DPF_DATA_SOURCES_DATA_TYPE:
            raise TypeError("DPF All Time Freq Scoping accepts DPF Model or DPF Data Sources handles.")
        model = dpf.Model(receiver)
    else:
        raise TypeError("DPF All Time Freq Scoping accepts DPF Model or DPF Data Sources handles.")

    scoping = dpf.time_freq_scoping_factory.scoping_on_all_time_freqs(receiver)
    set_ids = tuple(int(item) for item in tuple(getattr(scoping, "ids", ())))
    time_selection = ResolvedTimeSelection(
        set_ids=set_ids,
        time_values=_time_values_for_model(model, count=len(set_ids)),
    )
    scoping_ref = ctx.register_handle(
        scoping,
        kind=DPF_TIME_SCOPING_HANDLE_KIND,
        metadata=build_time_scoping_metadata(
            model_ref=model_ref,
            time_selection=time_selection,
        ),
    )
    return NodeResult(outputs={"scoping": scoping_ref, "exec_out": True})


def _constructor_source(
    callable_name: str,
    *,
    source_path: str,
    family_path: tuple[str, ...],
) -> DpfCallableSourceSpec:
    return DpfCallableSourceSpec(
        callable_name=callable_name,
        callable_kind="constructor",
        source_path=source_path,
        family_path=family_path,
        stability="core",
    )


def _factory_source(
    callable_name: str,
    *,
    source_path: str,
    family_path: tuple[str, ...],
) -> DpfCallableSourceSpec:
    return DpfCallableSourceSpec(
        callable_name=callable_name,
        callable_kind="factory",
        source_path=source_path,
        family_path=family_path,
        stability="core",
    )


def _mutator_source(
    callable_name: str,
    *,
    source_path: str,
    family_path: tuple[str, ...],
) -> DpfCallableSourceSpec:
    return DpfCallableSourceSpec(
        callable_name=callable_name,
        callable_kind="mutator",
        source_path=source_path,
        family_path=family_path,
        stability="core",
    )


def load_generated_dpf_helper_definitions() -> tuple[GeneratedDpfHelperDefinition, ...]:
    return (
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("data_sources", "DataSources"),
                display_name="DPF Data Sources",
                category_path=_INPUT_RESULT_SETUP_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "data_sources",
                        "out",
                        "data",
                        DPF_DATA_SOURCES_DATA_TYPE,
                        exposed=True,
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="data_sources",
                            data_type=DPF_DATA_SOURCES_DATA_TYPE,
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(
                    PropertySpec(
                        "result_path",
                        "path",
                        "",
                        "Result File",
                        source_metadata=_property_source(
                            "result_path",
                            value_key="result_path",
                            data_type="path",
                            binding_name="result_path",
                        ),
                        group="Source",
                    ),
                    PropertySpec(
                        "key",
                        "str",
                        "",
                        "Key",
                        source_metadata=_property_source(
                            "key",
                            value_key="key",
                            data_type="str",
                            binding_name="key",
                        ),
                        group="Source",
                    ),
                ),
                description="Constructs a DPF DataSources helper for result-file setup.",
                source_metadata=_constructor_source(
                    "DataSources",
                    source_path="ansys.dpf.core.data_sources.DataSources",
                    family_path=_INPUT_RESULT_SETUP_FAMILY_PATH,
                ),
            ),
            execute=_execute_data_sources_constructor,
        ),
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("data_sources", "set_result_file_path"),
                display_name="DPF Set Result File Path",
                category_path=_INPUT_RESULT_SETUP_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "receiver",
                        "in",
                        "data",
                        DPF_OBJECT_HANDLE_DATA_TYPE,
                        required=True,
                        exposed=True,
                        accepted_data_types=(DPF_DATA_SOURCES_DATA_TYPE,),
                        source_metadata=_port_source(
                            "self",
                            direction="in",
                            value_key="receiver",
                            data_type=DPF_OBJECT_HANDLE_DATA_TYPE,
                            presence="required",
                            omission_semantics="disallowed",
                            accepted_data_types=(DPF_DATA_SOURCES_DATA_TYPE,),
                            callable_binding=DpfCallableBindingSpec("receiver"),
                        ),
                    ),
                    PortSpec(
                        "result_path",
                        "in",
                        "data",
                        "path",
                        required=True,
                        exposed=True,
                        source_metadata=_port_source(
                            "filepath",
                            direction="in",
                            value_key="result_path",
                            data_type="path",
                            presence="required",
                            omission_semantics="disallowed",
                            callable_binding=DpfCallableBindingSpec("parameter", "filepath"),
                        ),
                    ),
                    PortSpec(
                        "updated_receiver",
                        "out",
                        "data",
                        DPF_OBJECT_HANDLE_DATA_TYPE,
                        exposed=True,
                        accepted_data_types=(DPF_DATA_SOURCES_DATA_TYPE,),
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="updated_receiver",
                            data_type=DPF_OBJECT_HANDLE_DATA_TYPE,
                            accepted_data_types=(DPF_DATA_SOURCES_DATA_TYPE,),
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(
                    PropertySpec(
                        "key",
                        "str",
                        "",
                        "Key",
                        source_metadata=_property_source(
                            "key",
                            value_key="key",
                            data_type="str",
                            binding_name="key",
                        ),
                        group="Source",
                    ),
                ),
                description="Updates an existing DPF DataSources helper with a result-file path.",
                source_metadata=_mutator_source(
                    "DataSources.set_result_file_path",
                    source_path="ansys.dpf.core.data_sources.DataSources.set_result_file_path",
                    family_path=_INPUT_RESULT_SETUP_FAMILY_PATH,
                ),
            ),
            execute=_execute_data_sources_set_result_file_path,
        ),
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("streams_container", "StreamsContainer"),
                display_name="DPF Streams Container",
                category_path=DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "streams_container",
                        "out",
                        "data",
                        DPF_STREAMS_CONTAINER_DATA_TYPE,
                        exposed=True,
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="streams_container",
                            data_type=DPF_STREAMS_CONTAINER_DATA_TYPE,
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(),
                description="Constructs an empty DPF StreamsContainer helper.",
                source_metadata=_constructor_source(
                    "StreamsContainer",
                    source_path="ansys.dpf.core.streams_container.StreamsContainer",
                    family_path=("Helpers", "Containers"),
                ),
            ),
            execute=_execute_streams_container_constructor,
        ),
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("model", "Model"),
                display_name="DPF Helper Model",
                category_path=DPF_HELPERS_MODELS_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "data_sources",
                        "in",
                        "data",
                        DPF_DATA_SOURCES_DATA_TYPE,
                        required=True,
                        exposed=True,
                        source_metadata=_port_source(
                            "data_sources",
                            direction="in",
                            value_key="data_sources",
                            data_type=DPF_DATA_SOURCES_DATA_TYPE,
                            presence="required",
                            omission_semantics="disallowed",
                            callable_binding=DpfCallableBindingSpec("parameter", "data_sources"),
                        ),
                    ),
                    PortSpec(
                        "model",
                        "out",
                        "data",
                        DPF_MODEL_DATA_TYPE,
                        exposed=True,
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="model",
                            data_type=DPF_MODEL_DATA_TYPE,
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(),
                description="Constructs a DPF Model from a DataSources helper.",
                source_metadata=_constructor_source(
                    "Model",
                    source_path="ansys.dpf.core.model.Model",
                    family_path=("Helpers", "Models"),
                ),
            ),
            execute=_execute_model_constructor,
        ),
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("workflow", "Workflow"),
                display_name="DPF Workflow",
                category_path=_WORKFLOW_BUILD_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "workflow",
                        "out",
                        "data",
                        DPF_WORKFLOW_DATA_TYPE,
                        exposed=True,
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="workflow",
                            data_type=DPF_WORKFLOW_DATA_TYPE,
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(),
                description="Constructs an empty DPF Workflow helper.",
                source_metadata=_constructor_source(
                    "Workflow",
                    source_path="ansys.dpf.core.workflow.Workflow",
                    family_path=_WORKFLOW_BUILD_FAMILY_PATH,
                ),
            ),
            execute=_execute_workflow_constructor,
        ),
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("fields_factory", "field_from_array"),
                display_name="DPF Field From Array",
                category_path=DPF_HELPERS_FACTORIES_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "arr",
                        "in",
                        "data",
                        "json",
                        required=True,
                        exposed=True,
                        source_metadata=_port_source(
                            "arr",
                            direction="in",
                            value_key="arr",
                            data_type="json",
                            presence="required",
                            omission_semantics="disallowed",
                            callable_binding=DpfCallableBindingSpec("parameter", "arr"),
                        ),
                    ),
                    PortSpec(
                        "field",
                        "out",
                        "data",
                        DPF_FIELD_DATA_TYPE,
                        exposed=True,
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="field",
                            data_type=DPF_FIELD_DATA_TYPE,
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(),
                description="Constructs a DPF Field from a JSON-compatible array payload.",
                source_metadata=_factory_source(
                    "field_from_array",
                    source_path="ansys.dpf.core.fields_factory.field_from_array",
                    family_path=("Helpers", "Factories"),
                ),
            ),
            execute=_execute_field_from_array,
        ),
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("fields_factory", "create_scalar_field"),
                display_name="DPF Create Scalar Field",
                category_path=DPF_HELPERS_FACTORIES_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "field",
                        "out",
                        "data",
                        DPF_FIELD_DATA_TYPE,
                        exposed=True,
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="field",
                            data_type=DPF_FIELD_DATA_TYPE,
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(
                    PropertySpec(
                        "num_entities",
                        "int",
                        1,
                        "Num Entities",
                        source_metadata=_property_source(
                            "num_entities",
                            value_key="num_entities",
                            data_type="int",
                            binding_name="num_entities",
                        ),
                        group="Source",
                    ),
                    PropertySpec(
                        "location",
                        "str",
                        DPF_LOCATION_NODAL,
                        "Location",
                        source_metadata=_property_source(
                            "location",
                            value_key="location",
                            data_type="str",
                            binding_name="location",
                        ),
                        group="Source",
                    ),
                ),
                description="Constructs an empty scalar DPF Field with a chosen entity count and location.",
                source_metadata=_factory_source(
                    "create_scalar_field",
                    source_path="ansys.dpf.core.fields_factory.create_scalar_field",
                    family_path=("Helpers", "Factories"),
                ),
            ),
            execute=_execute_create_scalar_field,
        ),
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("fields_container_factory", "over_time_freq_fields_container"),
                display_name="DPF Over Time Freq Fields Container",
                category_path=DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "field",
                        "in",
                        "data",
                        DPF_FIELD_DATA_TYPE,
                        required=True,
                        exposed=True,
                        source_metadata=_port_source(
                            "fields",
                            direction="in",
                            value_key="field",
                            data_type=DPF_FIELD_DATA_TYPE,
                            presence="required",
                            omission_semantics="disallowed",
                            callable_binding=DpfCallableBindingSpec("parameter", "fields"),
                        ),
                    ),
                    PortSpec(
                        "fields_container",
                        "out",
                        "data",
                        DPF_FIELDS_CONTAINER_DATA_TYPE,
                        exposed=True,
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="fields_container",
                            data_type=DPF_FIELDS_CONTAINER_DATA_TYPE,
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(
                    PropertySpec(
                        "time_freq_unit",
                        "str",
                        "",
                        "Time Freq Unit",
                        source_metadata=_property_source(
                            "time_freq_unit",
                            value_key="time_freq_unit",
                            data_type="str",
                            binding_name="time_freq_unit",
                        ),
                        group="Source",
                    ),
                ),
                description="Constructs a DPF FieldsContainer over time/frequency from one or more field inputs.",
                source_metadata=_factory_source(
                    "over_time_freq_fields_container",
                    source_path="ansys.dpf.core.fields_container_factory.over_time_freq_fields_container",
                    family_path=("Helpers", "Containers"),
                ),
            ),
            execute=_execute_over_time_freq_fields_container,
        ),
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("mesh_scoping_factory", "nodal_scoping"),
                display_name="DPF Nodal Scoping",
                category_path=DPF_HELPERS_SCOPING_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "scoping",
                        "out",
                        "data",
                        DPF_SCOPING_DATA_TYPE,
                        exposed=True,
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="scoping",
                            data_type=DPF_SCOPING_DATA_TYPE,
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(
                    PropertySpec(
                        "node_ids",
                        "json",
                        [],
                        "Node IDs",
                        inspector_editor="textarea",
                        source_metadata=_property_source(
                            "node_ids",
                            value_key="node_ids",
                            data_type="json",
                            binding_name="node_ids",
                        ),
                        group="Selection",
                    ),
                ),
                description="Constructs a mesh scoping from an explicit list of node ids.",
                source_metadata=_factory_source(
                    "nodal_scoping",
                    source_path="ansys.dpf.core.mesh_scoping_factory.nodal_scoping",
                    family_path=("Helpers", "Scoping"),
                ),
            ),
            execute=_execute_nodal_scoping,
        ),
        GeneratedDpfHelperDefinition(
            spec=NodeTypeSpec(
                type_id=_helper_type_id("time_freq_scoping_factory", "scoping_on_all_time_freqs"),
                display_name="DPF All Time Freq Scoping",
                category_path=DPF_HELPERS_SCOPING_CATEGORY_PATH,
                icon=_HELPER_ICON,
                ports=(
                    _EXEC_IN_PORT,
                    PortSpec(
                        "obj",
                        "in",
                        "data",
                        DPF_OBJECT_HANDLE_DATA_TYPE,
                        required=True,
                        exposed=True,
                        accepted_data_types=(DPF_MODEL_DATA_TYPE, DPF_DATA_SOURCES_DATA_TYPE),
                        source_metadata=_port_source(
                            "obj",
                            direction="in",
                            value_key="obj",
                            data_type=DPF_OBJECT_HANDLE_DATA_TYPE,
                            presence="required",
                            omission_semantics="disallowed",
                            accepted_data_types=(DPF_MODEL_DATA_TYPE, DPF_DATA_SOURCES_DATA_TYPE),
                            callable_binding=DpfCallableBindingSpec("parameter", "obj"),
                        ),
                    ),
                    PortSpec(
                        "scoping",
                        "out",
                        "data",
                        DPF_SCOPING_DATA_TYPE,
                        exposed=True,
                        source_metadata=_port_source(
                            "return_value",
                            direction="out",
                            value_key="scoping",
                            data_type=DPF_SCOPING_DATA_TYPE,
                            callable_binding=DpfCallableBindingSpec("return_value"),
                        ),
                    ),
                    _EXEC_OUT_PORT,
                ),
                properties=(),
                description="Constructs a time-frequency scoping that covers every set available on a model or data sources input.",
                source_metadata=_factory_source(
                    "scoping_on_all_time_freqs",
                    source_path="ansys.dpf.core.time_freq_scoping_factory.scoping_on_all_time_freqs",
                    family_path=("Helpers", "Scoping"),
                ),
            ),
            execute=_execute_scoping_on_all_time_freqs,
        ),
    )


__all__ = [
    "GeneratedDpfHelperDefinition",
    "load_generated_dpf_helper_definitions",
]
