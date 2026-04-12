#!/usr/bin/env python3
"""Validate the packet-owned verification traceability layer."""

from __future__ import annotations

from pathlib import Path
import re
import sys

try:
    import verification_manifest as manifest
except ModuleNotFoundError:
    import scripts.verification_manifest as manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_REQUIRED_ARTIFACTS = manifest.PROOF_AUDIT_REQUIRED_ARTIFACTS
GENERIC_DOCUMENT_RULES = manifest.GENERIC_DOCUMENT_RULES
OLD_SHELL_TAIL_RESULT_PATTERN = re.compile(r"^`\d+\.\d+s` mean across `\d+` reps$")
SHELL_ISOLATION_RESULT_PATTERN = re.compile(r"^`\d+ passed in \d+\.\d+s`$")

P10_TRACEABILITY_TEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC = (
    manifest.ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC
)
ARCHITECTURE_RESIDUAL_REFACTOR_TARGETED_REGRESSION_COMMAND = (
    manifest.ARCHITECTURE_RESIDUAL_REFACTOR_TARGETED_REGRESSION_COMMAND
)
ARCHITECTURE_RESIDUAL_REFACTOR_TRACEABILITY_COMMAND = (
    manifest.ARCHITECTURE_RESIDUAL_REFACTOR_TRACEABILITY_COMMAND
)
ARCHITECTURE_RESIDUAL_REFACTOR_MARKDOWN_COMMAND = (
    manifest.ARCHITECTURE_RESIDUAL_REFACTOR_MARKDOWN_COMMAND
)
UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_DOC = (
    "docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md"
)
UI_CONTEXT_SCALABILITY_REFACTOR_FINAL_PYTEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest "
    "tests/test_traceability_checker.py tests/test_markdown_hygiene.py "
    "tests/test_run_verification.py --ignore=venv -q"
)
UI_CONTEXT_SCALABILITY_REFACTOR_TRACEABILITY_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_traceability.py"
)
UI_CONTEXT_SCALABILITY_REFACTOR_MARKDOWN_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_markdown_links.py"
)
DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_DOC = "docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md"
DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX_DOC = (
    "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md"
)
DPF_OPERATOR_PLUGIN_BACKEND_P01_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py "
    r"tests/test_dpf_node_catalog.py --ignore=venv -q"
)
DPF_OPERATOR_PLUGIN_BACKEND_P02_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py "
    r"tests/test_registry_validation.py tests/test_registry_filters.py --ignore=venv -q"
)
DPF_OPERATOR_PLUGIN_BACKEND_P03_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_dpf_compute_nodes.py "
    r"tests/test_dpf_runtime_service.py tests/test_passive_runtime_wiring.py "
    r"tests/test_execution_worker.py --ignore=venv -q"
)
DPF_OPERATOR_PLUGIN_BACKEND_P04_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_serializer.py "
    r"tests/test_serializer_schema_migration.py "
    r"tests/test_graph_scene_bridge_bind_regression.py "
    r"tests/test_graph_surface_input_contract.py --ignore=venv -q"
)
DPF_OPERATOR_PLUGIN_BACKEND_CLOSEOUT_PYTEST_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py "
    r"tests/test_markdown_hygiene.py --ignore=venv -q"
)
DPF_OPERATOR_PLUGIN_BACKEND_TRACEABILITY_COMMAND = (
    r".\venv\Scripts\python.exe scripts/check_traceability.py"
)
DPF_OPERATOR_PLUGIN_BACKEND_MARKDOWN_COMMAND = (
    r".\venv\Scripts\python.exe scripts/check_markdown_links.py"
)
REQUIRED_ARTIFACTS = (
    *BASE_REQUIRED_ARTIFACTS,
    UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_DOC,
    DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_DOC,
    DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX_DOC,
)
P08_REQUIRED_ARTIFACTS = (
    "docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json",
    "docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/SHELL_PACKET.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/PRESENTERS_PACKET.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SCENE_PACKET.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/EDGE_RENDERING_PACKET.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/VIEWER_PACKET.md",
)
GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR = "artifacts/graphics_performance_modes_docs"
GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD = (
    f"{GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR}/TRACK_H_BENCHMARK_REPORT.md"
)
GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON = (
    f"{GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR}/track_h_benchmark_report.json"
)
P09_FULL_FIDELITY_REPORT_MD = (
    "artifacts/graph_canvas_interaction_perf_p09_full_fidelity/TRACK_H_BENCHMARK_REPORT.md"
)
P09_FULL_FIDELITY_REPORT_JSON = (
    "artifacts/graph_canvas_interaction_perf_p09_full_fidelity/track_h_benchmark_report.json"
)
P09_MAX_PERFORMANCE_REPORT_MD = (
    "artifacts/graph_canvas_interaction_perf_p09_max_performance/TRACK_H_BENCHMARK_REPORT.md"
)
P09_MAX_PERFORMANCE_REPORT_JSON = (
    "artifacts/graph_canvas_interaction_perf_p09_max_performance/track_h_benchmark_report.json"
)
P09_NODE_DRAG_REPORT_MD = (
    "artifacts/graph_canvas_interaction_perf_p09_node_drag_control/TRACK_H_BENCHMARK_REPORT.md"
)
P09_NODE_DRAG_REPORT_JSON = (
    "artifacts/graph_canvas_interaction_perf_p09_node_drag_control/track_h_benchmark_report.json"
)
P09_DESKTOP_REFERENCE_REPORT_MD = (
    "artifacts/graph_canvas_interaction_perf_p09_desktop_reference/TRACK_H_BENCHMARK_REPORT.md"
)
P09_DESKTOP_REFERENCE_REPORT_JSON = (
    "artifacts/graph_canvas_interaction_perf_p09_desktop_reference/track_h_benchmark_report.json"
)
P10_REQUIRED_GENERATED_ARTIFACTS = (
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD,
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
    P09_FULL_FIDELITY_REPORT_MD,
    P09_FULL_FIDELITY_REPORT_JSON,
    P09_MAX_PERFORMANCE_REPORT_MD,
    P09_MAX_PERFORMANCE_REPORT_JSON,
    P09_NODE_DRAG_REPORT_MD,
    P09_NODE_DRAG_REPORT_JSON,
    P09_DESKTOP_REFERENCE_REPORT_MD,
    P09_DESKTOP_REFERENCE_REPORT_JSON,
)
GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe "
    "-m ea_node_editor.telemetry.performance_harness "
    "--nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 "
    "--baseline-runs 3 --performance-mode max_performance --scenario heavy_media "
    f"--report-dir artifacts/graph_canvas_interaction_perf_p09_max_performance"
)
P09_FULL_FIDELITY_OFFSCREEN_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe "
    "-m ea_node_editor.telemetry.performance_harness "
    "--nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 "
    "--baseline-runs 3 --performance-mode full_fidelity --scenario heavy_media "
    "--report-dir artifacts/graph_canvas_interaction_perf_p09_full_fidelity"
)
P09_NODE_DRAG_OFFSCREEN_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe "
    "-m ea_node_editor.telemetry.performance_harness "
    "--nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 "
    "--baseline-runs 3 --performance-mode full_fidelity --scenario heavy_media "
    "--report-dir artifacts/graph_canvas_interaction_perf_p09_node_drag_control"
)
GRAPHICS_PERFORMANCE_MODES_INTERACTIVE_COMMAND = (
    "./venv/Scripts/python.exe "
    "-m ea_node_editor.telemetry.performance_harness "
    "--nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 "
    "--baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference "
    "--performance-mode full_fidelity --scenario heavy_media --qt-platform windows "
    "--report-dir artifacts/graph_canvas_interaction_perf_p09_desktop_reference"
)

