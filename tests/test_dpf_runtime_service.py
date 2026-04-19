from __future__ import annotations

import sys
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest import mock

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

dpf = pytest.importorskip("ansys.dpf.core")

from ea_node_editor.addons.catalog import ANSYS_DPF_ADDON_ID, AddOnRegistration
from ea_node_editor.addons.hot_apply import apply_addon_enabled_state
from ea_node_editor.app_preferences import addon_state, default_app_preferences_document
from ansys_dpf_core.fixture_paths import MODAL_ANALYSIS_RST, STATIC_ANALYSIS_RST, THERMAL_ANALYSIS_RTH
from ea_node_editor.execution.dpf_runtime.contracts import (
    DPF_OBJECT_HANDLE_KIND,
    DpfOperatorInvocationError,
)
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
    DpfResultFile,
    DpfRuntimeUnavailableError,
)
from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.node_specs import (
    DPF_DATA_SOURCES_DATA_TYPE,
    DPF_STREAMS_CONTAINER_DATA_TYPE,
)
from ea_node_editor.nodes.plugin_contracts import AddOnManifest


class _FakeScoping:
    def __init__(self, *, ids: list[int], location: str) -> None:
        self.ids = list(ids)
        self.location = location


class _FakeFieldsContainer:
    def __init__(self, fields: list[object] | tuple[object, ...], label_spaces: list[dict[str, int]]) -> None:
        self._fields = list(fields)
        self._label_spaces = [dict(item) for item in label_spaces]
        self.labels = ("time",)

    def __len__(self) -> int:
        return len(self._fields)

    def __getitem__(self, index: int) -> object:
        return self._fields[index]

    def get_label_space(self, index: int) -> dict[str, int]:
        return dict(self._label_spaces[index])


class _FakeFieldsContainerBuilder(_FakeFieldsContainer):
    def __init__(self) -> None:
        super().__init__(fields=(), label_spaces=[])
        self.labels = ()

    def set_labels(self, labels: list[str]) -> None:
        self.labels = tuple(labels)

    def add_field(self, label_space: dict[str, int], field: object) -> None:
        self._fields.append(field)
        self._label_spaces.append(dict(label_space))


class _FakeBindingNamespace:
    def __init__(self) -> None:
        self.calls: dict[str, object] = {}

    def __getattr__(self, name: str):
        def binder(value: object) -> None:
            self.calls[name] = value

        return binder


class _FakeOutputNamespace:
    def __init__(self, outputs: dict[str, object]) -> None:
        self._outputs = dict(outputs)

    def __getattr__(self, name: str):
        if name not in self._outputs:
            raise AttributeError(name)

        def getter() -> object:
            value = self._outputs[name]
            if isinstance(value, Exception):
                raise value
            return value

        return getter


class _FakeOperator:
    def __init__(self, outputs: dict[str, object]) -> None:
        self.inputs = _FakeBindingNamespace()
        self.outputs = _FakeOutputNamespace(outputs)


def _capturing_factory(capture: dict[str, object], outputs: dict[str, object]):
    def factory() -> _FakeOperator:
        operator = _FakeOperator(outputs)
        capture["operator"] = operator
        return operator

    return factory


def _fake_dpf_module(*, result_factory=None, min_max_factory=None):
    return SimpleNamespace(
        Scoping=lambda ids, location: _FakeScoping(ids=list(ids), location=location),
        FieldsContainer=_FakeFieldsContainerBuilder,
        operators=SimpleNamespace(
            result=SimpleNamespace(displacement=result_factory),
            min_max=SimpleNamespace(min_max_fc=min_max_factory),
        ),
    )


def _fake_model(*, location: str = "TimeFreq") -> SimpleNamespace:
    return SimpleNamespace(
        metadata=SimpleNamespace(
            data_sources="fake_data_sources",
            meshed_region="fake_mesh",
            time_freq_support=SimpleNamespace(
                time_frequencies=SimpleNamespace(
                    scoping=SimpleNamespace(location=location),
                )
            ),
        )
    )


