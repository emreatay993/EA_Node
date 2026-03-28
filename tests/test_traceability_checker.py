from __future__ import annotations

import importlib.util
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = REPO_ROOT / "scripts" / "check_traceability.py"
VERIFICATION_MANIFEST_PATH = REPO_ROOT / "scripts" / "verification_manifest.py"
PROJECT_MANAGED_FILES_QA_MATRIX = REPO_ROOT / "docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md"
PROJECT_MANAGED_FILES_FINAL_REGRESSION_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py "
    "tests/test_pdf_preview_provider.py tests/test_project_save_as_flow.py "
    "tests/test_app_preferences_import_defaults.py tests/test_project_file_issues.py "
    "tests/test_project_files_dialog.py tests/test_execution_artifact_refs.py "
    "tests/test_integrations_track_f.py tests/test_process_run_node.py "
    "tests/test_graph_output_mode_ui.py tests/test_shell_project_session_controller.py "
    "--ignore=venv -q"
)
PROJECT_MANAGED_FILES_TRACEABILITY_COMMAND = "./venv/Scripts/python.exe scripts/check_traceability.py"

PROJECT_MANAGED_FILES_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/10_ARCHITECTURE.md": {
        "REQ-ARCH-014": (".sfe", "<project-stem>.data/", "assets/", "artifacts/", ".staging"),
        "REQ-ARCH-015": ("metadata.artifact_store", "artifact://<artifact_id>", "artifact-stage://<artifact_id>"),
    },
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-028": ("Project Files...", "staged", "broken"),
        "REQ-UI-029": ("Save As", "self-contained copy", "staged scratch"),
        "REQ-UI-030": ("managed_copy", "external_link", "File Read", "Excel Read"),
        "REQ-UI-031": ("Process Run", "memory", "stored", "status chip"),
    },
    "docs/specs/requirements/40_NODE_SDK.md": {
        "REQ-NODE-022": ("RuntimeArtifactRef", "ExecutionContext.resolve_path_value()", "runtime_artifact_ref()"),
    },
    "docs/specs/requirements/45_NODE_EXECUTION_MODEL.md": {
        "REQ-NODE-023": ("RuntimeArtifactRef", "same run", "runtime-snapshot"),
        "REQ-NODE-024": ("io.process_run", "memory", "stored", "automatic size-based switching"),
    },
    "docs/specs/requirements/50_EXECUTION_ENGINE.md": {
        "REQ-EXEC-010": ("RuntimeArtifactRef", "artifact_ref", "artifact://...", "artifact-stage://..."),
        "REQ-EXEC-011": ("runtime-snapshot", "project artifact metadata", "same run"),
        "REQ-EXEC-012": ("Process Run", "staged refs", "non-zero failure or cancellation"),
    },
    "docs/specs/requirements/60_PERSISTENCE.md": {
        "REQ-PERSIST-015": (".sfe", "<project-stem>.data/", "assets/", "artifacts/", ".staging"),
        "REQ-PERSIST-016": ("metadata.artifact_store", "artifact://<artifact_id>", "artifact-stage://<artifact_id>"),
        "REQ-PERSIST-017": ("stage first", "Save", "prune orphaned permanent managed files"),
        "REQ-PERSIST-018": ("Save As", "self-contained copy", "excluding staged scratch data"),
        "REQ-PERSIST-019": ("crash-only", "clean close", "autosave snapshot"),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-021": ("PROJECT_MANAGED_FILES", "runtime artifact refs", "Process Run", "full artifact manager"),
        "REQ-QA-022": ("PROJECT_MANAGED_FILES_QA_MATRIX.md", "final aggregate regression command", "traceability gate"),
        "AC-REQ-QA-021-01": (PROJECT_MANAGED_FILES_FINAL_REGRESSION_COMMAND,),
        "AC-REQ-QA-022-01": (PROJECT_MANAGED_FILES_TRACEABILITY_COMMAND, "PROJECT_MANAGED_FILES_QA_MATRIX.md"),
    },
}

