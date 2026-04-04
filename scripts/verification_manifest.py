"""Canonical verification workflow facts for runner, tests, and proof audits."""

from __future__ import annotations

from dataclasses import dataclass

LOCAL_VENV_PYTHON_DISPLAY = "./venv/Scripts/python.exe"
RUN_VERIFICATION_SCRIPT = "scripts/run_verification.py"
CHECK_TRACEABILITY_SCRIPT = "scripts/check_traceability.py"
CHECK_MARKDOWN_LINKS_SCRIPT = "scripts/check_markdown_links.py"
OFFSCREEN_ENV = {"QT_QPA_PLATFORM": "offscreen"}
WORKTREE_PYTEST_IGNORE_PATHS = ("venv",)
SHELL_WINDOW_LIFECYCLE_TEST_PATH = "tests/test_shell_window_lifecycle.py"
SHELL_LIFECYCLE_TRUTH = "deterministic in-process shell window teardown"
SHELL_LIFECYCLE_SHARED_WINDOW_SCOPE = "repeated create/show/close cycles inside one isolated child process"

MODE_NAMES = ("fast", "gui", "slow", "full")
MAX_GUI_PARALLEL_WORKERS = 6

PACKAGING_WINDOWS_DOC = "docs/PACKAGING_WINDOWS.md"
PILOT_RUNBOOK_DOC = "docs/PILOT_RUNBOOK.md"
SPEC_INDEX_DOC = "docs/specs/INDEX.md"
QA_ACCEPTANCE_DOC = "docs/specs/requirements/90_QA_ACCEPTANCE.md"
TRACEABILITY_MATRIX_DOC = "docs/specs/requirements/TRACEABILITY_MATRIX.md"
VERIFICATION_SPEED_MATRIX_DOC = "docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md"
GRAPH_CANVAS_PERF_MATRIX_DOC = "docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md"
TRACK_H_BENCHMARK_REPORT_DOC = "docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md"
GRAPH_SURFACE_INPUT_MATRIX_DOC = "docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md"
ARCHITECTURE_REFACTOR_QA_MATRIX_DOC = "docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md"
ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX_DOC = (
    "docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md"
)
ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC = (
    "docs/specs/perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md"
)
CURRENT_CLOSEOUT_QA_MATRIX_DOC = ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX_DOC
MARKDOWN_HYGIENE_TEST = "tests/test_markdown_hygiene.py"

ARCHITECTURE_RESIDUAL_REFACTOR_TARGETED_REGRESSION_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_architecture_boundaries.py tests/test_shell_isolation_phase.py "
    "tests/test_traceability_checker.py tests/test_markdown_hygiene.py --ignore=venv -q"
)
ARCHITECTURE_RESIDUAL_REFACTOR_TRACEABILITY_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_traceability.py"
)
ARCHITECTURE_RESIDUAL_REFACTOR_MARKDOWN_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_markdown_links.py"
)
ARCHITECTURE_RESIDUAL_REFACTOR_PACKET_WRAPUPS = (
    "P01_shell_host_surface_retirement_WRAPUP.md",
    "P02_shell_lifecycle_isolation_hardening_WRAPUP.md",
    "P03_graph_scene_bridge_decomposition_WRAPUP.md",
    "P04_viewer_projection_authority_split_WRAPUP.md",
    "P05_runtime_snapshot_boundary_decoupling_WRAPUP.md",
    "P06_graph_mutation_service_decoupling_WRAPUP.md",
    "P07_shared_runtime_contract_extraction_WRAPUP.md",
)
ARCHITECTURE_RESIDUAL_REFACTOR_SPEC_INDEX_TOKENS = (
    "ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md",
)
ARCHITECTURE_RESIDUAL_REFACTOR_CURRENT_EVIDENCE_TOKENS = (
    ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC,
)

SERIALIZER_BASELINE_COMMAND = (
    "./venv/Scripts/python.exe -m pytest "
    "tests/test_serializer.py -k passive_image_panel_properties_and_size -q"
)
TRACK_H_REGRESSION_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_track_h_perf_harness.py tests/test_traceability_checker.py -q"
)
GRAPH_CANVAS_SNAPSHOT_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe "
    "-m ea_node_editor.telemetry.performance_harness "
    "--nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 "
    "--baseline-runs 1 --report-dir artifacts/graph_canvas_perf_docs"
)
DOCS_RELEASE_TRACEABILITY_PYTEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest "
    "tests/test_dead_code_hygiene.py tests/test_run_verification.py "
    "tests/test_traceability_checker.py tests/test_markdown_hygiene.py "
    "tests/test_shell_isolation_phase.py --ignore=venv -q"
)
GRAPH_CANVAS_REPORT_DIR = "artifacts/graph_canvas_perf_docs"
TRACK_H_BENCHMARK_ARTIFACT = "artifacts/graph_canvas_perf_docs/TRACK_H_BENCHMARK_REPORT.md"

SHELL_BACKED_TEST_PATHS = (
    "tests/test_main_window_shell.py",
    "tests/test_script_editor_dock.py",
    "tests/test_shell_run_controller.py",
    "tests/test_shell_project_session_controller.py",
)
SHELL_BACKED_TEST_MODULES = tuple(
    path.removesuffix(".py").replace("/", ".") for path in SHELL_BACKED_TEST_PATHS
)
SHELL_ISOLATION_PHASE_TEST = "tests/test_shell_isolation_phase.py"
NON_SHELL_PYTEST_IGNORES = SHELL_BACKED_TEST_PATHS + (SHELL_ISOLATION_PHASE_TEST,)

