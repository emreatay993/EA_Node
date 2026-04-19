from __future__ import annotations

import json
import unittest

try:
    import ansys.dpf.core as _dpf_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    _dpf_core = None

from ea_node_editor.addons.ansys_dpf.operator_catalog import (
    load_ansys_dpf_operator_plugin_descriptors,
)
from ea_node_editor.help.dpf_operator_docs import (
    docs_root,
    is_dpf_operator_type_id,
    markdown_for_type_id,
    markdown_path_for_type_id,
)
from ea_node_editor.nodes.node_specs import DpfOperatorSourceSpec
from ea_node_editor.nodes.registry import NodeRegistry

_GENERATED_OPERATOR_PREFIX = "dpf.op."


class _RegistryLookup:
    """Thin wrapper to build a NodeRegistry once per test run."""

    _registry: NodeRegistry | None = None

    @classmethod
    def registry(cls) -> NodeRegistry:
        if cls._registry is None:
            registry = NodeRegistry()
            for descriptor in load_ansys_dpf_operator_plugin_descriptors():
                registry.register_descriptor(descriptor)
            cls._registry = registry
        return cls._registry


class DpfOperatorHelpTypeIdCheckTests(unittest.TestCase):
    def test_accepts_dpf_operator_prefix(self) -> None:
        self.assertTrue(is_dpf_operator_type_id("dpf.op.result.displacement"))

    def test_rejects_empty_and_non_operator_ids(self) -> None:
        self.assertFalse(is_dpf_operator_type_id(""))
        self.assertFalse(is_dpf_operator_type_id(None))  # type: ignore[arg-type]
        self.assertFalse(is_dpf_operator_type_id("core.subnode"))
        self.assertFalse(is_dpf_operator_type_id("dpf.helper.model.model"))


@unittest.skipIf(_dpf_core is None, "ansys.dpf.core is not installed")
class DpfOperatorHelpLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _RegistryLookup.registry()
        self.operator_type_ids = [
            spec.type_id
            for spec in self.registry.all_specs()
            if spec.type_id.startswith(_GENERATED_OPERATOR_PREFIX)
        ]
        self.assertGreater(len(self.operator_type_ids), 0)

    def test_every_registered_operator_has_reachable_docs(self) -> None:
        index_path = docs_root() / "doc_index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        missing: list[str] = []
        documented: list[str] = []
        for type_id in self.operator_type_ids:
            spec = self.registry.get_spec(type_id)
            source = spec.source_metadata
            if not isinstance(source, DpfOperatorSourceSpec) or not source.variants:
                continue
            operator_name = str(source.variants[0].operator_name or "").strip()
            if not operator_name or operator_name not in index:
                continue
            documented.append(type_id)
            path = markdown_path_for_type_id(type_id, self.registry)
            if path is None or not path.is_file():
                missing.append(type_id)
        self.assertGreater(len(documented), 0)
        self.assertEqual(missing, [])

    def test_markdown_for_type_id_returns_heading(self) -> None:
        sample_type_id = self.operator_type_ids[0]
        markdown = markdown_for_type_id(sample_type_id, self.registry)
        self.assertIsNotNone(markdown)
        assert markdown is not None
        self.assertIn("# ", markdown)

    def test_merge_fields_container_resolves(self) -> None:
        target_type_id = "dpf.op.utility.merge_fields_containers"
        if self.registry.spec_or_none(target_type_id) is None:
            self.skipTest(f"{target_type_id} not registered in this DPF build")
        markdown = markdown_for_type_id(target_type_id, self.registry)
        self.assertIsNotNone(markdown)
        assert markdown is not None
        self.assertIn("# ", markdown)

    def test_returned_markdown_is_stripped_of_qt_unfriendly_html(self) -> None:
        target_type_id = "dpf.op.logic.ascending_sort_fc"
        if self.registry.spec_or_none(target_type_id) is None:
            self.skipTest(f"{target_type_id} not registered in this DPF build")
        markdown = markdown_for_type_id(target_type_id, self.registry)
        self.assertIsNotNone(markdown)
        assert markdown is not None
        for needle in ("<strong>", "<details>", "<summary>", "<span"):
            self.assertNotIn(needle, markdown)

    def test_unknown_type_id_returns_none(self) -> None:
        self.assertIsNone(
            markdown_for_type_id("dpf.op.does_not.exist", self.registry),
        )
        self.assertIsNone(markdown_path_for_type_id("dpf.op.does_not.exist", self.registry))

    def test_non_operator_type_id_returns_none(self) -> None:
        self.assertIsNone(markdown_for_type_id("core.subnode", self.registry))
        self.assertIsNone(markdown_path_for_type_id("core.subnode", self.registry))


if __name__ == "__main__":
    unittest.main()
