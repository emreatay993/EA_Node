# Requirement Traceability Matrix

| Requirement ID | Spec Module | Implementation Artifact |
|---|---|---|
| REQ-ARCH-001 | 10_ARCHITECTURE | `ea_node_editor/app.py`, `ea_node_editor/ui/shell/window.py`, `tests/test_main_window_shell.py` |
| REQ-ARCH-006 | 10_ARCHITECTURE | `ea_node_editor/workspace/manager.py`, `ea_node_editor/ui/shell/window.py`, `tests/test_workspace_manager.py`, `tests/test_main_window_shell.py` |
| REQ-ARCH-005 | 10_ARCHITECTURE | `ea_node_editor/ui/shell/window.py` status API methods, `ea_node_editor/ui_qml/status_model.py`, `tests/test_main_window_shell.py` |
| REQ-UI-001 | 20_UI_UX | `ea_node_editor/ui/shell/window.py` shell layout zones, `tests/test_main_window_shell.py` |
| REQ-UI-002 | 20_UI_UX | `ea_node_editor/ui/shell/window.py` workspace tab logic |
| REQ-UI-003 | 20_UI_UX | `ea_node_editor/ui/shell/window.py` canvas/tab/console stacking, `tests/test_main_window_shell.py` |
| REQ-UI-004 | 20_UI_UX | `ea_node_editor/graph/model.py` view model, `ea_node_editor/ui/shell/window.py` view switch/create logic, `tests/test_main_window_shell.py` |
| REQ-UI-005 | 20_UI_UX | `ea_node_editor/ui/shell/window.py` per-view camera save/restore, `tests/test_main_window_shell.py`, `tests/test_serializer.py` |
| REQ-UI-006 | 20_UI_UX | `ea_node_editor/nodes/registry.py`, `ea_node_editor/ui_qml/MainShell.qml`, `tests/test_registry_filters.py`, `tests/test_main_window_shell.py` (`test_node_library_add_uses_selected_item_when_current_row_is_unset`) |
| REQ-UI-008 | 20_UI_UX | `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui/shell/window.py`, `tests/test_inspector_reflection.py`, `tests/test_graph_track_b.py` |
| REQ-GRAPH-001 | 30_GRAPH_MODEL | `ea_node_editor/graph/model.py` dataclasses |
| REQ-GRAPH-002 | 30_GRAPH_MODEL | `ea_node_editor/graph/model.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/edge_routing.py`, `tests/test_graph_track_b.py` |
| REQ-GRAPH-003 | 30_GRAPH_MODEL | `ea_node_editor/graph/model.py` workspace/view state, `ea_node_editor/ui/shell/window.py`, `tests/test_main_window_shell.py` |
| REQ-GRAPH-004 | 30_GRAPH_MODEL | `ea_node_editor/graph/model.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `tests/test_graph_track_b.py` |
| REQ-GRAPH-005 | 30_GRAPH_MODEL | `ea_node_editor/graph/model.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui/shell/window.py`, `tests/test_graph_track_b.py` |
| REQ-GRAPH-006 | 30_GRAPH_MODEL | `ea_node_editor/graph/model.py`, `ea_node_editor/workspace/manager.py`, `ea_node_editor/ui/shell/window.py`, `tests/test_workspace_manager.py`, `tests/test_main_window_shell.py` |
| REQ-GRAPH-007 | 30_GRAPH_MODEL | `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/edge_routing.py` |
| REQ-GRAPH-008 | 30_GRAPH_MODEL | `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `tests/test_graph_track_b.py` |
| REQ-NODE-001 | 40_NODE_SDK | `ea_node_editor/nodes/types.py` |
| REQ-NODE-002 | 40_NODE_SDK | `ea_node_editor/nodes/builtins/core.py`, `ea_node_editor/nodes/builtins/integrations.py`, `ea_node_editor/nodes/builtins/integrations_*.py`, `ea_node_editor/execution/worker.py` |
| REQ-NODE-003 | 40_NODE_SDK | `ea_node_editor/nodes/registry.py` |
| REQ-NODE-004 | 40_NODE_SDK | `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/execution/worker.py`, `tests/test_inspector_reflection.py` |
| REQ-NODE-005 | 40_NODE_SDK | `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `tests/test_graph_track_b.py` |
| REQ-NODE-006 | 40_NODE_SDK | `ea_node_editor/nodes/types.py`, `ea_node_editor/nodes/builtins/core.py`, `ea_node_editor/nodes/builtins/integrations.py`, `ea_node_editor/nodes/builtins/integrations_*.py`, `tests/test_registry_validation.py` |
| REQ-NODE-009 | 45_NODE_EXECUTION_MODEL | `ea_node_editor/nodes/types.py` port kind declarations (`exec`, `completed`, `failed`, `data`), `tests/test_registry_validation.py` |
| REQ-NODE-010 | 45_NODE_EXECUTION_MODEL | `ea_node_editor/graph/rules.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py` connection validation, `tests/test_graph_track_b.py`, `tests/test_main_window_shell.py` |
| REQ-NODE-011 | 45_NODE_EXECUTION_MODEL | `ea_node_editor/execution/worker.py` data-edge propagation and dependency evaluation, `tests/test_execution_worker.py` |
| REQ-NODE-012 | 45_NODE_EXECUTION_MODEL | `ea_node_editor/execution/worker.py` exec scheduling/failure flow, `ea_node_editor/nodes/builtins/integrations_process.py`, `tests/test_process_run_node_rc2.py`, `tests/test_execution_worker.py` |
| REQ-NODE-013 | 45_NODE_EXECUTION_MODEL | `ea_node_editor/nodes/decorators.py`, `ea_node_editor/nodes/__init__.py`, `docs/specs/requirements/40_NODE_SDK.md`, `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md` |
| REQ-NODE-014 | 45_NODE_EXECUTION_MODEL | `ea_node_editor/nodes/bootstrap.py`, `ea_node_editor/nodes/builtins/core.py`, `ea_node_editor/nodes/builtins/integrations.py`, `ea_node_editor/nodes/builtins/integrations_*.py`, `ea_node_editor/nodes/builtins/hpc.py` |
| REQ-EXEC-001 | 50_EXECUTION_ENGINE | `ea_node_editor/execution/client.py`, `worker.py` |
| REQ-EXEC-002 | 50_EXECUTION_ENGINE | `ea_node_editor/execution/protocol.py` (typed dataclasses + queue boundary adapters), `ea_node_editor/execution/client.py`, `ea_node_editor/execution/worker.py`, `tests/test_execution_worker.py`, `tests/test_execution_client.py` |
| REQ-EXEC-003 | 50_EXECUTION_ENGINE | `ea_node_editor/ui/shell/window.py` Qt queued `execution_event` path, `ea_node_editor/execution/client.py` listener thread, `tests/test_main_window_shell.py` |
| REQ-EXEC-004 | 50_EXECUTION_ENGINE | `ea_node_editor/execution/worker.py` exec-edge scheduling, `tests/test_execution_worker.py` |
| REQ-EXEC-005 | 50_EXECUTION_ENGINE | `ea_node_editor/execution/worker.py` data-edge input propagation, `tests/test_execution_worker.py` |
| REQ-EXEC-006 | 50_EXECUTION_ENGINE | `ea_node_editor/execution/worker.py` structured `run_failed` traceback payload, `ea_node_editor/ui/shell/window.py` failure routing/focus, `tests/test_execution_worker.py`, `tests/test_main_window_shell.py` |
| REQ-EXEC-007 | 50_EXECUTION_ENGINE | `ea_node_editor/execution/worker.py` event emissions |
| REQ-EXEC-009 | 50_EXECUTION_ENGINE | `ea_node_editor/execution/protocol.py` dataclasses + dict adapters, `ea_node_editor/execution/client.py` typed command/event usage, `ea_node_editor/execution/worker.py` typed command/event usage |
| REQ-UI-010 | 20_UI_UX | `ea_node_editor/ui/shell/window.py` failed-node focus + parent-chain reveal via `parent_node_id`, `tests/test_main_window_shell.py` |
| REQ-PERSIST-001 | 60_PERSISTENCE | `ea_node_editor/persistence/serializer.py` (facade), `ea_node_editor/persistence/project_codec.py` |
| REQ-PERSIST-002 | 60_PERSISTENCE | `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/persistence/serializer.py`, `tests/test_serializer.py`, `tests/test_main_window_shell.py` |
| REQ-PERSIST-003 | 60_PERSISTENCE | `ea_node_editor/persistence/project_codec.py` deterministic workspace/view/node/edge ordering, `tests/test_serializer.py` deterministic save assertions |
| REQ-PERSIST-004 | 60_PERSISTENCE | `ea_node_editor/persistence/migration.py` migration/normalization pipeline + legacy repair, `tests/fixtures/persistence/schema_v0_*.json`, `tests/test_serializer.py` migration tests |
| REQ-PERSIST-005 | 60_PERSISTENCE | `ea_node_editor/persistence/migration.py` migrate-before-model construction (`load`/`from_document`), `ea_node_editor/ui/shell/window.py` guarded restore/open flow |
| REQ-PERSIST-006 | 60_PERSISTENCE | `ea_node_editor/persistence/session_store.py`, `ea_node_editor/ui/shell/window.py` session restore/persist + autosave/recovery prompt flow, `tests/test_main_window_shell.py` session/autosave recovery tests including `test_recovery_prompt_is_deferred_until_main_window_is_visible` |
| REQ-PERSIST-008 | 60_PERSISTENCE | `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/persistence/migration.py`, `ea_node_editor/persistence/session_store.py`, `ea_node_editor/persistence/serializer.py` |
| REQ-INT-001 | 70_INTEGRATIONS | `ea_node_editor/nodes/builtins/core.py` |
| REQ-INT-002 | 70_INTEGRATIONS | `ea_node_editor/nodes/builtins/integrations.py` (facade), `ea_node_editor/nodes/builtins/integrations_spreadsheet.py`, `ea_node_editor/nodes/builtins/integrations_file_io.py`, `ea_node_editor/nodes/builtins/integrations_email.py`, `ea_node_editor/nodes/builtins/integrations_process.py` |
| REQ-INT-003 | 70_INTEGRATIONS | `ea_node_editor/nodes/builtins/integrations_spreadsheet.py` CSV/XLSX handling and dependency gate, `tests/test_integrations_track_f.py` |
| REQ-INT-004 | 70_INTEGRATIONS | `ea_node_editor/nodes/builtins/integrations_file_io.py` File Read/Write text+JSON behavior, `tests/test_integrations_track_f.py` |
| REQ-INT-005 | 70_INTEGRATIONS | `ea_node_editor/nodes/builtins/integrations_email.py` Email Send SMTP/TLS/auth validation, `tests/test_integrations_track_f.py` |
| REQ-INT-007 | 70_INTEGRATIONS | `ea_node_editor/nodes/builtins/integrations_spreadsheet.py`, `ea_node_editor/nodes/builtins/integrations_file_io.py`, `ea_node_editor/nodes/builtins/integrations_email.py`, `ea_node_editor/nodes/builtins/integrations_process.py`, `ea_node_editor/nodes/builtins/integrations.py` |
| REQ-PERF-001 | 80_PERFORMANCE | `ea_node_editor/telemetry/performance_harness.py` target-scale synthetic graph generator (`generate_synthetic_project`), `tests/test_track_h_perf_harness.py`, `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` |
| REQ-PERF-002 | 80_PERFORMANCE | `ea_node_editor/telemetry/performance_harness.py` pan/zoom interaction benchmark with p50/p95 reporting, `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`, `docs/specs/perf/track_h_benchmark_report.json` |
| REQ-PERF-003 | 80_PERFORMANCE | `ea_node_editor/telemetry/performance_harness.py` project+graph load benchmark, `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`, `docs/specs/perf/track_h_benchmark_report.json` |
| REQ-PERF-004 | 80_PERFORMANCE | `ea_node_editor/ui_qml/viewport_bridge.py` view optimization flags |
| REQ-PERF-005 | 80_PERFORMANCE | `ea_node_editor/ui_qml/graph_scene_bridge.py` explicit scene rect and local item updates, `tests/test_graph_track_b.py` |
| REQ-QA-001 | 90_QA_ACCEPTANCE | `tests/test_registry_filters.py`, `tests/test_registry_validation.py`, `tests/test_graph_track_b.py`, `tests/test_inspector_reflection.py`, other `tests/test_*.py` |
| REQ-QA-002 | 90_QA_ACCEPTANCE | `tests/test_execution_worker.py`, `tests/test_execution_client.py`, `tests/test_main_window_shell.py` |
| REQ-QA-003 | 90_QA_ACCEPTANCE | `tests/test_integrations_track_f.py` smoke workflows (Excel/File input -> Python transform -> Excel/File output) |
| REQ-QA-004 | 90_QA_ACCEPTANCE | `tests/test_workspace_manager.py`, `tests/test_main_window_shell.py` |
| REQ-QA-005 | 90_QA_ACCEPTANCE | `tests/test_main_window_shell.py`, `tests/test_serializer.py` |
| REQ-QA-006 | 90_QA_ACCEPTANCE | `tests/test_graph_track_b.py`, `tests/test_inspector_reflection.py` |
| REQ-QA-007 | 90_QA_ACCEPTANCE | `ea_node_editor/ui/shell/window.py`, `tests/test_main_window_shell.py` |
| AC-REQ-PERF-002-01 | 80_PERFORMANCE | `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness` output in `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` and `docs/specs/perf/track_h_benchmark_report.json` |
| AC-REQ-PERF-003-01 | 80_PERFORMANCE | `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness` load timing evidence in `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` and `docs/specs/perf/track_h_benchmark_report.json` |
| AC-REQ-QA-001-01 | 90_QA_ACCEPTANCE | Full-suite run `venv\Scripts\python -m unittest discover -s tests -v`, summarized in `docs/specs/perf/QA_GATE_REPORT.md` |
| AC-REQ-QA-004-01 | 90_QA_ACCEPTANCE | `tests/test_workspace_manager.py`, `tests/test_main_window_shell.py`, gate status in `docs/specs/perf/QA_GATE_REPORT.md` |
| AC-REQ-QA-007-01 | 90_QA_ACCEPTANCE | `tests/test_main_window_shell.py` (`test_run_failed_event_centers_failed_node_and_reports_exception_details`), `docs/specs/perf/QA_GATE_REPORT.md` |
| AC-REQ-NODE-009-01 | 45_NODE_EXECUTION_MODEL | `tests/test_registry_validation.py` port-kind declaration validation |
| AC-REQ-NODE-010-01 | 45_NODE_EXECUTION_MODEL | `tests/test_main_window_shell.py` (`test_qml_connect_ports_rejects_exec_to_data_kind_mismatch`), `tests/test_graph_track_b.py` |
| AC-REQ-NODE-011-01 | 45_NODE_EXECUTION_MODEL | `tests/test_execution_worker.py` data-edge propagation assertions |
| AC-REQ-NODE-012-01 | 45_NODE_EXECUTION_MODEL | `tests/test_process_run_node_rc2.py`, `tests/test_execution_worker.py` execution/failure/cancel behavior |
| AC-REQ-NODE-013-01 | 45_NODE_EXECUTION_MODEL | `docs/specs/requirements/40_NODE_SDK.md`, `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md` authoring guidance |
| AC-REQ-NODE-014-01 | 45_NODE_EXECUTION_MODEL | `ea_node_editor/nodes/bootstrap.py`, `tests/test_registry_filters.py` built-in catalog coverage |
| AC-REQ-QA-001-02 | 90_QA_ACCEPTANCE | Windows RC packaging/release artifacts: `ea_node_editor.spec`, `scripts/build_windows_package.ps1`, build/smoke evidence in `docs/specs/perf/RC_PACKAGING_REPORT.md`, operator guide `docs/PACKAGING_WINDOWS.md`, `RELEASE_NOTES.md` |
| AC-REQ-PERF-002-02 | 80_PERFORMANCE | Desktop/manual benchmark execution checklist in `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` for real display/GPU validation |
| AC-REQ-QA-001-03 | 90_QA_ACCEPTANCE | Packaged desktop pilot gate execution summary in `docs/specs/perf/PILOT_SIGNOFF.md` with run artifact `artifacts/pilot_signoff/20260301_211523/pilot_signoff_results.json` |
| AC-REQ-QA-005-02 | 90_QA_ACCEPTANCE | Save/reopen/restore+recovery packaged pilot evidence and outcome in `docs/specs/perf/PILOT_SIGNOFF.md` (`05_recovery_prompt.png`, `06_recovered_state.png`) |
| AC-REQ-QA-007-02 | 90_QA_ACCEPTANCE | Controlled failure dialog + failed-node focus pilot evidence in `docs/specs/perf/PILOT_SIGNOFF.md` (`04_failure_error_dialog.png`) |
| AC-REQ-QA-001-04 | 90_QA_ACCEPTANCE | Remaining pilot-readiness risk backlog and prioritization in `docs/specs/perf/PILOT_BACKLOG.md` |
| AC-REQ-QA-001-05 | 90_QA_ACCEPTANCE | RC1 frozen release bundle + manifest in `artifacts/releases/EA_Node_Editor_RC1_2026-03-01/` (`manifest.json`, `EA_Node_Editor.exe.sha256`, packaged `dist/EA_Node_Editor/`) |
| AC-REQ-QA-001-06 | 90_QA_ACCEPTANCE | Internal pilot operator runbook in `docs/PILOT_RUNBOOK.md` (install/start, smoke workflows, failure reporting template, rollback) |
| REQ-ARCH-009 | 10_ARCHITECTURE | `ea_node_editor/ui/shell/window.py` (`show_workflow_settings_dialog`, `set_script_editor_panel_visible`), `tests/test_theme_shell_rc2.py`, `tests/test_settings_dialog_rc2.py`, `tests/test_script_editor_dock_rc2.py` |
| REQ-UI-011 | 20_UI_UX | Tokenized Stitch dark theme: `ea_node_editor/ui/theme/tokens.py`, `ea_node_editor/ui/theme/styles.py`, `ea_node_editor/app.py`, `tests/test_theme_shell_rc2.py` |
| REQ-UI-012 | 20_UI_UX | Workflow settings modal + API: `ea_node_editor/ui/dialogs/workflow_settings_dialog.py`, `ea_node_editor/ui/shell/window.py::show_workflow_settings_dialog`, `tests/test_settings_dialog_rc2.py` |
| REQ-UI-013 | 20_UI_UX | Script editor dock + API: `ea_node_editor/ui_qml/script_editor_model.py`, `ea_node_editor/ui/editor/code_editor.py`, `ea_node_editor/ui/shell/window.py::set_script_editor_panel_visible`, `tests/test_script_editor_dock_rc2.py` |
| REQ-GRAPH-009 | 30_GRAPH_MODEL | Stitch visual refresh + LOD: `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/viewport_bridge.py`, `tests/test_graph_track_b.py` |
| REQ-NODE-007 | 40_NODE_SDK | Decorator helpers: `ea_node_editor/nodes/decorators.py`, `ea_node_editor/nodes/__init__.py`, `tests/test_decorator_sdk_rc2.py` |
| REQ-NODE-008 | 40_NODE_SDK | Decorator compatibility with registry: `ea_node_editor/nodes/builtins/core.py` (`ConstantNodePlugin`), `tests/test_decorator_sdk_rc2.py`, `tests/test_registry_validation.py` |
| REQ-INT-006 | 70_INTEGRATIONS | External process runner node: `ea_node_editor/nodes/builtins/integrations_process.py::ProcessRunNodePlugin`, compatibility export in `ea_node_editor/nodes/builtins/integrations.py`, `ea_node_editor/nodes/bootstrap.py`, `tests/test_process_run_node_rc2.py` |
| REQ-EXEC-008 | 50_EXECUTION_ENGINE | Active subprocess cancellation on `stop_run`: `ea_node_editor/execution/worker.py`, `tests/test_process_run_node_rc2.py::test_stop_run_cancels_active_process_node` |
| REQ-PERSIST-007 | 60_PERSISTENCE | Schema v2 metadata normalization (`metadata.ui`, `metadata.workflow_settings`) + migration: `ea_node_editor/settings.py`, `ea_node_editor/persistence/migration.py`, `ea_node_editor/persistence/serializer.py`, `tests/test_serializer_v2_migration_rc2.py`, `tests/test_serializer.py` |