P10_REQUIREMENT_DOC_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-016": ("graphics performance mode", "Full Fidelity", "Max Performance"),
        "REQ-UI-024": ("status strip", "Graphics:", "same persisted preference"),
        "AC-REQ-UI-016-01": ("graphics performance mode", "shell-theme", "graph-theme"),
        "AC-REQ-UI-024-01": ("status-strip", "Graphics Settings", "saved mode"),
    },
    "docs/specs/requirements/40_NODE_SDK.md": {
        "REQ-NODE-016": (
            "render_quality",
            "weight_class",
            "max_performance_strategy",
            "supported_quality_tiers",
            "safe defaults",
        ),
        "AC-REQ-NODE-016-01": ("render_quality", "graph-surface payload", "safe defaults"),
    },
    "docs/specs/requirements/60_PERSISTENCE.md": {
        "REQ-PERSIST-011": ("graphics performance mode", "user_data_dir()", "last_session.json"),
        "AC-REQ-PERSIST-011-01": ("graphics performance mode", "last_session.json"),
    },
    "docs/specs/requirements/80_PERFORMANCE.md": {
        "REQ-PERF-006": (
            "full_fidelity",
            "max_performance",
            "whole-canvas simplification",
            "proxy-surface",
            "steady-state idle appearance returns automatically",
        ),
        "AC-REQ-PERF-002-01": (
            "performance_mode",
            "resolved_graphics_performance_mode",
            "scenario",
            "media_surface_count",
            "GraphCanvas.qml",
        ),
        "AC-REQ-PERF-002-02": (
            "--baseline-runs 3 --performance-mode max_performance --scenario heavy_media",
            GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
            "desktop/manual exit-gate status",
            "desktop_reference",
        ),
        "AC-REQ-PERF-003-01": (
            GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
            "3-run mode-aware heavy-media benchmark workflow",
        ),
    },
}

P10_QA_ACCEPTANCE_REQUIREMENT_TOKENS = {
    "REQ-QA-009": ("graphics-performance", "status-strip quick-toggle", "canvas preference behavior"),
    "REQ-QA-011": ("render-quality metadata", "built-in media proxy behavior"),
    "REQ-QA-018": (
        "performance_mode",
        "scenario",
        "canonical artifact path",
        "desktop/manual exit-gate status",
    ),
    "AC-REQ-QA-018-01": (
        GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND,
        manifest.proof_audit_command(),
        manifest.GRAPH_CANVAS_PERF_MATRIX_DOC,
        manifest.TRACK_H_BENCHMARK_REPORT_DOC,
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD,
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
        P09_DESKTOP_REFERENCE_REPORT_MD,
    ),
}
QA_ACCEPTANCE_REQUIREMENT_TOKENS = dict(manifest.QA_ACCEPTANCE_REQUIREMENT_TOKENS)
QA_ACCEPTANCE_REQUIREMENT_TOKENS.update(P10_QA_ACCEPTANCE_REQUIREMENT_TOKENS)
QA_ACCEPTANCE_REQUIREMENT_TOKENS.update(
    {
        "REQ-QA-030": (
            "UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md",
            "P07",
            "context-budget",
            "P08",
            "subsystem-doc",
            "CONTEXT_BUDGET_RULES.json",
            "SUBSYSTEM_PACKET_INDEX.md",
            "FEATURE_PACKET_TEMPLATE.md",
        ),
        "AC-REQ-QA-030-01": (
            UI_CONTEXT_SCALABILITY_REFACTOR_FINAL_PYTEST_COMMAND,
            UI_CONTEXT_SCALABILITY_REFACTOR_TRACEABILITY_COMMAND,
            UI_CONTEXT_SCALABILITY_REFACTOR_MARKDOWN_COMMAND,
            "UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md",
        ),
        "REQ-QA-035": (
            "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR",
            "optional plugin lifecycle",
            "operator metadata and generated ports",
            "generic operator-backed runtime invocation",
            "missing-plugin placeholder portability",
        ),
        "REQ-QA-036": (
            "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
            "`P01` through `P04`",
            "traceability, markdown-hygiene, and markdown-link",
            "manual DPF availability or reopen smoke checks",
            "later operator-rollout packet set",
        ),
        "AC-REQ-QA-035-01": (
            DPF_OPERATOR_PLUGIN_BACKEND_P01_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_P02_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_P03_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_P04_COMMAND,
            "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
        ),
        "AC-REQ-QA-036-01": (
            DPF_OPERATOR_PLUGIN_BACKEND_CLOSEOUT_PYTEST_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_TRACEABILITY_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_MARKDOWN_COMMAND,
            "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
        ),
    }
)
QA_ACCEPTANCE_CURRENT_CLOSEOUT_EVIDENCE_TOKENS = (
    *manifest.ARCHITECTURE_RESIDUAL_REFACTOR_CURRENT_EVIDENCE_TOKENS,
    UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_DOC,
    DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_DOC,
    DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX_DOC,
    "docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json",
    "docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md",
)

