from __future__ import annotations

import ast
import unittest
from pathlib import Path

from ea_node_editor.graph import transforms
from ea_node_editor.graph.mutation_service import WorkspaceMutationService
from scripts import verification_manifest as manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
_RETIRED_GUARDRAIL_PRESENT_NAMES = {
    (
        "graph_canvas_qml_legacy_view_alias",
        "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml",
    ): {"_legacyCanvasViewBridgeRef"},
    ("old_preference_schema_compatibility", "ea_node_editor/app_preferences.py"): {
        "_APP_PREFERENCES_MIGRATION_VERSION",
    },
    ("legacy_plugin_class_probing", "ea_node_editor/nodes/plugin_loader.py"): {
        "_legacy_plugin_spec",
        "_register_plugin_classes",
    },
    ("runtime_project_doc_trigger_compatibility", "ea_node_editor/execution/runtime_snapshot.py"): {
        "sanitize_execution_trigger",
    },
}


def parse_module(relative_path: str) -> ast.Module:
    return ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"), filename=relative_path)


def qualified_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = qualified_name(node.value)
        if parent is None:
            return node.attr
        return f"{parent}.{node.attr}"
    return None


def imported_names_from(tree: ast.AST, module_name: str) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module_name:
            imported.update(alias.name for alias in node.names)
    return imported


def imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def call_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = qualified_name(node.func)
            if name is not None:
                names.add(name)
    return names


def class_node(tree: ast.Module, class_name: str) -> ast.ClassDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Missing class {class_name!r}.")


