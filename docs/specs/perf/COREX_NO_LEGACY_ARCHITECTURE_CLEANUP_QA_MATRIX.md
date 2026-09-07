# COREX No-Legacy Architecture Cleanup QA Matrix

- Updated: `2026-04-24`
- Packet set: `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP`
- Packet window: `P00` through `P14`
- Active baseline: this matrix supersedes older compatibility-closeout matrices for current no-legacy architecture claims. Historical matrices remain archive evidence for their packet windows only.

## Locked Scope

This closeout covers focused bridges, explicit source contracts, current-schema persistence, descriptor-only plugins/add-ons, snapshot-only runtime payloads, typed viewer transport, canonical launch/import paths, traceability rows, and documentation hygiene for the no-legacy cleanup packet set.

Historical packet matrices may still be cited as archive references for earlier waves, but they do not describe the active architecture after P14.

## Packet Outcomes

| Packet | Accepted Commit | Outcome | Wrap-up |
| --- | --- | --- | --- |
| P00 Bootstrap | `bootstrap-docs-uncommitted` | Packet docs, status ledger, execution waves, prompts, and planning registration were bootstrapped before worker commits. | control-doc bootstrap only |
| P01 No-Legacy Guardrails | `c413beae3eab13eb40aaceb86bd143587900d6de` | Converted compatibility assertions into packet-owned no-legacy guardrails. | `P01_no_legacy_guardrails_WRAPUP.md` |
| P02 Graph Canvas Bridge Retirement | `50ff2d1ee3005827983b596c9ef87b7b15b4d008` | Retired graph-canvas QML compatibility aliases while retaining the host-only edge adapter. | `P02_graph_canvas_bridge_retirement_WRAPUP.md` |
| P03 Shell Graph Action Facade Retirement | `9b99e92acd4eefccfc526f004774924034fe9170` | Routed graph actions through explicit graph-action dependencies and removed duplicate shell facade action slots. | `P03_shell_graph_action_facade_retirement_WRAPUP.md` |
| P04 QML Context Source Contract Cleanup | `ff191540dd3ddd498ed67eb5e84cf8ce3cef517e` | Narrowed QML context source contracts to focused bridges and shell context bundles. | `P04_qml_context_source_contract_cleanup_WRAPUP.md` |
| P05 Workspace Custom Workflow Authority | `dddb6716cfebf25831edb8d7395d857f6c773d2e` | Made workspace ordering and custom workflow authority explicit, scoped, and ID-based. | `P05_workspace_custom_workflow_authority_WRAPUP.md` |
| P06 Current Schema Persistence Cleanup | `f966d97d6c474606cd344df7912efec8d44d54da` | Kept current schema validation/normalization while removing old input-shape tolerance. | `P06_current_schema_persistence_cleanup_WRAPUP.md` |
| P07 Graph Persistence Overlay Removal | `966fcbd1a7f03476ed2287e6f96eb927d3fe4a28` | Removed unresolved persistence overlay state from graph-owned models and normalization. | `P07_graph_persistence_overlay_removal_WRAPUP.md` |
| P08 Graph Mutation and Fragment Consolidation | `5e351b22990d153d8f09e670c538f5bf2ed05dbe` | Collapsed duplicate graph mutation, parser, and facade paths onto one domain API. | `P08_graph_mutation_and_fragment_consolidation_WRAPUP.md` |
| P09 Node SDK Registry Cleanup | `2c5f7000f6698b167eccf1b4a69c7cee3d823a6e` | Removed registry category aliases, broad SDK shims, and class-first built-in registration. | `P09_node_sdk_registry_cleanup_WRAPUP.md` |
| P10 Plugin Add-on Descriptor Only | `b291c9e09ed18a0093d3189063c694038b2b0241` | Required descriptor/add-on records and retired plugin class probing plus add-on ID aliases. | `P10_plugin_addon_descriptor_only_WRAPUP.md` |
| P11 Runtime Snapshot Only Protocol | `f3b2d0c36db28513e054bd84559b9e4f02e7e220` | Made `RuntimeSnapshot` mandatory and removed `project_doc` / project-path rebuild tolerance. | `P11_runtime_snapshot_only_protocol_WRAPUP.md` |
| P12 Viewer Session Transport Cleanup | `4f2e2552393dd972d8f42dea4df9d9918fd0648b` | Replaced viewer projection aliases and widget property handshakes with typed transport/session state. | `P12_viewer_session_transport_cleanup_WRAPUP.md` |
| P13 Launch Package Import Shim Cleanup | `dfd3ab4b746a13628f4eb2d803bd653809092d89` | Collapsed launch, package, telemetry, lazy import, and packaging path shims onto canonical entry points. | `P13_launch_package_import_shim_cleanup_WRAPUP.md` |
| P14 Docs Traceability Closeout | `5ca8fcebb7607b7af3d8ffda9fc1d38afc5ca616` | Publishes the final no-legacy docs, QA matrix, traceability rows, semantic checker baseline, and hygiene guards. | `P14_docs_traceability_closeout_WRAPUP.md` |

