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

DPF_OPERATOR_PLUGIN_BACKEND_REVIEW = (
    REPO_ROOT / "docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md"
)
DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md"
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

DPF_OPERATOR_PLUGIN_BACKEND_PUBLIC_DOC_TOKENS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "DPF operator backend review",
        "DPF operator backend QA matrix",
        "ansys-dpf-core",
        "locked unavailable-add-on projections",
    ),
    "ARCHITECTURE.md": (
        "## DPF operator backend preparation",
        "`ansys-dpf-core` remains optional",
        "DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md",
        "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
        "locked unavailable-add-on projections",
    ),
    "docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md": (
        "## Delivered Backend Contract",
        "## Explicit Deferrals For Later Operator Rollout",
        "plugin_loader.py",
        "ansys_dpf_catalog.py",
        "graph_scene_payload_builder.py",
        "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
        "Non-operator `ansys.dpf.core` reflection",
    ),
}

DPF_OPERATOR_PLUGIN_BACKEND_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/70_INTEGRATIONS.md": {
        "REQ-INT-009": (
            "ansys-dpf-core",
            "register shipped DPF descriptors",
            "normalize operator metadata",
            "generic DPF runtime adapter",
            "locked unavailable-add-on surfaces",
            "non-operator `ansys.dpf.core` reflection",
        ),
        "AC-REQ-INT-009-01": (
            "DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md",
            "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
            "plugin-loader",
            "locked unavailable-add-on projection",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-035": (
            "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR",
            "optional plugin lifecycle",
            "operator metadata and generated ports",
            "generic operator-backed runtime invocation",
            "unavailable-backend node projection",
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
    },
}

DPF_OPERATOR_PLUGIN_BACKEND_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-INT-009": (
        "plugin_loader.py",
        "plugin_contracts.py",
        "ansys_dpf_catalog.py",
        "operations.py",
        "project_codec.py",
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

DPF_OPERATOR_PLUGIN_BACKEND_QA_MATRIX_TOKENS = (
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

ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md"
)
ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P01_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py "
    r"tests/test_dpf_node_catalog.py --ignore=venv -q"
)
ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P02_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py "
    r"tests/test_dpf_contracts.py --ignore=venv -q"
)
ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P03_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_dpf_library_taxonomy.py "
    r"tests/test_dpf_node_catalog.py tests/test_registry_filters.py "
    r"--ignore=venv -q"
)
ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P04_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest "
    r"tests/test_dpf_generated_operator_catalog.py tests/test_dpf_node_catalog.py "
    r"--ignore=venv -q"
)
ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P05_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest "
    r"tests/test_dpf_generated_helper_catalog.py tests/test_dpf_workflow_helpers.py "
    r"--ignore=venv -q"
)
ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P06_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_dpf_materialization.py "
    r"tests/test_dpf_runtime_service.py tests/test_serializer.py "
    r"tests/test_serializer_schema_migration.py --ignore=venv -q"
)
ANSYS_DPF_FULL_PLUGIN_ROLLOUT_CLOSEOUT_PYTEST_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py "
    r"tests/test_markdown_hygiene.py --ignore=venv -q"
)
ANSYS_DPF_FULL_PLUGIN_ROLLOUT_TRACEABILITY_COMMAND = (
    r".\venv\Scripts\python.exe scripts/check_traceability.py"
)

ANSYS_DPF_FULL_PLUGIN_ROLLOUT_PUBLIC_DOC_TOKENS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "workflow-first",
        "Ansys DPF > Inputs",
        "Ansys DPF > Helpers",
        "Ansys DPF > Operators",
        "ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
    ),
    "ARCHITECTURE.md": (
        "workflow-first and descriptor-driven",
        "version-aware",
        "Ansys DPF > Operators > <Family>",
        "generic object handles",
        "ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
    ),
}

ANSYS_DPF_FULL_PLUGIN_ROLLOUT_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/70_INTEGRATIONS.md": {
        "REQ-INT-008": (
            '("Ansys DPF", "Inputs")',
            '("Ansys DPF", "Workflow")',
            '("Ansys DPF", "Helpers", ...)',
            '("Ansys DPF", "Operators", ...)',
            '("Ansys DPF", "Advanced", "Raw API Mirror")',
        ),
        "REQ-INT-009": (
            "version-aware plugin lifecycle",
            "generated operator and helper descriptors",
            "generic object handles",
            "locked unavailable-add-on surfaces",
            "non-operator `ansys.dpf.core` reflection",
        ),
        "AC-REQ-INT-008-01": (
            "generated operator and helper",
            "Ansys DPF > Inputs",
            "ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
        ),
        "AC-REQ-INT-009-01": (
            "ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
            "generated operator/helper",
            "helper object-handle portability",
            "locked unavailable-add-on projection",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-038": (
            "ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
            "`P00` through `P06`",
            "`P07` traceability and markdown-hygiene closeout commands",
            "workflow-first `Ansys DPF` family taxonomy",
            "version-aware plugin lifecycle evidence",
            "`Ansys DPF > Advanced > Raw API Mirror` deferral",
        ),
        "AC-REQ-QA-038-01": (
            ANSYS_DPF_FULL_PLUGIN_ROLLOUT_CLOSEOUT_PYTEST_COMMAND,
            ANSYS_DPF_FULL_PLUGIN_ROLLOUT_TRACEABILITY_COMMAND,
            "ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
        ),
    },
}

