from __future__ import annotations

import json
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
from ea_node_editor.execution.plot_backend import normalize_dpf_plot_frame_selector
from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from tests.typed_handle_support import dpf_worker_services
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_DATA_SOURCES_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_RESULT_FILE_DATA_TYPE,
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


def _fake_model(*, location: str = "TimeFreq", part_names: object = ()) -> SimpleNamespace:
    return SimpleNamespace(
        metadata=SimpleNamespace(
            data_sources="fake_data_sources",
            meshed_region="fake_mesh",
            mesh_info=SimpleNamespace(part_names=part_names),
            time_freq_support=SimpleNamespace(
                time_frequencies=SimpleNamespace(
                    scoping=SimpleNamespace(location=location),
                )
            ),
        )
    )


class DpfRuntimeServiceTests(unittest.TestCase):
    def test_dpf_plot_frame_selector_supports_set_ids_and_frame_positions(self) -> None:
        by_set_id = normalize_dpf_plot_frame_selector(
            "7",
            frame_count=3,
            label_spaces=({"time": 1}, {"time": 4}, {"time": 7}),
        )
        by_position = normalize_dpf_plot_frame_selector(
            "2",
            frame_count=3,
            label_spaces=({"time": 10}, {"time": 20}, {"time": 30}),
        )

        self.assertEqual(by_set_id.selected_indices, (2,))
        self.assertEqual(by_set_id.selected_set_ids, (7,))
        self.assertEqual(by_position.selected_indices, (1,))
        self.assertEqual(by_position.selected_set_ids, (20,))

    def test_worker_services_lazy_service_defers_optional_dpf_import(self) -> None:
        services = dpf_worker_services()

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
        services = dpf_worker_services()
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

    def test_model_part_names_preserve_raw_order_duplicates_and_survive_reset(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        expected = (" leading", "duplicate", "duplicate", "trailing ", " \t ")
        provider_names = list(expected)
        disposed: list[str] = []
        model_ref = services.register_handle(
            _fake_model(part_names=provider_names),
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="run:model_part_names",
            dispose=lambda: disposed.append("model"),
        )

        names = service.model_part_names(model_ref)

        self.assertIs(type(names), tuple)
        self.assertEqual(names, expected)
        self.assertTrue(all(type(name) is str for name in names))
        with self.assertRaises(TypeError):
            names[0] = "changed"  # type: ignore[index]

        provider_names.clear()
        self.assertEqual(service.model_part_names(model_ref), ())
        self.assertEqual(services.reset(), 1)
        self.assertEqual(disposed, ["model"])
        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        self.assertEqual(names, expected)

    def test_model_part_names_reject_unsupported_malformed_and_oversized_providers(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        unsupported_error = "DPF model does not support metadata.mesh_info.part_names."

        class RaisingPartNames:
            def __init__(self, error: Exception) -> None:
                self.error = error

            @property
            def part_names(self) -> object:
                raise self.error

        class BrokenIterable:
            def __init__(self, error: Exception) -> None:
                self.error = error

            def __iter__(self):
                raise self.error

        class BrokenIterator:
            def __init__(self, error: Exception) -> None:
                self.error = error
                self.yielded = False

            def __iter__(self):
                return self

            def __next__(self) -> str:
                if not self.yielded:
                    self.yielded = True
                    return "partial"
                raise self.error

        class CountOverflowProvider:
            def __init__(self) -> None:
                self.pulls = 0

            def __iter__(self):
                return self

            def __next__(self) -> str:
                self.pulls += 1
                if self.pulls <= 4_097:
                    return "part"
                raise AssertionError("item 4,098 was pulled")

        class StringSubclass(str):
            pass

        def register_model(model: object):
            return services.register_handle(
                model,
                data_type_id=DPF_MODEL_DATA_TYPE,
                kind=DPF_MODEL_HANDLE_KIND,
                owner_scope="run:model_part_names_failures",
            )

        def project(part_names: object) -> tuple[str, ...]:
            return service.model_part_names(register_model(_fake_model(part_names=part_names)))

        def assert_unsupported(model: object) -> None:
            with self.assertRaises(DpfOperatorInvocationError) as caught:
                service.model_part_names(register_model(model))
            self.assertEqual(str(caught.exception), unsupported_error)
            self.assertIsNone(caught.exception.__cause__)
            self.assertNotIn("native", str(caught.exception))

        for error_type in (TypeError, ValueError):
            with self.subTest(stage="acquisition", error_type=error_type.__name__):
                model = _fake_model()
                model.metadata.mesh_info = RaisingPartNames(
                    error_type("native acquisition detail")
                )
                assert_unsupported(model)
            with self.subTest(stage="iterator", error_type=error_type.__name__):
                assert_unsupported(
                    _fake_model(
                        part_names=BrokenIterable(error_type("native iterator detail"))
                    )
                )
            with self.subTest(stage="next", error_type=error_type.__name__):
                assert_unsupported(
                    _fake_model(part_names=BrokenIterator(error_type("native next detail")))
                )

        public_type_errors = (
            ("noniterable", 42),
            ("string", "part"),
            ("bytes", b"part"),
            ("bytearray", bytearray(b"part")),
            ("memoryview", memoryview(b"part")),
            ("non_string_item", [object()]),
            ("string_subclass_item", [StringSubclass("part")]),
            ("unencodable_string", ["\ud800"]),
        )
        for case, part_names in public_type_errors:
            with self.subTest(case=case):
                with self.assertRaises(TypeError):
                    project(part_names)

        with self.assertRaises(ValueError):
            project([""])

        count_overflow = CountOverflowProvider()
        with self.assertRaises(ValueError):
            project(count_overflow)
        self.assertEqual(count_overflow.pulls, 4_097)

        maximum_name = "x" * (64 * 1024)
        self.assertEqual(project([maximum_name]), (maximum_name,))
        with self.assertRaises(ValueError):
            project([maximum_name, "x"])

        self.assertEqual(project(["clean", "complete"]), ("clean", "complete"))

    def test_cached_result_and_model_lease_once_per_requesting_run(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service

        cached_result = service.load_result_file(STATIC_ANALYSIS_RST)
        result_a = service.load_result_file(
            STATIC_ANALYSIS_RST,
            run_id="dpf_a",
        )
        repeated_result_a = service.load_result_file(
            result_a,
            run_id="dpf_a",
        )
        result_b = service.load_result_file(
            STATIC_ANALYSIS_RST,
            run_id="dpf_b",
        )
        cached_model = service.load_model(STATIC_ANALYSIS_RST)
        model_a = service.load_model(STATIC_ANALYSIS_RST, run_id="dpf_a")
        repeated_model_a = service.load_model(model_a, run_id="dpf_a")
        model_b = service.load_model(STATIC_ANALYSIS_RST, run_id="dpf_b")

        self.assertEqual(
            {
                cached_result.handle_id,
                result_a.handle_id,
                repeated_result_a.handle_id,
                result_b.handle_id,
            },
            {cached_result.handle_id},
        )
        self.assertEqual(
            {
                cached_model.handle_id,
                model_a.handle_id,
                repeated_model_a.handle_id,
                model_b.handle_id,
            },
            {cached_model.handle_id},
        )
        for runtime_ref in (cached_result, cached_model):
            for owner_scope in (
                runtime_ref.owner_scope,
                "run:dpf_a",
                "run:dpf_b",
            ):
                self.assertEqual(
                    services.handle_registry.lease_count(
                        runtime_ref,
                        owner_scope=owner_scope,
                    ),
                    1,
                )

        services.cleanup_run("dpf_a")
        for runtime_ref in (cached_result, cached_model):
            self.assertEqual(
                services.handle_registry.lease_count(
                    runtime_ref,
                    owner_scope="run:dpf_a",
                ),
                0,
            )
        services.resolve_handle(
            cached_result,
            expected_kind=DPF_RESULT_FILE_HANDLE_KIND,
        )
        services.resolve_handle(
            cached_model,
            expected_kind=DPF_MODEL_HANDLE_KIND,
        )
        services.resolve_handle(
            result_b,
            expected_kind=DPF_RESULT_FILE_HANDLE_KIND,
        )
        services.resolve_handle(
            model_b,
            expected_kind=DPF_MODEL_HANDLE_KIND,
        )

    def test_invalid_cached_result_releases_owner_before_replacement(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        result_path = Path(STATIC_ANALYSIS_RST).resolve()
        cache_key = service._cache_key(result_path)  # noqa: SLF001
        owner_scope = service._cache_owner_scope("result_file", cache_key)  # noqa: SLF001
        disposed_while_cached: list[bool] = []

        stale_ref = services.register_handle(
            object(),
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope=owner_scope,
            dispose=lambda: disposed_while_cached.append(
                cache_key in service._result_file_cache  # noqa: SLF001
            ),
        )
        service._result_file_cache[cache_key] = stale_ref  # noqa: SLF001

        replacement_ref = service.load_result_file(result_path)

        self.assertEqual(disposed_while_cached, [True])
        self.assertNotEqual(replacement_ref.handle_id, stale_ref.handle_id)
        self.assertEqual(replacement_ref.data_type_id, DPF_RESULT_FILE_DATA_TYPE)
        self.assertEqual(
            service._result_file_cache[cache_key].handle_id,  # noqa: SLF001
            replacement_ref.handle_id,
        )

    def test_scoping_helpers_create_worker_local_handles_and_run_cleanup_releases_them(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service

        model_ref = service.load_model(MODAL_ANALYSIS_RST)
        model = services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        time_ref = service.create_time_scoping([1, 3], model=model_ref, run_id="run_scoping")
        mesh_ref = service.create_mesh_scoping([1, 2, 3], location="nodal", run_id="run_scoping")

        time_scoping = services.resolve_handle(time_ref, expected_kind=DPF_TIME_SCOPING_HANDLE_KIND)
        mesh_scoping = services.resolve_handle(mesh_ref, expected_kind=DPF_MESH_SCOPING_HANDLE_KIND)

        self.assertEqual([int(value) for value in time_scoping.ids], [1, 3])
        # Set ids are cumulative set numbers, so time scopings use the
        # cumulative-set location rather than the model's step-based location.
        self.assertEqual(time_scoping.location, dpf.locations.time_freq)
        self.assertEqual([int(value) for value in mesh_scoping.ids], [1, 2, 3])
        self.assertEqual(mesh_scoping.location, "Nodal")

        self.assertEqual(services.cleanup_run("run_scoping"), 2)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            services.resolve_handle(time_ref)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            services.resolve_handle(mesh_ref)

        self.assertIs(services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND), model)

    def test_large_mesh_scoping_uses_bounded_handle_metadata(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service

        mesh_ref = service.create_mesh_scoping(
            range(20_000),
            location="nodal",
            run_id="run_large_scoping",
        )

        self.assertEqual(mesh_ref.metadata["ids_count"], 20_000)
        self.assertEqual(mesh_ref.metadata["ids_sample"], list(range(16)))
        self.assertEqual(len(mesh_ref.metadata["ids_sha256"]), 64)
        self.assertNotIn("ids", mesh_ref.metadata)
        mesh_scoping = services.resolve_handle(
            mesh_ref,
            expected_kind=DPF_MESH_SCOPING_HANDLE_KIND,
        )
        self.assertEqual(len(mesh_scoping.ids), 20_000)

    def test_large_fields_metadata_is_deterministic_and_below_handle_limit(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        field = SimpleNamespace(
            location="Nodal",
            component_count=1,
            scoping=SimpleNamespace(size=1),
            unit="Pa",
            data=[1.0],
        )

        class _LargeFieldsContainer:
            labels = ("time",)

            def __len__(self) -> int:
                return 20_000

            def __getitem__(self, _index: int):
                return field

            @staticmethod
            def get_label_space(index: int) -> dict[str, int]:
                return {"time": index + 1}

        model = SimpleNamespace(
            metadata=SimpleNamespace(
                time_freq_support=SimpleNamespace(
                    time_frequencies=SimpleNamespace(
                        data=[float(index) for index in range(20_000)]
                    )
                )
            )
        )
        fields = _LargeFieldsContainer()

        first = service._build_fields_container_metadata(fields, model=model)
        second = service._build_fields_container_metadata(fields, model=model)
        encoded = json.dumps(
            first,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

        self.assertLess(len(encoded), 64 * 1024)
        self.assertEqual(first, second)
        for key in ("set_ids", "time_values", "value_ranges"):
            self.assertEqual(first[f"{key}_count"], 20_000)
            self.assertEqual(len(first[f"{key}_sample"]), 16)
            self.assertEqual(len(first[f"{key}_sha256"]), 64)
            self.assertNotIn(key, first)

    def test_reset_invalidates_cached_model_handles_and_rebuilds_service_cache(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service

        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        self.assertEqual(services.reset(), 2)

        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)

        reloaded_ref = service.load_model(STATIC_ANALYSIS_RST)
        self.assertNotEqual(model_ref.handle_id, reloaded_ref.handle_id)
        reloaded_model = services.resolve_handle(reloaded_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        self.assertEqual(reloaded_model.metadata.time_freq_support.n_sets, 2)

    def test_reset_warns_and_continues_when_model_stream_cleanup_fails(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        disposed: list[str] = []
        warnings: list[str] = []
        fake_model = _fake_model()

        def fail_release_streams() -> None:
            disposed.append("model")
            raise RuntimeError("private stream cleanup detail")

        fake_model.metadata.release_streams = fail_release_streams
        fake_dpf = SimpleNamespace(Model=lambda _path: fake_model)
        previous_generation = services.worker_generation
        with mock.patch.object(service, "_dpf_module", return_value=fake_dpf):
            model_ref = service.load_model(STATIC_ANALYSIS_RST)
            released_count = services.reset(warn=warnings.append)

        self.assertEqual(released_count, 2)
        self.assertEqual(disposed, ["model"])
        self.assertEqual(
            warnings,
            ["Runtime handle automatic disposal failed."],
        )
        self.assertEqual(service._model_cache, {})  # noqa: SLF001
        self.assertEqual(service._result_file_cache, {})  # noqa: SLF001
        self.assertEqual(services.worker_generation, previous_generation + 1)
        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)

    def test_hot_apply_disable_rebuilds_worker_runtime_and_reenable_restores_dpf_services(self) -> None:
        services = dpf_worker_services()
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
        services = dpf_worker_services()
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
        services = dpf_worker_services()
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
        services = dpf_worker_services()
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
            data_type_id=DPF_MODEL_DATA_TYPE,
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
        services = dpf_worker_services()
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
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
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
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        capture: dict[str, object] = {}

        data_sources = object()
        streams_container = object()
        mesh = object()
        mesh_scoping = _FakeScoping(ids=[3, 4], location="Nodal")
        data_sources_ref = services.register_handle(
            data_sources,
            data_type_id=DPF_DATA_SOURCES_DATA_TYPE,
            kind=DPF_OBJECT_HANDLE_KIND,
            owner_scope="run:generated_operator",
        )
        streams_container_ref = services.register_handle(
            streams_container,
            data_type_id=DPF_STREAMS_CONTAINER_DATA_TYPE,
            kind=DPF_OBJECT_HANDLE_KIND,
            owner_scope="run:generated_operator",
        )
        mesh_ref = services.register_handle(
            mesh,
            data_type_id=DPF_MESH_DATA_TYPE,
            kind=DPF_MESH_HANDLE_KIND,
            owner_scope="run:generated_operator",
        )
        mesh_scoping_ref = services.register_handle(
            mesh_scoping,
            data_type_id=DPF_SCOPING_DATA_TYPE,
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