PROJECT_MANAGED_FILES_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-ARCH-014": ("artifact_store.py", "test_project_artifact_store.py", "round_trip_cases.py"),
    "REQ-UI-028": ("project_files_dialog.py", "test_project_files_dialog.py", "test_shell_project_session_controller.py"),
    "REQ-NODE-022": ("Runtime artifact-ref SDK helpers", "test_execution_artifact_refs.py"),
    "REQ-NODE-023": ("Stored-output runtime artifact refs", "test_integrations_track_f.py"),
    "REQ-EXEC-010": ("protocol.py", "test_execution_artifact_refs.py", "test_execution_client.py"),
    "REQ-PERSIST-015": ("Canonical `.sfe` plus sibling `.data` layout", "test_project_artifact_store.py"),
    "REQ-QA-021": ("PROJECT_MANAGED_FILES_QA_MATRIX.md", "test_graph_output_mode_ui.py", "test_shell_project_session_controller.py"),
    "AC-REQ-QA-021-01": (PROJECT_MANAGED_FILES_FINAL_REGRESSION_COMMAND, "PROJECT_MANAGED_FILES_QA_MATRIX.md"),
    "AC-REQ-QA-022-01": (PROJECT_MANAGED_FILES_TRACEABILITY_COMMAND, "tests/test_traceability_checker.py"),
}

PROJECT_MANAGED_FILES_QA_MATRIX_TOKENS = (
    "Project Managed Files QA Matrix",
    "## Locked Scope",
    "artifact://<artifact_id>",
    "artifact-stage://<artifact_id>",
    PROJECT_MANAGED_FILES_FINAL_REGRESSION_COMMAND,
    PROJECT_MANAGED_FILES_TRACEABILITY_COMMAND,
    "## Future-Scope Deferrals",
    "no full artifact-manager pane",
    "Process Run",
)

PYDPF_VIEWER_V1_QA_MATRIX = REPO_ROOT / "docs/specs/perf/PYDPF_VIEWER_V1_QA_MATRIX.md"
PYDPF_VIEWER_V1_FINAL_REGRESSION_COMMAND = (
    "./venv/Scripts/python.exe -m pytest "
    "tests/test_dpf_viewer_node.py tests/test_dpf_node_catalog.py "
    "tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py "
    "tests/test_packaging_configuration.py tests/test_traceability_checker.py "
    "--ignore=venv -q"
)
PYDPF_VIEWER_V1_TRACEABILITY_COMMAND = "./venv/Scripts/python.exe scripts/check_traceability.py"
PYDPF_VIEWER_V1_TRACEABILITY_TEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)

PYDPF_VIEWER_V1_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/10_ARCHITECTURE.md": {
        "REQ-ARCH-016": (
            "RuntimeHandleRef",
            "DpfRuntimeService",
            "ViewerSessionBridge",
            "EmbeddedViewerOverlayManager",
        ),
    },
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-032": ("dpf.viewer", "viewerSessionBridge", "focus_only", "keep_live"),
    },
    "docs/specs/requirements/40_NODE_SDK.md": {
        "REQ-NODE-025": ("dpf.viewer", 'surface_family="viewer"', "output_mode", "viewer_live_policy"),
    },
    "docs/specs/requirements/45_NODE_EXECUTION_MODEL.md": {
        "REQ-NODE-026": ("session-owned", "proxy", "live", "worker viewer session service"),
    },
    "docs/specs/requirements/50_EXECUTION_ENGINE.md": {
        "REQ-EXEC-013": ("viewer-session", "runtime handle refs", "typed viewer protocol", "worker-local"),
    },
    "docs/specs/requirements/60_PERSISTENCE.md": {
        "REQ-PERSIST-020": ("tests/ansys_dpf_core/example_outputs/", ".rst", ".rth", "serialized project artifacts"),
    },
    "docs/specs/requirements/70_INTEGRATIONS.md": {
        "REQ-INT-008": (
            "ansys-dpf-core",
            "pyvista",
            "pyvistaqt",
            "vtk",
            "dpf.result_file",
            "dpf.mesh_extract",
            "dpf.viewer",
        ),
    },
    "docs/specs/requirements/80_PERFORMANCE.md": {
        "REQ-PERF-008": ("PYDPF_VIEWER_V1_QA_MATRIX.md", "large-model", "Windows packaged-build", ".rst"),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-023": ("PYDPF_VIEWER_V1", "dpf.viewer", "packaging configuration", "traceability"),
        "REQ-QA-024": ("PYDPF_VIEWER_V1_QA_MATRIX.md", ".rst", ".rth", "traceability gate"),
        "AC-REQ-QA-023-01": (PYDPF_VIEWER_V1_FINAL_REGRESSION_COMMAND, "PYDPF_VIEWER_V1_QA_MATRIX.md"),
        "AC-REQ-QA-024-01": (
            PYDPF_VIEWER_V1_TRACEABILITY_COMMAND,
            PYDPF_VIEWER_V1_TRACEABILITY_TEST_COMMAND,
            "PYDPF_VIEWER_V1_QA_MATRIX.md",
        ),
    },
}

