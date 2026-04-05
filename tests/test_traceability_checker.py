from __future__ import annotations

import importlib.util
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import verification_manifest as manifest


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

CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md"
)
CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_COMMAND = (
    "./venv/Scripts/python.exe -m pytest "
    "tests/test_execution_viewer_protocol.py tests/test_execution_client.py "
    "tests/test_execution_viewer_service.py tests/test_execution_worker.py "
    "tests/test_dpf_viewer_node.py --ignore=venv -q"
)
CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_SERVICE_COMMAND = (
    "./venv/Scripts/python.exe -m pytest "
    "tests/test_execution_viewer_service.py tests/test_execution_worker.py "
    "tests/test_dpf_viewer_node.py --ignore=venv -q"
)
CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_MATERIALIZATION_COMMAND = (
    "./venv/Scripts/python.exe -m pytest "
    "tests/test_dpf_runtime_service.py tests/test_dpf_materialization.py "
    "--ignore=venv -q"
)
CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P03_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_embedded_viewer_overlay_manager.py tests/test_viewer_host_service.py "
    "--ignore=venv -q"
)
CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_embedded_viewer_overlay_manager.py tests/test_viewer_host_service.py "
    "tests/test_dpf_viewer_widget_binder.py --ignore=venv -q"
)
CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_BRIDGE_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_viewer_session_bridge.py tests/test_shell_run_controller.py "
    "tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py "
    "--ignore=venv -q"
)
CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_SURFACE_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_viewer_surface_contract.py tests/test_viewer_surface_host.py "
    "--ignore=venv -q"
)
CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_TEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_traceability.py"
)

CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/10_ARCHITECTURE.md": {
        "REQ-ARCH-016": (
            "registry-driven",
            "backend_id",
            "ViewerHostService",
            "ViewerWidgetBinderRegistry",
            "EmbeddedViewerOverlayManager",
        ),
        "AC-REQ-ARCH-016-01": (
            "worker-side DPF authority",
            "backend and binder seams",
            "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-032": (
            "viewerSessionBridge",
            "ViewerHostService",
            "backend_id",
            "transport_revision",
            "rerun_required",
        ),
        "AC-REQ-UI-032-01": ("focus_only", "keep_live", "rerun_required", "widget cleanup and rebinding"),
    },
    "docs/specs/requirements/45_NODE_EXECUTION_MODEL.md": {
        "REQ-NODE-026": ("session-owned", "output_mode=memory", "temp transport bundle", "rerun-required"),
        "AC-REQ-NODE-026-01": (
            "output_mode=memory",
            "rerun-required reopen blocking",
            "post-rerun restoration",
        ),
    },
    "docs/specs/requirements/50_EXECUTION_ENGINE.md": {
        "REQ-EXEC-013": (
            "ViewerBackendRegistry",
            "ViewerSessionService",
            "backend_id",
            "transport_revision",
            "live_open_status",
            "live_open_blocker",
        ),
        "AC-REQ-EXEC-013-01": (
            "temp-bundle reuse and cleanup",
            "rerun-required blocker projection",
            "queue-safe viewer payloads",
        ),
    },
    "docs/specs/requirements/60_PERSISTENCE.md": {
        "REQ-PERSIST-020": (".sfe", "temp transport bundles", "transport revisions", "serialized project artifacts"),
        "AC-REQ-PERSIST-020-01": (
            "rerun-required projection",
            "temp bundles",
            "dene3.sfe",
            "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/70_INTEGRATIONS.md": {
        "REQ-INT-008": ("ansys-dpf-core", "pyvistaqt", "dpf.viewer", "dpf_embedded"),
        "AC-REQ-INT-008-01": ("viewer-backend", "binder", "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md"),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-023": (
            "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK",
            "ViewerHostService",
            "rerun-required reopen behavior",
            "traceability coverage",
        ),
        "REQ-QA-024": (
            "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
            "dene3.sfe",
            "desktop-only validation",
            "traceability gate",
        ),
        "AC-REQ-QA-023-01": (
            "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
            CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_TEST_COMMAND,
            CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_COMMAND,
        ),
        "AC-REQ-QA-024-01": (
            CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_TEST_COMMAND,
            CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_COMMAND,
            "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
        ),
    },
}

CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-ARCH-016": (
        "viewer_backend.py",
        "viewer_session_backend.py",
        "viewer_host_service.py",
        "viewer_widget_binder.py",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "AC-REQ-ARCH-016-01": (
        "test_execution_viewer_protocol.py",
        "test_viewer_host_service.py",
        "test_dpf_viewer_widget_binder.py",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "REQ-UI-032": (
        "viewer_session_bridge.py",
        "viewer_host_service.py",
        "dpf_viewer_widget_binder.py",
        "GraphViewerSurface.qml",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "AC-REQ-UI-032-01": (
        "test_viewer_surface_contract.py",
        "test_viewer_surface_host.py",
        "test_dpf_viewer_widget_binder.py",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "REQ-NODE-026": (
        "viewer_session_service.py",
        "project_session_services.py",
        "run_controller.py",
        "GraphViewerSurface.qml",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "AC-REQ-NODE-026-01": (
        "test_execution_worker.py",
        "test_shell_run_controller.py",
        "test_project_session_controller_unit.py",
        "test_shell_project_session_controller.py",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "REQ-EXEC-013": (
        "viewer_backend.py",
        "materialization.py",
        "viewer_session_backend.py",
        "test_execution_viewer_protocol.py",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "AC-REQ-EXEC-013-01": (
        "test_execution_viewer_service.py",
        "test_execution_worker.py",
        "test_dpf_materialization.py",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "REQ-PERSIST-020": (
        "project_session_services.py",
        "viewer_session_backend.py",
        "fixture_paths.py",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "AC-REQ-PERSIST-020-01": (
        "test_project_session_controller_unit.py",
        "test_shell_project_session_controller.py",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "REQ-INT-008": (
        "ansys_dpf.py",
        "ansys_dpf_viewer_adapter.py",
        "dpf_viewer_widget_binder.py",
        "ea_node_editor.spec",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "AC-REQ-INT-008-01": (
        "test_dpf_compute_nodes.py",
        "test_dpf_viewer_widget_binder.py",
        "test_packaging_configuration.py",
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "REQ-QA-023": (
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
        "test_execution_viewer_protocol.py",
        "test_dpf_materialization.py",
        "test_viewer_host_service.py",
        "test_shell_project_session_controller.py",
    ),
    "REQ-QA-024": (
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
        "tests/test_traceability_checker.py",
        "scripts/check_traceability.py",
    ),
    "AC-REQ-QA-023-01": (
        CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_COMMAND,
        CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_COMMAND,
        CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_BRIDGE_COMMAND,
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
    "AC-REQ-QA-024-01": (
        CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_TEST_COMMAND,
        CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_COMMAND,
        "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
    ),
}

CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX_TOKENS = (
    "Cross-Process Viewer Backend Framework QA Matrix",
    "## Locked Scope",
    "backend_id",
    "ViewerHostService",
    "ViewerWidgetBinderRegistry",
    "dpf_embedded",
    "output_mode=memory",
    CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_COMMAND,
    CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_SERVICE_COMMAND,
    CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_MATERIALIZATION_COMMAND,
    CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P03_COMMAND,
    CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_COMMAND,
    CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_BRIDGE_COMMAND,
    CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_SURFACE_COMMAND,
    CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_TEST_COMMAND,
    CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_COMMAND,
    "dene3.sfe",
    "rerun-required blocker",
    "transport_revision",
    "## Residual Desktop-Only Validation",
)
GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md"
)
GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P01_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py "
    "tests/graph_track_b/qml_preference_bindings.py "
    "tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q"
)
GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P02_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/graph_track_b/qml_preference_bindings.py tests/test_flow_edge_labels.py "
    "--ignore=venv -q"
)
GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_TEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_traceability.py"
)

GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-033": (
            "Crossing style",
            "graphics.canvas.edge_crossing_style",
            "none",
            "gap_break",
            "global-only",
        ),
        "AC-REQ-UI-033-01": (
            "Crossing style",
            "Gap break",
            "app-wide choice",
            "hit testing",
            "stored graph data",
        ),
    },
    "docs/specs/requirements/80_PERFORMANCE.md": {
        "REQ-PERF-009": (
            "graphics.canvas.edge_crossing_style",
            "screen space",
            "previewed and selected edges",
            "visible-edge order",
            "max_performance",
        ),
        "AC-REQ-PERF-009-01": (
            "qml_preference_bindings.py",
            "test_flow_edge_labels.py",
            "GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-026": (
            "GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md",
            "edge_crossing_style",
            "manual desktop checks",
            "desktop-only validation",
            "traceability gate",
        ),
        "AC-REQ-QA-026-01": (
            GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P01_COMMAND,
            GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P02_COMMAND,
            GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_TEST_COMMAND,
            GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_COMMAND,
            "GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md",
        ),
    },
}

GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-UI-033": (
        "graphics_settings_dialog.py",
        "GraphCanvas.qml",
        "EdgeLayer.qml",
        "tests/test_graphics_settings_preferences.py",
    ),
    "AC-REQ-UI-033-01": (
        "tests/test_graphics_settings_dialog.py",
        "tests/graph_track_b/qml_preference_bindings.py",
        "tests/main_window_shell/shell_basics_and_search.py",
    ),
    "REQ-PERF-009": (
        "EdgeMath.js",
        "EdgeLayer.qml",
        "tests/test_flow_edge_labels.py",
        "GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md",
    ),
    "AC-REQ-PERF-009-01": (
        "tests/graph_track_b/qml_preference_bindings.py",
        "tests/test_flow_edge_labels.py",
        "GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md",
    ),
    "REQ-QA-026": (
        "GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md",
        "tests/test_traceability_checker.py",
        "scripts/check_traceability.py",
    ),
    "AC-REQ-QA-026-01": (
        GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_TEST_COMMAND,
        GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_COMMAND,
        "GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md",
    ),
}

GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX_TOKENS = (
    "Global Gap Break Edge Crossing Variant QA Matrix",
    "## Locked Scope",
    "edge_crossing_style",
    "Crossing style",
    GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P01_COMMAND,
    GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P02_COMMAND,
    GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_TEST_COMMAND,
    GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_COMMAND,
    "P01_edge_crossing_preference_pipeline_WRAPUP.md",
    "P02_gap_break_renderer_adoption_WRAPUP.md",
    "render-only decoration",
    "## Remaining Manual Smoke Checks",
    "## Residual Desktop-Only Validation",
    "max_performance",
)
NODE_EXECUTION_VISUALIZATION_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md"
)
NODE_EXECUTION_VISUALIZATION_P01_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_run_controller_unit.py tests/main_window_shell/bridge_contracts.py "
    "-k node_execution_bridge --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_P02_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_main_window_shell.py -k node_execution_canvas --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_P03_SHELL_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_shell_run_controller.py -k node_execution_visualization --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_P03_HOST_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/test_passive_graph_surface_host.py -k node_execution_visualization --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_P03_QML_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
    "tests/graph_track_b/qml_preference_bindings.py -k node_execution_visualization --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_TRACEABILITY_TEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_TRACEABILITY_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_traceability.py"
)

NODE_EXECUTION_VISUALIZATION_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-034": (
            "blue pulse halo",
            "green border",
            "failure red",
            "inactive workspaces",
            "QML-local",
        ),
        "AC-REQ-UI-034-01": (
            "blue pulse halo",
            "green completed flash",
            "failure red priority",
            "QML-local elapsed timer",
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/45_NODE_EXECUTION_MODEL.md": {
        "REQ-NODE-027": (
            "node_started",
            "node_completed",
            "run_started",
            "run_failed",
            "no `.sfe` persistence",
        ),
        "AC-REQ-NODE-027-01": (
            "node_started",
            "active-workspace bridge filtering",
            "run_started",
            "run_stopped",
            "non-fatal `run_failed`",
        ),
    },
    "docs/specs/requirements/80_PERFORMANCE.md": {
        "REQ-PERF-010": (
            "QML-local",
            "no Python monotonic timestamp bridge",
            "render-active",
            "hit-testing contracts",
            "cached scene payload structure",
        ),
        "AC-REQ-PERF-010-01": (
            "test_passive_graph_surface_host.py",
            "qml_preference_bindings.py",
            "QML-local timer constraint",
            "geometry",
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-027": (
            "NODE_EXECUTION_VISUALIZATION",
            "run-state projection",
            "active-workspace bridge filtering",
            "QML-local timer",
            "retained packet-owned reruns",
        ),
        "REQ-QA-028": (
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
            "A+E-hybrid visual baseline",
            "QML-local timer constraint",
            "traceability gate",
        ),
        "AC-REQ-QA-027-01": (
            NODE_EXECUTION_VISUALIZATION_P01_COMMAND,
            NODE_EXECUTION_VISUALIZATION_P02_COMMAND,
            NODE_EXECUTION_VISUALIZATION_P03_SHELL_COMMAND,
            NODE_EXECUTION_VISUALIZATION_P03_HOST_COMMAND,
            NODE_EXECUTION_VISUALIZATION_P03_QML_COMMAND,
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        ),
        "AC-REQ-QA-028-01": (
            NODE_EXECUTION_VISUALIZATION_TRACEABILITY_TEST_COMMAND,
            NODE_EXECUTION_VISUALIZATION_TRACEABILITY_COMMAND,
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        ),
    },
}

