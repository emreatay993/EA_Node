"""Canonical verification workflow facts for runner, tests, and proof audits."""

from __future__ import annotations

from dataclasses import dataclass

LOCAL_VENV_PYTHON_DISPLAY = "./venv/Scripts/python.exe"
RUN_VERIFICATION_SCRIPT = "scripts/run_verification.py"
CHECK_TRACEABILITY_SCRIPT = "scripts/check_traceability.py"
OFFSCREEN_ENV = {"QT_QPA_PLATFORM": "offscreen"}

MODE_NAMES = ("fast", "gui", "slow", "full")
MAX_GUI_PARALLEL_WORKERS = 6

QA_ACCEPTANCE_DOC = "docs/specs/requirements/90_QA_ACCEPTANCE.md"
TRACEABILITY_MATRIX_DOC = "docs/specs/requirements/TRACEABILITY_MATRIX.md"
VERIFICATION_SPEED_MATRIX_DOC = "docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md"
GRAPH_CANVAS_PERF_MATRIX_DOC = "docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md"
TRACK_H_BENCHMARK_REPORT_DOC = "docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md"
GRAPH_SURFACE_INPUT_MATRIX_DOC = "docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md"

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
SHELL_ISOLATION_TARGET_CATALOG_PATHS = (
    "tests/shell_isolation_main_window_targets.py",
    "tests/shell_isolation_controller_targets.py",
)
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
    "tests/test_shell_theme.py",
    "tests/test_workflow_settings_dialog.py",
)
SLOW_TEST_PATHS = ("tests/test_track_h_perf_harness.py",)

XDIST_RESOLUTION_TOKENS = (
    "psutil.cpu_count(logical=True)",
    "os.cpu_count()",
    "1",
)

PROOF_AUDIT_REQUIRED_ARTIFACTS = (
    "README.md",
    "docs/GETTING_STARTED.md",
    "docs/specs/requirements/80_PERFORMANCE.md",
    QA_ACCEPTANCE_DOC,
    TRACEABILITY_MATRIX_DOC,
    GRAPH_CANVAS_PERF_MATRIX_DOC,
    "docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md",
    GRAPH_SURFACE_INPUT_MATRIX_DOC,
    VERIFICATION_SPEED_MATRIX_DOC,
    TRACK_H_BENCHMARK_REPORT_DOC,
    "docs/specs/perf/RC_PACKAGING_REPORT.md",
    "docs/specs/perf/PILOT_SIGNOFF.md",
    "scripts/run_verification.py",
    "scripts/verification_manifest.py",
    "scripts/check_traceability.py",
    "tests/conftest.py",
    "tests/test_run_verification.py",
    "tests/test_traceability_checker.py",
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

SHELL_ISOLATION_SPEC = ShellIsolationSpec(
    phase="full.shell_isolation.pytest",
    test_path=SHELL_ISOLATION_PHASE_TEST,
    target_catalog_paths=SHELL_ISOLATION_TARGET_CATALOG_PATHS,
    shell_module_paths=SHELL_BACKED_TEST_PATHS,
    shell_module_names=SHELL_BACKED_TEST_MODULES,
)


def run_verification_command(mode: str, *, dry_run: bool = False) -> str:
    """Return the documented developer-facing verification command."""

    argv = [LOCAL_VENV_PYTHON_DISPLAY, RUN_VERIFICATION_SCRIPT, "--mode", mode]
    if dry_run:
        argv.append("--dry-run")
    return " ".join(argv)


def shell_isolation_pytest_command(worker_count: int | str | None = "<resolved_count>") -> str:
    """Return the documented dedicated shell-isolation pytest command."""

    argv = [
        "QT_QPA_PLATFORM=offscreen",
        LOCAL_VENV_PYTHON_DISPLAY,
        "-m",
        "pytest",
        SHELL_ISOLATION_PHASE_TEST,
        "-q",
    ]
    if worker_count is not None:
        argv.extend(["-n", str(worker_count), "--dist", "load"])
    return " ".join(argv)


def shell_direct_unittest_commands() -> tuple[str, ...]:
    """Return the focused module-level shell rerun commands."""

    return tuple(
        f"QT_QPA_PLATFORM=offscreen {LOCAL_VENV_PYTHON_DISPLAY} -m unittest {module_name} -v"
        for module_name in SHELL_BACKED_TEST_MODULES
    )


def proof_audit_command() -> str:
    """Return the canonical proof-audit command."""

    return f"{LOCAL_VENV_PYTHON_DISPLAY} {CHECK_TRACEABILITY_SCRIPT}"


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
}

TRACEABILITY_ROW_FORBIDDEN_TOKENS = {
    "AC-REQ-QA-013-01": ("approved fresh-process shell fallback",),
    "AC-REQ-QA-017-01": ("Recorded serializer baseline caveat",),
}
