from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

dpf = pytest.importorskip("ansys.dpf.core")
np = pytest.importorskip("numpy")

from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST
import ea_node_editor.execution.dpf_runtime.materialization as materialization_module
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
)
from ea_node_editor.execution.worker_services import WorkerServices
from tests.typed_handle_support import dpf_worker_services
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELDS_CONTAINER_DATA_TYPE,
)
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.runtime_contracts import PATH_DATA_TYPE_ID

_BOLT_NAMED_SELECTION = "BOLT_NODES"


def _register_synthetic_container(
    services: WorkerServices,
    values_by_set: dict[int, list[float]],
    *,
    run_id: str,
    result_name: str = "synthetic",
) -> object:
    container = dpf.FieldsContainer()
    container.labels = ["time"]
    for set_id, values in values_by_set.items():
        field = dpf.fields_factory.field_from_array(np.asarray(values, dtype=float))
        field.scoping = dpf.Scoping(ids=list(range(1, len(values) + 1)), location="Nodal")
        container.add_field({"time": int(set_id)}, field)
    return services.register_handle(
        container,
        data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
        kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        owner_scope=services.run_owner_scope(run_id),
        metadata={"result_name": result_name},
    )


def _bolt_mesh_scoping(service, services: WorkerServices, model_ref, *, run_id: str):
    model = services.resolve_handle(model_ref)
    named_selection = model.metadata.named_selection(_BOLT_NAMED_SELECTION)
    node_ids = [int(item) for item in named_selection.ids]
    return (
        service.create_mesh_scoping(node_ids, location="nodal", run_id=run_id),
        node_ids,
    )


def _container_values_by_entity(container) -> list[dict[int, float]]:
    values: list[dict[int, float]] = []
    for index in range(len(container)):
        field = container[index]
        data = np.asarray(field.data, dtype=float).reshape(-1)
        ids = [int(item) for item in field.scoping.ids]
        values.append(dict(zip(ids, data.tolist())))
    return values


class DpfComputeInvariantTests(unittest.TestCase):
    def test_von_mises_principal_ordering_and_derived_identities(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        stress_ref = service.extract_result_fields(
            model=model_ref,
            result_name="stress",
            set_ids=[1],
            run_id="run_invariant",
        )

        von_mises_ref = service.compute_invariant(
            stress_ref, invariant="von_mises", run_id="run_invariant"
        )
        von_mises = services.resolve_handle(
            von_mises_ref, expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND
        )
        source = services.resolve_handle(stress_ref)
        self.assertEqual(int(von_mises[0].component_count), 1)
        self.assertEqual(int(von_mises[0].scoping.size), int(source[0].scoping.size))
        self.assertTrue(bool(np.all(np.asarray(von_mises[0].data) >= 0.0)))
        self.assertEqual(von_mises_ref.metadata["operation"], "von_mises")
        self.assertEqual(von_mises_ref.metadata["result_name"], "stress")
        self.assertEqual(von_mises_ref.metadata["source_handle_id"], stress_ref.handle_id)

        principal_refs = {
            token: service.compute_invariant(stress_ref, invariant=token, run_id="run_invariant")
            for token in ("principal_1", "principal_2", "principal_3")
        }
        principal_data = {
            token: np.asarray(services.resolve_handle(ref)[0].data, dtype=float)
            for token, ref in principal_refs.items()
        }
        self.assertTrue(
            bool(np.all(principal_data["principal_1"] >= principal_data["principal_2"] - 1e-6))
        )
        self.assertTrue(
            bool(np.all(principal_data["principal_2"] >= principal_data["principal_3"] - 1e-6))
        )

        intensity_ref = service.compute_invariant(
            stress_ref, invariant="intensity", run_id="run_invariant"
        )
        intensity = np.asarray(services.resolve_handle(intensity_ref)[0].data, dtype=float)
        self.assertTrue(
            bool(
                np.allclose(
                    intensity,
                    principal_data["principal_1"] - principal_data["principal_3"],
                    rtol=1e-4,
                    atol=1e-3,
                )
            )
        )

        max_shear_ref = service.compute_invariant(
            stress_ref, invariant="max_shear", run_id="run_invariant"
        )
        max_shear = np.asarray(services.resolve_handle(max_shear_ref)[0].data, dtype=float)
        self.assertTrue(bool(np.allclose(max_shear, intensity / 2.0, rtol=1e-5)))

    def test_rejects_non_tensor_input_and_unknown_invariant(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        displacement_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1],
            run_id="run_invariant_errors",
        )

        with self.assertRaisesRegex(ValueError, "6-component tensor"):
            service.compute_invariant(
                displacement_ref, invariant="von_mises", run_id="run_invariant_errors"
            )
        with self.assertRaisesRegex(ValueError, "invariant must be one of"):
            service.compute_invariant(
                displacement_ref, invariant="bogus", run_id="run_invariant_errors"
            )