GRAPHICS_PERFORMANCE_MODES_MATRIX_REQUIRED_TOKENS = (
    "GraphCanvas.qml",
    "--baseline-runs 3 --performance-mode max_performance --scenario heavy_media",
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
    "## Desktop/Manual Exit Gate",
    "Status: `PASS`",
    P09_DESKTOP_REFERENCE_REPORT_MD,
)
GRAPHICS_PERFORMANCE_MODES_MATRIX_AUDIT_COMMANDS = (
    P10_TRACEABILITY_TEST_COMMAND,
    P09_FULL_FIDELITY_OFFSCREEN_COMMAND,
    GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND,
    P09_NODE_DRAG_OFFSCREEN_COMMAND,
    GRAPHICS_PERFORMANCE_MODES_INTERACTIVE_COMMAND,
    manifest.proof_audit_command(),
)
GRAPHICS_PERFORMANCE_MODES_TRACK_H_REPORT_REQUIRED_TOKENS = (
    "GraphCanvas.qml",
    GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND,
    GRAPHICS_PERFORMANCE_MODES_INTERACTIVE_COMMAND,
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD,
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
    "Performance mode: `max_performance`",
    "Scenario: `heavy_media`",
    "Resolved canvas mode: `max_performance`",
    "Media surface count: `6`",
    "## 2026-03-21 Offscreen Snapshot",
    "## Windows Desktop Exit Gate",
    "Status: `PASS`",
    P09_DESKTOP_REFERENCE_REPORT_MD,
    P09_DESKTOP_REFERENCE_REPORT_JSON,
    manifest.GRAPH_CANVAS_PERF_MATRIX_DOC,
)
GRAPHICS_PERFORMANCE_MODES_TRACK_H_REPORT_FORBIDDEN_TOKENS = (
    "artifacts/graph_canvas_perf_docs",
    "Historical offscreen harness baseline restored from repo",
    "`P04`",
    "P08 did not rerun the performance harness.",
    "Interactive desktop/GPU validation remains required",
)
ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX_REQUIRED_TOKENS = (
    "## Locked Scope",
    "## Shell Isolation Contract",
    "## Final Verification Commands",
    "## Focused Narrow Reruns",
    "## 2026-03-28 Execution Results",
    "## Remaining Manual and Windows-Only Checks",
    "## Historical References",
    "## Residual Risks",
    manifest.PACKAGING_WINDOWS_DOC,
    manifest.PILOT_RUNBOOK_DOC,
    manifest.ARCHITECTURE_REFACTOR_QA_MATRIX_DOC,
    "tests/shell_isolation_runtime.py",
    "tests/shell_isolation_main_window_targets.py",
    "tests/shell_isolation_controller_targets.py",
    "RC_PACKAGING_REPORT.md",
    "PILOT_SIGNOFF.md",
    manifest.MARKDOWN_HYGIENE_TEST,
)
ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX_AUDIT_COMMANDS = (
    manifest.DOCS_RELEASE_TRACEABILITY_PYTEST_COMMAND,
    manifest.proof_audit_command(),
    f"{manifest.LOCAL_VENV_PYTHON_DISPLAY} {manifest.CHECK_MARKDOWN_LINKS_SCRIPT}",
)
ARCHITECTURE_DOC_REQUIRED_TOKENS = (
    "docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md",
    "docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md",
    "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
    "Broad autogenerated operator rollout and non-operator `ansys.dpf.core` reflection remain deferred",
    "read-only missing-plugin placeholders",
)
SPEC_INDEX_REQUIRED_TOKENS = (
    *manifest.ARCHITECTURE_RESIDUAL_REFACTOR_SPEC_INDEX_TOKENS,
    "UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md",
)
ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_REQUIRED_TOKENS = (
    manifest.ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_REQUIRED_TOKENS
)
ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_AUDIT_COMMANDS = (
    manifest.ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_AUDIT_COMMANDS
)
UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_REQUIRED_TOKENS = (
    "UI Context Scalability Refactor QA Matrix",
    "## Locked Scope",
    "## Retained Automated Verification",
    "## Final Closeout Commands",
    "## 2026-04-05 Execution Results",
    "## Remaining Manual Desktop Checks",
    "## Residual Risks",
    "docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json",
    "docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md",
    "scripts/check_context_budgets.py",
    "tests/test_run_verification.py",
    UI_CONTEXT_SCALABILITY_REFACTOR_FINAL_PYTEST_COMMAND,
    UI_CONTEXT_SCALABILITY_REFACTOR_TRACEABILITY_COMMAND,
    UI_CONTEXT_SCALABILITY_REFACTOR_MARKDOWN_COMMAND,
    "P01_shell_window_facade_collapse_WRAPUP.md",
    "P02_presenter_family_split_WRAPUP.md",
    "P03_graph_scene_bridge_packet_split_WRAPUP.md",
    "P04_graph_canvas_root_packetization_WRAPUP.md",
    "P05_edge_renderer_packet_split_WRAPUP.md",
    "P06_viewer_surface_isolation_WRAPUP.md",
    "P07_context_budget_guardrails_WRAPUP.md",
    "P08_subsystem_packet_docs_WRAPUP.md",
)
UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_AUDIT_COMMANDS = (
    UI_CONTEXT_SCALABILITY_REFACTOR_FINAL_PYTEST_COMMAND,
    UI_CONTEXT_SCALABILITY_REFACTOR_TRACEABILITY_COMMAND,
    UI_CONTEXT_SCALABILITY_REFACTOR_MARKDOWN_COMMAND,
)
README_DPF_OPERATOR_PLUGIN_BACKEND_TOKENS = (
    "DPF operator backend review",
    "DPF operator backend QA matrix",
    "ansys-dpf-core` is optional at startup",
    "read-only missing-plugin placeholders",
    "broad autogenerated operator exposure plus non-operator",
)
DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_REQUIRED_TOKENS = (
    "## Delivered Backend Contract",
    "## Explicit Deferrals For Later Operator Rollout",
    "plugin_loader.py",
    "ansys_dpf_catalog.py",
    "graph_scene_payload_builder.py",
    "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
    "Non-operator `ansys.dpf.core` reflection",
)
DPF_OPERATOR_PLUGIN_BACKEND_INTEGRATIONS_REQUIREMENT_TOKENS = {
    "REQ-INT-009": (
        "ansys-dpf-core",
        "lazily register",
        "normalize operator metadata",
        "generic DPF runtime adapter",
        "read-only missing-plugin placeholders",
        "non-operator `ansys.dpf.core` reflection",
    ),
    "AC-REQ-INT-009-01": (
        "DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md",
        "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
        "plugin-loader",
        "missing-plugin placeholder portability",
    ),
}
DPF_OPERATOR_PLUGIN_BACKEND_QA_MATRIX_REQUIRED_TOKENS = (
    "DPF Operator Plugin Backend Refactor QA Matrix",
    "## Locked Scope",
    "## Retained Automated Verification",
    "## Final Closeout Commands",
    "## 2026-04-12 Execution Results",
    "## Retained Manual Evidence",
    "## Residual Risks",
    "ansys-dpf-core",
    "generated-port semantics",
    "read-only missing-plugin placeholders",
    "tests/ansys_dpf_core/example_outputs/",
    "ElementalNodal",
    "P01_optional_dpf_plugin_lifecycle_WRAPUP.md",
    "P04_missing_plugin_placeholder_portability_WRAPUP.md",
    DPF_OPERATOR_PLUGIN_BACKEND_P01_COMMAND,
    DPF_OPERATOR_PLUGIN_BACKEND_P02_COMMAND,
    DPF_OPERATOR_PLUGIN_BACKEND_P03_COMMAND,
    DPF_OPERATOR_PLUGIN_BACKEND_P04_COMMAND,
    DPF_OPERATOR_PLUGIN_BACKEND_CLOSEOUT_PYTEST_COMMAND,
    DPF_OPERATOR_PLUGIN_BACKEND_TRACEABILITY_COMMAND,
    DPF_OPERATOR_PLUGIN_BACKEND_MARKDOWN_COMMAND,
)
DPF_OPERATOR_PLUGIN_BACKEND_QA_MATRIX_AUDIT_COMMANDS = (
    DPF_OPERATOR_PLUGIN_BACKEND_CLOSEOUT_PYTEST_COMMAND,
    DPF_OPERATOR_PLUGIN_BACKEND_TRACEABILITY_COMMAND,
    DPF_OPERATOR_PLUGIN_BACKEND_MARKDOWN_COMMAND,
)