PYDPF_VIEWER_V1_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-ARCH-016": ("runtime_value_codec.py", "viewer_session_service.py", "viewer_session_bridge.py"),
    "REQ-NODE-025": ("ansys_dpf.py", "ansys_dpf_common.py", "test_dpf_viewer_node.py"),
    "REQ-INT-008": ("pyproject.toml", "ea_node_editor.spec", "test_packaging_configuration.py"),
    "REQ-QA-024": ("PYDPF_VIEWER_V1_QA_MATRIX.md", "tests/test_traceability_checker.py", "scripts/check_traceability.py"),
    "AC-REQ-QA-023-01": (PYDPF_VIEWER_V1_FINAL_REGRESSION_COMMAND, "PYDPF_VIEWER_V1_QA_MATRIX.md"),
    "AC-REQ-QA-024-01": (
        PYDPF_VIEWER_V1_TRACEABILITY_COMMAND,
        PYDPF_VIEWER_V1_TRACEABILITY_TEST_COMMAND,
    ),
}

PYDPF_VIEWER_V1_QA_MATRIX_TOKENS = (
    "PYDPF Viewer V1 QA Matrix",
    "## Locked Scope",
    "dpf.viewer",
    "tests/ansys_dpf_core/fixture_paths.py",
    "static_analysis_1_bolted_joint/file.rst",
    "modal_analysis_1_bolted_joint/file.rst",
    "steady_state_thermal_analysis_1_bolted_joint/file.rth",
    PYDPF_VIEWER_V1_FINAL_REGRESSION_COMMAND,
    PYDPF_VIEWER_V1_TRACEABILITY_COMMAND,
    PYDPF_VIEWER_V1_TRACEABILITY_TEST_COMMAND,
    ".\\scripts\\build_windows_package.ps1 -PackageProfile viewer -Clean -SkipSmoke",
    "## Remaining Manual Smoke Checks",
    "## Future-Scope Deferrals",
)
ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md"
)
ARCHITECTURE_MAINTAINABILITY_REFACTOR_FINAL_REGRESSION_COMMAND = (
    "./venv/Scripts/python.exe -m pytest "
    "tests/test_dead_code_hygiene.py tests/test_run_verification.py "
    "tests/test_traceability_checker.py tests/test_markdown_hygiene.py "
    "tests/test_shell_isolation_phase.py --ignore=venv -q"
)
ARCHITECTURE_MAINTAINABILITY_REFACTOR_TRACEABILITY_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_traceability.py"
)
ARCHITECTURE_MAINTAINABILITY_REFACTOR_MARKDOWN_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_markdown_links.py"
)

ARCHITECTURE_MAINTAINABILITY_REFACTOR_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-025": (
            "scripts/check_markdown_links.py",
            "docs/PACKAGING_WINDOWS.md",
            "docs/PILOT_RUNBOOK.md",
            "docs/specs/INDEX.md",
            "ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md",
        ),
        "AC-REQ-QA-025-01": (
            ARCHITECTURE_MAINTAINABILITY_REFACTOR_FINAL_REGRESSION_COMMAND,
            ARCHITECTURE_MAINTAINABILITY_REFACTOR_TRACEABILITY_COMMAND,
            ARCHITECTURE_MAINTAINABILITY_REFACTOR_MARKDOWN_COMMAND,
            "ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md",
        ),
    },
}

