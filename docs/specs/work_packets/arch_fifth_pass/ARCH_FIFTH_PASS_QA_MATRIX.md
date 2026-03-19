# ARCH_FIFTH_PASS QA Matrix

- Updated: `2026-03-20`
- Packet set: `ARCH_FIFTH_PASS` (`P01` through `P13`)
- Scope: closeout regression slice and traceability evidence for the sequential architecture cleanup follow-up after `ARCH_FOURTH_PASS`.

## Accepted Packet Outcomes

| Packet | Accepted Commit | Outcome | Primary Evidence |
|---|---|---|---|
| `P01` | `d0b9977861692d566f51a2365d443e1ba3beda24` | Unified startup entrypoints, isolated startup preferences from UI host logic, and made the performance-harness package boundary honest. | `P01_startup_preferences_boundary_WRAPUP.md`, `ARCHITECTURE.md` |
| `P02` | `c0dceb8dcadbd68d23dc3c68f7c20d288bc1f645` | Moved shell object construction into an explicit composition module and reduced `ShellWindow` to a host/facade. | `P02_shell_composition_root_WRAPUP.md`, `ARCHITECTURE.md` |
| `P03` | `f2dd6078563fed9c5f08c3feb3f58677542f9aae` | Split `WorkspaceLibraryController` responsibilities across focused controllers while preserving the current shell surface. | `P03_shell_controller_surface_split_WRAPUP.md`, `ARCHITECTURE.md` |
| `P04` | `d1f64bdb39dc1276e2e1da8ef1fac935441c076a` | Introduced focused canvas state/command bridges behind the stable compatibility-preserving scene/canvas surface. | `P04_bridge_contract_foundation_WRAPUP.md`, `ARCHITECTURE.md` |
| `P05` | `0bb412c0d70a5c5562575a511783b44ec0faefab` | Migrated packet-owned QML off raw compatibility globals onto the bridge-first shell/canvas contract. | `P05_bridge_first_qml_migration_WRAPUP.md`, `ARCHITECTURE.md` |
| `P06` | `02f91b2792167b523ac719e306be61d5716726ca` | Added the authoritative authoring mutation service and routed primary packet-owned graph edits through it. | `P06_authoring_mutation_service_foundation_WRAPUP.md`, `ARCHITECTURE.md` |
| `P07` | `a3d5ffd6cae0761d40d02328f1dcc694d1e589f1` | Finished mutation-service adoption for transforms/payload normalization and broadened undo/history capture to the full mutable workspace state. | `P07_authoring_mutation_completion_history_WRAPUP.md`, `ARCHITECTURE.md` |
| `P08` | `16114adc6ff34d9bd261e51e464776ccad3819fa` | Moved persistence-only overlay ownership out of the live graph model and narrowed load/save to the current schema boundary. | `P08_current_schema_persistence_boundary_WRAPUP.md`, `ARCHITECTURE.md` |
| `P09` | `867f218980e05967dc594891bc581920da5b7dc1` | Replaced packet-owned `project_doc` run transport with a typed `runtime_snapshot` execution boundary. | `P09_runtime_snapshot_execution_pipeline_WRAPUP.md`, `ARCHITECTURE.md` |
| `P10` | `36a50afc74b0a94e8e523a9ea5550cf56a0ea774` | Added descriptor-first plugin loading and semantic package validation while preserving legacy fallback. | `P10_plugin_descriptor_package_contract_WRAPUP.md`, `ARCHITECTURE.md` |
| `P11` | `da771e5b55fe99f70c055950fbf0d5a93f0ba052` | Split oversized regression suites into focused modules while keeping the current command entrypoints stable. | `P11_regression_suite_modularization_WRAPUP.md`, `docs/specs/requirements/TRACEABILITY_MATRIX.md` |
| `P12` | `0a063c1b7d8d55a011b9fee6dd7ae1a821f01a87` | Centralized verification facts in `scripts/verification_manifest.py` and removed runner/checker duplication without changing proof outcomes. | `P12_verification_manifest_traceability_WRAPUP.md`, `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` |
| `P13` | `see wrap-up` | Publishes the packet-set closeout docs, QA matrix, refreshed traceability anchors, and relative-link cleanup for packet-owned spec surfaces. | `P13_docs_traceability_closeout_WRAPUP.md`, this matrix |

## Accepted Verification Anchors