GUI_TEST_PATHS = (
    "tests/test_flow_edge_labels.py",
    "tests/test_flowchart_surfaces.py",
    "tests/test_flowchart_visual_polish.py",
    "tests/test_graph_surface_input_contract.py",
    "tests/test_graph_surface_input_controls.py",
    "tests/test_graph_surface_input_inline.py",
    "tests/test_graph_theme_editor_dialog.py",
    "tests/test_graph_theme_shell.py",
    "tests/test_graph_track_b.py",
    "tests/test_graphics_settings_dialog.py",
    "tests/test_main_window_shell.py",
    "tests/test_passive_graph_surface_host.py",
    "tests/test_passive_image_nodes.py",
    "tests/test_passive_style_dialogs.py",
    "tests/test_passive_style_presets.py",
    "tests/test_pdf_preview_provider.py",
    "tests/test_planning_annotation_catalog.py",
    "tests/test_script_editor_dock.py",
    "tests/test_shell_project_session_controller.py",
    "tests/test_shell_run_controller.py",
    SHELL_WINDOW_LIFECYCLE_TEST_PATH,
    "tests/test_shell_theme.py",
    "tests/test_viewer_surface_contract.py",
    "tests/test_viewer_surface_host.py",
    "tests/test_workflow_settings_dialog.py",
)
SLOW_TEST_PATHS = ("tests/test_track_h_perf_harness.py",)

XDIST_RESOLUTION_TOKENS = (
    "psutil.cpu_count(logical=True)",
    "os.cpu_count()",
    "1",
)

PROOF_AUDIT_REQUIRED_ARTIFACTS = (
    "ARCHITECTURE.md",
    "README.md",
    "docs/GETTING_STARTED.md",
    PACKAGING_WINDOWS_DOC,
    PILOT_RUNBOOK_DOC,
    SPEC_INDEX_DOC,
    "docs/specs/requirements/80_PERFORMANCE.md",
    QA_ACCEPTANCE_DOC,
    TRACEABILITY_MATRIX_DOC,
    CURRENT_CLOSEOUT_QA_MATRIX_DOC,
    ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC,
    ARCHITECTURE_REFACTOR_QA_MATRIX_DOC,
    GRAPH_CANVAS_PERF_MATRIX_DOC,
    "docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md",
    GRAPH_SURFACE_INPUT_MATRIX_DOC,
    VERIFICATION_SPEED_MATRIX_DOC,
    TRACK_H_BENCHMARK_REPORT_DOC,
    "docs/specs/perf/RC_PACKAGING_REPORT.md",
    "docs/specs/perf/PILOT_SIGNOFF.md",
    "scripts/build_windows_package.ps1",
    "scripts/build_windows_installer.ps1",
    CHECK_MARKDOWN_LINKS_SCRIPT,
    "scripts/run_verification.py",
    "scripts/sign_release_artifacts.ps1",
    "scripts/verification_manifest.py",
    "scripts/check_traceability.py",
    "tests/conftest.py",
    MARKDOWN_HYGIENE_TEST,
    "tests/test_dead_code_hygiene.py",
    "tests/test_run_verification.py",
    "tests/test_traceability_checker.py",
    "tests/test_shell_isolation_phase.py",
)


@dataclass(frozen=True)
class PytestPhaseSpec:
    """One non-shell pytest phase in the verification workflow."""

    mode: str
    phase: str
    marker_expression: str
    uses_xdist: bool
    worker_cap: int | None = None


@dataclass(frozen=True)
class ShellIsolationSpec:
    """Dedicated shell-isolation phase metadata."""

    phase: str
    test_path: str
    target_catalog_paths: tuple[str, ...]
    shell_module_paths: tuple[str, ...]
    shell_module_names: tuple[str, ...]


@dataclass(frozen=True)
class ShellIsolationCatalogSpec:
    """One manifest-owned shell-isolation target catalog."""

    label: str
    module_path: str
    module_name: str
    target_id_prefixes: tuple[str, ...]


@dataclass(frozen=True)
class ShellIsolationOwnershipSpec:
    """Manifest-owned ownership rule for shell-isolated regression surfaces."""

    source_path: str
    coverage_kind: str
    owner_name: str | None = None
    covered_names: tuple[str, ...] = ()
    excluded_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentRule:
    """Required and forbidden text snippets for a packet-owned proof document."""

    required: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()


PYTEST_PHASE_SPECS = (
    PytestPhaseSpec(
        mode="fast",
        phase="fast.pytest",
        marker_expression="not gui and not slow",
        uses_xdist=True,
    ),
    PytestPhaseSpec(
        mode="gui",
        phase="gui.pytest",
        marker_expression="gui and not slow",
        uses_xdist=True,
        worker_cap=MAX_GUI_PARALLEL_WORKERS,
    ),
    PytestPhaseSpec(
        mode="slow",
        phase="slow.pytest",
        marker_expression="slow",
        uses_xdist=False,
    ),
)
PYTEST_PHASE_SPECS_BY_MODE = {spec.mode: spec for spec in PYTEST_PHASE_SPECS}