P10_TRACEABILITY_ROW_REQUIRED_TOKENS = {
    "REQ-UI-016": (
        "graphics_settings_dialog.py",
        "show_graphics_settings_dialog",
        "tests/test_graphics_settings_preferences.py",
    ),
    "REQ-UI-024": ("ShellStatusStrip.qml", "shell_runtime_contracts.py", "bridge_qml_boundaries.py"),
    "AC-REQ-UI-016-01": (
        "tests/test_graphics_settings_preferences.py",
        "tests/test_shell_theme.py",
        "tests/test_main_window_shell.py",
    ),
    "AC-REQ-UI-024-01": (
        "shell_runtime_contracts.py",
        "bridge_qml_boundaries.py",
        "tests/test_graphics_settings_preferences.py",
    ),
    "REQ-NODE-016": (
        "graph_scene_payload_builder.py",
        "tests/test_graph_surface_input_contract.py",
        "tests/test_passive_node_contracts.py",
    ),
    "AC-REQ-NODE-016-01": (
        "tests/test_graph_surface_input_contract.py",
        "tests/test_passive_node_contracts.py",
        "tests/test_registry_validation.py",
    ),
    "REQ-PERSIST-011": (
        "tests/test_graphics_settings_preferences.py",
        "tests/main_window_shell/shell_basics_and_search.py",
    ),
    "AC-REQ-PERSIST-011-01": (
        "tests/test_shell_project_session_controller.py",
        "tests/main_window_shell/shell_basics_and_search.py",
    ),
    "REQ-PERF-001": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
    ),
    "REQ-PERF-002": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
        "GraphCanvas.qml",
    ),
    "REQ-PERF-003": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
        "load",
    ),
    "REQ-PERF-006": (
        "GraphCanvasPerformancePolicy.js",
        "tests/graph_track_b/qml_preference_bindings.py",
        "tests/test_passive_graph_surface_host.py",
    ),
    "REQ-QA-009": (
        "shell_runtime_contracts.py",
        "bridge_qml_boundaries.py",
        "tests/test_graphics_settings_dialog.py",
    ),
    "REQ-QA-011": (
        "tests/test_graph_surface_input_contract.py",
        "tests/test_passive_node_contracts.py",
        "tests/test_passive_graph_surface_host.py",
    ),
    "REQ-QA-018": (
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "TRACK_H_BENCHMARK_REPORT.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
        P09_DESKTOP_REFERENCE_REPORT_JSON,
        manifest.CHECK_TRACEABILITY_SCRIPT,
    ),
    "AC-REQ-PERF-002-01": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "tests/test_track_h_perf_harness.py",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
    ),
    "AC-REQ-PERF-003-01": (
        "TRACK_H_BENCHMARK_REPORT.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
        P09_MAX_PERFORMANCE_REPORT_JSON,
    ),
    "AC-REQ-PERF-002-02": (
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "TRACK_H_BENCHMARK_REPORT.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
        P09_DESKTOP_REFERENCE_REPORT_JSON,
    ),
    "AC-REQ-QA-018-01": (
        GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND,
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "TRACK_H_BENCHMARK_REPORT.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD,
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
        P09_DESKTOP_REFERENCE_REPORT_MD,
        manifest.CHECK_TRACEABILITY_SCRIPT,
    ),
}
TRACEABILITY_ROW_REQUIRED_TOKENS = dict(manifest.TRACEABILITY_ROW_REQUIRED_TOKENS)
TRACEABILITY_ROW_REQUIRED_TOKENS.update(P10_TRACEABILITY_ROW_REQUIRED_TOKENS)
TRACEABILITY_ROW_REQUIRED_TOKENS.update(
    {
        "REQ-QA-030": (
            "docs/specs/INDEX.md",
            "docs/specs/requirements/90_QA_ACCEPTANCE.md",
            "docs/specs/requirements/TRACEABILITY_MATRIX.md",
            UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_DOC,
            "docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json",
            "docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md",
            "docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md",
            "scripts/check_context_budgets.py",
            "scripts/check_traceability.py",
            "tests/test_traceability_checker.py",
            "tests/test_markdown_hygiene.py",
            "tests/test_run_verification.py",
        ),
        "AC-REQ-QA-030-01": (
            UI_CONTEXT_SCALABILITY_REFACTOR_FINAL_PYTEST_COMMAND,
            UI_CONTEXT_SCALABILITY_REFACTOR_TRACEABILITY_COMMAND,
            UI_CONTEXT_SCALABILITY_REFACTOR_MARKDOWN_COMMAND,
            "UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md",
        ),
        "REQ-INT-009": (
            "plugin_loader.py",
            "plugin_contracts.py",
            "ansys_dpf_catalog.py",
            "ansys_dpf_common.py",
            "base.py",
            "operations.py",
            "project_codec.py",
            "DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md",
            "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
        ),
        "AC-REQ-INT-009-01": (
            "tests/test_plugin_loader.py",
            "tests/test_dpf_node_catalog.py",
            "tests/test_dpf_compute_nodes.py",
            "tests/test_dpf_runtime_service.py",
            "tests/test_serializer_schema_migration.py",
            "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
        ),
        "REQ-QA-035": (
            "docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md",
            "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
            "tests/test_plugin_loader.py",
            "tests/test_dpf_node_catalog.py",
            "tests/test_dpf_compute_nodes.py",
            "tests/test_dpf_runtime_service.py",
            "tests/test_serializer_schema_migration.py",
            "scripts/check_traceability.py",
        ),
        "REQ-QA-036": (
            "ARCHITECTURE.md",
            "README.md",
            "docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md",
            "docs/specs/requirements/70_INTEGRATIONS.md",
            "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
            "tests/test_traceability_checker.py",
            "tests/test_markdown_hygiene.py",
            "scripts/check_traceability.py",
        ),
        "AC-REQ-QA-035-01": (
            DPF_OPERATOR_PLUGIN_BACKEND_P01_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_P02_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_P03_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_P04_COMMAND,
            "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
        ),
        "AC-REQ-QA-036-01": (
            DPF_OPERATOR_PLUGIN_BACKEND_CLOSEOUT_PYTEST_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_TRACEABILITY_COMMAND,
            DPF_OPERATOR_PLUGIN_BACKEND_MARKDOWN_COMMAND,
            "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
        ),
    }
)