ANSYS_DPF_FULL_PLUGIN_ROLLOUT_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-INT-008": (
        "ansys_dpf_taxonomy.py",
        "ansys_dpf_operator_catalog.py",
        "ansys_dpf_helper_catalog.py",
        "tests/test_dpf_library_taxonomy.py",
        "docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
    ),
    "AC-REQ-INT-008-01": (
        "tests/test_dpf_generated_operator_catalog.py",
        "tests/test_dpf_generated_helper_catalog.py",
        "tests/test_packaging_configuration.py",
        "docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
    ),
    "REQ-INT-009": (
        "settings.py",
        "app_preferences.py",
        "bootstrap.py",
        "ansys_dpf_helper_adapters.py",
        "docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
    ),
    "AC-REQ-INT-009-01": (
        "tests/test_app_preferences.py",
        "tests/test_dpf_contracts.py",
        "tests/test_dpf_materialization.py",
        "tests/test_serializer.py",
        "docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
    ),
    "REQ-QA-038": (
        "ARCHITECTURE.md",
        "README.md",
        "docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
        "tests/test_traceability_checker.py",
        "tests/test_markdown_hygiene.py",
        "scripts/check_traceability.py",
    ),
    "AC-REQ-QA-038-01": (
        ANSYS_DPF_FULL_PLUGIN_ROLLOUT_CLOSEOUT_PYTEST_COMMAND,
        ANSYS_DPF_FULL_PLUGIN_ROLLOUT_TRACEABILITY_COMMAND,
        "docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md",
    ),
}

ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX_TOKENS = (
    "ANSYS DPF Full Plugin Rollout QA Matrix",
    "## Locked Scope",
    "## Retained Automated Verification",
    "## Final Closeout Commands",
    "## 2026-04-15 Execution Results",
    "## Retained Manual Evidence",
    "## Residual Risks",
    "workflow-first",
    "version-aware",
    "Ansys DPF > Advanced > Raw API Mirror",
    "generic object handles",
    "read-only placeholders",
    "P00_bootstrap_WRAPUP.md",
    "P03_family_taxonomy_WRAPUP.md",
    "P06_runtime_persistence_portability_WRAPUP.md",
    ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P01_COMMAND,
    ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P02_COMMAND,
    ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P03_COMMAND,
    ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P04_COMMAND,
    ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P05_COMMAND,
    ANSYS_DPF_FULL_PLUGIN_ROLLOUT_P06_COMMAND,
    ANSYS_DPF_FULL_PLUGIN_ROLLOUT_CLOSEOUT_PYTEST_COMMAND,
    ANSYS_DPF_FULL_PLUGIN_ROLLOUT_TRACEABILITY_COMMAND,
)

ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md"
)
ADDON_MANAGER_BACKEND_PREPARATION_P01_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py --ignore=venv -q"
)
ADDON_MANAGER_BACKEND_PREPARATION_P02_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py "
    r"tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q"
)
ADDON_MANAGER_BACKEND_PREPARATION_P03_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_serializer.py "
    r"tests/test_serializer_schema_migration.py tests/test_registry_validation.py "
    r"tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q"
)
ADDON_MANAGER_BACKEND_PREPARATION_P04_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py "
    r"tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py "
    r"tests/test_passive_graph_surface_host.py --ignore=venv -q"
)
ADDON_MANAGER_BACKEND_PREPARATION_P05_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py "
    r"tests/test_dpf_generated_helper_catalog.py tests/test_dpf_generated_operator_catalog.py "
    r"tests/test_dpf_operator_help_lookup.py --ignore=venv -q"
)
ADDON_MANAGER_BACKEND_PREPARATION_P06_COMMAND = (
    "./venv/Scripts/python.exe -m pytest tests/test_dpf_runtime_service.py "
    "tests/test_execution_viewer_service.py tests/test_viewer_host_service.py "
    "tests/test_dpf_viewer_node.py tests/test_dpf_viewer_widget_binder.py "
    "--ignore=venv -q"
)
ADDON_MANAGER_BACKEND_PREPARATION_P07_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py "
    r"tests/main_window_shell/shell_basics_and_search.py "
    r"tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q"
)
ADDON_MANAGER_BACKEND_PREPARATION_CLOSEOUT_PYTEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py "
    "tests/test_markdown_hygiene.py --ignore=venv -q"
)
ADDON_MANAGER_BACKEND_PREPARATION_TRACEABILITY_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_traceability.py"
)
ADDON_MANAGER_BACKEND_PREPARATION_MARKDOWN_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_markdown_links.py"
)
ADDON_MANAGER_BACKEND_PREPARATION_INDEX_TOKENS = (
    "[ADDON_MANAGER_BACKEND_PREPARATION Work Packet Manifest](work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_MANIFEST.md)",
    "[ADDON_MANAGER_BACKEND_PREPARATION Status Ledger](work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md)",
    "[ADDON_MANAGER_BACKEND_PREPARATION QA Matrix](perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md)",
)
ADDON_MANAGER_BACKEND_PREPARATION_PUBLIC_DOC_TOKENS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "Add-On Manager",
        "Variant 4 inspector-style drawer",
        "`hot_apply` or `restart_required`",
        "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "ARCHITECTURE.md": (
        "## Add-on backend preparation",
        "Variant 4 inspector-style right drawer",
        "locked Mockup B surfaces",
        "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
}
ADDON_MANAGER_BACKEND_PREPARATION_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-041": (
            "Add-On Manager",
            "Variant 4 inspector-style right drawer",
            "focus_addon_id",
            "`About` / `Dependencies` / `Nodes` / `Changelog`",
        ),
        "REQ-UI-042": (
            "locked Mockup B placeholders",
            "`LOCKED` badge",
            "`Load missing add-ons`",
            "drag, and resize mutations",
        ),
        "AC-REQ-UI-041-01": (
            "Variant 4 drawer fidelity",
            "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
        ),
        "AC-REQ-UI-042-01": (
            "locked placeholders",
            "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/60_PERSISTENCE.md": {
        "REQ-PERSIST-023": (
            "pending-restart intent",
            "locked unavailable-add-on projections",
            "rebind them when the add-on returns",
            "projection payloads",
        ),
        "AC-REQ-PERSIST-023-01": (
            "plugin-loader",
            "locked projection",
            "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/70_INTEGRATIONS.md": {
        "REQ-INT-011": (
            "stable id, name, version, category, dependency, and availability facts",
            "`hot_apply` or `restart_required`",
            "open-manager requests",
            "add-on ids",
        ),
        "REQ-INT-012": (
            "first repo-local `hot_apply` add-on",
            "`ea_node_editor.addons.ansys_dpf`",
            "locked unavailable-add-on projections",
            "full app restart",
        ),
        "AC-REQ-INT-011-01": (
            "generic add-on catalog",
            "shell focus-target plumbing",
            "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
        ),
        "AC-REQ-INT-012-01": (
            "repo-local `ANSYS DPF` add-on package",
            "hot-apply lifecycle",
            "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-040": (
            "ADDON_MANAGER_BACKEND_PREPARATION",
            "generic add-on contract and persisted state model",
            "Mockup B locked-node behavior",
            "Variant 4 manager surface",
        ),
        "REQ-QA-041": (
            "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
            "`P01` through `P07`",
            "`P08` traceability, markdown-hygiene, and markdown-link closeout commands",
            "menu open/toggle/projection/DPF flows",
        ),
        "AC-REQ-QA-040-01": (
            ADDON_MANAGER_BACKEND_PREPARATION_P01_COMMAND,
            ADDON_MANAGER_BACKEND_PREPARATION_P07_COMMAND,
            "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
        ),
        "AC-REQ-QA-041-01": (
            ADDON_MANAGER_BACKEND_PREPARATION_CLOSEOUT_PYTEST_COMMAND,
            ADDON_MANAGER_BACKEND_PREPARATION_TRACEABILITY_COMMAND,
            ADDON_MANAGER_BACKEND_PREPARATION_MARKDOWN_COMMAND,
            "ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
        ),
    },
}
ADDON_MANAGER_BACKEND_PREPARATION_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-UI-041": (
        "window_actions.py",
        "addon_manager_presenter.py",
        "AddOnManagerPane.qml",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "AC-REQ-UI-041-01": (
        "tests/test_main_window_shell.py",
        "tests/main_window_shell/shell_basics_and_search.py",
        "tests/main_window_shell/bridge_qml_boundaries.py",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "REQ-UI-042": (
        "graph/normalization.py",
        "GraphNodeHost.qml",
        "GraphNodeHeaderLayer.qml",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "AC-REQ-UI-042-01": (
        "tests/test_serializer.py",
        "tests/test_graph_surface_input_contract.py",
        "tests/test_graph_surface_input_controls.py",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "REQ-PERSIST-023": (
        "app_preferences.py",
        "settings.py",
        "project_codec.py",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "AC-REQ-PERSIST-023-01": (
        "tests/test_plugin_loader.py",
        "tests/test_serializer_schema_migration.py",
        "tests/test_registry_validation.py",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "REQ-INT-011": (
        "addons/catalog.py",
        "plugin_contracts.py",
        "plugin_loader.py",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "AC-REQ-INT-011-01": (
        "tests/test_plugin_loader.py",
        "tests/test_main_window_shell.py",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "REQ-INT-012": (
        "ansys_dpf/catalog.py",
        "hot_apply.py",
        "worker_services.py",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "AC-REQ-INT-012-01": (
        "tests/test_dpf_node_catalog.py",
        "tests/test_dpf_runtime_service.py",
        "tests/test_viewer_host_service.py",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "REQ-QA-040": (
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
        "20_UI_UX.md",
        "70_INTEGRATIONS.md",
        "tests/test_traceability_checker.py",
        "scripts/check_traceability.py",
    ),
    "AC-REQ-QA-040-01": (
        ADDON_MANAGER_BACKEND_PREPARATION_P01_COMMAND,
        ADDON_MANAGER_BACKEND_PREPARATION_P06_COMMAND,
        ADDON_MANAGER_BACKEND_PREPARATION_P07_COMMAND,
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
    "REQ-QA-041": (
        "ARCHITECTURE.md",
        "README.md",
        "docs/specs/INDEX.md",
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
        "tests/test_markdown_hygiene.py",
        "scripts/check_markdown_links.py",
    ),
    "AC-REQ-QA-041-01": (
        ADDON_MANAGER_BACKEND_PREPARATION_CLOSEOUT_PYTEST_COMMAND,
        ADDON_MANAGER_BACKEND_PREPARATION_TRACEABILITY_COMMAND,
        ADDON_MANAGER_BACKEND_PREPARATION_MARKDOWN_COMMAND,
        "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
    ),
}
ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX_TOKENS = (
    "Add-On Manager Backend Preparation QA Matrix",
    "## Locked Scope",
    "## Retained Automated Verification",
    "## Final Closeout Commands",
    "## 2026-04-20 Execution Results",
    "## Remaining Manual Desktop Checks",
    "## Residual Risks",
    "Variant 4 inspector-style right drawer",
    "Mockup B placeholders",
    "`hot_apply`",
    "`restart_required`",
    "P01_addon_contracts_and_state_model_WRAPUP.md",
    "P07_addon_manager_variant4_surface_WRAPUP.md",
    ADDON_MANAGER_BACKEND_PREPARATION_P01_COMMAND,
    ADDON_MANAGER_BACKEND_PREPARATION_P02_COMMAND,
    ADDON_MANAGER_BACKEND_PREPARATION_P03_COMMAND,
    ADDON_MANAGER_BACKEND_PREPARATION_P04_COMMAND,
    ADDON_MANAGER_BACKEND_PREPARATION_P05_COMMAND,
    ADDON_MANAGER_BACKEND_PREPARATION_P06_COMMAND,
    ADDON_MANAGER_BACKEND_PREPARATION_P07_COMMAND,
    ADDON_MANAGER_BACKEND_PREPARATION_CLOSEOUT_PYTEST_COMMAND,
    ADDON_MANAGER_BACKEND_PREPARATION_TRACEABILITY_COMMAND,
    ADDON_MANAGER_BACKEND_PREPARATION_MARKDOWN_COMMAND,
)

COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX = (
    REPO_ROOT / manifest.COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX_DOC
)
COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_PYTEST_COMMAND = (
    manifest.COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_PYTEST_COMMAND
)
COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_TRACEABILITY_COMMAND = (
    manifest.COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_TRACEABILITY_COMMAND
)
COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_MARKDOWN_COMMAND = (
    manifest.COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_MARKDOWN_COMMAND
)
COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_INDEX_TOKENS = (
    "COREX_NO_LEGACY_ARCHITECTURE_CLEANUP QA Matrix",
    "COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md",
)
COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_PUBLIC_DOC_TOKENS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md",
        "ea_node_editor.bootstrap",
        "descriptor-first",
        "locked unavailable-add-on projections",
        "Constructor probing and class scanning are not part",
    ),
    "ARCHITECTURE.md": (
        "## Current focused contracts",
        "focused bridges",
        "current-schema",
        "descriptor-only",
        "snapshot-only",
        "typed transport/session",
        "ea_node_editor.ui.perf.performance_harness",
        "COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md",
    ),
}
COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/10_ARCHITECTURE.md": {
        "REQ-ARCH-008": ("current-schema-normalization", "schema validation", "normalization"),
    },
    "docs/specs/requirements/40_NODE_SDK.md": {
        "REQ-NODE-003": ("category_path", "derived display labels", "not a compatibility alias"),
        "REQ-NODE-007": ("category_path=", "derived display labels", "presentation only"),
        "AC-REQ-NODE-003-01": ("derived category display", "descendant nodes"),
    },
    "docs/specs/requirements/60_PERSISTENCE.md": {
        "REQ-PERSIST-004": ("current `.sfe` schema", "pre-current documents"),
        "REQ-PERSIST-005": ("current-schema", "before model construction"),
        "REQ-PERSIST-023": ("locked unavailable-add-on projections", "projection payloads"),
        "AC-REQ-PERSIST-023-01": ("current-schema", "unavailable-add-on locked projection"),
    },
    "docs/specs/requirements/70_INTEGRATIONS.md": {
        "REQ-INT-009": ("descriptor/add-on catalog", "locked unavailable-add-on surfaces"),
        "AC-REQ-INT-009-01": ("locked unavailable-add-on projection",),
        "REQ-INT-012": ("locked unavailable-add-on projections",),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-042": manifest.QA_ACCEPTANCE_REQUIREMENT_TOKENS["REQ-QA-042"],
        "AC-REQ-QA-042-01": manifest.QA_ACCEPTANCE_REQUIREMENT_TOKENS["AC-REQ-QA-042-01"],
    },
}
COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-INT-006": (
        "explicit public built-ins export",
        "descriptor aggregation",
        "INTEGRATION_NODE_DESCRIPTORS",
    ),
    "REQ-QA-042": manifest.TRACEABILITY_ROW_REQUIRED_TOKENS["REQ-QA-042"],
    "AC-REQ-QA-042-01": manifest.TRACEABILITY_ROW_REQUIRED_TOKENS["AC-REQ-QA-042-01"],
    "AC-REQ-QA-018-01": ("ea_node_editor.ui.perf.performance_harness",),
    "REQ-PERF-001": ("ea_node_editor/ui/perf/performance_harness.py",),
    "REQ-PERF-002": ("ea_node_editor/ui/perf/performance_harness.py",),
    "REQ-PERF-003": ("ea_node_editor/ui/perf/performance_harness.py",),
}
COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_TRACEABILITY_ROW_FORBIDDEN_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-INT-006": ("compatibility export",),
}
COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX_TOKENS = (
    "COREX No-Legacy Architecture Cleanup QA Matrix",
    "## Locked Scope",
    "## Packet Outcomes",
    "## Retained Automated Verification",
    "## Final Closeout Commands",
    "## 2026-04-24 Execution Results",
    "## Manual Smoke Guidance",
    "## Residual Risks",
    "focused bridges",
    "explicit source contracts",
    "current-schema persistence",
    "descriptor-only plugins/add-ons",
    "snapshot-only runtime payloads",
    "typed viewer transport",
    "canonical launch/import paths",
    "P01_no_legacy_guardrails_WRAPUP.md",
    "P13_launch_package_import_shim_cleanup_WRAPUP.md",
    "P14_docs_traceability_closeout_WRAPUP.md",
    "c413beae3eab13eb40aaceb86bd143587900d6de",
    "dfd3ab4b746a13628f4eb2d803bd653809092d89",
    COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_PYTEST_COMMAND,
    COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_TRACEABILITY_COMMAND,
    COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_MARKDOWN_COMMAND,
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
NODE_EXECUTION_VISUALIZATION_P01_WORKER_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py "
    r"-k execution_edge_progress_projection --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_P01_CONTROLLER_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_run_controller_unit.py -k execution_edge_progress_projection "
    r"--ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_P02_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/bridge_contracts.py tests/test_main_window_shell.py "
    r"-k execution_edge_progress_canvas --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_P03_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_flow_edge_labels.py -k execution_edge_progress_snapshot "
    r"--ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_P04_SHELL_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_shell_run_controller.py -k execution_edge_progress_visualization "
    r"--ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_P04_QML_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/graph_track_b/qml_preference_bindings.py "
    r"-k execution_edge_progress_visualization --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P01_PROTOCOL_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py "
    r"tests/test_execution_client.py -k persistent_node_elapsed_time_protocol "
    r"--ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P02_CONTROLLER_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_run_controller_unit.py -k persistent_node_elapsed_state "
    r"--ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P02_SESSION_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_project_session_controller_unit.py "
    r"-k persistent_node_elapsed_state --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P03_BRIDGE_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/bridge_contracts.py tests/test_main_window_shell.py "
    r"-k persistent_node_elapsed_canvas --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P03_QML_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/bridge_qml_boundaries.py -k persistent_node_elapsed_canvas "
    r"--ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P04_HISTORY_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/graph_track_b/runtime_history.py "
    r"tests/graph_track_b/scene_model_graph_scene_suite.py "
    r"-k persistent_node_elapsed_action_types --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P05_INVALIDATION_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/edit_clipboard_history.py tests/test_main_window_shell.py "
    r"-k persistent_node_elapsed_invalidation --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_SHELL_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_shell_run_controller.py -k persistent_node_elapsed_footer "
    r"--ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_PASSIVE_HOST_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/graph_surface/passive_host_interaction_suite.py -k persistent_node_elapsed_footer "
    r"--ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_QML_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/graph_track_b/qml_preference_bindings.py -k persistent_node_elapsed_footer "
    r"--ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_TRACEABILITY_TEST_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
NODE_EXECUTION_VISUALIZATION_TRACEABILITY_COMMAND = (
    r".\venv\Scripts\python.exe scripts/check_traceability.py"
)

NODE_EXECUTION_VISUALIZATION_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-034": (
            "blue pulse halo",
            "authored control-edge progress visualization",
            "started_at_epoch_ms",
            "elapsed_ms",
            "shell fallback timing",
            "session-only per-workspace persistent cached footer",
            "execution-affecting invalidation",
            "node_failed_handled",
            "240ms",
        ),
        "AC-REQ-UI-034-01": (
            "blue pulse halo",
            "dim-before-progress",
            "shell fallback timing",
            "session-only per-workspace persistent cached footer retention",
            "execution-affecting invalidation",
            "passive-host",
            "QML-local elapsed timer",
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/45_NODE_EXECUTION_MODEL.md": {
        "REQ-NODE-027": (
            "node_started",
            "node_completed",
            "started_at_epoch_ms",
            "elapsed_ms",
            "shell fallback timing",
            "run-start authored workspace snapshot",
            "session-only",
            "execution-affecting edits",
            "session-restore payloads",
        ),
        "AC-REQ-NODE-027-01": (
            "worker/client",
            "project-session",
            "bridge-contract/QML-boundary",
            "execution-affecting cache clears",
            "persistent cached footer behavior",
            "no `.sfe` persistence expansion",
        ),
    },
    "docs/specs/requirements/50_EXECUTION_ENGINE.md": {
        "REQ-EXEC-007": (
            "started_at_epoch_ms",
            "elapsed_ms",
            "actual plugin execution time",
            "shell-side fallback timing",
        ),
        "AC-REQ-EXEC-007-01": (
            "tests/test_execution_worker.py",
            "tests/test_execution_client.py",
            "started_at_epoch_ms",
            "elapsed_ms",
            "shell-side fallback timing",
        ),
    },
    "docs/specs/requirements/80_PERFORMANCE.md": {
        "REQ-PERF-010": (
            "shell fallback timing",
            "persistent cached footer",
            "shared history/revision path",
            "QML-local live timer",
            "hit-testing contracts",
            "cached scene payload structure",
        ),
        "AC-REQ-PERF-010-01": (
            "test_flow_edge_labels.py",
            "passive_host_interaction_suite.py",
            "qml_preference_bindings.py",
            "persistent cached footer",
            "geometry",
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-027": (
            "NODE_EXECUTION_VISUALIZATION",
            "additive worker timing metadata",
            "shell fallback timing",
            "session-only per-workspace cached elapsed state",
            "persistent cached footer behavior",
            "`PERSISTENT_NODE_ELAPSED_TIMES`",
        ),
        "REQ-QA-028": (
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
            "A+E-hybrid visual baseline",
            "`PERSISTENT_NODE_ELAPSED_TIMES`",
            "persistent cached footer checks",
            "no-`.sfe`-persistence",
            "shell fallback timing",
            "traceability gate",
        ),
        "AC-REQ-QA-027-01": (
            NODE_EXECUTION_VISUALIZATION_P01_WORKER_COMMAND,
            NODE_EXECUTION_VISUALIZATION_P01_CONTROLLER_COMMAND,
            NODE_EXECUTION_VISUALIZATION_P02_COMMAND,
            NODE_EXECUTION_VISUALIZATION_P03_COMMAND,
            NODE_EXECUTION_VISUALIZATION_P04_SHELL_COMMAND,
            NODE_EXECUTION_VISUALIZATION_P04_QML_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P01_PROTOCOL_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P02_CONTROLLER_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P02_SESSION_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P03_BRIDGE_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P03_QML_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P04_HISTORY_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P05_INVALIDATION_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_SHELL_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_PASSIVE_HOST_COMMAND,
            NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_QML_COMMAND,
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        ),
        "AC-REQ-QA-028-01": (
            NODE_EXECUTION_VISUALIZATION_TRACEABILITY_TEST_COMMAND,
            NODE_EXECUTION_VISUALIZATION_TRACEABILITY_COMMAND,
            "persistent elapsed-time extension",
            "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        ),
    },
}

NODE_EXECUTION_VISUALIZATION_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-EXEC-007": (
        "protocol.py",
        "client.py",
        "worker.py",
        "tests/test_execution_worker.py",
        "tests/test_execution_client.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "AC-REQ-EXEC-007-01": (
        "tests/test_execution_worker.py",
        "tests/test_execution_client.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "REQ-UI-034": (
        "run_controller.py",
        "GraphCanvas.qml",
        "GraphNodeChromeBackground.qml",
        "GraphNodeHost.qml",
        "test_project_session_controller_unit.py",
        "bridge_qml_boundaries.py",
        "edit_clipboard_history.py",
        "passive_host_interaction_suite.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "AC-REQ-UI-034-01": (
        "tests/test_shell_run_controller.py",
        "tests/test_flow_edge_labels.py",
        "tests/graph_surface/passive_host_interaction_suite.py",
        "tests/main_window_shell/edit_clipboard_history.py",
        "tests/graph_track_b/qml_preference_bindings.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "REQ-NODE-027": (
        "protocol.py",
        "worker_runner.py",
        "state.py",
        "run_controller.py",
        "graph_canvas_state_bridge.py",
        "tests/test_execution_worker.py",
        "tests/test_execution_client.py",
        "tests/test_project_session_controller_unit.py",
        "bridge_qml_boundaries.py",
        "runtime_history.py",
        "edit_clipboard_history.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "AC-REQ-NODE-027-01": (
        "tests/test_execution_worker.py",
        "tests/test_execution_client.py",
        "tests/test_run_controller_unit.py",
        "tests/test_project_session_controller_unit.py",
        "tests/main_window_shell/bridge_qml_boundaries.py",
        "tests/main_window_shell/edit_clipboard_history.py",
        "tests/test_shell_run_controller.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "REQ-PERF-010": (
        "EdgeLayer.qml",
        "EdgeSnapshotCache.js",
        "GraphCanvasRootLayers.qml",
        "GraphNodeHost.qml",
        "tests/test_flow_edge_labels.py",
        "tests/graph_surface/passive_host_interaction_suite.py",
        "tests/graph_track_b/qml_preference_bindings.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "AC-REQ-PERF-010-01": (
        "tests/test_flow_edge_labels.py",
        "tests/graph_track_b/qml_preference_bindings.py",
        "tests/test_shell_run_controller.py",
        "tests/graph_surface/passive_host_interaction_suite.py",
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
    ),
    "REQ-QA-027": (
        "NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md",
        "docs/specs/requirements/20_UI_UX.md",
        "docs/specs/requirements/45_NODE_EXECUTION_MODEL.md",
        "docs/specs/requirements/50_EXECUTION_ENGINE.md",
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
        NODE_EXECUTION_VISUALIZATION_P01_WORKER_COMMAND,
        NODE_EXECUTION_VISUALIZATION_P01_CONTROLLER_COMMAND,
        NODE_EXECUTION_VISUALIZATION_P02_COMMAND,
        NODE_EXECUTION_VISUALIZATION_P03_COMMAND,
        NODE_EXECUTION_VISUALIZATION_P04_SHELL_COMMAND,
        NODE_EXECUTION_VISUALIZATION_P04_QML_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P01_PROTOCOL_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P02_CONTROLLER_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P02_SESSION_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P03_BRIDGE_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P03_QML_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P04_HISTORY_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P05_INVALIDATION_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_SHELL_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_PASSIVE_HOST_COMMAND,
        NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_QML_COMMAND,
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
    "started_at_epoch_ms",
    "elapsed_ms",
    "session-only",
    "persistent cached footer",
    "execution-affecting",
    "authored control-edge",
    "node_failed_handled",
    "0.2",
    "1.4px",
    "240ms",
    NODE_EXECUTION_VISUALIZATION_P01_WORKER_COMMAND,
    NODE_EXECUTION_VISUALIZATION_P01_CONTROLLER_COMMAND,
    NODE_EXECUTION_VISUALIZATION_P02_COMMAND,
    NODE_EXECUTION_VISUALIZATION_P03_COMMAND,
    NODE_EXECUTION_VISUALIZATION_P04_SHELL_COMMAND,
    NODE_EXECUTION_VISUALIZATION_P04_QML_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P01_PROTOCOL_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P02_CONTROLLER_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P02_SESSION_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P03_BRIDGE_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P03_QML_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P04_HISTORY_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P05_INVALIDATION_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_SHELL_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_PASSIVE_HOST_COMMAND,
    NODE_EXECUTION_VISUALIZATION_PERSISTENT_P06_QML_COMMAND,
    NODE_EXECUTION_VISUALIZATION_TRACEABILITY_TEST_COMMAND,
    NODE_EXECUTION_VISUALIZATION_TRACEABILITY_COMMAND,
    "P01_run_state_edge_progress_projection_WRAPUP.md",
    "P02_graph_canvas_execution_edge_bindings_WRAPUP.md",
    "P03_execution_edge_snapshot_metadata_WRAPUP.md",
    "P04_execution_edge_renderer_highlights_WRAPUP.md",
    "P01_worker_timing_protocol_projection_WRAPUP.md",
    "P02_shell_elapsed_cache_projection_WRAPUP.md",
    "P03_graph_canvas_elapsed_bindings_WRAPUP.md",
    "P04_history_action_type_expansion_WRAPUP.md",
    "P05_timing_cache_invalidation_hooks_WRAPUP.md",
    "P06_node_footer_persistent_elapsed_rendering_WRAPUP.md",
    "## Final Closeout Commands",
    "## 2026-04-08 Execution Results",
    "## Remaining Manual A+E-Hybrid, Execution-Edge, and Persistent Elapsed Checks",
    "## Residual Desktop-Only Validation",
)
NESTED_NODE_CATEGORIES_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/NESTED_NODE_CATEGORIES_QA_MATRIX.md"
)
NESTED_NODE_CATEGORIES_P01_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_decorator_sdk.py "
    r"tests/test_registry_validation.py -k nested_category_sdk --ignore=venv -q"
)
NESTED_NODE_CATEGORIES_P01_REVIEW_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py "
    r"-k nested_category_sdk --ignore=venv -q"
)
NESTED_NODE_CATEGORIES_P02_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_registry_filters.py "
    r"tests/test_dpf_node_catalog.py tests/test_graph_theme_shell.py "
    r"-k nested_category_registry --ignore=venv -q"
)
NESTED_NODE_CATEGORIES_P02_REVIEW_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_registry_filters.py "
    r"tests/test_dpf_node_catalog.py -k nested_category_registry --ignore=venv -q"
)
NESTED_NODE_CATEGORIES_P03_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_window_library_inspector.py "
    r"tests/main_window_shell/bridge_support.py -k nested_category_library_payload --ignore=venv -q"
)
NESTED_NODE_CATEGORIES_P03_REVIEW_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/drop_connect_and_workflow_io.py "
    r"-k nested_category_library_payload --ignore=venv -q"
)
NESTED_NODE_CATEGORIES_P04_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/bridge_qml_boundaries.py "
    r"tests/main_window_shell/drop_connect_and_workflow_io.py tests/test_main_window_shell.py "
    r"-k nested_category_qml --ignore=venv -q"
)
NESTED_NODE_CATEGORIES_P04_REVIEW_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/drop_connect_and_workflow_io.py "
    r"-k nested_category_qml --ignore=venv -q"
)
NESTED_NODE_CATEGORIES_TRACEABILITY_TEST_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
NESTED_NODE_CATEGORIES_TRACEABILITY_COMMAND = (
    r".\venv\Scripts\python.exe scripts/check_traceability.py"
)