ARCHITECTURE_MAINTAINABILITY_REFACTOR_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-QA-025": (
        "ARCHITECTURE.md",
        "docs/PACKAGING_WINDOWS.md",
        "docs/PILOT_RUNBOOK.md",
        "docs/specs/INDEX.md",
        "ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md",
        "scripts/check_markdown_links.py",
        "tests/test_shell_isolation_phase.py",
        "tests/test_markdown_hygiene.py",
    ),
    "AC-REQ-QA-025-01": (
        ARCHITECTURE_MAINTAINABILITY_REFACTOR_FINAL_REGRESSION_COMMAND,
        ARCHITECTURE_MAINTAINABILITY_REFACTOR_TRACEABILITY_COMMAND,
        ARCHITECTURE_MAINTAINABILITY_REFACTOR_MARKDOWN_COMMAND,
        "ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md",
    ),
}

ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX_TOKENS = (
    "Architecture Maintainability Refactor QA Matrix",
    "## Locked Scope",
    "## Shell Isolation Contract",
    ARCHITECTURE_MAINTAINABILITY_REFACTOR_FINAL_REGRESSION_COMMAND,
    ARCHITECTURE_MAINTAINABILITY_REFACTOR_TRACEABILITY_COMMAND,
    ARCHITECTURE_MAINTAINABILITY_REFACTOR_MARKDOWN_COMMAND,
    "docs/PACKAGING_WINDOWS.md",
    "docs/PILOT_RUNBOOK.md",
    "ARCHITECTURE_REFACTOR_QA_MATRIX.md",
    "RC_PACKAGING_REPORT.md",
    "PILOT_SIGNOFF.md",
    "tests/shell_isolation_runtime.py",
    "tests/shell_isolation_main_window_targets.py",
    "tests/shell_isolation_controller_targets.py",
    "tests/test_markdown_hygiene.py",
    "## Remaining Manual and Windows-Only Checks",
    "## Historical References",
)


def load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def replace_text(path: Path, old: str, new: str) -> None:
    path.write_text(path.read_text(encoding="utf-8-sig").replace(old, new), encoding="utf-8")


def update_markdown_table_result(path: Path, command: str, new_result: str, new_notes: str | None = None) -> None:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    command_cell = f"`{command}`"
    for index, line in enumerate(lines):
        if not line.startswith(f"| {command_cell} |"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        cells[1] = new_result
        if new_notes is not None and len(cells) > 2:
            cells[2] = new_notes
        lines[index] = "| " + " | ".join(cells) + " |"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    raise AssertionError(f"Command row not found: {command}")


def remove_token_from_traceability_row(path: Path, row_id: str, token: str) -> None:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"| {row_id} |"):
            continue
        lines[index] = line.replace(token, "").replace(", ,", ",")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    raise AssertionError(f"Traceability row not found: {row_id}")


def remove_token_from_requirement_line(path: Path, requirement_id: str, token: str) -> None:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"- `{requirement_id}`:"):
            continue
        lines[index] = line.replace(token, "").replace("  ", " ")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    raise AssertionError(f"Requirement line not found: {requirement_id}")