SHELL_ISOLATION_CATALOG_SPECS = (
    ShellIsolationCatalogSpec(
        label="main-window",
        module_path="tests/shell_isolation_main_window_targets.py",
        module_name="tests.shell_isolation_main_window_targets",
        target_id_prefixes=("main_window__",),
    ),
    ShellIsolationCatalogSpec(
        label="controllers",
        module_path="tests/shell_isolation_controller_targets.py",
        module_name="tests.shell_isolation_controller_targets",
        target_id_prefixes=(
            "script_editor__",
            "run_controller__",
            "project_session__",
        ),
    ),
)
SHELL_ISOLATION_TARGET_CATALOG_PATHS = tuple(
    spec.module_path for spec in SHELL_ISOLATION_CATALOG_SPECS
)

SHELL_ISOLATION_SPEC = ShellIsolationSpec(
    phase="full.shell_isolation.pytest",
    test_path=SHELL_ISOLATION_PHASE_TEST,
    target_catalog_paths=SHELL_ISOLATION_TARGET_CATALOG_PATHS,
    shell_module_paths=SHELL_BACKED_TEST_PATHS,
    shell_module_names=SHELL_BACKED_TEST_MODULES,
)

SHELL_ISOLATION_OWNERSHIP_SPECS = (
    ShellIsolationOwnershipSpec(
        source_path="tests/test_main_window_shell.py",
        coverage_kind="class_targets",
        excluded_names=(
            "MainWindowShellContextBootstrapTests",
            "MainWindowGraphCanvasBridgeTests",
            "ShellWorkspaceBridgeQmlBoundaryTests",
            "GraphCanvasQmlBoundaryTests",
            "MainWindowNodeExecutionCanvasTests",
            "MainWindowShellGraphCanvasHostTests",
            "MainWindowShellHostFacadeDelegationTests",
        ),
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/bridge_contracts.py",
        coverage_kind="class_targets",
        covered_names=(
            "ShellLibraryBridgeTests",
            "ShellInspectorBridgeTests",
            "GraphCanvasBridgeTests",
            "ShellWorkspaceBridgeTests",
        ),
        excluded_names=(
            "MainWindowGraphCanvasBridgeTests",
            "SharedUiSupportBoundaryTests",
        ),
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/bridge_qml_boundaries.py",
        coverage_kind="class_targets",
        covered_names=(
            "ShellLibraryBridgeQmlBoundaryTests",
            "ShellInspectorBridgeQmlBoundaryTests",
            "ShellWorkspaceBridgeQmlBoundaryTests",
        ),
        excluded_names=("ShellStatusStripQmlBoundaryTests", "GraphCanvasQmlBoundaryTests"),
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/comment_backdrop_workflows.py",
        coverage_kind="class_targets",
        excluded_names=("MainWindowShellCommentBackdropWorkflowTests",),
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/drop_connect_and_workflow_io.py",
        coverage_kind="module_target",
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/edit_clipboard_history.py",
        coverage_kind="module_target",
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/passive_image_nodes.py",
        coverage_kind="class_targets",
        covered_names=("MainWindowShellPassiveImageNodesTests",),
        excluded_names=("MainWindowShellPassiveImageNodesSubprocessTests",),
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/passive_pdf_nodes.py",
        coverage_kind="class_targets",
        covered_names=("MainWindowShellPassivePdfNodesTests",),
        excluded_names=("MainWindowShellPassivePdfNodesSubprocessTests",),
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/passive_property_editors.py",
        coverage_kind="module_target",
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/passive_style_context_menus.py",
        coverage_kind="module_target",
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/shell_basics_and_search.py",
        coverage_kind="module_target",
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/shell_runtime_contracts.py",
        coverage_kind="class_targets",
        covered_names=(
            "FrameRateSamplerTests",
            "MainWindowShellTelemetryTests",
            "MainWindowShellBootstrapCompositionTests",
            "MainWindowShellContextBootstrapTests",
            "MainWindowShellHostProtocolStateTests",
            "_MainWindowShellGraphCanvasHostDirectTests",
        ),
        excluded_names=(
            "MainWindowShellStatusStripQuickToggleTests",
            "MainWindowShellPassiveImageNodesTests",
            "MainWindowShellPassivePdfNodesTests",
            "MainWindowShellGraphCanvasHostTests",
        ),
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/main_window_shell/view_library_inspector.py",
        coverage_kind="module_target",
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/test_script_editor_dock.py",
        coverage_kind="method_targets",
        owner_name="ScriptEditorDockTests",
        covered_names=(
            "test_script_editor_binds_to_selected_python_script_node",
            "test_script_editor_state_persists_in_metadata",
            "test_script_editor_exposes_cursor_diagnostics_and_dirty_state",
            "test_set_script_editor_panel_visible_focuses_editor_for_script_node",
        ),
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/test_shell_run_controller.py",
        coverage_kind="method_targets",
        owner_name="ShellRunControllerTests",
        covered_names=(
            "test_stream_log_events_are_scoped_to_active_run",
            "test_stale_run_events_do_not_mutate_active_run_ui",
            "test_failure_focus_reveals_parent_chain_when_present",
            "test_run_failed_event_centers_failed_node_and_reports_exception_details",
        ),
        excluded_names=(
            "test_node_execution_visualization_shell_events_drive_graph_node_chrome_states",
            "test_node_execution_visualization_failure_priority_overrides_completed_chrome",
            "test_nonfatal_run_failed_hides_elapsed_timer_for_failed_running_node",
            "test_viewer_session_bridge_context_property_exists_and_rerun_invalidates_current_workspace",
            "test_shell_context_bridge_fallbacks_wrap_shell_window_with_focused_sources",
            "test_fatal_run_failed_event_invalidates_viewer_sessions_as_worker_reset",
            "test_node_completed_artifact_ref_payload_keeps_run_ui_running",
            "test_new_run_clears_failed_node_highlight_before_start",
        ),
    ),
    ShellIsolationOwnershipSpec(
        source_path="tests/test_shell_project_session_controller.py",
        coverage_kind="scenario_targets",
        owner_name="ShellProjectSessionControllerTests",
        covered_names=(
            "test_session_restore_recovers_workspace_order_active_workspace_and_view_camera",
            "test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc",
            "test_recovery_prompt_accept_loads_newer_autosave",
            "test_recovery_prompt_reject_keeps_session_state_and_discards_autosave",
            "test_restore_session_handles_corrupted_session_and_autosave_files",
            "test_recovery_prompt_is_deferred_until_main_window_is_visible",
            "test_recent_project_paths_are_owned_by_explicit_session_state",
        ),
        excluded_names=(
            "test_saved_project_reopen_seeds_run_required_viewer_projection_without_persisting_live_transport",
            "test_session_restore_recovers_unsaved_temp_staged_refs_without_autosave",
            "test_recovery_prompt_accept_recovers_unsaved_temp_staged_refs",
            "test_recovery_prompt_is_skipped_when_autosave_matches_restored_session",
            "test_clean_close_discards_staged_scratch_and_clears_unsaved_root_hint",
            "test_explicit_save_promotes_referenced_staged_refs_and_prunes_orphans",
            "test_save_as_default_copy_switches_project_path_and_excludes_staging",
            "test_new_project_uses_navigation_controller_surface_without_workspace_library_facade",
            "test_project_files_menu_action_triggers_dialog",
            "test_save_prompt_receives_project_file_summary_before_saving",
            "test_open_project_path_can_abort_when_project_files_summary_has_staged_and_broken_entries",
            "test_recovery_prompt_receives_project_file_summary_for_recovered_project",
        ),
    ),
)

