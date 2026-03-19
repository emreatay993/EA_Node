# ARCH_FOURTH_PASS QA Matrix

- Updated: `2026-03-19`
- Packet set: `ARCH_FOURTH_PASS` (`P01` through `P08`)
- Scope: closeout regression slice and traceability evidence for the targeted architecture follow-up packets after `ARCH_THIRD_PASS`.

## Accepted Packet Outcomes

| Packet | Accepted Commit | Outcome | Primary Evidence |
|---|---|---|---|
| `P01` | `cf2e4ed51d389e2e49371af0151fc9f5d4fa4c4e` | Preserved unresolved plugin-authored nodes and mixed edges through an authored/runtime document split plus a live unresolved-content sidecar. | `docs/specs/work_packets/arch_fourth_pass/P01_unknown_plugin_preservation_WRAPUP.md`, `ARCHITECTURE.md` |
| `P02` | `4846a3a4fd22914d76901258269f9e8f4ff6c0a7` | Promoted subnode shell and pin semantics into `ea_node_editor.graph.subnode_contract` while keeping builtin type ids and authored shape stable. | `docs/specs/work_packets/arch_fourth_pass/P02_subnode_contract_promotion_WRAPUP.md`, `ARCHITECTURE.md` |
| `P03` | `8af79944be5cca6dd0c8dcfc4ec670f6566e5eda` | Added a registry-aware `ValidatedGraphMutation` seam for packet-owned authoring writes and canonicalized port-capacity validation. | `docs/specs/work_packets/arch_fourth_pass/P03_graph_mutation_validation_boundary_WRAPUP.md`, `ARCHITECTURE.md` |
| `P04` | `c62084a9432c81bb8df6bf7ce40a80d80406e240` | Shifted compiler and worker preparation onto typed runtime DTOs while leaving queue-boundary dict adapters stable. | `docs/specs/work_packets/arch_fourth_pass/P04_execution_runtime_dto_pipeline_WRAPUP.md`, `ARCHITECTURE.md` |
| `P05` | `cc0fd14e9e586eb44eae0d6a8108a78af6bdf340` | Moved packet-owned shell/QML state and commands behind presenter seams without breaking public `ShellWindow` contracts. | `docs/specs/work_packets/arch_fourth_pass/P05_shell_presenter_boundary_WRAPUP.md`, `ARCHITECTURE.md` |
| `P06` | `8c4b041311abc74d5833ac5423c451b84cb2a6b3` | Completed bridge-first packet-owned QML routing and moved shared node-presentation helpers below both `ui` and `ui_qml`. | `docs/specs/work_packets/arch_fourth_pass/P06_bridge_first_qml_contract_cleanup_WRAPUP.md`, `ARCHITECTURE.md` |
| `P07` | `dca3dd4cb4b982b11e16153610e3af5d4a8f8f2c` | Centralized verification phase, shell-isolation catalog, and proof-audit facts in `scripts/verification_manifest.py`. | `docs/specs/work_packets/arch_fourth_pass/P07_verification_manifest_consolidation_WRAPUP.md`, `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` |
| `P08` | `see wrap-up` | Publishes the packet-set closeout docs, QA matrix, updated architecture snapshot, and refreshed traceability anchors. | `docs/specs/work_packets/arch_fourth_pass/P08_docs_traceability_closeout_WRAPUP.md`, this matrix |

## Approved Regression Slice

- Rows marked `carried forward` are accepted packet-level verification commands from `P01` through `P07`.
- Rows marked `rerun in P08` are the only commands rerun during the packet-set closeout.