## Retained Automated Verification

| Packet | Accepted Commit | Retained Verification |
| --- | --- | --- |
| P01 | `c413beae3eab13eb40aaceb86bd143587900d6de` | `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py tests/test_architecture_boundaries.py tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q` |
| P02 | `50ff2d1ee3005827983b596c9ef87b7b15b4d008` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_scene_bridge_bind_regression.py tests/test_main_window_shell.py tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/bridge_contracts_graph_canvas.py --ignore=venv -q` |
| P03 | `9b99e92acd4eefccfc526f004774924034fe9170` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q` |
| P04 | `ff191540dd3ddd498ed67eb5e84cf8ce3cef517e` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_support.py --ignore=venv -q` |
| P05 | `dddb6716cfebf25831edb8d7395d857f6c773d2e` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_workspace_manager.py tests/test_workspace_library_controller_unit.py tests/workspace_library_controller_unit/custom_workflow_io.py tests/main_window_shell/drop_connect_and_workflow_io.py tests/serializer/workflow_cases.py --ignore=venv -q` |
| P06 | `f966d97d6c474606cd344df7912efec8d44d54da` | `.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py tests/test_graphics_settings_preferences.py tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_project_artifact_store.py tests/test_project_session_controller_unit.py tests/test_registry_validation.py --ignore=venv -q` |
| P07 | `966fcbd1a7f03476ed2287e6f96eb927d3fe4a28` | `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py tests/test_serializer.py tests/test_project_file_issues.py tests/test_workspace_manager.py --ignore=venv -q`; `git diff --check` |
| P08 | `5e351b22990d153d8f09e670c538f5bf2ed05dbe` | `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py tests/test_workspace_manager.py tests/test_passive_runtime_wiring.py tests/test_serializer.py --ignore=venv -q`; `git diff --check` |
| P09 | `2c5f7000f6698b167eccf1b4a69c7cee3d823a6e` | `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py tests/test_library_projection.py tests/test_passive_node_contracts.py tests/test_port_labels.py tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py --ignore=venv -q`; `git diff --check` |
| P10 | `b291c9e09ed18a0093d3189063c694038b2b0241` | `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py tests/test_registry_validation.py tests/test_engineering_viewer_node.py tests/test_execution_viewer_service.py --ignore=venv -q`; `git diff --check` |
| P11 | `f3b2d0c36db28513e054bd84559b9e4f02e7e220` | `.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py tests/test_execution_viewer_protocol.py tests/test_run_controller_unit.py tests/test_shell_run_controller.py tests/test_architecture_boundaries.py --ignore=venv -q`; `git diff --check` |
| P12 | `4f2e2552393dd972d8f42dea4df9d9918fd0648b` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_execution_viewer_protocol.py tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_engineering_viewer_widget_binder.py tests/test_engineering_viewer_node.py tests/test_graph_surface_input_controls.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q` |
| P13 | `dfd3ab4b746a13628f4eb2d803bd653809092d89` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_track_h_perf_harness.py tests/test_persistence_package_imports.py tests/test_dead_code_hygiene.py tests/test_run_verification.py tests/test_shell_theme.py tests/test_graphics_settings_dialog.py tests/test_graph_theme_shell.py --ignore=venv -q`; `.\venv\Scripts\python.exe scripts/run_verification.py --mode full --dry-run` |

## Final Closeout Commands

| Command | Purpose |
| --- | --- |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_dead_code_hygiene.py --ignore=venv -q` | Validate traceability checker mirrors, markdown hygiene, and retired no-legacy guardrails. |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Validate semantic traceability baseline and active no-legacy matrix. |
| `.\venv\Scripts\python.exe scripts/check_markdown_links.py` | Validate docs/index/matrix links after P14 registration. |

## 2026-04-24 Execution Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_dead_code_hygiene.py --ignore=venv -q` | `PASS` | P14 closeout validation. |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | `PASS` | P14 semantic traceability review gate. |
| `.\venv\Scripts\python.exe scripts/check_markdown_links.py` | `PASS` | P14 markdown-link validation. |

## Manual Smoke Guidance

Ready for manual testing after the final closeout commands pass.

