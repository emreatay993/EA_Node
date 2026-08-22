from __future__ import annotations

import json
import tempfile
import unittest
import warnings
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from unittest import mock

from ea_node_editor.addons.ansys_dpf import catalog as dpf_catalog
from ea_node_editor.addons.ansys_dpf import operator_catalog
from ea_node_editor.addons.ansys_dpf.curated_catalog import load_ansys_dpf_curated_plugin_descriptors
from ea_node_editor.addons.ansys_dpf.helper_catalog import load_ansys_dpf_helper_plugin_descriptors
from ea_node_editor.addons.ansys_dpf.plot_catalog import load_ansys_dpf_plot_plugin_descriptors


class DpfOperatorCatalogAssetTests(unittest.TestCase):
    def setUp(self) -> None:
        dpf_catalog.invalidate_ansys_dpf_descriptor_cache()
        operator_catalog.load_ansys_dpf_operator_plugin_descriptors.cache_clear()
        operator_catalog._generated_operator_plugin_descriptors.cache_clear()
        operator_catalog._discovered_generated_operator_definitions.cache_clear()
        operator_catalog._CATALOG_FALLBACK_WARNED = False

    def tearDown(self) -> None:
        dpf_catalog.invalidate_ansys_dpf_descriptor_cache()
        operator_catalog.load_ansys_dpf_operator_plugin_descriptors.cache_clear()
        operator_catalog._CATALOG_FALLBACK_WARNED = False

    def test_committed_catalog_matches_live_discovery_and_complete_contract(self) -> None:
        document = json.loads(operator_catalog.OPERATOR_CATALOG_PATH.read_text(encoding="utf-8"))

        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(document["ansys_dpf_core_version"], version("ansys-dpf-core"))
        self.assertEqual(
            operator_catalog.OPERATOR_CATALOG_PATH.read_text(encoding="utf-8"),
            operator_catalog.render_ansys_dpf_operator_catalog(),
        )

        raw_descriptors = document["descriptors"]
        self.assertGreater(len(raw_descriptors), 700)
        sample = raw_descriptors[0]
        self.assertTrue(
            {
                "type_id",
                "display_name",
                "description",
                "category",
                "category_path",
                "ports",
                "properties",
                "source_metadata",
            }.issubset(sample)
        )
        self.assertTrue(
            {"family_path", "source_path", "stability", "variants"}.issubset(sample["source_metadata"])
        )
        raw_ports = [port for descriptor in raw_descriptors for port in descriptor["ports"]]
        self.assertTrue(all(port["kind"] == "data" for port in raw_ports))
        self.assertTrue(
            all(port["data_access"] in {"item", "list", "tree"} for port in raw_ports)
        )
        self.assertTrue(any(port["data_access"] == "list" for port in raw_ports))
        descriptors_by_id = {
            descriptor["type_id"]: descriptor for descriptor in raw_descriptors
        }
        for type_id in operator_catalog._SINGLE_RUN_OPERATOR_TYPE_IDS:
            effect_inputs = [
                port
                for port in descriptors_by_id[type_id]["ports"]
                if port["direction"] == "in"
            ]
            self.assertTrue(effect_inputs, type_id)
            self.assertTrue(
                all(port["data_access"] == "tree" for port in effect_inputs),
                type_id,
            )
        self.assertFalse(any(port["allow_multiple_connections"] for port in raw_ports))

        catalog_specs = tuple(
            descriptor.spec
            for descriptor in operator_catalog._descriptors_from_catalog_document(document)
        )
        live_specs = tuple(
            descriptor.spec
            for descriptor in operator_catalog._generated_operator_plugin_descriptors()
        )
        self.assertEqual(tuple(asdict(spec) for spec in catalog_specs), tuple(asdict(spec) for spec in live_specs))

    def test_exact_version_load_does_not_run_live_discovery(self) -> None:
        with mock.patch.object(
            operator_catalog,
            "_generated_operator_plugin_descriptors",
            side_effect=AssertionError("live discovery must not run"),
        ):
            descriptors = operator_catalog.load_ansys_dpf_operator_plugin_descriptors()

        self.assertGreater(len(descriptors), 700)
        self.assertEqual(descriptors[0].spec.type_id, "dpf.result_field")
        self.assertEqual(descriptors[1].spec.type_id, "dpf.field_ops")

    def test_version_mismatch_warns_once_and_discovers_live_in_memory(self) -> None:
        document = json.loads(operator_catalog.OPERATOR_CATALOG_PATH.read_text(encoding="utf-8"))
        document["ansys_dpf_core_version"] = "0.16.0"
        with tempfile.TemporaryDirectory() as temp_dir:
            catalog_path = Path(temp_dir) / "operator_catalog.json"
            catalog_path.write_text(json.dumps(document), encoding="utf-8")
            with (
                mock.patch.object(operator_catalog, "OPERATOR_CATALOG_PATH", catalog_path),
                mock.patch.object(operator_catalog, "_generated_operator_plugin_descriptors", return_value=()) as live,
                warnings.catch_warnings(record=True) as caught,
            ):
                warnings.simplefilter("always")
                first = operator_catalog.load_ansys_dpf_operator_plugin_descriptors()
                second = operator_catalog.load_ansys_dpf_operator_plugin_descriptors()

        self.assertEqual(len(first), 2)
        self.assertIs(first, second)
        live.assert_called_once_with()
        self.assertEqual(len(caught), 1)
        self.assertIn("does not match runtime", str(caught[0].message))

    def test_corrupt_or_unsupported_catalog_warns_and_requests_live_discovery(self) -> None:
        cases = (
            "not-json",
            json.dumps(
                {
                    "schema_version": 99,
                    "ansys_dpf_core_version": version("ansys-dpf-core"),
                    "descriptors": [],
                }
            ),
            json.dumps(
                {
                    "schema_version": 1,
                    "ansys_dpf_core_version": version("ansys-dpf-core"),
                    "descriptors": [{}],
                }
            ),
        )
        for content in cases:
            with self.subTest(content=content[:20]), tempfile.TemporaryDirectory() as temp_dir:
                catalog_path = Path(temp_dir) / "operator_catalog.json"
                catalog_path.write_text(content, encoding="utf-8")
                operator_catalog._CATALOG_FALLBACK_WARNED = False
                with (
                    mock.patch.object(operator_catalog, "OPERATOR_CATALOG_PATH", catalog_path),
                    warnings.catch_warnings(record=True) as caught,
                ):
                    warnings.simplefilter("always")
                    descriptors = operator_catalog._packaged_generated_operator_descriptors(
                        version("ansys-dpf-core")
                    )
                self.assertIsNone(descriptors)
                self.assertEqual(len(caught), 1)

    def test_live_discovery_failure_keeps_foundational_descriptors(self) -> None:
        with (
            mock.patch.object(operator_catalog, "_packaged_generated_operator_descriptors", return_value=None),
            mock.patch.object(
                operator_catalog,
                "_generated_operator_plugin_descriptors",
                side_effect=RuntimeError("discovery failed"),
            ),
            warnings.catch_warnings(record=True) as caught,
        ):
            warnings.simplefilter("always")
            descriptors = operator_catalog.load_ansys_dpf_operator_plugin_descriptors()

        self.assertEqual(tuple(descriptor.spec.type_id for descriptor in descriptors), ("dpf.result_field", "dpf.field_ops"))
        self.assertEqual(len(caught), 1)
        self.assertIn("live discovery failed", str(caught[0].message))

    def test_live_discovery_failure_keeps_non_generated_dpf_families(self) -> None:
        expected_type_ids = {
            descriptor.spec.type_id
            for descriptor in (
                load_ansys_dpf_helper_plugin_descriptors()
                + load_ansys_dpf_curated_plugin_descriptors()
                + load_ansys_dpf_plot_plugin_descriptors()
            )
        } | {"dpf.result_field", "dpf.field_ops"}
        with (
            mock.patch.object(operator_catalog, "_packaged_generated_operator_descriptors", return_value=None),
            mock.patch.object(
                operator_catalog,
                "_generated_operator_plugin_descriptors",
                side_effect=RuntimeError("discovery failed"),
            ),
            warnings.catch_warnings(record=True),
        ):
            descriptors = dpf_catalog.load_ansys_dpf_plugin_descriptors()

        actual_type_ids = {descriptor.spec.type_id for descriptor in descriptors}
        self.assertTrue(expected_type_ids.issubset(actual_type_ids))
        self.assertFalse(any(type_id.startswith("dpf.op.") for type_id in actual_type_ids))

    def test_plugin_version_uses_distribution_metadata(self) -> None:
        with (
            mock.patch.object(dpf_catalog, "_find_spec", return_value=object()),
            mock.patch.object(dpf_catalog, "version", return_value="0.16.1") as metadata_version,
        ):
            self.assertEqual(dpf_catalog.resolve_ansys_dpf_plugin_version(), "0.16.1")
        metadata_version.assert_called_once_with("ansys-dpf-core")


if __name__ == "__main__":
    unittest.main()