SHELL_ISOLATION_PHASE_KEY = "shell_isolation"
RUN_VERIFICATION_MODE_SEQUENCE = {
    "fast": ("fast",),
    "gui": ("gui",),
    "slow": ("slow",),
    "full": ("fast", "gui", "slow", SHELL_ISOLATION_PHASE_KEY),
}


def non_shell_pytest_ignore_args() -> tuple[str, ...]:
    """Return the documented pytest ignore arguments for non-shell phases."""

    return tuple(f"--ignore={path}" for path in NON_SHELL_PYTEST_IGNORES)


def worktree_pytest_ignore_args() -> tuple[str, ...]:
    """Return pytest ignore arguments required by packet worktrees."""

    return tuple(f"--ignore={path}" for path in WORKTREE_PYTEST_IGNORE_PATHS)


def run_verification_command(mode: str, *, dry_run: bool = False) -> str:
    """Return the documented developer-facing verification command."""

    argv = [LOCAL_VENV_PYTHON_DISPLAY, RUN_VERIFICATION_SCRIPT, "--mode", mode]
    if dry_run:
        argv.append("--dry-run")
    return " ".join(argv)


def shell_isolation_phase_pytest_args(
    worker_count: int | str | None = "<resolved_count>",
) -> tuple[str, ...]:
    """Return argv for the dedicated shell-isolation pytest phase."""

    argv = ("-m", "pytest", *worktree_pytest_ignore_args(), SHELL_ISOLATION_PHASE_TEST, "-q")
    if worker_count is not None:
        return (*argv, "-n", str(worker_count), "--dist", "load")
    return argv


def shell_isolation_pytest_command(worker_count: int | str | None = "<resolved_count>") -> str:
    """Return the documented dedicated shell-isolation pytest command."""

    argv = [
        "QT_QPA_PLATFORM=offscreen",
        LOCAL_VENV_PYTHON_DISPLAY,
        *shell_isolation_phase_pytest_args(worker_count),
    ]
    return " ".join(argv)


def shell_isolation_target_catalog_module_names() -> tuple[str, ...]:
    """Return the target catalog module names for shell-isolated child runs."""

    return tuple(spec.module_name for spec in SHELL_ISOLATION_CATALOG_SPECS)


def shell_isolation_target_id_prefixes() -> tuple[str, ...]:
    """Return the owned target-id prefixes across all shell-isolation catalogs."""

    return tuple(
        prefix
        for spec in SHELL_ISOLATION_CATALOG_SPECS
        for prefix in spec.target_id_prefixes
    )


def shell_isolation_ownership_specs_by_path() -> dict[str, ShellIsolationOwnershipSpec]:
    """Return manifest-owned shell-isolation ownership rules keyed by source path."""

    return {spec.source_path: spec for spec in SHELL_ISOLATION_OWNERSHIP_SPECS}