P10_TRACEABILITY_ROW_FORBIDDEN_TOKENS = {
    "REQ-QA-018": ("artifacts/graph_canvas_perf_docs",),
    "AC-REQ-PERF-003-01": ("artifacts/graph_canvas_perf_docs",),
    "AC-REQ-QA-018-01": ("artifacts/graph_canvas_perf_docs",),
}
TRACEABILITY_ROW_FORBIDDEN_TOKENS = dict(manifest.TRACEABILITY_ROW_FORBIDDEN_TOKENS)
TRACEABILITY_ROW_FORBIDDEN_TOKENS.update(P10_TRACEABILITY_ROW_FORBIDDEN_TOKENS)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def strip_code_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
        return stripped[1:-1]
    return stripped


def strip_worktree_ignore_args(command: str) -> str:
    stripped = command
    for arg in manifest.worktree_pytest_ignore_args():
        stripped = stripped.replace(f" {arg}", "")
    return stripped


def extract_section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return None
    return match.group("body").strip("\n")


def parse_markdown_table(section_text: str) -> list[dict[str, str]] | None:
    table_lines: list[str] = []
    in_table = False
    for line in section_text.splitlines():
        if line.startswith("|"):
            table_lines.append(line)
            in_table = True
            continue
        if in_table:
            break
    if len(table_lines) < 2:
        return None

    headers = [cell.strip() for cell in table_lines[0].strip().strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def parse_traceability_rows(matrix_text: str) -> dict[str, dict[str, str]]:
    """Parse the top-level requirement traceability table by requirement id."""

    rows = parse_markdown_table(matrix_text)
    if rows is None:
        return {}
    parsed: dict[str, dict[str, str]] = {}
    for row in rows:
        row_id = strip_code_fence(row.get("Requirement ID", ""))
        if row_id:
            parsed[row_id] = row
    return parsed


def table_after_heading(
    text: str,
    *,
    relative_path: str,
    heading: str,
    issues: list[str],
) -> list[dict[str, str]] | None:
    section = extract_section(text, heading)
    if section is None:
        issues.append(f"{relative_path}: missing section: {heading}")
        return None
    rows = parse_markdown_table(section)
    if rows is None:
        issues.append(f"{relative_path}: missing markdown table in section: {heading}")
        return None
    return rows


def find_row(
    rows: list[dict[str, str]],
    *,
    column: str,
    predicate,
) -> dict[str, str] | None:
    for row in rows:
        value = row.get(column, "")
        if predicate(value):
            return row
    return None


def require_tokens(
    text: str,
    tokens: tuple[str, ...],
    *,
    relative_path: str,
    label: str,
    issues: list[str],
) -> None:
    for token in tokens:
        if token not in text:
            issues.append(f"{relative_path}: {label} missing fact: {token}")


def require_command_result(
    rows: list[dict[str, str]],
    *,
    relative_path: str,
    heading: str,
    predicate,
    label: str,
    issues: list[str],
) -> dict[str, str] | None:
    row = find_row(rows, column="Command", predicate=lambda value: predicate(strip_code_fence(value)))
    if row is None:
        issues.append(f"{relative_path}: {heading} missing command row: {label}")
        return None
    result = strip_code_fence(row.get("Result", ""))
    if result != "PASS":
        issues.append(
            f"{relative_path}: {heading} command {label} has unexpected result: {result}"
        )
    return row


def parse_requirement_lines(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^- `([^`]+)`: (.+)$", line.strip())
        if match is not None:
            parsed[match.group(1)] = match.group(2)
    return parsed


def audit_requirement_tokens(
    text: str,
    relative_path: str,
    requirement_tokens: dict[str, tuple[str, ...]],
    issues: list[str],
) -> None:
    requirements = parse_requirement_lines(text)
    for requirement_id, tokens in requirement_tokens.items():
        body = requirements.get(requirement_id)
        if body is None:
            issues.append(f"{relative_path}: missing requirement line: {requirement_id}")
            continue
        require_tokens(
            body,
            tokens,
            relative_path=relative_path,
            label=f"requirement {requirement_id}",
            issues=issues,
        )


def audit_generic_document_rule(
    *,
    relative_path: str,
    text: str,
    rule: manifest.DocumentRule,
    issues: list[str],
) -> None:
    for snippet in rule.required:
        if snippet not in text:
            issues.append(f"{relative_path}: missing required text: {snippet}")
    for snippet in rule.forbidden:
        if snippet in text:
            issues.append(f"{relative_path}: found stale text: {snippet}")


def audit_qa_acceptance(text: str, relative_path: str, issues: list[str]) -> None:
    audit_requirement_tokens(text, relative_path, QA_ACCEPTANCE_REQUIREMENT_TOKENS, issues)
    current_closeout_evidence = extract_section(text, "Current Closeout Evidence")
    if current_closeout_evidence is None:
        issues.append(f"{relative_path}: missing section: Current Closeout Evidence")
    else:
        require_tokens(
            current_closeout_evidence,
            QA_ACCEPTANCE_CURRENT_CLOSEOUT_EVIDENCE_TOKENS,
            relative_path=relative_path,
            label="Current Closeout Evidence",
            issues=issues,
        )


def audit_requirement_doc(text: str, relative_path: str, issues: list[str]) -> None:
    requirement_tokens = P10_REQUIREMENT_DOC_TOKENS.get(relative_path)
    if requirement_tokens is None:
        return
    audit_requirement_tokens(text, relative_path, requirement_tokens, issues)


def audit_verification_speed_matrix(text: str, relative_path: str, issues: list[str]) -> None:
    for forbidden in manifest.VERIFICATION_SPEED_FORBIDDEN_TOKENS:
        if forbidden in text:
            issues.append(f"{relative_path}: found stale text: {forbidden}")

    workflow_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Approved Verification Workflow",
        issues=issues,
    )
    if workflow_rows is not None:
        for mode in manifest.MODE_NAMES:
            row = find_row(
                workflow_rows,
                column="Mode",
                predicate=lambda value, mode=mode: strip_code_fence(value) == mode,
            )
            if row is None:
                issues.append(
                    f"{relative_path}: Approved Verification Workflow missing mode row: {mode}"
                )
                continue
            command = strip_code_fence(row.get("Command", ""))
            expected_command = manifest.run_verification_command(mode)
            if command != expected_command:
                issues.append(
                    f"{relative_path}: Approved Verification Workflow row {mode} has unexpected command: {command}"
                )
            require_tokens(
                row.get("Notes", ""),
                manifest.VERIFICATION_SPEED_WORKFLOW_NOTE_TOKENS[mode],
                relative_path=relative_path,
                label=f"workflow row {mode}",
                issues=issues,
            )

    shell_rules = extract_section(text, "Locked Shell Isolation Rules")
    if shell_rules is None:
        issues.append(f"{relative_path}: missing section: Locked Shell Isolation Rules")
    else:
        shell_rule_command = manifest.shell_isolation_pytest_command()
        require_tokens(
            shell_rules,
            tuple(
                token
                for token in manifest.VERIFICATION_SPEED_SHELL_RULE_TOKENS
                if token != shell_rule_command
            ),
            relative_path=relative_path,
            label="Locked Shell Isolation Rules",
            issues=issues,
        )
        if (
            shell_rule_command not in shell_rules
            and strip_worktree_ignore_args(shell_rule_command) not in shell_rules
        ):
            issues.append(
                f"{relative_path}: Locked Shell Isolation Rules missing fact: "
                f"{shell_rule_command}"
            )

    benchmark_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Published Shell-Tail Benchmark Evidence",
        issues=issues,
    )
    if benchmark_rows is not None:
        old_row = find_row(
            benchmark_rows,
            column="Workflow Shape",
            predicate=lambda value: value == "Old sequential shell-tail baseline",
        )
        if old_row is None:
            issues.append(
                f"{relative_path}: Published Shell-Tail Benchmark Evidence missing row: Old sequential shell-tail baseline"
            )
        elif not OLD_SHELL_TAIL_RESULT_PATTERN.match(old_row.get("Recorded Result", "")):
            issues.append(
                f"{relative_path}: old shell-tail benchmark result is not a timed mean summary: {old_row.get('Recorded Result', '')}"
            )

        dedicated_row = find_row(
            benchmark_rows,
            column="Workflow Shape",
            predicate=lambda value: value == "Dedicated shell-isolation phase",
        )
        if dedicated_row is None:
            issues.append(
                f"{relative_path}: Published Shell-Tail Benchmark Evidence missing row: Dedicated shell-isolation phase"
            )
        else:
            result = dedicated_row.get("Recorded Result", "")
            if not SHELL_ISOLATION_RESULT_PATTERN.match(result):
                issues.append(
                    f"{relative_path}: dedicated shell-isolation benchmark result is not a pytest timing summary: {result}"
                )

    environment_notes = extract_section(text, "Current Environment Notes")
    if environment_notes is None:
        issues.append(f"{relative_path}: missing section: Current Environment Notes")
    else:
        require_tokens(
            environment_notes,
            manifest.VERIFICATION_SPEED_ENVIRONMENT_NOTE_TOKENS,
            relative_path=relative_path,
            label="Current Environment Notes",
            issues=issues,
        )

    proof_audit = extract_section(text, "Companion Proof Audit")
    if proof_audit is None:
        issues.append(f"{relative_path}: missing section: Companion Proof Audit")
    else:
        require_tokens(
            proof_audit,
            manifest.VERIFICATION_SPEED_COMPANION_PROOF_TOKENS,
            relative_path=relative_path,
            label="Companion Proof Audit",
            issues=issues,
        )

    baseline_status = extract_section(text, "Current Baseline Status")
    if baseline_status is None:
        issues.append(f"{relative_path}: missing section: Current Baseline Status")
    else:
        require_tokens(
            baseline_status,
            manifest.VERIFICATION_SPEED_BASELINE_REQUIRED_TOKENS,
            relative_path=relative_path,
            label="Current Baseline Status",
            issues=issues,
        )
        for forbidden in manifest.VERIFICATION_SPEED_BASELINE_FORBIDDEN_TOKENS:
            if forbidden in baseline_status:
                issues.append(f"{relative_path}: found stale text: {forbidden}")

    result_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="2026-03-18 Verification Results",
        issues=issues,
    )
    if result_rows is not None:
        require_command_result(
            result_rows,
            relative_path=relative_path,
            heading="2026-03-18 Verification Results",
            predicate=lambda command: command == manifest.VERIFICATION_SPEED_RESULT_COMMANDS[0],
            label=manifest.VERIFICATION_SPEED_RESULT_COMMANDS[0],
            issues=issues,
        )
        require_command_result(
            result_rows,
            relative_path=relative_path,
            heading="2026-03-18 Verification Results",
            predicate=lambda command: (
                (
                    command.startswith(manifest.VERIFICATION_SPEED_SHELL_RESULT_COMMAND_PREFIX)
                    or command.startswith(
                        strip_worktree_ignore_args(
                            manifest.VERIFICATION_SPEED_SHELL_RESULT_COMMAND_PREFIX
                        )
                    )
                )
                and all(
                    token in command
                    for token in manifest.VERIFICATION_SPEED_SHELL_RESULT_REQUIRED_TOKENS
                )
            ),
            label=manifest.SHELL_ISOLATION_SPEC.test_path,
            issues=issues,
        )
        require_command_result(
            result_rows,
            relative_path=relative_path,
            heading="2026-03-18 Verification Results",
            predicate=lambda command: command == manifest.VERIFICATION_SPEED_RESULT_COMMANDS[1],
            label=manifest.VERIFICATION_SPEED_RESULT_COMMANDS[1],
            issues=issues,
        )


def audit_graph_canvas_perf_matrix(text: str, relative_path: str, issues: list[str]) -> None:
    require_tokens(
        text,
        GRAPHICS_PERFORMANCE_MODES_MATRIX_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="graph-canvas perf matrix",
        issues=issues,
    )

    approved_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Approved Regression Commands",
        issues=issues,
    )
    if approved_rows is not None:
        for command in GRAPHICS_PERFORMANCE_MODES_MATRIX_AUDIT_COMMANDS:
            row = find_row(
                approved_rows,
                column="Command",
                predicate=lambda value, command=command: strip_code_fence(value) == command,
            )
            if row is None:
                issues.append(
                    f"{relative_path}: Approved Regression Commands missing command row: {command}"
                )

    execution_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="2026-03-21 Execution Results",
        issues=issues,
    )
    if execution_rows is not None:
        for command in GRAPHICS_PERFORMANCE_MODES_MATRIX_AUDIT_COMMANDS:
            require_command_result(
                execution_rows,
                relative_path=relative_path,
                heading="2026-03-21 Execution Results",
                predicate=lambda value, command=command: value == command,
                label=command,
                issues=issues,
            )


def audit_track_h_report(text: str, relative_path: str, issues: list[str]) -> None:
    require_tokens(
        text,
        GRAPHICS_PERFORMANCE_MODES_TRACK_H_REPORT_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="track-h benchmark report",
        issues=issues,
    )
    for forbidden in GRAPHICS_PERFORMANCE_MODES_TRACK_H_REPORT_FORBIDDEN_TOKENS:
        if forbidden in text:
            issues.append(f"{relative_path}: found stale text: {forbidden}")


def audit_architecture_maintainability_refactor_qa_matrix(
    text: str,
    relative_path: str,
    issues: list[str],
) -> None:
    require_tokens(
        text,
        ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="architecture-maintainability-refactor qa matrix",
        issues=issues,
    )

    final_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Final Verification Commands",
        issues=issues,
    )
    if final_rows is not None:
        for command in ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX_AUDIT_COMMANDS:
            row = find_row(
                final_rows,
                column="Command",
                predicate=lambda value, command=command: strip_code_fence(value) == command,
            )
            if row is None:
                issues.append(
                    f"{relative_path}: Final Verification Commands missing command row: {command}"
                )

    execution_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="2026-03-28 Execution Results",
        issues=issues,
    )
    if execution_rows is not None:
        for command in ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX_AUDIT_COMMANDS:
            require_command_result(
                execution_rows,
                relative_path=relative_path,
                heading="2026-03-28 Execution Results",
                predicate=lambda value, command=command: value == command,
                label=command,
                issues=issues,
            )


def audit_architecture_doc(text: str, relative_path: str, issues: list[str]) -> None:
    require_tokens(
        text,
        ARCHITECTURE_DOC_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="architecture closeout discovery",
        issues=issues,
    )


def audit_readme_doc(text: str, relative_path: str, issues: list[str]) -> None:
    require_tokens(
        text,
        README_DPF_OPERATOR_PLUGIN_BACKEND_TOKENS,
        relative_path=relative_path,
        label="readme dpf backend closeout",
        issues=issues,
    )


def audit_dpf_operator_plugin_backend_review(
    text: str,
    relative_path: str,
    issues: list[str],
) -> None:
    require_tokens(
        text,
        DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="dpf backend review",
        issues=issues,
    )


def audit_dpf_operator_plugin_backend_integrations(
    text: str,
    relative_path: str,
    issues: list[str],
) -> None:
    audit_requirement_tokens(
        text,
        relative_path,
        DPF_OPERATOR_PLUGIN_BACKEND_INTEGRATIONS_REQUIREMENT_TOKENS,
        issues,
    )


def audit_spec_index(text: str, relative_path: str, issues: list[str]) -> None:
    require_tokens(
        text,
        SPEC_INDEX_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="spec index registration",
        issues=issues,
    )


def audit_architecture_residual_refactor_qa_matrix(
    text: str,
    relative_path: str,
    issues: list[str],
) -> None:
    require_tokens(
        text,
        ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="architecture-residual-refactor qa matrix",
        issues=issues,
    )

    final_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Final Closeout Commands",
        issues=issues,
    )
    if final_rows is not None:
        for command in ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_AUDIT_COMMANDS:
            row = find_row(
                final_rows,
                column="Command",
                predicate=lambda value, command=command: strip_code_fence(value) == command,
            )
            if row is None:
                issues.append(
                    f"{relative_path}: Final Closeout Commands missing command row: {command}"
                )

    execution_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="2026-04-04 Execution Results",
        issues=issues,
    )
    if execution_rows is not None:
        for command in ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_AUDIT_COMMANDS:
            require_command_result(
                execution_rows,
                relative_path=relative_path,
                heading="2026-04-04 Execution Results",
                predicate=lambda value, command=command: value == command,
                label=command,
                issues=issues,
            )


def audit_ui_context_scalability_refactor_qa_matrix(
    text: str,
    relative_path: str,
    issues: list[str],
) -> None:
    require_tokens(
        text,
        UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="ui-context-scalability-refactor qa matrix",
        issues=issues,
    )

    final_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Final Closeout Commands",
        issues=issues,
    )
    if final_rows is not None:
        for command in UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_AUDIT_COMMANDS:
            row = find_row(
                final_rows,
                column="Command",
                predicate=lambda value, command=command: strip_code_fence(value) == command,
            )
            if row is None:
                issues.append(
                    f"{relative_path}: Final Closeout Commands missing command row: {command}"
                )

    execution_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="2026-04-05 Execution Results",
        issues=issues,
    )
    if execution_rows is not None:
        for command in UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_AUDIT_COMMANDS:
            require_command_result(
                execution_rows,
                relative_path=relative_path,
                heading="2026-04-05 Execution Results",
                predicate=lambda value, command=command: value == command,
                label=command,
                issues=issues,
            )


def audit_dpf_operator_plugin_backend_refactor_qa_matrix(
    text: str,
    relative_path: str,
    issues: list[str],
) -> None:
    require_tokens(
        text,
        DPF_OPERATOR_PLUGIN_BACKEND_QA_MATRIX_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="dpf-operator-plugin-backend-refactor qa matrix",
        issues=issues,
    )

    final_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Final Closeout Commands",
        issues=issues,
    )
    if final_rows is not None:
        for command in DPF_OPERATOR_PLUGIN_BACKEND_QA_MATRIX_AUDIT_COMMANDS:
            row = find_row(
                final_rows,
                column="Command",
                predicate=lambda value, command=command: strip_code_fence(value) == command,
            )
            if row is None:
                issues.append(
                    f"{relative_path}: Final Closeout Commands missing command row: {command}"
                )

    execution_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="2026-04-12 Execution Results",
        issues=issues,
    )
    if execution_rows is not None:
        for command in DPF_OPERATOR_PLUGIN_BACKEND_QA_MATRIX_AUDIT_COMMANDS:
            require_command_result(
                execution_rows,
                relative_path=relative_path,
                heading="2026-04-12 Execution Results",
                predicate=lambda value, command=command: value == command,
                label=command,
                issues=issues,
            )


def find_traceability_row(matrix_text: str, row_id: str) -> dict[str, str] | None:
    return parse_traceability_rows(matrix_text).get(row_id)


def audit_traceability_rows(matrix_text: str, issues: list[str]) -> None:
    rows = parse_traceability_rows(matrix_text)
    if not rows:
        issues.append(f"{manifest.TRACEABILITY_MATRIX_DOC}: missing requirement traceability table")
        return

    for row_id, required_tokens in TRACEABILITY_ROW_REQUIRED_TOKENS.items():
        row = rows.get(row_id)
        if row is None:
            issues.append(f"{manifest.TRACEABILITY_MATRIX_DOC}: missing row: {row_id}")
            continue
        implementation_artifacts = row.get("Implementation Artifact", "")
        for token in required_tokens:
            if token not in implementation_artifacts:
                issues.append(
                    f"{manifest.TRACEABILITY_MATRIX_DOC}: row {row_id} missing implementation "
                    f"artifact text: {token}"
                )
        for token in TRACEABILITY_ROW_FORBIDDEN_TOKENS.get(row_id, ()):
            if token in implementation_artifacts:
                issues.append(
                    f"{manifest.TRACEABILITY_MATRIX_DOC}: row {row_id} found stale implementation "
                    f"artifact text: {token}"
                )


SPECIAL_DOCUMENT_AUDITORS = {
    "ARCHITECTURE.md": audit_architecture_doc,
    "README.md": audit_readme_doc,
    DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_DOC: audit_dpf_operator_plugin_backend_review,
    manifest.SPEC_INDEX_DOC: audit_spec_index,
    "docs/specs/requirements/20_UI_UX.md": audit_requirement_doc,
    "docs/specs/requirements/40_NODE_SDK.md": audit_requirement_doc,
    "docs/specs/requirements/60_PERSISTENCE.md": audit_requirement_doc,
    "docs/specs/requirements/80_PERFORMANCE.md": audit_requirement_doc,
    "docs/specs/requirements/70_INTEGRATIONS.md": audit_dpf_operator_plugin_backend_integrations,
    manifest.QA_ACCEPTANCE_DOC: audit_qa_acceptance,
    manifest.VERIFICATION_SPEED_MATRIX_DOC: audit_verification_speed_matrix,
    manifest.GRAPH_CANVAS_PERF_MATRIX_DOC: audit_graph_canvas_perf_matrix,
    manifest.TRACK_H_BENCHMARK_REPORT_DOC: audit_track_h_report,
    manifest.CURRENT_CLOSEOUT_QA_MATRIX_DOC: audit_architecture_maintainability_refactor_qa_matrix,
    ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC: audit_architecture_residual_refactor_qa_matrix,
    UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_DOC: audit_ui_context_scalability_refactor_qa_matrix,
    DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX_DOC: audit_dpf_operator_plugin_backend_refactor_qa_matrix,
}


def audit_repository(repo_root: Path) -> list[str]:
    issues: list[str] = []
    matrix_text: str | None = None

    for relative_path in REQUIRED_ARTIFACTS:
        path = repo_root / relative_path
        if not path.exists():
            issues.append(f"Missing required artifact: {relative_path}")
    for relative_path in P08_REQUIRED_ARTIFACTS:
        path = repo_root / relative_path
        if not path.exists():
            issues.append(f"Missing required artifact: {relative_path}")
    for relative_path in P10_REQUIRED_GENERATED_ARTIFACTS:
        path = repo_root / relative_path
        if not path.exists():
            issues.append(f"Missing required generated artifact: {relative_path}")

    audited_documents = set(GENERIC_DOCUMENT_RULES) | set(SPECIAL_DOCUMENT_AUDITORS)
    for relative_path in audited_documents:
        path = repo_root / relative_path
        if not path.exists():
            continue
        text = read_text(path)
        if relative_path == manifest.TRACEABILITY_MATRIX_DOC:
            matrix_text = text
        rule = GENERIC_DOCUMENT_RULES.get(relative_path)
        if rule is not None:
            audit_generic_document_rule(
                relative_path=relative_path,
                text=text,
                rule=rule,
                issues=issues,
            )
        auditor = SPECIAL_DOCUMENT_AUDITORS.get(relative_path)
        if auditor is not None:
            auditor(text, relative_path, issues)

    if matrix_text is None:
        matrix_path = repo_root / manifest.TRACEABILITY_MATRIX_DOC
        if matrix_path.exists():
            matrix_text = read_text(matrix_path)

    if matrix_text is None:
        issues.append(f"Missing required artifact: {manifest.TRACEABILITY_MATRIX_DOC}")
        return issues

    audit_traceability_rows(matrix_text, issues)
    return issues


def main() -> int:
    issues = audit_repository(REPO_ROOT)
    if issues:
        print("TRACEABILITY CHECK FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("TRACEABILITY CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
