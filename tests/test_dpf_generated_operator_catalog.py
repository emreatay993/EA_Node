from __future__ import annotations

import importlib
import pkgutil
import re
import unittest

try:
    import ansys.dpf.core.operators as dpf_operators
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    dpf_operators = None

from ea_node_editor.nodes.builtins.ansys_dpf_operator_catalog import (
    load_ansys_dpf_operator_plugin_descriptors,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_OPERATOR_FAMILY_ORDER,
    dpf_category_path,
    operator_family_display_name,
)

_SKIPPED_OPERATOR_PACKAGES = frozenset({"specification", "translator"})
_GENERATED_OPERATOR_PREFIX = "dpf.op."
_FAMILY_ORDER_INDEX = {family: index for index, family in enumerate(DPF_OPERATOR_FAMILY_ORDER)}
_TYPE_TOKEN_SANITIZE_RE = re.compile(r"[^0-9a-zA-Z_]+")


def _generated_operator_category_path(family: str) -> tuple[str, ...]:
    return dpf_category_path("Operators", operator_family_display_name(family))


def _generated_operator_type_id(family: str, module_name: str) -> str:
    normalized_family = _TYPE_TOKEN_SANITIZE_RE.sub("_", str(family).strip().lower())
    normalized_module_name = _TYPE_TOKEN_SANITIZE_RE.sub("_", str(module_name).strip().lower())
    normalized_family = re.sub(r"_+", "_", normalized_family).strip("_")
    normalized_module_name = re.sub(r"_+", "_", normalized_module_name).strip("_")
    return f"{_GENERATED_OPERATOR_PREFIX}{normalized_family}.{normalized_module_name}"


def _discover_public_operator_modules() -> dict[tuple[str, str], dict[str, str]]:
    if dpf_operators is None:
        return {}

    discovered: dict[tuple[str, str], dict[str, str]] = {}
    for family_info in pkgutil.iter_modules(dpf_operators.__path__):
        if not family_info.ispkg or family_info.name in _SKIPPED_OPERATOR_PACKAGES:
            continue
        family = family_info.name
        package = importlib.import_module(f"ansys.dpf.core.operators.{family}")
        for module_info in pkgutil.iter_modules(package.__path__):
            if module_info.ispkg or module_info.name.startswith("_"):
                continue
            module_name = module_info.name
            module_path = f"ansys.dpf.core.operators.{family}.{module_name}"
            module = importlib.import_module(module_path)
            operator_class = getattr(module, module_name, None)
            if operator_class is None:
                continue
            try:
                operator = operator_class()
            except Exception:
                continue
            specification = operator.specification
            properties = getattr(specification, "properties", {}) or {}
            exposure = str(properties.get("exposure", "") or "").strip().casefold()
            category = str(properties.get("category", "") or "").strip().casefold()
            outputs = getattr(specification, "outputs", {}) or {}
            operator_name = str(getattr(operator, "name", "") or "").strip()
            if exposure != "public" or not category or not outputs or not operator_name:
                continue
            discovered[(category, module_name)] = {
                "operator_name": operator_name,
                "source_path": module_path,
            }
    return discovered


class DpfGeneratedOperatorCatalogTests(unittest.TestCase):
    @unittest.skipIf(dpf_operators is None, "ansys.dpf.core is not installed")
    def test_generated_operator_catalog_covers_public_operator_modules(self) -> None:
        descriptors = [
            descriptor
            for descriptor in load_ansys_dpf_operator_plugin_descriptors()
            if descriptor.spec.type_id.startswith(_GENERATED_OPERATOR_PREFIX)
        ]
        expected = _discover_public_operator_modules()

        actual_ids = {descriptor.spec.type_id for descriptor in descriptors}
        expected_ids = {
            _generated_operator_type_id(family, module_name)
            for family, module_name in expected
        }

        self.assertEqual(actual_ids, expected_ids)
        self.assertEqual(
            {descriptor.spec.category_path for descriptor in descriptors},
            {_generated_operator_category_path(family) for family, _ in expected},
        )

    @unittest.skipIf(dpf_operators is None, "ansys.dpf.core is not installed")
    def test_generated_operator_catalog_order_is_family_then_module(self) -> None:
        descriptors = [
            descriptor.spec.type_id
            for descriptor in load_ansys_dpf_operator_plugin_descriptors()
            if descriptor.spec.type_id.startswith(_GENERATED_OPERATOR_PREFIX)
        ]
        expected = sorted(
            _discover_public_operator_modules(),
            key=lambda item: (
                _FAMILY_ORDER_INDEX.get(item[0], len(_FAMILY_ORDER_INDEX)),
                item[0],
                item[1],
            ),
        )
        expected_ids = [_generated_operator_type_id(family, module_name) for family, module_name in expected]

        self.assertEqual(descriptors, expected_ids)

    @unittest.skipIf(dpf_operators is None, "ansys.dpf.core is not installed")
    def test_generated_operator_samples_preserve_pin_and_source_contracts(self) -> None:
        descriptors = {
            descriptor.spec.type_id: descriptor.spec
            for descriptor in load_ansys_dpf_operator_plugin_descriptors()
        }

        displacement = descriptors["dpf.op.result.displacement"]
        displacement_ports = {port.key: port for port in displacement.ports}
        displacement_properties = {prop.key: prop for prop in displacement.properties}
        self.assertEqual(displacement.category_path, _generated_operator_category_path("result"))
        self.assertEqual(
            displacement.source_metadata.source_path,
            "ansys.dpf.core.operators.result.displacement",
        )
        self.assertEqual(displacement.source_metadata.variants[0].operator_name, "U")
        self.assertTrue(displacement_ports["data_sources"].required)
        self.assertTrue(displacement_ports["data_sources"].exposed)
        self.assertEqual(displacement_ports["data_sources"].source_metadata.pin_name, "data_sources")
        self.assertFalse(displacement_ports["time_scoping"].exposed)
        self.assertIn("dpf_scoping", displacement_ports["time_scoping"].accepted_data_types)
        self.assertEqual(displacement_properties["bool_rotate_to_global"].type, "bool")
        self.assertEqual(displacement_properties["read_cyclic"].type, "int")
        self.assertTrue(displacement_properties["phi"].expose_port_toggle)

        add = descriptors["dpf.op.math.add"]
        add_ports = {port.key: port for port in add.ports}
        self.assertEqual(add.category_path, _generated_operator_category_path("math"))
        self.assertTrue(add_ports["fielda"].required)
        self.assertTrue(add_ports["fielda"].exposed)
        self.assertIn("dpf_fields_container", add_ports["fielda"].accepted_data_types)
        self.assertIn("float", add_ports["fielda"].accepted_data_types)
        self.assertEqual(add_ports["field"].source_metadata.pin_name, "field")


if __name__ == "__main__":
    unittest.main()
