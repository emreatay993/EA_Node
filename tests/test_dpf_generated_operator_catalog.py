from __future__ import annotations

import importlib
import pkgutil
import re
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    import ansys.dpf.core.operators as dpf_operators
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    dpf_operators = None

from ea_node_editor.addons.ansys_dpf.operator_catalog import (
    load_ansys_dpf_operator_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf import operator_catalog
from tests.typed_handle_support import dpf_worker_services
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
)
from ea_node_editor.nodes.core_data_types import DOUBLE_DATA_TYPE_ID
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_OPERATOR_FAMILY_ORDER,
    operator_family_category_path,
)
from ea_node_editor.runtime_contracts import DataTree, RuntimeHandleRef

_SKIPPED_OPERATOR_PACKAGES = frozenset({"specification", "translator"})
_GENERATED_OPERATOR_PREFIX = "dpf.op."
_FAMILY_ORDER_INDEX = {family: index for index, family in enumerate(DPF_OPERATOR_FAMILY_ORDER)}
_TYPE_TOKEN_SANITIZE_RE = re.compile(r"[^0-9a-zA-Z_]+")


def _generated_operator_category_path(family: str) -> tuple[str, ...]:
    return operator_family_category_path(family)


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
    def test_catalog_payload_decodes_settings_groups(self) -> None:
        spec = operator_catalog._spec_from_payload(
            {
                "type_id": "dpf.op.tests.settings_groups",
                "display_name": "Settings Groups",
                "category_path": ["Ansys DPF", "Tests"],
                "ports": [
                    {
                        "key": "value",
                        "direction": "in",
                        "kind": "data",
                        "data_type": "float",
                        "required": False,
                    }
                ],
                "properties": [
                    {
                        "key": "value",
                        "type": "float",
                        "default": 0.0,
                        "label": "Value",
                        "inline_editor": "number",
                    }
                ],
                "settings_groups": [
                    {
                        "group_id": "general",
                        "label": "General Options",
                        "items": [{"port_key": "value", "property_key": "value"}],
                    }
                ],
                "source_metadata": {
                    "variants": [{"key": "default", "operator_name": "settings_groups"}],
                    "source_path": "ansys.dpf.core.operators.tests.settings_groups",
                    "family_path": ["tests"],
                },
            }
        )

        self.assertEqual(spec.settings_groups[0].group_id, "general")
        self.assertEqual(spec.settings_groups[0].items[0].port_key, "value")
        self.assertEqual(spec.settings_groups[0].items[0].property_key, "value")

    def test_catalog_payload_rejects_missing_or_misaligned_required_metadata(self) -> None:
        base_payload = {
            "type_id": "dpf.op.tests.required",
            "display_name": "Required",
            "category_path": ["Ansys DPF", "Tests"],
            "properties": [],
            "source_metadata": {
                "variants": [{"key": "default", "operator_name": "required"}],
            },
        }
        missing_required = {
            **base_payload,
            "ports": [
                {
                    "key": "value",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "float",
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "declare required explicitly"):
            operator_catalog._spec_from_payload(missing_required)

        misaligned = {
            **base_payload,
            "ports": [
                {
                    "key": "value",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "float",
                    "required": False,
                    "source_metadata": {
                        "pin_name": "value",
                        "pin_direction": "input",
                        "value_origin": "port",
                        "value_key": "value",
                        "data_type": "float",
                        "presence": "required",
                        "omission_semantics": "disallowed",
                    },
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "does not align"):
            operator_catalog._spec_from_payload(misaligned)

    def test_generated_union_output_classifies_each_live_item_before_wrapping(self) -> None:
        class Field:
            location = "Nodal"
            component_count = 1
            scoping = SimpleNamespace(size=2)
            unit = "m"

        class FieldsContainer:
            labels = ("time",)

            def __init__(self, field: object) -> None:
                self._fields = [field]

            def __len__(self) -> int:
                return len(self._fields)

            def __getitem__(self, index: int) -> object:
                return self._fields[index]

            def get_label_space(self, index: int) -> dict[str, int]:
                self._fields[index]
                return {"time": 2}

        services = dpf_worker_services()
        ctx = ExecutionContext(
            run_id="run_union_output",
            node_id="node_union_output",
            workspace_id="ws_union_output",
            inputs={},
            properties={},
            emit_log=lambda *_args: None,
            worker_services=services,
        )
        service = services.dpf_runtime_service
        field = Field()
        fields = FieldsContainer(field)
        port = operator_catalog.PortSpec(
            "values",
            "out",
            "data",
            DPF_FIELD_DATA_TYPE,
            accepted_data_types=(DPF_FIELDS_CONTAINER_DATA_TYPE, DPF_FIELD_DATA_TYPE),
            data_access="list",
        )

        wrapped = operator_catalog._wrap_generated_dpf_output(
            ctx,
            service=service,
            port=port,
            value=[field, fields],
        )

        self.assertEqual(
            [item.data_type_id for item in wrapped],
            [DPF_FIELD_DATA_TYPE, DPF_FIELDS_CONTAINER_DATA_TYPE],
        )
        self.assertEqual(
            [item.kind for item in wrapped],
            ["dpf.field", "dpf.fields_container"],
        )
        self.assertIs(
            services.resolve_handle(
                wrapped[0],
                expected_data_type=DPF_FIELD_DATA_TYPE,
                expected_kind="dpf.field",
            ),
            field,
        )
        self.assertIs(
            services.resolve_handle(
                wrapped[1],
                expected_data_type=DPF_FIELDS_CONTAINER_DATA_TYPE,
                expected_kind="dpf.fields_container",
            ),
            fields,
        )

    def test_generated_union_output_fails_unsupported_and_ambiguous_values(self) -> None:
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        port = operator_catalog.PortSpec(
            "value",
            "out",
            "data",
            DPF_FIELD_DATA_TYPE,
            accepted_data_types=(DPF_FIELDS_CONTAINER_DATA_TYPE,),
        )
        with self.assertRaisesRegex(TypeError, "unsupported"):
            operator_catalog._classify_generated_dpf_output(
                service,
                port=port,
                value=object(),
            )

        catalog = mock.Mock()
        catalog.require.return_value = SimpleNamespace(abstract=False)
        catalog.validate_output.return_value = None
        ambiguous_service = SimpleNamespace(
            _worker_services=SimpleNamespace(data_types=catalog)
        )
        ambiguous_port = operator_catalog.PortSpec(
            "value",
            "out",
            "data",
            "tests.First",
            accepted_data_types=("tests.Second",),
        )
        with self.assertRaisesRegex(TypeError, "ambiguous"):
            operator_catalog._classify_generated_dpf_output(
                ambiguous_service,
                port=ambiguous_port,
                value=object(),
            )

    def test_generated_single_candidate_output_requires_live_value_proof(self) -> None:
        class Field:
            location = "Nodal"
            component_count = 1
            scoping = SimpleNamespace(size=1)
            unit = "m"

        services = dpf_worker_services()
        ctx = ExecutionContext(
            run_id="run_single_output",
            node_id="node_single_output",
            workspace_id="ws_single_output",
            inputs={},
            properties={},
            emit_log=lambda *_args: None,
            worker_services=services,
        )
        port = operator_catalog.PortSpec(
            "field",
            "out",
            "data",
            DPF_FIELD_DATA_TYPE,
        )
        with self.assertRaisesRegex(TypeError, "unsupported"):
            operator_catalog._wrap_generated_dpf_output(
                ctx,
                service=services.dpf_runtime_service,
                port=port,
                value=object(),
            )

        field = Field()
        wrapped = operator_catalog._wrap_generated_dpf_output(
            ctx,
            service=services.dpf_runtime_service,
            port=port,
            value=field,
        )

        self.assertEqual(wrapped.data_type_id, DPF_FIELD_DATA_TYPE)
        self.assertEqual(wrapped.kind, "dpf.field")
        self.assertIs(
            services.resolve_handle(
                wrapped,
                expected_data_type=DPF_FIELD_DATA_TYPE,
                expected_kind="dpf.field",
            ),
            field,
        )

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
        self.assertIn(
            DPF_SCOPING_DATA_TYPE,
            displacement_ports["time_scoping"].accepted_data_types,
        )
        self.assertEqual(displacement_properties["bool_rotate_to_global"].type, "bool")
        self.assertEqual(displacement_properties["read_cyclic"].type, "int")
        self.assertTrue(displacement_properties["phi"].expose_port_toggle)

        add = descriptors["dpf.op.math.add"]
        add_ports = {port.key: port for port in add.ports}
        self.assertEqual(add.category_path, _generated_operator_category_path("math"))
        self.assertTrue(add_ports["fielda"].required)
        self.assertTrue(add_ports["fielda"].exposed)
        self.assertIn(
            DPF_FIELDS_CONTAINER_DATA_TYPE,
            add_ports["fielda"].accepted_data_types,
        )
        self.assertIn(DOUBLE_DATA_TYPE_ID, add_ports["fielda"].accepted_data_types)
        self.assertEqual(add_ports["field"].source_metadata.pin_name, "field")

        concatenate_fields = descriptors["dpf.op.utility.concatenate_fields"]
        fields_port = next(port for port in concatenate_fields.ports if port.key == "fields")
        self.assertEqual(fields_port.data_access, "list")
        self.assertFalse(fields_port.allow_multiple_connections)

        split_data_sources = descriptors["dpf.op.logic.split_data_sources"]
        outputs_port = next(port for port in split_data_sources.ports if port.key == "outputs")
        self.assertEqual(outputs_port.direction, "out")
        self.assertEqual(outputs_port.data_access, "list")
        self.assertFalse(outputs_port.allow_multiple_connections)

        for type_id in operator_catalog._SINGLE_RUN_OPERATOR_TYPE_IDS:
            effect_inputs = [
                port for port in descriptors[type_id].ports if port.direction == "in"
            ]
            self.assertTrue(effect_inputs, type_id)
            self.assertTrue(
                all(port.data_access == "tree" for port in effect_inputs),
                type_id,
            )

        self.assertTrue(
            all(
                port.kind == "data"
                for descriptor in descriptors.values()
                for port in descriptor.ports
            )
        )

    @unittest.skipIf(dpf_operators is None, "ansys.dpf.core is not installed")
    def test_generated_operator_execute_wraps_dpf_outputs_as_runtime_handles(self) -> None:
        class Field:
            def __init__(self) -> None:
                self.location = "Nodal"
                self.component_count = 3
                self.scoping = SimpleNamespace(size=2)
                self.unit = "m"

        class FieldsContainer:
            def __init__(self, field: object) -> None:
                self._fields = [field]
                self.labels = ("time",)

            def __len__(self) -> int:
                return len(self._fields)

            def __getitem__(self, index: int) -> object:
                return self._fields[index]

            def get_label_space(self, index: int) -> dict[str, int]:
                self._fields[index]
                return {"time": 2}

        descriptors = {
            descriptor.spec.type_id: descriptor
            for descriptor in load_ansys_dpf_operator_plugin_descriptors()
        }
        plugin = descriptors["dpf.op.result.displacement"].factory()
        services = dpf_worker_services()
        service = services.dpf_runtime_service
        fake_field = Field()
        fake_fields = FieldsContainer(fake_field)
        ctx = ExecutionContext(
            run_id="run_generated_wrap",
            node_id="node_generated_wrap",
            workspace_id="ws_generated_wrap",
            inputs={},
            properties={},
            emit_log=lambda *_args: None,
            worker_services=services,
        )

        with mock.patch.object(
            service,
            "invoke_operator",
            return_value=SimpleNamespace(outputs={"fields_container_2": fake_fields}),
        ):
            result = plugin.execute(ctx)

        wrapped = result.outputs["fields_container_2"]
        self.assertIsInstance(wrapped, RuntimeHandleRef)
        if not isinstance(wrapped, RuntimeHandleRef):
            return
        self.assertEqual(wrapped.kind, "dpf.fields_container")
        self.assertEqual(wrapped.metadata["field_count"], 1)
        self.assertEqual(wrapped.metadata["set_ids"], [2])
        self.assertIs(services.resolve_handle(wrapped, expected_kind="dpf.fields_container"), fake_fields)
        self.assertNotIn("exec_out", result.outputs)

    @unittest.skipIf(dpf_operators is None, "ansys.dpf.core is not installed")
    def test_generated_file_writer_unwraps_tree_inputs_once_and_rejects_ambiguous_scalars(self) -> None:
        descriptor = {
            item.spec.type_id: item
            for item in load_ansys_dpf_operator_plugin_descriptors()
        }["dpf.op.serialization.serializer"]
        service = dpf_worker_services().dpf_runtime_service
        ctx = ExecutionContext(
            run_id="run_generated_write",
            node_id="node_generated_write",
            workspace_id="ws_generated_write",
            inputs={
                "stream_type": DataTree.from_item(7),
                "file_path": DataTree.from_item("output.bin"),
                "any_input": DataTree({(0,): ("first",), (1,): ("second",)}),
            },
            properties={},
            emit_log=lambda *_args: None,
            worker_services=SimpleNamespace(dpf_runtime_service=service),
        )

        with mock.patch.object(
            service,
            "invoke_operator",
            return_value=SimpleNamespace(outputs={}),
        ) as invoke:
            descriptor.factory().execute(ctx)

        invoke.assert_called_once()
        self.assertEqual(
            invoke.call_args.kwargs["inputs"],
            {"stream_type": 7, "file_path": "output.bin", "any_input": ["first", "second"]},
        )

        ctx.inputs["stream_type"] = DataTree.from_list([7, 8])
        with mock.patch.object(service, "invoke_operator") as invoke:
            with self.assertRaisesRegex(ValueError, "requires exactly one item"):
                descriptor.factory().execute(ctx)
        invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