class DpfCombineFieldsContainersTests(unittest.TestCase):
    def test_operations_match_reference_arithmetic(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        a_ref = _register_synthetic_container(
            services, {1: [1.0, 2.0, 4.0]}, run_id="run_math", result_name="stress"
        )
        b_ref = _register_synthetic_container(services, {1: [3.0, 5.0, 8.0]}, run_id="run_math")

        expected = {
            "add": [4.0, 7.0, 12.0],
            "subtract": [-2.0, -3.0, -4.0],
            "multiply": [3.0, 10.0, 32.0],
            "divide": [1.0 / 3.0, 2.0 / 5.0, 0.5],
        }
        for operation, expected_values in expected.items():
            result_ref = service.combine_fields_containers(
                a_ref, b_ref, operation=operation, run_id="run_math"
            )
            result = services.resolve_handle(
                result_ref, expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND
            )
            self.assertTrue(
                bool(np.allclose(np.asarray(result[0].data, dtype=float).reshape(-1), expected_values)),
                msg=f"operation {operation} produced unexpected values",
            )
            self.assertEqual(result_ref.metadata["operation"], operation)
            self.assertEqual(result_ref.metadata["source_handle_id"], a_ref.handle_id)
            self.assertEqual(result_ref.metadata["second_handle_id"], b_ref.handle_id)
            self.assertEqual(result_ref.metadata["result_name"], "stress")

        scaled_ref = service.combine_fields_containers(
            a_ref, operation="scale", scalar=2.5, run_id="run_math"
        )
        scaled = services.resolve_handle(scaled_ref)
        self.assertTrue(
            bool(np.allclose(np.asarray(scaled[0].data, dtype=float).reshape(-1), [2.5, 5.0, 10.0]))
        )
        self.assertEqual(scaled_ref.metadata["scalar"], 2.5)

    def test_operand_validation_errors(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        a_ref = _register_synthetic_container(services, {1: [1.0, 2.0]}, run_id="run_math_errors")
        b_ref = _register_synthetic_container(services, {1: [3.0, 4.0]}, run_id="run_math_errors")

        with self.assertRaisesRegex(ValueError, "operation must be one of"):
            service.combine_fields_containers(a_ref, b_ref, operation="power", run_id="run_math_errors")
        with self.assertRaisesRegex(ValueError, "requires a second fields container"):
            service.combine_fields_containers(a_ref, operation="subtract", run_id="run_math_errors")
        with self.assertRaisesRegex(ValueError, "uses only input A"):
            service.combine_fields_containers(
                a_ref, b_ref, operation="scale", scalar=2.0, run_id="run_math_errors"
            )


class DpfMinMaxEnvelopeTests(unittest.TestCase):
    def test_envelope_on_static_displacement_named_selection(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        mesh_ref, node_ids = _bolt_mesh_scoping(service, services, model_ref, run_id="run_envelope")
        displacement_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1, 2],
            mesh_scoping=mesh_ref,
            run_id="run_envelope",
        )

        envelope = service.compute_min_max_envelope(
            displacement_ref, model=model_ref, run_id="run_envelope"
        )

        self.assertEqual(len(envelope.per_set_rows), 2)
        self.assertEqual([row["set_id"] for row in envelope.per_set_rows], [1, 2])
        self.assertEqual([row["time_value"] for row in envelope.per_set_rows], [1.0, 2.0])
        for row in envelope.per_set_rows:
            self.assertIn(row["min_entity_id"], node_ids)
            self.assertIn(row["max_entity_id"], node_ids)
            self.assertLessEqual(row["min"], row["max"])

        self.assertEqual(
            envelope.overall["max"]["value"],
            max(row["max"] for row in envelope.per_set_rows),
        )
        self.assertEqual(
            envelope.overall["min"]["value"],
            min(row["min"] for row in envelope.per_set_rows),
        )
        self.assertEqual(envelope.overall["location"], "Nodal")
        coordinates = envelope.overall["max"]["coordinates"]
        self.assertIsInstance(coordinates, list)
        self.assertEqual(len(coordinates), 3)

        envelope_max = services.resolve_handle(
            envelope.envelope_max, expected_kind=DPF_FIELD_HANDLE_KIND
        )
        envelope_min = services.resolve_handle(
            envelope.envelope_min, expected_kind=DPF_FIELD_HANDLE_KIND
        )
        self.assertEqual(int(envelope_max.scoping.size), len(node_ids))
        self.assertEqual(envelope.envelope_max.metadata["reduction"], "envelope_max")
        self.assertEqual(envelope.envelope_min.metadata["reduction"], "envelope_min")

        source = services.resolve_handle(displacement_ref)
        norms_by_set = []
        for index in range(len(source)):
            data = np.asarray(source[index].data, dtype=float).reshape(len(node_ids), -1)
            ids = [int(item) for item in source[index].scoping.ids]
            norms_by_set.append(dict(zip(ids, np.linalg.norm(data, axis=1).tolist())))
        for position, entity_id in enumerate(int(item) for item in envelope_max.scoping.ids):
            expected_max = max(norms[entity_id] for norms in norms_by_set)
            expected_min = min(norms[entity_id] for norms in norms_by_set)
            self.assertAlmostEqual(
                float(np.asarray(envelope_max.data).reshape(-1)[position]), expected_max, places=9
            )
            self.assertAlmostEqual(
                float(np.asarray(envelope_min.data).reshape(-1)[position]), expected_min, places=9
            )

    def test_envelope_rejects_tensor_input(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        stress_ref = service.extract_result_fields(
            model=model_ref,
            result_name="stress",
            set_ids=[1],
            run_id="run_envelope_errors",
        )
        with self.assertRaisesRegex(ValueError, "6-component tensor"):
            service.compute_min_max_envelope(
                stress_ref, model=model_ref, run_id="run_envelope_errors"
            )


class DpfTimeHistorySeriesTests(unittest.TestCase):
    def test_series_holds_one_field_per_probed_entity(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        mesh_ref, node_ids = _bolt_mesh_scoping(service, services, model_ref, run_id="run_history")
        displacement_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1, 2],
            mesh_scoping=mesh_ref,
            run_id="run_history",
        )

        history = service.build_time_history_series(
            displacement_ref, model=model_ref, run_id="run_history"
        )

        self.assertEqual(sorted(history.entity_ids), sorted(node_ids))
        self.assertEqual(history.time_values, (1.0, 2.0))
        self.assertEqual(len(history.rows), len(node_ids) * 2)

        series = services.resolve_handle(
            history.series, expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND
        )
        self.assertEqual(len(series), len(node_ids))
        self.assertEqual(tuple(series.labels), ("entity",))
        for index in range(len(series)):
            field = series[index]
            self.assertEqual(int(field.scoping.size), 2)
            self.assertEqual([int(item) for item in field.scoping.ids], [1, 2])
            self.assertEqual(str(field.scoping.location), "TimeFreq")

        self.assertEqual(history.series.metadata["x_axis"], "time")
        self.assertEqual(history.series.metadata["time_values"], [1.0, 2.0])
        self.assertEqual(
            sorted(history.series.metadata["entity_ids"]), sorted(node_ids)
        )

        source = services.resolve_handle(displacement_ref)
        source_norms = []
        for index in range(len(source)):
            data = np.asarray(source[index].data, dtype=float).reshape(len(node_ids), -1)
            ids = [int(item) for item in source[index].scoping.ids]
            source_norms.append(dict(zip(ids, np.linalg.norm(data, axis=1).tolist())))
        for row in history.rows:
            expected = source_norms[row["set_id"] - 1][row["entity_id"]]
            self.assertAlmostEqual(row["value"], expected, places=9)


class DpfTableExportTests(unittest.TestCase):
    def test_table_export_writes_csv_with_coordinates(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        mesh_ref, node_ids = _bolt_mesh_scoping(service, services, model_ref, run_id="run_table")
        displacement_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1, 2],
            mesh_scoping=mesh_ref,
            run_id="run_table",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProjectArtifactStore(
                project_path=Path(temp_dir) / "table_demo.cxproj",
                metadata=None,
            )
            result = service.export_field_table(
                displacement_ref,
                model=model_ref,
                artifact_store=store,
                artifact_key="bolt_history",
            )

            self.assertEqual(
                result.columns,
                (
                    "entity_id",
                    "x",
                    "y",
                    "z",
                    "set_id",
                    "time_value",
                    "comp_1",
                    "comp_2",
                    "comp_3",
                    "magnitude",
                ),
            )
            self.assertEqual(len(result.rows), len(node_ids) * 2)

            model = services.resolve_handle(model_ref)
            coordinates_field = model.metadata.meshed_region.nodes.coordinates_field
            coordinate_ids = [int(item) for item in coordinates_field.scoping.ids]
            coordinates = np.asarray(coordinates_field.data, dtype=float).reshape(-1, 3)
            for row in result.rows[: len(node_ids)]:
                reference = coordinates[coordinate_ids.index(row["entity_id"])]
                self.assertAlmostEqual(row["x"], float(reference[0]), places=9)
                self.assertAlmostEqual(row["y"], float(reference[1]), places=9)
                self.assertAlmostEqual(row["z"], float(reference[2]), places=9)
                self.assertAlmostEqual(
                    row["magnitude"],
                    float(np.linalg.norm([row["comp_1"], row["comp_2"], row["comp_3"]])),
                    places=9,
                )

            self.assertIsNotNone(result.csv_artifact)
            self.assertEqual(result.csv_artifact.data_type_id, PATH_DATA_TYPE_ID)
            self.assertEqual(result.csv_artifact.schema_version, 1)
            self.assertEqual(result.csv_artifact.format, "csv")
            self.assertNotIn("format", result.csv_artifact.metadata)
            self.assertNotIn("absolute_path", result.csv_artifact.metadata)
            self.assertNotIn("relative_path", result.csv_artifact.metadata)
            csv_path = store.resolve_staged_path(result.csv_artifact.ref)
            self.assertIsNotNone(csv_path)
            csv_lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(csv_lines[0], ",".join(result.columns))
            self.assertEqual(len(csv_lines), len(result.rows) + 1)

    def test_table_export_rerun_rolls_back_registration_failure_before_mutation(
        self,
    ) -> None:
        self._assert_table_rerun_rollback(registration_mutates=False)

    def test_table_export_rerun_rolls_back_registration_failure_after_mutation(
        self,
    ) -> None:
        self._assert_table_rerun_rollback(registration_mutates=True)

    def test_table_export_rejects_no_id_intermediate_reparse_before_write(
        self,
    ) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        displacement_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1],
            run_id="run_table_prewrite_reparse",
        )
        artifact_key = "table_prewrite_reparse"
        artifact_id = f"dpf.{artifact_key}.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            store = ProjectArtifactStore(project_path=None, metadata=None)
            root = store.ensure_staging_root(temporary_root_parent=parent)
            artifact_paths = store.node_artifact_paths(
                artifact_id=artifact_id,
                workspace_id="workspace",
                workspace_name="Workspace",
                node_id="node",
                node_title="DPF Table Export",
                node_type="DPF Table Export",
                io_dir="out",
                subdirectory=f"dpf/{artifact_key}",
                filename="table.csv",
            )
            relative_parts = PurePosixPath(
                artifact_paths.staged_relative_path
            ).parts
            reparse_directory = root.joinpath(*relative_parts[:-1])
            reparse_directory.mkdir(parents=True)
            expected_target = root.joinpath(*relative_parts)
            outside_sentinel = parent / "outside-table-sentinel.txt"
            outside_sentinel.write_text("outside", encoding="utf-8")
            root_hint = store.staging_root_hint
            original_state = store.state
            reparse_key = os.path.normcase(os.path.abspath(reparse_directory))
            real_lstat = os.lstat
            real_mkdir = Path.mkdir
            mkdir_calls: list[Path] = []

            def reparse_lstat(path: str | os.PathLike[str]) -> object:
                result = real_lstat(path)
                if os.path.normcase(os.path.abspath(path)) == reparse_key:
                    return SimpleNamespace(
                        st_mode=result.st_mode,
                        st_file_attributes=0x400,
                    )
                return result

            def tracked_mkdir(path: Path, *args: Any, **kwargs: Any) -> None:
                mkdir_calls.append(Path(path))
                real_mkdir(path, *args, **kwargs)

            with (
                patch(
                    "ea_node_editor.persistence.artifact_store.os.lstat",
                    side_effect=reparse_lstat,
                ),
                patch.object(
                    Path,
                    "mkdir",
                    autospec=True,
                    side_effect=tracked_mkdir,
                ),
                patch.object(
                    service,
                    "_clear_output_path",
                ) as clear_path,
                patch.object(
                    service,
                    "_write_table_csv",
                ) as write_table,
                patch.object(
                    store,
                    "staged_target_path",
                    wraps=store.staged_target_path,
                ) as resolve_target,
                patch.object(
                    materialization_module,
                    "register_staged_artifact",
                ) as register_artifact,
                self.assertRaises(ValueError) as caught,
            ):
                service.export_field_table(
                    displacement_ref,
                    model=model_ref,
                    artifact_store=store,
                    artifact_key=artifact_key,
                    temporary_root_parent=parent,
                    node_workspace_id="workspace",
                    node_workspace_name="Workspace",
                    node_id="node",
                    node_title="DPF Table Export",
                    node_type="DPF Table Export",
                )

            self.assertEqual(
                str(caught.exception),
                "staged artifact discard target is unsafe",
            )
            self.assertNotIn(str(root), str(caught.exception))
            self.assertNotIn(str(outside_sentinel), str(caught.exception))
            self.assertIsNone(store.staged_entry(artifact_id))
            self.assertIs(store.state, original_state)
            self.assertEqual(store.active_staging_root(), root)
            self.assertIs(store.staging_root_hint, root_hint)
            self.assertEqual(store.metadata["staged"], {})
            self.assertTrue(root.exists())
            self.assertTrue(reparse_directory.exists())
            self.assertFalse(expected_target.exists())
            self.assertEqual(
                outside_sentinel.read_text(encoding="utf-8"),
                "outside",
            )
            self.assertNotIn(reparse_directory, mkdir_calls)
            clear_path.assert_not_called()
            write_table.assert_not_called()
            resolve_target.assert_not_called()
            register_artifact.assert_not_called()

    def _assert_table_rerun_rollback(self, *, registration_mutates: bool) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        displacement_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1],
            run_id="run_table_rollback",
        )
        failure_marker = (
            "table registration failed after mutation"
            if registration_mutates
            else "table registration failed before mutation"
        )
        original_error = RuntimeError(failure_marker)
        new_payload = f"{failure_marker}\n".encode()
        original_register = materialization_module.register_staged_artifact

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProjectArtifactStore(project_path=None, metadata=None)
            seeded_result = service.export_field_table(
                displacement_ref,
                model=model_ref,
                artifact_store=store,
                artifact_key="table_rollback",
                temporary_root_parent=temp_dir,
            )
            seeded_ref = seeded_result.csv_artifact
            self.assertIsNotNone(seeded_ref)
            if seeded_ref is None:
                self.fail("Expected seeded table artifact")
            seeded_descriptor = seeded_ref.to_descriptor()
            seeded_relative_path = store.metadata["staged"][
                seeded_ref.artifact_id
            ]["relative_path"]
            seeded_path = store.resolve_staged_path(seeded_ref.ref)
            self.assertIsNotNone(seeded_path)
            if seeded_path is None:
                self.fail("Expected seeded table path")
            root = store.active_staging_root()
            self.assertIsNotNone(root)
            if root is None:
                self.fail("Expected an unsaved-project staging root")
            root_hint = store.staging_root_hint

            unrelated_paths = store.node_artifact_paths(
                artifact_id="unrelated-table",
                workspace_id="unrelated_workspace",
                node_id="unrelated_node",
                node_title="Unrelated",
                node_type="Unrelated",
                io_dir="out",
                filename="keep.bin",
            )
            unrelated_payload = store.staged_target_path(
                unrelated_paths.staged_relative_path
            )
            unrelated_payload.parent.mkdir(parents=True, exist_ok=True)
            unrelated_payload.write_bytes(b"unrelated-table-payload")
            store.register_staged_entry(
                "unrelated-table",
                relative_path=unrelated_paths.staged_relative_path,
                extra=unrelated_paths.metadata,
            )
            sentinel = root / "unrelated-table.txt"
            sentinel.write_text("keep", encoding="utf-8")

            def write_new_table(
                output_path: Path,
                _rows: Any,
                _columns: Any,
            ) -> None:
                Path(output_path).write_bytes(new_payload)

            def fail_registration(**kwargs: Any) -> Any:
                self.assertEqual(
                    Path(kwargs["payload_path"]).read_bytes(),
                    new_payload,
                )
                if registration_mutates:
                    original_register(**kwargs)
                    self.assertNotEqual(
                        store.metadata["staged"][seeded_ref.artifact_id][
                            "runtime_artifact"
                        ],
                        seeded_descriptor,
                    )
                else:
                    self.assertNotIn(
                        seeded_ref.artifact_id,
                        store.metadata["staged"],
                    )
                raise original_error

            with (
                patch.object(
                    service,
                    "_write_table_csv",
                    side_effect=write_new_table,
                ),
                patch.object(
                    materialization_module,
                    "register_staged_artifact",
                    side_effect=fail_registration,
                ),
                patch.object(
                    store,
                    "discard_staged_paths",
                    wraps=store.discard_staged_paths,
                ) as discard_paths,
            ):
                with self.assertRaises(RuntimeError) as raised:
                    service.export_field_table(
                        displacement_ref,
                        model=model_ref,
                        artifact_store=store,
                        artifact_key="table_rollback",
                        temporary_root_parent=temp_dir,
                    )

            self.assertIs(raised.exception, original_error)
            self.assertEqual(raised.exception.args, (failure_marker,))
            self.assertEqual(discard_paths.call_count, 2)
            discard_paths.assert_called_with((seeded_relative_path,))
            self.assertNotIn(seeded_ref.artifact_id, store.metadata["staged"])
            self.assertFalse(seeded_path.exists())
            self.assertEqual(
                set(store.metadata["staged"]),
                {"unrelated-table"},
            )
            self.assertEqual(
                unrelated_payload.read_bytes(),
                b"unrelated-table-payload",
            )
            self.assertEqual(store.active_staging_root(), root)
            self.assertIs(store.staging_root_hint, root_hint)
            self.assertTrue(root.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_table_export_memory_profile_skips_csv_and_guards_elemental_nodal(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        displacement_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1],
            run_id="run_table_memory",
        )

        result = service.export_field_table(
            displacement_ref,
            model=model_ref,
            output_profile="memory",
            include_coordinates=False,
        )
        self.assertIsNone(result.csv_artifact)
        self.assertEqual(
            result.columns,
            ("entity_id", "set_id", "time_value", "comp_1", "comp_2", "comp_3", "magnitude"),
        )
        self.assertNotIn("x", result.rows[0])

        stress_ref = service.extract_result_fields(
            model=model_ref,
            result_name="stress",
            set_ids=[1],
            run_id="run_table_memory",
        )
        with self.assertRaisesRegex(ValueError, "one row of values per scoped entity"):
            service.export_field_table(
                stress_ref,
                model=model_ref,
                output_profile="memory",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
