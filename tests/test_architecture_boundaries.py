from __future__ import annotations

import ast
import importlib.util
import unittest
from pathlib import Path

import corex
from ea_node_editor.graph import transforms
from ea_node_editor.graph.record_mutation_ops import GraphRecordMutation
from scripts import verification_manifest as manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
_RETIRED_GUARDRAIL_PRESENT_NAMES = {
    (
        "graph_canvas_qml_legacy_view_alias",
        "ea_node_editor/ui_qml/components/GraphCanvas.qml",
    ): {"_legacyCanvasViewBridgeRef"},
    ("old_preference_schema_compatibility", "ea_node_editor/app_preferences.py"): {
        "_APP_PREFERENCES_MIGRATION_VERSION",
    },
    ("runtime_project_doc_trigger_compatibility", "ea_node_editor/execution/runtime_snapshot.py"): {
        "sanitize_execution_trigger",
    },
}


def parse_module(relative_path: str) -> ast.Module:
    return ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8-sig"), filename=relative_path)


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


def top_level_imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in tree.body:
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
                if surface.expectation == manifest.COREX_NO_LEGACY_GUARDRAIL_PATH_ABSENT:
                    self.assertFalse(source_path.exists())
                    continue
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

    def test_graph_mutation_operations_use_graph_owned_boundary_adapters(self) -> None:
        self.assertFalse((REPO_ROOT / "ea_node_editor/graph/mutation_service.py").exists())
        validated_tree = parse_module("ea_node_editor/graph/validated_mutation.py")
        comment_tree = parse_module("ea_node_editor/graph/group_backdrop_mutation_ops.py")
        imports = imported_modules(validated_tree) | imported_modules(comment_tree)

        self.assertNotIn("ea_node_editor.ui.pdf_preview_provider", imports)
        self.assertNotIn("ea_node_editor.ui_qml.edge_routing", imports)
        self.assertNotIn("ea_node_editor.graph.transforms", imports)
        self.assertTrue(
            {"GraphBoundaryAdapters", "fallback_graph_boundary_adapters"}
            <= imported_names_from(validated_tree, "ea_node_editor.graph.boundary_adapters")
        )

        boundary_field = class_ann_assign(validated_tree, "ValidatedGraphMutation", "boundary_adapters")
        self.assertIsInstance(boundary_field.value, ast.Call)
        self.assertEqual("field", qualified_name(boundary_field.value.func))
        default_factory = next(
            keyword.value
            for keyword in boundary_field.value.keywords
            if keyword.arg == "default_factory"
        )
        self.assertEqual("fallback_graph_boundary_adapters", qualified_name(default_factory))
        self.assertIn("adapters.node_size", call_names(comment_tree))

    def test_scene_bridge_injects_ui_boundary_implementations_without_global_installation(self) -> None:
        tree = parse_module("ea_node_editor/ui_qml/graph_scene_bridge.py")

        self.assertIn("build_graph_boundary_adapters", imported_names_from(tree, "ea_node_editor.graph.boundary_adapters"))
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

    def test_canvas_bridge_owners_and_effective_port_policy_have_single_authority(self) -> None:
        canvas_text = (REPO_ROOT / "ea_node_editor/ui_qml/components/GraphCanvas.qml").read_text(encoding="utf-8")
        mutation_history_text = (
            REPO_ROOT / "ea_node_editor/ui_qml/graph_scene_mutation_history.py"
        ).read_text(encoding="utf-8")
        mutation_policy_tree = parse_module("ea_node_editor/ui_qml/graph_scene_mutation/policy.py")
        policy_bridge_tree = parse_module("ea_node_editor/ui_qml/graph_scene/policy_bridge.py")

        self.assertIn("readonly property var canvasStateBridgeRef: root.canvasStateBridge || null", canvas_text)
        self.assertIn("readonly property var canvasCommandBridgeRef: root.canvasCommandBridge || null", canvas_text)
        self.assertIn("readonly property var canvasViewBridgeRef: root._canvasViewportBridge", canvas_text)
        self.assertIn("readonly property var sceneCommandBridge: root.canvasCommandBridgeRef", canvas_text)
        self.assertIn("readonly property var sceneBridge: root.canvasStateBridgeRef", canvas_text)
        for retired_name in (
            "graphCanvasFacade",
            "canvasFacadeRef",
            "_facadeService",
            "graphCanvasFacadeAdapter",
            "_canvasStateBridgeRef",
            "_canvasViewStateBridgeRef",
        ):
            with self.subTest(retired_name=retired_name):
                self.assertNotIn(retired_name, canvas_text)
        self.assertNotIn("_viewportBridgeFrom", canvas_text)

        self.assertEqual(
            imported_names_from(policy_bridge_tree, "ea_node_editor.graph.effective_ports"),
            {"are_port_kinds_compatible"},
        )
        self.assertIn("registry.data_types.compatibility(", (
            REPO_ROOT / "ea_node_editor/ui_qml/graph_scene/policy_bridge.py"
        ).read_text(encoding="utf-8"))
        self.assertNotIn("are_port_kinds_compatible", declared_python_names(mutation_policy_tree))
        self.assertNotIn("are_data_types_compatible", declared_python_names(mutation_policy_tree))
        self.assertNotIn("GraphSceneMutationPolicy.are_port_kinds_compatible = staticmethod", mutation_history_text)
        self.assertNotIn("GraphSceneMutationPolicy.are_data_types_compatible = staticmethod", mutation_history_text)

    def test_graph_model_exposes_direct_mutation_operation_factories(self) -> None:
        model_tree = parse_module("ea_node_editor/graph/model.py")
        validated_tree = parse_module("ea_node_editor/graph/validated_mutation.py")
        view_tree = parse_module("ea_node_editor/graph/workspace_view_ops.py")
        helper_tree = parse_module("ea_node_editor/ui_qml/graph_scene_mutation_history.py")
        composition_trees = [
            parse_module(path.relative_to(REPO_ROOT).as_posix())
            for path in sorted((REPO_ROOT / "ea_node_editor/ui/shell/composition").glob("*.py"))
        ]

        self.assertNotIn("WorkspaceMutationService", call_names(model_tree))
        self.assertNotIn("ea_node_editor.graph.mutation_service", imported_modules(model_tree))
        self.assertFalse((REPO_ROOT / "ea_node_editor/graph/mutation_service.py").exists())
        self.assertNotIn("mutation_service_factory", function_args(method_node(model_tree, "GraphModel", "__init__")))
        self.assertIn("boundary_adapters", function_args(method_node(model_tree, "GraphModel", "validated_mutations")))
        self.assertIn("ValidatedGraphMutation", declared_python_names(validated_tree))
        self.assertIn("WorkspaceViewMutation", declared_python_names(view_tree))
        self.assertIn("workspace_view_mutations", declared_python_names(view_tree))
        self.assertIn("model.validated_mutations", call_names(helper_tree))
        self.assertNotIn("model.mutation_service", call_names(helper_tree))
        self.assertIn("GraphRecordMutation", declared_python_names(helper_tree))
        self.assertNotIn("WorkspaceMutationService", call_names(helper_tree))
        for composition_tree in composition_trees:
            self.assertNotIn(
                "create_workspace_mutation_service",
                imported_names_from(composition_tree, "ea_node_editor.graph.mutation_service"),
            )
            self.assertNotIn("mutation_service_factory", call_names(composition_tree))

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
        self.assertNotIn("ea_node_editor.persistence.project_codec", imported_modules(snapshot_tree))
        snapshot_names = {node.id for node in ast.walk(snapshot_tree) if isinstance(node, ast.Name)}
        assembly_names = {node.id for node in ast.walk(assembly_tree) if isinstance(node, ast.Name)}
        self.assertNotIn("normalize_artifact_store_metadata", snapshot_names)
        self.assertIn("RuntimeSnapshotAssembly", {node.name for node in assembly_tree.body if isinstance(node, ast.ClassDef)})
        self.assertNotIn("JsonProjectMigration", assembly_names)
        self.assertNotIn("normalize_artifact_store_metadata", assembly_names)
        build_runtime_snapshot = next(
            node
            for node in snapshot_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "build_runtime_snapshot"
        )
        self.assertNotIn("serializer", {arg.arg for arg in build_runtime_snapshot.args.args})
        self.assertNotIn("sanitize_execution_trigger", snapshot_names)
        self.assertNotIn("ea_node_editor.persistence.serializer", imported_modules(worker_runtime_tree))

    def test_headless_runtime_api_does_not_import_ui_or_qt(self) -> None:
        tree = parse_module("ea_node_editor/execution/headless_runtime.py")
        imports = imported_modules(tree)
        forbidden_prefixes = (
            "PyQt6",
            "ea_node_editor.app",
            "ea_node_editor.ui",
            "ea_node_editor.ui_qml",
        )
        offenders = sorted(
            module
            for module in imports
            if any(
                module == prefix or module.startswith(f"{prefix}.")
                for prefix in forbidden_prefixes
            )
        )

        self.assertEqual(offenders, [])

    def test_shell_execution_client_uses_headless_runtime_boundary(self) -> None:
        tree = parse_module("ea_node_editor/ui/shell/composition/controllers.py")

        self.assertIn("CorexRuntime", imported_names_from(tree, "ea_node_editor.execution.headless_runtime"))
        self.assertNotIn("ProcessExecutionClient", imported_names_from(tree, "ea_node_editor.execution.client"))

    def test_solution_store_stays_execution_owned_and_persistence_neutral(self) -> None:
        imports = imported_modules(
            parse_module("ea_node_editor/execution/solution_store.py")
        )
        self.assertFalse(
            {
                module
                for module in imports
                if module.startswith("ea_node_editor.persistence")
                or module.startswith("ea_node_editor.ui")
                or module.startswith("ea_node_editor.ui_qml")
            }
        )

    def test_solution_repository_implements_only_the_execution_port_boundary(self) -> None:
        imports = imported_modules(
            parse_module("ea_node_editor/persistence/solution_repository.py")
        )
        self.assertIn("ea_node_editor.execution.solution_store", imports)
        self.assertFalse(
            {
                module
                for module in imports
                if module.startswith("ea_node_editor.execution.")
                and module != "ea_node_editor.execution.solution_store"
            }
        )
        self.assertNotIn("ea_node_editor.persistence.serializer", imports)
        self.assertNotIn("ea_node_editor.persistence.project_codec", imports)

    def test_project_artifact_store_replacement_uses_public_controller_boundary(
        self,
    ) -> None:
        controller_tree = parse_module(
            "ea_node_editor/ui/shell/controllers/project_session_controller.py"
        )
        project_files_tree = parse_module(
            "ea_node_editor/ui/shell/controllers/"
            "project_session_services_support/project_files_service.py"
        )
        controller_methods = {
            node.name
            for node in class_node(
                controller_tree,
                "ProjectSessionController",
            ).body
            if isinstance(node, ast.FunctionDef)
        }
        project_files_methods = {
            node.name
            for node in class_node(project_files_tree, "ProjectFilesService").body
            if isinstance(node, ast.FunctionDef)
        }

        self.assertIn("replace_project_artifact_store", controller_methods)
        self.assertIn("replace_project_artifact_store", project_files_methods)
        self.assertNotIn("_set_project_artifact_store", controller_methods)
        self.assertNotIn("_set_project_artifact_store", project_files_methods)

        for relative_path in (
            "ea_node_editor/ui/shell/controllers/workspace_navigation_controller.py",
            "ea_node_editor/ui_qml/content_fullscreen_bridge.py",
            "ea_node_editor/ui_qml/graph_scene_mutation_history.py",
        ):
            with self.subTest(path=relative_path):
                self.assertNotIn(
                    "_set_project_artifact_store",
                    (REPO_ROOT / relative_path).read_text(encoding="utf-8"),
                )

    def test_content_fullscreen_uses_only_explicit_owner_dependencies(self) -> None:
        relative_path = "ea_node_editor/ui_qml/content_fullscreen_bridge.py"
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        bridge = class_node(parse_module(relative_path), "ContentFullscreenBridge")
        init = next(
            node
            for node in bridge.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        self.assertEqual(
            [argument.arg for argument in init.args.kwonlyargs],
            [
                "model_provider",
                "registry_provider",
                "active_workspace_id_provider",
                "project_context_provider",
                "scene_bridge",
                "viewer_session_bridge",
                "run_state",
                "execution_state_changed_signal",
                "script_editor",
                "save_file_dialog",
                "trim_video_clip_replace",
                "trim_video_clip_copy",
                "create_web_surface_artifact_service",
            ],
        )
        for retired in (
            "ShellWindow",
            "shell_window",
            "_shell_window",
            "_ContentFullscreenPolicyService",
            "_policy_service",
            "_set_selected_node_property",
        ):
            self.assertNotIn(retired, source)

        runtime_source = (
            REPO_ROOT / "ea_node_editor/ui/shell/composition/runtime_services.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "persist_artifact_store=project_session.replace_project_artifact_store",
            runtime_source,
        )
        self.assertNotIn("persist_project_metadata=", runtime_source)
        for service_path in (
            "ea_node_editor/ui_qml/viewer_host_service.py",
            "ea_node_editor/ui_qml/plot_host_service.py",
        ):
            service_source = (REPO_ROOT / service_path).read_text(encoding="utf-8")
            self.assertNotIn("_connect_content_fullscreen_bridge", service_source)

    def test_solution_repository_has_no_project_commit_and_t08_owns_prune_call(self) -> None:
        repository_source = (
            REPO_ROOT / "ea_node_editor" / "persistence" / "solution_repository.py"
        ).read_text(encoding="utf-8")
        production_source = "\n".join(
            path.read_text(encoding="utf-8")
            for root in (
                REPO_ROOT / "ea_node_editor" / "execution",
                REPO_ROOT / "ea_node_editor" / "persistence",
                REPO_ROOT / "ea_node_editor" / "ui" / "shell",
            )
            for path in root.rglob("*.py")
        )
        self.assertNotIn("os.replace(", repository_source)
        self.assertNotIn("JsonProjectSerializer", repository_source)
        self.assertEqual(production_source.count(".prune_unreachable_paths("), 1)
        self.assertIn(
            "def collect_project_solution_garbage(",
            repository_source,
        )

    def test_production_save_path_uses_only_copy_on_write_staging(self) -> None:
        document_io_source = (
            REPO_ROOT
            / "ea_node_editor"
            / "ui"
            / "shell"
            / "controllers"
            / "project_session_services_support"
            / "document_io_service.py"
        ).read_text(encoding="utf-8")
        save_source = document_io_source.split("def _run_project_save(", 1)[1]
        self.assertIn(".stage_project_save(", save_source)
        self.assertIn('"stage_project_solution_save"', save_source)
        self.assertIn(".stage_document(", save_source)
        self.assertNotIn(".migrate_workspace_artifact_folders(", save_source)
        self.assertNotIn(".commit_referenced_artifacts(", save_source)
        self.assertNotIn(".save_document(", save_source)
        self.assertNotIn("project_save_as_dialog", document_io_source)

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

    def test_settled_results_have_one_runtime_contract_owner(self) -> None:
        settled_tree = parse_module(
            "ea_node_editor/runtime_contracts/settled_results.py"
        )
        protocol_tree = parse_module("ea_node_editor/execution/protocol.py")
        worker_runtime_tree = parse_module(
            "ea_node_editor/execution/worker_runtime.py"
        )
        settled_classes = {
            node.name for node in settled_tree.body if isinstance(node, ast.ClassDef)
        }
        protocol_classes = {
            node.name for node in protocol_tree.body if isinstance(node, ast.ClassDef)
        }
        worker_runtime_classes = {
            node.name
            for node in worker_runtime_tree.body
            if isinstance(node, ast.ClassDef)
        }

        self.assertTrue(
            {"RootExecutionError", "SettledPortResult"} <= settled_classes
        )
        self.assertFalse(
            {"RootExecutionError", "SettledPortResult"} & protocol_classes
        )
        self.assertNotIn("ExecutionPlan", worker_runtime_classes)

        offenders: dict[str, list[str]] = {}
        for root_name in ("ea_node_editor", "tests"):
            for source_path in (REPO_ROOT / root_name).rglob("*.py"):
                relative_path = source_path.relative_to(REPO_ROOT).as_posix()
                old_owner_imports = sorted(
                    imported_names_from(
                        parse_module(relative_path),
                        "ea_node_editor.execution.protocol",
                    )
                    & {"RootExecutionError", "SettledPortResult"}
                )
                if old_owner_imports:
                    offenders[relative_path] = old_owner_imports
        self.assertEqual(offenders, {})

    def test_nodes_sdk_modules_do_not_import_runtime_or_ui_implementations_at_module_load(self) -> None:
        nodes_root = REPO_ROOT / "ea_node_editor" / "nodes"
        forbidden_prefixes = (
            "ea_node_editor.execution",
            "ea_node_editor.persistence",
            "ea_node_editor.ui",
            "ea_node_editor.ui_qml",
        )

        offenders: dict[str, list[str]] = {}
        for source_path in nodes_root.rglob("*.py"):
            relative_path = source_path.relative_to(REPO_ROOT).as_posix()
            imports = top_level_imported_modules(parse_module(relative_path))
            forbidden_imports = sorted(
                module
                for module in imports
                if any(
                    module == prefix or module.startswith(f"{prefix}.")
                    for prefix in forbidden_prefixes
                )
            )
            if forbidden_imports:
                offenders[relative_path] = forbidden_imports

        self.assertEqual(offenders, {})

    def test_public_corex_sdk_is_dependency_free(self) -> None:
        self.assertEqual(
            corex.__all__,
            [
                "node",
                "input",
                "output",
                "text",
                "text_area",
                "number",
                "switch",
                "dropdown",
                "slider",
                "color",
                "path",
                "interval",
                "list",
                "Any",
                "Image",
                "Color",
                "Interval",
            ],
        )
        offenders: dict[str, list[str]] = {}
        for source_path in (REPO_ROOT / "corex").rglob("*.py"):
            relative_path = source_path.relative_to(REPO_ROOT).as_posix()
            imports = imported_modules(parse_module(relative_path))
            forbidden = sorted(
                module
                for module in imports
                if module == "ea_node_editor"
                or module.startswith("ea_node_editor.")
                or module.startswith("PyQt")
            )
            if forbidden:
                offenders[relative_path] = forbidden

        self.assertEqual(offenders, {})

    def test_function_declaration_modules_stay_inside_nodes_sdk_boundary(self) -> None:
        forbidden_prefixes = (
            "ea_node_editor.execution",
            "ea_node_editor.persistence",
            "ea_node_editor.ui",
            "ea_node_editor.ui_qml",
        )
        offenders: dict[str, list[str]] = {}
        for relative_path in (
            "ea_node_editor/nodes/declaration_engine.py",
            "ea_node_editor/nodes/plugin_declaration.py",
        ):
            imports = top_level_imported_modules(parse_module(relative_path))
            forbidden = sorted(
                module
                for module in imports
                if any(
                    module == prefix or module.startswith(f"{prefix}.")
                    for prefix in forbidden_prefixes
                )
            )
            if forbidden:
                offenders[relative_path] = forbidden

        self.assertEqual(offenders, {})

    def test_package_internal_code_does_not_import_nodes_types_barrel(self) -> None:
        package_root = REPO_ROOT / "ea_node_editor"
        forbidden_module = "ea_node_editor.nodes.types"
        offenders: list[str] = []

        for source_path in package_root.rglob("*.py"):
            relative_path = source_path.relative_to(REPO_ROOT).as_posix()
            for node in ast.walk(parse_module(relative_path)):
                if isinstance(node, ast.ImportFrom) and node.level:
                    package = ".".join(source_path.parent.relative_to(REPO_ROOT).parts)
                    imported_module = importlib.util.resolve_name(
                        f"{'.' * node.level}{node.module or ''}",
                        package,
                    )
                else:
                    imported_module = node.module if isinstance(node, ast.ImportFrom) else None
                imports_barrel = (
                    isinstance(node, ast.ImportFrom)
                    and (
                        imported_module == forbidden_module
                        or (
                            imported_module == "ea_node_editor.nodes"
                            and any(alias.name == "types" for alias in node.names)
                        )
                    )
                ) or (
                    isinstance(node, ast.Import)
                    and any(alias.name == forbidden_module for alias in node.names)
                )
                if imports_barrel:
                    offenders.append(f"{relative_path}:{node.lineno}")

        self.assertEqual(offenders, [])

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

    def test_record_mutation_ops_keep_packet_owned_raw_write_helpers_internal(self) -> None:
        self.assertFalse(hasattr(GraphRecordMutation, "add_node_raw"))
        self.assertFalse(hasattr(GraphRecordMutation, "add_edge_raw"))
        self.assertFalse(hasattr(GraphRecordMutation, "remove_node_raw"))
        self.assertFalse(hasattr(GraphRecordMutation, "remove_edge_raw"))
        self.assertFalse(hasattr(GraphRecordMutation, "set_node_parent_raw"))
        self.assertFalse(hasattr(GraphRecordMutation, "set_node_fragment_state"))
        self.assertTrue(hasattr(GraphRecordMutation, "_add_node_record"))
        self.assertTrue(hasattr(GraphRecordMutation, "_add_edge_record"))
        self.assertTrue(hasattr(GraphRecordMutation, "_remove_node_record"))
        self.assertTrue(hasattr(GraphRecordMutation, "_remove_edge_record"))
        self.assertTrue(hasattr(GraphRecordMutation, "_set_node_parent_record"))
        self.assertTrue(hasattr(GraphRecordMutation, "_set_node_fragment_state_record"))

    def test_graph_mutation_authority_uses_private_model_record_writers(self) -> None:
        validated_tree = parse_module("ea_node_editor/graph/validated_mutation.py")
        record_tree = parse_module("ea_node_editor/graph/record_mutation_ops.py")
        fragment_tree = parse_module("ea_node_editor/graph/transform_fragment_ops.py")
        grouping_tree = parse_module("ea_node_editor/graph/transform_grouping_ops.py")
        comment_tree = parse_module("ea_node_editor/graph/group_backdrop_mutation_ops.py")
        validated_methods = {
            node.name
            for node in class_node(validated_tree, "ValidatedGraphMutation").body
            if isinstance(node, ast.FunctionDef)
        }

        for method_name in {
            "remove_edge",
            "remove_node",
            "set_edge_label",
            "set_edge_visual_style",
            "set_node_settings_section_expanded",
            "set_node_collapsed",
            "set_node_geometry",
            "set_node_position",
            "set_node_title",
            "set_node_visual_style",
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
            "self.model.set_node_settings_section_expanded",
            "self.model.set_node_collapsed",
            "self.model.set_node_geometry",
            "self.model.set_node_position",
            "self.model.set_node_property",
            "self.model.set_node_title",
            "self.model.set_node_visual_style",
            "self.model.set_port_label",
        }
        self.assertFalse(public_model_write_calls & call_names(validated_tree))
        for tree in (record_tree, fragment_tree, grouping_tree, comment_tree):
            with self.subTest(module=getattr(tree, "type_ignores", None)):
                self.assertFalse(public_model_write_calls & call_names(tree))

        validated_calls = call_names(validated_tree)
        record_calls = call_names(record_tree)
        fragment_calls = call_names(fragment_tree)
        grouping_calls = call_names(grouping_tree)
        comment_calls = call_names(comment_tree)
        self.assertIn("self.model._add_node_record", validated_calls)
        self.assertIn("self.model._add_edge_record", validated_calls)
        self.assertIn("self.model._set_node_property_record", validated_calls)
        self.assertIn("self.model._add_node_record", record_calls)
        self.assertIn("self.model._set_node_fragment_state_record", record_calls)
        self.assertIn("mutations._add_node_record", fragment_calls)
        self.assertIn("records._add_edge_record", grouping_calls)
        self.assertIn("model._set_node_geometry_record", comment_calls)

    def test_graph_view_mutations_and_dirty_marking_use_workspace_domain_boundary(self) -> None:
        model_tree = parse_module("ea_node_editor/graph/model.py")
        workspace_state_tree = parse_module("ea_node_editor/graph/workspace_state.py")
        view_tree = parse_module("ea_node_editor/graph/workspace_view_ops.py")
        validated_tree = parse_module("ea_node_editor/graph/validated_mutation.py")

        workspace_methods = {
            node.name
            for node in class_node(workspace_state_tree, "WorkspaceData").body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertTrue({"active_view_state", "mark_dirty"} <= workspace_methods)
        self.assertNotIn("workspace.dirty = True", (REPO_ROOT / "ea_node_editor/graph/model.py").read_text(encoding="utf-8"))
        self.assertNotIn(
            "workspace.dirty = True",
            (REPO_ROOT / "ea_node_editor/graph/workspace_state.py").read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "self.workspace.dirty = True",
            (REPO_ROOT / "ea_node_editor/graph/workspace_view_ops.py").read_text(encoding="utf-8"),
        )
        self.assertNotIn("self.workspace.dirty = True", (REPO_ROOT / "ea_node_editor/graph/validated_mutation.py").read_text(encoding="utf-8"))

        view_to_record_writer = {
            "create_view": "self.model._create_view_record",
            "set_active_view": "self.model._set_active_view_record",
            "close_view": "self.model._close_view_record",
            "rename_view": "self.model._rename_view_record",
            "move_view": "self.model._move_view_record",
        }
        for public_method, private_writer in view_to_record_writer.items():
            with self.subTest(method=public_method):
                model_method_calls = call_names(method_node(model_tree, "GraphModel", public_method))
                view_method_calls = call_names(method_node(view_tree, "WorkspaceViewMutation", public_method))

                self.assertIn("self.workspace_view_mutations", model_method_calls)
                self.assertIn(private_writer, view_method_calls)
                self.assertNotIn(f"self.model.{public_method}", view_method_calls)

        self.assertIn(
            "self.workspace.active_view_state",
            call_names(method_node(validated_tree, "ValidatedGraphMutation", "_active_view_state")),
        )
        self.assertIn(
            "self.workspace.active_view_state",
            call_names(method_node(view_tree, "WorkspaceViewMutation", "active_view_state")),
        )

    def test_workspace_manager_owns_order_not_view_lifecycle_mutation(self) -> None:
        manager_tree = parse_module("ea_node_editor/workspace/manager.py")

        self.assertIn(
            "resolve_workspace_ownership",
            imported_names_from(manager_tree, "ea_node_editor.workspace.ownership"),
        )
        self.assertNotIn(
            "sync_project_workspace_ownership",
            imported_names_from(manager_tree, "ea_node_editor.workspace.ownership"),
        )
        manager_methods = {
            node.name
            for node in class_node(manager_tree, "WorkspaceManager").body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertFalse(
            {
                "create_view",
                "set_active_view",
                "close_view",
                "rename_view",
                "move_view",
            }
            & manager_methods
        )

    def test_workspace_navigation_view_lifecycle_uses_view_mutation_boundary(self) -> None:
        navigation_tree = parse_module("ea_node_editor/ui/shell/controllers/workspace_navigation_controller.py")

        for method_name in {"close_view", "rename_view", "move_view"}:
            with self.subTest(method=method_name):
                method_calls = call_names(method_node(navigation_tree, "WorkspaceNavigationController", method_name))
                self.assertIn("self._host.model.workspace_view_mutations", method_calls)

        navigation_calls = call_names(navigation_tree)
        self.assertNotIn("self._host.workspace_manager.close_view", navigation_calls)
        self.assertNotIn("self._host.workspace_manager.rename_view", navigation_calls)
        self.assertNotIn("self._host.workspace_manager.move_view", navigation_calls)

    def test_fragment_payload_helpers_share_model_mapping_parsers(self) -> None:
        fragment_payload_tree = parse_module("ea_node_editor/graph/fragment_payloads.py")
        fragment_tree = parse_module("ea_node_editor/graph/transform_fragment_ops.py")

        self.assertTrue(
            {
                "edge_instance_from_mapping",
                "edge_instance_to_mapping",
                "node_instance_from_mapping",
                "node_instance_to_mapping",
            }
            <= imported_names_from(fragment_payload_tree, "ea_node_editor.graph.record_payloads")
        )
        self.assertTrue(
            {
                "edge_instance_from_mapping",
                "edge_instance_to_mapping",
                "node_instance_to_mapping",
            }
            <= imported_names_from(fragment_tree, "ea_node_editor.graph.record_payloads")
        )
        self.assertTrue(
            {"fragment_node_from_payload", "normalize_graph_fragment_payload"}
            <= imported_names_from(fragment_tree, "ea_node_editor.graph.fragment_payloads")
        )
        self.assertIn(
            "graph_fragment_payload_is_valid",
            imported_names_from(fragment_tree, "ea_node_editor.graph.fragment_payloads"),
        )
        self.assertNotIn("GraphInvariantKernel.fragment_node_from_payload", call_names(fragment_tree))
        self.assertNotIn("GraphInvariantKernel.graph_fragment_payload_is_valid", call_names(fragment_tree))

    def test_graph_normalization_split_has_focused_owner_modules(self) -> None:
        self.assertFalse((REPO_ROOT / "ea_node_editor/graph/normalization.py").exists())

        fragment_payload_tree = parse_module("ea_node_editor/graph/fragment_payloads.py")
        invariant_tree = parse_module("ea_node_editor/graph/invariant_kernel.py")
        registry_tree = parse_module("ea_node_editor/graph/registry_normalization.py")
        validated_tree = parse_module("ea_node_editor/graph/validated_mutation.py")

        self.assertTrue(
            {
                "GRAPH_FRAGMENT_KIND",
                "GRAPH_FRAGMENT_VERSION",
                "build_graph_fragment_payload",
                "fragment_node_from_payload",
                "graph_fragment_payload_is_valid",
                "normalize_edge_label",
                "normalize_graph_fragment_payload",
                "normalize_visual_style_payload",
            }
            <= declared_python_names(fragment_payload_tree)
        )
        self.assertTrue(
            {
                "GraphInvariantKernel",
                "RegistryEdgeResolution",
                "RegistryNodeResolution",
                "accept_registry_edge",
                "resolve_registry_nodes",
                "validate_registry_edge",
            }
            <= declared_python_names(invariant_tree)
        )
        self.assertEqual(
            {"normalize_project_for_registry"} & declared_python_names(registry_tree),
            {"normalize_project_for_registry"},
        )
        self.assertEqual(
            {"ValidatedGraphMutation"} & declared_python_names(validated_tree),
            {"ValidatedGraphMutation"},
        )

    def test_graph_model_split_has_focused_owner_modules(self) -> None:
        model_tree = parse_module("ea_node_editor/graph/model.py")
        records_tree = parse_module("ea_node_editor/graph/records.py")
        payload_tree = parse_module("ea_node_editor/graph/record_payloads.py")
        workspace_state_tree = parse_module("ea_node_editor/graph/workspace_state.py")
        project_state_tree = parse_module("ea_node_editor/graph/project_state.py")
        hierarchy_tree = parse_module("ea_node_editor/graph/hierarchy.py")

        self.assertEqual({"GraphModel"} & declared_python_names(model_tree), {"GraphModel"})
        self.assertTrue({"NodeInstance", "EdgeInstance"} <= declared_python_names(records_tree))
        self.assertTrue(
            {
                "edge_instance_from_mapping",
                "edge_instance_to_mapping",
                "node_instance_from_mapping",
                "node_instance_to_mapping",
            }
            <= declared_python_names(payload_tree)
        )
        self.assertTrue(
            {"ViewState", "WorkspaceData", "WorkspaceSnapshot"}
            <= declared_python_names(workspace_state_tree)
        )
        self.assertIn("ProjectData", declared_python_names(project_state_tree))
        self.assertIn("sanitize_workspace_parent_links", declared_python_names(hierarchy_tree))
        self.assertFalse(
            {
                "ProjectData",
                "WorkspaceData",
                "WorkspaceSnapshot",
                "ViewState",
                "NodeInstance",
                "EdgeInstance",
                "node_instance_from_mapping",
                "edge_instance_from_mapping",
                "sanitize_workspace_parent_links",
            }
            & declared_python_names(model_tree)
        )

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