def parse_requirement_lines(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^- `([^`]+)`: (.+)$", line.strip())
        if match is not None:
            parsed[match.group(1)] = match.group(2)
    return parsed


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    table_lines = [line for line in text.splitlines() if line.startswith("|")]
    if len(table_lines) < 2:
        raise AssertionError("Markdown table not found.")
    headers = [cell.strip() for cell in table_lines[0].strip().strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def requirement_line(path: Path, requirement_id: str) -> str:
    requirements = parse_requirement_lines(path.read_text(encoding="utf-8-sig"))
    body = requirements.get(requirement_id)
    if body is None:
        raise AssertionError(f"Requirement line not found: {requirement_id}")
    return body


def traceability_row(path: Path, row_id: str) -> str:
    rows = parse_markdown_table(path.read_text(encoding="utf-8-sig"))
    for row in rows:
        if row.get("Requirement ID") == row_id:
            return row.get("Implementation Artifact", "")
    raise AssertionError(f"Traceability row not found: {row_id}")


class TraceabilityCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_module("verification_manifest_for_traceability_tests", VERIFICATION_MANIFEST_PATH)
        cls.checker = load_module("check_traceability_for_tests", CHECKER_PATH)

    def test_checker_uses_manifest_owned_audit_catalogs(self) -> None:
        self.assertEqual(self.manifest.PROOF_AUDIT_REQUIRED_ARTIFACTS, self.checker.REQUIRED_ARTIFACTS)
        manifest_rules = {
            path: (rule.required, rule.forbidden)
            for path, rule in self.manifest.GENERIC_DOCUMENT_RULES.items()
        }
        checker_rules = {
            path: (rule.required, rule.forbidden)
            for path, rule in self.checker.GENERIC_DOCUMENT_RULES.items()
        }
        self.assertEqual(manifest_rules, checker_rules)

    def make_repo_fixture(self, root: Path) -> None:
        required_paths = set(self.checker.REQUIRED_ARTIFACTS) | set(
            self.checker.P10_REQUIRED_GENERATED_ARTIFACTS
        )
        required_paths.update(self.checker.P10_REQUIREMENT_DOC_TOKENS.keys())
        for relative_path in required_paths:
            source = REPO_ROOT / relative_path
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def test_audit_repository_passes_for_current_repo(self) -> None:
        self.assertEqual([], self.checker.audit_repository(REPO_ROOT))

    def test_audit_repository_reports_missing_required_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            (repo_root / self.manifest.GRAPH_CANVAS_PERF_MATRIX_DOC).unlink()

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            f"Missing required artifact: {self.manifest.GRAPH_CANVAS_PERF_MATRIX_DOC}",
            issues,
        )

    def test_audit_repository_reports_missing_generated_graphics_modes_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            (repo_root / self.checker.GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON).unlink()

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "Missing required generated artifact: "
            f"{self.checker.GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON}",
            issues,
        )

    def test_audit_repository_reports_structured_perf_and_row_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            graph_canvas_doc = repo_root / self.manifest.GRAPH_CANVAS_PERF_MATRIX_DOC
            update_markdown_table_result(
                graph_canvas_doc,
                self.checker.GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND,
                "Pending",
                "Mode-aware heavy-media snapshot was not rerun",
            )
            replace_text(graph_canvas_doc, "Status: `PASS`", "Status: `PENDING`")

            track_h_doc = repo_root / self.manifest.TRACK_H_BENCHMARK_REPORT_DOC
            replace_text(track_h_doc, "Scenario: `heavy_media`", "Scenario: `synthetic_exec`")
            replace_text(
                track_h_doc,
                "artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json",
                "artifacts/graphics_performance_modes_docs/report.json",
            )
            replace_text(
                track_h_doc,
                "artifacts/graph_canvas_interaction_perf_p09_desktop_reference/track_h_benchmark_report.json",
                "artifacts/graph_canvas_interaction_perf_p09_desktop_reference/report.json",
            )

            traceability_matrix = repo_root / self.manifest.TRACEABILITY_MATRIX_DOC
            remove_token_from_traceability_row(
                traceability_matrix,
                "AC-REQ-QA-018-01",
                "artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            f"{self.manifest.GRAPH_CANVAS_PERF_MATRIX_DOC}: 2026-03-21 Execution Results command "
            f"{self.checker.GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND} has unexpected result: Pending",
            issues,
        )
        self.assertIn(
            f"{self.manifest.GRAPH_CANVAS_PERF_MATRIX_DOC}: graph-canvas perf matrix missing fact: "
            "Status: `PASS`",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACK_H_BENCHMARK_REPORT_DOC}: track-h benchmark report missing fact: "
            "Scenario: `heavy_media`",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACK_H_BENCHMARK_REPORT_DOC}: track-h benchmark report missing fact: "
            f"{self.checker.GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON}",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACK_H_BENCHMARK_REPORT_DOC}: track-h benchmark report missing fact: "
            "artifacts/graph_canvas_interaction_perf_p09_desktop_reference/track_h_benchmark_report.json",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACEABILITY_MATRIX_DOC}: row AC-REQ-QA-018-01 missing implementation "
            "artifact text: artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json",
            issues,
        )

    def test_audit_repository_reports_graphics_performance_modes_requirement_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            remove_token_from_requirement_line(
                repo_root / "docs/specs/requirements/20_UI_UX.md",
                "REQ-UI-024",
                "same persisted preference",
            )
            remove_token_from_requirement_line(
                repo_root / "docs/specs/requirements/40_NODE_SDK.md",
                "REQ-NODE-016",
                "render_quality",
            )
            remove_token_from_requirement_line(
                repo_root / "docs/specs/requirements/60_PERSISTENCE.md",
                "REQ-PERSIST-011",
                "graphics performance mode",
            )
            remove_token_from_requirement_line(
                repo_root / "docs/specs/requirements/80_PERFORMANCE.md",
                "REQ-PERF-006",
                "proxy-surface",
            )
            remove_token_from_requirement_line(
                repo_root / self.manifest.QA_ACCEPTANCE_DOC,
                "REQ-QA-018",
                "performance_mode",
            )

            traceability_matrix = repo_root / self.manifest.TRACEABILITY_MATRIX_DOC
            remove_token_from_traceability_row(
                traceability_matrix,
                "REQ-UI-024",
                "ShellStatusStrip.qml",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "docs/specs/requirements/20_UI_UX.md: requirement REQ-UI-024 missing fact: "
            "same persisted preference",
            issues,
        )
        self.assertIn(
            "docs/specs/requirements/40_NODE_SDK.md: requirement REQ-NODE-016 missing fact: "
            "render_quality",
            issues,
        )
        self.assertIn(
            "docs/specs/requirements/60_PERSISTENCE.md: requirement REQ-PERSIST-011 missing fact: "
            "graphics performance mode",
            issues,
        )
        self.assertIn(
            "docs/specs/requirements/80_PERFORMANCE.md: requirement REQ-PERF-006 missing fact: "
            "proxy-surface",
            issues,
        )
        self.assertIn(
            f"{self.manifest.QA_ACCEPTANCE_DOC}: requirement REQ-QA-018 missing fact: performance_mode",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACEABILITY_MATRIX_DOC}: row REQ-UI-024 missing implementation "
            "artifact text: ShellStatusStrip.qml",
            issues,
        )

    def test_audit_repository_reports_shell_phase_doc_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            readme_path = repo_root / "README.md"
            replace_text(
                readme_path,
                "dedicated fresh-process shell-isolation phase",
                "shell-wrapper suites for isolated `unittest` execution",
            )

            qa_path = repo_root / self.manifest.QA_ACCEPTANCE_DOC
            replace_text(
                qa_path,
                self.manifest.SHELL_ISOLATION_SPEC.test_path,
                "tests/test_shell_wrapper_phase.py",
            )
            qa_path.write_text(
                qa_path.read_text(encoding="utf-8-sig")
                + "\n"
                + "`REQ-QA-015`: the four shell-wrapper modules `tests.test_main_window_shell`, "
                + "`tests.test_script_editor_dock`, `tests.test_shell_run_controller`, and "
                + "`tests.test_shell_project_session_controller` shall remain on explicit "
                + "fresh-process `unittest` execution inside the documented `full` workflow rather "
                + "than the pytest phases.\n",
                encoding="utf-8",
            )

            verification_matrix = repo_root / self.manifest.VERIFICATION_SPEED_MATRIX_DOC
            replace_text(
                verification_matrix,
                "`26 passed in 57.27s`",
                "57.27 seconds",
            )
            replace_text(
                verification_matrix,
                "resolved value to `6` workers.",
                "resolved value to `6` workers.\nadds `-n auto` only when `pytest-xdist` is importable in the project venv",
            )

            traceability_matrix = repo_root / self.manifest.TRACEABILITY_MATRIX_DOC
            remove_token_from_traceability_row(
                traceability_matrix,
                "REQ-QA-015",
                self.manifest.SHELL_ISOLATION_SPEC.test_path,
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "README.md: missing required text: dedicated fresh-process shell-isolation phase",
            issues,
        )
        self.assertIn(
            "README.md: found stale text: shell-wrapper suites for isolated `unittest` execution",
            issues,
        )
        self.assertIn(
            f"{self.manifest.QA_ACCEPTANCE_DOC}: found stale text: the four shell-wrapper modules "
            "`tests.test_main_window_shell`, `tests.test_script_editor_dock`, "
            "`tests.test_shell_run_controller`, and `tests.test_shell_project_session_controller` "
            "shall remain on explicit fresh-process `unittest` execution",
            issues,
        )
        self.assertIn(
            f"{self.manifest.QA_ACCEPTANCE_DOC}: requirement REQ-QA-015 missing fact: {self.manifest.SHELL_ISOLATION_SPEC.test_path}",
            issues,
        )
        self.assertIn(
            f"{self.manifest.VERIFICATION_SPEED_MATRIX_DOC}: dedicated shell-isolation benchmark result is not a pytest timing summary: 57.27 seconds",
            issues,
        )
        self.assertIn(
            f"{self.manifest.VERIFICATION_SPEED_MATRIX_DOC}: found stale text: adds `-n auto` only when `pytest-xdist` is importable in the project venv",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACEABILITY_MATRIX_DOC}: row REQ-QA-015 missing implementation "
            f"artifact text: {self.manifest.SHELL_ISOLATION_SPEC.test_path}",
            issues,
        )

    def test_audit_repository_reports_release_doc_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            replace_text(
                repo_root / "README.md",
                "scripts/check_markdown_links.py",
                "scripts/check_docs.py",
            )
            replace_text(
                repo_root / "docs/specs/INDEX.md",
                "ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md",
                "ARCHITECTURE_MAINTAINABILITY_REFACTOR_MATRIX.md",
            )
            update_markdown_table_result(
                repo_root / "docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md",
                ARCHITECTURE_MAINTAINABILITY_REFACTOR_MARKDOWN_COMMAND,
                "Pending",
                "Markdown links were not rerun after the doc refresh",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "README.md: missing required text: scripts/check_markdown_links.py",
            issues,
        )
        self.assertIn(
            "docs/specs/INDEX.md: missing required text: ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md",
            issues,
        )
        self.assertIn(
            "docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md: "
            "2026-03-28 Execution Results command "
            f"{ARCHITECTURE_MAINTAINABILITY_REFACTOR_MARKDOWN_COMMAND} has unexpected result: Pending",
            issues,
        )

    def test_project_managed_files_docs_record_final_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in PROJECT_MANAGED_FILES_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_project_managed_files_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in PROJECT_MANAGED_FILES_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_project_managed_files_qa_matrix_records_final_commands_and_deferrals(self) -> None:
        text = PROJECT_MANAGED_FILES_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in PROJECT_MANAGED_FILES_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_pydpf_viewer_docs_record_closeout_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in PYDPF_VIEWER_V1_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_pydpf_viewer_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in PYDPF_VIEWER_V1_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_pydpf_viewer_qa_matrix_records_commands_and_manual_checks(self) -> None:
        text = PYDPF_VIEWER_V1_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in PYDPF_VIEWER_V1_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_architecture_maintainability_refactor_docs_record_final_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in ARCHITECTURE_MAINTAINABILITY_REFACTOR_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_architecture_maintainability_refactor_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in ARCHITECTURE_MAINTAINABILITY_REFACTOR_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_architecture_maintainability_refactor_qa_matrix_records_commands_and_boundaries(self) -> None:
        text = ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX_TOKENS:
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