class DpfRuntimeServiceTests(unittest.TestCase):
    def test_worker_services_lazy_service_defers_optional_dpf_import(self) -> None:
        services = WorkerServices()

        self.assertIsNone(services._dpf_runtime_service)
        service = services.dpf_runtime_service
        self.assertIs(service, services.dpf_runtime_service)

        with mock.patch(
            "ea_node_editor.execution.dpf_runtime_service.importlib.import_module",
            side_effect=ModuleNotFoundError("ansys.dpf.core"),
        ):
            with self.assertRaises(DpfRuntimeUnavailableError):
                service.create_mesh_scoping([1], location="nodal", run_id="run_lazy")

    def test_load_result_file_and_model_reuse_stable_cached_handles(self) -> None:
        services = WorkerServices()
        service = services.dpf_runtime_service

        result_ref = service.load_result_file(STATIC_ANALYSIS_RST)
        repeated_result_ref = service.load_result_file(STATIC_ANALYSIS_RST)
        self.assertEqual(result_ref.handle_id, repeated_result_ref.handle_id)
        self.assertEqual(result_ref.kind, DPF_RESULT_FILE_HANDLE_KIND)

        result_record = services.resolve_handle(result_ref, expected_kind=DPF_RESULT_FILE_HANDLE_KIND)
        self.assertIsInstance(result_record, DpfResultFile)
        self.assertEqual(result_record.path, STATIC_ANALYSIS_RST)
        self.assertEqual(result_record.extension, ".rst")

        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        repeated_model_ref = service.load_model(result_ref)
        self.assertEqual(model_ref.handle_id, repeated_model_ref.handle_id)
        self.assertEqual(model_ref.kind, DPF_MODEL_HANDLE_KIND)

        model = services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        self.assertIsInstance(model, dpf.Model)
        self.assertEqual(model.metadata.time_freq_support.n_sets, 2)

        thermal_model_ref = service.load_model(THERMAL_ANALYSIS_RTH)
        thermal_model = services.resolve_handle(thermal_model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        self.assertIsInstance(thermal_model, dpf.Model)
        self.assertEqual(thermal_model.metadata.time_freq_support.n_sets, 1)
        self.assertEqual(thermal_model_ref.metadata["extension"], ".rth")

    def test_scoping_helpers_create_worker_local_handles_and_run_cleanup_releases_them(self) -> None:
        services = WorkerServices()
        service = services.dpf_runtime_service

        model_ref = service.load_model(MODAL_ANALYSIS_RST)
        model = services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        time_ref = service.create_time_scoping([1, 3], model=model_ref, run_id="run_scoping")
        mesh_ref = service.create_mesh_scoping([1, 2, 3], location="nodal", run_id="run_scoping")

        time_scoping = services.resolve_handle(time_ref, expected_kind=DPF_TIME_SCOPING_HANDLE_KIND)
        mesh_scoping = services.resolve_handle(mesh_ref, expected_kind=DPF_MESH_SCOPING_HANDLE_KIND)

        self.assertEqual([int(value) for value in time_scoping.ids], [1, 3])
        self.assertEqual(
            time_scoping.location,
            model.metadata.time_freq_support.time_frequencies.scoping.location,
        )
        self.assertEqual([int(value) for value in mesh_scoping.ids], [1, 2, 3])
        self.assertEqual(mesh_scoping.location, "Nodal")

        self.assertEqual(services.cleanup_run("run_scoping"), 2)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            services.resolve_handle(time_ref)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            services.resolve_handle(mesh_ref)

        self.assertIs(services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND), model)

    def test_reset_invalidates_cached_model_handles_and_rebuilds_service_cache(self) -> None:
        services = WorkerServices()
        service = services.dpf_runtime_service

        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        self.assertEqual(services.reset(), 2)

        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)

        reloaded_ref = service.load_model(STATIC_ANALYSIS_RST)
        self.assertNotEqual(model_ref.handle_id, reloaded_ref.handle_id)
        reloaded_model = services.resolve_handle(reloaded_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        self.assertEqual(reloaded_model.metadata.time_freq_support.n_sets, 2)

    def test_hot_apply_disable_rebuilds_worker_runtime_and_reenable_restores_dpf_services(self) -> None:
        services = WorkerServices()
        model_ref = services.dpf_runtime_service.load_model(STATIC_ANALYSIS_RST)
        services.viewer_backend_registry.resolve(DPF_EXECUTION_VIEWER_BACKEND_ID)

        disabled = apply_addon_enabled_state(
            ANSYS_DPF_ADDON_ID,
            enabled=False,
            preferences_document=default_app_preferences_document(),
            worker_services=services,
        )

        self.assertFalse(disabled.restart_required)
        self.assertFalse(addon_state(disabled.preferences_document, ANSYS_DPF_ADDON_ID)["enabled"])
        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        with self.assertRaises(LookupError):
            services.viewer_backend_registry.resolve(DPF_EXECUTION_VIEWER_BACKEND_ID)

        reenabled = apply_addon_enabled_state(
            ANSYS_DPF_ADDON_ID,
            enabled=True,
            preferences_document=disabled.preferences_document,
            worker_services=services,
        )

        self.assertFalse(reenabled.restart_required)
        self.assertTrue(addon_state(reenabled.preferences_document, ANSYS_DPF_ADDON_ID)["enabled"])
        self.assertEqual(
            services.viewer_backend_registry.resolve(DPF_EXECUTION_VIEWER_BACKEND_ID).backend_id,
            DPF_EXECUTION_VIEWER_BACKEND_ID,
        )
        reloaded_ref = services.dpf_runtime_service.load_model(STATIC_ANALYSIS_RST)
        reloaded_model = services.resolve_handle(reloaded_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        self.assertEqual(reloaded_model.metadata.time_freq_support.n_sets, 2)

    def test_restart_required_apply_only_persists_pending_restart_state(self) -> None:
        restart_registration = AddOnRegistration(
            manifest=AddOnManifest(
                addon_id="tests.addons.restart_only",
                display_name="Restart Only",
                apply_policy="restart_required",
            ),
            backend_module="tests.addons.restart_only",
            backend_id="tests.addons.restart_only",
        )

        with mock.patch(
            "ea_node_editor.addons.hot_apply.registered_addon_registration_by_id",
            return_value=restart_registration,
        ):
            result = apply_addon_enabled_state(
                "tests.addons.restart_only",
                enabled=False,
                preferences_document=default_app_preferences_document(),
            )

        self.assertTrue(result.restart_required)
        self.assertIsNone(result.registry)
        persisted_state = addon_state(result.preferences_document, "tests.addons.restart_only")
        self.assertFalse(persisted_state["enabled"])
        self.assertTrue(persisted_state["pending_restart"])

    def test_field_extraction_field_ops_and_mesh_extraction_use_worker_local_handles(self) -> None:
        services = WorkerServices()
        service = services.dpf_runtime_service

        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        model = services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        element_ids = [int(value) for value in model.metadata.meshed_region.elements.scoping.ids[:2]]
        mesh_scoping_ref = service.create_mesh_scoping(
            element_ids,
            location="elemental",
            run_id="run_extract",
        )

        stress_ref = service.extract_result_fields(
            model=model_ref,
            result_name="stress",
            set_ids=[1],
            location="nodal",
            run_id="run_extract",
        )
        stress_fields = services.resolve_handle(
            stress_ref,
            expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        )
        self.assertEqual(stress_ref.metadata["result_name"], "stress")
        self.assertEqual(stress_ref.metadata["set_ids"], [1])
        self.assertEqual(stress_fields[0].location, "Nodal")
        self.assertEqual(stress_fields[0].component_count, 6)

        norm_ref = service.compute_field_norm(stress_ref, run_id="run_extract")
        norm_fields = services.resolve_handle(norm_ref, expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND)
        self.assertEqual(norm_ref.metadata["operation"], "norm")
        self.assertEqual(norm_fields[0].location, "Nodal")
        self.assertEqual(norm_fields[0].component_count, 1)

        field_range = service.reduce_fields_min_max(norm_ref, run_id="run_extract")
        min_field = services.resolve_handle(field_range.minimum, expected_kind=DPF_FIELD_HANDLE_KIND)
        max_field = services.resolve_handle(field_range.maximum, expected_kind=DPF_FIELD_HANDLE_KIND)
        self.assertEqual(field_range.minimum.metadata["reduction"], "min")
        self.assertEqual(field_range.maximum.metadata["reduction"], "max")
        self.assertEqual(min_field.component_count, 1)
        self.assertEqual(max_field.component_count, 1)
        self.assertEqual(min_field.scoping.size, 1)
        self.assertEqual(max_field.scoping.size, 1)

        mesh_ref = service.extract_mesh(
            model=model_ref,
            mesh_scoping=mesh_scoping_ref,
            run_id="run_extract",
        )
        mesh = services.resolve_handle(mesh_ref, expected_kind=DPF_MESH_HANDLE_KIND)
        self.assertEqual(mesh_ref.metadata["element_count"], 2)
        self.assertEqual(mesh.elements.n_elements, 2)
        self.assertGreater(mesh.nodes.n_nodes, 0)

        self.assertEqual(services.cleanup_run("run_extract"), 6)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            services.resolve_handle(mesh_scoping_ref, expected_kind=DPF_MESH_SCOPING_HANDLE_KIND)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            services.resolve_handle(stress_ref, expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            services.resolve_handle(mesh_ref, expected_kind=DPF_MESH_HANDLE_KIND)

    def test_temperature_extraction_supports_rth_models_and_time_scoping_handles(self) -> None:
        services = WorkerServices()
        service = services.dpf_runtime_service

        model_ref = service.load_model(THERMAL_ANALYSIS_RTH)
        time_ref = service.create_time_scoping([1], model=model_ref, run_id="run_thermal_extract")
        temperature_ref = service.extract_result_fields(
            model=model_ref,
            result_name="temperature",
            time_scoping=time_ref,
            run_id="run_thermal_extract",
        )

        temperature_fields = services.resolve_handle(
            temperature_ref,
            expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        )
        self.assertEqual(temperature_ref.metadata["result_name"], "temperature")
        self.assertEqual(temperature_ref.metadata["set_ids"], [1])
        self.assertEqual(temperature_fields[0].location, "Nodal")
        self.assertEqual(temperature_fields[0].component_count, 1)
        self.assertGreater(temperature_fields[0].scoping.size, 1000)

    def test_invoke_operator_uses_descriptor_bindings_and_preserves_omitted_defaults(self) -> None:
        services = WorkerServices()
        service = services.dpf_runtime_service
        capture: dict[str, object] = {}
        output_field = SimpleNamespace(
            location="Nodal",
            component_count=3,
            scoping=SimpleNamespace(size=4),
            unit="m",
        )
        output_fields = _FakeFieldsContainer([output_field], [{"time": 2}])
        fake_dpf = _fake_dpf_module(
            result_factory=_capturing_factory(capture, {"fields_container": output_fields}),
        )
        model_ref = services.register_handle(
            _fake_model(),
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="run:invoke_operator",
        )

        with mock.patch.object(service, "_dpf_module", return_value=fake_dpf):
            invocation = service.invoke_operator(
                "dpf.result_field",
                inputs={
                    "model": model_ref,
                    "mesh_scoping": None,
                    "time_scoping": None,
                },
                properties={
                    "result_name": "displacement",
                    "location": "",
                    "set_ids": [2],
                    "time_values": (),
                },
            )

        self.assertEqual(invocation.variant_key, "result")
        self.assertEqual(invocation.operator_name, "result.displacement")
        self.assertIs(invocation.outputs["field"], output_fields)

        bindings = {binding.value_key: binding for binding in invocation.bound_inputs}
        self.assertFalse(bindings["model"].omitted)
        self.assertFalse(bindings["set_ids"].omitted)
        self.assertTrue(bindings["location"].omitted)
        self.assertTrue(bindings["mesh_scoping"].omitted)
        self.assertTrue(bindings["time_scoping"].omitted)
        self.assertTrue(bindings["time_values"].omitted)

        operator = capture["operator"]
        self.assertIsInstance(operator, _FakeOperator)
        self.assertEqual(operator.inputs.calls["data_sources"], "fake_data_sources")
        self.assertIn("time_scoping", operator.inputs.calls)
        self.assertNotIn("requested_location", operator.inputs.calls)
        self.assertEqual(operator.inputs.calls["time_scoping"].ids, [2])
        self.assertEqual(operator.inputs.calls["time_scoping"].location, "TimeFreq")

    def test_invoke_operator_wraps_output_failures_with_operator_context(self) -> None:
        services = WorkerServices()
        service = services.dpf_runtime_service
        fields_ref = services.register_handle(
            _FakeFieldsContainer(
                [
                    SimpleNamespace(
                        location="Nodal",
                        component_count=1,
                        scoping=SimpleNamespace(size=1),
                        unit="m",
                    )
                ],
                [{"time": 1}],
            ),
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="run:invoke_operator_failure",
        )
        fake_dpf = _fake_dpf_module(
            min_max_factory=_capturing_factory(
                {},
                {
                    "field_min": SimpleNamespace(
                        location="Nodal",
                        component_count=1,
                        scoping=SimpleNamespace(size=1),
                        unit="m",
                    ),
                    "field_max": RuntimeError("boom"),
                },
            ),
        )

        with mock.patch.object(service, "_dpf_module", return_value=fake_dpf):
            with self.assertRaises(DpfOperatorInvocationError) as exc_info:
                service.invoke_operator(
                    "dpf.field_ops",
                    inputs={"field": fields_ref},
                    properties={"operation": "min_max", "location": ""},
                )

        self.assertIn("min_max.min_max_fc", str(exc_info.exception))
        self.assertIn("dpf.field_ops", str(exc_info.exception))
        self.assertIn("boom", str(exc_info.exception))

    def test_invoke_generated_operator_uses_source_path_and_materializes_helper_handles(self) -> None:
        services = WorkerServices()
        service = services.dpf_runtime_service
        capture: dict[str, object] = {}

        data_sources = object()
        streams_container = object()
        mesh = object()
        mesh_scoping = _FakeScoping(ids=[3, 4], location="Nodal")
        data_sources_ref = services.register_handle(
            data_sources,
            kind=DPF_OBJECT_HANDLE_KIND,
            owner_scope="run:generated_operator",
            metadata={"dpf_data_type": DPF_DATA_SOURCES_DATA_TYPE},
        )
        streams_container_ref = services.register_handle(
            streams_container,
            kind=DPF_OBJECT_HANDLE_KIND,
            owner_scope="run:generated_operator",
            metadata={"dpf_data_type": DPF_STREAMS_CONTAINER_DATA_TYPE},
        )
        mesh_ref = services.register_handle(
            mesh,
            kind=DPF_MESH_HANDLE_KIND,
            owner_scope="run:generated_operator",
        )
        mesh_scoping_ref = services.register_handle(
            mesh_scoping,
            kind=DPF_MESH_SCOPING_HANDLE_KIND,
            owner_scope="run:generated_operator",
            metadata={"ids": [3, 4], "location": "Nodal"},
        )
        fake_dpf = _fake_dpf_module(
            result_factory=_capturing_factory(capture, {"fields_container": "generated_output"}),
        )

        with mock.patch.object(service, "_dpf_module", return_value=fake_dpf):
            invocation = service.invoke_operator(
                "dpf.op.result.displacement",
                inputs={
                    "data_sources": data_sources_ref,
                    "streams_container": streams_container_ref,
                    "mesh": mesh_ref,
                    "mesh_scoping": mesh_scoping_ref,
                },
                properties={},
            )

        self.assertEqual(invocation.operator_name, "result.displacement")
        self.assertEqual(invocation.outputs["fields_container_2"], "generated_output")

        operator = capture["operator"]
        self.assertIsInstance(operator, _FakeOperator)
        self.assertIs(operator.inputs.calls["data_sources"], data_sources)
        self.assertIs(operator.inputs.calls["streams_container"], streams_container)
        self.assertIs(operator.inputs.calls["mesh"], mesh)
        self.assertIs(operator.inputs.calls["mesh_scoping"], mesh_scoping)


if __name__ == "__main__":
    unittest.main()