NESTED_NODE_CATEGORIES_INDEX_TOKENS = (
    "NESTED_NODE_CATEGORIES QA Matrix",
    "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
)

NESTED_NODE_CATEGORIES_PUBLIC_DOC_TOKENS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "(\"Math\",)",
        "breaking change for external plugins",
        "Ansys DPF > Compute",
        "Input / Output",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "docs/GETTING_STARTED.md": (
        "category_path=(\"Math\",)",
        "breaking change for external plugins",
        "category_key",
        "Ansys DPF > Viewer",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
}

NESTED_NODE_CATEGORIES_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-006": (
            "normalized category path",
            "descendant-inclusive",
            "ListView",
            "category_key",
            "Input / Output",
        ),
        "AC-REQ-UI-006-01": (
            "Ansys DPF > Compute",
            "Ansys DPF > Viewer",
            "category rows default collapsed",
            "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/40_NODE_SDK.md": {
        "REQ-NODE-003": (
            "category_path",
            "descendant-inclusive",
            "category_paths()",
        ),
        "REQ-NODE-007": (
            "category_path=",
            "category=",
            "external plugins",
            "derived display labels",
        ),
        "AC-REQ-NODE-003-01": (
            "category_path",
            "parent category filters including descendant nodes",
        ),
        "AC-REQ-NODE-008-01": (
            "category_path=",
            "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/70_INTEGRATIONS.md": {
        "REQ-INT-008": (
            "category_path",
            "(\"Ansys DPF\", \"Compute\")",
            "(\"Ansys DPF\", \"Viewer\")",
        ),
        "AC-REQ-INT-008-01": (
            "Ansys DPF > Compute",
            "Ansys DPF > Viewer",
            "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-033": (
            "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
            "`P01` through `P05`",
            "external-plugin",
            "category_path=",
            "display-only ` > ` delimiter",
            "manual evidence",
        ),
        "AC-REQ-QA-033-01": (
            NESTED_NODE_CATEGORIES_TRACEABILITY_TEST_COMMAND,
            NESTED_NODE_CATEGORIES_TRACEABILITY_COMMAND,
            "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
        ),
    },
}

NESTED_NODE_CATEGORIES_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-UI-006": (
        "category_paths.py",
        "window_library_inspector.py",
        "NodeLibraryPane.qml",
        "tests/test_window_library_inspector.py",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "AC-REQ-UI-006-01": (
        "tests/main_window_shell/bridge_qml_boundaries.py",
        "tests/main_window_shell/drop_connect_and_workflow_io.py",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "REQ-NODE-003": (
        "category_paths.py",
        "registry.py",
        "tests/test_registry_filters.py",
        "tests/test_registry_validation.py",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "REQ-NODE-007": (
        "decorators.py",
        "node_specs.py",
        "README.md",
        "docs/GETTING_STARTED.md",
        "tests/test_decorator_sdk.py",
    ),
    "AC-REQ-NODE-003-01": (
        NESTED_NODE_CATEGORIES_P02_COMMAND,
        "tests/test_registry_filters.py",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "AC-REQ-NODE-008-01": (
        "tests/test_decorator_sdk.py",
        "category_path=",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "REQ-NODE-025": (
        "ansys_dpf_compute.py",
        "ansys_dpf_viewer.py",
        "DPF_COMPUTE_CATEGORY_PATH",
        "DPF_VIEWER_CATEGORY_PATH",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "AC-REQ-NODE-025-01": (
        NESTED_NODE_CATEGORIES_P02_REVIEW_COMMAND,
        "tests/test_dpf_node_catalog.py",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "REQ-INT-008": (
        "ansys_dpf_compute.py",
        "ansys_dpf_viewer.py",
        "tests/test_dpf_node_catalog.py",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "AC-REQ-INT-008-01": (
        "tests/test_dpf_compute_nodes.py",
        "tests/test_dpf_node_catalog.py",
        "NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
    "REQ-QA-033": (
        "README.md",
        "docs/GETTING_STARTED.md",
        "docs/specs/INDEX.md",
        "docs/specs/perf/NESTED_NODE_CATEGORIES_QA_MATRIX.md",
        "tests/test_traceability_checker.py",
        "scripts/check_traceability.py",
    ),
    "AC-REQ-QA-033-01": (
        NESTED_NODE_CATEGORIES_TRACEABILITY_TEST_COMMAND,
        NESTED_NODE_CATEGORIES_TRACEABILITY_COMMAND,
        "docs/specs/perf/NESTED_NODE_CATEGORIES_QA_MATRIX.md",
    ),
}

NESTED_NODE_CATEGORIES_QA_MATRIX_TOKENS = (
    "Nested Node Categories QA Matrix",
    "## Locked Scope",
    "category_path: tuple[str, ...]",
    "`1..10`",
    "`category=` is a breaking change for external plugins",
    "` > `",
    "Input / Output",
    "descendant-inclusive",
    "Ansys DPF > Compute",
    "Ansys DPF > Viewer",
    "Custom Workflows",
    "flat `ListView`",
    "category_key",
    NESTED_NODE_CATEGORIES_P01_COMMAND,
    NESTED_NODE_CATEGORIES_P01_REVIEW_COMMAND,
    NESTED_NODE_CATEGORIES_P02_COMMAND,
    NESTED_NODE_CATEGORIES_P02_REVIEW_COMMAND,
    NESTED_NODE_CATEGORIES_P03_COMMAND,
    NESTED_NODE_CATEGORIES_P03_REVIEW_COMMAND,
    NESTED_NODE_CATEGORIES_P04_COMMAND,
    NESTED_NODE_CATEGORIES_P04_REVIEW_COMMAND,
    NESTED_NODE_CATEGORIES_TRACEABILITY_TEST_COMMAND,
    NESTED_NODE_CATEGORIES_TRACEABILITY_COMMAND,
    "P01_sdk_category_path_contract_WRAPUP.md",
    "P04_qml_nested_library_presentation_WRAPUP.md",
    "## Final Closeout Commands",
    "## 2026-04-11 Execution Results",
    "## Retained Manual Evidence",
    "## Residual Risks",
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P01_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py "
    r"-k graph_typography_preferences --ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P02_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/bridge_contracts_graph_canvas.py tests/test_main_window_shell.py "
    r"-k graph_typography_bridge --ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P03_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/bridge_qml_boundaries.py tests/graph_track_b/qml_preference_bindings.py "
    r"-k graph_typography_qml_contract --ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_SHELL_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_shell_run_controller.py -k graph_typography_host_chrome --ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_PASSIVE_HOST_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/graph_surface/passive_host_interaction_suite.py -k graph_typography_host_chrome "
    r"--ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_QML_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/graph_track_b/qml_preference_bindings.py -k graph_typography_host_chrome "
    r"--ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_INLINE_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_graph_surface_input_inline.py tests/graph_track_b/qml_preference_bindings.py "
    r"-k graph_typography_inline_edge --ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_EDGE_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_flow_edge_labels.py tests/graph_track_b/qml_preference_bindings.py "
    r"-k graph_typography_inline_edge --ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_PASSIVE_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/graph_surface/passive_host_interaction_suite.py -k graph_typography_inline_edge "
    r"--ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P06_DIALOG_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_graphics_settings_dialog.py tests/test_graphics_settings_preferences.py "
    r"-k graph_typography_dialog --ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_P06_SHELL_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/shell_basics_and_search.py tests/graph_track_b/qml_preference_bindings.py "
    r"-k graph_typography_dialog --ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_TEST_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_COMMAND = (
    r".\venv\Scripts\python.exe scripts/check_traceability.py"
)

SHARED_GRAPH_TYPOGRAPHY_CONTROL_INDEX_TOKENS = (
    "SHARED_GRAPH_TYPOGRAPHY_CONTROL QA Matrix",
    "SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
)

SHARED_GRAPH_TYPOGRAPHY_CONTROL_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-035": (
            "graphics.typography.graph_label_pixel_size",
            "defaulting to `10`",
            "clamping to `8..18`",
            "GraphSharedTypography",
            "visual_style.font_size",
            "visual_style.font_weight",
            "graph-theme typography schema",
            ".sfe",
        ),
        "AC-REQ-UI-035-01": (
            "Theme > Typography",
            "host-chrome",
            "passive-host",
            "shared role hierarchy",
            "SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/80_PERFORMANCE.md": {
        "REQ-PERF-011": (
            "deterministic metric alignment",
            "graph_label_pixel_size",
            "standard_metrics.py",
            "existing graph-canvas payload refresh or revision seam",
            "second typography-only invalidation channel",
            "stale clipping/label-width drift",
        ),
        "AC-REQ-PERF-011-01": (
            "bridge_qml_boundaries.py",
            "qml_preference_bindings.py",
            "test_flow_edge_labels.py",
            "8..18",
            "SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-032": (
            "SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
            "`P01` through `P06`",
            "manual desktop checks",
            "`PERSISTENT_NODE_ELAPSED_TIMES`",
            "desktop-only validation",
            "traceability gate",
        ),
        "AC-REQ-QA-032-01": (
            SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_TEST_COMMAND,
            SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_COMMAND,
            "SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
        ),
    },
}

SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-UI-035": (
        "settings.py",
        "app_preferences.py",
        "graphics_settings_dialog.py",
        "GraphSharedTypography.qml",
        "GraphNodeHeaderLayer.qml",
        "GraphNodePortsLayer.qml",
        "GraphInlinePropertiesLayer.qml",
        "GraphNodeHost.qml",
        "EdgeFlowLabelLayer.qml",
        "SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
    ),
    "AC-REQ-UI-035-01": (
        "tests/test_graphics_settings_dialog.py",
        "tests/test_graphics_settings_preferences.py",
        "tests/test_shell_run_controller.py",
        "tests/test_graph_surface_input_inline.py",
        "tests/test_flow_edge_labels.py",
        "tests/graph_surface/passive_host_interaction_suite.py",
        "tests/graph_track_b/qml_preference_bindings.py",
        "SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
    ),
    "REQ-PERF-011": (
        "standard_metrics.py",
        "graph_scene_payload_builder.py",
        "GraphCanvasRootBindings.qml",
        "GraphSharedTypography.qml",
        "tests/main_window_shell/bridge_qml_boundaries.py",
        "SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
    ),
    "AC-REQ-PERF-011-01": (
        "tests/main_window_shell/bridge_qml_boundaries.py",
        "tests/graph_track_b/qml_preference_bindings.py",
        "tests/test_flow_edge_labels.py",
        "SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
    ),
    "REQ-QA-032": (
        "docs/specs/INDEX.md",
        "docs/specs/perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
        "docs/specs/requirements/20_UI_UX.md",
        "docs/specs/requirements/80_PERFORMANCE.md",
        "docs/specs/requirements/90_QA_ACCEPTANCE.md",
        "docs/specs/requirements/TRACEABILITY_MATRIX.md",
        "tests/test_traceability_checker.py",
        "scripts/check_traceability.py",
    ),
    "AC-REQ-QA-032-01": (
        SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_TEST_COMMAND,
        SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_COMMAND,
        "docs/specs/perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md",
    ),
}

SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX_TOKENS = (
    "Shared Graph Typography Control QA Matrix",
    "## Locked Scope",
    "graphics.typography.graph_label_pixel_size",
    "default `10`",
    "`8..18`",
    "GraphSharedTypography.qml",
    "visual_style.font_size",
    "visual_style.font_weight",
    "PERSISTENT_NODE_ELAPSED_TIMES",
    "second typography-only invalidation channel",
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P01_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P02_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P03_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_SHELL_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_PASSIVE_HOST_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_QML_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_INLINE_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_EDGE_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_PASSIVE_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P06_DIALOG_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_P06_SHELL_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_TEST_COMMAND,
    SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_COMMAND,
    "Accepted `P01` packet commit `af6d24a665b0910bfec54259424c89e3a9840593`",
    "Accepted `P06` packet commit `cd409e0cffd8d6e7c41a94f9dd70bee336c75965`",
    "## Final Closeout Commands",
    "## 2026-04-09 Execution Results",
    "## Remaining Manual Smoke Checks",
    "## Residual Desktop-Only Validation",
    "## Residual Risks",
)
PORT_VALUE_LOCKING_QA_MATRIX = REPO_ROOT / "docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md"
PORT_VALUE_LOCKING_P01_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_port_locking.py "
    r"tests/test_serializer.py --ignore=venv -q"
)
PORT_VALUE_LOCKING_P02_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_port_locking.py "
    r"tests/graph_track_b/scene_model_graph_scene_suite.py --ignore=venv -q"
)
PORT_VALUE_LOCKING_P03_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_graph_scene_bridge_bind_regression.py "
    r"tests/main_window_shell/view_library_inspector.py "
    r"tests/graph_surface/passive_host_boundary_suite.py --ignore=venv -q"
)
PORT_VALUE_LOCKING_P04_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_graph_surface_input_contract.py "
    r"tests/test_graph_surface_input_controls.py "
    r"tests/test_graph_surface_input_inline.py --ignore=venv -q"
)
PORT_VALUE_LOCKING_P05_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/graph_surface/pointer_and_modal_suite.py "
    r"tests/graph_track_b/qml_preference_performance_suite.py --ignore=venv -q"
)
PORT_VALUE_LOCKING_TRACEABILITY_TEST_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
PORT_VALUE_LOCKING_TRACEABILITY_COMMAND = (
    r".\venv\Scripts\python.exe scripts/check_traceability.py"
)

PORT_VALUE_LOCKING_INDEX_TOKENS = (
    "PORT_VALUE_LOCKING QA Matrix",
    "PORT_VALUE_LOCKING_QA_MATRIX.md",
)

PORT_VALUE_LOCKING_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-036": (
            "lockable primitive input rows",
            "locked rows keep their inline editors",
            "lock affordance",
            "suppress incoming-edge drop eligibility",
            "only edge eligibility",
        ),
        "REQ-UI-037": (
            "hide_locked_ports",
            "hide_optional_ports",
            "empty-canvas gestures",
            "view-local persistence",
        ),
        "AC-REQ-UI-036-01": (
            "graph-surface input",
            "view-inspector",
            "manual lock toggle undo/redo",
            "PORT_VALUE_LOCKING_QA_MATRIX.md",
        ),
        "AC-REQ-UI-037-01": (
            "scene-bridge",
            "pointer/modal",
            "view-switch plus undo/redo persistence",
            "PORT_VALUE_LOCKING_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/30_GRAPH_MODEL.md": {
        "REQ-GRAPH-019": (
            "lockable primitive input data ports",
            "one-way auto-lock",
            "set_locked_port",
            "without rewriting the property value",
            "pruning now-illegal existing incoming edges",
        ),
        "REQ-GRAPH-020": (
            "ViewState",
            "hide_locked_ports",
            "hide_optional_ports",
            "project locked/optional metadata",
            "hide only the active-view rows",
        ),
        "AC-REQ-GRAPH-019-01": (
            "one-way auto-lock",
            "locked-target rejection",
            "manual toggle",
            "fragment round-trip retention",
            "PORT_VALUE_LOCKING_QA_MATRIX.md",
        ),
        "AC-REQ-GRAPH-020-01": (
            "scene-bridge",
            "passive-host",
            "pointer/gesture",
            "undo/redo-safe row filtering",
            "PORT_VALUE_LOCKING_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/60_PERSISTENCE.md": {
        "REQ-PERSIST-021": (
            "NodeInstance.locked_ports",
            "ViewState.hide_locked_ports",
            "hide_optional_ports",
            "one-way auto-lock outcomes",
            "workspace duplication",
        ),
        "AC-REQ-PERSIST-021-01": (
            "serializer and port-locking regressions",
            "workspace snapshot restore",
            "duplicate-workspace flows",
            "PORT_VALUE_LOCKING_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/80_PERFORMANCE.md": {
        "REQ-PERF-012": (
            "existing graph-scene payload, host-row, and canvas-input seams",
            "filter emitted rows instead of rebuilding graph topology",
            "keep inline editors on the existing row surface",
            "second view-filter invalidation path",
            "edge hit geometry",
        ),
        "AC-REQ-PERF-012-01": (
            "tests/test_graph_scene_bridge_bind_regression.py",
            "tests/graph_surface/passive_host_boundary_suite.py",
            "tests/graph_surface/pointer_and_modal_suite.py",
            "PORT_VALUE_LOCKING_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-034": (
            "PORT_VALUE_LOCKING_QA_MATRIX.md",
            "`P01` through `P05`",
            "manual lock toggle",
            "empty-canvas gestures",
            "traceability gate",
        ),
        "AC-REQ-QA-034-01": (
            PORT_VALUE_LOCKING_TRACEABILITY_TEST_COMMAND,
            PORT_VALUE_LOCKING_TRACEABILITY_COMMAND,
            "PORT_VALUE_LOCKING_QA_MATRIX.md",
        ),
    },
}

PORT_VALUE_LOCKING_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-UI-036": (
        "GraphNodeHost.qml",
        "GraphNodePortsLayer.qml",
        "GraphCanvasNodeDelegate.qml",
        "tests/test_graph_surface_input_controls.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "AC-REQ-UI-036-01": (
        "tests/test_graph_surface_input_contract.py",
        "tests/test_graph_surface_input_controls.py",
        "tests/test_graph_surface_input_inline.py",
        "tests/main_window_shell/view_library_inspector.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "REQ-UI-037": (
        "graph_canvas_state_bridge.py",
        "GraphCanvasRootBindings.qml",
        "GraphCanvasInputLayers.qml",
        "tests/graph_surface/pointer_and_modal_suite.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "AC-REQ-UI-037-01": (
        "tests/test_graph_scene_bridge_bind_regression.py",
        "tests/main_window_shell/view_library_inspector.py",
        "tests/graph_track_b/qml_preference_performance_suite.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "REQ-GRAPH-019": (
        "port_locking.py",
        "mutation_service.py",
        "scene_model_graph_scene_suite.py",
        "tests/test_port_locking.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "AC-REQ-GRAPH-019-01": (
        "tests/test_port_locking.py",
        "tests/graph_track_b/scene_model_graph_scene_suite.py",
        "tests/main_window_shell/view_library_inspector.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "REQ-GRAPH-020": (
        "graph_scene_payload_builder.py",
        "graph_scene_mutation_history.py",
        "view_library_inspector.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "AC-REQ-GRAPH-020-01": (
        "tests/test_graph_scene_bridge_bind_regression.py",
        "tests/graph_surface/passive_host_boundary_suite.py",
        "tests/graph_surface/pointer_and_modal_suite.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "REQ-PERSIST-021": (
        "model.py",
        "project_codec.py",
        "tests/test_serializer.py",
        "tests/test_port_locking.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "AC-REQ-PERSIST-021-01": (
        "tests/test_serializer.py",
        "tests/test_port_locking.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "REQ-PERF-012": (
        "graph_scene_payload_builder.py",
        "GraphNodeHost.qml",
        "GraphCanvasInputLayers.qml",
        "tests/graph_surface/passive_host_boundary_suite.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "AC-REQ-PERF-012-01": (
        "tests/test_graph_scene_bridge_bind_regression.py",
        "tests/graph_surface/passive_host_boundary_suite.py",
        "tests/graph_surface/pointer_and_modal_suite.py",
        "PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
    "REQ-QA-034": (
        "docs/specs/INDEX.md",
        "docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md",
        "docs/specs/requirements/20_UI_UX.md",
        "docs/specs/requirements/30_GRAPH_MODEL.md",
        "docs/specs/requirements/60_PERSISTENCE.md",
        "docs/specs/requirements/80_PERFORMANCE.md",
        "docs/specs/requirements/90_QA_ACCEPTANCE.md",
        "docs/specs/requirements/TRACEABILITY_MATRIX.md",
        "tests/test_traceability_checker.py",
        "scripts/check_traceability.py",
    ),
    "AC-REQ-QA-034-01": (
        PORT_VALUE_LOCKING_TRACEABILITY_TEST_COMMAND,
        PORT_VALUE_LOCKING_TRACEABILITY_COMMAND,
        "docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md",
    ),
}

PORT_VALUE_LOCKING_QA_MATRIX_TOKENS = (
    "Port Value Locking QA Matrix",
    "## Locked Scope",
    "one-way auto-lock",
    "hide_locked_ports",
    "hide_optional_ports",
    "Ctrl-double-click",
    PORT_VALUE_LOCKING_P01_COMMAND,
    PORT_VALUE_LOCKING_P02_COMMAND,
    PORT_VALUE_LOCKING_P03_COMMAND,
    PORT_VALUE_LOCKING_P04_COMMAND,
    PORT_VALUE_LOCKING_P05_COMMAND,
    PORT_VALUE_LOCKING_TRACEABILITY_TEST_COMMAND,
    PORT_VALUE_LOCKING_TRACEABILITY_COMMAND,
    "Accepted `P01` packet commit `dfef8d2f5110d3893c09ba17a170853c8ead7cc6`",
    "Accepted `P05` packet commit `0fd842953f464795190c1d6f199dcdcaae82cbad`",
    "## Final Closeout Commands",
    "## 2026-04-12 Execution Results",
    "## Remaining Manual Smoke Checks",
    "## Residual Desktop-Only Validation",
    "## Residual Risks",
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md"
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_P01_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_node_title_icon_sources.py "
    r"tests/test_registry_validation.py tests/test_passive_visual_metadata.py "
    r"-k title_icon --ignore=venv -q"
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_P02_DIALOG_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py "
    r"-k graph_node_icon_size --ignore=venv -q"
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_P02_BRIDGE_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/bridge_contracts_graph_canvas.py "
    r"tests/main_window_shell/bridge_qml_boundaries.py tests/test_main_window_shell.py "
    r"tests/test_shell_run_controller.py tests/graph_track_b/qml_preference_bindings.py "
    r"-k graph_node_icon_size --ignore=venv -q"
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_P03_HEADER_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/graph_surface/inline_editor_suite.py "
    r"tests/graph_surface/passive_host_interaction_suite.py "
    r"tests/graph_track_b/qml_preference_rendering_suite.py "
    r"-k title_icon --ignore=venv -q"
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_P03_COMMENT_COMMAND = (
    r"$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest "
    r"tests/main_window_shell/comment_backdrop_workflows.py "
    r"tests/main_window_shell/shell_runtime_contracts.py "
    r"tests/test_icon_registry.py tests/test_comment_backdrop_contracts.py "
    r"-k title_icon --ignore=venv -q"
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_P04_ASSET_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_node_title_icon_assets.py "
    r"tests/test_registry_validation.py -k title_icon --ignore=venv -q"
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_P04_CATALOG_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py "
    r"tests/test_passive_node_contracts.py tests/test_passive_flowchart_catalog.py "
    r"-k title_icon --ignore=venv -q"
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_TEST_COMMAND = (
    r".\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_COMMAND = (
    r".\venv\Scripts\python.exe scripts/check_traceability.py"
)

TITLE_ICONS_FOR_NON_PASSIVE_NODES_INDEX_TOKENS = (
    "TITLE_ICONS_FOR_NON_PASSIVE_NODES QA Matrix",
    "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
)

TITLE_ICONS_FOR_NON_PASSIVE_NODES_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-038": (
            "leading local title icon only for `active` and `compile_only` nodes",
            "supported local `.svg`, `.png`, `.jpg`, or `.jpeg` file",
            "passive nodes remain iconless",
            "`uiIcons` / `comment.svg`",
            "`graph_node_icon_pixel_size_override`",
            "`null` mode follows `graph_label_pixel_size`",
            "`8..50`",
        ),
        "AC-REQ-UI-038-01": (
            "active and `compile_only` headers render the path-backed icon",
            "passive titles stay iconless",
            "centered/elided title behavior",
            "automatic/custom icon-size modes",
            "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/40_NODE_SDK.md": {
        "REQ-NODE-028": (
            "`NodeTypeSpec.icon` remains the authoring field",
            "local image-path reference only",
            "repo-managed node-title icon asset root",
            "safe provenance roots",
            "symbolic icon names",
            "derived live `icon_source` payload",
            "`active` and `compile_only`",
        ),
        "AC-REQ-NODE-028-01": (
            "node-title icon resolver",
            "safe provenance resolution",
            "built-in asset-path packaging",
            "passive icon exclusion",
            "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/60_PERSISTENCE.md": {
        "REQ-PERSIST-022": (
            "derived live `icon_source` values shall not serialize into `.sfe` project files",
            "`graphics.typography.graph_node_icon_pixel_size_override`",
            "nullable app-global integer",
            "`null` mode follows `graph_label_pixel_size`",
            "`8..50`",
        ),
        "AC-REQ-PERSIST-022-01": (
            "payload-contract",
            "app preferences",
            "does not widen `.sfe` persistence",
            "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/80_PERFORMANCE.md": {
        "REQ-PERF-013": (
            "existing graph-scene payload, shared header, and shared typography seams",
            "already-derived local `icon_source` plus the effective node-title icon size",
            "centered/elided title reserve math",
            "collapsed comment-backdrop exception",
            "authored image colors without theme tinting",
            "remote image loading",
            "second icon-specific invalidation path",
        ),
        "AC-REQ-PERF-013-01": (
            "tests/graph_surface/inline_editor_suite.py",
            "tests/graph_surface/passive_host_interaction_suite.py",
            "tests/main_window_shell/comment_backdrop_workflows.py",
            "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
        ),
    },
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-037": (
            "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
            "`P01` through `P04`",
            "canonical `docs/specs/INDEX.md` registration",
            "SVG plus PNG/JPG/JPEG fixture coverage where available",
            "collapsed comment-backdrop icon preservation",
            "traceability gate",
        ),
        "AC-REQ-QA-037-01": (
            TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_TEST_COMMAND,
            TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_COMMAND,
            "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
        ),
    },
}

TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-UI-038": (
        "graphics_settings_dialog.py",
        "graph_canvas_state_bridge.py",
        "GraphNodeHeaderLayer.qml",
        "GraphNodeHost.qml",
        "GraphSharedTypography.qml",
        "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
    ),
    "AC-REQ-UI-038-01": (
        "tests/test_graphics_settings_dialog.py",
        "tests/test_graphics_settings_preferences.py",
        "tests/main_window_shell/bridge_contracts_graph_canvas.py",
        "tests/graph_surface/inline_editor_suite.py",
        "tests/graph_surface/passive_host_interaction_suite.py",
        "tests/graph_track_b/qml_preference_rendering_suite.py",
        "tests/main_window_shell/comment_backdrop_workflows.py",
        "tests/test_comment_backdrop_contracts.py",
        "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
    ),
    "REQ-NODE-028": (
        "node_title_icon_sources.py",
        "graph_scene_payload_builder.py",
        "assets/node_title_icons",
        "tests/test_node_title_icon_sources.py",
        "tests/test_node_title_icon_assets.py",
        "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
    ),
    "AC-REQ-NODE-028-01": (
        "tests/test_node_title_icon_sources.py",
        "tests/test_registry_validation.py",
        "tests/test_passive_visual_metadata.py",
        "tests/test_node_title_icon_assets.py",
        "tests/test_dpf_node_catalog.py",
        "tests/test_passive_node_contracts.py",
        "tests/test_passive_flowchart_catalog.py",
        "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
    ),
    "REQ-PERSIST-022": (
        "app_preferences.py",
        "settings.py",
        "graph_scene_payload_builder.py",
        "tests/test_graphics_settings_preferences.py",
        "tests/test_node_title_icon_sources.py",
        "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
    ),
    "AC-REQ-PERSIST-022-01": (
        "tests/test_graphics_settings_preferences.py",
        "tests/main_window_shell/bridge_contracts_graph_canvas.py",
        "tests/test_main_window_shell.py",
        "tests/test_node_title_icon_sources.py",
        "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
    ),
    "REQ-PERF-013": (
        "GraphNodeHeaderLayer.qml",
        "GraphNodeHost.qml",
        "GraphSharedTypography.qml",
        "node_title_icon_sources.py",
        "tests/graph_track_b/qml_preference_rendering_suite.py",
        "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
    ),
    "AC-REQ-PERF-013-01": (
        "tests/graph_surface/inline_editor_suite.py",
        "tests/graph_surface/passive_host_interaction_suite.py",
        "tests/graph_track_b/qml_preference_rendering_suite.py",
        "tests/main_window_shell/comment_backdrop_workflows.py",
        "tests/test_comment_backdrop_contracts.py",
        "TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
    ),
    "REQ-QA-037": (
        "docs/specs/INDEX.md",
        "docs/specs/perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
        "docs/specs/requirements/20_UI_UX.md",
        "docs/specs/requirements/40_NODE_SDK.md",
        "docs/specs/requirements/60_PERSISTENCE.md",
        "docs/specs/requirements/80_PERFORMANCE.md",
        "docs/specs/requirements/90_QA_ACCEPTANCE.md",
        "docs/specs/requirements/TRACEABILITY_MATRIX.md",
        "tests/test_traceability_checker.py",
        "scripts/check_traceability.py",
    ),
    "AC-REQ-QA-037-01": (
        TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_TEST_COMMAND,
        TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_COMMAND,
        "docs/specs/perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md",
    ),
}

TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX_TOKENS = (
    "Title Icons for Non-Passive Nodes QA Matrix",
    "## Locked Scope",
    "`NodeTypeSpec.icon` remains the authoring field",
    "`uiIcons` / `comment.svg`",
    "`graphics.typography.graph_node_icon_pixel_size_override`",
    "node-library tiles",
    TITLE_ICONS_FOR_NON_PASSIVE_NODES_P01_COMMAND,
    TITLE_ICONS_FOR_NON_PASSIVE_NODES_P02_DIALOG_COMMAND,
    TITLE_ICONS_FOR_NON_PASSIVE_NODES_P02_BRIDGE_COMMAND,
    TITLE_ICONS_FOR_NON_PASSIVE_NODES_P03_HEADER_COMMAND,
    TITLE_ICONS_FOR_NON_PASSIVE_NODES_P03_COMMENT_COMMAND,
    TITLE_ICONS_FOR_NON_PASSIVE_NODES_P04_ASSET_COMMAND,
    TITLE_ICONS_FOR_NON_PASSIVE_NODES_P04_CATALOG_COMMAND,
    TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_TEST_COMMAND,
    TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_COMMAND,
    "Accepted `P01` packet commit `bfb953365082f1d96371fe919e92e995875b43f0`",
    "Accepted `P04` packet commit `33090d22b59e01b45fb37521cd283cc53dce8548`",
    "## Final Closeout Commands",
    "## 2026-04-13 Execution Results",
    "## Remaining Manual Smoke Checks",
    "## Residual Desktop-Only Validation",
    "## Residual Risks",
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
UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX = (
    REPO_ROOT / "docs/specs/perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md"
)
UI_CONTEXT_SCALABILITY_FOLLOWUP_FINAL_PYTEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest "
    "tests/test_traceability_checker.py tests/test_markdown_hygiene.py "
    "tests/test_run_verification.py --ignore=venv -q"
)
UI_CONTEXT_SCALABILITY_FOLLOWUP_TRACEABILITY_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_traceability.py"
)
UI_CONTEXT_SCALABILITY_FOLLOWUP_MARKDOWN_COMMAND = (
    "./venv/Scripts/python.exe scripts/check_markdown_links.py"
)
UI_CONTEXT_SCALABILITY_FOLLOWUP_REQUIREMENT_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": {
        "REQ-QA-031": (
            "UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md",
            "P01",
            "guardrail",
            "P08",
            "packet-doc",
            "UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md",
            "UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md",
            "packet wrap-up evidence",
            "CONTEXT_BUDGET_RULES.json",
            "SUBSYSTEM_PACKET_INDEX.md",
            "FEATURE_PACKET_TEMPLATE.md",
        ),
        "AC-REQ-QA-031-01": (
            UI_CONTEXT_SCALABILITY_FOLLOWUP_FINAL_PYTEST_COMMAND,
            UI_CONTEXT_SCALABILITY_FOLLOWUP_TRACEABILITY_COMMAND,
            UI_CONTEXT_SCALABILITY_FOLLOWUP_MARKDOWN_COMMAND,
            "UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md",
        ),
    },
}
UI_CONTEXT_SCALABILITY_FOLLOWUP_TRACEABILITY_ROW_TOKENS: dict[str, tuple[str, ...]] = {
    "REQ-QA-031": (
        "docs/specs/INDEX.md",
        "docs/specs/requirements/90_QA_ACCEPTANCE.md",
        "docs/specs/requirements/TRACEABILITY_MATRIX.md",
        "docs/specs/perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md",
        "docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md",
        "docs/specs/work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md",
        "docs/specs/work_packets/ui_context_scalability_followup/P01_guardrail_catalog_expansion_WRAPUP.md",
        "docs/specs/work_packets/ui_context_scalability_followup/P02_shell_session_surface_split_WRAPUP.md",
        "docs/specs/work_packets/ui_context_scalability_followup/P03_graph_geometry_facade_split_WRAPUP.md",
        "docs/specs/work_packets/ui_context_scalability_followup/P04_graph_scene_mutation_packet_split_WRAPUP.md",
        "docs/specs/work_packets/ui_context_scalability_followup/P05_main_window_bridge_test_packetization_WRAPUP.md",
        "docs/specs/work_packets/ui_context_scalability_followup/P06_graph_surface_test_packetization_WRAPUP.md",
        "docs/specs/work_packets/ui_context_scalability_followup/P07_track_b_test_packetization_WRAPUP.md",
        "docs/specs/work_packets/ui_context_scalability_followup/P08_canonical_ui_test_packet_docs_WRAPUP.md",
        "docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json",
        "docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md",
        "docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md",
        "scripts/check_context_budgets.py",
        "scripts/check_traceability.py",
        "tests/test_traceability_checker.py",
        "tests/test_markdown_hygiene.py",
        "tests/test_run_verification.py",
    ),
    "AC-REQ-QA-031-01": (
        UI_CONTEXT_SCALABILITY_FOLLOWUP_FINAL_PYTEST_COMMAND,
        UI_CONTEXT_SCALABILITY_FOLLOWUP_TRACEABILITY_COMMAND,
        UI_CONTEXT_SCALABILITY_FOLLOWUP_MARKDOWN_COMMAND,
        "UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md",
    ),
}
UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX_TOKENS = (
    "UI Context Scalability Follow-Up QA Matrix",
    "## Locked Scope",
    "## Retained Automated Verification",
    "## Final Closeout Commands",
    "## 2026-04-05 Execution Results",
    "## Remaining Manual Desktop Checks",
    "## Residual Risks",
    "UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md",
    "UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json",
    "docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SURFACE_TEST_PACKET.md",
    "docs/specs/work_packets/ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md",
    manifest.CONTEXT_BUDGET_CHECK_COMMAND,
    manifest.FOLLOWUP_P01_GUARDRAIL_CATALOG_EXPANSION_PYTEST_COMMAND,
    manifest.FOLLOWUP_P01_GUARDRAIL_CATALOG_EXPANSION_FAST_DRY_RUN_COMMAND,
    UI_CONTEXT_SCALABILITY_FOLLOWUP_FINAL_PYTEST_COMMAND,
    UI_CONTEXT_SCALABILITY_FOLLOWUP_TRACEABILITY_COMMAND,
    UI_CONTEXT_SCALABILITY_FOLLOWUP_MARKDOWN_COMMAND,
    "P01_guardrail_catalog_expansion_WRAPUP.md",
    "P02_shell_session_surface_split_WRAPUP.md",
    "P03_graph_geometry_facade_split_WRAPUP.md",
    "P04_graph_scene_mutation_packet_split_WRAPUP.md",
    "P05_main_window_bridge_test_packetization_WRAPUP.md",
    "P06_graph_surface_test_packetization_WRAPUP.md",
    "P07_track_b_test_packetization_WRAPUP.md",
    "P08_canonical_ui_test_packet_docs_WRAPUP.md",
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
        self.assertIn(
            "docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md",
            self.checker.REQUIRED_ARTIFACTS,
        )
        self.assertIn(
            "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
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
        required_paths.update(DPF_OPERATOR_PLUGIN_BACKEND_REQUIREMENT_TOKENS.keys())
        required_paths.update(ADDON_MANAGER_BACKEND_PREPARATION_REQUIREMENT_TOKENS.keys())
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

    def test_audit_repository_reports_dpf_backend_closeout_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            replace_text(
                repo_root / "README.md",
                "DPF operator backend QA matrix",
                "DPF operator backend proof",
            )
            remove_token_from_requirement_line(
                repo_root / "docs/specs/requirements/70_INTEGRATIONS.md",
                "REQ-INT-009",
                "generic DPF runtime adapter",
            )
            replace_text(
                repo_root / "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md",
                "generated-port semantics",
                "generated port semantics",
            )
            remove_token_from_traceability_row(
                repo_root / self.manifest.TRACEABILITY_MATRIX_DOC,
                "REQ-QA-036",
                "tests/test_markdown_hygiene.py",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "README.md: readme dpf backend closeout missing fact: "
            "DPF operator backend QA matrix",
            issues,
        )
        self.assertIn(
            "docs/specs/requirements/70_INTEGRATIONS.md: requirement REQ-INT-009 missing fact: "
            "generic DPF runtime adapter",
            issues,
        )
        self.assertIn(
            "docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md: "
            "dpf-operator-plugin-backend-refactor qa matrix missing fact: "
            "generated-port semantics",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACEABILITY_MATRIX_DOC}: row REQ-QA-036 missing implementation "
            "artifact text: tests/test_markdown_hygiene.py",
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

    def test_dpf_operator_plugin_backend_docs_record_closeout_scope_tokens(self) -> None:
        for relative_path, tokens in DPF_OPERATOR_PLUGIN_BACKEND_PUBLIC_DOC_TOKENS.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")
            for token in tokens:
                self.assertIn(token, text, msg=f"{relative_path} missing token {token!r}")

        for relative_path, requirement_tokens in DPF_OPERATOR_PLUGIN_BACKEND_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_dpf_operator_plugin_backend_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in DPF_OPERATOR_PLUGIN_BACKEND_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_dpf_operator_plugin_backend_qa_matrix_records_commands_and_manual_checks(self) -> None:
        text = DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in DPF_OPERATOR_PLUGIN_BACKEND_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_ansys_dpf_full_plugin_rollout_public_docs_record_closeout_scope_tokens(self) -> None:
        for relative_path, tokens in ANSYS_DPF_FULL_PLUGIN_ROLLOUT_PUBLIC_DOC_TOKENS.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")
            for token in tokens:
                self.assertIn(token, text, msg=f"{relative_path} missing token {token!r}")

    def test_ansys_dpf_full_plugin_rollout_requirements_record_closeout_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in ANSYS_DPF_FULL_PLUGIN_ROLLOUT_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(
                        token,
                        body,
                        msg=f"{relative_path} {requirement_id} missing token {token!r}",
                    )

    def test_ansys_dpf_full_plugin_rollout_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in ANSYS_DPF_FULL_PLUGIN_ROLLOUT_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_ansys_dpf_full_plugin_rollout_qa_matrix_records_commands_and_manual_checks(self) -> None:
        text = ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_addon_manager_backend_preparation_spec_index_registers_packet_set(self) -> None:
        text = (REPO_ROOT / "docs/specs/INDEX.md").read_text(encoding="utf-8-sig")
        for token in ADDON_MANAGER_BACKEND_PREPARATION_INDEX_TOKENS:
            self.assertIn(token, text)

    def test_addon_manager_backend_preparation_docs_record_closeout_scope_tokens(self) -> None:
        for relative_path, tokens in ADDON_MANAGER_BACKEND_PREPARATION_PUBLIC_DOC_TOKENS.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")
            for token in tokens:
                self.assertIn(token, text, msg=f"{relative_path} missing token {token!r}")

        for (
            relative_path,
            requirement_tokens,
        ) in ADDON_MANAGER_BACKEND_PREPARATION_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(
                        token,
                        body,
                        msg=f"{relative_path} {requirement_id} missing token {token!r}",
                    )

    def test_addon_manager_backend_preparation_traceability_rows_reference_packet_artifacts(
        self,
    ) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in ADDON_MANAGER_BACKEND_PREPARATION_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_addon_manager_backend_preparation_qa_matrix_records_commands_and_manual_checks(
        self,
    ) -> None:
        text = ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_corex_no_legacy_architecture_cleanup_spec_index_registers_qa_matrix(self) -> None:
        text = (REPO_ROOT / "docs/specs/INDEX.md").read_text(encoding="utf-8-sig")
        for token in COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_INDEX_TOKENS:
            self.assertIn(token, text)

    def test_corex_no_legacy_architecture_cleanup_docs_record_final_scope_tokens(self) -> None:
        for relative_path, tokens in COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_PUBLIC_DOC_TOKENS.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")
            for token in tokens:
                self.assertIn(token, text, msg=f"{relative_path} missing token {token!r}")

        for relative_path, requirement_tokens in COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_corex_no_legacy_architecture_cleanup_traceability_rows_reference_packet_artifacts(
        self,
    ) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")
            for token in COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_TRACEABILITY_ROW_FORBIDDEN_TOKENS.get(row_id, ()):
                self.assertNotIn(token, row_text, msg=f"traceability row {row_id} has stale token {token!r}")

    def test_corex_no_legacy_architecture_cleanup_qa_matrix_records_commands_and_manual_checks(
        self,
    ) -> None:
        text = COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX_TOKENS:
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

    def test_nested_node_categories_spec_index_registers_qa_matrix(self) -> None:
        text = (REPO_ROOT / "docs/specs/INDEX.md").read_text(encoding="utf-8-sig")
        for token in NESTED_NODE_CATEGORIES_INDEX_TOKENS:
            self.assertIn(token, text)

    def test_nested_node_categories_public_docs_record_authoring_change(self) -> None:
        for relative_path, tokens in NESTED_NODE_CATEGORIES_PUBLIC_DOC_TOKENS.items():
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")
            for token in tokens:
                self.assertIn(token, text, msg=f"{relative_path} missing token {token!r}")

    def test_nested_node_categories_requirements_record_closeout_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in NESTED_NODE_CATEGORIES_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_nested_node_categories_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in NESTED_NODE_CATEGORIES_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_nested_node_categories_qa_matrix_records_commands_and_manual_checks(self) -> None:
        text = NESTED_NODE_CATEGORIES_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in NESTED_NODE_CATEGORIES_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_shared_graph_typography_control_spec_index_registers_qa_matrix(self) -> None:
        text = (REPO_ROOT / "docs/specs/INDEX.md").read_text(encoding="utf-8-sig")
        for token in SHARED_GRAPH_TYPOGRAPHY_CONTROL_INDEX_TOKENS:
            self.assertIn(token, text)

    def test_shared_graph_typography_control_docs_record_closeout_scope_tokens(self) -> None:
        for (
            relative_path,
            requirement_tokens,
        ) in SHARED_GRAPH_TYPOGRAPHY_CONTROL_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_shared_graph_typography_control_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in SHARED_GRAPH_TYPOGRAPHY_CONTROL_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_shared_graph_typography_control_qa_matrix_records_commands_and_manual_checks(self) -> None:
        text = SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_port_value_locking_spec_index_registers_qa_matrix(self) -> None:
        text = (REPO_ROOT / "docs/specs/INDEX.md").read_text(encoding="utf-8-sig")
        for token in PORT_VALUE_LOCKING_INDEX_TOKENS:
            self.assertIn(token, text)

    def test_port_value_locking_docs_record_closeout_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in PORT_VALUE_LOCKING_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_port_value_locking_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in PORT_VALUE_LOCKING_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_port_value_locking_qa_matrix_records_commands_and_manual_checks(self) -> None:
        text = PORT_VALUE_LOCKING_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in PORT_VALUE_LOCKING_QA_MATRIX_TOKENS:
            self.assertIn(token, text)

    def test_title_icons_for_non_passive_nodes_spec_index_registers_qa_matrix(self) -> None:
        text = (REPO_ROOT / "docs/specs/INDEX.md").read_text(encoding="utf-8-sig")
        for token in TITLE_ICONS_FOR_NON_PASSIVE_NODES_INDEX_TOKENS:
            self.assertIn(token, text)

    def test_title_icons_for_non_passive_nodes_docs_record_closeout_scope_tokens(self) -> None:
        for (
            relative_path,
            requirement_tokens,
        ) in TITLE_ICONS_FOR_NON_PASSIVE_NODES_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_title_icons_for_non_passive_nodes_traceability_rows_reference_packet_artifacts(
        self,
    ) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in TITLE_ICONS_FOR_NON_PASSIVE_NODES_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_title_icons_for_non_passive_nodes_qa_matrix_records_commands_and_manual_checks(
        self,
    ) -> None:
        text = TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX_TOKENS:
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

    def test_ui_context_scalability_followup_docs_record_closeout_scope_tokens(self) -> None:
        for relative_path, requirement_tokens in UI_CONTEXT_SCALABILITY_FOLLOWUP_REQUIREMENT_TOKENS.items():
            path = REPO_ROOT / relative_path
            for requirement_id, tokens in requirement_tokens.items():
                body = requirement_line(path, requirement_id)
                for token in tokens:
                    self.assertIn(token, body, msg=f"{relative_path} {requirement_id} missing token {token!r}")

    def test_ui_context_scalability_followup_traceability_rows_reference_packet_artifacts(self) -> None:
        traceability_path = REPO_ROOT / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        for row_id, tokens in UI_CONTEXT_SCALABILITY_FOLLOWUP_TRACEABILITY_ROW_TOKENS.items():
            row_text = traceability_row(traceability_path, row_id)
            for token in tokens:
                self.assertIn(token, row_text, msg=f"traceability row {row_id} missing token {token!r}")

    def test_ui_context_scalability_followup_qa_matrix_records_commands_and_guardrails(self) -> None:
        text = UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.read_text(encoding="utf-8-sig")
        for token in UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX_TOKENS:
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