| Coverage | Command | Evidence Status | Packet Anchors |
|---|---|---|---|
| Unknown-plugin preservation | `./venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_serializer_schema_migration tests.test_registry_validation -v` | Carried forward from accepted `P01` verification. | `P01`, `REQ-PERSIST-004`, `REQ-PERSIST-005`, `REQ-PERSIST-009` |
| Subnode contract promotion | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_worker tests.test_graph_track_b tests.test_registry_validation tests.test_passive_runtime_wiring -v` | Carried forward from accepted `P02` verification. | `P02`, `REQ-NODE-011`, `REQ-NODE-015`, `REQ-NODE-018` |
| Validated graph mutation boundary | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_workspace_library_controller_unit tests.test_graph_scene_bridge_bind_regression -v` | Carried forward from accepted `P03` verification. | `P03`, `REQ-GRAPH-010`, `REQ-GRAPH-011`, `REQ-UI-014` |
| Runtime DTO pipeline | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_client tests.test_execution_worker tests.test_process_run_node tests.test_passive_runtime_wiring -v` | Carried forward from accepted `P04` verification. | `P04`, `REQ-EXEC-002`, `REQ-EXEC-009`, `REQ-NODE-018` |
| Shell presenter boundary | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_bootstrap tests.test_main_window_shell tests.test_shell_run_controller tests.test_shell_project_session_controller -v` | Carried forward from accepted `P05` verification. | `P05`, `REQ-ARCH-002`, `REQ-UI-001`, `REQ-UI-003` |
| Bridge-first QML contract cleanup | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_graph_scene_bridge_bind_regression tests.test_graph_surface_input_contract tests.test_passive_graph_surface_host -v` | Carried forward from accepted `P06` verification. | `P06`, `REQ-ARCH-010`, `REQ-ARCH-011`, `REQ-QA-013` |
| Verification manifest consolidation | `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py tests/test_traceability_checker.py -q` | Carried forward from accepted `P07` verification. | `P07`, `REQ-QA-014`, `REQ-QA-015`, `REQ-QA-016`, `REQ-QA-017` |
| Closeout proof audit | `./venv/Scripts/python.exe scripts/check_traceability.py` | Rerun in `P08` closeout. | `P08`, `REQ-QA-014`, `REQ-QA-017`, `REQ-QA-018` |
| Closeout workflow audit | `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run` | Rerun in `P08` closeout. | `P08`, `REQ-QA-014` |

## 2026-03-19 P08 Closeout Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Packet-owned proof audit passed after the architecture snapshot, closeout matrix, and traceability rows were refreshed. |
| `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run` | PASS | Dry-run output kept the project-venv `fast` workflow aligned with the manifest-backed non-shell pytest slice and documented ignore list. |

## Traceability Anchors

| Requirement Anchor | Closeout Evidence |
|---|---|
| `REQ-ARCH-002`, `AC-REQ-ARCH-002-01`, `REQ-ARCH-010`, `REQ-ARCH-011`, `AC-REQ-ARCH-011-01` | `ARCHITECTURE.md` closure snapshot plus the accepted `P05` and `P06` rows in this matrix. |
| `REQ-GRAPH-010`, `REQ-GRAPH-011`, `REQ-UI-014`, `REQ-NODE-015` | Accepted `P02` and `P03` outcomes, the carried-forward graph mutation/runtime rows in this matrix, and the updated residual-seam summary in `ARCHITECTURE.md`. |
| `REQ-PERSIST-004`, `REQ-PERSIST-005`, `REQ-PERSIST-009` | Accepted `P01` outcome plus the carried-forward serializer and registry regression row in this matrix. |
| `REQ-QA-008` through `REQ-QA-013` | The accepted `P01` through `P06` regression rows in this matrix, `docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md`, and the refreshed `TRACEABILITY_MATRIX.md` anchors. |
| `REQ-QA-014` through `REQ-QA-018` | `scripts/verification_manifest.py`, `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md`, `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`, `scripts/check_traceability.py`, and the `P08` rerun rows in this matrix. |

## Residual Risks

- Raw runtime entry points can still bypass the serializer/model hydration path that preserves unresolved plugin-authored content.
- Builtin subnode re-exports remain available, and `ea_node_editor.graph.subnode_contract` still lives higher in the package graph than the eventual ideal shared seam.
- Packet-external callers can still mutate `GraphModel` directly, packet-external fragment validation still carries local rule checks, and direct `add_edge` intentionally keeps the accepted data-port leniency.
- `compile_workspace_document()` and some `RuntimeNode` fields remain compatibility adapters for packet-external execution callers.
- `ShellWindow` compatibility slots, raw context-property exports from `shell_context_bootstrap.py`, and the widened `GraphCanvasBridge` contract remain in place for deferred consumers.
- Preserved unresolved payloads remain opaque in the live model, so there is still no packet-owned inspection or repair UI for missing-plugin content.
- Shell-backed regression suites still rely on fresh-process execution because the Windows Qt/QML multi-`ShellWindow()` lifetime issue is not yet resolved.