def shell_isolation_target_pytest_args(*nodeids: str) -> tuple[str, ...]:
    """Return argv for one or more shell-isolated pytest child targets."""

    if not nodeids:
        raise ValueError("shell_isolation_target_pytest_args requires at least one nodeid.")
    return ("-m", "pytest", *worktree_pytest_ignore_args(), *nodeids, "-q")


def shell_direct_unittest_commands() -> tuple[str, ...]:
    """Return the focused module-level shell rerun commands."""

    return tuple(
        f"QT_QPA_PLATFORM=offscreen {LOCAL_VENV_PYTHON_DISPLAY} -m unittest {module_name} -v"
        for module_name in SHELL_BACKED_TEST_MODULES
    )


def proof_audit_command() -> str:
    """Return the canonical proof-audit command."""

    return f"{LOCAL_VENV_PYTHON_DISPLAY} {CHECK_TRACEABILITY_SCRIPT}"


GENERIC_DOCUMENT_RULES: dict[str, DocumentRule] = {
    "README.md": DocumentRule(
        required=(
            CHECK_TRACEABILITY_SCRIPT,
            CHECK_MARKDOWN_LINKS_SCRIPT,
            "Graph Surface Input QA Matrix",
            "Verification Speed QA Matrix",
            "ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md",
            "dedicated fresh-process shell-isolation phase",
            SHELL_ISOLATION_SPEC.test_path,
            "proof-audit command",
            "SHELL_ISOLATION_CATALOG_SPECS",
        ),
        forbidden=(
            "Only the retained `PROJECT_MANAGED_FILES` packet window",
            "serializer caveat.",
            "shell-wrapper suites for isolated `unittest` execution",
        ),
    ),
    "docs/GETTING_STARTED.md": DocumentRule(
        required=(
            CHECK_TRACEABILITY_SCRIPT,
            CHECK_MARKDOWN_LINKS_SCRIPT,
            SHELL_ISOLATION_SPEC.test_path,
            XDIST_RESOLUTION_TOKENS[0],
            "ARCHITECTURE_REFACTOR_QA_MATRIX.md",
            "dedicated fresh-process",
            "serializer spot-check",
            "no longer carries that",
            "benchmark evidence",
        ),
        forbidden=(
            "Only the retained `PROJECT_MANAGED_FILES` packet window",
            "remains a separate persistence follow-up",
            "isolated module-level",
        ),
    ),
    "ARCHITECTURE.md": DocumentRule(
        required=(
            CHECK_TRACEABILITY_SCRIPT,
            CHECK_MARKDOWN_LINKS_SCRIPT,
            CURRENT_CLOSEOUT_QA_MATRIX_DOC,
            PACKAGING_WINDOWS_DOC,
            PILOT_RUNBOOK_DOC,
            "tests/shell_isolation_runtime.py",
        ),
        forbidden=(
            "The P12 closeout sweep",
        ),
    ),
    SPEC_INDEX_DOC: DocumentRule(
        required=(
            "ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md",
            "ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md",
            "PROJECT_MANAGED_FILES_QA_MATRIX.md",
            "PYDPF_VIEWER_V1_QA_MATRIX.md",
            "closeout evidence only",
            "historical pointer",
        ),
        forbidden=(
            "work_packets/pydpf_viewer_v1/PYDPF_VIEWER_V1_MANIFEST.md",
            "work_packets/pydpf_viewer_v1/PYDPF_VIEWER_V1_STATUS.md",
        ),
    ),
    PACKAGING_WINDOWS_DOC: DocumentRule(
        required=(
            ".\\scripts\\build_windows_package.ps1 -PackageProfile base -Clean",
            ".\\scripts\\build_windows_package.ps1 -PackageProfile viewer -Clean -SkipSmoke",
            "artifacts\\pyinstaller\\dist\\base\\COREX_Node_Editor\\",
            "artifacts\\pyinstaller\\dist\\viewer\\COREX_Node_Editor\\",
            ".\\scripts\\build_windows_installer.ps1 -PackageProfile base",
            ".\\scripts\\sign_release_artifacts.ps1 -PackageProfile base -VerifyOnly",
            "artifacts\\releases\\signing\\base\\",
            "tests/test_packaging_configuration.py",
        ),
        forbidden=(
            "RC3",
            "artifacts\\pyinstaller\\dist\\COREX_Node_Editor\\COREX_Node_Editor.exe",
        ),
    ),
    PILOT_RUNBOOK_DOC: DocumentRule(
        required=(
            "build_windows_package.ps1 -PackageProfile base -Clean",
            "build_windows_installer.ps1 -PackageProfile base",
            "artifacts\\pyinstaller\\dist\\base\\COREX_Node_Editor\\COREX_Node_Editor.exe",
            "ARCHITECTURE_REFACTOR_QA_MATRIX.md",
            "PILOT_SIGNOFF.md",
        ),
        forbidden=(
            "RC1",
            "PILOT_BACKLOG.md",
        ),
    ),
    ARCHITECTURE_REFACTOR_QA_MATRIX_DOC: DocumentRule(
        required=(
            "Historical pointer",
            CURRENT_CLOSEOUT_QA_MATRIX_DOC,
        ),
        forbidden=(
            "## 2026-03-27 Execution Results",
            "tests/test_packaging_configuration.py",
        ),
    ),
    QA_ACCEPTANCE_DOC: DocumentRule(
        forbidden=(
            "the four shell-wrapper modules `tests.test_main_window_shell`, "
            "`tests.test_script_editor_dock`, `tests.test_shell_run_controller`, and "
            "`tests.test_shell_project_session_controller` shall remain on explicit "
            "fresh-process `unittest` execution",
            "on separate `unittest` commands after the pytest phases",
        ),
    ),
    GRAPH_SURFACE_INPUT_MATRIX_DOC: DocumentRule(
        required=(
            "## Shell Verification Policy",
            "Both module-level shell wrappers passed directly",
        ),
        forbidden=(
            "wrapper instability (`code 5`)",
            "approved fresh-process fallback completed",
        ),
    ),
    "docs/specs/requirements/80_PERFORMANCE.md": DocumentRule(
        required=(
            "GraphCanvas.qml",
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "steady-state idle appearance returns automatically",
        ),
    ),
    "docs/specs/perf/RC_PACKAGING_REPORT.md": DocumentRule(
        required=(
            "Evidence Status: Archived 2026-03-01 packaging smoke snapshot.",
            "Current release proof lives in `docs/PACKAGING_WINDOWS.md` and "
            "`docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md`.",
            "## Archived 2026-03-01 Snapshot",
        ),
    ),
    "docs/specs/perf/PILOT_SIGNOFF.md": DocumentRule(
        required=(
            "Evidence Status: Archived 2026-03-01 packaged desktop pilot snapshot.",
            "Current pilot proof must be rerun from `docs/PILOT_RUNBOOK.md` and "
            "tracked in `docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md`.",
            "## Archived 2026-03-01 Snapshot",
        ),
    ),
}

