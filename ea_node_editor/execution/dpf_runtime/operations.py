from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from ea_node_editor.common.payload_tools import compact_sequence_metadata
from ea_node_editor.execution.dpf_runtime.base import DpfRuntimeBase
from ea_node_editor.execution.dpf_runtime.contracts import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
    DpfFieldRange,
    DpfOperatorInvocationError,
    DpfOperatorInvocationResult,
    DpfResultFile,
)
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
)
from ea_node_editor.runtime_contracts.value_refs import (
    RuntimeHandleRef,
    coerce_runtime_handle_ref,
)

_DPF_RESULT_FIELD_NODE_TYPE_ID = "dpf.result_field"
_DPF_FIELD_OPS_NODE_TYPE_ID = "dpf.field_ops"
_DPF_MODEL_PART_NAMES_MAX_COUNT = 4_096
_DPF_MODEL_PART_NAMES_MAX_UTF8_BYTES = 64 * 1024


class DpfRuntimeOperationsMixin(DpfRuntimeBase):
    def invoke_operator(
        self,
        type_id: str,
        *,
        inputs: Mapping[str, Any] | None = None,
        properties: Mapping[str, Any] | None = None,
    ) -> DpfOperatorInvocationResult:
        normalized_inputs = dict(inputs or {})
        normalized_properties = dict(properties or {})
        spec = self._operator_spec(type_id)
        variant = self._select_operator_variant(spec, properties=normalized_properties)
        operator_name = self._render_operator_name(
            spec,
            variant,
            properties=normalized_properties,
        )

        try:
            operator = self._resolve_operator_factory(operator_name)()
            bound_inputs = []
            bound_pins: dict[str, str] = {}
            for source, raw_value in self._iter_input_sources(
                spec,
                variant_key=variant.key,
                inputs=normalized_inputs,
                properties=normalized_properties,
            ):
                omitted = self._source_value_is_omitted(raw_value)
                if omitted:
                    if source.presence == "required" or source.omission_semantics == "disallowed":
                        raise ValueError(
                            f"Node type {spec.type_id!r} requires a value for DPF input "
                            f"{source.value_key!r}."
                        )
                    bound_inputs.append(self._binding_record(source, omitted=True))
                    continue

                existing_pin = bound_pins.get(source.pin_name)
                if existing_pin is not None:
                    group = source.exclusive_group.strip()
                    if group:
                        raise ValueError(
                            f"Node type {spec.type_id!r} received multiple explicit values for "
                            f"mutually exclusive DPF input group {group!r}."
                        )
                    raise ValueError(
                        f"Node type {spec.type_id!r} received multiple explicit values for "
                        f"DPF input pin {source.pin_name!r}."
                    )

                input_accessor = getattr(operator.inputs, source.pin_name, None)
                if input_accessor is None or not callable(input_accessor):
                    raise DpfOperatorInvocationError(
                        f"DPF operator {operator_name!r} does not expose input pin "
                        f"{source.pin_name!r} for node type {spec.type_id!r}."
                    )
                input_accessor(
                    self._materialize_operator_input(
                        source,
                        raw_value,
                        inputs=normalized_inputs,
                        properties=normalized_properties,
                    )
                )
                bound_inputs.append(self._binding_record(source, omitted=False))
                bound_pins[source.pin_name] = source.value_key

            outputs: dict[str, Any] = {}
            output_sources = tuple(self._iter_output_sources(spec, variant_key=variant.key))
            if not output_sources:
                raise DpfOperatorInvocationError(
                    f"Node type {spec.type_id!r} does not publish DPF operator outputs for "
                    f"variant {variant.key!r}."
                )
            for port_key, source in output_sources:
                output_accessor = getattr(operator.outputs, source.pin_name, None)
                if output_accessor is None or not callable(output_accessor):
                    raise DpfOperatorInvocationError(
                        f"DPF operator {operator_name!r} does not expose output pin "
                        f"{source.pin_name!r} for node type {spec.type_id!r}."
                    )
                outputs[port_key] = output_accessor()

            return DpfOperatorInvocationResult(
                node_type_id=spec.type_id,
                variant_key=variant.key,
                operator_name=operator_name,
                outputs=outputs,
                bound_inputs=tuple(bound_inputs),
            )
        except (DpfOperatorInvocationError, TypeError, ValueError):
            raise
        except Exception as exc:
            raise DpfOperatorInvocationError(
                f"DPF operator {operator_name!r} failed for node type {spec.type_id!r}: {exc}"
            ) from exc

    def load_result_file(
        self,
        value: Any,
        *,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is not None:
            if (
                runtime_ref.data_type_id != DPF_RESULT_FILE_DATA_TYPE
                or runtime_ref.kind != DPF_RESULT_FILE_HANDLE_KIND
            ):
                raise TypeError(
                    "DpfRuntimeService.load_result_file requires a path-like value or "
                    "dpf.result_file handle ref."
                )
            self._worker_services.resolve_handle(
                runtime_ref,
                expected_data_type=DPF_RESULT_FILE_DATA_TYPE,
                expected_kind=DPF_RESULT_FILE_HANDLE_KIND,
            )
            return self._lease_cached_ref_for_owner(
                runtime_ref,
                run_id=run_id,
                owner_scope=owner_scope,
            )

        result_path = self._coerce_result_path(value)
        cache_key = self._cache_key(result_path)
        cached_ref = self._resolve_cached_ref(
            self._result_file_cache,
            cache_key,
            expected_data_type=DPF_RESULT_FILE_DATA_TYPE,
            expected_kind=DPF_RESULT_FILE_HANDLE_KIND,
        )
        if cached_ref is not None:
            return self._lease_cached_ref_for_owner(
                cached_ref,
                run_id=run_id,
                owner_scope=owner_scope,
            )

        result_file = DpfResultFile(
            path=result_path,
            extension=result_path.suffix.lower(),
            cache_key=cache_key,
        )
        handle_ref = self._worker_services.register_handle(
            result_file,
            data_type_id=DPF_RESULT_FILE_DATA_TYPE,
            kind=DPF_RESULT_FILE_HANDLE_KIND,
            owner_scope=self._cache_owner_scope("result_file", cache_key),
            metadata={
                "extension": result_file.extension,
            },
        )
        self._result_file_cache[cache_key] = handle_ref
        return self._lease_cached_ref_for_owner(
            handle_ref,
            run_id=run_id,
            owner_scope=owner_scope,
        )

    def load_model(
        self,
        value: Any,
        *,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is not None:
            if (
                runtime_ref.data_type_id == DPF_MODEL_DATA_TYPE
                and runtime_ref.kind == DPF_MODEL_HANDLE_KIND
            ):
                self._worker_services.resolve_handle(
                    runtime_ref,
                    expected_data_type=DPF_MODEL_DATA_TYPE,
                    expected_kind=DPF_MODEL_HANDLE_KIND,
                )
                return self._lease_cached_ref_for_owner(
                    runtime_ref,
                    run_id=run_id,
                    owner_scope=owner_scope,
                )
            if (
                runtime_ref.data_type_id != DPF_RESULT_FILE_DATA_TYPE
                or runtime_ref.kind != DPF_RESULT_FILE_HANDLE_KIND
            ):
                raise TypeError(
                    "DpfRuntimeService.load_model requires a path-like value, dpf.result_file "
                    "handle ref, or dpf.model handle ref."
                )

        result_file_ref = self.load_result_file(value)
        result_file = self._worker_services.resolve_handle(
            result_file_ref,
            expected_data_type=DPF_RESULT_FILE_DATA_TYPE,
            expected_kind=DPF_RESULT_FILE_HANDLE_KIND,
        )
        if not isinstance(result_file, DpfResultFile):
            raise TypeError("Resolved dpf.result_file handle does not carry a DpfResultFile record.")

        cached_ref = self._resolve_cached_ref(
            self._model_cache,
            result_file.cache_key,
            expected_data_type=DPF_MODEL_DATA_TYPE,
            expected_kind=DPF_MODEL_HANDLE_KIND,
        )
        if cached_ref is not None:
            return self._lease_cached_ref_for_owner(
                cached_ref,
                run_id=run_id,
                owner_scope=owner_scope,
            )

        dpf = self._dpf_module()
        model = dpf.Model(str(result_file.path))
        handle_ref = self._worker_services.register_handle(
            model,
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope=self._cache_owner_scope("model", result_file.cache_key),
            metadata={
                "extension": result_file.extension,
                "result_file_handle_id": result_file_ref.handle_id,
            },
            dispose=model.metadata.release_streams,
        )
        self._model_cache[result_file.cache_key] = handle_ref
        return self._lease_cached_ref_for_owner(
            handle_ref,
            run_id=run_id,
            owner_scope=owner_scope,
        )

    def model_part_names(self, value: Any) -> tuple[str, ...]:
        _, resolved_model = self._resolve_model_handle_and_object(value)
        unsupported_error = "DPF model does not support metadata.mesh_info.part_names."

        try:
            part_names = resolved_model.metadata.mesh_info.part_names
        except Exception:
            raise DpfOperatorInvocationError(unsupported_error) from None

        if isinstance(part_names, (str, bytes, bytearray, memoryview)) or not isinstance(
            part_names, Iterable
        ):
            raise TypeError("DPF model part names must be an iterable of strings.")

        try:
            iterator = iter(part_names)
        except Exception:
            raise DpfOperatorInvocationError(unsupported_error) from None

        result: list[str] = []
        total_utf8_bytes = 0
        while True:
            try:
                name = next(iterator)
            except StopIteration:
                break
            except Exception:
                raise DpfOperatorInvocationError(unsupported_error) from None

            if type(name) is not str:
                raise TypeError("DPF model part names must contain only strings.")
            if not name:
                raise ValueError("DPF model part names must not contain empty strings.")
            try:
                encoded_name = name.encode("utf-8")
            except UnicodeEncodeError:
                raise TypeError("DPF model part names must be UTF-8 encodable.") from None
            if len(result) >= _DPF_MODEL_PART_NAMES_MAX_COUNT:
                raise ValueError("DPF model part names exceed the supported count.")
            next_total_utf8_bytes = total_utf8_bytes + len(encoded_name)
            if next_total_utf8_bytes > _DPF_MODEL_PART_NAMES_MAX_UTF8_BYTES:
                raise ValueError("DPF model part names exceed the supported UTF-8 size.")
            result.append(name)
            total_utf8_bytes = next_total_utf8_bytes

        return tuple(result)

    def create_mesh_scoping(
        self,
        ids: Iterable[Any],
        *,
        location: str,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        dpf = self._dpf_module()
        normalized_ids = self._normalize_ids("ids", ids)
        normalized_location = self._normalize_mesh_location(location)
        scoping = dpf.Scoping(ids=list(normalized_ids), location=normalized_location)
        return self._worker_services.register_handle(
            scoping,
            data_type_id=DPF_SCOPING_DATA_TYPE,
            kind=DPF_MESH_SCOPING_HANDLE_KIND,
            owner_scope=self._resolve_scoping_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata={
                "location": normalized_location,
                **compact_sequence_metadata("ids", normalized_ids),
            },
        )

    def create_time_scoping(
        self,
        set_ids: Iterable[Any],
        *,
        model: Any | None = None,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        dpf = self._dpf_module()
        normalized_ids = self._normalize_ids("set_ids", set_ids)
        location = self._time_scoping_location(model)
        scoping = dpf.Scoping(ids=list(normalized_ids), location=location)
        return self._worker_services.register_handle(
            scoping,
            data_type_id=DPF_SCOPING_DATA_TYPE,
            kind=DPF_TIME_SCOPING_HANDLE_KIND,
            owner_scope=self._resolve_scoping_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata={
                "location": location,
                **compact_sequence_metadata("ids", normalized_ids),
            },
        )

    def extract_result_fields(
        self,
        *,
        model: Any,
        result_name: str,
        set_ids: Iterable[Any] | None = None,
        time_scoping: Any | None = None,
        mesh_scoping: Any | None = None,
        location: str = "",
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        normalized_result_name = self._normalize_result_name(result_name)
        resolved_owner_scope = self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope)
        model_ref, resolved_model = self._resolve_model_handle_and_object(model)
        requested_location = self._normalize_field_location(location, allow_empty=True)
        normalized_set_ids = self._normalize_ids("set_ids", set_ids) if set_ids is not None else ()
        invocation = self.invoke_operator(
            _DPF_RESULT_FIELD_NODE_TYPE_ID,
            inputs={
                "model": model_ref,
                "mesh_scoping": mesh_scoping,
                "time_scoping": time_scoping,
            },
            properties={
                "result_name": normalized_result_name,
                "location": "",
                "set_ids": () if time_scoping is not None else normalized_set_ids,
                "time_values": (),
            },
        )
        fields_container = invocation.outputs.get("field")
        if fields_container is None:
            raise DpfOperatorInvocationError(
                "Descriptor-driven DPF result-field invocation did not produce a field output."
            )
        if requested_location and self._fields_container_location(fields_container) != requested_location:
            fields_container = self._convert_fields_container_location(
                fields_container,
                location=requested_location,
                mesh=resolved_model.metadata.meshed_region,
            )

        return self._worker_services.register_handle(
            fields_container,
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope=resolved_owner_scope,
            metadata=self._build_fields_container_metadata(
                fields_container,
                result_name=normalized_result_name,
                model_ref=model_ref,
                mesh_scoping=mesh_scoping,
                time_scoping=time_scoping,
            ),
        )

    def convert_fields_location(
        self,
        value: Any,
        *,
        model: Any,
        location: str,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        normalized_location = self._normalize_field_location(location)
        if self._fields_container_location(fields_container) == normalized_location:
            return fields_ref

        model_ref, resolved_model = self._resolve_model_handle_and_object(model)
        if normalized_location == "ElementalNodal":
            converted = self._convert_fields_container_location(
                fields_container,
                location=normalized_location,
                mesh=resolved_model.metadata.meshed_region,
            )
        else:
            invocation = self.invoke_operator(
                _DPF_FIELD_OPS_NODE_TYPE_ID,
                inputs={"field": fields_ref, "model": model_ref},
                properties={
                    "operation": "convert_location",
                    "location": normalized_location,
                },
            )
            converted = invocation.outputs.get("field_out")
            if converted is None:
                raise DpfOperatorInvocationError(
                    "Descriptor-driven DPF field-ops invocation did not produce a field_out output."
                )
        metadata = dict(fields_ref.metadata)
        metadata.update(
            self._build_fields_container_metadata(
                converted,
                result_name=str(metadata.get("result_name", "")).strip(),
                model_ref=model_ref,
                mesh_scoping=metadata.get("mesh_scoping_handle_id", ""),
                time_scoping=metadata.get("time_scoping_handle_id", ""),
            )
        )
        metadata["source_handle_id"] = fields_ref.handle_id
        metadata["operation"] = "convert_location"
        metadata["requested_location"] = normalized_location
        return self._worker_services.register_handle(
            converted,
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata=metadata,
        )

    def compute_field_norm(
        self,
        value: Any,
        *,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        invocation = self.invoke_operator(
            _DPF_FIELD_OPS_NODE_TYPE_ID,
            inputs={"field": fields_ref},
            properties={"operation": "norm", "location": ""},
        )
        normalized = invocation.outputs.get("field_out")
        if normalized is None:
            raise DpfOperatorInvocationError(
                "Descriptor-driven DPF field-ops invocation did not produce a field_out output."
            )
        metadata = dict(fields_ref.metadata)
        metadata.update(
            self._build_fields_container_metadata(
                normalized,
                result_name=str(metadata.get("result_name", "")).strip(),
            )
        )
        metadata["source_handle_id"] = fields_ref.handle_id
        metadata["operation"] = "norm"
        return self._worker_services.register_handle(
            normalized,
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata=metadata,
        )

    def reduce_fields_min_max(
        self,
        value: Any,
        *,
        run_id: str = "",
        owner_scope: str = "",
    ) -> DpfFieldRange:
        fields_ref, _ = self._resolve_fields_container_handle_and_object(value)
        invocation = self.invoke_operator(
            _DPF_FIELD_OPS_NODE_TYPE_ID,
            inputs={"field": fields_ref},
            properties={"operation": "min_max", "location": ""},
        )
        resolved_owner_scope = self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope)
        base_metadata = {
            "source_handle_id": fields_ref.handle_id,
            "operation": "min_max",
            "result_name": str(fields_ref.metadata.get("result_name", "")).strip(),
        }
        minimum_field = invocation.outputs.get("field_min")
        maximum_field = invocation.outputs.get("field_max")
        if minimum_field is None or maximum_field is None:
            raise DpfOperatorInvocationError(
                "Descriptor-driven DPF field-ops invocation did not produce both field_min and field_max outputs."
            )
        minimum = self._worker_services.register_handle(
            minimum_field,
            data_type_id=DPF_FIELD_DATA_TYPE,
            kind=DPF_FIELD_HANDLE_KIND,
            owner_scope=resolved_owner_scope,
            metadata={
                **base_metadata,
                "reduction": "min",
                **self._build_field_metadata(minimum_field),
            },
        )
        maximum = self._worker_services.register_handle(
            maximum_field,
            data_type_id=DPF_FIELD_DATA_TYPE,
            kind=DPF_FIELD_HANDLE_KIND,
            owner_scope=resolved_owner_scope,
            metadata={
                **base_metadata,
                "reduction": "max",
                **self._build_field_metadata(maximum_field),
            },
        )
        return DpfFieldRange(minimum=minimum, maximum=maximum)

    def extract_mesh(
        self,
        *,
        model: Any,
        mesh_scoping: Any | None = None,
        nodes_only: bool = False,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        dpf = self._dpf_module()
        model_ref, resolved_model = self._resolve_model_handle_and_object(model)
        mesh = resolved_model.metadata.meshed_region.deep_copy()
        if mesh_scoping is not None:
            scoping = self._resolve_mesh_scoping_input(mesh_scoping)
            if scoping is None:
                raise TypeError("mesh_scoping could not be resolved")
            operator = dpf.operators.mesh.from_scoping()
            operator.inputs.mesh(mesh)
            operator.inputs.scoping(scoping)
            if nodes_only:
                operator.inputs.nodes_only(True)
            mesh = operator.outputs.mesh()

        return self._worker_services.register_handle(
            mesh,
            data_type_id=DPF_MESH_DATA_TYPE,
            kind=DPF_MESH_HANDLE_KIND,
            owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata={
                "model_handle_id": model_ref.handle_id,
                "mesh_scoping_handle_id": self._handle_id_or_empty(mesh_scoping),
                "nodes_only": bool(nodes_only),
                **self._build_mesh_metadata(mesh),
            },
        )

    def cleanup_owner_scope(self, owner_scope: str) -> None:
        self._drop_cached_owner_scope(self._result_file_cache, owner_scope)
        self._drop_cached_owner_scope(self._model_cache, owner_scope)

    def reset(
        self,
        *,
        warn: Callable[[str], None] | None = None,
    ) -> None:
        self._release_cached_refs(self._model_cache, warn=warn)
        self._release_cached_refs(self._result_file_cache, warn=warn)


__all__ = [
    "DpfRuntimeOperationsMixin",
]