NODE_EXECUTION_VISUALIZATION_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-UI-034": (
        "run_controller.py",
        "GraphCanvas.qml",
        "GraphNodeChromeBackground.qml",
        "GraphNodeHost.qml",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "AC-REQ-UI-034-01": (
        "tests/test_shell_run_controller.py",
        "tests/test_passive_graph_surface_host.py",
        "tests/graph_track_b/qml_preference_bindings.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "REQ-NODE-027": (
        "state.py",
        "run_controller.py",
        "graph_canvas_state_bridge.py",
        "tests/test_run_controller_unit.py",
        "bridge_contracts.py",
    ),
    "AC-REQ-NODE-027-01": (
        "tests/test_run_controller_unit.py",
        "tests/main_window_shell/bridge_contracts.py",
        "tests/test_main_window_shell.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "REQ-PERF-010": (
        "GraphNodeChromeBackground.qml",
        "GraphNodeHost.qml",
        "tests/test_passive_graph_surface_host.py",
        "tests/graph_track_b/qml_preference_bindings.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "AC-REQ-PERF-010-01": (
        "tests/test_passive_graph_surface_host.py",
        "tests/graph_track_b/qml_preference_bindings.py",
        "tests/test_shell_run_controller.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "REQ-QA-027": (
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        "docs/specs/requirements/20_UI_UX.md",
        "docs/specs/requirements/45_NODE_EXECUTION_MODEL.md",
        "tests/test_traceability_checker.py",
        "scripts/check_traceability.py",
    ),
    "REQ-QA-028": (
        "docs/node_execution_visualization_alternatives.html",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        "tests/test_traceability_checker.py",
        "scripts/check_traceability.py",
    ),
    "AC-REQ-QA-027-01": (
        NODE_EXECUTION_VISUALIZATION_P01_COMMAND,
        NODE_EXECUTION_VISUALIZATION_P02_COMMAND,
        NODE_EXECUTION_VISUALIZATION_P03_SHELL_COMMAND,
        NODE_EXECUTION_VISUALIZATION_P03_HOST_COMMAND,
        NODE_EXECUTION_VISUALIZATION_P03_QML_COMMAND,
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "AC-REQ-QA-028-01": (
        NODE_EXECUTION_VISUALIZATION_TRACEABILITY_TEST_COMMAND,
        NODE_EXECUTION_VISUALIZATION_TRACEABILITY_COMMAND,
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
}

NODE_EXECUTION_VISUALIZATION_QA_MATRIX_TOKENS = (
    "Node Execution Visualization QA Matrix",
    "## Locked Scope",
    "docs/node_execution_visualization_alternatives.html",
    "A+E-hybrid visual baseline",
    "blue pulse halo",
    "green border",
    "QML-local elapsed timer",
    NODE_EXECUTION_VISUALIZATION_P01_COMMAND,
    NODE_EXECUTION_VISUALIZATION_P02_COMMAND,
    NODE_EXECUTION_VISUALIZATION_P03_SHELL_COMMAND,
    NODE_EXECUTION_VISUALIZATION_P03_HOST_COMMAND,
    NODE_EXECUTION_VISUALIZATION_P03_QML_COMMAND,
    NODE_EXECUTION_VISUALIZATION_TRACEABILITY_TEST_COMMAND,
    NODE_EXECUTION_VISUALIZATION_TRACEABILITY_COMMAND,
    "P01_run_state_execution_projection_WRAPUP.md",
    "P02_graph_canvas_execution_bindings_WRAPUP.md",
    "P03_node_chrome_execution_highlights_WRAPUP.md",
    "## Remaining Manual A+E-Hybrid Visual Checks",
    "## Residual Desktop-Only Validation",
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
ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX = (
    REPO_ROOT / manifest.ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC
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
ARCHITECTURE_RESIDUAL_REFACTOR_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-029": manifest.QA_ACCEPTANCE_REQUIREMENT_TOKENS["REQ-QA-029"],
        "AC-REQ-QA-029-01": manifest.QA_ACCEPTANCE_REQUIREMENT_TOKENS["AC-REQ-QA-029-01"],
    },
}

ARCHITECTURE_RESIDUAL_REFACTOR_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-QA-029": manifest.TRACEABILITY_ROW_REQUIRED_TOKENS["REQ-QA-029"],
    "AC-REQ-QA-029-01": manifest.TRACEABILITY_ROW_REQUIRED_TOKENS["AC-REQ-QA-029-01"],
}

ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_TOKENS = (
    manifest.ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_REQUIRED_TOKENS
)
UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md"
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
UI_CONTEXT_SCALABILITY_REFACTOR_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
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
    },
}
UI_CONTEXT_SCALABILITY_REFACTOR_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-QA-030": (
        "docs/specs/INDEX.md",
        "docs/specs/requirements/90_QA_ACCEPTANCE.md",
        "docs/specs/requirements/TRACEABILITY_MATRIX.md",
        "docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md",
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
}
UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_TOKENS = (
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
        self.assertTrue(
            set(self.manifest.PROOF_AUDIT_REQUIRED_ARTIFACTS).issubset(self.checker.REQUIRED_ARTIFACTS)
        )
        self.assertIn(
            "docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md",
            self.checker.REQUIRED_ARTIFACTS,
        )
        self.assertEqual(
            (
                "docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json",
                "docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md",
                "docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md",
                "docs/specs/work_packets/ui_context_scalability_refactor/SHELL_PACKET.md",
                "docs/specs/work_packets/ui_context_scalability_refactor/PRESENTERS_PACKET.md",
                "docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SCENE_PACKET.md",
                "docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md",
                "docs/specs/work_packets/ui_context_scalability_refactor/EDGE_RENDERING_PACKET.md",
                "docs/specs/work_packets/ui_context_scalability_refactor/VIEWER_PACKET.md",
            ),
            self.checker.P08_REQUIRED_ARTIFACTS,
        )
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
        required_paths.update(self.checker.P08_REQUIRED_ARTIFACTS)
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

    def test_audit_repository_reports_ui_context_closeout_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            replace_text(
                repo_root / "docs/specs/INDEX.md",
                "UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md",
                "UI_CONTEXT_SCALABILITY_REFACTOR_MATRIX.md",
            )
            remove_token_from_requirement_line(
                repo_root / self.manifest.QA_ACCEPTANCE_DOC,
                "REQ-QA-030",
                "CONTEXT_BUDGET_RULES.json",
            )
            update_markdown_table_result(
                repo_root / "docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md",
                UI_CONTEXT_SCALABILITY_REFACTOR_MARKDOWN_COMMAND,
                "Pending",
                "Markdown links were not rerun after the UI closeout refresh",
            )
            remove_token_from_traceability_row(
                repo_root / self.manifest.TRACEABILITY_MATRIX_DOC,
                "REQ-QA-030",
                "tests/test_run_verification.py",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "docs/specs/INDEX.md: spec index registration missing fact: "
            "UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md",
            issues,
        )
        self.assertIn(
            f"{self.manifest.QA_ACCEPTANCE_DOC}: requirement REQ-QA-030 missing fact: "
            "CONTEXT_BUDGET_RULES.json",
            issues,
        )
        self.assertIn(
            "docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md: "
            "2026-04-05 Execution Results command "
            f"{UI_CONTEXT_SCALABILITY_REFACTOR_MARKDOWN_COMMAND} has unexpected result: Pending",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACEABILITY_MATRIX_DOC}: row REQ-QA-030 missing implementation "
            "artifact text: tests/test_run_verification.py",
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

    def test_cross_process_viewer_backend_framework_docs_record_closeout_scope_tokens(self) -> None:
        for (
            relative_path,
            requirement_tokens,
        ) in CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_cross_process_viewer_backend_framework_traceability_rows_reference_packet_artifacts(
        self,
    ) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_cross_process_viewer_backend_framework_qa_matrix_records_commands_and_manual_checks(
        self,
    ) -> None:
        text = CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_global_gap_break_edge_crossing_variant_docs_record_closeout_scope_tokens(self) -> None:
        for (
            relative_path,
            requirement_tokens,
        ) in GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_global_gap_break_edge_crossing_variant_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_global_gap_break_edge_crossing_variant_qa_matrix_records_commands_and_manual_checks(self) -> None:
        text = GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_node_execution_visualization_docs_record_closeout_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in NODE_EXECUTION_VISUALIZATION_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_node_execution_visualization_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in NODE_EXECUTION_VISUALIZATION_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_node_execution_visualization_qa_matrix_records_commands_and_manual_checks(self) -> None:
        text = NODE_EXECUTION_VISUALIZATION_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in NODE_EXECUTION_VISUALIZATION_QA_MATRIX_TOKENS:
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

    def test_architecture_residual_refactor_docs_record_closeout_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in ARCHITECTURE_RESIDUAL_REFACTOR_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_architecture_residual_refactor_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in ARCHITECTURE_RESIDUAL_REFACTOR_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_architecture_residual_refactor_qa_matrix_records_commands_and_boundaries(self) -> None:
        text = ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_ui_context_scalability_refactor_docs_record_closeout_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in UI_CONTEXT_SCALABILITY_REFACTOR_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_ui_context_scalability_refactor_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in UI_CONTEXT_SCALABILITY_REFACTOR_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_ui_context_scalability_refactor_qa_matrix_records_commands_and_guardrails(self) -> None:
        text = UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX_TOKENS:
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