def method_node(tree: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef:
    owner = class_node(tree, class_name)
    for node in owner.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    raise AssertionError(f"Missing method {class_name}.{method_name}.")


def class_ann_assign(tree: ast.Module, class_name: str, field_name: str) -> ast.AnnAssign:
    owner = class_node(tree, class_name)
    for node in owner.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == field_name:
            return node
    raise AssertionError(f"Missing annotated field {class_name}.{field_name}.")


def assignment_call(method: ast.FunctionDef, target_name: str) -> ast.Call:
    for node in ast.walk(method):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if qualified_name(target) == target_name and isinstance(node.value, ast.Call):
                    return node.value
    raise AssertionError(f"Missing call assignment for {target_name!r}.")


def has_call_with_keyword(tree: ast.AST, call_name: str, keyword_name: str, keyword_value: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and qualified_name(node.func) == call_name:
            for keyword in node.keywords:
                if keyword.arg == keyword_name and qualified_name(keyword.value) == keyword_value:
                    return True
    return False


def function_args(method: ast.FunctionDef) -> set[str]:
    return {arg.arg for arg in (*method.args.args, *method.args.kwonlyargs)}


def declared_python_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.asname or alias.name.partition(".")[0] for alias in node.names)
    return names


class GraphArchitectureBoundaryTests(unittest.TestCase):
    def test_corex_no_legacy_guardrail_inventory_matches_current_source_anchors(self) -> None:
        for surface in manifest.COREX_NO_LEGACY_GUARDRAIL_INVENTORY:
            source_path = REPO_ROOT / surface.path
            with self.subTest(category=surface.category, path=surface.path):
                if (
                    surface.expectation == manifest.COREX_NO_LEGACY_GUARDRAIL_ABSENT
                    and not source_path.exists()
                ):
                    continue
                self.assertTrue(source_path.is_file())
                if source_path.suffix == ".py":
                    text_names = declared_python_names(parse_module(surface.path))
                    source_text = ""
                else:
                    text_names = set()
                    source_text = source_path.read_text(encoding="utf-8")

                if surface.expectation == manifest.COREX_NO_LEGACY_GUARDRAIL_PRESENT:
                    expected_names = set(surface.names) - _RETIRED_GUARDRAIL_PRESENT_NAMES.get(
                        (surface.category, surface.path),
                        set(),
                    )
                    if source_path.suffix == ".py":
                        self.assertTrue(expected_names <= text_names)
                    else:
                        for name in expected_names:
                            self.assertIn(name, source_text)
                elif surface.expectation == manifest.COREX_NO_LEGACY_GUARDRAIL_ABSENT:
                    source_text = source_path.read_text(encoding="utf-8")
                    for name in surface.names:
                        self.assertNotIn(name, source_text)
                else:
                    self.fail(f"Unknown no-legacy guardrail expectation: {surface.expectation!r}")

    def test_graph_mutation_service_uses_graph_owned_boundary_adapters(self) -> None:
        tree = parse_module("ea_node_editor/graph/mutation_service.py")
        imports = imported_modules(tree)

        self.assertNotIn("ea_node_editor.ui.pdf_preview_provider", imports)
        self.assertNotIn("ea_node_editor.ui_qml.edge_routing", imports)
        self.assertNotIn("ea_node_editor.graph.transforms", imports)
        self.assertTrue(
            {"GraphBoundaryAdapters", "fallback_graph_boundary_adapters"}
            <= imported_names_from(tree, "ea_node_editor.graph.boundary_adapters")
        )
        self.assertIn("WorkspaceMutationServiceFactory", {node.name for node in tree.body if isinstance(node, ast.ClassDef)})
        self.assertIn("create_workspace_mutation_service", {node.name for node in tree.body if isinstance(node, ast.FunctionDef)})

        boundary_field = class_ann_assign(tree, "WorkspaceMutationService", "boundary_adapters")
        self.assertIsInstance(boundary_field.value, ast.Call)
        self.assertEqual("field", qualified_name(boundary_field.value.func))
        default_factory = next(
            keyword.value
            for keyword in boundary_field.value.keywords
            if keyword.arg == "default_factory"
        )
        self.assertEqual("fallback_graph_boundary_adapters", qualified_name(default_factory))
        self.assertIn("self.boundary_adapters.node_size", call_names(tree))
        self.assertIn("self.boundary_adapters.clamp_pdf_page_number", call_names(tree))

    def test_scene_bridge_injects_ui_boundary_implementations_without_global_installation(self) -> None:
        tree = parse_module("ea_node_editor/ui_qml/graph_scene_bridge.py")
        imports = imported_modules(tree)

        self.assertIn("build_graph_boundary_adapters", imported_names_from(tree, "ea_node_editor.graph.boundary_adapters"))
        self.assertIn("clamp_pdf_page_number", imported_names_from(tree, "ea_node_editor.ui.pdf_preview_provider"))
        self.assertIn("node_size", imported_names_from(tree, "ea_node_editor.ui_qml.edge_routing"))
        self.assertNotIn("set_graph_boundary_adapters", call_names(tree))

        init_method = method_node(tree, "GraphSceneBridge", "__init__")
        boundary_call = assignment_call(init_method, "self._boundary_adapters")
        self.assertEqual("build_graph_boundary_adapters", qualified_name(boundary_call.func))
        payload_call = assignment_call(init_method, "self._payload_builder")
        self.assertEqual("GraphScenePayloadBuilder", qualified_name(payload_call.func))
        self.assertTrue(
            any(
                keyword.arg == "boundary_adapters" and qualified_name(keyword.value) == "self._boundary_adapters"
                for keyword in payload_call.keywords
            )
        )
        self.assertTrue(
            has_call_with_keyword(
                init_method,
                "GraphSceneMutationHistory",
                "boundary_adapters",
                "self._boundary_adapters",
            )
        )

    def test_graph_model_externalizes_workspace_mutation_service_factory(self) -> None:
        model_tree = parse_module("ea_node_editor/graph/model.py")
        mutation_tree = parse_module("ea_node_editor/graph/mutation_service.py")
        helper_tree = parse_module("ea_node_editor/ui_qml/graph_scene_mutation_history.py")
        composition_tree = parse_module("ea_node_editor/ui/shell/composition.py")

        self.assertNotIn("WorkspaceMutationService", call_names(model_tree))
        self.assertIn(
            "create_workspace_mutation_service",
            imported_names_from(model_tree, "ea_node_editor.graph.mutation_service"),
        )
        self.assertIn("WorkspaceMutationServiceFactory", {node.name for node in mutation_tree.body if isinstance(node, ast.ClassDef)})
        self.assertIn("create_workspace_mutation_service", {node.name for node in mutation_tree.body if isinstance(node, ast.FunctionDef)})

        resolved_factory = method_node(model_tree, "GraphModel", "_resolved_mutation_service_factory")
        self.assertIn(
            "create_workspace_mutation_service",
            imported_names_from(resolved_factory, "ea_node_editor.graph.mutation_service"),
        )
        mutation_service_method = method_node(model_tree, "GraphModel", "mutation_service")
        self.assertIn("mutation_service_factory", function_args(method_node(model_tree, "GraphModel", "__init__")))
        self.assertIn("boundary_adapters", function_args(mutation_service_method))
        self.assertIn("self._resolved_mutation_service_factory", call_names(mutation_service_method))
        self.assertIn("model.mutation_service", call_names(helper_tree))
        self.assertNotIn("WorkspaceMutationService", call_names(helper_tree))
        self.assertTrue(
            has_call_with_keyword(
                composition_tree,
                "GraphModel",
                "mutation_service_factory",
                "create_workspace_mutation_service",
            )
        )

    def test_graph_domain_does_not_expose_persistence_overlay_state(self) -> None:
        model_tree = parse_module("ea_node_editor/graph/model.py")
        normalization_tree = parse_module("ea_node_editor/graph/normalization.py")
        codec_tree = parse_module("ea_node_editor/persistence/project_codec.py")

        self.assertNotIn("ea_node_editor.persistence.overlay", imported_modules(model_tree))
        self.assertNotIn("import_module", call_names(model_tree))
        self.assertNotIn("WorkspacePersistenceState", {node.id for node in ast.walk(model_tree) if isinstance(node, ast.Name)})
        graph_names = {node.id for node in ast.walk(model_tree) if isinstance(node, ast.Name)}
        normalization_names = {node.id for node in ast.walk(normalization_tree) if isinstance(node, ast.Name)}
        codec_names = {node.id for node in ast.walk(codec_tree) if isinstance(node, ast.Name)}

        for name in {
            "capture_persistence_state",
            "restore_persistence_state",
            "unresolved_node_docs",
            "unresolved_edge_docs",
            "authored_node_overrides",
        }:
            self.assertNotIn(name, graph_names)
            self.assertNotIn(name, normalization_names)
        self.assertNotIn("restore_workspace_persistence_state", codec_names)

    def test_graph_file_issue_module_is_a_boundary_adapter_to_persistence(self) -> None:
        tree = parse_module("ea_node_editor/graph/file_issue_state.py")
        imported_names = imported_names_from(tree, "ea_node_editor.persistence.file_issues")
        all_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}

        self.assertTrue(imported_names)
        self.assertNotIn("ProjectArtifactResolver", all_names)
        self.assertNotIn("_TRACKED_REPAIR_MODES", all_names)

    def test_runtime_snapshot_builder_uses_execution_owned_assembly_seam(self) -> None:
        snapshot_tree = parse_module("ea_node_editor/execution/runtime_snapshot.py")
        assembly_tree = parse_module("ea_node_editor/execution/runtime_snapshot_assembly.py")
        worker_runtime_tree = parse_module("ea_node_editor/execution/worker_runtime.py")

        self.assertIn(
            "RuntimeSnapshotAssembly",
            imported_names_from(snapshot_tree, "ea_node_editor.execution.runtime_snapshot_assembly"),
        )
        self.assertNotIn("ea_node_editor.persistence.migration", imported_modules(snapshot_tree))
        self.assertNotIn("ea_node_editor.persistence.overlay", imported_modules(snapshot_tree))
        self.assertNotIn("ea_node_editor.persistence.project_codec", imported_modules(snapshot_tree))
        snapshot_names = {node.id for node in ast.walk(snapshot_tree) if isinstance(node, ast.Name)}
        assembly_names = {node.id for node in ast.walk(assembly_tree) if isinstance(node, ast.Name)}
        self.assertNotIn("normalize_artifact_store_metadata", snapshot_names)
        self.assertIn("RuntimeSnapshotAssembly", {node.name for node in assembly_tree.body if isinstance(node, ast.ClassDef)})
        self.assertNotIn("JsonProjectMigration", assembly_names)
        self.assertNotIn("WorkspacePersistenceEnvelope", assembly_names)
        self.assertNotIn("ProjectPersistenceEnvelope", assembly_names)
        self.assertNotIn("normalize_artifact_store_metadata", assembly_names)
        build_runtime_snapshot = next(
            node
            for node in snapshot_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "build_runtime_snapshot"
        )
        self.assertNotIn("serializer", {arg.arg for arg in build_runtime_snapshot.args.args})
        self.assertNotIn("sanitize_execution_trigger", snapshot_names)
        self.assertNotIn("ea_node_editor.persistence.serializer", imported_modules(worker_runtime_tree))

    def test_runtime_contracts_do_not_import_execution_implementation(self) -> None:
        contract_root = REPO_ROOT / "ea_node_editor" / "runtime_contracts"

        for source_path in contract_root.glob("*.py"):
            relative_path = source_path.relative_to(REPO_ROOT).as_posix()
            imports = imported_modules(parse_module(relative_path))
            with self.subTest(path=relative_path):
                self.assertFalse(
                    {
                        module
                        for module in imports
                        if module == "ea_node_editor.execution"
                        or module.startswith("ea_node_editor.execution.")
                    }
                )

    def test_execution_value_codec_is_contract_compatibility_export(self) -> None:
        codec_tree = parse_module("ea_node_editor/execution/runtime_value_codec.py")

        self.assertIn("RuntimeValueRef", imported_names_from(codec_tree, "ea_node_editor.runtime_contracts"))
        self.assertIn("serialize_runtime_value", imported_names_from(codec_tree, "ea_node_editor.runtime_contracts"))
        self.assertIn("deserialize_runtime_value", imported_names_from(codec_tree, "ea_node_editor.runtime_contracts"))
        self.assertNotIn("_coerce_runtime_value_ref", declared_python_names(codec_tree))
        self.assertNotIn("_extract_runtime_marker", declared_python_names(codec_tree))

    def test_transform_surface_reexports_focused_operation_modules(self) -> None:
        self.assertEqual(transforms.collect_layout_node_bounds.__module__, "ea_node_editor.graph.transform_layout_ops")
        self.assertEqual(transforms.build_subtree_fragment_payload_data.__module__, "ea_node_editor.graph.transform_fragment_ops")
        self.assertEqual(transforms.plan_subnode_shell_pin_addition.__module__, "ea_node_editor.graph.transform_subnode_ops")
        self.assertEqual(transforms.group_selection_into_subnode.__module__, "ea_node_editor.graph.transform_grouping_ops")
        self.assertEqual(transforms.ungroup_subnode.__module__, "ea_node_editor.graph.transform_grouping_ops")

    def test_mutation_service_keeps_packet_owned_raw_write_helpers_internal(self) -> None:
        self.assertFalse(hasattr(WorkspaceMutationService, "add_node_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "add_edge_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "remove_node_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "remove_edge_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "set_node_parent_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "set_node_fragment_state"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_add_node_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_add_edge_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_remove_node_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_remove_edge_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_set_node_parent_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_set_node_fragment_state_record"))

    def test_graph_mutation_authority_uses_private_model_record_writers(self) -> None:
        normalization_tree = parse_module("ea_node_editor/graph/normalization.py")
        mutation_tree = parse_module("ea_node_editor/graph/mutation_service.py")
        validated_methods = {
            node.name
            for node in class_node(normalization_tree, "ValidatedGraphMutation").body
            if isinstance(node, ast.FunctionDef)
        }

        for method_name in {
            "remove_edge",
            "remove_node",
            "set_edge_label",
            "set_edge_visual_style",
            "set_node_collapsed",
            "set_node_geometry",
            "set_node_position",
            "set_node_title",
            "set_node_visual_style",
            "set_port_label",
        }:
            self.assertNotIn(method_name, validated_methods)

        public_model_write_calls = {
            "self.model.add_edge",
            "self.model.add_node",
            "self.model.remove_edge",
            "self.model.remove_node",
            "self.model.set_edge_label",
            "self.model.set_edge_visual_style",
            "self.model.set_exposed_port",
            "self.model.set_node_collapsed",
            "self.model.set_node_geometry",
            "self.model.set_node_position",
            "self.model.set_node_property",
            "self.model.set_node_title",
            "self.model.set_node_visual_style",
            "self.model.set_port_label",
        }
        self.assertFalse(public_model_write_calls & call_names(normalization_tree))
        self.assertFalse(public_model_write_calls & call_names(mutation_tree))

        normalization_calls = call_names(normalization_tree)
        mutation_calls = call_names(mutation_tree)
        self.assertIn("self.model._add_node_record", normalization_calls)
        self.assertIn("self.model._add_edge_record", normalization_calls)
        self.assertIn("self.model._set_node_property_record", normalization_calls)
        self.assertIn("self.model._add_node_record", mutation_calls)
        self.assertIn("self.model._set_node_fragment_state_record", mutation_calls)

    def test_fragment_payload_helpers_share_model_mapping_parsers(self) -> None:
        normalization_tree = parse_module("ea_node_editor/graph/normalization.py")
        fragment_tree = parse_module("ea_node_editor/graph/transform_fragment_ops.py")

        self.assertTrue(
            {
                "edge_instance_from_mapping",
                "edge_instance_to_mapping",
                "node_instance_from_mapping",
                "node_instance_to_mapping",
            }
            <= imported_names_from(normalization_tree, "ea_node_editor.graph.model")
        )
        self.assertTrue(
            {
                "edge_instance_from_mapping",
                "edge_instance_to_mapping",
                "node_instance_to_mapping",
            }
            <= imported_names_from(fragment_tree, "ea_node_editor.graph.model")
        )
        self.assertNotIn("GraphInvariantKernel.fragment_node_from_payload", call_names(fragment_tree))
        self.assertNotIn("GraphInvariantKernel.graph_fragment_payload_is_valid", call_names(fragment_tree))

    def test_closeout_docs_publish_architecture_residual_matrix_from_packet_owned_surfaces(self) -> None:
        spec_index_text = (REPO_ROOT / manifest.SPEC_INDEX_DOC).read_text(encoding="utf-8")
        qa_acceptance_text = (REPO_ROOT / manifest.QA_ACCEPTANCE_DOC).read_text(encoding="utf-8")
        traceability_text = (REPO_ROOT / manifest.TRACEABILITY_MATRIX_DOC).read_text(encoding="utf-8")
        matrix_path = REPO_ROOT / manifest.ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC
        matrix_text = matrix_path.read_text(encoding="utf-8")

        self.assertIn("ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md", spec_index_text)
        self.assertIn("REQ-QA-029", qa_acceptance_text)
        self.assertIn("ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md", qa_acceptance_text)
        self.assertIn("REQ-QA-029", traceability_text)
        self.assertIn("AC-REQ-QA-029-01", traceability_text)
        self.assertIn("ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md", traceability_text)
        self.assertTrue(matrix_path.is_file())
        self.assertIn(manifest.ARCHITECTURE_RESIDUAL_REFACTOR_TARGETED_REGRESSION_COMMAND, matrix_text)


if __name__ == "__main__":
    unittest.main()
