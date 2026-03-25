from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

dpf = pytest.importorskip("ansys.dpf.core")

from ansys_dpf_core.fixture_paths import MODAL_ANALYSIS_RST, STATIC_ANALYSIS_RST, THERMAL_ANALYSIS_RTH
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
from ea_node_editor.execution.worker_services import WorkerServices


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


if __name__ == "__main__":
    unittest.main()