QA_ACCEPTANCE_REQUIREMENT_TOKENS = {
    "REQ-QA-014": (RUN_VERIFICATION_SCRIPT, *MODE_NAMES),
    "REQ-QA-015": (SHELL_ISOLATION_SPEC.test_path, *SHELL_ISOLATION_SPEC.shell_module_names),
    "REQ-QA-016": ("pytest-xdist", *XDIST_RESOLUTION_TOKENS),
    "REQ-QA-017": ("baseline failures", "fully green aggregate"),
    "REQ-QA-018": ("GraphCanvas.qml", "interactive desktop/manual follow-up"),
    "REQ-QA-025": (
        CHECK_MARKDOWN_LINKS_SCRIPT,
        PACKAGING_WINDOWS_DOC,
        PILOT_RUNBOOK_DOC,
        SPEC_INDEX_DOC,
        CURRENT_CLOSEOUT_QA_MATRIX_DOC,
    ),
    "AC-REQ-QA-014-01": (
        run_verification_command("full", dry_run=True),
        VERIFICATION_SPEED_MATRIX_DOC,
    ),
    "AC-REQ-QA-015-01": (
        SHELL_ISOLATION_SPEC.test_path,
        *SHELL_ISOLATION_SPEC.shell_module_names,
    ),
    "AC-REQ-QA-016-01": (VERIFICATION_SPEED_MATRIX_DOC,),
    "AC-REQ-QA-018-01": (
        GRAPH_CANVAS_SNAPSHOT_COMMAND,
        proof_audit_command(),
        GRAPH_CANVAS_PERF_MATRIX_DOC,
        TRACK_H_BENCHMARK_REPORT_DOC,
    ),
    "AC-REQ-QA-025-01": (
        DOCS_RELEASE_TRACEABILITY_PYTEST_COMMAND,
        proof_audit_command(),
        f"{LOCAL_VENV_PYTHON_DISPLAY} {CHECK_MARKDOWN_LINKS_SCRIPT}",
        CURRENT_CLOSEOUT_QA_MATRIX_DOC,
    ),
    "REQ-QA-029": (
        "ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md",
        "`P01` through `P07`",
        "`P08`",
        "docs/specs/INDEX.md",
        "manual desktop checks inherited from the packet-set wrap-ups",
    ),
    "AC-REQ-QA-029-01": (
        ARCHITECTURE_RESIDUAL_REFACTOR_TARGETED_REGRESSION_COMMAND,
        ARCHITECTURE_RESIDUAL_REFACTOR_TRACEABILITY_COMMAND,
        ARCHITECTURE_RESIDUAL_REFACTOR_MARKDOWN_COMMAND,
        "ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md",
    ),
}