| Coverage | Accepted Evidence | Status | Packet Anchor |
|---|---|---|---|
| Startup and preferences boundary | `./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_graphics_settings_preferences.py tests/test_graph_theme_preferences.py tests/test_track_h_perf_harness.py -q` | Carried forward from accepted packet verification. | `P01` |
| Shell composition root | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/test_shell_run_controller.py tests/test_shell_project_session_controller.py -q` | Carried forward from accepted packet verification. | `P02` |
| Shell controller surface split | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py tests/test_window_library_inspector.py tests/test_node_package_io_ops.py -q` | Carried forward from accepted packet verification. | `P03` |
| Bridge contract foundation | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_surface_input_contract.py -q -k "ShellLibraryBridgeTests or ShellInspectorBridgeTests or ShellWorkspaceBridgeTests or GraphCanvasBridgeTests"` | Carried forward from accepted packet verification. | `P04` |
| Bridge-first QML migration | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py tests/test_track_h_perf_harness.py -q` | Carried forward from accepted packet verification. | `P05` |
| Mutation service foundation | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py tests/test_workspace_library_controller_unit.py tests/test_graph_scene_bridge_bind_regression.py -q` | Carried forward from accepted packet verification. | `P06` |
| Mutation completion and history | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py tests/test_passive_visual_metadata.py tests/test_passive_runtime_wiring.py tests/test_graph_surface_input_contract.py -q` | Carried forward from accepted packet verification after focused remediation. | `P07` |
| Current-schema persistence boundary | `./venv/Scripts/python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_registry_validation.py -q` | Carried forward from accepted packet verification. | `P08` |
| Runtime snapshot execution pipeline | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_process_run_node.py tests/test_run_controller_unit.py tests/test_passive_runtime_wiring.py -q` | Carried forward from accepted packet verification. | `P09` |
| Plugin descriptor and package contract | `./venv/Scripts/python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py tests/test_node_package_io_ops.py tests/test_registry_validation.py -q` | Carried forward from accepted packet verification. | `P10` |
| Regression suite modularization | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_track_b.py tests/test_serializer.py -q` | Carried forward from accepted packet verification. | `P11` |
| Verification manifest and traceability | `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py tests/test_traceability_checker.py -q` | Carried forward from accepted packet verification. | `P12` |
| Closeout proof audit | `./venv/Scripts/python.exe scripts/check_traceability.py` | Rerun in `P13` closeout. | `P13` |
| Closeout workflow audit | `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run` | Rerun in `P13` closeout. | `P13` |

## 2026-03-20 P13 Closeout Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | The proof audit passed after the packet-owned spec index links, architecture snapshot, traceability anchors, and closeout QA matrix were refreshed. |
| `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run` | PASS | The dry-run output kept the manifest-owned `fast` workflow, ignore list, and worker-resolution behavior aligned with the refreshed proof docs. |

## Traceability Anchors

| Requirement Anchor | Closeout Evidence |
|---|---|
| `REQ-ARCH-002`, `REQ-ARCH-010`, `REQ-ARCH-011`, `AC-REQ-ARCH-002-01`, `AC-REQ-ARCH-011-01` | `ARCHITECTURE.md`, the carried-forward `P02` through `P05` verification anchors in this matrix, and the refreshed rows in `docs/specs/requirements/TRACEABILITY_MATRIX.md`. |
| `REQ-PERSIST-009` through `REQ-PERSIST-013`, `REQ-UI-021`, `REQ-UI-022`, `REQ-NODE-019` | The accepted `P01`, `P06`, `P07`, and `P08` outcomes in this matrix plus the post-closeout boundary summary in `ARCHITECTURE.md`. |
| `REQ-EXEC-002`, `REQ-EXEC-009`, `REQ-NODE-016`, `REQ-NODE-018`, `REQ-NODE-019` | The accepted `P09` and `P10` outcomes and verification anchors in this matrix together with the refreshed `TRACEABILITY_MATRIX.md` rows. |
| `REQ-QA-008` through `REQ-QA-018` and `AC-REQ-QA-013-01` through `AC-REQ-QA-018-01` | The carried-forward `P11` and `P12` verification anchors, the `P13` closeout reruns in this matrix, `README.md`, `docs/GETTING_STARTED.md`, `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md`, and the refreshed `TRACEABILITY_MATRIX.md`. |

## Final Residual Risks

- Packet-external execution callers can still enter through the `project_doc` compatibility adapter, so the runtime-snapshot boundary is authoritative for packet-owned flows but not yet universal.
- Legacy packages without `PLUGIN_DESCRIPTORS` still load through the constructor fallback path, which is intentional for compatibility but keeps a wider plugin discovery seam alive.
- Raw compatibility context properties (`mainWindow`, `sceneBridge`, `viewBridge`) and the widened `GraphCanvasBridge` surface still ship for deferred QML consumers outside the packet-owned migration set.
- Some higher-level authoring callers still depend on internal mutation-service/raw-helper seams outside the packet-owned write scope, even though packet-owned graph edits now go through the authoritative service.
- Pre-current-schema `.sfe` documents require an out-of-band conversion path before they can load on this branch.
- Preserved unresolved payloads remain intentionally opaque in the live model, so there is still no packet-owned inspection or repair UI for missing-plugin content.
- Shell-backed regression suites still require fresh-process execution because repeated Windows Qt/QML `ShellWindow()` construction is not yet reliable in one interpreter process.
