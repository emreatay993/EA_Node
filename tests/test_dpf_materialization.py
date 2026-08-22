from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from ea_node_editor.common.payload_tools import artifact_content_integrity
import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

pytest.importorskip("ansys.dpf.core")
pytest.importorskip("pyvista")

from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST, THERMAL_ANALYSIS_RTH
from ea_node_editor.execution.dpf_runtime import materialization as materialization_module
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_VIEWER_DATASET_HANDLE_KIND,
)
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_VIEWER_DATASET_DATA_TYPE,
)
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.runtime_contracts import PATH_DATA_TYPE_ID
from tests.typed_handle_support import dpf_worker_services


class DpfMaterializationTests(unittest.TestCase):
    def test_materialize_viewer_dataset_honors_output_profiles_and_stages_portable_exports(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service

        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        fields_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1, 2],
            run_id="run_materialize",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProjectArtifactStore(
                project_path=Path(temp_dir) / "viewer_demo.cxproj",
                metadata=None,
            )

            both_result = service.materialize_viewer_dataset(
                fields_ref,
                model=model_ref,
                output_profile="both",
                artifact_store=store,
                artifact_key="static_displacement",
                export_formats=("csv", "png", "vtu", "vtm"),
                run_id="run_materialize",
            )

            self.assertEqual(both_result.output_profile, "both")
            self.assertIsNotNone(both_result.dataset_ref)
            self.assertEqual(
                both_result.dataset_ref.data_type_id,
                DPF_VIEWER_DATASET_DATA_TYPE,
            )
            self.assertEqual(
                both_result.dataset_ref.schema_version,
                services.data_types.require(
                    DPF_VIEWER_DATASET_DATA_TYPE
                ).payload_schema_version,
            )
            self.assertEqual(set(both_result.artifacts), {"csv", "png", "vtu", "vtm"})
            self.assertEqual(both_result.summary["field_count"], 2)
            self.assertEqual(both_result.summary["set_ids"], [1, 2])

            time_values = both_result.summary["time_values"]
            self.assertEqual(len(time_values), 2)
            self.assertTrue(all(isinstance(value, float) for value in time_values))
            value_ranges = both_result.summary["value_ranges"]
            self.assertEqual(len(value_ranges), 2)
            for entry in value_ranges:
                self.assertLessEqual(entry["min"], entry["max"])
                self.assertEqual(len(entry["component_min"]), 3)
                self.assertEqual(len(entry["component_max"]), 3)
            self.assertGreater(value_ranges[0]["max"], 0.0)

            dataset = services.resolve_handle(
                both_result.dataset_ref,
                expected_kind=DPF_VIEWER_DATASET_HANDLE_KIND,
            )
            self.assertEqual(getattr(dataset, "n_blocks", 0), 2)

            csv_path = store.resolve_staged_path(both_result.artifacts["csv"].ref)
            png_path = store.resolve_staged_path(both_result.artifacts["png"].ref)
            vtu_path = store.resolve_staged_path(both_result.artifacts["vtu"].ref)
            vtm_path = store.resolve_staged_path(both_result.artifacts["vtm"].ref)

            self.assertIsNotNone(csv_path)
            self.assertIsNotNone(png_path)
            self.assertIsNotNone(vtu_path)
            self.assertIsNotNone(vtm_path)
            if csv_path is None or png_path is None or vtu_path is None or vtm_path is None:
                self.fail("Expected staged export paths to resolve through the artifact store")

            self.assertIn("num_sets,2", csv_path.read_text(encoding="utf-8"))
            self.assertGreater(png_path.stat().st_size, 0)
            self.assertEqual(len(list(vtu_path.glob("*.vtu"))), 2)
            self.assertTrue((vtm_path / "dataset.vtm").exists())
            for artifact_ref in both_result.artifacts.values():
                entry = store.staged_entry(artifact_ref.artifact_id)
                self.assertIsNotNone(entry)
                trusted_root = store.active_staging_root()
                self.assertIsNotNone(trusted_root)
                if (
                    entry is None
                    or entry.relative_path is None
                    or trusted_root is None
                ):
                    self.fail("Expected store-owned staged content target")
                self.assertEqual(
                    artifact_content_integrity(
                        trusted_root,
                        entry.relative_path,
                    ),
                    (artifact_ref.size_bytes, artifact_ref.sha256),
                )
                self.assertEqual(
                    store.metadata["staged"][artifact_ref.artifact_id][
                        "runtime_artifact"
                    ],
                    artifact_ref.to_descriptor(),
                )
                self.assertEqual(
                    artifact_ref.provenance,
                    "corex.ansys_dpf.materialization",
                )
            self.assertEqual(
                both_result.artifacts["png"].data_type_id,
                PATH_DATA_TYPE_ID,
            )
            self.assertEqual(
                both_result.artifacts["png"].schema_version,
                services.data_types.require(PATH_DATA_TYPE_ID).payload_schema_version,
            )
            self.assertEqual(both_result.artifacts["png"].format, "png")
            self.assertNotIn("format", both_result.artifacts["png"].metadata)
            self.assertNotIn("absolute_path", both_result.artifacts["png"].metadata)
            self.assertNotIn("relative_path", both_result.artifacts["png"].metadata)

            csv_entry = store.metadata["staged"][both_result.artifacts["csv"].artifact_id]
            self.assertNotIn("format", csv_entry)
            self.assertTrue(csv_entry["relative_path"].startswith("workspaces/"))
            self.assertIn("/nodes/", csv_entry["relative_path"])
            # Artifact store humanizes subdir separators ("_" -> " ") for readable folders.
            self.assertIn("/tmp/out/dpf/static displacement", csv_entry["relative_path"])
            for bundle_format in ("vtu", "vtm"):
                bundle_entry = store.metadata["staged"][
                    both_result.artifacts[bundle_format].artifact_id
                ]
                self.assertNotIn("format", bundle_entry)
                self.assertNotIn("files", bundle_entry)
                self.assertGreater(bundle_entry["file_count"], 0)

            memory_only = service.materialize_viewer_dataset(
                fields_ref,
                model=model_ref,
                output_profile="memory",
                run_id="run_memory_only",
            )
            self.assertIsNotNone(memory_only.dataset_ref)
            self.assertEqual(memory_only.artifacts, {})

            stored_only = service.materialize_viewer_dataset(
                fields_ref,
                model=model_ref,
                output_profile="stored",
                artifact_store=store,
                artifact_key="static_displacement_store",
                export_formats=("csv",),
                run_id="run_store_only",
            )
            self.assertIsNone(stored_only.dataset_ref)
            self.assertEqual(set(stored_only.artifacts), {"csv"})

    def test_export_field_artifacts_supports_rth_temperature_outputs(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service

        model_ref = service.load_model(THERMAL_ANALYSIS_RTH)
        fields_ref = service.extract_result_fields(
            model=model_ref,
            result_name="temperature",
            set_ids=[1],
            run_id="run_thermal_materialize",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProjectArtifactStore(
                project_path=Path(temp_dir) / "thermal_demo.cxproj",
                metadata=None,
            )
            artifacts = service.export_field_artifacts(
                fields_ref,
                model=model_ref,
                artifact_store=store,
                artifact_key="thermal_temperature",
                export_formats=("csv", "png"),
            )

            self.assertEqual(set(artifacts), {"csv", "png"})
            csv_path = store.resolve_staged_path(artifacts["csv"].ref)
            png_path = store.resolve_staged_path(artifacts["png"].ref)
            self.assertIsNotNone(csv_path)
            self.assertIsNotNone(png_path)
            if csv_path is None or png_path is None:
                self.fail("Expected thermal exports to resolve through the artifact store")

            self.assertIn("num_sets,1", csv_path.read_text(encoding="utf-8"))
            self.assertGreater(png_path.stat().st_size, 0)
            self.assertIn(artifacts["csv"].artifact_id, store.metadata["staged"])
            self.assertIn(artifacts["png"].artifact_id, store.metadata["staged"])

    def test_export_field_artifacts_rerun_rolls_back_second_registration_failure(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        fields_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1],
            run_id="run_batch_rollback",
        )
        original_register = materialization_module.register_staged_artifact
        failure_marker = "second registration failed after new png bytes"
        original_error = RuntimeError(failure_marker)
        new_png_bytes = b"new-png-before-second-registration"

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProjectArtifactStore(project_path=None, metadata=None)
            seeded = service.export_field_artifacts(
                fields_ref,
                model=model_ref,
                artifact_store=store,
                artifact_key="batch_rollback",
                export_formats=("csv", "png"),
                temporary_root_parent=temp_dir,
            )
            root = store.active_staging_root()
            self.assertIsNotNone(root)
            if root is None:
                self.fail("Expected an unsaved-project staging root")
            root_hint = store.staging_root_hint
            seeded_descriptors = {
                export_format: artifact_ref.to_descriptor()
                for export_format, artifact_ref in seeded.items()
            }
            seeded_relative_paths = [
                store.metadata["staged"][seeded[export_format].artifact_id][
                    "relative_path"
                ]
                for export_format in ("csv", "png")
            ]
            seeded_paths: dict[str, Path] = {}
            for export_format, artifact_ref in seeded.items():
                seeded_path = store.resolve_staged_path(artifact_ref.ref)
                self.assertIsNotNone(seeded_path)
                if seeded_path is None:
                    self.fail("Expected seeded staged export path")
                seeded_paths[export_format] = seeded_path
                self.assertEqual(
                    store.metadata["staged"][artifact_ref.artifact_id][
                        "runtime_artifact"
                    ],
                    seeded_descriptors[export_format],
                )

            unrelated_paths = store.node_artifact_paths(
                artifact_id="unrelated",
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
            unrelated_payload.write_bytes(b"unrelated-payload")
            store.register_staged_entry(
                "unrelated",
                relative_path=unrelated_paths.staged_relative_path,
                extra=unrelated_paths.metadata,
            )
            sentinel = root / "unrelated.txt"
            sentinel.write_text("keep", encoding="utf-8")

            registration_formats: list[str] = []

            def write_new_png(
                _fields_container: Any,
                _mesh: Any,
                output_path: Path,
                *,
                camera_state: Any = None,
            ) -> None:
                del camera_state
                Path(output_path).write_bytes(new_png_bytes)

            def fail_second_registration(**kwargs: Any) -> Any:
                registration_formats.append(str(kwargs["format"]))
                if len(registration_formats) == 2:
                    self.assertNotIn(
                        seeded["png"].artifact_id,
                        store.metadata["staged"],
                    )
                    self.assertEqual(
                        Path(kwargs["payload_path"]).read_bytes(),
                        new_png_bytes,
                    )
                    raise original_error
                return original_register(**kwargs)

            with (
                patch.object(
                    service,
                    "_write_png_export",
                    side_effect=write_new_png,
                ),
                patch.object(
                    materialization_module,
                    "register_staged_artifact",
                    side_effect=fail_second_registration,
                ),
                patch.object(
                    store,
                    "discard_staged_paths",
                    wraps=store.discard_staged_paths,
                ) as discard_paths,
            ):
                with self.assertRaises(RuntimeError) as raised:
                    service.export_field_artifacts(
                        fields_ref,
                        model=model_ref,
                        artifact_store=store,
                        artifact_key="batch_rollback",
                        export_formats=("csv", "png"),
                        temporary_root_parent=temp_dir,
                    )

            self.assertIs(raised.exception, original_error)
            self.assertEqual(raised.exception.args, (failure_marker,))
            self.assertEqual(registration_formats, ["csv", "png"])
            self.assertEqual(discard_paths.call_count, 3)
            self.assertEqual(
                tuple(discard_paths.call_args_list[-1].args[0]),
                tuple(seeded_relative_paths),
            )
            self.assertEqual(set(store.metadata["staged"]), {"unrelated"})
            for artifact_ref in seeded.values():
                self.assertNotIn(
                    artifact_ref.artifact_id,
                    store.metadata["staged"],
                )
            self.assertTrue(all(not path.exists() for path in seeded_paths.values()))
            self.assertEqual(
                unrelated_payload.read_bytes(),
                b"unrelated-payload",
            )
            self.assertEqual(store.active_staging_root(), root)
            self.assertIs(store.staging_root_hint, root_hint)
            self.assertTrue(root.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_export_field_artifacts_rejects_no_id_intermediate_reparse_before_write(
        self,
    ) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        fields_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1],
            run_id="run_batch_prewrite_reparse",
        )
        artifact_key = "prewrite_reparse"
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
                node_title="DPF Export",
                node_type="DPF Export",
                io_dir="out",
                subdirectory=f"dpf/{artifact_key}",
                filename="field.csv",
            )
            relative_parts = PurePosixPath(
                artifact_paths.staged_relative_path
            ).parts
            reparse_directory = root.joinpath(*relative_parts[:-1])
            reparse_directory.mkdir(parents=True)
            expected_target = root.joinpath(*relative_parts)
            outside_sentinel = parent / "outside-sentinel.txt"
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
                    "_write_csv_export",
                ) as write_csv,
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
                service.export_field_artifacts(
                    fields_ref,
                    model=model_ref,
                    artifact_store=store,
                    artifact_key=artifact_key,
                    export_formats=("csv",),
                    temporary_root_parent=parent,
                    node_workspace_id="workspace",
                    node_workspace_name="Workspace",
                    node_id="node",
                    node_title="DPF Export",
                    node_type="DPF Export",
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
            write_csv.assert_not_called()
            resolve_target.assert_not_called()
            register_artifact.assert_not_called()

    def test_export_viewer_transport_bundle_writes_manifest_and_entry_file(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service

        model_ref = service.load_model(STATIC_ANALYSIS_RST)
        fields_ref = service.extract_result_fields(
            model=model_ref,
            result_name="displacement",
            set_ids=[1],
            run_id="run_transport_bundle",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            transport = service.export_viewer_transport_bundle(
                fields_ref,
                model=model_ref,
                bundle_root=Path(temp_dir) / "session_transport",
                workspace_id="ws_bundle",
                session_id="session_bundle",
                transport_revision=2,
            )

            self.assertEqual(transport["kind"], "dpf_transport_bundle")
            self.assertEqual(transport["version"], 1)
            self.assertEqual(transport["schema"], "ea.dpf.viewer_transport_bundle.v1")
            manifest_path = Path(transport["manifest_path"])
            entry_path = Path(transport["entry_path"])
            self.assertTrue(manifest_path.is_file())
            self.assertTrue(entry_path.is_file())
            self.assertTrue(any(path.endswith("dataset/dataset.vtm") for path in transport["files"]))
            self.assertEqual(transport["entry_file"], "dataset/dataset.vtm")

            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest_payload["transport_revision"], 2)
            self.assertEqual(manifest_payload["workspace_id"], "ws_bundle")
            self.assertEqual(manifest_payload["session_id"], "session_bundle")
            self.assertEqual(manifest_payload["entry_file"], "dataset/dataset.vtm")

            manifest_metadata = manifest_payload["metadata"]
            self.assertEqual(len(manifest_metadata["time_values"]), 1)
            self.assertIsInstance(manifest_metadata["time_values"][0], float)
            self.assertEqual(len(manifest_metadata["value_ranges"]), 1)
            self.assertLessEqual(
                manifest_metadata["value_ranges"][0]["min"],
                manifest_metadata["value_ranges"][0]["max"],
            )


if __name__ == "__main__":
    unittest.main()