VERIFICATION_SPEED_FORBIDDEN_TOKENS = (
    "isolated shell-wrapper `unittest` phase",
    "adds `-n auto` only when `pytest-xdist` is importable in the project venv",
)
VERIFICATION_SPEED_WORKFLOW_NOTE_TOKENS = {
    "fast": (
        "pytest-xdist",
        XDIST_RESOLUTION_TOKENS[0],
        "not gui and not slow",
        SHELL_ISOLATION_SPEC.test_path,
    ),
    "gui": (
        "pytest-xdist",
        XDIST_RESOLUTION_TOKENS[0],
        str(MAX_GUI_PARALLEL_WORKERS),
        SHELL_ISOLATION_SPEC.test_path,
    ),
    "slow": ("Serial", SHELL_ISOLATION_SPEC.test_path),
    "full": ("--dry-run",),
}
VERIFICATION_SPEED_SHELL_RULE_TOKENS = (
    *non_shell_pytest_ignore_args(),
    shell_isolation_pytest_command(),
    *XDIST_RESOLUTION_TOKENS,
    *shell_direct_unittest_commands(),
)
VERIFICATION_SPEED_ENVIRONMENT_NOTE_TOKENS = (
    LOCAL_VENV_PYTHON_DISPLAY,
    "pytest-xdist",
    XDIST_RESOLUTION_TOKENS[0],
    str(MAX_GUI_PARALLEL_WORKERS),
)
VERIFICATION_SPEED_COMPANION_PROOF_TOKENS = (
    proof_audit_command(),
    CHECK_TRACEABILITY_SCRIPT,
)
VERIFICATION_SPEED_BASELINE_REQUIRED_TOKENS = (
    SERIALIZER_BASELINE_COMMAND,
    "retired",
    "No known out-of-scope verification baseline failures remain",
)
VERIFICATION_SPEED_BASELINE_FORBIDDEN_TOKENS = (
    "serializer baseline remains open",
    "still fails because passive image-panel round-trips add default crop fields",
)
VERIFICATION_SPEED_RESULT_COMMANDS = (
    run_verification_command("full", dry_run=True),
    SERIALIZER_BASELINE_COMMAND,
)
VERIFICATION_SPEED_SHELL_RESULT_COMMAND_PREFIX = shell_isolation_pytest_command(
    worker_count=None
)
VERIFICATION_SPEED_SHELL_RESULT_REQUIRED_TOKENS = ("--dist load",)

GRAPH_CANVAS_PERF_REQUIRED_TOKENS = (
    "## Locked Benchmark Contract",
    "GraphCanvas.qml",
    "## Desktop/Manual Follow-Up",
    "desktop/manual",
    "outstanding",
)
GRAPH_CANVAS_PERF_AUDIT_COMMANDS = (
    TRACK_H_REGRESSION_COMMAND,
    GRAPH_CANVAS_SNAPSHOT_COMMAND,
    proof_audit_command(),
)

TRACK_H_REPORT_REQUIRED_TOKENS = (
    "GraphCanvas.qml",
    "offscreen regression snapshot",
    "`P04`",
    GRAPH_CANVAS_SNAPSHOT_COMMAND,
    TRACK_H_BENCHMARK_ARTIFACT,
    "## 2026-03-18 Offscreen Snapshot",
    "Interactive desktop/GPU validation remains required",
    GRAPH_CANVAS_PERF_MATRIX_DOC,
)
TRACK_H_REPORT_FORBIDDEN_TOKENS = (
    "Historical offscreen harness baseline restored from repo",
    "P08 did not rerun the performance harness.",
)


