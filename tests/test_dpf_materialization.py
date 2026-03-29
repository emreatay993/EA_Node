from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

pytest.importorskip("ansys.dpf.core")
pytest.importorskip("pyvista")

from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST, THERMAL_ANALYSIS_RTH
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_VIEWER_DATASET_HANDLE_KIND,
)
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore


class DpfMaterializationTests(unittest.TestCase):
    def test_materialize_viewer_dataset_honors_output_profiles_and_stages_portable_exports(self) -> None:
        services = WorkerServices()
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
                project_path=Path(temp_dir) / "viewer_demo.sfe",
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
            self.assertEqual(set(both_result.artifacts), {"csv", "png", "vtu", "vtm"})
            self.assertEqual(both_result.summary["field_count"], 2)
            self.assertEqual(both_result.summary["set_ids"], [1, 2])

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

            csv_entry = store.metadata["staged"][both_result.artifacts["csv"].artifact_id]
            self.assertTrue(csv_entry["relative_path"].startswith(".staging/artifacts/dpf/static_displacement"))

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
        services = WorkerServices()
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
                project_path=Path(temp_dir) / "thermal_demo.sfe",
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

    def test_export_viewer_transport_bundle_writes_manifest_and_entry_file(self) -> None:
        services = WorkerServices()
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


if __name__ == "__main__":
    unittest.main()