1. Launch from source with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`; expected result: the shell opens without requiring a root `main.py` path.
2. Open a graph and exercise context menu actions and shortcuts; expected result: graph actions route through focused bridges and no raw QML global fallback is required.
3. Save and reopen a current-schema `.cxproj` project; expected result: current schema normalizes and round-trips, while pre-current schema input is rejected with a clear load error.
4. Import a descriptor-only plugin package; expected result: descriptors/backends load from provenance and no constructor/class-scan fallback is required.
5. Toggle the retained Tabular Data and MARS add-ons when their dependencies are available or unavailable; expected result: unavailable nodes remain visible as locked projections and rebind after the add-on returns.
6. Run a workflow; expected result: the worker receives a `RuntimeSnapshot` and uses `project_path` only as artifact context.
7. Open a Model Viewer node; expected result: typed viewer transport/session state drives the UI, and restored live viewers show rerun-required state until rerun.

## Residual Risks

- Desktop Model Viewer validation still depends on local PyVista/Qt availability; automated tests cover contract behavior with fixtures.
- Shell-backed Qt/QML suites still require fresh-process execution on Windows because repeated `ShellWindow()` construction in one interpreter remains unreliable.
- Historical matrices can contain archive wording for prior compatibility cleanup windows; this matrix and P14 traceability checks are the active no-legacy baseline.
- Pre-current project schemas require offline conversion before normal app load.

## 2026-08-29 Current-State Addendum

This addendum updates current architecture authority only. Every historical packet row, commit, command, and outcome above remains verbatim evidence for its original window.

| Current surface | Current authority and evidence |
| --- | --- |
| Graph-canvas Python/QML ownership | `GraphCanvasStateBridge` owns state projections, `GraphCanvasCommandBridge` owns commands and batch rewiring, `ViewportBridge` owns view facts/commands, and `GraphCanvas.qml` composes them directly. The aggregate `graph_canvas_bridge.py`, QML facade adapter, and private facade aliases are absent. |
| Direct bridge tests | `tests/test_graph_canvas_split_bridges.py` collects exactly 15 direct-owner tests; graph-scene, graph-action, and graphics-preference cases live with their current owners. |
| Frozen QML-visible surface | `tests/test_graph_canvas_surface_snapshot.py` checks `tests/fixtures/graph_canvas_surface_snapshot.json`; the retired aggregate class is not part of `BRIDGE_CLASSES`. |
| No-legacy guardrail | `scripts/verification_manifest.py` requires `ea_node_editor/ui_qml/graph_canvas_bridge.py` to be path-absent and forbids the six removed QML facade names in `GraphCanvas.qml`. |
| Shell-isolation catalog | The registry has 51 targets. The retired `GraphCanvasBridgeTests` nodeid left the existing `main_window__bridge_local_pack__contracts_and_library_qml` pack; the pack itself remains. |
| Focused retirement proof | T02 passed 157 tests plus 63 subtests, with exactly 15 moved-root tests collected. T03 passed 165 tests plus 671 subtests; the focused meta/drill follow-up passed 22 tests and the renamed snapshot matched exactly. |
| Cycle-safe invalidation ownership | `CorexRuntime` compiles and reuses the phase workspace, while `ExecutionPlan.for_invalidation` falls back to compiled declaration order only for invalidation topology cycles. Ordinary prepare and prepared worker validation remain cycle-rejecting. |
| Shared shell save fake | `tests/main_window_shell/base.py` implements the current solution-store DTO protocol for capture, currency checks, staging, adoption preparation/adoption, cancellation, and garbage collection with per-token context and binding-revision tracking. |
| Undo replay direction | `WorkspaceEditOps.undo` supplies downstream effects with a transient reversed `HistoryEntry` (`after` to `before`); the canonical forward entry remains unchanged for redo. |
| Flow-edge GUI ownership | `tests/test_flow_edge_labels.py` is deselected from the six-worker `gui.pytest` lane and runs in `gui.serial.pytest`, keeping its nested Qt subprocess probes serial without changing timeouts. |
| Native relative performance | The final Windows/D3D11 medians remained within the accepted 5% caps: load `151.733 ms <= 170.785 ms`, combined pan/zoom `88.205 ms <= 92.328 ms`, and node-drag control `27.893 ms <= 28.180 ms`. |
| Final full verification | `artifacts/verification_logs/20260830_030957` records fast `4284 passed, 2 skipped`; fast serial `225 passed`; QML QuickTest `PASS`; GUI `597 passed, 1 skipped`; GUI serial `38 passed, 1 skipped`; slow `56 passed`; and shell isolation `58 passed`. |
| Current authority integrity | The execution agent map and generated route indexes are exact. Protected user work in `docs/specs/INDEX.md` and `docs/PLAN_COREX_Physical_Simulation_Backend.md` remains untouched. |