TRACEABILITY_ROW_REQUIRED_TOKENS = {
    "REQ-PERF-001": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "GraphCanvas.qml",
    ),
    "REQ-PERF-002": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "GraphCanvas.qml",
    ),
    "REQ-PERF-003": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "load",
    ),
    "AC-REQ-QA-001-02": (
        "RC_PACKAGING_REPORT.md",
        "archived `2026-03-01` build/smoke summary",
    ),
    "AC-REQ-QA-001-03": (
        "PILOT_SIGNOFF.md",
        "archived `2026-03-01` run",
    ),
    "REQ-QA-013": (
        CHECK_TRACEABILITY_SCRIPT,
        "tests/test_traceability_checker.py",
        "GRAPH_SURFACE_INPUT_QA_MATRIX.md",
    ),
    "REQ-QA-014": (
        CHECK_TRACEABILITY_SCRIPT,
        "tests/test_traceability_checker.py",
        "VERIFICATION_SPEED_QA_MATRIX.md",
    ),
    "REQ-QA-015": (
        SHELL_ISOLATION_PHASE_TEST,
        *SHELL_ISOLATION_TARGET_CATALOG_PATHS,
        "README.md",
        "docs/GETTING_STARTED.md",
        "VERIFICATION_SPEED_QA_MATRIX.md",
    ),
    "REQ-QA-016": (
        *XDIST_RESOLUTION_TOKENS[:2],
        "README.md",
        "docs/GETTING_STARTED.md",
        "VERIFICATION_SPEED_QA_MATRIX.md",
    ),
    "REQ-QA-017": (
        "VERIFICATION_SPEED_QA_MATRIX.md",
        CHECK_TRACEABILITY_SCRIPT,
        "tests/test_traceability_checker.py",
    ),
    "REQ-QA-018": (
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "TRACK_H_BENCHMARK_REPORT.md",
        CHECK_TRACEABILITY_SCRIPT,
    ),
    "AC-REQ-UI-023-01": (
        "GRAPH_SURFACE_INPUT_QA_MATRIX.md",
        CHECK_TRACEABILITY_SCRIPT,
        "tests/test_traceability_checker.py",
    ),
    "AC-REQ-QA-013-01": (
        "GRAPH_SURFACE_INPUT_QA_MATRIX.md",
        CHECK_TRACEABILITY_SCRIPT,
        "tests/test_traceability_checker.py",
    ),
    "AC-REQ-QA-014-01": (
        run_verification_command("full", dry_run=True),
        RUN_VERIFICATION_SCRIPT,
        CHECK_TRACEABILITY_SCRIPT,
        "tests/test_traceability_checker.py",
        "VERIFICATION_SPEED_QA_MATRIX.md",
    ),
    "AC-REQ-QA-015-01": (
        run_verification_command("full", dry_run=True),
        RUN_VERIFICATION_SCRIPT,
        SHELL_ISOLATION_PHASE_TEST,
        "README.md",
        "docs/GETTING_STARTED.md",
    ),
    "AC-REQ-QA-016-01": (
        RUN_VERIFICATION_SCRIPT,
        CHECK_TRACEABILITY_SCRIPT,
        "tests/test_traceability_checker.py",
        "README.md",
        "docs/GETTING_STARTED.md",
        "VERIFICATION_SPEED_QA_MATRIX.md",
    ),
    "AC-REQ-QA-017-01": (
        "VERIFICATION_SPEED_QA_MATRIX.md",
        CHECK_TRACEABILITY_SCRIPT,
        "tests/test_traceability_checker.py",
    ),
    "REQ-QA-025": (
        CHECK_TRACEABILITY_SCRIPT,
        CHECK_MARKDOWN_LINKS_SCRIPT,
        PACKAGING_WINDOWS_DOC,
        PILOT_RUNBOOK_DOC,
        SPEC_INDEX_DOC,
        CURRENT_CLOSEOUT_QA_MATRIX_DOC,
        "tests/test_shell_isolation_phase.py",
        MARKDOWN_HYGIENE_TEST,
    ),
    "AC-REQ-PERF-002-01": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "tests/test_track_h_perf_harness.py",
        "2026-03-18",
    ),
    "AC-REQ-PERF-003-01": (
        "TRACK_H_BENCHMARK_REPORT.md",
        GRAPH_CANVAS_REPORT_DIR,
    ),
    "AC-REQ-PERF-002-02": (
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "TRACK_H_BENCHMARK_REPORT.md",
    ),
    "AC-REQ-QA-018-01": (
        GRAPH_CANVAS_REPORT_DIR,
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "TRACK_H_BENCHMARK_REPORT.md",
        CHECK_TRACEABILITY_SCRIPT,
    ),
    "AC-REQ-QA-025-01": (
        DOCS_RELEASE_TRACEABILITY_PYTEST_COMMAND,
        proof_audit_command(),
        f"{LOCAL_VENV_PYTHON_DISPLAY} {CHECK_MARKDOWN_LINKS_SCRIPT}",
        CURRENT_CLOSEOUT_QA_MATRIX_DOC,
    ),
    "REQ-QA-029": (
        "docs/specs/INDEX.md",
        "docs/specs/requirements/90_QA_ACCEPTANCE.md",
        "docs/specs/requirements/TRACEABILITY_MATRIX.md",
        ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC,
        "scripts/verification_manifest.py",
        "scripts/check_traceability.py",
        "tests/test_architecture_boundaries.py",
        "tests/test_shell_isolation_phase.py",
        "tests/test_markdown_hygiene.py",
        "tests/test_traceability_checker.py",
        "tests/shell_isolation_main_window_targets.py",
        "tests/shell_isolation_controller_targets.py",
    ),
    "AC-REQ-QA-029-01": (
        ARCHITECTURE_RESIDUAL_REFACTOR_TARGETED_REGRESSION_COMMAND,
        ARCHITECTURE_RESIDUAL_REFACTOR_TRACEABILITY_COMMAND,
        ARCHITECTURE_RESIDUAL_REFACTOR_MARKDOWN_COMMAND,
        "ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md",
    ),
}

TRACEABILITY_ROW_FORBIDDEN_TOKENS = {
    "AC-REQ-QA-013-01": ("approved fresh-process shell fallback",),
    "AC-REQ-QA-017-01": ("Recorded serializer baseline caveat",),
}

ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_REQUIRED_TOKENS = (
    "Architecture Residual Refactor QA Matrix",
    "## Locked Scope",
    "## Retained Automated Verification",
    "## Final Closeout Commands",
    "## 2026-04-04 Execution Results",
    "## Remaining Manual Desktop Checks",
    "## Residual Risks",
    "docs/specs/INDEX.md",
    "docs/specs/requirements/90_QA_ACCEPTANCE.md",
    "docs/specs/requirements/TRACEABILITY_MATRIX.md",
    "scripts/verification_manifest.py",
    "scripts/check_traceability.py",
    "tests/test_architecture_boundaries.py",
    "tests/test_shell_isolation_phase.py",
    "tests/test_traceability_checker.py",
    MARKDOWN_HYGIENE_TEST,
    CURRENT_CLOSEOUT_QA_MATRIX_DOC,
    ARCHITECTURE_RESIDUAL_REFACTOR_TARGETED_REGRESSION_COMMAND,
    ARCHITECTURE_RESIDUAL_REFACTOR_TRACEABILITY_COMMAND,
    ARCHITECTURE_RESIDUAL_REFACTOR_MARKDOWN_COMMAND,
    *ARCHITECTURE_RESIDUAL_REFACTOR_PACKET_WRAPUPS,
)
ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_AUDIT_COMMANDS = (
    ARCHITECTURE_RESIDUAL_REFACTOR_TARGETED_REGRESSION_COMMAND,
    ARCHITECTURE_RESIDUAL_REFACTOR_TRACEABILITY_COMMAND,
    ARCHITECTURE_RESIDUAL_REFACTOR_MARKDOWN_COMMAND,
)
