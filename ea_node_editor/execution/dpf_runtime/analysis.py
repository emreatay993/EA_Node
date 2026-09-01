from __future__ import annotations

from typing import Any

from ea_node_editor.common.payload_tools import compact_sequence_metadata
from ea_node_editor.execution.dpf_runtime.base import DpfRuntimeBase
from ea_node_editor.execution.dpf_runtime.contracts import (
    DEFAULT_TIME_SCOPING_LOCATION,
    SUPPORTED_FIELD_MATH_OPERATIONS,
    SUPPORTED_INVARIANTS,
    DpfMinMaxEnvelope,
    DpfTimeHistorySeries,
)
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_FIELD_HANDLE_KIND,
)
from ea_node_editor.runtime_contracts.value_refs import RuntimeHandleRef

_TENSOR_COMPONENT_COUNT = 6


class DpfRuntimeAnalysisMixin(DpfRuntimeBase):
    """Post-processing reductions built directly on the ansys.dpf.core Python API.

    Operators with variadic/ellipsis pins (add_fc, min_max variants) cannot be
    wired through descriptor-driven graph bindings, so these methods bind them
    in-process instead.
    """

    def compute_invariant(
        self,
        value: Any,
        *,
        invariant: str,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        normalized_invariant = self._normalize_invariant(invariant)
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        self._require_tensor_fields(fields_container, context="compute_invariant")

        dpf = self._dpf_module()
        if normalized_invariant == "von_mises":
            operator = dpf.operators.invariant.von_mises_eqv_fc()
            operator.inputs.fields_container(fields_container)
            result = operator.outputs.fields_container()
        elif normalized_invariant in {"intensity", "max_shear"}:
            operator = dpf.operators.invariant.invariants_fc()
            operator.inputs.fields_container(fields_container)
            if normalized_invariant == "intensity":
                result = operator.outputs.fields_int()
            else:
                result = operator.outputs.fields_max_shear()
        else:
            operator = dpf.operators.invariant.principal_invariants_fc()
            operator.inputs.fields_container(fields_container)
            # DPF returns eigenvalues in descending order: eig_1 >= eig_2 >= eig_3.
            if normalized_invariant == "principal_1":
                result = operator.outputs.fields_eig_1()
            elif normalized_invariant == "principal_2":
                result = operator.outputs.fields_eig_2()
            else:
                result = operator.outputs.fields_eig_3()

        metadata = dict(fields_ref.metadata)
        metadata.update(
            self._build_fields_container_metadata(
                result,
                result_name=str(metadata.get("result_name", "")).strip(),
            )
        )
        metadata["source_handle_id"] = fields_ref.handle_id
        metadata["operation"] = normalized_invariant
        return self._worker_services.register_handle(
            result,
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata=metadata,
        )

    def combine_fields_containers(
        self,
        a: Any,
        b: Any | None = None,
        *,
        operation: str,
        scalar: float = 1.0,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        normalized_operation = str(operation).strip().casefold()
        if normalized_operation not in SUPPORTED_FIELD_MATH_OPERATIONS:
            supported = ", ".join(sorted(SUPPORTED_FIELD_MATH_OPERATIONS))
            raise ValueError(f"operation must be one of {supported}; got {operation!r}")

        a_ref, a_container = self._resolve_fields_container_handle_and_object(a)
        b_ref: RuntimeHandleRef | None = None
        b_container: Any = None
        if normalized_operation == "scale":
            if b is not None:
                raise ValueError("operation 'scale' uses only input A; disconnect input B")
        else:
            if b is None:
                raise ValueError(
                    f"operation {normalized_operation!r} requires a second fields container on input B"
                )
            b_ref, b_container = self._resolve_fields_container_handle_and_object(b)

        dpf = self._dpf_module()
        if normalized_operation == "add":
            operator = dpf.operators.math.add_fc()
            operator.inputs.fields_container1(a_container)
            operator.inputs.fields_container2(b_container)
            result = operator.outputs.fields_container()
        elif normalized_operation == "subtract":
            operator = dpf.operators.math.minus_fc()
            operator.inputs.field_or_fields_container_A(a_container)
            operator.inputs.field_or_fields_container_B(b_container)
            result = operator.outputs.fields_container()
        elif normalized_operation == "divide":
            operator = dpf.operators.math.component_wise_divide_fc()
            operator.inputs.fields_containerA(a_container)
            operator.inputs.fields_containerB(b_container)
            result = operator.outputs.fields_container()
        elif normalized_operation == "multiply":
            result = self._component_wise_product(dpf, a_container, b_container)
        else:
            operator = dpf.operators.math.scale_fc()
            operator.inputs.fields_container(a_container)
            operator.inputs.weights(float(scalar))
            result = operator.outputs.fields_container()

        metadata = dict(a_ref.metadata)
        metadata.update(
            self._build_fields_container_metadata(
                result,
                result_name=str(metadata.get("result_name", "")).strip(),
            )
        )
        metadata["source_handle_id"] = a_ref.handle_id
        metadata["operation"] = normalized_operation
        if b_ref is not None:
            metadata["second_handle_id"] = b_ref.handle_id
        if normalized_operation == "scale":
            metadata["scalar"] = float(scalar)
        return self._worker_services.register_handle(
            result,
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata=metadata,
        )

    def compute_min_max_envelope(
        self,
        value: Any,
        *,
        model: Any,
        run_id: str = "",
        owner_scope: str = "",
    ) -> DpfMinMaxEnvelope:
        import numpy as np

        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        _, resolved_model = self._resolve_model_handle_and_object(model)
        working_container = self._scalar_reduced_container(
            fields_container,
            context="compute_min_max_envelope",
        )

        resolved_owner_scope = self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope)
        result_name = str(fields_ref.metadata.get("result_name", "")).strip()
        set_ids = self._set_ids_or_positional(working_container)
        time_values = self._time_values_for_set_ids(resolved_model, set_ids)
        location = self._fields_container_location(working_container)
        unit = str(getattr(working_container[0], "unit", "") or "")

        per_set_rows: list[dict[str, Any]] = []
        for index in range(len(working_container)):
            field_value = working_container[index]
            data = np.asarray(field_value.data, dtype=float).reshape(-1)
            entity_ids = np.asarray(field_value.scoping.ids, dtype=int)
            if data.size == 0:
                continue
            self._require_entity_aligned_data(
                data_size=int(data.size),
                entity_count=int(entity_ids.size),
                location=location,
                context="compute_min_max_envelope",
            )
            min_index = int(np.argmin(data))
            max_index = int(np.argmax(data))
            per_set_rows.append(
                {
                    "set_id": int(set_ids[index]),
                    "time_value": time_values[index],
                    "min": float(data[min_index]),
                    "min_entity_id": int(entity_ids[min_index]),
                    "max": float(data[max_index]),
                    "max_entity_id": int(entity_ids[max_index]),
                }
            )
        if not per_set_rows:
            raise ValueError("compute_min_max_envelope requires at least one non-empty field")

        dpf = self._dpf_module()
        operator = dpf.operators.min_max.min_max_over_time_by_entity()
        operator.inputs.fields_container(working_container)
        envelope_min_field = operator.outputs.min()[0]
        envelope_max_field = operator.outputs.max()[0]

        base_metadata = {
            "source_handle_id": fields_ref.handle_id,
            "operation": "min_max_envelope",
            "result_name": result_name,
            **compact_sequence_metadata(
                "set_ids",
                (int(set_id) for set_id in set_ids),
            ),
        }
        envelope_min = self._worker_services.register_handle(
            envelope_min_field,
            data_type_id=DPF_FIELD_DATA_TYPE,
            kind=DPF_FIELD_HANDLE_KIND,
            owner_scope=resolved_owner_scope,
            metadata={
                **base_metadata,
                "reduction": "envelope_min",
                **self._build_field_metadata(envelope_min_field),
            },
        )
        envelope_max = self._worker_services.register_handle(
            envelope_max_field,
            data_type_id=DPF_FIELD_DATA_TYPE,
            kind=DPF_FIELD_HANDLE_KIND,
            owner_scope=resolved_owner_scope,
            metadata={
                **base_metadata,
                "reduction": "envelope_max",
                **self._build_field_metadata(envelope_max_field),
            },
        )

        overall_min_row = min(per_set_rows, key=lambda row: row["min"])
        overall_max_row = max(per_set_rows, key=lambda row: row["max"])
        overall = {
            "location": location,
            "unit": unit,
            "result_name": result_name,
            "min": self._overall_extreme_entry(
                resolved_model,
                value=overall_min_row["min"],
                entity_id=overall_min_row["min_entity_id"],
                set_id=overall_min_row["set_id"],
                time_value=overall_min_row["time_value"],
                location=location,
            ),
            "max": self._overall_extreme_entry(
                resolved_model,
                value=overall_max_row["max"],
                entity_id=overall_max_row["max_entity_id"],
                set_id=overall_max_row["set_id"],
                time_value=overall_max_row["time_value"],
                location=location,
            ),
        }
        return DpfMinMaxEnvelope(
            envelope_min=envelope_min,
            envelope_max=envelope_max,
            per_set_rows=tuple(per_set_rows),
            overall=overall,
        )

    def build_time_history_series(
        self,
        value: Any,
        *,
        model: Any,
        run_id: str = "",
        owner_scope: str = "",
    ) -> DpfTimeHistorySeries:
        import numpy as np

        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        _, resolved_model = self._resolve_model_handle_and_object(model)
        working_container = self._scalar_reduced_container(
            fields_container,
            context="build_time_history_series",
        )

        result_name = str(fields_ref.metadata.get("result_name", "")).strip()
        set_ids = self._set_ids_or_positional(working_container)
        raw_time_values = self._time_values_for_set_ids(resolved_model, set_ids)
        time_values = tuple(
            float(time_value) if time_value is not None else float(set_id)
            for time_value, set_id in zip(raw_time_values, set_ids)
        )
        unit = str(getattr(working_container[0], "unit", "") or "")

        entity_ids = tuple(int(item) for item in working_container[0].scoping.ids)
        if not entity_ids:
            raise ValueError("build_time_history_series requires a mesh-scoped fields container")
        values_by_set: list[dict[int, float]] = []
        for index in range(len(working_container)):
            field_value = working_container[index]
            data = np.asarray(field_value.data, dtype=float).reshape(-1)
            ids = tuple(int(item) for item in field_value.scoping.ids)
            self._require_entity_aligned_data(
                data_size=int(data.size),
                entity_count=len(ids),
                location=str(getattr(field_value, "location", "")),
                context="build_time_history_series",
            )
            lookup = dict(zip(ids, data.tolist()))
            missing = [entity_id for entity_id in entity_ids if entity_id not in lookup]
            if missing:
                raise ValueError(
                    "build_time_history_series requires every probed entity to be present in "
                    f"all sets; set {set_ids[index]} is missing entities {missing[:5]}"
                )
            values_by_set.append(lookup)

        dpf = self._dpf_module()
        series_container = dpf.FieldsContainer()
        series_container.labels = ["entity"]
        rows: list[dict[str, Any]] = []
        for entity_id in entity_ids:
            history = np.asarray(
                [values_by_set[index][entity_id] for index in range(len(values_by_set))],
                dtype=float,
            )
            entity_field = dpf.fields_factory.field_from_array(history)
            entity_field.scoping = dpf.Scoping(
                ids=[int(set_id) for set_id in set_ids],
                location=DEFAULT_TIME_SCOPING_LOCATION,
            )
            if unit:
                entity_field.unit = unit
            series_container.add_field({"entity": int(entity_id)}, entity_field)
            for index, set_id in enumerate(set_ids):
                rows.append(
                    {
                        "set_id": int(set_id),
                        "time_value": time_values[index],
                        "entity_id": int(entity_id),
                        "value": float(history[index]),
                    }
                )

        metadata = {
            **self._build_fields_container_metadata(series_container, result_name=result_name),
            "source_handle_id": fields_ref.handle_id,
            "operation": "time_history",
            "x_axis": "time",
            **compact_sequence_metadata(
                "time_values",
                (float(item) for item in time_values),
            ),
            **compact_sequence_metadata(
                "entity_ids",
                (int(entity_id) for entity_id in entity_ids),
            ),
        }
        series = self._worker_services.register_handle(
            series_container,
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata=metadata,
        )
        return DpfTimeHistorySeries(
            series=series,
            rows=tuple(rows),
            time_values=time_values,
            entity_ids=entity_ids,
        )

    def _scalar_reduced_container(self, fields_container: Any, *, context: str) -> Any:
        if len(fields_container) == 0:
            raise ValueError(f"{context} requires a non-empty fields container")
        component_count = int(getattr(fields_container[0], "component_count", 0))
        if component_count == _TENSOR_COMPONENT_COUNT:
            raise ValueError(
                f"{context} does not accept 6-component tensor results directly; "
                "reduce them first (e.g. DPF Stress Invariants for stress)."
            )
        if component_count <= 1:
            return fields_container
        dpf = self._dpf_module()
        operator = dpf.operators.math.norm_fc()
        operator.inputs.fields_container(fields_container)
        return operator.outputs.fields_container()

    def _component_wise_product(self, dpf: Any, a_container: Any, b_container: Any) -> Any:
        if len(b_container) not in {1, len(a_container)}:
            raise ValueError(
                "operation 'multiply' requires input B to hold one field or match input A "
                f"({len(a_container)} fields); got {len(b_container)}"
            )
        result = dpf.FieldsContainer()
        labels = list(getattr(a_container, "labels", ()) or ())
        result.labels = labels if labels else ["time"]
        for index in range(len(a_container)):
            operator = dpf.operators.math.component_wise_product()
            operator.inputs.fieldA(a_container[index])
            operator.inputs.fieldB(b_container[index if len(b_container) > 1 else 0])
            product = operator.outputs.field()
            if labels:
                label_space = a_container.get_label_space(index)
            else:
                label_space = {"time": index + 1}
            result.add_field(label_space, product)
        return result

    @staticmethod
    def _require_entity_aligned_data(
        *,
        data_size: int,
        entity_count: int,
        location: str,
        context: str,
    ) -> None:
        if entity_count and data_size == entity_count:
            return
        raise ValueError(
            f"{context} requires one value per scoped entity; got {data_size} values for "
            f"{entity_count} entities at location {location or 'unknown'!r}. "
            "Convert ElementalNodal results to Nodal or Elemental first."
        )

    @staticmethod
    def _normalize_invariant(value: object) -> str:
        normalized = str(value).strip().casefold()
        if normalized not in SUPPORTED_INVARIANTS:
            supported = ", ".join(sorted(SUPPORTED_INVARIANTS))
            raise ValueError(f"invariant must be one of {supported}; got {value!r}")
        return normalized

    def _require_tensor_fields(self, fields_container: Any, *, context: str) -> None:
        if len(fields_container) == 0:
            raise ValueError(f"{context} requires a non-empty fields container")
        component_count = int(getattr(fields_container[0], "component_count", 0))
        if component_count != _TENSOR_COMPONENT_COUNT:
            raise ValueError(
                f"{context} requires a 6-component tensor result (e.g. stress); "
                f"got {component_count} component(s)."
            )

    def _set_ids_or_positional(self, fields_container: Any) -> tuple[int, ...]:
        set_ids = self._fields_container_set_ids(fields_container)
        if len(set_ids) == len(fields_container):
            return set_ids
        return tuple(range(1, len(fields_container) + 1))

    @staticmethod
    def _time_values_for_set_ids(resolved_model: Any, set_ids: tuple[int, ...]) -> tuple[float | None, ...]:
        try:
            frequencies = list(resolved_model.metadata.time_freq_support.time_frequencies.data)
        except Exception:
            frequencies = []
        values: list[float | None] = []
        for set_id in set_ids:
            index = int(set_id) - 1
            if 0 <= index < len(frequencies):
                values.append(float(frequencies[index]))
            else:
                values.append(None)
        return tuple(values)

    def _overall_extreme_entry(
        self,
        resolved_model: Any,
        *,
        value: float,
        entity_id: int,
        set_id: int,
        time_value: float | None,
        location: str,
    ) -> dict[str, Any]:
        return {
            "value": float(value),
            "entity_id": int(entity_id),
            "set_id": int(set_id),
            "time_value": time_value,
            "coordinates": self._nodal_coordinates(resolved_model, entity_id) if location == "Nodal" else None,
        }

    @staticmethod
    def _nodal_coordinates(resolved_model: Any, entity_id: int) -> list[float] | None:
        import numpy as np

        try:
            coordinates_field = resolved_model.metadata.meshed_region.nodes.coordinates_field
            node_ids = np.asarray(coordinates_field.scoping.ids, dtype=int)
            positions = np.nonzero(node_ids == int(entity_id))[0]
            if positions.size == 0:
                return None
            coordinates = np.asarray(coordinates_field.data, dtype=float).reshape(-1, 3)[int(positions[0])]
            return [float(item) for item in coordinates]
        except Exception:
            return None

__all__ = [
    "DpfRuntimeAnalysisMixin",
]
